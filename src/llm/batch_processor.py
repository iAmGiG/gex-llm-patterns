"""Batch LLM Processing System Implements Issue #70: Batch LLM API Optimization for continuous experiment framework.

Reduces API calls by 5x through weekly batching while maintaining individual day analysis quality.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder
from src.utils.config_manager import get_config
from src.utils.date_utils import date_range_trading_days, now_iso, parse_date_string

logger = logging.getLogger(__name__)


class BatchLLMProcessor:
    """Batch LLM processor for efficient options analysis.

    Features:
    - Weekly batching (5 trading days per LLM call)
    - Robust response parsing with individual day extraction
    - Graceful fallback to individual calls on batch failures
    - Context preservation across trading days
    - Cost optimization: 80% reduction in API calls
    """

    def __init__(self, llm_provider, batch_size: int = None, max_retries: int = None):
        """Initialize batch processor.

        Args:
            llm_provider: LLM client (O3-mini, GPT-4o, etc.)
            batch_size: Number of trading days per batch (default from config: 5 for weekly)
            max_retries: Maximum retry attempts for failed batches (default from config: 3)
        """
        config = get_config()

        self.llm = llm_provider
        self.batch_size = (
            batch_size
            if batch_size is not None
            else config.get("llm_market_mechanics.batch_processor.default_batch_size", 5)
        )
        self.max_retries = (
            max_retries
            if max_retries is not None
            else config.get("llm_market_mechanics.batch_processor.max_retries", 3)
        )
        self.prompt_builder = MechanicsPromptBuilder()

        # Batch processing state
        self.prepared_analyses = {}  # Store batch results for fast retrieval
        self.batch_preparation_complete = False
        self.failed_batches = []

        logger.info(f"Initialized BatchLLMProcessor with batch_size={batch_size}")

    def prepare_batch_analysis(
        self, start_date: str, end_date: str, symbol: str, market_data: Dict, gex_data: Dict
    ) -> Dict:
        """Prepare batch analysis for entire date range.

        This is the main optimization: instead of 252 individual LLM calls per year,
        we make ~52 weekly batch calls.

        Args:
            start_date: Start date for batch preparation
            end_date: End date for batch preparation
            symbol: Trading symbol
            market_data: Market data dictionary
            gex_data: GEX data dictionary

        Returns:
            Prepared batch analysis results
        """
        logger.info(f"Starting batch preparation for {symbol}: {start_date} to {end_date}")

        # Generate weekly chunks
        weekly_chunks = self._generate_weekly_chunks(start_date, end_date)
        logger.info(f"Generated {len(weekly_chunks)} weekly chunks for processing")

        # Process each week in batch
        total_batches = len(weekly_chunks)
        successful_batches = 0

        for i, week_chunk in enumerate(weekly_chunks):
            logger.info(f"Processing batch {i+1}/{total_batches}: {week_chunk[0]} to {week_chunk[-1]}")

            try:
                # Prepare weekly data
                weekly_data = self._prepare_weekly_data(week_chunk, symbol, market_data, gex_data)

                if not weekly_data:
                    logger.warning(f"No data available for week chunk: {week_chunk}")
                    continue

                # Generate batch LLM analysis
                batch_analysis = self._process_weekly_batch(weekly_data, week_chunk)

                if batch_analysis:
                    # Store individual day results
                    for date, analysis in batch_analysis.items():
                        self.prepared_analyses[date] = analysis

                    successful_batches += 1
                    logger.info(f"Successfully processed batch {i+1}: {len(batch_analysis)} days analyzed")
                else:
                    logger.warning(f"Failed to process batch {i+1}")
                    self.failed_batches.append(week_chunk)

            except Exception as e:
                logger.error(f"Error processing batch {i+1}: {e}")
                self.failed_batches.append(week_chunk)

        # Mark preparation complete
        self.batch_preparation_complete = True

        logger.info(f"Batch preparation complete: {successful_batches}/{total_batches} successful")
        logger.info(f"Prepared analyses for {len(self.prepared_analyses)} trading days")

        if self.failed_batches:
            logger.warning(f"Failed batches: {len(self.failed_batches)} - will use individual fallback")

        return {
            "total_batches": total_batches,
            "successful_batches": successful_batches,
            "prepared_days": len(self.prepared_analyses),
            "failed_batches": len(self.failed_batches),
            "batch_preparation_complete": self.batch_preparation_complete,
        }

    def get_day_analysis(self, date: str, market_data: Dict, gex_data: Dict, symbol: str = "SPY") -> Optional[Dict]:
        """Get analysis for specific day with 3-tier fallback.

        Tier 1: Batch prepared data (90%+ of cases)
        Tier 2: Individual LLM call (cache miss or batch failure)
        Tier 3: Neutral analysis (emergency fallback)

        Args:
            date: Trading date (YYYY-MM-DD)
            market_data: Market data for the date
            gex_data: GEX data for the date
            symbol: Trading symbol

        Returns:
            LLM analysis for the trading day
        """
        # Tier 1: Use batch prepared data (fastest)
        if self.batch_preparation_complete and date in self.prepared_analyses:
            logger.debug(f"Using batch prepared analysis for {date}")
            return self.prepared_analyses[date]

        # Tier 2: Individual LLM call (fallback)
        logger.info(f"Batch data not available for {date}, using individual LLM call")
        try:
            individual_analysis = self._process_individual_day(date, market_data, gex_data, symbol)
            if individual_analysis:
                # Cache for future use
                self.prepared_analyses[date] = individual_analysis
                return individual_analysis
        except Exception as e:
            logger.error(f"Individual LLM call failed for {date}: {e}")

        # Tier 3: Neutral fallback (emergency)
        logger.warning(f"All LLM methods failed for {date}, using neutral fallback")
        return {
            "signal_type": "neutral",
            "confidence": 0.0,
            "reasoning": f"LLM analysis unavailable for {date} - batch and individual calls failed",
            "analysis_method": "fallback_neutral",
            "metadata": {"date": date, "symbol": symbol, "fallback_reason": "llm_failure"},
        }

    def _generate_weekly_chunks(self, start_date: str, end_date: str) -> List[List[str]]:
        """Generate weekly chunks of trading days using robust date utilities."""
        try:
            # Use robust date parsing that supports obfuscated dates
            start = parse_date_string(start_date)
            end = parse_date_string(end_date)

            # Use date_utils function for consistent trading day generation
            trading_days = date_range_trading_days(start_date, end_date)
        except Exception as e:
            logger.error(f"Date parsing failed for {start_date} to {end_date}: {e}")
            # Fallback to basic parsing
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            business_days = pd.bdate_range(start=start, end=end)
            trading_days = [day.strftime("%Y-%m-%d") for day in business_days]

        # Group into weekly chunks
        weekly_chunks = []
        for i in range(0, len(trading_days), self.batch_size):
            chunk = trading_days[i : i + self.batch_size]
            if chunk:  # Only add non-empty chunks
                weekly_chunks.append(chunk)

        return weekly_chunks

    def _prepare_weekly_data(
        self, week_chunk: List[str], symbol: str, market_data: Dict, gex_data: Dict
    ) -> Optional[Dict]:
        """Prepare data for weekly batch processing."""
        weekly_data = {}

        for date in week_chunk:
            # Get market data for date
            day_market_data = market_data.get(date)
            if not day_market_data:
                logger.debug(f"No market data for {date}")
                continue

            # Get GEX data for date
            day_gex_data = gex_data.get(date)
            if not day_gex_data:
                logger.debug(f"No GEX data for {date}")
                continue

            weekly_data[date] = {"market_data": day_market_data, "gex_data": day_gex_data, "symbol": symbol}

        return weekly_data if weekly_data else None

    def _process_weekly_batch(self, weekly_data: Dict, week_chunk: List[str]) -> Optional[Dict]:
        """Process entire week in single LLM call."""
        try:
            # Build batch prompt
            batch_prompt = self._build_batch_prompt(weekly_data, week_chunk)

            # Generate LLM response
            logger.debug(f"Sending batch LLM request for {len(week_chunk)} days")
            response = self.llm.generate(batch_prompt)

            if not response:
                logger.error("Empty response from batch LLM call")
                return None

            # Parse response into individual day analyses
            parsed_analyses = self._parse_batch_response(response, week_chunk)

            if not parsed_analyses:
                logger.error("Failed to parse batch LLM response")
                return None

            logger.info(f"Successfully parsed {len(parsed_analyses)} day analyses from batch")
            return parsed_analyses

        except Exception as e:
            logger.error(f"Batch LLM processing failed: {e}")
            return None

    def _build_batch_prompt(self, weekly_data: Dict, week_chunk: List[str]) -> str:
        """Build optimized batch prompt for weekly analysis."""
        prompt_parts = []

        # System prompt
        prompt_parts.append(
            """You are an expert options trader analyzing GEX (Gamma Exposure) patterns for trading opportunities.

Analyze the following multi-day trading sequence and provide WHO/WHOM/WHAT market mechanics analysis for each day.

For each day, identify:
1. WHO is forcing action (dealers, institutions, retail, etc.)
2. WHOM they are forcing (market makers, other participants)
3. WHAT action is being forced (buying, selling, hedging, etc.)
4. Trading signal: 'long', 'short', or 'neutral'
5. Confidence level: 0.0 to 1.0
6. Brief reasoning (2-3 sentences max)

IMPORTANT: Return your analysis as JSON with this exact structure:
{
  "YYYY-MM-DD": {
    "signal_type": "long|short|neutral",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "who": "who is forcing",
    "whom": "whom they force",
    "what": "what action forced"
  }
}"""
        )

        # Add weekly trading sequence
        prompt_parts.append("\n\nTRADING SEQUENCE ANALYSIS:")

        for i, date in enumerate(week_chunk):
            if date not in weekly_data:
                continue

            day_data = weekly_data[date]
            market = day_data["market_data"]
            gex = day_data["gex_data"]

            # Format day information
            day_info = f"""
Day {i+1} ({date}):
- Price: ${market.get('close', market.get('price', 'N/A'))}
- GEX: {gex.get('net_gex', 0):,.0f}
- Regime: {gex.get('gex_regime', 'UNKNOWN')}
- Volume: {market.get('volume', 'N/A')}"""

            # Add options-specific data if available
            if "options_data" in gex:
                options_info = gex["options_data"]
                if isinstance(options_info, dict) and options_info:
                    total_volume = sum(opt.get("volume", 0) for opt in options_info.values() if isinstance(opt, dict))
                    day_info += f"\n- Options Volume: {total_volume:,}"

            prompt_parts.append(day_info)

        # Add context and instructions
        prompt_parts.append(
            f"""

CONTEXT: This is a {len(week_chunk)}-day sequence showing market mechanics evolution.
Consider day-to-day patterns and how dealer positioning changes affect subsequent days.

Provide JSON analysis for each day focusing on actionable trading insights."""
        )

        return "\n".join(prompt_parts)

    def _parse_batch_response(self, response: str, week_chunk: List[str]) -> Optional[Dict]:
        """Parse batch LLM response into individual day analyses."""
        try:
            # Extract JSON from response (handle various formats)
            json_text = self._extract_json_from_response(response)

            if not json_text:
                logger.error("Could not extract JSON from batch response")
                return None

            # Parse JSON
            batch_analysis = json.loads(json_text)

            # Validate and clean up parsed data
            cleaned_analyses = {}
            for date in week_chunk:
                if date in batch_analysis:
                    day_analysis = batch_analysis[date]

                    # Validate required fields
                    if self._validate_day_analysis(day_analysis):
                        cleaned_analyses[date] = {
                            "signal_type": day_analysis.get("signal_type", "neutral"),
                            "confidence": float(day_analysis.get("confidence", 0.0)),
                            "reasoning": day_analysis.get("reasoning", "No reasoning provided"),
                            "who": day_analysis.get("who", "Unknown"),
                            "whom": day_analysis.get("whom", "Unknown"),
                            "what": day_analysis.get("what", "Unknown"),
                            "analysis_method": "batch_llm",
                            "batch_date": now_iso(),
                            "metadata": {"date": date, "batch_size": len(week_chunk)},
                        }
                    else:
                        logger.warning(f"Invalid analysis structure for {date}")
                else:
                    logger.warning(f"Missing analysis for {date} in batch response")

            return cleaned_analyses if cleaned_analyses else None

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in batch response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing batch response: {e}")
            return None

    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extract JSON content from LLM response."""
        import re

        # Try to find JSON block (between { and })
        json_pattern = r"\{.*\}"
        json_match = re.search(json_pattern, response, re.DOTALL)

        if json_match:
            return json_match.group(0)

        # Try markdown code block
        code_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        code_match = re.search(code_block_pattern, response, re.DOTALL | re.IGNORECASE)

        if code_match:
            return code_match.group(1)

        # Return original if no patterns found
        return response.strip()

    def _validate_day_analysis(self, analysis: Dict) -> bool:
        """Validate individual day analysis structure."""
        required_fields = ["signal_type", "confidence", "reasoning"]

        for field in required_fields:
            if field not in analysis:
                return False

        # Validate signal_type
        valid_signals = ["long", "short", "neutral"]
        if analysis["signal_type"] not in valid_signals:
            return False

        # Validate confidence
        try:
            confidence = float(analysis["confidence"])
            if not (0.0 <= confidence <= 1.0):
                return False
        except (ValueError, TypeError):
            return False

        return True

    def _process_individual_day(self, date: str, market_data: Dict, gex_data: Dict, symbol: str) -> Optional[Dict]:
        """Fallback: process individual day with single LLM call."""
        try:
            # Build individual day prompt
            individual_prompt = self.prompt_builder.build_analysis_prompt(
                market_data=market_data, gex_data=gex_data, symbol=symbol, date=date
            )

            # Generate LLM response
            response = self.llm.generate(individual_prompt)

            if not response:
                return None

            # Parse individual response (simpler than batch)
            analysis = self._parse_individual_response(response, date)

            if analysis:
                analysis["analysis_method"] = "individual_llm"
                analysis["metadata"] = {"date": date, "symbol": symbol, "fallback": True}

            return analysis

        except Exception as e:
            logger.error(f"Individual day processing failed for {date}: {e}")
            return None

    def _parse_individual_response(self, response: str, date: str) -> Optional[Dict]:
        """Parse individual LLM response using same logic as batch parsing."""
        try:
            # Extract JSON from response
            json_text = self._extract_json_from_response(response)

            if not json_text:
                logger.warning(f"Could not extract JSON from individual response for {date}")
                return self._create_fallback_analysis(date, "json_extraction_failed")

            # Parse JSON
            analysis = json.loads(json_text)

            # Handle both single analysis and date-keyed analysis
            if date in analysis:
                day_analysis = analysis[date]
            elif isinstance(analysis, dict) and "signal_type" in analysis:
                day_analysis = analysis
            else:
                logger.warning(f"Unexpected response format for {date}")
                return self._create_fallback_analysis(date, "unexpected_format")

            # Validate and clean up
            if self._validate_day_analysis(day_analysis):
                return {
                    "signal_type": day_analysis.get("signal_type", "neutral"),
                    "confidence": float(day_analysis.get("confidence", 0.0)),
                    "reasoning": day_analysis.get("reasoning", "No reasoning provided"),
                    "who": day_analysis.get("who", "Unknown"),
                    "whom": day_analysis.get("whom", "Unknown"),
                    "what": day_analysis.get("what", "Unknown"),
                    "analysis_method": "individual_llm",
                    "response_timestamp": now_iso(),
                    "metadata": {"date": date, "parsing_method": "individual"},
                }
            else:
                logger.warning(f"Invalid analysis structure for {date}")
                return self._create_fallback_analysis(date, "validation_failed")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for {date}: {e}")
            return self._create_fallback_analysis(date, "json_decode_error")
        except Exception as e:
            logger.error(f"Error parsing individual response for {date}: {e}")
            return self._create_fallback_analysis(date, "parsing_error")

    def _create_fallback_analysis(self, date: str, reason: str) -> Dict:
        """Create fallback analysis when parsing fails."""
        return {
            "signal_type": "neutral",
            "confidence": 0.0,
            "reasoning": f"Individual analysis parsing failed for {date}: {reason}",
            "analysis_method": "individual_fallback",
            "fallback_reason": reason,
            "response_timestamp": now_iso(),
            "metadata": {"date": date, "fallback": True},
        }

    def get_batch_statistics(self) -> Dict:
        """Get batch processing performance statistics."""
        return {
            "batch_preparation_complete": self.batch_preparation_complete,
            "prepared_analyses_count": len(self.prepared_analyses),
            "failed_batches_count": len(self.failed_batches),
            "batch_size": self.batch_size,
            "api_call_reduction_pct": (1 - 1 / self.batch_size) * 100 if self.batch_size > 1 else 0,
        }
