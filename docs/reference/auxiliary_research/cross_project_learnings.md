# Cross-Project Research Learnings

**Source**: AutoGen-Trader (AutoTrader-AgentEdge) practitioner research
**Date**: January 2026
**Purpose**: Inform academic research direction based on practitioner testing outcomes

---

## Executive Summary

The companion AutoGen-Trader project conducted extensive practitioner-based GEX testing (50M+ options records, 34 symbols, 5+ years). Key findings that inform our academic research:

| Finding | Status | Academic Implication |
|---------|--------|---------------------|
| GEX swing filter (Close→Close+1) | 🛑 STOP | Don't pursue overnight GEX signals |
| GEX + TSMOM hybrid | 🛑 STOP | Hybrid approaches underperform |
| Intraday GEX (Open→Close) | ❓ UNTESTED | **Primary research opportunity** |
| Gamma walls/flip points | ❓ UNTESTED | Maps to our per-strike analysis |
| UVXY leads SPY by 1 day | ✅ VALIDATED | Support for #181 volatility spillover |
| Rolling Z-score normalization | ❓ UNTESTED | Addresses stationarity gap |

---

## Invalidated Hypotheses (🛑 STOP)

These should NOT be pursued in the academic project:

### 1. GEX as Overnight Swing Filter

- **Test**: Close(t) signal → Execute at Close(t+1)
- **Result**: Median improvement -2.9% (makes performance worse)
- **Issue**: #516 in AutoGen-Trader
- **Reason**: Dealer rebalancing is **intraday**, not overnight

### 2. GEX + TSMOM Hybrid Strategy

- **Test**: Combine GEX regime with momentum signals
- **Result**: Underperforms both pure strategies
- **Issue**: #516, #519 in AutoGen-Trader

### 3. Academic TSMOM (12-month lookback)

- **Test**: Moskowitz et al. (2012) time-series momentum
- **Result**: 19% pass rate, -0.259 avg net Sharpe
- **Reason**: TSMOM is portfolio construction technique, not single-asset signal

---

## Validated Findings (✅ DONE)

These provide empirical support for our methodology:

### 1. GEX Volatility Impact

- **Finding**: 3.81x higher volatility in negative gamma periods
- **Finding**: 10.1x more extreme moves (>2% daily) in negative gamma
- **Data**: SPY 2020-2021, 4.73M options contracts
- **Supports**: Our regime classification approach (Paper 2)

### 2. Cross-Asset Regime Characteristics

| Asset Class | Positive Gamma | Persistence |
|-------------|----------------|-------------|
| Equity (SPY, QQQ) | 81.9% | ~8 days |
| Volatility (UVXY) | 32.8% | ~5 days |
| Bonds (TLT, IEF) | 85.2% | ~7.6 days |
| Commodities (GLD) | 53.8% | ~5.7 days |

### 3. UVXY→SPY Lead-Lag

- **Finding**: UVXY leads SPY by 1 day (0.456 correlation)
- **Supports**: Issue #181 (Volatility Spillover Signal)

---

## Untested Opportunities (❓ GAP)

These represent **primary research opportunities** for Papers 3-4:

### 1. Intraday GEX (Open→Close) - HIGH PRIORITY

**What practitioners actually claim**:

- Dealer rebalancing happens **during the day** as price approaches gamma concentrations
- "Fade the open" / "follow momentum" based on intraday GEX dynamics
- Edge is in **volatility prediction**, not direction

**What we could test**:

- LLM interpretation of intraday gamma dynamics
- Whether LLM can reason about dealer hedging timing
- Compare to overnight signal (which failed)

**Maps to**: Issue #116 (Intraday GEX Regime Shift Detection)
**Data needed**: Intraday options data (30-min or hourly snapshots)

### 2. Gamma Walls / Flip Points - HIGH PRIORITY

**What practitioners use**:

- Concentrated gamma at specific strikes acts as support/resistance
- Distance to "gamma flip" (zero gamma level) predicts volatility regime
- This is **spatial** information lost in scalar GEX

**What we could test**:

- LLM interpretation of gamma distribution shape
- Whether LLM can identify "walls" without explicit labeling
- Per-strike analysis vs aggregated GEX

**Maps to**: Issue #135 (Per-Strike GEX Analysis), Issue #29 (Flip Points)
**Data needed**: Full options chain with per-strike gamma

### 3. Rolling Z-Score Normalization - MEDIUM PRIORITY

**Mathematical gap identified**:

```python
# Raw GEX not stationary - market inflation affects thresholds
# A "High GEX" in 2020 might be "Low GEX" in 2025

gex_zscore = (gex - gex.rolling(252).mean()) / gex.rolling(252).std()
signal = gex_zscore > 1.5  # High relative to recent history
```

**What we could test**:

- Does LLM regime detection improve with normalized inputs?
- Can LLM implicitly normalize without explicit Z-scores?
- Threshold sensitivity under normalization

**Maps to**: Issue #114/115 (Sensitivity Analysis)
**Data needed**: Multi-year GEX time series (already have)

### 4. Continuous vs Binary Regime - MEDIUM PRIORITY

**Gap identified**:

- Binary classification (Positive/Negative) loses information
- "Slightly negative" gamma very different from "deeply negative"
- Distance to flip as continuous signal

**What we could test**:

- LLM confidence calibration with continuous GEX inputs
- Whether regime "intensity" improves predictions
- Probabilistic regime classification

**Maps to**: Paper 2 regime detection methodology
**Data needed**: Existing data, different presentation to LLM

---

## Mapping to Open Issues

| AutoGen-Trader Finding | gex-llm-patterns Issue | Status |
|------------------------|----------------------|--------|
| Intraday GEX untested | #116 (Intraday Regime Shift) | **Pursue** |
| Intraday GEX untested | #205 (Intraday Validation Framework) | **Pursue** |
| Per-strike / gamma walls | #135 (Per-Strike GEX Analysis) | **Pursue** |
| Flip point distance | #29 (Flip Points & Hedging Flow) | **Pursue** |
| UVXY lead-lag validated | #181 (Volatility Spillover Signal) | **Validated** |
| Cross-asset regimes | #182 (Regime-Conditional Correlation) | **Validated** |
| Stationarity concern | #114/115 (Sensitivity Analysis) | **Add scope** |
| Overnight swing failed | n/a | **Avoid** |

---

## Potential New Issues

Based on gaps not covered by existing issues:

### 1. GEX Stationarity & Normalization Study

**Scope**: Test if rolling Z-score normalization improves LLM regime detection
**Approach**: One-shot validation script
**Academic value**: Addresses reviewer concern about threshold stability
**Data**: Existing multi-year GEX data

### 2. Gamma Distribution Shape Analysis

**Scope**: Beyond scalar GEX - test if LLM interprets distribution characteristics
**Approach**: Per-strike data with kurtosis/skew metrics
**Academic value**: Novel contribution (practitioners use this, academics don't)
**Data**: Full options chain per-strike gamma

### 3. Continuous Regime Classification Validation

**Scope**: Compare binary vs continuous regime inputs for LLM
**Approach**: A/B test with existing validation framework
**Academic value**: Methodology improvement for Paper 2/3
**Data**: Existing data, different prompt structure

---

## Implementation Approach

### Agent vs One-Shot Script Decision

**Recommendation**: One-shot scripts for all proposed research

| Research Task | Approach | Rationale |
|--------------|----------|-----------|
| Stationarity study | One-shot | Single experiment, reproducible |
| Gamma distribution | One-shot | Data transformation + validation |
| Continuous regime | One-shot | A/B comparison, fixed methodology |
| Intraday validation | One-shot | Historical data analysis |

**Why not agents**:

- Academic research requires reproducibility
- Discrete experiments, not continuous processes
- Agent overhead not justified for validation tasks
- Keep thesis scope focused on LLM capability, not infrastructure

---

## Academic Rigor Opportunities

### Statistical Improvements from AutoGen-Trader

Their methodology corrections we should adopt:

1. **Look-ahead prevention**: `signals.shift(1)` for proper t+1 execution
2. **Transaction costs**: Turnover-proportional (not fixed)
3. **Div-by-zero protection**: EPSILON = 1e-9
4. **Robust reporting**: Median alongside mean for outlier-resistance

### Data Requirements for Academic Validation

| Research Area | Data Needed | Source | Status |
|--------------|-------------|--------|--------|
| Intraday regime | Hourly options snapshots | Alpha Vantage / CBOE | **Need** |
| Per-strike gamma | Full chain data | Existing SQLite | **Have** |
| Multi-year GEX | 2020-2025 daily | Existing | **Have** |
| Cross-asset | SPY, QQQ, TLT, GLD | Existing | **Have** |

---

## Conclusion

**Key takeaway**: AutoGen-Trader's practitioner testing has **narrowed our scope** significantly:

1. ✅ **Don't pursue**: Overnight swing signals, GEX+TSMOM hybrids
2. ✅ **Do pursue**: Intraday dynamics, per-strike analysis, gamma walls
3. ✅ **Validated**: Volatility regime impact, UVXY lead-lag, cross-asset regimes

This saves months of potential dead-end research and focuses Papers 3-4 on untested but promising directions.

---

## Related Documentation

- [practitioner_methods.md](practitioner_methods.md) - Practitioner vs academic methodology
- [gex_formula_comparison.md](gex_formula_comparison.md) - Formula sensitivity analysis
- [abandoned_research_paths.md](../abandoned_research_paths.md) - Full deferred research log

## Source Issues (AutoGen-Trader)

- #394: GEX Forward Testing (validated volatility impact)
- #501: Big Data GEX Pipeline (50M+ records)
- #516: GEX swing filter invalidation
- #519: Academic TSMOM failure
- #530: Intraday GEX opportunity (untested)
