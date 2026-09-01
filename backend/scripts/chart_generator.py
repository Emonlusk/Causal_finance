"""
Paper-Ready Chart Generation
==============================
Generates all publication-quality figures for the research paper at 300 DPI.

Charts:
1. Cumulative returns (log scale) -- all portfolios
2. Rolling 12-month Sharpe ratio
3. Drawdown chart
4. Portfolio weight evolution (stacked area)
5. CATE distribution plot
6. Causal DAG visualization (delegated to causal_discovery.py)
7. Granger causality heatmap (delegated to causal_discovery.py)

Usage:
    from scripts.chart_generator import generate_all_charts
    generate_all_charts(backtest_results)
"""

import os
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'figures')


def _ensure_dir():
    """Ensure results/figures directory exists."""
    os.makedirs(RESULTS_DIR, exist_ok=True)


def plot_cumulative_returns(
    backtest_results: Dict[str, Dict],
    output_path: Optional[str] = None,
    log_scale: bool = True,
    title: str = 'Cumulative Portfolio Returns'
) -> str:
    """
    Plot cumulative returns of all portfolios on one chart.
    
    Args:
        backtest_results: Dict mapping portfolio name to backtest result dict
        output_path: Save path (defaults to results/figures/cumulative_returns.png)
        log_scale: Use log scale for y-axis
        title: Plot title
    
    Returns:
        Path to saved figure
    """
    _ensure_dir()
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, 'cumulative_returns.png')
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        plotted = 0

        # Prefer daily_returns (present for all four strategies - walk-forward
        # results only carry this, not time_series) so every series plots on
        # the same trading-day-index x-axis, matching plot_drawdown's pattern.
        # Fall back to time_series (calendar dates) only if daily_returns is
        # absent.
        for idx, (name, bt) in enumerate(backtest_results.items()):
            color = colors[idx % len(colors)]
            daily_returns = bt.get('daily_returns', [])
            if daily_returns:
                cumulative = np.cumprod(1 + np.array(daily_returns))
                ax.plot(range(len(cumulative)), cumulative, label=name, linewidth=1.5, color=color)
                plotted += 1
                continue

            ts = bt.get('time_series', [])
            if not ts:
                continue

            dates = pd.to_datetime([p['date'] for p in ts])
            values = [p['value'] for p in ts]
            ax.plot(dates, values, label=name, linewidth=1.5, color=color)
            plotted += 1

        if plotted == 0:
            plt.close()
            logger.warning("No return data available for cumulative returns chart")
            return ''

        if log_scale:
            ax.set_yscale('log')
            ax.set_ylabel('Cumulative Return (Log Scale)', fontsize=11)
        else:
            ax.set_ylabel('Cumulative Return', fontsize=11)

        ax.set_xlabel('Trading Days', fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Cumulative returns chart saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate cumulative returns chart: {e}")
        return ''


def plot_rolling_sharpe(
    backtest_results: Dict[str, Dict],
    window_days: int = 252,
    risk_free_rate: float = 0.04,
    output_path: Optional[str] = None,
    title: str = 'Rolling 12-Month Sharpe Ratio'
) -> str:
    """
    Plot rolling Sharpe ratio for each portfolio.
    
    Args:
        backtest_results: Dict of backtest results with 'daily_returns' arrays
        window_days: Rolling window in trading days (252 = ~12 months)
        risk_free_rate: Annual risk-free rate
        output_path: Save path
        title: Plot title
    
    Returns:
        Path to saved figure
    """
    _ensure_dir()
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, 'rolling_sharpe.png')
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        plotted = 0
        
        for idx, (name, bt) in enumerate(backtest_results.items()):
            daily_returns = bt.get('daily_returns', [])
            if not daily_returns or len(daily_returns) < window_days:
                continue
            
            returns = pd.Series(daily_returns)
            
            # Rolling Sharpe
            rolling_mean = returns.rolling(window_days).mean() * 252
            rolling_std = returns.rolling(window_days).std() * np.sqrt(252)
            rolling_sharpe = (rolling_mean - risk_free_rate) / rolling_std
            
            color = colors[idx % len(colors)]
            ax.plot(range(len(rolling_sharpe)), rolling_sharpe.values,
                   label=name, linewidth=1.5, color=color)
            plotted += 1
        
        if plotted == 0:
            plt.close()
            logger.warning("No daily_returns data available for rolling Sharpe chart")
            return ''
        
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        ax.set_xlabel('Trading Days', fontsize=11)
        ax.set_ylabel('Rolling Sharpe Ratio', fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Rolling Sharpe chart saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate rolling Sharpe chart: {e}")
        return ''


def plot_drawdown(
    backtest_results: Dict[str, Dict],
    output_path: Optional[str] = None,
    title: str = 'Portfolio Drawdowns'
) -> str:
    """
    Plot drawdown chart for each portfolio.
    
    Args:
        backtest_results: Dict of backtest results
        output_path: Save path
        title: Plot title
    
    Returns:
        Path to saved figure
    """
    _ensure_dir()
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, 'drawdowns.png')
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(12, 6))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for idx, (name, bt) in enumerate(backtest_results.items()):
            daily_returns = bt.get('daily_returns', [])
            if not daily_returns:
                # Try drawdown_series
                dd_series = bt.get('drawdown_series', [])
                if dd_series:
                    dates = pd.to_datetime([p['date'] for p in dd_series])
                    dd_values = [p['drawdown'] for p in dd_series]
                    color = colors[idx % len(colors)]
                    ax.fill_between(dates, dd_values, 0, alpha=0.3, color=color, label=name)
                    ax.plot(dates, dd_values, linewidth=0.8, color=color)
                continue
            
            returns = np.array(daily_returns)
            cumulative = np.cumprod(1 + returns)
            rolling_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative / rolling_max - 1) * 100
            
            color = colors[idx % len(colors)]
            ax.fill_between(range(len(drawdown)), drawdown, 0, alpha=0.3, color=color, label=name)
            ax.plot(range(len(drawdown)), drawdown, linewidth=0.8, color=color)
        
        ax.set_xlabel('Trading Days', fontsize=11)
        ax.set_ylabel('Drawdown (%)', fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Drawdown chart saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate drawdown chart: {e}")
        return ''


def plot_weight_evolution(
    weights_over_time: List[Dict[str, Any]],
    output_path: Optional[str] = None,
    title: str = 'Causal Portfolio Weight Evolution'
) -> str:
    """
    Plot stacked area chart of portfolio weight evolution.
    
    Args:
        weights_over_time: List of dicts with 'date' and weight keys per asset
        output_path: Save path
        title: Plot title
    
    Returns:
        Path to saved figure
    """
    _ensure_dir()
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, 'weight_evolution.png')
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        if not weights_over_time:
            logger.warning("No weight history to plot")
            return ''
        
        df = pd.DataFrame(weights_over_time)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        asset_cols = [c for c in df.columns if c not in ['date']]
        df[asset_cols].plot.area(ax=ax, alpha=0.8, linewidth=0.5)
        
        ax.set_xlabel('Date', fontsize=11)
        ax.set_ylabel('Portfolio Weight', fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.legend(fontsize=8, loc='center left', bbox_to_anchor=(1, 0.5))
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Weight evolution chart saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate weight evolution chart: {e}")
        return ''


def plot_cate_distribution(
    cate_values: Dict[str, Dict[str, float]],
    treatment_name: str = 'Fed_Funds_Rate_Change',
    output_path: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """
    Plot CATE distribution across sectors.
    
    Args:
        cate_values: Dict mapping sector to CATE stats (mean, std, 5th, 95th)
        treatment_name: Name of the treatment variable
        output_path: Save path
        title: Plot title
    
    Returns:
        Path to saved figure
    """
    _ensure_dir()
    if output_path is None:
        output_path = os.path.join(RESULTS_DIR, 'cate_distribution.png')
    
    if title is None:
        title = f'CATE Distribution by Sector -- Treatment: {treatment_name}'
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        sectors = list(cate_values.keys())
        means = [cate_values[s].get('mean', 0) for s in sectors]
        stds = [cate_values[s].get('std', 0) for s in sectors]
        ci_low = [cate_values[s].get('5th', means[i] - 1.645 * stds[i]) for i, s in enumerate(sectors)]
        ci_high = [cate_values[s].get('95th', means[i] + 1.645 * stds[i]) for i, s in enumerate(sectors)]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        y_pos = range(len(sectors))
        errors = [[m - l for m, l in zip(means, ci_low)],
                   [h - m for m, h in zip(means, ci_high)]]
        
        colors = ['#d62728' if m < 0 else '#2ca02c' for m in means]
        
        ax.barh(y_pos, means, xerr=errors, align='center', alpha=0.8,
               color=colors, edgecolor='black', linewidth=0.5, capsize=3)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels([s.replace('_', ' ') for s in sectors], fontsize=9)
        ax.set_xlabel('CATE (Treatment Effect)', fontsize=11)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.axvline(x=0, color='black', linestyle='-', linewidth=0.8)
        ax.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"CATE distribution chart saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate CATE distribution chart: {e}")
        return ''


def generate_all_charts(
    backtest_results: Dict[str, Dict],
    weights_history: Optional[List[Dict]] = None,
    cate_values: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Generate all paper-required charts.
    
    Args:
        backtest_results: Dict mapping portfolio name to backtest results
        weights_history: Optional weight history for evolution chart
        cate_values: Optional CATE values for distribution chart
    
    Returns:
        Dict mapping chart name to saved file path
    """
    charts = {}
    
    # Chart 1: Cumulative returns (log scale)
    charts['cumulative_returns'] = plot_cumulative_returns(backtest_results)
    
    # Chart 2: Rolling 12-month Sharpe
    charts['rolling_sharpe'] = plot_rolling_sharpe(backtest_results)
    
    # Chart 3: Drawdown chart
    charts['drawdowns'] = plot_drawdown(backtest_results)
    
    # Chart 4: Weight evolution
    if weights_history:
        charts['weight_evolution'] = plot_weight_evolution(weights_history)
    
    # Chart 5: CATE distribution
    if cate_values:
        charts['cate_distribution'] = plot_cate_distribution(cate_values)
    
    logger.info(f"Generated {len(charts)} charts")
    return charts
