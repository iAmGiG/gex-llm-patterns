"""Market Intelligence Module for Agent Tools Extracted from agent_utils.py for clean integration.

Provides market sector classification and query parsing capabilities.
"""

import json
import os
import re


class MarketIntelligence:
    """Market sector intelligence and query parsing for GEX agents."""

    def __init__(self):
        """Initialize with market sectors data."""
        self.market_sectors = self._load_market_sectors()

    def _load_market_sectors(self):
        """Load market sectors from config or use defaults."""
        try:
            # Get the project root directory
            config_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sectors_file = os.path.join(config_dir, "config", "market_sectors.json")

            with open(sectors_file, "r") as f:
                data = json.load(f)
                return data.get("sectors", {})
        except Exception:
            # Return default sectors for GEX analysis
            return self._get_default_sectors()

    def _get_default_sectors(self):
        """Default market sectors for GEX analysis if config file not available."""
        return {
            "technology": {
                "representative": "QQQ",
                "keywords": ["technology", "tech", "software", "ai", "artificial intelligence", "cloud"],
                "related_topics": ["innovation", "digital", "automation", "semiconductors"],
            },
            "finance": {
                "representative": "XLF",
                "keywords": ["finance", "financial", "banking", "banks", "insurance"],
                "related_topics": ["interest rates", "credit", "mortgages", "lending"],
            },
            "energy": {
                "representative": "XLE",
                "keywords": ["energy", "oil", "gas", "petroleum", "renewable"],
                "related_topics": ["crude", "natural gas", "solar", "wind"],
            },
            "healthcare": {
                "representative": "XLV",
                "keywords": ["healthcare", "health", "medical", "pharma", "biotech"],
                "related_topics": ["drugs", "medicine", "treatment", "clinical"],
            },
            "retail": {
                "representative": "XRT",
                "keywords": ["retail", "consumer", "shopping", "e-commerce"],
                "related_topics": ["holiday season", "spending", "discretionary"],
            },
        }

    def extract_query_details(self, message):
        """Extract ticker, sector, dates from a user query.

        Args:
            message: User's query message

        Returns:
            Dict with extracted details (ticker, topic, sector, dates)
        """
        ticker = None
        topic = None
        start_date = None
        end_date = None
        sector = None
        anchor = None

        # List of common financial terms that aren't tickers
        common_terms = ["I", "A", "AI", "US", "ER", "GDP", "CPI", "IPO", "EPS", "ROI", "YOY"]

        # Extract ticker if present (uppercase 1-5 chars)
        words = message.split()
        for word in words:
            # Filter out punctuation
            clean_word = "".join(c for c in word if c.isalnum())

            # Skip common terms that aren't tickers
            if clean_word.isupper() and 1 <= len(clean_word) <= 5 and clean_word not in common_terms:
                ticker = clean_word
                break

        # Check for sector keywords
        message_lower = message.lower()
        priority_matches = []

        for sector_name, sector_data in self.market_sectors.items():
            keywords = sector_data.get("keywords", [])

            for keyword in keywords:
                if keyword in message_lower:
                    # Calculate match priority (longer matches = higher priority)
                    priority = len(keyword)

                    # Exact sector names get higher priority
                    if sector_name.replace("_", " ") == keyword:
                        priority += 10

                    # "Sector" mentions get higher priority
                    if keyword.endswith(" sector") or keyword.endswith(" stocks"):
                        priority += 5

                    priority_matches.append((sector_name, priority, sector_data))

        # Take highest priority match
        if priority_matches:
            priority_matches.sort(key=lambda x: x[1], reverse=True)
            sector_name, _, sector_data = priority_matches[0]

            sector = sector_name
            topic = sector_name.replace("_", " ")

            # Use sector's representative ticker if none specified
            if not ticker:
                ticker = sector_data.get("representative")

        # Extract date patterns
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

        # Default to recent data if no date provided
        if not start_date:
            start_date = "-5d"

        # Default to SPY if no ticker identified
        if not ticker:
            ticker = "SPY"

        return {
            "ticker": ticker,
            "topic": topic,
            "sector": sector,
            "start_date": start_date,
            "end_date": end_date,
            "anchor": anchor,
        }

    def get_sector_tickers(self, sector_name):
        """Get representative ticker for a sector."""
        sector_data = self.market_sectors.get(sector_name.lower())
        if sector_data:
            return sector_data.get("representative")
        return None

    def identify_sector(self, ticker):
        """Attempt to identify sector from ticker."""
        ticker_upper = ticker.upper()

        # Check if ticker is a sector representative
        for sector_name, sector_data in self.market_sectors.items():
            if sector_data.get("representative") == ticker_upper:
                return sector_name

        # Default mappings for common tickers
        sector_mappings = {
            "SPY": "broad_market",
            "QQQ": "technology",
            "IWM": "small_cap",
            "XLF": "finance",
            "XLE": "energy",
            "XLV": "healthcare",
            "XRT": "retail",
            "AAPL": "technology",
            "MSFT": "technology",
            "GOOGL": "technology",
            "AMZN": "technology",
            "TSLA": "technology",
        }

        return sector_mappings.get(ticker_upper)

    def get_related_symbols(self, sector, include_leveraged: bool = False) -> list:
        """Get related symbols for a sector."""
        if sector not in self.market_sectors:
            return []

        symbols = []
        sector_data = self.market_sectors[sector]

        # Add representative ETF
        if "representative" in sector_data:
            symbols.append(sector_data["representative"])

        # Add other ETFs if available
        if "etfs" in sector_data:
            symbols.extend(sector_data["etfs"])

        # Add blue chip stocks
        if "blue_chips" in sector_data:
            symbols.extend(sector_data["blue_chips"])

        # Add leveraged ETFs if requested
        if include_leveraged and "leveraged_etfs" in sector_data:
            symbols.extend(sector_data["leveraged_etfs"])

        return list(set(symbols))  # Remove duplicates


# Global instance for easy access
market_intelligence = MarketIntelligence()
