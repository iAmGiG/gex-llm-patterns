# Paper #2: Multi-Year Expansion Roadmap (Issue #140)

**Created**: November 20, 2025
**Scope**: Expand from 2-year comparison (2020, 2024) → 6-year evolution (2020-2025)
**Timeline**: ~4 weeks (Dec 18, 2025 target)
**Cost**: ~$90 total ($43 validation + $47 already spent on Phases 1-4)

---

## Overview

**Current Status**: 2020 vs 2024 baseline complete (69.1pp discrimination, p < 0.0001)

**Goal**: Identify when 0DTE proliferation drove regime persistence increase

**Key Questions**:

1. When did transition occur? 2021? 2022 (SPX 0DTE launch)? Gradual?
2. Is shift sustained into 2025, or reverting?
3. Does dual GEX (OI vs Volume) provide additional insights?
4. Do election cycles (2020, 2024) show distinctive patterns?

---

## Phase Status

### ✅ Phase 0: 2020 vs 2024 Baseline (COMPLETE)

- Detection: 2024 (81.2%) vs 2020 (12.1%) = 69.1pp difference
- Cost: $13.60 (Batch API)
- Limitation: Phase 2a shuffle test (61% FP on Q1 2024)

---

### ✅ Phase 1: Infrastructure Upgrades (2 days) - COMPLETE

**Owner**: Chat A
**Completed**: November 20, 2025

**Tasks**:

- [x] 1A: Modify HistoricalGEXDatabaseBuilder to use consolidated_historical.db
- [x] 1B: Add dual GEX support (calculate_dual_gex integration) - **SCHEMA BUG FIXED**
- [x] 1C: Test with 2020 data (backward compatibility) - **RESUME LOGIC FIXED**

**Success Criteria**: ✅ ALL MET

- Builder writes to consolidated_historical.db
- Dual GEX columns populated (gex_oi, gex_volume, activity_ratio, economic_regime)
- 2020 data rebuilds successfully with dual GEX

**Files Modified**:

- src/data_sources/historical_gex_builder.py:344-347 (schema fix)
- src/data_sources/historical_gex_builder.py:991-1000 (resume logic fix)

**Documentation**: docs/papers/paper2/infrastructure/phase1_upgrades_complete.md

---

### ✅ Phase 2: Multi-Year Data Collection (5-7 days) - COMPLETE

**Owner**: Chat A
**Completed**: November 20, 2025

**Data Requirements**: ✅ ALL COLLECTED
| Year | Days | Status | Notes |
|------|------|--------|-------|
| 2020 | 252 | ✅ COMPLETE | Recalculated with dual GEX |
| 2021 | 250 | ✅ COMPLETE | +2 Columbus/Veterans Day |
| 2022 | 251 | ✅ COMPLETE | +2 Columbus/Veterans Day |
| 2023 | 250 | ✅ COMPLETE | +2 Columbus/Veterans Day |
| 2024 | 251 | ✅ COMPLETE | +2 Columbus/Veterans Day |
| 2025 | 221 | ✅ COMPLETE | Through Nov 20, 2025 |
| **TOTAL** | **1,475** | ✅ | 99.9% dual GEX coverage |

**Collection Strategy**: Sequential (SQLite single-writer constraint)

**Timeline**: ~45 minutes actual (sequential + gap fixes)
**Cost**: $0 (Premium Alpha Vantage API)

**Success Criteria**: ✅ ALL MET

- All 6 years collected (1,475 trading days)
- Dual GEX populated for 1,473 days (99.9%)
- Columbus/Veterans Day gaps filled (8 dates)
- Data quality: 100/100 all dates

**Documentation**: docs/papers/paper2/infrastructure/phase2_3_collection_summary.md

---

### ✅ Phase 3: Database Verification (1 day) - COMPLETE

**Owner**: Chat A
**Completed**: November 20, 2025

**Checks**: ✅ ALL PASSED

- [x] Coverage: All expected trading days present (2020-2025) - 1,475 days
- [x] Gaps: Columbus/Veterans Day gaps identified and filled (8 dates)
- [x] Dual GEX: gex_oi, gex_volume, activity_ratio, economic_regime populated (99.9%)
- [x] Magnitudes: All GEX values reasonable (Quality 100/100)
- [x] Continuity: 2024 matches existing Phase 3 data perfectly

**Verification Scripts**:

- /tmp/check_missing_dates.py (gap detection)
- SQL queries for coverage verification

**Success Criteria**: ✅ ALL MET

- 100% coverage for 2020-2025 NYSE trading days
- Dual GEX populated for 1,473/1,475 days (99.9%)
- Quality score: 100/100 for all years
- Economic regimes properly classified (4 categories)

**Documentation**: docs/papers/paper2/infrastructure/phase2_3_collection_summary.md

---

### 📅 Phase 4A: Single GEX Validation (3-4 days)

**Owner**: Chat A

**Scope**: Traditional GEX_OI methodology (comparable to 2020/2024 baseline)

**Windows to Validate**:
| Year | Windows | Cost |
|------|---------|------|
| 2021 | ~223 | $11 |
| 2022 | ~223 | $11 |
| 2023 | ~223 | $11 |
| 2025 | ~210 | $10 |
| **TOTAL** | ~879 | $43 |

**Method**:

- Same regime detection prompt used in Phases 1-4
- Batch API (50% cost savings)
- o4-mini model (consistency with baseline)

**Expected Results**:
| Year | Detection % | Hypothesis |
|------|-------------|------------|
| 2021 | 15-25% | Early 0DTE growth |
| 2022 | 30-50% | SPX 0DTE launch impact |
| 2023 | 60-75% | 0DTE volume expansion |
| 2025 | 75-85% | Sustained persistence |

**Timeline**: 1-2 hours submission, 2-4 hours Batch API processing

**Success Criteria**:

- All 4 years validated with o4-mini
- Results comparable to 2020/2024 baseline
- Clear temporal trend visible

---

### 📅 Phase 4B: Dual GEX Validation (3-4 days) - OPTIONAL

**Owner**: Chat A

**Scope**: Novel dual GEX analysis (GEX_OI vs GEX_Volume divergence)

**Additional Criteria**:

- **High-conviction regime**: OI and Volume agree (activity_ratio > 0.70)
- **Low-conviction regime**: OI dominates, Volume weak (activity_ratio < 0.70)
- **Mixed signal**: OI positive, Volume negative (transitional warning)

**Windows**: Same ~879 windows as Phase 4A
**Cost**: $43 (separate batch submission)

**Research Question**: Does dual GEX provide leading indicators of regime transitions?

**Success Criteria**:

- All 4 years validated with dual GEX criteria
- Activity ratio calculated for all windows
- Divergence patterns identified

**Decision Point**: Run only if time/budget permits, or defer to future work

---

### 📅 Phase 5: Analysis & Writing (2 weeks)

**Owner**: Chat A (analysis), Chat B (writing)

#### 5A: Temporal Trend Analysis (3-4 days)

**Deliverable**: Regime persistence evolution chart (2020→2025)

**Analysis**:

- Detection rate by year (6 data points)
- Average GEX magnitude by year
- Persistence % (same-sign dominance) by year
- Flip rate stability by year

**Output**: Markdown summary + figure for Paper #2

---

#### 5B: 0DTE Transition Timing (2-3 days)

**Deliverable**: Identification of regime shift period

**Analysis**:

- Quarter-by-quarter detection rates (2020 Q1 → 2025 Q4)
- Correlation with 0DTE volume data (external dataset)
- Statistical test: Before vs After 0DTE launch (May 2022)

**Hypothesis Tests**:

- H1: 2022 Q2/Q3 shows sharp increase (0DTE launch effect)
- H2: 2020-2021 low, 2023-2025 high (binary shift)
- H3: Gradual linear trend 2020→2025 (continuous growth)

**Output**: Statistical summary for Discussion section

---

#### 5C: Dual GEX Divergence Analysis (2-3 days) - IF PHASE 4B DONE

**Deliverable**: Regime quality insights

**Analysis**:

- High-conviction vs low-conviction regime frequency by year
- Divergence events (OI ≠ Volume) and subsequent regime changes
- Activity ratio as leading indicator

**Output**: Dual GEX contribution for Discussion/Future Work

---

#### 5D: Election Cycle Analysis (1-2 days)

**Deliverable**: Election year comparison (2020 vs 2024)

**Analysis**:

- GEX behavior Q3-Q4 2020 vs Q3-Q4 2024
- Volatility regimes during election periods
- Persistence differences (if any)

**Output**: Brief section for Discussion or Future Work

---

#### 5E: Paper #2 Draft (1 week)

**Owner**: Chat B (with Chat A data)

**Sections to Update**:

1. **Introduction**: Change "2-year comparison" → "6-year evolution"
2. **Methodology**: Add multi-year data collection details
3. **Results**: Replace 2020 vs 2024 → Full 6-year temporal analysis
4. **Discussion**: 0DTE transition timing, dual GEX insights, limitations
5. **Conclusion**: Strengthen causal attribution claims

**Target Length**: 10-12 pages IEEE format

**Figures Needed** (Chat A will generate):

- Figure 1: Temporal trend (detection rate 2020→2025)
- Figure 2: GEX magnitude evolution
- Figure 3: 0DTE volume overlay (external data)
- Figure 4: Dual GEX divergence patterns (if Phase 4B done)

---

## Success Criteria (Issue #140)

- [ ] All 6 years in database (2020-2025, ~1,500 days)
- [ ] Dual GEX populated for all years
- [ ] Single GEX validation complete (~879 new windows)
- [ ] Temporal trend identified (detection % by year)
- [ ] 0DTE transition timing quantified (statistical test)
- [ ] Paper #2 draft complete (10-12 pages)

---

## Risk Mitigation

**Risk 1**: Data collection hits API rate limits

- **Mitigation**: Spread over 5-7 days, use caching aggressively

**Risk 2**: Dual GEX analysis shows no signal

- **Mitigation**: Phase 4B is optional, single GEX sufficient for paper

**Risk 3**: No clear transition point (gradual trend)

- **Mitigation**: Report as gradual evolution, still strengthens causal claim

**Risk 4**: 2025 data shows regime reversal (detection drops)

- **Mitigation**: Document as regime instability, still interesting finding

---

## Coordination

**Chat A Responsibilities**:

- All infrastructure (Phases 1-3)
- All validation (Phases 4A-4B)
- All analysis (Phases 5A-5D)
- Figure generation for Paper #2

**Chat B Responsibilities**:

- Documentation updates (this roadmap)
- GitHub issue tracking
- Paper #2 LaTeX writing (Phase 5E)
- Literature review updates if needed

**Communication**:

- Update sync.yaml after each phase completion
- Flag any blockers immediately
- Share interim findings in Issue #140 comments

---

## Timeline

**Week 1 (Nov 20-26)**:

- Phase 1: Infrastructure upgrades
- Phase 2 start: 2021 data collection

**Week 2 (Nov 27-Dec 3)**:

- Phase 2: Complete 2022, 2023, 2025 collection
- Phase 3: Database verification

**Week 3 (Dec 4-10)**:

- Phase 4A: Single GEX validation (~879 windows)
- Phase 5A-B start: Initial analysis

**Week 4 (Dec 11-18)**:

- Phase 5A-E: Complete analysis and writing
- Paper #2 draft ready

**Target**: December 18, 2025 (Paper #2 draft complete)

---

## Files

**Issue**: #140
**Roadmap**: docs/papers/paper2/planning/issue140_multiyear_roadmap.md (this file)
**Sync**: .claude/sync.yaml (coordination)
**Results**: reports/validation/paper2_regime_windows/ (Phases 4A-4B)
