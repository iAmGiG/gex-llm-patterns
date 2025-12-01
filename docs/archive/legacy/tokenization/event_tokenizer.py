"""
Event Tokenizer
Detects and tokenizes market events and special conditions.
"""

import datetime
import logging

import numpy as np
import pandas as pd

# Use date_utils instead of datetime
from src.utils.date_utils import (
    add_business_days,
    calculate_duration_minutes,
    date_range_trading_days,
    next_business_day,
    now_timestamp,
    parse_date_string,
    today_str,
)

from .vocabulary import ContextToken, EventToken, TokenVocabulary

logger = logging.getLogger(__name__)


class EventTokenizer:
    """
    Detect and tokenize market events and context.
    """

    def __init__(self):
        """Initialize event tokenizer."""
        self.vocabulary = TokenVocabulary()

        # Standard options expiration dates (3rd Friday of month)
        self.opex_dates = self._generate_opex_dates()

        # Placeholder for FOMC dates (would be loaded from data)
        self.fomc_dates = self._load_fomc_dates()

    def detect_gex_events(self, gex_series, threshold=0):
        """
        Detect GEX-related events.

        Args:
            gex_series: Series of GEX values
            threshold: Threshold for flip detection (default 0)

        Returns of detected events with timestamps
        """
        events = []

        # Detect zero crossings
        sign_changes = np.sign(gex_series).diff()
        flip_dates = gex_series[sign_changes != 0].index

        for date in flip_dates:
            if not pd.isna(sign_changes[date]):
                events.append(
                    {
                        "date": date,
                        "event": EventToken.CROSS_FLIP.value,
                        "details": {"from": gex_series.shift(1)[date], "to": gex_series[date]},
                    }
                )

        # Detect gamma squeezes (high concentration)
        rolling_std = gex_series.rolling(window=20).std()
        squeeze_threshold = rolling_std.mean() + 2 * rolling_std.std()

        squeeze_dates = gex_series[abs(gex_series) > squeeze_threshold].index
        for date in squeeze_dates:
            events.append(
                {
                    "date": date,
                    "event": EventToken.GAMMA_SQUEEZE.value,
                    "details": {"gex_value": gex_series[date], "threshold": squeeze_threshold},
                }
            )

        return events

    def detect_price_events(self, prices, call_walls=None, put_supports=None):
        """
        Detect price-related events.

        Args:
            prices: Price series
            call_walls: Series of call wall strike prices
            put_supports: Series of put support strike prices

        Returns of detected price events
        """
        events = []

        # Detect breaks above call walls
        if call_walls is not None:
            for date in prices.index:
                if date in call_walls.index:
                    if prices[date] > call_walls[date]:
                        if date > prices.index[0]:  # Not first date
                            prev_date = prices.index[prices.index.get_loc(date) - 1]
                            if prices[prev_date] <= call_walls[date]:
                                events.append(
                                    {
                                        "date": date,
                                        "event": EventToken.BREAK_CALL_WALL.value,
                                        "details": {"price": prices[date], "wall": call_walls[date]},
                                    }
                                )

        # Detect breaks below put supports
        if put_supports is not None:
            for date in prices.index:
                if date in put_supports.index:
                    if prices[date] < put_supports[date]:
                        if date > prices.index[0]:
                            prev_date = prices.index[prices.index.get_loc(date) - 1]
                            if prices[prev_date] >= put_supports[date]:
                                events.append(
                                    {
                                        "date": date,
                                        "event": EventToken.BREAK_PUT_SUPPORT.value,
                                        "details": {"price": prices[date], "support": put_supports[date]},
                                    }
                                )

        # Detect pinning (price stuck at strike)
        if len(prices) > 5:
            rolling_std = prices.rolling(window=5).std()
            low_vol_threshold = rolling_std.quantile(0.1)

            for date in rolling_std.index:
                if rolling_std[date] < low_vol_threshold:
                    # Check if near a round number (potential strike)
                    price = prices[date]
                    nearest_strike = round(price / 5) * 5  # Assume $5 strikes
                    if abs(price - nearest_strike) / price < 0.005:  # Within 0.5%
                        events.append(
                            {
                                "date": date,
                                "event": EventToken.PIN_RISK.value,
                                "details": {"price": price, "strike": nearest_strike},
                            }
                        )

        return events

    def detect_volatility_events(self, vix=None, returns=None):
        """
        Detect volatility-related events.

        Args:
            vix: VIX series
            returns: Returns series for realized vol

        Returns of volatility events
        """
        events = []

        # Detect VIX spikes
        if vix is not None:
            vix_returns = vix.pct_change()
            spike_threshold = 0.2  # 20% daily move

            spike_dates = vix[vix_returns > spike_threshold].index
            for date in spike_dates:
                events.append(
                    {
                        "date": date,
                        "event": EventToken.VOL_SPIKE.value,
                        "details": {"vix": vix[date], "change": vix_returns[date]},
                    }
                )

        # Detect realized vol regime changes
        if returns is not None:
            realized_vol = returns.rolling(window=20).std() * np.sqrt(252)
            vol_ma = realized_vol.rolling(window=60).mean()

            regime_changes = (realized_vol > vol_ma * 1.5) | (realized_vol < vol_ma * 0.5)

            for date in realized_vol[regime_changes].index:
                if not pd.isna(realized_vol[date]):
                    events.append(
                        {
                            "date": date,
                            "event": "VOL_REGIME_CHANGE",
                            "details": {"realized_vol": realized_vol[date], "expected": vol_ma[date]},
                        }
                    )

        return events

    def generate_context_tokens(self, date: datetime.datetime):
        """
        Generate context tokens for a specific date.

        Args:
            date: Date to generate context for

        Returns of context tokens
        """
        tokens = []

        # Days to options expiration
        days_to_opex = self._days_to_next_opex(date)
        if days_to_opex <= 5:
            tokens.append(EventToken.OPEX_WEEK.value)
        tokens.append(f"DAYS_{min(days_to_opex, 30)}")

        # Days since FOMC
        days_since_fomc = self._days_since_last_fomc(date)
        if days_since_fomc <= 7:
            tokens.append(EventToken.FOMC_WEEK.value)

        # Month-end effects
        if date.day >= 25:
            tokens.append(ContextToken.MONTH_END.value)

        # Quarter-end effects
        if date.month in [3, 6, 9, 12] and date.day >= 25:
            tokens.append(ContextToken.QUARTER_END.value)

        # Window dressing (last week of quarter)
        if date.month in [3, 6, 9, 12] and date.day >= 23:
            tokens.append(ContextToken.WINDOW_DRESSING.value)

        # Tax loss harvesting (December)
        if date.month == 12:
            tokens.append(ContextToken.TAX_LOSS_HARVEST.value)

        return tokens

    def tokenize_events_timeline(self, events, start_date: datetime.datetime, end_date: datetime.datetime):
        """
        Create timeline of event tokens.

        Args:
            events of detected events
            start_date: Start of timeline
            end_date: End of timeline

        Returns:
            DataFrame with date index and event tokens
        """
        # Create date range
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # Initialize timeline
        timeline = pd.DataFrame(index=dates, columns=["events", "context"])
        timeline["events"] = ""
        timeline["context"] = ""

        # Add events
        for event in events:
            event_date = event["date"]
            if event_date in timeline.index:
                if timeline.loc[event_date, "events"]:
                    timeline.loc[event_date, "events"] += f",{event['event']}"
                else:
                    timeline.loc[event_date, "events"] = event["event"]

        # Add context for each date
        for date in timeline.index:
            context_tokens = self.generate_context_tokens(date)
            timeline.loc[date, "context"] = ",".join(context_tokens)

        return timeline

    def _generate_opex_dates(self, years=5):
        """Generate standard monthly options expiration dates."""
        opex_dates = set()

        current_year = datetime.datetime.now().year
        for year in range(current_year - years, current_year + 2):
            for month in range(1, 13):
                # Find third Friday of month
                first_day = datetime.datetime(year, month, 1)
                first_friday = first_day + datetime.timedelta(days=(4 - first_day.weekday()) % 7)
                third_friday = first_friday + datetime.timedelta(weeks=2)
                opex_dates.add(third_friday)

        return opex_dates

    def _load_fomc_dates(self):
        """Load FOMC meeting dates (placeholder - would load from data)."""
        # Approximate FOMC dates (8 per year, roughly every 6 weeks)
        fomc_dates = set()

        current_date = datetime.datetime(2020, 1, 29)  # Starting point
        end_date = datetime.datetime.now() + datetime.timedelta(days=365)

        while current_date < end_date:
            fomc_dates.add(current_date)
            current_date += datetime.timedelta(weeks=6)

        return fomc_dates

    def _days_to_next_opex(self, date: datetime.datetime) -> int:
        """Calculate days to next options expiration."""
        future_opex = [d for d in self.opex_dates if d >= date]

        if future_opex:
            next_opex = min(future_opex)
            return (next_opex - date).days

        return 30  # Default if no future date found

    def _days_since_last_fomc(self, date: datetime.datetime) -> int:
        """Calculate days since last FOMC meeting."""
        past_fomc = [d for d in self.fomc_dates if d <= date]

        if past_fomc:
            last_fomc = max(past_fomc)
            return (date - last_fomc).days

        return 30  # Default if no past date found

    def validate_event_detection(self, events, known_events=None):
        """
        Validate event detection accuracy.

        Args:
            events: Detected events
            known_events: Known/labeled events for comparison

        Returns:
            Validation metrics
        """
        validation = {"total_events": len(events), "event_types": {}}

        # Count event types
        for event in events:
            event_type = event["event"]
            if event_type not in validation["event_types"]:
                validation["event_types"][event_type] = 0
            validation["event_types"][event_type] += 1

        # Compare with known events if provided
        if known_events:
            detected_dates = {e["date"] for e in events}
            known_dates = {e["date"] for e in known_events}

            validation["precision"] = len(detected_dates & known_dates) / len(detected_dates) if detected_dates else 0
            validation["recall"] = len(detected_dates & known_dates) / len(known_dates) if known_dates else 0

            if validation["precision"] + validation["recall"] > 0:
                validation["f1_score"] = (
                    2
                    * validation["precision"]
                    * validation["recall"]
                    / (validation["precision"] + validation["recall"])
                )
            else:
                validation["f1_score"] = 0

        return validation
