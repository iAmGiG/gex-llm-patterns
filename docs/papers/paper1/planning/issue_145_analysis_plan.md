# Issue #145: EOD Latent Information Analysis - Implementation Plan

**Issue**: [#145 - Temporal Mismatch (0DTE vs EOD Data)](https://github.com/iAmGiG/gex-llm-patterns/issues/145)
**Priority**: P1 (Critical for journal submission)
**Effort**: M (2-3 weeks)
**Status**: Ready to execute
**Date**: November 22, 2025

---

## Objective

**MC's Requirement:**
> "Prove that EOD GEX data contains sufficient 'latent information' to predict T+1 or T+2 market outcomes, independent of the LLM. Provide statistical analysis (e.g., Logit/Probit Regression p-values, R²) proving EOD GEX data has predictive power over T+1 or T+2 market outcomes."

**Defense Goal:**
Validate that the LLM operates on EOD snapshots containing legitimate forward-looking signals about next-day hedging constraints, refuting temporal mismatch criticism.

---

## Analysis Components

### 1. EOD Feature Extraction

**Data Source**: `consolidated_historical.db` → `daily_gex_metrics` table

**Features to Extract (EOD snapshot):**

```python
eod_features = {
    # Primary GEX Metrics
    "net_gex": abs(total_gex),                    # Aggregate gamma exposure magnitude
    "gex_sign": 1 if total_gex < 0 else 0,        # Regime indicator (short gamma)

    # Concentration Metrics
    "gex_concentration": gini_coefficient(gamma_by_strike),  # Gini coefficient
    "concentrated_strikes": count_strikes_with_80pct_gamma,  # Number of dominant strikes
    "max_gamma_pct": max_strike_gamma / sum_all_gamma,       # Largest strike concentration

    # Strike Positioning
    "zero_gamma_proximity": abs(spot - gamma_flip_point) / spot,  # Distance to flip point
    "spot_above_flip": 1 if spot > gamma_flip_point else 0,      # Positioning indicator
    "max_gamma_strike_dist": abs(spot - max_gamma_strike) / spot, # Distance to max gamma

    # Options Activity
    "put_call_gex_ratio": sum(put_gamma) / sum(call_gamma),  # Directional bias
    "oi_volume_ratio": total_oi / daily_volume,              # Institutional vs retail
    "total_oi": sum(open_interest),                          # Overall positioning

    # Volatility Context
    "vix_level": vix_close,                       # Market volatility expectation
    "gex_vix_ratio": abs(net_gex) / vix_close,    # Gamma exposure relative to vol
}
```

**Implementation:**

- Function: `extract_eod_features(date: str) -> Dict`
- Query consolidated database for each trading day in 2024
- Calculate derived metrics (Gini, concentration, ratios)
- Store in DataFrame with date index

**Expected Dataset:**

- Rows: N=242 (all detection-eligible days from 2024)
- Columns: 13 EOD features + date
- Format: pandas DataFrame for sklearn compatibility

---

### 2. Next-Day Outcome Targets

**Data Source**: Daily OHLCV data (already available in database)

**Binary Targets (T+1 materialization):**

```python
next_day_outcomes = {
    # Volatility Targets
    "high_volatility": realized_vol_t1 > 1.2 * forecast_vol_t0,
    "range_expansion": (high_t1 - low_t1) > 1.3 * avg_range_5d,

    # Directional Targets
    "directional_move": abs(return_t1) > 0.5,  # >0.5% absolute move
    "gap_move": abs(open_t1 - close_t0) / close_t0 > 0.3,  # >0.3% gap

    # Strike Convergence Target
    "strike_convergence": min(abs(close_t1 - strike)) / close_t1 < 0.005,  # Within 0.5%

    # Aggregate Target
    "any_materialization": any of above = True
}
```

**Continuous Targets (for regression):**

```python
next_day_continuous = {
    "realized_volatility": sqrt(252 * (return_t1)^2),  # Annualized
    "intraday_range_pct": (high_t1 - low_t1) / open_t1 * 100,
    "abs_return_pct": abs((close_t1 - open_t1) / open_t1) * 100,
}
```

**Implementation:**

- Function: `calculate_next_day_targets(date: str) -> Dict`
- Fetch T+1 OHLCV data for each EOD date
- Calculate binary flags and continuous metrics
- Handle edge cases (end of quarter, holidays)

**Expected Dataset:**

- Rows: N=242 (matching EOD features)
- Columns: 6 binary targets + 3 continuous targets
- Format: pandas DataFrame aligned with features by date

---

### 3. Logistic Regression Analysis

**Primary Model: Binary Classification**

```python
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import TimeSeriesSplit

# Target: any_materialization (primary success metric)
X = eod_features_df[feature_columns]
y = next_day_outcomes_df["any_materialization"]

# Time-series cross-validation (no lookahead bias)
tscv = TimeSeriesSplit(n_splits=5)

# Train model
model = LogisticRegression(
    penalty='l2',
    C=1.0,
    solver='lbfgs',
    max_iter=1000,
    random_state=42
)

# Cross-validated AUC
auc_scores = []
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model.fit(X_train, y_train)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    auc_scores.append(auc)

mean_auc = np.mean(auc_scores)
std_auc = np.std(auc_scores)

# Expected: AUC 0.70-0.75 (strong predictive power)
```

**Feature Importance Analysis:**

```python
# Coefficient-based importance
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'coefficient': model.coef_[0],
    'abs_coefficient': np.abs(model.coef_[0])
}).sort_values('abs_coefficient', ascending=False)

# SHAP values for non-linear importance
import shap
explainer = shap.Explainer(model, X_train)
shap_values = explainer(X_test)

# Expected top features:
# 1. net_gex (aggregate constraint)
# 2. gex_concentration (pinning vs distributed)
# 3. zero_gamma_proximity (flip point risk)
```

**Statistical Tests:**

```python
# Individual predictor p-values
from scipy.stats import chi2

# Likelihood ratio test for each feature
def likelihood_ratio_test(full_model, reduced_model, df=1):
    lr_stat = -2 * (reduced_model.score() - full_model.score())
    p_value = 1 - chi2.cdf(lr_stat, df)
    return p_value

# p-values for each feature
p_values = {}
for feature in feature_columns:
    reduced_features = [f for f in feature_columns if f != feature]
    reduced_model = LogisticRegression().fit(X[reduced_features], y)
    p_values[feature] = likelihood_ratio_test(model, reduced_model)
```

---

### 4. Comparison to LLM Detection

**Objective**: Does LLM outperform statistical baseline?

```python
# Load LLM detections from validation YAMLs
llm_detections = load_gamma_positioning_detections_2024()  # N=242

# LLM binary predictions
llm_predictions = llm_detections["pattern_detected"]  # Boolean

# LLM confidence scores (for probability-based AUC)
llm_confidence = llm_detections["confidence"] / 100  # 0-1 scale

# Calculate LLM AUC
llm_auc = roc_auc_score(
    next_day_outcomes_df["any_materialization"],
    llm_confidence
)

# Compare to statistical model
comparison = {
    "Statistical Model AUC": statistical_auc,
    "LLM Detection AUC": llm_auc,
    "Difference": llm_auc - statistical_auc,
    "Interpretation": "LLM adds value" if llm_auc > statistical_auc else "LLM replicates stats"
}

# Expected:
# Statistical: ~0.70-0.72
# LLM: ~0.75-0.78 (outperforms by 5+ points)
```

**Interpretation Matrix:**

| Statistical AUC | LLM AUC | Interpretation |
|----------------|---------|----------------|
| < 0.60 | Any | EOD data insufficient (HIGH RISK) |
| 0.60-0.70 | > Statistical | LLM adds value, EOD partially valid |
| > 0.70 | > Statistical | Strong defense (EOD valid, LLM enhances) |
| > 0.70 | ≈ Statistical | Good defense (LLM replicates valid signals) |
| > 0.70 | < Statistical | Concerning (LLM underperforms simple model) |

---

### 5. Overnight Constraint Persistence Analysis

**Objective**: Validate EOD gamma correlates with next-day open gamma

**Note**: This requires next-day open options chain data, which may not be available.

**Alternative Proxy**: Correlation between EOD GEX and next-day opening volatility/gap

```python
# Overnight persistence metrics
overnight_metrics = {
    "eod_gex_t0": abs(net_gex_t0),
    "opening_gap_t1": abs(open_t1 - close_t0) / close_t0,
    "opening_vol_t1": realized_vol_first_30min_t1,  # If available
}

# Correlation analysis
correlation = np.corrcoef(
    overnight_metrics["eod_gex_t0"],
    overnight_metrics["opening_gap_t1"]
)[0, 1]

# Expected: correlation > 0.4 (moderate to strong persistence)
```

**Interpretation:**

- Correlation > 0.5: Strong overnight persistence (validates EOD snapshot)
- Correlation 0.3-0.5: Moderate persistence (acceptable)
- Correlation < 0.3: Weak persistence (raises concerns about temporal scope)

---

## Implementation Checklist

### Phase 1: Data Preparation (3-4 days)

- [ ] **Day 1**: Extract EOD features from consolidated_historical.db (N=242)
  - Query daily_gex_metrics table for all 2024 detection days
  - Calculate Gini coefficient for GEX concentration
  - Calculate all derived metrics (ratios, distances, positioning)
  - Store in `eod_features_2024.csv`

- [ ] **Day 2**: Calculate next-day outcome targets
  - Query OHLCV data for T+1 for each date
  - Calculate binary materialization flags
  - Calculate continuous metrics (realized vol, range, returns)
  - Store in `next_day_outcomes_2024.csv`

- [ ] **Day 3**: Load LLM detections from existing validation YAMLs
  - Extract gamma_positioning pattern detections
  - Parse confidence scores, materialization flags
  - Align by date with EOD features
  - Store in `llm_detections_2024.csv`

- [ ] **Day 4**: Data validation and alignment
  - Verify all dates match across datasets
  - Handle missing data (holidays, gaps)
  - Create master dataset (features + targets + LLM)
  - Quality checks (no lookahead, no NaNs)

### Phase 2: Statistical Analysis (4-5 days)

- [ ] **Day 5**: Logistic regression baseline
  - Train model on primary target (any_materialization)
  - Time-series cross-validation (5 folds)
  - Calculate mean AUC and confidence interval
  - Generate ROC curve

- [ ] **Day 6**: Feature importance analysis
  - Extract logistic regression coefficients
  - Calculate SHAP values for non-linear importance
  - Run likelihood ratio tests for p-values
  - Rank features by predictive power

- [ ] **Day 7**: Individual target analysis
  - Separate models for each binary target:
    - high_volatility
    - range_expansion
    - directional_move
    - strike_convergence
  - Compare AUCs across targets
  - Identify which EOD features predict which outcomes

- [ ] **Day 8**: LLM comparison analysis
  - Calculate LLM AUC using confidence scores
  - Compare to statistical baseline
  - Analyze where LLM outperforms/underperforms
  - Generate comparative ROC curves

- [ ] **Day 9**: Overnight persistence analysis
  - EOD GEX correlation with next-day opening gaps
  - Regime stability analysis (negative gamma persistence)
  - Constraint window characterization

### Phase 3: Visualization & Documentation (3-4 days)

- [ ] **Day 10**: Create primary figures
  - ROC curves (Statistical vs LLM vs Random)
  - Feature importance bar chart (top 10 predictors)
  - Confusion matrix heatmaps
  - AUC comparison plot

- [ ] **Day 11**: Statistical results tables
  - Logistic regression coefficients and p-values
  - AUC scores by target and model
  - Feature importance rankings
  - Model performance metrics (precision, recall, F1)

- [ ] **Day 12**: Analysis documentation
  - Write `docs/papers/paper1/analysis/issue_145_eod_predictive_analysis.md`
  - Document methodology, findings, interpretation
  - Include all tables and figures
  - Provide recommendations for paper updates

- [ ] **Day 13**: LaTeX table generation
  - Create `table_eod_logistic_regression.tex`
  - Create `table_feature_importance.tex`
  - Create `table_model_comparison.tex`
  - Format for IEEE two-column template

### Phase 4: Paper #1 Updates (2-3 days)

- [ ] **Day 14**: Methodology section update
  - Add subsection: "Temporal Resolution and Information Content"
  - Present EOD→T+1/T+2 scope clearly
  - Include logistic regression validation results
  - File: `04_Experimental_setup.tex`

- [ ] **Day 15**: Results section update
  - Add paragraph: "EOD Predictive Power Analysis"
  - Present AUC results (statistical and LLM)
  - Show feature importance findings
  - File: `05_Results.tex`

- [ ] **Day 16**: Discussion/Limitations update
  - Clarify temporal limitation (EOD vs intraday)
  - Frame overnight constraint as valid contribution
  - Acknowledge intraday extension as future work
  - File: `06_Discussion.tex`

---

## Deliverables

### 1. Analysis Script

**File**: `scripts/validation/paper1/eod_latent_information_analysis.py`

**Functions:**

- `extract_eod_features(db_path, year=2024) -> DataFrame`
- `calculate_next_day_targets(eod_dates, db_path) -> DataFrame`
- `train_logistic_regression(X, y) -> (model, metrics)`
- `calculate_feature_importance(model, X, y) -> DataFrame`
- `compare_to_llm_detection(statistical_preds, llm_preds, targets) -> Dict`
- `generate_visualizations(results) -> None`

**Usage:**

```bash
# Run full analysis
python scripts/validation/paper1/eod_latent_information_analysis.py \
    --year 2024 \
    --output-dir docs/papers/paper1/analysis/ \
    --generate-figures
```

### 2. Data Files

- `docs/papers/paper1/analysis/eod_features_2024.csv` - EOD predictor features
- `docs/papers/paper1/analysis/next_day_outcomes_2024.csv` - T+1 targets
- `docs/papers/paper1/analysis/llm_detections_2024.csv` - LLM predictions for comparison

### 3. Results Documentation

**File**: `docs/papers/paper1/analysis/issue_145_eod_predictive_analysis.md`

**Structure:**

1. Executive Summary
2. Methodology
3. Feature Extraction Details
4. Logistic Regression Results
5. Feature Importance Analysis
6. LLM Comparison
7. Overnight Persistence Analysis
8. Recommendations for Paper #1
9. Appendix (Full statistical tables)

### 4. Visualizations

**Directory**: `docs/papers/paper1/figures/`

**Files:**

- `issue_145_roc_curves.png` - Statistical vs LLM vs Random baseline
- `issue_145_feature_importance.png` - Top 10 EOD predictors
- `issue_145_overnight_persistence.png` - EOD GEX correlation with T+1 gaps
- `issue_145_auc_comparison.png` - Model performance comparison

### 5. LaTeX Tables

**Directory**: `docs/papers/paper1/tables/`

**Files:**

- `table_eod_logistic_regression.tex` - Coefficients, p-values, AUC
- `table_feature_importance.tex` - Ranked predictive features
- `table_model_comparison.tex` - Statistical vs LLM performance

### 6. Paper #1 Updates

**Files Modified:**

- `docs/papers/paper1/journal_version/04_Experimental_setup.tex` - Temporal scope subsection
- `docs/papers/paper1/journal_version/05_Results.tex` - EOD predictive power paragraph
- `docs/papers/paper1/journal_version/06_Discussion.tex` - Temporal limitation clarification

---

## Success Criteria

### Minimum Viable Defense

- ✅ Logistic regression AUC > 0.60 (EOD data has predictive power)
- ✅ At least 3 features with p < 0.05 (significant predictors)
- ✅ Paper methodology clearly states "EOD → T+1/T+2" scope

### Strong Defense

- ✅ Logistic regression AUC > 0.70 (strong predictive power)
- ✅ LLM AUC ≥ Statistical AUC (LLM adds value or matches)
- ✅ Overnight correlation > 0.40 (moderate constraint persistence)
- ✅ Top 5 features clearly interpretable (gamma concentration, positioning, etc.)

### Optimal Defense

- ✅ Logistic regression AUC > 0.75 (very strong predictive power)
- ✅ LLM AUC > Statistical AUC + 0.05 (LLM outperforms by 5+ points)
- ✅ Overnight correlation > 0.50 (strong constraint persistence)
- ✅ Net GEX and concentration among top 3 features (validates core hypothesis)

---

## Risk Mitigation

### Risk 1: Low Statistical AUC (< 0.60)

**Symptom**: Logistic regression fails to predict T+1 outcomes from EOD features

**Mitigation Options:**

1. **T+2 Analysis**: Test if predictive power emerges at T+2 (dealer hedging delay)
2. **Regime-Specific Models**: Separate models for high/low GEX environments
3. **Non-Linear Models**: Try Random Forest or Gradient Boosting (may capture interactions)
4. **Feature Engineering**: Add lagged features (T-1, T-2 GEX for momentum)

**Fallback Defense**:

- Reframe as "proof-of-concept with methodological limitations"
- Emphasize qualitative structural reasoning validation (Issue #146)
- Acknowledge intraday data required for full validation (Issue #116 future work)

### Risk 2: LLM Underperforms Statistical Model

**Symptom**: LLM AUC < Statistical AUC (model worse than simple logistic regression)

**Mitigation Options:**

1. **Investigate Non-Detections**: Analyze 74 non-detection days for signal quality
2. **Confidence Calibration**: Check if LLM confidence poorly calibrated (rescale)
3. **Pattern-Specific Analysis**: Gamma positioning may outperform, others underperform
4. **Prompt Optimization**: Test if current prompts suboptimal for statistical prediction

**Defense Strategy**:

- Frame LLM as "interpretable reasoning" not "optimal statistical predictor"
- Statistical model provides validation that signals exist (LLM just interprets them)
- LLM value is explainability + structural reasoning, not maximizing AUC

### Risk 3: Weak Overnight Persistence (< 0.30)

**Symptom**: EOD GEX poorly correlates with next-day opening dynamics

**Mitigation Options:**

1. **Alternative Metrics**: Use full-day T+1 volatility (not just opening gap)
2. **Regime Averaging**: Analyze persistence within negative gamma regime only
3. **Event Filtering**: Remove earnings days, FOMC, major news (exogenous shocks)

**Defense Strategy**:

- Overnight persistence is supportive evidence, not core requirement
- Primary validation is T+1 full-day materialization (already in Paper #1)
- EOD→Close T+1 is valid prediction window regardless of overnight correlation

---

## Timeline Summary

**Total Effort**: 16 days (~3 weeks)

- **Week 1 (Days 1-5)**: Data preparation + logistic regression baseline
- **Week 2 (Days 6-11)**: Feature importance + LLM comparison + overnight analysis
- **Week 3 (Days 12-16)**: Documentation + visualization + Paper #1 updates

**Critical Path**:

1. Extract EOD features (Day 1) → Required for all downstream analysis
2. Logistic regression baseline (Day 5) → Determines if defense viable
3. LLM comparison (Day 8) → Core finding for paper
4. Paper updates (Days 14-16) → Integration into journal version

**Parallelization Opportunities**:

- Visualization (Days 10-11) can start after Day 8 results
- LaTeX table generation (Day 13) can run concurrently with documentation (Day 12)
- Paper updates (Days 14-16) can be drafted while analysis finalizes

---

## Dependencies

**Data Dependencies:**

- ✅ `consolidated_historical.db` with `daily_gex_metrics` table (available)
- ✅ 2024 OHLCV data for T+1 outcome calculation (available)
- ✅ Gamma positioning validation YAMLs for LLM detections (available)

**Code Dependencies:**

- ✅ `src/gex/gex_calculator.py` - GEX calculation utilities (exists)
- ✅ `src/validation/outcome_calculator.py` - Materialization logic (exists)
- ⏳ `scripts/validation/paper1/eod_latent_information_analysis.py` - Need to create

**External Libraries:**

- `scikit-learn` - Logistic regression, cross-validation, metrics
- `shap` - Feature importance analysis
- `matplotlib/seaborn` - Visualization
- `pandas/numpy` - Data manipulation

**No external data acquisition required** - all data already collected for Paper #1.

---

## Next Steps

1. ✅ MC directive documented (GitHub Issue #145)
2. ✅ Implementation plan created (this document)
3. 📅 Begin Phase 1 Day 1: Extract EOD features from consolidated database
4. 📅 Set up script skeleton: `scripts/validation/paper1/eod_latent_information_analysis.py`
5. 📅 Query `daily_gex_metrics` for all 2024 detection-eligible days

**Ready to execute** - awaiting user approval to proceed.
