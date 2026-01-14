# [Research] LLM-Informed GNN Architecture

## Summary

**Type:** Research / Novel Architecture | **Timeline:** Year 3-4 | **Status:** Concept

Explore hybrid architecture where LLM extracts graph structure from GEX patterns, and GNN learns from LLM-informed relationships.

## Motivation

Papers 1-2 demonstrate LLM can detect market mechanics patterns:

- "Large put concentration at 4200 strike"
- "Dealer gamma exposure negative near resistance"
- "Volume anomaly with institutional signature"

**Question:** Can LLM pattern detection inform GNN graph construction for improved prediction?

## Precedent

ChatGPT-Informed GNN ([arXiv:2306.03763](https://arxiv.org/pdf/2306.03763)):

- LLM extracts relationships from financial news
- GNN learns from LLM-extracted structure
- Outperforms both LLM-only and GNN-only on DOW 30

## Proposed Architecture

### Option A: LLM Extracts Edges

```text
Step 1: LLM Pattern Detection
Input: Daily GEX data for 7 assets
Output: Detected relationships
  - "JPM put buying correlated with XLF call selling"
  - "SPY gamma flip preceded BAC volatility spike"

Step 2: Edge Construction
LLM output → Edge weights
  - High confidence pattern → Strong edge
  - No pattern detected → Weak/no edge

Step 3: GNN Training
Train GNN on LLM-informed graph
  - Edges: From LLM relationship extraction
  - Node features: Standard GEX metrics
  - Target: Spillover prediction
```text

### Option B: LLM as Node Feature

```text
Step 1: LLM Regime Classification (per asset)
For each node, LLM classifies:
  - Regime: Positive/Negative/Transitional
  - Confidence: 0-1
  - Pattern type: Pinning/Momentum/Uncertain

Step 2: GNN with LLM Features
Node features include:
  - Standard: GEX, OI, volume
  - LLM-derived: Regime label, confidence, pattern embedding

Step 3: Joint Learning
GNN learns which LLM features matter for spillover
```text

### Option C: Ensemble

```text
Parallel Predictions:
- LLM: P(spillover | GEX patterns)
- GNN: P(spillover | graph structure)

Ensemble:
- Weighted average based on historical accuracy
- Or: Meta-learner selects best predictor per regime
```text

## Research Questions

1. Does LLM-informed graph structure outperform correlation-based edges?
2. Which architecture (A, B, or C) performs best?
3. What's the computational overhead of LLM in the loop?
4. Can we distill LLM knowledge into GNN (train once, deploy without LLM)?

## Implementation Considerations

### Computational Cost

| Approach | LLM Calls | Training Time | Inference Time |
|----------|-----------|---------------|----------------|
| Option A | Once (edge construction) | Standard GNN | Fast (GNN only) |
| Option B | Per sample | Standard GNN | Fast (GNN only) |
| Option C | Per prediction | Standard GNN | Slow (LLM + GNN) |

**Recommendation:** Option A or B preferred for deployment (LLM not in inference loop)

### Data Requirements

- Same as TGNN/Temporal GAT issues
- Plus: LLM API access for pattern extraction
- Plus: Labeled validation set for LLM accuracy

## Novelty Assessment

| Component | Novelty |
|-----------|---------|
| LLM for GEX pattern detection | Established (Papers 1-2) |
| GNN for financial networks | Established (literature) |
| LLM-informed GNN edges | Novel for options domain |
| GEX-specific graph construction | Novel |

**Publication angle:** "We show that LLM-extracted market mechanics relationships provide superior graph structure for GNN-based spillover prediction compared to correlation-based approaches."

## Success Criteria

- [ ] LLM-informed GNN outperforms correlation-based GNN by >5%
- [ ] Architecture is computationally feasible (LLM not in inference)
- [ ] Results interpretable (which LLM patterns matter for GNN?)
- [ ] Generalizes beyond training period

## Risks

| Risk | Mitigation |
|------|------------|
| LLM patterns too noisy for edges | Filter by confidence threshold |
| Circular reasoning (LLM trained on similar data) | Use obfuscated data for LLM |
| Overfitting to LLM errors | Ensemble with correlation baseline |
| High compute cost | Option A (one-time LLM extraction) |

## Dependencies

- Requires: Completed LLM baseline (Papers 1-2 methodology)
- Requires: GNN baseline implementation (TGNN or Temporal GAT)
- Enables: Novel contribution combining both approaches

## Timeline

- **Prerequisite:** TGNN or Temporal GAT working baseline
- **Phase 1:** Design LLM extraction prompts for relationships
- **Phase 2:** Compare LLM-informed vs correlation edges
- **Phase 3:** Full hybrid architecture if Phase 2 positive

## References

- ChatGPT-Informed GNN: [arXiv:2306.03763](https://arxiv.org/pdf/2306.03763)
- Papers 1-2: LLM pattern detection methodology
- Literature review: `docs/reference/auxiliary_research/gnn_literature_review.md`

---

**Labels:** `research`, `novel`, `gnn`, `llm`, `paper-4`, `paper-5`
