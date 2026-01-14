# Papers 3-4 Research Roadmap: Advisor Discussion

**Date**: January 2026
**Status**: Planning (pending Paper 2 completion)
**Purpose**: Outline research directions for advisor input

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

**Expected Contributions**:

1. First systematic study of intraday dealer gamma dynamics
2. Per-strike analysis bridges practitioner intuition with academic rigor
3. Earlier detection of regime shifts (morning signal vs EOD)

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

## Related Documentation

- [Paper 3 Detailed Planning](../paper3/README.md) - Full Track A/B breakdown
- [Paper 4 Detailed Planning](../paper4/README.md) - GNN methodology options
- [GNN Literature Review](../../reference/auxiliary_research/gnn_literature_review.md) - Paper summaries
- [Research Roadmap](../research_roadmap.md) - Overall dissertation trajectory

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
