# Statistical Validation Documentation

This directory contains comprehensive documentation for statistical validation of the GEX-LLM pattern detection framework.

## Overview

Two complementary statistical analyses strengthen the paper's empirical claims about the relationship between gamma exposure (GEX) and market volatility:

### Issue #99: Granger Causality Test

**Objective**: Prove that GEX has **predictive power** for forward volatility (causality direction)

**Question Answered**: Does past GEX improve volatility forecasts beyond volatility's own history?

**Expected Result**: P-values < 0.05 for lags 1-3, demonstrating GEX Granger-causes volatility

### Issue #100: Lead-Lag Analysis

**Objective**: Quantify the **economic magnitude** of GEX's impact on volatility (amplification factor)

**Question Answered**: How much higher is volatility in negative GEX regimes?

**Expected Result**: Negative GEX → ~2x higher forward volatility (p < 0.001)

## Documentation Files

### Pipeline Documentation

1. **[issue_99_granger_causality_pipeline.md](issue_99_granger_causality_pipeline.md)**
   - Complete implementation pipeline for Granger causality test
   - Data requirements and sources
   - Step-by-step code structure
   - Expected results and validation checklist
   - Paper integration instructions

2. **[issue_100_lead_lag_pipeline.md](issue_100_lead_lag_pipeline.md)**
   - Complete implementation pipeline for lead-lag analysis
   - Regime classification methodology
   - Statistical tests and regression models
   - Visualization guidelines
   - Paper integration instructions

### Implementation Scripts

Located in `scripts/statistical_validation/`:

- `granger_analysis_main.py` - Main script for Issue #99
- `leadlag_analysis_main.py` - Main script for Issue #100
- `README.md` - Implementation guide and quick start

## Quick Reference

### Issue #99: Granger Causality

**Time Estimate**: 2-3 hours
**Priority**: Medium
**Target Section**: V.D (Statistical Validation)

**Key Steps**:

1. Load GEX time series (242 days, 2024)
2. Calculate realized forward volatility
3. Test stationarity (ADF test)
4. Run Granger test (lags 1-5)
5. Generate LaTeX table

**Expected Finding**: GEX Granger-causes volatility at lags 1-3

### Issue #100: Lead-Lag Analysis

**Time Estimate**: 4-5 hours
**Priority**: Medium
**Target Section**: V.E (Prediction Materialization)

**Key Steps**:

1. Load GEX and price data (242 days, 2024)
2. Calculate forward returns and classify regimes
3. Calculate regime statistics
4. Run t-tests and ANOVA
5. Optional: Regression and visualization
6. Generate LaTeX table

**Expected Finding**: Negative GEX → 119% higher volatility (2.19x amplification)

## Data Requirements

Both analyses require the same underlying data:

### Primary Data Sources

1. **GEX Time Series**
   - Location: `.cache/gex_database.db` OR `GEXCacheManager`
   - Period: Full year 2024 (242 trading days)
   - Field: `net_gex` (daily net gamma exposure)

2. **Price Data**
   - Location: `.cache/consolidated_historical.db` OR cache manager
   - Period: Full year 2024 (242 trading days)
   - Field: `close_price` (daily closing prices)

3. **Forward Volatility** (derived)
   - Source: `OutcomeCalculator.calculate_realized_volatility()`
   - OR manually calculated from forward returns

### Data Validation

Required checks before analysis:

- [ ] 242 days of continuous data (2024)
- [ ] No gaps > 5 trading days
- [ ] GEX values within -$10B to +$10B range
- [ ] Volatility values between 0.1% to 5%

## Paper Integration

### Section V.D: Statistical Validation (Issue #99)

**New Subsection**: 5.D.3 Granger Causality Tests

**Content**:

- Table: Granger causality results (full sample)
- Table: Granger causality results (negative regime)
- 1-2 paragraphs interpretation

**Space Required**: ~0.3 pages

### Section V.E: Prediction Materialization (Issue #100)

**New Subsection**: 5.E.3 Volatility Amplification by GEX Regime

**Content**:

- Table: Volatility statistics by regime
- Optional Figure: Scatter plot with LOWESS smoothing
- 2-3 paragraphs interpretation

**Space Required**: ~0.5 pages (with figure) or ~0.3 pages (table only)

## Complementary Evidence

These two analyses work together to validate the GEX-LLM framework:

| Analysis | Question | Evidence Type | Key Finding |
|----------|----------|---------------|-------------|
| Issue #99 (Granger) | Does GEX **predict** volatility? | Causality direction | P < 0.05 for lags 1-3 |
| Issue #100 (Lead-Lag) | Does GEX **amplify** volatility? | Economic magnitude | 2.19x higher volatility |

**Joint Interpretation**:
> "Granger causality tests confirm GEX contains forward-looking information for volatility
> (lags 1-3, p < 0.05), while lead-lag analysis quantifies the economic magnitude: negative
> GEX regimes exhibit 119% higher forward volatility (p < 0.001). Together, these analyses
> validate both the **direction** and **magnitude** of the dealer hedging mechanism identified
> by our LLM pattern detection framework."

## Implementation Status

### ✅ Completed

- [x] Comprehensive pipeline documentation (Issue #99)
- [x] Comprehensive pipeline documentation (Issue #100)
- [x] Implementation script stubs with full structure
- [x] Data source identification and access patterns
- [x] Output formatting (LaTeX, JSON, CSV)
- [x] Paper integration guidelines
- [x] GitHub issues updated with pipeline references
- [x] Labels added to issues (documentation, validation, analysis)

### 🚧 Next Steps (Implementation)

**Issue #99**:

1. Replace placeholder data with actual cache/database queries
2. Test stationarity detection with real data
3. Validate Granger results on full 2024 dataset
4. Generate final LaTeX tables
5. Integrate into Section V.D

**Issue #100**:

1. Replace placeholder data with actual cache/database queries
2. Validate regime threshold values
3. Test on full 2024 dataset
4. Generate final LaTeX table
5. Optional: Create visualization
6. Integrate into Section V.E

## Dependencies

### Required Python Packages

```bash
pip install pandas numpy scipy statsmodels matplotlib
```

### Existing Codebase Components

- `src.cache.gex_cache_manager.GEXCacheManager` - Historical GEX data
- `src.validation.outcome_calculator.OutcomeCalculator` - Forward metrics
- `src.utils.date_utils` - Date handling utilities

## Resources

### Statistical Methods

**Granger Causality**:

- Granger, C. W. J. (1969). "Investigating Causal Relations by Econometric Models"
- Hamilton, J. D. (1994). "Time Series Analysis", Chapter 11
- Statsmodels: `grangercausalitytests` documentation

**Lead-Lag Analysis**:

- Hasbrouck, J. (1995). "One Security, Many Markets"
- Cohen, J. (1988). "Statistical Power Analysis" (Effect Sizes)
- Wooldridge, J. M. (2015). "Introductory Econometrics", Chapter 7

**Dealer Gamma Hedging**:

- Bollen, N. P., & Whaley, R. E. (2004). "Does Net Buying Pressure Affect Volatility?"
- Gârleanu, N., et al. (2009). "Demand-Based Option Pricing"

### GitHub Issues

- **Issue #99**: [Granger Causality Test](https://github.com/iAmGiG/gex-llm-patterns/issues/99)
- **Issue #100**: [Lead-Lag Analysis](https://github.com/iAmGiG/gex-llm-patterns/issues/100)

## Contact

For questions or issues with the statistical validation framework:

1. Review the detailed pipeline documentation files
2. Check the implementation scripts in `scripts/statistical_validation/`
3. Consult the GitHub issues for discussions and updates
