#!/usr/bin/env python3
"""
Issue #146 Phase 2: Rich Reasoning Extraction via Batch API
Paper #1 MC Review Defense - Alpha Divergence / Hallucination

This script samples detection days from Q1 and Q4 2024, generates
detailed causal explanation prompts using the new "rich_reasoning"
template, and submits them via OpenAI Batch API for keyword analysis.

Purpose:
    Test if LLM reasoning adapts qualitatively from Q1 (high alpha)
    to Q4 (zero alpha). Specifically, look for:
    - Q1: "amplification", "cascading", "reinforcing" language
    - Q4: "fragmentation", "dampening", "absorbed" language

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/146
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RichReasoningBatchValidator:
    """
    Wrapper for Issue #146 Phase 2 - Rich reasoning extraction via Batch API.

    Reuses Paper #2's batch infrastructure but builds custom prompts for
    single-day pattern detection with detailed causal explanations.
    """

    def __init__(self):
        """Initialize validator with config and directories."""
        # Load OpenAI API key from config
        config_path = project_root / "config" / "config.json"
        with open(config_path, "r") as f:
            config = json.load(f)

        self.client = OpenAI(api_key=config["OPEN_AI_KEY"])

        # Set up directories
        self.analysis_dir = project_root / "docs" / "papers" / "paper1" / "analysis"
        self.batch_dir = self.analysis_dir / "batch_jobs"
        self.batch_dir.mkdir(parents=True, exist_ok=True)

        # Load prompt template configuration
        with open(project_root / "config_defaults" / "llm_prompts.yaml", "r") as f:
            self.prompt_config = yaml.safe_load(f)

        logger.info(f"Initialized RichReasoningBatchValidator")
        logger.info(f"Batch directory: {self.batch_dir}")

    def load_phase1_detections(self) -> pd.DataFrame:
        """Load Phase 1 extraction results (519 detections)."""
        csv_path = self.analysis_dir / "issue_146_reasoning_by_quarter.csv"

        if not csv_path.exists():
            raise FileNotFoundError(
                f"Phase 1 extraction file not found: {csv_path}\n" "Run issue_146_extract_reasoning_by_quarter.py first"
            )

        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} detections from Phase 1")
        logger.info(f"  Q1: {len(df[df['quarter']=='Q1'])} detections")
        logger.info(f"  Q2: {len(df[df['quarter']=='Q2'])} detections")
        logger.info(f"  Q3: {len(df[df['quarter']=='Q3'])} detections")
        logger.info(f"  Q4: {len(df[df['quarter']=='Q4'])} detections")

        return df

    def sample_days_for_batch(self, detections_df: pd.DataFrame, n_per_quarter: int = 25) -> Dict[str, List[Dict]]:
        """Sample days from Q1 and Q4 for batch processing.

        Args:
            detections_df: Phase 1 detection data
            n_per_quarter: Number of samples per quarter (default: 25)

        Returns:
            Dict with 'Q1' and 'Q4' keys, each containing list of sample dicts
        """
        samples = {}

        for quarter in ["Q1", "Q4"]:
            quarter_df = detections_df[detections_df["quarter"] == quarter]

            # Deduplicate by date (some dates detected multiple patterns)
            # Keep first occurrence for each date
            quarter_df_unique = quarter_df.drop_duplicates(subset=["date"], keep="first")

            # Random sample (with seed for reproducibility)
            sample_size = min(n_per_quarter, len(quarter_df_unique))
            sampled = quarter_df_unique.sample(n=sample_size, random_state=42)

            samples[quarter] = sampled.to_dict("records")

            logger.info(
                f"{quarter}: Sampled {sample_size} unique days from {len(quarter_df)} total detections ({len(quarter_df_unique)} unique dates)"
            )

        return samples

    def load_gex_data_for_date(self, date_str: str) -> Optional[Dict]:
        """Load GEX data for a specific date from consolidated database.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Dict with net_gex, spot_price, flip_point, or None if not found
        """
        import sqlite3

        db_path = project_root / ".cache" / "consolidated_historical.db"

        if not db_path.exists():
            logger.warning(f"Database not found: {db_path}")
            return None

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Query for GEX data
            query = """
                SELECT total_gex, spot_price, gamma_flip_point
                FROM daily_gex_metrics
                WHERE date = ? AND symbol = 'SPY'
            """

            cursor.execute(query, (date_str,))
            row = cursor.fetchone()
            conn.close()

            if row is None:
                logger.warning(f"No GEX data found for {date_str}")
                return None

            return {
                "net_gex_usd": row[0],  # Using total_gex (in USD already)
                "spot_price": row[1],
                "flip_point": row[2],
            }

        except Exception as e:
            logger.error(f"Error loading GEX data for {date_str}: {e}")
            return None

    def build_rich_reasoning_prompt(self, date_str: str, gex_data: Dict) -> str:
        """Build rich reasoning prompt for a single day.

        Uses the new "detailed_causal_explanation" question template
        from config_defaults/llm_prompts.yaml.

        Args:
            date_str: Date in YYYY-MM-DD format
            gex_data: Dict with net_gex_usd, spot_price, flip_point

        Returns:
            Complete prompt text
        """
        # Get question template
        question_template = self.prompt_config["question_templates"]["detailed_causal_explanation"]

        # Format GEX data
        net_gex_b = gex_data["net_gex_usd"] / 1e9
        spot_price = gex_data["spot_price"]
        flip_point = gex_data["flip_point"]

        # Handle None values for flip_point
        if flip_point is None or flip_point == 0:
            distance_to_flip = 0
            distance_pct = 0
            flip_point_str = "N/A"
            distance_str = "N/A"
        else:
            distance_to_flip = spot_price - flip_point
            distance_pct = (distance_to_flip / flip_point) * 100
            flip_point_str = f"${flip_point:.2f}"
            distance_str = f"${distance_to_flip:+.2f} ({distance_pct:+.1f}%)"

        # Build prompt
        prompt = f"""You are analyzing market mechanics for SPY on a single trading day.

{question_template['overall_analysis'].format(symbol='SPY')}

## MARKET DATA (Single Day)

- Net GEX: ${net_gex_b:+.2f}B
- Spot Price: ${spot_price:.2f}
- Gamma Flip Point: {flip_point_str}
- Spot vs Flip: {distance_str}

{question_template['individual_days']}

## RESPONSE FORMAT

Return your analysis as a JSON object with this EXACT structure:

{{
  "pattern_detected": true/false,
  "who": "Primary forcing party (if pattern detected)",
  "whom": "Party being forced (if pattern detected)",
  "what_mechanism": "DETAILED 50-100 word causal explanation using rich qualitative language",
  "intensity_language": "Qualitative descriptor (e.g., 'strong amplification', 'moderate dampening')",
  "context_factors": "Market structure factors (e.g., 'concentrated positioning', 'fragmented exposure')",
  "confidence": 0-100,
  "caveats": ["caveat1", "caveat2"] or [] if none
}}

IMPORTANT: Use rich descriptive language in what_mechanism, intensity_language, and context_factors.
"""

        return prompt

    def prepare_batch_file(self, samples: Dict[str, List[Dict]], model: str = "gpt-4o-mini") -> Path:
        """Generate JSONL batch file for OpenAI Batch API.

        Args:
            samples: Dict with 'Q1' and 'Q4' sample lists
            model: OpenAI model (default: gpt-4o-mini for cost efficiency)

        Returns:
            Path to generated JSONL file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.batch_dir / f"issue_146_rich_reasoning_{timestamp}.jsonl"

        logger.info(f"Preparing batch file: {output_file}")

        batch_requests = []
        request_id = 0

        for quarter, sample_list in samples.items():
            for sample in sample_list:
                date_str = sample["date"]

                # Load GEX data for this date
                gex_data = self.load_gex_data_for_date(date_str)

                if gex_data is None:
                    logger.warning(f"Skipping {date_str} - no GEX data")
                    continue

                # Build rich reasoning prompt
                prompt_text = self.build_rich_reasoning_prompt(date_str, gex_data)

                # OpenAI Batch API format
                request = {
                    "custom_id": f"{quarter}-{date_str}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt_text}],
                        "temperature": 0.0,  # Deterministic for consistency
                    },
                }

                batch_requests.append(request)
                request_id += 1

        # Write JSONL file
        with open(output_file, "w") as f:
            for request in batch_requests:
                f.write(json.dumps(request) + "\n")

        logger.info(f"✅ Generated {len(batch_requests)} batch requests")
        logger.info(f"   File: {output_file}")

        return output_file

    def submit_batch(self, batch_file: Path) -> str:
        """Upload batch file and submit batch job to OpenAI.

        Args:
            batch_file: Path to JSONL batch file

        Returns:
            Batch ID for polling/retrieval
        """
        logger.info(f"Uploading batch file: {batch_file}")

        # Upload file
        with open(batch_file, "rb") as f:
            file_response = self.client.files.create(file=f, purpose="batch")

        file_id = file_response.id
        logger.info(f"✅ File uploaded: {file_id}")

        # Submit batch job
        batch_response = self.client.batches.create(
            input_file_id=file_id, endpoint="/v1/chat/completions", completion_window="24h"
        )

        batch_id = batch_response.id
        logger.info(f"✅ Batch submitted: {batch_id}")
        logger.info(f"   Status: {batch_response.status}")
        logger.info(f"   Expected completion: 1-2 hours")

        # Save batch metadata
        metadata = {
            "batch_id": batch_id,
            "file_id": file_id,
            "batch_file": str(batch_file),
            "submitted_at": datetime.now().isoformat(),
            "status": batch_response.status,
            "model": "gpt-4o-mini",
        }

        metadata_file = self.batch_dir / f"batch_metadata_{batch_id}.yaml"
        with open(metadata_file, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False)

        logger.info(f"✅ Metadata saved: {metadata_file}")

        return batch_id

    def poll_batch_status(self, batch_id: str):
        """Poll batch job status.

        Args:
            batch_id: Batch ID from submit_batch()
        """
        batch = self.client.batches.retrieve(batch_id)

        logger.info(f"Batch {batch_id} status: {batch.status}")

        if batch.request_counts:
            logger.info(f"  Total: {batch.request_counts.total}")
            logger.info(f"  Completed: {batch.request_counts.completed}")
            logger.info(f"  Failed: {batch.request_counts.failed}")

        return batch.status

    def retrieve_results(self, batch_id: str) -> Path:
        """Retrieve and parse batch results.

        Args:
            batch_id: Batch ID from submit_batch()

        Returns:
            Path to saved results file
        """
        logger.info(f"Retrieving results for batch {batch_id}")

        # Get batch status
        batch = self.client.batches.retrieve(batch_id)

        if batch.status != "completed":
            raise ValueError(f"Batch not completed yet. Status: {batch.status}")

        # Download output file
        output_file_id = batch.output_file_id

        if not output_file_id:
            raise ValueError("Batch completed but no output file available")

        # Retrieve file content
        file_content = self.client.files.content(output_file_id)

        # Save raw results
        results_file = self.batch_dir / f"batch_results_{batch_id}.jsonl"
        with open(results_file, "wb") as f:
            f.write(file_content.content)

        logger.info(f"✅ Results saved: {results_file}")

        # Parse results into structured format
        parsed_results = self._parse_batch_results(results_file)

        # Save parsed results
        parsed_file = self.analysis_dir / f"issue_146_phase2_batch_results_{batch_id}.csv"
        parsed_df = pd.DataFrame(parsed_results)
        parsed_df.to_csv(parsed_file, index=False)

        logger.info(f"✅ Parsed results saved: {parsed_file}")
        logger.info(f"   Total responses: {len(parsed_results)}")

        return parsed_file

    def _parse_batch_results(self, results_file: Path) -> List[Dict]:
        """Parse batch results JSONL file into structured data."""
        results = []

        with open(results_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue

                response = json.loads(line)
                custom_id = response["custom_id"]

                # Extract quarter and date from custom_id (format: "Q1-2024-01-02")
                quarter, date_str = custom_id.split("-", 1)

                # Extract LLM response
                try:
                    message_content = response["response"]["body"]["choices"][0]["message"]["content"]

                    # Strip markdown code fences if present (```json ... ```)
                    if message_content.strip().startswith("```"):
                        # Find the JSON content between code fences
                        lines = message_content.strip().split("\n")
                        # Remove first line (```json) and last line (```)
                        json_content = "\n".join(lines[1:-1])
                    else:
                        json_content = message_content

                    # Parse JSON response from LLM
                    llm_json = json.loads(json_content)

                    result = {
                        "quarter": quarter,
                        "date": date_str,
                        "pattern_detected": llm_json.get("pattern_detected", False),
                        "who": llm_json.get("who", ""),
                        "whom": llm_json.get("whom", ""),
                        "what_mechanism": llm_json.get("what_mechanism", ""),
                        "intensity_language": llm_json.get("intensity_language", ""),
                        "context_factors": llm_json.get("context_factors", ""),
                        "confidence": llm_json.get("confidence", 0),
                        "caveats": json.dumps(llm_json.get("caveats", [])),
                    }

                    results.append(result)

                except (KeyError, json.JSONDecodeError) as e:
                    logger.error(f"Error parsing response for {custom_id}: {e}")
                    continue

        return results


def main():
    """Main workflow for Issue #146 Phase 2."""
    import argparse

    parser = argparse.ArgumentParser(description="Issue #146 Phase 2: Rich Reasoning Extraction via Batch API")
    parser.add_argument(
        "--action", choices=["prepare", "submit", "poll", "retrieve"], required=True, help="Action to perform"
    )
    parser.add_argument("--batch-id", help="Batch ID (for poll/retrieve actions)")
    parser.add_argument("--n-samples", type=int, default=25, help="Number of samples per quarter (default: 25)")

    args = parser.parse_args()

    validator = RichReasoningBatchValidator()

    if args.action == "prepare":
        # Step 1: Load Phase 1 detections
        detections_df = validator.load_phase1_detections()

        # Step 2: Sample days from Q1 and Q4
        samples = validator.sample_days_for_batch(detections_df, n_per_quarter=args.n_samples)

        # Step 3: Prepare batch file
        batch_file = validator.prepare_batch_file(samples)

        print(f"\n✅ Batch file prepared: {batch_file}")
        print(f"\nNext step: python {__file__} --action submit")

    elif args.action == "submit":
        # Find most recent batch file
        batch_files = sorted(validator.batch_dir.glob("issue_146_rich_reasoning_*.jsonl"))
        if not batch_files:
            print("❌ No batch file found. Run --action prepare first.")
            return

        batch_file = batch_files[-1]
        print(f"Submitting batch file: {batch_file}")

        batch_id = validator.submit_batch(batch_file)

        print(f"\n✅ Batch submitted: {batch_id}")
        print(f"\nNext step: python {__file__} --action poll --batch-id {batch_id}")

    elif args.action == "poll":
        if not args.batch_id:
            print("❌ --batch-id required for poll action")
            return

        status = validator.poll_batch_status(args.batch_id)
        print(f"\nStatus: {status}")

        if status == "completed":
            print(f"\n✅ Batch complete! Ready to retrieve results.")
            print(f"\nNext step: python {__file__} --action retrieve --batch-id {args.batch_id}")

    elif args.action == "retrieve":
        if not args.batch_id:
            print("❌ --batch-id required for retrieve action")
            return

        results_file = validator.retrieve_results(args.batch_id)

        print(f"\n✅ Results retrieved: {results_file}")
        print(f"\nNext step: Analyze keyword frequencies and TF-IDF")


if __name__ == "__main__":
    main()
