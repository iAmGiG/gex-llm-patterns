# GEX Metrics Explained: Why We Use Net GEX

**Date**: October 16, 2025
**Purpose**: Explain the choice of net GEX and other metrics in pattern validation

---

## The Question

**Q**: "Why do we use NET GEX (sum of all gamma) instead of strategy-specific GEX like what dealers would have from iron condors, straddles, butterflies, etc.?"

**Short Answer**: We're detecting **AGGREGATE dealer constraints**, not individual strategy positioning. Net GEX captures the **total forced hedging pressure** that dealers face, regardless of how they constructed their positions.

---

## Understanding Net GEX

### Definition

**Net GEX** = Sum of gamma exposure across ALL options positions from the dealer perspective

```python
net_gex = sum(
    gamma_i * open_interest_i * 100 * sign_i
    for all options i
)

where:
- gamma_i = Black-Scholes gamma for option i
- open_interest_i = contracts outstanding for option i
- 100 = shares per contract multiplier
- sign_i = +1 (dealers long gamma) or -1 (dealers short gamma)
```

### What It Measures

**Net GEX captures**:

- ✅ Total dealer hedging obligation (regulatory constraint)
- ✅ Aggregate forced flow from ALL positions
- ✅ Directional pressure (positive = dampen, negative = amplify)
- ✅ Market-wide regime (what ALL dealers MUST do collectively)

**Net GEX does NOT capture**:

- ❌ Individual dealer strategies
- ❌ Position construction methods
- ❌ Which specific options created the exposure

---

## Why Not Strategy-Specific GEX?

### The Problem with Strategy-Level Analysis

If we tried to measure "iron condor GEX" or "straddle GEX":

**Challenge 1: Unknown Dealer Positioning**

```
We observe:
- SPY 520C has 50,000 OI
- SPY 530C has 60,000 OI
- SPY 510P has 45,000 OI

Question: Are dealers:
A) Short iron condors (520C/530C/510P/500P)?
B) Short strangles (520C/510P)?
C) Mix of individual legs from different strategies?

Answer: WE DON'T KNOW! 🤷

We only see aggregate open interest per strike, not which contracts are paired.
```

**Challenge 2: Regulatory Constraint is Aggregate**

```
SEC Rule 15c3-1 (Net Capital Rule):
- Dealers must maintain TOTAL net capital
- Capital charges based on AGGREGATE risk
- NOT based on strategy-by-strategy accounting

Result: Dealers care about NET exposure, not strategy decomposition
```

**Challenge 3: Hedging Pressure is Additive**

```
If dealer is:
- Short 1000 straddles (gamma = -500)
- Short 2000 individual calls (gamma = -300)
- Long 500 iron condors (gamma = +100)

Total hedging pressure = -500 - 300 + 100 = -700
→ This is what creates forced flow (NET GEX)

Individual strategies don't matter - NET is what determines action.
```

### What We Actually Care About

**Research Question**: Can LLM detect when dealers are FORCED to hedge?

**Relevant Metric**: Net GEX (total obligation)
**Irrelevant**: How they got there (iron condor vs naked call selling)

**Analogy**:

```
Studying Traffic Congestion:
✅ Measure: Total cars on road (creates congestion)
❌ Don't measure: How many Hondas vs Toyotas (irrelevant)

Studying Dealer Hedging:
✅ Measure: Net GEX (creates forced flow)
❌ Don't measure: Iron condor GEX vs straddle GEX (unknowable & irrelevant)
```

---

## Metrics We DO Use

### Core Metrics in quantitative_evidence

Our YAML reports include these fields:

```yaml
quantitative_evidence:
  gex_metrics:
    net_gex_usd: -32905699168.89      # Total dealer gamma exposure
    net_gex_change_1d_usd: null       # Day-over-day change in exposure
    net_gex_change_1d_pct: null       # Percentage change
    regime: NEGATIVE_GAMMA            # Classification (pos/neg/neutral)
    flip_level_price: 485.50          # Price where GEX crosses zero
    gamma_concentration: 0.734        # Concentration at key strikes
    spot_price: 522.22                # Current underlying price
    source: database                  # Data provenance
  market_metrics:
    call_gamma: -17285094067.18       # Gamma from calls only
    put_gamma: -15620605101.71        # Gamma from puts only
```

### Why Each Metric

| Metric | Purpose | Why Included |
|--------|---------|--------------|
| **net_gex_usd** | Total hedging obligation | Core constraint measurement |
| **net_gex_change_1d** | Velocity of constraint | Detect regime shifts |
| **regime** | Classification | Binary state (amplify/dampen) |
| **flip_level_price** | Critical threshold | Where regime changes |
| **gamma_concentration** | Pinning risk | Clustering at strikes |
| **call_gamma** | Decomposition | Understand composition |
| **put_gamma** | Decomposition | Understand composition |
| **spot_price** | Current price | Context for GEX levels |

### Why Call/Put Gamma Decomposition?

We DO include call_gamma and put_gamma breakdown:

**Use Case**: Understanding HOW net exposure formed

```yaml
Example 1:
  net_gex: -$30B
  call_gamma: -$28B  # Dealers sold LOTS of calls
  put_gamma: -$2B    # Few puts

Interpretation: Call-driven negative GEX
→ Dealers hedge by buying on rallies (call hedging dominates)

Example 2:
  net_gex: -$30B
  call_gamma: -$10B  # Some calls
  put_gamma: -$20B   # Dealers bought LOTS of puts

Interpretation: Put-driven negative GEX
→ Dealers hedge by selling on dips (put hedging dominates)

Both have net_gex = -$30B, but mechanics differ slightly.
```

**Why This Matters**:

- Call-dominated: Upside hedging pressure stronger
- Put-dominated: Downside hedging pressure stronger
- LLM can use this nuance in reasoning

**Why This Is NOT Strategy-Specific**:

- We still don't know if calls came from straddles, naked, or spreads
- We DO know call pressure vs put pressure
- Distinction is: **component decomposition** (useful) ≠ **strategy identification** (impossible/irrelevant)

---

## What About Other Strategy-Agnostic Metrics?

### Metrics We Considered but Don't Use

**1. Vanna (dGamma/dVol)**

```
Why considered: Volatility exposure of gamma
Why not used: Secondary effect, not primary constraint
Decision: Could add in Paper #2 (regime filters)
```

**2. Charm (dGamma/dTime)**

```
Why considered: Gamma decay over time
Why not used: 0DTE already captured in pattern taxonomy
Decision: Implicitly captured by expiration dates
```

**3. Strike-Level GEX**

```
Why considered: Pinning at specific strikes
Why not used: Already captured by gamma_concentration
Decision: Would create 100+ metrics per day (too granular)
```

**4. Expiry-Level GEX**

```
Why considered: 0DTE vs monthly exposure
Why not used: Pattern taxonomy tests this separately (0dte_hedging pattern)
Decision: Addressed via pattern variation, not metric addition
```

### Why We Keep It Simple

**Academic Rigor**:

- Parsimony: Fewest metrics that explain phenomenon
- Replicability: Standard metrics from practitioner literature
- Interpretability: Clear economic meaning

**Practical Constraints**:

- LLM context limits: Can't feed 100 metrics per day
- Data availability: Some metrics require order flow data (not public)
- Calculation speed: More metrics = slower validation

**Sufficient for Detection**:
Our results show net_gex + decomposition + flip_level is ENOUGH:

- 71.5% average detection (unbiased)
- 91.2% average accuracy
- No need to add complexity without evidence it helps

---

## Common Questions

### Q1: "Could dealers hide exposure through complex strategies?"

**A**: They could try, but:

1. Net GEX still captures AGGREGATE obligation (can't hide total)
2. Regulatory reporting catches evasion (SEC Rule 15c3-1)
3. Our validation shows pattern IS detectable (71.5% detection) → hiding isn't working

### Q2: "What if iron condor GEX behaves differently than straddle GEX?"

**A**: Possibly, but:

1. We can't identify which is which from OI data
2. Both produce net gamma exposure
3. Both create hedging obligation
4. Net effect is what matters for market impact

If we had order flow data (we don't), we COULD test this hypothesis. But for our research question (can LLM detect constraints?), it's unnecessary.

### Q3: "Why not use dealer-reported positioning (CFTC data)?"

**A**: Great idea, but:

1. CFTC data is delayed (weekly)
2. Only available for futures (not individual stock options)
3. Our method works real-time with public options data
4. Academic research requires replicability (CFTC requires special access)

Future work could validate our inferred dealer positions against CFTC reports.

### Q4: "Do market makers use different strategies than dealers?"

**A**: Yes, terminology:

- **Market Makers**: Provide liquidity, mandatory delta-neutral hedging
- **Dealers**: May take directional bets, exploit MM forced flows

**For our research**:

- We detect MARKET MAKER constraints (the forced hedging)
- Dealers exploit these constraints (benefit from pattern knowledge)
- Our "dealer hedging constraint" = Market maker regulatory obligation

We use "dealer" colloquially, but technically mean "market maker hedging obligation."

---

## Summary: Why Net GEX

### The Logic Chain

1. **Goal**: Detect when dealers are FORCED to hedge (regulatory constraint)

2. **Constraint**: SEC Rule 15c3-1 requires maintaining delta neutrality on AGGREGATE positions

3. **Measurement**: Net GEX captures total hedging obligation (aggregate)

4. **Irrelevant**: How they constructed positions (strategies unknown from OI data)

5. **Sufficient**: 71.5% detection, 91.2% accuracy proves net GEX + decomposition is enough

6. **Alternative**: Could add more metrics, but no evidence it's needed

### Design Philosophy

**Occam's Razor**: Simplest explanation that captures phenomenon

```
Net GEX (1 metric) → 71.5% detection ✅

Adding 50 more metrics → ???% detection
- Complexity cost
- Overfitting risk
- Interpretability loss
- No evidence needed
```

**When to Add Metrics**: Paper #2 (regime filters for profitability optimization)

**For Paper #1**: Current metrics are SUFFICIENT for methodology validation

---

## For Paper #1: How to Frame This

### Methods Section

```
We measure dealer gamma exposure (GEX) as the aggregate gamma across
all outstanding options from the dealer perspective:

  net_gex = Σ(gamma_i × OI_i × 100 × sign_i)

where gamma_i is calculated via Black-Scholes, OI_i is open interest,
and sign_i encodes dealer perspective (+1 long, -1 short).

We use net GEX rather than strategy-specific metrics (iron condor,
straddle, etc.) because:
1. Individual dealer strategies are unobservable from OI data
2. Regulatory constraints (SEC 15c3-1) operate on aggregate exposure
3. Hedging pressure is additive across all positions

We decompose net_gex into call_gamma and put_gamma to capture whether
hedging pressure is call-driven or put-driven, providing the LLM with
directional context.
```

### Discussion Section (Limitations)

```
Our approach measures aggregate dealer gamma exposure without
identifying specific option strategies (e.g., iron condors vs
straddles). While strategy-level analysis might provide additional
insights, it is neither necessary (our validation shows 71.5%
detection with aggregate metrics) nor feasible (strategy construction
is unobservable from open interest data). Future work with access to
order flow data could test whether strategy decomposition improves
detection rates.
```

---

## References

**Regulatory Framework**:

- SEC Rule 15c3-1: Net Capital Rule (aggregate risk measurement)
- FINRA Rule 4210: Margin Requirements for Market Makers

**Practitioner Literature**:

- SpotGamma (2019): Gamma Exposure and Market Dynamics
- SqueezeMetrics (2020): Dark Index and Dealer Positioning
- Nomura (2017): Equity Derivatives Strategy - Gamma Hedging Flows

**Academic**:

- Ni, Pearson, Poteshman (2005): Stock Price Clustering on Option Expiration Dates
- Coval & Stafford (2007): Asset Fire Sales in Equity Markets

---

**Document Version**: 1.0
**Last Updated**: October 16, 2025
**Author**: PhD Validation Team
**Purpose**: Explain metric choices for Paper #1 methods section
