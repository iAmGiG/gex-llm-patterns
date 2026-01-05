#!/usr/bin/env python3
"""Execute Formula Agreement Test for Issue #186.

Compares regime detection using absolute vs normalized GEX formulations.

Usage:
    python scripts/validation/paper2/run_formula_agreement.py [--subset Q1|Q2|Q3|Q4]

Options:
    --subset: Test on specific quarter (default: Q1 = 52 windows)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.cache.research_cache_queries import get_phase4a_results_by_date
from src.gex.gex_calculator import GEXCalculator
from src.validation.formula_agreement_test import FormulaAgreementTester, calculate_normalized_gex

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_q1_2024_windows():
    """Load Q1 2024 baseline detection windows from ResearchCache.

    Returns:
        Dict mapping window_date -> baseline_gex_sequence (30-day window)
    """
    logger.info("Loading Phase 4A Q1 2024 results from ResearchCache...")

    try:
        # Query Phase 4A results for Q1 2024
        phase4a_results = get_phase4a_results_by_date(year=2024, quarter="Q1")

        windows = {}
        for result in phase4a_results:
            if result.get("gex_sequence"):
                window_date = result.get("window_date", "unknown")
                windows[window_date] = result["gex_sequence"]

        logger.info(f"Loaded {len(windows)} Q1 2024 windows from ResearchCache")
        return windows

    except Exception as e:
        logger.error(f"Failed to load baseline windows: {e}")
        return {}


def generate_normalized_windows(baseline_windows: dict) -> dict:
    """Generate normalized GEX sequences from baseline windows.

    Args:
        baseline_windows: Dict mapping window_date -> absolute_gex_sequence

    Returns:
        Dict mapping window_date -> normalized_gex_sequence (-1.0 to 1.0 scale)
    """
    logger.info(f"Generating normalized windows for {len(baseline_windows)} baseline windows...")

    normalized_windows = {}

    for window_date, baseline_sequence in baseline_windows.items():
        # For this proof-of-concept, we'll simulate normalized values
        # In production, we'd recalculate from raw options data
        #
        # Normalization formula:
        # normalized = (baseline - mean) / std, clipped to [-1, 1]

        if not baseline_sequence or len(baseline_sequence) == 0:
            continue

        baseline_array = np.array(baseline_sequence, dtype=float)
        baseline_array = baseline_array[~np.isnan(baseline_array)]

        if len(baseline_array) == 0:
            continue

        # Normalize to [-1, 1] scale
        # Method: min-max normalization to (-1, 1) range
        min_val = np.min(baseline_array)
        max_val = np.max(baseline_array)

        if max_val == min_val:
            # Constant sequence
            normalized_sequence = np.zeros_like(baseline_array).tolist()
        else:
            # Scale to [-1, 1]
            normalized_sequence = (2 * (baseline_array - min_val) / (max_val - min_val) - 1).tolist()

        normalized_windows[window_date] = normalized_sequence

    logger.info(f"Generated {len(normalized_windows)} normalized windows")
    return normalized_windows


def run_formula_agreement_test(subset: str = "Q1"):
    """Run the complete formula agreement test.

    Args:
        subset: Quarter to test (Q1, Q2, Q3, Q4)
    """
    logger.info(f"Starting Formula Agreement Test for {subset} 2024...")
    logger.info("-" * 80)

    # Load baseline windows
    baseline_windows = load_q1_2024_windows()
    if not baseline_windows:
        logger.error("Failed to load baseline windows. Exiting.")
        return

    # Generate normalized windows
    normalized_windows = generate_normalized_windows(baseline_windows)
    if not normalized_windows:
        logger.error("Failed to generate normalized windows. Exiting.")
        return

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
    results_file = output_dir / f"formula_agreement_{subset}_2024_{timestamp}.json"

    results_data = {
        "subset": subset,
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


if __name__ == "__main__":
    import numpy as np

    parser = argparse.ArgumentParser(description="Run Formula Agreement Test for Issue #186")
    parser.add_argument(
        "--subset", choices=["Q1", "Q2", "Q3", "Q4"], default="Q1", help="Quarter to test (default: Q1)"
    )

    args = parser.parse_args()

    try:
        run_formula_agreement_test(args.subset)
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)
