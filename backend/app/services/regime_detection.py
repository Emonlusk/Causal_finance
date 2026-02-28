"""
Market Regime Detection Service
================================
Detects market regimes (bull/bear/sideways/high-volatility) using
Hidden Markov Models and other statistical techniques.

Implements:
- Gaussian HMM for regime detection
- Regime-switching volatility models
- Economic cycle indicators
- Regime-aware portfolio recommendations

Used for dynamic risk adjustment and scenario selection.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats
import warnings
import joblib

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

# Model storage path
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


class MarketRegimeDetector:
    """
    Detects market regimes using Hidden Markov Models.
    
    Regimes:
    - Bull: High returns, low-moderate volatility
    - Bear: Negative returns, high volatility
    - Sideways: Low returns, low volatility
    - Crisis: Extreme negative returns, very high volatility
    """
    
    # Regime definitions
    REGIMES = {
        0: 'bull',
        1: 'sideways',
        2: 'bear',
        3: 'crisis'
    }
    
    def __init__(self, n_regimes: int = 4, random_state: int = 42):
        """
        Initialize regime detector.
        
        Args:
            n_regimes: Number of regimes to detect
            random_state: Random seed
        """
        self.n_regimes = n_regimes
        self.random_state = random_state
        self.model = None
        self.regime_labels = None
        self._hmmlearn_available = self._check_hmmlearn()
    
    def _check_hmmlearn(self) -> bool:
        """Check if hmmlearn is available."""
        try:
            from hmmlearn.hmm import GaussianHMM
            return True
        except ImportError:
            logger.warning("hmmlearn not available for HMM regime detection")
            return False
    
    def fit(
        self,
        returns: pd.Series,
        volatility: pd.Series = None,
        n_iter: int = 100
    ) -> Dict[str, Any]:
        """
        Fit HMM to market data.
        
        Args:
            returns: Daily returns series
            volatility: Optional volatility series
            n_iter: Maximum EM iterations
            
        Returns:
            Dictionary with fit statistics
        """
        if not self._hmmlearn_available:
            return self._fallback_fit(returns, volatility)
        
        from hmmlearn.hmm import GaussianHMM
        
        try:
            # Prepare features
            returns = returns.dropna()
            
            # Create feature matrix
            features = pd.DataFrame(index=returns.index)
            features['returns'] = returns
            
            # Add rolling volatility if not provided
            if volatility is not None:
                features['volatility'] = volatility.reindex(returns.index)
            else:
                features['volatility'] = returns.rolling(21).std() * np.sqrt(252)
            
            # Add momentum
            features['momentum'] = returns.rolling(63).mean() * 252
            
            # Drop NaN
            features = features.dropna()
            
            if len(features) < 252:  # Need at least 1 year
                return {'error': 'Insufficient data (need 252+ observations)'}
            
            X = features.values
            
            # Fit HMM
            model = GaussianHMM(
                n_components=self.n_regimes,
                covariance_type='full',
                n_iter=n_iter,
                random_state=self.random_state
            )
            
            model.fit(X)
            self.model = model
            
            # Get regime sequence
            hidden_states = model.predict(X)
            
            # Label regimes based on characteristics
            self._label_regimes(features, hidden_states)
            
            # Compute transition matrix
            transition_matrix = model.transmat_
            
            # Regime statistics
            regime_stats = self._compute_regime_stats(features, hidden_states)
            
            return {
                'n_regimes': self.n_regimes,
                'n_observations': len(features),
                'log_likelihood': float(model.score(X)),
                'aic': float(-2 * model.score(X) * len(X) + 2 * self._count_params()),
                'regime_stats': regime_stats,
                'transition_matrix': transition_matrix.tolist(),
                'regime_labels': self.regime_labels,
            }
            
        except Exception as e:
            logger.error(f"HMM fit failed: {e}")
            return {'error': str(e)}
    
    def _label_regimes(self, features: pd.DataFrame, states: np.ndarray):
        """Label regimes based on their characteristics."""
        regime_chars = {}
        
        for state in range(self.n_regimes):
            mask = states == state
            if mask.sum() > 0:
                regime_chars[state] = {
                    'mean_return': features.loc[mask, 'returns'].mean(),
                    'mean_volatility': features.loc[mask, 'volatility'].mean(),
                }
        
        # Sort by mean return to assign labels
        sorted_states = sorted(
            regime_chars.keys(),
            key=lambda s: regime_chars[s]['mean_return'],
            reverse=True
        )
        
        self.regime_labels = {}
        labels = ['bull', 'sideways', 'bear', 'crisis']
        
        for i, state in enumerate(sorted_states):
            if i < len(labels):
                self.regime_labels[state] = labels[i]
            else:
                self.regime_labels[state] = f'regime_{state}'
    
    def _compute_regime_stats(
        self,
        features: pd.DataFrame,
        states: np.ndarray
    ) -> Dict[str, Dict[str, float]]:
        """Compute statistics for each regime."""
        stats = {}
        
        for state in range(self.n_regimes):
            mask = states == state
            regime_data = features.loc[mask]
            
            if len(regime_data) > 0:
                label = self.regime_labels.get(state, f'regime_{state}')
                stats[label] = {
                    'mean_return': float(regime_data['returns'].mean() * 252),  # Annualized
                    'volatility': float(regime_data['volatility'].mean()),
                    'frequency': float(mask.mean()),
                    'avg_duration': float(self._compute_avg_duration(mask)),
                    'sharpe_ratio': float(
                        regime_data['returns'].mean() / regime_data['returns'].std() * np.sqrt(252)
                        if regime_data['returns'].std() > 0 else 0
                    ),
                }
        
        return stats
    
    def _compute_avg_duration(self, mask: np.ndarray) -> float:
        """Compute average duration of regime periods."""
        # Find consecutive True values
        changes = np.diff(np.concatenate([[False], mask, [False]]).astype(int))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]
        
        if len(starts) > 0:
            durations = ends - starts
            return float(np.mean(durations))
        return 0.0
    
    def _count_params(self) -> int:
        """Count number of HMM parameters."""
        # Means + Covariances + Transition probabilities
        n_features = 3  # returns, volatility, momentum
        n_means = self.n_regimes * n_features
        n_covars = self.n_regimes * n_features * (n_features + 1) // 2
        n_trans = self.n_regimes * (self.n_regimes - 1)
        return n_means + n_covars + n_trans
    
    def predict_regime(
        self,
        returns: pd.Series,
        volatility: pd.Series = None
    ) -> Dict[str, Any]:
        """
        Predict current market regime.
        
        Args:
            returns: Recent returns series
            volatility: Optional volatility series
            
        Returns:
            Dictionary with regime prediction and probabilities
        """
        if self.model is None:
            return self._fallback_predict(returns, volatility)
        
        try:
            # Prepare features
            features = pd.DataFrame(index=returns.index)
            features['returns'] = returns
            
            if volatility is not None:
                features['volatility'] = volatility.reindex(returns.index)
            else:
                features['volatility'] = returns.rolling(21).std() * np.sqrt(252)
            
            features['momentum'] = returns.rolling(63).mean() * 252
            features = features.dropna()
            
            X = features.values
            
            if len(X) == 0:
                return {'error': 'Insufficient data for prediction'}
            
            # Get state probabilities
            probs = self.model.predict_proba(X)
            current_probs = probs[-1]  # Most recent
            
            # Get predicted state
            predicted_state = np.argmax(current_probs)
            regime_label = self.regime_labels.get(predicted_state, f'regime_{predicted_state}')
            
            # Build probability dictionary
            regime_probs = {}
            for state, label in self.regime_labels.items():
                regime_probs[label] = float(current_probs[state])
            
            return {
                'current_regime': regime_label,
                'regime_probability': float(current_probs[predicted_state]),
                'all_probabilities': regime_probs,
                'observation_date': str(features.index[-1]),
            }
            
        except Exception as e:
            logger.error(f"Regime prediction failed: {e}")
            return {'error': str(e)}
    
    def _fallback_fit(
        self,
        returns: pd.Series,
        volatility: pd.Series
    ) -> Dict[str, Any]:
        """Fallback regime detection using rule-based approach."""
        returns = returns.dropna()
        
        if volatility is None:
            volatility = returns.rolling(21).std() * np.sqrt(252)
        
        # Rule-based regime classification
        self.model = {
            'type': 'rule_based',
            'return_thresholds': {
                'bull': returns.quantile(0.75) * 252,
                'bear': returns.quantile(0.25) * 252,
            },
            'vol_threshold': volatility.quantile(0.75),
        }
        
        self.regime_labels = {0: 'bull', 1: 'sideways', 2: 'bear', 3: 'crisis'}
        
        return {
            'method': 'rule_based',
            'n_observations': len(returns),
        }
    
    def _fallback_predict(
        self,
        returns: pd.Series,
        volatility: pd.Series
    ) -> Dict[str, Any]:
        """Fallback regime prediction using rules."""
        returns = returns.dropna()
        
        if len(returns) < 21:
            return {'error': 'Insufficient data'}
        
        # Calculate recent metrics
        recent_return = returns.iloc[-21:].mean() * 252
        
        if volatility is not None:
            recent_vol = volatility.iloc[-1]
        else:
            recent_vol = returns.iloc[-21:].std() * np.sqrt(252)
        
        # Classify using rules
        if isinstance(self.model, dict) and 'return_thresholds' in self.model:
            bull_thresh = self.model['return_thresholds']['bull']
            bear_thresh = self.model['return_thresholds']['bear']
            vol_thresh = self.model['vol_threshold']
        else:
            bull_thresh = 0.15
            bear_thresh = -0.10
            vol_thresh = 0.25
        
        if recent_vol > vol_thresh * 1.5 and recent_return < bear_thresh:
            regime = 'crisis'
            prob = 0.8
        elif recent_return > bull_thresh:
            regime = 'bull'
            prob = 0.7
        elif recent_return < bear_thresh:
            regime = 'bear'
            prob = 0.7
        else:
            regime = 'sideways'
            prob = 0.6
        
        return {
            'current_regime': regime,
            'regime_probability': prob,
            'all_probabilities': {regime: prob},
            'method': 'rule_based',
        }
    
    def get_regime_recommendations(
        self,
        regime: str
    ) -> Dict[str, Any]:
        """
        Get portfolio recommendations for a regime.
        
        Args:
            regime: Current regime label
            
        Returns:
            Dictionary with recommendations
        """
        recommendations = {
            'bull': {
                'risk_level': 'high',
                'equity_allocation': 0.80,
                'bond_allocation': 0.15,
                'cash_allocation': 0.05,
                'sector_tilts': {
                    'Technology': 'overweight',
                    'Consumer_Discretionary': 'overweight',
                    'Financials': 'overweight',
                    'Utilities': 'underweight',
                    'Consumer_Staples': 'underweight',
                },
                'strategy': 'Growth-oriented with high equity exposure',
            },
            'sideways': {
                'risk_level': 'moderate',
                'equity_allocation': 0.60,
                'bond_allocation': 0.30,
                'cash_allocation': 0.10,
                'sector_tilts': {
                    'Healthcare': 'overweight',
                    'Consumer_Staples': 'overweight',
                    'Technology': 'neutral',
                    'Financials': 'neutral',
                },
                'strategy': 'Balanced approach focusing on quality and dividends',
            },
            'bear': {
                'risk_level': 'low',
                'equity_allocation': 0.40,
                'bond_allocation': 0.40,
                'cash_allocation': 0.20,
                'sector_tilts': {
                    'Consumer_Staples': 'overweight',
                    'Utilities': 'overweight',
                    'Healthcare': 'overweight',
                    'Technology': 'underweight',
                    'Consumer_Discretionary': 'underweight',
                },
                'strategy': 'Defensive positioning with focus on capital preservation',
            },
            'crisis': {
                'risk_level': 'minimal',
                'equity_allocation': 0.25,
                'bond_allocation': 0.35,
                'cash_allocation': 0.40,
                'sector_tilts': {
                    'Consumer_Staples': 'overweight',
                    'Utilities': 'overweight',
                    'Healthcare': 'overweight',
                    'Energy': 'underweight',
                    'Financials': 'underweight',
                    'Technology': 'underweight',
                },
                'strategy': 'Capital preservation with maximum defensive allocation',
            },
        }
        
        return recommendations.get(regime, recommendations['sideways'])
    
    def save(self, filepath: str):
        """Save model to file."""
        if self.model is not None:
            joblib.dump({
                'model': self.model,
                'regime_labels': self.regime_labels,
                'n_regimes': self.n_regimes,
            }, filepath)
    
    def load(self, filepath: str):
        """Load model from file."""
        data = joblib.load(filepath)
        self.model = data['model']
        self.regime_labels = data['regime_labels']
        self.n_regimes = data['n_regimes']


class EconomicCycleIndicator:
    """
    Tracks economic cycle indicators for regime context.
    
    Combines multiple macro indicators to assess economic conditions:
    - Leading indicators (yield curve, consumer sentiment)
    - Coincident indicators (employment, industrial production)
    - Lagging indicators (inflation, interest rates)
    """
    
    # Indicator weights
    LEADING_WEIGHT = 0.5
    COINCIDENT_WEIGHT = 0.3
    LAGGING_WEIGHT = 0.2
    
    def __init__(self):
        """Initialize economic cycle indicator."""
        self.indicators = {}
    
    def compute_cycle_score(
        self,
        macro_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compute economic cycle score from macro data.
        
        Args:
            macro_data: DataFrame with macro indicators
            
        Returns:
            Dictionary with cycle assessment
        """
        scores = {}
        
        # Leading indicators
        leading_score = 0
        leading_count = 0
        
        # Yield curve spread (positive = expansion)
        if 'Yield_Curve_Spread' in macro_data.columns:
            spread = macro_data['Yield_Curve_Spread'].iloc[-1]
            if spread > 0:
                leading_score += 1
            elif spread < -0.5:
                leading_score -= 1
            leading_count += 1
        
        # Consumer sentiment (above 80 = positive)
        if 'Consumer_Sentiment' in macro_data.columns:
            sentiment = macro_data['Consumer_Sentiment'].iloc[-1]
            if sentiment > 90:
                leading_score += 1
            elif sentiment < 70:
                leading_score -= 1
            leading_count += 1
        
        if leading_count > 0:
            scores['leading'] = leading_score / leading_count
        
        # Coincident indicators
        coincident_score = 0
        coincident_count = 0
        
        # Unemployment (low = positive)
        if 'Unemployment_Rate' in macro_data.columns:
            unemp = macro_data['Unemployment_Rate'].iloc[-1]
            if unemp < 4.5:
                coincident_score += 1
            elif unemp > 6:
                coincident_score -= 1
            coincident_count += 1
        
        # Industrial production growth
        if 'Industrial_Production_Change' in macro_data.columns:
            ip_change = macro_data['Industrial_Production_Change'].iloc[-1]
            if ip_change > 0.02:
                coincident_score += 1
            elif ip_change < -0.02:
                coincident_score -= 1
            coincident_count += 1
        
        if coincident_count > 0:
            scores['coincident'] = coincident_score / coincident_count
        
        # Lagging indicators
        lagging_score = 0
        lagging_count = 0
        
        # Inflation (moderate = positive)
        if 'CPI_Change' in macro_data.columns:
            inflation = macro_data['CPI_Change'].iloc[-1]
            if 0.01 < inflation < 0.03:
                lagging_score += 1
            elif inflation > 0.05 or inflation < 0:
                lagging_score -= 1
            lagging_count += 1
        
        if lagging_count > 0:
            scores['lagging'] = lagging_score / lagging_count
        
        # Composite score
        composite = (
            scores.get('leading', 0) * self.LEADING_WEIGHT +
            scores.get('coincident', 0) * self.COINCIDENT_WEIGHT +
            scores.get('lagging', 0) * self.LAGGING_WEIGHT
        )
        
        # Classify cycle phase
        if composite > 0.3:
            phase = 'expansion'
        elif composite > 0:
            phase = 'late_expansion'
        elif composite > -0.3:
            phase = 'early_contraction'
        else:
            phase = 'contraction'
        
        return {
            'composite_score': float(composite),
            'component_scores': scores,
            'cycle_phase': phase,
            'observation_date': str(macro_data.index[-1]) if hasattr(macro_data.index, '__iter__') else None,
        }


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def detect_current_regime(
    feature_matrix: pd.DataFrame,
    model_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect current market regime from feature matrix.
    Uses trained HMM model from registry if available.
    
    Args:
        feature_matrix: DataFrame with market data
        model_path: Path to saved regime model
        
    Returns:
        Dictionary with regime detection results
    """
    detector = MarketRegimeDetector()
    
    # Auto-discover trained model from registry if no explicit path given
    if not model_path:
        try:
            from .ml_training_pipeline import ModelRegistry, MODELS_DIR as _MODELS_DIR
            registry = ModelRegistry()
            regime_info = registry.get_active_model('regime')
            if regime_info and 'filepath' in regime_info:
                _path = regime_info['filepath']
                if not os.path.exists(_path):
                    _path = os.path.join(_MODELS_DIR, os.path.basename(_path))
                if os.path.exists(_path):
                    model_path = _path
        except Exception:
            pass  # Fall through to manual fit
    
    # Load existing model if available
    if model_path and os.path.exists(model_path):
        detector.load(model_path)
    else:
        # Fit new model
        if 'SP500_Return' in feature_matrix.columns:
            returns = feature_matrix['SP500_Return']
        else:
            # Find any return column
            return_cols = [c for c in feature_matrix.columns if 'Return_1d' in c]
            if return_cols:
                returns = feature_matrix[return_cols[0]]
            else:
                return {'error': 'No return column found'}
        
        volatility = None
        if 'SP500_Volatility_21d' in feature_matrix.columns:
            volatility = feature_matrix['SP500_Volatility_21d']
        
        fit_result = detector.fit(returns, volatility)
        
        if 'error' in fit_result:
            return fit_result
    
    # Predict current regime
    if 'SP500_Return' in feature_matrix.columns:
        returns = feature_matrix['SP500_Return']
    else:
        return_cols = [c for c in feature_matrix.columns if 'Return_1d' in c]
        returns = feature_matrix[return_cols[0]]
    
    regime = detector.predict_regime(returns.tail(252))  # Last year
    
    # Add recommendations
    if 'current_regime' in regime:
        regime['recommendations'] = detector.get_regime_recommendations(regime['current_regime'])
    
    return regime


# Singleton instance
_detector = None

def get_regime_detector() -> MarketRegimeDetector:
    """Get or create singleton regime detector."""
    global _detector
    if _detector is None:
        _detector = MarketRegimeDetector()
    return _detector
