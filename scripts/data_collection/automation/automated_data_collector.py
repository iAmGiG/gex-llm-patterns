#!/usr/bin/env python3
"""
Automated Historical Data Collection System

Collects options data from Alpha Vantage (25/day limit) and
stock data from Polygon.io (7,200/day) with intelligent scheduling.

Designed to run continuously, respecting API limits.
"""

from gex.gex_calculator import GEXCalculator
from cache.unified_cache import UnifiedCacheManager
from data_sources.historical_collector import HistoricalOptionsCollector
from data_sources.polygon_client import PolygonClient
from data_sources.alpha_vantage_gex import AlphaVantageGEXClient
import sys
import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Set
import time

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / 'src'))


class AutomatedDataCollector:
    """
    Comprehensive automated data collection system.

    Features:
    - Collects options from Alpha Vantage (25/day)
    - Collects stock data from Polygon.io (7,200/day)
    - Auto-calculates and caches GEX
    - Tracks progress and resumes from failures
    - Expands ticker universe intelligently
    """

    def __init__(self):
        self.cache = UnifiedCacheManager()
        self.options_client = AlphaVantageGEXClient(cache_manager=self.cache)
        self.polygon_client = PolygonClient()  # Will need API key
        self.gex_calculator = GEXCalculator()

        # Progress tracking
        self.progress_file = self.cache.base_dir / "automated_collection_progress.json"
        self.progress = self.load_progress()

        # Collection priorities
        self.options_priority = [
            # Core ETFs
            'SPY', 'QQQ', 'IWM', 'DIA', 'TLT', 'GLD',
            # Sector ETFs
            'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLP', 'XLY', 'XLU', 'XLB',
            # Volatility
            'VXX', 'UVXY', 'SVXY',
            # Bonds
            'HYG', 'LQD', 'TIP', 'IEF', 'SHY',
            # International
            'EEM', 'EFA', 'FXI', 'EWZ', 'VEA'
        ]

        # Stock priorities (will expand based on ETF holdings)
        self.stock_priority = self._build_stock_universe()

        # API limits
        self.options_daily_limit = 25
        self.stocks_per_minute = 5

        # Collection dates
        self.start_date = '2008-01-01'  # Alpha Vantage historical limit
        self.end_date = date.today().strftime('%Y-%m-%d')

        self.logger = logging.getLogger(__name__)

    def load_progress(self) -> Dict:
        """Load collection progress."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load progress: {e}")

        return {
            'options_collected': {},  # symbol -> [dates]
            'stocks_collected': {},   # symbol -> date_range
            'gex_calculated': {},     # symbol_date -> True
            'last_options_collection': None,
            'last_stock_collection': None,
            'options_calls_today': 0,
            'options_date_reset': date.today().isoformat()
        }

    def save_progress(self):
        """Save collection progress."""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")

    def _build_stock_universe(self) -> List[str]:
        """Build comprehensive stock universe for collection."""
        # Start with major indices components
        stock_universe = []

        # S&P 500 top components (abbreviated for demo)
        sp500_top = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B',
            'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'DIS', 'ADBE',
            'NFLX', 'CRM', 'CMCSA', 'PFE', 'TMO', 'CSCO', 'PEP', 'ABT', 'CVX',
            'ABBV', 'NKE', 'WMT', 'ACN', 'MRK', 'COST', 'T', 'DHR', 'VZ', 'NEE'
        ]

        # QQQ top holdings
        qqq_top = [
            'MSFT', 'AAPL', 'AMZN', 'NVDA', 'META', 'GOOGL', 'GOOG', 'TSLA',
            'AVGO', 'PEP', 'COST', 'TMUS', 'CSCO', 'ADBE', 'TXN', 'CMCSA', 'NFLX',
            'QCOM', 'INTC', 'AMD', 'INTU', 'AMGN', 'HON', 'PYPL', 'SBUX'
        ]

        # IWM top holdings (small cap)
        iwm_top = [
            'SMCI', 'CHRD', 'MDB', 'FTAI', 'KVUE', 'TMDX', 'RVMD', 'ATI',
            'MTDR', 'CG', 'SFM', 'RBC', 'VIRT', 'XPEL', 'AIT', 'PIPR'
        ]

        # Combine and deduplicate
        all_stocks = list(set(sp500_top + qqq_top + iwm_top))

        # Add high-volume options stocks
        options_popular = [
            'GME', 'AMC', 'BB', 'PLTR', 'F', 'GE', 'BAC', 'WFC', 'C',
            'SOFI', 'LCID', 'RIVN', 'NIO', 'COIN', 'MARA', 'RIOT'
        ]

        all_stocks.extend(options_popular)

        return list(set(all_stocks))

    async def collect_options_batch(self) -> int:
        """
        Collect one batch of options data (respecting 25/day limit).
        Returns number of successful collections.
        """
        # Check if we need to reset daily counter
        today = date.today().isoformat()
        if self.progress.get('options_date_reset') != today:
            self.progress['options_calls_today'] = 0
            self.progress['options_date_reset'] = today
            self.save_progress()

        # Check daily limit
        remaining_calls = self.options_daily_limit - \
            self.progress['options_calls_today']
        if remaining_calls <= 0:
            self.logger.info(
                "Daily options API limit reached. Will resume tomorrow.")
            return 0

        collected = 0

        # Generate trading dates from start
        all_dates = self._get_trading_dates(self.start_date, self.end_date)

        for symbol in self.options_priority:
            if collected >= remaining_calls:
                break

            # Get uncollected dates for this symbol
            collected_dates = set(
                self.progress['options_collected'].get(symbol, []))
            remaining_dates = [
                d for d in all_dates if d not in collected_dates]

            if not remaining_dates:
                continue

            # Collect oldest first
            for date_str in remaining_dates[:remaining_calls - collected]:
                try:
                    # Check cache first
                    cached = self.cache.get_options_data(symbol, date_str)
                    if cached is not None and not cached.empty:
                        self.logger.info(
                            f"Using cached {symbol} options for {date_str}")
                    else:
                        # Fetch from API
                        self.logger.info(
                            f"Fetching {symbol} options for {date_str}")
                        data = self.options_client.fetch_historical_options(
                            symbol, date_str)

                        if data is not None and not data.empty:
                            # Store in cache
                            self.cache.store_options_data(
                                symbol, date_str, data)
                            self.progress['options_calls_today'] += 1

                            # Auto-calculate GEX
                            await self.calculate_and_cache_gex(symbol, date_str, data)

                    # Mark as collected
                    if symbol not in self.progress['options_collected']:
                        self.progress['options_collected'][symbol] = []
                    self.progress['options_collected'][symbol].append(date_str)
                    collected += 1

                    # Save progress after each successful collection
                    self.save_progress()

                except Exception as e:
                    self.logger.error(
                        f"Error collecting {symbol} options for {date_str}: {e}")

        return collected

    async def collect_stocks_batch(self) -> int:
        """
        Collect stock data from Polygon.io.
        Returns number of stocks collected.
        """
        collected = 0

        for symbol in self.stock_priority:
            try:
                # Check if we already have this stock's data
                existing = self.cache.get_market_data(
                    symbol, self.start_date, self.end_date)
                if existing is not None and not existing.empty:
                    self.logger.info(f"Stock data for {symbol} already cached")
                    continue

                # Fetch from Polygon
                self.logger.info(f"Fetching stock data for {symbol}")
                data = self.polygon_client.fetch_daily_bars(
                    symbol, self.start_date, self.end_date)

                if data is not None and not data.empty:
                    # Store in cache
                    self.cache.store_market_data(
                        symbol, data, self.start_date, self.end_date)

                    # Mark as collected
                    self.progress['stocks_collected'][symbol] = {
                        'start': self.start_date,
                        'end': self.end_date,
                        'bars': len(data)
                    }
                    collected += 1

                    # Save progress
                    self.save_progress()

                    # Rate limit (5/minute for free tier)
                    # 5 calls per minute = 12 seconds between calls
                    await asyncio.sleep(12)

            except Exception as e:
                self.logger.error(
                    f"Error collecting stock data for {symbol}: {e}")

        return collected

    async def calculate_and_cache_gex(self, symbol: str, date_str: str, options_data):
        """Calculate and cache GEX for given options data."""
        try:
            gex_key = f"{symbol}_{date_str}"

            # Check if already calculated
            if self.progress['gex_calculated'].get(gex_key):
                return

            # Calculate GEX
            self.logger.info(f"Calculating GEX for {symbol} {date_str}")

            # Get spot price (use mid of bid/ask for options data estimation)
            spot_price = options_data['strike'].median(
            ) if 'strike' in options_data.columns else 100

            gex_results = self.gex_calculator.calculate_gex(
                options_data,
                spot_price=spot_price
            )

            if gex_results and gex_results.get('status') == 'success':
                # Store in GEX cache
                gex_summary = gex_results.get('metrics', {})
                gex_summary.update({
                    'symbol': symbol,
                    'trading_date': date_str,
                    'calculation_timestamp': datetime.now().isoformat()
                })

                self.cache.gex_cache.store_gex_calculation(
                    symbol, date_str, gex_summary)

                # Mark as calculated
                self.progress['gex_calculated'][gex_key] = True
                self.save_progress()

                self.logger.info(f"GEX cached for {symbol} {date_str}: "
                                 f"Total GEX = ${gex_summary.get('total_gex', 0)/1e9:.2f}B")

        except Exception as e:
            self.logger.error(
                f"Error calculating GEX for {symbol} {date_str}: {e}")

    def _get_trading_dates(self, start: str, end: str) -> List[str]:
        """Generate list of trading dates."""
        dates = []
        current = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()

        while current <= end_date:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        return dates

    def get_collection_status(self) -> Dict:
        """Get current collection status."""
        status = {
            'options': {
                'symbols_collected': len(self.progress['options_collected']),
                'total_dates': sum(len(dates) for dates in self.progress['options_collected'].values()),
                'calls_today': self.progress['options_calls_today'],
                'calls_remaining': self.options_daily_limit - self.progress['options_calls_today']
            },
            'stocks': {
                'symbols_collected': len(self.progress['stocks_collected']),
                'total_bars': sum(s.get('bars', 0) for s in self.progress['stocks_collected'].values())
            },
            'gex': {
                'calculations_cached': len(self.progress['gex_calculated'])
            },
            'cache': self.cache.get_cache_summary()
        }

        return status

    async def run_continuous_collection(self):
        """Run continuous collection respecting all API limits."""
        self.logger.info("Starting automated data collection system")
        self.logger.info(
            f"Options: {len(self.options_priority)} symbols prioritized")
        self.logger.info(
            f"Stocks: {len(self.stock_priority)} symbols prioritized")

        while True:
            try:
                # Collect options (25/day limit)
                options_collected = await self.collect_options_batch()
                if options_collected > 0:
                    self.logger.info(
                        f"Collected {options_collected} options datasets")

                # Collect stocks (much higher limit)
                stocks_collected = await self.collect_stocks_batch()
                if stocks_collected > 0:
                    self.logger.info(
                        f"Collected {stocks_collected} stock datasets")

                # Log status
                status = self.get_collection_status()
                self.logger.info(
                    f"Collection Status: {json.dumps(status, indent=2)}")

                # If we've hit daily options limit and collected all stocks, wait until tomorrow
                if status['options']['calls_remaining'] == 0:
                    tomorrow = datetime.now() + timedelta(days=1)
                    tomorrow_start = tomorrow.replace(
                        hour=0, minute=1, second=0)
                    wait_seconds = (tomorrow_start -
                                    datetime.now()).total_seconds()

                    self.logger.info(
                        f"Daily options limit reached. Waiting {wait_seconds/3600:.1f} hours until reset.")
                    await asyncio.sleep(wait_seconds)
                else:
                    # Short pause between batches
                    await asyncio.sleep(60)

            except KeyboardInterrupt:
                self.logger.info("Collection interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Collection error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error


async def main():
    """Run the automated collector."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('automated_collection.log'),
            logging.StreamHandler()
        ]
    )

    collector = AutomatedDataCollector()

    # Show initial status
    status = collector.get_collection_status()
    print("\nAutomated Data Collection System")
    print("=" * 60)
    print("Initial Status:")
    print(json.dumps(status, indent=2))
    print("\nStarting continuous collection...")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    await collector.run_continuous_collection()


if __name__ == "__main__":
    asyncio.run(main())
