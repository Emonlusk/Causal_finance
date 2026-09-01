"""
Phase 6 -- Robustness Checks
============================
Validates that results hold across different conditions:
1. Sub-period analysis (Pre-COVID, COVID, Post-COVID)
2. Asset universe robustness (full vs. large-cap)
3. Transaction cost sensitivity (0, 10, 30, 50 bps)
4. Train/test split sensitivity (+/-6 months)

Every check uses run_walk_forward_backtest from portfolio_service - the SAME
methodology as the headline Phase 3 number: a rolling 3-year training window,
re-optimized/rebalanced every 63 trading days, 10bps transaction costs
charged at each rebalance (see phase3_backtesting.py). No check here holds
one fixed allocation for years without rebalancing - that was a real bug
(sub_period_analysis and split_sensitivity used run_single_period_backtest,
a single train-then-hold-for-years split with zero rebalancing) that made
those two checks describe a different strategy than the headline number and
than each other's implied claims. Fixed so every phase6 output is
apples-to-apples with phase3/phase5.

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

DEFAULT_ASSETS = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
DEFAULT_TEST_START = '2021-05-01'
DEFAULT_TEST_END = '2024-01-01'


def sub_period_analysis(
    assets: Optional[List[str]] = None,
    sub_periods: Optional[Dict[str, tuple]] = None
) -> pd.DataFrame:
    """
    Walk-forward backtest (run_walk_forward_backtest - 3yr rolling train
    window, 63-day test folds, re-optimized/rebalanced every fold, 10bps
    transaction costs at each rebalance; identical methodology to
    phase3_backtesting.py's headline number) restricted to each named
    sub-period's date range via first_test_start/end_date, so each period's
    metrics describe the same walk-forward re-optimized strategy the
    headline number does - not a single fixed allocation held for the whole
    period.

    Args:
        assets: Asset universe
        sub_periods: Dict mapping period name to (start_date, end_date) tuple

    Returns:
        DataFrame with per-period metrics
    """
    from app.services.portfolio_service import run_walk_forward_backtest

    if assets is None:
        assets = DEFAULT_ASSETS
    if sub_periods is None:
        sub_periods = {
            'Pre-COVID': ('2018-01-01', '2019-12-31'),
            'COVID Crash': ('2020-01-01', '2020-12-31'),
            'Post-COVID': ('2021-01-01', '2023-12-31'),
        }

    rows = []
    for period_name, (start, end) in sub_periods.items():
        logger.info(f"Running sub-period backtest: {period_name} ({start} to {end})")
        result = run_walk_forward_backtest(assets, use_causal=True, first_test_start=start, end_date=end)

        row = {'Period': period_name, 'Start': start, 'End': end}
        if 'error' in result or not result.get('fold_results'):
            row['error'] = result.get('error', 'no folds')
            logger.warning(f"{period_name} skipped: {row['error']}")
        else:
            row['train_start'] = result['fold_results'][0]['train_start']
            row['n_folds'] = result['n_folds']
            agg = result['aggregate']
            for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio',
                        'max_drawdown', 'calmar_ratio', 'var_95_daily', 'cvar_95_daily']:
                row[key] = agg.get(key, None)

        rows.append(row)

    return pd.DataFrame(rows)


def asset_universe_robustness(
    start_date: str = DEFAULT_TEST_START,
    end_date: str = DEFAULT_TEST_END
) -> pd.DataFrame:
    """
    Uses run_walk_forward_backtest - same 3yr train / 63-day test /
    10bps-per-rebalance methodology as the headline Phase 3 comparison. This
    check already used walk-forward before the sub_period_analysis /
    split_sensitivity fix above; kept as-is.

    Universe 1: Large-cap dominated (5 sectors)
    Universe 2: Full 11-sector
    """
    from app.services.portfolio_service import run_walk_forward_backtest

    universes = {
        'Large-Cap (5 sectors)': ['XLK', 'XLV', 'XLF', 'XLI', 'XLY'],
        'Full Universe (11 sectors)': DEFAULT_ASSETS,
    }

    rows = []
    for uni_name, assets in universes.items():
        logger.info(f"Walk-forward backtest for universe: {uni_name}")
        result = run_walk_forward_backtest(
            assets, use_causal=True, first_test_start=start_date, end_date=end_date
        )

        row = {'Universe': uni_name, 'N_Assets': len(assets)}
        if 'error' in result or not result.get('fold_results'):
            row['error'] = result.get('error', 'no folds')
            logger.warning(f"{uni_name} skipped: {row['error']}")
        else:
            agg = result['aggregate']
            for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio',
                        'max_drawdown', 'calmar_ratio']:
                row[key] = agg.get(key, None)
        rows.append(row)

    return pd.DataFrame(rows)


def transaction_cost_sensitivity(
    assets: Optional[List[str]] = None,
    start_date: str = DEFAULT_TEST_START,
    end_date: str = DEFAULT_TEST_END,
    cost_levels_bps: List[float] = None
) -> pd.DataFrame:
    """
    Test Sharpe ratio degradation at different transaction cost levels,
    walk-forward backtested (costs are charged at each fold's rebalance, so
    this varies with how much turnover the strategy actually has).

    Args:
        assets: Asset universe
        start_date: Backtest start
        end_date: Backtest end
        cost_levels_bps: List of cost levels in basis points
    """
    from app.services.portfolio_service import run_walk_forward_backtest

    if assets is None:
        assets = DEFAULT_ASSETS
    if cost_levels_bps is None:
        cost_levels_bps = [0, 10, 30, 50]

    rows = []
    for bps in cost_levels_bps:
        logger.info(f"Running walk-forward backtest with transaction cost = {bps} bps")
        result = run_walk_forward_backtest(
            assets, use_causal=True, first_test_start=start_date, end_date=end_date,
            transaction_cost_bps=bps
        )

        row = {'Transaction_Cost_BPS': bps}
        if 'error' in result or not result.get('fold_results'):
            row['error'] = result.get('error', 'no folds')
        else:
            agg = result['aggregate']
            row['annualized_return'] = agg.get('annualized_return')
            row['sharpe_ratio'] = agg.get('sharpe_ratio')
            row['sortino_ratio'] = agg.get('sortino_ratio')
            row['max_drawdown'] = agg.get('max_drawdown')
        rows.append(row)

    return pd.DataFrame(rows)


def split_sensitivity(
    assets: List[str] = None,
    base_split: str = DEFAULT_TEST_START,
    shift_months: int = 6
) -> pd.DataFrame:
    """
    Walk-forward backtest (run_walk_forward_backtest - same 3yr train /
    63-day test / 10bps-per-rebalance methodology as phase3_backtesting.py
    and sub_period_analysis above) run from test_start shifted
    +/-shift_months around base_split through DEFAULT_TEST_END, to test
    sensitivity to the train/test split date. Each split's first fold trains
    on data ending just before its own (shifted) test_start, and the
    strategy is re-optimized every fold thereafter through DEFAULT_TEST_END
    - not one fixed allocation held for the whole multi-year window.
    """
    from app.services.portfolio_service import run_walk_forward_backtest
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    if assets is None:
        assets = DEFAULT_ASSETS

    base_date = datetime.strptime(base_split, '%Y-%m-%d')

    splits = {
        f'Early (-{shift_months}m)': (base_date - relativedelta(months=shift_months)).strftime('%Y-%m-%d'),
        'Baseline': base_split,
        f'Late (+{shift_months}m)': (base_date + relativedelta(months=shift_months)).strftime('%Y-%m-%d'),
    }

    rows = []
    for split_name, test_start in splits.items():
        logger.info(f"Testing split: {split_name} (test starts {test_start})")

        result = run_walk_forward_backtest(
            assets, use_causal=True, first_test_start=test_start, end_date=DEFAULT_TEST_END
        )

        row = {'Split': split_name, 'Test_Start': test_start}
        if 'error' in result or not result.get('fold_results'):
            row['error'] = result.get('error', 'no folds')
            logger.warning(f"{split_name} skipped: {row['error']}")
        else:
            row['train_start'] = result['fold_results'][0]['train_start']
            row['n_folds'] = result['n_folds']
            agg = result['aggregate']
            for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown']:
                row[key] = agg.get(key, None)
        rows.append(row)

    return pd.DataFrame(rows)


def run_robustness(
    assets: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Run all Phase 6 robustness checks.

    Args:
        assets: Asset universe

    Returns:
        Dictionary of DataFrames for each robustness check
    """
    if assets is None:
        assets = DEFAULT_ASSETS

    results = {}

    # 6.1 Sub-period analysis
    logger.info("=== 6.1 Sub-Period Analysis ===")
    results['sub_periods'] = sub_period_analysis(assets)

    # 6.2 Asset universe robustness
    logger.info("=== 6.2 Asset Universe Robustness ===")
    results['asset_universe'] = asset_universe_robustness()

    # 6.3 Transaction cost sensitivity
    logger.info("=== 6.3 Transaction Cost Sensitivity ===")
    results['transaction_costs'] = transaction_cost_sensitivity(assets)

    # 6.4 Split sensitivity
    logger.info("=== 6.4 Split Date Sensitivity ===")
    try:
        results['split_sensitivity'] = split_sensitivity(assets)
    except ImportError:
        logger.warning("dateutil not available, skipping split sensitivity")
        results['split_sensitivity'] = pd.DataFrame()

    return results
