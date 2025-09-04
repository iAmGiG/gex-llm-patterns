"""
GEX-focused technical indicators for enhanced gamma exposure analysis.
Selected indicators from utils/indicator_library.py that complement GEX calculations.
"""

import pandas as pd

##################################
# Core Indicators for GEX Analysis
##################################

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range - measures volatility.
    Useful for GEX analysis to assess volatility regime changes.
    """
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index - momentum oscillator.
    Helps identify oversold/overbought conditions that may affect dealer positioning.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    roll_up = gain.rolling(period).mean()
    roll_down = loss.rolling(period).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))

def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Bollinger Bands - volatility bands around moving average.
    Critical for GEX analysis as bands often align with key gamma levels.
    """
    sma_val = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = sma_val + num_std * std
    lower = sma_val - num_std * std
    return pd.DataFrame({
        "BB_upper": upper,
        "BB_middle": sma_val,
        "BB_lower": lower,
    })

def fibonacci_retracement(high: pd.Series, low: pd.Series, period: int = 20) -> pd.DataFrame:
    """
    Fibonacci retracement levels - key support/resistance.
    Often aligns with major gamma strike concentrations.
    """
    swing_high = high.rolling(window=period).max()
    swing_low = low.rolling(window=period).min()
    price_range = swing_high - swing_low

    return pd.DataFrame({
        "Fib_0_0": swing_high,  # 0% (swing high)
        "Fib_23_6": swing_high - (price_range * 0.236),  # 23.6%
        "Fib_38_2": swing_high - (price_range * 0.382),  # 38.2%
        "Fib_50_0": swing_high - (price_range * 0.500),  # 50% (key level)
        "Fib_61_8": swing_high - (price_range * 0.618),  # 61.8%
        "Fib_100_0": swing_low,  # 100% (swing low)
        "Fib_range": price_range   # Range for reference
    })

def avwap(close: pd.Series, volume: pd.Series, anchor_ts=0) -> pd.Series:
    """
    Anchored VWAP - volume weighted average price from anchor point.
    Critical level that often coincides with dealer zero-gamma levels.
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

##################################
# GEX-Enhanced Analysis Functions
##################################

def gex_volatility_regime(price_data: pd.DataFrame, atr_period: int = 14) :
    """
    Assess volatility regime to contextualize GEX calculations.
    
    Args:
        price_data: DataFrame with OHLCV data
        atr_period: ATR calculation period
        
    Returns:
        Dict with volatility regime assessment
    """
    try:
        atr_vals = atr(price_data['high'], price_data['low'], price_data['close'], atr_period)
        rsi_vals = rsi(price_data['close'])
        
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
            'volatility_regime': vol_regime,
            'atr_current': current_atr,
            'atr_percentile': atr_percentile,
            'rsi_current': current_rsi,
            'gex_interpretation': gex_interpretation,
            'regime_strength': 'high' if abs(atr_percentile - 50) > 30 else 'moderate'
        }
        
    except Exception as e:
        return {
            'volatility_regime': 'unknown',
            'error': str(e)
        }

def identify_key_levels(price_data: pd.DataFrame, gex_levels = None) :
    """
    Identify key technical levels that may align with gamma concentrations.
    
    Args:
        price_data: DataFrame with OHLCV data
        gex_levels: Optional dict with GEX strike levels
        
    Returns:
        Dict with key technical levels and GEX correlation
    """
    try:
        current_price = price_data['close'].iloc[-1]
        
        # Calculate technical levels
        bb_bands = bollinger_bands(price_data['close'])
        fib_levels = fibonacci_retracement(price_data['high'], price_data['low'])
        
        # Get current levels
        current_bb_upper = bb_bands['BB_upper'].iloc[-1]
        current_bb_lower = bb_bands['BB_lower'].iloc[-1]
        current_bb_mid = bb_bands['BB_middle'].iloc[-1]
        
        current_fib_50 = fib_levels['Fib_50_0'].iloc[-1]
        current_fib_618 = fib_levels['Fib_61_8'].iloc[-1]
        current_fib_382 = fib_levels['Fib_38_2'].iloc[-1]
        
        key_levels = {
            'bb_upper': current_bb_upper,
            'bb_middle': current_bb_mid,
            'bb_lower': current_bb_lower,
            'fib_50': current_fib_50,
            'fib_618': current_fib_618,
            'fib_382': current_fib_382,
        }
        
        # Calculate distances from current price
        level_distances = {}
        for level_name, level_price in key_levels.items():
            distance_pct = ((level_price - current_price) / current_price) * 100
            level_distances[f"{level_name}_distance"] = distance_pct
        
        # Find nearest significant levels
        abs_distances = {k: abs(v) for k, v in level_distances.items()}
        nearest_level = min(abs_distances, key=abs_distances.get).replace('_distance', '')
        
        result = {
            'current_price': current_price,
            'key_levels': key_levels,
            'level_distances': level_distances,
            'nearest_technical_level': nearest_level,
            'nearest_distance': level_distances[f"{nearest_level}_distance"]
        }
        
        # Add GEX correlation if provided
        if gex_levels:
            gex_correlations = []
            for tech_name, tech_level in key_levels.items():
                for gex_name, gex_level in gex_levels.items():
                    if abs(tech_level - gex_level) / tech_level < 0.02:  # Within 2%
                        gex_correlations.append({
                            'technical_level': tech_name,
                            'gex_level': gex_name,
                            'convergence': abs(tech_level - gex_level)
                        })
            
            result['gex_correlations'] = gex_correlations
        
        return result
        
    except Exception as e:
        return {
            'current_price': price_data['close'].iloc[-1] if not price_data.empty else None,
            'error': str(e)
        }

def enhanced_gex_context(price_data: pd.DataFrame, gex_data = None) :
    """
    Comprehensive technical context for GEX analysis.
    
    Args:
        price_data: DataFrame with OHLCV data
        gex_data: Optional GEX calculation results
        
    Returns:
        Dict with enhanced GEX context including technical analysis
    """
    try:
        vol_regime = gex_volatility_regime(price_data)
        key_levels = identify_key_levels(price_data, gex_data.get('levels', {}) if gex_data else None)
        
        # Calculate AVWAP if volume data available
        avwap_level = None
        if 'volume' in price_data.columns:
            avwap_vals = avwap(price_data['close'], price_data['volume'])
            avwap_level = avwap_vals.iloc[-1]
        
        context = {
            'volatility_analysis': vol_regime,
            'technical_levels': key_levels,
            'avwap_level': avwap_level,
            'analysis_timestamp': pd.Timestamp.now(),
        }
        
        # Add trading recommendations based on technical + GEX confluence
        recommendations = []
        
        if vol_regime['volatility_regime'] == 'low_volatility':
            recommendations.append("Low vol regime: GEX effects amplified - watch for sharp moves near flip points")
        
        if key_levels.get('gex_correlations'):
            recommendations.append("Technical-GEX convergence detected - key inflection points identified")
        
        if abs(key_levels.get('nearest_distance', 100)) < 2:
            recommendations.append(f"Near key technical level: {key_levels.get('nearest_technical_level')}")
        
        context['trading_recommendations'] = recommendations
        
        return context
        
    except Exception as e:
        return {
            'error': str(e),
            'analysis_timestamp': pd.Timestamp.now()
        }

##################################
# Exported Functions
##################################

__all__ = [
    'atr',
    'rsi', 
    'bollinger_bands',
    'fibonacci_retracement',
    'avwap',
    'gex_volatility_regime',
    'identify_key_levels',
    'enhanced_gex_context'
]