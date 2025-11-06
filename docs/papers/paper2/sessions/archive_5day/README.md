# Archived: 5-Day Sequential Approach Session Logs

**Archived**: November 5, 2025
**Reason**: 5-day approach abandoned, pivoted to 30-day regime windows

---

## What's Here

4 session logs documenting the 5-day sequential GEX trajectory analysis work (Oct 31 - Nov 4, 2025).

### Sessions

1. **s01-implementation-bugfixes.md** (Nov 3-4)
   - Implementation of SequentialGEXFetcher (5-day version)
   - Fixed 3 critical bugs
   - 120 windows validated successfully

2. **s02-phase1-completion.md** (Nov 4)
   - Proof-of-concept results (100% detection)
   - Negative controls framework design
   - Phase 1 completion declaration

3. **s03-prompt-evolution.md** (Nov 4)
   - Tested 4 prompt iterations (v1-v3b)
   - Selected v3a (mechanical confidence guidance)
   - Key finding: 60% FP reduction with mechanical guidance

4. **s04-test4-requirement.md** (Nov 4)
   - Identified 100% detection concern
   - Designed Test 4 (low-GEX negative control)
   - Blocked Phase 2 pending Test 4 results

---

## Why Abandoned

**Test 4 Discovery** (November 5, 2025):
- 5-day detection: 98.4% (2020 weak GEX) vs 100% (2024 strong GEX)
- **Finding**: Detects universal daily hedging (trivial), not distinctive regimes (interesting)
- **Decision**: Pivot to 30-day regime windows for meaningful selectivity (30-50% expected)

---

## What Was Learned

**Infrastructure Built** (reusable):
- SequentialGEXFetcher (adapted for 30-day windows)
- MechanicsPromptBuilder sequential methods
- Validation script patterns

**Methodology Insights** (valuable):
- Mechanical confidence guidance reduces FP by 60%
- Need for negative controls at multiple levels
- Window size critical for detecting regimes vs flows

**Data Created** (reusable):
- 2020 historical GEX data (252 days, $2.85B avg)
- Available for 30-day regime comparison

---

## Current Work

See parent `README.md` for 30-day regime detection work (Session 05+).

**Active Documentation**:
- `docs/papers/paper2/methodology/regime_windows_design.md`
- `docs/papers/paper2/validation/test4/` (explains pivot)
- `docs/papers/paper2/prompts/regime_detection_v1.md`

---

**Archived**: November 5, 2025
**Total**: 4 sessions, 5 days of work, valuable negative result
