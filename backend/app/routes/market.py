from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import cache

market_bp = Blueprint('market', __name__)


@market_bp.route('/indicators', methods=['GET'])
@cache.cached(timeout=3600, key_prefix='market_indicators')
def get_market_indicators():
    """Get current market indicators (VIX, Fed Rates, CPI, etc.)"""
    from app.services.market_service import get_current_indicators
    indicators = get_current_indicators()
    
    return jsonify({
        'indicators': indicators
    }), 200


@market_bp.route('/sectors', methods=['GET'])
@cache.cached(timeout=1800, key_prefix='sector_performance')
def get_sector_performance():
    """Get current sector ETF performance"""
    period = request.args.get('period', '1M')  # 1D, 1W, 1M, 3M, 1Y
    
    from app.services.market_service import get_sector_performance
    performance = get_sector_performance(period)
    
    return jsonify({
        'period': period,
        'sectors': performance
    }), 200


@market_bp.route('/historical', methods=['GET'])
def get_historical_data():
    """Get historical market data"""
    symbol = request.args.get('symbol')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    interval = request.args.get('interval', '1d')  # 1d, 1wk, 1mo
    
    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400
    
    from app.services.market_service import get_historical_prices
    data = get_historical_prices(symbol, start_date, end_date, interval)
    
    return jsonify({
        'symbol': symbol,
        'interval': interval,
        'data': data
    }), 200


@market_bp.route('/macro', methods=['GET'])
@cache.cached(timeout=86400, key_prefix='macro_data')  # Cache for 24 hours
def get_macro_data():
    """Get macroeconomic data from FRED"""
    series = request.args.get('series')  # e.g., 'FEDFUNDS', 'CPIAUCSL'
    
    from app.services.market_service import get_fred_data
    
    if series:
        data = get_fred_data(series)
        return jsonify({
            'series': series,
            'data': data
        }), 200
    else:
        # Return all common macro indicators
        data = get_fred_data()
        return jsonify({
            'macro_data': data
        }), 200


@market_bp.route('/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """Get real-time quote for a symbol"""
    from app.services.market_service import get_real_time_quote
    quote = get_real_time_quote(symbol)
    
    if not quote:
        return jsonify({'error': f'Unable to fetch quote for {symbol}'}), 404
    
    return jsonify({
        'symbol': symbol,
        'quote': quote
    }), 200


@market_bp.route('/benchmark', methods=['GET'])
def get_benchmark_performance():
    """Get benchmark (S&P 500) performance"""
    period = request.args.get('period', '1Y')
    
    from app.services.market_service import get_benchmark_data
    data = get_benchmark_data(period)
    
    return jsonify({
        'benchmark': 'SPY',
        'period': period,
        'data': data
    }), 200


@market_bp.route('/condition', methods=['GET'])
@cache.cached(timeout=3600, key_prefix='market_condition')
def get_market_condition():
    """Get overall market condition assessment"""
    from app.services.market_service import assess_market_condition
    condition = assess_market_condition()
    
    return jsonify({
        'condition': condition
    }), 200
