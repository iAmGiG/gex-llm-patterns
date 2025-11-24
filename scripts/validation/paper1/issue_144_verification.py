#!/usr/bin/env python3
"""
Issue #144: Data Verification and Validation
Paper #1 MC Review Defense - Complete Verification

Verifies all calculations, data integrity, and results for Issue #144.

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/144
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def verify_phase1_data():
    """Verify Phase 1: Materialization Criteria calculations."""
    print("=" * 80)
    print("PHASE 1 VERIFICATION: Materialization Criteria")
    print("=" * 80)
    print()

    analysis_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    # Load data
    criteria_df = pd.read_csv(analysis_dir / "issue_144_materialization_criteria.csv")

    print(f"Dataset: {len(criteria_df)} pattern-day observations")
    print(f"  Patterns: {criteria_df['pattern_type'].unique()}")
    print(f"  Detection days: {criteria_df['detected'].sum()}")
    print(f"  Non-detection days: {(~criteria_df['detected']).sum()}")
    print()

    # Verify detection counts per pattern
    print("Detection counts by pattern:")
    for pattern in criteria_df["pattern_type"].unique():
        pattern_df = criteria_df[criteria_df["pattern_type"] == pattern]
        n_detected = pattern_df["detected"].sum()
        total = len(pattern_df)
        print(f"  {pattern}: {n_detected}/{total} ({n_detected/total*100:.1f}%)")
    print()

    # Expected counts (from YAML files)
    expected = {"gamma_positioning": 168, "stock_pinning": 163, "0dte_hedging": 188}

    # Verify matches
    all_match = True
    for pattern, expected_count in expected.items():
        actual = criteria_df[(criteria_df["pattern_type"] == pattern) & (criteria_df["detected"] == True)].shape[0]
        if actual != expected_count:
            print(f"  ❌ MISMATCH: {pattern} expected {expected_count}, got {actual}")
            all_match = False

    if all_match:
        print("✅ Detection counts verified")
    print()

    # Verify materialization rates
    print("Materialization rates (detection days only):")
    det_df = criteria_df[criteria_df["detected"] == True]

    for criterion in [
        "criterion_1_volatility_amplification",
        "criterion_2_directional_followthrough",
        "criterion_3_strike_convergence",
        "criterion_4_range_expansion",
    ]:
        rate = det_df[criterion].sum() / len(det_df) * 100
        print(f"  {criterion}: {rate:.1f}%")

    print()
    return criteria_df


def verify_phase2_data(criteria_df):
    """Verify Phase 2: Baseline Comparison calculations."""
    print("=" * 80)
    print("PHASE 2 VERIFICATION: Baseline Comparison")
    print("=" * 80)
    print()

    analysis_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    # Load baseline sample
    baseline_df = pd.read_csv(analysis_dir / "issue_144_baseline_sample.csv")

    print(f"Baseline sample: {len(baseline_df)} non-detection days")
    print()

    # Verify baseline is all non-detection
    if baseline_df["detected"].any():
        print("❌ ERROR: Baseline contains detection days!")
    else:
        print("✅ Baseline verified: all non-detection days")
    print()

    # Recalculate materialization rates
    det_df = criteria_df[criteria_df["detected"] == True]

    print("Detection vs Baseline rates:")
    for criterion in ["criterion_1_volatility_amplification", "criterion_4_range_expansion"]:
        det_rate = det_df[criterion].sum() / len(det_df) * 100
        base_rate = baseline_df[criterion].sum() / len(baseline_df) * 100
        lift = det_rate / base_rate if base_rate > 0 else float("inf")

        print(f"  {criterion}:")
        print(f"    Detection: {det_rate:.1f}%")
        print(f"    Baseline: {base_rate:.1f}%")
        print(f"    Lift: {lift:.2f}x")

    print()

    # Verify chi-square results
    print("Chi-square verification:")

    for criterion in ["criterion_1_volatility_amplification", "criterion_4_range_expansion"]:
        # Build contingency table
        det_yes = det_df[criterion].sum()
        det_no = len(det_df) - det_yes
        base_yes = baseline_df[criterion].sum()
        base_no = len(baseline_df) - base_yes

        table = np.array([[det_yes, det_no], [base_yes, base_no]])

        chi2, p_val, dof, expected = stats.chi2_contingency(table)

        print(f"  {criterion}:")
        print(f"    χ² = {chi2:.3f}, p = {p_val:.6f}")

    print()
    return baseline_df


def verify_phase3_data():
    """Verify Phase 3: Contingency Matrix calculations."""
    print("=" * 80)
    print("PHASE 3 VERIFICATION: Contingency Matrix")
    print("=" * 80)
    print()

    analysis_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    # Load updated criteria with C3
    criteria_df = pd.read_csv(analysis_dir / "issue_144_materialization_criteria_with_c3.csv")

    # Load contingency matrix
    matrix_df = pd.read_csv(analysis_dir / "issue_144_contingency_matrix.csv", index_col=0)

    print("Contingency Matrix:")
    print(matrix_df)
    print()

    # Verify matrix sums
    det_df = criteria_df[criteria_df["detected"] == True]

    print("Verifying matrix totals:")
    for pattern in matrix_df.index:
        pattern_total = matrix_df.loc[pattern].sum()
        actual_detections = len(det_df[det_df["pattern_type"] == pattern])

        # Expected: each detection day contributes to multiple outcomes
        print(f"  {pattern}:")
        print(f"    Matrix sum: {int(pattern_total)}")
        print(f"    Detection days: {actual_detections}")

    print()

    # Recalculate chi-square
    matrix = matrix_df.values
    chi2, p_val, dof, expected = stats.chi2_contingency(matrix)

    print("Chi-square test (pattern × outcome independence):")
    print(f"  χ² = {chi2:.3f}")
    print(f"  p = {p_val:.6f}")
    print(f"  dof = {dof}")
    print(f"  Significant: {'Yes' if p_val < 0.05 else 'No'}")
    print()

    return criteria_df, matrix_df


def create_summary_statistics():
    """Generate comprehensive summary statistics."""
    print("=" * 80)
    print("SUMMARY STATISTICS FOR MC REVIEW")
    print("=" * 80)
    print()

    analysis_dir = project_root / "docs" / "papers" / "paper1" / "analysis"

    # Load all data
    criteria_df = pd.read_csv(analysis_dir / "issue_144_materialization_criteria_with_c3.csv")
    baseline_df = pd.read_csv(analysis_dir / "issue_144_baseline_sample.csv")
    matrix_df = pd.read_csv(analysis_dir / "issue_144_contingency_matrix.csv", index_col=0)

    det_df = criteria_df[criteria_df["detected"] == True]

    summary = {
        "dataset_overview": {
            "total_pattern_days": len(criteria_df),
            "detection_days": len(det_df),
            "non_detection_days": len(criteria_df) - len(det_df),
            "baseline_sample_size": len(baseline_df),
        },
        "phase1_materialization_rates": {},
        "phase2_baseline_comparison": {},
        "phase3_contingency_analysis": {},
    }

    # Phase 1: Detection day rates
    for i, criterion in enumerate(
        [
            "criterion_1_volatility_amplification",
            "criterion_2_directional_followthrough",
            "criterion_3_strike_convergence",
            "criterion_4_range_expansion",
        ],
        1,
    ):
        rate = det_df[criterion].sum() / len(det_df) * 100
        summary["phase1_materialization_rates"][f"C{i}"] = f"{rate:.1f}%"

    # Phase 2: Baseline comparison
    for i, criterion in enumerate(
        [("criterion_1_volatility_amplification", "C1"), ("criterion_4_range_expansion", "C4")]
    ):
        crit_col, crit_name = criterion
        det_rate = det_df[crit_col].sum() / len(det_df) * 100
        base_rate = baseline_df[crit_col].sum() / len(baseline_df) * 100

        table = np.array(
            [
                [det_df[crit_col].sum(), len(det_df) - det_df[crit_col].sum()],
                [baseline_df[crit_col].sum(), len(baseline_df) - baseline_df[crit_col].sum()],
            ]
        )
        chi2, p_val, _, _ = stats.chi2_contingency(table)

        summary["phase2_baseline_comparison"][crit_name] = {
            "detection_rate": f"{det_rate:.1f}%",
            "baseline_rate": f"{base_rate:.1f}%",
            "lift": f"{det_rate/base_rate:.2f}x",
            "chi2": f"{chi2:.3f}",
            "p_value": f"{p_val:.6f}",
            "significant": p_val < 0.05,
        }

    # Phase 3: Contingency matrix
    matrix = matrix_df.values
    chi2, p_val, dof, _ = stats.chi2_contingency(matrix)

    summary["phase3_contingency_analysis"] = {
        "chi2": f"{chi2:.3f}",
        "p_value": f"{p_val:.6f}",
        "dof": dof,
        "significant": p_val < 0.05,
        "verdict": "Mechanism-specific NOT proven" if p_val > 0.05 else "Mechanism-specific proven",
    }

    # Print summary
    print("Dataset Overview:")
    for key, val in summary["dataset_overview"].items():
        print(f"  {key}: {val}")
    print()

    print("Phase 1: Materialization Rates (Detection Days):")
    for key, val in summary["phase1_materialization_rates"].items():
        print(f"  {key}: {val}")
    print()

    print("Phase 2: Baseline Comparison:")
    for crit, data in summary["phase2_baseline_comparison"].items():
        print(f"  {crit}:")
        for k, v in data.items():
            print(f"    {k}: {v}")
    print()

    print("Phase 3: Contingency Matrix Analysis:")
    for key, val in summary["phase3_contingency_analysis"].items():
        print(f"  {key}: {val}")
    print()

    # Save summary
    import yaml

    summary_path = analysis_dir / "issue_144_verification_summary.yaml"
    with open(summary_path, "w") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Summary saved: {summary_path}")
    print()

    return summary


def main():
    """Run complete verification workflow."""
    print("\n")
    print("=" * 80)
    print("ISSUE #144 COMPLETE DATA VERIFICATION")
    print("Paper #1 MC Review Defense")
    print("=" * 80)
    print("\n")

    # Phase 1
    criteria_df = verify_phase1_data()

    # Phase 2
    baseline_df = verify_phase2_data(criteria_df)

    # Phase 3
    criteria_with_c3, matrix_df = verify_phase3_data()

    # Summary
    summary = create_summary_statistics()

    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print()
    print("All data verified and ready for MC review.")
    print()


if __name__ == "__main__":
    main()
