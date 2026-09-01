"""
Diagnose: Walk-Forward Fold Weight Concentration
===================================================
Reconstructs the exact portfolio weights the walk-forward backtest chose for
individual folds, to inspect how the base Markowitz optimizer concentrates
weight relative to the (much smaller) causal adjustment. Mirrors
run_walk_forward_backtest's per-fold indexing exactly (train_window=756,
test_window=63, fold 0 anchored to first_test_start='2021-05-01') but stops
to record weights instead of moving on to the next fold.

Persists the per-asset, per-fold breakdown referenced in paper.tex Section 6
(Limitations) - the fold 3/4 concentration finding and the "0.1-1.7
percentage points" vs. "11-37% dispersion" comparison (previously an
unsaved, ad-hoc diagnostic - see research_paper/claims_to_evidence.md,
claims #27/#28).

Usage:
    cd backend
    python scripts/diagnose_fold_concentration.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'results')

UNIVERSE = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']
TRAIN_WINDOW = 756
TEST_WINDOW = 63
FIRST_TEST_START = '2021-05-01'

# 0-indexed fold numbers to inspect. Folds 2 and 3 here correspond to the
# "fold 3" and "fold 4" referenced in paper.tex Section 6 (1-indexed there).
FOLDS_TO_INSPECT = [2, 3]


def run_diagnostic(folds=FOLDS_TO_INSPECT):
    import numpy as np
    import pandas as pd
    from app.services.portfolio_service import _optimize_markowitz, _optimize_with_causal
    from app.services.price_store import get_price_store

    prices = get_price_store().get_history(UNIVERSE + ['SPY'], start='2010-01-01', end='2024-01-01')
    returns = prices.pct_change().dropna()
    n_total = len(returns)

    target_idx = int(returns.index.searchsorted(pd.Timestamp(FIRST_TEST_START)))
    fold0_train_start = max(0, target_idx - TRAIN_WINDOW)

    rows = []
    for fold in folds:
        train_start = fold0_train_start + fold * TEST_WINDOW
        train_end = train_start + TRAIN_WINDOW
        test_end = train_end + TEST_WINDOW

        train_returns = returns.iloc[train_start:train_end]
        test_returns = returns.iloc[train_end:test_end]
        as_of_date = returns.index[train_end - 1].strftime('%Y-%m-%d')
        test_start_date = returns.index[train_end].strftime('%Y-%m-%d')
        test_end_date = returns.index[min(test_end - 1, n_total - 1)].strftime('%Y-%m-%d')

        cols = list(train_returns.columns)
        mean_ret = train_returns.mean().values * 252
        cov_mat = train_returns.cov().values * 252

        mkw_weights = _optimize_markowitz(mean_ret, cov_mat, 'max_sharpe')
        causal_weights, adjustments = _optimize_with_causal(
            mean_ret, cov_mat, 'max_sharpe', cols, None, as_of_date=as_of_date
        )

        test_asset_rets = (np.prod(1 + test_returns[cols], axis=0) - 1) * 100

        print(f"\n{'=' * 90}\nFOLD {fold + 1}: train {returns.index[train_start].date()} to "
              f"{returns.index[train_end - 1].date()}, test {test_start_date} to {test_end_date}"
              f"\n{'=' * 90}")
        print(f"{'Asset':<8}{'TrailingAnnRet%':>18}{'TrailingVol%':>15}{'Markowitz W%':>15}"
              f"{'Causal W%':>13}{'TestRealized%':>16}")

        for i, c in enumerate(cols):
            if c == 'SPY':
                continue
            trailing_ret = mean_ret[i] * 100
            trailing_vol = np.sqrt(cov_mat[i, i]) * 100
            mkw_w = mkw_weights[i] * 100
            causal_w = causal_weights[i] * 100
            realized = test_asset_rets[c]
            print(f"{c:<8}{trailing_ret:>18.2f}{trailing_vol:>15.2f}{mkw_w:>15.2f}"
                  f"{causal_w:>13.2f}{realized:>16.2f}")
            rows.append({
                'fold': fold + 1,
                'as_of_date': as_of_date,
                'test_start': test_start_date,
                'test_end': test_end_date,
                'asset': c,
                'trailing_ann_return_pct': round(trailing_ret, 4),
                'trailing_vol_pct': round(trailing_vol, 4),
                'markowitz_weight_pct': round(mkw_w, 4),
                'causal_weight_pct': round(causal_w, 4),
                'causal_adjustment_pp': round(causal_w - mkw_w, 4),
                'test_realized_return_pct': round(float(realized), 4),
            })

        print(f"  SPY test-window return: {test_asset_rets['SPY']:.2f}%")
        if adjustments:
            print(f"Causal adjustments applied: {adjustments}")
        else:
            print("Causal adjustments applied: NONE (empty list - causal tilt had zero effect this fold)")

    return pd.DataFrame(rows)


if __name__ == '__main__':
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df = run_diagnostic()
    out_path = os.path.join(RESULTS_DIR, 'fold_concentration_diagnostic.csv')
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")
