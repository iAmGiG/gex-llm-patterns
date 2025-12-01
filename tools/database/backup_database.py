#!/usr/bin/env python3
"""
On-Demand Database Backup Tool

Creates timestamped backups of GEX databases for safekeeping before
major operations like backfilling missing data.

Usage:
    python tools/database/backup_database.py
    python tools/database/backup_database.py --database gex_database.db
    python tools/database/backup_database.py --all
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class DatabaseBackupTool:
    """Tool for creating timestamped database backups."""

    def __init__(self, cache_dir=None):
        """Initialize backup tool.

        Args:
            cache_dir: Path to cache directory (default: .cache/)
        """
        self.cache_dir = Path(cache_dir) if cache_dir else project_root / ".cache"
        self.backup_dir = self.cache_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_timestamp(self):
        """Generate timestamp for backup filename."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_database_info(self, db_path):
        """Get information about database contents.

        Args:
            db_path: Path to database file

        Returns:
            Dict with database metadata
        """
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            # Get row counts for each table
            table_info = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                table_info[table] = count

            # Get date range if daily_gex_metrics exists
            date_range = None
            if "daily_gex_metrics" in tables:
                cursor.execute("SELECT MIN(date), MAX(date) FROM daily_gex_metrics;")
                min_date, max_date = cursor.fetchone()
                if min_date and max_date:
                    date_range = f"{min_date} to {max_date}"

            conn.close()

            return {
                "tables": tables,
                "table_info": table_info,
                "date_range": date_range,
                "size_mb": db_path.stat().st_size / (1024 * 1024),
            }

        except Exception as e:
            return {"error": str(e)}

    def backup_database(self, db_name, description=None):
        """Create timestamped backup of database.

        Args:
            db_name: Name of database file (e.g., 'gex_database.db')
            description: Optional description for backup

        Returns:
            Path to backup file
        """
        source_path = self.cache_dir / db_name

        if not source_path.exists():
            raise FileNotFoundError(f"Database not found: {source_path}")

        # Get database info before backup
        db_info = self.get_database_info(source_path)

        # Create backup filename
        timestamp = self.get_timestamp()
        base_name = source_path.stem
        backup_name = f"{base_name}_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_name

        # Copy database file
        print(f"Creating backup: {backup_name}")
        print(f"Source: {source_path}")
        print(f"Destination: {backup_path}")

        shutil.copy2(source_path, backup_path)

        # Verify backup
        backup_info = self.get_database_info(backup_path)

        # Display results
        print(f"\n✅ Backup created successfully!")
        print(f"   Size: {db_info.get('size_mb', 0):.2f} MB")

        if "date_range" in db_info and db_info["date_range"]:
            print(f"   Date Range: {db_info['date_range']}")

        if "table_info" in db_info:
            print(f"   Tables:")
            for table, count in db_info["table_info"].items():
                print(f"      - {table}: {count:,} rows")

        # Save metadata file
        metadata_path = backup_path.with_suffix(".txt")
        with open(metadata_path, "w") as f:
            f.write(f"Database Backup Metadata\n")
            f.write(f"=" * 50 + "\n\n")
            f.write(f"Backup Created: {datetime.now().isoformat()}\n")
            f.write(f"Source Database: {db_name}\n")
            f.write(f"Backup File: {backup_name}\n")
            f.write(f"Size: {db_info.get('size_mb', 0):.2f} MB\n")

            if description:
                f.write(f"Description: {description}\n")

            f.write(f"\nDatabase Contents:\n")
            f.write(f"-" * 50 + "\n")

            if "date_range" in db_info and db_info["date_range"]:
                f.write(f"Date Range: {db_info['date_range']}\n")

            if "table_info" in db_info:
                f.write(f"\nTables:\n")
                for table, count in db_info["table_info"].items():
                    f.write(f"  - {table}: {count:,} rows\n")

        print(f"\n📝 Metadata saved: {metadata_path.name}")

        return backup_path

    def backup_all(self, description=None):
        """Backup all databases in cache directory.

        Args:
            description: Optional description for backups

        Returns:
            List of backup paths created
        """
        db_files = list(self.cache_dir.glob("*.db"))

        # Filter out existing backups
        db_files = [f for f in db_files if "backup" not in f.name.lower()]

        if not db_files:
            print("No database files found to backup.")
            return []

        print(f"Found {len(db_files)} database(s) to backup:")
        for db in db_files:
            print(f"  - {db.name}")
        print()

        backups = []
        for db_file in db_files:
            try:
                backup_path = self.backup_database(db_file.name, description)
                backups.append(backup_path)
                print()
            except Exception as e:
                print(f"❌ Failed to backup {db_file.name}: {e}")
                print()

        return backups

    def list_backups(self):
        """List all existing backups."""
        backups = sorted(self.backup_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True)

        if not backups:
            print("No backups found.")
            return

        print(f"\nExisting Backups ({len(backups)}):")
        print("=" * 80)

        for backup in backups:
            size_mb = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)

            print(f"\n{backup.name}")
            print(f"  Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Size: {size_mb:.2f} MB")

            # Check if metadata file exists
            metadata_path = backup.with_suffix(".txt")
            if metadata_path.exists():
                print(f"  Metadata: {metadata_path.name}")


def main():
    """Main entry point for backup tool."""
    parser = argparse.ArgumentParser(
        description="Create timestamped backups of GEX databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Backup main GEX database
  python tools/database/backup_database.py

  # Backup specific database
  python tools/database/backup_database.py --database consolidated_historical.db

  # Backup all databases
  python tools/database/backup_database.py --all

  # Add description to backup
  python tools/database/backup_database.py --description "Before Issue #102 backfill"

  # List existing backups
  python tools/database/backup_database.py --list
        """,
    )

    parser.add_argument(
        "--database", default="gex_database.db", help="Database file to backup (default: gex_database.db)"
    )

    parser.add_argument("--all", action="store_true", help="Backup all database files in .cache/")

    parser.add_argument("--list", action="store_true", help="List existing backups")

    parser.add_argument("--description", help="Optional description for the backup")

    parser.add_argument("--cache-dir", help="Path to cache directory (default: .cache/)")

    args = parser.parse_args()

    # Initialize backup tool
    backup_tool = DatabaseBackupTool(cache_dir=args.cache_dir)

    # Handle list command
    if args.list:
        backup_tool.list_backups()
        return

    # Handle backup commands
    try:
        if args.all:
            backups = backup_tool.backup_all(description=args.description)
            print(f"\n✅ Created {len(backups)} backup(s)")
        else:
            backup_path = backup_tool.backup_database(args.database, description=args.description)
            print(f"\n✅ Backup location: {backup_path}")

        print(f"\n💡 Tip: Use --list to see all backups")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
