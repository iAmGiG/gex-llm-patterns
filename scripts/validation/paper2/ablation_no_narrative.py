#!/usr/bin/env python3
"""Ablation Study: Narrative vs Data-Only Detection (Issue #191)

Tests whether the WHO→WHOM→WHAT narrative framework is necessary for regime detection
by comparing detection accuracy with and without narrative requirements.

Design:
- Control: Full narrative prompt (regime_prompt.j2)
- Treatment: Data-only prompt (no WHO→WHOM→WHAT structure)
- Sample: Balanced 100 windows (50 detected, 50 rejected from Phase 3 2024)
- Model: o4-mini (loaded from config.json, NEVER hardcoded)

Critical Lessons from Issue #133:
1. NEVER hardcode model names - always load from config
2. Use balanced samples - include both positive and negative cases
3. Verify model before running - add pre-flight check

Usage:
    python ablation_no_narrative.py --sample-size 100 --output results.yaml
"""

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import Dict, List

import yaml
from openai import OpenAI

# Add project root to path (use main repo for data access)
PROJECT_ROOT = Path("/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns")
sys.path.insert(0, str(PROJECT_ROOT))  # noqa: E402

# pylint: disable=wrong-import-position

from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.data_sources.sequential_gex_fetcher import SequentialGEXFetcher
from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_model_from_config() -> str:
    """Load OpenAI model name from config.json.

        Returns:
            model_name string

        CRITICAL: Never hardcode model names - Issue #133 root cause
    Note: API key should be set via OPENAI_API_KEY environment variable.    The OpenAI client reads this automatically - no need to pass explicitly.
    """
    # Verify API key is set in environment (standard secure practice)    if not os.environ.get("OPENAI_API_KEY"):        raise ValueError(            "OPENAI_API_KEY environment variable not set. "            "Set it with: export OPENAI_API_KEY='your-key'"        )    # Use absolute path to main repo config (worktrees don't share untracked files)
    config_path = Path("/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/config/config.json")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    model_name = config.get("LLM_MODEL", "o4-mini")

    logger.info(f"Loaded LLM model from config: {model_name}")
    return model_name


def load_phase3_results() -> Dict:
    """Load Phase 3 2024 full year validation results."""
    phase3_file = (
        PROJECT_ROOT / "reports" / "validation" / "paper2_regime_windows" / "phase3_baseline_2024_full_year.yaml"
    )

    if not phase3_file.exists():
        raise FileNotFoundError(f"Phase 3 results not found: {phase3_file}")

    with open(phase3_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    logger.info(f"✅ Loaded Phase 3 results: {len(data['windows'])} windows")
    logger.info(f"   Detection rate: {data['summary_statistics']['detection_rate_pct']:.1f}%")

    return data


def create_balanced_sample(phase3_data: Dict, sample_size: int = 100) -> List[Dict]:
    """Create balanced sample of detected and rejected windows.

    Args:
        phase3_data: Phase 3 validation results
        sample_size: Total sample size (default 100)

    Returns:
        List of sampled windows (50/50 split)

    Critical: Use balanced sample to avoid sampling bias (Issue #133 lesson)
    """
    windows = phase3_data["windows"]

    # Separate detected and rejected
    detected = [w for w in windows if w["regime_detected"]]
    rejected = [w for w in windows if not w["regime_detected"]]

    logger.info(f"Phase 3 totals: {len(detected)} detected, {len(rejected)} rejected")

    # Balance sample
    n_per_class = sample_size // 2

    if len(detected) < n_per_class:
        raise ValueError(f"Not enough detected windows: need {n_per_class}, have {len(detected)}")
    if len(rejected) < n_per_class:
        raise ValueError(f"Not enough rejected windows: need {n_per_class}, have {len(rejected)}")

    # Random sample from each class
    random.seed(42)  # Reproducibility
    sampled_detected = random.sample(detected, n_per_class)
    sampled_rejected = random.sample(rejected, n_per_class)

    balanced_sample = sampled_detected + sampled_rejected
    random.shuffle(balanced_sample)  # Shuffle to avoid ordering bias

    logger.info(
        f"✅ Created balanced sample: {n_per_class} detected + {n_per_class} rejected = {len(balanced_sample)} total"
    )

    return balanced_sample


def create_data_only_prompt(gex_sequence: List[Dict], _end_date: str) -> str:
    """Create data-only prompt WITHOUT WHO→WHOM→WHAT narrative framework.

    Args:
        gex_sequence: 30-day GEX sequence
        end_date: Window end date

    Returns:
        Data-only prompt string
    """
    # Format GEX data as table
    table_rows = []
    for day in gex_sequence:
        date = day.get("date", "")
        net_gex = day.get("net_gex_usd", 0) / 1e9  # Convert to billions
        table_rows.append(f"{date}: {net_gex:+.2f}B")

    gex_table = "\n".join(table_rows)

    # Data-only prompt (removes WHO→WHOM→WHAT structure)
    prompt = f"""Analyze the following 30-day gamma exposure (GEX) data:

{gex_table}

Determine if this window represents a persistent regime based on these criteria:

1. **Sign Persistence**: ≥70% of days share the dominant GEX sign
2. **Economic Magnitude**: Average absolute GEX ≥$5B
3. **Stability**: ≤5 sign flips across the 30-day window

Output JSON format:
{{
  "regime_detected": true/false,
  "regime_type": "persistent_positive" | "persistent_negative" | "transitional",
  "positive_days": <count>,
  "negative_days": <count>,
  "avg_magnitude_billions": <value>,
  "sign_flips": <count>,
  "persistence_pct": <value>,
  "confidence": 0-100,
  "reasoning": "<brief explanation>"
}}

Analyze the data and provide your assessment."""

    return prompt


def run_ablation_validation(sample: List[Dict], model: str, use_narrative: bool = True) -> List[Dict]:
    """Run validation on sample with or without narrative framework.

    Args:
        sample: List of windows to validate
        model: OpenAI model name
        use_narrative: If True, use narrative prompt; if False, use data-only

    Returns:
        List of validation results
    """
    # OpenAI client automatically reads OPENAI_API_KEY from environment    client = OpenAI()
    cache_manager = UnifiedCacheManager()
    gex_fetcher = SequentialGEXFetcher(cache_manager=cache_manager, window_size=30)
    prompt_builder = MechanicsPromptBuilder()

    results = []

    for i, window in enumerate(sample):
        window_id = window["window_id"]
        end_date = window_id.replace("window-", "")
        ground_truth = window["regime_detected"]

        logger.info(f"Processing {i+1}/{len(sample)}: {window_id} (ground truth: {ground_truth})")

        # Fetch GEX sequence
        gex_result = gex_fetcher.get_sequential_gex(symbol="SPY", end_date=end_date)

        if gex_result is None:
            logger.warning(f"Could not fetch GEX for {window_id} - skipping")
            continue

        gex_sequence = gex_result["gex_sequence"]

        # Obfuscate dates
        gex_sequence_obfuscated = []
        for j, day in enumerate(gex_sequence):
            day_offset = j - 30 + 1
            day_label = f"Day T{day_offset:+d}" if day_offset != 0 else "Day T+0"

            gex_sequence_obfuscated.append(
                {
                    "date": day_label,
                    "net_gex_usd": day.get("net_gex", 0),
                    "positive_gex": day.get("positive_gex", 0),
                    "negative_gex": day.get("negative_gex", 0),
                }
            )

        # Build prompt (narrative or data-only)
        if use_narrative:
            prompt_text = prompt_builder.build_regime_prompt(gex_sequence=gex_sequence_obfuscated, end_date=end_date)
            prompt_type = "narrative"
        else:
            prompt_text = create_data_only_prompt(gex_sequence=gex_sequence_obfuscated, end_date=end_date)
            prompt_type = "data_only"

        # Call LLM
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_text}],
            )

            llm_output = response.choices[0].message.content

            # Parse JSON response
            if llm_output.startswith("```json"):
                llm_output = llm_output.replace("```json\n", "").replace("\n```", "").strip()
            elif llm_output.startswith("```"):
                llm_output = llm_output.replace("```\n", "").replace("\n```", "").strip()

            # Handle JSON parsing with strict=False to allow escaped characters
            llm_result = json.loads(llm_output, strict=False)

            predicted = llm_result.get("regime_detected", False)
            confidence = llm_result.get("confidence", 0)

            results.append(
                {
                    "window_id": window_id,
                    "ground_truth": ground_truth,
                    "predicted": predicted,
                    "correct": predicted == ground_truth,
                    "confidence": confidence,
                    "prompt_type": prompt_type,
                    "llm_response": llm_result,
                }
            )

            logger.info(f"  Predicted: {predicted}, Ground truth: {ground_truth}, Correct: {predicted == ground_truth}")

        except Exception as e:
            logger.error(f"Error processing {window_id}: {e}")
            continue

    return results


def calculate_metrics(results: List[Dict]) -> Dict:
    """Calculate accuracy, precision, recall, F1 score.

    Args:
        results: List of validation results

    Returns:
        Dictionary of metrics
    """
    total = len(results)
    correct = sum(1 for r in results if r["correct"])

    # Binary classification metrics
    tp = sum(1 for r in results if r["ground_truth"] and r["predicted"])  # True positives
    fp = sum(1 for r in results if not r["ground_truth"] and r["predicted"])  # False positives
    tn = sum(1 for r in results if not r["ground_truth"] and not r["predicted"])  # True negatives
    fn = sum(1 for r in results if r["ground_truth"] and not r["predicted"])  # False negatives

    accuracy = correct / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
    }


def main():
    parser = argparse.ArgumentParser(description="Ablation study: Narrative vs Data-Only Detection")
    parser.add_argument("--sample-size", type=int, default=100, help="Total sample size (default 100)")
    parser.add_argument("--output", type=str, default="ablation_results.yaml", help="Output file")
    parser.add_argument("--skip-control", action="store_true", help="Skip control (narrative) condition")
    parser.add_argument("--skip-treatment", action="store_true", help="Skip treatment (data-only) condition")

    args = parser.parse_args()

    # Load model from config (CRITICAL: never hardcode)
    model_name = load_model_from_config()

    # Pre-flight check
    logger.info("=" * 60)
    logger.info("PRE-FLIGHT CHECK")
    logger.info("=" * 60)
    logger.info(f"LLM Model: {model_name}")
    logger.info("API Key: [set via OPENAI_API_KEY env var]")
    logger.info(f"Sample size: {args.sample_size}")
    logger.info(f"Output file: {args.output}")
    logger.info("=" * 60)

    # Load Phase 3 data
    phase3_data = load_phase3_results()

    # Create balanced sample
    sample = create_balanced_sample(phase3_data, sample_size=args.sample_size)

    # Run validation experiments
    results = {}

    if not args.skip_control:
        logger.info("\n" + "=" * 60)
        logger.info("CONTROL: Narrative Prompt (WHO→WHOM→WHAT)")
        logger.info("=" * 60)
        control_results = run_ablation_validation(sample, model_name, use_narrative=True)
        control_metrics = calculate_metrics(control_results)
        results["control"] = {
            "prompt_type": "narrative",
            "metrics": control_metrics,
            "results": control_results,
        }
        logger.info(
            f"\nControl Metrics: Accuracy={control_metrics['accuracy']:.2%}, F1={control_metrics['f1_score']:.2%}"
        )

    if not args.skip_treatment:
        logger.info("\n" + "=" * 60)
        logger.info("TREATMENT: Data-Only Prompt (No Narrative)")
        logger.info("=" * 60)
        treatment_results = run_ablation_validation(sample, model_name, use_narrative=False)
        treatment_metrics = calculate_metrics(treatment_results)
        results["treatment"] = {
            "prompt_type": "data_only",
            "metrics": treatment_metrics,
            "results": treatment_results,
        }
        logger.info(
            f"\nTreatment Metrics: Accuracy={treatment_metrics['accuracy']:.2%}, F1={treatment_metrics['f1_score']:.2%}"
        )

    # Save results
    output_path = PROJECT_ROOT / "reports" / "validation" / "paper2_regime_windows" / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "experiment": "ablation_narrative_vs_data_only",
        "issue": "#191",
        "model": model_name,
        "sample_size": args.sample_size,
        "balanced": True,
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, default_flow_style=False, sort_keys=False)

    logger.info(f"\n✅ Results saved to: {output_path}")

    # Print summary
    if "control" in results and "treatment" in results:
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY COMPARISON")
        logger.info("=" * 60)
        ctrl_acc = results["control"]["metrics"]["accuracy"]
        treat_acc = results["treatment"]["metrics"]["accuracy"]
        diff = ctrl_acc - treat_acc

        logger.info(f"Control (Narrative):   {ctrl_acc:.2%}")
        logger.info(f"Treatment (Data-Only): {treat_acc:.2%}")
        logger.info(f"Difference:            {diff:+.2%}")

        if diff > 0.20:
            logger.info("→ CONCLUSION: Framework is CRITICAL for reasoning")
        elif diff > 0.10:
            logger.info("→ CONCLUSION: Framework HELPS performance")
        else:
            logger.info("→ CONCLUSION: Framework is UNNECESSARY (data alone sufficient)")


if __name__ == "__main__":
    main()
