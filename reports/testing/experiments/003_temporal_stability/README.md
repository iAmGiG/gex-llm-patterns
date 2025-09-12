# Experiment 003: Temporal Stability Testing

## Experiment Definition
**Objective**: Validate pattern performance stability across different time periods and market regimes.

## Why This Test
- **Current Problem**: Pattern might work in some periods but fail in others
- **Risk**: Overfitting to specific market conditions (e.g., bull markets only)
- **Business Impact**: Need confidence pattern works in various market environments

## Methodology

### Data Inputs
- **Time Periods**:
  - 2015-2019: Pre-COVID bull market
  - 2020: COVID crash and recovery
  - 2021: Meme stock mania
  - 2022: Bear market and rate hikes
  - 2023-2024: AI bubble and recovery
- **Market Regimes**:
  - High volatility (VIX > 20)
  - Low volatility (VIX < 15)
  - Trending markets (20-day momentum > 5%)
  - Range-bound markets

### Calculation Method
1. **Period-Specific Analysis**:
   ```python
   for period in time_periods:
       patterns = detect_patterns(period)
       performance = calculate_returns(patterns)
       stability_score = 1 - std(performance) / mean(performance)
   ```

2. **Regime-Specific Performance**:
   - Group patterns by market regime
   - Calculate win rate per regime
   - Test for statistical differences

3. **Rolling Window Analysis**:
   - 6-month rolling windows
   - Track performance consistency
   - Identify degradation periods

## Test Execution

### Script
```bash
python src/testing/temporal_stability_test.py \
  --symbol SPY \
  --start-date 2015-01-01 \
  --end-date 2024-12-31 \
  --window-size 6M
```

### Expected Outputs
1. `period_analysis/` - Results by time period
   - `2015_2019_results.json`
   - `2020_results.json`
   - `2021_results.json`
   - `2022_results.json`
   - `2023_2024_results.json`
2. `regime_analysis/` - Results by market regime
   - `high_volatility_results.json`
   - `low_volatility_results.json`
   - `trending_results.json`
   - `range_bound_results.json`
3. `rolling_performance.csv` - Time series of rolling performance
4. `stability_metrics.json` - Overall stability scores

## Success Criteria
- ✅ Positive expected value in 4/5 time periods
- ✅ Win rate > 50% in at least 3/4 market regimes
- ✅ Rolling Sharpe ratio stays positive 80% of time
- ✅ No period with >3 consecutive losing trades

## Expected Results

### By Time Period
| Period     | Expected Patterns | Target Win Rate | Acceptable EV |
|------------|------------------|-----------------|---------------|
| 2015-2019  | 8-12             | >55%            | >+0.35%       |
| 2020       | 3-5              | >52%            | >+0.25%       |
| 2021       | 4-6              | >54%            | >+0.30%       |
| 2022       | 5-7              | >53%            | >+0.30%       |
| 2023-2024  | 6-8              | >55%            | >+0.40%       |

### By Market Regime
| Regime        | Performance Expectation              |
|---------------|-------------------------------------|
| High Vol      | Best performance (contrarian works) |
| Low Vol       | Moderate performance                |
| Trending      | Weakest (momentum dominates)       |
| Range-bound   | Strong (mean reversion)             |

### Stability Metrics
- **Coefficient of Variation**: <0.5 (moderate consistency)
- **Max Drawdown Period**: <30 days
- **Recovery Time**: <15 days average
- **Regime Robustness**: >0.7 score

## Files in This Experiment
- `README.md` - This documentation
- `inputs/` - Period definitions and parameters
- `outputs/`
  - `period_analysis/` - Time period results
  - `regime_analysis/` - Market regime results
  - `rolling_analysis/` - Rolling window results
- `visualizations/` - Performance charts
- `logs/` - Execution logs

## Related Issues
- Issue #43: Expand Testing Sample Size and Coverage
- Issue #31: Market Regime Classification
- Issue #40: Fed Data Integration (for regime identification)