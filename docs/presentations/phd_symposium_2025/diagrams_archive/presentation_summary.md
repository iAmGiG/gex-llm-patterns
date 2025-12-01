# Oct 22 Research Presentation - Summary

**Date**: October 22, 2025
**Topic**: LLM-Based Pattern Detection in Options Markets
**Status**: ✅ All figures ready
**Last Updated**: October 21, 2025

---

## Presentation Figures (Final - pres## naming scheme)

All figures optimized for symposium presentation (1920x1080, 120 DPI, high contrast for well-lit rooms):

### Main Slides (9 figures - actually used)

1. **pres02_greeks_gamma.png** - Delta vs Gamma explanation (gamma as "urgency beacon")
2. **pres12_system_flow_compact.png** - System architecture overview (compact 5-stage pipeline)
3. **pres06_forced_hedging_loop.png** - The constraint (WHO forces WHOM to do WHAT loop)
4. **pres04_methodology_obfuscation.png** - Obfuscation testing (before/after comparison)
5. **pres05_methodology_refinement.png** - Biased vs unbiased testing (100% → 69.4%)
6. **pres07_detection_progression.png** - Results progression table
7. **pres08_accuracy_vs_profit.png** - Key finding: Accuracy ≠ Profitability (Q1-Q4 divergence)
8. **pres09_llm_causal_framework.png** - Takeaway: LLMs as causal framework detectors
9. **pres10_pattern_taxonomy.png** - Pattern classification (structural vs narrative)

### Appendix/Backup Figures (3 additional)

- **pres03_gex_vs_gamma.png** - GEX ≠ Gamma (Greek) explanation
- **pres01_system_overview.png** - Full 6-stage pipeline (not used but kept)
- **pres11_system_architecture_layered.png** - Detailed layered architecture

**Total**: 12 presentation figures + 9 generation scripts in `scripts/` folder

---

## Actual Presentation Flow (Oct 22, 2025)

### Slides Created:

1. **Intro**: Research overview
2. **Greeks Explanation**: pres02_greeks_gamma.png
3. **Architecture**: pres12_system_flow_compact.png
4. **The Constraint**: pres06_forced_hedging_loop.png
5. **Methodology**: pres04_methodology_obfuscation.png + pres05_methodology_refinement.png
6. **Results 1**: pres07_detection_progression.png (100% → 69.4% with unbiased prompts)
7. **Results 2**: pres08_accuracy_vs_profit.png (accuracy up, profits down)
8. **Takeaway**: pres09_llm_causal_framework.png (LLMs as causal detectors)
9. **Questions**: Placeholder for Q&A
10. **Appendix slides**: GEX explanation, pattern taxonomy

---

## Key Talking Points

### Slide: Beyond Prediction - LLMs as Causal Framework Detectors

**Main Message**: Transformers were designed for language translation (pattern contextualization), but we show they excel at detecting **causal constraints** when properly constrained.

**Example from validation** (Jan 2, 2024):

- **Input**: Obfuscated GEX data only (Day T+0, INDEX_1, -$32.49B net GEX)
- **LLM Output**: WHO (Market Makers) forces WHOM (Market Participants) to do WHAT (forced hedging)
- **Verification**: SPY forward returns matched predicted mechanism (-0.86% move, dealers amplified)

**Key Points**:

- Not prediction (not forecasting -0.86% return)
- Mechanistic reasoning (identifying structural constraint)
- Verified by outcomes (92.5% accuracy - predictions materialize)

### Slide: Accuracy ≠ Profitability Divergence

**Data** (gamma_positioning quarterly results, biased prompts):

- Q1 2024: 84.9% accuracy, +20.8 bps net alpha
- Q2 2024: 91.7% accuracy, +1.6 bps net alpha
- Q3 2024: 96.9% accuracy, +4.6 bps net alpha
- Q4 2024: 96.8% accuracy, -0.7 bps net alpha

**Interpretation**:

- Accuracy IMPROVES while profitability DECLINES
- Proves methodology measures understanding, not trading edge
- Not overfitting (both would decline)
- Not cherry-picking (we showed unprofitable Q4)

---

## Speaker Notes Highlights

### On "Confidence" scores:

- **Question**: "How can you trust LLM confidence when it's stochastic?"
- **Answer**:
  - Confidence is LLM self-assessment (0-100 text output), not mathematically derived probability
  - We use it only as filter threshold (≥60%)
  - Real validation comes from **outcome verification** (92.5% accuracy)
  - Confidence is heuristic signal strength, not prediction probability

### On "Pattern" definition:

- **Question**: "What exactly is a pattern? How do you define it?"
- **Answer**:
  - Pattern = Causal mechanism description in prompt (WHO forces WHOM to do WHAT)
  - LLM does zero-shot reasoning: "Do these numbers indicate this constraint is active?"
  - No fixed threshold (not "if GEX < -$30B then pattern=True")
  - Context-dependent: Same GEX value might indicate pattern in low-vol but not high-vol regime

### On outcome verification:

- **Question**: "What does 'prediction materialized' mean?"
- **Answer**:
  - LLM predicts mechanism: "Dealers forced to hedge by buying dips/selling rallies"
  - We measure **SPY underlying moves** (not options returns)
  - Verification: Did stock behavior match the predicted constraint?
  - Example: Negative GEX predicted amplified moves → SPY dropped -0.86% → Verified TRUE

---

## File Organization

**Figures**: `docs/presentations/oct22_research/diagrams/pres##_*.png`
**Scripts**: `docs/presentations/oct22_research/diagrams/scripts/pres##_*.py`
**Documentation**:

- `presentation_summary.md` (this file)
- `technical_details.md` (system specifications)
- `diagram_options.md` (figure selection guide)

**Validation Data**: `reports/validation/pattern_taxonomy/gamma_positioning_SPY_2024Q*.yaml`

---

## GitHub Issue

**Issue #95**: Presentation Diagrams for Oct 22 Research Presentation

**Status**: ✅ Complete - All figures generated and organized with pres## naming scheme

---

**Last Updated**: October 21, 2025 (evening)
**Figures reorganized**: Oct 21, 2025 - pres## naming scheme implemented
**Ready for**: Symposium presentation week of Oct 22, 2025
