# Paper #2: Temporal Dynamics of LLM-Based Market Microstructure Detection

**Status**: ✅ Validation complete. Venue-specific formats under [docs/papers/paper2/aiai/](../aiai/) (AIAI 2026 accepted), [docs/papers/paper2/jfqa/](../jfqa/), and [docs/papers/jrfm/](../../jrfm/) (under review). This folder retains the master LaTeX structure for reference.

## Overview

This directory contains the LaTeX source for Paper #2, which extends Paper #1's obfuscation testing methodology to sequential gamma exposure patterns.

**Title**: Temporal Dynamics of LLM-Based Market Microstructure Detection: Sequential Gamma Exposure Pattern Analysis

**Authors**: Christopher Regan, Ying Xie

**Institution**: Kennesaw State University

---

## Paper Structure

### Main Files

- `Main.tex` - Main document (includes all sections)
- `00_Header.tex` - LaTeX preamble and package imports
- `references.bib` - Bibliography (verified academic citations)

### Section Files

1. `01_Introduction.tex` - Motivation, research questions, contributions
2. `02_Related_work.tex` - Literature review (gamma dynamics, temporal detection, LLM reasoning)
3. `03_Methodology.tex` - Pattern detection rules, outcome verification, statistical framework
4. `04_Experimental_setup.tex` - Dataset, obfuscation, pipeline, baseline comparison
5. `05_Results.tex` - Detection rates, verification rates, GO/NO-GO decision
6. `06_Discussion.tex` - Temporal reasoning, structural understanding, limitations
7. `07_Conclusion.tex` - Summary, implications, future work

### Supporting Directories

- `figures/` - Placeholder for figures (to be generated from results)
- `tables/` - Placeholder for tables (to be generated from results)

---

## Compilation

```bash
cd docs/papers/paper2/latex
pdflatex Main.tex
bibtex Main
pdflatex Main.tex
pdflatex Main.tex
```

Or use LaTeX Workshop in VS Code (recommended).

---

## Current Status

**Phase**: Pre-results (LaTeX structure complete, awaiting validation data)

**TODO Sections** (marked in .tex files):

- Abstract (write after Phase 1 results)
- Introduction (complete after results)
- Results (populate with actual data from Issue #108)
- Discussion (interpret findings)
- Conclusion (summarize contribution)

**Blocked By**:

- Issue #108: Implement Sequential GEX Validation (Day 1-5 implementation)
- Phase 1 fast test (50-day sample or full 248 windows)
- GO/NO-GO decision (determines scope of final paper)

---

## Key Design Decisions

### Alpha Policy (scope_boundaries.md)

**Results Section Language**:
> "Sequential patterns achieved [TBD]% detection with [TBD]% prediction accuracy. Economic alpha remained marginal (+[TBD] bps), consistent with Paper #1 (+5.6 bps), reinforcing that our methodology validates STRUCTURAL understanding rather than profitable trading strategies."

**Discussion Section Language**:
> "The persistence of high detection accuracy ([TBD]%) with marginal profitability ([TBD] bps) across both single-day and sequential approaches demonstrates our methodology measures constraint detection, not alpha generation."

### Pattern Taxonomy

4 sequential pattern types:

1. **Gamma Accumulation** - 30% magnitude increase (predicts high vol, P75 > 0.86%)
2. **Gamma Relief** - 30% magnitude decrease (predicts low vol, P25 < 0.22%)
3. **Gamma Reversal** - Sign flip (predicts spike, P90 > 1.32%) - **0% occurrence in 2024**
4. **Persistent Gamma** - CV < 15% (predicts continuation, P50 < 0.48%)

### Empirical Thresholds (2024 SPY Data)

**T+1 Volatility Distribution**:

- P25: 0.22% (low vol)
- P50: 0.48% (median)
- P75: 0.86% (high vol)
- P90: 1.32% (extreme vol)

**Pattern Significance**:

- $5B minimum mean GEX magnitude
- $8B minimum for accumulation end / relief start
- 40 minimum confidence score

---

## References

### Verified Academic Citations

**Industry Practitioner Perspective**:

- Fishman (2023) - Goldman Sachs gamma derivatives research

**Peer-Reviewed Papers**:

- Baltussen et al. (2021) - Hedging demand and intraday momentum (JFE)
- Gao et al. (2018) - Market intraday momentum (JFE)

### TODO: Add Citations For

- Temporal pattern detection (time series, regime detection)
- LLM reasoning (temporal understanding, sequence modeling)
- Granger causality (econometric foundations)
- Import relevant citations from Paper #1 (obfuscation testing, WHO→WHOM→WHAT)

### DO NOT CITE (Not Academic Sources)

- SpotGamma (commercial data provider) - Mention in text only
- GTBR Working Paper (2024) - Authors unknown, cite Baltussen/Gao instead

---

## Phase 1 vs Phase 2 Strategy

### Phase 1 (2024 Baseline - Issue #108)

- **Data**: 248 5-day windows (2024 SPY only)
- **Thresholds**: 2024-specific (P75=0.86%, P25=0.22%, etc.)
- **Goal**: GO/NO-GO decision (does sequential improve vs single-day?)
- **Patterns Tested**: Accumulation, Relief, Persistent (Reversal 0% occurrence)

### Phase 2 (Multi-Year Extension - Issue #107, OPTIONAL)

- **Data**: 702 5-day windows (2023-2025 combined)
- **Thresholds**: Pooled (~5-10% higher, more conservative)
- **Goal**: Demonstrate robustness across regimes
- **Patterns Tested**: All 4 (including Reversal with regime variation)

**Decision Point**: Proceed to Phase 2 IF Phase 1 shows ≥2 patterns with hit rate > baseline + 10pp AND p < 0.05

---

## Related Documentation

**Paper #2 Foundations**:

- `docs/papers/paper2/outcome_verification_thresholds.md` - Empirical thresholds
- `docs/papers/paper2/sequential_pattern_detection_rules.md` - Algorithmic definitions
- `docs/papers/paper2/scope_boundaries.md` - In/out of scope decisions

**GitHub Issues**:

- Issue #107: Paper #2 Sequential GEX Validation Strategy
- Issue #108: Implement Sequential GEX Validation (Phase 1)

---

**Last Updated**: 2025-11-01
**Next Step**: Implement Issue #108 (5-day pattern detection and validation)
