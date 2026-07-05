from datetime import datetime
from app import db


class Trade(db.Model):
    """Executed paper trade (order history + realized P&L ledger)."""
    __tablename__ = 'trades'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False, index=True)

    symbol = db.Column(db.String(12), nullable=False, index=True)
    side = db.Column(db.String(4), nullable=False)          # 'buy' | 'sell'
    shares = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)             # fill price
    total = db.Column(db.Float, nullable=False)             # shares * price
    price_source = db.Column(db.String(12), default='live')  # live | cached

    # Realized P&L on sells (vs average cost basis); NULL for buys
    realized_pnl = db.Column(db.Float, nullable=True)
    avg_cost_at_trade = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'portfolio_id': self.portfolio_id,
            'symbol': self.symbol,
            'side': self.side,
            'shares': self.shares,
            'price': self.price,
            'total': self.total,
            'price_source': self.price_source,
            'realized_pnl': self.realized_pnl,
            'avg_cost_at_trade': self.avg_cost_at_trade,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PortfolioSnapshot(db.Model):
    """Daily equity snapshot per portfolio (drives the equity curve)."""
    __tablename__ = 'portfolio_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolios.id'), nullable=False, index=True)

    equity = db.Column(db.Float, nullable=False)            # cash + market value
    cash_balance = db.Column(db.Float, nullable=False)
    market_value = db.Column(db.Float, nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('portfolio_id', 'snapshot_date', name='uq_snapshot_per_day'),
    )

    def to_dict(self):
        return {
            'portfolio_id': self.portfolio_id,
            'equity': round(self.equity, 2),
            'cash_balance': round(self.cash_balance, 2),
            'market_value': round(self.market_value, 2),
            'date': self.snapshot_date.isoformat() if self.snapshot_date else None,
        }
