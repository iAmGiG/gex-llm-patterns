"""
Date sanitization utilities for V4 sentiment agent.
Removes temporal information while preserving entity relationships.
"""

import re
from typing import Dict, List, Any
import pandas as pd


def sanitize_dates_only(text: str) -> str:
    """
    Remove temporal anchors while preserving all other content.
    Prevents the LLM from using knowledge of future events.

    Args:
        text: Original text (typically article summary)

    Returns:
        Text with dates replaced by generic markers
    """
    if not text:
        return ""

    # Replace specific date patterns with generic markers
    text = re.sub(
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}', '[DATE]', text)
    text = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '[DATE]', text)
    text = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', '[DATE]', text)
    text = re.sub(r'\b(Q[1-4])\s+\d{4}\b', r'\1 [YEAR]', text)
    text = re.sub(r'\b20\d{2}\b', '[YEAR]', text)  # Years 2000-2099
    text = re.sub(r'\b19\d{2}\b', '[YEAR]', text)  # Years 1900-1999

    # Replace relative time references
    text = re.sub(r'\b(yesterday|today|tomorrow)\b', '[RECENT]', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(last|this|next)\s+(week|month|quarter|year)\b',
                  '[PERIOD]', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
                  '[WEEKDAY]', text, flags=re.IGNORECASE)

    # Clean up any double spaces created
    text = ' '.join(text.split())

    return text


def prepare_news_for_v4(news_df: pd.DataFrame, requested_ticker: str = None) -> List[Dict[str, Any]]:
    """
    Prepare news data for V4 with date sanitization and selective ticker obfuscation.
    Leverages the categorization already done by hierarchical_news_tool.

    Args:
        news_df: DataFrame from hierarchical news tool (already categorized)
        requested_ticker: The actual ticker being analyzed (e.g., 'AAPL')
                         This will be obfuscated in direct news only

    Returns:
        List of processed news items for LLM consumption
    """
    processed_news = []

    for _, article in news_df.iterrows():
        # Determine if this is direct news about the requested ticker
        is_primary = (requested_ticker and
                      article.get('news_category') == 'direct' and
                      (article.get('ticker') == requested_ticker or
                          article.get('target_ticker') == requested_ticker))

        # Get the appropriate ticker to display
        article_ticker = article.get('ticker', article.get('news_source_ticker', 'UNKNOWN'))

        # Obfuscate ONLY the primary ticker in direct news
        # Keep sector (XLK, QQQ) and market (SPY) tickers visible
        display_ticker = 'TICKER_001' if is_primary else article_ticker

        news_item = {
            'title': article['title'],  # Keep titles as-is
            'summary': sanitize_dates_only(article.get('summary', '')),  # Sanitize dates
            'ticker': display_ticker,
            'source': article.get('url_pattern_source', 'Unknown'),
            'relevance': float(article.get('relevance_score', 0.5)),
            'category': article.get('news_category', 'unknown')  # Already set by hierarchical tool
        }

        processed_news.append(news_item)

    return processed_news


def format_news_for_llm_prompt(processed_news: List[Dict[str, Any]]) -> str:
    """
    Format processed news into structured text for LLM prompt.
    Replaces the raw DataFrame string representation that was leaking dates.

    Args:
        processed_news: List of news items from prepare_news_for_v4

    Returns:
        Formatted string for LLM consumption
    """
    # Group by category (already marked by hierarchical tool)
    direct_news = [n for n in processed_news if n.get('category') == 'direct']
    sector_news = [n for n in processed_news if n.get('category') == 'sector']
    market_news = [n for n in processed_news if n.get('category') == 'market']

    output_parts = []

    # Direct news - with obfuscated ticker (TICKER_001)
    if direct_news:
        output_parts.append("PRIMARY COMPANY NEWS:")
        for item in direct_news[:8]:  # Limit to prevent token overflow
            output_parts.append(f"[{item['ticker']}] {item['title']}")
            if item['summary']:
                output_parts.append(f"  Summary: {item['summary'][:200]}")
            output_parts.append(f"  Source: {item['source']} | Relevance: {item['relevance']:.2f}")
            output_parts.append("")

    # Sector news - real tickers visible (XLK, QQQ, etc.)
    if sector_news:
        output_parts.append("SECTOR CONTEXT:")
        for item in sector_news[:4]:
            output_parts.append(f"[{item['ticker']}] {item['title']}")
            if item['summary']:
                output_parts.append(f"  Summary: {item['summary'][:150]}")
            output_parts.append(f"  Source: {item['source']}")
            output_parts.append("")

    # Market news - SPY visible
    if market_news:
        output_parts.append("MARKET SENTIMENT:")
        for item in market_news[:3]:
            output_parts.append(f"[{item['ticker']}] {item['title']}")
            if item['summary']:
                output_parts.append(f"  Summary: {item['summary'][:100]}")
            output_parts.append(f"  Source: {item['source']}")
            output_parts.append("")

    # Add footer explaining the structure
    output_parts.append(
        "Note: Analyze sentiment based on the above news to recommend BUY, SELL, or HOLD for TICKER_001")

    return "\n".join(output_parts)
