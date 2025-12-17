#!/usr/bin/env python3
"""Collection Progress Monitor - System-Agnostic.

Real-time monitoring of leveraged ETF historical options collection.
Shows progress, ETAs, and database growth for all tiers.

Designed for both Windows and Linux/HPCC environments.
"""

import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path (system-agnostic)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Leveraged ETF tiers (must match collect_leveraged_etfs.py)
LEVERAGED_ETFS = {
    "tier1": ["TQQQ", "SQQQ", "SOXL", "SOXS", "UVXY"],
    "tier2": ["SPXL", "SPXS", "UPRO", "SPXU", "TNA", "TZA"],
    "tier3": ["FAS", "FAZ", "LABU", "LABD", "TECL", "TECS", "NUGT", "DUST"],
}

ALL_SYMBOLS = []
for tier in LEVERAGED_ETFS.values():
    ALL_SYMBOLS.extend(tier)

# Collection date range
START_DATE = "2020-01-02"
END_DATE = datetime.now().strftime("%Y-%m-%d")


def get_trading_days_count(start_date: str, end_date: str) -> int:
    """Estimate trading days between dates (~252/year)."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (end - start).days
    # Rough estimate: 252 trading days / 365 calendar days
    return int(total_days * (252 / 365))


def get_collection_status(db_path: Path) -> dict:
    """Get detailed collection status for all leveraged ETFs."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Get database size
    db_size_mb = db_path.stat().st_size / (1024 * 1024)

    # Get total records
    cur.execute("SELECT COUNT(*) FROM options_chains")
    total_records = cur.fetchone()[0]

    # Get per-symbol stats
    cur.execute(
        """
        SELECT
            symbol,
            COUNT(*) as records,
            COUNT(DISTINCT trading_date) as trading_days,
            MIN(trading_date) as earliest,
            MAX(trading_date) as latest
        FROM options_chains
        WHERE symbol IN ({})
        GROUP BY symbol
    """.format(
            ",".join("?" * len(ALL_SYMBOLS))
        ),
        ALL_SYMBOLS,
    )

    symbol_stats = {}
    for row in cur.fetchall():
        symbol, records, days, earliest, latest = row
        symbol_stats[symbol] = {
            "records": records,
            "trading_days": days,
            "earliest": earliest,
            "latest": latest,
        }

    conn.close()

    # Calculate expected trading days
    expected_days = get_trading_days_count(START_DATE, END_DATE)

    return {
        "db_size_mb": db_size_mb,
        "total_records": total_records,
        "expected_days": expected_days,
        "symbol_stats": symbol_stats,
    }


def format_tier_status(tier_name: str, symbols: list, status: dict) -> str:
    """Format status display for a tier."""
    lines = []
    lines.append(f"\n{tier_name.upper()}:")
    lines.append("-" * 80)

    for symbol in symbols:
        if symbol in status["symbol_stats"]:
            stats = status["symbol_stats"][symbol]
            days_collected = stats["trading_days"]
            pct_complete = (days_collected / status["expected_days"]) * 100

            lines.append(
                f"  {symbol:<6} {stats['records']:>10,} records | "
                f"{days_collected:>4} days ({pct_complete:>5.1f}%) | "
                f"{stats['earliest']} to {stats['latest']}"
            )
        else:
            lines.append(f"  {symbol:<6} {'NOT STARTED':>10} | 0 days (0.0%)")

    return "\n".join(lines)


def calculate_eta(status: dict) -> dict:
    """Calculate ETA based on recent collection rate."""
    total_collected = sum(s["trading_days"] for s in status["symbol_stats"].values())
    total_needed = status["expected_days"] * len(ALL_SYMBOLS)
    remaining = total_needed - total_collected

    if remaining <= 0:
        return {"eta": "COMPLETE", "remaining_days": 0}

    # Assume ~150 dates/hour for sequential mode (conservative)
    hours_remaining = remaining / 150
    eta_time = datetime.now() + timedelta(hours=hours_remaining)

    return {
        "eta": eta_time.strftime("%Y-%m-%d %H:%M"),
        "remaining_days": remaining,
        "hours_remaining": hours_remaining,
    }


def display_status(db_path: Path, watch: bool = False):
    """Display collection status."""
    while True:
        status = get_collection_status(db_path)
        eta_info = calculate_eta(status)

        # Clear screen for watch mode
        if watch:
            print("\033[2J\033[H")  # ANSI clear screen

        print("=" * 80)
        print("LEVERAGED ETF COLLECTION MONITOR")
        print("=" * 80)
        print(f"Database: {db_path}")
        print(f"Size: {status['db_size_mb']:,.1f} MB | Records: {status['total_records']:,}")
        print(
            f"Target: {len(ALL_SYMBOLS)} symbols × {status['expected_days']} days = "
            f"{len(ALL_SYMBOLS) * status['expected_days']:,} total symbol-days"
        )
        print(f"\nETA: {eta_info['eta']} ({eta_info['remaining_days']:,} symbol-days remaining)")

        # Show tier-by-tier status
        for tier_name, symbols in LEVERAGED_ETFS.items():
            print(format_tier_status(tier_name, symbols, status))

        # Overall completion
        total_collected = sum(s["trading_days"] for s in status["symbol_stats"].values())
        total_needed = status["expected_days"] * len(ALL_SYMBOLS)
        overall_pct = (total_collected / total_needed) * 100

        print("\n" + "=" * 80)
        print(f"OVERALL PROGRESS: {total_collected:,}/{total_needed:,} symbol-days ({overall_pct:.1f}%)")
        print("=" * 80)

        if watch:
            print(f"\nUpdating every 60 seconds... (Ctrl+C to exit)")
            time.sleep(60)
        else:
            break


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Monitor leveraged ETF collection progress")
    parser.add_argument(
        "--db", type=str, default=str(project_root / ".cache" / "options_historical.db"), help="Path to SQLite database"
    )
    parser.add_argument("--watch", action="store_true", help="Watch mode - update every 60 seconds")

    args = parser.parse_args()
    db_path = Path(args.db)

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    try:
        display_status(db_path, watch=args.watch)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


if __name__ == "__main__":
    main()
