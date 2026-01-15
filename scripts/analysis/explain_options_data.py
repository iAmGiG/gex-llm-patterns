#!/usr/bin/env python3
"""Explain Options Data Structure.

Shows what we're collecting and how it enables GEX analysis.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd

from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient


def explain_options_data():
    """Walk through the options data structure and meaning."""
    print("=" * 60)
    print("🔍 WHAT YOU'RE LOOKING AT: SPY OPTIONS CHAIN DATA")
    print("=" * 60)

    # Get sample data
    cache = UnifiedCacheManager()
    client = AlphaVantageGEXClient(cache_manager=cache)
    data = client.fetch_historical_options("SPY", "2024-01-08")

    # 1. Dataset Overview
    print("\n📊 DATASET OVERVIEW:")
    print(f"   • Total contracts: {len(data):,}")
    print(f"   • Data columns: {len(data.columns)}")
    print(f"   • Date: January 8, 2024")
    print(f"   • Symbol: SPY (S&P 500 ETF)")
    print(f"   • Memory usage: {data.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

    # 2. What Each Row Represents
    print("\n🏷️  WHAT EACH ROW IS:")
    print("   • One specific options contract")
    print("   • Example: SPY Jan 8 2024 $475 Call")
    print("   • Each contract controls 100 shares of SPY")
    print("   • Includes all pricing, volume, and Greeks data")

    # 3. Strike Distribution
    strikes = sorted(data["strike"].dropna().unique())
    print(f"\n💰 STRIKE PRICES:")
    print(f"   • Range: ${strikes[0]:.0f} to ${strikes[-1]:.0f}")
    print(f"   • Total strikes: {len(strikes)}")
    print(f"   • Typical spacing: $1, $5, $10 intervals")
    print(f"   • Sample strikes: {[int(s) for s in strikes[:10]]}")

    # 4. Expiration Analysis
    expirations = sorted(data["expiration"].unique())
    print(f"\n📅 EXPIRATION DATES:")
    print(f"   • Total expirations: {len(expirations)}")
    print(f"   • 0 DTE (same day): {expirations[0].strftime('%Y-%m-%d')}")
    print(f"   • Near-term: {expirations[1].strftime('%Y-%m-%d')}, {expirations[2].strftime('%Y-%m-%d')}")
    print(f"   • LEAPs (long-term): {expirations[-1].strftime('%Y-%m-%d')}")

    # 5. Call vs Put Split
    call_count = len(data[data["type"] == "call"])
    put_count = len(data[data["type"] == "put"])
    print(f"\n📈 CALLS vs PUTS:")
    print(f"   • Calls: {call_count:,} contracts")
    print(f"   • Puts: {put_count:,} contracts")
    print(f"   • Balanced coverage across strikes")

    # 6. Key Columns for GEX
    print(f"\n🎯 CRITICAL COLUMNS FOR GEX CALCULATION:")
    key_columns = {
        "strike": "Strike price ($)",
        "type": "Call or Put",
        "open_interest": "Outstanding contracts",
        "gamma": "Price sensitivity (Greek)",
        "implied_volatility": "Market volatility expectation",
        "delta": "Hedge ratio (Greek)",
        "bid": "Buyer price",
        "ask": "Seller price",
        "volume": "Daily trading activity",
    }

    for col, desc in key_columns.items():
        print(f"   ✅ {col:15} → {desc}")

    # 7. Sample Data Around Current Price
    print(f"\n📋 SAMPLE DATA (Around $474 SPY Price):")
    gex_cols = ["strike", "type", "open_interest", "gamma", "delta", "implied_volatility"]
    sample = data[data["strike"].between(470, 478)][gex_cols].head(10)
    print(sample.to_string(index=False))

    # 8. Open Interest Analysis
    total_call_oi = data[data["type"] == "call"]["open_interest"].sum()
    total_put_oi = data[data["type"] == "put"]["open_interest"].sum()
    total_oi = total_call_oi + total_put_oi

    print(f"\n📊 OPEN INTEREST (Market Positioning):")
    print(f"   • Call Open Interest: {total_call_oi:,} contracts")
    print(f"   • Put Open Interest: {total_put_oi:,} contracts")
    print(f"   • Total: {total_oi:,} contracts")
    print(f"   • Share equivalent: {total_oi * 100:,} shares")
    print(f"   • Dollar exposure: ~${total_oi * 100 * 474 / 1e9:.1f}B")

    # 9. What This Enables
    print(f"\n🧮 WHAT THIS DATA ENABLES:")
    print("   🎯 Gamma Exposure (GEX) Calculation:")
    print("      → GEX = Spot × Gamma × Open Interest × 100")
    print("      → Separate for calls (+) and puts (-)")
    print("      → Sum across all strikes for total GEX")
    print()
    print("   📍 Key Level Identification:")
    print("      → Gamma Flip Point (where total GEX = 0)")
    print("      → Call Walls (high call gamma above price)")
    print("      → Put Floors (high put gamma below price)")
    print()
    print("   📊 Market Regime Classification:")
    print("      → Positive GEX = Dealers buy dips, sell rallies")
    print("      → Negative GEX = Dealers sell dips, buy rallies")
    print("      → Magnitude indicates strength of hedging flows")
    print()
    print("   🔮 Trading Signal Generation:")
    print("      → Predict price reactions at key levels")
    print("      → Identify high-probability reversal zones")
    print("      → Time entries around dealer rebalancing")

    print(f"\n" + "=" * 60)
    print("✅ This is the foundation for all GEX analysis!")
    print("   Next: Calculate GEX for each strike → Find patterns")
    print("=" * 60)


if __name__ == "__main__":
    explain_options_data()
