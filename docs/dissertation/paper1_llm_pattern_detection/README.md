# Paper #1: LLM-Based Detection of Dealer Constraint Patterns

**Dissertation Component 1 of 3**

## Overview

This paper validates a novel methodology for testing whether LLMs can detect structural market constraints without memorization. It establishes the foundation for the broader dissertation on LLM-based market regime detection.

**Working Title**: "Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing"

**Status**: Submitted (October 26, 2025), Under Revision (November 10, 2025)

**Venue**: IEEE DSAA (Data Science and Advanced Analytics)

**Reviewer Feedback**: Positive overall, minor revisions requested (page reduction, justifications)

---

## Core Research Question

**Can LLMs detect structural market constraints (dealer gamma hedging) when all temporal and contextual information is stripped away?**

**Answer**: YES - 71.5% detection rate with 91.2% predictive accuracy across 242 trading days.

---

## Key Innovation: Obfuscation Testing

**Problem**: LLMs may memorize financial patterns from training data rather than reasoning about market mechanics.

**Solution**: Strip all identifying information before presenting data to LLM:

- Real dates → "Day T+0", "Day T+1", "Day T+2"
- Real tickers → "INDEX_1", "STOCK_G"
- Remove all news, events, earnings dates
- Preserve only mechanical metrics (GEX, strikes, volume, greeks)

**If LLM still detects patterns** → Proves reasoning about structure, not memorization.

---

## Primary Findings

### 1. Detection Performance (Unbiased Prompts)

**Full Year 2024 Validation** (242 trading days):

| Pattern | Detection | Accuracy | Sample | Status |
|---------|-----------|----------|--------|--------|
| Gamma Positioning | 69.4% | 92.5% | 242 days | PASS |
| Stock Pinning | 67.4% | 90.4% | 242 days | PASS |
| 0DTE Hedging | 77.7% | 90.8% | 242 days | PASS |
| **Average** | **71.5%** | **91.2%** | **242 days** | **PASS** |

**Threshold for validation**: >60% detection, >30 samples
**Result**: ALL patterns exceed threshold

### 2. Prompt Bias Analysis

**Ablation Study** - Same data, different prompts:

| Prompt Type | Detection Rate | Accuracy | Interpretation |
|-------------|---------------|----------|----------------|
| Pattern-specific (biased) | 100% | 92.2% | LLM detects when primed |
| Unbiased (neutral) | 71.5% | 91.2% | LLM detects without hints |
| **Difference** | **-28.5 pp** | **-1.0 pp** | Detection drops, accuracy stable |

**Key Finding**: 28.5 percentage point drop in detection proves LLM requires structural reasoning when not primed. Stable accuracy proves detected patterns are still valid.

### 3. Detection vs Profitability Divergence

**Quarterly Analysis**:

| Quarter | Detection | Accuracy | Net Alpha | Market Regime |
|---------|-----------|----------|-----------|---------------|
| Q1 2024 | 100% | 96.2% | +21 bps | Strong negative GEX |
| Q3 2024 | 100% | 98.4% | +4 bps | Moderate negative GEX |
| Q4 2024 | 100% | 98.4% | -1 bps | Weak negative GEX |

**Critical Insight**: Detection and accuracy remain high (96-100%) even as economic profitability declines to zero. This proves:

- ✅ Methodology detects **structure**, not **profits**
- ✅ No cherry-picking of profitable periods
- ✅ Pattern detection persists across varying market conditions

---

## Methodological Contribution

### WHO → WHOM → WHAT Framework

Structured approach to causal attribution in market mechanics:

1. **WHO**: Identify the market participants (dealers, retail, institutions)
2. **WHOM**: Identify who is forced/influenced (retail flows → dealer hedging)
3. **WHAT**: Identify the forced action (dealers sell underlying when negative GEX)

**Example Detection** (from 2024-01-02):

```
WHO: Options dealers at major market makers
WHOM: Retail/institutional option buyers create imbalance
WHAT: Dealers forced to sell SPY when price rises (amplify volatility)

GEX: -$32.49B (negative = short gamma = volatility amplification)
Prediction: Price moves >0.5% within 3 days
Outcome: -0.86% move next day (MATERIALIZED ✅)
```

### Three-Level Validation Criteria

**Level 1 - Pattern Presence**: Does LLM detect constraint consistently?

- Threshold: >60% detection rate
- Result: 71.5% average (PASS)

**Level 2 - Prediction Accuracy**: Do predictions materialize?

- Threshold: >75% materialization rate
- Result: 91.2% (PASS)

**Level 3 - Causal Attribution**: Does LLM explain WHO→WHOM→WHAT?

- Method: Manual review of LLM reasoning
- Result: 100% of detections include causal chain (PASS)

---

## Statistical Validation

### Sample Size and Power

**Detection Rate Test** (69.4% vs 50% random):

- Required sample: n = 30 (80% power)
- Actual sample: n = 242
- **Statistical power**: >99%

**Accuracy Test** (92.5% vs 80% baseline):

- Required sample: n = 50
- Actual sample: n = 242
- **Statistical power**: >99%

**Coverage Analysis**:

- Expected trading days: 258 (after holidays)
- Actually tested: 242 days
- **Coverage**: 94% (9 holidays + 10 data gaps)

### Granger Causality Results

**Test**: Does GEX Granger-cause forward volatility?

**Finding**: NULL RESULT (p = 0.973 at lag 1)

- GEX does NOT predict volatility in lagged regression
- All 242 days had negative GEX (no regime variation)
- Relationship appears **contemporaneous** (same-day) not lagged

**Interpretation**:

- ❌ Does NOT invalidate LLM detection (91.2% predictions still materialize)
- ✅ Confirms 2024 was persistent single regime (structural shift from 0DTE)
- ⚠️ Granger test requires regime variation; 2024 had none

**Decision**: Acknowledge null result in Discussion > Limitations, frame as data limitation not methodology flaw.

---

## Academic Significance

### Contributions to Literature

**1. Novel Validation Framework**

- First application of obfuscation testing to LLM market analysis
- Addresses memorization concern in financial LLMs
- Provides replicable methodology for validating LLM reasoning

**2. Multi-Pattern Generalization**

- Tests 3 different narrative framings of same constraint
- Proves detection is structural (not pattern-specific)
- Demonstrates robustness across prompt variations

**3. Detection-Profitability Separation**

- Shows pattern detection persists when alpha disappears
- Proves methodology detects mechanics, not anomalies
- Strengthens academic rigor (no cherry-picking)

### Addresses Research Gap

**Prior work on LLMs in finance**:

- Sentiment analysis (Xing et al. 2018)
- Event detection (Chen et al. 2020)
- Price prediction (Lopez-Lira & Tang 2023)

**Gap**: No rigorous validation of **structural reasoning** vs **memorization**

**This paper**: First to use obfuscation testing for market constraint detection

---

## Reviewer Feedback (November 2025)

### Positive Comments (Both Reviewers)

✅ "Well written and organized"
✅ "Clear background and framework"
✅ "Generalizable testing methodology"
✅ "Rigorous causal validation"
✅ "Results and discussion section excellent"

### Requested Revisions (10-day deadline)

**Issue #120 (CRITICAL)**: Reduce manuscript from 12 to 10 pages

- Current: ~12 pages
- Target: ≤10 pages (IEEE DSAA limit)
- Strategy: Condense Related Work, reduce figures, tighten Results section

**Issue #121 (DEFER)**: Multi-year validation (2022-2024)

- Reviewer 1: "Would be more convincing if covers more years"
- Effort: 6-9 days (database rebuild + validation)
- Decision: DEFER to future work, justify in Limitations section

**Issue #122 (DO)**: Strengthen single-asset (SPY-only) justification

- Reviewer 2: "Single-asset focus" limitation
- Strategy: Reframe as methodological strength (most efficient market)
- Effort: 1-2 hours

**Issue #123 (DO)**: Address reasoning explainability

- Reviewer 2: "Reasoning depth not fully explainable"
- Strategy: Acknowledge black-box nature, list validation mitigations
- Effort: 2-3 hours

**Overall assessment**: Minor revisions, acceptance likely

---

## Files in This Archive

### Core Documentation

1. **README.md** (this file) - Comprehensive overview
2. **paper1_complete_abstract.md** - Executive summary of all sections
3. **validation_summary.md** - Condensed validation results
4. **key_findings_and_implications.md** - Research contributions and significance

### Paper Materials

5. **figures/** - 8 core figures (1.8 MB total):
   - fig1_obfuscation_example.png - Methodology visualization
   - fig2_gex_profile.png - GEX calculation example
   - fig3_validation_pipeline.png - Framework overview
   - fig4_detection_comparison.png - Biased vs unbiased results
   - fig5_quarterly_stability.png - Temporal robustness
   - fig6_validation_funnel.png - Testing pipeline
   - fig7_confidence_distribution.png - Detection confidence
   - fig8_performance_matrix.png - Multi-pattern results

### LaTeX Source (if needed)

6. **latex_source/** - Complete LaTeX project for recompilation
   - Main.tex, all section files, references.bib
   - Compile instructions in COMPILE_INSTRUCTIONS.md

---

## Connection to Broader Dissertation

### Three-Paper Dissertation Arc

**Paper #1 (This Paper)**: Validation Methodology

- Question: Can LLMs detect market constraints?
- Method: Obfuscation testing
- Finding: Yes, 71.5% detection with 91.2% accuracy

**Paper #2 (In Progress)**: Regime Detection

- Question: Can LLMs identify persistent market regimes (30-day windows)?
- Method: Sequential GEX analysis with regime classification
- Status: Phase 1 validation underway (76% detection on 46 windows)

**Paper #3 (Planned)**: Sector Rotation at Regime Boundaries

- Question: Do sector rotations occur when regimes shift?
- Method: Cross-sectional analysis at detected regime transitions
- Timeline: Post-Paper #2 validation

### Why This Sequence Matters

**Paper #1 establishes foundation**:

- Proves obfuscation testing methodology works
- Validates LLM structural reasoning capability
- Provides framework for Papers #2 and #3

**Paper #2 extends to regimes**:

- Applies same methodology to longer windows
- Tests selectivity (30-50% expected vs 98-100% trivial)
- Sets up regime boundary analysis

**Paper #3 applies to trading**:

- Uses detected regime shifts for sector rotation timing
- Validates economic value of LLM regime detection
- Completes research → application → validation cycle

---

## Future Extensions

### Short-term (1-2 months)

1. Complete Paper #1 revisions (Issues #120, #122, #123)
2. Submit revised manuscript (IEEE DSAA)
3. Complete Paper #2 Phase 1 validation

### Medium-term (3-6 months)

1. Test 2022-2023 data (different volatility regime)
2. Complete Paper #2 full validation (Phases 2-4)
3. Begin Paper #3 sector rotation analysis

### Long-term (6-12 months)

1. Test other assets (QQQ, IWM, individual stocks)
2. Extend to credit markets (corporate bonds, CDS)
3. Apply to cryptocurrency gamma (if data available)

---

## Citation

```bibtex
@article{regan2025inferring,
  title={Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing},
  author={Regan, Christopher and Xie, Ying},
  journal={IEEE DSAA (under review)},
  year={2025},
  institution={Kennesaw State University}
}
```

---

## Contact

**Author**: Christopher Regan
**Email**: <cregan1@kennesaw.edu>
**Advisor**: Ying Xie (<yxie2@kennesaw.edu>)
**Institution**: Kennesaw State University, Department of Computer Science

**GitHub**: <https://github.com/iAmGiG/gex-llm-patterns>
**Branch**: paper1-reviewer-revisions (current work)

---

**Document Version**: 1.0 (Dissertation Archive)
**Created**: November 10, 2025
**Purpose**: Comprehensive reference for dissertation material
