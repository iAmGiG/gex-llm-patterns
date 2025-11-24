"""Alpha Vantage Sample Data Loader Handles loading and parsing of sample Alpha Vantage options data for testing and
development without API calls."""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class AlphaVantageSampleLoader:
    """Load and parse Alpha Vantage sample options data."""

    def __init__(self, sample_file_path=None):
        """Initialize the sample data loader.

        Args:
            sample_file_path: Path to the sample JSON file.
                            Defaults to .cache/sample_alpha_vantage/alpha_vantage_sample02.json
        """
        if sample_file_path is None:
            base_dir = Path(__file__).parent.parent.parent
            sample_file_path = base_dir / ".cache" / "sample_alpha_vantage" / "alpha_vantage_sample02.json"

        self.sample_file = Path(sample_file_path)
        self._data_cache = None
        self._df_cache = None

    def load_raw_data(self):
        """Load raw JSON data from sample file.

        Returnsionary containing the raw Alpha Vantage response
        """
        if self._data_cache is not None:
            return self._data_cache

        if not self.sample_file.exists():
            raise FileNotFoundError(f"Sample data file not found: {self.sample_file}")

        logger.info(f"Loading sample data from {self.sample_file}")

        with open(self.sample_file, "r") as f:
            self._data_cache = json.load(f)

        logger.info(f"Loaded {len(self._data_cache.get('data', []))} option contracts")
        return self._data_cache

    def to_dataframe(self):
        """Convert sample data to a pandas DataFrame.

        Returns:
            DataFrame with parsed options data
        """
        if self._df_cache is not None:
            return self._df_cache

        data = self.load_raw_data()

        if "data" not in data:
            raise ValueError("Invalid data format: missing 'data' key")

        df = pd.DataFrame(data["data"])

        # Convert numeric columns
        numeric_columns = [
            "strike",
            "last",
            "mark",
            "bid",
            "ask",
            "volume",
            "open_interest",
            "bid_size",
            "ask_size",
            "implied_volatility",
            "delta",
            "gamma",
            "theta",
            "vega",
            "rho",
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse dates
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        if "expiration" in df.columns:
            df["expiration"] = pd.to_datetime(df["expiration"])

        # Add derived columns
        df["days_to_expiry"] = (df["expiration"] - df["date"]).dt.days
        df["moneyness"] = df["strike"] / df.groupby("symbol")["mark"].transform("mean")

        self._df_cache = df
        return df

    def get_options_chain(self, symbol, date=None):
        """Get options chain for a specific symbol and date.

        Args:
            symbol: Stock symbol (e.g., 'IBM')
            date: Options data date (YYYY-MM-DD format). If None, returns all dates.

        Returns:
            DataFrame filtered for the specified symbol and date
        """
        df = self.to_dataframe()

        # Filter by symbol
        chain = df[df["symbol"] == symbol].copy()

        # Filter by date if specified
        if date:
            date_dt = pd.to_datetime(date)
            chain = chain[chain["date"] == date_dt]

        if chain.empty:
            logger.warning(f"No data found for symbol={symbol}, date={date}")
        else:
            logger.info(f"Found {len(chain)} contracts for {symbol}")

        return chain

    def get_unique_symbols(self):
        """Get list of unique symbols in the sample data."""
        df = self.to_dataframe()
        return df["symbol"].unique().tolist()

    def get_date_range(self):
        """Get the date range of the sample data."""
        df = self.to_dataframe()
        return {"start": df["date"].min().strftime("%Y-%m-%d"), "end": df["date"].max().strftime("%Y-%m-%d")}

    def get_expiration_dates(self, symbol=None):
        """Get unique expiration dates.

        Args:
            symbol: If specified, returns expirations only for that symbol

        Returns of expiration dates in YYYY-MM-DD format
        """
        df = self.to_dataframe()

        if symbol:
            df = df[df["symbol"] == symbol]

        exp_dates = df["expiration"].dt.strftime("%Y-%m-%d").unique().tolist()
        return sorted(exp_dates)

    def get_strikes(self, symbol, expiration):
        """Get all strikes for a symbol and expiration.

        Args:
            symbol: Stock symbol
            expiration: Expiration date (YYYY-MM-DD)

        Returns:
            Sorted list of strike prices
        """
        df = self.to_dataframe()
        exp_dt = pd.to_datetime(expiration)

        strikes = df[(df["symbol"] == symbol) & (df["expiration"] == exp_dt)]["strike"].unique()

        return sorted(strikes.tolist())

    def filter_by_greeks(self, min_delta=None, max_delta=None, min_gamma=None, min_volume=None):
        """Filter options by Greek values and volume.

        Args:
            min_delta: Minimum delta value
            max_delta: Maximum delta value
            min_gamma: Minimum gamma value
            min_volume: Minimum volume

        Returns:
            Filtered DataFrame
        """
        df = self.to_dataframe()

        if min_delta is not None:
            df = df[df["delta"] >= min_delta]
        if max_delta is not None:
            df = df[df["delta"] <= max_delta]
        if min_gamma is not None:
            df = df[df["gamma"] >= min_gamma]
        if min_volume is not None:
            df = df[df["volume"] >= min_volume]

        return df

    def get_summary_stats(self):
        """Get summary statistics about the sample data."""
        df = self.to_dataframe()

        return {
            "total_contracts": len(df),
            "unique_symbols": df["symbol"].nunique(),
            "unique_dates": df["date"].nunique(),
            "unique_expirations": df["expiration"].nunique(),
            "date_range": self.get_date_range(),
            "avg_implied_vol": df["implied_volatility"].mean(),
            "total_open_interest": df["open_interest"].sum(),
            "total_volume": df["volume"].sum(),
            "put_call_ratio": len(df[df["type"] == "put"]) / len(df[df["type"] == "call"]),
        }


class SampleDataProvider:
    """Provides a cache-like interface for agents to retrieve sample data.

    Mimics the behavior of pulling from cache/API.
    """

    def __init__(self, loader=None):
        """Initialize the data provider.

        Args:
            loader: AlphaVantageSampleLoader instance. Creates new one if None.
        """
        self.loader = loader or AlphaVantageSampleLoader()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the data provider by loading sample data."""
        if not self._initialized:
            self.loader.load_raw_data()
            self._initialized = True
            logger.info("Sample data provider initialized")

    def fetch_options_data(self, symbol, date=None, use_cache=True):
        """Fetch options data with cache-like interface.

        Args:
            symbol: Stock symbol
            date: Options date (YYYY-MM-DD)
            use_cache: Ignored for sample data, but maintains interface compatibility

        Returns:
            Options chain DataFrame
        """
        self.initialize()
        return self.loader.get_options_chain(symbol, date)

    def fetch_available_symbols(self):
        """Get available symbols in the sample data."""
        self.initialize()
        return self.loader.get_unique_symbols()

    def fetch_available_dates(self, symbol):
        """Get available dates for a symbol."""
        self.initialize()
        df = self.loader.to_dataframe()
        dates = df[df["symbol"] == symbol]["date"].dt.strftime("%Y-%m-%d").unique()
        return sorted(dates.tolist())

    def is_data_available(self, symbol, date) -> bool:
        """Check if data is available for symbol and date.

        Args:
            symbol: Stock symbol
            date: Date in YYYY-MM-DD format

        Returns:
            True if data exists
        """
        self.initialize()
        chain = self.loader.get_options_chain(symbol, date)
        return not chain.empty
