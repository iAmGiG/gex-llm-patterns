# [Implementation] TGNN for Cross-Asset Dealer Hedging

## Summary

**Type:** Implementation | **Timeline:** After methodology selection | **Status:** Blocked (pending methodology decision)

Implement Trading Graph Neural Network (TGNN) architecture for modeling cross-asset dealer hedging relationships.

## Why TGNN

From literature review, TGNN ([arXiv:2504.07923](https://arxiv.org/abs/2504.07923)) is the strongest candidate because:

1. **Explicitly models dealer networks** - Not generic graph learning
2. **Economically interpretable** - Message passing derived from bargaining theory
3. **Heterogeneous support** - Different node types (stocks, ETFs, index)
4. **Outperforms baselines** - Better than network centrality measures

## Proposed Architecture

### Graph Structure

```text
Nodes:
- Individual stocks: JPM, BAC, C, GS, MS (5 nodes)
- Sector ETF: XLF (1 node)
- Index: SPY (1 node)
- Total: 7 nodes (Phase 1: Financials only)

Edges:
- Initialize: Gamma exposure correlation (rolling 30-day)
- Learn: Attention weights during training
- Directed: Asymmetric hedging relationships

Node Features:
- GEX (daily)
- OI concentration (ATM vs wings)
- Put/Call ratio
- Volume anomaly score
- Delta exposure

Edge Features:
- Correlation strength
- Lag structure (Granger causality)
- Historical hedge ratio
```text

### TGNN-Specific Components

```text
Dealer Features (per node):
- Estimated inventory (from OI changes)
- Hedging capacity proxy (market cap, liquidity)
- Historical positioning patterns

Message Passing:
- Economically-motivated aggregation
- "Given dealer inventory at JPM, predict gamma absorption at XLF"
- Interpretable weights (not black box)

Output:
- Cross-asset hedging probability
- Spillover magnitude prediction
- Network centrality for systemic risk
```text

## Implementation Tasks

### Phase 1: Data Pipeline

- [ ] Extract daily GEX for 7 assets (JPM, BAC, C, GS, MS, XLF, SPY)
- [ ] Calculate rolling correlation matrix (30-day window)
- [ ] Compute node features (GEX, OI concentration, etc.)
- [ ] Build edge feature matrix (correlation, lag structure)

### Phase 2: Graph Construction

- [ ] Implement PyTorch Geometric data loader
- [ ] Create heterogeneous graph structure (stock vs ETF vs index)
- [ ] Validate graph connectivity and feature shapes

### Phase 3: TGNN Architecture

- [ ] Implement dealer-aware message passing layer
- [ ] Add economic interpretability constraints
- [ ] Build prediction head (spillover magnitude)

### Phase 4: Training

- [ ] Define loss function (spillover prediction vs actual)
- [ ] Implement training loop with early stopping
- [ ] Hyperparameter tuning (learning rate, hidden dims, layers)

### Phase 5: Evaluation

- [ ] Compare vs baseline (single-asset GEX only)
- [ ] Compare vs simple correlation model
- [ ] Ablation: Which features matter most?
- [ ] Interpretability analysis: What do edge weights mean?

## Data Requirements

| Data | Source | Frequency | History |
|------|--------|-----------|---------|
| Single-stock options OI | TBD | Daily | 2+ years |
| Sector ETF options OI | TBD | Daily | 2+ years |
| Index options OI | Existing | Daily | Available |
| Stock prices | Yahoo/existing | Daily | Available |

## Computational Requirements

- PyTorch Geometric or DGL
- GPU recommended for training (but small graph, CPU feasible)
- Estimated training time: Hours (not days) for 7-node graph

## Success Criteria

- [ ] Model trains without divergence
- [ ] Spillover prediction beats single-asset baseline by >10%
- [ ] Edge weights are interpretable (correlate with known hedging patterns)
- [ ] Results reproducible across random seeds

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Insufficient data for training | Start with longer history, simpler model |
| Overfitting on small graph | Strong regularization, cross-validation |
| Edge weights not interpretable | Add interpretability loss term |
| Correlation ≠ causation | Granger causality validation |

## Dependencies

- Blocked by: GNN Methodology Selection issue
- Requires: Single-stock options data access
- Enables: Cross-asset spillover prediction

## References

- TGNN paper: [arXiv:2504.07923](https://arxiv.org/abs/2504.07923)
- Literature review: `docs/reference/auxiliary_research/gnn_literature_review.md`

---

**Labels:** `implementation`, `gnn`, `paper-5`, `blocked`
