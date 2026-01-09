# Abandoned Research Paths

This document records research directions that were explored but ultimately abandoned, along with the rationale for discontinuation. Maintaining this record helps prevent redundant investigation and provides context for future researchers.

## Evaluation Criteria for Research Viability

Before abandoning a research path, we assess:

1. **Data Availability** - Is the required data accessible at reasonable cost?
2. **Signal Frequency** - Are there enough observable events for statistical significance?
3. **Scope Alignment** - Does the research align with project goals (GEX-based LLM pattern detection)?
4. **Technical Feasibility** - Can we implement the required analysis with available tools?
5. **Time-to-Value** - Is the effort justified by expected insights?

---

## #13: Short Put Arbitrage Pattern Detection

**Status:** Closed as "not planned"
**GitHub Issue:** [#13](https://github.com/vli777/gex-llm-patterns/issues/13)
**Date Abandoned:** January 2026

### Original Concept

Detect anomalous short put activity through options chain analysis that could indicate:

- Dealer hedging pressure from concentrated short put positions
- Volatility selling strategies creating gamma exposure buildups
- Potential squeeze setups from accumulated short gamma

### Why It Was Abandoned

#### 1. Data Requirements Exceed Available Sources

The pattern requires data we cannot obtain:

| Required Data | Purpose | Availability |
|---------------|---------|--------------|
| Fill-side TAQ data | Determine trade initiator (buyer vs seller) | Unavailable (expensive institutional feeds) |
| 0DTE SPX options | Where short put arbitrage actually occurs | Not collected in current pipeline |
| Real-time order flow | Distinguish aggressive vs passive fills | Unavailable |
| Dealer positioning data | Validate hedge pressure hypothesis | Proprietary/unavailable |

#### 2. Signal vs Noise Problem

Even with complete data:

- Short puts are the most common options strategy (covered puts, cash-secured puts, vol selling)
- Distinguishing "arbitrage" from normal activity requires fill-side context
- Without knowing who initiated the trade, we cannot infer positioning intent

#### 3. Scope Misalignment

This pattern detection would require:

- Building a separate 0DTE data collection pipeline
- Purchasing TAQ data feeds ($10K+/year)
- Developing order flow classification algorithms

This exceeds the scope of LLM-based GEX pattern interpretation.

### What Would Make This Viable

If in the future:

1. **0DTE SPX data becomes available** in our collection pipeline
2. **Fill-side indicators** become accessible through public APIs
3. **Dealer positioning reports** become available (e.g., CFTC-style reporting for options)

Then this research path could be reconsidered.

### Related Work

- Issue #179: Leveraged ETF data collection (addresses some data gaps)
- Issue #180: SQLite migration (scalable storage for expanded data)
- `docs/reference/auxiliary_research/practitioner_methods.md` - Practitioner data sources

---

## Template for Future Entries

When abandoning a research path, document:

```markdown
## #[Issue Number]: [Research Topic]

**Status:** Closed as "not planned"
**GitHub Issue:** [#XXX](link)
**Date Abandoned:** [Month Year]

### Original Concept
[Brief description of what we hoped to achieve]

### Why It Was Abandoned
[Specific reasons with evidence]

### What Would Make This Viable
[Conditions under which to reconsider]

### Related Work
[Links to related issues or documentation]
```

---

## Partially Implemented (Deferred)

Research that was started but not fully completed due to scope prioritization.

---

## #11: Monte Carlo & Permutation Testing Framework

**Status:** Partially implemented, full framework deferred
**GitHub Issue:** [#11](https://github.com/iAmGiG/gex-llm-patterns/issues/11)
**Date Closed:** September 2025

### Original Concept

Comprehensive statistical validation framework including:

- Permutation testing with 10,000+ iterations for pattern significance
- False Discovery Rate (FDR) corrections (Benjamini-Hochberg)
- Temporal stability testing across rolling windows
- Market regime robustness analysis (4+ regimes: COVID crash, recovery, rate hikes, normalization)
- Monte Carlo simulations for confidence intervals
- Data mining bias detection

### What Was Implemented

Basic statistical validation was completed:

- Wilson confidence intervals for pattern accuracy
- Sharpe ratio and Calmar ratio calculations
- Kelly Criterion position sizing
- Baseline comparison (proved +10.44% edge over random)
- Sample size validation (7 trades meeting minimum threshold)

### What Was NOT Implemented

- **10,000+ iteration permutation tests** - Not done
- **Full Monte Carlo simulations** - Only bootstrap CI, not full MC
- **FDR correction** - Multiple testing adjustment not implemented
- **4-regime robustness analysis** - COVID/recovery/bear/normalization testing not executed
- **Temporal stability rolling windows** - Not implemented

### Why It Was Deferred

1. **PhD timeline pressure**: Paper #1 submission took priority
2. **"Good enough" validation**: Basic stats proved positive expected value
3. **Scope creep risk**: Full framework would delay research by weeks
4. **Diminishing returns**: Pattern validation via LLM obfuscation testing (Issue #79) became the primary validation approach

### Potential Future Use

If revisiting for Papers 2-3 or publication revision:

1. Implement `PermutationTester` class from issue specification
2. Add `test_regime_robustness()` for multi-regime validation
3. Apply FDR correction when testing multiple patterns simultaneously

### Related Work

- Issue #79: Obfuscation testing (became primary validation approach)
- `src/analysis/pattern_probability_mapper.py` - Contains basic statistical validation

---

## Superseded Approaches

These research directions were not abandoned due to infeasibility, but replaced by better approaches that emerged during research.

---

## #6: Algorithmic Pattern Mining (PrefixSpan)

**Status:** Superseded by LLM-based detection
**GitHub Issue:** [#6](https://github.com/iAmGiG/gex-llm-patterns/issues/6)
**Date Closed:** November 2025

### Original Concept

Implement automated sequential pattern mining using algorithms like PrefixSpan to:

- Extract frequent, statistically significant patterns from tokenized GEX sequences
- Calculate support thresholds (>10 occurrences) and confidence thresholds (>60%)
- Perform statistical significance testing (chi-square, permutation tests)
- Rank patterns by predictive value and lift ratios

### Why It Was Superseded

The research direction evolved to favor LLM-based pattern detection:

| Approach | Algorithmic Mining | LLM-Based Detection |
|----------|-------------------|---------------------|
| Pattern discovery | Automated (PrefixSpan) | Human-guided prompts |
| Interpretability | Statistical metrics only | Natural language reasoning |
| Flexibility | Fixed pattern types | Adapts to novel patterns |
| PhD thesis fit | Supporting analysis | Core contribution |

### What Was Learned

1. **PatternProbabilityMapper** implementation was completed and functional
2. Demonstrated 60% win rate for gamma_trap pattern (5 samples)
3. Key insight: "Pattern correctly identifies DIRECTION (60% accuracy) but has poor exit timing"
4. Statistical validation framework proved useful for evaluating LLM outputs

### Replacement Approach

Issue #89 (Sequential GEX Analysis) addresses temporal dynamics through LLM interpretation rather than algorithmic mining. This aligns better with the PhD thesis focus on demonstrating LLM capabilities in market analysis.

### Potential Future Use

May revisit automated mining as a **comparative baseline** in future work (post-PhD) to quantify the value-add of LLM interpretation vs. pure statistical approaches.

### Related Work

- Issue #79: Obfuscation testing framework (validates LLM detection)
- Issue #89: Sequential GEX Analysis (replacement approach)
- `src/analysis/pattern_probability_mapper.py` - Completed implementation (archived)

---

## Future Research Backlog (Deferred with Blockers)

Ideas captured for potential future revisit. Unlike "superseded" approaches, these could still be valuable if blockers are resolved.

---

## #130: 0DTE Intraday Gamma Dynamics

**Status:** Blocked by methodological challenge
**GitHub Issue:** [#130](https://github.com/iAmGiG/gex-llm-patterns/issues/130) (closed) → consolidated to [#116](https://github.com/iAmGiG/gex-llm-patterns/issues/116) (open)
**Date Deferred:** November 2025

### Original Concept

Test if LLM can detect **time-dependent** dealer hedging constraints when 0DTE gamma is concentrated. 0DTE options exploded from ~5% to 40%+ of SPX volume (2020-2024).

```python
pattern_0dte = {
    "net_gex": -5e9,
    "pct_0dte_gamma": 0.45,  # 45% in same-day expiry
    "time_to_close": "3 hours",  # Intraday timing
    "prompt": "0DTE options with high gamma expire in 3 hours. What dealer actions are FORCED before 4pm close?"
}
```

### Why It's Blocked

**Methodological conflict with obfuscation testing:**

- Adding "3 hours to close" reveals market hours (breaks obfuscation principle)
- LLM could memorize that "market close = 4pm EST" rather than reasoning about gamma decay
- Obfuscation is foundational to Papers 1-2 validation methodology

**Proposed solution (not yet implemented):**

Frame as relative time: "T hours until gamma decay" without specifying market close time.

### What Would Unblock This

1. Develop relative-time obfuscation methodology
2. Validate that time-obfuscated prompts still enable constraint reasoning
3. Academic grounding in 0DTE literature (Gao et al. 2024)

### Potential Value

- 0DTE is now dominant microstructure factor
- Practitioners report intraday regime flips are tradeable
- First academic work on intraday gamma dynamics (Paper 3/4 candidate)

### Related Work

- Issue #116: Intraday GEX Regime Shift Detection (open - future Paper 3)
- Issue #203/#204: Intraday data collection infrastructure (completed)

---

## #132: Cross-Asset Dealer Hedging Networks

**Status:** Deferred to future PhD work
**GitHub Issue:** [#132](https://github.com/iAmGiG/gex-llm-patterns/issues/132) (closed) → consolidated to [#117](https://github.com/iAmGiG/gex-llm-patterns/issues/117) (open)
**Date Deferred:** November 2025

### Original Concept

Test if LLM can detect dealer hedging constraints across asset classes:

- Treasury options (TLT) - duration/convexity mechanics
- Currency options (FXE, EUO) - FX dealer hedging
- Commodity options (GLD, USO) - storage cost dynamics

### Why It's Deferred

1. **Different literature base required**: Fixed income options require Fabozzi/Tuckman grounding (not current focus)
2. **Data complexity**: Multiple exchanges, different data formats, separate vendor relationships
3. **Scope creep risk**: Each asset class is potentially a separate research project
4. **Sequencing**: Need to complete equity-based Papers 1-3 first for credibility

### What Would Unblock This

1. Complete Papers 1-3 (foundational credibility)
2. Identify data vendors with multi-asset options coverage
3. Literature review for each target asset class
4. Advisor approval for PhD timeline extension

### Potential Value

- Test methodology generalizability beyond equities
- Distinguish universal constraints vs asset-specific mechanics
- Top-tier venue potential (JFE, RFS) if results show cross-asset predictability

### Related Work

- Issue #117: Cross-Asset Dealer Hedging Networks (open - future Paper 4/5)
- Issue #87: Individual equities expansion (prerequisite)

---

## See Also

- [auxiliary_research/](auxiliary_research/) - Research that's out of scope but documented for reference
- [CLAUDE.md](../../CLAUDE.md) - Current project status and active research paths
- Open issues #116, #117, #118, #119 - Active future research tracking
