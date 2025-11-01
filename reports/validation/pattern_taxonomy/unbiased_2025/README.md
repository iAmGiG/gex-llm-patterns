# 2025 Partial Validation Results (Placeholder)

**Status**: Not yet collected
**Issue**: #106 - Collect Partial 2025 Data (Jan 1 - Oct 30)

## Target

- **Trading Days**: ~210 (Jan-Oct 2025)
- **Patterns**: gamma_positioning, stock_pinning, 0dte_hedging
- **Expected Detection**: 65-75%
- **Expected Accuracy**: 88-93%

## Generation Command

```bash
for pattern in gamma_positioning stock_pinning 0dte_hedging; do
  python scripts/validation/validate_pattern_taxonomy.py \
    --pattern $pattern \
    --symbol SPY \
    --start-date 2025-01-02 \
    --end-date 2025-10-31 \
    --prompt-template unbiased \
    --with-outcomes \
    --output-dir reports/validation/pattern_taxonomy/unbiased_2025
done
```

## Why 2025 Matters

- Current market validation
- New administration regime (policy shift)
- Tests real-time applicability
