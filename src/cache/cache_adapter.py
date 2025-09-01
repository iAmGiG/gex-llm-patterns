"""
Cache adapter to route all market data through UnifiedCacheManager.

Simple approach: Instead of complex consolidation, just ensure all tools
use the same unified cache system with set-based union operations.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Optional
from .unified_cache import UnifiedCacheManager


class CacheAdapter:
    """
    Adapter to ensure all market data tools use unified caching.

    Provides a single interface that:
    1. Checks existing cache locations for data
    2. Routes all new data through UnifiedCacheManager
    3. Handles set-based union operations for overlapping data
    """

    def __init__(self):
        self.unified_cache = UnifiedCacheManager()
        self.legacy_locations = [
            Path(".cache/polygon/prices"),
            Path(".cache/market_data")
        ]

    def get_market_data(self, symbol: str, start_date: str, end_date: str,
                        source: str = "any") -> Optional[pd.DataFrame]:
        """
        Get market data from any cache location, preferring unified cache.

        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)  
            source: Data source preference ("any", "polygon", "alpha_vantage")
        """
        # First try unified cache
        data = self.unified_cache.get_market_data(symbol, start_date, end_date, source)
        if data is not None:
            return data

        # Fallback: check legacy locations
        for location in self.legacy_locations:
            if not location.exists():
                continue

            legacy_data = self._check_legacy_cache(location, symbol, start_date, end_date)
            if legacy_data is not None:
                # Found in legacy cache - migrate to unified cache
                self.unified_cache.set_market_data(
                    symbol, start_date, end_date, source, legacy_data)
                return legacy_data

        return None

    def set_market_data(self, symbol: str, start_date: str, end_date: str,
                        source: str, data: pd.DataFrame) -> None:
        """
        Store market data using unified cache (with set-based union logic).

        Args:
            symbol: Stock symbol
            start_date: Start date 
            end_date: End date
            source: Data source
            data: OHLCV DataFrame
        """
        # Check if we already have overlapping data
        existing_data = self.unified_cache.get_market_data(symbol, start_date, end_date, source)

        if existing_data is not None and not existing_data.empty:
            # Perform set-based union (merge and deduplicate)
            unified_data = self._union_data(existing_data, data)
            self.unified_cache.set_market_data(symbol, start_date, end_date, source, unified_data)
        else:
            # No existing data - store directly
            self.unified_cache.set_market_data(symbol, start_date, end_date, source, data)

    def _check_legacy_cache(self, cache_dir: Path, symbol: str,
                            start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Check legacy cache locations for matching data."""
        if not cache_dir.exists():
            return None

        # Try different filename patterns
        patterns = [
            f"{symbol}_{start_date}_{end_date}_*.json",
            f"{symbol}_{start_date}_to_{end_date}_*.json",
        ]

        for pattern in patterns:
            for file_path in cache_dir.glob(pattern):
                try:
                    data = self._load_legacy_file(file_path)
                    if data is not None:
                        return data
                except Exception as e:
                    print(f"Warning: Error loading legacy cache file {file_path}: {e}")

        return None

    def _load_legacy_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """Load data from legacy cache file format."""
        try:
            with open(file_path, 'r') as f:
                cache_data = json.load(f)

            # Handle different legacy formats
            if isinstance(cache_data, dict):
                if 'data' in cache_data:
                    data = cache_data['data']
                    if isinstance(data, dict) and 'values' in data:
                        # New format
                        df = pd.DataFrame(data['values'])
                        if 'index' in data and not df.empty:
                            df.index = pd.to_datetime(data['index'])
                        return df
                    elif isinstance(data, list):
                        # List format
                        return pd.DataFrame(data)
            elif isinstance(cache_data, list):
                # Direct list format
                return pd.DataFrame(cache_data)

        except Exception as e:
            print(f"Error loading legacy file {file_path}: {e}")

        return None

    def _union_data(self, existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        """
        Perform set-based union of two DataFrames.

        Combines data and removes duplicates by index (date).
        Prefers newer data for overlapping dates.
        """
        if existing.empty:
            return new
        if new.empty:
            return existing

        # Combine DataFrames
        combined = pd.concat([existing, new])

        # Remove duplicates, keeping last occurrence (newer data)
        combined = combined[~combined.index.duplicated(keep='last')]

        # Sort by index
        combined = combined.sort_index()

        return combined

    def clear_legacy_caches(self) -> None:
        """
        Optional: Clear legacy cache locations after migration.
        Use with caution - only after confirming unified cache works.
        """
        print("⚠️  This will permanently delete legacy cache data!")
        if input("Continue? (y/N): ").lower().startswith('y'):
            for location in self.legacy_locations:
                if location.exists() and location.name == "prices":
                    # Only clear polygon/prices, not the whole polygon dir
                    for file in location.glob("*.json"):
                        file.unlink()
                    print(f"Cleared {location}")


# Global instance for easy access
cache_adapter = CacheAdapter()
