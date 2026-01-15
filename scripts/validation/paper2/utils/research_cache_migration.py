#!/usr/bin/env python3
"""
Agent B Migration - Fixed Version
Imports Phase 4A detections from batch results JSONL files.

Key fixes:
1. Correct path: batch_jobs/ subdirectory
2. Correct custom_id format: "window-YYYY-MM-DD"
3. Uses record_detection() method (not store_detection)
4. Parses nested JSON content field
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns')

from gex_db_infrastructure.cache.research_cache import ResearchCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_git_info():
    """Get current git commit and branch."""
    try:
        commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd='/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns',
            stderr=subprocess.DEVNULL
        ).decode().strip()[:8]
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd='/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns',
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return commit, branch
    except Exception:
        return "unknown", "unknown"


def extract_year_from_batch_file(filename: str) -> str:
    """Infer year from batch filename or results context."""
    # Try to extract from filename patterns like batch_regime_20251122_...
    match = re.search(r'batch_regime_(\d{4})(\d{2})(\d{2})', filename)
    if match:
        return match.group(1)  # Year of batch creation
    return "unknown"


def parse_detection_content(content: str) -> dict:
    """Parse the JSON content from LLM response.

    Handles both clean JSON and JSON wrapped in markdown code blocks.
    """
    try:
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try direct JSON parsing
        # Handle JSON that might have trailing content
        brace_match = re.search(r'\{.*\}', content, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(0))

        return {}
    except json.JSONDecodeError:
        return {}


def import_detections(cache: ResearchCache, dry_run: bool = False):
    """Import detections from batch results JSONL files."""
    logger.info("=" * 70)
    logger.info("PHASE 4A DETECTION IMPORT (Fixed)")
    logger.info("=" * 70)

    # FIXED: Look in batch_jobs subdirectory
    base_path = Path('/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/reports/validation/paper2_regime_windows/batch_jobs')

    # Only process results files (not input batch files)
    results_files = sorted(base_path.glob('results_batch_*.jsonl'))
    logger.info(f"Found {len(results_files)} results files")

    git_commit, git_branch = get_git_info()
    logger.info(f"Git commit: {git_commit}, branch: {git_branch}")

    total_imported = 0
    total_skipped = 0
    errors = []

    for results_file in results_files:
        logger.info(f"\nProcessing: {results_file.name}")
        file_imported = 0

        try:
            with open(results_file) as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        result = json.loads(line)

                        # Extract custom_id (format: "window-YYYY-MM-DD")
                        custom_id = result.get('custom_id', '')
                        if not custom_id.startswith('window-'):
                            total_skipped += 1
                            continue

                        # Parse date from custom_id
                        trading_date = custom_id.replace('window-', '')

                        # Get response content
                        response = result.get('response', {})
                        body = response.get('body', {})
                        choices = body.get('choices', [])
                        if not choices:
                            total_skipped += 1
                            continue

                        message = choices[0].get('message', {})
                        content = message.get('content', '')

                        # Parse the JSON response
                        detection_data = parse_detection_content(content)

                        # Extract fields
                        detected = detection_data.get('regime_detected', False)
                        confidence = detection_data.get('confidence', 50)
                        reasoning = detection_data.get('reasoning', '')
                        regime_type = detection_data.get('regime_type', 'unknown')

                        # Get model from response
                        model = body.get('model', 'o4-mini-2025-04-16')

                        # Get token usage
                        usage = body.get('usage', {})
                        token_count = usage.get('total_tokens', 0)

                        if dry_run:
                            logger.info(f"  [DRY RUN] {trading_date}: detected={detected}, conf={confidence}, type={regime_type}")
                        else:
                            # Store in ResearchCache using record_detection
                            cache.record_detection(
                                symbol="SPY",
                                trading_date=trading_date,
                                pattern_id="regime_30day",
                                llm_model=model,
                                prompt_version="v1.0",
                                detected=detected,
                                confidence=confidence,
                                reasoning_chain=reasoning,
                                raw_response=content[:5000],  # Truncate if too long
                                token_count=token_count,
                            )

                        file_imported += 1
                        total_imported += 1

                        if total_imported % 200 == 0:
                            logger.info(f"  Progress: {total_imported} detections imported...")

                    except json.JSONDecodeError as e:
                        errors.append(f"{results_file.name}:{line_num} - JSON decode error")
                        continue
                    except Exception as e:
                        errors.append(f"{results_file.name}:{line_num} - {str(e)}")
                        continue

        except Exception as e:
            errors.append(f"File error {results_file.name}: {str(e)}")
            continue

        logger.info(f"  Imported: {file_imported} detections")

    logger.info("\n" + "=" * 70)
    logger.info("IMPORT SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total imported: {total_imported}")
    logger.info(f"Total skipped: {total_skipped}")
    if errors:
        logger.warning(f"Errors encountered: {len(errors)}")
        for err in errors[:5]:
            logger.warning(f"  - {err}")
        if len(errors) > 5:
            logger.warning(f"  ... and {len(errors) - 5} more errors")

    return total_imported


def import_experiments(cache: ResearchCache, dry_run: bool = False):
    """Document Paper 2 experiment runs."""
    logger.info("=" * 70)
    logger.info("EXPERIMENT RUNS DOCUMENTATION")
    logger.info("=" * 70)

    experiments = [
        {
            "run_id": "paper2_phase1_2024q1",
            "run_name": "Paper 2 Phase 1: 2024 Q1 Baseline",
            "symbols": ["SPY"],
            "date_range": ("2024-01-02", "2024-03-29"),
            "pattern_ids": ["regime_30day"],
            "llm_model": "o4-mini",
            "prompt_version": "v1.0",
            "paper_version": "paper2",
            "config": {
                "window_size": 30,
                "obfuscation": True,
                "description": "Initial baseline validation"
            }
        },
        {
            "run_id": "paper2_phase3_2024_full",
            "run_name": "Paper 2 Phase 3: 2024 Full Year",
            "symbols": ["SPY"],
            "date_range": ("2024-01-01", "2024-12-31"),
            "pattern_ids": ["regime_30day"],
            "llm_model": "o4-mini",
            "prompt_version": "v1.0",
            "paper_version": "paper2",
            "config": {
                "windows": 223,
                "description": "Full year 2024 validation"
            }
        },
        {
            "run_id": "paper2_phase4_2020_control",
            "run_name": "Paper 2 Phase 4: 2020 Negative Control",
            "symbols": ["SPY"],
            "date_range": ("2020-01-01", "2020-12-31"),
            "pattern_ids": ["regime_30day"],
            "llm_model": "o4-mini",
            "prompt_version": "v1.0",
            "paper_version": "paper2",
            "config": {
                "windows": 223,
                "description": "Pre-0DTE negative control (expected: low detection)"
            }
        },
        {
            "run_id": "paper2_phase4a_multiyear",
            "run_name": "Paper 2 Phase 4A: Multi-Year Validation",
            "symbols": ["SPY"],
            "date_range": ("2020-01-01", "2025-12-31"),
            "pattern_ids": ["regime_30day"],
            "llm_model": "o4-mini",
            "prompt_version": "v1.0",
            "paper_version": "paper2",
            "config": {
                "windows": 1418,
                "cost_usd": 11.26,
                "description": "6-year multi-year expansion validation"
            }
        }
    ]

    count = 0
    for exp in experiments:
        if dry_run:
            logger.info(f"[DRY RUN] Would document: {exp['run_id']}")
        else:
            try:
                cache.record_experiment_run(
                    run_id=exp['run_id'],
                    run_name=exp['run_name'],
                    config=exp['config'],
                    symbols=exp['symbols'],
                    date_range=exp['date_range'],
                    pattern_ids=exp['pattern_ids'],
                    llm_model=exp['llm_model'],
                    prompt_version=exp['prompt_version'],
                    paper_version=exp['paper_version'],
                )
                logger.info(f"✓ Documented: {exp['run_id']}")
                count += 1
            except Exception as e:
                logger.error(f"Error documenting {exp['run_id']}: {e}")

    logger.info(f"\n✓ Documented {count} experiment runs")
    return count


def verify_results(cache: ResearchCache):
    """Verify the migration results."""
    logger.info("=" * 70)
    logger.info("VERIFICATION")
    logger.info("=" * 70)

    stats = cache.get_cache_stats()
    logger.info(f"Detection records: {stats.get('llm_detections_count', 0)}")
    logger.info(f"Experiment runs: {stats.get('experiment_runs_count', 0)}")

    # Get detection breakdown by year
    df = cache.get_detections(symbol="SPY", pattern_ids=["regime_30day"])
    if not df.empty:
        df['year'] = df['trading_date'].str[:4]
        yearly = df.groupby('year').agg({
            'id': 'count',
            'detected': 'sum'
        }).rename(columns={'id': 'total', 'detected': 'detected_count'})
        yearly['detection_rate'] = (yearly['detected_count'] / yearly['total'] * 100).round(1)

        logger.info("\nDetection by Year:")
        for year, row in yearly.iterrows():
            logger.info(f"  {year}: {row['detected_count']}/{row['total']} ({row['detection_rate']}%)")

    return stats


def main():
    parser = argparse.ArgumentParser(description='Agent B Migration (Fixed)')
    parser.add_argument('--phase', choices=['all', 'detections', 'experiments', 'verify'],
                       default='all', help='Which phase to run')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("AGENT B - DATA MIGRATION (FIXED VERSION)")
    logger.info("=" * 70)

    cache = ResearchCache()
    logger.info(f"✓ Connected to ResearchCache: {cache.db_path}")

    results = {}

    if args.phase in ['all', 'detections']:
        results['detections'] = import_detections(cache, dry_run=args.dry_run)

    if args.phase in ['all', 'experiments']:
        results['experiments'] = import_experiments(cache, dry_run=args.dry_run)

    if args.phase in ['all', 'verify']:
        results['verify'] = verify_results(cache)

    logger.info("\n" + "=" * 70)
    logger.info("MIGRATION COMPLETE")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()
