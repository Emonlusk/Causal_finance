"""
Scenario Simulation Service
Simulates portfolio performance under various economic scenarios
"""

from typing import Dict, List, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Import causal sensitivity data
# Use get_active_sensitivity_matrix() to prefer trained ML models over hardcoded defaults
from app.services.causal_service import DEFAULT_SECTOR_SENSITIVITY, get_active_sensitivity_matrix

# Sector ETF to sector key mapping
SECTOR_ETF_MAP = {
    'XLK': 'technology',
    'XLV': 'healthcare',
    'XLE': 'energy',
    'XLF': 'financials',
    'XLI': 'industrials',
    'XLY': 'consumer_discretionary',
    'XLP': 'consumer_staples',
    'XLU': 'utilities',
    'XLB': 'materials',
    'XLRE': 'real_estate',
    'XLC': 'communication_services'
}


def run_scenario_simulation(
    parameters: Dict[str, Dict],
    portfolio_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Run a scenario simulation based on economic shock parameters
    
    Args:
        parameters: Dict of economic factors and their changes
            e.g., {'interest_rates': {'change': 0.02}, 'inflation': {'change': 0.01}}
        portfolio_weights: Optional portfolio weights to simulate
            e.g., {'XLK': 0.25, 'XLV': 0.20, ...}
    
    Returns:
        Simulation results with impacts on different portfolio types
    """
    # Default portfolio if not provided
    if not portfolio_weights:
        portfolio_weights = {
            'XLK': 0.25,  # Technology
            'XLV': 0.15,  # Healthcare
            'XLE': 0.10,  # Energy
            'XLF': 0.15,  # Financials
            'XLI': 0.10,  # Industrials
            'XLY': 0.10,  # Consumer Discretionary
            'XLP': 0.05,  # Consumer Staples
            'XLU': 0.05,  # Utilities
            'XLB': 0.05   # Materials
        }
    
    # Calculate sector impacts based on causal relationships
    sector_impacts = _calculate_sector_impacts(parameters)
    
    # Calculate portfolio impact
    portfolio_impact = _calculate_portfolio_impact(portfolio_weights, sector_impacts)
    
    # Calculate causal-optimized portfolio impact (adjusted weights)
    causal_weights = _get_causal_adjusted_weights(portfolio_weights, parameters)
    causal_impact = _calculate_portfolio_impact(causal_weights, sector_impacts)
    
    # Calculate traditional benchmark impact (equal weight)
    n_sectors = len(portfolio_weights)
    traditional_weights = {k: 1/n_sectors for k in portfolio_weights}
    traditional_impact = _calculate_portfolio_impact(traditional_weights, sector_impacts)
    
    # Generate recommendations
    recommendations = _generate_recommendations(portfolio_weights, sector_impacts, parameters)
    
    # Build sector breakdown for visualization
    sector_breakdown = []
    for etf, weight in portfolio_weights.items():
        sector_key = SECTOR_ETF_MAP.get(etf, etf.lower())
        impact = sector_impacts.get(sector_key, 0)
        
        sector_breakdown.append({
            'sector': sector_key.replace('_', ' ').title(),
            'symbol': etf,
            'weight': round(weight * 100, 1),
            'current': round(impact * weight * 100, 2),
            'causal': round(impact * causal_weights.get(etf, weight) * 100, 2),
            'traditional': round(impact * traditional_weights.get(etf, 1/n_sectors) * 100, 2),
            'raw_impact': round(impact * 100, 2)
        })
    
    return {
        'portfolio_impact': round(portfolio_impact, 4),
        'portfolio_impact_percent': round(portfolio_impact * 100, 2),
        'causal_optimized_impact': round(causal_impact, 4),
        'causal_optimized_percent': round(causal_impact * 100, 2),
        'traditional_impact': round(traditional_impact, 4),
        'traditional_percent': round(traditional_impact * 100, 2),
        'sector_impacts': {k: round(v * 100, 2) for k, v in sector_impacts.items()},
        'sector_breakdown': sector_breakdown,
        'recommendations': recommendations,
        'parameters_used': parameters,
        'causal_weights': {k: round(v, 4) for k, v in causal_weights.items()},
        'improvement': {
            'vs_current': round((portfolio_impact - causal_impact) * 100, 2),
            'vs_traditional': round((traditional_impact - causal_impact) * 100, 2)
        }
    }


def _calculate_sector_impacts(parameters: Dict[str, Dict]) -> Dict[str, float]:
    """
    Calculate the impact on each sector based on economic changes.
    Uses trained ML sensitivity matrix if available, otherwise falls back to defaults.
    """
    sector_impacts = {}
    
    # Use trained ML matrix when available, fall back to hardcoded defaults
    active_matrix = get_active_sensitivity_matrix()
    
    for sector, sensitivities in active_matrix.items():
        total_impact = 0
        
        for factor, params in parameters.items():
            change = params.get('change', 0)
            sensitivity = sensitivities.get(factor, 0)
            
            # Impact = sensitivity * change magnitude
            impact = sensitivity * change
            total_impact += impact
        
        sector_impacts[sector] = total_impact
    
    return sector_impacts


def _calculate_portfolio_impact(
    weights: Dict[str, float],
    sector_impacts: Dict[str, float]
) -> float:
    """
    Calculate total portfolio impact given weights and sector impacts
    """
    total_impact = 0
    
    for etf, weight in weights.items():
        sector_key = SECTOR_ETF_MAP.get(etf, etf.lower())
        impact = sector_impacts.get(sector_key, 0)
        total_impact += weight * impact
    
    return total_impact


def _get_causal_adjusted_weights(
    current_weights: Dict[str, float],
    parameters: Dict[str, Dict]
) -> Dict[str, float]:
    """
    Adjust portfolio weights based on causal insights for the scenario
    """
    adjusted_weights = current_weights.copy()
    
    # Calculate expected impacts
    sector_impacts = _calculate_sector_impacts(parameters)
    
    # Identify sectors to reduce/increase
    sorted_sectors = sorted(sector_impacts.items(), key=lambda x: x[1])
    
    # Get worst and best performing sectors
    worst_sectors = [s[0] for s in sorted_sectors[:3]]
    best_sectors = [s[0] for s in sorted_sectors[-3:]]
    
    # Adjust weights: reduce exposure to worst, increase to best
    reallocation = 0
    
    for etf, weight in adjusted_weights.items():
        sector_key = SECTOR_ETF_MAP.get(etf, etf.lower())
        
        if sector_key in worst_sectors and weight > 0.05:
            reduction = weight * 0.3  # Reduce by 30%
            adjusted_weights[etf] = weight - reduction
            reallocation += reduction
        elif sector_key in best_sectors:
            # Mark for increase
            pass
    
    # Redistribute to best sectors
    best_etfs = [etf for etf in adjusted_weights if SECTOR_ETF_MAP.get(etf, etf.lower()) in best_sectors]
    if best_etfs and reallocation > 0:
        increase_per_etf = reallocation / len(best_etfs)
        for etf in best_etfs:
            adjusted_weights[etf] = adjusted_weights.get(etf, 0) + increase_per_etf
    
    # Normalize weights to sum to 1
    total = sum(adjusted_weights.values())
    if total > 0:
        adjusted_weights = {k: v/total for k, v in adjusted_weights.items()}
    
    return adjusted_weights


def _generate_recommendations(
    weights: Dict[str, float],
    sector_impacts: Dict[str, float],
    parameters: Dict[str, Dict]
) -> Dict[str, List[Dict]]:
    """
    Generate actionable recommendations based on scenario analysis
    """
    immediate_actions = []
    strategic_shifts = []
    
    # Sort sectors by impact
    sorted_impacts = sorted(sector_impacts.items(), key=lambda x: x[1])
    
    # Immediate actions: reduce exposure to worst performing
    for sector, impact in sorted_impacts[:3]:
        if impact < -0.02:  # More than 2% negative impact
            etfs_in_sector = [etf for etf, s in SECTOR_ETF_MAP.items() if s == sector]
            for etf in etfs_in_sector:
                if etf in weights and weights[etf] > 0.05:
                    immediate_actions.append({
                        'action': 'reduce',
                        'sector': sector.replace('_', ' ').title(),
                        'symbol': etf,
                        'current_weight': round(weights[etf] * 100, 1),
                        'suggested_reduction': round(weights[etf] * 0.3 * 100, 1),
                        'reason': f"High negative impact ({impact*100:.1f}%) under this scenario"
                    })
    
    # Immediate actions: increase exposure to best performing
    for sector, impact in sorted_impacts[-2:]:
        if impact > 0.01:  # More than 1% positive impact
            etfs_in_sector = [etf for etf, s in SECTOR_ETF_MAP.items() if s == sector]
            for etf in etfs_in_sector:
                immediate_actions.append({
                    'action': 'increase',
                    'sector': sector.replace('_', ' ').title(),
                    'symbol': etf,
                    'current_weight': round(weights.get(etf, 0) * 100, 1),
                    'suggested_increase': 5,
                    'reason': f"Positive impact ({impact*100:.1f}%) under this scenario"
                })
    
    # Strategic shifts based on economic factors
    for factor, params in parameters.items():
        change = params.get('change', 0)
        
        if factor == 'interest_rates' and change > 0.01:
            strategic_shifts.append({
                'strategy': 'Rate Protection',
                'description': 'Diversify into rate-resistant assets like consumer staples and healthcare',
                'confidence': 'high' if change > 0.02 else 'medium'
            })
        
        if factor == 'inflation' and change > 0.02:
            strategic_shifts.append({
                'strategy': 'Inflation Hedge',
                'description': 'Consider TIPS, commodities, or energy sector exposure',
                'confidence': 'high'
            })
        
        if factor == 'gdp_growth' and change < -0.01:
            strategic_shifts.append({
                'strategy': 'Defensive Positioning',
                'description': 'Increase allocation to defensive sectors (utilities, healthcare, staples)',
                'confidence': 'high' if change < -0.02 else 'medium'
            })
    
    # Add general hedging recommendation for high-impact scenarios
    total_impact = sum(sector_impacts.values()) / len(sector_impacts) if sector_impacts else 0
    if total_impact < -0.03:
        strategic_shifts.append({
            'strategy': 'Hedging',
            'description': 'Consider protective puts or increasing cash allocation',
            'confidence': 'medium'
        })
    
    return {
        'immediate': immediate_actions[:5],  # Limit to top 5
        'strategic': strategic_shifts[:3]  # Limit to top 3
    }


def compare_scenarios(
    scenarios: List[Dict],
    portfolio_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Compare multiple scenarios side by side
    """
    results = []
    
    for scenario in scenarios:
        name = scenario.get('name', 'Unnamed')
        parameters = scenario.get('parameters', {})
        
        simulation = run_scenario_simulation(parameters, portfolio_weights)
        
        results.append({
            'name': name,
            'parameters': parameters,
            'portfolio_impact': simulation['portfolio_impact_percent'],
            'causal_impact': simulation['causal_optimized_percent'],
            'traditional_impact': simulation['traditional_percent'],
            'improvement': simulation['improvement']
        })
    
    # Find best and worst scenarios
    sorted_by_impact = sorted(results, key=lambda x: x['portfolio_impact'])
    
    return {
        'scenarios': results,
        'worst_scenario': sorted_by_impact[0]['name'],
        'best_scenario': sorted_by_impact[-1]['name'],
        'average_impact': round(np.mean([r['portfolio_impact'] for r in results]), 2),
        'average_causal_improvement': round(np.mean([r['improvement']['vs_current'] for r in results]), 2)
    }


def get_regime_analysis(portfolio_weights: Dict[str, float]) -> Dict[str, Any]:
    """
    Analyze portfolio performance across different market regimes
    """
    regimes = {
        'rate_hike': {'interest_rates': {'change': 0.02}, 'inflation': {'change': 0.01}},
        'inflation_spike': {'inflation': {'change': 0.04}, 'gdp_growth': {'change': -0.005}},
        'recession': {'gdp_growth': {'change': -0.03}, 'unemployment': {'change': 0.02}},
        'bull_market': {'gdp_growth': {'change': 0.04}, 'vix': {'change': -0.25}}
    }
    
    regime_results = {}
    
    for regime_name, parameters in regimes.items():
        simulation = run_scenario_simulation(parameters, portfolio_weights)
        
        regime_results[regime_name] = {
            'current': simulation['portfolio_impact_percent'],
            'causal': simulation['causal_optimized_percent'],
            'traditional': simulation['traditional_percent'],
            'improvement': simulation['improvement']['vs_current']
        }
    
    return {
        'regimes': regime_results,
        'summary': {
            'best_regime': max(regime_results.items(), key=lambda x: x[1]['current'])[0],
            'worst_regime': min(regime_results.items(), key=lambda x: x[1]['current'])[0],
            'causal_advantage': round(np.mean([r['improvement'] for r in regime_results.values()]), 2)
        }
    }
