from datetime import datetime
from app import db


class CausalModel(db.Model):
    """Causal model for storing DAG structures and treatment effects"""
    __tablename__ = 'causal_models'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Model info
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # DAG structure stored as JSON
    # {
    #   "nodes": [
    #     {"id": "rates", "label": "Interest Rates", "type": "economic", "x": 100, "y": 100},
    #     {"id": "tech", "label": "Tech Sector", "type": "asset", "x": 300, "y": 100}
    #   ],
    #   "edges": [
    #     {"from": "rates", "to": "tech", "strength": -0.8, "confidence": 0.95}
    #   ]
    # }
    dag_structure = db.Column(db.JSON, default=dict)
    
    # Treatment effects stored as JSON
    # {
    #   "rates_to_tech": {"effect": -0.008, "ci_lower": -0.012, "ci_upper": -0.004, "p_value": 0.001},
    #   "inflation_to_energy": {"effect": 0.003, "ci_lower": 0.001, "ci_upper": 0.005, "p_value": 0.02}
    # }
    treatment_effects = db.Column(db.JSON, default=dict)
    
    # Confidence scores for each relationship
    confidence_scores = db.Column(db.JSON, default=dict)
    
    # Sector sensitivity matrix
    # {"technology": {"rates": -0.8, "inflation": -0.3, "gdp": 0.5}, ...}
    sector_sensitivity = db.Column(db.JSON, default=dict)
    
    # Model validation metrics
    validation_metrics = db.Column(db.JSON, default=dict)
    
    # Status
    is_validated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Serialize causal model to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'dag_structure': self.dag_structure,
            'treatment_effects': self.treatment_effects,
            'confidence_scores': self.confidence_scores,
            'sector_sensitivity': self.sector_sensitivity,
            'validation_metrics': self.validation_metrics,
            'is_validated': self.is_validated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_nodes(self):
        """Extract nodes from DAG structure"""
        if not self.dag_structure:
            return []
        return self.dag_structure.get('nodes', [])
    
    def get_edges(self):
        """Extract edges from DAG structure"""
        if not self.dag_structure:
            return []
        return self.dag_structure.get('edges', [])
    
    def __repr__(self):
        return f'<CausalModel {self.name}>'


# Default economic factors for causal analysis
ECONOMIC_FACTORS = {
    'interest_rates': {
        'label': 'Interest Rates',
        'fred_series': 'FEDFUNDS',
        'unit': '%',
        'description': 'Federal Funds Effective Rate'
    },
    'inflation': {
        'label': 'Inflation (CPI)',
        'fred_series': 'CPIAUCSL',
        'unit': '%',
        'description': 'Consumer Price Index for All Urban Consumers'
    },
    'gdp_growth': {
        'label': 'GDP Growth',
        'fred_series': 'GDP',
        'unit': '%',
        'description': 'Gross Domestic Product'
    },
    'unemployment': {
        'label': 'Unemployment',
        'fred_series': 'UNRATE',
        'unit': '%',
        'description': 'Unemployment Rate'
    },
    'vix': {
        'label': 'VIX (Volatility)',
        'fred_series': 'VIXCLS',
        'unit': '',
        'description': 'CBOE Volatility Index'
    },
    'oil_price': {
        'label': 'Oil Price',
        'fred_series': 'DCOILWTICO',
        'unit': '$',
        'description': 'Crude Oil Prices: West Texas Intermediate'
    },
    'dollar_index': {
        'label': 'US Dollar Index',
        'fred_series': 'DTWEXBGS',
        'unit': '',
        'description': 'Trade Weighted U.S. Dollar Index'
    }
}
