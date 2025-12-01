# Paper #2 Validation Scripts

**Paper Title**: "LLM-Based Regime Detection in Gamma Exposure Markets"

**Status**: 🔄 Phase 1 complete (71.2% detection, Q1 2024), Phase 2 pending

---

## Core Validation Scripts

### `validate_regime_windows.py`

**Purpose**: Synchronous validation of 30-day regime windows (legacy)

**Status**: ⚠️ Use `validate_regime_windows_batch.py` instead for 50% cost savings

**Usage**:

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

python scripts/validation/paper2/validate_regime_windows.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --model o4-mini \
  --output reports/validation/regime_windows/phase1_q1_2024.yaml
```

**Note**: Blocks terminal for 1-2 hours during processing

---

### `validate_regime_windows_batch.py` ✅ RECOMMENDED

**Purpose**: Batch API validation for 50% cost reduction and async processing

**Usage**:

**1. Submit batch**:

```bash
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --submit
```

**2. Poll for completion**:

```bash
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_690d320b0ce08190b63db73858cbddf8 \
  --poll
```

**3. Retrieve results**:

```bash
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_690d320b0ce08190b63db73858cbddf8 \
  --retrieve
```

**Cost Savings**:

- Phase 1 (52 windows): $1.62 → $0.81 (save $0.81)
- Phase 3 (223 windows): $3.50 → $1.75 (save $1.75)
- Phase 4 (223 windows): $3.50 → $1.75 (save $1.75)
- **Total**: ~$4.31 savings across all phases

**Key Features**:

- Asynchronous processing (1-2 hours, terminal free)
- Automatic batch metadata tracking
- JSON parsing fixes for o4-mini quirks (Issue #137)
- Obfuscation support (Day T-29 through Day T+0 format)

**Related**: Issue #112 (Batch API implementation)

---

## Negative Control Generators (Phase 2)

### `generate_shuffled_windows.py`

**Purpose**: Generate randomized GEX sequences to validate temporal structure detection

**Expected Result**: 0% detection (should reject as non-regimes)

**Usage**:

```bash
python scripts/validation/paper2/generate_shuffled_windows.py \
  --count 10 \
  --output reports/validation/regime_windows/phase2_shuffled.yaml
```

**How it works**: Takes real 30-day GEX sequences, randomizes day order, destroys temporal coherence

---

### `generate_transitional_windows.py`

**Purpose**: Generate high-volatility windows with 7-10 sign flips

**Expected Result**: 0-10% detection (should reject as "transitional")

**Usage**:

```bash
python scripts/validation/paper2/generate_transitional_windows.py \
  --count 10 \
  --output reports/validation/regime_windows/phase2_transitional.yaml
```

**How it works**: Creates windows violating "≤5 sign flips" regime criterion

---

### `generate_low_magnitude_windows.py`

**Purpose**: Generate persistent sequences with <$3B average magnitude

**Expected Result**: 0-10% detection (should reject as "low_conviction")

**Usage**:

```bash
python scripts/validation/paper2/generate_low_magnitude_windows.py \
  --count 10 \
  --output reports/validation/regime_windows/phase2_low_magnitude.yaml
```

**How it works**: Scales persistent sequences to violate ">$5B avg" regime criterion

---

## Validation Framework

### Regime Detection Criteria (30-Day Windows)

1. **Persistence**: ≥70% days same sign (positive or negative)
2. **Magnitude**: ≥$5B average absolute GEX
3. **Stability**: ≤5 sign flips across window

### Detection Rate Targets

- **Phase 1** (Q1 2024): ✅ 71.2% (borderline, Q1 anomaly)
- **Phase 2** (Negative controls): <10% false positive rate
- **Phase 3** (Full 2024): 30-50% (selective detection)
- **Phase 4** (2020 comparison): 10-30% (0DTE hypothesis)

### 4-Phase Validation Strategy

| Phase | Windows | Purpose | Cost (Batch) | Status |
|-------|---------|---------|--------------|--------|
| **Phase 1** | 52 (Q1 2024) | Baseline detection | $0.81 | ✅ Complete (71.2%) |
| **Phase 2** | ~30 | Negative controls | $0.50 | 📅 Pending |
| **Phase 3** | 223 (Full 2024) | Full year validation | $1.75 | 🔮 Planned |
| **Phase 4** | 223 (2020) | 0DTE hypothesis test | $1.75 | 🔮 Planned |

---

## Key Phase 1 Results (November 2025)

**Execution**:

- 52 windows (Q1 2024: 2024-01-02 through 2024-03-27)
- Model: o4-mini-2025-04-16
- Cost: $0.81 (50% savings vs sync)
- Processing time: 23 minutes
- Success rate: 100% (52/52 windows parsed)

**Detection**:

- **Detection rate**: 71.2% (37/52 windows)
- **Detected**: 37 persistent_positive regimes
- **Rejected**: 15 transitional regimes
- **Average confidence**: 71% (detected), 40% (rejected)

**Selectivity Metrics**:

- **Persistence gap**: 39 points (96% detected vs 57% rejected)
- **Magnitude gap**: $11.66B vs $4.82B
- **Confidence gap**: 53.5 points (93.0 vs 39.5)

**Decision**: Proceed to Phase 2 (borderline but acceptable given Q1 2024 anomaly)

---

## Related Documentation

- **Batch API Guide**: `docs/papers/paper2/validation/BATCH_API_GUIDE.md`
- **Implementation Summary**: `docs/papers/paper2/validation/BATCH_API_IMPLEMENTATION_SUMMARY.md`
- **Validation Phases**: `docs/papers/paper2/planning/validation_phases.md`
- **Phase 2 Controls**: `docs/papers/paper2/validation/phase2_negative_controls_README.md`
- **Results**: `reports/validation/regime_windows/`

---

## GitHub Issues

- **#89**: 30-day regime detection framework
- **#107**: Paper #2 validation strategy
- **#112**: OpenAI Batch API implementation (COMPLETE)
- **#137**: JSON parsing fixes for o4-mini (COMPLETE)

---

## Dependencies

**Python Modules**:

- `src.validation.batch_regime_validator` - Batch API wrapper for regime validation
- `src.validation.regime_classifier` - 30-day window classification logic
- `src.llm.mechanics_prompt_builder` - Regime detection prompt builder
- `src.data_sources.sequential_gex_fetcher` - 30-day GEX window fetching

**Data Sources**:

- Historical GEX database (`.cache/consolidated_historical.db`)
- OpenAI Batch API (o4-mini-2025-04-16 model)

**Config Files**:

- `config_defaults/llm_prompts.yaml` - Regime detection prompts
- `config/config.json` - API keys (OPENAI_API_KEY)
