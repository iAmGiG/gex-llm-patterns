# Paper #1: Executive Summary

**One-Page Overview for Quick Reference**

---

## Research Question

**Can LLMs detect structural market constraints (dealer gamma hedging) when all memorization pathways are removed?**

---

## Answer

**YES** - LLMs detect dealer gamma hedging constraints with:

- **71.5%** detection rate (>60% threshold)
- **91.2%** predictive accuracy (predictions materialize)
- **242 days** tested (94% coverage of 2024)

---

## Key Innovation

**Obfuscation Testing Methodology**

Strip all information that could enable memorization:

- Dates → "Day T+0", "Day T+1"
- Tickers → "INDEX_1", "STOCK_G"
- Events → Removed entirely
- Preserve only mechanical metrics (GEX, strikes, volume)

**If LLM still detects patterns** → Proves structural reasoning, not recall.

---

## Primary Results

### Multi-Pattern Validation (Full Year 2024)

| Pattern | Detection | Accuracy | Pass/Fail |
|---------|-----------|----------|-----------|
| Gamma Positioning | 69.4% | 92.5% | ✅ PASS |
| Stock Pinning | 67.4% | 90.4% | ✅ PASS |
| 0DTE Hedging | 77.7% | 90.8% | ✅ PASS |
| **Average** | **71.5%** | **91.2%** | ✅ **PASS** |

### Prompt Bias Ablation Study

| Prompt Type | Detection | Accuracy | Interpretation |
|-------------|-----------|----------|----------------|
| Pattern-specific (biased) | 100% | 92.2% | Detects when primed |
| Neutral (unbiased) | 71.5% | 91.2% | Detects without hints |
| **Difference** | **-28.5 pp** | **-1.0 pp** | Harder but still valid |

**Finding**: 28.5 percentage point drop proves structural reasoning required.

### Detection vs Profitability Divergence

| Quarter | Detection | Accuracy | Net Alpha |
|---------|-----------|----------|-----------|
| Q1 2024 | 100% | 96.2% | +21 bps |
| Q3 2024 | 100% | 98.4% | +4 bps |
| Q4 2024 | 100% | 98.4% | **-1 bps** |

**Finding**: Detection stable (96-100%) while profitability declines to zero.
**Proves**: Methodology detects structure, not profits (no cherry-picking).

---

## Methodological Contributions

### 1. Obfuscation Testing Framework

- Systematic removal of memorization pathways
- Validation criteria: Detection >60%, Accuracy >75%, Attribution present
- Reusable for any LLM market analysis task

### 2. WHO → WHOM → WHAT Attribution

- **WHO**: Identify market participants
- **WHOM**: Identify forced/influenced parties
- **WHAT**: Identify forced action
- Forces LLM to explain mechanism, not just label pattern

### 3. Multi-Level Validation

- **Level 1**: Pattern presence (detection rate)
- **Level 2**: Prediction accuracy (materialization rate)
- **Level 3**: Causal attribution (WHO→WHOM→WHAT)

---

## Statistical Validation

**Sample Size**: 242 days (>99% power for both detection and accuracy tests)

**Effect Size**: Cohen's h = 0.44 (medium-large)

**Coverage**: 94% of 2024 trading year (9 holidays + 10 data gaps)

**p-value**: <0.001 for both detection and accuracy

**Verdict**: Results statistically robust with high confidence.

---

## Key Findings

1. **Obfuscation Testing Works**: 71.5% detection without memorization pathways validates structural reasoning

2. **Detection ≠ Profitability**: Pattern detection persists when alpha disappears (proves no cherry-picking)

3. **Multi-Pattern Generalization**: Consistent results across 3 framings (67-78% detection, 90-92% accuracy)

4. **Prompt Bias Measurable**: 28.5 pp detection drop quantifies bias impact

5. **Null Granger Causality**: GEX doesn't Granger-cause volatility in 2024 (data limitation: no regime variation)

---

## Significance

### For Finance Research

- Validates dealer gamma hedging constraint is detectable in GEX data
- Provides automated alternative to manual pattern identification
- Addresses LLM memorization concern in financial applications

### For AI/ML Research

- First rigorous obfuscation testing for LLM market analysis
- Demonstrates structural vs statistical reasoning validation
- Contributes to interpretability via output validation (WHO→WHOM→WHAT)

### For Trading Practice

- Pattern is real (91.2% predictions materialize)
- But profitability is marginal (+5.6 bps, below 10 bps threshold)
- Needs enhancements (volatility filters, regime selection) for viability

---

## Limitations

1. **Single Asset (SPY)**: Only S&P 500 tested, may not generalize to stocks
2. **Single Year (2024)**: Only one year tested, persistent negative regime
3. **LLM Black Box**: Cannot trace internal reasoning mechanisms
4. **Null Granger**: GEX doesn't Granger-cause volatility (contemporaneous relationship likely)

---

## Future Work

**Short-term**: Multi-year validation (2022-2024), single-stock testing

**Medium-term**: Cross-asset validation (QQQ, IWM), intraday GEX dynamics

**Long-term**: Real-time trading integration, sector rotation analysis (Paper #3)

---

## Dissertation Context

**Paper #1** (This Paper): Methodology validation (5-day windows)

- Proves obfuscation testing works
- Validates LLM structural reasoning

**Paper #2** (In Progress): Regime detection (30-day windows)

- Extends to persistent regimes
- Tests selectivity (30-50% expected)

**Paper #3** (Planned): Sector rotation at regime boundaries

- Applies regime detection to trading
- Validates economic value

---

## Reviewer Feedback (November 2025)

**Overall**: Positive, minor revisions requested

**Strengths Noted**:

- Well written and organized
- Clear methodology and framework
- Rigorous validation
- Excellent results and discussion

**Revisions Requested**:

- Reduce 12 → 10 pages (CRITICAL)
- Justify single-year data (DEFER to future work)
- Strengthen SPY-only justification (DO)
- Address reasoning explainability (DO)

**Expected Outcome**: Acceptance likely after revisions

---

## Files in Dissertation Archive

1. **README.md** - Comprehensive overview
2. **paper1_executive_summary.md** - This file (one-page summary)
3. **key_findings_and_implications.md** - Detailed findings and significance
4. **validation_summary.md** - Condensed validation data
5. **figures/** - 8 core figures (1.8 MB)
6. **latex_source/** - Complete LaTeX project for recompilation

---

## Citation

```bibtex
@article{regan2025inferring,
  title={Inferring Latent Market Forces: Evaluating LLM Detection of
         Gamma Exposure Patterns via Obfuscation Testing},
  author={Regan, Christopher and Xie, Ying},
  journal={IEEE DSAA (under review)},
  year={2025},
  institution={Kennesaw State University}
}
```

---

## Bottom Line

**Paper #1 establishes that LLMs can detect structural market constraints without memorization, validating the methodology for the broader dissertation on regime detection and sector rotation.**

**Status**: Under revision, acceptance expected
**Contribution**: Novel obfuscation testing framework for LLM market analysis
**Impact**: Enables Papers #2 and #3, advances both finance and AI/ML research

---

**Document Version**: 1.0
**Created**: November 10, 2025
**Purpose**: Quick-reference executive summary for dissertation committee
