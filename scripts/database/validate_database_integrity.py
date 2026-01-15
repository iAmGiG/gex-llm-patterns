"""Database Integrity Validation Script.

Compares database GEX values against fresh calculations to identify corruption. Checks all tables for data quality
issues.
"""

import logging
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

from gex_db_infrastructure.cache.options_db_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_gex_data(db_path: str, options_db: PostgreSQLOptionsManager, sample_size: int = 20):
    """Validate GEX data in database against fresh calculations.

    Uses PostgreSQL by default (migrated from SQLite).

    Args:
        db_path: Path to database
        options_db: PostgreSQLOptionsManager for fetching options data
        sample_size: Number of random dates to check

    Returns:
        Validation report dict
    """
    conn = sqlite3.connect(db_path)
    gex_calc = GEXCalculator()

    # Get sample of dates from database
    query = """
    SELECT symbol, date, total_gex, spot_price
    FROM daily_gex_metrics
    WHERE symbol = 'SPY'
    ORDER BY date DESC
    LIMIT ?
    """

    db_samples = pd.read_sql(query, conn, params=(sample_size,))

    logger.info(f"Validating {len(db_samples)} database entries...")

    results = []
    for _, row in db_samples.iterrows():
        symbol = row["symbol"]
        date = row["date"]
        db_gex = row["total_gex"]
        spot_price = row["spot_price"]

        # Issue #180: Get fresh options data from SQLite
        options_data = options_db.get_options_chain(symbol, date)

        if options_data is None or options_data.empty:
            results.append(
                {"date": date, "status": "NO_DATA", "db_gex": db_gex, "fresh_gex": None, "discrepancy": None}
            )
            continue

        # Calculate fresh GEX
        try:
            fresh_calc = gex_calc.calculate_gex_profile(options_data, spot_price if spot_price else None)
            fresh_gex = fresh_calc.get("net_gex", 0)

            # Calculate discrepancy
            if db_gex and fresh_gex:
                ratio = abs(fresh_gex / db_gex) if db_gex != 0 else float("inf")
                sign_match = (db_gex > 0) == (fresh_gex > 0)

                status = "OK" if (0.9 < ratio < 1.1 and sign_match) else "CORRUPT"
            else:
                ratio = None
                status = "MISSING"

            results.append(
                {
                    "date": date,
                    "status": status,
                    "db_gex": db_gex,
                    "fresh_gex": fresh_gex,
                    "discrepancy_ratio": ratio,
                    "sign_match": sign_match if "sign_match" in locals() else None,
                }
            )

        except Exception as e:
            logger.error(f"Error calculating fresh GEX for {date}: {e}")
            results.append({"date": date, "status": "ERROR", "db_gex": db_gex, "fresh_gex": None, "error": str(e)})

    conn.close()

    # Generate report
    results_df = pd.DataFrame(results)
    corrupt_count = len(results_df[results_df["status"] == "CORRUPT"])
    ok_count = len(results_df[results_df["status"] == "OK"])

    report = {
        "total_checked": len(results),
        "corrupt": corrupt_count,
        "ok": ok_count,
        "corrupt_pct": (corrupt_count / len(results) * 100) if len(results) > 0 else 0,
        "details": results_df,
    }

    return report


def check_database_schema(db_path: str):
    """Check database schema and table stats."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    schema_info = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        schema_info[table] = {"row_count": row_count, "columns": [col[1] for col in columns]}

    conn.close()
    return schema_info


if __name__ == "__main__":
    DB_PATH = ".cache/consolidated_historical.db"

    logger.info("=" * 80)
    logger.info("DATABASE INTEGRITY VALIDATION")
    logger.info("=" * 80)

    # Check if database exists
    if not Path(DB_PATH).exists():
        logger.error(f"Database not found: {DB_PATH}")
        sys.exit(1)

    # Check schema
    logger.info("\n1. Checking database schema...")
    schema = check_database_schema(DB_PATH)
    for table, info in schema.items():
        logger.info(f"  {table}: {info['row_count']} rows")

    # Validate GEX data (use PostgreSQL by default)
    logger.info("\n2. Validating GEX calculations...")
    options_db = PostgreSQLOptionsManager()
    report = validate_gex_data(DB_PATH, options_db, sample_size=20)

    logger.info(f"\nValidation Results:")
    logger.info(f"  Total checked: {report['total_checked']}")
    logger.info(f"  Corrupt: {report['corrupt']} ({report['corrupt_pct']:.1f}%)")
    logger.info(f"  OK: {report['ok']}")

    # Show examples
    if report["corrupt"] > 0:
        logger.info("\nExample Corruptions:")
        corrupt_samples = report["details"][report["details"]["status"] == "CORRUPT"].head(5)
        for _, row in corrupt_samples.iterrows():
            logger.info(
                f"  {row['date']}: DB={row['db_gex']:,.0f} vs Fresh={row['fresh_gex']:,.0f} "
                f"(ratio={row['discrepancy_ratio']:.1f}x)"
            )

    # Recommendation
    if report["corrupt_pct"] > 50:
        logger.warning("\n⚠️  DATABASE IS HEAVILY CORRUPTED")
        logger.warning("   Recommendation: Rebuild database from scratch")
    elif report["corrupt_pct"] > 10:
        logger.warning("\n⚠️  DATABASE HAS SIGNIFICANT CORRUPTION")
        logger.warning("   Recommendation: Rebuild corrupted sections")
    else:
        logger.info("\n✅ Database integrity is good")
