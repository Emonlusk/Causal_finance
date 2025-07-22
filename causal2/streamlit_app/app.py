import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import networkx as nx
from src.causal_models import estimate_cate
from src.portfolio_builder import causal_portfolio_weights, backtest_portfolio

st.title("Causal Portfolio Optimization Dashboard")

# Upload data
data_file = st.file_uploader("Upload processed data (parquet)", type=["parquet"])
if data_file:
    df = pd.read_parquet(data_file)
    st.write(df.head())

    # DAG visualization (placeholder)
    st.subheader("Causal DAG")
    # ... code to display DAG ...

    # Treatment effect simulation
    st.subheader("Treatment Effect Simulator")
    rate_change = st.slider("Fed Rate Change (%)", -2, 2, 0)
    # ... code to run CATE estimation ...

    # Portfolio construction
    st.subheader("Portfolio Weights")
    # ... code to show weights and backtest results ... 