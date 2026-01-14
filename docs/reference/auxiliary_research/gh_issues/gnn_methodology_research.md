# [Research] GNN Methodology Selection for Cross-Asset Networks

## Summary

**Type:** Literature Review / Methodology | **Timeline:** Pre-implementation | **Status:** Research

Evaluate Graph Neural Network architectures for modeling cross-asset dealer hedging networks. Select optimal approach before implementation.

## Background

GNN research offers methodological foundations for network-based options analysis. Key papers identified in preliminary literature review (January 2026).

## Papers to Evaluate

### Tier 1: Directly Applicable

| Paper | arXiv | Key Contribution |
|-------|-------|------------------|
| Trading GNN (TGNN) | [2504.07923](https://arxiv.org/abs/2504.07923) | Dealer network modeling with interpretable economics |
| Temporal GAT | [2410.16858](https://arxiv.org/abs/2410.16858) | Volatility spillovers as directed graphs |
| Regime-Dependent GNN | MDPI 2025 | Hurst-based regime switching |

### Tier 2: Architecture Patterns

| Paper | arXiv | Key Contribution |
|-------|-------|------------------|
| LSTM-GNN Hybrid | [2502.15813](https://arxiv.org/abs/2502.15813) | Temporal + relational architecture |
| ChatGPT-Informed GNN | [2306.03763](https://arxiv.org/pdf/2306.03763) | LLM extracts graph structure |
| GNN-MS Options | JFM 2024 | Momentum spillover in options pricing |

### Tier 3: Background

| Paper | arXiv | Use |
|-------|-------|-----|
| GNN Financial Review | [2111.15367](https://arxiv.org/abs/2111.15367) | Related work section |

## Evaluation Criteria

- [ ] **Interpretability:** Can we explain *why* edges matter? (Required for finance publication)
- [ ] **Domain fit:** Does architecture match dealer hedging dynamics?
- [ ] **Data compatibility:** Works with available GEX/OI data structure?
- [ ] **Computational feasibility:** Trainable on available compute?
- [ ] **Publication precedent:** Accepted in target venues (JFE, RFS, JFM)?

## Deliverables

1. **Paper summaries:** 1-page summary of each Tier 1 paper
2. **Architecture comparison:** Table of pros/cons for our use case
3. **Recommendation:** Selected approach with justification
4. **Implementation plan:** Data requirements, compute needs, timeline

## Research Questions

1. Is TGNN's dealer-specific framing essential, or can generic GNN work?
2. Do we need temporal extension (Temporal GAT) or static graph sufficient?
3. Can we construct meaningful edges from correlation alone, or need actual flows?
4. What's the minimum graph size for meaningful results?

## Success Criteria

- [ ] All Tier 1 papers read and summarized
- [ ] Clear recommendation documented with rationale
- [ ] Advisor sign-off on selected approach
- [ ] Data requirements confirmed as feasible

## Timeline

- **Week 1-2:** Read and summarize Tier 1 papers
- **Week 3:** Architecture comparison and recommendation
- **Week 4:** Advisor discussion and finalization

## References

- Literature review: `docs/reference/auxiliary_research/gnn_literature_review.md`
- Parent issue: Cross-Asset Dealer Hedging Networks

---

**Labels:** `research`, `methodology`, `gnn`, `paper-5`
