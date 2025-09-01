"""News and sentiment data caching to reduce API calls during backtesting."""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime, timedelta


class NewsCache:
    """Simple file-based cache for news and sentiment data."""

    def __init__(self, cache_dir: str = ".cache/news_data"):
        """Initialize cache with directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, keywords: List[str], ticker: str, start: str, end: str, source: str) -> str:
        """Generate cache key from parameters."""
        # Sort keywords for consistent hashing
        keywords_str = ",".join(sorted(keywords)) if keywords else ""
        key_string = f"{ticker}_{keywords_str}_{start}_{end}_{source}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Get full path for cache file."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get(self, keywords: List[str], ticker: str, start: str, end: str, source: str) -> Optional[pd.DataFrame]:
        """Retrieve cached news data if available and not expired."""
        cache_key = self._get_cache_key(keywords, ticker, start, end, source)
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is expired (7 days for news)
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(days=7):
                return None

            # Reconstruct DataFrame
            data = cache_data['data']
            if data:
                df = pd.DataFrame(data)
                print(
                    f"✅ News cache hit for {ticker} ({start} to {end}) from {source}")
                return df
            else:
                # Return empty DataFrame if data was empty (to avoid re-fetching)
                return pd.DataFrame()

        except Exception as e:
            print(f"News cache read error: {e}")
            return None

    def set(self, keywords: List[str], ticker: str, start: str, end: str,
            source: str, data: pd.DataFrame) -> None:
        """Store news data in cache."""
        cache_key = self._get_cache_key(keywords, ticker, start, end, source)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Convert DataFrame to JSON-serializable format
            if not data.empty:
                data_dict = data.to_dict(orient='records')
            else:
                data_dict = []  # Cache empty results too

            cache_data = {
                'keywords': keywords,
                'ticker': ticker,
                'start': start,
                'end': end,
                'source': source,
                'timestamp': datetime.now().isoformat(),
                'data': data_dict,
                'record_count': len(data_dict)
            }

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

            print(
                f"💾 Cached news data for {ticker} ({start} to {end}) from {source} - {len(data_dict)} articles")

        except Exception as e:
            print(f"News cache write error: {e}")

    def get_sentiment_score(self, ticker: str, date: str) -> Optional[float]:
        """Get cached sentiment score for a specific date."""
        # Check if we have any cached news for this ticker around this date
        cache_files = os.listdir(self.cache_dir)

        for file in cache_files:
            if not file.endswith('.json'):
                continue

            try:
                with open(os.path.join(self.cache_dir, file), 'r') as f:
                    cache_data = json.load(f)

                # Check if this cache entry contains our ticker
                if cache_data.get('ticker') == ticker:
                    # Check if date falls within range
                    start = cache_data.get('start')
                    end = cache_data.get('end')

                    if start <= date <= end:
                        # Calculate sentiment from cached news
                        if cache_data.get('data'):
                            df = pd.DataFrame(cache_data['data'])
                            if 'sentiment' in df.columns:
                                return df['sentiment'].mean()
                        else:
                            # No news data = neutral sentiment
                            return 0.0

            except:
                continue

        return None

    def clear(self) -> None:
        """Clear all cached news data."""
        for file in os.listdir(self.cache_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, file))
        print("🗑️  News cache cleared")

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = [f for f in os.listdir(
            self.cache_dir) if f.endswith('.json')]
        total_size = sum(os.path.getsize(os.path.join(
            self.cache_dir, f)) for f in cache_files)

        # Analyze cache contents
        tickers = set()
        total_articles = 0

        for file in cache_files:
            try:
                with open(os.path.join(self.cache_dir, file), 'r') as f:
                    data = json.load(f)
                    tickers.add(data.get('ticker', 'Unknown'))
                    total_articles += data.get('record_count', 0)
            except:
                pass

        return {
            'cache_files': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'unique_tickers': len(tickers),
            'total_articles': total_articles,
            'tickers': sorted(list(tickers))
        }
