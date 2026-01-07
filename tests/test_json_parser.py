#!/usr/bin/env python3
"""Unit tests for robust JSON parser (Issue #192).

Tests cover the three failure cases from Phase 4 validation plus additional
edge cases for LLM response parsing.

Run with: python -m pytest tests/test_json_parser.py -v
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.json_parser import ParseStrategy, RobustJSONParser, extract_json, extract_json_with_fallback


class TestPhase4FailureCases:
    """Test cases from Phase 4 validation failures (Issue #192)."""

    def test_markdown_wrapper(self):
        """Example 1: Markdown wrapper around JSON."""
        response = """```json
{"regime_type": "persistent_negative", "confidence": 85, "reasoning": "Strong negative gamma"}
```"""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "persistent_negative"
        assert result["confidence"] == 85

    def test_conversational_prefix(self):
        """Example 2: Conversational text before JSON."""
        response = """Based on my analysis, here is the result:
{"regime_type": "persistent_negative", "confidence": 75, "reasoning": "Dealer hedging pressure"}"""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "persistent_negative"
        assert result["confidence"] == 75

    def test_trailing_comma(self):
        """Example 3: Trailing comma in JSON."""
        response = '{"regime_type": "persistent_negative", "confidence": 85,}'
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "persistent_negative"
        assert result["confidence"] == 85


class TestMarkdownStripping:
    """Test markdown code block removal."""

    def test_json_code_block(self):
        """Standard ```json code block."""
        response = '```json\n{"key": "value"}\n```'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_plain_code_block(self):
        """Plain ``` code block without language."""
        response = '```\n{"key": "value"}\n```'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_inline_code_block(self):
        """Inline code block on single line."""
        response = '```json{"key": "value"}```'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_nested_json_in_markdown(self):
        """Complex nested JSON in markdown."""
        response = """```json
{
    "regime_type": "persistent_negative",
    "confidence": 80,
    "details": {
        "magnitude": 5.2,
        "persistence": 0.85
    }
}
```"""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "persistent_negative"
        assert result["details"]["magnitude"] == 5.2


class TestConversationalStripping:
    """Test conversational prefix/suffix removal."""

    def test_here_is_prefix(self):
        """'Here is the result' prefix."""
        response = 'Here is the result: {"key": "value"}'
        result = extract_json(response)
        assert result == {"key": "value"}

    def test_analysis_prefix(self):
        """'Based on my analysis' prefix."""
        response = 'Based on my analysis, here is the JSON: {"status": "ok"}'
        result = extract_json(response)
        assert result == {"status": "ok"}

    def test_multiple_sentences_before(self):
        """Multiple sentences before JSON."""
        response = """I've analyzed the data carefully. The gamma exposure shows clear patterns.
Here is my assessment: {"regime_type": "transitional", "confidence": 45}"""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "transitional"

    def test_suffix_after_json(self):
        """Text after JSON object."""
        response = '{"key": "value"} Let me know if you need anything else.'
        result = extract_json(response)
        assert result == {"key": "value"}


class TestCommonFixes:
    """Test common JSON formatting fixes."""

    def test_trailing_comma_object(self):
        """Trailing comma before closing brace."""
        response = '{"a": 1, "b": 2,}'
        result = extract_json(response)
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma_array(self):
        """Trailing comma in array."""
        response = '{"items": [1, 2, 3,]}'
        result = extract_json(response)
        assert result == {"items": [1, 2, 3]}

    def test_invalid_escape_dollar(self):
        """Invalid \\$ escape sequence (o4-mini quirk)."""
        response = '{"reasoning": "The \\$5B threshold was exceeded"}'
        result = extract_json(response)
        assert result is not None
        assert "$5B" in result["reasoning"]

    def test_invalid_escape_hash(self):
        """Invalid \\# escape sequence."""
        response = '{"note": "Issue \\#192"}'
        result = extract_json(response)
        assert result is not None
        assert "#192" in result["note"]


class TestWordBasedNumbers:
    """Test word-to-number conversion for confidence values."""

    def test_thirty_five(self):
        """Word 'thirty-five' to 35."""
        response = '{"confidence": thirty-five, "regime_type": "low"}'
        result = extract_json(response)
        assert result is not None
        assert result["confidence"] == 35

    def test_seventy(self):
        """Word 'seventy' to 70."""
        response = '{"confidence": seventy, "regime_type": "high"}'
        result = extract_json(response)
        assert result is not None
        assert result["confidence"] == 70


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        """Empty string input."""
        result = extract_json("")
        assert result is None

    def test_whitespace_only(self):
        """Whitespace-only input."""
        result = extract_json("   \n\t  ")
        assert result is None

    def test_no_json_content(self):
        """Text with no JSON content."""
        result = extract_json("This is just plain text with no JSON.")
        assert result is None

    def test_partial_json(self):
        """Incomplete JSON object."""
        result = extract_json('{"key": "value"')
        # May or may not parse depending on repair strategy
        # Just ensure no crash
        assert result is None or isinstance(result, dict)

    def test_nested_braces_in_string(self):
        """JSON with braces inside string values."""
        response = '{"code": "function() { return {}; }"}'
        result = extract_json(response)
        assert result is not None
        assert "function()" in result["code"]

    def test_unicode_characters(self):
        """Unicode characters in JSON."""
        response = '{"message": "Analysis complete: \u2714"}'
        result = extract_json(response)
        assert result is not None
        assert "\u2714" in result["message"] or "complete" in result["message"]


class TestParserClass:
    """Test RobustJSONParser class directly."""

    def test_strategy_tracking(self):
        """Verify strategy used is tracked."""
        parser = RobustJSONParser()
        result = parser.parse('{"key": "value"}')
        assert result.success
        assert result.strategy == ParseStrategy.STRICT

    def test_markdown_strategy(self):
        """Verify markdown strategy is used when needed."""
        parser = RobustJSONParser()
        result = parser.parse('```json\n{"key": "value"}\n```')
        assert result.success
        assert result.strategy == ParseStrategy.MARKDOWN_STRIP

    def test_parse_result_contains_data(self):
        """ParseResult contains correct data."""
        parser = RobustJSONParser()
        result = parser.parse('{"a": 1, "b": 2}')
        assert result.success
        assert result.data == {"a": 1, "b": 2}
        assert result.error is None

    def test_parse_result_on_failure(self):
        """ParseResult on failure contains error info."""
        parser = RobustJSONParser(use_repair_library=False)
        result = parser.parse("not json at all")
        assert not result.success
        assert result.data is None
        assert result.strategy == ParseStrategy.FAILED


class TestExtractJsonWithFallback:
    """Test extract_json_with_fallback function."""

    def test_successful_parse(self):
        """Successful parse returns data."""
        result = extract_json_with_fallback('{"key": "value"}')
        assert result == {"key": "value"}

    def test_failed_parse_default(self):
        """Failed parse returns empty dict by default."""
        result = extract_json_with_fallback("not json")
        assert result == {}

    def test_failed_parse_custom_default(self):
        """Failed parse returns custom default."""
        result = extract_json_with_fallback("not json", default={"status": "error"})
        assert result == {"status": "error"}


class TestReturnStrategy:
    """Test return_strategy parameter."""

    def test_return_strategy_true(self):
        """return_strategy=True returns tuple."""
        data, strategy = extract_json('{"key": "value"}', return_strategy=True)
        assert data == {"key": "value"}
        assert strategy == "strict"

    def test_return_strategy_markdown(self):
        """Strategy name for markdown parsing."""
        data, strategy = extract_json('```json\n{"key": "value"}\n```', return_strategy=True)
        assert data == {"key": "value"}
        assert strategy == "markdown_strip"


class TestRealWorldExamples:
    """Test with realistic LLM response patterns."""

    def test_gpt4_style_response(self):
        """GPT-4 style response with explanation."""
        response = """Based on the gamma exposure data provided, I can identify a clear persistent negative regime.

```json
{
    "regime_type": "persistent_negative",
    "regime_detected": true,
    "confidence": 82,
    "reasoning": "The 30-day window shows consistent negative GEX with magnitude exceeding $5B threshold. Persistence rate of 87% indicates strong dealer hedging pressure.",
    "key_metrics": {
        "persistence_rate": 0.87,
        "avg_magnitude_billions": 6.2,
        "sign_flips": 4
    }
}
```

This pattern suggests significant market maker constraints during this period."""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "persistent_negative"
        assert result["confidence"] == 82
        assert result["key_metrics"]["persistence_rate"] == 0.87

    def test_o4_mini_style_response(self):
        """o4-mini style response (more concise)."""
        response = """{"regime_type": "transitional", "regime_detected": false, "confidence": 35, "reasoning": "Insufficient persistence (62%) and low magnitude ($2.1B avg)"}"""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "transitional"
        assert result["confidence"] == 35
        assert not result["regime_detected"]

    def test_claude_style_response(self):
        """Claude-style response with context."""
        response = """I'll analyze this gamma exposure sequence to identify any regime patterns.

Here's my assessment:

{"regime_type": "persistent_negative", "confidence": 78, "reasoning": "The data shows a clear negative gamma regime with 83% persistence over the 30-day window."}

The high persistence rate and consistent negative values indicate strong dealer positioning constraints."""
        result = extract_json(response)
        assert result is not None
        assert result["regime_type"] == "persistent_negative"
        assert result["confidence"] == 78


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
