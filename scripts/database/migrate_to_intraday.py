#!/usr/bin/env python3
"""Database Migration Script for Intraday Support Adds intraday tables alongside existing daily tables."""

import logging
import sqlite3
import sys
from pathlib import Path

from src.utils.date_utils import format_for_filename, now_iso

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class IntradayMigration:
    """Database migration manager for intraday support."""

    def __init__(self, db_path: str = ".cache/consolidated_historical.db"):
        """Initialize migration with database path."""
        self.db_path = Path(db_path)
        self.backup_path = Path(f"{db_path}.backup_{format_for_filename()}")
        self.schema_path = Path(__file__).parent / "create_intraday_schema.sql"

    def create_backup(self) -> bool:
        """Create backup of existing database."""
        try:
            if self.db_path.exists():
                import shutil

                shutil.copy2(self.db_path, self.backup_path)
                logger.info(f"Created backup: {self.backup_path}")
                return True
            else:
                logger.info("No existing database to backup")
                return True
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def check_existing_schema(self) -> dict:
        """Check what tables already exist."""
        if not self.db_path.exists():
            logger.info("Database doesn't exist - will create new")
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
                )

                existing_tables = [row[0] for row in cursor.fetchall()]

                logger.info(f"Existing tables: {existing_tables}")

                return {
                    "daily_gex_metrics": "daily_gex_metrics" in existing_tables,
                    "strike_gex_details": "strike_gex_details" in existing_tables,
                    "intraday_gex_metrics": "intraday_gex_metrics" in existing_tables,
                    "intraday_strike_details": "intraday_strike_details" in existing_tables,
                    "algo_time_markers": "algo_time_markers" in existing_tables,
                }
        except Exception as e:
            logger.error(f"Failed to check schema: {e}")
            return {}

    def apply_schema(self) -> bool:
        """Apply the intraday schema to database."""
        try:
            # Read schema file
            if not self.schema_path.exists():
                logger.error(f"Schema file not found: {self.schema_path}")
                return False

            with open(self.schema_path, "r") as f:
                schema_sql = f.read()

            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Apply schema
            with sqlite3.connect(self.db_path) as conn:
                # Execute the entire schema at once - SQLite can handle it
                try:
                    conn.executescript(schema_sql)
                    logger.info("Executed complete schema script")
                except sqlite3.Error as e:
                    logger.error(f"Schema execution failed: {e}")
                    return False

                conn.commit()
                logger.info("Schema applied successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to apply schema: {e}")
            return False

    def validate_migration(self) -> bool:
        """Validate that migration completed successfully."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check that new tables exist
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN (
                        'intraday_gex_metrics',
                        'intraday_strike_details',
                        'algo_time_markers'
                    )
                """
                )

                new_tables = [row[0] for row in cursor.fetchall()]
                expected_tables = ["intraday_gex_metrics", "intraday_strike_details", "algo_time_markers"]

                missing_tables = set(expected_tables) - set(new_tables)
                if missing_tables:
                    logger.error(f"Missing tables after migration: {missing_tables}")
                    return False

                # Check that indexes exist
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name LIKE 'idx_intraday%'
                """
                )

                indexes = [row[0] for row in cursor.fetchall()]
                logger.info(f"Created indexes: {indexes}")

                # Check that views exist
                cursor = conn.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='view' AND name IN (
                        'friday_gamma_analysis',
                        'key_algo_times',
                        'max_gamma_strikes',
                        'friday_330_validation'
                    )
                """
                )

                views = [row[0] for row in cursor.fetchall()]
                logger.info(f"Created views: {views}")

                logger.info("Migration validation successful")
                return True

        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False

    def get_migration_info(self) -> dict:
        """Get information about the migration."""
        schema_status = self.check_existing_schema()

        return {
            "database_path": str(self.db_path),
            "database_exists": self.db_path.exists(),
            "backup_path": str(self.backup_path),
            "schema_file": str(self.schema_path),
            "existing_tables": schema_status,
            "migration_needed": not schema_status.get("intraday_gex_metrics", False),
            "database_size": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }

    def run_migration(self, force: bool = False) -> bool:
        """Run complete migration process."""
        logger.info("Starting intraday database migration")

        # Get current status
        info = self.get_migration_info()
        logger.info(f"Database info: {info}")

        # Check if migration needed
        if not force and not info["migration_needed"]:
            logger.info("Migration not needed - intraday tables already exist")
            return True

        # Create backup
        if not self.create_backup():
            logger.error("Backup failed - aborting migration")
            return False

        # Apply schema
        if not self.apply_schema():
            logger.error("Schema application failed")
            return False

        # Validate results
        if not self.validate_migration():
            logger.error("Migration validation failed")
            return False

        logger.info("Intraday migration completed successfully")
        return True


def main():
    """Run migration from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate database for intraday support")
    parser.add_argument("--db-path", default=".cache/consolidated_historical.db", help="Database path")
    parser.add_argument("--force", action="store_true", help="Force migration even if tables exist")
    parser.add_argument("--info", action="store_true", help="Show migration info without running")

    args = parser.parse_args()

    migration = IntradayMigration(args.db_path)

    if args.info:
        info = migration.get_migration_info()
        print("\nMigration Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        return

    success = migration.run_migration(force=args.force)

    if success:
        print("\n✅ Migration completed successfully")
        print(f"Database: {args.db_path}")
        print(f"Backup created: {migration.backup_path}")
    else:
        print("\n❌ Migration failed - check logs")
        sys.exit(1)


if __name__ == "__main__":
    main()
