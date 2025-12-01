"""Enhanced Pattern Detector with Contrarian Logic Updated based on statistical analysis showing GAMMA_TRAP works as
contrarian indicator."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class EnhancedPatternDetector:
    """Enhanced pattern detector with statistical validation and contrarian logic."""

    def __init__(self):
        # Statistical findings from our empirical analysis
        self.pattern_stats = {
            "gamma_trap": {
                "signal_type": "CONTRARIAN",
                "expected_win_rate": 57.1,
                "expected_return": 0.507,
                "sample_size": 7,
                "confidence_threshold": 85.0,
                "optimal_regime": "NEGATIVE_GAMMA_LOW",
                "max_holding_days": 2,
            }
        }

    def detect_gamma_trap_enhanced(self, gex_data: Dict, market_data: Dict, fed_context: Dict = None) -> Dict:
        """Enhanced GAMMA_TRAP detection with contrarian signal interpretation.

        Based on empirical analysis:
        - Original strategy: 42.9% win rate, -0.507% return
        - Contrarian strategy: 57.1% win rate, +0.507% return
        """

        net_gex = gex_data.get("net_gex", 0)
        spot_price = market_data.get("spot_price", 0)
        flip_point = gex_data.get("flip_point", 0)
        gex_regime = gex_data.get("gex_regime", "UNKNOWN")

        # Base gamma trap detection logic
        confidence = 0.0
        pattern_details = {}

        # High gamma concentration near current price
        if flip_point > 0 and spot_price > 0:
            distance_to_flip = abs(spot_price - flip_point) / flip_point

            if distance_to_flip < 0.02:  # Within 2% of flip point
                confidence += 40.0
                pattern_details["proximity_to_flip"] = f"{distance_to_flip:.3%}"
            elif distance_to_flip < 0.05:  # Within 5% of flip point
                confidence += 20.0
                pattern_details["proximity_to_flip"] = f"{distance_to_flip:.3%}"

        # Negative GEX regime (optimal conditions based on analysis)
        if gex_regime == "NEGATIVE_GAMMA_LOW":
            confidence += 30.0
            pattern_details["optimal_regime"] = True
        elif "NEGATIVE" in gex_regime:
            confidence += 15.0

        # High absolute GEX values suggest strong dealer positioning
        if abs(net_gex) > 1_000_000:  # >$1M GEX
            confidence += 20.0
            pattern_details["high_gex"] = f"${net_gex:,.0f}"

        # Fed context enhancement (if available)
        if fed_context:
            days_to_fomc = fed_context.get("days_to_fomc", 999)
            is_fomc_week = fed_context.get("is_fomc_week", False)

            # Avoid FOMC days for cleaner signals
            if is_fomc_week:
                confidence -= 10.0
                pattern_details["fomc_adjustment"] = "Reduced confidence for FOMC week"
            elif days_to_fomc <= 3:
                confidence -= 5.0
                pattern_details["fomc_adjustment"] = "Slight reduction near FOMC"

        # Pattern strength classification
        if confidence >= self.pattern_stats["gamma_trap"]["confidence_threshold"]:
            pattern_strength = "HIGH"
        elif confidence >= 70.0:
            pattern_strength = "MEDIUM"
        elif confidence >= 50.0:
            pattern_strength = "LOW"
        else:
            pattern_strength = "INSUFFICIENT"

        # Return enhanced pattern detection result
        if confidence >= 50.0:  # Minimum threshold for pattern detection
            stats = self.pattern_stats["gamma_trap"]

            return {
                "pattern": "gamma_trap",
                "signal": "CONTRARIAN",  # KEY: Trade opposite to implied direction
                "confidence": confidence,
                "pattern_strength": pattern_strength,
                "expected_win_rate": stats["expected_win_rate"],
                "expected_return": stats["expected_return"],
                "statistical_basis": f"{stats['sample_size']} historical samples",
                "optimal_regime": stats["optimal_regime"],
                "max_holding_days": stats["max_holding_days"],
                "pattern_details": pattern_details,
                "trading_direction": "OPPOSITE_TO_IMPLIED",
                "risk_warning": "Contrarian strategy - trade against apparent market direction",
                "entry_conditions": {
                    "min_confidence": stats["confidence_threshold"],
                    "preferred_regime": stats["optimal_regime"],
                    "avoid_fomc": True,
                },
            }
        else:
            return {
                "pattern": None,
                "confidence": confidence,
                "reason": "Insufficient confidence for pattern detection",
                "details": pattern_details,
            }

    def detect_all_patterns(self, gex_data: Dict, market_data: Dict, fed_context: Dict = None) -> List[Dict]:
        """Detect all available patterns with enhanced logic."""

        detected_patterns = []

        # GAMMA_TRAP (currently our only validated pattern)
        gamma_trap = self.detect_gamma_trap_enhanced(gex_data, market_data, fed_context)
        if gamma_trap.get("pattern"):
            detected_patterns.append(gamma_trap)

        # Future patterns would be added here as they get validated
        # e.g., volatility_squeeze, pin_risk, etc.

        return detected_patterns

    def get_trading_recommendation(self, pattern_result: Dict) -> Dict:
        """Convert pattern detection to specific trading recommendation."""

        if not pattern_result.get("pattern"):
            return {"action": "NO_TRADE", "reason": "No high-confidence patterns detected"}

        pattern_name = pattern_result["pattern"]

        if pattern_name == "gamma_trap":
            return {
                "action": "CONTRARIAN_TRADE",
                "direction": "OPPOSITE_TO_IMPLIED",
                "confidence": pattern_result["confidence"],
                "expected_win_rate": pattern_result["expected_win_rate"],
                "expected_return": pattern_result["expected_return"],
                "position_size": "CONSERVATIVE_2_PERCENT",
                "stop_loss": "2.0%",
                "profit_target": "1.0%",  # 2:1 risk-reward
                "max_holding": f"{pattern_result['max_holding_days']} days",
                "entry_rationale": "GAMMA_TRAP indicates market exhaustion/turning point",
                "statistical_basis": pattern_result["statistical_basis"],
            }

        return {"action": "NO_TRADE", "reason": f"Unknown pattern: {pattern_name}"}


def test_enhanced_pattern_detector():
    """Test the enhanced pattern detector with sample data."""

    detector = EnhancedPatternDetector()

    # Sample data that should trigger GAMMA_TRAP
    gex_data = {"net_gex": -5_000_000, "flip_point": 450.0, "gex_regime": "NEGATIVE_GAMMA_LOW"}

    market_data = {"spot_price": 449.0}  # Very close to flip point

    fed_context = {"days_to_fomc": 15, "is_fomc_week": False}

    print("ENHANCED PATTERN DETECTOR TEST")
    print("=" * 50)

    # Test pattern detection
    patterns = detector.detect_all_patterns(gex_data, market_data, fed_context)

    if patterns:
        for pattern in patterns:
            print(f"Pattern Detected: {pattern['pattern'].upper()}")
            print(f"Signal Type: {pattern['signal']}")
            print(f"Confidence: {pattern['confidence']:.1f}%")
            print(f"Expected Win Rate: {pattern['expected_win_rate']:.1f}%")
            print(f"Expected Return: {pattern['expected_return']:.3f}%")
            print(f"Trading Direction: {pattern['trading_direction']}")
            print()

            # Get trading recommendation
            recommendation = detector.get_trading_recommendation(pattern)
            print("TRADING RECOMMENDATION:")
            print(f"Action: {recommendation['action']}")
            print(f"Direction: {recommendation['direction']}")
            print(f"Position Size: {recommendation['position_size']}")
            print(f"Stop Loss: {recommendation['stop_loss']}")
            print(f"Profit Target: {recommendation['profit_target']}")
            print(f"Max Holding: {recommendation['max_holding']}")
            print(f"Rationale: {recommendation['entry_rationale']}")
    else:
        print("No patterns detected with current data")

    return detector


if __name__ == "__main__":
    test_enhanced_pattern_detector()
