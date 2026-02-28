"""
ML Model Training Pipeline
===========================
Orchestrates training, evaluation, and management of all ML models.

Provides:
- Automated training workflows
- Model versioning and registry
- Performance tracking and comparison
- Scheduled retraining
- A/B testing support

This is the central coordination point for all ML operations.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import numpy as np
import pandas as pd
import joblib
import warnings

from .data_pipeline import DataPipeline
from .causal_discovery import CausalDiscoveryEngine
from .treatment_effects import TreatmentEffectEstimator
from .forecasting_service import (
    ARIMAForecaster, GARCHForecaster, LSTMForecaster, EnsembleForecaster
)
from .regime_detection import MarketRegimeDetector

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

# Storage paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(DATA_DIR, 'models')
REGISTRY_PATH = os.path.join(MODELS_DIR, 'model_registry.json')

os.makedirs(MODELS_DIR, exist_ok=True)


class ModelRegistry:
    """
    Manages model versioning and metadata tracking.
    
    Features:
    - Model version tracking
    - Performance metrics storage
    - Model comparison
    - Automatic model selection
    """
    
    def __init__(self, registry_path: str = REGISTRY_PATH):
        """Initialize model registry."""
        self.registry_path = registry_path
        self.models = self._load_registry()
    
    def _load_registry(self) -> Dict:
        """Load registry from disk."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}")
        return {'models': {}, 'active_versions': {}}
    
    def _save_registry(self):
        """Save registry to disk."""
        try:
            with open(self.registry_path, 'w') as f:
                json.dump(self.models, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def register_model(
        self,
        model_type: str,
        model_name: str,
        version: str,
        metrics: Dict[str, float],
        hyperparameters: Dict,
        filepath: str,
        training_data_hash: str = None
    ) -> str:
        """
        Register a trained model.
        
        Args:
            model_type: Type of model (causal, forecast, regime, etc.)
            model_name: Name identifier
            version: Version string
            metrics: Performance metrics
            hyperparameters: Model hyperparameters
            filepath: Path to saved model file
            training_data_hash: Hash of training data
            
        Returns:
            Model ID
        """
        model_id = f"{model_type}_{model_name}_{version}"
        
        if model_type not in self.models['models']:
            self.models['models'][model_type] = {}
        
        self.models['models'][model_type][model_id] = {
            'model_name': model_name,
            'version': version,
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'filepath': filepath,
            'training_data_hash': training_data_hash,
            'created_at': datetime.now().isoformat(),
            'is_active': False,
        }
        
        self._save_registry()
        logger.info(f"Registered model: {model_id}")
        return model_id
    
    def set_active_model(self, model_type: str, model_id: str) -> bool:
        """Set a model as the active version for its type."""
        if model_type not in self.models['models']:
            return False
        
        if model_id not in self.models['models'][model_type]:
            return False
        
        # Deactivate current active
        if model_type in self.models['active_versions']:
            old_id = self.models['active_versions'][model_type]
            if old_id in self.models['models'][model_type]:
                self.models['models'][model_type][old_id]['is_active'] = False
        
        # Activate new
        self.models['models'][model_type][model_id]['is_active'] = True
        self.models['active_versions'][model_type] = model_id
        
        self._save_registry()
        logger.info(f"Set active model: {model_type} -> {model_id}")
        return True
    
    def get_active_model(self, model_type: str) -> Optional[Dict]:
        """Get the active model for a type."""
        if model_type not in self.models['active_versions']:
            return None
        
        model_id = self.models['active_versions'][model_type]
        return self.models['models'].get(model_type, {}).get(model_id)
    
    def get_best_model(self, model_type: str, metric: str = 'rmse', higher_is_better: bool = False) -> Optional[str]:
        """Get the best model based on a metric."""
        if model_type not in self.models['models']:
            return None
        
        models = self.models['models'][model_type]
        if not models:
            return None
        
        best_id = None
        best_value = float('inf') if not higher_is_better else float('-inf')
        
        for model_id, info in models.items():
            if metric in info.get('metrics', {}):
                value = info['metrics'][metric]
                if higher_is_better:
                    if value > best_value:
                        best_value = value
                        best_id = model_id
                else:
                    if value < best_value:
                        best_value = value
                        best_id = model_id
        
        return best_id
    
    def list_models(self, model_type: str = None) -> Dict:
        """List all registered models."""
        if model_type:
            return self.models['models'].get(model_type, {})
        return self.models['models']


class MLTrainingPipeline:
    """
    Orchestrates the complete ML training workflow.
    
    Coordinates:
    1. Data fetching and preprocessing
    2. Causal discovery
    3. Treatment effect estimation
    4. Forecasting models
    5. Regime detection
    6. Model evaluation and selection
    """
    
    def __init__(self, fred_api_key: str = None):
        """
        Initialize training pipeline.
        
        Args:
            fred_api_key: FRED API key for macro data
        """
        self.data_pipeline = DataPipeline(fred_api_key=fred_api_key)
        self.registry = ModelRegistry()
        self.training_status = {}
    
    def _generate_version(self) -> str:
        """Generate version string based on timestamp."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _compute_data_hash(self, data: pd.DataFrame) -> str:
        """Compute hash of training data."""
        return hashlib.md5(
            pd.util.hash_pandas_object(data).values
        ).hexdigest()[:12]
    
    def run_full_pipeline(
        self,
        start_date: str = '2010-01-01',
        end_date: str = None,
        train_test_split: float = 0.2,
        skip_data_fetch: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete training pipeline.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            train_test_split: Test set proportion
            skip_data_fetch: Skip data fetch if data exists
            
        Returns:
            Dictionary with training results
        """
        pipeline_id = f"pipeline_{self._generate_version()}"
        self.training_status[pipeline_id] = {
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'steps_completed': [],
            'errors': [],
        }
        
        results = {
            'pipeline_id': pipeline_id,
            'data': None,
            'causal': None,
            'treatment': None,
            'forecasting': None,
            'regime': None,
        }
        
        try:
            # Step 1: Fetch and prepare data
            logger.info("Step 1: Fetching data...")
            if not skip_data_fetch:
                data_result = self.data_pipeline.run_full_pipeline(
                    start_date=start_date,
                    end_date=end_date
                )
                results['data'] = data_result
            
            self.training_status[pipeline_id]['steps_completed'].append('data_fetch')
            
            # Load feature matrix
            feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
            if os.path.exists(feature_path):
                feature_matrix = pd.read_parquet(feature_path)
            else:
                return {
                    'error': 'Feature matrix not found. Run data pipeline first.',
                    'status': 'failed'
                }
            
            # Split data
            split_idx = int(len(feature_matrix) * (1 - train_test_split))
            train_data = feature_matrix.iloc[:split_idx]
            test_data = feature_matrix.iloc[split_idx:]
            
            data_hash = self._compute_data_hash(train_data)
            version = self._generate_version()
            
            # Step 2: Train causal discovery models
            logger.info("Step 2: Training causal discovery...")
            results['causal'] = self._train_causal_models(
                train_data, test_data, version, data_hash
            )
            self.training_status[pipeline_id]['steps_completed'].append('causal_discovery')
            
            # Step 3: Train treatment effect models
            logger.info("Step 3: Training treatment effect models...")
            results['treatment'] = self._train_treatment_models(
                train_data, test_data, version, data_hash
            )
            self.training_status[pipeline_id]['steps_completed'].append('treatment_effects')
            
            # Step 4: Train forecasting models
            logger.info("Step 4: Training forecasting models...")
            results['forecasting'] = self._train_forecasting_models(
                train_data, test_data, version, data_hash
            )
            self.training_status[pipeline_id]['steps_completed'].append('forecasting')
            
            # Step 5: Train regime detection
            logger.info("Step 5: Training regime detection...")
            results['regime'] = self._train_regime_model(
                train_data, test_data, version, data_hash
            )
            self.training_status[pipeline_id]['steps_completed'].append('regime_detection')
            
            self.training_status[pipeline_id]['status'] = 'completed'
            self.training_status[pipeline_id]['completed_at'] = datetime.now().isoformat()
            
            logger.info("Training pipeline completed successfully!")
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.training_status[pipeline_id]['status'] = 'failed'
            self.training_status[pipeline_id]['errors'].append(str(e))
            return {'error': str(e), 'status': 'failed'}
    
    def _train_causal_models(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        version: str,
        data_hash: str
    ) -> Dict[str, Any]:
        """Train causal discovery models."""
        results = {}
        
        # Extract sector columns
        sector_cols = [c for c in train_data.columns if c.endswith('_Return_1d')]
        
        if len(sector_cols) < 2:
            return {'error': 'Insufficient sector data'}
        
        sector_returns = train_data[sector_cols]
        
        # Causal discovery engine
        causal_engine = CausalDiscoveryEngine()
        
        # Granger causality matrix
        granger_matrix = causal_engine.granger_causality_matrix(sector_returns)
        results['granger_matrix'] = granger_matrix
        
        # PC algorithm
        pc_result = causal_engine.pc_algorithm(sector_returns.dropna())
        results['pc_algorithm'] = pc_result
        
        # Build DAG
        dag = causal_engine.build_causal_dag(sector_returns)
        results['causal_dag'] = dag
        
        # Save results
        causal_path = os.path.join(MODELS_DIR, f'causal_discovery_{version}.pkl')
        joblib.dump({
            'granger_matrix': granger_matrix,
            'pc_result': pc_result,
            'dag': dag,
        }, causal_path)
        
        # Register model
        self.registry.register_model(
            model_type='causal',
            model_name='discovery_engine',
            version=version,
            metrics={
                'n_relationships': len(dag.get('edges', [])),
                'n_nodes': len(dag.get('nodes', [])),
            },
            hyperparameters={'max_lag': 5, 'significance': 0.05},
            filepath=causal_path,
            training_data_hash=data_hash
        )
        
        # Set as active
        model_id = f"causal_discovery_engine_{version}"
        self.registry.set_active_model('causal', model_id)
        
        return results
    
    def _train_treatment_models(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        version: str,
        data_hash: str
    ) -> Dict[str, Any]:
        """Train treatment effect models."""
        results = {}
        
        estimator = TreatmentEffectEstimator()
        
        # Macro to sector effects
        macro_cols = ['Fed_Funds_Rate', 'CPI_Change', 'GDP_Change']
        sector_cols = [c for c in train_data.columns if c.endswith('_Return_1d')]
        
        available_macro = [c for c in macro_cols if c in train_data.columns]
        
        if available_macro and sector_cols:
            # Extract sector names from column names (e.g. 'Technology_Return_1d' -> 'Technology')
            sector_names = [c.replace('_Return_1d', '') for c in sector_cols]

            effects_matrix = estimator.estimate_macro_sector_effects(
                train_data,
                sectors=sector_names,
                macro_treatments=[f'{m}_Change' if not m.endswith('_Change') else m for m in available_macro]
            )
            results['macro_sector_effects'] = effects_matrix
            
            # Build sensitivity matrix from estimated effects
            sensitivity_matrix = estimator.build_sensitivity_matrix(
                effects_matrix
            )
            results['sensitivity_matrix'] = sensitivity_matrix
            
            # Save
            treatment_path = os.path.join(MODELS_DIR, f'treatment_effects_{version}.pkl')
            joblib.dump({
                'effects_matrix': effects_matrix,
                'sensitivity_matrix': sensitivity_matrix,
            }, treatment_path)
            
            # Register
            self.registry.register_model(
                model_type='treatment',
                model_name='effect_estimator',
                version=version,
                metrics={'n_effects': len(effects_matrix)},
                hyperparameters={'method': 'auto'},
                filepath=treatment_path,
                training_data_hash=data_hash
            )
            
            model_id = f"treatment_effect_estimator_{version}"
            self.registry.set_active_model('treatment', model_id)
        
        return results
    
    def _train_forecasting_models(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        version: str,
        data_hash: str
    ) -> Dict[str, Any]:
        """Train forecasting models for each sector."""
        results = {'models': {}, 'evaluations': {}}
        
        sector_cols = [c for c in train_data.columns if c.endswith('_Return_1d')]
        
        for sector_col in sector_cols[:5]:  # Limit to 5 sectors for speed
            sector_name = sector_col.replace('_Return_1d', '')
            results['models'][sector_name] = {}
            results['evaluations'][sector_name] = {}
            
            train_series = train_data[sector_col].dropna()
            test_series = test_data[sector_col].dropna()
            
            if len(train_series) < 252:
                continue
            
            # ARIMA
            try:
                arima = ARIMAForecaster()
                arima.fit(train_series)
                arima_preds = arima.predict(steps=len(test_series))
                
                arima_rmse = np.sqrt(np.mean((test_series.values - arima_preds['mean'][:len(test_series)])**2))
                results['evaluations'][sector_name]['arima'] = {'rmse': float(arima_rmse)}
                
                arima_path = os.path.join(MODELS_DIR, f'arima_{sector_name}_{version}.pkl')
                arima.save(arima_path)
                results['models'][sector_name]['arima'] = arima_path
            except Exception as e:
                logger.warning(f"ARIMA failed for {sector_name}: {e}")
            
            # GARCH
            try:
                garch = GARCHForecaster()
                garch.fit(train_series)
                garch_preds = garch.predict(steps=len(test_series))
                
                results['evaluations'][sector_name]['garch'] = {
                    'mean_volatility': float(np.mean(garch_preds['volatility']))
                }
                
                garch_path = os.path.join(MODELS_DIR, f'garch_{sector_name}_{version}.pkl')
                garch.save(garch_path)
                results['models'][sector_name]['garch'] = garch_path
            except Exception as e:
                logger.warning(f"GARCH failed for {sector_name}: {e}")
            
            # LSTM (if enough data)
            if len(train_series) >= 500:
                try:
                    lstm = LSTMForecaster(sequence_length=60, hidden_size=64)
                    lstm.fit(train_series, epochs=50, verbose=False)
                    lstm_preds = lstm.predict(train_series.values[-60:], steps=len(test_series))
                    
                    lstm_rmse = np.sqrt(np.mean((test_series.values - lstm_preds['mean'][:len(test_series)])**2))
                    results['evaluations'][sector_name]['lstm'] = {'rmse': float(lstm_rmse)}
                    
                    lstm_path = os.path.join(MODELS_DIR, f'lstm_{sector_name}_{version}.pkl')
                    lstm.save(lstm_path)
                    results['models'][sector_name]['lstm'] = lstm_path
                except Exception as e:
                    logger.warning(f"LSTM failed for {sector_name}: {e}")
        
        # Register ensemble
        self.registry.register_model(
            model_type='forecast',
            model_name='ensemble',
            version=version,
            metrics=results['evaluations'],
            hyperparameters={'models': ['arima', 'garch', 'lstm']},
            filepath=MODELS_DIR,
            training_data_hash=data_hash
        )
        
        model_id = f"forecast_ensemble_{version}"
        self.registry.set_active_model('forecast', model_id)
        
        return results
    
    def _train_regime_model(
        self,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        version: str,
        data_hash: str
    ) -> Dict[str, Any]:
        """Train regime detection model."""
        results = {}
        
        # Use market index returns
        if 'SP500_Return' in train_data.columns:
            returns = train_data['SP500_Return']
        else:
            # Fallback to sector average
            sector_cols = [c for c in train_data.columns if c.endswith('_Return_1d')]
            if sector_cols:
                returns = train_data[sector_cols].mean(axis=1)
            else:
                return {'error': 'No return data available'}
        
        volatility = None
        if 'SP500_Volatility_21d' in train_data.columns:
            volatility = train_data['SP500_Volatility_21d']
        
        # Train HMM
        detector = MarketRegimeDetector(n_regimes=4)
        fit_result = detector.fit(returns, volatility)
        results['fit_result'] = fit_result
        
        # Evaluate on test
        if 'SP500_Return' in test_data.columns:
            test_returns = test_data['SP500_Return']
        else:
            sector_cols = [c for c in test_data.columns if c.endswith('_Return_1d')]
            test_returns = test_data[sector_cols].mean(axis=1)
        
        test_regime = detector.predict_regime(test_returns)
        results['test_regime'] = test_regime
        
        # Save model
        regime_path = os.path.join(MODELS_DIR, f'regime_detector_{version}.pkl')
        detector.save(regime_path)
        
        # Register
        self.registry.register_model(
            model_type='regime',
            model_name='hmm_detector',
            version=version,
            metrics=fit_result.get('regime_stats', {}),
            hyperparameters={'n_regimes': 4},
            filepath=regime_path,
            training_data_hash=data_hash
        )
        
        model_id = f"regime_hmm_detector_{version}"
        self.registry.set_active_model('regime', model_id)
        
        return results
    
    def get_training_status(self, pipeline_id: str = None) -> Dict:
        """Get status of training pipeline(s)."""
        if pipeline_id:
            return self.training_status.get(pipeline_id, {'error': 'Pipeline not found'})
        return self.training_status
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of all registered models."""
        summary = {
            'total_models': 0,
            'by_type': {},
            'active_models': self.registry.models.get('active_versions', {}),
        }
        
        for model_type, models in self.registry.list_models().items():
            summary['total_models'] += len(models)
            summary['by_type'][model_type] = {
                'count': len(models),
                'models': list(models.keys())
            }
        
        return summary


class PredictionService:
    """
    Service for generating predictions using trained models.
    
    Provides:
    - Sector return forecasts
    - Volatility forecasts
    - Regime predictions
    - Causal impact estimates
    """
    
    def __init__(self):
        """Initialize prediction service."""
        self.registry = ModelRegistry()
        self._loaded_models = {}
    
    def _load_model(self, model_type: str) -> Optional[Any]:
        """Load active model for a type."""
        if model_type in self._loaded_models:
            return self._loaded_models[model_type]
        
        model_info = self.registry.get_active_model(model_type)
        if not model_info or 'filepath' not in model_info:
            return None
        
        filepath = model_info['filepath']
        
        # Resolve path: try as-is, then MODELS_DIR/filepath, then MODELS_DIR/basename
        if not os.path.exists(filepath):
            candidates = [
                os.path.join(MODELS_DIR, filepath),
                os.path.join(MODELS_DIR, os.path.basename(filepath)),
            ]
            resolved = next((c for c in candidates if os.path.exists(c)), None)
            if resolved:
                filepath = resolved
            else:
                logger.warning(f"Model file not found: {filepath} (tried: {candidates})")
                return None
        
        try:
            model = joblib.load(filepath)
            self._loaded_models[model_type] = model
            return model
        except Exception as e:
            logger.error(f"Failed to load model {model_type}: {e}")
            return None
    
    def predict_sector_returns(
        self,
        sector: str,
        recent_data: pd.Series,
        horizon: int = 21
    ) -> Dict[str, Any]:
        """
        Predict sector returns.
        
        Args:
            sector: Sector name
            recent_data: Recent return series
            horizon: Forecast horizon in days
            
        Returns:
            Dictionary with predictions
        """
        # Try to load sector-specific model
        forecast_info = self.registry.get_active_model('forecast')
        if not forecast_info:
            return self._fallback_prediction(recent_data, horizon)
        
        # Always use MODELS_DIR for glob — registry path may be stale or from another machine
        models_dir = MODELS_DIR
        raw_path = forecast_info.get('filepath', '')
        if os.path.isdir(raw_path):
            models_dir = raw_path
        
        # Try ARIMA first
        arima_path = os.path.join(models_dir, f'arima_{sector}_*.pkl')
        import glob
        arima_files = glob.glob(arima_path)
        
        predictions = {'ensemble': [], 'models': {}}
        
        if arima_files:
            try:
                arima = ARIMAForecaster()
                arima.load(sorted(arima_files)[-1])
                pred = arima.predict(steps=horizon)
                predictions['models']['arima'] = pred
                predictions['ensemble'].append(pred['mean'])
            except Exception as e:
                logger.warning(f"ARIMA prediction failed: {e}")
        
        # Try GARCH
        garch_path = os.path.join(models_dir, f'garch_{sector}_*.pkl')
        garch_files = glob.glob(garch_path)
        
        if garch_files:
            try:
                garch = GARCHForecaster()
                garch.load(sorted(garch_files)[-1])
                pred = garch.predict(steps=horizon)
                predictions['models']['garch'] = pred
            except Exception as e:
                logger.warning(f"GARCH prediction failed: {e}")
        
        # Ensemble
        if predictions['ensemble']:
            ensemble_mean = np.mean(predictions['ensemble'], axis=0)
            predictions['mean'] = ensemble_mean.tolist()
            predictions['std'] = np.std(predictions['ensemble'], axis=0).tolist()
        else:
            return self._fallback_prediction(recent_data, horizon)
        
        return predictions
    
    def _fallback_prediction(
        self,
        recent_data: pd.Series,
        horizon: int
    ) -> Dict[str, Any]:
        """Simple fallback when no models available."""
        mean_return = recent_data.mean()
        std_return = recent_data.std()
        
        return {
            'mean': [float(mean_return)] * horizon,
            'std': [float(std_return)] * horizon,
            'method': 'historical_mean'
        }
    
    def predict_regime(
        self,
        recent_returns: pd.Series,
        recent_volatility: pd.Series = None
    ) -> Dict[str, Any]:
        """
        Predict current market regime.
        
        Args:
            recent_returns: Recent return series
            recent_volatility: Optional volatility series
            
        Returns:
            Dictionary with regime prediction
        """
        model_info = self.registry.get_active_model('regime')
        
        if model_info:
            filepath = model_info.get('filepath', '')
            # Resolve path: try as-is, then MODELS_DIR/filepath, then MODELS_DIR/basename
            if not os.path.exists(filepath):
                candidates = [
                    os.path.join(MODELS_DIR, filepath),
                    os.path.join(MODELS_DIR, os.path.basename(filepath)),
                ]
                filepath = next((c for c in candidates if os.path.exists(c)), filepath)
            
            if os.path.exists(filepath):
                detector = MarketRegimeDetector()
                detector.load(filepath)
                return detector.predict_regime(recent_returns, recent_volatility)
        
        # Fallback
        detector = MarketRegimeDetector()
        return detector._fallback_predict(recent_returns, recent_volatility)
    
    def get_causal_effects(
        self,
        treatment: str,
        outcome: str
    ) -> Optional[Dict[str, Any]]:
        """Get estimated causal effect between two variables."""
        model = self._load_model('treatment')
        
        if model and 'effects_matrix' in model:
            effects = model['effects_matrix']
            for effect in effects:
                if effect.get('treatment') == treatment and effect.get('outcome') == outcome:
                    return effect
        
        return None
    
    def get_sensitivity_matrix(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Get the trained sensitivity matrix."""
        model = self._load_model('treatment')
        
        if model and 'sensitivity_matrix' in model:
            return model['sensitivity_matrix']
        
        return None


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def run_training_pipeline(
    fred_api_key: str = None,
    start_date: str = '2015-01-01',
    end_date: str = None
) -> Dict[str, Any]:
    """
    Convenience function to run full training pipeline.
    
    Args:
        fred_api_key: FRED API key
        start_date: Start date for training data
        end_date: End date for training data
        
    Returns:
        Training results
    """
    pipeline = MLTrainingPipeline(fred_api_key=fred_api_key)
    return pipeline.run_full_pipeline(start_date=start_date, end_date=end_date)


def get_predictions(
    sector: str,
    recent_data: pd.Series,
    horizon: int = 21
) -> Dict[str, Any]:
    """
    Convenience function to get predictions.
    
    Args:
        sector: Sector to predict
        recent_data: Recent data series
        horizon: Forecast horizon
        
    Returns:
        Predictions dictionary
    """
    service = PredictionService()
    return service.predict_sector_returns(sector, recent_data, horizon)


# Singleton instances
_pipeline = None
_prediction_service = None

def get_training_pipeline(fred_api_key: str = None) -> MLTrainingPipeline:
    """Get or create singleton training pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = MLTrainingPipeline(fred_api_key=fred_api_key)
    return _pipeline

def get_prediction_service() -> PredictionService:
    """Get or create singleton prediction service."""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service
