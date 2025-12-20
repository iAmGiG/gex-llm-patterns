# Auxiliary Research

This folder contains supplementary research, comparisons, and reference materials that inform our methodology but are not directly part of the published papers.

## Contents

- [gex_formula_comparison.md](gex_formula_comparison.md) - Complete GEX formula comparison (S², normalization, regime classification)
- [practitioner_methods.md](practitioner_methods.md) - Comparison of practitioner GEX approaches vs our methodology
- [backtesting/](backtesting/) - Walk-forward backtesting results and strategy comparisons

## Related GitHub Issues

| Issue | Project | Purpose |
|-------|---------|---------|
| [#186](https://github.com/iAmGiG/gex-llm-patterns/issues/186) | gex-llm-patterns | Formula Agreement Test (normalized vs absolute GEX) |
| [#502](https://github.com/iAmGiG/AutoTrader-AgentEdge/issues/502) | AutoTrader-AgentEdge | S² scaling test for trading signals |
| [#114](https://github.com/iAmGiG/gex-llm-patterns/issues/114) | gex-llm-patterns | Sensitivity Analysis (includes formula sensitivity) |

## Purpose

This research serves as:

1. **Reference points** for methodology decisions documented in papers
2. **Validation context** - showing we considered alternative approaches
3. **Cross-project coordination** - linking with AutoGen-Trader companion research
4. **Future work foundation** - materials that may inform Papers 3-4

## Relationship to Papers

| Paper | How Auxiliary Research Informs It |
|-------|-----------------------------------|
| Paper 1 | Pattern materialization validation (91.2% accuracy) |
| Paper 2 | Why our GEX calculation vs practitioner approaches (Section 3 citation) |
| Paper 3 | Per-strike analysis builds on practitioner "gamma walls" concept |

## Cross-Project Coordination

**AutoGen-Trader** (companion project) handles:

- Testing practitioner trading rules for alpha generation
- Strategy comparison (which approach makes more money)
- GEX VoterAgent integration (#419)

**This Project** handles:

- Whether LLMs can UNDERSTAND market mechanics
- Obfuscation testing methodology
- Academic rigor and publication

The backtesting work here focuses on **materialization validation** (do detected patterns predict price movement?) rather than trading strategy optimization.
