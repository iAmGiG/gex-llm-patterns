"""
Paper #2 Figure Theme Module

Supports both SpotGamma dark theme and IEEE publication theme.
All figure scripts should import from this module for consistency.

Issue #216: Dark theme implementation
Issue #XXX: IEEE publication theme (white background)
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# =============================================================================
# PATHS
# =============================================================================

# Base paths - all relative to this module
SCRIPTS_DIR = Path(__file__).parent
FIGURES_DIR = SCRIPTS_DIR.parent
OUTPUT_DIR = FIGURES_DIR / "output"
PROJECT_ROOT = FIGURES_DIR.parent.parent.parent.parent
CACHE_DB = PROJECT_ROOT / ".cache" / "research_cache.db"

# =============================================================================
# IEEE PUBLICATION THEME (White background for journals)
# =============================================================================

IEEE_THEME = {
    # Background colors
    "background": "#FFFFFF",  # White background
    "panel_bg": "#F5F5F5",  # Light grey for panels
    "grid": "#DDDDDD",  # Light grey grid lines
    # Text colors
    "text": "#000000",  # Black text
    "dim": "#444444",  # Dark grey for secondary text
    # Accent colors (print-friendly, high contrast)
    "accent_positive": "#2E7D32",  # Dark green (detected)
    "accent_negative": "#C62828",  # Dark red (rejected)
    "accent_neutral": "#1565C0",  # Dark blue (highlight)
    "accent_warning": "#E65100",  # Dark orange (threshold)
    # Year-specific colors
    "year_2020": "#757575",  # Grey for pre-0DTE
    "year_2024": "#1565C0",  # Blue for post-0DTE
    # Border colors
    "detected_border": "#2E7D32",  # Green border
    "rejected_border": "#C62828",  # Red border
}

# =============================================================================
# DARK THEME COLORS (SpotGamma-inspired) - kept for reference
# =============================================================================

DARK_THEME = {
    # Background colors
    "background": "#1a1a2e",  # Deep navy/black
    "panel_bg": "#252540",  # Slightly lighter for panels
    "grid": "#2d2d44",  # Subtle grid lines
    # Text colors
    "text": "#ffffff",  # Primary white text
    "dim": "#666666",  # Grey for secondary text
    # Accent colors
    "accent_positive": "#00ff88",  # Neon green (bullish/detected)
    "accent_negative": "#ff4444",  # Neon red (bearish/rejected)
    "accent_neutral": "#00d4ff",  # Cyan (neutral/highlight)
    "accent_warning": "#ffaa00",  # Orange/amber (threshold)
    # Year-specific colors (for temporal comparisons)
    "year_2020": "#ff6b6b",  # Coral red for pre-0DTE
    "year_2024": "#00d4ff",  # Cyan for post-0DTE
    # Border colors
    "detected_border": "#00ff88",  # Green border for detected
    "rejected_border": "#ff4444",  # Red border for rejected
}

# Active theme - set to IEEE for publication
ACTIVE_THEME = IEEE_THEME

# Extended colors for specific figures
STAGE_COLORS = {
    "stage1": "#00d4ff",  # Cyan - Data Ingestion
    "stage2": "#00ff88",  # Green - GEX Calculation
    "stage3": "#ffaa00",  # Amber - Obfuscation
    "stage4": "#a855f7",  # Purple - Window Generation
    "stage5": "#ff6b6b",  # Coral - LLM Analysis
    "arrow": "#888888",  # Grey arrows
    "data_flow": "#4a4a6a",  # Muted for data examples
}

PHASE_COLORS = {
    "phase1": "#00d4ff",  # Cyan - baseline
    "phase2": "#ff4444",  # Red - negative control
    "phase3": "#00ff88",  # Green - full validation
    "phase4": "#a855f7",  # Purple - temporal comparison
}

YEAR_COLORS = {
    "pre_regime": "#6b8cae",  # Muted blue for pre-regime (2020-2021)
    "growing": "#7cb377",  # Muted green for growing (2022-2023)
    "structural": "#ff6b6b",  # Coral red for structural shift (2024-2025)
}

DIAGRAM_COLORS = {
    "intraday": "#00d4ff",  # Cyan for intraday
    "gamma": "#00ff88",  # Neon green for gamma
    "hedging": "#a855f7",  # Purple for hedging
    "volatility": "#ff6b6b",  # Coral for volatility
    "positioning": "#ffaa00",  # Amber for positioning
    "measurement": "#ff4444",  # Red for measurement/observable
    "transition": "#4a4a6a",  # Muted for transitions
}

OBFUSCATION_COLORS = {
    "before": "#ff6b6b",  # Coral for original data
    "after": "#00ff88",  # Green for obfuscated
    "redact": "#ff4444",  # Red for redacted elements
    "preserve": "#00d4ff",  # Cyan for preserved elements
}

# =============================================================================
# FIGURE SETTINGS
# =============================================================================

FIGURE_DEFAULTS = {
    "dpi": 300,
    "figsize_single": (10, 6),
    "figsize_wide": (12, 7),
    "figsize_tall": (10, 8),
    "figsize_double": (14, 10),
    "font_title": 14,
    "font_label": 12,
    "font_tick": 11,
    "font_annotation": 10,
    "font_legend": 11,
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def apply_dark_theme():
    """Apply dark theme to matplotlib globally."""
    plt.style.use("dark_background")


def reset_theme():
    """Reset to default matplotlib style."""
    plt.style.use("default")


def create_figure(figsize="single", dpi=None):
    """
    Create a figure with dark theme applied.

    Args:
        figsize: 'single', 'wide', 'tall', 'double', or tuple (w, h)
        dpi: Override default DPI

    Returns:
        fig, ax tuple
    """
    apply_dark_theme()

    if isinstance(figsize, str):
        size = FIGURE_DEFAULTS.get(f"figsize_{figsize}", FIGURE_DEFAULTS["figsize_single"])
    else:
        size = figsize

    dpi = dpi or FIGURE_DEFAULTS["dpi"]

    fig, ax = plt.subplots(figsize=size, dpi=dpi)
    fig.patch.set_facecolor(DARK_THEME["background"])
    ax.set_facecolor(DARK_THEME["background"])

    return fig, ax


def create_subplots(nrows, ncols, figsize="double", dpi=None):
    """
    Create subplots with dark theme applied.

    Args:
        nrows: Number of rows
        ncols: Number of columns
        figsize: 'single', 'wide', 'tall', 'double', or tuple (w, h)
        dpi: Override default DPI

    Returns:
        fig, axes tuple
    """
    apply_dark_theme()

    if isinstance(figsize, str):
        size = FIGURE_DEFAULTS.get(f"figsize_{figsize}", FIGURE_DEFAULTS["figsize_double"])
    else:
        size = figsize

    dpi = dpi or FIGURE_DEFAULTS["dpi"]

    fig, axes = plt.subplots(nrows, ncols, figsize=size, dpi=dpi)
    fig.patch.set_facecolor(DARK_THEME["background"])

    # Apply to all axes
    if hasattr(axes, "flatten"):
        for ax in axes.flatten():
            ax.set_facecolor(DARK_THEME["background"])
    else:
        axes.set_facecolor(DARK_THEME["background"])

    return fig, axes


def style_axis(ax, title=None, xlabel=None, ylabel=None, grid=True):
    """
    Apply consistent styling to an axis.

    Args:
        ax: Matplotlib axis
        title: Optional title
        xlabel: Optional x-axis label
        ylabel: Optional y-axis label
        grid: Whether to show grid
    """
    # Spine styling
    for spine in ax.spines.values():
        spine.set_color(DARK_THEME["dim"])
        spine.set_linewidth(0.5)

    # Tick styling
    ax.tick_params(colors=DARK_THEME["text"], labelsize=FIGURE_DEFAULTS["font_tick"])

    # Grid styling
    if grid:
        ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5, color=DARK_THEME["grid"])
        ax.set_axisbelow(True)

    # Labels
    if title:
        ax.set_title(title, fontsize=FIGURE_DEFAULTS["font_title"], fontweight="bold", color=DARK_THEME["text"], pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=FIGURE_DEFAULTS["font_label"], fontweight="bold", color=DARK_THEME["text"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=FIGURE_DEFAULTS["font_label"], fontweight="bold", color=DARK_THEME["text"])


def style_legend(ax, loc="best", **kwargs):
    """
    Create a styled legend.

    Args:
        ax: Matplotlib axis
        loc: Legend location
        **kwargs: Additional legend arguments

    Returns:
        Legend object
    """
    legend = ax.legend(
        loc=loc,
        fontsize=FIGURE_DEFAULTS["font_legend"],
        framealpha=0.9,
        facecolor=DARK_THEME["background"],
        edgecolor=DARK_THEME["dim"],
        **kwargs,
    )
    for text in legend.get_texts():
        text.set_color(DARK_THEME["text"])
    return legend


def save_figure(fig, filename, tight=True):
    """
    Save figure with correct settings.

    Args:
        fig: Matplotlib figure
        filename: Filename (will be saved to OUTPUT_DIR)
        tight: Whether to use tight bounding box
    """
    import io

    from PIL import Image

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_path = OUTPUT_DIR / filename

    bbox = "tight" if tight else None
    facecolor = fig.get_facecolor()

    # Save to buffer first
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=FIGURE_DEFAULTS["dpi"], bbox_inches=bbox, facecolor=facecolor, edgecolor="none")
    buf.seek(0)

    # Convert RGBA to RGB with white background (removes alpha channel)
    img = Image.open(buf)
    if img.mode == "RGBA":
        # Create white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        img = background

    img.save(output_path, "PNG", dpi=(300, 300))

    plt.close(fig)
    reset_theme()

    print(f"Figure saved: {output_path}")
    return output_path


def create_spotgamma_colormap():
    """Create SpotGamma-style colormap: dim grey -> neon cyan -> neon green."""
    colors = [
        (0.4, 0.4, 0.4),  # Dim grey for low values
        (0.0, 0.83, 1.0),  # Cyan (#00d4ff)
        (0.0, 1.0, 0.53),  # Neon green (#00ff88)
    ]
    return LinearSegmentedColormap.from_list("spotgamma", colors, N=256)


def add_stats_box(ax, text, loc="upper right", transform=None):
    """
    Add a styled statistics text box.

    Args:
        ax: Matplotlib axis
        text: Text content
        loc: Location ('upper right', 'upper left', 'lower right', 'lower left')
        transform: Optional transform (defaults to ax.transAxes)
    """
    # Parse location to coordinates
    loc_map = {
        "upper right": (0.98, 0.98, "top", "right"),
        "upper left": (0.02, 0.98, "top", "left"),
        "lower right": (0.98, 0.02, "bottom", "right"),
        "lower left": (0.02, 0.02, "bottom", "left"),
    }
    x, y, va, ha = loc_map.get(loc, loc_map["upper right"])

    transform = transform or ax.transAxes

    ax.text(
        x,
        y,
        text,
        transform=transform,
        fontsize=FIGURE_DEFAULTS["font_annotation"],
        verticalalignment=va,
        horizontalalignment=ha,
        color=DARK_THEME["text"],
        bbox=dict(boxstyle="round,pad=0.4", facecolor=DARK_THEME["panel_bg"], edgecolor=DARK_THEME["dim"], alpha=0.95),
        family="monospace",
    )
