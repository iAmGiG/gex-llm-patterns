"""Hedge Ratio Optimization Analysis (#500)

Determine optimal hedge ratios and allocations across GEX regimes.

Research questions:
- Optimal bond/commodity allocation in negative gamma
- Correlation stability across regime transitions
- Dynamic vs static hedge ratios
- Stress test portfolio against regime transitions

Data: Cross-asset GEX database (2020 has best multi-asset coverage)
"""

import sqlite3
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize


def load_price_data(db_path: str = ".cache/options_historical.db") -> pd.DataFrame:
    """Load price and regime data from SQLite database."""
    conn = sqlite3.connect(db_path)
    query = """
        SELECT symbol, trading_date, underlying_price, regime, asset_class
        FROM options_daily_summary
        WHERE underlying_price IS NOT NULL
        ORDER BY trading_date, symbol
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df["trading_date"] = pd.to_datetime(df["trading_date"])

    # Normalize regime names
    regime_map = {
        "POSITIVE_GAMMA": "POSITIVE",
        "NEGATIVE_GAMMA": "NEGATIVE",
        "NEUTRAL": "NEUTRAL",
    }
    df["regime"] = df["regime"].map(regime_map).fillna("UNKNOWN")

    return df


def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily returns for each symbol."""
    # Pivot to get prices
    prices = df.pivot_table(index="trading_date", columns="symbol", values="underlying_price", aggfunc="first")

    # Calculate returns (drop rows where all values are NaN)
    returns = prices.pct_change(fill_method=None)
    # Keep rows that have at least some valid returns
    returns = returns.dropna(how="all")
    # Drop the first row which is all NaN from pct_change
    returns = returns.iloc[1:]

    return returns


def get_regime_series(df: pd.DataFrame, reference_symbol: str = "SPY") -> pd.Series:
    """Get regime series for a reference symbol."""
    symbol_df = df[df["symbol"] == reference_symbol].copy()
    symbol_df = symbol_df.set_index("trading_date")["regime"]
    return symbol_df


def calculate_regime_returns(returns: pd.DataFrame, regime_series: pd.Series) -> Dict[str, pd.DataFrame]:
    """Split returns by regime."""
    common_dates = returns.index.intersection(regime_series.index)
    returns_aligned = returns.loc[common_dates]
    regime_aligned = regime_series.loc[common_dates]

    regime_returns = {}
    for regime in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
        mask = regime_aligned == regime
        if mask.sum() > 5:
            regime_returns[regime] = returns_aligned[mask]

    return regime_returns


def portfolio_variance(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """Calculate portfolio variance."""
    return weights @ cov_matrix @ weights


def portfolio_return(weights: np.ndarray, mean_returns: np.ndarray) -> float:
    """Calculate portfolio return."""
    return weights @ mean_returns


def optimize_min_variance(returns: pd.DataFrame, symbols: List[str]) -> Tuple[np.ndarray, float]:
    """Find minimum variance portfolio."""
    available = [s for s in symbols if s in returns.columns]
    if len(available) < 2:
        return None, None

    ret_subset = returns[available].dropna()
    if len(ret_subset) < 30:
        return None, None

    cov = ret_subset.cov().values
    n = len(available)

    # Constraints: weights sum to 1
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    # Bounds: 0 <= weight <= 1
    bounds = [(0, 1) for _ in range(n)]
    # Initial guess: equal weight
    x0 = np.ones(n) / n

    result = minimize(
        portfolio_variance,
        x0,
        args=(cov,),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )

    if result.success:
        return dict(zip(available, result.x)), np.sqrt(result.fun) * np.sqrt(252)
    return None, None


def optimize_max_sharpe(returns: pd.DataFrame, symbols: List[str], risk_free: float = 0.02) -> Tuple[Dict, float]:
    """Find maximum Sharpe ratio portfolio."""
    available = [s for s in symbols if s in returns.columns]
    if len(available) < 2:
        return None, None

    ret_subset = returns[available].dropna()
    if len(ret_subset) < 30:
        return None, None

    mean_ret = ret_subset.mean().values * 252
    cov = ret_subset.cov().values * 252
    n = len(available)

    def neg_sharpe(weights):
        port_ret = weights @ mean_ret
        port_vol = np.sqrt(weights @ cov @ weights)
        if port_vol == 0:
            return 0
        return -(port_ret - risk_free) / port_vol

    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
    bounds = [(0, 1) for _ in range(n)]
    x0 = np.ones(n) / n

    result = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    if result.success:
        weights_dict = dict(zip(available, result.x))
        sharpe = -result.fun
        return weights_dict, sharpe
    return None, None


def calculate_hedge_effectiveness(returns: pd.DataFrame, equity_symbol: str, hedge_symbols: List[str]) -> Dict:
    """Calculate hedge effectiveness metrics."""
    available_hedges = [s for s in hedge_symbols if s in returns.columns]
    if equity_symbol not in returns.columns or not available_hedges:
        return {}

    results = {}
    equity_ret = returns[equity_symbol]

    for hedge in available_hedges:
        hedge_ret = returns[hedge]
        common = equity_ret.notna() & hedge_ret.notna()

        if common.sum() < 30:
            continue

        eq = equity_ret[common]
        hd = hedge_ret[common]

        # Correlation
        corr = eq.corr(hd)

        # Optimal hedge ratio (beta from regression)
        slope, intercept, r_value, p_value, std_err = stats.linregress(hd, eq)

        # Variance reduction
        hedged_var = eq.var() - 2 * slope * eq.cov(hd) + slope**2 * hd.var()
        var_reduction = 1 - hedged_var / eq.var() if eq.var() > 0 else 0

        results[hedge] = {
            "correlation": round(corr, 4),
            "optimal_ratio": round(-slope, 4),  # Negative for hedge
            "r_squared": round(r_value**2, 4),
            "variance_reduction": round(var_reduction, 4),
            "p_value": round(p_value, 6),
        }

    return results


def analyze_correlation_stability(
    returns: pd.DataFrame,
    regime_series: pd.Series,
    symbols_a: List[str],
    symbols_b: List[str],
) -> pd.DataFrame:
    """Analyze correlation stability across regime transitions."""
    common_dates = returns.index.intersection(regime_series.index)
    ret = returns.loc[common_dates]
    reg = regime_series.loc[common_dates]

    results = []

    for sym_a in symbols_a:
        for sym_b in symbols_b:
            if sym_a not in ret.columns or sym_b not in ret.columns:
                continue

            for regime in ["POSITIVE", "NEGATIVE", "NEUTRAL"]:
                mask = reg == regime
                if mask.sum() < 20:
                    continue

                corr = ret.loc[mask, sym_a].corr(ret.loc[mask, sym_b])
                results.append(
                    {
                        "asset_a": sym_a,
                        "asset_b": sym_b,
                        "regime": regime,
                        "correlation": round(corr, 4) if pd.notna(corr) else None,
                        "obs": mask.sum(),
                    }
                )

    return pd.DataFrame(results)


def stress_test_portfolio(
    returns: pd.DataFrame,
    regime_series: pd.Series,
    weights: Dict[str, float],
    transition_window: int = 5,
) -> Dict:
    """Stress test portfolio around regime transitions."""
    common_dates = returns.index.intersection(regime_series.index)
    ret = returns.loc[common_dates]
    reg = regime_series.loc[common_dates]

    # Find transition dates
    transitions = reg != reg.shift(1)
    transition_dates = transitions[transitions].index

    # Calculate portfolio returns
    available = [s for s in weights.keys() if s in ret.columns]
    if not available:
        return {}

    w = np.array([weights[s] for s in available])
    port_ret = (ret[available] * w).sum(axis=1)

    # Analyze around transitions
    pre_transition = []
    post_transition = []

    for td in transition_dates[1:]:  # Skip first (no prior)
        idx = ret.index.get_loc(td)

        # Pre-transition window
        if idx >= transition_window:
            pre_ret = port_ret.iloc[idx - transition_window : idx]
            pre_transition.extend(pre_ret.values)

        # Post-transition window
        if idx + transition_window < len(port_ret):
            post_ret = port_ret.iloc[idx : idx + transition_window]
            post_transition.extend(post_ret.values)

    return {
        "transitions_analyzed": len(transition_dates) - 1,
        "pre_transition_mean": round(np.mean(pre_transition) * 252, 4) if pre_transition else None,
        "pre_transition_vol": (round(np.std(pre_transition) * np.sqrt(252), 4) if pre_transition else None),
        "post_transition_mean": (round(np.mean(post_transition) * 252, 4) if post_transition else None),
        "post_transition_vol": (round(np.std(post_transition) * np.sqrt(252), 4) if post_transition else None),
    }


def compare_dynamic_vs_static(
    returns: pd.DataFrame,
    regime_returns: Dict[str, pd.DataFrame],
    symbols: List[str],
) -> Dict:
    """Compare dynamic (regime-based) vs static allocation."""
    # Static: optimize on full period
    static_weights, static_sharpe = optimize_max_sharpe(returns, symbols)
    if static_weights is None:
        return {}

    # Dynamic: optimize per regime
    dynamic_weights = {}
    for regime, ret in regime_returns.items():
        w, sharpe = optimize_max_sharpe(ret, symbols)
        if w:
            dynamic_weights[regime] = w

    # Calculate performance
    available = [s for s in static_weights.keys() if s in returns.columns]
    static_w = np.array([static_weights[s] for s in available])
    static_port = (returns[available] * static_w).sum(axis=1)

    return {
        "static_weights": static_weights,
        "static_sharpe": round(static_sharpe, 4) if static_sharpe else None,
        "static_annual_return": round(static_port.mean() * 252, 4),
        "static_annual_vol": round(static_port.std() * np.sqrt(252), 4),
        "dynamic_weights": dynamic_weights,
    }


def _report_regime_allocation_section(regime_alloc: Dict) -> List[str]:
    """Generate regime-specific allocation section."""
    report = []
    report.append("## Optimal Allocations by Regime")
    report.append("")

    for regime, data in regime_alloc.items():
        if not data.get("weights"):
            continue
        report.append(f"### {regime} Gamma Regime")
        report.append("")
        report.append("| Asset | Weight | Asset Class |")
        report.append("|-------|--------|-------------|")

        for asset, weight in sorted(data["weights"].items(), key=lambda x: -x[1]):
            if weight > 0.01:
                report.append(f"| {asset} | {weight:.1%} | {data.get('classes', {}).get(asset, '-')} |")

        if data.get("sharpe"):
            report.append("")
            report.append(f"**Sharpe Ratio**: {data['sharpe']:.3f}")
        report.append("")

    return report


def _report_hedge_effectiveness_section(hedge_results: Dict, ref_symbol: str = "QQQ") -> List[str]:
    """Generate hedge effectiveness section."""
    report = []
    report.append(f"## Hedge Effectiveness (vs {ref_symbol})")
    report.append("")

    if not hedge_results:
        report.append("No hedge effectiveness data available.")
        report.append("")
        return report

    report.append("| Hedge Asset | Correlation | Optimal Ratio | Var Reduction | Significant |")
    report.append("|-------------|-------------|---------------|---------------|-------------|")

    for asset, metrics in hedge_results.items():
        sig = "Yes" if metrics.get("p_value", 1) < 0.05 else "No"
        report.append(
            f"| {asset} | {metrics['correlation']:.3f} | {metrics['optimal_ratio']:.3f} | "
            f"{metrics['variance_reduction']:.1%} | {sig} |"
        )

    report.append("")
    return report


def _report_correlation_stability_section(stability_df: pd.DataFrame) -> List[str]:
    """Generate correlation stability section."""
    report = []
    report.append("## Correlation Stability Across Regimes")
    report.append("")

    if stability_df.empty:
        report.append("Insufficient data for correlation stability analysis.")
        report.append("")
        return report

    # Pivot for better display
    pivot = stability_df.pivot_table(index=["asset_a", "asset_b"], columns="regime", values="correlation")

    report.append("| Pair | POSITIVE | NEUTRAL | NEGATIVE | Stability |")
    report.append("|------|----------|---------|----------|-----------|")

    for idx in pivot.index:
        row = pivot.loc[idx]
        values = [row.get(r, np.nan) for r in ["POSITIVE", "NEUTRAL", "NEGATIVE"]]
        valid = [v for v in values if pd.notna(v)]

        if len(valid) >= 2:
            stability = "Stable" if np.std(valid) < 0.2 else "Variable"
            report.append(
                f"| {idx[0]}-{idx[1]} | "
                + " | ".join([f"{v:.2f}" if pd.notna(v) else "-" for v in values])
                + f" | {stability} |"
            )

    report.append("")
    return report


def _report_dynamic_vs_static_section(comparison: Dict) -> List[str]:
    """Generate dynamic vs static comparison section."""
    report = []
    report.append("## Dynamic vs Static Allocation")
    report.append("")

    if not comparison:
        report.append("Insufficient data for comparison.")
        report.append("")
        return report

    report.append("### Static Allocation (Full Period)")
    report.append("")
    if comparison.get("static_weights"):
        report.append("| Asset | Weight |")
        report.append("|-------|--------|")
        for asset, weight in sorted(comparison["static_weights"].items(), key=lambda x: -x[1]):
            if weight > 0.01:
                report.append(f"| {asset} | {weight:.1%} |")
        report.append("")
        report.append(f"- **Sharpe Ratio**: {comparison.get('static_sharpe', 'N/A')}")
        report.append(f"- **Annual Return**: {comparison.get('static_annual_return', 'N/A'):.1%}")
        report.append(f"- **Annual Volatility**: {comparison.get('static_annual_vol', 'N/A'):.1%}")
        report.append("")

    report.append("### Dynamic Allocation (Regime-Based)")
    report.append("")
    for regime, weights in comparison.get("dynamic_weights", {}).items():
        report.append(f"**{regime} Regime**:")
        top_assets = sorted(weights.items(), key=lambda x: -x[1])[:3]
        report.append("  Top holdings: " + ", ".join([f"{a} ({w:.0%})" for a, w in top_assets if w > 0.05]))
    report.append("")

    return report


def _report_stress_test_section(stress_results: Dict) -> List[str]:
    """Generate stress test section."""
    report = []
    report.append("## Stress Test: Regime Transitions")
    report.append("")

    if not stress_results:
        report.append("Insufficient data for stress testing.")
        report.append("")
        return report

    report.append(f"**Transitions Analyzed**: {stress_results.get('transitions_analyzed', 0)}")
    report.append("")
    report.append("| Period | Annualized Return | Annualized Vol |")
    report.append("|--------|-------------------|----------------|")

    pre_ret = stress_results.get("pre_transition_mean")
    pre_vol = stress_results.get("pre_transition_vol")
    post_ret = stress_results.get("post_transition_mean")
    post_vol = stress_results.get("post_transition_vol")

    report.append(
        f"| Pre-Transition | {pre_ret:.1%} | {pre_vol:.1%} |" if pre_ret is not None else "| Pre-Transition | - | - |"
    )
    report.append(
        f"| Post-Transition | {post_ret:.1%} | {post_vol:.1%} |"
        if post_ret is not None
        else "| Post-Transition | - | - |"
    )

    report.append("")
    return report


def generate_report(
    regime_allocations: Dict,
    hedge_effectiveness: Dict,
    correlation_stability: pd.DataFrame,
    dynamic_vs_static: Dict,
    stress_test: Dict,
    hedge_ref_symbol: str = "QQQ",
) -> str:
    """Generate markdown report for hedge ratio optimization."""
    report = []
    report.append("# Hedge Ratio Optimization Analysis")
    report.append("")
    report.append("**Issue**: #500")
    report.append("**Purpose**: Determine optimal hedge ratios across GEX regimes")
    report.append("**Application**: gex-llm-patterns Paper 3 (cross-asset flows)")
    report.append("")

    report.append("## Executive Summary")
    report.append("")

    # Add sections
    report.extend(_report_regime_allocation_section(regime_allocations))
    report.extend(_report_hedge_effectiveness_section(hedge_effectiveness, hedge_ref_symbol))
    report.extend(_report_correlation_stability_section(correlation_stability))
    report.extend(_report_dynamic_vs_static_section(dynamic_vs_static))
    report.extend(_report_stress_test_section(stress_test))

    # Interpretation
    report.append("## Interpretation for Paper 3")
    report.append("")
    report.append("### Key Findings")
    report.append("")

    # Analyze hedge effectiveness
    if hedge_effectiveness:
        best_hedge = max(
            hedge_effectiveness.items(),
            key=lambda x: x[1].get("variance_reduction", 0),
        )
        report.append(f"1. **Best Hedge Asset**: {best_hedge[0]}")
        report.append(f"   - Variance Reduction: {best_hedge[1]['variance_reduction']:.1%}")
        report.append(f"   - Optimal Ratio: {best_hedge[1]['optimal_ratio']:.2f}")
        report.append("")

    report.append("### Implications")
    report.append("")
    report.append("1. **Regime-Aware Allocation**: Adjust hedge ratios based on GEX regime")
    report.append("2. **Transition Risk**: Monitor correlation stability during regime shifts")
    report.append("3. **Dynamic vs Static**: Compare regime-based vs fixed allocation performance")
    report.append("")
    report.append("---")
    report.append("")
    report.append("Generated by hedge_ratio_optimization.py")

    return "\n".join(report)


if __name__ == "__main__":
    print("=" * 70)
    print("HEDGE RATIO OPTIMIZATION ANALYSIS (#500)")
    print("=" * 70)

    # Load data
    df = load_price_data()
    print(f"Total records: {len(df):,}")
    print(f"Symbols: {df['symbol'].nunique()}")
    print(f"Date range: {df['trading_date'].min().date()} to {df['trading_date'].max().date()}")

    # Focus on 2020 for best cross-asset coverage
    df_2020 = df[df["trading_date"].dt.year == 2020]
    print(f"\n2020 data: {len(df_2020):,} records")

    # Calculate returns
    returns = calculate_returns(df_2020)
    print(f"Return series: {len(returns)} days, {len(returns.columns)} symbols")

    # Get regime series (use SPY or QQQ)
    if "SPY" in df_2020["symbol"].unique():
        regime_symbol = "SPY"
    else:
        regime_symbol = "QQQ"
    regime_series = get_regime_series(df_2020, regime_symbol)
    print(f"Regime reference: {regime_symbol}")

    # Split returns by regime
    regime_returns = calculate_regime_returns(returns, regime_series)
    for regime, ret in regime_returns.items():
        print(f"  {regime}: {len(ret)} days")

    # Define asset groups
    equities = ["SPY", "QQQ", "IWM"]
    bonds = ["TLT", "IEF", "LQD"]
    commodities = ["GLD", "SLV"]
    volatility = ["UVXY", "VXX"]
    all_assets = equities + bonds + commodities + volatility

    # 1. Optimal allocations by regime
    print("\n1. Calculating optimal allocations by regime...")
    regime_allocations = {}
    for regime, ret in regime_returns.items():
        weights, sharpe = optimize_max_sharpe(ret, all_assets)
        if weights:
            # Get asset classes
            classes = {}
            for sym in weights.keys():
                sym_class = df_2020[df_2020["symbol"] == sym]["asset_class"].iloc[0]
                classes[sym] = sym_class

            regime_allocations[regime] = {"weights": weights, "sharpe": sharpe, "classes": classes}
            top = sorted(weights.items(), key=lambda x: -x[1])[:3]
            print(f"  {regime}: Sharpe={sharpe:.3f}, Top: {', '.join([f'{a}({w:.0%})' for a,w in top])}")

    # 2. Hedge effectiveness (use QQQ since SPY data starts late)
    print("\n2. Calculating hedge effectiveness...")
    hedge_ref = "QQQ" if "QQQ" in returns.columns else "IWM"
    hedge_effectiveness = calculate_hedge_effectiveness(returns, hedge_ref, bonds + commodities + volatility)
    for hedge, metrics in hedge_effectiveness.items():
        print(
            f"  {hedge_ref} vs {hedge}: corr={metrics['correlation']:.3f}, var_red={metrics['variance_reduction']:.1%}"
        )

    # 3. Correlation stability
    print("\n3. Analyzing correlation stability across regimes...")
    correlation_stability = analyze_correlation_stability(returns, regime_series, equities, bonds + commodities)
    if not correlation_stability.empty:
        print(f"  {len(correlation_stability)} pair-regime observations")

    # 4. Dynamic vs static comparison
    print("\n4. Comparing dynamic vs static allocation...")
    dynamic_vs_static = compare_dynamic_vs_static(returns, regime_returns, all_assets)
    if dynamic_vs_static.get("static_sharpe"):
        print(f"  Static Sharpe: {dynamic_vs_static['static_sharpe']:.3f}")

    # 5. Stress test
    print("\n5. Stress testing around regime transitions...")
    if dynamic_vs_static.get("static_weights"):
        stress_test = stress_test_portfolio(returns, regime_series, dynamic_vs_static["static_weights"])
        print(f"  Transitions analyzed: {stress_test.get('transitions_analyzed', 0)}")
    else:
        stress_test = {}

    # Generate report
    report = generate_report(
        regime_allocations,
        hedge_effectiveness,
        correlation_stability,
        dynamic_vs_static,
        stress_test,
        hedge_ref_symbol=hedge_ref,
    )

    # Save report
    report_path = Path("docs/08_research/03_gex_research/hedge_ratio_optimization.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"\n[OK] Report saved: {report_path}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if regime_allocations:
        print("\nRegime-specific optimal allocations found")
        for regime, data in regime_allocations.items():
            if data.get("weights"):
                # Group by asset class
                by_class = {}
                for asset, weight in data["weights"].items():
                    ac = data.get("classes", {}).get(asset, "other")
                    by_class[ac] = by_class.get(ac, 0) + weight
                class_str = ", ".join([f"{c}:{w:.0%}" for c, w in sorted(by_class.items())])
                print(f"  {regime}: {class_str}")

    if hedge_effectiveness:
        best = max(hedge_effectiveness.items(), key=lambda x: x[1]["variance_reduction"])
        print(f"\nBest hedge for {hedge_ref}: {best[0]} (reduces variance by {best[1]['variance_reduction']:.1%})")

    print("\nKey takeaway:")
    print("  -> Use regime-aware hedge ratios for optimal risk management")
