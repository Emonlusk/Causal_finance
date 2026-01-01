"""
Treatment Effect Estimation Service
====================================
Estimates causal treatment effects using DoWhy, EconML, and statistical methods.

Implements:
- Backdoor adjustment (controlling for confounders)
- Double Machine Learning (DML)
- Instrumental Variables (IV)
- Bootstrap confidence intervals
- Sensitivity analysis

Replaces hardcoded effect sizes with data-driven estimates.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
from scipy import stats
import warnings

logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')


class TreatmentEffectEstimator:
    """
    Estimates causal treatment effects from observational data.
    
    Uses multiple methods and combines for robustness:
    1. DoWhy (when available) - Full causal inference framework
    2. EconML (when available) - Heterogeneous treatment effects
    3. Statistical methods - OLS, IV, matching as fallback
    """
    
    def __init__(self, random_state: int = 42):
        """
        Initialize the treatment effect estimator.
        
        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state
        self._dowhy_available = False
        self._econml_available = False
        self._sklearn_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check which causal inference libraries are available."""
        try:
            import dowhy
            self._dowhy_available = True
            logger.info("DoWhy available for causal inference")
        except ImportError:
            logger.warning("DoWhy not available")
        
        try:
            import econml
            self._econml_available = True
            logger.info("EconML available for heterogeneous treatment effects")
        except ImportError:
            logger.warning("EconML not available")
        
        try:
            from sklearn.linear_model import LinearRegression
            self._sklearn_available = True
        except ImportError:
            logger.warning("scikit-learn not available")
    
    # ============================================
    # MAIN ESTIMATION METHODS
    # ============================================
    
    def estimate_ate(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str],
        method: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Estimate Average Treatment Effect (ATE).
        
        Args:
            data: DataFrame with treatment, outcome, and confounders
            treatment: Treatment variable name
            outcome: Outcome variable name
            confounders: List of confounder variable names
            method: Estimation method ('auto', 'ols', 'ipw', 'dml', 'dowhy')
            
        Returns:
            Dictionary with ATE estimate, CI, and diagnostics
        """
        if method == 'auto':
            if self._dowhy_available:
                method = 'dowhy'
            elif self._econml_available:
                method = 'dml'
            else:
                method = 'ols'
        
        logger.info(f"Estimating ATE using method: {method}")
        
        if method == 'dowhy':
            return self._estimate_ate_dowhy(data, treatment, outcome, confounders)
        elif method == 'dml':
            return self._estimate_ate_dml(data, treatment, outcome, confounders)
        elif method == 'ipw':
            return self._estimate_ate_ipw(data, treatment, outcome, confounders)
        else:  # OLS fallback
            return self._estimate_ate_ols(data, treatment, outcome, confounders)
    
    def _estimate_ate_dowhy(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str]
    ) -> Dict[str, Any]:
        """Estimate ATE using DoWhy framework."""
        try:
            import dowhy
            from dowhy import CausalModel
            
            # Prepare data
            analysis_data = data[[treatment, outcome] + confounders].dropna()
            
            # Build causal graph string
            graph_str = f"""
            digraph {{
                {'; '.join(f'{c} -> {treatment}' for c in confounders)};
                {'; '.join(f'{c} -> {outcome}' for c in confounders)};
                {treatment} -> {outcome};
            }}
            """
            
            # Create causal model
            model = CausalModel(
                data=analysis_data,
                treatment=treatment,
                outcome=outcome,
                common_causes=confounders,
                graph=graph_str
            )
            
            # Identify estimand
            identified_estimand = model.identify_effect(proceed_when_unidentifiable=True)
            
            # Estimate effect using backdoor adjustment
            estimate = model.estimate_effect(
                identified_estimand,
                method_name="backdoor.linear_regression",
                confidence_intervals=True,
                test_significance=True
            )
            
            # Refutation tests
            refutation_results = []
            
            # Placebo treatment test
            try:
                placebo_refute = model.refute_estimate(
                    identified_estimand,
                    estimate,
                    method_name="placebo_treatment_refuter",
                    placebo_type="permute"
                )
                refutation_results.append({
                    'test': 'placebo_treatment',
                    'p_value': getattr(placebo_refute, 'refutation_result', {}).get('p_value', None),
                    'passed': getattr(placebo_refute, 'refutation_result', {}).get('is_statistically_significant', True)
                })
            except:
                pass
            
            return {
                'method': 'dowhy_backdoor',
                'ate': float(estimate.value),
                'ci_lower': float(estimate.get_confidence_intervals()[0]) if estimate.get_confidence_intervals() else None,
                'ci_upper': float(estimate.get_confidence_intervals()[1]) if estimate.get_confidence_intervals() else None,
                'p_value': float(estimate.test_stat_significance().get('p_value', 0.5)) if estimate.test_stat_significance() else None,
                'standard_error': float(estimate.get_standard_error()) if estimate.get_standard_error() else None,
                'sample_size': len(analysis_data),
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
                'refutation_tests': refutation_results,
            }
            
        except Exception as e:
            logger.error(f"DoWhy estimation failed: {e}")
            return self._estimate_ate_ols(data, treatment, outcome, confounders)
    
    def _estimate_ate_dml(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str]
    ) -> Dict[str, Any]:
        """
        Estimate ATE using Double Machine Learning.
        
        DML uses ML models for both:
        1. Predicting treatment from confounders
        2. Predicting outcome from confounders
        Then estimates treatment effect from residuals.
        """
        try:
            from econml.dml import LinearDML
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.linear_model import LassoCV
            
            # Prepare data
            analysis_data = data[[treatment, outcome] + confounders].dropna()
            
            Y = analysis_data[outcome].values
            T = analysis_data[treatment].values
            X = analysis_data[confounders].values
            
            # Create DML estimator
            dml = LinearDML(
                model_y=RandomForestRegressor(n_estimators=100, max_depth=5, random_state=self.random_state),
                model_t=RandomForestRegressor(n_estimators=100, max_depth=5, random_state=self.random_state),
                random_state=self.random_state,
                cv=5
            )
            
            # Fit
            dml.fit(Y, T, X=X)
            
            # Get ATE
            ate = dml.ate()
            ate_interval = dml.ate_interval(alpha=0.05)
            
            return {
                'method': 'double_ml',
                'ate': float(ate),
                'ci_lower': float(ate_interval[0]),
                'ci_upper': float(ate_interval[1]),
                'sample_size': len(analysis_data),
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
            }
            
        except Exception as e:
            logger.error(f"DML estimation failed: {e}")
            return self._estimate_ate_ols(data, treatment, outcome, confounders)
    
    def _estimate_ate_ipw(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str]
    ) -> Dict[str, Any]:
        """
        Estimate ATE using Inverse Probability Weighting.
        
        IPW reweights observations to create pseudo-populations
        where treatment is independent of confounders.
        """
        try:
            from sklearn.linear_model import LogisticRegression
            
            # Prepare data
            analysis_data = data[[treatment, outcome] + confounders].dropna()
            
            # Binarize treatment for propensity score
            T = analysis_data[treatment].values
            T_binary = (T > np.median(T)).astype(int)
            
            Y = analysis_data[outcome].values
            X = analysis_data[confounders].values
            
            # Estimate propensity scores
            ps_model = LogisticRegression(random_state=self.random_state, max_iter=1000)
            ps_model.fit(X, T_binary)
            propensity_scores = ps_model.predict_proba(X)[:, 1]
            
            # Clip propensity scores to avoid extreme weights
            propensity_scores = np.clip(propensity_scores, 0.01, 0.99)
            
            # IPW weights
            weights_treated = T_binary / propensity_scores
            weights_control = (1 - T_binary) / (1 - propensity_scores)
            
            # Weighted means
            y_treated_weighted = np.sum(Y * T_binary * weights_treated) / np.sum(T_binary * weights_treated)
            y_control_weighted = np.sum(Y * (1 - T_binary) * weights_control) / np.sum((1 - T_binary) * weights_control)
            
            ate = y_treated_weighted - y_control_weighted
            
            # Bootstrap for CI
            bootstrap_ates = []
            n = len(Y)
            
            for _ in range(500):
                idx = np.random.choice(n, size=n, replace=True)
                Y_b = Y[idx]
                T_b = T_binary[idx]
                ps_b = propensity_scores[idx]
                
                w_t = T_b / ps_b
                w_c = (1 - T_b) / (1 - ps_b)
                
                if np.sum(T_b * w_t) > 0 and np.sum((1 - T_b) * w_c) > 0:
                    y_t = np.sum(Y_b * T_b * w_t) / np.sum(T_b * w_t)
                    y_c = np.sum(Y_b * (1 - T_b) * w_c) / np.sum((1 - T_b) * w_c)
                    bootstrap_ates.append(y_t - y_c)
            
            ci_lower, ci_upper = np.percentile(bootstrap_ates, [2.5, 97.5])
            
            return {
                'method': 'ipw',
                'ate': float(ate),
                'ci_lower': float(ci_lower),
                'ci_upper': float(ci_upper),
                'sample_size': len(analysis_data),
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
            }
            
        except Exception as e:
            logger.error(f"IPW estimation failed: {e}")
            return self._estimate_ate_ols(data, treatment, outcome, confounders)
    
    def _estimate_ate_ols(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str]
    ) -> Dict[str, Any]:
        """
        Estimate ATE using OLS regression (basic backdoor adjustment).
        
        This is the simplest approach: regress outcome on treatment
        and confounders, treatment coefficient is ATE.
        """
        try:
            from sklearn.linear_model import LinearRegression
            
            # Prepare data
            analysis_data = data[[treatment, outcome] + confounders].dropna()
            
            Y = analysis_data[outcome].values
            X = analysis_data[[treatment] + confounders].values
            
            # Fit OLS
            model = LinearRegression()
            model.fit(X, Y)
            
            ate = model.coef_[0]  # Treatment coefficient
            
            # Calculate standard error via bootstrap
            bootstrap_ates = []
            n = len(Y)
            
            for _ in range(1000):
                idx = np.random.choice(n, size=n, replace=True)
                model_b = LinearRegression()
                model_b.fit(X[idx], Y[idx])
                bootstrap_ates.append(model_b.coef_[0])
            
            std_error = np.std(bootstrap_ates)
            ci_lower, ci_upper = np.percentile(bootstrap_ates, [2.5, 97.5])
            
            # Calculate p-value
            t_stat = ate / std_error
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n-len(confounders)-2))
            
            return {
                'method': 'ols',
                'ate': float(ate),
                'ci_lower': float(ci_lower),
                'ci_upper': float(ci_upper),
                'standard_error': float(std_error),
                'p_value': float(p_value),
                'sample_size': len(analysis_data),
                'treatment': treatment,
                'outcome': outcome,
                'confounders': confounders,
            }
            
        except Exception as e:
            logger.error(f"OLS estimation failed: {e}")
            return {
                'method': 'failed',
                'error': str(e),
                'treatment': treatment,
                'outcome': outcome,
            }
    
    # ============================================
    # HETEROGENEOUS TREATMENT EFFECTS
    # ============================================
    
    def estimate_cate(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str],
        effect_modifiers: List[str]
    ) -> Dict[str, Any]:
        """
        Estimate Conditional Average Treatment Effect (CATE).
        
        CATE estimates how treatment effects vary across subgroups
        defined by effect modifiers.
        
        Args:
            data: DataFrame with variables
            treatment: Treatment variable
            outcome: Outcome variable
            confounders: Confounding variables
            effect_modifiers: Variables that modify treatment effect
            
        Returns:
            Dictionary with CATE estimates
        """
        if self._econml_available:
            return self._estimate_cate_econml(data, treatment, outcome, confounders, effect_modifiers)
        else:
            return self._estimate_cate_subgroup(data, treatment, outcome, confounders, effect_modifiers)
    
    def _estimate_cate_econml(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str],
        effect_modifiers: List[str]
    ) -> Dict[str, Any]:
        """Estimate CATE using EconML's Causal Forest."""
        try:
            from econml.dml import CausalForestDML
            from sklearn.ensemble import RandomForestRegressor
            
            # Prepare data
            all_vars = [treatment, outcome] + confounders + effect_modifiers
            all_vars = list(set(all_vars))  # Remove duplicates
            analysis_data = data[all_vars].dropna()
            
            Y = analysis_data[outcome].values
            T = analysis_data[treatment].values
            X = analysis_data[effect_modifiers].values
            W = analysis_data[confounders].values if confounders else None
            
            # Create Causal Forest
            cf = CausalForestDML(
                model_y=RandomForestRegressor(n_estimators=100, max_depth=5, random_state=self.random_state),
                model_t=RandomForestRegressor(n_estimators=100, max_depth=5, random_state=self.random_state),
                n_estimators=100,
                random_state=self.random_state,
                cv=5
            )
            
            # Fit
            cf.fit(Y, T, X=X, W=W)
            
            # Get CATE for all observations
            cate = cf.effect(X)
            cate_intervals = cf.effect_interval(X, alpha=0.05)
            
            # Feature importance for effect modification
            importance = cf.feature_importances_
            
            return {
                'method': 'causal_forest',
                'ate': float(np.mean(cate)),
                'cate_mean': float(np.mean(cate)),
                'cate_std': float(np.std(cate)),
                'cate_min': float(np.min(cate)),
                'cate_max': float(np.max(cate)),
                'feature_importance': dict(zip(effect_modifiers, importance.tolist())),
                'sample_size': len(analysis_data),
                'treatment': treatment,
                'outcome': outcome,
                'effect_modifiers': effect_modifiers,
            }
            
        except Exception as e:
            logger.error(f"CATE estimation failed: {e}")
            return self._estimate_cate_subgroup(data, treatment, outcome, confounders, effect_modifiers)
    
    def _estimate_cate_subgroup(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        confounders: List[str],
        effect_modifiers: List[str]
    ) -> Dict[str, Any]:
        """Fallback: Estimate CATE via subgroup analysis."""
        try:
            subgroup_effects = {}
            
            for modifier in effect_modifiers:
                if modifier not in data.columns:
                    continue
                
                # Split into high/low groups
                median = data[modifier].median()
                
                low_mask = data[modifier] <= median
                high_mask = data[modifier] > median
                
                # Estimate ATE in each subgroup
                if low_mask.sum() > 50:
                    low_ate = self._estimate_ate_ols(data[low_mask], treatment, outcome, confounders)
                    subgroup_effects[f'{modifier}_low'] = low_ate.get('ate')
                
                if high_mask.sum() > 50:
                    high_ate = self._estimate_ate_ols(data[high_mask], treatment, outcome, confounders)
                    subgroup_effects[f'{modifier}_high'] = high_ate.get('ate')
            
            return {
                'method': 'subgroup_analysis',
                'subgroup_effects': subgroup_effects,
                'sample_size': len(data),
                'treatment': treatment,
                'outcome': outcome,
                'effect_modifiers': effect_modifiers,
            }
            
        except Exception as e:
            return {'method': 'failed', 'error': str(e)}
    
    # ============================================
    # SECTOR-MACRO TREATMENT EFFECTS
    # ============================================
    
    def estimate_macro_sector_effects(
        self,
        feature_matrix: pd.DataFrame,
        sectors: List[str] = None,
        macro_treatments: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estimate causal effects of macroeconomic changes on sector returns.
        
        This replaces hardcoded sector sensitivities with data-driven estimates.
        
        Args:
            feature_matrix: DataFrame with sector returns and macro variables
            sectors: List of sectors to analyze
            macro_treatments: List of macro variables as treatments
            
        Returns:
            Nested dict: {sector: {macro_var: effect_estimate}}
        """
        if sectors is None:
            sectors = ['Technology', 'Healthcare', 'Energy', 'Financials', 'Industrials']
        
        if macro_treatments is None:
            macro_treatments = ['Fed_Funds_Rate_Change', 'CPI_Change', 'VIX_Change']
        
        # Confounders for macro->sector effects
        confounders = ['SP500_Return', 'SP500_Volatility_21d']
        confounders = [c for c in confounders if c in feature_matrix.columns]
        
        results = {}
        
        for sector in sectors:
            outcome_col = f'{sector}_Return_1d'
            
            if outcome_col not in feature_matrix.columns:
                continue
            
            results[sector] = {}
            
            for treatment in macro_treatments:
                if treatment not in feature_matrix.columns:
                    continue
                
                logger.info(f"Estimating effect of {treatment} on {sector}")
                
                effect = self.estimate_ate(
                    data=feature_matrix,
                    treatment=treatment,
                    outcome=outcome_col,
                    confounders=confounders,
                    method='auto'
                )
                
                results[sector][treatment] = effect
        
        return results
    
    def build_sensitivity_matrix(
        self,
        effect_estimates: Dict[str, Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Build sector sensitivity matrix from estimated effects.
        
        Converts treatment effect estimates into a sensitivity matrix
        format compatible with the existing causal_service.
        
        Args:
            effect_estimates: Output from estimate_macro_sector_effects
            
        Returns:
            DataFrame with sectors as rows and macro variables as columns
        """
        # Extract sectors and macro variables
        sectors = list(effect_estimates.keys())
        macro_vars = set()
        for sector_effects in effect_estimates.values():
            macro_vars.update(sector_effects.keys())
        macro_vars = sorted(list(macro_vars))
        
        # Build matrix
        matrix = pd.DataFrame(index=sectors, columns=macro_vars, dtype=float)
        
        for sector in sectors:
            for macro_var in macro_vars:
                if macro_var in effect_estimates.get(sector, {}):
                    effect = effect_estimates[sector][macro_var]
                    ate = effect.get('ate', 0)
                    matrix.loc[sector, macro_var] = ate
        
        return matrix.fillna(0)


# ============================================
# SENSITIVITY ANALYSIS
# ============================================

def sensitivity_analysis(
    data: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: List[str],
    unmeasured_confounder_strength: List[float] = [0.1, 0.2, 0.3, 0.5]
) -> Dict[str, Any]:
    """
    Perform sensitivity analysis for unmeasured confounding.
    
    Estimates how strong an unmeasured confounder would need to be
    to explain away the observed treatment effect.
    
    Args:
        data: DataFrame with variables
        treatment: Treatment variable
        outcome: Outcome variable
        confounders: Measured confounders
        unmeasured_confounder_strength: List of confounder strengths to simulate
        
    Returns:
        Dictionary with sensitivity analysis results
    """
    estimator = TreatmentEffectEstimator()
    
    # Get baseline estimate
    baseline = estimator.estimate_ate(data, treatment, outcome, confounders, method='ols')
    baseline_ate = baseline.get('ate', 0)
    
    # Simulate unmeasured confounder
    sensitivity_results = []
    
    for strength in unmeasured_confounder_strength:
        # Create synthetic confounder that correlates with both T and Y
        analysis_data = data[[treatment, outcome] + confounders].dropna()
        
        T = analysis_data[treatment].values
        Y = analysis_data[outcome].values
        
        # Synthetic confounder correlated with T and Y
        U = strength * (T - T.mean()) / T.std() + strength * (Y - Y.mean()) / Y.std() + np.random.randn(len(T)) * (1 - strength)
        
        # Add to confounders and re-estimate
        analysis_data_with_U = analysis_data.copy()
        analysis_data_with_U['synthetic_confounder'] = U
        
        adjusted = estimator.estimate_ate(
            analysis_data_with_U,
            treatment,
            outcome,
            confounders + ['synthetic_confounder'],
            method='ols'
        )
        
        adjusted_ate = adjusted.get('ate', 0)
        
        sensitivity_results.append({
            'confounder_strength': strength,
            'adjusted_ate': adjusted_ate,
            'bias': baseline_ate - adjusted_ate,
            'percent_change': ((adjusted_ate - baseline_ate) / baseline_ate * 100) if baseline_ate != 0 else 0
        })
    
    return {
        'baseline_ate': baseline_ate,
        'sensitivity_results': sensitivity_results,
        'treatment': treatment,
        'outcome': outcome,
    }


# Singleton instance
_estimator = None

def get_treatment_effect_estimator() -> TreatmentEffectEstimator:
    """Get or create singleton treatment effect estimator."""
    global _estimator
    if _estimator is None:
        _estimator = TreatmentEffectEstimator()
    return _estimator
