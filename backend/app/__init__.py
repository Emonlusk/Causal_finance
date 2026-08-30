from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache

from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cache = Cache()


def create_app(config_name='default'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == 'production' and not (app.config.get('SECRET_KEY') and app.config.get('JWT_SECRET_KEY')):
        raise RuntimeError(
            'SECRET_KEY and JWT_SECRET_KEY must be set in the production environment. '
            'A random per-process fallback was removed because it silently breaks JWT '
            'verification across gunicorn workers/restarts - set both env vars instead '
            '(render.yaml already declares them with generateValue: true).'
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cache.init_app(app)
    
    # JWT error handlers for better error messages
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({
            'error': 'Invalid token',
            'message': error_string
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token expired',
            'message': 'Please login again'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({
            'error': 'Authorization required',
            'message': error_string
        }), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check whether a token has been revoked (e.g., after logout)"""
        from app.models.revoked_token import RevokedToken
        jti = jwt_payload.get('jti')
        return bool(jti) and RevokedToken.is_revoked(jti)
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token revoked',
            'message': 'Please login again'
        }), 401
    
    # Configure CORS
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.portfolios import portfolios_bp
    from app.routes.causal import causal_bp
    from app.routes.market import market_bp
    from app.routes.scenarios import scenarios_bp
    from app.routes.users import users_bp
    from app.routes.ml import ml_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(portfolios_bp, url_prefix='/api/portfolios')
    app.register_blueprint(causal_bp, url_prefix='/api/causal')
    app.register_blueprint(market_bp, url_prefix='/api/market')
    app.register_blueprint(scenarios_bp, url_prefix='/api/scenarios')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(ml_bp)
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Causal Finance API is running'}
    
    # Create database tables
    with app.app_context():
        db.create_all()

    # Background data refresh (quote prewarm, price store updates)
    from app.services.scheduler import start_scheduler
    start_scheduler(app)

    return app
