#!/usr/bin/env python3
"""
Phase 1 Pilot: Narrative Removal Test (Issue #133)

Purpose:
    Test if WHO→WHOM→WHAT framework is necessary for LLM detection.

Test Design:
    - Control: Full framework prompt
    - Treatment: Data-only prompt (no causal structure)
    - Compare detection rates

Expected Outcomes:
    - Treatment < 30% → Framework is critical (best case)
    - Treatment 30-60% → Framework helps but not essential (mixed)
    - Treatment ≥ 60% → Framework unnecessary (concern)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def load_test_dates():
    """Load 3 strong detection dates from Paper #1 validation."""
    validation_file = (
        project_root / "reports/validation/paper1_pattern_taxonomy/gamma_positioning_SPY_2024_unbiased.yaml"
    )

    with open(validation_file, "r") as f:
        data = yaml.safe_load(f)

    # Find strong detections (confidence ≥ 80%) from Q1, Q3, Q4
    strong_detections = [d for d in data["detections"] if d["detected"] and d["narrative"]["confidence"] >= 80]

    q1 = [d for d in strong_detections if d["date"].startswith("2024-01")][0]
    q3 = [d for d in strong_detections if d["date"].startswith("2024-07")][0]
    q4 = [d for d in strong_detections if d["date"].startswith("2024-10")][0]

    return [q1, q3, q4]


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


def parse_control_response(response_text):
    """Parse control response (expects JSON with WHO/WHOM/WHAT/confidence)."""
    try:
        # Try JSON parsing first
        data = json.loads(response_text)
        return {
            "detected": data.get("confidence", 0) >= 60,
            "confidence": data.get("confidence", 0),
            "reasoning": f"{data.get('who', '')} → {data.get('whom', '')} → {data.get('what', '')}",
            "parse_success": True,
        }
    except json.JSONDecodeError:
        # Fallback: Check if key terms present
        has_who = "market maker" in response_text.lower() or "dealer" in response_text.lower()
        has_constraint = "force" in response_text.lower() or "hedge" in response_text.lower()

        return {
            "detected": has_who and has_constraint,
            "confidence": 50 if (has_who and has_constraint) else 0,
            "reasoning": response_text[:200],
            "parse_success": False,
        }


def parse_treatment_response(response_text):
    """Parse treatment response (no expected format, check for constraint recognition)."""
    # Check if response mentions key concepts
    text_lower = response_text.lower()

    mentions_dealers = "market maker" in text_lower or "dealer" in text_lower
    mentions_hedging = "hedge" in text_lower or "hedging" in text_lower
    mentions_constraint = "force" in text_lower or "must" in text_lower or "required" in text_lower
    mentions_gamma = "gamma" in text_lower

    # Detect if response shows constraint reasoning
    detected = mentions_dealers and mentions_hedging and (mentions_constraint or mentions_gamma)

    return {
        "detected": detected,
        "mentions_dealers": mentions_dealers,
        "mentions_hedging": mentions_hedging,
        "mentions_constraint": mentions_constraint,
        "mentions_gamma": mentions_gamma,
        "reasoning": response_text[:200],
    }


def run_pilot_test(dry_run=True):
    """Run Phase 1 pilot test.

    Args:
        dry_run: If True, print prompts without calling LLM (default)
                 If False, actually call LLM API (costs money)
    """
    print("=" * 80)
    print("PHASE 1 PILOT: Narrative Removal Test (Issue #133)")
    print("=" * 80)

    # Load test dates
    test_dates = load_test_dates()

    print(f"\nTest Dates:")
    for d in test_dates:
        print(f"  - {d['date']}: Net GEX ${d['quantitative_evidence']['gex_metrics']['net_gex_usd']/1e9:.2f}B")

    if dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN MODE - Showing prompts only (no LLM calls)")
        print("=" * 80)

        for date_data in test_dates:
            gex_metrics = date_data["quantitative_evidence"]["gex_metrics"]

            print(f"\n{'='*80}")
            print(f"Date: {date_data['date']}")
            print(f"{'='*80}")

            print("\n--- CONTROL PROMPT (with framework) ---")
            print(build_control_prompt(gex_metrics))

            print("\n--- TREATMENT PROMPT (no framework) ---")
            print(build_treatment_prompt(gex_metrics))

            print(f"\nPaper #1 Result (Control): {date_data['narrative']['confidence']}% confidence")
            print(f"Expected: WHO={date_data['narrative']['who']}, WHAT={date_data['narrative']['what']}")

        print("\n" + "=" * 80)
        print("To run actual LLM test:")
        print("  python scripts/validation/test_narrative_removal_pilot.py --run")
        print("\nEstimated cost: 6 LLM calls × $0.01 = $0.06")
        print("=" * 80)
        return

    # ACTUAL TEST (if --run flag provided)
    print("\n" + "=" * 80)
    print("RUNNING ACTUAL LLM TEST")
    print("=" * 80)

    # Import OpenAI client only when actually running
    import json

    from openai import OpenAI

    # Load API key from config
    config_path = project_root / "config/config.json"
    with open(config_path, "r") as f:
        config = json.load(f)

    # Try both key names (OPEN_AI_KEY is the actual name in config)
    api_key = config.get("OPEN_AI_KEY") or config.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPEN_AI_KEY not found in config/config.json")
        return

    client = OpenAI(api_key=api_key)
    results = []

    for date_data in test_dates:
        date = date_data["date"]
        gex_metrics = date_data["quantitative_evidence"]["gex_metrics"]

        print(f"\nTesting {date}...")

        # Control test (with framework)
        control_prompt = build_control_prompt(gex_metrics)
        control_response = client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": control_prompt}], temperature=0.0
        )
        control_result = parse_control_response(control_response.choices[0].message.content)

        # Treatment test (no framework)
        treatment_prompt = build_treatment_prompt(gex_metrics)
        treatment_response = client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": treatment_prompt}], temperature=0.0
        )
        treatment_result = parse_treatment_response(treatment_response.choices[0].message.content)

        results.append(
            {
                "date": date,
                "paper1_confidence": date_data["narrative"]["confidence"],
                "control": control_result,
                "treatment": treatment_result,
            }
        )

        print(
            f"  Control: {'✅ Detected' if control_result['detected'] else '❌ Not Detected'} ({control_result['confidence']}%)"
        )
        print(f"  Treatment: {'✅ Detected' if treatment_result['detected'] else '❌ Not Detected'}")

    # Calculate summary statistics
    control_detection_rate = sum(r["control"]["detected"] for r in results) / len(results) * 100
    treatment_detection_rate = sum(r["treatment"]["detected"] for r in results) / len(results) * 100

    print("\n" + "=" * 80)
    print("PHASE 1 RESULTS")
    print("=" * 80)
    print(
        f"Control (with framework):    {control_detection_rate:.0f}% detection ({sum(r['control']['detected'] for r in results)}/3)"
    )
    print(
        f"Treatment (no framework):    {treatment_detection_rate:.0f}% detection ({sum(r['treatment']['detected'] for r in results)}/3)"
    )
    print(f"Difference:                  {control_detection_rate - treatment_detection_rate:.0f}pp")

    # Interpretation
    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)

    if treatment_detection_rate < 30:
        print("✅ FRAMEWORK IS CRITICAL")
        print("   Treatment detection < 30% suggests WHO→WHOM→WHAT framework is necessary")
        print("   Recommendation: Document finding, close Issue #133")
    elif treatment_detection_rate < 60:
        print("⚠️  FRAMEWORK HELPS BUT NOT ESSENTIAL")
        print("   Treatment detection 30-60% suggests framework improves but LLM has baseline understanding")
        print("   Recommendation: Run Phase 2 full validation (30 dates)")
    else:
        print("❌ FRAMEWORK MAY BE UNNECESSARY")
        print("   Treatment detection ≥ 60% suggests LLM doesn't need framework (concern)")
        print("   Recommendation: Run Phase 2 full validation + analyze reasoning quality")

    # Save results
    output_file = project_root / "reports/validation/paper2_extensions/issue133_phase1_results.yaml"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        yaml.dump(
            {
                "test_metadata": {
                    "issue": "Issue #133 - Narrative Removal Test",
                    "phase": "Phase 1 Pilot",
                    "test_date": datetime.now().isoformat(),
                    "test_dates": [r["date"] for r in results],
                    "control_detection_rate": control_detection_rate,
                    "treatment_detection_rate": treatment_detection_rate,
                },
                "results": results,
            },
            f,
            default_flow_style=False,
        )

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phase 1 Pilot: Narrative Removal Test")
    parser.add_argument("--run", action="store_true", help="Actually run LLM test (costs $0.06)")

    args = parser.parse_args()

    run_pilot_test(dry_run=not args.run)
