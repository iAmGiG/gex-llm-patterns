"""Actionable Trading Patterns Extension Enhances pattern_library.py patterns with specific trading signals and risk
management."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .pattern_library import MarketMechanicsPattern, PatternLibrary

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """Trading signal strength levels."""

    STRONG = "strong"  # >75% confidence
    MODERATE = "moderate"  # 60-75% confidence
    WEAK = "weak"  # 50-60% confidence
    NONE = None  # <50% confidence


@dataclass
class ActionableSignal:
    """Concrete trading signal with entry/exit/risk parameters.

    Extends the base pattern with actionable specifics.
    """

    # Pattern identification
    pattern: MarketMechanicsPattern
    signal_strength: SignalStrength

    # Entry parameters
    entry_price: float
    entry_trigger: str  # Specific condition to enter

    # Exit parameters
    stop_loss: float
    initial_target: float

    # Risk management
    position_size_pct: float  # % of portfolio
    risk_reward_ratio: float
    max_holding_period: str  # e.g., "2 days", "1 week"

    # Context
    current_spot: float
    gamma_metrics: Dict
    confidence_factors: List[str]

    # Optional parameters with defaults
    trailing_stop_pct: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML export."""
        return {
            "pattern_name": self.pattern.pattern_name,
            "signal_strength": self.signal_strength.value,
            "entry": {
                "price": self.entry_price,
                "trigger": self.entry_trigger,
                "distance_from_spot": f"{((self.entry_price/self.current_spot - 1) * 100):.2f}%",
            },
            "risk_management": {
                "stop_loss": self.stop_loss,
                "stop_distance": f"{((1 - self.stop_loss/self.entry_price) * 100):.2f}%",
                "initial_target": self.initial_target,
                "target_gain": f"{((self.initial_target/self.entry_price - 1) * 100):.2f}%",
                "risk_reward": self.risk_reward_ratio,
                "position_size": f"{self.position_size_pct}%",
                "max_hold": self.max_holding_period,
            },
            "confidence": {"strength": self.signal_strength.value, "factors": self.confidence_factors},
        }


class ActionablePatternDetector:
    """Converts pattern library patterns into actionable trading signals.

    Bridges the gap between pattern identification and trade execution.
    """

    def __init__(self, config: Dict = None):
        """Initialize with pattern library and configuration."""
        self.pattern_library = PatternLibrary()
        self.config = config or {}

        # Risk management defaults
        self.max_position_size = self.config.get("max_position_size", 2.0)  # 2% max
        self.min_risk_reward = self.config.get("min_risk_reward", 1.5)
        self.min_confidence = self.config.get("min_confidence", 60)

        logger.info("Initialized actionable pattern detector")

    def generate_signals(
        self, gex_metrics: Dict, market_mechanics: Dict, spot_price: float, options_data: Optional[Dict] = None
    ) -> List[ActionableSignal]:
        """Generate actionable trading signals from current market state.

        Args:
            gex_metrics: Current GEX calculations
            market_mechanics: LLM WHO/WHOM/WHAT analysis
            spot_price: Current underlying price
            options_data: Optional options chain data

        Returns:
            List of actionable trading signals
        """
        signals = []

        # Check each high-priority pattern
        priority_patterns = ["gamma_squeeze", "dealer_trap", "opex_pin", "delta_hedging_cascade"]

        for pattern_name in priority_patterns:
            signal = self._check_pattern(pattern_name, gex_metrics, market_mechanics, spot_price)
            if signal:
                signals.append(signal)

        logger.info(f"Generated {len(signals)} actionable signals")
        return signals

    def _check_pattern(
        self, pattern_name: str, gex_metrics: Dict, market_mechanics: Dict, spot_price: float
    ) -> Optional[ActionableSignal]:
        """Check if a specific pattern is actionable."""

        pattern = self.pattern_library.patterns.get(pattern_name)
        if not pattern:
            return None

        # Pattern-specific detection logic
        if pattern_name == "gamma_squeeze":
            return self._check_gamma_squeeze(pattern, gex_metrics, market_mechanics, spot_price)
        elif pattern_name == "dealer_trap":
            return self._check_dealer_trap(pattern, gex_metrics, market_mechanics, spot_price)
        elif pattern_name == "opex_pin":
            return self._check_opex_pin(pattern, gex_metrics, market_mechanics, spot_price)
        elif pattern_name == "delta_hedging_cascade":
            return self._check_delta_cascade(pattern, gex_metrics, market_mechanics, spot_price)

        return None

    def _check_gamma_squeeze(
        self, pattern: MarketMechanicsPattern, gex_metrics: Dict, market_mechanics: Dict, spot_price: float
    ) -> Optional[ActionableSignal]:
        """Check for actionable gamma squeeze setup.

        Criteria:
        - Negative total GEX (dealers short gamma)
        - High call concentration above spot
        - LLM confirms dealer hedging mechanics
        """
        total_gex = gex_metrics.get("total_gamma", 0)
        gamma_concentration = gex_metrics.get("gamma_concentration", 0)
        mechanics_confidence = market_mechanics.get("confidence", 0)

        # Check basic criteria
        if total_gex >= 0:  # Need negative GEX
            return None

        if gamma_concentration < 0.7:  # Need concentrated gamma
            return None

        if mechanics_confidence < self.min_confidence:
            return None

        # Check WHO/WHOM/WHAT aligns with gamma squeeze
        who = market_mechanics.get("who", "").lower()
        what = market_mechanics.get("what", "").lower()

        squeeze_indicators = [
            "call" in who or "buyer" in who,
            "dealer" in market_mechanics.get("whom", "").lower(),
            "hedge" in what or "buy" in what or "force" in what,
        ]

        if sum(squeeze_indicators) < 2:
            return None

        # Calculate signal parameters
        signal_strength = self._calculate_signal_strength(mechanics_confidence, gamma_concentration)

        # Entry 0.5% above current (breakout confirmation)
        entry_price = spot_price * 1.005

        # Stop 1.5% below entry (tight risk)
        stop_loss = entry_price * 0.985

        # Target based on gamma concentration (2-5% move)
        # 2% base + up to 3% more
        target_multiplier = 1.02 + (gamma_concentration * 0.03)
        initial_target = entry_price * target_multiplier

        # Risk/reward calculation
        risk = entry_price - stop_loss
        reward = initial_target - entry_price
        risk_reward = reward / risk if risk > 0 else 0

        if risk_reward < self.min_risk_reward:
            return None

        # Position sizing based on confidence
        position_size = min(
            self.max_position_size, 0.5 + (mechanics_confidence / 100) * 1.5  # 0.5-2% based on confidence
        )

        confidence_factors = [
            f"Negative GEX: ${total_gex/1e9:.1f}B",
            f"Gamma concentration: {gamma_concentration:.1%}",
            f"Mechanics confidence: {mechanics_confidence}%",
            f"Call buying detected in WHO/WHAT",
        ]

        return ActionableSignal(
            pattern=pattern,
            signal_strength=signal_strength,
            entry_price=entry_price,
            entry_trigger=f"Break above {entry_price:.2f} with volume",
            stop_loss=stop_loss,
            initial_target=initial_target,
            trailing_stop_pct=2.0,  # Trail by 2% after profit
            position_size_pct=position_size,
            risk_reward_ratio=risk_reward,
            max_holding_period="3 days",
            current_spot=spot_price,
            gamma_metrics=gex_metrics,
            confidence_factors=confidence_factors,
        )

    def _check_dealer_trap(
        self, pattern: MarketMechanicsPattern, gex_metrics: Dict, market_mechanics: Dict, spot_price: float
    ) -> Optional[ActionableSignal]:
        """Check for dealer trap pattern (dealers forced into bad position)."""

        gamma_flip = gex_metrics.get("gamma_flip_point", 0)
        total_gex = gex_metrics.get("total_gamma", 0)

        if not gamma_flip:
            return None

        # Check if we're near gamma flip (within 1%)
        distance_to_flip = abs(spot_price - gamma_flip) / spot_price
        if distance_to_flip > 0.01:
            return None

        mechanics_confidence = market_mechanics.get("confidence", 0)
        if mechanics_confidence < self.min_confidence:
            return None

        # Determine trap direction
        above_flip = spot_price > gamma_flip

        # Entry based on flip dynamics
        if above_flip:
            # Above flip - dealers short gamma, bullish continuation
            entry_price = spot_price * 1.002
            stop_loss = gamma_flip * 0.995
            initial_target = spot_price * 1.02
            entry_trigger = "Momentum continuation above flip"
        else:
            # Below flip - dealers long gamma, mean reversion
            entry_price = spot_price * 0.998
            stop_loss = gamma_flip * 1.005
            initial_target = gamma_flip * 0.99
            entry_trigger = "Rejection at flip resistance"

        risk = abs(entry_price - stop_loss)
        reward = abs(initial_target - entry_price)
        risk_reward = reward / risk if risk > 0 else 0

        if risk_reward < self.min_risk_reward:
            return None

        signal_strength = self._calculate_signal_strength(mechanics_confidence, 60)

        confidence_factors = [
            f"Gamma flip at: {gamma_flip:.2f}",
            f"Distance to flip: {distance_to_flip:.2%}",
            f"Total GEX: ${total_gex/1e9:.1f}B",
            f"Above/Below flip: {'Above' if above_flip else 'Below'}",
        ]

        return ActionableSignal(
            pattern=pattern,
            signal_strength=signal_strength,
            entry_price=entry_price,
            entry_trigger=entry_trigger,
            stop_loss=stop_loss,
            initial_target=initial_target,
            position_size_pct=1.0,  # Conservative size for flip trades
            risk_reward_ratio=risk_reward,
            max_holding_period="1 day",
            current_spot=spot_price,
            gamma_metrics=gex_metrics,
            confidence_factors=confidence_factors,
        )

    def _check_opex_pin(
        self, pattern: MarketMechanicsPattern, gex_metrics: Dict, market_mechanics: Dict, spot_price: float
    ) -> Optional[ActionableSignal]:
        """Check for options expiration pin risk pattern."""

        # Would need to check if today is expiration day
        # And identify max pain / high OI strikes
        # Placeholder for now
        return None

    def _check_delta_cascade(
        self, pattern: MarketMechanicsPattern, gex_metrics: Dict, market_mechanics: Dict, spot_price: float
    ) -> Optional[ActionableSignal]:
        """Check for delta hedging cascade pattern."""

        # Look for rapid gamma changes that force hedging
        # Would need intraday data to properly detect
        # Placeholder for now
        return None

    def _calculate_signal_strength(self, mechanics_confidence: float, pattern_confidence: float) -> SignalStrength:
        """Calculate overall signal strength."""

        avg_confidence = (mechanics_confidence + pattern_confidence) / 2

        if avg_confidence >= 75:
            return SignalStrength.STRONG
        elif avg_confidence >= 60:
            return SignalStrength.MODERATE
        elif avg_confidence >= 50:
            return SignalStrength.WEAK
        else:
            return SignalStrength.NONE

    def validate_signal(self, signal: ActionableSignal) -> bool:
        """Validate signal meets minimum requirements."""

        validations = [
            signal.signal_strength != SignalStrength.NONE,
            signal.risk_reward_ratio >= self.min_risk_reward,
            signal.position_size_pct <= self.max_position_size,
            signal.entry_price > 0,
            signal.stop_loss > 0,
            signal.initial_target > 0,
        ]

        return all(validations)
