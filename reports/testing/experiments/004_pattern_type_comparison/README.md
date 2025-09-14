# Experiment 004: Pattern Type Comparison

## Experiment Definition
**Objective**: Compare performance of different GEX pattern types to identify the most reliable trading signals.

## Why This Test
- **Current Problem**: Only GAMMA_TRAP validated, other patterns unexplored
- **Opportunity**: Multiple pattern types could increase sample size and diversification
- **Business Impact**: Portfolio of patterns could smooth returns and increase opportunities

## Methodology

### Pattern Types to Test
1. **GAMMA_TRAP**: Original contrarian pattern (validated)
2. **GAMMA_SQUEEZE**: Low GEX before volatility events
3. **GAMMA_UNWIND**: Post-OpEx dealer repositioning
4. **GAMMA_FLIP**: Zero-gamma crossing events
5. **GAMMA_PIN**: OpEx pinning with high OI

### Data Inputs
- **Symbol**: SPY (primary testing)
- **Date Range**: 2015-01-01 to 2024-12-31
- **Detection Parameters**: 
  - Confidence thresholds: 65-75% (pattern-specific)
  - Holding periods: 1-5 days (optimized per pattern)

### Calculation Method
1. **Pattern-Specific Optimization**:
   ```python
   for pattern_type in PATTERN_TYPES:
       best_params = optimize_parameters(pattern_type)
       results = backtest_pattern(pattern_type, best_params)
       scores[pattern_type] = calculate_score(results)
   ```

2. **Comparative Metrics**:
   - Win rate comparison
   - Expected value ranking
   - Sharpe ratio analysis
   - Correlation matrix (diversification potential)

3. **Portfolio Construction**:
   - Equal weight portfolio
   - Risk-parity portfolio
   - Optimal weight calculation

## Test Execution

### Script
```bash
python src/testing/pattern_comparison_test.py \
  --symbol SPY \
  --patterns ALL \
  --start-date 2015-01-01 \
  --end-date 2024-12-31 \
  --optimize True
```

### Expected Outputs
1. `pattern_results/` - Individual pattern performance
   - `gamma_trap_results.json`
   - `gamma_squeeze_results.json`
   - `gamma_unwind_results.json`
   - `gamma_flip_results.json`
   - `gamma_pin_results.json`
2. `comparison_matrix.csv` - Side-by-side comparison
3. `correlation_analysis.json` - Pattern correlation matrix
4. `portfolio_results.json` - Combined portfolio performance
5. `optimization_log.csv` - Parameter optimization results

## Success Criteria
- ✅ At least 3 patterns with positive expected value
- ✅ Combined sample size > 50 trades
- ✅ Portfolio Sharpe > individual patterns
- ✅ Low correlation between patterns (<0.5)

## Expected Results

### Individual Pattern Performance
| Pattern        | Expected Samples | Target Win Rate | Expected Value | Strategy Type |
|---------------|-----------------|-----------------|----------------|---------------|
| GAMMA_TRAP    | 10-15           | >55%            | >+0.40%        | Contrarian    |
| GAMMA_SQUEEZE | 15-20           | >53%            | >+0.30%        | Volatility    |
| GAMMA_UNWIND  | 12-18           | >54%            | >+0.35%        | Mean Reversion|
| GAMMA_FLIP    | 8-12            | >52%            | >+0.25%        | Momentum      |
| GAMMA_PIN     | 10-15           | >56%            | >+0.45%        | Pinning       |

### Portfolio Metrics
- **Total Opportunities**: 50-80 trades per year
- **Portfolio Win Rate**: >54%
- **Portfolio Expected Value**: >+0.35%
- **Portfolio Sharpe**: >0.5
- **Max Correlation**: <0.5

### Ranking (Expected)
1. **GAMMA_PIN**: Highest win rate (OpEx edge)
2. **GAMMA_TRAP**: Most validated (contrarian)
3. **GAMMA_UNWIND**: Post-event clarity
4. **GAMMA_SQUEEZE**: Volatility expansion
5. **GAMMA_FLIP**: Trend following

## Optimization Parameters

### Per Pattern
| Pattern        | Confidence Range | Holding Days | Risk/Reward |
|---------------|-----------------|--------------|-------------|
| GAMMA_TRAP    | 70-75%          | 2 days       | 1:1.5       |
| GAMMA_SQUEEZE | 65-70%          | 3 days       | 1:2.0       |
| GAMMA_UNWIND  | 65-70%          | 2 days       | 1:1.5       |
| GAMMA_FLIP    | 70-75%          | 1 day        | 1:1.0       |
| GAMMA_PIN     | 65-70%          | 1 day        | 1:1.2       |

## Files in This Experiment
- `README.md` - This documentation
- `inputs/` - Pattern definitions and parameters
- `outputs/`
  - `pattern_results/` - Individual pattern results
  - `comparison/` - Comparative analysis
  - `portfolio/` - Portfolio construction results
- `optimization/` - Parameter optimization logs
- `visualizations/` - Comparison charts
- `logs/` - Execution logs

## Related Issues
- Issue #43: Expand Testing Sample Size and Coverage
- Issue #6: Pattern Detection Algorithms
- Issue #7: Pattern Mining with LLMs
- Issue #30: Trading Signal Generation