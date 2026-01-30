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


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Production configuration for Render/Heroku"""
    DEBUG = False
    
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        """
        Handle Render's DATABASE_URL format.
        Render uses 'postgres://' but SQLAlchemy 2.0+ requires 'postgresql://'.
        """
        uri = os.getenv('DATABASE_URL', '')
        if uri.startswith('postgres://'):
            uri = uri.replace('postgres://', 'postgresql://', 1)
        return uri or 'sqlite:///causal_finance.db'
    
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
