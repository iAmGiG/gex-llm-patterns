"""
Market Mechanics LLM Integration
OpenAI integration for market mechanics interpretation using gpt-4o-mini
"""

import os
import logging
import json
from typing import Dict, Optional, Any
from openai import OpenAI
from pathlib import Path

logger = logging.getLogger(__name__)


class MarketMechanicsLLM:
    """OpenAI integration for market mechanics interpretation using gpt-4o-mini"""

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.3):
        """
        Initialize OpenAI client for mechanics interpretation.

        Using gpt-4o-mini for cost efficiency:
        - Input: $0.15 per 1M tokens
        - Output: $0.60 per 1M tokens
        - ~500 tokens per analysis = ~$0.0003 per call
        """
        # Try to get API key from config or environment
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment")

        # Initialize OpenAI client (new API v1)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = 1000  # Enough for mechanics analysis

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

        logger.info(f"MarketMechanicsLLM initialized with {model}")

    def _get_api_key(self) -> Optional[str]:
        """Get API key from config file or environment."""
        # First try config file
        try:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Try different key names in config (prioritize OPEN_AI_KEY)
                    for key_name in ['OPEN_AI_KEY', 'OPENAI_API_KEY', 'RH2MAS_OPEN_AI_KEY']:
                        if key_name in config:
                            logger.debug(f"Using API key from config: {key_name}")
                            return config[key_name]
        except Exception as e:
            logger.debug(f"Could not load API key from config: {e}")

        # Fall back to environment variable
        return os.getenv('OPENAI_API_KEY')

    def interpret_mechanics(self, prompt: str) -> Dict[str, Any]:
        """
        Get LLM interpretation of market mechanics.

        Args:
            prompt: Formatted prompt with GEX data and context

        Returns:
            Dictionary with mechanics interpretation
        """
        try:
            # Create the chat completion (new API v1)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=30
            )

            # Extract and parse the response
            content = response.choices[0].message.content
            return self._parse_llm_response(content)

        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}")
            # Check for specific error types in the exception message
            error_msg = str(e).lower()
            if 'rate' in error_msg and 'limit' in error_msg:
                return self._error_response("Rate limit exceeded")
            elif 'auth' in error_msg or 'api' in error_msg and 'key' in error_msg:
                return self._error_response("Authentication failed - check API key")
            else:
                return self._error_response(str(e))

    def generate(self, prompt: str) -> str:
        """
        Simple generation for compatibility.

        Args:
            prompt: Text prompt

        Returns:
            Raw string response
        """
        result = self.interpret_mechanics(prompt)
        return result.get('narrative', '')

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
        # gpt-4o-mini pricing
        input_cost = (input_tokens * 0.15) / 1_000_000
        output_cost = (output_tokens * 0.60) / 1_000_000
        return input_cost + output_cost