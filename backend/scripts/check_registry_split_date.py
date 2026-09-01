"""
Check: Global Model Train/Test Split Boundary Date
=====================================================
Reproduces the row-index -> calendar-date computation for the original
globally-trained treatment-effects model's 80/20 train/test split, exactly
mirroring MLTrainingPipeline.run_full_pipeline's split logic
(app/services/ml_training_pipeline.py:283-285):

    split_idx = int(len(feature_matrix) * (1 - train_test_split))  # train_test_split=0.2
    train_data = feature_matrix.iloc[:split_idx]
    test_data = feature_matrix.iloc[split_idx:]

paper.tex Section 4.6 states this boundary falls at 2023-03-07 (claim #15 in
research_paper/claims_to_evidence.md, previously a one-off unsaved
computation). This script persists the computation and its output.

Usage:
    cd backend
    python scripts/check_registry_split_date.py
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'results')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

TRAIN_TEST_SPLIT = 0.2  # matches MLTrainingPipeline.run_full_pipeline's default


def compute_split_date() -> dict:
    import pandas as pd

    feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
    feature_matrix = pd.read_parquet(feature_path)

    n_rows = len(feature_matrix)
    split_idx = int(n_rows * (1 - TRAIN_TEST_SPLIT))

    train_data = feature_matrix.iloc[:split_idx]
    test_data = feature_matrix.iloc[split_idx:]

    result = {
        'n_rows': n_rows,
        'train_test_split': TRAIN_TEST_SPLIT,
        'split_idx': split_idx,
        'split_date': str(train_data.index[-1].date()),
        'first_test_date': str(test_data.index[0].date()),
        'train_start_date': str(train_data.index[0].date()),
        'test_end_date': str(test_data.index[-1].date()),
        'n_train_rows': len(train_data),
        'n_test_rows': len(test_data),
    }
    return result


if __name__ == '__main__':
    os.makedirs(RESULTS_DIR, exist_ok=True)
    result = compute_split_date()

    print("Global model 80/20 train/test split boundary:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    out_path = os.path.join(RESULTS_DIR, 'registry_split_date_check.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved: {out_path}")
