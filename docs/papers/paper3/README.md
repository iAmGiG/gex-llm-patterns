# Paper 3: Comprehensive Research Planning

**Status**: 📋 Planned (Q2-Q3 2026)
**Dependencies**: Paper 2 complete

---

## Scope Clarification: Two Research Tracks

There is **numbering inconsistency** between documentation and GitHub issues. This document covers BOTH interpretations:

### Track A: Cross-Asset Generalization (Canonical Roadmap)

Per `research_roadmap.md`, Paper 3 = **Cross-Asset Generalization**:

- Test obfuscation methodology on individual stocks (AAPL, MSFT, NVDA, TSLA)
- Compare index (SPY) vs single-name dealer dynamics
- ~10-20 stocks × 242 days = 2,420-4,840 tests

**Working Title**: "Cross-Asset Validation of LLM Market Microstructure Understanding"

### Track B: Intraday/Per-Strike Analysis (GitHub Issues)

Many GitHub issues labeled `[Paper #3]` cover **intraday/per-strike analysis**:

- Intraday regime shift detection (#116)
- Per-strike GEX distribution (#135, #221)
- Continuous vs binary classification (#222)
- Supplementary signals (#226, #228)

**Working Title**: "Intraday Dealer Gamma Dynamics: Per-Strike Analysis and Regime Shift Detection"

### Resolution Options

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **Combined Paper 3** | Both tracks in one paper | Comprehensive | Scope creep risk |
| **Paper 3A + 3B** | Split into two papers | Clear separation | More papers |
| **Paper 3 + 4** | Cross-asset = P3, Intraday = P4 | Follows roadmap | Delays intraday |

**Recommendation**: Discuss with advisor. Document covers both tracks below.

---

# TRACK A: Cross-Asset Generalization

## Research Questions (Track A)

1. Does obfuscation testing generalize beyond SPY index options?
2. Do dealer constraints differ between index and single-name options?
3. Can LLMs detect stock-specific vs market-wide patterns?

## Asset Selection

### Tier 1: High Liquidity (Primary)

| Sector | Symbols | Rationale |
|--------|---------|-----------|
| Tech | AAPL, MSFT, NVDA, TSLA, AMD | High options volume |
| Finance | JPM, BAC, GS | Different dealer dynamics |
| Consumer | AMZN, META | Retail + institutional mix |

### Tier 2: Secondary (If Time)

| Sector | Symbols | Rationale |
|--------|---------|-----------|
| Healthcare | UNH, JNJ | Defensive, different volatility |
| Energy | XOM, CVX | Commodity-linked |
| Consumer Staples | WMT, COST | Low volatility comparison |

## Methodology (Track A)

### Validation Framework

Reuse Paper 2 methodology with adjustments:

- 30-day regime windows per stock
- Same regime criteria (>70% same sign, magnitude threshold, ≤5 flips)
- **Adjust magnitude thresholds** per stock (different option volumes)

### Key Differences: Index vs Single-Name

| Aspect | SPY (Index) | Single-Name |
|--------|-------------|-------------|
| Dealer base | Broad, diversified | Concentrated |
| Hedging focus | Market-making | Directional hedging |
| 0DTE volume | Constant, high | Variable, lower |
| Liquidity | Ultra-liquid | Fragmented |
| Gamma dynamics | Smooth | More volatile |
| Correlation | Market beta ~1.0 | Varies by stock |

### Hypotheses (Track A)

1. **Detection rates similar** across liquid names (methodology generalizes)
2. **Single-name shows idiosyncratic patterns** (stock-specific events)
3. **Index detection reflects market-wide** dynamics, single-name is specific

## Data Requirements (Track A)

| Data | Source | Status | Estimate |
|------|--------|--------|----------|
| Single-stock options chains | Alpha Vantage / vendor | Partial | ~10 stocks available |
| 2+ years history | Required | TBD | |
| Greeks (gamma, delta, OI) | Required | TBD | |

## Timeline (Track A)

| Phase | Duration |
|-------|----------|
| Data collection (10 stocks) | 2-3 weeks |
| Validation runs | 1-2 weeks |
| Analysis | 2-3 weeks |
| Writing | 3-4 weeks |
| **Total** | **8-12 weeks** |

## Expected Contributions (Track A)

1. **Generalization proof**: Methodology works beyond single asset
2. **Cross-asset comparison**: Index vs single-name dealer dynamics
3. **Pattern persistence analysis**: Universal vs asset-specific constraints

---

# TRACK B: Intraday/Per-Strike Analysis

## Research Questions (Track B)

### Primary Question

**Can LLMs detect intraday dealer gamma regime shifts, and does this improve prediction compared to EOD-only analysis?**

### Secondary Questions

1. Does per-strike gamma distribution improve detection over aggregate GEX?
2. Are practitioner gamma "walls" predictive of support/resistance?
3. Does continuous regime classification outperform binary?
4. Can supplementary signals (SABR ρ, GAMMA-SVIX divergence) improve detection?

---

## Consolidated GitHub Issues (Track B)

### Core Research Issues

| Issue | Title | Status | Priority |
|-------|-------|--------|----------|
| #116 | Intraday GEX Regime Shift Detection | CONCEPT | **Primary** |
| #135 | Per-Strike GEX Analysis and Intraday Dynamics | CONCEPT | **Primary** |
| #221 | Gamma Distribution Shape Analysis | CONCEPT | High |
| #222 | Continuous vs Binary Regime Classification | CONCEPT | High |
| #223 | Intraday GEX Validation (Open→Close) | CONCEPT | High |

### Supplementary Signal Issues

| Issue | Title | Status | Priority |
|-------|-------|--------|----------|
| #226 | SABR Parameters (ρ, ν) as Regime Indicators | CONCEPT | Medium |
| #228 | GAMMA-SVIX Divergence as Regime Indicator | CONCEPT | Medium |

### Infrastructure Issues

| Issue | Title | Status | Priority |
|-------|-------|--------|----------|
| #156 | Multi-Asset Architecture | CONCEPT | Medium |
| #205 | Intraday Pattern Validation Framework | CONCEPT | Medium |

---

## Methodology (Track B)

### 1. Intraday Data Collection (#116)

**Approach**: 4 snapshots per trading day

```text
Snapshots:
- 9:45 AM  (post-open stabilization)
- 12:00 PM (midday)
- 3:00 PM  (pre-close)
- 4:00 PM  (close)
```text

**Data Requirements**:

- Per-strike gamma, delta, OI at each snapshot
- Underlying price at each snapshot
- Volume between snapshots

**Open Questions**:

- [ ] Which vendors provide intraday options Greeks?
- [ ] Cost structure for 4 daily snapshots vs EOD?
- [ ] Sufficient history for paper-length study (6-12 months minimum)?

### 2. Per-Strike Analysis (#221, #135)

**Beyond Scalar GEX**:

```python
# Current (Paper 2): Single number
total_gex = sum(gamma * oi * spot^2 * 0.01 * 100)

# Proposed: Distribution metrics
gamma_kurtosis = kurtosis(per_strike_gamma)
gamma_skew = skew(per_strike_gamma)
gamma_concentration = max(per_strike_gamma) / total_gex
dominant_strike = strike_with_max_gamma
distance_to_dominant = (spot - dominant_strike) / spot
```text

**Gamma Wall Detection**:

```python
def calculate_gamma_walls(chain_df, spot_price, threshold_pct=0.10):
    """
    Identify strikes with concentrated gamma (>10% of total).
    Practitioners claim these act as support/resistance.
    """
    total_gamma = chain_df['gamma'].abs().sum()
    chain_df['gamma_pct'] = chain_df['gamma'].abs() / total_gamma
    walls = chain_df[chain_df['gamma_pct'] > threshold_pct]
    return walls
```text

**Validation**:

1. Do gamma walls correlate with price respect levels?
2. Does distribution shape predict next-day volatility?
3. Does per-strike input improve LLM detection?

### 3. Continuous Regime Classification (#222)

**Binary (Current)**:

```python
regime = "POSITIVE" if net_gex > 0 else "NEGATIVE"
```text

**Continuous (Proposed)**:

```python
# Distance to flip point
flip_distance = (spot - zero_gamma_level) / spot

# Regime intensity (magnitude)
regime_intensity = abs(flip_distance)

# Probabilistic confidence
regime_confidence = sigmoid(flip_distance * scale_factor)
```text

**Hypothesis**: Continuous regime signals improve LLM confidence calibration.

### 4. Supplementary Signals (#226, #228)

**SABR Parameters (ρ, ν)**:
| Parameter | Interpretation | Signal Use |
|-----------|----------------|------------|
| ρ (Rho) | Vol-Spot correlation | Directional bias |
| ν (Nu) | Vol-of-vol | Jump risk / uncertainty |

**GAMMA-SVIX Divergence**:
| Condition | Interpretation |
|-----------|----------------|
| Normal | GAMMA and SVIX inversely correlated (-0.89) |
| Divergence | Regime transition signal |
| +5σ divergence | Extreme event (mispriced vol premium) |

---

## Proposed Experiments

### Experiment 1: Intraday Regime Flip Detection

**Setup**:

- Input: 9:45 AM + 12:00 PM snapshots (partial day)
- Target: Predict regime flip by 4:00 PM
- Baseline: EOD-only prediction

**Metrics**:

- Detection accuracy (did flip occur?)
- Timing accuracy (predicted window vs actual)
- Price impact correlation (flip → move size)

### Experiment 2: Per-Strike vs Aggregate Comparison

**Setup**:

- Condition A: LLM receives aggregate GEX only
- Condition B: LLM receives per-strike distribution + aggregate
- Same validation framework as Paper 2

**Metrics**:

- Detection rate difference (A vs B)
- Confidence calibration improvement
- Gamma wall identification accuracy

### Experiment 3: Continuous vs Binary Classification

**Setup**:

- Condition A: Binary regime labels
- Condition B: Continuous regime intensity + flip distance
- A/B test with identical prompts otherwise

**Metrics**:

- Calibration improvement (confidence vs outcome)
- Detection rate stability
- LLM reasoning quality (qualitative)

### Experiment 4: Supplementary Signal Value

**Setup**:

- Baseline: GEX-only prompts
- +SABR: Add ρ, ν parameters
- +SVIX: Add GAMMA-SVIX divergence
- Combined: All signals

**Metrics**:

- Incremental detection improvement per signal
- Diminishing returns analysis
- Computational cost vs accuracy tradeoff

---

## Data Requirements

### Intraday Options Data

| Requirement | Source | Status | Cost |
|-------------|--------|--------|------|
| Per-strike Greeks (4x daily) | TBD | **UNKNOWN** | **UNKNOWN** |
| Historical depth (6-12 months) | TBD | **UNKNOWN** | **UNKNOWN** |
| Underlying price (intraday) | Yahoo/existing | Available | Free |

**Critical Blocker**: Intraday options data access and cost

### Supplementary Data

| Requirement | Source | Status |
|-------------|--------|--------|
| SVIX data | CBOE | TBD |
| SABR calibration | Compute from chain | Available |
| Flip point calculation | Existing code | Available |

---

## Technical Implementation

### Phase 1: Data Pipeline (2-3 weeks)

- [ ] Identify intraday options data vendor
- [ ] Build 4-snapshot collection pipeline
- [ ] Implement per-strike storage schema
- [ ] Validate data quality (Greeks consistency)

### Phase 2: Feature Engineering (1-2 weeks)

- [ ] Implement gamma distribution metrics (kurtosis, skew, concentration)
- [ ] Build gamma wall detector
- [ ] Calculate continuous regime features (flip distance, intensity)
- [ ] Integrate SABR calibration (if pursuing)

### Phase 3: Validation Framework (2-3 weeks)

- [ ] Extend Paper 2 validation for intraday windows
- [ ] Build A/B test infrastructure (per-strike vs aggregate)
- [ ] Implement continuous regime prompts
- [ ] Create supplementary signal integration

### Phase 4: Experiments (3-4 weeks)

- [ ] Run Experiment 1: Intraday flip detection
- [ ] Run Experiment 2: Per-strike comparison
- [ ] Run Experiment 3: Continuous classification
- [ ] Run Experiment 4: Supplementary signals

### Phase 5: Analysis & Writing (3-4 weeks)

- [ ] Statistical analysis of results
- [ ] Identify key findings and contributions
- [ ] Draft paper sections
- [ ] Create figures and tables

---

## Expected Contributions

### Academic

1. **First systematic study** of intraday dealer gamma dynamics
2. **Per-strike analysis** bridges practitioner intuition with academic rigor
3. **Continuous regime classification** improves LLM calibration
4. **Supplementary signals** (SABR, SVIX) add predictive value

### Methodological

1. **Intraday obfuscation framework** extends Paper 2 methodology
2. **Per-strike prompt design** for distribution-aware LLM reasoning
3. **Multi-signal integration** pattern for complex regime detection

### Practical

1. **Earlier detection** of regime shifts (9:45 AM signal vs EOD)
2. **Gamma wall validation** confirms/refutes practitioner claims
3. **Actionable alpha** from intraday regime flip prediction

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Intraday data unavailable/expensive | Medium | **Blocking** | Identify vendors early, fallback to EOD per-strike only |
| Per-strike doesn't improve over aggregate | Medium | Reduces contribution | Document as negative result, focus on intraday |
| LLM struggles with distribution input | Low | Medium | Simplify to key metrics (wall distance, intensity) |
| SABR/SVIX data access issues | Medium | Low | These are supplementary, can proceed without |

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Data vendor investigation | 2 weeks | None |
| Data pipeline | 2-3 weeks | Vendor confirmed |
| Feature engineering | 1-2 weeks | Pipeline complete |
| Validation framework | 2-3 weeks | Features complete |
| Experiments | 3-4 weeks | Framework complete |
| Analysis & writing | 3-4 weeks | Experiments complete |
| **Total** | **13-18 weeks** | |

**Realistic Start**: After Paper 2 writing complete (Q2 2026)
**Target Submission**: Q3 2026

---

## GNN Enhancement (Contingent)

If baseline LLM detection is insufficient (<70% accuracy), consider GNN enhancement:

**Architecture** (from `gh_issues/intraday_regime_gnn.md`):

- Nodes: Strike prices with significant OI
- Edges: Gamma concentration relationships
- Temporal: 4 snapshots as graph sequence

**Trigger to pursue**:

- LLM baseline < 70% on intraday flip prediction
- Per-strike structure proves critical for prediction
- Advisor recommends methodological diversity

**Reference**: `docs/reference/auxiliary_research/gnn_literature_review.md`

---

## Related Documentation

- [Paper 2 Methodology](../paper2/methodology.md) - Regime criteria foundation
- [GNN Literature Review](../../reference/auxiliary_research/gnn_literature_review.md) - Enhancement options
- [Dissertation Backlog](../../dissertation/dissertation-research-backlog.md) - Timeline context
- [Research Roadmap](../research_roadmap.md) - Paper sequencing

---

## Open Questions for Advisor

1. **Scope**: Should intraday and per-strike be combined or separate papers?
2. **Data**: Budget for intraday options data (critical blocker)?
3. **Timeline**: Q3 2026 realistic given Paper 2 completion needs?
4. **Contribution**: Is per-strike analysis sufficient novelty alone?

---

**Last Updated**: 2026-01-14
**Next Review**: After Paper 2 writing milestone
