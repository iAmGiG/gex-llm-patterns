"""
Common data schemas for standardizing data from different sources.
Merged from general_normalizer.py with existing options schemas.
"""

import pandas as pd
import re
from typing import Dict
##################################
# Standard Data Schemas
##################################

# Schema for options data (from existing options_normalizer.py)
OPTIONS_SCHEMA = {
    "symbol": "str",                    # Underlying symbol (SPY, SPX, etc.)
    "strike": "float",                  # Strike price
    "expiration": "datetime64[ns]",     # Expiration date
    "option_type": "str",               # "call" or "put"
    "last_price": "float",              # Last traded price
    "bid": "float",                     # Bid price
    "ask": "float",                     # Ask price
    "volume": "float",                  # Trading volume
    "open_interest": "float",           # Open interest
    "implied_volatility": "float",      # Implied volatility
    "delta": "float",                   # Delta Greek
    "gamma": "float",                   # Gamma Greek
    "theta": "float",                   # Theta Greek
    "vega": "float",                    # Vega Greek
    "rho": "float",                     # Rho Greek
    "source": "str",                    # Data source
    "timestamp": "datetime64[ns]",      # Data timestamp
}

# Schema for market/stock data
MARKET_SCHEMA = {
    "timestamp": "datetime64[ns]",      # Date/time of the data point
    "symbol": "str",                    # Stock/asset symbol
    "open": "float",                    # Opening price
    "high": "float",                    # High price
    "low": "float",                     # Low price
    "close": "float",                   # Closing price
    "volume": "float",                  # Trading volume
    # Data source (e.g., "Polygon", "AlphaVantage")
    "source": "str",
}

# Schema for news/text data
NEWS_SCHEMA = {
    "timestamp": "datetime64[ns]",      # When the article/data was published
    "title": "str",                     # Article title or headline
    "content": "str",                   # Main content text
    # Source of the content (e.g., "Bloomberg", "Reuters")
    "source": "str",
    "url": "str",                       # URL to the original content
    "sentiment_score": "float",         # Pre-calculated sentiment score if available
    "keywords": "object",               # List of keywords or tags
    # News category (e.g., "Economy", "Markets", "Technology")
    "category": "str",
}

# Schema for economic data (from FRED and similar sources)
ECONOMIC_SCHEMA = {
    "timestamp": "datetime64[ns]",      # Date/time of the data point
    # Economic indicator name/code (e.g., "GDP", "UNRATE")
    "indicator": "str",
    "value": "float",                   # Value of the indicator
    # Units of measurement (e.g., "Percent", "Billions of Dollars")
    "units": "str",
    # Data frequency (e.g., "Monthly", "Quarterly")
    "frequency": "str",
    "title": "str",                     # Full title/description of the indicator
    "source": "str",                    # Data source (e.g., "FRED", "BEA")
}

##################################
# Schema Creation Functions
##################################


def create_empty_dataframe(schema: Dict[str, str]) -> pd.DataFrame:
    """Create an empty DataFrame with the specified schema."""
    return pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in schema.items()})


def create_empty_options_df() -> pd.DataFrame:
    """Create an empty DataFrame with the standard options schema."""
    return create_empty_dataframe(OPTIONS_SCHEMA)


def create_empty_market_df() -> pd.DataFrame:
    """Create an empty DataFrame with the standard market schema."""
    return create_empty_dataframe(MARKET_SCHEMA)


def create_empty_news_df() -> pd.DataFrame:
    """Create an empty DataFrame with the standard news schema."""
    return create_empty_dataframe(NEWS_SCHEMA)


def create_empty_economic_df() -> pd.DataFrame:
    """Create an empty DataFrame with the standard economic data schema."""
    return create_empty_dataframe(ECONOMIC_SCHEMA)

##################################
# Data Normalization Functions
##################################


def standardize_indicator_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename indicator columns to `INDICATOR_param` format."""
    rename_map = {}
    pattern = re.compile(r"([A-Za-z]+)(\d+)$")
    for col in df.columns:
        m = pattern.match(col)
        if m:
            rename_map[col] = f"{m.group(1).upper()}_{m.group(2)}"
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def normalize_alpha_vantage_market_data(raw_df: pd.DataFrame, symbol) -> pd.DataFrame:
    """
    Normalize market data from Alpha Vantage to the common market schema.
    """
    if raw_df.empty:
        return create_empty_market_df()

    normalized_df = pd.DataFrame()

    # Check column names since Alpha Vantage might use different formats
    if "1. open" in raw_df.columns:
        # Map Alpha Vantage's numbered column format
        column_map = {
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close",
            "5. volume": "volume",
        }

        for av_col, norm_col in column_map.items():
            if av_col in raw_df.columns:
                normalized_df[norm_col] = raw_df[av_col]

        normalized_df["timestamp"] = raw_df.index

    elif "open" in raw_df.columns or "Open" in raw_df.columns:
        # Handle more standard column names
        col_mapping = {
            "open": "open", "Open": "open",
            "high": "high", "High": "high",
            "low": "low", "Low": "low",
            "close": "close", "Close": "close",
            "volume": "volume", "Volume": "volume",
        }

        for raw_col, norm_col in col_mapping.items():
            if raw_col in raw_df.columns:
                normalized_df[norm_col] = raw_df[raw_col]

        if "timestamp" not in normalized_df and "date" not in raw_df.columns:
            normalized_df["timestamp"] = raw_df.index
        elif "date" in raw_df.columns:
            normalized_df["timestamp"] = raw_df["date"]

    # Add symbol and source
    normalized_df["symbol"] = symbol
    normalized_df["source"] = "Alpha Vantage"

    return normalized_df


def normalize_polygon_market_data(raw_df: pd.DataFrame, symbol) -> pd.DataFrame:
    """
    Normalize market data from Polygon.io to the common market schema.
    """
    if raw_df.empty:
        return create_empty_market_df()

    normalized_df = pd.DataFrame()

    # Polygon typically uses lowercase OHLCV format
    col_mapping = {
        "o": "open", "open": "open", "Open": "open",
        "h": "high", "high": "high", "High": "high",
        "l": "low", "low": "low", "Low": "low",
        "c": "close", "close": "close", "Close": "close",
        "v": "volume", "volume": "volume", "Volume": "volume",
        "t": "timestamp", "timestamp": "timestamp",
    }

    for raw_col, norm_col in col_mapping.items():
        if raw_col in raw_df.columns:
            normalized_df[norm_col] = raw_df[raw_col]

    # Handle timestamp if not already mapped
    if "timestamp" not in normalized_df:
        if raw_df.index.name in ['date', 'timestamp']:
            normalized_df["timestamp"] = raw_df.index
        else:
            normalized_df["timestamp"] = pd.Timestamp.now()

    # Add symbol and source
    normalized_df["symbol"] = symbol
    normalized_df["source"] = "Polygon.io"

    return normalized_df

##################################
# Schema Validation
##################################


def validate_schema(df: pd.DataFrame, schema: Dict[str, str], strict: bool = False):
    """
    Validate a DataFrame against a schema.

    Args:
        df: DataFrame to validate
        schema: Expected schema dictionary
        strict: If True, require all schema columns to be present

    Returns:
        Dict with validation results
    """
    results = {
        "valid": True,
        "missing_columns": [],
        "extra_columns": [],
        "type_mismatches": [],
        "warnings": []
    }

    # Check for missing columns
    schema_cols = set(schema.keys())
    df_cols = set(df.columns)

    missing = schema_cols - df_cols
    extra = df_cols - schema_cols

    if missing:
        results["missing_columns"] = list(missing)
        if strict:
            results["valid"] = False
        else:
            results["warnings"].append(f"Missing columns: {list(missing)}")

    if extra:
        results["extra_columns"] = list(extra)
        results["warnings"].append(f"Extra columns: {list(extra)}")

    # Check data types for common columns
    common_cols = schema_cols & df_cols
    for col in common_cols:
        expected_type = schema[col]
        actual_type = str(df[col].dtype)

        # Simplified type checking (could be enhanced)
        if expected_type.startswith("datetime") and not pd.api.types.is_datetime64_any_dtype(df[col]):
            results["type_mismatches"].append(
                f"{col}: expected {expected_type}, got {actual_type}")
        elif expected_type == "float" and not pd.api.types.is_numeric_dtype(df[col]):
            results["type_mismatches"].append(
                f"{col}: expected {expected_type}, got {actual_type}")

    if results["type_mismatches"]:
        results["valid"] = False

    return results
