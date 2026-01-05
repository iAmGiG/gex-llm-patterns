"""Volatility Spillover Analysis (#497)

Extends cross-asset correlation to answer:
1. Does VXX/UVXY GEX lead equity regime changes? (Granger causality)
2. How stable are cross-asset relationships over time? (Rolling correlations)
3. Can we identify early warning signals for regime transitions?
4. What is the spillover network structure?

This analysis feeds gex-llm-patterns Paper 3 (cross-asset flows).
"""

import sqlite3
import os
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DB_PATH = Path(".cache/options_historical.db")


# Asset definitions
VOLATILITY_ASSETS = ["UVXY", "VXX"]
EQUITY_ASSETS = ["SPY", "QQQ", "IWM"]
BOND_ASSETS = ["TLT", "IEF", "LQD"]
COMMODITY_ASSETS = ["GLD", "SLV"]

ALL_ASSETS = VOLATILITY_ASSETS + EQUITY_ASSETS + BOND_ASSETS + COMMODITY_ASSETS


def load_gex_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load GEX data for spillover analysis."""
    query = """
        SELECT symbol, trading_date, total_gex, net_call_gex, net_put_gex,
               regime, underlying_price, asset_class
        FROM options_daily_summary
        WHERE underlying_price IS NOT NULL
        ORDER BY symbol, trading_date
    """
    df = pd.read_sql_query(query, conn)
    df["trading_date"] = pd.to_datetime(df["trading_date"])

    # Regime as numeric
    regime_map = {"POSITIVE_GAMMA": 1, "NEUTRAL": 0, "NEGATIVE_GAMMA": -1}
    df["regime_numeric"] = df["regime"].map(regime_map)

    # Daily returns
    df["return"] = df.groupby("symbol")["underlying_price"].pct_change()

    return df


def granger_causality_test(df: pd.DataFrame, cause_symbol: str, effect_symbol: str, max_lag: int = 5) -> dict:
    """Test if cause_symbol GEX Granger-causes effect_symbol regime changes.

    Uses simple F-test approach:
    - H0: Lagged cause doesn't improve prediction of effect
    - H1: Lagged cause improves prediction
    """
    # Get aligned data
    cause_data = df[df["symbol"] == cause_symbol].set_index("trading_date")
    effect_data = df[df["symbol"] == effect_symbol].set_index("trading_date")

    common_dates = cause_data.index.intersection(effect_data.index)
    if len(common_dates) < 50:
        return None

    cause_gex = cause_data.loc[common_dates, "total_gex"]
    effect_regime = effect_data.loc[common_dates, "regime_numeric"]

    results = {"cause": cause_symbol, "effect": effect_symbol, "lags": {}}

    for lag in range(1, max_lag + 1):
        # Lag the cause variable
        cause_lagged = cause_gex.shift(lag)

        # Drop NaN
        valid = ~(cause_lagged.isna() | effect_regime.isna())
        y = effect_regime[valid].values
        x = cause_lagged[valid].values

        if len(y) < 30:
            continue

        # Simple linear regression F-test
        correlation, p_value = stats.pearsonr(x, y)

        # Also calculate predictive accuracy
        # Does sign of lagged GEX predict regime?
        cause_sign = np.sign(x)
        effect_sign = np.sign(y)
        agreement = (cause_sign == effect_sign).mean()

        results["lags"][lag] = {
            "correlation": round(correlation, 4),
            "p_value": round(p_value, 6),
            "significant": p_value < 0.05,
            "sign_agreement": round(agreement, 4),
        }

    # Find best lag
    if results["lags"]:
        best_lag = max(results["lags"].keys(), key=lambda lag: abs(results["lags"][lag]["correlation"]))
        results["best_lag"] = best_lag
        results["best_correlation"] = results["lags"][best_lag]["correlation"]
        results["best_p_value"] = results["lags"][best_lag]["p_value"]

    return results


def calculate_rolling_correlation(df: pd.DataFrame, symbol1: str, symbol2: str, window: int = 60) -> pd.DataFrame:
    """Calculate rolling correlation between two assets' GEX."""
    data1 = df[df["symbol"] == symbol1].set_index("trading_date")["total_gex"]
    data2 = df[df["symbol"] == symbol2].set_index("trading_date")["total_gex"]

    # Align on common dates
    common = data1.index.intersection(data2.index)
    data1 = data1.loc[common]
    data2 = data2.loc[common]

    # Rolling correlation
    rolling_corr = data1.rolling(window=window).corr(data2)

    result = pd.DataFrame(
        {
            "date": common,
            "rolling_correlation": rolling_corr.values,
            "symbol1": symbol1,
            "symbol2": symbol2,
        }
    )

    return result.dropna()


def analyze_regime_transitions(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Identify regime transitions and what preceded them."""
    sym_data = df[df["symbol"] == symbol].sort_values("trading_date").copy()

    # Identify transitions
    sym_data["prev_regime"] = sym_data["regime"].shift(1)
    sym_data["is_transition"] = sym_data["regime"] != sym_data["prev_regime"]

    transitions = sym_data[sym_data["is_transition"]].copy()
    transitions["transition_type"] = transitions["prev_regime"] + " -> " + transitions["regime"]

    return transitions[["trading_date", "symbol", "prev_regime", "regime", "transition_type"]]


def find_leading_indicators(df: pd.DataFrame, target_symbol: str, candidate_symbols: list, lookback: int = 5) -> dict:
    """Find which symbols' GEX changes precede target regime transitions."""
    # Get target transitions
    transitions = analyze_regime_transitions(df, target_symbol)

    if transitions.empty:
        return {}

    results = {}

    for candidate in candidate_symbols:
        if candidate == target_symbol:
            continue

        cand_data = df[df["symbol"] == candidate].set_index("trading_date")

        if cand_data.empty:
            continue

        # For each transition, check candidate's behavior before
        signals = []

        for _, transition in transitions.iterrows():
            trans_date = transition["trading_date"]

            # Look at candidate's GEX in days before transition
            lookback_start = trans_date - timedelta(days=lookback * 2)  # Account for weekends
            lookback_data = cand_data.loc[lookback_start:trans_date]

            if len(lookback_data) < 3:
                continue

            # Did candidate's GEX trend in same direction as transition?
            trans_direction = 1 if "POSITIVE" in transition["regime"] else -1
            gex_trend = lookback_data["total_gex"].diff().mean()
            gex_trend_sign = np.sign(gex_trend) if gex_trend != 0 else 0

            # Did candidate's regime change first?
            cand_regime_change = (lookback_data["regime"] != lookback_data["regime"].shift()).sum()

            signals.append(
                {
                    "transition_date": trans_date,
                    "transition_type": transition["transition_type"],
                    "candidate_gex_trend": gex_trend_sign,
                    "expected_direction": trans_direction,
                    "match": gex_trend_sign == trans_direction,
                    "candidate_regime_changes": cand_regime_change,
                }
            )

        if signals:
            signals_df = pd.DataFrame(signals)
            match_rate = signals_df["match"].mean()

            results[candidate] = {
                "transitions_analyzed": len(signals),
                "match_rate": round(match_rate, 3),
                "avg_regime_changes_before": round(signals_df["candidate_regime_changes"].mean(), 2),
                "is_leading_indicator": match_rate > 0.55,  # Better than random
            }

    return results


def calculate_spillover_network(df: pd.DataFrame, lag: int = 1) -> pd.DataFrame:
    """
    Calculate spillover network: which assets' GEX influences others?
    Returns correlation matrix with lagged relationships.
    """
    # Pivot to wide format
    pivot = df.pivot_table(index="trading_date", columns="symbol", values="total_gex", aggfunc="first")

    # Only use assets with sufficient data
    valid_symbols = pivot.columns[pivot.notna().sum() > 100].tolist()
    pivot = pivot[valid_symbols]

    # Calculate lagged correlations
    network = pd.DataFrame(index=valid_symbols, columns=valid_symbols, dtype=float)

    for cause in valid_symbols:
        cause_lagged = pivot[cause].shift(lag)
        for effect in valid_symbols:
            valid = ~(cause_lagged.isna() | pivot[effect].isna())
            if valid.sum() > 30:
                corr, _ = stats.pearsonr(cause_lagged[valid], pivot[effect][valid])
                network.loc[cause, effect] = round(corr, 3)

    return network


def _report_granger_section(granger_results: list) -> list:
    """Generate Granger causality section of report."""
    report = []
    report.append("## Granger Causality Tests")
    report.append("")
    report.append("Does Asset A's GEX predict Asset B's regime changes?")
    report.append("")
    report.append("| Cause | Effect | Best Lag | Correlation | P-Value | Significant |")
    report.append("|-------|--------|----------|-------------|---------|-------------|")

    for r in granger_results:
        if r and "best_lag" in r:
            sig = "Yes" if r.get("best_p_value", 1) < 0.05 else "No"
            report.append(
                f"| {r['cause']} | {r['effect']} | {r['best_lag']} days | "
                f"{r['best_correlation']:.3f} | {r['best_p_value']:.4f} | {sig} |"
            )
    report.append("")
    return report


def _report_rolling_corr_section(rolling_corrs: list) -> list:
    """Generate rolling correlation section of report."""
    report = []
    if not rolling_corrs:
        return report

    report.append("## Correlation Stability Over Time")
    report.append("")
    report.append("60-day rolling correlations between volatility and equity GEX:")
    report.append("")

    for rc in rolling_corrs:
        if not rc.empty:
            sym1, sym2 = rc["symbol1"].iloc[0], rc["symbol2"].iloc[0]
            mean_corr = rc["rolling_correlation"].mean()
            std_corr = rc["rolling_correlation"].std()

            report.append(f"### {sym1} vs {sym2}")
            report.append("")
            report.append(f"- Mean: {mean_corr:.3f}")
            report.append(f"- Std Dev: {std_corr:.3f}")
            report.append(f"- Range: [{rc['rolling_correlation'].min():.3f}, {rc['rolling_correlation'].max():.3f}]")
            report.append(f"- Stability: {'Stable' if std_corr < 0.2 else 'Variable'}")
            report.append("")
    return report


def _report_leading_indicators_section(leading_indicators: dict) -> list:
    """Generate leading indicators section of report."""
    report = []
    if not leading_indicators:
        return report

    report.append("## Leading Indicators for SPY Regime Transitions")
    report.append("")
    report.append("Which assets' GEX trends predict SPY regime changes?")
    report.append("")
    report.append("| Asset | Transitions | Match Rate | Leading? |")
    report.append("|-------|-------------|------------|----------|")

    for asset, info in sorted(leading_indicators.items(), key=lambda x: -x[1]["match_rate"]):
        leading = "Yes" if info["is_leading_indicator"] else "No"
        report.append(f"| {asset} | {info['transitions_analyzed']} | {info['match_rate']:.1%} | {leading} |")
    report.append("")
    return report


def _report_spillover_network_section(spillover_network: pd.DataFrame) -> list:
    """Generate spillover network section of report."""
    report = []
    if spillover_network.empty:
        return report

    report.append("## 1-Day Lagged Spillover Network")
    report.append("")
    report.append("Correlation of Asset A's GEX (t-1) with Asset B's GEX (t):")
    report.append("")

    key_assets = ["UVXY", "VXX", "SPY", "QQQ", "IWM", "TLT", "GLD"]
    key_assets = [a for a in key_assets if a in spillover_network.columns]

    if key_assets:
        report.append("| From \\ To | " + " | ".join(key_assets) + " |")
        report.append("|---|" + "|".join(["---"] * len(key_assets)) + "|")

        for asset in key_assets:
            if asset in spillover_network.index:
                row_vals = [
                    (f"{spillover_network.loc[asset, a]:.2f}" if pd.notna(spillover_network.loc[asset, a]) else "-")
                    for a in key_assets
                ]
                report.append(f"| {asset} | " + " | ".join(row_vals) + " |")
        report.append("")
    return report


def generate_spillover_report(
    granger_results: list,
    rolling_corrs: list,
    leading_indicators: dict,
    spillover_network: pd.DataFrame,
) -> str:
    """Generate markdown report for volatility spillover analysis."""
    report = []
    report.append("# Volatility Spillover Analysis")
    report.append("")
    report.append("**Issue**: #497")
    report.append("**Purpose**: Identify cross-asset GEX regime leading indicators")
    report.append("**Application**: gex-llm-patterns Paper 3 (cross-asset flows)")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    significant_granger = [r for r in granger_results if r and r.get("best_p_value", 1) < 0.05]
    if significant_granger:
        report.append("### Statistically Significant Lead-Lag Relationships")
        report.append("")
        for r in significant_granger:
            report.append(
                f"- **{r['cause']} → {r['effect']}**: "
                f"lag={r['best_lag']} days, r={r['best_correlation']:.3f}, p={r['best_p_value']:.4f}"
            )
        report.append("")
    else:
        report.append("No statistically significant Granger causality relationships found at p<0.05.")
        report.append("")

    # Add sections from helper functions
    report.extend(_report_granger_section(granger_results))
    report.extend(_report_rolling_corr_section(rolling_corrs))
    report.extend(_report_leading_indicators_section(leading_indicators))
    report.extend(_report_spillover_network_section(spillover_network))

    # Interpretation
    report.append("## Interpretation for Paper 3")
    report.append("")
    report.append("### Key Findings")
    report.append("")

    uvxy_granger = next((r for r in granger_results if r and r.get("cause") == "UVXY"), None)
    if uvxy_granger:
        report.append("1. **UVXY as Leading Indicator**:")
        if uvxy_granger.get("best_p_value", 1) < 0.05:
            report.append(
                f"   - UVXY GEX leads SPY regime by {uvxy_granger['best_lag']} day(s) "
                f"(r={uvxy_granger['best_correlation']:.3f}, p={uvxy_granger['best_p_value']:.4f})"
            )
        report.append("")

    report.append("### Implications")
    report.append("")
    report.append("1. **Risk Management**: Monitor volatility GEX for early warning of equity regime shifts")
    report.append("2. **Trading Strategy**: Use UVXY/VXX regime changes as filter for equity positions")
    report.append("3. **Paper 3 Direction**: Focus on volatility→equity spillover channel for cross-asset analysis")
    report.append("")
    report.append("---")
    report.append("")
    report.append("Generated by volatility_spillover_analysis.py")

    return "\n".join(report)


def main():
    """Main entry point."""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    try:
        print("=" * 70)
        print("VOLATILITY SPILLOVER ANALYSIS (#497)")
        print("=" * 70)

        # Load data
        df = load_gex_data(conn)
        print(f"Total records: {len(df):,}")
        print(f"Symbols: {df['symbol'].nunique()}")
        print(f"Date range: {df['trading_date'].min().date()} to {df['trading_date'].max().date()}")

        # 1. Granger Causality Tests
        print("\n1. Running Granger causality tests...")
        granger_pairs = [
            ("UVXY", "SPY"),
            ("VXX", "SPY"),
            ("UVXY", "QQQ"),
            ("SPY", "TLT"),
            ("TLT", "SPY"),
            ("GLD", "SPY"),
            ("SPY", "IWM"),
            ("UVXY", "IWM"),
        ]

        granger_results = []
        for cause, effect in granger_pairs:
            if cause in df["symbol"].unique() and effect in df["symbol"].unique():
                result = granger_causality_test(df, cause, effect, max_lag=5)
                if result:
                    granger_results.append(result)
                    sig = "*" if result.get("best_p_value", 1) < 0.05 else ""
                    print(
                        f"  {cause} -> {effect}: lag={result.get('best_lag', '?')}, "
                        f"r={result.get('best_correlation', 0):.3f}{sig}"
                    )

        # 2. Rolling Correlations
        print("\n2. Calculating rolling correlations...")
        rolling_pairs = [("UVXY", "SPY"), ("VXX", "SPY"), ("UVXY", "QQQ")]

        rolling_corrs = []
        for sym1, sym2 in rolling_pairs:
            if sym1 in df["symbol"].unique() and sym2 in df["symbol"].unique():
                rc = calculate_rolling_correlation(df, sym1, sym2, window=60)
                if not rc.empty:
                    rolling_corrs.append(rc)
                    mean_c = rc["rolling_correlation"].mean()
                    std_c = rc["rolling_correlation"].std()
                    print(f"  {sym1} vs {sym2}: mean={mean_c:.3f}, std={std_c:.3f}")

        # 3. Leading Indicators
        print("\n3. Finding leading indicators for SPY regime transitions...")
        leading_indicators = find_leading_indicators(df, "SPY", ["UVXY", "VXX", "QQQ", "IWM", "TLT", "GLD"])
        for asset, info in sorted(leading_indicators.items(), key=lambda x: -x[1]["match_rate"]):
            status = "LEADING" if info["is_leading_indicator"] else ""
            print(f"  {asset}: {info['match_rate']:.1%} match rate {status}")

        # 4. Spillover Network
        print("\n4. Building spillover network...")
        spillover_network = calculate_spillover_network(df, lag=1)

        # Generate report
        report = generate_spillover_report(granger_results, rolling_corrs, leading_indicators, spillover_network)

        # Save report
        report_path = Path("docs/08_research/03_gex_research/volatility_spillover_analysis.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"\n[OK] Report saved: {report_path}")

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        significant = [r for r in granger_results if r and r.get("best_p_value", 1) < 0.05]
        print(f"Significant Granger relationships: {len(significant)}/{len(granger_results)}")

        leading = [a for a, i in leading_indicators.items() if i["is_leading_indicator"]]
        print(f"Leading indicators identified: {leading if leading else 'None'}")

        print("\nKey takeaway for Paper 3:")
        if "UVXY" in leading:
            print("  -> UVXY GEX shows promise as early warning signal for equity regimes")
        else:
            print("  -> Cross-asset relationships exist but may not be reliable predictors")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
