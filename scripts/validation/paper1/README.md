# Paper #1 Validation Scripts

**Paper Title**: "LLM-Based Detection of Dealer Gamma Constraints: Obfuscation Testing Methodology"

**Status**: ✅ Paper submitted (October 26, 2025), under revision (November 10, 2025)

---

## Scripts

### `validate_pattern_taxonomy.py`

**Purpose**: Single-pattern validation using obfuscation testing methodology

**Usage**:

```bash
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

python scripts/validation/paper1/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --confidence 60.0 \
  --with-outcomes
```

**Key Features**:

- Obfuscation testing (strips dates/tickers to prevent LLM memorization)
- Outcome calculation (forward returns, realized volatility)
- Pattern detection with WHO→WHOM→WHAT framework
- YAML output with comprehensive metrics

**Output**: `reports/validation/pattern_taxonomy/{pattern}_{symbol}_{quarter}.yaml`

---

### `validate_all_patterns.py`

**Purpose**: Batch validation across multiple patterns

**Usage**:

```bash
python scripts/validation/paper1/validate_all_patterns.py \
  --patterns stock_pinning 0dte_hedging gamma_positioning \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --skip-completed
```

**Key Features**:

- Validates multiple patterns in sequence
- Skips already-completed pattern-quarter combinations
- Tracks progress across multi-pattern runs
- Comprehensive error handling and logging

**Output**: Multiple YAML files (one per pattern)

---

### `validate_patterns.py`

**Purpose**: Legacy validation script (pre-Issue #79 refactor)

**Status**: ⚠️ DEPRECATED - Use `validate_pattern_taxonomy.py` instead

**Note**: Retained for historical reference but not actively maintained

---

## Key Validation Results (Full 2024)

| Pattern | Q1 Detection | Q3 Detection | Q4 Detection | Avg Accuracy |
|---------|-------------|-------------|-------------|--------------|
| gamma_positioning | 100% (53/53) | 100% (64/64) | 100% (64/64) | 97.7% |
| stock_pinning | 100% (53/53) | 100% (64/64) | 100% (64/64) | 90.3% |
| 0dte_hedging | 100% (53/53) | 100% (64/64) | 100% (64/64) | 90.5% |

**Total**: 181 trading days validated across 3 patterns (543 pattern-day combinations)

**Key Finding**: Detection remains 100% even as profitability declines Q1→Q4, proving LLM detects market structure (not profits)

---

## Related Documentation

- **Validation results**: `reports/validation/pattern_taxonomy/`
- **Paper LaTeX source**: `docs/papers/paper1/Main.tex`
- **Dissertation archive**: `docs/dissertation/paper1_llm_pattern_detection/`
- **GitHub Issues**: #79 (validation), #80 (outcomes), #81 (obfuscation fix)

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
