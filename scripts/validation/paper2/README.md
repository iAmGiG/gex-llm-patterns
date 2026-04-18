# Paper #2 Validation Scripts

**Paper Title**: *Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation*

**Status**: ✅ All five validation phases complete. Paper accepted at AIAI 2026 (camera-ready May 2026), under review at JRFM (MDPI). Final results: 81.2% detection 2024 vs 12.1% 2020 (69.1pp separation, φ = 0.672, p < 0.0001), 2,221 evaluations.

---

## Scripts (Workflow Order)

Scripts are numbered by execution order in the validation workflow.

### Negative Control Generation (Phase 2)

| Script | Purpose |
|--------|---------|
| `01_generate_shuffled_windows.py` | Generate randomized GEX sequences (0% expected detection) |
| `02_generate_transitional_windows.py` | Generate high-volatility windows with 7-10 sign flips |
| `03_generate_low_magnitude_windows.py` | Generate low-magnitude persistent sequences |

### Regime Validation

| Script | Purpose |
|--------|---------|
| `04_validate_regime_windows.py` | Synchronous validation (legacy) |
| `05_validate_regime_windows_batch.py` | Batch API validation (50% cost savings, recommended) |

### Testing

| Script | Purpose |
|--------|---------|
| `06_test_dual_gex.py` | Test dual GEX framework |
| `07_test_price_normalization.py` | Test price normalization |

---

## Usage Examples

**Batch validation (recommended):**

```bash
# 1. Submit batch
python scripts/validation/paper2/05_validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --submit

# 2. Poll for completion
python scripts/validation/paper2/05_validate_regime_windows_batch.py \
  --batch-id batch_xxx \
  --poll

# 3. Retrieve results
python scripts/validation/paper2/05_validate_regime_windows_batch.py \
  --batch-id batch_xxx \
  --retrieve
```

**Generate negative controls:**

```bash
python scripts/validation/paper2/01_generate_shuffled_windows.py \
  --count 10 \
  --output reports/validation/regime_windows/phase2_shuffled.yaml
```

---

## Validation Framework

### Regime Detection Criteria (30-Day Windows)

1. **Persistence**: >=70% days same sign (positive or negative)
2. **Magnitude**: >=$5B average absolute GEX
3. **Stability**: <=5 sign flips across window

### 4-Phase Validation Strategy

| Phase | Windows | Purpose | Cost (Batch) | Status |
|-------|---------|---------|--------------|--------|
| **Phase 1** | 52 (Q1 2024) | Baseline detection | $0.81 | Complete (71.2%) |
| **Phase 2** | ~30 | Negative controls | $0.50 | Pending |
| **Phase 3** | 223 (Full 2024) | Full year validation | $1.75 | Planned |
| **Phase 4** | 223 (2020) | 0DTE hypothesis test | $1.75 | Planned |

---

## Key Phase 1 Results (November 2025)

- **Detection rate**: 71.2% (37/52 windows)
- **Model**: o4-mini-2025-04-16
- **Cost**: $0.81 (50% savings vs sync)
- **Average confidence**: 71% (detected), 40% (rejected)

---

## Related Documentation

- **Batch API Guide**: `docs/papers/paper2/validation/BATCH_API_GUIDE.md`
- **Phase 2 Controls**: `phase2_negative_controls_README.md`
- **Results**: `reports/validation/regime_windows/`

---

## Dependencies

**Python Modules**:

- `src.validation.batch_regime_validator` - Batch API wrapper
- `src.validation.regime_classifier` - Window classification logic
- `src.llm.mechanics_prompt_builder` - Regime detection prompts
- `src.data_sources.sequential_gex_fetcher` - GEX window fetching

**Data Sources**:

- Historical GEX database (`.cache/consolidated_historical.db`)
- OpenAI Batch API (o4-mini-2025-04-16)
