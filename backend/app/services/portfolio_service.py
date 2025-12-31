"""
Portfolio Service
Handles portfolio optimization, backtesting, and performance calculations
"""

from typing import Dict, List, Any, Optional
import logging
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Sector ETF mapping
SECTOR_ETFS = {
    'XLK': {'name': 'Technology', 'sector': 'technology'},
    'XLV': {'name': 'Healthcare', 'sector': 'healthcare'},
    'XLE': {'name': 'Energy', 'sector': 'energy'},
    'XLF': {'name': 'Financials', 'sector': 'financials'},
    'XLI': {'name': 'Industrials', 'sector': 'industrials'},
    'XLY': {'name': 'Consumer Discretionary', 'sector': 'consumer_discretionary'},
    'XLP': {'name': 'Consumer Staples', 'sector': 'consumer_staples'},
    'XLU': {'name': 'Utilities', 'sector': 'utilities'},
    'XLB': {'name': 'Materials', 'sector': 'materials'},
    'XLRE': {'name': 'Real Estate', 'sector': 'real_estate'},
    'XLC': {'name': 'Communication Services', 'sector': 'communication_services'}
}


def calculate_portfolio_performance(portfolio, period: str = '1Y') -> Dict[str, Any]:
    """
    Calculate historical performance for a portfolio
    """
    try:
        import yfinance as yf
        import pandas as pd
        
        weights = portfolio.weights
        if not weights:
            return _get_empty_performance()
        
        # Map period to date range
        period_days = {'1M': 30, '3M': 90, '1Y': 365, 'ALL': 1825}
        days = period_days.get(period, 365)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Fetch historical data for all assets
        symbols = list(weights.keys())
        
        try:
            data = yf.download(symbols, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                return _get_simulated_performance(weights, period)
            
            # Get adjusted close prices
            if len(symbols) == 1:
                prices = data['Adj Close'].to_frame(symbols[0])
            else:
                prices = data['Adj Close']
            
            # Calculate returns
            returns = prices.pct_change().dropna()
            
            # Calculate portfolio returns
            weight_array = np.array([weights.get(s, 0) for s in returns.columns])
            portfolio_returns = returns.dot(weight_array)
            
            # Calculate cumulative returns
            cumulative = (1 + portfolio_returns).cumprod() - 1
            
            # Calculate metrics
            total_return = float(cumulative.iloc[-1]) * 100
            volatility = float(portfolio_returns.std() * np.sqrt(252) * 100)
            sharpe_ratio = (total_return / 100) / (volatility / 100) if volatility > 0 else 0
            
            # Max drawdown
            rolling_max = (1 + portfolio_returns).cumprod().expanding().max()
            drawdown = ((1 + portfolio_returns).cumprod() / rolling_max - 1)
            max_drawdown = float(drawdown.min() * 100)
            
            # Build time series
            time_series = []
            for date, cum_ret in cumulative.items():
                time_series.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'return': round(float(cum_ret) * 100, 2)
                })
            
            return {
                'total_return': round(total_return, 2),
                'volatility': round(volatility, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown, 2),
                'time_series': time_series,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch historical data: {e}")
            return _get_simulated_performance(weights, period)
            
    except ImportError:
        return _get_simulated_performance(portfolio.weights, period)


def _get_empty_performance() -> Dict[str, Any]:
    """Return empty performance data"""
    return {
        'total_return': 0,
        'volatility': 0,
        'sharpe_ratio': 0,
        'max_drawdown': 0,
        'time_series': [],
        'start_date': None,
        'end_date': None
    }


def _get_simulated_performance(weights: Dict[str, float], period: str) -> Dict[str, Any]:
    """Generate simulated performance data when real data unavailable"""
    np.random.seed(42)
    
    period_days = {'1M': 30, '3M': 90, '1Y': 365, 'ALL': 1825}
    days = period_days.get(period, 365)
    
    # Generate random returns based on typical market behavior
    daily_return = 0.0004  # ~10% annual
    daily_vol = 0.01  # ~16% annual vol
    
    returns = np.random.normal(daily_return, daily_vol, days)
    cumulative = np.cumprod(1 + returns) - 1
    
    # Generate dates
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=days-i)).strftime('%Y-%m-%d') for i in range(days)]
    
    time_series = [
        {'date': dates[i], 'return': round(float(cumulative[i]) * 100, 2)}
        for i in range(0, len(dates), max(1, len(dates) // 50))  # Sample ~50 points
    ]
    
    return {
        'total_return': round(float(cumulative[-1]) * 100, 2),
        'volatility': round(float(np.std(returns) * np.sqrt(252) * 100), 2),
        'sharpe_ratio': round(float(cumulative[-1]) / (np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0, 2),
        'max_drawdown': round(float(np.min(cumulative) * 100), 2),
        'time_series': time_series,
        'start_date': dates[0],
        'end_date': dates[-1],
        'note': 'Simulated data - real market data unavailable'
    }


def optimize_portfolio_weights(
    assets: List[str],
    objective: str = 'max_sharpe',
    use_causal: bool = True,
    causal_model_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Optimize portfolio weights using mean-variance optimization
    Optionally incorporate causal insights
    """
    try:
        # Get historical returns
        returns_data = _get_asset_returns(assets)
        
        if returns_data is None:
            return _get_default_optimization(assets, objective, use_causal)
        
        mean_returns = returns_data['mean_returns']
        cov_matrix = returns_data['cov_matrix']
        
        # Traditional Markowitz optimization
        traditional_weights = _optimize_markowitz(mean_returns, cov_matrix, objective)
        traditional_metrics = _calculate_metrics(traditional_weights, mean_returns, cov_matrix)
        
        # Causal optimization (adjust expected returns based on causal insights)
        if use_causal:
            causal_weights, causal_adjustments = _optimize_with_causal(
                mean_returns, cov_matrix, objective, assets, causal_model_id
            )
            causal_metrics = _calculate_metrics(causal_weights, mean_returns, cov_matrix)
        else:
            causal_weights = traditional_weights.copy()
            causal_metrics = traditional_metrics.copy()
            causal_adjustments = []
        
        return {
            'traditional': {
                'weights': {assets[i]: round(w, 4) for i, w in enumerate(traditional_weights)},
                'metrics': traditional_metrics
            },
            'causal': {
                'weights': {assets[i]: round(w, 4) for i, w in enumerate(causal_weights)},
                'metrics': causal_metrics,
                'adjustments': causal_adjustments
            },
            'improvement': {
                'return': round(causal_metrics['expected_return'] - traditional_metrics['expected_return'], 2),
                'volatility': round(traditional_metrics['volatility'] - causal_metrics['volatility'], 2),
                'sharpe': round(causal_metrics['sharpe_ratio'] - traditional_metrics['sharpe_ratio'], 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in portfolio optimization: {e}")
        return _get_default_optimization(assets, objective, use_causal)


def _get_asset_returns(assets: List[str], period: str = '1y') -> Optional[Dict]:
    """Fetch and calculate asset returns"""
    try:
        import yfinance as yf
        import pandas as pd
        
        data = yf.download(assets, period=period, progress=False)
        
        if data.empty:
            return None
        
        if len(assets) == 1:
            prices = data['Adj Close'].to_frame(assets[0])
        else:
            prices = data['Adj Close']
        
        returns = prices.pct_change().dropna()
        
        return {
            'mean_returns': returns.mean().values * 252,  # Annualized
            'cov_matrix': returns.cov().values * 252,  # Annualized
            'assets': assets
        }
        
    except Exception as e:
        logger.warning(f"Failed to get asset returns: {e}")
        return None


def _optimize_markowitz(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    objective: str
) -> np.ndarray:
    """
    Perform Markowitz mean-variance optimization
    """
    try:
        from scipy.optimize import minimize
        
        n_assets = len(mean_returns)
        
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        def portfolio_return(weights):
            return np.dot(weights, mean_returns)
        
        def neg_sharpe(weights, risk_free_rate=0.04):
            ret = portfolio_return(weights)
            vol = portfolio_volatility(weights)
            return -(ret - risk_free_rate) / vol if vol > 0 else 0
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        # Bounds (0 to 1 for each asset - long only)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess (equal weights)
        init_weights = np.array([1/n_assets] * n_assets)
        
        # Select objective function
        if objective == 'max_sharpe':
            result = minimize(neg_sharpe, init_weights, method='SLSQP',
                            bounds=bounds, constraints=constraints)
        elif objective == 'min_volatility':
            result = minimize(portfolio_volatility, init_weights, method='SLSQP',
                            bounds=bounds, constraints=constraints)
        elif objective == 'max_returns':
            result = minimize(lambda w: -portfolio_return(w), init_weights, method='SLSQP',
                            bounds=bounds, constraints=constraints)
        else:
            result = minimize(neg_sharpe, init_weights, method='SLSQP',
                            bounds=bounds, constraints=constraints)
        
        return result.x
        
    except ImportError:
        # Fallback to simple equal-weight or heuristic
        return np.array([1/len(mean_returns)] * len(mean_returns))


def _optimize_with_causal(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    objective: str,
    assets: List[str],
    causal_model_id: Optional[int]
) -> tuple:
    """
    Optimize portfolio with causal adjustments to expected returns
    """
    from app.services.causal_service import DEFAULT_SECTOR_SENSITIVITY
    
    # Get current economic conditions for causal adjustment
    # In production, this would fetch real economic data and forecasts
    economic_forecast = {
        'interest_rates': 0.005,  # Expected 0.5% increase
        'inflation': -0.002,  # Expected slight decrease
        'gdp_growth': 0.003  # Expected modest growth
    }
    
    # Adjust expected returns based on causal relationships
    adjusted_returns = mean_returns.copy()
    adjustments = []
    
    for i, asset in enumerate(assets):
        sector_info = SECTOR_ETFS.get(asset, {})
        sector_key = sector_info.get('sector', '')
        
        if sector_key in DEFAULT_SECTOR_SENSITIVITY:
            sensitivity = DEFAULT_SECTOR_SENSITIVITY[sector_key]
            
            total_adjustment = 0
            for factor, forecast in economic_forecast.items():
                if factor in sensitivity:
                    adjustment = sensitivity[factor] * forecast
                    total_adjustment += adjustment
            
            adjusted_returns[i] += total_adjustment
            
            if abs(total_adjustment) > 0.001:
                adjustments.append({
                    'asset': asset,
                    'sector': sector_info.get('name', asset),
                    'original_return': round(float(mean_returns[i]) * 100, 2),
                    'adjusted_return': round(float(adjusted_returns[i]) * 100, 2),
                    'adjustment': round(float(total_adjustment) * 100, 2),
                    'reason': f"Causal adjustment based on economic forecast"
                })
    
    # Optimize with adjusted returns
    causal_weights = _optimize_markowitz(adjusted_returns, cov_matrix, objective)
    
    return causal_weights, adjustments


def _calculate_metrics(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.04
) -> Dict[str, float]:
    """Calculate portfolio metrics"""
    portfolio_return = float(np.dot(weights, mean_returns))
    portfolio_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))
    sharpe = (portfolio_return - risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
    
    return {
        'expected_return': round(portfolio_return * 100, 2),
        'volatility': round(portfolio_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 2),
        'max_drawdown': round(-portfolio_vol * 2 * 100, 2)  # Approximate
    }


def _get_default_optimization(
    assets: List[str],
    objective: str,
    use_causal: bool
) -> Dict[str, Any]:
    """Return default optimization when real data unavailable"""
    n = len(assets)
    equal_weights = {asset: round(1/n, 4) for asset in assets}
    
    # Slightly different weights for causal
    causal_weights = equal_weights.copy()
    if use_causal and 'XLK' in assets:
        # Reduce tech, increase energy for demonstration
        causal_weights['XLK'] = round(causal_weights.get('XLK', 0.1) * 0.8, 4)
        if 'XLE' in assets:
            causal_weights['XLE'] = round(causal_weights.get('XLE', 0.1) * 1.3, 4)
        # Normalize
        total = sum(causal_weights.values())
        causal_weights = {k: round(v/total, 4) for k, v in causal_weights.items()}
    
    return {
        'traditional': {
            'weights': equal_weights,
            'metrics': {
                'expected_return': 10.5,
                'volatility': 15.2,
                'sharpe_ratio': 0.69,
                'max_drawdown': -12.3
            }
        },
        'causal': {
            'weights': causal_weights,
            'metrics': {
                'expected_return': 11.2,
                'volatility': 14.1,
                'sharpe_ratio': 0.79,
                'max_drawdown': -10.8
            },
            'adjustments': [
                {'asset': 'XLK', 'reason': 'Reduced due to rate sensitivity'},
                {'asset': 'XLE', 'reason': 'Increased due to inflation hedge'}
            ]
        },
        'improvement': {
            'return': 0.7,
            'volatility': 1.1,
            'sharpe': 0.1
        },
        'note': 'Default optimization - real market data unavailable'
    }


def run_backtest(
    weights: Dict[str, float],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run historical backtest on portfolio weights
    """
    try:
        import yfinance as yf
        import pandas as pd
        
        if not weights:
            return {'error': 'No weights provided'}
        
        # Default dates
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        symbols = list(weights.keys())
        
        data = yf.download(symbols, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            return _get_simulated_backtest(weights, start_date, end_date)
        
        if len(symbols) == 1:
            prices = data['Adj Close'].to_frame(symbols[0])
        else:
            prices = data['Adj Close']
        
        returns = prices.pct_change().dropna()
        
        # Calculate portfolio returns
        weight_array = np.array([weights.get(s, 0) for s in returns.columns])
        portfolio_returns = returns.dot(weight_array)
        
        # Cumulative returns
        cumulative = (1 + portfolio_returns).cumprod()
        
        # Metrics
        total_return = float(cumulative.iloc[-1] - 1) * 100
        ann_return = float((cumulative.iloc[-1] ** (252/len(returns)) - 1) * 100)
        volatility = float(portfolio_returns.std() * np.sqrt(252) * 100)
        sharpe = ann_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative / rolling_max - 1)
        max_drawdown = float(drawdown.min() * 100)
        
        # Time series
        time_series = [
            {'date': date.strftime('%Y-%m-%d'), 'value': round(float(val), 4)}
            for date, val in cumulative.items()
        ]
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_return': round(total_return, 2),
            'annualized_return': round(ann_return, 2),
            'volatility': round(volatility, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_drawdown, 2),
            'time_series': time_series[::max(1, len(time_series)//100)]  # Sample 100 points
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return _get_simulated_backtest(weights, start_date, end_date)


def _get_simulated_backtest(
    weights: Dict[str, float],
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """Generate simulated backtest results"""
    np.random.seed(42)
    
    days = 252
    returns = np.random.normal(0.0004, 0.01, days)
    cumulative = np.cumprod(1 + returns)
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'total_return': round(float(cumulative[-1] - 1) * 100, 2),
        'annualized_return': round(float((cumulative[-1] - 1) * 100), 2),
        'volatility': round(float(np.std(returns) * np.sqrt(252) * 100), 2),
        'sharpe_ratio': 0.65,
        'max_drawdown': -8.5,
        'time_series': [],
        'note': 'Simulated backtest - real market data unavailable'
    }
