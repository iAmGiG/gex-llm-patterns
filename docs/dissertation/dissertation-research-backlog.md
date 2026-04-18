# Future Research Tracker: GitHub Issues 115-119

**Created:** 2025-11-09
**Last substantive update:** 2025-11-09
**Purpose:** Snapshot of dissertation research roadmap as of Nov 2025
**Status:** Historical snapshot — dissertation defense proposal has since been made. Paper 1 published at IEEE BigData 2025; Paper 2 accepted at AIAI 2026 and under review at JRFM. See [docs/papers/extensions/](../papers/extensions/) for consolidated future-work tracking.

---

## Overview

Five GitHub issues (115-119) created to capture future research ideas without premature commitment. Each issue is scoped with explicit acknowledgment of unknowns and timeline realism (2-4 years out).

**Key principle:** These are research notebooks, not firm commitments. Scope will evolve as you learn from Papers 1-2 and feedback from advisor.

---

## Issues at a Glance

| Issue | Type | Title | Timeline | Status |
|-------|------|-------|----------|--------|
| #115 | Dissertation | Sensitivity Analysis (Threshold Robustness) | 2-3 yrs | PLANNED |
| #116 | Paper 4 | Intraday GEX Regime Shifts | Year 3 | CONCEPT |
| #117 | Paper 5 | Cross-Asset Dealer Hedging Networks | Year 3-4 | CONCEPT |
| #118 | Paper 6 | Single-Stock Options Flow Quality | Year 3-4 | CONCEPT |
| #119 | Meta | Dissertation Structure & Paper Sequencing | Ongoing | LIVING DOC |

---

## Issue #115: [Dissertation] Sensitivity Analysis for Threshold Robustness

**GitHub:** <https://github.com/iAmGiG/gex-llm-patterns/issues/115>

### Purpose

Dissertation defense material (not journal publication). Answer committee questions about parameter sensitivity and demonstrate methodological rigor in dissertation appendix.

### Scope

**Phase 1 (Core):**

- GEX magnitude thresholds: ±20% variations
- Concentration thresholds: 60-80% ranges
- Temporal windows: DTE and proximity variations

**Phase 2 (If time):**

- Bootstrap confidence intervals
- Hypothesis testing vs baseline
- Multiple testing corrections

**Phase 3 (Stretch):**

- Regime stratification (VIX, market direction)
- Conditional detection heatmaps

### Key Questions

- How stable are detection rates across parameter variations?
- What are "safe operating ranges" for deployment?
- Where do patterns break down?

### Timeline

- Start: After Paper 2 validation complete
- Complete: Before dissertation defense (2-3 years)
- Effort: 15-20 hours

### Related Work

- Builds on: #113 (Dealer citations foundation)
- Complements: #105 (Multi-year validation)
- Uses: #112 (Batch API for cost control)

---

## Issue #116: [Future Research] Intraday GEX Regime Shifts

**GitHub:** <https://github.com/iAmGiG/gex-llm-patterns/issues/116>

### Practitioner Insight

"Positions for the day are relatively accurate but we have seen that change and large positions shift intraday causing market moves."

### Research Gap

Existing academic work (Krishnan, Anderegg, Dim) focuses on daily/EOD analysis. No systematic study of intraday gamma dynamics.

### Core Question

Can we detect **when** gamma regimes flip intraday, and does this improve prediction of mechanical price moves?

### Proposed Approach

- Calculate GEX at 4 snapshots: 9:45 AM, 12:00 PM, 3:00 PM, 4:00 PM
- Identify regime flips (positive ↔ negative)
- Measure price impact in 30-minute window after flip
- Compare intraday detection vs EOD-only approach

### Hypotheses to Test

1. Intraday flips predict larger moves than EOD levels alone
2. Most regime shifts occur near 3 PM (closing window)
3. LLMs can detect early warning signs from partial intraday data

### Timeline

- Paper 4 candidate (Year 3 of PhD)
- Prerequisite: Paper 2 (regime classification) complete
- Requires: Data access exploration for intraday GEX costs

### Open Questions

- [ ] What vendors have intraday GEX at reasonable cost?
- [ ] Are 4 snapshots sufficient or need higher frequency?
- [ ] How to handle overnight gap risk?
- [ ] Standalone paper or dissertation chapter?

### Potential Contribution

First academic work quantifying intraday dealer gamma dynamics

---

## Issue #117: [Future Research] Cross-Asset Dealer Hedging Networks

**GitHub:** <https://github.com/iAmGiG/gex-llm-patterns/issues/117>

### Practitioner Insight

"Selling JPM but buying XLF... Cross asset strategies."

### The Gap

- **Naive assumption:** JPM options → hedge with JPM stock
- **Reality:** JPM options → hedge with XLF + JPM + SPY + sector basket
- **Problem:** Single-asset GEX misses this cross-asset complexity

### Core Questions

1. How often do dealers hedge single-stock gamma with sector ETFs?
2. What's the correlation structure between stocks and sectors?
3. How much dealer exposure does naive GEX miss?
4. Do cross-asset patterns predict volatility spillovers?

### Potential Approaches

**Approach A: Network Analysis**

- Nodes: Individual stocks + sector ETFs + index
- Edges: Gamma exposure correlations
- Research: How network structure changes during stress?

**Approach B: Portfolio Hedging Model**

- Given JPM gamma, predict optimal hedge basket
- Test: Does (XLF + BAC + C) hedge better than JPM alone?

**Approach C: LLM Pattern Detection**

- Detect: "Large JPM put buying + XLF call selling + SPY neutral"
- Interpret: "Sector-neutral volatility trade, not directional JPM"

### Data Requirements (Complex)

- Single-stock options OI
- Sector ETF options OI (XLF, XLK, XLE, etc.)
- Index options OI (SPY, SPX)
- **Challenge:** Most vendors separate single-stock from index

### Simplified Scope

- Phase 1: Financials only (JPM, BAC, C, GS, MS vs XLF)
- Phase 2: Use correlation as hedging proxy
- Phase 3: Hand-picked case studies before systematic test

### Timeline

- Year 3-4 of PhD
- Prerequisite: Papers 1-2 complete, possibly Paper 3 (sector rotation)
- Effort: High (6+ months) due to data engineering

### Open Questions

- [ ] Can we access dealer hedge book data?
- [ ] Is correlation sufficient proxy or need actual flows?
- [ ] Focus on crisis periods or normal times?
- [ ] Standalone paper or dissertation chapter?

### Potential Contribution

- Quantify spillover effects in options market
- Show how single-asset analysis misses critical hedging dynamics
- Top-tier venue potential (JFE, RFS) or strong dissertation chapter

---

## Issue #118: [Future Research] Single-Stock Options Flow Quality

**GitHub:** <https://github.com/iAmGiG/gex-llm-patterns/issues/118>

### Practitioner Insight

"The synthesizing of flow across 16 exchanges gets hairy and I see people flag flow wrong all the time. Or think something way out of the money is relevant."

### The Problem

**Exchange Fragmentation:**

- Same option trades on 16+ venues (CBOE, ISE, AMEX, PHLX, BOX, etc.)
- Naive aggregation creates false signals

**False Signals Examples:**

- "10k contracts traded!" → But 1-lot HFT bots (not real positioning)
- "Large OTM flow!" → But 0.05 delta lottery tickets (not actionable)
- "Unusual activity!" → But standard market making

### Core Questions

1. What % of "flagged significant flow" is actually noise?
2. How do you classify trade intent without seeing order IDs?
3. Can LLMs improve signal-to-noise in options flow?
4. Does "cleaned" flow predict stock moves better than raw flow?

### Potential Approaches

**Approach A: Supervised Learning (Need Ground Truth)**

- Partner with market maker for labeled dataset
- Labels: "Customer-initiated" vs "Our hedging" vs "Arb noise"
- Train ML/LLM on microstructure features

**Approach B: Unsupervised Clustering**

- Cluster trades into: Informed vs Noise vs Market-making
- Validate: Do "informed" clusters predict?
- Advantage: No ground truth needed

**Approach C: Context-Aware OTM Filtering**

- "10k at 0.05 delta 30 DTE" → Likely irrelevant
- "10k at 0.05 delta 1 DTE" → Possibly relevant (0DTE gamma)
- Use LLM to evaluate strategic meaningfulness

**Approach D: Cross-Exchange Deduplication**

- Detect: "Same order routed across venues"
- Deduplicate intelligently

### Simplified Scope (Realistic)

**Data Phase:**

- Phase 1: CBOE only (primary exchange)
- Phase 2: Add 2-3 major venues (ISE, PHLX)
- Phase 3: Full consolidation only if Phases 1-2 show material difference

**Frequency Phase:**

- Phase 1: EOD flow analysis (daily aggregates)
- Phase 2: 15-minute buckets
- Phase 3: Tick-level only if necessary

### Timeline

- Year 3-4 of PhD
- Prerequisite: Established credibility from Papers 1-2
- Requires: Data vendor investigation for costs

### Open Questions

- [ ] Can we access multi-exchange trade data affordably?
- [ ] Which venue is most "information-rich" for shortcuts?
- [ ] Is this Paper 6 or dissertation-only work?
- [ ] Need market maker partnership for labeled validation data?

### Potential Contribution

- First ML/LLM application to options flow quality control
- Quantifies noise in commonly-used options data
- Practitioner-friendly venue (JOIM, JFM) or strong dissertation chapter

---

## Issue #119: [Meta] Dissertation Structure & Paper Sequencing

**GitHub:** <https://github.com/iAmGiG/gex-llm-patterns/issues/119>

### Purpose

Living document tracking overall dissertation structure. Updates as research evolves.

### Current Structure (Version 1.0)

**Part I: Foundations (Core Papers)**

- Paper 1 ✅ Submitted: Index options, dealer constraints, obfuscation testing
- Paper 2 🔄 In Progress: Regime classification, 30-day windows

**Part II: Extensions (Planned, May Evolve)**

- Paper 3 📋 Planned: Cross-asset flows, sector rotation
- Paper 4 💡 Concept: Intraday dynamics (#116)
- Paper 5 💡 Concept: Cross-asset networks (#117)
- Paper 6 💡 Concept: Flow quality (#118)

**Part III: Integration (Dissertation-Only)**

- Sensitivity analysis (#115)
- Combined trading system
- Real-world deployment
- Limitations and future work

### Evolution Expectations

**Version 2.0 (Future):**

- Some concept papers merge (e.g., #116 + #117)
- Some become dissertation-only chapters
- New ideas from Paper 2 results reshape structure

### Timeline Milestones

- **Now**: Paper 1 in review, Paper 2 validation
- **Month 6**: Paper 1 revisions, Paper 2 draft
- **Month 12**: Paper 2 submitted, Paper 3 design
- **Month 18**: Paper 3 in progress
- **Month 24**: Dissertation proposal (lock structure)
- **Month 36+**: Final papers + dissertation writing

### Open Strategic Questions

- [ ] Target 3 papers + dissertation OR 5 papers + dissertation?
- [ ] Focus on top-tier journals (JFE, RFS, AER) or tier-2 (JFM, JOIM)?
- [ ] When to start integrating papers into dissertation narrative?
- [ ] How will advisor feedback reshape this structure?

### Key Principles

1. **Flexible Scope:** Each paper/concept includes "may evolve to" language
2. **Open Questions:** Explicit unknowns rather than premature commitments
3. **Priority Realism:** Most future work is backlog—ideas to revisit later
4. **Timeline Honesty:** These are 2-4 years out, not immediate plans
5. **No Over-Commitment:** "Concept" and "TBD" labels signal thinking-stage

### Living Document Philosophy

These issues serve as research notebooks that evolve as you:

- Get feedback from advisor
- Discover data availability and costs
- Learn from Papers 1-2 what actually matters
- Talk to practitioners about real problems
- Identify new research questions

---

## Implementation Strategy

### How to Use These Issues

1. **Regular Updates:** Review every 3-6 months
   - Update timeline as you progress
   - Refine scope as you learn
   - Add new questions as they emerge

2. **Advisor Discussion:** Share with advisor
   - Get feedback on prioritization
   - Discuss realistic scope
   - Align with dissertation timeline

3. **Community Feedback:** Use as discussion points
   - Share with practitioners for validation
   - Discuss with peers for methodological input
   - Refine based on feedback

4. **Scope Evolution:** Let issues evolve
   - Add unknowns as you uncover them
   - Merge related issues if combined makes sense
   - Split issues if scope grows too large

### When to Start Each Issue

**Issue #115 (Dissertation):**

- Can start after Paper 2 validation (not before)
- Relatively straightforward once baseline established
- Good "wrapping up" work before defense

**Issue #116 (Intraday):**

- Research question validated with practitioners ✓
- Data exploration needed first
- Realistic start: Month 12-18 of PhD

**Issue #117 (Cross-Asset Networks):**

- Complex data engineering required
- Start research design after Paper 2
- Implementation: Month 18-24 of PhD

**Issue #118 (Flow Quality):**

- Interesting but complex
- Data cost investigation needed
- Realistic start: Month 18-24 of PhD

**Issue #119 (Dissertation Structure):**

- Update continuously
- Lock structure at Month 24 (proposal stage)
- Will drive decisions about #115-118

---

## Your Immediate Focus (Next 2-3 Months)

### DO

- ✅ Wait for Paper 1 reviews and address feedback
- ✅ Complete Paper 2 regime classification validation
- ✅ Work on Issue #114 (dissertation appendix, not a paper)
- ✅ Update Issue #119 (dissertation structure) quarterly

### DON'T

- ❌ Start Issue #115-118 research
- ❌ Commit deeply to scope details
- ❌ Assume timelines are firm

### MAYBE (Check with Advisor)

- 📋 Begin preliminary data exploration for #116-118
- 📋 Identify practitioners to discuss #116-118 ideas
- 📋 Scoping conversations for potential Paper 3

---

## Key Quotes to Remember

From your main chat:

> "Bottom Line: Paper 1 done, wait for reviews. Paper 2 continue regime work. Issue #114 is dissertation appendix not a paper. Real-world complexity is good future papers (3-4 years out) - document as issues, don't start yet."

This entire set of 5 issues implements exactly that philosophy:

- **Papers 1-2** get focused attention now
- **Issue #114** is explicitly dissertation appendix (not paper)
- **Issues #115-118** are 2-4 years out (documented, not started)
- **Issue #119** tracks the big picture as it evolves

---

**Status:** ✅ Complete
**Next Review:** Month 6 (after Paper 2 draft complete)
**Last Updated:** 2025-11-09
