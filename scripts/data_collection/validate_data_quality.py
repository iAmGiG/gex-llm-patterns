#!/usr/bin/env python3
"""Data Quality Validation - System-Agnostic.

Validates leveraged ETF options data quality:
- Checks for date gaps
- Identifies market holidays
- Validates contract counts
- Checks for data anomalies

Designed for both Windows and Linux/HPCC environments.
"""

import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path (system-agnostic)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Known market holidays (simplified - major ones only)
MARKET_HOLIDAYS_2020_2025 = [
    "2020-01-01",
    "2020-01-20",
    "2020-02-17",
    "2020-04-10",
    "2020-05-25",
    "2020-07-03",
    "2020-09-07",
    "2020-11-26",
    "2020-12-25",
    "2021-01-01",
    "2021-01-18",
    "2021-02-15",
    "2021-04-02",
    "2021-05-31",
    "2021-07-05",
    "2021-09-06",
    "2021-11-25",
    "2021-12-24",
    "2022-01-17",
    "2022-02-21",
    "2022-04-15",
    "2022-05-30",
    "2022-06-20",
    "2022-07-04",
    "2022-09-05",
    "2022-11-24",
    "2022-12-26",
    "2023-01-02",
    "2023-01-16",
    "2023-02-20",
    "2023-04-07",
    "2023-05-29",
    "2023-06-19",
    "2023-07-04",
    "2023-09-04",
    "2023-11-23",
    "2023-12-25",
    "2024-01-01",
    "2024-01-15",
    "2024-02-19",
    "2024-03-29",
    "2024-05-27",
    "2024-06-19",
    "2024-07-04",
    "2024-09-02",
    "2024-11-28",
    "2024-12-25",
    "2025-01-01",
    "2025-01-20",
    "2025-02-17",
    "2025-04-18",
    "2025-05-26",
    "2025-06-19",
    "2025-07-04",
    "2025-09-01",
    "2025-11-27",
    "2025-12-25",
]


def get_trading_dates(symbol: str, db_path: Path) -> set:
    """Get all trading dates for a symbol."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT trading_date FROM options_chains WHERE symbol = ? ORDER BY trading_date", (symbol,))
    dates = {row[0] for row in cur.fetchall()}
    conn.close()
    return dates


def get_contract_counts(symbol: str, db_path: Path) -> dict:
    """Get contract counts per trading date."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT trading_date, COUNT(*) as cnt
        FROM options_chains
        WHERE symbol = ?
        GROUP BY trading_date
        ORDER BY trading_date
        """,
        (symbol,),
    )
    counts = {row[0]: row[1] for row in cur.fetchall()}
    conn.close()
    return counts


def find_gaps(trading_dates: set, start_date: str, end_date: str) -> list:
    """Find missing trading days (excluding weekends and known holidays)."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    gaps = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")

        # Skip weekends
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue

        # Skip known holidays
        if date_str in MARKET_HOLIDAYS_2020_2025:
            current += timedelta(days=1)
            continue

        # Check if we have data for this date
        if date_str not in trading_dates:
            gaps.append(date_str)

        current += timedelta(days=1)

    return gaps


def find_anomalies(contract_counts: dict) -> dict:
    """Find dates with unusually low/high contract counts."""
    if not contract_counts:
        return {"low": [], "high": []}

    counts = list(contract_counts.values())
    avg_count = sum(counts) / len(counts)
    std_dev = (sum((x - avg_count) ** 2 for x in counts) / len(counts)) ** 0.5

    low_threshold = avg_count - 2 * std_dev
    high_threshold = avg_count + 2 * std_dev

    anomalies = {"low": [], "high": [], "avg": avg_count, "std": std_dev}

    for date, count in contract_counts.items():
        if count < low_threshold:
            anomalies["low"].append((date, count))
        elif count > high_threshold:
            anomalies["high"].append((date, count))

    return anomalies


def validate_symbol(symbol: str, db_path: Path, verbose: bool = False) -> dict:
    """Validate data quality for a single symbol."""
    print(f"\n{'='*80}")
    print(f"Validating {symbol}")
    print(f"{'='*80}")

    trading_dates = get_trading_dates(symbol, db_path)
    contract_counts = get_contract_counts(symbol, db_path)

    if not trading_dates:
        print(f"  ERROR: No data found for {symbol}")
        return {"symbol": symbol, "has_data": False}

    # Date range
    min_date = min(trading_dates)
    max_date = max(trading_dates)
    print(f"  Date range: {min_date} to {max_date}")
    print(f"  Trading days collected: {len(trading_dates)}")

    # Find gaps
    gaps = find_gaps(trading_dates, min_date, max_date)
    if gaps:
        print(f"  WARNING: {len(gaps)} missing trading days")
        if verbose:
            for gap in gaps[:10]:  # Show first 10
                print(f"    - {gap}")
            if len(gaps) > 10:
                print(f"    ... and {len(gaps) - 10} more")
    else:
        print(f"  OK: No gaps in trading days")

    # Contract count analysis
    total_contracts = sum(contract_counts.values())
    avg_contracts = total_contracts / len(contract_counts) if contract_counts else 0
    print(f"  Total contracts: {total_contracts:,}")
    print(f"  Avg contracts/day: {avg_contracts:.0f}")

    # Find anomalies
    anomalies = find_anomalies(contract_counts)
    if anomalies["low"]:
        print(f"  WARNING: {len(anomalies['low'])} days with unusually low contract counts")
        if verbose:
            for date, count in sorted(anomalies["low"])[:5]:
                print(f"    - {date}: {count} contracts (avg: {anomalies['avg']:.0f})")
    if anomalies["high"]:
        print(f"  NOTE: {len(anomalies['high'])} days with unusually high contract counts")
        if verbose:
            for date, count in sorted(anomalies["high"])[:5]:
                print(f"    - {date}: {count} contracts (avg: {anomalies['avg']:.0f})")

    if not gaps and not anomalies["low"]:
        print(f"  ✓ Data quality looks good")

    return {
        "symbol": symbol,
        "has_data": True,
        "date_range": (min_date, max_date),
        "trading_days": len(trading_dates),
        "total_contracts": total_contracts,
        "gaps": len(gaps),
        "low_anomalies": len(anomalies["low"]),
        "high_anomalies": len(anomalies["high"]),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate leveraged ETF options data quality")
    parser.add_argument(
        "--db", type=str, default=str(project_root / ".cache" / "options_historical.db"), help="Path to SQLite database"
    )
    parser.add_argument("--symbols", type=str, nargs="+", help="Symbols to validate (default: all leveraged ETFs)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed anomaly information")

    args = parser.parse_args()
    db_path = Path(args.db)

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    # Default to all leveraged ETFs
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        symbols = [
            "TQQQ",
            "SQQQ",
            "SOXL",
            "SOXS",
            "UVXY",
            "SPXL",
            "SPXS",
            "UPRO",
            "SPXU",
            "TNA",
            "TZA",
            "FAS",
            "FAZ",
            "LABU",
            "LABD",
            "TECL",
            "TECS",
            "NUGT",
            "DUST",
        ]

    print("=" * 80)
    print("LEVERAGED ETF DATA QUALITY VALIDATION")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Symbols to validate: {len(symbols)}")

    results = []
    for symbol in symbols:
        result = validate_symbol(symbol, db_path, verbose=args.verbose)
        results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")

    symbols_with_data = [r for r in results if r["has_data"]]
    symbols_without_data = [r for r in results if not r["has_data"]]

    print(f"\nSymbols with data: {len(symbols_with_data)}/{len(symbols)}")
    if symbols_without_data:
        print(f"Symbols without data: {', '.join(r['symbol'] for r in symbols_without_data)}")

    symbols_with_gaps = [r for r in symbols_with_data if r["gaps"] > 0]
    if symbols_with_gaps:
        print(f"\nSymbols with date gaps: {len(symbols_with_gaps)}")
        for r in symbols_with_gaps:
            print(f"  {r['symbol']}: {r['gaps']} gaps")

    symbols_with_anomalies = [r for r in symbols_with_data if r["low_anomalies"] > 0]
    if symbols_with_anomalies:
        print(f"\nSymbols with low contract count anomalies: {len(symbols_with_anomalies)}")
        for r in symbols_with_anomalies:
            print(f"  {r['symbol']}: {r['low_anomalies']} days")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    main()
