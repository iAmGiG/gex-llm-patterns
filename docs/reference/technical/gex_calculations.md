# GEX Calculations Documentation

## Overview

Gamma Exposure (GEX) calculations form the mathematical core of this research project. GEX quantifies the dollar amount of gamma exposure dealers have from options market making, which directly influences their hedging behavior and creates predictable market movements.

**Status**: Enhanced with three-metric approach and pattern detection framework (Issue #29 completed).

## Data Organization

Market data is organized with structured caching:

- `cache/options/SYMBOL/` - Options chains by symbol and date
- `cache/market_data/SYMBOL/` - Stock OHLCV data by symbol
- Local caching system for efficient data access

## Mathematical Foundation

### Gamma Exposure Formula

The fundamental GEX calculation for each strike:

```md
GEX_strike = Spot_Price × Gamma_strike × Open_Interest_strike × 100 × 0.01

Where:
- Spot_Price: Current underlying price
- Gamma_strike: Option gamma at that strike  
- Open_Interest_strike: Outstanding contracts
- 100: Contract multiplier (shares per contract)
- 0.01: Delta hedging factor
```

### Call vs Put Contributions

```python
Total_GEX_strike = Call_GEX_strike - Put_GEX_strike

Call_GEX_strike = +1 × Spot × Call_Gamma × Call_OI × 100 × 0.01
Put_GEX_strike = -1 × Spot × Put_Gamma × Put_OI × 100 × 0.01
```

**Key Insight**: Calls contribute positive GEX, puts contribute negative GEX to the dealer's position.

## Black-Scholes Gamma Calculation

### Gamma Formula

```python
def calculate_gamma(S, K, T, r, sigma):
    """
    Calculate option gamma using Black-Scholes
    
    S: Spot price
    K: Strike price  
    T: Time to expiration (years)
    r: Risk-free rate
    sigma: Implied volatility
    """
    from scipy.stats import norm
    import numpy as np
    
    # d1 from Black-Scholes
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    # Gamma is same for calls and puts
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    return gamma
```

### Implementation Example

```python
class GEXCalculator:
    def __init__(self, risk_free_rate=0.05):
        self.risk_free_rate = risk_free_rate
        
    def calculate_strike_gex(self, spot_price, strike, time_to_expiry, 
                           implied_vol, call_oi, put_oi):
        """Calculate GEX for a single strike"""
        
        # Calculate gamma using Black-Scholes
        gamma = self.calculate_gamma(
            S=spot_price,
            K=strike, 
            T=time_to_expiry,
            r=self.risk_free_rate,
            sigma=implied_vol
        )
        
        # Calculate contributions
        call_gex = spot_price * gamma * call_oi * 100 * 0.01
        put_gex = -spot_price * gamma * put_oi * 100 * 0.01  # Negative for puts
        
        total_gex = call_gex + put_gex
        
        return {
            'strike': strike,
            'gamma': gamma,
            'call_gex': call_gex,
            'put_gex': put_gex, 
            'total_gex': total_gex
        }
```

## Key Level Identification

### Gamma Flip Point

The most critical level - where total GEX crosses zero:

```python
def find_gamma_flip_point(gex_by_strike):
    """Find where total GEX crosses zero"""
    
    strikes = sorted(gex_by_strike.keys())
    
    for i in range(len(strikes) - 1):
        current_strike = strikes[i]
        next_strike = strikes[i + 1]
        
        current_gex = gex_by_strike[current_strike]['total_gex']
        next_gex = gex_by_strike[next_strike]['total_gex']
        
        # Look for sign change (zero crossing)
        if current_gex * next_gex < 0:
            # Linear interpolation to find exact flip point
            flip_point = current_strike + (next_strike - current_strike) * (
                -current_gex / (next_gex - current_gex)
            )
            return flip_point
    
    return None  # No flip point found
```

### Call Wall and Put Support

```python
def identify_key_levels(gex_by_strike, top_n=5):
    """Identify critical GEX levels"""
    
    # Separate call and put contributions
    call_levels = {k: v['call_gex'] for k, v in gex_by_strike.items() 
                   if v['call_gex'] > 0}
    put_levels = {k: abs(v['put_gex']) for k, v in gex_by_strike.items() 
                  if v['put_gex'] < 0}
    
    # Find highest concentrations
    call_wall = max(call_levels.items(), key=lambda x: x[1])[0] if call_levels else None
    put_support = max(put_levels.items(), key=lambda x: x[1])[0] if put_levels else None
    
    # Top gamma strikes by absolute value
    high_gamma_strikes = sorted(
        gex_by_strike.keys(), 
        key=lambda k: abs(gex_by_strike[k]['total_gex']), 
        reverse=True
    )[:top_n]
    
    return {
        'call_wall': call_wall,
        'put_support': put_support, 
        'high_gamma_strikes': high_gamma_strikes,
        'gamma_flip': find_gamma_flip_point(gex_by_strike)
    }
```

## Market Regime Analysis

### GEX Regimes

```python
def classify_gex_regime(total_gex, gamma_flip, current_price):
    """Classify current market regime based on GEX"""
    
    if total_gex > 1e9:  # > $1B positive
        regime = "POSITIVE_GAMMA_HIGH"
        behavior = "Dealers buy dips, sell rallies (stabilizing)"
        
    elif total_gex > 0:
        regime = "POSITIVE_GAMMA_LOW" 
        behavior = "Mild dealer stabilization"
        
    elif total_gex > -1e9:  # Negative but not extreme
        regime = "NEGATIVE_GAMMA_LOW"
        behavior = "Mild dealer amplification"
        
    else:  # < -$1B negative
        regime = "NEGATIVE_GAMMA_HIGH"
        behavior = "Dealers sell dips, buy rallies (destabilizing)"
    
    # Add flip point context
    if gamma_flip and current_price:
        distance_to_flip = (current_price - gamma_flip) / gamma_flip
        if abs(distance_to_flip) < 0.02:  # Within 2%
            regime += "_NEAR_FLIP"
            behavior += " - NEAR GAMMA FLIP (unstable)"
    
    return {
        'regime': regime,
        'behavior': behavior,
        'total_gex': total_gex,
        'distance_to_flip': distance_to_flip if gamma_flip else None
    }
```

## Daily GEX Metrics

### Complete Daily Calculation

```python
def calculate_daily_gex_metrics(options_chain, spot_price, expiration_dates):
    """Calculate comprehensive daily GEX metrics"""
    
    calculator = GEXCalculator()
    all_strikes = {}
    
    # Process each expiration
    for exp_date in expiration_dates:
        time_to_expiry = calculate_time_to_expiry(exp_date)
        
        exp_chain = options_chain[options_chain['expiration'] == exp_date]
        
        for _, row in exp_chain.iterrows():
            strike = row['strike']
            
            # Calculate GEX for this strike/expiration
            strike_gex = calculator.calculate_strike_gex(
                spot_price=spot_price,
                strike=strike,
                time_to_expiry=time_to_expiry,
                implied_vol=row['implied_vol'],
                call_oi=row['call_oi'],
                put_oi=row['put_oi']
            )
            
            # Aggregate across expirations for same strike
            if strike not in all_strikes:
                all_strikes[strike] = {
                    'total_gex': 0,
                    'call_gex': 0, 
                    'put_gex': 0,
                    'gamma': 0
                }
            
            all_strikes[strike]['total_gex'] += strike_gex['total_gex']
            all_strikes[strike]['call_gex'] += strike_gex['call_gex']
            all_strikes[strike]['put_gex'] += strike_gex['put_gex']
            all_strikes[strike]['gamma'] += strike_gex['gamma']
    
    # Calculate summary metrics
    total_gex = sum(s['total_gex'] for s in all_strikes.values())
    key_levels = identify_key_levels(all_strikes)
    regime = classify_gex_regime(total_gex, key_levels['gamma_flip'], spot_price)
    
    return {
        'date': datetime.now().date(),
        'spot_price': spot_price,
        'total_gex': total_gex,
        'gamma_flip': key_levels['gamma_flip'],
        'call_wall': key_levels['call_wall'],
        'put_support': key_levels['put_support'],
        'high_gamma_strikes': key_levels['high_gamma_strikes'],
        'regime': regime['regime'],
        'regime_behavior': regime['behavior'],
        'strikes_detail': all_strikes
    }
```

## Validation Framework

### Historical Validation

```python
class GEXValidator:
    def __init__(self, reference_source="SpotGamma"):
        self.reference_source = reference_source
        
    def validate_against_reference(self, our_gex, reference_gex, tolerance=0.1):
        """Validate our GEX calculations against known reference"""
        
        # Compare total GEX
        gex_diff_pct = abs(our_gex['total_gex'] - reference_gex['total_gex']) / abs(reference_gex['total_gex'])
        
        # Compare gamma flip
        if our_gex['gamma_flip'] and reference_gex['gamma_flip']:
            flip_diff_pct = abs(our_gex['gamma_flip'] - reference_gex['gamma_flip']) / reference_gex['gamma_flip']
        else:
            flip_diff_pct = 0 if our_gex['gamma_flip'] == reference_gex['gamma_flip'] else 1
        
        validation_result = {
            'total_gex_match': gex_diff_pct < tolerance,
            'gamma_flip_match': flip_diff_pct < tolerance,
            'gex_difference_pct': gex_diff_pct,
            'flip_difference_pct': flip_diff_pct,
            'overall_valid': (gex_diff_pct < tolerance) and (flip_diff_pct < tolerance)
        }
        
        return validation_result
    
    def validate_calculation_sanity(self, gex_data):
        """Perform sanity checks on GEX calculations"""
        
        checks = []
        
        # Check 1: Gamma flip should be near current price
        if gex_data['gamma_flip']:
            flip_distance = abs(gex_data['gamma_flip'] - gex_data['spot_price']) / gex_data['spot_price']
            checks.append({
                'check': 'gamma_flip_reasonable',
                'passed': flip_distance < 0.1,  # Within 10% of spot
                'value': flip_distance,
                'description': 'Gamma flip should be near current price'
            })
        
        # Check 2: Call wall should be above current price
        if gex_data['call_wall']:
            call_wall_above = gex_data['call_wall'] > gex_data['spot_price']
            checks.append({
                'check': 'call_wall_above_spot',
                'passed': call_wall_above,
                'description': 'Call wall should typically be above current price'
            })
        
        # Check 3: Put support should be below current price  
        if gex_data['put_support']:
            put_support_below = gex_data['put_support'] < gex_data['spot_price']
            checks.append({
                'check': 'put_support_below_spot',
                'passed': put_support_below,
                'description': 'Put support should typically be below current price'
            })
        
        # Check 4: Total GEX magnitude should be reasonable
        gex_magnitude = abs(gex_data['total_gex'])
        reasonable_magnitude = 1e8 < gex_magnitude < 1e12  # $100M to $1T
        checks.append({
            'check': 'reasonable_gex_magnitude',
            'passed': reasonable_magnitude,
            'value': gex_magnitude,
            'description': 'Total GEX should be within reasonable bounds'
        })
        
        return {
            'all_checks_passed': all(check['passed'] for check in checks),
            'individual_checks': checks,
            'validation_score': sum(check['passed'] for check in checks) / len(checks)
        }
```

## Performance Optimization

### Efficient Calculation for Large Datasets

```python
def calculate_gex_vectorized(options_df, spot_price, risk_free_rate=0.05):
    """Vectorized GEX calculation for performance"""
    
    import numpy as np
    from scipy.stats import norm
    
    # Vectorized Black-Scholes gamma calculation
    S = spot_price
    K = options_df['strike'].values
    T = options_df['time_to_expiry'].values  
    r = risk_free_rate
    sigma = options_df['implied_vol'].values
    
    # Calculate d1 for all options at once
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    # Calculate gamma (same for calls and puts)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Calculate GEX contributions
    call_gex = S * gamma * options_df['call_oi'].values * 100 * 0.01
    put_gex = -S * gamma * options_df['put_oi'].values * 100 * 0.01
    total_gex = call_gex + put_gex
    
    # Create results DataFrame
    results_df = options_df.copy()
    results_df['gamma'] = gamma
    results_df['call_gex'] = call_gex
    results_df['put_gex'] = put_gex  
    results_df['total_gex'] = total_gex
    
    return results_df
```

### Memory-Efficient Processing

```python
def process_large_options_dataset(options_data, chunk_size=1000):
    """Process large options datasets in chunks"""
    
    total_gex = 0
    all_results = []
    
    for i in range(0, len(options_data), chunk_size):
        chunk = options_data[i:i+chunk_size]
        
        # Process chunk
        chunk_results = calculate_gex_vectorized(chunk, spot_price)
        
        # Accumulate results
        total_gex += chunk_results['total_gex'].sum()
        all_results.append(chunk_results)
        
        # Memory management
        if len(all_results) > 10:
            # Combine and save intermediate results
            combined = pd.concat(all_results)
            save_intermediate_gex_results(combined)
            all_results = []
    
    # Combine final results
    final_results = pd.concat(all_results) if all_results else pd.DataFrame()
    
    return {
        'total_gex': total_gex,
        'detailed_results': final_results
    }
```

## Integration with Pipeline

### Daily GEX Calculation Workflow

```python
def daily_gex_workflow(date, symbol='SPY'):
    """Complete daily GEX calculation workflow"""
    
    # 1. Load options and underlying data
    options_data = load_options_chain(symbol, date)
    spot_price = get_spot_price(symbol, date)
    
    # 2. Calculate GEX metrics
    gex_metrics = calculate_daily_gex_metrics(options_data, spot_price)
    
    # 3. Validate results
    validator = GEXValidator()
    validation_results = validator.validate_calculation_sanity(gex_metrics)
    
    if not validation_results['all_checks_passed']:
        logger.warning(f"GEX validation failed for {date}: {validation_results}")
    
    # 4. Save results
    save_gex_metrics(date, gex_metrics, validation_results)
    
    # 5. Return standardized format
    return {
        'date': date,
        'symbol': symbol,
        'spot_price': spot_price,
        'gex_metrics': gex_metrics,
        'validation': validation_results
    }
```

This GEX calculation framework provides the mathematical foundation for identifying dealer hedging patterns that the LLM will analyze for exploitable market movements.

## Implementation Module

**Location**: `src/gex/`

The complete GEX calculation system is implemented in the `src/gex/` module:

- **`GEXCalculator`** (`src/gex/gex_calculator.py`): Core calculation engine implementing all mathematical formulas documented above
- **Legacy Components** (moved to `docs/legacy/`): Advanced Greeks, validators, and other mathematical precision tools superseded by LLM-interpretable mechanics approach
  - **Second-order Greeks**: Vanna, Charm, Vomma, Veta (Issues #26, #28)
  - **Third-order Greeks**: Speed, Zomma, Color (Issue #27)
  - Both analytical Black-Scholes and finite difference methods

### Usage Example

```python
from src.gex import GEXCalculator
# Legacy: GEXValidator moved to docs/legacy/

# Initialize calculator
calculator = GEXCalculator(risk_free_rate=0.05)

# Calculate daily GEX metrics
gex_metrics = calculator.calculate_daily_gex_metrics(
    options_chain=options_df,
    spot_price=current_price
)

# Validate results
validator = GEXValidator()
validation = validator.validate_calculation_sanity(gex_metrics)

print(f"Total GEX: ${gex_metrics['total_gex']:,.0f}")
print(f"Gamma Flip: {gex_metrics['gamma_flip']}")
print(f"Regime: {gex_metrics['regime']}")
```

### Advanced Greeks Usage

```python
# LEGACY: Advanced Greeks moved to docs/legacy/advanced_greeks.py
# Strategic decision: Focus on LLM-interpretable mechanics vs complex mathematics
# from docs.legacy.advanced_greeks import AdvancedGreeks

# Initialize Greeks calculator (legacy approach)
# greeks_calc = AdvancedGreeks(risk_free_rate=0.05)

# Calculate all Greeks for an option
all_greeks = greeks_calc.calculate_all_greeks(
    S=100,      # Spot price
    K=105,      # Strike price
    T=0.25,     # Time to expiry (years)
    r=0.05,     # Risk-free rate
    sigma=0.2,  # Implied volatility
    option_type='call',
    method='analytical'  # or 'finite_difference'
)

# Access individual Greeks
print(f"Gamma: {all_greeks['gamma']:.6f}")
print(f"Vanna: {all_greeks['vanna']:.6f}")  # Second-order
print(f"Speed: {all_greeks['speed']:.6f}")  # Third-order

# Calculate Greeks surface for visualization
spot_range = np.linspace(90, 110, 100)
gamma_surface = greeks_calc.calculate_greeks_surface(
    spot_range, K=100, T=0.25, r=0.05, sigma=0.2, greek_name='gamma'
)
```

The module provides both individual strike calculations and vectorized processing for high-performance analysis of large options datasets.
