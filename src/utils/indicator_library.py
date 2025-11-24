import numpy as np
import pandas as pd

# Exported indicator functions
__all__ = [
    "ema",
    "sma",
    "rsi",
    "atr",
    "supertrend",
    "avwap",
    "macd",
    "bollinger_bands",
    "adx",
    "ichimoku",
    "stochrsi",
    "cci",
    "fibonacci_retracement",
    "gex_volatility_regime",
    "identify_key_levels",
    "enhanced_gex_context",
]


# --- Trend ---
def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()


def sma(series, window):
    return series.rolling(window=window).mean()


# --- momentum ---
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    roll_up = gain.rolling(period).mean()
    roll_down = loss.rolling(period).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))


# --- Volatility ---
def atr(high, low, close, period=14):
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# --- Composit trend/stop ---
def supertrend(
    high,
    low,
    close,
    period=10,
    mult=3.0,
):
    """Vectorised Supertrend implementation (no explicit Python loop).

    Returns a pd.Series aligned to `close.index`.
    """
    atr_vals = atr(high=high, low=low, close=close, period=period)
    hl2 = (high + low) / 2
    upper = hl2 + mult * atr_vals
    lower = hl2 - mult * atr_vals

    st = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(True, index=close.index)  # when true = uptrend

    for i in range(len(close)):
        if i == 0:
            st.iat[i] = lower.iat[i]
            continue
        # In-trend "stickiness"
        if direction.iat[i - 1]:
            st.iat[i] = max(lower.iat[i], st.iat[i - 1])
        else:
            st.iat[i] = min(upper.iat[i], st.iat[i - 1])

        # flip on close cross
        direction.iat[i] = close.iat[i] > st.iat[i]
    return st


# --- AVWAP ---
def avwap(
    close,
    volume,
    anchor_ts=0,
):
    """Anchored VWAP.

    Parameters
    ----------
    close : pd.Series
        Close prices.
    volume : pd.Series
        Volume series.
    anchor_ts : int, str, or pd.Timestamp, optional
        Anchor position (index value, ISO date string, or integer index).
        Defaults to the first row when ``0``.
    """
    anchor_idx = 0
    if anchor_ts is not None:
        if isinstance(anchor_ts, (str, pd.Timestamp)):
            anchor_idx = close.index.get_indexer([pd.Timestamp(anchor_ts)], method="nearest")[0]
        elif isinstance(anchor_ts, int):
            anchor_idx = anchor_ts
    pv = (close * volume).cumsum()
    vol = volume.cumsum()
    if anchor_idx > 0:
        pv = pv - pv.iloc[anchor_idx - 1]
        vol = vol - vol.iloc[anchor_idx - 1]
    return pv / vol


# --- MACD ---
def macd(series, fast=12, slow=26, signal=9):
    """Moving Average Convergence Divergence."""
    ema_fast = ema(series, span=fast)
    ema_slow = ema(series, span=slow)
    macd_line = ema_fast - ema_slow
    macd_signal = ema(macd_line, span=signal)
    hist = macd_line - macd_signal
    return pd.DataFrame(
        {
            "MACD_line": macd_line,
            "MACD_signal": macd_signal,
            "MACD_hist": hist,
        }
    )


# --- Bollinger Bands ---
def bollinger_bands(series, window=20, num_std=2.0):
    mid = sma(series, window)
    std = series.rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame(
        {
            "BB_upper": upper,
            "BB_middle": mid,
            "BB_lower": lower,
        }
    )


# --- ADX and DI +/- ---
def adx(high, low, close, period=14):
    up_move = high.diff()
    down_move = low.diff().abs()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr_vals = tr.rolling(window=period).sum()
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period).sum() / atr_vals
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period).sum() / atr_vals
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx_val = dx.rolling(window=period).mean()

    return pd.DataFrame(
        {
            "ADX": adx_val,
            "DI_pos": plus_di,
            "DI_neg": minus_di,
        }
    )


# --- Ichimoku Baseline & Cloud ---
def ichimoku(
    high,
    low,
    close,
    conv_period=9,
    base_period=26,
    span_b_period=52,
):
    tenkan = (high.rolling(conv_period).max() + low.rolling(conv_period).min()) / 2
    kijun = (high.rolling(base_period).max() + low.rolling(base_period).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(base_period)
    span_b = ((high.rolling(span_b_period).max() + low.rolling(span_b_period).min()) / 2).shift(base_period)

    return pd.DataFrame(
        {
            "Ichimoku_baseline": kijun,
            "Ichimoku_span_a": span_a,
            "Ichimoku_span_b": span_b,
        }
    )


# --- Stochastic RSI ---
def stochrsi(
    series,
    rsi_period=14,
    stoch_period=14,
    k_period=3,
    d_period=3,
):
    rsi_vals = rsi(series, rsi_period)
    min_rsi = rsi_vals.rolling(stoch_period).min()
    max_rsi = rsi_vals.rolling(stoch_period).max()
    stoch = (rsi_vals - min_rsi) / (max_rsi - min_rsi)
    k = stoch.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return pd.DataFrame(
        {
            "StochRSI": stoch,
            "StochRSI_K": k,
            "StochRSI_D": d,
        }
    )


# --- Commodity Channel Index ---
def cci(high, low, close, period=20):
    tp = (high + low + close) / 3
    ma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - ma) / (0.015 * mad)


# --- Fibonacci Retracement ---
def fibonacci_retracement(high, low, period=20):
    """Calculate Fibonacci retracement levels for support and resistance analysis.

    Parameters:
    -----------
    high : pd.Series
        High price series
    low : pd.Series
        Low price series
    period : int, default 20
        Lookback period for identifying significant high/low points

    Returns:
    --------
    pd.DataFrame
        DataFrame with fibonacci retracement levels:
        - Fib_0_0: 0% level (swing high)
        - Fib_23_6: 23.6% retracement level
        - Fib_38_2: 38.2% retracement level
        - Fib_50_0: 50% retracement level (key support/resistance)
        - Fib_61_8: 61.8% retracement level
        - Fib_100_0: 100% level (swing low)
    """
    # Find swing highs and lows over the lookback period
    swing_high = high.rolling(window=period).max()
    swing_low = low.rolling(window=period).min()

    # Calculate the range between swing high and low
    price_range = swing_high - swing_low

    # Calculate fibonacci retracement levels
    fib_0_0 = swing_high  # 0% (swing high)
    fib_23_6 = swing_high - (price_range * 0.236)  # 23.6%
    fib_38_2 = swing_high - (price_range * 0.382)  # 38.2%
    fib_50_0 = swing_high - (price_range * 0.500)  # 50% (key level)
    fib_61_8 = swing_high - (price_range * 0.618)  # 61.8%
    fib_100_0 = swing_low  # 100% (swing low)

    return pd.DataFrame(
        {
            "Fib_0_0": fib_0_0,
            "Fib_23_6": fib_23_6,
            "Fib_38_2": fib_38_2,
            "Fib_50_0": fib_50_0,  # Key 50% retracement level
            "Fib_61_8": fib_61_8,
            "Fib_100_0": fib_100_0,
            "Fib_range": price_range,  # Range for reference
        }
    )


##################################
# GEX-Enhanced Analysis Functions
##################################


def gex_volatility_regime(price_data, atr_period: int = 14):
    """Assess volatility regime to contextualize GEX calculations.

    Args:
        price_data: DataFrame with OHLCV data
        atr_period: ATR calculation period

    Returns:
        Dict with volatility regime assessment
    """
    try:
        atr_vals = atr(price_data["high"], price_data["low"], price_data["close"], atr_period)
        rsi_vals = rsi(price_data["close"])

        current_atr = atr_vals.iloc[-1]
        atr_percentile = (atr_vals <= current_atr).mean() * 100

        current_rsi = rsi_vals.iloc[-1]

        # Determine volatility regime
        if atr_percentile > 80:
            vol_regime = "high_volatility"
            gex_interpretation = "Expect reduced gamma effects due to wide spreads"
        elif atr_percentile < 20:
            vol_regime = "low_volatility"
            gex_interpretation = "Enhanced gamma effects - tight dealer positioning"
        else:
            vol_regime = "normal_volatility"
            gex_interpretation = "Standard gamma exposure dynamics"

        return {
            "volatility_regime": vol_regime,
            "atr_current": current_atr,
            "atr_percentile": atr_percentile,
            "rsi_current": current_rsi,
            "gex_interpretation": gex_interpretation,
            "regime_strength": "high" if abs(atr_percentile - 50) > 30 else "moderate",
        }

    except Exception as e:
        return {"volatility_regime": "unknown", "error": str(e)}


def identify_key_levels(price_data, gex_levels=None):
    """Identify key technical levels that may align with gamma concentrations.

    Args:
        price_data: DataFrame with OHLCV data
        gex_levels: Optional dict with GEX strike levels

    Returns:
        Dict with key technical levels and GEX correlation
    """
    try:
        current_price = price_data["close"].iloc[-1]

        # Calculate technical levels
        bb_bands = bollinger_bands(price_data["close"])
        fib_levels = fibonacci_retracement(price_data["high"], price_data["low"])

        # Get current levels
        current_bb_upper = bb_bands["BB_upper"].iloc[-1]
        current_bb_lower = bb_bands["BB_lower"].iloc[-1]
        current_bb_mid = bb_bands["BB_middle"].iloc[-1]

        current_fib_50 = fib_levels["Fib_50_0"].iloc[-1]
        current_fib_618 = fib_levels["Fib_61_8"].iloc[-1]
        current_fib_382 = fib_levels["Fib_38_2"].iloc[-1]

        key_levels = {
            "bb_upper": current_bb_upper,
            "bb_middle": current_bb_mid,
            "bb_lower": current_bb_lower,
            "fib_50": current_fib_50,
            "fib_618": current_fib_618,
            "fib_382": current_fib_382,
        }

        # Calculate distances from current price
        level_distances = {}
        for level_name, level_price in key_levels.items():
            distance_pct = ((level_price - current_price) / current_price) * 100
            level_distances[f"{level_name}_distance"] = distance_pct

        # Find nearest significant levels
        abs_distances = {k: abs(v) for k, v in level_distances.items()}
        nearest_level = min(abs_distances, key=abs_distances.get).replace("_distance", "")

        result = {
            "current_price": current_price,
            "key_levels": key_levels,
            "level_distances": level_distances,
            "nearest_technical_level": nearest_level,
            "nearest_distance": level_distances[f"{nearest_level}_distance"],
        }

        # Add GEX correlation if provided
        if gex_levels:
            gex_correlations = []
            for tech_name, tech_level in key_levels.items():
                for gex_name, gex_level in gex_levels.items():
                    if abs(tech_level - gex_level) / tech_level < 0.02:  # Within 2%
                        gex_correlations.append(
                            {
                                "technical_level": tech_name,
                                "gex_level": gex_name,
                                "convergence": abs(tech_level - gex_level),
                            }
                        )

            result["gex_correlations"] = gex_correlations

        return result

    except Exception as e:
        return {"current_price": price_data["close"].iloc[-1] if not price_data.empty else None, "error": str(e)}


def enhanced_gex_context(price_data, gex_data=None):
    """Comprehensive technical context for GEX analysis.

    Args:
        price_data: DataFrame with OHLCV data
        gex_data: Optional GEX calculation results

    Returns:
        Dict with enhanced GEX context including technical analysis
    """
    try:
        vol_regime = gex_volatility_regime(price_data)
        key_levels = identify_key_levels(price_data, gex_data.get("levels", {}) if gex_data else None)

        # Calculate AVWAP if volume data available
        avwap_level = None
        if "volume" in price_data.columns:
            avwap_vals = avwap(price_data["close"], price_data["volume"])
            avwap_level = avwap_vals.iloc[-1]

        context = {
            "volatility_analysis": vol_regime,
            "technical_levels": key_levels,
            "avwap_level": avwap_level,
            "analysis_timestamp": pd.Timestamp.now(),
        }

        # Add trading recommendations based on technical + GEX confluence
        recommendations = []

        if vol_regime["volatility_regime"] == "low_volatility":
            recommendations.append("Low vol regime: GEX effects amplified - watch for sharp moves near flip points")

        if key_levels.get("gex_correlations"):
            recommendations.append("Technical-GEX convergence detected - key inflection points identified")

        if abs(key_levels.get("nearest_distance", 100)) < 2:
            recommendations.append(f"Near key technical level: {key_levels.get('nearest_technical_level')}")

        context["trading_recommendations"] = recommendations

        return context

    except Exception as e:
        return {"error": str(e), "analysis_timestamp": pd.Timestamp.now()}
