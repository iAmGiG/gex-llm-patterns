#!/usr/bin/env python3
"""
Issue #144 Phase 3: Pattern-Outcome Contingency Matrix Analysis
Paper #1 MC Review Defense - Mechanism-Specific Relationships

Builds 3×4 contingency matrix to prove mechanism-specific relationships:
- Gamma Positioning → Volatility Amplification (C1)
- Stock Pinning → Strike Convergence (C3)
- 0DTE Hedging → Range Expansion (C4)

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/144
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import chi2_contingency

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def recalculate_c3_with_flip_points(df, flip_points_df):
    """Recalculate C3 (Strike Convergence) using real flip points.

    C3: Distance to flip point decreases T+1
    """
    print("\nRecalculating C3 (Strike Convergence) with flip points...")

    # Merge flip points (includes spot_price, flip_point, distance_from_spot)
    df = df.merge(
        flip_points_df[["date", "spot_price", "flip_point", "distance_from_spot"]],
        on="date",
        how="left",
        suffixes=("", "_merged"),
    )

    # Rename for clarity
    df["flip_point_t"] = df["flip_point"]
    df["distance_to_flip_t"] = df["distance_from_spot"]

    # Sort by pattern and date
    df = df.sort_values(["pattern_type", "date"]).reset_index(drop=True)

    # Create t+1 columns by pattern (shift within each pattern)
    for pattern in df["pattern_type"].unique():
        mask = df["pattern_type"] == pattern
        df.loc[mask, "flip_point_t1"] = df.loc[mask, "flip_point_t"].shift(-1)
        df.loc[mask, "spot_price_t1"] = df.loc[mask, "spot_price"].shift(-1)

    # Calculate distance at t+1 (spot_price(t+1) to flip_point(t))
    df["distance_to_flip_t1"] = abs(df["spot_price_t1"] - df["flip_point_t"])

    # C3: Strike convergence = distance decreased
    df["criterion_3_strike_convergence"] = df["distance_to_flip_t1"] < df["distance_to_flip_t"]

    materialized = df["criterion_3_strike_convergence"].sum()
    total = df["criterion_3_strike_convergence"].notna().sum()

    print(f"  C3 recalculated: {materialized}/{total} days ({materialized/total*100:.1f}%)")

    return df


def build_contingency_matrix(df):
    """Build 3×4 contingency matrix: 3 patterns × 4 outcomes.

    Returns:
        matrix: 3×4 numpy array
        pattern_names: list of pattern names
        criterion_names: list of criterion names
    """
    print("\n" + "=" * 80)
    print("BUILDING 3×4 CONTINGENCY MATRIX")
    print("=" * 80)

    patterns = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
    criteria = [
        "criterion_1_volatility_amplification",
        "criterion_2_directional_followthrough",
        "criterion_3_strike_convergence",
        "criterion_4_range_expansion",
    ]

    # Filter to detection days only
    det_df = df[df["detected"] == True].copy()

    print(f"\nDetection days by pattern:")
    for pattern in patterns:
        n = len(det_df[det_df["pattern_type"] == pattern])
        print(f"  {pattern}: {n}")

    # Build matrix
    matrix = np.zeros((3, 4))

    for i, pattern in enumerate(patterns):
        pattern_df = det_df[det_df["pattern_type"] == pattern]

        for j, criterion in enumerate(criteria):
            count = pattern_df[criterion].sum()
            matrix[i, j] = count

    # Display matrix
    print("\n" + "=" * 80)
    print("CONTINGENCY MATRIX: Patterns × Outcomes (Detection Days Only)")
    print("=" * 80)
    print()

    # Create DataFrame for nice display
    matrix_df = pd.DataFrame(
        matrix, index=patterns, columns=["C1: Vol Amp", "C2: Directional", "C3: Convergence", "C4: Range Exp"]
    )

    print(matrix_df.to_string())
    print()

    # Calculate row totals (pattern totals)
    row_totals = matrix.sum(axis=1)
    print("Pattern Totals (Detection Days):")
    for i, pattern in enumerate(patterns):
        print(f"  {pattern}: {int(row_totals[i])}")
    print()

    # Calculate materialization rates per pattern
    print("Materialization Rates by Pattern:")
    for i, pattern in enumerate(patterns):
        pattern_df = det_df[det_df["pattern_type"] == pattern]
        n = len(pattern_df)

        print(f"\n{pattern} (n={n}):")
        for j, criterion in enumerate(criteria):
            count = matrix[i, j]
            rate = count / n * 100 if n > 0 else 0
            print(f"  {criterion.replace('criterion_', 'C').replace('_', ' ').title()}: {int(count)}/{n} ({rate:.1f}%)")

    return matrix, patterns, ["C1", "C2", "C3", "C4"]


def chi_square_test_independence(matrix, pattern_names, criterion_names):
    """
    Test independence: H0: Pattern type and outcome are independent.

    If p < 0.05, we reject H0 and conclude patterns predict specific outcomes.
    """
    print("\n" + "=" * 80)
    print("CHI-SQUARE TEST FOR INDEPENDENCE")
    print("=" * 80)
    print()

    # Run chi-square test
    chi2, p_value, dof, expected = chi2_contingency(matrix)

    print(f"Chi-square statistic: {chi2:.3f}")
    print(f"Degrees of freedom: {dof}")
    print(f"p-value: {p_value:.6f}")
    print()

    if p_value < 0.001:
        sig_marker = "***"
        verdict = "HIGHLY SIGNIFICANT"
    elif p_value < 0.01:
        sig_marker = "**"
        verdict = "VERY SIGNIFICANT"
    elif p_value < 0.05:
        sig_marker = "*"
        verdict = "SIGNIFICANT"
    else:
        sig_marker = "ns"
        verdict = "NOT SIGNIFICANT"

    print(f"Significance: {verdict} {sig_marker}")
    print()

    if p_value < 0.05:
        print("✅ RESULT: Pattern type and outcome are NOT independent")
        print("   → Patterns predict specific outcomes (mechanism-specific)")
    else:
        print("❌ RESULT: Pattern type and outcome are independent")
        print("   → Patterns do NOT predict specific outcomes")

    print()
    print("Expected frequencies under independence:")
    expected_df = pd.DataFrame(expected, index=pattern_names, columns=criterion_names)
    print(expected_df.to_string())
    print()

    # Calculate standardized residuals
    print("Standardized Residuals (observed - expected) / sqrt(expected):")
    residuals = (matrix - expected) / np.sqrt(expected)
    residuals_df = pd.DataFrame(residuals, index=pattern_names, columns=criterion_names)
    print(residuals_df.to_string())
    print()

    print("Interpretation of residuals:")
    print("  > +2: Pattern predicts this outcome MORE than expected (mechanism-specific)")
    print("  < -2: Pattern predicts this outcome LESS than expected (mechanism-avoidant)")
    print()

    return {"chi2": chi2, "p_value": p_value, "dof": dof, "expected": expected, "residuals": residuals}


def analyze_mechanism_specificity(matrix, residuals, pattern_names, criterion_names):
    """Analyze whether patterns show mechanism-specific associations.

    Expected:
    - Gamma Positioning → C1 (Volatility Amplification)
    - Stock Pinning → C3 (Strike Convergence)
    - 0DTE Hedging → C4 (Range Expansion)
    """
    print("\n" + "=" * 80)
    print("MECHANISM-SPECIFIC ASSOCIATION ANALYSIS")
    print("=" * 80)
    print()

    # Map expected associations
    expected_associations = {"gamma_positioning": "C1", "stock_pinning": "C3", "0dte_hedging": "C4"}

    criterion_map = {"C1": 0, "C2": 1, "C3": 2, "C4": 3}

    print("Expected Mechanism-Specific Associations:")
    print("  Gamma Positioning → C1 (Volatility Amplification)")
    print("  Stock Pinning → C3 (Strike Convergence)")
    print("  0DTE Hedging → C4 (Range Expansion)")
    print()

    results = []

    for i, pattern in enumerate(pattern_names):
        expected_criterion = expected_associations[pattern]
        expected_idx = criterion_map[expected_criterion]

        residual = residuals[i, expected_idx]

        print(f"{pattern}:")
        print(f"  Expected association: {expected_criterion}")
        print(f"  Standardized residual: {residual:.3f}")

        if residual > 2:
            status = "✅ STRONG POSITIVE (mechanism-specific)"
        elif residual > 1:
            status = "✓ POSITIVE (supports specificity)"
        elif residual > -1:
            status = "~ NEUTRAL (no clear association)"
        elif residual > -2:
            status = "✗ NEGATIVE (contradicts specificity)"
        else:
            status = "❌ STRONG NEGATIVE (mechanism-avoidant)"

        print(f"  Status: {status}")
        print()

        results.append(
            {"pattern": pattern, "expected_criterion": expected_criterion, "residual": residual, "status": status}
        )

    # Summary
    strong_positive = sum(1 for r in results if r["residual"] > 2)
    positive = sum(1 for r in results if r["residual"] > 1)

    print("=" * 80)
    print("MECHANISM-SPECIFICITY VERDICT")
    print("=" * 80)
    print()

    if strong_positive >= 2:
        print("✅ PROVEN: Mechanism-specific relationships detected")
        print(f"   {strong_positive}/3 patterns show strong positive residuals (>2)")
    elif positive >= 2:
        print("✓ SUPPORTED: Mechanism-specific relationships likely")
        print(f"   {positive}/3 patterns show positive residuals (>1)")
    else:
        print("❌ NOT PROVEN: Mechanism-specific relationships not detected")
        print(f"   Only {positive}/3 patterns show positive residuals")

    print()

    return results


def main():
    """Main workflow for Issue #144 Phase 3."""

    print("=" * 80)
    print("Issue #144 Phase 3: Pattern-Outcome Contingency Matrix")
    print("Paper #1 MC Review Defense - Mechanism-Specific Relationships")
    print("=" * 80)
    print()

    # Paths
    analysis_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    # Load Phase 1 data
    print("Step 1: Loading Phase 1 materialization criteria...")
    criteria_df = pd.read_csv(analysis_dir / "issue_144_materialization_criteria.csv")
    print(f"  Loaded {len(criteria_df)} pattern-day observations")
    print()

    # Load flip points
    print("Step 2: Loading flip points...")
    flip_df = pd.read_csv(analysis_dir / "issue_144_flip_points.csv")
    print(f"  Loaded {len(flip_df)} flip points")
    print()

    # Recalculate C3
    print("Step 3: Recalculating C3 with real flip points...")
    criteria_df = recalculate_c3_with_flip_points(criteria_df, flip_df)

    # Build contingency matrix
    print("\nStep 4: Building 3×4 contingency matrix...")
    matrix, patterns, criteria_names = build_contingency_matrix(criteria_df)

    # Chi-square test
    print("\nStep 5: Testing pattern-outcome independence...")
    chi_results = chi_square_test_independence(matrix, patterns, criteria_names)

    # Analyze mechanism specificity
    print("\nStep 6: Analyzing mechanism-specific associations...")
    specificity_results = analyze_mechanism_specificity(matrix, chi_results["residuals"], patterns, criteria_names)

    # Save results
    print("\nStep 7: Saving results...")

    # Save updated criteria with C3
    criteria_path = analysis_dir / "issue_144_materialization_criteria_with_c3.csv"
    criteria_df.to_csv(criteria_path, index=False)
    print(f"  Saved: {criteria_path}")

    # Save contingency matrix
    matrix_df = pd.DataFrame(matrix, index=patterns, columns=criteria_names)
    matrix_path = analysis_dir / "issue_144_contingency_matrix.csv"
    matrix_df.to_csv(matrix_path)
    print(f"  Saved: {matrix_path}")

    # Save chi-square results
    import yaml

    results_summary = {
        "chi_square_test": {
            "chi2": float(chi_results["chi2"]),
            "p_value": float(chi_results["p_value"]),
            "dof": int(chi_results["dof"]),
            "significant": chi_results["p_value"] < 0.05,
        },
        "mechanism_specificity": specificity_results,
        "contingency_matrix": matrix.tolist(),
        "expected_frequencies": chi_results["expected"].tolist(),
        "residuals": chi_results["residuals"].tolist(),
    }

    results_path = analysis_dir / "issue_144_phase3_results.yaml"
    with open(results_path, "w") as f:
        yaml.dump(results_summary, f, default_flow_style=False, sort_keys=False)
    print(f"  Saved: {results_path}")

    print()
    print("=" * 80)
    print("PHASE 3 COMPLETE")
    print("=" * 80)
    print()

    return criteria_df, matrix, chi_results, specificity_results


if __name__ == "__main__":
    criteria_df, matrix, chi_results, specificity_results = main()
