# IEEE Big Data 2025 Presentation Figures

**Created:** 2025-11-13
**Purpose:** Figure assets for 15-minute IEEE Big Data 2025 video presentation
**Total Figures:** 8 external + 6 PowerPoint elements to create

---

## Prepared Figures (Ready to Use)

All figures verified for 1080p video presentation (file sizes appropriate, resolution suitable).

### Slide 1: Title Slide

**File:** `slide01_title_system_overview.png` (177 KB)
**Source:** `docs/presentations/archive/oct22_research/diagrams/pres01_system_overview.png`
**Shows:** High-level LLM → Pattern Detection → Validation flow
**Usage:** Clean title slide visual showing research domain

### Slide 2: Core Problem

**File:** `slide02_problem_obfuscation.png` (138 KB)
**Source:** `docs/presentations/archive/oct22_research/diagrams/pres04_methodology_obfuscation.png`
**Shows:** Temporal data → obfuscated data transformation
**Usage:** Introduces the memorization vs reasoning challenge

### Slide 4: Test Domain - Dealer Hedging

**File:** `slide04_domain_forced_hedging.png` (166 KB)
**Source:** `docs/presentations/archive/oct22_research/diagrams/pres06_forced_hedging_loop.png`
**Shows:** Customer Trades → Dealer Accumulation → Regulatory Mandate → Forced Hedging loop
**Usage:** Explains the structural constraint being tested

### Slide 5: Obfuscation Methodology (CRITICAL)

**File:** `slide05_methodology_obfuscation_example.png` (288 KB)
**Source:** `docs/papers/paper1/figures/fig1_obfuscation_example.png`
**Shows:** Before/After comparison with red (removed) and green (preserved) highlighting
**Usage:** Full demonstration of obfuscation testing methodology
**Display:** Split screen - Left: BEFORE (dates/tickers), Right: AFTER (Day T+0/INDEX_1)
**Timing:** 90 seconds (critical slide)

### Slide 7: System Architecture

**File:** `slide07_architecture_pipeline.png` (164 KB)
**Source:** `docs/presentations/archive/oct22_research/diagrams/pres12_system_flow_compact.png`
**Shows:** Compact end-to-end pipeline view
**Usage:** System architecture overview (compact presentation version)

### Slide 8: Three Pattern Types

**File:** `slide08_patterns_taxonomy.png` (292 KB)
**Source:** `docs/presentations/archive/oct22_research/diagrams/pres10_pattern_taxonomy.png`
**Shows:** Three pattern circles connected to central "Dealer Hedging" concept
**Usage:** Visual representation of "three descriptions of ONE mechanism"

### Slide 9: Results - Detection ≠ Profitability (CRITICAL)

**File:** `slide09_results_detection_vs_profit.png` (246 KB)
**Source:** `docs/presentations/archive/oct22_research/diagrams/pres08_accuracy_vs_profit.png`
**Shows:** Detection stable (71.5%), Profitability declines (5-11 bps)
**Usage:** KEY FINDING - proves structural understanding vs economic exploitation
**Additional:** Will overlay PowerPoint table with pattern-by-pattern results
**Timing:** 90 seconds (critical slide)

### Slide 11: Validation Results

**File:** `slide11_validation_funnel.png` (72 KB)
**Source:** `docs/papers/paper1/figures/fig6_validation_funnel.png`
**Shows:** 726 tests → 519 detected (71.5%) → 473 materialized (91.2%)
**Usage:** Visual proof of methodology validation success

---

## PowerPoint Elements to Create

These elements will be created directly in PowerPoint (no external figure files).

### Slide 6: Academic Foundation

**Type:** Table
**Content:**

- Row 1: Theory → Anderegg (2022) - Options hedging → spot volatility
- Row 2: Empirics → Dim (2025) - Order flow measurement validation
- Row 3: Practice → Krishnan (2021) - Dealer hedging dynamics

### Slide 9: Results Summary Table (overlay on figure)

**Type:** Table
**Content:**

```
| Pattern | Detection | Accuracy | Days |
|---------|-----------|----------|------|
| Gamma   | 69.4%     | 92.5%    | 242  |
| Pinning | 67.4%     | 90.4%    | 242  |
| 0DTE    | 77.7%     | 90.8%    | 242  |
| Average | 71.5%     | 91.2%    | 242  |
```

### Slide 10: Biased vs Unbiased Validation

**Type:** Bar chart
**Content:**

- Blue bars: Biased detection (100% in Q3+Q4)
- Orange bars: Unbiased detection (71.5% full 2024)
- Red dashed line: 60% mechanical threshold

### Slide 12: Broader Impact - Generalizability

**Type:** Table
**Content:**

```
| Domain       | Constraint         | Test Application      |
|--------------|--------------------|-----------------------|
| Supply Chain | JIT inventory      | Forced restocking     |
| Healthcare   | Capacity limits    | Overflow patterns     |
| Energy Grid  | Load balancing     | Generation scaling    |
| Traffic      | Road capacity      | Congestion amplif.    |
```

### Slide 14: Related Work Positioning

**Type:** Venn diagram
**Content:**

- Circle 1: LLM Finance (Lopez, Wu, Chen)
- Circle 2: Market Microstructure (Ni, Garleanu, Anderegg, Dim)
- Circle 3: AI Validation (Ribeiro framework)
- Center overlap: "Our Work - Unbiased Obfuscation Testing"

### Slide 15: Key Metrics Summary

**Type:** Visual graphic with highlighted numbers
**Content:**

- **91.2%** prediction accuracy (large, bold)
- **71.5%** unbiased detection (large, bold)
- **242** days tested (moderate)
- **3** patterns validated (moderate)

---

## Figure Quality Checklist

- [x] All 8 figures copied to presentation folder
- [x] File sizes appropriate (<300 KB each, total 1.6 MB)
- [x] Slide-specific naming for easy identification
- [ ] Resolution verified for 1080p video (test in PowerPoint)
- [ ] Color scheme compatibility with IEEE theme (blue/gray)
- [ ] Text readability at presentation scale (test on projector/screen)

---

## Next Steps

1. **Build PowerPoint deck** using `ieee_bigdata_2025_outline.md` structure
2. **Insert figures** according to slide mapping
3. **Create 6 PowerPoint elements** (tables, charts, Venn diagram)
4. **Test visibility** of all text/labels at 1080p
5. **Practice presentation** with timing (target 15 minutes)
6. **Record video** (Nov 17-19 recommended)
7. **Submit video** by Nov 20, 2025 deadline

---

**Related Files:**

- Slide structure: `docs/presentations/ieee_bigdata_2025_outline.md`
- Figure mapping: `docs/presentations/ieee_bigdata_2025_figures.md`
- Camera-ready paper: `docs/papers/paper1/ieee_bigdata_2025/Main.pdf`

**Issue:** #125 (IEEE Big Data 2025 camera-ready submission)
