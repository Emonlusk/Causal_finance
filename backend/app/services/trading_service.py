"""
Paper Trading Engine
====================
Simulated brokerage: executes market orders at live quotes, maintains
average-cost positions, records every fill with realized P&L, and
snapshots portfolio equity for the equity curve.

All valuation goes through market_service.get_quotes (one batched request
per portfolio) - no fabricated prices. When a live quote is unavailable
the last cached price is used and clearly marked.
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class TradeError(Exception):
    """Raised for rejected orders (insufficient funds/shares, bad symbol...)."""


def get_fill_price(symbol: str) -> Tuple[float, str]:
    """
    Determine the fill price for a market order.
    Returns (price, source). Raises TradeError if no price is available.
    """
    from app.services.market_service import get_quotes
    quotes = get_quotes([symbol])
    q = quotes.get(symbol.upper())
    if not q or not q.get('price'):
        raise TradeError(
            f'No market price available for {symbol}. '
            'The symbol may be invalid or market data is temporarily unavailable.'
        )
    return float(q['price']), q.get('source', 'live')


def execute_trade(
    portfolio,
    user_id: int,
    symbol: str,
    side: str,
    shares: float,
) -> Dict[str, Any]:
    """
    Execute a market order against a portfolio. Mutates portfolio holdings
    and cash, records a Trade row, and returns the fill details.
    Caller is responsible for the DB commit.
    """
    from app import db
    from app.models.trade import Trade
    from sqlalchemy.orm.attributes import flag_modified

    symbol = symbol.upper().strip()
    side = side.lower().strip()
    if side not in ('buy', 'sell'):
        raise TradeError('Action must be "buy" or "sell"')
    try:
        shares = float(shares)
    except (TypeError, ValueError):
        raise TradeError('Shares must be a number')
    if shares <= 0:
        raise TradeError('Shares must be a positive number')

    price, source = get_fill_price(symbol)
    total = price * shares

    holdings = dict(portfolio.holdings or {})
    cash = float(portfolio.cash_balance or 0)
    realized_pnl = None
    avg_cost_at_trade = None

    if side == 'buy':
        if cash < total:
            raise TradeError(
                f'Insufficient portfolio funds. Need ${total:,.2f}, '
                f'portfolio has ${cash:,.2f}. Allocate more cash first.'
            )
        portfolio.cash_balance = cash - total
        pos = holdings.get(symbol)
        if pos:
            old_shares = float(pos.get('shares', 0))
            old_cost = float(pos.get('avg_cost', 0))
            new_shares = old_shares + shares
            new_avg = (old_shares * old_cost + shares * price) / new_shares
            holdings[symbol] = {'shares': new_shares, 'avg_cost': round(new_avg, 4)}
        else:
            holdings[symbol] = {'shares': shares, 'avg_cost': round(price, 4)}
    else:
        pos = holdings.get(symbol)
        held = float(pos.get('shares', 0)) if pos else 0.0
        if held < shares - 1e-9:
            raise TradeError(f'Insufficient shares. Have {held:g}, trying to sell {shares:g}')
        avg_cost_at_trade = float(pos.get('avg_cost', 0))
        realized_pnl = round((price - avg_cost_at_trade) * shares, 2)
        portfolio.cash_balance = cash + total
        remaining = held - shares
        if remaining <= 1e-9:
            holdings.pop(symbol, None)
        else:
            holdings[symbol] = {'shares': remaining, 'avg_cost': pos['avg_cost']}

    portfolio.holdings = holdings
    flag_modified(portfolio, 'holdings')

    trade = Trade(
        user_id=user_id,
        portfolio_id=portfolio.id,
        symbol=symbol,
        side=side,
        shares=shares,
        price=round(price, 4),
        total=round(total, 2),
        price_source=source,
        realized_pnl=realized_pnl,
        avg_cost_at_trade=avg_cost_at_trade,
    )
    db.session.add(trade)

    return {
        'action': side,
        'symbol': symbol,
        'shares': shares,
        'price': round(price, 2),
        'total': round(total, 2),
        'price_source': source,
        'realized_pnl': realized_pnl,
    }


def value_portfolio(portfolio) -> Dict[str, Any]:
    """
    Value all positions with ONE batched quote request.
    Returns enriched holdings + totals. Positions without a live quote are
    valued at last cached price (marked) or cost basis as a last resort.
    """
    from app.services.market_service import get_quotes

    holdings = portfolio.holdings or {}
    cash = float(portfolio.cash_balance or 0)
    if not holdings:
        return {
            'holdings': [], 'total_value': 0.0, 'cash_balance': round(cash, 2),
            'total_equity': round(cash, 2), 'total_cost_basis': 0.0,
            'total_gain_loss': 0.0, 'total_day_change': 0.0,
        }

    symbols = list(holdings.keys())
    quotes = get_quotes(symbols)

    enriched = []
    total_value = 0.0
    total_cost = 0.0
    total_day_change = 0.0

    for symbol, pos in holdings.items():
        shares = float(pos.get('shares', 0))
        avg_cost = float(pos.get('avg_cost', 0))
        q = quotes.get(symbol)

        if q and q.get('price'):
            price = float(q['price'])
            prev = float(q.get('previous_close') or price)
            source = q.get('source', 'live')
        else:
            price = avg_cost
            prev = avg_cost
            source = 'unavailable'

        market_value = price * shares
        cost_basis = avg_cost * shares
        day_change = (price - prev) * shares

        enriched.append({
            'symbol': symbol,
            'shares': shares,
            'avg_cost': round(avg_cost, 2),
            'current_price': round(price, 2),
            'previous_close': round(prev, 2),
            'day_change': round(price - prev, 2),
            'day_change_pct': round((price - prev) / prev * 100, 2) if prev else 0.0,
            'market_value': round(market_value, 2),
            'cost_basis': round(cost_basis, 2),
            'gain_loss': round(market_value - cost_basis, 2),
            'gain_loss_pct': round((price - avg_cost) / avg_cost * 100, 2) if avg_cost else 0.0,
            'price_source': source,
        })
        total_value += market_value
        total_cost += cost_basis
        total_day_change += day_change

    enriched.sort(key=lambda h: -h['market_value'])
    return {
        'holdings': enriched,
        'total_value': round(total_value, 2),
        'cash_balance': round(cash, 2),
        'total_equity': round(total_value + cash, 2),
        'total_cost_basis': round(total_cost, 2),
        'total_gain_loss': round(total_value - total_cost, 2),
        'total_day_change': round(total_day_change, 2),
    }


def snapshot_portfolio(portfolio, valuation: Optional[Dict[str, Any]] = None) -> None:
    """Upsert today's equity snapshot for a portfolio."""
    from app import db
    from app.models.trade import PortfolioSnapshot

    try:
        if valuation is None:
            valuation = value_portfolio(portfolio)
        today = date.today()
        snap = PortfolioSnapshot.query.filter_by(
            portfolio_id=portfolio.id, snapshot_date=today).first()
        if snap is None:
            snap = PortfolioSnapshot(portfolio_id=portfolio.id, snapshot_date=today,
                                     equity=0, cash_balance=0, market_value=0)
            db.session.add(snap)
        snap.equity = valuation['total_equity']
        snap.cash_balance = valuation['cash_balance']
        snap.market_value = valuation['total_value']
    except Exception as e:
        logger.warning(f"Snapshot failed for portfolio {portfolio.id}: {e}")


def snapshot_all_portfolios() -> int:
    """EOD scheduler job: snapshot every active portfolio with holdings or cash."""
    from app import db
    from app.models.portfolio import Portfolio

    count = 0
    portfolios = Portfolio.query.filter(Portfolio.is_active.is_(True)).all()
    for p in portfolios:
        if (p.holdings or {}) or (p.cash_balance or 0) > 0:
            snapshot_portfolio(p)
            count += 1
    db.session.commit()
    return count


def get_equity_curve(portfolio, days: int = 365) -> List[Dict[str, Any]]:
    """Equity curve from stored snapshots, ending with a live point for today."""
    from app.models.trade import PortfolioSnapshot
    from datetime import timedelta

    cutoff = date.today() - timedelta(days=days)
    snaps = (PortfolioSnapshot.query
             .filter(PortfolioSnapshot.portfolio_id == portfolio.id,
                     PortfolioSnapshot.snapshot_date >= cutoff)
             .order_by(PortfolioSnapshot.snapshot_date)
             .all())
    curve = [s.to_dict() for s in snaps]

    # Live point for today
    valuation = value_portfolio(portfolio)
    today_iso = date.today().isoformat()
    live_point = {
        'portfolio_id': portfolio.id,
        'equity': valuation['total_equity'],
        'cash_balance': valuation['cash_balance'],
        'market_value': valuation['total_value'],
        'date': today_iso,
    }
    if curve and curve[-1]['date'] == today_iso:
        curve[-1] = live_point
    else:
        curve.append(live_point)
    return curve
