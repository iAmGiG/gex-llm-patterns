#!/usr/bin/env python3
"""
Pattern Taxonomy Validation Script - Issue #79
Validates core mechanical patterns using obfuscation tests across full 2024 dataset.

Proof-of-concept: Start with single pattern to validate workflow.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

from src.agents.market_mechanics_agent import MarketMechanicsAgent
from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator
from gex_db_infrastructure.validation.outcome_calculator import OutcomeCalculator
from gex_db_infrastructure.validation.pattern_taxonomy import PatternTaxonomy, ValidationCriteria

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def convert_numpy_types(obj):
    """Recursively convert numpy types to native Python types for YAML serialization.

    Fixes Issue: numpy.float64, numpy.int64, etc. serialize as binary in YAML.
    Solution: Convert to Python float/int before serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj


class PatternTaxonomyValidator:
    """Validates patterns using obfuscation tests to prove they work without context.

    Issue #79 Requirements:
    - Obfuscation: Pattern works without date/ticker context
    - Success Rate: >60% with 30+ samples
    - Economic Value: >20bps after costs
    - Academic Support: Clear causal mechanism
    """

    def __init__(self, symbol: str = "SPY", calculate_outcomes: bool = True):
        self.symbol = symbol
        # Issue #180: SQLite is primary options storage
        self.db = PostgreSQLOptionsManager()
        self.cache = UnifiedCacheManager()  # For non-options data
        self.taxonomy = PatternTaxonomy()
        self.obfuscator = DataObfuscator()
        self.agent = None  # Lazy init

        # Get validation criteria from taxonomy
        self.criteria = self.taxonomy.criteria

        # Outcome calculator (Issue #80)
        self.calculate_outcomes = calculate_outcomes
        self.outcome_calculator = OutcomeCalculator() if calculate_outcomes else None

        # Validation tracking
        self.test_dates = []
        self.failed_dates = []
        self.data_gaps = []
        self.results = {}

    def _get_expected_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """Calculate expected trading days (business days minus US holidays)."""
        # Generate business days
        all_dates = pd.date_range(start_date, end_date, freq="B")

        # US market holidays (2024)
        us_holidays_2024 = {
            "2024-01-01",
            "2024-01-15",
            "2024-02-19",
            "2024-03-29",
            "2024-05-27",
            "2024-07-04",
            "2024-09-02",
            "2024-11-28",
            "2024-12-25",
        }

        # Filter out holidays
        trading_days = [d.strftime("%Y-%m-%d") for d in all_dates if d.strftime("%Y-%m-%d") not in us_holidays_2024]

        return trading_days

    def get_test_date_range(self, start_date: str, end_date: str) -> List[str]:
        """Get all trading days in range from cache.

        Issue #84 Fix: Validates data coverage and fails fast if insufficient. Requires >=80% coverage for statistical
        validity (prevents silent incomplete testing).
        """
        logger.info(f"Scanning cache for dates between {start_date} and {end_date}")

        # Calculate expected trading days
        expected_dates = self._get_expected_trading_days(start_date, end_date)

        # Use cache manager to get cache directory (respects configuration)
        cache_base = self.cache.options_dir / self.symbol
        if not cache_base.exists():
            logger.error(f"Cache directory not found: {cache_base}")
            return []

        # Scan cache for available dates
        available_dates = []
        for file_path in sorted(cache_base.glob("*.pickle")):
            date_str = file_path.stem  # e.g., "2024-01-02"
            if start_date <= date_str <= end_date:
                available_dates.append(date_str)

        # Calculate coverage
        coverage_pct = (len(available_dates) / len(expected_dates) * 100) if expected_dates else 0
        missing_dates = sorted(set(expected_dates) - set(available_dates))

        logger.info(f"Data coverage: {coverage_pct:.1f}% ({len(available_dates)}/{len(expected_dates)} trading days)")

        # Issue #84: Fail fast if coverage insufficient for statistical validity
        MIN_COVERAGE_PCT = 80.0
        if coverage_pct < MIN_COVERAGE_PCT:
            error_msg = (
                f"\n{'='*80}\n"
                f"❌ INSUFFICIENT DATA COVERAGE: {coverage_pct:.1f}%\n"
                f"{'='*80}\n"
                f"Expected trading days: {len(expected_dates)}\n"
                f"Available in cache: {len(available_dates)}\n"
                f"Missing: {len(missing_dates)}\n"
                f"Minimum required: {MIN_COVERAGE_PCT}% coverage\n\n"
                f"First 10 missing dates: {missing_dates[:10]}\n\n"
                f"📥 COLLECT MISSING DATA:\n"
                f"   python scripts/data_collection/start_historical_collection.py \\\n"
                f"     --symbols {self.symbol} \\\n"
                f"     --start-date {start_date} \\\n"
                f"     --end-date {end_date}\n\n"
                f"⚠️  Running validation with <{MIN_COVERAGE_PCT}% coverage may produce\n"
                f"   misleading results due to selection bias.\n"
                f"{'='*80}\n"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if missing_dates:
            logger.warning(f"Missing {len(missing_dates)} dates (within {MIN_COVERAGE_PCT}% threshold)")
            logger.warning(f"Missing dates: {missing_dates[:5]}{'...' if len(missing_dates) > 5 else ''}")

        return available_dates

    def validate_data_continuity(self, dates: List[str]) -> Dict:
        """Check data continuity and identify gaps.

        Returns gaps that need to be filled by agent.
        """
        logger.info(f"Validating data continuity for {len(dates)} dates")

        available = []
        missing = []

        for date_str in dates:
            try:
                # Issue #180: Check SQLite for options data
                options_data = self.db.get_options_chain(self.symbol, date_str)
                if options_data is not None and not options_data.empty:
                    available.append(date_str)
                else:
                    missing.append(date_str)
                    logger.warning(f"Missing or empty data for {date_str}")
            except Exception as e:
                missing.append(date_str)
                logger.warning(f"Error checking data for {date_str}: {e}")

        continuity_report = {
            "total_dates": len(dates),
            "available_count": len(available),
            "missing_count": len(missing),
            "available_dates": available,
            "missing_dates": missing,
            "continuity_pct": (len(available) / len(dates) * 100) if dates else 0,
        }

        logger.info(
            f"Data continuity: {continuity_report['continuity_pct']:.1f}% ({len(available)}/{len(dates)} dates)"
        )

        if missing:
            logger.warning(f"Missing data for {len(missing)} dates: {missing[:5]}{'...' if len(missing) > 5 else ''}")

        return continuity_report

    def validate_pattern_with_obfuscation(
        self, pattern_name: str, dates: List[str], confidence_threshold: float = None
    ) -> Dict:
        """Validate single pattern using obfuscation test.

        Args:
            pattern_name: Pattern to validate (e.g., 'gamma_positioning')
            dates: List of dates to test
            confidence_threshold: Minimum confidence for detection (uses taxonomy criteria if None)

        Returns:
            Validation results with pattern detection metrics
        """
        # Use pattern-specific threshold from taxonomy if not specified
        if confidence_threshold is None:
            confidence_threshold = self.criteria.min_success_rate * 100  # Convert 0.60 to 60.0

        logger.info(f"=" * 80)
        logger.info(f"PATTERN VALIDATION: {pattern_name}")
        logger.info(f"=" * 80)
        logger.info(f"Testing {len(dates)} dates with obfuscation")
        logger.info(f"Confidence threshold: {confidence_threshold}% (from taxonomy criteria)")
        logger.info(f"Symbol: {self.symbol}")

        # Initialize agent if needed
        if self.agent is None:
            logger.info("Initializing MarketMechanicsAgent...")
            self.agent = MarketMechanicsAgent(symbol=self.symbol)

        detections = []
        high_confidence_count = 0
        failed_fetches = []

        # Track previous GEX for velocity calculation (Issue #80)
        previous_gex = None

        # PERFORMANCE OPTIMIZATION: Use batch processing (Issue #78)
        # Process dates in batches of 10 for 75% API cost reduction
        batch_size = 10
        total_batches = (len(dates) + batch_size - 1) // batch_size

        logger.info(f"Processing {len(dates)} dates in {total_batches} batches of {batch_size}")

        for batch_idx in range(0, len(dates), batch_size):
            batch_dates = dates[batch_idx : batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1

            logger.info(f"\n{'='*80}")
            logger.info(f"BATCH {batch_num}/{total_batches}: Processing {len(batch_dates)} dates")
            logger.info(f"{'='*80}")

            try:
                # Create pattern-specific experiment template
                experiment_template = self._generate_pattern_experiment(pattern_name, "DATE_PLACEHOLDER")

                # Run batch experiment with obfuscation
                batch_result = self.agent.run_batch_experiments(
                    dates=batch_dates,
                    experiment_template=experiment_template,
                    use_obfuscation=True,  # Critical: prevent LLM from seeing real dates/tickers
                )

                # Check if batch failed
                if batch_result.get("status") == "error":
                    logger.error(f"Batch {batch_num} failed: {batch_result.get('error')}")
                    failed_fetches.extend(batch_dates)
                    continue

                # Process individual results from batch
                individual_results = batch_result.get("individual_results", {})

                for i, date_str in enumerate(batch_dates, 1):
                    result = individual_results.get(date_str)

                    if not result:
                        logger.warning(f"  [{batch_idx + i}/{len(dates)}] {date_str}: No result in batch")
                        failed_fetches.append(date_str)
                        continue

                    logger.info(f"  [{batch_idx + i}/{len(dates)}] Processing {date_str}...")

                    # Check if pattern was detected
                    # Handle both error returns and successful results
                    if result and isinstance(result, dict):
                        # Debug: log result structure
                        logger.debug(f"Result keys: {result.keys()}")
                        logger.debug(f"Full result: {result}")

                        # Get mechanics interpretation from result
                        # NOTE: MarketMechanicsAgent returns 'mechanics_interpretation', not 'llm_analysis'
                        mechanics = result.get("mechanics_interpretation", {})

                        confidence = mechanics.get("confidence", 0)

                        # Get obfuscated date from result (Issue #81 fix)
                        date_obfuscated = result.get("obfuscated_date", date_str)

                        # Extract GEX metrics
                        gex_raw = result.get("gex_metrics", {})

                        # Consolidate redundant GEX fields (net_gex = total_gamma = gex_value)
                        net_gex_usd = gex_raw.get("net_gex") or gex_raw.get("total_gamma") or gex_raw.get("gex_value")

                        # Calculate GEX velocity (Issue #80: day-over-day change is often the signal)
                        gex_velocity = None
                        if previous_gex is not None and net_gex_usd is not None:
                            from gex_db_infrastructure.gex.gex_calculator import GEXCalculator

                            calculator = GEXCalculator()
                            gex_velocity = calculator.calculate_gex_velocity(
                                current_gex=net_gex_usd, previous_gex=previous_gex
                            )

                        # Update previous_gex for next iteration
                        if net_gex_usd is not None:
                            previous_gex = net_gex_usd

                        detection = {
                            "date": date_str,
                            "date_obfuscated": date_obfuscated,
                            "detected": confidence >= confidence_threshold,
                            "obfuscation_verified": batch_result.get("obfuscation_used", False),
                            # Narrative interpretation (grouped)
                            "narrative": {
                                "who": mechanics.get("who", "N/A"),
                                "whom": mechanics.get("whom", "N/A"),
                                "what": mechanics.get("what", "N/A"),
                                "confidence": confidence,
                                "time_horizon": mechanics.get("time_horizon", "Unknown"),
                            },
                            # Quantitative evidence (grouped and consolidated)
                            "quantitative_evidence": {
                                "gex_metrics": {
                                    "net_gex_usd": net_gex_usd,  # Consolidated from total_gamma/net_gex/gex_value
                                    # Issue #80: velocity signal
                                    "net_gex_change_1d_usd": (
                                        gex_velocity["net_gex_change_1d_usd"] if gex_velocity else None
                                    ),
                                    "net_gex_change_1d_pct": (
                                        gex_velocity["net_gex_change_1d_pct"] if gex_velocity else None
                                    ),
                                    "regime": gex_raw.get("regime"),
                                    "flip_level_price": gex_raw.get("flip_level") or gex_raw.get("zero_gamma_level"),
                                    "gamma_concentration": gex_raw.get("gamma_concentration"),
                                    "spot_price": gex_raw.get("spot_price"),
                                    "source": gex_raw.get("source"),
                                },
                                "market_metrics": {
                                    "call_gamma": gex_raw.get("call_gamma"),
                                    "put_gamma": gex_raw.get("put_gamma"),
                                },
                            },
                            # outcome_metrics will be added by backtest script
                        }

                        # Add outcome metrics (Issue #80) if enabled
                        if self.calculate_outcomes and self.outcome_calculator:
                            try:
                                detection = self.outcome_calculator.add_outcome_metrics(detection, self.symbol)
                                logger.debug(f"Added outcome metrics for {date_str}")
                            except Exception as e:
                                logger.warning(f"Could not calculate outcomes for {date_str}: {e}")

                        detections.append(detection)

                        if detection["detected"]:
                            high_confidence_count += 1
                            logger.info(f"  ✅ DETECTED: {confidence}% confidence")
                            logger.info(f"     WHO: {detection['narrative']['who']}")
                            logger.info(f"     WHOM: {detection['narrative']['whom']}")
                            logger.info(f"     WHAT: {detection['narrative']['what']}")

                            # Log outcome metrics if available
                            if "outcome_metrics" in detection:
                                outcome = detection["outcome_metrics"]
                                logger.info(f"     OUTCOME: {outcome.get('forward_1d_return_pct', 'N/A')}% T+1 return")
                                logger.info(f"     MATERIALIZED: {outcome.get('prediction_materialized', 'N/A')}")
                        else:
                            logger.info(f"  ⚠️  Low confidence: {confidence}%")

                    else:
                        logger.warning(f"  ❌ No analysis result for {date_str}")
                        failed_fetches.append(date_str)

            except Exception as e:
                logger.error(f"Batch {batch_num} processing error: {e}")
                failed_fetches.extend(batch_dates)
                for date_str in batch_dates:
                    self.failed_dates.append({"date": date_str, "error": f"Batch error: {str(e)}"})

        # Calculate metrics
        total_tested = len(detections)
        success_rate = (high_confidence_count / total_tested * 100) if total_tested > 0 else 0

        # Calculate outcome metrics (will be populated by backtest)
        avg_forward_1d_return = None
        predictive_accuracy = None
        net_alpha = None

        # Check if outcome_metrics exist in detections (from backtest)
        detections_with_outcomes = [d for d in detections if "outcome_metrics" in d]
        if detections_with_outcomes:
            # Handle missing forward_1d_return_pct gracefully (happens when forward price data unavailable)
            forward_returns = [
                d["outcome_metrics"]["forward_1d_return_pct"]
                for d in detections_with_outcomes
                if "forward_1d_return_pct" in d["outcome_metrics"]
            ]
            avg_forward_1d_return = sum(forward_returns) / len(forward_returns) if forward_returns else None

            # Handle missing prediction_materialized gracefully
            predictions_materialized = [
                d["outcome_metrics"]["prediction_materialized"]
                for d in detections_with_outcomes
                if "prediction_materialized" in d["outcome_metrics"]
                and d["outcome_metrics"]["prediction_materialized"] is not None
            ]
            predictive_accuracy = (
                (sum(predictions_materialized) / len(predictions_materialized) * 100)
                if predictions_materialized
                else None
            )

            # Calculate net alpha (gross return - estimated 5bps transaction costs)
            if avg_forward_1d_return is not None:
                net_alpha = avg_forward_1d_return - 0.05

        validation_result = {
            "pattern_name": pattern_name,
            "test_metadata": {
                "symbol": self.symbol,
                "start_date": dates[0],
                "end_date": dates[-1],
                "test_period": f"{dates[0]} to {dates[-1]}",
                "total_dates_requested": len(dates),
                "total_dates_tested": total_tested,
                "failed_fetches": len(failed_fetches),
                "confidence_threshold": confidence_threshold,
                "obfuscation_enabled": True,
                "test_date": datetime.now().isoformat(),
            },
            "performance_metrics": {
                # Detection metrics (did we find the pattern?)
                "total_tested": total_tested,
                "detection_rate_pct": success_rate,  # Renamed from success_rate_pct
                "high_confidence_detections": high_confidence_count,
                "low_confidence_detections": total_tested - high_confidence_count,
                # Prediction validation (did it actually work?) - populated by backtest
                "predictive_accuracy_pct": predictive_accuracy,
                "avg_forward_1d_return_pct": avg_forward_1d_return,
                # Economic metrics - populated by backtest
                "net_alpha_pct": net_alpha,
                "passes_economic_threshold": net_alpha > 0.20 if net_alpha is not None else None,
                "is_validated": success_rate >= 60.0 and total_tested >= 30,
            },
            "obfuscation_test": {
                "passed": success_rate >= 60.0 and total_tested >= 30,
                "success_rate": success_rate,
                "sample_size": total_tested,
                "required_success_rate": 60.0,
                "required_sample_size": 30,
                "verdict": self._generate_verdict(success_rate, total_tested),
            },
            "detections": detections,
            "failed_dates": failed_fetches,
        }

        # Log summary
        logger.info(f"\n" + "=" * 80)
        logger.info(f"VALIDATION SUMMARY: {pattern_name}")
        logger.info(f"=" * 80)
        logger.info(f"Dates Tested: {total_tested}/{len(dates)}")
        logger.info(f"High-Confidence Detections: {high_confidence_count}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(
            f"Obfuscation Test: {'✅ PASSED' if validation_result['obfuscation_test']['passed'] else '❌ FAILED'}"
        )

        if failed_fetches:
            logger.warning(f"Failed Fetches: {len(failed_fetches)} dates")
            logger.warning(f"  Dates: {failed_fetches[:5]}{'...' if len(failed_fetches) > 5 else ''}")

        return validation_result

    def _generate_pattern_experiment(self, pattern_name: str, date_str: str) -> str:
        """Generate experiment description focused on specific pattern."""
        pattern_experiments = {
            "gamma_positioning": (
                f"Analyze {self.symbol} gamma exposure and dealer positioning on {date_str}. "
                "Focus on: 1) Total gamma exposure magnitude and sign, "
                "2) Dealer delta hedging requirements, "
                "3) Price dampening/amplification effects from gamma positioning."
            ),
            "stock_pinning": (
                f"Analyze {self.symbol} option expiration dynamics on {date_str}. "
                "Focus on: 1) Large open interest concentrations at specific strikes, "
                "2) Gamma explosion near high-OI strikes, "
                "3) Pinning effects attracting price to strikes."
            ),
            "0dte_hedging": (
                f"Analyze {self.symbol} 0DTE option hedging flows on {date_str}. "
                "Focus on: 1) Rapid gamma changes requiring immediate hedging, "
                "2) Strike breach cascade effects, "
                "3) Dealer forced hedging at specific price levels."
            ),
            "dealer_trap": (
                f"Analyze {self.symbol} gamma flip point positioning on {date_str}. "
                "Focus on: 1) Distance to gamma flip point, "
                "2) Dealer positioning stability at flip, "
                "3) Forced unwinding or hedging escalation near flip."
            ),
            "friday_330_squeeze": (
                f"Analyze {self.symbol} end-of-day gamma dynamics on {date_str}. "
                "Focus on: 1) Final hedging window before expiration, "
                "2) Weekend gamma risk management, "
                "3) Directional momentum into close."
            ),
            "volume_anomaly": (
                f"Analyze {self.symbol} unusual options volume on {date_str}. "
                "Focus on: 1) 100K+ contract flows, "
                "2) Institutional positioning signals, "
                "3) Market impact of large flows."
            ),
        }

        return pattern_experiments.get(pattern_name, f"Analyze {self.symbol} options market mechanics on {date_str}.")

    def _generate_verdict(self, success_rate: float, sample_size: int) -> str:
        """Generate human-readable verdict with actionable interpretation.

        Verdict Categories:
        - MECHANICAL (>=60%): Structural pattern, high confidence trading
        - INVESTIGATE (40-60%): May be profitable (like dealer_trap 37.7%), needs Phase 2 economic test
        - NARRATIVE (<40%): Likely folklore, not actionable
        """
        if sample_size < 30:
            return f"INSUFFICIENT_SAMPLES - Need 30+, have {sample_size}"
        elif success_rate >= 60.0:
            return f"MECHANICAL - {success_rate:.1f}% success with {sample_size} samples (validated for trading)"
        elif success_rate >= 40.0:
            return f"INVESTIGATE - {success_rate:.1f}% success (may be profitable edge, run economic backtest)"
        else:
            return f"NARRATIVE/FOLKLORE - {success_rate:.1f}% success (not actionable)"

    def save_results(self, validation_result: Dict, output_dir: Path = None):
        """Save validation results to YAML file."""
        if output_dir is None:
            output_dir = Path("reports/validation/paper1_pattern_taxonomy")

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename: pattern_TICKER_daterange.yaml (e.g., gamma_positioning_SPY_2024Q1.yaml)
        pattern_name = validation_result["pattern_name"]
        symbol = validation_result.get("test_metadata", {}).get("symbol", "UNKNOWN")
        start_date = validation_result.get("test_metadata", {}).get("start_date", "")
        end_date = validation_result.get("test_metadata", {}).get("end_date", "")

        # Extract quarter/year from date range (e.g., 2024-01-02 to 2024-03-29 -> 2024Q1)
        if start_date and end_date:
            year = start_date[:4]
            start_month = int(start_date[5:7])
            quarter = (start_month - 1) // 3 + 1
            date_label = f"{year}Q{quarter}"
        else:
            date_label = datetime.now().strftime("%Y%m%d")

        filename = f"{pattern_name}_{symbol}_{date_label}.yaml"
        filepath = output_dir / filename

        # Convert numpy types to native Python types before YAML serialization
        validation_result_clean = convert_numpy_types(validation_result)

        # Save as YAML
        with open(filepath, "w") as f:
            yaml.dump(validation_result_clean, f, default_flow_style=False, sort_keys=False)

        logger.info(f"\n✅ Results saved to: {filepath}")
        return filepath


def main():
    """Main entry point for pattern validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate pattern taxonomy with obfuscation tests")
    parser.add_argument(
        "--pattern", type=str, default="gamma_positioning", help="Pattern to validate (default: gamma_positioning)"
    )
    parser.add_argument("--symbol", type=str, default="SPY", help="Symbol to test (default: SPY)")
    parser.add_argument("--start-date", type=str, default="2024-01-02", help="Start date (default: 2024-01-02)")
    parser.add_argument("--end-date", type=str, default="2024-06-28", help="End date (default: 2024-06-28)")
    parser.add_argument("--confidence", type=float, default=60.0, help="Confidence threshold (default: 60.0)")
    parser.add_argument("--check-continuity", action="store_true", help="Check data continuity before running test")
    parser.add_argument(
        "--with-outcomes",
        action="store_true",
        default=True,
        help="Calculate outcome metrics (Issue #80) - enabled by default",
    )
    parser.add_argument(
        "--no-outcomes",
        action="store_false",
        dest="with_outcomes",
        help="Skip outcome calculation (faster, detection only)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for validation results (default: reports/validation/paper1_pattern_taxonomy)",
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default="unbiased",
        choices=["unbiased", "biased"],
        help="Prompt template to use (default: unbiased, biased is deprecated)",
    )

    args = parser.parse_args()

    # Initialize validator
    validator = PatternTaxonomyValidator(symbol=args.symbol, calculate_outcomes=args.with_outcomes)

    if args.with_outcomes:
        logger.info("✅ Outcome metrics calculation ENABLED (Issue #80)")
    else:
        logger.info("⚠️  Outcome metrics calculation DISABLED (detection only)")

    # Get test dates
    test_dates = validator.get_test_date_range(args.start_date, args.end_date)

    if not test_dates:
        logger.error(f"No dates found in cache for {args.symbol} between {args.start_date} and {args.end_date}")
        return 1

    # MANDATORY: Check data continuity before validation
    continuity_report = validator.validate_data_continuity(test_dates)

    # Save continuity report
    continuity_path = Path("reports/validation/data_continuity.yaml")
    continuity_path.parent.mkdir(parents=True, exist_ok=True)
    with open(continuity_path, "w") as f:
        yaml.dump(continuity_report, f, default_flow_style=False)

    logger.info(f"Continuity report saved to: {continuity_path}")

    if continuity_report["continuity_pct"] < 90:
        logger.warning(f"⚠️  Data continuity is {continuity_report['continuity_pct']:.1f}% - expect some failed fetches")
        logger.warning("Agent will attempt to fetch missing data via API")

    # Run validation
    logger.info(f"\n🚀 Starting validation for pattern: {args.pattern}")
    validation_result = validator.validate_pattern_with_obfuscation(
        pattern_name=args.pattern, dates=test_dates, confidence_threshold=args.confidence
    )

    # Save results
    output_dir = Path(args.output_dir) if args.output_dir else None
    output_path = validator.save_results(validation_result, output_dir=output_dir)

    # Print final verdict
    obfuscation_test = validation_result["obfuscation_test"]
    logger.info(f"\n" + "=" * 80)
    logger.info(f"FINAL VERDICT: {obfuscation_test['verdict']}")
    logger.info(f"=" * 80)

    if obfuscation_test["passed"]:
        logger.info(f"✅ Pattern '{args.pattern}' VALIDATED as mechanical")
        logger.info(f"   Success rate: {obfuscation_test['success_rate']:.1f}%")
        logger.info(f"   Sample size: {obfuscation_test['sample_size']}")
        return 0
    else:
        logger.warning(f"❌ Pattern '{args.pattern}' NOT VALIDATED")
        logger.warning(f"   Success rate: {obfuscation_test['success_rate']:.1f}% (need 60%+)")
        logger.warning(f"   Sample size: {obfuscation_test['sample_size']} (need 30+)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
