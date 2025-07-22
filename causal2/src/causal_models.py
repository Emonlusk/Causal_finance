import pandas as pd
import numpy as np
from dowhy import CausalModel
from econml.dml import CausalForestDML
from sklearn.ensemble import RandomForestRegressor

# --- Data Preparation Helper ---
def load_merged_data(path='data/processed/merged_for_causal.parquet'):
    """Load merged data for causal analysis."""
    return pd.read_parquet(path)

# --- Phase 3: ATE Estimation (DoWhy) ---
def estimate_ate(df, treatment, outcome, common_causes=None, instruments=None, graph=None):
    """
    Estimate Average Treatment Effect (ATE) using DoWhy.
    df: DataFrame with all variables
    treatment: str, treatment variable name
    outcome: str, outcome variable name
    common_causes: list of str, confounders
    instruments: list of str, IVs (optional)
    graph: str, optional DOT format DAG
    Returns: model, identified estimand, estimate
    """
    model = CausalModel(
        data=df,
        treatment=treatment,
        outcome=outcome,
        common_causes=common_causes,
        instruments=instruments,
        graph=graph
    )
    estimand = model.identify_effect()
    estimate = model.estimate_effect(estimand, method_name="backdoor.linear_regression")
    return model, estimand, estimate

# --- Phase 4: CATE Estimation (EconML CausalForestDML) ---
def estimate_cate(X, T, Y, random_state=42):
    """
    Estimate Conditional Average Treatment Effects (CATE) using EconML's CausalForestDML.
    X: Covariates (e.g., firm size, sector)
    T: Treatment (e.g., rate change)
    Y: Outcome (e.g., returns)
    Returns: fitted model, CATE estimates
    """
    X_proc = pd.get_dummies(X, drop_first=True)
    est = CausalForestDML(
        model_t=RandomForestRegressor(n_estimators=100, min_samples_leaf=10, random_state=random_state),
        model_y=RandomForestRegressor(n_estimators=100, min_samples_leaf=10, random_state=random_state),
        n_estimators=100,
        min_samples_leaf=5,
        random_state=random_state,
        verbose=0
    )
    est.fit(Y, T, X=X_proc)
    cate = est.effect(X_proc)
    return est, cate

# --- Example Usage (for testing, not run on import) ---
if __name__ == "__main__":
    # Example: Load data and estimate ATE
    df = load_merged_data()
    model, estimand, estimate = estimate_ate(
        df,
        treatment='FedRate',
        outcome='SP500',
        common_causes=['GDP', 'CPI', 'UNRATE']
    )
    print("ATE estimate:", estimate.value)
    # Example: Estimate CATE
    X = df[['GDP', 'CPI', 'UNRATE']]
    T = df['FedRate']
    Y = df['SP500']
    est, cate = estimate_cate(X, T, Y)
    print("CATE (first 5):", cate[:5])