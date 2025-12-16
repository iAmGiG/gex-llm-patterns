"""Historical Options Data Collection Service.

Systematically collects historical options chains from Alpha Vantage API
with SQLite storage, rate limiting, progress tracking, and resume capability.

Issue #147: Store raw options data in database
Issue #179: Paper 3 multi-symbol data collection
"""

import asyncio
import datetime
import json
import logging
import os
import sys
import time
from typing import Dict, List, Optional

import pandas as pd

from src.cache.sqlite_options_manager import SQLiteOptionsManager
from src.cache.unified_cache import UnifiedCacheManager
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.utils.date_utils import now_iso, today_str

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HistoricalOptionsCollector:
    """Service to systematically collect historical options data.

    Features:
    - SQLite storage (primary) with pickle fallback
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
        use_sqlite: bool = True,
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
        if use_sqlite:
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
        if self.use_sqlite:
            return self.db.has_options_data(symbol, trading_date)
        else:
            cached = self.cache.get_options_data(symbol, trading_date)
            return cached is not None and not cached.empty

    def _store_data(self, symbol: str, trading_date: str, data: pd.DataFrame) -> bool:
        """Store options data in the appropriate backend.

        Args:
            symbol: Stock symbol
            trading_date: Trading date
            data: Options DataFrame

        Returns:
            True if stored successfully
        """
        if self.use_sqlite:
            count = self.db.store_options_chain(symbol, trading_date, data)
            return count > 0
        else:
            return self.cache.store_options_data(symbol, trading_date, data)

    def _get_missing_dates(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """Get dates that still need collection.

        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date

        Returns:
            List of missing trading dates
        """
        if self.use_sqlite:
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
        legacy_progress = self._load_legacy_progress() if not self.use_sqlite else None

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
                self.logger.info(f"Fetching {symbol} options for {trade_date} " f"({i+1}/{len(remaining_dates)})")

                self.stats["last_call_time"] = time.time()
                # Skip legacy cache since we handle SQLite storage ourselves
                options_data = self.client.fetch_historical_options(
                    symbol, trade_date, cache_result=not self.use_sqlite
                )
                self.stats["total_calls"] += 1

                # Validate data quality
                is_valid, reason = self.validate_options_data(options_data, symbol, trade_date)

                if is_valid:
                    # Store data
                    stored = self._store_data(symbol, trade_date, options_data)

                    if stored:
                        self.stats["successful_calls"] += 1
                        summary["completed_dates"] += 1
                        self.logger.info(f"Stored {len(options_data)} options for {symbol} {trade_date}")

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
        if self.use_sqlite:
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
    ) -> Dict:
        """Collect historical data for multiple symbols.

        Supports both sequential and parallel collection modes:
        - Sequential: One symbol at a time (slower but simpler)
        - Parallel: Interleaves API calls across symbols (faster, uses quota efficiently)

        Args:
            symbols: List of symbols to collect (e.g., ["SPY", "QQQ", "IWM"])
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            skip_existing: Skip dates that already have data
            parallel: Use parallel collection (interleaved API calls) - faster

        Returns:
            Complete collection summary
        """
        if parallel:
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
            "storage_backend": "sqlite" if self.use_sqlite else "pickle",
            "collection_start": now_iso(),
            "symbol_summaries": {},
            "total_api_calls": 0,
            "total_successful": 0,
            "total_failed": 0,
            "mode": "sequential",
        }

        for symbol in symbols:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Starting collection for {symbol}")
            self.logger.info(f"{'='*60}")

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
            "storage_backend": "sqlite" if self.use_sqlite else "pickle",
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

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Starting parallel collection for {len(symbols)} symbols")
        self.logger.info(f"{'='*60}\n")

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
                            symbol, trade_date, cache_result=not self.use_sqlite
                        )
                        self.stats["total_calls"] += 1
                        call_count += 1

                        is_valid, reason = self.validate_options_data(options_data, symbol, trade_date)

                        if is_valid:
                            stored = self._store_data(symbol, trade_date, options_data)
                            if stored:
                                self.stats["successful_calls"] += 1
                                overall_summary["symbol_summaries"][symbol]["completed_dates"] += 1
                                self.logger.info(f"[{symbol}] Stored {len(options_data)} options for {trade_date}")
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
                        if self.use_sqlite:
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
        if self.use_sqlite:
            summary["final_db_stats"] = self.db.get_database_stats()
        else:
            summary["final_cache_stats"] = self._get_legacy_cache_info()

        # Log final status
        self.logger.info(f"\n{'='*60}")
        self.logger.info("COLLECTION COMPLETE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Mode: {summary.get('mode', 'sequential')}")
        self.logger.info(f"Total API calls: {summary['total_api_calls']}")
        self.logger.info(f"Successful: {summary['total_successful']}")
        self.logger.info(f"Failed: {summary['total_failed']}")

        if self.use_sqlite:
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
        if self.use_sqlite:
            stats = self.db.get_database_stats()
            progress = self.db.get_collection_progress(symbol)

            return {
                "storage": "sqlite",
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
    """Example usage of the historical collector with SQLite backend."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("historical_collection.log"),
            logging.StreamHandler(),
        ],
    )

    # Initialize collector with SQLite backend (recommended)
    collector = HistoricalOptionsCollector(
        db_path=".cache/options_historical.db",
        use_sqlite=True,
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
