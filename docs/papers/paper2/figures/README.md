# Paper #2 Figures

Publication-quality figures for "LLM Detection of Persistent Dealer Gamma Regimes"

## Generated Figures

### Figure 1: Multi-Year Detection Rates (2020-2025)

**File**: `output/figure1_multiyear_detection.png`

Bar chart showing sharp 2020→2021 structural transition (12.1% → 100% detection).

- Annotates 87.9 pp increase (p < 10⁻⁸⁶, φ = 0.909)
- Color-coded: Red (pre-transition), Green (post-transition), Yellow (volatile 2024)
- Shows window counts for each year

**Key Finding**: Sharp transition, not gradual evolution

### Figure 2: 2020 vs 2024 Metrics Comparison

**File**: `output/figure2_2020_vs_2024.png`

Side-by-side grouped bar chart comparing 4 metrics:

- Detection Rate: 12.1% → 81.2% (+69.1 pp)
- Avg Confidence: 72.4% → 86.8% (+14.4 pts)
- Persistence: 83.3% → 96.0% (+12.7 pp)
- Avg Magnitude: $2.85B → $13.95B (4.9x increase)

**Key Finding**: Comprehensive market structure change across all metrics

### Figure 3: Phase 2 Negative Controls

**File**: `output/figure3_negative_controls.png`

Grouped bar chart showing false positive rates for 3 synthetic tests:

- Shuffle Test: 61.1% (2024) vs 12.1% (2020) - PASS (5x discrimination)
- Transitional Test (7-10 flips): 0% both years - PASS
- Low Magnitude (<$5B): 0% both years - PASS

**Key Finding**: Framework selectivity validated (0% FP on critical tests)

### Figure 4: GEX Magnitude Evolution

**File**: `output/figure4_gex_evolution.png`

Line chart showing average GEX magnitude across 6 years:

- 2020: $17.3B (pre-0DTE baseline)
- 2021: $27.2B (+58% jump)
- 2022-2025: Stable $20-32B range
- Annotates structural transition at 2020→2021 boundary

**Key Finding**: Magnitude increased 58% during transition year

## Generation

### Requirements

```bash
# Standard Python scientific stack
pip install matplotlib numpy pandas
```

### Run

```bash
cd a:\Projects\gex-llm-patterns
python docs/papers/paper2/figures/scripts/generate_paper2_figures.py
```

### Output

All figures saved to `docs/papers/paper2/figures/output/` at 300 DPI (publication quality)

## Notes

- **DPI**: 300 (publication standard)
- **Font**: Serif family for academic publications
- **Format**: PNG (can convert to PDF/EPS for LaTeX if needed)
- **Color Scheme**: Colorblind-friendly palette
- **Style**: Consistent with Paper #1 figures

## LaTeX Integration

Add to paper with:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figures/figure1_multiyear_detection.png}
\caption{Multi-Year Detection Rates showing sharp 2020→2021 structural transition.}
\label{fig:multiyear}
\end{figure}
```

## Windows Compatibility

Script is Windows-compatible (no Unicode emoji in console output after fix).
If matplotlib import fails on HPCC, update environment:

```bash
# On HPCC/Linux cluster
conda install matplotlib numpy pandas
# or
pip install --upgrade matplotlib
```
