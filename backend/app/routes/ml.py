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
    Predict sector returns with the walk-forward validated ensemble
    (GBM + ARIMA + EGARCH + LSTM). Returns expected return, 90% CI,
    direction probability, and honest validation metrics per horizon.

    Request body: { "sector": "Technology" }
    """
    try:
        data = request.get_json() or {}
        sector = data.get('sector', 'Technology')

        from ..services.prediction_engine import get_prediction_engine
        result = get_prediction_engine().predict_sector(sector)

        if 'error' in result:
            return jsonify({'success': False, **result}), 404

        # Back-compat fields for older frontend components:
        # a 'mean'/'std' daily path derived from the 21d forecast
        h21 = result['horizons'].get('21') or next(iter(result['horizons'].values()), None)
        if h21:
            daily_mean = h21['expected_return'] / 21
            daily_std = (h21['volatility_pct'] / 100) / (21 ** 0.5)
            result['predictions'] = {
                'mean': [daily_mean] * 21,
                'std': [daily_std] * 21,
                'models': result['horizons'],
            }

        return jsonify({'success': True, **result})

    except Exception as e:
        logger.error(f"Sector prediction failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/predict/symbol/<symbol>', methods=['GET'])
def predict_symbol(symbol):
    """
    Per-stock forecast: sector ensemble forecast propagated through the
    stock's beta to its sector ETF plus idiosyncratic volatility.
    """
    try:
        from ..services.prediction_engine import get_prediction_engine
        result = get_prediction_engine().predict_symbol(symbol)
        if 'error' in result:
            return jsonify({'success': False, **result}), 404
        return jsonify({'success': True, **result})
    except Exception as e:
        logger.error(f"Symbol prediction failed for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@ml_bp.route('/forecast/all', methods=['GET'])
def forecast_all():
    """All-sector forecast summary (used by dashboard/predictions page)."""
    try:
        from ..services.prediction_engine import get_prediction_engine
        engine = get_prediction_engine()
        out = {}
        for sector in engine.available_sectors():
            f = engine.predict_sector(sector)
            if 'error' not in f:
                out[sector] = {
                    'etf': f['etf'],
                    'as_of': f['as_of'],
                    'horizons': f['horizons'],
                    'model_version': f['model_version'],
                }
        return jsonify({'success': True, 'forecasts': out})
    except Exception as e:
        logger.error(f"Forecast summary failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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

        # Live returns from the price store (not a stale research parquet)
        from ..services.prediction_engine import SECTOR_TO_ETF, SectorModelBundle
        from ..services.price_store import get_price_store
        from ..services.forecasting_service import GARCHForecaster
        import numpy as np

        sector_key = sector.replace(' ', '_')
        etf = SECTOR_TO_ETF.get(sector_key)
        if not etf:
            return jsonify({'success': False, 'error': f'Unknown sector: {sector}'}), 404

        prices = get_price_store().get_history([etf], start='2018-01-01')
        if prices.empty or etf not in prices.columns:
            return jsonify({'success': False, 'error': 'Price data unavailable'}), 503
        recent_returns = np.log(prices[etf] / prices[etf].shift(1)).dropna()

        # Prefer the trained bundle's EGARCH; refit fresh if missing
        garch = None
        bundle = SectorModelBundle.load(sector_key)
        if bundle is not None and bundle.garch is not None:
            garch = bundle.garch
        if garch is None:
            garch = GARCHForecaster(model_type='EGARCH')
            garch.fit(recent_returns.tail(1000))
            logger.info(f"Fitted fresh EGARCH model for {sector}")

        predictions = garch.predict(steps=horizon, method='simulation', n_simulations=500)
        
        vol_list = predictions['volatility'].tolist() if hasattr(predictions['volatility'], 'tolist') else list(predictions['volatility'])
        var_list = predictions['variance'].tolist() if hasattr(predictions['variance'], 'tolist') else list(predictions['variance'])
        
        return jsonify({
            'success': True,
            'sector': sector,
            'horizon': horizon,
            'predictions': {
                'volatility': vol_list,
                'variance': var_list
            },
            'volatility': vol_list  # Top-level for frontend compatibility
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

def _live_regime_features():
    """Build the regime-detection input frame from live price store data."""
    try:
        import numpy as np
        from ..services.price_store import get_price_store
        prices = get_price_store().get_history(['SPY'], start='2015-01-01')
        if prices.empty or 'SPY' not in prices.columns:
            return None
        frame = pd.DataFrame(index=prices.index)
        frame['SP500_Return'] = prices['SPY'].pct_change()
        frame['SP500_Volatility_21d'] = frame['SP500_Return'].rolling(21).std() * np.sqrt(252)
        return frame.dropna()
    except Exception as e:
        logger.error(f"Live regime features failed: {e}")
        return None


@ml_bp.route('/regime/current', methods=['GET'])
def get_current_regime():
    """
    Get current market regime detection.
    """
    try:
        features = _live_regime_features()
        if features is None:
            return jsonify({'success': False,
                            'error': 'Live market data unavailable for regime detection'}), 503

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
        features = _live_regime_features()
        if features is None:
            return jsonify({'success': False,
                            'error': 'Live market data unavailable for regime detection'}), 503

        regime = detect_current_regime(features)
        current_regime = regime.get('current_regime', 'sideways')

        detector = MarketRegimeDetector()
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
        # Discover relationships first, then build consensus DAG
        relationships = engine.discover_all_relationships(
            sector_returns,
            methods=['granger', 'pc', 'correlation']
        )
        dag = engine.build_causal_dag(relationships)
        
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
        sector_names = [c.replace('_Return_1d', '') for c in sector_cols]
        
        estimator = TreatmentEffectEstimator()
        # First compute effects, then build sensitivity matrix from them
        macro_treatments = [f'{m}_Change' if not m.endswith('_Change') else m for m in available_macro]
        effects = estimator.estimate_macro_sector_effects(
            features, sectors=sector_names, macro_treatments=macro_treatments
        )
        matrix = estimator.build_sensitivity_matrix(effects)
        
        return jsonify({
            'success': True,
            'sensitivity_matrix': matrix,
            'matrix': matrix  # Also at 'matrix' for frontend compatibility
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
