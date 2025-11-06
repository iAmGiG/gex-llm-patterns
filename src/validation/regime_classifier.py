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
    - Issues #89, #107
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

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
    """
    Classifies 30-day GEX windows into persistent regime types.

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

    # Classification thresholds
    PERSISTENCE_THRESHOLD = 0.70  # 70% of days (21/30) same sign
    MAGNITUDE_THRESHOLD = 5e9     # $5B average GEX
    MAX_SIGN_FLIPS = 5            # Max flips for persistent regime
    # $3B (below this is too weak even if persistent)
    LOW_CONVICTION_MAG = 3e9

    def __init__(
        self,
        persistence_threshold: float = 0.70,
        magnitude_threshold: float = 5e9,
        max_sign_flips: int = 5
    ):
        """
        Initialize regime classifier with custom thresholds.

        Args:
            persistence_threshold: Minimum fraction of days with same sign (default 0.70)
            magnitude_threshold: Minimum average GEX magnitude for persistence (default $5B)
            max_sign_flips: Maximum sign flips allowed for persistent regime (default 5)
        """
        self.persistence_threshold = persistence_threshold
        self.magnitude_threshold = magnitude_threshold
        self.max_sign_flips = max_sign_flips

        logger.info(
            f"RegimeClassifier initialized: "
            f"persistence={persistence_threshold:.0%}, "
            f"magnitude=${magnitude_threshold/1e9:.0f}B, "
            f"max_flips={max_sign_flips}"
        )

    def classify_window(
        self,
        gex_sequence: List[Dict]
    ) -> Dict[str, any]:
        """
        Classify 30-day GEX window into regime type.

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
            raise ValueError(
                f"Expected 30-day window, got {len(gex_sequence)} days"
            )

        # Validate all days have net_gex
        for i, day in enumerate(gex_sequence):
            if 'net_gex' not in day:
                raise ValueError(
                    f"Day {i} missing 'net_gex' field: {day.keys()}"
                )

        # Calculate metrics
        metrics = self._calculate_metrics(gex_sequence)

        # Classify regime
        regime_type = self._classify_regime_type(metrics)

        # Update metrics with final classification
        metrics.regime_type = regime_type

        # Determine if persistent
        is_persistent = regime_type in [
            'persistent_positive',
            'persistent_negative'
        ]

        return {
            'regime_type': regime_type,
            'is_persistent': is_persistent,
            'should_detect': is_persistent,  # LLM should only detect persistent regimes
            'metrics': metrics,
            'window_size': len(gex_sequence)
        }

    def _calculate_metrics(
        self,
        gex_sequence: List[Dict]
    ) -> RegimeMetrics:
        """
        Calculate regime metrics from 30-day sequence.

        Args:
            gex_sequence: List of 30 daily GEX observations

        Returns:
            RegimeMetrics dataclass with all calculated values
        """
        # Extract GEX values
        gex_values = [d['net_gex'] for d in gex_sequence]

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
        coefficient_of_variation = (
            std_magnitude / avg_magnitude
            if avg_magnitude > 0
            else 0
        )

        # Count sign flips (regime transitions)
        sign_flips = sum(
            1 for i in range(1, 30)
            if np.sign(gex_values[i]) != np.sign(gex_values[i-1])
        )

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
            regime_type=""  # Set by _classify_regime_type
        )

    def _classify_regime_type(
        self,
        metrics: RegimeMetrics
    ) -> str:
        """
        Determine regime type from calculated metrics.

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
        if (pos_days >= min_days and
            avg_mag >= self.magnitude_threshold and
                flips <= self.max_sign_flips):
            return "persistent_positive"

        # Check for persistent negative regime
        if (neg_days >= min_days and
            avg_mag >= self.magnitude_threshold and
                flips <= self.max_sign_flips):
            return "persistent_negative"

        # Check for low conviction (persistent sign but weak magnitude)
        if (pos_days >= min_days or neg_days >= min_days):
            if avg_mag >= self.LOW_CONVICTION_MAG:
                return "low_conviction"
            else:
                return "transitional"  # Too weak even for low conviction

        # Otherwise transitional (frequent flips, no persistent direction)
        return "transitional"

    def get_classification_summary(
        self,
        classification: Dict
    ) -> str:
        """
        Generate human-readable summary of classification.

        Args:
            classification: Output from classify_window()

        Returns:
            str: Multi-line summary
        """
        metrics = classification['metrics']
        regime = classification['regime_type']

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
    persistent_negative = [
        {'net_gex': -15e9 + np.random.normal(0, 2e9)}
        for _ in range(25)
    ] + [
        {'net_gex': 5e9 + np.random.normal(0, 1e9)}
        for _ in range(5)
    ]

    # Example 2: Transitional (frequent flips)
    transitional = [
        {'net_gex': 10e9 * (1 if i % 2 == 0 else -1) +
         np.random.normal(0, 2e9)}
        for i in range(30)
    ]

    # Example 3: Low conviction (persistent but weak)
    low_conviction = [
        {'net_gex': 2e9 + np.random.normal(0, 0.5e9)}
        for _ in range(25)
    ] + [
        {'net_gex': -1e9}
        for _ in range(5)
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
