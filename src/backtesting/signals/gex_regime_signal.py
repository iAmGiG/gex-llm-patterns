"""
GEX Regime Signal Generator

Matches AutoGen-Trader's regime-based trading approach:
- Regime: POSITIVE_GAMMA when net_call_gex > net_put_gex
- Signal on regime TRANSITIONS
- Maintain positions in current regime direction

This implementation can use:
1. Pre-calculated regimes from AutoGen-Trader's gex_research.db
2. Calculate compatible regimes from our options database
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class GEXRegimeSignal:
    """
    GEX regime-based signal generator matching AutoGen-Trader methodology.

    Key differences from flip-based approach:
    - Uses net_call_gex vs net_put_gex for regime classification
    - Signals on regime TRANSITIONS (not just sign flips)
    - Maintains position in current regime direction (0.5x size)

    Usage:
        ```python
        from src.backtesting import BacktestEngine
        from src.backtesting.signals import GEXRegimeSignal

        # Use AutoGen-Trader's pre-calculated regimes
        signal = GEXRegimeSignal(use_precalculated=True)

        # Or calculate from our options data
        signal = GEXRegimeSignal(use_precalculated=False)

        engine = BacktestEngine()
        results = engine.run(
            signal_generator=signal.generate_signal,
            symbol="TQQQ",
            start_date="2020-01-01",
            end_date="2024-12-31"
        )
        ```
    """

    # Path to AutoGen-Trader's pre-calculated regime database
    AUTOGEN_DB_PATH = Path(r"A:\Projects\AutoGen-Trader\.cache\gex_research.db")

    def __init__(
        self,
        use_precalculated: bool = True,
        options_db_path: str = ".cache/options_historical.db",
        transition_weight: float = 1.0,
        maintenance_weight: float = 0.5,
    ):
        """
        Initialize GEX regime signal generator.

        Args:
            use_precalculated: Use AutoGen-Trader's pre-calculated regimes
            options_db_path: Path to options database (for calculated mode)
            transition_weight: Position size on regime transitions (default: 1.0)
            maintenance_weight: Position size when maintaining regime (default: 0.5)
        """
        self.use_precalculated = use_precalculated
        self.options_db_path = options_db_path
        self.transition_weight = transition_weight
        self.maintenance_weight = maintenance_weight

        # State tracking
        self.prev_regime: Optional[str] = None
        self.current_position: float = 0.0
        self._regime_cache: Dict[str, pd.DataFrame] = {}

    def _load_precalculated_regimes(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load pre-calculated regimes from AutoGen-Trader database."""
        if symbol in self._regime_cache:
            return self._regime_cache[symbol]

        if not self.AUTOGEN_DB_PATH.exists():
            logger.warning(f"AutoGen-Trader database not found: {self.AUTOGEN_DB_PATH}")
            return None

        try:
            conn = sqlite3.connect(str(self.AUTOGEN_DB_PATH))
            df = pd.read_sql(
                """
                SELECT trading_date, regime, net_call_gex, net_put_gex, total_gex
                FROM options_daily_summary
                WHERE symbol = ?
                ORDER BY trading_date
                """,
                conn,
                params=(symbol,),
            )
            conn.close()

            if df.empty:
                logger.warning(f"No regime data for {symbol} in AutoGen-Trader DB")
                return None

            df["trading_date"] = pd.to_datetime(df["trading_date"])
            df.set_index("trading_date", inplace=True)
            self._regime_cache[symbol] = df
            logger.info(f"Loaded {len(df)} regime records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Error loading regimes for {symbol}: {e}")
            return None

    def _calculate_regime(self, net_call_gex: float, net_put_gex: float) -> str:
        """
        Calculate regime using AutoGen-Trader's methodology.

        Regime is POSITIVE_GAMMA when call GEX dominates put GEX.
        This indicates dealers are more hedged on the upside.
        """
        if net_call_gex > net_put_gex:
            return "POSITIVE_GAMMA"
        elif net_call_gex < net_put_gex:
            return "NEGATIVE_GAMMA"
        else:
            return "NEUTRAL"

    def get_regime_for_date(self, symbol: str, date: str) -> Optional[str]:
        """
        Get regime for a specific date.

        Args:
            symbol: Stock symbol
            date: Trading date (YYYY-MM-DD)

        Returns:
            Regime string or None if not available
        """
        if self.use_precalculated:
            regimes_df = self._load_precalculated_regimes(symbol)
            if regimes_df is None:
                return None

            try:
                date_ts = pd.to_datetime(date)
                if date_ts in regimes_df.index:
                    return regimes_df.loc[date_ts, "regime"]

                # Try to find closest date
                valid_dates = regimes_df.index[regimes_df.index <= date_ts]
                if len(valid_dates) > 0:
                    return regimes_df.loc[valid_dates[-1], "regime"]
            except Exception:
                pass
            return None
        else:
            # Calculate from options data (not implemented yet)
            logger.warning("Calculated regime mode not implemented - use precalculated")
            return None

    def generate_signal(self, symbol: str, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Generate trading signal based on GEX regime transitions.

        Signal logic (matching AutoGen-Trader):
        - On NEGATIVE -> POSITIVE transition: BUY (full position)
        - On POSITIVE -> NEGATIVE transition: SELL (exit or short)
        - While in POSITIVE regime: maintain long at 0.5x
        - While in NEGATIVE regime: maintain flat/short at 0.5x

        Args:
            symbol: Stock symbol
            data: Price DataFrame with datetime index
            **kwargs: Additional arguments

        Returns:
            Decision dictionary with action, position_size, confidence, reasoning
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

        # Get current regime
        current_regime = self.get_regime_for_date(symbol, current_date)

        if current_regime is None:
            return {
                "action": "HOLD",
                "position_size": 0.0,
                "confidence": 0.0,
                "reasoning": f"No regime data for {current_date}",
            }

        # Detect regime transition
        prev_regime = self.prev_regime
        self.prev_regime = current_regime

        # Signal on regime transitions
        if prev_regime is not None and current_regime != prev_regime:
            # Regime transition detected
            if current_regime == "POSITIVE_GAMMA":
                # Transition to positive gamma - go long
                self.current_position = self.transition_weight
                return {
                    "action": "BUY",
                    "position_size": self.transition_weight,
                    "confidence": 0.9,
                    "reasoning": f"Regime transition: {prev_regime} -> {current_regime}",
                }
            elif current_regime == "NEGATIVE_GAMMA":
                # Transition to negative gamma - exit/short
                self.current_position = -self.maintenance_weight
                return {
                    "action": "SELL",
                    "position_size": self.transition_weight,
                    "confidence": 0.9,
                    "reasoning": f"Regime transition: {prev_regime} -> {current_regime}",
                }

        # Maintain position in current regime
        if current_regime == "POSITIVE_GAMMA":
            # Stay long at maintenance weight
            if self.current_position <= 0:
                self.current_position = self.maintenance_weight
                return {
                    "action": "BUY",
                    "position_size": self.maintenance_weight,
                    "confidence": 0.7,
                    "reasoning": f"Maintain position in {current_regime}",
                }
            else:
                return {
                    "action": "HOLD",
                    "position_size": self.current_position,
                    "confidence": 0.6,
                    "reasoning": f"Holding in {current_regime}",
                }
        elif current_regime == "NEGATIVE_GAMMA":
            # Stay flat/short at maintenance weight
            if self.current_position > 0:
                self.current_position = 0.0
                return {
                    "action": "SELL",
                    "position_size": self.maintenance_weight,
                    "confidence": 0.7,
                    "reasoning": f"Exit position in {current_regime}",
                }
            else:
                return {
                    "action": "HOLD",
                    "position_size": 0.0,
                    "confidence": 0.6,
                    "reasoning": f"Flat in {current_regime}",
                }
        else:
            # NEUTRAL regime - hold current position
            return {
                "action": "HOLD",
                "position_size": self.current_position,
                "confidence": 0.5,
                "reasoning": f"Neutral regime on {current_date}",
            }

    def reset(self):
        """Reset state for new backtest."""
        self.prev_regime = None
        self.current_position = 0.0
