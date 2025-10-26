# 1. Introduction

## 1.1 Research Question and Motivation

[DRAFT NEEDED]

**Key Points to Cover**:

- Large language models (LLMs) increasingly used for financial market analysis
- Critical question: Can LLMs understand market microstructure mechanisms, or just pattern-match from training data?
- Market microstructure = dealer constraints forcing predictable hedging behavior
- Need rigorous validation methodology to distinguish understanding from memorization

**Opening Hook Ideas**:

- "Recent advances in large language models (LLMs) have sparked interest in their application to financial market analysis. However, a critical question remains unanswered: Can these models genuinely understand market microstructure mechanisms, or are they merely pattern-matching from historical data in their training corpus?"
- Or: "Dealer hedging behavior in options markets creates predictable price dynamics when regulatory constraints (delta neutrality) and risk limits (gamma exposure) force market makers into specific actions. We ask: Can large language models reason about these structural constraints without temporal context?"

---

## 1.2 Gap in Existing Literature

[DRAFT NEEDED]

**Key Points to Cover**:

- **LLMs in Finance Literature**: Existing work shows LLMs can predict prices, analyze sentiment, but...
  - Most studies don't test *understanding* of mechanisms (just correlations)
  - Vulnerable to training data leakage (LLM recalls "GameStop Jan 2021")
  - No rigorous methodology to prevent memorization

- **Market Microstructure Literature**: Well-established dealer constraint patterns but...
  - Traditional validation uses historical backtests (data mining risks)
  - Human expert validation is subjective and not scalable
  - No automated validation framework for causal understanding

- **The Gap**: No methodology exists to rigorously test whether LLMs understand market microstructure constraints vs. memorize training data patterns

---

## 1.3 Our Contribution

[DRAFT NEEDED]

**Key Novel Contributions**:

1. **Obfuscation Testing Framework**: Novel methodology for testing LLM understanding
   - Strip all temporal context (dates → "Day T+0")
   - Remove ticker identity (SPY → "INDEX_1")
   - Force reasoning from market structure alone (GEX values, strike distribution)
   - Prevents training data memorization

2. **Dealer Constraint Pattern Taxonomy**: Formal classification system
   - Type 1: Structural constraints (regulatory/risk limits force behavior) ← WE TEST THIS
   - Type 2: Statistical regularities (correlations without mechanisms)
   - Type 3: Narrative explanations (post-hoc storytelling)

3. **Prompt Bias Discovery and Mitigation**: Methodological rigor
   - Discovered: Including regime labels ("NEGATIVE_GAMMA") inflates detection 100% → 71%
   - Solution: Unbiased prompts with raw GEX data only
   - Result: 71.5% detection proves structural understanding without label hints

4. **Multi-Pattern Validation**: Generalization proof
   - Tested 3 different dealer constraint manifestations
   - All pass mechanical threshold (≥60% detection)
   - All show high accuracy (91.2% predictions materialize)
   - Proves methodology generalizes, not cherry-picked for one pattern

**Main Finding**:
> Large language models can detect structural dealer constraint patterns from market structure alone (71.5% detection rate, 91.2% accuracy) without temporal context or regime label hints, demonstrating genuine understanding of market microstructure mechanisms rather than training data memorization.

---

## 1.4 Paper Roadmap

[DRAFT NEEDED]

**Structure Overview**:

The remainder of this paper proceeds as follows:

- **Section 2** reviews related work on LLMs in financial markets and dealer hedging literature
- **Section 3** presents our obfuscation testing methodology and pattern taxonomy
- **Section 4** describes experimental setup, data sources, and validation pipeline
- **Section 5** reports results from full-year 2024 validation (242 trading days, 3 patterns)
- **Section 6** discusses implications, limitations, and comparison to alternative approaches
- **Section 7** concludes with contributions and future research directions

---

## Notes for Writing

**Tone**: Balance accessibility with rigor

- Explain LLM methodology clearly for finance audience
- Explain dealer constraints clearly for AI/ML audience
- Avoid jargon where possible, define when necessary

**Defensive Writing**: Preempt common criticisms

- Address data leakage concerns upfront (obfuscation)
- Acknowledge limitations transparently (confidence calibration, validation not discovery)
- Emphasize conservative approach (71% > 100% for credibility)

**Key Message**:
This paper contributes a **validation methodology** (obfuscation testing framework), not just empirical findings about specific patterns. The methodology is the main contribution.

---

**Status**: Template created - needs full draft
**Word Count Target**: 800-1000 words for introduction
**Next**: Draft Section 2 (Background and Related Work)
