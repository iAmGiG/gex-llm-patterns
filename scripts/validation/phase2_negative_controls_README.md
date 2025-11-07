# Phase 2: Negative Controls for Regime Detection

**Status**: Implementation complete (Nov 6, 2025)
**Related**: [validation_phases.md](../../docs/papers/paper2/validation/validation_phases.md)

---

## Overview

Phase 2 validates that the LLM regime detection methodology doesn't produce false positives in structured negative control scenarios.

### Three Sub-Phases

| Phase | Purpose | Method | Windows | Expected FP Rate |
|-------|---------|--------|---------|------------------|
| **2a** | Random data | Shuffle GEX days | ~10 | <10% |
| **2b** | Unstable direction | High sign flips | ~10 | <10% |
| **2c** | Weak constraint | Low magnitude | ~10 | <10% |

---

## Prerequisites

**REQUIRES Phase 1 COMPLETION**

Before running Phase 2, you need:

1. Phase 1 Q1 2024 validation results (from `validate_regime_windows.py`)
2. Baseline detection rate (expected 3-10%)
3. Baseline accuracy rate (expected 70-80%)

**Why**: Phase 2 false positive thresholds are calibrated against Phase 1 baseline detection rate.

---

## Phase 2a: Shuffled Windows

**File**: `generate_shuffled_windows.py`

### Purpose

Validate that LLM doesn't detect false regimes in randomized data with no temporal structure.

### Method

1. Take real 30-day GEX sequences from Q1 2024
2. Randomly shuffle the day order (destroys temporal structure)
3. Present shuffled sequence to LLM with obfuscation
4. Count false positive detections

### What We're Testing

- Does the LLM rely on temporal patterns?
- Does it confuse noise for regime?

### Expected Results

- **Detection rate**: 0% (ideal) or <10% (acceptable threshold)
- **Regime type**: Should be "transitional" (sign flips from shuffling)

### Usage

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

python scripts/validation/generate_shuffled_windows.py
```

### Output

- **Location**: `reports/validation/regime_windows/phase2a_shuffled/shuffled_windows.yaml`
- **Format**: YAML with metadata, characteristics, and shuffled window data

### Success Criteria

✅ False positive rate <10%

### If Fails

- Action 1: Recalibrate confidence thresholds in prompt
- Action 2: Strengthen sign flip penalty in prompt
- Action 3: Add "consistency check" to prompt (are flips random or structured?)

---

## Phase 2b: Transitional Windows

**File**: `generate_transitional_windows.py`

### Purpose

Validate that LLM correctly rejects windows with frequent sign flips (no persistent direction).

### Method

1. Find or create 30-day windows with 7-10 sign flips
2. May be rare in Q1 2024 (persistent negative regime)
3. Option A: Hand-pick from full 2024 dataset
4. Option B: Create synthetic by splicing positive/negative days
5. Present to LLM with obfuscation

### What We're Testing

- Does the LLM enforce sign flip constraint (max 5 flips)?
- Does it recognize lack of persistent direction?

### Characteristics

- Sign persistence: 50-65% (15-20 days same sign)
- Sign flips: 7-10 flips
- Magnitude: May be adequate (>$5B) but direction unstable

### Expected Results

- **Detection rate**: 0-10% (should reject as "transitional")
- **LLM reasoning**: Should cite "too many sign flips" or "no persistent direction"

### Usage

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

python scripts/validation/generate_transitional_windows.py
```

### Output

- **Location**: `reports/validation/regime_windows/phase2b_transitional/transitional_windows.yaml`
- **Format**: YAML with natural and/or synthetic windows

### Success Criteria

✅ False positive rate <10%

### If Fails

- Action 1: Lower max sign flip threshold from 5 to 3
- Action 2: Strengthen "stability" requirement in prompt

---

## Phase 2c: Low-Magnitude Persistent

**File**: `generate_low_magnitude_windows.py`

### Purpose

Validate that LLM correctly rejects persistent-sign but weak-magnitude windows.

### Method

1. Take real persistent window (e.g., 26/30 days negative, $8B avg)
2. Scale GEX values down: multiply by 0.3 → now $2.4B avg
3. Present scaled window to LLM with obfuscation
4. Should reject as "low_conviction" despite sign persistence

### What We're Testing

- Does the LLM enforce magnitude threshold ($5B minimum)?
- Does it recognize weak constraint despite directional persistence?

### Characteristics

- Sign persistence: 70-90% (21-27 days same sign) ✅
- Sign flips: 0-3 (very stable) ✅
- Magnitude: <$3B average ❌ (below $5B threshold)

### Expected Results

- **Detection rate**: 0-10% (should reject as "low_conviction")
- **LLM reasoning**: Should cite "magnitude below $5B threshold"

### Usage

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

python scripts/validation/generate_low_magnitude_windows.py
```

### Output

- **Location**: `reports/validation/regime_windows/phase2c_low_magnitude/low_magnitude_windows.yaml`
- **Format**: YAML with original, scaled, and characteristics

### Success Criteria

✅ False positive rate <10%

### If Fails

- Action 1: Increase magnitude threshold from $5B to $7B
- Action 2: Add "minimum constraint strength" language to prompt

---

## Running Phase 2 (Complete Workflow)

### Step 1: Confirm Phase 1 Complete

```bash
# Check Phase 1 results
ls -lh reports/validation/regime_windows/phase1_q1_2024.yaml

# Verify detection rate (should be 3-10%)
grep "detection_rate_pct" reports/validation/regime_windows/phase1_q1_2024.yaml
```

### Step 2: Generate All Three Negative Control Sets

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

# Phase 2a: Shuffled windows
python scripts/validation/generate_shuffled_windows.py

# Phase 2b: Transitional windows
python scripts/validation/generate_transitional_windows.py

# Phase 2c: Low-magnitude windows
python scripts/validation/generate_low_magnitude_windows.py
```

### Step 3: Feed to LLM Validator

```bash
# Run Phase 2a through validator
python scripts/validation/validate_regime_windows.py \
  --phase2a \
  --input reports/validation/regime_windows/phase2a_shuffled/shuffled_windows.yaml

# Run Phase 2b through validator
python scripts/validation/validate_regime_windows.py \
  --phase2b \
  --input reports/validation/regime_windows/phase2b_transitional/transitional_windows.yaml

# Run Phase 2c through validator
python scripts/validation/validate_regime_windows.py \
  --phase2c \
  --input reports/validation/regime_windows/phase2c_low_magnitude/low_magnitude_windows.yaml
```

### Step 4: Analyze Results

```bash
# Aggregate Phase 2 results
# Expected output: phase2_negative_controls_summary.yaml
# Shows: false positive rates for 2a, 2b, 2c
# Decision: Pass all? Recalibrate? Revise prompt?
```

---

## Regime Criteria (From Phase 1)

These are the thresholds that Phase 2 tests:

| Criterion | Threshold | Phase 2 Tests |
|-----------|-----------|---------------|
| **Persistence** | >70% days same sign (21/30) | 2c (low persistence) |
| **Magnitude** | >$5B average GEX | 2c (below threshold) |
| **Stability** | ≤5 sign flips | 2b (above threshold) |
| **Temporal Structure** | Consecutive days required | 2a (randomized order) |

---

## Integration with validate_regime_windows.py

These generators produce YAML files that should be consumed by `validate_regime_windows.py`.

Expected interface:

```python
# Load negative control windows
with open("phase2a_shuffled/shuffled_windows.yaml") as f:
    controls = yaml.safe_load(f)

# Feed to LLM validator
for window in controls["shuffled_windows"]:
    result = validator.run_experiment(
        gex_values=window["shuffled_gex_values"],
        dates=window["obfuscated_dates"],
        control_type="shuffled"
    )
```

---

## Decision Tree: When Phase 2 Passes/Fails

### If All Three Tests Pass (<10% false positives)

```bash
✅ Phase 1 + Phase 2 complete
└─> Proceed to Phase 3 (Full 2024 validation)
└─> Methodology validated, ready for comprehensive analysis
```

### If Any Test Fails (>10% false positives)

```bash
⚠️  Recalibration needed

Option A: Adjust thresholds
├─ Lower persistence to 60% (18/30 days)
├─ Lower magnitude to $3B
└─ Re-run Phase 1 + Phase 2

Option B: Revise prompt
├─ Strengthen mechanical guidance
├─ Add more examples
└─ Re-run Phase 1 + Phase 2

Decision: Which changes first?
```

---

## File Organization

```bash
scripts/validation/
├── generate_shuffled_windows.py        # Phase 2a
├── generate_transitional_windows.py    # Phase 2b
├── generate_low_magnitude_windows.py   # Phase 2c
├── phase2_negative_controls_README.md  # This file
└── validate_regime_windows.py          # Main validator (Chat A creating)

reports/validation/regime_windows/
├── phase1_q1_2024.yaml                 # Phase 1 results
├── phase2a_shuffled/
│   └── shuffled_windows.yaml
├── phase2b_transitional/
│   └── transitional_windows.yaml
├── phase2c_low_magnitude/
│   └── low_magnitude_windows.yaml
└── phase2_negative_controls_summary.yaml  # Aggregate results
```

---

## Next Steps

1. **Chat A** completes Phase 1 validation (Q1 2024, ~32 windows)
2. **Chat B** (or both) runs Phase 2a, 2b, 2c generators
3. **Both** feed results through `validate_regime_windows.py` with LLM
4. **Both** analyze false positive rates
5. **Decision**: Thresholds OK? Or recalibrate and iterate?
6. **If Pass**: Proceed to Phase 3 (Full 2024 validation)

---

## Related Documentation

- [validation_phases.md](../../docs/papers/paper2/validation/validation_phases.md) - Full 4-phase roadmap
- [regime_windows_design.md](../../docs/papers/paper2/methodology/regime_windows_design.md) - 30-day methodology
- [regime_detection_v1.md](../../docs/papers/paper2/prompts/regime_detection_v1.md) - LLM prompt

---

**Status**: Ready for Phase 1 results (Nov 6, 2025)
**Next**: Waiting for Chat A to complete Phase 1 validation
