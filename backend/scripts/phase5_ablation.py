"""
Phase 5 -- Ablation Study
========================
Isolates what drives performance by systematically removing components:

Ablation 1: No Causal Graph -- Replace causal sensitivities with raw correlations
Ablation 2: No Refutation -- Use raw ATE without validation
Ablation 3: No CATE -- Use sector-averaged ATE instead of heterogeneous CATE
Ablation 4: Alternative Treatment -- Swap primary treatment variable

All five strategies (including the Full Model baseline) are walk-forward
backtested: weights are re-derived every fold from only the data available
before that fold's test window, and causal/economic adjustments are applied
using that fold's own training cutoff - not present-day data applied
retroactively to a historical test window. See portfolio_service.
run_walk_forward_backtest / _optimize_with_causal(as_of_date=...).

Usage:
    from scripts.phase5_ablation import run_ablation
    results = run_ablation()
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


def _no_cate_weight_fn(train_returns: pd.DataFrame, as_of_date: str, cols: List[str]) -> np.ndarray:
    """
    Ablation 3: sector-averaged ATE applied uniformly to every asset,
    instead of each sector's own heterogeneous sensitivity - tests whether
    CATE's heterogeneity adds value over a single average effect.
    Uses a fixed hypothetical economic forecast (not live data), matching
    the original ablation's design - so the only lookahead-bias source here
    was the training window itself, not this forecast.
    """
    from app.services.portfolio_service import _optimize_markowitz
    from app.services.treatment_effects import get_sensitivity_matrix_as_of
    from app.services.causal_service import DEFAULT_SECTOR_SENSITIVITY

    mean_ret = train_returns.mean().values * 252
    cov_mat = train_returns.cov().values * 252

    active_matrix = get_sensitivity_matrix_as_of(as_of_date) or DEFAULT_SECTOR_SENSITIVITY
    all_factors = set()
    for sector_sens in active_matrix.values():
        all_factors.update(sector_sens.keys())
    mean_sensitivity = {
        factor: np.mean([active_matrix[s].get(factor, 0) for s in active_matrix])
        for factor in all_factors
    }

    economic_forecast = {'interest_rates': 0.005, 'inflation': -0.002, 'gdp_growth': 0.003}
    total_adjustment = sum(mean_sensitivity.get(f, 0) * v for f, v in economic_forecast.items())

    adjusted_returns = mean_ret.copy()
    for i in range(len(cols)):
        adjusted_returns[i] += total_adjustment

    return _optimize_markowitz(adjusted_returns, cov_mat, 'max_sharpe')


def _alt_treatment_weight_fn(train_returns: pd.DataFrame, as_of_date: str, cols: List[str]) -> np.ndarray:
    """
    Ablation 4: VIX as the primary treatment instead of interest rates -
    zeroes out rate/inflation/growth effects and adjusts only on a
    hypothetical VIX move, per-sector. Fixed forecast, not live data.
    """
    from app.services.portfolio_service import _optimize_markowitz, SECTOR_ETFS
    from app.services.treatment_effects import get_sensitivity_matrix_as_of
    from app.services.causal_service import DEFAULT_SECTOR_SENSITIVITY

    mean_ret = train_returns.mean().values * 252
    cov_mat = train_returns.cov().values * 252

    active_matrix = get_sensitivity_matrix_as_of(as_of_date) or DEFAULT_SECTOR_SENSITIVITY
    economic_forecast = {
        'interest_rates': 0.0, 'inflation': 0.0, 'gdp_growth': 0.0,
        'oil_price': 0.0, 'vix': 0.01,
    }

    adjusted_returns = mean_ret.copy()
    for i, asset in enumerate(cols):
        sector_info = SECTOR_ETFS.get(asset, {})
        sector_key = sector_info.get('sector', '')
        if sector_key in active_matrix:
            sensitivity = active_matrix[sector_key]
            total_adj = sum(sensitivity.get(f, 0) * v for f, v in economic_forecast.items())
            adjusted_returns[i] += total_adj

    return _optimize_markowitz(adjusted_returns, cov_mat, 'max_sharpe')


def run_ablation(
    assets: Optional[List[str]] = None,
    start_date: str = '2021-05-01',
    end_date: str = '2024-01-01'
) -> pd.DataFrame:
    """
    Run all 4 ablation studies plus the full-model baseline, all walk-forward
    backtested over the same realized out-of-sample window, and produce a
    comparison table.

    Returns:
        DataFrame with ablation results comparison
    """
    from app.services.portfolio_service import run_walk_forward_backtest

    if assets is None:
        assets = DEFAULT_ASSETS

    strategies = {
        'full_model': dict(
            description='Full Causal Model',
            kwargs=dict(use_causal=True),
        ),
        'no_causal_graph': dict(
            description='No causal adjustment (plain Markowitz)',
            kwargs=dict(use_causal=False),
        ),
        'no_refutation': dict(
            description='Raw ATE without refutation validation',
            # Refutation tests validate an estimate, they don't change the
            # weights the live pipeline computes either way (see
            # ml_training_pipeline.py) - this ablation is a structural no-op
            # against full_model in the current implementation, preserved
            # as-is here rather than inventing new behavior.
            kwargs=dict(use_causal=True),
        ),
        'no_cate': dict(
            description='Uniform ATE (no heterogeneous CATE by sector)',
            kwargs=dict(weight_fn=_no_cate_weight_fn),
        ),
        'alt_treatment': dict(
            description='VIX as primary treatment (replaces interest rate)',
            kwargs=dict(weight_fn=_alt_treatment_weight_fn),
        ),
    }

    wf_results = {}
    for name, spec in strategies.items():
        logger.info(f"Running walk-forward backtest: {name} ({spec['description']})...")
        wf_results[name] = run_walk_forward_backtest(
            assets, first_test_start=start_date, end_date=end_date, **spec['kwargs']
        )

    full_wf = wf_results['full_model']
    if 'error' in full_wf or not full_wf.get('fold_results'):
        raise RuntimeError(f"Walk-forward backtest failed for full_model: {full_wf.get('error', 'no folds')}")

    realized_start = full_wf['fold_results'][0]['test_start']
    realized_end = full_wf['fold_results'][-1]['test_end']
    logger.info(f"Realized out-of-sample window: {realized_start} to {realized_end} "
                f"({full_wf['n_folds']} folds)")

    metrics_keys = [
        'annualized_return', 'annualized_volatility', 'sharpe_ratio',
        'sortino_ratio', 'max_drawdown', 'calmar_ratio',
        'var_95_daily', 'cvar_95_daily'
    ]

    full_sharpe = full_wf['aggregate'].get('sharpe_ratio', 0)

    rows = []
    for name, spec in strategies.items():
        wf = wf_results[name]
        row = {'Ablation': name, 'Description': spec['description']}
        if 'error' in wf or not wf.get('fold_results'):
            row['error'] = wf.get('error', 'no folds')
            for key in metrics_keys:
                row[key] = None
            row['delta_sharpe_vs_full'] = None
        else:
            agg = wf['aggregate']
            for key in metrics_keys:
                row[key] = agg.get(key, None)
            this_sharpe = agg.get('sharpe_ratio', 0) or 0
            row['delta_sharpe_vs_full'] = round(this_sharpe - full_sharpe, 4) if full_sharpe else None
        rows.append(row)

    df = pd.DataFrame(rows)

    logger.info("Ablation study complete")
    logger.info(f"\n{df.to_string(index=False)}")

    return df
