#!/usr/bin/env python
"""
run_all_results.py
==================
Reproduce all paper results from scratch with a single command:
    
    cd backend
    python run_all_results.py

This master script runs all 7 phases of the evaluation protocol
and saves all outputs (CSV tables, PNG figures) to the results/ directory.

Phases:
    1. Data Validation
    2. Causal Model Evaluation (ATE + Refutations + CATE)
    3. Portfolio Backtesting (4-way comparison)
    4. Statistical Significance Testing
    5. Ablation Study (4 ablations)
    6. Robustness Checks (sub-periods, universes, transaction costs, split sensitivity)
    7. Chart Generation (all paper-ready figures at 300 DPI)
"""

import os
import sys
import json
import logging
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

# Setup path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Results directory - must be created BEFORE logging FileHandler
RESULTS_DIR = os.path.join(BACKEND_DIR, '..', 'results')
FIGURES_DIR = os.path.join(RESULTS_DIR, 'figures')
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# Setup logging (after directory creation)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(RESULTS_DIR, 'run_log.txt'), mode='w')
    ]
)
logger = logging.getLogger('run_all_results')
warnings.filterwarnings('ignore')

# Configuration
BACKTEST_START = '2021-05-01'
BACKTEST_END = '2024-01-01'
TRAIN_END = '2021-04-30'
UNIVERSE = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']


def save_csv(df, filename):
    """Save DataFrame to CSV in results directory."""
    path = os.path.join(RESULTS_DIR, filename)
    df.to_csv(path, index=False)
    logger.info(f"Saved: {path}")
    return path


def main():
    start_time = datetime.now()
    
    print("=" * 70)
    print("  CAUSAL FINANCE: FULL RESULTS REPRODUCTION")
    print(f"  Run date: {start_time.isoformat()}")
    print(f"  Train period: 2010-01-01 to {TRAIN_END}")
    print(f"  Test  period: {BACKTEST_START} to {BACKTEST_END}")
    print(f"  Universe: {len(UNIVERSE)} sector ETFs")
    print("=" * 70)
    
    all_results = {}
    
    # ============================================================
    # PHASE 1: Data Validation
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 1] Data Validation...")
    print("=" * 50)
    
    try:
        from scripts.phase1_data_validation import run_validation
        validation_df = run_validation(train_end_date=TRAIN_END)
        save_csv(validation_df, 'phase1_data_validation.csv')
        all_results['phase1'] = 'COMPLETE'
    except Exception as e:
        logger.error(f"Phase 1 failed: {e}")
        all_results['phase1'] = f'FAILED: {e}'
    
    # ============================================================
    # PHASE 2: Causal Model Evaluation
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 2] Causal Model Evaluation...")
    print("=" * 50)
    
    try:
        from scripts.phase2_causal_evaluation import run_causal_evaluation, compute_cate_table
        
        ate_df = run_causal_evaluation(train_end_date=TRAIN_END)
        save_csv(ate_df, 'phase2_ate_results.csv')
        
        cate_df = compute_cate_table(train_end_date=TRAIN_END)
        save_csv(cate_df, 'phase2_cate_table.csv')
        
        all_results['phase2'] = 'COMPLETE'
    except Exception as e:
        logger.error(f"Phase 2 failed: {e}")
        all_results['phase2'] = f'FAILED: {e}'
    
    # ============================================================
    # PHASE 3: Portfolio Backtesting
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 3] Portfolio Performance Backtesting...")
    print("=" * 50)
    
    backtest_results = {}
    try:
        from scripts.phase3_backtesting import run_all_backtests
        
        comparison_df, backtest_results = run_all_backtests(
            start_date=BACKTEST_START,
            end_date=BACKTEST_END,
            assets=UNIVERSE
        )
        save_csv(comparison_df, 'phase3_backtest_comparison.csv')
        all_results['phase3'] = 'COMPLETE'
    except Exception as e:
        logger.error(f"Phase 3 failed: {e}")
        all_results['phase3'] = f'FAILED: {e}'
    
    # ============================================================
    # PHASE 4: Statistical Significance Testing
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 4] Statistical Significance Testing...")
    print("=" * 50)
    
    try:
        from scripts.phase4_statistical_tests import run_statistical_tests
        
        if backtest_results:
            causal_returns = np.array(
                backtest_results.get('Causal Portfolio', {}).get('daily_returns', [])
            )
            
            benchmark_returns = {}
            for name in ['Equal Weight', 'Markowitz MPT', 'S&P 500 (SPY)']:
                bt = backtest_results.get(name, {})
                dr = bt.get('daily_returns', [])
                if dr:
                    benchmark_returns[name] = np.array(dr)
            
            if len(causal_returns) > 0 and benchmark_returns:
                stats_results = run_statistical_tests(causal_returns, benchmark_returns)
                
                summary = stats_results.get('summary_table')
                if summary is not None:
                    save_csv(summary, 'phase4_statistical_significance.csv')
                
                # Save detailed results
                for test_type, test_results in stats_results.items():
                    if isinstance(test_results, list):
                        df = pd.DataFrame(test_results)
                        save_csv(df, f'phase4_{test_type}.csv')
                
                all_results['phase4'] = 'COMPLETE'
            else:
                all_results['phase4'] = 'SKIPPED: No backtest returns available'
        else:
            all_results['phase4'] = 'SKIPPED: Phase 3 did not complete'
            
    except Exception as e:
        logger.error(f"Phase 4 failed: {e}")
        all_results['phase4'] = f'FAILED: {e}'
    
    # ============================================================
    # PHASE 5: Ablation Study
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 5] Ablation Study...")
    print("=" * 50)
    
    try:
        from scripts.phase5_ablation import run_ablation
        
        ablation_df = run_ablation(
            assets=UNIVERSE,
            start_date=BACKTEST_START,
            end_date=BACKTEST_END
        )
        save_csv(ablation_df, 'phase5_ablation.csv')
        all_results['phase5'] = 'COMPLETE'
    except Exception as e:
        logger.error(f"Phase 5 failed: {e}")
        all_results['phase5'] = f'FAILED: {e}'
    
    # ============================================================
    # PHASE 6: Robustness Checks
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 6] Robustness Checks...")
    print("=" * 50)
    
    try:
        from scripts.phase6_robustness import run_robustness

        # Each check now derives its own point-in-time weights internally
        # (see phase6_robustness.py) rather than reusing one weight vector
        # computed from present-day data across every historical window.
        robustness_results = run_robustness(assets=UNIVERSE)

        for check_name, check_df in robustness_results.items():
            if isinstance(check_df, pd.DataFrame) and not check_df.empty:
                save_csv(check_df, f'phase6_{check_name}.csv')
        
        all_results['phase6'] = 'COMPLETE'
    except Exception as e:
        logger.error(f"Phase 6 failed: {e}")
        all_results['phase6'] = f'FAILED: {e}'
    
    # ============================================================
    # PHASE 7: Chart Generation
    # ============================================================
    print("\n" + "=" * 50)
    print("[PHASE 7] Paper-Ready Chart Generation...")
    print("=" * 50)
    
    try:
        from scripts.chart_generator import generate_all_charts
        
        if backtest_results:
            chart_paths = generate_all_charts(backtest_results)
            all_results['phase7_charts'] = chart_paths
        
        # DAG visualization
        from app.services.causal_discovery import visualize_causal_dag, generate_granger_heatmap
        
        # Try to generate DAG from discovered edges
        try:
            from app.services.data_pipeline import get_pipeline
            from app.services.causal_discovery import discover_sector_macro_relationships
            
            pipeline = get_pipeline()
            feature_matrix = pipeline.load_data('feature_matrix')
            
            if feature_matrix is not None:
                sector_drivers = discover_sector_macro_relationships(feature_matrix)
                
                # Convert to edges for visualization
                edges = []
                for sector, drivers in sector_drivers.items():
                    for driver in drivers:
                        edges.append({
                            'cause': driver['variable'],
                            'effect': f'{sector}_Return',
                            'weight': driver.get('f_statistic', 1.0),
                        })
                
                if edges:
                    dag_path = visualize_causal_dag(
                        edges,
                        output_path=os.path.join(FIGURES_DIR, 'causal_dag.png')
                    )
                    all_results['dag_chart'] = dag_path
                
                # Granger heatmap
                cause_vars = [c for c in feature_matrix.columns if 'Change' in c][:6]
                effect_vars = [c for c in feature_matrix.columns if 'Return_1d' in c][:11]
                
                if cause_vars and effect_vars:
                    heatmap_path = generate_granger_heatmap(
                        feature_matrix,
                        cause_vars=cause_vars,
                        effect_vars=effect_vars,
                        output_path=os.path.join(FIGURES_DIR, 'granger_heatmap.png')
                    )
                    all_results['granger_heatmap'] = heatmap_path
        except Exception as e:
            logger.warning(f"DAG/Granger visualization failed: {e}")
        
        all_results['phase7'] = 'COMPLETE'
    except Exception as e:
        logger.error(f"Phase 7 failed: {e}")
        all_results['phase7'] = f'FAILED: {e}'
    
    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("  EXECUTION SUMMARY")
    print("=" * 70)
    print(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"  Results saved to: {os.path.abspath(RESULTS_DIR)}")
    print()
    
    for phase, status in all_results.items():
        if isinstance(status, dict):
            print(f"  {phase}: {len(status)} items generated")
        else:
            icon = "OK" if status == 'COMPLETE' else "X"
            print(f"  {icon} {phase}: {status}")
    
    # Save execution summary
    summary = {
        'run_date': start_time.isoformat(),
        'duration_seconds': round(duration, 1),
        'phases': {k: v if isinstance(v, str) else f'{len(v)} items' for k, v in all_results.items()},
        'config': {
            'train_end': TRAIN_END,
            'test_start': BACKTEST_START,
            'test_end': BACKTEST_END,
            'universe': UNIVERSE,
        }
    }
    
    with open(os.path.join(RESULTS_DIR, 'execution_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    
    # List all output files
    print(f"\n  Output files:")
    for root, dirs, files in os.walk(RESULTS_DIR):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            relpath = os.path.relpath(filepath, RESULTS_DIR)
            print(f"    {relpath} ({size:,} bytes)")
    
    print("\n" + "=" * 70)
    print("  DONE. All paper results generated.")
    print("=" * 70)
    
    return all_results


if __name__ == '__main__':
    main()
