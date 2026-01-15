#!/usr/bin/env python3
"""Leveraged ETF Collection Script (System-Agnostic).

Collects historical options data for leveraged/inverse ETFs for GEX analysis.
These ETFs have amplified gamma effects and high retail participation.

Designed to run on both Windows and Linux/HPCC environments.

Usage:
    # Tier 1 (highest liquidity) - default
    python scripts/data_collection/collect_leveraged_etfs.py -y

    # All tiers
    python scripts/data_collection/collect_leveraged_etfs.py --tier all -y

    # Specific tier
    python scripts/data_collection/collect_leveraged_etfs.py --tier 2 -y

    # Custom symbols
    python scripts/data_collection/collect_leveraged_etfs.py --symbols TQQQ SQQQ -y

    # Check status
    python scripts/data_collection/collect_leveraged_etfs.py --status
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from gex_db_infrastructure.data_sources.historical_collector import HistoricalOptionsCollector
from src.utils.date_utils import today_str

# Leveraged ETF tiers by options liquidity
LEVERAGED_ETFS = {
    "tier1": {
        "description": "Tier 1: Highest liquidity leveraged ETFs",
        "symbols": [
            "TQQQ",  # ProShares UltraPro QQQ (3x Bull Nasdaq) - #2 most traded ETF
            "SQQQ",  # ProShares UltraPro Short QQQ (3x Bear Nasdaq)
            "SOXL",  # Direxion Semiconductor Bull 3X - #1 most traded ETF 2024
            "SOXS",  # Direxion Semiconductor Bear 3X
            "UVXY",  # ProShares Ultra VIX Short-Term (1.5x VIX)
        ],
    },
    "tier2": {
        "description": "Tier 2: High liquidity S&P and Russell leveraged ETFs",
        "symbols": [
            "SPXL",  # Direxion S&P 500 Bull 3X
            "SPXS",  # Direxion S&P 500 Bear 3X - 37.5M daily volume
            "UPRO",  # ProShares UltraPro S&P500 (3x Bull) - $3.9B AUM
            "SPXU",  # ProShares UltraPro Short S&P500 (3x Bear)
            "TNA",  # Direxion Small Cap Bull 3X (Russell 2000)
            "TZA",  # Direxion Small Cap Bear 3X
        ],
    },
    "tier3": {
        "description": "Tier 3: Sector-specific leveraged ETFs",
        "symbols": [
            "FAS",  # Direxion Financial Bull 3X - $2.5B AUM
            "FAZ",  # Direxion Financial Bear 3X
            "LABU",  # Direxion Biotech Bull 3X
            "LABD",  # Direxion Biotech Bear 3X
            "TECL",  # Direxion Technology Bull 3X
            "TECS",  # Direxion Technology Bear 3X
            "NUGT",  # Direxion Gold Miners Bull 2X
            "DUST",  # Direxion Gold Miners Bear 2X
        ],
    },
}


def get_symbols_for_tier(tier: str) -> tuple[list[str], str]:
    """Get symbols for specified tier(s).

    Args:
        tier: "1", "2", "3", or "all"

    Returns:
        Tuple of (symbols list, description)
    """
    if tier == "all":
        symbols = []
        for t in ["tier1", "tier2", "tier3"]:
            symbols.extend(LEVERAGED_ETFS[t]["symbols"])
        return symbols, "All tiers (19 leveraged ETFs)"

    tier_key = f"tier{tier}"
    if tier_key not in LEVERAGED_ETFS:
        raise ValueError(f"Invalid tier: {tier}. Use 1, 2, 3, or all")

    return LEVERAGED_ETFS[tier_key]["symbols"], LEVERAGED_ETFS[tier_key]["description"]


def setup_logging(verbose: bool = False):
    """Configure logging (system-agnostic paths)."""
    level = logging.DEBUG if verbose else logging.INFO
    log_file = project_root / "logs" / "leveraged_etf_collection.log"

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )


def estimate_collection(symbols: list, start_date: str, end_date: str) -> dict:
    """Estimate collection time for buffered mode."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Count trading days (exclude weekends)
    trading_days = sum(1 for d in range((end - start).days + 1) if (start + timedelta(days=d)).weekday() < 5)

    # Total API calls needed
    total_calls = trading_days * len(symbols)

    # Buffered mode: rate limit is the only bottleneck (DB writes are async)
    estimated_minutes = total_calls / 900

    return {
        "trading_days": trading_days,
        "total_calls": total_calls,
        "estimated_minutes": estimated_minutes,
        "estimated_hours": estimated_minutes / 60,
        "symbols_count": len(symbols),
    }


async def run_collection(args):
    """Run leveraged ETF collection."""
    # System-agnostic database path
    db_path = project_root / ".cache" / "options_historical.db"

    collector = HistoricalOptionsCollector(
        db_path=str(db_path),
        use_sqlite=True,
        rate_limit_per_minute=900,
    )

    if args.status:
        # Show status
        status = collector.get_collection_status()
        print("\n=== Leveraged ETF Collection Status ===")
        print(f"Storage: {status['storage']}")
        print(f"Database: {db_path}")

        if status["storage"] == "sqlite":
            stats = status.get("database_stats", {})
            print(f"Total records: {stats.get('total_options_records', 0):,}")
            print(f"Database size: {stats.get('db_size_mb', 0):.2f} MB")

            # Filter to show only leveraged ETFs
            all_leveraged = []
            for tier in LEVERAGED_ETFS.values():
                all_leveraged.extend(tier["symbols"])

            by_symbol = stats.get("by_symbol", {})
            leveraged_symbols = {k: v for k, v in by_symbol.items() if k in all_leveraged}

            if leveraged_symbols:
                print("\nLeveraged ETFs in database:")
                for sym, info in sorted(leveraged_symbols.items()):
                    print(
                        f"  {sym}: {info['records']:,} records, "
                        f"{info['trading_days']} days "
                        f"({info['min_date']} to {info['max_date']})"
                    )
            else:
                print("\nNo leveraged ETFs collected yet.")

            # Show which are missing
            missing = [s for s in all_leveraged if s not in by_symbol]
            if missing:
                print(f"\nMissing leveraged ETFs: {', '.join(missing)}")
        return

    # Determine symbols
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
        description = f"Custom symbols ({len(symbols)})"
    else:
        symbols, description = get_symbols_for_tier(args.tier)
        print(f"Using preset: {description}")

    # Parse dates
    start_date = args.start or "2020-01-01"
    end_date = args.end or today_str()

    # Show collection plan
    estimate = estimate_collection(symbols, start_date, end_date)

    print(f"\n{'='*70}")
    print("LEVERAGED ETF HISTORICAL OPTIONS COLLECTION")
    print(f"{'='*70}")
    print(f"\nPreset: {description}")
    mode_desc = (
        "Sequential (one symbol at a time)"
        if args.sequential
        else ("Buffered (RAM queue + async writes)" if args.buffered else "Standard parallel")
    )
    print(f"Mode: {mode_desc}")
    print(f"Symbols ({len(symbols)}): {', '.join(symbols)}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Database: {db_path}")
    print(f"Skip existing: {not args.force}")
    print()
    print(f"Estimated trading days: ~{estimate['trading_days']}")
    print(f"Total API calls needed: ~{estimate['total_calls']:,}")
    print(
        f"Estimated time (at 900/min): ~{estimate['estimated_minutes']:.1f} min ({estimate['estimated_hours']:.1f} hours)"
    )
    print()

    if not args.yes:
        response = input("Start collection? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return

    # Run collection
    print(f"\n{'='*70}")
    print("Starting collection...")
    print(f"{'='*70}\n")

    summary = await collector.collect_multi_symbol_historical(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        skip_existing=not args.force,
        parallel=not args.sequential,
        buffered=args.buffered if not args.sequential else False,
    )

    print(f"\n{'='*70}")
    print("COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"Mode: {summary.get('mode', 'parallel')}")
    print(f"Total API calls: {summary.get('total_api_calls', 'N/A')}")
    print(f"Successful: {summary.get('total_successful', 'N/A')}")
    print(f"Failed: {summary.get('total_failed', 'N/A')}")

    if "final_db_stats" in summary:
        stats = summary["final_db_stats"]
        print(f"\nDatabase stats:")
        print(f"  Total records: {stats.get('total_options_records', 0):,}")
        print(f"  Database size: {stats.get('db_size_mb', 0):.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Collect historical options data for leveraged/inverse ETFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Leveraged ETF Tiers:
  Tier 1 (default): TQQQ, SQQQ, SOXL, SOXS, UVXY
  Tier 2: SPXL, SPXS, UPRO, SPXU, TNA, TZA
  Tier 3: FAS, FAZ, LABU, LABD, TECL, TECS, NUGT, DUST

Examples:
  # Tier 1 only (highest liquidity)
  %(prog)s -y

  # All tiers (19 symbols)
  %(prog)s --tier all -y

  # Specific tier
  %(prog)s --tier 2 -y

  # Custom symbols
  %(prog)s --symbols TQQQ SQQQ SOXL -y

  # Check status
  %(prog)s --status

  # With buffered mode (faster on systems with more RAM)
  %(prog)s --tier all --buffered -y
        """,
    )

    # Tier/symbol selection
    symbol_group = parser.add_mutually_exclusive_group()
    symbol_group.add_argument("--tier", type=str, default="1", help="ETF tier to collect: 1, 2, 3, or all (default: 1)")
    symbol_group.add_argument("--symbols", type=str, nargs="+", help="Custom symbols to collect")

    # Date range
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD (default: 2020-01-01)")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD (default: today)")

    # Actions
    parser.add_argument("--status", action="store_true", help="Show collection status and exit")

    # Options
    parser.add_argument(
        "--buffered", action="store_true", help="Use buffered mode (RAM queue + async DB writes) - faster with more RAM"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run symbols sequentially (one at a time) - slower but avoids DB locks",
    )
    parser.add_argument("--force", action="store_true", help="Re-collect even if data exists")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()
    setup_logging(args.verbose)

    asyncio.run(run_collection(args))


if __name__ == "__main__":
    main()
