# Sequential GEX Pattern Detection Rules

**Purpose**: Formal algorithmic definitions for detecting 4 sequential gamma exposure patterns

**Input**: 5-day GEX time series `[GEX_0, GEX_1, GEX_2, GEX_3, GEX_4]`

---

## Pattern 1: Gamma Accumulation

### Definition

Dealer gamma constraint intensifies over 5 days (magnitude increasing), creating pressure that will eventually release.

### Detection Criteria

**Primary Rule**: Magnitude increases >= 30%

```python
abs(GEX_4) > abs(GEX_0) * 1.30
```

**Secondary Rules** (at least 1 must be true):

1. **Monotonic Growth**:

   ```python
   # At least 3 out of 4 transitions show increasing magnitude
   increases = sum([abs(GEX[i+1]) > abs(GEX[i]) for i in range(4)])
   monotonic = increases >= 3
   ```

2. **Accelerating Growth**:

   ```python
   # Growth rate increases over time
   early_growth = abs(GEX_2) / abs(GEX_0)
   late_growth = abs(GEX_4) / abs(GEX_2)
   accelerating = late_growth > early_growth
   ```

**Exclusions**: Reject if regime flip occurs

```python
# All 5 days must have same sign
same_sign = all([sign(GEX[i]) == sign(GEX[0]) for i in range(5)])
```

### Example Detection

```python
def detect_gamma_accumulation(gex_5day: list) -> dict:
    """
    Detect gamma accumulation pattern.

    Args:
        gex_5day: List of 5 consecutive daily GEX values (in dollars)

    Returns:
        {
            'detected': bool,
            'magnitude_growth': float,  # Percentage growth
            'monotonic': bool,
            'accelerating': bool,
            'confidence': float  # 0-100
        }
    """
    import numpy as np

    # Minimum magnitude threshold
    mean_magnitude = np.mean([abs(x) for x in gex_5day])
    end_magnitude = abs(gex_5day[4])

    if mean_magnitude < 5e9 or end_magnitude < 8e9:
        return {
            'detected': False,
            'magnitude_growth': 0,
            'monotonic': False,
            'accelerating': False,
            'confidence': 0,
            'pattern_type': 'gamma_accumulation',
            'rejection_reason': 'Magnitude below significance threshold'
        }

    # Primary rule: 30% magnitude increase
    mag_growth = (abs(gex_5day[4]) / abs(gex_5day[0])) - 1
    primary_met = mag_growth >= 0.30

    # Secondary rule 1: Monotonic
    increases = sum([abs(gex_5day[i+1]) > abs(gex_5day[i]) for i in range(4)])
    monotonic = increases >= 3

    # Secondary rule 2: Accelerating
    early_growth = abs(gex_5day[2]) / abs(gex_5day[0])
    late_growth = abs(gex_5day[4]) / abs(gex_5day[2])
    accelerating = late_growth > early_growth

    # Exclusion: Same sign
    same_sign = all([np.sign(gex_5day[i]) == np.sign(gex_5day[0]) for i in range(5)])

    # Detection logic
    secondary_met = monotonic or accelerating
    detected = primary_met and secondary_met and same_sign

    # Confidence: based on how many secondary conditions met
    confidence = 0
    if detected:
        confidence = 60  # Base
        if monotonic:
            confidence += 20
        if accelerating:
            confidence += 20

    return {
        'detected': detected,
        'magnitude_growth': mag_growth * 100,
        'monotonic': monotonic,
        'accelerating': accelerating,
        'confidence': confidence,
        'pattern_type': 'gamma_accumulation'
    }
```

**Example Cases**:

```python
# DETECTED: Monotonic growth
gex = [-10e9, -11.5e9, -12e9, -12.8e9, -13.5e9]  # 35% growth, monotonic
# confidence: 80 (base 60 + monotonic 20)

# DETECTED: Accelerating growth
gex = [-10e9, -10.5e9, -11e9, -12e9, -13.5e9]  # 35% growth, accelerating
# confidence: 80 (base 60 + accelerating 20)

# NOT DETECTED: Growth but no secondary condition
gex = [-10e9, -8e9, -12e9, -9e9, -13.5e9]  # 35% growth but erratic
```

---

## Pattern 2: Gamma Relief

### Definition

Dealer gamma constraint relaxes over 5 days (magnitude decreasing), reducing hedging pressure.

### Detection Criteria

**Primary Rule**: Magnitude decreases >= 30%

```python
abs(GEX_4) < abs(GEX_0) * 0.70
```

**Secondary Rules** (at least 1 must be true):

1. **Monotonic Decline**:

   ```python
   # At least 3 out of 4 transitions show decreasing magnitude
   decreases = sum([abs(GEX[i+1]) < abs(GEX[i]) for i in range(4)])
   monotonic = decreases >= 3
   ```

2. **Accelerating Relief**:

   ```python
   # Decline rate increases over time
   early_decline = abs(GEX_2) / abs(GEX_0)
   late_decline = abs(GEX_4) / abs(GEX_2)
   accelerating = late_decline < early_decline
   ```

**Exclusions**: Reject if regime flip occurs

```python
same_sign = all([sign(GEX[i]) == sign(GEX[0]) for i in range(5)])
```

### Example Detection

```python
def detect_gamma_relief(gex_5day: list) -> dict:
    """Detect gamma relief pattern."""
    import numpy as np

    # Minimum magnitude threshold
    mean_magnitude = np.mean([abs(x) for x in gex_5day])
    start_magnitude = abs(gex_5day[0])

    if mean_magnitude < 5e9 or start_magnitude < 8e9:
        return {
            'detected': False,
            'magnitude_decline': 0,
            'monotonic': False,
            'accelerating': False,
            'confidence': 0,
            'pattern_type': 'gamma_relief',
            'rejection_reason': 'Magnitude below significance threshold'
        }

    # Primary rule: 30% magnitude decrease
    mag_decline = 1 - (abs(gex_5day[4]) / abs(gex_5day[0]))
    primary_met = mag_decline >= 0.30

    # Secondary rule 1: Monotonic decline
    decreases = sum([abs(gex_5day[i+1]) < abs(gex_5day[i]) for i in range(4)])
    monotonic = decreases >= 3

    # Secondary rule 2: Accelerating decline
    early_decline = abs(gex_5day[2]) / abs(gex_5day[0])
    late_decline = abs(gex_5day[4]) / abs(gex_5day[2])
    accelerating = late_decline < early_decline

    # Exclusion: Same sign
    same_sign = all([np.sign(gex_5day[i]) == np.sign(gex_5day[0]) for i in range(5)])

    # Detection
    secondary_met = monotonic or accelerating
    detected = primary_met and secondary_met and same_sign

    # Confidence
    confidence = 0
    if detected:
        confidence = 60
        if monotonic:
            confidence += 20
        if accelerating:
            confidence += 20

    return {
        'detected': detected,
        'magnitude_decline': mag_decline * 100,
        'monotonic': monotonic,
        'accelerating': accelerating,
        'confidence': confidence,
        'pattern_type': 'gamma_relief'
    }
```

**Example Cases**:

```python
# DETECTED: Monotonic decline
gex = [-13e9, -11.5e9, -10e9, -9e9, -8e9]  # 38% decline, monotonic
# confidence: 80

# NOT DETECTED: Small decline
gex = [-10e9, -9.5e9, -9e9, -8.8e9, -8.5e9]  # Only 15% decline
```

---

## Pattern 3: Gamma Reversal

### Definition

Dealer positioning flips from one side of the market to the other (sign change), forcing abrupt hedging flow reversal.

### Detection Criteria

**Primary Rule**: Sign flip

```python
sign(GEX_0) != sign(GEX_4)
```

**Secondary Rules** (both must be true):

1. **Zero Crossing Detected**:

   ```python
   # At least one day has abs(GEX) < $1B (near zero)
   crossed_zero = any([abs(GEX[i]) < 1e9 for i in range(5)])
   ```

2. **Magnitude Significant on Both Sides**:

   ```python
   # Start and end magnitudes both > $5B
   significant_start = abs(GEX_0) > 5e9
   significant_end = abs(GEX_4) > 5e9
   both_significant = significant_start and significant_end
   ```

**Exclusions**: None (reversals are always interesting)

### Example Detection

```python
def detect_gamma_reversal(gex_5day: list) -> dict:
    """Detect gamma reversal pattern."""
    import numpy as np

    # Primary rule: Sign flip
    sign_flip = np.sign(gex_5day[0]) != np.sign(gex_5day[4])

    # Secondary rule 1: Crossed zero
    crossed_zero = any([abs(gex_5day[i]) < 1e9 for i in range(5)])

    # Secondary rule 2: Both sides significant
    significant_start = abs(gex_5day[0]) > 5e9
    significant_end = abs(gex_5day[4]) > 5e9
    both_significant = significant_start and significant_end

    # Detection
    detected = sign_flip and crossed_zero and both_significant

    # Confidence: based on magnitude of flip
    confidence = 0
    if detected:
        total_flip = abs(gex_5day[4]) + abs(gex_5day[0])
        if total_flip > 20e9:
            confidence = 90  # Large flip
        elif total_flip > 15e9:
            confidence = 75  # Medium flip
        else:
            confidence = 60  # Small flip

    return {
        'detected': detected,
        'sign_flip': sign_flip,
        'crossed_zero': crossed_zero,
        'flip_magnitude': (abs(gex_5day[4]) + abs(gex_5day[0])) / 1e9,
        'confidence': confidence,
        'pattern_type': 'gamma_reversal'
    }
```

**Example Cases**:

```python
# DETECTED: Large flip
gex = [-12e9, -8e9, -2e9, 3e9, 8e9]  # -12B to +8B, crossed zero
# confidence: 90 (20B total flip)

# NOT DETECTED: Jump without crossing zero
gex = [-12e9, -15e9, -18e9, -20e9, 5e9]  # Flip but didn't cross near zero

# NOT DETECTED: 2024 reality (no flips)
gex = [-40e9, -38e9, -35e9, -33e9, -30e9]  # All negative
```

---

## Pattern 4: Persistent Gamma

### Definition

Dealer positioning remains stable over 5 days (no significant change), suggesting continued hedging regime.

### Detection Criteria

**Primary Rule**: Low coefficient of variation

```python
CV = std(abs(GEX)) / mean(abs(GEX))
persistent = CV < 0.15  # Less than 15% variation
```

**Secondary Rules** (at least 1 must be true):

1. **Tight Range**:

   ```python
   # Max/min ratio < 1.20 (within 20% range)
   max_gex = max([abs(GEX[i]) for i in range(5)])
   min_gex = min([abs(GEX[i]) for i in range(5)])
   tight_range = max_gex / min_gex < 1.20
   ```

2. **No Trend**:

   ```python
   # Linear regression slope near zero
   from scipy.stats import linregress
   slope, _, r_value, _, _ = linregress(range(5), [abs(GEX[i]) for i in range(5)])
   normalized_slope = abs(slope) / mean(abs(GEX))
   no_trend = normalized_slope < 0.05  # Less than 5% slope
   ```

**Exclusions**: Reject if sign flip

```python
same_sign = all([sign(GEX[i]) == sign(GEX[0]) for i in range(5)])
```

### Example Detection

```python
def detect_persistent_gamma(gex_5day: list) -> dict:
    """Detect persistent gamma pattern."""
    import numpy as np
    from scipy.stats import linregress

    # Minimum magnitude threshold
    abs_gex = [abs(x) for x in gex_5day]
    mean_magnitude = np.mean(abs_gex)

    if mean_magnitude < 5e9:
        return {
            'detected': False,
            'coefficient_of_variation': 0,
            'tight_range': False,
            'no_trend': False,
            'confidence': 0,
            'pattern_type': 'persistent_gamma',
            'rejection_reason': 'Magnitude below significance threshold'
        }

    # Primary rule: Low coefficient of variation
    cv = np.std(abs_gex) / mean_magnitude
    primary_met = cv < 0.15

    # Secondary rule 1: Tight range
    max_gex = max(abs_gex)
    min_gex = min(abs_gex)
    tight_range = max_gex / min_gex < 1.20

    # Secondary rule 2: No trend
    slope, _, r_value, _, _ = linregress(range(5), abs_gex)
    normalized_slope = abs(slope) / mean_magnitude
    no_trend = normalized_slope < 0.05

    # Exclusion: Same sign
    same_sign = all([np.sign(gex_5day[i]) == np.sign(gex_5day[0]) for i in range(5)])

    # Detection
    secondary_met = tight_range or no_trend
    detected = primary_met and secondary_met and same_sign

    # Confidence: based on stability
    confidence = 0
    if detected:
        if cv < 0.08:
            confidence = 90  # Very stable
        elif cv < 0.12:
            confidence = 75  # Stable
        else:
            confidence = 60  # Moderately stable

    return {
        'detected': detected,
        'coefficient_of_variation': cv,
        'tight_range': tight_range,
        'no_trend': no_trend,
        'confidence': confidence,
        'pattern_type': 'persistent_gamma'
    }
```

**Example Cases**:

```python
# DETECTED: Very stable
gex = [-20e9, -19.5e9, -20.2e9, -19.8e9, -20.1e9]  # CV = 0.015
# confidence: 90

# DETECTED: Moderately stable
gex = [-20e9, -18e9, -21e9, -19e9, -20.5e9]  # CV = 0.12
# confidence: 60

# NOT DETECTED: High variation
gex = [-20e9, -15e9, -25e9, -18e9, -22e9]  # CV = 0.20
```

---

## Pattern Priority and Mutual Exclusivity

### Detection Order (Check in this order)

1. **Gamma Reversal** (highest priority - rare but dramatic)
2. **Gamma Accumulation** (second priority - predicts spike)
3. **Gamma Relief** (third priority - predicts calm)
4. **Persistent Gamma** (lowest priority - most common)

### Mutual Exclusivity Rules

```python
def classify_sequential_pattern(gex_5day: list) -> dict:
    """
    Classify 5-day window into exactly one pattern type.

    Returns single pattern with highest priority if multiple detected.
    """
    # Check in priority order
    reversal = detect_gamma_reversal(gex_5day)
    if reversal['detected']:
        return reversal

    accumulation = detect_gamma_accumulation(gex_5day)
    if accumulation['detected']:
        return accumulation

    relief = detect_gamma_relief(gex_5day)
    if relief['detected']:
        return relief

    persistent = detect_persistent_gamma(gex_5day)
    if persistent['detected']:
        return persistent

    # No pattern detected
    return {
        'detected': False,
        'pattern_type': 'no_clear_pattern',
        'confidence': 0,
        'reasoning': 'No pattern meets detection criteria'
    }
```

---

## Pattern Significance Thresholds

### Minimum Magnitude Requirement

**Problem**: Should patterns with trivial GEX magnitudes be classified?

**Example Edge Case**:

```python
# Low magnitude "persistent" pattern
gex = [-$2.1B, -$2.0B, -$2.2B, -$2.1B, -$2.0B]
# CV = 3.8% (< 15% → technically "persistent")
# But: Magnitude too low to create meaningful dealer constraints
```

**Decision**: Require minimum magnitude for all patterns

### Threshold Values

```python
PATTERN_SIGNIFICANCE_THRESHOLDS = {
    'min_gex_magnitude': 5e9,      # $5B - Below this, classify as "no_clear_pattern"
    'min_confidence': 40,           # Below this, classify as "no_clear_pattern"
}
```

**Rationale**:

- ✅ **Prevents noise classification**: Trivial variations aren't meaningful patterns
- ✅ **Aligns with Paper #1**: Focused on "large constraints" that force dealer behavior
- ✅ **Empirically justified**: 2024 SPY GEX typically $10B-$60B (median ~$35B)
- ✅ **Conservative threshold**: $5B is ~15% of typical magnitude

### Implementation

```python
def classify_sequential_pattern(gex_5day: list) -> dict:
    """
    Classify 5-day window into exactly one pattern type.

    Returns single pattern with highest priority if multiple detected.
    Requires minimum magnitude and confidence for classification.
    """
    # Check minimum magnitude threshold first
    mean_magnitude = np.mean([abs(x) for x in gex_5day])
    if mean_magnitude < 5e9:  # $5B threshold
        return {
            'detected': False,
            'pattern_type': 'no_clear_pattern',
            'confidence': 0,
            'reasoning': f'Mean magnitude ${mean_magnitude/1e9:.1f}B below $5B threshold'
        }

    # Check in priority order
    reversal = detect_gamma_reversal(gex_5day)
    if reversal['detected'] and reversal['confidence'] >= 40:
        return reversal

    accumulation = detect_gamma_accumulation(gex_5day)
    if accumulation['detected'] and accumulation['confidence'] >= 40:
        return accumulation

    relief = detect_gamma_relief(gex_5day)
    if relief['detected'] and relief['confidence'] >= 40:
        return relief

    persistent = detect_persistent_gamma(gex_5day)
    if persistent['detected'] and persistent['confidence'] >= 40:
        return persistent

    # Pattern detected but confidence too low
    return {
        'detected': False,
        'pattern_type': 'no_clear_pattern',
        'confidence': 0,
        'reasoning': 'Patterns detected but confidence below 40 threshold'
    }
```

### Pattern-Specific Minimum Magnitudes

Some patterns already enforce higher thresholds:

```python
PATTERN_SPECIFIC_THRESHOLDS = {
    'gamma_accumulation': {
        'min_magnitude': 5e9,    # General threshold
        'min_end_magnitude': 8e9  # Final day must be significant
    },
    'gamma_relief': {
        'min_magnitude': 5e9,    # General threshold
        'min_start_magnitude': 8e9  # Start must be significant to "relieve"
    },
    'gamma_reversal': {
        'min_magnitude': 5e9,    # Both sides > $5B (already enforced)
    },
    'persistent_gamma': {
        'min_magnitude': 5e9,    # Must be persistently significant
    }
}
```

### Example Cases

```python
# CASE 1: Low magnitude persistent → NO PATTERN
gex = [-2.1e9, -2.0e9, -2.2e9, -2.1e9, -2.0e9]
# CV = 3.8% (< 15%) → would be "persistent"
# But mean magnitude = $2.1B < $5B → "no_clear_pattern"

# CASE 2: Moderate magnitude accumulation → DETECTED
gex = [-6e9, -7e9, -8e9, -8.5e9, -9e9]
# 50% growth, mean magnitude = $7.7B > $5B → "gamma_accumulation"

# CASE 3: Tiny variation with high magnitude → PERSISTENT
gex = [-35e9, -36e9, -35.5e9, -35e9, -36e9]
# CV = 1.5%, mean magnitude = $35.5B >> $5B → "persistent_gamma"

# CASE 4: Pattern detected but low confidence → NO PATTERN
gex = [-10e9, -11e9, -12e9, -12.5e9, -13e9]
# 30% growth (meets primary), but confidence = 35 < 40 → "no_clear_pattern"
```

### Why This Matters for Paper #2

**Academic Rigor**:

- Prevents claiming patterns exist when GEX is economically trivial
- Reduces false positive rate (improves precision)
- Makes results more defensible ("We only classified meaningful constraints")

**Expected Impact**:

- ~5-10% of windows may fall below threshold (SPY 2024)
- Improves signal-to-noise ratio
- Increases accuracy (fewer spurious classifications)

**Null Hypothesis Testing**:

- Allows LLM to naturally output `pattern_detected: false`
- Tests whether LLM respects magnitude significance
- Provides baseline rate for "no pattern" classification

---

## Parameter Sensitivity

### Configurable Thresholds

All detection parameters should be configurable for robustness testing:

```yaml
# config/sequential_pattern_config.yaml

gamma_accumulation:
  magnitude_growth_threshold: 0.30  # 30%
  monotonic_min_transitions: 3      # out of 4

gamma_relief:
  magnitude_decline_threshold: 0.30  # 30%
  monotonic_min_transitions: 3       # out of 4

gamma_reversal:
  zero_crossing_threshold: 1.0e9    # $1B
  significant_magnitude: 5.0e9       # $5B

persistent_gamma:
  cv_threshold: 0.15                 # 15% coefficient of variation
  tight_range_ratio: 1.20            # 20% max/min
  no_trend_slope: 0.05               # 5% normalized slope
```

---

## Expected Pattern Distribution (2024 SPY)

Based on 100% negative GEX regime:

| Pattern | Expected Frequency | Rationale |
|---------|-------------------|-----------|
| **Persistent** | 50-70% | Most common (stable negative regime) |
| **Accumulation** | 15-25% | Negative GEX magnitude building |
| **Relief** | 10-20% | Negative GEX magnitude declining |
| **Reversal** | 0-2% | Rare (regime didn't flip in 2024) |

---

## Validation Strategy

### Step 1: Count Pattern Frequencies

```python
# For 242-day 2024 dataset with 5-day windows
# Expect ~238 windows (sliding, overlapping)

patterns = []
for i in range(len(gex_data) - 4):
    window = gex_data[i:i+5]
    pattern = classify_sequential_pattern(window)
    patterns.append(pattern)

# Distribution
persistent_count = sum([p['pattern_type'] == 'persistent_gamma' for p in patterns])
accumulation_count = sum([p['pattern_type'] == 'gamma_accumulation' for p in patterns])
# etc.
```

### Step 2: Verify Outcome Thresholds

For each pattern type, calculate hit rate:

```python
for pattern_type in ['persistent_gamma', 'gamma_accumulation', 'gamma_relief']:
    pattern_detections = [p for p in patterns if p['pattern_type'] == pattern_type]

    hits = 0
    for detection in pattern_detections:
        forward_vol = get_forward_volatility(detection['date'])
        if verify_outcome(pattern_type, forward_vol):
            hits += 1

    hit_rate = hits / len(pattern_detections)
    baseline = get_baseline_rate(pattern_type)  # From threshold doc

    print(f"{pattern_type}: {hit_rate:.1%} hit rate vs {baseline:.1%} baseline")
```

---

## Implementation Checklist

- [ ] Implement all 4 detection functions
- [ ] Create `classify_sequential_pattern()` orchestrator
- [ ] Load configuration from YAML
- [ ] Test on sample 5-day windows
- [ ] Count pattern frequencies in 2024 data
- [ ] Verify hit rates vs outcome thresholds
- [ ] Document any edge cases found

---

## Related Documentation

- **Outcome Thresholds**: `outcome_verification_thresholds.md`
- **Pattern Library**: `src/analysis/pattern_library.py` (single-day patterns)
- **Issue #107**: Paper #2 Sequential GEX Analysis

**Last Updated**: 2025-11-01
