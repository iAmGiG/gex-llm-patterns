# C-Day Video Script (Long) - 1-2 Minutes

**Title:** Detecting Dealer Gamma Hedging Mechanics: How LLMs Identify Market Structure Without Context

**Format:** Screen share with voiceover
**Duration:** 90-120 seconds
**Target:** Detailed overview for C-Day attendees interested in methodology

---

## Script

**[0:00-0:15] Opening Hook + Problem Statement**

"Can large language models actually understand market structure, or are they just sophisticated pattern matchers? This is critical for AI in trading—we need to know if models reason about causal mechanics or just regurgitate memorized patterns from training data.

We developed a novel testing methodology to answer this definitively."

**Screen:** Title slide

- Show research question
- Optionally show example of "memorization vs reasoning" visual

---

**[0:15-0:45] Methodology: Obfuscation Testing**

"Here's the innovation: We took 242 days of S&P 500 options data from 2024 and stripped every piece of temporal context. January 28th becomes 'Day T+0.' SPY becomes 'INDEX_1.' All the structural data—gamma exposure, strike prices, open interest—stays intact, but the LLM has zero context to anchor on.

This is called obfuscation testing. If the model can still detect dealer hedging constraints with this anonymized data, it's reasoning about the structure itself, not memorizing specific events like the GME squeeze or COVID crash."

**Screen:** Show Figure 1 (obfuscation example)

- Point to before/after comparison
- Highlight preserved structure (GEX values, strikes remain)
- Highlight removed context (dates → Day T+0, ticker → INDEX_1)

**Optional Screen 2:** Show Figure 3 (validation pipeline)

- Briefly trace: Raw Data → Obfuscation → LLM → Validation

---

**[0:45-1:15] Results: Detection vs Profitability Divergence**

"Testing GPT-o3-mini on 242 fully obfuscated days: 71.5% detection rate without any hints. We then validated these detections using forward market returns—no backtesting tricks.

But here's the critical finding that proves this is genuine reasoning: We tracked detection performance quarterly across 2024. Detection rates stayed stable—84% to 100%—while economic profitability collapsed. Quarter 1: Sharpe ratio of 1.8. Quarter 4: Sharpe ratio of 0.1, basically zero alpha.

Think about what this means: The LLM keeps detecting the same structural constraints—dealers short gamma, forced hedging dynamics—even when those constraints stop generating profit. If it were memorizing profitable patterns, detection should drop when alpha disappears. Instead, it stayed stable because the underlying market structure was still there."

**Screen:** Show Figure 5 (quarterly stability)

- Point to detection bars (Q1-Q4: stable ~90%)
- Trace Sharpe ratio line (Q1: 1.8 → Q4: 0.1)
- Visually emphasize the divergence with cursor circles

**Key Visual Moment:** Draw a dividing line or annotation:

- Left side: "High Alpha" (Q1-Q2)
- Right side: "Zero Alpha" (Q3-Q4)
- Show detection bars don't change

---

**[1:35-1:50] Broader Implications**

"This methodology—obfuscation testing—provides the first rigorous framework for distinguishing genuine AI structural reasoning from training data memorization. It's not just for options markets. Any domain where you need to prove a model understands causal mechanics rather than statistical correlations can use this approach.

For trading specifically: This validates using LLMs to detect hidden market constraints, not predict profits."

**Screen:** Show slide with key takeaways:

1. 71% detection with zero context
2. Detection stable, profitability varies
3. Proves structural reasoning
4. Applicable beyond finance

---

**[1:50-2:00] Call to Action**

"Published at the 2nd IEEE International Workshop on Large Language Models for Finance, part of IEEE BigData 2025 in Macau. Camera-ready paper is available now. Come find me at C-Day to discuss the full methodology, or check out the GitHub repository for implementation details."

**Screen:** End card with:

- Paper title: "Inferring Latent Market Forces..."
- Authors: Christopher Regan, Dr. Ying Xie
- Conference: IEEE BigData 2025
- GitHub: github.com/iAmGiG/gex-llm-patterns (optional)
- Contact: Email or LinkedIn (optional)
- QR code linking to paper PDF

---

## Screen Share Sequence (Detailed)

1. **Slide 1 (0:00-0:15):** Title + Research question
2. **Slide 2 (0:15-0:30):** Figure 1 - Obfuscation example (before/after)
3. **Slide 3 (0:30-0:45):** Figure 3 - Validation pipeline (optional, can merge with Slide 2)
4. **Slide 4 (0:45-1:15):** Figure 5 - Detection vs profitability divergence ⭐ **MAIN SLIDE**
5. **Slide 5 (1:15-1:35):** Figure 6 or Table III - Granger causality (optional)
6. **Slide 6 (1:35-1:50):** Key takeaways slide (text summary)
7. **Slide 7 (1:50-2:00):** End card with contact info

---

## Key Talking Points (Must Hit)

✅ Problem: AI memorization vs genuine reasoning
✅ Innovation: Obfuscation testing (strip dates/tickers)
✅ Result 1: 71% detection rate with zero context
✅ Result 2: Detection stable while profitability drops to zero
✅ Validation: Granger causality confirms directional relationship
✅ Implication: Proves structural reasoning, not memorization
✅ Broader applicability: Framework for any domain

---

## Visual Assets Needed

**Required Figures:**

1. `fig1_obfuscation_example.png` - Before/after obfuscation
2. `fig5_quarterly_stability.png` - Detection vs profitability divergence (MAIN VISUAL)

**Recommended:**
3. `fig3_validation_pipeline.png` - System architecture
4. `fig6_granger_causality.png` or Table III - Causal validation

**Text Slides:**
5. Title slide with research question
6. Key takeaways slide (4 bullet points)
7. End card with conference info + contact

---

## Tone

- **Engaging but rigorous** - Trading audience appreciates methodological depth
- **Emphasize innovation** - Obfuscation testing is novel contribution
- **Connect to practical implications** - Why traders/quants should care
- **Confident findings** - Strong p-values, clear divergence pattern

---

## Tips for Recording

1. **Pace:** Moderate speed (6-7 words per second, ~180-200 words total)
2. **Pauses:** Strategic pauses at key transitions:
   - After "we developed a novel methodology" (0:15)
   - After "zero context to anchor on" (0:35)
   - After "basically zero alpha" (1:05)
   - After "detection stayed stable" (1:10)
3. **Emphasis:** Vocal stress on:
   - "71% detection rate"
   - "Detection stayed stable while profitability collapsed"
   - "p-value less than 0.001"
   - "Structural reasoning, not memorization"
4. **Visual cues:** Use cursor to point, circle, or draw arrows during key moments:
   - Obfuscation transformation (0:20-0:25)
   - Divergence between detection and Sharpe (1:00-1:10)
   - Granger p-values (1:20)

---

## Word Count

**Total:** ~280-320 words (target: 90-120 seconds at 6-7 words/sec)

**Breakdown:**

- Hook (0:00-0:15): 40 words
- Methodology (0:15-0:45): 80 words
- Results (0:45-1:15): 100 words
- Validation (1:15-1:35): 50 words (optional)
- Implications (1:35-1:50): 50 words
- CTA (1:50-2:00): 30 words

---

## Backup Script Options

### If Need to Cut to 90 Seconds (Remove Granger Section)

Skip the Granger causality segment (1:15-1:35) and go straight from detection/profitability divergence to broader implications. This saves 20 seconds.

**Modified transition at 1:15:**

"This divergence—stable detection, collapsing profitability—definitively proves the LLM reasons about structure, not memorization. *[Continue to implications at 1:15 instead of 1:35]*"

### If Have Extra Time for 2-Minute Version

Add **one additional result** at 1:10-1:15 before Granger:

"We also tested three different constraint patterns—gamma positioning, stock pinning, and 0DTE hedging—all showed the same behavior: 70-78% detection rate, 90%+ accuracy, stable across quarters."

**Screen:** Briefly show Table I or Figure 8 (performance matrix)

---

## Visual Emphasis Points

### When showing Figure 1 (Obfuscation)

- **Arrow or highlight:** Point to "2024-01-28" → "Day T+0"
- **Arrow or highlight:** Point to "SPY" → "INDEX_1"
- **Verbal cue:** "Notice the structure stays—gamma, strikes, prices—but context disappears"

### When showing Figure 5 (Divergence) ⭐ **CRITICAL MOMENT**

- **First:** Circle Q1 detection bar + Sharpe at 1.8 → "Here: 100% detection, high profitability"
- **Then:** Circle Q4 detection bar + Sharpe at 0.1 → "Here: Still 100% detection, zero profitability"
- **Draw line:** Trace Sharpe ratio decline with cursor
- **Verbal cue:** "Same structural patterns detected, but market absorbed them—no more alpha"

### When showing Granger (if included)

- **Point to:** p-values < 0.001
- **Draw arrow:** GEX → Returns (directional causality)
- **Verbal cue:** "Statistical confirmation: constraints drive returns, not the reverse"

---

## Keywords to Emphasize (Vocal Stress)

**Core Innovation:**

- "Obfuscation testing"
- "Zero context"
- "Stripped all dates and tickers"

**Quantitative Results:**

- "71.5% detection rate"
- "Sharpe ratio collapsed from 1.8 to 0.1"
- "p-value less than 0.001"

**Key Findings:**

- "Detection stayed stable"
- "Profitability disappeared"
- "Structural reasoning, not memorization"

**Broader Impact:**

- "First rigorous framework"
- "Any domain"
- "Causal mechanics"

---

## Optional: Story Arc for Engagement

If you want to add narrative flow:

**Hook:** "Imagine you're a trader, and your AI signals look great—until they stop working. Was it luck? Overfitting? Memorization?"

**Challenge:** "We needed to know: Does the AI understand WHY dealers hedge, or did it just learn 'negative GEX = buy signal'?"

**Solution:** "So we stripped everything that could be memorized..."

**Twist:** "Detection stayed perfect even as profits vanished—proving it understood the structure all along."

**Resolution:** "This changes how we validate AI in markets..."

---

## Technical Details (If Asked Follow-Up Questions)

Be prepared to mention:

- **Model:** GPT-4 (via API)
- **Data:** 242 days, 95.6% coverage of 2024
- **Validation:** Forward returns T+1, no backtesting
- **Threshold:** 60% confidence (3-sigma mechanical significance)
- **Cost:** ~$0.50 per validation run (API costs)
- **GitHub:** Available for replication

---

## Closing Impact Statement

"Bottom line: We proved LLMs can detect structural market constraints without memorization. For traders, this means AI can identify hidden forces—dealer hedging, institutional positioning—that drive price action. For researchers, this methodology finally lets us test whether AI truly understands causality."

**Screen:** Final impact slide with this statement + conference details

---

## Post-Recording Checklist

✅ All figures clearly visible (no blur, high contrast)
✅ Cursor movements smooth and deliberate (not jittery)
✅ Audio clear with minimal background noise
✅ Pace consistent (6-7 words/sec, no rushing at end)
✅ Key numbers emphasized vocally (71%, 1.8→0.1, p<0.001)
✅ End card includes all contact info + QR code
✅ Total length: 90-120 seconds (verify with timer)
