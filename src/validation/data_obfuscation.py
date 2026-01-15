"""Data Obfuscation Utilities for LLM Trading Validation.

This module provides functions to remove temporal and ticker references
that could allow LLMs to use training knowledge rather than genuine analysis.

Critical for Issue #61: Validate LLM trading decisions without data leakage.

Key Problem Solved:
    LLMs can "cheat" by recognizing famous market events from training data:
    - "GameStop January 2021" → LLM recalls documented squeeze mechanics
    - "COVID crash March 2020" → LLM knows about put hedging dynamics

    This obfuscation ensures genuine analytical capability testing.

Transformations:
    - Dates: "2021-01-28" → "Day T+17"
    - Tickers: "GME" → "STOCK_G", "SPY" → "INDEX_1"
    - Context: Remove market event references (COVID, Fed, specific years)

Usage:
    from gex_db_infrastructure.validation.data_obfuscation import DataObfuscator

    obfuscator = DataObfuscator()

    # Obfuscate dates
    date_mapping = obfuscator.obfuscate_dates(["2021-01-25", "2021-01-28"])

    # Obfuscate tickers
    ticker_mapping = obfuscator.obfuscate_tickers(["GME", "SPY"])

    # Result: Anonymous data that LLM must analyze genuinely

See docs/data-obfuscation.md for comprehensive documentation.
"""

import json
import logging
import os
import re

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


class DataObfuscator:
    """Obfuscates market data to prevent LLM from using training knowledge.

    Key transformations:
    - Dates: "2022-07-26" → "Day T+0", "Day T+1", etc.
    - Tickers: "SPY" → "INDEX_1", "AAPL" → "STOCK_A", etc.
    - Context: Remove market event references
    """

    def __init__(self, config_path=None):
        """Initialize obfuscator with mapping dictionaries.

        Args:
            config_path: Path to obfuscation patterns YAML config.
                        If None, uses config_defaults/obfuscation_patterns.yaml
        """
        self.date_mapping = {}
        self.ticker_mapping = {}
        self.reverse_mappings = {}
        self.base_date = None

        # Load patterns from YAML config
        if config_path is None:
            # Default to config_defaults/obfuscation_patterns.yaml
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_root, "config_defaults", "obfuscation_patterns.yaml")

        self._load_config(config_path)

        # Pre-compile temporal patterns for performance (10x speedup)
        self._temporal_patterns_compiled = self._compile_temporal_patterns()

    def _load_config(self, config_path):
        """Load obfuscation patterns from YAML config file."""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            self.temporal_patterns = config.get("temporal_patterns", [])
            self.standard_tickers = config.get("standard_tickers", {})
            self.unknown_ticker_config = config.get(
                "unknown_ticker_handling",
                {"enabled": True, "prefix": "STOCK_", "start_after": "I", "warn_on_unknown": True},
            )
            self.validation_config = config.get("validation", {})

            logger.info(f"Loaded {len(self.temporal_patterns)} temporal patterns from {config_path}")
            logger.info(f"Loaded {len(self.standard_tickers)} standard ticker mappings")

        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}. Using fallback defaults.")
            self._use_fallback_config()
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}. Using fallback defaults.")
            self._use_fallback_config()

    def _use_fallback_config(self):
        """Fallback to hardcoded patterns if YAML config unavailable."""
        # Fallback temporal patterns (same as before)
        self.temporal_patterns = [
            {
                "pattern": r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
                "replacement": "Period A",
            },
            {
                "pattern": r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
                "replacement": "Period A",
            },
            {"pattern": r"\b\d{4}\s+(bear|bull)\s+market\b", "replacement": "Market Period"},
            {"pattern": r"\bCOVID[-\s]19\b", "replacement": "Economic Event A"},
            {"pattern": r"\bpandemic\b", "replacement": "Economic Event A"},
            {"pattern": r"\b(Fed|Federal Reserve)\b", "replacement": "Central Bank"},
            {"pattern": r"\binterest rate\b", "replacement": "monetary policy"},
            {"pattern": r"\b(recession|recovery)\b", "replacement": "economic cycle"},
            {"pattern": r"\b\d{4}\b", "replacement": "YEAR"},
        ]

        # Fallback ticker mappings (same as before)
        self.standard_tickers = {
            "SPY": "INDEX_1",
            "AAPL": "STOCK_A",
            "MSFT": "STOCK_B",
            "GOOGL": "STOCK_C",
            "AMZN": "STOCK_D",
            "NVDA": "STOCK_E",
            "META": "STOCK_F",
            "TSLA": "STOCK_G",
            "VXX": "VOLATILITY_INDEX",
        }

        self.unknown_ticker_config = {"enabled": True, "prefix": "STOCK_", "start_after": "I", "warn_on_unknown": True}

        self.validation_config = {}

    def _compile_temporal_patterns(self):
        """Pre-compile temporal regex patterns for performance.

        Returns:
            List of (compiled_pattern, replacement) tuples

        Performance Impact:
            - Single call: 1.0ms → 0.8ms (1.25x speedup)
            - 180-day batch: 250ms → 25ms (10x speedup)
        """
        compiled = []
        for pattern_config in self.temporal_patterns:
            pattern_str = pattern_config.get("pattern") if isinstance(pattern_config, dict) else pattern_config[0]
            replacement = pattern_config.get("replacement") if isinstance(pattern_config, dict) else pattern_config[1]

            try:
                compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                compiled.append((compiled_pattern, replacement))
            except re.error as e:
                logger.warning(f"Invalid regex pattern: {pattern_str}. Error: {e}")

        return compiled

    def obfuscate_dates(self, date_list, base_date=None):
        """Convert real dates to relative timestamps.

        Args:
            date_list of date strings to obfuscate
            base_date: Optional base date (first date becomes T+0)

        Returnsionary mapping real dates to obfuscated dates
        """
        if not date_list:
            return {}

        # Sort dates to ensure consistent T+0, T+1 mapping
        sorted_dates = sorted(pd.to_datetime(date_list))

        if base_date:
            self.base_date = pd.to_datetime(base_date)
        else:
            self.base_date = sorted_dates[0]

        mapping = {}

        for date in sorted_dates:
            # Calculate days difference from base
            days_diff = (date - self.base_date).days

            if days_diff == 0:
                obfuscated = "Day T+0"
            elif days_diff > 0:
                obfuscated = f"Day T+{days_diff}"
            else:
                obfuscated = f"Day T{days_diff}"  # Negative numbers

            mapping[date.strftime("%Y-%m-%d")] = obfuscated

        self.date_mapping = mapping
        return mapping

    def obfuscate_tickers(self, ticker_list):
        """Convert real tickers to anonymous symbols.

        Args:
            ticker_list: List of ticker symbols to obfuscate

        Returns:
            Dictionary mapping real tickers to obfuscated tickers
        """
        mapping = {}
        unknown_counter = 0  # Track unknown tickers separately (bug fix)

        for ticker in ticker_list:
            if ticker in self.standard_tickers:
                # Use standard mapping (e.g., SPY → INDEX_1)
                mapping[ticker] = self.standard_tickers[ticker]
            else:
                # Handle unknown ticker
                if self.unknown_ticker_config.get("enabled", True):
                    # Generate dynamic mapping (STOCK_J, STOCK_K, ...)
                    prefix = self.unknown_ticker_config.get("prefix", "STOCK_")
                    start_after = self.unknown_ticker_config.get("start_after", "I")

                    # Calculate next letter (start after 'I' → 'J')
                    next_letter = chr(ord(start_after) + 1 + unknown_counter)
                    mapping[ticker] = f"{prefix}{next_letter}"
                    unknown_counter += 1

                    # Warn if configured
                    if self.unknown_ticker_config.get("warn_on_unknown", True):
                        logger.warning(
                            f"Unknown ticker '{ticker}' mapped to '{mapping[ticker]}'. "
                            f"Consider adding to config_defaults/obfuscation_patterns.yaml"
                        )
                else:
                    # Strict mode: raise error for unknown tickers
                    raise ValueError(
                        f"Unknown ticker '{ticker}' encountered and unknown_ticker_handling is disabled. "
                        f"Add '{ticker}' to config_defaults/obfuscation_patterns.yaml"
                    )

        self.ticker_mapping = mapping
        return mapping

    def obfuscate_text_content(self, text) -> str:
        """Remove temporal and market context from text.

        Args:
            text: Raw text containing potential temporal references

        Returns:
            Obfuscated text with temporal references removed
        """
        if not text:
            return text

        obfuscated = text

        # Apply date mappings
        for real_date, obfuscated_date in self.date_mapping.items():
            obfuscated = obfuscated.replace(real_date, obfuscated_date)

        # Apply ticker mappings
        for real_ticker, obfuscated_ticker in self.ticker_mapping.items():
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(real_ticker) + r"\b"
            obfuscated = re.sub(pattern, obfuscated_ticker, obfuscated, flags=re.IGNORECASE)

        # Use pre-compiled temporal patterns (OPTIMIZATION: 10x faster)
        for compiled_pattern, replacement in self._temporal_patterns_compiled:
            obfuscated = compiled_pattern.sub(replacement, obfuscated)

        return obfuscated

    def obfuscate_market_data(self, market_data):
        """Obfuscate a complete market data DataFrame.

        Args:
            market_data: DataFrame with Date index and market data

        Returns:
            Tuple of (obfuscated_dataframe, metadata_for_reversal)
        """
        if market_data.empty:
            return market_data, {}

        # Create copy to avoid modifying original
        obfuscated_df = market_data.copy()

        # Extract unique dates and tickers
        if isinstance(obfuscated_df.index, pd.DatetimeIndex):
            date_strings = [d.strftime("%Y-%m-%d") for d in obfuscated_df.index]
        else:
            date_strings = obfuscated_df.index.tolist()

        tickers = []
        if "Symbol" in obfuscated_df.columns:
            tickers = obfuscated_df["Symbol"].unique().tolist()

        # Create mappings
        date_map = self.obfuscate_dates(date_strings)
        ticker_map = self.obfuscate_tickers(tickers) if tickers else {}

        # Apply obfuscation to index
        if isinstance(obfuscated_df.index, pd.DatetimeIndex):
            new_index = [date_map[d.strftime("%Y-%m-%d")] for d in obfuscated_df.index]
            obfuscated_df.index = new_index

        # Apply obfuscation to Symbol column
        if "Symbol" in obfuscated_df.columns:
            obfuscated_df["Symbol"] = obfuscated_df["Symbol"].map(ticker_map)

        # Store metadata for reversal
        metadata = {
            "date_mapping": date_map,
            "ticker_mapping": ticker_map,
            "base_date": self.base_date.strftime("%Y-%m-%d") if self.base_date else None,
            "original_columns": list(market_data.columns),
            "original_index_type": str(type(market_data.index)),
        }

        return obfuscated_df, metadata

    def obfuscate_news_data(self, news_data):
        """Obfuscate news articles by removing temporal references.

        Args:
            news_data of news article dictionaries

        Returns of obfuscated news articles
        """
        obfuscated_articles = []

        for article in news_data:
            obfuscated_article = article.copy()

            # Obfuscate text fields
            for field in ["title", "description", "content", "summary"]:
                if field in obfuscated_article and obfuscated_article[field]:
                    obfuscated_article[field] = self.obfuscate_text_content(obfuscated_article[field])

            # Obfuscate date fields
            if "publishedAt" in obfuscated_article:
                # Extract YYYY-MM-DD
                pub_date = obfuscated_article["publishedAt"][:10]
                if pub_date in self.date_mapping:
                    obfuscated_article["publishedAt"] = self.date_mapping[pub_date]

            obfuscated_articles.append(obfuscated_article)

        return obfuscated_articles

    def create_reverse_mapping(self):
        """Create reverse mappings to convert obfuscated data back to original.

        Returnsionary with reverse mappings for dates and tickers
        """
        reverse_mapping = {
            "dates": {v: k for k, v in self.date_mapping.items()},
            "tickers": {v: k for k, v in self.ticker_mapping.items()},
        }

        self.reverse_mappings = reverse_mapping
        return reverse_mapping

    def save_mappings(self, filepath):
        """Save obfuscation mappings to file for later use."""
        mappings = {
            "date_mapping": self.date_mapping,
            "ticker_mapping": self.ticker_mapping,
            "base_date": self.base_date.strftime("%Y-%m-%d") if self.base_date else None,
            "standard_tickers": self.standard_tickers,
        }

        with open(filepath, "w") as f:
            json.dump(mappings, f, indent=2, default=str)

    def load_mappings(self, filepath):
        """Load obfuscation mappings from file."""
        with open(filepath, "r") as f:
            mappings = json.load(f)

        self.date_mapping = mappings.get("date_mapping", {})
        self.ticker_mapping = mappings.get("ticker_mapping", {})
        if mappings.get("base_date"):
            self.base_date = pd.to_datetime(mappings["base_date"])


def validate_obfuscation_quality(original_text, obfuscated_text):
    """Validate that obfuscation successfully removed temporal references.

    Args:
        original_text: Original text with temporal references
        obfuscated_text: Obfuscated text

    Returnsionary with validation results
    """
    issues = []

    # Check for remaining date patterns
    date_patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
        r"\b\d{1,2}/\d{1,2}/\d{4}\b",  # MM/DD/YYYY
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
    ]

    for pattern in date_patterns:
        matches = re.findall(pattern, obfuscated_text, re.IGNORECASE)
        if matches:
            issues.append(f"Found remaining dates: {matches}")

    # Check for remaining ticker patterns
    # 2-5 uppercase letters (typical tickers)
    ticker_patterns = [r"\b[A-Z]{2,5}\b"]
    for pattern in ticker_patterns:
        matches = re.findall(pattern, obfuscated_text)
        # Filter out our obfuscated patterns and replacement words
        excluded_patterns = [
            "STOCK_",
            "INDEX",
            "VOLATILITY",
            "PERIOD",
            "MARKET",
            "ECONOMIC",
            "EVENT",
            "CENTRAL",
            "BANK",
            "YEAR",
        ]
        real_tickers = [m for m in matches if not any(excluded in m for excluded in excluded_patterns)]
        if real_tickers:
            issues.append(f"Potential remaining tickers: {real_tickers}")

    return {
        "validation_passed": len(issues) == 0,
        "issues_found": issues,
        "original_length": len(original_text),
        "obfuscated_length": len(obfuscated_text),
        "reduction_ratio": 1 - (len(obfuscated_text) / len(original_text)) if original_text else 0,
    }


# Convenience functions for quick usage
def obfuscate_date_range(start_date, end_date):
    """Quick function to obfuscate a date range."""
    obfuscator = DataObfuscator()
    dates = pd.date_range(start_date, end_date, freq="D").strftime("%Y-%m-%d").tolist()
    return obfuscator.obfuscate_dates(dates, start_date)


def obfuscate_mag7_tickers():
    """Quick function to get MAG7 ticker obfuscation mapping."""
    obfuscator = DataObfuscator()
    mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    return obfuscator.obfuscate_tickers(mag7)
