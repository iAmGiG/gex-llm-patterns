#!/usr/bin/env python3
"""Intraday OI Monitor - Adaptive Theta Decay Sampling Service.

Background service that captures intraday options snapshots using formula-driven
adaptive sampling matching 0DTE theta decay patterns and algorithmic activity bursts.

Issue #204: https://github.com/iAmGiG/gex-llm-patterns/issues/204

Usage:
    # Direct execution
    python scripts/collection/intraday_oi_monitor.py

    # Background via screen
    screen -dmS intraday-monitor python scripts/collection/intraday_oi_monitor.py

    # Check status
    screen -r intraday-monitor
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import pytz
import schedule

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data_sources.alpha_vantage_gex import AlphaVantageGEXClient
from src.cache.postgresql_options_manager import PostgreSQLOptionsManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/intraday_oi_monitor.log')
    ]
)
logger = logging.getLogger('IntradayOIMonitor')


class IntradayOIMonitor:
    """Intraday options monitoring service with adaptive theta decay sampling.

    Sampling Schedule (21 snapshots/day):
    - Morning (9:30-14:00): 30-minute intervals (10 snapshots)
    - Theta Acceleration (14:00-15:00): 15-minute intervals (4 snapshots)
    - Expiry Rush (15:00-15:50): 10-minute intervals (5 snapshots)
    - Final Rush (15:55-16:00): 5-minute intervals (2 snapshots)

    All captures occur at :59 seconds to ensure algo streams complete.
    """

    # Default symbols to monitor (can be overridden)
    DEFAULT_SYMBOLS = [
        # Major indices/ETFs
        'SPY', 'QQQ', 'IWM', 'DIA',
        # Volatility
        'VIX', 'UVXY', 'SVXY',
        # Leveraged
        'TQQQ', 'SQQQ', 'SPXL', 'SPXS',
        # Sector ETFs
        'XLF', 'XLE', 'XLK', 'XLV', 'XLI',
        # International
        'EEM', 'EFA', 'FXI',
        # Bonds
        'TLT', 'HYG', 'LQD',
        # Commodities
        'GLD', 'SLV', 'USO',
        # Large cap tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
    ]

    # Snapshot type definitions
    SNAPSHOT_TYPES = {
        'market_open': '09:30',
        'morning_baseline': ['10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00'],
        'theta_accel': ['14:15', '14:30', '14:45', '15:00'],
        'expiry_rush': ['15:10', '15:20', '15:30', '15:40', '15:50'],
        'final_rush': '15:55',
        'market_close': '16:00'
    }

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        dry_run: bool = False,
        db_host: str = 'localhost',
        db_port: int = 5432,
        db_user: str = 'cregan1',
        db_name: str = 'gex_options'
    ):
        """Initialize the intraday monitor.

        Args:
            symbols: List of symbols to monitor (default: DEFAULT_SYMBOLS)
            dry_run: If True, log actions without making API calls or DB writes
            db_host: PostgreSQL host
            db_port: PostgreSQL port
            db_user: PostgreSQL user
            db_name: PostgreSQL database name
        """
        self.symbols = symbols or self.DEFAULT_SYMBOLS[:30]  # Limit to 30 for API capacity
        self.dry_run = dry_run
        self.et_tz = pytz.timezone('US/Eastern')

        # Statistics tracking
        self.stats = {
            'snapshots_captured': 0,
            'api_calls': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

        if not dry_run:
            # Initialize API client
            self.api_client = AlphaVantageGEXClient()

            # Initialize PostgreSQL connection
            self.db = PostgreSQLOptionsManager(
                host=db_host,
                port=db_port,
                user=db_user,
                database=db_name
            )
            logger.info(f"Connected to PostgreSQL: {db_name}@{db_host}:{db_port}")
        else:
            self.api_client = None
            self.db = None
            logger.info("DRY RUN MODE - No API calls or database writes")

        logger.info(f"Monitoring {len(self.symbols)} symbols: {', '.join(self.symbols[:5])}...")

    def _wait_until_59_seconds(self):
        """Wait until :59 seconds of the current minute.

        This ensures we capture data after algorithmic trading streams complete,
        which typically finish processing by :55-:58 seconds.
        """
        now = datetime.now()
        target_second = 59

        if now.second < target_second:
            wait_time = target_second - now.second
        else:
            # Already past :59, wait for next minute's :59
            wait_time = (60 - now.second) + target_second

        if wait_time > 0:
            logger.debug(f"Waiting {wait_time} seconds until :59")
            time.sleep(wait_time)

    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours (9:30 AM - 4:00 PM ET)."""
        now_et = datetime.now(self.et_tz)
        market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now_et.replace(hour=16, minute=5, second=0, microsecond=0)

        # Also check if it's a weekday
        if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        return market_open <= now_et <= market_close

    def _store_snapshot(
        self,
        symbol: str,
        data: pd.DataFrame,
        snapshot_type: str,
        timestamp: datetime
    ):
        """Store options snapshot in PostgreSQL intraday_snapshots table.

        Args:
            symbol: Stock symbol
            data: Options chain DataFrame
            snapshot_type: Type of snapshot (market_open, theta_accel, etc.)
            timestamp: Snapshot timestamp
        """
        if self.dry_run or data.empty:
            return

        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()

            # Prepare data for insertion
            records = []
            for _, row in data.iterrows():
                record = (
                    symbol,
                    row.get('strike', 0),
                    row.get('expiration', timestamp.date()),
                    timestamp,
                    snapshot_type,
                    row.get('type', 'call'),  # call or put
                    row.get('open_interest', 0),
                    row.get('volume', 0),
                    row.get('implied_volatility', None),
                    row.get('underlying_price', None),
                    row.get('delta', None),
                    row.get('gamma', None),
                    row.get('theta', None),
                    row.get('vega', None),
                    row.get('bid', None),
                    row.get('ask', None),
                    row.get('last', None)
                )
                records.append(record)

            # Batch insert with ON CONFLICT handling
            insert_query = """
                INSERT INTO intraday_snapshots (
                    symbol, strike, expiration_date, snapshot_timestamp, snapshot_type,
                    option_type, open_interest, volume, implied_volatility, spot_price,
                    delta, gamma, theta, vega, bid, ask, last_price
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, strike, expiration_date, snapshot_timestamp, option_type)
                DO UPDATE SET
                    open_interest = EXCLUDED.open_interest,
                    volume = EXCLUDED.volume,
                    implied_volatility = EXCLUDED.implied_volatility
            """

            from psycopg2.extras import execute_batch
            execute_batch(cursor, insert_query, records, page_size=1000)
            conn.commit()

            logger.debug(f"Stored {len(records)} contracts for {symbol}")

        except Exception as e:
            logger.error(f"Error storing snapshot for {symbol}: {e}")
            self.stats['errors'] += 1

    def capture_snapshot(self, snapshot_type: str):
        """Capture options snapshot at :59 seconds of current minute.

        Args:
            snapshot_type: Type of snapshot (market_open, morning_baseline, etc.)
        """
        # Check market hours
        if not self._is_market_hours():
            logger.info(f"Outside market hours, skipping {snapshot_type} snapshot")
            return

        # Wait until :59 seconds
        self._wait_until_59_seconds()

        timestamp = datetime.now(self.et_tz)
        logger.info(f"Capturing {snapshot_type} snapshot at {timestamp.strftime('%H:%M:%S')}")

        successful = 0
        failed = 0

        for symbol in self.symbols:
            try:
                if self.dry_run:
                    logger.debug(f"[DRY RUN] Would capture {symbol}")
                    successful += 1
                    continue

                # Fetch current options data (no date = current/latest)
                data = self.api_client.fetch_historical_options(
                    symbol=symbol,
                    date=None,  # Current data
                    cache_result=False  # Don't cache intraday data in SQLite
                )

                self.stats['api_calls'] += 1

                if not data.empty:
                    self._store_snapshot(symbol, data, snapshot_type, timestamp)
                    successful += 1
                else:
                    logger.warning(f"No data returned for {symbol}")
                    failed += 1

                # Brief pause between symbols to respect rate limits
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error capturing {symbol}: {e}")
                failed += 1
                self.stats['errors'] += 1

        self.stats['snapshots_captured'] += 1
        logger.info(
            f"Snapshot complete: {successful}/{len(self.symbols)} symbols captured, "
            f"{failed} failed"
        )

    def schedule_captures(self):
        """Set up the adaptive sampling schedule."""
        logger.info("Setting up capture schedule...")

        # Market open
        schedule.every().day.at("09:30").do(
            self.capture_snapshot, snapshot_type="market_open"
        )

        # Morning baseline (30-min intervals)
        for time_str in self.SNAPSHOT_TYPES['morning_baseline']:
            schedule.every().day.at(time_str).do(
                self.capture_snapshot, snapshot_type="morning_baseline"
            )

        # Theta acceleration (15-min intervals)
        for time_str in self.SNAPSHOT_TYPES['theta_accel']:
            schedule.every().day.at(time_str).do(
                self.capture_snapshot, snapshot_type="theta_accel"
            )

        # Expiry rush (10-min intervals)
        for time_str in self.SNAPSHOT_TYPES['expiry_rush']:
            schedule.every().day.at(time_str).do(
                self.capture_snapshot, snapshot_type="expiry_rush"
            )

        # Final rush
        schedule.every().day.at("15:55").do(
            self.capture_snapshot, snapshot_type="final_rush"
        )

        # Market close
        schedule.every().day.at("16:00").do(
            self.capture_snapshot, snapshot_type="market_close"
        )

        # Log scheduled jobs
        total_jobs = len(schedule.get_jobs())
        logger.info(f"Scheduled {total_jobs} capture jobs per day")

        for job in schedule.get_jobs():
            logger.debug(f"  {job}")

    def print_status(self):
        """Print current monitoring status."""
        uptime = datetime.now() - self.stats['start_time']
        logger.info("=" * 50)
        logger.info("INTRADAY MONITOR STATUS")
        logger.info("=" * 50)
        logger.info(f"Uptime: {uptime}")
        logger.info(f"Symbols: {len(self.symbols)}")
        logger.info(f"Snapshots captured: {self.stats['snapshots_captured']}")
        logger.info(f"API calls: {self.stats['api_calls']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Next job: {schedule.next_run()}")
        logger.info("=" * 50)

    def run(self):
        """Run the monitoring service."""
        logger.info("=" * 50)
        logger.info("INTRADAY OI MONITOR STARTING")
        logger.info("=" * 50)
        logger.info(f"Symbols: {len(self.symbols)}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 50)

        self.schedule_captures()

        # Print status every hour
        schedule.every().hour.do(self.print_status)

        logger.info("Monitor running. Press Ctrl+C to stop.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")
            self.print_status()


def main():
    parser = argparse.ArgumentParser(
        description='Intraday OI Monitor - Adaptive Theta Decay Sampling'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without API calls or database writes'
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Symbols to monitor (default: predefined list)'
    )
    parser.add_argument(
        '--test-capture',
        action='store_true',
        help='Run a single test capture and exit'
    )
    parser.add_argument(
        '--db-host',
        default='localhost',
        help='PostgreSQL host (default: localhost)'
    )
    parser.add_argument(
        '--db-port',
        type=int,
        default=5432,
        help='PostgreSQL port (default: 5432)'
    )

    args = parser.parse_args()

    monitor = IntradayOIMonitor(
        symbols=args.symbols,
        dry_run=args.dry_run,
        db_host=args.db_host,
        db_port=args.db_port
    )

    if args.test_capture:
        logger.info("Running test capture...")
        monitor.capture_snapshot("test")
        logger.info("Test capture complete")
    else:
        monitor.run()


if __name__ == '__main__':
    main()
