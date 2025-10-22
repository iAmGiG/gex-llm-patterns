# System Flow - Visual Guide

**NOTE**: This document describes the METHODOLOGY and CODE FLOW. Actual validation results (detection rates, accuracy metrics, etc.) are stored on HPCC and documented in validation reports.

## The Complete Validation Pipeline (Simplified)

### Overview: Three Main Components

```bash
┌─────────────────────────────────────────────────────────────┐
│                    1. PATTERN LIBRARY                       │
│              (src/analysis/pattern_library.py)              │
│                                                             │
│  various Market Mechanics Patterns with WHO → WHOM → WHAT   │
│  - Gamma Positioning (Traditional)                          │
│  - Stock Pinning (Open Interest)                            │
│  - 0DTE Hedging (Intraday)                                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 2. MARKET MECHANICS AGENT                   │
│            (src/agents/market_mechanics_agent.py)           │
│                                                             │
│  Fetches Data → Calculates GEX → Obfuscates → Asks LLM      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                  3. VALIDATION PIPELINE                     │
│         (scripts/validation/validate_pattern_taxonomy.py)   │
│                                                             │
│  Tests Multiple Days → Measures Detection → Calculates Outcomes│
│  Generates: reports/validation/pattern_taxonomy/*.yaml      │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Flow: Single Day Analysis

### Step-by-Step Process

**Note**: Values shown below are ILLUSTRATIVE EXAMPLES to demonstrate data flow, not actual research results.

```bash
INPUT: "Test gamma_positioning pattern on SPY for 2024-01-05"
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: FETCH OPTIONS DATA                                  │
│                                                             │
│ Source: cache/options/SPY/2024-01-05.pickle                 │
│ Contains: All options contracts (strikes, prices, OI, IV)   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: CALCULATE GEX METRICS                               │
│ (src/gex/gex_calculator.py)                                 │
│                                                             │
│ Calculates:                                                 │
│   • Net GEX: -$5.2B                                         │
│   • Flip Point: $548.00                                     │
│   • Call Gamma: +$2.1B                                      │
│   • Put Gamma: -$7.3B                                       │
│   • Gamma Concentration: 78% at $555 strike                 │
│   • Spot Price: $552.10                                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: OBFUSCATE DATA                                      │
│ (src/validation/data_obfuscation.py)                        │
│                                                             │
│ BEFORE:                    AFTER:                           │
│   Date: 2024-01-05    →    Date: Day T+0                    │
│   Symbol: SPY         →    Symbol: INDEX_1                  │
│   [Remove all events]                                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: BUILD LLM PROMPT                                    │
│ (src/llm/mechanics_prompt_builder.py)                       │
│                                                             │
│ "Analyze INDEX_1 gamma exposure on Day T+0:                 │
│  - Net GEX: -$5.2B (negative gamma regime)                  │
│  - Flip point: $548 (current price: $552)                   │
│  - Call gamma concentration: 78% at $555 strike             │
│  Focus on: WHO is forcing WHOM to do WHAT?"                 │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: LLM ANALYSIS                                        │
│ (src/llm/autogen_market_mechanics.py)                       │
│                                                             │
│ LLM Response:                                               │
│   WHO: "Dealers with negative gamma exposure"               │
│   WHOM: "Market participants"                               │
│   WHAT: "Force dealers to sell into rallies and buy dips,   │
│          amplifying volatility"                             │
│   CONFIDENCE: 85%                                           │
│   TIME_HORIZON: "1-3 days"                                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: CALCULATE OUTCOMES                                  │
│ (src/validation/outcome_calculator.py)                      │
│                                                             │
│ Measures:                                                   │
│   • T+1 Price (forward return calculation)                  │
│   • Realized Volatility (amplification check)               │
│   • Prediction Materialization (boolean verification)       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: RECORD RESULT                                       │
│                                                             │
│ detection:                                                  │
│   date: [actual date]                                       │
│   date_obfuscated: Day T+0                                  │
│   detected: [boolean] (confidence > threshold?)             │
│   obfuscation_verified: [boolean]                           │
│   narrative:                                                │
│     who: [actor identification]                             │
│     whom: [counterparty identification]                     │
│     what: [mechanism description]                           │
│   outcome_metrics:                                          │
│     forward_1d_return_pct: [calculated return]              │
│     prediction_materialized: [boolean]                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Batch Processing: Full Quarter Validation

### Efficient Multi-Day Analysis

```bash
INPUT: "Validate [pattern_name] for [date_range]"
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ DATA COVERAGE CHECK (Issue #84 fix)                         │
│                                                             │
│ Expected trading days: [calculated from business calendar]  │
│ Available in cache: [count of cached data files]            │
│ Coverage: [percentage] (threshold: ≥80%)                    │
│                                                             │
│ IF <80%: FAIL FAST to prevent selection bias                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ BATCH PROCESSING (configurable batch size)                  │
│                                                             │
│ Batch 1: [date_start...date_end] (N days)                   │
│   → Obfuscate all N dates at once                           │
│   → Single LLM API call for batch                           │
│   → Significant cost reduction vs individual calls          │
│                                                             │
│ Batch 2: [next batch dates]                                 │
│ ...                                                          │
│ Batch K: [remaining dates]                                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ AGGREGATE METRICS                                           │
│                                                             │
│ Calculated per quarter/period:                              │
│   • Total days tested                                       │
│   • High-confidence detections (>= threshold)               │
│   • Detection rate (% of days detected)                     │
│   • Predictive accuracy (% predictions materialized)        │
│   • Average forward returns                                 │
│   • Net alpha (after transaction costs)                     │
│                                                             │
│ VERDICT: MECHANICAL or NARRATIVE (based on thresholds)      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ SAVE YAML REPORT                                            │
│                                                             │
│ File: reports/validation/pattern_taxonomy/                  │
│       [pattern]_[symbol]_[period].yaml                      │
│                                                             │
│ Contains:                                                   │
│   - Test metadata (dates, coverage, thresholds)             │
│   - Performance metrics (detection, accuracy, alpha)        │
│   - Obfuscation test verdict                                │
│   - All daily-level detection results                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Multi-Quarter Validation: Methodology

### How Multi-Pattern Testing Works

```bash
N PATTERNS × M QUARTERS = N×M VALIDATION RUNS

┌─────────────────────────────────────────────────────────────┐
│ PATTERN 1: [pattern_name]                                   │
├─────────────────────────────────────────────────────────────┤
│ Period 1: [date_range] → [pattern]_[symbol]_[period].yaml   │
│ Period 2: [date_range] → [pattern]_[symbol]_[period].yaml   │
│ Period 3: [date_range] → [pattern]_[symbol]_[period].yaml   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PATTERN 2: [pattern_name]                                   │
├─────────────────────────────────────────────────────────────┤
│ Period 1: [date_range] → [pattern]_[symbol]_[period].yaml   │
│ Period 2: [date_range] → [pattern]_[symbol]_[period].yaml   │
│ Period 3: [date_range] → [pattern]_[symbol]_[period].yaml   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PATTERN K: [pattern_name]                                   │
├─────────────────────────────────────────────────────────────┤
│ Period 1: [date_range] → [pattern]_[symbol]_[period].yaml   │
│ Period 2: [date_range] → [pattern]_[symbol]_[period].yaml   │
│ Period 3: [date_range] → [pattern]_[symbol]_[period].yaml   │
└─────────────────────────────────────────────────────────────┘

TOTAL: Multiple trading days analyzed with obfuscation testing
```

### Command Structure (Reproducible)

```bash
# General validation command format
python scripts/validation/validate_pattern_taxonomy.py \
  --pattern [PATTERN_NAME] \
  --symbol [SYMBOL] \
  --start-date [YYYY-MM-DD] \
  --end-date [YYYY-MM-DD] \
  --with-outcomes

# Example usage for multiple patterns across quarters:
# Run for each pattern × quarter combination
# Results stored in reports/validation/pattern_taxonomy/
```

---

## Data Flow: From Raw Options to Research Conclusion

### The Complete Journey

```bash
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 1: DATA COLLECTION                                         │
│                                                                  │
│ Source: Options data API (Polygon, Alpha Vantage, etc.)          │
│ Stored: cache/options/SPY/YYYY-MM-DD.pickle                      │
│ Contains: Strike, Price, OI, IV, Greeks for all contracts        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 2: GEX CALCULATION                                         │
│ (src/gex/gex_calculator.py)                                      │
│                                                                  │
│ Formulas:                                                        │
│   Call GEX = Σ(call_gamma × OI × 100 × spot²)                    │
│   Put GEX = Σ(put_gamma × OI × 100 × spot²) × -1                 │
│   Net GEX = Call GEX + Put GEX                                   │
│   Flip Point = Strike where net GEX crosses zero                 │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 3: PATTERN MATCHING                                        │
│ (src/analysis/pattern_library.py)                                │
│                                                                  │
│ Pattern: gamma_positioning                                       │
│ Criteria Check:                                                  │
│   ✓ Net GEX < -$2B? (Yes: -$5.2B)                                │
│   ✓ Price within 2% of flip point? (Yes: $552 vs $548)           │
│   ✓ Heavy call OI above price? (Yes: 78% at $555)                │
│ Result: Pattern matches → proceed to LLM analysis                │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 4: OBFUSCATION (CRITICAL FOR RESEARCH)                     │
│ (src/validation/data_obfuscation.py)                             │
│                                                                  │
│ Transformation:                                                  │
│   2024-01-05, SPY, Net GEX -$5.2B                                │
│   ↓                                                              │
│   Day T+0, INDEX_1, Net GEX -$5.2B                               │
│                                                                  │
│ Why: Prevents LLM from using training data memorization          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 5: LLM INTERPRETATION                                      │
│ (src/agents/market_mechanics_agent.py)                           │
│                                                                  │
│ Prompt: "Analyze INDEX_1 on Day T+0 with negative gamma..."      │
│ LLM: "Dealers forced to hedge by selling into rallies..."        │
│ Structured Output: WHO/WHOM/WHAT + confidence score              │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 6: OUTCOME VERIFICATION                                    │
│ (src/validation/outcome_calculator.py)                           │
│                                                                  │
│ Measures:                                                        │
│   T+1 price movement (did prediction materialize?)               │
│   Realized volatility (was it amplified as predicted?)           │
│   Returns (what was the economic outcome?)                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 7: VALIDATION REPORT                                       │
│ (scripts/validation/validate_pattern_taxonomy.py)                │
│                                                                  │
│ Aggregates metrics across all tested dates:                      │
│   • Detection Rate (% days with confident detection)             │
│   • Predictive Accuracy (% predictions materialized)             │
│   • Net Alpha (avg returns - transaction costs)                  │
│   • Verdict: MECHANICAL or NARRATIVE (threshold-based)           │
│                                                                  │
│ Saves: [pattern]_[symbol]_[period].yaml                          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│ STAGE 8: ACADEMIC ANALYSIS                                       │
│                                                                  │
│ Research Question: Can LLMs understand market mechanics?         │
│ Evidence: Validation results across multiple patterns/periods    │
│ Analysis: Compare detection vs profitability independence        │
│                                                                  │
│ Novel Contribution: Obfuscation testing framework                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key Validation Checkpoints

### What Makes This Research Rigorous

```bash
CHECKPOINT 1: DATA COVERAGE (Issue #84)
├─ Expected trading days calculated from business calendar
├─ Available data verified in cache
├─ Coverage ≥80% required or FAIL FAST
└─ Prevents: Selection bias from incomplete data

CHECKPOINT 2: OBFUSCATION VERIFICATION
├─ All dates → "Day T+N" format
├─ All tickers → Generic symbols
├─ All events → Removed
└─ Prevents: LLM using training data memorization

CHECKPOINT 3: DETECTION THRESHOLD
├─ Confidence ≥60% required for "detected"
├─ Based on taxonomy validation criteria
├─ Sample size ≥30 days for statistical significance
└─ Prevents: Cherry-picking low-confidence results

CHECKPOINT 4: OUTCOME VERIFICATION
├─ Forward returns calculated from real prices
├─ Realized volatility measured objectively
├─ Prediction materialization verified rule-based
└─ Prevents: Subjective outcome interpretation

CHECKPOINT 5: REPRODUCIBILITY
├─ All results saved in YAML with metadata
├─ Commands documented for re-running
├─ Cache ensures same data across runs
└─ Enables: Independent verification by reviewers
```

---

## Common Pitfalls Avoided

### How This Research Differs from Flawed Approaches

```bash
❌ PITFALL 1: Training Data Leakage
Problem: LLM memorizes "GameStop January 2021"
Our Solution: Obfuscation testing removes all temporal context
Result: LLM must reason from mechanics, not memory

❌ PITFALL 2: Cherry-Picking Dates
Problem: Only test days when patterns were profitable
Our Solution: Issue #84 enforces ≥80% data coverage
Result: Test ALL available days, not selected subset

❌ PITFALL 3: Overfitting to Profitability
Problem: Only validate "patterns that work"
Our Solution: Test across Q1 (profitable), Q3/Q4 (not profitable)
Result: Detection independent of economic outcome

❌ PITFALL 4: Single Pattern Testing
Problem: Can't prove generalization with one example
Our Solution: Test 3 different dealer hedging manifestations
Result: Same methodology works across pattern types

❌ PITFALL 5: Subjective Outcome Measurement
Problem: "Did the pattern work?" is ambiguous
Our Solution: Rule-based verification (forward returns, realized vol)
Result: Reproducible outcome calculation

❌ PITFALL 6: Insufficient Sample Size
Problem: 10-20 days isn't statistically significant
Our Solution: Minimum 30 days per test (taxonomy criteria)
Result: 53-64 days per quarter validation
```

---

## Quick Reference: How Metrics Are Calculated

### Metric Definitions and Calculation Methods

```bash
DETECTION RATE
├─ Definition: % of days where pattern detected (confidence ≥60%)
├─ Threshold: ≥60% for MECHANICAL status (<60% = NARRATIVE)
├─ Calculation: (days_detected / total_days_tested) × 100%
└─ Purpose: Measure consistency of LLM pattern recognition

PREDICTIVE ACCURACY
├─ Definition: % of predictions that materialized
├─ Measurement: Rule-based verification (forward returns, realized vol)
├─ Calculation: (predictions_correct / predictions_made) × 100%
└─ Purpose: Verify LLM predictions against actual outcomes

NET ALPHA
├─ Definition: Average return minus transaction costs
├─ Transaction Costs: Typically 5 basis points (0.05%) per trade
├─ Calculation: mean(forward_returns) - 0.0005
└─ Purpose: Economic viability assessment (not research validity)

OBFUSCATION TEST
├─ Definition: Detection rate maintained with obfuscated data
├─ Method: Strip dates/symbols, present only GEX metrics
├─ Pass Criteria: Detection rate ≥ threshold with obfuscation
└─ Purpose: Proves structural detection (not memorization)

DATA COVERAGE CHECK
├─ Definition: % of expected trading days with available data
├─ Threshold: ≥80% required (prevents selection bias)
├─ Calculation: (available_dates / expected_dates) × 100%
└─ Purpose: Ensure statistical validity, not cherry-picking
```

---

## Data Verification Checklist

**Before sharing validation results with stakeholders:**

1. ✓ Database spot prices verified (not obfuscated values like 450.0)
2. ✓ Forward returns are physically plausible (typically <5% for SPY)
3. ✓ Data coverage ≥80% for all tested periods
4. ✓ YAML reports exist for all claimed validations
5. ✓ Obfuscation properly applied (dates → "Day T+N", symbols → generic)

**This is a methodology guide - actual results stored on HPCC**

---

This visual guide complements the main briefing document with clear flow diagrams and checkpoint explanations. Use this for demonstrating the system architecture during your presentation!
