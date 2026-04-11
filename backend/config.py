import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database - SQLite for development
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///causal_finance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # CORS - Allow multiple origins
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    
    # API Keys (Free tier APIs)
    FRED_API_KEY = os.getenv('FRED_API_KEY', '')
    ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY', '')
    
    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 3600
    
    # Rate limiting for external APIs
    FRED_RATE_LIMIT = 120
    ALPHA_VANTAGE_RATE_LIMIT = 5
    
    # ============================================
    # RESEARCH PAPER CONFIGURATION
    # ============================================
    
    # Data pipeline dates
    DATA_START_DATE = '2010-01-01'
    TRAIN_END_DATE = '2021-04-30'
    TEST_START_DATE = '2021-05-01'
    DATA_END_DATE = '2024-01-01'
    
    # Portfolio optimization
    RISK_FREE_RATE = 0.04
    MAX_SECTOR_WEIGHT = 0.20                # Enforce per-asset cap in optimizer
    REBALANCE_FREQUENCY = 'monthly'
    TARGET_HORIZON_DAYS = 21
    CAUSAL_BLEND_RATIO = 0.30               # Weight on causal vs traditional
    
    # Causal discovery
    GRANGER_MAX_LAG = 10
    PC_SIGNIFICANCE = 0.05
    
    # Statistical testing
    BOOTSTRAP_ITERATIONS = 10000
    SIGNIFICANCE_LEVEL = 0.05
    
    # Transaction costs (basis points)
    TRANSACTION_COST_BPS = 10
    
    # Backtesting
    BACKTEST_START = '2021-05-01'
    BACKTEST_END = '2024-01-01'
    
    # Asset universe
    SECTOR_UNIVERSE = ['XLK', 'XLV', 'XLE', 'XLF', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE', 'XLC']


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration for Render/Heroku"""
    DEBUG = False

    # Secret keys — Render auto-generates these via render.yaml generateValue
    # Fallback ensures Flask doesn't crash during initial cold-start
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or os.urandom(32).hex()

    # CORS - set to all deployed frontend origins
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS',
        'https://causal-finance.vercel.app,https://causal-finance-frontend.vercel.app'
    ).split(',')

    # Database - handle Render postgres:// → postgresql:// rename
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url or 'sqlite:///causal_finance.db'

    # Stricter security in production
    JWT_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
