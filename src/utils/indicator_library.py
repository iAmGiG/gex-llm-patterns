import pandas as pd
import numpy as np


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
]


# --- Trend ---
def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


# --- momentum ---
def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    roll_up = gain.rolling(period).mean()
    roll_down = loss.rolling(period).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))


# --- Volatility ---
def atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()


# --- Composit trend/stop ---
def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    mult: float = 3.0,
) -> pd.Series:
    """
    Vectorised Supertrend implementation (no explicit Python loop).
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
    close: pd.Series,
    volume: pd.Series,
    anchor_ts: int | str | pd.Timestamp = 0,
) -> pd.Series:
    """Anchored VWAP.

    Parameters
    ----------
    close : pd.Series
        Close prices.
    volume : pd.Series
        Volume series.
    anchor_ts : int | str | pd.Timestamp, optional
        Anchor position (index value, ISO date string, or integer index).
        Defaults to the first row when ``0``.
    """
    anchor_idx = 0
    if anchor_ts is not None:
        if isinstance(anchor_ts, (str, pd.Timestamp)):
            anchor_idx = close.index.get_indexer(
                [pd.Timestamp(anchor_ts)], method="nearest")[0]
        elif isinstance(anchor_ts, int):
            anchor_idx = anchor_ts
    pv = (close * volume).cumsum()
    vol = volume.cumsum()
    if anchor_idx > 0:
        pv = pv - pv.iloc[anchor_idx - 1]
        vol = vol - vol.iloc[anchor_idx - 1]
    return pv / vol


# --- MACD ---
def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
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
def bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
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
def adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.DataFrame:
    up_move = high.diff()
    down_move = low.diff().abs()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) &
                        (down_move > 0), down_move, 0.0)

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
    minus_di = 100 * \
        pd.Series(minus_dm).rolling(window=period).sum() / atr_vals
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
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    conv_period: int = 9,
    base_period: int = 26,
    span_b_period: int = 52,
) -> pd.DataFrame:
    tenkan = (high.rolling(conv_period).max() +
              low.rolling(conv_period).min()) / 2
    kijun = (high.rolling(base_period).max() +
             low.rolling(base_period).min()) / 2
    span_a = ((tenkan + kijun) / 2).shift(base_period)
    span_b = (
        (high.rolling(span_b_period).max() + low.rolling(span_b_period).min()) / 2
    ).shift(base_period)

    return pd.DataFrame(
        {
            "Ichimoku_baseline": kijun,
            "Ichimoku_span_a": span_a,
            "Ichimoku_span_b": span_b,
        }
    )


# --- Stochastic RSI ---
def stochrsi(
    series: pd.Series,
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_period: int = 3,
    d_period: int = 3,
) -> pd.DataFrame:
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
def cci(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20
) -> pd.Series:
    tp = (high + low + close) / 3
    ma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    return (tp - ma) / (0.015 * mad)


# --- Fibonacci Retracement ---
def fibonacci_retracement(
    high: pd.Series, low: pd.Series, period: int = 20
) -> pd.DataFrame:
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

    return pd.DataFrame({
        "Fib_0_0": fib_0_0,
        "Fib_23_6": fib_23_6,
        "Fib_38_2": fib_38_2,
        "Fib_50_0": fib_50_0,      # Key 50% retracement level
        "Fib_61_8": fib_61_8,
        "Fib_100_0": fib_100_0,
        "Fib_range": price_range   # Range for reference
    })
