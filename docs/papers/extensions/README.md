# Research Extensions — Forward-Looking Directions

> **Snapshot as of April 2026.** The dissertation defense proposal has been made. This folder captures research directions that extended the published work but were not pursued within the scope of this repository. It consolidates earlier planning material (previously in `paper3/` and `paper4/`) into a single snapshot.

---

## Published Foundation

These directions build on the two papers anchored in this repository:

- **Paper 1** — *Validating LLM Understanding of Market Microstructure Through Obfuscation Testing* — IEEE BigData 2025 Workshop (published). Single-day dealer constraint detection, 71.5% detection / 91.2% predictive accuracy, 726 evaluations.
- **Paper 2** — *Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation* — AIAI 2026 (accepted, camera-ready May 2026), JRFM (MDPI, under review). Multi-day regime detection across 2020–2025, 2,221 evaluations, 69.1pp discrimination between 2020 (12.1%) and 2024 (81.2%), documents 0DTE-driven market structure evolution.

---

## Extension Track A — Cross-Asset Generalization

**Core question:** Does temporal obfuscation testing generalize beyond SPY index options to individual equities?

**Rationale.** Paper 2 validated on SPY only. Single-name dealer dynamics differ from index dealer dynamics — more concentrated dealer base, directional (not market-making) hedging, variable 0DTE participation, fragmented liquidity. Whether structural reasoning findings persist across these conditions is a direct generalizability test.

**Proposed asset tiers:**

| Sector | Symbols |
|--------|---------|
| Tech | AAPL, MSFT, NVDA, TSLA, AMD |
| Finance | JPM, BAC, GS |
| Consumer | AMZN, META |
| Defensive (secondary) | UNH, JNJ, WMT, COST |

**Method.** Reuse Paper 2 regime criteria (persistence ≥ 0.70, stability ≤ 5 flips), with magnitude thresholds calibrated per-stock to reflect different options volumes. Run the same five-phase validation framework.

**Open hypotheses:**

1. Detection rates remain high on liquid names (methodology generalizes across index vs single-name).
2. Single-name detection reveals idiosyncratic (stock-specific) patterns absent from index analysis.
3. Index detection captures market-wide dealer behavior; single-name captures asset-specific constraints.

---

## Extension Track B — Intraday and Per-Strike Analysis

**Core question:** Can LLMs detect intraday dealer gamma regime shifts, and does per-strike input improve detection over aggregate GEX?

**Rationale.** Paper 2 used end-of-day open-interest-based GEX, aggregated to a scalar per window. Practitioners work with continuous intraday data and per-strike distributions (gamma concentration at specific strikes is often cited as support/resistance). Whether this extra granularity helps LLMs reason — or introduces noise — is an open question.

### B1. Intraday regime shift detection

- Four daily snapshots: 09:45 ET, 12:00, 15:00, 16:00
- Input: partial-day snapshots (09:45 + 12:00)
- Target: regime flip by close
- Baseline: end-of-day-only prediction

### B2. Per-strike distribution analysis

Replace scalar GEX with distribution-aware features:

```python
gamma_kurtosis    = kurtosis(per_strike_gamma)
gamma_skew        = skew(per_strike_gamma)
gamma_concentration = max(per_strike_gamma) / total_gex
dominant_strike   = strike_with_max_gamma
flip_distance     = (spot - dominant_strike) / spot
```

Validate whether gamma walls (strikes with >10% of total gamma) correlate with observed price respect levels.

### B3. Continuous versus binary regime classification

Binary labels (POSITIVE / NEGATIVE) vs continuous features (distance-to-flip, regime intensity, sigmoid confidence). Hypothesis: continuous signals improve LLM confidence calibration.

### B4. Supplementary signals

- **SABR parameters (ρ, ν)** — directional bias and vol-of-vol as additional regime indicators
- **GAMMA / SVIX divergence** — normal correlation is ≈−0.89; divergences above 5σ may signal regime transitions

**Critical blocker.** Intraday per-strike Greeks data access and cost. The EOD methodology used in Paper 2 does not extend here without a new data vendor.

---

## Extension Track C — Cross-Asset Dealer Hedging Networks (GNN)

**Core question:** Does modeling options dealer hedging as a graph — with correlated assets as nodes and hedging flows as edges — improve regime detection over single-asset GEX?

**Rationale.** A dealer short JPM calls typically hedges across the financials complex (XLF, BAC, SPY), not only in JPM itself. Single-asset GEX misses this cross-asset hedging structure. Graph neural networks provide a natural formalism for this problem.

### Methodological options

| Approach | Reference | Positioning |
|----------|-----------|-------------|
| Trading Graph Neural Network (TGNN) | arXiv:2504.07923 | Explicitly models dealer inventory, capacity, bargaining |
| Temporal Graph Attention (Temporal GAT) | arXiv:2410.16858 | Directed spillovers, regime-transition dynamics |
| LLM-informed GNN hybrid | arXiv:2306.03763 | LLM extracts edges or enriches node features; GNN learns structure |
| Causal Constraint Networks | Extension of WHO→WHOM→WHAT | Market participants as nodes; forced transactions as edges |

### Candidate initial graph (financials)

Nodes: JPM, BAC, C, GS, MS, XLF, SPY (7). Node features: daily GEX, OI concentration, put/call ratio, volume-anomaly score, delta exposure. Edges: initialized by rolling 30-day gamma correlation; refined via attention.

### Novel spillover measure

```
GEX_Spillover(i→j) = Corr(GEX_i_t, Volatility_j_{t+1})
```

Tests whether one asset's GEX predicts another's next-period volatility — a GEX-based analog to the Diebold–Yilmaz spillover index.

**Critical blocker.** Multi-asset options data procurement. Training history of 2+ years across 7+ tickers is substantially more expensive than the single-asset SPY dataset used in Papers 1–2.

---

## Cross-Track Observations

**Relationship to published work.**

- Track A tests whether Paper 2's obfuscation methodology *generalizes* across assets.
- Track B tests whether finer-grained input (intraday, per-strike) *refines* detection at the single-asset level.
- Track C extends the *scope* from single-asset regimes to cross-asset hedging structure.

**Shared blockers.** Tracks B and C both depend on data access (intraday Greeks, multi-asset options chains) that was not available during the published work. Track A is the most data-accessible and may be the natural first extension.

**Out of scope for this repository.** Live trading implementation, strategy backtesting, and production pipelines belong in the [AutoTrader-AgentEdge](https://github.com/iAmGiG/AutoTrader-AgentEdge) repository, where trading-side issues were migrated (see AutoTrader #534, #573).

---

## Provenance

This document consolidates material from:

- `docs/papers/paper3/README.md` (cross-asset + intraday research planning, 484 lines)
- `docs/papers/paper4/README.md` (GNN / cross-asset hedging networks, 428 lines)

Both source files are preserved in git history. Detailed methodology notes, timelines, data-acquisition checklists, and risk assessments from those files remain available via `git log` on the predecessor paths if needed.

---

**Last consolidated:** April 2026
