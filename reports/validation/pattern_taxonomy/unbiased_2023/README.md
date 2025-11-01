# 2023 Unbiased Validation Results (Placeholder)

**Status**: Not yet collected
**Issue**: #103 - Extend Historical Data to Full Year 2023

## Target

- **Trading Days**: 252 (full year 2023)
- **Patterns**: gamma_positioning, stock_pinning, 0dte_hedging
- **Expected Detection**: 70-80%
- **Expected Accuracy**: 93-95%

## Generation Command

```bash
for pattern in gamma_positioning stock_pinning 0dte_hedging; do
  python scripts/validation/validate_pattern_taxonomy.py \
    --pattern $pattern \
    --symbol SPY \
    --start-date 2023-01-03 \
    --end-date 2023-12-29 \
    --prompt-template unbiased \
    --with-outcomes \
    --output-dir reports/validation/pattern_taxonomy/unbiased_2023
done
```

## Why 2023 Matters

- Different market regime (moderate volatility, VIX avg ~15)
- Banking crisis (March 2023)
- Tests pattern robustness across regime shifts
