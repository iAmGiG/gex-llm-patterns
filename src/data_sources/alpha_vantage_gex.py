# Copied from gex-database-infrastructure fc70767, which retires it (issue #272).
"""Alpha Vantage API Client for GEX-LLM Pattern Analysis.

This module specializes in retrieving options chain data from Alpha Vantage API for SPY/SPX gamma exposure calculations.
Optimized for entry premium tier rate limits (75 calls/min) with intelligent caching.

RETIREMENT (Issue #115, 2026-10-10)
-----------------------------------
The Alpha Vantage PREMIUM key was retired on 2026-10-10 (Dr. Xie: cost, no
renewal plan). It was the only source of options chains (REALTIME_OPTIONS /
HISTORICAL_OPTIONS for equities and the SPX/VIX/DJX roots), of the event
calendar (EARNINGS / EARNINGS_CALENDAR / DIVIDENDS) and of the nightly
TIME_SERIES_DAILY prices. The stored history (2008-01-02 -> 2026-10-09) is
complete and stays; nothing further can be fetched from this vendor.

The constructor is the kill switch:

- a premium key (env or config ``ALPHA_VANTAGE_PREMO_KEY``) is REFUSED with
  ``RuntimeError("Alpha Vantage premium key retired 2026-10-10 (Issue #115)")``
  unless ``GEX_ALLOW_ALPHA_VANTAGE_PREMIUM=1`` is set explicitly. A refused
  premium key never falls through to the free key: a stray premium key must
  surface as an error, not as a silently different tier;
- a FREE key alone (``ALPHA_VANTAGE_KEY``, 25 requests/day) constructs in
  free-tier mode (``is_free_tier`` True, free-tier limiter). It is for manual
  one-off lookups only; no scheduled caller (monitors, cron, backfills) may
  rely on it;
- no key at all raises ``RuntimeError`` - the old behaviour was a warning and
  a client that would then make keyless requests, which is exactly what the
  kill switch has to prevent in the monitors.

Callers that must keep running without the vendor (the two monitors,
``backfill_daily_summary.py``, ``backfill_equity_prices.py --use-polygon``)
catch the ``RuntimeError`` and run with the client set to ``None``.
Replacement options are tracked in Issue #115; see docs/029_VENDOR_RETIREMENT.md.
"""

import datetime
import logging
import os
import time
from collections import deque
from datetime import date

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ChunkedEncodingError, ConnectionError as RequestsConnectionError
from urllib3.exceptions import ProtocolError
from urllib3.util.retry import Retry

from gex_db_infrastructure.utils.config_loader import ConfigLoader

from gex_db_infrastructure.utils.config_manager import get_config
from gex_db_infrastructure.utils.date_utils import get_default_timezone, get_processed_date_range, localize_df

# The day the premium key stopped being used (Issue #115). Every scheduled
# options/calendar/price series from this vendor ends with the 2026-10-09
# session; status reporting and docs key off this date.
ALPHA_VANTAGE_RETIRED = date(2026, 10, 10)

# Explicit, manual-only override for the premium key (one-off repairs with a
# key that is known to still work). Never set it in cron, screen launchers or
# the monitors' environment.
PREMIUM_OVERRIDE_ENV = "GEX_ALLOW_ALPHA_VANTAGE_PREMIUM"
PREMIUM_RETIRED_MESSAGE = "Alpha Vantage premium key retired 2026-10-10 (Issue #115)"

# Free tier (vendor terms as of 2026-10): 25 requests per day, 5 per minute.
# The per-day cap is not enforced here - the free key is for manual one-off
# lookups, and a caller that needs more than 25 calls has no business on it.
FREE_TIER_CALLS_PER_MINUTE = 5
FREE_TIER_CALLS_PER_DAY = 25


class AlphaVantageGEXClient:
    """Alpha Vantage client specialized for GEX calculation data needs.

    Focuses on:
    - SPY/SPX options chains (historical and current)
    - Underlying stock price data
    - Rate limiting for free tier (75 calls/min)
    - Intelligent caching for historical data
    """

    def __init__(self, cache_manager=None, options_manager=None, calls_per_minute=None):
        """Initialize Alpha Vantage client.

        Args:
            cache_manager: Optional cache manager for market data (default: None, no
                           market-data cache; every call goes to the API)
            options_manager: Optional options storage manager, e.g. PostgreSQLOptionsManager
                           (default: None, options chains are neither read from nor
                           written to a store by this client)
            calls_per_minute: Optional per-INSTANCE ceiling that can only LOWER
                the tier limit, never raise it. The limiter is per process, and
                two monitor processes share one key; the index monitor caps
                itself so its post-close sweep plus the equity monitor's close
                sweep stay under the key's 75/min (Issue #75). Raising is
                refused because the deque below is sized from this number —
                a larger value would silently disable the limiter.

        Raises:
            RuntimeError: a premium key is configured and the
                ``GEX_ALLOW_ALPHA_VANTAGE_PREMIUM=1`` override is not set
                (Issue #115), or no key is configured at all.
        """
        # Load configuration from centralized config system
        config = get_config()

        # Key resolution (Issue #115): the premium key is looked at FIRST so
        # that its presence is always an error and never quietly bypassed by
        # a free key sitting next to it. Env overrides config for each name,
        # as before.
        config_loader = ConfigLoader()
        premium_key = os.getenv("ALPHA_VANTAGE_PREMO_KEY") or config_loader.get("ALPHA_VANTAGE_PREMO_KEY")
        free_key = os.getenv("ALPHA_VANTAGE_KEY") or config_loader.get("ALPHA_VANTAGE_KEY")

        if premium_key:
            if os.getenv(PREMIUM_OVERRIDE_ENV) != "1":
                raise RuntimeError(PREMIUM_RETIRED_MESSAGE)
            self.api_key = premium_key
            self.is_free_tier = False
            logging.warning(
                f"Alpha Vantage PREMIUM key in use under {PREMIUM_OVERRIDE_ENV}=1 "
                f"(retired {ALPHA_VANTAGE_RETIRED.isoformat()}, Issue #115) - manual override only"
            )
        elif free_key:
            self.api_key = free_key
            self.is_free_tier = True
            logging.info(
                f"Alpha Vantage FREE-tier key configured ({FREE_TIER_CALLS_PER_DAY} requests/day; "
                f"manual one-off lookups only, no scheduled caller may rely on it - Issue #115)"
            )
        else:
            raise RuntimeError(
                "Alpha Vantage API key not found in @config/ loader "
                f"(premium key retired {ALPHA_VANTAGE_RETIRED.isoformat()}, Issue #115)"
            )

        self.base_url = "https://www.alphavantage.co/query"
        self.logger = logging.getLogger(self.__class__.__name__)

        # Retry-mounted session (Issue #66). The ~30k-row SPX REALTIME_OPTIONS
        # payload produced a real mid-stream ChunkedEncodingError during live
        # probing (2026-07-24), so retry here is required, not defensive. The
        # urllib3 Retry covers connect/status errors; streamed-body failures
        # (ChunkedEncodingError/ProtocolError) escape it and are handled by the
        # explicit loop in _http_get.
        self.session = requests.Session()
        self.session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=1.5,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"],
                )
            ),
        )

        # Options storage manager via dependency injection (Issue #169 architectural fix)
        # Accepts e.g. PostgreSQLOptionsManager; None disables the store (the SQLite-era
        # defaults were removed in 2.0.0)
        self.options_manager = options_manager
        # Backward compatibility alias
        self.sqlite_options = self.options_manager
        # Optional cache for non-options data (market data); None = no cache
        self.cache = cache_manager

        # Load request timeout from config
        self.request_timeout = config.get("data_sources.alpha_vantage.request_timeout", 30)

        # Rate limiting - premium tier has higher limits (configurable)
        # Use deque with maxlen for O(1) rate limiting instead of O(n) list scan
        default_calls_per_minute = config.get("data_sources.alpha_vantage.calls_per_minute", 75)
        if not self.is_free_tier:
            # Honest ceiling (doc audit 2026-07-25): the lowest premium tier
            # sustains ~75 req/min in practice — the old 1000/min constant was
            # optimistic and made the limiter decorative. Serial call pacing
            # keeps us well under this anyway; the limiter is a backstop.
            self.calls_per_minute = 75
            logging.info("Using premium tier rate limits (75/min sustained)")
        else:
            # The config value was written for the premium key; a free key is
            # 5/min and 25/day whatever the config says.
            self.calls_per_minute = min(int(default_calls_per_minute), FREE_TIER_CALLS_PER_MINUTE)
            logging.info(f"Using free tier rate limits ({self.calls_per_minute}/min, "
                         f"{FREE_TIER_CALLS_PER_DAY}/day)")
        if calls_per_minute is not None:
            requested = int(calls_per_minute)
            if 0 < requested < self.calls_per_minute:
                logging.info(f"Alpha Vantage client capped at {requested}/min for this process "
                             f"(tier allows {self.calls_per_minute})")
                self.calls_per_minute = requested
            elif requested != self.calls_per_minute:
                logging.warning(f"Ignoring calls_per_minute={requested}: may only lower the "
                                f"tier limit of {self.calls_per_minute}/min")
        # deque with maxlen auto-evicts oldest entries - O(1) operations
        self.call_timestamps = deque(maxlen=self.calls_per_minute)

    def _check_rate_limit(self) -> bool:
        """Check if we're within API rate limits (premium or standard tier).

        Uses deque with maxlen for O(1) rate limiting instead of O(n) list scan.
        """
        now = datetime.datetime.now()
        one_minute_ago = now - datetime.timedelta(minutes=1)

        # Remove old timestamps from front (they're in chronological order)
        while self.call_timestamps and self.call_timestamps[0] < one_minute_ago:
            self.call_timestamps.popleft()

        if len(self.call_timestamps) >= self.calls_per_minute:
            # Debug, not warning: since _wait_for_rate_slot() exists this is
            # ordinary back-pressure that the caller absorbs by waiting, not an
            # incident. It used to warn "caching is critical" on every hit,
            # which was both alarming and (post-pacing) untrue — the nightly
            # 99-symbol run trips it routinely and simply paces through.
            self.logger.debug("Rate window full (%d/min) — caller will pace",
                              self.calls_per_minute)
            return False

        self.call_timestamps.append(now)
        return True

    def _wait_for_rate_slot(self, max_wait: float = 90.0) -> bool:
        """Block until _check_rate_limit grants a slot (or max_wait elapses).

        The window is 60s deep, so under normal operation the wait is bounded
        by ~60s; 90s covers clock jitter. Waiting turns a >75-symbol batch
        into a correctly PACED run instead of a burst whose tail is refused —
        the refusal path is what silently starved VTI/TECS (and the advisor
        basket's stragglers) of daily prices for a month (2026-08-13..09-09).
        """
        deadline = time.monotonic() + max_wait
        while not self._check_rate_limit():
            if time.monotonic() >= deadline:
                return False
            # Sleep until the oldest in-window call ages out (plus margin).
            if self.call_timestamps:
                age = (datetime.datetime.now() - self.call_timestamps[0]).total_seconds()
                pause = max(60.0 - age, 0.0) + 0.1
            else:
                pause = 0.5
            time.sleep(min(pause, max(deadline - time.monotonic(), 0.1)))
        return True

    def _http_get(self, params, stream_retries: int = 2):
        """GET via the retry-mounted session, also retrying streamed-body failures.

        ChunkedEncodingError/ProtocolError happen after headers arrive (the body
        dies mid-stream on very large payloads), so urllib3's Retry never sees
        them — hence the explicit loop.
        """
        last_exc = None
        for attempt in range(stream_retries + 1):
            try:
                return self.session.get(self.base_url, params=params, timeout=self.request_timeout)
            except (ChunkedEncodingError, ProtocolError, RequestsConnectionError) as e:
                last_exc = e
                self.logger.warning(
                    f"Streamed-body failure on attempt {attempt + 1}/{stream_retries + 1}: {e}"
                )
        raise last_exc

    # REALTIME_OPTIONS symbol spellings that differ from our stored symbols.
    # Discovered 2026-08-13: realtime REJECTS "BRKB" ("Invalid symbol") but
    # accepts "BRK.B" — while HISTORICAL_OPTIONS accepts "BRKB". The returned
    # contractIDs are BRKB-rooted either way, so only the REQUEST needs
    # translating; storage keeps our dotless spelling. BRKB failed every
    # snapshot from the Jul-25 realtime switch until this alias landed.
    REALTIME_SYMBOL_ALIASES = {"BRKB": "BRK.B"}

    def fetch_realtime_options(self, symbol, require_greeks=True):
        """Fetch the LIVE options chain (today's date, current quotes).

        This is the intraday path for index options (Issue #66). It differs from
        ``fetch_historical_options(date=None)`` in a way that matters a great
        deal: verified live 2026-07-24 at 10:31 ET, HISTORICAL_OPTIONS with no
        date returns the PREVIOUS session (date=2026-07-23) while
        REALTIME_OPTIONS returns today with live quotes and current OI (see
        Issue #64 for the damage the historical variant quietly did).

        Vendor quirks this method inherits and callers must know:
        - Roots are merged: requesting SPX returns SPX + SPXW contracts (29,420
          rows), VIX returns VIX + VIXW, DJX returns DJX + DJXW. The vendor
          ``symbol`` column says the REQUEST symbol on every row — split by root
          via utils/occ_symbol.split_by_root, never by ``symbol``.
        - Requesting SPXW directly is rejected as "Invalid symbol".
        - Greeks/IV are the string "-" for every index root (equities get real
          values). ``_apply_standard_processing`` coerces those to NaN; the
          index pipeline then computes its own (gex/implied_vol.py).
        - XSP is not served at all (0 rows) — that root comes from Alpaca.

        Never cached: realtime data is only true for the moment it was fetched.

        Args:
            symbol: Underlying/request symbol (SPY, SPX, VIX, DJX, ...)
            require_greeks: Ask the vendor for greeks fields (real for equities,
                "-" for index roots; keeping the columns present either way
                keeps the frame shape uniform downstream)

        Returns:
            DataFrame in the same processed shape as fetch_historical_options.
        """
        if not self._wait_for_rate_slot():
            # A skipped realtime fetch is a permanent intraday hole (the slot
            # never comes back) — pace instead of refuse; see _wait_for_rate_slot.
            self.logger.warning("Rate-slot wait timed out, skipping realtime fetch")
            return pd.DataFrame()

        try:
            params = {
                "function": "REALTIME_OPTIONS",
                "symbol": self.REALTIME_SYMBOL_ALIASES.get(symbol, symbol),
                "apikey": self.api_key,
            }
            if require_greeks:
                params["require_greeks"] = "true"

            self.logger.info(f"Fetching REALTIME options chain for {symbol}")
            response = self._http_get(params)

            if response.status_code != 200:
                self.logger.error(f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()
            if "Error Message" in data:
                self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()
            if "Note" in data and "rate limit" in data.get("Note", "").lower():
                self.logger.warning(f"Rate limit warning: {data['Note']}")
                return pd.DataFrame()

            df = self._process_options_data(data)
            if df.empty:
                self.logger.warning(f"No realtime options data returned for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching realtime options: {e}")
            return pd.DataFrame()

    def fetch_historical_options(self, symbol, date=None, datatype="json", cache_result=True):
        """Fetch full historical options chain for a specific trading date.

        Args:
            symbol: Underlying symbol (SPY, SPX, IBM, etc.)
            date: Trading date (YYYY-MM-DD). If None, uses previous trading day
            datatype: Response format ('json' or 'csv')
            cache_result: Whether to cache result (False when caller handles storage)

        Returns:
            DataFrame with complete options chain for the trading date

        Note:
            - Returns ALL expirations available for the trading date
            - Covers 15+ years of history (since 2008-01-01)
            - Requires Alpha Vantage Premium for full functionality
        """
        if not self._wait_for_rate_slot():
            self.logger.warning("Rate-slot wait timed out, using cached data only")
            return pd.DataFrame()

        # Create cache key - use 'latest' if no date specified
        cache_date = date or "latest"
        cache_key = f"options_{symbol}_{cache_date}"

        # Check SQLite first (Issue #180: primary storage, critical for rate limits)
        if date and self.sqlite_options is not None:  # Only cache specific dates, not 'latest'
            cached_data = self.sqlite_options.get_options_chain(symbol, date)
            if cached_data is not None and not cached_data.empty:
                self.logger.info(f"Using SQLite options data for {symbol} {date}")
                return cached_data

        try:
            # Build API parameters according to Alpha Vantage docs
            params = {"function": "HISTORICAL_OPTIONS", "symbol": symbol, "apikey": self.api_key}

            # Add optional date parameter
            if date:
                params["date"] = date

            # Add datatype parameter
            if datatype != "json":
                params["datatype"] = datatype

            self.logger.info(
                f"Fetching options data for {symbol}" + (f" on {date}" if date else " (previous trading day)")
            )

            response = self._http_get(params)

            if response.status_code != 200:
                self.logger.error(f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            # Handle different response formats
            if datatype == "csv":
                # Parse CSV response
                df = self._process_csv_response(response.text, symbol, date)
            else:
                # Parse JSON response
                data = response.json()

                if "Error Message" in data:
                    self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                    return pd.DataFrame()

                if "Note" in data and "rate limit" in data["Note"].lower():
                    self.logger.warning(f"Rate limit warning: {data['Note']}")
                    return pd.DataFrame()

                df = self._process_options_data(data)

            if df.empty:
                self.logger.warning(f"No options data returned for {symbol}" + (f" on {date}" if date else ""))
                return df

            # Store in SQLite (Issue #180: primary storage, only for specific dates)
            if date and cache_result and self.sqlite_options is not None:
                self.sqlite_options.store_options_chain(symbol, date, df)

            self.logger.info(f"Successfully fetched {len(df)} option contracts")
            return df

        except Exception as e:
            self.logger.error(f"Error fetching historical options: {e}")
            return pd.DataFrame()

    def fetch_underlying_data(self, symbol, start_date, end_date):
        """Fetch underlying stock data for GEX calculations.

        Args:
            symbol: Stock symbol (SPY, SPX)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        if not self._wait_for_rate_slot():
            # Only after a genuine timeout (limiter stuck >90s) fall back to
            # cache. Before 2026-09-09 this fallback fired on EVERY limit hit:
            # the nightly 96-symbol price run bursts ~75 calls in <30s, so the
            # tail of the symbol list was served yesterday's cache night after
            # night — VTI and TECS sit at positions ~77-78 and stalled for a
            # month while the log cheerfully said "1 records inserted".
            cached_only = self.cache.get_market_data(symbol, start_date, end_date) if self.cache is not None else None
            if cached_only is not None:
                self.logger.warning(f"Rate-slot wait timed out for {symbol}; serving cached data")
                return cached_only
            else:
                self.logger.error("Rate limit exceeded and no cached data available")
                return pd.DataFrame()

        try:
            # Process date range
            processed_start, processed_end = get_processed_date_range(start_date, end_date)

            # Check cache first - validate it covers the requested date range
            cached_data = (
                self.cache.get_market_data(symbol, processed_start, processed_end) if self.cache is not None else None
            )
            if cached_data is not None and not cached_data.empty:
                # Verify cache actually covers the requested date range on both ends
                cache_min_date = cached_data.index.min()
                cache_max_date = cached_data.index.max()

                # Convert to comparable format
                start_dt = pd.to_datetime(processed_start)
                end_dt = pd.to_datetime(processed_end)

                # Handle timezone-aware index
                if hasattr(cache_min_date, 'tz') and cache_min_date.tz is not None:
                    start_dt = start_dt.tz_localize(cache_min_date.tz)
                    end_dt = end_dt.tz_localize(cache_min_date.tz)

                # Cache is valid if it starts at or before requested start (30-day
                # tolerance) AND is not missing any TRADING sessions at the end.
                #
                # The end tolerance must count TRADING days, not calendar days
                # (incident 2026-07-22..24): a calendar tolerance of 3 days —
                # meant to span weekends — also accepted a cache ending Monday
                # when Tue/Wed/Thu data was requested, silently serving stale
                # frames for 65/78 symbols three sessions running. equity_prices
                # under-collected (13/day vs 77) until the daily status report's
                # PARTIAL flag surfaced it. busday_count is zero across a
                # weekend (Fri cache, Mon request => fetch, correctly) and
                # positive the moment a real session is missing. Holidays cost
                # one unnecessary API call — the safe direction.
                import numpy as np

                start_gap = (cache_min_date - start_dt).days
                missing_sessions = int(np.busday_count(
                    (cache_max_date + pd.Timedelta(days=1)).date(),
                    (end_dt + pd.Timedelta(days=1)).date(),
                ))

                if start_gap <= 30 and missing_sessions <= 0:
                    self.logger.info(f"Using cached stock data for {symbol}")
                    return cached_data
                elif missing_sessions > 0:
                    self.logger.info(
                        f"Cache for {symbol} ends {cache_max_date.date()}, "
                        f"{missing_sessions} trading session(s) missing through {end_dt.date()}, fetching from API"
                    )
                else:
                    self.logger.info(f"Cache for {symbol} starts at {cache_min_date.date()}, need data from {start_dt.date()}, fetching from API")

            self.logger.info(f"Fetching stock data for {symbol} from {processed_start} to {processed_end}")

            # Determine outputsize based on whether we need historical data
            end_date_obj = datetime.datetime.strptime(processed_end, "%Y-%m-%d")
            now = datetime.datetime.now()
            days_from_now = (now - end_date_obj).days

            # Use full output if requesting historical data (>30 days old) or large range
            days_range = (
                datetime.datetime.strptime(processed_end, "%Y-%m-%d")
                - datetime.datetime.strptime(processed_start, "%Y-%m-%d")
            ).days
            use_full = days_from_now > 30 or days_range > 100

            # Same spelling trap as REALTIME_OPTIONS, but WORSE (found
            # 2026-08-13): AV's "BRKB" TIME_SERIES is a dead ticker frozen at
            # 2017-09-27 — it answers OK with nine-year-old data, so the fetch
            # never errors and the stall is silent. "BRK.B" is the live series.
            # Berkshire daily prices froze 2026-03-20 until this alias landed.
            # Cache/storage keys stay on OUR spelling; only the request maps.
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": self.REALTIME_SYMBOL_ALIASES.get(symbol, symbol),
                "apikey": self.api_key,
                "outputsize": "full" if use_full else "compact",
                "datatype": "json",
            }

            response = requests.get(self.base_url, params=params, timeout=self.request_timeout)

            if response.status_code != 200:
                self.logger.error(f"Alpha Vantage API error: {response.status_code}")
                return pd.DataFrame()

            data = response.json()

            if "Error Message" in data:
                self.logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return pd.DataFrame()

            if "Time Series (Daily)" not in data:
                self.logger.warning(f"No time series data found for {symbol}")
                return pd.DataFrame()

            time_series = data["Time Series (Daily)"]
            df = pd.DataFrame.from_dict(time_series, orient="index")

            # Standardize column names for GEX calculations
            df = df.rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                    "5. volume": "volume",
                }
            )

            # Convert to proper types
            df.index = pd.to_datetime(df.index)
            for col in df.columns:
                df[col] = pd.to_numeric(df[col])

            # Filter by date range
            df = df[(df.index >= processed_start) & (df.index <= processed_end)]
            df = df.sort_index(ascending=False)

            # Localize timezone - Alpha Vantage dates are already in ET, not UTC
            # Do NOT use localize_df as it treats dates as UTC first, which shifts dates by one day
            if df.index.tz is None:
                df.index = df.index.tz_localize(get_default_timezone())

            # Cache for future use (critical for rate limits)
            if self.cache is not None:
                self.cache.store_market_data(symbol, df, processed_start, processed_end)

            return df

        except Exception as e:
            self.logger.error(f"Error fetching underlying data: {e}")
            return pd.DataFrame()

    def _process_csv_response(self, csv_text, symbol, date):
        """Process CSV response from Alpha Vantage Historical Options API.

        Args:
            csv_text: Raw CSV response text
            symbol: Symbol for logging
            date: Date for logging

        Returns:
            DataFrame with processed options data
        """
        try:
            import io

            # Parse CSV into DataFrame
            df = pd.read_csv(io.StringIO(csv_text))

            if df.empty:
                self.logger.warning(f"Empty CSV response for {symbol}")
                return df

            # CSV format should match JSON structure, so process similarly
            # Convert column names to match expected format if needed
            df = self._standardize_csv_columns(df)

            # Apply same processing as JSON data
            processed_df = self._apply_standard_processing(df)

            return processed_df

        except Exception as e:
            self.logger.error(f"Error processing CSV response: {e}")
            return pd.DataFrame()

    def _standardize_csv_columns(self, df):
        """Standardize CSV column names to match JSON format."""
        # CSV might have different column naming - adjust as needed
        # This will be refined once we see actual CSV format
        return df

    def _process_options_data(self, raw_data):
        """Process raw options data into standardized format for GEX calculations.

        Args:
            raw_data: Raw API response data from Historical Options endpoint

        Returns:
            DataFrame with options chain data organized by strike
        """
        if "data" not in raw_data:
            self.logger.warning("No 'data' field in options API response")
            return pd.DataFrame()

        options_data = raw_data["data"]
        if not options_data:
            self.logger.warning("Empty options data in API response")
            return pd.DataFrame()

        try:
            # Convert to DataFrame
            df = pd.DataFrame(options_data)
            return self._apply_standard_processing(df)

        except Exception as e:
            self.logger.error(f"Error processing options data: {e}")
            return pd.DataFrame()

    def _apply_standard_processing(self, df):
        """Apply standard processing to options DataFrame (shared by JSON and CSV).

        Args:
            df: Raw options DataFrame

        Returns:
            Processed DataFrame with derived fields
        """
        try:
            if df.empty:
                return df

            # Convert numeric columns
            numeric_columns = [
                "strike",
                "last",
                "mark",
                "bid",
                "ask",
                "bid_size",
                "ask_size",
                "volume",
                "open_interest",
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

            # Convert dates
            if "expiration" in df.columns:
                df["expiration"] = pd.to_datetime(df["expiration"])
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])

            # Add derived columns for GEX analysis
            df["mid_price"] = (df["bid"] + df["ask"]) / 2
            df["bid_ask_spread"] = df["ask"] - df["bid"]
            df["bid_ask_spread_pct"] = df["bid_ask_spread"] / df["mid_price"] * 100

            # Volume-to-OI ratios (useful for detecting unusual activity)
            df["vol_oi_ratio"] = df["volume"] / (df["open_interest"] + 1)  # +1 to avoid div by zero

            # Sort by expiration, then by strike
            df = df.sort_values(["expiration", "strike"])

            self.logger.info(f"Processed {len(df)} option contracts")
            return df

        except Exception as e:
            self.logger.error(f"Error in standard processing: {e}")
            return pd.DataFrame()

    def get_rate_limit_status(self):
        """Get current rate limit status."""
        now = datetime.datetime.now()
        one_minute_ago = now - datetime.timedelta(minutes=1)

        # Count recent calls (deque is already bounded, just filter by time)
        recent_calls = sum(1 for ts in self.call_timestamps if ts >= one_minute_ago)

        return {
            "calls_last_minute": recent_calls,
            "calls_remaining": max(0, self.calls_per_minute - recent_calls),
            "reset_time": now + datetime.timedelta(minutes=1) if recent_calls > 0 else now,
        }

    def fetch_underlying_price(self, symbol: str, date: str) -> float:
        """Fetch the closing price for a specific date.

        Uses cached data when available to avoid extra API calls.

        Args:
            symbol: Stock symbol (SPY, QQQ, TQQQ, etc.)
            date: Date in YYYY-MM-DD format

        Returns:
            Closing price as float, or None if not available
        """
        try:
            # Try to get from cache first (no API call)
            cached_data = self.cache.get_market_data(symbol, date, date) if self.cache is not None else None
            if cached_data is not None and not cached_data.empty:
                # Find the exact date in the cached data
                date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
                for idx in cached_data.index:
                    try:
                        idx_str = pd.to_datetime(idx).strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        idx_str = str(idx)[:10]
                    if idx_str == date_str:
                        return float(cached_data.loc[idx, "close"])

            # Fetch from API - use a small range to get the specific date
            # This makes one API call but gets cached for future use
            df = self.fetch_underlying_data(symbol, date, date)

            if df is not None and not df.empty:
                # Return the close price
                if "close" in df.columns:
                    return float(df["close"].iloc[0])

            return None

        except Exception as e:
            self.logger.warning(f"Could not fetch underlying price for {symbol} on {date}: {e}")
            return None
