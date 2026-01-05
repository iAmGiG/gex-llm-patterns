#!/usr/bin/env python3
"""
Issue #141: Non-Detection Day Analysis
Paper #1 MC Review Defense - Signal Sensitivity vs Base Rate Guessing

Analyzes the 74 non-detection days (30.6%) to prove LLM has signal sensitivity.
Tests 7 hypotheses (H1-H7) comparing detection vs non-detection characteristics.

Author: Research Team
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/141
"""

import os
import sqlite3
import sys

# Visualization imports (deferred to separate script)
# import matplotlib.pyplot as plt
# import seaborn as sns
# import calendar
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def calculate_gini_coefficient(values):
    """Calculate Gini coefficient for concentration measurement.

    Higher Gini (closer to 1) = more concentrated
    Lower Gini (closer to 0) = more dispersed/fragmented

    Args:
        values: Array of positive values (e.g., absolute gamma per strike)

    Returns:
        float: Gini coefficient [0, 1]
    """
    values = np.abs(values)  # Ensure positive
    values = values[values > 0]  # Remove zeros

    if len(values) == 0:
        return np.nan

    sorted_values = np.sort(values)
    n = len(sorted_values)

    # Gini formula
    gini = (2 * np.sum((n - np.arange(1, n + 1) + 0.5) * sorted_values)) / (n * np.sum(sorted_values)) - 1

    return gini


def test_hypothesis(detected_values, not_detected_values, hypothesis_name):
    """Statistical comparison with t-test and effect size.

    Args:
        detected_values: Values for detection days
        not_detected_values: Values for non-detection days
        hypothesis_name: Name of hypothesis being tested

    Returns:
        dict: Statistical test results
    """
    # Remove NaN values
    detected_clean = detected_values.dropna()
    not_detected_clean = not_detected_values.dropna()

    # Check if we have enough data
    if len(detected_clean) < 2 or len(not_detected_clean) < 2:
        return {
            "hypothesis": hypothesis_name,
            "detected_mean": np.nan,
            "detected_std": np.nan,
            "not_detected_mean": np.nan,
            "not_detected_std": np.nan,
            "t_statistic": np.nan,
            "p_value": np.nan,
            "cohen_d": np.nan,
            "significant": False,
            "effect_size": "insufficient_data",
            "n_detected": len(detected_clean),
            "n_not_detected": len(not_detected_clean),
        }

    # T-test
    t_stat, p_val = stats.ttest_ind(detected_clean, not_detected_clean)

    # Cohen's d effect size
    pooled_std = np.sqrt((detected_clean.std() ** 2 + not_detected_clean.std() ** 2) / 2)
    cohen_d = (detected_clean.mean() - not_detected_clean.mean()) / pooled_std if pooled_std > 0 else 0

    # Effect size category
    abs_d = abs(cohen_d)
    if abs_d > 0.8:
        effect_category = "large"
    elif abs_d > 0.5:
        effect_category = "medium"
    elif abs_d > 0.2:
        effect_category = "small"
    else:
        effect_category = "negligible"

    result = {
        "hypothesis": hypothesis_name,
        "detected_mean": detected_clean.mean(),
        "detected_std": detected_clean.std(),
        "not_detected_mean": not_detected_clean.mean(),
        "not_detected_std": not_detected_clean.std(),
        "t_statistic": t_stat,
        "p_value": p_val,
        "cohen_d": cohen_d,
        "significant": p_val < 0.05,
        "effect_size": effect_category,
        "n_detected": len(detected_clean),
        "n_not_detected": len(not_detected_clean),
    }

    return result


def extract_database_data(db_path, start_date="2024-01-02", end_date="2024-12-31"):
    """Extract strike-level and daily metrics from consolidated database.

    Args:
        db_path: Path to consolidated_historical.db
        start_date: Start date for analysis
        end_date: End date for analysis

    Returns:
        tuple: (strike_gex_df, daily_metrics_df)
    """
    conn = sqlite3.connect(db_path)

    print(f"Extracting data from {db_path}...")

    # Query 1: Strike-level GEX distribution
    strike_query = """
    SELECT
        date,
        strike,
        net_gex,
        distance_from_spot,
        ABS(net_gex) as abs_gex
    FROM strike_gex_details
    WHERE date BETWEEN ? AND ?
      AND symbol = 'SPY'
    ORDER BY date, strike
    """

    strike_df = pd.read_sql_query(strike_query, conn, params=(start_date, end_date))
    print(f"  Loaded {len(strike_df):,} strike-level records")

    # Query 2: Daily aggregates (includes put/call breakdown)
    daily_query = """
    SELECT
        date,
        spot_price,
        total_gex,
        net_call_gex,
        net_put_gex,
        gamma_flip_point,
        flip_ratio,
        gex_regime,
        data_quality_score,
        options_count
    FROM daily_gex_metrics
    WHERE date BETWEEN ? AND ?
      AND symbol = 'SPY'
    ORDER BY date
    """

    daily_df = pd.read_sql_query(daily_query, conn, params=(start_date, end_date))
    print(f"  Loaded {len(daily_df):,} daily aggregate records")

    conn.close()

    return strike_df, daily_df


def main():
    """Main analysis workflow for Issue #141."""

    print("=" * 80)
    print("Issue #141: Non-Detection Day Analysis")
    print("Paper #1 MC Review Defense - Signal Sensitivity Proof")
    print("=" * 80)
    print()

    # Paths
    db_path = project_root / ".cache" / "consolidated_historical.db"
    csv_path = project_root / "reports" / "statistical_validation" / "gamma_positioning_timeseries_2024.csv"
    output_dir = project_root / "docs" / "papers" / "paper1" / "analysis"
    figures_dir = project_root / "docs" / "papers" / "paper1" / "figures"

    output_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Load existing CSV data (detection status)
    print("Step 1: Loading validation results...")
    df = pd.read_csv(csv_path)
    print(f"  Total days: {len(df)}")
    print(f"  Detected: {df['detected'].sum()} ({df['detected'].sum()/len(df)*100:.1f}%)")
    print(f"  Not detected: {(~df['detected']).sum()} ({(~df['detected']).sum()/len(df)*100:.1f}%)")
    print()

    # Step 2: Extract database data
    print("Step 2: Extracting database metrics...")
    strike_df, daily_df = extract_database_data(db_path)
    print()

    # Step 3: Calculate derived metrics
    print("Step 3: Calculating derived metrics...")

    # 3A: GEX Concentration (Gini coefficient per day)
    print("  Calculating GEX concentration (Gini coefficient)...")
    gex_concentration = strike_df.groupby("date")["abs_gex"].apply(calculate_gini_coefficient)
    gex_concentration_df = pd.DataFrame(
        {"date": gex_concentration.index, "gex_concentration": gex_concentration.values}
    )

    # 3B: Put-Call Ratio
    print("  Calculating put-call ratio...")
    daily_df["put_call_ratio"] = abs(daily_df["net_put_gex"]) / abs(daily_df["net_call_gex"])

    # 3C: Strike concentration (number of strikes with >5% of total gamma)
    print("  Calculating strike concentration metrics...")
    strike_concentration = []
    for date, group in strike_df.groupby("date"):
        total_gex = group["abs_gex"].sum()
        if total_gex > 0:
            group["pct_of_total"] = group["abs_gex"] / total_gex
            n_concentrated = (group["pct_of_total"] > 0.05).sum()
        else:
            n_concentrated = 0
        strike_concentration.append({"date": date, "n_concentrated_strikes": n_concentrated})

    strike_conc_df = pd.DataFrame(strike_concentration)

    # Step 4: Merge all metrics
    print("  Merging all metrics...")
    df = df.merge(gex_concentration_df, on="date", how="left")
    df = df.merge(
        daily_df[["date", "net_call_gex", "net_put_gex", "put_call_ratio", "data_quality_score", "options_count"]],
        on="date",
        how="left",
    )
    df = df.merge(strike_conc_df, on="date", how="left")

    print()

    # Step 5: Split by detection status
    print("Step 4: Splitting by detection status...")
    detected = df[df["detected"] == True].copy()
    not_detected = df[df["detected"] == False].copy()
    print(f"  Detection days: {len(detected)}")
    print(f"  Non-detection days: {len(not_detected)}")
    print()

    # Step 6: Test all hypotheses
    print("Step 5: Testing hypotheses...")
    results = []

    # H1: GEX Magnitude (already tested, but rerun for completeness)
    print("  H1: GEX Magnitude...")
    results.append(
        test_hypothesis(abs(detected["net_gex"]), abs(not_detected["net_gex"]), "H1: GEX Magnitude (Signal Strength)")
    )

    # H2: Realized Volatility (signal noise)
    print("  H2: Realized Volatility...")
    results.append(
        test_hypothesis(
            detected["realized_vol_t1"], not_detected["realized_vol_t1"], "H2: Realized Volatility T+1 (Signal Noise)"
        )
    )

    # H3: Rolling Volatility (market context)
    print("  H3: Rolling Volatility...")
    results.append(
        test_hypothesis(
            detected["realized_vol_rolling_5d"],
            not_detected["realized_vol_rolling_5d"],
            "H3: Rolling 5D Volatility (Market Regime)",
        )
    )

    # H5: GEX Concentration (fragmentation)
    print("  H5: GEX Concentration...")
    results.append(
        test_hypothesis(
            detected["gex_concentration"],
            not_detected["gex_concentration"],
            "H5: GEX Concentration (Gini - Fragmentation)",
        )
    )

    # H6: Put-Call Balance (signal conflict)
    print("  H6: Put-Call Ratio...")
    results.append(
        test_hypothesis(
            detected["put_call_ratio"], not_detected["put_call_ratio"], "H6: Put-Call Ratio (Signal Conflict)"
        )
    )

    # H7A: Data Quality Score
    print("  H7A: Data Quality...")
    results.append(
        test_hypothesis(
            detected["data_quality_score"],
            not_detected["data_quality_score"],
            "H7A: Data Quality Score (Signal Reliability)",
        )
    )

    # H7B: Options Count (market depth)
    print("  H7B: Options Count...")
    results.append(
        test_hypothesis(detected["options_count"], not_detected["options_count"], "H7B: Options Count (Market Depth)")
    )

    # H7C: Strike Concentration
    print("  H7C: Strike Concentration...")
    results.append(
        test_hypothesis(
            detected["n_concentrated_strikes"],
            not_detected["n_concentrated_strikes"],
            "H7C: Concentrated Strikes (>5% gamma each)",
        )
    )

    print()

    # Step 7: Create results summary
    print("Step 6: Creating results summary...")
    results_df = pd.DataFrame(results)

    # Display results
    print()
    print("=" * 80)
    print("HYPOTHESIS TEST RESULTS")
    print("=" * 80)
    print()
    print(
        results_df[
            ["hypothesis", "detected_mean", "not_detected_mean", "p_value", "cohen_d", "effect_size", "significant"]
        ].to_string(index=False)
    )
    print()

    # Identify significant factors
    significant = results_df[results_df["significant"] == True].copy()
    if len(significant) > 0:
        print(f"SIGNIFICANT FACTORS (p < 0.05): {len(significant)}")
        print()
        for _, row in significant.iterrows():
            direction = "higher" if row["detected_mean"] > row["not_detected_mean"] else "lower"
            print(f"  ✓ {row['hypothesis']}")
            print(f"    Detection days: {row['detected_mean']:.4f} ± {row['detected_std']:.4f}")
            print(f"    Non-detection days: {row['not_detected_mean']:.4f} ± {row['not_detected_std']:.4f}")
            print(f"    Effect: {direction} for detected days (d={row['cohen_d']:.3f}, p={row['p_value']:.4f})")
            print()
    else:
        print("⚠️  NO SIGNIFICANT FACTORS FOUND")
        print()

    # Step 8: Save results
    print("Step 7: Saving results...")
    results_path = output_dir / "issue_141_hypothesis_tests.csv"
    results_df.to_csv(results_path, index=False)
    print(f"  Saved: {results_path}")

    # Save enhanced dataset with all metrics
    enhanced_path = output_dir / "issue_141_enhanced_dataset.csv"
    df.to_csv(enhanced_path, index=False)
    print(f"  Saved: {enhanced_path}")
    print()

    # Step 9: Generate visualizations (next phase)
    print("Step 8: Generating visualizations...")
    print("  (Creating calendar heatmap, concentration distribution, multi-factor plots)")
    print("  → Run visualization script separately")
    print()

    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print(f"Next steps:")
    print(f"  1. Review hypothesis test results: {results_path}")
    print(f"  2. Generate visualizations (3 figures)")
    print(f"  3. Write analysis report")
    print(f"  4. Update GitHub Issue #141")
    print()

    return results_df, df


if __name__ == "__main__":
    results_df, enhanced_df = main()
