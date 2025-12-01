#!/usr/bin/env python3
"""
Issue #146: Extract WHO/WHOM/WHAT Reasoning by Quarter
Paper #1 MC Review Defense - Alpha Divergence / Hallucination

Extracts LLM reasoning texts from existing validation YAMLs and categorizes
by quarter to analyze qualitative changes from Q1 (high alpha) to Q4 (zero alpha).

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/146
"""

import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def load_validation_data(pattern_name):
    """Load validation YAML for a pattern."""
    yaml_path = (
        project_root / "reports" / "validation" / "paper1_pattern_taxonomy" / f"{pattern_name}_SPY_2024_unbiased.yaml"
    )

    if not yaml_path.exists():
        print(f"Warning: {yaml_path} not found")
        return None

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    return data


def categorize_by_quarter(date_str):
    """Categorize date into Q1, Q2, Q3, or Q4 2024."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    month = date.month

    if month <= 3:
        return "Q1"
    elif month <= 6:
        return "Q2"
    elif month <= 9:
        return "Q3"
    else:
        return "Q4"


def extract_reasoning_by_quarter(patterns):
    """Extract WHO/WHOM/WHAT reasoning texts categorized by quarter.

    Returns:
        dict: {quarter: [reasoning_texts]}
    """
    reasoning_by_quarter = defaultdict(
        lambda: {"detections": [], "who_texts": [], "whom_texts": [], "what_texts": [], "confidences": []}
    )

    for pattern_name in patterns:
        print(f"\nProcessing {pattern_name}...")
        data = load_validation_data(pattern_name)

        if data is None:
            continue

        detections = data.get("detections", [])
        print(f"  Found {len(detections)} total days")

        detected_count = 0

        for detection in detections:
            date = detection["date"]
            detected = detection.get("detected", False)

            if not detected:
                continue

            detected_count += 1
            quarter = categorize_by_quarter(date)

            narrative = detection.get("narrative", {})
            who = narrative.get("who", "")
            whom = narrative.get("whom", "")
            what = narrative.get("what", "")
            confidence = narrative.get("confidence", 0)

            # Store detection info
            reasoning_by_quarter[quarter]["detections"].append(
                {
                    "date": date,
                    "pattern": pattern_name,
                    "who": who,
                    "whom": whom,
                    "what": what,
                    "confidence": confidence,
                }
            )

            # Store text components
            if who:
                reasoning_by_quarter[quarter]["who_texts"].append(who)
            if whom:
                reasoning_by_quarter[quarter]["whom_texts"].append(whom)
            if what:
                reasoning_by_quarter[quarter]["what_texts"].append(what)
            if confidence > 0:
                reasoning_by_quarter[quarter]["confidences"].append(confidence)

        print(f"  Detected: {detected_count} days")

    return dict(reasoning_by_quarter)


def analyze_keyword_frequencies(reasoning_by_quarter):
    """Analyze keyword frequencies in WHAT texts by quarter.

    Focus on MC's expected keywords:
    - Q1 (high alpha): "amplification", "cascading", "reinforcing"
    - Q4 (zero alpha): "fragmentation", "dampening", "absorbed"
    """
    print("\n" + "=" * 80)
    print("KEYWORD FREQUENCY ANALYSIS")
    print("=" * 80)

    # Define keywords of interest
    amplification_keywords = [
        "amplif",
        "cascade",
        "cascading",
        "reinforc",
        "feedback",
        "accelerat",
        "momentum",
        "amplify",
    ]

    dampening_keywords = ["fragment", "dampen", "absorb", "dispers", "scatter", "neutral", "balanced", "offset"]

    hedging_keywords = ["hedge", "hedging", "adjust", "rebalanc", "delta"]

    results = {}

    for quarter in ["Q1", "Q2", "Q3", "Q4"]:
        if quarter not in reasoning_by_quarter:
            continue

        what_texts = reasoning_by_quarter[quarter]["what_texts"]
        total_detections = len(reasoning_by_quarter[quarter]["detections"])

        # Combine all WHAT texts
        combined_text = " ".join(what_texts).lower()

        # Count keywords
        amp_count = sum(1 for kw in amplification_keywords if kw in combined_text)
        damp_count = sum(1 for kw in dampening_keywords if kw in combined_text)
        hedge_count = sum(1 for kw in hedging_keywords if kw in combined_text)

        results[quarter] = {
            "total_detections": total_detections,
            "amplification_keywords": amp_count,
            "dampening_keywords": damp_count,
            "hedging_keywords": hedge_count,
            "avg_confidence": (
                sum(reasoning_by_quarter[quarter]["confidences"]) / len(reasoning_by_quarter[quarter]["confidences"])
                if reasoning_by_quarter[quarter]["confidences"]
                else 0
            ),
        }

        print(f"\n{quarter} 2024:")
        print(f"  Total detections: {total_detections}")
        print(f"  Amplification keywords: {amp_count}")
        print(f"  Dampening keywords: {damp_count}")
        print(f"  Hedging keywords: {hedge_count}")
        print(f"  Avg confidence: {results[quarter]['avg_confidence']:.1f}")

    return results


def extract_sample_responses(reasoning_by_quarter, n_samples=10):
    """Extract sample WHAT responses from Q1 and Q4 for qualitative review."""
    print("\n" + "=" * 80)
    print("SAMPLE REASONING TEXTS")
    print("=" * 80)

    samples = {}

    for quarter in ["Q1", "Q4"]:
        if quarter not in reasoning_by_quarter:
            continue

        detections = reasoning_by_quarter[quarter]["detections"]

        print(f"\n{quarter} 2024 Sample Responses (n={min(n_samples, len(detections))}):")
        print("-" * 80)

        samples[quarter] = []

        for i, detection in enumerate(detections[:n_samples]):
            sample = {
                "date": detection["date"],
                "pattern": detection["pattern"],
                "what": detection["what"],
                "confidence": detection["confidence"],
            }
            samples[quarter].append(sample)

            print(f"\n{i+1}. {detection['date']} ({detection['pattern']}):")
            print(f"   WHAT: {detection['what']}")
            print(f"   Confidence: {detection['confidence']}")

    return samples


def save_results(reasoning_by_quarter, keyword_results, samples):
    """Save extraction results to CSV and YAML."""
    output_dir = project_root / "docs" / "papers" / "paper1" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save all detections to CSV
    all_detections = []
    for quarter, data in reasoning_by_quarter.items():
        for detection in data["detections"]:
            all_detections.append({"quarter": quarter, **detection})

    df = pd.DataFrame(all_detections)
    csv_path = output_dir / "issue_146_reasoning_by_quarter.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n✅ Saved: {csv_path}")

    # Save keyword analysis to YAML
    summary = {
        "analysis_date": datetime.now().isoformat(),
        "total_detections_by_quarter": {q: len(data["detections"]) for q, data in reasoning_by_quarter.items()},
        "keyword_frequency_analysis": keyword_results,
        "sample_responses": samples,
    }

    yaml_path = output_dir / "issue_146_keyword_analysis.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(summary, f, default_flow_style=False, sort_keys=False)
    print(f"✅ Saved: {yaml_path}")

    return csv_path, yaml_path


def main():
    """Main workflow for Issue #146 reasoning extraction."""
    print("=" * 80)
    print("Issue #146: Extract Reasoning by Quarter")
    print("Paper #1 MC Review Defense - Alpha Divergence Analysis")
    print("=" * 80)

    # Patterns to analyze
    patterns = ["gamma_positioning", "stock_pinning", "0dte_hedging"]

    # Extract reasoning by quarter
    print("\nStep 1: Extracting reasoning texts from validation YAMLs...")
    reasoning_by_quarter = extract_reasoning_by_quarter(patterns)

    # Analyze keyword frequencies
    print("\nStep 2: Analyzing keyword frequencies...")
    keyword_results = analyze_keyword_frequencies(reasoning_by_quarter)

    # Extract sample responses
    print("\nStep 3: Extracting sample responses...")
    samples = extract_sample_responses(reasoning_by_quarter, n_samples=15)

    # Save results
    print("\nStep 4: Saving results...")
    csv_path, yaml_path = save_results(reasoning_by_quarter, keyword_results, samples)

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Review keyword frequency differences between Q1 and Q4")
    print("  2. Examine sample responses for qualitative differences")
    print("  3. Document findings in issue_146_analysis_report.md")
    print("  4. Determine if brief responses show sufficient differentiation")
    print("  5. If insufficient, consider Option 2 (batch API with rich prompts)")
    print()


if __name__ == "__main__":
    main()
