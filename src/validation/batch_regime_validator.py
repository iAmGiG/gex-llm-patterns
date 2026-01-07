#!/usr/bin/env python3
"""Batch API validator for regime window detection using OpenAI Batch API.

Purpose:
    Process 30-day regime windows using OpenAI Batch API for 50% cost reduction
    and async processing (no terminal blocking).

Benefits:
    - 50% cost reduction: $0.15 vs $0.30 per 1M tokens
    - Async processing: Submit 223 jobs, results in 1-2 hours
    - 250M input token quota (separate from sync API)
    - Total savings: ~$15-30 per validation phase

Usage:
    validator = BatchRegimeValidator()
    batch_id = validator.submit_batch(windows, symbol="SPY")
    results = validator.retrieve_results(batch_id)

Related:
    - Issue #112: OpenAI Batch API for cost optimization
    - validate_regime_windows.py: Main validation script
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from openai import APIError, OpenAI

# Import prompt builder for consistent prompts
from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder

# Import robust JSON parser (Issue #192)
from src.utils.json_parser import RobustJSONParser, extract_json

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_CACHE = PROJECT_ROOT / ".cache"

logger = logging.getLogger(__name__)


class BatchRegimeValidator:
    """Validates regime windows using OpenAI Batch API for cost efficiency.

    Batch API workflow:
    1. Prepare batch file (JSONL format)
    2. Upload to OpenAI
    3. Submit batch job
    4. Poll for completion (1-24 hours)
    5. Download and parse results
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize batch validator.

        Args:
            api_key: OpenAI API key (or use OPENAI_API_KEY env var or config.json)
        """
        # Load API key from config.json if not provided
        if api_key is None:
            api_key = self._load_api_key_from_json()

        self.client = OpenAI(api_key=api_key)
        self.prompt_builder = MechanicsPromptBuilder()
        self.batch_dir = PROJECT_ROOT / "reports" / "validation" / "paper2_regime_windows" / "batch_jobs"
        self.batch_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized BatchRegimeValidator")
        logger.info(f"Batch job directory: {self.batch_dir}")

    def _load_api_key_from_json(self) -> str:
        """Load OpenAI API key from config/config.json."""
        import os

        try:
            config_path = PROJECT_ROOT / "config" / "config.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    json_config = json.load(f)
                return json_config.get("OPEN_AI_KEY", "")
        except Exception as e:
            logger.warning(f"Failed to load config.json: {e}")

        # Fallback to environment
        return os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY") or ""

    def prepare_batch_file(
        self, windows: List[Dict], model: str = "o4-mini", output_file: Optional[Path] = None
    ) -> Path:
        """Generate JSONL batch file with regime detection prompts.

        Args:
            windows: List of window dicts with 'end_date' and 'gex_values'
            model: OpenAI model to use (default: o4-mini)
            output_file: Path to save JSONL file (auto-generated if None)

        Returns:
            Path to generated JSONL file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.batch_dir / f"batch_regime_{timestamp}.jsonl"

        logger.info(f"Preparing batch file with {len(windows)} windows")
        logger.info(f"Output file: {output_file}")

        batch_requests = []

        for i, window in enumerate(windows):
            end_date = window.get("end_date", f"Window_{i}")
            gex_sequence = window.get("gex_sequence", [])

            # Build regime detection prompt using consistent MechanicsPromptBuilder
            # This ensures batch API uses identical prompts as sync validator
            prompt_text = self.prompt_builder.build_regime_prompt(gex_sequence=gex_sequence, end_date=end_date)

            # OpenAI Batch API format - single user message with full prompt
            messages = [{"role": "user", "content": prompt_text}]

            # OpenAI Batch API format
            # OpenAI Batch API format
            request_body = {"model": model, "messages": messages}

            # Only add temperature for non-reasoning models (o4-mini requires default temperature=1)
            if not model.startswith("o"):
                request_body["temperature"] = 0.0  # Deterministic for non-reasoning models

            request = {
                "custom_id": f"window-{end_date}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": request_body,
            }

            batch_requests.append(request)

        # Write JSONL file
        with open(output_file, "w") as f:
            for request in batch_requests:
                f.write(json.dumps(request) + "\n")

        logger.info(f"Generated {len(batch_requests)} batch requests")
        logger.info(f"Saved to {output_file}")

        return output_file

    def submit_batch(self, batch_file: Path, description: Optional[str] = None) -> str:
        """Upload batch file and create batch job.

        Args:
            batch_file: Path to JSONL batch file
            description: Optional batch description (e.g., "Phase 1 Q1 2024")

        Returns:
            Batch job ID
        """
        logger.info(f"Uploading batch file: {batch_file}")
        logger.info(f"File size: {batch_file.stat().st_size} bytes")

        # Upload file
        with open(batch_file, "rb") as f:
            response = self.client.files.create(file=f, purpose="batch")
            batch_file_id = response.id

        logger.info(f"Uploaded file ID: {batch_file_id}")

        # Create batch job
        batch_description = description or f"Regime validation - {datetime.now().isoformat()}"

        batch = self.client.batches.create(
            input_file_id=batch_file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"description": batch_description},
        )

        batch_id = batch.id
        logger.info(f"Created batch job: {batch_id}")
        logger.info(f"Status: {batch.status}")
        logger.info(f"Expected completion: Within 24 hours (typically 1-2 hours)")

        # Save batch metadata for tracking
        metadata_file = self.batch_dir / f"batch_{batch_id}_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(
                {
                    "batch_id": batch_id,
                    "file_id": batch_file_id,
                    "input_file": str(batch_file),
                    "created_at": datetime.now().isoformat(),
                    "description": batch_description,
                    "status": batch.status,
                },
                f,
                indent=2,
            )

        logger.info(f"Saved metadata to {metadata_file}")

        return batch_id

    def poll_batch(
        self, batch_id: str, poll_interval: int = 60, max_polls: int = 1440  # 24 hours at 1 min intervals
    ) -> Dict:
        """Poll batch job status until completion.

        Args:
            batch_id: Batch job ID
            poll_interval: Seconds between polls (default 60)
            max_polls: Maximum number of polls (default 1440 = 24 hours)

        Returns:
            Final batch status dict
        """
        logger.info(f"Polling batch {batch_id} (interval={poll_interval}s, max_polls={max_polls})")

        poll_count = 0
        start_time = time.time()

        while poll_count < max_polls:
            batch = self.client.batches.retrieve(batch_id)

            logger.info(f"Poll {poll_count + 1}: Status={batch.status}, Request counts: {batch.request_counts}")

            if batch.status == "completed":
                elapsed = time.time() - start_time
                logger.info(f"✅ Batch completed in {elapsed/60:.1f} minutes")
                return {
                    "batch_id": batch_id,
                    "status": batch.status,
                    "output_file_id": batch.output_file_id,
                    "elapsed_seconds": elapsed,
                    "request_counts": batch.request_counts,
                }

            elif batch.status == "failed":
                logger.error(f"❌ Batch failed: {batch.errors}")
                return {
                    "batch_id": batch_id,
                    "status": batch.status,
                    "errors": batch.errors if hasattr(batch, "errors") else "Unknown error",
                }

            elif batch.status in ["validating", "queued", "in_progress", "finalizing"]:
                poll_count += 1
                logger.info(f"Batch still processing... Waiting {poll_interval}s before next poll")
                time.sleep(poll_interval)

            else:
                logger.warning(f"Unexpected status: {batch.status}")
                poll_count += 1
                time.sleep(poll_interval)

        logger.error(f"Polling timeout after {max_polls} attempts")
        return {"batch_id": batch_id, "status": "timeout", "elapsed_seconds": time.time() - start_time}

    def retrieve_results(self, batch_id: str, output_file: Optional[Path] = None) -> List[Dict]:
        """Download and parse batch results.

        Args:
            batch_id: Batch job ID
            output_file: Path to save results JSONL (auto-generated if None)

        Returns:
            List of parsed results (one per window)
        """
        logger.info(f"Retrieving results for batch {batch_id}")

        # Get batch info
        batch = self.client.batches.retrieve(batch_id)

        if batch.status != "completed":
            logger.error(f"Batch not completed: status={batch.status}")
            return []

        output_file_id = batch.output_file_id
        logger.info(f"Output file ID: {output_file_id}")

        # Download results
        if output_file is None:
            output_file = self.batch_dir / f"results_{batch_id}.jsonl"

        logger.info(f"Downloading results to {output_file}")

        file_content = self.client.files.content(output_file_id)
        with open(output_file, "wb") as f:
            f.write(file_content.read())

        # Parse results
        results = []
        with open(output_file, "r") as f:
            for line in f:
                if line.strip():
                    result = json.loads(line)
                    results.append(result)

        logger.info(f"Retrieved {len(results)} results")

        # Parse LLM responses from batch results
        parsed_results = []
        for result in results:
            try:
                parsed = self._parse_batch_result(result)
                parsed_results.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing result for {result.get('custom_id')}: {e}")
                continue

        return parsed_results

    def _parse_batch_result(self, batch_result: Dict) -> Dict:
        """Parse individual batch result from OpenAI format.

        Uses robust JSON parser (Issue #192) to handle LLM formatting quirks:
        - Markdown code blocks (```json ... ```)
        - Conversational prefixes/suffixes
        - Trailing commas
        - Invalid escape sequences

        Args:
            batch_result: Single result from batch output

        Returns:
            Parsed regime detection result
        """
        custom_id = batch_result.get("custom_id", "unknown")

        # Check for errors
        if batch_result.get("error"):
            return {"window_id": custom_id, "error": batch_result["error"], "regime_detected": False}

        # Extract LLM response
        try:
            response = batch_result.get("response", {})
            body = response.get("body", {})
            choices = body.get("choices", [])

            if not choices:
                logger.warning(f"No choices in response for {custom_id}")
                return {"window_id": custom_id, "error": "No choices in response", "regime_detected": False}

            message = choices[0].get("message", {})
            content = message.get("content", "{}")

            # Use robust JSON parser (Issue #192)
            llm_response, strategy = extract_json(content, return_strategy=True)

            if llm_response is None:
                logger.error(f"All JSON parsing strategies failed for {custom_id}")
                return {
                    "window_id": custom_id,
                    "error": "JSON parse error: all strategies failed",
                    "regime_detected": False,
                    "raw_content": content[:500],  # Include truncated content for debugging
                }

            logger.debug(f"Parsed {custom_id} using strategy: {strategy}")

            return {
                "window_id": custom_id,
                "regime_type": llm_response.get("regime_type", "unknown"),
                "regime_detected": llm_response.get("regime_detected", False),
                "confidence": llm_response.get("confidence", 0),
                "reasoning": llm_response.get("reasoning", ""),
                "raw_response": llm_response,
                "parse_strategy": strategy,  # Track which strategy succeeded
            }

        except Exception as e:
            logger.error(f"Unexpected error parsing result for {custom_id}: {e}")
            return {"window_id": custom_id, "error": f"Parse error: {e}", "regime_detected": False}

    def save_results_yaml(self, results: List[Dict], windows: List[Dict], output_file: Path, batch_id: str):
        """Save batch results in YAML format compatible with sync validation.

        Args:
            results: Parsed batch results from retrieve_results()
            windows: Original window list
            output_file: Path to save YAML
            batch_id: Batch job ID for reference
        """
        logger.info(f"Saving {len(results)} results to {output_file}")

        # Create YAML structure
        yaml_output = {
            "validation_metadata": {
                "batch_mode": True,
                "batch_id": batch_id,
                "windows_tested": len(results),
                "timestamp": datetime.now().isoformat(),
                "cost_savings_pct": 50,
                "note": "Results from OpenAI Batch API (50% cost reduction)",
            },
            "summary_statistics": self._calculate_summary(results),
            "windows": results,
        }

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            yaml.dump(yaml_output, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved results to {output_file}")

    def _calculate_summary(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics from results."""
        detected = sum(1 for r in results if r.get("regime_detected", False))
        total = len(results)

        return {
            "detection_rate_pct": (detected / total * 100) if total > 0 else 0,
            "regimes_detected": detected,
            "total_windows": total,
            "confidence_avg": sum(r.get("confidence", 0) for r in results) / total if total > 0 else 0,
        }


def format_gex_for_prompt(gex_values: List[float]) -> str:
    """Format GEX values for LLM prompt (obfuscated dates).

    Args:
        gex_values: List of GEX values in dollars

    Returns:
        Formatted string for LLM prompt
    """
    lines = []
    for i, gex in enumerate(gex_values):
        day_offset = i - len(gex_values) + 1
        day_label = f"Day T{day_offset:+d}" if day_offset != 0 else "Day T+0"
        gex_billions = gex / 1e9
        sign = "+" if gex > 0 else ""
        lines.append(f"{day_label}: {sign}{gex_billions:.2f}B")

    return "\n".join(lines)


def main():
    """Example usage of BatchRegimeValidator."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenAI Batch API validator")
    parser.add_argument("--submit", action="store_true", help="Submit batch job")
    parser.add_argument("--poll", type=str, help="Poll batch job status")
    parser.add_argument("--retrieve", type=str, help="Retrieve batch results")
    parser.add_argument("--batch-file", type=str, help="Path to JSONL batch file")

    args = parser.parse_args()

    validator = BatchRegimeValidator()

    if args.submit and args.batch_file:
        batch_file = Path(args.batch_file)
        batch_id = validator.submit_batch(batch_file, description="Phase 1 Q1 2024")
        print(f"Submitted batch: {batch_id}")
        print(f"Save this ID to poll later: {batch_id}")

    elif args.poll:
        status = validator.poll_batch(args.poll, poll_interval=10)  # 10s for testing
        print(f"Batch status: {json.dumps(status, indent=2)}")

    elif args.retrieve:
        results = validator.retrieve_results(args.retrieve)
        print(f"Retrieved {len(results)} results")
        for result in results[:5]:
            print(
                f"  {result.get('window_id')}: {result.get('regime_type')} " f"(confidence={result.get('confidence')})"
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
