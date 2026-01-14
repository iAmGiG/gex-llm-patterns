# Paper #2 Figure Generation

Publication-quality figures for "LLM Detection of Persistent Dealer Gamma Regimes"

## Quick Start

```bash
cd docs/papers/paper2/figures/scripts

# Generate all figures
python run_all.py

# Generate specific figures
python run_all.py fig01 fig05

# Check which figures exist
python run_all.py --check

# List all available figures
python run_all.py --list
```

## SpotGamma Dark Theme

All figures use consistent dark theme styling defined in `scripts/theme.py`:

| Color | Hex | Usage |
|-------|-----|-------|
| Background | `#1a1a2e` | Deep navy |
| Text | `#ffffff` | Primary text |
| Positive | `#00ff88` | Neon green (bullish/detected) |
| Negative | `#ff4444` | Neon red (bearish/rejected) |
| Neutral | `#00d4ff` | Cyan (highlight) |
| Warning | `#ffaa00` | Orange/amber (threshold) |

## Figure Scripts

All scripts are consolidated in `scripts/`:

| Figure | Script | Description | Data Source |
|--------|--------|-------------|-------------|
| Fig 1 | `fig01_architecture.py` | System Architecture Pipeline | Conceptual |
| Fig 2 | `fig02_regime_window_example.py` | 30-Day Regime Example | Database/Synthetic |
| Fig 3 | `fig03_obfuscation.py` | Temporal Obfuscation | Conceptual |
| Fig 4 | `fig04_validation_pipeline.py` | Validation Pipeline | Conceptual |
| Fig 5 | `fig05_selectivity_demo.py` | Selectivity Demo (4-panel) | Synthetic |
| Fig 6 | `fig06_gex_magnitude_distribution.py` | GEX Magnitude Distribution | ResearchCache |
| Fig 7 | `fig07_confidence_discrimination.py` | Confidence Discrimination | ResearchCache |
| Fig 8 | `fig08_detection_progression.py` | Temporal Progression (2020-2025) | ResearchCache |
| Fig 9 | `fig09_scar_tissue.py` | Scar Tissue Mechanism (2-panel) | Conceptual |
| Fig 10 | `fig10_borderline_persistence.py` | Borderline Persistence | ResearchCache |
| Fig 11 | `fig11_threshold_sensitivity_heatmap.py` | Threshold Sensitivity | ResearchCache |
| Fig 12 | `fig12_overnight_intraday_divergence.py` | Overnight vs Intraday Divergence | Database (OHLC) |

## Module Structure

```text
figures/
├── output/                  # Generated PNG files (300 DPI)
│   ├── fig01_architecture.png
│   ├── fig02_regime_window.png
│   └── ...
├── scripts/                 # Generation scripts
│   ├── theme.py            # Shared dark theme module
│   ├── run_all.py          # Master generation script
│   ├── fig01_architecture.py
│   └── ...
├── archive/                 # Legacy scripts
│   └── generate_improved_figures.py
└── README.md
```

## Theme Module API

All scripts import from `theme.py`:

```python
from theme import (
    DARK_THEME,           # Base color dictionary
    OUTPUT_DIR,           # Output path
    CACHE_DB,             # ResearchCache database path
    apply_dark_theme,     # Apply plt.style.use('dark_background')
    reset_theme,          # Reset to default style
    save_figure,          # Save with correct settings
    create_spotgamma_colormap,  # Custom colormap
)

# Extended color sets for specific figures
from theme import STAGE_COLORS      # fig01 pipeline stages
from theme import PHASE_COLORS      # fig04 validation phases
from theme import YEAR_COLORS       # fig08 temporal colors
from theme import DIAGRAM_COLORS    # fig09 mechanism diagram
from theme import OBFUSCATION_COLORS  # fig03 before/after
```

## Data Dependencies

Scripts with ResearchCache dependencies require `.cache/research_cache.db`:

- fig06, fig07, fig08, fig10, fig11

Scripts with no external dependencies (synthetic/conceptual):

- fig01, fig03, fig04, fig05, fig09

Scripts with optional database (fallback to synthetic):

- fig02

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

- **Fig 9**: Scar tissue mechanism diagram (2-panel: dynamics + phase change)
- **Fig 10**: Borderline persistence region analysis (3-panel)
- **Fig 11**: Threshold sensitivity heatmap
- **Fig 12**: Overnight vs Intraday return divergence ("Great Divergence")

## LaTeX Integration

Figures are referenced in LaTeX:

```latex
\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{../figures/output/fig01_architecture.png}
\caption{LLM Regime Detection System Architecture.}
\label{fig:architecture}
\end{figure}
```

## Technical Details

- **Resolution**: 300 DPI (publication standard)
- **Format**: PNG (LaTeX compatible)
- **Style**: IEEE publication theme (white background)
- **Total figures**: 12

## Figure Notes

### Fig 9: Scar Tissue Mechanism (Combined Two-Panel)

Updated January 2026 to use combined two-panel layout:

- **Panel A**: Time-series gamma decay curve showing intraday dynamics
- **Panel B**: "Phase Change" Before/After schematic at 4:00 PM expiration

Uses `figure*` environment in LaTeX for full two-column width.

### Fig 12: Overnight vs Intraday Divergence ("Great Divergence")

Added January 2026 to provide supplementary evidence for scar tissue mechanism:

- **Panel A**: Cumulative "jaw" chart showing overnight (Close→Open) vs intraday (Open→Close) returns
- **Panel B**: Year-by-year bar chart breakdown

Key findings:

- Pre-0DTE (2020-2021): Overnight and intraday returns roughly balanced
- Post-0DTE (2024): Overnight dominates (+21.2%) while intraday compressed (+0.6%)

**Important caveat**: This shows correlation, not causation. Alternative explanations (interest rates, market structure) cannot be excluded.

Uses `figure*` environment in LaTeX for full two-column width.

## Data Limitations & Future Figures

### Global Session Heatmap (NOT IMPLEMENTED)

**Concept**: 2D heatmap showing GEX regime impact on Tokyo/London/NY session volatility

- X-Axis: Hour of Day (0-23 ET)
- Y-Axis: GEX Regime bins
- Color: Realized volatility or absolute returns

**Data Gap**: Requires overnight futures data (8 PM - 4 AM ET) not available through Alpha Vantage:

- Alpha Vantage extended hours: 4 AM - 8 PM ET only
- Tokyo session (7 PM - 2 AM ET): NOT covered
- London early session (3 AM - 4 AM ET): NOT covered
- No S&P 500 futures (ES) data available

**Status**: Deferred to future work. Limitation documented in Discussion section.

**Alternative Data Sources** (for future implementation):

- CME ES futures (requires separate data subscription)
- Interactive Brokers historical data
- Polygon.io (may have extended hours)
