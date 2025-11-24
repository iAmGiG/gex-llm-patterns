"""
Baseline GEX Strategy - Issue #58
Trades every negative GEX day without LLM filtering to establish performance baseline.

This strategy proves whether LLM intelligence adds value over mechanical rules.
Uses configuration from config_defaults/trading_config.yaml
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

from src.utils.date_utils import today_str

logger = logging.getLogger(__name__)


class BaselineGEXStrategy:
    """
    Raw negative GEX strategy - trades every occurrence without intelligence.

    Purpose: Establish baseline performance to prove LLM filtering adds value.
    Configuration-driven for consistent comparison with LLM strategies.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize baseline strategy with configuration.

        Args:
            config_path: Path to trading config YAML file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Extract trading parameters from config
        trading_config = self.config.get("validated_trading_engine", {})

        # Position sizing from config
        position_config = trading_config.get("position_sizing", {})
        self.conservative_position_pct = position_config.get("conservative_position_pct", 1.5) / 100
        self.kelly_optimal_pct = position_config.get("kelly_optimal_pct", 7.1) / 100
        self.max_position_pct = position_config.get("max_position_pct", 10.0) / 100

        # Risk management from config
        risk_config = trading_config.get("risk_management", {})
        self.stop_loss_pct = risk_config.get("stop_loss_pct", 1.0) / 100
        self.profit_target_pct = risk_config.get("profit_target_pct", 1.5) / 100
        self.max_holding_days = risk_config.get("max_holding_days", 2)
        self.daily_loss_limit_pct = risk_config.get("daily_loss_limit_pct", 2.0) / 100

        # Gamma trap specific parameters
        gamma_trap_config = trading_config.get("gamma_trap_strategy", {})
        self.min_confidence = gamma_trap_config.get("min_confidence", 75.0)
        self.max_flip_distance = gamma_trap_config.get("max_flip_distance", 5.0) / 100
        self.required_gex_regime = gamma_trap_config.get("required_gex_regime", "negative")
        self.fomc_avoidance_days = gamma_trap_config.get("fomc_avoidance_days", 7)

        # Strategy state
        self.signals_generated = []
        self.position_size = self.conservative_position_pct  # Default to conservative

        logger.info(f"Initialized BaselineGEXStrategy with parameters:")
        logger.info(f"  Risk: {self.stop_loss_pct:.1%}, Reward: {self.profit_target_pct:.1%}")
        logger.info(f"  Position Size: {self.position_size:.1%} (conservative)")
        logger.info(f"  Max Holding: {self.max_holding_days} days")

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

    def set_position_sizing(self, mode: str = "conservative"):
        """Set position sizing mode.

        Args:
            mode: 'conservative', 'kelly', or 'aggressive'
        """
        if mode == "conservative":
            self.position_size = self.conservative_position_pct
        elif mode == "kelly":
            self.position_size = self.kelly_optimal_pct
        elif mode == "aggressive":
            self.position_size = self.max_position_pct
        else:
            logger.warning(f"Unknown position sizing mode: {mode}")

        logger.info(f"Position sizing set to {mode}: {self.position_size:.1%}")

    def generate_signals(
        self, gex_data: Dict, price_data: Optional[pd.DataFrame] = None, flip_points: Optional[Dict] = None
    ) -> List[Dict]:
        """Generate signals for every negative GEX day (no filtering).

        Args:
            gex_data: Dictionary with date -> GEX value mappings
            price_data: Optional price data for additional context
            flip_points: Optional flip point data for distance calculations

        Returns:
            List of trading signals
        """
        signals = []

        for date_str, gex_value in gex_data.items():
            # Simple rule: enter contrarian when GEX < 0
            if gex_value < 0:
                signal = {
                    "date": date_str,
                    "gex_value": gex_value,
                    "gex_regime": self._classify_gex_regime(gex_value),
                    "direction": "contrarian",  # Trade opposite to implied direction
                    "confidence": 100.0,  # No filtering - always 100%
                    "reason": "negative_gex_regime",
                    "entry_trigger": "GEX < 0 (baseline rule)",
                    "position_size": self.position_size,
                    "stop_loss_pct": self.stop_loss_pct,
                    "target_pct": self.profit_target_pct,
                    "max_holding_days": self.max_holding_days,
                }

                # Add flip point distance if available
                if flip_points and date_str in flip_points:
                    flip_point = flip_points[date_str]
                    if price_data is not None and not price_data.empty:
                        date_price = price_data[price_data["date"] == pd.to_datetime(date_str)]
                        if not date_price.empty:
                            spot = date_price["close"].iloc[0]
                            distance_pct = abs(spot - flip_point) / flip_point
                            signal["flip_distance_pct"] = distance_pct
                            signal["within_flip_threshold"] = distance_pct <= self.max_flip_distance

                signals.append(signal)

        self.signals_generated = signals
        logger.info(f"Generated {len(signals)} baseline signals from {len(gex_data)} days")
        logger.info(f"  Negative GEX days: {len(signals)} ({len(signals)/len(gex_data)*100:.1f}%)")

        return signals

    def _classify_gex_regime(self, gex_value: float) -> str:
        """Classify GEX regime based on value."""
        if gex_value > 1e9:
            return "POSITIVE_GAMMA_HIGH"
        elif gex_value > 0:
            return "POSITIVE_GAMMA_LOW"
        elif gex_value > -1e9:
            return "NEGATIVE_GAMMA_LOW"
        else:
            return "NEGATIVE_GAMMA_HIGH"

    def backtest(
        self,
        gex_data: Dict,
        price_data: pd.DataFrame,
        flip_points: Optional[Dict] = None,
        symbol: str = "SPY",
        test_period: Optional[str] = None,
    ) -> Dict:
        """Backtest the baseline strategy.

        Args:
            gex_data: GEX values by date
            price_data: Price data with columns ['date', 'open', 'high', 'low', 'close']
            flip_points: Optional flip point data

        Returns:
            Backtest results with performance metrics
        """
        signals = self.generate_signals(gex_data, price_data, flip_points)

        if not signals:
            return self._empty_results("No signals generated")

        trades = []
        daily_pnl = []

        for signal in signals:
            trade_result = self._execute_trade(signal, price_data)
            if trade_result:
                trades.append(trade_result)
                daily_pnl.append(trade_result["pnl_pct"] * self.position_size)

        # Calculate performance metrics
        if trades:
            results = self._calculate_metrics(trades, daily_pnl)
            # Add metadata
            results.update(self._add_metadata(symbol, test_period, gex_data, price_data))
            return results
        else:
            empty_results = self._empty_results("No valid trades executed")
            empty_results.update(self._add_metadata(symbol, test_period, gex_data, price_data))
            return empty_results

    def _execute_trade(self, signal: Dict, price_data: pd.DataFrame) -> Optional[Dict]:
        """Execute a single trade based on signal."""
        date = pd.to_datetime(signal["date"])
        entry_row = price_data[price_data["date"] == date]

        if entry_row.empty:
            return None

        entry_price = entry_row["close"].iloc[0]
        stop_loss = entry_price * (1 - self.stop_loss_pct)
        target = entry_price * (1 + self.profit_target_pct)

        # Track trade over holding period
        for days_held in range(1, self.max_holding_days + 1):
            check_date = date + pd.Timedelta(days=days_held)
            check_row = price_data[price_data["date"] == check_date]

            if check_row.empty:
                continue

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

            # Time exit on last day
            if days_held == self.max_holding_days:
                exit_price = check_row["close"].iloc[0]
                exit_reason = "time_exit"
                exit_date = check_date
                break
        else:
            return None  # No valid exit found

        # Calculate return based on direction
        if signal["direction"] == "contrarian":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
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
            "gex_value": signal["gex_value"],
            "gex_regime": signal["gex_regime"],
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
            "trades": trades,
            "strategy_type": "baseline_negative_gex",
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
            "strategy_type": "baseline_negative_gex",
        }

    def _add_metadata(self, symbol: str, test_period: Optional[str], gex_data: Dict, price_data: pd.DataFrame) -> Dict:
        """Add metadata to results."""

        # Determine test period from data if not provided
        if test_period is None:
            start_date = price_data["date"].min()
            end_date = price_data["date"].max()
            if hasattr(start_date, "strftime"):
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                test_period = f"{start_str} to {end_str}"
            else:
                test_period = "Unknown period"

        # Calculate GEX statistics
        gex_values = list(gex_data.values())
        negative_gex_days = sum(1 for v in gex_values if v < 0)

        return {
            "metadata": {
                "symbol": symbol,
                "test_period": test_period,
                "total_days": len(price_data),
                "negative_gex_days": negative_gex_days,
                "negative_gex_percentage": negative_gex_days / len(gex_values) * 100 if gex_values else 0,
                "run_date": today_str(),
                "strategy_version": "baseline_negative_gex_v1.0",
                "position_sizing": f"{self.position_size:.1%}",
                "risk_management": {
                    "stop_loss": f"{self.stop_loss_pct:.1%}",
                    "profit_target": f"{self.profit_target_pct:.1%}",
                    "max_holding_days": self.max_holding_days,
                },
            }
        }

    def compare_to_llm(self, llm_results: Dict) -> Dict:
        """Compare baseline performance to LLM-filtered strategy.

        Args:
            llm_results: Results from LLM strategy backtest

        Returns:
            Comparison metrics showing value added by LLM
        """
        baseline_signals = len(self.signals_generated)
        llm_signals = llm_results.get("total_trades", 0)

        # Calculate filtering efficiency
        if baseline_signals > 0:
            filtering_ratio = 1 - (llm_signals / baseline_signals)
            selectivity = llm_signals / baseline_signals
        else:
            filtering_ratio = 0
            selectivity = 0

        # Performance improvements - use config-based baseline if no backtest was run
        if not hasattr(self, "last_backtest_results"):
            # Load baseline expectations from config
            analysis_config = self.config.get("baseline_comparison", {})
            baseline_metrics = {
                "win_rate": analysis_config.get("expected_baseline_win_rate", 0.43),
                "expected_value": analysis_config.get("expected_baseline_ev", -0.0028),
                "sharpe_ratio": analysis_config.get("expected_baseline_sharpe", -0.15),
                "max_drawdown": analysis_config.get("expected_baseline_drawdown", -0.045),
                "total_trades": baseline_signals,
            }
            self.last_backtest_results = baseline_metrics  # Cache for future use
        else:
            baseline_metrics = self.last_backtest_results

        comparison = {
            "signal_analysis": {
                "baseline_signals": baseline_signals,
                "llm_signals": llm_signals,
                "filtering_ratio": filtering_ratio,
                "selectivity": selectivity,
                "signals_per_day": baseline_signals / len(self.signals_generated) if self.signals_generated else 0,
            },
            "performance_comparison": {
                "win_rate": {
                    "baseline": baseline_metrics.get("win_rate", 0.5),
                    "llm": llm_results.get("win_rate", 0),
                    "improvement": llm_results.get("win_rate", 0) - baseline_metrics.get("win_rate", 0.5),
                },
                "expected_value": {
                    "baseline": baseline_metrics.get("expected_value", 0),
                    "llm": llm_results.get("expected_value", 0),
                    "improvement": llm_results.get("expected_value", 0) - baseline_metrics.get("expected_value", 0),
                },
                "sharpe_ratio": {
                    "baseline": baseline_metrics.get("sharpe_ratio", 0),
                    "llm": llm_results.get("sharpe_ratio", 0),
                    "improvement": llm_results.get("sharpe_ratio", 0) - baseline_metrics.get("sharpe_ratio", 0),
                },
                "max_drawdown": {
                    "baseline": baseline_metrics.get("max_drawdown", 0),
                    "llm": llm_results.get("max_drawdown", 0),
                    "improvement": llm_results.get("max_drawdown", 0) - baseline_metrics.get("max_drawdown", 0),
                },
            },
            "value_added": self._calculate_value_added(baseline_metrics, llm_results),
            "conclusion": self._generate_conclusion(baseline_metrics, llm_results),
        }

        return comparison

    def _calculate_value_added(self, baseline: Dict, llm: Dict) -> Dict:
        """Calculate the value added by LLM filtering."""
        baseline_ev = baseline.get("expected_value", 0)
        llm_ev = llm.get("expected_value", 0)

        # Calculate improvement percentage
        if baseline_ev != 0:
            ev_improvement_pct = ((llm_ev - baseline_ev) / abs(baseline_ev)) * 100
        else:
            ev_improvement_pct = 100 if llm_ev > 0 else 0

        return {
            "expected_value_improvement_pct": ev_improvement_pct,
            "additional_return_per_trade": llm_ev - baseline_ev,
            "risk_adjusted_improvement": llm.get("sharpe_ratio", 0) - baseline.get("sharpe_ratio", 0),
            "selectivity_value": (
                "Positive"
                if llm_ev > baseline_ev and llm.get("total_trades", 0) < len(self.signals_generated)
                else "Negative"
            ),
        }

    def _generate_conclusion(self, baseline: Dict, llm: Dict) -> str:
        """Generate conclusion about LLM value add."""
        baseline_ev = baseline.get("expected_value", 0)
        llm_ev = llm.get("expected_value", 0)

        if llm_ev > baseline_ev:
            improvement = ((llm_ev - baseline_ev) / abs(baseline_ev) * 100) if baseline_ev != 0 else 100
            return f"✅ LLM filtering adds {improvement:.1f}% improvement in expected value - intelligent filtering provides edge"
        elif llm_ev == baseline_ev:
            return "⚠️ LLM filtering matches baseline performance - no clear value added"
        else:
            degradation = ((baseline_ev - llm_ev) / abs(baseline_ev) * 100) if baseline_ev != 0 else 100
            return f"❌ LLM filtering degrades performance by {degradation:.1f}% - model upgrade or prompt engineering needed"
