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

## Phase 2: Negative Controls

### Purpose
Validate LLM doesn't hallucinate regimes in non-regime data.

### Dependencies
**Requires Phase 1 completion** - Need baseline detection rate before testing false positives.

### Three Sub-Phases

---

### Phase 2a: Shuffled Windows

**Question**: Does LLM detect false regimes in randomized data?

**Method**:
1. Take real 30-day GEX sequences from Q1 2024
2. Randomly shuffle day order (destroys temporal structure)
3. Present shuffled sequence to LLM with obfuscation
4. Count false positive detections

**Sampling**: Every 5-10 days (efficiency)
- Window 1 (Jan 30): Shuffle days 1-30 → Present as Day T-29 to T+0
- Window 6 (Feb 6): Shuffle days 7-36 → Present as Day T-29 to T+0
- Window 11 (Feb 13): Shuffle days 12-41 → Present as Day T-29 to T+0
- ...
- ~10 shuffled windows total

**Expected Results**:
- **Detection rate**: 0% (ideal) or <10% (acceptable threshold)
- **Regime type**: Should be "transitional" (sign flips from shuffling)

**Pass Criteria**: <10% false positive rate

**If fails (>10% detection)**:
- Action: Recalibrate confidence thresholds
- Action: Strengthen sign flip penalty in prompt
- Action: Add "consistency check" to prompt (are flips random or structured?)

---

### Phase 2b: Transitional Periods

**Question**: Does LLM correctly reject windows with frequent sign flips?

**Method**:
1. Find real windows with high sign flip count (7-10 flips)
2. May be rare in Q1 2024 (persistent negative regime)
3. Option A: Hand-pick from full 2024 dataset
4. Option B: Create synthetic by splicing positive/negative days

**Sampling**: Hand-pick or sample every 5-10 days (~10 windows)

**Characteristics**:
- Sign persistence: 50-65% (15-20 days same sign)
- Sign flips: 7-10 flips
- Magnitude: May be adequate (>$5B) but direction unstable

**Expected Results**:
- **Detection rate**: 0-10% (should reject as "transitional")
- **LLM reasoning**: Should cite "too many sign flips" or "no persistent direction"

**Pass Criteria**: <10% detection rate

**If fails (>10% detection)**:
- Action: Lower max sign flip threshold from 5 to 3
- Action: Strengthen "stability" requirement in prompt

---

### Phase 2c: Low-Magnitude Persistent

**Question**: Does LLM correctly reject persistent-sign but weak-magnitude windows?

**Method**:
1. Take real persistent window (e.g., 26/30 days negative, $8B avg)
2. Scale GEX values down: multiply by 0.3 → now $2.4B avg
3. Present scaled window to LLM
4. Should reject as "low_conviction" despite sign persistence

**Sampling**: Hand-pick or sample every 5-10 days (~10 windows)

**Characteristics**:
- Sign persistence: 70-90% (21-27 days same sign) ✅
- Sign flips: 0-3 (very stable) ✅
- Magnitude: <$3B average ❌

**Expected Results**:
- **Detection rate**: 0-10% (should reject as "low_conviction")
- **LLM reasoning**: Should cite "magnitude below $5B threshold"

**Pass Criteria**: <10% detection rate

**If fails (>10% detection)**:
- Action: Increase magnitude threshold from $5B to $7B
- Action: Add "minimum constraint strength" language to prompt

---

### Phase 2 Summary Output

**File**: `reports/validation/regime_windows/phase2_negative_controls.yaml`

**Structure**:
```yaml
validation_metadata:
  phase: "Phase 2 - Negative Controls"
  baseline_detection: <Phase 1 detection rate>
  false_positive_threshold: "10%"

phase2a_shuffled:
  windows_tested: 10
  detection_rate_pct: <value>
  pass: true/false
  examples:
    - window_id: 1
      shuffled_from: "2024-01-30"
      llm_classification: "transitional"
      false_positive: false
    # ...

phase2b_transitional:
  windows_tested: 10
  detection_rate_pct: <value>
  pass: true/false
  # ...

phase2c_low_magnitude:
  windows_tested: 10
  detection_rate_pct: <value>
  pass: true/false
  # ...

overall_result:
  all_controls_pass: true/false
  action_required: "none|recalibrate|revise_prompt"
```

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
