# Paper #2 Session Logs

Development history for Paper #2 regime detection methodology.

---

## Current Work (30-Day Regime Detection)

**Status**: Week 1 implementation (November 5, 2025)

### s05: Strategic Pivot to 30-Day Regimes

**Date**: November 5, 2025
**Focus**: Pivot from 5-day trajectories to 30-day regime windows

**Critical Discovery**:
- 5-day approach: 98.4% detection (2020) vs 100% (Q1 2024)
- Finding: Detects universal daily hedging (trivial), not distinctive regimes (interesting)
- Decision: Pivot to 30-day regime windows (expected 30-50% detection)

**Implementation (Week 1)**:
- ✅ RegimeClassifier module (332 lines)
- ✅ SequentialGEXFetcher updated (window_size=30 parameter)
- ✅ Regime detection prompt v1
- ✅ GitHub issues #89, #107 updated
- ⏸️ Validation script integration (in progress)
- ⏸️ Phase 1: Q1 2024 validation (~32 windows expected)

**Files Created**:
- `src/validation/regime_classifier.py`
- `docs/papers/paper2/prompts/regime_detection_v1.md`
- `docs/papers/paper2/methodology/regime_windows_design.md`

**Related Issues**: #89 (30-day methodology), #107 (validation strategy), #111 (Test 4 led to pivot)

---

## Archived Work (5-Day Sequential Approach)

**Status**: Abandoned November 5, 2025 - Moved to `archive_5day/`

### Why 5-Day Approach Was Abandoned

**Test 4 Result** (November 5, 2025):
- 2020 (weak GEX, avg $2.85B): 98.4% detection (253/257 windows)
- Q1 2024 (strong GEX, avg $13.95B): 100% detection (61/61 windows)
- **Delta**: Only 1.6 percentage points despite 79% lower GEX

**Interpretation**: 5-day windows detect universal daily hedging (always present, known since Black-Scholes 1973) rather than distinctive regime patterns (sometimes present, interesting research).

**Strategic Decision**: Pivot to 30-day regime windows to detect persistent structural constraints with meaningful selectivity (30-50% expected detection).

### Archived Sessions (5-Day Work)

Located in `archive_5day/`:

1. **s01**: Implementation & Bug Fixes (Nov 3-4)
   - Built SequentialGEXFetcher (5-day version)
   - Fixed 3 critical bugs (config, methods, field names)
   - Result: 120 windows validated

2. **s02**: Phase 1 Completion (Nov 4)
   - Proof-of-concept successful (100% detection)
   - Negative controls framework designed
   - Phase 1 declared complete

3. **s03**: Prompt Evolution & Decision (Nov 4)
   - Tested 4 prompt versions (v1-v3b)
   - v3a selected (mechanical confidence guidance)
   - Key finding: 60% reduction in false positives vs qualitative guidance

4. **s04**: Test 4 Requirement (Nov 4)
   - Identified 100% detection concern
   - Designed Test 4 (low-GEX negative control)
   - Blocked Phase 2 pending Test 4

**Total Work**: 4 sessions, Oct 31 - Nov 4, 2025

**Value Retained**:
- Infrastructure (SequentialGEXFetcher, prompt builder methods)
- 2020 historical data (reusable for 30-day validation)
- Negative controls principles (mechanical confidence guidance)
- Methodology rigor lessons

---

## Documentation Structure

### Active (30-Day Regimes)

```
docs/papers/paper2/
├── methodology/
│   ├── regime_windows_design.md (30-day framework)
│   └── negative_controls_design.md (updated with Test 4)
├── prompts/
│   └── regime_detection_v1.md (30-day prompt)
└── validation/
    ├── negative_controls_archive.md (5-day Tests 1-4 summary)
    └── test4/ (4 comprehensive docs on 5-day pivot discovery)
```

### Archived (5-Day Approach)

```
docs/papers/paper2/sessions/archive_5day/
├── s01-implementation-bugfixes.md
├── s02-phase1-completion.md
├── s03-prompt-evolution.md
└── s04-test4-requirement.md
```

---

## Quick Reference

**Understanding the pivot**: See Test 4 docs (`../validation/test4/`)

**30-day methodology**: See `../methodology/regime_windows_design.md`

**Current implementation status**: Check `.claude/sync.yaml` or Issues #89/#107

---

## Timeline

**Oct 31 - Nov 4, 2025**: 5-day sequential approach (4 sessions)
- Implementation, debugging, proof-of-concept, negative controls
- Result: 98-100% detection across all conditions (too universal)

**Nov 5, 2025**: Strategic pivot
- Test 4 completed, findings analyzed
- Decision: 30-day regime windows
- Week 1: Core components implemented

**Nov 11-15, 2025** (planned): Phase 1 validation
- Q1 2024: ~32 windows, expect 1-2 detections (60-80% LLM accuracy)
- Go/no-go decision for Phase 2

---

**Last Updated**: November 5, 2025 (Post-pivot, Week 1)
