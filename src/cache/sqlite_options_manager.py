"""SQLite Options Data Manager for Historical Options Storage.

Provides efficient storage and retrieval of historical options chain data
with support for batch inserts, range queries, and GEX calculations.

Database: options_historical.db
Tables:
- options_chains: Raw options contract data from Alpha Vantage
- options_daily_summary: Pre-calculated daily GEX metrics

Issue #147: Store raw options data in database
Issue #179: Paper 3 multi-symbol data collection
Issue #16: Options chain quality validation at ingress
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.utils.date_utils import now_iso
from gex_db_infrastructure.validation.options_chain_validator import OptionsChainValidator, ValidationResult, ValidationSeverity

logger = logging.getLogger(__name__)


class SQLiteOptionsManager:
    """High-performance SQLite manager for historical options data.

    Features:
    - Batch inserts (>1000 records/sec)
    - Thread-safe writes
    - Efficient range queries
    - GEX summary calculation and storage
    - Data quality validation

    Example:
        >>> manager = SQLiteOptionsManager()
        >>> manager.store_options_chain("SPY", "2024-01-15", options_df)
        >>> data = manager.get_options_chain("SPY", "2024-01-15")
        >>> summary = manager.get_daily_summary("SPY", "2024-01-01", "2024-12-31")
    """

    def __init__(
        self,
        db_path: str = ".cache/options_historical.db",
        validation_config: Dict = None,
        enable_validation: bool = True,
    ):
        """Initialize SQLite options manager.

        Args:
            db_path: Path to SQLite database file
            validation_config: Optional config overrides for OptionsChainValidator
            enable_validation: Enable/disable validation at ingress (default: True)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._enable_validation = enable_validation
        self._validator = OptionsChainValidator(validation_config) if enable_validation else None
        self._init_database()

    def _init_database(self):
        """Create tables and indexes if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            # Options chains table - raw contract data
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS options_chains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Contract identification
                    symbol TEXT NOT NULL,
                    asset_class TEXT DEFAULT 'equity',  -- equity, bond, commodity, volatility, real_estate
                    trading_date TEXT NOT NULL,
                    strike REAL NOT NULL,
                    option_type TEXT NOT NULL CHECK(option_type IN ('call', 'put')),
                    expiration TEXT NOT NULL,
                    contract_symbol TEXT,

                    -- Pricing
                    bid REAL,
                    ask REAL,
                    last REAL,
                    mark REAL,
                    bid_size INTEGER,
                    ask_size INTEGER,

                    -- Volume & Interest
                    volume INTEGER,
                    open_interest INTEGER,

                    -- Greeks
                    delta REAL,
                    gamma REAL,
                    theta REAL,
                    vega REAL,
                    rho REAL,
                    implied_volatility REAL,

                    -- Underlying context
                    underlying_price REAL,

                    -- Derived fields
                    mid_price REAL,
                    bid_ask_spread REAL,
                    bid_ask_spread_pct REAL,
                    vol_oi_ratio REAL,

                    -- Metadata
                    data_source TEXT DEFAULT 'alpha_vantage',
                    data_quality_score REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(symbol, trading_date, strike, option_type, expiration)
                )
            """
            )

            # Options daily summary table - pre-calculated GEX
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS options_daily_summary (
                    symbol TEXT NOT NULL,
                    asset_class TEXT DEFAULT 'equity',  -- equity, bond, commodity, volatility, real_estate
                    trading_date TEXT NOT NULL,

                    -- Underlying context
                    underlying_price REAL,

                    -- GEX metrics
                    total_gex REAL,
                    net_call_gex REAL,
                    net_put_gex REAL,

                    -- Key levels
                    zero_gamma_level REAL,
                    max_gamma_strike REAL,

                    -- Regime classification
                    regime TEXT CHECK(regime IN ('POSITIVE_GAMMA', 'NEGATIVE_GAMMA', 'NEUTRAL')),

                    -- Concentration metrics
                    call_oi_concentration REAL,
                    put_oi_concentration REAL,

                    -- Data quality
                    contracts_count INTEGER,
                    expirations_count INTEGER,
                    data_quality_score REAL DEFAULT 1.0,

                    -- Calculation metadata
                    calculation_method TEXT DEFAULT 'black_scholes_iv',
                    calculation_timestamp TEXT,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY(symbol, trading_date)
                )
            """
            )

            # Collection progress tracking table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending', 'completed', 'failed', 'skipped')),
                    contracts_count INTEGER,
                    error_message TEXT,
                    api_call_made INTEGER DEFAULT 0,
                    validation_quality_score REAL,  -- Issue #16: Quality score from validation
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, trading_date)
                )
            """
            )

            conn.commit()

            # Run migrations for existing databases (before creating indexes on new columns)
            self._migrate_schema(conn)

            # Performance indexes (after migrations ensure columns exist)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_options_symbol_date ON options_chains(symbol, trading_date)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_options_strike_range ON options_chains(symbol, trading_date, strike)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_options_expiration ON options_chains(expiration)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_options_greeks ON options_chains(symbol, trading_date, gamma, delta)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_options_asset_class ON options_chains(asset_class)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_summary_symbol_date ON options_daily_summary(symbol, trading_date)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_regime ON options_daily_summary(regime)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_asset_class ON options_daily_summary(asset_class)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_progress_symbol ON collection_progress(symbol, status)")

            conn.commit()

        logger.info(f"SQLite options database initialized: {self.db_path}")

    def _migrate_schema(self, conn):
        """Apply schema migrations for existing databases."""
        try:
            # Check if asset_class column exists in options_chains
            cursor = conn.execute("PRAGMA table_info(options_chains)")
            columns = {row[1] for row in cursor.fetchall()}

            if "asset_class" not in columns:
                logger.info("Migrating: Adding asset_class column to options_chains")
                conn.execute("ALTER TABLE options_chains ADD COLUMN asset_class TEXT DEFAULT 'equity'")

            # Check if asset_class column exists in options_daily_summary
            cursor = conn.execute("PRAGMA table_info(options_daily_summary)")
            columns = {row[1] for row in cursor.fetchall()}

            if "asset_class" not in columns:
                logger.info("Migrating: Adding asset_class column to options_daily_summary")
                conn.execute("ALTER TABLE options_daily_summary ADD COLUMN asset_class TEXT DEFAULT 'equity'")

            # Check if validation_quality_score column exists in collection_progress (Issue #16)
            cursor = conn.execute("PRAGMA table_info(collection_progress)")
            columns = {row[1] for row in cursor.fetchall()}

            if "validation_quality_score" not in columns:
                logger.info("Migrating: Adding validation_quality_score column to collection_progress")
                conn.execute("ALTER TABLE collection_progress ADD COLUMN validation_quality_score REAL")

            conn.commit()
        except Exception as e:
            logger.warning(f"Migration check/apply failed (may be expected for new DB): {e}")

    # ================================================================
    # OPTIONS CHAIN METHODS
    # ================================================================

    def store_options_chain(
        self,
        symbol: str,
        trading_date: str,
        df: pd.DataFrame,
        underlying_price: float = None,
        asset_class: str = None,
        data_source: str = "alpha_vantage",
        skip_validation: bool = False,
    ) -> int:
        """Store options chain data with batch insert.

        Args:
            symbol: Stock symbol (SPY, QQQ, IWM, etc.)
            trading_date: Trading date (YYYY-MM-DD)
            df: DataFrame with options data
            underlying_price: Spot price (auto-detected from df if not provided)
            asset_class: Asset class (auto-detected from symbol if not provided)
            data_source: Data source identifier
            skip_validation: Skip validation for this call (default: False)

        Returns:
            Number of records inserted
        """
        # Auto-detect asset class from symbol if not provided
        if asset_class is None:
            asset_class = self._get_asset_class(symbol)
        if df.empty:
            logger.warning(f"Empty DataFrame for {symbol} {trading_date}, skipping")
            return 0

        try:
            # Standardize column names
            df = self._standardize_columns(df.copy())

            # === VALIDATION (Issue #16) ===
            validation_result = None
            if self._enable_validation and self._validator and not skip_validation:
                df, validation_result = self._validator.validate_and_filter(df, symbol, trading_date)

                # Log validation results
                if validation_result:
                    if validation_result.critical_count > 0:
                        logger.warning(
                            f"Validation {symbol} {trading_date}: "
                            f"{validation_result.rejected_records} rejected, "
                            f"{validation_result.warning_count} warnings, "
                            f"quality={validation_result.quality_score:.3f}"
                        )
                    elif validation_result.warning_count > 0:
                        logger.info(
                            f"Validation {symbol} {trading_date}: "
                            f"{validation_result.warning_count} warnings, "
                            f"quality={validation_result.quality_score:.3f}"
                        )

                # Check if all records were rejected
                if df.empty:
                    logger.error(
                        f"All records rejected for {symbol} {trading_date} - "
                        f"validation failed with {validation_result.critical_count} critical issues"
                    )
                    self._update_progress(
                        symbol,
                        trading_date,
                        "failed",
                        error_message=f"Validation failed: {validation_result.critical_count} critical issues",
                    )
                    return 0

            # Auto-detect underlying price if not provided
            if underlying_price is None and "underlying_price" in df.columns:
                underlying_price = df["underlying_price"].iloc[0]

            # Calculate derived fields if missing
            df = self._calculate_derived_fields(df)

            # Prepare records for insertion
            records = []
            for _, row in df.iterrows():
                record = {
                    "symbol": symbol.upper(),
                    "asset_class": asset_class,
                    "trading_date": trading_date,
                    "strike": row.get("strike"),
                    "option_type": self._normalize_option_type(row.get("type", row.get("option_type"))),
                    "expiration": self._normalize_date(row.get("expiration")),
                    "contract_symbol": row.get("contractID", row.get("contract_symbol")),
                    "bid": row.get("bid"),
                    "ask": row.get("ask"),
                    "last": row.get("last"),
                    "mark": row.get("mark"),
                    "bid_size": row.get("bid_size"),
                    "ask_size": row.get("ask_size"),
                    "volume": row.get("volume"),
                    "open_interest": row.get("open_interest"),
                    "delta": row.get("delta"),
                    "gamma": row.get("gamma"),
                    "theta": row.get("theta"),
                    "vega": row.get("vega"),
                    "rho": row.get("rho"),
                    "implied_volatility": row.get("implied_volatility"),
                    "underlying_price": underlying_price,
                    "mid_price": row.get("mid_price"),
                    "bid_ask_spread": row.get("bid_ask_spread"),
                    "bid_ask_spread_pct": row.get("bid_ask_spread_pct"),
                    "vol_oi_ratio": row.get("vol_oi_ratio"),
                    "data_source": data_source,
                    "data_quality_score": self._calculate_quality_score(row),
                }
                records.append(record)

            # Batch insert with thread safety
            inserted = self._batch_insert_options(records)

            # Update collection progress with validation info
            quality_score = validation_result.quality_score if validation_result else 1.0
            self._update_progress(
                symbol, trading_date, "completed", len(records), validation_quality_score=quality_score
            )

            # Enhanced logging with validation summary
            if validation_result and validation_result.rejected_records > 0:
                logger.info(
                    f"Stored {inserted} options for {symbol} {trading_date} "
                    f"(rejected {validation_result.rejected_records}, quality={quality_score:.3f})"
                )
            else:
                logger.info(f"Stored {inserted} options contracts for {symbol} {trading_date}")

            return inserted

        except Exception as e:
            logger.error(f"Error storing options chain for {symbol} {trading_date}: {e}")
            self._update_progress(symbol, trading_date, "failed", error_message=str(e))
            return 0

    def _batch_insert_options(self, records: List[Dict]) -> int:
        """Batch insert options records with conflict resolution.

        Args:
            records: List of record dictionaries

        Returns:
            Number of records inserted/updated
        """
        if not records:
            return 0

        columns = list(records[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        columns_str = ", ".join(columns)

        with self._write_lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Use INSERT OR REPLACE for upsert behavior
                sql = f"INSERT OR REPLACE INTO options_chains ({columns_str}) VALUES ({placeholders})"

                values = [[r.get(col) for col in columns] for r in records]
                cursor.executemany(sql, values)
                conn.commit()

                return cursor.rowcount

    def get_options_chain(
        self,
        symbol: str,
        trading_date: str,
        strike_min: float = None,
        strike_max: float = None,
        option_type: str = None,
    ) -> Optional[pd.DataFrame]:
        """Retrieve options chain for a specific date.

        Args:
            symbol: Stock symbol
            trading_date: Trading date (YYYY-MM-DD)
            strike_min: Minimum strike filter
            strike_max: Maximum strike filter
            option_type: Filter by 'call' or 'put'

        Returns:
            DataFrame with options data or None if not found
        """
        try:
            query = """
                SELECT * FROM options_chains
                WHERE symbol = ? AND trading_date = ?
            """
            params = [symbol.upper(), trading_date]

            if strike_min is not None:
                query += " AND strike >= ?"
                params.append(strike_min)

            if strike_max is not None:
                query += " AND strike <= ?"
                params.append(strike_max)

            if option_type:
                query += " AND option_type = ?"
                params.append(option_type.lower())

            query += " ORDER BY strike, option_type, expiration"

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)

            if df.empty:
                return None

            # Convert date columns
            for col in ["trading_date", "expiration"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])

            logger.debug(f"Retrieved {len(df)} options for {symbol} {trading_date}")
            return df

        except Exception as e:
            logger.error(f"Error retrieving options chain: {e}")
            return None

    def get_options_date_range(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get options data for a date range.

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with options data
        """
        try:
            query = """
                SELECT * FROM options_chains
                WHERE symbol = ?
                  AND trading_date >= ?
                  AND trading_date <= ?
                ORDER BY trading_date, strike, option_type
            """

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=[symbol.upper(), start_date, end_date])

            return df

        except Exception as e:
            logger.error(f"Error retrieving options date range: {e}")
            return pd.DataFrame()

    def has_options_data(self, symbol: str, trading_date: str) -> bool:
        """Check if options data exists for a date.

        Args:
            symbol: Stock symbol
            trading_date: Trading date

        Returns:
            True if data exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM options_chains WHERE symbol = ? AND trading_date = ?",
                    [symbol.upper(), trading_date],
                )
                count = cursor.fetchone()[0]
                return count > 0

        except Exception as e:
            logger.error(f"Error checking options data existence: {e}")
            return False

    # ================================================================
    # DAILY SUMMARY METHODS
    # ================================================================

    def store_daily_summary(self, symbol: str, trading_date: str, summary: Dict[str, Any]) -> bool:
        """Store pre-calculated daily GEX summary.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            summary: Dictionary with GEX metrics

        Returns:
            True if stored successfully
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO options_daily_summary (
                            symbol, trading_date, underlying_price,
                            total_gex, net_call_gex, net_put_gex,
                            zero_gamma_level, max_gamma_strike, regime,
                            call_oi_concentration, put_oi_concentration,
                            contracts_count, expirations_count,
                            data_quality_score, calculation_method,
                            calculation_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            symbol.upper(),
                            trading_date,
                            summary.get("underlying_price"),
                            summary.get("total_gex"),
                            summary.get("net_call_gex"),
                            summary.get("net_put_gex"),
                            summary.get("zero_gamma_level", summary.get("flip_point")),
                            summary.get("max_gamma_strike"),
                            summary.get("regime"),
                            summary.get("call_oi_concentration"),
                            summary.get("put_oi_concentration"),
                            summary.get("contracts_count"),
                            summary.get("expirations_count"),
                            summary.get("data_quality_score", 1.0),
                            summary.get("calculation_method", "black_scholes_iv"),
                            now_iso(),
                        ),
                    )
                    conn.commit()

            logger.debug(f"Stored daily summary for {symbol} {trading_date}")
            return True

        except Exception as e:
            logger.error(f"Error storing daily summary: {e}")
            return False

    def get_daily_summary(self, symbol: str, trading_date: str) -> Optional[Dict[str, Any]]:
        """Get daily GEX summary for a specific date.

        Args:
            symbol: Stock symbol
            trading_date: Trading date

        Returns:
            Dictionary with GEX metrics or None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM options_daily_summary WHERE symbol = ? AND trading_date = ?",
                    [symbol.upper(), trading_date],
                )
                row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error retrieving daily summary: {e}")
            return None

    def get_daily_summaries_range(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get daily summaries for a date range.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with daily summaries
        """
        try:
            query = """
                SELECT * FROM options_daily_summary
                WHERE symbol = ?
                  AND trading_date >= ?
                  AND trading_date <= ?
                ORDER BY trading_date
            """

            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=[symbol.upper(), start_date, end_date])

            if not df.empty:
                df["trading_date"] = pd.to_datetime(df["trading_date"])
                df.set_index("trading_date", inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error retrieving daily summaries: {e}")
            return pd.DataFrame()

    # ================================================================
    # COLLECTION PROGRESS METHODS
    # ================================================================

    def _update_progress(
        self,
        symbol: str,
        trading_date: str,
        status: str,
        contracts_count: int = None,
        error_message: str = None,
        api_call_made: bool = False,
        validation_quality_score: float = None,
    ):
        """Update collection progress tracking.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            status: 'pending', 'completed', 'failed', 'skipped'
            contracts_count: Number of contracts collected
            error_message: Error message if failed
            api_call_made: Whether an API call was made
            validation_quality_score: Quality score from validation (Issue #16)
        """
        try:
            with self._write_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO collection_progress
                        (symbol, trading_date, status, contracts_count, error_message, api_call_made, validation_quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            symbol.upper(),
                            trading_date,
                            status,
                            contracts_count,
                            error_message,
                            1 if api_call_made else 0,
                            validation_quality_score,
                        ),
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def get_collection_progress(self, symbol: str = None) -> pd.DataFrame:
        """Get collection progress summary.

        Args:
            symbol: Filter by symbol (None for all)

        Returns:
            DataFrame with progress data
        """
        try:
            query = "SELECT * FROM collection_progress"
            params = []

            if symbol:
                query += " WHERE symbol = ?"
                params.append(symbol.upper())

            query += " ORDER BY symbol, trading_date"

            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql_query(query, conn, params=params)

        except Exception as e:
            logger.error(f"Error retrieving progress: {e}")
            return pd.DataFrame()

    def get_missing_dates(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """Get list of dates that need collection.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of missing trading dates
        """
        try:
            # Get all trading dates in range (weekdays)
            import datetime

            start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

            all_dates = set()
            current = start
            while current <= end:
                if current.weekday() < 5:  # Monday=0, Friday=4
                    all_dates.add(current.strftime("%Y-%m-%d"))
                current += datetime.timedelta(days=1)

            # Get completed dates from database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT trading_date FROM options_chains
                    WHERE symbol = ? AND trading_date >= ? AND trading_date <= ?
                """,
                    [symbol.upper(), start_date, end_date],
                )
                completed_dates = {row[0] for row in cursor.fetchall()}

            # Also check progress table for failed dates that should be retried
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT trading_date FROM collection_progress
                    WHERE symbol = ? AND status = 'skipped'
                """,
                    [symbol.upper()],
                )
                skipped_dates = {row[0] for row in cursor.fetchall()}

            # Missing = all dates - completed dates + any skipped dates we should retry
            missing = (all_dates - completed_dates) | skipped_dates

            return sorted(list(missing))

        except Exception as e:
            logger.error(f"Error getting missing dates: {e}")
            return []

    # ================================================================
    # STATISTICS METHODS
    # ================================================================

    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics.

        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # Total options records
                stats["total_options_records"] = conn.execute("SELECT COUNT(*) FROM options_chains").fetchone()[0]

                # Records by symbol
                cursor = conn.execute(
                    """
                    SELECT symbol, COUNT(*) as count,
                           MIN(trading_date) as min_date,
                           MAX(trading_date) as max_date,
                           COUNT(DISTINCT trading_date) as trading_days
                    FROM options_chains
                    GROUP BY symbol
                """
                )
                stats["by_symbol"] = {
                    row[0]: {"records": row[1], "min_date": row[2], "max_date": row[3], "trading_days": row[4]}
                    for row in cursor.fetchall()
                }

                # Daily summaries count
                stats["daily_summaries"] = conn.execute("SELECT COUNT(*) FROM options_daily_summary").fetchone()[0]

                # Greeks coverage
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN delta IS NOT NULL THEN 1 ELSE 0 END) as has_delta,
                        SUM(CASE WHEN gamma IS NOT NULL THEN 1 ELSE 0 END) as has_gamma,
                        SUM(CASE WHEN implied_volatility IS NOT NULL THEN 1 ELSE 0 END) as has_iv
                    FROM options_chains
                """
                )
                row = cursor.fetchone()
                if row[0] > 0:
                    stats["greeks_coverage"] = {
                        "delta_pct": round(row[1] / row[0] * 100, 2),
                        "gamma_pct": round(row[2] / row[0] * 100, 2),
                        "iv_pct": round(row[3] / row[0] * 100, 2),
                    }

                # Database file size
                stats["db_size_mb"] = round(self.db_path.stat().st_size / (1024 * 1024), 2)

                # Collection progress summary
                cursor = conn.execute(
                    """
                    SELECT status, COUNT(*) FROM collection_progress GROUP BY status
                """
                )
                stats["collection_progress"] = dict(cursor.fetchall())

            return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

    # ================================================================
    # HELPER METHODS
    # ================================================================

    # Asset class mapping for multi-asset research
    ASSET_CLASS_MAP = {
        # Equities - Tech + Broad Market
        "SPY": "equity",  # S&P 500
        "QQQ": "equity",  # Nasdaq 100
        "IWM": "equity",  # Russell 2000
        "AAPL": "equity",  # Apple
        "MSFT": "equity",  # Microsoft
        "TSLA": "equity",  # Tesla
        "VTI": "equity",  # Vanguard Total Stock
        "DIA": "equity",  # Dow Jones
        "SPX": "equity",  # S&P 500 Index
        # Bond ETFs
        "TLT": "bond",  # 20+ Year Treasury
        "IEF": "bond",  # 7-10 Year Treasury
        "LQD": "bond",  # Investment Grade Corporate
        # Commodities / Precious Metals
        "GLD": "commodity",  # Gold
        "SLV": "commodity",  # Silver
        # Volatility
        "VXX": "volatility",  # VIX Short-Term Futures
        "VIX": "volatility",  # VIX Index
        "UVXY": "volatility",  # Ultra VIX Short-Term
        # Real Estate
        "IYR": "real_estate",  # US Real Estate
        "VNQ": "real_estate",  # Vanguard Real Estate
    }

    def _get_asset_class(self, symbol: str) -> str:
        """Get asset class for a symbol.

        Args:
            symbol: Stock/ETF symbol

        Returns:
            Asset class string (equity, bond, commodity, volatility, real_estate)
        """
        return self.ASSET_CLASS_MAP.get(symbol.upper(), "equity")

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize DataFrame column names."""
        column_mapping = {
            "contractID": "contract_symbol",
            "type": "option_type",
            "impliedVolatility": "implied_volatility",
            "openInterest": "open_interest",
            "bidSize": "bid_size",
            "askSize": "ask_size",
        }

        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and new_name not in df.columns:
                df[new_name] = df[old_name]

        return df

    def _normalize_option_type(self, option_type: Any) -> Optional[str]:
        """Normalize option type to 'call' or 'put'."""
        if option_type is None:
            return None

        option_type = str(option_type).lower().strip()

        if option_type in ("call", "c"):
            return "call"
        elif option_type in ("put", "p"):
            return "put"

        return option_type

    def _normalize_date(self, date_val: Any) -> Optional[str]:
        """Normalize date to YYYY-MM-DD string."""
        if date_val is None:
            return None

        if isinstance(date_val, str):
            return date_val[:10]  # Take first 10 chars (YYYY-MM-DD)

        if hasattr(date_val, "strftime"):
            return date_val.strftime("%Y-%m-%d")

        return str(date_val)[:10]

    def _calculate_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate derived fields if not present."""
        if "mid_price" not in df.columns and "bid" in df.columns and "ask" in df.columns:
            df["mid_price"] = (df["bid"] + df["ask"]) / 2

        if "bid_ask_spread" not in df.columns and "bid" in df.columns and "ask" in df.columns:
            df["bid_ask_spread"] = df["ask"] - df["bid"]

        if "bid_ask_spread_pct" not in df.columns and "mid_price" in df.columns and "bid_ask_spread" in df.columns:
            df["bid_ask_spread_pct"] = df["bid_ask_spread"] / df["mid_price"] * 100

        if "vol_oi_ratio" not in df.columns and "volume" in df.columns and "open_interest" in df.columns:
            df["vol_oi_ratio"] = df["volume"] / (df["open_interest"] + 1)

        return df

    def _calculate_quality_score(self, row: pd.Series) -> float:
        """Calculate data quality score for a record.

        Score based on:
        - Greeks availability (40%)
        - IV availability (20%)
        - Bid/Ask spread reasonableness (20%)
        - Volume/OI presence (20%)
        """
        score = 0.0

        # Greeks (40%)
        greeks_present = sum([1 for g in ["delta", "gamma", "theta", "vega"] if pd.notna(row.get(g))])
        score += (greeks_present / 4) * 0.4

        # IV (20%)
        if pd.notna(row.get("implied_volatility")):
            score += 0.2

        # Bid/Ask spread (20%)
        bid = row.get("bid", 0) or 0
        ask = row.get("ask", 0) or 0
        if bid > 0 and ask > 0:
            spread_pct = (ask - bid) / ((bid + ask) / 2) * 100
            if spread_pct < 50:  # Reasonable spread
                score += 0.2
            elif spread_pct < 100:
                score += 0.1

        # Volume/OI (20%)
        if row.get("volume", 0) and row.get("volume", 0) > 0:
            score += 0.1
        if row.get("open_interest", 0) and row.get("open_interest", 0) > 0:
            score += 0.1

        return round(score, 2)

    def vacuum(self):
        """Optimize database (reclaim space after deletions)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("VACUUM")
            logger.info("Database optimized (VACUUM completed)")
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")

    def close(self):
        """Close any open connections (placeholder for connection pooling)."""
        pass
