# [Implementation] Temporal GAT for Volatility Spillover Prediction

## Summary

**Type:** Implementation | **Timeline:** After methodology selection | **Status:** Blocked (pending methodology decision)

Implement Temporal Graph Attention Network for predicting volatility spillovers between assets based on GEX dynamics.

## Why Temporal GAT

From literature review, Temporal GAT ([arXiv:2410.16858](https://arxiv.org/abs/2410.16858)) excels at:

1. **Directed spillover modeling** - Asymmetric relationships (JPM → XLF ≠ XLF → JPM)
2. **Temporal dynamics** - How network structure evolves over time
3. **Attention weights** - Reveal which assets drive spillovers
4. **Proven results** - Beats GARCH on 15-year, 8-index study

## Proposed Architecture

### Graph Structure

```text
Nodes: Same as TGNN (7 assets in Phase 1)

Edges (Directed):
- Construct using Diebold-Yilmaz spillover index
- Or: GEX-based spillover (novel contribution)
- Asymmetric: Edge(JPM→XLF) ≠ Edge(XLF→JPM)

Temporal Component:
- Rolling windows (e.g., 30-day)
- Graph sequence: G_t, G_{t+1}, ..., G_{t+T}
- Capture how network topology changes
```text

### Temporal GAT Layers

```text
Layer 1: Graph Convolution
- Aggregate neighbor features
- Learn initial node representations

Layer 2: Graph Attention
- Attention weights per edge
- "How much does JPM gamma affect XLF volatility?"

Layer 3: Temporal Encoding
- LSTM/GRU over graph sequence
- Capture regime transitions in network structure

Output:
- Next-period volatility spillover matrix
- Attention heatmap (interpretability)
```text

## Implementation Tasks

### Phase 1: Spillover Index Construction

- [ ] Implement Diebold-Yilmaz spillover index
- [ ] Alternative: GEX-based spillover measure (novel)
- [ ] Validate: Does spillover index correlate with known events?

### Phase 2: Temporal Graph Sequence

- [ ] Build rolling window graph generator
- [ ] Create graph sequence dataset (G_t to G_{t+T})
- [ ] Implement PyG TemporalData loader

### Phase 3: Model Architecture

- [ ] GCN layer for initial embedding
- [ ] GAT layer with multi-head attention
- [ ] Temporal encoder (LSTM over graph sequence)
- [ ] Prediction head (spillover magnitude)

### Phase 4: Training and Evaluation

- [ ] Loss: MSE on spillover prediction
- [ ] Baseline: GARCH, VAR, static GNN
- [ ] Metric: RMSE, directional accuracy

### Phase 5: Interpretability

- [ ] Extract attention weights per time step
- [ ] Visualize: Which edges strengthen in crisis?
- [ ] Validate: Do attention patterns match intuition?

## Novel Contribution Opportunity

**GEX-Based Spillover Index:**

Standard Diebold-Yilmaz uses return/volatility spillovers. We could define:

```text
GEX_Spillover(i→j) = Corr(GEX_i_t, Volatility_j_{t+1})

Interpretation:
- "Does JPM gamma exposure predict XLF volatility tomorrow?"
- Novel measure specific to dealer hedging dynamics
```text

This would be a methodological contribution beyond applying existing GNN.

## Research Questions

1. Does GEX spillover outperform return spillover for edge construction?
2. How does network topology change during stress (COVID, VIX spikes)?
3. Which assets are most central (drive spillovers to others)?
4. Can we predict regime transitions from network structure changes?

## Success Criteria

- [ ] Temporal GAT beats static GNN by >5% on spillover prediction
- [ ] Attention weights identify known spillover relationships
- [ ] Network topology changes are interpretable (crisis = denser graph)
- [ ] GEX spillover index shows novelty vs standard measures

## Dependencies

- Blocked by: GNN Methodology Selection issue
- Requires: Multi-asset GEX data
- Complements: TGNN implementation (can ensemble)

## References

- Temporal GAT paper: [arXiv:2410.16858](https://arxiv.org/abs/2410.16858)
- Diebold-Yilmaz: "Better to Give than to Receive" (2012)
- Literature review: `docs/reference/auxiliary_research/gnn_literature_review.md`

---

**Labels:** `implementation`, `gnn`, `paper-5`, `blocked`, `novel-contribution`
