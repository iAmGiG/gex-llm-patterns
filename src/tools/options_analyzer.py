"""Options Chain Analysis Tools.

Tools for analyzing options chain data with focus on patterns like Short Put Arbitrage and other institutional flow
behaviors.

Issue #180: Updated to use SQLiteOptionsManager for options data.
"""

import logging
import os
import sys

from src.utils.config_manager import get_config
from src.utils.date_utils import now_iso

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class OptionsChainAnalyzer:
    """Analyze options chains for patterns and anomalies."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load configuration
        config = get_config()
        self.signal_strength_threshold = config.get(
            "options_analysis.options_chain_analyzer.signal_strength_threshold", 0.6
        )
        self.volume_oi_ratio_quantile = config.get(
            "options_analysis.options_chain_analyzer.volume_oi_ratio_quantile", 0.8
        )
        self.otm_put_threshold = config.get("options_analysis.options_chain_analyzer.otm_put_threshold", 0.95)
        self.min_unusual_strikes = config.get("options_analysis.options_chain_analyzer.min_unusual_strikes", 3)
        self.tight_spread_pct = config.get("options_analysis.options_chain_analyzer.tight_spread_pct", 5.0)
        self.min_otm_put_activity = config.get("options_analysis.options_chain_analyzer.min_otm_put_activity", 3)
        self.summer_months = config.get("options_analysis.options_chain_analyzer.summer_months", [6, 7, 8])

    def detect_short_put_arbitrage_signals(self, options_df):
        """Detect potential Short Put Arbitrage patterns in options chain data.

        Args:
            options_df: DataFrame with options chain data from Alpha Vantage

        Returnsionary with pattern detection results
        """
        if options_df.empty:
            return {"pattern_detected": False, "reason": "No options data"}

        try:
            # Separate calls and puts
            calls = options_df[options_df["type"] == "call"].copy()
            puts = options_df[options_df["type"] == "put"].copy()

            if calls.empty or puts.empty:
                return {"pattern_detected": False, "reason": "Missing call or put data"}

            results = {"pattern_detected": False, "signals": {}, "metrics": {}, "timestamp": now_iso()}

            # Signal 1: Unusual Put Volume vs OI
            put_vol_oi_signals = self._detect_unusual_put_volume(puts)
            results["signals"]["put_volume_anomalies"] = put_vol_oi_signals

            # Signal 2: Call Volume Above Ask (urgency creation)
            call_urgency_signals = self._detect_call_urgency(calls)
            results["signals"]["call_urgency"] = call_urgency_signals

            # Signal 3: Multiple OTM Put Strikes Active
            put_spread_signals = self._detect_put_spread_pattern(puts, calls)
            results["signals"]["put_spread_activity"] = put_spread_signals

            # Signal 4: Seasonal Context (summer months)
            seasonal_context = self._check_seasonal_context()
            results["signals"]["seasonal_context"] = seasonal_context

            # Combine signals for pattern detection
            signal_strength = self._calculate_pattern_strength(results["signals"])
            results["pattern_detected"] = signal_strength > self.signal_strength_threshold
            results["signal_strength"] = signal_strength

            # Add detailed metrics
            results["metrics"] = self._calculate_chain_metrics(calls, puts)

            return results

        except Exception as e:
            self.logger.error(f"Error detecting Short Put Arbitrage: {e}")
            return {"pattern_detected": False, "error": str(e)}

    def _detect_unusual_put_volume(self, puts):
        """Detect unusual put volume vs open interest patterns."""
        if puts.empty:
            return {"detected": False, "reason": "No put data"}

        # Calculate volume/OI ratios
        puts_with_ratios = puts.copy()
        puts_with_ratios["vol_oi_ratio"] = puts_with_ratios["vol_oi_ratio"].fillna(0)

        # Find strikes with unusually high volume vs OI
        high_vol_threshold = puts_with_ratios["vol_oi_ratio"].quantile(self.volume_oi_ratio_quantile)
        unusual_puts = puts_with_ratios[
            (puts_with_ratios["vol_oi_ratio"] > high_vol_threshold) & (puts_with_ratios["volume"] > 0)
        ]

        # Look for OTM puts specifically
        current_price = self._estimate_underlying_price(puts)
        otm_unusual_puts = unusual_puts[unusual_puts["strike"] < current_price * self.otm_put_threshold]

        return {
            "detected": len(otm_unusual_puts) >= self.min_unusual_strikes,
            "unusual_strikes": otm_unusual_puts["strike"].tolist(),
            "volume_ratios": otm_unusual_puts["vol_oi_ratio"].tolist(),
            "total_volume": otm_unusual_puts["volume"].sum(),
            "strikes_count": len(otm_unusual_puts),
        }

    def _detect_call_urgency(self, calls):
        """Detect above-ask call buying patterns."""
        if calls.empty:
            return {"detected": False, "reason": "No call data"}

        # Look for calls with high volume and tight bid/ask spreads (indicating urgency)
        calls_with_activity = calls[calls["volume"] > 0].copy()

        if calls_with_activity.empty:
            return {"detected": False, "reason": "No call volume"}

        # Calculate metrics that indicate urgency
        calls_with_activity["spread_pct"] = calls_with_activity["bid_ask_spread_pct"].fillna(0)
        calls_with_activity["volume_score"] = calls_with_activity["volume"] / (calls_with_activity["volume"].max() + 1)

        # High volume, tight spreads = urgency
        urgent_calls = calls_with_activity[
            (calls_with_activity["volume_score"] > 0.3) & (calls_with_activity["spread_pct"] < self.tight_spread_pct)
        ]

        return {
            "detected": len(urgent_calls) > 0,
            "urgent_strikes": urgent_calls["strike"].tolist(),
            "total_urgent_volume": urgent_calls["volume"].sum(),
            "avg_spread_pct": urgent_calls["spread_pct"].mean() if not urgent_calls.empty else 0,
        }

    def _detect_put_spread_pattern(self, puts, calls):
        """Detect multiple OTM put strikes being shorted simultaneously."""
        if puts.empty:
            return {"detected": False, "reason": "No put data"}

        current_price = self._estimate_underlying_price(puts)

        # Focus on OTM puts with volume
        otm_puts_with_volume = puts[
            (puts["strike"] < current_price * self.otm_put_threshold) & (puts["volume"] > 0)
        ].copy()

        if len(otm_puts_with_volume) < self.min_otm_put_activity:
            return {"detected": False, "reason": "Insufficient OTM put activity"}

        # Check for coordinated activity across strikes
        strike_range = otm_puts_with_volume["strike"].max() - otm_puts_with_volume["strike"].min()
        volume_concentration = otm_puts_with_volume["volume"].std() / (otm_puts_with_volume["volume"].mean() + 1)

        # Pattern: Spread across multiple strikes rather than concentrated
        spread_pattern = strike_range > current_price * 0.05 and volume_concentration < 2.0

        return {
            "detected": spread_pattern,
            "strike_range": strike_range,
            "strikes_with_volume": len(otm_puts_with_volume),
            "volume_distribution": volume_concentration,
            "otm_put_strikes": otm_puts_with_volume["strike"].tolist(),
        }

    def _check_seasonal_context(self):
        """Check if current period matches summer month pattern."""
        from src.utils.date_utils import get_datetime_now

        current_month = get_datetime_now().month
        is_summer = current_month in self.summer_months

        return {
            "is_summer_period": is_summer,
            "current_month": current_month,
            "seasonal_boost": 1.2 if is_summer else 1.0,
        }

    def _calculate_pattern_strength(self, signals) -> float:
        """Calculate overall pattern strength from individual signals."""
        weights = {
            "put_volume_anomalies": 0.3,
            "call_urgency": 0.2,
            "put_spread_activity": 0.3,
            "seasonal_context": 0.2,
        }

        total_strength = 0.0

        # Put volume anomalies
        if signals.get("put_volume_anomalies", {}).get("detected", False):
            strikes_count = signals["put_volume_anomalies"].get("strikes_count", 0)
            # Scale by number of strikes
            strength = min(strikes_count / 5.0, 1.0)
            total_strength += weights["put_volume_anomalies"] * strength

        # Call urgency
        if signals.get("call_urgency", {}).get("detected", False):
            total_strength += weights["call_urgency"]

        # Put spread activity
        if signals.get("put_spread_activity", {}).get("detected", False):
            total_strength += weights["put_spread_activity"]

        # Seasonal context
        seasonal_boost = signals.get("seasonal_context", {}).get("seasonal_boost", 1.0)
        if seasonal_boost > 1.0:
            total_strength += weights["seasonal_context"]

        return min(total_strength * seasonal_boost, 1.0)

    def _estimate_underlying_price(self, options_df) -> float:
        """Estimate underlying price from options chain data."""
        if options_df.empty:
            return 0.0

        # Use ATM options to estimate current price
        # Find the strike with the highest gamma (usually near ATM)
        if "gamma" in options_df.columns:
            max_gamma_row = options_df.loc[options_df["gamma"].idxmax()]
            return float(max_gamma_row["strike"])

        # Fallback: use median strike
        return float(options_df["strike"].median())

    def _calculate_chain_metrics(self, calls, puts):
        """Calculate comprehensive options chain metrics."""
        metrics = {}

        if not calls.empty:
            metrics["call_metrics"] = {
                "total_volume": calls["volume"].sum(),
                "total_oi": calls["open_interest"].sum(),
                "avg_iv": calls["implied_volatility"].mean(),
                "strike_range": calls["strike"].max() - calls["strike"].min(),
            }

        if not puts.empty:
            metrics["put_metrics"] = {
                "total_volume": puts["volume"].sum(),
                "total_oi": puts["open_interest"].sum(),
                "avg_iv": puts["implied_volatility"].mean(),
                "strike_range": puts["strike"].max() - puts["strike"].min(),
            }

        if not calls.empty and not puts.empty:
            metrics["put_call_ratios"] = {
                "volume_ratio": puts["volume"].sum() / (calls["volume"].sum() + 1),
                "oi_ratio": puts["open_interest"].sum() / (calls["open_interest"].sum() + 1),
                "iv_skew": puts["implied_volatility"].mean() - calls["implied_volatility"].mean(),
            }

        return metrics


def test_with_alpha_vantage_demo():
    """Test the options analyzer with Alpha Vantage demo data."""
    print("Testing Options Chain Analyzer with Alpha Vantage demo data...")

    try:
        # Use the updated Alpha Vantage client (Issue #180: Skip cache, fetch live only)
        from gex_db_infrastructure.data_sources.alpha_vantage_gex import AlphaVantageGEXClient

        # Initialize client without cache (demo fetches live data)
        client = AlphaVantageGEXClient(cache_manager=None)

        # Test the new fetch_historical_options method
        print("Fetching IBM options data...")
        options_df = client.fetch_historical_options("IBM")  # Uses demo API key

        if options_df.empty:
            print("No options data returned - check API key or connection")
            return None

        print(f"✅ Processed {len(options_df)} option contracts")
        print(f"📊 Columns: {list(options_df.columns)}")

        if "expiration" in options_df.columns:
            print(f"📅 Expiration range: {options_df['expiration'].min()} to {options_df['expiration'].max()}")

        if "strike" in options_df.columns:
            print(f"💰 Strike range: ${options_df['strike'].min():.2f} to ${options_df['strike'].max():.2f}")

        # Test with specific date (historical)
        print("\nTesting historical date (2017-11-15)...")
        historical_df = client.fetch_historical_options("IBM", date="2017-11-15")

        if not historical_df.empty:
            print(f"✅ Historical data: {len(historical_df)} contracts")

        # Analyze for patterns (using latest data)
        analyzer = OptionsChainAnalyzer()
        results = analyzer.detect_short_put_arbitrage_signals(options_df)

        print(f"\n🔍 Short Put Arbitrage Analysis:")
        print(f"   Pattern Detected: {results['pattern_detected']}")
        print(f"   Signal Strength: {results.get('signal_strength', 0):.2f}")

        for signal_name, signal_data in results.get("signals", {}).items():
            detected = signal_data.get("detected", False)
            print(f"   {signal_name}: {'✅' if detected else '❌'}")

        return results

    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_with_alpha_vantage_demo()
