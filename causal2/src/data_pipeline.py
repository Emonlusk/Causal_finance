import yfinance as yf
import pandas as pd
import pandas_datareader.data as web
import numpy as np
from datetime import datetime
from statsmodels.tsa.stattools import adfuller
import os
from typing import Dict, Any, List, Tuple

# Configuration
SNP500_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BRK-B', 'NVDA', 'JPM', 'JNJ'
]

MACRO_VARS = {
    'GDP': {'source': 'fred', 'symbol': 'GDP'},
    'CPI': {'source': 'fred', 'symbol': 'CPIAUCSL'},
    'UNRATE': {'source': 'fred', 'symbol': 'UNRATE'},
}

START_DATE = '2000-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PARQUET_VERSION = 'v1'

def fetch_equity_data(tickers: List[str] = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Fetch equity data from Yahoo Finance
    """
    try:
        tickers = tickers or SNP500_TICKERS
        start_date = start_date or START_DATE
        end_date = end_date or END_DATE

        print(f"Fetching data for {len(tickers)} tickers...")
        data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', auto_adjust=True)
        
        if data.empty:
            raise ValueError("No data retrieved from Yahoo Finance")
            
        print(f"Successfully fetched data. Shape: {data.shape}")
        return data
    except Exception as e:
        print(f"Error fetching equity data: {str(e)}")
        return pd.DataFrame()

def get_sample_data(num_assets: int = 5, num_days: int = 100) -> pd.DataFrame:
    """
    Generate sample data with asset returns and macro variables for testing.
    """
    try:
        dates = pd.date_range(end=datetime.now(), periods=num_days)
        data = {}
        
        # Generate asset returns with realistic parameters
        for i in range(num_assets):
            # Simulate daily returns with annual vol of ~20%
            data[f"asset_{i+1}"] = np.random.normal(0.0001, 0.01, size=num_days)
        
        # Generate macro variables
        data["fed_rate"] = np.random.normal(0.02, 0.001, size=num_days)  # Federal funds rate
        data["inflation"] = np.random.normal(0.02, 0.002, size=num_days)  # CPI
        data["gdp_growth"] = np.random.normal(0.025, 0.003, size=num_days)  # GDP growth
        data["unemployment"] = np.random.normal(0.05, 0.002, size=num_days)  # Unemployment rate
        
        df = pd.DataFrame(data, index=dates)
        
        # Ensure data is properly sorted and has no missing values
        df = df.sort_index().fillna(method='ffill')
        
        return df
    except Exception as e:
        print(f"Error generating sample data: {str(e)}")
        return pd.DataFrame()

def fetch_macro_data(start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
    """
    Fetch macroeconomic data from FRED
    """
    try:
        start_date = start_date or START_DATE
        end_date = end_date or END_DATE
        macro = {}

        print("Fetching macro data...")
        for var, info in MACRO_VARS.items():
            try:
                df = web.DataReader(info['symbol'], info['source'], start_date, end_date)
                if not df.empty:
                    macro[var] = df
                    print(f"Successfully fetched {var} data")
                else:
                    print(f"Warning: No data retrieved for {var}")
            except Exception as e:
                print(f"Error fetching {var}: {str(e)}")
                continue

        if not macro:
            raise ValueError("No macro data could be retrieved")

        return macro
    except Exception as e:
        print(f"Error in macro data fetch: {str(e)}")
        return {}

def compute_log_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute log returns for a DataFrame of asset prices.
    Handles missing values and validates input/output.
    """
    try:
        if df.empty:
            raise ValueError("Empty DataFrame provided")
            
        # Remove any zero or negative values that would cause issues with log returns
        df = df[df > 0]
        
        # Compute log returns
        log_returns = np.log(df / df.shift(1))
        
        # Remove infinite values that might occur from division
        log_returns = log_returns.replace([np.inf, -np.inf], np.nan)
        
        # Forward fill any remaining NaN values
        log_returns = log_returns.fillna(method='ffill')
        
        if log_returns.empty:
            raise ValueError("Log returns calculation resulted in empty DataFrame")
            
        return log_returns
    except Exception as e:
        print(f"Error computing log returns: {str(e)}")
        return pd.DataFrame()

def align_frequency(equity_df: pd.DataFrame, macro_dict: Dict[str, pd.DataFrame], 
                   freq: str = 'B') -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    Align the frequency of equity data to macro data by resampling and forward filling.
    Args:
        equity_df: DataFrame with equity data
        macro_dict: Dictionary of DataFrames with macro data
        freq: Frequency to align to ('B' for business daily, 'M' for monthly, etc.)
    """
    try:
        if equity_df.empty:
            raise ValueError("Empty equity DataFrame provided")
        if not macro_dict:
            raise ValueError("Empty macro data dictionary provided")

        # Resample and align macro data
        aligned = {}
        for var, df in macro_dict.items():
            # Resample to desired frequency
            df_resampled = df.resample(freq).last()
            # Forward fill missing values
            df_resampled = df_resampled.fillna(method='ffill')
            aligned[var] = df_resampled

        # Resample equity data to the same frequency
        equity_resampled = equity_df.resample(freq).last()

        # Find common date range
        all_indices = [equity_resampled.index] + [df.index for df in aligned.values()]
        common_idx = all_indices[0]
        for idx in all_indices[1:]:
            common_idx = common_idx.intersection(idx)

        # Align all data to common dates
        equity_aligned = equity_resampled.loc[common_idx]
        aligned = {var: df.loc[common_idx] for var, df in aligned.items()}

        # Validate output
        if equity_aligned.empty:
            raise ValueError("Alignment resulted in empty DataFrame")

        return equity_aligned, aligned
    except Exception as e:
        print(f"Error aligning data frequencies: {str(e)}")
        return pd.DataFrame(), {}


def check_stationarity(df: pd.DataFrame, alpha: float = 0.05) -> Dict[str, bool]:
    """
    Check if the time series in each column of the DataFrame is stationary
    using the Augmented Dickey-Fuller test.
    
    Returns:
        Dictionary with column names as keys and boolean values indicating stationarity
    """
    try:
        if df.empty:
            raise ValueError("Empty DataFrame provided")
            
        results = {}
        for column in df.columns:
            series = df[column].dropna()
            if len(series) < 10:  # Need sufficient data points for the test
                print(f"Warning: Insufficient data points for stationarity test in {column}")
                results[column] = False
                continue
                
            try:
                stat_test = adfuller(series)
                results[column] = stat_test[1] < alpha  # p-value < alpha => stationary
            except Exception as e:
                print(f"Error testing stationarity for {column}: {str(e)}")
                results[column] = False
                
        return results
    except Exception as e:
        print(f"Error checking stationarity: {str(e)}")
        return {}

def save_parquet(df: pd.DataFrame, name: str, version: str = 'v1', 
                data_dir: str = PROCESSED_DIR) -> str:
    """
    Save the DataFrame as a parquet file with error handling
    """
    try:
        if df.empty:
            raise ValueError(f"Empty DataFrame provided for {name}")
            
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
            
        # Create file path
        path = os.path.join(data_dir, f"{name}_{version}.parquet")
        
        # Save file
        df.to_parquet(path)
        print(f"Successfully saved {name} to {path}")
        
        return path
    except Exception as e:
        print(f"Error saving parquet file {name}: {str(e)}")
        return ""

def ensure_dir(path: str) -> bool:
    """
    Ensure that the directory exists; if not, create it.
    Returns True if successful, False otherwise.
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {path}: {str(e)}")
        return False

def process_data(start_date: str = None, end_date: str = None, 
              tickers: List[str] = None) -> Dict[str, pd.DataFrame]:
    """
    Main function to process all data and prepare it for causal analysis
    """
    try:
        # Initialize directories
        for directory in [DATA_DIR, PROCESSED_DIR, RAW_DIR]:
            if not ensure_dir(directory):
                raise RuntimeError(f"Failed to create directory: {directory}")

        # Fetch data
        print("\nFetching equity data...")
        eq_data = fetch_equity_data(tickers, start_date, end_date)
        if eq_data.empty:
            raise ValueError("Failed to fetch equity data")

        print("\nFetching macro data...")
        macro_data = fetch_macro_data(start_date, end_date)
        if not macro_data:
            raise ValueError("Failed to fetch macro data")

        # Process equity data
        print("\nProcessing equity data...")
        eq_close = eq_data.xs('Close', axis=1, level=1)
        eq_returns = compute_log_returns(eq_close)
        eq_returns = eq_returns.dropna(how='all')

        # Check stationarity
        print("\nChecking stationarity...")
        stationarity_results = check_stationarity(eq_returns)
        non_stationary = [col for col, is_stationary in stationarity_results.items() 
                         if not is_stationary]
        
        if non_stationary:
            print(f"\nWarning: Non-stationary series detected: {non_stationary}")
            print("Taking first difference of non-stationary series...")
            eq_returns[non_stationary] = eq_returns[non_stationary].diff()

        # Align frequencies
        print("\nAligning frequencies...")
        eq_aligned, macro_aligned = align_frequency(eq_returns, macro_data)

        # Save processed data
        print("\nSaving processed data...")
        save_parquet(eq_aligned, 'sp500_logret', PARQUET_VERSION)
        for var, df in macro_aligned.items():
            save_parquet(df, var, PARQUET_VERSION)

        # Merge all data for causal analysis
        print("\nMerging data...")
        merged_data = eq_aligned.copy()
        for var, df in macro_aligned.items():
            # Assuming each macro DataFrame has one main column
            merged_data[var] = df.iloc[:, 0]

        # Save merged dataset
        save_parquet(merged_data, 'merged_for_causal', PARQUET_VERSION)

        print("\nData processing completed successfully!")
        return {
            'equity': eq_aligned,
            'macro': macro_aligned,
            'merged': merged_data
        }

    except Exception as e:
        print(f"\nError in data processing: {str(e)}")
        return {}

if __name__ == "__main__":
    # Example usage
    data = process_data(
        start_date='2020-01-01',
        end_date=datetime.now().strftime('%Y-%m-%d'),
        tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    )