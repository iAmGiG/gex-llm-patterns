"""YAML Reports Manager for GEX-LLM Analysis Outputs.

⚠️ DEPRECATED: This module is deprecated in favor of unified_reports_manager.py
Please update your imports to:
    from src.utils.unified_reports_manager import yaml_reports

This file is maintained for backward compatibility only.
New code should use UnifiedReportsManager which provides:
- Cleaner directory structure (experiments/, validation/, archive/)
- Better organization by experiment type
- All methods from this class are available via backward compatibility wrappers
- Same YAML format and obfuscation support

Legacy code using this import will continue to work through global alias.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..validation.data_obfuscation import DataObfuscator
from .date_utils import now_iso

logger = logging.getLogger(__name__)


class YAMLReportsManager:
    """Manages analysis outputs in YAML format with obfuscation support.

    Key improvements:
    - YAML format for token efficiency
    - Simplified filenames: ticker-date-testtype.yaml
    - Structured LLM analysis output
    - Data obfuscation integration
    - API source tracking
    """

    def __init__(self, base_dir: str = "reports"):
        """Initialize YAML reports manager."""
        self.base_dir = Path(base_dir)
        self.yaml_dir = self.base_dir / "yaml_outputs"
        self.yaml_dir.mkdir(parents=True, exist_ok=True)

        # Initialize obfuscator for anti-cheating
        self.obfuscator = DataObfuscator()

    def _create_filename(self, ticker: str, date: str, test_type: str) -> str:
        """
        Create clean filename: ticker-date-testtype.yaml

        Args:
            ticker: Stock symbol
            date: Trading date (YYYY-MM-DD)
            test_type: Type of test/analysis

        Returns:
            Clean filename string
        """
        # Remove time components if present
        if " " in date:
            date = date.split(" ")[0]

        # Clean test type (remove spaces, special chars)
        test_type_clean = test_type.lower().replace(" ", "_").replace("-", "_")

        return f"{ticker}-{date}-{test_type_clean}.yaml"

    def save_experiment_results(
        self,
        ticker: str,
        date: str,
        test_type: str,
        experiment_description: str,
        results: Dict,
        obfuscate: bool = False,
    ) -> Path:
        """Save experiment results in structured YAML format.

        Args:
            ticker: Stock symbol
            date: Trading date
            test_type: Type of experiment
            experiment_description: Natural language description
            results: Experiment results dictionary
            obfuscate: Whether to obfuscate temporal/ticker references

        Returns:
            Path to saved YAML file
        """
        filename = self._create_filename(ticker, date, test_type)
        file_path = self.yaml_dir / filename

        # Apply obfuscation if requested
        display_ticker = ticker
        display_date = date
        if obfuscate:
            date_mapping = self.obfuscator.obfuscate_dates([date])
            ticker_mapping = self.obfuscator.obfuscate_tickers([ticker])
            display_date = date_mapping.get(date, date)
            display_ticker = ticker_mapping.get(ticker, ticker)
            experiment_description = self.obfuscator.obfuscate_text_content(experiment_description)

        # Structure the output
        output = {
            "metadata": {
                "test_type": test_type,
                "ticker": display_ticker,
                "date": display_date,
                "original_ticker": ticker if obfuscate else None,
                "original_date": date if obfuscate else None,
                "description": experiment_description,
                "generated_at": now_iso(),
                "obfuscated": obfuscate,
                "test_rationale": self._get_test_rationale(date, test_type),
            },
            "data_sources": self._extract_data_sources(results),
            "gex_metrics": self._extract_gex_metrics(results),
            "llm_analysis": self._structure_llm_analysis(results),
            "trading_signal": self._extract_trading_signal(results),
            "patterns_detected": self._extract_patterns(results),
            "performance": self._extract_performance_metrics(results),
        }

        # Remove None values for cleaner output
        output = self._clean_output(output)

        # Save as YAML
        with open(file_path, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False, width=120)

        logger.info(f"Saved YAML report to {file_path}")
        return file_path

    def _get_test_rationale(self, date: str, test_type: str) -> Dict[str, str]:
        """Explain why this date/test combination was chosen.

        Args:
            date: Trading date
            test_type: Type of test

        Returns:
            Dictionary with test rationale
        """
        # Common test dates and their significance
        known_dates = {
            "2024-06-28": "End of Q2 2024, quarterly expiration, high options volume",
            "2024-03-15": "Triple witching day, high gamma exposure expected",
            "2024-01-19": "Monthly OPEX, VIX expiration convergence",
            "2023-12-15": "Year-end positioning, tax loss harvesting effects",
        }

        return {
            "date_significance": known_dates.get(date, "Random historical date for backtesting"),
            "test_purpose": self._get_test_purpose(test_type),
            "validation_goal": "Verify LLM can identify market mechanics without temporal context",
        }

    def _get_test_purpose(self, test_type: str) -> str:
        """Map test type to its purpose."""
        purposes = {
            "gamma_analysis": "Analyze dealer hedging dynamics and strike-level gamma exposure",
            "pattern_detection": "Identify recurring market microstructure patterns",
            "support_resistance": "Detect options-derived support and resistance levels",
            "flow_analysis": "Track smart money positioning through options flow",
            "volatility_regime": "Classify current volatility regime and predict changes",
        }

        test_key = test_type.lower().replace("-", "_").replace(" ", "_")
        for key, purpose in purposes.items():
            if key in test_key:
                return purpose

        return "General market mechanics analysis and validation"

    def _extract_data_sources(self, results: Dict) -> Dict[str, Any]:
        """Extract and structure data source information."""
        sources = {}

        if "data_source" in results:
            sources["primary"] = results["data_source"]

        if "options_data" in results and isinstance(results["options_data"], dict):
            if "source" in results["options_data"]:
                sources["options"] = results["options_data"]["source"]
            elif "status" in results["options_data"]:
                sources["options"] = results["options_data"].get("source", "cache")

        # Track API usage without exposing keys
        if "api_calls" in results:
            sources["api_calls"] = results["api_calls"]

        # Add cache vs live tracking
        sources["data_freshness"] = "cached" if "cache" in str(sources).lower() else "live"

        return sources

    def _extract_gex_metrics(self, results: Dict) -> Dict[str, Any]:
        """Extract key GEX metrics."""
        metrics = {}

        if "gex_analysis" in results:
            gex = results["gex_analysis"]
            if isinstance(gex, dict):
                metrics = {
                    "total_gex": gex.get("total_gex"),
                    "spot_price": gex.get("spot_price"),
                    "gamma_flip": gex.get("gamma_flip"),
                    "max_gamma_strike": gex.get("max_gamma_strike"),
                    "put_call_ratio": gex.get("put_call_ratio"),
                }

        return {k: v for k, v in metrics.items() if v is not None}

    def _structure_llm_analysis(self, results: Dict) -> Dict[str, Any]:
        """Structure LLM analysis into clear components.

        Breaks down the messy reasoning line into structured fields.
        """
        analysis = {}

        if "llm_analysis" in results:
            llm = results["llm_analysis"]

            if isinstance(llm, dict):
                # Extract WHO/WHOM/WHAT mechanics
                if "market_mechanics" in llm:
                    mechanics = llm["market_mechanics"]
                    if isinstance(mechanics, dict):
                        analysis["market_mechanics"] = {
                            "who": mechanics.get("who", "Unknown actors"),
                            "whom": mechanics.get("whom", "Unknown targets"),
                            "what": mechanics.get("what", "Unknown action"),
                            "confidence": mechanics.get("confidence", 0),
                        }
                    elif isinstance(mechanics, str):
                        # Parse from string if needed
                        analysis["market_mechanics"] = self._parse_mechanics_string(mechanics)

                # Extract key insights
                if "key_insights" in llm:
                    analysis["key_insights"] = llm["key_insights"]
                elif "insights" in llm:
                    analysis["key_insights"] = llm["insights"]

                # Extract reasoning components
                if "reasoning" in llm:
                    reasoning = llm["reasoning"]
                    if isinstance(reasoning, str):
                        # Break down complex reasoning string
                        analysis["reasoning"] = self._parse_reasoning_components(reasoning)
                    else:
                        analysis["reasoning"] = reasoning

                # Extract risk assessment
                if "risk_assessment" in llm:
                    analysis["risk_assessment"] = llm["risk_assessment"]

                # Token usage
                if "token_usage" in llm:
                    analysis["token_usage"] = llm["token_usage"]

        return analysis

    def _parse_mechanics_string(self, mechanics_str: str) -> Dict[str, str]:
        """Parse WHO/WHOM/WHAT from string format."""
        result = {"who": "Unknown", "whom": "Unknown", "what": "Unknown", "confidence": 0}

        if "WHO:" in mechanics_str:
            parts = mechanics_str.split("WHO:")
            if len(parts) > 1:
                who_part = parts[1].split("WHOM:")[0] if "WHOM:" in parts[1] else parts[1]
                result["who"] = who_part.strip()

        if "WHOM:" in mechanics_str:
            parts = mechanics_str.split("WHOM:")
            if len(parts) > 1:
                whom_part = parts[1].split("WHAT:")[0] if "WHAT:" in parts[1] else parts[1]
                result["whom"] = whom_part.strip()

        if "WHAT:" in mechanics_str:
            parts = mechanics_str.split("WHAT:")
            if len(parts) > 1:
                what_part = parts[1].split("CONFIDENCE:")[0] if "CONFIDENCE:" in parts[1] else parts[1]
                result["what"] = what_part.strip()

        if "CONFIDENCE:" in mechanics_str:
            parts = mechanics_str.split("CONFIDENCE:")
            if len(parts) > 1:
                try:
                    conf_str = parts[1].strip().rstrip("%")
                    result["confidence"] = int(conf_str)
                except:
                    pass

        return result

    def _parse_reasoning_components(self, reasoning: str) -> Dict[str, Any]:
        """Break down complex reasoning into components."""
        components = {
            "data_quality": None,
            "pattern_significance": None,
            "market_regime": None,
            "edge_detection": None,
            "confidence_factors": [],
        }

        # Extract different reasoning aspects
        reasoning_lower = reasoning.lower()

        if "data quality" in reasoning_lower or "volume" in reasoning_lower:
            components["data_quality"] = "Sufficient volume and OI for analysis"

        if "pattern" in reasoning_lower:
            components["pattern_significance"] = "Patterns detected in strike distribution"

        if "bullish" in reasoning_lower:
            components["market_regime"] = "Bullish"
        elif "bearish" in reasoning_lower:
            components["market_regime"] = "Bearish"
        elif "neutral" in reasoning_lower:
            components["market_regime"] = "Neutral"

        if "edge" in reasoning_lower or "opportunity" in reasoning_lower:
            components["edge_detection"] = "Potential edge identified"

        return {k: v for k, v in components.items() if v is not None}

    def _extract_trading_signal(self, results: Dict) -> Dict[str, Any]:
        """Extract trading signal information."""
        signal = {}

        if "trading_signal" in results:
            sig = results["trading_signal"]
            if isinstance(sig, dict):
                signal = {
                    "action": sig.get("action", "HOLD"),
                    "confidence": sig.get("confidence", 0),
                    "rationale": sig.get("rationale", "No clear edge detected"),
                    "risk_level": sig.get("risk_level", "Medium"),
                }

        return signal

    def _extract_patterns(self, results: Dict) -> List[Dict[str, Any]]:
        """Extract detected patterns."""
        patterns = []

        if "patterns" in results:
            pattern_data = results["patterns"]
            if isinstance(pattern_data, list):
                for pattern in pattern_data:
                    if isinstance(pattern, dict):
                        patterns.append(
                            {
                                "type": pattern.get("type"),
                                "strike": pattern.get("strike"),
                                "strength": pattern.get("strength"),
                                "description": pattern.get("description"),
                            }
                        )

        return patterns if patterns else None

    def _extract_performance_metrics(self, results: Dict) -> Dict[str, Any]:
        """Extract performance and timing metrics."""
        metrics = {}

        if "performance" in results:
            perf = results["performance"]
            if isinstance(perf, dict):
                metrics = {
                    "execution_time": perf.get("execution_time"),
                    "cache_hits": perf.get("cache_hits"),
                    "api_calls": perf.get("api_calls"),
                }

        if "timestamp" in results:
            metrics["completed_at"] = results["timestamp"]

        return {k: v for k, v in metrics.items() if v is not None}

    def _clean_output(self, output: Dict) -> Dict:
        """Remove None values and empty sections."""
        cleaned = {}

        for key, value in output.items():
            if value is not None:
                if isinstance(value, dict):
                    cleaned_dict = self._clean_output(value)
                    if cleaned_dict:
                        cleaned[key] = cleaned_dict
                elif isinstance(value, list) and value:
                    cleaned[key] = value
                elif not isinstance(value, (dict, list)):
                    cleaned[key] = value

        return cleaned

    def load_yaml_report(self, filepath: Path) -> Dict:
        """Load a YAML report."""
        with open(filepath, "r") as f:
            return yaml.safe_load(f)

    def list_yaml_reports(self) -> List[Path]:
        """List all YAML reports."""
        return sorted(self.yaml_dir.glob("*.yaml"))


# Global instance
yaml_reports_manager = YAMLReportsManager()
