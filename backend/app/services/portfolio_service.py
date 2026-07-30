"""
Portfolio Service
Handles portfolio optimization, backtesting, and performance calculations.

Implements:
- Markowitz mean-variance optimization with sector weight caps
- Causal-adjusted portfolio construction
- Full backtest engine with comprehensive metrics
- All paper-required performance measures (Sharpe, Sortino, Calmar, VaR, CVaR, etc.)
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Research paper configuration defaults (overridden by Config when available)
RISK_FREE_RATE = 0.04
MAX_SECTOR_WEIGHT = 0.20
TRANSACTION_COST_BPS = 10
CAUSAL_BLEND_RATIO = 0.30  # Weight on the causal-adjusted signal vs. traditional returns

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
        import pandas as pd
        from app.services.price_store import get_price_store

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
            prices = get_price_store().get_history(
                symbols,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
            )
            if prices.empty:
                return {**_get_empty_performance(),
                        'error': 'Market data unavailable for portfolio assets'}

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

            # Sharpe ratio: annualize the (cumulative, non-annualized) total
            # return to match the already-annualized volatility, and net out
            # the risk-free rate - matching the convention used in
            # compute_full_metrics elsewhere in this file.
            days_elapsed = len(portfolio_returns)
            annualized_return = (1 + total_return / 100) ** (252 / days_elapsed) - 1 if days_elapsed > 0 else 0
            excess_return = annualized_return - RISK_FREE_RATE
            sharpe_ratio = excess_return / (volatility / 100) if volatility > 0 else 0
            
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
            return {**_get_empty_performance(),
                    'error': f'Market data unavailable: {e}'}

    except ImportError:
        return {**_get_empty_performance(), 'error': 'Data dependencies unavailable'}


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

        # Some assets may have been dropped for lack of data
        assets = returns_data['assets']
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
    """Fetch and calculate asset returns from the local price store."""
    try:
        from app.services.price_store import get_price_store

        period_days = {'6mo': 182, '1y': 365, '2y': 730, '5y': 1825}
        days = period_days.get(period, 365)
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        prices = get_price_store().get_history(assets, start=start)
        if prices.empty:
            return None
        # Preserve requested asset order; drop assets with no data
        cols = [a for a in assets if a in prices.columns]
        returns = prices[cols].pct_change().dropna()
        if returns.empty:
            return None

        return {
            'mean_returns': returns.mean().values * 252,  # Annualized
            'cov_matrix': returns.cov().values * 252,  # Annualized
            'assets': cols
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
        
        def neg_sharpe(weights, risk_free_rate=RISK_FREE_RATE):
            ret = portfolio_return(weights)
            vol = portfolio_volatility(weights)
            return -(ret - risk_free_rate) / vol if vol > 0 else 0
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        # Bounds: long-only with per-asset cap (default 20%)
        bounds = tuple((0, MAX_SECTOR_WEIGHT) for _ in range(n_assets))
        
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
    causal_model_id: Optional[int],
    as_of_date: Optional[str] = None
) -> tuple:
    """
    Optimize portfolio with causal adjustments to expected returns.
    Uses ML-trained sensitivity matrix when available.

    Args:
        as_of_date: If given, use market indicators as of this historical
            date (for backtesting) instead of a live quote, so a fold under
            test can't see market conditions that hadn't happened yet.
    """
    from app.services.causal_service import get_active_sensitivity_matrix
    from app.services.market_service import get_current_indicators, get_indicators_as_of

    active_matrix = get_active_sensitivity_matrix()

    # Fetch market indicators for causal adjustment: point-in-time for a
    # backtest fold, live for real-time/production use.
    try:
        indicators = get_indicators_as_of(as_of_date) if as_of_date else get_current_indicators()
        # Derive directional economic forecasts from current levels
        # Fed rate direction: above 4% → tightening (+), below → easing (-)
        fed_rate = indicators.get('treasury_10y', {}).get('value', 4.5)
        rate_forecast = (fed_rate - 4.0) / 100  # Normalize to impact scale
        
        # VIX direction: above 20 → risk-off, below → risk-on
        vix = indicators.get('vix', {}).get('value', 18.0)
        inflation_proxy = (vix - 18.0) / 1000  # Higher VIX correlates with inflation fears
        
        # S&P 500 trend as GDP growth proxy
        sp500_change = indicators.get('sp500', {}).get('change', 0)
        gdp_proxy = sp500_change / 100  # Market momentum as growth indicator
        
        economic_forecast = {
            'interest_rates': round(rate_forecast, 4),
            'inflation': round(inflation_proxy, 4),
            'gdp_growth': round(gdp_proxy, 4)
        }
        logger.info(f"Causal optimizer using live indicators: {economic_forecast}")
    except Exception as e:
        logger.warning(f"Failed to fetch live indicators, using defaults: {e}")
        economic_forecast = {
            'interest_rates': 0.005,
            'inflation': -0.002,
            'gdp_growth': 0.003
        }
    
    # Adjust expected returns based on causal relationships
    adjusted_returns = mean_returns.copy()
    adjustments = []
    
    for i, asset in enumerate(assets):
        sector_info = SECTOR_ETFS.get(asset, {})
        sector_key = sector_info.get('sector', '')
        
        if sector_key in active_matrix:
            sensitivity = active_matrix[sector_key]
            
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
    
    # Blend the causal-adjusted returns with the unadjusted traditional
    # returns per CAUSAL_BLEND_RATIO, rather than feeding the fully-adjusted
    # vector straight into the optimizer. `adjusted_returns` above already
    # equals traditional + causal_delta, so blending it against the raw
    # `mean_returns` is equivalent to scaling the causal delta itself by
    # CAUSAL_BLEND_RATIO: blended = mean + CAUSAL_BLEND_RATIO * causal_delta.
    blended_returns = (
        CAUSAL_BLEND_RATIO * adjusted_returns
        + (1 - CAUSAL_BLEND_RATIO) * mean_returns
    )

    causal_weights = _optimize_markowitz(blended_returns, cov_matrix, objective)

    return causal_weights, adjustments


def _calculate_metrics(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = RISK_FREE_RATE
) -> Dict[str, float]:
    """
    Calculate portfolio metrics from weights, expected returns, and covariance matrix.
    
    Computes parametric estimates when only summary statistics are available.
    For historical-data-based metrics (Sortino, VaR, CVaR, etc.), 
    see compute_full_metrics() which uses actual return series.
    """
    portfolio_return = float(np.dot(weights, mean_returns))
    portfolio_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))
    excess = portfolio_return - risk_free_rate
    sharpe = excess / portfolio_vol if portfolio_vol > 0 else 0
    
    # Parametric Sortino approximation (assumes normal distribution)
    daily_vol = portfolio_vol / np.sqrt(252)
    daily_rf = risk_free_rate / 252
    daily_mean = portfolio_return / 252
    # Downside deviation for normal distribution
    downside_vol_daily = daily_vol * np.sqrt(0.5)  # E[min(r - rf, 0)^2] for symmetric
    downside_vol = downside_vol_daily * np.sqrt(252)
    sortino = excess / downside_vol if downside_vol > 0 else 0
    
    # Parametric expected max drawdown (Magdon-Ismail et al., 2004)
    if portfolio_vol > 0:
        base_mdd = portfolio_vol * np.sqrt(np.pi / 2)
        excess_return_adj = max(0, excess)
        drift_reduction = excess_return_adj * 0.5
        expected_mdd = max(base_mdd - drift_reduction, portfolio_vol * 0.5)
        max_drawdown = round(-expected_mdd * 100, 2)
    else:
        max_drawdown = 0.0
    
    # Calmar ratio
    calmar = excess / abs(max_drawdown / 100) if max_drawdown < 0 else 0
    
    # Parametric VaR (95%) - daily
    var_95_daily = -(daily_mean - 1.645 * daily_vol)
    # Parametric CVaR (95%) - daily using normal distribution
    cvar_95_daily = -(daily_mean - daily_vol * (stats_norm_pdf(1.645) / 0.05))
    
    return {
        'expected_return': round(portfolio_return * 100, 2),
        'volatility': round(portfolio_vol * 100, 2),
        'sharpe_ratio': round(sharpe, 4),
        'sortino_ratio': round(sortino, 4),
        'max_drawdown': max_drawdown,
        'calmar_ratio': round(calmar, 4),
        'var_95_daily': round(var_95_daily * 100, 4),
        'cvar_95_daily': round(cvar_95_daily * 100, 4),
    }


def stats_norm_pdf(x: float) -> float:
    """Standard normal PDF at x (avoids importing scipy for simple case)."""
    return (1.0 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * x * x)


def compute_full_metrics(
    portfolio_returns: np.ndarray,
    benchmark_returns: Optional[np.ndarray] = None,
    risk_free_rate: float = RISK_FREE_RATE,
    weights_history: Optional[List[Dict[str, float]]] = None
) -> Dict[str, float]:
    """
    Compute all paper-required portfolio metrics from actual return series.
    
    Args:
        portfolio_returns: Array of daily portfolio returns
        benchmark_returns: Array of daily benchmark returns (for Information Ratio, Treynor)
        risk_free_rate: Annual risk-free rate
        weights_history: List of weight dicts over time (for Turnover calculation)
    
    Returns:
        Dictionary with all comprehensive metrics
    """
    returns = np.asarray(portfolio_returns)
    n_days = len(returns)
    rf_daily = risk_free_rate / 252
    
    # Annualized return
    cumulative = np.prod(1 + returns)
    ann_return = cumulative ** (252 / n_days) - 1 if n_days > 0 else 0
    
    # Annualized volatility
    ann_vol = np.std(returns, ddof=1) * np.sqrt(252) if n_days > 1 else 0
    
    # Excess return
    excess = ann_return - risk_free_rate
    
    # Sharpe Ratio
    sharpe = excess / ann_vol if ann_vol > 0 else 0
    
    # Sortino Ratio
    downside_returns = returns[returns < rf_daily] - rf_daily
    if len(downside_returns) > 0:
        downside_vol = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(252)
    else:
        downside_vol = 0.0
    sortino = excess / downside_vol if downside_vol > 0 else 0
    
    # Max Drawdown (actual, not parametric)
    cumulative_curve = np.cumprod(1 + returns)
    rolling_max = np.maximum.accumulate(cumulative_curve)
    drawdowns = cumulative_curve / rolling_max - 1
    max_dd = float(np.min(drawdowns))
    
    # Calmar Ratio
    calmar = ann_return / abs(max_dd) if max_dd < 0 else 0
    
    # VaR (95%) - Historical
    var_95 = float(np.percentile(returns, 5))
    
    # CVaR (95%) - Expected Shortfall
    cvar_95 = float(np.mean(returns[returns <= var_95])) if np.any(returns <= var_95) else var_95
    
    # Hit Rate (% positive days)
    hit_rate_daily = float(np.mean(returns > 0))
    
    # Monthly hit rate
    if n_days >= 21:
        # Approximate monthly returns by grouping every 21 days
        n_months = n_days // 21
        monthly_returns = np.array([
            np.prod(1 + returns[i*21:(i+1)*21]) - 1
            for i in range(n_months)
        ])
        hit_rate_monthly = float(np.mean(monthly_returns > 0)) if len(monthly_returns) > 0 else 0
    else:
        monthly_returns = returns
        hit_rate_monthly = hit_rate_daily
    
    # Turnover (average monthly weight change)
    turnover = 0.0
    if weights_history and len(weights_history) > 1:
        turnovers = []
        for t in range(1, len(weights_history)):
            all_assets = set(weights_history[t].keys()) | set(weights_history[t-1].keys())
            turn = sum(abs(weights_history[t].get(a, 0) - weights_history[t-1].get(a, 0))
                      for a in all_assets) / 2  # Half-turn
            turnovers.append(turn)
        turnover = float(np.mean(turnovers))
    
    result = {
        'annualized_return': round(ann_return * 100, 4),
        'annualized_volatility': round(ann_vol * 100, 4),
        'sharpe_ratio': round(sharpe, 4),
        'sortino_ratio': round(sortino, 4),
        'max_drawdown': round(max_dd * 100, 4),
        'calmar_ratio': round(calmar, 4),
        'var_95_daily': round(var_95 * 100, 4),
        'cvar_95_daily': round(cvar_95 * 100, 4),
        'hit_rate_daily': round(hit_rate_daily * 100, 2),
        'hit_rate_monthly': round(hit_rate_monthly * 100, 2),
        'turnover_monthly': round(turnover * 100, 4),
        'total_return': round((cumulative - 1) * 100, 4),
    }
    
    # Information Ratio and Treynor (require benchmark)
    if benchmark_returns is not None:
        bench = np.asarray(benchmark_returns)
        min_len = min(len(returns), len(bench))
        r, b = returns[:min_len], bench[:min_len]
        
        # Information Ratio = (annualized excess return vs benchmark) / tracking error
        excess_vs_bench = r - b
        tracking_error = np.std(excess_vs_bench, ddof=1) * np.sqrt(252)
        ann_excess_vs_bench = np.mean(excess_vs_bench) * 252
        info_ratio = ann_excess_vs_bench / tracking_error if tracking_error > 0 else 0
        result['information_ratio'] = round(info_ratio, 4)
        
        # Treynor Ratio = excess return / beta
        if np.var(b) > 0:
            beta = np.cov(r, b)[0, 1] / np.var(b)
            treynor = excess / beta if beta != 0 else 0
            result['treynor_ratio'] = round(treynor, 4)
            result['beta'] = round(float(beta), 4)
        else:
            result['treynor_ratio'] = 0.0
            result['beta'] = 0.0
    
    return result


def _get_default_optimization(
    assets: List[str],
    objective: str,
    use_causal: bool
) -> Dict[str, Any]:
    """Return default optimization when real data unavailable.
    
    NOTE: This fallback should NEVER be used for paper results.
    It returns equal weights with zero-valued metrics to clearly 
    indicate that real data was not available.
    """
    n = len(assets)
    equal_weights = {asset: round(1/n, 4) for asset in assets}
    
    empty_metrics = {
        'expected_return': 0.0,
        'volatility': 0.0,
        'sharpe_ratio': 0.0,
        'sortino_ratio': 0.0,
        'max_drawdown': 0.0,
        'calmar_ratio': 0.0,
        'var_95_daily': 0.0,
        'cvar_95_daily': 0.0,
    }
    
    return {
        'traditional': {
            'weights': equal_weights,
            'metrics': empty_metrics
        },
        'causal': {
            'weights': equal_weights,
            'metrics': empty_metrics,
            'adjustments': []
        },
        'improvement': {
            'return': 0.0,
            'volatility': 0.0,
            'sharpe': 0.0
        },
        'warning': 'FALLBACK: Real market data unavailable. These are placeholder results.'
    }


def run_backtest(
    weights: Dict[str, float],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    benchmark_ticker: str = 'SPY',
    transaction_cost_bps: float = TRANSACTION_COST_BPS
) -> Dict[str, Any]:
    """
    Run historical backtest on portfolio weights with comprehensive metrics.
    
    Args:
        weights: Dict mapping ticker symbols to portfolio weights
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)
        benchmark_ticker: Benchmark ticker for relative metrics
        transaction_cost_bps: Transaction costs in basis points
        
    Returns:
        Dictionary with all performance metrics, time series, and diagnostics
    """
    try:
        from app.services.price_store import get_price_store

        if not weights:
            return {'error': 'No weights provided'}

        # Default dates
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        symbols = list(weights.keys())
        all_tickers = symbols.copy()
        if benchmark_ticker not in all_tickers:
            all_tickers.append(benchmark_ticker)

        prices = get_price_store().get_history(all_tickers, start=start_date, end=end_date)

        if prices.empty:
            return {'error': 'Market data unavailable for backtest',
                    'start_date': start_date, 'end_date': end_date}
        
        # Separate benchmark
        benchmark_returns = None
        if benchmark_ticker in prices.columns:
            benchmark_returns = prices[benchmark_ticker].pct_change().dropna().values
        
        # Portfolio returns
        portfolio_prices = prices[[s for s in symbols if s in prices.columns]]
        returns = portfolio_prices.pct_change().dropna()
        
        weight_array = np.array([weights.get(s, 0) for s in returns.columns])
        # Normalize weights if they don't sum to 1
        if np.sum(weight_array) > 0:
            weight_array = weight_array / np.sum(weight_array)
        
        portfolio_returns_series = returns.dot(weight_array)
        
        # Apply transaction costs (initial buy)
        if transaction_cost_bps > 0:
            initial_cost = transaction_cost_bps / 10000.0
            portfolio_returns_series.iloc[0] -= initial_cost
        
        # Align benchmark to same dates
        if benchmark_returns is not None:
            bench_aligned = prices[benchmark_ticker].pct_change().dropna()
            common_idx = portfolio_returns_series.index.intersection(bench_aligned.index)
            portfolio_returns_series = portfolio_returns_series.loc[common_idx]
            benchmark_returns = bench_aligned.loc[common_idx].values
        
        portfolio_returns_arr = portfolio_returns_series.values
        
        # Compute full metrics
        metrics = compute_full_metrics(
            portfolio_returns_arr,
            benchmark_returns=benchmark_returns,
            risk_free_rate=RISK_FREE_RATE
        )
        
        # Cumulative returns for time series
        cumulative = np.cumprod(1 + portfolio_returns_arr)
        
        # Build time series
        dates = portfolio_returns_series.index
        time_series = [
            {'date': date.strftime('%Y-%m-%d'), 'value': round(float(val), 4)}
            for date, val in zip(dates, cumulative)
        ]
        
        # Drawdown time series
        rolling_max = np.maximum.accumulate(cumulative)
        drawdown_series = cumulative / rolling_max - 1
        drawdown_ts = [
            {'date': date.strftime('%Y-%m-%d'), 'drawdown': round(float(dd) * 100, 4)}
            for date, dd in zip(dates, drawdown_series)
        ]
        
        # Benchmark cumulative for comparison
        benchmark_ts = []
        if benchmark_returns is not None:
            bench_cumulative = np.cumprod(1 + benchmark_returns)
            benchmark_ts = [
                {'date': date.strftime('%Y-%m-%d'), 'value': round(float(val), 4)}
                for date, val in zip(dates, bench_cumulative)
            ]
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'weights': weights,
            **metrics,
            'time_series': time_series[::max(1, len(time_series)//100)],
            'drawdown_series': drawdown_ts[::max(1, len(drawdown_ts)//100)],
            'benchmark_series': benchmark_ts[::max(1, len(benchmark_ts)//100)],
            'benchmark_ticker': benchmark_ticker,
            'transaction_cost_bps': transaction_cost_bps,
            'n_trading_days': len(portfolio_returns_arr),
            'daily_returns': portfolio_returns_arr.tolist(),  # For downstream statistical tests
        }
        
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return {'error': f'Backtest failed: {e}',
                'start_date': start_date, 'end_date': end_date}


def apply_transaction_costs(
    returns_series: np.ndarray,
    weights_history: List[Dict[str, float]],
    cost_bps: float,
    rebalance_indices: Optional[List[int]] = None
) -> np.ndarray:
    """
    Apply round-trip transaction costs in basis points at each rebalance.

    Args:
        returns_series: Array of daily portfolio returns
        weights_history: List of weight dicts at each rebalance point,
            weights_history[0] is the initial entry (compared against an
            empty/all-cash portfolio, so it still carries an entry cost)
        cost_bps: Transaction cost in basis points (e.g., 10 = 10bps)
        rebalance_indices: Index into returns_series where each entry in
            weights_history takes effect. If omitted, assumes monthly
            rebalancing (21 trading days apart) for backward compatibility.

    Returns:
        Adjusted return series with costs subtracted
    """
    adjusted = returns_series.copy()
    cost_per_trade = cost_bps / 10000.0

    if not weights_history:
        return adjusted

    prev_weights: Dict[str, float] = {}
    for t, weights in enumerate(weights_history):
        all_assets = set(weights.keys()) | set(prev_weights.keys())
        turnover = sum(abs(weights.get(s, 0) - prev_weights.get(s, 0)) for s in all_assets)
        cost = 0.5 * turnover * cost_per_trade  # Half-turn cost

        if rebalance_indices is not None:
            if t >= len(rebalance_indices):
                break
            idx = rebalance_indices[t]
        else:
            idx = min(t * 21, len(adjusted) - 1)

        if 0 <= idx < len(adjusted):
            adjusted[idx] -= cost
        prev_weights = weights

    return adjusted


def run_walk_forward_backtest(
    assets: List[str],
    train_window: int = 252 * 3,
    test_window: int = 63,
    n_folds: int = 20,
    use_causal: bool = True,
    start_date: str = '2010-01-01',
    end_date: str = '2024-01-01',
    first_test_start: Optional[str] = None,
    transaction_cost_bps: float = TRANSACTION_COST_BPS,
    weight_fn: Optional[Callable[[pd.DataFrame, str, List[str]], np.ndarray]] = None
) -> Dict[str, Any]:
    """
    Run walk-forward (rolling window) cross-validation backtest. This is the
    leak-free alternative to a single optimize-then-backtest pass: every
    fold's weights are chosen using only data available before that fold's
    test window begins.

    Each fold:
    1. Train on train_window days ending at some historical cutoff
    2. Optimize weights (causal adjustment, if used, sees only market
       indicators as of that cutoff - not live/current data)
    3. Test on the following, unseen test_window days
    4. Roll forward by test_window days and repeat

    Args:
        assets: List of ticker symbols
        train_window: Training window size in trading days
        test_window: Testing window size in trading days
        n_folds: Maximum number of rolling folds (actual count is capped by
            available data through end_date - this just needs to be large
            enough not to be the limiting factor)
        use_causal: Whether to use causal optimization (ignored if weight_fn
            is given)
        start_date: Earliest date to pull price history from
        end_date: Overall end date
        first_test_start: If given, anchor fold 0's test window to start at
            this date (e.g. the paper's declared out-of-sample start) rather
            than immediately after `train_window` days from `start_date`.
        transaction_cost_bps: Round-trip cost charged at each rebalance,
            based on turnover between consecutive folds' weights.
        weight_fn: Optional custom weight-computation strategy, called once
            per fold as weight_fn(train_returns, as_of_date, columns) ->
            weight array aligned to `columns`. Lets callers (e.g. ablation
            studies) swap in a different weighting approach while still
            getting point-in-time-correct, leak-free folds for free. When
            omitted, falls back to the standard Markowitz/causal path.

    Returns:
        Dictionary with per-fold and aggregate results
    """
    try:
        from app.services.price_store import get_price_store

        prices = get_price_store().get_history(
            assets + ['SPY'], start=start_date, end=end_date)
        if prices.empty:
            return {'error': 'Could not fetch data for walk-forward backtest'}

        returns = prices.pct_change().dropna()
        n_total = len(returns)

        if first_test_start:
            target_idx = int(returns.index.searchsorted(pd.Timestamp(first_test_start)))
            fold0_train_start = max(0, target_idx - train_window)
        else:
            fold0_train_start = 0

        fold_results = []
        all_oos_returns: List[float] = []
        all_bench_returns: List[float] = []
        weights_history: List[Dict[str, float]] = []
        fold_start_positions: List[int] = []

        for fold in range(n_folds):
            train_start = fold0_train_start + fold * test_window
            train_end = train_start + train_window
            test_end = train_end + test_window

            if test_end > n_total:
                break

            # Training data - strictly precedes the test window
            train_returns = returns.iloc[train_start:train_end]
            test_returns = returns.iloc[train_end:test_end]
            as_of_date = returns.index[train_end - 1].strftime('%Y-%m-%d')

            if weight_fn is not None:
                weights_arr = weight_fn(train_returns, as_of_date, list(train_returns.columns))
            else:
                # Compute mean returns and covariance from training data only
                mean_ret = train_returns.mean().values * 252
                cov_mat = train_returns.cov().values * 252

                weights_arr = _optimize_markowitz(mean_ret, cov_mat, 'max_sharpe')

                if use_causal:
                    try:
                        weights_arr, _ = _optimize_with_causal(
                            mean_ret, cov_mat, 'max_sharpe',
                            list(train_returns.columns), None,
                            as_of_date=as_of_date
                        )
                    except Exception:
                        pass  # Fall back to Markowitz weights

            # Test on out-of-sample data
            portfolio_cols = [c for c in test_returns.columns if c in assets]
            test_asset_returns = test_returns[portfolio_cols]
            weight_vec = np.array([weights_arr[list(returns.columns).index(c)]
                                   for c in portfolio_cols if c in returns.columns])
            if np.sum(weight_vec) > 0:
                weight_vec = weight_vec / np.sum(weight_vec)

            oos_returns = test_asset_returns.dot(weight_vec).values

            weights_history.append(dict(zip(portfolio_cols, weight_vec.tolist())))
            fold_start_positions.append(len(all_oos_returns))
            all_oos_returns.extend(oos_returns.tolist())
            if 'SPY' in test_returns.columns:
                all_bench_returns.extend(test_returns['SPY'].values.tolist())

            fold_results.append({
                'fold': fold + 1,
                'train_start': returns.index[train_start].strftime('%Y-%m-%d'),
                'train_end': returns.index[train_end - 1].strftime('%Y-%m-%d'),
                'test_start': returns.index[train_end].strftime('%Y-%m-%d'),
                'test_end': returns.index[min(test_end - 1, n_total - 1)].strftime('%Y-%m-%d'),
                '_n_test_days': len(oos_returns),
            })

        if not all_oos_returns:
            return {'error': 'No folds fit in the requested date range'}

        # Apply turnover-based transaction costs at each fold's rebalance point
        cost_adjusted_returns = apply_transaction_costs(
            np.array(all_oos_returns), weights_history,
            transaction_cost_bps, rebalance_indices=fold_start_positions
        )

        bench_arr = np.array(all_bench_returns) if len(all_bench_returns) == len(cost_adjusted_returns) else None

        # Recompute each fold's metrics on its cost-adjusted slice
        for i, fold_metrics in enumerate(fold_results):
            start_pos = fold_start_positions[i]
            end_pos = fold_start_positions[i + 1] if i + 1 < len(fold_start_positions) else len(cost_adjusted_returns)
            fold_slice = cost_adjusted_returns[start_pos:end_pos]
            fold_bench = bench_arr[start_pos:end_pos] if bench_arr is not None else None
            fold_metrics.pop('_n_test_days')
            computed = compute_full_metrics(fold_slice, benchmark_returns=fold_bench, risk_free_rate=RISK_FREE_RATE)
            fold_metrics.update(computed)

        aggregate_metrics = compute_full_metrics(
            cost_adjusted_returns, benchmark_returns=bench_arr,
            risk_free_rate=RISK_FREE_RATE, weights_history=weights_history
        )

        return {
            'n_folds': len(fold_results),
            'train_window_days': train_window,
            'test_window_days': test_window,
            'transaction_cost_bps': transaction_cost_bps,
            'fold_results': fold_results,
            'aggregate': aggregate_metrics,
            'daily_returns': cost_adjusted_returns.tolist(),
        }

    except Exception as e:
        logger.error(f"Walk-forward backtest error: {e}")
        return {'error': str(e)}


def run_single_period_backtest(
    assets: List[str],
    test_start: str,
    test_end: str,
    train_window: int = 252 * 3,
    min_train_window: int = 126,
    use_causal: bool = True,
    transaction_cost_bps: float = TRANSACTION_COST_BPS,
    weight_fn: Optional[Callable[[pd.DataFrame, str, List[str]], np.ndarray]] = None
) -> Dict[str, Any]:
    """
    One train/test split, anchored at an arbitrary historical test_start:
    train on the `train_window` trading days immediately preceding
    test_start, then test on [test_start, test_end]. This is
    run_walk_forward_backtest with a single fold - for checks that need a
    specific historical boundary (a named sub-period, a shifted split date)
    rather than a rolling series of folds, while keeping the same
    point-in-time guarantee: weights are chosen using only data available
    before test_start, never data from the test window itself.

    Args:
        assets: List of ticker symbols
        test_start: Start of the out-of-sample test window
        test_end: End of the out-of-sample test window
        train_window: Training window size in trading days, ending the
            trading day before test_start
        min_train_window: Minimum trading days of prior history required to
            proceed. If less than train_window is actually available before
            test_start (e.g. a sub-period starting shortly after the asset
            universe's youngest member began trading), uses whatever's
            available rather than requiring the full window - a real
            investor at that point wouldn't have had more history either.
            Errors only if even this minimum isn't available.
        use_causal: Whether to use causal optimization (ignored if
            weight_fn is given)
        transaction_cost_bps: Round-trip cost charged for the single entry
            into this position
        weight_fn: Optional custom weight-computation strategy, see
            run_walk_forward_backtest for the calling convention

    Returns:
        Dictionary with metrics, weights, and the realized train/test dates
    """
    try:
        from app.services.price_store import get_price_store

        prices = get_price_store().get_history(assets + ['SPY'], end=test_end)
        if prices.empty:
            return {'error': 'Could not fetch data for single-period backtest'}

        returns = prices.pct_change().dropna()
        n_total = len(returns)

        test_start_idx = int(returns.index.searchsorted(pd.Timestamp(test_start)))
        train_start_idx = max(0, test_start_idx - train_window)
        test_end_idx = int(returns.index.searchsorted(pd.Timestamp(test_end), side='right'))
        test_end_idx = min(test_end_idx, n_total)

        available_train_days = test_start_idx - train_start_idx
        if available_train_days < min_train_window or test_start_idx >= test_end_idx:
            return {'error': f'Insufficient data: only {max(available_train_days, 0)} trading '
                              f'days available before test_start={test_start} '
                              f'(need at least {min_train_window})'}

        train_returns = returns.iloc[train_start_idx:test_start_idx]
        test_returns = returns.iloc[test_start_idx:test_end_idx]
        as_of_date = returns.index[test_start_idx - 1].strftime('%Y-%m-%d')

        if weight_fn is not None:
            weights_arr = weight_fn(train_returns, as_of_date, list(train_returns.columns))
        else:
            mean_ret = train_returns.mean().values * 252
            cov_mat = train_returns.cov().values * 252

            weights_arr = _optimize_markowitz(mean_ret, cov_mat, 'max_sharpe')

            if use_causal:
                try:
                    weights_arr, _ = _optimize_with_causal(
                        mean_ret, cov_mat, 'max_sharpe',
                        list(train_returns.columns), None,
                        as_of_date=as_of_date
                    )
                except Exception:
                    pass

        portfolio_cols = [c for c in test_returns.columns if c in assets]
        test_asset_returns = test_returns[portfolio_cols]
        weight_vec = np.array([weights_arr[list(returns.columns).index(c)]
                               for c in portfolio_cols if c in returns.columns])
        if np.sum(weight_vec) > 0:
            weight_vec = weight_vec / np.sum(weight_vec)

        oos_returns = test_asset_returns.dot(weight_vec).values
        weight_dict = dict(zip(portfolio_cols, weight_vec.tolist()))

        cost_adjusted = apply_transaction_costs(
            oos_returns, [weight_dict], transaction_cost_bps, rebalance_indices=[0]
        )

        bench_returns = test_returns['SPY'].values if 'SPY' in test_returns.columns else None
        metrics = compute_full_metrics(
            cost_adjusted, benchmark_returns=bench_returns, risk_free_rate=RISK_FREE_RATE
        )

        return {
            **metrics,
            'weights': {k: round(v, 4) for k, v in weight_dict.items()},
            'train_start': returns.index[train_start_idx].strftime('%Y-%m-%d'),
            'train_end': as_of_date,
            'test_start': returns.index[test_start_idx].strftime('%Y-%m-%d'),
            'test_end': returns.index[test_end_idx - 1].strftime('%Y-%m-%d'),
            'transaction_cost_bps': transaction_cost_bps,
            'daily_returns': cost_adjusted.tolist(),
        }

    except Exception as e:
        logger.error(f"Single-period backtest error: {e}")
        return {'error': str(e)}
