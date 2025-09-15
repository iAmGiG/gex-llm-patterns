"""
AutoGen-based Market Mechanics LLM Integration
Uses AutoGen framework for consistent LLM interaction across the system
"""

import os
import asyncio
import logging
from typing import Dict, Any

# AutoGen imports
from autogen_core.models import UserMessage, SystemMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import config loader
from config.config_loader import ConfigLoader

logger = logging.getLogger(__name__)


class AutoGenMarketMechanics:
    """AutoGen-based market mechanics interpreter using existing infrastructure."""

    def __init__(self, model: str = None, temperature: float = 0.3):
        """
        Initialize AutoGen OpenAI client for mechanics interpretation.

        Args:
            model: Model to use (defaults to config OPEN_MODEL)
            temperature: Temperature for generation (lower = more consistent)
        """
        # Load configuration
        config_loader = ConfigLoader()

        # Get model and API key from config
        self.model = model or os.getenv("OPEN_MODEL", config_loader.get("OPEN_MODEL", "gpt-4o-mini"))
        api_key = os.getenv("OPEN_AI_KEY", config_loader.get("OPEN_AI_KEY"))

        if not api_key:
            # Try alternative key names
            api_key = os.getenv("OPENAI_API_KEY", config_loader.get("OPENAI_API_KEY"))

        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment")

        # Initialize AutoGen OpenAI client
        self.client = OpenAIChatCompletionClient(
            model=self.model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=1000,
            top_p=0.95,
            timeout=30,
            max_retries=3
        )

        self.system_prompt = """You are a market mechanics analyst specializing in dealer positioning and forced hedging flows.

Your task is to identify WHO is forcing WHOM to do WHAT in the market based on gamma exposure (GEX) data.

Focus on:
1. Dealer hedging mechanics (forced buying/selling due to gamma)
2. Squeeze setups (aggressive positioning to force dealer flows)
3. Pin dynamics (large OI creating price magnetism)
4. Trap patterns (dealers being flipped from long to short gamma)

Provide specific, actionable intelligence about market mechanics.
Be concise and focus on causality chains (X leads to Y leads to Z).

Format your response as:
WHO: [Identify the forcing party - dealers/institutions/retail]
WHOM: [Identify who is being forced to act]
WHAT: [Specific forced action that will occur]
MECHANICS: [Brief explanation of the causal chain]
CONFIDENCE: [High/Medium/Low based on data clarity]"""

        logger.info(f"AutoGenMarketMechanics initialized with {self.model}")

    async def interpret_mechanics_async(self, prompt: str) -> Dict[str, Any]:
        """
        Async method to get LLM interpretation of market mechanics.

        Args:
            prompt: Formatted prompt with GEX data and context

        Returns:
            Dictionary with mechanics interpretation
        """
        try:
            # Build message sequence
            messages = [
                SystemMessage(content=self.system_prompt),
                UserMessage(content=prompt, source="user")
            ]

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
        """
        Synchronous wrapper for mechanics interpretation.

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
        """
        Simple generation for compatibility with existing code.

        Args:
            prompt: Text prompt

        Returns:
            Raw string response
        """
        result = self.interpret_mechanics(prompt)
        return result.get('narrative', '')

    def _extract_content(self, response: Any) -> str:
        """
        Extract content from AutoGen response object.

        Args:
            response: Response from AutoGen client

        Returns:
            Content string
        """
        if not response:
            return "No response generated"

        # Check for content attribute (AutoGen response format)
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                return response.content
            elif isinstance(response.content, list):
                # If content is a list (tool calls), extract text
                text_parts = []
                for item in response.content:
                    if hasattr(item, 'text'):
                        text_parts.append(item.text)
                    elif isinstance(item, str):
                        text_parts.append(item)
                return ' '.join(text_parts)
            else:
                return str(response.content)

        # Fall back to string representation
        return str(response)

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.

        Args:
            response: Raw LLM response

        Returns:
            Structured interpretation dictionary
        """
        parsed = {
            'who': 'Unknown',
            'whom': 'Unknown',
            'what': 'Unknown',
            'confidence': 50,
            'narrative': response,
            'mechanics': ''
        }

        # Parse structured elements from response
        lines = response.split('\n')
        for line in lines:
            line_upper = line.upper()
            if line_upper.startswith('WHO:'):
                parsed['who'] = line.split(':', 1)[1].strip()
            elif line_upper.startswith('WHOM:'):
                parsed['whom'] = line.split(':', 1)[1].strip()
            elif line_upper.startswith('WHAT:'):
                parsed['what'] = line.split(':', 1)[1].strip()
            elif line_upper.startswith('MECHANICS:'):
                parsed['mechanics'] = line.split(':', 1)[1].strip()
            elif line_upper.startswith('CONFIDENCE:'):
                conf_str = line.split(':', 1)[1].strip().upper()
                if 'HIGH' in conf_str:
                    parsed['confidence'] = 80
                elif 'MEDIUM' in conf_str or 'MED' in conf_str:
                    parsed['confidence'] = 60
                elif 'LOW' in conf_str:
                    parsed['confidence'] = 40
                else:
                    parsed['confidence'] = 50

        # Create a concise narrative if we have the components
        if parsed['who'] != 'Unknown' and parsed['what'] != 'Unknown':
            parsed['key_insight'] = f"{parsed['who']} forcing {parsed['whom']} to {parsed['what']}"

        return parsed

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create error response structure."""
        return {
            'who': 'Error',
            'whom': 'N/A',
            'what': 'N/A',
            'confidence': 0,
            'narrative': f"LLM interpretation unavailable: {error_msg}",
            'error': True
        }

    def estimate_cost(self, input_tokens: int = 500, output_tokens: int = 200) -> float:
        """
        Estimate cost for an API call.

        Args:
            input_tokens: Estimated input tokens (default 500)
            output_tokens: Estimated output tokens (default 200)

        Returns:
            Estimated cost in USD
        """
        # Pricing based on model
        if 'gpt-4o-mini' in self.model:
            # gpt-4o-mini pricing
            input_cost = (input_tokens * 0.15) / 1_000_000
            output_cost = (output_tokens * 0.60) / 1_000_000
        elif 'gpt-4' in self.model:
            # gpt-4 pricing (more expensive)
            input_cost = (input_tokens * 30) / 1_000_000
            output_cost = (output_tokens * 60) / 1_000_000
        else:
            # Default/unknown model - use gpt-3.5 pricing
            input_cost = (input_tokens * 0.50) / 1_000_000
            output_cost = (output_tokens * 1.50) / 1_000_000

        return input_cost + output_cost