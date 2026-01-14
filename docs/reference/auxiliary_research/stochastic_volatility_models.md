# Stochastic Volatility Models: Research Notes

**Source**: Academic literature review (January 2026)
**Status**: Auxiliary research - informs methodology, potential Paper 5
**Relevance**: High for 0DTE/intraday analysis (Paper 3)

---

## Executive Summary

Deep dive into stochastic volatility model comparison for options pricing, with focus on short-dated (0DTE/1DTE) options. Key findings inform GEX analysis methodology and potential LLM input features.

**Key Takeaway**: SABR for short-dated, Heston for long-dated. Rough volatility models have structural limitations. SABR parameters (ρ, ν) could serve as LLM regime indicators.

---

## Model Comparison Overview

| Model | Best For | Weakness | Dissertation Relevance |
|-------|----------|----------|------------------------|
| **Black-Scholes** | Baseline quoting | Structurally inconsistent with vol surfaces | Current GEX baseline |
| **SABR** | Short-dated (<3mo), rates | No mean reversion, approximation breaks at wings | **High** - 0DTE/1DTE focus |
| **Heston** | Equity, long-dated, path-dependent | Struggles with steep short-term skew | Medium - longer expiries |
| **Bates** | Short-dated with jumps | More complex calibration | High - jump effects in 0DTE |
| **Rough Heston** | Joint SPX/VIX calibration | Computationally expensive, structural limits | Low - complexity vs benefit |

> "SABR for short maturities, Heston for long maturities - a mixture doesn't improve."
> — Columbia FE Notes

---

## SABR Model Details

### Parameters

| Parameter | Interpretation | LLM Signal Potential |
|-----------|----------------|---------------------|
| α (Alpha) | ATM volatility level | Regime magnitude |
| β (Beta) | CEV parameter (0=normal, 1=lognormal) | Market structure |
| **ρ (Rho)** | Vol-Spot correlation (skew driver) | **Directional bias signal** |
| **ν (Nu)** | Vol-of-vol (smile curvature) | **Jump risk indicator** |

### Empirical Example (SPX 1DTE, Jan 12 2026)

| Parameter | Value | Interpretation |
|-----------|-------|----------------|
| Alpha | 0.3222 | ATM vol elevated at 32% |
| Beta | 0.5000 | Balanced CEV |
| **Rho** | **0.9690** | Near-maximum positive - extreme call demand |
| Nu | 0.6107 | High vol-of-vol clustering |

> **ρ = 0.97 indicates market expects vol to RISE with spot** (unusual call-side demand, potential squeeze setup).

### SABR Limitations

- Hagan approximation degrades for high vol, long maturity, deep OTM
- "Wing effect" not captured - smile rises at extreme strikes
- Each forward needs separate calibration
- Can admit butterfly arbitrage at extreme strikes

### Dissertation Connection

**SABR ρ and ν as LLM input features**:

- Extreme ρ (>0.9 or <-0.9) could signal directional conviction
- High ν could indicate jump risk pricing
- These parameters complement GEX regime classification

---

## Heston Model Details

### SDE Formulation

```text
dS_t = μS_t dt + √v_t S_t dW_t^S
dv_t = κ(θ - v_t)dt + σ√v_t dW_t^v
```

### Parameters

| Parameter | Interpretation |
|-----------|----------------|
| κ (kappa) | Mean reversion speed |
| θ (theta) | Long-run variance |
| σ (sigma) | Vol-of-vol |
| ρ (rho) | Correlation (skew) |
| v_0 | Initial variance |

### Key Properties

- Closed-form solution via characteristic function
- Mean-reverting variance (realistic)
- Captures volatility clustering
- Reduces pricing error ~25% vs Black-Scholes
- **Limitation**: Always overprices short-term options

> "Heston captures longer-dated skew well but struggles with steep near-term skew."

---

## Jump-Diffusion Models (Merton, Bates)

For ultra-short-dated options, **jumps dominate diffusion**.

### Merton (1976)

- Adds Poisson jumps to GBM
- Produces volatility smile
- Jump risk assumed diversifiable

### Bates (1991) = Heston + Merton

| Component | Controls |
|-----------|----------|
| Jump part | Short-term smile (<1 year) |
| Stoch vol | Long-term smile (>1 year) |

> "SVJ models improve pricing accuracy especially for short-dated and OTM options where jump impact is pronounced."

### Dissertation Relevance

For Paper 3 (intraday dynamics), Bates model may better capture 0DTE behavior than pure SABR or Heston.

---

## Rough Volatility Models

### Rough Heston / Rough Bergomi

Replace Brownian motion with fractional BM (Hurst parameter H < 0.5).

| Model | Key Feature |
|-------|-------------|
| Rough Bergomi | 3 params: H, η, ρ - H controls ATM skew decay |
| Rough Heston | Derived from Hawkes microstructure |

### Critical Finding

> "Rough volatility models are INCONSISTENT with global shape of SPX smiles. They suffer severe structural limitations - the Hurst parameter H controls the smile in a poor way."

**Specific Issues**:

- Fail to create sufficiently pronounced term structure
- Short-expiry SPX smiles are MORE symmetric than long-expiry (models can't reproduce)
- SPX ATM skew incompatible with power-law shape from roughness
- Standard rough Bergomi produces flat VIX smile (market shows upward slope)

### Dissertation Relevance

**Low priority** - complexity doesn't justify benefits for current scope.

---

## 0DTE Academic Research (2024-2025)

### Key Papers

1. **Dim, Eraker, Vilkov (2024)** - "0DTEs: Trading, Gamma Risk and Volatility Propagation"
   - MM inventory gamma is positive on average, negatively related to future intraday vol
   - Positive gamma → price reversal; Negative gamma → momentum
   - **Consistent with delta-hedging, NOT information-based trading**

2. **CBOE Research (2024)** - "Much Ado About 0DTEs"
   - 0DTE volume: 5% (2016) → 50%+ (2024)
   - Flow is "remarkably balanced" between buy/sell
   - Balanced flow = net zero gamma risk despite large volume

3. **2025 Pricing Framework** - "Revisiting local expansions for 0DTE pricing"
   - Semi-analytical framework: local-in-time expansions + jump-diffusion
   - Validated on intraday SPX, DAX, Euro Stoxx 50

### Consensus Finding

> "0DTE options do NOT destabilize markets. Higher 0DTE gamma linked to REDUCED intraday volatility."

### Statistical Finding (2024)

- 242/253 trading days (95.6%): Negative GEX < -$2B
- Mean GEX: -$19.87B (range: -$40.69B to -$4.75B)
- **Persistent negative gamma regime** = structural shift from historical alternation

### Dissertation Relevance

**HIGH** - Directly supports Paper 3 (Issue #223: Intraday GEX Validation).
The Dim, Eraker, Vilkov findings align with our regime detection methodology.

---

## Practitioner Insight: GAMMA-SVIX Divergence

**Source**: @TailThatWagsDog (Twitter/X practitioner analysis, January 2026)

### Key Finding

Practitioners track the divergence between aggregate GAMMA exposure and SVIX (VIX of VIX) implied volatility as a regime indicator:

| Metric | Observed Value | Interpretation |
|--------|----------------|----------------|
| GAMMA vs SVIX IV correlation | -0.89 | Strong inverse relationship |
| Current divergence | +5σ | EXTREME divergence event |
| VRP (Volatility Risk Premium) | Elevated | Premium selling opportunity |

### Mechanism

1. **Normal regime**: GAMMA and SVIX move inversely (negative correlation)
2. **Divergence**: When correlation breaks down, signals regime transition
3. **+5σ divergence**: Extreme - either GAMMA too high or SVIX IV too low
4. **VRP edge**: Large divergence suggests mispriced volatility premium

### LLM Signal Potential

| Signal | What It Measures | Regime Implication |
|--------|------------------|-------------------|
| GAMMA-SVIX correlation | Structural relationship health | Normal vs stressed markets |
| Divergence magnitude (σ) | Deviation from normal | Transition probability |
| VRP direction | Premium buyer vs seller edge | Positioning bias |

### Dissertation Connection

**Potential LLM input features**:

- Real-time GAMMA-SVIX divergence as regime transition indicator
- Complements SABR ρ (skew) and GEX regime classification
- Could serve as "meta-signal" for LLM confidence calibration

**Research Question**: Does LLM regime detection improve when given GAMMA-SVIX divergence context alongside raw GEX data?

---

## Neural Network Calibration

### The Calibration Bottleneck

Classical calibration is slow (minutes per surface).

### Deep Learning Solutions

| Approach | Speed | Accuracy |
|----------|-------|----------|
| Classical | Minutes | Baseline |
| Horvath et al. (2021) | Milliseconds | Comparable |
| DML (Huge & Savine) | Milliseconds | Better than standard DL |
| Residual Learning (2025) | 10x less training data | Comparable |

### Differential Machine Learning (DML)

- Train on features, labels, AND differentials (∂label/∂feature)
- Dramatically reduces Heston calibration time
- Outperforms classical deep learning

### Chebyshev Tensors

- 100x more efficient than DNNs for rough Bergomi
- Similar accuracy

### Dissertation Relevance

**Infrastructure** - Not directly relevant to LLM interpretation thesis, but could support real-time GEX analysis in companion project.

---

## Research Directions

### For Dissertation (Papers 3-4)

| Topic | Research Question | Priority | Paper |
|-------|-------------------|----------|-------|
| SABR ρ as LLM input | Does extreme ρ improve regime detection? | High | Paper 3 |
| 0DTE volatility dynamics | Validate Dim et al. findings with our data | High | Paper 3 |
| Model selection rationale | Document why SABR/Heston chosen | Medium | Methodology |

### For Companion Project (AutoTrader-AgentEdge)

| Topic | Research Question | Priority |
|-------|-------------------|----------|
| SABR Calibration | Replicate PDF analysis framework | High |
| Heston Comparison | Same data, compare vol surface fit | High |
| DNN Calibration | Real-time surface fitting | Medium |

### Potential Paper 5 (Post-Dissertation)

**Title**: "Stochastic Volatility Model Selection for Ultra-Short-Dated Options: An Empirical Study"

**Contribution**: Systematic comparison of SABR, Heston, Bates for 0DTE/1DTE SPX options with neural network calibration.

**Timeline**: After Papers 2-4 completion

---

## Implementation Notes

### For GEX Analysis Tool

- SABR ρ = 0.97 signals unusual market structure
- High ν (vol-of-vol) suggests jump risk pricing
- Negative butterfly indicates pin risk (ATM > wings)

### Model Selection Heuristic

| Condition | Recommended Model |
|-----------|-------------------|
| 0-7 DTE, extreme skew | SABR + Jump component |
| 7-30 DTE | Heston or SABR |
| >30 DTE | Heston |
| VIX calibration needed | Rough Heston / Grey Bergomi |
| Real-time requirement | DNN-calibrated Heston |

---

## Key Academic Sources

- [Heston (1993)](https://www.ma.imperial.ac.uk/~ajacquie/IC_Num_Methods/IC_Num_Methods_Docs/Literature/Heston.pdf) - Original closed-form solution
- [SABR Wikipedia](https://en.wikipedia.org/wiki/SABR_volatility_model) - Parameter interpretation
- [Rough Volatility Empirical Analysis](https://www.tandfonline.com/doi/full/10.1080/14697688.2022.2081592) - SPX/VIX calibration
- [0DTE Research (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstractid=4692190) - Gamma dynamics
- [Deep Learning Calibration](https://arxiv.org/abs/2309.07843) - Neural network approach
- [Columbia FE Notes](http://www.columbia.edu/~mh2078/ContinuousFE/LocalStochasticJumps.pdf) - Model comparison

## Practitioner Sources

- @TailThatWagsDog (Twitter/X) - GAMMA-SVIX divergence analysis, VRP regime indicators

---

## Related Issues

- #223: Intraday GEX Validation (Open→Close)
- #221: Gamma Distribution Shape Analysis
- #228: GAMMA-SVIX Divergence as LLM Regime Indicator
- #116: Intraday GEX Regime Shift Detection
- #135: Per-Strike GEX Analysis

## See Also

- [cross_project_learnings.md](cross_project_learnings.md) - AutoGen-Trader findings
- [practitioner_methods.md](practitioner_methods.md) - Practitioner vs academic approaches
