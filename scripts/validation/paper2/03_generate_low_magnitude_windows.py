#!/usr/bin/env python3
"""Generate low-magnitude windows for Phase 2c negative control testing.

Purpose: Validate that LLM correctly rejects persistent-sign but weak-magnitude windows.

Method:
1. Take real persistent window (26/30 days same sign, $8B avg)
2. Scale GEX values down: multiply by 0.3 → now $2.4B avg
3. Present scaled window to LLM
4. Should reject as "low_conviction" despite sign persistence

Expected Results: 0-10% detection rate (should classify as "low_conviction")

Characteristics of low-magnitude windows:
- Sign persistence: 70-90% (21-27 days same sign) ✅
- Sign flips: 0-3 (very stable) ✅
- Magnitude: <$3B average ❌ (below $5B threshold)

Related: Issue #89 (30-day regime detection), validation_phases.md (Phase 2c)
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import yaml

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_CACHE = PROJECT_ROOT / ".cache"


def count_sign_flips(gex_values: list) -> int:
    """Count number of sign changes in a sequence."""
    flips = 0
    for i in range(len(gex_values) - 1):
        if (gex_values[i] > 0 and gex_values[i + 1] < 0) or (gex_values[i] < 0 and gex_values[i + 1] > 0):
            flips += 1
    return flips


def calculate_persistence(gex_values: list) -> float:
    """Calculate percentage of days with same sign as majority."""
    positive_count = sum(1 for x in gex_values if x > 0)
    negative_count = len(gex_values) - positive_count

    if positive_count > negative_count:
        return (positive_count / len(gex_values)) * 100
    else:
        return (negative_count / len(gex_values)) * 100


def get_gex_sequence(db_path: str, end_date: str, window_size: int = 30) -> dict:
    """Fetch GEX sequence for a specific window end date."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=window_size * 1.5)

    query = """
    SELECT date, net_gex_usd
    FROM gex_data
    WHERE symbol = 'SPY'
        AND date >= ? AND date <= ?
    ORDER BY date ASC
    """

    cursor.execute(query, (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    # Keep only the last 30 trading days
    rows = rows[-window_size:]
    dates = [row[0] for row in rows]
    gex_values = [row[1] for row in rows]

    return {
        "dates": dates,
        "gex_values": gex_values,
        "end_date": end_date,
        "window_size": len(dates),
    }


def scale_to_low_magnitude(gex_sequence: dict, scale_factor: float = 0.3, target_magnitude_b: float = 2.4) -> dict:
    """Scale GEX values to low magnitude while preserving sign persistence.

    Args:
        gex_sequence: Original sequence
        scale_factor: Scale factor (0.3 = 30% of original)
        target_magnitude_b: Target average magnitude in billions

    Returns:
        Dict with scaled values marked as "control_type: low_magnitude"
    """
    original_values = gex_sequence["gex_values"]
    original_magnitude = np.mean(np.abs(original_values))

    # Scale to achieve target magnitude
    actual_scale = target_magnitude_b * 1e9 / original_magnitude if original_magnitude > 0 else scale_factor

    scaled_values = [v * actual_scale for v in original_values]

    return {
        "control_type": "low_magnitude",
        "original_end_date": gex_sequence["end_date"],
        "original_dates": gex_sequence["dates"],
        "scaled_gex_values": scaled_values,
        "obfuscated_dates": [f"Day T-{30-i}" for i in range(30)],
        "scaling_info": {
            "original_avg_magnitude_b": original_magnitude / 1e9,
            "scaled_avg_magnitude_b": np.mean(np.abs(scaled_values)) / 1e9,
            "scale_factor": actual_scale,
            "target_magnitude_b": target_magnitude_b,
        },
        "characteristics": {
            "persistence_pct": calculate_persistence(scaled_values),
            "sign_flips": count_sign_flips(scaled_values),
            "magnitude_status": "WEAK (<$3B threshold)",
        },
        "window_size": len(scaled_values),
        "note": "Sign persistence preserved but magnitude scaled to <$3B (below $5B regime threshold)",
    }


def find_low_magnitude_windows(
    db_path: str,
    q1_2024_dates: list,
    persistence_threshold: float = 70,
    sampling_interval: int = 5,
    num_windows: int = 10,
) -> list:
    """Find and scale windows to low magnitude.

    Strategy: Find windows with high persistence (>70%), then scale down.
    """
    low_mag_windows = []

    # Sample every 5-10 days
    sampled_dates = q1_2024_dates[::sampling_interval][: num_windows * 2]

    for end_date in sampled_dates:
        if len(low_mag_windows) >= num_windows:
            break

        gex_seq = get_gex_sequence(db_path, end_date, window_size=30)

        if not gex_seq or gex_seq["window_size"] < 30:
            continue

        persistence = calculate_persistence(gex_seq["gex_values"])
        flips = count_sign_flips(gex_seq["gex_values"])
        magnitude = np.mean(np.abs(gex_seq["gex_values"])) / 1e9

        # Check if suitable for scaling (high persistence, low flips, but currently high magnitude)
        if persistence >= persistence_threshold and flips <= 3 and magnitude > 4:
            print(f"Found persistent window: {end_date} ({persistence:.1f}% persistence, {magnitude:.2f}B)")

            # Scale it down
            low_mag = scale_to_low_magnitude(gex_seq, target_magnitude_b=2.4)
            low_mag_windows.append(low_mag)
            print(f"  → Scaled to {low_mag['scaling_info']['scaled_avg_magnitude_b']:.2f}B")

    return low_mag_windows


def load_q1_2024_dates(db_path: str) -> list:
    """Load all Q1 2024 trading dates from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT date
    FROM gex_data
    WHERE symbol = 'SPY'
        AND date >= '2024-01-02' AND date <= '2024-03-29'
    ORDER BY date ASC
    """

    cursor.execute(query)
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()

    return dates


def main():
    """Generate Phase 2c low-magnitude windows and output to YAML."""

    db_path = DATA_CACHE / "consolidated_historical.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    print("Phase 2c: Generating Low-Magnitude Windows")
    print("=" * 60)

    # Load Q1 2024 dates
    q1_dates = load_q1_2024_dates(str(db_path))
    print(f"Q1 2024: {len(q1_dates)} trading days")

    # Find and scale windows
    low_mag_windows = find_low_magnitude_windows(
        str(db_path), q1_dates, persistence_threshold=70, sampling_interval=5, num_windows=10
    )

    print(f"\nGenerated {len(low_mag_windows)} low-magnitude windows")

    # Output structure
    output = {
        "metadata": {
            "phase": "Phase 2c - Low-Magnitude Persistent Windows",
            "purpose": "Validate magnitude threshold enforcement",
            "dataset": "Q1 2024 (61 trading days)",
            "windows_generated": len(low_mag_windows),
            "sampling_strategy": "Every 5 days for efficiency",
            "generated_at": datetime.now().isoformat(),
        },
        "expected_results": {
            "detection_rate_pct": "0-10% (false positive threshold)",
            "expected_regime_type": "low_conviction (persistent sign but weak magnitude)",
            "pass_criteria": "<10% false positive rate",
        },
        "scaling_strategy": {
            "approach": "Take high-persistence windows, scale GEX values down",
            "source_persistence": "70-90% days same sign",
            "source_flips": "0-3 sign flips",
            "scaled_magnitude": "<$3B average",
            "rationale": "Tests if LLM enforces magnitude threshold despite sign persistence",
        },
        "low_magnitude_windows": low_mag_windows,
        "next_steps": "Run through validate_regime_windows.py with LLM classification",
    }

    # Save to YAML
    output_dir = PROJECT_ROOT / "reports" / "validation" / "regime_windows" / "phase2c_low_magnitude"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "low_magnitude_windows.yaml"

    with open(output_file, "w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Output saved to: {output_file}")
    print("\nNext step: Feed low-magnitude windows through validate_regime_windows.py")


if __name__ == "__main__":
    main()
