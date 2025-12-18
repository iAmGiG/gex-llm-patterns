#!/usr/bin/env python3
"""Generate shuffled windows for Phase 2a negative control testing.

Purpose: Validate that LLM doesn't detect false regimes in randomized data.

Method:
1. Take real 30-day GEX sequences from Q1 2024
2. Randomly shuffle the day order (destroys temporal structure)
3. Preserve all negative control metadata
4. Output in same format as validate_regime_windows.py

Expected Results: <10% false positive detection rate (should mostly reject as "transitional")

Related: Issue #89 (30-day regime detection), validation_phases.md (Phase 2a)
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import yaml

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_CACHE = PROJECT_ROOT / ".cache"


def get_gex_sequence(db_path: str, end_date: str, window_size: int = 30) -> dict:
    """Fetch GEX sequence for a specific window end date.

    Args:
        db_path: Path to consolidated_historical.db
        end_date: Window end date (YYYY-MM-DD)
        window_size: Default 30 days

    Returns:
        Dict with dates, gex_values, trading_days, and raw_data
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get end date as datetime
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    # Extra margin for weekends/holidays
    start_dt = end_dt - timedelta(days=window_size * 1.5)

    # Fetch GEX data
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

    return {"dates": dates, "gex_values": gex_values, "end_date": end_date, "window_size": len(dates), "raw_data": rows}


def shuffle_gex_sequence(gex_sequence: dict) -> dict:
    """Shuffle a GEX sequence while preserving metadata.

    Destroys temporal structure by randomizing day order.
    This breaks any regime persistence that exists in the real data.

    Args:
        gex_sequence: Dict from get_gex_sequence()

    Returns:
        Dict with shuffled data, marked as "control_type: shuffled"
    """
    # Shuffle indices
    indices = list(range(len(gex_sequence["gex_values"])))
    random.shuffle(indices)

    # Reorder values
    shuffled_gex = [gex_sequence["gex_values"][i] for i in indices]
    shuffled_dates = [f"Day T-{30-i}" for i in range(30)]  # Obfuscated format

    return {
        "control_type": "shuffled",
        "original_end_date": gex_sequence["end_date"],
        "original_dates": gex_sequence["dates"],
        "shuffled_gex_values": shuffled_gex,
        "obfuscated_dates": shuffled_dates,
        "window_size": len(shuffled_gex),
        "note": "Day order randomized to destroy temporal structure",
    }


def generate_phase2a_windows(
    db_path: str, q1_2024_end_dates: list, sampling_interval: int = 5, num_windows: int = 10
) -> list:
    """Generate Phase 2a shuffled windows.

    Args:
        db_path: Path to database
        q1_2024_end_dates: List of all Q1 2024 trading dates
        sampling_interval: Sample every N days (5-10 recommended for efficiency)
        num_windows: Target number of shuffled windows

    Returns:
        List of shuffled window dicts
    """
    shuffled_windows = []

    # Sample every 5-10 days
    sampled_dates = q1_2024_end_dates[::sampling_interval][:num_windows]

    for end_date in sampled_dates:
        print(f"Generating shuffled window: {end_date}")

        # Get real sequence
        gex_seq = get_gex_sequence(db_path, end_date, window_size=30)

        if not gex_seq or gex_seq["window_size"] < 30:
            print(f"  ⚠️  Skipping {end_date}: insufficient data")
            continue

        # Shuffle it
        shuffled = shuffle_gex_sequence(gex_seq)
        shuffled_windows.append(shuffled)

    return shuffled_windows


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
    """Generate Phase 2a shuffled windows and output to YAML."""

    db_path = DATA_CACHE / "consolidated_historical.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return

    print("Phase 2a: Generating Shuffled Windows")
    print("=" * 60)

    # Load Q1 2024 dates
    q1_dates = load_q1_2024_dates(str(db_path))
    print(f"Q1 2024: {len(q1_dates)} trading days")
    print(f"Date range: {q1_dates[0]} to {q1_dates[-1]}")

    # Generate shuffled windows (every 5 days for efficiency)
    shuffled_windows = generate_phase2a_windows(str(db_path), q1_dates, sampling_interval=5, num_windows=10)

    print(f"\nGenerated {len(shuffled_windows)} shuffled windows")

    # Output structure
    output = {
        "metadata": {
            "phase": "Phase 2a - Shuffled Windows",
            "purpose": "Validate no false positives in randomized data",
            "dataset": "Q1 2024 (61 trading days)",
            "windows_generated": len(shuffled_windows),
            "sampling_strategy": "Every 5 days for efficiency",
            "generated_at": datetime.now().isoformat(),
        },
        "expected_results": {
            "detection_rate_pct": "0-10% (false positive threshold)",
            "expected_regime_type": "transitional (sign flips from shuffling)",
            "pass_criteria": "<10% false positive rate",
        },
        "shuffled_windows": shuffled_windows,
        "next_steps": "Run through validate_regime_windows.py with LLM classification",
    }

    # Save to YAML
    output_dir = PROJECT_ROOT / "reports" / "validation" / "regime_windows" / "phase2a_shuffled"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "shuffled_windows.yaml"

    with open(output_file, "w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Output saved to: {output_file}")
    print("\nNext step: Feed shuffled windows through validate_regime_windows.py")


if __name__ == "__main__":
    main()
