"""
Concurrent GEX Processing System
High-performance concurrent processing for multi-symbol, multi-date GEX calculations.
"""

import logging
import datetime
import pandas as pd
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.date_utils import now_iso

from .gex_cache_manager import GEXCacheManager
from .unified_cache import UnifiedCacheManager

logger = logging.getLogger(__name__)


class ConcurrentGEXProcessor:
    """
    Concurrent processor for efficient GEX calculation and caching.

    Handles:
    - Multi-symbol parallel processing
    - Date range processing with optimal threading
    - Memory-efficient batch operations
    - Progress tracking and error handling
    """

    def __init__(self, max_workers: int = 4, unified_cache_manager=None):
        """
        Initialize concurrent processor.

        Args:
            max_workers: Maximum concurrent threads
            unified_cache_manager: Existing cache manager (optional)
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Use provided cache manager or create new one
        if unified_cache_manager:
            self.cache_manager = unified_cache_manager
            self.gex_cache = unified_cache_manager.gex_cache if hasattr(
                unified_cache_manager, 'gex_cache') else GEXCacheManager()
        else:
            self.cache_manager = UnifiedCacheManager()
            self.gex_cache = GEXCacheManager()

        logger.info(
            f"Concurrent GEX Processor initialized with {max_workers} workers")

    def process_symbol_date_range(self,
                                  symbol,
                                  start_date,
                                  end_date,
                                  force_recalculate: bool = False):
        """
        Process GEX for entire date range concurrently.

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

            logger.info(
                f"Processing GEX for {symbol}: {len(trading_dates)} trading dates")

            # Submit all calculations concurrently
            futures = {}
            for date in trading_dates:
                future = self.executor.submit(
                    self._process_single_date,
                    symbol, date, force_recalculate
                )
                futures[future] = date

            # Collect results with progress tracking
            results = {}
            errors = {}
            processed_count = 0

            for future in as_completed(futures):
                date = futures[future]
                processed_count += 1

                try:
                    # 5 minute timeout per calculation
                    result = future.result(timeout=300)
                    results[date] = result

                    if processed_count % 10 == 0:  # Progress logging
                        logger.info(
                            f"Progress: {processed_count}/{len(trading_dates)} dates processed")

                except Exception as e:
                    errors[date] = str(e)
                    logger.error(
                        f"GEX calculation failed for {symbol} {date}: {e}")

            # Summary statistics
            successful = len(results)
            failed = len(errors)
            cache_hits = sum(1 for r in results.values()
                             if r and r.get('cache_hit', False))

            summary = {
                'symbol': symbol,
                'date_range': f"{start_date} to {end_date}",
                'total_dates': len(trading_dates),
                'successful': successful,
                'failed': failed,
                'cache_hits': cache_hits,
                'new_calculations': successful - cache_hits,
                'errors': errors,
                'processing_time': now_iso()
            }

            logger.info(
                f"Completed {symbol} range processing: {successful}/{len(trading_dates)} successful")
            return summary

        except Exception as e:
            logger.error(f"Failed to process date range for {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'processing_time': now_iso()
            }

    def process_multi_symbol(self,
                             symbols: List[str],
                             trading_date,
                             force_recalculate: bool = False):
        """
        Process multiple symbols for same date concurrently.

        Args:
            symbols: List of stock symbols
            trading_date: Trading date (YYYY-MM-DD)
            force_recalculate: Force recalculation even if cached

        Returns:
            Dict with processing results by symbol
        """
        try:
            logger.info(
                f"Processing {len(symbols)} symbols for {trading_date}")

            # Submit all symbols concurrently
            futures = {}
            for symbol in symbols:
                future = self.executor.submit(
                    self._process_single_date,
                    symbol, trading_date, force_recalculate
                )
                futures[future] = symbol

            # Collect results
            results = {}
            errors = {}

            for future in as_completed(futures):
                symbol = futures[future]

                try:
                    result = future.result(timeout=300)
                    results[symbol] = result

                except Exception as e:
                    errors[symbol] = str(e)
                    logger.error(
                        f"GEX calculation failed for {symbol} {trading_date}: {e}")

            # Summary
            summary = {
                'trading_date': trading_date,
                'total_symbols': len(symbols),
                'successful': len(results),
                'failed': len(errors),
                'results': results,
                'errors': errors,
                'processing_time': now_iso()
            }

            logger.info(
                f"Multi-symbol processing complete: {len(results)}/{len(symbols)} successful")
            return summary

        except Exception as e:
            logger.error(
                f"Failed multi-symbol processing for {trading_date}: {e}")
            return {
                'trading_date': trading_date,
                'error': str(e),
                'processing_time': now_iso()
            }

    def batch_process_requests(self,
                               requests: List[Tuple[str, str]],
                               force_recalculate: bool = False):
        """
        Efficient batch processing of multiple (symbol, date) requests.

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
                future = self.executor.submit(
                    self._process_single_date,
                    symbol, trading_date, force_recalculate
                )
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
                    result = future.result(timeout=300)
                    results[key] = result

                    if processed % 25 == 0:  # Progress logging
                        logger.info(
                            f"Batch progress: {processed}/{len(requests)} requests processed")

                except Exception as e:
                    errors[key] = str(e)
                    logger.error(
                        f"Batch request failed for {symbol} {trading_date}: {e}")

            # Summary statistics
            cache_hits = sum(1 for r in results.values()
                             if r and r.get('cache_hit', False))

            summary = {
                'total_requests': len(requests),
                'successful': len(results),
                'failed': len(errors),
                'cache_hits': cache_hits,
                'new_calculations': len(results) - cache_hits,
                'results': results,
                'errors': errors,
                'processing_time': now_iso()
            }

            logger.info(
                f"Batch processing complete: {len(results)}/{len(requests)} successful")
            return summary

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {
                'error': str(e),
                'processing_time': now_iso()
            }

    def _process_single_date(self, symbol, trading_date, force_recalculate: bool = False):
        """
        Process GEX for single symbol/date combination.
        Internal method used by concurrent processing.
        """
        try:
            # Check cache first (unless forcing recalculation)
            if not force_recalculate:
                cached_gex = self.gex_cache.get_gex_summary(
                    symbol, trading_date)
                if cached_gex:
                    return {
                        'status': 'success',
                        'cache_hit': True,
                        'data': cached_gex
                    }

            # Get options data
            options_data = self.cache_manager.get_options_data(
                symbol, trading_date)

            if options_data is None or options_data.empty:
                logger.warning(
                    f"No options data available for {symbol} {trading_date}")
                return {
                    'status': 'no_data',
                    'cache_hit': False,
                    'message': 'No options data available'
                }

            # Calculate GEX using existing GEX calculation engine
            gex_results = self._calculate_gex_with_cache(
                symbol, trading_date, options_data)

            return {
                'status': 'success',
                'cache_hit': False,
                'data': gex_results,
                'calculated': True
            }

        except Exception as e:
            logger.error(
                f"Single date processing failed for {symbol} {trading_date}: {e}")
            return {
                'status': 'error',
                'cache_hit': False,
                'error': str(e)
            }

    def _calculate_gex_with_cache(self, symbol, trading_date, options_data: pd.DataFrame):
        """
        Calculate GEX and store in cache.
        Uses existing GEX calculation engine.
        """
        try:
            # Import GEX calculation engine
            from src.gex.sample_data_gex import SampleDataGEXInterface

            gex_interface = SampleDataGEXInterface()

            # Calculate GEX metrics
            gex_results = gex_interface.calculate_gex_metrics(
                options_data,
                symbol=symbol,
                trading_date=trading_date
            )

            if gex_results and 'status' in gex_results and gex_results['status'] == 'success':
                # Extract components for caching
                gex_summary = gex_results.get('metrics', {})

                # Add metadata
                gex_summary.update({
                    'symbol': symbol,
                    'trading_date': trading_date,
                    'calculation_timestamp': now_iso(),
                    'calculation_metadata': {
                        'options_contracts_processed': len(options_data),
                        'calculation_method': 'sample_data_gex_interface',
                        'calculation_duration_ms': gex_results.get('calculation_time_ms', 0)
                    }
                })

                # Store in GEX cache
                success = self.gex_cache.store_gex_calculation(
                    symbol, trading_date, gex_summary
                )

                if success:
                    logger.debug(
                        f"Cached GEX calculation for {symbol} {trading_date}")

                return gex_summary
            else:
                raise Exception(f"GEX calculation failed: {gex_results}")

        except Exception as e:
            logger.error(
                f"GEX calculation with cache failed for {symbol} {trading_date}: {e}")
            raise

    def _get_trading_dates(self, start_date, end_date):
        """
        Generate list of trading dates between start and end.
        Simplified approximation - excludes weekends but not holidays.
        """
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d')

            dates = []
            current = start

            while current <= end:
                # Skip weekends (Saturday=5, Sunday=6)
                if current.weekday() < 5:
                    dates.append(current.strftime('%Y-%m-%d'))
                current += datetime.timedelta(days=1)

            return dates

        except Exception as e:
            logger.error(f"Error generating trading dates: {e}")
            return []

    def get_processing_stats(self):
        """Get processor performance statistics."""
        return {
            'max_workers': self.max_workers,
            'executor_class': type(self.executor).__name__,
            'cache_manager_type': type(self.cache_manager).__name__,
            'active_threads': self.executor._threads if hasattr(self.executor, '_threads') else 'unknown'
        }

    def shutdown(self, wait: bool = True):
        """Shutdown the concurrent processor."""
        logger.info("Shutting down concurrent GEX processor")
        self.executor.shutdown(wait=wait)
