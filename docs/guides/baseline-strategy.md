# Baseline Strategy Documentation

## Overview

The Baseline GEX Strategy provides a mechanical trading approach that trades every negative GEX day without LLM filtering. This serves as a performance baseline to prove whether LLM intelligence adds value.

## Current Status: ✅ Framework Ready for A/B Testing

### What's Complete ✅

1. **Baseline Strategy Implementation**
   - Location: `src/analysis/baseline_gex_strategy.py`
   - Configuration-driven parameters from `config_defaults/`
   - Comprehensive backtesting and metrics calculation

2. **Comparison Framework**
   - Location: `scripts/compare_baseline_vs_llm.py`
   - Ready to compare baseline vs LLM performance
   - Standardized metrics and reporting

3. **Experiment Tracking**
   - Location: `src/utils/experiment_tracker.py`
   - Model-aware naming convention
   - Tracks tool vs prompt model usage

### LLM Configuration

**Current Setup:**

- **Reasoning Model**: O3-mini/O4-mini for pattern analysis
- **Tool Calling**: GPT-4o-mini for function execution
- **Validation**: Data obfuscation prevents LLM memorization
- Need working LLM model first (Issue #62)
- Current LLM cannot perform genuine market mechanics analysis

## Implementation Details

### Configuration Parameters

From `config_defaults/trading_config.yaml`:

```yaml
validated_trading_engine:
  position_sizing:
    conservative_position_pct: 1.5  # 1.5% position size
  risk_management:
    stop_loss_pct: 1.0             # 1% stop loss
    profit_target_pct: 1.5         # 1.5% profit target
    max_holding_days: 2            # 2-day max hold
```

From `config_defaults/analysis_config.yaml`:

```yaml
baseline_comparison:
  expected_baseline_win_rate: 0.43    # 43% win rate expected
  expected_baseline_ev: -0.0028       # -0.28% expected value
  expected_baseline_sharpe: -0.15     # Negative Sharpe ratio
  expected_baseline_drawdown: -0.045  # -4.5% max drawdown
```

**Note (October 2025)**: `baseline_comparison.py` has been updated to load pattern results from validation YAML files (`reports/validation/pattern_taxonomy/*.yaml`) instead of database queries. See Issue #82 for migration details.

### Strategy Logic

**Entry Rule:** Trade contrarian on every day when GEX < 0

- No intelligence filtering
- No pattern recognition
- 100% of negative GEX days generate signals

**Risk Management:** Same parameters as LLM strategy for fair comparison

- Stop loss: 1%
- Profit target: 1.5%
- Max holding: 2 days

### Example Output

```python
baseline = BaselineGEXStrategy()
signals = baseline.generate_signals(gex_data)

# Output:
# Generated 7 baseline signals from 10 days
# Negative GEX days: 7 (70.0%)
```

## Dependencies

### Completed Dependencies ✅

- Issue #53: Simplified data pipeline
- Enhanced MarketMechanicsAgent with robust error handling
- Configuration system ready

### Blocking Dependencies ❌

- **Issue #62**: Model selection research (CRITICAL)
  - Need LLM that works on obfuscated data
  - GPT-4o-mini fails genuine analysis test
  - Must resolve before baseline comparison

## Next Steps

1. **Priority 1:** Complete Issue #62 model research
   - Test GPT-4 Turbo on obfuscated validation
   - Implement hybrid architecture if needed
   - Establish working LLM baseline

2. **Priority 2:** Run actual baseline comparison
   - Use working LLM results vs baseline
   - Generate empirical proof of LLM value
   - Document performance improvements

3. **Priority 3:** Close Issue #58 with real data
   - Prove LLM filtering beats mechanical rules
   - Quantify value added by intelligence

## Key Insight

**Cannot prove LLM value without a working LLM.** The baseline strategy infrastructure is ready, but Issue #62 (model research) is the critical blocker for completing this validation.

The framework proves we can measure LLM value - we just need an LLM that actually works on unbiased data first.
