# Paper #2: 30-Day Regime Detection with LLMs

**Research Question**: Can LLMs identify persistent market regimes from 30-day GEX sequences without temporal context?

**Status**: Phase 1 COMPLETE (71.2% detection), Phase 2 Ready to Execute
**Last Updated**: November 19, 2025
**Branch**: `paper2-sequential-gex`

---

## START HERE: Navigation Guide

### New to Paper #2? Read These First

1. **[CURRENT_PHASE.md](CURRENT_PHASE.md)** (5 min) - What we're doing NOW and WHY
   - One-page summary of current work
   - Phase 2 execution plan
   - Decision criteria

2. **[ROADMAP.md](ROADMAP.md)** (15 min) - All GitHub issues mapped to status
   - 14 Paper #2 issues with dependencies
   - Phase 1 results summary
   - Future work backlog

3. **This README** (below) - Paper #2 overview and methodology

### Want Details? Follow Sequential Reading Path

**Recommended Order**:
1. `1_methodology/` - Research question and regime criteria (4 docs)
2. `2_validation_strategy/` - 4-phase validation roadmap (6 docs)
3. `3_phase1_results/` - Phase 1 execution and results (4 docs)
4. `4_phase2_execution/` - Current work (Phase 2 workflow, 4 docs)
5. `5_extensions/` - Future work (dual GEX, multi-pattern, etc.)

_(Note: Folders 1-5 to be created during consolidation)_

### Need Technical Details?

- **Batch API**: `batch_api/` - OpenAI Batch API implementation (3 docs)
- **Prompts**: `prompts/` - LLM regime detection prompt
- **Scripts**: `scripts/validation/paper2/` - Validation scripts with READMEs

---

## Research Overview

### The Pivot (November 5, 2025)

**FROM**: 5-day trajectory analysis (98-100% detection - too universal)
**TO**: 30-day regime persistence (30-50% target - selective)

**Why?**
- 5-day windows detected universal daily hedging (known since 1973)
- 30-day windows detect persistent structural regimes (meaningful contribution)
- User insight: "Nobody trades 5-day patterns, market regimes are 30 days"

### Regime Criteria

A 30-day window qualifies as a **persistent regime** if it meets ALL three criteria:

| Criterion | Threshold | Purpose |
|-----------|-----------|---------|
| **Persistence** | ≥70% days same sign | Dominance test (21+ days) |
| **Magnitude** | ≥$5B average | Economic significance |
| **Stability** | ≤5 sign flips | Low volatility (not transitional) |

**Detection Target**: 30-50% of windows (proves framework is selective)

### Why 30-50% Detection is Success

**NOT 98-100%** (universal patterns - trivial contribution):
- Detects daily hedging flows present in all regimes
- No discrimination between market conditions
- Unpublishable (not a new finding)

**YES 30-50%** (selective detection - meaningful contribution):
- Distinguishes persistent regimes from transitional periods
- Can test 0DTE hypothesis (compare 2020 vs 2024)
- Can identify regime boundaries for sector rotation (Paper #3)
- Publishable (new methodology with discrimination power)

**Q1 2024 Result**: 71.2% detection (borderline high but acceptable)
- Q1 was anomalously persistent (sustained positive gamma)
- Framework IS selective (39-point persistence gap)
- Expected regression to 30-50% in full year

---

## Current Status

### Phase 1: Q1 2024 Baseline ✅ COMPLETE

**Windows**: 52 (2024-01-02 through 2024-03-29)
**Detection**: 71.2% (37/52 windows)
**Cost**: $0.81 (Batch API)

**Selectivity Metrics** (Detected vs Rejected):
- **Persistence gap**: 39 percentage points (96% vs 57%)
- **Confidence gap**: 53.5 points (93.0 vs 39.5)
- **Magnitude gap**: $6.84B ($11.66B vs $4.82B)

**Key Finding**: Framework IS selective - LLM correctly rejects borderline windows

**Decision**: ✅ **Proceed to Phase 2** (validate <10% false positive rate)

**Documentation**: `3_phase1_results/` _(to be created during consolidation)_

---

### Phase 2: Negative Controls 📍 READY TO EXECUTE

**Purpose**: Validate framework has <10% false positive rate before expensive Phase 3

**Three Tests**:
1. **Shuffle** (Phase 2a): Randomize GEX day order → expect 0% detection
2. **Transitional** (Phase 2b): Filter for 7-10 flip windows → expect 0-10% detection
3. **Low-Magnitude** (Phase 2c): Scale GEX down 75% → expect 0-10% detection

**Cost**: ~$0.50 total
**Time**: ~2 hours async processing

**Pass Criteria**: <10% false positive rate across all 3 tests

**Documentation**:
- `CURRENT_PHASE.md` - Execution plan (this is our current focus)
- `PHASE2_IMPLEMENTATION_SUMMARY.md` - Technical workflow
- `4_phase2_execution/` _(to be created during consolidation)_

---

### Phase 3: Full 2024 Validation 🔮 PLANNED

**Windows**: 223 (full 2024 year)
**Expected Detection**: 30-50% (regression from Q1's 71%)
**Cost**: ~$1.75
**Timeline**: ~2 hours async processing

**Purpose**: Measure full-year selectivity across all market conditions

**Depends On**: Phase 2 pass (<10% FP rate)

---

### Phase 4: 2020 Comparison 🔮 PLANNED

**Windows**: 223 (pre-0DTE era)
**Expected Detection**: <30% (less persistent without 0DTE)
**Cost**: ~$1.75

**Purpose**: Test 0DTE hypothesis (0DTE proliferation creates persistent regimes)

**Depends On**: Phase 3 completion

---

## Methodology Innovation

### Obfuscation Testing

**Problem**: How do we know LLMs detect structural mechanics vs memorized patterns?

**Solution**: Strip all temporal/contextual information
- Real dates → "Day T-29" through "Day T+0"
- Real tickers → Generic labels
- No event context (earnings, Fed meetings, etc.)

**Validation**: If LLM still detects regimes, it's using dealer constraint logic

### Mechanical Criteria Guidance

**Finding** (Issue #110): Mechanical guidance > qualitative guidance
- **Mechanical v3a**: 20% false positive rate (cite specific thresholds)
- **Qualitative v3b**: 50% false positive rate (describe patterns)
- **Winner**: Mechanical (provides clear decision boundaries)

**Implementation**: LLM prompt specifies exact thresholds (≥70%, ≥$5B, ≤5)

### Batch API Cost Optimization

**Achievement** (Issue #112): 50% cost reduction
- **Sync API**: $0.032/window
- **Batch API**: $0.016/window
- **Total Savings**: $19.25 across Paper #2 validation

**Processing**: 1-2 hours async (vs 7.5 hours blocking)

---

## Extensions & Future Work

### Phase 1.5: Dual GEX Framework (Issue #138)

**Research Question**: Why does profitability vary when detection stays constant?

**Answer**: GEX_OI (structural positioning) vs GEX_VOL (economic activity)

**Four Regimes**:
- **HIGH_FRAGILITY**: GEX_OI negative + GEX_VOL near zero → Low profitability
- **ELEVATED_RISK**: GEX_OI negative + GEX_VOL negative → High profitability
- **STABLE_POSITIVE**: Both positive → Low volatility
- **TRANSITIONAL**: Mixed signals

**Impact**: Explains Paper #1 profitability mystery (Q1 +21bp → Q4 -1bp)

**Timeline**: After Phase 3 completion

---

### Other Extensions (Backlog)

**Multi-Pattern Interference** (Issue #131)
- Can LLMs detect multiple regimes simultaneously?
- Requires Phase 3 baseline

**Alternative Obfuscation** (Issue #133)
- Robustness testing (reverse chronological, percentage changes, z-scores)
- Requires Phase 3 baseline

**Multi-Ticker** (Issue #87)
- Generalization to QQQ, IWM, XLE
- Dissertation Paper #4

**Multi-Year** (Issue #105)
- 2020-2024 comparison (overlaps with Phase 4)
- 0DTE hypothesis test

---

## Quick Commands

### Execute Phase 2

```bash
# Set PYTHONPATH (required)
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

# Submit Phase 2a (shuffle)
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 --end-date 2024-03-29 \
  --phase shuffle --submit

# Submit Phase 2b (transitional)
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 --end-date 2024-03-29 \
  --phase transitional --submit

# Submit Phase 2c (low-magnitude)
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 --end-date 2024-03-29 \
  --phase low-magnitude --submit

# Poll for completion
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> --poll

# Retrieve results
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> --retrieve
```

### Analyze Results

```bash
# Count detections
grep "regime:" reports/validation/regime_windows/phase2a*.yaml | grep -c "persistent"

# View results
cat reports/validation/regime_windows/phase2a*.yaml
```

---

## Key Insights

### From Phase 1 Results
1. Q1 2024 was anomalously persistent (71.2% vs 30-50% target)
2. Framework IS selective (39-point persistence gap, 53.5-point confidence gap)
3. LLM correctly cites metrics (persistence %, magnitude, flips)
4. High confidence calibration (83% of detections are 90-100%)
5. Expected regression to target in full year

### From 5-Day Pivot (Issue #111)
1. 5-day windows achieved 98-100% detection (too universal)
2. Detected universal daily hedging, not persistent regimes
3. User insight: "Nobody trades 5-day patterns"
4. 30-day windows expected to be selective (30-50%)

### From Prompt Calibration (Issue #110)
1. Mechanical guidance reduces false positives 60%
2. Mechanical v3a: 20% FP vs Qualitative v3b: 50% FP
3. Clear thresholds prevent LLM hallucination

---

## File Organization

### Current Structure (Pre-Consolidation)

```
docs/papers/paper2/
├── README.md (this file)
├── ROADMAP.md (issue mapping)
├── CURRENT_PHASE.md (current work)
├── PHASE2_IMPLEMENTATION_SUMMARY.md (technical workflow)
├── BATCH_API_GUIDE.md
├── BATCH_API_IMPLEMENTATION_SUMMARY.md
├── BATCH_API_REVIEW.md
├── STATISTICAL_RIGOR_GUIDE.md
├── methodology/ (5 files)
├── validation/ (12 files)
├── prompts/ (1 file)
├── adr/ (7 files)
├── sessions/ (6 files - historical)
└── archive/ (old 5-day content)
```

### Planned Structure (Post-Consolidation)

```
docs/papers/paper2/
├── README.md (master index - this file)
├── ROADMAP.md (issue mapping + status)
├── CURRENT_PHASE.md (what/why/how/decision)
│
├── 1_methodology/ (research question + criteria - 4 files)
├── 2_validation_strategy/ (4-phase roadmap - 6 files)
├── 3_phase1_results/ (execution + results - 4 files)
├── 4_phase2_execution/ (current work - 4 files)
├── 5_extensions/ (future work - 5 files)
│
├── batch_api/ (technical infrastructure - 3 files)
├── prompts/ (LLM prompts - 1 file)
├── adr/ (architecture decisions - 7 files)
└── archive/ (deprecated 5-day content)
```

---

## Related Documentation

**Scripts**: `scripts/validation/paper2/README.md` - Validation scripts documentation
**Paper #1**: `docs/papers/paper1/` - Pattern taxonomy (submitted Oct 2025)
**GitHub Issues**: See ROADMAP.md for all 14 Paper #2 issues

---

## Contact & Coordination

**Branch**: `paper2-sequential-gex`
**GitHub Labels**: `paper2`, `validation`, `batch-api`, `phase1`, `phase2`, `phase3`, `phase4`
**Last Major Update**: November 19, 2025 (Phase 1 complete, Phase 2 ready)

---

## What's Next?

**Immediate**: Execute Phase 2 negative controls (~2 hours)
**Short-term**: Phase 3 full 2024 validation (if Phase 2 passes)
**Medium-term**: Phase 4 2020 comparison (0DTE hypothesis)
**Long-term**: Phase 1.5 Dual GEX extension (profitability variance)

**See**: CURRENT_PHASE.md for detailed execution plan
