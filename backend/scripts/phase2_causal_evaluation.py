"""
Phase 2 -- Causal Model Evaluation
===================================
Runs and reports results for every causal model:

DoWhy:
- Identified estimand, ATE, 95% CI
- All 4 refutation tests with pass/fail

EconML (CATE):
- CATE estimate per sector (mean, std, 5th, 95th percentiles)
- DML first/second stage R?

Usage:
    from scripts.phase2_causal_evaluation import run_causal_evaluation
    results = run_causal_evaluation()
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)

# Treatment-Outcome pairs for the paper
TREATMENTS = ['Fed_Funds_Rate_Change', 'CPI_Change', 'Treasury_10Y_Yield_Change',
              'Oil_WTI_Change', 'VIX_Change']

OUTCOMES = ['Technology_Return_1d', 'Healthcare_Return_1d', 'Energy_Return_1d',
            'Financials_Return_1d', 'Industrials_Return_1d']

CONFOUNDERS = ['SP500_Return', 'SP500_Volatility_21d']


def run_causal_evaluation(
    train_end_date: str = '2021-04-30',
    max_pairs: int = 25
) -> pd.DataFrame:
    """
    Run full causal model evaluation (Phase 2).
    
    Args:
        train_end_date: Use only training data up to this date
        max_pairs: Maximum treatment-outcome pairs to evaluate
    
    Returns:
        DataFrame with ATE results for all treatment-outcome pairs
    """
    from app.services.data_pipeline import get_pipeline
    from app.services.treatment_effects import TreatmentEffectEstimator
    
    pipeline = get_pipeline()
    feature_matrix = pipeline.load_data('feature_matrix')
    
    if feature_matrix is None:
        logger.info("Running data pipeline first...")
        result = pipeline.run_full_pipeline()
        feature_matrix = result.get('feature_matrix')
    
    if feature_matrix is None or feature_matrix.empty:
        return pd.DataFrame({'error': ['No feature matrix available']})
    
    # Use ONLY training data
    train_data = feature_matrix[feature_matrix.index <= train_end_date]
    logger.info(f"Using training data: {len(train_data)} rows, ending {train_end_date}")
    
    # Filter to available columns
    available_treatments = [t for t in TREATMENTS if t in train_data.columns]
    available_outcomes = [o for o in OUTCOMES if o in train_data.columns]
    available_confounders = [c for c in CONFOUNDERS if c in train_data.columns]
    
    if not available_treatments or not available_outcomes:
        logger.warning("No treatment/outcome columns found in data")
        # Try column name variations
        return_cols = [c for c in train_data.columns if 'Return_1d' in c]
        change_cols = [c for c in train_data.columns if 'Change' in c]
        logger.info(f"Available return columns: {return_cols[:5]}")
        logger.info(f"Available change columns: {change_cols[:5]}")
        
        if return_cols and change_cols:
            available_outcomes = return_cols[:5]
            available_treatments = change_cols[:5]
    
    estimator = TreatmentEffectEstimator()
    
    results = []
    pair_count = 0
    
    print("=" * 60)
    print("PHASE 2: CAUSAL MODEL EVALUATION")
    print("=" * 60)
    
    for treatment in available_treatments:
        for outcome in available_outcomes:
            if pair_count >= max_pairs:
                break
            
            logger.info(f"Estimating: {treatment} -> {outcome}")
            print(f"\n--- {treatment} -> {outcome} ---")
            
            try:
                result = estimator.estimate_ate(
                    data=train_data,
                    treatment=treatment,
                    outcome=outcome,
                    confounders=available_confounders,
                    method='auto'
                )
                
                row = {
                    'treatment': treatment,
                    'outcome': outcome,
                    'method': result.get('method', 'unknown'),
                    'ate': result.get('ate'),
                    'ci_lower': result.get('ci_lower'),
                    'ci_upper': result.get('ci_upper'),
                    'p_value': result.get('p_value'),
                    'standard_error': result.get('standard_error'),
                    'sample_size': result.get('sample_size'),
                }
                
                # Print results
                print(f"  Method: {result.get('method')}")
                print(f"  ATE: {result.get('ate', 'N/A'):.6f}" if result.get('ate') else "  ATE: N/A")
                if result.get('ci_lower') is not None and result.get('ci_upper') is not None:
                    print(f"  95% CI: [{result['ci_lower']:.6f}, {result['ci_upper']:.6f}]")
                if result.get('p_value') is not None:
                    print(f"  p-value: {result['p_value']:.6f}")
                
                # Refutation results
                refutations = result.get('refutation_tests', [])
                for ref in refutations:
                    test_name = ref.get('test', 'unknown')
                    ref_p = ref.get('p_value')
                    passed = ref.get('passed')
                    row[f'refutation_{test_name}_p'] = ref_p
                    row[f'refutation_{test_name}_passed'] = passed
                    
                    # passed can genuinely be None (undetermined, e.g. when
                    # the refuter returned no new_effect) since the pass/fail
                    # logic in treatment_effects.py was fixed to distinguish
                    # that from an actual failure - don't collapse it to FAIL.
                    status = 'PASS' if passed is True else ('FAIL' if passed is False else 'UNDETERMINED')
                    ref_p_str = f"{ref_p:.4f}" if ref_p is not None else 'N/A'
                    print(f"  Refutation [{test_name}]: p={ref_p_str}, {status}")
                
                results.append(row)
                pair_count += 1
                
            except Exception as e:
                logger.error(f"Failed to estimate {treatment} -> {outcome}: {e}")
                results.append({
                    'treatment': treatment,
                    'outcome': outcome,
                    'method': 'error',
                    'ate': None,
                    'error': str(e)
                })
                pair_count += 1
    
    df = pd.DataFrame(results)
    
    # Summary statistics
    print(f"\n{'=' * 60}")
    print("CAUSAL EVALUATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total pairs evaluated: {len(df)}")
    
    if 'p_value' in df.columns:
        significant = df[df['p_value'].notna() & (df['p_value'] < 0.05)]
    else:
        # Every pair errored out (e.g. no valid data for any treatment/
        # outcome pair) - nothing to summarize, but don't crash the run over it.
        logger.warning("No pair produced a p_value - all estimations failed")
        significant = pd.DataFrame()
    print(f"Statistically significant (p < 0.05): {len(significant)}")
    
    if len(significant) > 0:
        print("\nSignificant causal relationships:")
        for _, row in significant.iterrows():
            print(f"  {row['treatment']} -> {row['outcome']}: ATE={row['ate']:.6f}, p={row['p_value']:.6f}")
    
    return df


def compute_cate_table(
    train_end_date: str = '2021-04-30'
) -> pd.DataFrame:
    """
    Compute CATE (Conditional Average Treatment Effect) for each sector.
    
    Uses LinearDML from EconML to estimate heterogeneous effects.
    
    Returns:
        DataFrame with CATE stats per sector per treatment
    """
    from app.services.data_pipeline import get_pipeline
    
    pipeline = get_pipeline()
    feature_matrix = pipeline.load_data('feature_matrix')
    
    if feature_matrix is None:
        return pd.DataFrame({'error': ['No data']})
    
    train_data = feature_matrix[feature_matrix.index <= train_end_date]
    
    try:
        from econml.dml import LinearDML
        from sklearn.ensemble import RandomForestRegressor
    except ImportError:
        logger.warning("EconML not available for CATE estimation")
        return pd.DataFrame({'error': ['EconML not installed']})
    
    # Find available columns
    return_cols = [c for c in train_data.columns if 'Return_1d' in c]
    change_cols = [c for c in train_data.columns if 'Change' in c]
    confounders = [c for c in train_data.columns 
                   if c not in return_cols and c not in change_cols 
                   and train_data[c].dtype in ['float64', 'float32', 'int64']]
    
    if not return_cols or not change_cols:
        return pd.DataFrame({'error': ['No return/change columns found']})
    
    # Use primary treatment
    treatment = change_cols[0] if change_cols else None
    
    results = []
    
    for outcome in return_cols:
        analysis_data = train_data[[treatment, outcome] + confounders[:10]].dropna()
        
        if len(analysis_data) < 100:
            continue
        
        Y = analysis_data[outcome].values
        T = analysis_data[treatment].values
        X = analysis_data[confounders[:10]].values
        
        try:
            dml = LinearDML(
                model_y=RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42),
                model_t=RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42),
                random_state=42,
                cv=3
            )
            dml.fit(Y, T, X=X)
            
            cate = dml.effect(X)
            
            sector = outcome.replace('_Return_1d', '')
            results.append({
                'sector': sector,
                'treatment': treatment,
                'cate_mean': round(float(np.mean(cate)), 6),
                'cate_std': round(float(np.std(cate)), 6),
                'cate_5th': round(float(np.percentile(cate, 5)), 6),
                'cate_95th': round(float(np.percentile(cate, 95)), 6),
                'cate_median': round(float(np.median(cate)), 6),
                'n_samples': len(cate),
            })
            
        except Exception as e:
            logger.error(f"CATE estimation failed for {outcome}: {e}")
            results.append({
                'sector': outcome.replace('_Return_1d', ''),
                'treatment': treatment,
                'error': str(e),
            })
    
    return pd.DataFrame(results)
