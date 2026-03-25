"""
Sensitivity Analysis for Regime Classification Thresholds

Re-classifies all 1,412 cached regime windows under varying threshold
combinations to demonstrate robustness of the three classification
parameters: persistence (%), magnitude ($B), and max sign flips.

Data source: .cache/research_cache.db (llm_detections table)
No LLM re-runs needed — uses stored structured_output metrics.

Related: GitHub Issue #114 / ISSUES_TO_CREATE Issue #3
Output: reports/validation/sensitivity_analysis/
"""

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DB = PROJECT_ROOT / ".cache" / "research_cache.db"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "validation" / "sensitivity_analysis"


def load_windows():
    """Load all 1,412 regime windows from research cache."""
    conn = sqlite3.connect(str(CACHE_DB))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT trading_date, detected, confidence, structured_output
        FROM llm_detections
        WHERE structured_output IS NOT NULL
        ORDER BY trading_date
    """)
    rows = cursor.fetchall()
    conn.close()

    windows = []
    for date, detected, confidence, so_json in rows:
        so = json.loads(so_json)
        windows.append({
            "date": date,
            "year": int(date[:4]),
            "llm_detected": bool(detected),
            "confidence": confidence,
            "persistence_pct": so["persistence_pct"],
            "avg_magnitude_b": so["avg_magnitude_billions"],
            "sign_flips": so["sign_flips"],
            "positive_days": so["positive_days"],
            "negative_days": so["negative_days"],
            "regime_type": so["regime_type"],
        })
    return windows


def classify_window(w, persist_thresh, mag_thresh_b, max_flips):
    """Re-classify a window under given thresholds."""
    min_days = int(30 * persist_thresh)
    is_persistent = (
        (w["positive_days"] >= min_days or w["negative_days"] >= min_days)
        and w["avg_magnitude_b"] >= mag_thresh_b
        and w["sign_flips"] <= max_flips
    )
    return is_persistent


def run_sensitivity(windows):
    """Run all four sensitivity tests from Issue #114."""
    # Default thresholds
    DEFAULT_PERSIST = 0.70
    DEFAULT_MAG = 5.0  # $B
    DEFAULT_FLIPS = 5

    results = {}

    # --- Test 1: Persistence Threshold ---
    persist_values = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    test1 = {"parameter": "persistence_threshold", "values": {}}
    for p in persist_values:
        by_year = {}
        for year in range(2020, 2026):
            year_wins = [w for w in windows if w["year"] == year]
            detected = sum(1 for w in year_wins
                          if classify_window(w, p, DEFAULT_MAG, DEFAULT_FLIPS))
            total = len(year_wins)
            by_year[year] = {
                "detected": detected,
                "total": total,
                "rate": round(detected / total * 100, 1) if total else 0,
            }
        # Effect size: 2024 vs 2020
        r24 = by_year[2024]["rate"]
        r20 = by_year[2020]["rate"]
        test1["values"][f"{p:.0%}"] = {
            "by_year": by_year,
            "effect_size_pp": round(r24 - r20, 1),
            "discrimination_2024_vs_2020": f"{r24:.1f}% vs {r20:.1f}%",
        }
    results["test1_persistence"] = test1

    # --- Test 2: Magnitude Threshold ---
    mag_values = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
    test2 = {"parameter": "magnitude_threshold_billions", "values": {}}
    for m in mag_values:
        by_year = {}
        for year in range(2020, 2026):
            year_wins = [w for w in windows if w["year"] == year]
            detected = sum(1 for w in year_wins
                          if classify_window(w, DEFAULT_PERSIST, m, DEFAULT_FLIPS))
            total = len(year_wins)
            by_year[year] = {
                "detected": detected,
                "total": total,
                "rate": round(detected / total * 100, 1) if total else 0,
            }
        r24 = by_year[2024]["rate"]
        r20 = by_year[2020]["rate"]
        test2["values"][f"${m:.0f}B"] = {
            "by_year": by_year,
            "effect_size_pp": round(r24 - r20, 1),
            "discrimination_2024_vs_2020": f"{r24:.1f}% vs {r20:.1f}%",
        }
    results["test2_magnitude"] = test2

    # --- Test 3: Stability (Max Flips) Threshold ---
    flip_values = [2, 3, 4, 5, 6, 7, 8, 10]
    test3 = {"parameter": "max_sign_flips", "values": {}}
    for f in flip_values:
        by_year = {}
        for year in range(2020, 2026):
            year_wins = [w for w in windows if w["year"] == year]
            detected = sum(1 for w in year_wins
                          if classify_window(w, DEFAULT_PERSIST, DEFAULT_MAG, f))
            total = len(year_wins)
            by_year[year] = {
                "detected": detected,
                "total": total,
                "rate": round(detected / total * 100, 1) if total else 0,
            }
        r24 = by_year[2024]["rate"]
        r20 = by_year[2020]["rate"]
        test3["values"][f"{f} flips"] = {
            "by_year": by_year,
            "effect_size_pp": round(r24 - r20, 1),
            "discrimination_2024_vs_2020": f"{r24:.1f}% vs {r20:.1f}%",
        }
    results["test3_stability"] = test3

    # --- Test 4: Combined Relaxation/Tightening ---
    test4 = {"parameter": "combined_threshold_shift", "values": {}}
    shifts = [
        ("-20%", 0.56, 4.0, 6),
        ("-10%", 0.63, 4.5, 6),
        ("default", 0.70, 5.0, 5),
        ("+10%", 0.77, 5.5, 5),
        ("+20%", 0.84, 6.0, 4),
    ]
    for label, p, m, f in shifts:
        by_year = {}
        for year in range(2020, 2026):
            year_wins = [w for w in windows if w["year"] == year]
            detected = sum(1 for w in year_wins
                          if classify_window(w, p, m, f))
            total = len(year_wins)
            by_year[year] = {
                "detected": detected,
                "total": total,
                "rate": round(detected / total * 100, 1) if total else 0,
            }
        r24 = by_year[2024]["rate"]
        r20 = by_year[2020]["rate"]
        test4["values"][label] = {
            "thresholds": {"persistence": p, "magnitude_b": m, "max_flips": f},
            "by_year": by_year,
            "effect_size_pp": round(r24 - r20, 1),
            "discrimination_2024_vs_2020": f"{r24:.1f}% vs {r20:.1f}%",
        }
    results["test4_combined"] = test4

    return results


def print_summary(results):
    """Print human-readable summary to stdout."""
    print("=" * 70)
    print("SENSITIVITY ANALYSIS: Regime Classification Thresholds")
    print("=" * 70)

    # Test 1: Persistence
    print("\nTest 1: Persistence Threshold (default=70%)")
    print(f"{'Threshold':>10} | {'2020':>6} | {'2021':>6} | {'2022':>6} | "
          f"{'2023':>6} | {'2024':>6} | {'2025':>6} | {'Effect':>8}")
    print("-" * 70)
    for label, data in results["test1_persistence"]["values"].items():
        by = data["by_year"]
        print(f"{label:>10} | {by[2020]['rate']:5.1f}% | {by[2021]['rate']:5.1f}% | "
              f"{by[2022]['rate']:5.1f}% | {by[2023]['rate']:5.1f}% | "
              f"{by[2024]['rate']:5.1f}% | {by[2025]['rate']:5.1f}% | "
              f"{data['effect_size_pp']:+6.1f}pp")

    # Test 2: Magnitude
    print("\nTest 2: Magnitude Threshold (default=$5B)")
    print(f"{'Threshold':>10} | {'2020':>6} | {'2021':>6} | {'2022':>6} | "
          f"{'2023':>6} | {'2024':>6} | {'2025':>6} | {'Effect':>8}")
    print("-" * 70)
    for label, data in results["test2_magnitude"]["values"].items():
        by = data["by_year"]
        print(f"{label:>10} | {by[2020]['rate']:5.1f}% | {by[2021]['rate']:5.1f}% | "
              f"{by[2022]['rate']:5.1f}% | {by[2023]['rate']:5.1f}% | "
              f"{by[2024]['rate']:5.1f}% | {by[2025]['rate']:5.1f}% | "
              f"{data['effect_size_pp']:+6.1f}pp")

    # Test 3: Stability
    print("\nTest 3: Max Sign Flips (default=5)")
    print(f"{'Threshold':>10} | {'2020':>6} | {'2021':>6} | {'2022':>6} | "
          f"{'2023':>6} | {'2024':>6} | {'2025':>6} | {'Effect':>8}")
    print("-" * 70)
    for label, data in results["test3_stability"]["values"].items():
        by = data["by_year"]
        print(f"{label:>10} | {by[2020]['rate']:5.1f}% | {by[2021]['rate']:5.1f}% | "
              f"{by[2022]['rate']:5.1f}% | {by[2023]['rate']:5.1f}% | "
              f"{by[2024]['rate']:5.1f}% | {by[2025]['rate']:5.1f}% | "
              f"{data['effect_size_pp']:+6.1f}pp")

    # Test 4: Combined
    print("\nTest 4: Combined Threshold Shift")
    print(f"{'Shift':>10} | {'Persist':>7} | {'Mag':>5} | {'Flips':>5} | "
          f"{'2020':>6} | {'2024':>6} | {'Effect':>8}")
    print("-" * 70)
    for label, data in results["test4_combined"]["values"].items():
        t = data["thresholds"]
        by = data["by_year"]
        print(f"{label:>10} | {t['persistence']:6.0%} | ${t['magnitude_b']:.0f}B | "
              f"{t['max_flips']:5d} | {by[2020]['rate']:5.1f}% | "
              f"{by[2024]['rate']:5.1f}% | {data['effect_size_pp']:+6.1f}pp")

    # Overall robustness summary
    print("\n" + "=" * 70)
    print("ROBUSTNESS SUMMARY")
    print("=" * 70)

    # Check if effect size remains large across all tests
    all_effects = []
    for test_key in ["test1_persistence", "test2_magnitude",
                     "test3_stability", "test4_combined"]:
        for label, data in results[test_key]["values"].items():
            all_effects.append(data["effect_size_pp"])

    print(f"Effect size range: {min(all_effects):+.1f}pp to {max(all_effects):+.1f}pp")
    print(f"Mean effect size: {np.mean(all_effects):+.1f}pp")
    print(f"All positive: {all(e > 0 for e in all_effects)}")
    print(f"All >30pp: {all(e > 30 for e in all_effects)}")


def main():
    print(f"Loading windows from {CACHE_DB}...")
    windows = load_windows()
    print(f"Loaded {len(windows)} windows across "
          f"{len(set(w['year'] for w in windows))} years")

    results = run_sensitivity(windows)
    print_summary(results)

    # Save YAML output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "threshold_sensitivity.yaml"

    # Convert to serializable format
    def make_serializable(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [make_serializable(v) for v in obj]
        return obj

    with open(output_path, "w") as f:
        yaml.dump(make_serializable(results), f, default_flow_style=False,
                  sort_keys=False, width=120)

    print(f"\nResults saved to {output_path}")
    return results


if __name__ == "__main__":
    main()
