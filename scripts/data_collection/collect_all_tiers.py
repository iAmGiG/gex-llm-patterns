#!/usr/bin/env python3
"""Auto-Queue All Tiers Collection - System-Agnostic.

Sequentially collects all three tiers of leveraged ETFs.
Runs Tier 1, then Tier 2, then Tier 3 automatically.

Designed for both Windows and Linux/HPCC environments.
Can be run unattended for full collection.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path (system-agnostic)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.data_sources.historical_collector import HistoricalOptionsCollector
from src.utils.date_utils import today_str

# Leveraged ETF tiers (must match collect_leveraged_etfs.py)
TIERS = {
    "tier1": {
        "name": "Tier 1: Highest Liquidity",
        "symbols": ["TQQQ", "SQQQ", "SOXL", "SOXS", "UVXY"],
    },
    "tier2": {
        "name": "Tier 2: S&P & Russell Leveraged",
        "symbols": ["SPXL", "SPXS", "UPRO", "SPXU", "TNA", "TZA"],
    },
    "tier3": {
        "name": "Tier 3: Sector-Specific Leveraged",
        "symbols": ["FAS", "FAZ", "LABU", "LABD", "TECL", "TECS", "NUGT", "DUST"],
    },
}


def setup_logging(log_dir: Path):
    """Configure logging for tier collection."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"all_tiers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


async def collect_tier(
    collector: HistoricalOptionsCollector,
    tier_name: str,
    symbols: list,
    start_date: str,
    end_date: str,
    logger: logging.Logger,
    sequential: bool = True,
) -> dict:
    """Collect a single tier of symbols."""
    logger.info(f"\n{'='*80}")
    logger.info(f"STARTING {tier_name.upper()}")
    logger.info(f"{'='*80}")
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Mode: {'Sequential' if sequential else 'Parallel'}")

    tier_start = datetime.now()

    summary = await collector.collect_multi_symbol_historical(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        skip_existing=True,
        parallel=not sequential,
        buffered=False if sequential else True,
    )

    tier_duration = datetime.now() - tier_start

    logger.info(f"\n{'='*80}")
    logger.info(f"{tier_name.upper()} COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Duration: {tier_duration}")
    logger.info(f"Mode: {summary.get('mode', 'N/A')}")
    logger.info(f"Total API calls: {summary.get('total_api_calls', 'N/A')}")
    logger.info(f"Successful: {summary.get('total_successful', 'N/A')}")
    logger.info(f"Failed: {summary.get('total_failed', 'N/A')}")

    return {
        "tier": tier_name,
        "duration": tier_duration,
        "summary": summary,
    }


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-queue all tiers of leveraged ETF collection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script sequentially collects all three tiers:
  - Tier 1: TQQQ, SQQQ, SOXL, SOXS, UVXY (5 symbols)
  - Tier 2: SPXL, SPXS, UPRO, SPXU, TNA, TZA (6 symbols)
  - Tier 3: FAS, FAZ, LABU, LABD, TECL, TECS, NUGT, DUST (8 symbols)

Total: 19 leveraged ETF symbols

Example:
  # Run all tiers sequentially from 2020 to present
  %(prog)s --sequential -y

  # Start from a specific date (useful for resuming)
  %(prog)s --start 2023-01-01 --sequential -y

  # Skip specific tiers (e.g., if Tier 1 already complete)
  %(prog)s --skip-tier1 --sequential -y
        """,
    )

    parser.add_argument("--start", type=str, default="2020-01-01", help="Start date YYYY-MM-DD (default: 2020-01-01)")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--sequential", action="store_true", help="Run in sequential mode (slower but more stable)")
    parser.add_argument("--skip-tier1", action="store_true", help="Skip Tier 1 collection")
    parser.add_argument("--skip-tier2", action="store_true", help="Skip Tier 2 collection")
    parser.add_argument("--skip-tier3", action="store_true", help="Skip Tier 3 collection")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    args = parser.parse_args()

    # Setup
    log_dir = project_root / "logs" / "collection"
    logger = setup_logging(log_dir)

    db_path = project_root / ".cache" / "options_historical.db"
    start_date = args.start
    end_date = args.end or today_str()

    # Determine which tiers to run
    tiers_to_run = []
    if not args.skip_tier1:
        tiers_to_run.append(("tier1", TIERS["tier1"]))
    if not args.skip_tier2:
        tiers_to_run.append(("tier2", TIERS["tier2"]))
    if not args.skip_tier3:
        tiers_to_run.append(("tier3", TIERS["tier3"]))

    if not tiers_to_run:
        logger.error("All tiers skipped - nothing to collect!")
        return

    total_symbols = sum(len(tier["symbols"]) for _, tier in tiers_to_run)

    logger.info(f"\n{'='*80}")
    logger.info("LEVERAGED ETF MULTI-TIER COLLECTION")
    logger.info(f"{'='*80}")
    logger.info(f"Database: {db_path}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Mode: {'Sequential' if args.sequential else 'Parallel/Buffered'}")
    logger.info(f"Total symbols: {total_symbols} across {len(tiers_to_run)} tiers")
    logger.info("")
    for tier_key, tier in tiers_to_run:
        logger.info(f"  {tier['name']}: {', '.join(tier['symbols'])}")

    if not args.yes:
        response = input("\nStart multi-tier collection? [y/N]: ")
        if response.lower() != "y":
            logger.info("Aborted.")
            return

    # Initialize collector
    collector = HistoricalOptionsCollector(
        db_path=str(db_path),
        use_sqlite=True,
        rate_limit_per_minute=900,
    )

    # Run each tier sequentially
    collection_start = datetime.now()
    tier_results = []

    for tier_key, tier in tiers_to_run:
        result = await collect_tier(
            collector=collector,
            tier_name=tier["name"],
            symbols=tier["symbols"],
            start_date=start_date,
            end_date=end_date,
            logger=logger,
            sequential=args.sequential,
        )
        tier_results.append(result)

    # Final summary
    total_duration = datetime.now() - collection_start

    logger.info(f"\n{'='*80}")
    logger.info("ALL TIERS COMPLETE")
    logger.info(f"{'='*80}")
    logger.info(f"Total duration: {total_duration}")
    logger.info("")
    for result in tier_results:
        logger.info(f"  {result['tier']}: {result['duration']}")

    # Get final database stats
    status = collector.get_collection_status()
    if status.get("storage") == "sqlite":
        stats = status.get("database_stats", {})
        logger.info(f"\nFinal database stats:")
        logger.info(f"  Total records: {stats.get('total_options_records', 0):,}")
        logger.info(f"  Database size: {stats.get('db_size_mb', 0):.2f} MB")

    logger.info(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
