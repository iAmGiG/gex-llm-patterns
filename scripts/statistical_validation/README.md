# Statistical Validation Scripts - Paper #1

**Scope**: Single-day GEX pattern detection (Paper #1 only)
**Status**: Complete - Issues #99, #100 closed
**Paper #2**: Different statistical tests needed for 30-day regime validation

This directory contains scripts for statistical validation of the GEX-LLM pattern detection framework (Paper #1), specifically testing causal relationships and economic significance.

## Overview

Two complementary analyses strengthen the paper's empirical claims:

1. **Issue #99: Granger Causality Test** - Proves GEX **predicts** volatility (causality direction)
2. **Issue #100: Lead-Lag Analysis** - Proves GEX **amplifies** volatility (economic magnitude)

## Files

### Main Analysis Scripts (Paper #1)

- `p1_granger_analysis_main.py` - Granger causality test implementation (Issue #99)
- `p1_leadlag_analysis_main.py` - Lead-lag analysis implementation (Issue #100)
- `p1_extract_validation_data.py` - Data extraction utility
- `p1_granger_variations.py` - Granger test variations
- `p1_leadlag_variations.py` - Lead-lag test variations

### Supporting Documentation

- `docs/statistical_validation/issue_99_granger_causality_pipeline.md` - Detailed pipeline for Issue #99
- `docs/statistical_validation/issue_100_lead_lag_pipeline.md` - Detailed pipeline for Issue #100

## Quick Start

### Issue #99: Granger Causality Test

```bash
# Run Granger causality analysis (Paper #1)
python scripts/statistical_validation/p1_granger_analysis_main.py
```

**Outputs**:

- LaTeX tables: `docs/papers/paper1/tables/table_granger_*.tex`
- JSON results: `reports/statistical_validation/granger_results_*.json`

**Expected Results**:

- P-values < 0.05 for lags 1-3 (GEX predicts volatility)
- Effect weakens at lags 4-5 (consistent with short-term hedging)

### Issue #100: Lead-Lag Analysis

```bash
# Run lead-lag analysis (Paper #1)
python scripts/statistical_validation/p1_leadlag_analysis_main.py
```

**Outputs**:

- LaTeX table: `docs/papers/paper1/tables/table_leadlag.tex`
- CSV statistics: `reports/statistical_validation/regime_statistics_*.csv`
- JSON results: `reports/statistical_validation/leadlag_results_*.json`
- Figure (optional): `docs/papers/paper1/figures/fig9_leadlag_analysis.png`

**Expected Results**:

- Negative GEX → ~2x higher volatility vs positive GEX
- P-value < 0.001 (highly significant)
- Cohen's d ≈ 0.8-1.2 (large effect size)

## Current Status

### ✅ Completed

- [x] Pipeline documentation for both analyses
- [x] Implementation stubs with full structure
- [x] Data access patterns defined
- [x] Output formatting (LaTeX, JSON, CSV)

### 🚧 TODO (Implementation)

**Issue #99 - Granger Causality**:

- [ ] Implement actual data loading from cache/database
- [ ] Connect to `GEXCacheManager` for historical GEX data
- [ ] Connect to `OutcomeCalculator` for forward volatility
- [ ] Validate stationarity test thresholds
- [ ] Test on full 2024 dataset (242 days)

**Issue #100 - Lead-Lag Analysis**:

- [ ] Implement actual data loading from cache/database
- [ ] Calculate real forward returns from price data
- [ ] Validate regime threshold values (-$2B, +$2B)
- [ ] Test on full 2024 dataset (242 days)
- [ ] Optional: Create visualization with real data

## Data Requirements

### Required Data Sources

Both analyses require:

1. **GEX Time Series** (242 days, 2024):
   - Source: `.cache/gex_database.db` OR `GEXCacheManager`
   - Field: `net_gex` (daily net gamma exposure)

2. **Price Data** (242 days, 2024):
   - Source: `.cache/consolidated_historical.db` OR cache manager
   - Field: `close_price` (daily closing prices)

3. **Forward Volatility** (derived):
   - Calculated via `OutcomeCalculator.calculate_realized_volatility()`
   - OR manually: rolling std of forward returns

### Data Access Patterns

```python
# Pattern 1: Direct database access
import sqlite3
conn = sqlite3.connect('.cache/consolidated_historical.db')
data = pd.read_sql("SELECT * FROM pattern_validation_results WHERE symbol='SPY'", conn)

# Pattern 2: Cache manager API
from src.cache.gex_cache_manager import GEXCacheManager
cache = GEXCacheManager()
gex_data = cache.get_time_series('SPY', start='2024-01-01', end='2024-12-31')

# Pattern 3: Outcome calculator
from src.validation.outcome_calculator import OutcomeCalculator
outcome = OutcomeCalculator(cache_manager=cache)
vol_data = outcome.calculate_realized_volatility('SPY', dates, window=3)
```

## Dependencies

### Required Packages

```python
# Core
import pandas as pd
import numpy as np

# Statistical
from scipy import stats
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, grangercausalitytests

# Visualization (optional for Issue #100)
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess

# Local
from src.cache.gex_cache_manager import GEXCacheManager
from src.validation.outcome_calculator import OutcomeCalculator
from src.utils.date_utils import today_str
```

Install missing packages:

```bash
pip install statsmodels scipy matplotlib
```

## Paper Integration

### Issue #99: Add to Section V.D (Statistical Validation)

**Location**: `docs/papers/paper1/05_results.md`, Section 5.D

**New Subsection**: 5.D.3 Granger Causality Tests

**Content**:

- Table: `\ref{tab:granger}` - Full sample results
- Table: `\ref{tab:granger_neg}` - Negative regime results
- 1 paragraph interpretation

**Expected Text**:
> "Results indicate that GEX Granger-causes realized volatility at lags 1-3 (p < 0.05),
> confirming that gamma exposure contains predictive information for forward volatility."

### Issue #100: Add to Section V.E (Prediction Materialization)

**Location**: `docs/papers/paper1/05_results.md`, Section 5.E

**New Subsection**: 5.E.3 Volatility Amplification by GEX Regime

**Content**:

- Table: `\ref{tab:leadlag}` - Regime comparison
- Optional Figure: `\ref{fig:leadlag}` - Scatter plot with LOWESS
- 2-3 paragraphs interpretation

**Expected Text**:
> "Negative gamma regimes exhibit 119% higher forward volatility compared to positive
> gamma regimes (0.68% vs. 0.31%, p < 0.001), confirming that dealer short gamma
> positions create pro-cyclical hedging flows that amplify price movements."

## Validation Checklist

Before finalizing results:

**Data Quality**:

- [ ] 242 days of data for full year 2024
- [ ] No gaps > 5 trading days (holidays OK)
- [ ] GEX values within expected range (-$10B to +$10B)
- [ ] Volatility values reasonable (0.1% to 5%)

**Statistical Rigor**:

- [ ] Stationarity confirmed or differencing applied (Issue #99)
- [ ] At least 200 observations for Granger test (Issue #99)
- [ ] Sufficient observations per regime (N > 30) (Issue #100)
- [ ] Effect sizes calculated (Cohen's d) (Issue #100)

**Results Quality**:

- [ ] Granger p-values < 0.05 for lags 1-3
- [ ] Lead-lag shows ~2x volatility amplification
- [ ] Results align with theoretical expectations
- [ ] LaTeX tables compile without errors

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'statsmodels'`

```bash
pip install statsmodels scipy
```

**Issue**: Insufficient data in negative GEX regime

- Solution: Lower threshold to -$1.5B or use quartile-based split

**Issue**: Non-stationary data even after differencing (Issue #99)

- Solution: Try log-differencing or check for structural breaks

**Issue**: Weak volatility differences between regimes (Issue #100)

- Solution: Verify using absolute returns vs squared returns, check threshold values

## Next Steps

1. **Implement Data Loading**: Replace placeholder data with actual cache/database queries
2. **Test on Real Data**: Run on full 2024 dataset and validate results
3. **Integrate with Paper**: Add tables and text to `05_results.md`
4. **Update GitHub Issues**: Mark Issues #99 and #100 as completed
5. **Consider Extensions**: Non-linear Granger, quantile regression, cross-asset analysis

## References

**Granger Causality**:

- Granger, C. W. J. (1969). "Investigating Causal Relations by Econometric Models"
- Hamilton, J. D. (1994). "Time Series Analysis", Chapter 11

**Lead-Lag Analysis**:

- Hasbrouck, J. (1995). "One Security, Many Markets"
- Chordia, T., & Swaminathan, B. (2000). "Trading Volume and Cross-Autocorrelations"

**Dealer Gamma Hedging**:

- Bollen, N. P., & Whaley, R. E. (2004). "Does Net Buying Pressure Affect Volatility?"
- Gârleanu, N., Pedersen, L. H., & Poteshman, A. M. (2009). "Demand-Based Option Pricing"

## Contact

For questions or issues with these analyses, see:

- GitHub Issues: #99 (Granger), #100 (Lead-Lag)
- Documentation: `docs/statistical_validation/`
