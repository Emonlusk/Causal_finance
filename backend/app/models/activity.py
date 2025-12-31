from datetime import datetime
from app import db


class Activity(db.Model):
    """Activity model for tracking user actions and system events"""
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Activity info
    activity_type = db.Column(db.String(50), nullable=False)
    # Types: portfolio_rebalance, economic_alert, model_update, scenario_run, 
    #        portfolio_created, causal_analysis, market_alert
    
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Related entity (optional)
    entity_type = db.Column(db.String(50))  # portfolio, causal_model, scenario
    entity_id = db.Column(db.Integer)
    
    # Metadata stored as JSON
    # {"old_weights": {...}, "new_weights": {...}, "reason": "Rate hike impact"}
    activity_metadata = db.Column(db.JSON, default=dict)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Serialize activity to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'title': self.title,
            'description': self.description,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'metadata': self.activity_metadata,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def log_activity(cls, user_id, activity_type, title, description=None, 
                     entity_type=None, entity_id=None, activity_metadata=None):
        """Helper method to create and save an activity"""
        activity = cls(
            user_id=user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_metadata=activity_metadata or {}
        )
        db.session.add(activity)
        db.session.commit()
        return activity
    
    def __repr__(self):
        return f'<Activity {self.activity_type}: {self.title}>'


# Activity type constants
ACTIVITY_TYPES = {
    'portfolio_rebalance': {
        'icon': '📊',
        'color': 'blue'
    },
    'economic_alert': {
        'icon': '⚠️',
        'color': 'yellow'
    },
    'model_update': {
        'icon': '🔄',
        'color': 'green'
    },
    'scenario_run': {
        'icon': '🎮',
        'color': 'purple'
    },
    'portfolio_created': {
        'icon': '✨',
        'color': 'teal'
    },
    'causal_analysis': {
        'icon': '🔍',
        'color': 'indigo'
    },
    'market_alert': {
        'icon': '📈',
        'color': 'red'
    }
}
