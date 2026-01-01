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


# ============================================
# TRAINING ENDPOINTS
# ============================================

@ml_bp.route('/train', methods=['POST'])
def start_training():
    """
    Start model training pipeline.
    
    Request body:
    {
        "start_date": "2015-01-01",
        "end_date": null,
        "fred_api_key": "optional_key",
        "skip_data_fetch": false
    }
    
    Returns:
        Training job status
    """
    try:
        data = request.get_json() or {}
        
        start_date = data.get('start_date', '2015-01-01')
        end_date = data.get('end_date')
        fred_api_key = data.get('fred_api_key', os.environ.get('FRED_API_KEY'))
        skip_data_fetch = data.get('skip_data_fetch', False)
        
        # Get pipeline
        pipeline = get_training_pipeline(fred_api_key=fred_api_key)
        
        # Start training (synchronous for now)
        # TODO: Make async with Celery/Redis
        result = pipeline.run_full_pipeline(
            start_date=start_date,
            end_date=end_date,
            skip_data_fetch=skip_data_fetch
        )
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
        
        return jsonify({
            'success': True,
            'pipeline_id': result.get('pipeline_id'),
            'message': 'Training completed successfully',
            'results': {
                'causal': bool(result.get('causal')),
                'treatment': bool(result.get('treatment')),
                'forecasting': bool(result.get('forecasting')),
                'regime': bool(result.get('regime')),
            }
        })
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        horizon = data.get('horizon', 21)
        
        # Load recent data
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            return jsonify({
                'success': False,
                'error': 'Feature matrix not found. Run data fetch first.'
            }), 404
        
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
        horizon = data.get('horizon', 21)
        
        # Load recent data
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            return jsonify({
                'success': False,
                'error': 'Feature matrix not found'
            }), 404
        
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
            # Return default regime
            return jsonify({
                'success': True,
                'regime': {
                    'current_regime': 'unknown',
                    'message': 'No data available for regime detection'
                }
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
        
        detector = MarketRegimeDetector()
        
        if os.path.exists(feature_path):
            features = pd.read_parquet(feature_path)
            regime = detect_current_regime(features)
            current_regime = regime.get('current_regime', 'sideways')
        else:
            current_regime = 'sideways'
        
        recommendations = detector.get_regime_recommendations(current_regime)
        
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
                'sensitivity_matrix': matrix
            })
        
        # Fallback to computing on the fly
        feature_path = os.path.join(DATA_DIR, 'processed', 'feature_matrix.parquet')
        
        if not os.path.exists(feature_path):
            return jsonify({
                'success': False,
                'error': 'No trained model or data available'
            }), 404
        
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
