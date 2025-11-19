# Paper #2 Roadmap: GitHub Issues & Documentation Map

**Last Updated**: November 19, 2025

**Purpose**: Single source of truth mapping all Paper #2 GitHub issues to their current status, dependencies, and related documentation.

---

## Quick Status

| Category | Count | Status |
|----------|-------|--------|
| **In Progress** | 4 | Phase 2 execution pending |
| **Completed** | 6 | Infrastructure ready |
| **Future Work** | 4 | Backlog (after Phase 3/4) |
| **Total Issues** | 14 | All Paper #2 work |

**Current Phase**: Phase 2 (Negative Controls) - Ready to Execute
**Blocker**: None - All infrastructure complete, awaiting Phase 2 batch submission

---

## Active Issues (In Progress)

### #89: 30-Day Regime Detection Framework
**Status**: ✅ Infrastructure COMPLETE, 📅 Validation In Progress (Phase 1 done)

**Research Question**: Can LLMs detect persistent market regimes from 30-day GEX sequences?

**Pivot Context** (November 5, 2025):
- **FROM**: 5-day trajectory analysis (98-100% detection - too universal)
- **TO**: 30-day regime persistence (30-50% target - selective)
- **Why**: 5-day detects universal daily hedging (trivial), not persistent regimes (meaningful)

**Regime Criteria**:
- ≥70% persistence (same sign dominance)
- ≥$5B average magnitude
- ≤5 sign flips over 30 days

**Related Docs**:
- `methodology/regime_windows_design.md` - Design rationale
- `validation/validation_phases.md` - 4-phase validation strategy
- `prompts/regime_detection_v1.md` - LLM prompt

**Dependencies**: None (foundation issue)

**Next Step**: Phase 2 execution (negative controls)

---

### #107: Validation Strategy (4-Phase Framework)
**Status**: ✅ Phase 1 COMPLETE (71.2% detection), 📅 Phase 2 Pending

**Phase Breakdown**:

| Phase | Purpose | Windows | Status | Detection Target |
|-------|---------|---------|--------|------------------|
| **Phase 1** | Q1 2024 baseline | 52 | ✅ **COMPLETE** | 71.2% (borderline) |
| **Phase 2** | Negative controls | 30 | 📅 **PENDING** | <10% FP target |
| **Phase 3** | Full 2024 validation | 223 | 🔮 **PLANNED** | 30-50% target |
| **Phase 4** | 2020 comparison | 223 | 🔮 **PLANNED** | 0DTE hypothesis |

**Phase 1 Results** (November 19, 2025):
- **Detection**: 71.2% (37/52 windows) - Higher than 30-50% target
- **Selectivity Metrics**:
  - Persistence gap: 39 percentage points (96% vs 57%)
  - Confidence gap: 53.5 points (93.0 vs 39.5)
  - Magnitude gap: $6.84B ($11.66B vs $4.82B)
- **Decision**: ✅ **Proceed to Phase 2** (framework IS selective)

**Phase 2 Design** (3 negative control tests):
1. **Shuffle** (Phase 2a): Randomize GEX day order → expect 0% detection
2. **Transitional** (Phase 2b): Filter for 7-10 sign flip windows → expect 0-10% detection
3. **Low-Magnitude** (Phase 2c): Scale GEX down 75% → expect 0-10% detection

**Related Docs**:
- `validation/validation_phases.md` - Complete 4-phase roadmap
- `3_phase1_results/02_results.md` - Phase 1 detailed analysis
- `4_phase2_execution/` - Phase 2 execution docs (to be created)
- `PHASE2_IMPLEMENTATION_SUMMARY.md` - Technical workflow

**Dependencies**:
- Blocks: #138 (Phase 1.5), Phase 3, Phase 4
- Depends on: #112 (Batch API - COMPLETE)

**Next Step**: Execute Phase 2 batch jobs (~$0.50, ~2 hours)

---

### #138: Dual GEX Framework (OI vs Volume)
**Status**: 📅 **PLANNED** (Phase 1.5 Extension)

**Research Question**: Why does profitability vary when detection remains constant?

**Motivation**: Paper #1 showed:
- Q1 2024: 100% detection, +21bp alpha (profitable)
- Q4 2024: 100% detection, -1bp alpha (unprofitable)
- **Question**: What changed?

**Answer**: GEX_OI (open interest) vs GEX_VOL (volume) split
- **GEX_OI**: Structural positioning (dealers HAVE exposure)
- **GEX_VOL**: Economic activity (dealers ARE hedging)

**Four Regime Framework**:
1. **HIGH_FRAGILITY**: GEX_OI negative + GEX_VOL near zero (Q4 2024)
   - Dealers have exposure but aren't hedging much
   - Low profitability despite detection
2. **ELEVATED_RISK**: GEX_OI negative + GEX_VOL negative (Q1 2024)
   - Dealers hedging aggressively
   - High profitability
3. **STABLE_POSITIVE**: Both positive (low volatility)
4. **TRANSITIONAL**: Mixed signals

**Potential Impact on Phase 2c**:
- Low-magnitude test scales total GEX down 75%
- Question: Does this create HIGH_FRAGILITY regime artificially?
- May need separate OI/VOL scaling tests

**Related Docs**:
- `5_extensions/01_dual_gex_oi_volume.md` - Design doc (to be created)
- Issue #74 (OI-to-Volume infrastructure) - Foundation work

**Dependencies**:
- Depends on: Phase 3 completion (need full year data)
- Blocks: Paper #3 (sector rotation)

**Timeline**: Phase 1.5 (after Phase 3, before Phase 4)

---

### #74: OI-to-Volume Pattern Detection Infrastructure
**Status**: 🔄 **IN PROGRESS** (Foundation for #138)

**Purpose**: Build infrastructure to separate open interest from trading volume in GEX calculations

**Technical Work**:
- Database schema updates (OI vs Volume fields)
- GEXCalculator split calculations
- Validation pipeline updates

**Related Docs**: (infrastructure, no user-facing docs)

**Dependencies**:
- Blocks: #138 (Dual GEX extension)
- Depends on: None

---

## Completed Issues (Background Context)

### #112: OpenAI Batch API Implementation ✅ COMPLETE
**Completed**: November 6, 2025

**Achievement**: 50% cost reduction + async processing

**Metrics**:
- **Cost**: $0.016/window (Batch) vs $0.032/window (Sync)
- **Time**: 1-2 hours async vs 7.5 hours blocking
- **Total Savings**: $19.25 across Paper #2 validation
- **Success Rate**: 100% parsing (after Issue #137 fixes)

**Related Docs**:
- `batch_api/guide.md` - User guide
- `batch_api/implementation.md` - Technical summary
- `batch_api/review.md` - Code review

**Impact**: Enabled cost-effective Phase 1-4 validation

---

### #137: JSON Parsing Fixes ✅ COMPLETE
**Completed**: November 6, 2025

**Problem**: o4-mini quirks causing parse failures
- Invalid `\escape` sequences in JSON
- Writing numbers as words ("thirty" instead of 30)

**Solution**:
- Defensive parsing in 4 locations
- Prompt specification (numeric field requirements)
- Markdown code block stripping

**Result**: 100% parsing success rate in Phase 1 (52/52 windows)

**Related Docs**: `PHASE2_IMPLEMENTATION_SUMMARY.md` (JSON parsing section)

---

### #108: Phase 1 Implementation (5-Day Sequential) ✅ DEPRECATED
**Completed**: November 5, 2025 → **SUPERSEDED** by 30-day pivot

**Original Approach**: 5-day trajectory analysis
- Achieved 98-100% detection (2020: 98.4%, Q1 2024: 100%)
- Too universal - detects daily hedging, not persistent regimes

**Outcome**: Led to methodology pivot (Issue #89)

**Related Docs**: `archive/5day_methodology/` (archived)

---

### #110: Prompt Calibration ✅ COMPLETE
**Completed**: November 5, 2025

**Finding**: Mechanical guidance > qualitative guidance
- Mechanical v3a: 20% false positive rate
- Qualitative v3b: 50% false positive rate
- **Winner**: Mechanical criteria (>70% persist, >$5B, ≤5 flips)

**Impact**: Regime detection prompt v1 uses mechanical guidance

**Related Docs**: `methodology/prompt_bias_mitigation.md`

---

### #111: Test 4 - Low GEX Control (2020 Full Year) ✅ COMPLETE
**Completed**: November 5, 2025

**Purpose**: Validate discrimination using pre-0DTE era data

**Result**: ❌ **98.4% detection** (253/257 windows)
- Same as Q1 2024 (100%) despite 79% lower GEX magnitude
- **Conclusion**: 5-day windows not selective enough

**Outcome**: **Led to methodology pivot** (Issue #89)

**Related Docs**: `validation/test4/` (archived to `archive/5day_methodology/`)

---

### #90: Prompt Bias Testing ✅ COMPLETE
**Completed**: November 4, 2025

**Finding**: No leading language bias detected
- Leading prompt: 100% detection (10/10)
- Neutral prompt: 80% detection (8/10)
- Difference: 20 points (acceptable - 2 borderline cases)

**Impact**: Confirmed prompt design is conservative, not biased

**Related Docs**: `methodology/prompt_bias_mitigation.md`

---

## Future Work (Backlog)

### #131: Multi-Pattern Interference Testing
**Status**: 🔮 **BACKLOG** (After Phase 3/4)

**Research Question**: Can LLMs detect multiple regimes simultaneously?

**Example**:
- Window with persistent negative GEX (detected)
- AND high 0DTE volume spike on Friday (separate pattern)
- Can LLM identify both?

**Dependencies**: Requires Phase 3 completion + multi-pattern prompt design

**Related Docs**: `5_extensions/02_multi_pattern.md` (to be created)

---

### #133: Alternative Obfuscation Methods
**Status**: 🔮 **BACKLOG** (Paper #2 robustness extension)

**Research Question**: Does obfuscation method affect detection?

**Current**: Day T-29 through T+0 format
**Alternatives**: Reverse chronological, percentage changes, z-scores

**Dependencies**: Requires Phase 3 baseline completion

**Related Docs**: `5_extensions/03_alternative_obfuscation.md` (to be created)

---

### #87: Multi-Ticker Extension (Beyond SPY)
**Status**: 🔮 **BACKLOG** (Dissertation Paper #4)

**Research Question**: Do regime patterns generalize beyond SPY?

**Tickers**: QQQ (tech-heavy), IWM (small-cap), XLE (energy sector)

**Dependencies**: Requires Paper #2 complete + database expansion

**Related Docs**: `5_extensions/04_multi_year_ticker.md` (to be created)

---

### #105: Multi-Year Extension (2020-2024)
**Status**: 🔮 **BACKLOG** (Paper #2 Phase 4 overlap)

**Research Question**: 0DTE hypothesis test

**Approach**: Compare 2020 (pre-0DTE) vs 2024 (post-0DTE) detection rates
- Expected: Lower detection in 2020 (less persistent regimes)

**Dependencies**: Phase 3 complete (2024 baseline)

**Related Docs**: `validation/validation_phases.md` (Phase 4 section)

---

### #115-118: Dissertation Planning
**Status**: 🔮 **BACKLOG** (Long-term planning)

**Papers**:
- Paper #1: Pattern taxonomy (submitted Oct 2025)
- Paper #2: Regime detection (current)
- Paper #3: Sector rotation at regime boundaries
- Paper #4: Multi-ticker generalization

**Dependencies**: Paper #2 completion

---

## Non-Paper #2 Issues (Filter Out)

**Paper #1 Work**:
- #88: Paper #1 figures
- #92: Granger causality analysis
- #95: Symposium presentation
- #99-101: Statistical validation
- #121, #124: Paper #1 revisions

**Early System Development** (Pre-Paper #1):
- #2, #6, #8, #9, #13: Infrastructure and cache system

**Future Papers**:
- #135-136: Paper #3/4 planning

---

## Documentation Map

### Master Navigation
- **README.md**: Paper #2 overview and navigation
- **ROADMAP.md** (this file): Issue mapping and status
- **CURRENT_PHASE.md**: What we're doing NOW and WHY

### Sequential Reading Path
1. `1_methodology/` - Research question and regime criteria (4 files)
2. `2_validation_strategy/` - 4-phase validation roadmap (6 files)
3. `3_phase1_results/` - Phase 1 execution and results (4 files)
4. `4_phase2_execution/` - Current work (Phase 2 workflow, 4 files)
5. `5_extensions/` - Future work (dual GEX, multi-pattern, etc., 5 files)

### Technical Infrastructure
- `batch_api/` - OpenAI Batch API guides (3 files)
- `prompts/` - LLM prompts (1 file)
- `adr/` - Architecture decision records (7 files)

### Archive
- `archive/5day_methodology/` - OLD 5-day approach (deprecated Nov 5, 2025)

---

## Decision Trees

### After Phase 2 Results

**IF Phase 2 passes** (<10% false positive rate):
1. ✅ Proceed to Phase 3 (full 2024, 223 windows, ~$1.75)
2. ✅ Expect detection rate regression to 30-50% target
3. ✅ Phase 4 becomes possible (2020 comparison)

**IF Phase 2 fails** (≥10% false positive rate):
1. ❌ Diagnose which criterion failed (persistence? magnitude? flips?)
2. 🔄 Recalibrate criteria (e.g., raise persistence to 75%, magnitude to $7B)
3. 🔄 Re-run Phase 1 with new criteria
4. 🔄 Retry Phase 2

### After Phase 3 Results

**IF Phase 3 shows 30-50% detection**:
1. ✅ Framework validated as selective
2. ✅ Proceed to Phase 4 (2020 comparison)
3. ✅ Begin Phase 1.5 (Issue #138 - Dual GEX)

**IF Phase 3 shows >60% detection**:
1. ⚠️ Criteria may be too loose
2. 🔄 Recalibrate and re-run
3. ⚠️ Question: Is 2024 anomalous year?

**IF Phase 3 shows <20% detection**:
1. ⚠️ Criteria may be too strict
2. 🔄 Relax criteria (e.g., 65% persistence, $4B magnitude)
3. 🔄 Re-run Phase 3

---

## Key Insights to Integrate

### From Phase 1 Results
- Q1 2024 was anomalously persistent (71.2% detection vs 30-50% target)
- Framework IS selective (39-point persistence gap, 53.5-point confidence gap)
- Expect regression to target in full year

### From Issue #138 (Dual GEX)
- GEX_OI (structural) vs GEX_VOL (economic) explains profitability variance
- Phase 2c (low-magnitude) may need rethinking (could create HIGH_FRAGILITY regime)
- Extension unlocks Paper #1 profitability mystery

### From 5-Day Pivot (Issue #111)
- 5-day windows detect universal hedging (98-100% detection)
- 30-day windows detect persistent regimes (30-50% expected)
- User insight: "Nobody trades 5-day patterns, market regimes are 30 days"

---

## Contact & Coordination

**GitHub Labels**:
- `paper2` - All Paper #2 work
- `validation` - Validation infrastructure
- `batch-api` - Batch API related
- `phase1`, `phase2`, `phase3`, `phase4` - Validation phases

**Branch**: `paper2-sequential-gex`

**Last Major Update**: November 19, 2025 (Phase 1 complete, Phase 2 ready)
