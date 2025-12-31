from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    
    # Investment profile
    risk_tolerance = db.Column(db.String(50), default='moderate')  # conservative, moderate, aggressive
    investment_goals = db.Column(db.Text)
    investment_horizon = db.Column(db.String(50), default='5Y')  # 1M, 3M, 1Y, 5Y, 10Y+
    
    # Account info
    plan = db.Column(db.String(50), default='free')  # free, pro, enterprise
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    portfolios = db.relationship('Portfolio', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    causal_models = db.relationship('CausalModel', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    scenarios = db.relationship('Scenario', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_email=False):
        """Serialize user to dictionary"""
        data = {
            'id': self.id,
            'name': self.name,
            'risk_tolerance': self.risk_tolerance,
            'investment_goals': self.investment_goals,
            'investment_horizon': self.investment_horizon,
            'plan': self.plan,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'portfolio_count': self.portfolios.count(),
        }
        if include_email:
            data['email'] = self.email
        return data
    
    def __repr__(self):
        return f'<User {self.email}>'
