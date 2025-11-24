# Phase 2: Multi-Year Data Collection Plan

**Issue**: #140 (Multi-Year Regime Validation 2020-2025)
**Date**: November 20, 2025
**Owner**: Chat A
**Status**: ✅ Ready to Execute (awaiting approval)

---

## Summary

Collect historical GEX data for 5 years (2021-2025) to expand Paper #2 from 2-year comparison to 6-year evolution study. Dual GEX metrics will be calculated automatically by HistoricalGEXDatabaseBuilder.

**Goal**: Build comprehensive 6-year database (2020-2025) with dual GEX support for regime validation.

---

## Current Database Status

### Coverage by Year

| Year | Existing Days | Expected | Coverage | Dual GEX | Status |
|------|---------------|----------|----------|----------|--------|
| 2020 | 252 | 252 | 100.0% | **0.0%** | ⚠️ Recalculate dual GEX |
| 2021 | 0 | 249 | 0.0% | 0.0% | ❌ Full collection needed |
| 2022 | 0 | 250 | 0.0% | 0.0% | ❌ Full collection needed |
| 2023 | 0 | 250 | 0.0% | 0.0% | ❌ Full collection needed |
| 2024 | 86 | 250 | 34.4% | 0.0% | ⚠️ Fill gaps + dual GEX |
| 2025 | 0 | 230 | 0.0% | 0.0% | ❌ YTD collection needed |
| **TOTAL** | **338** | **1,481** | **22.8%** | **0.0%** | **~1,143 days to collect** |

### Key Findings

1. **2020 Complete** - All 252 trading days exist, but dual GEX not calculated (old data)
2. **2024 Partial** - Only 86/250 days (Q1-Q2 partial coverage)
3. **2021-2023 Missing** - Zero data for transition years
4. **2025 Missing** - No current year data yet

---

## Collection Plan (Broken into Sub-Phases)

**Strategy**: Execute year-by-year for cost monitoring and error recovery

### Phase 2A: 2021 Collection ⏸️ READY

- **Days**: 249 trading days
- **Date Range**: 2021-01-01 to 2021-12-31
- **Status**: 0/249 days (0% existing) - Full collection needed
- **Time**: ~0.4 hours (premium) / ~3.5 hours (standard)
- **Command**: `python scripts/data_collection/phase2_collect_multiyear.py --year 2021`
- **Dependencies**: None (Phase 1 complete)
- **Next**: Phase 2B after verification

### Phase 2B: 2022 Collection ⏸️ PENDING

- **Days**: 250 trading days
- **Date Range**: 2022-01-01 to 2022-12-31
- **Status**: 0/250 days (0% existing) - Full collection needed
- **Time**: ~0.4 hours (premium) / ~3.5 hours (standard)
- **Command**: `python scripts/data_collection/phase2_collect_multiyear.py --year 2022`
- **Dependencies**: Phase 2A complete
- **Next**: Phase 2C after verification

### Phase 2C: 2023 Collection ⏸️ PENDING

- **Days**: 250 trading days
- **Date Range**: 2023-01-01 to 2023-12-31
- **Status**: 0/250 days (0% existing) - Full collection needed (KEY TRANSITION YEAR)
- **Time**: ~0.4 hours (premium) / ~3.5 hours (standard)
- **Command**: `python scripts/data_collection/phase2_collect_multiyear.py --year 2023`
- **Dependencies**: Phase 2B complete
- **Next**: Phase 2D after verification
- **Note**: 2023 is critical for identifying 0DTE proliferation timing

### Phase 2D: 2024 Completion ⏸️ PENDING

- **Days**: ~164 trading days (fill gaps)
- **Date Range**: 2024-01-01 to 2024-12-31
- **Status**: 86/250 days (34% existing) - Need Q3-Q4 + some Q2
- **Time**: ~0.3 hours (premium) / ~2.5 hours (standard)
- **Command**: `python scripts/data_collection/phase2_collect_multiyear.py --year 2024`
- **Dependencies**: Phase 2C complete
- **Next**: Phase 2E after verification

### Phase 2E: 2025 Collection (YTD) ⏸️ PENDING

- **Days**: ~230 trading days
- **Date Range**: 2025-01-01 to 2025-11-20
- **Status**: 0/230 days (0% existing) - Full YTD collection needed
- **Time**: ~0.4 hours (premium) / ~3 hours (standard)
- **Command**: `python scripts/data_collection/phase2_collect_multiyear.py --year 2025 --ytd`
- **Dependencies**: Phase 2D complete
- **Next**: Phase 2F after verification

### Phase 2F: 2020 Dual GEX Recalculation ⏸️ PENDING

- **Days**: 252 trading days
- **Date Range**: 2020-01-01 to 2020-12-31
- **Status**: 252/252 days (100% existing) - Recalculate dual GEX only
- **Time**: ~0.4 hours (premium) / ~3.5 hours (standard)
- **Command**: `python scripts/data_collection/phase2_collect_multiyear.py --year 2020 --rebuild`
- **Dependencies**: Phase 2E complete
- **Method**: Use `--rebuild` flag to recalculate with Issue #138 dual GEX framework
- **Next**: Phase 3 (database verification)

---

## Total Effort Estimate

### With Premium API (1000 calls/min)

- **New Data Collection**: ~1,143 days ÷ 1000/min = **1.9 hours**
- **2020 Recalculation**: 252 days ÷ 1000/min = **0.4 hours**
- **Total Time**: **~2.3 hours**
- **Can complete**: Same day

### With Standard API (75 calls/min)

- **New Data Collection**: ~1,143 days ÷ 75/min = **25.4 hours**
- **2020 Recalculation**: 252 days ÷ 75/min = **5.6 hours**
- **Total Time**: **~31 hours**
- **Spread over**: 5-7 days (rate-limited)

**Note**: Script detected **premium API key** (1000/min), so fast completion is possible.

---

## Execution Strategy

### Year-by-Year Collection (REQUIRED)

Execute sub-phases sequentially for cost monitoring and verification:

```bash
# Phase 2A: 2021
python scripts/data_collection/phase2_collect_multiyear.py --year 2021
# → Verify coverage, monitor cost, check dual GEX population

# Phase 2B: 2022 (after 2A verified)
python scripts/data_collection/phase2_collect_multiyear.py --year 2022
# → Verify coverage, monitor cost, check dual GEX population

# Phase 2C: 2023 (after 2B verified)
python scripts/data_collection/phase2_collect_multiyear.py --year 2023
# → Verify coverage, monitor cost, check dual GEX population

# Phase 2D: 2024 (after 2C verified)
python scripts/data_collection/phase2_collect_multiyear.py --year 2024
# → Verify coverage, monitor cost, check dual GEX population

# Phase 2E: 2025 YTD (after 2D verified)
python scripts/data_collection/phase2_collect_multiyear.py --year 2025 --ytd
# → Verify coverage, monitor cost, check dual GEX population

# Phase 2F: 2020 recalc (after 2E verified)
python scripts/data_collection/phase2_collect_multiyear.py --year 2020 --rebuild
# → Verify 100% dual GEX population for 2020
```

### Verification After Each Sub-Phase

After each year completes, verify before proceeding:

```bash
# Check coverage and dual GEX for completed year
python -c "
import sqlite3
conn = sqlite3.connect('.cache/consolidated_historical.db')
cursor = conn.cursor()

year = 2021  # Replace with completed year

cursor.execute('''
    SELECT
        COUNT(*) as total,
        COUNT(gex_oi) as dual_gex,
        AVG(data_quality_score) as avg_quality
    FROM daily_gex_metrics
    WHERE date LIKE ?
''', (f'{year}%',))

total, dual_gex, avg_quality = cursor.fetchone()
dual_pct = (dual_gex/total*100) if total > 0 else 0

print(f'{year}: {total} days, {dual_pct:.1f}% dual GEX, {avg_quality:.0f} quality')
conn.close()
"
```

**Expected**: `YYYY: 249-252 days, 100.0% dual GEX, 100 quality`

### Batch All Years (NOT RECOMMENDED)

The `--all` flag exists but is **NOT recommended** for this project due to:

- Need to monitor API costs between years
- Better error recovery with year-by-year
- Can verify data quality incrementally

---

## Success Criteria

### Phase Completion Checklist

- [x] **Phase 1** complete (schema fixed, builder ready)
- [ ] **Phase 2A** (2021): ≥95% coverage (≥237/249 days), 100% dual GEX
- [ ] **Phase 2B** (2022): ≥95% coverage (≥238/250 days), 100% dual GEX
- [ ] **Phase 2C** (2023): ≥95% coverage (≥238/250 days), 100% dual GEX
- [ ] **Phase 2D** (2024): ≥95% coverage (≥238/250 days), 100% dual GEX
- [ ] **Phase 2E** (2025): ≥95% coverage (≥219/230 days YTD), 100% dual GEX
- [ ] **Phase 2F** (2020): 100% dual GEX recalculated (252/252 days)

### Data Quality Requirements (Per Year)

Each sub-phase must achieve:

- ✅ Coverage: ≥95% of expected trading days
- ✅ Dual GEX: 100% of collected days have gex_oi, gex_volume populated
- ✅ Quality Score: Average ≥90 (ideally 100)
- ✅ Economic Regime: 100% of collected days classified (high_conviction, low_conviction, mixed)

### Overall Target

**Target**: ≥1,408 total days with dual GEX metrics (95% of 1,481 expected days across 6 years)

---

## Risks and Mitigations

### Risk 1: API Rate Limiting

- **Impact**: Collection takes longer than estimated
- **Mitigation**: Script has built-in rate limiting (70 calls/min conservative)
- **Fallback**: Can pause/resume using year-by-year approach

### Risk 2: Data Gaps (Weekends/Holidays)

- **Impact**: Fewer trading days than expected
- **Mitigation**: Using pandas business day calendar with US federal holidays
- **Expected**: Minor variance (±2-3 days per year)

### Risk 3: API Failures

- **Impact**: Collection stops mid-year
- **Mitigation**: Script skips already-collected dates, can resume
- **Recovery**: Rerun same year with `--year YYYY` flag

### Risk 4: Database Corruption

- **Impact**: Lose work if database corrupted during collection
- **Mitigation**: Automatic backup created before rebuild operations
- **Recovery**: Restore from `.cache/backups/consolidated_historical_backup_*.db`

---

## Quality Verification

After collection completes, verify data quality:

```bash
# Check coverage and dual GEX population
python -c "
import sqlite3
conn = sqlite3.connect('.cache/consolidated_historical.db')
cursor = conn.cursor()

for year in [2020, 2021, 2022, 2023, 2024, 2025]:
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            COUNT(gex_oi) as dual_gex,
            AVG(data_quality_score) as avg_quality
        FROM daily_gex_metrics
        WHERE date LIKE ?
    ''', (f'{year}%',))

    total, dual_gex, avg_quality = cursor.fetchone()
    dual_pct = (dual_gex/total*100) if total > 0 else 0

    print(f'{year}: {total} days, {dual_pct:.1f}% dual GEX, {avg_quality:.0f} quality')

conn.close()
"
```

**Expected Output**:

```
2020: 252 days, 100.0% dual GEX, 100 quality
2021: 249 days, 100.0% dual GEX, 100 quality
2022: 250 days, 100.0% dual GEX, 100 quality
2023: 250 days, 100.0% dual GEX, 100 quality
2024: 250 days, 100.0% dual GEX, 100 quality
2025: 230 days, 100.0% dual GEX, 100 quality
```

---

## Next Steps After Phase 2

Once Phase 2 completes:

**Phase 3**: Database Verification (30 minutes)

- Verify 6-year continuity
- Check for data gaps
- Validate dual GEX ranges

**Phase 4A**: Single GEX Validation (~$37 cost)

- Generate ~892 regime windows (4 new years × 223 windows/year)
- Run batch validation with o4-mini
- Compare detection rates across years

**Phase 4B**: Dual GEX Validation (~$37 cost)

- Same 892 windows
- Test GEX_OI vs GEX_Volume discrimination
- Identify high vs low conviction regimes

**Phase 5**: Analysis & Paper Writing (1-2 weeks)

- Temporal trend analysis
- 0DTE transition timing
- Election cycle comparison
- LaTeX draft updates

---

## Files Created

- **Collection Script**: `scripts/data_collection/phase2_collect_multiyear.py`
- **This Plan**: `docs/papers/paper2/infrastructure/phase2_collection_plan.md`

---

## Status

**Phase 1**: ✅ Complete (schema fixed, builder ready)
**Phase 2**: ⏸️ **AWAITING APPROVAL** to begin collection
**Estimated Completion**: Same day (with premium API) or 5-7 days (with standard API)

**Approval Needed**: User confirmation to proceed with ~2-31 hours of data collection.
