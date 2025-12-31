from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.portfolio import Portfolio, SECTOR_ETFS
from app.models.activity import Activity

portfolios_bp = Blueprint('portfolios', __name__)


@portfolios_bp.route('/', methods=['GET'])
@jwt_required()
def get_portfolios():
    """Get all portfolios for current user"""
    current_user_id = get_jwt_identity()
    portfolios = Portfolio.query.filter_by(user_id=current_user_id).all()
    
    return jsonify({
        'portfolios': [p.to_dict() for p in portfolios]
    }), 200


@portfolios_bp.route('/', methods=['POST'])
@jwt_required()
def create_portfolio():
    """Create a new portfolio"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Portfolio name is required'}), 400
    
    portfolio = Portfolio(
        user_id=current_user_id,
        name=name,
        description=data.get('description'),
        portfolio_type=data.get('portfolio_type', 'custom'),
        weights=data.get('weights', {}),
        optimization_objective=data.get('optimization_objective', 'max_sharpe'),
        time_horizon=data.get('time_horizon', '1Y'),
        causal_factors=data.get('causal_factors', [])
    )
    
    db.session.add(portfolio)
    db.session.commit()
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='portfolio_created',
        title=f'Created portfolio: {name}',
        description=f'New {portfolio.portfolio_type} portfolio created',
        entity_type='portfolio',
        entity_id=portfolio.id
    )
    
    return jsonify({
        'message': 'Portfolio created successfully',
        'portfolio': portfolio.to_dict()
    }), 201


@portfolios_bp.route('/<int:portfolio_id>', methods=['GET'])
@jwt_required()
def get_portfolio(portfolio_id):
    """Get a specific portfolio"""
    current_user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    return jsonify({
        'portfolio': portfolio.to_dict()
    }), 200


@portfolios_bp.route('/<int:portfolio_id>', methods=['PUT'])
@jwt_required()
def update_portfolio(portfolio_id):
    """Update a portfolio"""
    current_user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    data = request.get_json()
    
    # Track if weights changed for activity logging
    weights_changed = False
    old_weights = portfolio.weights.copy() if portfolio.weights else {}
    
    # Update fields
    if 'name' in data:
        portfolio.name = data['name']
    if 'description' in data:
        portfolio.description = data['description']
    if 'weights' in data:
        portfolio.weights = data['weights']
        weights_changed = True
    if 'optimization_objective' in data:
        portfolio.optimization_objective = data['optimization_objective']
    if 'time_horizon' in data:
        portfolio.time_horizon = data['time_horizon']
    if 'causal_factors' in data:
        portfolio.causal_factors = data['causal_factors']
    if 'performance_metrics' in data:
        portfolio.performance_metrics = data['performance_metrics']
    
    db.session.commit()
    
    # Log rebalance activity if weights changed
    if weights_changed:
        Activity.log_activity(
            user_id=current_user_id,
            activity_type='portfolio_rebalance',
            title=f'Rebalanced portfolio: {portfolio.name}',
            description='Portfolio weights updated',
            entity_type='portfolio',
            entity_id=portfolio.id,
            metadata={'old_weights': old_weights, 'new_weights': portfolio.weights}
        )
    
    return jsonify({
        'message': 'Portfolio updated successfully',
        'portfolio': portfolio.to_dict()
    }), 200


@portfolios_bp.route('/<int:portfolio_id>', methods=['DELETE'])
@jwt_required()
def delete_portfolio(portfolio_id):
    """Delete a portfolio"""
    current_user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    portfolio_name = portfolio.name
    db.session.delete(portfolio)
    db.session.commit()
    
    return jsonify({
        'message': f'Portfolio "{portfolio_name}" deleted successfully'
    }), 200


@portfolios_bp.route('/<int:portfolio_id>/performance', methods=['GET'])
@jwt_required()
def get_portfolio_performance(portfolio_id):
    """Get historical performance for a portfolio"""
    current_user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    # Get time range from query params
    period = request.args.get('period', '1Y')  # 1M, 3M, 1Y, ALL
    
    # This would use real market data service in production
    # For now, return structured mock data
    from app.services.portfolio_service import calculate_portfolio_performance
    performance_data = calculate_portfolio_performance(portfolio, period)
    
    return jsonify({
        'portfolio_id': portfolio_id,
        'period': period,
        'performance': performance_data
    }), 200


@portfolios_bp.route('/optimize', methods=['POST'])
@jwt_required()
def optimize_portfolio():
    """Run portfolio optimization"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    objective = data.get('objective', 'max_sharpe')
    assets = data.get('assets', list(SECTOR_ETFS.keys()))
    use_causal = data.get('use_causal', True)
    causal_model_id = data.get('causal_model_id')
    
    # Run optimization
    from app.services.portfolio_service import optimize_portfolio_weights
    result = optimize_portfolio_weights(
        assets=assets,
        objective=objective,
        use_causal=use_causal,
        causal_model_id=causal_model_id,
        user_id=current_user_id
    )
    
    return jsonify(result), 200


@portfolios_bp.route('/backtest', methods=['POST'])
@jwt_required()
def backtest_portfolio():
    """Run portfolio backtest"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    weights = data.get('weights', {})
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    # Run backtest
    from app.services.portfolio_service import run_backtest
    result = run_backtest(weights, start_date, end_date)
    
    return jsonify(result), 200


@portfolios_bp.route('/sectors', methods=['GET'])
def get_sectors():
    """Get available sector ETFs"""
    return jsonify({
        'sectors': SECTOR_ETFS
    }), 200
