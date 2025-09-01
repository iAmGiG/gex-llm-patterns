"""
Unified cache manager for V0-V4 framework.

Provides standardized caching interface for all data sources, ensuring consistent
data formats regardless of source (Polygon.io, Alpha Vantage, Google Search).
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import logging


class UnifiedCacheManager:
    """
    Unified cache manager for market data and news.

    Provides consistent caching interface regardless of data source.
    All OHLCV data stored in same format whether from Polygon or Alpha Vantage.
    """

    def __init__(self, base_dir: str = ".cache"):
        """Initialize unified cache manager."""
        self.base_dir = Path(base_dir)
        self.market_dir = self.base_dir / "market_data"
        self.news_dir = self.base_dir / "news"
        self.metadata_dir = self.base_dir / "metadata"

        # Create directories
        for dir_path in [self.market_dir, self.news_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)

    def _calculate_market_data_expiration(self, start_date: str, end_date: str) -> datetime:
        """
        Calculate appropriate expiration based on data recency.

        Historical data (>2 days old): Long expiration (10 years)
        Recent data (≤2 days): Short expiration (24 hours) for fresh updates
        """
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            today = datetime.now().date()

            # Historical data should never practically expire
            if end_dt.date() < today - timedelta(days=2):
                return datetime.now() + timedelta(days=365 * 10)  # 10 years

            # Recent data needs fresh updates
            else:
                return datetime.now() + timedelta(hours=24)

        except ValueError:
            # Fallback to short expiration if date parsing fails
            return datetime.now() + timedelta(hours=24)

    def _get_market_cache_key(self, symbol: str, start: str, end: str, source: str) -> str:
        """Generate standardized cache key for market data."""
        return f"{symbol}_{start}_{end}_{source}.json"

    def _get_news_cache_key(self, query: str, start: str, end: str, source: str = "google_search") -> str:
        """Generate standardized cache key for news data."""
        # Clean query for filename
        clean_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_query = clean_query.replace(' ', '_')[:50]  # Limit length
        return f"{clean_query}_{start}_{end}_{source}.json"

    def get_market_data(self, symbol: str, start: str, end: str, source: str) -> Optional[pd.DataFrame]:
        """
        Get cached market data.

        Returns standardized OHLCV data regardless of original source.
        First tries exact cache key match, then searches for overlapping date ranges.
        """
        cache_key = self._get_market_cache_key(symbol, start, end, source)
        cache_path = self.market_dir / cache_key

        # First try exact match
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)

                # Check expiration using date-aware logic
                start_date = cache_data['metadata']['start_date']
                end_date = cache_data['metadata']['end_date']
                expected_expiry = self._calculate_market_data_expiration(start_date, end_date)

                # Use stored expiry if available, otherwise calculate
                if 'expires_at' in cache_data['metadata']:
                    expires_at = datetime.fromisoformat(cache_data['metadata']['expires_at'])
                else:
                    expires_at = expected_expiry

                if datetime.now() > expires_at:
                    self.logger.debug(f"Market data cache expired: {cache_key}")
                else:
                    # Convert to DataFrame
                    df = pd.DataFrame(cache_data['data'])
                    if not df.empty and 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)

                    self.logger.debug(f"Market data cache hit (exact): {cache_key}")
                    return df

            except Exception as e:
                self.logger.error(f"Error reading market cache {cache_key}: {e}")

        # PRIORITY FIX: Try overlapping/complete files first, quarterly fragments as fallback
        # This prevents fragmented quarterly data from overriding complete datasets
        complete_result = self._search_overlapping_cache(symbol, start, end, source)
        if complete_result is not None:
            # Calculate expected trading days for the time range
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            calendar_days = (end_dt - start_dt).days + 1
            expected_trading_days = calendar_days * 0.7  # Rough estimate: ~70% of calendar days are trading days
            # At least 50% coverage or 5 days minimum
            min_threshold = max(expected_trading_days * 0.5, 5)

            if len(complete_result) >= min_threshold:
                self.logger.debug(
                    f"Market data: Using complete cache file ({len(complete_result)} days, expected ~{expected_trading_days:.0f})")
                return complete_result

        # FALLBACK: For full-year requests, try loading quarterly files if no complete data
        if source == 'alpha_vantage' and start == f"{start[:4]}-01-01" and end == f"{end[:4]}-12-31":
            quarterly_result = self._load_quarterly_cache(symbol, start[:4], source)
            if quarterly_result is not None and len(quarterly_result) > 200:  # Good coverage
                self.logger.debug(
                    f"Market data: Using quarterly cache fallback ({len(quarterly_result)} days)")
                return quarterly_result

        return None

    def _load_quarterly_cache(self, symbol: str, year: str, source: str) -> Optional[pd.DataFrame]:
        """
        Load quarterly cache files for a full year (Q1-Q4).

        This method specifically handles the case where we have quarterly cache files
        like SPY_2024-01-01_2024-03-31_alpha_vantage.json for each quarter.
        """
        try:
            quarterly_files = [
                f"{symbol}_{year}-01-01_{year}-03-31_{source}.json",  # Q1
                f"{symbol}_{year}-04-01_{year}-06-30_{source}.json",  # Q2
                f"{symbol}_{year}-07-01_{year}-09-30_{source}.json",  # Q3
                f"{symbol}_{year}-10-01_{year}-12-31_{source}.json",  # Q4
            ]

            quarterly_dfs = []
            loaded_files = []

            for filename in quarterly_files:
                cache_path = self.market_dir / filename
                if cache_path.exists():
                    try:
                        with open(cache_path, 'r') as f:
                            cache_data = json.load(f)

                        # Check if this is historical data (don't apply expiration to historical data)
                        metadata_end_str = cache_data['metadata']['end_date']
                        file_end_date = datetime.strptime(metadata_end_str, '%Y-%m-%d')
                        is_historical = file_end_date.date() < datetime.now().date() - timedelta(days=2)

                        # For historical data, ignore expiration
                        if not is_historical:
                            if 'expires_at' in cache_data['metadata']:
                                expires_at = datetime.fromisoformat(
                                    cache_data['metadata']['expires_at'])
                                if datetime.now() > expires_at:
                                    continue

                        # Convert to DataFrame
                        df = pd.DataFrame(cache_data['data'])
                        if 'date' in df.columns and not df.empty:
                            df['date'] = pd.to_datetime(df['date'])
                            df.set_index('date', inplace=True)
                            quarterly_dfs.append(df)
                            loaded_files.append(filename)

                    except Exception as e:
                        self.logger.warning(f"Could not load quarterly cache {filename}: {e}")
                        continue

            # Combine quarterly data if we have good coverage (at least 3 quarters)
            if len(quarterly_dfs) >= 3:
                combined = pd.concat(quarterly_dfs, axis=0)
                combined = combined.sort_index()
                combined = combined[~combined.index.duplicated(keep='first')]

                self.logger.debug(
                    f"Quarterly cache loaded: {len(loaded_files)} files, {len(combined)} days")
                return combined

            return None

        except Exception as e:
            self.logger.error(f"Error in quarterly cache loading: {e}")
            return None

    def _search_overlapping_cache(self, symbol: str, start: str, end: str, source: str) -> Optional[pd.DataFrame]:
        """
        Search for cached data with overlapping date ranges.

        This handles cases where we request a broad date range that spans 
        multiple cached files (e.g., requesting 2024-01-01 to 2024-12-31
        but having quarterly cache files).
        """
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")

            # Look for cache files that might contain our date range
            # Handle both regular and consolidated files
            pattern1 = f"{symbol}_*_{source}.json"
            pattern2 = f"{symbol}_*_{source}_consolidated.json"
            matching_files = list(self.market_dir.glob(pattern1)) + \
                list(self.market_dir.glob(pattern2))

            # Collect all overlapping data files
            overlapping_data = []

            for cache_file in matching_files:
                try:
                    # Parse filename to extract date range
                    name_parts = cache_file.stem.split('_')
                    if len(name_parts) < 4:
                        continue

                    file_start_str = name_parts[1]
                    file_end_str = name_parts[2]

                    # Skip if not proper date format
                    if len(file_start_str) != 10 or len(file_end_str) != 10:
                        continue

                    file_start_date = datetime.strptime(file_start_str, "%Y-%m-%d")
                    file_end_date = datetime.strptime(file_end_str, "%Y-%m-%d")

                    # Check if cached range overlaps with requested range
                    if file_start_date <= end_date and file_end_date >= start_date:
                        # Found overlapping range, load and filter data
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)

                        # Check expiration using date-aware logic
                        metadata_start_str = cache_data['metadata']['start_date']
                        metadata_end_str = cache_data['metadata']['end_date']
                        expected_expiry = self._calculate_market_data_expiration(
                            metadata_start_str, metadata_end_str)

                        # Use stored expiry if available, otherwise calculate
                        if 'expires_at' in cache_data['metadata']:
                            expires_at = datetime.fromisoformat(
                                cache_data['metadata']['expires_at'])
                        else:
                            expires_at = expected_expiry

                        # HISTORICAL DATA FIX: Don't expire historical market data (>2 days old)
                        # Historical data never changes, so expired cache is still valid
                        try:
                            file_end_date = datetime.strptime(metadata_end_str, '%Y-%m-%d')
                            is_historical = file_end_date.date() < datetime.now().date() - timedelta(days=2)

                            if not is_historical and datetime.now() > expires_at:
                                continue  # Only skip expired recent data, not historical data
                        except ValueError:
                            # If date parsing fails, fall back to original expiry check
                            if datetime.now() > expires_at:
                                continue

                        # Convert to DataFrame
                        df = pd.DataFrame(cache_data['data'])
                        if df.empty or 'date' not in df.columns:
                            continue

                        df['date'] = pd.to_datetime(df['date'])
                        df.set_index('date', inplace=True)

                        # Add to overlapping data list
                        overlapping_data.append((file_start_date, df, cache_file.name))

                except (ValueError, KeyError) as e:
                    # Skip files with parsing errors
                    continue

            # Combine overlapping data if found
            if overlapping_data:
                # Sort by start date to ensure proper chronological order
                overlapping_data.sort(key=lambda x: x[0])

                # PRIORITY FIX: Prefer larger files (quarterly) over smaller (incremental)
                # to avoid loading partial data when complete data exists

                # Check if we have quarterly files (90+ days) that can cover the full range
                quarterly_files = []
                incremental_files = []

                for start_date, df, filename in overlapping_data:
                    if len(df) >= 50:  # Quarterly files typically have 60-65 trading days
                        quarterly_files.append((start_date, df, filename))
                    else:
                        incremental_files.append((start_date, df, filename))

                # Use quarterly files if they provide good coverage
                if quarterly_files:
                    # Calculate total coverage from quarterly files
                    quarterly_dfs = [df for _, df, _ in quarterly_files]
                    if quarterly_dfs:
                        combined_quarterly = pd.concat(quarterly_dfs, axis=0)
                        combined_quarterly = combined_quarterly.sort_index()

                        # Remove duplicates (overlapping quarterly files)
                        combined_quarterly = combined_quarterly[~combined_quarterly.index.duplicated(
                            keep='first')]

                        # Check coverage quality - do quarterly files cover most of requested range?
                        requested_days = (end_date - start_date).days
                        actual_coverage = len(combined_quarterly)
                        # ~70% of calendar days are trading days
                        coverage_ratio = actual_coverage / max(requested_days * 0.7, 180)

                        if coverage_ratio > 0.8:  # If quarterly files provide 80%+ coverage
                            self.logger.debug(
                                f"Market data: Using quarterly files for better coverage "
                                f"({actual_coverage} days from {len(quarterly_files)} quarterly files)"
                            )
                            combined_df = combined_quarterly
                            self.logger.debug(
                                f"QUARTERLY PATH: Final combined_df has {len(combined_df)} rows")
                        else:
                            # Fall back to combining all files if quarterly coverage is poor
                            combined_dfs = [df for _, df, _ in overlapping_data]
                            combined_df = pd.concat(combined_dfs, axis=0)
                    else:
                        # No quarterly data, use incremental
                        combined_dfs = [df for _, df, _ in overlapping_data]
                        combined_df = pd.concat(combined_dfs, axis=0)
                else:
                    # No quarterly files found, combine all incremental files
                    combined_dfs = [df for _, df, _ in overlapping_data]
                    combined_df = pd.concat(combined_dfs, axis=0)

                # Remove duplicates (in case of overlapping ranges) and sort
                combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
                combined_df = combined_df.sort_index()

                # Filter to requested date range
                self.logger.debug(
                    f"BEFORE FILTERING: combined_df has {len(combined_df)} rows from {combined_df.index.min()} to {combined_df.index.max()}")
                self.logger.debug(
                    f"FILTER DEBUG: start_date={start_date} ({type(start_date)}), end_date={end_date} ({type(end_date)})")
                self.logger.debug(
                    f"FILTER DEBUG: index type={type(combined_df.index[0])}, timezone={combined_df.index.tz}")

                # Debug the mask application
                mask = (combined_df.index >= start_date) & (combined_df.index <= end_date)
                true_count = mask.sum()
                self.logger.debug(f"FILTER DEBUG: mask selected {true_count}/{len(mask)} rows")

                # Sample some comparisons to debug the issue
                sample_indices = combined_df.index[:5].tolist() + combined_df.index[-5:].tolist()
                for idx in sample_indices:
                    ge_start = idx >= start_date
                    le_end = idx <= end_date
                    self.logger.debug(
                        f"SAMPLE: {idx} >= {start_date}: {ge_start}, <= {end_date}: {le_end}")

                filtered_df = combined_df[mask]
                self.logger.debug(
                    f"AFTER FILTERING: filtered_df has {len(filtered_df)} rows from {filtered_df.index.min() if not filtered_df.empty else 'EMPTY'} to {filtered_df.index.max() if not filtered_df.empty else 'EMPTY'}")

                if not filtered_df.empty:
                    file_names = [name for _, _, name in overlapping_data]
                    self.logger.debug(
                        f"Market data cache hit (combined): {', '.join(file_names)} "
                        f"-> {len(filtered_df)} records for {start} to {end}"
                    )
                    return filtered_df

            self.logger.debug(
                f"No overlapping market data cache found for {symbol} {start} to {end}")
            return None

        except Exception as e:
            self.logger.error(f"Error in overlapping cache search: {e}")
            return None

    def set_market_data(self, symbol: str, start: str, end: str, source: str, data: pd.DataFrame):
        """
        Cache market data in standardized format.

        Stores OHLCV data consistently regardless of source.
        """
        if data.empty:
            return

        try:
            # Standardize DataFrame format
            df = data.copy()

            # Ensure standard columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    # Try common variants
                    for variant in [col.title(), col.upper()]:
                        if variant in df.columns:
                            df[col] = df[variant]
                            break
                    else:
                        self.logger.warning(f"Missing column {col} in market data")
                        return

            # Reset index to get date column
            if isinstance(df.index, pd.DatetimeIndex):
                df.reset_index(inplace=True)
                df.rename(columns={'index': 'date'}, inplace=True)
            elif 'date' not in df.columns and 'Date' in df.columns:
                df.rename(columns={'Date': 'date'}, inplace=True)

            # Ensure date is string for JSON serialization
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            # Create standardized cache structure with date-aware expiration
            expires_at = self._calculate_market_data_expiration(start, end)
            cache_data = {
                "metadata": {
                    "symbol": symbol,
                    "start_date": start,
                    "end_date": end,
                    "source": source,
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": expires_at.isoformat()
                },
                "data": df[['date', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
            }

            cache_key = self._get_market_cache_key(symbol, start, end, source)
            cache_path = self.market_dir / cache_key

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)

            self.logger.debug(f"Market data cached: {cache_key}")

        except Exception as e:
            self.logger.error(f"Error caching market data: {e}")

    def get_news(self, query: str, start: str, end: str, source: str = "google_search") -> Optional[pd.DataFrame]:
        """Get cached news data."""
        cache_key = self._get_news_cache_key(query, start, end, source)
        cache_path = self.news_dir / source / f"{cache_key}"

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)

            # Check expiration (7 days for news)
            cached_time = datetime.fromisoformat(cache_data['metadata']['cached_at'])
            if datetime.now() - cached_time > timedelta(days=7):
                self.logger.debug(f"News cache expired: {cache_key}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(cache_data['data'])
            self.logger.debug(f"News cache hit: {cache_key}")
            return df

        except Exception as e:
            self.logger.error(f"Error reading news cache {cache_key}: {e}")
            return None

    def set_news(self, query: str, start: str, end: str, data: pd.DataFrame, source: str = "google_search"):
        """Cache news data in standardized format."""
        if data.empty:
            return

        try:
            # Create source directory
            source_dir = self.news_dir / source
            source_dir.mkdir(exist_ok=True)

            cache_data = {
                "metadata": {
                    "query": query,
                    "start_date": start,
                    "end_date": end,
                    "source": source,
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
                },
                "data": data.to_dict('records')
            }

            cache_key = self._get_news_cache_key(query, start, end, source)
            cache_path = source_dir / cache_key

            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)

            self.logger.debug(f"News data cached: {cache_key}")

        except Exception as e:
            self.logger.error(f"Error caching news data: {e}")

    def cleanup_expired(self):
        """Remove expired cache files."""
        now = datetime.now()
        cleaned_count = 0

        # Clean market data (24h expiry)
        for cache_file in self.market_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)

                expires_at = datetime.fromisoformat(cache_data['metadata']['expires_at'])
                if now > expires_at:
                    cache_file.unlink()
                    cleaned_count += 1

            except Exception as e:
                self.logger.warning(f"Error checking expiry for {cache_file}: {e}")

        # Clean news data (7d expiry)
        for cache_file in self.news_dir.rglob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)

                expires_at = datetime.fromisoformat(cache_data['metadata']['expires_at'])
                if now > expires_at:
                    cache_file.unlink()
                    cleaned_count += 1

            except Exception as e:
                self.logger.warning(f"Error checking expiry for {cache_file}: {e}")

        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired cache files")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        market_files = list(self.market_dir.glob("*.json"))
        news_files = list(self.news_dir.rglob("*.json"))

        total_size = sum(f.stat().st_size for f in market_files + news_files)

        return {
            "market_data_files": len(market_files),
            "news_files": len(news_files),
            "total_files": len(market_files) + len(news_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dirs": {
                "market_data": str(self.market_dir),
                "news": str(self.news_dir),
                "metadata": str(self.metadata_dir)
            }
        }
