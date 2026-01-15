#!/usr/bin/env python3
"""Execute Formula Agreement Test for Issue #186/#217.

Compares regime detection using absolute vs normalized GEX formulations.

Usage:
    python scripts/validation/paper2/run_formula_agreement.py [--subset Q1|Q2|Q3|Q4]

Options:
    --subset: Test on specific quarter (default: Q1 = 52 windows)
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from gex_db_infrastructure.validation.formula_agreement_test import FormulaAgreementTester

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONSOLIDATED_DB = PROJECT_ROOT / ".cache" / "consolidated_historical.db"


def get_quarter_dates(year: int, quarter: str) -> tuple:
    """Get start and end dates for a quarter."""
    quarters = {
        "Q1": (f"{year}-01-01", f"{year}-03-31"),
        "Q2": (f"{year}-04-01", f"{year}-06-30"),
        "Q3": (f"{year}-07-01", f"{year}-09-30"),
        "Q4": (f"{year}-10-01", f"{year}-12-31"),
    }
    return quarters[quarter]


def load_gex_data(year: int, quarter: str) -> dict:
    """Load daily GEX data from consolidated database.

    Returns:
        Dict mapping date -> total_gex value
    """
    start_date, end_date = get_quarter_dates(year, quarter)

    # We need 30 days before quarter start for initial windows
    conn = sqlite3.connect(CONSOLIDATED_DB)
    cursor = conn.cursor()

    # Get extended date range (30 days before quarter start)
    extended_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=45)).strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT date, total_gex
        FROM daily_gex_metrics
        WHERE symbol = 'SPY'
          AND date BETWEEN ? AND ?
        ORDER BY date
    """, (extended_start, end_date))

    results = cursor.fetchall()
    conn.close()

    gex_data = {row[0]: row[1] for row in results if row[1] is not None}
    logger.info(f"Loaded {len(gex_data)} days of GEX data ({extended_start} to {end_date})")

    return gex_data


def create_30day_windows(gex_data: dict, year: int, quarter: str) -> dict:
    """Create 30-day rolling windows for the specified quarter.

    Returns:
        Dict mapping window_end_date -> list of 30 GEX values
    """
    start_date, end_date = get_quarter_dates(year, quarter)

    # Sort dates
    sorted_dates = sorted(gex_data.keys())

    windows = {}

    # Find dates within the quarter
    quarter_dates = [d for d in sorted_dates if start_date <= d <= end_date]

    for end_date_str in quarter_dates:
        end_idx = sorted_dates.index(end_date_str)

        if end_idx < 29:  # Need at least 30 days
            continue

        # Get 30-day window
        window_dates = sorted_dates[end_idx - 29:end_idx + 1]
        window_gex = [gex_data[d] for d in window_dates]

        if len(window_gex) == 30 and all(v is not None for v in window_gex):
            windows[end_date_str] = window_gex

    logger.info(f"Created {len(windows)} 30-day windows for {quarter} {year}")
    return windows


def generate_normalized_windows(baseline_windows: dict, global_max: float = None) -> dict:
    """Generate normalized GEX sequences from baseline windows.

    Uses sign-preserving normalization: divides by global max magnitude to
    scale to [-1, +1] while preserving sign structure.

    Args:
        baseline_windows: Dict mapping window_date -> absolute_gex_sequence
        global_max: Maximum magnitude for normalization (computed if None)

    Returns:
        Dict mapping window_date -> normalized_gex_sequence (-1.0 to 1.0 scale)
    """
    logger.info(f"Generating normalized windows for {len(baseline_windows)} baseline windows...")

    # Compute global max magnitude for sign-preserving normalization
    if global_max is None:
        all_values = []
        for sequence in baseline_windows.values():
            all_values.extend(sequence)
        global_max = max(abs(v) for v in all_values if v is not None)

    logger.info(f"Using global max magnitude: ${global_max:.2f}B for normalization")

    normalized_windows = {}

    for window_date, baseline_sequence in baseline_windows.items():
        if not baseline_sequence or len(baseline_sequence) == 0:
            continue

        baseline_array = np.array(baseline_sequence, dtype=float)
        baseline_array = baseline_array[~np.isnan(baseline_array)]

        if len(baseline_array) == 0:
            continue

        # Sign-preserving normalization: divide by global max
        # This preserves sign structure: all-negative stays all-negative
        normalized_sequence = (baseline_array / global_max).tolist()

        # Clip to [-1, 1] just in case
        normalized_sequence = np.clip(normalized_sequence, -1.0, 1.0).tolist()

        normalized_windows[window_date] = normalized_sequence

    logger.info(f"Generated {len(normalized_windows)} normalized windows")
    return normalized_windows


def run_formula_agreement_test(subset: str = "Q1", year: int = 2024):
    """Run the complete formula agreement test.

    Args:
        subset: Quarter to test (Q1, Q2, Q3, Q4)
        year: Year to test (default: 2024)
    """
    logger.info(f"Starting Formula Agreement Test for {subset} {year}...")
    logger.info("-" * 80)

    # Load GEX data
    gex_data = load_gex_data(year, subset)
    if not gex_data:
        logger.error("Failed to load GEX data. Exiting.")
        return None

    # Create 30-day windows
    baseline_windows = create_30day_windows(gex_data, year, subset)
    if not baseline_windows:
        logger.error("Failed to create baseline windows. Exiting.")
        return None

    # Generate normalized windows
    normalized_windows = generate_normalized_windows(baseline_windows)
    if not normalized_windows:
        logger.error("Failed to generate normalized windows. Exiting.")
        return None

    # Run comparison
    logger.info(f"Comparing {len(baseline_windows)} window pairs...")
    tester = FormulaAgreementTester()
    results, agreement_rate = tester.compare_windows(baseline_windows, normalized_windows)

    # Generate report
    report = tester.generate_report(results, agreement_rate)
    print(report)

    # Save results
    output_dir = Path("reports/validation/paper2_formula_agreement")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"formula_agreement_{subset}_{year}_{timestamp}.json"

    results_data = {
        "subset": subset,
        "year": year,
        "test_date": datetime.now().isoformat(),
        "agreement_rate": agreement_rate,
        "total_windows": len(results),
        "agreements": sum(1 for r in results if r.agreement),
        "disagreements": sum(1 for r in results if not r.agreement),
        "results": [
            {
                "window_date": r.window_date,
                "baseline_regime": r.baseline_regime,
                "normalized_regime": r.normalized_regime,
                "baseline_confidence": float(r.baseline_confidence),
                "normalized_confidence": float(r.normalized_confidence),
                "agreement": r.agreement,
            }
            for r in results
        ],
    }

    with open(results_file, "w") as f:
        json.dump(results_data, f, indent=2)

    logger.info(f"Results saved to: {results_file}")
    logger.info(f"Agreement Rate: {agreement_rate:.1%}")

    # Interpretation
    if agreement_rate > 0.90:
        interpretation = "CALCULATION-INDEPENDENT: Formula choice does not materially affect detection"
    elif agreement_rate >= 0.70:
        interpretation = "PARTIALLY DEPENDENT: Magnitude provides some value but is not essential"
    else:
        interpretation = "MAGNITUDE-DEPENDENT: LLM requires absolute dollar values for structural reasoning"

    logger.info(f"\nInterpretation: {interpretation}")

    return {
        "agreement_rate": agreement_rate,
        "total_windows": len(results),
        "interpretation": interpretation,
        "results_file": str(results_file),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Formula Agreement Test for Issue #186/#217")
    parser.add_argument(
        "--subset", choices=["Q1", "Q2", "Q3", "Q4"], default="Q1", help="Quarter to test (default: Q1)"
    )
    parser.add_argument(
        "--year", type=int, default=2024, help="Year to test (default: 2024)"
    )

    args = parser.parse_args()

    try:
        run_formula_agreement_test(args.subset, args.year)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
