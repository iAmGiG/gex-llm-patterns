# Research Roadmap: LLM-Based Market Microstructure Analysis

**Last Updated**: November 5, 2025
**Status**: Paper #1 submitted (Oct 26), Paper #2 pivoted to 30-day regimes (Nov 5)

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
| **Paper #1** | ✅ Submitted | Oct 2025 | Baseline obfuscation methodology (single-day, SPY) |
| **Paper #2** | 🔄 In Progress | Q1 2026 | 30-day regime detection (pivoted Nov 5 from 5-day approach) |
| **Paper #3** | 📋 Planned | Q2 2026 | Cross-asset generalization (individual equities) |
| **Paper #4+** | 💭 Future | 2026+ | Pattern discovery, comparative LLMs, hybrid systems |

---

## Paper #1: Obfuscation Testing Baseline (Workshop)

### Status: ✅ Submitted October 26, 2025

**Title**: "Validating Large Language Model Understanding of Market Microstructure Through Obfuscation Testing"

**Target**: LLM-Finance 2025 Workshop @ IEEE BigData 2025

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

### Status: 🔄 In Progress - Q1 2026 (Pivoted Nov 5, 2025)

**⚠️ STRATEGIC PIVOT (November 5, 2025)**

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

**Implementation Status** (Nov 5, 2025):
- ✅ RegimeClassifier module (332 lines)
- ✅ SequentialGEXFetcher updated (window_size=30 parameter)
- ✅ Regime detection prompt v1
- ⏸️ Phase 1 validation (Q1 2024, ~32 windows)

**Expected Timeline**:
- Week 1 (Nov 4-8): Core implementation ✅
- Week 2 (Nov 11-15): Phase 1 + Phase 2 validation
- Week 3 (Nov 18-22): Phase 3 (2020 comparison)
- Weeks 4-5 (Dec): Analysis + paper draft

**Documentation**:
- `docs/papers/paper2/methodology/regime_windows_design.md`
- `docs/papers/paper2/validation/test4/` (explains pivot)
- Issues #89 (30-day methodology), #107 (validation strategy)

**5-Day Work Value**: Valuable negative result, documented in sessions archive

---

## Paper #3: Cross-Asset Generalization (Journal)

### Status: 📋 Planned - Q2 2026

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

## Open GitHub Issues Mapping

### Paper #2 Related

- **#89** (OPEN): Sequential GEX Analysis - Paper #2 primary methodology

### Paper #3 Related

- **#6** (OPEN): Cross-asset validation - relates to Paper #3

### Paper #1 Complete

- **#88** (OPEN): Paper #1 status tracking (submitted Oct 26)
- **#90** (CLOSED): Prompt bias resolved
- **#91-93** (CLOSED): Core figures complete
- **#94** (OPEN): Suggested advanced figures (future work)
- **#95** (CLOSED): Presentation diagrams
- **#96-97** (CLOSED): DataObfuscator optimization, performance benchmarks

### Infrastructure (Not Paper-Specific)

- **#29** (OPEN): Database optimization
- **#16** (OPEN): Performance improvements
- **#45** (OPEN): Error handling enhancements
- **#13** (OPEN): Pattern consolidation (defer)
- **#74, #75** (OPEN): Additional pattern validation (defer)

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

**Paper #1** (Workshop):

- LLM-Finance 2025 Workshop @ IEEE BigData 2025
- Deadline: October 26, 2025 ✅
- Format: 4-6 pages workshop paper

**Paper #2** (Journal):

- Target: Journal of Financial Markets, Journal of Finance, or similar
- Format: 6-8 pages journal article
- Timeline: Q1 2026 submission

**Paper #3** (Journal):

- Target: Same tier as Paper #2
- Format: 8-10 pages (larger scope with cross-asset)
- Timeline: Q2 2026 submission

**Paper #4+** (Journal/Conference):

- Depends on direction chosen
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
| Nov-Dec 2025 | Paper #1 review period |
| Jan 2026 | Start Paper #2 (sequential GEX) |
| Q1 2026 | Paper #2 submission |
| Q2 2026 | Paper #3 submission (cross-asset) |
| 2026+ | Paper #4+ (discovery/comparative/hybrid) |

**Key Dependency**: Paper #1 acceptance gates Paper #2 timeline. If acceptance delayed, adjust subsequent timelines accordingly.

---

## Contact & Collaboration

**Repository**: <https://github.com/iAmGiG/gex-llm-patterns>
**Primary Issues**: #88 (Paper #1), #89 (Paper #2), #6 (Paper #3)
**Documentation**: `docs/papers/paper1/`, `docs/papers/research_roadmap.md`

---

**Status**: Roadmap consolidated October 25, 2025 based on advisor input (Issue #89) and repository-wide Paper #2/3 reference analysis.
