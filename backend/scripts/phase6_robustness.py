"""
Phase 6 -- Robustness Checks
============================
Validates that results hold across different conditions:
1. Sub-period analysis (Pre-COVID, COVID, Post-COVID)
2. Asset universe robustness (full vs. large-cap)
3. Transaction cost sensitivity (0, 10, 30, 50 bps)
4. Train/test split sensitivity (?6 months)

Usage:
    from scripts.phase6_robustness import run_robustness
    results = run_robustness()
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)


def sub_period_analysis(
    weights: Dict[str, float],
    sub_periods: Optional[Dict[str, tuple]] = None
) -> pd.DataFrame:
    """
    Run backtest across different time sub-periods.
    
    Args:
        weights: Portfolio weights dict
        sub_periods: Dict mapping period name to (start_date, end_date) tuple
    
    Returns:
        DataFrame with per-period metrics
    """
    from app.services.portfolio_service import run_backtest
    
    if sub_periods is None:
        sub_periods = {
            'Pre-COVID': ('2018-01-01', '2019-12-31'),
            'COVID Crash': ('2020-01-01', '2020-12-31'),
            'Post-COVID': ('2021-01-01', '2023-12-31'),
        }
    
    rows = []
    for period_name, (start, end) in sub_periods.items():
        logger.info(f"Running sub-period backtest: {period_name} ({start} to {end})")
        result = run_backtest(weights, start, end)
        
        row = {
            'Period': period_name,
            'Start': start,
            'End': end,
        }
        
        for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio',
                     'max_drawdown', 'calmar_ratio', 'var_95_daily', 'cvar_95_daily']:
            row[key] = result.get(key, None)
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def asset_universe_robustness(
    start_date: str = '2021-05-01',
    end_date: str = '2024-01-01'
) -> pd.DataFrame:
    """
    Test with different asset universes.
    
    Universe 1: Large-cap dominated (5 sectors)
    Universe 2: Full 11-sector
    """
    from app.services.portfolio_service import optimize_portfolio_weights, run_backtest
    
    universes = {
        'Large-Cap (5 sectors)': ['XLK', 'XLV', 'XLF', 'XLI', 'XLY'],
        'Full Universe (11 sectors)': ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY',
                                        'XLP', 'XLU', 'XLB', 'XLRE', 'XLC'],
    }
    
    rows = []
    for uni_name, assets in universes.items():
        logger.info(f"Optimizing for universe: {uni_name}")
        
        opt = optimize_portfolio_weights(assets, 'max_sharpe', use_causal=True)
        weights = opt.get('causal', {}).get('weights', {})
        
        if not weights:
            logger.warning(f"No weights for universe {uni_name}")
            continue
        
        result = run_backtest(weights, start_date, end_date)
        
        row = {'Universe': uni_name, 'N_Assets': len(assets)}
        for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio',
                     'max_drawdown', 'calmar_ratio']:
            row[key] = result.get(key, None)
        rows.append(row)
    
    return pd.DataFrame(rows)


def transaction_cost_sensitivity(
    weights: Dict[str, float],
    start_date: str = '2021-05-01',
    end_date: str = '2024-01-01',
    cost_levels_bps: List[float] = None
) -> pd.DataFrame:
    """
    Test Sharpe ratio degradation at different transaction cost levels.
    
    Args:
        weights: Portfolio weights
        start_date: Backtest start
        end_date: Backtest end
        cost_levels_bps: List of cost levels in basis points
    """
    from app.services.portfolio_service import run_backtest
    
    if cost_levels_bps is None:
        cost_levels_bps = [0, 10, 30, 50]
    
    rows = []
    for bps in cost_levels_bps:
        logger.info(f"Running backtest with transaction cost = {bps} bps")
        result = run_backtest(weights, start_date, end_date, transaction_cost_bps=bps)
        
        row = {
            'Transaction_Cost_BPS': bps,
            'annualized_return': result.get('annualized_return'),
            'sharpe_ratio': result.get('sharpe_ratio'),
            'sortino_ratio': result.get('sortino_ratio'),
            'max_drawdown': result.get('max_drawdown'),
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


def split_sensitivity(
    assets: List[str] = None,
    base_split: str = '2021-05-01',
    shift_months: int = 6
) -> pd.DataFrame:
    """
    Test sensitivity to train/test split date ?shift_months.
    
    For each split, re-optimize and re-backtest.
    """
    from app.services.portfolio_service import optimize_portfolio_weights, run_backtest
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    if assets is None:
        assets = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
    
    base_date = datetime.strptime(base_split, '%Y-%m-%d')
    
    splits = {
        f'Early (-{shift_months}m)': (base_date - relativedelta(months=shift_months)).strftime('%Y-%m-%d'),
        'Baseline': base_split,
        f'Late (+{shift_months}m)': (base_date + relativedelta(months=shift_months)).strftime('%Y-%m-%d'),
    }
    
    rows = []
    for split_name, test_start in splits.items():
        logger.info(f"Testing split: {split_name} (test starts {test_start})")
        
        # re-optimize
        opt = optimize_portfolio_weights(assets, 'max_sharpe', use_causal=True)
        weights = opt.get('causal', {}).get('weights', {})
        
        if not weights:
            continue
        
        # Backtest from split date to end
        result = run_backtest(weights, test_start, '2024-01-01')
        
        row = {
            'Split': split_name,
            'Test_Start': test_start,
        }
        for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown']:
            row[key] = result.get(key, None)
        rows.append(row)
    
    return pd.DataFrame(rows)


def run_robustness(
    weights: Optional[Dict[str, float]] = None,
    assets: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Run all Phase 6 robustness checks.
    
    Args:
        weights: Causal portfolio weights (if None, will optimize fresh)
        assets: Asset universe
    
    Returns:
        Dictionary of DataFrames for each robustness check
    """
    if assets is None:
        assets = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
    
    if weights is None:
        from app.services.portfolio_service import optimize_portfolio_weights
        opt = optimize_portfolio_weights(assets, 'max_sharpe', use_causal=True)
        weights = opt.get('causal', {}).get('weights', {})
    
    results = {}
    
    # 6.1 Sub-period analysis
    logger.info("=== 6.1 Sub-Period Analysis ===")
    results['sub_periods'] = sub_period_analysis(weights)
    
    # 6.2 Asset universe robustness
    logger.info("=== 6.2 Asset Universe Robustness ===")
    results['asset_universe'] = asset_universe_robustness()
    
    # 6.3 Transaction cost sensitivity
    logger.info("=== 6.3 Transaction Cost Sensitivity ===")
    results['transaction_costs'] = transaction_cost_sensitivity(weights)
    
    # 6.4 Split sensitivity
    logger.info("=== 6.4 Split Date Sensitivity ===")
    try:
        results['split_sensitivity'] = split_sensitivity(assets)
    except ImportError:
        logger.warning("dateutil not available, skipping split sensitivity")
        results['split_sensitivity'] = pd.DataFrame()
    
    return results
