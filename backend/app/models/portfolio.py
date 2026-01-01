from datetime import datetime
from app import db
import json


class Portfolio(db.Model):
    """Portfolio model for storing user portfolios and allocations"""
    __tablename__ = 'portfolios'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Portfolio info
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    portfolio_type = db.Column(db.String(50), default='custom')  # traditional, causal, custom
    
    # Asset weights stored as JSON: {"XLK": 0.25, "XLV": 0.20, "XLE": 0.15, ...}
    weights = db.Column(db.JSON, default=dict)
    
    # Paper Trading Holdings: {"XLK": {"shares": 100, "avg_cost": 150.50}, ...}
    holdings = db.Column(db.JSON, default=dict)
    
    # Cash allocated to this portfolio for paper trading
    cash_balance = db.Column(db.Float, default=0.0)
    
    # Performance metrics stored as JSON
    # {"expected_return": 0.12, "volatility": 0.15, "sharpe_ratio": 0.8, "max_drawdown": -0.15}
    performance_metrics = db.Column(db.JSON, default=dict)
    
    # Optimization settings
    optimization_objective = db.Column(db.String(50), default='max_sharpe')  # max_sharpe, min_volatility, max_returns
    time_horizon = db.Column(db.String(10), default='1Y')
    
    # Causal factors applied (references to CausalModel insights)
    causal_factors = db.Column(db.JSON, default=list)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Serialize portfolio to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'portfolio_type': self.portfolio_type,
            'weights': self.weights,
            'holdings': self.holdings or {},
            'cash_balance': self.cash_balance or 0.0,
            'performance_metrics': self.performance_metrics,
            'optimization_objective': self.optimization_objective,
            'time_horizon': self.time_horizon,
            'causal_factors': self.causal_factors,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_total_weight(self):
        """Calculate total weight (should sum to 1.0)"""
        if not self.weights:
            return 0.0
        return sum(self.weights.values())
    
    def validate_weights(self):
        """Validate that weights sum to approximately 1.0"""
        total = self.get_total_weight()
        return 0.99 <= total <= 1.01
    
    def __repr__(self):
        return f'<Portfolio {self.name} ({self.portfolio_type})>'


# Sector ETF mappings for reference
SECTOR_ETFS = {
    'XLK': {'name': 'Technology', 'color': '#3B82F6'},
    'XLV': {'name': 'Healthcare', 'color': '#10B981'},
    'XLE': {'name': 'Energy', 'color': '#F59E0B'},
    'XLF': {'name': 'Financials', 'color': '#8B5CF6'},
    'XLI': {'name': 'Industrials', 'color': '#6366F1'},
    'XLY': {'name': 'Consumer Discretionary', 'color': '#EC4899'},
    'XLP': {'name': 'Consumer Staples', 'color': '#14B8A6'},
    'XLU': {'name': 'Utilities', 'color': '#F97316'},
    'XLB': {'name': 'Materials', 'color': '#84CC16'},
    'XLRE': {'name': 'Real Estate', 'color': '#A855F7'},
    'XLC': {'name': 'Communication Services', 'color': '#06B6D4'},
}
