"""Concurrent GEX Processing System High-performance concurrent processing for multi-symbol, multi-date GEX
calculations.

Issue #180: Migrated to SQLiteOptionsManager for options data.
"""

import datetime
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple

import pandas as pd

from src.utils.config_manager import get_config
from src.utils.date_utils import now_iso

from .gex_cache_manager import GEXCacheManager
from .sqlite_options_manager import SQLiteOptionsManager
from .unified_cache import UnifiedCacheManager

logger = logging.getLogger(__name__)


def _get_optimal_workers(max_workers: Optional[int] = None) -> int:
    """Calculate optimal worker count based on CPU cores.

    Args:
        max_workers: Optional override for max workers

    Returns:
        Optimal number of workers (between 2 and 8)
    """
    if max_workers is not None:
        return max_workers

    cpu_count = os.cpu_count() or 4
    # Use CPU count - 1 to leave headroom, bounded between 2 and 8
    return max(2, min(8, cpu_count - 1))


class ConcurrentGEXProcessor:
    """Concurrent processor for efficient GEX calculation and caching.

    Handles:
    - Multi-symbol parallel processing
    - Date range processing with optimal threading
    - Memory-efficient batch operations
    - Progress tracking and error handling
    """

    def __init__(self, max_workers: Optional[int] = None, unified_cache_manager=None, sqlite_options_manager=None):
        """Initialize concurrent processor.

        Args:
            max_workers: Maximum concurrent threads (auto-calculated if None, or from config)
            unified_cache_manager: Legacy cache manager (deprecated for options)
            sqlite_options_manager: SQLiteOptionsManager for options data (preferred)
        """
        # Load configuration from centralized config system
        config = get_config()

        # Get defaults from data_sources_config.yaml
        config_max_workers = config.get("data_sources.concurrent_processor.max_workers", None)
        self.future_timeout = config.get("data_sources.concurrent_processor.future_timeout", 300)
        self.log_interval = config.get("data_sources.concurrent_processor.log_interval", 10)

        # Use adaptive worker calculation if not explicitly overridden
        if max_workers is not None:
            self.max_workers = max_workers
        elif config_max_workers is not None:
            self.max_workers = config_max_workers
        else:
            self.max_workers = _get_optimal_workers()

        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # Issue #180: Use SQLiteOptionsManager as primary options data source
        self.sqlite_options = sqlite_options_manager or SQLiteOptionsManager()

        # Legacy cache manager (still used for GEX cache)
        if unified_cache_manager:
            self.cache_manager = unified_cache_manager
            self.gex_cache = (
                unified_cache_manager.gex_cache if hasattr(unified_cache_manager, "gex_cache") else GEXCacheManager()
            )
        else:
            self.cache_manager = UnifiedCacheManager()
            self.gex_cache = GEXCacheManager()

        logger.info(f"Concurrent GEX Processor initialized with {self.max_workers} workers")

    def process_symbol_date_range(self, symbol, start_date, end_date, force_recalculate: bool = False):
        """Process GEX for entire date range concurrently.

        Args:
            symbol: Stock symbol (SPY, SPX, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            force_recalculate: Force recalculation even if cached

        Returns:
            Dict with processing results and statistics
        """
        try:
            # Get trading dates (approximate - would need market calendar for exact dates)
            trading_dates = self._get_trading_dates(start_date, end_date)

            logger.info(f"Processing GEX for {symbol}: {len(trading_dates)} trading dates")

            # Submit all calculations concurrently
            futures = {}
            for date in trading_dates:
                future = self.executor.submit(self._process_single_date, symbol, date, force_recalculate)
                futures[future] = date

            # Collect results with progress tracking
            results = {}
            errors = {}
            processed_count = 0

            for future in as_completed(futures):
                date = futures[future]
                processed_count += 1

                try:
                    # Configurable timeout per calculation
                    result = future.result(timeout=self.future_timeout)
                    results[date] = result

                    if processed_count % self.log_interval == 0:  # Progress logging
                        logger.info(f"Progress: {processed_count}/{len(trading_dates)} dates processed")

                except Exception as e:
                    errors[date] = str(e)
                    logger.error(f"GEX calculation failed for {symbol} {date}: {e}")

            # Summary statistics
            successful = len(results)
            failed = len(errors)
            cache_hits = sum(1 for r in results.values() if r and r.get("cache_hit", False))

            summary = {
                "symbol": symbol,
                "date_range": f"{start_date} to {end_date}",
                "total_dates": len(trading_dates),
                "successful": successful,
                "failed": failed,
                "cache_hits": cache_hits,
                "new_calculations": successful - cache_hits,
                "errors": errors,
                "processing_time": now_iso(),
            }

            logger.info(f"Completed {symbol} range processing: {successful}/{len(trading_dates)} successful")
            return summary

        except Exception as e:
            logger.error(f"Failed to process date range for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "processing_time": now_iso()}

    def process_multi_symbol(self, symbols: List[str], trading_date, force_recalculate: bool = False):
        """Process multiple symbols for same date concurrently.

        Args:
            symbols: List of stock symbols
            trading_date: Trading date (YYYY-MM-DD)
            force_recalculate: Force recalculation even if cached

        Returns:
            Dict with processing results by symbol
        """
        try:
            logger.info(f"Processing {len(symbols)} symbols for {trading_date}")

            # Submit all symbols concurrently
            futures = {}
            for symbol in symbols:
                future = self.executor.submit(self._process_single_date, symbol, trading_date, force_recalculate)
                futures[future] = symbol

            # Collect results
            results = {}
            errors = {}

            for future in as_completed(futures):
                symbol = futures[future]

                try:
                    result = future.result(timeout=self.future_timeout)
                    results[symbol] = result

                except Exception as e:
                    errors[symbol] = str(e)
                    logger.error(f"GEX calculation failed for {symbol} {trading_date}: {e}")

            # Summary
            summary = {
                "trading_date": trading_date,
                "total_symbols": len(symbols),
                "successful": len(results),
                "failed": len(errors),
                "results": results,
                "errors": errors,
                "processing_time": now_iso(),
            }

            logger.info(f"Multi-symbol processing complete: {len(results)}/{len(symbols)} successful")
            return summary

        except Exception as e:
            logger.error(f"Failed multi-symbol processing for {trading_date}: {e}")
            return {"trading_date": trading_date, "error": str(e), "processing_time": now_iso()}

    def batch_process_requests(self, requests: List[Tuple[str, str]], force_recalculate: bool = False):
        """Efficient batch processing of multiple (symbol, date) requests.

        Args:
            requests: List of (symbol, trading_date) tuples
            force_recalculate: Force recalculation even if cached

        Returns:
            Dict with batch processing results
        """
        try:
            logger.info(f"Batch processing {len(requests)} GEX requests")

            # Submit all requests concurrently
            futures = {}
            for symbol, trading_date in requests:
                future = self.executor.submit(self._process_single_date, symbol, trading_date, force_recalculate)
                futures[future] = (symbol, trading_date)

            # Collect results
            results = {}
            errors = {}
            processed = 0

            for future in as_completed(futures):
                symbol, trading_date = futures[future]
                key = f"{symbol}_{trading_date}"
                processed += 1

                try:
                    result = future.result(timeout=self.future_timeout)
                    results[key] = result

                    if processed % (self.log_interval * 2.5) == 0:  # Progress logging (batch)
                        logger.info(f"Batch progress: {processed}/{len(requests)} requests processed")

                except Exception as e:
                    errors[key] = str(e)
                    logger.error(f"Batch request failed for {symbol} {trading_date}: {e}")

            # Summary statistics
            cache_hits = sum(1 for r in results.values() if r and r.get("cache_hit", False))

            summary = {
                "total_requests": len(requests),
                "successful": len(results),
                "failed": len(errors),
                "cache_hits": cache_hits,
                "new_calculations": len(results) - cache_hits,
                "results": results,
                "errors": errors,
                "processing_time": now_iso(),
            }

            logger.info(f"Batch processing complete: {len(results)}/{len(requests)} successful")
            return summary

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {"error": str(e), "processing_time": now_iso()}

    def _process_single_date(self, symbol, trading_date, force_recalculate: bool = False):
        """Process GEX for single symbol/date combination.

        Internal method used by concurrent processing. Issue #180: Now uses SQLiteOptionsManager as primary options
        source.
        """
        try:
            # Check cache first (unless forcing recalculation)
            if not force_recalculate:
                cached_gex = self.gex_cache.get_gex_summary(symbol, trading_date)
                if cached_gex:
                    return {"status": "success", "cache_hit": True, "data": cached_gex}

            # Get options data from SQLite (Issue #180)
            options_data = self.sqlite_options.get_options_chain(symbol, trading_date)

            if options_data is None or options_data.empty:
                logger.warning(f"No options data available for {symbol} {trading_date}")
                return {"status": "no_data", "cache_hit": False, "message": "No options data available"}

            # Calculate GEX using existing GEX calculation engine
            gex_results = self._calculate_gex_with_cache(symbol, trading_date, options_data)

            return {"status": "success", "cache_hit": False, "data": gex_results, "calculated": True}

        except Exception as e:
            logger.error(f"Single date processing failed for {symbol} {trading_date}: {e}")
            return {"status": "error", "cache_hit": False, "error": str(e)}

    def _calculate_gex_with_cache(self, symbol, trading_date, options_data: pd.DataFrame):
        """Calculate GEX and store in cache.

        Uses existing GEX calculation engine.
        """
        try:
            # Import GEX calculation engine
            from gex_db_infrastructure.gex.live_gex_interface import LiveGEXInterface

            gex_interface = LiveGEXInterface()

            # Calculate GEX metrics
            gex_results = gex_interface.calculate_gex_for_symbol(
                symbol=symbol,
                trading_date=trading_date,
                spot_price=None,  # Auto-detect from data
                options_data=options_data,  # Pass the live cached data
            )

            if gex_results and "status" in gex_results and gex_results["status"] == "success":
                # Extract components for caching
                gex_summary = gex_results.get("metrics", {})

                # Add metadata
                gex_summary.update(
                    {
                        "symbol": symbol,
                        "trading_date": trading_date,
                        "calculation_timestamp": now_iso(),
                        "calculation_metadata": {
                            "options_contracts_processed": len(options_data),
                            "calculation_method": "sample_data_gex_interface",
                            "calculation_duration_ms": gex_results.get("calculation_time_ms", 0),
                        },
                    }
                )

                # Store in GEX cache
                success = self.gex_cache.store_gex_calculation(symbol, trading_date, gex_summary)

                if success:
                    logger.debug(f"Cached GEX calculation for {symbol} {trading_date}")

                return gex_summary
            else:
                raise Exception(f"GEX calculation failed: {gex_results}")

        except Exception as e:
            logger.error(f"GEX calculation with cache failed for {symbol} {trading_date}: {e}")
            raise

    def _get_trading_dates(self, start_date, end_date):
        """Generate list of trading dates between start and end.

        Simplified approximation - excludes weekends but not holidays.
        """
        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d")

            dates = []
            current = start

            while current <= end:
                # Skip weekends (Saturday=5, Sunday=6)
                if current.weekday() < 5:
                    dates.append(current.strftime("%Y-%m-%d"))
                current += datetime.timedelta(days=1)

            return dates

        except Exception as e:
            logger.error(f"Error generating trading dates: {e}")
            return []

    def get_processing_stats(self):
        """Get processor performance statistics."""
        return {
            "max_workers": self.max_workers,
            "executor_class": type(self.executor).__name__,
            "cache_manager_type": type(self.cache_manager).__name__,
            "active_threads": self.executor._threads if hasattr(self.executor, "_threads") else "unknown",
        }

    def shutdown(self, wait: bool = True):
        """Shutdown the concurrent processor."""
        logger.info("Shutting down concurrent GEX processor")
        self.executor.shutdown(wait=wait)
