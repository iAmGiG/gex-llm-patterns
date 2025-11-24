#!/usr/bin/env python3
"""
Rebuild GEX Database with Real Spot Prices

Rebuilds the database using the fixed get_stock_price() method that:
- Uses put-call parity estimation
- Fetches from API if needed
- Raises error instead of storing obfuscated 450.0 prices

Run this after fixing the architectural violation where obfuscated
prices were being stored in the database.
"""

import logging
import sys
from pathlib import Path

from data_sources.historical_gex_builder import HistoricalGEXDatabaseBuilder

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

logger = logging.getLogger(__name__)

print("=" * 80)
print("REBUILDING GEX DATABASE WITH REAL SPOT PRICES")
print("=" * 80)
print()
print("Fix: get_stock_price() now uses real data sources")
print("  Method 1: underlyingPrice column from options data")
print("  Method 2: Put-call parity estimation")
print("  Method 3: Polygon API fetch")
print("  No fallback: Raises error instead of storing 450.0")
print()
print("Building SPY for full 2024 (Jan-Dec)...")
print()

builder = HistoricalGEXDatabaseBuilder()

stats = builder.build_gex_database(
    symbols=["SPY"], start_date="2024-01-01", end_date="2024-12-31", min_quality_score=60
)

print()
print("=" * 80)
print("REBUILD COMPLETE")
print("=" * 80)
print(f"Days successful: {stats['total_days_successful']}/{stats['total_days_attempted']}")
print(f"Duration: {stats['build_duration_minutes']:.2f} minutes")
print(f"Database: {stats['database_path']}")
print()
print("Next steps:")
print("  1. Verify Q3 spot prices (should be ~$545-560, NOT 450.0)")
print("  2. Re-run all quarter validations")
print("  3. Compare results to determine pattern viability")
