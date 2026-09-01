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
            
            is_causal = bool(best_pvalue < self.significance_level)
            
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
                'is_causal': bool(best_pvalue < self.significance_level and abs(best_corr) > 0.1),
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
            
            # Run PC algorithm. ci_test defaults to 'chi_square' in pgmpy,
            # which assumes discrete/categorical variables and builds a
            # contingency table per test - on continuous return series (each
            # row effectively its own category) that's both statistically
            # wrong and combinatorially slow (multi-minute runs observed on
            # 11 variables). 'pearsonr' (partial correlation) is the
            # standard conditional-independence test for continuous data and
            # is what this algorithm should have been using all along.
            # max_cond_vars bounds worst-case runtime as variable count
            # grows; 3 is enough to catch real confounding among ~10-15
            # macro/sector variables without the combinatorial blowup of
            # pgmpy's default of 5.
            pc = PC(analysis_data)
            model = pc.estimate(
                variant='stable',
                ci_test='pearsonr',
                max_cond_vars=3,
                significance_level=self.significance_level,
                return_type='dag',
                show_progress=False,
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


def visualize_causal_dag(
    edges: List[Dict[str, Any]],
    output_path: str = 'results/figures/causal_dag.png',
    title: str = 'Discovered Causal DAG: Macroeconomic Factors → Sector Returns'
) -> str:
    """
    Generate publication-quality causal DAG visualization.
    
    Args:
        edges: List of edge dicts with 'cause', 'effect', 'weight', 'method' keys
        output_path: Path to save the PNG figure
        title: Plot title
        
    Returns:
        Path to saved figure
    """
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        import networkx as nx
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        G = nx.DiGraph()
        
        # Classify nodes
        macro_nodes = set()
        sector_nodes = set()
        
        for edge in edges:
            cause = edge.get('cause', edge.get('from', ''))
            effect = edge.get('effect', edge.get('to', ''))
            weight = edge.get('weight', edge.get('strength', 1.0))
            
            G.add_edge(cause, effect, weight=abs(weight))
            
            # Heuristic classification
            if 'Return' in effect or any(s in effect for s in ['Technology', 'Healthcare', 'Energy', 'Financial']):
                sector_nodes.add(effect)
                macro_nodes.add(cause)
            else:
                macro_nodes.add(cause)
                macro_nodes.add(effect)
        
        if len(G.nodes()) == 0:
            logger.warning("No edges to visualize")
            return ''
        
        # Layout
        if len(macro_nodes) > 0 and len(sector_nodes) > 0:
            # Bipartite-like layout: macros on left, sectors on right
            pos = {}
            macro_list = sorted(macro_nodes)
            sector_list = sorted(sector_nodes)
            for i, node in enumerate(macro_list):
                pos[node] = (-1, -i * 1.5)
            for i, node in enumerate(sector_list):
                pos[node] = (1, -i * 1.2)
            # Any remaining nodes
            remaining = set(G.nodes()) - macro_nodes - sector_nodes
            for i, node in enumerate(remaining):
                pos[node] = (0, -i * 1.5)
        else:
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # Draw edges with varying widths based on weight
        edge_weights = [G[u][v].get('weight', 1) for u, v in G.edges()]
        max_w = max(edge_weights) if edge_weights else 1
        edge_widths = [1 + 3 * (w / max_w) for w in edge_weights]
        
        # Node colors
        node_colors = []
        for node in G.nodes():
            if node in macro_nodes:
                node_colors.append('#4A90D9')  # Blue for macro
            elif node in sector_nodes:
                node_colors.append('#50C878')  # Green for sectors
            else:
                node_colors.append('#FFB347')  # Orange for other
        
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, 
                              node_size=2000, alpha=0.9, edgecolors='black', linewidths=1.5)
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=7, font_weight='bold')
        nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths, alpha=0.6,
                              edge_color='#333333', arrows=True, arrowsize=20,
                              connectionstyle='arc3,rad=0.1')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#4A90D9', edgecolor='black', label='Macro Factors'),
            Patch(facecolor='#50C878', edgecolor='black', label='Sector Returns'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
        
        ax.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"DAG visualization saved to {output_path}")
        return output_path
        
    except ImportError as e:
        logger.error(f"Cannot create DAG visualization (missing dependency): {e}")
        return ''
    except Exception as e:
        logger.error(f"DAG visualization error: {e}")
        return ''


def generate_granger_heatmap(
    feature_matrix: pd.DataFrame,
    cause_vars: List[str],
    effect_vars: List[str],
    max_lag: int = 10,
    output_path: str = 'results/figures/granger_heatmap.png'
) -> str:
    """
    Generate Granger causality p-value heatmap.
    
    Args:
        feature_matrix: DataFrame with time series data
        cause_vars: List of potential cause variable names
        effect_vars: List of potential effect variable names
        max_lag: Maximum lag for Granger test
        output_path: Path to save figure
        
    Returns:
        Path to saved figure
    """
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        engine = CausalDiscoveryEngine()
        
        # Build p-value matrix
        p_matrix = np.ones((len(cause_vars), len(effect_vars)))
        
        for i, cause in enumerate(cause_vars):
            for j, effect in enumerate(effect_vars):
                if cause not in feature_matrix.columns or effect not in feature_matrix.columns:
                    continue
                result = engine.granger_causality_test(
                    feature_matrix, cause_col=cause, effect_col=effect, max_lag=max_lag
                )
                if 'p_value' in result and result['p_value'] is not None:
                    p_matrix[i, j] = result['p_value']
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Heatmap: -log10(p) so significant values are brighter
        log_p = -np.log10(p_matrix + 1e-10)
        
        im = ax.imshow(log_p, cmap='YlOrRd', aspect='auto', interpolation='nearest')
        
        ax.set_xticks(range(len(effect_vars)))
        ax.set_xticklabels([v.replace('_Return_1d', '').replace('_', ' ') for v in effect_vars],
                          rotation=45, ha='right', fontsize=8)
        ax.set_yticks(range(len(cause_vars)))
        ax.set_yticklabels([v.replace('_Change', '').replace('_', ' ') for v in cause_vars], fontsize=8)
        
        # Add significance markers
        for i in range(len(cause_vars)):
            for j in range(len(effect_vars)):
                p_val = p_matrix[i, j]
                marker = ''
                if p_val < 0.01:
                    marker = '***'
                elif p_val < 0.05:
                    marker = '**'
                elif p_val < 0.10:
                    marker = '*'
                ax.text(j, i, f'{p_val:.3f}\n{marker}', ha='center', va='center', fontsize=6,
                       color='white' if log_p[i, j] > 1.5 else 'black')
        
        plt.colorbar(im, ax=ax, label='-log10(p-value)')
        ax.set_title('Granger Causality p-values: Macro Factors → Sector Returns', fontsize=12, fontweight='bold')
        ax.set_xlabel('Sector Returns')
        ax.set_ylabel('Macro Factors')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Granger heatmap saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Granger heatmap error: {e}")
        return ''


# Singleton instance
_engine = None

def get_causal_discovery_engine() -> CausalDiscoveryEngine:
    """Get or create singleton causal discovery engine."""
    global _engine
    if _engine is None:
        _engine = CausalDiscoveryEngine()
    return _engine
