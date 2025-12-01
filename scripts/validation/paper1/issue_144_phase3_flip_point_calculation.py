#!/usr/bin/env python3
"""
Issue #144 Phase 3: Calculate Gamma Flip Point from Strike Data
Paper #1 MC Review Defense - Enable C3 (Strike Convergence)

Calculates gamma flip point for each day from strike-level GEX data,
enabling C3 (Strike Convergence) criterion for mechanism-specific analysis.

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/144
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def calculate_flip_point(strikes_df, spot_price):
    """Calculate gamma flip point from strike-level GEX data.

    The flip point is the strike price where net GEX crosses zero.

    Args:
        strikes_df: DataFrame with columns [strike, net_gex]
        spot_price: Current spot price

    Returns:
        dict with flip_point, distance_from_spot, flip_type
    """
    # Sort by strike and reset index
    strikes_df = strikes_df.sort_values("strike").reset_index(drop=True).copy()

    # Find sign changes
    strikes_df["sign"] = np.sign(strikes_df["net_gex"])
    strikes_df["sign_change"] = strikes_df["sign"].diff() != 0

    # Get sign change locations (now using integer positions)
    sign_change_mask = strikes_df["sign_change"]
    sign_change_positions = strikes_df.index[sign_change_mask].tolist()

    if len(sign_change_positions) == 0:
        # No sign change - all same sign
        return {"flip_point": None, "distance_from_spot": None, "flip_type": "no_flip", "net_gex_at_flip": None}

    # Get first sign change (primary flip point)
    curr_pos = sign_change_positions[0]

    # Get the two strikes around the flip
    prev_pos = curr_pos - 1

    if prev_pos < 0:
        # Sign change at first strike
        flip_strike = strikes_df.loc[curr_pos, "strike"]
        flip_gex = strikes_df.loc[curr_pos, "net_gex"]
        flip_type = "first_strike"
    else:
        # Interpolate between two strikes
        strike1 = strikes_df.loc[prev_pos, "strike"]
        strike2 = strikes_df.loc[curr_pos, "strike"]
        gex1 = strikes_df.loc[prev_pos, "net_gex"]
        gex2 = strikes_df.loc[curr_pos, "net_gex"]

        # Linear interpolation to find zero crossing
        if gex2 - gex1 != 0:
            flip_strike = strike1 - gex1 * (strike2 - strike1) / (gex2 - gex1)
        else:
            flip_strike = (strike1 + strike2) / 2

        flip_gex = 0  # By definition at flip point

        # Determine flip type
        if gex1 > 0 and gex2 < 0:
            flip_type = "positive_to_negative"
        elif gex1 < 0 and gex2 > 0:
            flip_type = "negative_to_positive"
        else:
            flip_type = "unknown"

    # Calculate distance from spot
    distance = abs(flip_strike - spot_price)

    return {
        "flip_point": flip_strike,
        "distance_from_spot": distance,
        "flip_type": flip_type,
        "net_gex_at_flip": flip_gex,
    }


def calculate_all_flip_points(db_path, start_date="2024-01-02", end_date="2024-12-31"):
    """Calculate flip points for all dates from strike-level data.

    Returns:
        DataFrame with date, flip_point, distance_from_spot
    """
    conn = sqlite3.connect(db_path)

    print("Extracting strike-level GEX data...")

    # Get all strike-level data
    strike_query = """
    SELECT
        date,
        strike,
        net_gex
    FROM strike_gex_details
    WHERE date BETWEEN ? AND ?
      AND symbol = 'SPY'
    ORDER BY date, strike
    """

    strikes_df = pd.read_sql_query(strike_query, conn, params=(start_date, end_date))
    print(f"  Loaded {len(strikes_df):,} strike records")

    # Get spot prices
    spot_query = """
    SELECT date, spot_price
    FROM daily_gex_metrics
    WHERE date BETWEEN ? AND ?
      AND symbol = 'SPY'
    """

    spot_df = pd.read_sql_query(spot_query, conn, params=(start_date, end_date))
    print(f"  Loaded {len(spot_df)} daily spot prices")

    conn.close()

    # Calculate flip point for each date
    print("\nCalculating flip points...")

    flip_points = []

    for date, group in strikes_df.groupby("date"):
        spot = spot_df[spot_df["date"] == date]["spot_price"].values

        if len(spot) == 0:
            print(f"  ⚠️ No spot price for {date}, skipping")
            continue

        spot_price = spot[0]

        result = calculate_flip_point(group, spot_price)

        flip_points.append(
            {
                "date": date,
                "spot_price": spot_price,
                "flip_point": result["flip_point"],
                "distance_from_spot": result["distance_from_spot"],
                "flip_type": result["flip_type"],
            }
        )

    flip_df = pd.DataFrame(flip_points)

    print(f"\nFlip point calculation complete:")
    print(f"  Total days: {len(flip_df)}")
    print(f"  Days with flip: {flip_df['flip_point'].notna().sum()}")
    print(f"  Days without flip: {flip_df['flip_point'].isna().sum()}")

    if flip_df["flip_point"].notna().sum() > 0:
        print(f"\n  Flip point statistics:")
        print(f"    Mean distance from spot: ${flip_df['distance_from_spot'].mean():.2f}")
        print(f"    Median distance: ${flip_df['distance_from_spot'].median():.2f}")
        print(f"    Min distance: ${flip_df['distance_from_spot'].min():.2f}")
        print(f"    Max distance: ${flip_df['distance_from_spot'].max():.2f}")

    return flip_df


def main():
    """Main workflow for Issue #144 Phase 3 flip point calculation."""

    print("=" * 80)
    print("Issue #144 Phase 3: Gamma Flip Point Calculation")
    print("Paper #1 MC Review Defense - Enable C3 (Strike Convergence)")
    print("=" * 80)
    print()

    # Paths
    db_path = project_root / ".cache" / "consolidated_historical.db"
    output_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate flip points
    print("Step 1: Calculating flip points from strike-level data...")
    flip_df = calculate_all_flip_points(db_path)
    print()

    # Save results
    print("Step 2: Saving results...")
    output_path = output_dir / "issue_144_flip_points.csv"
    flip_df.to_csv(output_path, index=False)
    print(f"  Saved: {output_path}")
    print()

    print("=" * 80)
    print("FLIP POINT CALCULATION COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Merge flip points with materialization criteria dataset")
    print("  2. Recalculate C3 (Strike Convergence) with real flip points")
    print("  3. Build 3×4 contingency matrix")
    print()

    return flip_df


if __name__ == "__main__":
    flip_df = main()
