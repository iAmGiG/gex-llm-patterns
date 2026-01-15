"""
GEX Pattern Signal Generator (Issue #8)

Generates trading signals based on Gamma Exposure (GEX) patterns.
Uses historical options data from SQLiteOptionsManager.

Patterns detected:
- GEX flip (positive to negative or vice versa)
- Gamma concentration at strikes
- Put wall / call wall levels
- Dealer positioning changes
"""

import logging
import os
from typing import Any, Dict, Optional

import pandas as pd

from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator

logger = logging.getLogger(__name__)


class GEXPatternSignal:
    """
    GEX-based signal generator for backtesting.

    Uses historical options data to calculate GEX and generate signals
    based on dealer positioning and gamma concentration patterns.

    Usage:
        ```python
        from src.backtesting import BacktestEngine
        from src.backtesting.signals import GEXPatternSignal

        gex_signal = GEXPatternSignal()
        engine = BacktestEngine()

        results = engine.run(
            signal_generator=gex_signal.generate_signal,
            symbol="SPY",
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        ```

    Attributes:
        db_manager: SQLiteOptionsManager for options data
        gex_calculator: GEXCalculator for GEX calculations
        gex_flip_threshold: GEX value threshold for flip detection
        confidence_threshold: Minimum confidence for signal generation
    """

    def __init__(
        self,
        db_path: str = ".cache/options_historical.db",
        gex_flip_threshold: float = 0.0,
        confidence_threshold: float = 0.5,
    ):
        """
        Initialize GEX pattern signal generator.

        Args:
            db_path: Path to options database
            gex_flip_threshold: Threshold for GEX flip detection (default: 0)
            confidence_threshold: Minimum confidence for signals (default: 0.5)
        """
        self.db_manager = SQLiteOptionsManager(db_path=db_path, enable_validation=False)
        self.gex_calculator = GEXCalculator()
        self.gex_flip_threshold = gex_flip_threshold
        self.confidence_threshold = confidence_threshold

        # State tracking
        self.prev_net_gex: Optional[float] = None
        self.prev_gex_data: Optional[Dict] = None

    def get_gex_for_date(self, symbol: str, date: str) -> Optional[Dict]:
        """
        Calculate GEX metrics for a given date.

        Args:
            symbol: Stock symbol
            date: Trading date (YYYY-MM-DD)

        Returns:
            Dictionary with GEX metrics or None if no data
        """
        try:
            # Get options chain from database
            options_df = self.db_manager.get_options_chain(symbol, date)

            if options_df is None or options_df.empty:
                return None

            # Get underlying price
            if "underlying_price" in options_df.columns:
                spot_price = options_df["underlying_price"].iloc[0]
            else:
                # Try to get from daily summary
                summary = self.db_manager.get_daily_summary(symbol, date, date)
                if summary is not None and not summary.empty:
                    spot_price = summary["spot_price"].iloc[0]
                else:
                    spot_price = None

            if spot_price is None:
                return None

            # Rename columns for GEX calculator compatibility
            if "option_type" in options_df.columns and "type" not in options_df.columns:
                options_df = options_df.rename(columns={"option_type": "type"})

            # Add date column for proper DTE calculation (critical for historical backtesting)
            if "trading_date" in options_df.columns and "date" not in options_df.columns:
                options_df = options_df.rename(columns={"trading_date": "date"})
            elif "date" not in options_df.columns:
                options_df["date"] = pd.to_datetime(date)

            # Calculate GEX using the correct method
            gex_result = self.gex_calculator.calculate_gex_profile(options_df, spot_price)

            if gex_result is None or gex_result.get("net_gex", 0) == 0:
                return None

            # Extract key levels for put/call walls
            key_levels = gex_result.get("key_levels", [])
            max_gamma_strike = key_levels[0]["strike"] if key_levels else None

            # Find put wall (highest negative GEX) and call wall (highest positive GEX)
            strike_gex = gex_result.get("strike_gex")
            put_wall = None
            call_wall = None
            if strike_gex is not None and not strike_gex.empty:
                negative_gex = strike_gex[strike_gex["total_gex"] < 0]
                positive_gex = strike_gex[strike_gex["total_gex"] > 0]
                if not negative_gex.empty:
                    put_wall = negative_gex.loc[negative_gex["total_gex"].idxmin(), "strike"]
                if not positive_gex.empty:
                    call_wall = positive_gex.loc[positive_gex["total_gex"].idxmax(), "strike"]

            return {
                "net_gex": gex_result.get("net_gex", 0),
                "call_gex": gex_result.get("gex_range", (0, 0))[1],  # Max positive
                "put_gex": gex_result.get("gex_range", (0, 0))[0],  # Min negative
                "gex_by_strike": strike_gex.to_dict("records") if strike_gex is not None else [],
                "spot_price": spot_price,
                "max_gamma_strike": max_gamma_strike,
                "put_wall": put_wall,
                "call_wall": call_wall,
            }

        except Exception as e:
            logger.debug(f"Error calculating GEX for {symbol} {date}: {e}")
            return None

    def detect_gex_flip(self, current_gex: float) -> Optional[str]:
        """
        Detect GEX flip (positive to negative or vice versa).

        Args:
            current_gex: Current net GEX value

        Returns:
            "bullish_flip", "bearish_flip", or None
        """
        if self.prev_net_gex is None:
            return None

        threshold = self.gex_flip_threshold

        # Bearish flip: positive GEX -> negative GEX
        # When GEX goes negative, dealers are short gamma and will amplify moves
        if self.prev_net_gex > threshold and current_gex < -threshold:
            return "bearish_flip"

        # Bullish flip: negative GEX -> positive GEX
        # When GEX goes positive, dealers dampen moves (mean reversion)
        if self.prev_net_gex < -threshold and current_gex > threshold:
            return "bullish_flip"

        return None

    def calculate_confidence(self, gex_data: Dict, flip_type: Optional[str]) -> float:
        """
        Calculate signal confidence based on GEX metrics.

        Args:
            gex_data: Dictionary with GEX metrics
            flip_type: Type of GEX flip if any

        Returns:
            Confidence score 0.0 to 1.0
        """
        confidence = 0.5  # Base confidence

        net_gex = gex_data.get("net_gex", 0)
        spot = gex_data.get("spot_price", 0)

        # Higher confidence for larger GEX magnitudes
        if spot > 0:
            gex_pct = abs(net_gex) / spot
            confidence += min(gex_pct * 100, 0.3)  # Up to +0.3

        # Higher confidence on GEX flips
        if flip_type:
            confidence += 0.2

        # Cap at 1.0
        return min(confidence, 1.0)

    def generate_signal(self, symbol: str, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Generate trading signal based on GEX patterns.

        Args:
            symbol: Stock symbol
            data: Price DataFrame with datetime index (used for current date)
            **kwargs: Additional arguments

        Returns:
            Decision dictionary with:
            - action: "BUY", "SELL", or "HOLD"
            - position_size: 0.0 to 1.0
            - confidence: 0.0 to 1.0
            - reasoning: str
        """
        if data.empty:
            return {
                "action": "HOLD",
                "position_size": 0.0,
                "confidence": 0.0,
                "reasoning": "No price data",
            }

        # Get current date
        current_date = data.index[-1].strftime("%Y-%m-%d")

        # Get GEX data for current date
        gex_data = self.get_gex_for_date(symbol, current_date)

        if gex_data is None:
            # No GEX data - hold
            return {
                "action": "HOLD",
                "position_size": 0.0,
                "confidence": 0.0,
                "reasoning": f"No GEX data for {current_date}",
            }

        net_gex = gex_data["net_gex"]

        # Detect GEX flip
        flip_type = self.detect_gex_flip(net_gex)

        # Calculate confidence
        confidence = self.calculate_confidence(gex_data, flip_type)

        # Update state
        self.prev_net_gex = net_gex
        self.prev_gex_data = gex_data

        # Generate signal based on GEX regime and patterns
        if flip_type == "bullish_flip":
            if confidence >= self.confidence_threshold:
                return {
                    "action": "BUY",
                    "position_size": confidence,
                    "confidence": confidence,
                    "reasoning": f"GEX bullish flip: {self.prev_net_gex:.2f} -> {net_gex:.2f}",
                }

        elif flip_type == "bearish_flip":
            if confidence >= self.confidence_threshold:
                return {
                    "action": "SELL",
                    "position_size": confidence,
                    "confidence": confidence,
                    "reasoning": f"GEX bearish flip: {self.prev_net_gex:.2f} -> {net_gex:.2f}",
                }

        # GEX regime trading (without flip)
        if net_gex > 0:
            # Positive GEX = dealers dampen moves = mean reversion regime
            # In this regime, we could fade extremes
            return {
                "action": "HOLD",
                "position_size": 0.0,
                "confidence": 0.5,
                "reasoning": f"Positive GEX regime ({net_gex:.2f}) - mean reversion expected",
            }
        else:
            # Negative GEX = dealers amplify moves = momentum regime
            # In this regime, trend following works better
            return {
                "action": "HOLD",
                "position_size": 0.0,
                "confidence": 0.5,
                "reasoning": f"Negative GEX regime ({net_gex:.2f}) - momentum expected",
            }

    def reset(self):
        """Reset state for new backtest."""
        self.prev_net_gex = None
        self.prev_gex_data = None
