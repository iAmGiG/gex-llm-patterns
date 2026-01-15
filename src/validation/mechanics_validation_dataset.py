"""
Mechanics Validation Dataset - Issue #59
Historical market mechanics events for validating LLM interpretation accuracy.

Core objective: Test if LLM can correctly identify WHO forces WHOM to do WHAT
in documented market mechanics events.

Key Features:
- Data Obfuscation: Prevents training data leakage by anonymizing dates/tickers
- Historical Events: 6 curated market events (GME squeeze, COVID crash, etc.)
- Accuracy Scoring: Quantifies LLM market mechanics interpretation capability
- Academic Rigor: Normal vs obfuscated validation for unbiased testing

Usage Examples:
    # Standard academic validation (default - obfuscated for rigor)
    result = quick_validate_event("covid_crash_2020")

    # Development/debugging validation (not recommended for research)
    result = quick_validate_event("covid_crash_2020", obfuscate_data=False)

    # Compare both to detect training data leakage
    normal = quick_validate_event("covid_crash_2020", obfuscate_data=False)
    obfuscated = quick_validate_event("covid_crash_2020")  # Default obfuscated
    leakage = normal.accuracy_score - obfuscated.accuracy_score

See docs/validation-framework.md for comprehensive documentation.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.agents.market_mechanics_agent import MarketMechanicsAgent
from src.tools.autogen_tools import (
    calculate_gamma_exposure,
    fetch_market_data,
    fetch_options_data,
    process_historical_gex_range,
)
from src.utils.date_utils import parse_date_string, today_str
from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator

logger = logging.getLogger(__name__)


@dataclass
class MechanicsEvent:
    """Structure for documented market mechanics events."""

    event_id: str
    symbol: str
    start_date: str
    end_date: str
    event_type: str  # 'gamma_squeeze', 'crash_rehedging', 'opex_pinning', etc.
    documented_mechanics: Dict[str, str]  # who, forces, what, outcome
    expected_llm_response: str
    confidence_threshold: float = 0.75
    # Track what data we actually have
    data_availability: Optional[Dict] = None


@dataclass
class ValidationResult:
    """Results from LLM validation against known events."""

    event_id: str
    llm_response: Dict[str, Any]
    expected_mechanics: Dict[str, str]
    accuracy_score: float
    matches_expected: bool
    analysis_notes: str


class MechanicsValidationDataset:
    """Curated dataset of historical market mechanics events for LLM validation.

    This class manages known market events, fetches historical data, and validates LLM interpretations against
    documented mechanics.
    """

    def __init__(self, data_dir: str = "reports/validation_experiments"):
        """Initialize validation dataset.

        Args:
            data_dir: Directory to store validation data and results (follows reports/ structure)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize market mechanics agent for LLM validation
        self.agent = MarketMechanicsAgent()

        # Load or create the curated events dataset
        self.events = self._load_curated_events()

        logger.info(f"Initialized validation dataset with {len(self.events)} events")

    def _load_curated_events(self) -> List[MechanicsEvent]:
        """Load the curated list of known market mechanics events."""

        events = [
            # GameStop Gamma Squeeze - January 2021
            MechanicsEvent(
                event_id="gme_squeeze_2021",
                symbol="GME",
                start_date="2021-01-11",
                end_date="2021-01-28",
                event_type="gamma_squeeze",
                documented_mechanics={
                    "who": "Retail options buyers",
                    "forces": "Market makers",
                    "what": "Massive delta hedging buying amplifying price moves",
                    "outcome": "Forced covering creates positive feedback loop",
                },
                expected_llm_response="Retail call buying forces MM hedging creating squeeze dynamics",
                confidence_threshold=0.8,
            ),
            # Tesla Stock Split Rally - August 2020
            MechanicsEvent(
                event_id="tsla_gamma_2020",
                symbol="TSLA",
                start_date="2020-08-11",
                end_date="2020-08-28",
                event_type="gamma_squeeze",
                documented_mechanics={
                    "who": "Options flow (retail + institutional)",
                    "forces": "Dealers",
                    "what": "Accelerating gamma hedging amplifies split announcement rally",
                    "outcome": "Positive gamma regime creates momentum amplification",
                },
                expected_llm_response="Options-driven gamma hedging amplifies Tesla rally dynamics",
                confidence_threshold=0.75,
            ),
            # AMC Meme Stock Squeeze - May 2021
            MechanicsEvent(
                event_id="amc_squeeze_2021",
                symbol="AMC",
                start_date="2021-05-24",
                end_date="2021-06-02",
                event_type="gamma_squeeze",
                documented_mechanics={
                    "who": "Retail coordinated buying",
                    "forces": "Market makers and short sellers",
                    "what": "Forced hedging and covering creates price acceleration",
                    "outcome": "Similar mechanics to GME but smaller scale",
                },
                expected_llm_response="Retail gamma squeeze forcing MM hedging similar to GME pattern",
                confidence_threshold=0.75,
            ),
            # COVID Market Crash - March 2020
            MechanicsEvent(
                event_id="covid_crash_2020",
                symbol="SPY",
                start_date="2020-03-09",
                end_date="2020-03-23",
                event_type="crash_rehedging",
                documented_mechanics={
                    "who": "Put hedging flows",
                    "forces": "Dealers",
                    "what": "Forced selling into declining market amplifies crash",
                    "outcome": "Negative gamma regime creates selling feedback loops",
                },
                expected_llm_response="Put hedging forces dealer selling creating negative feedback loop",
                confidence_threshold=0.8,
            ),
            # Triple Witching OPEX - March 2021
            MechanicsEvent(
                event_id="opex_pin_mar2021",
                symbol="SPY",
                start_date="2021-03-15",
                end_date="2021-03-19",
                event_type="opex_pinning",
                documented_mechanics={
                    "who": "Market makers",
                    "forces": "Underlying price",
                    "what": "Active management to maximize option value decay at key strikes",
                    "outcome": "Price gravitates toward max pain levels",
                },
                expected_llm_response="MMs actively pinning SPY to max pain for option expiration",
                confidence_threshold=0.7,
            ),
            # VIX Spike Event - February 2018
            MechanicsEvent(
                event_id="vix_spike_2018",
                symbol="SPY",
                start_date="2018-02-02",
                end_date="2018-02-09",
                event_type="volatility_unwind",
                documented_mechanics={
                    "who": "Volatility product unwinding",
                    "forces": "Market makers and volatility traders",
                    "what": "Forced selling as volatility products implode",
                    "outcome": "Rapid deleveraging amplifies market decline",
                },
                expected_llm_response="Volatility product unwinding forces systematic selling pressure",
                confidence_threshold=0.75,
            ),
        ]

        logger.info(f"Loaded {len(events)} curated market mechanics events")
        return events

    def validate_event(
        self, event: MechanicsEvent, use_cached_data: bool = True, obfuscate_data: bool = True
    ) -> ValidationResult:
        """Validate LLM interpretation against a known market mechanics event.

        Args:
            event: The market event to analyze
            use_cached_data: Whether to use cached data for faster processing
            obfuscate_data: Whether to obfuscate dates/tickers (DEFAULT: True for academic rigor)

        Returns:
            ValidationResult with LLM analysis and accuracy assessment

        Note:
            Academic rigor is the default - obfuscated validation prevents training data leakage.
            Set obfuscate_data=False only for development/debugging purposes.
        """
        try:
            logger.info(f"Validating event: {event.event_id} (obfuscated={obfuscate_data})")

            # Ensure we have data for this event
            self._ensure_event_data(event, use_cached_data)

            # Apply data obfuscation if requested
            if obfuscate_data:
                event_for_analysis = self._apply_obfuscation(event)
                logger.info(f"Data obfuscated: {event.symbol} → {event_for_analysis.symbol}")
            else:
                event_for_analysis = event

            # Get LLM analysis for the event period
            llm_analysis = self._analyze_event_period(event_for_analysis)

            # Score the LLM response against expected mechanics
            accuracy_score, matches_expected = self._score_llm_response(
                llm_analysis, event.documented_mechanics, event.expected_llm_response
            )

            # Create validation result
            result = ValidationResult(
                event_id=event.event_id,
                llm_response=llm_analysis,
                expected_mechanics=event.documented_mechanics,
                accuracy_score=accuracy_score,
                matches_expected=matches_expected,
                analysis_notes=self._generate_analysis_notes(llm_analysis, event),
            )

            # Save results for review
            self._save_validation_result(result)

            logger.info(f"Event {event.event_id} validation: {accuracy_score:.1%} accuracy")
            return result

        except Exception as e:
            logger.error(f"Error validating event {event.event_id}: {e}")
            return ValidationResult(
                event_id=event.event_id,
                llm_response={"error": str(e)},
                expected_mechanics=event.documented_mechanics,
                accuracy_score=0.0,
                matches_expected=False,
                analysis_notes=f"Validation failed: {e}",
            )

    def _ensure_event_data(self, event: MechanicsEvent, use_cached: bool = True):
        """Ensure we have the necessary data for event analysis."""
        try:
            # Fetch options data for the event period
            options_result = fetch_options_data(
                symbol=event.symbol, trading_date=event.start_date, use_cache=use_cached
            )

            if options_result["status"] != "success":
                logger.warning(f"Limited options data for {event.event_id}")

            # Fetch market data for context
            market_result = fetch_market_data(
                symbol=event.symbol, start_date=event.start_date, end_date=event.end_date, use_cache=use_cached
            )

            if market_result["status"] != "success":
                logger.warning(f"Limited market data for {event.event_id}")

            # Process historical GEX for the event period if we have data
            if options_result["status"] == "success":
                gex_result = process_historical_gex_range(
                    symbol=event.symbol,
                    start_date=event.start_date,
                    end_date=event.end_date,
                    max_workers=2,  # Conservative for validation
                )

                if gex_result["status"] == "success":
                    logger.info(f"GEX data processed for {event.event_id}")
                else:
                    logger.warning(f"GEX processing issues for {event.event_id}")

        except Exception as e:
            logger.warning(f"Data preparation for {event.event_id} had issues: {e}")

    def _apply_obfuscation(self, event: MechanicsEvent) -> MechanicsEvent:
        """Apply data obfuscation to prevent LLM training data leakage.

        Args:
            event: Original market event

        Returns:
            Obfuscated event with anonymous dates and tickers
        """
        try:
            obfuscator = DataObfuscator()

            # Create date range for the event
            event_dates = (
                pd.date_range(start=event.start_date, end=event.end_date, freq="D").strftime("%Y-%m-%d").tolist()
            )

            # Obfuscate dates and ticker
            date_mapping = obfuscator.obfuscate_dates(event_dates, event.start_date)
            ticker_mapping = obfuscator.obfuscate_tickers([event.symbol])

            # Create obfuscated event
            obfuscated_event = MechanicsEvent(
                event_id=f"{event.event_id}_obfuscated",
                symbol=ticker_mapping[event.symbol],
                start_date=date_mapping[event.start_date],
                end_date=date_mapping[event.end_date],
                event_type=event.event_type,
                documented_mechanics=event.documented_mechanics,  # Keep original for scoring
                expected_llm_response=event.expected_llm_response,
                confidence_threshold=event.confidence_threshold,
            )

            # Store obfuscation mappings for potential reversal
            obfuscated_event.data_availability = {
                "obfuscation_applied": True,
                "date_mapping": date_mapping,
                "ticker_mapping": ticker_mapping,
                "original_symbol": event.symbol,
                "original_dates": f"{event.start_date} to {event.end_date}",
            }

            return obfuscated_event

        except Exception as e:
            logger.error(f"Error applying obfuscation to {event.event_id}: {e}")
            return event  # Return original if obfuscation fails

    def _analyze_event_period(self, event: MechanicsEvent) -> Dict[str, Any]:
        """Analyze the event period using the MarketMechanicsAgent."""
        try:
            # Set the agent to analyze the event symbol
            self.agent.symbol = event.symbol

            # Analyze the key date in the event period (usually start date)
            analysis_date = parse_date_string(event.start_date)

            # Get LLM analysis
            analysis_result = self.agent.daily_analysis(analysis_date)

            if analysis_result and "mechanics_interpretation" in analysis_result:
                return analysis_result
            else:
                logger.warning(f"No mechanics interpretation for {event.event_id}")
                return {"error": "No LLM interpretation generated"}

        except Exception as e:
            logger.error(f"Error analyzing {event.event_id}: {e}")
            return {"error": str(e)}

    def _score_llm_response(
        self, llm_analysis: Dict, expected_mechanics: Dict, expected_response: str
    ) -> tuple[float, bool]:
        """Score LLM response against expected market mechanics.

        Returns:
            (accuracy_score, matches_expected) tuple
        """
        try:
            score = 0.0
            max_points = 4.0  # who, forces, what, confidence

            # Extract LLM mechanics interpretation
            mechanics = llm_analysis.get("mechanics_interpretation", {})

            # Check WHO identification (25% weight)
            if "who" in mechanics and "who" in expected_mechanics:
                if self._check_semantic_match(mechanics["who"], expected_mechanics["who"]):
                    score += 1.0

            # Check FORCES identification (25% weight)
            if "whom" in mechanics and "forces" in expected_mechanics:
                if self._check_semantic_match(mechanics["whom"], expected_mechanics["forces"]):
                    score += 1.0

            # Check WHAT identification (25% weight)
            if "what" in mechanics and "what" in expected_mechanics:
                if self._check_semantic_match(mechanics["what"], expected_mechanics["what"]):
                    score += 1.0

            # Check confidence level (25% weight)
            confidence = llm_analysis.get("confidence", 0)
            if confidence >= 70:  # Reasonable confidence threshold
                score += 1.0

            accuracy_score = score / max_points
            matches_expected = accuracy_score >= 0.6  # 60% threshold for "match"

            return accuracy_score, matches_expected

        except Exception as e:
            logger.error(f"Error scoring LLM response: {e}")
            return 0.0, False

    def _check_semantic_match(self, llm_text: str, expected_text: str) -> bool:
        """Check if LLM response semantically matches expected text."""
        # Simple keyword-based matching (can be enhanced with semantic similarity)
        llm_lower = llm_text.lower()
        expected_lower = expected_text.lower()

        # Key terms that should appear
        key_terms = {
            "retail",
            "market makers",
            "dealers",
            "hedge",
            "covering",
            "squeeze",
            "buying",
            "selling",
            "forced",
            "amplify",
        }

        # Check if key concepts are present
        matches = 0
        total_terms = 0

        for term in key_terms:
            if term in expected_lower:
                total_terms += 1
                if term in llm_lower:
                    matches += 1

        # Require at least 50% of key terms to match
        return (matches / max(total_terms, 1)) >= 0.5

    def _generate_analysis_notes(self, llm_analysis: Dict, event: MechanicsEvent) -> str:
        """Generate analysis notes comparing LLM output to expected mechanics."""
        mechanics = llm_analysis.get("mechanics_interpretation", {})

        notes = [
            f"Event: {event.event_id} ({event.event_type})",
            f"Expected: {event.expected_llm_response}",
            f"LLM WHO: {mechanics.get('who', 'Not identified')}",
            f"LLM WHOM: {mechanics.get('whom', 'Not identified')}",
            f"LLM WHAT: {mechanics.get('what', 'Not identified')}",
            f"Confidence: {llm_analysis.get('confidence', 0)}%",
        ]

        return " | ".join(notes)

    def _save_validation_result(self, result: ValidationResult):
        """Save validation result to file for analysis following reports structure."""
        try:
            from src.utils.date_utils import format_for_filename

            # Create experiment-specific filename
            timestamp = format_for_filename()
            obfuscated_suffix = "_obfuscated" if result.event_id.endswith("_obfuscated") else "_normal"

            # JSONL for streaming results (good for ongoing experiments)
            results_file = self.data_dir / f"validation_results_{timestamp}.jsonl"

            # JSON for individual experiment results (good for analysis)
            individual_file = self.data_dir / f"{result.event_id}_{timestamp}.json"

            # Convert to dict and add metadata
            result_dict = asdict(result)
            result_dict["timestamp"] = datetime.now().isoformat()
            result_dict["experiment_type"] = "obfuscated" if "_obfuscated" in result.event_id else "normal"
            result_dict["validation_framework_version"] = "1.0"

            # Save to JSONL (append for streaming)
            with open(results_file, "a") as f:
                f.write(json.dumps(result_dict) + "\n")

            # Save individual result (JSON for easy analysis)
            with open(individual_file, "w") as f:
                json.dump(result_dict, f, indent=2)

            logger.info(f"Validation result saved: {individual_file.name}")

        except Exception as e:
            logger.error(f"Error saving validation result: {e}")

    def run_full_validation(self, use_cached_data: bool = True, obfuscate_data: bool = True) -> Dict[str, Any]:
        """Run validation against all curated events with academic rigor by default.

        Args:
            use_cached_data: Whether to use cached data for faster processing
            obfuscate_data: Whether to obfuscate dates/tickers (DEFAULT: True for academic rigor)

        Returns:
            Summary of validation results across all events

        Note:
            Academic rigor is the default - all events validated with obfuscated data.
            Set obfuscate_data=False only for development/debugging.
        """
        logger.info("Starting full validation dataset analysis")

        results = []
        total_events = len(self.events)

        for i, event in enumerate(self.events, 1):
            logger.info(f"Processing event {i}/{total_events}: {event.event_id}")

            try:
                result = self.validate_event(event, use_cached_data, obfuscate_data)
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to validate {event.event_id}: {e}")
                # Continue with other events

        # Generate summary statistics
        if results:
            accuracy_scores = [r.accuracy_score for r in results]
            matches = [r.matches_expected for r in results]

            summary = {
                "total_events": len(results),
                "avg_accuracy": sum(accuracy_scores) / len(accuracy_scores),
                "events_matching": sum(matches),
                "match_rate": sum(matches) / len(matches),
                "results": results,
            }

            logger.info(
                f"Validation complete: {summary['match_rate']:.1%} match rate, {summary['avg_accuracy']:.1%} avg accuracy"
            )

            # Save summary with experiment identification
            from src.utils.date_utils import format_for_filename

            timestamp = format_for_filename()
            summary_file = self.data_dir / f"validation_summary_{timestamp}.json"

            with open(summary_file, "w") as f:
                # Convert results to dicts for JSON serialization
                summary_copy = summary.copy()
                summary_copy["results"] = [asdict(r) for r in results]
                summary_copy["timestamp"] = datetime.now().isoformat()
                summary_copy["experiment_metadata"] = {
                    "framework_version": "1.0",
                    "total_events_tested": len(results),
                    "events_tested": [r.event_id for r in results],
                    "experiment_id": timestamp,
                }
                json.dump(summary_copy, f, indent=2)

            logger.info(f"Validation summary saved: {summary_file.name}")

            return summary

        else:
            logger.error("No validation results generated")
            return {"error": "No results generated"}

    def get_event_by_id(self, event_id: str) -> Optional[MechanicsEvent]:
        """Get a specific event by ID."""
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def list_events(self) -> List[Dict[str, str]]:
        """List all available events with basic info."""
        return [
            {
                "event_id": event.event_id,
                "symbol": event.symbol,
                "date_range": f"{event.start_date} to {event.end_date}",
                "type": event.event_type,
                "expected": event.expected_llm_response,
            }
            for event in self.events
        ]


# Convenience function for quick validation testing
def quick_validate_event(event_id: str, use_cache: bool = True, obfuscate_data: bool = True) -> ValidationResult:
    """Quick validation of a single event with academic rigor by default.

    Args:
        event_id: ID of the event to validate (e.g., 'covid_crash_2020')
        use_cache: Whether to use cached data for faster processing
        obfuscate_data: Whether to obfuscate dates/tickers (DEFAULT: True for academic rigor)

    Returns:
        ValidationResult for the event

    Examples:
        # Standard academic validation (default)
        result = quick_validate_event("covid_crash_2020")

        # Development/debugging only (not recommended for research)
        result = quick_validate_event("covid_crash_2020", obfuscate_data=False)
    """
    dataset = MechanicsValidationDataset()
    event = dataset.get_event_by_id(event_id)

    if event is None:
        raise ValueError(f"Event {event_id} not found")

    return dataset.validate_event(event, use_cache, obfuscate_data)


if __name__ == "__main__":
    # Example usage: validate a specific event
    logging.basicConfig(level=logging.INFO)

    # Test with the COVID crash event
    result = quick_validate_event("covid_crash_2020")
    print(f"Validation result: {result.accuracy_score:.1%} accuracy")
    print(f"Analysis: {result.analysis_notes}")
