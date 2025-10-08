#!/usr/bin/env python3
"""
Pattern Taxonomy Validation Script - Issue #79
Validates core mechanical patterns using obfuscation tests across full 2024 dataset.

Proof-of-concept: Start with single pattern to validate workflow.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Optional
import yaml
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.market_mechanics_agent import MarketMechanicsAgent
from validation.pattern_taxonomy import PatternTaxonomy, ValidationCriteria
from validation.data_obfuscation import DataObfuscator
from cache.unified_cache import UnifiedCacheManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PatternTaxonomyValidator:
    """
    Validates patterns using obfuscation tests to prove they work without context.

    Issue #79 Requirements:
    - Obfuscation: Pattern works without date/ticker context
    - Success Rate: >60% with 30+ samples
    - Economic Value: >20bps after costs
    - Academic Support: Clear causal mechanism
    """

    def __init__(self, symbol: str = "SPY"):
        self.symbol = symbol
        self.cache = UnifiedCacheManager()
        self.taxonomy = PatternTaxonomy()
        self.obfuscator = DataObfuscator()
        self.agent = None  # Lazy init

        # Validation tracking
        self.test_dates = []
        self.failed_dates = []
        self.data_gaps = []
        self.results = {}

    def get_test_date_range(self, start_date: str, end_date: str) -> List[str]:
        """Get all trading days in range from cache."""
        logger.info(f"Scanning cache for dates between {start_date} and {end_date}")

        # Get available dates from cache
        cache_dir = Path('.cache/options') / self.symbol
        if not cache_dir.exists():
            logger.error(f"Cache directory not found: {cache_dir}")
            return []

        available_dates = []
        for file_path in sorted(cache_dir.glob("*.pickle")):
            date_str = file_path.stem  # e.g., "2024-01-02"
            if start_date <= date_str <= end_date:
                available_dates.append(date_str)

        logger.info(f"Found {len(available_dates)} dates in cache")
        return available_dates

    def validate_data_continuity(self, dates: List[str]) -> Dict:
        """
        Check data continuity and identify gaps.
        Returns gaps that need to be filled by agent.
        """
        logger.info(f"Validating data continuity for {len(dates)} dates")

        available = []
        missing = []

        for date_str in dates:
            try:
                # Check if options data exists and is valid
                options_data = self.cache.get_options_data(self.symbol, date_str)
                if options_data is not None and not options_data.empty:
                    available.append(date_str)
                else:
                    missing.append(date_str)
                    logger.warning(f"Missing or empty data for {date_str}")
            except Exception as e:
                missing.append(date_str)
                logger.warning(f"Error checking data for {date_str}: {e}")

        continuity_report = {
            'total_dates': len(dates),
            'available_count': len(available),
            'missing_count': len(missing),
            'available_dates': available,
            'missing_dates': missing,
            'continuity_pct': (len(available) / len(dates) * 100) if dates else 0
        }

        logger.info(f"Data continuity: {continuity_report['continuity_pct']:.1f}% ({len(available)}/{len(dates)} dates)")

        if missing:
            logger.warning(f"Missing data for {len(missing)} dates: {missing[:5]}{'...' if len(missing) > 5 else ''}")

        return continuity_report

    def validate_pattern_with_obfuscation(
        self,
        pattern_name: str,
        dates: List[str],
        confidence_threshold: float = 60.0
    ) -> Dict:
        """
        Validate single pattern using obfuscation test.

        Args:
            pattern_name: Pattern to validate (e.g., 'gamma_positioning')
            dates: List of dates to test
            confidence_threshold: Minimum confidence for detection

        Returns:
            Validation results with pattern detection metrics
        """
        logger.info(f"=" * 80)
        logger.info(f"PATTERN VALIDATION: {pattern_name}")
        logger.info(f"=" * 80)
        logger.info(f"Testing {len(dates)} dates with obfuscation")
        logger.info(f"Confidence threshold: {confidence_threshold}%")
        logger.info(f"Symbol: {self.symbol}")

        # Initialize agent if needed
        if self.agent is None:
            logger.info("Initializing MarketMechanicsAgent...")
            self.agent = MarketMechanicsAgent(symbol=self.symbol)

        detections = []
        high_confidence_count = 0
        failed_fetches = []

        for i, date_str in enumerate(dates, 1):
            logger.info(f"\n[{i}/{len(dates)}] Testing {date_str}...")

            try:
                # Agent will fetch data (with cache fallback → API fallback)
                # Create experiment description focused on the pattern
                experiment_desc = self._generate_pattern_experiment(pattern_name, date_str)

                # Run experiment with obfuscation
                result = self.agent.run_experiment(
                    experiment_description=experiment_desc,
                    date=date_str,
                    obfuscate=True  # Critical: prevent LLM from seeing real dates/tickers
                )

                # Check if pattern was detected
                # Handle both error returns and successful results
                if result and isinstance(result, dict):
                    # Debug: log result structure
                    logger.debug(f"Result keys: {result.keys()}")
                    logger.debug(f"Full result: {result}")

                    # Check for error status
                    if result.get('status') == 'error':
                        logger.warning(f"  ❌ Agent returned error: {result.get('error', 'Unknown error')}")
                        failed_fetches.append(date_str)
                        continue

                    # Get mechanics interpretation from result
                    # NOTE: MarketMechanicsAgent returns 'mechanics_interpretation', not 'llm_analysis'
                    mechanics = result.get('mechanics_interpretation', {})

                    confidence = mechanics.get('confidence', 0)

                    # Extract obfuscated date from agent result
                    obfuscation_meta = result.get('obfuscation_metadata', {})
                    date_obfuscated = obfuscation_meta.get('obfuscated_date', date_str)

                    detection = {
                        'date': date_str,
                        'date_obfuscated': date_obfuscated,  # From agent's obfuscation_metadata
                        'confidence': confidence,
                        'detected': confidence >= confidence_threshold,
                        'who': mechanics.get('who', 'N/A'),
                        'whom': mechanics.get('whom', 'N/A'),
                        'what': mechanics.get('what', 'N/A'),
                        'gex_metrics': result.get('gex_metrics', {}),
                        'obfuscation_verified': obfuscation_meta.get('obfuscated', False)
                    }

                    detections.append(detection)

                    if detection['detected']:
                        high_confidence_count += 1
                        logger.info(f"  ✅ DETECTED: {confidence}% confidence")
                        logger.info(f"     WHO: {detection['who']}")
                        logger.info(f"     WHOM: {detection['whom']}")
                        logger.info(f"     WHAT: {detection['what']}")
                    else:
                        logger.info(f"  ⚠️  Low confidence: {confidence}%")

                else:
                    logger.warning(f"  ❌ No analysis result for {date_str}")
                    failed_fetches.append(date_str)

            except Exception as e:
                logger.error(f"  ❌ Error testing {date_str}: {e}")
                failed_fetches.append(date_str)
                self.failed_dates.append({'date': date_str, 'error': str(e)})

        # Calculate metrics
        total_tested = len(detections)
        success_rate = (high_confidence_count / total_tested * 100) if total_tested > 0 else 0

        validation_result = {
            'pattern_name': pattern_name,
            'test_metadata': {
                'symbol': self.symbol,
                'test_period': f"{dates[0]} to {dates[-1]}",
                'total_dates_requested': len(dates),
                'total_dates_tested': total_tested,
                'failed_fetches': len(failed_fetches),
                'confidence_threshold': confidence_threshold,
                'obfuscation_enabled': True,
                'test_date': datetime.now().isoformat()
            },
            'detection_metrics': {
                'high_confidence_detections': high_confidence_count,
                'low_confidence_detections': total_tested - high_confidence_count,
                'success_rate_pct': success_rate,
                'total_tested': total_tested
            },
            'obfuscation_test': {
                'passed': success_rate >= 60.0 and total_tested >= 30,
                'success_rate': success_rate,
                'sample_size': total_tested,
                'required_success_rate': 60.0,
                'required_sample_size': 30,
                'verdict': self._generate_verdict(success_rate, total_tested)
            },
            'detections': detections,
            'failed_dates': failed_fetches
        }

        # Log summary
        logger.info(f"\n" + "=" * 80)
        logger.info(f"VALIDATION SUMMARY: {pattern_name}")
        logger.info(f"=" * 80)
        logger.info(f"Dates Tested: {total_tested}/{len(dates)}")
        logger.info(f"High-Confidence Detections: {high_confidence_count}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Obfuscation Test: {'✅ PASSED' if validation_result['obfuscation_test']['passed'] else '❌ FAILED'}")

        if failed_fetches:
            logger.warning(f"Failed Fetches: {len(failed_fetches)} dates")
            logger.warning(f"  Dates: {failed_fetches[:5]}{'...' if len(failed_fetches) > 5 else ''}")

        return validation_result

    def _generate_pattern_experiment(self, pattern_name: str, date_str: str) -> str:
        """Generate experiment description focused on specific pattern."""
        pattern_experiments = {
            'gamma_positioning': (
                f"Analyze {self.symbol} gamma exposure and dealer positioning on {date_str}. "
                "Focus on: 1) Total gamma exposure magnitude and sign, "
                "2) Dealer delta hedging requirements, "
                "3) Price dampening/amplification effects from gamma positioning."
            ),
            'stock_pinning': (
                f"Analyze {self.symbol} option expiration dynamics on {date_str}. "
                "Focus on: 1) Large open interest concentrations at specific strikes, "
                "2) Gamma explosion near high-OI strikes, "
                "3) Pinning effects attracting price to strikes."
            ),
            '0dte_hedging': (
                f"Analyze {self.symbol} 0DTE option hedging flows on {date_str}. "
                "Focus on: 1) Rapid gamma changes requiring immediate hedging, "
                "2) Strike breach cascade effects, "
                "3) Dealer forced hedging at specific price levels."
            ),
            'dealer_trap': (
                f"Analyze {self.symbol} gamma flip point positioning on {date_str}. "
                "Focus on: 1) Distance to gamma flip point, "
                "2) Dealer positioning stability at flip, "
                "3) Forced unwinding or hedging escalation near flip."
            ),
            'friday_330_squeeze': (
                f"Analyze {self.symbol} end-of-day gamma dynamics on {date_str}. "
                "Focus on: 1) Final hedging window before expiration, "
                "2) Weekend gamma risk management, "
                "3) Directional momentum into close."
            ),
            'volume_anomaly': (
                f"Analyze {self.symbol} unusual options volume on {date_str}. "
                "Focus on: 1) 100K+ contract flows, "
                "2) Institutional positioning signals, "
                "3) Market impact of large flows."
            )
        }

        return pattern_experiments.get(
            pattern_name,
            f"Analyze {self.symbol} options market mechanics on {date_str}."
        )

    def _generate_verdict(self, success_rate: float, sample_size: int) -> str:
        """Generate human-readable verdict."""
        if sample_size < 30:
            return f"INSUFFICIENT_SAMPLES - Need 30+, have {sample_size}"
        elif success_rate >= 60.0:
            return f"MECHANICAL - {success_rate:.1f}% success with {sample_size} samples (validated)"
        elif success_rate >= 50.0:
            return f"PROBABILISTIC - {success_rate:.1f}% success (borderline)"
        else:
            return f"NARRATIVE/FOLKLORE - {success_rate:.1f}% success (not validated)"

    def save_results(self, validation_result: Dict, output_dir: Path = None):
        """Save validation results to YAML file."""
        if output_dir is None:
            output_dir = Path('reports/validation/pattern_taxonomy')

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename: pattern_TICKER_daterange.yaml (e.g., gamma_positioning_SPY_2024Q1.yaml)
        pattern_name = validation_result['pattern_name']
        symbol = validation_result.get('test_metadata', {}).get('symbol', 'UNKNOWN')
        start_date = validation_result.get('test_metadata', {}).get('start_date', '')
        end_date = validation_result.get('test_metadata', {}).get('end_date', '')

        # Extract quarter/year from date range (e.g., 2024-01-02 to 2024-03-29 -> 2024Q1)
        if start_date and end_date:
            year = start_date[:4]
            start_month = int(start_date[5:7])
            quarter = (start_month - 1) // 3 + 1
            date_label = f"{year}Q{quarter}"
        else:
            date_label = datetime.now().strftime('%Y%m%d')

        filename = f"{pattern_name}_{symbol}_{date_label}.yaml"
        filepath = output_dir / filename

        # Save as YAML
        with open(filepath, 'w') as f:
            yaml.dump(validation_result, f, default_flow_style=False, sort_keys=False)

        logger.info(f"\n✅ Results saved to: {filepath}")
        return filepath


def main():
    """Main entry point for pattern validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate pattern taxonomy with obfuscation tests")
    parser.add_argument('--pattern', type=str, default='gamma_positioning',
                        help='Pattern to validate (default: gamma_positioning)')
    parser.add_argument('--symbol', type=str, default='SPY',
                        help='Symbol to test (default: SPY)')
    parser.add_argument('--start-date', type=str, default='2024-01-02',
                        help='Start date (default: 2024-01-02)')
    parser.add_argument('--end-date', type=str, default='2024-06-28',
                        help='End date (default: 2024-06-28)')
    parser.add_argument('--confidence', type=float, default=60.0,
                        help='Confidence threshold (default: 60.0)')
    parser.add_argument('--check-continuity', action='store_true',
                        help='Check data continuity before running test')

    args = parser.parse_args()

    # Initialize validator
    validator = PatternTaxonomyValidator(symbol=args.symbol)

    # Get test dates
    test_dates = validator.get_test_date_range(args.start_date, args.end_date)

    if not test_dates:
        logger.error(f"No dates found in cache for {args.symbol} between {args.start_date} and {args.end_date}")
        return 1

    # Check continuity if requested
    if args.check_continuity:
        continuity_report = validator.validate_data_continuity(test_dates)

        # Save continuity report
        continuity_path = Path('reports/validation/data_continuity.yaml')
        continuity_path.parent.mkdir(parents=True, exist_ok=True)
        with open(continuity_path, 'w') as f:
            yaml.dump(continuity_report, f, default_flow_style=False)

        logger.info(f"Continuity report saved to: {continuity_path}")

        if continuity_report['continuity_pct'] < 90:
            logger.warning(f"⚠️  Data continuity is {continuity_report['continuity_pct']:.1f}% - expect some failed fetches")
            logger.warning("Agent will attempt to fetch missing data via API")

    # Run validation
    logger.info(f"\n🚀 Starting validation for pattern: {args.pattern}")
    validation_result = validator.validate_pattern_with_obfuscation(
        pattern_name=args.pattern,
        dates=test_dates,
        confidence_threshold=args.confidence
    )

    # Save results
    output_path = validator.save_results(validation_result)

    # Print final verdict
    obfuscation_test = validation_result['obfuscation_test']
    logger.info(f"\n" + "=" * 80)
    logger.info(f"FINAL VERDICT: {obfuscation_test['verdict']}")
    logger.info(f"=" * 80)

    if obfuscation_test['passed']:
        logger.info(f"✅ Pattern '{args.pattern}' VALIDATED as mechanical")
        logger.info(f"   Success rate: {obfuscation_test['success_rate']:.1f}%")
        logger.info(f"   Sample size: {obfuscation_test['sample_size']}")
        return 0
    else:
        logger.warning(f"❌ Pattern '{args.pattern}' NOT VALIDATED")
        logger.warning(f"   Success rate: {obfuscation_test['success_rate']:.1f}% (need 60%+)")
        logger.warning(f"   Sample size: {obfuscation_test['sample_size']} (need 30+)")
        return 1


if __name__ == '__main__':
    sys.exit(main())