"""
GEX Strategy V0: Raw GEX Baseline
Implements the current BaselineGEXStrategy as V0 in the continuous experiment framework.

Trades every negative GEX day without LLM filtering to establish performance baseline.
"""

import logging
from typing import Dict, Optional
from src.strategies.base_gex_strategy import BaseGEXStrategy, GEXSignal

logger = logging.getLogger(__name__)


class GEXStrategyV0(BaseGEXStrategy):
    """
    V0: Raw GEX Baseline Strategy

    - Fixed mechanical rules: Negative GEX → Short bias
    - No intelligence filtering - trades every negative GEX occurrence
    - Uses aggregate GEX thresholds from config
    - Purpose: Establish baseline to prove LLM value-add
    """

    def __init__(self, symbol: str = "SPY", config: Optional[Dict] = None):
        """Initialize V0 with GEX thresholds from config."""
        super().__init__(symbol, config)

        # Extract GEX thresholds from config
        gex_config = self.config.get('gex_thresholds', {})
        self.negative_high_threshold = gex_config.get('negative_high', -5000000000)  # -5e9
        self.positive_high_threshold = gex_config.get('positive_high', 5000000000)   # 5e9

        # Position sizing
        position_config = self.config.get('position_sizing', {})
        self.position_pct = position_config.get('conservative_position_pct', 1.5) / 100

        logger.info(f"Initialized GEXStrategyV0 for {symbol}")
        logger.info(f"  Negative GEX threshold: {self.negative_high_threshold:,.0f}")
        logger.info(f"  Position size: {self.position_pct:.1%}")

    def _get_version(self) -> str:
        """Return V0 version identifier."""
        return "V0"

    def analyze_day(self, date: str, market_data: Dict, gex_data: Dict) -> GEXSignal:
        """
        Analyze single day using raw GEX rules.

        Simple mechanical logic:
        - High negative GEX → Short signal
        - High positive GEX → Long signal
        - Otherwise → Neutral

        Args:
            date: Trading date
            market_data: Market data for the date
            gex_data: GEX data containing net_gex value

        Returns:
            GEXSignal with mechanical decision
        """
        # Extract net GEX from data
        net_gex = gex_data.get('net_gex', 0)

        # Mechanical decision logic
        if net_gex <= self.negative_high_threshold:
            # High negative GEX - dealers short gamma, market unstable
            signal_type = 'short'
            confidence = 0.75  # Fixed confidence for mechanical rule
            reasoning = f"High negative GEX ({net_gex:,.0f}) - dealers short gamma, expect volatility"

        elif net_gex >= self.positive_high_threshold:
            # High positive GEX - dealers long gamma, market stable
            signal_type = 'long'
            confidence = 0.75
            reasoning = f"High positive GEX ({net_gex:,.0f}) - dealers long gamma, expect stability"

        else:
            # Neutral GEX range
            signal_type = 'neutral'
            confidence = 0.0
            reasoning = f"Neutral GEX ({net_gex:,.0f}) - no clear directional bias"

        return GEXSignal(
            date=date,
            signal_type=signal_type,
            confidence=confidence,
            reasoning=reasoning,
            gamma_exposure=net_gex,
            metadata={
                'strategy_version': 'V0',
                'threshold_negative': self.negative_high_threshold,
                'threshold_positive': self.positive_high_threshold,
                'net_gex': net_gex
            }
        )