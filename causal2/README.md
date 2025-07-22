# Causal Portfolio Optimization System

This project implements a full Causal AI pipeline for portfolio optimization, from data collection to deployment. The codebase is organized according to best practices and covers all six phases:

1. **Data Collection & Preprocessing**
2. **Causal Graph Construction (DAG)**
3. **ATE Estimation**
4. **CATE Estimation**
5. **Portfolio Construction**
6. **Deployment (Streamlit, Docker, CI/CD)**

## Directory Structure

```
causal-portfolio/
├── data/
│   ├── raw/                   # Original CSVs (if any)
│   └── processed/             # Parquet files (from causal/data)
├── notebooks/
│   ├── 01_eda.ipynb           # Data exploration (add as needed)
│   └── 02_dag_validation.ipynb
├── src/
│   ├── data_pipeline.py       # Automated data fetcher, preprocessing
│   ├── causal_models.py       # DoWhy/EconML wrappers, ATE/CATE
│   ├── portfolio_builder.py   # Weight optimization, backtest
│   └── visualization.py       # Plotting, DAG viz
├── tests/
├── streamlit_app/
│   └── app.py                 # Dashboard code
├── Dockerfile
├── .github/workflows/ci.yml   # CI pipeline
├── requirements.txt           # Pinned dependencies
├── finance_dag.png            # DAG image
├── dag_assumption_report.txt  # DAG assumptions
```

See each phase's code and documentation in the respective files. 