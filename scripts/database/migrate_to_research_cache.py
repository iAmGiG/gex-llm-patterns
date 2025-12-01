#!/usr/bin/env python3
"""Migrate existing GEX cache data to new ResearchCache schema.

This script migrates data from:
- GEXCacheManager (SQLite index + JSON/Parquet files)
- UnifiedCacheManager (pickle files)

To the new ResearchCache production database.

Usage:
    python scripts/database/migrate_to_research_cache.py [--dry-run] [--verbose]

Options:
    --dry-run   Show what would be migrated without making changes
    --verbose   Show detailed progress
"""

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

import pandas as pd

from src.cache.research_cache import ResearchCache
from src.utils.date_utils import now_iso

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CacheMigrator:
    """Migrate existing cache data to ResearchCache."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.cache_dir = Path(".cache")
        self.stats = {"gex_summaries": 0, "gex_strikes": 0, "options_chains": 0, "market_data": 0, "errors": 0}

        if not dry_run:
            self.research_cache = ResearchCache()
        else:
            self.research_cache = None

    def migrate_all(self):
        """Run complete migration."""
        logger.info("=" * 60)
        logger.info("Starting cache migration to ResearchCache")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 60)

        # 1. Migrate GEX cache (from gex_cache_manager SQLite index)
        self.migrate_gex_cache()

        # 2. Migrate options pickle files
        self.migrate_options_cache()

        # 3. Migrate market data pickle files
        self.migrate_market_data()

        # 4. Print summary
        self.print_summary()

    def migrate_gex_cache(self):
        """Migrate GEX data from existing gex_cache_manager."""
        logger.info("\n--- Migrating GEX Cache ---")

        # Check for old GEX index
        old_index_path = self.cache_dir / "index" / "gex_cache_index.sqlite"
        if not old_index_path.exists():
            logger.warning(f"No GEX index found at {old_index_path}")
            return

        try:
            with sqlite3.connect(old_index_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get all indexed GEX calculations
                cursor = conn.execute(
                    """
                    SELECT symbol, trading_date, file_path, total_gex, net_gex,
                           flip_point, underlying_price, contracts_processed,
                           calculation_duration_ms, calculation_timestamp
                    FROM gex_cache_index
                    ORDER BY trading_date
                """
                )

                rows = cursor.fetchall()
                logger.info(f"Found {len(rows)} GEX calculations to migrate")

                for row in rows:
                    self._migrate_single_gex(dict(row))

        except Exception as e:
            logger.error(f"Error migrating GEX cache: {e}")
            self.stats["errors"] += 1

    def _migrate_single_gex(self, row: dict):
        """Migrate a single GEX calculation."""
        symbol = row["symbol"]
        trading_date = row["trading_date"]

        if self.verbose:
            logger.info(f"  Migrating GEX: {symbol} {trading_date}")

        # Load the full summary JSON if available
        summary_path = self.cache_dir / "gex_data" / symbol / trading_date / "gex_summary.json"
        gex_data = {}

        if summary_path.exists():
            try:
                with open(summary_path) as f:
                    gex_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load summary for {symbol} {trading_date}: {e}")

        # Merge with index data
        gex_data.update(
            {
                "total_gex": row.get("total_gex"),
                "net_gex": row.get("net_gex"),
                "flip_point": row.get("flip_point"),
                "underlying_price": row.get("underlying_price"),
                "contracts_processed": row.get("contracts_processed"),
                "calculation_duration_ms": row.get("calculation_duration_ms"),
                "calculation_timestamp": row.get("calculation_timestamp") or now_iso(),
            }
        )

        # Load strike breakdown if available
        strike_df = None
        strike_parquet = self.cache_dir / "gex_data" / symbol / trading_date / "gex_by_strike.parquet"
        strike_pickle = self.cache_dir / "gex_data" / symbol / trading_date / "gex_by_strike.pickle"

        if strike_parquet.exists():
            try:
                strike_df = pd.read_parquet(strike_parquet)
                self.stats["gex_strikes"] += 1
            except Exception as e:
                logger.warning(f"Could not load parquet for {symbol} {trading_date}: {e}")
        elif strike_pickle.exists():
            try:
                strike_df = pd.read_pickle(strike_pickle)
                self.stats["gex_strikes"] += 1
            except Exception as e:
                logger.warning(f"Could not load pickle for {symbol} {trading_date}: {e}")

        # Store in new cache
        if not self.dry_run:
            try:
                self.research_cache.set_gex_summary(
                    symbol=symbol, trading_date=trading_date, gex_data=gex_data, strike_df=strike_df
                )
                self.stats["gex_summaries"] += 1
            except Exception as e:
                logger.error(f"Error storing GEX {symbol} {trading_date}: {e}")
                self.stats["errors"] += 1
        else:
            self.stats["gex_summaries"] += 1

    def migrate_options_cache(self):
        """Migrate options pickle files."""
        logger.info("\n--- Migrating Options Cache ---")

        options_dir = self.cache_dir / "options"
        if not options_dir.exists():
            logger.warning(f"No options directory found at {options_dir}")
            return

        for symbol_dir in options_dir.iterdir():
            if not symbol_dir.is_dir():
                continue

            symbol = symbol_dir.name.upper()

            for pickle_file in symbol_dir.glob("*.pickle"):
                trading_date = pickle_file.stem

                if self.verbose:
                    logger.info(f"  Migrating options: {symbol} {trading_date}")

                try:
                    df = pd.read_pickle(pickle_file)

                    if not self.dry_run and not df.empty:
                        # Store in new cache (would need options_chain table population)
                        # For now, just count
                        pass

                    self.stats["options_chains"] += 1

                except Exception as e:
                    logger.error(f"Error migrating options {symbol} {trading_date}: {e}")
                    self.stats["errors"] += 1

        logger.info(f"Found {self.stats['options_chains']} options files")

    def migrate_market_data(self):
        """Migrate market data pickle files."""
        logger.info("\n--- Migrating Market Data ---")

        market_dir = self.cache_dir / "market_data"
        if not market_dir.exists():
            logger.warning(f"No market data directory found at {market_dir}")
            return

        for symbol_dir in market_dir.iterdir():
            if not symbol_dir.is_dir():
                continue

            symbol = symbol_dir.name.upper()

            for pickle_file in symbol_dir.glob("*.pickle"):
                if self.verbose:
                    logger.info(f"  Migrating market data: {symbol} {pickle_file.stem}")

                try:
                    df = pd.read_pickle(pickle_file)

                    if not self.dry_run and not df.empty:
                        self.research_cache.set_market_data(symbol=symbol, data=df, source="migrated_pickle")

                    self.stats["market_data"] += 1

                except Exception as e:
                    logger.error(f"Error migrating market data {symbol}: {e}")
                    self.stats["errors"] += 1

    def print_summary(self):
        """Print migration summary."""
        logger.info("\n" + "=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"GEX Summaries:    {self.stats['gex_summaries']}")
        logger.info(f"GEX Strike Files: {self.stats['gex_strikes']}")
        logger.info(f"Options Chains:   {self.stats['options_chains']}")
        logger.info(f"Market Data:      {self.stats['market_data']}")
        logger.info(f"Errors:           {self.stats['errors']}")
        logger.info("=" * 60)

        if self.dry_run:
            logger.info("DRY RUN - No changes were made")
        else:
            # Show new cache stats
            cache_stats = self.research_cache.get_cache_stats()
            logger.info("\nNew ResearchCache Stats:")
            for key, value in cache_stats.items():
                logger.info(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description="Migrate existing cache to ResearchCache")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")
    parser.add_argument("--verbose", action="store_true", help="Show detailed progress")

    args = parser.parse_args()

    migrator = CacheMigrator(dry_run=args.dry_run, verbose=args.verbose)
    migrator.migrate_all()


if __name__ == "__main__":
    main()
