"""
Model training CLI
==================
Retrains the prediction stack from fresh market data.

Usage (from backend/):
    python -m scripts.train_models                 # forecast models, all sectors
    python -m scripts.train_models --skip-lstm     # faster, tree/ARIMA/GARCH only
    python -m scripts.train_models --sectors Technology Energy
    python -m scripts.train_models --regime        # also retrain HMM regime model
    python -m scripts.train_models --full          # everything incl. causal models
"""

import argparse
import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('train_models')


def main():
    parser = argparse.ArgumentParser(description='Train Causal Finance models')
    parser.add_argument('--skip-lstm', action='store_true', help='Skip LSTM training (much faster)')
    parser.add_argument('--sectors', nargs='*', default=None, help='Specific sectors to train')
    parser.add_argument('--regime', action='store_true', help='Also retrain regime detection')
    parser.add_argument('--full', action='store_true',
                        help='Full pipeline: refresh feature matrix + causal + treatment + regime + forecast')
    args = parser.parse_args()

    if args.full:
        logger.info("Running FULL training pipeline (data + causal + treatment + regime)...")
        from app.services.ml_training_pipeline import MLTrainingPipeline
        pipeline = MLTrainingPipeline(fred_api_key=os.getenv('FRED_API_KEY'))
        result = pipeline.run_full_pipeline(fetch_fresh_data=True)
        print(json.dumps({k: v for k, v in result.items() if k != 'results'}, indent=2, default=str))

    logger.info("Training sector forecast ensembles (walk-forward validated)...")
    from app.services.prediction_engine import train_all_sectors
    results = train_all_sectors(train_lstm=not args.skip_lstm, sectors=args.sectors)

    print("\n=== Forecast training summary ===")
    for sector, val in results.get('sectors', {}).items():
        if 'error' in val:
            print(f"{sector}: ERROR {val['error']}")
            continue
        h1 = val.get('horizons', {}).get('1', {})
        h21 = val.get('horizons', {}).get('21', {})
        print(f"{sector}: 1d GBM dir={h1.get('gbm_dir')} rmse={h1.get('gbm_rmse')} "
              f"(naive {h1.get('naive_rmse')}) | 21d dir={h21.get('gbm_dir')} "
              f"rmse={h21.get('gbm_rmse')} (naive {h21.get('naive_rmse')})")

    if args.regime and not args.full:
        logger.info("Retraining regime detection model...")
        from app.services.price_store import get_price_store
        from app.services.regime_detection import MarketRegimeDetector
        from app.services.ml_training_pipeline import ModelRegistry, MODELS_DIR
        from datetime import datetime
        import numpy as np

        prices = get_price_store().get_history(['SPY', '^VIX'], start='2010-01-01')
        returns = prices['SPY'].pct_change().dropna()
        vol = returns.rolling(21).std() * np.sqrt(252)

        detector = MarketRegimeDetector(n_regimes=3)
        fit_result = detector.fit(returns, vol.reindex(returns.index))
        version = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(MODELS_DIR, f'regime_detector_{version}.pkl')
        detector.save(path)
        registry = ModelRegistry()
        registry.register_model(
            model_type='regime', model_name='hmm_detector', version=version,
            metrics=fit_result.get('regime_stats', {}),
            hyperparameters={'n_regimes': 3}, filepath=path,
        )
        registry.set_active_model('regime', f'regime_hmm_detector_{version}')
        print(f"Regime model retrained: {path}")


if __name__ == '__main__':
    main()
