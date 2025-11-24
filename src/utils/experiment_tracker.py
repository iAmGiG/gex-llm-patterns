"""
Experiment Tracker - Standardized naming and tracking for validation experiments
Ensures consistent naming convention and model tracking across all experiments.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ExperimentTracker:
    """Track experiments with standardized naming and model information.

    Naming convention:
    {event_id}_{model_name}_{experiment_type}_{timestamp}.json

    Example:
    covid_crash_2020_gpt4omini_normal_exp001.json
    covid_crash_2020_gpt4turbo_obfuscated_exp002.json
    """

    def __init__(self, base_dir: str = "reports/validation_experiments"):
        """Initialize experiment tracker with base directory."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_counter = self._get_next_experiment_id()

    def _get_next_experiment_id(self) -> int:
        """Get next experiment ID by scanning existing files."""
        existing_files = list(self.base_dir.glob("*_exp*.json"))
        if not existing_files:
            return 1

        max_id = 0
        for file in existing_files:
            parts = file.stem.split("_exp")
            if len(parts) > 1:
                try:
                    exp_id = int(parts[-1])
                    max_id = max(max_id, exp_id)
                except ValueError:
                    continue

        return max_id + 1

    def create_experiment_name(self, event_id: str, model_info: Dict[str, str], experiment_type: str = "normal") -> str:
        """Create standardized experiment filename.

        Args:
            event_id: Event identifier (e.g., "covid_crash_2020")
            model_info: Dictionary with model information
                - 'tool_model': Model used for tool/data operations (e.g., 'gpt-4o-mini')
                - 'prompt_model': Model used for analysis prompts (e.g., 'gpt-4-turbo')
            experiment_type: Type of experiment ('normal' or 'obfuscated')

        Returns:
            Standardized filename
        """
        # Clean model names for filename
        tool_model = self._clean_model_name(model_info.get("tool_model", "unknown"))
        prompt_model = self._clean_model_name(model_info.get("prompt_model", "unknown"))

        # If same model for both, use single name
        if tool_model == prompt_model:
            model_str = prompt_model
        else:
            model_str = f"{tool_model}_and_{prompt_model}"

        # Create filename with experiment ID
        exp_id = f"exp{self.experiment_counter:03d}"
        self.experiment_counter += 1

        filename = f"{event_id}_{model_str}_{experiment_type}_{exp_id}.json"

        return filename

    def _clean_model_name(self, model_name: str) -> str:
        """Clean model name for use in filename."""
        # Remove version numbers and special characters
        cleaned = model_name.lower()
        cleaned = cleaned.replace("gpt-4-turbo", "gpt4turbo")
        cleaned = cleaned.replace("gpt-4o-mini", "gpt4omini")
        cleaned = cleaned.replace("gpt-4o", "gpt4o")
        cleaned = cleaned.replace("gpt-4", "gpt4")
        cleaned = cleaned.replace("gpt-3.5-turbo", "gpt35turbo")
        cleaned = cleaned.replace("claude-", "claude")
        cleaned = cleaned.replace("-", "")
        cleaned = cleaned.replace(".", "")

        # Truncate if too long
        if len(cleaned) > 15:
            cleaned = cleaned[:15]

        return cleaned

    def save_experiment(
        self, event_id: str, model_info: Dict[str, str], results: Dict[str, Any], experiment_type: str = "normal"
    ) -> str:
        """Save experiment results with standardized naming.

        Args:
            event_id: Event identifier
            model_info: Model information dictionary
            results: Experiment results to save
            experiment_type: Type of experiment

        Returns:
            Path to saved file
        """
        # Add model info to results
        results["model_info"] = model_info
        results["experiment_metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "experiment_type": experiment_type,
            "event_id": event_id,
            "tool_model": model_info.get("tool_model", "unknown"),
            "prompt_model": model_info.get("prompt_model", "unknown"),
        }

        # Create filename
        filename = self.create_experiment_name(event_id, model_info, experiment_type)
        filepath = self.base_dir / filename

        # Save results
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)

        logger.info(f"Saved experiment to {filepath}")
        return str(filepath)

    def load_experiment(self, filename: str) -> Optional[Dict]:
        """Load experiment results from file."""
        filepath = self.base_dir / filename

        if not filepath.exists():
            logger.error(f"Experiment file not found: {filepath}")
            return None

        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading experiment: {e}")
            return None

    def list_experiments(
        self, event_id: Optional[str] = None, model: Optional[str] = None, experiment_type: Optional[str] = None
    ) -> list:
        """List experiments matching criteria.

        Args:
            event_id: Filter by event ID
            model: Filter by model name (searches both tool and prompt models)
            experiment_type: Filter by experiment type

        Returns:
            List of matching experiment filenames
        """
        pattern = "*"

        if event_id:
            pattern = f"{event_id}_*"

        files = list(self.base_dir.glob(f"{pattern}.json"))
        results = []

        for file in files:
            # Apply filters
            filename = file.name

            if model and model.lower() not in filename.lower():
                continue

            if experiment_type and f"_{experiment_type}_" not in filename:
                continue

            results.append(filename)

        return sorted(results)

    def get_experiment_summary(self, filename: str) -> Optional[Dict]:
        """Get summary of experiment without loading full results."""
        data = self.load_experiment(filename)

        if not data:
            return None

        metadata = data.get("experiment_metadata", {})

        return {
            "filename": filename,
            "event_id": metadata.get("event_id"),
            "timestamp": metadata.get("timestamp"),
            "tool_model": metadata.get("tool_model"),
            "prompt_model": metadata.get("prompt_model"),
            "experiment_type": metadata.get("experiment_type"),
            "accuracy_score": data.get("accuracy_score", 0),
            "confidence": data.get("llm_response", {}).get("confidence", 0),
        }


def demo_experiment_tracker():
    """Demonstrate experiment tracker usage."""
    tracker = ExperimentTracker()

    # Example model configurations
    model_configs = [
        {"tool_model": "gpt-4o-mini", "prompt_model": "gpt-4o-mini"},
        {"tool_model": "gpt-4o-mini", "prompt_model": "gpt-4-turbo"},
        {"tool_model": "gpt-4-turbo", "prompt_model": "gpt-4-turbo"},
    ]

    print("Experiment Naming Examples:")
    print("-" * 50)

    for config in model_configs:
        normal_name = tracker.create_experiment_name("covid_crash_2020", config, "normal")
        obfuscated_name = tracker.create_experiment_name("covid_crash_2020", config, "obfuscated")

        print(f"\nModel Config: {config}")
        print(f"  Normal: {normal_name}")
        print(f"  Obfuscated: {obfuscated_name}")

    print("\n" + "=" * 50)
    print("Standardized naming ensures clear model tracking!")


if __name__ == "__main__":
    demo_experiment_tracker()
