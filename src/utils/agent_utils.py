"""
Utility functions and classes for agents.
Provides helper functions for data processing, query parsing, and other common tasks.
"""

import os
import json
import re
from collections import Counter


def load_agent_config(agent_key: str) -> dict:
    """
    Load an agent's configuration from the agent_prompts.json file.

    Args:
        agent_key: The key for the agent (e.g., "sentiment_agent")

    Returns:
        The agent's configuration dictionary
    """
    try:
        # Get the project root directory (up two levels from this file)
        config_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        config_file = os.path.join(config_dir, 'config', 'agent_prompts.json')

        with open(config_file, 'r') as f:
            all_configs = json.load(f)

        # Return the config for the requested agent, or an empty dict if not found
        return all_configs.get(agent_key, {})
    except Exception as e:
        print(f"Error loading agent config: {e}")
        return {}


def load_market_sectors() -> dict:
    """
    Load market sectors data from market_sectors.json file.

    Returns:
        Dictionary with market sectors data, or empty dict if file not found
    """
    try:
        # Get the project root directory
        config_dir = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        sectors_file = os.path.join(
            config_dir, 'config', 'market_sectors.json')

        with open(sectors_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading market sectors: {e}")
        return {"sectors": {}}


class QueryParser:
    """
    Parse user queries to extract topics, sectors, dates, and tickers.
    """

    def __init__(self, market_sectors=None):
        """
        Initialize with optional market sectors data.

        Args:
            market_sectors: Dictionary of market sectors. If None, will be loaded from file.
        """
        if market_sectors is None:
            self.market_sectors = load_market_sectors().get("sectors", {})
        else:
            self.market_sectors = market_sectors

    def extract_query_details(self, message: str) -> dict:
        """
        Extract details from a user query.

        Args:
            message: The user's query message

        Returns:
            Dictionary with extracted details (ticker, topic, sector, dates)
        """
        ticker = None
        topic = None
        start_date = None
        end_date = None
        sector = None
        anchor = None

        # List of common financial terms and abbreviations that aren't tickers
        common_terms = ["I", "A", "AI", "US", "ER", "GDP",
                        "CPI", "IPO", "P/E", "EPS", "ROI", "YOY"]

        # List of common financial terms and abbreviations that aren't tickers
        common_terms = ["I", "A", "AI", "US", "ER", "GDP",
                        "CPI", "IPO", "P/E", "EPS", "ROI", "YOY"]

        # Extract ticker if present (uppercase 1-5 chars)
        words = message.split()
        for word in words:
            # Filter out punctuation from the word
            clean_word = ''.join(c for c in word if c.isalnum())

            # Skip common terms/acronyms that aren't tickers
            if clean_word.isupper() and 1 <= len(clean_word) <= 5 and clean_word not in common_terms:
                ticker = clean_word
                break

        # Check if message contains keywords for specific sectors
        message_lower = message.lower()

        # First pass: Check for direct mentions of keywords with priority
        priority_matches = []

        for sector_name, sector_data in self.market_sectors.items():
            keywords = sector_data.get("keywords", [])

            # Check if any primary keyword from this sector appears in the message
            for keyword in keywords:
                if keyword in message_lower:
                    # Calculate a match priority score
                    # Longer matches are more specific and should have higher priority
                    priority = len(keyword)

                    # Exact sector names get higher priority
                    if sector_name.replace("_", " ") == keyword:
                        priority += 10

                    # "Sector" mentions get higher priority
                    if keyword.endswith(" sector") or keyword.endswith(" stocks"):
                        priority += 5

                    # Holiday season and retail should have very high priority for retail sector
                    if sector_name == "retail" and ("holiday season" in message_lower or "shopping" in message_lower):
                        priority += 15

                    priority_matches.append(
                        (sector_name, priority, sector_data))

        # If we have matches, take the highest priority one
        if priority_matches:
            # Sort by priority (highest first)
            priority_matches.sort(key=lambda x: x[1], reverse=True)
            sector_name, _, sector_data = priority_matches[0]

            sector = sector_name
            topic = sector_name.replace("_", " ")

            # If no specific ticker found, use the sector's representative ticker
            if not ticker:
                ticker = sector_data.get("representative")

        # Second pass: If no direct match, try related topics with sector context
        if not sector:
            for sector_name, sector_data in self.market_sectors.items():
                related = sector_data.get("related_topics", [])

                # Check for related topics combined with sector context
                if any(rel_topic in message_lower for rel_topic in related):
                    # Check if the sector itself is mentioned
                    sector_terms = [sector_name.replace(
                        "_", " "), "sector", "stocks", "industry"]
                    if any(term in message_lower for term in sector_terms):
                        sector = sector_name
                        topic = sector_name.replace("_", " ")

                        # If no specific ticker found, use the sector's representative ticker
                        if not ticker:
                            ticker = sector_data.get("representative")
                        break

        # If no sector detected, try to extract topic from standard patterns
        if not topic:
            topic_indicators = ["about", "on", "for",
                                "around", "sentiment on", "sentiment around"]
            for indicator in topic_indicators:
                if indicator in message_lower:
                    parts = message_lower.split(indicator)
                    if len(parts) > 1:
                        # Grab the part right after the indicator, clean it up
                        topic_candidate = parts[1].strip().split("?")[
                            0].split(".")[0]
                        if not (ticker and ticker.lower() in topic_candidate):
                            topic = topic_candidate
                            break

        # Look for date-related keywords
        if "since" in message_lower:
            after_since = message_lower.split("since")[-1].strip()
            words = after_since.split()
            if words:
                if re.match(r"\d{4}-\d{2}-\d{2}", words[0]):
                    anchor = words[0]
                elif words[0] in ["earnings", "fomc", "year_open"]:
                    anchor = words[0]
                elif words[0].startswith("-") or words[0] in ["yesterday", "today", "ytd"]:
                    start_date = words[0]

        if "last" in message_lower:
            after_last = message_lower.split("last")[-1].strip()
            words = after_last.split()
            if words:
                if "day" in after_last or "days" in after_last:
                    try:
                        days = int(words[0])
                        start_date = f"-{days}d"
                    except ValueError:
                        start_date = "-5d"  # Default to 5 days
                elif "week" in after_last or "weeks" in after_last:
                    try:
                        weeks = int(words[0])
                        start_date = f"-{weeks}w"
                    except ValueError:
                        start_date = "-1w"
                elif "month" in after_last or "months" in after_last:
                    try:
                        months = int(words[0])
                        start_date = f"-{months}m"
                    except ValueError:
                        start_date = "-1m"

        if not anchor:
            match = re.search(
                r"(?:from|since)\s+(earnings|fomc|year[_ ]?open)", message_lower
            )
            if match:
                anchor = match.group(1).replace(" ", "_")
        if not anchor:
            match = re.search(r"(?:from|since)\s+(\d{4}-\d{2}-\d{2})", message_lower)
            if match:
                anchor = match.group(1)

        # For open-ended queries, extract topic using NLP techniques if needed
        if not topic and not ticker and len(message.split()) > 3:
            # Remove common stopwords and extract likely topic words
            stopwords = ['the', 'and', 'to', 'of', 'on', 'in', 'for', 'is', 'are', 'what', 'how',
                         'a', 'an', 'this', 'that', 'with', 'by', 'as', 'be', 'it', 'from',
                         'might', 'affect', 'impact', 'recent', 'sentiment', 'market', 'understand',
                         'analyze', 'need', 'their', 'behavior', 'reaction', 'perceived', 'future',
                         'around', 'light', 'being', 'i', 'me', 'my', 'you', 'your']

            # Clean up the message and extract potential topic words
            clean_words = [word.lower() for word in re.findall(r'\b\w+\b', message_lower)
                           if word.lower() not in stopwords and len(word) > 3]

            # Use word frequency to identify potential topics
            word_counts = Counter(clean_words)
            common_words = [word for word, count in word_counts.most_common(3)]

            if common_words:
                topic = " ".join(common_words)

                # Try to map extracted topic to a sector if possible
                for sector_name, sector_data in self.market_sectors.items():
                    if any(word in sector_data.get("keywords", []) for word in common_words):
                        sector = sector_name
                        ticker = sector_data.get("representative")
                        break

        # If no date provided, default to 5 days
        if not start_date:
            start_date = "-5d"

        # If we still have no ticker but have a topic, try to find a relevant ticker
        if not ticker and topic:
            # Default to SPY for general market topics
            ticker = "SPY"

            # Check if our topic might match any sector
            topic_words = topic.lower().split()
            for sector_name, sector_data in self.market_sectors.items():
                if any(keyword in topic_words for keyword in sector_data.get("keywords", [])):
                    ticker = sector_data.get("representative")
                    break

        return {
            "ticker": ticker,
            "topic": topic,
            "sector": sector,
            "start_date": start_date,
            "end_date": end_date,
            "anchor": anchor,
        }

    @staticmethod
    def _lookback_to_days(lookback: str) -> int:
        """Convert lookback strings like '90d' or '2w' to day counts."""
        if not lookback:
            return 0
        m = re.match(r"(\d+)([dwmy])", lookback)
        if not m:
            return 0
        value = int(m.group(1))
        unit = m.group(2)
        factors = {"d": 1, "w": 7, "m": 30, "y": 365}
        return value * factors.get(unit, 1)

    @classmethod
    def validate_interval_lookback(cls, interval: str, lookback: str) -> None:
        """Validate that the requested lookback is allowed for the interval."""
        limits = {
            "1m": 60,
            "5m": 60,
            "15m": 60,
            "30m": 60,
            "1h": 730,
            "4h": 730,
            "1d": 3650,
            "1w": 3650,
            "1M": 3650,
        }

        days = cls._lookback_to_days(lookback)
        max_days = limits.get(interval)
        if max_days is not None and days > max_days:
            raise ValueError(
                f"Lookback {lookback} exceeds {max_days}d limit for {interval}. "
                f"Try max {max_days}d for {interval} or use a larger interval like 1h."
            )


class DataProcessor:
    """
    Process data for sentiment analysis and market behavior explanations.
    """

    @staticmethod
    def preprocess_news_data(news_data) -> dict:
        """
        Processes news data to extract sentiment signals.
        Handles different column names from various sources.

        Args:
            news_data: DataFrame with news data

        Returns:
            Dictionary with extracted signals
        """
        signals = {}
        if news_data.empty:
            signals["error"] = "No news data available"
            return signals

        # Count articles
        signals["article_count"] = len(news_data)

        # Extract headlines - handle different column names
        headline_cols = ["Headline", "title", "Title", "headline"]
        for col in headline_cols:
            if col in news_data.columns:
                signals["headlines"] = news_data[col].tolist()
                break
        else:
            # No recognized headline column
            signals["headlines"] = ["No headline available"] * len(news_data)

        # Extract sentiment scores - handle different column names
        sentiment_cols = ["Sentiment Score", "sentiment_score",
                          "overall_sentiment_score", "score"]
        for col in sentiment_cols:
            if col in news_data.columns:
                signals["average_sentiment"] = news_data[col].mean()
                break
        else:
            # No recognized sentiment column
            signals["average_sentiment"] = None

        return signals

    @staticmethod
    def preprocess_market_data(market_data, ticker) -> dict:
        """
        Processes market data to extract price signals.

        Args:
            market_data: DataFrame with market data
            ticker: Ticker symbol

        Returns:
            Dictionary with extracted signals
        """
        signals = {}
        if market_data.empty:
            signals["error"] = "No market data available"
            return signals

        # Get the most recent price data
        latest = market_data.iloc[0]

        # Basic price information
        if 'close' in latest:
            signals["latest_close"] = latest['close']
        if 'low' in latest and 'high' in latest:
            signals["range_low"] = latest['low']
            signals["range_high"] = latest['high']
        if 'volume' in latest:
            signals["volume"] = latest['volume']

        # Calculate price change if we have enough data
        if len(market_data) > 1 and 'close' in market_data.columns:
            oldest_close = market_data.iloc[-1]['close']
            newest_close = latest['close']
            signals["price_change"] = (
                (newest_close - oldest_close) / oldest_close) * 100
            signals["start_price"] = oldest_close
            signals["end_price"] = newest_close

        signals["ticker"] = ticker

        return signals

    @staticmethod
    def format_data_for_llm(data) -> dict:
        """
        Format all data for the LLM to generate a comprehensive response.

        Args:
            data: Dictionary with all collected data

        Returns:
            Formatted data for LLM consumption
        """
        formatted = {
            "query_info": {
                "ticker": data.get("ticker"),
                "topic": data.get("topic"),
                "sector": data.get("sector"),
                "date_range": f"{data.get('start_date')} to {data.get('end_date') or 'present'}"
            }
        }

        # Add news data if available
        if "news_data" in data:
            formatted["news_analysis"] = {
                "article_count": data["news_data"].get("article_count", 0),
                "headlines": data["news_data"].get("headlines", [])[:3],
                "average_sentiment": data["news_data"].get("average_sentiment"),
            }

        # Add market data if available
        if "market_data" in data:
            formatted["market_analysis"] = {
                "ticker": data["market_data"].get("ticker"),
                "latest_price": data["market_data"].get("latest_close"),
                "price_range": f"{data['market_data'].get('range_low')} - {data['market_data'].get('range_high')}",
                "volume": data["market_data"].get("volume"),
                "price_change": data["market_data"].get("price_change")
            }

        # Add sector context if available
        if "sector" in data and data["sector"]:
            formatted["sector_context"] = {
                "name": data["sector"],
                "etfs": data.get("etfs", []),
                "blue_chips": data.get("blue_chips", []),
                "leveraged_etfs": data.get("leveraged_etfs", [])
            }

        return formatted
