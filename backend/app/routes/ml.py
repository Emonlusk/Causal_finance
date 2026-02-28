"""
ML API Routes
==============
RESTful API endpoints for ML operations.

Provides:
- Model training endpoints
- Prediction endpoints
- Model status and management
- Causal analysis endpoints
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import logging
import os
import threading
import uuid

# Import ML services
from ..services.ml_training_pipeline import (
    MLTrainingPipeline, 
    PredictionService, 
    ModelRegistry,
    get_training_pipeline,
    get_prediction_service
)
from ..services.data_pipeline import DataPipeline
from ..services.causal_discovery import CausalDiscoveryEngine
from ..services.regime_detection import MarketRegimeDetector, detect_current_regime
import pandas as pd

logger = logging.getLogger(__name__)
ml_bp = Blueprint('ml', __name__, url_prefix='/api/ml')

# Data directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Track async training jobs
_training_jobs = {}


# ============================================
# TRAINING ENDPOINTS
# ============================================

@ml_bp.route('/train', methods=['POST'])
def start_training():
    """
    Start model training pipeline asynchronously in a background thread.
    
    Request body:
    {
        "start_date": "2015-01-01",
        "end_date": null,
        "fred_api_key": "optional_key",
        "skip_data_fetch": false
    }
    
    Returns:
        Training job ID for status polling
    """
    try:
        data = request.get_json() or {}
        
        start_date = data.get('start_date', '2015-01-01')
        end_date = data.get('end_date')
        fred_api_key = data.get('fred_api_key', os.environ.get('FRED_API_KEY'))
        skip_data_fetch = data.get('skip_data_fetch', False)
        
        # Get pipeline
        pipeline = get_training_pipeline(fred_api_key=fred_api_key)
        
        # Create job ID
        job_id = str(uuid.uuid4())[:8]
        _training_jobs[job_id] = {
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'result': None,
            'error': None
        }
        
        # Run training in background thread
        def run_training():
            try:
                result = pipeline.run_full_pipeline(
                    start_date=start_date,
                    end_date=end_date,
                    skip_data_fetch=skip_data_fetch
                )
                if 'error' in result:
                    _training_jobs[job_id]['status'] = 'failed'
                    _training_jobs[job_id]['error'] = result['error']
                else:
                    _training_jobs[job_id]['status'] = 'completed'
                    _training_jobs[job_id]['result'] = {
                        'pipeline_id': result.get('pipeline_id'),
                        'causal': bool(result.get('causal')),
                        'treatment': bool(result.get('treatment')),
                        'forecasting': bool(result.get('forecasting')),
                        'regime': bool(result.get('regime')),
                    }
            except Exception as e:
                logger.error(f"Background training failed: {e}")
                _training_jobs[job_id]['status'] = 'failed'
                _training_jobs[job_id]['error'] = str(e)
            finally:
                _training_jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
        thread = threading.Thread(target=run_training, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Training started in background. Poll /api/ml/train/job/<job_id> for status.',
        })
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/train/job/<job_id>', methods=['GET'])
def get_training_job_status(job_id):
    """Get the status of an async training job."""
    job = _training_jobs.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404
    return jsonify({'success': True, **job})


@ml_bp.route('/train/status', methods=['GET'])
@ml_bp.route('/train/status/<pipeline_id>', methods=['GET'])
def get_training_status(pipeline_id=None):
    """
    Get training status.
    
    Returns:
        Current training status
    """
    try:
        pipeline = get_training_pipeline()
        status = pipeline.get_training_status(pipeline_id)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# DATA ENDPOINTS
# ============================================

@ml_bp.route('/data/fetch', methods=['POST'])
def fetch_data():
    """
    Fetch market and macro data.
    
    Request body:
    {
        "start_date": "2015-01-01",
        "end_date": null,
        "fred_api_key": "optional"
    }
    """
    try:
        data = request.get_json() or {}
        
        start_date = data.get('start_date', '2015-01-01')
        end_date = data.get('end_date')
        fred_api_key = data.get('fred_api_key', os.environ.get('FRED_API_KEY'))
        
        pipeline = DataPipeline(fred_api_key=fred_api_key)
        result = pipeline.run_full_pipeline(start_date=start_date, end_date=end_date)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Data fetch failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/data/status', methods=['GET'])
def get_data_status():
    """
    Get status of available data.
    """
    try:
        status = {
            'sector_data': False,
            'macro_data': False,
            'feature_matrix': False,
            'last_update': None
        }
        
        # Check for data files
        sector_path = os.path.join(DATA_DIR, 'raw', 'sector_etf_prices.parquet')
        macro_path = os.path.join(DATA_DIR, 'raw', 'fred_data.parquet')
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if os.path.exists(sector_path):
            status['sector_data'] = True
            status['last_update'] = datetime.fromtimestamp(
                os.path.getmtime(sector_path)
            ).isoformat()
        
        if os.path.exists(macro_path):
            status['macro_data'] = True
        
        if os.path.exists(feature_path):
            status['feature_matrix'] = True
            df = pd.read_parquet(feature_path)
            status['feature_matrix_rows'] = len(df)
            status['feature_matrix_cols'] = len(df.columns)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Data status check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# PREDICTION ENDPOINTS
# ============================================

@ml_bp.route('/predict/sector', methods=['POST'])
def predict_sector():
    """
    Predict sector returns.
    
    Request body:
    {
        "sector": "Technology",
        "horizon": 21
    }
    """
    try:
        data = request.get_json() or {}
        
        sector = data.get('sector', 'Technology')
        horizon = min(data.get('horizon', 21), 30)  # Cap at 30 days
        
        # Load recent data
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            # Return demo predictions when no data available
            import random
            random.seed(hash(sector))  # Consistent by sector
            
            # Generate realistic-looking predictions based on sector characteristics
            base_returns = {
                'Technology': 0.0012,
                'Financials': 0.0008,
                'Healthcare': 0.0007,
                'Energy': 0.0010,
                'Consumer Staples': 0.0005,
                'Consumer Discretionary': 0.0009,
                'Industrials': 0.0008,
                'Utilities': 0.0004,
                'Real Estate': 0.0006,
                'Materials': 0.0007,
            }
            base = base_returns.get(sector, 0.0008)
            predictions = [base + random.uniform(-0.015, 0.02) for _ in range(horizon)]
            
            return jsonify({
                'success': True,
                'sector': sector,
                'horizon': horizon,
                'predictions': predictions,
                'demo_mode': True,
                'message': 'Using demo predictions. Train ML models for real forecasts.'
            })
        
        features = pd.read_parquet(feature_path)
        
        # Find sector column
        sector_col = f"{sector}_Return_1d"
        if sector_col not in features.columns:
            # Try to find similar
            similar = [c for c in features.columns if sector.lower() in c.lower()]
            if similar:
                sector_col = similar[0]
            else:
                return jsonify({
                    'success': False,
                    'error': f'Sector {sector} not found'
                }), 404
        
        recent_data = features[sector_col].tail(252)  # Last year
        
        service = get_prediction_service()
        predictions = service.predict_sector_returns(sector, recent_data, horizon)
        
        return jsonify({
            'success': True,
            'sector': sector,
            'horizon': horizon,
            'predictions': predictions
        })
        
    except Exception as e:
        logger.error(f"Sector prediction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/predict/volatility', methods=['POST'])
def predict_volatility():
    """
    Predict volatility using GARCH models.
    
    Request body:
    {
        "sector": "Technology",
        "horizon": 21
    }
    """
    try:
        data = request.get_json() or {}
        
        sector = data.get('sector', 'Technology')
        horizon = min(data.get('horizon', 21), 30)  # Cap at 30 days
        
        # Load recent data
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            # Return demo volatility predictions when no data available
            import random
            random.seed(hash(sector) + 42)  # Consistent by sector
            
            # Generate realistic volatility forecasts based on sector
            base_vol = {
                'Technology': 0.022,
                'Financials': 0.020,
                'Healthcare': 0.018,
                'Energy': 0.028,
                'Consumer Staples': 0.012,
                'Consumer Discretionary': 0.024,
                'Industrials': 0.019,
                'Utilities': 0.014,
                'Real Estate': 0.020,
                'Materials': 0.021,
            }
            base = base_vol.get(sector, 0.020)
            volatility = [base * (1 + random.uniform(-0.2, 0.3)) for _ in range(horizon)]
            variance = [v ** 2 for v in volatility]
            
            return jsonify({
                'success': True,
                'sector': sector,
                'horizon': horizon,
                'predictions': {
                    'volatility': volatility,
                    'variance': variance
                },
                'volatility': volatility,  # Also at top level for frontend compatibility
                'demo_mode': True,
                'message': 'Using demo predictions. Train ML models for GARCH forecasts.'
            })
        
        features = pd.read_parquet(feature_path)
        
        # Get return column
        sector_col = f"{sector}_Return_1d"
        if sector_col not in features.columns:
            sector_col = [c for c in features.columns if sector.lower() in c.lower() and 'Return' in c][0]
        
        from ..services.forecasting_service import GARCHForecaster
        
        recent_returns = features[sector_col].dropna().tail(500)
        
        garch = GARCHForecaster()
        garch.fit(recent_returns)
        predictions = garch.predict(steps=horizon)
        
        return jsonify({
            'success': True,
            'sector': sector,
            'horizon': horizon,
            'predictions': {
                'volatility': predictions['volatility'].tolist(),
                'variance': predictions['variance'].tolist()
            }
        })
        
    except Exception as e:
        logger.error(f"Volatility prediction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# REGIME ENDPOINTS
# ============================================

@ml_bp.route('/regime/current', methods=['GET'])
def get_current_regime():
    """
    Get current market regime detection.
    """
    try:
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            # Return demo regime with realistic market data
            import random
            regimes = ['bull_market', 'sideways', 'high_volatility', 'recovery']
            weights = [0.35, 0.40, 0.15, 0.10]  # Realistic distribution
            selected_regime = random.choices(regimes, weights=weights)[0]
            
            regime_descriptions = {
                'bull_market': 'Markets showing positive momentum with healthy economic indicators.',
                'sideways': 'Markets in consolidation phase with mixed signals.',
                'high_volatility': 'Elevated market uncertainty with larger price swings.',
                'recovery': 'Markets rebounding from recent weakness.',
            }
            
            return jsonify({
                'success': True,
                'regime': {
                    'current_regime': selected_regime,
                    'message': regime_descriptions.get(selected_regime, 'Market conditions evolving.'),
                    'confidence': round(random.uniform(0.65, 0.85), 2)
                },
                'demo_mode': True
            })
        
        features = pd.read_parquet(feature_path)
        regime = detect_current_regime(features)
        
        return jsonify({
            'success': True,
            'regime': regime
        })
        
    except Exception as e:
        logger.error(f"Regime detection failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/regime/recommendations', methods=['GET'])
def get_regime_recommendations():
    """
    Get portfolio recommendations for current regime.
    """
    try:
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        current_regime = 'sideways'  # default
        
        if os.path.exists(feature_path):
            features = pd.read_parquet(feature_path)
            regime = detect_current_regime(features)
            current_regime = regime.get('current_regime', 'sideways')
            
            detector = MarketRegimeDetector()
            recommendations = detector.get_regime_recommendations(current_regime)
        else:
            # Return demo recommendations based on typical market conditions
            demo_recommendations = {
                'bull_market': [
                    {'sector': 'Technology', 'action': 'buy', 'reason': 'High growth potential in expansionary markets'},
                    {'sector': 'Consumer Discretionary', 'action': 'buy', 'reason': 'Consumer spending rises in bull markets'},
                    {'sector': 'Financials', 'action': 'buy', 'reason': 'Banks benefit from economic growth'},
                    {'sector': 'Utilities', 'action': 'reduce', 'reason': 'Defensive sectors underperform in bull markets'},
                ],
                'bear_market': [
                    {'sector': 'Consumer Staples', 'action': 'buy', 'reason': 'Defensive positioning for market downturn'},
                    {'sector': 'Healthcare', 'action': 'buy', 'reason': 'Recession-resistant sector'},
                    {'sector': 'Utilities', 'action': 'buy', 'reason': 'Stable dividends in volatile markets'},
                    {'sector': 'Technology', 'action': 'reduce', 'reason': 'High-growth stocks vulnerable to selloff'},
                ],
                'high_volatility': [
                    {'sector': 'Consumer Staples', 'action': 'buy', 'reason': 'Low beta stocks reduce portfolio risk'},
                    {'sector': 'Utilities', 'action': 'buy', 'reason': 'Stability during market turbulence'},
                    {'sector': 'Healthcare', 'action': 'hold', 'reason': 'Defensive with growth potential'},
                    {'sector': 'Energy', 'action': 'reduce', 'reason': 'High volatility amplifies sector swings'},
                ],
                'sideways': [
                    {'sector': 'Financials', 'action': 'buy', 'reason': 'Value opportunities in consolidation'},
                    {'sector': 'Healthcare', 'action': 'buy', 'reason': 'Defensive growth mix'},
                    {'sector': 'Technology', 'action': 'hold', 'reason': 'Wait for directional clarity'},
                    {'sector': 'Industrials', 'action': 'hold', 'reason': 'Cyclical sector needs momentum'},
                ],
                'recovery': [
                    {'sector': 'Industrials', 'action': 'buy', 'reason': 'Early cycle recovery play'},
                    {'sector': 'Materials', 'action': 'buy', 'reason': 'Benefits from economic rebound'},
                    {'sector': 'Financials', 'action': 'buy', 'reason': 'Credit conditions improving'},
                    {'sector': 'Consumer Discretionary', 'action': 'buy', 'reason': 'Consumer confidence recovering'},
                ],
            }
            recommendations = demo_recommendations.get(current_regime, demo_recommendations['sideways'])
        
        return jsonify({
            'success': True,
            'current_regime': current_regime,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logger.error(f"Recommendations failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# CAUSAL ANALYSIS ENDPOINTS
# ============================================

@ml_bp.route('/causal/granger', methods=['POST'])
def compute_granger_causality():
    """
    Compute Granger causality between variables.
    
    Request body:
    {
        "cause_variable": "Fed_Funds_Rate",
        "effect_variable": "Technology_Return_1d",
        "max_lag": 5
    }
    """
    try:
        data = request.get_json() or {}
        
        cause = data.get('cause_variable')
        effect = data.get('effect_variable')
        max_lag = data.get('max_lag', 5)
        
        if not cause or not effect:
            return jsonify({
                'success': False,
                'error': 'cause_variable and effect_variable required'
            }), 400
        
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            return jsonify({
                'success': False,
                'error': 'Feature matrix not found'
            }), 404
        
        features = pd.read_parquet(feature_path)
        
        if cause not in features.columns or effect not in features.columns:
            return jsonify({
                'success': False,
                'error': f'Variables not found in data'
            }), 404
        
        engine = CausalDiscoveryEngine()
        result = engine.granger_causality_test(
            features[[cause, effect]].dropna(),
            cause, effect, max_lag
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Granger causality failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/causal/dag', methods=['GET'])
def get_causal_dag():
    """
    Get the learned causal DAG structure.
    """
    try:
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            return jsonify({
                'success': False,
                'error': 'Feature matrix not found'
            }), 404
        
        features = pd.read_parquet(feature_path)
        
        # Get sector returns
        sector_cols = [c for c in features.columns if c.endswith('_Return_1d')]
        sector_returns = features[sector_cols].dropna()
        
        engine = CausalDiscoveryEngine()
        dag = engine.build_causal_dag(sector_returns)
        
        return jsonify({
            'success': True,
            'dag': dag
        })
        
    except Exception as e:
        logger.error(f"DAG construction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/causal/sensitivity-matrix', methods=['GET'])
def get_sensitivity_matrix():
    """
    Get the learned sensitivity matrix (macro -> sector effects).
    """
    try:
        service = get_prediction_service()
        matrix = service.get_sensitivity_matrix()
        
        if matrix:
            return jsonify({
                'success': True,
                'sensitivity_matrix': matrix,
                'matrix': matrix  # Also at 'matrix' for frontend compatibility
            })
        
        # Fallback to computing on the fly
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            # Return demo sensitivity matrix
            demo_matrix = {
                'Fed_Funds_Rate': {
                    'Technology': -0.015,
                    'Financials': 0.012,
                    'Healthcare': -0.005,
                    'Energy': 0.003,
                    'Consumer Staples': -0.008,
                    'Consumer Discretionary': -0.018,
                    'Industrials': -0.010,
                    'Utilities': -0.020,
                    'Real Estate': -0.025,
                    'Materials': -0.007,
                },
                'CPI_Change': {
                    'Technology': -0.008,
                    'Financials': 0.005,
                    'Healthcare': 0.002,
                    'Energy': 0.025,
                    'Consumer Staples': -0.003,
                    'Consumer Discretionary': -0.012,
                    'Industrials': -0.006,
                    'Utilities': 0.008,
                    'Real Estate': -0.010,
                    'Materials': 0.015,
                },
                'GDP_Growth': {
                    'Technology': 0.020,
                    'Financials': 0.018,
                    'Healthcare': 0.008,
                    'Energy': 0.022,
                    'Consumer Staples': 0.005,
                    'Consumer Discretionary': 0.028,
                    'Industrials': 0.025,
                    'Utilities': 0.003,
                    'Real Estate': 0.015,
                    'Materials': 0.020,
                },
                'VIX': {
                    'Technology': -0.035,
                    'Financials': -0.025,
                    'Healthcare': -0.015,
                    'Energy': -0.020,
                    'Consumer Staples': -0.008,
                    'Consumer Discretionary': -0.030,
                    'Industrials': -0.022,
                    'Utilities': -0.010,
                    'Real Estate': -0.025,
                    'Materials': -0.018,
                },
            }
            return jsonify({
                'success': True,
                'sensitivity_matrix': demo_matrix,
                'matrix': demo_matrix,
                'demo_mode': True,
                'message': 'Using demo sensitivity matrix. Train ML models for real causal analysis.'
            })
        
        features = pd.read_parquet(feature_path)
        
        from ..services.treatment_effects import TreatmentEffectEstimator
        
        macro_cols = ['Fed_Funds_Rate', 'CPI_Change', 'GDP_Change']
        sector_cols = [c for c in features.columns if c.endswith('_Return_1d')]
        
        available_macro = [c for c in macro_cols if c in features.columns]
        
        estimator = TreatmentEffectEstimator()
        matrix = estimator.build_sensitivity_matrix(features, available_macro, sector_cols)
        
        return jsonify({
            'success': True,
            'sensitivity_matrix': matrix
        })
        
    except Exception as e:
        logger.error(f"Sensitivity matrix failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# MODEL MANAGEMENT ENDPOINTS
# ============================================

@ml_bp.route('/models', methods=['GET'])
def list_models():
    """
    List all registered models.
    """
    try:
        registry = ModelRegistry()
        models = registry.list_models()
        
        pipeline = get_training_pipeline()
        summary = pipeline.get_model_summary()
        
        return jsonify({
            'success': True,
            'summary': summary,
            'models': models
        })
        
    except Exception as e:
        logger.error(f"Model listing failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/models/<model_type>/active', methods=['GET'])
def get_active_model(model_type):
    """
    Get active model for a type.
    """
    try:
        registry = ModelRegistry()
        model = registry.get_active_model(model_type)
        
        if model:
            return jsonify({
                'success': True,
                'model': model
            })
        
        return jsonify({
            'success': False,
            'error': f'No active model for type: {model_type}'
        }), 404
        
    except Exception as e:
        logger.error(f"Active model fetch failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/models/<model_type>/<model_id>/activate', methods=['POST'])
def activate_model(model_type, model_id):
    """
    Set a model as active.
    """
    try:
        registry = ModelRegistry()
        success = registry.set_active_model(model_type, model_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Model {model_id} activated'
            })
        
        return jsonify({
            'success': False,
            'error': 'Model not found'
        }), 404
        
    except Exception as e:
        logger.error(f"Model activation failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# HEALTH CHECK
# ============================================

@ml_bp.route('/health', methods=['GET'])
def health_check():
    """
    ML service health check.
    """
    try:
        status = {
            'ml_service': 'healthy',
            'models_available': False,
            'data_available': False
        }
        
        # Check for models
        registry = ModelRegistry()
        models = registry.list_models()
        status['models_available'] = len(models) > 0
        
        # Check for data
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        status['data_available'] = os.path.exists(feature_path)
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'status': {'ml_service': 'unhealthy'},
            'error': str(e)
        }), 500
