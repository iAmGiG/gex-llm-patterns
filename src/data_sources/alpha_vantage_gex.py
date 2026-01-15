"""Alpha Vantage API Client for GEX-LLM Pattern Analysis.

This module specializes in retrieving options chain data from Alpha Vantage API for SPY/SPX gamma exposure calculations.
Optimized for entry premium tier rate limits (75 calls/min) with intelligent caching.
"""

import datetime
import logging
import os
import sys
from collections import deque

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config_loader import ConfigLoader

from gex_db_infrastructure.cache import SQLiteOptionsManager, UnifiedCacheManager
from src.utils.config_manager import get_config
from src.utils.date_utils import get_default_timezone, get_processed_date_range, localize_df


class AlphaVantageGEXClient:
    """Alpha Vantage client specialized for GEX calculation data needs.

    Focuses on:
    - SPY/SPX options chains (historical and current)
    - Underlying stock price data
    - Rate limiting for free tier (75 calls/min)
    - Intelligent caching for historical data
    """

    def __init__(self, cache_manager=None, options_manager=None):
        """Initialize Alpha Vantage client.

        Args:
            cache_manager: Optional cache manager for market data (default: UnifiedCacheManager)
            options_manager: Optional options storage manager (default: SQLiteOptionsManager)
                           Can be SQLiteOptionsManager or PostgreSQLOptionsManager for
                           consistent data source across the application.
        """
        # Load configuration from centralized config system
        config = get_config()

        # Load premium API key from @config/ loader
        config_loader = ConfigLoader()
        self.api_key = os.getenv("ALPHA_VANTAGE_PREMO_KEY", config_loader.get("ALPHA_VANTAGE_PREMO_KEY"))

        # Fallback to regular key if premium not available
        if not self.api_key:
            self.api_key = os.getenv("ALPHA_VANTAGE_KEY", config_loader.get("ALPHA_VANTAGE_KEY"))

        if not self.api_key:
            logging.warning("Alpha Vantage API key not found in @config/ loader.")
        else:
            key_type = (
                "Premium"
                if "PREMO" in str(self.api_key) or self.api_key == config_loader.get("ALPHA_VANTAGE_PREMO_KEY")
                else "Standard"
            )
            logging.info(f"Alpha Vantage {key_type} API key configured")

        self.base_url = "https://www.alphavantage.co/query"
        self.logger = logging.getLogger(self.__class__.__name__)

        # Options storage manager via dependency injection (Issue #169 architectural fix)
        # Accepts SQLiteOptionsManager or PostgreSQLOptionsManager for consistent data source
        self.options_manager = options_manager or SQLiteOptionsManager()
        # Backward compatibility alias
        self.sqlite_options = self.options_manager
        # Legacy cache for non-options data (market data)
        self.cache = cache_manager or UnifiedCacheManager()

        # Load request timeout from config
        self.request_timeout = config.get("data_sources.alpha_vantage.request_timeout", 30)

        # Rate limiting - premium tier has higher limits (configurable)
        # Use deque with maxlen for O(1) rate limiting instead of O(n) list scan
        premium_key = config_loader.get("ALPHA_VANTAGE_PREMO_KEY")
        default_calls_per_minute = config.get("data_sources.alpha_vantage.calls_per_minute", 75)
        if self.api_key == premium_key:
            self.calls_per_minute = 1000  # Premium tier limit (fixed)
            logging.info("Using premium tier rate limits (1000/min)")
        else:
            self.calls_per_minute = default_calls_per_minute  # Standard tier limit from config
            logging.info(f"Using standard tier rate limits ({self.calls_per_minute}/min)")
        # deque with maxlen auto-evicts oldest entries - O(1) operations
        self.call_timestamps = deque(maxlen=self.calls_per_minute)

    def _check_rate_limit(self) -> bool:
        """Check if we're within API rate limits (premium or standard tier).

        Uses deque with maxlen for O(1) rate limiting instead of O(n) list scan.
        """
        now = datetime.datetime.now()
        one_minute_ago = now - datetime.timedelta(minutes=1)

        # Remove old timestamps from front (they're in chronological order)
        while self.call_timestamps and self.call_timestamps[0] < one_minute_ago:
            self.call_timestamps.popleft()

        if len(self.call_timestamps) >= self.calls_per_minute:
            self.logger.warning("Rate limit approached, caching is critical")
            return False

        self.call_timestamps.append(now)
        return True

    def fetch_historical_options(self, symbol, date=None, datatype="json", cache_result=True):
        """Fetch full historical options chain for a specific trading date.

        Args:
            symbol: Underlying symbol (SPY, SPX, IBM, etc.)
            date: Trading date (YYYY-MM-DD). If None, uses previous trading day
            datatype: Response format ('json' or 'csv')
            cache_result: Whether to cache result (False when caller handles storage)

        Returns:
            DataFrame with complete options chain for the trading date

        Note:
            - Returns ALL expirations available for the trading date
            - Covers 15+ years of history (since 2008-01-01)
            - Requires Alpha Vantage Premium for full functionality
        """
        if not self._check_rate_limit():
            self.logger.warning("Rate limit exceeded, using cached data only")
            return pd.DataFrame()

        # Create cache key - use 'latest' if no date specified
        cache_date = date or "latest"
        cache_key = f"options_{symbol}_{cache_date}"

        # Check SQLite first (Issue #180: primary storage, critical for rate limits)
        if date:  # Only cache specific dates, not 'latest'
            cached_data = self.sqlite_options.get_options_chain(symbol, date)
            if cached_data is not None and not cached_data.empty:
                self.logger.info(f"Using SQLite options data for {symbol} {date}")
                return cached_data

        try:
            # Build API parameters according to Alpha Vantage docs
            params = {"function": "HISTORICAL_OPTIONS", "symbol": symbol, "apikey": self.api_key}

            # Add optional date parameter
            if date:
                params["date"] = date

            # Add datatype parameter
            if datatype != "json":
                params["datatype"] = datatype

            self.logger.info(
                f"Fetching options data for {symbol}" + (f" on {date}" if date else " (previous trading day)")
            )

            response = requests.get(self.base_url, params=params, timeout=self.request_timeout)

            if response.status_code != 200:
                self.logger.error(f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            # Handle different response formats
            if datatype == "csv":
                # Parse CSV response
                df = self._process_csv_response(response.text, symbol, date)
            else:
                # Parse JSON response
                data = response.json()

                if "Error Message" in data:
                    self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                    return pd.DataFrame()

                if "Note" in data and "rate limit" in data["Note"].lower():
                    self.logger.warning(f"Rate limit warning: {data['Note']}")
                    return pd.DataFrame()

                df = self._process_options_data(data)

            if df.empty:
                self.logger.warning(f"No options data returned for {symbol}" + (f" on {date}" if date else ""))
                return df

            # Store in SQLite (Issue #180: primary storage, only for specific dates)
            if date and cache_result:
                self.sqlite_options.store_options_chain(symbol, date, df)

            self.logger.info(f"Successfully fetched {len(df)} option contracts")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching historical options: {e}")
            return pd.DataFrame()

    def fetch_underlying_data(self, symbol, start_date, end_date):
        """Fetch underlying stock data for GEX calculations.

        Args:
            symbol: Stock symbol (SPY, SPX)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        if not self._check_rate_limit():
            cached_only = self.cache.get_market_data(symbol, start_date, end_date)
            if cached_only is not None:
                return cached_only
            else:
                self.logger.error("Rate limit exceeded and no cached data available")
                return pd.DataFrame()

        try:
            # Process date range
            processed_start, processed_end = get_processed_date_range(start_date, end_date)

            # Check cache first
            cached_data = self.cache.get_market_data(symbol, processed_start, processed_end)
            if cached_data is not None:
                self.logger.info(f"Using cached stock data for {symbol}")
                return cached_data

            self.logger.info(f"Fetching stock data for {symbol} from {processed_start} to {processed_end}")

            # Determine outputsize based on whether we need historical data
            end_date_obj = datetime.datetime.strptime(processed_end, "%Y-%m-%d")
            now = datetime.datetime.now()
            days_from_now = (now - end_date_obj).days

            # Use full output if requesting historical data (>30 days old) or large range
            days_range = (
                datetime.datetime.strptime(processed_end, "%Y-%m-%d")
                - datetime.datetime.strptime(processed_start, "%Y-%m-%d")
            ).days
            use_full = days_from_now > 30 or days_range > 100

            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "full" if use_full else "compact",
                "datatype": "json",
            }

            response = requests.get(self.base_url, params=params)

            if response.status_code != 200:
                self.logger.error(f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()

            if "Error Message" in data:
                self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            if "Time Series (Daily)" not in data:
                self.logger.warning(f"No time series data found for {symbol}")
                return pd.DataFrame()

            time_series = data["Time Series (Daily)"]
            df = pd.DataFrame.from_dict(time_series, orient="index")

            # Standardize column names for GEX calculations
            df = df.rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                    "5. volume": "volume",
                }
            )

            # Convert to proper types
            df.index = pd.to_datetime(df.index)
            for col in df.columns:
                df[col] = pd.to_numeric(df[col])

            # Filter by date range
            df = df[(df.index >= processed_start) & (df.index <= processed_end)]
            df = df.sort_index(ascending=False)

            # Localize timezone - Alpha Vantage dates are already in ET, not UTC
            # Do NOT use localize_df as it treats dates as UTC first, which shifts dates by one day
            if df.index.tz is None:
                df.index = df.index.tz_localize(get_default_timezone())

            # Cache for future use (critical for rate limits)
            self.cache.store_market_data(symbol, df, processed_start, processed_end)

            return df

        except Exception as e:
            self.logger.error(f"Error fetching underlying data: {e}")
            return pd.DataFrame()

    def _process_csv_response(self, csv_text, symbol, date):
        """Process CSV response from Alpha Vantage Historical Options API.

        Args:
            csv_text: Raw CSV response text
            symbol: Symbol for logging
            date: Date for logging

        Returns:
            DataFrame with processed options data
        """
        try:
            import io

            # Parse CSV into DataFrame
            df = pd.read_csv(io.StringIO(csv_text))

            if df.empty:
                self.logger.warning(f"Empty CSV response for {symbol}")
                return df

            # CSV format should match JSON structure, so process similarly
            # Convert column names to match expected format if needed
            df = self._standardize_csv_columns(df)

            # Apply same processing as JSON data
            processed_df = self._apply_standard_processing(df)

            return processed_df

        except Exception as e:
            self.logger.error(f"Error processing CSV response: {e}")
            return pd.DataFrame()

    def _standardize_csv_columns(self, df):
        """Standardize CSV column names to match JSON format."""
        # CSV might have different column naming - adjust as needed
        # This will be refined once we see actual CSV format
        return df

    def _process_options_data(self, raw_data):
        """Process raw options data into standardized format for GEX calculations.

        Args:
            raw_data: Raw API response data from Historical Options endpoint

        Returns:
            DataFrame with options chain data organized by strike
        """
        if "data" not in raw_data:
            self.logger.warning("No 'data' field in options API response")
            return pd.DataFrame()

        options_data = raw_data["data"]
        if not options_data:
            self.logger.warning("Empty options data in API response")
            return pd.DataFrame()

        try:
            # Convert to DataFrame
            df = pd.DataFrame(options_data)
            return self._apply_standard_processing(df)

        except Exception as e:
            self.logger.error(f"Error processing options data: {e}")
            return pd.DataFrame()

    def _apply_standard_processing(self, df):
        """Apply standard processing to options DataFrame (shared by JSON and CSV).

        Args:
            df: Raw options DataFrame

        Returns:
            Processed DataFrame with derived fields
        """
        try:
            if df.empty:
                return df

            # Convert numeric columns
            numeric_columns = [
                "strike",
                "last",
                "mark",
                "bid",
                "ask",
                "bid_size",
                "ask_size",
                "volume",
                "open_interest",
                "implied_volatility",
                "delta",
                "gamma",
                "theta",
                "vega",
                "rho",
            ]

            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # Convert dates
            if "expiration" in df.columns:
                df["expiration"] = pd.to_datetime(df["expiration"])
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])

            # Add derived columns for GEX analysis
            df["mid_price"] = (df["bid"] + df["ask"]) / 2
            df["bid_ask_spread"] = df["ask"] - df["bid"]
            df["bid_ask_spread_pct"] = df["bid_ask_spread"] / df["mid_price"] * 100

            # Volume-to-OI ratios (useful for detecting unusual activity)
            df["vol_oi_ratio"] = df["volume"] / (df["open_interest"] + 1)  # +1 to avoid div by zero

            # Sort by expiration, then by strike
            df = df.sort_values(["expiration", "strike"])

            self.logger.info(f"Processed {len(df)} option contracts")
            return df

        except Exception as e:
            self.logger.error(f"Error in standard processing: {e}")
            return pd.DataFrame()

    def get_rate_limit_status(self):
        """Get current rate limit status."""
        now = datetime.datetime.now()
        one_minute_ago = now - datetime.timedelta(minutes=1)

        # Count recent calls (deque is already bounded, just filter by time)
        recent_calls = sum(1 for ts in self.call_timestamps if ts >= one_minute_ago)

        return {
            "calls_last_minute": recent_calls,
            "calls_remaining": max(0, self.calls_per_minute - recent_calls),
            "reset_time": now + datetime.timedelta(minutes=1) if recent_calls > 0 else now,
        }

    def fetch_underlying_price(self, symbol: str, date: str) -> float:
        """Fetch the closing price for a specific date.

        Uses cached data when available to avoid extra API calls.

        Args:
            symbol: Stock symbol (SPY, QQQ, TQQQ, etc.)
            date: Date in YYYY-MM-DD format

        Returns:
            Closing price as float, or None if not available
        """
        try:
            # Try to get from cache first (no API call)
            cached_data = self.cache.get_market_data(symbol, date, date)
            if cached_data is not None and not cached_data.empty:
                # Find the exact date in the cached data
                if hasattr(cached_data.index, "strftime"):
                    date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
                    for idx in cached_data.index:
                        if idx.strftime("%Y-%m-%d") == date_str:
                            return float(cached_data.loc[idx, "close"])
                elif date in cached_data.index:
                    return float(cached_data.loc[date, "close"])

            # Fetch from API - use a small range to get the specific date
            # This makes one API call but gets cached for future use
            df = self.fetch_underlying_data(symbol, date, date)

            if df is not None and not df.empty:
                # Return the close price
                if "close" in df.columns:
                    return float(df["close"].iloc[0])

            return None

        except Exception as e:
            self.logger.warning(f"Could not fetch underlying price for {symbol} on {date}: {e}")
            return None
