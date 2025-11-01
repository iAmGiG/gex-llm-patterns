# Sequential GEX Pattern: Outcome Verification Thresholds

**Purpose**: Define empirically-driven thresholds for verifying sequential pattern predictions

**Data Source**: 2024 SPY validation data (242 trading days, 100% negative GEX regime)

---

## 2024 Baseline Volatility Distribution

### T+1 Forward Volatility (Realized)
- **Mean**: 0.62%
- **Median (P50)**: 0.48%
- **P25 (Low vol)**: 0.22%
- **P75 (High vol)**: 0.86%
- **P90 (Extreme vol)**: 1.32%

### T+3 Forward Volatility
- **Mean**: 1.09%
- **Median (P50)**: 0.88%
- **P75 (High vol)**: 1.48%
- **P90 (Extreme vol)**: 2.32%

---

## Pattern-Specific Thresholds

### Pattern 1: Gamma Accumulation

**Definition**: GEX magnitude increases >= 30% over 5 days (constraint building)

**Prediction**: Amplified volatility when constraint released

**Verification Thresholds**:

#### Option A: Conservative (Recommended for Paper #2)
```yaml
verification:
  forward_1d_realized_vol: ">0.86%"  # P75 threshold (top quartile)
  forward_3d_max_range: ">1.48%"     # P75 threshold
  rationale: "Predicts above-average volatility (top 25%)"
  expected_hit_rate: "25% baseline, 35-45% if pattern works"
```

#### Option B: Moderate
```yaml
verification:
  forward_1d_realized_vol: ">0.72%"  # P66 threshold (top third)
  forward_3d_max_range: ">1.23%"     # P66 threshold
  rationale: "Predicts elevated volatility (top 33%)"
  expected_hit_rate: "33% baseline, 45-55% if pattern works"
```

#### Option C: Aggressive (High bar)
```yaml
verification:
  forward_1d_realized_vol: ">1.32%"  # P90 threshold (top decile)
  forward_3d_max_range: ">2.32%"     # P90 threshold
  rationale: "Predicts extreme volatility only"
  expected_hit_rate: "10% baseline, 15-25% if pattern works"
```

**Recommendation**: Use **Conservative (A)** for Paper #2 to demonstrate statistical edge while maintaining reasonable hit rates.

---

### Pattern 2: Gamma Relief

**Definition**: GEX magnitude decreases >= 30% over 5 days (constraint relaxing)

**Prediction**: Below-average volatility (dealers need less hedging)

**Verification Thresholds**:

#### Option A: Conservative (Recommended)
```yaml
verification:
  forward_1d_realized_vol: "<0.22%"  # P25 threshold (bottom quartile)
  forward_3d_avg_vol: "<0.44%"       # P25 threshold for T+3
  rationale: "Predicts below-average volatility (bottom 25%)"
  expected_hit_rate: "25% baseline, 35-45% if pattern works"
```

#### Option B: Moderate
```yaml
verification:
  forward_1d_realized_vol: "<0.35%"  # P33 threshold (bottom third)
  forward_3d_avg_vol: "<0.60%"       # P33 threshold
  rationale: "Predicts dampened volatility (bottom 33%)"
  expected_hit_rate: "33% baseline, 43-53% if pattern works"
```

**Recommendation**: Use **Conservative (A)** for clear signal vs noise.

---

### Pattern 3: Gamma Reversal

**Definition**: GEX flips sign (e.g., -$10B to +$5B) within 5 days

**Prediction**: Immediate volatility spike as market reprices hedging flows

**Verification Thresholds**:

#### Option A: Aggressive (Recommended - Expect Spike)
```yaml
verification:
  forward_1d_realized_vol: ">1.32%"  # P90 threshold (top decile)
  day_of_spike: "True"               # Volatility on flip day itself
  rationale: "Reversals should cause sharp repricing"
  expected_hit_rate: "10% baseline, 25-40% if pattern works"
```

#### Option B: Moderate
```yaml
verification:
  forward_1d_realized_vol: ">0.86%"  # P75 threshold
  rationale: "At minimum, above-average volatility"
  expected_hit_rate: "25% baseline, 40-55% if pattern works"
```

**Recommendation**: Use **Aggressive (A)** because reversals are rare but should be dramatic.

**Note**: In 2024, zero GEX reversals occurred (100% negative regime). This pattern may require 2023 or 2025 data to test.

---

### Pattern 4: Persistent Gamma

**Definition**: GEX magnitude stable (+/- 10%) over 5 days (no constraint change)

**Prediction**: Continued low-moderate volatility (status quo)

**Verification Thresholds**:

#### Option A: Conservative (Recommended)
```yaml
verification:
  forward_1d_realized_vol: "<0.48%"  # P50 threshold (below median)
  forward_3d_avg_vol: "<0.88%"       # P50 threshold
  rationale: "Predicts below-median volatility (continuation)"
  expected_hit_rate: "50% baseline, 55-65% if pattern works"
```

#### Option B: Strict
```yaml
verification:
  forward_1d_realized_vol: "<0.22%"  # P25 threshold (bottom quartile)
  rationale: "Predicts very low volatility"
  expected_hit_rate: "25% baseline, 35-45% if pattern works"
```

**Recommendation**: Use **Conservative (A)** for modest but testable prediction.

---

## Statistical Framework

### How to Interpret Hit Rates

**Pattern Success Criteria**:
- **Null Hypothesis**: Hit rate = baseline percentile (random)
- **Alternative**: Hit rate > baseline + 10pp (pattern has signal)

**Examples**:

| Pattern | Threshold | Baseline | Success Threshold | Strong Success |
|---------|-----------|----------|-------------------|----------------|
| Accumulation (P75) | >0.86% | 25% | 35% | 45% |
| Relief (P25) | <0.22% | 25% | 35% | 45% |
| Reversal (P90) | >1.32% | 10% | 20% | 30% |
| Persistent (P50) | <0.48% | 50% | 60% | 70% |

### Statistical Test

For each pattern with N detections:

```python
# Binomial test
from scipy.stats import binom_test

detections = 50  # Number of times pattern detected
hits = 22        # Number of times outcome verified
baseline = 0.25  # P75 threshold

p_value = binom_test(hits, detections, baseline, alternative='greater')

if p_value < 0.05:
    print("Pattern has statistically significant predictive power")
```

---

## Multi-Threshold Testing Strategy

**For Paper #2**, test all patterns with multiple thresholds:

### Phase 1: Primary Analysis (Conservative Thresholds)
- Use P75/P25 thresholds for all patterns
- Report hit rates and binomial p-values
- This is the main result

### Phase 2: Robustness Check (Moderate Thresholds)
- Use P66/P33 thresholds
- Show results are stable across threshold choices
- Include in appendix

### Phase 3: Extreme Event Detection (Aggressive Thresholds)
- Use P90/P10 thresholds
- Test if patterns predict extreme moves
- Valuable for risk management applications

---

## Expected Results by Pattern

### Best Case Scenarios (If Patterns Work)

**Gamma Accumulation**:
- Conservative: 40-50% hit rate vs 25% baseline
- Binomial p < 0.01 with N = 30+ detections

**Gamma Relief**:
- Conservative: 35-45% hit rate vs 25% baseline
- Binomial p < 0.05 with N = 30+ detections

**Gamma Reversal**:
- Aggressive: 25-35% hit rate vs 10% baseline
- Hard to test (need regime variation)

**Persistent Gamma**:
- Conservative: 60-70% hit rate vs 50% baseline
- Easiest to validate (most common in 2024)

### Worst Case Scenarios (If Patterns Don't Work)

- Hit rates = baseline percentiles
- p-values > 0.10 (no statistical significance)
- **Still publishable**: "Temporal patterns show limited predictive power beyond single-day constraints"

---

## Recommended Approach for Paper #2

### Step 1: Use Conservative Thresholds Across Board

```yaml
gamma_accumulation:
  forward_1d_realized_vol: ">0.86%"  # P75

gamma_relief:
  forward_1d_realized_vol: "<0.22%"  # P25

gamma_reversal:
  forward_1d_realized_vol: ">1.32%"  # P90 (expect extreme)

persistent_gamma:
  forward_1d_realized_vol: "<0.48%"  # P50
```

### Step 2: Run Fast Test (50-day sample from 2024)

- Detect sequential patterns in 50-day window
- Calculate hit rates for each pattern
- Compute binomial p-values

### Step 3: GO/NO-GO Decision

**GO (Full Paper #2)**:
- At least 2 patterns show hit rate > baseline + 10pp
- At least 1 pattern has p < 0.05

**NO-GO (Fold into Paper #1 discussion)**:
- All patterns show hit rate ≈ baseline
- No statistical significance

---

## Implementation

### Python Code Snippet

```python
def verify_pattern_outcome(
    pattern_name: str,
    forward_vol: float,
    threshold_config: dict
) -> bool:
    """
    Verify if pattern prediction materialized.

    Args:
        pattern_name: 'gamma_accumulation', 'gamma_relief', etc.
        forward_vol: Actual forward realized volatility (%)
        threshold_config: Dict with thresholds per pattern

    Returns:
        bool: True if outcome verified
    """
    thresholds = {
        'gamma_accumulation': {'forward_1d_realized_vol': 0.86, 'operator': '>'},
        'gamma_relief': {'forward_1d_realized_vol': 0.22, 'operator': '<'},
        'gamma_reversal': {'forward_1d_realized_vol': 1.32, 'operator': '>'},
        'persistent_gamma': {'forward_1d_realized_vol': 0.48, 'operator': '<'}
    }

    config = thresholds[pattern_name]
    threshold = config['forward_1d_realized_vol']
    operator = config['operator']

    if operator == '>':
        return forward_vol > threshold
    else:
        return forward_vol < threshold
```

---

## References

**Data Source**: `reports/statistical_validation/gamma_positioning_timeseries_2024.csv`

**Related Issues**:
- Issue #99: Granger causality (validates predictive relationship)
- Issue #100: Lead-lag analysis (validates regime effects)
- Issue #107: Paper #2 sequential GEX analysis

**Last Updated**: 2025-11-01
