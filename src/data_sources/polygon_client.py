"""Polygon.io REST API client for stock data.

Free tier provides daily stock data with 5 calls/minute limit.
"""

import datetime
import logging
import time

import pandas as pd
import requests

from src.utils.config_manager import get_config


class PolygonClient:
    """Client for Polygon.io REST API - focused on daily stock data."""

    def __init__(self, api_key: str = None):
        """Initialize client with API key."""
        import json
        import os
        from pathlib import Path

        # Try to load from config if not provided
        if not api_key:
            try:
                config_path = Path(__file__).parent.parent.parent / "config" / "config.json"
                if config_path.exists():
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    api_key = config.get("POLYGON_IO")
            except Exception:
                pass

        self.api_key = api_key or os.getenv("POLYGON_IO", "your_polygon_api_key")
        self.base_url = "https://api.polygon.io/v2"
        self.logger = logging.getLogger(self.__class__.__name__)

        # Rate limiting - Load from config
        config = get_config()
        self.requests_per_minute = config.get("data_source.polygon_client.requests_per_minute", 5)
        self.rate_limit_timeout = config.get("data_source.polygon_client.rate_limit_timeout", 60)
        self.last_request_times = []

    def _rate_limit(self):
        """Simple rate limiting for free tier."""
        now = time.time()

        # Remove requests older than rate limit timeout
        self.last_request_times = [t for t in self.last_request_times if now - t < self.rate_limit_timeout]

        # If we're at the limit, wait
        if len(self.last_request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.last_request_times[0])
            if sleep_time > 0:
                self.logger.info(f"Rate limiting: waiting {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self.last_request_times.append(now)

    def fetch_daily_bars(self, symbol, start_date, end_date):
        """Fetch daily OHLCV data for a symbol.

        Args:
            symbol: Stock symbol (e.g., SPY)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            self._rate_limit()

            url = f"{self.base_url}/aggs/ticker/{symbol.upper()}/range/1/day/{start_date}/{end_date}"
            params = {"apiKey": self.api_key, "adjusted": "true", "sort": "asc"}  # Note: capital K in apiKey

            self.logger.info(f"Fetching {symbol} daily data: {start_date} to {end_date}")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 403:
                self.logger.error("Authentication failed - check your Polygon API key")
                return None
            elif response.status_code == 429:
                self.logger.error("Rate limit exceeded - waiting before retry")
                time.sleep(60)
                return self.fetch_daily_bars(symbol, start_date, end_date)
            elif response.status_code != 200:
                self.logger.error(f"API error {response.status_code}: {response.text}")
                return None

            data = response.json()

            # Accept both OK and DELAYED status (DELAYED = 15-min delayed data for free tier)
            if data.get("status") not in ["OK", "DELAYED"]:
                self.logger.warning(f"API returned unexpected status: {data.get('status')}")
                return None

            results = data.get("results", [])
            if not results:
                self.logger.warning(f"No data returned for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(results)

            # Convert timestamp to datetime
            df["date"] = pd.to_datetime(df["t"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("America/New_York")
            df = df.set_index("date")

            # Rename columns to standard format (lowercase for cache compatibility)
            df = df.rename(
                columns={
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                    "vw": "vwap",
                    "n": "transactions",
                }
            )

            # Select relevant columns
            df = df[["open", "high", "low", "close", "volume"]]

            self.logger.info(f"Successfully fetched {len(df)} days for {symbol}")
            return df

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None

    def fetch_recent_data(self, symbol, days: int = 30):
        """Fetch recent daily data for a symbol.

        Args:
            symbol: Stock symbol
            days: Number of days to fetch

        Returns:
            DataFrame with recent OHLCV data
        """
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)

        return self.fetch_daily_bars(symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    def test_connection(self) -> bool:
        """Test API connection with a simple request."""
        try:
            self._rate_limit()

            # Get recent SPY data as test
            yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            url = f"{self.base_url}/aggs/ticker/SPY/range/1/day/{yesterday}/{yesterday}"

            response = requests.get(url, params={"apiKey": self.api_key}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK":
                    self.logger.info("✅ Polygon API connection successful")
                    return True

            self.logger.error(f"Connection test failed: {response.status_code}")
            return False

        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return False
