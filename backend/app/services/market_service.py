"""
Market Data Service
Integrates with free APIs: Yahoo Finance (yfinance), FRED, Alpha Vantage
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

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
    """
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
    """
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
    Get real-time quote for a symbol
    """
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            'symbol': symbol,
            'price': info.get('regularMarketPrice'),
            'change': info.get('regularMarketChange'),
            'change_percent': info.get('regularMarketChangePercent'),
            'volume': info.get('regularMarketVolume'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'dividend_yield': info.get('dividendYield'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        return None


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
