"""
ML Models Database Models
=========================
SQLAlchemy models for storing trained ML models, predictions, and training metadata.
"""

from datetime import datetime
from app import db
import json


class TrainedModel(db.Model):
    """Store trained ML model metadata and serialized model files."""
    __tablename__ = 'trained_models'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Model identification
    name = db.Column(db.String(100), nullable=False)  # e.g., "sector_return_predictor"
    model_type = db.Column(db.String(50), nullable=False)  # e.g., "lstm", "xgboost", "garch"
    version = db.Column(db.String(20), nullable=False)  # e.g., "v1.0.0"
    
    # What this model predicts
    target_variable = db.Column(db.String(100))  # e.g., "Technology_Return_21d"
    target_sector = db.Column(db.String(50))  # e.g., "Technology"
    prediction_horizon = db.Column(db.Integer)  # days ahead
    
    # Model storage
    model_path = db.Column(db.String(500))  # Path to serialized model file
    model_size_bytes = db.Column(db.Integer)
    
    # Training configuration
    hyperparameters = db.Column(db.JSON, default=dict)
    feature_columns = db.Column(db.JSON, default=list)  # List of feature names used
    
    # Training data info
    training_start_date = db.Column(db.DateTime)
    training_end_date = db.Column(db.DateTime)
    training_samples = db.Column(db.Integer)
    validation_samples = db.Column(db.Integer)
    
    # Performance metrics
    metrics = db.Column(db.JSON, default=dict)
    # Example: {"rmse": 0.02, "mae": 0.015, "r2": 0.65, "sharpe": 1.2}
    
    # Status
    status = db.Column(db.String(20), default='trained')  # trained, deployed, archived
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'model_type': self.model_type,
            'version': self.version,
            'target_variable': self.target_variable,
            'target_sector': self.target_sector,
            'prediction_horizon': self.prediction_horizon,
            'hyperparameters': self.hyperparameters,
            'feature_columns': self.feature_columns,
            'training_start_date': self.training_start_date.isoformat() if self.training_start_date else None,
            'training_end_date': self.training_end_date.isoformat() if self.training_end_date else None,
            'training_samples': self.training_samples,
            'metrics': self.metrics,
            'status': self.status,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<TrainedModel {self.name} v{self.version}>'


class ModelPrediction(db.Model):
    """Store model predictions for tracking and analysis."""
    __tablename__ = 'model_predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey('trained_models.id'), nullable=False, index=True)
    
    # Prediction details
    prediction_date = db.Column(db.DateTime, nullable=False, index=True)  # When prediction was made
    target_date = db.Column(db.DateTime, nullable=False)  # Date being predicted
    
    # Prediction values
    predicted_value = db.Column(db.Float, nullable=False)
    confidence_lower = db.Column(db.Float)  # Lower bound of CI
    confidence_upper = db.Column(db.Float)  # Upper bound of CI
    confidence_level = db.Column(db.Float, default=0.95)  # e.g., 95% CI
    
    # Actual value (filled in later)
    actual_value = db.Column(db.Float)
    prediction_error = db.Column(db.Float)  # actual - predicted
    
    # Context
    input_features = db.Column(db.JSON)  # Snapshot of features used
    market_regime = db.Column(db.String(20))  # bull, bear, sideways
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    model = db.relationship('TrainedModel', backref=db.backref('predictions', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'prediction_date': self.prediction_date.isoformat() if self.prediction_date else None,
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'predicted_value': self.predicted_value,
            'confidence_lower': self.confidence_lower,
            'confidence_upper': self.confidence_upper,
            'actual_value': self.actual_value,
            'prediction_error': self.prediction_error,
            'market_regime': self.market_regime,
        }


class CausalRelationship(db.Model):
    """Store discovered causal relationships from causal discovery algorithms."""
    __tablename__ = 'causal_relationships'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationship identification
    cause_variable = db.Column(db.String(100), nullable=False, index=True)
    effect_variable = db.Column(db.String(100), nullable=False, index=True)
    
    # Discovery method
    discovery_method = db.Column(db.String(50))  # pc_algorithm, granger, transfer_entropy
    
    # Effect statistics
    effect_size = db.Column(db.Float)  # Estimated causal effect
    effect_std_error = db.Column(db.Float)
    confidence_lower = db.Column(db.Float)
    confidence_upper = db.Column(db.Float)
    p_value = db.Column(db.Float)
    
    # Granger causality specific
    granger_f_statistic = db.Column(db.Float)
    optimal_lag = db.Column(db.Integer)
    
    # Strength and confidence
    edge_strength = db.Column(db.Float)  # 0 to 1
    confidence_score = db.Column(db.Float)  # 0 to 1
    
    # Data info
    sample_size = db.Column(db.Integer)
    data_start_date = db.Column(db.DateTime)
    data_end_date = db.Column(db.DateTime)
    
    # Status
    is_validated = db.Column(db.Boolean, default=False)
    validated_by = db.Column(db.String(50))  # manual, cross_validation, holdout
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'cause_variable': self.cause_variable,
            'effect_variable': self.effect_variable,
            'discovery_method': self.discovery_method,
            'effect_size': self.effect_size,
            'confidence_lower': self.confidence_lower,
            'confidence_upper': self.confidence_upper,
            'p_value': self.p_value,
            'granger_f_statistic': self.granger_f_statistic,
            'optimal_lag': self.optimal_lag,
            'edge_strength': self.edge_strength,
            'confidence_score': self.confidence_score,
            'is_validated': self.is_validated,
        }
    
    def __repr__(self):
        return f'<CausalRelationship {self.cause_variable} -> {self.effect_variable}>'


class MarketRegime(db.Model):
    """Store detected market regimes from HMM or other regime detection models."""
    __tablename__ = 'market_regimes'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Regime identification
    date = db.Column(db.DateTime, nullable=False, index=True, unique=True)
    regime = db.Column(db.String(20), nullable=False)  # bull, bear, sideways, high_volatility
    regime_probability = db.Column(db.Float)  # Probability of being in this regime
    
    # All regime probabilities
    regime_probabilities = db.Column(db.JSON)  # {"bull": 0.7, "bear": 0.2, "sideways": 0.1}
    
    # Market conditions at this date
    vix_level = db.Column(db.Float)
    sp500_return_21d = db.Column(db.Float)
    yield_curve_spread = db.Column(db.Float)
    
    # Model info
    model_id = db.Column(db.Integer, db.ForeignKey('trained_models.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'regime': self.regime,
            'regime_probability': self.regime_probability,
            'regime_probabilities': self.regime_probabilities,
            'vix_level': self.vix_level,
            'sp500_return_21d': self.sp500_return_21d,
        }


class TrainingJob(db.Model):
    """Track model training jobs for async processing."""
    __tablename__ = 'training_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Job identification
    job_type = db.Column(db.String(50), nullable=False)  # full_pipeline, single_model, causal_discovery
    model_type = db.Column(db.String(50))  # lstm, xgboost, garch, etc.
    
    # Configuration
    config = db.Column(db.JSON, default=dict)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    progress = db.Column(db.Float, default=0.0)  # 0 to 100
    current_step = db.Column(db.String(200))
    
    # Results
    result_model_id = db.Column(db.Integer, db.ForeignKey('trained_models.id'))
    error_message = db.Column(db.Text)
    logs = db.Column(db.Text)
    
    # Timing
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_type': self.job_type,
            'model_type': self.model_type,
            'config': self.config,
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'result_model_id': self.result_model_id,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def __repr__(self):
        return f'<TrainingJob {self.id} {self.job_type} {self.status}>'
