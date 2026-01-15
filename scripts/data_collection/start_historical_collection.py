#!/usr/bin/env python3
"""Start Historical Options Data Collection.

Script to begin systematic collection of historical options data from Alpha Vantage API. Configurable date ranges and
symbols.
"""

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from gex_db_infrastructure.data_sources.historical_collector import HistoricalOptionsCollector


def setup_logging(log_level="INFO", log_file=None):
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=handlers)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Collect historical options data from Alpha Vantage")

    parser.add_argument("--symbols", nargs="+", default=["SPY"], help="Symbols to collect (default: SPY)")

    parser.add_argument(
        "--start-date",
        default=(date.today() - timedelta(days=30)).strftime("%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format (default: 30 days ago)",
    )

    parser.add_argument(
        "--end-date", default=date.today().strftime("%Y-%m-%d"), help="End date in YYYY-MM-DD format (default: today)"
    )

    parser.add_argument("--rate-limit", type=int, default=70, help="API calls per minute (default: 70, max: 75)")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument("--log-file", help="Log file path (optional, defaults to console only)")

    parser.add_argument("--dry-run", action="store_true", help="Show what would be collected without making API calls")

    return parser.parse_args()


async def main():
    """Main collection function."""
    args = parse_arguments()

    # Setup logging
    log_file = args.log_file or f"historical_collection_{args.start_date}_{args.end_date}.log"
    setup_logging(args.log_level, log_file)

    logger = logging.getLogger(__name__)

    # Display collection plan
    logger.info("=" * 60)
    logger.info("HISTORICAL OPTIONS DATA COLLECTION")
    logger.info("=" * 60)
    logger.info(f"Symbols: {', '.join(args.symbols)}")
    logger.info(f"Date Range: {args.start_date} to {args.end_date}")
    logger.info(f"Rate Limit: {args.rate_limit} calls/minute")
    logger.info(f"Log File: {log_file}")
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("DRY RUN MODE - No API calls will be made")

        # Calculate estimated trading days
        collector = HistoricalOptionsCollector(rate_limit_per_minute=args.rate_limit)
        trading_dates = collector.get_trading_dates(args.start_date, args.end_date)

        total_calls = len(trading_dates) * len(args.symbols)
        estimated_minutes = total_calls / args.rate_limit
        estimated_hours = estimated_minutes / 60

        logger.info(f"Estimated trading days: {len(trading_dates)}")
        logger.info(f"Total API calls needed: {total_calls}")
        logger.info(f"Estimated time: {estimated_minutes:.1f} minutes ({estimated_hours:.1f} hours)")
        logger.info("Use --dry-run=false to start actual collection")
        return

    # Confirm with user for large collections
    trading_dates = HistoricalOptionsCollector().get_trading_dates(args.start_date, args.end_date)
    total_calls = len(trading_dates) * len(args.symbols)

    if total_calls > 100:
        response = input(f"This will make approximately {total_calls} API calls. Continue? (y/N): ")
        if response.lower() != "y":
            logger.info("Collection cancelled by user")
            return

    # Initialize collector
    collector = HistoricalOptionsCollector(rate_limit_per_minute=args.rate_limit)

    try:
        # Start collection
        summary = await collector.collect_multi_symbol_historical(
            symbols=args.symbols, start_date=args.start_date, end_date=args.end_date
        )

        # Display results
        logger.info("=" * 60)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total API Calls: {summary['total_api_calls']}")
        logger.info(f"Successful: {summary['total_successful']}")
        logger.info(f"Failed: {summary['total_failed']}")

        for symbol, symbol_summary in summary["symbol_summaries"].items():
            logger.info(f"{symbol}: {symbol_summary['completed_dates']} dates completed")

        logger.info("=" * 60)
        logger.info("Collection completed successfully!")

    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        logger.info("Progress has been saved and can be resumed later")
    except Exception as e:
        logger.error(f"Collection failed with error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
