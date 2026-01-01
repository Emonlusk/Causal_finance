"""
Data Pipeline Service
=====================
Automated fetching, processing, and storage of historical market and macroeconomic data
for training causal inference and ML models.

Data Sources:
- Yahoo Finance: Sector ETFs, Market Indices, VIX
- FRED API: Fed Funds Rate, CPI, GDP, Unemployment, Treasury Yields
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
from functools import lru_cache

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================

# Sector ETF tickers and their corresponding sectors
SECTOR_ETFS = {
    'XLK': 'Technology',
    'XLV': 'Healthcare', 
    'XLE': 'Energy',
    'XLF': 'Financials',
    'XLI': 'Industrials',
    'XLY': 'Consumer_Discretionary',
    'XLP': 'Consumer_Staples',
    'XLU': 'Utilities',
    'XLB': 'Materials',
    'XLRE': 'Real_Estate',
    'XLC': 'Communication_Services'
}

# Market indices
MARKET_INDICES = {
    'SPY': 'SP500',
    '^VIX': 'VIX',
    '^TNX': 'Treasury_10Y',
    '^TYX': 'Treasury_30Y',
    '^IRX': 'Treasury_3M',
}

# FRED series for macroeconomic indicators
FRED_SERIES = {
    'FEDFUNDS': 'Fed_Funds_Rate',
    'CPIAUCSL': 'CPI',
    'GDP': 'GDP',
    'UNRATE': 'Unemployment_Rate',
    'DGS10': 'Treasury_10Y_Yield',
    'DGS2': 'Treasury_2Y_Yield',
    'T10Y2Y': 'Yield_Curve_Spread',
    'DCOILWTICO': 'Oil_WTI',
    'GOLDAMGBD228NLBM': 'Gold_Price',
    'UMCSENT': 'Consumer_Sentiment',
    'INDPRO': 'Industrial_Production',
    'HOUST': 'Housing_Starts',
    'M2SL': 'M2_Money_Supply',
}

# Data storage paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
RAW_DATA_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, 'processed')
MODELS_DIR = os.path.join(DATA_DIR, 'models')


class DataPipeline:
    """
    Main data pipeline for fetching, processing, and storing financial data.
    Handles both market data (yfinance) and macroeconomic data (FRED).
    """
    
    def __init__(self, fred_api_key: Optional[str] = None):
        """
        Initialize the data pipeline.
        
        Args:
            fred_api_key: FRED API key for macroeconomic data
        """
        self.fred_api_key = fred_api_key or os.getenv('FRED_API_KEY')
        self._fred = None
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary data directories if they don't exist."""
        for directory in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, MODELS_DIR]:
            os.makedirs(directory, exist_ok=True)
    
    @property
    def fred(self):
        """Lazy load FRED API client."""
        if self._fred is None and self.fred_api_key:
            try:
                from fredapi import Fred
                self._fred = Fred(api_key=self.fred_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize FRED API: {e}")
        return self._fred
    
    # ============================================
    # DATA FETCHING
    # ============================================
    
    def fetch_sector_etf_data(
        self, 
        start_date: str = '2010-01-01',
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch historical price data for all sector ETFs.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date (defaults to today)
            
        Returns:
            DataFrame with columns: Date, Ticker, Open, High, Low, Close, Volume, Sector
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching sector ETF data from {start_date} to {end_date}")
        
        all_data = []
        tickers = list(SECTOR_ETFS.keys())
        
        try:
            # Batch download for efficiency
            data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker', progress=False)
            
            for ticker, sector in SECTOR_ETFS.items():
                try:
                    if ticker in data.columns.get_level_values(0):
                        ticker_data = data[ticker].copy()
                        ticker_data['Ticker'] = ticker
                        ticker_data['Sector'] = sector
                        ticker_data = ticker_data.reset_index()
                        all_data.append(ticker_data)
                except Exception as e:
                    logger.warning(f"Error processing {ticker}: {e}")
            
            if all_data:
                result = pd.concat(all_data, ignore_index=True)
                result.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume', 'Ticker', 'Sector']
                return result
            
        except Exception as e:
            logger.error(f"Error fetching sector ETF data: {e}")
        
        return pd.DataFrame()
    
    def fetch_market_indices(
        self,
        start_date: str = '2010-01-01',
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch market index data (SPY, VIX, Treasury yields).
        
        Returns:
            DataFrame with Date as index and index values as columns
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching market indices from {start_date} to {end_date}")
        
        result_df = pd.DataFrame()
        
        for ticker, name in MARKET_INDICES.items():
            try:
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if not data.empty:
                    result_df[name] = data['Close']
            except Exception as e:
                logger.warning(f"Error fetching {ticker}: {e}")
        
        return result_df
    
    def fetch_fred_data(
        self,
        start_date: str = '2010-01-01',
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch macroeconomic data from FRED.
        
        Returns:
            DataFrame with Date as index and macro indicators as columns
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if not self.fred:
            logger.warning("FRED API not available, using fallback data")
            return self._generate_synthetic_macro_data(start_date, end_date)
        
        logger.info(f"Fetching FRED data from {start_date} to {end_date}")
        
        result_df = pd.DataFrame()
        
        for series_id, name in FRED_SERIES.items():
            try:
                data = self.fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
                if data is not None and len(data) > 0:
                    result_df[name] = data
            except Exception as e:
                logger.warning(f"Error fetching FRED series {series_id}: {e}")
        
        return result_df
    
    def _generate_synthetic_macro_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Generate synthetic macro data when FRED is unavailable."""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        n = len(dates)
        
        np.random.seed(42)
        
        # Generate realistic-looking macro data
        data = {
            'Fed_Funds_Rate': np.cumsum(np.random.randn(n) * 0.01) + 2.0,
            'CPI': np.cumsum(np.random.randn(n) * 0.05) + 250,
            'GDP': np.cumsum(np.random.randn(n) * 50) + 20000,
            'Unemployment_Rate': np.clip(np.cumsum(np.random.randn(n) * 0.02) + 5.0, 3, 15),
            'Treasury_10Y_Yield': np.clip(np.cumsum(np.random.randn(n) * 0.01) + 3.0, 0.5, 8),
            'Treasury_2Y_Yield': np.clip(np.cumsum(np.random.randn(n) * 0.01) + 2.5, 0.2, 7),
            'Oil_WTI': np.clip(np.cumsum(np.random.randn(n) * 0.5) + 60, 20, 150),
            'Consumer_Sentiment': np.clip(np.cumsum(np.random.randn(n) * 0.5) + 80, 50, 120),
        }
        
        df = pd.DataFrame(data, index=dates)
        df['Yield_Curve_Spread'] = df['Treasury_10Y_Yield'] - df['Treasury_2Y_Yield']
        
        return df
    
    # ============================================
    # DATA PROCESSING
    # ============================================
    
    def compute_returns(
        self, 
        price_data: pd.DataFrame,
        price_col: str = 'Close',
        periods: List[int] = [1, 5, 21, 63, 252]
    ) -> pd.DataFrame:
        """
        Compute log returns for multiple periods.
        
        Args:
            price_data: DataFrame with price data
            price_col: Column name for prices
            periods: List of periods for return calculation (1=daily, 5=weekly, 21=monthly, etc.)
            
        Returns:
            DataFrame with return columns added
        """
        df = price_data.copy()
        
        for period in periods:
            col_name = f'Return_{period}d'
            df[col_name] = np.log(df[price_col] / df[price_col].shift(period))
        
        return df
    
    def compute_volatility(
        self,
        returns: pd.Series,
        windows: List[int] = [21, 63, 252]
    ) -> pd.DataFrame:
        """
        Compute rolling volatility for multiple windows.
        
        Args:
            returns: Series of returns
            windows: Rolling window sizes
            
        Returns:
            DataFrame with volatility columns
        """
        result = pd.DataFrame(index=returns.index)
        
        for window in windows:
            result[f'Volatility_{window}d'] = returns.rolling(window=window).std() * np.sqrt(252)
        
        return result
    
    def compute_technical_indicators(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute technical indicators for ML features.
        
        Args:
            price_data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with technical indicators
        """
        df = price_data.copy()
        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        
        # Moving Averages
        for window in [10, 20, 50, 200]:
            df[f'SMA_{window}'] = close.rolling(window=window).mean()
            df[f'EMA_{window}'] = close.ewm(span=window, adjust=False).mean()
        
        # Relative Strength Index (RSI)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        df['BB_Upper'] = sma20 + (std20 * 2)
        df['BB_Lower'] = sma20 - (std20 * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / sma20
        
        # Average True Range (ATR)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(window=14).mean()
        
        # Volume indicators
        df['Volume_SMA_20'] = volume.rolling(window=20).mean()
        df['Volume_Ratio'] = volume / df['Volume_SMA_20']
        
        # Price momentum
        df['Momentum_10'] = close / close.shift(10) - 1
        df['Momentum_20'] = close / close.shift(20) - 1
        
        return df
    
    def create_features_matrix(
        self,
        sector_data: pd.DataFrame,
        macro_data: pd.DataFrame,
        market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create unified feature matrix for ML models.
        
        Combines:
        - Sector ETF returns and technicals
        - Macroeconomic indicators
        - Market indices (VIX, Treasury yields)
        
        Returns:
            DataFrame with all features aligned by date
        """
        logger.info("Creating unified feature matrix")
        
        # Process sector data - pivot to wide format
        sector_returns = sector_data.pivot_table(
            index='Date',
            columns='Sector',
            values='Close',
            aggfunc='last'
        )
        
        # Compute returns for each sector
        for col in sector_returns.columns:
            sector_returns[f'{col}_Return_1d'] = np.log(sector_returns[col] / sector_returns[col].shift(1))
            sector_returns[f'{col}_Return_5d'] = np.log(sector_returns[col] / sector_returns[col].shift(5))
            sector_returns[f'{col}_Return_21d'] = np.log(sector_returns[col] / sector_returns[col].shift(21))
        
        # Drop price columns, keep only returns
        return_cols = [c for c in sector_returns.columns if 'Return' in c]
        sector_returns = sector_returns[return_cols]
        
        # Resample macro data to daily (forward fill)
        macro_daily = macro_data.resample('D').ffill()
        
        # Compute macro changes
        for col in macro_daily.columns:
            macro_daily[f'{col}_Change'] = macro_daily[col].pct_change()
            macro_daily[f'{col}_Change_21d'] = macro_daily[col].pct_change(periods=21)
        
        # Add market data
        market_daily = market_data.copy()
        if 'VIX' in market_daily.columns:
            market_daily['VIX_Change'] = market_daily['VIX'].pct_change()
            market_daily['VIX_MA_10'] = market_daily['VIX'].rolling(10).mean()
        
        if 'SP500' in market_daily.columns:
            market_daily['SP500_Return'] = np.log(market_daily['SP500'] / market_daily['SP500'].shift(1))
            market_daily['SP500_Volatility_21d'] = market_daily['SP500_Return'].rolling(21).std() * np.sqrt(252)
        
        # Merge all data
        features = sector_returns.join(macro_daily, how='outer')
        features = features.join(market_daily, how='outer')
        
        # Forward fill then backward fill remaining NaNs
        features = features.ffill().bfill()
        
        # Drop rows with any NaN
        features = features.dropna()
        
        logger.info(f"Created feature matrix with shape {features.shape}")
        
        return features
    
    # ============================================
    # DATA STORAGE
    # ============================================
    
    def save_data(self, df: pd.DataFrame, filename: str, processed: bool = True):
        """Save DataFrame to parquet file."""
        directory = PROCESSED_DATA_DIR if processed else RAW_DATA_DIR
        filepath = os.path.join(directory, f"{filename}.parquet")
        df.to_parquet(filepath)
        logger.info(f"Saved data to {filepath}")
    
    def load_data(self, filename: str, processed: bool = True) -> Optional[pd.DataFrame]:
        """Load DataFrame from parquet file."""
        directory = PROCESSED_DATA_DIR if processed else RAW_DATA_DIR
        filepath = os.path.join(directory, f"{filename}.parquet")
        
        if os.path.exists(filepath):
            return pd.read_parquet(filepath)
        return None
    
    def get_data_info(self) -> Dict:
        """Get information about stored data files."""
        info = {'raw': {}, 'processed': {}}
        
        for directory, key in [(RAW_DATA_DIR, 'raw'), (PROCESSED_DATA_DIR, 'processed')]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    if filename.endswith('.parquet'):
                        filepath = os.path.join(directory, filename)
                        stat = os.stat(filepath)
                        info[key][filename] = {
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        }
        
        return info
    
    # ============================================
    # FULL PIPELINE
    # ============================================
    
    def run_full_pipeline(
        self,
        start_date: str = '2010-01-01',
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Run the complete data pipeline:
        1. Fetch all data sources
        2. Process and compute features
        3. Save to disk
        
        Args:
            start_date: Start date for historical data
            end_date: End date (defaults to today)
            force_refresh: If True, re-fetch even if data exists
            
        Returns:
            Dictionary of processed DataFrames
        """
        logger.info("Starting full data pipeline")
        
        # Check for existing data
        if not force_refresh:
            existing = self.load_data('feature_matrix')
            if existing is not None:
                logger.info("Loading existing feature matrix")
                return {'feature_matrix': existing}
        
        # Fetch all data
        sector_data = self.fetch_sector_etf_data(start_date, end_date)
        market_data = self.fetch_market_indices(start_date, end_date)
        macro_data = self.fetch_fred_data(start_date, end_date)
        
        # Save raw data
        if not sector_data.empty:
            self.save_data(sector_data, 'sector_etfs_raw', processed=False)
        if not market_data.empty:
            self.save_data(market_data, 'market_indices_raw', processed=False)
        if not macro_data.empty:
            self.save_data(macro_data, 'macro_data_raw', processed=False)
        
        # Create feature matrix
        if not sector_data.empty and not market_data.empty:
            feature_matrix = self.create_features_matrix(sector_data, macro_data, market_data)
            self.save_data(feature_matrix, 'feature_matrix')
            
            logger.info("Data pipeline completed successfully")
            return {
                'sector_data': sector_data,
                'market_data': market_data,
                'macro_data': macro_data,
                'feature_matrix': feature_matrix
            }
        
        logger.warning("Data pipeline completed with missing data")
        return {}
    
    def get_training_data(
        self,
        target_sector: str = 'Technology',
        lookback_days: int = 252 * 5,  # 5 years
        target_horizon: int = 21  # 21-day forward return
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for ML model training.
        
        Args:
            target_sector: Sector to predict returns for
            lookback_days: How many days of history to use
            target_horizon: Forward return horizon in days
            
        Returns:
            Tuple of (X features, y target)
        """
        feature_matrix = self.load_data('feature_matrix')
        
        if feature_matrix is None:
            logger.warning("No feature matrix found, running pipeline")
            result = self.run_full_pipeline()
            feature_matrix = result.get('feature_matrix')
        
        if feature_matrix is None or feature_matrix.empty:
            raise ValueError("Could not load or create feature matrix")
        
        # Use recent data
        feature_matrix = feature_matrix.tail(lookback_days)
        
        # Create target: forward return
        target_col = f'{target_sector}_Return_1d'
        if target_col not in feature_matrix.columns:
            raise ValueError(f"Target column {target_col} not found")
        
        y = feature_matrix[target_col].shift(-target_horizon)
        
        # Remove target from features
        X = feature_matrix.drop(columns=[c for c in feature_matrix.columns if target_sector in c and 'Return' in c])
        
        # Drop rows with NaN target
        valid_idx = ~y.isna()
        X = X[valid_idx]
        y = y[valid_idx]
        
        return X, y


# Singleton instance
_pipeline = None

def get_pipeline() -> DataPipeline:
    """Get or create singleton data pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DataPipeline()
    return _pipeline
