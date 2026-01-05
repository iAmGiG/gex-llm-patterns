#!/usr/bin/env python3
"""Batch validation script for all 6 patterns in Issue #79.

Tests each pattern individually and generates a summary report.
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_pattern_validation(
    pattern: str, start_date: str, end_date: str, confidence: float = 60.0, symbol: str = "SPY"
) -> dict:
    """Run validation for a single pattern."""
    logger.info(f"\n{'='*80}")
    logger.info(f"TESTING PATTERN: {pattern}")
    logger.info(f"{'='*80}")

    cmd = [
        "python",
        "scripts/validation/paper1/02_validate_pattern_taxonomy.py",
        "--pattern",
        pattern,
        "--symbol",
        symbol,
        "--start-date",
        start_date,
        "--end-date",
        end_date,
        "--confidence",
        str(confidence),
    ]

    logger.info(f"Running: {' '.join(cmd)}")

    try:
        # Run validation script
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout

        if result.returncode == 0:
            logger.info(f"✅ {pattern} validation completed successfully")
        else:
            logger.warning(f"⚠️  {pattern} validation returned non-zero exit code")

        # Find the generated YAML file
        pattern_dir = Path("reports/validation/paper1_pattern_taxonomy")
        yaml_files = sorted(pattern_dir.glob(f"{pattern}_validation_*.yaml"))

        if yaml_files:
            latest_file = yaml_files[-1]
            logger.info(f"Reading results from: {latest_file}")

            with open(latest_file, "r") as f:
                validation_data = yaml.safe_load(f)

            return {
                "pattern": pattern,
                "file": str(latest_file),
                "success_rate": validation_data["obfuscation_test"]["success_rate"],
                "sample_size": validation_data["obfuscation_test"]["sample_size"],
                "passed": validation_data["obfuscation_test"]["passed"],
                "verdict": validation_data["obfuscation_test"]["verdict"],
                "high_confidence": validation_data["detection_metrics"]["high_confidence_detections"],
                "total_tested": validation_data["detection_metrics"]["total_tested"],
            }
        else:
            logger.error(f"No YAML output found for {pattern}")
            return {
                "pattern": pattern,
                "file": None,
                "success_rate": 0,
                "sample_size": 0,
                "passed": False,
                "verdict": "ERROR - No output file",
                "high_confidence": 0,
                "total_tested": 0,
            }

    except subprocess.TimeoutExpired:
        logger.error(f"❌ {pattern} validation timed out after 1 hour")
        return {
            "pattern": pattern,
            "file": None,
            "success_rate": 0,
            "sample_size": 0,
            "passed": False,
            "verdict": "TIMEOUT",
            "high_confidence": 0,
            "total_tested": 0,
        }
    except Exception as e:
        logger.error(f"❌ Error running {pattern} validation: {e}")
        return {
            "pattern": pattern,
            "file": None,
            "success_rate": 0,
            "sample_size": 0,
            "passed": False,
            "verdict": f"ERROR - {str(e)}",
            "high_confidence": 0,
            "total_tested": 0,
        }


def main():
    """Run validation for all patterns and generate summary."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate all patterns for Issue #79")
    parser.add_argument(
        "--patterns",
        nargs="+",
        default=[
            "gamma_positioning",
            "stock_pinning",
            "0dte_hedging",
            "dealer_trap",
            "friday_330_squeeze",
            "volume_anomaly",
        ],
        help="Patterns to test (default: all 6)",
    )
    parser.add_argument("--symbol", type=str, default="SPY", help="Symbol to test (default: SPY)")
    parser.add_argument("--start-date", type=str, default="2024-01-02", help="Start date (default: 2024-01-02)")
    parser.add_argument("--end-date", type=str, default="2024-03-29", help="End date (default: 2024-03-29)")
    parser.add_argument("--confidence", type=float, default=60.0, help="Confidence threshold (default: 60.0)")
    parser.add_argument(
        "--skip-completed", action="store_true", help="Skip patterns that already have results for this date range"
    )

    args = parser.parse_args()

    results = []

    # Check for existing results if skip-completed is set
    completed_patterns = set()
    if args.skip_completed:
        pattern_dir = Path("reports/validation/paper1_pattern_taxonomy")
        for pattern in args.patterns:
            yaml_files = pattern_dir.glob(f"{pattern}_validation_*.yaml")
            for yaml_file in yaml_files:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                    test_period = data["test_metadata"]["test_period"]
                    if f"{args.start_date} to" in test_period:
                        logger.info(f"⏭️  Skipping {pattern} - already completed")
                        completed_patterns.add(pattern)
                        # Add existing result
                        results.append(
                            {
                                "pattern": pattern,
                                "file": str(yaml_file),
                                "success_rate": data["obfuscation_test"]["success_rate"],
                                "sample_size": data["obfuscation_test"]["sample_size"],
                                "passed": data["obfuscation_test"]["passed"],
                                "verdict": data["obfuscation_test"]["verdict"],
                                "high_confidence": data["detection_metrics"]["high_confidence_detections"],
                                "total_tested": data["detection_metrics"]["total_tested"],
                            }
                        )
                        break

    # Run validation for each pattern
    for pattern in args.patterns:
        if pattern in completed_patterns:
            continue

        result = run_pattern_validation(
            pattern=pattern,
            start_date=args.start_date,
            end_date=args.end_date,
            confidence=args.confidence,
            symbol=args.symbol,
        )
        results.append(result)

    # Generate summary report
    logger.info(f"\n{'='*80}")
    logger.info("VALIDATION SUMMARY - ISSUE #79 PATTERN TAXONOMY")
    logger.info(f"{'='*80}")
    logger.info(f"Test Period: {args.start_date} to {args.end_date}")
    logger.info(f"Symbol: {args.symbol}")
    logger.info(f"Confidence Threshold: {args.confidence}%")
    logger.info(f"\n{'Pattern':<25} {'Success Rate':<15} {'Samples':<10} {'Status':<10} {'Verdict'}")
    logger.info("-" * 80)

    for result in results:
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        logger.info(
            f"{result['pattern']:<25} "
            f"{result['success_rate']:<14.1f}% "
            f"{result['sample_size']:<10} "
            f"{status:<10} "
            f"{result['verdict'][:40]}"
        )

    # Classification summary
    mechanical = [r for r in results if r["passed"] and r["success_rate"] >= 60]
    probabilistic = [r for r in results if 30 <= r["success_rate"] < 60]
    narrative = [r for r in results if r["success_rate"] < 30]

    logger.info(f"\n{'='*80}")
    logger.info("PATTERN CLASSIFICATION")
    logger.info(f"{'='*80}")
    logger.info(f"MECHANICAL (>60%, validated): {len(mechanical)} patterns")
    for r in mechanical:
        logger.info(f"  ✅ {r['pattern']}: {r['success_rate']:.1f}%")

    logger.info(f"\nPROBABILISTIC (30-60%): {len(probabilistic)} patterns")
    for r in probabilistic:
        logger.info(f"  ⚠️  {r['pattern']}: {r['success_rate']:.1f}%")

    logger.info(f"\nNARRATIVE/FOLKLORE (<30%): {len(narrative)} patterns")
    for r in narrative:
        logger.info(f"  ❌ {r['pattern']}: {r['success_rate']:.1f}%")

    # Save summary to YAML
    summary = {
        "test_metadata": {
            "date": datetime.now().isoformat(),
            "symbol": args.symbol,
            "test_period": f"{args.start_date} to {args.end_date}",
            "confidence_threshold": args.confidence,
            "patterns_tested": len(results),
        },
        "pattern_results": results,
        "classification": {
            "mechanical": [r["pattern"] for r in mechanical],
            "probabilistic": [r["pattern"] for r in probabilistic],
            "narrative": [r["pattern"] for r in narrative],
        },
        "issue_79_validation": {
            "total_mechanical_patterns": len(mechanical),
            "target_mechanical_patterns": "5-7",
            "success": len(mechanical) >= 5,
        },
    }

    # Generate summary filename: all_patterns_summary_TICKER_daterange.yaml
    year = start_date[:4]
    start_month = int(start_date[5:7])
    quarter = (start_month - 1) // 3 + 1
    date_label = f"{year}Q{quarter}"

    summary_file = (
        Path("reports/validation/paper1_pattern_taxonomy") / f"all_patterns_summary_{symbol}_{date_label}.yaml"
    )
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_file, "w") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)

    logger.info(f"\n✅ Summary saved to: {summary_file}")

    # Exit code based on Issue #79 success criteria
    if len(mechanical) >= 5:
        logger.info(f"\n🎉 SUCCESS: {len(mechanical)} patterns validated as mechanical (target: 5-7)")
        return 0
    else:
        logger.warning(f"\n⚠️  PARTIAL: Only {len(mechanical)} patterns validated as mechanical (target: 5-7)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
