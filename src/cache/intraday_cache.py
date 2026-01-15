"""Intraday Cache Manager Extends UnifiedCacheManager with timestamp-based storage for 10-minute intervals.

Structure:
.cache/
├── intraday_options/SPY/2024-01-17/
│   ├── 0930.json    # 9:30 AM market open
│   ├── 0940.json    # 9:40 AM
│   ├── 1000.json    # 10:00 AM algo time
│   ├── 1430.json    # 2:30 PM FOMC time
│   ├── 1530.json    # 3:30 PM gamma time
│   ├── 1540.json    # 3:40 PM gamma time
│   ├── 1550.json    # 3:50 PM gamma time
│   └── 1615.json    # 4:15 PM extended close
├── intraday_gex/SPY/2024-01-17/
│   └── [same structure]
└── intraday_market/SPY/2024-01-17/
    └── [same structure]
"""

import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml

from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from src.utils.date_utils import get_market_close_time, get_market_open_time, parse_date_string

logger = logging.getLogger(__name__)


class IntradayCacheManager(UnifiedCacheManager):
    """Intraday cache manager with timestamp-based storage."""

    def __init__(self, base_dir=".cache"):
        """Initialize intraday cache manager."""
        super().__init__(base_dir)

        # Intraday directories (created lazily when needed)
        self.intraday_options_dir = self.base_dir / "intraday_options"
        self.intraday_gex_dir = self.base_dir / "intraday_gex"
        self.intraday_market_dir = self.base_dir / "intraday_market"

        # Load intraday configuration
        self.intraday_config = self._load_intraday_config()

        # Build algo times from config + 10-minute intervals
        self.algo_times = self._build_algo_times()

    def _load_intraday_config(self) -> Dict:
        """Load intraday configuration from analysis_config.yaml."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config_defaults" / "analysis_config.yaml"
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("intraday_analysis", {})
        except Exception as e:
            logger.warning(f"Failed to load intraday config: {e}. Using defaults.")
            return {
                "algo_times": {
                    "market_open": "09:30:00",
                    "algo_10am": "10:00:00",
                    "fomc_230pm": "14:30:00",
                    "gamma_330pm": "15:30:00",
                    "gamma_340pm": "15:40:00",
                    "gamma_350pm": "15:50:00",
                    "market_close": "16:00:00",
                    "extended_close": "16:15:00",
                },
                "data_intervals": {"standard_interval": 10},
            }

    def _build_algo_times(self) -> List[time]:
        """Build algo times from config plus 10-minute intervals."""
        algo_times = []

        # Get key algo times from config
        config_times = self.intraday_config.get("algo_times", {})
        key_times_str = list(config_times.values())

        # Get interval from config
        interval = self.intraday_config.get("data_intervals", {}).get("standard_interval", 10)

        # Build 10-minute intervals from market open to extended close
        start_time = time(9, 30)  # Market open
        end_time = time(16, 15)  # Extended close

        current_hour, current_min = start_time.hour, start_time.minute
        end_hour, end_min = end_time.hour, end_time.minute

        while (current_hour < end_hour) or (current_hour == end_hour and current_min <= end_min):
            algo_times.append(time(current_hour, current_min))

            # Add interval minutes
            current_min += interval
            if current_min >= 60:
                current_hour += 1
                current_min -= 60

        return algo_times

    def _get_time_filename(self, timestamp: str) -> str:
        """Convert timestamp to filename format."""
        try:
            dt = parse_date_string(timestamp)
            return dt.strftime("%H%M")  # HHMM format
        except Exception:
            # Fallback to basic format
            return timestamp.split(" ")[1].replace(":", "")[:4] if " " in timestamp else "0000"

    def _get_date_from_timestamp(self, timestamp: str) -> str:
        """Extract date from timestamp."""
        try:
            dt = parse_date_string(timestamp)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return timestamp.split(" ")[0] if " " in timestamp else timestamp

    def _is_market_hours(self, timestamp: str) -> Tuple[bool, str]:
        """Check if timestamp is during market hours and return session type."""
        try:
            dt = parse_date_string(timestamp)
            time_only = dt.time()

            # Regular market hours: 9:30 AM - 4:00 PM ET
            if time(9, 30) <= time_only <= time(16, 0):
                return True, "regular"

            # Extended hours: 4:00 PM - 4:15 PM ET
            elif time(16, 0) < time_only <= time(16, 15):
                return True, "extended"

            else:
                return False, "closed"

        except Exception:
            return False, "unknown"

    def store_intraday_options(self, symbol: str, timestamp: str, data: Dict) -> bool:
        """Store intraday options data.

        Args:
            symbol: Stock symbol
            timestamp: Full timestamp (YYYY-MM-DD HH:MM:SS)
            data: Options data dictionary

        Returns:
            True if stored successfully
        """
        try:
            # Check market hours
            is_market, session = self._is_market_hours(timestamp)
            if not is_market:
                logger.warning(f"Timestamp {timestamp} outside market hours - storing anyway")

            # Create directory structure: symbol/date/
            date_str = self._get_date_from_timestamp(timestamp)
            symbol_date_dir = self.intraday_options_dir / symbol.upper() / date_str
            symbol_date_dir.mkdir(parents=True, exist_ok=True)

            # Create filename: HHMM.json
            time_filename = self._get_time_filename(timestamp)
            file_path = symbol_date_dir / f"{time_filename}.json"

            # Add metadata
            data_with_metadata = {
                "symbol": symbol,
                "timestamp": timestamp,
                "market_session": session,
                "data": data,
                "cached_at": datetime.now().isoformat(),
            }

            # Store as JSON
            with open(file_path, "w") as f:
                json.dump(data_with_metadata, f, indent=2)

            logger.info(f"Stored intraday options for {symbol} at {timestamp}")
            return True

        except Exception as e:
            logger.error(f"Failed to store intraday options: {e}")
            return False

    def get_intraday_options(self, symbol: str, timestamp: str) -> Optional[Dict]:
        """Get intraday options data.

        Args:
            symbol: Stock symbol
            timestamp: Full timestamp (YYYY-MM-DD HH:MM:SS)

        Returns:
            Options data dictionary or None
        """
        try:
            date_str = self._get_date_from_timestamp(timestamp)
            time_filename = self._get_time_filename(timestamp)

            file_path = self.intraday_options_dir / symbol.upper() / date_str / f"{time_filename}.json"

            if file_path.exists():
                with open(file_path, "r") as f:
                    cached_data = json.load(f)

                logger.debug(f"Loaded intraday options for {symbol} at {timestamp}")
                # Handle both formats
                return cached_data.get("data", cached_data)

            logger.debug(f"No intraday options data for {symbol} at {timestamp}")
            return None

        except Exception as e:
            logger.error(f"Failed to load intraday options: {e}")
            return None

    def store_intraday_gex(self, symbol: str, timestamp: str, gex_data: Dict) -> bool:
        """Store intraday GEX data."""
        try:
            date_str = self._get_date_from_timestamp(timestamp)
            symbol_date_dir = self.intraday_gex_dir / symbol.upper() / date_str
            symbol_date_dir.mkdir(parents=True, exist_ok=True)

            time_filename = self._get_time_filename(timestamp)
            file_path = symbol_date_dir / f"{time_filename}.json"

            # Add metadata
            gex_with_metadata = {
                "symbol": symbol,
                "timestamp": timestamp,
                "market_session": self._is_market_hours(timestamp)[1],
                "gex_data": gex_data,
                "cached_at": datetime.now().isoformat(),
            }

            with open(file_path, "w") as f:
                json.dump(gex_with_metadata, f, indent=2)

            logger.info(f"Stored intraday GEX for {symbol} at {timestamp}")
            return True

        except Exception as e:
            logger.error(f"Failed to store intraday GEX: {e}")
            return False

    def get_intraday_gex(self, symbol: str, timestamp: str) -> Optional[Dict]:
        """Get intraday GEX data."""
        try:
            date_str = self._get_date_from_timestamp(timestamp)
            time_filename = self._get_time_filename(timestamp)

            file_path = self.intraday_gex_dir / symbol.upper() / date_str / f"{time_filename}.json"

            if file_path.exists():
                with open(file_path, "r") as f:
                    cached_data = json.load(f)

                return cached_data.get("gex_data", cached_data)

            return None

        except Exception as e:
            logger.error(f"Failed to load intraday GEX: {e}")
            return None

    def store_intraday_market(self, symbol: str, timestamp: str, market_data: Dict) -> bool:
        """Store intraday market data."""
        try:
            date_str = self._get_date_from_timestamp(timestamp)
            symbol_date_dir = self.intraday_market_dir / symbol.upper() / date_str
            symbol_date_dir.mkdir(parents=True, exist_ok=True)

            time_filename = self._get_time_filename(timestamp)
            file_path = symbol_date_dir / f"{time_filename}.json"

            market_with_metadata = {
                "symbol": symbol,
                "timestamp": timestamp,
                "market_session": self._is_market_hours(timestamp)[1],
                "market_data": market_data,
                "cached_at": datetime.now().isoformat(),
            }

            with open(file_path, "w") as f:
                json.dump(market_with_metadata, f, indent=2)

            logger.info(f"Stored intraday market data for {symbol} at {timestamp}")
            return True

        except Exception as e:
            logger.error(f"Failed to store intraday market data: {e}")
            return False

    def get_intraday_market(self, symbol: str, timestamp: str) -> Optional[Dict]:
        """Get intraday market data."""
        try:
            date_str = self._get_date_from_timestamp(timestamp)
            time_filename = self._get_time_filename(timestamp)

            file_path = self.intraday_market_dir / symbol.upper() / date_str / f"{time_filename}.json"

            if file_path.exists():
                with open(file_path, "r") as f:
                    cached_data = json.load(f)

                return cached_data.get("market_data", cached_data)

            return None

        except Exception as e:
            logger.error(f"Failed to load intraday market data: {e}")
            return None

    def get_available_timestamps(self, symbol: str, date: str) -> List[str]:
        """Get all available timestamps for a symbol and date."""
        timestamps = []

        try:
            # Check all three data types
            for base_dir in [self.intraday_options_dir, self.intraday_gex_dir, self.intraday_market_dir]:
                symbol_date_dir = base_dir / symbol.upper() / date

                if symbol_date_dir.exists():
                    for file_path in symbol_date_dir.glob("*.json"):
                        # Convert filename back to timestamp
                        time_str = file_path.stem  # Remove .json
                        if len(time_str) == 4:  # HHMM format
                            hour = time_str[:2]
                            minute = time_str[2:]
                            timestamp = f"{date} {hour}:{minute}:00"
                            if timestamp not in timestamps:
                                timestamps.append(timestamp)

            timestamps.sort()
            return timestamps

        except Exception as e:
            logger.error(f"Failed to get available timestamps: {e}")
            return []

    def get_friday_algo_times(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """Get all Friday algo time data for gamma pinning analysis."""
        friday_data = []

        try:
            # Generate date range
            from src.utils.date_utils import date_range_trading_days

            trading_days = date_range_trading_days(start_date, end_date)

            for date in trading_days:
                # Check if Friday
                dt = parse_date_string(date)
                if dt.weekday() == 4:  # Friday
                    # Get key algo times for this Friday
                    # Get key algo times from config
                    config_times = self.intraday_config.get("algo_times", {})
                    key_times = list(config_times.values())

                    for time_str in key_times:
                        timestamp = f"{date} {time_str}"

                        # Try to get GEX data
                        gex_data = self.get_intraday_gex(symbol, timestamp)
                        market_data = self.get_intraday_market(symbol, timestamp)

                        if gex_data or market_data:
                            friday_data.append(
                                {
                                    "symbol": symbol,
                                    "date": date,
                                    "timestamp": timestamp,
                                    "time": time_str,
                                    "algo_marker": self._get_algo_marker(time_str),
                                    "gex_data": gex_data,
                                    "market_data": market_data,
                                }
                            )

        except Exception as e:
            logger.error(f"Failed to get Friday algo times: {e}")

        return friday_data

    def _get_algo_marker(self, time_str: str) -> str:
        """Get algo marker for time using config."""
        # Get algo times from config
        config_times = self.intraday_config.get("algo_times", {})

        # Create reverse mapping from time to marker
        time_markers = {}
        for marker, time_val in config_times.items():
            time_markers[time_val] = marker.upper()

        return time_markers.get(time_str, "OTHER")

    def cleanup_old_intraday_data(self, days_to_keep: int = 30) -> int:
        """Clean up old intraday data to manage storage."""
        cleaned_files = 0

        try:
            cutoff_date = datetime.now() - pd.Timedelta(days=days_to_keep)

            for base_dir in [self.intraday_options_dir, self.intraday_gex_dir, self.intraday_market_dir]:
                for symbol_dir in base_dir.iterdir():
                    if symbol_dir.is_dir():
                        for date_dir in symbol_dir.iterdir():
                            if date_dir.is_dir():
                                try:
                                    date_dt = datetime.strptime(date_dir.name, "%Y-%m-%d")
                                    if date_dt < cutoff_date:
                                        # Remove entire date directory
                                        import shutil

                                        shutil.rmtree(date_dir)
                                        cleaned_files += 1
                                        logger.info(f"Cleaned up old data: {date_dir}")
                                except ValueError:
                                    # Skip invalid date directories
                                    continue

            logger.info(f"Cleaned up {cleaned_files} old intraday data directories")
            return cleaned_files

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
