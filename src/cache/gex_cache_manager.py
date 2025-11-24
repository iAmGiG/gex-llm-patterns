"""GEX Calculation Caching System Pre-computed gamma exposure storage for efficient multi-symbol, multi-timeframe
analysis."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Use date_utils instead of direct datetime calls
from src.utils.date_utils import now_iso

# Optional pyarrow dependency for parquet support
try:
    import pyarrow as pa
    import pyarrow.parquet as pq

    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False

logger = logging.getLogger(__name__)


class GEXCacheManager:
    """High-performance caching system for GEX calculations.

    Provides hierarchical storage with SQLite indexing for fast lookup:
    - Daily GEX summaries (JSON)
    - Strike-level breakdowns (Parquet)
    - Expiration breakdowns (JSON)
    - Fast indexing for historical analysis
    """

    def __init__(self, base_cache_dir: str = ".cache"):
        """Initialize GEX cache manager with directory structure and indexing."""
        self.base_cache_dir = Path(base_cache_dir)
        self.gex_cache_dir = self.base_cache_dir / "gex_data"
        self.index_dir = self.base_cache_dir / "index"
        self.index_path = self.index_dir / "gex_cache_index.sqlite"

        self._setup_cache_structure()
        self._setup_index()

        logger.info(f"GEX Cache Manager initialized: {self.gex_cache_dir}")

    def _setup_cache_structure(self):
        """Create directory structure for GEX cache."""
        self.gex_cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Symbol directories created lazily when first used (on-demand)
        # This aligns with the lazy loading philosophy used in UnifiedCacheManager

    def _setup_index(self):
        """Initialize SQLite index for fast GEX lookup."""
        with sqlite3.connect(self.index_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS gex_cache_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    trading_date TEXT NOT NULL,
                    calculation_timestamp TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    total_gex REAL,
                    net_gex REAL,
                    flip_point REAL,
                    underlying_price REAL,
                    contracts_processed INTEGER,
                    calculation_duration_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, trading_date, data_type)
                )
            """
            )

            # Create indexes for fast lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_date ON gex_cache_index(symbol, trading_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_flip_point ON gex_cache_index(symbol, flip_point)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_total_gex ON gex_cache_index(symbol, total_gex)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calculation_time ON gex_cache_index(calculation_timestamp)")

            conn.commit()

    def store_gex_calculation(
        self,
        symbol: str,
        trading_date: str,
        gex_summary: Dict[str, Any],
        strike_breakdown: pd.DataFrame = None,
        expiry_breakdown: Dict[str, Any] = None,
    ) -> bool:
        """Store complete GEX calculation results with indexing.

        Args:
            symbol: Stock symbol (SPY, SPX, etc.)
            trading_date: Trading date in YYYY-MM-DD format
            gex_summary: Daily aggregated GEX metrics
            strike_breakdown: Strike-level GEX breakdown DataFrame
            expiry_breakdown: Expiration-level aggregations

        Returns:
            True if stored successfully
        """
        try:
            # Create date directory
            date_dir = self.gex_cache_dir / symbol.upper() / trading_date
            date_dir.mkdir(parents=True, exist_ok=True)

            # Store GEX summary (JSON)
            summary_path = date_dir / "gex_summary.json"
            with open(summary_path, "w") as f:
                json.dump(gex_summary, f, indent=2, default=str)

            # Store strike breakdown (Parquet for performance, pickle as fallback)
            strike_path = None
            if strike_breakdown is not None and not strike_breakdown.empty:
                if PARQUET_AVAILABLE:
                    strike_path = date_dir / "gex_by_strike.parquet"
                    strike_breakdown.to_parquet(strike_path, compression="snappy")
                else:
                    strike_path = date_dir / "gex_by_strike.pickle"
                    strike_breakdown.to_pickle(strike_path)

            # Store expiry breakdown (JSON)
            expiry_path = None
            if expiry_breakdown:
                expiry_path = date_dir / "gex_by_expiration.json"
                with open(expiry_path, "w") as f:
                    json.dump(expiry_breakdown, f, indent=2, default=str)

            # Store metadata
            metadata = {
                "symbol": symbol,
                "trading_date": trading_date,
                "stored_timestamp": now_iso(),
                "files": {
                    "summary": str(summary_path.relative_to(self.base_cache_dir)),
                    "strike_detail": str(strike_path.relative_to(self.base_cache_dir)) if strike_path else None,
                    "expiry_breakdown": str(expiry_path.relative_to(self.base_cache_dir)) if expiry_path else None,
                },
            }

            metadata_path = date_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

            # Update index
            self._update_index(symbol, trading_date, gex_summary, str(summary_path))

            logger.info(f"Stored GEX calculation for {symbol} {trading_date}")
            return True

        except Exception as e:
            logger.error(f"Failed to store GEX calculation for {symbol} {trading_date}: {e}")
            return False

    def _update_index(self, symbol: str, trading_date: str, gex_summary: Dict, file_path: str):
        """Update SQLite index with GEX calculation metadata."""
        try:
            with sqlite3.connect(self.index_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO gex_cache_index
                    (symbol, trading_date, calculation_timestamp, data_type, file_path,
                     total_gex, net_gex, flip_point, underlying_price,
                     contracts_processed, calculation_duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        symbol,
                        trading_date,
                        gex_summary.get("calculation_timestamp", now_iso()),
                        "summary",
                        file_path,
                        gex_summary.get("total_gex"),
                        gex_summary.get("net_gex"),
                        gex_summary.get("flip_point"),
                        gex_summary.get("underlying_price"),
                        gex_summary.get("calculation_metadata", {}).get("options_contracts_processed"),
                        gex_summary.get("calculation_metadata", {}).get("calculation_duration_ms"),
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to update index for {symbol} {trading_date}: {e}")

    def get_raw_options_from_db(self, symbol: str, trading_date: str) -> Optional[pd.DataFrame]:
        """Retrieve raw options chain from database (Issue #147).

        Args:
            symbol: Stock symbol (SPY)
            trading_date: Trading date (YYYY-MM-DD)

        Returns:
            DataFrame with raw options or None if not found

        Schema matches Alpha Vantage format for backward compatibility.
        """
        db_path = self.base_cache_dir / "consolidated_historical.db"

        if not db_path.exists():
            logger.debug(f"Database not found: {db_path}")
            return None

        try:
            import sqlite3

            with sqlite3.connect(str(db_path)) as conn:
                query = """
                    SELECT
                        strike,
                        option_type as type,
                        expiration,
                        bid, ask, last,
                        volume, open_interest,
                        implied_volatility,
                        delta, gamma, theta, vega, rho,
                        contract_symbol,
                        underlying_price
                    FROM raw_options_chain
                    WHERE symbol = ? AND date = ?
                    ORDER BY strike, option_type
                """

                df = pd.read_sql_query(query, conn, params=(symbol.upper(), trading_date))

                if df.empty:
                    logger.debug(f"No raw options in DB for {symbol} {trading_date}")
                    return None

                logger.info(f"Retrieved {len(df)} raw options from DB for {symbol} {trading_date}")
                return df

        except Exception as e:
            logger.error(f"Error retrieving raw options from DB: {e}")
            return None

    def get_gex_summary(self, symbol: str, trading_date: str) -> Optional[Dict[str, Any]]:
        """Retrieve daily GEX summary from cache.

        Strategy (Nov 20, 2025 update): Query database first, fall back to file cache.
        Rationale: Database is single source of truth with complete historical data.

        Args:
            symbol: Stock symbol
            trading_date: Trading date in YYYY-MM-DD format

        Returns:
            GEX summary dict or None if not cached
        """
        # Try database first (primary source as of Nov 20, 2025)
        db_path = self.base_cache_dir / "gex_database.db"

        if db_path.exists():
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.execute(
                        """
                        SELECT spot_price, total_gex, net_call_gex, net_put_gex,
                               gamma_flip_point, flip_ratio, gex_regime,
                               data_quality_score, options_count
                        FROM daily_gex_metrics
                        WHERE symbol = ? AND date = ?
                        """,
                        (symbol.upper(), trading_date),
                    )
                    row = cursor.fetchone()

                    if row:
                        # Map database fields to GEX summary format
                        data = {
                            "underlying_price": row[0],
                            "spot_price": row[0],  # Alias for compatibility
                            "total_gex": row[1],
                            "net_call_gex": row[2],
                            "net_put_gex": row[3],
                            "net_gex": row[1],  # total_gex is net_gex
                            "net_gex_usd": row[1],  # Alias for prompt builder compatibility
                            "flip_point": row[4],
                            "gamma_flip_point": row[4],  # Alias for compatibility
                            "flip_ratio": row[5],
                            "gex_regime": row[6],
                            "calculation_metadata": {
                                "data_quality_score": row[7],
                                "options_contracts_processed": row[8],
                            },
                            "_cache_info": {"cache_hit": True, "source": "database", "retrieved_at": now_iso()},
                        }

                        logger.debug(f"Database hit for GEX summary: {symbol} {trading_date}")
                        return data

            except Exception as e:
                logger.warning(f"Database query failed for {symbol} {trading_date}: {e}, falling back to file cache")

        # Fall back to file cache (legacy support)
        try:
            summary_path = self.gex_cache_dir / symbol.upper() / trading_date / "gex_summary.json"

            if summary_path.exists():
                with open(summary_path, "r") as f:
                    data = json.load(f)

                # Add compatibility aliases for file cache data
                # File cache may have 'total_gex' (database export) or 'net_gex' (legacy)
                # Prompt builder expects 'net_gex_usd'
                # Database (2024) already adds this alias in the query mapping above
                if "net_gex_usd" not in data:
                    if "net_gex" in data:
                        data["net_gex_usd"] = data["net_gex"]
                    elif "total_gex" in data:
                        data["net_gex_usd"] = data["total_gex"]
                        # Also create net_gex alias for consistency
                        data["net_gex"] = data["total_gex"]

                # Add underlying_price alias if missing (for consistency with database)
                if "spot_price" in data and "underlying_price" not in data:
                    data["underlying_price"] = data["spot_price"]

                # Add cache metadata
                data["_cache_info"] = {
                    "cache_hit": True,
                    "source": "file_cache",
                    "retrieved_at": now_iso(),
                    "file_path": str(summary_path),
                }

                logger.debug(f"File cache hit for GEX summary: {symbol} {trading_date}")
                return data
            else:
                logger.debug(f"Cache miss for GEX summary: {symbol} {trading_date}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving GEX summary for {symbol} {trading_date}: {e}")
            return None

    def get_gex_by_strike_range(
        self, symbol: str, trading_date: str, strike_min: float = None, strike_max: float = None
    ) -> Optional[pd.DataFrame]:
        """Retrieve GEX data for specific strike range.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            strike_min: Minimum strike (None for no limit)
            strike_max: Maximum strike (None for no limit)

        Returns:
            DataFrame with strike-level GEX data or None
        """
        try:
            # Check for parquet file first, then pickle fallback
            parquet_path = self.gex_cache_dir / symbol.upper() / trading_date / "gex_by_strike.parquet"
            pickle_path = self.gex_cache_dir / symbol.upper() / trading_date / "gex_by_strike.pickle"

            df = None
            if parquet_path.exists() and PARQUET_AVAILABLE:
                df = pd.read_parquet(parquet_path)
            elif pickle_path.exists():
                df = pd.read_pickle(pickle_path)
            else:
                return None

            # Filter by strike range if specified
            if strike_min is not None:
                df = df[df["strike"] >= strike_min]
            if strike_max is not None:
                df = df[df["strike"] <= strike_max]

            logger.debug(f"Retrieved strike-level GEX for {symbol} {trading_date}: {len(df)} strikes")
            return df

        except Exception as e:
            logger.error(f"Error retrieving strike-level GEX for {symbol} {trading_date}: {e}")
            return None

    def get_historical_flip_points(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Retrieve historical gamma flip point time series.

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with historical flip points
        """
        try:
            with sqlite3.connect(self.index_path) as conn:
                query = """
                    SELECT symbol, trading_date, flip_point, total_gex, net_gex,
                           underlying_price, calculation_timestamp
                    FROM gex_cache_index
                    WHERE symbol = ? AND trading_date BETWEEN ? AND ?
                    AND data_type = 'summary' AND flip_point IS NOT NULL
                    ORDER BY trading_date
                """

                df = pd.read_sql_query(query, conn, params=(symbol, start_date, end_date))

                if not df.empty:
                    df["trading_date"] = pd.to_datetime(df["trading_date"])
                    df.set_index("trading_date", inplace=True)

                logger.info(f"Retrieved {len(df)} historical flip points for {symbol}")
                return df

        except Exception as e:
            logger.error(f"Error retrieving historical flip points: {e}")
            return pd.DataFrame()

    def find_nearest_flip_points(
        self, symbol: str, target_price: float, date_range: Tuple[str, str], tolerance: float = 5.0
    ) -> pd.DataFrame:
        """Find dates where flip point was near target price.

        Args:
            symbol: Stock symbol
            target_price: Target flip point price
            date_range: (start_date, end_date) tuple
            tolerance: Price tolerance for "near" matches

        Returns:
            DataFrame with matching dates and flip points
        """
        try:
            with sqlite3.connect(self.index_path) as conn:
                query = """
                    SELECT symbol, trading_date, flip_point, total_gex, underlying_price,
                           ABS(flip_point - ?) as distance
                    FROM gex_cache_index
                    WHERE symbol = ? AND trading_date BETWEEN ? AND ?
                    AND data_type = 'summary' AND ABS(flip_point - ?) <= ?
                    ORDER BY ABS(flip_point - ?)
                """

                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(target_price, symbol, date_range[0], date_range[1], target_price, tolerance, target_price),
                )

                logger.info(f"Found {len(df)} flip points near {target_price} for {symbol}")
                return df

        except Exception as e:
            logger.error(f"Error finding nearest flip points: {e}")
            return pd.DataFrame()

    def batch_get_gex(self, requests: List[Tuple[str, str]]) -> Dict[str, Dict[str, Any]]:
        """Efficient batch retrieval for multiple symbol/date combinations.

        Args:
            requests: List of (symbol, trading_date) tuples

        Returns:
            Dict mapping "symbol_date" to GEX summary data
        """
        results = {}

        for symbol, trading_date in requests:
            key = f"{symbol}_{trading_date}"
            gex_data = self.get_gex_summary(symbol, trading_date)

            if gex_data:
                results[key] = gex_data

        logger.info(f"Batch retrieval: {len(results)}/{len(requests)} cache hits")
        return results

    def invalidate_cache(self, symbol: str, trading_date: str = None) -> bool:
        """Remove cached GEX data for recalculation.

        Args:
            symbol: Stock symbol
            trading_date: Specific date (None to clear all dates for symbol)

        Returns:
            True if invalidated successfully
        """
        try:
            if trading_date:
                # Remove specific date
                date_dir = self.gex_cache_dir / symbol.upper() / trading_date
                if date_dir.exists():
                    import shutil

                    shutil.rmtree(date_dir)

                # Remove from index
                with sqlite3.connect(self.index_path) as conn:
                    conn.execute(
                        "DELETE FROM gex_cache_index WHERE symbol = ? AND trading_date = ?", (symbol, trading_date)
                    )
                    conn.commit()

                logger.info(f"Invalidated GEX cache for {symbol} {trading_date}")
            else:
                # Remove all dates for symbol
                symbol_dir = self.gex_cache_dir / symbol.upper()
                if symbol_dir.exists():
                    import shutil

                    shutil.rmtree(symbol_dir)
                    symbol_dir.mkdir()

                # Remove from index
                with sqlite3.connect(self.index_path) as conn:
                    conn.execute("DELETE FROM gex_cache_index WHERE symbol = ?", (symbol,))
                    conn.commit()

                logger.info(f"Invalidated all GEX cache for {symbol}")

            return True

        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health information."""
        try:
            with sqlite3.connect(self.index_path) as conn:
                # Basic stats
                total_entries = conn.execute("SELECT COUNT(*) FROM gex_cache_index").fetchone()[0]

                symbols = conn.execute(
                    "SELECT symbol, COUNT(*) as count FROM gex_cache_index GROUP BY symbol"
                ).fetchall()

                # Recent activity
                recent_calculations = conn.execute(
                    """
                    SELECT COUNT(*) FROM gex_cache_index
                    WHERE datetime(created_at) > datetime('now', '-7 days')
                """
                ).fetchone()[0]

            # Disk usage
            total_size = sum(f.stat().st_size for f in self.gex_cache_dir.rglob("*") if f.is_file())

            return {
                "total_cached_calculations": total_entries,
                "symbols": dict(symbols),
                "recent_calculations_7d": recent_calculations,
                "total_disk_usage_mb": total_size / (1024 * 1024),
                "cache_directory": str(self.gex_cache_dir),
                "index_path": str(self.index_path),
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
