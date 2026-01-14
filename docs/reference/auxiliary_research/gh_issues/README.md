# GitHub Issue Templates for Papers 3+

**Purpose:** Pre-drafted GitHub issues for the separate Papers 3+ repository.

## Issues in This Directory

| File | Target Paper | Description |
|------|--------------|-------------|
| `gnn_methodology_research.md` | Paper 5 | GNN literature review and methodology selection |
| `tgnn_dealer_networks.md` | Paper 5 | TGNN implementation for cross-asset hedging |
| `temporal_gat_spillovers.md` | Paper 5 | Temporal GAT for volatility spillover prediction |
| `intraday_regime_gnn.md` | Paper 4 | GNN enhancement for intraday regime detection (contingent) |
| `llm_gnn_hybrid.md` | Paper 4/5 | LLM-informed graph construction - novel contribution |

## Usage

When setting up the new repository:

```bash
# Create issues from templates
gh issue create --title "Title from file" --body-file path/to/template.md
```text

Or copy/paste content directly into GitHub issue creation UI.

## Cross-References

These issues reference the main literature review:

- `gnn_literature_review.md` (same directory) - Full paper summaries and citations
