# Validation Scripts

**Purpose**: Organized validation tooling for Paper #1 (pattern taxonomy) and Paper #2 (regime detection)

---

## Directory Structure

```text
scripts/validation/
├── paper1/          Paper #1: Pattern Taxonomy Validation (Submitted Oct 2025)
│   ├── 01_validate_raw_options_chain.py     - Raw options chain validation
│   ├── 02_validate_pattern_taxonomy.py      - Single pattern obfuscation testing
│   ├── 03_validate_all_patterns.py          - Multi-pattern batch validation
│   ├── 04_validate_patterns_legacy.py       - Legacy validation (deprecated)
│   ├── 05-09_*materialization*.py           - Materialization analysis (5 scripts)
│   ├── 10_analyze_non_detections.py         - Non-detection analysis
│   ├── 11-13_narrative_test_*.py            - Narrative framework testing (3 scripts)
│   ├── 14-15_*reasoning*.py                 - Reasoning extraction (2 scripts)
│   ├── 16_analyze_eod_latent_information.py - Latent information analysis
│   ├── 17_regenerate_validation_figures.py  - Figure generation
│   └── README.md                            - Paper #1 documentation
│
├── paper2/          Paper #2: Regime Detection (Multi-Year Expansion)
│   ├── 01-03_generate_*_windows.py          - Negative control generators (3 scripts)
│   ├── 04_validate_regime_windows.py        - Synchronous validation (legacy)
│   ├── 05_validate_regime_windows_batch.py  - Batch API validation (recommended)
│   ├── 06_test_dual_gex.py                  - Dual GEX framework test
│   ├── 07_test_price_normalization.py       - Price normalization test
│   └── README.md                            - Paper #2 documentation
│
└── shared/          Cross-Paper Utilities
    ├── export_db_to_cache.py                - Database to cache export
    └── production_cache_test.py             - Cache integrity testing
```

---

## Quick Start

### Paper #1: Pattern Taxonomy Validation

**Single pattern test** (gamma positioning, Q1 2024):

```bash
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --with-outcomes
```

**Multi-pattern batch**:

```bash
python scripts/validation/paper1/03_validate_all_patterns.py \
  --patterns stock_pinning 0dte_hedging gamma_positioning \
  --start-date 2024-01-02 \
  --end-date 2024-03-29
```

**Results**: Paper #1 achieved 100% detection, 87-98% accuracy across 181 trading days (Q1, Q3, Q4 2024)

---

### Paper #2: Regime Detection

**Phase 1 validation** (Q1 2024, 52 windows, Batch API):

```bash
# 1. Submit batch
python scripts/validation/paper2/05_validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --submit

# 2. Poll for completion
python scripts/validation/paper2/05_validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> \
  --poll

# 3. Retrieve results
python scripts/validation/paper2/05_validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> \
  --retrieve
```

**Phase 2 negative controls** (pending):

```bash
python scripts/validation/paper2/01_generate_shuffled_windows.py \
  --count 10 \
  --output reports/validation/regime_windows/phase2_shuffled.yaml
```

**Results**: Phase 1 achieved 71.2% detection (37/52 windows) with strong selectivity

---

## Key Differences Between Papers

| Aspect | Paper #1 | Paper #2 |
|--------|----------|----------|
| **Focus** | Pattern taxonomy obfuscation | Regime persistence detection |
| **Window Size** | 1-day (single trading day) | 30-day (regime windows) |
| **Detection Target** | 100% (universal mechanics) | 30-50% (selective regimes) |
| **Validation Type** | Obfuscation testing | Negative controls + full year |
| **Cost per Window** | ~$0.03 (o3-mini) | ~$0.016 (o4-mini batch) |
| **Processing** | Synchronous | Batch API (async) |
| **Status** | Complete (submitted) | Phase 1 complete |

---

## Validation Methodology

### Paper #1: Obfuscation Testing

1. Strip all dates/tickers/events from market data
2. Present as "Day T+0", "Day T+1", "INDEX_1" to LLM
3. Test if LLM can still detect dealer constraints
4. Verify predictions with outcome calculation

**Success Criteria**: >=60% detection, >=30 samples, no temporal context

---

### Paper #2: 4-Phase Validation

1. **Phase 1**: Q1 2024 baseline (52 windows) - 71.2% detection
2. **Phase 2**: Negative controls (30 windows) - Pending (<10% FP target)
3. **Phase 3**: Full 2024 (223 windows) - Planned (30-50% target)
4. **Phase 4**: 2020 comparison (223 windows) - Planned (0DTE hypothesis)

**Regime Criteria**: >=70% persistence + >=$5B avg + <=5 sign flips

---

## Common Workflows

### Before Starting Validation

**1. Verify cache integrity**:

```bash
python scripts/validation/shared/production_cache_test.py --date 2024-01-02 --symbol SPY
```

**2. Check database coverage**:

```bash
sqlite3 .cache/consolidated_historical.db "SELECT MIN(date), MAX(date), COUNT(*) FROM gex_daily_summary;"
```

---

### After Validation Runs

**1. Check results**:

```bash
# Paper #1 results
ls -lth reports/validation/pattern_taxonomy/

# Paper #2 results
ls -lth reports/validation/regime_windows/
```

---

## Related Documentation

- **Paper #1 LaTeX**: `docs/papers/paper1/Main.tex`
- **Paper #2 Planning**: `docs/papers/paper2/planning/`
- **Validation Results**: `reports/validation/`

---

**Last Updated**: December 17, 2025
