"""
Local Price Store
=================
Parquet-backed store of daily OHLCV data (dividend/split adjusted) used by
backtests, portfolio optimization, and model training.

Design:
- One parquet file with MultiIndex columns (field, symbol), DatetimeIndex rows.
- Incremental refresh: only downloads rows newer than what is stored, at most
  once per REFRESH_COOLDOWN per symbol batch.
- All heavy downloads are batched through a single yf.download call.

This removes the pattern of every service calling yf.download independently
(slow, rate-limit prone, and previously silently falling back to fake data).
"""

import os
import logging
import threading
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

STORE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'price_store')
STORE_PATH = os.path.join(STORE_DIR, 'daily_prices.parquet')

DEFAULT_START = '2010-01-01'
FIELDS = ['Open', 'High', 'Low', 'Close', 'Volume']

# Don't re-attempt a network refresh for a symbol more often than this
REFRESH_COOLDOWN = timedelta(minutes=30)


def _last_expected_trading_day(now: Optional[datetime] = None) -> date:
    """Most recent weekday with a (likely) completed US trading session."""
    now = now or datetime.utcnow()
    d = now.date()
    # Before ~21:30 UTC the current session hasn't closed; expect previous day
    if now.hour < 22:
        d = d - timedelta(days=1)
    while d.weekday() >= 5:  # Sat/Sun
        d = d - timedelta(days=1)
    return d


class PriceStore:
    """Thread-safe local store of adjusted daily OHLCV prices."""

    def __init__(self, path: str = STORE_PATH):
        self.path = path
        self._lock = threading.RLock()
        self._df: Optional[pd.DataFrame] = None
        self._last_refresh: Dict[str, datetime] = {}
        os.makedirs(os.path.dirname(path), exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> pd.DataFrame:
        if self._df is None:
            if os.path.exists(self.path):
                try:
                    self._df = pd.read_parquet(self.path)
                    self._df.index = pd.to_datetime(self._df.index)
                except Exception as e:
                    logger.error(f"Failed to read price store, rebuilding: {e}")
                    self._df = pd.DataFrame()
            else:
                self._df = pd.DataFrame()
        return self._df

    def _save(self) -> None:
        if self._df is not None and not self._df.empty:
            try:
                self._df.to_parquet(self.path)
            except Exception as e:
                logger.error(f"Failed to persist price store: {e}")

    def _stored_symbols(self) -> List[str]:
        df = self._load()
        if df.empty or not isinstance(df.columns, pd.MultiIndex):
            return []
        return sorted(set(df.columns.get_level_values(1)))

    def _download(self, symbols: List[str], start: str) -> pd.DataFrame:
        """Batched download of adjusted daily OHLCV. Returns (field, symbol) frame."""
        import yfinance as yf

        raw = yf.download(
            symbols, start=start, interval='1d',
            auto_adjust=True, progress=False, group_by='column', threads=True,
        )
        if raw is None or raw.empty:
            return pd.DataFrame()
        if not isinstance(raw.columns, pd.MultiIndex):
            # Single symbol: promote to MultiIndex
            raw.columns = pd.MultiIndex.from_product([raw.columns, [symbols[0]]])
        keep = [c for c in raw.columns if c[0] in FIELDS]
        raw = raw[keep]
        raw.index = pd.to_datetime(raw.index).tz_localize(None)
        return raw

    def _needs_refresh(self, symbols: List[str]) -> List[str]:
        df = self._load()
        stored = set(self._stored_symbols())
        expected = pd.Timestamp(_last_expected_trading_day())
        now = datetime.utcnow()
        out = []
        for s in symbols:
            last_try = self._last_refresh.get(s)
            if last_try and now - last_try < REFRESH_COOLDOWN:
                continue
            if s not in stored:
                out.append(s)
                continue
            col = ('Close', s)
            if col not in df.columns:
                out.append(s)
                continue
            series = df[col].dropna()
            if series.empty or series.index.max() < expected:
                out.append(s)
        return out

    def _refresh(self, symbols: List[str]) -> None:
        """Download and merge fresh rows for the given symbols."""
        to_fetch = self._needs_refresh(symbols)
        if not to_fetch:
            return

        df = self._load()
        # For known symbols only fetch the tail; new symbols get full history
        known = [s for s in to_fetch if s in set(self._stored_symbols())]
        new = [s for s in to_fetch if s not in set(self._stored_symbols())]

        frames = []
        if new:
            logger.info(f"PriceStore: full download for new symbols {new}")
            frames.append(self._download(new, DEFAULT_START))
        if known:
            tail_start = (datetime.utcnow() - timedelta(days=14)).strftime('%Y-%m-%d')
            logger.info(f"PriceStore: incremental refresh for {len(known)} symbols")
            frames.append(self._download(known, tail_start))

        for fresh in frames:
            if fresh is None or fresh.empty:
                continue
            if df.empty:
                df = fresh
            else:
                df = fresh.combine_first(df)

        # De-fragment and persist
        self._df = df.sort_index()
        self._save()
        now = datetime.utcnow()
        for s in to_fetch:
            self._last_refresh[s] = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_history(
        self,
        symbols: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        field: str = 'Close',
        refresh: bool = True,
    ) -> pd.DataFrame:
        """
        Return a DataFrame of daily values (index=date, columns=symbols).
        `Close` is dividend/split adjusted (auto_adjust=True).
        """
        symbols = [s.upper() for s in symbols]
        with self._lock:
            if refresh:
                try:
                    self._refresh(symbols)
                except Exception as e:
                    logger.warning(f"PriceStore refresh failed, serving stored data: {e}")
            df = self._load()
            if df.empty:
                return pd.DataFrame()
            cols = [(field, s) for s in symbols if (field, s) in df.columns]
            if not cols:
                return pd.DataFrame()
            out = df[cols].copy()
            out.columns = [c[1] for c in out.columns]
            if start:
                out = out[out.index >= pd.Timestamp(start)]
            if end:
                out = out[out.index <= pd.Timestamp(end)]
            return out.dropna(how='all')

    def get_returns(
        self,
        symbols: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        refresh: bool = True,
    ) -> pd.DataFrame:
        """Daily simple returns computed from adjusted close."""
        prices = self.get_history(symbols, start=start, end=end, refresh=refresh)
        if prices.empty:
            return pd.DataFrame()
        return prices.pct_change().dropna(how='all')

    def get_ohlcv(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        refresh: bool = True,
    ) -> pd.DataFrame:
        """Full OHLCV frame for one symbol (columns: Open/High/Low/Close/Volume)."""
        symbol = symbol.upper()
        with self._lock:
            if refresh:
                try:
                    self._refresh([symbol])
                except Exception as e:
                    logger.warning(f"PriceStore refresh failed for {symbol}: {e}")
            df = self._load()
            if df.empty:
                return pd.DataFrame()
            cols = [(f, symbol) for f in FIELDS if (f, symbol) in df.columns]
            if not cols:
                return pd.DataFrame()
            out = df[cols].copy()
            out.columns = [c[0] for c in out.columns]
            if start:
                out = out[out.index >= pd.Timestamp(start)]
            if end:
                out = out[out.index <= pd.Timestamp(end)]
            return out.dropna(subset=['Close'])

    def update_all(self) -> Dict[str, int]:
        """Refresh every stored symbol (used by the background scheduler)."""
        with self._lock:
            symbols = self._stored_symbols()
            if not symbols:
                return {'symbols': 0}
            self._last_refresh.clear()
            self._refresh(symbols)
            return {'symbols': len(symbols)}


_store: Optional[PriceStore] = None
_store_lock = threading.Lock()


def get_price_store() -> PriceStore:
    """Singleton accessor."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = PriceStore()
    return _store
