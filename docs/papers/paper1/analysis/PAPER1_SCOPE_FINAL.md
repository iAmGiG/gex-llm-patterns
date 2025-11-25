# Paper #1 Final Scope - Issue Triage Complete (Nov 26, 2025)

## Issues CLOSED Per MC Guidance

### ✅ #105: Causal Discovery (PC/FCI Algorithms)

**Reason**: Shifts paper from "LLM validation" to "mechanism discovery"

- Granger causality (p=0.042) is sufficient
- High risk of noisy results
- Would bury Issue #143's "mic drop" moment
**Save for**: Paper #3 (mechanism discovery focus)

### ✅ #121: Multi-Year Validation (2022-2024)

**Reason**: Cross-regime validation is "nice-to-have", not "fatal flaw"

- Issue #143 (raw chain) is stronger evidence
- 242 days in 2024 = robust sample
- Issue #141 proves sensitivity within regime
**Save for**: Dissertation appendix / future research

### ✅ #148: Expand Pattern Taxonomy (3 → 5+ patterns)

**Reason**: More patterns = more p-hacking attack surface

- Current 3 patterns test same mechanism (dealer hedging)
- Three is sufficient for framework generality
- Six patterns dilutes focus without proportional benefit
**Save for**: Future research / Paper #3

### ✅ #87: Individual Equities Extension

**Reason**: SPY is optimal test case (liquid, no confounders)

- Individual stocks introduce earnings/news noise
- Not claiming "works for all assets"
- Claiming "LLM does structural reasoning"
**Save for**: Future research / dissertation

### ✅ #142: Base Rate via Dual GEX (OI vs Volume)

**Reason**: Issue #141 already solved base rate problem

- 3.72× weaker signal in misses (p < 0.0001)
- Dual GEX introduces novel methodology (wrong paper)
- Clean defense > complex defense
**Save for**: Paper #3/4 (intraday analysis)

---

## Issues KEPT (Critical Path)

### ✅ #143: Raw Chain Validation - COMPLETE

**Status**: LaTeX integrated, ready for merge
**Impact**: Definitive defense (92.3% > 61.5%)
**Next**: Merge `paper1-issue143-raw-chain` branch to main

### 🔄 #144: P-Hacking Defense (Inverse P-Hacking) - ⚡ ACCELERATED

**Status**: IN PROGRESS (Chat C)
**Timeline**: 2.5 weeks (accelerated from 4 weeks per MC)
**Impact**: One of 5 core defenses - CRITICAL
**Keep**: MC directive - "Without #144, reviewer can say 'it just flags high variance days'"

**MC's Acceleration Rationale**:

- We ALREADY have the key result (Lift 0.67x, p=0.033)
- No need for 4 weeks of exploration
- Week 1: Finalize data table
- Week 2: Generate histogram (Detection vs Baseline Range)
- Week 3: Write paragraph

**Why Essential**:
> "The Raw Chain (#143) proves the model is smart (it calculates). The Inverse P-Hacking (#144) proves the model is discriminating (it detects suppression, not just noise)."

### ⏳ #159: Publication-Quality Figures (4 Required)

**Status**: NEEDED
**Timeline**: 1-2 weeks (after #144 complete)
**MC's Specification** (4 figures, not 3):

- **Figure 1**: The Divergence (Alpha down, Detection flat)
- **Figure 2**: The Miss Rate (Signal strength - 3.72× weaker, p < 0.0001)
- **Figure 3**: The Raw Chain (Bar chart: 92.3% vs 61.5%)
- **Figure 4**: The Inverse P-Hacking (Density plot - 33% lower range, p=0.033) ← NEW
**Requirement**: ALL must use real data (no synthetic)

### ⏳ #164: Model Upgrade to o4-mini - ⚠️ MC WARNING

**Status**: MINIMAL SCOPE ONLY
**Timeline**: Documentation only (no re-runs)
**MC's Critical Warning**:
> "If you re-run the full 242-day dataset with o4-mini and the detection rate drops to 55% or jumps to 99%, you have created a new problem. You will have to rewrite the entire Results section."

**Approved Scope**:

- ✅ Keep baseline model for 242-day study (o3-mini/o1-preview)
- ✅ Use o4-mini ONLY for Raw Chain (#143) - already complete
- ✅ Document in paper: "For Raw Chain Validation, we utilized o4-mini..."
- ❌ DO NOT re-run full baseline

**Principle**: **Consistency > Novelty**

---

## Paper #1 Comprehensive Defense Framework (Final)

### The 5 Pillars (All Complete or In Progress)

| Issue | Defense | Evidence | Status |
|-------|---------|----------|--------|
| #141 | Sensitivity (not guessing) | 3.72× weaker signal (p < 0.0001) | ✅ COMPLETE |
| #143 | Structural analyst (not calculator) | 92.3% raw > 61.5% GEX (+30.8pp) | ✅ COMPLETE |
| #144 | Pattern-specific (not p-hacking) | 33% lower range (p = 0.03) | 🔄 IN PROGRESS |
| #145 | EOD validity (temporal mechanism) | AUC = 0.681 (p = 0.0075) | ✅ COMPLETE |
| #146 | Mechanism-based (not profit-chasing) | Sharpe 1.8 → 0.1, detection stable | ✅ COMPLETE |

### Supporting Evidence (Already in Paper)

- Granger Causality: p = 0.042 (lag 2)
- Materialization Rate: 91.2% (robust)
- Detection Coverage: 242 days, 95.6% of 2024
- Obfuscation: Complete temporal stripping
- WHO→WHOM→WHAT: Causal framework

---

## MC's Core Guidance Summary

### What Makes Paper #1 Strong

1. **Methodology Focus**: Obfuscation testing is the contribution
2. **Depth > Breadth**: 5 defenses on one asset > shallow coverage of many assets
3. **The Climax**: Issue #143 raw chain (92.3%) is your "mic drop"
4. **Clean Arguments**: Simple defenses beat complex ones

### What Would Weaken Paper #1

1. **Scope Creep**: Adding multi-year, more patterns, individual stocks
2. **Novel Metrics**: Introducing dual GEX, PC/FCI algorithms
3. **Distraction**: Burying Issue #143 with additional complexity
4. **Attack Surface**: More evidence = more opportunities for critique

### The Final Recommendation

> "You just achieved a massive win with Issue #143 (Raw Chain Validation). The LLM detects pattern (71.5%). Critics say 'it's just reading the GEX number.' Defense: We removed the GEX number, gave it raw data, and it got 92.3% accuracy. **Don't step on your own punchline** with unnecessary additions."

---

## Remaining Work (Critical Path Only)

### Must Complete (Critical Path)

1. **Issue #144** (2.5 weeks) ⚡ ACCELERATED
   - **Week 1**: Finalize data table (detection vs baseline range expansion)
   - **Week 2**: Generate Figure 4 histogram (density plot showing LEFT shift)
   - **Week 3**: Write Results paragraph + update Conclusion
   - **Key Result**: 33% lower range expansion (p=0.033) - proves suppression detection

2. **Issue #159** (1-2 weeks)
   - Publication-quality figures (**4 required**, not 3)
   - Figure 4 depends on #144 completion
   - All from real data (no synthetic)
   - 300 DPI minimum, colorblind-friendly

3. **Final Integration** (1 week)
   - Merge Issue #143 branch to main
   - Final proofreading pass
   - Generate submission PDF
   - Supplementary materials package

### Minimal Scope Only

4. **Issue #164** - ⚠️ NO RE-RUNS
   - Document o4-mini use in Raw Chain section only
   - **DO NOT** re-run 242-day baseline (risk of breaking results)
   - Consistency > Novelty

---

## Timeline to Submission (MC-Approved)

### Critical Path (WITH Issue #144 - Required)

- **Week 1-2.5**: Complete #144 (inverse p-hacking defense) ⚡ ACCELERATED
- **Week 3-4**: Generate publication figures (#159) - all 4 figures
- **Week 5**: Final integration, proofreading, submission package
- **Total**: ~5 weeks from today (Nov 26, 2025)

**Target Submission**: End of December 2025 / Early January 2026

### MC's Green Light
>
> "Green Light to execute. 🟢 Prioritize #144 immediately, but time-box it to 2-3 weeks. Do not let it drift. The paper is winning; you just need to cross the finish line."

**MC's Decision**: YES, Issue #144 is worth 2.5 weeks delay

**Rationale**:

- Raw Chain (#143): Proves model calculates constraints from first principles
- Inverse P-Hacking (#144): Proves model discriminates (detects suppression, not noise)
- **Without #144**: Reviewer can say "Maybe it just flags high variance days?"
- **With #144**: Impossible - it flagged QUIETER days (p=0.033 lower range)

**The Two Pillars Must Stand Together**

---

## Success Criteria (Paper #1 Ready)

### Content Complete

- [x] 71.5% detection rate validated
- [x] 91.2% materialization rate verified
- [x] Granger causality (p = 0.042)
- [x] Raw chain superiority (92.3% > 61.5%)
- [x] Sensitivity analysis (3.72×, p < 0.0001)
- [x] EOD validity (AUC = 0.681)
- [x] Profit independence (Sharpe collapsed)
- [ ] Inverse p-hacking (pending #144)

### LaTeX Complete

- [x] Abstract updated (5 defenses)
- [x] Section IV: Methodology Validation (raw chain)
- [x] Conclusion: Twin pillars narrative
- [x] Comprehensive defense framework enumerated
- [ ] Publication figures integrated (pending #159)

### Submission Package

- [ ] Main manuscript PDF
- [ ] Supplementary materials
- [ ] Code repository (GitHub)
- [ ] Data availability statement
- [ ] Author contributions

---

## Closed Issues Log (For Reference)

| Issue | Title | Closed Date | Reason |
|-------|-------|-------------|--------|
| #105 | Causal Discovery | Nov 26, 2025 | Shifts burden, save for Paper #3 |
| #121 | Multi-Year Validation | Nov 26, 2025 | Nice-to-have, not fatal flaw |
| #148 | Expand Pattern Taxonomy | Nov 26, 2025 | Increases p-hacking risk |
| #87 | Individual Equities | Nov 26, 2025 | SPY is optimal test case |
| #142 | Base Rate via Dual GEX | Nov 26, 2025 | #141 already solved this |

**Total Closed**: 5 issues (20-30 weeks of work avoided)

---

## Final Status

**Paper #1 Scope**: LOCKED
**Remaining Work**: #144 (optional), #159 (required), final integration
**Timeline**: 3-7 weeks depending on #144 decision
**Quality**: 4-5 comprehensive defenses, strongest possible validation

**Recommendation**: Focus on depth (completing #144 + #159) rather than breadth (closed issues). The current scope provides sufficient evidence for top-tier journal submission.
