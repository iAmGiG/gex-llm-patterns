#!/usr/bin/env python3
"""Phase 4A Batch Generation using PostgreSQL GEX Data

Generates 1,418 30-day windows (2020-2025) for OpenAI Batch API submission.
Uses verified PostgreSQL data (11M SPY contracts) instead of corrupted cache.

Usage:
    python /tmp/phase4a_postgresql_batch.py --mode generate  # Generate batch file
    python /tmp/phase4a_postgresql_batch.py --mode submit    # Submit to OpenAI
    python /tmp/phase4a_postgresql_batch.py --mode poll --batch-id <id>
    python /tmp/phase4a_postgresql_batch.py --mode retrieve --batch-id <id>
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import psycopg2

sys.path.insert(0, '/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns')

# Import production prompt builder for consistent prompts
from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder
# Import GEXCalculator for single source of truth (Issue #169 architectural fix)
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgreSQLGEXFetcher:
    """Fetch and calculate GEX from PostgreSQL database.

    Uses GEXCalculator.calculate_net_gex_from_raw() for single source of truth
    on GEX calculations (Issue #169 architectural fix).
    """

    def __init__(self):
        self.conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="cregan1",
            database="gex_options"
        )
        # Use centralized GEX calculator (Issue #169: eliminate formula duplication)
        self.gex_calculator = GEXCalculator()
        logger.info("Connected to PostgreSQL")

    def get_trading_days(self, symbol: str, start_date: str, end_date: str) -> List[str]:
        """Get all trading days with options data"""
        query = """
            SELECT DISTINCT trading_date
            FROM options_chains_partitioned
            WHERE symbol = %s
              AND trading_date >= %s
              AND trading_date <= %s
            ORDER BY trading_date
        """
        with self.conn.cursor() as cur:
            cur.execute(query, (symbol, start_date, end_date))
            rows = cur.fetchall()
        return [row[0].strftime('%Y-%m-%d') for row in rows]

    def calculate_daily_gex(self, symbol: str, trading_date: str) -> Optional[Dict]:
        """Calculate net GEX for a single trading day from raw options data.

        Uses GEXCalculator.calculate_net_gex_from_raw() for single source of truth
        on GEX formula (Issue #169 architectural fix).

        Returns:
            Dict with date, net_gex, positive_gex (call), negative_gex (put), underlying_price
        """
        query = """
            SELECT
                option_type,
                gamma,
                open_interest,
                underlying_price
            FROM options_chains_partitioned
            WHERE symbol = %s
              AND trading_date = %s
              AND gamma IS NOT NULL
              AND open_interest IS NOT NULL
              AND open_interest > 0
              AND underlying_price IS NOT NULL
              AND underlying_price > 0
        """

        with self.conn.cursor() as cur:
            cur.execute(query, (symbol, trading_date))
            rows = cur.fetchall()

        if not rows:
            return None

        # Convert to format expected by GEXCalculator.calculate_net_gex_from_raw()
        contracts = [
            {
                "option_type": row[0],
                "gamma": row[1],
                "open_interest": row[2],
                "underlying_price": row[3],
            }
            for row in rows
        ]

        # Use centralized GEX calculator (single source of truth)
        result = self.gex_calculator.calculate_net_gex_from_raw(contracts)

        if result["contract_count"] == 0:
            return None

        return {
            'date': trading_date,
            'net_gex': result['net_gex'],
            'positive_gex': result['call_gex'],
            'negative_gex': result['put_gex'],
            'underlying_price': result['underlying_price']
        }

    def get_30day_window(self, symbol: str, end_date: str, all_trading_days: List[str]) -> Optional[List[Dict]]:
        """Get 30-day GEX window ending on end_date"""
        try:
            end_idx = all_trading_days.index(end_date)
        except ValueError:
            return None

        if end_idx < 29:  # Need at least 30 days of history
            return None

        window_dates = all_trading_days[end_idx - 29:end_idx + 1]

        gex_sequence = []
        for date in window_dates:
            gex = self.calculate_daily_gex(symbol, date)
            if gex is None:
                return None  # Missing data
            gex_sequence.append(gex)

        return gex_sequence

    def close(self):
        self.conn.close()


def generate_batch_file(output_path: Path = None):
    """Generate OpenAI Batch API request file for all Phase 4A windows"""

    fetcher = PostgreSQLGEXFetcher()

    # Get all trading days 2020-2025
    logger.info("Fetching trading days from PostgreSQL...")
    all_trading_days = fetcher.get_trading_days("SPY", "2020-01-02", "2025-12-31")
    logger.info(f"Found {len(all_trading_days)} trading days")

    # Generate windows (start from day 30 to have 30-day history)
    potential_windows = all_trading_days[29:]  # First valid window ends on day 30
    logger.info(f"Can generate {len(potential_windows)} 30-day windows")

    # Prepare batch requests
    batch_requests = []
    windows_generated = 0

    for i, end_date in enumerate(potential_windows):
        if (i + 1) % 100 == 0:
            logger.info(f"Processing window {i+1}/{len(potential_windows)}: {end_date}")

        gex_sequence = fetcher.get_30day_window("SPY", end_date, all_trading_days)

        if gex_sequence is None:
            logger.warning(f"Skipping {end_date}: incomplete data")
            continue

        # Obfuscate dates (T-29 to T+0) - format for MechanicsPromptBuilder
        obfuscated_sequence = []
        for j, day in enumerate(gex_sequence):
            day_offset = j - 29
            day_label = f"Day T{day_offset:+d}" if day_offset != 0 else "Day T+0"

            obfuscated_sequence.append({
                "date": day_label,
                "net_gex_usd": day['net_gex'],  # Keep in USD for prompt builder
                "positive_gex": day.get('positive_gex', 0),
                "negative_gex": day.get('negative_gex', 0),
            })

        # Use production prompt from MechanicsPromptBuilder (consistent with all phases)
        prompt = MechanicsPromptBuilder.build_regime_prompt(
            gex_sequence=obfuscated_sequence,
            end_date=end_date
        )

        # Create batch request in OpenAI format (single user message, no system)
        batch_request = {
            "custom_id": f"window-{end_date}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "o4-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        }

        batch_requests.append(batch_request)
        windows_generated += 1

    fetcher.close()

    # Save batch file
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/reports/validation/paper2_regime_windows/batch_jobs/phase4a_postgresql_{timestamp}.jsonl")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        for req in batch_requests:
            f.write(json.dumps(req) + "\n")

    logger.info(f"=" * 70)
    logger.info(f"BATCH FILE GENERATED")
    logger.info(f"=" * 70)
    logger.info(f"Output: {output_path}")
    logger.info(f"Windows: {windows_generated}")
    logger.info(f"Estimated cost: ${windows_generated * 0.015:.2f} (50% batch discount)")
    logger.info(f"")
    logger.info(f"To submit:")
    logger.info(f"  python /tmp/phase4a_postgresql_batch.py --mode submit --batch-file {output_path}")

    return output_path, windows_generated


def submit_batch(batch_file: Path):
    """Submit batch file to OpenAI Batch API"""
    from openai import OpenAI

    client = OpenAI()

    # Upload file
    logger.info(f"Uploading batch file: {batch_file}")
    with open(batch_file, 'rb') as f:
        file_response = client.files.create(file=f, purpose="batch")

    file_id = file_response.id
    logger.info(f"Uploaded file ID: {file_id}")

    # Create batch
    batch = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={
            "description": "Phase 4A Multi-Year Validation (PostgreSQL GEX)",
            "experiment": "paper2_phase4a_postgresql",
            "git_branch": "db/upgrades"
        }
    )

    logger.info(f"=" * 70)
    logger.info(f"BATCH SUBMITTED")
    logger.info(f"=" * 70)
    logger.info(f"Batch ID: {batch.id}")
    logger.info(f"Status: {batch.status}")
    logger.info(f"")
    logger.info(f"To poll status:")
    logger.info(f"  python /tmp/phase4a_postgresql_batch.py --mode poll --batch-id {batch.id}")

    return batch.id


def poll_batch(batch_id: str):
    """Poll batch status"""
    from openai import OpenAI
    import time

    client = OpenAI()

    logger.info(f"Polling batch: {batch_id}")

    while True:
        batch = client.batches.retrieve(batch_id)

        logger.info(f"Status: {batch.status} | "
                   f"Completed: {batch.request_counts.completed}/{batch.request_counts.total} | "
                   f"Failed: {batch.request_counts.failed}")

        if batch.status == "completed":
            logger.info(f"✅ Batch completed!")
            logger.info(f"Output file ID: {batch.output_file_id}")
            logger.info(f"")
            logger.info(f"To retrieve results:")
            logger.info(f"  python /tmp/phase4a_postgresql_batch.py --mode retrieve --batch-id {batch_id}")
            return batch
        elif batch.status in ["failed", "expired", "cancelled"]:
            logger.error(f"❌ Batch {batch.status}")
            if batch.errors:
                for error in batch.errors.data:
                    logger.error(f"  Error: {error.message}")
            return batch

        time.sleep(60)  # Poll every minute


def retrieve_results(batch_id: str):
    """Retrieve and store batch results"""
    from openai import OpenAI

    sys.path.insert(0, '/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns')
    from gex_db_infrastructure.cache.research_cache import ResearchCache

    client = OpenAI()

    # Get batch info
    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        logger.error(f"Batch not completed. Status: {batch.status}")
        return None

    # Download results
    logger.info(f"Downloading results from {batch.output_file_id}...")
    content = client.files.content(batch.output_file_id)

    # Save raw results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path(f"/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/reports/validation/paper2_regime_windows/batch_jobs/results_phase4a_postgresql_{timestamp}.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'wb') as f:
        f.write(content.content)

    logger.info(f"Saved raw results to: {output_file}")

    # Parse and store in ResearchCache
    cache = ResearchCache()

    results = []
    stored = 0

    with open(output_file, 'r') as f:
        for line in f:
            try:
                result = json.loads(line)
                custom_id = result.get('custom_id', '')

                if not custom_id.startswith('window-'):
                    continue

                trading_date = custom_id.replace('window-', '')

                # Parse response
                response = result.get('response', {})
                body = response.get('body', {})
                choices = body.get('choices', [])

                if not choices:
                    continue

                content = choices[0].get('message', {}).get('content', '')

                # Parse JSON from content
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    detection = json.loads(json_match.group(0))
                else:
                    continue

                detected = detection.get('regime_detected', False)
                confidence = detection.get('confidence', 50)
                reasoning = detection.get('reasoning', '')
                regime_type = detection.get('regime_type', 'unknown')

                # Get token usage
                usage = body.get('usage', {})
                token_count = usage.get('total_tokens', 0)
                model = body.get('model', 'o4-mini')

                # Store in ResearchCache with structured_output for analysis
                cache.record_detection(
                    symbol="SPY",
                    trading_date=trading_date,
                    pattern_id="regime_30day",
                    llm_model=model,
                    prompt_version="v2.0_postgresql",
                    detected=detected,
                    confidence=confidence,
                    structured_output={
                        "regime_type": detection.get("regime_type", "unknown"),
                        "positive_days": detection.get("positive_days", 0),
                        "negative_days": detection.get("negative_days", 0),
                        "avg_magnitude_billions": detection.get("avg_magnitude_billions", 0.0),
                        "sign_flips": detection.get("sign_flips", 0),
                        "persistence_pct": detection.get("persistence_pct", 0.0),
                    },
                    reasoning_chain=reasoning,
                    raw_response=content[:5000],
                    token_count=token_count,
                )

                results.append({
                    'date': trading_date,
                    'detected': detected,
                    'confidence': confidence,
                    'regime_type': regime_type
                })
                stored += 1

            except Exception as e:
                logger.warning(f"Error parsing result: {e}")
                continue

    logger.info(f"=" * 70)
    logger.info(f"RESULTS RETRIEVED AND STORED")
    logger.info(f"=" * 70)
    logger.info(f"Total results: {len(results)}")
    logger.info(f"Stored in ResearchCache: {stored}")

    # Summary by year
    df = pd.DataFrame(results)
    if not df.empty:
        df['year'] = df['date'].str[:4]
        summary = df.groupby('year').agg({
            'detected': ['sum', 'count']
        })
        summary.columns = ['detected', 'total']
        summary['rate'] = (summary['detected'] / summary['total'] * 100).round(1)

        logger.info(f"\nDetection by Year:")
        for year, row in summary.iterrows():
            logger.info(f"  {year}: {int(row['detected'])}/{int(row['total'])} ({row['rate']}%)")

    return results


def main():
    parser = argparse.ArgumentParser(description='Phase 4A PostgreSQL Batch Generator')
    parser.add_argument('--mode', choices=['generate', 'submit', 'poll', 'retrieve'],
                       required=True, help='Operation mode')
    parser.add_argument('--batch-file', type=str, help='Batch file path (for submit)')
    parser.add_argument('--batch-id', type=str, help='Batch ID (for poll/retrieve)')

    args = parser.parse_args()

    if args.mode == 'generate':
        generate_batch_file()
    elif args.mode == 'submit':
        if not args.batch_file:
            parser.error("--submit requires --batch-file")
        submit_batch(Path(args.batch_file))
    elif args.mode == 'poll':
        if not args.batch_id:
            parser.error("--poll requires --batch-id")
        poll_batch(args.batch_id)
    elif args.mode == 'retrieve':
        if not args.batch_id:
            parser.error("--retrieve requires --batch-id")
        retrieve_results(args.batch_id)


if __name__ == '__main__':
    main()
