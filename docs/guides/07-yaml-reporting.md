# YAML Reporting and Data Obfuscation Guide

## Overview

The GEX-LLM system now uses YAML format for all experiment reports with integrated data obfuscation to prevent LLM cheating on known market events.

## Key Features

### 1. Clean Report Structure

- **Filename Format**: `ticker-date-testtype.yaml`
- **Location**: `reports/experiments/`
- **No Timestamps**: Clean, predictable filenames

### 2. Data Obfuscation (Default)

- **Tickers**: SPY → INDEX_1, AAPL → STOCK_A, NVDA → STOCK_E
- **Dates**: 2024-06-28 → Day T+0, Day T+1, etc.
- **Prevents**: LLM from using memorized knowledge of famous events

### 3. YAML Format Benefits

- **Token Efficient**: ~30% fewer tokens than JSON
- **Human Readable**: Clear structure for analysis
- **Structured Data**: Proper field organization

## Usage Examples

### Basic Experiment (Obfuscated by Default)

```bash
python scripts/orchestrate_experiment_yaml.py \
  --experiment "Analyze gamma concentration patterns" \
  --symbol SPY \
  --date 2024-06-28 \
  --test-type gamma_analysis
```

### Disable Obfuscation (Debugging Only)

```bash
python scripts/orchestrate_experiment_yaml.py \
  --experiment "Debug analysis" \
  --symbol SPY \
  --date 2024-06-28 \
  --no-obfuscate
```

## Report Structure

### Complete YAML Report Format

```yaml
metadata:
  experiment:
    description: "Analyze gamma concentration patterns"
    type: gamma_analysis
    ticker: INDEX_1        # Obfuscated from SPY
    date: Day T+0         # Obfuscated from 2024-06-28
    obfuscated: true
  test_rationale:
    date_chosen:
      significance: "Q2 2024 end, quarterly expiration"
      characteristics: "High options volume, rebalancing flows"
      expected_patterns: "Pin risk around major strikes"
    test_purpose: "Analyze dealer hedging dynamics"
    validation_goal: "Verify LLM analyzes without temporal context"

tool_execution:
  plan:
    tools_selected: ["fetch_options_data", "calculate_gamma_exposure"]
    execution_order: ["data_collection", "gex_calculation", "analysis"]
    rationale: "Need options chain and gamma metrics"
  data_sources:
    primary: cache
    type: cached
    api_calls: 0

gex_analysis:
  total_gamma: 8674937175
  spot_price: 530.06
  gamma_concentration: 0.254
  key_strikes: [525, 530, 535]

llm_analysis:
  market_mechanics:
    who: "Aggressive call buyers"
    whom: "Options dealers/market makers"
    what: "Force dealers to hedge by buying shares on upward moves"
    confidence: 85
    time_horizon: "Intraday"

  patterns_detected:
    - pattern: gamma_squeeze
      confidence: 75
      evidence: ["High call gamma concentration"]

  trading_signal:
    action: null          # No fallback signals
    confidence: null
    rationale: null       # Clean when no edge detected

  confidence_reasoning:
    summary: "Strong mechanics identification but insufficient edge"

validation:
  data_quality:
    data_completeness: complete
    options_contracts: 3880
  analysis_quality:
    completeness: 0.67    # 2/3 components (mechanics + patterns)
    confidence: 85        # From mechanics analysis
```

## Obfuscation Mappings

### Standard Ticker Mappings

- `SPY` → `INDEX_1`
- `AAPL` → `STOCK_A`
- `MSFT` → `STOCK_B`
- `GOOGL` → `STOCK_C`
- `AMZN` → `STOCK_D`
- `NVDA` → `STOCK_E`
- `META` → `STOCK_F`
- `TSLA` → `STOCK_G`
- `VXX` → `VOLATILITY_INDEX`

### Date Obfuscation

- First date becomes `Day T+0`
- Subsequent dates: `Day T+1`, `Day T+2`, etc.
- Past dates: `Day T-1`, `Day T-2`, etc.

### Context Obfuscation

- `COVID-19` → `Economic Event A`
- `Federal Reserve` → `Central Bank`
- `2024` → `YEAR`
- `March 2020` → `Period A`

## Test Date Significance

The system documents why specific dates are chosen:

### 2024-06-28

- **Significance**: Q2 2024 end, quarterly expiration
- **Characteristics**: High options volume, rebalancing flows
- **Expected Patterns**: Pin risk around major strikes, gamma concentration

### 2024-03-15

- **Significance**: Triple witching day
- **Characteristics**: Simultaneous expiration of futures and options
- **Expected Patterns**: Elevated gamma exposure, volatility compression

### 2024-01-19

- **Significance**: Monthly OPEX with VIX expiration
- **Characteristics**: VIX futures and SPX options convergence
- **Expected Patterns**: Volatility regime shifts, correlation breaks

## Anti-Cheating Validation

### Purpose

Prevent LLM from using training knowledge of famous events:

- GameStop squeeze (January 2021)
- COVID crash (March 2020)
- Fed announcements
- Earnings events

### Implementation

1. **Automatic Obfuscation**: Default behavior for all experiments
2. **Temporal Sanitization**: Remove year references and event names
3. **Context Stripping**: Generic labels for market events
4. **Validation Metrics**: Track analysis quality independently

## Migration from JSON

### Old Format Issues

- Long filenames with timestamps
- Token-heavy JSON structure
- Scattered report directories
- No obfuscation support

### New Benefits

- Clean `ticker-date-testtype.yaml` filenames
- Unified `reports/experiments/` directory
- Token-efficient YAML format
- Built-in anti-cheating measures
- Structured LLM analysis sections

## Best Practices

1. **Always Use Obfuscation**: Keeps validation honest
2. **Descriptive Experiments**: Clear experiment descriptions
3. **Appropriate Test Types**: Use specific test types for better organization
4. **Regular Cleanup**: Archive old reports periodically

## Troubleshooting

### Obfuscation Not Working

- Check `obfuscated: true` in metadata
- Verify ticker shows as INDEX_1/STOCK_A format
- Ensure date shows as Day T+0 format

### Missing LLM Analysis

- Check validation.analysis_quality.completeness
- Verify mechanics_interpretation exists
- Look for patterns_detected section

### Empty Trading Signals

- Expected behavior when no edge detected
- Shows `action: null` instead of misleading "HOLD"
- Indicates honest analysis without false confidence
