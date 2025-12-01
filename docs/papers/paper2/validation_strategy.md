# Paper #2: Validation Phases - 30-Day Regime Detection

**Created**: November 6, 2025
**Purpose**: Phased validation strategy for regime window testing
**Related**: [regime_windows_design.md](../methodology/regime_windows_design.md), [regime_detection_v1.md](../prompts/regime_detection_v1.md)

---

## Overview

**Goal**: Validate LLM can identify persistent market regimes with **30-50% detection rate** (selective, not universal like 5-day's 98-100%).

**Four-Phase Approach**:

1. **Phase 1**: Positive validation (Q1 2024) - establish baseline detection rate
2. **Phase 2**: Negative controls (shuffled, transitional, low-mag) - validate selectivity
3. **Phase 3**: Full 2024 validation - comprehensive regime analysis
4. **Phase 4**: 2020 comparison - test 0DTE proliferation hypothesis

---

## Phase 1: Positive Validation (Q1 2024)

### Purpose

Establish baseline detection rate on real data with known regime characteristics.

### Dataset

- **Period**: Q1 2024 (January 2 - March 29, 2024)
- **Trading days**: 61 days
- **Potential windows**: 32 windows (days 30-61 can serve as window ends)
- **Known characteristics**: Strong persistent negative GEX (0DTE proliferation)

### Sampling Strategy

**Test every day as window end** (N=1, maximum coverage)

**Why every day?**

- See regime evolution: When does regime start/end?
- Validate stability: Persistent regimes should appear in multiple overlapping windows
- Maximum signal: Need full coverage to catch all potential regimes

**Window Overlap**:

- Window 1: Jan 2 - Jan 30 (days 1-30)
- Window 2: Jan 3 - Jan 31 (days 2-31)
- Window 3: Jan 4 - Feb 1 (days 3-32)
- ...
- 29-day overlap between consecutive windows (this is intentional)

### Expected Results

- **Detection rate**: 3-6% (1-2 persistent regimes detected out of 32 windows)
- **Accuracy rate**: 70-80% (LLM vs deterministic classifier agreement)
- **Regime type**: Mostly persistent_negative (Q1 had strong negative GEX)

### Metrics Tracked

1. **Detection Rate**: `regime_detected=true` / total windows
2. **Accuracy Rate**: LLM classification matches deterministic classification
3. **Confidence Calibration**: Distribution of 90-100 vs 70-89 vs 50-69 vs <50
4. **Regime Type Distribution**: persistent_positive, persistent_negative, transitional, low_conviction

### Obfuscation

**✅ REQUIRED** - Critical for Paper #1 methodology validation

**Format**: Day T-29, T-28, ..., T-1, T+0

**Why critical**: LLM knows "Q1 2024 had strong negative GEX from 0DTE explosion." Without obfuscation, LLM cheats using temporal knowledge instead of structural analysis.

### Outcomes (Forward Returns)

**Skip for Phase 1** - Focus on classification accuracy

**Rationale**: Need to validate regime detection first before testing if regimes predict future volatility.

### Timeline

**Estimated duration**: ~1 hour (32 LLM calls at ~2 min each)

### Output

**File**: `reports/validation/regime_windows/phase1_q1_2024.yaml`

**Structure**:

```yaml
validation_metadata:
  phase: "Phase 1 - Positive Validation"
  dataset: "Q1 2024 (61 trading days)"
  windows_tested: 32
  sampling_strategy: "Every day (N=1)"
  obfuscation: true
  date_range: "2024-01-02 to 2024-03-29"

summary_statistics:
  detection_rate_pct: <value>
  accuracy_rate_pct: <value>
  regimes_detected: <count>
  regime_types:
    persistent_positive: <count>
    persistent_negative: <count>
    transitional: <count>
    low_conviction: <count>

windows:
  - window_id: 1
    end_date: "2024-01-30"
    date_range: "2024-01-02 to 2024-01-30"
    deterministic_classification:
      regime_type: "persistent_negative"
      metrics:
        positive_days: 4
        negative_days: 26
        persistence_pct: 86.7
        avg_magnitude: 8.5e9
        sign_flips: 3
    llm_classification:
      regime_detected: true
      regime_type: "persistent_negative"
      confidence: 85
      reasoning: "..."
    agreement: true
    accuracy: "correct"
  # ... 31 more windows
```

### Success Criteria

1. **Detection rate**: 3-10% (1-3 regimes detected)
   - Too low (<3%): Thresholds too strict
   - Too high (>10%): Thresholds too loose
2. **Accuracy rate**: ≥70% (LLM agrees with deterministic)
3. **Confidence calibration**: High confidence (80-100) aligns with correct classifications
4. **No contradictions**: Overlapping windows show consistent regime detection

### Decision Points

**If detection rate 3-10% and accuracy ≥70%**:

- ✅ Proceed to Phase 2 (negative controls)

**If detection rate <3%**:

- ⚠️ Thresholds too strict
- Action: Decrease persistence to 60% (18/30 days) OR magnitude to $3B
- Re-run Phase 1 with adjusted thresholds

**If detection rate >10%**:

- ⚠️ Thresholds too loose
- Action: Increase persistence to 80% (24/30 days) OR magnitude to $7B
- Re-run Phase 1 with adjusted thresholds

**If accuracy rate <60%**:

- ⚠️ Prompt issues
- Action: Revise mechanical guidance, add more examples
- Re-run Phase 1 with improved prompt

---

## Phase 2: Negative Controls ✅ COMPLETE

**Status**: ✅ **COMPLETE** (November 19, 2025)
**Result**: All tests PASS - Framework validated
**Decision**: ✅ PROCEED TO PHASE 3

### Purpose

Validate LLM doesn't hallucinate regimes in non-regime data.

### Dependencies

**Requires Phase 1 completion** - Need baseline detection rate before testing false positives.

### Three Sub-Phases

---

### Phase 2a: Shuffled Windows ✅ COMPLETE

**Question**: Does LLM detect false regimes in randomized data?

**Method**:

1. Take real 30-day GEX sequences
2. Randomly shuffle day order (destroys temporal structure)
3. Present shuffled sequence to LLM with obfuscation
4. Count false positive detections

**Datasets Tested**:

- **Q1 2024**: 54 shuffled windows
- **2020 Full Year**: 223 shuffled windows (comprehensive validation)

**Results**:

- **Q1 2024**: 61.1% FP (extreme persistence - windows averaged 99.2% before shuffle)
- **2020**: 12.1% FP (normal market conditions)
- **5x Difference**: Proves framework discriminates between extreme and normal regimes

**Status**: ✅ **PASS** - Framework validated

- Q1 2024 high FP explained by statistical extremity (not framework failure)
- 2020 normal FP rate confirms selectivity in regular markets
- Selectivity proven by 5x difference between regimes

---

### Phase 2b: Transitional Periods ✅ COMPLETE

**Question**: Does LLM correctly reject windows with frequent sign flips?

**Method**:

1. Take low-flip windows (0-2 flips) as base
2. Artificially invert 7-10 days' signs to create high volatility
3. Present modified sequence to LLM
4. Count false positive detections

**Why Artificial Transformation**: No real windows with ≥7 flips exist in 2020-2024 dataset (max = 4 flips)

**Datasets Tested**:

- **Q1 2024**: 32 high-flip windows
- **2020 Full Year**: 223 high-flip windows

**Results**:

- **Q1 2024**: 0% FP (perfect rejection)
- **2020**: 0% FP (perfect rejection)

**Status**: ✅ **PASS** - Stability criterion (≤5 flips) working perfectly

- 100% rejection rate across both datasets
- LLM reasoning correctly cites excessive sign flips

---

### Phase 2c: Low-Magnitude Persistent ✅ COMPLETE

**Question**: Does LLM correctly reject persistent-sign but weak-magnitude windows?

**Method**:

1. Take persistent windows with adequate magnitude
2. Scale GEX values down 75% (e.g., $12B → $3B)
3. Present scaled window to LLM
4. Count false positive detections

**Datasets Tested**:

- **Q1 2024**: 32 scaled-down windows
- **2020 Full Year**: 223 scaled-down windows

**Results**:

- **Q1 2024**: 0% FP (perfect rejection)
- **2020**: 0% FP (perfect rejection)

**Status**: ✅ **PASS** - Magnitude criterion (≥$5B) working perfectly

- 100% rejection rate across both datasets
- LLM reasoning correctly cites insufficient magnitude

---

### Phase 2 Summary Output ✅ COMPLETE

**Files**: 6 batch result YAML files

- Q1 2024: 3 tests (shuffle, transitional, low-magnitude)
- 2020: 3 tests (shuffle, transitional, low-magnitude)

**Summary Statistics**:

| Test | Q1 2024 | 2020 | Status |
|------|---------|------|--------|
| **Shuffle** | 61.1% (33/54) | 12.1% (27/223) | ✅ PASS (5x difference proves selectivity) |
| **Transitional** | 0% (0/32) | 0% (0/223) | ✅ PASS (perfect rejection) |
| **Low-Magnitude** | 0% (0/32) | 0% (0/223) | ✅ PASS (perfect rejection) |

**Overall Result**:

- ✅ All controls pass validation
- ✅ Framework demonstrates selectivity (5x FP difference)
- ✅ Criteria working correctly (0% FP on transitional and low-magnitude)
- ✅ Action required: **PROCEED TO PHASE 3**

**Total Cost**: $12.12 (809 windows across 6 batches)

**Detailed Analysis**: See [results/phase2_results.md](../results/phase2_results.md)

---

## Phase 3: Full 2024 Validation

### Purpose

Comprehensive regime analysis across full year with validated methodology.

### Dependencies

**Requires Phase 1 + Phase 2 complete** - Thresholds calibrated, false positives controlled.

### Dataset

- **Period**: Full 2024 (252 trading days)
- **Potential windows**: ~223 windows (days 30-252)
- **Characteristics**: 0DTE proliferation year (strong GEX effects)

### Sampling Strategy

**Test every day as window end** (N=1, maximum coverage)

**Why every day?**

- Full regime timeline: See when regimes emerge, persist, transition
- Regime duration analysis: How long do persistent regimes last?
- Transition detection: When do regimes break down?

### Expected Results

- **Detection rate**: 30-50% (4-8 persistent regimes across ~223 windows)
- **Regime duration**: Persistent regimes should span multiple overlapping windows
- **Transitions**: Should see regime_type changes at regime boundaries

### Metrics Tracked

1. **Detection rate**: Overall and by quarter (Q1 vs Q2 vs Q3 vs Q4)
2. **Regime duration**: Average window count per regime
3. **Regime transitions**: How many regime→non-regime boundaries?
4. **Regime type distribution**: Positive vs negative dominance

### Timeline

**Estimated duration**: ~6 hours (223 LLM calls)

### Output

**File**: `reports/validation/regime_windows/phase3_full_2024.yaml`

**Additional Analysis**:

- Regime timeline visualization (which periods had persistent regimes?)
- Quarterly comparison (did regime persistence change across 2024?)
- Transition analysis (what triggers regime breakdown?)

---

## Phase 4: 2020 Comparison (0DTE Hypothesis)

### Purpose

Test if 0DTE option proliferation (2020→2024) increased regime persistence.

### Dependencies

**Requires Phase 3 complete** - Need 2024 baseline for comparison.

### Dataset

- **Period**: Full 2020 (252 trading days)
- **Potential windows**: ~223 windows
- **Characteristics**: Pre-0DTE era (weaker GEX constraints)

### Hypothesis

**H1**: 2024 detection rate > 2020 detection rate
**Rationale**: 0DTE options create stronger, more persistent gamma constraints

### Expected Results

- **Detection rate**: 20-30% (2-4 persistent regimes) - LOWER than 2024
- **Regime duration**: Shorter than 2024 (less stability)
- **Statistical test**: Two-proportion z-test (2024 vs 2020 detection rates)

### Metrics Tracked

1. **Detection rate**: 2020 vs 2024 comparison
2. **Regime duration**: Average windows per regime (2020 vs 2024)
3. **Magnitude comparison**: Average GEX magnitude in detected regimes

### Timeline

**Estimated duration**: ~6 hours (223 LLM calls)

### Output

**File**: `reports/validation/regime_windows/phase4_2020_comparison.yaml`

**Statistical Analysis**:

```yaml
comparison_statistics:
  detection_rate_2020: <pct>
  detection_rate_2024: <pct>
  difference: <pct>
  z_statistic: <value>
  p_value: <value>
  significant: true/false
  conclusion: "0DTE proliferation did/did not increase regime persistence"
```

---

## Summary: Why This Phased Approach?

### Phase 1 (Q1 2024)

**Purpose**: Quick validation, threshold calibration
**Why first**: Small dataset (32 windows), fast results (~1 hour)
**Decision point**: Adjust thresholds before full validation

### Phase 2 (Negative Controls)

**Purpose**: Prove methodology selectivity
**Why after Phase 1**: Need baseline before testing false positives
**Decision point**: Recalibrate if controls fail

### Phase 3 (Full 2024)

**Purpose**: Comprehensive regime analysis
**Why after Phase 2**: Methodology validated, ready for full dataset
**Output**: Primary results for Paper #2

### Phase 4 (2020 Comparison)

**Purpose**: 0DTE hypothesis testing
**Why last**: Comparative analysis requires 2024 baseline
**Output**: Novel finding about 0DTE proliferation effect

---

## Key Differences from Paper #1 (Pattern Taxonomy)

| Aspect | Paper #1 (Pattern) | Paper #2 (Regime) |
|--------|-------------------|-------------------|
| **Window size** | Single day | 30 days |
| **Detection target** | 100% (universal hedging) | 30-50% (selective regimes) |
| **Obfuscation** | Day T+0 | Days T-29 to T+0 |
| **Metrics** | Detection + Accuracy | Detection + Accuracy + Duration |
| **Negative controls** | Tests 1-3 (5-day approach) | Phase 2a-c (30-day approach) |
| **Sampling** | Every day (181 days Q1+Q3+Q4) | Every day (223 windows full year) |
| **Outcome calc** | Forward returns (trading) | Skip Phase 1 (research focus) |

---

## Implementation Checklist

### Phase 1

- [ ] Create `validate_regime_windows.py`
- [ ] Add `build_regime_prompt()` to `MechanicsPromptBuilder`
- [ ] Run Q1 2024 validation (32 windows)
- [ ] Analyze results: detection rate, accuracy rate
- [ ] Decision: Proceed to Phase 2 or recalibrate

### Phase 2

- [ ] Create `generate_shuffled_windows.py` (Chat B)
- [ ] Create `generate_transitional_windows.py` (Chat B)
- [ ] Create `generate_low_magnitude_windows.py` (Chat B)
- [ ] Run Phase 2a: Shuffled (10 windows)
- [ ] Run Phase 2b: Transitional (10 windows)
- [ ] Run Phase 2c: Low-magnitude (10 windows)
- [ ] Decision: Proceed to Phase 3 or recalibrate

### Phase 3

- [ ] Run full 2024 validation (223 windows)
- [ ] Analyze regime timeline (when do regimes occur?)
- [ ] Analyze regime duration (how long do they last?)
- [ ] Quarterly comparison (Q1 vs Q2 vs Q3 vs Q4)

### Phase 4

- [ ] Run 2020 validation (223 windows)
- [ ] Statistical comparison (2020 vs 2024)
- [ ] 0DTE hypothesis test (detection rate difference)
- [ ] Results write-up for Paper #2

---

**Status**: Phase 1 implementation starting (Nov 6, 2025)
**Next**: Chat A creates `validate_regime_windows.py`
**Timeline**: Phases 1-4 completion by end of November 2025
