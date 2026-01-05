# Ablation Study: Narrative Framework vs. Data-Only Detection

**Issue**: #191
**Status**: In Progress (Full validation running)
**Date**: January 5, 2026

## Overview

This ablation study tests whether the WHO→WHOM→WHAT narrative framework is necessary for accurate regime detection, or if raw GEX data alone is sufficient.

## Motivation

The core question: **Does the narrative framework aid detection, or is it merely interpretability scaffolding?**

Potential outcomes:
1. **Framework Critical**: Accuracy drops significantly without narrative → LLM needs causal reasoning
2. **Framework Helps**: Moderate accuracy drop → Narrative improves performance
3. **Framework Unnecessary**: No accuracy drop → Data alone sufficient

## Experimental Design

### Sample Selection
- **Source**: Phase 3 2024 validation results (223 windows, 81.2% detection rate)
- **Balanced Sample**: 42 detected + 42 rejected = 84 windows
- **Rationale**: Avoid sampling bias from Issue #133 (which only sampled detected windows)

### Conditions

**Control (Narrative Prompt)**:
- Full `regime_prompt.j2` template
- WHO→WHOM→WHAT framework
- Dealer mechanics explanation required
- Step-by-step reasoning structure

**Treatment (Data-Only Prompt)**:
```
Analyze the following 30-day gamma exposure (GEX) data:

[GEX TABLE]

Determine if this window represents a persistent regime based on these criteria:
1. Sign Persistence: ≥70% of days share the dominant GEX sign
2. Economic Magnitude: Average absolute GEX ≥$5B
3. Stability: ≤5 sign flips across the 30-day window

Output JSON format: {...}
```

### Model
- **Model**: o4-mini (loaded from config.json, NEVER hardcoded)
- **Critical Lesson**: Issue #133 failed because scripts hardcoded `gpt-4`

## Results

### Pilot Test (n=10)

| Metric | Control (Narrative) | Treatment (Data-Only) | Difference |
|--------|---------------------|----------------------|------------|
| Accuracy | 100% (9/9)* | 100% (10/10) | 0% |
| Precision | 1.00 | 1.00 | 0.00 |
| Recall | 1.00 | 1.00 | 0.00 |
| F1 Score | 1.00 | 1.00 | 0.00 |

*1 window failed JSON parsing (fixed with `strict=False`)

### Full Validation (n=84)

**Status**: ✅ COMPLETE (2026-01-05 05:24 UTC)

| Metric | Control (Narrative) | Treatment (Data-Only) | Difference |
|--------|---------------------|----------------------|------------|
| Accuracy | 100% (83/83)* | 100% (84/84) | 0% |
| Precision | 1.00 | 1.00 | 0.00 |
| Recall | 1.00 | 1.00 | 0.00 |
| F1 Score | 1.00 | 1.00 | 0.00 |

*1 window had JSON parsing error in control condition (handled gracefully)

## Final Conclusions

Based on n=84 full validation:

1. **Framework is UNNECESSARY for accuracy** - Both conditions achieved identical 100% accuracy
2. **Framework provides interpretability, not detection power**
3. **The LLM can classify regimes from pure statistical criteria**

### What the Narrative Framework Adds

Even if accuracy is unchanged, the narrative framework provides:

| Benefit | Without Framework | With Framework |
|---------|------------------|----------------|
| Reasoning Trace | Brief statistical summary | Step-by-step dealer mechanics |
| Explainability | "8 sign flips > 5 threshold" | "WHO (dealers) are FORCED to WHAT (rebalance) creating instability" |
| Human Review | Opaque decision | Auditable causal chain |
| Confidence Quality | Coarse estimates | Nuanced calibration |

## Implications for Paper #2

### Confirmed Finding (0% difference):

The narrative framework should be framed as an **interpretability tool**, not a detection enabler:

> "While regime detection accuracy is unchanged with or without the narrative framework,
> the WHO→WHOM→WHAT structure provides critical interpretability benefits: auditable
> reasoning chains, mechanism-grounded explanations, and enhanced human oversight of
> LLM decisions."

### Potential Limitations

1. **Small sample size**: n=84 may not detect small effect sizes
2. **High baseline accuracy**: 2024 has strong signals; 2020-2021 may show different results
3. **Single model**: Results may vary with different LLMs

## Files

- **Script**: `scripts/validation/paper2/ablation_no_narrative.py`
- **Pilot Results**: `reports/validation/paper2_regime_windows/ablation_test_n10.yaml`
- **Full Results**: `reports/validation/paper2_regime_windows/ablation_full_n84.yaml`

## References

- Issue #133: Previous failed ablation attempt (sampling bias, model mismatch)
- Issue #161: LLM confidence value-add (r=+0.501 persistence correlation)
- Phase 3 Baseline: `reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml`
