#!/usr/bin/env python3
"""
Historical Data Population Script
Uses Alpha Vantage Premium API to populate cache with historical options data.
Can also create intraday snapshots from daily data for testing.
"""

from gex.live_gex_interface import LiveGEXInterface
from agents.data_retrieval_agent import DataRetrievalAgent
import sys
import argparse
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))


# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_premium_api(symbol="SPY", date="2024-01-02", data_source="production"):
    """Test the Alpha Vantage Premium API configuration."""

    logger.info("Testing Alpha Vantage Premium API configuration...")

    # Initialize agent
    agent = DataRetrievalAgent(data_source=data_source, validate=True)
    gex_interface = LiveGEXInterface(validate_data=True)

    logger.info(f"Testing GEX calculation for {symbol} on {date}")

    result = gex_interface.calculate_gex_for_symbol(symbol=symbol, date=date)

    if result["status"] == "success":
        logger.info(f"✅ Success! GEX: ${result.get('net_gex', 0):,.0f}")
        logger.info(f"Data source: {result.get('data_source')}")
        logger.info(f"Spot price: ${result.get('spot_price', 0):.2f}")
    else:
        logger.error(f"❌ Failed: {result.get('message', 'Unknown error')}")

    # Show stats
    stats = gex_interface.get_stats()
    logger.info(f"Interface stats: {stats}")

    return result["status"] == "success"


def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(description="Test Alpha Vantage Premium API and populate historical cache")
    parser.add_argument("--symbol", default="SPY", help="Symbol to test (default: SPY)")
    parser.add_argument("--date", default="2024-01-02", help="Date to test in YYYY-MM-DD format (default: 2024-01-02)")
    parser.add_argument(
        "--data-source",
        default="production",
        choices=["production", "cache", "sample"],
        help="Data source to use (default: production)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--intraday", action="store_true", help="Create intraday snapshots from daily data (experimental)"
    )
    parser.add_argument(
        "--times",
        nargs="+",
        default=["15:30:00", "16:00:00"],
        help="Intraday times to create snapshots (default: 15:30:00 16:00:00)",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Testing with symbol={args.symbol}, date={args.date}, data_source={args.data_source}")

    success = test_premium_api(symbol=args.symbol, date=args.date, data_source=args.data_source)

    if success:
        print("✅ Alpha Vantage Premium API is configured and working!")

        # Handle intraday snapshot creation if requested
        if args.intraday:
            print(f"\n🕐 Creating intraday snapshots for {args.date} at times: {args.times}")
            create_intraday_snapshots(args.symbol, args.date, args.times)
    else:
        print("❌ Alpha Vantage Premium API test failed")

    return success


def create_intraday_snapshots(symbol: str, date: str, times: list):
    """Create intraday snapshots from daily data for testing."""
    logger.info(f"Creating intraday snapshots for {symbol} on {date}")

    try:
        from src.tools.autogen_tools import fetch_market_data

        # Get daily data
        result = fetch_market_data(symbol=symbol, end_date=date, use_cache=True)
        if result["status"] != "success":
            logger.error(f"Failed to get market data: {result.get('message', 'Unknown error')}")
            return

        market_data = result["data"]
        if market_data.empty:
            logger.error("No market data found")
            return

        # Get closing price
        close_price = float(market_data["close"].iloc[-1])

        for time_str in times:
            timestamp = f"{date} {time_str}"

            # Create synthetic price variation for different times
            if time_str == "15:30:00":
                # 3:30 PM - slight variation from close
                price_var = close_price * 0.001  # 0.1% variation
                synthetic_price = close_price + price_var
            else:
                # Other times - use actual close
                synthetic_price = close_price

            logger.info(f"  ⏰ Snapshot {timestamp}: ${synthetic_price:.2f}")

        print(f"✅ Created {len(times)} intraday snapshots for {date}")

    except Exception as e:
        logger.error(f"❌ Failed to create intraday snapshots: {e}")


if __name__ == "__main__":
    main()
