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

## #33: Combinatorial Purged Cross-Validation (CPCV)

**Status:** Deferred as "overly complex for POC"
**GitHub Issue:** [#33](https://github.com/iAmGiG/gex-llm-patterns/issues/33)
**Date Closed:** 2025

### Original Concept

Implement CPCV (Combinatorial Purged Cross-Validation) from de Prado's "Advances in Financial Machine Learning" for:

- Proper time-series cross-validation that respects temporal ordering
- Purging overlapping training/test samples to prevent data leakage
- Embargo periods between train/test sets
- Multiple combinatorial paths for more robust statistical estimates

### Why It Was Deferred

1. **Complexity vs POC scope**: Full CPCV implementation requires substantial engineering effort
2. **Diminishing returns for PhD timeline**: Basic validation proved sufficient for paper submissions
3. **Alternative validation approaches**: Obfuscation testing (Issue #79) became primary validation method
4. **Sample size constraints**: With limited pattern occurrences, sophisticated CV provides marginal benefit

### What Would Make This Viable

1. Scale to hundreds of pattern instances (current: ~7-15 per pattern type)
2. Production system where overfitting prevention justifies implementation cost
3. Post-PhD publication requiring additional statistical rigor

### Related Work

- de Prado, "Advances in Financial Machine Learning" (2018), Chapter 7
- Issue #11: Monte Carlo testing (also deferred for similar reasons)
- Issue #79: Obfuscation testing (replacement validation approach)

---

## #38: LLM Few-Shot Training Pipeline

**Status:** Abandoned as excessive scope
**GitHub Issue:** [#38](https://github.com/iAmGiG/gex-llm-patterns/issues/38)
**Date Closed:** September 2025

### Original Concept

Full ML training pipeline for few-shot learning:

- Example library builder with quality scoring and diverse selection
- Context template system (market context, GEX profile, technical context)
- Prompt engineering framework with chain-of-thought reasoning
- Iterative learning system with outcome tracking and example refinement
- Performance validation with backtesting and regime testing

### Why It Was Abandoned

1. **Way over the top**: Full ML training pipeline exceeds thesis scope
2. **PhD focus mismatch**: Thesis demonstrates LLM capability, not ML pipeline engineering
3. **Complexity explosion**: Example curation, prompt A/B testing, feedback integration = months of work
4. **Diminishing returns**: Simple prompts proved sufficient for pattern detection validation
5. **Production vs research**: This is production infrastructure, not research contribution

### What Would Make This Viable

1. Post-PhD commercialization of the research
2. Production trading system requiring continuous improvement
3. Multi-year development timeline with dedicated engineering resources

### Related Work

- Issue #32: Dynamic Prompt Generation (simpler approach used instead)
- `src/llm/mechanics_prompt_builder.py` - Simple prompt system that proved sufficient

---

## #46: Trailing Stop Logic for GAMMA_TRAP Strategy

**Status:** Partially implemented (field exists, no execution logic)
**GitHub Issue:** [#46](https://github.com/iAmGiG/gex-llm-patterns/issues/46)
**Date Closed:** October 2025

### Original Concept

Dynamic trailing stop system for position management:

- Move to breakeven at +0.5% profit
- Trail by 0.5% after +1% profit
- `TrailingStopManager` class for position tracking
- Integration with `ValidatedTradingEngine`

### What Was Implemented

- `trailing_stop_pct` field added to `ActionableSignal` dataclass
- Field used in signal generation (2.0% default trailing value)

### What Was NOT Implemented

- **`TrailingStopManager` class** - Never created
- **Execution logic** - No actual trailing stop updates during position holding
- **Integration with trading engine** - Field exists but unused
- **Backtesting validation** - Never tested trailing vs fixed stops

### Why It Was Deferred

1. **Thesis scope**: Trading execution is outside LLM pattern detection research
2. **AutoTrader handoff**: Execution logic belongs in AutoTrader-AgentEdge project (#502)
3. **PhD boundary**: Paper focuses on pattern detection, not position management

### Potential Future Use

- AutoTrader-AgentEdge project (production trading system)
- Post-PhD trading system development
- Cross-project integration when both systems mature

### Related Work

- `src/analysis/actionable_patterns.py` - Contains partial implementation
- AutoTrader-AgentEdge Issue #502 - Production trading integration

---

## #20: Multi-Agent LLM Orchestration System

**Status:** Abandoned in favor of simplified architecture
**GitHub Issue:** [#20](https://github.com/iAmGiG/gex-llm-patterns/issues/20)
**Date Closed:** September 2025

### Original Concept

Complex multi-agent system with AutoGen framework:

- DataRetrievalAgent for API calls and caching
- Multi-agent communication protocols
- Agent orchestrator with parallel processing
- Comprehensive agent lifecycle management

### Why It Was Abandoned

Issue #50 (Agent Architecture Analysis) concluded:

1. **Complexity not justified**: 75% win rate achieved without complex agent system
2. **Mathematical workflow works**: Data → GEX → Pattern → Validation pipeline is deterministic
3. **Agents are overkill for**: Data retrieval, GEX calculations, basic pattern detection
4. **Single agent sufficient**: One LLM agent for pattern context enhancement
5. **PhD focus**: Research paper, not production infrastructure

### What Was Actually Built

- Single `MarketMechanicsAgent` (simplified from multi-agent)
- Direct Python implementation without agent overhead
- LLM used only where it adds clear value (pattern interpretation)

### Related Work

- Issue #50: Agent Architecture Analysis (decision document)
- Issue #51: LLM Market Mechanics Interpreter (replacement approach)
- `src/agents/market_mechanics_agent.py` - Simplified single-agent implementation

---

## #39: Forward-Test Experiment Runner

**Status:** Abandoned as production infrastructure
**GitHub Issue:** [#39](https://github.com/iAmGiG/gex-llm-patterns/issues/39)
**Date Closed:** October 2025

### Original Concept

Live paper trading system for real-time validation:

- Real-time data integration with <5 second latency
- Live GEX calculation and pattern detection
- Paper trading engine with position management
- 30+ days of live forward testing
- Risk management with drawdown protection

### Why It Was Abandoned

1. **Production infrastructure, not research**: PhD focuses on pattern detection, not trading execution
2. **Massive scope**: Real-time data, position management, risk systems = months of work
3. **Validation accomplished differently**: Historical backtesting and obfuscation testing proved sufficient
4. **AutoTrader handoff**: Production trading belongs in separate AutoTrader-AgentEdge project

### What Would Make This Viable

1. Post-PhD commercialization with dedicated engineering team
2. Clear separation from research (production system vs research validation)
3. Partnership with data vendors for real-time feeds

### Related Work

- Issue #47: Live Trading Execution (related scope)
- Issue #48: Complete Daily Trading Pipeline (related scope)
- AutoTrader-AgentEdge project - Future production trading

---

## #31: Six-Category Pattern Detection

**Status:** Partially implemented, full testing deferred
**GitHub Issue:** [#31](https://github.com/iAmGiG/gex-llm-patterns/issues/31)
**Date Closed:** 2025

### Original Concept

Comprehensive six-category pattern classification framework:

1. **Gamma Trap** - Concentrated gamma creating pin risk
2. **Gamma Squeeze** - Forced dealer hedging amplifying moves
3. **Volatility Compression** - Low gamma enabling breakout setups
4. **Mean Reversion** - GEX extremes suggesting reversal
5. **Momentum Continuation** - Gamma alignment with trend
6. **Neutral/No Signal** - Insufficient gamma structure

### What Was Implemented

- Pattern library structure with 15 patterns (`src/analysis/pattern_library.py`)
- Basic pattern detection logic
- Some validation on subset of patterns (gamma_trap: 60% win rate)

### What Was NOT Implemented

- **Full validation across all 6 categories** - Only gamma_trap thoroughly tested
- **Category-specific thresholds** - Generic thresholds used
- **Inter-category confusion matrix** - Pattern misclassification rates not measured
- **Edge case handling** - Overlapping pattern conditions not resolved

### Why It Was Deferred

1. **Scope consolidation**: Issue closed as "duplicates existing pattern_library.py functionality"
2. **PhD focus shift**: Papers 1-2 focused on regime detection rather than categorical patterns
3. **Validation bottleneck**: Each category requires dedicated historical event testing
4. **Diminishing thesis contribution**: Six-category proved less novel than regime-based approach

### Potential Future Use

- Post-PhD expansion of pattern taxonomy
- Trading system development requiring granular pattern classification
- Comparative study: categorical vs regime-based detection accuracy

### Related Work

- `src/analysis/pattern_library.py` - Contains implemented patterns
- Issue #54: Market Mechanics Pattern Library (15 patterns implemented)
- Issue #79: Obfuscation testing applied to subset of patterns

---

## Explored but Found Infeasible

Research that was completed (exploratory analysis performed) but concluded to be impractical for the thesis scope. Paper 1 documents the rationale.

---

## #27: Third-Order Greeks (Speed, Zomma, Color)

**Status:** Explored, deemed infeasible for LLM interpretation
**GitHub Issue:** [#27](https://github.com/iAmGiG/gex-llm-patterns/issues/27)
**Date Closed:** 2025

### Original Concept

Incorporate third-order Greeks into GEX analysis:

- **Speed** (DgammaDspot): Rate of gamma change with underlying price
- **Zomma** (DgammaDvol): Gamma sensitivity to volatility changes
- **Color** (DgammaDtime): Gamma decay rate over time

### Why It's Infeasible

Paper 1 addresses this in the methodology limitations:

1. **Signal-to-noise ratio**: Third-order derivatives amplify measurement noise
2. **Data quality requirements**: Requires tick-level precision not available in daily data
3. **LLM interpretability**: Natural language explanation of third-order effects is extremely difficult
4. **Practitioner irrelevance**: No market practitioners use third-order Greeks for positioning
5. **Computational instability**: Numerical differentiation errors compound at higher orders

### What Would Make This Viable

1. Intraday tick-level options data with sub-second timestamps
2. Market maker interviews confirming third-order Greeks influence hedging
3. Academic literature establishing predictive value (currently absent)

### Related Work

- Paper 1, Section [Methodology Limitations] - Documents infeasibility rationale
- `src/gex/advanced_greeks.py` (archived in `docs/legacy/`) - Exploratory implementation

---

## #28: Volatility Greeks (Vomma, Veta)

**Status:** Explored, deemed infeasible for LLM interpretation
**GitHub Issue:** [#28](https://github.com/iAmGiG/gex-llm-patterns/issues/28)
**Date Closed:** 2025

### Original Concept

Incorporate volatility-related Greeks into analysis:

- **Vomma** (Volga): Second derivative of option price with respect to volatility
- **Veta**: Sensitivity of vega to time decay
- **Vanna**: Cross-derivative (delta sensitivity to volatility)

### Why It's Infeasible

Paper 1 addresses this alongside #27:

1. **Implied volatility surface complexity**: Requires modeling full IV surface, not just ATM vol
2. **Regime-dependent behavior**: Vomma effects vary dramatically across volatility regimes
3. **LLM hallucination risk**: Complex volatility dynamics prone to confident but incorrect reasoning
4. **Scope creep**: Full volatility surface modeling is a separate research project
5. **Data requirements**: Need real-time IV surface data across strikes and expirations

### What Would Make This Viable

1. Partnership with volatility surface data provider (e.g., OptionMetrics, LiveVol)
2. Separate research focus on volatility trading (not GEX-based thesis)
3. Constrained scope: single-strike Vanna effects only

### Related Work

- Paper 1, Section [Methodology Limitations] - Documents infeasibility rationale
- Issue #27: Third-Order Greeks (related feasibility concerns)
- `src/gex/advanced_greeks.py` (archived) - Contains vomma/veta calculations

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
