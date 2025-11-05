# Paper #2 Scope Boundaries

**Date**: 2025-11-01
**Purpose**: Define what's IN vs OUT of scope for Paper #2 to prevent mission creep

---

## Paper #2 Identity: Pure Computer Science ✅

**Title**: "Temporal Dynamics of LLM-Based Market Microstructure Detection"

**Core Claim**: LLMs detect multi-day constraint evolution (WHEN), not just snapshots

**Primary Metrics**:

- Detection rate (%)
- Predictive accuracy (%)
- Pattern prevalence across regimes

**Secondary Metrics** (for transparency only):

- Net alpha (transaction-cost adjusted returns)
- Reported but de-emphasized: "Pattern detected but economically marginal"

---

## IN SCOPE ✅

### 1. Sequential Pattern Detection (Core)

- 4 pattern types: Accumulation, Relief, Reversal, Persistent
- 5-day rolling windows (advisor-suggested)
- Multi-year validation (2023, 2024, 2025)
- Conservative thresholds (P75/P25)

**⚠️ Reversal Pattern Limitation (2024 Data):**

- **Problem**: 2024 SPY had 100% negative GEX regime (no sign flips)
- **Occurrence**: 0% in 2024 baseline data (0 out of 248 windows)
- **Solution**: Implement detection logic, document limitation, defer testing
- **Strategy**:

  ```yaml
  phase_1_2024:
    patterns_tested: [Accumulation, Relief, Persistent]
    patterns_implemented: [Accumulation, Relief, Reversal, Persistent]
    reversal_status: "Code complete, 0% occurrence, untestable"
    documentation: "Single-regime limitation noted in paper"

  phase_2_multi_year:
    patterns_tested: [Accumulation, Relief, Reversal, Persistent]
    reversal_status: "Testable when 2023/2025 data added (expect 2-5% occurrence)"
  ```

- **Academic Handling**:
  - Include Reversal in pattern taxonomy (complete framework)
  - Report: "Reversal pattern: 0% occurrence in 2024 single-regime data"
  - Defer empirical validation to multi-year extension
  - Sets up natural Phase 2 motivation ("test all 4 patterns across regimes")
- **Why NOT Redefine**: Reversal = sign flip is theoretically meaningful; magnitude-based alternative would be different pattern type

### 2. Robustness Checks (Appendix)

- Window size sensitivity (3-day, 7-day vs 5-day baseline)
- Threshold sensitivity (P66/P33 moderate, P90/P10 aggressive)
- Regime-specific detection rates (low/medium/high vol)

### 3. Alpha Tracking (Transparency)

- Same methodology as Paper #1
- Report net alpha (+5-7 bps expected)
- Interpretation: "Structural understanding ≠ trading profitability"

**Why**: Consistency with Paper #1, reviewer expectations

---

## OUT OF SCOPE 🚫

### 1. Strike-Level Analysis (DEFERRED to Paper #3)

**What**: Analyze individual strikes vs aggregate GEX
**Why defer**:

- Adds complexity without clear Paper #2 benefit
- Better suited for Paper #3 (equity applications)
- Already documented as Paper #1 limitation

**GH Issue**: #111 (Future Work)

### 2. Context-Aware Analysis (DEFERRED to Paper #4+)

**What**: Combine GEX with VIX, volume, news
**Why defer**:

- Breaks obfuscation testing constraint
- Moves away from "structural reasoning" claim
- Different research question ("does context help?")

**GH Issue**: #113 (Future Work)

### 3. Strike-Level Alpha Backtest (OUT OF SCOPE)

**What**: Trade individual strikes/options (not index)
**Why exclude**:

- Scope creep: CS → Quantitative Finance
- Requires options pricing, execution models
- Overfitting risk (1000s of strikes)
- Mission drift: "Does LLM understand?" → "Can we make money?"

**GH Issue**: #115 (Deferred to Paper #3)

**Advisor's warning**: This is a rabbit hole

---

## OPTIONAL (If Time Permits)

### 1. Window Size Sensitivity Analysis

**Status**: LOW priority for Paper #2 appendix
**Effort**: 1-2 days (run 3-day and 7-day on 50-day sample)
**Value**: Robustness check (show results stable across windows)

**GH Issue**: #112

### 2. Regime-Specific Detection Rates

**Status**: MEDIUM priority (include if fast test succeeds)
**Effort**: 1 day (classify days by VIX, report detection by regime)
**Value**: "Pattern persistence across regimes" discussion point

**GH Issue**: #114

---

## Decision Framework

**When someone suggests a new analysis**:

1. **Does it test temporal reasoning?** → YES = Consider for Paper #2
2. **Does it add trading complexity?** → YES = Defer to Paper #3+
3. **Does it break obfuscation?** → YES = Different paper (Paper #4+)
4. **Does it improve CS contribution?** → NO = Out of scope

---

## The Trading vs CS Tension 💰

**Question**: Should we optimize for alpha or detection accuracy?

**Answer**: Detection accuracy (CS), report alpha (transparency)

**Why**:

- Paper #1 precedent: 95.9% detection + 5.6 bps alpha = "Structural understanding ≠ profitability"
- Paper #2 follows same logic: High detection + marginal alpha = Validates LLM reasoning, not trading edge
- Switching to alpha optimization = Different paper (quantitative finance, not CS)

**Key Insight**: If detection is high but alpha is low, that's GOOD for our claim

- Proves LLM understands mechanics (detects constraints)
- Proves we're not p-hacking for returns (not overfitting)
- Strengthens "no memorization" argument (not exploiting training data)

---

## Recommended Commit Message

```bash
Add Paper #2 scope boundaries to prevent mission creep

IN SCOPE:
- Sequential pattern detection (4 types, 5-day windows)
- Multi-year validation (2023-2025)
- Robustness checks (window/threshold sensitivity)
- Alpha tracking (transparency, de-emphasized)

OUT OF SCOPE:
- Strike-level analysis (Paper #3)
- Context-aware features (Paper #4+)
- Options trading strategies (quantitative finance)

Decision framework: Optimize for CS contribution (detection accuracy)
not trading performance (alpha generation). Report alpha for transparency
but interpret as "structural understanding ≠ profitability" per Paper #1.

Related Issues: #111, #112, #113, #114, #115 (future work)
```

---

## References

**Related Documents**:

- `outcome_verification_thresholds.md` - Empirical thresholds for pattern verification
- `sequential_pattern_detection_rules.md` - Algorithmic detection rules

**Related Issues**:

- #107: Paper #2 Sequential GEX Analysis (main issue)
- #111: Strike-Level Analysis (deferred)
- #112: Window Size Sensitivity (optional)
- #113: Context-Aware Analysis (deferred)
- #114: Regime-Specific Analysis (optional)
- #115: Strike-Level Alpha Backtest (out of scope)

**Last Updated**: 2025-11-01
