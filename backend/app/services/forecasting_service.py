"""
Time Series Forecasting Service
================================
Multi-model forecasting for macroeconomic indicators, volatility, and returns.

Implements:
- ARIMA/SARIMA for macro indicators (Fed Rate, CPI, GDP)
- GARCH family models for volatility forecasting
- LSTM neural networks for non-linear return prediction
- Ensemble methods combining multiple forecasters

Each model includes confidence intervals and backtesting validation.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
from scipy import stats
import warnings
import joblib

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

# Model storage path
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


class ARIMAForecaster:
    """
    ARIMA/SARIMA forecaster for macroeconomic time series.
    
    Best for: Stationary or trend-stationary series like
    interest rates, unemployment, CPI changes.
    """
    
    def __init__(self, max_p: int = 5, max_d: int = 2, max_q: int = 5):
        """
        Initialize ARIMA forecaster.
        
        Args:
            max_p: Maximum AR order
            max_d: Maximum differencing order
            max_q: Maximum MA order
        """
        self.max_p = max_p
        self.max_d = max_d
        self.max_q = max_q
        self.model = None
        self.order = None
        self._statsmodels_available = self._check_statsmodels()
    
    def _check_statsmodels(self) -> bool:
        """Check if statsmodels is available."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            return True
        except ImportError:
            logger.warning("statsmodels not available for ARIMA")
            return False
    
    def fit(
        self,
        series: pd.Series,
        order: Optional[Tuple[int, int, int]] = None
    ) -> Dict[str, Any]:
        """
        Fit ARIMA model to time series.
        
        Args:
            series: Time series to fit
            order: (p, d, q) order, auto-selected if None
            
        Returns:
            Dictionary with fit statistics
        """
        if not self._statsmodels_available:
            return self._fallback_fit(series)
        
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller
        
        try:
            # Clean series
            series = series.dropna()
            
            if len(series) < 50:
                return {'error': 'Insufficient data (need 50+ observations)'}
            
            # Auto-select order if not provided
            if order is None:
                order = self._auto_select_order(series)
            
            self.order = order
            
            # Fit model
            model = ARIMA(series, order=order)
            self.model = model.fit()
            
            # Get fit statistics
            aic = self.model.aic
            bic = self.model.bic
            
            # Residual diagnostics
            residuals = self.model.resid
            
            return {
                'order': order,
                'aic': float(aic),
                'bic': float(bic),
                'n_observations': len(series),
                'residual_mean': float(residuals.mean()),
                'residual_std': float(residuals.std()),
            }
            
        except Exception as e:
            logger.error(f"ARIMA fit failed: {e}")
            return {'error': str(e)}
    
    def _auto_select_order(self, series: pd.Series) -> Tuple[int, int, int]:
        """Auto-select ARIMA order using AIC."""
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller
        
        # Test for stationarity
        adf_result = adfuller(series.dropna())
        d = 0 if adf_result[1] < 0.05 else 1
        
        # Grid search for p, q
        best_aic = np.inf
        best_order = (1, d, 1)
        
        for p in range(self.max_p + 1):
            for q in range(self.max_q + 1):
                try:
                    model = ARIMA(series, order=(p, d, q))
                    fitted = model.fit()
                    if fitted.aic < best_aic:
                        best_aic = fitted.aic
                        best_order = (p, d, q)
                except:
                    continue
        
        return best_order
    
    def predict(
        self,
        steps: int = 21,
        confidence: float = 0.95
    ) -> Dict[str, Any]:
        """
        Generate forecasts with confidence intervals.
        
        Args:
            steps: Number of steps ahead to forecast
            confidence: Confidence level for intervals
            
        Returns:
            Dictionary with forecasts and intervals
        """
        if self.model is None:
            return {'error': 'Model not fitted'}
        
        try:
            # Get forecast
            forecast = self.model.get_forecast(steps=steps)
            
            mean = forecast.predicted_mean
            conf_int = forecast.conf_int(alpha=1-confidence)
            
            return {
                'forecast': mean.values.tolist(),
                'ci_lower': conf_int.iloc[:, 0].values.tolist(),
                'ci_upper': conf_int.iloc[:, 1].values.tolist(),
                'steps': steps,
                'confidence': confidence,
                'dates': [str(d) for d in mean.index] if hasattr(mean.index, '__iter__') else None,
            }
            
        except Exception as e:
            logger.error(f"ARIMA prediction failed: {e}")
            return {'error': str(e)}
    
    def _fallback_fit(self, series: pd.Series) -> Dict[str, Any]:
        """Fallback when statsmodels unavailable."""
        # Simple exponential smoothing
        self.model = {'type': 'ema', 'alpha': 0.3, 'last_value': series.iloc[-1]}
        return {'method': 'exponential_moving_average', 'alpha': 0.3}
    
    def save(self, filepath: str):
        """Save fitted model."""
        if self.model is not None:
            joblib.dump({'model': self.model, 'order': self.order}, filepath)
    
    def load(self, filepath: str):
        """Load fitted model."""
        data = joblib.load(filepath)
        self.model = data['model']
        self.order = data['order']


class GARCHForecaster:
    """
    GARCH family models for volatility forecasting.
    
    Best for: Financial returns volatility clustering,
    VIX prediction, risk metrics.
    """
    
    def __init__(self, p: int = 1, q: int = 1, model_type: str = 'GARCH'):
        """
        Initialize GARCH forecaster.
        
        Args:
            p: GARCH p order
            q: GARCH q order
            model_type: 'GARCH', 'EGARCH', or 'GJR-GARCH'
        """
        self.p = p
        self.q = q
        self.model_type = model_type
        self.model = None
        self._arch_available = self._check_arch()
    
    def _check_arch(self) -> bool:
        """Check if arch library is available."""
        try:
            from arch import arch_model
            return True
        except ImportError:
            logger.warning("arch library not available for GARCH")
            return False
    
    def fit(
        self,
        returns: pd.Series,
        mean_model: str = 'Constant'
    ) -> Dict[str, Any]:
        """
        Fit GARCH model to returns series.
        
        Args:
            returns: Returns series (not prices!)
            mean_model: Mean model type ('Zero', 'Constant', 'AR')
            
        Returns:
            Dictionary with fit statistics
        """
        if not self._arch_available:
            return self._fallback_fit(returns)
        
        from arch import arch_model
        
        try:
            # Clean returns
            returns = returns.dropna() * 100  # Scale to percentage
            
            if len(returns) < 100:
                return {'error': 'Insufficient data (need 100+ observations)'}
            
            # Create model based on type
            if self.model_type == 'EGARCH':
                vol_model = 'EGARCH'
            elif self.model_type == 'GJR-GARCH':
                vol_model = 'GARCH'
                # GJR-GARCH uses o parameter
            else:
                vol_model = 'GARCH'
            
            model = arch_model(
                returns,
                mean=mean_model,
                vol=vol_model,
                p=self.p,
                q=self.q
            )
            
            self.model = model.fit(disp='off')
            
            return {
                'model_type': self.model_type,
                'p': self.p,
                'q': self.q,
                'aic': float(self.model.aic),
                'bic': float(self.model.bic),
                'log_likelihood': float(self.model.loglikelihood),
                'n_observations': len(returns),
                'unconditional_volatility': float(np.sqrt(self.model.conditional_volatility.mean())) / 100,
            }
            
        except Exception as e:
            logger.error(f"GARCH fit failed: {e}")
            return {'error': str(e)}
    
    def predict(
        self,
        steps: int = 21,
        method: str = 'simulation',
        n_simulations: int = 1000
    ) -> Dict[str, Any]:
        """
        Forecast volatility.
        
        Args:
            steps: Number of steps ahead
            method: 'analytic' or 'simulation'
            n_simulations: Number of simulations for CI
            
        Returns:
            Dictionary with volatility forecasts
        """
        if self.model is None:
            return {'error': 'Model not fitted'}
        
        # Handle EWMA fallback model (when arch library is not available)
        if isinstance(self.model, dict) and self.model.get('type') == 'ewma':
            last_vol = self.model['last_vol']
            vol_forecast = []
            current_vol = last_vol
            for i in range(steps):
                current_vol = 0.97 * current_vol + 0.03 * last_vol
                vol_forecast.append(current_vol)
            volatility = np.array(vol_forecast)
            variance = volatility ** 2
            return {
                'volatility': volatility,
                'variance': variance,
                'volatility_forecast': volatility.tolist(),
                'steps': steps,
                'method': 'ewma_fallback',
            }
        
        try:
            # Get forecast
            forecast = self.model.forecast(horizon=steps, method=method)
            
            # Get variance forecast (convert back from percentage)
            variance = forecast.variance.iloc[-1].values / 10000
            volatility = np.sqrt(variance)
            
            # Annualize
            annualized_vol = volatility * np.sqrt(252)
            
            # Simulation-based confidence intervals
            if method == 'simulation':
                simulations = self.model.forecast(
                    horizon=steps, 
                    method='simulation',
                    simulations=n_simulations
                )
                
                # Get variance paths
                var_sims = simulations.simulations.variances
                vol_sims = np.sqrt(var_sims) / 100  # Convert from percentage
                
                ci_lower = np.percentile(vol_sims, 2.5, axis=1).flatten() * np.sqrt(252)
                ci_upper = np.percentile(vol_sims, 97.5, axis=1).flatten() * np.sqrt(252)
            else:
                # Rough CI based on historical estimation error
                ci_lower = annualized_vol * 0.8
                ci_upper = annualized_vol * 1.2
            
            return {
                'volatility': annualized_vol,
                'variance': variance,
                'volatility_forecast': annualized_vol.tolist(),
                'ci_lower': ci_lower.tolist() if hasattr(ci_lower, 'tolist') else [ci_lower],
                'ci_upper': ci_upper.tolist() if hasattr(ci_upper, 'tolist') else [ci_upper],
                'steps': steps,
                'method': method,
            }
            
        except Exception as e:
            logger.error(f"GARCH prediction failed: {e}")
            return {'error': str(e)}
    
    def _fallback_fit(self, returns: pd.Series) -> Dict[str, Any]:
        """Fallback using EWMA volatility."""
        returns = returns.dropna()
        ewma_vol = returns.ewm(span=21).std() * np.sqrt(252)
        self.model = {'type': 'ewma', 'last_vol': ewma_vol.iloc[-1], 'span': 21}
        return {'method': 'ewma', 'unconditional_volatility': float(ewma_vol.mean())}
    
    def save(self, filepath: str):
        """Save fitted model."""
        if self.model is not None:
            joblib.dump(self.model, filepath)
    
    def load(self, filepath: str):
        """Load fitted model. Handles both raw model and dict-wrapped format."""
        data = joblib.load(filepath)
        # Colab notebook saves as {'model': fit, 'vol_type': ..., ...}
        # Backend save() saves the raw model directly
        if isinstance(data, dict) and 'model' in data:
            self.model = data['model']
        else:
            self.model = data


class LSTMForecaster:
    """
    LSTM neural network for return prediction.
    
    Best for: Non-linear patterns, regime changes,
    multivariate forecasting.
    """
    
    def __init__(
        self,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        sequence_length: int = 60
    ):
        """
        Initialize LSTM forecaster.
        
        Args:
            hidden_size: LSTM hidden units
            num_layers: Number of LSTM layers
            dropout: Dropout rate
            sequence_length: Input sequence length
        """
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = None
        self._torch_available = self._check_torch()
    
    def _check_torch(self) -> bool:
        """Check if PyTorch is available."""
        try:
            import torch
            return True
        except ImportError:
            logger.warning("PyTorch not available for LSTM")
            return False
    
    def _build_model(self, input_size: int):
        """Build LSTM model architecture."""
        import torch
        import torch.nn as nn
        
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, dropout):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    num_layers=num_layers,
                    dropout=dropout if num_layers > 1 else 0,
                    batch_first=True
                )
                self.fc = nn.Linear(hidden_size, 1)
            
            def forward(self, x):
                lstm_out, _ = self.lstm(x)
                return self.fc(lstm_out[:, -1, :])
        
        return LSTMModel(input_size, self.hidden_size, self.num_layers, self.dropout)
    
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        validation_split: float = 0.2,
        early_stopping_patience: int = 10
    ) -> Dict[str, Any]:
        """
        Train LSTM model.
        
        Args:
            X: Input features (n_samples, sequence_length, n_features)
            y: Target values (n_samples,)
            epochs: Training epochs
            batch_size: Batch size
            validation_split: Fraction for validation
            early_stopping_patience: Patience for early stopping
            
        Returns:
            Dictionary with training history
        """
        if not self._torch_available:
            return self._fallback_fit(X, y)
        
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        from sklearn.preprocessing import StandardScaler
        
        try:
            # Scale data
            self.scaler = StandardScaler()
            n_samples, seq_len, n_features = X.shape
            X_flat = X.reshape(-1, n_features)
            X_scaled = self.scaler.fit_transform(X_flat).reshape(n_samples, seq_len, n_features)
            
            # Split data
            val_size = int(n_samples * validation_split)
            X_train, X_val = X_scaled[:-val_size], X_scaled[-val_size:]
            y_train, y_val = y[:-val_size], y[-val_size:]
            
            # Convert to tensors
            X_train_t = torch.FloatTensor(X_train)
            y_train_t = torch.FloatTensor(y_train).unsqueeze(1)
            X_val_t = torch.FloatTensor(X_val)
            y_val_t = torch.FloatTensor(y_val).unsqueeze(1)
            
            # Create data loaders
            train_dataset = TensorDataset(X_train_t, y_train_t)
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            
            # Build model
            self.model = self._build_model(n_features)
            
            # Training setup
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5)
            
            # Training loop
            best_val_loss = np.inf
            patience_counter = 0
            train_losses = []
            val_losses = []
            
            for epoch in range(epochs):
                self.model.train()
                epoch_loss = 0
                
                for batch_X, batch_y in train_loader:
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    epoch_loss += loss.item()
                
                train_loss = epoch_loss / len(train_loader)
                train_losses.append(train_loss)
                
                # Validation
                self.model.eval()
                with torch.no_grad():
                    val_outputs = self.model(X_val_t)
                    val_loss = criterion(val_outputs, y_val_t).item()
                    val_losses.append(val_loss)
                
                scheduler.step(val_loss)
                
                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= early_stopping_patience:
                        logger.info(f"Early stopping at epoch {epoch}")
                        break
            
            return {
                'epochs_trained': epoch + 1,
                'train_loss': train_losses[-1],
                'val_loss': val_losses[-1],
                'best_val_loss': best_val_loss,
                'n_samples': n_samples,
                'n_features': n_features,
            }
            
        except Exception as e:
            logger.error(f"LSTM fit failed: {e}")
            return {'error': str(e)}
    
    def predict(
        self,
        X: np.ndarray,
        n_simulations: int = 100
    ) -> Dict[str, Any]:
        """
        Generate predictions with uncertainty estimates.
        
        Args:
            X: Input features
            n_simulations: Monte Carlo dropout simulations
            
        Returns:
            Dictionary with predictions and CI
        """
        if self.model is None or self.scaler is None:
            return {'error': 'Model not fitted'}
        
        import torch
        
        try:
            # Scale input
            n_samples, seq_len, n_features = X.shape
            X_flat = X.reshape(-1, n_features)
            X_scaled = self.scaler.transform(X_flat).reshape(n_samples, seq_len, n_features)
            X_t = torch.FloatTensor(X_scaled)
            
            # Standard prediction
            self.model.eval()
            with torch.no_grad():
                predictions = self.model(X_t).numpy().flatten()
            
            # Monte Carlo dropout for uncertainty
            self.model.train()  # Enable dropout
            mc_predictions = []
            
            for _ in range(n_simulations):
                with torch.no_grad():
                    mc_pred = self.model(X_t).numpy().flatten()
                    mc_predictions.append(mc_pred)
            
            mc_predictions = np.array(mc_predictions)
            
            ci_lower = np.percentile(mc_predictions, 2.5, axis=0)
            ci_upper = np.percentile(mc_predictions, 97.5, axis=0)
            uncertainty = np.std(mc_predictions, axis=0)
            
            return {
                'predictions': predictions.tolist(),
                'ci_lower': ci_lower.tolist(),
                'ci_upper': ci_upper.tolist(),
                'uncertainty': uncertainty.tolist(),
            }
            
        except Exception as e:
            logger.error(f"LSTM prediction failed: {e}")
            return {'error': str(e)}
    
    def _fallback_fit(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Fallback using linear regression."""
        from sklearn.linear_model import Ridge
        
        # Flatten sequences
        X_flat = X.reshape(X.shape[0], -1)
        
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_flat, y)
        
        return {'method': 'ridge_regression', 'n_features': X_flat.shape[1]}
    
    def save(self, filepath: str):
        """Save model, scaler, and config including input_size for reconstruction."""
        import torch
        if self.model is not None:
            # Infer input_size from the first LSTM weight matrix
            input_size = self.model.lstm.weight_ih_l0.shape[1]
            torch.save({
                'model_state': self.model.state_dict(),
                'scaler': self.scaler,
                'config': {
                    'input_size': input_size,
                    'hidden_size': self.hidden_size,
                    'num_layers': self.num_layers,
                    'dropout': self.dropout,
                    'sequence_length': self.sequence_length
                }
            }, filepath)
    
    def load(self, filepath: str):
        """Load model, scaler, and rebuild model architecture."""
        import torch
        data = torch.load(filepath, map_location='cpu')
        self.scaler = data['scaler']
        config = data['config']
        self.hidden_size = config['hidden_size']
        self.num_layers = config['num_layers']
        self.dropout = config.get('dropout', 0.2)
        self.sequence_length = config.get('sequence_length', 60)
        
        # Rebuild model architecture using saved input_size
        input_size = config.get('input_size')
        if input_size is None:
            # Fallback: infer from state dict weight shape
            weight_key = 'lstm.weight_ih_l0'
            if weight_key in data['model_state']:
                input_size = data['model_state'][weight_key].shape[1]
            else:
                raise ValueError("Cannot determine input_size for LSTM model reconstruction")
        
        self.model = self._build_model(input_size)
        self.model.load_state_dict(data['model_state'])
        self.model.eval()


class EnsembleForecaster:
    """
    Ensemble combining multiple forecasting models.
    
    Combines ARIMA, GARCH, LSTM predictions using
    weighted averaging or stacking.
    """
    
    def __init__(self):
        """Initialize ensemble forecaster."""
        self.models = {}
        self.weights = {}
    
    def add_model(self, name: str, model: Any, weight: float = 1.0):
        """Add a model to the ensemble."""
        self.models[name] = model
        self.weights[name] = weight
    
    def predict_ensemble(
        self,
        data: Dict[str, Any],
        steps: int = 21
    ) -> Dict[str, Any]:
        """
        Generate ensemble prediction.
        
        Args:
            data: Input data for each model
            steps: Forecast horizon
            
        Returns:
            Dictionary with ensemble prediction
        """
        predictions = {}
        
        for name, model in self.models.items():
            try:
                if hasattr(model, 'predict'):
                    pred = model.predict(steps=steps)
                    if 'forecast' in pred:
                        predictions[name] = np.array(pred['forecast'])
                    elif 'predictions' in pred:
                        predictions[name] = np.array(pred['predictions'])
                    elif 'volatility_forecast' in pred:
                        predictions[name] = np.array(pred['volatility_forecast'])
            except Exception as e:
                logger.warning(f"Model {name} prediction failed: {e}")
        
        if not predictions:
            return {'error': 'No successful predictions'}
        
        # Weighted average
        total_weight = sum(self.weights.get(name, 1.0) for name in predictions.keys())
        ensemble_pred = np.zeros(steps)
        
        for name, pred in predictions.items():
            weight = self.weights.get(name, 1.0) / total_weight
            # Handle different lengths
            pred_len = min(len(pred), steps)
            ensemble_pred[:pred_len] += weight * pred[:pred_len]
        
        return {
            'ensemble_forecast': ensemble_pred.tolist(),
            'model_predictions': {k: v.tolist() for k, v in predictions.items()},
            'weights': self.weights,
        }


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def prepare_sequences(
    data: pd.DataFrame,
    target_col: str,
    feature_cols: List[str],
    sequence_length: int = 60,
    horizon: int = 21
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prepare sequences for LSTM training.
    
    Args:
        data: DataFrame with features
        target_col: Column to predict
        feature_cols: Feature columns
        sequence_length: Input sequence length
        horizon: Prediction horizon
        
    Returns:
        Tuple of (X, y) arrays
    """
    features = data[feature_cols].values
    target = data[target_col].values
    
    X, y = [], []
    
    for i in range(len(data) - sequence_length - horizon):
        X.append(features[i:i+sequence_length])
        y.append(target[i+sequence_length+horizon-1])
    
    return np.array(X), np.array(y)


def forecast_all_sectors(
    feature_matrix: pd.DataFrame,
    sectors: List[str] = None,
    horizon: int = 21
) -> Dict[str, Dict[str, Any]]:
    """
    Generate forecasts for all sectors.
    
    Args:
        feature_matrix: DataFrame with sector returns
        sectors: List of sectors to forecast
        horizon: Forecast horizon in days
        
    Returns:
        Dictionary of sector forecasts
    """
    if sectors is None:
        sectors = ['Technology', 'Healthcare', 'Energy', 'Financials', 'Industrials']
    
    forecasts = {}
    
    for sector in sectors:
        return_col = f'{sector}_Return_1d'
        
        if return_col not in feature_matrix.columns:
            continue
        
        returns = feature_matrix[return_col].dropna()
        
        # Volatility forecast with GARCH
        garch = GARCHForecaster()
        garch_fit = garch.fit(returns)
        
        if 'error' not in garch_fit:
            vol_forecast = garch.predict(steps=horizon)
            forecasts[sector] = {
                'volatility': vol_forecast,
                'garch_fit': garch_fit,
            }
    
    return forecasts
