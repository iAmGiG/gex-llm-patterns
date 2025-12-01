# C-Day Presentation Guide: Detecting Dealer Gamma Hedging Mechanics

**Project:** Detecting Dealer Gamma Hedging Mechanics: How LLMs Identify Market Structure Without Context
**Repository:** gex-llm-patterns (houses multiple related projects)
**Presentation Date:** C-Day
**Conference:** 2nd IEEE International Workshop on Large Language Models for Finance (LLM-Finance 2025)
**Parent Conference:** IEEE BigData 2025 (December 8-11, 2025, Macau SAR, China)
**Paper Status:** Camera-ready submitted (10 pages)

---

## Abstract

We prove LLMs detect structural dealer hedging constraints through obfuscation testing—removing all dates and tickers while preserving market structure. Testing 242 trading days of S&P 500 options data, LLMs achieve 71.5% detection rate with fully obfuscated inputs and 91.2% prediction accuracy. Critically, detection remains stable (84-100%) while profitability declines to zero, proving models identify structural mechanics rather than profitable patterns. This validates genuine causal reasoning in financial markets and provides the first rigorous framework for distinguishing LLM structural understanding from training data memorization.

---

## Conference Submission Information

**Full Workshop Title:**
**"The 2nd IEEE International Workshop on Large Language Models for Finance (LLM-Finance 2025)"**

**Workshop Details:**

- Part of IEEE BigData 2025
- In-person, half-day workshop
- Location: Macau SAR, China
- Dates: December 8-11, 2025
- Follows 1st edition at IEEE BigData 2024 (Washington DC)

**Paper Title:**
"Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing"

**Authors:**

- Christopher Regan (Kennesaw State University)
- Dr. Ying Xie (Kennesaw State University)

---

## Research Question

**Primary Research Question:**
Can large language models detect structural dealer hedging constraints without temporal context—proving genuine mechanical understanding rather than memorized pattern associations?

**Sub-Questions:**

1. Do LLMs identify gamma exposure patterns when dates and tickers are fully obfuscated?
2. Does detection capability remain stable even as economic profitability varies?
3. Can we distinguish structural reasoning from training data memorization?

**Key Innovation:**
Obfuscation testing methodology that strips all temporal/contextual information while preserving quantitative market structure.

---

## Methodology (Concise)

**Five-Stage Validation Pipeline:**

1. **Data Collection:** S&P 500 options data (SPY), 242 trading days, full year 2024 (95.6% coverage)

2. **GEX Calculation:** Compute net gamma exposure, flip points, concentration metrics across strike prices

3. **Obfuscation:** Strip temporal context (dates → "Day T+0"), remove tickers (SPY → "INDEX_1"), preserve structure

4. **LLM Detection:** GPT-4 analyzes obfuscated data, extracts WHO/WHOM/WHAT causal framework + confidence score

5. **Validation:** Measure forward returns (T+1), verify pattern materialization, statistical testing (Granger causality)

**Key Methodological Controls:**

- Unbiased prompts (no regime labels, no hints)
- 60% confidence threshold (3-sigma mechanical significance)
- Validation through forward market behavior, not backtested profits

**Visual Recommendation for Methodology Section:**
✅ **USE Figure 1 (System Architecture):** `fig3_validation_pipeline.png`

- Shows complete 5-stage pipeline visually
- Demonstrates data flow from raw options → obfuscation → LLM → validation
- Perfect for explaining "how we did it" without dense text

Alternative: Use Figure 2 (`fig1_obfuscation_example.png`) if focusing specifically on the obfuscation innovation (before/after comparison).

---

## Poster Guide: Figure Selection

### Recommended Poster Figures (6 total)

#### 1. **Figure 3: Detection vs Profitability Divergence** ⭐ CRITICAL

**File:** [fig5_quarterly_stability.png](../paper1/figures/fig5_quarterly_stability.png)

**Why Include:** This is the KEY finding - shows LLM detects structural patterns (stable 84-100% detection) even as profitability declines (+1.6 bps → -0.7 bps). Proves methodology detects STRUCTURE not PROFITS.

**Poster Message:** "LLMs identify market mechanics, not trading opportunities"

---

#### 2. **Figure 2: Obfuscation Example**

**File:** [fig1_obfuscation_example.png](../paper1/figures/fig1_obfuscation_example.png)

**Why Include:** Visual demonstration of core methodology - before/after data transformation that prevents training data memorization.

**Poster Message:** "Obfuscation ensures genuine structural reasoning"

---

#### 3. **Figure 8: Validation Funnel**

**File:** [fig6_validation_funnel.png](../paper1/figures/fig6_validation_funnel.png)

**Why Include:** Shows complete validation pipeline: 726 tests → 519 detected (71.5%) → 473 materialized (91.2%). Clear visualization of methodology rigor.

**Poster Message:** "71.5% detection rate proves pattern recognition without context"

---

#### 4. **Figure 4: GEX Profile Visualization**

**File:** [fig2_gex_profile.png](../paper1/figures/fig2_gex_profile.png)

**Why Include:** Helps audience understand the raw market data structure (gamma exposure distribution) that LLM analyzes.

**Poster Message:** "LLM analyzes dealer hedging constraints from pure quantitative structure"

---

#### 5. **Figure 6: Pattern Detection Heatmap**

**File:** [fig4_detection_comparison.png](../paper1/figures/fig4_detection_comparison.png)

**Why Include:** Shows all three patterns exceed 60% mechanical threshold (67.4% - 77.7%), demonstrating robustness across pattern types.

**Poster Message:** "Consistent detection across three dealer constraint patterns"

---

#### 6. **Figure 1: System Architecture Diagram**

**File:** [fig3_validation_pipeline.png](../paper1/figures/fig3_validation_pipeline.png)

**Why Include:** End-to-end pipeline from raw options data → GEX calculation → obfuscation → LLM analysis → statistical validation.

**Poster Message:** "Six-stage validation pipeline ensures methodological rigor"

---

### Alternative/Supplementary Figures

#### Figure 5: Confidence Distribution

**File:** [fig7_confidence_distribution.png](../paper1/figures/fig7_confidence_distribution.png)

**Use If:** Space available - shows all patterns have ~80% mean confidence, well above 60% threshold.

---

#### Figure 7: Performance Matrix

**File:** [fig8_performance_matrix.png](../paper1/figures/fig8_performance_matrix.png)

**Use If:** Need to show detection vs accuracy breakdown by pattern type.

---

### Presentation Slide Figures (IEEE BigData 2025)

**Location:** [docs/presentations/ieee_bigdata_2025/figures/](../ieee_bigdata_2025/figures/)

**Available Slides (9 figures):**

1. `slide01_title_system_overview.png` - Title slide with system overview
2. `slide02_problem_obfuscation.png` - Problem statement and obfuscation rationale
3. `slide04_domain_forced_hedging.png` - Dealer hedging constraints explanation
4. `slide05_methodology_obfuscation_example.png` - Obfuscation methodology example
5. `slide07_architecture_pipeline.png` - Validation pipeline architecture
6. `slide08_patterns_taxonomy.png` - Three pattern types taxonomy
7. `slide09_results_detection_vs_profit.png` - Detection vs profitability divergence
8. `slide11_validation_funnel.png` - Validation funnel results

**Note:** These are pre-formatted for 16:9 presentation slides with larger fonts and simplified layouts vs. paper figures.

---

## Trade Show Poster Strategy

### Format: **Stand-Around Poster + 30-Second Video Loop**

**Perfect fit for research project** - no live demo needed, visual storytelling through poster + video.

---

### Poster Layout Design (Vertical 36" x 48" or similar)

**Poster Title:**
**"Detecting Dealer Gamma Hedging Mechanics: How LLMs Identify Market Structure Without Context"**

```
┌─────────────────────────────────────────────────────┐
│  Detecting Dealer Gamma Hedging Mechanics:          │
│  How LLMs Identify Market Structure Without Context │
│  Christopher Regan & Dr. Ying Xie (KSU)            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [30-SEC VIDEO LOOP - QR CODE OR TABLET MOUNT]     │
│                                                     │
├──────────────────┬──────────────────┬───────────────┤
│ 1. THE PROBLEM   │ 2. METHODOLOGY   │ 3. KEY RESULT │
│                  │                  │               │
│ Fig 4: GEX       │ Fig 2:           │ Fig 3: ⭐     │
│ Profile          │ Obfuscation      │ Detection vs  │
│                  │ Example          │ Profitability │
│ "Dealers hedge   │ "Strip temporal  │               │
│ $3T+ daily in    │ context, keep    │ "71.5% detect │
│ forced flows"    │ structure"       │ even as profit│
│                  │                  │ → 0"          │
├──────────────────┼──────────────────┼───────────────┤
│ 4. VALIDATION    │ 5. RESULTS       │ 6. SO WHAT?   │
│                  │                  │               │
│ Fig 8: Funnel    │ Fig 6: Heatmap   │ Applications: │
│ 726 tests        │ All patterns     │               │
│ 71.5% detect     │ >60% threshold   │ • Risk mgmt   │
│ 91.2% accuracy   │ 91.2% accurate   │ • Regulation  │
│                  │                  │ • AI validity │
│                  │                  │               │
│ [QR: GitHub]     │ [QR: Paper]      │ [Contact]     │
└──────────────────┴──────────────────┴───────────────┘
```

---

### 30-Second Video Loop Script

**Visual Sequence:**

**0-10 sec:** Title + Problem Setup

- Animated text: "Can AI detect hidden market forces?"
- Show Figure 4 (GEX Profile) with annotation: "$3+ trillion in daily dealer hedging"
- Voiceover: "Options dealers control massive hedging flows that amplify market volatility"

**10-20 sec:** Methodology + Key Finding

- Transition to Figure 2 (Obfuscation) - split screen before/after
- Show Figure 3 (Detection vs Profitability) - highlight divergence
- Voiceover: "We removed all dates and tickers. LLMs still detected structural patterns at 71.5% accuracy, even as profitability vanished"

**20-30 sec:** Results + Impact

- Show Figure 8 (Validation Funnel) - animated flow
- Display key stats: "726 tests • 71.5% detection • 91.2% accuracy"
- Voiceover: "First proof that LLMs understand market mechanics, not just memorize patterns. Implications for risk management and AI validation."
- End card: QR codes for paper + GitHub

---

### Elevator Pitch Variants (For Visitors)

#### **15-Second Version** (Passing interest)

"We proved LLMs can detect hidden dealer hedging patterns by removing all dates and tickers from market data. 71% detection rate with 91% accuracy. First rigorous test of AI structural reasoning in finance."

#### **30-Second Version** (Engaged visitor)

"Options dealers hedge $3+ trillion daily, creating structural constraints that amplify volatility. We tested if LLMs can detect these patterns without temporal context—fully obfuscated dates and tickers. Result: 71.5% detection rate, 91.2% prediction accuracy. The key finding? Detection stayed stable even as profitability declined to zero, proving LLMs identify market structure, not trading opportunities."

#### **60-Second Version** (Serious interest)

[Add dealer hedging mechanics explanation]
"When dealers are short gamma—negative GEX—they're forced to sell rallies and buy selloffs, amplifying price movements. 0DTE options exploded from 15% to 44% of volume, making this effect stronger than ever.

We built an obfuscation testing framework that strips all temporal context: '2024-01-16 SPY' becomes 'Day T+0 INDEX_1'. If LLMs truly understand market structure, they should still detect patterns.

Results: 71.5% detection across 242 trading days with zero context clues. 91.2% of predictions materialized in forward market behavior. Critically, detection remained stable across quarters while profitability declined from +16 bps to 0 bps. This proves LLMs identify structural constraints, not profitable patterns.

Applications: risk management early warning systems, regulatory surveillance for structural fragility, and validation framework for AI reasoning in finance."

---

### Visitor Engagement Strategy

#### **Hook Them In (5 seconds):**

Point to Figure 3: "See this chart? AI detection stayed at 90% while profits went to zero. That's the whole story."

#### **Tell the Story (Depends on interest):**

- **Technical audience:** Focus on obfuscation methodology, validation rigor
- **Finance audience:** Emphasize dealer hedging mechanics, 0DTE explosion
- **General audience:** "AI understands market structure without seeing dates or stock names"

#### **Leave Them With:**

- QR code to paper (IEEE Xplore when published)
- QR code to GitHub repo
- Business card with contact info
- One-liner: "First proof LLMs understand market mechanics, not just patterns"

---

### What to Have Ready at Poster

**Physical Materials:**

1. ✅ Printed poster (36" x 48" or larger)
2. ✅ Tablet/monitor looping 30-second video
3. ✅ QR code standees (paper + GitHub)
4. ✅ Business cards
5. ✅ 1-page handout (optional): Abstract + Figure 3 + contact

**Digital Backup:**

1. ✅ Full paper PDF on tablet (for deep-dive questions)
2. ✅ Slides with extra figures (if needed for technical discussions)
3. ✅ GitHub repo link ready to show

**Talking Points Cheat Sheet:**

- 0DTE options: 15% → 44% of SPY volume (2022-2024)
- Obfuscation: "Day T+0" instead of "2024-01-16"
- Key stat: 71.5% detection, 91.2% accuracy, 0% final profitability
- Implications: Risk management, regulatory surveillance, AI validation

---

### Questions You'll Get (Prepare Answers)

**Q1:** "What's obfuscation testing?"
**A1:** [Point to Figure 2] "We remove all dates and stock names so the AI can't memorize training data. 'January 28, 2021 GameStop' becomes 'Day T+0 Stock_G'. If it still detects patterns, it's genuine reasoning."

**Q2:** "Why does profitability matter?"
**A2:** [Point to Figure 3] "If the AI was just finding profitable trades, detection would drop when profits vanish. It didn't—stayed at 90%. Proves it detects structure, not opportunities."

**Q3:** "What's dealer gamma hedging?"
**A3:** [Point to Figure 4] "Dealers sell options to everyone. To stay risk-neutral, they must constantly hedge. When they're short gamma, they're forced to sell rallies and buy dips—amplifying volatility."

**Q4:** "Can I use this for trading?"
**A4:** "Not directly—profitability went to zero by Q4. But it validates AI can detect structural risk, useful for portfolio protection and risk management."

**Q5:** "What's next?"
**A5:** "Testing across more asset classes, intraday data, and crisis periods. Also building ensemble methods across multiple LLMs for consensus detection."

---

### What NOT to Do at Poster

**Avoid:**

- ❌ Starting with "So we used GPT-4 with a WHO-WHOM-WHAT prompt framework..."
- ❌ Explaining Granger causality unless explicitly asked
- ❌ Reading the abstract verbatim
- ❌ Defensive explanations of limitations (save for serious technical questions)

**Do:**

- ✅ Start with the hook: "AI detects market structure even as profits vanish"
- ✅ Use figures to tell story: "See this chart..."
- ✅ Adjust depth based on visitor cues (glazed eyes = simplify, leaning in = go deeper)
- ✅ End conversations with clear next step (QR code, business card, "email me")

---

## Key Takeaways for Audience

1. **Methodological Innovation:** Obfuscation testing prevents LLM training data memorization
2. **Main Finding:** LLMs detect structural patterns (71.5%) independent of profitability
3. **Validation Rigor:** 91.2% of detections materialize in forward market behavior
4. **Implications:** First framework for validating LLM structural reasoning in finance

---

## Key References (Top 5)

**Dealer Hedging Mechanics:**

1. **Anderegg, B., Ulmann, F., & Sornette, D. (2022).** "The impact of option hedging on the spot market volatility." *Journal of International Money and Finance*, 124, 102627.
   - Foundational paper on how dealer gamma hedging amplifies spot market volatility

2. **Dim, C., Eraker, B., & Vilkov, G. (2025).** "0DTEs: Trading, Gamma Risk and Volatility Propagation." *SSRN Working Paper*.
   - Empirical validation of 0DTE options' impact on market dynamics and dealer hedging constraints

3. **Krishnan, H. P., & Bennington, A. (2021).** *Market Tremors: Quantifying Structural Risks in Modern Financial Markets*. Palgrave Macmillan.
   - Comprehensive treatment of structural market risks and dealer hedging feedback loops

**LLM Applications & Methodology:**

4. **OpenAI. (2023).** "GPT-4 Technical Report." *arXiv preprint arXiv:2303.08774*.
   - Technical foundation for the LLM model used in pattern detection

5. **Lopez-Lira, A., & Tang, Y. (2023).** "Can ChatGPT forecast stock price movements? Return predictability and large language models." *arXiv preprint arXiv:2304.07619*.
   - Pioneering work on LLM applications in financial market prediction

---

## Supporting Materials

**Repository:** <https://github.com/iAmGiG/gex-llm-patterns>
**Paper Location:** `docs/papers/paper1/ieee_bigdata_2025/`
**Figures:** `docs/papers/paper1/figures/` (8 publication-ready figures)
**Presentation Slides:** `docs/presentations/ieee_bigdata_2025/figures/` (9 slide-optimized figures)

---

## Questions to Prepare For

**Q1:** "Why 60% detection threshold?"
**A1:** Represents 3-sigma significance (p<0.01) for structural detection vs random chance. All three patterns exceed this threshold even with unbiased prompts (67.4%-77.7%).

**Q2:** "What if LLM is just fitting to volatility patterns?"
**A2:** We tested this - within negative GEX regime, volatility doesn't correlate with GEX magnitude (r=-0.01, p=0.85). Detection is threshold-based (constraint present vs absent), not magnitude-based.

**Q3:** "Can you use this for trading?"
**A3:** Detection diverges from profitability (Figure 3), so this validates **understanding** of market mechanics, not trading edge. Application is risk management and surveillance, not alpha generation.

**Q4:** "How do you know obfuscation worked?"
**A4:** Detection rate drops -28.5% when regime labels removed (100% → 71.5%), proving LLM can't rely on training data memorization. The 71.5% remaining validates genuine structural reasoning.

**Q5:** "What about other asset classes?"
**A5:** Current validation limited to S&P 500 index options (SPY). Future work includes equity options, commodities, FX. Methodology generalizes to any market with structural constraints.

---

**Created:** 2025-11-15
**Purpose:** C-Day presentation preparation for Paper #1 LLM structural reasoning research
**Related Conference:** IEEE BigData 2025, LLM-Finance Workshop (2nd edition)
