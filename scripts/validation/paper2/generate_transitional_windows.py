#!/usr/bin/env python3
"""Generate transitional windows for Phase 2b negative control testing.

Purpose: Validate that LLM correctly rejects windows with frequent sign flips.

Method:
1. Find or create 30-day windows with 7-10 sign flips
2. Preserve magnitude and structure
3. Output in same format as validate_regime_windows.py

Expected Results: 0-10% detection rate (should classify as "transitional")

Characteristics of transitional windows:
- Sign persistence: 50-65% (15-20 days same sign)
- Sign flips: 7-10 flips
- Magnitude: May be adequate (>$5B) but direction unstable

Related: Issue #89 (30-day regime detection), validation_phases.md (Phase 2b)
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


def create_synthetic_transitional(gex_sequence: dict, flip_count: int = 8) -> dict:
    """Create transitional window by splicing positive and negative periods.

    Strategy:
    - Take real persistent sequence
    - Artificially introduce sign flips by replacing some days with opposite sign
    - Preserve magnitude profile but create frequent direction changes
    """
    gex_values = gex_sequence["gex_values"].copy()
    dates = gex_sequence["dates"].copy()

    # Count existing flips
    current_flips = count_sign_flips(gex_values)

    if current_flips >= flip_count - 2:
        # Already has enough flips, use as-is
        return {
            "method": "natural_transitional",
            "source": gex_sequence["end_date"],
            "gex_values": gex_values,
            "obfuscated_dates": [f"Day T-{30-i}" for i in range(30)],
            "characteristics": {
                "persistence_pct": calculate_persistence(gex_values),
                "sign_flips": count_sign_flips(gex_values),
                "avg_magnitude_b": np.mean(np.abs(gex_values)) / 1e9,
            },
        }

    # Splice positive and negative periods
    # Find where positives and negatives are located
    half = len(gex_values) // 2

    # Create alternating sign pattern
    synthetic = gex_values.copy()
    for i in range(5, min(25, len(synthetic)), 3):
        # Flip sign while preserving magnitude
        synthetic[i] = -abs(synthetic[i]) if synthetic[i] > 0 else abs(synthetic[i])

    return {
        "method": "synthetic_spliced",
        "source": gex_sequence["end_date"],
        "gex_values": synthetic,
        "obfuscated_dates": [f"Day T-{30-i}" for i in range(30)],
        "original_values": gex_values,
        "characteristics": {
            "persistence_pct": calculate_persistence(synthetic),
            "sign_flips": count_sign_flips(synthetic),
            "avg_magnitude_b": np.mean(np.abs(synthetic)) / 1e9,
            "note": "Spliced to create frequent sign changes while preserving magnitude",
        },
    }


def find_transitional_windows(
    db_path: str,
    q1_2024_dates: list,
    min_flips: int = 7,
    max_flips: int = 10,
    sampling_interval: int = 5,
    num_windows: int = 10,
) -> list:
    """Find or generate Phase 2b transitional windows.

    Strategy: First try to find natural transitional windows in the data.
    If not enough exist, create synthetic ones by splicing.
    """
    transitional_windows = []
    found_natural = 0
    created_synthetic = 0

    # Sample every 5-10 days
    sampled_dates = q1_2024_dates[::sampling_interval][: num_windows * 2]

    for end_date in sampled_dates:
        if len(transitional_windows) >= num_windows:
            break

        gex_seq = get_gex_sequence(db_path, end_date, window_size=30)

        if not gex_seq or gex_seq["window_size"] < 30:
            continue

        flips = count_sign_flips(gex_seq["gex_values"])
        persistence = calculate_persistence(gex_seq["gex_values"])

        # Check if naturally transitional
        if min_flips <= flips <= max_flips and persistence < 70:
            print(f"Found natural transitional: {end_date} ({flips} flips, {persistence:.1f}% persistence)")
            transitional = create_synthetic_transitional(gex_seq, flip_count=flips)
            transitional["type"] = "natural"
            transitional_windows.append(transitional)
            found_natural += 1
        elif flips < min_flips:
            # Too stable, create synthetic
            print(f"Creating synthetic from {end_date} ({flips}→8 flips)")
            transitional = create_synthetic_transitional(gex_seq, flip_count=8)
            transitional["type"] = "synthetic"
            transitional_windows.append(transitional)
            created_synthetic += 1

    return transitional_windows, found_natural, created_synthetic


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
    """Generate Phase 2b transitional windows and output to YAML."""

    db_path = DATA_CACHE / "consolidated_historical.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    print("Phase 2b: Generating Transitional Windows")
    print("=" * 60)

    # Load Q1 2024 dates
    q1_dates = load_q1_2024_dates(str(db_path))
    print(f"Q1 2024: {len(q1_dates)} trading days")

    # Find/create transitional windows
    transitional_windows, natural_count, synthetic_count = find_transitional_windows(
        str(db_path), q1_dates, min_flips=7, max_flips=10, sampling_interval=5, num_windows=10
    )

    print(f"\nGenerated {len(transitional_windows)} transitional windows")
    print(f"  - Natural: {natural_count}")
    print(f"  - Synthetic: {synthetic_count}")

    # Output structure
    output = {
        "metadata": {
            "phase": "Phase 2b - Transitional Windows",
            "purpose": "Validate rejection of high-flip windows",
            "dataset": "Q1 2024 (61 trading days)",
            "windows_generated": len(transitional_windows),
            "sampling_strategy": "Every 5 days for efficiency",
            "natural_count": natural_count,
            "synthetic_count": synthetic_count,
            "generated_at": datetime.now().isoformat(),
        },
        "expected_results": {
            "detection_rate_pct": "0-10% (false positive threshold)",
            "expected_regime_type": "transitional (reject due to sign flips)",
            "pass_criteria": "<10% false positive rate",
        },
        "transitional_windows": transitional_windows,
        "next_steps": "Run through validate_regime_windows.py with LLM classification",
    }

    # Save to YAML
    output_dir = PROJECT_ROOT / "reports" / "validation" / "regime_windows" / "phase2b_transitional"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "transitional_windows.yaml"

    with open(output_file, "w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Output saved to: {output_file}")
    print("\nNext step: Feed transitional windows through validate_regime_windows.py")


if __name__ == "__main__":
    main()
