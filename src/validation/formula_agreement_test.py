"""Formula Agreement Test: Normalized vs Absolute GEX Comparison

Tests whether LLM regime detection is calculation-independent by comparing:
- Control: Absolute-scaled GEX (current methodology, -$50B to +$50B)
- Treatment: Normalized GEX (ratio-based, -1.0 to +1.0)

Research Question:
    Does the LLM identify the same regimes regardless of GEX calculation method?

Expected Outcomes:
    AR > 90% = Calculation-Independent (formula choice doesn't matter)
    AR 70-90% = Partially Dependent (magnitude helps but isn't essential)
    AR < 70% = Magnitude-Dependent (requires absolute dollar values)

Related: Issue #186
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from gex_db_infrastructure.validation.regime_classifier import RegimeClassifier

logger = logging.getLogger(__name__)


def calculate_normalized_gex(gex_data: pd.DataFrame) -> pd.Series:
    """Calculate normalized GEX using ratio-based formulation.

    Normalized GEX = (call_weighted_gamma / call_oi) - (put_weighted_gamma / put_oi)
    Range: -1.0 to +1.0

    Where:
    - Calls contribute POSITIVE to normalized GEX (dealer long gamma = support)
    - Puts contribute NEGATIVE to normalized GEX (dealer short gamma = reactive)

    Args:
        gex_data: DataFrame with columns [type, gamma, open_interest, underlying_price]
                  (after calculate_dealer_gamma_exposure processing)

    Returns:
        Series of normalized GEX values (-1.0 to 1.0 scale)
    """
    if gex_data.empty:
        return pd.Series(dtype=float)

    # Separate calls and puts
    calls = gex_data[gex_data["type"] == "call"].copy()
    puts = gex_data[gex_data["type"] == "put"].copy()

    # Calculate gamma-weighted OI ratio for each type
    # This measures dealer positioning intensity: high ratio = concentrated positioning
    if not calls.empty:
        call_gamma_oi = (
            (calls["bs_gamma"] * calls["open_interest"]).sum()
            / (calls["open_interest"].sum() + 1e-10)  # Avoid division by zero
        )
    else:
        call_gamma_oi = 0.0

    if not puts.empty:
        put_gamma_oi = (
            (puts["bs_gamma"] * puts["open_interest"]).sum()
            / (puts["open_interest"].sum() + 1e-10)
        )
    else:
        put_gamma_oi = 0.0

    # Net normalized GEX: calls positive, puts negative
    # Range: typically -0.1 to +0.1 before scaling
    net_normalized = call_gamma_oi - put_gamma_oi

    # Scale to [-1.0, 1.0] range
    # Max observed gamma_oi is ~0.01, so multiply by ~100 to reach ±1.0 scale
    normalized_gex = np.clip(net_normalized * 100, -1.0, 1.0)

    # Create series matching original index if available
    if hasattr(gex_data, "index") and len(gex_data) > 0:
        # Broadcast scalar value to series
        return pd.Series(normalized_gex, index=gex_data.index)
    else:
        return pd.Series([normalized_gex])


@dataclass
class FormulaAgreementResult:
    """Results of formula agreement comparison."""

    window_date: str
    baseline_regime: str  # persistent_positive, persistent_negative, transitional, low_conviction
    normalized_regime: str
    baseline_confidence: float
    normalized_confidence: float
    agreement: bool  # True if both detected same regime type
    baseline_metrics: Optional[Dict] = None
    normalized_metrics: Optional[Dict] = None


class NormalizedRegimeClassifier:
    """Classify regimes using normalized GEX (0-1 scale).

    Adapted from RegimeClassifier, but uses ratio-based metrics instead of dollar magnitude.
    Removes magnitude threshold since normalized values are scale-independent.
    """

    PERSISTENCE_THRESHOLD = 0.70  # 70% of days same sign
    MAX_SIGN_FLIPS = 5  # Max flips for persistent regime
    # NOTE: No magnitude threshold for normalized GEX

    def __init__(self, persistence_threshold: Optional[float] = None, max_sign_flips: Optional[int] = None):
        """Initialize normalized regime classifier."""
        self.persistence_threshold = persistence_threshold or self.PERSISTENCE_THRESHOLD
        self.max_sign_flips = max_sign_flips or self.MAX_SIGN_FLIPS

    def classify_window(self, gex_sequence: List[float]) -> Tuple[str, float]:
        """Classify a 30-day normalized GEX window.

        Args:
            gex_sequence: List of 30 normalized GEX values (-1.0 to 1.0)

        Returns:
            (regime_type, confidence) where confidence is [0.0, 1.0]
        """
        if not gex_sequence or len(gex_sequence) == 0:
            return ("transitional", 0.0)

        # Convert to numpy array and filter out NaN
        gex_array = np.array(gex_sequence, dtype=float)
        gex_array = gex_array[~np.isnan(gex_array)]

        if len(gex_array) == 0:
            return ("transitional", 0.0)

        # Calculate metrics
        positive_days = np.sum(gex_array > 0)
        negative_days = np.sum(gex_array < 0)
        total_days = len(gex_array)

        # Sign flips (counting direction changes)
        sign_changes = np.sum(np.diff(np.sign(gex_array)) != 0)

        # Persistence percentage
        max_consecutive = max(positive_days, negative_days)
        persistence_pct = max_consecutive / total_days if total_days > 0 else 0

        # Average absolute normalized value (measures regime strength)
        avg_magnitude = np.mean(np.abs(gex_array))

        # Classify regime
        is_persistent = persistence_pct >= self.persistence_threshold and sign_changes <= self.max_sign_flips

        if is_persistent:
            if positive_days > negative_days:
                regime_type = "persistent_positive"
            else:
                regime_type = "persistent_negative"
        else:
            regime_type = "transitional"

        # Calculate confidence based on:
        # - Persistence strength (how dominant the direction is)
        # - Stability (few sign flips)
        # - Magnitude (how strong the positioning is)
        persistence_confidence = persistence_pct
        flip_penalty = 1.0 - (sign_changes / (self.max_sign_flips + 1))
        magnitude_confidence = min(avg_magnitude * 2.0, 1.0)  # Normalized magnitude boost

        confidence = (persistence_confidence * 0.5 + flip_penalty * 0.3 + magnitude_confidence * 0.2)
        confidence = np.clip(confidence, 0.0, 1.0)

        return (regime_type, confidence)


class FormulaAgreementTester:
    """Compare baseline (absolute GEX) vs normalized GEX regime detection."""

    def __init__(self):
        """Initialize formula agreement tester."""
        self.baseline_classifier = RegimeClassifier()
        self.normalized_classifier = NormalizedRegimeClassifier()

    def compare_windows(
        self, baseline_windows: Dict[str, List[float]], normalized_windows: Dict[str, List[float]]
    ) -> Tuple[List[FormulaAgreementResult], float]:
        """Compare regime classifications across windows.

        Args:
            baseline_windows: Dict mapping window_date -> list of absolute GEX values
            normalized_windows: Dict mapping window_date -> list of normalized GEX values

        Returns:
            (results_list, agreement_rate)
        """
        results = []
        agreements = 0

        for window_date in sorted(baseline_windows.keys()):
            if window_date not in normalized_windows:
                logger.warning(f"Window {window_date} missing from normalized set")
                continue

            baseline_gex = baseline_windows[window_date]
            normalized_gex = normalized_windows[window_date]

            # Convert list of floats to list of dicts for baseline classifier
            baseline_gex_dicts = [{"net_gex": v} for v in baseline_gex]

            # Classify with baseline method
            baseline_result = self.baseline_classifier.classify_window(baseline_gex_dicts)
            baseline_regime = baseline_result.get("regime_type", "unknown")
            # Calculate confidence from metrics
            baseline_metrics = baseline_result.get("metrics")
            baseline_confidence = baseline_metrics.persistence_pct / 100.0 if baseline_metrics else 0.0

            # Classify with normalized method
            norm_regime, norm_confidence = self.normalized_classifier.classify_window(normalized_gex)

            # Check agreement (only comparing regime categories, not full metrics)
            agreement = baseline_regime == norm_regime

            if agreement:
                agreements += 1

            result = FormulaAgreementResult(
                window_date=window_date,
                baseline_regime=baseline_regime,
                normalized_regime=norm_regime,
                baseline_confidence=baseline_confidence,
                normalized_confidence=norm_confidence,
                agreement=agreement,
            )
            results.append(result)

        agreement_rate = agreements / len(results) if results else 0.0
        return results, agreement_rate

    def generate_report(self, results: List[FormulaAgreementResult], agreement_rate: float) -> str:
        """Generate human-readable comparison report."""
        report = [
            "=" * 80,
            "FORMULA AGREEMENT TEST RESULTS",
            "=" * 80,
            f"\nTotal Windows Tested: {len(results)}",
            f"Agreement Rate (AR): {agreement_rate:.1%}",
            f"\nInterpretation:",
            f"  AR > 90% = Calculation-Independent",
            f"  AR 70-90% = Partially Dependent",
            f"  AR < 70% = Magnitude-Dependent",
            f"\n" + "-" * 80,
            "DETAILED RESULTS:",
            "-" * 80,
        ]

        # Breakdown by agreement
        agreement_count = sum(1 for r in results if r.agreement)
        disagreement_count = len(results) - agreement_count

        report.append(f"\nAgreements: {agreement_count}")
        report.append(f"Disagreements: {disagreement_count}\n")

        # Show disagreement patterns
        if disagreement_count > 0:
            report.append("Disagreement Cases:")
            for r in results:
                if not r.agreement:
                    report.append(
                        f"  {r.window_date}: "
                        f"Baseline={r.baseline_regime} (conf={r.baseline_confidence:.1%}), "
                        f"Normalized={r.normalized_regime} (conf={r.normalized_confidence:.1%})"
                    )

        report.append("\n" + "=" * 80)
        return "\n".join(report)
