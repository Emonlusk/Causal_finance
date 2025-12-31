from datetime import datetime
from app import db


class Scenario(db.Model):
    """Scenario model for storing simulation configurations and results"""
    __tablename__ = 'scenarios'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Scenario info
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    scenario_type = db.Column(db.String(50), default='custom')  # preset, custom
    
    # Economic shock parameters stored as JSON
    # {
    #   "interest_rates": {"change": 0.02, "current": 0.045},
    #   "inflation": {"change": 0.01, "current": 0.032},
    #   "gdp_growth": {"change": -0.03, "current": 0.025}
    # }
    parameters = db.Column(db.JSON, default=dict)
    
    # Simulation results stored as JSON
    # {
    #   "portfolio_impact": -0.042,
    #   "causal_optimized_impact": -0.018,
    #   "traditional_impact": -0.075,
    #   "sector_impacts": {
    #     "technology": -0.08,
    #     "energy": 0.03,
    #     "healthcare": -0.02
    #   },
    #   "recommendations": [
    #     {"action": "reduce", "sector": "technology", "amount": 0.05},
    #     {"action": "increase", "sector": "energy", "amount": 0.08}
    #   ]
    # }
    results = db.Column(db.JSON, default=dict)
    
    # Associated portfolio (optional)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    run_at = db.Column(db.DateTime)
    
    def to_dict(self):
        """Serialize scenario to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'scenario_type': self.scenario_type,
            'parameters': self.parameters,
            'results': self.results,
            'portfolio_id': self.portfolio_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'run_at': self.run_at.isoformat() if self.run_at else None,
        }
    
    def __repr__(self):
        return f'<Scenario {self.name}>'


# Preset scenario templates
PRESET_SCENARIOS = {
    'fed_hawkish': {
        'name': 'Fed Hawkish',
        'description': 'Federal Reserve raises rates aggressively to combat inflation',
        'parameters': {
            'interest_rates': {'change': 0.02},
            'inflation': {'change': 0.01},
            'gdp_growth': {'change': -0.005}
        }
    },
    'recession': {
        'name': 'Recession',
        'description': 'Economic downturn with falling GDP and employment',
        'parameters': {
            'gdp_growth': {'change': -0.03},
            'interest_rates': {'change': -0.01},
            'unemployment': {'change': 0.02}
        }
    },
    'stagflation': {
        'name': 'Stagflation',
        'description': 'High inflation combined with economic stagnation',
        'parameters': {
            'inflation': {'change': 0.04},
            'gdp_growth': {'change': -0.01},
            'unemployment': {'change': 0.01}
        }
    },
    'oil_shock': {
        'name': 'Oil Shock',
        'description': 'Significant spike in oil prices affecting the economy',
        'parameters': {
            'oil_price': {'change': 0.50},  # 50% increase
            'inflation': {'change': 0.02}
        }
    },
    'tech_correction': {
        'name': 'Tech Correction',
        'description': 'Technology sector experiences significant pullback',
        'parameters': {
            'interest_rates': {'change': 0.015},
            'vix': {'change': 10}  # VIX spike
        }
    },
    'bull_market': {
        'name': 'Bull Market',
        'description': 'Strong economic growth with rising asset prices',
        'parameters': {
            'gdp_growth': {'change': 0.04},
            'interest_rates': {'change': 0.005},
            'unemployment': {'change': -0.01}
        }
    }
}
