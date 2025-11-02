# Presentation Figure Guide

**Last Updated**: October 21, 2025
**Purpose**: Figure selection guide for Oct 22 symposium presentation

---

## Final Presentation Figures (pres## naming scheme)

All figures optimized for presentation (1920x1080, 120 DPI, high contrast colors for well-lit rooms).

### Main Presentation Figures (9 used)

| Figure | Filename | Purpose | Size |
|--------|----------|---------|------|
| **Greex Explanation** | `pres02_greeks_gamma.png` | Delta vs Gamma, gamma as "urgency beacon" | 222 KB |
| **System Architecture** | `pres12_system_flow_compact.png` | Compact 5-stage pipeline | 164 KB |
| **The Constraint** | `pres06_forced_hedging_loop.png` | Forced hedging loop (WHO→WHOM→WHAT) | 166 KB |
| **Obfuscation Testing** | `pres04_methodology_obfuscation.png` | Before/after obfuscation comparison | 138 KB |
| **Biased vs Unbiased** | `pres05_methodology_refinement.png` | 100% → 69.4% detection comparison | 228 KB |
| **Detection Progression** | `pres07_detection_progression.png` | Results table (100% → 71.5%) | 173 KB |
| **Key Finding** | `pres08_accuracy_vs_profit.png` | Accuracy ≠ Profitability divergence | 246 KB |
| **Takeaway** | `pres09_llm_causal_framework.png` | LLMs as causal framework detectors | 271 KB |
| **Pattern Taxonomy** | `pres10_pattern_taxonomy.png` | Structural vs narrative patterns | 212 KB |

### Appendix/Backup Figures (3 additional)

| Figure | Filename | Purpose | Size |
|--------|----------|---------|------|
| **GEX Explanation** | `pres03_gex_vs_gamma.png` | GEX ≠ Gamma (Greek) clarification | 236 KB |
| **Full Pipeline** | `pres01_system_overview.png` | Complete 6-stage pipeline (not used) | 177 KB |
| **Detailed Architecture** | `pres11_system_architecture_layered.png` | Layered system view | 371 KB |

---

## Figure Selection Recommendations

### Core Slides (Must Include)

1. **pres02_greeks_gamma.png** - Foundation for understanding GEX
2. **pres12_system_flow_compact.png** - Shows complete methodology
3. **pres09_llm_causal_framework.png** - Main contribution/takeaway
4. **pres08_accuracy_vs_profit.png** - Key empirical finding

### Optional Depending on Time

- **pres06_forced_hedging_loop.png** - If explaining dealer constraints in detail
- **pres05_methodology_refinement.png** - If discussing prompt bias investigation
- **pres07_detection_progression.png** - If showing methodological progression
- **pres10_pattern_taxonomy.png** - If discussing pattern classification

### Appendix Only

- **pres03_gex_vs_gamma.png** - Use if audience asks "what is GEX?"
- **pres11_system_architecture_layered.png** - Use if asked about technical architecture
- **pres01_system_overview.png** - Alternative to pres12 (more detailed)

---

## Design Specifications

**Resolution**: 1920×1080 (16:9 aspect ratio)
**DPI**: 120 (screen-optimized for projection)
**Colors**: High-contrast dark colors (navy #003366, dark red #8B0000, dark green #006400)
**Line Weight**: 4-6pt (thicker than paper figures)
**Text Size**: 18-28pt (larger than paper figures)
**Background**: White (no transparency)
**Venue**: Well-lit academic room (not dark auditorium)

---

## Generation Scripts

All generation scripts available in `scripts/` folder with matching pres## naming:

- `scripts/pres01_system_overview.py`
- `scripts/pres02_greeks_gamma.py`
- `scripts/pres03_gex_vs_gamma.py`
- `scripts/pres04_methodology_obfuscation.py`
- `scripts/pres05_methodology_refinement.py`
- `scripts/pres07_detection_progression.py`
- `scripts/pres08_accuracy_vs_profit.py`
- `scripts/pres09_llm_causal_framework.py`
- `scripts/pres10_pattern_taxonomy.py`

**Missing scripts** (can recreate if needed):

- pres06_forced_hedging_loop.py
- pres11_system_architecture_layered.py
- pres12_system_flow_compact.py

---

## Figure Quality Notes

**Optimization for Presentation**:

- ✅ High contrast (no yellow/pastel colors)
- ✅ Thick lines (5-6pt vs 2-3pt for paper)
- ✅ Large text (18-28pt vs 9-13pt for paper)
- ✅ White backgrounds (avoids transparency issues with projectors)
- ✅ 16:9 aspect ratio (standard slide format)
- ✅ Screen-optimized DPI (120 vs 300/600 for paper)

**All figures verified for**:

- Readability from back of room
- Color visibility in bright lighting
- No overlapping elements
- Proper z-ordering

---

**Last Updated**: October 21, 2025
**Total Files**: 12 PNG figures + 9 generation scripts
**Status**: ✅ Ready for symposium presentation
