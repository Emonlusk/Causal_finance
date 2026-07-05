"""
Background Scheduler
====================
Keeps market data warm so the UI always feels live:

- Quote prewarm (every 60s while the US market is open): refreshes the
  sector ETFs, trending symbols, and indicator snapshots so user requests
  hit a warm cache.
- Price store update (every 6h): tops up local daily history used by
  backtests, optimization, and model training.

Disable with DISABLE_SCHEDULER=1 (e.g. on memory-constrained hosts).
"""

import logging
import os

logger = logging.getLogger(__name__)

_scheduler = None


def _prewarm_quotes():
    from app.services import market_service as ms
    try:
        if not ms.get_market_status()['is_open']:
            return
        watch = list(ms.SECTOR_ETFS.keys()) + ms.TRENDING_SYMBOLS + ['SPY', '^VIX', '^TNX']
        ms.get_quotes(sorted(set(watch)))
        ms.get_current_indicators()
    except Exception as e:
        logger.warning(f"Quote prewarm failed: {e}")


def _update_price_store():
    from app.services.price_store import get_price_store
    try:
        result = get_price_store().update_all()
        logger.info(f"Price store updated: {result}")
    except Exception as e:
        logger.warning(f"Price store update failed: {e}")


def _snapshot_portfolios(app):
    """Snapshot equity for every active portfolio (equity curve history)."""
    from app.services.trading_service import snapshot_all_portfolios
    try:
        with app.app_context():
            count = snapshot_all_portfolios()
            logger.info(f"Snapshotted {count} portfolios")
    except Exception as e:
        logger.warning(f"Portfolio snapshots failed: {e}")


def start_scheduler(app) -> None:
    """Start background jobs once per process (skips Flask reloader parent)."""
    global _scheduler
    if _scheduler is not None:
        return
    if os.getenv('DISABLE_SCHEDULER') == '1':
        logger.info("Scheduler disabled via DISABLE_SCHEDULER=1")
        return
    # In debug mode Flask forks a reloader parent; only run in the child
    if app.debug and os.getenv('WERKZEUG_RUN_MAIN') != 'true':
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("APScheduler not installed - background refresh disabled")
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_prewarm_quotes, 'interval', seconds=60,
                       id='prewarm_quotes', max_instances=1, coalesce=True)
    _scheduler.add_job(_update_price_store, 'interval', hours=6,
                       id='update_price_store', max_instances=1, coalesce=True)
    # Twice daily (mid-session + after close ET) portfolio equity snapshots
    _scheduler.add_job(_snapshot_portfolios, 'cron', hour='18,22', minute=15,
                       args=[app], id='snapshot_portfolios',
                       max_instances=1, coalesce=True)
    _scheduler.start()
    logger.info("Background scheduler started (quote prewarm + price store + snapshots)")
