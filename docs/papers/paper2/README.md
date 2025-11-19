# Paper #2: 30-Day Regime Windows - LLM Detection of Persistent Dealer Gamma Constraints

**Status**: Phase 1 Complete, Phase 2 Pending  
**Date**: November 6, 2025  
**Branch**: paper2-sequential-gex

---

## Navigation Guide

**START HERE**:

1. **[PHASE1_DOCUMENTATION_INDEX.md](PHASE1_DOCUMENTATION_INDEX.md)** - Master reader's guide
2. Choose Quick Start, Standard Review, or Deep Dive path

**QUICK REFERENCE**:

- [00_PHASE1_QUICK_SUMMARY.md](validation/00_PHASE1_QUICK_SUMMARY.md) - 5 minute overview
- [03_DETECTION_RATE_TL_DR.md](validation/03_DETECTION_RATE_TL_DR.md) - 1 page on detection rate

---

## Phase 1 Results Summary

| Metric | Value | Status |
|--------|-------|--------|
| Windows Tested | 52 (Q1 2024) | Jan 2 - Mar 27 |
| Detection Rate | 67.3% (35/52) | ⚠️ Higher than 30-50% target |
| Selectivity Gap | 39 percentage points | ✅ Excellent (96% vs 57%) |
| Confidence (Detected) | 93.0 avg | ✅ Excellent |
| Confidence (Rejected) | 39.5 avg | ✅ Good separation |

**Status**: ✅ Conditional Pass - Framework works well, proceed to Phase 2 after JSON fixes

---

## Key Documents

1. **[02_PHASE1_RESULTS_ANALYSIS.md](validation/02_PHASE1_RESULTS_ANALYSIS.md)** - Detailed statistics
2. **[00_DETECTION_RATE_FRAMEWORK.md](methodology/00_DETECTION_RATE_FRAMEWORK.md)** - Why 30-50% is the target
3. **[04_DETECTION_RATE_Q1_VS_2024.md](validation/04_DETECTION_RATE_Q1_VS_2024.md)** - Why Q1 67% ≠ contradiction
4. **[regime_windows_design.md](methodology/regime_windows_design.md)** - Original methodology
5. **[validation_phases.md](validation/validation_phases.md)** - Phases 1-4 roadmap

---

## Quick Start

- **5 minutes**: Read 00_PHASE1_QUICK_SUMMARY.md + 03_DETECTION_RATE_TL_DR.md
- **20 minutes**: Follow Standard Review in PHASE1_DOCUMENTATION_INDEX.md
- **45 minutes**: Follow Deep Dive in PHASE1_DOCUMENTATION_INDEX.md

---

## Why 30-50% Matters

**30-50% detection = Selective detection** (distinctive regimes)  
**NOT 98% detection** (universal daily hedging)

- Can distinguish 2020 (25%) from 2024 (45%)
- Can test 0DTE hypothesis
- Paper is publishable

---

## Next Steps

1. **Fix JSON errors** (6 windows, 11.5%) - 30 min code + 1 hour rerun
2. **Spot-check obfuscation** - 5 minutes
3. **Phase 2 negative controls** - 1 hour
4. **Phase 3 full 2024** - 1-2 hours

---

Last Updated: November 6, 2025, 23:45 UTC
