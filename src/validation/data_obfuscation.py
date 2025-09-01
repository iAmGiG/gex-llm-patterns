"""
Data Obfuscation Utilities for LLM Trading Validation

This module provides functions to remove temporal and ticker references
that could allow LLMs to use training knowledge rather than genuine analysis.

Critical for Issue #134: Validate LLM trading decisions without data leakage.
"""

import pandas as pd
import re
from typing import Dict, List, Any, Tuple
import json


class DataObfuscator:
    """
    Obfuscates market data to prevent LLM from using training knowledge.

    Key transformations:
    - Dates: "2022-07-26" → "Day T+0", "Day T+1", etc.
    - Tickers: "SPY" → "INDEX_1", "AAPL" → "STOCK_A", etc.
    - Context: Remove market event references
    """

    def __init__(self):
        """Initialize obfuscator with mapping dictionaries."""
        self.date_mapping = {}
        self.ticker_mapping = {}
        self.reverse_mappings = {}
        self.base_date = None

        # Standard ticker mappings for consistency
        self.standard_tickers = {
            'SPY': 'INDEX_1',
            'AAPL': 'STOCK_A',
            'MSFT': 'STOCK_B',
            'GOOGL': 'STOCK_C',
            'AMZN': 'STOCK_D',
            'NVDA': 'STOCK_E',
            'META': 'STOCK_F',
            'TSLA': 'STOCK_G',
            'VXX': 'VOLATILITY_INDEX'
        }

    def obfuscate_dates(self, date_list: List[str], base_date: str = None) -> Dict[str, str]:
        """
        Convert real dates to relative timestamps.

        Args:
            date_list: List of date strings to obfuscate
            base_date: Optional base date (first date becomes T+0)

        Returns:
            Dictionary mapping real dates to obfuscated dates
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

            mapping[date.strftime('%Y-%m-%d')] = obfuscated

        self.date_mapping = mapping
        return mapping

    def obfuscate_tickers(self, ticker_list: List[str]) -> Dict[str, str]:
        """
        Convert real tickers to anonymous symbols.

        Args:
            ticker_list: List of ticker symbols to obfuscate

        Returns:
            Dictionary mapping real tickers to obfuscated tickers
        """
        mapping = {}

        for ticker in ticker_list:
            if ticker in self.standard_tickers:
                mapping[ticker] = self.standard_tickers[ticker]
            else:
                # Generate generic names for unknown tickers
                existing_count = len([k for k in mapping.values() if k.startswith('STOCK_')])
                next_letter = chr(ord('H') + existing_count)  # Start after G
                mapping[ticker] = f'STOCK_{next_letter}'

        self.ticker_mapping = mapping
        return mapping

    def obfuscate_text_content(self, text: str) -> str:
        """
        Remove temporal and market context from text.

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
            pattern = r'\b' + re.escape(real_ticker) + r'\b'
            obfuscated = re.sub(pattern, obfuscated_ticker, obfuscated, flags=re.IGNORECASE)

        # Remove specific temporal references
        temporal_patterns = [
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', 'Period A'),
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', 'Period A'),
            (r'\b\d{4}\s+(bear|bull)\s+market\b', 'Market Period'),
            (r'\bCOVID[-\s]19\b', 'Economic Event A'),
            (r'\bpandemic\b', 'Economic Event A'),
            (r'\b(Fed|Federal Reserve)\b', 'Central Bank'),
            (r'\binterest rate\b', 'monetary policy'),
            (r'\b(recession|recovery)\b', 'economic cycle'),
            (r'\b\d{4}\b', 'YEAR'),  # Replace any remaining 4-digit years
        ]

        for pattern, replacement in temporal_patterns:
            obfuscated = re.sub(pattern, replacement, obfuscated, flags=re.IGNORECASE)

        return obfuscated

    def obfuscate_market_data(self, market_data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Obfuscate a complete market data DataFrame.

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
            date_strings = [d.strftime('%Y-%m-%d') for d in obfuscated_df.index]
        else:
            date_strings = obfuscated_df.index.tolist()

        tickers = []
        if 'Symbol' in obfuscated_df.columns:
            tickers = obfuscated_df['Symbol'].unique().tolist()

        # Create mappings
        date_map = self.obfuscate_dates(date_strings)
        ticker_map = self.obfuscate_tickers(tickers) if tickers else {}

        # Apply obfuscation to index
        if isinstance(obfuscated_df.index, pd.DatetimeIndex):
            new_index = [date_map[d.strftime('%Y-%m-%d')] for d in obfuscated_df.index]
            obfuscated_df.index = new_index

        # Apply obfuscation to Symbol column
        if 'Symbol' in obfuscated_df.columns:
            obfuscated_df['Symbol'] = obfuscated_df['Symbol'].map(ticker_map)

        # Store metadata for reversal
        metadata = {
            'date_mapping': date_map,
            'ticker_mapping': ticker_map,
            'base_date': self.base_date.strftime('%Y-%m-%d') if self.base_date else None,
            'original_columns': list(market_data.columns),
            'original_index_type': str(type(market_data.index))
        }

        return obfuscated_df, metadata

    def obfuscate_news_data(self, news_data: List[Dict]) -> List[Dict]:
        """
        Obfuscate news articles by removing temporal references.

        Args:
            news_data: List of news article dictionaries

        Returns:
            List of obfuscated news articles
        """
        obfuscated_articles = []

        for article in news_data:
            obfuscated_article = article.copy()

            # Obfuscate text fields
            for field in ['title', 'description', 'content', 'summary']:
                if field in obfuscated_article and obfuscated_article[field]:
                    obfuscated_article[field] = self.obfuscate_text_content(
                        obfuscated_article[field])

            # Obfuscate date fields
            if 'publishedAt' in obfuscated_article:
                pub_date = obfuscated_article['publishedAt'][:10]  # Extract YYYY-MM-DD
                if pub_date in self.date_mapping:
                    obfuscated_article['publishedAt'] = self.date_mapping[pub_date]

            obfuscated_articles.append(obfuscated_article)

        return obfuscated_articles

    def create_reverse_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        Create reverse mappings to convert obfuscated data back to original.

        Returns:
            Dictionary with reverse mappings for dates and tickers
        """
        reverse_mapping = {
            'dates': {v: k for k, v in self.date_mapping.items()},
            'tickers': {v: k for k, v in self.ticker_mapping.items()}
        }

        self.reverse_mappings = reverse_mapping
        return reverse_mapping

    def save_mappings(self, filepath: str):
        """Save obfuscation mappings to file for later use."""
        mappings = {
            'date_mapping': self.date_mapping,
            'ticker_mapping': self.ticker_mapping,
            'base_date': self.base_date.strftime('%Y-%m-%d') if self.base_date else None,
            'standard_tickers': self.standard_tickers
        }

        with open(filepath, 'w') as f:
            json.dump(mappings, f, indent=2, default=str)

    def load_mappings(self, filepath: str):
        """Load obfuscation mappings from file."""
        with open(filepath, 'r') as f:
            mappings = json.load(f)

        self.date_mapping = mappings.get('date_mapping', {})
        self.ticker_mapping = mappings.get('ticker_mapping', {})
        if mappings.get('base_date'):
            self.base_date = pd.to_datetime(mappings['base_date'])


def validate_obfuscation_quality(original_text: str, obfuscated_text: str) -> Dict[str, Any]:
    """
    Validate that obfuscation successfully removed temporal references.

    Args:
        original_text: Original text with temporal references
        obfuscated_text: Obfuscated text

    Returns:
        Dictionary with validation results
    """
    issues = []

    # Check for remaining date patterns
    date_patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
    ]

    for pattern in date_patterns:
        matches = re.findall(pattern, obfuscated_text, re.IGNORECASE)
        if matches:
            issues.append(f"Found remaining dates: {matches}")

    # Check for remaining ticker patterns
    ticker_patterns = [r'\b[A-Z]{2,5}\b']  # 2-5 uppercase letters (typical tickers)
    for pattern in ticker_patterns:
        matches = re.findall(pattern, obfuscated_text)
        # Filter out our obfuscated patterns and replacement words
        excluded_patterns = ['STOCK_', 'INDEX', 'VOLATILITY', 'PERIOD',
                             'MARKET', 'ECONOMIC', 'EVENT', 'CENTRAL', 'BANK', 'YEAR']
        real_tickers = [m for m in matches if not any(
            excluded in m for excluded in excluded_patterns)]
        if real_tickers:
            issues.append(f"Potential remaining tickers: {real_tickers}")

    return {
        'validation_passed': len(issues) == 0,
        'issues_found': issues,
        'original_length': len(original_text),
        'obfuscated_length': len(obfuscated_text),
        'reduction_ratio': 1 - (len(obfuscated_text) / len(original_text)) if original_text else 0
    }


# Convenience functions for quick usage
def obfuscate_date_range(start_date: str, end_date: str) -> Dict[str, str]:
    """Quick function to obfuscate a date range."""
    obfuscator = DataObfuscator()
    dates = pd.date_range(start_date, end_date, freq='D').strftime('%Y-%m-%d').tolist()
    return obfuscator.obfuscate_dates(dates, start_date)


def obfuscate_mag7_tickers() -> Dict[str, str]:
    """Quick function to get MAG7 ticker obfuscation mapping."""
    obfuscator = DataObfuscator()
    mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    return obfuscator.obfuscate_tickers(mag7)
