#!/usr/bin/env python3
"""
Batch API wrapper for validate_regime_windows.py

Provides CLI interface for OpenAI Batch API mode for regime validation.

Usage (submit batch):
    python validate_regime_windows_batch.py \\
      --start-date 2024-01-02 \\
      --end-date 2024-03-29 \\
      --submit

Usage (poll batch):
    python validate_regime_windows_batch.py \\
      --batch-id batch_66d4d5c11ecf4f4fa1b30b8c7adf11ce \\
      --poll

Usage (retrieve results):
    python validate_regime_windows_batch.py \\
      --batch-id batch_66d4d5c11ecf4f4fa1b30b8c7adf11ce \\
      --retrieve

Cost Savings:
    - Phase 1 (32 windows): $2.50 → $1.25 (save $1.25)
    - Phase 3 (223 windows): $18 → $9 (save $9)
    - Phase 4 (223 windows): $18 → $9 (save $9)
    - Total: ~$19 savings across all phases

Related: Issue #112 - OpenAI Batch API for cost optimization
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.validation.batch_regime_validator import BatchRegimeValidator
from src.data_sources.sequential_gex_fetcher import SequentialGEXFetcher
from src.validation.regime_classifier import RegimeClassifier
from src.cache.unified_cache import UnifiedCacheManager
from src.validation.data_obfuscation import DataObfuscator

logger = logging.getLogger(__name__)


def prepare_windows(
    start_date: str,
    end_date: str,
    symbol: str = "SPY",
    window_size: int = 30,
    sample_every_n: int = 1
) -> List[Dict]:
    """
    Prepare regime windows for batch submission.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        symbol: Ticker symbol (default SPY)
        window_size: Regime window size (default 30)
        sample_every_n: Sample every N days (default 1 = all days)

    Returns:
        List of window dicts with 'end_date' and 'gex_values'
    """
    logger.info(f"Preparing windows: {start_date} to {end_date}")

    cache_manager = UnifiedCacheManager()
    gex_fetcher = SequentialGEXFetcher(
        cache_manager=cache_manager,
        window_size=window_size
    )
    obfuscator = DataObfuscator()

    # Get trading days in range
    from datetime import datetime as dt
    start_dt = dt.strptime(start_date, "%Y-%m-%d")
    end_dt = dt.strptime(end_date, "%Y-%m-%d")

    # Fetch from cache
    trading_days = cache_manager.get_trading_days_in_range(symbol, start_date, end_date)
    logger.info(f"Found {len(trading_days)} trading days in range")

    # Potential window ends (must have at least window_size days before)
    potential_window_ends = [d for d in trading_days if trading_days.index(d) >= window_size - 1]
    logger.info(f"Can create {len(potential_window_ends)} potential windows")

    # Sample
    if sample_every_n > 1:
        potential_window_ends = potential_window_ends[::sample_every_n]
        logger.info(f"Sampled to {len(potential_window_ends)} windows (every {sample_every_n} days)")

    # Fetch GEX for each window
    windows = []
    for i, end_date_window in enumerate(potential_window_ends):
        logger.info(f"Window {i+1}/{len(potential_window_ends)}: {end_date_window}")

        result = gex_fetcher.get_sequential_gex(
            symbol=symbol,
            end_date=end_date_window
        )

        if result is None:
            logger.warning(f"Could not fetch window for {end_date_window} - skipping")
            continue

        gex_sequence = result['gex_sequence']

        if len(gex_sequence) != window_size:
            logger.warning(f"Window has {len(gex_sequence)} days, expected {window_size} - skipping")
            continue

        # Extract GEX values (obfuscated format not needed for batch file, just values)
        gex_values = [entry['net_gex'] for entry in gex_sequence]

        windows.append({
            "end_date": end_date_window,
            "gex_values": gex_values,
            "start_date": gex_sequence[0]['date'] if gex_sequence else None
        })

    logger.info(f"Prepared {len(windows)} valid windows for batch")
    return windows


def submit_batch_job(
    start_date: str,
    end_date: str,
    symbol: str = "SPY",
    sample_every_n: int = 1
) -> str:
    """
    Prepare and submit batch job.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        symbol: Ticker symbol (default SPY)
        sample_every_n: Sample every N days (default 1)

    Returns:
        Batch job ID
    """
    logger.info(f"Submitting batch job: {start_date} to {end_date}")

    # Prepare windows
    windows = prepare_windows(start_date, end_date, symbol, sample_every_n=sample_every_n)

    if not windows:
        logger.error("No valid windows prepared - cannot submit batch")
        return None

    logger.info(f"Submitting {len(windows)} windows")

    # Create validator and prepare batch file
    validator = BatchRegimeValidator()
    batch_file = validator.prepare_batch_file(windows)

    # Submit batch
    description = f"Regime validation {start_date} to {end_date} ({len(windows)} windows)"
    batch_id = validator.submit_batch(batch_file, description=description)

    logger.info(f"✅ Batch submitted successfully!")
    logger.info(f"Batch ID: {batch_id}")
    logger.info(f"Windows: {len(windows)}")
    logger.info(f"Expected cost: ${len(windows) * 0.03 * 0.5:.2f} (50% of sync API)")
    logger.info(f"Expected time: 1-2 hours")
    logger.info(f"")
    logger.info(f"To poll status:")
    logger.info(f"  python validate_regime_windows_batch.py --batch-id {batch_id} --poll")
    logger.info(f"")
    logger.info(f"To retrieve results (after completion):")
    logger.info(f"  python validate_regime_windows_batch.py --batch-id {batch_id} --retrieve")

    return batch_id


def poll_batch_job(batch_id: str, poll_interval: int = 60) -> Dict:
    """
    Poll batch job status.

    Args:
        batch_id: Batch job ID
        poll_interval: Seconds between polls (default 60)

    Returns:
        Final status dict
    """
    logger.info(f"Polling batch: {batch_id}")
    logger.info(f"Poll interval: {poll_interval}s")
    logger.info(f"Max duration: 24 hours")
    logger.info("")
    logger.info("Waiting for batch completion... (press Ctrl+C to stop)")

    validator = BatchRegimeValidator()
    status = validator.poll_batch(batch_id, poll_interval=poll_interval)

    if status['status'] == 'completed':
        logger.info(f"✅ Batch completed!")
        logger.info(f"Output file ID: {status['output_file_id']}")
        logger.info(f"Elapsed time: {status['elapsed_seconds']/60:.1f} minutes")
        logger.info(f"Request counts: {status['request_counts']}")
        logger.info(f"")
        logger.info(f"To retrieve results:")
        logger.info(f"  python validate_regime_windows_batch.py --batch-id {batch_id} --retrieve")
    else:
        logger.error(f"❌ Batch failed or timed out: {status['status']}")

    return status


def retrieve_batch_results(batch_id: str) -> List[Dict]:
    """
    Retrieve batch results and save as YAML.

    Args:
        batch_id: Batch job ID

    Returns:
        List of parsed results
    """
    logger.info(f"Retrieving results for batch: {batch_id}")

    validator = BatchRegimeValidator()
    results = validator.retrieve_results(batch_id)

    if not results:
        logger.error("No results retrieved")
        return []

    # Save as YAML
    output_file = PROJECT_ROOT / "reports" / "validation" / "regime_windows" / f"phase_batch_{batch_id}.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    validator.save_results_yaml(results, [], output_file, batch_id)

    logger.info(f"✅ Retrieved {len(results)} results")
    logger.info(f"Saved to: {output_file}")

    # Print summary
    detected = sum(1 for r in results if r.get('regime_detected', False))
    logger.info(f"")
    logger.info(f"Summary:")
    logger.info(f"  Detection rate: {detected}/{len(results)} ({100*detected/len(results):.1f}%)")
    logger.info(f"  Avg confidence: {sum(r.get('confidence', 0) for r in results)/len(results):.0f}%")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="OpenAI Batch API validator for regime windows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Submit Phase 1 Q1 2024 (32 windows)
  python validate_regime_windows_batch.py \\
    --start-date 2024-01-02 \\
    --end-date 2024-03-29 \\
    --submit

  # Poll batch status
  python validate_regime_windows_batch.py \\
    --batch-id batch_66d4d5c11ecf4f4fa1b30b8c7adf11ce \\
    --poll \\
    --poll-interval 10

  # Retrieve results after completion
  python validate_regime_windows_batch.py \\
    --batch-id batch_66d4d5c11ecf4f4fa1b30b8c7adf11ce \\
    --retrieve

Cost savings: 50% reduction ($0.15 vs $0.30 per 1M tokens)
        """
    )

    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, default="SPY", help="Ticker symbol (default: SPY)")
    parser.add_argument("--sample-every-n", type=int, default=1, help="Sample every N days (default: 1)")

    parser.add_argument("--submit", action="store_true", help="Prepare and submit batch job")
    parser.add_argument("--batch-id", type=str, help="Batch ID for polling/retrieval")
    parser.add_argument("--poll", action="store_true", help="Poll batch status")
    parser.add_argument("--poll-interval", type=int, default=60, help="Poll interval in seconds (default: 60)")
    parser.add_argument("--retrieve", action="store_true", help="Retrieve batch results")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.submit:
        if not args.start_date or not args.end_date:
            parser.error("--submit requires --start-date and --end-date")
        submit_batch_job(args.start_date, args.end_date, args.symbol, args.sample_every_n)

    elif args.poll:
        if not args.batch_id:
            parser.error("--poll requires --batch-id")
        poll_batch_job(args.batch_id, args.poll_interval)

    elif args.retrieve:
        if not args.batch_id:
            parser.error("--retrieve requires --batch-id")
        retrieve_batch_results(args.batch_id)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
