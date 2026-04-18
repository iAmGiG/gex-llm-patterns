# Research Roadmap: LLM-Based Market Microstructure Analysis

> ⚠️ **Historical snapshot — January 13, 2026.** This document captured the research trajectory as of early 2026. For current state see:
>
> - **Paper 1**: ✅ Published at IEEE BigData 2025 (Dec 2025) — [`docs/papers/paper1/`](paper1/)
> - **Paper 2**: ✅ Accepted at AIAI 2026 (camera-ready May 2026), 🔄 under review at JRFM (MDPI), rejected at Digital Finance — [`docs/papers/paper2/`](paper2/)
> - **Forward-looking research directions**: consolidated in [`docs/papers/extensions/`](extensions/) (supersedes the Paper 3 / Paper 4 planning referenced below)
> - **GitHub issues referenced below**: all closed as of April 2026
>
> The content below is preserved as the trajectory-at-the-time, not current state.

---

**Last Updated**: January 13, 2026
**Status (at time of writing)**: Paper #1 published (arXiv:2512.17923), Paper #2 ready for submission (figures polished Jan 2026)

**Related Issues (all since closed)**: #118 (Dissertation Structure), #135 (Paper #3 Planning), #136 (Paper #4 Planning)

---

## Overview

This document outlines the multi-paper research trajectory for validating LLM understanding of market microstructure constraints through obfuscation testing.

**Core Methodology**: Obfuscation testing framework (strip temporal context, force reasoning from structure)
**Test Domain**: Options market dealer constraints (gamma exposure hedging)
**Key Innovation**: Rigorous validation that distinguishes understanding from memorization

---

## Paper Timeline

| Paper | Status | Timeline | Contribution |
|-------|--------|----------|--------------|
| **Paper #1** | ✅ Published | Dec 2025 | Baseline obfuscation methodology (single-day, SPY) |
| **Paper #2** | ✅ Ready for Submission | Q1 2026 | 30-day regime detection + 0DTE hypothesis confirmed |
| **Paper #3** | 🔀 Migrating | Q2 2026 | Cross-asset generalization → separate repository |
| **Paper #4+** | 🔀 Migrating | 2026+ | Causal networks, pattern discovery → separate repository |

---

## Paper #1: Obfuscation Testing Baseline (Workshop)

### Status: ✅ Published December 2025 (arXiv:2512.17923)

**Title**: "Validating Large Language Model Understanding of Market Microstructure Through Obfuscation Testing"

**Venue**: LLM-Finance 2025 Workshop @ IEEE BigData 2025

**Contribution**:

- Novel obfuscation testing framework for LLM validation
- Proof that LLMs can detect structural dealer constraints without temporal context
- Multi-pattern validation (3 patterns, 242 days, 726 tests)

**Key Results**:

- **Detection**: 71.5% average (unbiased prompts across 3 patterns)
- **Accuracy**: 91.2% (predictions materialize)
- **Validation**: Full 2024 (242 trading days per pattern)

**GitHub Issues**:

- #88: Paper #1 status tracking
- #90: Prompt bias investigation (resolved)
- #91-93: Core figures (complete)

**Documentation**: `docs/papers/paper1/`

---

## Paper #2: Regime Detection via Sequential GEX (Journal)

### Status: ✅ Ready for Submission (Figures polished Jan 2026, validation complete Nov 20, 2025)

**GitHub Issues**: [#89 (30-Day Regime Detection)](https://github.com/iAmGiG/gex-llm-patterns/issues/89), [#107 (Validation Strategy)](https://github.com/iAmGiG/gex-llm-patterns/issues/107)

### STRATEGIC PIVOT (November 5, 2025)

**Original Plan**: 5-day trajectory analysis (accumulation/relief/reversal)

- Result: 98-100% detection across all conditions (2020 weak GEX vs 2024 strong GEX)
- Finding: Detects universal daily hedging (trivial), not distinctive patterns (interesting)
- Decision: Pivot to 30-day regime windows for meaningful selectivity (30-50% expected detection)

---

**Current Approach**: 30-Day Regime Detection

**Title**: TBD - "LLM Detection of Persistent Dealer Gamma Regimes: 0DTE Evolution and Regime Persistence"

**Target**: Journal submission (6-8 pages)

**Research Questions**:

1. Can LLMs identify **persistent market regimes** from dealer gamma positioning?
2. Did 0DTE proliferation (2020→2024) increase regime persistence?
3. How do LLMs discriminate persistent regimes from transitional periods?

**Methodology**:

- **30-day regime windows** (not 5-day trajectories)
- **Regime classification**:
  - Persistent Positive: >70% days (21+/30) positive GEX, >$5B avg, ≤5 flips
  - Persistent Negative: >70% days (21+/30) negative GEX, >$5B avg, ≤5 flips
  - Transitional: Frequent flips, no dominant direction (REJECT)
  - Low Conviction: Consistent but weak magnitude <$5B (REJECT)
- **Expected selectivity**: 30-50% detection (vs 98-100% for 5-day)
- **0DTE comparison**: 2024 vs 2020 regime persistence

**Expected Contributions**:

1. Regime detection with meaningful selectivity (30-50%, not universal)
2. 0DTE proliferation effect on regime stability
3. LLM discrimination of structural vs transitional periods
4. Temporal extension of obfuscation framework (30-day, not 5-day)

**Validation Status** (Nov 20, 2025):

- ✅ Phase 1 (Q1 2024 Baseline): 71.2% detection (37/52 windows) - Borderline high
- ✅ Phase 2 (Negative Controls): All tests PASSED
  - Phase 2a (Shuffle): 61.1% Q1 2024 vs 12.1% 2020 (5x FP difference proves selectivity)
  - Phase 2b (Transitional): 0% FP (perfect rejection)
  - Phase 2c (Low-Magnitude): 0% FP (perfect rejection)
- ✅ Phase 3 (Full 2024): **81.2% detection** (181/223 windows) - Extreme year confirmed
- ✅ Phase 4 (2020 Comparison): **12.1% detection** (27/223 windows) - Normal baseline

**KEY FINDING**: 69.1pp difference (2024: 81.2%, 2020: 12.1%) confirms:

1. ✅ Framework IS selective (5.7x discrimination)
2. ✅ 2024 was genuinely extreme (not overdetection)
3. ✅ 0DTE hypothesis CONFIRMED (p < 0.001, φ = 0.672)

**Implementation Complete** (Nov 6-19, 2025):

- ✅ RegimeClassifier module (332 lines)
- ✅ SequentialGEXFetcher updated (window_size=30 parameter)
- ✅ Regime detection prompt v1
- ✅ OpenAI Batch API integration (50% cost reduction)
- ✅ Phase 2 negative control generators (shuffle, transitional, low-magnitude)

**Documentation**:

- `docs/papers/paper2/` - Complete Paper #2 documentation
- `docs/papers/paper2/methodology.md` - Regime criteria and framework
- `docs/papers/paper2/validation_strategy.md` - 4-phase validation roadmap
- `docs/papers/paper2/results/phase1_results.md` - Phase 1 detailed results
- `docs/papers/paper2/execution_plan.md` - Current work and next steps

**Section VI.K Added (December 2025)**:

- "Sensitivity to GEX Formulation" subsection added to Discussion
- Explains absolute dollar-scaling (S²) vs practitioner normalized approaches
- Justifies why magnitude preservation is essential for obfuscation testing
- Introduces Formula Agreement Test as future validation (Issue #186)
- Cross-project coordination: AutoTrader-AgentEdge Issue #502

**5-Day Work Value**: Valuable negative result (98-100% detection too universal), documented in archived sessions

---

## Paper #3: Cross-Asset Generalization (Journal)

### Status: 🔀 Migrating to Separate Repository

> **Note**: Paper #3 development is being moved to a dedicated repository to keep this repo focused on Papers #1-2 (SPY-based obfuscation validation). The cross-asset work requires different data infrastructure and will be tracked separately.

**GitHub Issue**: [#135 (Per-Strike GEX & Intraday Dynamics)](https://github.com/iAmGiG/gex-llm-patterns/issues/135)

**Title**: TBD - "Cross-Asset Validation of LLM Market Microstructure Understanding"

**Target**: Journal submission (8-10 pages)

**Research Questions**:

1. Does obfuscation testing generalize beyond SPY index options?
2. Do dealer constraints differ between index and single-name options?
3. Can LLMs detect stock-specific vs market-wide patterns?

**Methodology**:

- **Test on 10-20 individual stocks** (high liquidity: AAPL, MSFT, NVDA, TSLA, etc.)
- **Use sequential analysis** if Paper #2 validates it
- **Compare dealer dynamics**: Index (SPY) vs single-name (individual stocks)
- **Pattern persistence**: Test if patterns hold across asset classes

**Key Differences (Index vs Single-Name)**:

- **Index options**: Broader dealer base, market-making focus
- **Single-name options**: Concentrated positions, hedging focus
- **Gamma dynamics**: SPY has constant 0DTE volume, stocks vary
- **Liquidity**: SPY ultra-liquid, individual stocks more fragmented

**Expected Contributions**:

1. Full generalization proof (methodology works beyond single asset)
2. Cross-asset comparison (index vs single-name dealer dynamics)
3. Pattern persistence analysis (universal vs asset-specific constraints)
4. Combined temporal + cross-asset validation (if Paper #2 successful)

**Dataset Requirements**:

- Individual stock options data (2024)
- ~10-20 stocks × 242 days = ~2,420-4,840 tests
- Higher data collection effort than Paper #2

**Estimated Effort**:

- 1-2 weeks data collection (individual stocks)
- 1 week validation runs
- 2-3 weeks analysis/writing

**GitHub Issue**: #6 (Cross-asset validation) - relates to Paper #3

**Dependencies**:

- Paper #1 acceptance
- Paper #2 submission (determine if sequential method is validated)

---

## Paper #4+ Candidates (Long-Term)

### Status: 🔀 Migrating to Separate Repository

> **Note**: Paper #4+ work (causal constraint networks, pattern discovery, comparative LLMs) is being moved to a dedicated repository alongside Paper #3. This repo will remain focused on the completed Papers #1-2.

**GitHub Issue**: [#136 (Causal Constraint Networks - Graph-Theoretic Framework)](https://github.com/iAmGiG/gex-llm-patterns/issues/136)

### 1. Pattern Discovery (18-24 months)

**Research Question**: Can LLMs *discover* novel patterns (not just validate known ones)?

**Methodology**:

- Unsupervised pattern mining with LLMs
- Move from validation → discovery
- Different evaluation framework (data mining risks)

**Challenges**:

- Requires different validation methodology (how to verify discovered patterns?)
- Higher risk of false positives (data mining concerns)
- Need expert validation for novel patterns

**Status**: Deferred to Paper #4 or beyond (fundamentally different problem class)

### 2. Comparative LLM Analysis (12-18 months)

**Research Question**: How do different LLM architectures perform on constraint detection?

**Methodology**:

- Test multiple LLMs: GPT-4, o3-mini, Claude, open-source models
- Reasoning capabilities comparison
- Structured output quality assessment

**Key Comparison**: Reasoning models (o3-mini) vs standard models (GPT-4)

- Hypothesis: Explicit reasoning improves causal identification

**Status**: Medium-term (requires o3-mini availability)

### 3. Confidence Calibration Study

**Research Question**: Are LLM confidence scores well-calibrated to empirical accuracy?

**Methodology**:

- Compare stated confidence to prediction materialization rates
- Develop post-processing calibration adjustments if needed
- Test across sequential and cross-asset contexts

**Status**: Analysis component (fold into Paper #2 or #3, not standalone)

### 4. Hybrid Formal Methods

**Research Question**: Can we combine formal verification + LLM reasoning?

**Methodology**:

- Formal methods: Prove constraint properties mathematically
- LLM reasoning: Assess practical materialization from context
- Complementary strengths → robust validation

**Status**: Long-term vision (2026+)

### 5. Real-Time Applications

**Research Question**: Can obfuscation-validated LLMs monitor markets in real-time?

**Application**:

- Automated constraint detection
- Explainable alerts (WHO→WHOM→WHAT)
- Regulatory reporting (market structure surveillance)

**Status**: Long-term (requires production infrastructure)

---

## Superseded Ideas

These ideas were proposed earlier but have been superseded by the current roadmap:

### Alpha Decline Investigation (Oct 13, 2025)

**Original proposal**: Explain why profitability declined Q1→Q4 2024 despite stable detection

**Status**: **SUPERSEDED** - Fold into Paper #2 discussion section
**Rationale**: Interesting but not core methodology contribution. Sequential analysis may naturally explain regime changes.

### Pattern Discovery as Paper #3 (Oct 22, 2025)

**Original proposal**: Paper #3 focused on unsupervised pattern mining

**Status**: **DEFERRED** to Paper #4+
**Rationale**: Advisor sequence ("before going to individual stocks") prioritizes cross-asset generalization. Pattern discovery is fundamentally different problem requiring different validation framework.

---

## GitHub Issues Mapping

### Cross-Cutting

- **[#118](https://github.com/iAmGiG/gex-llm-patterns/issues/118)** (OPEN): Dissertation Structure & Paper Sequencing

### Paper #1 Related

- **[#88](https://github.com/iAmGiG/gex-llm-patterns/issues/88)** (OPEN): Paper #1 status tracking (submitted Oct 26)
- **#90** (CLOSED): Prompt bias resolved
- **#91-93** (CLOSED): Core figures complete
- **#95** (CLOSED): Presentation diagrams
- **#96-97** (CLOSED): DataObfuscator optimization, performance benchmarks

### Paper #2 Related

- **[#89](https://github.com/iAmGiG/gex-llm-patterns/issues/89)** (OPEN): 30-Day Regime Detection Framework (primary methodology)
- **[#107](https://github.com/iAmGiG/gex-llm-patterns/issues/107)** (OPEN): 4-Phase Validation Strategy
- **#112** (CLOSED): OpenAI Batch API implementation (50% cost reduction)
- **#137** (CLOSED): JSON parsing fixes (88.5% → 100% completion)
- **#139** (CLOSED): Documentation consolidation (48 → 10 files)

### Paper #3 Related

- **[#135](https://github.com/iAmGiG/gex-llm-patterns/issues/135)** (OPEN): Per-Strike GEX Analysis & Intraday Dynamics
- **#87** (OPEN): Cross-asset validation (5-7 individual equities)

### Paper #4+ Related

- **[#136](https://github.com/iAmGiG/gex-llm-patterns/issues/136)** (OPEN): Causal Constraint Networks (Graph-Theoretic Framework)

### Infrastructure (Not Paper-Specific)

- **#29** (OPEN): Database optimization
- **#16** (OPEN): Performance improvements
- **#45** (OPEN): Error handling enhancements
- **#13** (OPEN): Pattern consolidation (defer)

---

## Decision Points

### After Paper #1 Acceptance

**Decision**: Proceed with Paper #2 (Sequential GEX) implementation

- **Timeline**: Start immediately after acceptance notification
- **Effort**: 5 days implementation + 2-3 weeks writing
- **Risk**: Low (uses existing data)

### After Sequential Validation (Paper #2)

**Decision 1**: Include sequential in Paper #2 or defer?

- **If accuracy improves**: Paper #2 focuses on sequential methodology
- **If neutral/worse**: Fold into Paper #1 discussion, proceed to Paper #3 without sequential

**Decision 2**: Timeline for Paper #3

- **If Paper #2 quick**: Start Paper #3 data collection in parallel with Paper #2 writing
- **If Paper #2 delayed**: Sequential start (finish Paper #2, then start Paper #3)

### Paper #4+ Direction

**Decision**: After Papers #2-3 complete

- Assess which long-term direction has most impact:
  - Pattern discovery (high risk, high reward)
  - Comparative LLMs (medium risk, clear contribution)
  - Hybrid systems (long-term vision)
  - Real-time applications (practical impact)

---

## Publication Strategy

### Venues

**Paper #1** (Workshop): ✅ PUBLISHED

- LLM-Finance 2025 Workshop @ IEEE BigData 2025
- Published: December 2025 (arXiv:2512.17923)
- Format: 4-6 pages workshop paper

**Paper #2** (Journal): Ready for Submission

- Target: Journal of Financial Markets, Journal of Finance, or similar
- Format: 6-8 pages journal article
- Timeline: Q1 2026 submission
- Status: Figures polished Jan 2026, validation complete

**Paper #3 & #4+**: Migrating to Separate Repository

- Cross-asset generalization and causal networks work
- Will be tracked in dedicated repository
- Timeline: 2026+

### Conference Presentations

Consider presenting at:

- **AFA** (American Finance Association)
- **WFA** (Western Finance Association)
- **MFA** (Midwest Finance Association)
- **NeurIPS** (ML track)
- **ICML** (Finance + ML)

---

## Key Principles

Throughout all papers, maintain:

1. **Obfuscation rigor**: Always strip temporal context
2. **WHO→WHOM→WHAT**: Explicit causal identification
3. **Academic honesty**: Report failures and limitations
4. **Reproducibility**: All code/data documented
5. **Generalization**: Prove methodology scales beyond cherry-picked examples

---

## Timeline Summary

| Date | Milestone |
|------|-----------|
| ✅ Oct 26, 2025 | Paper #1 submitted |
| ✅ Dec 2025 | Paper #1 published (arXiv:2512.17923) |
| ✅ Jan 2026 | Paper #2 figures polished |
| 🔜 Q1 2026 | Paper #2 submission |
| 🔀 Q2 2026+ | Papers #3-4 → separate repository |

**Repository Focus**: This repository is now complete for Papers #1-2 (SPY obfuscation validation). Papers #3-4 (cross-asset, causal networks) are being migrated to a dedicated repository.

---

## Contact & Collaboration

**Repository**: <https://github.com/iAmGiG/gex-llm-patterns>
**Primary Issues**: #88 (Paper #1), #89 (Paper #2), #6 (Paper #3)
**Documentation**: `docs/papers/paper1/`, `docs/papers/research_roadmap.md`

---

**Status**: Updated January 13, 2026. Paper #1 published, Paper #2 ready for submission. Papers #3-4 migrating to separate repository.
