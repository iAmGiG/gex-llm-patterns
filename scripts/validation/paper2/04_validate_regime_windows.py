#!/usr/bin/env python3
"""
Validate 30-Day Regime Detection - Paper #2

Purpose:
    Validates LLM ability to identify persistent market regimes from 30-day
    dealer gamma positioning windows.

Phases:
    Phase 1: Q1 2024 positive validation (32 windows, baseline detection rate)
    Phase 2: Negative controls (shuffled, transitional, low-magnitude)
    Phase 3: Full 2024 validation (223 windows)
    Phase 4: 2020 comparison (0DTE hypothesis)

Expected Detection Rate: 30-50% (selective, not universal like 5-day's 98-100%)

Related:
    - docs/papers/paper2/methodology/regime_windows_design.md
    - docs/papers/paper2/validation/validation_phases.md
    - Issues #89, #107
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from src.agents.market_mechanics_agent import MarketMechanicsAgent
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.sequential_gex_fetcher import SequentialGEXFetcher
from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder
from src.utils.config_manager import get_config
from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator
from gex_db_infrastructure.validation.regime_classifier import RegimeClassifier

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


logger = logging.getLogger(__name__)


class RegimeWindowValidator:
    """Validates LLM regime detection on 30-day windows.

    Compares LLM classifications against deterministic RegimeClassifier.
    """

    def __init__(self, symbol: str = "SPY", window_size: int = 30, obfuscate: bool = True):
        """Initialize regime window validator.

        Args:
            symbol: Ticker symbol to analyze
            window_size: Regime window size in days (default 30)
            obfuscate: Whether to obfuscate dates (REQUIRED for research)
        """
        self.symbol = symbol
        self.window_size = window_size
        self.obfuscate = obfuscate

        # Initialize MarketMechanicsAgent (consistency with Paper #1)
        # Agent provides: LLM client, data fetching, caching
        self.agent = MarketMechanicsAgent(symbol=symbol)

        # Use agent's cache or create new one
        self.cache_manager = self.agent.cache if hasattr(self.agent, "cache") else UnifiedCacheManager()

        # Initialize components
        self.regime_classifier = RegimeClassifier()
        self.gex_fetcher = SequentialGEXFetcher(cache_manager=self.cache_manager, window_size=window_size)
        self.prompt_builder = MechanicsPromptBuilder()
        self.obfuscator = DataObfuscator() if obfuscate else None

        logger.info(
            f"Initialized RegimeWindowValidator: symbol={symbol}, window_size={window_size}, obfuscate={obfuscate}"
        )
        logger.info(f"Using MarketMechanicsAgent with LLM: {self.agent.llm.model if self.agent.llm else 'None'}")

    def _get_trading_days_in_range(self, start_date: str, end_date: str) -> List[str]:
        """Get list of trading days in date range from cache.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Sorted list of trading day strings in YYYY-MM-DD format
        """
        # Get all available dates from GEX cache (uses GEXCacheManager structure)
        # Structure: .cache/gex_data/SPY/YYYY-MM-DD/gex_summary.json
        cache_dir = Path(f".cache/gex_data/{self.symbol}")
        if not cache_dir.exists():
            logger.error(f"Cache directory not found: {cache_dir}")
            return []

        # Scan for date directories
        available_dates = []
        for date_dir in cache_dir.iterdir():
            if date_dir.is_dir() and (date_dir / "gex_summary.json").exists():
                # Directory name is the date (YYYY-MM-DD)
                date_str = date_dir.name
                available_dates.append(date_str)

        # Filter to date range
        trading_days = [d for d in sorted(available_dates) if start_date <= d <= end_date]

        return trading_days

    def validate_date_range(self, start_date: str, end_date: str, sample_every_n: int = 1) -> Dict:
        """Validate regime detection across a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            sample_every_n: Sample every N days (1 = every day, 5 = every 5th day)

        Returns:
            Validation results dict with summary statistics and per-window results
        """
        logger.info(f"Starting validation: {start_date} to {end_date}, sample every {sample_every_n} days")

        # Get ALL trading days available in cache (we need historical context for 30-day windows)
        all_trading_days = self._get_trading_days_in_range("2020-01-01", end_date)
        logger.info(f"Found {len(all_trading_days)} total trading days in cache")

        # Filter to potential window ends (must be within validation range)
        potential_window_ends = [d for d in all_trading_days if start_date <= d <= end_date]
        logger.info(
            f"{len(potential_window_ends)} dates in validation range: {potential_window_ends[:5]}..."
            if len(potential_window_ends) > 5
            else f"{len(potential_window_ends)} dates: {potential_window_ends}"
        )

        # Sample every N days
        if sample_every_n > 1:
            potential_window_ends = potential_window_ends[::sample_every_n]
            logger.info(f"Sampled to {len(potential_window_ends)} windows (every {sample_every_n} days)")

        # Validate each window
        results = []
        for i, end_date_window in enumerate(potential_window_ends):
            logger.info(f"\n{'='*60}")
            logger.info(f"Window {i+1}/{len(potential_window_ends)}: End date {end_date_window}")
            logger.info(f"{'='*60}")

            window_result = self._validate_single_window(end_date_window)
            if window_result:
                results.append(window_result)

        # Calculate summary statistics
        summary = self._calculate_summary_stats(results, start_date, end_date)

        return {
            "validation_metadata": {
                "symbol": self.symbol,
                "window_size": self.window_size,
                "obfuscation": self.obfuscate,
                "date_range": f"{start_date} to {end_date}",
                "sample_every_n": sample_every_n,
                "windows_tested": len(results),
                "timestamp": datetime.now().isoformat(),
            },
            "summary_statistics": summary,
            "windows": results,
        }

    def _validate_single_window(self, end_date: str) -> Optional[Dict]:
        """Validate a single 30-day regime window.

        Args:
            end_date: Window end date (YYYY-MM-DD)

        Returns:
            Window validation result dict, or None if window couldn't be fetched
        """
        # Fetch 30-day GEX sequence
        result = self.gex_fetcher.get_sequential_gex(symbol=self.symbol, end_date=end_date)

        if result is None:
            logger.warning(f"Could not fetch 30-day window ending {end_date} - skipping")
            return None

        gex_sequence = result["gex_sequence"]

        if len(gex_sequence) != self.window_size:
            logger.warning(f"Window has {len(gex_sequence)} days, expected {self.window_size} - skipping")
            return None

        logger.info(f"Fetched {len(gex_sequence)} days of GEX data")

        # Deterministic classification (ground truth)
        deterministic = self.regime_classifier.classify_window(gex_sequence)
        logger.info(f"Deterministic: {deterministic['regime_type']} (persistent={deterministic['is_persistent']})")

        # Obfuscate for LLM if enabled
        if self.obfuscate:
            gex_sequence_llm = self._obfuscate_sequence(gex_sequence)
        else:
            gex_sequence_llm = gex_sequence

        # Build LLM prompt
        prompt = self.prompt_builder.build_regime_prompt(
            gex_sequence=gex_sequence_llm, end_date=end_date  # For logging only, not shown to LLM
        )

        # Get LLM classification
        llm_response = self._call_llm(prompt)
        llm_classification = self.prompt_builder.parse_regime_response(llm_response)

        logger.info(
            f"LLM: {llm_classification['regime_type']} (detected={llm_classification['regime_detected']}, confidence={llm_classification['confidence']})"
        )

        # Compare classifications
        agreement = deterministic["regime_type"] == llm_classification["regime_type"]

        # Determine accuracy label
        if agreement:
            accuracy = "correct"
        else:
            accuracy = "incorrect"

        logger.info(f"Agreement: {agreement} ({accuracy})")

        # Build result
        start_date = gex_sequence[0]["date"]

        return {
            "window_id": len(self.window_id_counter) + 1 if hasattr(self, "window_id_counter") else 1,
            "end_date": end_date,
            "start_date": start_date,
            "date_range": f"{start_date} to {end_date}",
            "deterministic_classification": {
                "regime_type": deterministic["regime_type"],
                "is_persistent": deterministic["is_persistent"],
                "metrics": (
                    deterministic["metrics"].__dict__
                    if hasattr(deterministic["metrics"], "__dict__")
                    else deterministic["metrics"]
                ),
            },
            "llm_classification": llm_classification,
            "agreement": agreement,
            "accuracy": accuracy,
        }

    def _obfuscate_sequence(self, gex_sequence: List[Dict]) -> List[Dict]:
        """Obfuscate 30-day GEX sequence for LLM.

        Args:
            gex_sequence: List of 30 daily GEX dicts with real dates

        Returns:
            List of 30 daily GEX dicts with obfuscated dates (Day T-29 to T+0)
        """
        obfuscated = []

        for i, day_data in enumerate(gex_sequence):
            # Calculate relative day (T-29 to T+0)
            relative_day = i - (len(gex_sequence) - 1)  # -29, -28, ..., -1, 0

            if relative_day == 0:
                obf_date = "Day T+0"
            elif relative_day < 0:
                obf_date = f"Day T{relative_day}"  # T-29, T-28, etc.
            else:
                obf_date = f"Day T+{relative_day}"

            obfuscated.append(
                {
                    "obfuscated_date": obf_date,
                    "net_gex": day_data.get("net_gex", 0),
                    "spot_price": day_data.get("spot_price", None),  # Optional
                    # Keep for validation, not shown to LLM
                    "real_date": day_data.get("date"),
                }
            )

        return obfuscated

    def _call_llm(self, prompt: str) -> str:
        """Call LLM via MarketMechanicsAgent.

        Args:
            prompt: Regime detection prompt

        Returns:
            Raw LLM response text
        """
        try:
            # Use agent's LLM client (consistent with Paper #1)
            if self.agent.llm:
                response_text = self.agent.llm.generate(prompt)
                return response_text
            else:
                logger.error("Agent LLM not initialized")
                return ""

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            import traceback

            logger.debug(f"Traceback: {traceback.format_exc()}")
            return ""

    def _calculate_summary_stats(self, results: List[Dict], start_date: str, end_date: str) -> Dict:
        """Calculate summary statistics from validation results.

        Args:
            results: List of window validation results
            start_date: Validation start date
            end_date: Validation end date

        Returns:
            Summary statistics dict
        """
        if not results:
            return {
                "windows_tested": 0,
                "detection_rate_pct": 0.0,
                "accuracy_rate_pct": 0.0,
                "regimes_detected_llm": 0,
                "regimes_detected_deterministic": 0,
            }

        # Count detections
        llm_detections = sum(1 for r in results if r["llm_classification"]["regime_detected"])
        deterministic_detections = sum(1 for r in results if r["deterministic_classification"]["is_persistent"])

        # Count agreements
        agreements = sum(1 for r in results if r["agreement"])

        # Calculate rates
        detection_rate = llm_detections / len(results) * 100
        accuracy_rate = agreements / len(results) * 100

        # Regime type distribution (LLM)
        regime_types_llm = {}
        for r in results:
            regime_type = r["llm_classification"]["regime_type"]
            regime_types_llm[regime_type] = regime_types_llm.get(regime_type, 0) + 1

        # Regime type distribution (deterministic)
        regime_types_det = {}
        for r in results:
            regime_type = r["deterministic_classification"]["regime_type"]
            regime_types_det[regime_type] = regime_types_det.get(regime_type, 0) + 1

        # Confidence distribution (LLM)
        confidences = [r["llm_classification"]["confidence"] for r in results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "windows_tested": len(results),
            "detection_rate_pct": round(detection_rate, 2),
            "accuracy_rate_pct": round(accuracy_rate, 2),
            "regimes_detected_llm": llm_detections,
            "regimes_detected_deterministic": deterministic_detections,
            "agreements": agreements,
            "regime_types_llm": regime_types_llm,
            "regime_types_deterministic": regime_types_det,
            "avg_confidence_llm": round(avg_confidence, 1),
            "phase1_expected_detection": "3-10%",
            "phase1_pass_criteria": "detection_rate 3-10% AND accuracy_rate ≥70%",
        }


def main():
    """Main entry point for regime window validation."""
    parser = argparse.ArgumentParser(
        description="Validate 30-day regime detection (Paper #2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase 1: Q1 2024 baseline (32 windows, every day)
  # Output: p2_phase1_baseline_SPY_2024Q1.yaml
  python validate_regime_windows.py \\
    --start-date 2024-01-02 \\
    --end-date 2024-03-29 \\
    --symbol SPY

  # Phase 2: Negative controls (sampled every 5th day)
  # Output: p2_phase2_negctrl_SPY_2024Q1.yaml
  python validate_regime_windows.py \\
    --start-date 2024-01-02 \\
    --end-date 2024-03-29 \\
    --sample-every 5

  # Phase 3: Full 2024 (223 windows)
  # Output: p2_phase3_full_SPY_2024_full.yaml
  python validate_regime_windows.py \\
    --start-date 2024-01-02 \\
    --end-date 2024-12-31

  # Phase 4: 2020 comparison (0DTE hypothesis)
  # Output: p2_phase4_comparison_SPY_2020_2024.yaml (if multi-year range)
  python validate_regime_windows.py \\
    --start-date 2020-01-02 \\
    --end-date 2020-12-31
        """,
    )

    parser.add_argument("--symbol", type=str, default="SPY", help="Symbol to analyze (default: SPY)")

    parser.add_argument("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD)")

    parser.add_argument("--end-date", type=str, required=True, help="End date (YYYY-MM-DD)")

    parser.add_argument("--window-size", type=int, default=30, help="Regime window size in days (default: 30)")

    parser.add_argument(
        "--sample-every", type=int, default=1, help="Sample every N days (1=every day, 5=every 5th day). Default: 1"
    )

    parser.add_argument(
        "--no-obfuscate", action="store_true", help="Disable date obfuscation (NOT recommended for research)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output YAML file path (default: auto-generate in reports/validation/paper2_regime_windows/)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Force reconfiguration
    )

    print(f"DEBUG: Logging configured at level {log_level}")

    # Validate obfuscation
    if args.no_obfuscate:
        logger.warning("⚠️  OBFUSCATION DISABLED - Results not suitable for research publication!")
        logger.warning("⚠️  LLM may cheat using temporal knowledge instead of structural analysis")

    # Initialize validator
    validator = RegimeWindowValidator(
        symbol=args.symbol, window_size=args.window_size, obfuscate=(not args.no_obfuscate)
    )

    # Run validation
    logger.info(f"\nStarting Phase 1 Validation:")
    logger.info(f"  Symbol: {args.symbol}")
    logger.info(f"  Date range: {args.start_date} to {args.end_date}")
    logger.info(f"  Window size: {args.window_size} days")
    logger.info(f"  Sampling: Every {args.sample_every} day(s)")
    logger.info(f"  Obfuscation: {'ENABLED' if not args.no_obfuscate else 'DISABLED'}")
    logger.info("")

    results = validator.validate_date_range(
        start_date=args.start_date, end_date=args.end_date, sample_every_n=args.sample_every
    )

    # Print summary
    summary = results["summary_statistics"]
    logger.info(f"\n{'='*60}")
    logger.info(f"VALIDATION SUMMARY")
    logger.info(f"{'='*60}")

    # Debug: Check what's in summary
    if "windows_tested" not in summary or summary["windows_tested"] == 0:
        logger.error(f"No windows processed! Summary: {summary}")
        logger.error(f"Total results returned: {len(results.get('windows', []))}")
        return 1

    logger.info(f"Windows tested: {summary['windows_tested']}")
    logger.info(
        f"LLM detection rate: {summary['detection_rate_pct']}% ({summary['regimes_detected_llm']}/{summary['windows_tested']})"
    )
    logger.info(
        f"Deterministic detection rate: {summary['regimes_detected_deterministic']}/{summary['windows_tested']}"
    )
    logger.info(
        f"LLM accuracy rate: {summary['accuracy_rate_pct']}% ({summary['agreements']}/{summary['windows_tested']} agreements)"
    )
    logger.info(f"Average LLM confidence: {summary['avg_confidence_llm']}")
    logger.info(f"\nLLM regime types: {summary['regime_types_llm']}")
    logger.info(f"Deterministic regime types: {summary['regime_types_deterministic']}")
    logger.info(f"\nPhase 1 pass criteria: {summary['phase1_pass_criteria']}")

    # Determine output path
    if args.output is None:
        # Auto-generate filename based on test type and range
        output_dir = project_root / "reports" / "validation" / "paper2_regime_windows"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine period label from dates
        start_year = args.start_date[:4]
        end_year = args.end_date[:4]

        # Q1 2024: Jan-Mar
        # Q2 2024: Apr-Jun
        # Q3 2024: Jul-Sep
        # Q4 2024: Oct-Dec
        # Full year: Jan-Dec same year
        start_month = int(args.start_date[5:7])
        end_month = int(args.end_date[5:7])

        if start_year == end_year:
            year = start_year
            # Determine quarter or full year
            if start_month <= 3 and end_month <= 3:
                period = f"{year}Q1"
            elif start_month >= 4 and start_month <= 6 and end_month <= 6:
                period = f"{year}Q2"
            elif start_month >= 7 and start_month <= 9 and end_month <= 9:
                period = f"{year}Q3"
            elif start_month >= 10 and end_month >= 10:
                period = f"{year}Q4"
            elif start_month == 1 and end_month == 12:
                period = f"{year}_full"
            else:
                # Custom range
                period = f"{year}_custom"
        else:
            # Multi-year
            period = f"{start_year}_{end_year}"

        # Determine phase
        # Phase 1: Positive validation (every day sampling)
        # Phase 2: Negative controls (sampled)
        # Phase 3: Full year
        # Phase 4: Multi-year comparison
        if args.sample_every > 1:
            phase = "phase2_negctrl"  # Negative controls use sampling
        elif "full" in period or end_month - start_month >= 9:
            phase = "phase3_full"  # Full year or 9+ months
        elif start_year != end_year:
            phase = "phase4_comparison"  # Multi-year
        else:
            phase = "phase1_baseline"  # Quarterly baseline

        # Build filename: p2_<phase>_<symbol>_<period>.yaml
        # Examples:
        #   p2_phase1_baseline_SPY_2024Q1.yaml
        #   p2_phase2_negctrl_SPY_2024Q1.yaml
        #   p2_phase3_full_SPY_2024_full.yaml
        #   p2_phase4_comparison_SPY_2020_2024.yaml
        output_file = output_dir / f"p2_{phase}_{args.symbol}_{period}.yaml"
    else:
        output_file = Path(args.output)

    # Write YAML output
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        yaml.dump(results, f, default_flow_style=False, sort_keys=False)

    logger.info(f"\nResults written to: {output_file}")

    # Final verdict
    detection_ok = 3 <= summary["detection_rate_pct"] <= 10
    accuracy_ok = summary["accuracy_rate_pct"] >= 70

    if detection_ok and accuracy_ok:
        logger.info("\n✅ PHASE 1 VALIDATION PASSED")
        logger.info("   Detection rate in expected range (3-10%)")
        logger.info("   Accuracy rate meets threshold (≥70%)")
        logger.info("   → Ready to proceed to Phase 2 (negative controls)")
    elif not detection_ok and summary["detection_rate_pct"] < 3:
        logger.warning("\n⚠️  DETECTION RATE TOO LOW (<3%)")
        logger.warning("   Action: Consider decreasing thresholds")
        logger.warning("   - Persistence: 70% → 60% (18/30 days)")
        logger.warning("   - Magnitude: $5B → $3B")
    elif not detection_ok and summary["detection_rate_pct"] > 10:
        logger.warning("\n⚠️  DETECTION RATE TOO HIGH (>10%)")
        logger.warning("   Action: Consider increasing thresholds")
        logger.warning("   - Persistence: 70% → 80% (24/30 days)")
        logger.warning("   - Magnitude: $5B → $7B")
    elif not accuracy_ok:
        logger.warning("\n⚠️  ACCURACY RATE TOO LOW (<70%)")
        logger.warning("   Action: Revise prompt mechanical guidance")
        logger.warning("   Review disagreements to identify issues")

    return 0 if (detection_ok and accuracy_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
