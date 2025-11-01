# Sequential Prompt Template Design - Paper #2

**Status**: Approved (Nov 1, 2025)
**Issue**: #89, #107
**Purpose**: Define prompt structure for 5-day sequential GEX analysis

---

## Design Decisions - APPROVED ✅

### 1. Raw Data Only Approach (Option B - LLM Derives Trajectory)

**DECISION (Nov 1, 2025)**: Raw data only, NO pre-calculated trajectory summary

**Per-Day Data Provided**:
```yaml
day_data:
  net_gex: -2.1e9        # Raw GEX value (dollars)
  flip_point: 545.00     # Zero-gamma strike level
  spot_price: 548.10     # Current price
```

**NO Trajectory Summary** - LLM must recognize patterns from raw sequence

**Rationale**:
- ✅ **Maintains Paper #1 consistency**: Gave LLM raw GEX, it detected patterns
- ✅ **True test of temporal reasoning**: Can LLM identify escalation/relief from sequences?
- ✅ **More academically defensible**: "LLM detected escalating gamma" > "We labeled it escalating"
- ✅ **Aligns with obfuscation philosophy**: No hints, just structural data
- ✅ **Stronger signal if successful**: Lower detection rate expected, but more meaningful

**Expected Impact**:
- Detection rate: Likely **lower** than with hints (65-70% vs 71.5% baseline)
- If improves over single-day → **stronger evidence** of temporal understanding
- More impressive academically (LLM derives trajectory itself)

**Fallback Plan**:
- If Phase 1 shows NO improvement, run Phase 1b WITH trajectory summaries as ablation study
- Test if hints improve detection (measures benefit of pre-calculation)

### 2. Excluded Data (Phase 1 Baseline)

**NOT included in Phase 1**:
- ❌ Regime labels ("NEGATIVE_GAMMA" / "POSITIVE_GAMMA")
- ❌ Strike-level concentrations
- ❌ Volume anomalies
- ❌ Gamma walls
- ❌ Pattern hints

**Reason**: Keep baseline simple, matches Paper #1 unbiased approach

---

## Template Configuration

### Add to `config_defaults/llm_prompts.yaml`:

```yaml
  # SEQUENTIAL: 5-day trajectory analysis (Paper #2)
  sequential_unbiased:
    name: "Sequential Unbiased Prompt (5-day trajectory)"
    description: "5-day GEX sequence analysis without regime labels or hints"

    # Data inclusion flags
    include_regime_label: false
    include_pattern_hints: false
    include_flip_point: true
    include_spot_price: true
    include_gex_magnitude: true
    include_trajectory_summary: false     # DECISION: Raw data only, LLM derives trajectory

    # Temporal settings
    lookback_days: 5
    show_day_labels: true                 # "Day T-4", "Day T-3", etc.
    calculate_gex_velocity: false         # LLM must calculate if needed
    calculate_flip_movement: false        # LLM must calculate if needed

    # Question framing
    question_style: "sequential_neutral"
    null_hypothesis_allowed: true

    # Pattern significance thresholds
    min_gex_magnitude: 5e9                # $5B - Below this, classify as "no_clear_pattern"
    min_confidence: 40                     # Below this, classify as "no_clear_pattern"

    # Time horizon expectations (prevent hedging)
    expected_time_horizons:
      accumulation: "T+1"                  # Pressure releases sharply
      relief: "T+1"                        # Calm materializes immediately
      reversal: "T+1"                      # Regime flip causes spike
      persistent: "T+1 to T+3"             # Continuation plays out over days

    detect_hedging: true                   # Flag mismatched time horizons

    # Response structure
    response_format: "json"
    required_fields:
      - "pattern_detected"                # Boolean
      - "trajectory_type"                 # "accumulation" | "relief" | "reversal" | "persistent" | "no_clear_pattern"
      - "who"                             # If pattern detected
      - "whom"
      - "what"
      - "confidence"                      # 0-100 (0 = no pattern or below threshold)
      - "time_horizon"                    # "T+1" | "T+1 to T+3" (be specific, avoid hedging)
      - "trajectory_reasoning"            # Why this trajectory classification?
```

### Add to `question_templates:`:

```yaml
  sequential_neutral:
    overall_analysis: "Analyze the following 5-day GEX trajectory for {symbol}. Consider how constraints evolve over time, not just the current state."
    individual_windows: |
      SEQUENTIAL ANALYSIS FRAMEWORK:

      1. TRAJECTORY IDENTIFICATION:
         - Is net GEX magnitude increasing, decreasing, or stable?
         - Is the flip point moving (drifting up/down/stable)?
         - Is price moving relative to GEX levels?

      2. CONSTRAINT EVOLUTION:
         - Are dealer hedging pressures BUILDING (accumulation)?
         - Are they RELEASING (relief)?
         - Is there a REGIME CHANGE (reversal)?
         - Are they SUSTAINED (persistent)?

      3. PATTERN DETECTION:
         - Do you detect dealer constraint mechanics? YES/NO
         - If YES: WHO is forcing WHOM to do WHAT?
         - How does the TRAJECTORY affect confidence/timeframe?

      4. PREDICTION:
         - Based on 5-day trajectory, predict Day T+1 behavior
         - Time horizon: Choose ONE based on pattern mechanism:
           * T+1: Immediate next-day effect (use for sharp releases, reversals)
           * T+1 to T+3: Multi-day effect (use ONLY if accumulation builds over time)
           * Be specific - do not default to multi-day if unsure
         - Confidence: 0 if no pattern, 1-100 if pattern detected
```

---

## Example Prompt (What LLM Sees)

```
You are analyzing dealer hedging constraints for INDEX_1 over a 5-day period.

SEQUENTIAL GEX DATA (Day T-4 to Day T+0):

Day T-4:
- Net GEX: -$2.1B
- Flip Point: $545.00
- Spot Price: $548.10

Day T-3:
- Net GEX: -$3.2B
- Flip Point: $546.00
- Spot Price: $550.00

Day T-2:
- Net GEX: -$4.1B
- Flip Point: $547.00
- Spot Price: $551.00

Day T-1:
- Net GEX: -$4.8B
- Flip Point: $547.00
- Spot Price: $551.50

Day T+0 (TODAY):
- Net GEX: -$5.2B
- Flip Point: $548.00
- Spot Price: $552.00

SEQUENTIAL ANALYSIS FRAMEWORK:

1. TRAJECTORY IDENTIFICATION:
   - Is net GEX magnitude increasing, decreasing, or stable?
   - Is the flip point moving (drifting up/down/stable)?
   - Is price moving relative to GEX levels?

2. CONSTRAINT EVOLUTION:
   - Are dealer hedging pressures BUILDING (accumulation)?
   - Are they RELEASING (relief)?
   - Is there a REGIME CHANGE (reversal)?
   - Are they SUSTAINED (persistent)?

3. PATTERN DETECTION:
   - Do you detect dealer constraint mechanics? YES/NO
   - If YES: WHO is forcing WHOM to do WHAT?
   - How does the TRAJECTORY affect confidence/timeframe?

4. PREDICTION:
   - Based on 5-day trajectory, predict Day T+1 behavior
   - Time horizon: Just T+1, or extended (T+1 to T+3)?
   - Confidence: 0 if no pattern, 1-100 if pattern detected

Respond in JSON format:
{
  "pattern_detected": true/false,
  "trajectory_type": "accumulation" | "relief" | "reversal" | "persistent" | "no_clear_pattern",
  "who": "...",
  "whom": "...",
  "what": "...",
  "confidence": 0-100,
  "time_horizon": "T+1" | "T+1 to T+3",
  "trajectory_reasoning": "Why this trajectory classification?"
}

Note: Classify as "no_clear_pattern" if:
- Mean GEX magnitude < $5B (too small to create meaningful constraints)
- Confidence < 40 (pattern unclear or ambiguous)
- No pattern meets detection criteria
```

---

## Verification Thresholds - APPROVED ✅

### Quartile-Based Outcome Verification

**Empirical Distribution** (from SPY 2024 historical data):
```python
thresholds = {
    'accumulation': 0.86%,  # P75 - Top quartile realized vol
    'relief':       0.22%,  # P25 - Bottom quartile realized vol
    'reversal':     1.32%,  # P90 - Top decile realized vol
    'persistent':   0.48%,  # P50 - Median realized vol
}
```

### Verification Logic with Time Horizon Matching

```python
def verify_trajectory(predicted_type, time_horizon, forward_data):
    """
    Verify if predicted trajectory matches realized outcome.

    Args:
        predicted_type: "accumulation" | "relief" | "reversal" | "persistent"
        time_horizon: "T+1" | "T+1 to T+3"
        forward_data: Dict with {
            'forward_1d_vol': float,     # T+1 realized volatility
            'forward_3d_max': float,      # T+1 to T+3 max range
            'forward_3d_avg': float       # T+1 to T+3 avg volatility
        }

    Returns:
        bool: True if prediction verified
    """
    # Select metric based on time horizon
    if time_horizon == "T+1":
        metric = forward_data['forward_1d_vol']
    elif time_horizon == "T+1 to T+3":
        metric = forward_data['forward_3d_max']  # Use max range for multi-day
    else:
        raise ValueError(f"Invalid time_horizon: {time_horizon}")

    # Verify against pattern-specific thresholds
    if predicted_type == 'accumulation':
        # Pressure building → expect high vol when released
        threshold = 0.86 if time_horizon == "T+1" else 1.48  # P75 for T+1, T+3
        return metric > threshold

    elif predicted_type == 'relief':
        # Pressure easing → expect low vol
        threshold = 0.22 if time_horizon == "T+1" else 0.44  # P25 for T+1, T+3
        return metric < threshold

    elif predicted_type == 'reversal':
        # Regime change → expect extreme vol
        threshold = 1.32 if time_horizon == "T+1" else 2.32  # P90 for T+1, T+3
        return metric > threshold

    elif predicted_type == 'persistent':
        # Sustained constraint → expect moderate vol
        if time_horizon == "T+1":
            return 0.38 < metric < 0.58  # P50 ± 20%
        else:  # T+1 to T+3
            return 0.70 < metric < 1.06  # P50 ± 20% for T+3
```

### Expected Time Horizon by Pattern Type

**To discourage hedging, document expected time horizons:**

```python
EXPECTED_TIME_HORIZONS = {
    'accumulation': 'T+1',        # Pressure releases sharply next day
    'relief': 'T+1',               # Calm materializes immediately
    'reversal': 'T+1',             # Regime flip causes immediate spike
    'persistent': 'T+1 to T+3'     # Continuation plays out over multiple days
}
```

**Hedging Detection Logic:**

```python
def detect_hedging(predicted_type, time_horizon):
    """
    Flag potential hedging behavior.

    Returns:
        (is_hedging: bool, reason: str)
    """
    expected = EXPECTED_TIME_HORIZONS[predicted_type]

    # Flag if LLM picks multi-day for patterns that should be immediate
    if expected == 'T+1' and time_horizon == 'T+1 to T+3':
        return (True, f"{predicted_type} typically manifests T+1, not multi-day")

    # Flag if LLM picks immediate for persistent patterns
    if expected == 'T+1 to T+3' and time_horizon == 'T+1':
        return (True, f"{predicted_type} typically extends beyond T+1")

    return (False, "Time horizon matches expected pattern behavior")
```

**Why This Matters:**
- ✅ **Prevents hedging abuse** - LLM can't say "T+1 to T+3" for everything
- ✅ **Tests understanding** - Different patterns have different timeframes
- ✅ **Enables analysis** - Can report hedging rate (% of predictions with mismatched horizon)

**Expected Distribution (if LLM understands mechanics):**
- 75% predictions use expected time horizon
- 15% justifiable exceptions (e.g., "accumulation extreme, expect T+1 to T+3")
- 10% hedging/unclear cases

**Rationale**:
- ✅ Data-driven (empirical distribution from SPY 2024)
- ✅ Conservative (quartiles, not extremes)
- ✅ Testable (binomial tests for statistical significance)
- ✅ Defensible (not arbitrary thresholds)

---

## Implementation Checklist

### 1. Configuration (Day 1)
- [ ] Add `sequential_unbiased` template to `llm_prompts.yaml`
- [ ] Add `sequential_neutral` question template
- [ ] Add trajectory calculation settings

### 2. Prompt Builder Extension (Day 2)
- [ ] Extend `MechanicsPromptBuilder` with `build_sequential_prompt()`
- [ ] Implement 5-day data formatting
- [ ] Implement trajectory summary calculation
- [ ] Add day label obfuscation ("Day T-4", etc.)

### 3. Validation Script (Day 3)
- [ ] Create `validate_sequential_patterns.py`
- [ ] Implement 5-day window sliding logic
- [ ] Query GEX database for lookback windows
- [ ] Format and send to LLM
- [ ] Parse trajectory-specific responses

### 4. Outcome Verification (Day 4)
- [ ] Create `SequentialOutcomeVerifier` class
- [ ] Calculate empirical threshold distribution
- [ ] Implement trajectory-specific verification logic
- [ ] Generate comparison tables (single-day vs sequential)

### 5. Analysis (Day 5)
- [ ] Compare detection rates (71.5% baseline vs sequential)
- [ ] Compare accuracy (91.2% baseline vs sequential)
- [ ] Analyze confidence by trajectory type
- [ ] Generate decision point report (proceed to Phase 2?)

---

## Success Metrics (Phase 1 - 2024 Baseline)

### Proceed to Phase 2 IF:
- Accuracy improves by ≥2pp (91.2% → 93.2%+), OR
- Confidence increases on persistent patterns (72% → 85%+), OR
- False positives decrease significantly

### Stop at Phase 1 IF:
- Accuracy same or worse (≤91.2%)
- No meaningful improvement in any metric
- Added complexity not justified

---

## Files to Create

```
config_defaults/
└── llm_prompts.yaml                     # Add sequential_unbiased template

src/llm/
└── mechanics_prompt_builder.py          # Add build_sequential_prompt()

scripts/validation/
├── validate_sequential_patterns.py      # NEW - main validation script
└── verify_sequential_outcomes.py        # NEW - outcome verification

docs/papers/paper2/
├── sequential_prompt_design.md          # THIS FILE
└── sequential_results_comparison.md     # To be created after validation

reports/validation/sequential_2024/
└── (validation results will go here)
```

---

## Related Issues

- **#89**: Sequential GEX Analysis (5-Day Lookback) - defines methodology
- **#107**: Paper #2 Sequential GEX Validation Strategy - defines phased approach
- **#104**: Multi-Year GEX Database Structure - enables Phase 2 extension

---

**Date**: November 1, 2025
**Status**: Design approved, ready for implementation
**Next Step**: Implement configuration and prompt builder (Day 1-2)
