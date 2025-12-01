"""
Price Tokenizer
Converts price movements and returns into discrete tokens.
"""

import logging

import numpy as np
import pandas as pd

from .vocabulary import PriceToken, TokenVocabulary

logger = logging.getLogger(__name__)


class PriceTokenizer:
    """
    Tokenize price movements and returns.
    """

    def __init__(self, return_type="log"):
        """
        Initialize price tokenizer.

        Args:
            return_type: Type of returns to calculate ('simple' or 'log')
        """
        self.return_type = return_type
        self.vocabulary = TokenVocabulary()

    def tokenize_return(self, return_value) -> str:
        """
        Tokenize a single return value.

        Args:
            return_value: Percentage return value

        Returns:
            Token string representing the price movement
        """
        if pd.isna(return_value):
            return "[UNK]"

        token = PriceToken.from_return(return_value)
        return token.value

    def tokenize_price_series(self, prices, return_window=1):
        """
        Tokenize a series of prices by calculating returns.

        Args:
            prices: Series of prices with datetime index
            return_window: Window for return calculation (1 = daily, 5 = weekly, etc.)

        Returns of price movement tokens
        """
        # Calculate returns
        if self.return_type == "log":
            returns = (np.log(prices) - np.log(prices.shift(return_window))) * 100
        else:
            returns = ((prices - prices.shift(return_window)) / prices.shift(return_window)) * 100

        # Tokenize returns
        tokens = []
        for date, ret in returns.items():
            token = self.tokenize_return(ret)
            tokens.append(token)

        return tokens

    def tokenize_with_volume(self, prices, volumes):
        """
        Tokenize prices with volume context.

        Args:
            prices: Price series
            volumes: Volume series

        Returns of dictionaries with price and volume tokens
        """
        price_tokens = self.tokenize_price_series(prices)
        volume_tokens = self._tokenize_volume(volumes)

        result = []
        for i, (price_token, volume_token) in enumerate(zip(price_tokens, volume_tokens)):
            result.append({"price": price_token, "volume": volume_token, "composite": f"{price_token}_{volume_token}"})

        return result

    def tokenize_price_levels(self, price, support=None, resistance=None, vwap=None):
        """
        Tokenize price relative to key levels.

        Args:
            price: Current price
            support: Support level
            resistance: Resistance level
            vwap: Volume-weighted average price

        Returnsionary of position tokens
        """
        tokens = {}

        # Price relative to support/resistance
        if support is not None and resistance is not None:
            range_size = resistance - support
            if range_size > 0:
                position = (price - support) / range_size

                if position < 0:
                    tokens["range_position"] = "BELOW_SUPPORT"
                elif position < 0.2:
                    tokens["range_position"] = "NEAR_SUPPORT"
                elif position < 0.4:
                    tokens["range_position"] = "LOWER_RANGE"
                elif position < 0.6:
                    tokens["range_position"] = "MID_RANGE"
                elif position < 0.8:
                    tokens["range_position"] = "UPPER_RANGE"
                elif position < 1.0:
                    tokens["range_position"] = "NEAR_RESISTANCE"
                else:
                    tokens["range_position"] = "ABOVE_RESISTANCE"

        # Price relative to VWAP
        if vwap is not None:
            vwap_distance = (price - vwap) / vwap * 100

            if vwap_distance < -2:
                tokens["vwap_position"] = "FAR_BELOW_VWAP"
            elif vwap_distance < -0.5:
                tokens["vwap_position"] = "BELOW_VWAP"
            elif vwap_distance < 0.5:
                tokens["vwap_position"] = "AT_VWAP"
            elif vwap_distance < 2:
                tokens["vwap_position"] = "ABOVE_VWAP"
            else:
                tokens["vwap_position"] = "FAR_ABOVE_VWAP"

        return tokens

    def tokenize_trend(self, prices, short_window=5, long_window=20):
        """
        Tokenize price trend using moving averages.

        Args:
            prices: Price series
            short_window: Short MA window
            long_window: Long MA window

        Returns of trend tokens
        """
        short_ma = prices.rolling(window=short_window).mean()
        long_ma = prices.rolling(window=long_window).mean()

        tokens = []
        for date in prices.index:
            if pd.isna(short_ma[date]) or pd.isna(long_ma[date]):
                tokens.append("[UNK]")
                continue

            price = prices[date]

            # Determine trend
            if short_ma[date] > long_ma[date]:
                if price > short_ma[date]:
                    token = "TREND_STRONG_UP"
                else:
                    token = "TREND_WEAK_UP"
            else:
                if price < short_ma[date]:
                    token = "TREND_STRONG_DOWN"
                else:
                    token = "TREND_WEAK_DOWN"

            tokens.append(token)

        return tokens

    def _tokenize_volume(self, volumes):
        """Tokenize volume levels."""
        # Calculate volume percentiles
        volume_20 = volumes.rolling(window=20).quantile(0.2)
        volume_50 = volumes.rolling(window=20).quantile(0.5)
        volume_80 = volumes.rolling(window=20).quantile(0.8)

        tokens = []
        for date, volume in volumes.items():
            if pd.isna(volume) or pd.isna(volume_50[date]):
                tokens.append("VOL_UNKNOWN")
            elif volume < volume_20[date]:
                tokens.append("VOL_VERY_LOW")
            elif volume < volume_50[date]:
                tokens.append("VOL_LOW")
            elif volume < volume_80[date]:
                tokens.append("VOL_NORMAL")
            else:
                tokens.append("VOL_HIGH")

        return tokens

    def tokenize_volatility(self, prices, window=20):
        """
        Tokenize realized volatility.

        Args:
            prices: Price series
            window: Rolling window for volatility calculation

        Returns of volatility tokens
        """
        # Calculate returns
        returns = prices.pct_change()

        # Calculate rolling volatility (annualized)
        volatility = returns.rolling(window=window).std() * np.sqrt(252) * 100

        tokens = []
        for date, vol in volatility.items():
            if pd.isna(vol):
                tokens.append("VOL_UNKNOWN")
            elif vol < 10:
                tokens.append("VOL_VERY_LOW")
            elif vol < 15:
                tokens.append("VOL_LOW")
            elif vol < 20:
                tokens.append("VOL_NORMAL")
            elif vol < 30:
                tokens.append("VOL_HIGH")
            elif vol < 50:
                tokens.append("VOL_VERY_HIGH")
            else:
                tokens.append("VOL_EXTREME")

        return tokens

    def get_return_statistics(self, prices):
        """
        Calculate return distribution statistics.

        Args:
            prices: Price series

        Returnsionary with return statistics
        """
        returns = prices.pct_change() * 100

        return {
            "mean_return": returns.mean(),
            "std_return": returns.std(),
            "skewness": returns.skew(),
            "kurtosis": returns.kurtosis(),
            "sharpe_ratio": returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0,
            "max_return": returns.max(),
            "min_return": returns.min(),
            "positive_days": (returns > 0).sum() / len(returns),
            "large_move_days": (returns.abs() > 2).sum() / len(returns),
        }

    def validate_price_tokens(self, prices, tokens):
        """
        Validate price tokenization quality.

        Args:
            prices: Original price series
            tokens: Generated tokens

        Returns:
            Validation report
        """
        returns = prices.pct_change() * 100

        validation = {"length_match": len(prices) == len(tokens), "return_stats": self.get_return_statistics(prices)}

        # Check token distribution
        token_counts = {}
        for token_enum in PriceToken:
            token_counts[token_enum.value] = tokens.count(token_enum.value)

        validation["token_distribution"] = {k: v / len(tokens) for k, v in token_counts.items() if len(tokens) > 0}

        # Check extreme return mapping
        if len(returns.dropna()) > 0:
            extreme_up = returns > 3
            extreme_down = returns < -3

            if extreme_up.any():
                extreme_up_tokens = [tokens[i] for i, v in enumerate(extreme_up) if v]
                validation["extreme_up_accuracy"] = (
                    sum(1 for t in extreme_up_tokens if "MOON" in t) / len(extreme_up_tokens)
                    if extreme_up_tokens
                    else 0
                )

            if extreme_down.any():
                extreme_down_tokens = [tokens[i] for i, v in enumerate(extreme_down) if v]
                validation["extreme_down_accuracy"] = (
                    sum(1 for t in extreme_down_tokens if "CRASH" in t) / len(extreme_down_tokens)
                    if extreme_down_tokens
                    else 0
                )

        return validation
