from flask import Blueprint, request, jsonify

market_bp = Blueprint('market', __name__)

# NOTE: route-level caching removed for quote-bearing endpoints - the market
# service has its own market-hours-aware TTL caches (30s open / 10min closed).
# The old 1-hour route cache made "live" data an hour stale.


@market_bp.route('/indicators', methods=['GET'])
def get_market_indicators():
    """Get current market indicators (VIX, S&P 500, 10Y, Fed rate, CPI)"""
    from app.services.market_service import get_current_indicators
    return jsonify({'indicators': get_current_indicators()}), 200


@market_bp.route('/status', methods=['GET'])
def market_status():
    """US market session status (open / pre / post / closed)"""
    from app.services.market_service import get_market_status
    return jsonify({'status': get_market_status()}), 200


@market_bp.route('/quotes', methods=['GET'])
def get_batch_quotes():
    """Batched quotes: /api/market/quotes?symbols=AAPL,MSFT,SPY"""
    symbols_param = request.args.get('symbols', '')
    symbols = [s.strip().upper() for s in symbols_param.split(',') if s.strip()]
    if not symbols:
        return jsonify({'error': 'symbols query parameter required'}), 400
    if len(symbols) > 50:
        return jsonify({'error': 'Maximum 50 symbols per request'}), 400

    from app.services.market_service import get_quotes
    return jsonify({'quotes': get_quotes(symbols)}), 200


@market_bp.route('/sectors', methods=['GET'])
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
        'symbol': symbol.upper(),
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
def get_market_condition():
    """Get overall market condition assessment"""
    from app.services.market_service import assess_market_condition
    condition = assess_market_condition()

    return jsonify({
        'condition': condition
    }), 200


@market_bp.route('/search', methods=['GET'])
def search_stocks():
    """Search for stocks by symbol or name"""
    query = request.args.get('q', '')

    if not query or len(query) < 1:
        return jsonify({'error': 'Search query required'}), 400

    from app.services.market_service import search_stocks as search_fn
    results = search_fn(query)

    return jsonify({
        'query': query,
        'results': results
    }), 200


@market_bp.route('/news', methods=['GET'])
def get_news():
    """Get financial news, optionally for a specific stock"""
    symbol = request.args.get('symbol')

    from app.services.market_service import get_stock_news
    news = get_stock_news(symbol)

    return jsonify({
        'symbol': symbol or 'market',
        'news': news
    }), 200


@market_bp.route('/trending', methods=['GET'])
def get_trending():
    """Get trending/most active stocks"""
    from app.services.market_service import get_trending_stocks
    stocks = get_trending_stocks()

    return jsonify({
        'trending': stocks
    }), 200
