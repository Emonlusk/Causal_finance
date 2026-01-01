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
    
    symbol = data.get('symbol', '').upper()
    action = data.get('action', '').lower()  # 'buy' or 'sell'
    shares = data.get('shares', 0)
    
    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400
    if action not in ['buy', 'sell']:
        return jsonify({'error': 'Action must be "buy" or "sell"'}), 400
    if not shares or shares <= 0:
        return jsonify({'error': 'Shares must be a positive number'}), 400
    
    # Get current price using the market service (has fallback support)
    current_price = None
    price_source = 'unknown'
    
    try:
        from app.services.market_service import get_real_time_quote, get_fallback_quote
        
        # Try to get quote from market service (handles caching and fallbacks)
        quote = get_real_time_quote(symbol)
        if quote and quote.get('price'):
            current_price = quote['price']
            price_source = quote.get('source', 'live')
        
        # If market service failed, try direct fallback
        if not current_price:
            fallback = get_fallback_quote(symbol)
            if fallback:
                current_price = fallback['price']
                price_source = 'fallback'
        
        if not current_price:
            return jsonify({
                'error': f'Could not get price for {symbol}. The symbol may be invalid or the market data service is temporarily unavailable.'
            }), 400
            
    except Exception as e:
        # Try direct fallback as last resort
        try:
            from app.services.market_service import get_fallback_quote
            fallback = get_fallback_quote(symbol)
            if fallback:
                current_price = fallback['price']
                price_source = 'fallback'
            else:
                return jsonify({'error': f'Failed to fetch price for {symbol}: {str(e)}'}), 400
        except:
            return jsonify({'error': f'Failed to fetch price for {symbol}: {str(e)}'}), 400
    
    total_cost = current_price * shares
    holdings = portfolio.holdings or {}
    portfolio_cash = portfolio.cash_balance or 0
    
    if action == 'buy':
        # Check if PORTFOLIO has enough cash
        if portfolio_cash < total_cost:
            return jsonify({
                'error': f'Insufficient portfolio funds. Need ${total_cost:,.2f}, portfolio has ${portfolio_cash:,.2f}. Allocate more cash first.'
            }), 400
        
        # Deduct from PORTFOLIO balance
        portfolio.cash_balance = portfolio_cash - total_cost
        
        # Add to portfolio holdings
        if symbol in holdings:
            # Calculate new average cost
            existing_shares = holdings[symbol].get('shares', 0)
            existing_cost = holdings[symbol].get('avg_cost', 0)
            total_shares = existing_shares + shares
            new_avg_cost = ((existing_shares * existing_cost) + (shares * current_price)) / total_shares
            holdings[symbol] = {'shares': total_shares, 'avg_cost': round(new_avg_cost, 2)}
        else:
            holdings[symbol] = {'shares': shares, 'avg_cost': round(current_price, 2)}
        
        activity_title = f'Bought {shares} shares of {symbol}'
        activity_desc = f'Purchased {shares} shares of {symbol} at ${current_price:,.2f}'
        
    else:  # sell
        # Check if portfolio has enough shares
        if symbol not in holdings or holdings[symbol].get('shares', 0) < shares:
            available = holdings.get(symbol, {}).get('shares', 0)
            return jsonify({
                'error': f'Insufficient shares. Have {available}, trying to sell {shares}'
            }), 400
        
        # Add proceeds to PORTFOLIO balance
        portfolio.cash_balance = (portfolio.cash_balance or 0) + total_cost
        
        # Remove from portfolio holdings
        holdings[symbol]['shares'] -= shares
        if holdings[symbol]['shares'] <= 0:
            del holdings[symbol]
        
        activity_title = f'Sold {shares} shares of {symbol}'
        activity_desc = f'Sold {shares} shares of {symbol} at ${current_price:,.2f}'
    
    portfolio.holdings = holdings
    # Mark JSON column as modified (SQLAlchemy doesn't detect in-place changes)
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(portfolio, 'holdings')
    db.session.commit()
    
    # Log activity
    Activity.log_activity(
        user_id=current_user_id,
        activity_type='paper_trade',
        title=activity_title,
        description=activity_desc,
        entity_type='portfolio',
        entity_id=portfolio_id,
        activity_metadata={
            'action': action,
            'symbol': symbol,
            'shares': shares,
            'price': current_price,
            'total': total_cost
        }
    )
    
    return jsonify({
        'message': f'Successfully {action} {shares} shares of {symbol}',
        'trade': {
            'action': action,
            'symbol': symbol,
            'shares': shares,
            'price': current_price,
            'total': total_cost
        },
        'portfolio': portfolio.to_dict(),
        'portfolio_cash': portfolio.cash_balance,
        'user_balance': user.cash_balance
    }), 200


@portfolios_bp.route('/<int:portfolio_id>/holdings', methods=['GET'])
@jwt_required()
def get_portfolio_holdings(portfolio_id):
    """Get current holdings with live prices for a portfolio"""
    current_user_id = get_jwt_identity()
    
    portfolio = Portfolio.query.filter_by(id=portfolio_id, user_id=current_user_id).first()
    if not portfolio:
        return jsonify({'error': 'Portfolio not found'}), 404
    
    holdings = portfolio.holdings or {}
    
    if not holdings:
        return jsonify({
            'portfolio_id': portfolio_id,
            'holdings': [],
            'total_value': 0,
            'cash_balance': portfolio.cash_balance or 0
        }), 200
    
    # Get live prices
    enriched_holdings = []
    total_value = 0
    
    try:
        import yfinance as yf
        for symbol, data in holdings.items():
            try:
                ticker = yf.Ticker(symbol)
                current_price = ticker.info.get('regularMarketPrice', data.get('avg_cost', 0))
                shares = data.get('shares', 0)
                avg_cost = data.get('avg_cost', 0)
                market_value = current_price * shares
                cost_basis = avg_cost * shares
                gain_loss = market_value - cost_basis
                gain_loss_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0
                
                enriched_holdings.append({
                    'symbol': symbol,
                    'shares': shares,
                    'avg_cost': avg_cost,
                    'current_price': round(current_price, 2),
                    'market_value': round(market_value, 2),
                    'cost_basis': round(cost_basis, 2),
                    'gain_loss': round(gain_loss, 2),
                    'gain_loss_pct': round(gain_loss_pct, 2)
                })
                total_value += market_value
            except Exception as e:
                # Use avg_cost if live price fails
                shares = data.get('shares', 0)
                avg_cost = data.get('avg_cost', 0)
                market_value = avg_cost * shares
                enriched_holdings.append({
                    'symbol': symbol,
                    'shares': shares,
                    'avg_cost': avg_cost,
                    'current_price': avg_cost,
                    'market_value': round(market_value, 2),
                    'cost_basis': round(market_value, 2),
                    'gain_loss': 0,
                    'gain_loss_pct': 0,
                    'error': str(e)
                })
                total_value += market_value
    except ImportError:
        # yfinance not available
        for symbol, data in holdings.items():
            shares = data.get('shares', 0)
            avg_cost = data.get('avg_cost', 0)
            market_value = avg_cost * shares
            enriched_holdings.append({
                'symbol': symbol,
                'shares': shares,
                'avg_cost': avg_cost,
                'current_price': avg_cost,
                'market_value': round(market_value, 2),
                'cost_basis': round(market_value, 2),
                'gain_loss': 0,
                'gain_loss_pct': 0
            })
            total_value += market_value
    
    return jsonify({
        'portfolio_id': portfolio_id,
        'portfolio_name': portfolio.name,
        'holdings': enriched_holdings,
        'total_value': round(total_value, 2),
        'cash_balance': portfolio.cash_balance or 0,
        'total_equity': round(total_value + (portfolio.cash_balance or 0), 2)
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
