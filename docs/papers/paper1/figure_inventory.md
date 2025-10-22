# Paper #1 Figure Inventory & Reconciliation

**Last Updated**: October 18, 2025 20:30 UTC
**Purpose**: Master inventory of all figures with clear recommendations for paper inclusion

**Recent Update**: October 18 evening - Visual polish pass complete (see `FIGURE_POLISH_OCT18.md`)

---

## Quick Summary

| Category | Count | Details |
|----------|-------|---------|
| **PNG Files Total** | 25 | In `docs/papers/paper1/figures/` |
| **Core Figures (Must-Have)** | 8 | Required for paper (1, 2, 3, 4, 5, 6, 7, 8) |
| **Recommended Versions** | 8 | Specific file versions to use |
| **Alternative Versions** | 17 | Backup options or improved versions |
| **Scripts** | 11 | In `scripts/visualization/` |

---

## Figure-by-Figure Breakdown

### Figure 1: System Architecture Diagram

**Purpose**: Shows complete 6-stage validation pipeline

**Files Available**:

- ✅ `figure1_system_architecture.png` (200 KB) - **USE THIS**

**Script**: `generate_figure1_system_architecture.py`

**Status**: ✅ Complete, ready for paper
**Creator**: Chat A (Oct 16)
**Quality**: Excellent - clean flowchart, all components clear

---

### Figure 2: Obfuscation Example

**Purpose**: Before/after comparison demonstrating data obfuscation

**Files Available**:

- ✅ `figure2_obfuscation_example.png` (297 KB) - **USE THIS**

**Script**: `generate_figure2_obfuscation_example.py`

**Status**: ✅ Complete, ready for paper
**Creator**: Chat A (Oct 16)
**Quality**: Excellent - red/green highlighting effective
**Note**: Minor emoji font warnings during generation (non-blocking, visual output perfect)

---

### Figure 3: Detection vs Profitability Divergence ⭐ CRITICAL

**Purpose**: THE visual anchor - detection stable while profitability declines

**Files Available**:

- ✅ `figure3_detection_vs_profitability_300dpi.png` (221 KB) - **USE THIS** (paper version)
- ✅ `figure3_detection_vs_profitability_600dpi.png` (478 KB) - **USE THIS** (presentation version)

**Script**: `generate_figure3_detection_profitability.py`

**Status**: ✅ **POLISHED Oct 18** - Final layout optimization
**Creator**: Chat A (Oct 16, fixed Oct 17, polished Oct 18)
**Quality**: Excellent - Publication ready

**Updates**:

- **Oct 17**: Fixed misleading annotations, added Q1 data
- **Oct 18**: Layout optimization (6 iterations)
  - Y-axis now uses full vertical space (60-103%)
  - Legend moved to center right (no collisions)
  - Annotations moved to bottom summary box (no data blocking)
  - Inline labels for reference lines
  - DPI indicators added to filenames
  - Presentation version saved to `docs/presentations/oct22_research/diagrams/`

**Data**: Q1-Q4 2024 (all 4 quarters)

---

### Figure 4: GEX Profile Visualization

**Purpose**: Illustrates GEX structure that LLM analyzes

**Files Available** (4 versions):

1. `figure4_gex_profile_example.png` (246 KB) - Original, good
2. `figure4_gex_profile_comparison.png` (206 KB) - Original side-by-side
3. ✅ `figure4_gex_profile_clean.png` (236 KB) - **USE THIS** (improved)
4. `figure4_gex_comparison_clean.png` (240 KB) - Improved side-by-side

**Scripts**:

- `generate_figure4_gex_profile.py` (original)
- `generate_figure4_gex_profile_fixed.py` (improved)

**Status**: ✅ Complete, improved version ready
**Creator**: Chat B (Oct 16, improved same day)
**Quality**: **Excellent** - Best visualization quality in paper

**Improvements Made**:

- Huge NET GEX annotation (16pt bold, impossible to miss)
- Better color contrast (red #E74C3C vs green #27AE60)
- Enhanced dealer constraint explanation box
- Clearer visual hierarchy

**Recommendation**: Use `figure4_gex_profile_clean.png` (single profile, main version)

---

### Figure 5: Confidence Distribution

**Purpose**: Shows all patterns concentrated above 60% threshold

**Files Available** (2 versions):

1. ✅ `figure5_confidence_distribution.png` - **USE THIS** (grouped bar chart)
2. `figure5_confidence_distribution_kde.png` - KDE smooth version (legend repositioned Oct 18)

**Script**: `generate_figure5_confidence_distribution.py`

**Status**: ✅ **REDESIGNED Oct 18** - Complete visualization overhaul
**Creator**: Chat A (Oct 16, redesigned Oct 18)
**Quality**: Excellent - clear grouped bar chart

**Updates**:

- **Oct 18**: Complete redesign from overlapping histogram → grouped bar chart
  - Patterns now side-by-side instead of stacked (clearly distinguishable)
  - Legend: upper left (sparse area)
  - Stats box: mid-right (empty space)
  - Threshold line: zorder=2 (renders behind bars)
  - No visual collisions

**Recommendation**: Use grouped bar chart version (patterns clearly separated)

---

### Figure 6: Pattern Detection Visualization

**Purpose**: Multi-pattern performance comparison

**Files Available** (YAML-based versions, Oct 18):

1. ✅ `figure6_pattern_performance_bars_yaml.png` - **USE THIS** (grouped bar chart)
2. `figure6_detection_vs_accuracy_scatter_yaml.png` - Scatter plot (polished Oct 18)
3. `figure6_performance_matrix_yaml.png` - Quadrant visualization

**Script**: `generate_figure6_yaml_data.py`

**Status**: ✅ **POLISHED Oct 18** - Layout optimization
**Creator**: Chat B (Oct 16 hardcoded, Oct 18 YAML rebuild + polish)
**Quality**: Excellent - Publication ready

**Updates**:

- **Oct 18 AM**: Rebuilt with actual YAML data (was hardcoded)
- **Oct 18 PM**: Visual polish (3 iterations)
  - Scatter plot: Smaller markers (×2 instead of ×3)
  - Legend: Moved to upper right, markerscale=0.5
  - X-axis: Starts at 58 (makes 60% threshold visible)
  - Bar chart: Legend optimized by linter

**Recommendation**: Use `figure6_pattern_performance_bars_yaml.png` (grouped bar chart, clearest presentation)

---

### Figure 7: Biased vs Unbiased Comparison

**Purpose**: Demonstrates prompt bias impact on detection

**Files Available** (5 versions):

1. ✅ `figure7_biased_unbiased_comparison.png` (309 KB) - **USE THIS** (original dual y-axis)
2. `figure7_simple_detection_comparison.png` (222 KB) - Detection only
3. `figure7_detection_comparison_clean.png` (276 KB) - Improved with delta annotations
4. `figure7_detection_and_accuracy_panels.png` (295 KB) - Dual panel side-by-side
5. `figure7_minimal_publication.png` (116 KB) - Minimal design

**Scripts**:

- `generate_figure7_biased_unbiased.py` (original)
- `generate_figure7_biased_unbiased_fixed.py` (improved)

**Status**: ✅ Multiple good versions available
**Creator**: Chat B (Oct 16, improved same day)
**Quality**: All versions good, improved versions add clarity

**Recommendation**:

- **Primary**: Use `figure7_biased_unbiased_comparison.png` (original dual y-axis, works well)
- **Alternative**: Use `figure7_detection_comparison_clean.png` (has delta annotations, clearer message)

---

### Figure 8: Validation Funnel

**Purpose**: Shows validation pipeline progression (726 → 519 → 473)

**Files Available** (3 versions):

1. ✅ `figure8_validation_funnel.png` (187 KB) - **USE THIS** (traditional funnel)
2. `figure8_validation_flow.png` (269 KB) - Sankey-style flow
3. `figure8_validation_breakdown.png` (240 KB) - By pattern breakdown

**Script**: `generate_figure8_validation_funnel.py`

**Status**: ✅ Complete, all versions excellent
**Creator**: Chat B (Oct 16)
**Quality**: **Excellent** - Clean, professional funnel

**Recommendation**: Use `figure8_validation_funnel.png` (traditional funnel, most intuitive)

---

## Script Organization

**Location**: `scripts/visualization/`

### By Figure

| Figure | Scripts | Status |
|--------|---------|--------|
| Figure 1 | `generate_figure1_system_architecture.py` | ✅ Ready |
| Figure 2 | `generate_figure2_obfuscation_example.py` | ✅ Ready |
| Figure 3 | `generate_figure3_detection_profitability.py` | ✅ Fixed Oct 17 |
| Figure 4 | `generate_figure4_gex_profile.py` (original)<br>`generate_figure4_gex_profile_fixed.py` (improved) | ✅ Both available |
| Figure 5 | `generate_figure5_confidence_distribution.py` | ✅ Ready |
| Figure 6 | `generate_figure6_detection_heatmap.py` (original)<br>`generate_figure6_detection_heatmap_fixed.py` (improved) | ✅ Both available |
| Figure 7 | `generate_figure7_biased_unbiased.py` (original)<br>`generate_figure7_biased_unbiased_fixed.py` (improved) | ✅ Both available |
| Figure 8 | `generate_figure8_validation_funnel.py` | ✅ Ready |

**Note**: Chat B created "*_fixed.py" versions to address issues found in initial generation

---

## Recommended Figures for Paper

### Core 8 Figures (Must Include)

1. ✅ **Figure 1**: `figure1_system_architecture.png` (200 KB)
2. ✅ **Figure 2**: `figure2_obfuscation_example.png` (297 KB)
3. ✅ **Figure 3**: `figure3_detection_vs_profitability.png` (191 KB) OR hires version (421 KB)
4. ✅ **Figure 4**: `figure4_gex_profile_clean.png` (236 KB) ⭐ Use improved version
5. ✅ **Figure 5**: `figure5_confidence_distribution.png` (181 KB)
6. ✅ **Figure 6**: `figure6_pattern_performance_bars.png` (263 KB) ⭐ Use improved version
7. ✅ **Figure 7**: `figure7_biased_unbiased_comparison.png` (309 KB)
8. ✅ **Figure 8**: `figure8_validation_funnel.png` (187 KB)

**Total Size**: ~1.9 MB (standard res) or ~2.1 MB (with hires Fig 3)

---

## Alternative/Supplementary Figures

**Available for appendix or backup**:

### Figure 4 Alternatives

- `figure4_gex_profile_example.png` (original, still good)
- `figure4_gex_comparison_clean.png` (side-by-side comparison)

### Figure 5 Alternatives

- `figure5_confidence_distribution_kde.png` (smooth curves)

### Figure 6 Alternatives

- `figure6_detection_heatmap.png` (heatmap format, has cosmetic issue)
- `figure6_detection_vs_accuracy_scatter.png` (scatter plot)
- `figure6_performance_matrix.png` (quadrant viz)

### Figure 7 Alternatives

- `figure7_detection_comparison_clean.png` (with delta annotations)
- `figure7_detection_and_accuracy_panels.png` (dual panel)
- `figure7_minimal_publication.png` (minimal design)

### Figure 8 Alternatives

- `figure8_validation_flow.png` (Sankey style)
- `figure8_validation_breakdown.png` (by pattern)

---

## Quality Issues Summary

### ✅ RESOLVED Issues

**Figure 3** (FIXED Oct 17):

- Problem: Misleading annotations showing wrong detection trend
- Fix: Regenerated with correct data-driven annotations
- Status: **Now publication-ready**

**Figure 4** (IMPROVED Oct 16):

- Problem: NET GEX annotation too small
- Fix: Created improved version with huge annotation
- Status: **Use improved version**

**Figure 6** (IMPROVED Oct 16):

- Problem: Original heatmap had duplicate columns (misleading format)
- Fix: Created bar chart version with clear presentation
- Status: **Use improved bar chart version**

**Figure 7** (IMPROVED Oct 16):

- Problem: Original dual y-axis could be clearer
- Fix: Created version with delta annotations
- Status: **Both versions good, improved adds clarity**

### ⚠️ Minor Issues (Non-Blocking)

**Figure 2**: Unicode emoji font warnings during generation

- Impact: COSMETIC ONLY - PNG output is perfect
- Action: None needed

**Figure 6 Heatmaps**: Duplicate columns showing stable values

- Impact: COSMETIC ONLY - Data is accurate, format is suboptimal
- Action: Use improved bar chart instead (recommended above)

---

## Creator Attribution

| Figure | Primary Creator | Status |
|--------|----------------|--------|
| Figure 1 | Chat A | Original, ready |
| Figure 2 | Chat A | Original, ready |
| Figure 3 | Chat A | Original + fixed |
| Figure 4 | Chat B | Original + improved |
| Figure 5 | Chat A | Original, ready |
| Figure 6 | Chat B | Original + improved |
| Figure 7 | Chat B | Original + improved |
| Figure 8 | Chat B | Original, ready |

**Chat A**: Figures 1, 2, 3, 5 (technical/data extraction focus)
**Chat B**: Figures 4, 6, 7, 8 (presentation/visualization focus)

---

## File Management

### Current State

- ✅ All PNG files in: `docs/papers/paper1/figures/`
- ✅ All scripts in: `scripts/visualization/`
- ✅ All captions in: `docs/papers/paper1/figures/captions.md`
- ✅ No stray .py or .m files in figures directory

### Disk Usage

- **25 PNG files**: ~5.6 MB total
- **11 Python scripts**: ~50 KB total
- **Documentation**: ~40 KB (captions.md, FIGURE_*.md files)

---

## LaTeX Integration Plan

### Figure Placement

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figures/figure1_system_architecture.png}
\caption{Validation pipeline architecture...}
\label{fig:architecture}
\end{figure}
```

### Special Case - Figure 3 (Full Width)

```latex
\begin{figure*}[t]
\centering
\includegraphics[width=0.9\textwidth]{figures/figure3_detection_vs_profitability.png}
\caption{Detection persists despite declining profitability...}
\label{fig:divergence}
\end{figure*}
```

**Note**: Use `figure*` environment for Figure 3 to span both columns (critical figure benefits from larger size)

---

## Next Steps

1. ✅ All figures generated and quality-checked
2. ✅ Recommended versions identified
3. ⏳ Update captions.md to reflect recommended file versions
4. ⏳ Convert to LaTeX figure environments
5. ⏳ Integrate into paper sections

---

## References to Other Documentation

- **Captions**: See `figures/captions.md` for detailed figure captions
- **Quality Review**: See `FIGURE_REVIEW.md` for detailed quality assessment
- **Chat B Fixes**: See `FIGURE_FIXES_SUMMARY.md` for Chat B's YAML rebuild (Oct 18 AM)
- **Oct 18 Polish**: See `FIGURE_POLISH_OCT18.md` for visual refinement session (Oct 18 PM)
- **Paper Status**: See `PAPER1_STATUS_SUMMARY.md` for overall paper completion
- **Tables**: See `TABLE_SUMMARY.md` for table formatting guidance

---

**Status**: ✅ ALL FIGURES COMPLETE AND READY FOR PAPER

**Confidence**: HIGH - All quality issues resolved, clear recommendations provided
