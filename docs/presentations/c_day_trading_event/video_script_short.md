# C-Day Video Script (Short) - 30-45 Seconds

**Title:** Detecting Dealer Gamma Hedging Mechanics: How LLMs Identify Market Structure Without Context

**Format:** Screen share with voiceover
**Duration:** 30-45 seconds
**Target:** Quick introduction for C-Day attendees

---

## Script

**[0:00-0:10] Opening Hook**

"Can AI actually understand market mechanics, or is it just memorizing patterns from training data? We tested this with a radical approach."

**Screen:** Show title slide or Figure 1 (obfuscation example before/after)

---

**[0:10-0:25] Core Methodology**

"We stripped all dates and tickers from options data—turning January 28th into 'Day T+0' and SPY into 'INDEX_1'—forcing the LLM to reason from structure alone. No context. No memorization."

**Screen:** Show [fig1_obfuscation_example.png](../paper1/figures/fig1_obfuscation_example.png)

- Highlight the before/after comparison
- Point to "2024-01-28" → "Day T+0"
- Point to "SPY" → "INDEX_1"

---

**[0:25-0:40] Key Finding**

"Testing 242 days of S&P 500 options: 71% detection rate with zero context. But here's what proves it's genuine reasoning—detection stayed stable while profitability dropped to zero. The LLM identified structural constraints, not trading opportunities."

**Screen:** Show [fig5_quarterly_stability.png](../paper1/figures/fig5_quarterly_stability.png)

- Point to detection bars (stable at ~90%)
- Point to Sharpe ratio line (declining to 0)
- Highlight the divergence

---

**[0:40-0:45] Call to Action**

"Published at IEEE BigData 2025 2nd IEEE International Workshop on Large Language Models for Finance. Come see the full methodology and results."

**Screen:** End slide with:

- Paper title
- Authors: Christopher Regan, Dr. Ying Xie
- Conference: IEEE BigData 2025 Workshop
- QR code or link (optional)

---

## Screen Share Sequence

1. **Slide 1 (0:00-0:10):** Title + Research question
2. **Slide 2 (0:10-0:25):** Figure 1 obfuscation example
3. **Slide 3 (0:25-0:40):** Figure 5 detection vs profitability
4. **Slide 4 (0:40-0:45):** End card with contact info

---

## Key Talking Points (Must Hit)

✅ Obfuscation testing (removes dates/tickers)
✅ 71% detection rate with zero context
✅ Detection stable, profitability drops to zero
✅ Proves structural reasoning, not memorization

---

## Visual Assets Needed

**Required Figures:**

1. `fig1_obfuscation_example.png` - Before/after obfuscation
2. `fig5_quarterly_stability.png` - Detection vs profitability divergence

**Optional:**
3. Title slide with research question
4. End card with conference info

---

## Tone

- **Confident but accessible** - Trading audience, not academic jargon
- **Emphasize novelty** - First rigorous test of LLM structural understanding
- **Highlight practical implication** - Distinguishes AI reasoning from pattern matching

---

## Tips for Recording

1. **Pace:** Speak clearly but energetically (7-8 words per second)
2. **Pauses:** Brief pause at 0:10, 0:25, 0:40 (slide transitions)
3. **Emphasis:** Stress "71% detection" and "profitability dropped to zero"
4. **Screen transitions:** Smooth fade between slides, hold each for 10-15 seconds

---

## Word Count

**Total:** ~100 words (target: 30-45 seconds at moderate pace)

**Breakdown:**

- Hook: 20 words (10 seconds)
- Methodology: 30 words (15 seconds)
- Finding: 40 words (15 seconds)
- CTA: 10 words (5 seconds)

---

## Backup Script (If Need to Cut to 30 Seconds)

**[0:00-0:08]** "Can AI understand market structure, or just memorize patterns? We tested this by stripping all dates and tickers from options data."

**[0:08-0:20]** "Result: 71% detection rate with zero context. Detection stayed stable while profitability dropped to zero—proving genuine structural reasoning."

**[0:20-0:30]** "Published at IEEE BigData 2025. Full methodology at the conference."

---

## Visual Emphasis Points

**When showing Figure 1 (Obfuscation):**

- Use cursor/arrow to highlight "2024-01-28" → "Day T+0" transformation
- Briefly point to ticker removal

**When showing Figure 5 (Divergence):**

- Draw attention to stable detection bars (use cursor circle)
- Trace declining Sharpe ratio line
- Verbally emphasize "same patterns, zero profit"

---

## Keywords to Emphasize (Vocal Stress)

- **"Stripped all dates and tickers"** - Core innovation
- **"71% detection rate"** - Quantitative result
- **"Detection stayed stable while profitability dropped to zero"** - Key proof
- **"Structural reasoning, not memorization"** - Main conclusion
