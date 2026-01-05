# Paper #1 Validation Scripts

**Paper Title**: "LLM-Based Detection of Dealer Gamma Constraints: Obfuscation Testing Methodology"

**Status**: Paper submitted (October 26, 2025), under revision (November 10, 2025)

---

## Scripts (Workflow Order)

Scripts are numbered by execution order in the validation workflow.

### Data Validation

| Script | Purpose |
|--------|---------|
| `01_validate_raw_options_chain.py` | **Raw Chain Inference Validation** (Section 4.2) |

### Pattern Detection

| Script | Purpose |
|--------|---------|
| `02_validate_pattern_taxonomy.py` | Single-pattern obfuscation testing (primary) |
| `03_validate_all_patterns.py` | Batch validation across multiple patterns |
| `04_validate_patterns_legacy.py` | Legacy validation (deprecated) |

### Materialization Analysis

| Script | Purpose |
|--------|---------|
| `05_calculate_materialization_criteria.py` | Calculate pattern materialization criteria |
| `06_baseline_materialization_analysis.py` | Baseline comparison analysis |
| `07_build_contingency_matrix.py` | Build detection contingency matrix |
| `08_calculate_flip_points.py` | Calculate GEX flip points |
| `09_verify_materialization.py` | Verify materialization results |

### Non-Detection Analysis

| Script | Purpose |
|--------|---------|
| `10_analyze_non_detections.py` | Analyze why certain patterns weren't detected |

### Narrative Framework Testing

| Script | Purpose |
|--------|---------|
| `11_narrative_test_pilot.py` | Pilot test for WHO-WHOM-WHAT framework necessity |
| `12_narrative_test_batch.py` | Batch narrative framework testing |
| `13_narrative_test_analysis.py` | Analyze narrative test results |

### Reasoning Extraction

| Script | Purpose |
|--------|---------|
| `14_batch_llm_reasoning.py` | Batch extract LLM reasoning |
| `15_extract_quarterly_reasoning.py` | Extract reasoning by quarter |

### Latent Information Analysis

| Script | Purpose |
|--------|---------|
| `16_analyze_eod_latent_information.py` | Analyze end-of-day latent information |

### Figure Generation

| Script | Purpose |
|--------|---------|
| `17_regenerate_validation_figures.py` | Regenerate validation figures for paper |

---

## Usage Examples

**Single pattern validation:**

```bash
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --confidence 60.0 \
  --with-outcomes
```

**Batch validation:**

```bash
python scripts/validation/paper1/03_validate_all_patterns.py \
  --patterns stock_pinning 0dte_hedging gamma_positioning \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --skip-completed
```

---

## Key Validation Results (Full 2024)

| Pattern | Q1 Detection | Q3 Detection | Q4 Detection | Avg Accuracy |
|---------|-------------|-------------|-------------|--------------|
| gamma_positioning | 100% (53/53) | 100% (64/64) | 100% (64/64) | 97.7% |
| stock_pinning | 100% (53/53) | 100% (64/64) | 100% (64/64) | 90.3% |
| 0dte_hedging | 100% (53/53) | 100% (64/64) | 100% (64/64) | 90.5% |

**Key Finding**: Detection remains 100% even as profitability declines Q1-Q4, proving LLM detects market structure (not profits)

---

## Related Documentation

- **Validation results**: `reports/validation/pattern_taxonomy/`
- **Paper LaTeX source**: `docs/papers/paper1/Main.tex`
- **Dissertation archive**: `docs/dissertation/paper1_llm_pattern_detection/`

---

## Dependencies

**Python Modules**:

- `src.validation.pattern_taxonomy` - Pattern definitions and validation framework
- `src.validation.outcome_calculator` - Forward returns and prediction verification
- `src.validation.data_obfuscation` - Date/ticker obfuscation for anti-cheating
- `src.agents.market_mechanics_agent` - Core LLM agent for pattern detection

**Data Sources**:

- Alpha Vantage API (options chains)
- Polygon.io API (stock prices)
- Historical GEX database (`.cache/consolidated_historical.db`)
