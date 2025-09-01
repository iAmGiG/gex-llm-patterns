"""
Utilities for dynamic date handling in data tools.
"""

from typing import Tuple, Optional
import re
import datetime
import os
from config.config_loader import ConfigLoader

config_loader = ConfigLoader()


DEFAULT_TIMEZONE = "America/New_York"


def get_default_timezone() -> str:
    """Return the configured default timezone."""
    return os.getenv(
        "DEFAULT_TIMEZONE",
        config_loader.get("DEFAULT_TIMEZONE", DEFAULT_TIMEZONE),
    )


def localize_df(df, tz: str):
    """Ensure a DataFrame index is timezone-aware using the provided timezone."""
    import pandas as pd

    if df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        for col in ["timestamp", "date", "datetime", "Date", "Timestamp"]:
            if col in df.columns:
                df = df.set_index(pd.to_datetime(df[col]))
                break
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a datetime index or column")

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(tz)
    return df


def get_default_date_range(days_back: int = 5) -> Tuple[str, str]:
    """
    Calculate a default date range based on the current date.
    Returns (start_date, end_date) as strings in YYYY-MM-DD format.

    Args:
        days_back: Number of trading days to look back (default: 5)

    Returns:
        Tuple of (start_date, end_date) strings in YYYY-MM-DD format
    """
    # Get today's date, ensuring we use the current system time
    end_date = datetime.datetime.now()

    # Log the actual date being used (for debugging)
    print(
        f"Current date used for calculations: {end_date.strftime('%Y-%m-%d')}")

    # Calculate start date (approximately days_back trading days)
    # Add extra days to account for weekends and holidays
    # Rough estimate to get N trading days
    calendar_days = int(days_back * 1.4)
    start_date = end_date - datetime.timedelta(days=calendar_days)

    # Format dates as strings
    end_date_str = end_date.strftime("%Y-%m-%d")
    start_date_str = start_date.strftime("%Y-%m-%d")

    print(f"Date range generated: {start_date_str} to {end_date_str}")

    return (start_date_str, end_date_str)


def process_date_param(date_param: Optional[str]) -> Optional[str]:
    """
    Process a date parameter that might be a relative date string.
    Handles special strings like "today", "yesterday", "-7d", etc.

    Args:
        date_param: Date string to process, can be:
                   - None (will return None)
                   - YYYY-MM-DD (will return as-is)
                   - "today", "yesterday"
                   - "-Nd" (N days ago)
                   - "-Nw" (N weeks ago)
                   - "-Nm" (N months ago)
                   - "ytd" (year to date)

    Returns:
        Processed date string in YYYY-MM-DD format or None
    """
    if date_param is None:
        return None

    # If it's already a YYYY-MM-DD format, return as-is
    if isinstance(date_param, str) and len(date_param) == 10 and date_param[4] == "-" and date_param[7] == "-":
        return date_param

    today = datetime.datetime.now()

    # Handle special string formats
    if date_param == "today":
        return today.strftime("%Y-%m-%d")

    if date_param == "yesterday":
        yesterday = today - datetime.timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")

    if date_param == "ytd":  # Year to date
        start_of_year = datetime.datetime(today.year, 1, 1)
        return start_of_year.strftime("%Y-%m-%d")

    # Handle relative formats like "-7d", "-4w", "-2m", "+30d"
    if isinstance(date_param, str) and (date_param.startswith("-") or date_param.startswith("+")):
        try:
            # Extract the numeric part and unit
            sign = 1 if date_param.startswith("+") else -1
            value = int(date_param[1:-1])
            unit = date_param[-1].lower()

            if unit == "d":  # Days
                result_date = today + datetime.timedelta(days=sign * value)
            elif unit == "w":  # Weeks
                result_date = today + datetime.timedelta(weeks=sign * value)
            elif unit == "m":  # Months (approximate)
                # Create a date with months added/subtracted
                month = today.month + (sign * value)
                year = today.year

                # Handle month/year rollover
                while month <= 0:
                    month += 12
                    year -= 1
                while month > 12:
                    month -= 12
                    year += 1

                # Create new date with same day but adjusted month/year
                result_date = today.replace(year=year, month=month)
            elif unit == "y":  # Years
                result_date = today.replace(year=today.year + (sign * value))
            else:
                # Unrecognized unit, return None
                return None

            return result_date.strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            # If parsing fails, return None
            return None

    # If we get here, the format wasn't recognized
    return None


def get_processed_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    default_days_back: int = 5
) -> Tuple[str, str]:
    """
    Process start and end date parameters, applying defaults if needed.

    Args:
        start_date: Optional start date string (YYYY-MM-DD or relative)
        end_date: Optional end date string (YYYY-MM-DD or relative)
        default_days_back: Default number of days to look back if no dates provided

    Returns:
        Tuple of processed (start_date, end_date) strings in YYYY-MM-DD format
    """
    # Process any relative date strings
    processed_start = process_date_param(start_date)
    processed_end = process_date_param(end_date)

    # If both dates are provided and valid, use them
    if processed_start and processed_end:
        return (processed_start, processed_end)

    # If only end_date is provided, calculate start_date based on default_days_back
    if not processed_start and processed_end:
        end_dt = datetime.datetime.strptime(processed_end, "%Y-%m-%d")
        calendar_days = int(default_days_back * 1.4)
        start_dt = end_dt - datetime.timedelta(days=calendar_days)
        return (start_dt.strftime("%Y-%m-%d"), processed_end)

    # If only start_date is provided, use today as end_date
    if processed_start and not processed_end:
        return (processed_start, datetime.datetime.now().strftime("%Y-%m-%d"))

    # If neither is provided, use default range
    return get_default_date_range(default_days_back)


def align_interval(df, interval):
    """Resample DataFrame to match the desired interval."""
    import pandas as pd

    if df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        for col in ["timestamp", "date", "datetime", "Date", "Timestamp"]:
            if col in df.columns:
                df = df.set_index(pd.to_datetime(df[col]))
                break
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have a datetime index or column")

    freq_map = {
        "1m": "1T",
        "5m": "5T",
        "15m": "15T",
        "30m": "30T",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
        "1w": "1W",
        "1M": "1M",
    }

    if interval not in freq_map:
        raise ValueError(f"Unsupported interval: {interval}")

    agg = {}
    for c in df.columns:
        lc = c.lower()
        if lc == "open":
            agg[c] = "first"
        elif lc == "high":
            agg[c] = "max"
        elif lc == "low":
            agg[c] = "min"
        elif lc == "close":
            agg[c] = "last"
        elif lc == "volume":
            agg[c] = "sum"
        else:
            agg[c] = "last"

    result = df.resample(freq_map[interval]).agg(agg)
    result = result.ffill().dropna(how="all")
    result.index.name = df.index.name
    return result


def resolve_anchor(df, anchor_token):
    """Resolve an anchor token to a timestamp within ``df``.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with a ``DatetimeIndex`` and optional event columns like
        ``Earnings_Date`` or ``FOMC_Date``.
    anchor_token : str | None
        ISO date string (``YYYY-MM-DD``) or one of ``earnings``, ``fomc`` or
        ``year_open``.

    Returns
    -------
    tuple[pd.Timestamp, Optional[str]]
        The resolved timestamp and an optional warning message when the token
        could not be matched.  If ``anchor_token`` is ``None`` the first index
        value is returned.
    """
    import pandas as pd
    warning = None

    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must be non-empty with a DatetimeIndex")

    anchor_ts = df.index[0]

    if not anchor_token:
        return pd.Timestamp(anchor_ts), warning

    try:
        # ISO date pattern
        if re.match(r"\d{4}-\d{2}-\d{2}", str(anchor_token)):
            ts = pd.Timestamp(anchor_token)
            idx = df.index.get_indexer([ts], method="nearest")[0]
            anchor_ts = df.index[idx]
        else:
            token = str(anchor_token).lower()
            if token == "year_open":
                year_start = pd.Timestamp(df.index[-1].year, 1, 1,
                                          tz=df.index.tz)
                idx = df.index.get_indexer([year_start], method="bfill")[0]
                anchor_ts = df.index[idx]
            elif token in {"earnings", "fomc"}:
                col_match = None
                for c in df.columns:
                    if token in c.lower():
                        col_match = c
                        break
                if col_match:
                    series = pd.to_datetime(df[col_match]).dropna()
                    if not series.empty:
                        anchor_ts = series.iloc[-1]
                    else:
                        warning = f"No {token} date found"
                else:
                    warning = f"No {token} date found"
    except Exception as e:  # pragma: no cover - unexpected edge cases
        warning = str(e)

    return pd.Timestamp(anchor_ts), warning
