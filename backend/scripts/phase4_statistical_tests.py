"""
Phase 4 -- Statistical Significance Testing
============================================
Implements all statistical tests required for the research paper:
1. Paired t-test (Causal vs each benchmark)
2. Mann-Whitney U test
3. Bootstrap confidence intervals for Sharpe Ratio (10,000 iterations)
4. Diebold-Mariano test (for forecast comparison)

Usage:
    from scripts.phase4_statistical_tests import run_statistical_tests
    results = run_statistical_tests(causal_returns, benchmark_returns_dict)
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.04
BOOTSTRAP_ITERATIONS = 10000


def paired_t_test(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    name_a: str = 'Causal',
    name_b: str = 'Benchmark'
) -> Dict[str, Any]:
    """
    Paired t-test comparing monthly returns of two portfolios.
    
    H0: mean(returns_a - returns_b) = 0
    H1: mean(returns_a - returns_b) != 0
    
    Args:
        returns_a: Monthly returns of portfolio A
        returns_b: Monthly returns of portfolio B
        name_a: Name of portfolio A
        name_b: Name of portfolio B
    
    Returns:
        Dictionary with test statistic, p-value, significance level
    """
    min_len = min(len(returns_a), len(returns_b))
    a, b = returns_a[:min_len], returns_b[:min_len]
    
    diff = a - b
    t_stat, p_value = stats.ttest_1samp(diff, 0)
    
    significance = _get_significance_label(p_value)
    
    return {
        'test': 'Paired t-test',
        'comparison': f'{name_a} vs {name_b}',
        't_statistic': round(float(t_stat), 4),
        'p_value': round(float(p_value), 6),
        'significance': significance,
        'mean_diff': round(float(np.mean(diff)), 6),
        'std_diff': round(float(np.std(diff, ddof=1)), 6),
        'n_observations': min_len,
    }


def mann_whitney_u_test(
    returns_a: np.ndarray,
    returns_b: np.ndarray,
    name_a: str = 'Causal',
    name_b: str = 'Benchmark',
    alternative: str = 'greater'
) -> Dict[str, Any]:
    """
    Mann-Whitney U test (non-parametric) comparing return distributions.
    
    H0: distributions are equal
    H1: returns_a > returns_b (if alternative='greater')
    
    Args:
        returns_a: Returns of portfolio A
        returns_b: Returns of portfolio B
        name_a: Name of portfolio A
        name_b: Name of portfolio B
        alternative: 'greater', 'less', or 'two-sided'
    
    Returns:
        Dictionary with test statistic, p-value, significance
    """
    u_stat, p_value = stats.mannwhitneyu(returns_a, returns_b, alternative=alternative)
    
    significance = _get_significance_label(p_value)
    
    return {
        'test': 'Mann-Whitney U',
        'comparison': f'{name_a} vs {name_b}',
        'u_statistic': round(float(u_stat), 4),
        'p_value': round(float(p_value), 6),
        'significance': significance,
        'alternative': alternative,
        'n_a': len(returns_a),
        'n_b': len(returns_b),
    }


def bootstrap_sharpe_ci(
    returns: np.ndarray,
    risk_free_rate: float = RISK_FREE_RATE,
    n_bootstrap: int = BOOTSTRAP_ITERATIONS,
    confidence_level: float = 0.95,
    name: str = 'Portfolio',
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Bootstrap confidence interval for Sharpe Ratio.
    
    Resamples monthly returns n_bootstrap times to construct 
    an empirical distribution of Sharpe estimates.
    
    Args:
        returns: Monthly return series
        risk_free_rate: Annual risk-free rate
        n_bootstrap: Number of bootstrap iterations
        confidence_level: Confidence level (default 95%)
        name: Portfolio name
        random_state: Random seed
    
    Returns:
        Dictionary with bootstrap Sharpe mean, CI, std
    """
    np.random.seed(random_state)
    
    rf_monthly = risk_free_rate / 12
    n = len(returns)
    
    sharpe_samples = np.zeros(n_bootstrap)
    
    for i in range(n_bootstrap):
        sample = np.random.choice(returns, size=n, replace=True)
        ann_ret = sample.mean() * 12
        ann_vol = sample.std(ddof=1) * np.sqrt(12)
        sharpe_samples[i] = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else 0
    
    alpha = 1 - confidence_level
    ci_lower = np.percentile(sharpe_samples, alpha / 2 * 100)
    ci_upper = np.percentile(sharpe_samples, (1 - alpha / 2) * 100)
    
    return {
        'test': 'Bootstrap Sharpe CI',
        'portfolio': name,
        'sharpe_mean': round(float(np.mean(sharpe_samples)), 4),
        'sharpe_median': round(float(np.median(sharpe_samples)), 4),
        'sharpe_std': round(float(np.std(sharpe_samples)), 4),
        'ci_lower': round(float(ci_lower), 4),
        'ci_upper': round(float(ci_upper), 4),
        'confidence_level': confidence_level,
        'n_bootstrap': n_bootstrap,
        'n_observations': n,
    }


def diebold_mariano_test(
    actual: np.ndarray,
    forecast_a: np.ndarray,
    forecast_b: np.ndarray,
    name_a: str = 'Causal Forecast',
    name_b: str = 'Naive Forecast',
    loss: str = 'MSE'
) -> Dict[str, Any]:
    """
    Diebold-Mariano test for comparing forecast accuracy.
    
    H0: forecasts have equal accuracy
    H1: forecast_a is more accurate than forecast_b
    
    Args:
        actual: Actual observed values
        forecast_a: Forecast from model A
        forecast_b: Forecast from model B
        name_a: Name of model A
        name_b: Name of model B
        loss: Loss function ('MSE' or 'MAE')
    
    Returns:
        Dictionary with DM statistic, p-value, significance
    """
    min_len = min(len(actual), len(forecast_a), len(forecast_b))
    y, fa, fb = actual[:min_len], forecast_a[:min_len], forecast_b[:min_len]
    
    e1 = y - fa  # Errors from model A
    e2 = y - fb  # Errors from model B
    
    if loss == 'MSE':
        d = e1**2 - e2**2
    elif loss == 'MAE':
        d = np.abs(e1) - np.abs(e2)
    else:
        d = e1**2 - e2**2
    
    n = len(d)
    mean_d = np.mean(d)
    std_d = np.std(d, ddof=1) / np.sqrt(n)
    
    dm_stat = mean_d / std_d if std_d > 0 else 0
    p_value = 2 * (1 - stats.norm.cdf(abs(dm_stat)))
    
    significance = _get_significance_label(p_value)
    
    return {
        'test': 'Diebold-Mariano',
        'comparison': f'{name_a} vs {name_b}',
        'dm_statistic': round(float(dm_stat), 4),
        'p_value': round(float(p_value), 6),
        'significance': significance,
        'mean_loss_diff': round(float(mean_d), 6),
        'loss_function': loss,
        'n_observations': n,
        'model_a_mse': round(float(np.mean(e1**2)), 6),
        'model_b_mse': round(float(np.mean(e2**2)), 6),
    }


def _get_significance_label(p_value: float) -> str:
    """Get significance label from p-value."""
    if p_value < 0.01:
        return '*** (1%)'
    elif p_value < 0.05:
        return '** (5%)'
    elif p_value < 0.10:
        return '* (10%)'
    else:
        return 'ns'


def daily_to_monthly(daily_returns: np.ndarray) -> np.ndarray:
    """Convert daily returns to monthly returns (approx 21 trading days)."""
    n = len(daily_returns)
    n_months = n // 21
    monthly = np.array([
        np.prod(1 + daily_returns[i*21:(i+1)*21]) - 1
        for i in range(n_months)
    ])
    return monthly


def run_statistical_tests(
    causal_daily_returns: np.ndarray,
    benchmark_daily_returns: Dict[str, np.ndarray],
    forecast_data: Optional[Dict[str, np.ndarray]] = None
) -> Dict[str, Any]:
    """
    Run all Phase 4 statistical significance tests.
    
    Args:
        causal_daily_returns: Daily returns of causal portfolio
        benchmark_daily_returns: Dict mapping benchmark names to daily return arrays
        forecast_data: Optional dict with 'actual', 'causal_forecast', 'naive_forecast'
    
    Returns:
        Dictionary with all test results organized by test type
    """
    results = {
        'paired_t_tests': [],
        'mann_whitney_tests': [],
        'bootstrap_sharpe': [],
        'diebold_mariano': None,
    }
    
    # Convert to monthly for parametric tests
    causal_monthly = daily_to_monthly(causal_daily_returns)
    
    for bench_name, bench_daily in benchmark_daily_returns.items():
        bench_monthly = daily_to_monthly(bench_daily)
        
        # Paired t-test
        t_result = paired_t_test(causal_monthly, bench_monthly, 'Causal', bench_name)
        results['paired_t_tests'].append(t_result)
        
        # Mann-Whitney U
        mw_result = mann_whitney_u_test(causal_monthly, bench_monthly, 'Causal', bench_name)
        results['mann_whitney_tests'].append(mw_result)
    
    # Bootstrap Sharpe CI for causal portfolio
    causal_sharpe = bootstrap_sharpe_ci(causal_monthly, name='Causal')
    results['bootstrap_sharpe'].append(causal_sharpe)
    
    # Bootstrap Sharpe CI for each benchmark
    for bench_name, bench_daily in benchmark_daily_returns.items():
        bench_monthly = daily_to_monthly(bench_daily)
        bench_sharpe = bootstrap_sharpe_ci(bench_monthly, name=bench_name)
        results['bootstrap_sharpe'].append(bench_sharpe)
    
    # Diebold-Mariano test (if forecast data available)
    if forecast_data is not None:
        actual = forecast_data.get('actual')
        causal_fc = forecast_data.get('causal_forecast')
        naive_fc = forecast_data.get('naive_forecast')
        
        if actual is not None and causal_fc is not None and naive_fc is not None:
            dm_result = diebold_mariano_test(actual, causal_fc, naive_fc)
            results['diebold_mariano'] = dm_result
    
    # Summary table
    summary_rows = []
    for t in results['paired_t_tests']:
        summary_rows.append({
            'Test': f"Paired t-test: {t['comparison']}",
            'Statistic': t['t_statistic'],
            'p-value': t['p_value'],
            'Significance': t['significance'],
        })
    for mw in results['mann_whitney_tests']:
        summary_rows.append({
            'Test': f"Mann-Whitney: {mw['comparison']}",
            'Statistic': mw['u_statistic'],
            'p-value': mw['p_value'],
            'Significance': mw['significance'],
        })
    for bs in results['bootstrap_sharpe']:
        summary_rows.append({
            'Test': f"Bootstrap Sharpe: {bs['portfolio']}",
            'Statistic': bs['sharpe_mean'],
            'p-value': f"[{bs['ci_lower']}, {bs['ci_upper']}]",
            'Significance': f"{bs['confidence_level']*100:.0f}% CI",
        })
    if results['diebold_mariano']:
        dm = results['diebold_mariano']
        summary_rows.append({
            'Test': f"DM Test: {dm['comparison']}",
            'Statistic': dm['dm_statistic'],
            'p-value': dm['p_value'],
            'Significance': dm['significance'],
        })
    
    results['summary_table'] = pd.DataFrame(summary_rows)
    
    return results
