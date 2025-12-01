"""Unified Reports Manager with Clean Directory Structure.

Organizes reports by purpose:
- experiments/ - All experiment results (YAML format)
- validation/ - Validation and test results
- archive/ - Old reports for reference
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..validation.data_obfuscation import DataObfuscator
from .date_utils import now_iso

logger = logging.getLogger(__name__)


class UnifiedReportsManager:
    """Unified reports manager with clean directory structure.

    All outputs in YAML for token efficiency.
    """

    def __init__(self, base_dir: str = "reports"):
        """Initialize with clean directory structure."""
        self.base_dir = Path(base_dir)

        # Clean, purposeful structure
        self.experiments_dir = self.base_dir / "experiments"
        self.validation_dir = self.base_dir / "validation"
        self.archive_dir = self.base_dir / "archive"

        # Create directories
        for directory in [self.experiments_dir, self.validation_dir, self.archive_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # Data obfuscator for anti-cheating
        self.obfuscator = DataObfuscator()

    def save_experiment(
        self,
        ticker: str,
        date: str,
        test_type: str,
        experiment_description: str,
        tool_plan: Dict,
        experiment_data: Dict,
        llm_analysis: Dict,
        obfuscate: bool = False,
    ) -> Path:
        """Save complete experiment results with full LLM analysis.

        Args:
            ticker: Stock symbol
            date: Trading date
            test_type: Type of test/experiment
            experiment_description: Natural language description
            tool_plan: LLM-generated tool execution plan
            experiment_data: Raw data from tools
            llm_analysis: Complete LLM analysis results
            obfuscate: Whether to obfuscate for anti-cheating

        Returns:
            Path to saved YAML file
        """
        # Clean filename: ticker-date-testtype.yaml
        date_clean = date.split(" ")[0] if " " in date else date
        test_clean = test_type.lower().replace(" ", "_").replace("-", "_")
        filename = f"{ticker}-{date_clean}-{test_clean}.yaml"
        file_path = self.experiments_dir / filename

        # Apply obfuscation if needed
        display_ticker = ticker
        display_date = date
        if obfuscate:
            date_mapping = self.obfuscator.obfuscate_dates([date])
            ticker_mapping = self.obfuscator.obfuscate_tickers([ticker])
            display_date = date_mapping.get(date, date)
            display_ticker = ticker_mapping.get(ticker, ticker)
            experiment_description = self.obfuscator.obfuscate_text_content(experiment_description)

        # Structure the complete output
        output = {
            "metadata": {
                "experiment": {
                    "description": experiment_description,
                    "type": test_type,
                    "ticker": display_ticker,
                    "date": display_date,
                    "obfuscated": obfuscate,
                },
                "test_rationale": self._get_test_rationale(date, test_type),
                "generated_at": now_iso(),
            },
            "tool_execution": {
                "plan": self._extract_tool_plan(tool_plan),
                "data_sources": self._extract_data_sources(experiment_data),
                "execution_time": experiment_data.get("execution_time"),
            },
            "gex_analysis": self._extract_gex_metrics(experiment_data),
            "llm_analysis": {
                "market_mechanics": self._extract_market_mechanics(llm_analysis),
                "key_insights": self._extract_insights(llm_analysis),
                "patterns_detected": self._extract_patterns(llm_analysis),
                "risk_assessment": self._extract_risk(llm_analysis),
                "trading_signal": self._extract_signal(llm_analysis),
                "confidence_reasoning": self._extract_reasoning(llm_analysis),
                "token_usage": llm_analysis.get("token_usage", {}),
            },
            "validation": {
                "data_quality": self._assess_data_quality(experiment_data),
                "analysis_quality": self._assess_analysis_quality(llm_analysis),
            },
        }

        # Clean up None values
        output = self._clean_nulls(output)

        # Save as YAML
        with open(file_path, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False, width=120)

        logger.info(f"Saved experiment to {file_path}")
        return file_path

    def _get_test_rationale(self, date: str, test_type: str) -> Dict:
        """Explain why this date/test was chosen."""
        known_dates = {
            "2024-06-28": {
                "significance": "Q2 2024 end, quarterly expiration",
                "characteristics": "High options volume, rebalancing flows",
                "expected_patterns": "Pin risk around major strikes, gamma concentration",
            },
            "2024-03-15": {
                "significance": "Triple witching day",
                "characteristics": "Simultaneous expiration of index futures, options, and stock options",
                "expected_patterns": "Elevated gamma exposure, volatility compression",
            },
            "2024-01-19": {
                "significance": "Monthly OPEX with VIX expiration",
                "characteristics": "VIX futures and SPX options expiry convergence",
                "expected_patterns": "Volatility regime shifts, correlation breaks",
            },
        }

        date_info = known_dates.get(
            date,
            {
                "significance": "Standard trading day for backtesting",
                "characteristics": "Normal market conditions",
                "expected_patterns": "Typical intraday patterns",
            },
        )

        test_purposes = {
            "gamma_analysis": "Analyze dealer hedging flows and gamma positioning",
            "pattern_detection": "Identify unusual options activity and flow patterns",
            "support_resistance": "Detect options-derived price levels",
            "volatility_regime": "Classify volatility conditions and predict changes",
        }

        return {
            "date_chosen": date_info,
            "test_purpose": test_purposes.get(test_type.replace("-", "_"), "General market analysis"),
            "validation_goal": "Verify LLM analyzes mechanics without relying on memorized events",
        }

    def _extract_tool_plan(self, tool_plan: Dict) -> Dict:
        """Extract structured tool execution plan."""
        if not tool_plan:
            return {}

        return {
            "tools_selected": tool_plan.get("tools_to_use", []),
            "execution_order": tool_plan.get("execution_order", []),
            "rationale": tool_plan.get("rationale", ""),
            "expected_data": tool_plan.get("expected_data_types", []),
        }

    def _extract_data_sources(self, data: Dict) -> Dict:
        """Track data sources without exposing API keys."""
        sources = {}

        if "data_source" in data:
            sources["primary"] = data["data_source"]

        if "api_calls_made" in data:
            sources["api_calls"] = data["api_calls_made"]

        # Determine if cache or live
        if "cache" in str(data).lower():
            sources["type"] = "cached"
        else:
            sources["type"] = "live"

        return sources

    def _extract_gex_metrics(self, data: Dict) -> Dict:
        """Extract key GEX metrics."""
        gex = {}

        if "gex_metrics" in data:
            metrics = data["gex_metrics"]
            gex = {
                "total_gamma": metrics.get("total_gamma"),
                "spot_price": metrics.get("spot_price"),
                "gamma_flip": metrics.get("gamma_flip_point"),
                "max_gamma_strike": metrics.get("max_gamma_strike"),
                "put_call_ratio": metrics.get("put_call_ratio"),
                "gamma_concentration": metrics.get("gamma_concentration"),
                "key_strikes": metrics.get("key_strikes", []),
            }

        return {k: v for k, v in gex.items() if v is not None}

    def _extract_market_mechanics(self, llm_analysis: Dict) -> Dict:
        """Extract WHO/WHOM/WHAT mechanics."""
        # Check for mechanics_interpretation first (actual field name)
        mechanics = llm_analysis.get("mechanics_interpretation", {})
        if not mechanics:
            mechanics = llm_analysis.get("market_mechanics", {})

        if isinstance(mechanics, str):
            # Parse from string format
            return self._parse_mechanics_string(mechanics)
        elif isinstance(mechanics, dict):
            return {
                "who": mechanics.get("who", "Unknown actors"),
                "whom": mechanics.get("whom", "Unknown targets"),
                "what": mechanics.get("what", "Unknown action"),
                "confidence": mechanics.get("confidence", 0),
                "time_horizon": mechanics.get("time_horizon", "Intraday"),
            }
        return {}

    def _parse_mechanics_string(self, text: str) -> Dict:
        """Parse mechanics from text format."""
        mechanics = {"who": "", "whom": "", "what": "", "confidence": 0}

        for key in ["WHO", "WHOM", "WHAT"]:
            if f"{key}:" in text:
                start = text.find(f"{key}:") + len(f"{key}:")
                # Find next keyword or end
                end = len(text)
                for next_key in ["WHO", "WHOM", "WHAT", "CONFIDENCE"]:
                    next_pos = text.find(f"{next_key}:", start)
                    if next_pos > start:
                        end = min(end, next_pos)
                mechanics[key.lower()] = text[start:end].strip()

        if "CONFIDENCE:" in text:
            conf_text = text.split("CONFIDENCE:")[1].split("%")[0].strip()
            try:
                mechanics["confidence"] = int(conf_text)
            except:
                pass

        return mechanics

    def _extract_insights(self, llm_analysis: Dict) -> list:
        """Extract key insights as a list."""
        insights = llm_analysis.get("key_insights", [])
        if isinstance(insights, str):
            # Split by bullets or newlines
            insights = [i.strip() for i in insights.split("\n") if i.strip()]
        elif isinstance(insights, dict):
            insights = list(insights.values())
        return insights[:5]  # Limit to top 5

    def _extract_patterns(self, llm_analysis: Dict) -> list:
        """Extract detected patterns."""
        patterns = llm_analysis.get("patterns_detected", [])
        if not isinstance(patterns, list):
            patterns = [patterns] if patterns else []
        return patterns

    def _extract_risk(self, llm_analysis: Dict) -> Dict:
        """Extract risk assessment."""
        risk = llm_analysis.get("risk_assessment", {})
        if isinstance(risk, str):
            return {"summary": risk}
        return risk

    def _extract_signal(self, llm_analysis: Dict) -> Dict:
        """Extract trading signal."""
        signal = llm_analysis.get("actionable_signal", {})
        if not signal:
            signal = llm_analysis.get("trading_signal", {})
        return {
            "action": signal.get("action", "HOLD"),
            "confidence": signal.get("confidence", 0),
            "rationale": signal.get("rationale", ""),
            "risk_reward": signal.get("risk_reward", ""),
            "edge_quality": signal.get("edge_quality", ""),
        }

    def _extract_reasoning(self, llm_analysis: Dict) -> Dict:
        """Extract confidence reasoning components."""
        reasoning = llm_analysis.get("reasoning", "")
        if isinstance(reasoning, str):
            return {"summary": reasoning[:500] if reasoning else ""}
        return reasoning

    def _assess_data_quality(self, data: Dict) -> Dict:
        """Assess quality of input data."""
        quality = {}

        if "options_data" in data:
            options = data["options_data"]
            if isinstance(options, dict):
                quality["options_contracts"] = options.get("contract_count", 0)
                quality["volume_quality"] = "good" if options.get("total_volume", 0) > 1000 else "low"

        quality["data_completeness"] = "complete" if data else "incomplete"

        return quality

    def _assess_analysis_quality(self, llm_analysis: Dict) -> Dict:
        """Assess quality of LLM analysis."""
        quality = {}

        # Check if key components are present (use actual field names)
        has_mechanics = bool(llm_analysis.get("mechanics_interpretation"))
        has_patterns = bool(llm_analysis.get("patterns_detected"))

        # Only count as having signal if it's not empty/None
        signal = llm_analysis.get("actionable_signal", {})
        has_signal = bool(signal and signal.get("action") is not None)

        quality["completeness"] = sum([has_mechanics, has_patterns, has_signal]) / 3.0

        # Get confidence from mechanics_interpretation
        mechanics = llm_analysis.get("mechanics_interpretation", {})
        quality["confidence"] = mechanics.get("confidence", 0) if mechanics else 0

        return quality

    def _clean_nulls(self, obj):
        """Recursively remove None values and empty dicts/lists."""
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                cleaned_v = self._clean_nulls(v)
                if cleaned_v is not None and cleaned_v != {} and cleaned_v != []:
                    cleaned[k] = cleaned_v
            return cleaned
        elif isinstance(obj, list):
            return [self._clean_nulls(item) for item in obj if self._clean_nulls(item) is not None]
        else:
            return obj

    def archive_old_reports(self, days_old: int = 30):
        """Move old reports to archive."""
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=days_old)

        for file in self.experiments_dir.glob("*.yaml"):
            if file.stat().st_mtime < cutoff.timestamp():
                archive_path = self.archive_dir / file.name
                file.rename(archive_path)
                logger.info(f"Archived {file.name}")

    def list_experiments(self, limit: int = 10) -> list:
        """List recent experiments."""
        files = sorted(self.experiments_dir.glob("*.yaml"), key=lambda x: x.stat().st_mtime, reverse=True)
        return files[:limit]

    # ===========================
    # Additional Methods for Backward Compatibility
    # ===========================

    def save_gex_results(
        self, symbol: str, results: Dict[Any, Any], trading_date: str = None, is_demo: bool = False
    ) -> Path:
        """Save GEX calculation results (backward compatibility method).

        Args:
            symbol: Stock symbol
            results: GEX results dictionary
            trading_date: Trading date
            is_demo: Whether this is demo/test data
        """
        if not trading_date:
            trading_date = now_iso().split("T")[0]

        filename = f"{symbol}-{trading_date}-gex_results.yaml"
        file_path = self.validation_dir / filename

        output = {
            "metadata": {"symbol": symbol, "date": trading_date, "is_demo": is_demo, "generated_at": now_iso()},
            "gex_metrics": results.get("metrics", {}),
            "calculation_method": results.get("calculation_method", "unknown"),
            "contracts_analyzed": results.get("contracts_analyzed", 0),
        }

        with open(file_path, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved GEX results to {file_path}")
        return file_path

    def save_pattern_analysis(
        self, pattern_type: str, results: Dict[Any, Any], symbol: str = None, is_demo: bool = False
    ) -> Path:
        """Save pattern analysis results (backward compatibility method).

        Args:
            pattern_type: Type of pattern analyzed
            results: Analysis results
            symbol: Stock symbol
            is_demo: Whether this is demo/test data
        """
        timestamp = now_iso().split("T")[0]
        symbol_part = f"{symbol}-" if symbol else ""
        filename = f"{symbol_part}{pattern_type}-{timestamp}.yaml"
        file_path = self.validation_dir / filename

        output = {
            "metadata": {"pattern_type": pattern_type, "symbol": symbol, "is_demo": is_demo, "generated_at": now_iso()},
            "analysis": results,
        }

        with open(file_path, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved pattern analysis to {file_path}")
        return file_path

    def save_analysis_results(
        self, symbol: str, results: Dict[Any, Any], trading_date: str, analysis_type: str = "general"
    ) -> Path:
        """Save generic analysis results (backward compatibility method).

        Args:
            symbol: Stock symbol
            results: Analysis results
            trading_date: Trading date
            analysis_type: Type of analysis performed
        """
        filename = f"{symbol}-{trading_date}-{analysis_type}.yaml"
        file_path = self.validation_dir / filename

        output = {
            "metadata": {
                "symbol": symbol,
                "date": trading_date,
                "analysis_type": analysis_type,
                "generated_at": now_iso(),
            },
            "results": results,
        }

        with open(file_path, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved analysis results to {file_path}")
        return file_path

    def save_agent_conversation(
        self, agent_names: list, messages: list, final_result: Any = None, context: Dict = None
    ) -> Path:
        """Save agent conversation logs (backward compatibility method).

        Args:
            agent_names: List of participating agents
            messages: Conversation messages
            final_result: Final result from conversation
            context: Additional context
        """
        timestamp = now_iso().replace(":", "-").split("T")
        filename = f"agent_conversation-{timestamp[0]}-{timestamp[1][:5]}.yaml"
        file_path = self.validation_dir / "agent_logs" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        output = {
            "metadata": {"agents": agent_names, "message_count": len(messages), "generated_at": now_iso()},
            "context": context or {},
            "conversation": messages,
            "final_result": final_result,
        }

        with open(file_path, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False, width=120)

        logger.info(f"Saved agent conversation to {file_path}")
        return file_path

    def filter_strike_data(self, gex_data: Dict, min_volume: int = 0, min_oi: int = 1) -> Dict:
        """Filter strike data by volume and open interest (utility method).

        Args:
            gex_data: GEX data dictionary
            min_volume: Minimum volume threshold
            min_oi: Minimum open interest threshold

        Returns:
            Filtered GEX data
        """
        if not gex_data or "strikes" not in gex_data:
            return gex_data

        filtered_strikes = []
        for strike in gex_data.get("strikes", []):
            volume = strike.get("volume", 0)
            oi = strike.get("open_interest", 0)

            if volume >= min_volume and oi >= min_oi:
                filtered_strikes.append(strike)

        filtered_data = gex_data.copy()
        filtered_data["strikes"] = filtered_strikes
        filtered_data["filtered_count"] = len(filtered_strikes)
        filtered_data["original_count"] = len(gex_data.get("strikes", []))

        return filtered_data

    def cleanup_old_results(self, older_than_days: int = 30) -> int:
        """Move old results to archive (backward compatibility for cleanup_old_results).

        Args:
            older_than_days: Age threshold in days

        Returns:
            Number of files archived
        """
        self.archive_old_reports(days_old=older_than_days)

        # Count archived files
        archived_count = len(list(self.archive_dir.glob("*.yaml")))
        return archived_count

    def get_summary(self) -> Dict:
        """Get summary of all reports (backward compatibility method).

        Returns:
            Dictionary with report counts and stats
        """
        return {
            "experiments": {
                "count": len(list(self.experiments_dir.glob("*.yaml"))),
                "recent": [f.name for f in self.list_experiments(limit=5)],
            },
            "validation": {"count": len(list(self.validation_dir.glob("*.yaml")))},
            "archived": {"count": len(list(self.archive_dir.glob("*.yaml")))},
            "total_reports": (
                len(list(self.experiments_dir.glob("*.yaml"))) + len(list(self.validation_dir.glob("*.yaml")))
            ),
        }


# Global instance
unified_reports = UnifiedReportsManager()

# Backward compatibility aliases
reports_manager = unified_reports  # Alias for old imports from reports_manager.py
yaml_reports = unified_reports  # Alias for old imports from yaml_reports_manager.py
