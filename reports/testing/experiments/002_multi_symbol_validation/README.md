# Experiment 002: Multi-Symbol Validation

## Experiment Definition
**Objective**: Validate GAMMA_TRAP pattern consistency across multiple symbols (SPY, QQQ, IWM) to ensure pattern robustness.

## Why This Test
- **Current Problem**: Pattern only validated on SPY, unknown if it generalizes
- **Risk**: Pattern might be SPY-specific artifact, not universal market behavior
- **Business Impact**: Need cross-market validation for reliable trading signals

## Methodology

### Data Inputs
- **Symbols**: 
  - SPY: S&P 500 ETF (large-cap benchmark)
  - QQQ: NASDAQ 100 ETF (tech-heavy)
  - IWM: Russell 2000 ETF (small-cap)
- **Date Range**: 2015-01-01 to 2024-12-31
- **Data Requirements**: Full options chain with Greeks for each symbol

### Calculation Method
1. **Symbol-Specific Calibration**:
   - Adjust GEX thresholds by average market cap
   - Normalize flip point distances by volatility
   - Account for different liquidity profiles

2. **Cross-Symbol Metrics**:
   ```
   Consistency_Score = Correlation(Pattern_Returns_Symbol1, Pattern_Returns_Symbol2)
   Universal_Win_Rate = Weighted_Average(Win_Rates, by_volume)
   ```

3. **Statistical Tests**:
   - ANOVA for win rate differences across symbols
   - Correlation analysis between symbols
   - Chi-square test for pattern independence

## Test Execution

### Script
```bash
python src/testing/multi_symbol_backtest.py \
  --symbols SPY QQQ IWM \
  --start-date 2015-01-01 \
  --end-date 2024-12-31 \
  --pattern GAMMA_TRAP
```

### Expected Outputs
1. `spy_results_[timestamp].json` - SPY pattern performance
2. `qqq_results_[timestamp].json` - QQQ pattern performance
3. `iwm_results_[timestamp].json` - IWM pattern performance
4. `cross_symbol_analysis_[timestamp].json` - Correlation and consistency metrics

## Success Criteria
- ✅ Pattern detected in all three symbols
- ✅ Win rate > 50% for each symbol
- ✅ Correlation > 0.3 between symbol returns
- ✅ No significant difference in performance (ANOVA p > 0.05)

## Expected Results

### Per Symbol Targets
| Symbol | Min Patterns | Target Win Rate | Expected Value |
|--------|-------------|-----------------|----------------|
| SPY    | 10+         | >55%            | >+0.40%        |
| QQQ    | 10+         | >53%            | >+0.35%        |
| IWM    | 10+         | >52%            | >+0.30%        |

### Cross-Symbol Metrics
- **Pattern Correlation**: >0.30 (moderate consistency)
- **Universal Win Rate**: >54%
- **Robustness Score**: >70%

## Files in This Experiment
- `README.md` - This documentation
- `inputs/` - Symbol lists and parameters
- `outputs/` - Per-symbol results
  - `spy/` - SPY test results
  - `qqq/` - QQQ test results
  - `iwm/` - IWM test results
- `analysis/` - Cross-symbol analysis
- `logs/` - Execution logs

## Related Issues
- Issue #43: Expand Testing Sample Size and Coverage
- Issue #31: Market Regime Classification
- Issue #35: Baseline Comparison System