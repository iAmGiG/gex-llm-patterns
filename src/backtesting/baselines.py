"""
Baseline Trading Strategies for Comparison (Issue #8)

Simple strategies for benchmarking GEX pattern performance:
- BuyAndHold: Always long, rebalance monthly
- MACDStrategy: MACD signal line crossover
- RSIStrategy: RSI oversold/overbought mean reversion
- MomentumStrategy: Simple price momentum

These provide baselines to determine if GEX patterns add value.
"""

from typing import Any, Dict

import numpy as np
import pandas as pd


class BuyAndHoldStrategy:
    """
    Buy and hold baseline strategy.

    Simply buys on first signal and holds until end.
    Represents the passive benchmark.
    """

    def __init__(self):
        self.entered = False

    def generate_signal(self, symbol: str, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Generate buy-and-hold signal."""
        if not self.entered and len(data) > 0:
            self.entered = True
            return {
                "action": "BUY",
                "position_size": 1.0,
                "confidence": 1.0,
                "reasoning": "Buy and hold entry",
            }

        return {
            "action": "HOLD",
            "position_size": 0.0,
            "confidence": 1.0,
            "reasoning": "Holding position",
        }

    def reset(self):
        """Reset for new backtest."""
        self.entered = False


class MACDStrategy:
    """
    MACD crossover strategy.

    BUY when MACD crosses above signal line.
    SELL when MACD crosses below signal line.
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        Args:
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line EMA period (default: 9)
        """
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
        self.prev_histogram = None

    def generate_signal(self, symbol: str, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Generate MACD crossover signal."""
        if len(data) < self.slow + self.signal_period:
            return {"action": "HOLD", "position_size": 0.0, "confidence": 0.0, "reasoning": "Insufficient data"}

        prices = data["close"]

        # Calculate MACD
        fast_ema = prices.ewm(span=self.fast, adjust=False).mean()
        slow_ema = prices.ewm(span=self.slow, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        current_hist = histogram.iloc[-1]

        # Crossover detection
        if self.prev_histogram is not None:
            if self.prev_histogram < 0 and current_hist > 0:
                # Bullish crossover
                self.prev_histogram = current_hist
                return {
                    "action": "BUY",
                    "position_size": 1.0,
                    "confidence": min(abs(current_hist) / 0.5, 1.0),
                    "reasoning": f"MACD bullish crossover (histogram: {current_hist:.4f})",
                }
            elif self.prev_histogram > 0 and current_hist < 0:
                # Bearish crossover
                self.prev_histogram = current_hist
                return {
                    "action": "SELL",
                    "position_size": 1.0,
                    "confidence": min(abs(current_hist) / 0.5, 1.0),
                    "reasoning": f"MACD bearish crossover (histogram: {current_hist:.4f})",
                }

        self.prev_histogram = current_hist
        return {"action": "HOLD", "position_size": 0.0, "confidence": 0.5, "reasoning": "No MACD crossover"}

    def reset(self):
        """Reset for new backtest."""
        self.prev_histogram = None


class RSIStrategy:
    """
    RSI mean reversion strategy.

    BUY when RSI < oversold threshold.
    SELL when RSI > overbought threshold.
    """

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        """
        Args:
            period: RSI calculation period (default: 14)
            oversold: Oversold threshold (default: 30)
            overbought: Overbought threshold (default: 70)
        """
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signal(self, symbol: str, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Generate RSI mean reversion signal."""
        if len(data) < self.period + 1:
            return {"action": "HOLD", "position_size": 0.0, "confidence": 0.0, "reasoning": "Insufficient data"}

        prices = data["close"]

        # Calculate RSI
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return {"action": "HOLD", "position_size": 0.0, "confidence": 0.0, "reasoning": "RSI calculation error"}

        if current_rsi < self.oversold:
            confidence = (self.oversold - current_rsi) / self.oversold
            return {
                "action": "BUY",
                "position_size": min(confidence + 0.5, 1.0),
                "confidence": confidence,
                "reasoning": f"RSI oversold ({current_rsi:.1f} < {self.oversold})",
            }
        elif current_rsi > self.overbought:
            confidence = (current_rsi - self.overbought) / (100 - self.overbought)
            return {
                "action": "SELL",
                "position_size": min(confidence + 0.5, 1.0),
                "confidence": confidence,
                "reasoning": f"RSI overbought ({current_rsi:.1f} > {self.overbought})",
            }

        return {
            "action": "HOLD",
            "position_size": 0.0,
            "confidence": 0.5,
            "reasoning": f"RSI neutral ({current_rsi:.1f})",
        }

    def reset(self):
        """Reset for new backtest."""
        pass


class MomentumStrategy:
    """
    Simple price momentum strategy.

    BUY if price is above N-day moving average.
    SELL if price is below N-day moving average.
    """

    def __init__(self, lookback: int = 20, threshold: float = 0.0):
        """
        Args:
            lookback: Lookback period for moving average (default: 20)
            threshold: Percentage above/below MA to trigger (default: 0 = any)
        """
        self.lookback = lookback
        self.threshold = threshold

    def generate_signal(self, symbol: str, data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """Generate momentum signal."""
        if len(data) < self.lookback:
            return {"action": "HOLD", "position_size": 0.0, "confidence": 0.0, "reasoning": "Insufficient data"}

        prices = data["close"]
        current_price = prices.iloc[-1]
        ma = prices.rolling(window=self.lookback).mean().iloc[-1]

        if pd.isna(ma):
            return {"action": "HOLD", "position_size": 0.0, "confidence": 0.0, "reasoning": "MA calculation error"}

        pct_diff = (current_price - ma) / ma

        if pct_diff > self.threshold:
            confidence = min(pct_diff * 10, 1.0)
            return {
                "action": "BUY",
                "position_size": min(confidence + 0.5, 1.0),
                "confidence": confidence,
                "reasoning": f"Price above {self.lookback}-day MA by {pct_diff*100:.2f}%",
            }
        elif pct_diff < -self.threshold:
            confidence = min(abs(pct_diff) * 10, 1.0)
            return {
                "action": "SELL",
                "position_size": min(confidence + 0.5, 1.0),
                "confidence": confidence,
                "reasoning": f"Price below {self.lookback}-day MA by {abs(pct_diff)*100:.2f}%",
            }

        return {
            "action": "HOLD",
            "position_size": 0.0,
            "confidence": 0.5,
            "reasoning": f"Price near {self.lookback}-day MA",
        }

    def reset(self):
        """Reset for new backtest."""
        pass


# Convenience function to get all baselines
def get_baseline_strategies() -> Dict[str, object]:
    """
    Get dictionary of all baseline strategies.

    Returns:
        Dict mapping strategy name to strategy instance
    """
    return {
        "buy_and_hold": BuyAndHoldStrategy(),
        "macd_crossover": MACDStrategy(),
        "rsi_mean_revert": RSIStrategy(),
        "momentum_20d": MomentumStrategy(lookback=20),
    }
