"""
Historical Options Data Collection Service

Systematically collects historical options chains from Alpha Vantage API
with rate limiting, progress tracking, and resume capability.
"""

from src.cache.unified_cache import UnifiedCacheManager
from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
import asyncio
import logging
import pandas as pd
import datetime
from typing import List, Dict
import json
import time
import sys
import os

# Use date_utils for standardized datetime operations
from src.utils.date_utils import (
    now_iso,
    today_str
)

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HistoricalOptionsCollector:
    """
    Service to systematically collect historical options data.

    Features:
    - Rate-limited API calls (75/min for Entry Premium)
    - Progress tracking and resume capability
    - Error handling and retry logic
    - Multiple symbol support (SPY, SPX, QQQ)
    - Data quality validation
    """

    def __init__(self, cache_manager=None, rate_limit_per_minute=70):
        """
        Initialize historical data collector.

        Args:
            cache_manager: UnifiedCacheManager instance
            rate_limit_per_minute: API calls per minute (buffer below 75 limit)
        """
        self.cache = cache_manager or UnifiedCacheManager()
        self.client = AlphaVantageGEXClient(cache_manager=self.cache)
        self.rate_limit = rate_limit_per_minute
        self.call_interval = 60.0 / rate_limit_per_minute  # Seconds between calls

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Progress tracking
        self.progress_file = self.cache.base_dir / "collection_progress.json"
        self.stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'cached_hits': 0,
            'start_time': None,
            'last_call_time': None
        }

    def get_trading_dates(self, start_date, end_date):
        """
        Generate list of trading dates between start and end dates.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            List of trading date strings
        """
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

        trading_dates = []
        current = start

        while current <= end:
            # Skip weekends (basic trading day filter)
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                trading_dates.append(current.strftime('%Y-%m-%d'))
            current += datetime.timedelta(days=1)

        return trading_dates

    def load_progress(self):
        """Load collection progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")

        return {
            'completed_dates': [],
            'failed_dates': [],
            'current_symbol': None,
            'symbols_completed': []
        }

    def save_progress(self, progress: Dict):
        """Save collection progress to file."""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")

    def validate_options_data(self, data: pd.DataFrame, symbol, date):
        """
        Validate collected options data quality.

        Args:
            data: Options chain DataFrame
            symbol: Symbol being validated
            date: Date being validated

        Returns:
            (is_valid, reason) tuple
        """
        if data.empty:
            return False, "Empty DataFrame"

        required_columns = ['strike', 'expiration',
                            'bid', 'ask', 'type', 'open_interest']
        missing_cols = [
            col for col in required_columns if col not in data.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"

        # Check for reasonable number of strikes
        if len(data) < 10:
            return False, f"Too few strikes: {len(data)}"

        # Check for reasonable strike range
        strikes = data['strike'].values
        if len(strikes) > 0:
            strike_range = max(strikes) - min(strikes)
            if strike_range < 10:  # Less than $10 range seems unreasonable
                return False, f"Strike range too narrow: ${strike_range}"

        return True, "Valid"

    async def collect_symbol_historical(self, symbol, start_date, end_date):
        """
        Collect historical options data for a single symbol.

        Args:
            symbol: Symbol to collect (SPY, SPX, QQQ)
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD

        Returns:
            Collection summary dictionary
        """
        self.logger.info(
            f"Starting historical collection for {symbol}: {start_date} to {end_date}")

        trading_dates = self.get_trading_dates(start_date, end_date)
        progress = self.load_progress()

        # Filter out already completed dates
        remaining_dates = [
            d for d in trading_dates if d not in progress.get('completed_dates', [])]

        self.logger.info(
            f"Found {len(trading_dates)} trading dates, {len(remaining_dates)} remaining")

        summary = {
            'symbol': symbol,
            'total_dates': len(trading_dates),
            'completed_dates': 0,
            'failed_dates': 0,
            'skipped_dates': 0,
            'start_time': now_iso()
        }

        self.stats['start_time'] = now_iso()

        for i, trade_date in enumerate(remaining_dates):
            try:
                # Rate limiting
                if self.stats['last_call_time']:
                    elapsed = time.time() - self.stats['last_call_time']
                    if elapsed < self.call_interval:
                        wait_time = self.call_interval - elapsed
                        self.logger.info(
                            f"Rate limiting: waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)

                # Check if we already have cached options data
                cached_data = self.cache.get_options_data(symbol, trade_date)

                if cached_data is not None and not cached_data.empty:
                    self.logger.info(
                        f"Using cached options data for {symbol} {trade_date} ({len(cached_data)} options)")
                    self.stats['cached_hits'] += 1
                    summary['skipped_dates'] += 1

                    # Still validate cached data quality
                    is_valid, reason = self.validate_options_data(
                        cached_data, symbol, trade_date)
                    if not is_valid:
                        self.logger.warning(
                            f"Cached data quality issue for {trade_date}: {reason}")

                else:
                    # Make API call
                    self.logger.info(
                        f"Fetching {symbol} options for {trade_date} ({i+1}/{len(remaining_dates)})")

                    self.stats['last_call_time'] = time.time()
                    options_data = self.client.fetch_historical_options(
                        symbol, trade_date)
                    self.stats['total_calls'] += 1

                    # Validate data quality
                    is_valid, reason = self.validate_options_data(
                        options_data, symbol, trade_date)

                    if is_valid:
                        # Store in cache using proper method
                        cache_stored = self.cache.store_options_data(
                            symbol, trade_date, options_data)

                        if cache_stored:
                            self.stats['successful_calls'] += 1
                            summary['completed_dates'] += 1
                            progress['completed_dates'].append(trade_date)
                            self.logger.info(
                                f"✅ Successfully collected and cached {len(options_data)} options for {trade_date}")
                        else:
                            self.logger.warning(
                                f"⚠️ Data collected but cache storage failed for {trade_date}")
                            self.stats['successful_calls'] += 1
                            summary['completed_dates'] += 1
                            progress['completed_dates'].append(trade_date)
                    else:
                        self.stats['failed_calls'] += 1
                        summary['failed_dates'] += 1
                        progress['failed_dates'].append(trade_date)
                        self.logger.warning(
                            f"❌ Invalid data for {trade_date}: {reason}")

                # Save progress every 10 successful calls
                if (summary['completed_dates'] + summary['skipped_dates']) % 10 == 0:
                    progress['current_symbol'] = symbol
                    self.save_progress(progress)
                    self.log_status(summary)

            except Exception as e:
                self.logger.error(
                    f"Error collecting {symbol} {trade_date}: {e}")
                summary['failed_dates'] += 1
                progress['failed_dates'].append(trade_date)

        # Final progress save
        progress['symbols_completed'].append(symbol)
        progress['current_symbol'] = None
        self.save_progress(progress)

        summary['end_time'] = now_iso()
        self.logger.info(f"Completed {symbol}: {summary}")

        return summary

    def log_status(self, summary: Dict):
        """Log current collection status with cache statistics."""
        total_processed = summary['completed_dates'] + \
            summary['skipped_dates'] + summary['failed_dates']
        success_rate = (summary['completed_dates'] /
                        total_processed * 100) if total_processed > 0 else 0
        cache_hit_rate = (
            self.stats['cached_hits'] / total_processed * 100) if total_processed > 0 else 0

        self.logger.info(f"Progress: {total_processed}/{summary['total_dates']} dates "
                         f"({success_rate:.1f}% success rate)")
        self.logger.info(f"API Stats: {self.stats['total_calls']} calls, "
                         f"{self.stats['cached_hits']} cache hits ({cache_hit_rate:.1f}% cache hit rate)")

        # Get cache statistics
        cache_summary = self.cache.get_options_cache_summary()
        if cache_summary:
            total_cached_options = sum(cache_summary.get(
                'options_count_by_symbol', {}).values())
            self.logger.info(f"Cache: {len(cache_summary.get('cached_dates', []))} dates, "
                             f"{total_cached_options:,} total options cached")

    def get_cache_storage_info(self):
        """Get detailed cache storage information."""
        cache_summary = self.cache.get_options_cache_summary()

        # Calculate storage estimates
        cache_dir = self.cache.base_dir / "options"
        total_size = 0
        file_count = 0

        if cache_dir.exists():
            for file_path in cache_dir.rglob("*.pkl"):
                try:
                    total_size += file_path.stat().st_size
                    file_count += 1
                except OSError:
                    pass

        return {
            'cache_summary': cache_summary,
            'storage_mb': total_size / (1024 * 1024),
            'file_count': file_count,
            'avg_file_size_kb': (total_size / file_count / 1024) if file_count > 0 else 0
        }

    async def collect_multi_symbol_historical(self, symbols: List[str], start_date, end_date):
        """
        Collect historical data for multiple symbols.

        Args:
            symbols: List of symbols to collect
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD

        Returns:
            Complete collection summary
        """
        overall_summary = {
            'symbols': symbols,
            'start_date': start_date,
            'end_date': end_date,
            'collection_start': now_iso(),
            'symbol_summaries': {},
            'total_api_calls': 0,
            'total_successful': 0,
            'total_failed': 0
        }

        for symbol in symbols:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Starting collection for {symbol}")
            self.logger.info(f"{'='*50}")

            symbol_summary = await self.collect_symbol_historical(symbol, start_date, end_date)
            overall_summary['symbol_summaries'][symbol] = symbol_summary
            overall_summary['total_api_calls'] += self.stats['total_calls']
            overall_summary['total_successful'] += self.stats['successful_calls']
            overall_summary['total_failed'] += self.stats['failed_calls']

            # Reset stats for next symbol
            self.stats = {k: 0 for k in self.stats if k.endswith('_calls')}

        overall_summary['collection_end'] = now_iso()

        # Add final cache statistics
        cache_info = self.get_cache_storage_info()
        overall_summary['final_cache_stats'] = cache_info

        # Log final cache status
        self.logger.info(f"Final cache statistics:")
        self.logger.info(
            f"  Storage: {cache_info['storage_mb']:.1f} MB in {cache_info['file_count']} files")
        self.logger.info(
            f"  Average file size: {cache_info['avg_file_size_kb']:.1f} KB")
        if cache_info['cache_summary']:
            total_options = sum(cache_info['cache_summary'].get(
                'options_count_by_symbol', {}).values())
            self.logger.info(f"  Total options cached: {total_options:,}")

        # Save final summary
        summary_file = self.cache.base_dir / "historical_collection_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(overall_summary, f, indent=2)

        self.logger.info(
            f"Collection complete! Summary saved to {summary_file}")
        return overall_summary


async def main():
    """Example usage of the historical collector."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('historical_collection.log'),
            logging.StreamHandler()
        ]
    )

    collector = HistoricalOptionsCollector()

    # Start with recent data (last 30 days) for testing
    end_date = today_str()
    start_date = (datetime.date.today() -
                  datetime.timedelta(days=30)).strftime('%Y-%m-%d')

    # Start with SPY only for initial testing
    symbols = ['SPY']

    summary = await collector.collect_multi_symbol_historical(symbols, start_date, end_date)
    print(f"Collection completed: {summary}")


if __name__ == "__main__":
    asyncio.run(main())
