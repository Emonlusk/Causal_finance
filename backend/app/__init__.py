from flask import Flask
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
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cache.init_app(app)
    
    # Configure CORS
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.portfolios import portfolios_bp
    from app.routes.causal import causal_bp
    from app.routes.market import market_bp
    from app.routes.scenarios import scenarios_bp
    from app.routes.users import users_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(portfolios_bp, url_prefix='/api/portfolios')
    app.register_blueprint(causal_bp, url_prefix='/api/causal')
    app.register_blueprint(market_bp, url_prefix='/api/market')
    app.register_blueprint(scenarios_bp, url_prefix='/api/scenarios')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return {'status': 'healthy', 'message': 'Causal Finance API is running'}
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
