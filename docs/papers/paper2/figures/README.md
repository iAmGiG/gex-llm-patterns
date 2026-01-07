# Paper #2 Figure Generation

Publication-quality figures for "LLM Detection of Persistent Dealer Gamma Regimes"

## SpotGamma Dark Theme (Issue #216)

All figures use consistent styling:
- Background: `#1a1a2e` (deep navy)
- Text: `#ffffff` (white)
- Accent colors: `#00ff88` (green), `#ff4444` (red), `#00d4ff` (cyan), `#ffaa00` (amber)
- Resolution: 300 DPI

## Figure Generation Scripts

| Figure | Output File | Generation Script |
|--------|-------------|-------------------|
| Fig 1 | `output/fig01_architecture.png` | `scripts/figures/fig01_architecture.py` |
| Fig 2 | `output/fig02_regime_window.png` | `scripts/figures/fig02_regime_window_example.py` |
| Fig 3 | `output/fig03_obfuscation.png` | `scripts/figures/fig03_obfuscation.py` |
| Fig 4 | `output/fig04_validation_pipeline.png` | `scripts/figures/fig04_validation_pipeline.py` |
| Fig 5 | `output/fig05_selectivity.png` | `scripts/figures/fig05_selectivity_demo.py` |
| Fig 6 | `output/fig06_gex_magnitude_distribution.png` | `scripts/figures/fig06_gex_magnitude_distribution.py` |
| Fig 7 | `output/fig07_confidence_discrimination.png` | `scripts/figures/fig07_confidence_discrimination.py` |
| Fig 8 | `output/fig08_detection_progression.png` | `scripts/visualization/fig08_detection_progression.py` |
| Fig 9 | `output/fig09_scar_tissue.png` | `scripts/visualization/fig09_scar_tissue.py` |
| Fig 10 | `output/fig10_borderline_persistence.png` | `scripts/figures/fig10_borderline_persistence.py` |
| Fig 11 | `output/fig11_threshold_sensitivity.png` | `scripts/figures/fig11_threshold_sensitivity_heatmap.py` |

## Figure Descriptions

### Methodology Figures
- **Fig 1**: System architecture pipeline (5 stages: ingestion → calculation → obfuscation → windowing → LLM)
- **Fig 2**: 30-day regime window example with criteria annotations
- **Fig 3**: Temporal obfuscation before/after transformation
- **Fig 4**: Multi-phase validation pipeline with detection rates

### Results Figures
- **Fig 5**: Framework selectivity (4-panel: detected vs rejected windows)
- **Fig 6**: GEX magnitude distribution (2020 vs 2024 histograms)
- **Fig 7**: Confidence discrimination (persistence vs LLM confidence scatter)
- **Fig 8**: Detection rate temporal progression (2020-2025 bar chart)

### Discussion Figures
- **Fig 9**: Scar tissue mechanism diagram
- **Fig 10**: Borderline persistence region analysis (3-panel)
- **Fig 11**: Threshold sensitivity heatmap

## Running the Scripts

All scripts require Python with matplotlib and numpy. Use the AutoGex conda environment:

```bash
# Single figure
/mnt/bst/a100/yxie2/cregan1/miniconda3/envs/AutoGex/bin/python scripts/figures/fig01_architecture.py

# Regenerate all figures
for script in scripts/figures/fig*.py scripts/visualization/fig*.py; do
    /mnt/bst/a100/yxie2/cregan1/miniconda3/envs/AutoGex/bin/python "$script"
done
```

## Data Dependencies

Scripts that query the ResearchCache database:
- fig06, fig07, fig08, fig10, fig11 - Query `.cache/research_cache.db`
- fig02 - Queries database but falls back to synthetic data if unavailable

Scripts with no external dependencies (synthetic/conceptual diagrams):
- fig01, fig03, fig04, fig05, fig09

## Color Palette Reference

```python
DARK_THEME = {
    'background': '#1a1a2e',      # Deep navy/black
    'text': '#ffffff',             # White text
    'grid': '#2d2d44',            # Subtle grid
    'accent_positive': '#00ff88', # Neon green
    'accent_negative': '#ff4444', # Neon red
    'accent_neutral': '#00d4ff',  # Cyan
    'accent_warning': '#ffaa00',  # Orange/amber
    'dim': '#666666',             # Grey for low values
    'panel_bg': '#252540',        # Slightly lighter for panels
}
```

## LaTeX Integration

Figures are referenced in LaTeX with:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{../figures/output/fig01_architecture.png}
\caption{LLM Regime Detection System Architecture.}
\label{fig:architecture}
\end{figure}
```

## Notes

- **DPI**: 300 (publication standard)
- **Format**: PNG (can convert to PDF/EPS for LaTeX if needed)
- **Style**: SpotGamma-inspired dark theme for visual consistency
