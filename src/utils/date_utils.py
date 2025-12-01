"""Utilities for dynamic date handling in data tools."""

import datetime
import os
import re

from src.utils.config_manager import get_config

config = get_config()


DEFAULT_TIMEZONE = "America/New_York"


def get_default_timezone() -> str:
    """Return the configured default timezone."""
    return os.getenv(
        "DEFAULT_TIMEZONE",
        config.get("DEFAULT_TIMEZONE", DEFAULT_TIMEZONE),
    )


def localize_df(df, tz):
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


def get_default_date_range(days_back=5):
    """Calculate a default date range based on the current date. Returns (start_date, end_date) as strings in YYYY-MM-DD
    format.

    Args:
        days_back: Number of trading days to look back (default: 5)

    Returns:
        Tuple of (start_date, end_date) strings in YYYY-MM-DD format
    """
    # Get today's date, ensuring we use the current system time
    end_date = datetime.datetime.now()

    # Log the actual date being used (for debugging)
    print(f"Current date used for calculations: {end_date.strftime('%Y-%m-%d')}")

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


def process_date_param(date_param):
    """Process a date parameter that might be a relative date string. Handles special strings like "today", "yesterday",
    "-7d", etc.

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


def get_processed_date_range(start_date=None, end_date=None, default_days_back=5):
    """Process start and end date parameters, applying defaults if needed.

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
                year_start = pd.Timestamp(df.index[-1].year, 1, 1, tz=df.index.tz)
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


# === COMMON DATETIME UTILITIES ===
# Consolidation functions to reduce datetime import duplication across modules


def get_datetime_now() -> datetime.datetime:
    """Get current datetime object.

    Returns:
        Current datetime.datetime object
    """
    return datetime.datetime.now()


def get_datetime_from_timestamp(timestamp: float) -> datetime.datetime:
    """Convert Unix timestamp to datetime object.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        datetime.datetime object
    """
    return datetime.datetime.fromtimestamp(timestamp)


def subtract_days(dt: datetime.datetime, days: int) -> datetime.datetime:
    """Subtract days from a datetime object.

    Args:
        dt: datetime object
        days: Number of days to subtract

    Returns:
        New datetime object with days subtracted
    """
    return dt - datetime.timedelta(days=days)


def now_iso() -> str:
    """Get current timestamp as ISO string.

    Returns:
        Current timestamp in ISO format (YYYY-MM-DDTHH:MM:SS.ffffff)
    """
    return datetime.datetime.now().isoformat()


def now_timestamp() -> str:
    """Get current timestamp formatted for filenames/IDs.

    Returns:
        Current timestamp as YYYYMMDD_HHMMSS string
    """
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def today_str() -> str:
    """Get today's date as string.

    Returns:
        Today's date in YYYY-MM-DD format
    """
    return datetime.datetime.now().strftime("%Y-%m-%d")


def add_business_days(date_str, days) -> str:
    """Add business days to a date string.

    Args:
        date_str: Date in YYYY-MM-DD format
        days: Number of business days to add (can be negative)

    Returns:
        New date in YYYY-MM-DD format
    """
    import pandas as pd

    # Convert to datetime
    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")

    # Add business days using pandas
    result_dt = pd.bdate_range(start=dt, periods=abs(days) + 1, freq="B")

    if days >= 0:
        return result_dt[-1].strftime("%Y-%m-%d")
    else:
        # For negative days, go backwards
        result_dt = pd.bdate_range(end=dt, periods=abs(days) + 1, freq="B")
        return result_dt[0].strftime("%Y-%m-%d")


def parse_date_string(date_str) -> datetime.datetime:
    """Parse various date string formats to datetime object. Supports both real dates and obfuscated dates from data
    obfuscation system.

    Args:
        date_str: Date string in various formats, including obfuscated "Day T+N" format

    Returns:
        datetime.datetime object

    Raises:
        ValueError: If date string cannot be parsed
    """
    # Handle obfuscated date format (e.g., "Day T+0", "Day T+5", "Day T-2")
    if isinstance(date_str, str) and date_str.startswith("Day T"):
        try:
            # Extract the offset from "Day T+N" or "Day T-N" format
            if "T+" in date_str:
                offset_str = date_str.split("T+")[1]
                offset = int(offset_str)
            elif "T-" in date_str:
                offset_str = date_str.split("T-")[1]
                offset = -int(offset_str)
            else:  # "Day T+0" case
                offset = 0

            # Use a base date for obfuscated dates (arbitrary but consistent)
            # This allows date arithmetic to work properly
            base_date = datetime.datetime(2020, 1, 1)  # Arbitrary base date
            result_date = base_date + datetime.timedelta(days=offset)

            return result_date

        except (ValueError, IndexError) as e:
            raise ValueError(f"Unable to parse obfuscated date string: {date_str}") from e

    # Handle standard date formats
    formats_to_try = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]

    for fmt in formats_to_try:
        try:
            return datetime.datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date string: {date_str}")


def date_range_trading_days(start_date, end_date) -> list:
    """Generate list of trading days between start and end dates.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of trading day strings in YYYY-MM-DD format
    """
    import pandas as pd

    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    # Generate business days
    trading_days = pd.bdate_range(start=start_dt, end=end_dt, freq="B")

    return [dt.strftime("%Y-%m-%d") for dt in trading_days]


def calculate_duration_minutes(start_iso, end_iso) -> float:
    """Calculate duration in minutes between two ISO timestamp strings.

    Args:
        start_iso: Start timestamp in ISO format
        end_iso: End timestamp in ISO format

    Returns:
        Duration in minutes as float
    """
    start_dt = datetime.datetime.fromisoformat(start_iso)
    end_dt = datetime.datetime.fromisoformat(end_iso)

    return (end_dt - start_dt).total_seconds() / 60


def next_business_day(date_str) -> str:
    """Get the next business day after the given date.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Next business day in YYYY-MM-DD format
    """
    return add_business_days(date_str, 1)


def is_opex_week(date) -> bool:
    """Check if date is in OPEX week (third Friday of the month).

    Args:
        date: Date as string (YYYY-MM-DD) or datetime object

    Returns:
        True if date is in OPEX week
    """
    # Ensure date is a datetime object
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, "%Y-%m-%d")

    # Third Friday of the month
    first_day = date.replace(day=1)
    first_friday = first_day + datetime.timedelta(days=(4 - first_day.weekday()) % 7)
    third_friday = first_friday + datetime.timedelta(weeks=2)

    # Check if within OPEX week (Mon-Fri of third Friday week)
    week_start = third_friday - datetime.timedelta(days=third_friday.weekday())
    week_end = week_start + datetime.timedelta(days=4)

    return week_start <= date <= week_end


def is_business_day(date_str) -> bool:
    """Check if a date is a business day (Monday-Friday, excluding holidays).

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        True if it's a business day, False otherwise
    """
    import pandas as pd

    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")

    # Check if it's a weekday
    if dt.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False

    # Check against US market holidays (basic check)
    # This could be enhanced with a proper holiday calendar
    return True


def is_valid_trading_date(date_str: str, allow_future: bool = False) -> bool:
    """Check if a date is a valid trading date (business day and not in future).

    Args:
        date_str: Date in YYYY-MM-DD format
        allow_future: If True, allow future dates (default False)

    Returns:
        True if valid trading date, False otherwise
    """
    try:
        import pytz

        # Parse the date
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")

        # Check if it's a business day
        if not is_business_day(date_str):
            return False

        # Check if it's in the future
        if not allow_future:
            # Get current time in EDT/EST
            eastern = pytz.timezone("America/New_York")
            now = datetime.datetime.now(eastern).replace(tzinfo=None)

            # Date is in the future if after today
            if dt.date() > now.date():
                return False

        # Check if it's too far in the past (before 2000)
        if dt.year < 2000:
            return False

        return True

    except (ValueError, TypeError):
        return False


def format_for_filename(dt: datetime.datetime = None) -> str:
    """Format datetime for use in filenames (no special characters).

    Args:
        dt: datetime object (defaults to now)

    Returns:
        Formatted string safe for filenames
    """
    if dt is None:
        dt = datetime.datetime.now()

    return dt.strftime("%Y%m%d_%H%M%S")


def get_market_open_time(date_str, timezone: str = "America/New_York") -> datetime.datetime:
    """Get market open time for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format
        timezone: Market timezone (default: America/New_York)

    Returns:
        datetime object for market open (9:30 AM ET)
    """
    import pytz

    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")

    # Set to 9:30 AM
    market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)

    # Localize to market timezone
    tz = pytz.timezone(timezone)
    return tz.localize(market_open)


def get_market_close_time(date_str, timezone: str = "America/New_York") -> datetime.datetime:
    """Get market close time for a given date.

    Args:
        date_str: Date in YYYY-MM-DD format
        timezone: Market timezone (default: America/New_York)

    Returns:
        datetime object for market close (4:00 PM ET)
    """
    import pytz

    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")

    # Set to 4:00 PM
    market_close = dt.replace(hour=16, minute=0, second=0, microsecond=0)

    # Localize to market timezone
    tz = pytz.timezone(timezone)
    return tz.localize(market_close)


def calculate_days_to_expiration(expiration_dates, trade_dates):
    """Calculate days to expiration for options data. Handles both pandas Series and individual dates, and supports
    obfuscated dates.

    Args:
        expiration_dates: pandas Series or single date value representing expiration dates
        trade_dates: pandas Series or single date value representing trade dates

    Returns:
        pandas Series or int: Days to expiration for each option contract
    """
    import pandas as pd

    # Convert to pandas datetime if not already
    if not isinstance(expiration_dates, pd.Series):
        expiration_dates = pd.to_datetime(expiration_dates)
    if not isinstance(trade_dates, pd.Series):
        trade_dates = pd.to_datetime(trade_dates)

    # Handle obfuscated dates by parsing them first
    if isinstance(expiration_dates, pd.Series) and expiration_dates.dtype == "object":
        expiration_dates = expiration_dates.apply(lambda x: parse_date_string(str(x)) if isinstance(x, str) else x)
        expiration_dates = pd.to_datetime(expiration_dates)

    if isinstance(trade_dates, pd.Series) and trade_dates.dtype == "object":
        trade_dates = trade_dates.apply(lambda x: parse_date_string(str(x)) if isinstance(x, str) else x)
        trade_dates = pd.to_datetime(trade_dates)

    # Calculate the difference in days
    days_diff = (expiration_dates - trade_dates).dt.days

    return days_diff
