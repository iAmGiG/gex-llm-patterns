"""
GEX Tokenizer
Converts continuous GEX values into discrete tokens based on rolling percentiles.
"""

import datetime
import logging

import numpy as np
import pandas as pd

from src.utils.config_manager import get_config

from .vocabulary import GEXToken, TokenVocabulary

logger = logging.getLogger(__name__)


class GEXTokenizer:
    """
    Tokenize GEX values using adaptive percentile-based binning.
    """

    def __init__(self, lookback_days=None, update_frequency=None):
        """
        Initialize GEX tokenizer.

        Args:
            lookback_days: Days to look back for percentile calculation (default from config)
            update_frequency: How often to update percentiles (default from config)
        """
        config = get_config()

        # Use config values as defaults, allow override via parameters
        self.lookback_days = lookback_days or config.get("tokenization.gex_tokenizer.lookback_days", 252)
        self.update_frequency = update_frequency or config.get("tokenization.gex_tokenizer.update_frequency", "monthly")
        self.min_history_samples = config.get("tokenization.gex_tokenizer.min_history_samples", 20)
        self.percentile_thresholds = config.get(
            "tokenization.gex_tokenizer.percentile_thresholds", [10, 20, 30, 40, 50, 60, 70, 80, 90]
        )

        self.vocabulary = TokenVocabulary()

        # Cache for percentile thresholds
        self._percentile_cache = {}
        self._last_update = None

    def tokenize_single(self, gex_value, historical_gex, date=None) -> str:
        """
        Tokenize a single GEX value.

        Args:
            gex_value: The GEX value to tokenize
            historical_gex: Historical GEX values for percentile calculation
            date: Date for the GEX value (for cache management)

        Returns:
            Token string representing the GEX state
        """
        if pd.isna(gex_value):
            return "[UNK]"

        # Calculate percentile
        percentile = self._calculate_percentile(gex_value, historical_gex, date)

        # Get token from percentile
        token = GEXToken.from_percentile(percentile)
        return token.value

    def tokenize_series(self, gex_series, rolling_window=True):
        """
        Tokenize a series of GEX values.

        Args:
            gex_series: Series of GEX values with datetime index
            rolling_window: If True, use rolling window for each date

        Returns:
            List of tokens
        """
        tokens = []

        for date, gex_value in gex_series.items():
            if rolling_window:
                # Get historical data up to this date
                lookback_start = date - datetime.timedelta(days=self.lookback_days)
                historical = gex_series[lookback_start:date]
            else:
                # Use entire series for percentile calculation
                historical = gex_series

            token = self.tokenize_single(gex_value, historical, date)
            tokens.append(token)

        return tokens

    def tokenize_with_context(self, gex_value, historical_gex, spot_price, flip_point=None):
        """
        Tokenize GEX with additional context information.

        Args:
            gex_value: Current GEX value
            historical_gex: Historical GEX for percentiles
            spot_price: Current spot price
            flip_point: Zero gamma flip point

        Returns:
            Dictionary with multiple tokens including context
        """
        result = {
            "gex_state": self.tokenize_single(gex_value, historical_gex),
            "gex_sign": "GEX_POSITIVE" if gex_value > 0 else "GEX_NEGATIVE",
            "gex_magnitude": self._tokenize_magnitude(abs(gex_value), historical_gex),
        }

        # Add flip point context if available
        if flip_point is not None and spot_price is not None:
            distance_to_flip = (flip_point - spot_price) / spot_price
            result["flip_distance"] = self._tokenize_flip_distance(distance_to_flip)

        return result

    def _calculate_percentile(self, value, historical, date=None) -> float:
        """
        Calculate percentile of value in historical distribution.

        Args:
            value: Value to calculate percentile for
            historical: Historical values for distribution
            date: Date for cache management

        Returns:
            Percentile (0-100)
        """
        if len(historical) < self.min_history_samples:  # Need minimum history
            logger.warning(f"Insufficient history ({len(historical)} values), using naive percentile")
            return 50.0

        # Check if we need to update cache
        cache_key = self._get_cache_key(date)
        if cache_key not in self._percentile_cache or self._should_update_cache(date):
            self._update_percentile_cache(historical, cache_key)

        # Use cached percentiles
        percentiles = self._percentile_cache[cache_key]

        # Find percentile
        percentile = (historical <= value).sum() / len(historical) * 100
        return percentile

    def _tokenize_magnitude(self, abs_gex, historical) -> str:
        """Tokenize the magnitude of GEX."""
        abs_historical = historical.abs()

        if len(abs_historical) < self.min_history_samples:
            return "MAG_UNKNOWN"

        percentile = (abs_historical <= abs_gex).sum() / len(abs_historical) * 100

        if percentile < 20:
            return "MAG_VERY_LOW"
        elif percentile < 40:
            return "MAG_LOW"
        elif percentile < 60:
            return "MAG_MEDIUM"
        elif percentile < 80:
            return "MAG_HIGH"
        else:
            return "MAG_VERY_HIGH"

    def _tokenize_flip_distance(self, distance_pct) -> str:
        """Tokenize distance to flip point as percentage."""
        if distance_pct < -0.05:
            return "FLIP_FAR_BELOW"
        elif distance_pct < -0.02:
            return "FLIP_BELOW"
        elif distance_pct < -0.005:
            return "FLIP_NEAR_BELOW"
        elif distance_pct < 0.005:
            return "FLIP_AT"
        elif distance_pct < 0.02:
            return "FLIP_NEAR_ABOVE"
        elif distance_pct < 0.05:
            return "FLIP_ABOVE"
        else:
            return "FLIP_FAR_ABOVE"

    def _get_cache_key(self, date) -> str:
        """Get cache key based on update frequency."""
        if date is None:
            return "default"

        if self.update_frequency == "daily":
            return date.strftime("%Y-%m-%d")
        elif self.update_frequency == "weekly":
            return date.strftime("%Y-W%U")
        elif self.update_frequency == "monthly":
            return date.strftime("%Y-%m")
        else:
            return "default"

    def _should_update_cache(self, date) -> bool:
        """Check if cache should be updated."""
        if self._last_update is None:
            return True

        if date is None:
            return False

        if self.update_frequency == "daily":
            return date.date() != self._last_update.date()
        elif self.update_frequency == "weekly":
            return date.isocalendar()[1] != self._last_update.isocalendar()[1]
        elif self.update_frequency == "monthly":
            return date.month != self._last_update.month

        return False

    def _update_percentile_cache(self, historical, cache_key):
        """Update percentile cache with new thresholds."""
        self._percentile_cache[cache_key] = {
            p: np.percentile(historical.dropna(), p) for p in self.percentile_thresholds
        }
        self._last_update = datetime.datetime.now()

    def get_token_statistics(self, tokens):
        """
        Calculate statistics about token distribution.

        Args:
            tokens: List of GEX tokens

        Returns:
            Dictionary with token frequency statistics
        """
        total = len(tokens)
        if total == 0:
            return {}

        stats = {}
        for token_enum in GEXToken:
            count = tokens.count(token_enum.value)
            stats[token_enum.value] = count / total

        # Add balance metrics
        neg_tokens = sum(1 for t in tokens if "NEG" in t)
        pos_tokens = sum(1 for t in tokens if "POS" in t)

        stats["balance_ratio"] = pos_tokens / max(1, neg_tokens)
        stats["extremes_ratio"] = (
            tokens.count(GEXToken.EXTREME_NEG.value) + tokens.count(GEXToken.EXTREME_POS.value)
        ) / total

        return stats

    def validate_tokenization(self, original_series, tokens):
        """
        Validate that tokenization preserves important properties.

        Args:
            original_series: Original GEX series
            tokens: Generated tokens

        Returns:
            Validation report
        """
        validation = {
            "length_match": len(original_series) == len(tokens),
            "na_handling": sum(pd.isna(original_series)) == tokens.count("[UNK]"),
            "token_distribution": self.get_token_statistics(tokens),
        }

        # Check for regime preservation
        if len(original_series) > 0:
            # Check if extreme values map to extreme tokens
            extreme_high = original_series.quantile(0.95)
            extreme_low = original_series.quantile(0.05)

            extreme_high_idx = original_series >= extreme_high
            extreme_low_idx = original_series <= extreme_low

            if extreme_high_idx.any():
                high_tokens = [tokens[i] for i in extreme_high_idx[extreme_high_idx].index]
                validation["extreme_high_mapping"] = sum(1 for t in high_tokens if "EXTREME_POS" in t) / len(
                    high_tokens
                )

            if extreme_low_idx.any():
                low_tokens = [tokens[i] for i in extreme_low_idx[extreme_low_idx].index]
                validation["extreme_low_mapping"] = sum(1 for t in low_tokens if "EXTREME_NEG" in t) / len(low_tokens)

        return validation
