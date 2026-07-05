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
from typing import Any, Dict, List, Optional, Tuple
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
            # Batch download for efficiency (auto_adjust=False keeps Adj Close column)
            data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker',
                               auto_adjust=False, progress=False)
            
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
                data = yf.download(ticker, start=start_date, end=end_date,
                                   auto_adjust=False, progress=False)
                if not data.empty:
                    close = data['Close']
                    # Newer yfinance returns MultiIndex columns even for one ticker
                    if isinstance(close, pd.DataFrame):
                        close = close.iloc[:, 0]
                    result_df[name] = close
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
        target_horizon: int = 21,  # 21-day forward return
        train_end_date: str = '2021-04-30',
        test_start_date: str = '2021-05-01'
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for ML model training with STRICT temporal train/test split.
        
        CRITICAL: No future data leaks into training set.
        
        Args:
            target_sector: Sector to predict returns for
            lookback_days: How many days of history to use
            target_horizon: Forward return horizon in days
            train_end_date: Last date for training data (inclusive)
            test_start_date: First date for test data (inclusive)
            
        Returns:
            Tuple of (X features, y target) — training set only
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
        
        # STRICT TEMPORAL SPLIT — only return training data
        X = X[X.index <= train_end_date]
        y = y[y.index <= train_end_date]
        
        logger.info(f"Training data: {X.shape[0]} samples, ends at {train_end_date}")
        
        return X, y
    
    def get_train_test_split(
        self,
        target_sector: str = 'Technology',
        target_horizon: int = 21,
        train_end_date: str = '2021-04-30',
        test_start_date: str = '2021-05-01'
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        Get strict temporal train/test split for model evaluation.
        
        CRITICAL: Prevents all forms of data leakage:
        - Training data ends BEFORE test_start_date
        - Forward-looking target is computed BEFORE splitting
        - No overlap between train and test periods
        
        Args:
            target_sector: Sector to predict returns for
            target_horizon: Forward return horizon in days
            train_end_date: Last date for training data
            test_start_date: First date for test data
            
        Returns:
            Tuple of (X_train, y_train, X_test, y_test)
        """
        feature_matrix = self.load_data('feature_matrix')
        
        if feature_matrix is None:
            result = self.run_full_pipeline()
            feature_matrix = result.get('feature_matrix')
        
        if feature_matrix is None or feature_matrix.empty:
            raise ValueError("Could not load or create feature matrix")
        
        # Create target: forward return
        target_col = f'{target_sector}_Return_1d'
        if target_col not in feature_matrix.columns:
            raise ValueError(f"Target column {target_col} not found")
        
        y_all = feature_matrix[target_col].shift(-target_horizon)
        X_all = feature_matrix.drop(
            columns=[c for c in feature_matrix.columns if target_sector in c and 'Return' in c]
        )
        
        # Drop NaN targets
        valid_idx = ~y_all.isna()
        X_all = X_all[valid_idx]
        y_all = y_all[valid_idx]
        
        # STRICT TEMPORAL SPLIT
        train_mask = X_all.index <= train_end_date
        test_mask = X_all.index >= test_start_date
        
        X_train, y_train = X_all[train_mask], y_all[train_mask]
        X_test, y_test = X_all[test_mask], y_all[test_mask]
        
        # Verify no overlap
        if len(X_train) > 0 and len(X_test) > 0:
            assert X_train.index.max() < X_test.index.min(), \
                "DATA LEAKAGE: Train and test sets overlap!"
        
        logger.info(f"Train: {len(X_train)} samples ({X_train.index.min()} to {X_train.index.max()})")
        logger.info(f"Test:  {len(X_test)} samples ({X_test.index.min()} to {X_test.index.max()})")
        
        return X_train, y_train, X_test, y_test
    
    def run_adf_stationarity_tests(
        self,
        data: Optional[pd.DataFrame] = None,
        columns: Optional[List[str]] = None,
        significance: float = 0.05
    ) -> pd.DataFrame:
        """
        Run Augmented Dickey-Fuller stationarity test on all specified columns.
        
        Non-stationary treatment variables violate causal inference assumptions.
        
        Args:
            data: DataFrame to test (if None, loads feature_matrix from disk)
            columns: Columns to test (if None, tests all numeric columns)
            significance: Significance level for stationarity determination
            
        Returns:
            DataFrame with ADF test results for each column
        """
        from statsmodels.tsa.stattools import adfuller
        
        if data is not None:
            feature_matrix = data
        else:
            feature_matrix = self.load_data('feature_matrix')
            if feature_matrix is None:
                raise ValueError("No feature matrix available. Run pipeline first.")
        
        if columns is None:
            columns = feature_matrix.select_dtypes(include=[np.number]).columns.tolist()
        
        results = []
        for col in columns:
            series = feature_matrix[col].dropna()
            if len(series) < 30:
                results.append({
                    'variable': col,
                    'adf_statistic': None,
                    'p_value': None,
                    'stationary': None,
                    'note': 'Insufficient data'
                })
                continue
            
            try:
                adf_result = adfuller(series, maxlag=10, autolag='AIC')
                is_stationary = adf_result[1] < significance
                results.append({
                    'variable': col,
                    'adf_statistic': round(adf_result[0], 4),
                    'p_value': round(adf_result[1], 6),
                    'n_lags': adf_result[2],
                    'n_obs': adf_result[3],
                    'critical_1pct': round(adf_result[4]['1%'], 4),
                    'critical_5pct': round(adf_result[4]['5%'], 4),
                    'critical_10pct': round(adf_result[4]['10%'], 4),
                    'stationary': is_stationary,
                })
            except Exception as e:
                results.append({
                    'variable': col,
                    'adf_statistic': None,
                    'p_value': None,
                    'stationary': None,
                    'note': str(e)
                })
        
        df = pd.DataFrame(results)
        non_stationary = df[df['stationary'] == False]
        if len(non_stationary) > 0:
            logger.warning(f"NON-STATIONARY variables detected: {non_stationary['variable'].tolist()}")
        
        return df
    
    def validate_data(self, data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Run comprehensive data validation checks for Phase 1 of the paper protocol.
        
        Checks:
        1. Shape, date range, null counts
        2. Feature correlations (flag > 0.85)
        3. Distribution statistics (mean, std, skew, kurtosis)
        4. ADF stationarity tests
        
        Args:
            data: DataFrame to validate (if None, loads feature_matrix from disk)
        
        Returns:
            Dictionary with all validation results
        """
        if data is not None:
            feature_matrix = data
        else:
            feature_matrix = self.load_data('feature_matrix')
            if feature_matrix is None:
                return {'error': 'No feature matrix available'}
        
        results = {}
        
        # 1. Basic info
        results['shape'] = {'rows': feature_matrix.shape[0], 'columns': feature_matrix.shape[1]}
        results['date_range'] = {
            'start': str(feature_matrix.index.min()),
            'end': str(feature_matrix.index.max())
        }
        results['null_counts'] = feature_matrix.isnull().sum().to_dict()
        results['total_nulls'] = int(feature_matrix.isnull().sum().sum())
        
        # 2. Correlation check
        numeric_cols = feature_matrix.select_dtypes(include=[np.number]).columns
        corr_matrix = feature_matrix[numeric_cols].corr()
        high_corr_pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                corr_val = abs(corr_matrix.iloc[i, j])
                if corr_val > 0.85:
                    high_corr_pairs.append({
                        'var1': numeric_cols[i],
                        'var2': numeric_cols[j],
                        'correlation': round(corr_val, 4)
                    })
        results['high_correlations'] = high_corr_pairs
        results['n_high_correlations'] = len(high_corr_pairs)
        
        # 3. Distribution statistics
        dist_stats = {}
        for col in numeric_cols:
            series = feature_matrix[col].dropna()
            if len(series) > 0:
                from scipy import stats as scipy_stats
                dist_stats[col] = {
                    'mean': round(float(series.mean()), 6),
                    'std': round(float(series.std()), 6),
                    'skew': round(float(scipy_stats.skew(series)), 4),
                    'kurtosis': round(float(scipy_stats.kurtosis(series)), 4),
                    'min': round(float(series.min()), 6),
                    'max': round(float(series.max()), 6),
                }
        results['distribution_stats'] = dist_stats
        
        # 4. ADF stationarity tests (on treatment-like variables)
        treatment_cols = [c for c in numeric_cols if 'Change' in c or 'Return' in c or 'Rate' in c]
        if treatment_cols:
            try:
                adf_results = self.run_adf_stationarity_tests(data=feature_matrix, columns=treatment_cols)
                results['adf_tests'] = adf_results.to_dict('records')
            except Exception as e:
                results['adf_tests'] = {'error': str(e)}
        
        return results


# Singleton instance
_pipeline = None

def get_pipeline() -> DataPipeline:
    """Get or create singleton data pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DataPipeline()
    return _pipeline
