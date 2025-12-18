#!/usr/bin/env python3
"""
Phase 2: Narrative Removal Test - Batch API Version (Issue #133)

Purpose:
    Full statistical validation of WHO→WHOM→WHAT framework necessity.
    Uses OpenAI Batch API for 50% cost savings.

Sample:
    52 dates stratified by quarter (13 per Q1-Q4)
    104 total requests (52 dates × 2 conditions)

Cost:
    104 calls × $0.005 (Batch API) = $0.52

Usage:
    # Submit batch
    python scripts/validation/test_narrative_removal_phase2_batch.py --submit

    # Poll for completion
    python scripts/validation/test_narrative_removal_phase2_batch.py --poll

    # Retrieve results
    python scripts/validation/test_narrative_removal_phase2_batch.py --retrieve
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def load_phase2_sample():
    """Load Phase 2 sample (52 dates)."""
    sample_file = Path("/tmp/phase2_sample.json")

    if not sample_file.exists():
        print("ERROR: Phase 2 sample not found. Run design script first.")
        sys.exit(1)

    with open(sample_file, "r") as f:
        sample_data = json.load(f)

    # Load full detection data for these dates
    validation_file = (
        project_root / "reports/validation/paper1_pattern_taxonomy/gamma_positioning_SPY_2024_unbiased.yaml"
    )

    with open(validation_file, "r") as f:
        validation_data = yaml.safe_load(f)

    # Build lookup
    sample_dates = {d["date"] for d in sample_data["dates"]}
    detections = [d for d in validation_data["detections"] if d["date"] in sample_dates]

    return detections


def build_control_prompt(gex_metrics):
    """Build control prompt WITH WHO→WHOM→WHAT framework."""
    return f"""You are analyzing options market mechanics for an institutional trading desk.

## Market Data (Day T+0)

Symbol: INDEX_1
Net GEX: ${gex_metrics['net_gex_usd']/1e9:.2f}B
Spot Price: ${gex_metrics['spot_price']:.2f}

## Task

Based on these gamma exposure metrics, identify the structural constraint:

1. **WHO**: Which market participant is constrained by these conditions?
2. **WHOM**: Who bears the downstream impact of their actions?
3. **WHAT**: What specific action are they forced to take?

Provide confidence (0-100%) that a structural constraint exists.

Format your response as JSON:
{{
    "who": "...",
    "whom": "...",
    "what": "...",
    "confidence": 85
}}"""


def build_treatment_prompt(gex_metrics):
    """Build treatment prompt WITHOUT framework (data only)."""
    return f"""Analyze the following options market data:

## Market Data (Day T+0)

Symbol: INDEX_1
Net GEX: ${gex_metrics['net_gex_usd']/1e9:.2f}B
Spot Price: ${gex_metrics['spot_price']:.2f}

## Task

Provide your analysis of these metrics."""


def prepare_batch_file(detections):
    """Prepare JSONL file for Batch API."""
    batch_file = project_root / "reports/validation/paper2_extensions/issue133_phase2_batch.jsonl"
    batch_file.parent.mkdir(parents=True, exist_ok=True)

    with open(batch_file, "w") as f:
        for detection in detections:
            date = detection["date"]
            gex_metrics = detection["quantitative_evidence"]["gex_metrics"]

            # Control request
            control_request = {
                "custom_id": f"control_{date}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": build_control_prompt(gex_metrics)}],
                    "temperature": 0.0,
                },
            }
            f.write(json.dumps(control_request) + "\n")

            # Treatment request
            treatment_request = {
                "custom_id": f"treatment_{date}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": build_treatment_prompt(gex_metrics)}],
                    "temperature": 0.0,
                },
            }
            f.write(json.dumps(treatment_request) + "\n")

    print(f"Batch file prepared: {batch_file}")
    print(f"  Requests: {len(detections) * 2} (52 dates × 2 conditions)")
    return batch_file


def submit_batch(batch_file):
    """Submit batch to OpenAI API."""
    # Load API key
    config_path = project_root / "config/config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    api_key = config.get("OPEN_AI_KEY") or config.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPEN_AI_KEY not found in config/config.json")
        return None

    client = OpenAI(api_key=api_key)

    # Upload batch file
    print(f"\nUploading batch file...")
    with open(batch_file, "rb") as f:
        batch_input_file = client.files.create(file=f, purpose="batch")

    print(f"File uploaded: {batch_input_file.id}")

    # Create batch
    print(f"\nSubmitting batch...")
    batch = client.batches.create(
        input_file_id=batch_input_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h",
        metadata={"issue": "Issue #133 Phase 2", "description": "Narrative removal test - full validation"},
    )

    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.status}")
    print(f"Requests: {batch.request_counts.total}")

    # Save batch metadata
    metadata_file = project_root / "reports/validation/paper2_extensions/issue133_phase2_batch_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(
            {
                "batch_id": batch.id,
                "file_id": batch_input_file.id,
                "status": batch.status,
                "submitted_at": datetime.now().isoformat(),
                "total_requests": batch.request_counts.total,
            },
            f,
            indent=2,
        )

    print(f"\nMetadata saved: {metadata_file}")
    print(f"\nTo check status:")
    print(f"  python {Path(__file__).name} --poll")

    return batch.id


def poll_batch(batch_id=None):
    """Poll batch status."""
    if not batch_id:
        # Load from metadata
        metadata_file = project_root / "reports/validation/paper2_extensions/issue133_phase2_batch_metadata.json"
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        batch_id = metadata["batch_id"]

    # Load API key
    config_path = project_root / "config/config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    api_key = config.get("OPEN_AI_KEY") or config.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # Get batch status
    batch = client.batches.retrieve(batch_id)

    print(f"Batch ID: {batch.id}")
    print(f"Status: {batch.status}")
    print(f"Created: {batch.created_at}")
    print(f"Requests: {batch.request_counts.total}")
    print(f"Completed: {batch.request_counts.completed}")
    print(f"Failed: {batch.request_counts.failed}")

    if batch.status == "completed":
        print(f"\n✅ Batch complete! Output file: {batch.output_file_id}")
        print(f"\nTo retrieve results:")
        print(f"  python {Path(__file__).name} --retrieve")
    elif batch.status == "failed":
        print(f"\n❌ Batch failed")
        if batch.errors:
            print(f"Errors: {batch.errors}")
    else:
        print(f"\n⏳ Batch still processing... Poll again in a few minutes")

    return batch.status


def retrieve_results(batch_id=None):
    """Retrieve and parse batch results."""
    if not batch_id:
        # Load from metadata
        metadata_file = project_root / "reports/validation/paper2_extensions/issue133_phase2_batch_metadata.json"
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        batch_id = metadata["batch_id"]

    # Load API key
    config_path = project_root / "config/config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    api_key = config.get("OPEN_AI_KEY") or config.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # Get batch
    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        print(f"ERROR: Batch not yet completed (status: {batch.status})")
        return

    # Download output file
    output_file_id = batch.output_file_id
    file_response = client.files.content(output_file_id)

    # Save raw output
    raw_output_file = project_root / "reports/validation/paper2_extensions/issue133_phase2_batch_output.jsonl"
    with open(raw_output_file, "wb") as f:
        f.write(file_response.content)

    print(f"Raw output saved: {raw_output_file}")

    # Parse results
    results = parse_batch_results(raw_output_file)

    # Calculate statistics
    control_detected = sum(1 for r in results if r["condition"] == "control" and r["detected"])
    treatment_detected = sum(1 for r in results if r["condition"] == "treatment" and r["detected"])
    total_dates = len(results) // 2

    control_rate = control_detected / total_dates * 100
    treatment_rate = treatment_detected / total_dates * 100

    print(f"\n{'='*80}")
    print(f"PHASE 2 RESULTS")
    print(f"{'='*80}")
    print(f"Control (with framework):    {control_rate:.1f}% ({control_detected}/{total_dates})")
    print(f"Treatment (no framework):    {treatment_rate:.1f}% ({treatment_detected}/{total_dates})")
    print(f"Difference:                  {control_rate - treatment_rate:.1f}pp")

    # Statistical test
    from scipy.stats import chi2_contingency

    contingency_table = [
        [control_detected, total_dates - control_detected],
        [treatment_detected, total_dates - treatment_detected],
    ]

    chi2, p_value, dof, expected = chi2_contingency(contingency_table)

    print(f"\nStatistical Significance:")
    print(f"  Chi-square: {chi2:.2f}")
    print(f"  p-value: {p_value:.4f}")
    print(f"  Significant: {'YES' if p_value < 0.05 else 'NO'} (α=0.05)")

    # Save results (convert numpy types to native Python)
    results_file = project_root / "reports/validation/paper2_extensions/issue133_phase2_results.yaml"
    with open(results_file, "w") as f:
        yaml.dump(
            {
                "test_metadata": {
                    "issue": "Issue #133 Phase 2",
                    "test_date": datetime.now().isoformat(),
                    "batch_id": batch_id,
                    "total_dates": int(total_dates),
                    "control_detection_rate": float(control_rate),
                    "treatment_detection_rate": float(treatment_rate),
                    "difference_pp": float(control_rate - treatment_rate),
                    "chi2": float(chi2),
                    "p_value": float(p_value),
                },
                "results": results,
            },
            f,
            default_flow_style=False,
        )

    print(f"\nResults saved: {results_file}")


def parse_batch_results(output_file):
    """Parse batch API output."""
    results = []

    with open(output_file, "r") as f:
        for line in f:
            result = json.loads(line)

            custom_id = result["custom_id"]
            condition, date = custom_id.split("_", 1)

            response_text = result["response"]["body"]["choices"][0]["message"]["content"]

            if condition == "control":
                detected, confidence = parse_control_response(response_text)
            else:
                detected = parse_treatment_response(response_text)
                confidence = None

            results.append(
                {
                    "date": date,
                    "condition": condition,
                    "detected": detected,
                    "confidence": confidence,
                    "response": response_text[:500],  # First 500 chars
                }
            )

    return results


def parse_control_response(response_text):
    """Parse control response."""
    try:
        data = json.loads(response_text)
        confidence = data.get("confidence", 0)
        detected = confidence >= 60
        return detected, confidence
    except:
        # Fallback: check for keywords
        has_who = "market maker" in response_text.lower() or "dealer" in response_text.lower()
        has_constraint = "force" in response_text.lower() or "hedge" in response_text.lower()
        detected = has_who and has_constraint
        confidence = 50 if detected else 0
        return detected, confidence


def parse_treatment_response(response_text):
    """Parse treatment response."""
    text_lower = response_text.lower()

    mentions_dealers = "market maker" in text_lower or "dealer" in text_lower
    mentions_hedging = "hedge" in text_lower or "hedging" in text_lower
    mentions_constraint = "force" in text_lower or "must" in text_lower or "required" in text_lower
    mentions_gamma = "gamma" in text_lower

    detected = mentions_dealers and mentions_hedging and (mentions_constraint or mentions_gamma)
    return detected


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2: Narrative Removal Test (Batch API)")
    parser.add_argument("--submit", action="store_true", help="Submit batch")
    parser.add_argument("--poll", action="store_true", help="Poll batch status")
    parser.add_argument("--retrieve", action="store_true", help="Retrieve results")

    args = parser.parse_args()

    if args.submit:
        detections = load_phase2_sample()
        print(f"Loaded {len(detections)} dates for Phase 2")
        batch_file = prepare_batch_file(detections)
        submit_batch(batch_file)
    elif args.poll:
        poll_batch()
    elif args.retrieve:
        retrieve_results()
    else:
        print("Usage:")
        print("  --submit: Prepare and submit batch")
        print("  --poll: Check batch status")
        print("  --retrieve: Download and analyze results")


if __name__ == "__main__":
    main()
