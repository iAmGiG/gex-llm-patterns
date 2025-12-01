#!/usr/bin/env python3
"""
Issue #144: Calculate Materialization Criteria for P-Hacking Defense
Paper #1 MC Review Defense - Pattern-Outcome Specificity

Calculates 4 materialization criteria for all detection days:
1. Volatility Amplification: realized_vol > forecast_vol
2. Directional Follow-through: price direction matches GEX
3. Strike Convergence: distance reduction to flip point
4. Range Expansion: intraday_range > 1.3 * avg_5day_range

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/144
"""

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def load_detection_days_from_yaml():
    """Load detection status from 3 pattern YAML validation files.

    Returns:
        DataFrame with columns: date, pattern_type, detected
    """
    yaml_dir = project_root / "reports" / "validation" / "paper1_pattern_taxonomy"

    # 3 patterns for Issue #144 (using full-year unbiased data)
    patterns = {
        "gamma_positioning": yaml_dir / "gamma_positioning_SPY_2024_unbiased.yaml",
        "stock_pinning": yaml_dir / "stock_pinning_SPY_2024_unbiased.yaml",
        "0dte_hedging": yaml_dir / "0dte_hedging_SPY_2024_unbiased.yaml",
    }

    all_detections = []

    for pattern_name, yaml_path in patterns.items():
        if not yaml_path.exists():
            print(f"  ⚠️ Warning: {yaml_path} not found, skipping...")
            continue

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        # Extract detections list
        detections_list = data.get("detections", [])

        for entry in detections_list:
            date = entry.get("date")
            detected = entry.get("detected", False)

            all_detections.append({"date": date, "pattern_type": pattern_name, "detected": detected})

        print(f"  Loaded {len(detections_list)} days for {pattern_name}")

    df = pd.DataFrame(all_detections)

    print(f"\nTotal: {len(df)} pattern-day observations")
    print(f"  Detected: {df['detected'].sum()}")
    print(f"  Not detected: {(~df['detected']).sum()}")
    print(f"  By pattern:")
    for pattern in df["pattern_type"].unique():
        pattern_df = df[df["pattern_type"] == pattern]
        print(f"    {pattern}: {pattern_df['detected'].sum()}/{len(pattern_df)} detected")

    return df


def extract_database_metrics(db_path, start_date="2024-01-02", end_date="2024-12-31"):
    """Extract daily metrics from consolidated database.

    Returns:
        DataFrame with date, OHLCV, GEX metrics, volatility
    """
    conn = sqlite3.connect(db_path)

    query = """
    SELECT
        date,
        spot_price,
        open,
        high,
        low,
        close,
        volume,
        total_gex,
        net_call_gex,
        net_put_gex,
        gamma_flip_point,
        gex_regime
    FROM daily_gex_metrics
    WHERE date BETWEEN ? AND ?
      AND symbol = 'SPY'
    ORDER BY date
    """

    df = pd.read_sql_query(query, conn, params=(start_date, end_date))
    conn.close()

    print(f"Extracted {len(df)} days from database")
    print(f"  OHLC coverage: {df['open'].notna().sum()}/{len(df)} days")

    return df


def calculate_volatility_amplification(df):
    """
    Criterion 1: Volatility Amplification

    realized_vol(t+1) > forecast_vol(t)

    - Realized vol: ((high - low) / close) * 100
    - Forecast vol: 5-day rolling average of realized vol
    """
    print("\nCalculating Criterion 1: Volatility Amplification...")

    # Calculate realized volatility (intraday range as % of close)
    df["realized_vol_t1"] = ((df["high"] - df["low"]) / df["close"]) * 100

    # Calculate forecast (5-day rolling average of realized vol, shifted forward)
    df["forecast_vol"] = df["realized_vol_t1"].rolling(window=5, min_periods=1).mean().shift(1)

    # Criterion: realized > forecast
    df["criterion_1_volatility_amplification"] = df["realized_vol_t1"] > df["forecast_vol"]

    # Count materialized
    materialized = df["criterion_1_volatility_amplification"].sum()
    total = df["criterion_1_volatility_amplification"].notna().sum()

    print(f"  Materialized: {materialized}/{total} days ({materialized/total*100:.1f}%)")

    return df


def calculate_directional_followthrough(df):
    """
    Criterion 2: Directional Follow-through

    Price direction matches GEX regime expectation:
    - Negative GEX → Dealers short gamma → Trend amplification
    - Positive GEX → Dealers long gamma → Trend dampening

    Operationalization:
    - Negative GEX: close(t+1) moves AWAY from previous close (trend continues)
    - Positive GEX: close(t+1) moves TOWARD previous close (mean reversion)
    """
    print("\nCalculating Criterion 2: Directional Follow-through...")

    # Calculate price change (close_t+1 - close_t)
    df["price_change"] = df["close"].diff()

    # For negative GEX: materialized if |price_change| > 0 (trend continues)
    # For positive GEX: materialized if price reverses (sign flip)

    # Initialize as boolean column (not float with NaN)
    df["criterion_2_directional_followthrough"] = False

    # Negative GEX: any directional move counts
    negative_gex_mask = df["total_gex"] < 0
    df.loc[negative_gex_mask, "criterion_2_directional_followthrough"] = (
        abs(df.loc[negative_gex_mask, "price_change"]) > 0
    ).astype(bool)

    # Positive GEX: price stabilization (small move)
    positive_gex_mask = df["total_gex"] > 0
    # Use median absolute price change as threshold
    median_abs_change = abs(df["price_change"]).median()
    df.loc[positive_gex_mask, "criterion_2_directional_followthrough"] = (
        abs(df.loc[positive_gex_mask, "price_change"]) < median_abs_change
    ).astype(bool)

    materialized = df["criterion_2_directional_followthrough"].sum()
    total = df["criterion_2_directional_followthrough"].notna().sum()

    print(f"  Materialized: {materialized}/{total} days ({materialized/total*100:.1f}%)")

    return df


def calculate_strike_convergence(df):
    """
    Criterion 3: Strike Convergence

    Distance to gamma flip point decreases over T+1:
    |spot(t+1) - flip_point(t)| < |spot(t) - flip_point(t)|
    """
    print("\nCalculating Criterion 3: Strike Convergence...")

    # Distance at t
    df["distance_t"] = abs(df["spot_price"] - df["gamma_flip_point"])

    # Distance at t+1 (spot_price(t+1) vs flip_point(t))
    df["spot_price_t1"] = df["spot_price"].shift(-1)
    df["distance_t1"] = abs(df["spot_price_t1"] - df["gamma_flip_point"])

    # Criterion: distance decreased
    df["criterion_3_strike_convergence"] = df["distance_t1"] < df["distance_t"]

    materialized = df["criterion_3_strike_convergence"].sum()
    total = df["criterion_3_strike_convergence"].notna().sum()

    print(f"  Materialized: {materialized}/{total} days ({materialized/total*100:.1f}%)")

    return df


def calculate_range_expansion(df):
    """
    Criterion 4: Range Expansion

    Intraday range exceeds recent average:
    (high - low)(t+1) > 1.3 * avg_5day_range(t)
    """
    print("\nCalculating Criterion 4: Range Expansion...")

    # Calculate intraday range
    df["intraday_range"] = df["high"] - df["low"]

    # Calculate 5-day rolling average of range (shifted forward)
    df["avg_5day_range"] = df["intraday_range"].rolling(window=5, min_periods=1).mean().shift(1)

    # Criterion: range > 1.3 * avg
    df["criterion_4_range_expansion"] = df["intraday_range"] > (1.3 * df["avg_5day_range"])

    materialized = df["criterion_4_range_expansion"].sum()
    total = df["criterion_4_range_expansion"].notna().sum()

    print(f"  Materialized: {materialized}/{total} days ({materialized/total*100:.1f}%)")

    return df


def merge_with_patterns(metrics_df, validation_df):
    """Merge calculated criteria with pattern detection status.

    Returns:
        DataFrame with date, pattern_type, detected, 4 criteria columns
    """
    # Merge on date
    merged = validation_df.merge(
        metrics_df[
            [
                "date",
                "criterion_1_volatility_amplification",
                "criterion_2_directional_followthrough",
                "criterion_3_strike_convergence",
                "criterion_4_range_expansion",
                "realized_vol_t1",
                "forecast_vol",
                "price_change",
                "distance_t",
                "distance_t1",
                "intraday_range",
                "avg_5day_range",
            ]
        ],
        on="date",
        how="left",
    )

    print(f"\nMerged dataset: {len(merged)} days")
    print(f"  Detection days: {merged['detected'].sum()}")

    return merged


def calculate_pattern_specific_rates(df):
    """Calculate materialization rates by pattern type.

    Returns:
        DataFrame with pattern-level summaries
    """
    print("\n" + "=" * 80)
    print("PATTERN-SPECIFIC MATERIALIZATION RATES")
    print("=" * 80)

    # Group by pattern type and detected status
    pattern_groups = df[df["detected"] == True].groupby("pattern_type")

    results = []

    for pattern, group in pattern_groups:
        n_days = len(group)

        c1 = group["criterion_1_volatility_amplification"].sum()
        c2 = group["criterion_2_directional_followthrough"].sum()
        c3 = group["criterion_3_strike_convergence"].sum()
        c4 = group["criterion_4_range_expansion"].sum()

        c1_pct = c1 / n_days * 100 if n_days > 0 else 0
        c2_pct = c2 / n_days * 100 if n_days > 0 else 0
        c3_pct = c3 / n_days * 100 if n_days > 0 else 0
        c4_pct = c4 / n_days * 100 if n_days > 0 else 0

        results.append(
            {
                "pattern": pattern,
                "n_days": n_days,
                "c1_volatility_amp": c1,
                "c1_pct": c1_pct,
                "c2_directional": c2,
                "c2_pct": c2_pct,
                "c3_convergence": c3,
                "c3_pct": c3_pct,
                "c4_range_exp": c4,
                "c4_pct": c4_pct,
            }
        )

        print(f"\n{pattern} (n={n_days}):")
        print(f"  C1 Volatility Amplification: {c1}/{n_days} ({c1_pct:.1f}%)")
        print(f"  C2 Directional Follow-through: {c2}/{n_days} ({c2_pct:.1f}%)")
        print(f"  C3 Strike Convergence: {c3}/{n_days} ({c3_pct:.1f}%)")
        print(f"  C4 Range Expansion: {c4}/{n_days} ({c4_pct:.1f}%)")

    return pd.DataFrame(results)


def main():
    """Main workflow for Issue #144 Phase 1."""

    print("=" * 80)
    print("Issue #144 Phase 1: Calculate Materialization Criteria")
    print("Paper #1 MC Review Defense - P-Hacking Refutation")
    print("=" * 80)
    print()

    # Paths
    db_path = project_root / ".cache" / "consolidated_historical.db"
    output_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Load validation data from YAML files
    print("Step 1: Loading pattern detection data from YAML files...")
    validation_df = load_detection_days_from_yaml()
    print()

    # Step 2: Extract database metrics
    print("Step 2: Extracting database metrics...")
    metrics_df = extract_database_metrics(db_path)
    print()

    # Step 3: Calculate 4 criteria
    print("Step 3: Calculating materialization criteria...")
    metrics_df = calculate_volatility_amplification(metrics_df)
    metrics_df = calculate_directional_followthrough(metrics_df)
    metrics_df = calculate_strike_convergence(metrics_df)
    metrics_df = calculate_range_expansion(metrics_df)

    # Step 4: Merge with pattern types
    print("\nStep 4: Merging with pattern detection data...")
    merged_df = merge_with_patterns(metrics_df, validation_df)

    # Step 5: Calculate pattern-specific rates
    print("\nStep 5: Calculating pattern-specific materialization rates...")
    pattern_summary = calculate_pattern_specific_rates(merged_df)

    # Step 6: Save results
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    # Save full dataset
    full_path = output_dir / "issue_144_materialization_criteria.csv"
    merged_df.to_csv(full_path, index=False)
    print(f"  Saved: {full_path}")

    # Save pattern summary
    summary_path = output_dir / "issue_144_pattern_summary.csv"
    pattern_summary.to_csv(summary_path, index=False)
    print(f"  Saved: {summary_path}")

    print()
    print("=" * 80)
    print("PHASE 1 COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review materialization rates by pattern")
    print("  2. Sample 100 random non-detection days for baseline")
    print("  3. Build 3x4 contingency table (patterns × outcomes)")
    print("  4. Calculate chi-square test for independence")
    print()

    return merged_df, pattern_summary


if __name__ == "__main__":
    merged_df, pattern_summary = main()
