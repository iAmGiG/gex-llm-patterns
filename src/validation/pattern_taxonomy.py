"""
Pattern Taxonomy Framework - Mechanical vs Narrative Classification
Distinguishes real structural patterns from market folklore
Based on dealer constraint mechanics and academic validation
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Classification of pattern reality."""
    MECHANICAL = "mechanical"  # Clear causal mechanism, must happen
    PROBABILISTIC = "probabilistic"  # Statistical tendency, not guaranteed
    NARRATIVE = "narrative"  # Story-based, possibly folklore
    UNKNOWN = "unknown"  # Needs further validation


class DealerAction(Enum):
    """Limited set of dealer actions (state machine)."""
    DELTA_HEDGE = "delta_hedge"  # Buy/sell underlying
    GAMMA_HEDGE = "gamma_hedge"  # Trade options (expensive)
    VEGA_HEDGE = "vega_hedge"  # Trade different expirations
    DO_NOTHING = "do_nothing"  # Accept risk
    UNWIND = "unwind"  # Close positions


@dataclass
class CausalMechanism:
    """Documents WHY a pattern must occur."""
    constraint: str  # What forces the action
    required_action: DealerAction  # What dealers MUST do
    why_required: str  # Why this action is necessary
    alternative_actions: List[Tuple[DealerAction, str]]  # Why alternatives are inferior
    observable_impact: str  # Market impact we can measure
    academic_support: Optional[str] = None  # Supporting research

    def is_mechanical(self) -> bool:
        """Pattern is mechanical if dealer has no real choice."""
        return len(self.alternative_actions) == 0 or all(
            "impossible" in reason.lower() or "prohibited" in reason.lower()
            for _, reason in self.alternative_actions
        )


@dataclass
class ValidationCriteria:
    """Criteria for validating pattern reality."""
    out_of_sample_required: int = 30  # Minimum OOS tests
    min_success_rate: float = 0.60  # Minimum success rate
    economic_significance: float = 0.002  # 20bps after costs
    degradation_threshold: float = 0.10  # Max annual alpha decay
    obfuscation_test: bool = True  # Must work without context


@dataclass
class PatternValidation:
    """Tracks pattern validation status."""
    pattern_name: str
    pattern_type: PatternType
    causal_mechanism: Optional[CausalMechanism]

    # Validation tests
    has_causal_mechanism: bool = False
    out_of_sample_count: int = 0
    out_of_sample_success: float = 0.0
    economic_value_after_costs: float = 0.0
    annual_degradation: float = 0.0
    passes_obfuscation: bool = False

    # Academic validation
    academic_papers: List[str] = field(default_factory=list)
    empirical_evidence: List[str] = field(default_factory=list)

    # Final classification
    is_validated: bool = False
    validation_date: Optional[str] = None
    confidence_score: float = 0.0

    def calculate_validation(self, criteria: ValidationCriteria) -> bool:
        """Determine if pattern is validated as real."""
        checks = [
            self.has_causal_mechanism,
            self.out_of_sample_count >= criteria.out_of_sample_required,
            self.out_of_sample_success >= criteria.min_success_rate,
            self.economic_value_after_costs >= criteria.economic_significance,
            self.annual_degradation <= criteria.degradation_threshold,
            self.passes_obfuscation or not criteria.obfuscation_test
        ]

        # Calculate confidence based on passed checks
        self.confidence_score = sum(checks) / len(checks)
        self.is_validated = self.confidence_score >= 0.8

        if self.is_validated:
            self.validation_date = datetime.now().isoformat()

        return self.is_validated


class PatternTaxonomy:
    """
    Systematic taxonomy mapping dealer constraints to tradeable patterns.
    Distinguishes mechanical patterns from narrative folklore.
    """

    def __init__(self):
        self.validations: Dict[str, PatternValidation] = {}
        self.criteria = ValidationCriteria()
        self._initialize_known_patterns()

    def _initialize_known_patterns(self):
        """Initialize patterns with known academic validation."""

        # GAMMA POSITIONING - Mechanical (Buis et al. 2024)
        self.validations['gamma_positioning'] = PatternValidation(
            pattern_name="Gamma Positioning Effects",
            pattern_type=PatternType.MECHANICAL,
            causal_mechanism=CausalMechanism(
                constraint="Delta-neutral mandate with gamma exposure",
                required_action=DealerAction.DELTA_HEDGE,
                why_required="Regulatory requirement to maintain delta neutrality",
                alternative_actions=[
                    (DealerAction.DO_NOTHING, "Violates risk limits and mandate"),
                    (DealerAction.GAMMA_HEDGE, "Too expensive and illiquid")
                ],
                observable_impact="Positive gamma dampens volatility, negative amplifies",
                academic_support="Buis et al. (2024) 'Gamma positioning and market quality'"
            ),
            has_causal_mechanism=True,
            academic_papers=["Buis et al. 2024"],
            passes_obfuscation=True
        )

        # STOCK PINNING - Mechanical (Jeannin et al. 2008)
        self.validations['stock_pinning'] = PatternValidation(
            pattern_name="Option Expiration Pinning",
            pattern_type=PatternType.MECHANICAL,
            causal_mechanism=CausalMechanism(
                constraint="Large open interest at strike near expiration",
                required_action=DealerAction.DELTA_HEDGE,
                why_required="Gamma explosion near strike requires constant rehedging",
                alternative_actions=[
                    (DealerAction.UNWIND, "Impossible due to liquidity and size"),
                    (DealerAction.DO_NOTHING, "Gamma risk exceeds all limits")
                ],
                observable_impact="Price gravitates to heavy OI strikes",
                academic_support="Jeannin et al. (2008) theoretical proof of pinning"
            ),
            has_causal_mechanism=True,
            out_of_sample_success=0.75,
            academic_papers=["Jeannin et al. 2008"],
            passes_obfuscation=True
        )

        # 0DTE HEDGING - Mechanical (Recent papers)
        self.validations['0dte_hedging'] = PatternValidation(
            pattern_name="0DTE Delta Hedging Flows",
            pattern_type=PatternType.MECHANICAL,
            causal_mechanism=CausalMechanism(
                constraint="40-50% of SPX volume in 0DTE options",
                required_action=DealerAction.DELTA_HEDGE,
                why_required="Rapid gamma changes require immediate hedging",
                alternative_actions=[
                    (DealerAction.DO_NOTHING, "Gamma risk compounds exponentially"),
                    (DealerAction.GAMMA_HEDGE, "No time for option hedges at 0DTE")
                ],
                observable_impact="Measurable hedging flows at strike breaches",
                academic_support="0DTEs Trading Gamma Risk and Volatility Propagation"
            ),
            has_causal_mechanism=True,
            academic_papers=["0DTE Gamma Risk 2024"],
            passes_obfuscation=True
        )

        # DEALER TRAP - Potentially Novel
        self.validations['dealer_trap'] = PatternValidation(
            pattern_name="Dealer Trap at Flip Points",
            pattern_type=PatternType.PROBABILISTIC,
            causal_mechanism=CausalMechanism(
                constraint="Systematic targeting of flip point positioning",
                required_action=DealerAction.UNWIND,
                why_required="Position becomes unstable at flip",
                alternative_actions=[
                    (DealerAction.DELTA_HEDGE, "Hedging amplifies losses"),
                    (DealerAction.DO_NOTHING, "Risk escalates past limits")
                ],
                observable_impact="Volatility expansion and directional break",
                academic_support=None  # Needs validation
            ),
            has_causal_mechanism=True,
            passes_obfuscation=False  # Needs testing
        )

        # GAMMA SQUEEZE AT 3:30 - Potentially Novel
        self.validations['friday_330_squeeze'] = PatternValidation(
            pattern_name="Friday 3:30 PM Gamma Effects",
            pattern_type=PatternType.PROBABILISTIC,
            causal_mechanism=CausalMechanism(
                constraint="Weekly option expiration with 30 minutes to close",
                required_action=DealerAction.DELTA_HEDGE,
                why_required="Final hedging window before expiration",
                alternative_actions=[
                    (DealerAction.DO_NOTHING, "Weekend gamma risk unacceptable"),
                    (DealerAction.UNWIND, "Insufficient liquidity in 30 minutes")
                ],
                observable_impact="Directional momentum into close",
                academic_support=None  # Needs validation
            ),
            has_causal_mechanism=True,
            out_of_sample_success=0.75,  # From your testing
            passes_obfuscation=True  # Works without knowing it's Friday
        )

        # VOLUME ANOMALY - Needs Validation
        self.validations['volume_anomaly'] = PatternValidation(
            pattern_name="100K+ Institutional Flow Detection",
            pattern_type=PatternType.UNKNOWN,
            causal_mechanism=None,  # Need to establish mechanism
            has_causal_mechanism=False,
            passes_obfuscation=False
        )

    def classify_pattern(self, pattern_name: str,
                         test_results: Dict[str, Any]) -> PatternValidation:
        """
        Classify a pattern as mechanical, probabilistic, or narrative.
        Updates validation based on test results.
        """
        if pattern_name not in self.validations:
            self.validations[pattern_name] = PatternValidation(
                pattern_name=pattern_name,
                pattern_type=PatternType.UNKNOWN
            )

        validation = self.validations[pattern_name]

        # Update from test results
        if 'out_of_sample' in test_results:
            validation.out_of_sample_count = test_results['out_of_sample']['count']
            validation.out_of_sample_success = test_results['out_of_sample']['success_rate']

        if 'economic_value' in test_results:
            validation.economic_value_after_costs = test_results['economic_value']

        if 'degradation' in test_results:
            validation.annual_degradation = test_results['degradation']

        if 'obfuscation' in test_results:
            validation.passes_obfuscation = test_results['obfuscation']['passed']

        # Determine pattern type based on evidence
        if validation.causal_mechanism:
            if validation.causal_mechanism.is_mechanical():
                validation.pattern_type = PatternType.MECHANICAL
            else:
                validation.pattern_type = PatternType.PROBABILISTIC
        elif validation.out_of_sample_success < 0.55:
            validation.pattern_type = PatternType.NARRATIVE

        # Calculate final validation
        validation.calculate_validation(self.criteria)

        return validation

    def test_obfuscation_resistance(self, pattern_name: str,
                                   obfuscated_results: float,
                                   normal_results: float) -> bool:
        """
        Test if pattern works without context clues.
        Pattern is real if it works when LLM doesn't know:
        - It's Friday at 3:30 PM
        - It's option expiration
        - The specific ticker
        """
        # Pattern should maintain at least 80% of performance when obfuscated
        performance_ratio = obfuscated_results / normal_results if normal_results > 0 else 0

        validation = self.validations.get(pattern_name)
        if validation:
            validation.passes_obfuscation = performance_ratio >= 0.8

        return performance_ratio >= 0.8

    def calculate_economic_significance(self, pattern_name: str,
                                       gross_return: float,
                                       transaction_costs: float = 0.001,
                                       slippage: float = 0.0005) -> float:
        """Calculate if pattern survives real-world frictions."""
        net_return = gross_return - transaction_costs - slippage

        validation = self.validations.get(pattern_name)
        if validation:
            validation.economic_value_after_costs = net_return

        return net_return

    def track_degradation(self, pattern_name: str,
                         historical_performance: List[Tuple[str, float]]) -> float:
        """
        Track if pattern alpha is degrading over time.
        Returns annual degradation rate.
        """
        if len(historical_performance) < 2:
            return 0.0

        # Simple linear degradation calculation
        years = [(datetime.fromisoformat(date).year, perf)
                 for date, perf in historical_performance]

        first_year_avg = sum(p for y, p in years if y == years[0][0]) / len(
            [p for y, p in years if y == years[0][0]])
        last_year_avg = sum(p for y, p in years if y == years[-1][0]) / len(
            [p for y, p in years if y == years[-1][0]])

        years_diff = years[-1][0] - years[0][0]
        if years_diff > 0:
            annual_degradation = (first_year_avg - last_year_avg) / years_diff
        else:
            annual_degradation = 0.0

        validation = self.validations.get(pattern_name)
        if validation:
            validation.annual_degradation = annual_degradation

        return annual_degradation

    def generate_taxonomy_report(self) -> str:
        """Generate comprehensive taxonomy report."""
        mechanical = [v for v in self.validations.values()
                     if v.pattern_type == PatternType.MECHANICAL]
        probabilistic = [v for v in self.validations.values()
                        if v.pattern_type == PatternType.PROBABILISTIC]
        narrative = [v for v in self.validations.values()
                    if v.pattern_type == PatternType.NARRATIVE]
        unknown = [v for v in self.validations.values()
                  if v.pattern_type == PatternType.UNKNOWN]

        report = f"""
DEALER CONSTRAINT PATTERN TAXONOMY
Generated: {datetime.now().isoformat()}
{'=' * 60}

CLASSIFICATION SUMMARY:
- Mechanical Patterns: {len(mechanical)} (must happen due to constraints)
- Probabilistic Patterns: {len(probabilistic)} (statistical tendency)
- Narrative Patterns: {len(narrative)} (likely folklore)
- Unknown Patterns: {len(unknown)} (need more validation)

MECHANICAL PATTERNS (Academically Validated):
"""
        for pattern in mechanical:
            report += f"\n{pattern.pattern_name}:"
            if pattern.causal_mechanism:
                report += f"\n  Constraint: {pattern.causal_mechanism.constraint}"
                report += f"\n  Required Action: {pattern.causal_mechanism.required_action.value}"
                report += f"\n  Academic Support: {pattern.causal_mechanism.academic_support or 'Testing'}"
            report += f"\n  Confidence: {pattern.confidence_score:.0%}"
            report += f"\n  Validated: {'Yes' if pattern.is_validated else 'No'}\n"

        report += "\nPROBABILISTIC PATTERNS (Statistical Edge):\n"
        for pattern in probabilistic:
            report += f"\n{pattern.pattern_name}:"
            report += f"\n  Success Rate: {pattern.out_of_sample_success:.0%}"
            report += f"\n  Obfuscation Test: {'Passed' if pattern.passes_obfuscation else 'Failed'}"
            report += f"\n  Economic Value: {pattern.economic_value_after_costs:.2%}"
            report += f"\n  Degradation: {pattern.annual_degradation:.2%} per year\n"

        report += "\nNARRATIVE PATTERNS (Likely Folklore):\n"
        for pattern in narrative:
            report += f"\n{pattern.pattern_name}:"
            report += f"\n  Reason: Low success rate or no causal mechanism\n"

        report += "\nUNKNOWN PATTERNS (Need Testing):\n"
        for pattern in unknown:
            report += f"\n{pattern.pattern_name}: Requires validation\n"

        report += f"""
VALIDATION CRITERIA:
- Minimum OOS Tests: {self.criteria.out_of_sample_required}
- Minimum Success Rate: {self.criteria.min_success_rate:.0%}
- Economic Significance: {self.criteria.economic_significance:.2%} after costs
- Max Annual Degradation: {self.criteria.degradation_threshold:.0%}
- Must Pass Obfuscation: {self.criteria.obfuscation_test}

KEY FINDING: Patterns that work without context (obfuscated dates, tickers)
represent real structural market mechanics, not narrative folklore.
"""
        return report

    def create_state_machine(self) -> Dict[str, List[Tuple[str, DealerAction]]]:
        """
        Create dealer state machine showing transitions.
        Maps market conditions to forced dealer actions.
        """
        state_machine = {
            "negative_gamma": [
                ("price_rising", DealerAction.DELTA_HEDGE),  # Must buy
                ("price_falling", DealerAction.DELTA_HEDGE),  # Must sell
                ("at_flip_point", DealerAction.UNWIND)  # Position unstable
            ],
            "positive_gamma": [
                ("price_rising", DealerAction.DELTA_HEDGE),  # Sell into strength
                ("price_falling", DealerAction.DELTA_HEDGE),  # Buy into weakness
                ("low_volatility", DealerAction.DO_NOTHING)  # Comfortable position
            ],
            "near_expiration": [
                ("at_strike", DealerAction.DELTA_HEDGE),  # Pin maintenance
                ("away_from_strike", DealerAction.UNWIND),  # Reduce risk
                ("high_gamma", DealerAction.DELTA_HEDGE)  # Constant rehedging
            ],
            "0dte_exposure": [
                ("strike_breach", DealerAction.DELTA_HEDGE),  # Immediate hedge
                ("time_decay", DealerAction.UNWIND),  # Close positions
                ("volatility_spike", DealerAction.GAMMA_HEDGE)  # Emergency hedge
            ]
        }

        return state_machine


def validate_pattern_library():
    """
    Run validation framework on pattern library.
    Distinguishes real patterns from folklore.
    """
    taxonomy = PatternTaxonomy()

    # Example validation data (would come from actual testing)
    test_results = {
        'gamma_positioning': {
            'out_of_sample': {'count': 100, 'success_rate': 0.72},
            'economic_value': 0.008,  # 80bps after costs
            'degradation': 0.02,  # 2% annual degradation
            'obfuscation': {'passed': True}
        },
        'stock_pinning': {
            'out_of_sample': {'count': 50, 'success_rate': 0.75},
            'economic_value': 0.005,
            'degradation': 0.03,
            'obfuscation': {'passed': True}
        },
        'dealer_trap': {
            'out_of_sample': {'count': 20, 'success_rate': 0.58},
            'economic_value': 0.003,
            'degradation': 0.08,
            'obfuscation': {'passed': False}  # Needs context
        }
    }

    # Validate each pattern
    for pattern_name, results in test_results.items():
        validation = taxonomy.classify_pattern(pattern_name, results)
        logger.info(f"Pattern {pattern_name}: {validation.pattern_type.value}, "
                   f"Validated: {validation.is_validated}")

    # Generate report
    report = taxonomy.generate_taxonomy_report()

    # Save report
    with open('reports/pattern_taxonomy_validation.txt', 'w') as f:
        f.write(report)

    return taxonomy


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    taxonomy = validate_pattern_library()
    print(taxonomy.generate_taxonomy_report())