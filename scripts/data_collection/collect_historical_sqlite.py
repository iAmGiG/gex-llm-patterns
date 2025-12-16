#!/usr/bin/env python3
"""Historical Options Data Collection Script for Paper 3.

Collects historical options data from Alpha Vantage API into SQLite database.

Usage:
    # Base collection (SPY, QQQ, IWM)
    python scripts/data_collection/collect_historical_sqlite.py -y

    # Expanded collection (15 tickers across asset classes)
    python scripts/data_collection/collect_historical_sqlite.py --preset expanded -y

    # Custom symbols
    python scripts/data_collection/collect_historical_sqlite.py --symbols SPY QQQ AAPL MSFT

    # Extended date range
    python scripts/data_collection/collect_historical_sqlite.py --preset expanded --start 2018-01-01 -y

    # Check status
    python scripts/data_collection/collect_historical_sqlite.py --status

Issue #147: Store raw options data in database
Issue #179: Paper 3 multi-symbol data collection
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

# ================================================================
# TICKER PRESETS
# ================================================================

PRESETS = {
    "base": {
        "description": "Core ETFs for Paper 3 (SPY, QQQ, IWM)",
        "symbols": ["SPY", "QQQ", "IWM"],
    },
    "expanded": {
        "description": "Multi-asset collection (15 tickers across equity, bond, commodity, volatility)",
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
    },
    "full": {
        "description": "Complete collection including additional tickers",
        "symbols": [
            # All expanded tickers
            "SPY",
            "QQQ",
            "IWM",
            "AAPL",
            "MSFT",
            "TSLA",
            "VTI",
            "DIA",
            "TLT",
            "IEF",
            "LQD",
            "GLD",
            "SLV",
            "VXX",
            "IYR",
            # Additional
            "VNQ",
            "UVXY",
        ],
    },
}


def setup_logging(verbose: bool = False):
    """Configure logging for collection run."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(project_root / "historical_collection.log"),
            logging.StreamHandler(),
        ],
    )


def estimate_collection(symbols: list, start_date: str, end_date: str) -> dict:
    """Estimate collection time and API calls."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Count trading days (weekdays)
    trading_days = sum(1 for d in range((end - start).days + 1) if (start + timedelta(days=d)).weekday() < 5)

    total_calls = trading_days * len(symbols)
    estimated_minutes = total_calls / 900  # Premium tier with buffer

    return {
        "trading_days": trading_days,
        "total_calls": total_calls,
        "estimated_minutes": estimated_minutes,
        "symbols_count": len(symbols),
    }


async def run_collection(args):
    """Run the data collection based on arguments."""
    collector = HistoricalOptionsCollector(
        db_path=str(project_root / ".cache" / "options_historical.db"),
        use_sqlite=True,
        rate_limit_per_minute=900,  # Premium tier buffer
    )

    if args.status:
        # Show status
        status = collector.get_collection_status(args.symbol)
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

    if args.list_presets:
        print("\n=== Available Presets ===")
        for name, preset in PRESETS.items():
            print(f"\n{name}:")
            print(f"  Description: {preset['description']}")
            print(f"  Symbols ({len(preset['symbols'])}): {', '.join(preset['symbols'])}")
        return

    # Determine symbols
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    elif args.preset:
        if args.preset not in PRESETS:
            print(f"Error: Unknown preset '{args.preset}'. Use --list-presets to see options.")
            return
        symbols = PRESETS[args.preset]["symbols"]
        print(f"Using preset '{args.preset}': {PRESETS[args.preset]['description']}")
    elif args.symbol:
        symbols = [args.symbol.upper()]
    else:
        symbols = PRESETS["base"]["symbols"]

    # Parse dates
    start_date = args.start or "2020-01-01"
    end_date = args.end or today_str()

    # Show collection plan
    estimate = estimate_collection(symbols, start_date, end_date)

    print(f"\n{'='*60}")
    print("HISTORICAL OPTIONS DATA COLLECTION")
    print(f"{'='*60}")
    print(f"\nSymbols ({len(symbols)}): {', '.join(symbols)}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Database: {collector.db.db_path}")
    print(f"Skip existing: {not args.force}")
    print()
    print(f"Estimated trading days per symbol: ~{estimate['trading_days']}")
    print(f"Maximum API calls needed: ~{estimate['total_calls']:,}")
    print(f"Estimated time (at 900/min): ~{estimate['estimated_minutes']:.1f} minutes")
    print()

    if not args.yes:
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    # Run collection
    summary = await collector.collect_multi_symbol_historical(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        skip_existing=not args.force,
    )

    print(f"\n{'='*60}")
    print("COLLECTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total API calls: {summary['total_api_calls']}")
    print(f"Successful: {summary['total_successful']}")
    print(f"Failed: {summary['total_failed']}")

    if "final_db_stats" in summary:
        stats = summary["final_db_stats"]
        print(f"\nDatabase stats:")
        print(f"  Total records: {stats.get('total_options_records', 0):,}")
        print(f"  Database size: {stats.get('db_size_mb', 0):.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Collect historical options data into SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Base collection (SPY, QQQ, IWM from 2020)
  %(prog)s -y

  # Expanded multi-asset collection
  %(prog)s --preset expanded -y

  # Custom symbols
  %(prog)s --symbols SPY QQQ AAPL MSFT -y

  # Extended date range
  %(prog)s --preset expanded --start 2018-01-01 -y

  # Check status
  %(prog)s --status
        """,
    )

    # Symbol selection (mutually exclusive)
    symbol_group = parser.add_mutually_exclusive_group()
    symbol_group.add_argument("--symbol", type=str, help="Single symbol to collect")
    symbol_group.add_argument("--symbols", type=str, nargs="+", help="Multiple symbols to collect")
    symbol_group.add_argument(
        "--preset", type=str, choices=list(PRESETS.keys()), help="Use a preset symbol list (base, expanded, full)"
    )

    # Date range
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD (default: 2020-01-01)")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD (default: today)")

    # Actions
    parser.add_argument("--status", action="store_true", help="Show collection status and exit")
    parser.add_argument("--list-presets", action="store_true", help="List available presets and exit")

    # Options
    parser.add_argument("--force", action="store_true", help="Re-collect even if data exists")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()
    setup_logging(args.verbose)

    asyncio.run(run_collection(args))


if __name__ == "__main__":
    main()
