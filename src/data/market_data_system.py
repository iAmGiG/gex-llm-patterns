"""
Market Data System - Unified Data Access Architecture
Provides unified access to daily and intraday market data with intelligent fallback.

Architecture:
- Tier 1: Database (SQLite) - Fastest access for stored data
- Tier 2: Cache (Unified/Intraday) - Fallback for recent data
- No sample data fallback - warns user when data unavailable

Supports:
- Daily queries: fetch_market_data(date, symbol)
- Intraday queries: fetch_market_data(timestamp, symbol) with auto-detection
- Flexible algo time analysis: get_algo_time_data() with parameterizable times
- SPY/QQQ daily 0DTE vs regular ticker Friday-only expiration patterns
- Performance tracking and statistics
"""

import json
import os
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from gex_db_infrastructure.cache.intraday_cache import IntradayCacheManager
from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager

logger = logging.getLogger(__name__)


class UnifiedDataSystem:
    """Unified 2-tier data system supporting both daily and intraday queries.

    Features:
    - Automatic detection of daily vs intraday queries
    - Seamless fallback between database and cache
    - Performance tracking and optimization
    - No sample data - warns user when data unavailable
    """

    def __init__(self, db_path: str = ".cache/consolidated_historical.db"):
        """Initialize unified data system.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.sqlite_options = SQLiteOptionsManager()  # Issue #180: Primary options storage
        self.cache_manager = UnifiedCacheManager()  # For non-options data (market data)
        self.intraday_cache = IntradayCacheManager()

        # Performance tracking
        self.tier_stats = {
            # Daily stats
            "daily_tier1_hits": 0,
            "daily_tier2_hits": 0,
            "daily_misses": 0,
            "daily_requests": 0,
            # Intraday stats
            "intraday_tier1_hits": 0,
            "intraday_tier2_hits": 0,
            "intraday_misses": 0,
            "intraday_requests": 0,
            # Total stats
            "total_requests": 0,
        }

        logger.info(f"Initialized UnifiedDataSystem with database: {self.db_path}")

    def fetch_options_data(self, date_or_timestamp: str, symbol: str = "SPY") -> Optional[Dict]:
        """Fetch options data with automatic daily/intraday detection.

        Args:
            date_or_timestamp: Either YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
            symbol: Trading symbol

        Returns:
            Options data dictionary or None
        """
        self.tier_stats["total_requests"] += 1

        # Detect if this is intraday or daily
        if self._is_intraday(date_or_timestamp):
            return self._fetch_intraday_options(date_or_timestamp, symbol)
        else:
            return self._fetch_daily_options(date_or_timestamp, symbol)

    def fetch_market_data(self, date_or_timestamp: str, symbol: str = "SPY") -> Optional[Dict]:
        """Fetch market data with automatic daily/intraday detection.

        Args:
            date_or_timestamp: Either YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
            symbol: Trading symbol

        Returns:
            Market data dictionary or None
        """
        self.tier_stats["total_requests"] += 1

        # Detect if this is intraday or daily
        if self._is_intraday(date_or_timestamp):
            return self._fetch_intraday_market(date_or_timestamp, symbol)
        else:
            return self._fetch_daily_market(date_or_timestamp, symbol)

    def fetch_gex_data(self, date_or_timestamp: str, symbol: str = "SPY") -> Optional[Dict]:
        """Fetch GEX data with automatic daily/intraday detection.

        Args:
            date_or_timestamp: Either YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
            symbol: Trading symbol

        Returns:
            GEX data dictionary or None
        """
        self.tier_stats["total_requests"] += 1

        # Detect if this is intraday or daily
        if self._is_intraday(date_or_timestamp):
            return self._fetch_intraday_gex(date_or_timestamp, symbol)
        else:
            return self._fetch_daily_gex(date_or_timestamp, symbol)

    # ============= Daily Data Methods =============

    def _fetch_daily_options(self, date: str, symbol: str) -> Optional[Dict]:
        """Fetch daily options data through 2-tier system."""
        self.tier_stats["daily_requests"] += 1

        # Tier 1: Database
        data = self._query_database(date, symbol, "options", is_intraday=False)
        if data:
            self.tier_stats["daily_tier1_hits"] += 1
            logger.debug(f"Database hit: {symbol} daily options for {date}")
            return data

        # Tier 2: SQLite options manager (Issue #180: primary options storage)
        cache_data = self.sqlite_options.get_options_chain(symbol, date)
        data = self._convert_cache_result(cache_data)
        if data:
            self.tier_stats["daily_tier2_hits"] += 1
            logger.debug(f"Cache hit: {symbol} daily options for {date}")
            # Store in database for future
            self._store_in_database(date, symbol, data, "options", is_intraday=False)
            return data

        # No data available
        self.tier_stats["daily_misses"] += 1
        logger.warning(f"⚠️  No daily options data available for {symbol} on {date}")
        return None

    def _fetch_daily_market(self, date: str, symbol: str) -> Optional[Dict]:
        """Fetch daily market data through 2-tier system."""
        self.tier_stats["daily_requests"] += 1

        # Tier 1: Database
        data = self._query_database(date, symbol, "market", is_intraday=False)
        if data:
            self.tier_stats["daily_tier1_hits"] += 1
            return data

        # Tier 2: Cache
        cache_data = self.cache_manager.get_market_data(symbol, date, date)
        data = self._convert_cache_result(cache_data, single_record=True)
        if data:
            self.tier_stats["daily_tier2_hits"] += 1
            self._store_in_database(date, symbol, data, "market", is_intraday=False)
            return data

        self.tier_stats["daily_misses"] += 1
        logger.warning(f"⚠️  No daily market data available for {symbol} on {date}")
        return None

    def _fetch_daily_gex(self, date: str, symbol: str) -> Optional[Dict]:
        """Fetch daily GEX data through 2-tier system."""
        self.tier_stats["daily_requests"] += 1

        # Tier 1: Database
        data = self._query_database(date, symbol, "gex", is_intraday=False)
        if data:
            self.tier_stats["daily_tier1_hits"] += 1
            return data

        # Tier 2: Cache
        cache_data = self.cache_manager.get_or_calculate_gex(symbol, date)
        # GEX data might already be a dict, handle both cases
        if isinstance(cache_data, dict):
            data = cache_data
        else:
            data = self._convert_cache_result(cache_data, single_record=True)

        if data:
            self.tier_stats["daily_tier2_hits"] += 1
            self._store_in_database(date, symbol, data, "gex", is_intraday=False)
            return data

        self.tier_stats["daily_misses"] += 1
        logger.warning(f"⚠️  No daily GEX data available for {symbol} on {date}")
        return None

    # ============= Intraday Data Methods =============

    def _fetch_intraday_options(self, timestamp: str, symbol: str) -> Optional[Dict]:
        """Fetch intraday options data through 2-tier system."""
        self.tier_stats["intraday_requests"] += 1

        # Tier 1: Database
        data = self._query_database(timestamp, symbol, "options", is_intraday=True)
        if data:
            self.tier_stats["intraday_tier1_hits"] += 1
            logger.debug(f"Database hit: {symbol} intraday options at {timestamp}")
            return data

        # Tier 2: Intraday Cache
        data = self.intraday_cache.get_intraday_options(symbol, timestamp)
        if data:
            self.tier_stats["intraday_tier2_hits"] += 1
            logger.debug(f"Cache hit: {symbol} intraday options at {timestamp}")
            self._store_in_database(timestamp, symbol, data, "options", is_intraday=True)
            return data

        # Fallback: Try daily data for same date
        date = timestamp.split(" ")[0]
        daily_data = self._fetch_daily_options(date, symbol)
        if daily_data:
            # Add timestamp info to indicate this is interpolated
            if isinstance(daily_data, list) and len(daily_data) > 0:
                # If it's a list of records, wrap it in a dict
                result = {"timestamp": timestamp, "interpolated_from_daily": True, "options_data": daily_data}
                return result
            elif isinstance(daily_data, dict):
                daily_data["timestamp"] = timestamp
                daily_data["interpolated_from_daily"] = True
                return daily_data

        self.tier_stats["intraday_misses"] += 1
        logger.warning(f"⚠️  No intraday options data available for {symbol} at {timestamp}")
        return None

    def _fetch_intraday_market(self, timestamp: str, symbol: str) -> Optional[Dict]:
        """Fetch intraday market data through 2-tier system."""
        self.tier_stats["intraday_requests"] += 1

        # Tier 1: Database
        data = self._query_database(timestamp, symbol, "market", is_intraday=True)
        if data:
            self.tier_stats["intraday_tier1_hits"] += 1
            return data

        # Tier 2: Intraday Cache
        data = self.intraday_cache.get_intraday_market(symbol, timestamp)
        if data:
            self.tier_stats["intraday_tier2_hits"] += 1
            self._store_in_database(timestamp, symbol, data, "market", is_intraday=True)
            return data

        # Fallback: Try daily data
        date = timestamp.split(" ")[0]
        daily_data = self._fetch_daily_market(date, symbol)
        if daily_data and isinstance(daily_data, dict):
            daily_data["timestamp"] = timestamp
            daily_data["interpolated_from_daily"] = True
            return daily_data

        self.tier_stats["intraday_misses"] += 1
        logger.warning(f"⚠️  No intraday market data available for {symbol} at {timestamp}")
        return None

    def _fetch_intraday_gex(self, timestamp: str, symbol: str) -> Optional[Dict]:
        """Fetch intraday GEX data through 2-tier system."""
        self.tier_stats["intraday_requests"] += 1

        # Tier 1: Database
        data = self._query_database(timestamp, symbol, "gex", is_intraday=True)
        if data:
            self.tier_stats["intraday_tier1_hits"] += 1
            return data

        # Tier 2: Intraday Cache
        data = self.intraday_cache.get_intraday_gex(symbol, timestamp)
        if data:
            self.tier_stats["intraday_tier2_hits"] += 1
            self._store_in_database(timestamp, symbol, data, "gex", is_intraday=True)
            return data

        # Fallback: Try daily data
        date = timestamp.split(" ")[0]
        daily_data = self._fetch_daily_gex(date, symbol)
        if daily_data and isinstance(daily_data, dict):
            daily_data["timestamp"] = timestamp
            daily_data["interpolated_from_daily"] = True
            return daily_data

        self.tier_stats["intraday_misses"] += 1
        logger.warning(f"⚠️  No intraday GEX data available for {symbol} at {timestamp}")
        return None

    # ============= Database Operations =============

    def _query_database(self, date_or_timestamp: str, symbol: str, data_type: str, is_intraday: bool) -> Optional[Dict]:
        """Query database for data.

        Args:
            date_or_timestamp: Date or timestamp string
            symbol: Trading symbol
            data_type: 'options', 'market', or 'gex'
            is_intraday: Whether this is an intraday query

        Returns:
            Data dictionary or None
        """
        if not self.db_path.exists():
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                if is_intraday:
                    return self._query_intraday_database(conn, date_or_timestamp, symbol, data_type)
                else:
                    return self._query_daily_database(conn, date_or_timestamp, symbol, data_type)

        except Exception as e:
            logger.debug(f"Database query failed: {e}")
            return None

    def _query_daily_database(self, conn, date: str, symbol: str, data_type: str) -> Optional[Dict]:
        """Query daily data from database."""
        if data_type == "options":
            query = "SELECT data FROM options_data WHERE date = ? AND symbol = ?"
            cursor = conn.execute(query, (date, symbol))
            row = cursor.fetchone()
            return json.loads(row["data"]) if row and row["data"] else None

        elif data_type == "market":
            query = "SELECT close, volume, high, low, open FROM market_data WHERE date = ? AND symbol = ?"
            cursor = conn.execute(query, (date, symbol))
            row = cursor.fetchone()
            return dict(row) if row else None

        elif data_type == "gex":
            query = "SELECT net_gex, gex_regime, gamma_flip, data FROM gex_data WHERE date = ? AND symbol = ?"
            cursor = conn.execute(query, (date, symbol))
            row = cursor.fetchone()
            if row:
                gex_dict = dict(row)
                if row["data"]:
                    gex_dict.update(json.loads(row["data"]))
                return gex_dict
        return None

    def _query_intraday_database(self, conn, timestamp: str, symbol: str, data_type: str) -> Optional[Dict]:
        """Query intraday data from database."""
        if data_type == "gex":
            query = """
            SELECT timestamp, spot_price, total_gex, net_call_gex, net_put_gex,
                   gamma_flip_point, gex_regime, market_session
            FROM intraday_gex_metrics
            WHERE timestamp = ? AND symbol = ?
            """
            cursor = conn.execute(query, (timestamp, symbol))
            row = cursor.fetchone()
            return dict(row) if row else None

        elif data_type == "market":
            # Try intraday_market_data table if it exists
            query = """
            SELECT timestamp, open, high, low, close, volume
            FROM intraday_market_data
            WHERE timestamp = ? AND symbol = ?
            """
            try:
                cursor = conn.execute(query, (timestamp, symbol))
                row = cursor.fetchone()
                return dict(row) if row else None
            except sqlite3.Error as e:
                logger.debug(f"Intraday market query failed: {e}")
                return None

        elif data_type == "options":
            # Options data is complex - would need specialized storage
            return None

    def _store_in_database(self, date_or_timestamp: str, symbol: str, data: Dict, data_type: str, is_intraday: bool):
        """Store data in database for future Tier 1 access.

        Args:
            date_or_timestamp: Date or timestamp string
            symbol: Trading symbol
            data: Data dictionary to store
            data_type: 'options', 'market', or 'gex'
            is_intraday: Whether this is intraday data
        """
        if not data:
            return

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                if is_intraday:
                    self._store_intraday_database(conn, date_or_timestamp, symbol, data, data_type)
                else:
                    self._store_daily_database(conn, date_or_timestamp, symbol, data, data_type)

                conn.commit()

        except Exception as e:
            logger.warning(f"Failed to store {data_type} data in database: {e}")

    def _store_daily_database(self, conn, date: str, symbol: str, data: Dict, data_type: str):
        """Store daily data in database."""
        if data_type == "options":
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS options_data (
                date TEXT, symbol TEXT, data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            )"""
            )
            # Convert timestamps to strings for JSON serialization
            serializable_data = self._make_json_serializable(data)
            conn.execute(
                "INSERT OR REPLACE INTO options_data (date, symbol, data) VALUES (?, ?, ?)",
                (date, symbol, json.dumps(serializable_data)),
            )

        elif data_type == "market":
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS market_data (
                date TEXT, symbol TEXT, close REAL, volume INTEGER, high REAL, low REAL, open REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            )"""
            )
            conn.execute(
                """INSERT OR REPLACE INTO market_data
                       (date, symbol, close, volume, high, low, open) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    date,
                    symbol,
                    data.get("close"),
                    data.get("volume"),
                    data.get("high"),
                    data.get("low"),
                    data.get("open"),
                ),
            )

        elif data_type == "gex":
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS gex_data (
                date TEXT, symbol TEXT, net_gex REAL, gex_regime TEXT, gamma_flip REAL, data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, symbol)
            )"""
            )
            additional_data = {
                k: v for k, v in data.items() if k not in ["net_gex", "gex_regime", "gamma_flip", "date", "symbol"]
            }
            conn.execute(
                """INSERT OR REPLACE INTO gex_data
                       (date, symbol, net_gex, gex_regime, gamma_flip, data) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    date,
                    symbol,
                    data.get("net_gex"),
                    data.get("gex_regime"),
                    data.get("gamma_flip"),
                    json.dumps(additional_data) if additional_data else None,
                ),
            )

    def _store_intraday_database(self, conn, timestamp: str, symbol: str, data: Dict, data_type: str):
        """Store intraday data in database."""
        if data_type == "gex":
            # Create table if needed
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS intraday_gex_metrics (
                symbol TEXT, timestamp TEXT, spot_price REAL, total_gex REAL,
                net_call_gex REAL, net_put_gex REAL, gamma_flip_point REAL,
                gex_regime TEXT, market_session TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timestamp)
            )"""
            )

            conn.execute(
                """
            INSERT OR REPLACE INTO intraday_gex_metrics
            (symbol, timestamp, spot_price, total_gex, net_call_gex, net_put_gex,
             gamma_flip_point, gex_regime, market_session)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol,
                    timestamp,
                    data.get("spot_price"),
                    data.get("total_gex"),
                    data.get("net_call_gex"),
                    data.get("net_put_gex"),
                    data.get("gamma_flip_point"),
                    data.get("gex_regime"),
                    data.get("market_session", "regular"),
                ),
            )

            # Store strike details if available
            if "strike_data" in data:
                self._store_strike_details(conn, timestamp, symbol, data["strike_data"])

        elif data_type == "market":
            # Create intraday market table if needed
            conn.execute(
                """
            CREATE TABLE IF NOT EXISTS intraday_market_data (
                symbol TEXT, timestamp TEXT, open REAL, high REAL, low REAL,
                close REAL, volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol, timestamp)
            )"""
            )

            conn.execute(
                """
            INSERT OR REPLACE INTO intraday_market_data
            (symbol, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol,
                    timestamp,
                    data.get("open"),
                    data.get("high"),
                    data.get("low"),
                    data.get("close"),
                    data.get("volume"),
                ),
            )

    def _store_strike_details(self, conn, timestamp: str, symbol: str, strike_data: Dict):
        """Store strike-level details for intraday data."""
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS intraday_strike_details (
            symbol TEXT, timestamp TEXT, strike REAL, call_gex REAL, put_gex REAL,
            net_gex REAL, call_oi INTEGER, put_oi INTEGER, distance_from_spot REAL,
            gamma_concentration REAL,
            PRIMARY KEY (symbol, timestamp, strike)
        )"""
        )

        for strike, details in strike_data.items():
            conn.execute(
                """
            INSERT OR REPLACE INTO intraday_strike_details
            (symbol, timestamp, strike, call_gex, put_gex, net_gex,
             call_oi, put_oi, distance_from_spot, gamma_concentration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol,
                    timestamp,
                    float(strike),
                    details.get("call_gex"),
                    details.get("put_gex"),
                    details.get("net_gex"),
                    details.get("call_oi"),
                    details.get("put_oi"),
                    details.get("distance_from_spot"),
                    details.get("gamma_concentration"),
                ),
            )

    # ============= Utility Methods =============

    def _is_intraday(self, date_or_timestamp: str) -> bool:
        """Determine if input is an intraday timestamp or daily date.

        Args:
            date_or_timestamp: Input string

        Returns:
            True if intraday (contains time), False if daily
        """
        # Check for time component (space and colon indicate timestamp)
        return " " in date_or_timestamp and ":" in date_or_timestamp

    def _convert_cache_result(self, data, single_record: bool = False):
        """Convert cache result (DataFrame or dict) to dictionary.

        Args:
            data: Data from cache (can be DataFrame, dict, or None)
            single_record: If True, return single dict instead of list

        Returns:
            Dictionary, list of dictionaries, or None
        """
        if data is None or (hasattr(data, "empty") and data.empty):
            return None

        # Convert DataFrame to dict
        if hasattr(data, "to_dict"):
            records = data.to_dict("records")
            if single_record and len(records) > 0:
                return records[0]
            return records if len(records) > 0 else None

        return data

    def store_data(
        self,
        date_or_timestamp: str,
        symbol: str,
        options_data: Dict = None,
        market_data: Dict = None,
        gex_data: Dict = None,
    ) -> bool:
        """Store data in the system (both cache and database).

        Args:
            date_or_timestamp: Date or timestamp
            symbol: Trading symbol
            options_data: Options chain data
            market_data: Market OHLCV data
            gex_data: Calculated GEX metrics

        Returns:
            True if all data stored successfully
        """
        success = True
        is_intraday = self._is_intraday(date_or_timestamp)

        if is_intraday:
            # Store in intraday cache
            if options_data:
                success &= self.intraday_cache.store_intraday_options(symbol, date_or_timestamp, options_data)
            if market_data:
                success &= self.intraday_cache.store_intraday_market(symbol, date_or_timestamp, market_data)
            if gex_data:
                success &= self.intraday_cache.store_intraday_gex(symbol, date_or_timestamp, gex_data)
                # Also store in database
                self._store_in_database(date_or_timestamp, symbol, gex_data, "gex", is_intraday=True)
        else:
            # Store in daily cache - UnifiedCacheManager handles its own storage
            if options_data:
                self._store_in_database(date_or_timestamp, symbol, options_data, "options", is_intraday=False)

            if market_data:
                self._store_in_database(date_or_timestamp, symbol, market_data, "market", is_intraday=False)

            if gex_data:
                self._store_in_database(date_or_timestamp, symbol, gex_data, "gex", is_intraday=False)

        return success

    def get_algo_time_data(
        self, start_date: str, end_date: str, symbol: str = "SPY", algo_time: str = "15:30:00", weekday: int = None
    ) -> List[Dict]:
        """Get algo time data for flexible analysis.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            symbol: Trading symbol (SPY/QQQ have 0DTE daily, others Friday only)
            algo_time: Time in HH:MM:SS format (15:30:00, 15:50:00, etc.)
            weekday: Specific weekday (0=Mon, 4=Fri) or None for all days

        Returns:
            List of algo time data points
        """
        algo_data = []

        try:
            # Determine if symbol has daily 0DTE (SPY, QQQ) or Friday only
            has_daily_0dte = symbol.upper() in ["SPY", "QQQ"]

            if has_daily_0dte and weekday is None:
                # SPY/QQQ: Check all weekdays
                algo_data = self._query_algo_time_database(start_date, end_date, symbol, algo_time)
            elif weekday is not None:
                # Specific weekday requested
                algo_data = self._query_algo_time_database(start_date, end_date, symbol, algo_time, weekday)
            else:
                # Regular tickers: Default to Friday only
                algo_data = self._query_algo_time_database(start_date, end_date, symbol, algo_time, weekday=4)

        except Exception as e:
            logger.error(f"Failed to get algo time data: {e}")

        return algo_data

    def get_friday_gamma_data(self, start_date: str, end_date: str, symbol: str = "SPY") -> List[Dict]:
        """Backward compatibility method for Friday 3:30 PM gamma data.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            symbol: Trading symbol

        Returns:
            List of Friday 3:30 PM gamma data points
        """
        return self.get_algo_time_data(start_date, end_date, symbol, "15:30:00", weekday=4)

    def get_algo_time_from_config(self, algo_name: str) -> str:
        """Get algo time from config by name.

        Args:
            algo_name: Name like 'gamma_330pm', 'gamma_350pm', 'market_close'

        Returns:
            Time string in HH:MM:SS format
        """
        from src.utils.config_manager import ConfigManager

        config = ConfigManager()
        algo_times = config.get("intraday_analysis.algo_times", {})

        # Common algo time mappings
        default_times = {
            "market_open": "09:30:00",
            "algo_10am": "10:00:00",
            "fomc_230pm": "14:30:00",
            "gamma_330pm": "15:30:00",
            "gamma_340pm": "15:40:00",
            "gamma_350pm": "15:50:00",
            "market_close": "16:00:00",
            "extended_close": "16:15:00",
        }

        return algo_times.get(algo_name, default_times.get(algo_name, "15:30:00"))

    def _query_algo_time_database(
        self, start_date: str, end_date: str, symbol: str, algo_time: str, weekday: int = None
    ) -> List[Dict]:
        """Query database for algo time data with flexible parameters.

        Args:
            start_date: Start date
            end_date: End date
            symbol: Trading symbol
            algo_time: Time in HH:MM:SS format
            weekday: Specific weekday (0=Mon, 4=Fri) or None for all
        """
        if not self.db_path.exists():
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Build flexible query based on parameters
                base_query = """
                SELECT * FROM intraday_gex_metrics
                WHERE symbol = ?
                  AND DATE(timestamp) BETWEEN ? AND ?
                  AND TIME(timestamp) = ?
                """

                params = [symbol, start_date, end_date, algo_time]

                # Add weekday filter if specified
                if weekday is not None:
                    # Convert Python weekday (0=Mon, 6=Sun) to SQLite %w (0=Sun, 6=Sat)
                    # Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
                    # SQLite: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
                    sqlite_weekday = (weekday + 1) % 7
                    base_query += " AND strftime('%w', timestamp) = ?"
                    params.append(str(sqlite_weekday))

                base_query += " ORDER BY timestamp DESC"

                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Database algo time query failed: {e}")
            return []

    def get_performance_stats(self) -> Dict:
        """Get comprehensive performance statistics.

        Returns:
            Dictionary of performance metrics
        """
        total = self.tier_stats["total_requests"]
        daily_total = self.tier_stats["daily_requests"]
        intraday_total = self.tier_stats["intraday_requests"]

        stats = {
            "total_requests": total,
            "daily_requests": daily_total,
            "intraday_requests": intraday_total,
        }

        # Calculate daily rates
        if daily_total > 0:
            stats["daily_database_hit_rate"] = (self.tier_stats["daily_tier1_hits"] / daily_total) * 100
            stats["daily_cache_hit_rate"] = (self.tier_stats["daily_tier2_hits"] / daily_total) * 100
            stats["daily_miss_rate"] = (self.tier_stats["daily_misses"] / daily_total) * 100
            stats["daily_availability"] = 100 - stats["daily_miss_rate"]
        else:
            stats["daily_database_hit_rate"] = 0
            stats["daily_cache_hit_rate"] = 0
            stats["daily_miss_rate"] = 0
            stats["daily_availability"] = 0

        # Calculate intraday rates
        if intraday_total > 0:
            stats["intraday_database_hit_rate"] = (self.tier_stats["intraday_tier1_hits"] / intraday_total) * 100
            stats["intraday_cache_hit_rate"] = (self.tier_stats["intraday_tier2_hits"] / intraday_total) * 100
            stats["intraday_miss_rate"] = (self.tier_stats["intraday_misses"] / intraday_total) * 100
            stats["intraday_availability"] = 100 - stats["intraday_miss_rate"]
        else:
            stats["intraday_database_hit_rate"] = 0
            stats["intraday_cache_hit_rate"] = 0
            stats["intraday_miss_rate"] = 0
            stats["intraday_availability"] = 0

        # Overall rates
        if total > 0:
            total_hits = (
                self.tier_stats["daily_tier1_hits"]
                + self.tier_stats["daily_tier2_hits"]
                + self.tier_stats["intraday_tier1_hits"]
                + self.tier_stats["intraday_tier2_hits"]
            )
            total_misses = self.tier_stats["daily_misses"] + self.tier_stats["intraday_misses"]

            stats["overall_hit_rate"] = (total_hits / total) * 100
            stats["overall_miss_rate"] = (total_misses / total) * 100
            stats["overall_availability"] = 100 - stats["overall_miss_rate"]
        else:
            stats["overall_hit_rate"] = 0
            stats["overall_miss_rate"] = 0
            stats["overall_availability"] = 0

        return stats

    def reset_stats(self):
        """Reset performance statistics."""
        for key in self.tier_stats:
            self.tier_stats[key] = 0
        logger.info("Performance statistics reset")

    def _make_json_serializable(self, data):
        """Convert data to JSON-serializable format.

        Handles pandas Timestamps and other non-serializable types.
        """
        if isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif hasattr(data, "to_pydatetime"):  # pandas Timestamp
            return data.isoformat()
        elif hasattr(data, "isoformat"):  # datetime objects
            return data.isoformat()
        elif pd.isna(data):  # pandas NaN values
            return None
        else:
            return data


# Backward compatibility aliases
TwoTierDataSystem = UnifiedDataSystem
EnhancedTwoTierSystem = UnifiedDataSystem
