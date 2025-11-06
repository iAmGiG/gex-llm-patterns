# Phase 1 Game Plan - Q1 2024 Regime Validation

**Created**: November 6, 2025, 21:00
**Status**: Ready to Execute
**Cost**: $1.25 (50% savings with Batch API)
**Timeline**: 2-4 hours total

---

## 🎯 OBJECTIVE

Establish baseline detection rate for 30-day regime windows using Q1 2024 data.

**Success Criteria**:
- Detection rate: 30-50% (selective) → Proceed to Phase 2
- Detection rate: >80% (too loose) → Recalibrate or pivot
- Obfuscation working (Day T-29 through T+0)
- No JSON parsing errors

---

## 📋 EXECUTION STEPS

### Step 1: Submit Batch Job

```bash
# Set PYTHONPATH
export PYTHONPATH=/mnt/bst/yxie2/cregan1/gex-llm-patterns:$PYTHONPATH

# Submit Phase 1 batch
python scripts/validation/validate_regime_windows_batch.py \
  --start-date 2024-01-02 \
  --end-date 2024-03-29 \
  --submit \
  --description "Phase 1 Q1 2024 validation (32 windows)"
```

**Expected Output**:
- Batch file created: `batch_regime_YYYYMMDD_HHMMSS.jsonl`
- Batch ID: `batch_xyz...`
- Status: "validating" → "in_progress"

**Save the batch_id** - you'll need it for polling/retrieval

### Step 2: Poll for Completion (Background)

```bash
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id <batch_id_from_step1> \
  --poll \
  --poll-interval 60 \
  2>&1 | tee /tmp/phase1_poll.log &
```

**Timeline**:
- Expected: 1-2 hours processing
- Status progression: validating → in_progress → completed

**Monitoring**:
```bash
# Check status
tail -20 /tmp/phase1_poll.log

# Or check manually
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id <batch_id> \
  --poll \
  --poll-interval 300  # Check every 5 minutes
```

### Step 3: Retrieve Results

```bash
python scripts/validation/validate_regime_windows_batch.py \
  --batch-id <batch_id_from_step1> \
  --retrieve
```

**Expected Output**:
- Results file: `results_<batch_id>.jsonl`
- YAML output: `reports/validation/regime_windows/phase_batch_<batch_id>.yaml`
- Summary: Detection rate, confidence average

---

## 🔍 ANALYSIS TASKS

### 1. Calculate Detection Rate

```bash
# Quick check
cat reports/validation/regime_windows/phase_batch_<batch_id>.yaml | grep "detection_rate_pct"
```

**Interpretation**:
- 30-50%: ✅ Framework working as intended
- 50-80%: ⚠️ Borderline - review cases
- >80%: ❌ Too loose - same problem as 5-day
- <30%: ❌ Too strict - may need looser criteria

### 2. Review Confidence Distribution

```python
# Count confidence brackets
import yaml
with open('reports/validation/regime_windows/phase_batch_<batch_id>.yaml') as f:
    data = yaml.safe_load(f)

conf_90_100 = sum(1 for w in data['windows'] if w.get('confidence', 0) >= 90)
conf_70_89 = sum(1 for w in data['windows'] if 70 <= w.get('confidence', 0) < 90)
conf_50_69 = sum(1 for w in data['windows'] if 50 <= w.get('confidence', 0) < 70)

print(f"90-100: {conf_90_100}")
print(f"70-89: {conf_70_89}")
print(f"50-69: {conf_50_69}")
```

**Expected**: Most detections in 70-100 range, few in 50-69

### 3. Check Regime Types

```python
from collections import Counter
regime_types = [w.get('regime_type') for w in data['windows'] if w.get('regime_detected')]
print(Counter(regime_types))
```

**Expected**: Mostly persistent_positive (Q1 2024 had high positive GEX)

### 4. Spot Check 3-5 Windows

Pick a few detected regimes and verify LLM reasoning:
1. High confidence (95%): Should have >90% persistence, >$10B avg
2. Medium confidence (75%): Should have 70-80% persistence, $5-10B avg
3. Rejected window: Should fail one or more criteria

### 5. Verify Obfuscation

Check batch JSONL file:
```bash
head -1 reports/validation/regime_windows/batch_jobs/batch_regime_*.jsonl | \
  grep -o "Day T" | head -5
```

**Expected**: Should see "Day T-29", "Day T-28", etc. (NO real dates)

---

## 📊 DECISION MATRIX

| Detection Rate | Confidence | Decision |
|----------------|-----------|----------|
| 30-50% | 70-95% | ✅ **PROCEED TO PHASE 2** |
| 50-80% | 70-95% | ⚠️ Review borderline cases, consider tightening |
| >80% | Any | ❌ **TOO LOOSE** - Tighten criteria or pivot |
| <30% | 70-95% | ❌ **TOO STRICT** - Loosen criteria (60% persistence? $3B?) |
| Any | <70% | ❌ **LOW CONFIDENCE** - Review prompt guidance |

---

## 🚨 TROUBLESHOOTING

### Batch Submission Fails
- Check API key in config.json
- Verify PYTHONPATH set
- Check cache has Q1 2024 data: `ls .cache/gex_data/SPY/ | grep 2024-0[1-3]`

### Polling Timeout
- Batch API can take up to 24 hours (rare)
- Check status manually: `--poll --poll-interval 300`
- Batch ID saved in metadata file

### JSON Parsing Errors
- Should be fixed (markdown wrapper stripping)
- If errors persist: Check raw JSONL results file
- Verify o4-mini returning valid JSON in ```json blocks

### Low Detection Rate (<10%)
- Check if GEX data is correct (not all zeros)
- Verify obfuscation not breaking data
- Review a few windows manually

---

## 📝 OUTPUT ARTIFACTS

**Generated Files**:
1. `batch_regime_YYYYMMDD_HHMMSS.jsonl` - Input batch file
2. `batch_<batch_id>_metadata.json` - Batch metadata
3. `results_<batch_id>.jsonl` - Raw OpenAI results
4. `phase_batch_<batch_id>.yaml` - Parsed validation results

**Keep For Analysis**:
- YAML file (summary statistics + all windows)
- Metadata file (batch tracking)

**Can Delete**:
- JSONL files (large, can regenerate)

---

## ✅ SUCCESS CHECKLIST

- [ ] Batch submitted successfully (batch_id obtained)
- [ ] Polling completed (status = "completed")
- [ ] Results retrieved (YAML file created)
- [ ] Detection rate calculated
- [ ] Confidence distribution analyzed
- [ ] Regime types checked
- [ ] 3-5 windows spot-checked
- [ ] Obfuscation verified
- [ ] Decision made (proceed/recalibrate/pivot)
- [ ] TODO.md updated with results
- [ ] GitHub Issue #112 updated

---

## 🔜 NEXT STEPS

**If Detection 30-50% (SUCCESS)**:
1. Document Phase 1 results in TODO.md
2. Update GitHub Issue #112
3. Prepare Phase 2 (negative controls)
4. Run Phase 2a (shuffled windows)

**If Detection >80% (TOO LOOSE)**:
1. Analyze why (all windows persistent?)
2. Options:
   - Tighten persistence: 70% → 80% (24/30 days)
   - Tighten magnitude: $5B → $10B
   - Tighten stability: ≤5 flips → ≤3 flips
3. Rerun Phase 1 with new criteria

**If Detection <30% (TOO STRICT)**:
1. Analyze rejected windows
2. Options:
   - Loosen persistence: 70% → 60% (18/30 days)
   - Loosen magnitude: $5B → $3B
3. Rerun Phase 1 with new criteria

---

**Estimated Time**: 2-4 hours total (mostly waiting for Batch API)
**Estimated Cost**: $1.25 (vs $2.50 with sync API)
**Risk**: Low (infrastructure tested, obfuscation verified)
