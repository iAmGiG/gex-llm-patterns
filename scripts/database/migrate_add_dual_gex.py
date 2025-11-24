#!/usr/bin/env python3
"""
Database Migration: Add Dual GEX Columns (Issue #138)

Purpose:
    Add columns to daily_gex_metrics table to store dual GEX metrics:
    - gex_oi: Structural positioning (open interest weighted)
    - gex_volume: Economic activity (volume weighted)
    - activity_ratio: |gex_volume / gex_oi| (hedging intensity)
    - economic_regime: HIGH_FRAGILITY, ELEVATED_RISK, STABLE_POSITIVE, TRANSITIONAL

Backward Compatibility:
    - New columns are nullable (optional)
    - Existing total_gex column unchanged (aggregate metric)
    - Existing queries will continue to work

Usage:
    python scripts/database/migrate_add_dual_gex.py --database .cache/consolidated_historical.db
"""

import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DualGEXMigration:
    """Migrate database to support dual GEX metrics."""

    def __init__(self, database_path: str):
        """Initialize migration with database path."""
        self.database_path = Path(database_path)
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {database_path}")

        logger.info(f"Initializing migration for: {self.database_path}")

    def create_backup(self) -> Path:
        """Create backup of database before migration."""
        backup_path = (
            self.database_path.parent
            / f"{self.database_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )

        logger.info(f"Creating backup: {backup_path}")

        # Copy database file
        import shutil

        shutil.copy2(self.database_path, backup_path)

        logger.info(f"✅ Backup created: {backup_path}")
        return backup_path

    def check_if_migration_needed(self, conn: sqlite3.Connection) -> bool:
        """Check if migration is needed (columns don't exist yet)."""
        cursor = conn.execute("PRAGMA table_info(daily_gex_metrics);")
        columns = [row[1] for row in cursor.fetchall()]

        dual_gex_columns = ["gex_oi", "gex_volume", "activity_ratio", "economic_regime"]
        existing_dual_columns = [col for col in dual_gex_columns if col in columns]

        if existing_dual_columns:
            logger.warning(f"Some dual GEX columns already exist: {existing_dual_columns}")
            return False

        logger.info("Migration needed - dual GEX columns not found")
        return True

    def add_dual_gex_columns(self, conn: sqlite3.Connection):
        """Add dual GEX columns to daily_gex_metrics table."""
        logger.info("Adding dual GEX columns to daily_gex_metrics table...")

        # Add columns (nullable for backward compatibility)
        migrations = [
            "ALTER TABLE daily_gex_metrics ADD COLUMN gex_oi REAL;",
            "ALTER TABLE daily_gex_metrics ADD COLUMN gex_volume REAL;",
            "ALTER TABLE daily_gex_metrics ADD COLUMN activity_ratio REAL;",
            "ALTER TABLE daily_gex_metrics ADD COLUMN economic_regime TEXT;",
        ]

        for migration_sql in migrations:
            try:
                conn.execute(migration_sql)
                logger.info(f"✅ Executed: {migration_sql}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logger.warning(f"Column already exists, skipping: {e}")
                else:
                    raise

        conn.commit()
        logger.info("✅ All dual GEX columns added successfully")

    def verify_migration(self, conn: sqlite3.Connection) -> bool:
        """Verify migration completed successfully."""
        logger.info("Verifying migration...")

        cursor = conn.execute("PRAGMA table_info(daily_gex_metrics);")
        columns = [row[1] for row in cursor.fetchall()]

        required_columns = ["gex_oi", "gex_volume", "activity_ratio", "economic_regime"]
        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            logger.error(f"❌ Migration incomplete - missing: {missing_columns}")
            return False

        logger.info(f"✅ All required columns present: {required_columns}")

        # Verify backward compatibility (existing data still accessible)
        cursor = conn.execute("SELECT COUNT(*) FROM daily_gex_metrics WHERE total_gex IS NOT NULL;")
        existing_count = cursor.fetchone()[0]
        logger.info(f"✅ Backward compatibility verified - {existing_count} existing records accessible")

        return True

    def run_migration(self, create_backup: bool = True):
        """Execute the migration."""
        logger.info("=" * 80)
        logger.info("DUAL GEX DATABASE MIGRATION (Issue #138)")
        logger.info("=" * 80)

        # Step 1: Create backup
        if create_backup:
            backup_path = self.create_backup()
            logger.info(f"Backup saved to: {backup_path}")

        # Step 2: Connect to database
        conn = sqlite3.connect(self.database_path)

        try:
            # Step 3: Check if migration needed
            if not self.check_if_migration_needed(conn):
                logger.warning("Migration may have already been applied - verify manually")
                return False

            # Step 4: Add columns
            self.add_dual_gex_columns(conn)

            # Step 5: Verify migration
            if not self.verify_migration(conn):
                logger.error("Migration verification failed")
                return False

            logger.info("=" * 80)
            logger.info("✅ MIGRATION COMPLETE")
            logger.info("=" * 80)
            logger.info("\nNext steps:")
            logger.info("1. Update HistoricalGEXDatabaseBuilder to populate dual metrics")
            logger.info("2. Run backfill on sample data (Q1 2024) to test integration")
            logger.info("3. Verify agent queries work with new columns")

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            conn.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Migrate database to support dual GEX metrics (Issue #138)")
    parser.add_argument(
        "--database",
        type=str,
        default=".cache/consolidated_historical.db",
        help="Path to database file (default: .cache/consolidated_historical.db)",
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation (NOT recommended)")

    args = parser.parse_args()

    # Run migration
    migration = DualGEXMigration(args.database)
    success = migration.run_migration(create_backup=not args.no_backup)

    if success:
        print("\n✅ Migration completed successfully")
        return 0
    else:
        print("\n❌ Migration failed - check logs above")
        return 1


if __name__ == "__main__":
    exit(main())
