# Experiment 001: Sample Size Expansion

## Experiment Definition
**Objective**: Expand GAMMA_TRAP pattern detection from 7 samples to 30+ samples to achieve statistical significance.

## Why This Test
- **Current Problem**: Only 7 historical GAMMA_TRAP patterns detected (insufficient for 95% confidence)
- **Statistical Requirement**: Minimum 30 samples needed for Central Limit Theorem assumptions
- **Business Impact**: Cannot deploy to production without statistical validation

## Methodology

### Data Inputs
- **Source Database**: `.cache/consolidated_historical.db`
- **Symbol**: SPY (primary), QQQ and IWM (when available)
- **Date Range**: 2008-01-01 to 2024-12-31 (expanded from original)
- **Data Type**: Daily GEX metrics with options data

### Calculation Method
1. **Pattern Detection Relaxation**:
   - Original: 75% confidence threshold
   - Relaxed: 70% confidence threshold
   - Proximity: 7% of flip point (vs 5% original)
   - Regime: Accept NEUTRAL in addition to NEGATIVE

2. **Expected Value Calculation**:
   ```
   EV = (Win_Rate × Reward) - ((1 - Win_Rate) × Risk)
   Where: Risk = 1%, Reward = 1.5%
   ```

3. **Statistical Tests**:
   - T-test for mean returns vs zero
   - Binomial test for win rate vs 50%
   - 95% confidence intervals

## Test Execution

### Script
```bash
python src/testing/comprehensive_backtest.py \
  --symbols SPY \
  --start-date 2008-01-01 \
  --end-date 2024-12-31 \
  --min-samples 30 \
  --confidence-threshold 0.70
```

### Expected Outputs
1. `results_[timestamp].json` - Full test results with patterns
2. `statistics_[timestamp].csv` - Statistical metrics
3. `patterns_[timestamp].csv` - All detected patterns
4. `validation_[timestamp].json` - Statistical significance tests

## Success Criteria
- ✅ Achieve 30+ pattern samples
- ✅ Statistical significance p-value < 0.05
- ✅ Positive expected value maintained
- ✅ Win rate > 50% for contrarian strategy

## Results Summary

### Current Status (Pre-Expansion)
- **Sample Size**: 7 trades
- **Win Rate**: 57.1%
- **Expected Value**: +0.427%
- **Statistical Significance**: 66.1% (insufficient)

### Target (Post-Expansion)
- **Sample Size**: 30+ trades
- **Win Rate**: >55%
- **Expected Value**: >+0.40%
- **Statistical Significance**: >95%

## Files in This Experiment
- `README.md` - This documentation
- `inputs/` - Input data specifications
- `outputs/` - Test results and statistics
- `logs/` - Execution logs

## Related Issues
- Issue #43: Expand Testing Sample Size and Coverage
- Issue #11: Statistical Validation Framework
- Issue #39: Forward Testing Implementation