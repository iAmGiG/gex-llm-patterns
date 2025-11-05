# Paper #2: Sequential GEX Analysis (Temporal Dynamics)

**Status**: Phase 1 Complete, Phase 2 **BLOCKED** (Test 4 required)
**Target**: Journal submission Q1 2026 (6-8 pages)
**Branch**: `paper2-sequential-gex`
**Dependency**: Paper #1 acceptance
**Issues**: #89, #107, #108, #110, **#111 (CRITICAL - Test 4)**

---

## Quick Navigation

### Start Here

- **New to Paper #2?** → Read [Research Question](#research-question) below
- **Need design decisions?** → See [ADRs](#architecture-decision-records-adr) (stable references)
- **Want implementation history?** → See [Session Logs](#session-logs) (chronological work)
- **Checking methodology?** → See [Methodology](#methodology-validation) (rigor validation)

### File Organization

```
paper2/
├── README.md                              # This file (navigation hub)
├── adr/                                   # Architecture Decision Records (STABLE)
│   ├── 001-scope-boundaries.md            # What's in/out of scope
│   ├── 002-sequential-pattern-rules.md    # 4 pattern types defined
│   ├── 003-outcome-thresholds.md          # Verification criteria
│   ├── 004-comparative-framework.md       # Statistical comparison approach
│   ├── 005-prompt-design.md               # Prompt architecture (original + neutral)
│   ├── 006-sequential-gex-architecture.md # Sequential data fetching design
│   └── 007-agent-architecture-analysis.md # LLM agent framework decisions
├── methodology/                           # Research Methodology (EVOLVING)
│   ├── negative_controls_design.md        # 3-test validation plan (ready to run)
│   └── prompt_bias_mitigation.md          # Bias analysis + neutral framework
├── sessions/                              # Session Logs (CHRONOLOGICAL)
│   ├── 2025-11-03_implementation.md       # Phase 1 implementation
│   └── 2025-11-04_phase1_completion.md    # Bug fixes + proof-of-concept
├── drafts/                                # Paper drafts
├── figures/                               # Result figures
├── tables/                                # LaTeX tables
└── latex/                                 # LaTeX source
```

---

## Research Question

Can LLMs detect dealer constraint **trajectories** over time, not just single-day snapshots?

**Current Approach** (Paper #1):

- Single-day GEX snapshot at Day T
- Predict Day T+1 outcome
- LLM sees: "Net GEX = -$5.2B on Day T"

**Extension** (Paper #2):

- 5-day GEX sequence (Days T-4 → T-3 → T-2 → T-1 → T+0)
- Predict Day T+1 outcome with trajectory context
- LLM sees: "GEX escalating: -$2.1B → -$3.2B → -$4.1B → -$4.8B → -$5.2B"

---

## Architecture Decision Records (ADR)

These are **stable decisions** that define the framework. Read these for authoritative design choices.

| ADR | Topic | Purpose | Status |
|-----|-------|---------|--------|
| [001](adr/001-scope-boundaries.md) | Scope Boundaries | What's in/out of Paper #2 | ✅ Accepted |
| [002](adr/002-sequential-pattern-rules.md) | Pattern Rules | 4 trajectory types defined | ✅ Accepted |
| [003](adr/003-outcome-thresholds.md) | Outcome Thresholds | P75/P25 verification criteria | ✅ Accepted |
| [004](adr/004-comparative-framework.md) | Comparative Framework | Statistical comparison methodology | ✅ Accepted |
| [005](adr/005-prompt-design.md) | Prompt Design | Prompt architecture (original + neutral) | ✅ Accepted (revised Nov 4) |
| [006](adr/006-sequential-gex-architecture.md) | Sequential GEX Fetcher | 5-day window retrieval design | ✅ Accepted |
| [007](adr/007-agent-architecture-analysis.md) | Agent Framework | LLM agent architecture decisions | ✅ Accepted |

---

## Methodology (Validation)

These documents validate the rigor of the research methodology.

| Document | Purpose | Status |
|----------|---------|--------|
| [prompt_bias_mitigation.md](methodology/prompt_bias_mitigation.md) | Bias analysis + neutral framework | ✅ Implementation complete |
| [negative_controls_design.md](methodology/negative_controls_design.md) | 4-test validation framework | ⚠️ **PARTIAL** (Tests 1-3 complete, Test 4 required) |

**Negative Controls Results**:
1. ✅ Prompt comparison: 80% neutral vs 100% leading (conservative calibration)
2. ✅ Random synthetic GEX: 20% false positives (passed <30% threshold)
3. ✅ Zero-GEX: 0% false positives (passed <10% threshold)
4. ⚠️ **Low-GEX: PENDING** (Issue #111 - CRITICAL)

**Q1 2024 Validation**: 61 windows, **100% detection rate**

**Critical Issue Identified** (Nov 4, 2025):
- Q1 had zero weak GEX periods (all windows >$5B avg)
- Tests 1-3 validated rejection of synthetic/zero-GEX
- **Missing**: Test discrimination on realistic but weak GEX periods
- **User concern**: "100% will be called out by reviewers"

**Test 4 Required** (Issue #111):
- Dataset: 10-20 synthetic windows with $1-3B GEX (realistic but weak)
- Pass criteria: <50% detection rate
- Purpose: Prove LLM can discriminate pattern strength, not just synthetic/zero

**Key Finding**: Mechanical confidence guidance reduced false positives by **60%** (v3a: 20% FP vs v3b: 50% FP)

**Decision**: ⚠️ **PROVISIONAL** - v3a passed Tests 1-3, but Test 4 required before Phase 2

---

## Session Logs (Chronological)

Development history in chronological order. Read these to understand how the project evolved.

| Date | Session | What Happened |
|------|---------|---------------|
| [Nov 3](sessions/2025-11-03_implementation.md) | Phase 1 Implementation | Built SequentialGEXFetcher, validation script, unit tests (2,800 lines) |
| [Nov 4](sessions/2025-11-04_phase1_completion.md) | Bugs + Rigor Analysis | Fixed 3 critical bugs, created neutral framework, negative controls ready |

---

## New Pattern Types (Sequential)

**1. Gamma Accumulation**

- Definition: Net GEX magnitude increasing over time
- Example: -$2B → -$3B → -$4B → -$5B (escalating)
- Prediction: Amplified volatility when pressure releases

**2. Gamma Relief**

- Definition: Net GEX magnitude decreasing over time
- Example: -$5B → -$4B → -$3B → -$2B (de-escalating)
- Prediction: Volatility suppression as constraints ease

**3. Gamma Reversal**

- Definition: Net GEX flips sign over time
- Example: -$3B → -$1B → +$0.5B → +$2B (flip)
- Prediction: Volatility regime shift

**4. Persistent Constraint**

- Definition: Net GEX remains large and stable
- Example: -$5B → -$4.9B → -$5.1B → -$5.2B (sustained)
- Prediction: Volatility stays elevated

**See**: [adr/002_sequential_pattern_rules.md](adr/002_sequential_pattern_rules.md) for formal definitions

---

## Phase 1 Results (Proof-of-Concept)

**Status**: ✅ Complete (Nov 4, 2025)

**Tested**: 120 windows (Jan 8 - Jul 3, 2024)

**Results**:
- Detection rate: 100% (120/120)
- Confidence range: 70-85%
- Model: o4-mini-2025-04-16
- Data quality: Real GEX values verified ($8-14B range)

**Trajectory Distribution**:
- Persistent: 60% (most common in 2024 negative GEX regime)
- Accumulation: 25%
- Relief: 10%
- Reversal: 5% (rare - 2024 was 100% negative GEX)

**Interpretation**: 100% detection likely reflects market reality (dealer constraints present daily in 2024), but must validate with negative controls before concluding.

---

## Next Steps

### Immediate (Ready Now)

1. **Run negative controls**:
   ```bash
   python scripts/validation/validate_p2_negative_controls.py --all
   ```

2. **Analyze results**: Check `reports/validation/paper2/negative_controls_*.yaml`

3. **Make go/no-go decision**:
   - If ALL PASS → Proceed to Phase 2 validation
   - If ANY FAIL → Iterate on methodology

### Phase 2 Scope Options

| Option | Windows | Timeline | Pros | Cons |
|--------|---------|----------|------|------|
| **A: Q1 Only** | 60 | 1 week | Fast, matches Paper #1 | Limited regime variation |
| **B: Full 2024** | 249 | 3-4 weeks | Comprehensive | Long timeline, high API cost |
| **C: Q1 + Q3** | 124 | 2 weeks | Balanced | Mixed approach |

**Decision**: Pending negative control results

---

## Implementation Details

### Dataset

- **Symbol**: SPY (same as Paper #1)
- **Period**: 2024 (Q1, Q3, Q4 validated)
- **Windows**: 169 5-day sequences (242 days - 4 day warmup per quarter)

### Obfuscation (Maintained)

- Dates: "Day T-4", "Day T-3", ..., "Day T+0" (no real dates)
- Ticker: "INDEX_1" (no "SPY")
- Context: No events, VIX, news

### Validation Script

**Script**: `scripts/validation/validate_p2_sequential_patterns.py`

**Usage**:
```bash
python scripts/validation/validate_p2_sequential_patterns.py \
  --start-date 2024-01-08 \
  --end-date 2024-03-29 \
  --output-dir reports/validation/paper2
```

---

## Expected Outcomes

**Scenario 1: Sequential Improves (Best Case)**

- Accuracy: 96% → 98% (+2pp)
- Confidence: 72% → 85% on persistent patterns
- **Action**: Paper #2 standalone journal submission

**Scenario 2: Sequential Neutral**

- Accuracy: 96% → 96% (no change)
- **Action**: Fold into Paper #3 discussion section

**Scenario 3: Sequential Worse**

- Accuracy: 96% → 92% (-4pp)
- **Action**: Revert to single-day, document in limitations

---

## Related Work

**Paper #1**: Single-day explanatory framework (submitted Oct 26, 2025)
- Detection rate: 100%
- Accuracy: 87-98%
- Net alpha: Declined Q1→Q4 (proves detection ≠ profit optimization)

**Paper #3** (Future): Cross-asset extension (SPY → QQQ, IWM)

---

## GitHub Issues

- **#89**: Sequential GEX Analysis - Paper #2 Extension
- **#107**: Implementation progress tracking
- **#108**: Phase 1 completion and rigor validation

---

## Contact & Collaboration

- **Primary Investigator**: [Your Name]
- **Advisor**: [Advisor Name]
- **Branch**: `paper2-sequential-gex`
- **Timeline**: Start after Paper #1 acceptance (Jan 2026), submit Q1 2026

---

**Last Updated**: November 4, 2025
