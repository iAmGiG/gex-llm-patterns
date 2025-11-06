# Negative Controls Archive - Paper #2 (5-Day Approach)

**Status**: Scripts archived to `deprecated/negative_controls_5day/` (November 5, 2025)
**Location**: Moved from `scripts/validation/negative_controls/` to documentation folder

## What Was Here

This folder contained 5 scripts for validating the **5-day sequential GEX approach** (October-November 2025):

1. `validate_p2_negative_controls.py` - Tests 1-3 (prompt comparison, synthetic, zero-GEX)
2. `fetch_2020_options.py` - Test 4 data prep step 1
3. `process_2020_gex_simple.py` - Test 4 data prep step 2
4. `export_db_to_cache_v2.py` - Test 4 data prep step 3
5. `build_2019_2020_test4.py` - Deprecated (builder bugs)

## Why Moved to Deprecated

**5-day approach abandoned** (November 5, 2025):
- Test 4 result: 98.4% detection on 2020 weak GEX vs 100% on 2024 strong GEX
- Finding: 5-day windows detect universal daily hedging (trivial), not distinctive regimes (interesting)
- Strategic pivot: 30-day regime windows (expected 30-50% detection)

**Scripts were one-time data prep**, not ongoing methodology:
- Test 4 complete, findings documented
- 2020 data preserved in `.cache/` and database
- Scripts not needed for 30-day regime validation

## What Remains

**Test 4 Documentation** (comprehensive, 4 files):
- `docs/papers/paper2/validation/test4/test4_1_executive_summary.md`
- `docs/papers/paper2/validation/test4/test4_2_methodology.md`
- `docs/papers/paper2/validation/test4/test4_3_results_analysis.md`
- `docs/papers/paper2/validation/test4/test4_4_technical_appendix.md`

**2020 Historical Data** (reusable for 30-day validation):
- Database: `.cache/consolidated_historical.db` (252 days)
- Cache: `.cache/gex_data/SPY/2020-*/` (252 directories)
- Stats: Avg $2.85B GEX (11% of 2024's $25.83B)

**Negative Controls Design**:
- `docs/papers/paper2/methodology/negative_controls_design.md`

## For 30-Day Regime Validation

**New scripts needed** (to be created):
- `validate_regime_negative_controls.py` - Tests 1-3 for 30-day regimes
- Main regime validation script (in progress)

**Reusable**:
- 2020 data in cache (already available)
- v3a neutral prompt principles (mechanical confidence guidance)
- Test 4 findings (informed 30-day pivot)

## Scripts Location

**If you need the original scripts**:
- Location: `deprecated/negative_controls_5day/`
- Status: Not tracked in git (in `.gitignore`)
- Purpose: Archive of 5-day validation work

**Note**: Scripts are operational tools, not research methodology. The methodology and findings are documented in the `docs/` folder.

---

## Quick Reference

**What Test 4 proved**: 5-day approach too sensitive (98-100% detection = detects everything)

**Strategic decision**: Pivot to 30-day regime windows for selectivity (30-50% detection target)

**Data available**: 2020 and 2024 historical GEX in cache, ready for 30-day validation

**GitHub Issues**:
- #111: Test 4 Complete (CLOSED - led to pivot)
- #89: 30-Day Regime Detection (ACTIVE - new methodology)
- #107: Validation Strategy (ACTIVE - 30-day phases)

---

**Last Updated**: November 5, 2025 (Scripts moved to deprecated, folder repurposed for 30-day regime validation)
