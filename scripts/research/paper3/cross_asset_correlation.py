"""Cross-Asset Regime Correlation Analysis (#496)

Analyze GEX regime correlations across asset classes:
- Equities (SPY, QQQ, IWM)
- Volatility (UVXY, VXX)
- Bonds (TLT, IEF, LQD)
- Commodities (GLD, SLV)

Research questions:
1. Do bond GEX regimes correlate with equity GEX regimes?
2. Does commodity GEX provide diversification signal?
3. Can cross-asset regime divergence predict rotations?
"""

import sqlite3
import os
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

DB_PATH = Path(".cache/options_historical.db")

# Asset class groupings
ASSET_GROUPS = {
    "equity": ["SPY", "QQQ", "IWM"],
    "volatility": ["UVXY", "VXX"],
    "bond": ["TLT", "IEF", "LQD"],
    "commodity": ["GLD", "SLV"],
}


def get_regime_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Get regime data for all symbols with sufficient coverage."""
    query = """
        SELECT symbol, trading_date, regime, underlying_price, asset_class
        FROM options_daily_summary
        WHERE underlying_price IS NOT NULL
        ORDER BY symbol, trading_date
    """
    df = pd.read_sql_query(query, conn)
    df["trading_date"] = pd.to_datetime(df["trading_date"])

    # Convert regime to numeric for correlation
    regime_map = {"POSITIVE_GAMMA": 1, "NEUTRAL": 0, "NEGATIVE_GAMMA": -1}
    df["regime_numeric"] = df["regime"].map(regime_map)

    return df


def calculate_regime_correlation(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate regime correlation matrix across symbols."""
    # Pivot to get symbols as columns
    pivot = df.pivot_table(index="trading_date", columns="symbol", values="regime_numeric", aggfunc="first")

    # Calculate correlation
    corr = pivot.corr()

    return corr


def calculate_cross_asset_metrics(df: pd.DataFrame) -> Dict:
    """Calculate cross-asset regime metrics."""
    results = {}

    # Group by asset class
    for asset_class, symbols in ASSET_GROUPS.items():
        available_symbols = [s for s in symbols if s in df["symbol"].unique()]
        if not available_symbols:
            continue

        class_data = df[df["symbol"].isin(available_symbols)]

        # Regime distribution
        regime_dist = class_data["regime"].value_counts(normalize=True)

        # Average regime persistence (days in same regime)
        regime_changes = class_data.groupby("symbol").apply(lambda x: (x["regime"] != x["regime"].shift()).sum())
        avg_changes = regime_changes.mean()
        total_days = class_data.groupby("symbol").size().mean()
        persistence = total_days / avg_changes if avg_changes > 0 else total_days

        results[asset_class] = {
            "symbols": available_symbols,
            "total_days": int(class_data.groupby("symbol").size().mean()),
            "positive_gamma_pct": round(regime_dist.get("POSITIVE_GAMMA", 0) * 100, 1),
            "negative_gamma_pct": round(regime_dist.get("NEGATIVE_GAMMA", 0) * 100, 1),
            "neutral_pct": round(regime_dist.get("NEUTRAL", 0) * 100, 1),
            "avg_regime_persistence_days": round(persistence, 1),
        }

    return results


def calculate_lead_lag_correlation(df: pd.DataFrame, lead_asset: str, lag_asset: str, max_lag: int = 5) -> Dict:
    """Calculate lead-lag correlation between two assets."""
    # Get regime data for both
    lead_data = df[df["symbol"] == lead_asset].set_index("trading_date")["regime_numeric"]
    lag_data = df[df["symbol"] == lag_asset].set_index("trading_date")["regime_numeric"]

    # Align on common dates
    common_dates = lead_data.index.intersection(lag_data.index)
    if len(common_dates) < 30:
        return None

    lead_data = lead_data.loc[common_dates]
    lag_data = lag_data.loc[common_dates]

    # Calculate correlations at different lags
    correlations = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            # Lead asset leads
            shifted = lead_data.shift(-lag)
        else:
            # Lag asset leads
            shifted = lag_data.shift(lag)

        valid = ~(lead_data.isna() | shifted.isna())
        if valid.sum() > 30:
            corr = lead_data[valid].corr(shifted[valid])
            correlations[lag] = round(corr, 3)

    # Find optimal lag
    if correlations:
        optimal_lag = max(correlations, key=lambda x: abs(correlations[x]))
        return {
            "lead_asset": lead_asset,
            "lag_asset": lag_asset,
            "correlations": correlations,
            "optimal_lag": optimal_lag,
            "max_correlation": correlations[optimal_lag],
        }

    return None


def generate_report(corr_matrix: pd.DataFrame, asset_metrics: Dict, lead_lag_results: List[Dict]) -> str:
    """Generate markdown report."""
    report = []
    report.append("# Cross-Asset GEX Regime Correlation Analysis")
    report.append("")
    report.append("## Executive Summary")
    report.append("")

    # Key findings placeholder
    report.append("**Research Questions:**")
    report.append("1. Do bond GEX regimes correlate with equity GEX regimes?")
    report.append("2. Does commodity GEX provide diversification signal?")
    report.append("3. Can cross-asset regime divergence predict rotations?")
    report.append("")

    # Asset class metrics
    report.append("## Regime Distribution by Asset Class")
    report.append("")
    report.append("| Asset Class | Symbols | Days | Positive GEX | Negative GEX | Neutral | Persistence |")
    report.append("|-------------|---------|------|--------------|--------------|---------|-------------|")

    for asset_class, metrics in asset_metrics.items():
        report.append(
            f"| {asset_class} | {', '.join(metrics['symbols'])} | {metrics['total_days']} | "
            f"{metrics['positive_gamma_pct']}% | {metrics['negative_gamma_pct']}% | "
            f"{metrics['neutral_pct']}% | {metrics['avg_regime_persistence_days']} days |"
        )

    report.append("")

    # Correlation matrix
    if not corr_matrix.empty:
        report.append("## Regime Correlation Matrix")
        report.append("")
        report.append("Correlation of GEX regime states across symbols:")
        report.append("")

        # Format as table
        symbols = corr_matrix.columns.tolist()
        header = "| | " + " | ".join(symbols) + " |"
        separator = "|---|" + "|".join(["---"] * len(symbols)) + "|"
        report.append(header)
        report.append(separator)

        for symbol in symbols:
            row = f"| {symbol} | " + " | ".join([f"{corr_matrix.loc[symbol, s]:.2f}" for s in symbols]) + " |"
            report.append(row)

        report.append("")

    # Lead-lag analysis
    if lead_lag_results:
        report.append("## Lead-Lag Analysis")
        report.append("")
        report.append("Does one asset class's GEX regime lead another?")
        report.append("")
        report.append("| Lead Asset | Lag Asset | Optimal Lag | Max Correlation |")
        report.append("|------------|-----------|-------------|-----------------|")

        for result in lead_lag_results:
            if result:
                lag_str = f"{result['optimal_lag']} days" if result["optimal_lag"] != 0 else "Same day"
                report.append(
                    f"| {result['lead_asset']} -> {result['lag_asset']} | "
                    f"{lag_str} | {result['max_correlation']:.3f} |"
                )

        report.append("")

    # Interpretation
    report.append("## Interpretation")
    report.append("")

    # Check for equity-volatility relationship
    if "equity" in asset_metrics and "volatility" in asset_metrics:
        report.append("### Equity vs Volatility")
        report.append("")
        equity_neg = asset_metrics["equity"].get("negative_gamma_pct", 0)
        vol_neg = asset_metrics["volatility"].get("negative_gamma_pct", 0)
        if vol_neg > equity_neg:
            report.append(f"Volatility instruments spend more time in negative gamma ({vol_neg}% vs {equity_neg}%).")
            report.append("This is expected - volatility products tend to have more extreme positioning.")
        report.append("")

    # Check for diversification
    report.append("### Diversification Potential")
    report.append("")

    if not corr_matrix.empty:
        # Find lowest correlations
        equity_syms = ASSET_GROUPS.get("equity", [])
        other_syms = [s for group in ["bond", "commodity"] for s in ASSET_GROUPS.get(group, [])]

        low_corr_pairs = []
        for eq in equity_syms:
            for other in other_syms:
                if eq in corr_matrix.columns and other in corr_matrix.columns:
                    corr = corr_matrix.loc[eq, other]
                    if abs(corr) < 0.3:
                        low_corr_pairs.append((eq, other, corr))

        if low_corr_pairs:
            report.append("Low correlation pairs (potential diversification):")
            for eq, other, corr in low_corr_pairs:
                report.append(f"- {eq} vs {other}: {corr:.2f}")
        else:
            report.append("No strong diversification signals found between equity and other asset classes.")

    return "\n".join(report)


def main():
    """Main entry point."""
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    try:
        print("=" * 70)
        print("CROSS-ASSET GEX REGIME CORRELATION (#496)")
        print("=" * 70)

        # Get regime data
        df = get_regime_data(conn)
        print(f"Total records: {len(df):,}")
        print(f"Symbols: {df['symbol'].nunique()}")
        print(f"Date range: {df['trading_date'].min().date()} to {df['trading_date'].max().date()}")

        # Calculate correlation matrix
        print("\nCalculating regime correlations...")
        corr_matrix = calculate_regime_correlation(df)

        # Calculate asset class metrics
        print("Calculating asset class metrics...")
        asset_metrics = calculate_cross_asset_metrics(df)

        # Lead-lag analysis
        print("Running lead-lag analysis...")
        lead_lag_pairs = [
            ("UVXY", "SPY"),  # Does volatility GEX lead equity?
            ("SPY", "TLT"),  # Does equity GEX lead bonds?
            ("GLD", "SPY"),  # Does commodity GEX lead equity?
            ("SPY", "IWM"),  # Does large cap lead small cap?
        ]

        lead_lag_results = []
        for lead, lag in lead_lag_pairs:
            if lead in df["symbol"].unique() and lag in df["symbol"].unique():
                result = calculate_lead_lag_correlation(df, lead, lag)
                if result:
                    lead_lag_results.append(result)
                    print(f"  {lead} -> {lag}: lag={result['optimal_lag']}, corr={result['max_correlation']:.3f}")

        # Generate report
        report = generate_report(corr_matrix, asset_metrics, lead_lag_results)

        # Save report
        report_path = Path("docs/08_research/03_gex_research/cross_asset_correlation.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"\n[OK] Report saved: {report_path}")

        # Print summary
        print("\n" + "=" * 70)
        print("ASSET CLASS SUMMARY")
        print("=" * 70)
        for asset_class, metrics in asset_metrics.items():
            print(f"\n{asset_class.upper()}:")
            print(f"  Symbols: {', '.join(metrics['symbols'])}")
            print(f"  Positive GEX: {metrics['positive_gamma_pct']}%")
            print(f"  Negative GEX: {metrics['negative_gamma_pct']}%")
            print(f"  Regime persistence: {metrics['avg_regime_persistence_days']} days")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
