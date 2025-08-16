from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_pipeline import get_sample_data, process_data
from src.causal_models import estimate_cate
from src.portfolio_builder import causal_portfolio_weights, markowitz_weights

app = FastAPI(
    title="Causal Finance API",
    description="API for causal portfolio optimization",
    version="1.0.0"
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to Causal Finance API",
        "version": "1.0.0",
        "endpoints": [
            "/api/sample-data",
            "/api/upload",
            "/api/simulate",
            "/api/portfolio",
            "/api/backtest"
        ]
    }

@app.get("/api/sample-data")
async def get_sample_dataset():
    try:
        df = get_sample_data()
        return {
            "status": "success",
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_data(file: UploadFile):
    try:
        # Read the uploaded file
        if file.filename.endswith('.parquet'):
            df = pd.read_parquet(file.file)
        elif file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Validate data structure
        required_columns = ['date', 'symbol', 'price', 'return', 'volume']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail="Missing required columns")
        
        return {
            "status": "success",
            "data": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate")
async def simulate_effects(fed_rate: float):
    try:
        df = get_sample_data()  # In production, this would use real data
        cate, assets = estimate_cate(df)
        
        return {
            "status": "success",
            "effects": {
                asset: effect * (fed_rate/100)
                for asset, effect in zip(assets, cate)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio")
async def generate_portfolio(allow_short: bool = False):
    try:
        df = get_sample_data()  # In production, this would use real data
        cate, assets = estimate_cate(df)
        
        # Generate portfolio weights
        causal_weights = causal_portfolio_weights(cate, allow_short)
        
        # Calculate Markowitz weights for comparison
        returns = df[[col for col in df.columns if col != 'fed_rate']].values
        mean_returns = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns, rowvar=False)
        markowitz = markowitz_weights(mean_returns, cov_matrix)
        
        return {
            "status": "success",
            "causal_weights": dict(zip(assets, causal_weights)),
            "markowitz_weights": dict(zip(assets, markowitz))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backtest")
async def run_backtest():
    try:
        df = get_sample_data()  # In production, this would use real data
        cate, assets = estimate_cate(df)
        
        # Generate portfolio weights
        causal_weights = causal_portfolio_weights(cate)
        markowitz_weights_data = markowitz_weights(
            df[[col for col in df.columns if col != 'fed_rate']].mean().values,
            df[[col for col in df.columns if col != 'fed_rate']].cov().values
        )
        
        # Run backtests
        causal_returns = backtest_portfolio(causal_weights, df[assets])
        markowitz_returns = backtest_portfolio(markowitz_weights_data, df[assets])
        
        return {
            "status": "success",
            "causal_returns": causal_returns.to_dict(),
            "markowitz_returns": markowitz_returns.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
