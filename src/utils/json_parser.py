#!/usr/bin/env python3
"""Robust JSON extraction utility for LLM responses.

This module provides a multi-strategy JSON parser that handles common LLM
formatting quirks including:
- Markdown code block wrappers (```json ... ```)
- Conversational prefixes/suffixes
- Trailing commas
- Unquoted keys
- Invalid escape sequences
- Unicode characters in text fields

Issue #192: Improve JSON Parsing Robustness for Batch Results

Usage:
    from src.utils.json_parser import extract_json, RobustJSONParser

    # Simple function call
    result = extract_json(llm_response)

    # Or use the parser class for more control
    parser = RobustJSONParser()
    result = parser.parse(llm_response)
    print(parser.strategy_used)  # Shows which strategy succeeded

Author: Claude Code
Date: January 2026
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ParseStrategy(Enum):
    """Parsing strategies in order of preference."""

    STRICT = "strict"  # Direct json.loads()
    MARKDOWN_STRIP = "markdown_strip"  # Remove code blocks first
    CONVERSATIONAL_STRIP = "conversational_strip"  # Remove prefix/suffix text
    REGEX_EXTRACT = "regex_extract"  # Extract JSON object via regex
    REPAIR = "repair"  # Use json_repair library
    FAILED = "failed"  # All strategies failed


@dataclass
class ParseResult:
    """Result of JSON parsing attempt."""

    success: bool
    data: Optional[Dict[str, Any]]
    strategy: ParseStrategy
    error: Optional[str] = None
    raw_input: Optional[str] = None


class RobustJSONParser:
    """Multi-strategy JSON parser for LLM responses.

    Attempts parsing strategies in order of strictness:
    1. Strict JSON parsing
    2. Markdown code block stripping
    3. Conversational text stripping
    4. Regex-based JSON extraction
    5. json_repair library (if available)
    """

    def __init__(self, use_repair_library: bool = True):
        """Initialize parser.

        Args:
            use_repair_library: Whether to use json_repair as final fallback
        """
        self.use_repair_library = use_repair_library
        self.strategy_used: Optional[ParseStrategy] = None
        self._json_repair_available = self._check_json_repair()

    def _check_json_repair(self) -> bool:
        """Check if json_repair library is available."""
        try:
            import json_repair  # noqa: F401

            return True
        except ImportError:
            if self.use_repair_library:
                logger.debug("json_repair library not installed, repair strategy disabled")
            return False

    def parse(self, text: str) -> ParseResult:
        """Parse JSON from LLM response using multi-strategy approach.

        Args:
            text: Raw LLM response text

        Returns:
            ParseResult with parsed data and strategy used
        """
        if not text or not text.strip():
            return ParseResult(
                success=False, data=None, strategy=ParseStrategy.FAILED, error="Empty input", raw_input=text
            )

        # Try each strategy in order
        strategies = [
            (ParseStrategy.STRICT, self._try_strict),
            (ParseStrategy.MARKDOWN_STRIP, self._try_markdown_strip),
            (ParseStrategy.CONVERSATIONAL_STRIP, self._try_conversational_strip),
            (ParseStrategy.REGEX_EXTRACT, self._try_regex_extract),
        ]

        if self.use_repair_library and self._json_repair_available:
            strategies.append((ParseStrategy.REPAIR, self._try_repair))

        last_error = None
        for strategy, method in strategies:
            try:
                result = method(text)
                if result is not None:
                    self.strategy_used = strategy
                    logger.debug(f"JSON parsing succeeded with strategy: {strategy.value}")
                    return ParseResult(success=True, data=result, strategy=strategy, raw_input=text)
            except Exception as e:
                last_error = str(e)
                logger.debug(f"Strategy {strategy.value} failed: {e}")
                continue

        self.strategy_used = ParseStrategy.FAILED
        logger.warning(f"All JSON parsing strategies failed. Last error: {last_error}")
        return ParseResult(success=False, data=None, strategy=ParseStrategy.FAILED, error=last_error, raw_input=text)

    def _try_strict(self, text: str) -> Optional[Dict]:
        """Try strict JSON parsing."""
        return json.loads(text.strip())

    def _try_markdown_strip(self, text: str) -> Optional[Dict]:
        """Strip markdown code blocks and parse."""
        cleaned = self._strip_markdown(text)
        if cleaned != text.strip():
            return json.loads(cleaned)
        return None

    def _try_conversational_strip(self, text: str) -> Optional[Dict]:
        """Strip conversational prefix/suffix and parse."""
        cleaned = self._strip_conversational(text)
        if cleaned:
            return json.loads(cleaned)
        return None

    def _try_regex_extract(self, text: str) -> Optional[Dict]:
        """Extract JSON object using regex."""
        extracted = self._extract_json_object(text)
        if extracted:
            # Apply common fixes before parsing
            fixed = self._apply_common_fixes(extracted)
            return json.loads(fixed)
        return None

    def _try_repair(self, text: str) -> Optional[Dict]:
        """Use json_repair library for aggressive fixing."""
        from json_repair import repair_json

        # First extract the JSON-like content
        extracted = self._extract_json_object(text) or self._strip_markdown(text)
        repaired = repair_json(extracted, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        return None

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown code block wrappers.

        Handles:
        - ```json\n...\n```
        - ```\n...\n```
        - ``` ... ``` (inline)
        """
        text = text.strip()

        # Pattern for ```json ... ``` or ``` ... ```
        patterns = [
            r"^```json\s*\n(.*?)\n```\s*$",  # ```json block
            r"^```\s*\n(.*?)\n```\s*$",  # ``` block
            r"^```json\s*(.*?)```\s*$",  # ```json inline
            r"^```\s*(.*?)```\s*$",  # ``` inline
        ]

        for pattern in patterns:
            match = re.match(pattern, text, re.DOTALL)
            if match:
                return match.group(1).strip()

        return text

    def _strip_conversational(self, text: str) -> Optional[str]:
        """Strip conversational prefix and suffix text.

        Handles patterns like:
        - "Based on my analysis, here is the result: {...}"
        - "Here's the JSON: {...}"
        - "{...} Let me know if you need anything else."
        """
        text = text.strip()

        # Common conversational prefixes to remove
        prefix_patterns = [
            r"^(?:Based on (?:my |the )?analysis,?\s*)?(?:here(?:'s| is) (?:the |my )?(?:result|response|output|JSON|analysis)[:\s]*)",
            r"^(?:The (?:result|response|output|JSON) is[:\s]*)",
            r"^(?:I(?:'ve| have) (?:analyzed|processed|evaluated)[^{]*)",
            r"^(?:After (?:analyzing|reviewing|examining)[^{]*)",
            r"^(?:My analysis (?:shows|indicates|reveals)[:\s]*)",
        ]

        for pattern in prefix_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Common suffixes to remove (after the JSON object)
        suffix_patterns = [
            r"\s*(?:Let me know if (?:you )?(?:need|have|want)[^}]*)$",
            r"\s*(?:I hope this helps[^}]*)$",
            r"\s*(?:Please let me know[^}]*)$",
        ]

        for pattern in suffix_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        text = text.strip()

        # Verify we have JSON-like content
        if text.startswith("{") and text.endswith("}"):
            return text

        return None

    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract JSON object from text using brace matching.

        Handles nested objects by counting braces.
        """
        # Find the first { and match to closing }
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False
        end = start

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if depth == 0:
            return text[start : end + 1]

        return None

    def _apply_common_fixes(self, text: str) -> str:
        r"""Apply common fixes for LLM JSON quirks.

        Fixes:
        - Trailing commas before } or ]
        - Invalid escape sequences like \$
        - Word-based numbers (e.g., "thirty-five" -> 35)
        """
        # Fix trailing commas: ,} or ,]
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        # Fix invalid escape sequences (o4-mini quirk)
        text = text.replace(r"\$", "$")
        text = text.replace(r"\#", "#")
        text = text.replace(r"\@", "@")

        # Fix word-based confidence values (rare o4-mini quirk)
        word_to_num = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "twenty": 20,
            "thirty": 30,
            "forty": 40,
            "fifty": 50,
            "sixty": 60,
            "seventy": 70,
            "eighty": 80,
            "ninety": 90,
        }

        # Handle word-based numbers (simple and compound like "thirty-five")
        # First pass: compound numbers like "thirty-five"
        compound_pattern = r'"confidence"\s*:\s*(\w+)-(\w+)\b\s*,?'

        def replace_compound(m):
            base_word = m.group(1).lower()
            suffix_word = m.group(2).lower()
            base = word_to_num.get(base_word, 0)
            suffix = word_to_num.get(suffix_word, 0)
            return f'"confidence": {base + suffix},'

        text = re.sub(compound_pattern, replace_compound, text, flags=re.IGNORECASE)

        # Second pass: simple word numbers like "seventy"
        # Sort by length descending to match longer words first (e.g., "seventy" before "seven")
        sorted_words = sorted(word_to_num.items(), key=lambda x: len(x[0]), reverse=True)
        for word, num in sorted_words:
            # Use word boundary \b to avoid matching "seven" inside "seventy"
            simple_pattern = rf'"confidence"\s*:\s*{word}\b\s*,?'
            text = re.sub(simple_pattern, f'"confidence": {num},', text, flags=re.IGNORECASE)

        return text


def extract_json(
    text: str, use_repair: bool = True, return_strategy: bool = False
) -> Tuple[Optional[Dict], Optional[str]] | Optional[Dict]:
    """Extract JSON from LLM response text.

    Convenience function that wraps RobustJSONParser.

    Args:
        text: Raw LLM response text
        use_repair: Whether to use json_repair library as fallback
        return_strategy: If True, return (data, strategy) tuple

    Returns:
        Parsed dict if successful, None if failed.
        If return_strategy=True, returns (dict, strategy_name) tuple.

    Example:
        >>> result = extract_json('```json\\n{"key": "value"}\\n```')
        >>> print(result)
        {'key': 'value'}

        >>> result, strategy = extract_json(response, return_strategy=True)
        >>> print(f"Parsed with {strategy}")
    """
    parser = RobustJSONParser(use_repair_library=use_repair)
    result = parser.parse(text)

    if return_strategy:
        strategy_name = result.strategy.value if result.strategy else None
        return result.data, strategy_name

    return result.data


def extract_json_with_fallback(text: str, default: Optional[Dict] = None) -> Dict:
    """Extract JSON with a default fallback value.

    Args:
        text: Raw LLM response text
        default: Default value if parsing fails (default: empty dict)

    Returns:
        Parsed dict or default value
    """
    result = extract_json(text)
    if result is None:
        return default if default is not None else {}
    return result
