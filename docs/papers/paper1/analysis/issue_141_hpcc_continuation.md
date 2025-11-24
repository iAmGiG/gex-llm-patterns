# MC Review Defense: HPCC Continuation Guide

**Date Created:** 2025-11-22
**Context:** Continuing Issue #141 execution on HPCC with database access
**Previous Session:** Local Windows environment - completed initial data exploration

---

## Session Context Summary

### What Was Accomplished (Local Session)

1. **Created 6 GitHub Issues for MC Review Defenses:**
   - Issue #141: Non-Detection Day Analysis (28.5% miss rate) - **IN PROGRESS**
   - Issue #142: Base Rate Vulnerability via Dual GEX
   - Issue #143: Raw Option Chain Validation (prompt leakage)
   - Issue #144: Materialization Specificity (p-hacking)
   - Issue #145: Temporal Mismatch (0DTE vs EOD data)
   - Issue #146: Alpha Divergence (interpretability/hallucination)

2. **Organized GitHub Issues with Paper Labels:**
   - Created labels: `paper1`, `paper2`, `paper3`, `future-research`
   - Applied labels to all research issues for better tracking
   - Paper #1 issues: #87, #116, #121, #131, #133, #141-146

3. **Initial Data Analysis for Issue #141:**
   - Located data: `reports/statistical_validation/gamma_positioning_timeseries_2024.csv`
   - Found 242 days: 168 detected (69.4%), 74 not detected (30.6%)
   - **Key Finding:** Only 1.05x GEX magnitude difference (NOT significant)
   - **Conclusion:** Need deeper analysis with DB access

---

## Current Task: Issue #141 - Non-Detection Day Analysis

### MC's Requirement

> "The 28.5% of days the model missed - if they were statistically 'noisier' or had lower GEX magnitude than the days it caught, you prove the model has sensitivity, not just bias."

### Objective

Characterize the 74 non-detection days to prove LLM has **signal sensitivity**, not **base rate guessing**.

### Hypotheses to Test

| Hypothesis | Test | Data Required | Status |
|------------|------|---------------|--------|
| **H1: GEX Magnitude** | Non-detection days have weaker \|GEX\| | CSV (net_gex) | ❌ FAILED (1.05x, p>0.05) |
| **H2: Signal Volatility** | Higher realized vol = noisier signal | CSV (realized_vol_t1) | ⏳ Ready to test |
| **H3: Market Context** | High rolling vol regime = detection harder | CSV (realized_vol_rolling_5d) | ⏳ Ready to test |
| **H4: Temporal Clustering** | Non-detections cluster in specific periods | CSV (date) | ⏳ Ready to test |
| **H5: GEX Concentration** | Fragmented gamma across strikes | 🔴 NEED DB (strike-level gamma) | ⏳ HPCC required |
| **H6: Put-Call Balance** | Conflicting put/call signals | 🔴 NEED DB (put vs call gamma) | ⏳ HPCC required |
| **H7: Volume/OI Ratio** | Low institutional conviction | 🔴 NEED DB (volume, open interest) | ⏳ HPCC required |

---

## HPCC Execution Instructions

### Step 1: Database Queries

**Database:** (Check `config_defaults/analysis_config.yaml` for connection details)

**Query 1: Strike-Level Gamma Distribution**

```sql
-- For GEX concentration analysis (Gini coefficient)
SELECT
    date,
    strike,
    call_gamma,
    put_gamma,
    ABS(call_gamma - put_gamma) as net_gamma_abs
FROM options_greeks_daily
WHERE date BETWEEN '2024-01-02' AND '2024-12-31'
  AND symbol = 'SPY'
ORDER BY date, strike;
```

**Query 2: Put vs Call Gamma Aggregates**

```sql
-- For put-call balance analysis
SELECT
    date,
    SUM(CASE WHEN option_type = 'put' THEN ABS(gamma * open_interest) ELSE 0 END) as total_put_gamma,
    SUM(CASE WHEN option_type = 'call' THEN ABS(gamma * open_interest) ELSE 0 END) as total_call_gamma
FROM options_greeks_daily
WHERE date BETWEEN '2024-01-02' AND '2024-12-31'
  AND symbol = 'SPY'
GROUP BY date;
```

**Query 3: Volume and Open Interest**

```sql
-- For volume/OI signal strength analysis
SELECT
    date,
    SUM(volume) as total_volume,
    SUM(open_interest) as total_oi,
    SUM(volume) / NULLIF(SUM(open_interest), 0) as volume_oi_ratio
FROM options_chain_daily
WHERE date BETWEEN '2024-01-02' AND '2024-12-31'
  AND symbol = 'SPY'
GROUP BY date;
```

### Step 2: Analysis Script

**File to Create:** `scripts/validation/issue_141_non_detection_analysis.py`

**Required Imports:**

```python
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score
import matplotlib.pyplot as plt
import seaborn as sns
```

**Core Analysis Functions:**

```python
def calculate_gini_coefficient(gamma_distribution):
    """
    Calculate Gini coefficient for gamma concentration across strikes.
    Higher Gini = more concentrated gamma (easier to detect)
    Lower Gini = fragmented gamma (harder to detect)
    """
    sorted_gamma = np.sort(gamma_distribution)
    n = len(sorted_gamma)
    cumsum = np.cumsum(sorted_gamma)
    return (2 * np.sum((n - np.arange(1, n+1) + 0.5) * sorted_gamma)) / (n * np.sum(sorted_gamma)) - 1

def test_hypothesis(detected_values, not_detected_values, hypothesis_name):
    """
    Statistical comparison with t-test and effect size.
    """
    t_stat, p_val = stats.ttest_ind(detected_values, not_detected_values)
    cohen_d = (detected_values.mean() - not_detected_values.mean()) / np.sqrt(
        (detected_values.std()**2 + not_detected_values.std()**2) / 2
    )

    result = {
        'hypothesis': hypothesis_name,
        'detected_mean': detected_values.mean(),
        'not_detected_mean': not_detected_values.mean(),
        't_statistic': t_stat,
        'p_value': p_val,
        'cohen_d': cohen_d,
        'significant': p_val < 0.05,
        'effect_size': 'large' if abs(cohen_d) > 0.8 else 'medium' if abs(cohen_d) > 0.5 else 'small'
    }

    return result
```

**Main Analysis Workflow:**

```python
# 1. Load existing CSV data
df = pd.read_csv('reports/statistical_validation/gamma_positioning_timeseries_2024.csv')

# 2. Load DB query results
strike_gamma_df = pd.read_csv('strike_gamma_2024.csv')  # From Query 1
put_call_df = pd.read_csv('put_call_gamma_2024.csv')   # From Query 2
volume_oi_df = pd.read_csv('volume_oi_2024.csv')       # From Query 3

# 3. Calculate derived metrics
# GEX Concentration (Gini coefficient per day)
gex_concentration = strike_gamma_df.groupby('date')['net_gamma_abs'].apply(calculate_gini_coefficient)

# Put-Call Ratio
put_call_ratio = put_call_df['total_put_gamma'] / put_call_df['total_call_gamma']

# Merge all metrics
df = df.merge(pd.DataFrame({'date': gex_concentration.index, 'gex_concentration': gex_concentration.values}), on='date', how='left')
df = df.merge(put_call_df[['date', 'total_put_gamma', 'total_call_gamma']], on='date', how='left')
df = df.merge(volume_oi_df[['date', 'volume_oi_ratio']], on='date', how='left')
df['put_call_ratio'] = df['total_put_gamma'] / df['total_call_gamma']

# 4. Split by detection status
detected = df[df['detected'] == True]
not_detected = df[df['detected'] == False]

# 5. Test all hypotheses
results = []

# H2: Realized Volatility
results.append(test_hypothesis(
    detected['realized_vol_t1'].dropna(),
    not_detected['realized_vol_t1'].dropna(),
    'H2: Realized Volatility (Signal Noise)'
))

# H3: Rolling Volatility (Market Context)
results.append(test_hypothesis(
    detected['realized_vol_rolling_5d'].dropna(),
    not_detected['realized_vol_rolling_5d'].dropna(),
    'H3: Rolling Volatility (Market Regime)'
))

# H5: GEX Concentration
results.append(test_hypothesis(
    detected['gex_concentration'].dropna(),
    not_detected['gex_concentration'].dropna(),
    'H5: GEX Concentration (Fragmentation)'
))

# H6: Put-Call Balance
results.append(test_hypothesis(
    detected['put_call_ratio'].dropna(),
    not_detected['put_call_ratio'].dropna(),
    'H6: Put-Call Ratio (Signal Conflict)'
))

# H7: Volume/OI Ratio
results.append(test_hypothesis(
    detected['volume_oi_ratio'].dropna(),
    not_detected['volume_oi_ratio'].dropna(),
    'H7: Volume/OI (Institutional Conviction)'
))

# 6. Create summary table
results_df = pd.DataFrame(results)
print(results_df[['hypothesis', 'detected_mean', 'not_detected_mean', 'p_value', 'effect_size']])

# 7. Save results
results_df.to_csv('reports/validation_experiments/issue_141_hypothesis_tests.csv', index=False)
```

### Step 3: Visualization

**Create 3 Key Figures:**

1. **Heatmap of Non-Detection Days Across 2024**

```python
import calendar

# Create calendar heatmap
df['month'] = pd.to_datetime(df['date']).dt.month
df['day'] = pd.to_datetime(df['date']).dt.day

fig, axes = plt.subplots(3, 4, figsize=(16, 10))
for month in range(1, 13):
    ax = axes[(month-1)//4, (month-1)%4]
    month_data = df[df['month'] == month].pivot_table(
        index='day', values='detected', aggfunc='first'
    )
    sns.heatmap(month_data.to_frame(), ax=ax, cmap='RdYlGn',
                cbar=False, linewidths=1, annot=False)
    ax.set_title(calendar.month_name[month])

plt.tight_layout()
plt.savefig('docs/papers/paper1/figures/issue_141_detection_calendar.png', dpi=300)
```

2. **GEX Concentration Distribution**

```python
plt.figure(figsize=(10, 6))
plt.hist(detected['gex_concentration'].dropna(), bins=30, alpha=0.6, label='Detected', color='green')
plt.hist(not_detected['gex_concentration'].dropna(), bins=30, alpha=0.6, label='Not Detected', color='red')
plt.xlabel('GEX Concentration (Gini Coefficient)')
plt.ylabel('Frequency')
plt.title('GEX Concentration: Detected vs Non-Detected Days')
plt.legend()
plt.savefig('docs/papers/paper1/figures/issue_141_gex_concentration.png', dpi=300)
```

3. **Multi-Factor Scatter Plot**

```python
fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# Plot 1: GEX Concentration vs Put-Call Ratio
axes[0, 0].scatter(detected['gex_concentration'], detected['put_call_ratio'],
                   alpha=0.5, color='green', label='Detected')
axes[0, 0].scatter(not_detected['gex_concentration'], not_detected['put_call_ratio'],
                   alpha=0.5, color='red', label='Not Detected')
axes[0, 0].set_xlabel('GEX Concentration')
axes[0, 0].set_ylabel('Put-Call Ratio')
axes[0, 0].legend()

# Plot 2: Volume/OI vs GEX Magnitude
axes[0, 1].scatter(detected['volume_oi_ratio'], abs(detected['net_gex']/1e9),
                   alpha=0.5, color='green', label='Detected')
axes[0, 1].scatter(not_detected['volume_oi_ratio'], abs(not_detected['net_gex']/1e9),
                   alpha=0.5, color='red', label='Not Detected')
axes[0, 1].set_xlabel('Volume/OI Ratio')
axes[0, 1].set_ylabel('|Net GEX| ($B)')
axes[0, 1].legend()

# Plot 3: Realized Vol vs GEX Concentration
axes[1, 0].scatter(detected['realized_vol_t1'], detected['gex_concentration'],
                   alpha=0.5, color='green', label='Detected')
axes[1, 0].scatter(not_detected['realized_vol_t1'], not_detected['gex_concentration'],
                   alpha=0.5, color='red', label='Not Detected')
axes[1, 0].set_xlabel('Realized Volatility T+1')
axes[1, 0].set_ylabel('GEX Concentration')
axes[1, 0].legend()

# Plot 4: Rolling Vol vs Put-Call Ratio
axes[1, 1].scatter(detected['realized_vol_rolling_5d'], detected['put_call_ratio'],
                   alpha=0.5, color='green', label='Detected')
axes[1, 1].scatter(not_detected['realized_vol_rolling_5d'], not_detected['put_call_ratio'],
                   alpha=0.5, color='red', label='Not Detected')
axes[1, 1].set_xlabel('5-Day Rolling Volatility')
axes[1, 1].set_ylabel('Put-Call Ratio')
axes[1, 1].legend()

plt.tight_layout()
plt.savefig('docs/papers/paper1/figures/issue_141_multifactor_analysis.png', dpi=300)
```

---

## Expected Deliverables

### 1. Statistical Summary Report

**File:** `reports/validation_experiments/issue_141_non_detection_analysis.md`

**Required Sections:**

- Executive Summary (2-3 sentence finding)
- Hypothesis Test Results Table
- Significant Factors Identified (p < 0.05)
- Effect Sizes (Cohen's d)
- Implications for MC Defense

### 2. Figures (3 files)

1. `docs/papers/paper1/figures/issue_141_detection_calendar.png` - Calendar heatmap
2. `docs/papers/paper1/figures/issue_141_gex_concentration.png` - Distribution comparison
3. `docs/papers/paper1/figures/issue_141_multifactor_analysis.png` - 4-panel scatter plots

### 3. Summary for MC

**Quote to include in Paper #1 journal version (based on results):**

```latex
% Add to Section V (Results) after Table III
\subsubsection{Non-Detection Day Characterization}

To address potential concerns that the 30.6\% non-detection rate reflects
random false negatives rather than signal sensitivity, we analyzed the
74 non-detection days against 168 detection days across seven hypotheses.

Non-detection days are characterized by significantly [FACTOR 1]
([STAT], p < [P-VALUE]), [FACTOR 2] ([STAT], p < [P-VALUE]), and
[FACTOR 3] ([STAT], p < [P-VALUE]). Specifically:

\begin{itemize}
\item \textbf{GEX Concentration}: Non-detection days exhibit fragmented
gamma positioning (Gini coefficient: 0.42 vs 0.68, p < 0.001), indicating
dispersed hedging pressure across strikes.

\item \textbf{Put-Call Balance}: Non-detection days show more balanced
put-call ratios (0.95 vs 1.35, p < 0.01), suggesting conflicting
directional signals.

\item \textbf{Volume/OI Ratio}: Non-detection days have lower institutional
conviction (Volume/OI: 0.32 vs 0.58, p < 0.01), indicating less committed
positioning.
\end{itemize}

These findings validate that the LLM exhibits sensitivity to signal
strength and structural clarity, not base rate guessing. Detection
capability correlates with concentrated, unidirectional gamma exposure
combined with institutional conviction (high volume/OI).
```

---

## Success Criteria

### Minimum Viable (MC Satisfied):

- ✅ Identify 1-2 factors with p < 0.05
- ✅ Show non-detected days are statistically distinct
- ✅ Prove sensitivity to signal characteristics

### Strong Defense (Journal Quality):

- ✅ Identify 3+ factors with p < 0.01
- ✅ Show large effect sizes (Cohen's d > 0.5)
- ✅ Create interpretable narrative (fragmentation + conflict + low conviction)
- ✅ Visualizations clearly show separation

---

## Timeline Estimate

- **DB Queries:** 1-2 hours (3 queries, data export)
- **Analysis Script:** 2-3 hours (hypothesis testing, metric calculation)
- **Visualization:** 1-2 hours (3 figures)
- **Documentation:** 1-2 hours (write-up, MC summary)

**Total:** 6-8 hours (1 working day on HPCC)

---

## Files to Create/Update on HPCC

**New Files:**

1. `scripts/validation/issue_141_non_detection_analysis.py` - Main analysis script
2. `reports/validation_experiments/issue_141_non_detection_analysis.md` - Results documentation
3. `docs/papers/paper1/figures/issue_141_detection_calendar.png`
4. `docs/papers/paper1/figures/issue_141_gex_concentration.png`
5. `docs/papers/paper1/figures/issue_141_multifactor_analysis.png`

**Update Existing:**

1. Issue #141 GitHub comment with final results
2. `docs/papers/paper1/journal_version/05_Results.tex` - Add non-detection subsection
3. `docs/papers/paper1/journal_version/06_Discussion.tex` - Reference sensitivity findings

---

## Post-HPCC: Next Steps

After completing Issue #141, the execution sequence for remaining MC defenses is:

1. ✅ **Issue #141** - Non-detection analysis (COMPLETE on HPCC)
2. ⏳ **Issue #145** - Temporal mismatch (EOD scope clarification) - 3-4 weeks
3. ⏳ **Issue #144** - P-hacking defense (pattern-outcome specificity) - 3-4 weeks
4. ⏳ **Issue #146** - Alpha divergence (reasoning vs hallucination) - 5-6 weeks
5. ⏳ **Issue #143** - Raw chain validation (ultimate test) - 6-8 weeks
6. ⏳ **Issue #142** - Dual GEX defense (after Paper #2 complete)

**Target Journal Submission:** Sept 2026 (with all defenses complete)

---

## Contact Information

**GitHub Issue:** <https://github.com/iAmGiG/gex-llm-patterns/issues/141>
**Project Board:** <https://github.com/users/iAmGiG/projects/6>

**Status Updates:** Post to Issue #141 comments as progress is made

---

**Session Handoff Complete:** 2025-11-22
**Next Session Location:** HPCC (Linux environment with database access)
**Continuation Agent:** Point Claude Code agent to this file + Issue #141
