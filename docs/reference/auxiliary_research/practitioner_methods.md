# Practitioner GEX Methods vs Academic Methodology

**Purpose**: Document practitioner approaches to GEX analysis for Paper 2 methodology justification.

**Last Updated**: December 2025

---

## Practitioner Sources

### Primary Sources (Grey Literature)

| Source | Platform | Focus |
|--------|----------|-------|
| @TailThatWagsDog | Twitter/X | Gamma exposure analysis, ThinkOrSwim scripts |
| SpotGamma | Commercial | Dealer positioning dashboards, GEX levels |
| SqueezeMetrics | Commercial | GEX methodology, DIX/GEX indicators |

### Citation Approach

These sources represent **practitioner knowledge** rather than peer-reviewed research. In academic papers, we reference them as:

- "Commercial analysis tools" (SpotGamma, SqueezeMetrics)
- "Practitioner methodology" (without formal citation)
- Frame as motivation: "Practitioners observe X; we test whether LLMs can understand WHY"

---

## Practitioner GEX Calculation

### Formula (from practitioner sources)

```python
GEX = Σ(Gamma × OpenInterest × 100 × Spot² × Direction)

Where:
- Direction: +1 for calls, -1 for puts
- Result: Net dealer gamma positioning in dollar terms
```

### Regime Classification

**Practitioner approach** (AutoGen-Trader implementation):

```python
# Regime based on call vs put GEX comparison
if net_call_gex > net_put_gex:
    regime = "POSITIVE_GAMMA"  # Dealers hedged on upside
elif net_call_gex < net_put_gex:
    regime = "NEGATIVE_GAMMA"  # Dealers hedged on downside
else:
    regime = "NEUTRAL"
```

### Signal Generation

Practitioners use **regime transitions** as trading signals:

```python
# Signal on regime TRANSITIONS (not just levels)
if current_regime != prev_regime:
    if current_regime == "POSITIVE_GAMMA":
        signal = "BUY"  # Enter long
    elif current_regime == "NEGATIVE_GAMMA":
        signal = "SELL"  # Exit or short
else:
    # Maintain position in current regime direction
    signal = "HOLD" if current_regime == "POSITIVE_GAMMA" else "FLAT"
```

### Validated Results (AutoGen-Trader)

Testing practitioner rules achieved:

- **TQQQ**: +1.019 Sharpe ratio (GEX-only strategy)
- Outperformed technical indicators (MACD, RSI, Momentum)
- Validates that GEX signals contain meaningful information

---

## Our Academic Methodology

### Formula (Paper 1-2)

```python
GEX_strike = Spot_Price × Gamma × OI × 100 × 0.01

Total_GEX = Σ(Call_GEX - Put_GEX)  # Aggregated across strikes
```

### Regime Classification

**Our approach** (from `docs/reference/technical/gex_calculations.md`):

```python
# Regime based on total GEX magnitude and sign
if total_gex > 1e9:       # > $1B positive
    regime = "POSITIVE_GAMMA_HIGH"
elif total_gex > 0:
    regime = "POSITIVE_GAMMA_LOW"
elif total_gex > -1e9:    # Negative but not extreme
    regime = "NEGATIVE_GAMMA_LOW"
else:                      # < -$1B negative
    regime = "NEGATIVE_GAMMA_HIGH"
```

### Key Differences

| Aspect | Practitioner | Our Methodology |
|--------|--------------|-----------------|
| Regime basis | net_call_gex vs net_put_gex | Total GEX sign + magnitude |
| Signal type | Regime transitions | Pattern detection by LLM |
| Goal | Trading alpha | Understanding mechanics |
| Validation | Sharpe ratio | Detection accuracy + materialization |

---

## Why Our Approach Differs

### Research Question Alignment

**Practitioner goal**: "Does this signal make money?"
**Our goal**: "Can LLMs understand WHY dealer constraints create patterns?"

Our methodology tests **understanding**, not profitability. We need:

1. Clear mechanical thresholds for LLM prompts
2. Testable predictions (materialization)
3. Obfuscation compatibility (no context-dependent signals)

### Paper 2 Validation

Our methodology produces **meaningful discrimination**:

- 2020 (pre-0DTE): 12.1% persistent regime detection
- 2024 (post-0DTE): 81.2% persistent regime detection
- 5.7x difference validates selectivity

This proves our calculation method captures real market structure changes.

### Avoiding Overfitting to Practitioner Models

From Paper 1 Related Work section:
> "Training or testing LLMs on higher-order Greeks risks overfitting to specific institutional implementations. A model detecting 'vanna flows' might simply memorize patterns from one dealer's model that fail to generalize."

Similarly, adopting practitioner-specific regime classifications could bias our LLM toward memorizing their signal patterns rather than understanding underlying mechanics.

---

## Cross-Project Coordination

### What AutoGen-Trader Tests

- Practitioner trading rules → alpha generation
- GEX VoterAgent (#419) → triple voting system
- Strategy comparison → which approach profits more

### What This Project Tests

- LLM understanding of market mechanics
- Obfuscation testing → genuine reasoning vs memorization
- Pattern materialization → detected patterns predict outcomes

### Shared Infrastructure

- Options data collection (Alpha Vantage, cached)
- GEX calculation formulas (mathematically equivalent)
- Historical databases (`gex_research.db`, `options_historical.db`)

---

## Implications for Future Papers

### Paper 2 (30-Day Regime Detection)

- **Cite practitioner methods** in Section 3 (Methodology) as alternative approach
- Explain why we use magnitude-based thresholds vs call/put comparison
- Reference AutoGen-Trader results as evidence GEX signals are meaningful

### Paper 3 (Per-Strike Analysis)

- Build on practitioner concept of "gamma walls" and "flip points"
- SpotGamma/SqueezeMetrics popularized these terms
- Our contribution: systematic academic validation of these concepts

### Paper 4+ (Future)

- Potential comparison study: practitioner rules vs LLM-detected patterns
- Could test if LLM understanding improves on practitioner heuristics
- Requires AutoGen-Trader baseline data as comparison

---

## References

### Academic (Citable)

- Ni, S. X., et al. (2005). "Stock Option Return Predictability"
- Garleanu, N., et al. (2009). "Demand-based option pricing"
- Barbon & Buraschi (2021). "Gamma fragility"

### Practitioner (Grey Literature - Reference Only)

- SpotGamma: <https://spotgamma.com/>
- SqueezeMetrics: <https://squeezemetrics.com/>
- @TailThatWagsDog: Twitter/X (archived in AutoGen-Trader Issue #352)

---

## Summary

Practitioner methods are **valuable reference points** that:

1. Validate GEX signals contain meaningful information (+1.019 Sharpe)
2. Provide established terminology (gamma walls, flip points, regimes)
3. Inform our methodology decisions (what to test, what to cite)

But our research asks a **different question** (understanding vs profitability), so we maintain our own methodology while acknowledging practitioners in related work.
