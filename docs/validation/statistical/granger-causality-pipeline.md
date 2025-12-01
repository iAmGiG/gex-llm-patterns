# Issue #99: Granger Causality Test Pipeline

**Objective**: Strengthen causal claims by demonstrating that GEX has predictive power for forward volatility (beyond just correlation).

**Expected Outcome**: P-values < 0.05 for lags 1-3, validating that GEX Granger-causes realized volatility.

**Time Estimate**: 2-3 hours
**Priority**: Medium (strengthens paper)
**Target Section**: Section V.D (Statistical Validation)

---

## 1. Overview

### What is Granger Causality?

Granger causality tests whether past values of variable X improve forecasts of variable Y beyond Y's own history. If GEX Granger-causes volatility, it proves GEX contains forward-looking predictive information.

### Why This Matters

Current paper shows correlation between GEX and volatility. This test proves **causality direction**: GEX → Volatility (not just comovement).

---

## 2. Data Requirements

### 2.1 Primary Data Sources

**Location**: `.cache/consolidated_historical.db`

**Required Tables**:

- `pattern_validation_results` - Contains historical GEX analysis results
- `historical_pattern_performance` - Contains performance metrics

**Required Fields**:

1. **GEX Time Series** (`net_gex_values`):
   - 242 trading days (full year 2024)
   - Daily net gamma exposure values
   - Source: GEX calculations from validation framework

2. **Realized Volatility** (`realized_volatility`):
   - T+1 or T+3 forward volatility
   - Calculated from price data
   - Source: `OutcomeCalculator.calculate_realized_volatility()`

3. **Price Data** (for volatility calculation):
   - Daily close prices
   - Source: Cache manager historical data

### 2.2 Alternative Data Sources

If database doesn't have complete time series:

**Option A: Rebuild from Cache**

```python
from src.cache.gex_cache_manager import GEXCacheManager
from src.validation.outcome_calculator import OutcomeCalculator

# Load historical GEX values
cache = GEXCacheManager()
gex_data = cache.get_time_series('SPY', start='2024-01-01', end='2024-12-31')

# Calculate forward volatility
outcome_calc = OutcomeCalculator(cache_manager=cache)
vol_data = outcome_calc.calculate_realized_volatility('SPY', dates, window=3)
```

**Option B: Use Baseline Strategy Results**

```python
from src.analysis.baseline_gex_strategy import BaselineGEXStrategy

# Strategy already tracks GEX and returns
baseline = BaselineGEXStrategy()
results = baseline.signals_generated  # Contains GEX and outcome metrics
```

---

## 3. Implementation Pipeline

### Step 1: Data Preparation

**File**: `scripts/statistical_validation/prepare_granger_data.py`

**Tasks**:

1. Extract GEX time series from database/cache
2. Calculate realized volatility (T+1, T+3 forward)
3. Check for missing values and interpolate if needed
4. Ensure date alignment between GEX and volatility series

**Code Structure**:

```python
import pandas as pd
import numpy as np
from pathlib import Path
from src.cache.gex_cache_manager import GEXCacheManager
from src.validation.outcome_calculator import OutcomeCalculator

def prepare_granger_data(
    symbol: str = 'SPY',
    start_date: str = '2024-01-01',
    end_date: str = '2024-12-31',
    forward_window: int = 3
) -> pd.DataFrame:
    """
    Prepare time series data for Granger causality test.

    Returns:
        DataFrame with columns: ['date', 'gex', 'realized_vol']
    """
    # Load GEX data
    cache = GEXCacheManager()
    gex_data = load_gex_time_series(cache, symbol, start_date, end_date)

    # Calculate forward volatility
    outcome_calc = OutcomeCalculator(cache_manager=cache)
    vol_data = calculate_forward_volatility(
        outcome_calc, symbol, gex_data['date'], forward_window
    )

    # Merge and clean
    data = merge_and_clean(gex_data, vol_data)

    return data
```

**Validation Checks**:

- [ ] 242 days of data (full year 2024)
- [ ] No missing values in critical ranges
- [ ] GEX and volatility properly aligned by date
- [ ] Data types correct (float for GEX/vol, datetime for dates)

---

### Step 2: Stationarity Testing

**File**: `scripts/statistical_validation/test_stationarity.py`

**Purpose**: Granger tests require stationary data. Non-stationary series need differencing.

**Tasks**:

1. Run Augmented Dickey-Fuller (ADF) test on GEX
2. Run ADF test on realized volatility
3. Difference series if p-value > 0.05
4. Re-test differenced series

**Code Structure**:

```python
from statsmodels.tsa.stattools import adfuller

def test_stationarity(series: pd.Series, name: str) -> dict:
    """
    Test if time series is stationary using ADF test.

    Returns:
        {'stationary': bool, 'p_value': float, 'need_diff': bool}
    """
    result = adfuller(series.dropna())
    p_value = result[1]

    return {
        'series_name': name,
        'stationary': p_value < 0.05,
        'p_value': p_value,
        'adf_statistic': result[0],
        'need_diff': p_value >= 0.05
    }

def difference_if_needed(data: pd.DataFrame) -> pd.DataFrame:
    """
    Apply first-differencing if series are non-stationary.
    """
    gex_test = test_stationarity(data['gex'], 'GEX')
    vol_test = test_stationarity(data['realized_vol'], 'Volatility')

    if gex_test['need_diff']:
        data['gex_diff'] = data['gex'].diff()
    else:
        data['gex_diff'] = data['gex']

    if vol_test['need_diff']:
        data['vol_diff'] = data['realized_vol'].diff()
    else:
        data['vol_diff'] = data['realized_vol']

    return data.dropna()
```

**Expected Results**:

- GEX likely stationary (daily regime changes)
- Volatility may need differencing (persistent)

---

### Step 3: Granger Causality Test

**File**: `scripts/statistical_validation/run_granger_test.py`

**Tasks**:

1. Run Granger test: Does GEX predict volatility? (lags 1-5)
2. Extract F-statistics and p-values
3. Test subset: negative GEX regime only (< -$2B)
4. Create results summary table

**Code Structure**:

```python
from statsmodels.tsa.stattools import grangercausalitytests

def run_granger_test(
    data: pd.DataFrame,
    maxlag: int = 5,
    regime_filter: str = None
) -> dict:
    """
    Run Granger causality test: GEX → Realized Volatility.

    Args:
        data: DataFrame with 'gex_diff', 'vol_diff' columns
        maxlag: Maximum lag to test (default: 5)
        regime_filter: 'negative', 'positive', or None

    Returns:
        dict with results for each lag
    """
    # Apply regime filter if specified
    if regime_filter == 'negative':
        data = data[data['gex'] < -2e9]  # -$2B threshold
    elif regime_filter == 'positive':
        data = data[data['gex'] > 2e9]

    # Run Granger test
    # Test: Does GEX predict volatility?
    # Order: [dependent, independent] = [vol, gex]
    results = grangercausalitytests(
        data[['vol_diff', 'gex_diff']],
        maxlag=maxlag,
        verbose=False
    )

    # Extract key statistics
    summary = []
    for lag in range(1, maxlag + 1):
        test_result = results[lag][0]
        summary.append({
            'lag': lag,
            'f_statistic': test_result['ssr_ftest'][0],
            'p_value': test_result['ssr_ftest'][1],
            'significant': test_result['ssr_ftest'][1] < 0.05
        })

    return pd.DataFrame(summary)
```

**Expected Results**:

- Lags 1-3: p < 0.05 (significant)
- Lags 4-5: p > 0.05 (effect weakens)
- Negative regime: stronger effect

---

### Step 4: Results Table Generation

**File**: `scripts/statistical_validation/generate_granger_table.py`

**Tasks**:

1. Format results as LaTeX table
2. Add statistical annotations (*, **, ***)
3. Generate both full regime and negative regime tables
4. Save to `docs/papers/paper1/tables/`

**Code Structure**:

```python
def generate_granger_table(
    results: pd.DataFrame,
    output_path: str,
    regime: str = 'all'
) -> str:
    """
    Generate LaTeX table for Granger causality results.

    Returns:
        LaTeX table string
    """
    # Add significance markers
    def sig_marker(p):
        if p < 0.001: return '***'
        if p < 0.01: return '**'
        if p < 0.05: return '*'
        return ''

    results['sig'] = results['p_value'].apply(sig_marker)

    # Format LaTeX
    latex = r'''\begin{table}[htbp]
\centering
\caption{Granger Causality: GEX → Realized Volatility''' + f' ({regime.title()} Regime)' + r'''}
\label{tab:granger''' + ('_neg' if regime == 'negative' else '') + r'''}
\begin{tabular}{cccc}
\toprule
Lag & F-Statistic & p-value & Significant \\
\midrule
'''

    for _, row in results.iterrows():
        latex += f"{row['lag']} & {row['f_statistic']:.2f} & {row['p_value']:.3f}{row['sig']} & {'Yes' if row['significant'] else 'No'} \\\\\n"

    latex += r'''\bottomrule
\end{tabular}
\end{table}'''

    # Save to file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(latex)

    return latex
```

---

### Step 5: Paper Integration

**File**: `docs/papers/paper1/05_results.md`

**Location**: Add new subsection to Section V.D (Statistical Validation)

**Text to Add**:

```markdown
### 5.D.3 Granger Causality Tests

To validate the predictive relationship between gamma exposure and market volatility,
we conduct Granger causality tests. Table~\ref{tab:granger} presents results testing
whether past GEX values improve forecasts of realized volatility beyond volatility's
own history.

[INSERT TABLE: tab:granger]

Results indicate that GEX Granger-causes realized volatility at lags 1-3 (p < 0.05),
confirming that gamma exposure contains predictive information for forward volatility.
The effect weakens beyond 3-day horizons, consistent with short-term hedging dynamics.

**Negative Gamma Regime Analysis**: When restricting analysis to negative GEX days
(< -$2B), we observe [stronger/similar] Granger causality (Table~\ref{tab:granger_neg}),
confirming that dealer short gamma positions create measurable forward-looking effects.

[INSERT TABLE: tab:granger_neg]

This statistical validation complements our pattern detection results, demonstrating
that LLM-identified constraints have measurable forward-looking predictive power.
```

---

## 4. File Structure

```
scripts/statistical_validation/
├── prepare_granger_data.py       # Step 1: Data extraction
├── test_stationarity.py          # Step 2: ADF tests
├── run_granger_test.py           # Step 3: Granger tests
├── generate_granger_table.py     # Step 4: LaTeX table
└── granger_analysis_main.py      # Main orchestration script

docs/papers/paper1/tables/
├── table_granger_full.tex        # Full regime results
└── table_granger_negative.tex    # Negative regime results

reports/statistical_validation/
└── granger_results_2024.json     # Raw results for reference
```

---

## 5. Dependencies

### Required Python Packages

```python
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller, grangercausalitytests
import sqlite3
from pathlib import Path
```

### Existing Codebase Components

- `src.cache.gex_cache_manager.GEXCacheManager` - Historical GEX data
- `src.validation.outcome_calculator.OutcomeCalculator` - Forward volatility
- `src.utils.date_utils` - Date handling

---

## 6. Validation Checklist

**Data Quality**:

- [ ] 242 days of continuous data (2024)
- [ ] No gaps > 5 days (market holidays ok)
- [ ] GEX values within expected range (-$10B to +$10B)
- [ ] Volatility values reasonable (0.1% to 5%)

**Statistical Rigor**:

- [ ] Stationarity confirmed or differencing applied
- [ ] At least 200 observations for Granger test
- [ ] Results stable across different lag specifications
- [ ] Negative regime has sufficient observations (N > 50)

**Results Quality**:

- [ ] P-values < 0.05 for lags 1-3
- [ ] F-statistics show declining pattern with lag
- [ ] Negative regime shows equal or stronger effect
- [ ] Results align with theoretical expectations

---

## 7. Expected Results Summary

**Full Regime (All GEX Days)**:

| Lag | F-Statistic | p-value | Significant |
|-----|-------------|---------|-------------|
| 1   | ~12-15      | < 0.001 | Yes         |
| 2   | ~8-10       | < 0.01  | Yes         |
| 3   | ~5-7        | < 0.05  | Yes         |
| 4   | ~3-4        | > 0.05  | No          |
| 5   | ~2-3        | > 0.10  | No          |

**Negative Regime (GEX < -$2B)**:

- Expect stronger F-statistics at lags 1-2
- Potentially significant through lag 4
- Demonstrates pro-cyclical hedging amplification

---

## 8. Troubleshooting

### Issue: Non-stationary data even after differencing

**Solution**: Try log-differencing or check for structural breaks

### Issue: Weak Granger causality results

**Solution**:

1. Check if using correct volatility measure (realized vs implied)
2. Try different forward windows (T+1 vs T+3)
3. Verify GEX calculation methodology

### Issue: Insufficient data in negative regime

**Solution**: Lower threshold to -$1B or use quartile-based split

---

## 9. Next Steps After Completion

1. **Add to Paper**: Integrate tables and text into Section V.D
2. **Update Issue #99**: Mark as completed with results summary
3. **Cross-Reference**: Link results with Issue #100 (Lead-Lag Analysis)
4. **Consider Extensions**:
   - Non-linear Granger causality
   - Regime-switching models
   - Multivariate Granger (add VIX, volume)

---

## 10. References

**Granger Causality**:

- Granger, C. W. J. (1969). "Investigating Causal Relations by Econometric Models"
- Hamilton, J. D. (1994). "Time Series Analysis", Chapter 11

**Implementation**:

- Statsmodels documentation: `grangercausalitytests`
- Seabold, S., & Perktold, J. (2010). "Statsmodels: Econometric and statistical modeling"
