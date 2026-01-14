# Paper 4: Cross-Asset Dealer Hedging Networks

**Status**: 💡 Concept (Year 3-4 of PhD)
**Working Title**: "Graph Neural Networks for Cross-Asset Dealer Hedging Dynamics"
**Dependencies**: Papers 2-3 complete, multi-asset data access confirmed

---

## Paper Numbering Clarification

> **Note**: GitHub issue labels vary. This document consolidates:
>
> - #117: Cross-Asset Dealer Hedging Networks (labeled `[Paper #4]`)
> - #136: Causal Constraint Networks (labeled `[Paper #4]`)
> - GNN methodology research (from literature review)
>
> These may become one paper or split into separate contributions.

---

## Research Vision

### The Gap

**Naive Assumption**: JPM options → hedge with JPM stock
**Reality**: JPM options → hedge with XLF + BAC + SPY + sector basket
**Problem**: Single-asset GEX analysis misses cross-asset hedging complexity

### The Opportunity

Model dealer hedging as a **network problem** where:

- **Nodes** = Individual assets (stocks, ETFs, indices)
- **Edges** = Hedging relationships (correlation, gamma flow)
- **Dynamics** = How network structure changes during stress

---

## Consolidated GitHub Issues

### Core Research Issues

| Issue | Title | Status | Focus |
|-------|-------|--------|-------|
| #117 | Cross-Asset Dealer Hedging Networks | CONCEPT | Network structure |
| #136 | Causal Constraint Networks | CONCEPT | Graph-theoretic formalization |

### Supporting Research Issues

| Issue | Title | Relevance |
|-------|-------|-----------|
| #181 | Volatility→Equity Spillover (UVXY Lead-Lag) | Edge construction |
| #182 | Regime-Conditional Correlation Analysis | Dynamic edges |
| #184 | Regime-Based Portfolio Optimization | Application |

### GNN Literature Reference

| Document | Content |
|----------|---------|
| `gnn_literature_review.md` | TGNN, Temporal GAT, methodology options |
| `gh_issues/tgnn_dealer_networks.md` | Implementation template |
| `gh_issues/temporal_gat_spillovers.md` | Spillover prediction architecture |
| `gh_issues/llm_gnn_hybrid.md` | LLM+GNN novel contribution |

---

## Research Questions

### Primary

1. **How often do dealers hedge single-stock gamma with sector ETFs?**
2. **Does network structure predict volatility spillovers?**
3. **Can GNNs outperform scalar GEX for regime detection?**

### Secondary

1. What's the correlation structure between stocks and sectors?
2. How much dealer exposure does naive GEX miss?
3. Do cross-asset patterns predict regime transitions?
4. How does network topology change during market stress?

---

## Methodological Approaches

### Approach A: Trading Graph Neural Network (TGNN)

**Source**: [arXiv:2504.07923](https://arxiv.org/abs/2504.07923)

**Why TGNN**:

- Explicitly models dealer networks (not generic GNN)
- Economically interpretable message passing
- Combines SMM (econometrics) + GNN (deep learning)

**Proposed Architecture**:

```text
Nodes (Phase 1 - Financials):
├── Individual: JPM, BAC, C, GS, MS (5 nodes)
├── Sector ETF: XLF (1 node)
└── Index: SPY (1 node)
    Total: 7 nodes

Node Features:
├── GEX (daily)
├── OI concentration
├── Put/Call ratio
├── Volume anomaly score
└── Delta exposure

Edges:
├── Initialize: Gamma correlation (rolling 30-day)
├── Learn: Attention weights during training
└── Directed: Asymmetric hedging relationships

TGNN-Specific:
├── Dealer costs (inventory proxy)
├── Hedging capacity (liquidity)
└── Bargaining dynamics (who absorbs gamma)
```text

### Approach B: Temporal Graph Attention (Temporal GAT)

**Source**: [arXiv:2410.16858](https://arxiv.org/abs/2410.16858)

**Why Temporal GAT**:

- Models directed spillovers (JPM → XLF ≠ XLF → JPM)
- Captures temporal dynamics (regime transitions)
- Attention weights reveal critical edges
- Beats GARCH on volatility prediction

**Proposed Architecture**:

```text
Edge Construction:
├── Standard: Diebold-Yilmaz spillover index
└── Novel: GEX-based spillover measure

GEX Spillover Index (novel):
  GEX_Spillover(i→j) = Corr(GEX_i_t, Volatility_j_{t+1})
  "Does JPM gamma exposure predict XLF volatility tomorrow?"

Temporal Component:
├── Rolling windows (30-day)
├── Graph sequence: G_t, G_{t+1}, ..., G_{t+T}
└── Capture topology changes during stress
```text

### Approach C: LLM-Informed GNN (Novel)

**Source**: [arXiv:2306.03763](https://arxiv.org/pdf/2306.03763) + Papers 1-2

**Why LLM+GNN**:

- Combines proven LLM pattern detection (Papers 1-2) with GNN
- LLM extracts relationships → GNN learns from structure
- Novel contribution: First for options/GEX domain

**Architecture Options**:

```text
Option A: LLM Extracts Edges
  1. LLM detects: "JPM put buying + XLF call selling"
  2. Edge construction from LLM patterns
  3. GNN trains on LLM-informed graph

Option B: LLM as Node Feature
  1. LLM classifies regime per asset
  2. Node features include LLM regime + confidence
  3. GNN learns which LLM features matter

Option C: Ensemble
  1. LLM: P(spillover | GEX patterns)
  2. GNN: P(spillover | graph structure)
  3. Meta-learner combines predictions
```text

### Approach D: Causal Constraint Networks (#136)

**WHO→WHOM→WHAT as Graph**:

```python
# Nodes: Market participants
nodes = {
    "Dealer": {"constraint": "delta_neutral", "gamma": -0.05},
    "Retail": {"constraint": "maximize_premium", "position": "long_calls"},
    "Institutional": {"constraint": "tail_risk_hedge"},
    "Arbitrageur": {"constraint": "none"}
}

# Edges: Forced transactions
edges = {
    ("Retail", "Dealer"): {"type": "option_purchase", "forces": "hedge"},
    ("Dealer", "Market"): {"type": "delta_hedge", "cascades": True},
    ("Market", "Institutional"): {"type": "stop_loss_trigger"}
}
```text

**Graph Properties to Analyze**:

- Degree centrality: Who influences most?
- Betweenness centrality: Who mediates cascades?
- Clustering coefficient: Local constraint density
- Path length: Cascade propagation speed

---

## Implementation Roadmap

### Phase 1: Data & Graph Construction (4-6 weeks)

- [ ] Acquire multi-asset options data (JPM, BAC, C, GS, MS, XLF, SPY)
- [ ] Calculate daily GEX per asset
- [ ] Compute correlation matrix (30-day rolling)
- [ ] Build initial graph structure

**Deliverable**: PyTorch Geometric data loader with 7-node graph

### Phase 2: Baseline GNN (3-4 weeks)

- [ ] Implement simple GCN for regime classification
- [ ] Compare: GNN vs single-asset GEX baseline
- [ ] Validate on historical regime transitions
- [ ] Document baseline performance

**Deliverable**: Working GNN with performance metrics

### Phase 3: Advanced Architecture (4-6 weeks)

**Choose ONE based on Phase 2 results**:

- [ ] TGNN: If dealer-specific modeling needed
- [ ] Temporal GAT: If temporal dynamics critical
- [ ] LLM+GNN: If LLM patterns add clear value

**Deliverable**: Selected architecture with justification

### Phase 4: Validation & Analysis (3-4 weeks)

- [ ] Compare GNN vs LLM-only vs hybrid
- [ ] Interpretability analysis (what do edge weights mean?)
- [ ] Stress period analysis (COVID, VIX spikes)
- [ ] Ablation studies (which features matter?)

**Deliverable**: Comprehensive results with interpretation

### Phase 5: Writing (4-6 weeks)

- [ ] Literature review (GNN + finance)
- [ ] Methodology section with architecture diagrams
- [ ] Results with statistical tests
- [ ] Discussion of limitations and future work

**Deliverable**: Paper draft

---

## Data Requirements

### Multi-Asset Options Data

| Asset Type | Symbols | Data Needed | Status |
|------------|---------|-------------|--------|
| Single-stock | JPM, BAC, C, GS, MS | OI, Greeks, volume | **TBD** |
| Sector ETF | XLF | OI, Greeks, volume | **TBD** |
| Index | SPY | OI, Greeks, volume | Available |

**Critical Requirement**: 2+ years history for training

### Computed Features

| Feature | Source | Computation |
|---------|--------|-------------|
| Per-asset GEX | Options data | Existing calculator |
| Correlation matrix | GEX series | Rolling 30-day |
| Spillover index | GEX + volatility | Diebold-Yilmaz or novel |
| Node features | Multiple | Feature engineering |

---

## Expected Contributions

### Academic

1. **First graph-theoretic formalization** of options microstructure
2. **Novel GEX spillover index** for edge construction
3. **Quantified cross-asset hedging** patterns
4. **GNN vs LLM comparison** for regime detection

### Methodological

1. **TGNN adaptation** for dealer networks
2. **LLM-informed graph construction** (novel)
3. **Temporal graph** for regime dynamics
4. **Causal constraint propagation** framework

### Practical

1. **Network centrality** identifies systemically important assets
2. **Spillover prediction** for risk management
3. **Cross-asset regime** detection for portfolio hedging

---

## Publication Strategy

### Target Venues

| Venue | Fit | Notes |
|-------|-----|-------|
| JFE (Journal of Financial Economics) | High | Novel contribution to microstructure |
| RFS (Review of Financial Studies) | High | Empirical + theoretical |
| JFM (Journal of Financial Markets) | High | Market microstructure focus |
| NeurIPS Finance Workshop | Medium | ML methodology emphasis |

### Positioning

**Novel Angle 1**: First GNN application to options dealer hedging
**Novel Angle 2**: LLM-informed graph construction for finance
**Novel Angle 3**: GEX-based spillover index (vs return-based)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Multi-asset data expensive | High | **Blocking** | Start with correlation as proxy, Phase 1 only |
| GNN doesn't beat LLM | Medium | Reduces contribution | Document as comparison result |
| Graph too small (7 nodes) | Medium | Weak learning | Expand to more sectors |
| Interpretability lost | Low | Medium | Use TGNN's economic structure |
| Compute requirements | Low | Low | Small graph, GPU optional |

---

## Relationship to Other Work

### Papers 1-2 Foundation

- WHO→WHOM→WHAT framework → Graph edges
- Regime classification → Node labels
- Obfuscation testing → Can extend to graph

### Paper 3 Prerequisites

- Per-strike analysis informs node features
- Intraday dynamics inform temporal graphs
- Continuous regime → edge weights

### Future Extensions

- More sectors (Tech: AAPL, MSFT, NVDA + XLK)
- Higher frequency (intraday graphs)
- Real-time cascade prediction

---

## GNN Literature Reference

### Must-Read Papers

| Paper | arXiv | Key Contribution |
|-------|-------|------------------|
| **TGNN** | [2504.07923](https://arxiv.org/abs/2504.07923) | Dealer network modeling |
| **Temporal GAT** | [2410.16858](https://arxiv.org/abs/2410.16858) | Volatility spillovers |
| **ChatGPT-GNN** | [2306.03763](https://arxiv.org/pdf/2306.03763) | LLM-informed edges |
| **LSTM-GNN** | [2502.15813](https://arxiv.org/abs/2502.15813) | Hybrid architecture |

### Full Review

See: `docs/reference/auxiliary_research/gnn_literature_review.md`

### Issue Templates

Ready-to-use GitHub issues for new repo:

- `gh_issues/gnn_methodology_research.md`
- `gh_issues/tgnn_dealer_networks.md`
- `gh_issues/temporal_gat_spillovers.md`
- `gh_issues/llm_gnn_hybrid.md`

---

## Timeline

| Phase | Duration | Start | Dependencies |
|-------|----------|-------|--------------|
| Data investigation | 2 weeks | Q3 2026 | Paper 3 progress |
| Graph construction | 4-6 weeks | +2 weeks | Data confirmed |
| Baseline GNN | 3-4 weeks | +6 weeks | Graph complete |
| Advanced architecture | 4-6 weeks | +10 weeks | Baseline complete |
| Validation | 3-4 weeks | +16 weeks | Architecture complete |
| Writing | 4-6 weeks | +20 weeks | Validation complete |
| **Total** | **20-28 weeks** | | |

**Realistic Start**: Q3-Q4 2026 (Year 3 of PhD)
**Target Submission**: Q1-Q2 2027

---

## Open Questions for Advisor

1. **Scope**: TGNN vs Temporal GAT vs LLM+GNN - which direction?
2. **Data**: Budget for multi-asset options data?
3. **Novelty**: Is GNN application alone sufficient, or need theoretical contribution?
4. **Timeline**: Year 3-4 realistic given earlier paper dependencies?
5. **Venue**: JFE/RFS (top-tier) vs JFM (finance-specific)?

---

## Quick Start Checklist

When ready to begin this research:

- [ ] Review GNN literature (`gnn_literature_review.md`)
- [ ] Read TGNN paper in full ([arXiv:2504.07923](https://arxiv.org/abs/2504.07923))
- [ ] Investigate multi-asset data costs
- [ ] Prototype correlation-based graph with existing SPY data
- [ ] Discuss scope with advisor
- [ ] Select primary methodology (A, B, C, or D)

---

**Last Updated**: 2026-01-14
**Next Review**: After Paper 3 validation milestone
