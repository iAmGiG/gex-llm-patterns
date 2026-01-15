"""
Simple Unified Cache Manager - Real Data Only

Structure:
.cache/
├── market_data/SPY/     # Real stock data
├── options/SPY/         # Real options data
├── news/SPY/           # Real news data
└── metadata/           # Cache stats

samples/                 # Synthetic data (separate)
├── options/SPY/
└── stocks/SPY/
"""

import json
import logging
from pathlib import Path

import pandas as pd

from src.utils.date_utils import get_datetime_from_timestamp, get_datetime_now, now_iso, subtract_days, today_str


class UnifiedCacheManager:
    """Simple unified cache manager for REAL data only."""

    def __init__(self, base_dir=".cache"):
        """Initialize cache manager."""
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Define cache directories (created lazily when needed)
        self.market_data_dir = self.base_dir / "market_data"
        self.options_dir = self.base_dir / "options"
        self.news_dir = self.base_dir / "news"
        self.metadata_dir = self.base_dir / "metadata"

        # Only create base directory, others created when first used
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Initialize GEX cache manager (lazy loading)
        self._gex_cache = None

        # SQLite options manager for get_or_calculate_gex internal use
        self._sqlite_options = None

    @property
    def sqlite_options(self):
        """Lazy-loaded SQLiteOptionsManager for internal GEX calculations only.

        Note: For options data access, use SQLiteOptionsManager directly.
        Issue #180: Deprecated wrapper methods removed.
        """
        if self._sqlite_options is None:
            from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager

            self._sqlite_options = SQLiteOptionsManager()
        return self._sqlite_options

    # === MARKET DATA ===

    def store_market_data(self, symbol, df: pd.DataFrame, start_date: str = None, end_date: str = None) -> bool:
        """Store real market/stock data.

        Args:
            symbol: Stock symbol
            df: OHLCV DataFrame with datetime index
            start_date: Optional start date override
            end_date: Optional end date override
        """
        try:
            # Generate filename from data if dates not provided
            if not start_date or not end_date:
                start_date = df.index.min().strftime("%Y-%m-%d")
                end_date = df.index.max().strftime("%Y-%m-%d")

            # Path: .cache/market_data/SPY/2024-01-01_2024-12-31.pickle
            symbol_dir = self.market_data_dir / symbol.upper()
            symbol_dir.mkdir(exist_ok=True)

            file_path = symbol_dir / f"{start_date}_{end_date}.pickle"
            df.to_pickle(file_path)

            self.logger.info(f"Stored {len(df)} {symbol} market records ({start_date} to {end_date})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store {symbol} market data: {e}")
            return False

    def get_market_data(self, symbol, start_date: str = None, end_date: str = None):
        """Get real market data.

        Args:
            symbol: Stock symbol
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        try:
            symbol_dir = self.market_data_dir / symbol.upper()

            if not symbol_dir.exists():
                return None

            # Find files that might contain our data
            for file_path in symbol_dir.glob("*.pickle"):
                df = pd.read_pickle(file_path)

                # Apply date filtering if specified
                if start_date:
                    df = df[df.index >= start_date]
                if end_date:
                    df = df[df.index <= end_date]

                if not df.empty:
                    self.logger.info(f"Loaded {len(df)} {symbol} market records")
                    return df

            return None

        except Exception as e:
            self.logger.error(f"Failed to load {symbol} market data: {e}")
            return None

    # === NEWS DATA ===

    def store_news_data(self, category, df: pd.DataFrame, date_range: str = None) -> bool:
        """Store real news data.

        Args:
            category: News category (SPY, general, earnings, etc.)
            df: News DataFrame
            date_range: Optional date range string
        """
        try:
            # Generate date range if not provided
            if not date_range and "timestamp" in df.columns:
                start = df["timestamp"].min().strftime("%Y-%m-%d")
                end = df["timestamp"].max().strftime("%Y-%m-%d")
                date_range = f"{start}_{end}"
            elif not date_range:
                date_range = today_str()

            # Path: .cache/news/SPY/2024-01-01_2024-12-31.json
            category_dir = self.news_dir / category
            category_dir.mkdir(exist_ok=True)

            file_path = category_dir / f"{date_range}.json"
            # Convert DataFrame to JSON for news data
            with open(file_path, "w") as f:
                json.dump(df.to_dict("records"), f, indent=2, default=str)

            self.logger.info(f"Stored {len(df)} {category} news records")
            return True

        except Exception as e:
            self.logger.error(f"Failed to store {category} news: {e}")
            return False

    def get_news_data(self, category, start_date: str = None, end_date: str = None):
        """Get real news data.

        Args:
            category: News category
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        try:
            category_dir = self.news_dir / category

            if not category_dir.exists():
                return None

            # Find and load news files
            for file_path in category_dir.glob("*.json"):
                with open(file_path, "r") as f:
                    data = json.load(f)
                df = pd.DataFrame(data)

                # Apply date filtering if specified and timestamp exists
                if "timestamp" in df.columns:
                    # Convert timestamp strings back to datetime
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    if start_date:
                        df = df[df["timestamp"] >= start_date]
                    if end_date:
                        df = df[df["timestamp"] <= end_date]

                if not df.empty:
                    self.logger.info(f"Loaded {len(df)} {category} news records")
                    return df

            return None

        except Exception as e:
            self.logger.error(f"Failed to load {category} news: {e}")
            return None

    # === METADATA & STATS ===

    def get_cache_summary(self) -> dict:
        """Get summary of cached data."""
        summary = {"market_data": {}, "options": {}, "news": {}, "total_files": 0, "total_size_mb": 0.0}

        try:
            # Count files in each category
            for category, directory in [
                ("market_data", self.market_data_dir),
                ("options", self.options_dir),
                ("news", self.news_dir),
            ]:
                if directory.exists():
                    for ticker_dir in directory.iterdir():
                        if ticker_dir.is_dir():
                            ticker = ticker_dir.name
                            files = list(ticker_dir.glob("*.pickle"))

                            if files:
                                summary[category][ticker] = len(files)
                                summary["total_files"] += len(files)

                                # Calculate size
                                for file_path in files:
                                    summary["total_size_mb"] += file_path.stat().st_size / (1024 * 1024)

            return summary

        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return summary

    def get_options_cache_summary(self) -> dict:
        """Get detailed options cache summary."""
        summary = {"tickers": {}, "total_contracts": 0}

        try:
            if self.options_dir.exists():
                for ticker_dir in self.options_dir.iterdir():
                    if ticker_dir.is_dir():
                        ticker = ticker_dir.name
                        dates = []
                        total_contracts = 0

                        for file_path in ticker_dir.glob("*.pickle"):
                            date = file_path.stem
                            dates.append(date)

                            try:
                                df = pd.read_pickle(file_path)
                                total_contracts += len(df)
                            except Exception:
                                pass

                        if dates:
                            summary["tickers"][ticker] = {
                                "dates": sorted(dates),
                                "date_count": len(dates),
                                "total_contracts": total_contracts,
                            }
                            summary["total_contracts"] += total_contracts

            return summary

        except Exception as e:
            self.logger.error(f"Failed to generate options summary: {e}")
            return summary

    def cleanup_cache(self, older_than_days: int = 30) -> int:
        """Clean up old cache files."""
        try:
            cutoff_time = subtract_days(get_datetime_now(), older_than_days)
            cleaned = 0

            for file_path in self.base_dir.rglob("*.pickle"):
                if file_path.is_file():
                    file_time = get_datetime_from_timestamp(file_path.stat().st_mtime)

                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned += 1

            self.logger.info(f"Cleaned {cleaned} cache files older than {older_than_days} days")
            return cleaned

        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {e}")
            return 0

    # === GEX CACHE INTEGRATION ===

    @property
    def gex_cache(self):
        """Lazy-loaded GEX cache manager."""
        if self._gex_cache is None:
            from gex_db_infrastructure.cache.gex_cache_manager import GEXCacheManager

            self._gex_cache = GEXCacheManager(str(self.base_dir))
        return self._gex_cache

    def get_or_calculate_gex(self, symbol, trading_date) -> dict:
        """Get GEX from cache or calculate if missing. Integration point for seamless GEX caching.

        Args:
            symbol: Stock symbol (SPY, SPX, etc.)
            trading_date: Trading date in YYYY-MM-DD format

        Returns:
            GEX summary dict or None if calculation fails
        """
        try:
            # 1. Check GEX cache first
            cached_gex = self.gex_cache.get_gex_summary(symbol, trading_date)
            if cached_gex:
                self.logger.debug(f"GEX cache hit for {symbol} {trading_date}")
                return cached_gex

            # 2. Get options data (Issue #180: directly from SQLite)
            options_data = self.sqlite_options.get_options_chain(symbol, trading_date)

            if options_data is None or options_data.empty:
                self.logger.warning(f"No options data available for GEX calculation: {symbol} {trading_date}")
                return None

            # 3. Calculate GEX using live data engine
            from gex_db_infrastructure.gex.live_gex_interface import LiveGEXInterface

            gex_interface = LiveGEXInterface()

            gex_results = gex_interface.calculate_gex_for_symbol(
                symbol=symbol,
                trading_date=trading_date,
                spot_price=None,  # Auto-detect from data
                options_data=options_data,  # Pass the live cached data
            )

            if gex_results and gex_results.get("status") == "success":
                # Extract and enhance summary for caching
                gex_summary = gex_results.get("metrics", {})
                gex_summary.update(
                    {
                        "symbol": symbol,
                        "trading_date": trading_date,
                        "calculation_timestamp": now_iso(),
                        "calculation_metadata": {
                            "options_contracts_processed": len(options_data),
                            "calculation_method": "unified_cache_auto_calculation",
                            "calculation_duration_ms": gex_results.get("calculation_time_ms", 0),
                        },
                    }
                )

                # 4. Cache the results
                success = self.gex_cache.store_gex_calculation(symbol, trading_date, gex_summary)

                if success:
                    self.logger.info(f"Calculated and cached GEX for {symbol} {trading_date}")

                return gex_summary
            else:
                self.logger.error(f"GEX calculation failed for {symbol} {trading_date}: {gex_results}")
                return None

        except Exception as e:
            self.logger.error(f"GEX get_or_calculate failed for {symbol} {trading_date}: {e}")
            return None

    def batch_get_gex(self, requests: list) -> dict:
        """Efficient batch GEX retrieval.

        Args:
            requests: List of (symbol, trading_date) tuples

        Returns:
            Dict mapping "symbol_date" to GEX results
        """
        try:
            # Use GEX cache manager's batch functionality
            return self.gex_cache.batch_get_gex(requests)
        except Exception as e:
            self.logger.error(f"Batch GEX retrieval failed: {e}")
            return {}

    def get_gex_cache_stats(self) -> dict:
        """Get GEX cache statistics."""
        try:
            return self.gex_cache.get_cache_stats()
        except Exception as e:
            self.logger.error(f"Failed to get GEX cache stats: {e}")
            return {"error": str(e)}


# === SAMPLE DATA LOADER (for synthetic data) ===


class SampleDataLoader:
    """Load synthetic data from samples/ directory."""

    def __init__(self, samples_dir="samples"):
        self.samples_dir = Path(samples_dir)

    def get_sample_options(self, symbol, date):
        """Load synthetic options data."""
        try:
            file_path = self.samples_dir / "options" / symbol.upper() / f"{date}.json"

            if file_path.exists():
                with open(file_path, "r") as f:
                    data = json.load(f)

                df = pd.DataFrame(data)

                # Convert datetime columns
                datetime_cols = ["date", "expiration", "trading_date"]
                for col in datetime_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])

                return df

            return None

        except Exception as e:
            print(f"Failed to load sample options: {e}")
            return None

    def get_sample_stocks(self, symbol, date_range=None):
        """Load synthetic stock data."""
        try:
            symbol_dir = self.samples_dir / "stocks" / symbol.upper()

            if not symbol_dir.exists():
                return None

            # Find any stock file if date_range not specified
            for file_path in symbol_dir.glob("*.json"):
                with open(file_path, "r") as f:
                    data = json.load(f)

                if isinstance(data, dict) and "dates" in data:
                    df = pd.DataFrame(data["data"])
                    df.index = pd.to_datetime(data["dates"])
                else:
                    df = pd.DataFrame(data)
                    if "Date" in df.columns:
                        df.index = pd.to_datetime(df["Date"])
                        df.drop("Date", axis=1, inplace=True)

                return df

            return None

        except Exception as e:
            print(f"Failed to load sample stocks: {e}")
            return None
