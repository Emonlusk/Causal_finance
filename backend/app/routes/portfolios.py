from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.portfolio import Portfolio, SECTOR_ETFS
from app.models.activity import Activity

portfolios_bp = Blueprint('portfolios', __name__)


@portfolios_bp.route('/', methods=['GET'])
@jwt_required(optional=True)
def get_portfolios():
    """Get all portfolios for current user
    
    Returns user's portfolios if authenticated, empty list otherwise.
    """
    current_user_id = get_jwt_identity()
    
    if current_user_id:
        portfolios = Portfolio.query.filter_by(user_id=current_user_id).all()
        return jsonify({
            'portfolios': [p.to_dict() for p in portfolios]
        }), 200
    else:
        return jsonify({
            'portfolios': []
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
            activity_metadata={'old_weights': old_weights, 'new_weights': portfolio.weights}
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
    
    # Computes real returns/Sharpe/drawdown from price_store history; degrades
    # to zeroed metrics + an 'error' field (not fabricated numbers) if price
    # data for this portfolio's assets is unavailable.
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
    risk_tolerance = data.get('risk_tolerance')  # 0.0 (conservative) to 1.0 (aggressive)
    
    # Map risk_tolerance to objective if provided and no explicit objective given
    if risk_tolerance is not None and 'objective' not in data:
        if risk_tolerance <= 0.3:
            objective = 'min_volatility'
        elif risk_tolerance >= 0.7:
            objective = 'max_return'
        else:
            objective = 'max_sharpe'
    
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


# ============================================
# PAPER TRADING ENDPOINTS
# ============================================

@portfolios_bp.route('/<int:portfolio_id>/trade', methods=['POST'])
@jwt_required()
def execute_paper_trade(portfolio_id):
    """Execute a paper trade (buy/sell) in a portfolio"""
    current_user_id = get_jwt_identity()
    from app.models.user import User
    
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    from app.services.trading_service import execute_trade, snapshot_portfolio, TradeError

    try:
        fill = execute_trade(
            portfolio,
            user_id=current_user_id,
            symbol=data.get('symbol', ''),
            side=data.get('action', ''),
            shares=data.get('shares', 0),
        )
        snapshot_portfolio(portfolio)
        db.session.commit()
    except TradeError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Trade failed: {e}'}), 500

    verb = 'Bought' if fill['action'] == 'buy' else 'Sold'
    pnl_note = ''
    if fill.get('realized_pnl') is not None:
        pnl_note = f" (realized P&L ${fill['realized_pnl']:,.2f})"
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='paper_trade',
        title=f"{verb} {fill['shares']:g} shares of {fill['symbol']}",
        description=f"{verb} {fill['shares']:g} shares of {fill['symbol']} "
                    f"at ${fill['price']:,.2f}{pnl_note}",
        entity_type='portfolio',
        entity_id=portfolio_id,
        activity_metadata=fill
    )

    return jsonify({
        'message': f"Successfully {'bought' if fill['action'] == 'buy' else 'sold'} "
                   f"{fill['shares']:g} shares of {fill['symbol']}",
        'trade': fill,
        'portfolio': portfolio.to_dict(),
        'portfolio_cash': portfolio.cash_balance,
        'user_balance': user.cash_balance
    }), 200


@portfolios_bp.route('/<int:portfolio_id>/trades', methods=['GET'])
@jwt_required()
def get_trade_history(portfolio_id):
    """Order history for a portfolio (most recent first)."""
    current_user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404

    from app.models.trade import Trade
    limit = min(int(request.args.get('limit', 100)), 500)
    trades = (Trade.query.filter_by(portfolio_id=portfolio_id)
              .order_by(Trade.created_at.desc()).limit(limit).all())

    realized_total = sum(t.realized_pnl for t in trades if t.realized_pnl is not None)
    return jsonify({
        'portfolio_id': portfolio_id,
        'trades': [t.to_dict() for t in trades],
        'realized_pnl_total': round(realized_total, 2),
        'count': len(trades),
    }), 200


@portfolios_bp.route('/<int:portfolio_id>/equity-curve', methods=['GET'])
@jwt_required()
def get_portfolio_equity_curve(portfolio_id):
    """Equity curve (daily snapshots + live point) for a portfolio."""
    current_user_id = get_jwt_identity()
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404

    from app.services.trading_service import get_equity_curve
    days = min(int(request.args.get('days', 365)), 1825)
    curve = get_equity_curve(portfolio, days=days)
    return jsonify({'portfolio_id': portfolio_id, 'equity_curve': curve}), 200


@portfolios_bp.route('/<int:portfolio_id>/holdings', methods=['GET'])
@jwt_required()
def get_portfolio_holdings(portfolio_id):
    """Get current holdings with live prices for a portfolio"""
    current_user_id = get_jwt_identity()
    
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    from app.services.trading_service import value_portfolio, snapshot_portfolio

    valuation = value_portfolio(portfolio)

    # Opportunistically keep today's equity snapshot fresh
    try:
        snapshot_portfolio(portfolio, valuation)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify({
        'portfolio_id': portfolio_id,
        'portfolio_name': portfolio.name,
        **valuation,
    }), 200


@portfolios_bp.route('/<int:portfolio_id>/allocate-cash', methods=['POST'])
@jwt_required()
def allocate_cash_to_portfolio(portfolio_id):
    """Move cash from user account to portfolio"""
    current_user_id = get_jwt_identity()
    from app.models.user import User
    
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    amount = data.get('amount', 0)
    
    if not amount or amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    
    if user.cash_balance < amount:
        return jsonify({
            'error': f'Insufficient funds. Available: ${user.cash_balance:,.2f}'
        }), 400
    
    user.cash_balance -= amount
    portfolio.cash_balance = (portfolio.cash_balance or 0) + amount
    db.session.commit()
    
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='cash_allocation',
        title=f'Allocated ${amount:,.2f} to {portfolio.name}',
        description=f'Moved ${amount:,.2f} from account to portfolio',
        entity_type='portfolio',
        entity_id=portfolio_id
    )
    
    return jsonify({
        'message': f'Allocated ${amount:,.2f} to {portfolio.name}',
        'user_balance': user.cash_balance,
        'portfolio_balance': portfolio.cash_balance
    }), 200
