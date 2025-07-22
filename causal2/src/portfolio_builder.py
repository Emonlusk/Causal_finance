import numpy as np
import pandas as pd
from scipy.optimize import minimize

def causal_portfolio_weights(cate, allow_short=False):
    """
    Convert CATEs to portfolio weights using exponential weighting.
    cate: np.array of CATEs per asset
    allow_short: if True, allow negative weights (shorting)
    """
    if not allow_short:
        cate = np.clip(cate, 0, None)  # No shorting
    exp_cate = np.exp(cate)
    weights = exp_cate / exp_cate.sum()
    return weights

def markowitz_weights(returns, cov_matrix, risk_aversion=1.0):
    """
    Compute Markowitz mean-variance optimal weights.
    returns: expected returns vector
    cov_matrix: covariance matrix
    risk_aversion: lambda parameter
    """
    n = len(returns)
    def objective(w):
        return -w @ returns + risk_aversion * w @ cov_matrix @ w
    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
    bounds = [(0, 1) for _ in range(n)]
    res = minimize(objective, np.ones(n)/n, bounds=bounds, constraints=constraints)
    return res.x

def backtest_portfolio(weights, returns_df):
    """
    Backtest portfolio given weights and returns DataFrame.
    weights: np.array of portfolio weights
    returns_df: DataFrame of asset returns (rows: time, cols: assets)
    Returns: portfolio returns series
    """
    port_ret = returns_df @ weights
    return port_ret 