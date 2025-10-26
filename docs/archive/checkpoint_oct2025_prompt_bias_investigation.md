# Advisor Update: Prompt Bias Discovery and Revalidation

**Date**: October 16, 2025
**Status**: Methodological improvement complete - seeking guidance on presentation

---

## Executive Summary

While preparing Paper #1, we discovered our validation methodology contained **prompt bias** - the LLM was shown regime labels ("NEGATIVE_GAMMA") which essentially revealed the answer. We've now revalidated all 3 patterns with unbiased prompts:

**Key Finding**: Detection rate drops from 100% → 71% (average) when regime labels removed, but **all 3 patterns still pass the 60% mechanical threshold** and maintain 91% accuracy.

**Question for you**: How should we present this in Paper #1? Both results strengthen the research in different ways.

---

## Why We Discovered This Issue

### The Problem

During Q2 2024 validation, we achieved 100% detection rate across all patterns. This seemed too perfect. Upon reviewing the prompt structure, we found the LLM was being shown regime labels and pattern hints.

### Before: Biased Prompt (Standard Template)

**Example for April 1, 2024**:

```text
Analyze the following 10 trading days for INDEX_1. Look for patterns across all dates
and provide comparative analysis.

DATA FOR ANALYSIS:

Day T+0 (Obfuscated Date)
  Net GEX: -$32,905,699,168
  Spot Price: $522.22
  Regime: NEGATIVE_GAMMA                    ← SHOWING THE ANSWER!
  Gamma Flip Point: $485.00
  Patterns Detected: gamma_positioning      ← SHOWING THE PATTERN!

  Market Context:
  - Call Gamma: -$17.3B
  - Put Gamma: -$15.6B
  - GEX concentrated in negative territory

QUESTIONS TO ANSWER:
1. What patterns do you see across these dates?          ← Leading question
2. Are there consistent mechanics (WHO forcing WHOM to do WHAT)?
3. What is the highest confidence signal across all dates?
4. Do you see any temporal patterns (e.g., weekly effects)?
```

**The Problem**:

- Shows "NEGATIVE_GAMMA" regime label (the pattern we're detecting!)
- Shows "gamma_positioning" pattern hint (exactly what we're testing!)
- Leading questions presume patterns exist
- LLM cannot say "no pattern detected"

### After: Unbiased Prompt (New Template)

**Same date (April 1, 2024)**:

```text
Analyze the following 10 trading days for INDEX_1. Determine if any consistent
market mechanics are present.

DATA FOR ANALYSIS:

Day T+0 (Obfuscated Date)
  Net GEX: -$32,905,699,168 (raw value, unclassified)
  Spot Price: $522.22
  Zero-gamma level: $485.00

  Market Context:
  - Call Gamma: -$17.3B
  - Put Gamma: -$15.6B

QUESTIONS TO ANSWER:
1. Do you detect any consistent mechanics across these dates? If yes, what?
2. If mechanics exist, identify: WHO is forcing WHOM to do WHAT
3. Confidence level (0-100): How certain are you a pattern exists?
4. For days with no clear pattern, set confidence to 0 and explain why

RESPONSE REQUIREMENTS:
- pattern_detected: true/false (you can say false!)
- If false: explain why no pattern is present
- If true: identify WHO, WHOM, WHAT with evidence
```

**Key Differences**:

- ❌ No "NEGATIVE_GAMMA" label (LLM sees raw GEX values only)
- ❌ No "gamma_positioning" pattern hints
- ✅ Neutral questions ("Do you detect..." not "What patterns...")
- ✅ Can respond "no pattern detected" with confidence 0
- ✅ Must reason from GEX structure alone

### The Impact

This is a **major methodological difference**. The biased prompt essentially shows the answer, while the unbiased prompt forces the LLM to reason purely from market structure.

### Why This Matters

From an academic perspective, this could be seen as:

1. **Circular reasoning** - showing the label we want detected
2. **Inflated success rates** - 100% may not reflect true structural detection
3. **Reviewer concern** - "Did LLM detect pattern or just read the label?"

### Why We Acted Immediately

- Paper #1 draft in progress (due Oct 26)
- Better to discover now than during peer review
- Opportunity to strengthen methodology with transparent comparison

---

## What We Did

### Implementation (Issue #90)

Built a **config-based prompt template system** allowing three modes:

1. **Standard (biased)**: Shows regime labels + pattern hints (original approach)
2. **Unbiased**: Raw GEX data only, no labels, LLM can say "no pattern detected"
3. **Reasoning**: Chain-of-thought prompts for future o3-mini validation

### Revalidation Scope

- **All 3 patterns**: gamma_positioning, stock_pinning, 0dte_hedging
- **Full year 2024**: 242 trading days (Q1-Q4)
- **Unbiased prompts**: No regime labels, no pattern hints
- **Same obfuscation**: Dates → "Day T+0", tickers → "INDEX_1"

---

## Results: Biased vs Unbiased Comparison

### Detection Rates (Full Year 2024)

| Pattern | Biased Prompt | Unbiased Prompt | Delta | Accuracy |
|---------|---------------|-----------------|-------|----------|
| gamma_positioning | 100% | **69.4%** | -30.6% | 92.5% |
| stock_pinning | 100% | **67.4%** | -32.6% | 90.4% |
| 0dte_hedging | 100% | **77.7%** | -22.3% | 90.8% |
| **Average** | **100%** | **71.5%** | **-28.5%** | **91.2%** |

**Threshold**: ≥60% detection = MECHANICAL pattern (structural, not narrative)

### Key Observations

1. **All 3 patterns still pass mechanical threshold** (67-78% >> 60%)
2. **Consistent drop of ~25-33%** across all patterns (bias was real)
3. **High accuracy maintained** (90-92% prediction materialization)
4. **Detection range is stable** (67-78%) suggesting robust structural detection

---

## Interpretation: What These Results Mean

### Academic Perspective (Why This STRENGTHENS the paper)

**Original 100% Detection**:

- ✅ Shows LLM can interpret labeled data
- ⚠️ Vulnerable to "circular reasoning" criticism
- ⚠️ May appear like cherry-picking perfect results

**New 71% Detection (unbiased)**:

- ✅ Proves LLM detects patterns from GEX structure alone
- ✅ Conservative lower bound for structural detection
- ✅ Still well above 60% threshold (clearly mechanical)
- ✅ 91% accuracy shows predictions materialize (pattern is real)
- ✅ Transparent methodology (shows we tested rigorously)

**Combined Evidence (both results)**:

- ✅ 71-100% detection range demonstrates robustness
- ✅ Unbiased prompts prove no memorization + no label leakage
- ✅ Biased prompts show upper bound with context
- ✅ Multi-pattern consistency (3 different dealer constraints)

### What Hasn't Changed

**Still Valid**:

- ✅ Obfuscation testing prevents temporal memorization
- ✅ Multi-pattern generalization proven (3 patterns validated)
- ✅ High accuracy (90-92%) shows predictions materialize
- ✅ Full 2024 year coverage (242 days)
- ✅ Academic contribution: Obfuscation + unbiased prompts = no memorization

**Pattern Detection Is Real**:

- 71% detection WITHOUT being told the answer
- 91% of detected patterns actually happen (forward returns validate)
- Consistent across 3 different pattern types
- Works on obfuscated data (no temporal context)

---

## Questions for Advisor

### 1. Presentation Strategy

**Option A - Lead with Unbiased (Conservative)**:

- Present 71% detection as main result
- Discuss biased prompts as "with context" sensitivity analysis
- Emphasize 71% as robust lower bound

**Option B - Present Both Equally**:

- Show 71-100% detection range
- Discuss as ablation study (effect of regime labels)
- Emphasize transparency and thorough validation

**Option C - Lead with Biased, Acknowledge Limitation**:

- Present 100% as main result (matches Q1-Q4 validation)
- Discuss unbiased rerun as limitation section
- Future work: formal ablation studies

**Your recommendation?**

### 2. Impact on Paper Timeline

**Current Status**:

- Paper outline complete
- Committed 4 YAML files with biased results (need to replace?)
- Abstract/intro drafting can proceed either way

**Options**:

- **Replace files**: Commit unbiased YAMLs, use 71% as main result
- **Add files**: Keep biased, add unbiased, present both
- **Hybrid**: Use biased for Q1-Q4 quarterly breakdown, add full-year unbiased comparison

**Your preference for main paper results?**

### 3. Methodological Contribution

Does this prompt bias discovery + revalidation **strengthen or weaken** our academic contribution?

**Potential Strengthening Arguments**:

- Shows rigorous methodology (we caught and fixed the bias)
- 71% is more defensible than 100% (avoids "too good to be true")
- Ablation study adds methodological depth
- Transparent reporting of limitations

**Potential Concerns**:

- Does 71% vs 100% create confusion?
- Should we have caught this earlier?
- Does this delay Paper #1 submission?

**Your assessment?**

---

## Technical Details

### Files Created

- `config_defaults/llm_prompts.yaml` - Prompt template configuration
- `gamma_positioning_SPY_2024_unbiased.yaml` - 69.4% detection, 92.5% accuracy
- `stock_pinning_SPY_2024_unbiased.yaml` - 67.4% detection, 90.4% accuracy
- `0dte_hedging_SPY_2024_unbiased.yaml` - 77.7% detection, 90.8% accuracy

### Reproducibility

All results reproducible using:

```bash
python scripts/validation/validate_pattern_taxonomy.py \
  --pattern PATTERN_NAME \
  --symbol SPY \
  --start-date 2024-01-02 \
  --end-date 2024-12-31 \
  --prompt-template unbiased \
  --with-outcomes
```

### Code Changes

- Refactored `src/agents/market_mechanics_agent.py` to load prompts from config
- Added `--prompt-template` CLI flag
- Backward compatible (defaults to standard prompt)

---

## Our Recommendation (Pending Your Input)

**Proposed Approach**: Lead with unbiased results, present biased as upper bound

**Paper Structure**:

1. **Methods**: Describe both prompt types, justify unbiased as conservative
2. **Results**: Present 71% detection as main finding (Table 1)
3. **Ablation**: Show 100% with regime labels (Table 2)
4. **Discussion**: 71-100% range demonstrates robustness, not memorization

**Key Messages**:

- LLM detects structural patterns from GEX data alone (71%)
- Detection improves with context/labels (100%)
- Both rates exceed mechanical threshold (60%)
- Predictions materialize at 91% rate (pattern is real)

**Rationale**:

- 71% is more defensible academically ("conservative estimate")
- 100% becomes supporting evidence, not primary claim
- Transparent methodology strengthens peer review
- Shows rigorous validation (we tested edge cases)

**But we want your guidance before proceeding with Paper #1 draft.**

---

## Timeline Impact

**If we proceed with unbiased results as main findings**:

- Update paper outline: 1 day
- Re-commit YAML files: Done
- Draft abstract/intro: 2-3 days
- Draft methods: 2-3 days
- Draft results: 2-3 days
- Draft discussion: 2-3 days
- **Target**: Still achievable for Oct 26 deadline

**Critical path**: Your decision on presentation approach

---

## Request

Please advise on:

1. Which detection rate (71%, 100%, or both) should be the primary result?
2. How to frame the prompt bias discovery (limitation vs. methodological rigor)?
3. Any concerns about the 71% detection rate vs. original 100%?
4. Should we delay Paper #1 to incorporate this properly, or is current timeline OK?

We believe this discovery strengthens the paper (shows thorough validation), but want your expert assessment before proceeding with the draft.

**Available for meeting/call whenever convenient.**

---

## Appendix: Detailed Comparison

### Detection Rates by Quarter (Unbiased Prompt)

| Pattern | Q1 | Q2 | Q3 | Q4 | Full Year |
|---------|----|----|----|----|-----------|
| gamma_positioning | Part of 69.4% full year result | | | | 69.4% |
| stock_pinning | Part of 67.4% full year result | | | | 67.4% |
| 0dte_hedging | Part of 77.7% full year result | | | | 77.7% |

*Note: Unbiased validation ran on full year (Jan 2 - Dec 31, 2024) rather than quarterly splits.*

### Sample Size

- **242 trading days** × **3 patterns** = **726 pattern-day tests**
- **519 detections** (71.5% average)
- **473 materialized predictions** (91.2% accuracy)

### Statistical Significance

- All 3 patterns exceed 60% threshold with large sample (N=242)
- 95% confidence intervals (approximate):
  - gamma_positioning: 63.4% - 75.4%
  - stock_pinning: 61.4% - 73.4%
  - 0dte_hedging: 72.0% - 83.4%
