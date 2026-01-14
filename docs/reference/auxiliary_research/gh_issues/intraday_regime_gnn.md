# [Enhancement] GNN for Intraday Regime Detection

## Summary

**Type:** Enhancement | **Timeline:** After baseline LLM approach | **Status:** Future (contingent)

Enhance intraday regime detection with Graph Neural Networks if baseline LLM approach proves insufficient.

## Context

Issue #116 (Intraday GEX Regime Shifts) plans LLM-based detection of intraday regime flips. This issue explores GNN as an enhancement or alternative if:

1. LLM detection accuracy is insufficient (<70%)
2. Strike-level structure proves important for prediction
3. Temporal patterns require more sophisticated modeling

## Relevant Literature

| Paper | Application |
|-------|-------------|
| Regime-Dependent GNN (H-ETE-GNN) | Hurst exponent for regime transition detection |
| LSTM-GNN Hybrid ([2502.15813](https://arxiv.org/abs/2502.15813)) | Temporal snapshots + relational structure |

## Proposed Architecture

### Intraday Graph Structure

```text
Nodes: Strike prices with significant OI
- Filter: OI > threshold (e.g., top 20 strikes)
- Features: Gamma, delta, OI, volume, bid-ask spread

Edges: Gamma concentration relationships
- Adjacent strikes: Always connected
- High-gamma strikes: Connected to ATM
- Weight: Relative gamma contribution

Temporal: 4 snapshots as graph sequence
- 9:45 AM, 12:00 PM, 3:00 PM, 4:00 PM
- Graph structure may change (new strikes become significant)
```text

### Regime Detection Layer

```text
Hurst Exponent Integration:
- Calculate H on intraday GEX series (4 points)
- H > 0.5: Trending regime (momentum)
- H < 0.5: Mean-reverting regime (pinning)
- H ≈ 0.5: Random walk (uncertain)

GNN Behavior Switching:
- Different message passing weights per regime
- Or: Regime as additional node/graph feature
```text

### Prediction Target

```text
Input: Partial intraday data (9:45 AM + 12:00 PM)
Output:
- P(regime flip by 4:00 PM)
- Expected price impact magnitude
- Confidence score
```text

## Implementation Tasks

### Phase 1: Strike-Level Graph

- [ ] Extract intraday strike-level data (4 snapshots)
- [ ] Define node selection criteria (top N by OI/gamma)
- [ ] Build edge construction logic (adjacency + gamma-weighted)

### Phase 2: Temporal Sequence

- [ ] Create graph sequence from 4 snapshots
- [ ] Handle dynamic node sets (strikes may change)
- [ ] Implement temporal data loader

### Phase 3: Hurst Integration

- [ ] Calculate rolling Hurst exponent on GEX
- [ ] Define regime thresholds (0.5 boundary)
- [ ] Integrate as graph-level or node-level feature

### Phase 4: Model and Training

- [ ] LSTM-GNN architecture for temporal + relational
- [ ] Loss: Binary cross-entropy (flip prediction) + MSE (magnitude)
- [ ] Baseline comparison: LLM-only, simple threshold

### Phase 5: Evaluation

- [ ] Compare: GNN vs LLM vs ensemble
- [ ] Analyze: When does GNN add value over LLM?
- [ ] Interpretability: Which strikes/edges drive predictions?

## When to Pursue This

**Triggers to start:**

- LLM baseline accuracy < 70% on regime flip prediction
- Qualitative analysis suggests strike-level structure matters
- Advisor recommends methodological diversity

**Triggers to skip:**

- LLM baseline accuracy > 80% (GNN marginal value unclear)
- Intraday data cost prohibitive
- Timeline constraints favor simpler approach

## Research Questions

1. Does strike-level structure improve prediction over aggregate GEX?
2. Is Hurst exponent calculable with only 4 data points?
3. Can GNN detect regime flips earlier than LLM (from partial data)?
4. What's the compute/accuracy tradeoff vs LLM?

## Success Criteria

- [ ] GNN improves flip prediction accuracy by >5% over LLM baseline
- [ ] Model identifies which strikes drive regime transitions
- [ ] Predictions from partial data (9:45 + 12:00) are actionable
- [ ] Interpretability maintained (not black box)

## Dependencies

- Blocked by: LLM baseline implementation and evaluation
- Requires: Intraday strike-level options data
- Alternative to: Pure LLM approach

## References

- H-ETE-GNN: Hurst + Effective Transfer Entropy GNN
- LSTM-GNN: [arXiv:2502.15813](https://arxiv.org/abs/2502.15813)
- Literature review: `docs/reference/auxiliary_research/gnn_literature_review.md`

---

**Labels:** `enhancement`, `gnn`, `paper-4`, `contingent`, `future`
