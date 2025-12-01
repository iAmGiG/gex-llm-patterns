"""Reports Manager for GEX-LLM Analysis Outputs.

⚠️ DEPRECATED: This module is deprecated in favor of unified_reports_manager.py
Please update your imports to:
    from src.utils.unified_reports_manager import reports_manager

This file is maintained for backward compatibility only.
New code should use UnifiedReportsManager which provides:
- Cleaner directory structure (experiments/, validation/, archive/)
- YAML format support with obfuscation
- Better organization by experiment type
- All methods from this class are available via backward compatibility wrappers

Legacy code using this import will continue to work through global alias.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .date_utils import now_iso, now_timestamp

logger = logging.getLogger(__name__)


class ReportsManager:
    """Manages all analysis outputs and reports.

    Provides organized storage for:
    - GEX calculation results
    - Pattern analysis outputs
    - Agent conversation logs
    - Data quality reports
    """

    def __init__(self, base_dir: str = "reports"):
        """Initialize reports manager with directory structure."""
        self.base_dir = Path(base_dir)

        # Create subdirectories
        self.gex_dir = self.base_dir / "gex_calculations"
        self.pattern_dir = self.base_dir / "pattern_analysis"
        self.quality_dir = self.base_dir / "data_quality"
        self.agent_dir = self.base_dir / "agent_outputs"
        # demo_results removed - use validation_experiments instead

        # Ensure all directories exist
        for directory in [self.gex_dir, self.pattern_dir, self.quality_dir, self.agent_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    # ===========================
    # Data Filtering Helpers
    # ===========================

    def filter_strike_data(self, gex_data: Dict, min_volume: int = 0, min_oi: int = 1) -> Dict:
        """Filter strike data to remove zero OI strikes (keep volume > 0 for potential GEX).

        Args:
            gex_data: GEX data dictionary
            min_volume: Minimum volume (0 = keep all with any activity)
            min_oi: Minimum open interest (1 = remove zero OI)

        Returns:
            Filtered GEX data
        """
        if "gex_by_strike" not in gex_data:
            return gex_data

        filtered_data = gex_data.copy()
        gex_by_strike = gex_data["gex_by_strike"]

        if not isinstance(gex_by_strike, dict):
            return filtered_data

        # Count original strikes
        original_count = len(gex_by_strike.get("strike", {}))

        # Filter logic - keep strikes with volume OR open interest
        keep_indices = []

        for i, (strike_key, strike_val) in enumerate(gex_by_strike.get("strike", {}).items()):
            volume = gex_by_strike.get("volume", {}).get(str(i), 0)
            oi = gex_by_strike.get("open_interest", {}).get(str(i), 0)

            # Keep if has volume OR open interest (potential GEX contribution)
            if volume >= min_volume or oi >= min_oi:
                keep_indices.append(i)

        # Filter all strike arrays
        if keep_indices and len(keep_indices) < original_count:
            filtered_gex_by_strike = {}

            for field, field_data in gex_by_strike.items():
                if isinstance(field_data, dict):
                    filtered_field = {}
                    for new_idx, orig_idx in enumerate(keep_indices):
                        if str(orig_idx) in field_data:
                            filtered_field[str(new_idx)] = field_data[str(orig_idx)]
                    filtered_gex_by_strike[field] = filtered_field
                else:
                    filtered_gex_by_strike[field] = field_data

            filtered_data["gex_by_strike"] = filtered_gex_by_strike

            logger.info(f"Filtered strike data: {original_count} -> {len(keep_indices)} strikes")

        return filtered_data

    # ===========================
    # GEX Results Storage
    # ===========================

    def save_gex_results(self, symbol, results: Dict[Any, Any], trading_date=None, filter_strikes: bool = True) -> Path:
        """Save GEX calculation results with strike filtering.

        Args:
            symbol: Stock symbol
            results: GEX calculation results dictionary
            trading_date: Optional trading date
            filter_strikes: Remove zero OI strikes to reduce file size

        Returns:
            Path to saved file
        """
        # Filter strike data to prevent bloated files
        if filter_strikes and isinstance(results, dict):
            results = self.filter_strike_data(results)

        # Clean filename without timestamp bloat
        if trading_date:
            filename = f"gex_{symbol}_{trading_date}.json"
        else:
            filename = f"gex_{symbol}.json"

        save_dir = self.gex_dir
        file_path = save_dir / filename

        # If file exists, add counter instead of timestamp
        counter = 1
        while file_path.exists():
            if trading_date:
                filename = f"gex_{symbol}_{trading_date}_{counter}.json"
            else:
                filename = f"gex_{symbol}_{counter}.json"
            file_path = save_dir / filename
            counter += 1

        # Add metadata
        output_data = {
            "metadata": {
                "symbol": symbol,
                "trading_date": trading_date,
                "generated_at": now_iso(),
                "type": "gex_calculation_results",
            },
            "results": results,
        }

        with open(file_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"Saved GEX results to {file_path}")
        return file_path

    def save_gex_time_series(self, symbol, data: pd.DataFrame, is_demo: bool = False) -> Path:
        """Save GEX time series data as CSV."""
        timestamp = now_timestamp()
        filename = f"{symbol}_{timestamp}_gex_timeseries.csv"

        save_dir = self.gex_dir  # No more demo mode
        file_path = save_dir / filename

        data.to_csv(file_path, index=True)
        logger.info(f"Saved GEX time series to {file_path}")
        return file_path

    # ===========================
    # Pattern Analysis Storage
    # ===========================

    def save_pattern_analysis(self, pattern_type, results: Dict[Any, Any], symbol=None, is_demo: bool = False) -> Path:
        """Save pattern analysis results."""
        timestamp = now_timestamp()

        if symbol:
            filename = f"{pattern_type}_{symbol}_{timestamp}_analysis.json"
        else:
            filename = f"{pattern_type}_{timestamp}_analysis.json"

        save_dir = self.pattern_dir  # No more demo mode
        file_path = save_dir / filename

        output_data = {
            "metadata": {
                "pattern_type": pattern_type,
                "symbol": symbol,
                "generated_at": now_iso(),
                "type": "pattern_analysis_results",
            },
            "analysis": results,
        }

        with open(file_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"Saved pattern analysis to {file_path}")
        return file_path

    # ===========================
    # Agent Outputs Storage
    # ===========================

    def save_agent_conversation(
        self, agent_names: List[str], conversation_log: List[Dict[Any, Any]], is_demo: bool = False
    ) -> Path:
        """Save multi-agent conversation log."""
        timestamp = now_timestamp()
        agents_str = "_".join(agent_names)
        filename = f"{agents_str}_{timestamp}_conversation.json"

        save_dir = self.agent_dir  # No more demo mode
        file_path = save_dir / filename

        output_data = {
            "metadata": {
                "agents": agent_names,
                "generated_at": now_iso(),
                "type": "agent_conversation_log",
                "message_count": len(conversation_log),
            },
            "conversation": conversation_log,
        }

        with open(file_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"Saved agent conversation to {file_path}")
        return file_path

    def save_agent_results(self, agent_name, task, results: Dict[Any, Any], is_demo: bool = False) -> Path:
        """Save individual agent task results."""
        timestamp = now_timestamp()
        filename = f"{agent_name}_{task}_{timestamp}_results.json"

        save_dir = self.agent_dir  # No more demo mode
        file_path = save_dir / filename

        output_data = {
            "metadata": {
                "agent_name": agent_name,
                "task": task,
                "generated_at": now_iso(),
                "type": "agent_task_results",
            },
            "results": results,
        }

        with open(file_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"Saved agent results to {file_path}")
        return file_path

    # ===========================
    # Data Quality Reports
    # ===========================

    def save_quality_report(
        self, symbol, report: Dict[Any, Any], data_type: str = "options", is_demo: bool = False
    ) -> Path:
        """Save data quality assessment report."""
        timestamp = now_timestamp()
        filename = f"{symbol}_{data_type}_{timestamp}_quality_report.json"

        save_dir = self.quality_dir  # No more demo mode
        file_path = save_dir / filename

        output_data = {
            "metadata": {
                "symbol": symbol,
                "data_type": data_type,
                "generated_at": now_iso(),
                "type": "data_quality_report",
            },
            "report": report,
        }

        with open(file_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)

        logger.info(f"Saved quality report to {file_path}")
        return file_path

    # ===========================
    # Utility Methods
    # ===========================

    def list_reports(self, category: str = "all"):
        """List available reports by category."""
        if category == "gex":
            return list(self.gex_dir.glob("*.json")) + list(self.gex_dir.glob("*.csv"))
        elif category == "patterns":
            return list(self.pattern_dir.glob("*.json"))
        elif category == "agents":
            return list(self.agent_dir.glob("*.json"))
        elif category == "quality":
            return list(self.quality_dir.glob("*.json"))
        elif category == "demo":
            return list(self.demo_dir.glob("*"))
        else:  # all
            all_files = []
            for directory in [self.gex_dir, self.pattern_dir, self.quality_dir, self.agent_dir, self.demo_dir]:
                all_files.extend(list(directory.glob("*")))
            return all_files

    def cleanup_old_results(self, older_than_days: int = 7) -> int:
        """Clean up old results across all directories."""
        from datetime import datetime

        cutoff_time = datetime.now().timestamp() - (older_than_days * 24 * 3600)
        cleaned = 0

        # Clean up across all result directories
        for directory in [self.gex_dir, self.pattern_dir, self.quality_dir, self.agent_dir]:
            for file_path in directory.glob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    cleaned += 1

        logger.info(f"Cleaned {cleaned} old files older than {older_than_days} days")
        return cleaned

    def get_summary(self):
        """Get summary of all reports."""
        summary = {}

        for category, directory in [
            ("gex_calculations", self.gex_dir),
            ("pattern_analysis", self.pattern_dir),
            ("data_quality", self.quality_dir),
            ("agent_outputs", self.agent_dir),
            ("demo_results", self.demo_dir),
        ]:
            files = list(directory.glob("*"))
            total_size = sum(f.stat().st_size for f in files if f.is_file())

            summary[category] = {
                "file_count": len(files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "latest": max([f.stat().st_mtime for f in files if f.is_file()], default=0),
            }

        return summary


# Global instance
reports_manager = ReportsManager()
