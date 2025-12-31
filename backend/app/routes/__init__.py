from app.routes.auth import auth_bp
from app.routes.portfolios import portfolios_bp
from app.routes.causal import causal_bp
from app.routes.market import market_bp
from app.routes.scenarios import scenarios_bp
from app.routes.users import users_bp

__all__ = ['auth_bp', 'portfolios_bp', 'causal_bp', 'market_bp', 'scenarios_bp', 'users_bp']
