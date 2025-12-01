"""AutoGen-based Market Mechanics LLM Integration Uses AutoGen framework for consistent LLM interaction across the
system."""

import asyncio
import logging
import os
from typing import Any, Dict

# AutoGen imports
from autogen_core.models import SystemMessage, UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import config
from src.utils.config_manager import get_config

logger = logging.getLogger(__name__)


class AutoGenMarketMechanics:
    """AutoGen-based market mechanics interpreter using existing infrastructure."""

    def __init__(self, model: str = None, temperature: float = None):
        """Initialize AutoGen OpenAI client for mechanics interpretation.

        Args:
            model: Model to use (defaults to config)
            temperature: Temperature for generation (defaults to config)
        """
        # Load configuration
        config = get_config()

        # Load LLM config values
        self.model = model or config.get("llm_market_mechanics.autogen_client.default_model", "gpt-4o")
        temperature = (
            temperature
            if temperature is not None
            else config.get("llm_market_mechanics.autogen_client.default_temperature", 0.3)
        )
        timeout = config.get("llm_market_mechanics.autogen_client.timeout_seconds", 30)
        max_retries = config.get("llm_market_mechanics.autogen_client.max_retries", 3)
        analysis_tokens = config.get("llm_market_mechanics.autogen_client.analysis_tokens", 4000)
        top_p = config.get("llm_market_mechanics.autogen_client.top_p", 0.95)

        # Load confidence mapping
        self.confidence_high = config.get("llm_market_mechanics.response_parsing.confidence_high", 80)
        self.confidence_medium = config.get("llm_market_mechanics.response_parsing.confidence_medium", 60)
        self.confidence_low = config.get("llm_market_mechanics.response_parsing.confidence_low", 40)
        self.confidence_default = config.get("llm_market_mechanics.response_parsing.confidence_default", 50)

        # Load system prompt from config
        self.system_prompt = config.get(
            "llm_market_mechanics.system_prompts.mechanics_analyst", "You are a market mechanics analyst."
        )

        # Get API key from environment (not stored in config for security)
        api_key = os.getenv("OPEN_AI_KEY") or os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OpenAI API key not found in environment (OPEN_AI_KEY or OPENAI_API_KEY)")

        # Initialize AutoGen OpenAI client with model-specific parameters
        client_params = {"model": self.model, "api_key": api_key, "timeout": timeout, "max_retries": max_retries}

        # Configure token limits based on model type
        if "o3" in self.model or "o4" in self.model or "gpt-5" in self.model:
            # O3/O4/GPT-5 models use different parameters
            client_params["max_completion_tokens"] = analysis_tokens
            # These models don't support temperature or top_p
        else:
            # Standard models (GPT-4o, GPT-4o-mini, etc.)
            client_params["max_tokens"] = analysis_tokens
            client_params["temperature"] = temperature
            client_params["top_p"] = top_p

        self.client = OpenAIChatCompletionClient(**client_params)

        logger.info(f"AutoGenMarketMechanics initialized with {self.model}")

    async def interpret_mechanics_async(self, prompt: str) -> Dict[str, Any]:
        """Async method to get LLM interpretation of market mechanics.

        Args:
            prompt: Formatted prompt with GEX data and context

        Returns:
            Dictionary with mechanics interpretation
        """
        try:
            # Build message sequence
            messages = [SystemMessage(content=self.system_prompt), UserMessage(content=prompt, source="user")]

            # Call AutoGen client
            response = await self.client.create(messages=messages)

            # Extract content from response
            content = self._extract_content(response)

            # Parse the response
            return self._parse_llm_response(content)

        except Exception as e:
            logger.error(f"AutoGen LLM interpretation failed: {e}")
            return self._error_response(str(e))

    def interpret_mechanics(self, prompt: str) -> Dict[str, Any]:
        """Synchronous wrapper for mechanics interpretation.

        Args:
            prompt: Formatted prompt with GEX data and context

        Returns:
            Dictionary with mechanics interpretation
        """
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in a loop, need to run in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.interpret_mechanics_async(prompt))
                return future.result()
        except RuntimeError:
            # No event loop, we can create one
            return asyncio.run(self.interpret_mechanics_async(prompt))

    def generate(self, prompt: str) -> str:
        """Simple generation for compatibility with existing code.

        Args:
            prompt: Text prompt

        Returns:
            Raw string response
        """
        result = self.interpret_mechanics(prompt)
        return result.get("narrative", "")

    def _extract_content(self, response: Any) -> str:
        """Extract content from AutoGen response object.

        Args:
            response: Response from AutoGen client

        Returns:
            Content string
        """
        if not response:
            return "No response generated"

        # Check for content attribute (AutoGen response format)
        if hasattr(response, "content"):
            if isinstance(response.content, str):
                return response.content
            elif isinstance(response.content, list):
                # If content is a list (tool calls), extract text
                text_parts = []
                for item in response.content:
                    if hasattr(item, "text"):
                        text_parts.append(item.text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                return " ".join(text_parts)
            else:
                return str(response.content)

        # Fall back to string representation
        return str(response)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format.

        Args:
            response: Raw LLM response

        Returns:
            Structured interpretation dictionary
        """
        parsed = {
            "who": "Unknown",
            "whom": "Unknown",
            "what": "Unknown",
            "confidence": 50,
            "narrative": response,
            "mechanics": "",
        }

        # Parse structured elements from response
        lines = response.split("\n")
        for line in lines:
            line_upper = line.upper()
            if line_upper.startswith("WHO:"):
                parsed["who"] = line.split(":", 1)[1].strip()
            elif line_upper.startswith("WHOM:"):
                parsed["whom"] = line.split(":", 1)[1].strip()
            elif line_upper.startswith("WHAT:"):
                parsed["what"] = line.split(":", 1)[1].strip()
            elif line_upper.startswith("MECHANICS:"):
                parsed["mechanics"] = line.split(":", 1)[1].strip()
            elif line_upper.startswith("CONFIDENCE:"):
                conf_str = line.split(":", 1)[1].strip().upper()

                # Try to extract numeric confidence first
                import re

                numeric_match = re.search(r"(\d+)", conf_str)
                if numeric_match:
                    parsed["confidence"] = min(int(numeric_match.group(1)), 100)
                # Fallback to text-based confidence (use config values)
                elif "HIGH" in conf_str:
                    parsed["confidence"] = self.confidence_high
                elif "MEDIUM" in conf_str or "MED" in conf_str:
                    parsed["confidence"] = self.confidence_medium
                elif "LOW" in conf_str:
                    parsed["confidence"] = self.confidence_low
                else:
                    parsed["confidence"] = self.confidence_default

        # Create a concise narrative if we have the components
        if parsed["who"] != "Unknown" and parsed["what"] != "Unknown":
            parsed["key_insight"] = f"{parsed['who']} forcing {parsed['whom']} to {parsed['what']}"

        return parsed

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create error response structure."""
        return {
            "who": "Error",
            "whom": "N/A",
            "what": "N/A",
            "confidence": 0,
            "narrative": f"LLM interpretation unavailable: {error_msg}",
            "error": True,
        }
