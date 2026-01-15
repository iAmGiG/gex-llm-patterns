"""
Outcome Calculator - Validates pattern predictions with forward-looking metrics
Issue #80: Enhanced output structure for backtesting validation
Issue #180: Migrated to SQLiteOptionsManager for options data

Measures the market's subsequent behavior to validate pattern predictions.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from gex_db_infrastructure.cache.sqlite_options_manager import SQLiteOptionsManager
from gex_db_infrastructure.cache.postgresql_options_manager import PostgreSQLOptionsManager

logger = logging.getLogger(__name__)


class OutcomeCalculator:
    """Calculates outcome metrics to validate pattern predictions.

    Measures:
    1. Forward returns (T+1, T+3)
    2. Forward drawdown/gains (max loss/gain over next 3 days)
    3. Realized volatility (actual volatility over forward period)
    4. Prediction materialization (did expected outcome occur?)
    """

    def __init__(self, cache_manager=None, sqlite_options_manager=None):
        """
        Args:
            cache_manager: Legacy UnifiedCacheManager (deprecated for options)
            sqlite_options_manager: SQLiteOptionsManager for options data (preferred)
        """
        self.cache = cache_manager
        # Use provided SQLiteOptionsManager or create one
        self.sqlite_options = sqlite_options_manager or SQLiteOptionsManager()

    def calculate_forward_returns(self, symbol: str, date_str: str, horizons: List[int] = [1, 3]) -> Dict[str, float]:
        """Calculate forward returns for given horizons.

        Args:
            symbol: Ticker symbol (e.g., 'SPY')
            date_str: Date of prediction (e.g., '2024-01-02')
            horizons: List of forward days to calculate (default: [1, 3])

        Returns:
            Dict with keys like 'forward_1d_return_pct', 'forward_3d_return_pct'
        """
        if self.cache is None:
            logger.warning("No cache manager provided, cannot calculate forward returns")
            return {}

        try:
            # Get price at T (prediction date)
            price_t = self._get_close_price(symbol, date_str)
            if price_t is None:
                logger.warning(f"No price data for {symbol} on {date_str}")
                return {}

            forward_returns = {}

            for horizon in horizons:
                # Get price at T+horizon
                future_date = self._add_trading_days(date_str, horizon)
                if future_date is None:
                    logger.warning(f"Cannot calculate T+{horizon} for {date_str}")
                    continue

                price_future = self._get_close_price(symbol, future_date)
                if price_future is None:
                    logger.warning(f"No price data for {symbol} on {future_date}")
                    continue

                # Calculate return
                ret_pct = (price_future / price_t - 1) * 100
                forward_returns[f"forward_{horizon}d_return_pct"] = round(ret_pct, 4)

            return forward_returns

        except Exception as e:
            logger.error(f"Error calculating forward returns: {e}")
            return {}

    def calculate_forward_drawdown_and_gains(self, symbol: str, date_str: str, window: int = 3) -> Dict[str, float]:
        """Calculate maximum drawdown and maximum gain over forward window.

        Args:
            symbol: Ticker symbol
            date_str: Starting date
            window: Number of days to look forward (default: 3)

        Returns:
            Dict with:
                - forward_Xd_max_drawdown_pct: Worst loss from T to T+X
                - forward_Xd_max_gain_pct: Best gain from T to T+X
        """
        if self.cache is None:
            return {}

        try:
            # Get starting price at T
            price_t = self._get_close_price(symbol, date_str)
            if price_t is None:
                return {}

            # Get all prices from T+1 to T+window
            prices = []
            for i in range(1, window + 1):
                future_date = self._add_trading_days(date_str, i)
                if future_date is None:
                    continue
                price = self._get_close_price(symbol, future_date)
                if price is not None:
                    prices.append(price)

            if not prices:
                logger.warning(f"No forward prices found for drawdown calculation")
                return {}

            # Calculate returns from T to each future point
            returns = [(p / price_t - 1) * 100 for p in prices]

            # Max drawdown = worst negative return
            max_drawdown = min(returns)

            # Max gain = best positive return
            max_gain = max(returns)

            return {
                f"forward_{window}d_max_drawdown_pct": round(max_drawdown, 4),
                f"forward_{window}d_max_gain_pct": round(max_gain, 4),
            }

        except Exception as e:
            logger.error(f"Error calculating forward drawdown/gains: {e}")
            return {}

    def calculate_realized_volatility(self, symbol: str, date_str: str, window: int = 3) -> Optional[float]:
        """Calculate realized volatility over forward window.

        This measures the actual volatility that occurred after the prediction,
        which is critical for validating predictions about volatility expansion
        or dampening.

        Args:
            symbol: Ticker symbol
            date_str: Starting date
            window: Number of days to calculate vol over (default: 3)

        Returns:
            Annualized realized volatility as decimal (e.g., 0.012 = 1.2% daily vol)
        """
        if self.cache is None:
            return None

        try:
            # Get prices for T to T+window (need T for log return calculation)
            prices = []

            # Get T price
            price_t = self._get_close_price(symbol, date_str)
            if price_t is not None:
                prices.append(price_t)

            # Get T+1 to T+window
            for i in range(1, window + 1):
                future_date = self._add_trading_days(date_str, i)
                if future_date is None:
                    continue
                price = self._get_close_price(symbol, future_date)
                if price is not None:
                    prices.append(price)

            if len(prices) < 2:
                logger.warning(f"Insufficient price data for volatility calculation")
                return None

            # Calculate log returns
            prices_arr = np.array(prices)
            log_returns = np.diff(np.log(prices_arr))

            # Calculate standard deviation (daily volatility)
            daily_vol = np.std(log_returns, ddof=1)  # Use sample std dev

            return round(daily_vol, 6)

        except Exception as e:
            logger.error(f"Error calculating realized volatility: {e}")
            return None

    def verify_prediction(self, narrative: Dict, quantitative_evidence: Dict, forward_metrics: Dict) -> Dict:
        """Verify if predicted mechanics actually materialized.

        Uses rule-based logic to determine if the expected outcome occurred:
        - Trend acceleration/reversal
        - Volatility expansion/dampening
        - Forced hedging impact

        Args:
            narrative: WHO/WHOM/WHAT narrative from LLM
            quantitative_evidence: GEX metrics and market data
            forward_metrics: All forward-looking metrics calculated

        Returns:
            Dict with:
                - prediction_materialized: bool
                - verification_method: str
                - verification_note: str
                - forward_1d_direction: 'up'/'down'/'flat'
        """
        # Extract key metrics
        what = narrative.get("what", "").lower()
        confidence = narrative.get("confidence", 0)
        gex_metrics = quantitative_evidence.get("gex_metrics", {})
        net_gex = gex_metrics.get("net_gex_usd", 0)

        # Forward metrics (handle None values)
        forward_1d_return = forward_metrics.get("forward_1d_return_pct") or 0
        forward_3d_max_gain = forward_metrics.get("forward_3d_max_gain_pct") or 0
        forward_3d_max_dd = forward_metrics.get("forward_3d_max_drawdown_pct") or 0
        subsequent_vol = forward_metrics.get("subsequent_volatility") or 0

        # Rule-based verification logic
        materialized = False
        method = "rule_based"
        note = ""

        # Pattern 1: Negative GEX (dealer short gamma) → Predicts volatility amplification
        if net_gex < 0:
            # Dealers are short gamma → amplify moves via forced hedging
            # Check if we saw significant movement OR elevated volatility
            significant_move = (
                abs(forward_1d_return) > 0.3 or max(abs(forward_3d_max_gain), abs(forward_3d_max_dd)) > 0.5
            )
            elevated_vol = subsequent_vol and subsequent_vol > 0.010  # >1% daily vol

            if significant_move or elevated_vol:
                materialized = True
                direction = "up" if forward_1d_return > 0 else ("down" if forward_1d_return < 0 else "volatile")
                note = (
                    f"Negative GEX regime validated: Market moved {direction} with "
                    f"{abs(forward_1d_return):.2f}% next-day return. Dealers amplified move via forced hedging. "
                    f"Max 3d move: {forward_3d_max_gain:.2f}% gain / {forward_3d_max_dd:.2f}% drawdown"
                )
            else:
                vol_str = f"{subsequent_vol:.4f}" if subsequent_vol else "N/A"
                note = (
                    f"Negative GEX regime but muted response: {forward_1d_return:.2f}% next-day return. "
                    f"Expected amplification did not materialize (low vol={vol_str})"
                )

        # Pattern 2: Positive GEX (dealer long gamma) → Predicts dampening
        elif net_gex > 0:
            # Dealers are long gamma → dampen moves
            dampened_move = abs(forward_1d_return) < 0.3 and max(abs(forward_3d_max_gain), abs(forward_3d_max_dd)) < 0.5
            low_vol = subsequent_vol and subsequent_vol < 0.008  # <0.8% daily vol

            if dampened_move and low_vol:
                materialized = True
                vol_str = f"{subsequent_vol:.4f}" if subsequent_vol else "N/A"
                note = (
                    f"Positive GEX regime validated: Price dampened as predicted "
                    f"({forward_1d_return:.2f}% next-day, {vol_str} realized vol). "
                    f"Dealers absorbed volatility via gamma hedging"
                )
            else:
                vol_str = f"{subsequent_vol:.4f}" if subsequent_vol else "N/A"
                note = (
                    f"Positive GEX regime but price broke through: {forward_1d_return:.2f}% next-day return. "
                    f"Expected dampening failed (vol={vol_str})"
                )

        # Pattern 3: Forced hedging keywords → Check for directional move
        if any(keyword in what for keyword in ["force", "forced", "must", "required", "compelled"]):
            if abs(forward_1d_return) > 0.2 or max(abs(forward_3d_max_gain), abs(forward_3d_max_dd)) > 0.4:
                materialized = True
                if not note:  # Don't overwrite GEX regime note
                    note = (
                        f"Forced hedging prediction confirmed: {forward_1d_return:.2f}% next-day move observed. "
                        f"Max 3d excursion: {forward_3d_max_gain:.2f}% / {forward_3d_max_dd:.2f}%"
                    )

        # Pattern 4: High confidence predictions should have larger moves
        if confidence >= 80 and abs(forward_1d_return) > 0.5:
            materialized = True
            if not note:
                note = f"High-confidence ({confidence}%) prediction validated with {forward_1d_return:.2f}% move"

        # Pattern 5: Check for trend reversal keywords
        if any(keyword in what for keyword in ["reversal", "reverse", "unwind", "flip"]):
            # Check if price direction changed from T to T+1 vs T+1 to T+3
            if forward_1d_return * (forward_metrics.get("forward_3d_return_pct", 0) - forward_1d_return) < 0:
                materialized = True
                if not note:
                    note = f"Reversal pattern confirmed: {forward_1d_return:.2f}% initial move, then reversed"

        # Default note if none set
        if not note:
            note = (
                f"Standard outcome: {forward_1d_return:.2f}% T+1 return, "
                f"{forward_3d_max_gain:.2f}%/{forward_3d_max_dd:.2f}% 3d range"
            )

        # Determine direction
        if forward_1d_return > 0.1:
            direction = "up"
        elif forward_1d_return < -0.1:
            direction = "down"
        else:
            direction = "flat"

        return {
            "prediction_materialized": materialized,
            "verification_method": method,
            "verification_note": note,
            "forward_1d_direction": direction,
        }

    def add_outcome_metrics(self, detection: Dict, symbol: str) -> Dict:
        """Add comprehensive outcome_metrics to a detection dict.

        Args:
            detection: Detection dict from PatternTaxonomyValidator
            symbol: Ticker symbol

        Returns:
            Updated detection dict with outcome_metrics added
        """
        date_str = detection["date"]

        # Calculate all forward metrics
        forward_returns = self.calculate_forward_returns(symbol, date_str, horizons=[1, 3])
        forward_extremes = self.calculate_forward_drawdown_and_gains(symbol, date_str, window=3)
        subsequent_vol = self.calculate_realized_volatility(symbol, date_str, window=3)

        # Combine all forward metrics for verification
        all_forward_metrics = {**forward_returns, **forward_extremes, "subsequent_volatility": subsequent_vol}

        # Verify prediction
        narrative = detection.get("narrative", {})
        quant_evidence = detection.get("quantitative_evidence", {})
        verification = self.verify_prediction(
            narrative=narrative, quantitative_evidence=quant_evidence, forward_metrics=all_forward_metrics
        )

        # Build comprehensive outcome_metrics object
        # Only add if we have at least forward returns
        if forward_returns:
            detection["outcome_metrics"] = {
                # Forward returns
                **forward_returns,  # forward_1d_return_pct, forward_3d_return_pct
                # Forward extremes (max gain/loss over next 3 days)
                **forward_extremes,  # forward_3d_max_drawdown_pct, forward_3d_max_gain_pct
                # Realized volatility
                "subsequent_volatility": subsequent_vol,
                # Prediction verification
                **verification,  # prediction_materialized, verification_method, verification_note, forward_1d_direction
            }
        else:
            # No outcome data available
            detection["outcome_metrics"] = {
                "error": "No forward price data available",
                "subsequent_volatility": None,
                "prediction_materialized": None,
            }

        return detection

    def _get_close_price(self, symbol: str, date_str: str) -> Optional[float]:
        """Get closing price for a given date from database/cache.

        Issue #180: Now uses SQLiteOptionsManager as primary source.
        """
        try:
            # Method 1: Query SQLiteOptionsManager for underlying_price (PREFERRED)
            # This is the new primary source after Issue #147 migration
            options_data = self.sqlite_options.get_options_chain(symbol, date_str)
            if options_data is not None and not options_data.empty:
                # Check for explicit underlying price columns
                if "underlying_price" in options_data.columns:
                    price = options_data["underlying_price"].iloc[0]
                    if price and not pd.isna(price):
                        logger.debug(f"Retrieved underlying price {price:.2f} from SQLite for {date_str}")
                        return float(price)

            # Method 2: Query GEX database for spot_price (historical data)
            try:
                import sqlite3

                db_path = Path(".cache/gex_database.db")
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT spot_price FROM daily_gex_metrics WHERE date = ? AND symbol = ?", (date_str, symbol)
                    )
                    result = cursor.fetchone()
                    conn.close()

                    if result and result[0]:
                        spot_price = float(result[0])
                        logger.debug(f"Retrieved spot price {spot_price:.2f} from GEX database for {date_str}")
                        return spot_price
            except Exception as db_error:
                logger.warning(f"GEX database lookup failed: {db_error}")

            # Method 3: Infer from deep ITM call options (FALLBACK)
            # Find calls with delta ≈ 1.0 (deep ITM) - their strike + price ≈ underlying
            if options_data is not None and not options_data.empty:
                if "delta" in options_data.columns and "option_type" in options_data.columns:
                    deep_itm_calls = options_data[
                        (options_data["option_type"] == "call")
                        & (options_data["delta"] > 0.99)
                        & (options_data["delta"] <= 1.0)
                    ]

                    if not deep_itm_calls.empty:
                        # For deep ITM calls: underlying ≈ strike + option price
                        call = deep_itm_calls.iloc[0]
                        underlying = call["strike"] + call.get("last", call.get("mark", call.get("mid_price", 0)))
                        logger.debug(f"Inferred underlying price {underlying:.2f} from deep ITM call")
                        return float(underlying)

            # Method 4: Last resort - use median strike (UNRELIABLE for returns!)
            if options_data is not None and not options_data.empty and "strike" in options_data.columns:
                strikes = options_data["strike"].unique()
                median_strike = float(pd.Series(strikes).median())
                logger.warning(
                    f"Using median strike {median_strike:.2f} as price proxy for {date_str} - returns will be UNRELIABLE!"
                )
                return median_strike

            logger.warning(f"No price data found for {symbol} on {date_str}")
            return None

        except Exception as e:
            logger.error(f"Error getting close price: {e}")
            return None

    def _add_trading_days(self, date_str: str, days: int) -> Optional[str]:
        """Add trading days to a date (skips weekends, approximation for holidays).

        Args:
            date_str: Date in 'YYYY-MM-DD' format
            days: Number of trading days to add

        Returns:
            New date string or None if error
        """
        try:
            current_date = datetime.strptime(date_str, "%Y-%m-%d")

            # Simple approximation: add calendar days and skip weekends
            # TODO: Use actual trading calendar (pandas market calendars) for production
            days_added = 0
            while days_added < days:
                current_date += timedelta(days=1)
                # Skip weekends (Monday=0, Friday=4, Saturday=5, Sunday=6)
                if current_date.weekday() < 5:
                    days_added += 1

            return current_date.strftime("%Y-%m-%d")

        except Exception as e:
            logger.error(f"Error adding trading days: {e}")
            return None


def enrich_validation_results_with_outcomes(validation_result: Dict, symbol: str, cache_manager) -> Dict:
    """Enrich existing validation results with outcome metrics for all detections.

    This is a helper function to update existing YAML files from Issue #79 Phase 1
    with the new outcome metrics for Phase 2 economic backtesting.

    Args:
        validation_result: Dict loaded from YAML file
        symbol: Ticker symbol
        cache_manager: UnifiedCacheManager instance

    Returns:
        Updated validation_result with outcome_metrics added to each detection
    """
    calculator = OutcomeCalculator(cache_manager)

    detections = validation_result.get("detections", [])
    enriched_detections = []

    for detection in detections:
        try:
            enriched = calculator.add_outcome_metrics(detection, symbol)
            enriched_detections.append(enriched)
        except Exception as e:
            logger.error(f"Failed to enrich detection for {detection.get('date')}: {e}")
            enriched_detections.append(detection)  # Keep original if enrichment fails

    # Update validation result
    validation_result["detections"] = enriched_detections

    # Recalculate performance metrics with new outcome data
    detections_with_outcomes = [d for d in enriched_detections if "outcome_metrics" in d]
    if detections_with_outcomes:
        # Calculate predictive accuracy
        predictions_materialized = [d["outcome_metrics"]["prediction_materialized"] for d in detections_with_outcomes]
        predictive_accuracy = sum(predictions_materialized) / len(predictions_materialized) * 100

        # Calculate average forward returns
        forward_1d_returns = [
            d["outcome_metrics"]["forward_1d_return_pct"]
            for d in detections_with_outcomes
            if "forward_1d_return_pct" in d["outcome_metrics"]
        ]
        avg_forward_1d = sum(forward_1d_returns) / len(forward_1d_returns) if forward_1d_returns else None

        # Calculate net alpha (gross return - 5bps transaction costs)
        net_alpha = (avg_forward_1d - 0.05) if avg_forward_1d is not None else None

        # Update performance metrics
        if "performance_metrics" in validation_result:
            validation_result["performance_metrics"].update(
                {
                    "predictive_accuracy_pct": round(predictive_accuracy, 2),
                    "avg_forward_1d_return_pct": round(avg_forward_1d, 4) if avg_forward_1d else None,
                    "net_alpha_pct": round(net_alpha, 4) if net_alpha else None,
                    "passes_economic_threshold": net_alpha > 0.20 if net_alpha is not None else None,
                }
            )

    return validation_result
