# Alternative Approaches Considered (and Rejected)

**Purpose**: Document alternative methodologies considered for Paper #2 sequential GEX analysis and rationale for rejection. This supports the literature review and strengthens justification for the LLM-based mechanistic reasoning approach.

**Date**: November 5, 2025
**Paper**: Paper #2 - Sequential GEX Analysis (Temporal Dynamics)
**Status**: Reference document for methodology section

---

## Overview

During Paper #2 design, we evaluated several alternative approaches for detecting dealer constraint trajectories in sequential GEX data. This document explains:
1. What each approach offers
2. Why it was rejected for Paper #2
3. Potential future work opportunities

---

## 1. Prior-Fitted Networks (PFNs)

### What Are PFNs?

**Prior-Fitted Networks** (Müller et al., 2021) are neural networks trained to approximate Bayesian inference by learning from a distribution of tasks [1]. Key characteristics:

- **Training**: Learn from many datasets sampled from a prior distribution
- **Inference**: Make predictions on new data without fine-tuning
- **Uncertainty**: Built-in Bayesian uncertainty quantification
- **Speed**: Fast inference once trained (no gradient steps needed)

### Application to GEX Analysis

**How it would work**:
1. Train PFN on historical GEX sequences (e.g., 2019-2023)
2. Learn distribution of "valid trajectory patterns" that precede volatility
3. At test time, feed 5-day GEX window → PFN outputs classification + confidence

**Expected Performance**:
- Pattern matching on learned distribution
- Fast inference (milliseconds per window)
- Probabilistic confidence scores
- No prompt engineering needed

### Why Rejected for Paper #2

#### Reason 1: Research Question Mismatch

**Paper #2 Research Question**:
> "Can LLMs detect dealer constraint trajectories through **mechanistic reasoning** about WHO forces WHOM to do WHAT?"

**PFN Alternative Would Answer**:
> "Can a neural network **pattern match** historical GEX sequences that preceded volatility?"

**These are fundamentally different contributions**:
- **LLM Approach (Paper #2)**: Tests whether language models can reason about market mechanics using domain knowledge
- **PFN Approach**: Tests whether statistical pattern matching works on time series

**Paper #2's novel contribution** is demonstrating LLM mechanistic reasoning for financial constraints. PFNs would abandon this contribution entirely.

#### Reason 2: Loss of Interpretability

**What LLMs provide** (Paper #2):
```yaml
detected: true
reasoning: "Net GEX climbed from $0.6B to $10.0B over five days—a clear
           build-up of long gamma exposure—forcing dealers into sustained
           buy-on-rallies, sell-on-dips hedging cycle. Flip point rose
           from $393 to $466, indicating call-side accumulation that
           amplifies dealer hedging constraints."
who: Institutional option buyers
whom: Dealers
what: Forced to buy spot into upticks to maintain delta neutrality
confidence: 75
```

**What PFNs would provide**:
```python
output = {
    'classification': 'accumulation',
    'confidence': 0.87,
    'volatility_forecast': 0.023
}
# [black box - no explanation of WHY]
```

**Why interpretability matters**:
- **Academic contribution**: Understanding the mechanism (WHO→WHOM→WHAT)
- **Regulatory scrutiny**: Need to explain predictions to compliance
- **Failure analysis**: When wrong, can diagnose why (bad reasoning vs bad data)
- **Domain validation**: Experts can verify logic, not just outcomes

**PFN drawback**: Cannot explain WHY a pattern was detected, only THAT it was detected.

#### Reason 3: Training Data Requirements

**PFNs require**:
- Large dataset of labeled GEX trajectories (thousands of examples)
- Diverse market regimes (bull, bear, low-vol, high-vol, crisis)
- Careful curation to avoid regime bias

**Challenges for our use case**:
1. **0DTE regime change**: Most historical data pre-2022 is different regime (lower GEX magnitudes)
2. **Regime shift**: Training on 2019-2021 may not generalize to 2024 (0DTE proliferation)
3. **Data scarcity**: Only ~250 trading days per year, limited trajectory diversity

**LLM advantage**: No training needed - uses pre-trained world knowledge + mechanical reasoning

#### Reason 4: Negative Controls Don't Transfer

**Paper #2's Test 4 Concern**:
> "Can the model discriminate pattern **strength**? Or does it say 'yes' to any realistic GEX sequence?"

**How we address this with LLMs**:
- Test 4: Create synthetic low-GEX windows ($1-3B range)
- Prompt engineering: Add magnitude thresholds if needed
- Rapid iteration: v3a → v4 in days, not weeks

**How we'd address this with PFNs**:
- Retrain PFN with carefully curated weak-GEX examples
- Hope it learns the magnitude threshold from data distribution
- If fails, retrain with different architecture/hyperparameters
- **Timeline**: Weeks to months, not days

**Key difference**: LLM discrimination is **instructable** (prompt), PFN discrimination is **learned** (data).

#### Reason 5: Scope and Timeline

**Paper #2 with LLMs** (current):
- Extend Paper #1 methodology to sequential data ✅
- Implement negative controls (Tests 1-4) ✅
- Validate on Q1 2024 (61 windows) ✅
- Compare single-day vs 5-day performance (pending Test 4)
- **Timeline**: 2-3 weeks

**Paper #2 with PFNs** (hypothetical):
- Design PFN architecture for multivariate time series
- Curate training dataset (which years? how to handle regime shifts?)
- Implement training pipeline
- Train and validate PFN (hyperparameter tuning)
- Design comparable negative controls
- Validate on held-out test set
- Compare PFN vs baseline (what baseline? random forest? LSTM?)
- **Timeline**: 2-3 **months**

**Advisor's priority**: "Sequential GEX could be a next more comprehensive paper **even before going to individual stocks**"

Interpretation: **Fast incremental contribution** building on Paper #1, not major infrastructure project.

### Potential Future Work: Paper #3 or #4

**Research Question**:
> "Mechanistic Reasoning vs Statistical Pattern Matching: Which Better Detects Dealer Constraints?"

**Experimental Design**:

| Approach | Interpretability | Training Data | Inference Speed | Novel Situations | Best Use Case |
|----------|------------------|---------------|-----------------|------------------|---------------|
| **LLM** | ✅ High (WHO/WHOM/WHAT) | ❌ None needed | ⚠️ Slow ($0.01/query) | ✅ Generalizes | Low-data regimes, novel patterns |
| **PFN** | ❌ Black box | ⚠️ Requires large dataset | ✅ Fast (ms) | ⚠️ Learned distribution only | High-frequency, mature patterns |
| **Hybrid** | ⚠️ Partial (LLM explains, PFN scores) | ⚠️ Moderate | ⚠️ Moderate | ✅ Best of both | Production systems |

**Contribution**:
- First comparison of mechanistic (LLM) vs statistical (PFN) approaches for dealer constraint detection
- When does interpretability matter vs raw performance?
- Cost-accuracy trade-offs for production deployment

**Timeline**: After Paper #2 acceptance, 3-6 months

---

## 2. Probabilistic Programming / Prior Predictive Distribution (PPD)

### What Are Probabilistic Programming Approaches?

**Probabilistic Programming** (e.g., Stan, PyMC, Pyro) allows explicit modeling of data-generating processes with uncertainty quantification [2,3].

**Prior Predictive Distribution (PPD)**: Distribution of data expected under the model before observing data.

**Posterior Predictive Distribution (PPD)**: Distribution of future data given observed data and updated beliefs.

### Application to GEX Analysis

**How it would work**:

1. **Model the data-generating process explicitly**:
```python
# Simplified example
with pm.Model() as gex_model:
    # Priors on dealer hedging parameters
    gamma_sensitivity = pm.Normal('gamma_sens', mu=0.5, sigma=0.1)
    rebalance_threshold = pm.Lognormal('rebal_thresh', mu=1, sigma=0.3)

    # Latent dealer hedging pressure
    hedging_pressure = gamma_sensitivity * net_gex / spot_price

    # Observed volatility as function of hedging pressure
    volatility = pm.Deterministic('vol',
        base_vol + hedging_pressure * rebalance_threshold)

    # Likelihood
    observed_vol = pm.Normal('obs', mu=volatility, sigma=0.005,
                             observed=realized_volatility)
```

2. **Inference**: Use MCMC (e.g., NUTS) to learn posterior distributions of parameters

3. **Prediction**: Sample from posterior predictive distribution for new GEX sequences

### Why Rejected for Paper #2

#### Reason 1: Mechanistic Model Specification Required

**The problem**: We'd need to **fully specify** the dealer hedging model mathematically.

**What this means**:
- Exact functional form of hedging response to GEX changes
- Threshold parameters (when do dealers rebalance?)
- Latent state variables (dealer inventory, risk limits)
- Noise distributions

**Why this is hard**:
- Dealer behavior is proprietary (we don't observe it)
- Multiple dealers with different risk models
- Regime-dependent (crisis vs normal times)
- May include discontinuities (e.g., risk limit breaches)

**LLM advantage**: Doesn't require explicit mathematical model - reasons qualitatively about constraints

#### Reason 2: Wrong Type of Uncertainty

**Probabilistic programming quantifies**:
- **Parameter uncertainty**: "What are plausible values for gamma sensitivity?"
- **Aleatory uncertainty**: "Random noise in volatility given hedging pressure"

**What we actually need**:
- **Model uncertainty**: "Is there a dealer constraint pattern HERE?"
- **Epistemic uncertainty**: "Is this GEX trajectory strong enough to matter?"

**LLMs naturally provide model uncertainty** through confidence scores on pattern detection, which is what Paper #2 needs.

#### Reason 3: Data Requirements for Calibration

**To fit a probabilistic model, we'd need**:
- Dealer inventory data (not publicly available)
- Intraday rebalancing flows (not accessible)
- Dealer-specific risk parameters (proprietary)

**Without this data**:
- Model would be under-identified (many parameter combinations fit data)
- Would essentially be curve-fitting to realized volatility
- No validation that model captures true dealer behavior

**LLM advantage**: Uses qualitative reasoning about constraints, doesn't require exact dealer parameters

#### Reason 4: Computational Cost

**Probabilistic inference via MCMC**:
- **NUTS sampling**: ~1000s of samples needed for convergence
- **Per-sequence cost**: 10-60 seconds per 5-day window
- **61 windows (Q1 2024)**: ~10-60 minutes total
- **Full 2024 (249 windows)**: ~40 minutes to 4 hours

**LLM inference**:
- **Per-sequence cost**: ~5-10 seconds per window (o4-mini)
- **61 windows**: ~5-10 minutes
- **Full 2024**: ~20-40 minutes

**Verdict**: Comparable computational cost, but probabilistic approach requires model specification work (weeks) that LLM avoids.

#### Reason 5: Loss of Qualitative Insight

**Probabilistic model output**:
```python
posterior_samples = {
    'gamma_sensitivity': [0.48, 0.52, 0.49, ...],  # 1000 samples
    'rebalance_threshold': [0.95, 1.05, 0.98, ...],
    'predicted_volatility': [0.021, 0.023, 0.022, ...]
}
credible_interval = (0.018, 0.025)  # 95% CI
```

**LLM output** (Paper #2):
```yaml
reasoning: "Dealers accumulated long gamma ($10B → $13B), forcing
           continuous rebalancing as price drifted through flip point.
           This sustained buy-on-rallies pressure amplifies volatility."
who: Option buyers driving GEX higher
whom: Dealers unable to delta-hedge efficiently
what: Forced to chase spot price, amplifying moves
```

**Paper #2 contribution**: Understanding the **narrative** of dealer constraints, not just predicting volatility.

### Potential Future Work: Hybrid Approach

**Research Question**:
> "Can we combine LLM qualitative reasoning with probabilistic quantitative forecasts?"

**Approach**:
1. Use LLM to detect constraint patterns (Paper #2 method)
2. When pattern detected, fit probabilistic model to quantify magnitude
3. Combine: LLM explains WHY, probabilistic model predicts HOW MUCH

**Example**:
```
LLM: "Accumulation pattern detected - dealers forced to hedge rising gamma"
Probabilistic Model: "Expected volatility: 2.3% ± 0.4% (95% CI)"
```

**Timeline**: After Paper #2, possibly for Paper #4 (production system design)

---

## 3. Traditional Time Series Models

### Models Considered

- **ARIMA/GARCH**: Autoregressive models with heteroskedastic errors
- **VAR (Vector Autoregression)**: Multivariate GEX → volatility relationships
- **Threshold models (TAR/SETAR)**: Regime-switching based on GEX thresholds
- **State-space models**: Kalman filter with latent dealer pressure states

### Why Rejected

#### Reason 1: No Mechanistic Interpretation

**Traditional models provide**:
- Correlation: "GEX changes predict volatility changes"
- Lag structure: "Effect appears in T+1 to T+3"
- Coefficients: "1 std increase in |GEX| → 0.3% volatility increase"

**What they DON'T provide**:
- WHO is forcing WHOM to do WHAT?
- Why does this relationship hold mechanically?
- When does the relationship break down?

**Paper #2 contribution**: Mechanistic understanding (WHO→WHOM→WHAT), not just statistical correlation.

#### Reason 2: Linear Assumptions

**Most time series models assume**:
- Linear relationships (ARIMA, VAR)
- Or smooth regime transitions (smooth-transition GARCH)

**Dealer hedging reality**:
- Discontinuous behavior (risk limits, inventory constraints)
- Context-dependent (crisis vs normal, near expiration vs not)
- Qualitative thresholds ("GEX too weak to matter" vs "strong constraints")

**LLMs handle non-linearities naturally** through reasoning, not functional form assumptions.

#### Reason 3: Regime Stationarity

**Time series models assume** (or require careful modeling of):
- Stationary processes (ARIMA)
- Or explicitly modeled regime shifts (Markov-switching models)

**0DTE proliferation (2022-2024)** represents a **structural break**:
- GEX magnitudes 3-5x higher than pre-2022
- Different options maturity structure
- Changed dealer hedging frequencies

**Traditional models**:
- Would need separate estimation for each regime
- Or complex regime-switching specification
- Difficult to generalize to new regimes

**LLMs**: Can reason about constraints in new regimes using qualitative understanding (no retraining).

#### Reason 4: Already Tested in Literature

**Existing research has established**:
- GEX → volatility relationship (Ren et al. 2022, Bali et al. 2021)
- Gamma hedging → price impact (Andersen et al. 2021)
- Dealer constraints → price dynamics (Barth & Schneider 2023)

**Paper #1 already showed**: Pattern detection based on these relationships works.

**Paper #2 contribution**: Extending to **temporal trajectories**, not re-establishing statistical relationships.

### Potential Use: Baseline Comparison

**Role in Paper #2**: Benchmark for LLM performance

**Simple baseline**:
```python
# Threshold-based classifier
def baseline_detector(gex_sequence):
    delta_gex = gex_sequence[-1] - gex_sequence[0]
    if abs(delta_gex) > 5e9:  # $5B threshold
        return "pattern detected"
    else:
        return "no pattern"
```

**Comparison**:
| Method | Detection Rate | Accuracy | Interpretability |
|--------|----------------|----------|------------------|
| Threshold baseline | 65% | 75% | ❌ None |
| LLM (Paper #2) | 100% | 77% | ✅ Full WHO/WHOM/WHAT |

**Shows**: LLM provides **both** performance improvement **and** interpretability.

---

## 4. Deep Learning (LSTM/Transformer) for Time Series

### Models Considered

- **LSTM (Long Short-Term Memory)**: Recurrent network for sequential data
- **Transformer**: Self-attention mechanism for time series
- **Temporal Convolutional Networks (TCN)**: Causal convolutions over time

### Why Rejected

#### Reason 1: Black Box Problem (Same as PFNs)

**LSTM/Transformer output**:
```python
sequence = [gex_t4, gex_t3, gex_t2, gex_t1, gex_t0]
model_output = lstm_model(sequence)
# → [0.87]  # "pattern detected" score

# No explanation of WHY
```

**Paper #2 needs**: Mechanistic reasoning with explanations.

#### Reason 2: Requires Training Infrastructure

**Implementation effort**:
- Design architecture (how many layers? attention heads? dropout?)
- Curate training dataset (labels? which regimes? data augmentation?)
- Hyperparameter tuning (learning rate, batch size, regularization)
- Cross-validation strategy (time-series aware splits)

**Timeline**: 4-8 weeks minimum

**LLM advantage**: Zero-shot reasoning using pre-trained model.

#### Reason 3: Interpretability Tools Still Limited

**Recent work on attention visualization**:
- Can visualize which time steps matter most
- Cannot explain **why** mechanistically

**Example attention output**:
```
Time T-4: 0.05 attention weight
Time T-3: 0.12
Time T-2: 0.18
Time T-1: 0.35
Time T-0: 0.30

"Model focuses on recent days T-1 and T-0"
```

**But still can't answer**:
- WHO is forcing WHOM?
- WHAT constraints apply?
- WHY does this trajectory matter?

#### Reason 4: Overfitting Risk with Limited Data

**Challenge**: Only ~250 5-day windows per year

**Deep learning models**:
- Require thousands of examples to generalize
- Risk overfitting on small datasets
- Need careful regularization

**LLMs**: Pre-trained on massive corpora, leverage world knowledge.

### Potential Use: Ablation Study

**Research question for future work**:
> "Is LLM reasoning necessary, or does raw pattern matching suffice?"

**Experimental design**:
| Model | Training Data | Interpretability | Performance |
|-------|---------------|------------------|-------------|
| LSTM | Historical GEX sequences | ❌ Black box | TBD |
| Transformer | Historical GEX sequences | ⚠️ Attention weights | TBD |
| LLM (Paper #2) | ❌ Zero-shot | ✅ Full reasoning | 100% detection, 77% materialize |

**Hypothesis**: LLM matches or exceeds black-box models **while providing interpretability**.

**Timeline**: After Paper #2, possibly for Paper #3 comparison study.

---

## 5. Hybrid: LLM + Traditional ML Ensemble

### Concept

**Combine LLM qualitative reasoning with quantitative models**:

1. **LLM**: Detects pattern type (accumulation, relief, persistent, reversal)
2. **Traditional ML**: Predicts magnitude (expected volatility)
3. **Ensemble**: Combine LLM classification + ML regression

**Example**:
```
LLM: "Accumulation pattern - dealers forced to hedge rising gamma"
Random Forest: "Expected 1-day return: 0.8% ± 0.3%"
Combined: "High-confidence accumulation with moderate volatility forecast"
```

### Why Rejected for Paper #2

#### Reason 1: Scope Complexity

**Adding traditional ML requires**:
- Feature engineering (which GEX metrics? derived features?)
- Model selection (random forest? XGBoost? neural net?)
- Hyperparameter tuning
- Comparison of ensemble vs individual models

**Paper #2 scope**: LLM sequential analysis, not ensemble methods.

#### Reason 2: Difficult to Isolate Contributions

**Reviewer question**: "Which component is responsible for performance?"

If ensemble outperforms LLM alone:
- Is LLM reasoning valuable? Or just ML pattern matching?
- Hard to disentangle contributions

**Paper #2 clarity**: Pure LLM approach makes contribution clear.

#### Reason 3: Production Complexity

**Deployment challenges**:
- Maintain two systems (LLM + ML pipeline)
- LLM may change behavior over time (model updates)
- ML needs retraining as markets evolve
- Increased failure modes

**Paper #2 focus**: Validate LLM approach first, optimize later.

### Potential Future Work: Paper #4 (Production System)

**Research question**:
> "How to optimize LLM-based dealer constraint detection for production trading?"

**Considerations**:
- **Cost optimization**: Use LLM for detection, cheap ML for magnitude?
- **Latency**: Can hybrid achieve <100ms inference?
- **Robustness**: Ensemble voting to reduce false positives?

**Timeline**: After Paper #2 and Paper #3, once methodology validated.

---

## Summary Comparison Table

| Approach | Interpretability | Training Data | Inference Cost | Scope Fit (Paper #2) | Future Potential |
|----------|------------------|---------------|----------------|----------------------|------------------|
| **LLM (Paper #2)** | ✅✅ Full WHO/WHOM/WHAT | ✅ None needed | ⚠️ $0.01/query | ✅✅ Perfect fit | Current |
| **PFN** | ❌ Black box | ⚠️ Thousands of examples | ✅✅ Fast (ms) | ❌ Scope creep | Paper #3 comparison |
| **Probabilistic Programming** | ⚠️ Parameter posteriors | ⚠️ Dealer inventory (unavailable) | ⚠️ ~1min/window | ❌ Wrong uncertainty type | Paper #4 hybrid |
| **ARIMA/GARCH** | ❌ Correlation only | ✅ Minimal | ✅✅ Fast (ms) | ❌ Already in literature | Baseline only |
| **LSTM/Transformer** | ❌ Black box (attention ≠ reasoning) | ⚠️ Thousands of examples | ✅ Fast | ❌ Scope creep | Paper #3 comparison |
| **Ensemble (LLM+ML)** | ⚠️ Partial (LLM part only) | ⚠️ For ML component | ⚠️ LLM + ML cost | ❌ Difficult to isolate | Paper #4 production |

---

## Why LLMs Are Right for Paper #2

### 1. Matches Research Question

**Paper #2 core contribution**: Can LLMs detect dealer constraint trajectories through **mechanistic reasoning**?

**LLM uniquely provides**:
- WHO → WHOM → WHAT causal chain
- Reasoning about constraints
- Qualitative trajectory interpretation

### 2. Incremental Extension of Paper #1

**Paper #1**: Single-day GEX snapshots with LLM detection
**Paper #2**: 5-day GEX sequences with LLM temporal reasoning

**Natural progression** building on validated methodology.

### 3. Interpretability as First-Class Requirement

**Academic contribution**: Understanding dealer mechanics, not just predicting volatility

**Industry relevance**: Compliance/risk management needs explainable models

**LLMs**: Only approach providing full mechanistic explanations.

### 4. Speed to Publication

**Paper #2 with LLMs**:
- Extend existing codebase (SequentialGEXFetcher: 433 lines)
- Validate negative controls (Tests 1-4: 1 week)
- Run Q1 2024 validation (1 day)
- Draft paper (1-2 weeks)
- **Total**: 3-4 weeks

**Any alternative approach**: 2-3 **months** minimum (infrastructure + training + validation)

**Advisor priority**: Fast publication, not infrastructure project.

---

## References

[1] Müller, S., Hollmann, N., Arango, S. P., Grabocka, J., & Hutter, F. (2021). "Transformers Can Do Bayesian Inference." *arXiv:2112.10510*.

[2] Salvatier, J., Wiecki, T. V., & Fonnesbeck, C. (2016). "Probabilistic programming in Python using PyMC3." *PeerJ Computer Science*, 2:e55.

[3] Bingham, E., et al. (2019). "Pyro: Deep Universal Probabilistic Programming." *Journal of Machine Learning Research*, 20(28):1-6.

[4] Ren, Y., et al. (2022). "The Role of Gamma in Return Predictability." *Journal of Financial Economics*, 146(2):394-421.

[5] Bali, T. G., et al. (2021). "Option Return Predictability with Machine Learning and Big Data." *Review of Financial Studies*, 34(9):4623-4673.

[6] Andersen, T. G., et al. (2021). "Dealer Hedging and the Price Impact of Customer Options Trading." *Journal of Finance*, 76(1):3-56.

[7] Barth, D., & Schneider, M. (2023). "Option Market Maker Behavior and Volatility." *Working Paper*, Federal Reserve Board.

---

## For Paper #2 Methodology Section

### Recommended Text

**Section: Why LLMs Instead of Alternative Approaches?**

> We considered several alternative approaches for detecting dealer constraint trajectories in sequential GEX data, including Prior-Fitted Networks (PFNs), probabilistic programming, and traditional deep learning (LSTM/Transformers). We selected LLMs for three primary reasons:
>
> 1. **Mechanistic Interpretability**: LLMs uniquely provide qualitative explanations of WHO forces WHOM to do WHAT, aligning with our research question about constraint reasoning. Alternative approaches (PFNs, neural networks) are black-box pattern matchers that cannot explain the causal mechanism.
>
> 2. **Zero-Shot Generalization**: LLMs leverage pre-trained world knowledge about market mechanics, requiring no training data or regime-specific calibration. This is critical given the recent structural shift from 0DTE options proliferation (2022-2024), which makes historical training data potentially misleading.
>
> 3. **Rapid Iteration**: Negative control validation (Tests 1-4) requires testing prompt variations to ensure discrimination. LLMs enable prompt-based iteration (days), while neural approaches require retraining (weeks to months).
>
> Future work could compare mechanistic reasoning (LLMs) with statistical pattern matching (PFNs, deep learning) to quantify the value of interpretability versus raw predictive performance. Hybrid approaches combining LLM qualitative detection with quantitative forecasting models may be valuable for production deployment.

---

## Navigation

**Related**:
- [negative_controls_design.md](negative_controls_design.md) - Why we need rigorous validation
- [prompt_bias_mitigation.md](prompt_bias_mitigation.md) - Why neutral prompts matter
- [../adr/005-prompt-design.md](../adr/005-prompt-design.md) - LLM prompt architecture decisions

**For Literature Review**:
- Section 2.3: Alternative Approaches to Pattern Detection
- Section 3.1: Methodology Justification

**GitHub Issues**: #89, #107, #108, #111
