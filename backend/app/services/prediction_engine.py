"""
Prediction Engine
=================
Sector return prediction built for live serving, replacing the old
ARIMA-only "ensemble".

Per sector (11 SPDR sector ETFs), per horizon (1d / 5d / 21d):

- HistGradientBoostingRegressor  -> expected return  (primary tabular learner)
- HistGradientBoostingClassifier -> P(return > 0)    (direction probability)
- ARIMA on daily returns         -> mean path baseline
- EGARCH(1,1)                    -> volatility forecast, confidence bands
- LSTM (optional, 1d horizon)    -> nonlinear sequence model

Model combination uses inverse-validation-RMSE weights measured with
walk-forward (expanding window) validation - never in-sample fit. Every
prediction returned to the UI carries the validation metrics of the models
behind it, so users see honest accuracy, not marketing.

Feature engineering pulls directly from the local PriceStore (adjusted
daily closes for the ETFs + SPY, ^VIX, ^TNX), so serving-time features are
always current - no dependency on a stale research parquet.
"""

import os
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd
import joblib

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SECTOR_TO_ETF = {
    'Technology': 'XLK',
    'Healthcare': 'XLV',
    'Energy': 'XLE',
    'Financials': 'XLF',
    'Industrials': 'XLI',
    'Consumer_Discretionary': 'XLY',
    'Consumer_Staples': 'XLP',
    'Utilities': 'XLU',
    'Materials': 'XLB',
    'Real_Estate': 'XLRE',
    'Communication_Services': 'XLC',
}
ETF_TO_SECTOR = {v: k for k, v in SECTOR_TO_ETF.items()}

CONTEXT_SYMBOLS = ['SPY', '^VIX', '^TNX']
HORIZONS = [1, 5, 21]
Z_90 = 1.645  # 90% confidence bands


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def build_feature_frame(etf: str, prices: pd.DataFrame) -> pd.DataFrame:
    """
    Build the model feature matrix for one sector ETF.

    `prices`: adjusted close DataFrame containing at least
    [etf, 'SPY', '^VIX', '^TNX'] columns, daily index.
    """
    px = prices[etf].dropna()
    spy = prices['SPY'].reindex(px.index).ffill()
    vix = prices['^VIX'].reindex(px.index).ffill()
    tnx = prices['^TNX'].reindex(px.index).ffill()

    ret = np.log(px / px.shift(1))
    spy_ret = np.log(spy / spy.shift(1))

    f = pd.DataFrame(index=px.index)
    # Own dynamics
    for lag in [1, 2, 3, 5, 10, 21]:
        f[f'ret_{lag}d'] = np.log(px / px.shift(lag))
    f['vol_5d'] = ret.rolling(5).std()
    f['vol_21d'] = ret.rolling(21).std()
    f['vol_ratio'] = f['vol_5d'] / f['vol_21d']
    f['rsi_14'] = _rsi(px) / 100.0
    f['dist_sma50'] = px / px.rolling(50).mean() - 1
    f['dist_sma200'] = px / px.rolling(200).mean() - 1
    # Market context
    f['spy_ret_1d'] = spy_ret
    f['spy_ret_21d'] = np.log(spy / spy.shift(21))
    f['spy_vol_21d'] = spy_ret.rolling(21).std()
    f['rel_strength_21d'] = f['ret_21d'] - f['spy_ret_21d']
    f['vix_level'] = vix / 100.0
    f['vix_chg_5d'] = vix.pct_change(5)
    f['tnx_level'] = tnx / 100.0
    f['tnx_chg_21d'] = tnx.diff(21) / 100.0
    # Calendar
    f['month'] = px.index.month / 12.0
    f['dow'] = px.index.dayofweek / 4.0

    return f


def build_targets(etf: str, prices: pd.DataFrame) -> Dict[int, pd.Series]:
    """Forward log return over each horizon (aligned to feature date)."""
    px = prices[etf].dropna()
    return {h: np.log(px.shift(-h) / px) for h in HORIZONS}


# ---------------------------------------------------------------------------
# Per-sector model bundle
# ---------------------------------------------------------------------------

class SectorModelBundle:
    """Everything needed to serve one sector's forecasts."""

    def __init__(self, sector: str):
        self.sector = sector
        self.etf = SECTOR_TO_ETF[sector]
        self.version: str = ''
        self.feature_cols: List[str] = []
        self.gbm_reg: Dict[int, Any] = {}      # horizon -> regressor
        self.gbm_clf: Dict[int, Any] = {}      # horizon -> direction classifier
        self.arima = None                      # fitted ARIMAForecaster
        self.garch = None                      # fitted GARCHForecaster
        self.lstm = None                       # fitted LSTMForecaster (1d)
        self.weights: Dict[int, Dict[str, float]] = {}   # horizon -> model weights
        self.validation: Dict[str, Any] = {}   # honest walk-forward metrics
        self.trained_at: str = ''

    # -- persistence ---------------------------------------------------
    def path(self) -> str:
        return os.path.join(MODELS_DIR, f'sector_bundle_{self.sector}.pkl')

    def save(self):
        lstm_state = None
        if self.lstm is not None:
            # LSTM persists separately via its own torch save
            lstm_path = os.path.join(MODELS_DIR, f'lstm_v2_{self.sector}.pt')
            try:
                self.lstm.save(lstm_path)
                lstm_state = lstm_path
            except Exception as e:
                logger.warning(f"LSTM save failed for {self.sector}: {e}")
        payload = {
            'sector': self.sector, 'etf': self.etf, 'version': self.version,
            'feature_cols': self.feature_cols,
            'gbm_reg': self.gbm_reg, 'gbm_clf': self.gbm_clf,
            'arima': self.arima, 'garch': self.garch,
            'lstm_path': lstm_state,
            'weights': self.weights, 'validation': self.validation,
            'trained_at': self.trained_at,
        }
        joblib.dump(payload, self.path())

    @classmethod
    def load(cls, sector: str) -> Optional['SectorModelBundle']:
        bundle = cls(sector)
        if not os.path.exists(bundle.path()):
            return None
        try:
            payload = joblib.load(bundle.path())
            bundle.version = payload.get('version', '')
            bundle.feature_cols = payload['feature_cols']
            bundle.gbm_reg = payload['gbm_reg']
            bundle.gbm_clf = payload['gbm_clf']
            bundle.arima = payload.get('arima')
            bundle.garch = payload.get('garch')
            bundle.weights = payload['weights']
            bundle.validation = payload.get('validation', {})
            bundle.trained_at = payload.get('trained_at', '')
            lstm_path = payload.get('lstm_path')
            if lstm_path and os.path.exists(lstm_path):
                try:
                    from app.services.forecasting_service import LSTMForecaster
                    lstm = LSTMForecaster()
                    lstm.load(lstm_path)
                    bundle.lstm = lstm
                except Exception as e:
                    logger.warning(f"LSTM load failed for {sector}: {e}")
            return bundle
        except Exception as e:
            logger.error(f"Bundle load failed for {sector}: {e}")
            return None


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def _make_gbm_reg():
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(
        max_iter=300, max_depth=4, learning_rate=0.03,
        l2_regularization=1.0, early_stopping=True,
        validation_fraction=0.15, random_state=42,
    )


def _make_gbm_clf():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        max_iter=300, max_depth=4, learning_rate=0.03,
        l2_regularization=1.0, early_stopping=True,
        validation_fraction=0.15, random_state=42,
    )


def _fit_arima_returns(train_returns: pd.Series):
    """Small-grid ARIMA on daily returns (d=0: returns are stationary)."""
    from statsmodels.tsa.arima.model import ARIMA
    best = None
    best_aic = np.inf
    for p in (1, 2):
        for q in (1, 2):
            try:
                fit = ARIMA(train_returns, order=(p, 0, q)).fit()
                if fit.aic < best_aic:
                    best_aic, best = fit.aic, fit
            except Exception:
                continue
    return best


def _walk_forward_slices(n: int, n_folds: int = 4, test_len: int = 126,
                         min_train: int = 756) -> List[Tuple[int, int, int]]:
    """(train_end, test_start, test_end) index triples, expanding window."""
    slices = []
    end = n
    for _ in range(n_folds):
        test_end = end
        test_start = test_end - test_len
        train_end = test_start
        if train_end < min_train:
            break
        slices.append((train_end, test_start, test_end))
        end = test_start
    return list(reversed(slices))


def train_sector(
    sector: str,
    prices: pd.DataFrame,
    version: str,
    train_lstm: bool = True,
) -> Tuple[Optional[SectorModelBundle], Dict[str, Any]]:
    """Train + walk-forward validate all models for one sector."""
    etf = SECTOR_TO_ETF[sector]
    if etf not in prices.columns:
        return None, {'error': f'No price data for {etf}'}

    features = build_feature_frame(etf, prices)
    targets = build_targets(etf, prices)
    ret_1d = np.log(prices[etf] / prices[etf].shift(1)).dropna()

    # Align features/targets, drop warmup NaNs
    valid = features.dropna().index
    bundle = SectorModelBundle(sector)
    bundle.version = version
    bundle.feature_cols = list(features.columns)
    bundle.trained_at = datetime.utcnow().isoformat()

    validation: Dict[str, Any] = {'horizons': {}}

    for h in HORIZONS:
        y = targets[h]
        idx = valid.intersection(y.dropna().index)
        X_all = features.loc[idx].values
        y_all = y.loc[idx].values
        n = len(idx)
        if n < 900:
            continue

        slices = _walk_forward_slices(n)
        fold_metrics = {'gbm': [], 'arima': [], 'naive': [], 'gbm_dir': [], 'clf_dir': []}

        for train_end, test_start, test_end in slices:
            X_tr, y_tr = X_all[:train_end], y_all[:train_end]
            X_te, y_te = X_all[test_start:test_end], y_all[test_start:test_end]

            # GBM regressor
            try:
                reg = _make_gbm_reg()
                reg.fit(X_tr, y_tr)
                pred = reg.predict(X_te)
                fold_metrics['gbm'].append(float(np.sqrt(np.mean((pred - y_te) ** 2))))
                fold_metrics['gbm_dir'].append(float(np.mean(np.sign(pred) == np.sign(y_te))))
            except Exception as e:
                logger.warning(f"GBM fold failed ({sector} h={h}): {e}")

            # Direction classifier accuracy
            try:
                clf = _make_gbm_clf()
                clf.fit(X_tr, (y_tr > 0).astype(int))
                proba = clf.predict_proba(X_te)[:, 1]
                fold_metrics['clf_dir'].append(float(np.mean((proba > 0.5) == (y_te > 0))))
            except Exception:
                pass

            # ARIMA baseline: h-step path sum, refit per fold on fold train
            if h in (1, 5):  # ARIMA path degrades at 21d; skip to save time
                try:
                    fold_dates = idx[:train_end]
                    arima_fit = _fit_arima_returns(ret_1d.loc[ret_1d.index.isin(fold_dates)].iloc[-1500:])
                    if arima_fit is not None:
                        # Static h-step forecast reused across the fold (cheap proxy)
                        fc = float(np.sum(arima_fit.forecast(steps=h)))
                        preds = np.full(len(y_te), fc)
                        fold_metrics['arima'].append(float(np.sqrt(np.mean((preds - y_te) ** 2))))
                except Exception:
                    pass

            # Naive zero-return baseline (the bar to beat in finance)
            fold_metrics['naive'].append(float(np.sqrt(np.mean(y_te ** 2))))

        h_val = {}
        for k, vals in fold_metrics.items():
            if vals:
                h_val[k if 'dir' in k else f'{k}_rmse'] = round(float(np.mean(vals)), 6)
        validation['horizons'][str(h)] = h_val

        # Final fit on ALL data
        try:
            reg = _make_gbm_reg()
            reg.fit(X_all, y_all)
            bundle.gbm_reg[h] = reg
            clf = _make_gbm_clf()
            clf.fit(X_all, (y_all > 0).astype(int))
            bundle.gbm_clf[h] = clf
        except Exception as e:
            logger.error(f"Final GBM fit failed ({sector} h={h}): {e}")

        # Ensemble weights: inverse walk-forward RMSE (only models that ran)
        weights = {}
        gbm_rmse = h_val.get('gbm_rmse')
        arima_rmse = h_val.get('arima_rmse')
        if gbm_rmse:
            weights['gbm'] = 1.0 / gbm_rmse
        if arima_rmse:
            weights['arima'] = 1.0 / arima_rmse
        total = sum(weights.values()) or 1.0
        bundle.weights[h] = {k: round(v / total, 4) for k, v in weights.items()}

    # ARIMA final fit (for the mean path served live)
    try:
        from app.services.forecasting_service import ARIMAForecaster
        arima = ARIMAForecaster(max_p=3, max_d=0, max_q=3)
        arima.fit(ret_1d.iloc[-2000:], order=(2, 0, 2))
        bundle.arima = arima
    except Exception as e:
        logger.warning(f"ARIMA final fit failed for {sector}: {e}")

    # EGARCH final fit (volatility / confidence bands)
    try:
        from app.services.forecasting_service import GARCHForecaster
        garch = GARCHForecaster(model_type='EGARCH')
        garch.fit(ret_1d.iloc[-2000:])
        bundle.garch = garch
    except Exception as e:
        logger.warning(f"GARCH final fit failed for {sector}: {e}")

    # LSTM (1-day horizon, multivariate features)
    if train_lstm:
        try:
            from app.services.forecasting_service import LSTMForecaster
            seq_len = 40
            idx1 = valid.intersection(targets[1].dropna().index)
            F = features.loc[idx1].values
            y1 = targets[1].loc[idx1].values
            X_seq, y_seq = [], []
            for i in range(seq_len, len(F)):
                X_seq.append(F[i - seq_len:i])
                y_seq.append(y1[i])
            X_seq, y_seq = np.array(X_seq), np.array(y_seq)
            if len(X_seq) > 500:
                # Hold out last 15% to measure real out-of-sample RMSE
                split = int(len(X_seq) * 0.85)
                lstm = LSTMForecaster(sequence_length=seq_len, hidden_size=48, num_layers=1)
                lstm.fit(X_seq[:split], y_seq[:split], epochs=40, early_stopping_patience=6)
                oos = lstm.predict(X_seq[split:])
                if 'predictions' in oos:
                    preds = np.array(oos['predictions'])
                    lstm_rmse = float(np.sqrt(np.mean((preds - y_seq[split:]) ** 2)))
                    lstm_dir = float(np.mean(np.sign(preds) == np.sign(y_seq[split:])))
                    validation['horizons'].setdefault('1', {})['lstm_rmse'] = round(lstm_rmse, 6)
                    validation['horizons']['1']['lstm_dir'] = round(lstm_dir, 4)
                    # Add to 1d ensemble weights
                    w = bundle.weights.get(1, {})
                    raw = {k: 1.0 / validation['horizons']['1'][f'{k}_rmse']
                           for k in ('gbm', 'arima', 'lstm')
                           if validation['horizons']['1'].get(f'{k}_rmse')}
                    total = sum(raw.values()) or 1.0
                    bundle.weights[1] = {k: round(v / total, 4) for k, v in raw.items()}
                    # Refit on all data for serving
                    lstm.fit(X_seq, y_seq, epochs=25, early_stopping_patience=5)
                    bundle.lstm = lstm
        except Exception as e:
            logger.warning(f"LSTM training failed for {sector}: {e}")

    bundle.validation = validation
    bundle.save()
    return bundle, validation


def train_all_sectors(
    version: Optional[str] = None,
    train_lstm: bool = True,
    sectors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Train every sector bundle from PriceStore data. Returns metrics summary."""
    from app.services.price_store import get_price_store

    version = version or datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    sectors = sectors or list(SECTOR_TO_ETF.keys())

    symbols = [SECTOR_TO_ETF[s] for s in sectors] + CONTEXT_SYMBOLS
    prices = get_price_store().get_history(symbols, start='2012-01-01')
    if prices.empty:
        return {'error': 'No price data available'}

    results = {'version': version, 'sectors': {}}
    for sector in sectors:
        logger.info(f"Training {sector}...")
        try:
            bundle, val = train_sector(sector, prices, version, train_lstm=train_lstm)
            results['sectors'][sector] = val if bundle else {'error': val.get('error', 'failed')}
        except Exception as e:
            logger.error(f"Training failed for {sector}: {e}")
            results['sectors'][sector] = {'error': str(e)}

    # Register with the model registry so /ml/models reflects reality
    try:
        from app.services.ml_training_pipeline import ModelRegistry
        registry = ModelRegistry()
        registry.register_model(
            model_type='forecast',
            model_name='ensemble_v2',
            version=version,
            metrics=results['sectors'],
            hyperparameters={
                'models': ['gbm', 'arima', 'egarch'] + (['lstm'] if train_lstm else []),
                'horizons': HORIZONS,
                'validation': 'walk_forward_4x126d',
            },
            filepath=MODELS_DIR,
        )
        registry.set_active_model('forecast', f'forecast_ensemble_v2_{version}')
    except Exception as e:
        logger.warning(f"Registry update failed: {e}")

    return results


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------

class PredictionEngine:
    """Loads sector bundles and serves live forecasts."""

    def __init__(self):
        self._bundles: Dict[str, SectorModelBundle] = {}
        self._lock = threading.Lock()

    def _get_bundle(self, sector: str) -> Optional[SectorModelBundle]:
        with self._lock:
            if sector not in self._bundles:
                bundle = SectorModelBundle.load(sector)
                if bundle:
                    self._bundles[sector] = bundle
            return self._bundles.get(sector)

    def invalidate(self):
        with self._lock:
            self._bundles.clear()

    def available_sectors(self) -> List[str]:
        return [s for s in SECTOR_TO_ETF if os.path.exists(
            os.path.join(MODELS_DIR, f'sector_bundle_{s}.pkl'))]

    # ------------------------------------------------------------------
    def predict_sector(self, sector: str) -> Dict[str, Any]:
        """
        Live forecast for one sector: expected return, 90% bands, P(up),
        per-model detail + honest validation metrics.
        """
        sector = sector.replace(' ', '_')
        if sector not in SECTOR_TO_ETF:
            return {'error': f'Unknown sector: {sector}'}
        bundle = self._get_bundle(sector)
        if bundle is None:
            return {'error': f'No trained model for {sector}. Run training first.'}

        from app.services.price_store import get_price_store
        etf = bundle.etf
        prices = get_price_store().get_history([etf] + CONTEXT_SYMBOLS, start='2018-01-01')
        if prices.empty or etf not in prices.columns:
            return {'error': 'Price data unavailable'}

        features = build_feature_frame(etf, prices).dropna()
        if features.empty:
            return {'error': 'Insufficient feature history'}
        x_now = features.iloc[[-1]][bundle.feature_cols].values
        as_of = features.index[-1].strftime('%Y-%m-%d')

        # Daily vol forecast path from EGARCH ('variance' key is DAILY variance;
        # the 'volatility' key is annualized, so don't use it here)
        vol_path = None
        if bundle.garch is not None:
            try:
                # EGARCH multi-step needs simulation (analytic only supports h=1)
                g = bundle.garch.predict(steps=max(HORIZONS), method='simulation',
                                         n_simulations=500)
                if 'variance' in g:
                    vol_path = np.sqrt(np.asarray(g['variance'], dtype=float))
            except Exception as e:
                logger.debug(f"GARCH predict failed: {e}")
        if vol_path is None:
            ret = np.log(prices[etf] / prices[etf].shift(1)).dropna()
            vol_path = np.full(max(HORIZONS), float(ret.tail(63).std()))

        # ARIMA mean path
        arima_path = None
        if bundle.arima is not None:
            try:
                a = bundle.arima.predict(steps=max(HORIZONS))
                key = 'forecast' if 'forecast' in a else 'mean'
                if key in a:
                    arima_path = np.asarray(a[key], dtype=float)
            except Exception as e:
                logger.debug(f"ARIMA predict failed: {e}")

        # LSTM 1d prediction
        lstm_1d = None
        if bundle.lstm is not None:
            try:
                seq_len = bundle.lstm.sequence_length
                F = features[bundle.feature_cols].values
                if len(F) >= seq_len:
                    out = bundle.lstm.predict(F[-seq_len:][None, :, :])
                    if 'predictions' in out:
                        lstm_1d = float(out['predictions'][0])
            except Exception as e:
                logger.debug(f"LSTM predict failed: {e}")

        horizons_out = {}
        for h in HORIZONS:
            preds = {}
            if h in bundle.gbm_reg:
                try:
                    preds['gbm'] = float(bundle.gbm_reg[h].predict(x_now)[0])
                except Exception:
                    pass
            if arima_path is not None:
                preds['arima'] = float(np.sum(arima_path[:h]))
            if h == 1 and lstm_1d is not None:
                preds['lstm'] = lstm_1d

            weights = bundle.weights.get(h, {})
            avail = {k: v for k, v in preds.items() if k in weights} or preds
            if not avail:
                continue
            w = {k: weights.get(k, 1.0) for k in avail}
            total = sum(w.values()) or 1.0
            expected = sum(avail[k] * w[k] / total for k in avail)

            # Horizon volatility: sqrt of summed daily variances
            h_vol = float(np.sqrt(np.sum(vol_path[:h] ** 2)))

            # Direction probability: classifier blended with Normal-implied
            p_up = None
            if h in bundle.gbm_clf:
                try:
                    p_clf = float(bundle.gbm_clf[h].predict_proba(x_now)[0, 1])
                    from scipy.stats import norm
                    p_normal = float(norm.cdf(expected / h_vol)) if h_vol > 0 else 0.5
                    p_up = 0.6 * p_clf + 0.4 * p_normal
                except Exception:
                    pass

            val = bundle.validation.get('horizons', {}).get(str(h), {})
            horizons_out[str(h)] = {
                'expected_return': round(float(expected), 6),
                'expected_return_pct': round(float(expected) * 100, 3),
                'ci_lower_pct': round((float(expected) - Z_90 * h_vol) * 100, 3),
                'ci_upper_pct': round((float(expected) + Z_90 * h_vol) * 100, 3),
                'volatility_pct': round(h_vol * 100, 3),
                'prob_up': round(p_up, 4) if p_up is not None else None,
                'model_predictions_pct': {k: round(v * 100, 3) for k, v in preds.items()},
                'ensemble_weights': {k: round(w[k] / total, 3) for k in avail},
                'validation': val,
            }

        return {
            'sector': sector,
            'etf': etf,
            'as_of': as_of,
            'horizons': horizons_out,
            'model_version': bundle.version,
            'trained_at': bundle.trained_at,
            'method': 'walk-forward validated ensemble (GBM + ARIMA + EGARCH'
                      + (' + LSTM' if bundle.lstm else '') + ')',
        }

    # ------------------------------------------------------------------
    def predict_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Per-stock forecast: sector ensemble forecast propagated through the
        stock's beta to its sector ETF, plus idiosyncratic volatility.
        """
        symbol = symbol.upper()
        from app.services.price_store import get_price_store
        from app.services.market_service import SYMBOL_DIRECTORY

        # ETFs map directly to their sector model
        if symbol in ETF_TO_SECTOR:
            sector = ETF_TO_SECTOR[symbol]
            out = self.predict_sector(sector)
            out['symbol'] = symbol
            out['relationship'] = 'direct (sector ETF)'
            return out

        # Map stock -> sector via directory
        raw_sector = SYMBOL_DIRECTORY.get(symbol, {}).get('sector', '')
        sector_map = {
            'Technology': 'Technology',
            'Financial Services': 'Financials',
            'Healthcare': 'Healthcare',
            'Energy': 'Energy',
            'Industrials': 'Industrials',
            'Consumer Cyclical': 'Consumer_Discretionary',
            'Consumer Defensive': 'Consumer_Staples',
            'Communication Services': 'Communication_Services',
            'Utilities': 'Utilities',
            'Real Estate': 'Real_Estate',
            'Materials': 'Materials',
            'Basic Materials': 'Materials',
        }
        sector = sector_map.get(raw_sector)
        if sector is None:
            # Try live metadata
            from app.services.market_service import _get_symbol_meta
            meta = _get_symbol_meta(symbol)
            sector = sector_map.get(meta.get('sector', ''), 'Technology')

        sector_forecast = self.predict_sector(sector)
        if 'error' in sector_forecast:
            return sector_forecast

        etf = SECTOR_TO_ETF[sector]
        prices = get_price_store().get_history([symbol, etf], start='2022-01-01')
        if prices.empty or symbol not in prices.columns:
            return {'error': f'No price history for {symbol}'}

        rets = prices[[symbol, etf]].pct_change().dropna()
        if len(rets) < 63:
            return {'error': f'Insufficient history for {symbol}'}

        cov = np.cov(rets[symbol], rets[etf])
        beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] > 0 else 1.0
        beta = float(np.clip(beta, -3, 3))
        resid_vol = float(np.std(rets[symbol] - beta * rets[etf]))
        stock_vol_1d = float(rets[symbol].tail(63).std())

        from scipy.stats import norm
        horizons_out = {}
        for h_str, sf in sector_forecast['horizons'].items():
            h = int(h_str)
            expected = beta * sf['expected_return']
            h_vol = float(np.sqrt(h) * max(stock_vol_1d, 1e-6))
            p_up = float(norm.cdf(expected / h_vol)) if h_vol > 0 else 0.5
            # Blend with the sector's classifier signal
            if sf.get('prob_up') is not None:
                p_up = 0.5 * p_up + 0.5 * sf['prob_up']
            horizons_out[h_str] = {
                'expected_return_pct': round(expected * 100, 3),
                'ci_lower_pct': round((expected - Z_90 * h_vol) * 100, 3),
                'ci_upper_pct': round((expected + Z_90 * h_vol) * 100, 3),
                'volatility_pct': round(h_vol * 100, 3),
                'prob_up': round(p_up, 4),
                'sector_forecast_pct': sf['expected_return_pct'],
                'validation': sf.get('validation', {}),
            }

        return {
            'symbol': symbol,
            'sector': sector,
            'sector_etf': etf,
            'beta_to_sector': round(beta, 3),
            'idiosyncratic_vol_pct': round(resid_vol * 100, 3),
            'as_of': sector_forecast['as_of'],
            'horizons': horizons_out,
            'model_version': sector_forecast['model_version'],
            'method': f'sector ensemble x beta ({round(beta,2)}) + idiosyncratic vol',
        }


_engine: Optional[PredictionEngine] = None
_engine_lock = threading.Lock()


def get_prediction_engine() -> PredictionEngine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = PredictionEngine()
    return _engine
