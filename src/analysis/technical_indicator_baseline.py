"""
Technical Indicator Baseline Strategy - Issue #58
Implements traditional technical indicators (MACD, RSI, Bollinger Bands) as baseline.

This provides a benchmark for comparing against O3-mini LLM strategy.
"""

import logging
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

from src.utils.date_utils import today_str
from src.utils.indicator_library import macd, rsi

logger = logging.getLogger(__name__)


class TechnicalIndicatorBaseline:
    """Traditional technical indicator strategy using MACD, RSI, and Bollinger Bands.

    Purpose: Establish baseline performance without GEX or LLM intelligence.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize technical indicator strategy with configuration.

        Args:
            config_path: Path to trading config YAML file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Extract trading parameters from config
        trading_config = self.config.get("validated_trading_engine", {})

        # Position sizing from config
        position_config = trading_config.get("position_sizing", {})
        self.position_size = position_config.get("conservative_position_pct", 1.5) / 100

        # Risk management from config
        risk_config = trading_config.get("risk_management", {})
        self.stop_loss_pct = risk_config.get("stop_loss_pct", 1.0) / 100
        self.profit_target_pct = risk_config.get("profit_target_pct", 1.5) / 100
        self.max_holding_days = risk_config.get("max_holding_days", 2)

        # Load technical indicator config
        tech_config = self._load_tech_config()

        # MACD parameters (validated 13/34/8)
        macd_params = tech_config.get("strategy_parameters", {}).get("macd", {})
        self.macd_fast = macd_params.get("fast", 13)
        self.macd_slow = macd_params.get("slow", 34)
        self.macd_signal = macd_params.get("signal", 8)

        # RSI parameters
        rsi_params = tech_config.get("strategy_parameters", {}).get("rsi", {})
        self.rsi_period = rsi_params.get("period", 14)
        self.rsi_oversold = rsi_params.get("oversold", 30)
        self.rsi_overbought = rsi_params.get("overbought", 70)

        # Exit parameters (use balanced as default)
        exit_params = tech_config.get("strategy_parameters", {}).get("exits", {}).get("balanced", {})
        self.profit_target_pct = exit_params.get("take_profit", 0.08)  # 8% TP
        self.stop_loss_pct = exit_params.get("stop_loss", 0.05)  # 5% SL

        # Voting system - RH2MAS 3-tier logic
        voting_params = tech_config.get("strategy_parameters", {}).get("voting_system", {})
        self.voting_mode = voting_params.get("mode", "three_tier")

        # 3-tier voting parameters
        self.macd_threshold = voting_params.get("macd_threshold", 0.1)
        self.min_data_points = voting_params.get("min_data_points", 42)

        # Tier configurations
        self.strong_consensus = voting_params.get("strong_consensus", {})
        self.weak_signal = voting_params.get("weak_signal", {})
        self.hold_conflict = voting_params.get("hold_conflict", {})

        # Strategy state
        self.signals_generated = []

        logger.info("Initialized TechnicalIndicatorBaseline with validated parameters:")
        logger.info(f"  RSI: period={self.rsi_period}, oversold={self.rsi_oversold}, overbought={self.rsi_overbought}")
        logger.info(
            f"  MACD: fast={self.macd_fast}, slow={self.macd_slow}, signal={self.macd_signal} (validated 13/34/8)"
        )
        logger.info(f"  Exits: TP={self.profit_target_pct:.1%}, SL={self.stop_loss_pct:.1%}")
        logger.info(f"  Voting: {self.voting_mode} (3-tier RH2MAS system)")

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from YAML file."""
        if config_path is None:
            # Default to config_defaults/trading_config.yaml
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config_defaults" / "trading_config.yaml"

        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")
            logger.warning("Using default parameters")
            return {}

    def _load_tech_config(self) -> Dict:
        """Load technical indicator configuration."""
        base_dir = Path(__file__).parent.parent.parent
        config_path = base_dir / "config_defaults" / "technical_indicators_config.yaml"

        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load tech config from {config_path}: {e}")
            logger.warning("Using default technical parameters")
            return {}

    def calculate_indicators(self, price_data: pd.DataFrame) -> Dict:
        """Calculate all technical indicators using the indicator library.

        Args:
            price_data: DataFrame with OHLC data

        Returns:
            Dictionary with calculated indicators
        """
        close_prices = price_data["close"]
        # Note: high/low prices available if needed for additional indicators
        # high_prices = price_data['high']
        # low_prices = price_data['low']

        # Use the indicator library functions (MACD + RSI only for validated system)
        # RSI
        rsi_values = rsi(close_prices, period=self.rsi_period)

        # MACD
        macd_result = macd(close_prices, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)

        return {
            "rsi": rsi_values,
            "macd_line": macd_result["MACD_line"],
            "signal_line": macd_result["MACD_signal"],
            "macd_histogram": macd_result["MACD_hist"],
        }

    def generate_signals(self, price_data: pd.DataFrame) -> List[Dict]:
        """Generate signals based on technical indicators.

        Uses majority voting from:
        - RSI oversold/overbought
        - Bollinger Band squeeze/breakout
        - MACD crossover

        Args:
            price_data: DataFrame with columns ['date', 'open', 'high', 'low', 'close']

        Returns:
            List of trading signals
        """
        # Handle date as index (Alpha Vantage format) or column
        if "date" not in price_data.columns and hasattr(price_data.index, "to_pydatetime"):
            # Date is in index - reset index to create date column
            price_data = price_data.reset_index()
            price_data = price_data.rename(columns={price_data.columns[0]: "date"})

        if price_data.empty or len(price_data) < max(self.macd_slow, self.rsi_period):
            logger.warning(
                f"Insufficient data for technical indicators: {len(price_data)} days, need {max(self.macd_slow, self.rsi_period)}"
            )
            return []

        # Sort by date and reset index
        price_data = price_data.sort_values("date").reset_index(drop=True)

        # Calculate all indicators using the library
        indicators = self.calculate_indicators(price_data)

        # Extract individual indicators (MACD + RSI only for validated system)
        rsi_values = indicators["rsi"]
        macd_histogram = indicators["macd_histogram"]

        close_prices = price_data["close"]

        signals = []

        # Generate signals for each day (skip warm-up period)
        start_idx = max(self.macd_slow, self.rsi_period)

        for i in range(start_idx, len(price_data)):
            date = price_data.iloc[i]["date"]
            price = close_prices.iloc[i]

            # Individual indicator signals (-1 short, 0 neutral, 1 long)
            indicator_signals = []
            signal_reasons = []

            # RSI Signal
            if rsi_values.iloc[i] < self.rsi_oversold:
                indicator_signals.append(1)  # Oversold -> Buy
                signal_reasons.append("RSI_oversold")
            elif rsi_values.iloc[i] > self.rsi_overbought:
                indicator_signals.append(-1)  # Overbought -> Sell
                signal_reasons.append("RSI_overbought")
            else:
                indicator_signals.append(0)

            # MACD Signal using histogram threshold (RH2MAS system)
            macd_signal = 0
            if i > 0:
                current_hist = macd_histogram.iloc[i]
                # Use histogram threshold from config
                if abs(current_hist) > self.macd_threshold:
                    if current_hist > 0:
                        macd_signal = 1
                        signal_reasons.append("MACD_positive_histogram")
                    else:
                        macd_signal = -1
                        signal_reasons.append("MACD_negative_histogram")

            indicator_signals.append(macd_signal)

            # RH2MAS 3-tier voting system
            rsi_signal = indicator_signals[0]  # First signal is RSI
            macd_signal = indicator_signals[1]  # Second signal is MACD

            # Determine consensus type
            if rsi_signal != 0 and macd_signal != 0 and rsi_signal == macd_signal:
                # Strong Consensus: Both indicators agree
                consensus_type = "strong_consensus"
                direction = "long" if rsi_signal > 0 else "short"
                position_size = self.strong_consensus["position_size"]
                confidence_boost = self.strong_consensus["confidence_boost"]
                min_confidence = self.strong_consensus["min_confidence"]
                base_confidence = 0.65

            elif (rsi_signal != 0 and macd_signal == 0) or (rsi_signal == 0 and macd_signal != 0):
                # Weak Signal: One indicator signals, other neutral
                consensus_type = "weak_signal"
                direction = "long" if (rsi_signal + macd_signal) > 0 else "short"
                position_size = self.weak_signal["position_size"]
                confidence_boost = self.weak_signal["confidence_boost"]
                min_confidence = self.weak_signal["min_confidence"]
                base_confidence = 0.45

            else:
                # Hold/Conflict: No signals or conflicting signals
                consensus_type = "hold_conflict"
                continue  # Skip to next date

            # Calculate final confidence
            final_confidence = base_confidence + confidence_boost

            # Check minimum confidence requirement
            if final_confidence < min_confidence:
                continue  # Skip signal if confidence too low

            signal = {
                "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
                "direction": direction,
                "confidence": final_confidence * 100,  # Convert to percentage
                "reason": ", ".join(signal_reasons),
                "entry_trigger": f"RH2MAS {consensus_type}: {signal_reasons}",
                "position_size": position_size,  # Dynamic position sizing from RH2MAS
                "stop_loss_pct": self.stop_loss_pct,
                "target_pct": self.profit_target_pct,
                "max_holding_days": self.max_holding_days,
                "consensus_type": consensus_type,
                "rsi_signal": rsi_signal,
                "macd_signal": macd_signal,
                "indicators": {"rsi": rsi_values.iloc[i], "price": price, "macd_histogram": macd_histogram.iloc[i]},
            }

            signals.append(signal)

        self.signals_generated = signals
        logger.info(f"Generated {len(signals)} technical indicator signals from {len(price_data)} days")

        return signals

    def backtest(self, price_data: pd.DataFrame, symbol: str = "SPY", test_period: Optional[str] = None) -> Dict:
        """Backtest the technical indicator strategy.

        Args:
            price_data: Price data with columns ['date', 'open', 'high', 'low', 'close']

        Returns:
            Backtest results with performance metrics
        """
        signals = self.generate_signals(price_data)

        if not signals:
            return self._empty_results("No signals generated")

        trades = []
        daily_pnl = []

        # Handle date as index (Alpha Vantage format) or column
        if "date" not in price_data.columns and hasattr(price_data.index, "to_pydatetime"):
            # Date is in index - reset index to create date column
            price_data = price_data.reset_index()
            price_data = price_data.rename(columns={price_data.columns[0]: "date"})

        # Convert price_data date column to datetime if needed
        price_data["date"] = pd.to_datetime(price_data["date"])

        for signal in signals:
            trade_result = self._execute_trade(signal, price_data)
            if trade_result:
                trades.append(trade_result)
                daily_pnl.append(trade_result["pnl_pct"] * self.position_size)

        # Calculate performance metrics
        if trades:
            results = self._calculate_metrics(trades, daily_pnl)
            results.update(self._add_tech_metadata(symbol, test_period, price_data))
            return results
        else:
            empty_results = self._empty_results("No valid trades executed")
            empty_results.update(self._add_tech_metadata(symbol, test_period, price_data))
            return empty_results

    def _execute_trade(self, signal: Dict, price_data: pd.DataFrame) -> Optional[Dict]:
        """Execute a single trade based on signal."""
        date = pd.to_datetime(signal["date"])
        entry_row = price_data[price_data["date"] == date]

        if entry_row.empty:
            return None

        entry_price = entry_row["close"].iloc[0]

        # Set stops and targets based on direction
        if signal["direction"] == "long":
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            target = entry_price * (1 + self.profit_target_pct)
        else:  # short
            stop_loss = entry_price * (1 + self.stop_loss_pct)
            target = entry_price * (1 - self.profit_target_pct)

        # Track trade over holding period
        for days_held in range(1, self.max_holding_days + 1):
            check_date = date + timedelta(days=days_held)
            check_row = price_data[price_data["date"] == check_date]

            if check_row.empty:
                continue

            if signal["direction"] == "long":
                # Check stop loss
                if check_row["low"].iloc[0] <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "stop_loss"
                    exit_date = check_date
                    break

                # Check target
                if check_row["high"].iloc[0] >= target:
                    exit_price = target
                    exit_reason = "target"
                    exit_date = check_date
                    break
            else:  # short
                # Check stop loss
                if check_row["high"].iloc[0] >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "stop_loss"
                    exit_date = check_date
                    break

                # Check target
                if check_row["low"].iloc[0] <= target:
                    exit_price = target
                    exit_reason = "target"
                    exit_date = check_date
                    break

            # Time exit on last day
            if days_held == self.max_holding_days:
                exit_price = check_row["close"].iloc[0]
                exit_reason = "time_exit"
                exit_date = check_date
                break
        else:
            return None  # No valid exit found

        # Calculate return based on direction
        if signal["direction"] == "long":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:  # short
            pnl_pct = (entry_price - exit_price) / entry_price

        return {
            "entry_date": signal["date"],
            "exit_date": exit_date.strftime("%Y-%m-%d"),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl_pct": pnl_pct,
            "win": pnl_pct > 0,
            "days_held": days_held,
            "direction": signal["direction"],
            "indicators": signal.get("indicators", {}),
        }

    def _calculate_metrics(self, trades: List[Dict], daily_pnl: List[float]) -> Dict:
        """Calculate comprehensive performance metrics."""
        if not trades:
            return self._empty_results("No trades to calculate metrics")

        trade_df = pd.DataFrame(trades)
        wins = trade_df["win"].sum()
        total = len(trade_df)
        win_rate = wins / total

        # Expected value per trade
        avg_win = trade_df[trade_df["win"]]["pnl_pct"].mean() if wins > 0 else 0
        avg_loss = trade_df[~trade_df["win"]]["pnl_pct"].mean() if (total - wins) > 0 else 0
        expected_value = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        # Sharpe ratio (annualized)
        returns = pd.Series(daily_pnl)
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = 0

        # Max drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        # Exit reason breakdown
        exit_reasons = trade_df["exit_reason"].value_counts().to_dict()

        # Direction breakdown
        direction_counts = trade_df["direction"].value_counts().to_dict()

        return {
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": win_rate,
            "expected_value": expected_value,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_days_held": trade_df["days_held"].mean(),
            "exit_reasons": exit_reasons,
            "direction_breakdown": direction_counts,
            "trades": trades,
            "strategy_type": "technical_indicators",
            "indicators_used": ["RSI", "MACD", "Bollinger Bands"],
            "position_size": self.position_size,
            "risk_reward_ratio": self.profit_target_pct / self.stop_loss_pct,
        }

    def _empty_results(self, message: str) -> Dict:
        """Return empty results structure."""
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "expected_value": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "message": message,
            "strategy_type": "technical_indicators",
        }

    def _add_tech_metadata(self, symbol: str, test_period: Optional[str], price_data: pd.DataFrame) -> Dict:
        """Add metadata to technical baseline results."""
        # Determine test period from data if not provided
        if test_period is None:
            if "date" in price_data.columns:
                start_date = price_data["date"].min()
                end_date = price_data["date"].max()
            else:
                # Date is in index
                start_date = price_data.index.min()
                end_date = price_data.index.max()
            if hasattr(start_date, "strftime"):
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                test_period = f"{start_str} to {end_str}"
            else:
                test_period = "Unknown period"

        return {
            "metadata": {
                "symbol": symbol,
                "test_period": test_period,
                "total_days": len(price_data),
                "run_date": today_str(),
                "strategy_version": "technical_indicators_v1.0",
                "indicators": {
                    "MACD": f"{self.macd_fast}/{self.macd_slow}/{self.macd_signal}",
                    "RSI": f"period={self.rsi_period}, levels={self.rsi_oversold}/{self.rsi_overbought}",
                    "voting_system": f"3-tier consensus (mode={self.voting_mode})",
                },
                "position_sizing": f"{self.position_size:.1%}",
                "risk_management": {
                    "stop_loss": f"{self.stop_loss_pct:.1%}",
                    "profit_target": f"{self.profit_target_pct:.1%}",
                    "max_holding_days": self.max_holding_days,
                },
                "validation_source": "Proven 13/34/8 MACD + RSI from production system",
            }
        }


class GEXAwareTechnicalBaseline(TechnicalIndicatorBaseline):
    """Technical indicator strategy that also considers GEX levels (but no LLM).

    Combines technical indicators with simple GEX regime rules.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize GEX-aware technical strategy."""
        super().__init__(config_path)

        # GEX thresholds from config
        analysis_config = self.config.get("gex_thresholds", {})
        self.gex_positive_high = analysis_config.get("positive_high", 5e9)
        self.gex_negative_high = analysis_config.get("negative_high", -5e9)

        logger.info("Initialized GEXAwareTechnicalBaseline")
        logger.info(
            f"  GEX thresholds: positive>{self.gex_positive_high/1e9:.1f}B, negative<{self.gex_negative_high/1e9:.1f}B"
        )

    def generate_signals_with_gex(self, price_data: pd.DataFrame, gex_data: Dict) -> List[Dict]:
        """Generate signals combining technical indicators with GEX regime.

        Args:
            price_data: Price data DataFrame
            gex_data: Dictionary with date -> GEX value mappings

        Returns:
            List of trading signals
        """
        # Get technical indicator signals
        tech_signals = self.generate_signals(price_data)

        # Filter/adjust based on GEX regime
        filtered_signals = []

        for signal in tech_signals:
            date_str = signal["date"]

            # Get GEX value for this date
            gex_value = gex_data.get(date_str, 0)

            # Simple GEX rules (no LLM interpretation)
            gex_regime = self._classify_gex_regime(gex_value)

            # Adjust signal based on GEX
            if gex_regime == "NEGATIVE_GAMMA_HIGH":
                # High negative gamma - expect volatility
                if signal["direction"] == "long":
                    # Contrarian approach in negative gamma
                    signal["confidence"] *= 1.2  # Boost confidence
                    signal["reason"] += f", GEX={gex_value/1e9:.1f}B (negative gamma)"
                else:
                    # Reduce confidence for shorts in negative gamma
                    signal["confidence"] *= 0.8
            elif gex_regime == "POSITIVE_GAMMA_HIGH":
                # High positive gamma - expect pinning
                # Reduce confidence in pinned markets
                signal["confidence"] *= 0.7
                signal["reason"] += f", GEX={gex_value/1e9:.1f}B (pinned)"

            # Add GEX info to signal
            signal["gex_value"] = gex_value
            signal["gex_regime"] = gex_regime

            # Only keep high confidence signals
            if signal["confidence"] >= 60:
                filtered_signals.append(signal)

        self.signals_generated = filtered_signals
        logger.info(f"Generated {len(filtered_signals)} GEX-aware technical signals")
        logger.info(f"  Filtered from {len(tech_signals)} original technical signals")

        return filtered_signals

    def _classify_gex_regime(self, gex_value: float) -> str:
        """Classify GEX regime based on value."""
        if gex_value > self.gex_positive_high:
            return "POSITIVE_GAMMA_HIGH"
        elif gex_value > 0:
            return "POSITIVE_GAMMA_LOW"
        elif gex_value > self.gex_negative_high:
            return "NEGATIVE_GAMMA_LOW"
        else:
            return "NEGATIVE_GAMMA_HIGH"


def run_technical_baseline_test():
    """Run technical indicator baseline test."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger.info("=" * 80)
    logger.info("TECHNICAL INDICATOR BASELINE TEST")
    logger.info("Testing MACD + RSI + Bollinger Bands strategy")
    logger.info("=" * 80)

    # Create sample price data for testing
    dates = pd.date_range(start="2024-01-01", end="2024-03-01", freq="D")
    np.random.seed(42)

    # Generate synthetic price data with trend and volatility
    prices = [100]
    for i in range(1, len(dates)):
        # Add trend and random walk
        trend = 0.001 * np.sin(i / 10)  # Sinusoidal trend
        volatility = np.random.normal(0, 0.02)  # 2% daily volatility
        new_price = prices[-1] * (1 + trend + volatility)
        prices.append(new_price)

    price_data = pd.DataFrame(
        {
            "date": dates,
            "open": prices,
            "high": [p * 1.01 for p in prices],  # High ~1% above close
            "low": [p * 0.99 for p in prices],  # Low ~1% below close
            "close": prices,
        }
    )

    # Test basic technical indicator strategy
    logger.info("\n1. Basic Technical Indicator Strategy:")
    logger.info("-" * 40)
    tech_baseline = TechnicalIndicatorBaseline()
    signals = tech_baseline.generate_signals(price_data)

    if signals:
        logger.info(f"Signals generated: {len(signals)}")
        for signal in signals[:3]:  # Show first 3
            logger.info(
                f"  {signal['date']}: {signal['direction'].upper()} "
                f"(confidence: {signal['confidence']:.0f}%, reason: {signal['reason']})"
            )

    # Test GEX-aware technical strategy
    logger.info("\n2. GEX-Aware Technical Strategy:")
    logger.info("-" * 40)

    # Create sample GEX data
    gex_data = {}
    for i, date in enumerate(dates):
        # Oscillate between positive and negative gamma
        gex_value = 5e9 * np.sin(i / 15) + np.random.normal(0, 1e9)
        gex_data[date.strftime("%Y-%m-%d")] = gex_value

    gex_tech_baseline = GEXAwareTechnicalBaseline()
    gex_signals = gex_tech_baseline.generate_signals_with_gex(price_data, gex_data)

    if gex_signals:
        logger.info(f"GEX-filtered signals: {len(gex_signals)}")
        for signal in gex_signals[:3]:  # Show first 3
            logger.info(
                f"  {signal['date']}: {signal['direction'].upper()} "
                f"(GEX: {signal['gex_value']/1e9:.1f}B, regime: {signal['gex_regime']})"
            )

    logger.info("\n" + "=" * 80)
    logger.info("✅ Technical baseline strategies ready for comparison")
    logger.info("=" * 80)


if __name__ == "__main__":
    run_technical_baseline_test()
