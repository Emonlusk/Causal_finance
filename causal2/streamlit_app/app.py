import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from src.data_pipeline import get_sample_data
from src.causal_models import estimate_cate
from src.visualization import get_dag_graph
from src.portfolio_builder import causal_portfolio_weights, markowitz_weights, backtest_portfolio

st.title("Causal Portfolio Optimization Dashboard")

# Option to use sample generated data or uploaded file
data_source = st.radio("Choose Data Source:", ("Use Sample Data", "Upload Data (parquet)"))
if data_source == "Upload Data (parquet)":
    data_file = st.file_uploader("Upload processed data (parquet)", type=["parquet"])
    if data_file:
        df = pd.read_parquet(data_file)
else:
    df = get_sample_data()
    
if df is not None:
    st.write("Data Preview", df.head())

    # DAG visualization
    st.subheader("Causal DAG")
    G = get_dag_graph()
    plt.figure(figsize=(5, 4))
    pos = nx.spring_layout(G)
    nx.draw_networkx(G, pos, with_labels=True, node_color='lightblue', edge_color='gray')
    st.pyplot(plt)

    # Treatment effect simulation
    st.subheader("Treatment Effect Simulator")
    rate_change = st.slider("Fed Rate Change (%)", -2, 2, 0)
    # For demonstration, we won't incorporate slider input into cate estimation.
    cate, assets = estimate_cate(df)
    st.write("Estimated CATEs:", dict(zip(assets, cate)))

    # Portfolio construction using causal weights
    st.subheader("Portfolio Weights (Exponential Weighting)")
    weights = causal_portfolio_weights(cate, allow_short=False)
    portfolio = dict(zip(assets, weights))
    st.write("Portfolio Weights:", portfolio)

    # Backtesting portfolio on sample returns
    st.subheader("Backtest Portfolio")
    port_returns = backtest_portfolio(weights, df[assets])
    st.line_chart(port_returns)
    
    # Markowitz portfolio example
    st.subheader("Markowitz Optimal Weights")
    # For a simple demo, use mean returns from df and covariance matrix
    mean_returns = df[assets].mean().values
    cov_matrix = df[assets].cov().values
    m_weights = markowitz_weights(mean_returns, cov_matrix, risk_aversion=0.5)
    st.write("Markowitz Weights:", dict(zip(assets, m_weights)))