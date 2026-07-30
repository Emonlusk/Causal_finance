"""
Phase 3 -- Portfolio Performance Backtesting
=============================================
Runs full backtest for all portfolio strategies and generates comparison table.

Portfolios:
1. Causal Portfolio (causal-adjusted Markowitz)
2. Traditional Markowitz (no causal adjustment)
3. Equal Weight (1/N)
4. S&P 500 Benchmark (SPY)

Usage:
    from scripts.phase3_backtesting import run_all_backtests
    results = run_all_backtests()
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)

BACKTEST_START = '2021-05-01'
BACKTEST_END = '2024-01-01'
UNIVERSE = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']


def run_all_backtests(
    start_date: str = BACKTEST_START,
    end_date: str = BACKTEST_END,
    assets: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Run backtests for all 4 portfolio strategies and produce comparison table.

    Causal Portfolio and Markowitz MPT are walk-forward backtested: weights
    are re-optimized on a rolling training window and evaluated only on the
    following, unseen test window (see run_walk_forward_backtest). This
    avoids the lookahead bias of optimizing once on present-day data and
    then "backtesting" that against a historical window. Equal Weight and
    SPY require no optimization, so they're evaluated as static-weight
    backtests over the same realized out-of-sample window for a fair
    comparison.

    Args:
        start_date: Target out-of-sample test period start (walk-forward
            folds are anchored to start at/after this date; the realized
            start may land a few trading days later - see printed output)
        end_date: Test period end
        assets: Asset universe (defaults to 11 sector ETFs)

    Returns:
        (comparison_table, backtest_results) - DataFrame with metrics for
        each portfolio strategy, and the raw per-strategy result dicts
    """
    from app.services.portfolio_service import (
        run_backtest, run_walk_forward_backtest
    )

    if assets is None:
        assets = UNIVERSE

    print("=" * 60)
    print("PHASE 3: PORTFOLIO PERFORMANCE BACKTESTING (walk-forward, leak-free)")
    print(f"Target out-of-sample window: {start_date} to {end_date}")
    print(f"Universe: {len(assets)} assets")
    print("=" * 60)

    # Step 1: Walk-forward backtest the two strategies that require
    # optimization. Each fold trains on a rolling window and tests only on
    # the following unseen window - no fold ever sees its own test period,
    # and the causal adjustment uses market indicators as of that fold's
    # training cutoff rather than live/current data.
    logger.info("Running walk-forward backtest: Causal Portfolio...")
    causal_wf = run_walk_forward_backtest(
        assets, use_causal=True, first_test_start=start_date, end_date=end_date
    )
    logger.info("Running walk-forward backtest: Markowitz MPT...")
    markowitz_wf = run_walk_forward_backtest(
        assets, use_causal=False, first_test_start=start_date, end_date=end_date
    )

    for name, wf in [('Causal Portfolio', causal_wf), ('Markowitz MPT', markowitz_wf)]:
        if 'error' in wf or not wf.get('fold_results'):
            raise RuntimeError(f"Walk-forward backtest failed for {name}: {wf.get('error', 'no folds')}")

    # Fold boundaries won't land exactly on start_date/end_date. Use the
    # realized window for the static-weight benchmarks too, so all four
    # strategies are compared over identical dates.
    realized_start = causal_wf['fold_results'][0]['test_start']
    realized_end = causal_wf['fold_results'][-1]['test_end']
    print(f"\nRealized out-of-sample window: {realized_start} to {realized_end} "
          f"({causal_wf['n_folds']} folds, {markowitz_wf['n_folds']} folds)")

    # Step 2: Static-weight benchmarks over the same realized window - no
    # optimization happens for these, so no lookahead risk either way.
    n = len(assets)
    equal_weights = {s: round(1 / n, 4) for s in assets}
    spy_weights = {'SPY': 1.0}

    backtest_results = {
        # daily_returns lives alongside (not inside) run_walk_forward_backtest's
        # 'aggregate' metrics dict - merge it in so downstream consumers (Phase 4
        # significance testing) can use it the same way as run_backtest's output.
        'Causal Portfolio': {**causal_wf['aggregate'], 'daily_returns': causal_wf['daily_returns'],
                             'fold_results': causal_wf['fold_results']},
        'Markowitz MPT': {**markowitz_wf['aggregate'], 'daily_returns': markowitz_wf['daily_returns'],
                          'fold_results': markowitz_wf['fold_results']},
        'Equal Weight': run_backtest(equal_weights, realized_start, realized_end),
        'S&P 500 (SPY)': run_backtest(spy_weights, realized_start, realized_end),
    }

    for name, result in backtest_results.items():
        if 'error' in result:
            logger.warning(f"{name} backtest failed: {result['error']}")
            continue
        print(f"\n--- {name} ---")
        for key in ['annualized_return', 'sharpe_ratio', 'sortino_ratio',
                     'max_drawdown', 'calmar_ratio', 'var_95_daily', 'cvar_95_daily']:
            val = result.get(key, 'N/A')
            print(f"  {key}: {val}")

    # Step 3: Build comparison table
    metrics_keys = [
        'annualized_return', 'annualized_volatility', 'sharpe_ratio',
        'sortino_ratio', 'max_drawdown', 'calmar_ratio',
        'var_95_daily', 'cvar_95_daily', 'hit_rate_monthly',
        'turnover_monthly', 'total_return',
    ]
    
    # Check for optional metrics
    optional_keys = ['information_ratio', 'treynor_ratio', 'beta']
    for key in optional_keys:
        for bt in backtest_results.values():
            if key in bt:
                metrics_keys.append(key)
                break
    
    rows = []
    for name, bt in backtest_results.items():
        row = {'Portfolio': name}
        for key in metrics_keys:
            row[key] = bt.get(key, None)
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Print formatted table
    print(f"\n{'=' * 60}")
    print("PORTFOLIO COMPARISON TABLE")
    print(f"{'=' * 60}")
    print(df.to_string(index=False))
    
    return df, backtest_results
