"""
Market Mechanics Agent - Single Agent Architecture
Implements Issue #50: LLM as Market Mechanics Interpreter

Core hypothesis: LLM identifies WHO is forcing WHOM to do WHAT in market mechanics
"""

import datetime
import os
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

from src.analysis.actionable_patterns import ActionablePatternDetector
from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager
from gex_db_infrastructure.cache.unified_cache import UnifiedCacheManager
from gex_db_infrastructure.gex.enhanced_pattern_detector import EnhancedPatternDetector
from gex_db_infrastructure.gex.gex_calculator import GEXCalculator
from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder
from src.utils.date_utils import add_business_days, is_opex_week, now_iso, parse_date_string
from src.utils.unified_reports_manager import unified_reports

logger = logging.getLogger(__name__)

# Import autogen_tools at module level with fallback
try:
    from src.tools.autogen_tools import calculate_gamma_exposure, fetch_market_data, fetch_options_data

    AUTOGEN_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AutoGen tools not available: {e}")
    AUTOGEN_TOOLS_AVAILABLE = False


class MarketMechanicsAgent:
    """Single agent that interprets market mechanics from GEX data.

    Focus: WHO is forcing WHOM to do WHAT
    """

    def __init__(self, symbol: str = "SPY", llm_provider: Optional[object] = None, config: Optional[Dict] = None):
        """Initialize the Market Mechanics Agent.

        Args:
            symbol: Trading symbol to analyze
            llm_provider: LLM integration (OpenAI, Claude, etc.)
            config: Configuration dictionary (loads from file if None)
        """
        self.symbol = symbol
        self.config = config or self._load_config()
        self.gex_thresholds = self.config.get("gex_thresholds", {})
        self.strike_pattern_config = self.config.get("strike_level_patterns", {})
        self.prompt_templates = self._load_prompt_templates()
        self.cache = UnifiedCacheManager()
        # Use PostgreSQL by default (migrated from SQLite)
        self.db = PostgreSQLOptionsManager()
        self.pattern_detector = EnhancedPatternDetector()
        self.gex_calculator = GEXCalculator()
        self.prompt_builder = MechanicsPromptBuilder()

        # Initialize pattern library (Issue #54)
        try:
            from analysis.pattern_library import PatternLibrary

            self.pattern_library = PatternLibrary()
            logger.info("Initialized Pattern Library with comprehensive patterns")
        except ImportError as e:
            logger.warning(f"Pattern Library not available: {e}")
            self.pattern_library = None

        # Initialize actionable pattern detector (Issue #77)
        self.actionable_detector = ActionablePatternDetector(config=config)

        # Auto-initialize LLM if not provided
        if llm_provider is None:
            # Use AutoGen for consistency with base_agent architecture
            try:
                from src.llm.autogen_market_mechanics import AutoGenMarketMechanics

                self.llm = AutoGenMarketMechanics()
                logger.info("Initialized AutoGen LLM for mechanics interpretation")
            except Exception as e:
                logger.warning(f"Could not initialize AutoGen LLM: {e}")
                self.llm = None
        else:
            self.llm = llm_provider

        # Market mechanics patterns library
        # Use PatternLibrary (src/analysis/) instead of hardcoded patterns
        if self.pattern_library:
            self.mechanics_patterns = self._build_mechanics_dict_from_library()
            logger.info(f"Loaded {len(self.mechanics_patterns)} patterns from PatternLibrary")
        else:
            # Fallback to minimal hardcoded patterns (shouldn't happen)
            logger.warning("PatternLibrary not available, using minimal fallback")
            self.mechanics_patterns = {
                "gamma_squeeze": {
                    "description": "Positive feedback loop forcing dealers to chase price",
                    "indicators": ["positive_gamma_high", "accelerating_delta_hedging"],
                    "who": "Options flow",
                    "whom": "Dealers",
                    "what": "Forced to buy high/sell low amplifying moves",
                }
            }

    def _load_config(self) -> Dict:
        """Load configuration from analysis_config.yaml."""
        try:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config_defaults" / "analysis_config.yaml"

            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}. Using defaults.")
            return {
                "gex_thresholds": {
                    "positive_high": 5e9,
                    "negative_high": -5e9,
                    "gamma_concentration_threshold": 0.7,
                    "high_volume_threshold": 1e6,
                    "significant_flow_threshold": 5e5,
                }
            }

    def _load_prompt_templates(self) -> Dict:
        """Load LLM prompt templates from llm_prompts.yaml (agent_prompts section)."""
        try:
            base_dir = Path(__file__).parent.parent.parent
            templates_path = base_dir / "config_defaults" / "llm_prompts.yaml"

            with open(templates_path, "r") as f:
                config = yaml.safe_load(f)
                templates = config.get("agent_prompts", {})
                if templates:
                    logger.info("Loaded agent prompt templates from llm_prompts.yaml")
                else:
                    logger.warning("No agent_prompts section found in llm_prompts.yaml")
                return templates
        except Exception as e:
            logger.warning(f"Failed to load prompt templates: {e}. Using inline defaults.")
            return {}

    def _build_mechanics_dict_from_library(self) -> Dict:
        """Convert PatternLibrary patterns to mechanics dict format.

        Bridges between comprehensive PatternLibrary and simplified mechanics dict.
        """
        mechanics = {}
        for name, pattern in self.pattern_library.patterns.items():
            mechanics[name] = {
                "description": pattern.mechanics_description,
                "who": pattern.who,
                "whom": pattern.whom,
                "what": pattern.what,
                "indicators": pattern.identification_criteria,
            }
        return mechanics

    def _normalize_date(self, date) -> tuple[datetime.datetime, str]:
        """Normalize date input to (datetime_obj, date_string) tuple.

        Supports both daily dates ('2024-01-15') and intra-day timestamps ('2024-01-15 15:30:00'). For intra-day
        timestamps, preserves the full timestamp format.
        """
        if isinstance(date, str):
            try:
                # Use date_utils for parsing (handles obfuscated dates too)
                date_obj = parse_date_string(date)
                date_str = date  # Preserve original format
            except ValueError:
                # Try parsing other common formats
                try:
                    date_obj = pd.to_datetime(date).to_pydatetime()
                    # Determine if this has time component
                    if date_obj.hour != 0 or date_obj.minute != 0 or date_obj.second != 0:
                        date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        date_str = date_obj.strftime("%Y-%m-%d")
                except Exception:
                    raise ValueError(f"Unable to parse date: {date}")
        elif hasattr(date, "strftime"):
            date_obj = date
            # Determine if this has time component
            if date_obj.hour != 0 or date_obj.minute != 0 or date_obj.second != 0:
                date_str = date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = date.strftime("%Y-%m-%d")
        elif hasattr(date, "to_pydatetime"):
            date_obj = date.to_pydatetime()
            # Determine if this has time component
            if date_obj.hour != 0 or date_obj.minute != 0 or date_obj.second != 0:
                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = date_obj.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"Unsupported date type: {type(date)}")

        return date_obj, date_str

    def _normalize_gex_results(self, gex_profile: Dict, spot_price: float) -> Dict:
        """Normalize GEX results to consistent structure regardless of source."""
        return {
            "net_gex": gex_profile.get("net_gex", 0),
            "flip_point": gex_profile.get("flip_point", spot_price),
            "spot_price": spot_price,
            "gex_by_strike": gex_profile.get("gex_by_strike", {}),
            # Ensure these fields exist for downstream compatibility
            "total_gamma": gex_profile.get("total_gamma", 0),
            "gamma_concentration": gex_profile.get("gamma_concentration", {}),
            "max_strike": gex_profile.get("max_strike", spot_price),
        }

    def _generate_pattern_insights(self, pattern_matches: List[Dict]) -> List[str]:
        """Generate insights from pattern library matches."""
        insights = []

        for match in pattern_matches[:3]:  # Top 3 patterns
            pattern = match.get("pattern")
            if pattern and hasattr(pattern, "mechanics_description"):
                insight = f"{match['pattern_name']}: {pattern.mechanics_description}"
                insights.append(insight)
            elif isinstance(pattern, dict):
                insight = f"{match['pattern_name']}: Confidence {match['confidence']:.0%}"
                insights.append(insight)

        return insights

    def run_experiment(self, experiment_description: str, date: str = "2024-06-28", obfuscate: bool = False) -> Dict:
        """Run flexible experiment based on natural language description. Agent decides what tools to call and how to
        analyze.

        Args:
            experiment_description: Natural language experiment request
            date: Date for analysis
            obfuscate: If True, strip dates/tickers from LLM prompts (anti-cheating validation)

        Returns:
            Experiment results with agent's analysis
        """
        logger.info(f"Running experiment: {experiment_description}")
        if obfuscate:
            logger.info("Obfuscation ENABLED - LLM will not see real dates/tickers")

        try:
            # Step 0: Obfuscate dates/tickers if requested (BEFORE LLM calls)
            if obfuscate:
                from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator

                obfuscator = DataObfuscator()
                date_mapping = obfuscator.obfuscate_dates([date])
                ticker_mapping = obfuscator.obfuscate_tickers([self.symbol])

                obfuscated_date = date_mapping[date]
                obfuscated_ticker = ticker_mapping[self.symbol]

                # Replace date and ticker in experiment description
                experiment_description_llm = experiment_description.replace(date, obfuscated_date)
                experiment_description_llm = experiment_description_llm.replace(self.symbol, obfuscated_ticker)
                date_for_llm = obfuscated_date

                logger.info(f"Obfuscated: {date} → {obfuscated_date}, {self.symbol} → {obfuscated_ticker}")
            else:
                experiment_description_llm = experiment_description
                date_for_llm = date
                obfuscated_date = None
                obfuscated_ticker = None

            # Step 1: Use LLM to analyze experiment and decide what tools/data are needed
            # Pass obfuscated description and date to LLM
            tool_plan = self._plan_experiment_tools(experiment_description_llm, date_for_llm)
            logger.info(f"Agent tool plan: {tool_plan}")

            # Step 2: Execute the planned tools based on LLM decision
            # Use REAL date for data fetching (cache needs real dates)
            experiment_data = self._execute_tool_plan(tool_plan, date)

            # Step 3: Use LLM to analyze results and generate insights
            # Pass obfuscated description to LLM
            result = self._analyze_experiment_results(experiment_description_llm, experiment_data, tool_plan)

            # Step 4: Add pattern library analysis (Issue #54)
            if self.pattern_library and experiment_data:
                try:
                    pattern_matches = self.pattern_library.match_patterns(experiment_data)
                    if pattern_matches:
                        result["pattern_library_analysis"] = {
                            "detected_patterns": [
                                {
                                    "pattern": match["pattern_name"],
                                    "confidence": match["confidence"],
                                    "category": match["category"],
                                }
                                # Top 3 matches
                                for match in pattern_matches[:3]
                            ],
                            "mechanics_insights": self._generate_pattern_insights(pattern_matches),
                        }
                        logger.info(f"Pattern library detected {len(pattern_matches)} potential patterns")
                except Exception as e:
                    logger.warning(f"Pattern library analysis failed: {e}")

            # Add experiment metadata
            result["experiment_description"] = experiment_description
            result["experiment_timestamp"] = now_iso()
            result["agent_used"] = "MarketMechanicsAgent"
            result["tool_plan"] = tool_plan

            # Add obfuscation metadata if used
            if obfuscate:
                result["obfuscation_metadata"] = {
                    "obfuscated": True,
                    "real_date": date,
                    "obfuscated_date": obfuscated_date,
                    "real_ticker": self.symbol,
                    "obfuscated_ticker": obfuscated_ticker,
                }
                logger.info("Obfuscation metadata added to result")

            # Save full experiment report with unified reports manager
            test_type = tool_plan.get("experiment_type", "general_analysis")
            try:
                report_path = unified_reports.save_experiment(
                    ticker=self.symbol,
                    date=date,
                    test_type=test_type,
                    experiment_description=experiment_description,
                    tool_plan=tool_plan,
                    experiment_data=experiment_data,
                    llm_analysis=result,
                    obfuscate=True,  # Default to obfuscation for anti-cheating
                )
                logger.info(f"Saved full report to {report_path}")
                result["report_path"] = str(report_path)
            except Exception as e:
                logger.warning(f"Could not save report: {e}")

            logger.info(f"Experiment completed: {result.get('experiment_type')}")
            return result

        except Exception as e:
            logger.error(f"Experiment failed: {e}")
            return {
                "status": "error",
                "experiment_description": experiment_description,
                "error": str(e),
                "experiment_timestamp": now_iso(),
            }

    def run_batch_experiments(
        self, dates: List[str], experiment_template: str = None, use_obfuscation: bool = True
    ) -> Dict:
        """Run experiments on multiple dates in a single LLM call for better pattern recognition.

        Args:
            dates: List of dates to analyze
            experiment_template: Template for experiment description
            use_obfuscation: Whether to obfuscate dates/tickers to prevent LLM cheating

        Returns:
            Dictionary with batch analysis results
        """
        try:
            from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator

            # Prepare data for all dates first
            batch_data = {}
            obfuscator = DataObfuscator() if use_obfuscation else None

            # Obfuscate dates if needed
            if obfuscator:
                date_mapping = obfuscator.obfuscate_dates(dates)
                ticker_mapping = obfuscator.obfuscate_tickers([self.symbol])
                display_symbol = ticker_mapping[self.symbol]
            else:
                date_mapping = {d: d for d in dates}
                display_symbol = self.symbol

            # Collect data for all dates
            for date in dates:
                try:
                    # Fetch options and calculate GEX
                    options_data = self._fetch_options_data(date)
                    if options_data is not None and not options_data.empty:
                        # Get spot price for GEX calculation
                        spot_price = (
                            options_data["underlyingPrice"].iloc[0]
                            if "underlyingPrice" in options_data.columns
                            else 450.0
                        )

                        # Calculate GEX - returns DataFrame with per-strike GEX
                        gex_df = self.gex_calculator.calculate_dealer_gamma_exposure(
                            options_data, underlying_price=spot_price
                        )

                        # Aggregate to summary metrics
                        if not gex_df.empty and "dealer_gex" in gex_df.columns:
                            total_gex = gex_df["dealer_gex"].sum()
                            call_gex = (
                                gex_df[gex_df["type"] == "call"]["dealer_gex"].sum() if "type" in gex_df.columns else 0
                            )
                            put_gex = (
                                gex_df[gex_df["type"] == "put"]["dealer_gex"].sum() if "type" in gex_df.columns else 0
                            )

                            # Find gamma flip point (where GEX changes sign)
                            gex_by_strike = gex_df.groupby("strike")["dealer_gex"].sum()
                            flip_point = (
                                gex_by_strike[gex_by_strike >= 0].index.min()
                                if len(gex_by_strike[gex_by_strike >= 0]) > 0
                                else spot_price
                            )

                            gex_metrics = {
                                "total_gamma": total_gex,
                                "net_gex": total_gex,
                                "call_gamma": call_gex,
                                "put_gamma": put_gex,
                                "spot_price": spot_price,
                                "flip_point": flip_point,
                                "regime": "POSITIVE_GAMMA" if total_gex > 0 else "NEGATIVE_GAMMA",
                            }
                        else:
                            # Fallback if GEX calculation failed
                            gex_metrics = {
                                "total_gamma": 0,
                                "net_gex": 0,
                                "spot_price": spot_price,
                                "flip_point": spot_price,
                                "regime": "Unknown",
                            }

                        # Detect patterns
                        patterns = (
                            self.pattern_detector.detect_all_patterns(gex_metrics, {}, fed_context={})
                            if hasattr(self, "pattern_detector")
                            else []
                        )

                        batch_data[date] = {
                            "gex_metrics": gex_metrics,
                            "patterns": patterns,
                            "obfuscated_date": date_mapping[date],
                        }
                    else:
                        batch_data[date] = {"error": "No data available", "obfuscated_date": date_mapping[date]}
                except Exception as e:
                    import traceback

                    logger.warning(f"Failed to get data for {date}: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                    batch_data[date] = {"error": str(e), "obfuscated_date": date_mapping[date]}

            # Build batch analysis prompt
            batch_prompt = self._build_batch_prompt(batch_data, display_symbol, experiment_template)

            # Single LLM call for all dates
            logger.info(f"Analyzing {len(dates)} dates in single batch")
            batch_analysis = self._analyze_batch_with_llm(batch_prompt)

            # Parse results back to individual dates
            results = self._parse_batch_results(batch_analysis, dates, batch_data)

            return {
                "status": "success",
                "batch_size": len(dates),
                "dates_analyzed": dates,
                "obfuscation_used": use_obfuscation,
                "batch_analysis": batch_analysis,
                "individual_results": results,
                "timestamp": now_iso(),
            }

        except Exception as e:
            logger.error(f"Batch experiment failed: {e}")
            return {"status": "error", "error": str(e), "dates": dates, "timestamp": now_iso()}

    def _build_batch_prompt(self, batch_data: Dict, symbol: str, template: str = None) -> str:
        """Build prompt for batch LLM analysis using templates from config."""
        templates = self.prompt_templates.get("batch_analysis", {})

        # Fallback to inline if templates not loaded
        if not templates:
            return self._build_batch_prompt_inline(batch_data, symbol)

        # Build header
        prompt = templates.get("header", "").format(batch_size=len(batch_data), symbol=symbol)

        # Build data sections
        divider = templates.get("day_section_divider", "=" * 60)
        for date, data in batch_data.items():
            obfusc_date = data.get("obfuscated_date", date)
            prompt += f"\n{divider}\n{obfusc_date}:\n"

            if "error" in data:
                error_msg = templates.get("error_message", "  ERROR: {error}")
                prompt += error_msg.format(error=data["error"]) + "\n"
            else:
                gex = data.get("gex_metrics", {})
                # Use template fields with fallback
                data_fields = templates.get(
                    "data_fields",
                    [
                        "  Total GEX: ${total_gamma:,.0f}",
                        "  Spot Price: ${spot_price:.2f}",
                        "  Flip Point: ${flip_point:.2f}",
                        "  Regime: {regime}",
                    ],
                )

                for field_template in data_fields:
                    try:
                        prompt += (
                            field_template.format(
                                total_gamma=gex.get("total_gamma", 0),
                                spot_price=gex.get("spot_price", 0),
                                flip_point=gex.get("flip_point", 0),
                                regime=gex.get("regime", "Unknown"),
                            )
                            + "\n"
                        )
                    except KeyError:
                        # Skip malformed template fields
                        continue

                if data.get("patterns"):
                    patterns_line = templates.get("patterns_line", "  Patterns Detected: {patterns}")
                    patterns_str = ", ".join([p.get("pattern", "") for p in data["patterns"][:3]])
                    prompt += patterns_line.format(patterns=patterns_str) + "\n"

        # Add footer
        prompt += "\n" + templates.get("footer", "")
        return prompt

    def _build_batch_prompt_inline(self, batch_data: Dict, symbol: str) -> str:
        """Inline fallback for batch prompt (legacy compatibility)."""
        prompt = f"""Analyze the following {len(batch_data)} trading days for {symbol}.
Look for patterns across all dates and provide comparative analysis.

DATA FOR EACH DAY:
"""
        for date, data in batch_data.items():
            obfusc_date = data.get("obfuscated_date", date)
            prompt += f"\n{'='*60}\n{obfusc_date}:\n"

            if "error" in data:
                prompt += f"  ERROR: {data['error']}\n"
            else:
                gex = data.get("gex_metrics", {})
                prompt += f"  Total GEX: ${gex.get('total_gamma', 0):,.0f}\n"
                prompt += f"  Spot Price: ${gex.get('spot_price', 0):.2f}\n"
                prompt += f"  Flip Point: ${gex.get('flip_point', 0):.2f}\n"
                prompt += f"  Regime: {gex.get('regime', 'Unknown')}\n"

                if data.get("patterns"):
                    prompt += (
                        f"  Patterns Detected: {', '.join([p.get('pattern', '') for p in data['patterns'][:3]])}\n"
                    )

        prompt += f"""
{'='*60}
QUESTIONS TO ANSWER:
1. What patterns do you see across these dates?
2. Are there consistent mechanics (WHO forcing WHOM to do WHAT)?
3. What is the highest confidence signal across all dates?
4. Do you see any temporal patterns (e.g., weekly effects)?

IMPORTANT: Return your analysis in JSON format with this structure:
{{
  "overall_analysis": "Your overall analysis here",
  "individual_days": {{
    "DATE_KEY": {{
      "who": "Identify the forcing party",
      "whom": "Who is being forced",
      "what": "Specific forced action",
      "mechanics": "Brief causal chain",
      "confidence": 0-100 (numeric)
    }}
  }}
}}

Use the obfuscated date keys (e.g., "Day T+0") as the DATE_KEY.
Confidence must be a number 0-100.
"""
        return prompt

    def _analyze_batch_with_llm(self, prompt: str) -> Dict:
        """Send batch prompt to LLM and get analysis."""
        try:
            # Use the LLM client if available
            if hasattr(self, "llm") and self.llm is not None:
                response = self.llm.generate(prompt)
                # Parse response (may be string or dict)
                if isinstance(response, dict):
                    return response.get("content", response)
                else:
                    # Try to parse as JSON
                    import json

                    response_str = str(response)
                    start = response_str.find("{")
                    end = response_str.rfind("}") + 1
                    if start >= 0 and end > start:
                        json_str = response_str[start:end]
                        # FIX: Handle o4-mini JSON quirks (Issue #137)
                        json_str = json_str.replace(r"\$", "$")
                        return json.loads(json_str)
                    else:
                        # Fallback
                        return {"overall_analysis": response_str, "individual_days": {}}
            else:
                # Fallback to simple dict response
                logger.warning("No LLM client available, using mock response")
                response = {
                    "overall_analysis": "Mock batch analysis",
                    "temporal_patterns": "No patterns detected in mock mode",
                    "individual_days": {},
                }

            return response

        except Exception as e:
            logger.error(f"LLM batch analysis failed: {e}")
            return {"error": str(e)}

    def _parse_batch_results(self, batch_analysis: Dict, dates: List[str], batch_data: Dict) -> Dict:
        """Parse batch LLM results back to individual dates."""
        results = {}
        individual_days = batch_analysis.get("individual_days", {})

        for date in dates:
            # Get obfuscated date key (e.g., "Day T+0")
            obfuscated_date = batch_data[date].get("obfuscated_date", date)

            # Try to find analysis using obfuscated date key first, fall back to real date
            day_analysis = individual_days.get(obfuscated_date, individual_days.get(date, {}))

            # Combine with existing data
            results[date] = {
                "date": date,
                "obfuscated_date": obfuscated_date,  # Include obfuscated date
                "gex_metrics": batch_data[date].get("gex_metrics", {}),
                "patterns_detected": batch_data[date].get("patterns", []),
                "actionable_signal": day_analysis.get(
                    "signal", {"action": "wait", "confidence": 0, "rationale": "No clear signal"}
                ),
                "batch_context": batch_analysis.get("overall_analysis", ""),
                "mechanics_interpretation": {
                    "who": day_analysis.get("who", "Unknown"),
                    "whom": day_analysis.get("whom", "Unknown"),
                    "what": day_analysis.get("what", "Unknown"),
                    "confidence": day_analysis.get("confidence", 0),
                },
            }

        return results

    def _plan_experiment_tools(self, experiment_description: str, date: str) -> Dict:
        """Use LLM to analyze experiment description and decide what tools/data are needed.

        Returns a tool execution plan using templates from config.
        """
        templates = self.prompt_templates.get("experiment_planning", {})

        # Fallback to inline if templates not loaded
        if not templates:
            planning_prompt = self._build_planning_prompt_inline(experiment_description, date)
        else:
            # Build from templates
            planning_prompt = templates.get("header", "").format(
                experiment_description=experiment_description, date=date
            )
            planning_prompt += "\n" + templates.get("tools_section", "")
            planning_prompt += "\n" + templates.get("decision_framework", "")
            planning_prompt += "\n" + templates.get("response_format", "")

        try:
            response = self.llm.generate(planning_prompt)
            # Parse JSON response
            import json

            if isinstance(response, dict) and "content" in response:
                plan_text = response["content"]
            else:
                plan_text = str(response)

            # Extract JSON from response
            start = plan_text.find("{")
            end = plan_text.rfind("}") + 1
            if start >= 0 and end > start:
                plan_json = plan_text[start:end]
                # FIX: Handle o4-mini JSON quirks (Issue #137)
                plan_json = plan_json.replace(r"\$", "$")
                tool_plan = json.loads(plan_json)
            else:
                # Fallback if JSON parsing fails
                tool_plan = {
                    "experiment_type": "comprehensive",
                    "required_tools": ["fetch_options_data", "calculate_gamma_exposure"],
                    "data_requirements": ["options_chain"],
                    "analysis_focus": "general market analysis",
                    "reasoning": "fallback comprehensive analysis",
                }

            return tool_plan

        except Exception as e:
            logger.warning(f"Tool planning failed, using fallback: {e}")
            # Fallback comprehensive plan
            return {
                "experiment_type": "comprehensive",
                "required_tools": ["fetch_options_data", "calculate_gamma_exposure"],
                "data_requirements": ["options_chain"],
                "analysis_focus": "general market analysis",
                "reasoning": "fallback due to planning error",
            }

    def _build_planning_prompt_inline(self, experiment_description: str, date: str) -> str:
        """Inline fallback for planning prompt (legacy compatibility)."""
        return f"""
You are an autonomous market analysis agent. Analyze this experiment request and decide what tools and data are needed.

EXPERIMENT REQUEST: {experiment_description}
DATE: {date}

AVAILABLE TOOLS:
1. fetch_options_data(symbol, date) - Get options chain data
2. calculate_gamma_exposure(options_data) - Calculate GEX metrics
3. fetch_market_data(symbol, date) - Get underlying price/volume data
4. enhanced_pattern_detector - Detect strike-level patterns
5. daily_analysis - Full comprehensive analysis

DECISION FRAMEWORK:
- For gamma/GEX analysis: Need options data + GEX calculation
- For pattern detection: Need options data + pattern analysis
- For volatility analysis: Need market data + options data
- For timing studies: Need intraday data consideration
- For strike analysis: Need detailed strike-level data

Respond with a JSON plan:
{{
    "experiment_type": "gamma_pinning|volatility_analysis|pattern_detection|comprehensive",
    "required_tools": ["tool1", "tool2", ...],
    "data_requirements": ["options_chain", "market_data", "strike_details"],
    "analysis_focus": "What to focus the analysis on",
    "reasoning": "Why these tools are needed"
}}
"""

    def _execute_tool_plan(self, tool_plan: Dict, date: str) -> Dict:
        """Execute the tools specified in the LLM-generated plan.

        Returns collected data for analysis.
        """
        experiment_data = {}
        required_tools = tool_plan.get("required_tools", [])

        try:
            # Execute tools based on LLM decision
            if "fetch_options_data" in required_tools:
                if AUTOGEN_TOOLS_AVAILABLE:
                    logger.info("LLM decided: fetching options data")
                    result = fetch_options_data(self.symbol, date)
                    # Extract DataFrame from result dict
                    if isinstance(result, dict) and result.get("status") == "success":
                        experiment_data["options_data"] = result["data"]
                    else:
                        experiment_data["options_data"] = result
                else:
                    logger.info("LLM decided: fetching options data (cache fallback)")
                    # Use cache fallback
                    cache_data = self.cache_manager.get_daily_data(self.symbol, date)
                    experiment_data["options_data"] = cache_data

            if "calculate_gamma_exposure" in required_tools and experiment_data.get("options_data") is not None:
                if AUTOGEN_TOOLS_AVAILABLE:
                    logger.info("LLM decided: calculating gamma exposure")
                    # calculate_gamma_exposure expects symbol as first param, not options data
                    gex_result = calculate_gamma_exposure(symbol=self.symbol, trading_date=date, use_cache=True)
                    # Handle different return types
                    if isinstance(gex_result, dict) and gex_result.get("status") == "success":
                        experiment_data["gex_metrics"] = gex_result.get("metrics", {})
                    elif isinstance(gex_result, dict):
                        experiment_data["gex_metrics"] = gex_result
                    else:
                        logger.warning(f"Unexpected GEX result type: {type(gex_result)}")
                        experiment_data["gex_metrics"] = {}
                else:
                    logger.info("LLM decided: calculating gamma exposure (fallback)")
                    # Use local GEX calculator
                    experiment_data["gex_metrics"] = self.gex_calculator.calculate_gex(
                        experiment_data["options_data"], self.symbol
                    )

            if "fetch_market_data" in required_tools:
                if AUTOGEN_TOOLS_AVAILABLE:
                    logger.info("LLM decided: fetching market data")
                    market_result = fetch_market_data(self.symbol, date)
                    # Handle different return types from fetch_market_data
                    if isinstance(market_result, dict) and market_result.get("status") == "success":
                        experiment_data["market_data"] = market_result.get("data", {})
                    elif isinstance(market_result, dict):
                        experiment_data["market_data"] = market_result
                    else:
                        logger.warning(f"Unexpected market data type: {type(market_result)}")
                        experiment_data["market_data"] = {}

            if "enhanced_pattern_detector" in required_tools and experiment_data.get("gex_metrics"):
                logger.info("LLM decided: running pattern detection")
                patterns = self.pattern_detector.detect_all_patterns(experiment_data["gex_metrics"], {}, date)
                experiment_data["patterns"] = patterns

            if "daily_analysis" in required_tools:
                logger.info("LLM decided: running full daily analysis")
                # Run existing daily analysis but store intermediate results
                analysis_result = self.daily_analysis(date)
                experiment_data.update(analysis_result)

            return experiment_data

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            # Fallback to basic daily analysis
            return self.daily_analysis(date)

    def _analyze_experiment_results(self, experiment_description: str, experiment_data: Dict, tool_plan: Dict) -> Dict:
        """Use LLM to analyze the collected data and generate insights specific to the experiment.

        Uses templates from config.
        """
        templates = self.prompt_templates.get("experiment_analysis", {})

        # Fallback to inline if templates not loaded
        if not templates:
            analysis_prompt = self._build_analysis_prompt_inline(experiment_description, experiment_data, tool_plan)
        else:
            # Build from templates
            analysis_prompt = templates.get("header", "").format(
                experiment_description=experiment_description,
                tool_plan_reasoning=tool_plan.get("reasoning", "Unknown"),
                analysis_focus=tool_plan.get("analysis_focus", "General analysis"),
            )

            # Add GEX metrics section if available
            if experiment_data.get("gex_metrics"):
                gex = experiment_data["gex_metrics"]
                gex_section = templates.get("gex_metrics_section", "")
                try:
                    analysis_prompt += "\n" + gex_section.format(
                        total_gamma=gex.get("total_gamma", 0),
                        net_gex=gex.get("net_gex", 0),
                        spot_price=gex.get("spot_price", 0),
                        gamma_flip_point=gex.get("gamma_flip_point", 0),
                    )
                except KeyError:
                    # Skip if template has missing keys
                    pass

            # Add patterns section if available
            if experiment_data.get("patterns"):
                patterns = experiment_data["patterns"]
                patterns_section = templates.get("patterns_section", "")
                key_patterns = [p.get("pattern_type", "Unknown") for p in patterns[:3]]
                analysis_prompt += "\n" + patterns_section.format(
                    pattern_count=len(patterns), key_patterns=key_patterns
                )

            # Add requirements and response format
            analysis_prompt += "\n" + templates.get("analysis_requirements", "").format(
                experiment_description=experiment_description
            )
            analysis_prompt += "\n" + templates.get("response_format", "").format(
                experiment_type=tool_plan.get("experiment_type", "general")
            )

        try:
            response = self.llm.generate(analysis_prompt)

            # Parse JSON response
            import json

            if isinstance(response, dict) and "content" in response:
                analysis_text = response["content"]
            else:
                analysis_text = str(response)

            # Extract JSON from response
            start = analysis_text.find("{")
            end = analysis_text.rfind("}") + 1
            if start >= 0 and end > start:
                analysis_json = analysis_text[start:end]
                # FIX: Handle o4-mini JSON quirks (Issue #137)
                analysis_json = analysis_json.replace(r"\$", "$")
                result = json.loads(analysis_json)
            else:
                # Fallback structured result
                result = {
                    "experiment_type": tool_plan.get("experiment_type", "general"),
                    "mechanics_interpretation": {
                        "who": "Market Makers",
                        "whom": "Retail Traders",
                        "what": "Price Discovery",
                        "confidence": 70,
                    },
                    "key_findings": ["Analysis completed"],
                    "actionable_signal": {
                        "action": "wait",
                        "confidence": 50,
                        "rationale": "Insufficient data for clear signal",
                    },
                    "experiment_specific_insights": f"Completed analysis for: {experiment_description}",
                }

            # Merge with experiment data
            result.update(experiment_data)
            return result

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            # Return experiment data with basic structure
            result = experiment_data.copy()
            result.update(
                {
                    "experiment_type": tool_plan.get("experiment_type", "general"),
                    "status": "completed_with_errors",
                    "error": str(e),
                }
            )
            return result

    def _build_analysis_prompt_inline(self, experiment_description: str, experiment_data: Dict, tool_plan: Dict) -> str:
        """Inline fallback for analysis prompt (legacy compatibility)."""
        analysis_prompt = f"""
You are analyzing market data for this experiment: {experiment_description}

TOOL PLAN EXECUTED: {tool_plan.get('reasoning', 'Unknown')}
EXPERIMENT FOCUS: {tool_plan.get('analysis_focus', 'General analysis')}

DATA COLLECTED:
"""

        # Add relevant data summaries to prompt
        if experiment_data.get("gex_metrics"):
            gex = experiment_data["gex_metrics"]
            analysis_prompt += f"""
GEX METRICS:
- Total Gamma: ${gex.get('total_gamma', 0):,.0f}
- Net GEX: ${gex.get('net_gex', 0):,.0f}
- Spot Price: ${gex.get('spot_price', 0):.2f}
- Gamma Flip Point: ${gex.get('gamma_flip_point', 0):.2f}
"""

        if experiment_data.get("patterns"):
            patterns = experiment_data["patterns"]
            analysis_prompt += f"""
PATTERNS DETECTED: {len(patterns)} patterns found
Key Patterns: {[p.get('pattern_type', 'Unknown') for p in patterns[:3]]}
"""

        analysis_prompt += f"""

ANALYSIS REQUIREMENTS:
1. Interpret findings specifically for: {experiment_description}
2. Provide WHO/WHOM/WHAT market mechanics
3. Generate confidence score (0-100%)
4. Suggest actionable trading signal if applicable
5. Explain reasoning in context of the experiment

Respond with JSON:
{{
    "experiment_type": "{tool_plan.get('experiment_type', 'general')}",
    "mechanics_interpretation": {{
        "who": "Primary market actor",
        "whom": "Who they're acting against",
        "what": "What action is being forced",
        "confidence": 85
    }},
    "key_findings": ["finding1", "finding2"],
    "actionable_signal": {{
        "action": "buy|sell|wait",
        "confidence": 80,
        "rationale": "Why this signal makes sense"
    }},
    "experiment_specific_insights": "Analysis specific to the experiment request"
}}
"""
        return analysis_prompt

    def daily_analysis(self, date) -> Dict:
        # Store current date for logging
        self._current_date = date
        """Perform complete daily market mechanics analysis.

        Returns:
            Dict containing:
            - mechanics_interpretation: WHO is forcing WHOM to do WHAT
            - actionable_signal: Trading recommendation
            - confidence: Statistical confidence in the signal
            - supporting_evidence: Data backing the interpretation
        """
        try:
            # Normalize date input
            date_obj, date_str = self._normalize_date(date)

            # 1. Get data
            logger.info(f"Starting daily analysis for {date_str}")

            # Try database GEX first for consistency with baseline
            gex_metrics = self._fetch_gex_from_database(date_str)

            if gex_metrics:
                # If we got GEX from database, we might not have options data
                logger.info(f"Using database GEX for {date_str}, skipping options data fetch")
                options_data = pd.DataFrame()  # Empty DataFrame for downstream functions
            else:
                # Fallback to normal options data flow
                options_data = self._fetch_options_data(date_str)
                if options_data is None or options_data.empty:
                    logger.warning(f"No options data for {date_str}")
                    return self._empty_analysis()

                # 2. Calculate GEX metrics from options data
                gex_metrics = self._calculate_gex_metrics(options_data, date_str)

            # 3. Build comprehensive context
            context = self._build_market_context(date_obj, gex_metrics, options_data)

            # 4. Detect patterns
            patterns = self._detect_mechanics_patterns(context)

            # 5. LLM interprets mechanics (if available)
            if self.llm:
                interpretation = self._llm_interpret_mechanics(context, patterns)
            else:
                interpretation = self._rule_based_interpretation(patterns)

            # 6. Generate actionable signal
            # Add overall confidence and patterns to context for signal generation
            overall_confidence = self._calculate_confidence(patterns, context)
            context["overall_confidence"] = overall_confidence
            context["patterns_detected"] = patterns
            signal = self._generate_trading_signal(interpretation, context)

            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
            return {
                "date": date_str,
                "mechanics_interpretation": interpretation,
                "actionable_signal": signal,
                "patterns_detected": patterns,
                "gex_metrics": gex_metrics,
                "confidence": self._calculate_confidence(patterns, context),
            }

        except Exception as e:
            import traceback

            logger.error(f"Error in daily analysis: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._empty_analysis()

    def _fetch_options_data(self, date) -> Optional[pd.DataFrame]:
        """Fetch options data using autogen_tools for better caching.

        Issue #180: Now uses SQLiteOptionsManager directly for fallback.
        """
        _, date_str = self._normalize_date(date)

        if not AUTOGEN_TOOLS_AVAILABLE:
            # Fallback to direct SQLite access
            return self.db.get_options_chain(self.symbol, date_str)

        # Use autogen tool which handles cache → API → sample data fallback
        try:
            result = fetch_options_data(symbol=self.symbol, trading_date=date_str, use_cache=True)

            if result["status"] == "success":
                logger.info(f"Fetched options data from {result['source']} for {self.symbol} {date_str}")
                return result["data"]
            else:
                logger.error(f"AutoGen fetch failed: {result.get('message', 'Unknown error')}")
                # Fallback to direct SQLite access
                return self.db.get_options_chain(self.symbol, date_str)

        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"AutoGen API connection issue: {e}, falling back to SQLite")
            return self.db.get_options_chain(self.symbol, date_str)
        except Exception as e:
            logger.error(f"AutoGen tools error: {e}, falling back to SQLite")
            return self.db.get_options_chain(self.symbol, date_str)

    def _fetch_gex_from_database(self, date_str: str) -> Optional[Dict]:
        """Fetch GEX data from database, calculate and populate if missing.

        Supports both daily data and intra-day data retrieval. For timestamps, queries intraday_gex_metrics table. For
        dates, queries daily_gex_metrics table.
        """
        try:
            conn = sqlite3.connect("./.cache/consolidated_historical.db")

            # Determine if this is intra-day timestamp or daily date
            is_intraday = " " in date_str and ":" in date_str

            if is_intraday:
                # Query intraday table for exact timestamp
                query = """
                    SELECT timestamp, total_gex, gex_regime, gamma_flip_point,
                           net_call_gex, net_put_gex, flip_ratio, spot_price
                    FROM intraday_gex_metrics
                    WHERE symbol = ? AND timestamp = ?
                """
            else:
                # Query daily table for date
                query = """
                    SELECT date, total_gex, gex_regime, gamma_flip_point,
                           net_call_gex, net_put_gex, flip_ratio, spot_price
                    FROM daily_gex_metrics
                    WHERE symbol = ? AND date = ?
                """

            cursor = conn.execute(query, (self.symbol, date_str))
            row = cursor.fetchone()

            if row:
                # Data exists - return it
                conn.close()
                total_gex = row[1]
                return {
                    "total_gamma": total_gex,
                    "net_gex": total_gex,
                    "gex_value": total_gex,
                    "regime": row[2] or ("NEGATIVE_GAMMA" if total_gex < 0 else "POSITIVE_GAMMA"),
                    "flip_level": row[3] or 0,
                    # Use flip_ratio as proxy
                    "gamma_concentration": abs(row[6]) if row[6] else 0,
                    "call_gamma": row[4] or 0,
                    "put_gamma": row[5] or 0,
                    # Use flip point as zero gamma
                    "zero_gamma_level": row[3] or 0,
                    "spot_price": row[7] or 0,
                    "source": "historical_database",
                }

            # Data missing - calculate and populate
            logger.info(f"No database GEX data for {date_str}, calculating and populating...")

            # Fetch options data for calculation
            options_data = self._fetch_options_data(date_str)
            if options_data is None or options_data.empty:
                conn.close()
                logger.warning(f"Cannot calculate GEX for {date_str} - no options data")
                return None

            # Calculate GEX metrics
            gex_metrics = self._calculate_gex_metrics(options_data, date_str)
            if not gex_metrics:
                conn.close()
                logger.warning(f"GEX calculation failed for {date_str}")
                return None

            # Populate database with calculated data
            self._populate_database_entry(conn, date_str, gex_metrics)
            conn.close()

            # Return calculated data with database source flag
            gex_metrics["source"] = "calculated_and_populated"
            logger.info(f"Calculated and populated GEX for {date_str}: {gex_metrics.get('net_gex', 0):.2e}")
            return gex_metrics

        except Exception as e:
            logger.warning(f"Database GEX fetch/populate failed: {e}")
            return None

    def _calculate_gex_metrics(self, options_data: pd.DataFrame, date) -> Dict:
        """Calculate comprehensive GEX metrics using autogen_tools or direct calculation."""
        try:

            # Convert date to string format
            _, date_str = self._normalize_date(date)

            # Get market data for spot price using autogen tools
            if AUTOGEN_TOOLS_AVAILABLE:
                try:
                    market_result = fetch_market_data(symbol=self.symbol, end_date=date_str, use_cache=True)

                    if market_result["status"] == "success":
                        market_data = market_result["data"]
                        close_col = "close" if "close" in market_data.columns else "Close"
                        spot_price = market_data[close_col].iloc[-1]
                    else:
                        # Fallback to options data spot price
                        spot_price = (
                            options_data["underlying_last"].iloc[0] if "underlying_last" in options_data.columns else 0
                        )

                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"AutoGen market data API issue: {e}, using options data fallback")
                    spot_price = (
                        options_data["underlying_last"].iloc[0] if "underlying_last" in options_data.columns else 0
                    )
                except Exception as e:
                    logger.error(f"AutoGen market data error: {e}, using options data fallback")
                    spot_price = (
                        options_data["underlying_last"].iloc[0] if "underlying_last" in options_data.columns else 0
                    )
            else:
                # Direct fallback when AutoGen not available
                spot_price = options_data["underlying_last"].iloc[0] if "underlying_last" in options_data.columns else 0

            # Use autogen tool for GEX calculation which handles caching
            if AUTOGEN_TOOLS_AVAILABLE:
                try:
                    gex_result = calculate_gamma_exposure(
                        symbol=self.symbol, trading_date=date_str, spot_price=spot_price, use_cache=True
                    )

                    if gex_result["status"] == "success":
                        gex_metrics = gex_result["metrics"]
                        logger.info(
                            f"GEX calculation via autogen_tools (fallback): cache_hit={gex_result.get('cache_hit', False)}"
                        )

                        # Convert to expected format
                        gex_profile = {
                            "net_gex": gex_metrics.get("net_gex", 0),
                            "flip_point": gex_metrics.get("flip_point", spot_price),
                            "spot_price": spot_price,
                            "gex_by_strike": gex_metrics.get("gex_by_strike", {}),
                        }
                    else:
                        raise ValueError(
                            f"AutoGen GEX calculation failed: {gex_result.get('message', 'Unknown error')}"
                        )

                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"AutoGen GEX API issue: {e}, falling back to direct calculation")
                    gex_profile = self.gex_calculator.calculate_gex_profile(
                        options_data=options_data, underlying_price=spot_price
                    )
                except Exception as e:
                    logger.error(f"AutoGen GEX calculation error: {e}, falling back to direct calculation")
                    gex_profile = self.gex_calculator.calculate_gex_profile(
                        options_data=options_data, underlying_price=spot_price
                    )
            else:
                # Direct calculation when AutoGen not available
                gex_profile = self.gex_calculator.calculate_gex_profile(
                    options_data=options_data, underlying_price=spot_price
                )

            # Extract key metrics for compatibility - ensure consistent structure
            gex_results = self._normalize_gex_results(gex_profile, spot_price)

            # Add regime classification
            net_gex = gex_results.get("net_gex", 0)
            gex_results["gex_regime"] = self._classify_gex_regime(net_gex, spot_price)

            # Add Greeks concentration analysis
            gex_results["gamma_concentration"] = self._analyze_gamma_concentration(options_data, spot_price)

            return gex_results

        except Exception as e:
            logger.error(f"Error calculating GEX metrics: {e}")
            return {}

    def _build_market_context(self, date, gex_metrics: Dict, options_data: pd.DataFrame) -> Dict:
        """Build comprehensive market context for analysis."""
        # Enhanced temporal context with Friday 3:30 PM detection
        temporal_context = self._get_temporal_context(date)

        # Add Friday 3:30 PM flag for Issue #73 validation
        temporal_context["is_friday_330pm"] = (
            temporal_context.get("day_of_week") == "Friday"
            and hasattr(date, "hour")
            and hasattr(date, "minute")
            and date.hour == 15
            and date.minute == 30
        )

        context = {
            "date": date,
            "gex_metrics": gex_metrics,
            "options_data": options_data,  # Include options data for strike-level analysis
            "price_action": self._describe_price_action(date),
            "options_flow": self._analyze_flow_patterns(options_data),
            "temporal_context": temporal_context,
            "strike_distribution": self._analyze_strike_distribution(options_data),
            "volatility_surface": self._analyze_volatility_surface(options_data),
        }

        # Add strike-level patterns for enhanced analysis
        if not options_data.empty and gex_metrics.get("spot_price"):
            strike_patterns = {
                "gamma_concentration": self._detect_gamma_concentration_enhanced(
                    options_data, gex_metrics["spot_price"]
                ),
                "volume_anomalies": self._detect_volume_anomalies(options_data),
                "gamma_walls": self._detect_gamma_walls(options_data, gex_metrics["spot_price"]),
                "pin_setup": self._detect_pin_setup(options_data, gex_metrics["spot_price"], temporal_context),
                "dealer_positioning": self._calculate_dealer_exposure(options_data, gex_metrics["spot_price"]),
            }
            context["strike_level_patterns"] = strike_patterns

        # Add Fed context if available
        fed_context = self._get_fed_context(date)
        if fed_context:
            context["fed_context"] = fed_context

        return context

    def _describe_price_action(self, date) -> Dict:
        """Describe recent price action patterns."""
        try:
            # Ensure date is a datetime object
            if isinstance(date, str):
                date = parse_date_string(date)

            # Get last 5 days of price data
            price_data = []
            for i in range(5):
                check_date = date - datetime.timedelta(days=i)
                check_date_str = check_date.strftime("%Y-%m-%d")
                market_data = self.cache.get_market_data(self.symbol, check_date_str)
                if market_data is not None and not market_data.empty:
                    # Handle both lowercase and capitalized column names
                    open_col = "open" if "open" in market_data.columns else "Open"
                    high_col = "high" if "high" in market_data.columns else "High"
                    low_col = "low" if "low" in market_data.columns else "Low"
                    close_col = "close" if "close" in market_data.columns else "Close"
                    volume_col = "volume" if "volume" in market_data.columns else "Volume"

                    price_data.append(
                        {
                            "date": check_date,
                            "open": market_data[open_col].iloc[0],
                            "high": market_data[high_col].iloc[0],
                            "low": market_data[low_col].iloc[0],
                            "close": market_data[close_col].iloc[0],
                            "volume": market_data[volume_col].iloc[0],
                        }
                    )

            if not price_data:
                return {}

            # Calculate price action metrics
            closes = [p["close"] for p in price_data]
            return {
                "trend": "up" if closes[0] > closes[-1] else "down",
                "volatility": np.std(closes) / np.mean(closes) if closes else 0,
                "recent_range": (max(closes) - min(closes)) / np.mean(closes) if closes else 0,
                "volume_trend": "increasing" if price_data[0]["volume"] > price_data[-1]["volume"] else "decreasing",
            }

        except Exception as e:
            logger.error(f"Error describing price action: {e}")
            return {}

    def _analyze_flow_patterns(self, options_data: pd.DataFrame) -> Dict:
        """Analyze options flow patterns."""
        if options_data.empty:
            return {}

        try:
            total_call_volume = options_data[options_data["type"] == "call"]["volume"].sum()
            total_put_volume = options_data[options_data["type"] == "put"]["volume"].sum()
            total_call_oi = options_data[options_data["type"] == "call"]["open_interest"].sum()
            total_put_oi = options_data[options_data["type"] == "put"]["open_interest"].sum()

            return {
                "put_call_ratio": total_put_volume / max(total_call_volume, 1),
                "oi_put_call_ratio": total_put_oi / max(total_call_oi, 1),
                "volume_vs_oi": (total_call_volume + total_put_volume) / max(total_call_oi + total_put_oi, 1),
                "call_skew": self._calculate_skew(options_data[options_data["type"] == "call"]),
                "put_skew": self._calculate_skew(options_data[options_data["type"] == "put"]),
            }

        except Exception as e:
            logger.error(f"Error analyzing flow patterns: {e}")
            return {}

    def _get_temporal_context(self, date) -> Dict:
        """Get temporal context (day of week, month, expiry cycles)."""
        # Convert date to datetime object for consistent handling
        if isinstance(date, str):
            date_obj = pd.Timestamp(date).to_pydatetime()
        elif hasattr(date, "to_pydatetime"):
            date_obj = date.to_pydatetime()
        else:
            date_obj = date

        return {
            "day_of_week": date_obj.strftime("%A"),
            "day_of_month": date_obj.day,
            "month": date_obj.month,
            "is_opex": self._is_opex_week(date),
            "days_to_fomc": self._days_to_next_fomc(date),
            "is_month_end": date.day >= 25,
            "is_quarter_end": date.month in [3, 6, 9, 12] and date.day >= 25,
        }

    def _detect_mechanics_patterns(self, context: Dict) -> List[Dict]:
        """Enhanced pattern detection with strike-level analysis."""
        detected_patterns = []

        # Get enhanced strike-level patterns
        strike_patterns = self._detect_strike_level_patterns(context)

        # Traditional mechanics patterns with enhanced strike-level data
        gex_metrics = context.get("gex_metrics", {})
        # options_flow = context.get('options_flow', {})

        # Check for each mechanics pattern with enhanced detection
        for pattern_name, pattern_def in self.mechanics_patterns.items():
            confidence = 0
            evidence = []

            if pattern_name == "dealer_hedging":
                # Enhanced with strike-level gamma concentration
                gamma_config = self.strike_pattern_config.get("gamma_concentration", {})
                threshold = gamma_config.get("high_concentration_pct", 0.20)

                gamma_data = strike_patterns.get("gamma_concentration", {})
                if gamma_data.get("concentration_pct", 0) > threshold:
                    confidence += 50
                    evidence.append(
                        f"Gamma concentration: {gamma_data.get('concentration_pct', 0):.1%} at ${gamma_data.get('max_strike', 0):.0f}"
                    )

                # Strike-level volume validation
                volume_data = strike_patterns.get("volume_anomalies", {})
                if volume_data.get("detected", False):
                    confidence += 30
                    evidence.append(f"Volume anomaly: {volume_data.get('max_volume', 0):,.0f} contracts")

            elif pattern_name == "gamma_squeeze":
                if gex_metrics.get("gex_regime") == "POSITIVE_GAMMA_HIGH":
                    confidence += 40
                    evidence.append("Positive gamma regime")

                # Enhanced with gamma wall detection
                gamma_walls = strike_patterns.get("gamma_walls", {})
                if gamma_walls.get("resistance_strikes"):
                    confidence += 30
                    evidence.append(f"Gamma resistance at {gamma_walls.get('resistance_strikes')}")

            elif pattern_name == "pin_manipulation":
                # Enhanced pin detection using Issue #73 validated approach
                pin_data = strike_patterns.get("pin_setup", {})
                if pin_data.get("pin_probability", 0) > 0.60:  # Validated 60% threshold
                    confidence += 70
                    evidence.append(
                        f"Pin setup: {pin_data.get('pin_probability', 0):.1%} probability to ${pin_data.get('target_strike', 0):.0f}"
                    )

                # Add Friday 3:30 PM context if applicable
                time_context = context.get("temporal_context", {})
                if time_context.get("is_friday_330pm", False):
                    confidence += 20
                    evidence.append("Friday 3:30 PM expiration timing")

            if confidence > 30:
                detected_patterns.append(
                    {
                        "pattern": pattern_name,
                        "confidence": confidence,
                        "who": pattern_def["who"],
                        "whom": pattern_def["whom"],
                        "what": pattern_def["what"],
                        "evidence": evidence,
                    }
                )

        # Add compound pattern detection (main chat suggestion)
        compound_patterns = self._detect_compound_patterns(strike_patterns, context)
        detected_patterns.extend(compound_patterns)

        return sorted(detected_patterns, key=lambda x: x["confidence"], reverse=True)

    def _detect_strike_level_patterns(self, context: Dict) -> Dict:
        """Enhanced strike-level pattern detection based on Issue #73 validation."""
        options_data = context.get("options_data", pd.DataFrame())
        gex_metrics = context.get("gex_metrics", {})
        temporal_context = context.get("temporal_context", {})
        spot_price = gex_metrics.get("spot_price", 0)

        if options_data.empty or not spot_price:
            return {}

        patterns = {
            "gamma_concentration": self._detect_gamma_concentration_enhanced(options_data, spot_price),
            "volume_anomalies": self._detect_volume_anomalies(options_data),
            "gamma_walls": self._detect_gamma_walls(options_data, spot_price),
            "pin_setup": self._detect_pin_setup(options_data, spot_price, temporal_context),
            "dealer_positioning": self._calculate_dealer_exposure(options_data, spot_price),
        }

        return patterns

    def _detect_compound_patterns(self, strike_patterns: Dict, context: Dict) -> List[Dict]:
        """Detect compound patterns where multiple signals align for higher probability.

        Based on main chat suggestion for pattern combination detection.
        """
        compound_patterns = []
        temporal_context = context.get("temporal_context", {})

        # High Probability Pin (validated from Issue #73 - 75% success rate)
        gamma_data = strike_patterns.get("gamma_concentration", {})
        volume_data = strike_patterns.get("volume_anomalies", {})
        pin_data = strike_patterns.get("pin_setup", {})

        if (
            gamma_data.get("concentration_pct", 0) > 0.20  # 20% gamma concentration
            and
            # Volume anomaly present
            volume_data.get("detected", False)
            and temporal_context.get("is_friday_330pm", False)
        ):  # Friday 3:30 PM timing

            combined_confidence = min(
                0.95,
                gamma_data.get("confidence", 0.5) * 0.4
                + volume_data.get("confidence", 0.5) * 0.3
                + 0.85,  # Issue #73 validated Friday 3:30 PM boost
            )

            compound_patterns.append(
                {
                    "pattern": "high_probability_pin",
                    "confidence": combined_confidence * 100,  # Convert to percentage
                    "who": "Market makers and institutional traders",
                    "whom": "Price action and retail traders",
                    "what": "Coordinated gamma pinning toward max concentration strike",
                    "evidence": [
                        f"Gamma concentration: {gamma_data.get('concentration_pct', 0):.1%} at ${gamma_data.get('max_strike', 0):.0f}",
                        f"Volume anomaly: {volume_data.get('max_volume', 0):,.0f} contracts",
                        "Friday 3:30 PM expiration timing (75% historical success)",
                        f"Target pin level: ${pin_data.get('target_strike', gamma_data.get('max_strike', 0)):.0f}",
                    ],
                    "historical_validation": {
                        "source": "Issue #73 June 2024 validation",
                        "success_rate": "75%",
                        "sample_size": 4,
                        "methodology": "Friday 3:30 PM gamma pinning analysis",
                    },
                }
            )

        # Volume + Gamma Squeeze Combination
        gamma_walls = strike_patterns.get("gamma_walls", {})
        if (
            volume_data.get("detected", False)
            and gamma_walls.get("resistance_strikes")
            and gamma_data.get("concentration_pct", 0) > 0.15
        ):

            compound_patterns.append(
                {
                    "pattern": "volume_gamma_breakout",
                    "confidence": 75,
                    "who": "Large options players",
                    "whom": "Market makers and short-term traders",
                    "what": "Force breakout through gamma resistance levels",
                    "evidence": [
                        f"Volume surge: {volume_data.get('max_volume', 0):,.0f} contracts",
                        f"Gamma resistance: {gamma_walls.get('resistance_strikes')}",
                        f"Concentration: {gamma_data.get('concentration_pct', 0):.1%}",
                    ],
                }
            )

        return compound_patterns

    def _detect_gamma_concentration_enhanced(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Enhanced gamma concentration detection based on Issue #73 validation."""
        try:
            if "gamma" not in options_data.columns:
                return {}

            # Group by strike and sum absolute gamma exposure
            gamma_by_strike = options_data.groupby("strike")["gamma"].sum().abs()
            total_gamma = gamma_by_strike.sum()

            if total_gamma == 0:
                return {}

            # Find max gamma strike and concentration percentage
            max_gamma_strike = gamma_by_strike.idxmax()
            max_gamma_value = gamma_by_strike.max()
            concentration_pct = max_gamma_value / total_gamma

            # Distance from spot price
            distance_from_spot = (max_gamma_strike - spot_price) / spot_price

            return {
                "max_strike": float(max_gamma_strike),
                "concentration_pct": concentration_pct,
                "distance_from_spot": distance_from_spot,
                "max_gamma_value": max_gamma_value,
                # Higher concentration = higher confidence
                "confidence": min(1.0, concentration_pct * 2),
            }

        except Exception as e:
            logger.error(f"Error in enhanced gamma concentration detection: {e}")
            return {}

    def _detect_volume_anomalies(self, options_data: pd.DataFrame) -> Dict:
        """Detect unusual volume spikes indicating institutional activity."""
        try:
            if "volume" not in options_data.columns:
                return {"detected": False}

            # Find strikes with high volume
            high_volume_threshold = self.config.get("gex_thresholds", {}).get("high_volume_threshold", 100000)
            volume_by_strike = options_data.groupby("strike")["volume"].sum()

            # Detect anomalies (>3x average volume)
            avg_volume = volume_by_strike.mean()
            anomaly_threshold = max(high_volume_threshold, avg_volume * 3)

            anomalous_strikes = volume_by_strike[volume_by_strike > anomaly_threshold]

            if anomalous_strikes.empty:
                return {"detected": False}

            max_volume_strike = anomalous_strikes.idxmax()
            max_volume = anomalous_strikes.max()

            return {
                "detected": True,
                "max_volume_strike": float(max_volume_strike),
                "max_volume": int(max_volume),
                "anomalous_strikes": anomalous_strikes.index.tolist(),
                "vs_average": max_volume / avg_volume if avg_volume > 0 else 0,
                # Confidence based on volume level
                "confidence": min(1.0, max_volume / 500000),
            }

        except Exception as e:
            logger.error(f"Error in volume anomaly detection: {e}")
            return {"detected": False}

    def _detect_gamma_walls(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Identify resistance/support levels from gamma buildup."""
        try:
            if "gamma" not in options_data.columns:
                return {}

            gamma_by_strike = options_data.groupby("strike")["gamma"].sum()

            # Find significant gamma levels (>20% of total)
            total_gamma = gamma_by_strike.abs().sum()
            significant_threshold = total_gamma * 0.20

            significant_strikes = gamma_by_strike[gamma_by_strike.abs() > significant_threshold]

            if significant_strikes.empty:
                return {}

            # Classify as resistance (above spot) or support (below spot)
            resistance_strikes = [s for s in significant_strikes.index if s > spot_price]
            support_strikes = [s for s in significant_strikes.index if s <= spot_price]

            return {
                "resistance_strikes": resistance_strikes,
                "support_strikes": support_strikes,
                "strength": "high" if len(significant_strikes) >= 3 else "medium",
            }

        except Exception as e:
            logger.error(f"Error in gamma walls detection: {e}")
            return {}

    def _detect_pin_setup(self, options_data: pd.DataFrame, spot_price: float, temporal_context: Dict) -> Dict:
        """Detect pin setup using Issue #73 validated methodology."""
        try:
            # Get gamma concentration data
            gamma_data = self._detect_gamma_concentration_enhanced(options_data, spot_price)

            if not gamma_data:
                return {}

            max_gamma_strike = gamma_data.get("max_strike", 0)
            concentration_pct = gamma_data.get("concentration_pct", 0)

            # Friday 3:30 PM gets boost from Issue #73 validation (75% success rate)
            is_friday_330pm = temporal_context.get("is_friday_330pm", False)
            base_probability = concentration_pct

            if is_friday_330pm and concentration_pct > 0.15:
                # Apply Issue #73 validated 75% success rate
                pin_probability = 0.75
            else:
                # Standard calculation
                pin_probability = min(0.90, base_probability * 2)

            return {
                "target_strike": max_gamma_strike,
                "pin_probability": pin_probability,
                "distance_to_target": abs(spot_price - max_gamma_strike) / spot_price,
                "friday_330pm_boost": is_friday_330pm,
                "validated_setup": is_friday_330pm and concentration_pct > 0.15,
            }

        except Exception as e:
            logger.error(f"Error in pin setup detection: {e}")
            return {}

    def _calculate_dealer_exposure(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Calculate net dealer gamma exposure and positioning."""
        try:
            if "gamma" not in options_data.columns:
                return {}

            # Estimate dealer positioning (simplified)
            total_gamma = options_data["gamma"].sum()
            call_gamma = options_data[options_data["type"] == "call"]["gamma"].sum()
            put_gamma = options_data[options_data["type"] == "put"]["gamma"].sum()

            # Find approximate gamma flip point
            gamma_by_strike = options_data.groupby("strike")["gamma"].sum()

            # Simple flip point estimation
            cumulative_gamma = gamma_by_strike.cumsum()
            zero_crossings = cumulative_gamma[cumulative_gamma.abs() < abs(total_gamma) * 0.1]

            flip_point = zero_crossings.index[0] if not zero_crossings.empty else spot_price

            return {
                "total_gamma": total_gamma,
                "call_gamma": call_gamma,
                "put_gamma": put_gamma,
                "flip_point": flip_point,
                "distance_to_flip": (spot_price - flip_point) / flip_point if flip_point > 0 else 0,
                "regime": "short_gamma" if total_gamma < 0 else "long_gamma",
            }

        except Exception as e:
            logger.error(f"Error in dealer exposure calculation: {e}")
            return {}

    def _llm_interpret_mechanics(self, context: Dict, patterns: List[Dict]) -> Dict:
        """Use LLM to interpret market mechanics."""
        logger.debug(f"_llm_interpret_mechanics called, LLM available: {self.llm is not None}")
        if not self.llm:
            logger.warning("No LLM available, falling back to rule-based interpretation")
            return self._rule_based_interpretation(patterns)

        # Build LLM prompt
        try:
            prompt = self._build_mechanics_prompt(context, patterns)
            logger.debug(f"Built prompt for LLM (length: {len(prompt)} chars)")
        except Exception as e:
            logger.error(f"Prompt building failed: {e}")
            return self._rule_based_interpretation(patterns)

        try:
            # Use duck typing with proper error handling
            logger.debug("Invoking LLM for mechanics interpretation...")
            interpretation = self._invoke_llm_safely(prompt)
            logger.info(f"LLM interpretation successful: confidence={interpretation.get('confidence', 'Unknown')}")
            return interpretation

        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return self._rule_based_interpretation(patterns)

    def _invoke_llm_safely(self, prompt: str) -> Dict:
        """Safely invoke LLM with proper interface detection."""
        logger.debug(f"_invoke_llm_safely called with prompt length: {len(prompt)}")
        # Try structured interpretation method first (preferred)
        try:
            if callable(getattr(self.llm, "interpret_mechanics", None)):
                logger.debug("Using interpret_mechanics method")
                response = self.llm.interpret_mechanics(prompt)
                # Log raw LLM response for analysis
                logger.info("RAW_LLM_RESPONSE_START")
                logger.info(f"Date: {getattr(self, '_current_date', 'unknown')}")
                logger.info(f"Symbol: {self.symbol}")
                logger.info(f"Method: interpret_mechanics")
                logger.info(f"Prompt_length: {len(prompt)}")
                logger.info(f"Response_type: {type(response)}")
                logger.info("RESPONSE_CONTENT:")
                logger.info(response)
                logger.info("RAW_LLM_RESPONSE_END")
                return response
        except (AttributeError, TypeError) as e:
            logger.debug(f"interpret_mechanics not available: {e}")
            pass

        # Try AutoGen-style interpretation
        try:
            if callable(getattr(self.llm, "analyze_market_mechanics", None)):
                logger.debug("Using analyze_market_mechanics method")
                response = self.llm.analyze_market_mechanics(prompt)
                # Log raw LLM response for analysis
                logger.info("RAW_LLM_RESPONSE_START")
                logger.info(f"Date: {getattr(self, '_current_date', 'unknown')}")
                logger.info(f"Symbol: {self.symbol}")
                logger.info(f"Method: analyze_market_mechanics")
                logger.info(f"Prompt_length: {len(prompt)}")
                logger.info(f"Response_type: {type(response)}")
                logger.info("RESPONSE_CONTENT:")
                logger.info(response)
                logger.info("RAW_LLM_RESPONSE_END")
                return response
        except (AttributeError, TypeError) as e:
            logger.debug(f"analyze_market_mechanics not available: {e}")
            pass

        # Fall back to generic generate method
        try:
            if callable(getattr(self.llm, "generate", None)):
                response = self.llm.generate(prompt)
                # Log raw LLM response for analysis
                logger.info("RAW_LLM_RESPONSE_START")
                logger.info(f"Date: {getattr(self, '_current_date', 'unknown')}")
                logger.info(f"Symbol: {self.symbol}")
                logger.info(f"Prompt_length: {len(prompt)}")
                logger.info(f"Response_length: {len(response)}")
                logger.info("RESPONSE_CONTENT:")
                logger.info(response)
                logger.info("RAW_LLM_RESPONSE_END")
                return self._parse_llm_response(response)
        except (AttributeError, TypeError):
            pass

        # Last resort: try calling the object directly
        try:
            response = self.llm(prompt)
            # Log raw LLM response for analysis
            logger.info("RAW_LLM_RESPONSE_START")
            logger.info(f"Date: {getattr(self, '_current_date', 'unknown')}")
            logger.info(f"Symbol: {self.symbol}")
            logger.info(f"Prompt_length: {len(prompt)}")
            logger.info(f"Response_length: {len(response)}")
            logger.info("RESPONSE_CONTENT:")
            logger.info(response)
            logger.info("RAW_LLM_RESPONSE_END")
            return self._parse_llm_response(response)
        except (AttributeError, TypeError, Exception):
            raise ValueError(f"LLM object {type(self.llm)} does not implement any recognized interface")

    def _rule_based_interpretation(self, patterns: List[Dict]) -> Dict:
        """Fallback rule-based interpretation when LLM unavailable."""
        if not patterns:
            return {
                "primary_mechanic": "No clear mechanics detected",
                "who": "Market participants",
                "whom": "Price action",
                "what": "Normal trading activity",
                "confidence": 0,
                "narrative": "No significant market mechanics patterns detected.",
            }

        # Use highest confidence pattern
        primary = patterns[0]

        narrative = f"{primary['who']} are forcing {primary['whom']} to {primary['what']}. "
        narrative += f"Evidence: {', '.join(primary['evidence'])}. "

        if len(patterns) > 1:
            narrative += f"Secondary pattern: {patterns[1]['pattern']} (confidence: {patterns[1]['confidence']}%)"

        return {
            "primary_mechanic": primary["pattern"],
            "who": primary["who"],
            "whom": primary["whom"],
            "what": primary["what"],
            "confidence": primary["confidence"],
            "narrative": narrative,
        }

    def _generate_trading_signal(self, interpretation: Dict, context: Dict) -> Dict:
        """Generate actionable trading signal from mechanics interpretation."""

        # Default signal - empty until we have actionable patterns
        signal = {
            "action": None,
            "confidence": None,
            "rationale": None,
            "risk_reward": None,
            "entry": None,
            "stop_loss": None,
            "target": None,
            "position_size": None,
            "pattern": None,
        }

        # Try to generate actionable signals using pattern detector
        try:
            gex_metrics = context.get("gex_metrics", {})
            spot_price = context.get("spot_price")

            if gex_metrics and spot_price:
                actionable_signals = self.actionable_detector.generate_signals(
                    gex_metrics=gex_metrics, market_mechanics=interpretation, spot_price=spot_price
                )

                if actionable_signals:
                    # Use the highest confidence signal
                    best_signal = max(actionable_signals, key=lambda s: s.signal_strength.value is not None)

                    # Convert to trading signal format
                    signal = {
                        "action": "buy" if best_signal.entry_price > spot_price else "sell",
                        "confidence": interpretation.get("confidence", 0),
                        "rationale": best_signal.pattern.mechanics_description,
                        "risk_reward": best_signal.risk_reward_ratio,
                        "entry": best_signal.entry_price,
                        "stop_loss": best_signal.stop_loss,
                        "target": best_signal.initial_target,
                        "position_size": best_signal.position_size_pct,
                        "pattern": best_signal.pattern.pattern_name,
                    }

                    logger.info(f"Generated actionable signal: {best_signal.pattern.pattern_name}")
                    return signal

        except Exception as e:
            logger.warning(f"Failed to generate actionable signals: {e}")

        # Fallback to original logic if actionable patterns fail
        min_confidence = self.config.get("min_signal_confidence", 30)  # Default 30%

        # Use pattern confidence if interpretation confidence is missing/low
        interp_confidence = interpretation.get("confidence", 0)
        pattern_confidence = context.get("overall_confidence", 0)
        effective_confidence = max(interp_confidence, pattern_confidence)

        if effective_confidence < min_confidence:
            return signal

        primary_mechanic = interpretation.get("primary_mechanic")
        gex_metrics = context.get("gex_metrics", {})

        # Also check detected patterns directly
        patterns = context.get("patterns_detected", [])
        top_pattern = patterns[0]["pattern"] if patterns else None

        logger.info(
            f"Signal generation: confidence {effective_confidence}% >= {min_confidence}%, pattern: {top_pattern}"
        )

        # Apply contrarian logic for specific patterns (check both LLM and pattern detection)
        active_mechanic = primary_mechanic or top_pattern
        if active_mechanic == "dealer_hedging":
            if gex_metrics.get("regime") == "NEGATIVE_GAMMA_LOW":  # Fixed key name
                signal = {
                    "action": "BUY",
                    "confidence": effective_confidence,
                    "rationale": "Dealers forced to buy dips in negative gamma - fade the move",
                    "risk_reward": 1.5,
                    "entry": "Market",
                    "stop_loss": "1%",
                    "target": "1.5%",
                }

        elif primary_mechanic == "gamma_squeeze":
            signal = {
                "action": "SELL",
                "confidence": interpretation["confidence"],
                "rationale": "Gamma squeeze exhaustion likely - fade the squeeze",
                "risk_reward": 1.5,
                "entry": "Market",
                "stop_loss": "1%",
                "target": "1.5%",
            }

        elif primary_mechanic == "pin_manipulation":
            # Trade toward the pin
            signal = {
                "action": "NEUTRAL",
                "confidence": interpretation["confidence"],
                "rationale": f"Price likely pinned to {gex_metrics.get('max_strike', 'major strike')}",
                "risk_reward": None,
                "entry": "Sell straddle at pin",
                "stop_loss": "Gamma flip",
                "target": "Expiry",
            }

        return signal

    def _calculate_confidence(self, patterns: List[Dict], context: Dict) -> float:
        """Calculate overall confidence in the analysis."""
        if not patterns:
            # Base confidence from GEX regime alone
            gex_metrics = context.get("gex_metrics", {})
            if gex_metrics.get("regime") in ["NEGATIVE_GAMMA_HIGH", "NEGATIVE_GAMMA_LOW"]:
                return 30.0  # Base 30% confidence for negative GEX
            return 0.0

        # Use max pattern confidence instead of average
        max_confidence = max(p["confidence"] for p in patterns)

        # Bonus for multiple confirming patterns
        if len(patterns) > 1:
            # +10% per additional pattern
            max_confidence += 10 * (len(patterns) - 1)

        # Adjust for context factors
        temporal = context.get("temporal_context", {})
        if temporal.get("is_opex"):
            max_confidence *= 1.2  # Higher confidence during OPEX
        if temporal.get("days_to_fomc", 999) < 3:
            max_confidence *= 0.8  # Lower confidence near FOMC

        return min(max_confidence, 100.0)

    def _build_mechanics_prompt(self, context: Dict, patterns: List[Dict]) -> str:
        """Build prompt for LLM mechanics interpretation using exact format."""

        # Prepare data for prompt builder
        gex_metrics = context.get("gex_metrics", {})

        # Add key strikes info if available
        if "strike_distribution" in context:
            strike_dist = context["strike_distribution"]
            if strike_dist:
                # Find heavy put OI and call walls
                gex_metrics["key_strikes"] = {
                    "heavy_put_oi": strike_dist.get("max_oi_strike", 0),
                    "call_walls": strike_dist.get("top_3_strikes", [0])[0] if strike_dist.get("top_3_strikes") else 0,
                }

        # Enhance options flow with specific patterns
        options_flow = context.get("options_flow", {})

        # Add detected unusual activity
        if patterns:
            top_pattern = patterns[0]
            if top_pattern["pattern"] == "gamma_squeeze":
                options_flow["unusual_activity"] = "Aggressive call buying to force squeeze"
            elif top_pattern["pattern"] == "pin_manipulation":
                options_flow["unusual_activity"] = "Straddle selling at pin strike"
            elif top_pattern["pattern"] == "dealer_hedging":
                options_flow["unusual_activity"] = "Dealer hedging flows dominating price action"

        # Add market context with strike-level patterns
        market_context = {
            "price_action": context.get("price_action", {}),
            "temporal_context": context.get("temporal_context", {}),
            "strike_distribution": context.get("strike_distribution", {}),
            "volatility_surface": context.get("volatility_surface", {}),
            # Add enhanced patterns
            "strike_level_patterns": context.get("strike_level_patterns", {}),
        }

        # Use prompt builder with exact format
        return self.prompt_builder.build_analysis_prompt(
            date=context["date"], gex_metrics=gex_metrics, options_flow=options_flow, market_context=market_context
        )

    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured interpretation."""
        # Use the prompt builder's parser
        parsed = self.prompt_builder.parse_llm_response(response)

        # Convert to our expected format
        primary_mechanic = parsed.get("pattern_identified", "Unknown")

        # Extract WHO, WHOM, WHAT from key players
        who = "Unknown"
        whom = "Unknown"
        what = "Unknown"

        if parsed.get("key_players"):
            if len(parsed["key_players"]) >= 2:
                who = parsed["key_players"][0].get("who", "Unknown")
                whom = parsed["key_players"][1].get("who", "Unknown")
                what = parsed["key_players"][0].get("what", "Unknown")

        # Calculate confidence from outcome probabilities
        confidence = 0
        if parsed.get("likely_outcomes"):
            # Use highest probability outcome as confidence
            confidences = [o.get("probability", 0) for o in parsed["likely_outcomes"]]
            if confidences:
                confidence = max(confidences)

        # Build narrative from mechanics and actionable intelligence
        narrative = parsed.get("mechanics", "")
        if parsed.get("actionable_intelligence"):
            narrative += "\n\nActionable: " + "; ".join(parsed["actionable_intelligence"])

        return {
            "primary_mechanic": primary_mechanic,
            "who": who,
            "whom": whom,
            "what": what,
            "confidence": confidence,
            "narrative": narrative,
            "parsed_response": parsed,
        }

    # Helper methods
    def _classify_gex_regime(self, net_gex: float, spot_price: float) -> str:
        """Classify GEX regime."""
        positive_high = self.gex_thresholds.get("positive_high", 5e9)
        negative_high = self.gex_thresholds.get("negative_high", -5e9)

        if net_gex > positive_high:
            return "POSITIVE_GAMMA_HIGH"
        elif net_gex > 0:
            return "POSITIVE_GAMMA_LOW"
        elif net_gex > negative_high:
            return "NEGATIVE_GAMMA_LOW"
        else:
            return "NEGATIVE_GAMMA_HIGH"

    def _analyze_gamma_concentration(self, options_data: pd.DataFrame, spot_price: float) -> Dict:
        """Analyze gamma concentration around spot."""
        if options_data.empty:
            return {}

        try:
            # Find strikes near spot (within 2%)
            near_strikes = options_data[
                (options_data["strike"] >= spot_price * 0.98) & (options_data["strike"] <= spot_price * 1.02)
            ]

            total_gamma = options_data["gamma"].sum() if "gamma" in options_data.columns else 0
            near_gamma = near_strikes["gamma"].sum() if "gamma" in near_strikes.columns else 0

            return {
                "concentration_score": near_gamma / max(total_gamma, 1),
                "near_strikes_count": len(near_strikes["strike"].unique()),
                "peak_gamma_strike": (
                    options_data.loc[options_data["gamma"].idxmax(), "strike"] if "gamma" in options_data.columns else 0
                ),
            }

        except Exception as e:
            logger.error(f"Error analyzing gamma concentration: {e}")
            return {}

    def _analyze_strike_distribution(self, options_data: pd.DataFrame) -> Dict:
        """Analyze strike distribution and OI concentration."""
        if options_data.empty or "open_interest" not in options_data.columns:
            return {}

        try:
            strike_oi = options_data.groupby("strike")["open_interest"].sum()
            total_oi = strike_oi.sum()

            if total_oi == 0:
                return {}

            max_oi_strike = strike_oi.idxmax()
            max_oi_concentration = strike_oi.max() / total_oi

            return {
                "max_oi_strike": max_oi_strike,
                "max_oi_concentration": max_oi_concentration,
                "top_3_strikes": strike_oi.nlargest(3).index.tolist(),
                "oi_dispersion": strike_oi.std() / strike_oi.mean() if strike_oi.mean() > 0 else 0,
            }

        except Exception as e:
            logger.error(f"Error analyzing strike distribution: {e}")
            return {}

    def _analyze_volatility_surface(self, options_data: pd.DataFrame) -> Dict:
        """Analyze volatility surface characteristics."""
        if options_data.empty or "iv" not in options_data.columns:
            return {}

        try:
            # Separate calls and puts
            calls = options_data[options_data["type"] == "call"]
            puts = options_data[options_data["type"] == "put"]

            # Calculate skew
            atm_iv = options_data["iv"].median()
            otm_put_iv = puts[puts["delta"] < -0.3]["iv"].mean() if len(puts) > 0 else atm_iv
            otm_call_iv = calls[calls["delta"] > 0.3]["iv"].mean() if len(calls) > 0 else atm_iv

            return {
                "atm_iv": atm_iv,
                "put_skew": otm_put_iv - atm_iv,
                "call_skew": otm_call_iv - atm_iv,
                "term_structure": self._analyze_term_structure(options_data),
            }

        except Exception as e:
            logger.error(f"Error analyzing volatility surface: {e}")
            return {}

    def _analyze_term_structure(self, options_data: pd.DataFrame) -> str:
        """Analyze IV term structure."""
        if "expiry" not in options_data.columns or "iv" not in options_data.columns:
            return "unknown"

        try:
            # Group by expiry and get average IV
            options_data["expiry"] = pd.to_datetime(options_data["expiry"])
            term_structure = options_data.groupby("expiry")["iv"].mean().sort_index()

            if len(term_structure) < 2:
                return "insufficient_data"

            # Check if contango or backwardation
            if term_structure.iloc[-1] > term_structure.iloc[0]:
                return "contango"
            else:
                return "backwardation"

        except Exception as e:
            logger.error(f"Error analyzing term structure: {e}")
            return "error"

    def _calculate_skew(self, options_data: pd.DataFrame) -> float:
        """Calculate skew for options."""
        if options_data.empty or "iv" not in options_data.columns:
            return 0.0

        try:
            # Simple skew: OTM vs ATM IV difference
            if "delta" in options_data.columns:
                otm = options_data[abs(options_data["delta"]) < 0.3]
                atm = options_data[abs(options_data["delta"]) >= 0.3]

                if len(otm) > 0 and len(atm) > 0:
                    return otm["iv"].mean() - atm["iv"].mean()

        except Exception as e:
            logger.error(f"Error calculating skew: {e}")

        return 0.0

    def _is_opex_week(self, date) -> bool:
        """Check if date is in OPEX week."""
        # Use the date_utils function
        return is_opex_week(date)

    def _days_to_next_fomc(self, date) -> int:
        """Calculate days to next FOMC meeting."""
        # Simplified - would need actual FOMC calendar
        # For now, assume FOMC every 6 weeks on Wednesday
        days_since_epoch = (date - datetime.datetime(2024, 1, 31)).days
        days_until_fomc = 42 - (days_since_epoch % 42)
        return days_until_fomc

    def _get_fed_context(self, date) -> Optional[Dict]:
        """Get Fed context for the date."""
        # Would integrate with Fed calendar/news
        # For now, return based on proximity to FOMC
        days_to_fomc = self._days_to_next_fomc(date)

        if days_to_fomc <= 3:
            return {"event": "FOMC_WEEK", "days_to_event": days_to_fomc, "blackout": True, "impact": "HIGH"}
        elif days_to_fomc <= 10:
            return {
                "event": "PRE_FOMC",
                "days_to_event": days_to_fomc,
                "blackout": days_to_fomc <= 7,
                "impact": "MEDIUM",
            }

        return None

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure."""
        return {
            "date": None,
            "mechanics_interpretation": {
                "primary_mechanic": "No data",
                "who": "Unknown",
                "whom": "Unknown",
                "what": "No analysis possible",
                "confidence": 0,
                "narrative": "Insufficient data for analysis",
            },
            "actionable_signal": {"action": "NO_TRADE", "confidence": 0, "rationale": "No data available"},
            "patterns_detected": [],
            "gex_metrics": {},
            "confidence": 0,
        }

    def _populate_database_entry(self, conn, date_str: str, gex_metrics: Dict):
        """Populate database with calculated GEX metrics.

        Handles both daily and intra-day data population.
        """
        try:
            # Determine regime using configured thresholds
            net_gex = gex_metrics.get("net_gex", 0)
            positive_high = self.gex_thresholds.get("positive_high", 5e9)
            negative_high = self.gex_thresholds.get("negative_high", -5e9)

            if net_gex < negative_high:
                regime = "NEGATIVE_GAMMA_HIGH"
            elif net_gex < 0:
                regime = "NEGATIVE_GAMMA_LOW"
            elif net_gex > positive_high:
                regime = "POSITIVE_GAMMA_HIGH"
            else:
                regime = "POSITIVE_GAMMA_LOW"

            # Determine if this is intra-day timestamp or daily date
            is_intraday = " " in date_str and ":" in date_str

            cursor = conn.cursor()

            if is_intraday:
                # Insert into intraday table
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO intraday_gex_metrics
                    (symbol, timestamp, spot_price, total_gex, net_call_gex, net_put_gex,
                     gamma_flip_point, flip_ratio, gex_regime, data_quality_score,
                     options_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.symbol,
                        date_str,  # This is actually a timestamp for intraday
                        gex_metrics.get("spot_price", 0),
                        net_gex,
                        gex_metrics.get("call_gamma", 0),
                        gex_metrics.get("put_gamma", 0),
                        gex_metrics.get("flip_level", 0),
                        (
                            gex_metrics.get("gamma_concentration", {}).get("concentration_score", 0)
                            if isinstance(gex_metrics.get("gamma_concentration"), dict)
                            else gex_metrics.get("gamma_concentration", 0)
                        ),
                        regime,
                        1.0,  # data_quality_score
                        # options_count (would need to count from options_data)
                        0,
                        now_iso(),
                    ),
                )
            else:
                # Insert into daily table
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO daily_gex_metrics
                    (symbol, date, spot_price, total_gex, net_call_gex, net_put_gex,
                     gamma_flip_point, flip_ratio, gex_regime, data_quality_score,
                     options_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.symbol,
                        date_str,
                        gex_metrics.get("spot_price", 0),
                        net_gex,
                        gex_metrics.get("call_gamma", 0),
                        gex_metrics.get("put_gamma", 0),
                        gex_metrics.get("flip_level", 0),
                        (
                            gex_metrics.get("gamma_concentration", {}).get("concentration_score", 0)
                            if isinstance(gex_metrics.get("gamma_concentration"), dict)
                            else gex_metrics.get("gamma_concentration", 0)
                        ),
                        regime,
                        1.0,  # data_quality_score
                        # options_count (would need to count from options_data)
                        0,
                        now_iso(),
                    ),
                )

            conn.commit()
            table_type = "intraday" if is_intraday else "daily"
            logger.debug(f"Populated {table_type} database entry for {self.symbol} {date_str}")

        except Exception as e:
            logger.error(f"Failed to populate database entry for {date_str}: {e}")
            # Don't raise - we still want to return the calculated data
