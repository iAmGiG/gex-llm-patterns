# Pattern Taxonomy Validation Guide - Issue #79

## ✅ Status: VALIDATION COMPLETE (October 12, 2025)

**Multi-pattern validation successfully completed for full 2024 year:**

- **3 patterns tested**: gamma_positioning, stock_pinning, 0dte_hedging
- **181 trading days**: Q1, Q3, Q4 2024 (Q2 insufficient data coverage)
- **100% detection rate**: Maintained across all 9 quarter-pattern combinations
- **87-98% predictive accuracy**: Maintained across all quarters
- **All patterns MECHANICAL**: Pass obfuscation testing

**Research Question Answered**: LLMs can detect structural market microstructure patterns without memorization ✅

See `docs/archive/multipattern_validation_2024.md` for comprehensive analysis.

---

## Overview

Validates that patterns work via **obfuscation tests** - proving patterns detect mechanics without knowing dates/tickers/events.

## Quick Start

### Proof-of-Concept: Single Pattern Test

```bash
# Test gamma_positioning pattern across full 2024 dataset
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
  --pattern gamma_positioning \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-06-28 \
  --confidence 60.0
```

### Check Data Continuity First

```bash
# Check what dates are available and identify gaps
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
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
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
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
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
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
python scripts/validation/paper1/02_validate_pattern_taxonomy.py \
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

### Enhanced YAML Structure (Issue #80)

```yaml
pattern_name: gamma_positioning
test_metadata:
  symbol: SPY
  start_date: "2024-01-02"
  end_date: "2024-06-28"
  test_period: "2024-01-02 to 2024-06-28"
  total_dates_requested: 70
  total_dates_tested: 68
  failed_fetches: 2
  obfuscation_enabled: true

performance_metrics:  # Renamed from detection_metrics
  # Detection (Phase 1: Pattern Recognition)
  total_tested: 68
  detection_rate_pct: 66.2  # Renamed from success_rate_pct
  high_confidence_detections: 45
  low_confidence_detections: 23

  # Prediction (Phase 2: Outcome Validation - populated by backtest)
  predictive_accuracy_pct: 85.0
  avg_forward_1d_return_pct: 0.45

  # Economics (Phase 2: Profitability)
  net_alpha_pct: 0.40  # 45bps - 5bps costs
  passes_economic_threshold: true  # >20bps requirement
  is_validated: true

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
    detected: true
    obfuscation_verified: true

    # Narrative interpretation (grouped)
    narrative:
      who: "Institutional options flow"
      whom: "Dealers"
      what: "Force dealers to hedge - first buying, then selling"
      confidence: 75
      time_horizon: "Intraday"

    # Quantitative evidence (grouped and consolidated)
    quantitative_evidence:
      gex_metrics:
        net_gex_usd: -5386475.71  # Consolidated from total_gamma/net_gex/gex_value
        net_gex_change_1d_usd: -1200000.00  # Issue #80: Velocity signal
        net_gex_change_1d_pct: -28.67       # Issue #80: Velocity signal
        regime: NEGATIVE_GAMMA_LOW
        flip_level_price: 283.10
        spot_price: 472.65

      market_metrics:
        call_gamma: 0
        put_gamma: 0

      outcome_metrics:  # Populated by backtest script
        forward_1d_return_pct: 0.45
        forward_3d_realized_vol: 0.012
        prediction_materialized: true
        verification_note: "Price bounced as dealers covered shorts"
  # ... more detections ...

failed_dates:
  - "2024-01-15"
  - "2024-02-03"
```

### Key Changes (Issue #80)

1. **Performance Metrics** (renamed from detection_metrics):
   - `detection_rate_pct` (renamed from success_rate_pct) - pattern found
   - `predictive_accuracy_pct` - prediction actually worked
   - `net_alpha_pct` - economic profitability after costs

2. **Velocity Metrics** (GEX day-over-day changes):
   - `net_gex_change_1d_usd` - absolute change
   - `net_gex_change_1d_pct` - percentage change

3. **Grouped Structure**:
   - `narrative` - interpretation (who/whom/what)
   - `quantitative_evidence` - data (gex_metrics, market_metrics, outcome_metrics)

4. **Consolidated GEX Fields**:
   - Single `net_gex_usd` replaces redundant fields

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

- **Validation Script**: `scripts/validation/paper1/02_validate_pattern_taxonomy.py`
- **Batch Validation**: `scripts/validation/paper1/03_validate_all_patterns.py`
- **Pattern Framework**: `src/validation/pattern_taxonomy.py`
- **Obfuscation**: `src/validation/data_obfuscation.py`
- **Baseline Strategy**: `src/analysis/baseline_gex_strategy.py`
- **Config**: `config_defaults/trading_config.yaml`
- **Output**: `reports/validation/pattern_taxonomy/`
