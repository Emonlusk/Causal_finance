from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User

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
