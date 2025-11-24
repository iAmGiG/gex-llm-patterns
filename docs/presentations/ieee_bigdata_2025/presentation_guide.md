# IEEE Big Data 2025 Presentation - Complete Guide

## Testing LLM Structural Reasoning Through Unbiased Obfuscation

**Created:** 2025-11-14 (Consolidated from outline + figure mapping)
**Presentation Duration:** 15 minutes (slides-only with voiceover)
**Format:** Pre-recorded MP4 video (slides + audio narration, no camera)
**Audience:** IEEE Big Data conference attendees (asynchronous viewing, technical focus)
**Video Due:** November 20, 2025

---

## Design Guidelines

### Typography & Fonts

**Primary Font:** Calibri or Arial (sans-serif for international audience readability)

**Font Hierarchy:**

- **Slide Titles:** 32-40pt bold (IEEE blue #003C7D)
- **Body Text:** 20-24pt regular (dark gray #2B2B2B)
- **Key Numbers:** 48-60pt bold (91.2%, 71.5%, 242 days)
- **Figure Captions:** 16-18pt (medium gray #5A5A5A)
- **Maximum 5-6 lines per slide** (increased line spacing 1.2-1.5x)

### Color Scheme

**IEEE Official Colors:**

- **Primary Blue:** #003C7D (titles, key elements)
- **Dark Gray:** #2B2B2B (body text)
- **Medium Gray:** #5A5A5A (secondary text, captions)
- **Light Gray:** #E0E0E0 (backgrounds, dividers)
- **Accent Green:** #00A86B (checkmarks, positive indicators)
- **Accent Red:** #D32F2F (X marks, removed elements)

### Layout Standards

- **Slide Size:** 16:9 widescreen (1920x1080)
- **Margins:** 0.5 inch all sides
- **Consistent header:** Conference name + title (14pt, top right)
- **Slide numbers:** Bottom right corner
- **Clean backgrounds:** White or very light gray (#F5F5F5)

---

## Figure Inventory & Sources

### Paper #1 Figures (docs/papers/paper1/figures/)

| File | Description | Size | Used In |
|------|-------------|------|---------|
| `fig1_obfuscation_example.png` | Before/After obfuscation comparison | 294 KB | Slide 5 |
| `fig3_validation_pipeline.png` | 6-stage system architecture | 188 KB | Slide 7 (alternative) |
| `fig4_detection_comparison.png` | Detection vs profitability | 236 KB | Slide 9 (alternative) |
| `fig6_validation_funnel.png` | 726→519→473 funnel | 73 KB | Slide 11 |
| `fig8_performance_matrix.png` | Pattern effectiveness heatmap | 285 KB | Slide 9 (alternative) |

### Presentation Archive Diagrams (docs/presentations/archive/oct22_research/diagrams/)

| File | Description | Used In |
|------|-------------|---------|
| `pres01_system_overview.png` | High-level system flow | Slide 1 |
| `pres04_methodology_obfuscation.png` | Obfuscation process diagram | Slide 2 |
| `pres06_forced_hedging_loop.png` | Dealer constraint feedback loop | Slide 4 |
| `pres08_accuracy_vs_profit.png` | Detection stable, profit declines | Slide 9 |
| `pres10_pattern_taxonomy.png` | Three pattern types | Slide 8 |
| `pres12_system_flow_compact.png` | Compact pipeline view | Slide 7 |

### Prepared Presentation Figures (docs/presentations/ieee_bigdata_2025/figures/)

**All 8 external figures renamed and ready:**

1. `slide01_title_system_overview.png` - Slide 1 title visual
2. `slide02_problem_obfuscation.png` - Slide 2 core problem (138KB, presentation-optimized)
3. `slide04_domain_forced_hedging.png` - Slide 4 constraint mechanism
4. `slide05_methodology_obfuscation_example.png` - Slide 5 detailed methodology
5. `slide07_architecture_pipeline.png` - Slide 7 system architecture
6. `slide08_patterns_taxonomy.png` - Slide 8 three pattern types
7. `slide09_results_detection_vs_profit.png` - Slide 9 key finding
8. `slide11_validation_funnel.png` - Slide 11 validation results

---

## Complete Slide Specifications

### Slide 1: Title Slide (30 sec)

#### Content

**Title:** Testing LLM Structural Reasoning in Market Microstructure Through Unbiased Obfuscation

**Authors:** [Your Name], [Affiliation]

**Conference:** IEEE International Conference on Big Data 2025

#### Visual

**Figure:** `figures/slide01_title_system_overview.png`
**Placement:** Right half of slide (40% width)
**Description:** Simple diagram showing "LLM → Pattern Detection → Validation" flow

**Layout:** Title slide template with conference branding

#### Voiceover Script (30 seconds)
>
> "This presentation covers our work on validating Large Language Model structural reasoning capabilities through a novel obfuscation testing framework. We use financial markets as a test domain with measurable outcomes to prove LLMs can detect structural constraints without memorizing training data."

---

### Slide 2: The Core Problem (60 sec)

#### Content

**Title:** Distinguishing AI Reasoning from Memorization

**Two-column comparison:**

**Left Column - Traditional Test:**

- "January 2021 market data"
- → AI recalls GameStop from news
- ❌ Vulnerable to memorization

**Right Column - Our Test:**

- "Day T+0, INDEX_1"
- → AI must reason from mechanics
- ✅ Forces structural understanding

**Key Points:**

- Traditional LLM tests vulnerable to memorization
- Famous events in training data (GameStop squeeze, COVID crash)
- How do we know: genuine understanding vs. statistical recall?

#### Visual

**Figure:** `figures/slide02_problem_obfuscation.png`
**Placement:** Bottom half of slide, full width
**Description:** Simple obfuscation process diagram showing temporal data → obfuscated data transformation
**Note:** Using presentation-optimized version (138KB), saving detailed `fig1_obfuscation_example.png` for Slide 5

#### Voiceover Script (60 seconds)
>
> "The fundamental challenge when testing AI understanding is distinguishing genuine reasoning from memorized patterns. If we show an LLM data from January 2021, it might just recall the GameStop squeeze from its training data. Our solution: remove ALL context the LLM could have memorized—dates, tickers, events—forcing it to reason purely from structural mechanics."

---

### Slide 3: Research Question & Contribution (60 sec)

#### Content

**Title:** Can LLMs Detect Structural Constraints Without Context?

**Research Question:**
"Can Large Language Models identify structural constraints in complex systems using only numerical metrics, with all temporal and contextual information removed?"

**Test Domain:** Financial markets (dealer hedging constraints)

**Novel Contributions:**

1. **Obfuscation testing methodology** - first framework for validating LLM structural reasoning
2. **Empirical validation** - 91.2% prediction materialization with fully obfuscated data
3. **Cross-pattern generalization** - same methodology across three pattern types

#### Visual

**None** - Text-focused slide with bullet points
**Alternative:** Optional small icon diagram showing "Question mark → LLM brain → Checkmark" (minimal distraction)

#### Voiceover Script (60 seconds)
>
> "The research question: can LLMs detect structural constraints without any contextual clues? This work tests this using financial market dealer hedging—a regulatory constraint that forces predictable behavior. The key contributions are threefold: a novel obfuscation testing methodology, empirical validation achieving 91.2% accuracy with fully obfuscated data, and demonstration of cross-pattern generalization."

---

### Slide 4: Test Domain - Dealer Hedging Constraints (60 sec)

#### Content

**Title:** Why Dealer Hedging Provides Ideal Test Conditions

**The Structural Constraint:**

- Market makers (dealers) provide liquidity in options markets
- **Regulations REQUIRE delta neutrality** (SEC Rule 15c3-1, FINRA 4210)
- When gamma exposure accumulates, forced hedging creates predictable pressure
- This is a **structural constraint**, not behavioral sentiment

**Why Ideal for Testing:**

- ✅ Multi-agent system (dealers, traders, institutions)
- ✅ Known regulatory constraints
- ✅ Measurable outcomes (forward returns)
- ✅ Clean, comprehensive data

#### Visual

**Figure:** `figures/slide04_domain_forced_hedging.png`
**Placement:** Center, 60% width
**Description:** Flow diagram showing:

```
Customer Trades → Dealers Accumulate Positions →
Regulatory Mandate → Forced Hedging → Measurable Price Impact
```

#### Voiceover Script (60 seconds)
>
> "Financial markets provide ideal conditions for testing constraint detection. Market makers face regulatory requirements to maintain delta neutrality. When options positions accumulate, regulations FORCE dealers to hedge by trading stock, creating measurable price pressure. This is a structural constraint—not psychological sentiment—making it perfect for testing AI understanding."

---

### Slide 5: Obfuscation Testing Methodology (90 sec) ⭐ CRITICAL

#### Content

**Title:** Removing All Memorizable Context

**Two-column layout:**

**Left Column - What We Remove:**

- ❌ Dates → "Day T+0", "Day T+5"
- ❌ Tickers → "INDEX_1", "STOCK_G"
- ❌ Event references → no FOMC, earnings
- ❌ Years/months → no temporal context

**Right Column - What We Preserve:**

- ✅ Gamma exposure metrics
- ✅ Options data (strikes, OI, greeks)
- ✅ Pure numerical mechanics
- ✅ Structural relationships

**Validation Criteria:**

- ≥60% detection rate with obfuscated data → **MECHANICAL pattern**
- <60% detection → **NARRATIVE pattern** (requires memorization)

#### Visual

**Figure:** `figures/slide05_methodology_obfuscation_example.png`
**Placement:** Full width, bottom half of slide
**Description:** Before/After comparison with red (removed) and green (preserved) highlighting
**Split Display:**

- Left: BEFORE (Date: 2024-01-28, Symbol: GME, Context: Fed meeting)
- Right: AFTER (Date: Day T+17, Symbol: STOCK_G, No context)

#### Voiceover Script (90 seconds)
>
> "Here's how obfuscation testing works. We strip ALL context the LLM could have memorized: dates become 'Day T+0', tickers become 'INDEX_1', and we remove all event references. We preserve only pure numerical metrics—gamma exposure, strikes, open interest. If the LLM achieves 60% or higher detection with obfuscated data, the pattern is mechanical. Below 60%, it was relying on memorization. This methodology is generalizable to any domain with structural constraints."

---

### Slide 6: Academic Foundation - Dealer Framework (60 sec)

#### Content

**Title:** Academic Foundation - Dealer-Counterparty Framework

**Two-Layer Citation Strategy:**

| Layer | Citation | Contribution |
|-------|----------|--------------|
| **Theory** | Anderegg et al. (2022) | Options hedging → spot volatility mechanism |
| **Empirics** | Dim et al. (2025) | Order flow validates dealer positioning framework |

**Key Principle:**
"Market makers serve as counterparties to customer option positions, such that dealer gamma equals the negative of aggregate customer gamma."

**Practitioner Implementation:**

- CBOE (2023) and SpotGamma Research document operational gamma metrics
- Major investment banks track dealer hedging flows in real-time
- 0DTE options explosion intensifies these structural effects

**Robustness:**

- Our methodology robust to GEX measurement variations
- Validation through forward-return materialization, not formula accuracy
- Patterns reflect fundamental market mechanics

#### Visual

**PowerPoint Table** - Create citation table (no external figure)
**Design:** Clean table with 2 academic rows (Theory/Empirics), plus practitioner context below

#### Voiceover Script (60 seconds)
>
> "Our work builds on rigorous academic foundation. Anderegg 2022 establishes the theoretical mechanism linking options hedging to spot volatility. Dim 2025 provides empirical validation by measuring dealer inventory directly from order flow, demonstrating that market maker gamma is systematically opposite to customer demand. Practitioner research from CBOE and SpotGamma has operationalized these metrics, with investment banks now tracking gamma exposure in real-time. Critically, our LLM detection framework is robust to moderate GEX variations because validation occurs through forward-return materialization—we're testing if the mechanism exists, not if our formula is perfect."

---

### Slide 7: System Architecture (60 sec)

#### Content

**Title:** End-to-End Validation Pipeline

**Pipeline Flow (7 stages):**

1. Historical Market Data (2024)
2. GEX Calculation (Black-Scholes)
3. Data Obfuscation (strip context)
4. LLM Analysis (GPT-4)
5. Pattern Detection (confidence thresholding)
6. Outcome Verification (forward returns)
7. Results Storage (YAML reports)

**Key Implementation Choices:**

- **End-of-day measurement**: Stable positioning snapshot
- **SQLite database**: Pre-computed GEX for reproducibility
- **Batch processing**: Consistency + cost efficiency
- **Rule-based verification**: Objective outcome measurement

#### Visual

**Figure:** `figures/slide07_architecture_pipeline.png`
**Placement:** Full width, center
**Description:** Compact pipeline flowchart showing 7-stage process with data transformations
**Source:** Using `pres12_system_flow_compact.png` (cleaner for 60-second slide)
**Alternative:** `fig3_validation_pipeline.png` (more detailed, use if time permits)

#### Voiceover Script (60 seconds)
>
> "Our system architecture processes historical market data through seven stages. We calculate gamma exposure using Black-Scholes, obfuscate all temporal context, analyze with GPT-4, threshold detections by confidence, verify outcomes through forward returns, and store results in version-controlled YAML. Key design choice: end-of-day measurement provides stable positioning snapshots, and rule-based verification ensures objective outcome scoring without human judgment."

---

### Slide 8: Three Pattern Types Tested (60 sec)

#### Content

**Title:** Cross-Pattern Validation Strategy

**Pattern Types (All Testing Same Underlying Mechanism):**

1. **Gamma Positioning**
   - Multi-day volatility amplification
   - Dealers forced to amplify price moves

2. **Stock Pinning**
   - Price gravitates to high OI strikes
   - Open interest concentration creates gravitational pull

3. **0DTE Hedging**
   - Same-day expiration hedging pressure
   - Extreme gamma creates intraday urgency

**Key Insight:** Three descriptions of ONE structural constraint (dealer hedging)

**Why Multiple Patterns:**

- Tests generalization capability
- Validates methodology isn't pattern-specific
- Demonstrates cross-domain applicability

#### Visual

**Option 1 (Recommended): PowerPoint Diagram**
**Create simple visual in PowerPoint:**

- Center circle: "Dealer Hedging Constraint" (large, IEEE blue)
- Three connected boxes:
  - Box 1: "Gamma Positioning" (multi-day amplification)
  - Box 2: "Stock Pinning" (OI concentration)
  - Box 3: "0DTE Hedging" (same-day urgency)
- Arrows from center to each box showing "same underlying mechanism"
**Why:** Clean, simple, easy to understand at a glance

**Option 2: Use Performance Matrix**
**Figure:** `figures/fig8_performance_matrix.png` (from paper)
**Placement:** Right half, 40% width
**Description:** Heatmap showing pattern effectiveness across different conditions
**Why:** Data-driven visual, shows all three patterns performing

**Option 3: No Figure (Text-Only)**
**Layout:** Clean bullet list with pattern descriptions
**Why:** For a 60-second slide, text may be clearer than busy diagram

#### Voiceover Script (60 seconds)
>
> "We tested three pattern types: gamma positioning for multi-day volatility amplification, stock pinning where price gravitates to high open interest strikes, and 0DTE hedging for same-day expiration pressure. Key insight: these are actually three descriptions of the same underlying mechanic—dealer hedging constraints. Testing multiple framings validates our methodology generalizes and isn't pattern-specific."

---

### Slide 9: Results - Full Year 2024 Unbiased Validation (90 sec) ⭐ CRITICAL

#### Content

**Title:** Empirical Validation Results (242 Trading Days)

**Results Table:**

| Pattern Type | Detection Rate | Prediction Accuracy | Days Tested |
|--------------|----------------|---------------------|-------------|
| Gamma Positioning | 69.4% | 92.5% | 242 |
| Stock Pinning | 67.4% | 90.4% | 242 |
| 0DTE Hedging | 77.7% | 90.8% | 242 |
| **Average** | **71.5%** | **91.2%** | **242** |

**What This Proves:**

- ✅ LLM detects patterns on **519 of 726 tests** (71.5% detection)
- ✅ Predictions materialize with **91.2% accuracy** when detected
- ✅ **Full year coverage** (no seasonal bias, no cherry-picking)
- ✅ **Passed obfuscation test** (no temporal context needed)

**Key Finding: Detection ≠ Profitability**

- Detection: **71.5%** (consistent)
- Accuracy: **91.2%** (high)
- Economic alpha: **5-11 bps** (not significant)
- **Proves genuine structural understanding, not profitable signal**

#### Visual

**Primary Figure:** `figures/slide09_results_detection_vs_profit.png`
**Placement:** Right half of slide (40% width)
**Description:** Chart showing detection stable (71.5%), profitability declines (5-11 bps)
**Source:** Using `pres08_accuracy_vs_profit.png` (KEY FINDING visual)
**Table Overlay:** PowerPoint table with results (left half of slide)

#### Voiceover Script (90 seconds)
>
> "Our results across full year 2024: average 71.5% detection rate and 91.2% prediction materialization accuracy. 519 of 726 tests resulted in pattern detection, and when detected, predictions materialized 91% of the time. Critically, this was tested with UNBIASED obfuscation—no temporal context provided. Key finding: while detection and accuracy remain high, economic profitability is negligible at 5-11 basis points. This actually STRENGTHENS our contribution—we're measuring structural understanding, not trading edge. The LLM detects mechanical constraints even when they're not profitable."

---

### Slide 10: Unbiased vs Biased Validation (60 sec)

#### Content

**Title:** Discovery and Correction of Prompt Bias

**Initial Results (Q3+Q4 2024, Biased Prompts):**

- 100% detection rate across all patterns
- Prompts unintentionally guided LLM toward expected answers

**Corrected Results (Full Year 2024, Unbiased Prompts):**

- 71.5% detection rate (drop of 28.5%)
- Removed all hint words, expectations, leading questions

**Why This STRENGTHENS Research:**

- ✅ **Academic rigor**: 71% unbiased > 100% biased
- ✅ **Genuine understanding**: LLM reasons from structure, not prompt hints
- ✅ **Reproducible**: Other researchers can validate methodology
- ✅ **Scientific integrity**: Discovered bias and corrected it

**Comparison Table:**

| Metric | Biased (Q3+Q4) | Unbiased (Full 2024) |
|--------|----------------|----------------------|
| Detection | 100% | 71.5% |
| Accuracy | ~95% | 91.2% |
| Validity | ⚠️ Questionable | ✅ Defensible |

#### Visual

**PowerPoint Bar Chart** - Create comparison chart
**Design:**

- Blue bars: Biased detection (100%)
- Orange bars: Unbiased detection (71.5%)
- Red dashed line: 60% mechanical threshold
**Placement:** Right half of slide (40% width)

#### Voiceover Script (60 seconds)
>
> "A critical methodological discovery: our initial Q3-Q4 2024 tests showed 100% detection, but we discovered our prompts were biased—unintentionally guiding the LLM toward expected answers. We corrected this for full-year validation, achieving 71.5% detection with unbiased prompts. This drop actually STRENGTHENS our research: 71% detection without bias is far more defensible than 100% with bias. It demonstrates genuine structural reasoning, not prompt following. This honest reporting of bias discovery and correction exemplifies scientific integrity."

---

### Slide 11: Methodology Validation - Obfuscation Success (60 sec)

#### Content

**Title:** Proving Mechanical Detection (Not Memorization)

**Obfuscation Test Results:**

- ✅ **All patterns passed 60% threshold** (mechanical classification)
- ✅ **No temporal context required** (dates removed)
- ✅ **No ticker context required** (symbols anonymized)
- ✅ **Consistent across 242 days** (robust)

**Validation Framework:**

**MECHANICAL Pattern:**

- Detection ≥60% with obfuscation
- Reasoning from structure
- Generalizes across contexts

**NARRATIVE Pattern:**

- Detection <60% with obfuscation
- Requires memorization
- Context-dependent

#### Visual

**Figure:** `figures/slide11_validation_funnel.png`
**Placement:** Center, 50% width
**Description:** Funnel diagram showing:

- 726 tests → 519 detected (71.5%) → 473 materialized (91.2%)
- 207 not detected (28.5%)
- 46 false positives (8.8%)

#### Voiceover Script (60 seconds)
>
> "The obfuscation test validates our core claim: LLMs detect mechanical patterns, not narrative memorization. All three pattern types exceeded the 60% detection threshold with fully obfuscated data—no dates, no tickers, no temporal context. Had we observed below 60% detection, the pattern would be classified as narrative, requiring memorization. Instead, we observed 70%+ detection, proving the patterns are mechanical. The LLM is reasoning from structural constraints encoded in numerical metrics."

---

### Slide 12: Broader Impact & Generalizability (60 sec)

#### Content

**Title:** Beyond Finance - Methodology Applicability

**Generalizable to Any Domain With:**

1. **Structural constraints** (regulatory, physical, operational)
2. **Multi-agent systems** (interacting entities)
3. **Measurable outcomes** (objective verification)
4. **Temporal data** (can be obfuscated)

**Example Domains:**

| Domain | Constraint | Test Application |
|--------|-----------|------------------|
| **Supply Chain** | Just-in-time inventory requirements | Detect forced restocking patterns |
| **Healthcare** | Hospital capacity constraints | Predict overflow/transfer patterns |
| **Energy Grid** | Load balancing requirements | Identify forced generation scaling |
| **Traffic** | Road capacity limits | Detect congestion amplification |

**Academic Contribution:**

- **Novel validation framework** for testing LLM capabilities
- **Reusable methodology** across domains
- **Rigorous approach** to distinguishing reasoning from memorization

#### Visual

**PowerPoint Table** - Create cross-domain applicability table (no external figure)
**Design:** Clean table with 4 rows, IEEE blue header, examples in each domain

#### Voiceover Script (60 seconds)
>
> "Our obfuscation testing methodology generalizes beyond finance to any domain with structural constraints, multi-agent interactions, and measurable outcomes. Examples: supply chain just-in-time inventory creates forced restocking; hospital capacity constraints create predictable overflow patterns; energy grid load balancing requires forced generation scaling. The academic contribution isn't finance-specific—it's a novel validation framework for testing LLM structural reasoning across domains. This methodology is reusable and provides rigorous approach to distinguishing genuine understanding from statistical memorization."

---

### Slide 13: Limitations & Future Work (60 sec)

#### Content

**Title:** Methodological Limitations and Extensions

**Current Scope:**

- ⚠️ **Single asset class**: Equity index options (SPY) only
- ⚠️ **One year**: 2024 (need multi-year validation)
- ⚠️ **Single LLM**: GPT-4 only (model-specific?)
- ⚠️ **Three patterns**: All variations of dealer hedging

**Methodological Limitations:**

- Obfuscation testing necessary but not sufficient
- Outcome thresholds affect accuracy (rule design matters)
- Domain expertise still needed to identify candidate patterns

**Future Research Directions:**

1. **Multi-asset validation** (bonds, FX, commodities)
2. **Extended time periods** (2020-2025 for regime robustness)
3. **Cross-LLM comparison** (GPT-4 vs Claude vs o3-mini)
4. **Automated pattern discovery** (reduce expert dependence)
5. **Domain extension** (supply chain, healthcare, energy)

#### Visual

**PowerPoint Graphics** - Text slide with minimal icons
**Design:**

- Warning icons (⚠️) for limitations
- Arrow icons (→) for future directions
- Keep text-focused, avoid clutter

#### Voiceover Script (60 seconds)
>
> "Important limitations: our current scope covers one asset class, one year, one LLM model, and three pattern variations of dealer hedging. Methodologically, obfuscation testing is necessary but not sufficient for full validation, and outcome threshold choices affect accuracy measurements. Future work should extend to multiple asset classes, longer time periods, different LLM architectures, and automated pattern discovery to reduce expert dependence. Most importantly, applying this methodology to non-finance domains will test true generalizability."

---

### Slide 14: Related Work & Positioning (60 sec)

#### Content

**Title:** Academic Positioning

**LLM in Finance (Our Differentiation):**

- **NOT**: Price prediction (Lopez-Lira 2023, Chen 2023)
- **NOT**: Sentiment analysis (Wu 2023 BloombergGPT)
- **IS**: Structural constraint detection with validation

**AI Validation Methods:**

- Behavioral testing (Ribeiro 2020) - NLP model checklists
- **Our contribution**: Obfuscation testing for structural reasoning

**Market Microstructure:**

- Dealer hedging well-studied (Ni 2005, Garleanu 2009)
- **Our contribution**: First LLM-based pattern detection with rigorous validation

**Research Gap Filled:**

1. No prior validation of LLM structural reasoning in finance
2. No obfuscation testing framework for complex systems
3. No demonstration that pattern detection persists independent of profitability

#### Visual

**Option 1 (Recommended): Simple 3-Column Comparison Table**
**Create in PowerPoint:**

| Research Area | Prior Work | Our Differentiation |
|---------------|------------|---------------------|
| **LLM in Finance** | Price prediction (Lopez-Lira)<br>Sentiment analysis (Wu, Chen) | Structural constraint detection<br>Obfuscation validation |
| **Market Microstructure** | Dealer hedging theory (Ni, Garleanu)<br>Empirical studies (Anderegg, Dim) | First LLM-based detection<br>Unbiased methodology |
| **AI Validation** | Behavioral testing (Ribeiro)<br>NLP model checklists | Obfuscation for reasoning<br>Independent of profitability |

**Design:** Clean table, IEEE blue headers, left-aligned text, 18-20pt font
**Why:** Clear side-by-side comparison, easier to read than Venn diagram

**Option 2: Three-Box Positioning Diagram**
**Create simple boxes in PowerPoint:**

- Three rectangles side-by-side, each labeled with research area
- Arrow from each box pointing to center box: "Our Work: Intersection"
- Under each: key citations and differentiation point
**Why:** Visual without complexity of overlapping circles

#### Voiceover Script (60 seconds)
>
> "Our work differs from existing LLM finance research. We're NOT predicting prices like Lopez-Lira or extracting sentiment like BloombergGPT. We're detecting structural constraints with rigorous validation. While Ribeiro's behavioral testing validates NLP models, we extend this to structural reasoning through obfuscation. The dealer hedging mechanism is well-studied in market microstructure literature, but we're first to apply LLM detection with unbiased validation. We fill three research gaps: validating LLM structural reasoning in finance, creating obfuscation testing framework for complex systems, and demonstrating pattern detection independent of profitability."

---

### Slide 15: Conclusions & Takeaways (60 sec)

#### Content

**Title:** Key Contributions and Implications

**Main Contributions:**

1. **Novel validation framework**: Obfuscation testing for LLM structural reasoning
2. **Empirical evidence**: 91.2% prediction materialization with fully obfuscated data
3. **Methodological rigor**: Discovered and corrected prompt bias (71.5% unbiased detection)
4. **Cross-pattern generalization**: Same methodology across three pattern types
5. **Generalizable approach**: Applicable beyond finance to any domain with structural constraints

**Key Findings:**

- ✅ LLMs CAN detect structural constraints without memorization
- ✅ Obfuscation testing proves genuine understanding vs. statistical recall
- ✅ Detection persists independent of profitability (validates methodology)
- ✅ 71% unbiased detection more defensible than 100% biased

**Impact:**

- **AI Research**: New validation methodology for testing LLM capabilities
- **Computational Finance**: Alternative to purely rule-based approaches
- **Complex Systems**: Framework for validating AI constraint detection

**Next Steps:** Multi-asset validation, extended time periods, cross-LLM comparison, domain extension

#### Visual

**PowerPoint Metrics Graphic** - Create summary visual with key numbers
**Design:**

- **91.2%** prediction accuracy (48-60pt bold, center)
- **71.5%** unbiased detection (48-60pt bold, center)
- **242** days tested (32pt, secondary)
- **3** patterns validated (32pt, secondary)
**Alternative:** Use `slide01_title_system_overview.png` again (callback to title, shows complete validation loop)

#### Voiceover Script (60 seconds)
>
> "In conclusion, we present a novel obfuscation testing framework that proves LLMs can detect structural constraints without memorizing training data. Achieving 91.2% prediction accuracy with fully obfuscated temporal and ticker data demonstrates genuine understanding. Our discovery and correction of prompt bias strengthens methodological rigor—71.5% unbiased detection is more defensible than 100% biased. The methodology generalizes across pattern types and is applicable to any domain with structural constraints. This work provides AI researchers with new validation tools, offers computational finance an alternative to rule-based approaches, and gives complex systems analysts a framework for validating AI constraint detection. Thank you for your attention—I'm happy to answer questions."

---

## Timing Breakdown

| Slide | Topic | Time |
|-------|-------|------|
| 1 | Title | 0:30 |
| 2 | Core Problem | 1:00 |
| 3 | Research Question | 1:00 |
| 4 | Test Domain | 1:00 |
| 5 | Obfuscation Method | 1:30 ⭐ |
| 6 | Academic Foundation | 1:00 |
| 7 | System Architecture | 1:00 |
| 8 | Three Patterns | 1:00 |
| 9 | Results | 1:30 ⭐ |
| 10 | Bias Discovery | 1:00 |
| 11 | Obfuscation Validation | 1:00 |
| 12 | Broader Impact | 1:00 |
| 13 | Limitations | 1:00 |
| 14 | Related Work | 1:00 |
| 15 | Conclusions | 1:00 |
| **Total** | | **15:30** |

---

## Build Checklist

### External Figures (7 total - ✅ All Prepared)

- [x] `slide01_title_system_overview.png` - Slide 1
- [x] `slide02_problem_obfuscation.png` - Slide 2 (138KB, optimized)
- [x] `slide04_domain_forced_hedging.png` - Slide 4
- [x] `slide05_methodology_obfuscation_example.png` - Slide 5 ⭐
- [x] `slide07_architecture_pipeline.png` - Slide 7
- [x] `slide09_results_detection_vs_profit.png` - Slide 9 ⭐
- [x] `slide11_validation_funnel.png` - Slide 11

**Note:** Slide 8 will use PowerPoint-created diagram instead of external figure

### PowerPoint Elements to Create (7 total)

- [ ] **Slide 6:** Citation table (2 academic rows: Theory/Empirics, plus practitioner context)
- [ ] **Slide 8:** Pattern taxonomy diagram (center circle + 3 connected boxes)
- [ ] **Slide 9:** Results summary table (4 rows: Gamma/Pinning/0DTE/Average)
- [ ] **Slide 10:** Biased vs unbiased bar chart (blue/orange bars, 60% threshold line)
- [ ] **Slide 12:** Generalization table (4 domains: Supply/Healthcare/Energy/Traffic)
- [ ] **Slide 14:** Academic positioning table (3 rows: LLM Finance, Market Micro, AI Validation)
- [ ] **Slide 15:** Key metrics summary (91.2%, 71.5%, 242 days, 3 patterns)

### Slide Assembly Tasks

- [ ] Apply IEEE color scheme (#003C7D blue, #2B2B2B gray)
- [ ] Set fonts (Calibri/Arial, 20-24pt body, 32-40pt titles)
- [ ] Insert all 8 external figures
- [ ] Create 6 PowerPoint elements
- [ ] Add slide numbers (bottom right)
- [ ] Add conference header (top right, 14pt)
- [ ] Verify all text readable at 1080p
- [ ] Practice presentation with timing (aim for 14:30-15:00)

---

## Q&A Preparation

**Likely Questions:**

1. **"Why 242 days sufficient?"**
   - Power analysis: n=242 gives >95% power for our hypotheses
   - Exceeds academic standards (finance typically n=30)
   - Full year coverage eliminates seasonal bias

2. **"Why not formal methods instead of LLM?"**
   - High-dimensional context integration (20+ variables)
   - Causal reasoning needed (WHY dealers forced, not just THAT)
   - Adaptability (0DTE explosion 2022-2024)
   - LLMs provide validation advantage (obfuscation testing)

3. **"How does this differ from sentiment analysis?"**
   - Sentiment = behavioral/psychological (unpredictable)
   - Regime = structural/mechanical (regulatory constraint)
   - We detect FORCED actions, not beliefs

4. **"Single asset generalization concern?"**
   - SPY is most liquid (ideal for validation)
   - Methodology generalizes (not SPY-specific)
   - Future work: cross-asset validation

5. **"Profitability only 5-11 bps—why does this matter?"**
   - **This is a feature, not a bug!**
   - Proves detection is structural, not profitable signal
   - Measuring understanding, not trading edge
   - Academic contribution is methodology, not alpha

---

## Recording Guide (Slides-Only Voiceover Format)

### Why Slides-Only is Optimal

- ✅ **Smaller file size** (50-200 MB vs 500 MB+ with camera)
- ✅ **Focuses on content** (research findings, not presenter)
- ✅ **Better audio quality** (no need for camera lighting/setup)
- ✅ **Easier editing** (re-record individual slides without continuity issues)
- ✅ **Professional standard** (typical for IEEE workshop videos)

### Technical Setup

- **Video:** PowerPoint screen recording at 1080p (1920x1080)
- **Audio:** External USB microphone (Samson, Blue Yeti, or similar)
- **Environment:** Quiet room, no background noise, no fans/AC
- **Test recording:** Do 2-3 slide test before full recording

### Recording Options

**Option 1: PowerPoint Built-in Recording (Recommended)**

- PowerPoint → Slide Show → Record Slide Show
- Records slides with audio narration per slide
- Automatically advances slides
- Exports directly to MP4

**Option 2: OBS Studio (Free)**

- Screen capture PowerPoint in slideshow mode
- Separate audio track for narration
- More editing control
- Export to MP4 (H.264 codec)

### Audio Quality Tips

- **Microphone placement:** 6-8 inches from mouth
- **Test levels:** Peak at -12 to -6 dB (not clipping)
- **Room treatment:** Record away from walls (reduces echo)
- **Noise floor:** Record 5 sec silence, verify no background hum

### Delivery Style (Voiceover Narration)

- **Pace:** Moderate, clear enunciation (not rushed)
- **Tone:** Direct, professional, neutral (avoid "I/we" when possible)
- **Emphasis:** Stress key numbers (91.2%, 71.5%, 242 days)
- **Pauses:** Brief 1-2 sec pause between major points
- **Practice:** Record with timer, aim for 14:30-15:00 total
- **Energy:** Steady engagement (not monotone, not overly excited)

### Slide Advancement Timing

- Follow the timing guide (30-90 sec per slide)
- Don't rush through complex slides (5, 9, 10)
- Pause slightly when transitioning between sections
- If using OBS, advance slides manually during recording

### Post-Recording Editing

- **Trim:** Remove pauses longer than 2-3 seconds
- **Normalize audio:** Ensure consistent volume throughout
- **Add metadata:** Title, author, conference info
- **Quality check:** Watch full video, verify all text readable
- **File specs:** MP4 container, H.264 video codec, AAC audio codec
- **Target file size:** Under 300 MB (easily achievable with slides-only)

### Final Export Settings

- **Resolution:** 1920x1080 (1080p)
- **Frame rate:** 30 fps
- **Video codec:** H.264 (High profile)
- **Audio codec:** AAC, 192 kbps, 48 kHz
- **Bitrate:** 2-4 Mbps (sufficient for slides)
- **Format:** .mp4

---

## Next Steps

### Immediate (Nov 14-15)

1. ✅ Consolidate outline + figure mapping (this document)
2. ⏭️ Build PowerPoint deck using this guide
3. ⏭️ Create 6 PowerPoint elements (tables, charts, diagrams)
4. ⏭️ Practice presentation with timing

### Video Recording (Nov 17-19)

1. ⏭️ Set up recording environment
2. ⏭️ Test audio levels and slide visibility
3. ⏭️ Record full presentation (aim for 14:30-15:00)
4. ⏭️ Edit and export final MP4

### Submission (Nov 20-23)

1. ⏭️ Upload video presentation (due Nov 20)
2. ⏭️ Complete IEEE copyright form (eCF)
3. ⏭️ Submit camera-ready PDF (PDF eXpress validated version)
4. ⏭️ Upload source tar.gz archive
5. ⏭️ Verify all submissions received (due Nov 23)

---

**Document Created:** 2025-11-14
**For:** IEEE Big Data 2025 Video Presentation
**Consolidated From:**

- `ieee_bigdata_2025_outline.md` (slide content, timing, voiceover scripts)
- `ieee_bigdata_2025_figures.md` (figure inventory, slide-by-slide mapping)
**Related:** Issue #125, Paper #1 Camera-Ready Submission
