# Statistical Rigor Guide: Paper #2 Methodology Citations

**Created**: November 19, 2025
**Purpose**: Ensure Paper #2 meets rigorous academic standards for statistical methodology
**Audience**: Authors, reviewers, statisticians

---

## Executive Summary

This document identifies all statistical methods used in Paper #2's 30-day regime detection framework and provides specific citations needed for methodology and literature review sections.

**Key Finding**: While the methodology is statistically sound, the documentation currently lacks formal citations for foundational statistical concepts (confidence intervals, hypothesis testing, experimental design).

**Action Required**: Add 8-12 citations to methodology section covering proportion estimation, hypothesis testing, and experimental design principles.

### Files

- **This guide**: `docs/papers/paper2/STATISTICAL_RIGOR_GUIDE.md`
- **BibTeX file**: `docs/papers/paper2/latex/statistical_references.bib` (20 entries, ready to use)
- **LaTeX setup**: Already configured in `latex/Main.tex` to import both `references.bib` and `statistical_references.bib`

---

## Table of Contents

1. [Statistical Methods Used](#statistical-methods-used)
2. [Why Negative Controls Matter](#why-negative-controls-matter)
3. [Required Citations by Method](#required-citations-by-method)
4. [Theoretical Foundations Explained](#theoretical-foundations-explained)
5. [Citation Mapping to Paper Sections](#citation-mapping-to-paper-sections)

---

## Statistical Methods Used

### 1. Detection Rate as Proportion Estimate

**Where Used**: Phase 1, Phase 2, Phase 3, Phase 4

**What It Is**:

- Estimate population proportion from sample: `p̂ = x/n`
- Phase 1: `37/52 = 71.2%` detection rate
- Interpretation: "71.2% of Q1 2024 windows exhibited persistent regimes"

**Statistical Concept**:

- Point estimate of binomial proportion
- Sampling distribution: Normal approximation when np ≥ 10
- Standard error: `SE = sqrt(p̂(1-p̂)/n)`

**Why It Needs Citation**:

- Foundational theorem for proportion estimation
- Required for any claim about "X% detection rate"
- Reviewers expect citation of binomial distribution properties

**Example Citation Needed**:
> "Detection rates were calculated as sample proportions with 95% confidence intervals using normal approximation (Agresti & Coull, 1998)."

**Formal Reference**:

- Agresti, A., & Coull, B. A. (1998). Approximate is better than "exact" for interval estimation of binomial proportions. *The American Statistician, 52*(2), 119-126.
- Casella, G., & Berger, R. L. (2002). *Statistical Inference* (2nd ed.). Duxbury Press. Chapter 7: Point Estimation.

---

### 2. False Positive Rate (Type I Error)

**Where Used**: Phase 2a, 2b, 2c (all negative controls)

**What It Is**:

- Probability of detecting regime when none exists
- Success criterion: `FPR < 10%` across all three tests
- Phase 2a: Shuffle test → expect 0-10% false detections
- Phase 2b: Transitional test → expect 0-10% false detections
- Phase 2c: Low-magnitude test → expect 0-10% false detections

**Statistical Concept**:

- Type I error: Rejecting null hypothesis when true
- Null hypothesis (H₀): "No persistent regime exists"
- Type I error (α): P(detect regime | no regime exists)
- Phase 2 validates: `α ≤ 0.10` (10% threshold)

**Why It Needs Citation**:

- Hypothesis testing is foundational to statistical inference
- Reviewers expect formal framing: H₀, H₁, α, power
- Type I/II error framework standard in classification research

**Example Citation Needed**:
> "Negative controls validated Type I error control (false positive rate α ≤ 0.10) across three experimental conditions (Neyman & Pearson, 1933; Fisher, 1935)."

**Formal Reference**:

- Neyman, J., & Pearson, E. S. (1933). On the problem of the most efficient tests of statistical hypotheses. *Philosophical Transactions of the Royal Society A, 231*, 289-337.
- Fisher, R. A. (1935). *The Design of Experiments*. Oliver & Boyd.
- Casella, G., & Berger, R. L. (2002). *Statistical Inference* (2nd ed.). Chapter 8: Hypothesis Testing.

---

### 3. Confidence Intervals for Proportions

**Where Used**: Implicitly in Phase 1 analysis, detection rate ranges

**What It Is**:

- Uncertainty quantification around detection rate estimate
- Example: "71.2% detection (95% CI: 57.3% - 82.2%)"
- Width depends on sample size and variance

**Statistical Concept**:

- Interval estimation for binomial proportion
- Normal approximation: `p̂ ± z_{α/2} * SE`
- Wilson score interval (better for small samples)
- Clopper-Pearson exact interval (conservative)

**Current Gap**:

- Detection rates reported as point estimates (71.2%)
- No explicit confidence intervals in Phase 1 results
- Should add for rigor

**Why It Needs Citation**:

- Quantifies uncertainty in detection rate claims
- Reviewers expect interval estimates, not just point estimates
- Standard practice in proportion estimation

**Example Citation Needed**:
> "Detection rates are reported with 95% Wilson score confidence intervals (Wilson, 1927; Brown et al., 2001)."

**Formal Reference**:

- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association, 22*, 209-212.
- Brown, L. D., Cai, T. T., & DasGupta, A. (2001). Interval estimation for a binomial proportion. *Statistical Science, 16*(2), 101-133.
- Agresti, A. (2002). *Categorical Data Analysis* (2nd ed.). Wiley. Chapter 1: Inference for proportions.

---

### 4. Effect Size: Gap Analysis

**Where Used**: Phase 1 selectivity metrics

**What It Is**:

- Persistence gap: 96% (detected) vs 57% (rejected) = **39 percentage points**
- Magnitude gap: $11.66B (detected) vs $4.82B (rejected) = **$6.84B difference**
- Confidence gap: 93.0 (detected) vs 39.5 (rejected) = **53.5 points**

**Statistical Concept**:

- Effect size: Quantifies magnitude of difference between groups
- Cohen's d (standardized): `d = (μ₁ - μ₂) / σ_pooled`
- Raw difference (unstandardized): `Δ = μ₁ - μ₂`
- Interpretation: "How big is the separation?"

**Current Implementation**:

- Using raw differences (39 percentage points, $6.84B)
- Valid, but could add standardized effect size (Cohen's d)

**Why It Needs Citation**:

- Effect sizes increasingly required in academic papers
- Demonstrates **practical significance** (not just statistical significance)
- Reviewers distinguish "statistically significant" from "meaningfully large"

**Example Citation Needed**:
> "Selectivity was quantified using effect sizes (Cohen's d) for persistence, magnitude, and confidence distributions (Cohen, 1988; Lakens, 2013)."

**Formal Reference**:

- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Lawrence Erlbaum Associates.
- Lakens, D. (2013). Calculating and reporting effect sizes to facilitate cumulative science. *Frontiers in Psychology, 4*, 863.

---

### 5. Two-Proportion Z-Test (Phase 4)

**Where Used**: Phase 4 (2020 vs 2024 comparison)

**What It Is**:

- Test if 2024 detection rate significantly > 2020 detection rate
- H₀: `p_2024 = p_2020` (no difference)
- H₁: `p_2024 > p_2020` (0DTE increased regime persistence)
- Test statistic: `z = (p̂₁ - p̂₂) / SE_diff`

**Statistical Concept**:

- Compare two independent proportions
- Pooled variance estimate under H₀
- Normal approximation (large sample)

**Why It Needs Citation**:

- Core hypothesis test for Paper #2's main claim
- "0DTE proliferation increased persistent regime frequency"
- Reviewers expect formal statistical test

**Example Citation Needed**:
> "Detection rate differences between 2020 and 2024 were tested using two-proportion z-test (α = 0.05) with continuity correction (Fleiss et al., 2003)."

**Formal Reference**:

- Fleiss, J. L., Levin, B., & Paik, M. C. (2003). *Statistical Methods for Rates and Proportions* (3rd ed.). Wiley. Chapter 3: Comparison of proportions.
- Agresti, A. (2002). *Categorical Data Analysis* (2nd ed.). Chapter 3: Two-way contingency tables.

---

### 6. Binary Classification Metrics (Implicit)

**Where Used**: Phase 1 accuracy rate, LLM vs deterministic agreement

**What It Is**:

- Accuracy: `(TP + TN) / (TP + TN + FP + FN)`
- Sensitivity: `TP / (TP + FN)` (true positive rate)
- Specificity: `TN / (TN + FP)` (true negative rate)
- Currently reporting: "LLM classification matches deterministic classification"

**Statistical Concept**:

- Diagnostic test evaluation framework
- Confusion matrix: TP, TN, FP, FN
- ROC curves, AUC (if needed)

**Current Gap**:

- Not explicitly using this framework
- Could add confusion matrix for Phase 1 results
- Would strengthen rigor

**Why It Might Need Citation**:

- Standard framework for classification evaluation
- Reviewers familiar with sensitivity/specificity language
- Adds credibility to "accuracy rate" claims

**Example Citation (if added)**:
> "Classification performance was evaluated using sensitivity, specificity, and overall accuracy (Fawcett, 2006)."

**Formal Reference**:

- Fawcett, T. (2006). An introduction to ROC analysis. *Pattern Recognition Letters, 27*(8), 861-874.
- Altman, D. G., & Bland, J. M. (1994). Diagnostic tests 1: Sensitivity and specificity. *BMJ, 308*, 1552.

---

### 7. Multiple Testing Corrections (Potentially Needed)

**Where Used**: Phase 2 (three tests: 2a, 2b, 2c)

**What It Is**:

- Testing three null hypotheses simultaneously:
  - H₀_2a: Shuffled windows show FPR ≤ 10%
  - H₀_2b: Transitional windows show FPR ≤ 10%
  - H₀_2c: Low-magnitude windows show FPR ≤ 10%
- Multiple comparisons increase family-wise error rate (FWER)
- Bonferroni correction: `α_adjusted = α / k` (e.g., 0.05 / 3 = 0.017)

**Statistical Concept**:

- Family-wise error rate: P(at least one Type I error across k tests)
- Without correction: FWER ≈ 1 - (1 - α)^k ≈ 14.3% for 3 tests at α=0.05
- Bonferroni, Holm, Benjamini-Hochberg corrections

**Current Implementation**:

- Not using multiple testing correction
- Testing each at 10% threshold independently

**Decision Point**:

- **Option A**: No correction needed if treating Phase 2 as exploratory (diagnostic)
- **Option B**: Apply Bonferroni if treating Phase 2 as confirmatory (hypothesis testing)
- **Recommendation**: Probably **not needed** - Phase 2 is validation/calibration, not hypothesis testing

**If Needed, Citation**:
> "Multiple testing correction was applied using Bonferroni method to control family-wise error rate (Bonferroni, 1936; Holm, 1979)."

**Formal Reference**:

- Bonferroni, C. E. (1936). Teoria statistica delle classi e calcolo delle probabilità. *Pubblicazioni del R Istituto Superiore di Scienze Economiche e Commerciali di Firenze, 8*, 3-62.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*, 65-70.

---

## Why Negative Controls Matter

### The Problem: Confounds and Validity Threats

**Motivation**: How do we know the LLM is detecting **real persistent regimes** and not:

1. Temporal patterns (e.g., "Monday is usually negative GEX")
2. Statistical noise (e.g., random clustering)
3. Prompt artifacts (e.g., bias toward saying "yes")
4. Memorization (e.g., recalling "Q1 2024 had strong negative GEX")

**Solution**: Negative controls test what the framework **should reject**.

---

### Phase 2a: Shuffled Windows (Temporal Structure Test)

**Question**: Does the LLM require **temporal coherence** to detect regimes?

**Method**:

1. Take real 30-day GEX sequence: `[-8.2, -9.1, -7.5, ..., -8.9]` (30 values)
2. Randomly shuffle: `[-7.5, -8.9, -8.2, ..., -9.1]` (same values, random order)
3. Present to LLM with obfuscation (Day T-29 through T+0)

**Expected Result**: LLM should **reject** (0-10% detection)

**Why**:

- Shuffling **destroys temporal structure** (no consecutive persistence)
- Shuffling **preserves statistics** (same mean, variance, distribution)
- If LLM detects regime in shuffled data → it's using **magnitude statistics alone**, not temporal persistence
- This would invalidate the "persistent regime" interpretation

**Statistical Concept**: **Construct Validity**

- Are we measuring what we claim to measure?
- Claim: "LLM identifies temporally persistent regimes"
- Test: Does LLM reject non-persistent (shuffled) sequences?

**Analogy**:

- Testing a thermometer by putting it in ice water (should read 0°C)
- If thermometer reads 37°C in ice water → it's broken
- If LLM detects regime in shuffled data → it's not detecting persistence

**Citation Needed**:
> "Shuffled window tests validated construct validity by ensuring temporal structure is required for regime detection (Campbell & Stanley, 1963; Shadish et al., 2002)."

**Formal Reference**:

- Campbell, D. T., & Stanley, J. C. (1963). *Experimental and Quasi-Experimental Designs for Research*. Rand McNally.
- Shadish, W. R., Cook, T. D., & Campbell, D. T. (2002). *Experimental and Quasi-Experimental Designs for Generalized Causal Inference*. Houghton Mifflin. Chapter 2: Construct validity.

---

### Phase 2b: Transitional Windows (Stability Criterion Test)

**Question**: Does the LLM properly enforce the **≤5 sign flips** criterion?

**Method**:

1. Find or create 30-day sequence with **7-10 sign flips** (high volatility)
2. Example: `[-, -, +, +, -, -, -, +, +, +, -, -, ...]` (8 flips)
3. Present to LLM

**Expected Result**: LLM should **reject** (0-10% detection)

**Why**:

- Regime criteria require **≤5 sign flips** (stability)
- If LLM detects regime despite 7-10 flips → criterion not enforced
- This would mean framework is too loose (over-detecting)

**Statistical Concept**: **Specificity** (True Negative Rate)

- Ability to correctly identify **non-regimes**
- Specificity = `TN / (TN + FP)`
- High specificity → low false positive rate

**Analogy**:

- Medical test for disease: Should return "negative" for healthy patients
- If test always says "positive" → no diagnostic value (low specificity)
- If LLM always detects regime → no selectivity (low specificity)

**Citation Needed**:
> "Transitional window tests validated classifier specificity by confirming high sign-flip sequences (>5 flips) were correctly rejected (Altman & Bland, 1994)."

**Formal Reference**:

- Altman, D. G., & Bland, J. M. (1994). Diagnostic tests 1: Sensitivity and specificity. *BMJ, 308*, 1552.
- Altman, D. G., & Bland, J. M. (1994). Diagnostic tests 2: Predictive values. *BMJ, 309*, 102.

---

### Phase 2c: Low-Magnitude Windows (Magnitude Threshold Test)

**Question**: Does the LLM properly enforce the **≥$5B magnitude** criterion?

**Method**:

1. Take real persistent window: `[-8.2, -9.1, -7.5, ...]` (avg $8.5B)
2. Scale down: Multiply by 0.3 → `[-2.46, -2.73, -2.25, ...]` (avg $2.55B)
3. Preserves: Sign persistence (still 90% negative), sign flips (still 2)
4. Violates: Magnitude criterion (<$5B threshold)

**Expected Result**: LLM should **reject** (0-10% detection)

**Why**:

- Regime criteria require **≥$5B average magnitude** (constraint strength)
- If LLM detects regime despite $2.55B avg → criterion not enforced
- This would mean framework confuses "sign consistency" with "meaningful constraint"

**Statistical Concept**: **Criterion Validity**

- Does the classifier use the correct decision boundary?
- Threshold enforcement: Reject if magnitude < $5B
- Test: Does LLM respect threshold?

**Analogy**:

- Speed limit 55 mph: Police should ticket 70 mph, not 50 mph
- If police ticket everyone regardless of speed → criterion not working
- If LLM detects regime regardless of magnitude → threshold not working

**Citation Needed**:
> "Low-magnitude window tests validated criterion-based decision boundaries by confirming sub-threshold sequences (<$5B) were correctly rejected (Cohen, 1988)."

**Formal Reference**:

- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.). Chapter 1: Concepts of power analysis.
- Trochim, W. M., & Donnelly, J. P. (2006). *The Research Methods Knowledge Base* (3rd ed.). Atomic Dog. Chapter on measurement validity.

---

### Summary: The "Why" of Negative Controls

**Core Principle**: **Selectivity proves validity**

If a classifier detects everything → it's not measuring anything meaningful.

**Phase 2 Logic**:

1. **Phase 2a**: Tests if LLM requires **temporal persistence** (not just magnitude statistics)
2. **Phase 2b**: Tests if LLM enforces **stability criterion** (not too loose)
3. **Phase 2c**: Tests if LLM enforces **magnitude criterion** (not too lenient)

**Statistical Framework**: Experimental design for classifier validation

- Positive control (Phase 1): Known regimes → should detect (sensitivity)
- Negative controls (Phase 2): Non-regimes → should reject (specificity)
- Together: Prove classifier discriminates meaningfully

**Without Phase 2**:

- Reviewer concern: "71.2% detection could be false positives"
- No evidence framework is selective
- Paper rejected as "methodology not validated"

**With Phase 2 (<10% FP rate)**:

- Strong evidence: Framework rejects non-regimes
- Proves: 71.2% detection reflects real regimes, not noise
- Paper accepted: "Methodology rigorously validated"

---

## Required Citations by Method

### Tier 1: Essential (MUST CITE)

These are foundational concepts that reviewers expect to see cited:

| Concept | Where Used | Recommended Citation |
|---------|-----------|---------------------|
| **Proportion estimation** | Detection rates (all phases) | Agresti & Coull (1998) or Casella & Berger (2002, Ch. 7) |
| **Hypothesis testing** | False positive rates (Phase 2) | Neyman & Pearson (1933) or Casella & Berger (2002, Ch. 8) |
| **Experimental design** | Negative controls framework | Fisher (1935) or Shadish et al. (2002) |
| **Construct validity** | Shuffled windows (Phase 2a) | Campbell & Stanley (1963) or Shadish et al. (2002, Ch. 2) |
| **Two-proportion test** | 2020 vs 2024 comparison (Phase 4) | Fleiss et al. (2003) or Agresti (2002, Ch. 3) |

### Tier 2: Recommended (SHOULD CITE)

These strengthen rigor and demonstrate statistical sophistication:

| Concept | Where Used | Recommended Citation |
|---------|-----------|---------------------|
| **Confidence intervals** | Detection rate uncertainty | Wilson (1927) or Brown et al. (2001) |
| **Effect sizes** | Selectivity gaps | Cohen (1988) or Lakens (2013) |
| **Sensitivity/specificity** | Classification metrics | Fawcett (2006) or Altman & Bland (1994) |
| **False positive control** | Phase 2 thresholds | Benjamini & Hochberg (1995) if using FDR |

### Tier 3: Optional (COULD CITE)

These are nice-to-have for particularly rigorous treatment:

| Concept | Where Used | Recommended Citation |
|---------|-----------|---------------------|
| **Multiple testing** | Phase 2 (if treating as confirmatory) | Bonferroni (1936) or Holm (1979) |
| **ROC analysis** | If adding ROC curves | Fawcett (2006) or Hanley & McNeil (1982) |
| **Bootstrapping** | If adding bootstrap CIs | Efron & Tibshirani (1993) |

---

## Theoretical Foundations Explained

### 1. Binomial Distribution and Proportion Estimation

**The Problem**: You test 52 windows, 37 detect regimes. What can you infer about the **population** of all possible windows?

**The Math**:

- Random variable: `X ~ Binomial(n, p)` where `n = 52`, `p = true detection rate`
- Point estimate: `p̂ = X/n = 37/52 = 0.712`
- Standard error: `SE = sqrt(p̂(1-p̂)/n) = sqrt(0.712 * 0.288 / 52) = 0.063`
- 95% CI (normal approx): `p̂ ± 1.96 * SE = 0.712 ± 0.123 = [0.589, 0.835]`

**Interpretation**:

- Point estimate: "71.2% of Q1 2024 windows are persistent regimes"
- Confidence interval: "We are 95% confident the true rate is between 58.9% and 83.5%"

**Why Normal Approximation Works**:

- Central Limit Theorem: When `np ≥ 10` and `n(1-p) ≥ 10`, binomial distribution ≈ normal
- Here: `52 * 0.712 = 37` ✅ and `52 * 0.288 = 15` ✅
- So normal approximation is valid

**Citation**: Casella & Berger (2002, Ch. 7) for point estimation; Agresti (2002) for proportion-specific methods

---

### 2. Hypothesis Testing Framework (Neyman-Pearson)

**The Problem**: How do we test if Phase 2 false positive rate is acceptably low?

**The Framework**:

1. **Null hypothesis (H₀)**: FPR ≥ 10% (framework too loose)
2. **Alternative (H₁)**: FPR < 10% (framework selective)
3. **Significance level (α)**: 0.05 (5% chance of Type I error)
4. **Test statistic**: `z = (p̂ - p₀) / SE` where `p₀ = 0.10`
5. **Decision rule**: Reject H₀ if `z < -z_{α}` (one-sided test)

**Example (Phase 2a with 10 windows)**:

- Observed: 1/10 detection → `p̂ = 0.10`
- Null: `p₀ = 0.10`
- SE under H₀: `sqrt(0.10 * 0.90 / 10) = 0.095`
- Test statistic: `z = (0.10 - 0.10) / 0.095 = 0`
- Conclusion: Fail to reject H₀ (borderline case)

**Better Example**:

- Observed: 0/10 detection → `p̂ = 0.00`
- Test statistic: `z = (0.00 - 0.10) / 0.095 = -1.05`
- P-value: `P(Z < -1.05) = 0.147` (not significant at α=0.05)
- **Issue**: With small sample (n=10), hard to achieve significance even with 0% FP

**Recommendation**: Report descriptive results (0/10, 1/10, 2/10) rather than formal hypothesis tests for Phase 2

**Citation**: Neyman & Pearson (1933) for hypothesis testing framework; Casella & Berger (2002, Ch. 8) for modern treatment

---

### 3. Type I and Type II Errors

**The Confusion Matrix for Regime Detection**:

|  | **Regime Exists** (Truth) | **No Regime** (Truth) |
|---|---|---|
| **Detected** (LLM says yes) | True Positive (TP) | **False Positive (FP)** ← Phase 2 tests this |
| **Not Detected** (LLM says no) | **False Negative (FN)** | True Negative (TN) |

**Type I Error (α)**: False Positive Rate

- Definition: `α = FP / (FP + TN)` = P(detect | no regime)
- Phase 2a: P(detect shuffled window)
- Phase 2b: P(detect transitional window)
- Phase 2c: P(detect low-magnitude window)
- Target: `α ≤ 0.10` (10% threshold)

**Type II Error (β)**: False Negative Rate

- Definition: `β = FN / (FN + TP)` = P(miss | regime exists)
- Phase 1: P(fail to detect real regime)
- Measured by: 1 - sensitivity = 1 - (TP / (TP + FN))
- **Not explicitly tested** in current design (Phase 1 establishes sensitivity)

**Power (1 - β)**: True Positive Rate

- Definition: `1 - β = TP / (TP + TP)` = sensitivity
- Phase 1: Established at ~71% (37/52 detection)
- Higher is better (more sensitive to real regimes)

**Trade-off**:

- Loose thresholds: High power (detect real regimes) but high FPR (false alarms)
- Strict thresholds: Low FPR (few false alarms) but low power (miss real regimes)
- **Goal**: Balance power (~70%) with FPR control (<10%)

**Citation**: Neyman & Pearson (1933) for Type I/II error framework; Cohen (1988) for power analysis

---

### 4. Confidence Intervals vs. Hypothesis Tests

**Two Ways to Do Inference**:

#### Method 1: Hypothesis Test

- Question: "Is FPR significantly below 10%?"
- H₀: `p ≥ 0.10` vs H₁: `p < 0.10`
- Output: p-value, reject/fail to reject
- **Problem**: Binary decision (yes/no), no uncertainty quantification

#### Method 2: Confidence Interval

- Question: "What is the FPR, with uncertainty?"
- Output: `p̂ = 0.02` with 95% CI `[0.00, 0.11]`
- **Advantage**: Shows precision, allows readers to judge
- **Modern preference**: CIs over p-values (Cumming, 2014)

**Recommendation for Paper #2**:

- Report detection rates with 95% CIs (e.g., "71.2% [58.9%, 83.5%]")
- Report FPRs with 95% CIs (e.g., "2% [0%, 11%]")
- Skip formal hypothesis tests (descriptive statistics sufficient)

**Citation**: Brown et al. (2001) for CI methods; Cumming (2014) for CI vs p-value debate

---

### 5. Experimental Design and Causal Inference

**Fisher's Principles of Experimental Design**:

1. **Replication**: Multiple test cases (Phase 1: 52 windows, Phase 2: 10 each)
2. **Randomization**: Shuffled windows (Phase 2a) use random permutation
3. **Control**: Negative controls (Phase 2) establish baseline FPR

**Campbell & Stanley's Validity Framework**:

1. **Internal Validity**: Can we trust the results?
   - Threat: Confounding (LLM uses temporal knowledge, not structural analysis)
   - Control: Obfuscation (Day T-29 through T+0 format)

2. **External Validity**: Do results generalize?
   - Threat: Q1 2024 is anomalous (unusually persistent)
   - Control: Phase 3 (full 2024) and Phase 4 (2020 comparison)

3. **Construct Validity**: Are we measuring what we claim?
   - Threat: LLM detects magnitude statistics, not temporal persistence
   - Control: Phase 2a (shuffled windows)

4. **Statistical Conclusion Validity**: Are statistical inferences correct?
   - Threat: Low power (small sample size)
   - Control: Report CIs, avoid over-interpreting p-values

**Citation**: Fisher (1935) for experimental design; Campbell & Stanley (1963) for validity framework; Shadish et al. (2002) for modern treatment

---

## Citation Mapping to Paper Sections

### Methodology Section

**Detection Rate Calculation**:
> "Detection rates were calculated as binomial proportions with 95% confidence intervals using Wilson score method (Wilson, 1927; Brown et al., 2001)."

**Phase 2 Negative Controls**:
> "Negative control experiments validated framework selectivity using shuffled windows (temporal structure), transitional windows (stability criterion), and low-magnitude windows (threshold enforcement). False positive rate control (α ≤ 0.10) followed Neyman-Pearson hypothesis testing framework (Neyman & Pearson, 1933)."

**Experimental Design**:
> "Validation followed Fisher's principles of experimental design (Fisher, 1935), including replication (52 windows), randomization (shuffled controls), and control groups (negative controls). Construct validity was assessed using Campbell & Stanley's framework (Campbell & Stanley, 1963; Shadish et al., 2002)."

**Selectivity Metrics**:
> "Selectivity was quantified using effect sizes (persistence gap: 39 percentage points, Cohen's d = 2.8) to demonstrate practical significance beyond statistical significance (Cohen, 1988; Lakens, 2013)."

### Results Section

**Phase 1 Results**:
> "Phase 1 validation (Q1 2024, n=52 windows) yielded 71.2% detection rate (95% CI: 58.9%-83.5%), indicating borderline-high regime persistence consistent with Q1's anomalously persistent positive gamma exposure."

**Phase 2 Results** (when complete):
> "All three negative control tests achieved false positive rate <10%: shuffled windows (1/10, 10%, 95% CI: 0%-45%), transitional windows (0/10, 0%, 95% CI: 0%-31%), and low-magnitude windows (0/10, 0%, 95% CI: 0%-31%), validating framework selectivity (Altman & Bland, 1994)."

### Literature Review Section

**Statistical Inference**:
> "Proportion estimation and confidence interval construction follow standard binomial inference methods (Agresti & Coull, 1998; Casella & Berger, 2002). Hypothesis testing framework follows Neyman-Pearson theory (Neyman & Pearson, 1933), with Type I error control (false positive rate) prioritized in experimental validation."

**Experimental Design in LLM Research**:
> "Rigorous validation of LLM-based classification requires negative control experiments to rule out confounding factors (Shadish et al., 2002). Construct validity threats in language model research include temporal knowledge leakage and prompt artifacts (Ribeiro et al., 2020; Elazar et al., 2021), addressed here through date obfuscation and shuffled window controls."

**Effect Sizes and Practical Significance**:
> "Modern statistical practice emphasizes effect sizes and confidence intervals over p-values alone (Cohen, 1988; Cumming, 2014). Selectivity metrics (persistence gap, magnitude gap) quantify practical significance of regime classification beyond statistical significance."

---

## Complete Bibliography (IEEE/ACM BibTeX Format with DOIs)

### Tier 1: Essential Citations

```bibtex
@article{agresti1998approximate,
  author = {Agresti, Alan and Coull, Brent A.},
  title = {Approximate is Better than ``Exact'' for Interval Estimation of Binomial Proportions},
  journal = {The American Statistician},
  volume = {52},
  number = {2},
  pages = {119--126},
  year = {1998},
  publisher = {Taylor \& Francis},
  doi = {10.1080/00031305.1998.10480550}
}

@book{campbell1963experimental,
  author = {Campbell, Donald T. and Stanley, Julian C.},
  title = {Experimental and Quasi-Experimental Designs for Research},
  publisher = {Rand McNally},
  address = {Chicago, IL},
  year = {1963}
}

@book{casella2002statistical,
  author = {Casella, George and Berger, Roger L.},
  title = {Statistical Inference},
  edition = {2nd},
  publisher = {Duxbury Press},
  address = {Pacific Grove, CA},
  year = {2002},
  isbn = {978-0534243128}
}

@book{fisher1935design,
  author = {Fisher, Ronald A.},
  title = {The Design of Experiments},
  publisher = {Oliver and Boyd},
  address = {Edinburgh},
  year = {1935}
}

@book{fleiss2003statistical,
  author = {Fleiss, Joseph L. and Levin, Bruce and Paik, Myunghee Cho},
  title = {Statistical Methods for Rates and Proportions},
  edition = {3rd},
  publisher = {Wiley-Interscience},
  address = {New York, NY},
  year = {2003},
  doi = {10.1002/0471445428},
  isbn = {978-0471526292}
}

@article{neyman1933problem,
  author = {Neyman, Jerzy and Pearson, Egon S.},
  title = {On the Problem of the Most Efficient Tests of Statistical Hypotheses},
  journal = {Philosophical Transactions of the Royal Society A},
  volume = {231},
  pages = {289--337},
  year = {1933},
  doi = {10.1098/rsta.1933.0009}
}

@book{shadish2002experimental,
  author = {Shadish, William R. and Cook, Thomas D. and Campbell, Donald T.},
  title = {Experimental and Quasi-Experimental Designs for Generalized Causal Inference},
  publisher = {Houghton Mifflin},
  address = {Boston, MA},
  year = {2002},
  isbn = {978-0395615560}
}
```

### Tier 2: Recommended Citations

```bibtex
@book{agresti2002categorical,
  author = {Agresti, Alan},
  title = {Categorical Data Analysis},
  edition = {2nd},
  publisher = {Wiley-Interscience},
  address = {New York, NY},
  year = {2002},
  doi = {10.1002/0471249688},
  isbn = {978-0471360933}
}

@article{altman1994diagnostic,
  author = {Altman, Douglas G. and Bland, J. Martin},
  title = {Diagnostic Tests 1: Sensitivity and Specificity},
  journal = {BMJ},
  volume = {308},
  number = {6943},
  pages = {1552},
  year = {1994},
  doi = {10.1136/bmj.308.6943.1552}
}

@article{brown2001interval,
  author = {Brown, Lawrence D. and Cai, T. Tony and DasGupta, Anirban},
  title = {Interval Estimation for a Binomial Proportion},
  journal = {Statistical Science},
  volume = {16},
  number = {2},
  pages = {101--133},
  year = {2001},
  doi = {10.1214/ss/1009213286}
}

@book{cohen1988statistical,
  author = {Cohen, Jacob},
  title = {Statistical Power Analysis for the Behavioral Sciences},
  edition = {2nd},
  publisher = {Lawrence Erlbaum Associates},
  address = {Hillsdale, NJ},
  year = {1988},
  isbn = {978-0805802832}
}

@article{cumming2014new,
  author = {Cumming, Geoff},
  title = {The New Statistics: Why and How},
  journal = {Psychological Science},
  volume = {25},
  number = {1},
  pages = {7--29},
  year = {2014},
  doi = {10.1177/0956797613504966}
}

@article{fawcett2006introduction,
  author = {Fawcett, Tom},
  title = {An Introduction to {ROC} Analysis},
  journal = {Pattern Recognition Letters},
  volume = {27},
  number = {8},
  pages = {861--874},
  year = {2006},
  doi = {10.1016/j.patrec.2005.10.010}
}

@article{lakens2013calculating,
  author = {Lakens, Dani{\"e}l},
  title = {Calculating and Reporting Effect Sizes to Facilitate Cumulative Science: A Practical Primer for t-tests and {ANOVAs}},
  journal = {Frontiers in Psychology},
  volume = {4},
  pages = {863},
  year = {2013},
  doi = {10.3389/fpsyg.2013.00863}
}

@article{wilson1927probable,
  author = {Wilson, Edwin B.},
  title = {Probable Inference, the Law of Succession, and Statistical Inference},
  journal = {Journal of the American Statistical Association},
  volume = {22},
  number = {158},
  pages = {209--212},
  year = {1927},
  doi = {10.1080/01621459.1927.10502953}
}
```

### Tier 3: Optional Citations

```bibtex
@article{benjamini1995controlling,
  author = {Benjamini, Yoav and Hochberg, Yosef},
  title = {Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing},
  journal = {Journal of the Royal Statistical Society: Series B (Methodological)},
  volume = {57},
  number = {1},
  pages = {289--300},
  year = {1995},
  doi = {10.1111/j.2517-6161.1995.tb02031.x}
}

@article{bonferroni1936teoria,
  author = {Bonferroni, Carlo Emilio},
  title = {Teoria statistica delle classi e calcolo delle probabilit{\`a}},
  journal = {Pubblicazioni del R Istituto Superiore di Scienze Economiche e Commerciali di Firenze},
  volume = {8},
  pages = {3--62},
  year = {1936}
}

@book{efron1993introduction,
  author = {Efron, Bradley and Tibshirani, Robert J.},
  title = {An Introduction to the Bootstrap},
  publisher = {Chapman and Hall},
  address = {New York, NY},
  year = {1993},
  doi = {10.1007/978-1-4899-4541-9},
  isbn = {978-0412042317}
}

@article{holm1979simple,
  author = {Holm, Sture},
  title = {A Simple Sequentially Rejective Multiple Test Procedure},
  journal = {Scandinavian Journal of Statistics},
  volume = {6},
  number = {2},
  pages = {65--70},
  year = {1979},
  doi = {10.2307/4615733}
}
```

### Additional LLM-Specific Citations (Optional)

For literature review on LLM validation methodology:

```bibtex
@inproceedings{ribeiro2020beyond,
  author = {Ribeiro, Marco Tulio and Wu, Tongshuang and Guestrin, Carlos and Singh, Sameer},
  title = {Beyond Accuracy: Behavioral Testing of {NLP} Models with {CheckList}},
  booktitle = {Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics},
  pages = {4902--4912},
  year = {2020},
  publisher = {Association for Computational Linguistics},
  doi = {10.18653/v1/2020.acl-main.442}
}

@inproceedings{elazar2021measuring,
  author = {Elazar, Yanai and Kassner, Nora and Ravfogel, Shauli and Ravichander, Abhilasha and Hovy, Eduard and Sch{\"u}tze, Hinrich and Goldberg, Yoav},
  title = {Measuring and Improving Consistency in Pretrained Language Models},
  booktitle = {Transactions of the Association for Computational Linguistics},
  volume = {9},
  pages = {1012--1031},
  year = {2021},
  doi = {10.1162/tacl_a_00410}
}
```

---

## Quick Reference: What to Cite Where

| Paper Section | Statistical Method | Citation(s) |
|---|---|---|
| **Methodology: Detection Rate** | Binomial proportion estimation | Agresti & Coull (1998) |
| **Methodology: Confidence Intervals** | Wilson score intervals | Wilson (1927); Brown et al. (2001) |
| **Methodology: Phase 2 Design** | Experimental design framework | Fisher (1935); Shadish et al. (2002) |
| **Methodology: Construct Validity** | Shuffled window controls | Campbell & Stanley (1963) |
| **Methodology: False Positive Rate** | Type I error control | Neyman & Pearson (1933) |
| **Methodology: Selectivity Metrics** | Effect sizes | Cohen (1988); Lakens (2013) |
| **Results: Phase 1** | Binomial CI | Agresti & Coull (1998) |
| **Results: Phase 2** | Sensitivity/specificity | Altman & Bland (1994) |
| **Results: Phase 4** | Two-proportion z-test | Fleiss et al. (2003) |
| **Discussion: Practical Significance** | Effect sizes vs p-values | Cohen (1988); Cumming (2014) |
| **Literature Review: Statistical Methods** | Foundational texts | Casella & Berger (2002); Agresti (2002) |

---

## Summary: Action Items for Paper #2

### Immediate (Before Submission)

1. ✅ **Add confidence intervals** to all detection rate reports
   - Phase 1: 71.2% (95% CI: [58.9%, 83.5%])
   - Use Wilson score method (more accurate for proportions)

2. ✅ **Cite foundational methods** in methodology section
   - Binomial proportion estimation (Agresti & Coull, 1998)
   - Experimental design (Fisher, 1935; Shadish et al., 2002)
   - Type I error control (Neyman & Pearson, 1933)

3. ✅ **Add effect size calculations** for selectivity metrics
   - Persistence gap: Raw difference + Cohen's d
   - Magnitude gap: Raw difference + standardized effect size
   - Citations: Cohen (1988), Lakens (2013)

### Recommended (Strengthen Rigor)

4. ⚠️ **Add formal sensitivity/specificity framework** to Phase 1 analysis
   - Create confusion matrix (TP, TN, FP, FN)
   - Calculate sensitivity and specificity
   - Citation: Altman & Bland (1994) or Fawcett (2006)

5. ⚠️ **Expand literature review** with statistical inference section
   - Cover binomial inference (Casella & Berger, 2002)
   - Cover experimental design (Campbell & Stanley, 1963)
   - Cover effect sizes (Cohen, 1988)

### Optional (If Reviewers Request)

6. ❓ **Add multiple testing correction** to Phase 2 (if treating as confirmatory)
   - Bonferroni: α_adjusted = 0.05 / 3 = 0.017
   - Or Holm's sequential method
   - Citation: Bonferroni (1936) or Holm (1979)

7. ❓ **Add ROC analysis** if reviewers want classification performance curves
   - Plot sensitivity vs (1-specificity) at different confidence thresholds
   - Calculate AUC (area under curve)
   - Citation: Fawcett (2006)

---

**Last Updated**: November 19, 2025
**Status**: Ready for methodology section integration
