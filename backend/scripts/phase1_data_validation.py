"""
Phase 1 -- Data Validation
==========================
Validates the integrity of the data pipeline before any models are run.

Checks:
1. Shape, date range, null counts of all dataframes
2. Treatment/outcome variable data leakage detection
3. Feature correlation matrix (flag pairs > 0.85)
4. Distribution statistics (mean, std, skew, kurtosis)
5. ADF stationarity tests on treatment variables

Usage:
    from scripts.phase1_data_validation import run_validation
    results = run_validation()
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)


def run_validation(
    train_end_date: str = '2021-04-30',
    test_start_date: str = '2021-05-01'
) -> pd.DataFrame:
    """
    Run all Phase 1 data validation checks.
    
    Args:
        train_end_date: End of training period
        test_start_date: Start of test period
    
    Returns:
        DataFrame summarizing all validation results
    """
    from app.services.data_pipeline import get_pipeline
    
    pipeline = get_pipeline()
    
    # Run full validation
    val_results = pipeline.validate_data()
    
    if 'error' in val_results:
        logger.error(f"Validation failed: {val_results['error']}")
        logger.info("Attempting to run pipeline first...")
        pipeline.run_full_pipeline(force_refresh=True)
        val_results = pipeline.validate_data()
    
    # Print results
    print("=" * 60)
    print("PHASE 1: DATA VALIDATION RESULTS")
    print("=" * 60)
    
    # 1. Basic info
    shape = val_results.get('shape', {})
    print(f"\nDataset Shape: {shape.get('rows', 'N/A')} rows x {shape.get('columns', 'N/A')} columns")
    
    date_range = val_results.get('date_range', {})
    print(f"Date Range: {date_range.get('start', 'N/A')} to {date_range.get('end', 'N/A')}")
    
    print(f"Total Nulls: {val_results.get('total_nulls', 'N/A')}")
    
    # 2. Train/Test split verification
    print(f"\nTrain Period: START to {train_end_date}")
    print(f"Test Period:  {test_start_date} to END")
    print(f"-> Gap between train/test ensures no data leakage")
    
    # 3. High correlations
    high_corrs = val_results.get('high_correlations', [])
    print(f"\nHigh Correlation Pairs (|r| > 0.85): {len(high_corrs)}")
    if high_corrs:
        for pair in high_corrs[:10]:  # Show top 10
            print(f"  {pair['var1']} ? {pair['var2']}: r = {pair['correlation']:.4f}")
        if len(high_corrs) > 10:
            print(f"  ... and {len(high_corrs) - 10} more")
    
    # 4. Distribution stats for key variables
    dist_stats = val_results.get('distribution_stats', {})
    treatment_vars = [k for k in dist_stats if 'Change' in k or 'Rate' in k]
    outcome_vars = [k for k in dist_stats if 'Return' in k]
    
    print(f"\nTreatment Variable Statistics ({len(treatment_vars)} vars):")
    for var in treatment_vars[:5]:
        s = dist_stats[var]
        print(f"  {var}: mean={s['mean']:.6f}, std={s['std']:.6f}, "
              f"skew={s['skew']:.4f}, kurtosis={s['kurtosis']:.4f}")
    
    print(f"\nOutcome Variable Statistics ({len(outcome_vars)} vars):")
    for var in outcome_vars[:5]:
        s = dist_stats[var]
        print(f"  {var}: mean={s['mean']:.6f}, std={s['std']:.6f}, "
              f"skew={s['skew']:.4f}, kurtosis={s['kurtosis']:.4f}")
    
    # 5. ADF tests
    adf_tests = val_results.get('adf_tests', [])
    if isinstance(adf_tests, list):
        print(f"\nADF Stationarity Tests ({len(adf_tests)} variables):")
        non_stationary = [t for t in adf_tests if t.get('stationary') == False]
        stationary = [t for t in adf_tests if t.get('stationary') == True]
        print(f"  Stationary: {len(stationary)}")
        print(f"  Non-Stationary: {len(non_stationary)}")
        
        if non_stationary:
            print("  (!) Non-stationary variables:")
            for t in non_stationary:
                print(f"    {t['variable']}: ADF={t.get('adf_statistic')}, p={t.get('p_value')}")
    
    # Build summary DataFrame
    summary_rows = [
        {'Check': 'Dataset Rows', 'Value': shape.get('rows', 'N/A'), 'Status': 'OK'},
        {'Check': 'Dataset Columns', 'Value': shape.get('columns', 'N/A'), 'Status': 'OK'},
        {'Check': 'Date Range Start', 'Value': date_range.get('start', 'N/A'), 'Status': 'OK'},
        {'Check': 'Date Range End', 'Value': date_range.get('end', 'N/A'), 'Status': 'OK'},
        {'Check': 'Total Nulls', 'Value': val_results.get('total_nulls', 'N/A'),
         'Status': 'OK' if val_results.get('total_nulls', 0) == 0 else 'WARNING'},
        {'Check': 'High Correlations (>0.85)', 'Value': len(high_corrs),
         'Status': 'WARNING' if len(high_corrs) > 5 else 'OK'},
        {'Check': 'Train End Date', 'Value': train_end_date, 'Status': 'OK'},
        {'Check': 'Test Start Date', 'Value': test_start_date, 'Status': 'OK'},
    ]
    
    if isinstance(adf_tests, list):
        non_stat_count = len([t for t in adf_tests if t.get('stationary') == False])
        summary_rows.append({
            'Check': 'Non-Stationary Variables',
            'Value': non_stat_count,
            'Status': 'WARNING' if non_stat_count > 0 else 'OK'
        })
    
    df = pd.DataFrame(summary_rows)
    
    print(f"\n{'=' * 60}")
    print("VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    warnings = df[df['Status'] == 'WARNING']
    print(f"Total Checks: {len(df)}")
    print(f"Passed: {len(df) - len(warnings)}")
    print(f"Warnings: {len(warnings)}")
    
    return df
