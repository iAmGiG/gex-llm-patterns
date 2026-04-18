# Papers 3-4 Research Roadmap: Advisor Discussion

**Date**: January 2026 (original) · April 2026 (augmented with peer-review reflection)
**Status**: Planning. Paper 2 now accepted at AIAI 2026 (camera-ready May 2026); JRFM/Digital Finance both rejected.
**Purpose**: Outline research directions for advisor input, now informed by actual peer-review feedback and a post-hoc audit of results/reports data

---

## Current Status

| Paper | Status | Key Result |
|-------|--------|------------|
| **Paper 1** | ✅ Submitted (Oct 2025) | 71.5% detection, 91.2% materialization |
| **Paper 2** | 🔄 Writing in progress | 81.2% vs 12.1% (2024 vs 2020), 0DTE hypothesis confirmed |
| **Paper 3** | 📋 Planning | Two candidate tracks (see below) |
| **Paper 4** | 💡 Concept | Network/GNN approaches |

---

## Paper 3: Scope Decision Required

Two research tracks emerged from planning. **Advisor input needed on prioritization.**

### Option A: Cross-Asset Generalization

**Research Question**: Does obfuscation testing generalize beyond SPY to individual stocks?

**Scope**:

- 10 liquid stocks (AAPL, MSFT, NVDA, TSLA, AMD, JPM, BAC, GS, AMZN, META)
- Reuse Paper 2 methodology (30-day regime windows)
- Compare index vs single-name dealer dynamics

**Expected Contributions**:

1. Generalization proof (methodology works beyond single asset)
2. Cross-asset comparison (index vs single-name patterns)
3. Pattern persistence analysis (universal vs idiosyncratic)

**Timeline**: 8-12 weeks
**Data**: Partially available (Alpha Vantage)

### Option B: Intraday/Per-Strike Analysis

**Research Question**: Can LLMs detect intraday regime shifts from per-strike gamma distributions?

**Scope**:

- 4 daily snapshots (9:45 AM, 12:00 PM, 3:00 PM, 4:00 PM)
- Per-strike gamma distribution (beyond scalar GEX)
- Gamma "wall" validation (practitioner claim testing)
- Continuous vs binary regime classification

**Proposed Experiments** (from #116, #221-223):

| Experiment | Setup | Metric |
|------------|-------|--------|
| Intraday flip detection | Predict 4PM regime from 9:45+12:00 data | Detection accuracy, timing |
| Per-strike vs aggregate | A/B test: scalar GEX vs distribution | Detection rate improvement |
| Continuous vs binary | Regime intensity vs binary label | Calibration improvement |
| Supplementary signals | Add SABR ρ/ν, GAMMA-SVIX divergence | Incremental value |

**Supplementary Signal Research** (from #226, #228):

- **SABR Parameters**: ρ (vol-spot correlation) as directional bias, ν (vol-of-vol) as jump risk
- **GAMMA-SVIX Divergence**: Normal correlation is -0.89; divergence signals regime transition

**Expected Contributions**:

1. First systematic study of intraday dealer gamma dynamics
2. Per-strike analysis bridges practitioner intuition with academic rigor
3. Earlier detection of regime shifts (morning signal vs EOD)
4. Supplementary signals validation (SABR, SVIX)

**Timeline**: 13-18 weeks
**Data**: **Critical blocker** - intraday options Greeks vendor TBD

### Recommendation

| Factor | Option A | Option B |
|--------|----------|----------|
| Data availability | ✅ Partial | ⚠️ Unknown |
| Effort | Lower | Higher |
| Novelty | Moderate | Higher |
| Risk | Lower | Higher |
| Follows Paper 2 logic | Yes | Yes |

**Suggested path**: Start with Option A (lower risk, data available), pursue Option B as Paper 4 if data feasible.

---

## Paper 4: Network/GNN Approaches

**Research Vision**: Model dealer hedging as a network problem where single-asset GEX misses cross-asset complexity.

**Core Insight**:

- Naive: JPM options → hedge with JPM stock
- Reality: JPM options → hedge with XLF + BAC + SPY + sector basket

### Research Questions

1. How often do dealers hedge single-stock gamma with sector ETFs?
2. Does network structure predict volatility spillovers?
3. Can GNNs outperform scalar GEX for regime detection?

### Methodological Options

| Approach | Description | Novelty |
|----------|-------------|---------|
| **TGNN** | Trading Graph Neural Network (dealer-specific modeling) | Apply existing |
| **Temporal GAT** | Volatility spillover with attention weights | Apply existing |
| **LLM+GNN Hybrid** | LLM extracts graph structure, GNN learns | **Novel** |
| **Causal Constraints** | WHO→WHOM→WHAT as directed graph | **Novel** |

**Strongest contribution angle**: LLM+GNN hybrid (combines Papers 1-2 work with GNN, first for options/GEX domain)

### Literature Foundation

Recent GNN papers identified for methodology:

- TGNN ([arXiv:2504.07923](https://arxiv.org/abs/2504.07923)) - Dealer network modeling
- Temporal GAT ([arXiv:2410.16858](https://arxiv.org/abs/2410.16858)) - Volatility spillovers
- ChatGPT-Informed GNN ([arXiv:2306.03763](https://arxiv.org/pdf/2306.03763)) - LLM+GNN precedent

**Timeline**: 20-28 weeks (Year 3-4 of PhD)

---

## Decision Points for Advisor

### Immediate (Paper 3 Scope)

1. **Track selection**: Cross-asset (A) or Intraday (B) for Paper 3?
2. **Combined vs split**: One paper covering both, or separate papers?
3. **Data budget**: Can we afford intraday options data if pursuing Track B?

### Medium-term (Paper 4 Direction)

1. **GNN vs LLM-only**: Is methodological diversity (adding GNN) valuable, or should we stay LLM-focused?
2. **Novel vs applied**: Pursue LLM+GNN hybrid (novel) or apply existing TGNN/Temporal GAT?
3. **Venue strategy**: JFE/RFS (top-tier) or JFM (microstructure-specific)?

### Timeline Considerations

| Milestone | Target |
|-----------|--------|
| Paper 2 submission | Q1 2026 |
| Paper 3 start | Q2 2026 |
| Paper 3 submission | Q3 2026 |
| Paper 4 start | Q4 2026 |
| Paper 4 submission | Q1-Q2 2027 |

---

## Supplementary Research Ideas

These could enhance Papers 3-4 or become separate contributions:

| Idea | Paper | Priority |
|------|-------|----------|
| Continuous regime classification | 3B | High |
| SABR parameters (ρ, ν) as regime indicators | 3B | Medium |
| GAMMA-SVIX divergence signals | 3B | Medium |
| GEX-based spillover index (novel metric) | 4 | High |
| Causal constraint propagation | 4 | Medium |

---

## Gaps Flagged by Peer Review (AIAI 2026) and Results Audit

The AIAI 2026 reviews (2 Accept-with-revisions + 1 Borderline) and an April 2026 audit of `reports/` and `docs/papers/paper2/results/` surfaced five concrete gaps. Listed in order of leverage (impact per unit of effort).

### 1. Cross-Asset Validation — HIGHEST LEVERAGE, DATA ALREADY EXISTS

**Flag**: Reviewer #3 and Reviewer #4 both cited single-asset (SPY) validation as a generalizability concern. The April 2026 audit confirms: **45M+ options contracts already collected across 19 leveraged/inverse ETFs** (TQQQ, SQQQ, SOXL, SOXS, UVXY, SPXL, SPXS, UPRO, SPXU, TNA, TZA, FAS, FAZ, LABU, LABD, TECL, TECS, NUGT, DUST — 18 GB SQLite), yet **zero validation runs** have been performed on non-SPY assets.

**Why this is highest leverage:**

- Data acquisition is done. The expensive part (14 days of API calls at 600/min) is behind us.
- Directly neutralizes the strongest reviewer critique.
- Validates the methodology's central claim — that obfuscation-based structural reasoning generalizes.
- Allows an obvious Paper 3 narrative even if detection rates differ across assets (differences themselves are a finding).

**Concrete first experiment**: Reuse the Paper 2 five-phase protocol on QQQ (similar index, different dealer mix) and TQQQ (leveraged variant). If SPY's 2024-vs-2020 separation holds, publish as direct replication + extension. If it doesn't, the divergence itself is a finding worth documenting.

**Effort**: ~2 weeks (code is already written; only the data fetching changes).

**Recommend this as Paper 3 Option A, strongly prioritized over intraday (Option B) — the data bottleneck that blocked Option B in the original plan does not exist here.**

### 2. Threshold Sensitivity Analysis — QUICK WIN

**Flag**: Reviewer #4 flagged the 70% / $5B / ≤5-flip thresholds as "empirical design choices rather than first-principles derivations." The camera-ready rebuttal references "25 tested parameter combinations maintained >72pp discrimination" — but the audit found that **this claim is aspirational**: the sensitivity script (`docs/papers/paper2/figures/scripts/fig11_threshold_sensitivity_heatmap.py`) exists and sweeps persistence ∈ {60, 65, 70, 75, 80}% × magnitude ∈ {$3, $4, $5, $6, $7}B, but the actual 25-combination discrimination-gap grid was never published.

**Action**: Run the existing script to completion, publish the grid as a supplementary table or figure. If discrimination does hold across the 5×5 grid as claimed, this converts an aspirational footnote into citable evidence. If it *doesn't* hold uniformly, the sensitivity surface itself is a finding.

**Effort**: < 1 week. Script is complete; just needs execution + narrative.

**Where to publish**: Supplement to the AIAI camera-ready (allowed) OR as part of any Paper 2 journal follow-up.

### 3. Threshold-Withholding Experiment — SHARPEST TEST OF REVIEWER #4

**Flag**: The Issue #191 narrative-ablation (framework-with vs framework-without, both 100%) tested whether the WHO→WHOM→WHAT framing matters. It did not test Reviewer #4's actual critique, which was whether **giving the LLM the thresholds in the prompt** reduces the task to rule execution.

**Sharper experiment**: Remove the classification criteria (P ≥ 0.70, M ≥ $5B, S ≤ 5) entirely from the prompt. Ask the LLM only to identify whether a 30-day window is a "persistent dealer regime" without specifying what persistence means. Compare detection rates:

- **If detection rates stay comparable** → the LLM is inferring the structural criteria from the data itself (strong rebuttal to Reviewer #4)
- **If rates collapse** → the LLM was indeed executing given rules, and the true contribution is narrower than claimed

**Why this matters**: Either outcome is publishable. A strong detection result here would be the cleanest possible rebuttal to the rule-following critique. A weak result reshapes the contribution honestly (as "structural criterion execution under obfuscation" rather than "structural reasoning").

**Effort**: ~1 week. Same windows, same model, just one modified prompt. Cost ≈ $5 (Batch API, 2,221 evaluations).

**Positioning**: Could run as a pre-registered extension to Paper 2, or as the opening experiment of Paper 3.

### 4. Dual GEX Framework (Issue #138) — UNDERUTILIZED ASSET

**Flag**: The audit surfaced a methodologically interesting finding from Issue #138 that doesn't appear prominently in Paper 2's AIAI submission: a **dual GEX representation** separating structural positioning (GEX_OI, built from open interest) from economic activity (GEX_Volume). This framework explains the detection/profitability orthogonality cleanly — detection is driven by GEX_OI persistence; profitability is driven by GEX_Volume activity.

**Implication**: This dual framework *is* the answer to Reviewer #4's "what's the LLM adding beyond rules" critique, framed positively. A rule on GEX_OI alone gives you binary detection. A rule on GEX_Volume alone gives you profitability signal. The LLM that reasons over both can explain *why* detection and profitability diverge — which a threshold rule cannot.

**Paper 3 angle**: Make the dual-GEX distinction the paper's central methodological contribution, with cross-asset validation as the empirical backbone. Title something like *"Structural vs Economic Gamma Exposure: Dual-GEX Regime Detection Across Asset Classes."*

**Status**: Implementation exists (see [docs/papers/paper2/extensions/issue138_ext-impl.md](../paper2/extensions/issue138_ext-impl.md)), but the dual-GEX angle is currently mentioned only in the AIAI Discussion's sensitivity subsection. There's room to build a paper around it.

### 5. Transition-Timing Analysis (Issue #190, deferred)

**Flag**: Phase 5 results show a non-monotonic detection progression — 12.2% (2020) → 3.7% (2021) → 32.4% (2022) → 20.2% (2023) → 100% (2024). The AIAI discussion explains this as a tipping-point dynamic (regime persistence requires both sustained dealer pressure AND a consolidating volatility environment), but the exact transition timing is not characterized.

**Proposed analysis**: Fit a change-point model (binary segmentation, Bayesian online change detection, or a structural break test) to the monthly detection-rate series. Test whether the 2023→2024 jump is statistically a break or the endpoint of a smooth 2021→2024 progression. Compare the change-point dates against 0DTE volume-share milestones.

**Value**: Converts the current narrative ("gradual evolution") into a quantified finding with a specific date range for the structural break. Strengthens any follow-up paper's claim that methodology tracked a real market-structure shift, not a coincidence.

**Effort**: ~1 week. Data exists; analysis is statistical, not computational.

---

## Priority Recommendations (April 2026)

Merging the original Paper 3 / Paper 4 plan with the five gaps above:

| Rank | Item | Effort | Addresses |
| ---- | ---- | ------ | --------- |
| 1 | Cross-asset validation (QQQ + TQQQ first, then broader) | ~2 weeks | Reviewer #3, #4 generalizability; Paper 3 Track A |
| 2 | Threshold-sensitivity grid (run existing script) | < 1 week | Reviewer #4 threshold critique; substantiates aspirational claim |
| 3 | Threshold-withholding experiment | ~1 week | Reviewer #4 rule-following critique (sharpest test) |
| 4 | Dual-GEX angle as Paper 3 framing | Design decision | Elevates Issue #138 finding; cleanly answers "LLM vs rule" |
| 5 | Transition-timing change-point analysis | ~1 week | Strengthens 0DTE hypothesis causal claim |
| 6 | Intraday / per-strike (original Paper 3 Option B) | 13–18 weeks | Only viable if intraday data access resolves |
| 7 | GNN / cross-asset hedging networks (original Paper 4) | 20–28 weeks | Year 3–4, long-term vision |

**Combined Paper 3 proposal**: Lead with cross-asset validation (primary contribution), fold in threshold sensitivity grid (supplementary), close with the dual-GEX framing. This single paper would address the three highest-leverage gaps simultaneously and substantially strengthens the published Paper 2.

---

## Related Documentation

- [Research Extensions](../extensions/README.md) - Consolidated forward-looking directions (Tracks A, B, C)
- [GNN Literature Review](../../reference/auxiliary_research/gnn_literature_review.md) - Paper summaries
- [Research Roadmap](../research_roadmap.md) - Historical dissertation trajectory (Jan 2026 snapshot)

---

## GitHub Issues

### Paper 3 Related

- #116: Intraday GEX Regime Shift Detection
- #135: Per-Strike GEX Analysis
- #221-223: Gamma distribution, continuous classification, intraday validation
- #226, #228: SABR parameters, GAMMA-SVIX divergence

### Paper 4 Related

- #117: Cross-Asset Dealer Hedging Networks
- #136: Causal Constraint Networks

---

**Next Step**: Schedule advisor meeting to discuss Paper 3 scope selection after Paper 2 writing milestone.
