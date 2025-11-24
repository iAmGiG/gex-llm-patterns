# Validation Scripts

**Purpose**: Organized validation tooling for Paper #1 (pattern taxonomy) and Paper #2 (regime detection)

---

## Directory Structure

```
scripts/validation/
├── paper1/          ✅ Paper #1: Pattern Taxonomy Validation (Submitted Oct 2025)
│   ├── validate_pattern_taxonomy.py                     - Single pattern obfuscation testing
│   ├── validate_all_patterns.py                         - Multi-pattern batch validation
│   ├── validate_patterns.py                             - Legacy validation (deprecated)
│   ├── verify_narrative_necessity_pilot.py              - WHO→WHOM→WHAT necessity pilot (Issue #133)
│   ├── verify_narrative_necessity_phase2_batch.py       - Full narrative removal (52 dates, Batch API)
│   ├── verify_narrative_necessity_phase3_batch.py       - Balanced sample validation (Issue #133)
│   └── README.md                                        - Paper #1 script documentation
│
├── paper2/          🔄 Paper #2: Regime Detection (Multi-Year Expansion, Issue #140)
│   ├── validate_regime_windows_batch.py                 - Batch API regime validation (RECOMMENDED)
│   ├── validate_regime_windows.py                       - Synchronous regime validation (legacy)
│   ├── verify_dual_gex_framework.py                     - Dual GEX framework verification (Issue #138)
│   ├── generate_shuffled_windows.py                     - Phase 2a: Shuffled negative controls
│   ├── generate_transitional_windows.py                 - Phase 2b: Transitional negative controls
│   ├── generate_low_magnitude_windows.py                - Phase 2c: Low-magnitude negative controls
│   └── README.md                                        - Paper #2 script documentation
│
├── shared/          🔧 Cross-Paper Utilities
│   ├── export_db_to_cache.py                     - Database to cache export
│   ├── production_cache_test.py                  - Cache integrity testing
│   └── README.md                                 - Shared utilities documentation
│
└── deprecated/      ⚠️ Historical Scripts (Sept 2025, Not Maintained)
    ├── validate_sequential_patterns.py           - 5-day sequential validation (pivoted to 30-day)
    ├── test_10am_reversal.py                     - Time-based pattern tests
    ├── test_afternoon_drift.py                   - 3:30 PM pinning tests
    ├── test_*.py                                 - Various exploratory pattern tests (10 files)
    └── README.md                                 - Deprecated scripts context
```

---

## Quick Start

### Paper #1: Pattern Taxonomy Validation

**Single pattern test** (gamma positioning, Q1 2024):

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

python scripts/validation/paper1/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --with-outcomes
```

**Multi-pattern batch**:

```bash
python scripts/validation/paper1/validate_all_patterns.py \
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
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --submit

# 2. Poll for completion
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> \
  --poll

# 3. Retrieve results
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> \
  --retrieve
```

**Phase 2 negative controls** (pending):

```bash
# Generate shuffled windows
python scripts/validation/paper2/generate_shuffled_windows.py \
  --count 10 \
  --output reports/validation/regime_windows/phase2_shuffled.yaml
```

**Results**: Phase 1 achieved 71.2% detection (37/52 windows) with strong selectivity (39-point persistence gap)

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
| **Status** | ✅ Complete (submitted) | 🔄 Phase 1 complete |

---

## Validation Methodology

### Paper #1: Obfuscation Testing

1. Strip all dates/tickers/events from market data
2. Present as "Day T+0", "Day T+1", "INDEX_1" to LLM
3. Test if LLM can still detect dealer constraints
4. Verify predictions with outcome calculation

**Success Criteria**: ≥60% detection, ≥30 samples, no temporal context

---

### Paper #2: 4-Phase Validation

1. **Phase 1**: Q1 2024 baseline (52 windows) - ✅ 71.2% detection
2. **Phase 2**: Negative controls (30 windows) - 📅 Pending (<10% FP target)
3. **Phase 3**: Full 2024 (223 windows) - 🔮 Planned (30-50% target)
4. **Phase 4**: 2020 comparison (223 windows) - 🔮 Planned (0DTE hypothesis)

**Regime Criteria**: ≥70% persistence + ≥$5B avg + ≤5 sign flips

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

**3. Set PYTHONPATH** (required for all scripts):

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH
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

**2. Verify YAML integrity**:

```bash
python3 -c "import yaml; print(yaml.safe_load(open('reports/validation/pattern_taxonomy/gamma_positioning_SPY_2024Q1.yaml')))"
```

**3. Calculate statistics** (example for Paper #1):

```bash
grep "detection_rate_pct" reports/validation/pattern_taxonomy/*.yaml | awk '{sum+=$2; count++} END {print "Avg Detection:", sum/count "%"}'
```

---

## Cost Estimation

### Paper #1 (Full 2024)

- **Windows**: 181 trading days × 3 patterns = 543 validations
- **Cost per window**: ~$0.03 (o3-mini)
- **Total**: ~$16.29

### Paper #2 (All Phases)

- **Phase 1**: 52 windows × $0.016 = $0.83
- **Phase 2**: 30 windows × $0.016 = $0.48
- **Phase 3**: 223 windows × $0.016 = $3.57
- **Phase 4**: 223 windows × $0.016 = $3.57
- **Total**: ~$8.45 (Batch API savings: ~$4.31)

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Set PYTHONPATH before running scripts:

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH
```

---

### Cache Misses

**Problem**: API rate limits during validation

**Solution**: Pre-populate cache with historical data:

```bash
python scripts/validation/shared/export_db_to_cache.py \
  --start-date 2024-01-02 \
  --end-date 2024-12-31
```

---

### JSON Parsing Errors (Paper #2)

**Problem**: `JSONDecodeError: Invalid \escape`

**Solution**: Already fixed in Issue #137. If recurring, check:

- Batch API using o4-mini-2025-04-16 (not older models)
- Prompt includes numeric field specifications
- Defensive parsing enabled in `batch_regime_validator.py`

---

## Related Documentation

- **Paper #1 LaTeX**: `docs/papers/paper1/Main.tex`
- **Paper #2 Planning**: `docs/papers/paper2/planning/`
- **Validation Results**: `reports/validation/`
- **Batch API Guide**: `docs/papers/paper2/validation/BATCH_API_GUIDE.md`

---

## GitHub Issues

**Paper #1**:

- #79 - Pattern taxonomy validation (COMPLETE)
- #80 - Outcome calculator integration (COMPLETE)
- #81 - Obfuscation bug fix (RESOLVED)

**Paper #2**:

- #89 - 30-day regime detection framework
- #107 - Validation strategy (Phase 1 COMPLETE)
- #112 - Batch API implementation (COMPLETE)
- #137 - JSON parsing fixes (RESOLVED)

---

---

## Script Organization Notes

**November 22, 2025**: Reorganized scripts by paper affiliation to minimize merge conflicts across worktrees:

- **Paper #1 scripts** moved to `paper1/` subfolder (pattern validation + narrative removal tests)
- **Paper #2 scripts** moved to `paper2/` subfolder (regime detection + dual GEX tests)
- **Root-level scripts** removed (all now in paper-specific folders)

**Active Worktrees**:

- Issue #140 (Paper #2 multi-year): `/mnt/bst/yxie2/cregan1/gex-llm-patterns-issue140`
- Issue #141-146 (Paper #1 extensions): `/mnt/bst/yxie2/cregan1/gex-llm-patterns-issue141`

---

**Last Updated**: November 22, 2025
