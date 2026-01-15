"""
Historical GEX Database Builder - Issue #36

Production-ready version with:
- Concurrency control via lock files
- GEX results validation
- Resume capability for interrupted builds
- Batch database operations
- Memory monitoring
- Connection pooling

Issue #180: Migrated to SQLiteOptionsManager for options data.

Builds comprehensive historical GEX database by combining:
1. Historical options data collection
2. GEX calculations for each trading day
3. Fed context integration
4. Pattern detection and storage
5. Quality validation and database indexing
"""

import atexit
import datetime
import json
import logging
import sqlite3
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import psutil

from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.fed_data_integration import FedDataIntegration
from gex_db_infrastructure.data_sources.historical_collector import HistoricalOptionsCollector
from gex_db_infrastructure.data_sources.polygon_client import PolygonClient
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator
from src.utils.date_utils import calculate_duration_minutes, now_iso, now_timestamp, parse_date_string

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def safe_convert_for_sqlite(value):
    """Convert numpy types to Python native types for SQLite compatibility."""
    if value is None:
        return None
    elif isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    elif isinstance(value, str):
        return str(value)
    else:
        return value


class HistoricalGEXDatabaseBuilder:
    """Enhanced GEX database builder with production-ready features.

    Features:
    - Database concurrency control
    - Resume capability for interrupted builds
    - Batch database operations for performance
    - Memory monitoring to prevent OOM
    - GEX validation against known good values
    - Connection pooling for database efficiency
    """

    def __init__(self, database_path=None, cache_manager=None, sqlite_options_manager=None):
        """Initialize enhanced GEX database builder.

        Args:
            database_path: Path to SQLite database file
            cache_manager: Legacy UnifiedCacheManager (deprecated for options)
            sqlite_options_manager: SQLiteOptionsManager for options data (preferred)
        """
        self.cache = cache_manager or UnifiedCacheManager()
        self.collector = HistoricalOptionsCollector(cache_manager=self.cache)
        self.gex_calc = GEXCalculator()

        # Issue #180: Use SQLiteOptionsManager as primary options data source
        self.sqlite_options = sqlite_options_manager or SQLiteOptionsManager()

        # Initialize Fed integration if available
        try:
            self.fed_integration = FedDataIntegration()
            self.has_fed_data = True
        except Exception as e:
            self.has_fed_data = False
            logging.warning(f"Fed integration not available: {e}")

        # Initialize stock data client
        try:
            self.stock_client = PolygonClient()
            self.has_stock_data = True
        except Exception as e:
            self.has_stock_data = False
            logging.warning(f"Stock data client not available: {e}")

        # Database setup (Issue #140: Use unified consolidated_historical.db)
        self.db_path = Path(database_path) if database_path else self.cache.base_dir / "consolidated_historical.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Lock file for concurrency control
        self.lock_file = None

        # Connection pool
        self.connections = []
        self.max_connections = 5

        # Batch operation settings
        self.batch_size = 100
        self.batch_buffer = []

        # Memory monitoring thresholds
        self.memory_threshold_gb = 2.0
        self.last_memory_check = time.time()
        self.memory_check_interval = 30  # seconds

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Build statistics
        self.build_stats = {
            "days_processed": 0,
            "days_successful": 0,
            "days_failed": 0,
            "patterns_detected": 0,
            "start_time": None,
            "memory_warnings": 0,
        }

        # Register cleanup on exit
        atexit.register(self.cleanup)

    # === CONCURRENCY CONTROL ===

    def acquire_db_lock(self) -> Path:
        """Prevent concurrent database writes.

        Returns:
            Path to lock file

        Raises:
            RuntimeError: If database is already locked
        """
        lock_file = self.db_path.with_suffix(".lock")

        # Check if lock exists and is stale (older than 1 hour)
        if lock_file.exists():
            lock_age = time.time() - lock_file.stat().st_mtime
            if lock_age > 3600:  # 1 hour
                self.logger.warning(f"Removing stale lock file (age: {lock_age:.0f}s)")
                lock_file.unlink()
            else:
                raise RuntimeError(f"Database is locked by another process (age: {lock_age:.0f}s)")

        # Create lock file with PID info
        lock_file.write_text(
            json.dumps({"pid": psutil.Process().pid, "started": now_iso(), "host": psutil.Process().name()})
        )

        self.lock_file = lock_file
        self.logger.info(f"Acquired database lock: {lock_file}")
        return lock_file

    def release_db_lock(self):
        """Release database lock."""
        if self.lock_file and self.lock_file.exists():
            self.lock_file.unlink()
            self.logger.info(f"Released database lock: {self.lock_file}")
            self.lock_file = None

    # === CONNECTION POOLING ===

    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool.

        Yields:
            sqlite3.Connection: Database connection
        """
        if self.connections:
            conn = self.connections.pop()
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Faster writes

        try:
            yield conn
        finally:
            if len(self.connections) < self.max_connections:
                self.connections.append(conn)
            else:
                conn.close()

    # === MEMORY MONITORING ===

    def check_memory_usage(self) -> bool:
        """Monitor memory usage to prevent OOM.

        Returns:
            bool: True if memory is within limits, False if warning issued
        """
        current_time = time.time()
        if current_time - self.last_memory_check < self.memory_check_interval:
            return True

        self.last_memory_check = current_time
        process = psutil.Process()
        mem_info = process.memory_info()
        mem_gb = mem_info.rss / (1024 * 1024 * 1024)

        if mem_gb > self.memory_threshold_gb:
            self.logger.warning(f"High memory usage: {mem_gb:.2f}GB (threshold: {self.memory_threshold_gb}GB)")
            self.build_stats["memory_warnings"] += 1

            # Flush batch buffer to free memory
            if self.batch_buffer:
                self.flush_batch()

            # Clear cache if available
            if hasattr(self.cache, "clear_old_entries"):
                self.cache.clear_old_entries()

            return False

        return True

    # === RESUME CAPABILITY ===

    def get_resume_point(self, symbol):
        """Find last successfully processed date for resume capability.

        Args:
            symbol: Stock symbol

        Returns:
            Last processed date or None if starting fresh
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(date) FROM daily_gex_metrics WHERE symbol = ?", (symbol,))
                result = cursor.fetchone()
                last_date = result[0] if result and result[0] else None

                if last_date:
                    self.logger.info(f"Resume point for {symbol}: {last_date}")

                return last_date

        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return None
        except Exception as e:
            self.logger.error(f"Error getting resume point: {e}")
            return None

    # === GEX VALIDATION ===

    def validate_gex_results(self, gex_profile: Dict) -> bool:
        """Validate GEX calculations are reasonable.

        Args:
            gex_profile: GEX calculation results

        Returns:
            bool: True if valid, False if suspicious
        """
        try:
            # Check total GEX is within reasonable bounds
            # SPY typically has GEX between -1e10 and 1e10
            total_gex = gex_profile.get("total_gex", 0)
            if abs(total_gex) > 1e11:
                self.logger.warning(f"Suspicious GEX value: {total_gex:,.0f}")
                return False

            # Check flip point is within reasonable distance from spot
            spot_price = gex_profile.get("spot_price", 0)
            flip_point = gex_profile.get("gamma_flip_point", 0)

            if flip_point and spot_price:
                flip_ratio = gex_profile.get("flip_ratio", flip_point / spot_price)
                if flip_ratio < 0.8 or flip_ratio > 1.2:
                    self.logger.warning(f"Unusual flip ratio: {flip_ratio:.2f}")
                    return False

            # Check data quality score
            quality_score = gex_profile.get("data_quality_score", 0)
            if quality_score < 30:  # Very low quality
                self.logger.warning(f"Very low data quality: {quality_score}")
                return False

            # Check for NaN or Inf values
            numeric_fields = ["total_gex", "net_call_gex", "net_put_gex", "spot_price"]
            for field in numeric_fields:
                value = gex_profile.get(field)
                if value is not None and (np.isnan(value) or np.isinf(value)):
                    self.logger.warning(f"Invalid {field}: {value}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating GEX results: {e}")
            return False

    # === DATABASE SETUP ===

    def setup_database(self):
        """Create database schema with proper indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Main GEX metrics table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_gex_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    spot_price REAL,
                    total_gex REAL,
                    net_call_gex REAL,
                    net_put_gex REAL,
                    gamma_flip_point REAL,
                    flip_ratio REAL,
                    gex_regime TEXT,
                    data_quality_score INTEGER,
                    options_count INTEGER,
                    validation_status TEXT DEFAULT 'valid',
                    gex_oi REAL,
                    gex_volume REAL,
                    activity_ratio REAL,
                    economic_regime TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            """
            )

            # Strike-level GEX details
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS strike_gex_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    strike REAL NOT NULL,
                    net_gex REAL,
                    distance_from_spot REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol, date) REFERENCES daily_gex_metrics(symbol, date)
                )
            """
            )

            # Pattern detections
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pattern_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    pattern_name TEXT NOT NULL,
                    confidence REAL,
                    base_confidence REAL,
                    fed_weight REAL,
                    pattern_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol, date) REFERENCES daily_gex_metrics(symbol, date)
                )
            """
            )

            # Fed context
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fed_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    days_to_fomc INTEGER,
                    is_fomc_week BOOLEAN,
                    fed_context TEXT,
                    vix_level REAL,
                    market_stress_level TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """
            )

            # Build metadata
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS build_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_id TEXT UNIQUE,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    symbols_processed TEXT,
                    date_range TEXT,
                    total_days_processed INTEGER,
                    total_days_successful INTEGER,
                    memory_warnings INTEGER,
                    status TEXT
                )
            """
            )

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_gex_symbol_date ON daily_gex_metrics(symbol, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_gex_date ON daily_gex_metrics(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_strike_gex_symbol_date ON strike_gex_details(symbol, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_symbol_date ON pattern_detections(symbol, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_name ON pattern_detections(pattern_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fed_date ON fed_context(date)")

            conn.commit()

        self.logger.info(f"Database schema created: {self.db_path}")

    # [Continue with remaining methods in next part...]
    # === BATCH OPERATIONS ===

    def add_to_batch(self, operation_type, data: Tuple):
        """Add operation to batch buffer for efficient database writes.

        Args:
            operation_type: Type of operation ('gex', 'strike', 'pattern', 'fed')
            data: Tuple of data to insert
        """
        self.batch_buffer.append((operation_type, data))

        if len(self.batch_buffer) >= self.batch_size:
            self.flush_batch()

    def flush_batch(self):
        """Flush batch buffer to database."""
        if not self.batch_buffer:
            return

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Group operations by type
                gex_ops = []
                strike_ops = []
                pattern_ops = []
                fed_ops = []

                for op_type, data in self.batch_buffer:
                    if op_type == "gex":
                        gex_ops.append(data)
                    elif op_type == "strike":
                        strike_ops.append(data)
                    elif op_type == "pattern":
                        pattern_ops.append(data)
                    elif op_type == "fed":
                        fed_ops.append(data)

                # Batch insert each type
                if gex_ops:
                    # Issue #138: Updated INSERT to include dual GEX columns
                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO daily_gex_metrics
                        (symbol, date, spot_price, total_gex, net_call_gex, net_put_gex,
                         gamma_flip_point, flip_ratio, gex_regime, data_quality_score,
                         options_count, validation_status, gex_oi, gex_volume,
                         activity_ratio, economic_regime, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        gex_ops,
                    )

                if strike_ops:
                    cursor.executemany(
                        """
                        INSERT INTO strike_gex_details
                        (symbol, date, strike, net_gex, distance_from_spot, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        strike_ops,
                    )

                if pattern_ops:
                    cursor.executemany(
                        """
                        INSERT INTO pattern_detections
                        (symbol, date, pattern_name, confidence, base_confidence, fed_weight,
                         pattern_details, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        pattern_ops,
                    )

                if fed_ops:
                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO fed_context
                        (date, days_to_fomc, is_fomc_week, fed_context, vix_level,
                         market_stress_level, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        fed_ops,
                    )

                conn.commit()

                self.logger.debug(f"Flushed batch: {len(self.batch_buffer)} operations")
                self.batch_buffer.clear()

        except Exception as e:
            self.logger.error(f"Error flushing batch: {e}")
            # Don't clear buffer on error - allow retry

    # === CORE METHODS FROM ORIGINAL ===

    def get_stock_price(self, symbol, date, options_data: pd.DataFrame = None):
        """Get REAL stock closing price for the date.

        CRITICAL: Database must store REAL market prices, NEVER obfuscated values.
        Obfuscation is ONLY for LLM analysis layer (data_obfuscation.py), not storage.

        Methods (in priority order):
        1. Check options_data for underlyingPrice column
        2. Estimate from options using put-call parity
        3. Fetch from market data API
        4. ERROR if all methods fail (never store fake/obfuscated data)
        """
        # Method 1: Check for explicit underlying price in options data
        if options_data is not None and "underlyingPrice" in options_data.columns:
            spot = float(options_data["underlyingPrice"].iloc[0])
            self.logger.debug(f"Method 1: Got spot price from underlyingPrice column: {spot}")
            return spot

        # Method 2: Estimate from options data using put-call parity
        if options_data is not None and not options_data.empty:
            estimated = self.estimate_spot_from_options(options_data)
            if estimated:
                self.logger.info(f"Method 2: Estimated spot price from put-call parity: {estimated:.2f}")
                return estimated

        # Method 3: Fetch from market data API
        if self.has_stock_data:
            try:
                # Try to get closing price from Polygon
                price = self.stock_client.get_daily_close(symbol, date)
                if price:
                    self.logger.info(f"Method 3: Fetched spot price from API: {price:.2f}")
                    return price
            except Exception as e:
                self.logger.warning(f"Method 3 failed: Could not fetch price from API: {e}")

        # NO FALLBACK TO 450.0 - Raise error instead of storing bad data
        error_msg = (
            f"Cannot determine real spot price for {symbol} {date}. "
            f"All methods failed: underlyingPrice column missing, "
            f"put-call parity estimation failed, API fetch failed. "
            f"Database must store REAL prices only - refusing to store obfuscated/fake value."
        )
        self.logger.error(error_msg)
        raise ValueError(error_msg)

    def estimate_spot_from_options(self, options_data: pd.DataFrame):
        """Estimate spot price from options data using put-call parity."""
        try:
            calls = options_data[options_data["type"] == "call"]
            puts = options_data[options_data["type"] == "put"]

            if len(calls) == 0 or len(puts) == 0:
                return None

            # Find strikes with both calls and puts
            common_strikes = set(calls["strike"].values) & set(puts["strike"].values)

            if not common_strikes:
                return None

            # Use put-call parity: S = K + C - P (approximately, ignoring time value)
            best_estimates = []

            for strike in sorted(common_strikes):
                call_data = calls[calls["strike"] == strike]
                put_data = puts[puts["strike"] == strike]

                if len(call_data) > 0 and len(put_data) > 0:
                    call_price = (
                        call_data["mark"].iloc[0] if call_data["mark"].iloc[0] > 0 else call_data["last"].iloc[0]
                    )
                    put_price = put_data["mark"].iloc[0] if put_data["mark"].iloc[0] > 0 else put_data["last"].iloc[0]

                    if call_price > 0 and put_price > 0:
                        spot_estimate = strike + call_price - put_price
                        # Only consider reasonable estimates (within 50% of strike)
                        if 0.5 * strike <= spot_estimate <= 1.5 * strike:
                            best_estimates.append(spot_estimate)

            if best_estimates:
                # Return median estimate to avoid outliers
                median_estimate = sorted(best_estimates)[len(best_estimates) // 2]

                # Verify estimate is reasonable (within typical market ranges)
                if median_estimate < 10 or median_estimate > 10000:  # SPY/SPX range check
                    self.logger.warning(f"Suspicious spot estimate: {median_estimate}")
                    return None

                return median_estimate

            return None

        except Exception as e:
            self.logger.warning(f"Error estimating spot price from options: {e}")
            return None

    def prepare_options_data_for_gex(self, options_data: pd.DataFrame) -> pd.DataFrame:
        """Transform options data format for GEX calculator compatibility.

        Validates required columns and converts from separate call/put rows to combined format expected by GEX
        calculator.
        """
        # Validate required columns
        required_cols = ["strike", "expiration", "type", "open_interest", "volume", "implied_volatility"]
        missing_cols = [col for col in required_cols if col not in options_data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns for GEX calculation: {missing_cols}")

        if options_data.empty:
            raise ValueError("Cannot process empty options data")

        try:
            # Group by strike and expiration to combine calls and puts
            grouped_data = []

            for (strike, expiration), group in options_data.groupby(["strike", "expiration"]):
                calls = group[group["type"] == "call"]
                puts = group[group["type"] == "put"]

                # Create combined row for this strike/expiration
                row_data = {
                    "strike": strike,
                    "expiration": expiration,
                    "call_oi": calls["open_interest"].iloc[0] if len(calls) > 0 else 0,
                    "put_oi": puts["open_interest"].iloc[0] if len(puts) > 0 else 0,
                    "implied_vol": (
                        calls["implied_volatility"].iloc[0]
                        if len(calls) > 0
                        else (puts["implied_volatility"].iloc[0] if len(puts) > 0 else 0.2)
                    ),
                    "call_volume": calls["volume"].iloc[0] if len(calls) > 0 else 0,
                    "put_volume": puts["volume"].iloc[0] if len(puts) > 0 else 0,
                    "call_bid": calls["bid"].iloc[0] if len(calls) > 0 and "bid" in calls.columns else 0,
                    "call_ask": calls["ask"].iloc[0] if len(calls) > 0 and "ask" in calls.columns else 0,
                    "put_bid": puts["bid"].iloc[0] if len(puts) > 0 and "bid" in puts.columns else 0,
                    "put_ask": puts["ask"].iloc[0] if len(puts) > 0 and "ask" in puts.columns else 0,
                }

                grouped_data.append(row_data)

            return pd.DataFrame(grouped_data)

        except Exception as e:
            self.logger.error(f"Error preparing options data for GEX: {e}")
            return pd.DataFrame()

    def calculate_daily_gex_profile(self, symbol, date, options_data: pd.DataFrame, spot_price):
        """Calculate complete GEX profile for a trading day with validation.

        CRITICAL: Must use calculate_dealer_gamma_exposure() to match validation pipeline.

        Issue #138: Now also calculates dual GEX metrics (GEX_OI and GEX_Volume).
        """
        try:
            # Calculate dealer GEX using the SAME method as validation pipeline
            # This returns a DataFrame with 'dealer_gex' column for each contract
            gex_df = self.gex_calc.calculate_dealer_gamma_exposure(
                options_data, underlying_price=spot_price, open_interest_multiplier=100
            )

            if gex_df.empty:
                self.logger.warning(f"GEX calculation returned empty results for {symbol} {date}")
                return None

            # Sum total dealer GEX using the correctly signed 'weighted_gex' column
            total_gex = gex_df["weighted_gex"].sum()

            # Separate call and put GEX
            calls = gex_df[gex_df["type"] == "call"]
            puts = gex_df[gex_df["type"] == "put"]
            total_call_gex = calls["weighted_gex"].sum() if len(calls) > 0 else 0
            total_put_gex = puts["weighted_gex"].sum() if len(puts) > 0 else 0

            # Issue #138: Calculate dual GEX metrics (structural vs economic)
            dual_gex = None
            economic_regime = None
            if "volume" in options_data.columns:
                try:
                    dual_result = self.gex_calc.calculate_dual_gex(
                        options_data, underlying_price=spot_price, open_interest_multiplier=100
                    )
                    dual_gex = {
                        "gex_oi": float(dual_result["gex_oi"]),
                        "gex_volume": float(dual_result["gex_volume"]),
                        "activity_ratio": float(dual_result["activity_ratio"]),
                    }

                    # Classify economic regime using RegimeClassifier
                    from gex_db_infrastructure.validation.regime_classifier import RegimeClassifier

                    classifier = RegimeClassifier()
                    regime_result = classifier.classify_economic_regime(
                        dual_result["gex_oi"], dual_result["gex_volume"]
                    )
                    economic_regime = regime_result["regime"]

                    self.logger.info(
                        f"Dual GEX calculated for {symbol} {date}: "
                        f"OI=${dual_gex['gex_oi'] / 1e9:.2f}B, "
                        f"Vol=${dual_gex['gex_volume'] / 1e9:.2f}B, "
                        f"Regime={economic_regime}"
                    )
                except Exception as e:
                    self.logger.warning(f"Could not calculate dual GEX for {symbol} {date}: {e}")
                    dual_gex = None
                    economic_regime = None

            # Calculate strike-level GEX for database storage
            gex_by_strike = {}
            strike_groups = gex_df.groupby("strike")["dealer_gex"].sum()
            for strike, gex_value in strike_groups.items():
                gex_by_strike[str(strike)] = float(gex_value)

            # Calculate gamma flip point (strike where GEX crosses zero)
            gamma_flip = None
            strikes_sorted = sorted([(k, v) for k, v in gex_by_strike.items()], key=lambda x: float(x[0]))

            for i in range(len(strikes_sorted) - 1):
                strike1, gex1 = float(strikes_sorted[i][0]), strikes_sorted[i][1]
                strike2, gex2 = float(strikes_sorted[i + 1][0]), strikes_sorted[i + 1][1]

                # Check for sign change
                if (gex1 > 0 and gex2 < 0) or (gex1 < 0 and gex2 > 0):
                    # Linear interpolation to find zero crossing
                    gamma_flip = strike1 + (strike2 - strike1) * abs(gex1) / (abs(gex1) + abs(gex2))
                    break

            # Determine GEX regime
            if total_gex > 0:
                gex_regime = "positive"
            elif total_gex < 0:
                gex_regime = "negative"
            else:
                gex_regime = "neutral"

            # Data quality assessment
            options_count = len(options_data)
            unique_strikes = options_data["strike"].nunique()
            unique_expirations = options_data["expiration"].nunique()

            # Quality score based on data completeness (0-100)
            quality_score = min(
                100,
                int(
                    (unique_strikes / 50) * 40  # Strike coverage (40%)
                    + (unique_expirations / 10) * 30  # Expiration coverage (30%)
                    + (options_count / 500) * 30  # Volume of contracts (30%)
                ),
            )

            gex_profile = {
                "symbol": symbol,
                "date": date,
                "spot_price": spot_price,
                "total_gex": float(total_gex),
                "net_call_gex": float(total_call_gex),
                "net_put_gex": float(total_put_gex),
                "gamma_flip_point": gamma_flip,
                "flip_ratio": gamma_flip / spot_price if gamma_flip else None,
                "gex_regime": gex_regime,
                "strikes_detail": gex_by_strike,
                "data_quality_score": quality_score,
                "options_count": options_count,
                # Issue #138: Add dual GEX metrics (nullable for backward compatibility)
                "gex_oi": dual_gex["gex_oi"] if dual_gex else None,
                "gex_volume": dual_gex["gex_volume"] if dual_gex else None,
                "activity_ratio": dual_gex["activity_ratio"] if dual_gex else None,
                "economic_regime": economic_regime,
            }

            # Validate results
            if not self.validate_gex_results(gex_profile):
                gex_profile["validation_status"] = "suspicious"
            else:
                gex_profile["validation_status"] = "valid"

            return gex_profile

        except Exception as e:
            self.logger.error(f"Error calculating GEX for {symbol} {date}: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            return None

    def get_fed_context(self, date):
        """Get Fed context for the given date."""
        if not self.has_fed_data:
            return None

        try:
            # Convert string date to pandas Timestamp for fed_integration
            date_ts = pd.Timestamp(date)
            context = self.fed_integration.get_full_context(date_ts)
            if context:
                return {
                    "date": date,
                    "days_to_fomc": context.get("days_to_fomc"),
                    "is_fomc_week": context.get("is_fomc_week", False),
                    "fed_context": json.dumps(context),
                    "vix_level": context.get("vix_level"),
                    "market_stress_level": context.get("market_stress", "normal"),
                }
            return None
        except Exception as e:
            self.logger.debug(f"Could not get Fed context for {date}: {e}")
            return None

    def detect_patterns_with_context(self, gex_profile: Dict, fed_context: Optional[Dict]):
        """Detect patterns in GEX profile with Fed context weighting."""
        patterns = []

        try:
            # Example pattern detection (simplified)
            total_gex = gex_profile.get("total_gex", 0)
            flip_ratio = gex_profile.get("flip_ratio", 1.0)

            # Gamma trap pattern
            if abs(total_gex) > 1e9 and 0.98 <= flip_ratio <= 1.02:
                base_confidence = 0.7
                fed_weight = 1.0

                if fed_context and fed_context.get("is_fomc_week"):
                    fed_weight = 1.3  # Higher confidence during FOMC

                patterns.append(
                    {
                        "pattern": "gamma_trap",
                        "confidence": min(1.0, base_confidence * fed_weight),
                        "base_confidence": base_confidence,
                        "fed_weight": fed_weight,
                        "details": {"total_gex": total_gex, "flip_ratio": flip_ratio},
                    }
                )

            return patterns

        except Exception as e:
            self.logger.error(f"Error detecting patterns: {e}")
            return []

    def store_daily_analysis_batch(self, gex_profile: Dict, patterns: List[Dict], fed_context: Optional[Dict]):
        """Store daily analysis using batch operations.

        Issue #138: Now stores dual GEX metrics (gex_oi, gex_volume, activity_ratio, economic_regime).
        """
        try:
            # Add main GEX metrics to batch (including Issue #138 dual metrics)
            gex_data = (
                safe_convert_for_sqlite(gex_profile["symbol"]),
                safe_convert_for_sqlite(gex_profile["date"]),
                safe_convert_for_sqlite(gex_profile["spot_price"]),
                safe_convert_for_sqlite(gex_profile["total_gex"]),
                safe_convert_for_sqlite(gex_profile["net_call_gex"]),
                safe_convert_for_sqlite(gex_profile["net_put_gex"]),
                safe_convert_for_sqlite(gex_profile["gamma_flip_point"]),
                safe_convert_for_sqlite(gex_profile["flip_ratio"]),
                safe_convert_for_sqlite(gex_profile["gex_regime"]),
                safe_convert_for_sqlite(gex_profile["data_quality_score"]),
                safe_convert_for_sqlite(gex_profile["options_count"]),
                safe_convert_for_sqlite(gex_profile.get("validation_status", "valid")),
                # Issue #138: Add dual GEX metrics (nullable)
                safe_convert_for_sqlite(gex_profile.get("gex_oi")),
                safe_convert_for_sqlite(gex_profile.get("gex_volume")),
                safe_convert_for_sqlite(gex_profile.get("activity_ratio")),
                safe_convert_for_sqlite(gex_profile.get("economic_regime")),
                now_iso(),
            )
            self.add_to_batch("gex", gex_data)

            # Add strike details to batch
            for strike, gex_value in gex_profile.get("strikes_detail", {}).items():
                distance_from_spot = float(strike) - gex_profile["spot_price"]
                strike_data = (
                    safe_convert_for_sqlite(gex_profile["symbol"]),
                    safe_convert_for_sqlite(gex_profile["date"]),
                    safe_convert_for_sqlite(float(strike)),
                    safe_convert_for_sqlite(gex_value),
                    safe_convert_for_sqlite(distance_from_spot),
                    now_iso(),
                )
                self.add_to_batch("strike", strike_data)

            # Add patterns to batch
            for pattern in patterns:
                pattern_data = (
                    safe_convert_for_sqlite(gex_profile["symbol"]),
                    safe_convert_for_sqlite(gex_profile["date"]),
                    safe_convert_for_sqlite(pattern["pattern"]),
                    safe_convert_for_sqlite(pattern["confidence"]),
                    safe_convert_for_sqlite(pattern["base_confidence"]),
                    safe_convert_for_sqlite(pattern["fed_weight"]),
                    json.dumps(pattern.get("details", {})),
                    now_iso(),
                )
                self.add_to_batch("pattern", pattern_data)

            # Add Fed context to batch
            if fed_context:
                fed_data = (
                    safe_convert_for_sqlite(fed_context["date"]),
                    safe_convert_for_sqlite(fed_context.get("days_to_fomc")),
                    safe_convert_for_sqlite(fed_context.get("is_fomc_week", False)),
                    safe_convert_for_sqlite(fed_context.get("fed_context")),
                    safe_convert_for_sqlite(fed_context.get("vix_level")),
                    safe_convert_for_sqlite(fed_context.get("market_stress_level")),
                    now_iso(),
                )
                self.add_to_batch("fed", fed_data)

        except Exception as e:
            self.logger.error(f"Error storing daily analysis: {e}")

    def store_raw_options_chain(
        self, conn: sqlite3.Connection, symbol: str, date: str, options_df: pd.DataFrame, underlying_price: float
    ) -> int:
        """Store raw options chain data to database (Issue #147).

        Args:
            conn: Database connection
            symbol: Stock symbol (SPY)
            date: Trading date (YYYY-MM-DD)
            options_df: Raw options DataFrame from Alpha Vantage
            underlying_price: Spot price of underlying asset

        Returns:
            Number of rows inserted

        Note:
            Uses INSERT OR IGNORE to handle duplicates gracefully.
            All options for a given date share the same underlying_price.
        """
        if options_df is None or options_df.empty:
            self.logger.warning(f"Empty options data for {symbol} {date}")
            return 0

        # Prepare records for batch insert
        records = []
        for _, row in options_df.iterrows():
            try:
                # Handle expiration date conversion (may be Timestamp or string)
                expiration = row["expiration"]
                if hasattr(expiration, "strftime"):
                    expiration_str = expiration.strftime("%Y-%m-%d")
                else:
                    expiration_str = str(expiration)

                # Handle contract_symbol (may be missing or use contractID)
                contract_sym = row.get("contract_symbol") or row.get("contractID")

                record = (
                    symbol,
                    date,
                    safe_convert_for_sqlite(row["strike"]),
                    "call" if row.get("type", "call").lower() == "call" else "put",
                    expiration_str,
                    safe_convert_for_sqlite(row.get("bid")),
                    safe_convert_for_sqlite(row.get("ask")),
                    safe_convert_for_sqlite(row.get("last")),
                    safe_convert_for_sqlite(row.get("volume")),
                    safe_convert_for_sqlite(row.get("open_interest")),
                    safe_convert_for_sqlite(row.get("implied_volatility")),
                    safe_convert_for_sqlite(row.get("delta")),
                    safe_convert_for_sqlite(row.get("gamma")),
                    safe_convert_for_sqlite(row.get("theta")),
                    safe_convert_for_sqlite(row.get("vega")),
                    safe_convert_for_sqlite(row.get("rho")),
                    contract_sym,
                    safe_convert_for_sqlite(underlying_price),
                )
                records.append(record)
            except Exception as e:
                self.logger.warning(f"Error preparing option record: {e}, row: {row}")
                continue

        if not records:
            self.logger.warning(f"No valid records prepared for {symbol} {date}")
            return 0

        try:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR IGNORE INTO raw_options_chain
                (symbol, date, strike, option_type, expiration, bid, ask, last,
                 volume, open_interest, implied_volatility, delta, gamma, theta,
                 vega, rho, contract_symbol, underlying_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                records,
            )

            rows_inserted = cursor.rowcount
            self.logger.info(f"Stored {rows_inserted} raw options for {symbol} {date}")
            return rows_inserted

        except Exception as e:
            self.logger.error(f"Error inserting raw options: {e}")
            raise  # Re-raise to trigger transaction rollback

    def build_gex_database(self, symbols: List[str], start_date, end_date, min_quality_score: int = 60):
        """Build complete GEX database with resume capability and batch operations.

        Args:
            symbols: List of symbols to process
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            min_quality_score: Minimum data quality score to include

        Returns:
            Build summary with statistics
        """
        self.logger.info(f"Building GEX database: {symbols} from {start_date} to {end_date}")

        # Acquire lock for concurrency control
        try:
            self.acquire_db_lock()
        except RuntimeError as e:
            self.logger.error(f"Cannot acquire database lock: {e}")
            return {"error": str(e)}

        try:
            # Setup database
            self.setup_database()

            # Initialize build statistics
            build_id = now_timestamp()
            self.build_stats["start_time"] = now_iso()

            summary = {
                "build_id": build_id,
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "min_quality_score": min_quality_score,
                "build_start": self.build_stats["start_time"],
                "symbol_results": {},
                "total_days_attempted": 0,
                "total_days_successful": 0,
                "total_patterns_detected": 0,
                "database_path": str(self.db_path),
            }

            for symbol in symbols:
                self.logger.info(f"\n{'=' * 60}")
                self.logger.info(f"Processing {symbol}")
                self.logger.info(f"{'=' * 60}")

                symbol_summary = {
                    "symbol": symbol,
                    "days_processed": 0,
                    "days_successful": 0,
                    "days_failed": 0,
                    "patterns_detected": 0,
                    "avg_quality_score": 0,
                    "processing_start": now_iso(),
                }

                # Check for resume point
                resume_date = self.get_resume_point(symbol)
                if resume_date and start_date <= resume_date <= end_date:
                    # Only use resume date if it falls within requested range
                    self.logger.info(f"Resuming from {resume_date} (within range)")
                    # Adjust start date to day after last processed
                    resume_dt = parse_date_string(resume_date) + datetime.timedelta(days=1)
                    effective_start = max(resume_dt.strftime("%Y-%m-%d"), start_date)
                else:
                    if resume_date:
                        self.logger.info(
                            f"Ignoring resume point {resume_date} (outside range {start_date} to {end_date})"
                        )
                    effective_start = start_date

                # Get trading dates
                trading_dates = self.collector.get_trading_dates(effective_start, end_date)
                self.logger.info(f"Found {len(trading_dates)} trading dates to process")

                quality_scores = []

                for i, trade_date in enumerate(trading_dates):
                    try:
                        # Check memory usage periodically
                        self.check_memory_usage()

                        self.logger.info(f"Processing {symbol} {trade_date} ({i + 1}/{len(trading_dates)})")

                        # Get options data from SQLite (Issue #180)
                        options_data = self.sqlite_options.get_options_chain(symbol, trade_date)

                        if options_data is None or options_data.empty:
                            self.logger.warning(f"No options data available for {symbol} {trade_date}")
                            symbol_summary["days_failed"] += 1
                            continue

                        # Get stock price
                        spot_price = self.get_stock_price(symbol, trade_date, options_data)
                        if not spot_price:
                            self.logger.warning(f"No spot price available for {symbol} {trade_date}")
                            symbol_summary["days_failed"] += 1
                            continue

                        # Calculate GEX profile
                        gex_profile = self.calculate_daily_gex_profile(symbol, trade_date, options_data, spot_price)

                        if not gex_profile:
                            self.logger.warning(f"GEX calculation failed for {symbol} {trade_date}")
                            symbol_summary["days_failed"] += 1
                            continue

                        # Check quality threshold
                        if gex_profile["data_quality_score"] < min_quality_score:
                            self.logger.warning(f"Quality score {gex_profile['data_quality_score']} below threshold")
                            symbol_summary["days_failed"] += 1
                            continue

                        # Store raw options chain to database (Issue #147)
                        try:
                            conn = self.get_connection()
                            rows_inserted = self.store_raw_options_chain(
                                conn=conn,
                                symbol=symbol,
                                date=trade_date,
                                options_df=options_data,
                                underlying_price=spot_price,
                            )
                            conn.commit()
                            self.logger.debug(f"Stored {rows_inserted} raw options for {symbol} {trade_date}")
                        except Exception as e:
                            self.logger.error(f"Error storing raw options for {symbol} {trade_date}: {e}")
                            # Don't fail the whole process - raw options storage is supplementary
                            # Continue with GEX calculation and pattern detection

                        # Get Fed context
                        fed_context = self.get_fed_context(trade_date)

                        # Detect patterns
                        patterns = self.detect_patterns_with_context(gex_profile, fed_context)

                        # Store using batch operations
                        self.store_daily_analysis_batch(gex_profile, patterns, fed_context)

                        # Update statistics
                        symbol_summary["days_successful"] += 1
                        symbol_summary["patterns_detected"] += len(patterns)
                        quality_scores.append(gex_profile["data_quality_score"])

                        self.logger.info(
                            f"✅ {symbol} {trade_date}: GEX=${gex_profile['total_gex']:,.0f}, "
                            f"Quality={gex_profile['data_quality_score']}, "
                            f"Patterns={len(patterns)}"
                        )

                    except Exception as e:
                        self.logger.error(f"Error processing {symbol} {trade_date}: {e}")
                        symbol_summary["days_failed"] += 1

                    symbol_summary["days_processed"] += 1

                    # Progress update every 10 days
                    if symbol_summary["days_processed"] % 10 == 0:
                        progress_pct = (symbol_summary["days_processed"] / len(trading_dates)) * 100
                        self.logger.info(f"Progress: {progress_pct:.1f}% complete")

                # Flush any remaining batch operations
                self.flush_batch()

                # Finalize symbol summary
                symbol_summary["processing_end"] = now_iso()
                symbol_summary["avg_quality_score"] = sum(quality_scores) / len(quality_scores) if quality_scores else 0

                summary["symbol_results"][symbol] = symbol_summary
                summary["total_days_attempted"] += symbol_summary["days_processed"]
                summary["total_days_successful"] += symbol_summary["days_successful"]
                summary["total_patterns_detected"] += symbol_summary["patterns_detected"]

                self.logger.info(
                    f"Completed {symbol}: "
                    f"{symbol_summary['days_successful']}/{symbol_summary['days_processed']} "
                    f"days successful"
                )

            # Finalize build summary
            summary["build_end"] = now_iso()
            summary["build_duration_minutes"] = calculate_duration_minutes(summary["build_start"], summary["build_end"])
            summary["memory_warnings"] = self.build_stats["memory_warnings"]

            # Save build metadata to database
            self._save_build_metadata(summary)

            # Save build summary to file
            summary_file = self.cache.base_dir / f"gex_database_build_{build_id}.json"
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2, default=str)

            self.logger.info(f"\n{'=' * 60}")
            self.logger.info("GEX DATABASE BUILD COMPLETED")
            self.logger.info(f"{'=' * 60}")
            self.logger.info(f"Database: {self.db_path}")
            self.logger.info(f"Build summary: {summary_file}")
            self.logger.info(f"Duration: {summary['build_duration_minutes']:.1f} minutes")
            self.logger.info(f"Success rate: {summary['total_days_successful']}/{summary['total_days_attempted']}")
            self.logger.info(f"Total patterns detected: {summary['total_patterns_detected']}")

            return summary

        finally:
            # Always release lock
            self.release_db_lock()

    def _save_build_metadata(self, summary: Dict):
        """Save build metadata to database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO build_metadata
                    (build_id, started_at, completed_at, symbols_processed, date_range,
                     total_days_processed, total_days_successful, memory_warnings, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        summary["build_id"],
                        summary["build_start"],
                        summary["build_end"],
                        json.dumps(summary["symbols"]),
                        f"{summary['start_date']} to {summary['end_date']}",
                        summary["total_days_attempted"],
                        summary["total_days_successful"],
                        summary.get("memory_warnings", 0),
                        "completed",
                    ),
                )
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving build metadata: {e}")

    def cleanup(self):
        """Cleanup resources on exit."""
        try:
            # Flush any remaining batch operations
            if self.batch_buffer:
                self.flush_batch()

            # Close all connections in pool
            for conn in self.connections:
                conn.close()

            # Release lock if held
            if self.lock_file:
                self.release_db_lock()

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# === MAIN EXECUTION ===

if __name__ == "__main__":

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Example usage
    builder = HistoricalGEXDatabaseBuilder(database_path=".cache/enhanced_gex_database.db")

    # Define date range
    start_date = "2024-01-01"
    end_date = "2024-01-10"
    symbols = ["SPY"]

    # Build the database with all enhancements
    summary = builder.build_gex_database(symbols, start_date, end_date)

    print(f"\nBuild completed successfully!")
    print(f"Database: {builder.db_path}")
    print(f"Total days processed: {summary['total_days_attempted']}")
    print(f"Successful days: {summary['total_days_successful']}")
    print(f"Memory warnings: {summary.get('memory_warnings', 0)}")
