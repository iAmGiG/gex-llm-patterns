"""Test validation system on real production data.

Fetches live options data from Alpha Vantage and validates it.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging

from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_validation_on_real_data():
    """Test validation with real API data."""

    print("=" * 70)
    print("Testing Validation on Real Production Data")
    print("=" * 70)

    # Initialize clients
    print("\n[1] Initializing Alpha Vantage client and SQLite manager...")
    av_client = AlphaVantageGEXClient()
    db_manager = SQLiteOptionsManager(# db_path=".cache/options_historical.db"  # Migrated to PostgreSQL, enable_validation=True)

    # Fetch real data
    symbol = "SPY"
    print(f"\n[2] Fetching latest options data for {symbol} from Alpha Vantage...")

    # Get most recent trading date data
    from src.utils.date_utils import add_business_days, today_str

    # Try today and last few days
    for days_back in range(0, 5):
        test_date = add_business_days(today_str(), -days_back)
        print(f"  Trying date: {test_date}")

        options_df = av_client.fetch_historical_options(symbol, test_date)

        if options_df is not None and not options_df.empty:
            print(f"  [OK] Got {len(options_df)} contracts for {test_date}")
            trading_date = test_date
            break
    else:
        print("  [FAIL] Could not fetch data for any recent date")
        return False

    # Show sample of raw data
    print(f"\n[3] Sample of raw data (first 3 records):")
    # Handle both 'type' and 'option_type' column names
    type_col = "type" if "type" in options_df.columns else "option_type"
    oi_col = "open_interest" if "open_interest" in options_df.columns else "openInterest"
    iv_col = "implied_volatility" if "implied_volatility" in options_df.columns else "impliedVolatility"

    display_cols = ["strike", type_col, "bid", "ask", "delta", "gamma", oi_col, iv_col]
    print(options_df.head(3)[display_cols])

    # Check for potential validation issues in raw data
    print(f"\n[4] Pre-validation data quality check:")

    # Check bid > ask
    if "bid" in options_df.columns and "ask" in options_df.columns:
        bid_ask_issues = options_df[
            (options_df["bid"].notna()) & (options_df["ask"].notna()) & (options_df["bid"] > options_df["ask"])
        ]
        print(f"  Bid > Ask violations: {len(bid_ask_issues)}")

    # Check delta ranges
    if "delta" in options_df.columns and type_col in options_df.columns:
        call_delta_issues = options_df[
            (options_df[type_col] == "call") & ((options_df["delta"] < 0) | (options_df["delta"] > 1))
        ]
        put_delta_issues = options_df[
            (options_df[type_col] == "put") & ((options_df["delta"] < -1) | (options_df["delta"] > 0))
        ]
        print(f"  Call delta out of range: {len(call_delta_issues)}")
        print(f"  Put delta out of range: {len(put_delta_issues)}")

    # Check gamma
    if "gamma" in options_df.columns:
        gamma_issues = options_df[(options_df["gamma"].notna()) & (options_df["gamma"] < 0)]
        print(f"  Negative gamma: {len(gamma_issues)}")

    # Check OI
    if oi_col in options_df.columns:
        oi_issues = options_df[(options_df[oi_col].notna()) & (options_df[oi_col] < 0)]
        print(f"  Negative open interest: {len(oi_issues)}")

    # Store with validation
    print(f"\n[5] Storing data with validation enabled...")
    inserted = db_manager.store_options_chain(symbol, trading_date, options_df)

    print(f"  Input records: {len(options_df)}")
    print(f"  Stored records: {inserted}")
    print(f"  Rejected: {len(options_df) - inserted}")

    # Check validation quality score in database
    print(f"\n[6] Checking validation quality score in database...")
    progress = db_manager.get_collection_progress(symbol)

    if not progress.empty:
        recent = progress[progress["trading_date"] == trading_date]

        if not recent.empty:
            quality_score = recent["validation_quality_score"].iloc[0]
            status = recent["status"].iloc[0]
            contracts_count = recent["contracts_count"].iloc[0]

            print(f"  Status: {status}")
            print(f"  Contracts stored: {contracts_count}")
            print(f"  Quality score: {quality_score:.4f}")

            # Interpret quality score
            if quality_score >= 0.9:
                print(f"  Quality: EXCELLENT [OK]")
            elif quality_score >= 0.7:
                print(f"  Quality: GOOD [OK]")
            elif quality_score >= 0.5:
                print(f"  Quality: ACCEPTABLE [OK]")
            else:
                print(f"  Quality: POOR [FAIL]")
        else:
            print(f"  No progress record found for {trading_date}")
    else:
        print(f"  No progress records found")

    # Verify schema migration
    print(f"\n[7] Verifying schema migration...")
    import sqlite3

    with sqlite3.connect(db_manager.db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(collection_progress)")
        columns = {row[1] for row in cursor.fetchall()}

        if "validation_quality_score" in columns:
            print(f"  [OK] validation_quality_score column exists")
        else:
            print(f"  [FAIL] validation_quality_score column missing!")
            return False

    # Retrieve and verify stored data
    print(f"\n[8] Retrieving and verifying stored data...")
    retrieved = db_manager.get_options_chain(symbol, trading_date)

    if retrieved is not None and not retrieved.empty:
        print(f"  [OK] Retrieved {len(retrieved)} contracts")

        # Verify no critical violations in stored data
        print(f"\n[9] Verifying stored data quality (should have no critical violations):")

        # Check bid > ask
        bid_ask_violations = retrieved[
            (retrieved["bid"].notna()) & (retrieved["ask"].notna()) & (retrieved["bid"] > retrieved["ask"])
        ]
        print(f"  Bid > Ask: {len(bid_ask_violations)} (should be 0)")

        # Check delta
        call_violations = retrieved[
            (retrieved["option_type"] == "call")
            & (retrieved["delta"].notna())
            & ((retrieved["delta"] < 0) | (retrieved["delta"] > 1))
        ]
        put_violations = retrieved[
            (retrieved["option_type"] == "put")
            & (retrieved["delta"].notna())
            & ((retrieved["delta"] < -1) | (retrieved["delta"] > 0))
        ]
        print(f"  Call delta violations: {len(call_violations)} (should be 0)")
        print(f"  Put delta violations: {len(put_violations)} (should be 0)")

        # Check gamma
        gamma_violations = retrieved[(retrieved["gamma"].notna()) & (retrieved["gamma"] < 0)]
        print(f"  Negative gamma: {len(gamma_violations)} (should be 0)")

        # Check OI
        oi_violations = retrieved[(retrieved["open_interest"].notna()) & (retrieved["open_interest"] < 0)]
        print(f"  Negative OI: {len(oi_violations)} (should be 0)")

        total_violations = (
            len(bid_ask_violations)
            + len(call_violations)
            + len(put_violations)
            + len(gamma_violations)
            + len(oi_violations)
        )

        if total_violations == 0:
            print(f"\n  [OK] All stored data passes validation checks!")
        else:
            print(f"\n  [FAIL] Found {total_violations} violations in stored data")
            return False
    else:
        print(f"  [FAIL] Could not retrieve stored data")
        return False

    # Summary
    print("\n" + "=" * 70)
    print("PRODUCTION VALIDATION TEST RESULTS")
    print("=" * 70)
    print(f"Symbol: {symbol}")
    print(f"Trading Date: {trading_date}")
    print(f"Total Contracts Fetched: {len(options_df)}")
    print(f"Contracts Stored: {inserted}")
    print(f"Contracts Rejected: {len(options_df) - inserted}")
    print(f"Quality Score: {quality_score:.4f}")
    print(f"Critical Violations in DB: {total_violations}")

    if total_violations == 0 and inserted > 0:
        print("\n[OK] VALIDATION SYSTEM WORKING CORRECTLY ON PRODUCTION DATA")
        return True
    else:
        print("\n[FAIL] VALIDATION SYSTEM ISSUES DETECTED")
        return False


if __name__ == "__main__":
    success = test_validation_on_real_data()
    sys.exit(0 if success else 1)
