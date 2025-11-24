"""FOMC/Fed Data Integration Module.

Fetches and caches Federal Reserve data for market context analysis. Integrates FRED API for economic indicators and
FOMC calendar events.
"""

import datetime
import json
import logging
import pickle
from pathlib import Path
from typing import Dict

import pandas as pd

# Use date_utils for standardized datetime operations
from src.utils.date_utils import today_str

logger = logging.getLogger(__name__)

try:
    from fredapi import Fred

    FREDAPI_AVAILABLE = True
except ImportError:
    FREDAPI_AVAILABLE = False
    logger.warning("fredapi not available. Install with: pip install fredapi")


class FedDataIntegration:
    """Integrates Federal Reserve data for pattern context analysis.

    Provides:
    - FOMC meeting calendar and decisions
    - Fed Funds Rate history
    - Market stress indicators (VIX, spreads)
    - Economic indicators for regime context
    """

    # FOMC meetings typically on Tuesdays/Wednesdays, 8 times per year
    FOMC_INDICATORS = [
        "DFF",  # Effective Federal Funds Rate
        "DFEDTARU",  # Fed Funds Target Rate - Upper
        "DFEDTARL",  # Fed Funds Target Rate - Lower
        "VIXCLS",  # VIX Close
        "BAMLH0A0HYM2",  # High Yield Spread
        "T10Y2Y",  # 10Y-2Y Treasury Spread (yield curve)
        "DEXUSEU",  # USD/EUR Exchange Rate
    ]

    def __init__(self, fred_api_key: str = None, cache_dir: str = ".cache/fed_data"):
        """Initialize Fed Data Integration.

        Args:
            fred_api_key: FRED API key (will load from config if None)
            cache_dir: Directory for caching Fed data
        """
        # Load API key from config if not provided
        if fred_api_key is None:
            fred_api_key = self._load_fred_api_key()

        if not FREDAPI_AVAILABLE:
            raise ImportError("fredapi package required. Install with: pip install fredapi")

        self.fred = Fred(api_key=fred_api_key)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache files
        self.fomc_calendar_cache = self.cache_dir / "fomc_calendar.pkl"
        self.indicators_cache = self.cache_dir / "fed_indicators.pkl"

    def _load_fred_api_key(self) -> str:
        """Load FRED API key from config.json."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.json"
            with open(config_path, "r") as f:
                config = json.load(f)

            fred_key = config.get("FREDAPI")
            if not fred_key:
                raise ValueError("FREDAPI key not found in config.json")

            return fred_key
        except Exception as e:
            logger.error(f"Could not load FRED API key: {e}")
            raise

    def fetch_fomc_calendar(self, start_year: int = 2010, end_year: int = 2025) -> pd.DataFrame:
        """Fetch or load cached FOMC meeting calendar.

        Args:
            start_year: Start year for calendar
            end_year: End year for calendar

        Returns:
            DataFrame with FOMC meeting dates and decisions
        """
        # Check cache first
        if self.fomc_calendar_cache.exists():
            logger.info("Loading FOMC calendar from cache")
            with open(self.fomc_calendar_cache, "rb") as f:
                return pickle.load(f)

        logger.info(f"Creating FOMC calendar for {start_year}-{end_year}")

        # FOMC meeting dates and decisions (historical data)

        # 2024 FOMC meetings (actual dates)
        fomc_2024 = [
            ("2024-01-31", "hold", 5.50, 0.0),
            ("2024-03-20", "hold", 5.50, 0.0),
            ("2024-05-01", "hold", 5.50, 0.0),
            ("2024-06-12", "hold", 5.50, 0.0),
            ("2024-07-31", "hold", 5.50, 0.0),
            ("2024-09-18", "cut", 5.00, -0.50),
            ("2024-11-07", "cut", 4.75, -0.25),
            ("2024-12-18", "cut", 4.50, -0.25),
        ]

        # 2023 FOMC meetings (hiking cycle)
        fomc_2023 = [
            ("2023-02-01", "hike", 4.75, 0.25),
            ("2023-03-22", "hike", 5.00, 0.25),
            ("2023-05-03", "hike", 5.25, 0.25),
            ("2023-06-14", "hold", 5.25, 0.0),
            ("2023-07-26", "hike", 5.50, 0.25),
            ("2023-09-20", "hold", 5.50, 0.0),
            ("2023-11-01", "hold", 5.50, 0.0),
            ("2023-12-13", "hold", 5.50, 0.0),
        ]

        # 2022 FOMC meetings (aggressive hiking)
        fomc_2022 = [
            ("2022-03-16", "hike", 0.50, 0.25),
            ("2022-05-04", "hike", 1.00, 0.50),
            ("2022-06-15", "hike", 1.75, 0.75),
            ("2022-07-27", "hike", 2.50, 0.75),
            ("2022-09-21", "hike", 3.25, 0.75),
            ("2022-11-02", "hike", 4.00, 0.75),
            ("2022-12-14", "hike", 4.50, 0.50),
        ]

        # 2021 and earlier (near zero rates during COVID)
        fomc_2021 = [
            ("2021-01-27", "hold", 0.25, 0.0),
            ("2021-03-17", "hold", 0.25, 0.0),
            ("2021-04-28", "hold", 0.25, 0.0),
            ("2021-06-16", "hold", 0.25, 0.0),
            ("2021-07-28", "hold", 0.25, 0.0),
            ("2021-09-22", "hold", 0.25, 0.0),
            ("2021-11-03", "hold", 0.25, 0.0),
            ("2021-12-15", "hold", 0.25, 0.0),
        ]

        # Combine meetings within year range
        all_meetings = []
        for meetings in [fomc_2024, fomc_2023, fomc_2022, fomc_2021]:
            for meeting in meetings:
                year = int(meeting[0][:4])
                if start_year <= year <= end_year:
                    all_meetings.append(meeting)

        # Create DataFrame
        df = pd.DataFrame(all_meetings, columns=["date", "decision", "rate", "rate_change"])
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Add derived features
        df["is_pivot"] = df["decision"] != df["decision"].shift(1)
        df["meeting_number"] = range(1, len(df) + 1)

        # Cache the result
        with open(self.fomc_calendar_cache, "wb") as f:
            pickle.dump(df, f)

        logger.info(f"Created FOMC calendar with {len(df)} meetings")
        return df

    def get_fomc_context(self, date: pd.Timestamp):
        """Get FOMC context for a specific date.

        Args:
            date: Date to analyze

        Returns:
            Dictionary with FOMC context
        """
        fomc_calendar = self.fetch_fomc_calendar()

        # Find nearest FOMC meeting
        date_diff = (fomc_calendar["date"] - date).dt.days

        # Previous meeting
        prev_meetings = fomc_calendar[date_diff <= 0]
        if not prev_meetings.empty:
            last_meeting = prev_meetings.iloc[-1]
            days_since_fomc = (date - last_meeting["date"]).days
        else:
            last_meeting = None
            days_since_fomc = None

        # Next meeting
        next_meetings = fomc_calendar[date_diff > 0]
        if not next_meetings.empty:
            next_meeting = next_meetings.iloc[0]
            days_to_fomc = (next_meeting["date"] - date).days
        else:
            next_meeting = None
            days_to_fomc = None

        # Determine if we're in FOMC week (within 3 days)
        is_fomc_week = False
        fomc_day = False
        if days_to_fomc is not None and days_to_fomc <= 3:
            is_fomc_week = True
        if days_to_fomc == 0:
            fomc_day = True

        # Check for blackout period (10 days before FOMC)
        in_blackout = False
        if days_to_fomc is not None and 0 < days_to_fomc <= 10:
            in_blackout = True

        return {
            "is_fomc_week": is_fomc_week,
            "is_fomc_day": fomc_day,
            "days_to_fomc": days_to_fomc,
            "days_since_fomc": days_since_fomc,
            "in_blackout_period": in_blackout,
            "last_decision": last_meeting["decision"] if last_meeting is not None else None,
            "current_rate": last_meeting["rate"] if last_meeting is not None else None,
            "last_rate_change": last_meeting["rate_change"] if last_meeting is not None else None,
        }

    def fetch_economic_indicators(self, start_date: str = "2010-01-01", end_date: str = None) -> pd.DataFrame:
        """Fetch economic indicators from FRED.

        Args:
            start_date: Start date for data
            end_date: End date for data (None = today)

        Returns:
            DataFrame with economic indicators
        """
        cache_file = self.indicators_cache

        # Check if we have recent cache (less than 1 day old)
        if cache_file.exists():
            mod_time = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.datetime.now() - mod_time < datetime.timedelta(days=1):
                logger.info("Loading indicators from recent cache")
                with open(cache_file, "rb") as f:
                    return pickle.load(f)

        logger.info("Fetching economic indicators from FRED")

        if end_date is None:
            end_date = today_str()

        indicators_data = {}

        for indicator in self.FOMC_INDICATORS:
            try:
                series = self.fred.get_series(indicator, observation_start=start_date, observation_end=end_date)
                indicators_data[indicator] = series
                logger.info(f"Fetched {indicator}: {len(series)} observations")
            except Exception as e:
                logger.warning(f"Could not fetch {indicator}: {e}")

        # Combine into DataFrame
        df = pd.DataFrame(indicators_data)

        # Forward fill missing values (markets closed on weekends)
        df = df.ffill()

        # Cache the result
        with open(cache_file, "wb") as f:
            pickle.dump(df, f)

        logger.info(f"Cached {len(df)} days of indicators")
        return df

    def calculate_market_stress(self, date: pd.Timestamp, indicators: pd.DataFrame = None):
        """Calculate market stress indicators for pattern context.

        Args:
            date: Date to analyze
            indicators: DataFrame of indicators (will fetch if None)

        Returns:
            Dictionary with stress metrics
        """
        if indicators is None:
            indicators = self.fetch_economic_indicators()

        # Get data for the specific date (or most recent)
        if date in indicators.index:
            day_data = indicators.loc[date]
        else:
            # Get most recent data before date
            prev_dates = indicators[indicators.index <= date]
            if prev_dates.empty:
                return {}
            day_data = prev_dates.iloc[-1]

        # Calculate stress metrics
        stress_metrics = {}

        # VIX level and regime
        if "VIXCLS" in day_data:
            vix = day_data["VIXCLS"]
            if not pd.isna(vix):
                stress_metrics["vix"] = float(vix)
                stress_metrics["vix_regime"] = (
                    "low" if vix < 15 else "normal" if vix < 20 else "elevated" if vix < 30 else "high"
                )

        # Yield curve (10Y-2Y spread)
        if "T10Y2Y" in day_data:
            spread = day_data["T10Y2Y"]
            if not pd.isna(spread):
                stress_metrics["yield_curve"] = float(spread)
                stress_metrics["curve_inverted"] = spread < 0

        # Credit spreads (if available)
        if "BAMLH0A0HYM2" in day_data:
            hy_spread = day_data["BAMLH0A0HYM2"]
            if not pd.isna(hy_spread):
                stress_metrics["credit_spread"] = float(hy_spread)
                stress_metrics["credit_stress"] = (
                    "low"
                    if hy_spread < 400
                    else "normal" if hy_spread < 600 else "elevated" if hy_spread < 800 else "high"
                )

        # Calculate composite stress score (0-100)
        stress_score = 0
        weights = 0

        if "vix" in stress_metrics:
            # VIX contribution (normalized to 0-100)
            vix_score = min(100, (stress_metrics["vix"] / 50) * 100)
            stress_score += vix_score * 0.4
            weights += 0.4

        if "curve_inverted" in stress_metrics:
            # Yield curve contribution
            if stress_metrics["curve_inverted"]:
                stress_score += 30 * 0.3
            weights += 0.3

        if "credit_spread" in stress_metrics:
            # Credit spread contribution
            spread_score = min(100, (stress_metrics["credit_spread"] / 1000) * 100)
            stress_score += spread_score * 0.3
            weights += 0.3

        if weights > 0:
            stress_metrics["composite_stress"] = stress_score / weights
            stress_metrics["stress_regime"] = (
                "calm"
                if stress_metrics["composite_stress"] < 25
                else (
                    "normal"
                    if stress_metrics["composite_stress"] < 50
                    else "elevated" if stress_metrics["composite_stress"] < 75 else "extreme"
                )
            )

        return stress_metrics

    def get_full_context(self, date: pd.Timestamp):
        """Get complete Fed/market context for a date.

        Args:
            date: Date to analyze

        Returns:
            Dictionary with all context data
        """
        logger.info(f"Getting full Fed context for {date}")

        # Get FOMC context
        fomc_context = self.get_fomc_context(date)

        # Get market stress indicators
        stress_metrics = self.calculate_market_stress(date)

        # Combine all context
        full_context = {
            "date": date,
            "fomc": fomc_context,
            "stress": stress_metrics,
            "pattern_weight_adjustments": self._calculate_pattern_weights(fomc_context, stress_metrics),
        }

        return full_context

    def _calculate_pattern_weights(self, fomc_context: Dict, stress_metrics: Dict):
        """Calculate how Fed context should weight pattern confidence.

        Args:
            fomc_context: FOMC meeting context
            stress_metrics: Market stress indicators

        Returns:
            Dictionary of pattern weight adjustments
        """
        weights = {
            "gamma_trap": 1.0,
            "gamma_flip": 1.0,
            "pin_risk": 1.0,
            "volatility_squeeze": 1.0,
            "dealer_reload": 1.0,
            "liquidity_cascade": 1.0,
        }

        # FOMC adjustments
        if fomc_context.get("is_fomc_week"):
            weights["volatility_squeeze"] *= 1.5  # Vol squeeze more likely
            weights["pin_risk"] *= 0.8  # Pin less reliable during events

        if fomc_context.get("in_blackout_period"):
            weights["dealer_reload"] *= 1.3  # Dealers position ahead

        # Stress adjustments
        stress_regime = stress_metrics.get("stress_regime", "normal")
        if stress_regime in ["elevated", "extreme"]:
            weights["liquidity_cascade"] *= 1.4  # Cascades more likely
            weights["gamma_trap"] *= 1.3  # Traps more violent

        if stress_metrics.get("curve_inverted"):
            weights["volatility_squeeze"] *= 1.2  # Recession fears

        return weights

    def prepare_backtest_context(self, start_date, end_date) -> pd.DataFrame:
        """Prepare all Fed context for backtesting period.

        Args:
            start_date: Start date for backtest
            end_date: End date for backtest

        Returns:
            DataFrame with daily Fed context
        """
        logger.info(f"Preparing Fed context for backtest: {start_date} to {end_date}")

        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq="B")  # Business days

        # Fetch all indicators once
        indicators = self.fetch_economic_indicators(start_date, end_date)

        # Build context for each date
        context_data = []
        for date in dates:
            fomc_context = self.get_fomc_context(date)
            stress_metrics = self.calculate_market_stress(date, indicators)

            # Flatten for DataFrame
            flat_context = {
                "date": date,
                "is_fomc_week": fomc_context["is_fomc_week"],
                "is_fomc_day": fomc_context["is_fomc_day"],
                "days_to_fomc": fomc_context["days_to_fomc"],
                "days_since_fomc": fomc_context["days_since_fomc"],
                "current_rate": fomc_context["current_rate"],
                "last_decision": fomc_context["last_decision"],
                "vix": stress_metrics.get("vix"),
                "vix_regime": stress_metrics.get("vix_regime"),
                "yield_curve": stress_metrics.get("yield_curve"),
                "curve_inverted": stress_metrics.get("curve_inverted"),
                "stress_regime": stress_metrics.get("stress_regime"),
                "composite_stress": stress_metrics.get("composite_stress"),
            }
            context_data.append(flat_context)

        return pd.DataFrame(context_data)
