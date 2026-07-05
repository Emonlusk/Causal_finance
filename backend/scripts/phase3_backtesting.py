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
    
    Args:
        start_date: Out-of-sample test period start
        end_date: Test period end
        assets: Asset universe (defaults to 11 sector ETFs)
    
    Returns:
        DataFrame with metrics for each portfolio strategy
    """
    from app.services.portfolio_service import (
        optimize_portfolio_weights, run_backtest
    )
    
    if assets is None:
        assets = UNIVERSE
    
    print("=" * 60)
    print("PHASE 3: PORTFOLIO PERFORMANCE BACKTESTING")
    print(f"Period: {start_date} to {end_date}")
    print(f"Universe: {len(assets)} assets")
    print("=" * 60)
    
    # Step 1: Optimize portfolios
    logger.info("Optimizing portfolio weights...")
    opt = optimize_portfolio_weights(assets, objective='max_sharpe', use_causal=True)
    
    causal_weights = opt.get('causal', {}).get('weights', {})
    markowitz_weights = opt.get('traditional', {}).get('weights', {})
    
    n = len(assets)
    equal_weights = {s: round(1/n, 4) for s in assets}
    spy_weights = {'SPY': 1.0}
    
    portfolios = {
        'Causal Portfolio': causal_weights,
        'Equal Weight': equal_weights,
        'Markowitz MPT': markowitz_weights,
        'S&P 500 (SPY)': spy_weights,
    }
    
    # Step 2: Run backtests
    backtest_results = {}
    for name, weights in portfolios.items():
        if not weights:
            logger.warning(f"No weights for {name}, skipping")
            continue
        
        logger.info(f"Backtesting: {name}")
        result = run_backtest(weights, start_date, end_date)
        backtest_results[name] = result
        
        print(f"\n--- {name} ---")
        print(f"  Weights: {weights}")
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
