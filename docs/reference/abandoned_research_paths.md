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

## See Also

- [auxiliary_research/](auxiliary_research/) - Research that's out of scope but documented for reference
- [CLAUDE.md](../../CLAUDE.md) - Current project status and active research paths
