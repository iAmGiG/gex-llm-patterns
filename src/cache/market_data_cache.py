"""Market data caching to reduce API calls during backtesting."""

import os
import json
import hashlib
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta


class MarketDataCache:
    """Simple file-based cache for market data."""

    def __init__(self, cache_dir: str = ".cache/market_data"):
        """Initialize cache with directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, symbol: str, start: str, end: str, source: str) -> str:
        """Generate cache key from parameters."""
        key_string = f"{symbol}_{start}_{end}_{source}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Get full path for cache file."""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    def get(self, symbol: str, start: str, end: str, source: str) -> Optional[pd.DataFrame]:
        """Retrieve cached data if available and not expired."""
        cache_key = self._get_cache_key(symbol, start, end, source)
        cache_path = self._get_cache_path(cache_key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check if cache is expired (24 hours)
            cached_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=24):
                return None

            # Reconstruct DataFrame
            data = cache_data['data']
            if isinstance(data, dict) and 'values' in data:
                # New format
                df = pd.DataFrame(data['values'])
                if 'index' in data and not df.empty:
                    # Handle timezone-aware datetime
                    try:
                        df.index = pd.to_datetime(data['index'], utc=True)
                    except:
                        df.index = pd.to_datetime(data['index'])
                    df = df.sort_index()
            else:
                # Old format (backward compatibility)
                df = pd.DataFrame(data)
                if not df.empty:
                    try:
                        df.index = pd.to_datetime(df.index)
                        df = df.sort_index()
                    except:
                        pass

            print(f"✅ Cache hit for {symbol} ({start} to {end}) from {source}")
            return df

        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def set(self, symbol: str, start: str, end: str, source: str, data: pd.DataFrame) -> None:
        """Store data in cache."""
        if data.empty:
            return

        cache_key = self._get_cache_key(symbol, start, end, source)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Convert DataFrame to JSON-serializable format
            # Save both data and index separately for better reconstruction
            data_dict = {
                'values': data.to_dict(orient='records'),
                'index': [str(idx) for idx in data.index],
                'columns': list(data.columns)
            }

            cache_data = {
                'symbol': symbol,
                'start': start,
                'end': end,
                'source': source,
                'timestamp': datetime.now().isoformat(),
                'data': data_dict
            }

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)

            print(f"💾 Cached data for {symbol} ({start} to {end}) from {source}")

        except Exception as e:
            print(f"Cache write error: {e}")

    def clear(self) -> None:
        """Clear all cached data."""
        for file in os.listdir(self.cache_dir):
            if file.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, file))
        print("🗑️  Cache cleared")
