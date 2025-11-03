# Comparative Analysis Framework: Single-Day vs Sequential

**Purpose**: Define statistical methodology for comparing Paper #1 (single-day) vs Paper #2 (sequential) approaches

**Date**: November 1, 2025
**Status**: Design phase

---

## Research Question

**Does temporal context (5-day sequences) improve LLM pattern detection compared to single-day snapshots?**

**Null Hypothesis (H0)**: Sequential approach performance ≤ single-day performance
**Alternative (H1)**: Sequential approach shows significant improvement on at least one metric

---

## Primary Comparison Metrics

### 1. Detection Rate

**Definition**: % of days where LLM detects a pattern

**Baseline (Paper #1, 2024 unbiased prompt)**:

```yaml
single_day_detection:
  data_source: "reports/validation/paper1_unbiased_2024.json"
  detection_rate: 69.4%  # 168 of 242 days
  confidence_interval: [63.2%, 75.1%]  # 95% CI
```

**Sequential (Paper #2)**:

```yaml
sequential_detection:
  data_source: "reports/validation/sequential_2024/"
  detection_rate: TBD
  confidence_interval: TBD
```

**Statistical Test**: **McNemar's Test** (paired proportions)

```python
from statsmodels.stats.contingency_tables import mcnemar

# Contingency table
#                    Sequential Detected  |  Sequential No Pattern
# Single Detected    |       a            |         b
# Single No Pattern  |       c            |         d

table = [[a, b],
         [c, d]]

result = mcnemar(table, exact=False, correction=True)
# p < 0.05 → significant difference
```

**Why McNemar's Test:**

- ✅ Paired data (same days analyzed by both methods)
- ✅ Tests if methods disagree systematically (not just random)
- ✅ Handles "both detected" vs "one detected" cases

**Interpretation**:

- `b > c` and p < 0.05: Sequential detects patterns single-day missed (improvement)
- `c > b` and p < 0.05: Single-day detects patterns sequential missed (regression)
- p ≥ 0.05: No significant difference in detection rate

---

### 2. Predictive Accuracy

**Definition**: % of detected patterns that verify against outcome thresholds

**Baseline (Paper #1)**:

```yaml
single_day_accuracy:
  total_detected: 168
  verified: 154
  accuracy: 91.7%  # 154/168
  confidence_interval: [86.5%, 95.3%]
```

**Sequential (Paper #2)**:

```yaml
sequential_accuracy:
  total_detected: TBD
  verified: TBD
  accuracy: TBD
```

**Statistical Test**: **Two-Proportion Z-Test**

```python
from statsmodels.stats.proportion import proportions_ztest

counts = [verified_sequential, verified_single]
nobs = [detected_sequential, detected_single]

z_stat, p_value = proportions_ztest(counts, nobs, alternative='larger')
# p < 0.05 → sequential significantly more accurate
```

**Why Two-Proportion Test:**

- ✅ Independent proportions (accuracy of detected patterns)
- ✅ Tests if sequential predictions verify at higher rate
- ✅ One-sided test (H1: sequential > single-day)

**Interpretation**:

- Accuracy Δ > 2pp and p < 0.05: Meaningful improvement
- Accuracy Δ < 2pp: Marginal or no improvement
- Accuracy Δ < 0: Regression (sequential less accurate)

---

### 3. Confidence Score

**Definition**: Mean LLM-reported confidence (0-100) for detected patterns

**Baseline (Paper #1)**:

```yaml
single_day_confidence:
  mean: 72  # Estimated (Paper #1 reported ~70-75 typical)
  median: 75
  std: 12
```

**Sequential (Paper #2)**:

```yaml
sequential_confidence:
  mean: TBD
  median: TBD
  std: TBD
```

**Statistical Test**: **Welch's t-test** (unequal variances)

```python
from scipy.stats import ttest_ind

t_stat, p_value = ttest_ind(
    sequential_confidences,
    single_day_confidences,
    equal_var=False,  # Welch's t-test
    alternative='greater'  # H1: sequential > single
)
```

**Why Welch's t-test:**

- ✅ Continuous variable (confidence scores)
- ✅ Doesn't assume equal variances
- ✅ Tests if sequential confidences are significantly higher

**Interpretation**:

- Mean Δ > 10pts and p < 0.05: Sequential increases confidence meaningfully
- Mean Δ 5-10pts: Modest improvement
- Mean Δ < 5pts: No practical difference

---

## Secondary Metrics

### 4. False Positive Rate

**Definition**: % of detected patterns that do NOT verify

**Baseline (Paper #1)**:

```yaml
single_day_fpr:
  false_positives: 14  # 168 detected - 154 verified
  total_detected: 168
  fpr: 8.3%
```

**Sequential (Paper #2)**:

```yaml
sequential_fpr:
  false_positives: TBD
  total_detected: TBD
  fpr: TBD
```

**Statistical Test**: Same as accuracy (inverse metric)

**Interpretation**:

- Lower FPR = Better (fewer spurious detections)
- Ideal: Detection ↑ AND FPR ↓ (more patterns, higher precision)

---

### 5. Pattern-Specific Performance

**Compare performance by trajectory type:**

```python
pattern_comparison = {
    'gamma_accumulation': {
        'single_day': {'detection': '25%', 'accuracy': '88%'},
        'sequential': {'detection': 'TBD', 'accuracy': 'TBD'},
        'delta': 'TBD'
    },
    'gamma_relief': {
        'single_day': {'detection': '15%', 'accuracy': '92%'},
        'sequential': {'detection': 'TBD', 'accuracy': 'TBD'},
        'delta': 'TBD'
    },
    'persistent_gamma': {
        'single_day': {'detection': '60%', 'accuracy': '94%'},
        'sequential': {'detection': 'TBD', 'accuracy': 'TBD'},
        'delta': 'TBD'
    }
}
```

**Analysis**: Which patterns benefit most from temporal context?

**Hypothesis**:

- **Accumulation**: Should improve (5-day trend clearer than snapshot)
- **Relief**: Should improve (declining pressure visible in sequence)
- **Persistent**: May not improve (single day sufficient for stable regime)

---

## GO/NO-GO Decision Criteria (Day 5)

### ✅ GO - Proceed to Phase 2 (Multi-Year) IF

**Strong Evidence:**

1. Detection rate increases ≥5pp (p < 0.05), OR
2. Accuracy improves ≥2pp (p < 0.05), OR
3. Confidence increases ≥10pts (p < 0.05)

**AND**:
4. No metric regresses >3pp

**Example**:

```bash
Detection: 69.4% → 75.2% (+5.8pp, p=0.012) ✅
Accuracy: 91.7% → 93.1% (+1.4pp, p=0.18) (NS but not regressing)
Confidence: 72 → 81 (+9pts, p=0.045) (marginal)
→ GO (detection improvement is strong)
```

---

### ⚠️ CAUTION - Mixed Results IF

**Marginal Improvements:**

1. Detection +2-4pp (p > 0.05), OR
2. Accuracy +1-2pp (marginal), OR
3. Trade-offs (detection ↑, accuracy ↓)

**Example**:

```bash
Detection: 69.4% → 72.1% (+2.7pp, p=0.12) (NS)
Accuracy: 91.7% → 93.0% (+1.3pp, p=0.24) (NS)
Confidence: 72 → 77 (+5pts, p=0.08) (marginal)
→ CAUTION (no strong signal, but slight improvement)
```

**Decision**: Discuss with advisor, possibly proceed with caveats

---

### 🚫 NO-GO - Fold into Paper #1 Discussion IF

**No Improvement or Regression:**

1. Detection decreases >3pp, OR
2. Accuracy decreases >2pp, OR
3. No significant improvements on ANY metric

**Example**:

```bash
Detection: 69.4% → 67.8% (-1.6pp, p=0.35) ⚠️
Accuracy: 91.7% → 90.2% (-1.5pp, p=0.28) ⚠️
Confidence: 72 → 74 (+2pts, p=0.45) (NS)
→ NO-GO (slight regression, no improvements)
```

**Academic Handling**:

- Add to Paper #1 discussion: "We tested sequential context; no improvement observed"
- Explains why temporal dynamics are limited (stable regime)
- Honest null result (still publishable finding)

---

## Visualization Requirements

### 1. Detection Rate Comparison (Bar Chart)

```python
import matplotlib.pyplot as plt

methods = ['Single-Day', 'Sequential']
detection_rates = [69.4, TBD]
error_bars = [CI_width_single, CI_width_sequential]

plt.bar(methods, detection_rates, yerr=error_bars)
plt.ylabel('Detection Rate (%)')
plt.title('Pattern Detection: Single-Day vs Sequential')
# Add significance annotation if p < 0.05
```

---

### 2. Accuracy Comparison (Grouped Bar)

```python
patterns = ['Accumulation', 'Relief', 'Persistent', 'Overall']
single_accuracy = [88, 92, 94, 91.7]
sequential_accuracy = [TBD, TBD, TBD, TBD]

# Grouped bar chart with significance stars
```

---

### 3. Confidence Distribution (Violin Plot)

```python
import seaborn as sns

data = pd.DataFrame({
    'Method': ['Single']*168 + ['Sequential']*N,
    'Confidence': single_confidences + sequential_confidences
})

sns.violinplot(data=data, x='Method', y='Confidence')
plt.title('Confidence Score Distributions')
```

---

### 4. Calibration Curve (Reliability Diagram)

```python
# Bin predictions by confidence score
for confidence_bin in [40-50, 50-60, ..., 90-100]:
    predictions_in_bin = filter(confidences, bin)
    verification_rate = sum(verified) / len(predictions_in_bin)

# Plot predicted vs actual verification rate
plt.plot(predicted_confidence, actual_verification, label='Sequential')
plt.plot([0, 100], [0, 100], 'k--', label='Perfect Calibration')
```

---

## Implementation Code Structure

```python
# scripts/validation/compare_sequential_vs_single.py

def load_results(single_path, sequential_path):
    """Load validation results from both methods."""
    pass

def compute_detection_comparison(single, sequential):
    """McNemar's test for detection rates."""
    return {
        'single_rate': single['detection_rate'],
        'sequential_rate': sequential['detection_rate'],
        'mcnemar_stat': stat,
        'p_value': p,
        'interpretation': 'Significant improvement' if p < 0.05 else 'NS'
    }

def compute_accuracy_comparison(single, sequential):
    """Two-proportion test for accuracy."""
    return {
        'single_accuracy': single['accuracy'],
        'sequential_accuracy': sequential['accuracy'],
        'delta': delta,
        'z_stat': z,
        'p_value': p,
        'ci_95': [lower, upper]
    }

def compute_confidence_comparison(single, sequential):
    """Welch's t-test for confidence scores."""
    return {
        'single_mean': np.mean(single['confidences']),
        'sequential_mean': np.mean(sequential['confidences']),
        'delta': delta,
        't_stat': t,
        'p_value': p
    }

def generate_comparison_report():
    """Generate full comparison with GO/NO-GO decision."""
    metrics = {
        'detection': compute_detection_comparison(...),
        'accuracy': compute_accuracy_comparison(...),
        'confidence': compute_confidence_comparison(...)
    }

    decision = decide_go_no_go(metrics)

    return {
        'metrics': metrics,
        'decision': decision,
        'recommendation': recommendation,
        'visualizations': generate_plots(metrics)
    }
```

---

## Expected Results (Baseline Estimates)

### Best Case (Strong Sequential Advantage)

```yaml
best_case:
  detection_rate: 69.4% → 77% (+7.6pp, p=0.003) ✅
  accuracy: 91.7% → 94.5% (+2.8pp, p=0.02) ✅
  confidence: 72 → 84 (+12pts, p<0.001) ✅
  decision: STRONG GO
  interpretation: "Temporal context substantially improves pattern recognition"
```

### Moderate Case (Marginal Improvement)

```yaml
moderate_case:
  detection_rate: 69.4% → 72.8% (+3.4pp, p=0.06) ⚠️
  accuracy: 91.7% → 93.2% (+1.5pp, p=0.15) (NS)
  confidence: 72 → 78 (+6pts, p=0.03) ✅
  decision: CAUTION / GO
  interpretation: "Modest improvement, proceed with caveats"
```

### Null Case (No Improvement)

```yaml
null_case:
  detection_rate: 69.4% → 70.1% (+0.7pp, p=0.42) (NS)
  accuracy: 91.7% → 92.0% (+0.3pp, p=0.38) (NS)
  confidence: 72 → 73 (+1pt, p=0.35) (NS)
  decision: NO-GO
  interpretation: "Temporal context does not improve performance in stable regime"
```

**Academic Value of Null Result:**

- ✅ Still publishable: "We tested H1, found no support"
- ✅ Explains regime dependency: "2024 stable regime limits temporal signal"
- ✅ Sets up multi-year: "May differ in regime-change periods (2023)"

---

## Statistical Power Analysis

**Minimum Detectable Effect (MDE):**

```python
from statsmodels.stats.power import zt_ind_solve_power

# For accuracy comparison (two-proportion test)
n_single = 168  # Detected patterns in Paper #1
n_sequential = 170  # Estimated (assuming similar detection)

mde = zt_ind_solve_power(
    effect_size=None,
    nobs1=n_single,
    alpha=0.05,
    power=0.80,
    ratio=n_sequential/n_single
)

# MDE ≈ 0.25 (Cohen's h)
# Translates to ~5-7pp accuracy difference detectable at 80% power
```

**Interpretation**: We can reliably detect accuracy improvements ≥6pp

**Sample Size Adequate?**

- ✅ For 5pp detection rate change: 80% power with n=240
- ✅ For 3pp accuracy change: 65% power (marginal)
- ⚠️ For 10pt confidence change: 75% power (acceptable)

---

## Files Generated

```bash
reports/validation/sequential_2024/
├── comparative_analysis_summary.json     # All metrics
├── statistical_tests.json                # p-values, CIs
├── go_no_go_decision.md                  # Recommendation
└── figures/
    ├── detection_comparison.png
    ├── accuracy_by_pattern.png
    ├── confidence_distribution.png
    └── calibration_curve.png
```

---

## Related Documents

**Paper #1 Baseline**:

- `reports/validation/paper1_unbiased_2024.json`
- Detection: 69.4%, Accuracy: 91.7%

**Paper #2 Design**:

- `sequential_prompt_design.md` - Template and methodology
- `outcome_verification_thresholds.md` - Verification framework
- `sequential_pattern_detection_rules.md` - Pattern detection logic

**Related Issues**:

- Issue #107: Paper #2 Sequential GEX Analysis
- Issue #108: Implementation (5-day plan)

---

**Last Updated**: November 1, 2025
**Status**: Ready for implementation (Day 5 analysis)
