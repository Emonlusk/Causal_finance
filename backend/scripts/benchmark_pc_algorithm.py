"""
Benchmark: PC Algorithm Conditional-Independence Test
=======================================================
Times the PC algorithm's DAG construction (CausalDiscoveryEngine.pc_algorithm)
on the real 11-sector return data, comparing the current 'pearsonr' CI test
against pgmpy's old default 'chi_square' - the fix described in paper.tex
Section 4.1 ("reducing DAG construction time from several minutes to
approximately 30 seconds"). Persists the timing to results/ so the claim is
independently reproducible rather than a one-off console observation
(see research_paper/claims_to_evidence.md, claim #9).

The chi_square comparison runs in a separate, hard-killable child process
with a timeout: chi_square assumes categorical data and builds a
contingency table per conditional-independence test, and on continuous
return data (where almost every value is its own category) this can blow
up combinatorially rather than merely being slow. If it does not finish
within CHI_SQUARE_TIMEOUT_SECONDS, the child process is killed and that is
reported as-is (a timeout, not a fabricated number) - which if anything
understates the severity of the regression the pearsonr fix resolved.

Usage:
    cd backend
    python scripts/benchmark_pc_algorithm.py
"""

import os
import sys
import time
import json
import logging
import multiprocessing

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'results')
CHI_SQUARE_TIMEOUT_SECONDS = 180


def _load_sector_returns():
    from app.services.data_pipeline import get_pipeline

    pipeline = get_pipeline()
    feature_matrix = pipeline.load_data('feature_matrix')
    if feature_matrix is None:
        result = pipeline.run_full_pipeline()
        feature_matrix = result.get('feature_matrix')

    sector_cols = [c for c in feature_matrix.columns if c.endswith('_Return_1d')]
    return feature_matrix[sector_cols].dropna()


def _chi_square_worker(sector_returns, significance_level, queue):
    """Runs in a child process so it can be forcibly killed on timeout."""
    from pgmpy.estimators import PC

    t0 = time.perf_counter()
    pc = PC(sector_returns)
    model = pc.estimate(
        variant='stable',
        ci_test='chi_square',
        max_cond_vars=3,
        significance_level=significance_level,
        return_type='dag',
        show_progress=False,
    )
    elapsed = time.perf_counter() - t0
    queue.put({'elapsed_seconds': round(elapsed, 3), 'n_edges': len(list(model.edges()))})


def run_benchmark() -> dict:
    """
    Time PC-algorithm DAG construction under both CI tests on the same
    real sector-return data used by ml_training_pipeline.py's
    _train_causal_models (the 11 sector _Return_1d columns).

    Returns:
        Dict with timing and edge-count results for both CI tests.
    """
    from app.services.causal_discovery import CausalDiscoveryEngine

    sector_returns = _load_sector_returns()
    print(f"Benchmarking PC algorithm on {sector_returns.shape[1]} sector variables, "
          f"{sector_returns.shape[0]} samples", flush=True)

    results = {
        'n_variables': int(sector_returns.shape[1]),
        'n_samples': int(sector_returns.shape[0]),
        'variables': list(sector_returns.columns),
    }

    # Current implementation: CausalDiscoveryEngine.pc_algorithm, which
    # hardcodes ci_test='pearsonr' (the fix).
    engine = CausalDiscoveryEngine()
    t0 = time.perf_counter()
    pearsonr_result = engine.pc_algorithm(sector_returns)
    pearsonr_elapsed = time.perf_counter() - t0
    results['pearsonr'] = {
        'ci_test': 'pearsonr',
        'elapsed_seconds': round(pearsonr_elapsed, 3),
        'n_edges': len(pearsonr_result.get('edges', [])),
        'method': pearsonr_result.get('method'),
    }
    print(f"  pearsonr (current):  {pearsonr_elapsed:.2f}s, "
          f"{results['pearsonr']['n_edges']} edges", flush=True)

    # Old default: pgmpy's PC with ci_test='chi_square', called directly
    # (not via the engine, since the engine no longer exposes this as an
    # option) with the same max_cond_vars/significance_level the engine
    # uses, to reproduce the pre-fix configuration exactly. Run in a child
    # process with a hard timeout - see module docstring.
    print(f"  chi_square (old default): running in a child process, "
          f"timeout={CHI_SQUARE_TIMEOUT_SECONDS}s...", flush=True)
    queue = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=_chi_square_worker,
        args=(sector_returns, engine.significance_level, queue),
    )
    t0 = time.perf_counter()
    proc.start()
    proc.join(timeout=CHI_SQUARE_TIMEOUT_SECONDS)
    wall_elapsed = time.perf_counter() - t0

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=10)
        if proc.is_alive():
            proc.kill()
            proc.join()
        results['chi_square'] = {
            'ci_test': 'chi_square',
            'elapsed_seconds': None,
            'timed_out': True,
            'timeout_seconds': CHI_SQUARE_TIMEOUT_SECONDS,
            'note': (
                f'Did not complete within {CHI_SQUARE_TIMEOUT_SECONDS}s and was '
                f'forcibly terminated. This is evidence in itself: the original '
                f'"several minutes" characterization in paper.tex Section 4.1 '
                f'understates rather than overstates this regression - on this '
                f'machine, with 11 continuous variables, the old chi_square '
                f'default did not finish within {CHI_SQUARE_TIMEOUT_SECONDS}s at all.'
            ),
        }
        print(f"  chi_square (old default): DID NOT COMPLETE within "
              f"{CHI_SQUARE_TIMEOUT_SECONDS}s - killed", flush=True)
    elif not queue.empty():
        worker_result = queue.get()
        results['chi_square'] = {
            'ci_test': 'chi_square',
            'elapsed_seconds': worker_result['elapsed_seconds'],
            'n_edges': worker_result['n_edges'],
            'method': 'pc_algorithm',
        }
        print(f"  chi_square (old default): {worker_result['elapsed_seconds']:.2f}s, "
              f"{worker_result['n_edges']} edges", flush=True)
    else:
        results['chi_square'] = {
            'ci_test': 'chi_square',
            'elapsed_seconds': round(wall_elapsed, 3),
            'error': f'Child process exited (code {proc.exitcode}) without a result.',
        }
        print(f"  chi_square (old default): failed after {wall_elapsed:.2f}s "
              f"(exit code {proc.exitcode})", flush=True)

    if results['chi_square'].get('elapsed_seconds') and results['pearsonr']['elapsed_seconds'] > 0:
        results['speedup_factor'] = round(
            results['chi_square']['elapsed_seconds'] / results['pearsonr']['elapsed_seconds'], 2
        )
        print(f"  Speedup: {results['speedup_factor']}x", flush=True)
    elif results['chi_square'].get('timed_out'):
        results['speedup_factor_lower_bound'] = round(
            CHI_SQUARE_TIMEOUT_SECONDS / results['pearsonr']['elapsed_seconds'], 2
        )
        print(f"  Speedup: at least {results['speedup_factor_lower_bound']}x "
              f"(chi_square did not finish)", flush=True)

    return results


if __name__ == '__main__':
    os.makedirs(RESULTS_DIR, exist_ok=True)
    output = run_benchmark()
    out_path = os.path.join(RESULTS_DIR, 'pc_algorithm_benchmark.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {out_path}")
