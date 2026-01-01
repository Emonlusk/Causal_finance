"""
Causal Discovery Service
========================
Automated discovery of causal relationships from historical financial data.

Implements:
- PC Algorithm (constraint-based causal discovery)
- Granger Causality Tests (time-series causality)
- Transfer Entropy (information-theoretic causality)
- Structural learning with score-based methods

These replace the hardcoded SECTOR_SENSITIVITY_MATRIX with data-driven discoveries.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from scipy import stats
import warnings

logger = logging.getLogger(__name__)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class CausalDiscoveryEngine:
    """
    Engine for discovering causal relationships from financial time series data.
    Uses multiple methods and combines results for robustness.
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        Initialize the causal discovery engine.
        
        Args:
            significance_level: p-value threshold for statistical tests
        """
        self.significance_level = significance_level
        self._pc_available = False
        self._statsmodels_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check which causal discovery libraries are available."""
        try:
            from pgmpy.estimators import PC
            self._pc_available = True
            logger.info("pgmpy PC algorithm available")
        except ImportError:
            logger.warning("pgmpy not available, PC algorithm disabled")
        
        try:
            from statsmodels.tsa.stattools import grangercausalitytests
            self._statsmodels_available = True
            logger.info("statsmodels Granger causality available")
        except ImportError:
            logger.warning("statsmodels not available, Granger causality disabled")
    
    # ============================================
    # GRANGER CAUSALITY
    # ============================================
    
    def granger_causality_test(
        self,
        data: pd.DataFrame,
        cause_col: str,
        effect_col: str,
        max_lag: int = 10
    ) -> Dict[str, Any]:
        """
        Test if cause_col Granger-causes effect_col.
        
        Granger causality tests whether past values of X help predict Y
        beyond what past values of Y alone can predict.
        
        Args:
            data: DataFrame with time series columns
            cause_col: Potential cause variable
            effect_col: Potential effect variable
            max_lag: Maximum lag to test
            
        Returns:
            Dictionary with test results
        """
        if not self._statsmodels_available:
            return self._fallback_correlation_test(data, cause_col, effect_col)
        
        from statsmodels.tsa.stattools import grangercausalitytests
        
        try:
            # Prepare data - need both columns without NaN
            test_data = data[[effect_col, cause_col]].dropna()
            
            if len(test_data) < max_lag * 3:
                return {'error': 'Insufficient data for Granger test'}
            
            # Run Granger causality test
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                results = grangercausalitytests(test_data, maxlag=max_lag, verbose=False)
            
            # Find optimal lag (lowest p-value)
            best_lag = 1
            best_pvalue = 1.0
            best_fstat = 0.0
            
            for lag in range(1, max_lag + 1):
                if lag in results:
                    # Use the ssr_ftest result
                    ftest = results[lag][0]['ssr_ftest']
                    f_stat, p_value = ftest[0], ftest[1]
                    
                    if p_value < best_pvalue:
                        best_pvalue = p_value
                        best_fstat = f_stat
                        best_lag = lag
            
            is_causal = best_pvalue < self.significance_level
            
            return {
                'cause': cause_col,
                'effect': effect_col,
                'method': 'granger_causality',
                'is_causal': is_causal,
                'p_value': float(best_pvalue),
                'f_statistic': float(best_fstat),
                'optimal_lag': best_lag,
                'significance_level': self.significance_level,
                'sample_size': len(test_data),
            }
            
        except Exception as e:
            logger.error(f"Granger test error for {cause_col} -> {effect_col}: {e}")
            return {'error': str(e)}
    
    def _fallback_correlation_test(
        self,
        data: pd.DataFrame,
        cause_col: str,
        effect_col: str
    ) -> Dict[str, Any]:
        """Fallback to lagged correlation when statsmodels unavailable."""
        try:
            test_data = data[[cause_col, effect_col]].dropna()
            
            best_corr = 0
            best_lag = 0
            best_pvalue = 1.0
            
            for lag in range(1, 11):
                cause_lagged = test_data[cause_col].shift(lag)
                valid = ~cause_lagged.isna()
                
                if valid.sum() > 30:
                    corr, pvalue = stats.pearsonr(
                        cause_lagged[valid],
                        test_data[effect_col][valid]
                    )
                    
                    if abs(corr) > abs(best_corr):
                        best_corr = corr
                        best_lag = lag
                        best_pvalue = pvalue
            
            return {
                'cause': cause_col,
                'effect': effect_col,
                'method': 'lagged_correlation',
                'is_causal': best_pvalue < self.significance_level and abs(best_corr) > 0.1,
                'correlation': float(best_corr),
                'p_value': float(best_pvalue),
                'optimal_lag': best_lag,
                'sample_size': len(test_data),
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def granger_causality_matrix(
        self,
        data: pd.DataFrame,
        variables: Optional[List[str]] = None,
        max_lag: int = 10
    ) -> pd.DataFrame:
        """
        Compute full Granger causality matrix for all variable pairs.
        
        Args:
            data: DataFrame with time series
            variables: List of variables to test (default: all columns)
            max_lag: Maximum lag for Granger test
            
        Returns:
            DataFrame where entry (i,j) indicates if variable i Granger-causes variable j
        """
        if variables is None:
            variables = list(data.columns)
        
        n = len(variables)
        results_matrix = pd.DataFrame(
            np.zeros((n, n)),
            index=variables,
            columns=variables
        )
        pvalue_matrix = pd.DataFrame(
            np.ones((n, n)),
            index=variables,
            columns=variables
        )
        
        logger.info(f"Computing Granger causality matrix for {n} variables")
        
        for i, cause in enumerate(variables):
            for j, effect in enumerate(variables):
                if i != j:  # Skip self-causation
                    result = self.granger_causality_test(data, cause, effect, max_lag)
                    
                    if 'error' not in result:
                        if result.get('is_causal', False):
                            results_matrix.loc[cause, effect] = 1
                        pvalue_matrix.loc[cause, effect] = result.get('p_value', 1.0)
        
        return results_matrix, pvalue_matrix
    
    # ============================================
    # PC ALGORITHM (Constraint-Based Discovery)
    # ============================================
    
    def pc_algorithm(
        self,
        data: pd.DataFrame,
        variables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run PC algorithm for causal structure learning.
        
        The PC algorithm discovers the causal DAG structure by:
        1. Starting with a fully connected graph
        2. Removing edges based on conditional independence tests
        3. Orienting edges based on v-structures
        
        Args:
            data: DataFrame with variables
            variables: Variables to include (default: all)
            
        Returns:
            Dictionary with discovered edges and structure
        """
        if not self._pc_available:
            logger.warning("PC algorithm not available, using correlation-based fallback")
            return self._correlation_based_structure(data, variables)
        
        try:
            from pgmpy.estimators import PC
            
            if variables is None:
                variables = list(data.columns)
            
            # Prepare data
            analysis_data = data[variables].dropna()
            
            if len(analysis_data) < 100:
                return {'error': 'Insufficient data for PC algorithm (need 100+ samples)'}
            
            logger.info(f"Running PC algorithm on {len(variables)} variables with {len(analysis_data)} samples")
            
            # Run PC algorithm
            pc = PC(analysis_data)
            model = pc.estimate(
                variant='stable',
                significance_level=self.significance_level,
                return_type='dag'
            )
            
            # Extract edges
            edges = []
            for edge in model.edges():
                edges.append({
                    'from': edge[0],
                    'to': edge[1],
                    'method': 'pc_algorithm'
                })
            
            return {
                'method': 'pc_algorithm',
                'edges': edges,
                'nodes': variables,
                'significance_level': self.significance_level,
                'sample_size': len(analysis_data),
            }
            
        except Exception as e:
            logger.error(f"PC algorithm error: {e}")
            return self._correlation_based_structure(data, variables)
    
    def _correlation_based_structure(
        self,
        data: pd.DataFrame,
        variables: Optional[List[str]] = None,
        threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        Fallback: Build structure based on significant correlations.
        Not truly causal, but provides baseline structure.
        """
        if variables is None:
            variables = list(data.columns)
        
        analysis_data = data[variables].dropna()
        corr_matrix = analysis_data.corr()
        
        edges = []
        for i, var1 in enumerate(variables):
            for j, var2 in enumerate(variables):
                if i < j:  # Avoid duplicates
                    corr = corr_matrix.loc[var1, var2]
                    if abs(corr) > threshold:
                        # Use temporal order if available (earlier variable causes later)
                        edges.append({
                            'from': var1,
                            'to': var2,
                            'correlation': float(corr),
                            'method': 'correlation_threshold'
                        })
        
        return {
            'method': 'correlation_threshold',
            'edges': edges,
            'nodes': variables,
            'threshold': threshold,
            'sample_size': len(analysis_data),
            'warning': 'Correlation does not imply causation - use for exploration only'
        }
    
    # ============================================
    # TRANSFER ENTROPY
    # ============================================
    
    def transfer_entropy(
        self,
        data: pd.DataFrame,
        source: str,
        target: str,
        lag: int = 1,
        bins: int = 10
    ) -> Dict[str, Any]:
        """
        Compute transfer entropy from source to target.
        
        Transfer entropy measures information flow: how much knowing
        the past of source reduces uncertainty about target's future.
        
        Args:
            data: DataFrame with time series
            source: Source variable name
            target: Target variable name
            lag: Time lag
            bins: Number of bins for discretization
            
        Returns:
            Dictionary with transfer entropy result
        """
        try:
            # Get data
            source_data = data[source].dropna().values
            target_data = data[target].dropna().values
            
            # Align lengths
            min_len = min(len(source_data), len(target_data))
            source_data = source_data[:min_len]
            target_data = target_data[:min_len]
            
            if min_len < lag + 10:
                return {'error': 'Insufficient data for transfer entropy'}
            
            # Discretize
            source_binned = pd.cut(source_data, bins=bins, labels=False)
            target_binned = pd.cut(target_data, bins=bins, labels=False)
            
            # Compute transfer entropy
            # TE(X->Y) = H(Y_t | Y_{t-1}) - H(Y_t | Y_{t-1}, X_{t-1})
            
            # Create lagged variables
            y_t = target_binned[lag:]
            y_past = target_binned[:-lag]
            x_past = source_binned[:-lag]
            
            # Joint probabilities
            def entropy(x):
                _, counts = np.unique(x, return_counts=True)
                probs = counts / counts.sum()
                return -np.sum(probs * np.log2(probs + 1e-10))
            
            def conditional_entropy(x, y):
                """H(X|Y)"""
                joint = np.column_stack([x, y])
                _, joint_counts = np.unique(joint, axis=0, return_counts=True)
                _, y_counts = np.unique(y, return_counts=True)
                
                h_joint = entropy(np.arange(len(joint_counts)))
                h_y = entropy(y)
                
                return h_joint - h_y
            
            # H(Y_t | Y_{t-1})
            h_y_given_ypast = conditional_entropy(y_t, y_past)
            
            # H(Y_t | Y_{t-1}, X_{t-1})
            joint_past = np.column_stack([y_past, x_past])
            joint_past_hash = np.array([hash(tuple(row)) % 1000000 for row in joint_past])
            h_y_given_both = conditional_entropy(y_t, joint_past_hash)
            
            transfer_ent = h_y_given_ypast - h_y_given_both
            
            # Significance test via shuffling
            n_shuffles = 100
            shuffle_te = []
            
            for _ in range(n_shuffles):
                x_shuffled = np.random.permutation(x_past)
                joint_shuffled = np.column_stack([y_past, x_shuffled])
                joint_hash = np.array([hash(tuple(row)) % 1000000 for row in joint_shuffled])
                h_shuffled = conditional_entropy(y_t, joint_hash)
                shuffle_te.append(h_y_given_ypast - h_shuffled)
            
            p_value = np.mean(np.array(shuffle_te) >= transfer_ent)
            
            return {
                'source': source,
                'target': target,
                'method': 'transfer_entropy',
                'transfer_entropy': float(transfer_ent),
                'p_value': float(p_value),
                'is_causal': p_value < self.significance_level and transfer_ent > 0.01,
                'lag': lag,
                'sample_size': min_len - lag,
            }
            
        except Exception as e:
            logger.error(f"Transfer entropy error: {e}")
            return {'error': str(e)}
    
    # ============================================
    # COMBINED DISCOVERY
    # ============================================
    
    def discover_all_relationships(
        self,
        data: pd.DataFrame,
        variables: Optional[List[str]] = None,
        methods: List[str] = ['granger', 'correlation']
    ) -> List[Dict[str, Any]]:
        """
        Run multiple causal discovery methods and combine results.
        
        Args:
            data: DataFrame with variables
            variables: Variables to analyze
            methods: List of methods to use
            
        Returns:
            List of discovered causal relationships
        """
        if variables is None:
            variables = list(data.columns)
        
        all_relationships = []
        
        # Granger causality
        if 'granger' in methods:
            logger.info("Running Granger causality tests...")
            for i, cause in enumerate(variables):
                for j, effect in enumerate(variables):
                    if i != j:
                        result = self.granger_causality_test(data, cause, effect)
                        if 'error' not in result and result.get('is_causal', False):
                            all_relationships.append(result)
        
        # PC algorithm
        if 'pc' in methods:
            logger.info("Running PC algorithm...")
            pc_result = self.pc_algorithm(data, variables)
            if 'edges' in pc_result:
                for edge in pc_result['edges']:
                    all_relationships.append({
                        'cause': edge['from'],
                        'effect': edge['to'],
                        'method': 'pc_algorithm',
                        'is_causal': True,
                    })
        
        # Transfer entropy
        if 'transfer_entropy' in methods:
            logger.info("Computing transfer entropy...")
            for i, source in enumerate(variables):
                for j, target in enumerate(variables):
                    if i != j:
                        result = self.transfer_entropy(data, source, target)
                        if 'error' not in result and result.get('is_causal', False):
                            all_relationships.append(result)
        
        # Correlation-based (fallback)
        if 'correlation' in methods:
            corr_result = self._correlation_based_structure(data, variables)
            for edge in corr_result.get('edges', []):
                all_relationships.append({
                    'cause': edge['from'],
                    'effect': edge['to'],
                    'method': 'correlation',
                    'correlation': edge.get('correlation'),
                    'is_causal': False,  # Mark as association, not causation
                    'warning': 'Correlation only - not causal'
                })
        
        return all_relationships
    
    def build_causal_dag(
        self,
        relationships: List[Dict[str, Any]],
        min_methods: int = 1
    ) -> Dict[str, Any]:
        """
        Build a consensus DAG from multiple discovery methods.
        
        Args:
            relationships: List of discovered relationships
            min_methods: Minimum number of methods that must agree
            
        Returns:
            DAG structure with nodes and edges
        """
        # Count agreements
        edge_counts = {}
        edge_details = {}
        
        for rel in relationships:
            if not rel.get('is_causal', False):
                continue
                
            cause = rel.get('cause')
            effect = rel.get('effect')
            
            if cause and effect:
                edge_key = (cause, effect)
                edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1
                
                if edge_key not in edge_details:
                    edge_details[edge_key] = []
                edge_details[edge_key].append(rel)
        
        # Build consensus DAG
        nodes = set()
        edges = []
        
        for edge_key, count in edge_counts.items():
            if count >= min_methods:
                cause, effect = edge_key
                nodes.add(cause)
                nodes.add(effect)
                
                # Aggregate evidence
                details = edge_details[edge_key]
                avg_pvalue = np.mean([d.get('p_value', 0.5) for d in details if 'p_value' in d])
                methods_used = list(set(d.get('method', 'unknown') for d in details))
                
                edges.append({
                    'from': cause,
                    'to': effect,
                    'agreement_count': count,
                    'methods': methods_used,
                    'avg_p_value': float(avg_pvalue),
                    'strength': 1.0 - avg_pvalue,  # Higher strength for lower p-value
                })
        
        return {
            'nodes': list(nodes),
            'edges': edges,
            'min_methods': min_methods,
            'total_relationships': len(relationships),
        }


# ============================================
# SECTOR-SPECIFIC CAUSAL DISCOVERY
# ============================================

def discover_sector_macro_relationships(
    feature_matrix: pd.DataFrame,
    sectors: List[str] = None,
    macro_vars: List[str] = None
) -> Dict[str, Any]:
    """
    Discover causal relationships between macroeconomic variables and sector returns.
    
    This replaces the hardcoded SECTOR_SENSITIVITY_MATRIX with data-driven discoveries.
    
    Args:
        feature_matrix: DataFrame with sector returns and macro variables
        sectors: List of sectors to analyze
        macro_vars: List of macro variables to test
        
    Returns:
        Dictionary mapping sectors to their causal drivers
    """
    if sectors is None:
        sectors = ['Technology', 'Healthcare', 'Energy', 'Financials', 'Industrials',
                   'Consumer_Discretionary', 'Consumer_Staples', 'Utilities', 'Materials',
                   'Real_Estate', 'Communication_Services']
    
    if macro_vars is None:
        macro_vars = ['Fed_Funds_Rate_Change', 'CPI_Change', 'Treasury_10Y_Yield_Change',
                      'VIX_Change', 'Oil_WTI_Change', 'Unemployment_Rate_Change']
    
    engine = CausalDiscoveryEngine()
    
    sector_drivers = {}
    
    for sector in sectors:
        return_col = f'{sector}_Return_1d'
        
        if return_col not in feature_matrix.columns:
            continue
        
        drivers = []
        
        for macro_var in macro_vars:
            if macro_var not in feature_matrix.columns:
                continue
            
            # Test Granger causality
            result = engine.granger_causality_test(
                feature_matrix,
                cause_col=macro_var,
                effect_col=return_col,
                max_lag=10
            )
            
            if 'error' not in result and result.get('is_causal', False):
                drivers.append({
                    'variable': macro_var,
                    'lag': result.get('optimal_lag', 1),
                    'p_value': result.get('p_value'),
                    'f_statistic': result.get('f_statistic'),
                })
        
        sector_drivers[sector] = drivers
    
    return sector_drivers


# Singleton instance
_engine = None

def get_causal_discovery_engine() -> CausalDiscoveryEngine:
    """Get or create singleton causal discovery engine."""
    global _engine
    if _engine is None:
        _engine = CausalDiscoveryEngine()
    return _engine
