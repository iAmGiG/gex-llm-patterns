#!/usr/bin/env python3
"""
Backfill Missing 2024 Trading Dates - Issue #102

Collects missing SPY options data for 10 trading dates in 2024 using
Alpha Vantage API and populates the GEX database.

Missing dates (242/252 → 252/252):
- 2024-02-02, 02-09, 02-16 (Monthly OPEX), 02-23
- 2024-03-01, 03-08, 03-22 (Quarterly OPEX), 03-28
- 2024-06-04, 06-06

Usage:
    python tools/database/backfill_missing_dates.py
    python tools/database/backfill_missing_dates.py --dry-run
    python tools/database/backfill_missing_dates.py --dates 2024-02-02 2024-02-09
"""

import argparse
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.historical_collector import HistoricalOptionsCollector
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator


class MissingDatesBackfiller:
    """Backfill missing trading dates into GEX database."""

    # Missing dates identified in Issue #102
    MISSING_DATES_2024 = [
        "2024-02-02",  # Friday
        "2024-02-09",  # Friday
        "2024-02-16",  # Friday (Monthly OPEX)
        "2024-02-23",  # Friday
        "2024-03-01",  # Friday
        "2024-03-08",  # Friday
        "2024-03-22",  # Friday (Quarterly OPEX)
        "2024-03-28",  # Thursday
        "2024-06-04",  # Tuesday
        "2024-06-06",  # Thursday
    ]

    def __init__(self, database_path=None, dry_run=False):
        """Initialize backfiller.

        Args:
            database_path: Path to GEX database (default: .cache/gex_database.db)
            dry_run: If True, collect data but don't insert into database
        """
        self.cache = UnifiedCacheManager()
        self.collector = HistoricalOptionsCollector(cache_manager=self.cache)
        self.gex_calc = GEXCalculator()
        self.dry_run = dry_run

        # Database path
        self.db_path = Path(database_path) if database_path else self.cache.base_dir / "gex_database.db"

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Statistics
        self.stats = {
            "attempted": 0,
            "collected": 0,
            "calculated": 0,
            "inserted": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
        }

    def check_date_exists(self, date, symbol="SPY"):
        """Check if date already exists in database.

        Args:
            date: Date string (YYYY-MM-DD)
            symbol: Trading symbol

        Returns:
            bool: True if date exists
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM daily_gex_metrics WHERE date = ? AND symbol = ?", (date, symbol))
        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def collect_options_data(self, date, symbol="SPY"):
        """Collect options data for a specific date.

        Args:
            date: Date string (YYYY-MM-DD)
            symbol: Trading symbol

        Returns:
            dict: Options data or None if failed
        """
        print(f"\n  📥 Collecting options data from Alpha Vantage...")

        try:
            # Use AlphaVantageGEXClient to fetch historical options
            options_data = self.collector.client.fetch_historical_options(symbol, date)

            if options_data is None or options_data.empty:
                print(f"  ❌ No options data returned")
                return None

            print(f"  ✅ Collected {len(options_data)} option contracts")
            return options_data

        except Exception as e:
            print(f"  ❌ Error collecting data: {e}")
            import traceback

            traceback.print_exc()
            return None

    def calculate_gex(self, options_data, underlying_price):
        """Calculate GEX metrics from options data.

        Args:
            options_data: DataFrame with options chain
            underlying_price: Current stock price

        Returns:
            dict: GEX results or None if failed
        """
        print(f"  🧮 Calculating GEX metrics...")

        try:
            gex_results = self.gex_calc.calculate_gex_profile(options_data, underlying_price)

            if not gex_results:
                print(f"  ❌ GEX calculation returned empty results")
                return None

            net_gex = gex_results.get("net_gex", 0)
            print(f"  ✅ Net GEX: ${net_gex/1e9:.2f}B")

            return gex_results

        except Exception as e:
            print(f"  ❌ Error calculating GEX: {e}")
            return None

    def insert_into_database(self, date, symbol, gex_results):
        """Insert GEX data into database.

        Args:
            date: Date string (YYYY-MM-DD)
            symbol: Trading symbol
            gex_results: GEX calculation results

        Returns:
            bool: True if successful
        """
        if self.dry_run:
            print(f"  🔍 DRY RUN: Would insert into database")
            return True

        print(f"  💾 Inserting into database...")

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Extract daily metrics and map to database schema
            net_gex = gex_results.get("net_gex", 0)
            call_gex = gex_results.get("call_gex", 0)
            put_gex = gex_results.get("put_gex", 0)
            gex_flip = gex_results.get("zero_gamma_level", 0)
            spot_price = gex_results.get("spot_price", 0)

            # Determine GEX regime
            if net_gex > 0:
                gex_regime = "positive"
            elif net_gex < 0:
                gex_regime = "negative"
            else:
                gex_regime = "neutral"

            # Insert into daily_gex_metrics (matching actual schema)
            cursor.execute(
                """
                INSERT OR REPLACE INTO daily_gex_metrics
                (symbol, date, spot_price, total_gex, net_call_gex, net_put_gex,
                 gamma_flip_point, gex_regime, data_quality_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol,
                    date,
                    float(spot_price) if spot_price else None,
                    float(net_gex),
                    float(call_gex),
                    float(put_gex),
                    float(gex_flip) if gex_flip else None,
                    gex_regime,
                    100,  # Quality score
                    datetime.now().isoformat(),
                ),
            )

            # Insert strike-level details if available
            strike_gex = gex_results.get("strike_gex")
            if strike_gex is not None and not strike_gex.empty and spot_price:
                # strike_gex is a DataFrame with columns: strike, net_gex, etc.
                for _, row in strike_gex.iterrows():
                    strike_price = float(row["strike"])
                    gex_value = float(row.get("net_gex", 0))
                    distance = strike_price - float(spot_price)

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO strike_gex_details
                        (symbol, date, strike, net_gex, distance_from_spot, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (symbol, date, strike_price, gex_value, distance, datetime.now().isoformat()),
                    )

            conn.commit()
            conn.close()

            print(f"  ✅ Data inserted successfully")
            return True

        except Exception as e:
            print(f"  ❌ Error inserting data: {e}")
            return False

    def backfill_date(self, date, symbol="SPY"):
        """Backfill a single date.

        Args:
            date: Date string (YYYY-MM-DD)
            symbol: Trading symbol

        Returns:
            bool: True if successful
        """
        day_of_week = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
        is_opex = "📅 OPEX" if date in ["2024-02-16", "2024-03-22"] else ""

        print(f"\n{'='*70}")
        print(f"Processing: {date} ({day_of_week}) {is_opex}")
        print(f"{'='*70}")

        self.stats["attempted"] += 1

        # Check if already exists
        if self.check_date_exists(date, symbol):
            print(f"  ⏭️  Date already exists in database - skipping")
            self.stats["skipped"] += 1
            return True

        # Step 1: Collect options data
        options_data = self.collect_options_data(date, symbol)
        if options_data is None:
            self.stats["failed"] += 1
            return False

        self.stats["collected"] += 1

        # Get underlying price (from options data or fetch separately)
        # For now, use mid of options data or fetch from polygon
        try:
            # Simple approach: use first option's underlying price if available
            if "underlying_price" in options_data.columns:
                underlying_price = options_data["underlying_price"].iloc[0]
            else:
                # Estimate from strike prices (use ATM area)
                underlying_price = options_data["strike"].median()

            print(f"  📊 Underlying price: ${underlying_price:.2f}")

        except Exception as e:
            print(f"  ❌ Error getting underlying price: {e}")
            self.stats["failed"] += 1
            return False

        # Step 2: Calculate GEX
        gex_results = self.calculate_gex(options_data, underlying_price)
        if gex_results is None:
            self.stats["failed"] += 1
            return False

        # Add spot price to results for database insertion
        gex_results["spot_price"] = underlying_price

        self.stats["calculated"] += 1

        # Step 3: Insert into database
        success = self.insert_into_database(date, symbol, gex_results)
        if success:
            self.stats["inserted"] += 1
            return True
        else:
            self.stats["failed"] += 1
            return False

    def backfill_all(self, dates=None, symbol="SPY"):
        """Backfill all missing dates.

        Args:
            dates: List of dates to backfill (default: all missing dates)
            symbol: Trading symbol

        Returns:
            dict: Statistics
        """
        dates_to_process = dates or self.MISSING_DATES_2024

        print(f"\n{'#'*70}")
        print(f"# GEX Database Backfill - Issue #102")
        print(f"{'#'*70}")
        print(f"\nMode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Symbol: {symbol}")
        print(f"Database: {self.db_path}")
        print(f"Dates to process: {len(dates_to_process)}")
        print(f"\nMissing dates:")
        for date in dates_to_process:
            day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
            opex = " (OPEX)" if date in ["2024-02-16", "2024-03-22"] else ""
            print(f"  - {date} ({day}){opex}")

        if self.dry_run:
            print(f"\n⚠️  DRY RUN MODE: No data will be written to database")

        # Confirm before proceeding (skip if --yes flag or dry_run)
        # Note: confirmation will be skipped in non-interactive environments

        self.stats["start_time"] = datetime.now()

        # Process each date
        for i, date in enumerate(dates_to_process, 1):
            print(f"\n[{i}/{len(dates_to_process)}]", end=" ")
            self.backfill_date(date, symbol)

            # Rate limiting: Alpha Vantage allows 75 calls/min
            # Each date requires ~2-3 calls, so sleep between dates
            if i < len(dates_to_process):
                sleep_time = 2  # seconds
                print(f"  ⏳ Rate limiting: sleeping {sleep_time}s...")
                time.sleep(sleep_time)

        self.stats["end_time"] = datetime.now()

        # Print summary
        self.print_summary()

        return self.stats

    def print_summary(self):
        """Print backfill summary statistics."""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        print(f"\n{'='*70}")
        print(f"BACKFILL COMPLETE")
        print(f"{'='*70}")
        print(f"\nStatistics:")
        print(f"  Attempted:  {self.stats['attempted']}")
        print(f"  Collected:  {self.stats['collected']}")
        print(f"  Calculated: {self.stats['calculated']}")
        print(f"  Inserted:   {self.stats['inserted']}")
        print(f"  Skipped:    {self.stats['skipped']}")
        print(f"  Failed:     {self.stats['failed']}")
        print(f"\nDuration: {duration:.1f} seconds ({duration/60:.1f} minutes)")

        if self.dry_run:
            print(f"\n⚠️  DRY RUN: No changes made to database")
        else:
            success_rate = (
                (self.stats["inserted"] / self.stats["attempted"] * 100) if self.stats["attempted"] > 0 else 0
            )
            print(f"\nSuccess rate: {success_rate:.1f}%")

            if self.stats["inserted"] > 0:
                print(f"\n✅ Database updated successfully!")
                print(f"   New coverage: {242 + self.stats['inserted']}/252 trading days")

    def verify_database(self):
        """Verify final database state."""
        print(f"\n{'='*70}")
        print(f"DATABASE VERIFICATION")
        print(f"{'='*70}")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Count total days
        cursor.execute("SELECT COUNT(*) FROM daily_gex_metrics WHERE symbol='SPY' AND date LIKE '2024%'")
        total_days = cursor.fetchone()[0]

        # Get date range
        cursor.execute("SELECT MIN(date), MAX(date) FROM daily_gex_metrics WHERE symbol='SPY' AND date LIKE '2024%'")
        min_date, max_date = cursor.fetchone()

        # Check for missing dates
        cursor.execute("SELECT date FROM daily_gex_metrics WHERE symbol='SPY' AND date LIKE '2024%' ORDER BY date")
        existing_dates = [row[0] for row in cursor.fetchall()]

        conn.close()

        print(f"\nDatabase state:")
        print(f"  Total days: {total_days}/252")
        print(f"  Date range: {min_date} to {max_date}")
        print(f"  Coverage: {total_days/252*100:.1f}%")

        # Check which of the original missing dates are still missing
        still_missing = [d for d in self.MISSING_DATES_2024 if d not in existing_dates]
        if still_missing:
            print(f"\n⚠️  Still missing {len(still_missing)} dates:")
            for date in still_missing:
                print(f"    - {date}")
        else:
            print(f"\n✅ All originally missing dates have been backfilled!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill missing 2024 trading dates into GEX database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (no database changes)
  python tools/database/backfill_missing_dates.py --dry-run

  # Backfill all missing dates
  python tools/database/backfill_missing_dates.py

  # Backfill specific dates only
  python tools/database/backfill_missing_dates.py --dates 2024-02-02 2024-02-09

  # Verify database after backfill
  python tools/database/backfill_missing_dates.py --verify-only
        """,
    )

    parser.add_argument("--dry-run", action="store_true", help="Collect data but do not insert into database")

    parser.add_argument("--dates", nargs="+", help="Specific dates to backfill (YYYY-MM-DD format)")

    parser.add_argument("--database", help="Path to GEX database (default: .cache/gex_database.db)")

    parser.add_argument("--symbol", default="SPY", help="Trading symbol to backfill (default: SPY)")

    parser.add_argument("--verify-only", action="store_true", help="Only verify database state, do not backfill")

    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt (auto-confirm)")

    args = parser.parse_args()

    try:
        backfiller = MissingDatesBackfiller(database_path=args.database, dry_run=args.dry_run)

        if args.verify_only:
            backfiller.verify_database()
        else:
            backfiller.backfill_all(dates=args.dates, symbol=args.symbol)

            if not args.dry_run:
                backfiller.verify_database()

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
