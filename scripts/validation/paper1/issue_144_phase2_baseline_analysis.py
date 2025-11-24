#!/usr/bin/env python3
"""
Issue #144 Phase 2: Baseline Materialization Analysis
Paper #1 MC Review Defense - P-Hacking Refutation

Calculates baseline materialization rates for random non-detection days
and compares to detection days via contingency table + chi-square test.

Uses C1 (Volatility Amplification) and C4 (Range Expansion) only.

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


def load_phase1_results():
    """Load Phase 1 materialization criteria results."""
    data_path = project_root / "docs" / "papers" / "paper1" / "analysis" / "issue_144_materialization_criteria.csv"

    df = pd.read_csv(data_path)

    print(f"Loaded Phase 1 results: {len(df)} pattern-day observations")
    print(f"  Detection days: {df['detected'].sum()}")
    print(f"  Non-detection days: {(~df['detected']).sum()}")

    return df


def sample_baseline_days(df, n_samples=100, seed=42):
    """Sample random non-detection days for baseline comparison.

    Args:
        df: Full dataset with detection status
        n_samples: Number of random days to sample
        seed: Random seed for reproducibility

    Returns:
        DataFrame of sampled baseline days
    """
    print(f"\nSampling {n_samples} random baseline days...")

    # Get all non-detection days
    non_detection = df[df["detected"] == False].copy()

    # Sample without replacement
    np.random.seed(seed)

    if len(non_detection) < n_samples:
        print(f"  ⚠️ Only {len(non_detection)} non-detection days available, using all")
        baseline = non_detection
    else:
        baseline = non_detection.sample(n=n_samples, random_state=seed)

    print(f"  Sampled {len(baseline)} baseline days")
    print(f"  By pattern:")
    for pattern in baseline["pattern_type"].unique():
        n = len(baseline[baseline["pattern_type"] == pattern])
        print(f"    {pattern}: {n}")

    return baseline


def calculate_baseline_rates(baseline_df):
    """Calculate materialization rates for baseline (non-detection) days.

    Returns:
        dict with overall and pattern-specific rates
    """
    print("\n" + "=" * 80)
    print("BASELINE MATERIALIZATION RATES (Non-Detection Days)")
    print("=" * 80)

    results = {}

    # Overall baseline rates
    c1_rate = baseline_df["criterion_1_volatility_amplification"].sum() / len(baseline_df) * 100
    c4_rate = baseline_df["criterion_4_range_expansion"].sum() / len(baseline_df) * 100

    print(f"\nOverall Baseline (n={len(baseline_df)}):")
    print(f"  C1 (Volatility Amplification): {c1_rate:.1f}%")
    print(f"  C4 (Range Expansion): {c4_rate:.1f}%")

    results["overall"] = {"n": len(baseline_df), "c1_rate": c1_rate, "c4_rate": c4_rate}

    # By pattern
    print(f"\nBy Pattern:")
    for pattern in baseline_df["pattern_type"].unique():
        pattern_df = baseline_df[baseline_df["pattern_type"] == pattern]

        c1 = pattern_df["criterion_1_volatility_amplification"].sum()
        c4 = pattern_df["criterion_4_range_expansion"].sum()
        n = len(pattern_df)

        c1_pct = c1 / n * 100 if n > 0 else 0
        c4_pct = c4 / n * 100 if n > 0 else 0

        print(f"  {pattern} (n={n}):")
        print(f"    C1: {c1_pct:.1f}%")
        print(f"    C4: {c4_pct:.1f}%")

        results[pattern] = {"n": n, "c1_rate": c1_pct, "c4_rate": c4_pct}

    return results


def calculate_detection_rates(detection_df):
    """Calculate materialization rates for detection days.

    Returns:
        dict with overall and pattern-specific rates
    """
    print("\n" + "=" * 80)
    print("DETECTION MATERIALIZATION RATES (Detection Days)")
    print("=" * 80)

    results = {}

    # Overall detection rates
    c1_rate = detection_df["criterion_1_volatility_amplification"].sum() / len(detection_df) * 100
    c4_rate = detection_df["criterion_4_range_expansion"].sum() / len(detection_df) * 100

    print(f"\nOverall Detection (n={len(detection_df)}):")
    print(f"  C1 (Volatility Amplification): {c1_rate:.1f}%")
    print(f"  C4 (Range Expansion): {c4_rate:.1f}%")

    results["overall"] = {"n": len(detection_df), "c1_rate": c1_rate, "c4_rate": c4_rate}

    # By pattern
    print(f"\nBy Pattern:")
    for pattern in detection_df["pattern_type"].unique():
        pattern_df = detection_df[detection_df["pattern_type"] == pattern]

        c1 = pattern_df["criterion_1_volatility_amplification"].sum()
        c4 = pattern_df["criterion_4_range_expansion"].sum()
        n = len(pattern_df)

        c1_pct = c1 / n * 100 if n > 0 else 0
        c4_pct = c4 / n * 100 if n > 0 else 0

        print(f"  {pattern} (n={n}):")
        print(f"    C1: {c1_pct:.1f}%")
        print(f"    C4: {c4_pct:.1f}%")

        results[pattern] = {"n": n, "c1_rate": c1_pct, "c4_rate": c4_pct}

    return results


def calculate_lift(detection_rates, baseline_rates):
    """
    Calculate lift: detection rate / baseline rate.

    Returns:
        dict with lift metrics
    """
    print("\n" + "=" * 80)
    print("LIFT ANALYSIS (Detection / Baseline)")
    print("=" * 80)

    lifts = {}

    # Overall lift
    c1_lift = detection_rates["overall"]["c1_rate"] / baseline_rates["overall"]["c1_rate"]
    c4_lift = detection_rates["overall"]["c4_rate"] / baseline_rates["overall"]["c4_rate"]

    print(f"\nOverall Lift:")
    print(f"  C1 (Volatility Amplification): {c1_lift:.2f}x")
    print(f"    Detection: {detection_rates['overall']['c1_rate']:.1f}%")
    print(f"    Baseline: {baseline_rates['overall']['c1_rate']:.1f}%")
    print(f"  C4 (Range Expansion): {c4_lift:.2f}x")
    print(f"    Detection: {detection_rates['overall']['c4_rate']:.1f}%")
    print(f"    Baseline: {baseline_rates['overall']['c4_rate']:.1f}%")

    lifts["overall"] = {"c1_lift": c1_lift, "c4_lift": c4_lift}

    # By pattern
    print(f"\nBy Pattern:")
    patterns = [p for p in detection_rates.keys() if p != "overall"]
    for pattern in patterns:
        if pattern in baseline_rates:
            c1_lift = (
                detection_rates[pattern]["c1_rate"] / baseline_rates[pattern]["c1_rate"]
                if baseline_rates[pattern]["c1_rate"] > 0
                else float("inf")
            )
            c4_lift = (
                detection_rates[pattern]["c4_rate"] / baseline_rates[pattern]["c4_rate"]
                if baseline_rates[pattern]["c4_rate"] > 0
                else float("inf")
            )

            print(f"  {pattern}:")
            print(
                f"    C1 Lift: {c1_lift:.2f}x ({detection_rates[pattern]['c1_rate']:.1f}% vs {baseline_rates[pattern]['c1_rate']:.1f}%)"
            )
            print(
                f"    C4 Lift: {c4_lift:.2f}x ({detection_rates[pattern]['c4_rate']:.1f}% vs {baseline_rates[pattern]['c4_rate']:.1f}%)"
            )

            lifts[pattern] = {"c1_lift": c1_lift, "c4_lift": c4_lift}

    return lifts


def build_contingency_table(detection_df, baseline_df, criterion):
    """Build 2x2 contingency table for chi-square test.

    Rows: Detection status (detected, baseline)
    Cols: Criterion outcome (materialized, not materialized)

    Args:
        criterion: 'criterion_1_volatility_amplification' or 'criterion_4_range_expansion'

    Returns:
        2x2 numpy array
    """
    # Detection days
    det_yes = detection_df[criterion].sum()
    det_no = len(detection_df) - det_yes

    # Baseline days
    base_yes = baseline_df[criterion].sum()
    base_no = len(baseline_df) - base_yes

    # Contingency table
    table = np.array([[det_yes, det_no], [base_yes, base_no]])  # Detection days  # Baseline days

    return table


def chi_square_test(detection_df, baseline_df):
    """Perform chi-square tests for C1 and C4.

    Tests null hypothesis: materialization rate is independent of detection status.
    """
    print("\n" + "=" * 80)
    print("CHI-SQUARE TESTS (Detection vs Baseline)")
    print("=" * 80)

    results = {}

    # C1: Volatility Amplification
    print("\nCriterion 1: Volatility Amplification")
    c1_table = build_contingency_table(detection_df, baseline_df, "criterion_1_volatility_amplification")

    print(f"  Contingency Table:")
    print(f"                Materialized    Not Materialized")
    print(f"  Detection     {c1_table[0,0]:>6}          {c1_table[0,1]:>6}")
    print(f"  Baseline      {c1_table[1,0]:>6}          {c1_table[1,1]:>6}")

    chi2_c1, p_c1, dof_c1, expected_c1 = stats.chi2_contingency(c1_table)

    print(f"\n  Chi-square statistic: {chi2_c1:.3f}")
    print(f"  p-value: {p_c1:.6f} {'***' if p_c1 < 0.001 else '**' if p_c1 < 0.01 else '*' if p_c1 < 0.05 else 'ns'}")
    print(f"  Degrees of freedom: {dof_c1}")
    print(f"  Significant: {'Yes' if p_c1 < 0.05 else 'No'}")

    results["c1"] = {"chi2": chi2_c1, "p_value": p_c1, "significant": p_c1 < 0.05, "table": c1_table}

    # C4: Range Expansion
    print("\n" + "-" * 80)
    print("\nCriterion 4: Range Expansion")
    c4_table = build_contingency_table(detection_df, baseline_df, "criterion_4_range_expansion")

    print(f"  Contingency Table:")
    print(f"                Materialized    Not Materialized")
    print(f"  Detection     {c4_table[0,0]:>6}          {c4_table[0,1]:>6}")
    print(f"  Baseline      {c4_table[1,0]:>6}          {c4_table[1,1]:>6}")

    chi2_c4, p_c4, dof_c4, expected_c4 = stats.chi2_contingency(c4_table)

    print(f"\n  Chi-square statistic: {chi2_c4:.3f}")
    print(f"  p-value: {p_c4:.6f} {'***' if p_c4 < 0.001 else '**' if p_c4 < 0.01 else '*' if p_c4 < 0.05 else 'ns'}")
    print(f"  Degrees of freedom: {dof_c4}")
    print(f"  Significant: {'Yes' if p_c4 < 0.05 else 'No'}")

    results["c4"] = {"chi2": chi2_c4, "p_value": p_c4, "significant": p_c4 < 0.05, "table": c4_table}

    return results


def main():
    """Main workflow for Issue #144 Phase 2."""

    print("=" * 80)
    print("Issue #144 Phase 2: Baseline Materialization Analysis")
    print("Paper #1 MC Review Defense - P-Hacking Refutation")
    print("=" * 80)
    print()

    # Paths
    output_dir = project_root / "docs" / "papers" / "paper1" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Load Phase 1 results
    print("Step 1: Loading Phase 1 results...")
    df = load_phase1_results()
    print()

    # Step 2: Sample baseline days
    print("Step 2: Sampling baseline days...")
    baseline_df = sample_baseline_days(df, n_samples=100, seed=42)
    print()

    # Step 3: Split detection vs baseline
    print("Step 3: Splitting detection vs baseline...")
    detection_df = df[df["detected"] == True].copy()
    print(f"  Detection days: {len(detection_df)}")
    print(f"  Baseline days: {len(baseline_df)}")
    print()

    # Step 4: Calculate rates
    print("Step 4: Calculating materialization rates...")
    detection_rates = calculate_detection_rates(detection_df)
    baseline_rates = calculate_baseline_rates(baseline_df)

    # Step 5: Calculate lift
    print("\nStep 5: Calculating lift...")
    lifts = calculate_lift(detection_rates, baseline_rates)

    # Step 6: Chi-square tests
    print("\nStep 6: Running chi-square tests...")
    chi_square_results = chi_square_test(detection_df, baseline_df)

    # Step 7: Save results
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)

    # Save comparison summary
    summary = {
        "detection": detection_rates,
        "baseline": baseline_rates,
        "lift": lifts,
        "chi_square": chi_square_results,
    }

    import yaml as yaml_lib

    summary_path = output_dir / "issue_144_phase2_summary.yaml"
    with open(summary_path, "w") as f:
        # Convert numpy types to Python native types for YAML serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.bool_, np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            else:
                return obj

        summary_serializable = convert_numpy(summary)
        yaml_lib.dump(summary_serializable, f, default_flow_style=False, sort_keys=False)

    print(f"  Saved: {summary_path}")

    # Save baseline sample
    baseline_path = output_dir / "issue_144_baseline_sample.csv"
    baseline_df.to_csv(baseline_path, index=False)
    print(f"  Saved: {baseline_path}")

    print()
    print("=" * 80)
    print("PHASE 2 COMPLETE")
    print("=" * 80)
    print()
    print("Key Findings:")
    print(f"  1. C1 Lift: {lifts['overall']['c1_lift']:.2f}x (p={chi_square_results['c1']['p_value']:.6f})")
    print(f"  2. C4 Lift: {lifts['overall']['c4_lift']:.2f}x (p={chi_square_results['c4']['p_value']:.6f})")
    print()
    print("Interpretation:")
    if chi_square_results["c1"]["significant"] or chi_square_results["c4"]["significant"]:
        print("  ✅ Detection days show significantly different materialization rates")
        print("  ✅ Refutes p-hacking: patterns predict real outcomes, not noise")
    else:
        print("  ⚠️ No significant difference found")
        print("  ⚠️ May need to revisit criteria or increase sample size")
    print()

    return summary


if __name__ == "__main__":
    summary = main()
