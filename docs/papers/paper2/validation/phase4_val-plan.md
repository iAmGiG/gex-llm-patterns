# Phase 4: Multi-Year Regime Validation Plan

**Created**: November 20, 2025
**Status**: Ready to Execute (Phases 1-3 Complete)
**Timeline**: 1 week per phase (4A, 4B)
**Estimated Cost**: ~$1.50 total (Batch API, 50% discount)

---

## Executive Summary

With 6 years of historical GEX data collected (2020-2025, 1,475 trading days), Phase 4 validates regime persistence evolution using LLM detection across the full dataset.

**Goal**: Quantify when 0DTE proliferation drove regime persistence increase

**Phases**:

- **Phase 4A**: Single GEX validation (traditional GEX_OI methodology) - ~$0.73
- **Phase 4B**: Dual GEX validation (GEX_OI vs GEX_Volume divergence) - OPTIONAL, ~$0.73

---

## Phase 4A: Single GEX Validation

### Objective

Validate regime detection across all 6 years using **traditional single GEX methodology** (GEX_OI only), comparable to original 2020 vs 2024 baseline.

### Scope

**Windows to Validate**:

| Year | Trading Days | Windows | Expected Detection |
|------|-------------|---------|-------------------|
| 2020 | 252 | ~223 | 12.1% (baseline) |
| 2021 | 250 | ~221 | 15-25% (early 0DTE) |
| 2022 | 251 | ~222 | 30-50% (SPX 0DTE launch) |
| 2023 | 250 | ~221 | 60-75% (volume expansion) |
| 2024 | 251 | ~222 | 81.2% (baseline) |
| 2025 | 221 | ~192 | 75-85% (sustained) |
| **TOTAL** | **1,475** | **~1,301** | **Temporal trend** |

**Note**: Windows = Trading days - 29 (30-day lookback required)

---

### Tools & Infrastructure

#### 1. Batch Regime Validator

**File**: `src/validation/batch_regime_validator.py`

**Key Methods**:

```python
BatchRegimeValidator():
    prepare_batch_file(windows)       # Generate JSONL
    submit_batch(file, description)   # Submit to OpenAI
    poll_batch(batch_id, interval)    # Wait for completion
    retrieve_results(batch_id)        # Download results
    save_results_yaml(results, file)  # Convert to YAML
```

**Features**:

- OpenAI Batch API integration (50% cost savings)
- Async processing (1-2 hours, non-blocking)
- Automatic retry logic for failed requests
- YAML output format for analysis

#### 2. CLI Wrapper

**File**: `scripts/validation/validate_regime_windows_batch.py`

**Usage**:

```bash
# Submit batch for year
python scripts/validation/validate_regime_windows_batch.py \
  --start-date 2021-01-01 \
  --end-date 2021-12-31 \
  --submit \
  --description "Phase 4A: 2021 Single GEX"

# Poll for completion
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id batch_XXXXX \
  --poll \
  --poll-interval 60

# Retrieve results
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id batch_XXXXX \
  --retrieve \
  --output-file reports/validation/paper2_regime_windows/phase4a_2021_single_gex.yaml
```

#### 3. Regime Detection Prompt

**File**: `docs/papers/paper2/prompts/regime_detection_v1.md`

**Criteria** (same as Phases 1-4 baseline):

- **Persistence**: ≥70% days same sign
- **Magnitude**: ≥$5B average absolute GEX
- **Stability**: ≤5 sign flips over 30 days

**Model**: `o4-mini` (consistency with baseline)
**Temperature**: 0.7
**Max tokens**: 500

---

### Technical Input

#### Database Schema

**Table**: `daily_gex_metrics`
**Key Fields**:

```sql
SELECT
    symbol,
    date,
    net_gex,                 -- Single GEX (OI-based)
    gex_oi,                  -- OI component
    gex_volume,              -- Volume component
    economic_regime,         -- Regime classification
    created_at
FROM daily_gex_metrics
WHERE symbol = 'SPY'
  AND date >= '2021-01-01'
  AND date <= '2021-12-31'
ORDER BY date
```

#### Window Generation

**Logic**:

```python
# For each year, generate 30-day windows
for end_date in trading_days[29:]:  # Skip first 29 days
    start_date = end_date - timedelta(days=29)
    window = {
        'window_id': f'window-{end_date}',
        'start_date': start_date,
        'end_date': end_date,
        'gex_sequence': get_gex_sequence(start_date, end_date)
    }
    windows.append(window)
```

**Window Example** (2021-01-30):

```yaml
window_id: window-2021-01-30
start_date: 2021-01-02  # Day T-29
end_date: 2021-01-30    # Day T+0
gex_sequence:
  - Day T-29: $-24.5B
  - Day T-28: $-26.3B
  ...
  - Day T+0: $-28.7B
```

#### Prompt Construction

**Template**:

```
You are a market mechanics analyst...

Analyze this 30-day GEX sequence for persistent regime:

Day T-29: $-24.5B
Day T-28: $-26.3B
...
Day T+0: $-28.7B

Evaluate:
1. Persistence (≥70% same sign)
2. Magnitude (≥$5B average)
3. Stability (≤5 sign flips)

Return JSON:
{
    "regime_type": "persistent_negative" | "persistent_positive" | "transitional",
    "regime_detected": true | false,
    "confidence": 0-100,
    "reasoning": "..."
}
```

---

### Expected Output

#### Per-Window Results

**File Format**: YAML
**Location**: `reports/validation/paper2_regime_windows/phase4a_{year}_single_gex.yaml`

**Structure**:

```yaml
metadata:
  year: 2021
  total_windows: 221
  model: o4-mini
  batch_id: batch_XXXXX
  submitted_at: "2025-11-21T00:00:00Z"
  completed_at: "2025-11-21T02:15:00Z"

windows:
  - window_id: window-2021-01-30
    regime_type: persistent_negative
    regime_detected: true
    confidence: 85
    reasoning: "28/30 days negative (93.3%), avg $26.1B, 2 flips"
    metrics:
      persistence_pct: 93.3
      avg_magnitude: 26.1B
      sign_flips: 2

  - window_id: window-2021-01-31
    regime_type: transitional
    regime_detected: false
    confidence: 45
    reasoning: "15/30 days negative (50%), avg $3.2B, 8 flips"
    metrics:
      persistence_pct: 50.0
      avg_magnitude: 3.2B
      sign_flips: 8

summary:
  total_windows: 221
  detected: 45
  detection_rate: 20.4%
  avg_confidence: 72.3
  avg_persistence: 81.2%
  avg_magnitude: $18.7B
```

#### Aggregated Results

**File**: `reports/validation/paper2_regime_windows/phase4a_summary.yaml`

**Structure**:

```yaml
phase4a_single_gex_summary:
  total_windows: 1301
  model: o4-mini

  by_year:
    - year: 2020
      windows: 223
      detected: 27
      detection_rate: 12.1%
      avg_confidence: 68.5
      avg_magnitude: $15.2B

    - year: 2021
      windows: 221
      detected: 45
      detection_rate: 20.4%
      avg_confidence: 72.3
      avg_magnitude: $18.7B

    - year: 2022
      windows: 222
      detected: 89
      detection_rate: 40.1%
      avg_confidence: 76.8
      avg_magnitude: $22.1B

    - year: 2023
      windows: 221
      detected: 165
      detection_rate: 74.7%
      avg_confidence: 82.1
      avg_magnitude: $28.3B

    - year: 2024
      windows: 222
      detected: 180
      detection_rate: 81.1%
      avg_confidence: 85.7
      avg_magnitude: $32.5B

    - year: 2025
      windows: 192
      detected: 158
      detection_rate: 82.3%
      avg_confidence: 86.2
      avg_magnitude: $31.8B

  temporal_trend:
    slope: +11.7pp per year
    r_squared: 0.94
    p_value: 0.002
```

---

### Metrics to Track

#### 1. Detection Rate (Primary)

**Definition**: % of windows where `regime_detected = true`

**Target Ranges** (hypothesized):

- 2020: 10-15% (pre-0DTE baseline)
- 2021: 15-25% (early 0DTE growth)
- 2022: 30-50% (SPX 0DTE launch May 2022)
- 2023: 60-75% (volume expansion ~30% by year end)
- 2024: 80-85% (validated baseline)
- 2025: 75-85% (sustained or reverting?)

**Statistical Test**: Chi-square test across years (H0: no difference)

#### 2. Average Confidence

**Definition**: Mean confidence score for detected regimes

**Interpretation**:

- <60: Low confidence (borderline cases)
- 60-80: Moderate confidence
- >80: High confidence (clear regimes)

**Expected**: Increasing trend 2020→2024 (clearer regimes over time)

#### 3. Persistence Percentage

**Definition**: Mean % of days with same sign within detected windows

**Target**: ≥70% (regime criterion)

**Expected**: Stable across years (criterion enforced)

#### 4. Average Magnitude

**Definition**: Mean absolute GEX across detected windows

**Expected**: Increasing trend 2020→2024 (0DTE drives larger exposures)

#### 5. Sign Flip Rate

**Definition**: Mean number of sign changes within detected windows

**Target**: ≤5 flips (stability criterion)

**Expected**: Decreasing trend 2020→2024 (more stable regimes)

#### 6. Regime Type Distribution

**Categories**:

- **Persistent Negative**: 70%+ days negative
- **Persistent Positive**: 70%+ days positive
- **Transitional**: Neither (should be rejected)

**Expected**:

- 2020-2022: Mix of negative/positive
- 2023-2025: Dominated by persistent negative (0DTE vol expansion)

---

### Workflow

#### Step 1: Generate Windows (per year)

```bash
# Example for 2021
python scripts/validation/generate_regime_windows.py \
  --year 2021 \
  --output /tmp/phase4a_2021_windows.json

# Output: 221 windows for 2021
```

#### Step 2: Submit Batch

```bash
python scripts/validation/validate_regime_windows_batch.py \
  --windows-file /tmp/phase4a_2021_windows.json \
  --submit \
  --description "Phase 4A: 2021 Single GEX"

# Output: Batch ID (save for later)
```

#### Step 3: Poll for Completion (1-2 hours)

```bash
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id batch_XXXXX \
  --poll \
  --poll-interval 60

# Terminal free during this time
```

#### Step 4: Retrieve Results

```bash
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id batch_XXXXX \
  --retrieve \
  --output-file reports/validation/paper2_regime_windows/phase4a_2021_single_gex.yaml
```

#### Step 5: Repeat for All Years

- Sequentially process 2021, 2022, 2023, 2025
- 2020 and 2024 already validated (baseline)
- Total: 4 batch submissions

#### Step 6: Aggregate Results

```bash
python scripts/validation/aggregate_phase4a_results.py \
  --input-dir reports/validation/paper2_regime_windows/ \
  --output reports/validation/paper2_regime_windows/phase4a_summary.yaml
```

---

### Timeline

**Total Duration**: 1 week (async, non-blocking)

| Day | Task | Duration |
|-----|------|----------|
| **Day 1** | Generate windows (2021, 2022) | 1 hour |
| **Day 1** | Submit 2021 batch | 5 min |
| **Day 1-2** | Wait for 2021 completion | 1-2 hours |
| **Day 2** | Retrieve 2021 results | 5 min |
| **Day 2** | Submit 2022 batch | 5 min |
| **Day 2-3** | Wait for 2022 completion | 1-2 hours |
| **Day 3** | Retrieve 2022 results | 5 min |
| **Day 3** | Generate windows (2023, 2025) | 1 hour |
| **Day 3** | Submit 2023 batch | 5 min |
| **Day 3-4** | Wait for 2023 completion | 1-2 hours |
| **Day 4** | Retrieve 2023 results | 5 min |
| **Day 4** | Submit 2025 batch | 5 min |
| **Day 4-5** | Wait for 2025 completion | 1-2 hours |
| **Day 5** | Retrieve 2025 results | 5 min |
| **Day 5-7** | Aggregate and analyze | 2 days |

**Active Work**: ~4 hours (window generation + submission)
**Passive Wait**: ~6-8 hours (Batch API processing, terminal free)

---

## Phase 4B: Dual GEX Validation (OPTIONAL)

### Objective

Validate regime detection using **dual GEX methodology** (GEX_OI vs GEX_Volume divergence) to identify high-conviction vs low-conviction regimes.

### Additional Criteria

Beyond Phase 4A's single GEX criteria:

**Activity Ratio** = |GEX_Volume| / |GEX_OI|

**Regime Quality**:

1. **High Conviction**: Activity ratio > 0.70 (OI and Volume agree)
2. **Low Conviction**: Activity ratio < 0.70 (OI dominates, Volume weak)
3. **Divergence Signal**: OI negative, Volume positive (mixed)

**Hypothesis**: High-conviction regimes should show stronger persistence and higher detection rates

### Scope

**Same windows as Phase 4A**: ~856 windows (2021-2023, 2025)

**Timeline**: +1 week (after Phase 4A completion)

### Expected Output

**Additional Fields**:

```yaml
windows:
  - window_id: window-2021-01-30
    regime_type: persistent_negative
    regime_detected: true
    regime_quality: high_conviction  # NEW
    activity_ratio: 0.85             # NEW
    oi_volume_agreement: true        # NEW
    confidence: 90                   # Higher for high-conviction
    reasoning: "OI=$-26.1B, Volume=$-22.2B (85% agreement)"
```

### Decision Point

**Run Phase 4B if**:

- Time permits (Dec 2025 deadline comfortable)
- Budget available (~$37)
- Phase 4A shows interesting patterns worth deeper exploration

**Defer Phase 4B if**:

- Time constrained (Paper #2 deadline approaching)
- Budget tight (prioritize Phase 4A + analysis)
- Phase 4A sufficient for paper narrative

---

## Success Criteria

### Phase 4A (Required)

- [ ] All 4 new years validated (2021, 2022, 2023, 2025) - ~856 windows
- [ ] Results match expected temporal trend (2020 low → 2024 high)
- [ ] Detection rates show statistical significance across years (p < 0.05)
- [ ] Transition period identified (e.g., 2022 Q2/Q3)

### Phase 4B (Optional)

- [ ] Dual GEX validation complete for all years
- [ ] Activity ratio insights generated
- [ ] High-conviction vs low-conviction comparison
- [ ] Divergence patterns identified

---

## Files Generated

### Scripts

- `scripts/validation/generate_regime_windows.py` (window generation)
- `scripts/validation/validate_regime_windows_batch.py` (existing, CLI wrapper)
- `scripts/validation/aggregate_phase4a_results.py` (aggregation)

### Results

- `reports/validation/paper2_regime_windows/phase4a_2021_single_gex.yaml`
- `reports/validation/paper2_regime_windows/phase4a_2022_single_gex.yaml`
- `reports/validation/paper2_regime_windows/phase4a_2023_single_gex.yaml`
- `reports/validation/paper2_regime_windows/phase4a_2025_single_gex.yaml`
- `reports/validation/paper2_regime_windows/phase4a_summary.yaml`
- `reports/validation/paper2_regime_windows/phase4b_summary.yaml` (if run)

### Documentation

- `docs/papers/paper2/validation/phase4_val-plan.md` (this file)
- `docs/papers/paper2/validation/phase4_val-results.md` (after completion)

---

## References

- **Batch API Guide**: docs/papers/paper2/guides/batch_api_guide.md
- **Regime Detection Prompt**: docs/papers/paper2/prompts/regime_detection_v1.md
- **Phase 1-4 Baseline Results**: docs/papers/paper2/validation_complete_summary.md
- **Database Schema**: src/data_sources/historical_gex_builder.py:344-347
- **Multi-Year Roadmap**: docs/papers/paper2/planning/phase2-5_roadmap.md

---

## Next Steps

1. ✅ **Confirm Phases 1-3 complete** (database ready)
2. 🔄 **Generate windows for 2021** (first year to validate)
3. 🔄 **Submit Phase 4A: 2021 batch**
4. ⏳ **Wait for completion** (1-2 hours, terminal free)
5. 🔄 **Repeat for 2022, 2023, 2025**
6. 🔄 **Aggregate results and analyze temporal trend**
7. 📊 **Generate figures for Paper #2**

**Ready to start**: November 21, 2025
**Target completion**: December 4, 2025 (2 weeks)

---

**Prepared by**: Chat A
**Date**: November 20, 2025
