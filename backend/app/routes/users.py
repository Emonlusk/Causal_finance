from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.activity import Activity

users_bp = Blueprint('users', __name__)


@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': user.to_dict(include_email=True)
    }), 200


@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if 'name' in data:
        user.name = data['name']
    if 'risk_tolerance' in data:
        if data['risk_tolerance'] in ['conservative', 'moderate', 'aggressive']:
            user.risk_tolerance = data['risk_tolerance']
    if 'investment_goals' in data:
        user.investment_goals = data['investment_goals']
    if 'investment_horizon' in data:
        user.investment_horizon = data['investment_horizon']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Profile updated successfully',
        'user': user.to_dict(include_email=True)
    }), 200


@users_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """Get user settings"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'settings': {
            'risk_tolerance': user.risk_tolerance,
            'investment_goals': user.investment_goals,
            'investment_horizon': user.investment_horizon,
            'plan': user.plan
        }
    }), 200


@users_bp.route('/performance', methods=['GET'])
@jwt_required()
def get_performance():
    """Get user's overall portfolio performance"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get all active portfolios and calculate combined performance
    portfolios = user.portfolios.filter_by(is_active=True).all()
    
    if not portfolios:
        return jsonify({
            'performance': {
                'total_value': 0,
                'total_return': 0,
                'total_return_percent': 0,
                'portfolios': []
            }
        }), 200
    
    # Aggregate performance (this would use real data in production)
    portfolio_summaries = []
    for p in portfolios:
        metrics = p.performance_metrics or {}
        portfolio_summaries.append({
            'id': p.id,
            'name': p.name,
            'type': p.portfolio_type,
            'expected_return': metrics.get('expected_return', 0),
            'volatility': metrics.get('volatility', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0)
        })
    
    return jsonify({
        'performance': {
            'portfolio_count': len(portfolios),
            'portfolios': portfolio_summaries
        }
    }), 200


@users_bp.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_account():
    """Delete user account and all associated data"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Delete user (cascade will delete related data)
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Account deleted successfully'
    }), 200


@users_bp.route('/activities', methods=['GET'])
@jwt_required(optional=True)
def get_activities():
    """Get user's recent activities for the activity feed
    
    Returns user's activities if authenticated, empty list otherwise.
    """
    current_user_id = get_jwt_identity()
    
    if not current_user_id:
        return jsonify({
            'activities': []
        }), 200
    
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    limit = request.args.get('limit', 20, type=int)
    limit = min(limit, 100)  # Cap at 100
    
    activities = Activity.query.filter_by(user_id=current_user_id)\
        .order_by(Activity.created_at.desc())\
        .limit(limit)\
        .all()
    
    return jsonify({
        'activities': [activity.to_dict() for activity in activities]
    }), 200


@users_bp.route('/activities', methods=['POST'])
@jwt_required()
def create_activity():
    """Create a new activity record (for internal use)"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'activity_type' not in data or 'title' not in data:
        return jsonify({'error': 'activity_type and title are required'}), 400
    
    activity = Activity(
        user_id=current_user_id,
        activity_type=data['activity_type'],
        title=data['title'],
        description=data.get('description'),
        entity_type=data.get('entity_type'),
        entity_id=data.get('entity_id'),
        activity_metadata=data.get('metadata')
    )
    
    db.session.add(activity)
    db.session.commit()
    
    return jsonify({
        'message': 'Activity recorded',
        'activity': activity.to_dict()
    }), 201


# ============================================
# PAPER TRADING ENDPOINTS
# ============================================

@users_bp.route('/paper-trading/balance', methods=['GET'])
@jwt_required()
def get_paper_trading_balance():
    """Get user's paper trading cash balance"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'cash_balance': user.cash_balance or 0.0,
        'currency': 'USD'
    }), 200


@users_bp.route('/paper-trading/deposit', methods=['POST'])
@jwt_required()
def deposit_paper_money():
    """Add virtual money to paper trading account"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    amount = data.get('amount', 0)
    
    if not amount or amount <= 0:
        return jsonify({'error': 'Amount must be a positive number'}), 400
    
    if amount > 1000000:
        return jsonify({'error': 'Maximum deposit is $1,000,000'}), 400
    
    user.cash_balance = (user.cash_balance or 0) + amount
    db.session.commit()
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='paper_deposit',
        title=f'Deposited ${amount:,.2f}',
        description=f'Added ${amount:,.2f} to paper trading account',
        activity_metadata={'amount': amount, 'new_balance': user.cash_balance}
    )
    
    return jsonify({
        'message': f'Successfully deposited ${amount:,.2f}',
        'new_balance': user.cash_balance,
        'deposit_amount': amount
    }), 200


@users_bp.route('/paper-trading/withdraw', methods=['POST'])
@jwt_required()
def withdraw_paper_money():
    """Withdraw virtual money from paper trading account"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    amount = data.get('amount', 0)
    
    if not amount or amount <= 0:
        return jsonify({'error': 'Amount must be a positive number'}), 400
    
    current_balance = user.cash_balance or 0
    if amount > current_balance:
        return jsonify({'error': f'Insufficient balance. Available: ${current_balance:,.2f}'}), 400
    
    user.cash_balance = current_balance - amount
    db.session.commit()
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='paper_withdrawal',
        title=f'Withdrew ${amount:,.2f}',
        description=f'Removed ${amount:,.2f} from paper trading account',
        activity_metadata={'amount': amount, 'new_balance': user.cash_balance}
    )
    
    return jsonify({
        'message': f'Successfully withdrew ${amount:,.2f}',
        'new_balance': user.cash_balance,
        'withdrawal_amount': amount
    }), 200
