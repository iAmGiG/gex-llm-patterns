# Paper #2: Sequential GEX Analysis (Temporal Dynamics)

**Status**: Planning Phase (Nov 2025)
**Target**: Journal submission Q1 2026 (6-8 pages)
**Branch**: `paper2-sequential-gex`
**Dependency**: Paper #1 acceptance

---

## Research Question

Can LLMs detect dealer constraint *trajectories* over time, not just single-day snapshots?

**Current Approach** (Paper #1):

- Single-day GEX snapshot at Day T
- Predict Day T+1 outcome
- LLM sees: "Net GEX = -$5.2B on Day T"

**Extension** (Paper #2):

- 5-day GEX sequence (Days T-4 → T-3 → T-2 → T-1 → T+0)
- Predict Day T+1 outcome with trajectory context
- LLM sees: "GEX escalating: -$2.1B → -$3.2B → -$4.1B → -$4.8B → -$5.2B"

---

## Motivation (Advisor Input)

> "Currently you are looking on single day gamma exposure, will it be worthy look at most recent 5 days to detect the hidden force? I mean the sequential changes of gamma exposure would bring more info on dealers intention. This could be a next more comprehensive paper **even before going to individual stocks**"

**Why Sequential Before Cross-Asset (Paper #3)?**

- ✅ Uses existing SPY 2024 data (no new collection)
- ✅ 5 days implementation (vs 6-9 days for equities)
- ✅ Lower risk (test on validated dataset)
- ✅ Natural progression: Temporal → Cross-asset

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

---

## Methodology

### Dataset

- **Symbol**: SPY (same as Paper #1)
- **Period**: 2024 (Q1, Q3, Q4 validated)
- **Windows**: 169 5-day sequences (242 days - 4 day warmup per quarter)

### Obfuscation (Maintained)

- Dates: "Day T-4", "Day T-3", ..., "Day T+0" (no real dates)
- Ticker: "INDEX_1" (no "SPY")
- Context: No events, VIX, news

### Validation

- Compare single-day (Paper #1 baseline) vs sequential (Paper #2 test)
- Metrics: Detection rate, accuracy, confidence, false positives

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

## Implementation Plan (5 Days)

| Day | Task | Output |
|-----|------|--------|
| 1 | Database query extension (5-day windows) | `get_sequential_gex()` function |
| 2 | Sequential prompt template | New prompt builder |
| 3-4 | Validation runs (169 windows) | YAML results files |
| 5 | Comparative analysis | Single vs sequential comparison |

---

## File Organization

```bash
paper2/
├── README.md                          # This file
├── planning.md                        # Detailed implementation plan
├── sequential_methodology.md          # Methodology documentation
├── drafts/                            # Paper drafts
├── figures/                           # Result figures
│   └── scripts/                       # Figure generation
└── tables/                            # LaTeX tables
```

---

## GitHub Issues

- **#89**: Sequential GEX Analysis - Paper #2 Extension (OPEN)
- **#101**: Venue Research for Paper #2 Submission (NEW - to be created)

---

## Next Steps

1. ✅ Create paper2 folder structure
2. 🔄 Create venue research GitHub issue
3. ⏳ Research target journals/venues
4. ⏳ Implement 5-day lookback validation
5. ⏳ Run comparative analysis
6. ⏳ Determine if sequential adds value
7. ⏳ Write Paper #2 draft (if positive results)

---

**Timeline**: Start after Paper #1 acceptance (Jan 2026), submit Q1 2026
