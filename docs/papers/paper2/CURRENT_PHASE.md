# Current Phase: What We're Doing NOW and WHY

**Last Updated**: November 19, 2025
**Current Phase**: Phase 2 (Negative Controls)
**Status**: ✅ Infrastructure Ready, 📅 Execution Pending

---

## ONE-PAGE SUMMARY

### What Are We Doing?

**Phase 2 Negative Controls**: Three batch validation tests to prove framework has <10% false positive rate

| Test | Purpose | Expected Detection |
|------|---------|-------------------|
| **Phase 2a: Shuffle** | Randomize GEX day order (destroys temporal structure) | 0% |
| **Phase 2b: Transitional** | Filter for 7-10 sign flip windows (violates ≤5 criterion) | 0-10% |
| **Phase 2c: Low-Magnitude** | Scale GEX down 75% (~$12B → ~$3B, violates >$5B criterion) | 0-10% |

**Total Cost**: ~$0.50
**Total Time**: ~2 hours (async Batch API)

---

### Why Are We Doing This?

**Phase 1 Result**: 71.2% detection (37/52 windows) - Higher than 30-50% target

**Risk**: Is framework detecting TOO MANY regimes (not selective enough)?

**Phase 2 Purpose**: Validate framework is SELECTIVE before expensive Phase 3
- If Phase 2 passes (<10% FP) → Framework correctly rejects non-regimes → Proceed to Phase 3
- If Phase 2 fails (≥10% FP) → Framework too loose → Recalibrate criteria → Re-run Phase 1

**Why This Order?**
1. ✅ Phase 1 proves framework CAN detect regimes (71.2%)
2. 📍 Phase 2 proves framework WON'T detect non-regimes (<10% FP) ← **WE ARE HERE**
3. 🔮 Phase 3 measures full-year selectivity (30-50% target)

**Cost Justification**: Phase 2 costs $0.50 vs Phase 3 costs $1.75
- Better to fail Phase 2 ($0.50) than discover selectivity issues in Phase 3 ($1.75)

---

### How Are We Doing This?

**Tool**: `scripts/validation/paper2/validate_regime_windows_batch.py` (upgraded with --phase flag)

**Commands**:

```bash
# Phase 2a: Shuffled windows
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --phase shuffle \
  --submit

# Phase 2b: Transitional windows
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --phase transitional \
  --submit

# Phase 2c: Low-magnitude windows
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --phase low-magnitude \
  --submit
```

**Data Source**: Real 2024 market data (not synthetic)
- All transformations apply to real GEX values
- Shuffle randomizes real values, transitional filters real windows, low-magnitude scales real values
- No database contamination risk

**Processing**: OpenAI Batch API (o4-mini-2025-04-16)
- Submit 3 batches (~5 min each)
- Poll for completion (~1-2 hours)
- Retrieve and analyze results (~15 min)

---

### What's the Decision Point?

**Pass Criteria**: <10% false positive rate across all 3 tests

**IF PASS** (<10% FP rate):
1. ✅ Framework is selective (correctly rejects non-regimes)
2. ✅ Proceed to Phase 3 (full 2024, 223 windows, ~$1.75)
3. ✅ Expect detection rate regression to 30-50% target

**IF FAIL** (≥10% FP rate):
1. ❌ Framework too loose (detecting non-regimes)
2. 🔍 Diagnose which criterion failed:
   - Persistence criterion (≥70% → raise to 75%?)
   - Magnitude criterion (≥$5B → raise to $7B?)
   - Flips criterion (≤5 → lower to ≤3?)
3. 🔄 Recalibrate criteria based on failure pattern
4. 🔄 Re-run Phase 1 with new criteria (~$0.81)
5. 🔄 Retry Phase 2 with updated framework (~$0.50)

**Example Failure Analysis**:
- If Phase 2a (shuffle) has >10% FP → Persistence criterion not working
- If Phase 2b (transitional) has >10% FP → Flips criterion (≤5) too loose
- If Phase 2c (low-magnitude) has >10% FP → Magnitude criterion ($5B) too low

---

## CONTEXT: Where We Came From

### Phase 1 Results (November 19, 2025)

**Detection**: 71.2% (37/52 windows) - Borderline high vs 30-50% target

**Why Borderline is Acceptable**:
1. ✅ **Framework IS selective** - Not detecting everything blindly
   - Persistence gap: 39 percentage points (96% detected vs 57% rejected)
   - Confidence gap: 53.5 points (93.0 detected vs 39.5 rejected)
   - Magnitude gap: $6.84B ($11.66B detected vs $4.82B rejected)

2. ✅ **Q1 2024 was anomalous** - Sustained positive gamma throughout quarter
   - Expected regression to 30-50% in full year (more transitional periods)

3. ✅ **Decision**: Proceed to Phase 2 (validate selectivity before Phase 3)

**What We Learned**:
- LLM correctly cites persistence %, magnitude, and flips
- LLM correctly rejects borderline windows (56% persistence, $3-4B magnitude)
- High confidence calibration (83% of detections are 90-100% confidence)
- Much more selective than 5-day approach (71% vs 98-100%)

### Why We Pivoted from 5-Day to 30-Day (November 5, 2025)

**OLD Approach**: 5-day trajectory analysis (Issues #108-111)
- **Result**: 98-100% detection across ALL regimes
  - 2020 (weak GEX, $2.85B avg): 98.4% detection
  - Q1 2024 (strong GEX, $13.95B avg): 100% detection
- **Problem**: Detecting universal daily hedging, not persistent regimes
- **User Insight**: "Nobody trades 5-day patterns, market regimes are 30 days"

**NEW Approach**: 30-day regime persistence (Issue #89)
- **Regime Criteria**: ≥70% persistence + ≥$5B magnitude + ≤5 sign flips
- **Expected Detection**: 30-50% (selective, not universal)
- **Why Better**: Detects meaningful structural regimes, not trivial daily flows

---

## CONTEXT: What Comes Next

### After Phase 2 (If Pass)

**Phase 3: Full 2024 Validation** (🔮 Planned, ~3 weeks)
- **Windows**: 223 (full 2024 year)
- **Cost**: ~$1.75 (Batch API)
- **Expected Detection**: 30-50% (regression from Q1's 71%)
- **Purpose**: Measure full-year selectivity across all market conditions

**Phase 4: 2020 Comparison** (🔮 Planned, ~3 weeks)
- **Windows**: 223 (pre-0DTE era)
- **Cost**: ~$1.75 (Batch API)
- **Expected Detection**: <30% (less persistent regimes without 0DTE)
- **Purpose**: Test 0DTE hypothesis (0DTE creates persistent regimes)

### Extensions (After Phase 3/4)

**Phase 1.5: Dual GEX (Issue #138)** - Explains profitability variance
- **Research Question**: Why does profitability vary when detection stays constant?
- **Answer**: GEX_OI (structural) vs GEX_VOL (economic activity) split
- **Four Regimes**:
  - HIGH_FRAGILITY: GEX_OI negative + GEX_VOL near zero (Q4 2024: -1bp alpha)
  - ELEVATED_RISK: GEX_OI negative + GEX_VOL negative (Q1 2024: +21bp alpha)
  - STABLE_POSITIVE: Both positive (low volatility)
  - TRANSITIONAL: Mixed signals
- **Impact**: Unlocks Paper #1 profitability mystery

**Multi-Pattern (Issue #131)** - Can LLMs detect multiple regimes simultaneously?

**Alternative Obfuscation (Issue #133)** - Robustness testing

**Multi-Year/Ticker (Issues #87, #105)** - Generalization testing

---

## QUICK REFERENCE

### Key Files
- **Execution Script**: `scripts/validation/paper2/validate_regime_windows_batch.py`
- **Phase 2 Workflow**: `docs/papers/paper2/PHASE2_IMPLEMENTATION_SUMMARY.md`
- **Validation Strategy**: `docs/papers/paper2/validation/validation_phases.md`
- **Batch API Guide**: `docs/papers/paper2/batch_api/guide.md`

### Key Commands

**Submit Phase 2 batches**:
```bash
# Export PYTHONPATH (required)
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

# Submit each test
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 --end-date 2024-03-29 \
  --phase shuffle --submit

python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 --end-date 2024-03-29 \
  --phase transitional --submit

python scripts/validation/paper2/validate_regime_windows_batch.py \
  --start-date 2024-01-02 --end-date 2024-03-29 \
  --phase low-magnitude --submit
```

**Poll for completion**:
```bash
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> --poll
```

**Retrieve results**:
```bash
python scripts/validation/paper2/validate_regime_windows_batch.py \
  --batch-id batch_<YOUR_ID> --retrieve
```

**Analyze false positive rates**:
```bash
# Count detections in each phase
grep "regime:" reports/validation/regime_windows/phase2a_shuffle*.yaml | grep -c "persistent"
grep "regime:" reports/validation/regime_windows/phase2b_transitional*.yaml | grep -c "persistent"
grep "regime:" reports/validation/regime_windows/phase2c_low_magnitude*.yaml | grep -c "persistent"

# Calculate FP rate: (detections / total windows) × 100
```

### GitHub Issues
- **Phase 2 Work**: Issue #107 (Validation Strategy)
- **Dependencies**: Issue #112 (Batch API - COMPLETE), Issue #137 (JSON Parsing - COMPLETE)
- **Blockers**: None - Infrastructure complete

### Related Documentation
- **ROADMAP.md**: All Paper #2 issues and dependencies
- **README.md**: Paper #2 overview
- **validation/validation_phases.md**: Complete 4-phase strategy
- **PHASE2_IMPLEMENTATION_SUMMARY.md**: Technical execution details

---

**Status**: ✅ Ready to Execute - All infrastructure complete, awaiting batch submission

**Next Action**: Submit Phase 2a (shuffle) batch, monitor for completion, analyze FP rate

**Decision Horizon**: ~2 hours (async batch processing) + 15 min analysis = Phase 2 complete
