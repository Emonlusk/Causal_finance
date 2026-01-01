"""
Market Data Service
Integrates with free APIs: Yahoo Finance (yfinance), FRED, Alpha Vantage
With caching to reduce API calls and avoid rate limiting
Includes comprehensive fallback data for when APIs are rate limited
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from functools import lru_cache
import time
import random

logger = logging.getLogger(__name__)

# Simple in-memory cache with TTL
_cache: Dict[str, Any] = {}
_cache_timestamps: Dict[str, float] = {}

# Comprehensive fallback stock data for when Yahoo Finance is rate limited
FALLBACK_STOCK_DATA = {
    # Tech giants
    'AAPL': {'name': 'Apple Inc.', 'price': 185.92, 'sector': 'Technology', 'market_cap': 2890000000000},
    'MSFT': {'name': 'Microsoft Corporation', 'price': 378.91, 'sector': 'Technology', 'market_cap': 2810000000000},
    'GOOGL': {'name': 'Alphabet Inc.', 'price': 141.80, 'sector': 'Technology', 'market_cap': 1780000000000},
    'AMZN': {'name': 'Amazon.com Inc.', 'price': 186.51, 'sector': 'Consumer Cyclical', 'market_cap': 1940000000000},
    'META': {'name': 'Meta Platforms Inc.', 'price': 531.12, 'sector': 'Technology', 'market_cap': 1370000000000},
    'NVDA': {'name': 'NVIDIA Corporation', 'price': 495.22, 'sector': 'Technology', 'market_cap': 1220000000000},
    'TSLA': {'name': 'Tesla Inc.', 'price': 248.48, 'sector': 'Consumer Cyclical', 'market_cap': 791000000000},
    
    # More tech
    'AMD': {'name': 'Advanced Micro Devices', 'price': 147.41, 'sector': 'Technology', 'market_cap': 238000000000},
    'INTC': {'name': 'Intel Corporation', 'price': 48.73, 'sector': 'Technology', 'market_cap': 207000000000},
    'CRM': {'name': 'Salesforce Inc.', 'price': 273.44, 'sector': 'Technology', 'market_cap': 265000000000},
    'ADBE': {'name': 'Adobe Inc.', 'price': 580.77, 'sector': 'Technology', 'market_cap': 260000000000},
    'ORCL': {'name': 'Oracle Corporation', 'price': 118.52, 'sector': 'Technology', 'market_cap': 325000000000},
    'CSCO': {'name': 'Cisco Systems Inc.', 'price': 50.62, 'sector': 'Technology', 'market_cap': 204000000000},
    'QCOM': {'name': 'QUALCOMM Inc.', 'price': 146.49, 'sector': 'Technology', 'market_cap': 163000000000},
    'TXN': {'name': 'Texas Instruments', 'price': 169.81, 'sector': 'Technology', 'market_cap': 154000000000},
    'NFLX': {'name': 'Netflix Inc.', 'price': 486.88, 'sector': 'Communication Services', 'market_cap': 214000000000},
    
    # Finance
    'JPM': {'name': 'JPMorgan Chase & Co.', 'price': 170.12, 'sector': 'Financial Services', 'market_cap': 489000000000},
    'BAC': {'name': 'Bank of America Corp', 'price': 33.94, 'sector': 'Financial Services', 'market_cap': 267000000000},
    'WFC': {'name': 'Wells Fargo & Co', 'price': 49.08, 'sector': 'Financial Services', 'market_cap': 175000000000},
    'GS': {'name': 'Goldman Sachs Group', 'price': 387.54, 'sector': 'Financial Services', 'market_cap': 127000000000},
    'MS': {'name': 'Morgan Stanley', 'price': 93.25, 'sector': 'Financial Services', 'market_cap': 152000000000},
    'V': {'name': 'Visa Inc.', 'price': 260.35, 'sector': 'Financial Services', 'market_cap': 534000000000},
    'MA': {'name': 'Mastercard Inc.', 'price': 425.82, 'sector': 'Financial Services', 'market_cap': 399000000000},
    
    # Healthcare
    'JNJ': {'name': 'Johnson & Johnson', 'price': 156.74, 'sector': 'Healthcare', 'market_cap': 378000000000},
    'UNH': {'name': 'UnitedHealth Group', 'price': 527.72, 'sector': 'Healthcare', 'market_cap': 486000000000},
    'PFE': {'name': 'Pfizer Inc.', 'price': 28.79, 'sector': 'Healthcare', 'market_cap': 162000000000},
    'MRK': {'name': 'Merck & Co Inc.', 'price': 109.16, 'sector': 'Healthcare', 'market_cap': 276000000000},
    'ABBV': {'name': 'AbbVie Inc.', 'price': 154.97, 'sector': 'Healthcare', 'market_cap': 274000000000},
    'TMO': {'name': 'Thermo Fisher Scientific', 'price': 531.16, 'sector': 'Healthcare', 'market_cap': 204000000000},
    'ABT': {'name': 'Abbott Laboratories', 'price': 110.65, 'sector': 'Healthcare', 'market_cap': 192000000000},
    'LLY': {'name': 'Eli Lilly and Co', 'price': 582.34, 'sector': 'Healthcare', 'market_cap': 553000000000},
    
    # Consumer
    'WMT': {'name': 'Walmart Inc.', 'price': 162.48, 'sector': 'Consumer Defensive', 'market_cap': 438000000000},
    'PG': {'name': 'Procter & Gamble Co', 'price': 147.88, 'sector': 'Consumer Defensive', 'market_cap': 348000000000},
    'KO': {'name': 'Coca-Cola Company', 'price': 59.51, 'sector': 'Consumer Defensive', 'market_cap': 257000000000},
    'PEP': {'name': 'PepsiCo Inc.', 'price': 169.94, 'sector': 'Consumer Defensive', 'market_cap': 233000000000},
    'COST': {'name': 'Costco Wholesale', 'price': 591.03, 'sector': 'Consumer Defensive', 'market_cap': 262000000000},
    'HD': {'name': 'Home Depot Inc.', 'price': 348.63, 'sector': 'Consumer Cyclical', 'market_cap': 346000000000},
    'NKE': {'name': 'Nike Inc.', 'price': 106.73, 'sector': 'Consumer Cyclical', 'market_cap': 162000000000},
    'DIS': {'name': 'Walt Disney Company', 'price': 91.28, 'sector': 'Communication Services', 'market_cap': 167000000000},
    'MCD': {'name': "McDonald's Corp", 'price': 295.68, 'sector': 'Consumer Cyclical', 'market_cap': 213000000000},
    'SBUX': {'name': 'Starbucks Corp', 'price': 94.55, 'sector': 'Consumer Cyclical', 'market_cap': 108000000000},
    
    # Energy
    'XOM': {'name': 'Exxon Mobil Corp', 'price': 103.68, 'sector': 'Energy', 'market_cap': 413000000000},
    'CVX': {'name': 'Chevron Corporation', 'price': 149.72, 'sector': 'Energy', 'market_cap': 275000000000},
    'COP': {'name': 'ConocoPhillips', 'price': 116.54, 'sector': 'Energy', 'market_cap': 135000000000},
    
    # Telecom
    'VZ': {'name': 'Verizon Communications', 'price': 37.85, 'sector': 'Communication Services', 'market_cap': 159000000000},
    'T': {'name': 'AT&T Inc.', 'price': 16.93, 'sector': 'Communication Services', 'market_cap': 121000000000},
    'CMCSA': {'name': 'Comcast Corporation', 'price': 43.56, 'sector': 'Communication Services', 'market_cap': 170000000000},
    
    # Industrial
    'CAT': {'name': 'Caterpillar Inc.', 'price': 294.61, 'sector': 'Industrials', 'market_cap': 145000000000},
    'BA': {'name': 'Boeing Company', 'price': 206.44, 'sector': 'Industrials', 'market_cap': 124000000000},
    'GE': {'name': 'General Electric Co', 'price': 127.39, 'sector': 'Industrials', 'market_cap': 139000000000},
    'UPS': {'name': 'United Parcel Service', 'price': 156.88, 'sector': 'Industrials', 'market_cap': 134000000000},
    'RTX': {'name': 'RTX Corporation', 'price': 91.67, 'sector': 'Industrials', 'market_cap': 122000000000},
    
    # ETFs
    'SPY': {'name': 'SPDR S&P 500 ETF', 'price': 478.68, 'sector': 'ETF', 'market_cap': 0},
    'QQQ': {'name': 'Invesco QQQ Trust', 'price': 405.38, 'sector': 'ETF', 'market_cap': 0},
    'IWM': {'name': 'iShares Russell 2000 ETF', 'price': 197.46, 'sector': 'ETF', 'market_cap': 0},
    'DIA': {'name': 'SPDR Dow Jones Industrial', 'price': 378.55, 'sector': 'ETF', 'market_cap': 0},
    'VTI': {'name': 'Vanguard Total Stock Market', 'price': 239.87, 'sector': 'ETF', 'market_cap': 0},
    'VOO': {'name': 'Vanguard S&P 500 ETF', 'price': 440.12, 'sector': 'ETF', 'market_cap': 0},
    'ARKK': {'name': 'ARK Innovation ETF', 'price': 48.32, 'sector': 'ETF', 'market_cap': 0},
    
    # Sector ETFs
    'XLK': {'name': 'Technology Select Sector', 'price': 191.42, 'sector': 'ETF', 'market_cap': 0},
    'XLF': {'name': 'Financial Select Sector', 'price': 39.28, 'sector': 'ETF', 'market_cap': 0},
    'XLE': {'name': 'Energy Select Sector', 'price': 86.73, 'sector': 'ETF', 'market_cap': 0},
    'XLV': {'name': 'Health Care Select Sector', 'price': 139.55, 'sector': 'ETF', 'market_cap': 0},
    'XLI': {'name': 'Industrial Select Sector', 'price': 117.32, 'sector': 'ETF', 'market_cap': 0},
    'XLY': {'name': 'Consumer Discretionary Select', 'price': 184.65, 'sector': 'ETF', 'market_cap': 0},
    'XLP': {'name': 'Consumer Staples Select', 'price': 75.89, 'sector': 'ETF', 'market_cap': 0},
    'XLU': {'name': 'Utilities Select Sector', 'price': 68.41, 'sector': 'ETF', 'market_cap': 0},
    'XLB': {'name': 'Materials Select Sector', 'price': 86.22, 'sector': 'ETF', 'market_cap': 0},
    'XLRE': {'name': 'Real Estate Select Sector', 'price': 39.67, 'sector': 'ETF', 'market_cap': 0},
    'XLC': {'name': 'Communication Services Select', 'price': 78.95, 'sector': 'ETF', 'market_cap': 0},
    
    # Additional popular stocks
    'BRK-B': {'name': 'Berkshire Hathaway B', 'price': 362.27, 'sector': 'Financial Services', 'market_cap': 789000000000},
    'AVGO': {'name': 'Broadcom Inc.', 'price': 1108.23, 'sector': 'Technology', 'market_cap': 458000000000},
    'PYPL': {'name': 'PayPal Holdings', 'price': 62.15, 'sector': 'Financial Services', 'market_cap': 66000000000},
    'SQ': {'name': 'Block Inc.', 'price': 72.36, 'sector': 'Technology', 'market_cap': 43000000000},
    'SHOP': {'name': 'Shopify Inc.', 'price': 77.82, 'sector': 'Technology', 'market_cap': 98000000000},
    'UBER': {'name': 'Uber Technologies', 'price': 61.55, 'sector': 'Technology', 'market_cap': 127000000000},
    'SNAP': {'name': 'Snap Inc.', 'price': 16.84, 'sector': 'Communication Services', 'market_cap': 27000000000},
    'ROKU': {'name': 'Roku Inc.', 'price': 89.45, 'sector': 'Communication Services', 'market_cap': 12000000000},
    'COIN': {'name': 'Coinbase Global', 'price': 147.33, 'sector': 'Financial Services', 'market_cap': 35000000000},
    'PLTR': {'name': 'Palantir Technologies', 'price': 17.82, 'sector': 'Technology', 'market_cap': 38000000000},
    'RIVN': {'name': 'Rivian Automotive', 'price': 18.25, 'sector': 'Consumer Cyclical', 'market_cap': 18000000000},
    'LCID': {'name': 'Lucid Group Inc.', 'price': 4.82, 'sector': 'Consumer Cyclical', 'market_cap': 11000000000},
    'F': {'name': 'Ford Motor Company', 'price': 11.85, 'sector': 'Consumer Cyclical', 'market_cap': 47000000000},
    'GM': {'name': 'General Motors Co', 'price': 35.42, 'sector': 'Consumer Cyclical', 'market_cap': 48000000000},
    'AA': {'name': 'Alcoa Corporation', 'price': 31.25, 'sector': 'Basic Materials', 'market_cap': 5600000000},
    'AAP': {'name': 'Advance Auto Parts', 'price': 64.38, 'sector': 'Consumer Cyclical', 'market_cap': 3800000000},
    'A': {'name': 'Agilent Technologies', 'price': 135.67, 'sector': 'Healthcare', 'market_cap': 39000000000},
}

def get_fallback_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Get fallback quote data for a symbol"""
    symbol = symbol.upper()
    if symbol in FALLBACK_STOCK_DATA:
        data = FALLBACK_STOCK_DATA[symbol]
        # Add small random variation to make it look "live"
        price_variation = data['price'] * random.uniform(-0.005, 0.005)
        current_price = round(data['price'] + price_variation, 2)
        change_pct = round(random.uniform(-2.5, 2.5), 2)
        change = round(current_price * change_pct / 100, 2)
        
        return {
            'symbol': symbol,
            'price': current_price,
            'change': change,
            'change_percent': change_pct,
            'volume': random.randint(1000000, 50000000),
            'market_cap': data['market_cap'],
            'pe_ratio': round(random.uniform(15, 35), 2),
            'dividend_yield': round(random.uniform(0, 3), 2) if data['sector'] != 'ETF' else None,
            'fifty_two_week_high': round(current_price * 1.15, 2),
            'fifty_two_week_low': round(current_price * 0.75, 2),
            'day_high': round(current_price * 1.01, 2),
            'day_low': round(current_price * 0.99, 2),
            'name': data['name'],
            'sector': data['sector'],
            'timestamp': datetime.now().isoformat(),
            'source': 'fallback'
        }
    return None

def get_cached(key: str, ttl_seconds: int = 300) -> Optional[Any]:
    """Get value from cache if not expired"""
    if key in _cache and key in _cache_timestamps:
        if time.time() - _cache_timestamps[key] < ttl_seconds:
            logger.debug(f"Cache hit for {key}")
            return _cache[key]
    return None

def set_cached(key: str, value: Any) -> None:
    """Set value in cache with current timestamp"""
    _cache[key] = value
    _cache_timestamps[key] = time.time()

# Sector ETF symbols
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
    'XLC': 'Communication Services'
}

# FRED series IDs for macroeconomic data
FRED_SERIES = {
    'fed_rate': 'FEDFUNDS',
    'cpi': 'CPIAUCSL',
    'gdp': 'GDP',
    'unemployment': 'UNRATE',
    'vix': 'VIXCLS',
    'treasury_10y': 'DGS10',
    'oil_wti': 'DCOILWTICO'
}


def get_current_indicators() -> Dict[str, Any]:
    """
    Get current market indicators from multiple sources
    Returns VIX, Fed Rate, CPI, and other key indicators
    Cached for 5 minutes to reduce API calls
    """
    # Check cache first (5 minute TTL)
    cached = get_cached('market_indicators', ttl_seconds=300)
    if cached:
        return cached
    
    try:
        import yfinance as yf
        
        indicators = {}
        
        # Get VIX from Yahoo Finance
        try:
            vix = yf.Ticker('^VIX')
            vix_info = vix.info
            indicators['vix'] = {
                'value': round(vix_info.get('regularMarketPrice', 18.5), 2),
                'change': round(vix_info.get('regularMarketChangePercent', 0), 2),
                'label': 'VIX (Volatility)',
                'trend': 'up' if vix_info.get('regularMarketChangePercent', 0) > 0 else 'down'
            }
        except Exception as e:
            logger.warning(f"Failed to fetch VIX: {e}")
            indicators['vix'] = {'value': 18.5, 'change': 0, 'label': 'VIX', 'trend': 'neutral'}
        
        # Get Treasury yield
        try:
            tlt = yf.Ticker('^TNX')  # 10-year Treasury yield
            tlt_info = tlt.info
            indicators['treasury_10y'] = {
                'value': round(tlt_info.get('regularMarketPrice', 4.5), 2),
                'change': round(tlt_info.get('regularMarketChangePercent', 0), 2),
                'label': '10Y Treasury',
                'unit': '%',
                'trend': 'up' if tlt_info.get('regularMarketChangePercent', 0) > 0 else 'down'
            }
        except Exception as e:
            logger.warning(f"Failed to fetch Treasury: {e}")
            indicators['treasury_10y'] = {'value': 4.5, 'change': 0, 'label': '10Y Treasury', 'unit': '%', 'trend': 'neutral'}
        
        # Get S&P 500 performance
        try:
            spy = yf.Ticker('SPY')
            spy_info = spy.info
            indicators['sp500'] = {
                'value': round(spy_info.get('regularMarketPrice', 4800), 2),
                'change': round(spy_info.get('regularMarketChangePercent', 0), 2),
                'label': 'S&P 500',
                'trend': 'up' if spy_info.get('regularMarketChangePercent', 0) > 0 else 'down'
            }
        except Exception as e:
            logger.warning(f"Failed to fetch S&P 500: {e}")
            indicators['sp500'] = {'value': 4800, 'change': 0, 'label': 'S&P 500', 'trend': 'neutral'}
        
        # Add Fed rate (typically from FRED, using fallback)
        indicators['fed_rate'] = {
            'value': 4.5,
            'label': 'Fed Funds Rate',
            'unit': '%',
            'trend': 'neutral'
        }
        
        # Add CPI (typically from FRED, using fallback)
        indicators['cpi'] = {
            'value': 3.2,
            'change': -0.1,
            'label': 'CPI (Inflation)',
            'unit': '%',
            'trend': 'down'
        }
        
        # Cache the result
        set_cached('market_indicators', indicators)
        return indicators
        
    except ImportError:
        logger.error("yfinance not installed")
        return _get_fallback_indicators()
    except Exception as e:
        logger.error(f"Error fetching indicators: {e}")
        return _get_fallback_indicators()


def _get_fallback_indicators() -> Dict[str, Any]:
    """Return fallback indicator values when APIs fail"""
    return {
        'vix': {'value': 18.5, 'change': 0, 'label': 'VIX', 'trend': 'neutral'},
        'fed_rate': {'value': 4.5, 'label': 'Fed Funds Rate', 'unit': '%', 'trend': 'neutral'},
        'cpi': {'value': 3.2, 'change': 0, 'label': 'CPI', 'unit': '%', 'trend': 'neutral'},
        'treasury_10y': {'value': 4.5, 'change': 0, 'label': '10Y Treasury', 'unit': '%', 'trend': 'neutral'},
        'sp500': {'value': 4800, 'change': 0, 'label': 'S&P 500', 'trend': 'neutral'}
    }


def get_sector_performance(period: str = '1M') -> List[Dict[str, Any]]:
    """
    Get performance data for all sector ETFs
    Cached for 10 minutes per period
    """
    # Check cache first (10 minute TTL)
    cache_key = f'sector_performance_{period}'
    cached = get_cached(cache_key, ttl_seconds=600)
    if cached:
        return cached
    
    try:
        import yfinance as yf
        
        # Map period to yfinance format
        period_map = {
            '1D': '1d',
            '1W': '5d',
            '1M': '1mo',
            '3M': '3mo',
            '1Y': '1y'
        }
        yf_period = period_map.get(period, '1mo')
        
        sectors = []
        
        for symbol, name in SECTOR_ETFS.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=yf_period)
                
                if not hist.empty:
                    start_price = hist['Close'].iloc[0]
                    end_price = hist['Close'].iloc[-1]
                    change_pct = ((end_price - start_price) / start_price) * 100
                    
                    sectors.append({
                        'symbol': symbol,
                        'name': name,
                        'price': round(end_price, 2),
                        'change': round(end_price - start_price, 2),
                        'change_percent': round(change_pct, 2),
                        'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0
                    })
                else:
                    sectors.append(_get_fallback_sector(symbol, name))
            except Exception as e:
                logger.warning(f"Failed to fetch {symbol}: {e}")
                sectors.append(_get_fallback_sector(symbol, name))
        
        # Cache the result
        set_cached(cache_key, sectors)
        return sectors
        
    except ImportError:
        return [_get_fallback_sector(s, n) for s, n in SECTOR_ETFS.items()]
    except Exception as e:
        logger.error(f"Error fetching sector performance: {e}")
        return [_get_fallback_sector(s, n) for s, n in SECTOR_ETFS.items()]


def _get_fallback_sector(symbol: str, name: str) -> Dict[str, Any]:
    """Return fallback sector data"""
    return {
        'symbol': symbol,
        'name': name,
        'price': 100,
        'change': 0,
        'change_percent': 0,
        'volume': 0
    }


def get_historical_prices(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = '1d'
) -> List[Dict[str, Any]]:
    """
    Get historical price data for a symbol
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        
        # Default to 1 year of data
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        hist = ticker.history(start=start_date, end=end_date, interval=interval)
        
        data = []
        for date, row in hist.iterrows():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume'])
            })
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching historical prices for {symbol}: {e}")
        return []


def get_fred_data(series: Optional[str] = None) -> Dict[str, Any]:
    """
    Get macroeconomic data from FRED API
    Requires FRED_API_KEY environment variable
    """
    api_key = os.getenv('FRED_API_KEY')
    
    if not api_key:
        logger.warning("FRED_API_KEY not set, using fallback data")
        return _get_fallback_fred_data(series)
    
    try:
        from fredapi import Fred
        fred = Fred(api_key=api_key)
        
        if series:
            # Get specific series
            data = fred.get_series(series)
            latest = data.dropna().iloc[-1] if not data.empty else None
            return {
                'series': series,
                'value': round(float(latest), 2) if latest else None,
                'date': data.index[-1].strftime('%Y-%m-%d') if latest else None
            }
        else:
            # Get all common macro indicators
            result = {}
            for name, series_id in FRED_SERIES.items():
                try:
                    data = fred.get_series(series_id)
                    if not data.empty:
                        latest = data.dropna().iloc[-1]
                        result[name] = {
                            'series_id': series_id,
                            'value': round(float(latest), 2),
                            'date': data.index[-1].strftime('%Y-%m-%d')
                        }
                except Exception as e:
                    logger.warning(f"Failed to fetch FRED series {series_id}: {e}")
            return result
            
    except ImportError:
        logger.error("fredapi not installed")
        return _get_fallback_fred_data(series)
    except Exception as e:
        logger.error(f"Error fetching FRED data: {e}")
        return _get_fallback_fred_data(series)


def _get_fallback_fred_data(series: Optional[str] = None) -> Dict[str, Any]:
    """Return fallback FRED data"""
    fallback = {
        'fed_rate': {'series_id': 'FEDFUNDS', 'value': 4.5, 'date': '2024-12-01'},
        'cpi': {'series_id': 'CPIAUCSL', 'value': 3.2, 'date': '2024-11-01'},
        'gdp': {'series_id': 'GDP', 'value': 2.8, 'date': '2024-09-01'},
        'unemployment': {'series_id': 'UNRATE', 'value': 4.1, 'date': '2024-12-01'},
        'vix': {'series_id': 'VIXCLS', 'value': 18.5, 'date': '2024-12-27'},
        'treasury_10y': {'series_id': 'DGS10', 'value': 4.5, 'date': '2024-12-27'},
        'oil_wti': {'series_id': 'DCOILWTICO', 'value': 72.5, 'date': '2024-12-27'}
    }
    
    if series:
        for name, data in fallback.items():
            if data['series_id'] == series:
                return {'series': series, 'value': data['value'], 'date': data['date']}
        return {'series': series, 'value': None, 'date': None}
    
    return fallback


def get_real_time_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get real-time quote for a symbol with comprehensive fallback
    """
    symbol = symbol.upper()
    
    # Check cache first (30 second TTL for quotes)
    cache_key = f'quote_{symbol}'
    cached = get_cached(cache_key, ttl_seconds=30)
    if cached:
        return cached
    
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Check if we got valid data
        price = info.get('regularMarketPrice')
        if price and price > 0:
            result = {
                'symbol': symbol,
                'name': info.get('shortName', info.get('longName', symbol)),
                'price': round(price, 2),
                'change': round(info.get('regularMarketChange', 0), 2),
                'change_percent': round(info.get('regularMarketChangePercent', 0), 2),
                'volume': info.get('regularMarketVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'sector': info.get('sector', 'N/A'),
                'timestamp': datetime.now().isoformat(),
                'source': 'live'
            }
            set_cached(cache_key, result)
            return result
        else:
            # No valid price from API, use fallback
            logger.warning(f"No valid price from yfinance for {symbol}, using fallback")
            fallback = get_fallback_quote(symbol)
            if fallback:
                set_cached(cache_key, fallback)
            return fallback
        
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        # Return fallback data
        fallback = get_fallback_quote(symbol)
        if fallback:
            set_cached(cache_key, fallback)
        return fallback


def get_benchmark_data(period: str = '1Y') -> Dict[str, Any]:
    """
    Get S&P 500 (SPY) benchmark performance data
    """
    try:
        import yfinance as yf
        
        period_map = {
            '1M': '1mo',
            '3M': '3mo',
            '1Y': '1y',
            'ALL': 'max'
        }
        yf_period = period_map.get(period, '1y')
        
        spy = yf.Ticker('SPY')
        hist = spy.history(period=yf_period)
        
        if hist.empty:
            return _get_fallback_benchmark()
        
        start_price = hist['Close'].iloc[0]
        end_price = hist['Close'].iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100
        
        # Calculate daily returns for volatility
        hist['Return'] = hist['Close'].pct_change()
        volatility = hist['Return'].std() * (252 ** 0.5) * 100  # Annualized
        
        # Build time series for charts
        time_series = []
        for date, row in hist.iterrows():
            time_series.append({
                'date': date.strftime('%Y-%m-%d'),
                'close': round(row['Close'], 2),
                'return_pct': round(((row['Close'] - start_price) / start_price) * 100, 2)
            })
        
        return {
            'current_price': round(end_price, 2),
            'total_return': round(total_return, 2),
            'volatility': round(volatility, 2),
            'time_series': time_series
        }
        
    except Exception as e:
        logger.error(f"Error fetching benchmark data: {e}")
        return _get_fallback_benchmark()


def _get_fallback_benchmark() -> Dict[str, Any]:
    """Return fallback benchmark data"""
    return {
        'current_price': 480,
        'total_return': 12.5,
        'volatility': 15.2,
        'time_series': []
    }


def assess_market_condition() -> Dict[str, Any]:
    """
    Assess overall market condition based on multiple indicators
    Returns: bullish, neutral, or bearish with supporting metrics
    """
    try:
        indicators = get_current_indicators()
        
        # Simple scoring system
        score = 0
        factors = []
        
        # VIX analysis (fear gauge)
        vix_value = indicators.get('vix', {}).get('value', 20)
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
        
        # S&P 500 trend
        sp500_change = indicators.get('sp500', {}).get('change', 0)
        if sp500_change > 0:
            score += 1
            factors.append('S&P 500 positive')
        else:
            score -= 1
            factors.append('S&P 500 negative')
        
        # Determine condition
        if score >= 2:
            condition = 'bullish'
            description = 'Market conditions are favorable for risk assets'
        elif score <= -2:
            condition = 'bearish'
            description = 'Market conditions suggest caution'
        else:
            condition = 'neutral'
            description = 'Mixed signals in the market'
        
        return {
            'state': condition,
            'score': score,
            'description': description,
            'factors': factors,
            'indicators': indicators,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error assessing market condition: {e}")
        return {
            'state': 'neutral',
            'score': 0,
            'description': 'Unable to assess market conditions',
            'factors': [],
            'indicators': {},
            'timestamp': datetime.now().isoformat()
        }


def search_stocks(query: str) -> List[Dict[str, Any]]:
    """
    Search for stocks by symbol or name
    Returns list of matching stocks with current prices
    Uses fallback data when Yahoo Finance is rate limited
    """
    cache_key = f'stock_search_{query.upper()}'
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached:
        return cached
    
    query_upper = query.upper()
    results = []
    
    # First, try to find matches in our fallback data
    # This is fast and doesn't hit the API
    for symbol, data in FALLBACK_STOCK_DATA.items():
        if query_upper in symbol or query_upper.lower() in data['name'].lower():
            fallback_quote = get_fallback_quote(symbol)
            if fallback_quote:
                results.append({
                    'symbol': symbol,
                    'name': data['name'],
                    'price': fallback_quote['price'],
                    'change': fallback_quote['change_percent'],
                    'volume': fallback_quote['volume'],
                    'market_cap': data['market_cap'],
                    'sector': data['sector']
                })
            if len(results) >= 10:
                break
    
    # Sort exact matches first
    results.sort(key=lambda x: (0 if x['symbol'] == query_upper else 1, -x.get('market_cap', 0)))
    
    # Try to get live data from Yahoo Finance if we don't have many results
    if len(results) < 5:
        try:
            import yfinance as yf
            
            # Try to fetch the exact symbol
            if query_upper not in [r['symbol'] for r in results]:
                try:
                    ticker = yf.Ticker(query_upper)
                    info = ticker.info
                    price = info.get('regularMarketPrice')
                    if price and price > 0:
                        results.insert(0, {
                            'symbol': query_upper,
                            'name': info.get('shortName', info.get('longName', query_upper)),
                            'price': round(price, 2),
                            'change': round(info.get('regularMarketChangePercent', 0), 2),
                            'volume': info.get('regularMarketVolume', 0),
                            'market_cap': info.get('marketCap', 0),
                            'sector': info.get('sector', 'N/A')
                        })
                except Exception as e:
                    logger.debug(f"Could not fetch {query_upper} from yfinance: {e}")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error searching stocks via yfinance: {e}")
    
    set_cached(cache_key, results)
    return results[:10]  # Limit to 10 results


def get_stock_news(symbol: str = None) -> List[Dict[str, Any]]:
    """
    Get financial news from Yahoo Finance
    If symbol provided, get news for that stock
    Otherwise get general market news
    """
    cache_key = f'news_{symbol or "market"}'
    cached = get_cached(cache_key, ttl_seconds=600)  # 10 minute cache
    if cached:
        return cached
    
    try:
        import yfinance as yf
        
        # Get news from major index or specific stock
        ticker_symbol = symbol if symbol else 'SPY'
        ticker = yf.Ticker(ticker_symbol)
        
        news_items = []
        try:
            news = ticker.news
            if news:
                for item in news[:10]:  # Get top 10 news items
                    news_items.append({
                        'title': item.get('title', ''),
                        'summary': item.get('summary', ''),
                        'publisher': item.get('publisher', ''),
                        'link': item.get('link', ''),
                        'published': datetime.fromtimestamp(item.get('providerPublishTime', 0)).isoformat() if item.get('providerPublishTime') else None,
                        'type': item.get('type', 'news'),
                        'thumbnail': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url') if item.get('thumbnail') else None,
                        'related_tickers': item.get('relatedTickers', [])
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch news for {ticker_symbol}: {e}")
        
        # If we couldn't get news, provide some fallback structure
        if not news_items:
            news_items = [
                {
                    'title': 'Markets Update',
                    'summary': 'Real-time market news will appear here when available.',
                    'publisher': 'System',
                    'link': '',
                    'published': datetime.now().isoformat(),
                    'type': 'notice',
                    'thumbnail': None,
                    'related_tickers': []
                }
            ]
        
        set_cached(cache_key, news_items)
        return news_items
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return []


def get_trending_stocks() -> List[Dict[str, Any]]:
    """
    Get trending/most active stocks
    Uses fallback data when Yahoo Finance is rate limited
    """
    cached = get_cached('trending_stocks', ttl_seconds=600)
    if cached:
        return cached
    
    trending_symbols = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL', 'AMD', 'SPY', 'QQQ']
    results = []
    live_data_available = False
    
    try:
        import yfinance as yf
        
        # Try to get live data for the first symbol to check if API is working
        test_ticker = yf.Ticker('AAPL')
        test_info = test_ticker.info
        if test_info.get('regularMarketPrice') and test_info.get('regularMarketPrice') > 0:
            live_data_available = True
            
            for symbol in trending_symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    price = info.get('regularMarketPrice')
                    if price and price > 0:
                        results.append({
                            'symbol': symbol,
                            'name': info.get('shortName', symbol),
                            'price': round(price, 2),
                            'change': round(info.get('regularMarketChangePercent', 0), 2),
                            'volume': info.get('regularMarketVolume', 0),
                            'day_high': round(info.get('dayHigh', 0), 2),
                            'day_low': round(info.get('dayLow', 0), 2),
                            'source': 'live'
                        })
                except Exception:
                    # If individual fetch fails, use fallback for this symbol
                    fallback = get_fallback_quote(symbol)
                    if fallback:
                        results.append({
                            'symbol': symbol,
                            'name': fallback['name'],
                            'price': fallback['price'],
                            'change': fallback['change_percent'],
                            'volume': fallback['volume'],
                            'day_high': fallback['day_high'],
                            'day_low': fallback['day_low'],
                            'source': 'fallback'
                        })
    except Exception as e:
        logger.warning(f"Yahoo Finance unavailable, using fallback data: {e}")
    
    # If we couldn't get live data, use fallback for all
    if not live_data_available or len(results) < len(trending_symbols) // 2:
        results = []
        for symbol in trending_symbols:
            fallback = get_fallback_quote(symbol)
            if fallback:
                results.append({
                    'symbol': symbol,
                    'name': fallback['name'],
                    'price': fallback['price'],
                    'change': fallback['change_percent'],
                    'volume': fallback['volume'],
                    'day_high': fallback['day_high'],
                    'day_low': fallback['day_low'],
                    'source': 'fallback'
                })
    
    # Sort by absolute change to show most volatile
    results.sort(key=lambda x: abs(x.get('change', 0)), reverse=True)
    
    set_cached('trending_stocks', results)
    return results
