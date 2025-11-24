"""
Regime Classification for 30-Day GEX Windows - Paper #2 Pivot

Purpose:
    Classifies 30-day GEX windows into persistent regime types,
    replacing the 5-day trajectory analysis which showed 98-100% detection.

Research Question:
    "Can LLMs identify persistent market regimes from dealer gamma positioning?"

Expected Detection Rate: 30-50% (selective, not universal)

Related:
    - docs/papers/paper2/methodology/regime_windows_design.md
    - Issues #89, #107, #149
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from src.utils.config_manager import get_config

logger = logging.getLogger(__name__)


@dataclass
class RegimeMetrics:
    """Metrics for a 30-day GEX regime window."""

    positive_days: int
    negative_days: int
    persistence_pct: float
    avg_magnitude: float
    min_magnitude: float
    max_magnitude: float
    std_magnitude: float
    coefficient_of_variation: float
    sign_flips: int
    regime_type: str


class RegimeClassifier:
    """Classifies 30-day GEX windows into persistent regime types.

    Regime Types:
        - persistent_positive: >70% positive days, >$5B avg, ≤5 flips
        - persistent_negative: >70% negative days, >$5B avg, ≤5 flips
        - low_conviction: Persistent sign but weak magnitude (<$5B)
        - transitional: Frequent flips, no dominant direction

    Usage:
        classifier = RegimeClassifier()
        result = classifier.classify_window(gex_sequence_30d)

        if result.is_persistent:
            print(f"Persistent {result.metrics.regime_type}")
        else:
            print(f"Rejected: {result.metrics.regime_type}")
    """

    # Classification thresholds (class-level defaults, overridden by config)
    # Kept for backward compatibility with code that references these directly
    PERSISTENCE_THRESHOLD = 0.70  # 70% of days (21/30) same sign
    MAGNITUDE_THRESHOLD = 5e9  # $5B average GEX
    MAX_SIGN_FLIPS = 5  # Max flips for persistent regime
    LOW_CONVICTION_MAG = 3e9  # $3B (below this is too weak even if persistent)

    def __init__(
        self,
        persistence_threshold: Optional[float] = None,
        magnitude_threshold: Optional[float] = None,
        max_sign_flips: Optional[int] = None,
    ):
        """Initialize regime classifier with custom thresholds.

        Thresholds are loaded from config_defaults/analysis_config.yaml by default.
        Explicit parameters override config values (for testing/experimentation).

        Args:
            persistence_threshold: Minimum fraction of days with same sign (default from config: 0.70)
            magnitude_threshold: Minimum average GEX magnitude for persistence (default from config: $5B)
            max_sign_flips: Maximum sign flips allowed for persistent regime (default from config: 5)
        """
        # Load config
        config = get_config()

        # Use explicit parameters if provided, otherwise use config, fallback to class constants
        self.persistence_threshold = persistence_threshold or config.get(
            "regime_classification.persistence_threshold", self.PERSISTENCE_THRESHOLD
        )
        self.magnitude_threshold = magnitude_threshold or config.get(
            "regime_classification.magnitude_threshold", self.MAGNITUDE_THRESHOLD
        )
        self.max_sign_flips = max_sign_flips or config.get("regime_classification.max_sign_flips", self.MAX_SIGN_FLIPS)

        # Load low conviction threshold from config (not exposed as parameter)
        self.low_conviction_mag = config.get("regime_classification.low_conviction_threshold", self.LOW_CONVICTION_MAG)

        logger.info(
            f"RegimeClassifier initialized: "
            f"persistence={self.persistence_threshold:.0%}, "
            f"magnitude=${self.magnitude_threshold/1e9:.0f}B, "
            f"max_flips={self.max_sign_flips} "
            f"(source: {'config' if persistence_threshold is None else 'explicit'})"
        )

    def classify_window(self, gex_sequence: List[Dict]) -> Dict[str, any]:
        """Classify 30-day GEX window into regime type.

        Args:
            gex_sequence: List of 30 daily GEX observations
                Each dict must have 'net_gex' key

        Returns:
            dict with:
                - regime_type: str (persistent_positive/negative, low_conviction, transitional)
                - is_persistent: bool (True for persistent_positive/negative only)
                - metrics: RegimeMetrics dataclass
                - should_detect: bool (whether LLM should detect this)

        Raises:
            ValueError: If sequence is not exactly 30 days
        """
        if len(gex_sequence) != 30:
            raise ValueError(f"Expected 30-day window, got {len(gex_sequence)} days")

        # Validate all days have net_gex
        for i, day in enumerate(gex_sequence):
            if "net_gex" not in day:
                raise ValueError(f"Day {i} missing 'net_gex' field: {day.keys()}")

        # Calculate metrics
        metrics = self._calculate_metrics(gex_sequence)

        # Classify regime
        regime_type = self._classify_regime_type(metrics)

        # Update metrics with final classification
        metrics.regime_type = regime_type

        # Determine if persistent
        is_persistent = regime_type in ["persistent_positive", "persistent_negative"]

        return {
            "regime_type": regime_type,
            "is_persistent": is_persistent,
            "should_detect": is_persistent,  # LLM should only detect persistent regimes
            "metrics": metrics,
            "window_size": len(gex_sequence),
        }

    def _calculate_metrics(self, gex_sequence: List[Dict]) -> RegimeMetrics:
        """Calculate regime metrics from 30-day sequence.

        Args:
            gex_sequence: List of 30 daily GEX observations

        Returns:
            RegimeMetrics dataclass with all calculated values
        """
        # Extract GEX values
        gex_values = [d["net_gex"] for d in gex_sequence]

        # Count positive/negative days
        positive_days = sum(1 for v in gex_values if v > 0)
        negative_days = 30 - positive_days

        # Persistence percentage (max of positive or negative)
        persistence_pct = max(positive_days, negative_days) / 30 * 100

        # Magnitude metrics
        magnitudes = [abs(v) for v in gex_values]
        avg_magnitude = np.mean(magnitudes)
        min_magnitude = np.min(magnitudes)
        max_magnitude = np.max(magnitudes)
        std_magnitude = np.std(gex_values)

        # Coefficient of variation (relative volatility)
        coefficient_of_variation = std_magnitude / avg_magnitude if avg_magnitude > 0 else 0

        # Count sign flips (regime transitions)
        sign_flips = sum(1 for i in range(1, 30) if np.sign(gex_values[i]) != np.sign(gex_values[i - 1]))

        return RegimeMetrics(
            positive_days=positive_days,
            negative_days=negative_days,
            persistence_pct=persistence_pct,
            avg_magnitude=avg_magnitude,
            min_magnitude=min_magnitude,
            max_magnitude=max_magnitude,
            std_magnitude=std_magnitude,
            coefficient_of_variation=coefficient_of_variation,
            sign_flips=sign_flips,
            regime_type="",  # Set by _classify_regime_type
        )

    def _classify_regime_type(self, metrics: RegimeMetrics) -> str:
        """Determine regime type from calculated metrics.

        Classification Logic:
            1. Check persistence (≥70% same sign)
            2. Check magnitude (≥$5B avg for persistent, ≥$3B for low conviction)
            3. Check stability (≤5 sign flips for persistent)
            4. Assign regime type

        Args:
            metrics: RegimeMetrics with calculated values

        Returns:
            str: One of:
                - "persistent_positive" (detect)
                - "persistent_negative" (detect)
                - "low_conviction" (reject - too weak)
                - "transitional" (reject - unstable)
        """
        pos_days = metrics.positive_days
        neg_days = metrics.negative_days
        avg_mag = metrics.avg_magnitude
        flips = metrics.sign_flips

        # Convert threshold to number of days
        min_days = int(30 * self.persistence_threshold)

        # Check for persistent positive regime
        if pos_days >= min_days and avg_mag >= self.magnitude_threshold and flips <= self.max_sign_flips:
            return "persistent_positive"

        # Check for persistent negative regime
        if neg_days >= min_days and avg_mag >= self.magnitude_threshold and flips <= self.max_sign_flips:
            return "persistent_negative"

        # Check for low conviction (persistent sign but weak magnitude)
        if pos_days >= min_days or neg_days >= min_days:
            if avg_mag >= self.low_conviction_mag:
                return "low_conviction"
            else:
                return "transitional"  # Too weak even for low conviction

        # Otherwise transitional (frequent flips, no persistent direction)
        return "transitional"

    def classify_window_dual(self, gex_sequence: List[Dict], gex_calc=None) -> Dict[str, any]:
        """Classify 30-day window with both structural and economic regimes (Issue #138).

        Combines:
        1. Structural persistence (from classify_window) - structural constraint
        2. Economic activity (from classify_economic_regime) - hedging intensity

        Purpose: Explain detection vs profitability divergence
        Example:
        - Q1 2024: persistent_negative + elevated_risk → HIGH profitability (+21bp)
        - Q4 2024: persistent_negative + high_fragility → LOW profitability (-1bp)

        Args:
            gex_sequence: List of 30 daily GEX observations
                Each dict must have:
                - 'net_gex' or 'gex_oi': Structural GEX (required)
                - 'gex_volume': Economic GEX (optional, for dual analysis)
            gex_calc: Optional GEXCalculator instance for dual GEX calculation

        Returns:
            dict with:
                - structural_regime: str (persistent_positive/negative, transitional, low_conviction)
                - economic_regime: dict (from classify_economic_regime, if dual data available)
                - profitability_expectation: str (based on economic regime)
                - is_persistent: bool (structural constraint present)
                - should_detect: bool (LLM should detect structural constraint)
                - metrics: RegimeMetrics (structural)
                - has_dual_metrics: bool (whether economic regime is available)
        """
        if len(gex_sequence) != 30:
            raise ValueError(f"Expected 30-day window, got {len(gex_sequence)} days")

        # Step 1: Classify structural persistence (existing logic)
        structural_classification = self.classify_window(gex_sequence)

        # Step 2: Check if dual GEX metrics are available
        has_dual_metrics = all("gex_volume" in day for day in gex_sequence)

        if has_dual_metrics:
            # Calculate average dual GEX metrics over 30 days
            avg_gex_oi = np.mean([day.get("gex_oi", day.get("net_gex", 0)) for day in gex_sequence])
            avg_gex_volume = np.mean([day.get("gex_volume", 0) for day in gex_sequence])

            # Classify economic regime
            economic_regime = self.classify_economic_regime(avg_gex_oi, avg_gex_volume)

            profitability_expectation = economic_regime["expected_profitability"]

            logger.info(
                f"Dual classification complete: "
                f"Structural={structural_classification['regime_type']}, "
                f"Economic={economic_regime['regime']}, "
                f"Expected Profit={profitability_expectation}"
            )
        else:
            # No dual metrics available
            economic_regime = None
            profitability_expectation = "unknown"

            logger.warning("Dual GEX metrics not available - economic regime not classified")

        return {
            "structural_regime": structural_classification["regime_type"],
            "economic_regime": economic_regime,
            "profitability_expectation": profitability_expectation,
            "is_persistent": structural_classification["is_persistent"],
            "should_detect": structural_classification["should_detect"],
            "metrics": structural_classification["metrics"],
            "has_dual_metrics": has_dual_metrics,
            "window_size": 30,
        }

    def classify_economic_regime(
        self, gex_oi: float, gex_volume: float, volume_threshold: float = 3e9
    ) -> Dict[str, any]:
        """Classify economic regime using dual GEX metrics (Issue #138).

        4-Regime Framework (from @TailThatWagsDog):
        1. HIGH_FRAGILITY: GEX_OI negative, GEX_Volume near zero
           - Dealers have exposure but aren't actively hedging
           - Low profitability despite detection
        2. ELEVATED_RISK: GEX_OI negative, GEX_Volume negative
           - Dealers have exposure AND actively hedging
           - High profitability
        3. STABLE_POSITIVE: Both positive
           - Dealers stabilizing market
           - Low volatility environment
        4. TRANSITIONAL: Mixed signals
           - Regime shift in progress
           - Uncertain profitability

        Args:
            gex_oi: Structural positioning (open interest weighted)
            gex_volume: Economic activity (volume weighted)
            volume_threshold: Minimum GEX_Volume for "active" hedging (default $3B)

        Returns:
            dict with:
                - regime: str (high_fragility, elevated_risk, stable_positive, transitional)
                - constraint_present: bool (structural constraint exists)
                - economic_activity: str (low, high, stabilizing, unstable)
                - expected_profitability: str (low, high, low_volatility, uncertain)
                - gex_oi: float (structural)
                - gex_volume: float (activity)
                - activity_ratio: float (hedging intensity)
        """
        # Calculate activity ratio
        activity_ratio = abs(gex_volume / gex_oi) if gex_oi != 0 else 0.0

        # Classify regime
        if gex_oi < 0 and abs(gex_volume) < volume_threshold:
            # HIGH_FRAGILITY: Constraint exists but no active hedging
            regime = "high_fragility"
            constraint_present = True
            economic_activity = "low"
            expected_profitability = "low"
            description = "Dealers have short gamma exposure but minimal hedging activity"

        elif gex_oi < 0 and gex_volume < 0:
            # ELEVATED_RISK: Constraint exists AND active hedging
            regime = "elevated_risk"
            constraint_present = True
            economic_activity = "high"
            expected_profitability = "high"
            description = "Dealers actively hedging short gamma exposure"

        elif gex_oi > 0 and gex_volume > 0:
            # STABLE_POSITIVE: Dealers stabilizing market
            regime = "stable_positive"
            constraint_present = False
            economic_activity = "stabilizing"
            expected_profitability = "low_volatility"
            description = "Dealers long gamma, suppressing volatility"

        else:
            # TRANSITIONAL: Mixed signals
            regime = "transitional"
            constraint_present = "mixed"
            economic_activity = "unstable"
            expected_profitability = "uncertain"
            description = "Mixed signals - regime shift in progress"

        logger.info(
            f"Economic regime: {regime.upper()} "
            f"(GEX_OI=${gex_oi/1e9:.2f}B, GEX_Volume=${gex_volume/1e9:.2f}B, "
            f"Activity={activity_ratio:.2f})"
        )

        return {
            "regime": regime,
            "constraint_present": constraint_present,
            "economic_activity": economic_activity,
            "expected_profitability": expected_profitability,
            "description": description,
            "gex_oi": gex_oi,
            "gex_volume": gex_volume,
            "activity_ratio": activity_ratio,
            "volume_threshold": volume_threshold,
        }

    def get_classification_summary(self, classification: Dict) -> str:
        """Generate human-readable summary of classification.

        Args:
            classification: Output from classify_window()

        Returns:
            str: Multi-line summary
        """
        metrics = classification["metrics"]
        regime = classification["regime_type"]

        summary = f"""
Regime Classification: {regime.upper()}
  Persistence: {metrics.persistence_pct:.1f}% ({metrics.positive_days} pos, {metrics.negative_days} neg)
  Avg Magnitude: ${metrics.avg_magnitude/1e9:.2f}B
  Sign Flips: {metrics.sign_flips}
  Stability: CV={metrics.coefficient_of_variation:.2f}
  Verdict: {'DETECT' if classification['is_persistent'] else 'REJECT'}
"""
        return summary.strip()


def example_usage():
    """Example usage of RegimeClassifier."""

    # Example 1: Persistent negative regime (2024 Q1-like)
    persistent_negative = [{"net_gex": -15e9 + np.random.normal(0, 2e9)} for _ in range(25)] + [
        {"net_gex": 5e9 + np.random.normal(0, 1e9)} for _ in range(5)
    ]

    # Example 2: Transitional (frequent flips)
    transitional = [{"net_gex": 10e9 * (1 if i % 2 == 0 else -1) + np.random.normal(0, 2e9)} for i in range(30)]

    # Example 3: Low conviction (persistent but weak)
    low_conviction = [{"net_gex": 2e9 + np.random.normal(0, 0.5e9)} for _ in range(25)] + [
        {"net_gex": -1e9} for _ in range(5)
    ]

    classifier = RegimeClassifier()

    print("Example 1: Persistent Negative (should DETECT)")
    result1 = classifier.classify_window(persistent_negative)
    print(classifier.get_classification_summary(result1))

    print("\nExample 2: Transitional (should REJECT)")
    result2 = classifier.classify_window(transitional)
    print(classifier.get_classification_summary(result2))

    print("\nExample 3: Low Conviction (should REJECT)")
    result3 = classifier.classify_window(low_conviction)
    print(classifier.get_classification_summary(result3))


if __name__ == "__main__":
    # Run example
    example_usage()
