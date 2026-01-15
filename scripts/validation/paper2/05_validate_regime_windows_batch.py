#!/usr/bin/env python3
"""Batch API wrapper for validate_regime_windows.py.

Provides CLI interface for OpenAI Batch API mode for regime validation.

UPGRADED (November 19, 2025): Now supports phase transformations for negative controls:
  - Phase 1 (default): Normal regime validation with real GEX data
  - Phase 2a (--phase shuffle): Shuffle GEX day order (destroys temporal structure)
  - Phase 2b (--phase transitional): Artificially add 7-10 sign flips (creates high volatility)
  - Phase 2c (--phase low-magnitude): Scale GEX values down by 75% (<$3B avg)

All phases use REAL market data from historical database (no synthetic data).

Usage (Phase 1 - normal validation):
    python validate_regime_windows_batch.py \\
      --start-date 2024-01-02 \\
      --end-date 2024-03-29 \\
      --submit

Usage (Phase 2a - shuffled negative control):
    python validate_regime_windows_batch.py \\
      --start-date 2024-01-02 \\
      --end-date 2024-03-29 \\
      --phase shuffle \\
      --submit

Usage (Phase 2b - transitional negative control):
    python validate_regime_windows_batch.py \\
      --start-date 2024-01-02 \\
      --end-date 2024-03-29 \\
      --phase transitional \\
      --submit

Usage (Phase 2c - low-magnitude negative control):
    python validate_regime_windows_batch.py \\
      --start-date 2024-01-02 \\
      --end-date 2024-03-29 \\
      --phase low-magnitude \\
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
    - Phase 1 (52 windows): $1.62 → $0.81 (save $0.81)
    - Phase 2 (30 windows): $0.96 → $0.48 (save $0.48)
    - Phase 3 (223 windows): $3.50 → $1.75 (save $1.75)
    - Phase 4 (223 windows): $3.50 → $1.75 (save $1.75)
    - Total: ~$4.79 savings across all phases

Related: Issue #112 - OpenAI Batch API for cost optimization
"""

import argparse
import logging
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from gex_db_infrastructure.cache.research_cache import ResearchCache
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.sequential_gex_fetcher import SequentialGEXFetcher
from gex_db_infrastructure.validation.batch_regime_validator import BatchRegimeValidator
from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator
from gex_db_infrastructure.validation.regime_classifier import RegimeClassifier

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


def prepare_windows(
    start_date: str,
    end_date: str,
    symbol: str = "SPY",
    window_size: int = 30,
    sample_every_n: int = 1,
    phase: str = None,
) -> List[Dict]:
    """Prepare regime windows for batch submission with optional transformations.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        symbol: Ticker symbol (default SPY)
        window_size: Regime window size (default 30)
        sample_every_n: Sample every N days (default 1 = all days)
        phase: Transformation phase (None, 'shuffle', 'transitional', 'low-magnitude')

    Returns:
        List of window dicts with 'end_date' and 'gex_sequence'

    Phase Transformations:
        - None: Normal validation (Phase 1, 3, 4)
        - 'shuffle': Randomize GEX day order (Phase 2a - destroys temporal structure)
        - 'transitional': Artificially add 7-10 sign flips (Phase 2b - tests stability criterion)
        - 'low-magnitude': Scale GEX down 75% (Phase 2c - tests magnitude threshold)
    """
    phase_label = phase if phase else "normal"
    logger.info(f"Preparing windows: {start_date} to {end_date} (phase: {phase_label})")

    cache_manager = UnifiedCacheManager()
    gex_fetcher = SequentialGEXFetcher(cache_manager=cache_manager, window_size=window_size)
    obfuscator = DataObfuscator()

    # Get ALL trading days available in cache (need historical context for 30-day windows)
    cache_dir = Path(f".cache/gex_data/{symbol}")

    if not cache_dir.exists():
        logger.error(f"Cache directory not found: {cache_dir}")
        return []

    # Scan for date directories with GEX data
    available_dates = []
    for date_dir in cache_dir.iterdir():
        if date_dir.is_dir():
            gex_file = date_dir / "gex_summary.json"
            if gex_file.exists():
                date_str = date_dir.name
                available_dates.append(date_str)

    all_trading_days = sorted(available_dates)
    logger.info(f"Found {len(all_trading_days)} total trading days in cache")

    # Filter to potential window ends (must be within validation range)
    potential_window_ends = [d for d in all_trading_days if start_date <= d <= end_date]
    logger.info(f"Can create {len(potential_window_ends)} potential windows in range {start_date} to {end_date}")

    # Sample
    if sample_every_n > 1:
        potential_window_ends = potential_window_ends[::sample_every_n]
        logger.info(f"Sampled to {len(potential_window_ends)} windows (every {sample_every_n} days)")

    # Fetch GEX for each window
    windows = []
    for i, end_date_window in enumerate(potential_window_ends):
        logger.info(f"Window {i+1}/{len(potential_window_ends)}: {end_date_window}")

        result = gex_fetcher.get_sequential_gex(symbol=symbol, end_date=end_date_window)

        if result is None:
            logger.warning(f"Could not fetch window for {end_date_window} - skipping")
            continue

        gex_sequence = result["gex_sequence"]

        if len(gex_sequence) != window_size:
            logger.warning(f"Window has {len(gex_sequence)} days, expected {window_size} - skipping")
            continue

        # CRITICAL: Apply obfuscation to GEX sequence (required for research validity)
        # LLM must not see real dates - prevents temporal context cheating
        gex_sequence_obfuscated = []
        for j, day in enumerate(gex_sequence):
            # Compute day offset: if 30 days, first day is T-29, last day is T+0
            day_offset = j - window_size + 1
            day_label = f"Day T{day_offset:+d}" if day_offset != 0 else "Day T+0"

            obfuscated_day = {
                "date": day_label,  # e.g., "Day T-29", "Day T+0"
                "net_gex_usd": day.get("net_gex", 0),
                "positive_gex": day.get("positive_gex", 0),
                "negative_gex": day.get("negative_gex", 0),
            }
            gex_sequence_obfuscated.append(obfuscated_day)

        # Apply phase transformations (Phase 2 negative controls)
        if phase == "shuffle":
            # Phase 2a: Randomize day order (destroys temporal structure)
            # Keep dates labeled correctly (T-29 to T+0) but shuffle GEX values
            gex_values = [day["net_gex_usd"] for day in gex_sequence_obfuscated]
            random.shuffle(gex_values)
            for j, day in enumerate(gex_sequence_obfuscated):
                day["net_gex_usd"] = gex_values[j]

        elif phase == "transitional":
            # Phase 2b: Create artificial high-volatility windows (7-10 sign flips)
            # Real data has max 4 flips (2020-2024), so we artificially add flips

            # Count current sign flips
            current_flips = sum(
                1
                for k in range(1, len(gex_sequence_obfuscated))
                if (gex_sequence_obfuscated[k]["net_gex_usd"] > 0)
                != (gex_sequence_obfuscated[k - 1]["net_gex_usd"] > 0)
            )

            # Only use low-flip windows (0-2 flips) as base for transformation
            if current_flips > 2:
                logger.debug(f"Window {end_date_window}: {current_flips} flips, skipping (need 0-2 base)")
                continue

            # Randomly invert signs of 7-10 days to create artificial volatility
            target_flips = random.randint(7, 10)
            days_to_flip = random.sample(range(len(gex_sequence_obfuscated)), target_flips)

            for day_idx in days_to_flip:
                day = gex_sequence_obfuscated[day_idx]
                # Invert sign (multiply by -1)
                day["net_gex_usd"] *= -1
                # Swap positive/negative (represents sign flip)
                day["positive_gex"], day["negative_gex"] = day["negative_gex"], day["positive_gex"]

        elif phase == "low-magnitude":
            # Phase 2c: Scale GEX down by 75% (makes avg ~$3B from ~$12B)
            scale_factor = 0.25
            for day in gex_sequence_obfuscated:
                day["net_gex_usd"] *= scale_factor
                day["positive_gex"] *= scale_factor
                day["negative_gex"] *= scale_factor

        windows.append(
            {
                "end_date": end_date_window,
                # Full obfuscated sequence (possibly transformed)
                "gex_sequence": gex_sequence_obfuscated,
                "start_date": gex_sequence[0]["date"] if gex_sequence else None,
                "phase": phase if phase else "normal",
            }
        )

    logger.info(f"Prepared {len(windows)} valid windows for batch")
    return windows


def submit_batch_job(
    start_date: str, end_date: str, symbol: str = "SPY", sample_every_n: int = 1, phase: str = None
) -> str:
    """Prepare and submit batch job with optional phase transformation.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        symbol: Ticker symbol (default SPY)
        sample_every_n: Sample every N days (default 1)
        phase: Transformation phase (None, 'shuffle', 'transitional', 'low-magnitude')

    Returns:
        Batch job ID

    Phase Transformations:
        - None: Normal regime validation (Phase 1, 3, 4)
        - 'shuffle': Randomize GEX day order (Phase 2a)
        - 'transitional': Artificially add 7-10 sign flips (Phase 2b)
        - 'low-magnitude': Scale GEX down 75% (Phase 2c)
    """
    phase_label = phase if phase else "normal"
    logger.info(f"📊 Submitting batch job: {start_date} to {end_date}")
    logger.info(f"📊 Phase: {phase_label}")

    # Prepare windows with phase transformation
    windows = prepare_windows(start_date, end_date, symbol, sample_every_n=sample_every_n, phase=phase)

    if not windows:
        logger.error("❌ No valid windows prepared - cannot submit batch")
        return None

    logger.info(f"✅ Prepared {len(windows)} windows for submission")

    # Create validator and prepare batch file
    validator = BatchRegimeValidator()
    batch_file = validator.prepare_batch_file(windows)

    # Submit batch with phase-specific description
    if phase:
        description = f"Phase 2 ({phase}): {start_date} to {end_date} ({len(windows)} windows)"
    else:
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
    """Poll batch job status.

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

    if status["status"] == "completed":
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
    """Retrieve batch results and save as YAML.

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
    output_file = PROJECT_ROOT / "reports" / "validation" / "paper2_regime_windows" / f"phase_batch_{batch_id}.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    validator.save_results_yaml(results, [], output_file, batch_id)

    logger.info(f"✅ Retrieved {len(results)} results")
    logger.info(f"Saved to: {output_file}")

    # Print summary
    detected = sum(1 for r in results if r.get("regime_detected", False))
    logger.info(f"")
    logger.info(f"Summary:")
    logger.info(f"  Detection rate: {detected}/{len(results)} ({100*detected/len(results):.1f}%)")
    logger.info(f"  Avg confidence: {sum(r.get('confidence', 0) for r in results)/len(results):.0f}%")

    # Store results in ResearchCache for queryable access
    logger.info(f"")
    logger.info(f"Storing results in ResearchCache...")
    research_cache = ResearchCache()

    stored_count = 0
    for result in results:
        try:
            # Extract date from window_id (format: "window-YYYY-MM-DD")
            window_id = result.get("window_id", "")
            if window_id.startswith("window-"):
                trading_date = window_id.replace("window-", "")
            else:
                logger.warning(f"Could not parse date from window_id: {window_id}")
                continue

            # Store detection in ResearchCache
            research_cache.record_detection(
                symbol=symbol,
                trading_date=trading_date,
                pattern_id="regime_30day",
                llm_model="o4-mini",
                prompt_version="v2.0_regime_detection",
                detected=result.get("regime_detected", False),
                confidence=result.get("confidence", 0),
                structured_output={
                    "regime_type": result.get("regime_type", "unknown"),
                },
                reasoning_chain=result.get("reasoning", ""),
                raw_response=str(result.get("raw_response", {})),
                experiment_run_id=f"batch_{batch_id}",
            )
            stored_count += 1

        except Exception as e:
            logger.error(f"Failed to store result for {result.get('window_id')}: {e}")
            continue

    logger.info(f"✅ Stored {stored_count}/{len(results)} detections in ResearchCache")

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
        """,
    )

    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--symbol", type=str, default="SPY", help="Ticker symbol (default: SPY)")
    parser.add_argument("--sample-every-n", type=int, default=1, help="Sample every N days (default: 1)")
    parser.add_argument(
        "--phase",
        type=str,
        choices=["shuffle", "transitional", "low-magnitude"],
        help="Phase 2 transformation: shuffle (2a), transitional (2b), low-magnitude (2c)",
    )

    parser.add_argument("--submit", action="store_true", help="Prepare and submit batch job")
    parser.add_argument("--batch-id", type=str, help="Batch ID for polling/retrieval")
    parser.add_argument("--poll", action="store_true", help="Poll batch status")
    parser.add_argument("--poll-interval", type=int, default=60, help="Poll interval in seconds (default: 60)")
    parser.add_argument("--retrieve", action="store_true", help="Retrieve batch results")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    if args.submit:
        if not args.start_date or not args.end_date:
            parser.error("--submit requires --start-date and --end-date")
        submit_batch_job(args.start_date, args.end_date, args.symbol, args.sample_every_n, args.phase)

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
