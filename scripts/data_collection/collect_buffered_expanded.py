#!/usr/bin/env python3
"""Buffered Parallel Collection for Expanded Ticker Set.

FASTEST collection mode - decouples API calls from database I/O by:
1. Making API calls at full rate limit speed (900/min)
2. Queuing responses in RAM buffer
3. Background thread handles SQLite writes asynchronously

This prevents database lock contention from slowing down API collection.

Usage:
    # Start buffered parallel collection for expanded tickers (15 symbols)
    python scripts/data_collection/collect_buffered_expanded.py -y

    # Specify custom tickers
    python scripts/data_collection/collect_buffered_expanded.py --symbols SPY QQQ AAPL MSFT -y

    # Check collection status
    python scripts/data_collection/collect_buffered_expanded.py --status
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.data_sources.historical_collector import HistoricalOptionsCollector
from src.utils.date_utils import today_str

# Expanded ticker configuration
EXPANDED_TICKERS = {
    "description": "Multi-asset collection (15 tickers across equity, bond, commodity, volatility, real_estate)",
    "symbols": [
        # Equities - Tech + Broad Market
        "SPY",
        "QQQ",
        "IWM",
        "AAPL",
        "MSFT",
        "TSLA",
        "VTI",
        "DIA",
        # Bond ETFs
        "TLT",
        "IEF",
        "LQD",
        # Commodities
        "GLD",
        "SLV",
        # Volatility
        "VXX",
        # Real Estate
        "IYR",
    ],
}


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(project_root / "buffered_collection.log"),
            logging.StreamHandler(),
        ],
    )


def estimate_collection(symbols: list, start_date: str, end_date: str) -> dict:
    """Estimate collection time for buffered mode."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Count trading days
    trading_days = sum(1 for d in range((end - start).days + 1) if (start + timedelta(days=d)).weekday() < 5)

    # Total API calls needed
    total_calls = trading_days * len(symbols)

    # Buffered mode: rate limit is the only bottleneck (DB writes are async)
    estimated_minutes = total_calls / 900

    return {
        "trading_days": trading_days,
        "total_calls": total_calls,
        "estimated_minutes": estimated_minutes,
        "symbols_count": len(symbols),
        "speedup": f"{len(symbols)}x faster than sequential (DB writes async)",
    }


async def run_buffered_collection(args):
    """Run buffered parallel collection."""
    collector = HistoricalOptionsCollector(
        db_path=str(project_root / ".cache" / "options_historical.db"),
        use_sqlite=True,
        rate_limit_per_minute=900,
    )

    if args.status:
        # Show status
        status = collector.get_collection_status()
        print("\n=== Collection Status ===")
        print(f"Storage: {status['storage']}")

        if status["storage"] == "sqlite":
            stats = status.get("database_stats", {})
            print(f"Total records: {stats.get('total_options_records', 0):,}")
            print(f"Database size: {stats.get('db_size_mb', 0):.2f} MB")

            by_symbol = stats.get("by_symbol", {})
            if by_symbol:
                print("\nBy symbol:")
                for sym, info in sorted(by_symbol.items()):
                    print(
                        f"  {sym}: {info['records']:,} records, "
                        f"{info['trading_days']} days "
                        f"({info['min_date']} to {info['max_date']})"
                    )

            greeks = stats.get("greeks_coverage", {})
            if greeks:
                print(f"\nGreeks coverage:")
                print(f"  Delta: {greeks.get('delta_pct', 0)}%")
                print(f"  Gamma: {greeks.get('gamma_pct', 0)}%")
                print(f"  IV: {greeks.get('iv_pct', 0)}%")
        return

    # Determine symbols
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        symbols = EXPANDED_TICKERS["symbols"]
        print(f"Using expanded preset: {EXPANDED_TICKERS['description']}")

    # Parse dates
    start_date = args.start or "2020-01-01"
    end_date = args.end or today_str()

    # Show collection plan
    estimate = estimate_collection(symbols, start_date, end_date)

    print(f"\n{'='*70}")
    print("BUFFERED PARALLEL HISTORICAL OPTIONS DATA COLLECTION")
    print(f"{'='*70}")
    print(f"\nMode: RAM buffer with async DB writes (FASTEST)")
    print(f"Symbols ({len(symbols)}): {', '.join(symbols)}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Database: {collector.db.db_path}")
    print(f"Skip existing: {not args.force}")
    print()
    print(f"Estimated trading days: ~{estimate['trading_days']}")
    print(f"Total API calls needed: ~{estimate['total_calls']:,}")
    print(f"Estimated time (at 900/min): ~{estimate['estimated_minutes']:.1f} minutes")
    print(f"Speedup vs sequential: {estimate['speedup']}")
    print()
    print("NOTE: API calls run at full speed, DB writes happen asynchronously")
    print()

    if not args.yes:
        response = input("Start buffered parallel collection? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    # Run buffered parallel collection
    print(f"\n{'='*70}")
    print("Starting buffered parallel collection...")
    print(f"{'='*70}\n")

    summary = await collector.collect_multi_symbol_historical(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        skip_existing=not args.force,
        parallel=True,
        buffered=True,  # Use buffered mode (RAM queue + async writes)
    )

    print(f"\n{'='*70}")
    print("COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"Mode: {summary['mode']}")
    print(f"Total API calls: {summary['total_api_calls']}")
    print(f"Successful: {summary['total_successful']}")
    print(f"Failed: {summary['total_failed']}")

    if "final_db_stats" in summary:
        stats = summary["final_db_stats"]
        print(f"\nDatabase stats:")
        print(f"  Total records: {stats.get('total_options_records', 0):,}")
        print(f"  Database size: {stats.get('db_size_mb', 0):.2f} MB")

    print(f"\nSummary saved to collection_summary.json")


def main():
    parser = argparse.ArgumentParser(
        description="Collect historical options data with buffered parallel mode (FASTEST)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Expanded multi-asset collection (15 symbols) - buffered mode
  %(prog)s -y

  # Custom symbols
  %(prog)s --symbols SPY QQQ AAPL MSFT -y

  # Extended date range
  %(prog)s --start 2018-01-01 -y

  # Check status
  %(prog)s --status

BUFFERED MODE:
  - API calls run at full 900/min rate
  - Responses queued in RAM buffer
  - Background thread writes to SQLite asynchronously
  - No DB lock contention slowing down API calls
        """,
    )

    # Symbol selection
    symbol_group = parser.add_mutually_exclusive_group()
    symbol_group.add_argument("--symbols", type=str, nargs="+", help="Custom symbols to collect")

    # Date range
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD (default: 2020-01-01)")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD (default: today)")

    # Actions
    parser.add_argument("--status", action="store_true", help="Show collection status and exit")

    # Options
    parser.add_argument("--force", action="store_true", help="Re-collect even if data exists")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()
    setup_logging(args.verbose)

    asyncio.run(run_buffered_collection(args))


if __name__ == "__main__":
    main()
