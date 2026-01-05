# GEX Formula Comparison: Theory vs Implementation

**Purpose**: Document exact differences between our methodology, practitioner approaches, and academic theory.

---

## The Three Approaches

### 1. Our Implementation (Paper 2)

**Source**: [gex_calculator.py:120-130](../../src/gex/gex_calculator.py#L120)

```python
# Calculate dealer GEX per contract
dealer_gex = (
    -1
    * open_interest
    * bs_gamma            # Black-Scholes gamma
    * (underlying_price**2)  # S² scaling
    * 0.01                # 1% move factor
    * 100                 # Contract multiplier
)

# Weight by call/put type
weighted_gex = dealer_gex * (+1 if call else -1)

# Net GEX = sum(weighted_gex)
```

**Paper 2 Formula** ([03_Methodology.tex:56-60](../papers/paper2/latex/03_Methodology.tex#L56)):

```text
GEX = Σ ± OI_i × Γ_i × S² × 0.01 × 100
```

### 2. Practitioner Implementation (AutoGen-Trader)

**Source**: AutoGen-Trader `dask_gex_calculator.py:300-406`

```python
# Simple weighted gamma
weighted_gamma = gamma * open_interest  # No S², no 0.01, no 100

# Normalized by total OI
total_gex = total_weighted_gamma / total_oi

# Call/put breakdown (also normalized)
net_call_gex = call_weighted_gamma / call_oi
net_put_gex = put_weighted_gamma / put_oi

# Regime from net difference
net_gamma = net_call_gex - net_put_gex
regime = "POSITIVE_GAMMA" if net_gamma > 0 else "NEGATIVE_GAMMA"
```

### 3. Academic Theory (Citations)

**Ni et al. (2005)** - Stock Price Clustering on Option Expiration:

- Studies delta-hedging pressure near expiration
- Does not provide explicit GEX formula (focuses on price effects)

**Anderegg & Sokolov (2022)** - SqueezeMetrics:

- Commercial/practitioner methodology
- Cited as "standard market microstructure practice" in Paper 2

**SpotGamma (2021)** - Understanding Gamma Exposure:

- Commercial documentation
- Popular practitioner reference

**Fishman (2023)** - Goldman Sachs Equity Derivatives:

- Institutional dealer perspective
- "All You Ever Wanted To Know About Gamma"

---

## Key Differences

| Factor | Our Implementation | Practitioner | What It Means |
|--------|-------------------|--------------|---------------|
| **S² scaling** | Yes | No | We measure dollar exposure, they measure relative positioning |
| **0.01 factor** | Yes | No | We scale to 1% move, they don't |
| **100 multiplier** | Yes | No | We convert to shares, they stay in contracts |
| **Normalization** | No | Yes (÷ OI) | They normalize to remove position size effects |
| **Regime threshold** | Magnitude-based (>$5B) | Sign-based (net_gamma > 0) | Different definitions of "regime" |

---

## What Each Measures

### Our Approach: Dollar GEX

```text
"How many dollars must dealers hedge for every 1% move in the underlying?"

Example: GEX = -$15B
Meaning: Dealers must buy $15B of stock for every 1% drop
         (short gamma = amplifying volatility)
```

### Practitioner Approach: Relative GEX

```text
"What is the relative gamma positioning normalized by open interest?"

Example: net_gamma = 0.15
Meaning: Net positive gamma bias of 15% (call gamma > put gamma)
         Regime = POSITIVE_GAMMA
```

---

## Why Both Are Valid

**Dollar GEX (ours)** is useful for:

- Measuring absolute hedging pressure
- Comparing across different price levels
- LLM pattern detection (magnitude matters for thresholds)

**Relative GEX (practitioners)** is useful for:

- Comparing across different symbols
- Detecting regime transitions
- Trading signals (direction matters more than magnitude)

---

## What Paper 2 Actually Uses

From [03_Methodology.tex:52-72](../papers/paper2/latex/03_Methodology.tex#L52):

```tex
\subsection{GEX Calculation Methodology}

Following standard market microstructure practice~\cite{anderegg2022impact,spotgamma2021},
we calculate dealer gamma exposure from end-of-day open interest:

\begin{equation}
\text{GEX} = \sum_i \pm \text{OI}_i \times \Gamma_i \times S^2 \times 0.01 \times 100
\end{equation}

...

\subsubsection{Methodology Limitations}

This \textit{open interest-based} approach (GEX\_OI) measures dealer inventory
positioning rather than intraday flow.
```

**Key point**: Paper 2 acknowledges this is ONE approach (GEX_OI) and that alternatives exist (GEX_VOL, intraday flow).

---

## Regime Classification Difference

### Our Approach (magnitude-based)

```python
# From gex_calculator.py:376-390
if normalized_gex > long_gamma_threshold:
    regime = "Long Gamma"
elif normalized_gex < short_gamma_threshold:
    regime = "Short Gamma"
else:
    regime = "Neutral Gamma"
```

Thresholds are configurable (default: 0.0001 normalized)

### Practitioner Approach (sign-based)

```python
# From AutoGen-Trader dask_gex_calculator.py:414-422
if net_gamma > 0:
    regime = "POSITIVE_GAMMA"
elif net_gamma < 0:
    regime = "NEGATIVE_GAMMA"
else:
    regime = "NEUTRAL"
```

Pure sign-based, no magnitude threshold.

---

## Paper 2's 30-Day Regime Criteria

Paper 2 uses **additional criteria** beyond simple GEX sign ([03_Methodology.tex:17-41](../papers/paper2/latex/03_Methodology.tex#L17)):

1. **Persistence**: ≥70% days same sign (21/30 days)
2. **Magnitude**: ≥$5B average |GEX|
3. **Stability**: ≤5 sign flips

This is MORE selective than practitioner approach (which just uses daily sign).

---

## The "Right" Way?

**There is no single "right" formula.** Both measure dealer gamma, but:

| Question | Best Formula |
|----------|--------------|
| "How much hedging pressure in dollars?" | Our approach (S² scaling) |
| "Which direction is gamma tilted?" | Practitioner approach (normalized) |
| "Is there a persistent regime?" | Paper 2 approach (multi-criteria) |

**Our research question** (can LLMs understand mechanics?) uses magnitude-based thresholds because:

1. LLM prompts need concrete numbers (not just signs)
2. Obfuscation testing strips context (magnitude provides signal)
3. 30-day regime detection requires persistence + magnitude + stability

---

## Validation Through Results

**Both approaches produce meaningful results:**

| Approach | Result | Interpretation |
|----------|--------|----------------|
| Paper 2 | 12.1% (2020) vs 81.2% (2024) | Our formula discriminates between market eras |
| AutoGen-Trader | +1.019 Sharpe (TQQQ) | Practitioner formula produces alpha |

This suggests BOTH formulas capture real market structure, just measuring different aspects.

---

## Recommendations

1. **For Paper 2 citation**: Keep current methodology, acknowledge practitioner alternatives in Section 3
2. **For Issue #29**: Document both formulas, allow configuration choice
3. **For future work**: Compare formula performance (Paper 4 candidate?)

---

## References

**Academic:**

- Ni, Pearson, Poteshman (2005) - Stock Price Clustering on Option Expiration
- Dim, Marsh, Schrimpf (2025) - Zero Days to Expiration Options

**Practitioner:**

- Anderegg & Sokolov (2022) - SqueezeMetrics Technical Report
- SpotGamma (2021) - Understanding Gamma Exposure
- Fishman (2023) - Goldman Sachs Equity Derivatives

**Implementation:**

- `src/gex/gex_calculator.py` - Our implementation
- AutoGen-Trader `dask_gex_calculator.py` - Practitioner implementation
