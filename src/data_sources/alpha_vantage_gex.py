"""
Alpha Vantage API Client for GEX-LLM Pattern Analysis

This module specializes in retrieving options chain data from Alpha Vantage API
for SPY/SPX gamma exposure calculations. Optimized for the free tier rate limits
with intelligent caching.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
import requests
import pandas as pd
import os
from config.config_loader import ConfigLoader
from src.utils.date_utils import (
    get_processed_date_range,
    localize_df,
    get_default_timezone,
)
from src.cache import UnifiedCacheManager


class AlphaVantageGEXClient:
    """
    Alpha Vantage client specialized for GEX calculation data needs.

    Focuses on:
    - SPY/SPX options chains (historical and current)
    - Underlying stock price data
    - Rate limiting for free tier (75 calls/min)
    - Intelligent caching for historical data
    """

    def __init__(self, cache_manager: Optional[UnifiedCacheManager] = None):
        # Load API key from @config/ loader
        config_loader = ConfigLoader()
        self.api_key = os.getenv(
            "ALPHA_VANTAGE_KEY", config_loader.get("ALPHA_VANTAGE_KEY")
        )

        if not self.api_key:
            logging.warning(
                "Alpha Vantage API key not found in @config/ loader.")

        self.base_url = "https://www.alphavantage.co/query"
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize unified cache (critical for free tier)
        self.cache = cache_manager or UnifiedCacheManager()

        # Rate limiting for free tier
        self.calls_per_minute = 75
        self.call_timestamps = []

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits for free tier."""
        now = datetime.now()
        # Remove calls older than 1 minute
        self.call_timestamps = [
            ts for ts in self.call_timestamps
            if now - ts < timedelta(minutes=1)
        ]

        if len(self.call_timestamps) >= self.calls_per_minute:
            self.logger.warning("Rate limit approached, caching is critical")
            return False

        self.call_timestamps.append(now)
        return True

    def fetch_options_chain(self, symbol: str, expiration_date: str) -> pd.DataFrame:
        """
        Fetch options chain for specific symbol and expiration.

        Args:
            symbol: Underlying symbol (SPY, SPX)
            expiration_date: Options expiration date (YYYY-MM-DD)

        Returns:
            DataFrame with options chain data including strikes, calls, puts

        Note:
            This requires Alpha Vantage Premium. For free tier, we'll need
            to implement alternative data collection or use historical data.
        """
        if not self._check_rate_limit():
            self.logger.warning("Rate limit exceeded, using cached data only")
            return pd.DataFrame()

        cache_key = f"options_{symbol}_{expiration_date}"

        # Check cache first (critical for rate limits)
        cached_data = self.cache.get_market_data(
            cache_key, expiration_date, expiration_date, "options_chain"
        )
        if cached_data is not None:
            self.logger.info(
                f"Using cached options chain for {symbol} {expiration_date}")
            return cached_data

        try:
            # Note: Alpha Vantage free tier doesn't include options data
            # This would require premium subscription or alternative approach
            params = {
                "function": "HISTORICAL_OPTIONS",  # Premium feature
                "symbol": symbol,
                "date": expiration_date,
                "apikey": self.api_key
            }

            response = requests.get(self.base_url, params=params)

            if response.status_code != 200:
                self.logger.error(
                    f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()

            if "Error Message" in data:
                self.logger.error(
                    f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            # Process options data into standardized format
            # This would need to be implemented based on actual API response
            df = self._process_options_data(data)

            # Cache the processed data
            self.cache.set_market_data(
                cache_key, expiration_date, expiration_date, "options_chain", df
            )

            return df

        except Exception as e:
            self.logger.error(f"Error fetching options chain: {e}")
            return pd.DataFrame()

    def fetch_underlying_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch underlying stock data for GEX calculations.

        Args:
            symbol: Stock symbol (SPY, SPX)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        if not self._check_rate_limit():
            cached_only = self.cache.get_market_data(
                symbol, start_date, end_date, "daily_stock"
            )
            if cached_only is not None:
                return cached_only
            else:
                self.logger.error(
                    "Rate limit exceeded and no cached data available")
                return pd.DataFrame()

        try:
            # Process date range
            processed_start, processed_end = get_processed_date_range(
                start_date, end_date)

            # Check cache first
            cached_data = self.cache.get_market_data(
                symbol, processed_start, processed_end, "daily_stock"
            )
            if cached_data is not None:
                self.logger.info(f"Using cached stock data for {symbol}")
                return cached_data

            self.logger.info(
                f"Fetching stock data for {symbol} from {processed_start} to {processed_end}")

            # Determine outputsize based on date range
            days_range = (datetime.strptime(processed_end, "%Y-%m-%d") -
                          datetime.strptime(processed_start, "%Y-%m-%d")).days
            use_full = days_range > 100

            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "full" if use_full else "compact",
                "datatype": "json"
            }

            response = requests.get(self.base_url, params=params)

            if response.status_code != 200:
                self.logger.error(
                    f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()

            if "Error Message" in data:
                self.logger.error(
                    f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            if "Time Series (Daily)" not in data:
                self.logger.warning(f"No time series data found for {symbol}")
                return pd.DataFrame()

            time_series = data["Time Series (Daily)"]
            df = pd.DataFrame.from_dict(time_series, orient="index")

            # Standardize column names for GEX calculations
            df = df.rename(columns={
                "1. open": "open",
                "2. high": "high",
                "3. low": "low",
                "4. close": "close",
                "5. volume": "volume"
            })

            # Convert to proper types
            df.index = pd.to_datetime(df.index)
            for col in df.columns:
                df[col] = pd.to_numeric(df[col])

            # Filter by date range
            df = df[(df.index >= processed_start)
                    & (df.index <= processed_end)]
            df = df.sort_index(ascending=False)

            # Localize timezone
            df = localize_df(df, get_default_timezone())

            # Cache for future use (critical for rate limits)
            self.cache.set_market_data(
                symbol, processed_start, processed_end, "daily_stock", df
            )

            return df

        except Exception as e:
            self.logger.error(f"Error fetching underlying data: {e}")
            return pd.DataFrame()

    def _process_options_data(self, raw_data: Dict) -> pd.DataFrame:
        """
        Process raw options data into standardized format for GEX calculations.

        Args:
            raw_data: Raw API response data

        Returns:
            DataFrame with columns: strike, call_volume, call_oi, put_volume, put_oi, etc.
        """
        # This would need to be implemented based on actual API response format
        # For now, return empty DataFrame as placeholder
        return pd.DataFrame()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        now = datetime.now()
        recent_calls = len([
            ts for ts in self.call_timestamps
            if now - ts < timedelta(minutes=1)
        ])

        return {
            "calls_last_minute": recent_calls,
            "calls_remaining": max(0, self.calls_per_minute - recent_calls),
            "reset_time": now + timedelta(minutes=1) if recent_calls > 0 else now
        }
