# GNN Literature Review for Papers 4-5

**Created:** 2026-01-13
**Purpose:** Map Graph Neural Network literature to dissertation research roadmap
**Relevant Issues:** #116 (Intraday Regime Shifts), #117 (Cross-Asset Dealer Networks)

---

## Executive Summary

GNN research offers strong methodological foundations for Issues #116-117. The **Trading Graph Neural Network (TGNN)** paper is particularly relevant as it explicitly models dealer networks - a direct match for #117's cross-asset hedging research.

| Your Research | Best GNN Match | Relevance |
|---------------|----------------|-----------|
| #117: Cross-Asset Networks | TGNN (2504.07923) | **Direct** - models dealer/trader networks |
| #117: Volatility Spillovers | Temporal GAT (2410.16858) | **High** - directed spillover graphs |
| #116: Intraday Regime Shifts | Regime-Dependent GNN | **Medium** - Hurst-based regime detection |
| #116: Temporal Patterns | LSTM-GNN Hybrid (2502.15813) | **Medium** - temporal + relational |

---

## Tier 1: Directly Applicable Papers

### 1. Trading Graph Neural Network (TGNN)

**arXiv:** [2504.07923](https://arxiv.org/abs/2504.07923) (April 2025)

**Why It Matters for #117:**

- Explicitly models **dealer networks** with trader relationships
- Combines econometric SMM with GNN (interpretable + learnable)
- Models: asset features, dealer features, relationship features
- Outperforms network centrality baselines

**Key Innovation:**

- Economically-motivated message passing (not black box)
- Explicitly models dealer costs, customer values, bargaining powers
- Works with heterogeneous networks (different trader types)

**Application to Your Work:**

```text
Your Framework:
- Nodes: JPM, BAC, C, GS, MS, XLF, SPY
- Edges: Gamma exposure correlations (or actual hedge flows)
- Node features: GEX, OI concentration, dealer positioning
- Edge features: Correlation strength, lag structure

TGNN Addition:
- Dealer node features: Inventory, hedging capacity
- Bargaining dynamics: Who absorbs gamma risk?
- Message passing: How does JPM gamma propagate to XLF?
```text

**Citation for Paper 5:**
> "We adapt the Trading Graph Neural Network framework (Author et al., 2025) to model cross-asset dealer hedging relationships..."

---

### 2. Dynamic GNN for Volatility Prediction (Temporal GAT)

**arXiv:** [2410.16858](https://arxiv.org/abs/2410.16858) (October 2024)

**Why It Matters for #117:**

- Models volatility spillovers as **directed graphs**
- Temporal GAT = GCN + GAT + temporal encoding
- Beats GARCH on 8 global indices over 15 years
- Uses Diebold-Yilmaz spillover index for edge construction

**Key Results:**

- Superior short-to-mid term forecasting
- Captures non-linear interdependencies GARCH misses
- Graph structure adapts to changing market conditions

**Application to Your Work:**

```text
Your Framework:
- Construct directed graph: GEX spillover index between assets
- Temporal evolution: How does network topology change in crisis?
- Prediction target: Volatility spillovers from options → underlying

Temporal GAT Addition:
- Attention weights reveal which assets drive spillovers
- Temporal encoding captures regime transitions
- Directed edges model asymmetric hedging flows
```text

**Research Question:**
> "Does GEX exposure in JPM predict volatility spillover to XLF via the Temporal GAT framework?"

---

## Tier 2: Useful Architecture Patterns

### 3. Regime-Dependent GNN (H-ETE-GNN)

**Source:** [MDPI Mathematics](https://www.mdpi.com/2227-7390/14/2/289) (2025)

**Why It Matters for #116:**

- Uses **Hurst exponent for regime detection**
- Effective Transfer Entropy for directional edges
- Adapts GNN behavior based on market regime

**Direct Mapping to Your Work:**

```text
Your Regime Framework (Paper 2):
- Positive GEX regime: Dealer long gamma (buy dips, sell rips)
- Negative GEX regime: Dealer short gamma (amplify moves)
- Transition detection: When do regimes flip?

H-ETE-GNN Pattern:
- Use Hurst exponent to detect regime persistence
- High H (>0.5): Trending regime → one GNN behavior
- Low H (<0.5): Mean-reverting → different GNN behavior
- Switch GNN architecture based on detected regime
```text

**For Issue #116 (Intraday):**

- Calculate Hurst exponent on intraday GEX series
- Detect regime transitions at 9:45, 12:00, 3:00, 4:00
- GNN predicts whether transition leads to large price move

---

### 4. Hybrid LSTM-GNN Model

**arXiv:** [2502.15813](https://arxiv.org/abs/2502.15813) (February 2025)

**Why It Matters:**

- Clean architecture: LSTM (temporal) + GNN (relational)
- 10.6% MSE improvement over LSTM alone
- Uses Pearson correlation for graph construction

**Application Pattern:**

```text
For Intraday Regime Detection (#116):
- LSTM: Process 4-snapshot intraday GEX sequence
- GNN: Model cross-strike relationships (gamma clustering)
- Hybrid: Temporal regime evolution + strike-level structure

For Cross-Asset (#117):
- LSTM: Process daily GEX time series per asset
- GNN: Model hedging relationships between assets
- Hybrid: Temporal dynamics + network topology
```text

---

### 5. ChatGPT-Informed GNN

**arXiv:** [2306.03763](https://arxiv.org/pdf/2306.03763) (June 2023)

**Why It Matters:**

- **LLM extracts graph structure** from text → GNN predicts
- Precedent for LLM + GNN hybrid architecture
- DOW 30 evaluation with superior returns + lower volatility

**Novel Application:**

```text
Your LLM Already Detects:
- "Large put concentration at 4200 strike"
- "Dealer gamma exposure negative near resistance"
- "Volume anomaly with institutional signature"

LLM-Informed GNN:
- LLM extracts relationships from GEX patterns
- "4200 put concentration → hedging pressure on 4150-4250"
- GNN learns from LLM-extracted structure
- Combines structural reasoning + learned representations
```text

**Research Direction:**
> "Can LLM pattern detection inform GNN graph construction for improved regime prediction?"

---

## Tier 3: Background Literature

### 6. GNN Methods in Financial Applications (Review)

**arXiv:** [2111.15367](https://arxiv.org/abs/2111.15367)

**Use:** Related work section, comprehensive methodology survey

### 7. GNN-MS for Options Pricing

**Source:** [Journal of Futures Markets](https://onlinelibrary.wiley.com/doi/10.1002/fut.22506) (2024)

**Key Finding:** 8.81% RMSE improvement using momentum spillover graphs
**Relevance:** Precedent for GNN in options domain

### 8. Cross-Market ASTGCN

**Source:** [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0927539825000611) (2025)

**Key Finding:** Attention-based spatial-temporal GCN for volatility forecasting
**Relevance:** Architecture pattern for multi-market analysis

---

## Mapping to Your Research Questions

### Issue #117: Cross-Asset Dealer Hedging Networks

| Your Question | GNN Approach | Paper Reference |
|---------------|--------------|-----------------|
| How often do dealers hedge single-stock with ETFs? | Message passing reveals hedge flow paths | TGNN |
| Correlation structure between stocks and sectors? | Learned edge weights in GNN | Temporal GAT |
| How much does naive GEX miss? | Compare single-node vs graph prediction | LSTM-GNN |
| Do cross-asset patterns predict spillovers? | Temporal graph attention | Temporal GAT |

**Proposed Architecture for #117:**

```text
1. Graph Construction:
   - Nodes: Individual stocks + sector ETFs + index
   - Edges: Initialize with gamma correlation, learn with attention
   - Node features: GEX, OI, volume, delta exposure

2. Message Passing (TGNN-inspired):
   - Dealer-aware aggregation: "Given dealer inventory at JPM..."
   - Hedge flow propagation: "...predict gamma absorption at XLF"
   - Economically-interpretable weights

3. Temporal Evolution (Temporal GAT):
   - Track graph structure changes during stress
   - Attention reveals which links strengthen in crisis
   - Predict volatility spillover direction

4. Output:
   - Cross-asset hedging probability
   - Spillover magnitude prediction
   - Network centrality for systemic risk
```text

---

### Issue #116: Intraday GEX Regime Shifts

| Your Question | GNN Approach | Paper Reference |
|---------------|--------------|-----------------|
| When do gamma regimes flip intraday? | Hurst-based regime detection | H-ETE-GNN |
| Do flips predict larger moves? | Temporal encoding of transitions | LSTM-GNN |
| Can LLM detect early warnings? | LLM-informed graph construction | ChatGPT-GNN |

**Proposed Architecture for #116:**

```text
1. Intraday Graph:
   - Nodes: Strike prices with significant OI
   - Edges: Gamma concentration relationships
   - Temporal: 4 snapshots as graph sequence

2. Regime Detection:
   - Calculate Hurst exponent on GEX series
   - Detect transition points (H crosses 0.5)
   - Flag potential regime flips

3. Prediction:
   - Input: Partial intraday data (9:45, 12:00)
   - GNN: Process strike-level structure
   - Output: Probability of regime flip by 4:00 PM

4. Validation:
   - Compare: GNN prediction vs LLM detection vs baseline
   - Measure: Price impact in 30-min window after predicted flip
```text

---

## Implementation Considerations

### Data Requirements

| Component | Issue #116 | Issue #117 |
|-----------|------------|------------|
| Temporal resolution | 4 intraday snapshots | Daily EOD |
| Asset scope | SPY/SPX strikes | 5-10 stocks + ETFs |
| Graph size | ~50-100 nodes (strikes) | ~10-20 nodes (assets) |
| Edge construction | Gamma correlation | Hedging correlation |

### Computational Notes

- GNN training: PyTorch Geometric or DGL
- Temporal extension: Temporal Graph Networks (TGN)
- Integration with existing LLM: Ensemble or cascade

### Precedent for Publication

| Venue | GNN Finance Papers | Your Fit |
|-------|-------------------|----------|
| JFE/RFS | Limited (emerging) | Novel contribution |
| JFM/JOIM | Growing | Practitioner angle |
| ML venues (NeurIPS, ICML) | Finance workshops | Methodology focus |

---

## Recommended Reading Order

1. **TGNN (2504.07923)** - Most directly relevant, read first
2. **Temporal GAT (2410.16858)** - Volatility spillover methodology
3. **H-ETE-GNN** - Regime detection pattern
4. **LSTM-GNN (2502.15813)** - Clean hybrid architecture
5. **ChatGPT-GNN (2306.03763)** - LLM integration precedent
6. **Review paper (2111.15367)** - Background for related work

---

## Next Steps

### Immediate (Literature Review)

- [ ] Download and read TGNN full paper
- [ ] Study Temporal GAT methodology section
- [ ] Review regime-dependent GNN Hurst approach

### Short-term (Scoping)

- [ ] Assess: Can existing data support GNN graph construction?
- [ ] Prototype: Simple correlation-based graph for financials
- [ ] Discuss: GNN approach with advisor

### Medium-term (If Pursuing)

- [ ] Design: GNN architecture for #117 or #116
- [ ] Implement: Baseline GNN on existing GEX data
- [ ] Compare: GNN vs LLM-only vs hybrid

---

## Citation Block (for Papers)

```bibtex
@article{tgnn2025,
  title={Trading Graph Neural Network},
  author={...},
  journal={arXiv preprint arXiv:2504.07923},
  year={2025}
}

@article{temporalgat2024,
  title={Dynamic graph neural networks for enhanced volatility prediction},
  author={...},
  journal={arXiv preprint arXiv:2410.16858},
  year={2024}
}

@article{lstmgnn2025,
  title={Stock Price Prediction Using a Hybrid LSTM-GNN Model},
  author={...},
  journal={arXiv preprint arXiv:2502.15813},
  year={2025}
}
```text

---

**Status:** Initial literature mapping complete
**Next Review:** When starting Issue #116 or #117 research design
**Related:** [gex_formula_comparison.md](gex_formula_comparison.md), [practitioner_methods.md](practitioner_methods.md)
