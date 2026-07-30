"""
Market Data Service (rebuilt)
=============================
Near-real-time market data built on batched Yahoo Finance requests + FRED.

Principles:
- ONE batched download serves a whole watchlist (no per-symbol .info loops).
- Short TTL caches during market hours, longer when the market is closed.
- Every payload is honestly labeled with `source` ('live' | 'cached') and
  `as_of`. If data cannot be fetched we serve the last cached value marked
  stale, or return an explicit error - we never fabricate prices, volumes,
  PE ratios, or news.
"""

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from zoneinfo import ZoneInfo

import pandas as pd

logger = logging.getLogger(__name__)

EASTERN = ZoneInfo('America/New_York')

# ---------------------------------------------------------------------------
# Cache (in-memory, TTL based, thread-safe enough for a single Flask worker)
# ---------------------------------------------------------------------------
_cache: Dict[str, Any] = {}
_cache_timestamps: Dict[str, float] = {}
_cache_lock = threading.Lock()


def get_cached(key: str, ttl_seconds: int = 300) -> Optional[Any]:
    with _cache_lock:
        if key in _cache and time.time() - _cache_timestamps.get(key, 0) < ttl_seconds:
            return _cache[key]
    return None


def get_cached_stale(key: str) -> Optional[Any]:
    """Return a cached value regardless of age (for graceful degradation)."""
    with _cache_lock:
        return _cache.get(key)


def set_cached(key: str, value: Any) -> None:
    with _cache_lock:
        _cache[key] = value
        _cache_timestamps[key] = time.time()


# ---------------------------------------------------------------------------
# Symbol directory - names/sectors for search & display ranking ONLY.
# Never a source of prices.
# ---------------------------------------------------------------------------
SYMBOL_DIRECTORY: Dict[str, Dict[str, Any]] = {
    # Tech
    'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'},
    'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology'},
    'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Technology'},
    'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical'},
    'META': {'name': 'Meta Platforms Inc.', 'sector': 'Technology'},
    'NVDA': {'name': 'NVIDIA Corporation', 'sector': 'Technology'},
    'TSLA': {'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical'},
    'AMD': {'name': 'Advanced Micro Devices', 'sector': 'Technology'},
    'INTC': {'name': 'Intel Corporation', 'sector': 'Technology'},
    'CRM': {'name': 'Salesforce Inc.', 'sector': 'Technology'},
    'ADBE': {'name': 'Adobe Inc.', 'sector': 'Technology'},
    'ORCL': {'name': 'Oracle Corporation', 'sector': 'Technology'},
    'CSCO': {'name': 'Cisco Systems Inc.', 'sector': 'Technology'},
    'QCOM': {'name': 'QUALCOMM Inc.', 'sector': 'Technology'},
    'TXN': {'name': 'Texas Instruments', 'sector': 'Technology'},
    'AVGO': {'name': 'Broadcom Inc.', 'sector': 'Technology'},
    'NFLX': {'name': 'Netflix Inc.', 'sector': 'Communication Services'},
    'SHOP': {'name': 'Shopify Inc.', 'sector': 'Technology'},
    'SQ': {'name': 'Block Inc.', 'sector': 'Technology'},
    'PYPL': {'name': 'PayPal Holdings', 'sector': 'Financial Services'},
    # Financials
    'JPM': {'name': 'JPMorgan Chase & Co.', 'sector': 'Financial Services'},
    'BAC': {'name': 'Bank of America Corp', 'sector': 'Financial Services'},
    'WFC': {'name': 'Wells Fargo & Co', 'sector': 'Financial Services'},
    'GS': {'name': 'Goldman Sachs Group', 'sector': 'Financial Services'},
    'MS': {'name': 'Morgan Stanley', 'sector': 'Financial Services'},
    'V': {'name': 'Visa Inc.', 'sector': 'Financial Services'},
    'MA': {'name': 'Mastercard Inc.', 'sector': 'Financial Services'},
    'BRK-B': {'name': 'Berkshire Hathaway B', 'sector': 'Financial Services'},
    # Healthcare
    'JNJ': {'name': 'Johnson & Johnson', 'sector': 'Healthcare'},
    'UNH': {'name': 'UnitedHealth Group', 'sector': 'Healthcare'},
    'PFE': {'name': 'Pfizer Inc.', 'sector': 'Healthcare'},
    'MRK': {'name': 'Merck & Co Inc.', 'sector': 'Healthcare'},
    'ABBV': {'name': 'AbbVie Inc.', 'sector': 'Healthcare'},
    'TMO': {'name': 'Thermo Fisher Scientific', 'sector': 'Healthcare'},
    'ABT': {'name': 'Abbott Laboratories', 'sector': 'Healthcare'},
    'LLY': {'name': 'Eli Lilly and Co', 'sector': 'Healthcare'},
    # Consumer
    'WMT': {'name': 'Walmart Inc.', 'sector': 'Consumer Defensive'},
    'PG': {'name': 'Procter & Gamble Co', 'sector': 'Consumer Defensive'},
    'KO': {'name': 'Coca-Cola Company', 'sector': 'Consumer Defensive'},
    'PEP': {'name': 'PepsiCo Inc.', 'sector': 'Consumer Defensive'},
    'COST': {'name': 'Costco Wholesale', 'sector': 'Consumer Defensive'},
    'HD': {'name': 'Home Depot Inc.', 'sector': 'Consumer Cyclical'},
    'NKE': {'name': 'Nike Inc.', 'sector': 'Consumer Cyclical'},
    'DIS': {'name': 'Walt Disney Company', 'sector': 'Communication Services'},
    'MCD': {'name': "McDonald's Corp", 'sector': 'Consumer Cyclical'},
    'SBUX': {'name': 'Starbucks Corp', 'sector': 'Consumer Cyclical'},
    # Energy / Industrials / Telecom
    'XOM': {'name': 'Exxon Mobil Corp', 'sector': 'Energy'},
    'CVX': {'name': 'Chevron Corporation', 'sector': 'Energy'},
    'COP': {'name': 'ConocoPhillips', 'sector': 'Energy'},
    'CAT': {'name': 'Caterpillar Inc.', 'sector': 'Industrials'},
    'BA': {'name': 'Boeing Company', 'sector': 'Industrials'},
    'GE': {'name': 'GE Aerospace', 'sector': 'Industrials'},
    'UPS': {'name': 'United Parcel Service', 'sector': 'Industrials'},
    'RTX': {'name': 'RTX Corporation', 'sector': 'Industrials'},
    'VZ': {'name': 'Verizon Communications', 'sector': 'Communication Services'},
    'T': {'name': 'AT&T Inc.', 'sector': 'Communication Services'},
    'CMCSA': {'name': 'Comcast Corporation', 'sector': 'Communication Services'},
    # Utilities / REIT / Materials
    'NEE': {'name': 'NextEra Energy', 'sector': 'Utilities'},
    'DUK': {'name': 'Duke Energy', 'sector': 'Utilities'},
    'SO': {'name': 'Southern Company', 'sector': 'Utilities'},
    'AMT': {'name': 'American Tower', 'sector': 'Real Estate'},
    'PLD': {'name': 'Prologis', 'sector': 'Real Estate'},
    'SPG': {'name': 'Simon Property Group', 'sector': 'Real Estate'},
    'LIN': {'name': 'Linde plc', 'sector': 'Materials'},
    'APD': {'name': 'Air Products', 'sector': 'Materials'},
    'DD': {'name': 'DuPont de Nemours', 'sector': 'Materials'},
    # Broad ETFs
    'SPY': {'name': 'SPDR S&P 500 ETF', 'sector': 'ETF'},
    'QQQ': {'name': 'Invesco QQQ Trust', 'sector': 'ETF'},
    'IWM': {'name': 'iShares Russell 2000 ETF', 'sector': 'ETF'},
    'DIA': {'name': 'SPDR Dow Jones Industrial', 'sector': 'ETF'},
    'VTI': {'name': 'Vanguard Total Stock Market', 'sector': 'ETF'},
    'VOO': {'name': 'Vanguard S&P 500 ETF', 'sector': 'ETF'},
    'ARKK': {'name': 'ARK Innovation ETF', 'sector': 'ETF'},
    # Sector ETFs
    'XLK': {'name': 'Technology Select Sector', 'sector': 'ETF'},
    'XLF': {'name': 'Financial Select Sector', 'sector': 'ETF'},
    'XLE': {'name': 'Energy Select Sector', 'sector': 'ETF'},
    'XLV': {'name': 'Health Care Select Sector', 'sector': 'ETF'},
    'XLI': {'name': 'Industrial Select Sector', 'sector': 'ETF'},
    'XLY': {'name': 'Consumer Discretionary Select', 'sector': 'ETF'},
    'XLP': {'name': 'Consumer Staples Select', 'sector': 'ETF'},
    'XLU': {'name': 'Utilities Select Sector', 'sector': 'ETF'},
    'XLB': {'name': 'Materials Select Sector', 'sector': 'ETF'},
    'XLRE': {'name': 'Real Estate Select Sector', 'sector': 'ETF'},
    'XLC': {'name': 'Communication Services Select', 'sector': 'ETF'},
}

SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLV': 'Healthcare',
    'XLE': 'Energy',
    'XLF': 'Financials',
    'XLI': 'Industrials',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLU': 'Utilities',
    'XLB': 'Materials',
    'XLRE': 'Real Estate',
    'XLC': 'Communication Services',
}

FRED_SERIES = {
    'fed_rate': 'FEDFUNDS',
    'cpi': 'CPIAUCSL',
    'gdp': 'GDP',
    'unemployment': 'UNRATE',
    'vix': 'VIXCLS',
    'treasury_10y': 'DGS10',
    'oil_wti': 'DCOILWTICO',
}

TRENDING_SYMBOLS = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META', 'GOOGL', 'AMD', 'AVGO', 'NFLX', 'SPY', 'QQQ']


# ---------------------------------------------------------------------------
# Market clock
# ---------------------------------------------------------------------------

def get_market_status() -> Dict[str, Any]:
    """US equity market session status (approximate - no holiday calendar)."""
    now = datetime.now(EASTERN)
    minutes = now.hour * 60 + now.minute
    weekday = now.weekday() < 5
    if not weekday:
        state = 'closed'
    elif 9 * 60 + 30 <= minutes < 16 * 60:
        state = 'open'
    elif 4 * 60 <= minutes < 9 * 60 + 30:
        state = 'pre'
    elif 16 * 60 <= minutes < 20 * 60:
        state = 'post'
    else:
        state = 'closed'
    return {
        'state': state,
        'is_open': state == 'open',
        'local_time_et': now.strftime('%Y-%m-%d %H:%M:%S'),
        'note': 'Session inferred from clock; US holidays not modeled',
    }


def _quote_ttl() -> int:
    """Quote cache TTL: 30s during the session, 10 min otherwise."""
    return 30 if get_market_status()['is_open'] else 600


# ---------------------------------------------------------------------------
# Batched quote snapshots
# ---------------------------------------------------------------------------

def _fetch_snapshot(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    One batched daily-bar download for all symbols. The last daily bar tracks
    the live session intraday, so this gives price / change / range / volume
    in a single request.
    """
    import yfinance as yf

    raw = yf.download(
        symbols, period='7d', interval='1d',
        auto_adjust=False, progress=False, group_by='column', threads=True,
    )
    out: Dict[str, Dict[str, Any]] = {}
    if raw is None or raw.empty:
        return out
    if not isinstance(raw.columns, pd.MultiIndex):
        raw.columns = pd.MultiIndex.from_product([raw.columns, [symbols[0]]])

    now_iso = datetime.now(EASTERN).isoformat()
    for s in symbols:
        try:
            close = raw[('Close', s)].dropna()
            if close.empty:
                continue
            price = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) > 1 else price
            bar_date = close.index[-1]
            vol = raw[('Volume', s)].dropna()
            high = raw[('High', s)].dropna()
            low = raw[('Low', s)].dropna()
            out[s] = {
                'symbol': s,
                'price': round(price, 2),
                'previous_close': round(prev, 2),
                'change': round(price - prev, 2),
                'change_percent': round((price - prev) / prev * 100, 2) if prev else 0.0,
                'day_high': round(float(high.iloc[-1]), 2) if not high.empty else None,
                'day_low': round(float(low.iloc[-1]), 2) if not low.empty else None,
                'volume': int(vol.iloc[-1]) if not vol.empty else 0,
                'bar_date': bar_date.strftime('%Y-%m-%d'),
                'as_of': now_iso,
                'source': 'live',
            }
        except Exception:
            continue
    return out


def get_quotes(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Batched quotes for a list of symbols with per-symbol caching.
    Serves stale cached data (clearly marked) if the network fails.
    """
    symbols = [s.upper() for s in symbols if s]
    ttl = _quote_ttl()
    result: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []

    for s in symbols:
        cached = get_cached(f'snap_{s}', ttl_seconds=ttl)
        if cached:
            result[s] = cached
        else:
            missing.append(s)

    if missing:
        try:
            fresh = _fetch_snapshot(missing)
            for s, q in fresh.items():
                set_cached(f'snap_{s}', q)
                result[s] = q
        except Exception as e:
            logger.warning(f"Snapshot fetch failed for {missing}: {e}")
        # Anything still missing: serve stale cache, marked
        for s in missing:
            if s not in result:
                stale = get_cached_stale(f'snap_{s}')
                if stale:
                    stale = dict(stale)
                    stale['source'] = 'cached'
                    result[s] = stale
    return result


def _get_symbol_meta(symbol: str) -> Dict[str, Any]:
    """Slow-changing metadata (name, sector, market cap, PE) cached 24h."""
    cache_key = f'meta_{symbol}'
    cached = get_cached(cache_key, ttl_seconds=86400)
    if cached:
        return cached

    meta = {
        'name': SYMBOL_DIRECTORY.get(symbol, {}).get('name', symbol),
        'sector': SYMBOL_DIRECTORY.get(symbol, {}).get('sector', 'N/A'),
        'market_cap': None,
        'pe_ratio': None,
        'dividend_yield': None,
        'fifty_two_week_high': None,
        'fifty_two_week_low': None,
    }
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info or {}
        meta.update({
            'name': info.get('shortName') or info.get('longName') or meta['name'],
            'sector': info.get('sector') or meta['sector'],
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'dividend_yield': info.get('dividendYield'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
        })
    except Exception as e:
        logger.debug(f"Metadata fetch failed for {symbol}: {e}")
    set_cached(cache_key, meta)
    return meta


def get_real_time_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Full quote (snapshot + metadata) for a single symbol."""
    symbol = symbol.upper()
    quotes = get_quotes([symbol])
    snap = quotes.get(symbol)
    if not snap:
        return None
    meta = _get_symbol_meta(symbol)
    return {
        **snap,
        'name': meta['name'],
        'sector': meta['sector'],
        'market_cap': meta['market_cap'],
        'pe_ratio': meta['pe_ratio'],
        'dividend_yield': meta['dividend_yield'],
        'fifty_two_week_high': meta['fifty_two_week_high'],
        'fifty_two_week_low': meta['fifty_two_week_low'],
        'timestamp': snap['as_of'],
    }


def get_fallback_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Compatibility shim (old code imported this). Returns the last cached
    snapshot marked stale - never fabricated data.
    """
    stale = get_cached_stale(f'snap_{symbol.upper()}')
    if stale:
        stale = dict(stale)
        stale['source'] = 'cached'
        return stale
    return None


# ---------------------------------------------------------------------------
# Indicators / macro
# ---------------------------------------------------------------------------

def get_current_indicators() -> Dict[str, Any]:
    """Key market indicators from one batched snapshot + FRED macro."""
    cached = get_cached('market_indicators', ttl_seconds=_quote_ttl())
    if cached:
        return cached

    indicators: Dict[str, Any] = {}
    snaps = get_quotes(['SPY', '^VIX', '^TNX'])

    def _ind(sym: str, label: str, unit: Optional[str] = None) -> Dict[str, Any]:
        q = snaps.get(sym)
        if not q:
            return {'value': None, 'change': None, 'label': label, 'trend': 'neutral', 'unavailable': True}
        d = {
            'value': q['price'],
            'change': q['change_percent'],
            'label': label,
            'trend': 'up' if q['change_percent'] > 0 else ('down' if q['change_percent'] < 0 else 'neutral'),
            'as_of': q.get('bar_date'),
            'source': q.get('source', 'live'),
        }
        if unit:
            d['unit'] = unit
        return d

    indicators['sp500'] = _ind('SPY', 'S&P 500 (SPY)')
    indicators['vix'] = _ind('^VIX', 'VIX (Volatility)')
    indicators['treasury_10y'] = _ind('^TNX', '10Y Treasury', unit='%')

    # Macro from FRED (real values with real dates when a key is configured)
    macro = get_fred_data()
    if macro.get('fed_rate', {}).get('value') is not None:
        indicators['fed_rate'] = {
            'value': macro['fed_rate']['value'],
            'label': 'Fed Funds Rate', 'unit': '%',
            'as_of': macro['fed_rate'].get('date'),
            'trend': 'neutral',
            'source': 'fred' if not macro.get('is_fallback') else 'cached',
        }
    if macro.get('cpi_yoy', {}).get('value') is not None:
        indicators['cpi'] = {
            'value': macro['cpi_yoy']['value'],
            'label': 'CPI Inflation (YoY)', 'unit': '%',
            'as_of': macro['cpi_yoy'].get('date'),
            'trend': 'neutral',
            'source': 'fred' if not macro.get('is_fallback') else 'cached',
        }

    set_cached('market_indicators', indicators)
    return indicators


def get_indicators_as_of(as_of_date: str) -> Dict[str, Any]:
    """
    Point-in-time SPY/VIX/10Y-treasury indicators for a historical date,
    sourced from stored daily closes rather than a live quote.

    Used by the walk-forward backtest so that a fold's causal return
    adjustment only sees data available as of that fold's training cutoff,
    instead of leaking today's live market state into a historical decision.
    """
    from app.services.price_store import get_price_store

    symbols = {'sp500': 'SPY', 'vix': '^VIX', 'treasury_10y': '^TNX'}
    labels = {'sp500': 'S&P 500 (SPY)', 'vix': 'VIX (Volatility)', 'treasury_10y': '10Y Treasury'}

    history = get_price_store().get_history(list(symbols.values()), end=as_of_date, refresh=False)

    indicators: Dict[str, Any] = {}
    for key, sym in symbols.items():
        series = history[sym].dropna() if sym in history.columns else pd.Series(dtype=float)
        if series.empty:
            indicators[key] = {
                'value': None, 'change': None, 'label': labels[key],
                'trend': 'neutral', 'unavailable': True,
            }
            continue

        value = float(series.iloc[-1])
        change_pct = float(series.pct_change().iloc[-1] * 100) if len(series) > 1 else 0.0
        d = {
            'value': value,
            'change': change_pct,
            'label': labels[key],
            'trend': 'up' if change_pct > 0 else ('down' if change_pct < 0 else 'neutral'),
            'as_of': series.index[-1].strftime('%Y-%m-%d'),
            'source': 'historical',
        }
        if key == 'treasury_10y':
            d['unit'] = '%'
        indicators[key] = d

    return indicators


def get_fred_data(series: Optional[str] = None) -> Dict[str, Any]:
    """
    Macro data from FRED. Computes CPI YoY inflation properly.
    Without an API key, returns last-known values clearly marked as such.
    """
    cache_key = f'fred_{series or "all"}'
    cached = get_cached(cache_key, ttl_seconds=6 * 3600)
    if cached:
        return cached

    api_key = os.getenv('FRED_API_KEY')
    if api_key:
        try:
            from fredapi import Fred
            fred = Fred(api_key=api_key)

            if series:
                data = fred.get_series(series).dropna()
                result = {
                    'series': series,
                    'value': round(float(data.iloc[-1]), 2) if not data.empty else None,
                    'date': data.index[-1].strftime('%Y-%m-%d') if not data.empty else None,
                }
                set_cached(cache_key, result)
                return result

            result = {}
            for name, sid in FRED_SERIES.items():
                try:
                    data = fred.get_series(sid).dropna()
                    if data.empty:
                        continue
                    result[name] = {
                        'series_id': sid,
                        'value': round(float(data.iloc[-1]), 2),
                        'date': data.index[-1].strftime('%Y-%m-%d'),
                    }
                    if name == 'cpi' and len(data) > 12:
                        yoy = (data.iloc[-1] / data.iloc[-13] - 1) * 100
                        result['cpi_yoy'] = {
                            'series_id': sid,
                            'value': round(float(yoy), 2),
                            'date': data.index[-1].strftime('%Y-%m-%d'),
                        }
                except Exception as e:
                    logger.warning(f"FRED series {sid} failed: {e}")
            set_cached(cache_key, result)
            return result
        except Exception as e:
            logger.error(f"FRED fetch failed: {e}")

    # No key / failure: last-known values, clearly marked
    fallback = {
        'fed_rate': {'series_id': 'FEDFUNDS', 'value': 4.25, 'date': '2026-03-01'},
        'cpi_yoy': {'series_id': 'CPIAUCSL', 'value': 2.8, 'date': '2026-02-01'},
        'gdp': {'series_id': 'GDP', 'value': None, 'date': None},
        'unemployment': {'series_id': 'UNRATE', 'value': 4.3, 'date': '2026-02-01'},
        'is_fallback': True,
        'note': 'FRED_API_KEY not configured - last-known values shown',
    }
    if series:
        for data in fallback.values():
            if isinstance(data, dict) and data.get('series_id') == series:
                return {'series': series, 'value': data['value'], 'date': data['date'], 'is_fallback': True}
        return {'series': series, 'value': None, 'date': None, 'is_fallback': True}
    return fallback


# ---------------------------------------------------------------------------
# Sectors / benchmark / history
# ---------------------------------------------------------------------------

def get_sector_performance(period: str = '1M') -> List[Dict[str, Any]]:
    """Performance of all 11 sector ETFs from one batched history download."""
    cache_key = f'sector_performance_{period}'
    ttl = 60 if period == '1D' else 600
    cached = get_cached(cache_key, ttl_seconds=ttl)
    if cached:
        return cached

    symbols = list(SECTOR_ETFS.keys())
    sectors: List[Dict[str, Any]] = []

    if period == '1D':
        snaps = get_quotes(symbols)
        for sym, name in SECTOR_ETFS.items():
            q = snaps.get(sym)
            if q:
                sectors.append({
                    'symbol': sym, 'name': name,
                    'price': q['price'], 'change': q['change'],
                    'change_percent': q['change_percent'],
                    'volume': q['volume'], 'source': q.get('source', 'live'),
                })
    else:
        try:
            from app.services.price_store import get_price_store
            period_days = {'1W': 7, '1M': 30, '3M': 91, '1Y': 365}
            days = period_days.get(period, 30)
            start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            prices = get_price_store().get_history(symbols, start=start)
            snaps = get_quotes(symbols)
            for sym, name in SECTOR_ETFS.items():
                if sym not in prices.columns:
                    continue
                series = prices[sym].dropna()
                if series.empty:
                    continue
                start_price = float(series.iloc[0])
                # Prefer live price for the endpoint
                end_price = snaps.get(sym, {}).get('price') or float(series.iloc[-1])
                change_pct = (end_price - start_price) / start_price * 100
                sectors.append({
                    'symbol': sym, 'name': name,
                    'price': round(end_price, 2),
                    'change': round(end_price - start_price, 2),
                    'change_percent': round(change_pct, 2),
                    'volume': snaps.get(sym, {}).get('volume', 0),
                    'source': snaps.get(sym, {}).get('source', 'live'),
                })
        except Exception as e:
            logger.error(f"Sector performance failed: {e}")

    if sectors:
        set_cached(cache_key, sectors)
        return sectors

    stale = get_cached_stale(cache_key)
    return stale if stale else []


def get_historical_prices(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = '1d',
) -> List[Dict[str, Any]]:
    """Historical OHLCV. Daily data comes from the local price store."""
    symbol = symbol.upper()
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    try:
        if interval == '1d':
            from app.services.price_store import get_price_store
            hist = get_price_store().get_ohlcv(symbol, start=start_date, end=end_date)
        else:
            import yfinance as yf
            hist = yf.Ticker(symbol).history(start=start_date, end=end_date, interval=interval)
        data = []
        for date, row in hist.iterrows():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(float(row['Open']), 2),
                'high': round(float(row['High']), 2),
                'low': round(float(row['Low']), 2),
                'close': round(float(row['Close']), 2),
                'volume': int(row['Volume']) if row['Volume'] == row['Volume'] else 0,
            })
        return data
    except Exception as e:
        logger.error(f"Historical prices failed for {symbol}: {e}")
        return []


def get_benchmark_data(period: str = '1Y') -> Dict[str, Any]:
    """S&P 500 (SPY) benchmark performance from the price store."""
    cache_key = f'benchmark_{period}'
    cached = get_cached(cache_key, ttl_seconds=600)
    if cached:
        return cached

    try:
        from app.services.price_store import get_price_store
        period_days = {'1M': 30, '3M': 91, '1Y': 365, 'ALL': 5000}
        days = period_days.get(period, 365)
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        prices = get_price_store().get_history(['SPY'], start=start)
        if prices.empty or 'SPY' not in prices.columns:
            stale = get_cached_stale(cache_key)
            return stale if stale else {'error': 'Benchmark data unavailable'}

        series = prices['SPY'].dropna()
        start_price = float(series.iloc[0])
        end_price = float(series.iloc[-1])
        returns = series.pct_change().dropna()
        result = {
            'current_price': round(end_price, 2),
            'total_return': round((end_price - start_price) / start_price * 100, 2),
            'volatility': round(float(returns.std()) * (252 ** 0.5) * 100, 2),
            'time_series': [
                {
                    'date': d.strftime('%Y-%m-%d'),
                    'close': round(float(v), 2),
                    'return_pct': round((float(v) - start_price) / start_price * 100, 2),
                }
                for d, v in series.items()
            ],
        }
        set_cached(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Benchmark data failed: {e}")
        stale = get_cached_stale(cache_key)
        return stale if stale else {'error': 'Benchmark data unavailable'}


# ---------------------------------------------------------------------------
# Market condition / search / news / trending
# ---------------------------------------------------------------------------

def assess_market_condition() -> Dict[str, Any]:
    """Score market condition from VIX level, S&P trend, and yield move."""
    try:
        indicators = get_current_indicators()
        score = 0
        factors = []

        vix_value = indicators.get('vix', {}).get('value')
        if vix_value is not None:
            if vix_value < 15:
                score += 2
                factors.append('Low volatility (VIX < 15)')
            elif vix_value < 20:
                score += 1
                factors.append('Normal volatility')
            elif vix_value < 30:
                score -= 1
                factors.append('Elevated volatility')
            else:
                score -= 2
                factors.append('High fear (VIX > 30)')

        sp500_change = indicators.get('sp500', {}).get('change') or 0
        if sp500_change > 0:
            score += 1
            factors.append('S&P 500 positive today')
        elif sp500_change < 0:
            score -= 1
            factors.append('S&P 500 negative today')

        if score >= 2:
            condition, description = 'bullish', 'Market conditions are favorable for risk assets'
        elif score <= -2:
            condition, description = 'bearish', 'Market conditions suggest caution'
        else:
            condition, description = 'neutral', 'Mixed signals in the market'

        return {
            'state': condition,
            'score': score,
            'description': description,
            'factors': factors,
            'indicators': indicators,
            'market_status': get_market_status(),
            'timestamp': datetime.now(EASTERN).isoformat(),
        }
    except Exception as e:
        logger.error(f"Market condition assessment failed: {e}")
        return {
            'state': 'neutral', 'score': 0,
            'description': 'Unable to assess market conditions',
            'factors': [], 'indicators': {},
            'timestamp': datetime.now(EASTERN).isoformat(),
        }


def search_stocks(query: str) -> List[Dict[str, Any]]:
    """
    Search by symbol or name. Matches the local directory first, then Yahoo
    search for unknown symbols. Prices attached from one batched snapshot.
    """
    cache_key = f'stock_search_{query.upper()}'
    cached = get_cached(cache_key, ttl_seconds=120)
    if cached:
        return cached

    q = query.upper().strip()
    matches: List[str] = []

    for symbol, data in SYMBOL_DIRECTORY.items():
        if q in symbol or query.lower() in data['name'].lower():
            matches.append(symbol)
    # Exact symbol first, then alphabetical
    matches.sort(key=lambda s: (0 if s == q else 1, s))
    matches = matches[:8]

    # No exact directory hit? Ask Yahoo search (prefer US listings, no '.suffix')
    if q not in SYMBOL_DIRECTORY and len(q) <= 6:
        try:
            import yfinance as yf
            found = yf.Search(q, max_results=8).quotes
            found.sort(key=lambda i: ('.' in (i.get('symbol') or ''), (i.get('symbol') or '') != q))
            for item in found:
                sym = (item.get('symbol') or '').upper()
                if sym and sym not in matches and item.get('quoteType') in ('EQUITY', 'ETF'):
                    matches.insert(0, sym)
                    if sym not in SYMBOL_DIRECTORY:
                        SYMBOL_DIRECTORY[sym] = {
                            'name': item.get('shortname') or item.get('longname') or sym,
                            'sector': item.get('sector', 'N/A'),
                        }
                    break
        except Exception as e:
            logger.debug(f"Yahoo search failed for {q}: {e}")

    snaps = get_quotes(matches[:10])
    results = []
    for sym in matches[:10]:
        snap = snaps.get(sym)
        entry = {
            'symbol': sym,
            'name': SYMBOL_DIRECTORY.get(sym, {}).get('name', sym),
            'sector': SYMBOL_DIRECTORY.get(sym, {}).get('sector', 'N/A'),
            'price': snap['price'] if snap else None,
            'change': snap['change_percent'] if snap else None,
            'volume': snap['volume'] if snap else None,
            'source': snap.get('source') if snap else 'unavailable',
        }
        results.append(entry)

    set_cached(cache_key, results)
    return results


def _parse_news_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle both old (flat) and new (nested 'content') yfinance news formats."""
    try:
        content = item.get('content', item)
        title = content.get('title', '')
        if not title:
            return None
        link = ''
        if isinstance(content.get('canonicalUrl'), dict):
            link = content['canonicalUrl'].get('url', '')
        elif isinstance(content.get('clickThroughUrl'), dict):
            link = content['clickThroughUrl'].get('url', '')
        else:
            link = item.get('link', '')
        publisher = ''
        if isinstance(content.get('provider'), dict):
            publisher = content['provider'].get('displayName', '')
        else:
            publisher = item.get('publisher', '')
        published = content.get('pubDate') or content.get('displayTime')
        if not published and item.get('providerPublishTime'):
            published = datetime.fromtimestamp(item['providerPublishTime']).isoformat()
        thumbnail = None
        thumb = content.get('thumbnail') or item.get('thumbnail')
        if isinstance(thumb, dict):
            resolutions = thumb.get('resolutions') or []
            if resolutions:
                thumbnail = resolutions[0].get('url')
        return {
            'title': title,
            'summary': content.get('summary', content.get('description', '')),
            'publisher': publisher,
            'link': link,
            'published': published,
            'type': content.get('contentType', 'news'),
            'thumbnail': thumbnail,
            'related_tickers': item.get('relatedTickers', []),
        }
    except Exception:
        return None


def get_stock_news(symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """Real financial news from Yahoo. Returns [] if unavailable - no fake news."""
    cache_key = f'news_{symbol or "market"}'
    cached = get_cached(cache_key, ttl_seconds=600)
    if cached:
        return cached

    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol if symbol else 'SPY')
        news_items = []
        for item in (ticker.news or [])[:12]:
            parsed = _parse_news_item(item)
            if parsed:
                news_items.append(parsed)
        if news_items:
            set_cached(cache_key, news_items)
        return news_items
    except Exception as e:
        logger.error(f"News fetch failed: {e}")
        stale = get_cached_stale(cache_key)
        return stale if stale else []


def get_trending_stocks() -> List[Dict[str, Any]]:
    """Most-active large caps from one batched snapshot, sorted by |move|."""
    cached = get_cached('trending_stocks', ttl_seconds=_quote_ttl() * 2)
    if cached:
        return cached

    snaps = get_quotes(TRENDING_SYMBOLS)
    results = []
    for sym in TRENDING_SYMBOLS:
        q = snaps.get(sym)
        if not q:
            continue
        results.append({
            'symbol': sym,
            'name': SYMBOL_DIRECTORY.get(sym, {}).get('name', sym),
            'price': q['price'],
            'change': q['change_percent'],
            'volume': q['volume'],
            'day_high': q['day_high'],
            'day_low': q['day_low'],
            'source': q.get('source', 'live'),
        })
    results.sort(key=lambda x: abs(x.get('change') or 0), reverse=True)

    if results:
        set_cached('trending_stocks', results)
        return results
    stale = get_cached_stale('trending_stocks')
    return stale if stale else []
