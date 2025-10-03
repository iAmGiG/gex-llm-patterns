# Pattern Taxonomy Validation Guide - Issue #79

## Overview

Validates that patterns work via **obfuscation tests** - proving patterns detect mechanics without knowing dates/tickers/events.

## Quick Start

### Proof-of-Concept: Single Pattern Test

```bash
# Test gamma_positioning pattern across full 2024 dataset
python scripts/validation/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-06-28 \
  --confidence 60.0
```

### Check Data Continuity First

```bash
# Check what dates are available and identify gaps
python scripts/validation/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --check-continuity
```

## Available Patterns

| Pattern | Type | Academic Support | Status |
|---------|------|------------------|--------|
| `gamma_positioning` | Mechanical | Buis et al. 2024 | ✅ Ready |
| `stock_pinning` | Mechanical | Jeannin et al. 2008 | ✅ Ready |
| `0dte_hedging` | Mechanical | 0DTE papers | ✅ Ready |
| `dealer_trap` | Probabilistic | None | ⚠️ Needs test |
| `friday_330_squeeze` | Probabilistic | None | ⚠️ Needs test |
| `volume_anomaly` | Unknown | None | ❌ No mechanism |

## Validation Criteria (Issue #79)

### Obfuscation Test

- **Goal**: Pattern works without date/ticker context
- **Success**: ≥60% detection rate
- **Sample Size**: ≥30 dates
- **Method**: Dates → "Day T+0, T+7", Tickers → "INDEX_1"

### Economic Significance (Phase 2)

- **Goal**: Profitable after transaction costs
- **Success**: >20bps average return
- **Method**: Backtest with realistic slippage/commissions

### Baseline Comparison (Phase 3)

- **Goal**: LLM adds value over simple rules
- **Success**: Better win rate + Sharpe than raw GEX strategy
- **Method**: Compare vs `baseline_gex_strategy.py`

## Workflow

### Phase 1: Data Continuity Check

```bash
# Check cache coverage for date range
python scripts/validate_pattern_taxonomy.py \
  --start-date 2024-01-02 \
  --end-date 2024-06-28 \
  --check-continuity

# Review output: reports/validation/data_continuity.yaml
```

**What to look for:**

- `continuity_pct`: Should be >90%
- `missing_dates`: Agent will attempt to fetch these via API
- If continuity <90%, expect some API calls

### Phase 2: Run Pattern Validation

```bash
# Start with gamma_positioning (strongest academic support)
python scripts/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --confidence 60.0

# Watch logs for:
#   ✅ "DETECTED: X% confidence" (pattern found)
#   ⚠️  "Low confidence: X%" (pattern not found)
#   ❌ "Error testing date" (data fetch failed)
```

**Monitor for data fetch issues:**

- `"Fetched options data from cache"` → Good (using cached data)
- `"Fetched options data from api"` → OK (filling gaps)
- `"AutoGen fetch failed"` → Problem (API error, will use cache fallback)
- `"Error testing date"` → Problem (both cache and API failed)

### Phase 3: Review Results

```bash
# Check output: reports/validation/pattern_taxonomy/gamma_positioning_validation_YYYYMMDD_HHMMSS.yaml
cat reports/validation/pattern_taxonomy/gamma_positioning_validation_*.yaml
```

**Key metrics to check:**

- `obfuscation_test.passed`: true/false
- `obfuscation_test.success_rate`: Should be ≥60%
- `detection_metrics.total_tested`: Should be ≥30
- `failed_dates`: List of dates where data fetch failed

### Phase 4: Handle Data Gaps (if needed)

If you see many `failed_dates`, re-run to attempt fresh API fetches:

```bash
# Agent will retry fetching missing dates
python scripts/validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --start-date 2024-01-02 \
  --end-date 2024-06-28
```

**Iterative refinement:**

1. Run test
2. Check `failed_dates` in YAML output
3. Agent retries on next run (cache may be stale)
4. Repeat until `continuity_pct` ≥95%

## Output Format

### YAML Structure

```yaml
pattern_name: gamma_positioning
test_metadata:
  symbol: SPY
  test_period: "2024-01-02 to 2024-06-28"
  total_dates_requested: 70
  total_dates_tested: 68
  failed_fetches: 2
  obfuscation_enabled: true

detection_metrics:
  high_confidence_detections: 45
  low_confidence_detections: 23
  success_rate_pct: 66.2
  total_tested: 68

obfuscation_test:
  passed: true
  success_rate: 66.2
  sample_size: 68
  required_success_rate: 60.0
  required_sample_size: 30
  verdict: "MECHANICAL - 66.2% success with 68 samples (validated)"

detections:
  - date: "2024-01-02"
    date_obfuscated: "Day T+0"
    confidence: 75
    detected: true
    who: "Call buyers"
    whom: "Market makers"
    what: "Forced delta hedging"
    data_source: "cache"
  # ... more detections ...

failed_dates:
  - "2024-01-15"
  - "2024-02-03"
```

## Success Criteria Summary

| Criterion | Target | Measured By |
|-----------|--------|-------------|
| Obfuscation | Works without context | Pattern detected with obfuscated dates/tickers |
| Success Rate | ≥60% | High-confidence detections / total tests |
| Sample Size | ≥30 dates | Total dates successfully tested |
| Data Continuity | ≥90% | Available dates / requested dates |

## Next Steps After Validation

1. **If pattern PASSES obfuscation test:**
   - Move to Phase 2: Economic backtest (calculate returns after costs)
   - Use `baseline_gex_strategy.py` to measure profitability

2. **If pattern FAILS obfuscation test:**
   - Pattern may be narrative/folklore
   - Either (A) improve LLM prompts, or (B) discard pattern
   - Document as "not mechanically validated"

3. **After all patterns validated:**
   - Run baseline comparison (Issue #58)
   - Prove LLM adds value over simple GEX rules
   - Deploy only validated patterns to production

## Troubleshooting

### "No dates found in cache"

```bash
# Check cache directory
ls .cache/options/SPY/

# If empty, agent needs to fetch from API (may be slow)
```

### "Too many failed fetches"

- Check API rate limits (Alpha Vantage, Polygon, etc.)
- Verify cache permissions (read/write access)
- Run with smaller date range initially

### "Low success rate (<60%)"

- Pattern may not be mechanical (folklore)
- LLM may need prompt tuning
- Check if pattern requires specific market conditions (e.g., OPEX only)

### "Insufficient samples (<30)"

- Expand date range (use more of 2024)
- Use multiple symbols (SPY + QQQ + IWM)
- Accept lower confidence as "probabilistic" instead of "mechanical"

## Related Files

- **Validation Script**: `scripts/validate_pattern_taxonomy.py`
- **Pattern Framework**: `src/validation/pattern_taxonomy.py`
- **Obfuscation**: `src/validation/data_obfuscation.py`
- **Baseline Strategy**: `src/analysis/baseline_gex_strategy.py`
- **Config**: `config_defaults/trading_config.yaml`
- **Output**: `reports/validation/pattern_taxonomy/`
