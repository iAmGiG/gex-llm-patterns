#!/usr/bin/env python3
"""Run Baseline Comparison for Issue #58 Compares LLM-filtered dealer gamma hedging strategy against naive baselines."""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analysis.baseline_comparison import BaselineComparison

logger = logging.getLogger(__name__)


def main():
    """Run baseline comparison analysis."""
    parser = argparse.ArgumentParser(description="Compare LLM pattern strategy vs baseline strategies")
    parser.add_argument(
        "--db-path",
        type=str,
        default=".cache/consolidated_historical.db",
        help="Path to database (default: .cache/consolidated_historical.db)",
    )
    parser.add_argument("--start-date", type=str, default="2024-01-02", help="Start date (default: 2024-01-02)")
    parser.add_argument("--end-date", type=str, default="2024-03-29", help="End date (default: 2024-03-29)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    print("=" * 80)
    print("BASELINE COMPARISON ANALYSIS - Issue #58")
    print("=" * 80)
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Database: {args.db_path}")
    print()
    print("Comparing strategies:")
    print("  1. Buy & Hold")
    print("  2. Simple GEX (trade every negative GEX day)")
    print("  3. Random Baseline")
    print("  4. Dealer Gamma Hedging (LLM-filtered, ≥85% confidence)")
    print("  5. Always Long")
    print("  6. Always Short")
    print()
    print("=" * 80)
    print()

    try:
        # Initialize baseline comparison
        comparison = BaselineComparison(args.db_path)

        # Run comparison
        results = comparison.calculate_baselines(start_date=args.start_date, end_date=args.end_date)

        if not results:
            print("❌ No results generated")
            return 1

        print()
        print("=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)

        # Show key takeaway
        pattern_result = results.get("pattern_contrarian", {})
        simple_gex_result = results.get("simple_gex", {})

        if pattern_result.get("trades", 0) > 0:
            print()
            print("🎯 KEY FINDING:")
            print(
                f"  LLM-filtered strategy: {pattern_result['total_return']:.2f}% "
                f"({pattern_result['trades']} trades, {pattern_result['win_rate']:.1f}% win rate)"
            )
            print(
                f"  Simple GEX strategy: {simple_gex_result.get('total_return', 0):.2f}% "
                f"({simple_gex_result.get('trades', 0)} trades, {simple_gex_result.get('win_rate', 0):.1f}% win rate)"
            )

            if pattern_result["total_return"] > simple_gex_result.get("total_return", 0):
                improvement = pattern_result["total_return"] - simple_gex_result.get("total_return", 0)
                print(f"  ✅ LLM filtering adds {improvement:.2f}% incremental return")
            else:
                print(f"  ⚠️  LLM filtering underperformed naive GEX strategy")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Baseline comparison failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
