"""Historical Options Data Collection Service.

Systematically collects historical options chains from Alpha Vantage API with SQLite storage, rate limiting, progress
tracking, and resume capability.

Issue #147: Store raw options data in database Issue #179: Paper 3 multi-symbol data collection
"""

import asyncio
import datetime
import json
import logging
import os
import queue
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd

from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.utils.date_utils import now_iso, today_str

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HistoricalOptionsCollector:
    """Service to systematically collect historical options data.

    Features:
    - PostgreSQL storage (primary) for high concurrency
    - SQLite storage (legacy/local)
    - Rate-limited API calls (1000/min for Premium, 75/min for standard)
    - Progress tracking in database with resume capability
    - Error handling and retry logic
    - Multiple symbol support (SPY, QQQ, IWM)
    - Data quality validation and scoring

    Example:
        >>> collector = HistoricalOptionsCollector()
        >>> await collector.collect_symbol_historical("SPY", "2020-01-01", "2024-12-16")
    """

    def __init__(
        self,
        db_path: str = ".cache/options_historical.db",
        use_sqlite: bool = False,  # Default to PostgreSQL
        use_postgresql: bool = True,  # New parameter
        pg_host: str = "localhost",
        pg_port: int = 5432,
        pg_user: str = "cregan1",
        pg_database: str = "gex_options",
        rate_limit_per_minute: int = 900,  # Buffer below 1000 premium limit
    ):
        """Initialize historical data collector.

        Args:
            db_path: Path to SQLite database (when use_sqlite=True)
            use_sqlite: Use SQLite storage (True) or legacy pickle (False)
            rate_limit_per_minute: API calls per minute (900 for premium buffer)
        """
        self.use_sqlite = use_sqlite
        self.rate_limit = rate_limit_per_minute
        self.call_interval = 60.0 / rate_limit_per_minute

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Initialize storage backend
        if use_postgresql:
            self.db = PostgreSQLOptionsManager(
                host=pg_host,
                port=pg_port,
                user=pg_user,
                database=pg_database
            )
            self.cache = None
            self.logger.info(f"Using PostgreSQL storage: {pg_user}@{pg_host}:{pg_port}/{pg_database}")
        elif use_sqlite:
            self.db = SQLiteOptionsManager(db_path=db_path)
            self.cache = None  # Lazy load if needed
            self.logger.info(f"Using SQLite storage: {db_path}")
        else:
            self.cache = UnifiedCacheManager()
            self.db = None
            self.logger.info("Using legacy pickle storage")

        # Initialize API client (shares cache if using pickle)
        self.client = AlphaVantageGEXClient(cache_manager=self.cache if not use_sqlite else None)

        # Collection statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "cached_hits": 0,
            "start_time": None,
            "last_call_time": None,
        }

        # RAM buffer for async batch writes (decouples API calls from DB I/O)
        # Each options chain DataFrame is ~1-10MB average
        # With 64GB RAM and 15% target (~9.6GB), we can buffer ~1000-2000 items
        # Tuple: (symbol, trading_date, data, underlying_price)
        self._write_buffer: queue.Queue[Tuple[str, str, pd.DataFrame, Optional[float]]] = queue.Queue()
        self._buffer_size = 0  # Track approximate buffer size
        self._max_buffer_size = 1000  # ~1-10GB RAM buffer before backpressure
        self._write_thread: Optional[threading.Thread] = None
        self._stop_write_thread = threading.Event()
        self._buffer_lock = threading.Lock()
        self._pending_writes = 0  # Track writes in progress

    def get_trading_dates(self, start_date: str, end_date: str) -> List[str]:
        """Generate list of trading dates (weekdays) between start and end dates.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of trading date strings
        """
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        trading_dates = []
        current = start

        while current <= end:
            # Skip weekends (basic trading day filter)
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                trading_dates.append(current.strftime("%Y-%m-%d"))
            current += datetime.timedelta(days=1)

        return trading_dates

    def validate_options_data(self, data: pd.DataFrame, symbol: str, date: str) -> tuple:
        """Validate collected options data quality.

        Args:
            data: Options chain DataFrame
            symbol: Symbol being validated
            date: Date being validated

        Returns:
            (is_valid, reason) tuple
        """
        if data is None or data.empty:
            return False, "Empty DataFrame"

        # Check for required columns (flexible naming)
        required_cols_options = [
            ["strike"],
            ["expiration"],
            ["bid", "ask"],
            ["type", "option_type"],
            ["open_interest"],
        ]

        for col_options in required_cols_options:
            if not any(col in data.columns for col in col_options):
                return False, f"Missing one of columns: {col_options}"

        # Check for reasonable number of contracts
        if len(data) < 10:
            return False, f"Too few contracts: {len(data)}"

        # Check for reasonable strike range
        strikes = data["strike"].values
        if len(strikes) > 0:
            strike_range = max(strikes) - min(strikes)
            if strike_range < 10:  # Less than $10 range seems unreasonable
                return False, f"Strike range too narrow: ${strike_range}"

        return True, "Valid"

    def _has_cached_data(self, symbol: str, trading_date: str) -> bool:
        """Check if data already exists in storage.

        Args:
            symbol: Stock symbol
            trading_date: Trading date

        Returns:
            True if data exists
        """
        if self.db:
            return self.db.has_options_data(symbol, trading_date)

    def _store_data(self, symbol: str, trading_date: str, data: pd.DataFrame, underlying_price: float = None) -> bool:
        """Store options data in the appropriate backend.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            data: Options DataFrame
            underlying_price: Underlying stock price for the trading date

        Returns:
            True if stored successfully
        """
        if self.db:
            count = self.db.store_options_chain(symbol, trading_date, data, underlying_price=underlying_price)
            return count > 0
        return False

    def _store_data_buffered(
        self, symbol: str, trading_date: str, data: pd.DataFrame, underlying_price: float = None
    ) -> bool:
        """Buffer options data for async batch write (decouples API from DB I/O).

        Instead of blocking on SQLite writes, this queues data in RAM and a
        background thread handles the actual database writes. This allows
        API calls to proceed at full rate limit speed.

        BACKPRESSURE: If buffer exceeds max size, this will block until
        the background writer catches up. This prevents unbounded RAM usage.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            data: Options DataFrame
            underlying_price: Underlying stock price for the trading date

        Returns:
            True (data queued successfully)
        """
        if not self.db:
            return False

        # Start background write thread if not running
        self._ensure_write_thread_running()

        # BACKPRESSURE: Wait if buffer is too full (prevents OOM)
        while self._pending_writes >= self._max_buffer_size:
            self.logger.debug(f"Buffer full ({self._pending_writes}/{self._max_buffer_size}), waiting for writes...")
            time.sleep(0.1)

        # Queue the data for async write (include underlying_price in tuple)
        with self._buffer_lock:
            self._write_buffer.put((symbol, trading_date, data, underlying_price))
            self._pending_writes += 1
            self._buffer_size += 1

        return True

    def _ensure_write_thread_running(self):
        """Ensure background write thread is running."""
        if self._write_thread is None or not self._write_thread.is_alive():
            self._stop_write_thread.clear()
            self._write_thread = threading.Thread(target=self._background_write_worker, daemon=True)
            self._write_thread.start()
            self.logger.info("Started background database write thread")

    def _background_write_worker(self):
        """Background thread that processes the write buffer."""
        writes_completed = 0
        batch = []
        batch_size = 10  # Process in batches for efficiency

        while not self._stop_write_thread.is_set() or not self._write_buffer.empty():
            try:
                # Collect batch of items
                while len(batch) < batch_size:
                    try:
                        item = self._write_buffer.get(timeout=0.1)
                        batch.append(item)
                    except queue.Empty:
                        break

                # Process batch
                if batch:
                    for symbol, trading_date, data, underlying_price in batch:
                        try:
                            count = self.db.store_options_chain(
                                symbol, trading_date, data, underlying_price=underlying_price
                            )
                            if count > 0:
                                writes_completed += 1
                                with self._buffer_lock:
                                    self._pending_writes -= 1
                                    self._buffer_size = max(0, self._buffer_size - 1)
                            else:
                                self.logger.warning(f"Background write failed for {symbol} {trading_date}")
                                with self._buffer_lock:
                                    self._pending_writes -= 1
                        except Exception as e:
                            self.logger.error(f"Background write error for {symbol} {trading_date}: {e}")
                            with self._buffer_lock:
                                self._pending_writes -= 1

                    batch.clear()

                    # Log progress periodically
                    if writes_completed % 50 == 0 and writes_completed > 0:
                        self.logger.info(
                            f"Background writer: {writes_completed} writes completed, {self._pending_writes} pending"
                        )

            except Exception as e:
                self.logger.error(f"Background write thread error: {e}")
                time.sleep(0.5)

        self.logger.info(f"Background write thread finished: {writes_completed} total writes")

    def _flush_write_buffer(self, timeout: float = 60.0):
        """Wait for all pending writes to complete.

        Args:
            timeout: Maximum time to wait in seconds
        """
        if not self.db:
            return

        start_time = time.time()
        while self._pending_writes > 0 and (time.time() - start_time) < timeout:
            self.logger.info(f"Flushing write buffer: {self._pending_writes} pending writes...")
            time.sleep(1.0)

        if self._pending_writes > 0:
            self.logger.warning(f"Write buffer flush timed out with {self._pending_writes} pending writes")
        else:
            self.logger.info("Write buffer flushed successfully")

    def _stop_write_thread_gracefully(self):
        """Stop the background write thread gracefully."""
        if self._write_thread and self._write_thread.is_alive():
            self._stop_write_thread.set()
            self._write_thread.join(timeout=30.0)
            if self._write_thread.is_alive():
                self.logger.warning("Background write thread did not stop cleanly")

    def _get_missing_dates(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """Get dates that still need collection.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of missing trading dates
        """
        if self.db:
            return self.db.get_missing_dates(symbol, start_date, end_date)
        else:
            # Legacy: use JSON progress file
            all_dates = self.get_trading_dates(start_date, end_date)
            progress = self._load_legacy_progress()
            completed = set(progress.get("completed_dates", []))
            return [d for d in all_dates if d not in completed]

    def _load_legacy_progress(self) -> Dict:
        """Load progress from legacy JSON file."""
        if self.cache is None:
            return {"completed_dates": [], "failed_dates": []}

        progress_file = self.cache.base_dir / "collection_progress.json"
        if progress_file.exists():
            try:
                with open(progress_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"completed_dates": [], "failed_dates": []}

    def _save_legacy_progress(self, progress: Dict):
        """Save progress to legacy JSON file."""
        if self.cache is None:
            return

        progress_file = self.cache.base_dir / "collection_progress.json"
        try:
            with open(progress_file, "w") as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")

    async def collect_symbol_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        skip_existing: bool = True,
    ) -> Dict:
        """Collect historical options data for a single symbol.

        Args:
            symbol: Symbol to collect (SPY, QQQ, IWM)
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            skip_existing: Skip dates that already have data

        Returns:
            Collection summary dictionary
        """
        self.logger.info(f"Starting historical collection for {symbol}: {start_date} to {end_date}")

        # Get dates that need collection
        if skip_existing:
            remaining_dates = self._get_missing_dates(symbol, start_date, end_date)
            total_dates = len(self.get_trading_dates(start_date, end_date))
        else:
            remaining_dates = self.get_trading_dates(start_date, end_date)
            total_dates = len(remaining_dates)

        self.logger.info(f"Found {total_dates} trading dates, {len(remaining_dates)} need collection")

        summary = {
            "symbol": symbol,
            "total_dates": total_dates,
            "to_collect": len(remaining_dates),
            "completed_dates": 0,
            "failed_dates": 0,
            "skipped_dates": total_dates - len(remaining_dates),
            "start_time": now_iso(),
        }

        self.stats["start_time"] = now_iso()
        legacy_progress = self._load_legacy_progress() if not self.db else None

        for i, trade_date in enumerate(remaining_dates):
            try:
                # Rate limiting
                if self.stats["last_call_time"]:
                    elapsed = time.time() - self.stats["last_call_time"]
                    if elapsed < self.call_interval:
                        wait_time = self.call_interval - elapsed
                        await asyncio.sleep(wait_time)

                # Double-check cache (in case of concurrent collection)
                if skip_existing and self._has_cached_data(symbol, trade_date):
                    self.logger.debug(f"Already have data for {symbol} {trade_date}")
                    self.stats["cached_hits"] += 1
                    summary["skipped_dates"] += 1
                    continue

                # Make API call
                self.logger.info(f"Fetching {symbol} options for {trade_date} " f"({i + 1}/{len(remaining_dates)})")

                self.stats["last_call_time"] = time.time()
                # Skip legacy cache since we handle SQLite storage ourselves
                options_data = self.client.fetch_historical_options(
                    symbol, trade_date, cache_result=not self.db
                )
                self.stats["total_calls"] += 1

                # Validate data quality
                is_valid, reason = self.validate_options_data(options_data, symbol, trade_date)

                if is_valid:
                    # Fetch underlying price for this date
                    underlying_price = self.client.fetch_underlying_price(symbol, trade_date)

                    # Store data with underlying price
                    stored = self._store_data(symbol, trade_date, options_data, underlying_price=underlying_price)

                    if stored:
                        self.stats["successful_calls"] += 1
                        summary["completed_dates"] += 1
                        price_str = f"${underlying_price:.2f}" if underlying_price else "N/A"
                        self.logger.info(
                            f"Stored {len(options_data)} options for {symbol} {trade_date} (price: {price_str})"
                        )

                        # Update legacy progress if using pickle
                        if legacy_progress is not None:
                            legacy_progress["completed_dates"].append(trade_date)
                    else:
                        self.logger.warning(f"Storage failed for {symbol} {trade_date}")
                        self.stats["failed_calls"] += 1
                        summary["failed_dates"] += 1
                else:
                    self.stats["failed_calls"] += 1
                    summary["failed_dates"] += 1
                    self.logger.warning(f"Invalid data for {symbol} {trade_date}: {reason}")

                    if legacy_progress is not None:
                        legacy_progress["failed_dates"].append(trade_date)

                # Log progress periodically
                if (i + 1) % 10 == 0:
                    self._log_status(summary)
                    if legacy_progress is not None:
                        self._save_legacy_progress(legacy_progress)

            except Exception as e:
                self.logger.error(f"Error collecting {symbol} {trade_date}: {e}")
                summary["failed_dates"] += 1
                if legacy_progress is not None:
                    legacy_progress["failed_dates"].append(trade_date)

        # Final progress save
        if legacy_progress is not None:
            legacy_progress["symbols_completed"] = legacy_progress.get("symbols_completed", []) + [symbol]
            self._save_legacy_progress(legacy_progress)

        summary["end_time"] = now_iso()
        self.logger.info(f"Completed {symbol}: {summary}")

        return summary

    def _log_status(self, summary: Dict):
        """Log current collection status."""
        total_processed = summary["completed_dates"] + summary["skipped_dates"] + summary["failed_dates"]
        success_rate = (summary["completed_dates"] / max(1, summary["to_collect"])) * 100

        self.logger.info(
            f"Progress: {total_processed}/{summary['total_dates']} dates " f"({success_rate:.1f}% new data collected)"
        )
        self.logger.info(f"API Stats: {self.stats['total_calls']} calls, " f"{self.stats['cached_hits']} cache hits")

        # Show database stats if using SQLite
        if self.db:
            stats = self.db.get_database_stats()
            self.logger.info(
                f"Database: {stats.get('total_options_records', 0):,} records, " f"{stats.get('db_size_mb', 0):.2f} MB"
            )

    async def collect_multi_symbol_historical(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        skip_existing: bool = True,
        parallel: bool = True,
        buffered: bool = True,
    ) -> Dict:
        """Collect historical data for multiple symbols.

        Supports both sequential and parallel collection modes:
        - Sequential: One symbol at a time (slower but simpler)
        - Parallel: Interleaves API calls across symbols (faster, uses quota efficiently)
        - Buffered: Uses RAM buffer with async DB writes (fastest, decouples API from DB I/O)

        Args:
            symbols: List of symbols to collect (e.g., ["SPY", "QQQ", "IWM"])
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            skip_existing: Skip dates that already have data
            parallel: Use parallel collection (interleaved API calls) - faster
            buffered: Use RAM buffer with async writes (fastest) - default True

        Returns:
            Complete collection summary
        """
        if parallel and buffered:
            return await self._collect_multi_symbol_buffered(symbols, start_date, end_date, skip_existing)
        elif parallel:
            return await self._collect_multi_symbol_parallel(symbols, start_date, end_date, skip_existing)
        else:
            return await self._collect_multi_symbol_sequential(symbols, start_date, end_date, skip_existing)

    async def _collect_multi_symbol_sequential(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        skip_existing: bool = True,
    ) -> Dict:
        """Collect symbols sequentially (one at a time)."""
        overall_summary = {
            "symbols": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "storage_backend": "database" if self.db else "pickle",
            "collection_start": now_iso(),
            "symbol_summaries": {},
            "total_api_calls": 0,
            "total_successful": 0,
            "total_failed": 0,
            "mode": "sequential",
        }

        for symbol in symbols:
            self.logger.info(f"\n{'=' * 60}")
            self.logger.info(f"Starting collection for {symbol}")
            self.logger.info(f"{'=' * 60}")

            # Reset stats for each symbol
            self.stats = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "cached_hits": 0,
                "start_time": None,
                "last_call_time": None,
            }

            symbol_summary = await self.collect_symbol_historical(symbol, start_date, end_date, skip_existing)

            overall_summary["symbol_summaries"][symbol] = symbol_summary
            overall_summary["total_api_calls"] += self.stats["total_calls"]
            overall_summary["total_successful"] += self.stats["successful_calls"]
            overall_summary["total_failed"] += self.stats["failed_calls"]

        return self._finalize_collection_summary(overall_summary)

    async def _collect_multi_symbol_parallel(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        skip_existing: bool = True,
    ) -> Dict:
        """Collect symbols in parallel using interleaved API calls.

        This mode is much faster because it shares the 900 calls/min quota across
        multiple symbols, avoiding the sequential bottleneck.

        Example:
            SPY 2024-01-01 → QQQ 2024-01-01 → IWM 2024-01-01 → SPY 2024-01-02 → ...
            (Instead of: SPY 2024-01-01 to 2024-10-16 → then QQQ → then IWM)
        """
        overall_summary = {
            "symbols": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "storage_backend": "database" if self.db else "pickle",
            "collection_start": now_iso(),
            "symbol_summaries": {
                sym: {
                    "symbol": sym,
                    "total_dates": 0,
                    "to_collect": 0,
                    "completed_dates": 0,
                    "failed_dates": 0,
                    "skipped_dates": 0,
                }
                for sym in symbols
            },
            "total_api_calls": 0,
            "total_successful": 0,
            "total_failed": 0,
            "mode": "parallel",
        }

        # Initialize symbol iterators with remaining dates
        symbol_iterators = {}
        for symbol in symbols:
            if skip_existing:
                remaining = self._get_missing_dates(symbol, start_date, end_date)
                total = len(self.get_trading_dates(start_date, end_date))
            else:
                remaining = self.get_trading_dates(start_date, end_date)
                total = len(remaining)

            symbol_iterators[symbol] = {
                "dates": iter(remaining),
                "remaining": remaining,
                "total": total,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
            }

            self.logger.info(f"[{symbol}] Found {total} trading dates, {len(remaining)} need collection")
            overall_summary["symbol_summaries"][symbol]["total_dates"] = total
            overall_summary["symbol_summaries"][symbol]["to_collect"] = len(remaining)

        # Interleave collection across symbols
        active_tasks = {}

        for symbol in symbols:
            try:
                trade_date = next(symbol_iterators[symbol]["dates"])
                active_tasks[symbol] = {
                    "trade_date": trade_date,
                    "index": symbol_iterators[symbol]["skipped"] + symbol_iterators[symbol]["completed"] + 1,
                }
            except StopIteration:
                pass

        self.logger.info(f"\n{'=' * 60}")
        self.logger.info(f"Starting parallel collection for {len(symbols)} symbols")
        self.logger.info(f"{'=' * 60}\n")

        call_count = 0

        while active_tasks:
            # Process next symbol in rotation
            for symbol in list(active_tasks.keys()):
                if symbol not in active_tasks:
                    continue

                task = active_tasks[symbol]
                trade_date = task["trade_date"]

                try:
                    # Rate limiting
                    if self.stats["last_call_time"]:
                        elapsed = time.time() - self.stats["last_call_time"]
                        if elapsed < self.call_interval:
                            await asyncio.sleep(self.call_interval - elapsed)

                    # Double-check cache
                    if skip_existing and self._has_cached_data(symbol, trade_date):
                        self.logger.debug(f"[{symbol}] Already have {trade_date}")
                        overall_summary["symbol_summaries"][symbol]["skipped_dates"] += 1
                    else:
                        # Fetch and store
                        self.logger.info(
                            f"[{symbol}] Fetching {trade_date} ({task['index']}/{symbol_iterators[symbol]['total']})"
                        )

                        self.stats["last_call_time"] = time.time()
                        options_data = self.client.fetch_historical_options(
                            symbol, trade_date, cache_result=not self.db
                        )
                        self.stats["total_calls"] += 1
                        call_count += 1

                        is_valid, reason = self.validate_options_data(options_data, symbol, trade_date)

                        if is_valid:
                            # Fetch underlying price for this date
                            underlying_price = self.client.fetch_underlying_price(symbol, trade_date)

                            stored = self._store_data(
                                symbol, trade_date, options_data, underlying_price=underlying_price
                            )
                            if stored:
                                self.stats["successful_calls"] += 1
                                overall_summary["symbol_summaries"][symbol]["completed_dates"] += 1
                                price_str = f"${underlying_price:.2f}" if underlying_price else "N/A"
                                self.logger.info(
                                    f"[{symbol}] Stored {len(options_data)} options for {trade_date} (price: {price_str})"
                                )
                            else:
                                self.stats["failed_calls"] += 1
                                overall_summary["symbol_summaries"][symbol]["failed_dates"] += 1
                        else:
                            self.stats["failed_calls"] += 1
                            overall_summary["symbol_summaries"][symbol]["failed_dates"] += 1
                            self.logger.warning(f"[{symbol}] Invalid data for {trade_date}: {reason}")

                    # Log progress every 10 calls across all symbols
                    if call_count % 10 == 0:
                        self._log_parallel_status(symbol_iterators)
                        if self.db:
                            stats = self.db.get_database_stats()
                            self.logger.info(
                                f"Database: {stats.get('total_options_records', 0):,} records, {stats.get('db_size_mb', 0):.2f} MB\n"
                            )

                except Exception as e:
                    self.logger.error(f"[{symbol}] Error on {trade_date}: {e}")
                    overall_summary["symbol_summaries"][symbol]["failed_dates"] += 1

                # Load next date for this symbol
                try:
                    next_date = next(symbol_iterators[symbol]["dates"])
                    task["trade_date"] = next_date
                    task["index"] += 1
                except StopIteration:
                    del active_tasks[symbol]
                    self.logger.info(f"\n[{symbol}] Collection complete!\n")

        overall_summary["total_api_calls"] = self.stats["total_calls"]
        overall_summary["total_successful"] = self.stats["successful_calls"]
        overall_summary["total_failed"] = self.stats["failed_calls"]

        return self._finalize_collection_summary(overall_summary)

    async def _collect_multi_symbol_buffered(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        skip_existing: bool = True,
    ) -> Dict:
        """Collect symbols with RAM buffering and async DB writes.

        This is the FASTEST mode - it decouples API calls from database I/O by:
        1. Making API calls at full rate limit speed
        2. Queuing responses in RAM
        3. Background thread handles SQLite writes

        This prevents DB lock contention from slowing down API collection.
        """
        overall_summary = {
            "symbols": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "storage_backend": "database" if self.db else "pickle",
            "collection_start": now_iso(),
            "symbol_summaries": {
                sym: {
                    "symbol": sym,
                    "total_dates": 0,
                    "to_collect": 0,
                    "completed_dates": 0,
                    "failed_dates": 0,
                    "skipped_dates": 0,
                }
                for sym in symbols
            },
            "total_api_calls": 0,
            "total_successful": 0,
            "total_failed": 0,
            "mode": "parallel_buffered",
        }

        # Initialize symbol iterators with remaining dates
        symbol_iterators = {}
        for symbol in symbols:
            if skip_existing:
                remaining = self._get_missing_dates(symbol, start_date, end_date)
                total = len(self.get_trading_dates(start_date, end_date))
            else:
                remaining = self.get_trading_dates(start_date, end_date)
                total = len(remaining)

            symbol_iterators[symbol] = {
                "dates": iter(remaining),
                "remaining": remaining,
                "total": total,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
            }

            self.logger.info(f"[{symbol}] Found {total} trading dates, {len(remaining)} need collection")
            overall_summary["symbol_summaries"][symbol]["total_dates"] = total
            overall_summary["symbol_summaries"][symbol]["to_collect"] = len(remaining)

        # Start background write thread
        self._ensure_write_thread_running()

        # Interleave collection across symbols
        active_tasks = {}

        for symbol in symbols:
            try:
                trade_date = next(symbol_iterators[symbol]["dates"])
                active_tasks[symbol] = {
                    "trade_date": trade_date,
                    "index": symbol_iterators[symbol]["skipped"] + symbol_iterators[symbol]["completed"] + 1,
                }
            except StopIteration:
                pass

        self.logger.info(f"\n{'=' * 60}")
        self.logger.info(f"Starting BUFFERED parallel collection for {len(symbols)} symbols")
        self.logger.info(f"RAM buffer active - API calls decoupled from DB writes")
        self.logger.info(f"{'=' * 60}\n")

        call_count = 0

        while active_tasks:
            # Process next symbol in rotation
            for symbol in list(active_tasks.keys()):
                if symbol not in active_tasks:
                    continue

                task = active_tasks[symbol]
                trade_date = task["trade_date"]

                try:
                    # Rate limiting - MINIMAL delay since DB writes are async
                    if self.stats["last_call_time"]:
                        elapsed = time.time() - self.stats["last_call_time"]
                        if elapsed < self.call_interval:
                            await asyncio.sleep(self.call_interval - elapsed)

                    # Double-check cache
                    if skip_existing and self._has_cached_data(symbol, trade_date):
                        self.logger.debug(f"[{symbol}] Already have {trade_date}")
                        overall_summary["symbol_summaries"][symbol]["skipped_dates"] += 1
                    else:
                        # Fetch data (this is the rate-limited part)
                        self.logger.info(
                            f"[{symbol}] Fetching {trade_date} ({task['index']}/{symbol_iterators[symbol]['total']})"
                        )

                        self.stats["last_call_time"] = time.time()
                        options_data = self.client.fetch_historical_options(
                            symbol, trade_date, cache_result=not self.db
                        )
                        self.stats["total_calls"] += 1
                        call_count += 1

                        is_valid, reason = self.validate_options_data(options_data, symbol, trade_date)

                        if is_valid:
                            # Fetch underlying price for this date
                            underlying_price = self.client.fetch_underlying_price(symbol, trade_date)

                            # Queue for async write - NO BLOCKING on DB!
                            self._store_data_buffered(
                                symbol, trade_date, options_data, underlying_price=underlying_price
                            )
                            self.stats["successful_calls"] += 1
                            overall_summary["symbol_summaries"][symbol]["completed_dates"] += 1
                            price_str = f"${underlying_price:.2f}" if underlying_price else "N/A"
                            self.logger.info(
                                f"[{symbol}] Queued {len(options_data)} options for {trade_date} "
                                f"(price: {price_str}, buffer: {self._pending_writes} pending)"
                            )
                        else:
                            self.stats["failed_calls"] += 1
                            overall_summary["symbol_summaries"][symbol]["failed_dates"] += 1
                            self.logger.warning(f"[{symbol}] Invalid data for {trade_date}: {reason}")

                    # Log progress every 10 calls across all symbols
                    if call_count % 10 == 0:
                        self._log_buffered_status(symbol_iterators)

                except Exception as e:
                    self.logger.error(f"[{symbol}] Error on {trade_date}: {e}")
                    overall_summary["symbol_summaries"][symbol]["failed_dates"] += 1

                # Load next date for this symbol
                try:
                    next_date = next(symbol_iterators[symbol]["dates"])
                    task["trade_date"] = next_date
                    task["index"] += 1
                except StopIteration:
                    del active_tasks[symbol]
                    self.logger.info(f"\n[{symbol}] API collection complete! (writes may still be pending)\n")

        # Wait for all pending writes to complete
        self.logger.info(f"\nAPI collection finished. Flushing {self._pending_writes} pending DB writes...")
        self._flush_write_buffer(timeout=120.0)
        self._stop_write_thread_gracefully()

        overall_summary["total_api_calls"] = self.stats["total_calls"]
        overall_summary["total_successful"] = self.stats["successful_calls"]
        overall_summary["total_failed"] = self.stats["failed_calls"]

        return self._finalize_collection_summary(overall_summary)

    def _log_buffered_status(self, symbol_iterators: Dict):
        """Log status for buffered parallel collection."""
        self.logger.info("\n--- Buffered Parallel Collection Status ---")
        for sym, info in symbol_iterators.items():
            completed = info["completed"] if "completed" in info else 0
            total = info["total"]
            pct = (completed / total * 100) if total > 0 else 0
            self.logger.info(f"  {sym}: {completed}/{total} ({pct:.1f}%)")
        self.logger.info(
            f"API Stats: {self.stats['total_calls']} calls | " f"Buffer: {self._pending_writes} pending writes\n"
        )
        # Show database stats less frequently to avoid locking
        if self.stats["total_calls"] % 50 == 0 and self.db:
            try:
                stats = self.db.get_database_stats()
                self.logger.info(
                    f"Database: {stats.get('total_options_records', 0):,} records, {stats.get('db_size_mb', 0):.2f} MB\n"
                )
            except Exception:
                pass  # Skip if DB is busy

    def _log_parallel_status(self, symbol_iterators: Dict):
        """Log status for parallel collection."""
        self.logger.info("\n--- Parallel Collection Status ---")
        for sym, info in symbol_iterators.items():
            completed = info["completed"] if "completed" in info else 0
            total = info["total"]
            pct = (completed / total * 100) if total > 0 else 0
            self.logger.info(f"  {sym}: {completed}/{total} ({pct:.1f}%)")
        self.logger.info(
            f"API Stats: {self.stats['total_calls']} total calls, {self.stats['cached_hits']} cache hits\n"
        )

    def _finalize_collection_summary(self, summary: Dict) -> Dict:
        """Finalize collection summary with database stats."""
        summary["collection_end"] = now_iso()

        # Add final storage statistics
        if self.db:
            summary["final_db_stats"] = self.db.get_database_stats()
        else:
            summary["final_cache_stats"] = self._get_legacy_cache_info()

        # Log final status
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info("COLLECTION COMPLETE")
        self.logger.info(f"{'=' * 60}")
        self.logger.info(f"Mode: {summary.get('mode', 'sequential')}")
        self.logger.info(f"Total API calls: {summary['total_api_calls']}")
        self.logger.info(f"Successful: {summary['total_successful']}")
        self.logger.info(f"Failed: {summary['total_failed']}")

        if self.db:
            stats = summary["final_db_stats"]
            self.logger.info(f"Database: {stats.get('total_options_records', 0):,} records")
            self.logger.info(f"Database size: {stats.get('db_size_mb', 0):.2f} MB")

        # Save summary
        summary_path = (self.db.db_path.parent if self.use_sqlite else self.cache.base_dir) / "collection_summary.json"

        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        self.logger.info(f"Summary saved to {summary_path}")
        return summary

    def _get_legacy_cache_info(self) -> Dict:
        """Get storage info for legacy pickle cache."""
        if self.cache is None:
            return {}

        cache_dir = self.cache.base_dir / "options"
        total_size = 0
        file_count = 0

        if cache_dir.exists():
            for file_path in cache_dir.rglob("*.pickle"):
                try:
                    total_size += file_path.stat().st_size
                    file_count += 1
                except OSError:
                    pass

        return {
            "storage_mb": total_size / (1024 * 1024),
            "file_count": file_count,
            "avg_file_size_kb": (total_size / file_count / 1024) if file_count > 0 else 0,
        }

    def get_collection_status(self, symbol: str = None) -> Dict:
        """Get current collection status and statistics.

        Args:
            symbol: Filter by symbol (None for all)

        Returns:
            Status dictionary with progress and statistics
        """
        if self.db:
            stats = self.db.get_database_stats()
            progress = self.db.get_collection_progress(symbol)

            return {
                "storage": "database",
                "database_stats": stats,
                "progress_summary": (
                    {
                        "completed": len(progress[progress["status"] == "completed"]),
                        "failed": len(progress[progress["status"] == "failed"]),
                        "pending": len(progress[progress["status"] == "pending"]),
                    }
                    if not progress.empty
                    else {}
                ),
            }
        else:
            return {
                "storage": "pickle",
                "cache_stats": self._get_legacy_cache_info(),
                "progress": self._load_legacy_progress(),
            }


async def main():
    """Example usage of the historical collector with PostgreSQL backend."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("historical_collection.log"),
            logging.StreamHandler(),
        ],
    )

    # Initialize collector with PostgreSQL backend (default)
    collector = HistoricalOptionsCollector(
        use_postgresql=True,
        use_sqlite=False,
        pg_host="localhost",
        rate_limit_per_minute=900,  # Premium tier buffer
    )

    # Collect data for Paper 3 research
    symbols = ["SPY", "QQQ", "IWM"]
    start_date = "2020-01-01"
    end_date = today_str()

    summary = await collector.collect_multi_symbol_historical(symbols, start_date, end_date)

    print(f"\nCollection completed!")
    print(f"Total records: {summary.get('final_db_stats', {}).get('total_options_records', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
