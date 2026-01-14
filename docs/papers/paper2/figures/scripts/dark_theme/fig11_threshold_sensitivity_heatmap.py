#!/usr/bin/env python3
"""
Generate Threshold Sensitivity Heatmap (Issue #210)

Creates 2D heatmap showing discrimination gap across parameter space
to demonstrate framework robustness to threshold selection.

Updated with SpotGamma-inspired dark theme (Issue #216).

Output: docs/papers/paper2/figures/output/fig11_threshold_sensitivity.png
"""

import json
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle
from theme import (
    CACHE_DB,
    DARK_THEME,
    OUTPUT_DIR,
    apply_dark_theme,
    create_spotgamma_colormap,
    reset_theme,
    save_figure,
)

# Parameter ranges to test
PERSISTENCE_THRESHOLDS = [60, 65, 70, 75, 80]
MAGNITUDE_THRESHOLDS = [3, 4, 5, 6, 7]
STABILITY_THRESHOLD = 5  # Fixed at ≤5 flips

# Current paper parameters
CURRENT_PERSISTENCE = 70
CURRENT_MAGNITUDE = 5


def query_data():
    """Query window data from ResearchCache."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            substr(trading_date, 1, 4) as year,
            json_extract(structured_output, '$.persistence_pct') as persistence,
            json_extract(structured_output, '$.avg_magnitude_billions') as magnitude,
            json_extract(structured_output, '$.sign_flips') as flips
        FROM llm_detections
        WHERE structured_output IS NOT NULL
          AND substr(trading_date, 1, 4) IN ('2020', '2024')
    """
    )

    rows = cursor.fetchall()
    conn.close()

    data = {"2020": [], "2024": []}
    for year, persistence, magnitude, flips in rows:
        if all(v is not None for v in [persistence, magnitude, flips]):
            data[year].append({"persistence": float(persistence), "magnitude": float(magnitude), "flips": int(flips)})

    return data


def calculate_detection_rate(windows, persistence_thresh, magnitude_thresh, stability_thresh=5):
    """Calculate detection rate for given thresholds."""
    if not windows:
        return 0.0

    detected = sum(
        1
        for w in windows
        if w["persistence"] >= persistence_thresh
        and w["magnitude"] >= magnitude_thresh
        and w["flips"] <= stability_thresh
    )
    return detected / len(windows) * 100


def create_figure(data):
    """Create threshold sensitivity heatmap with dark theme."""

    # Calculate discrimination gaps for each parameter combination
    gaps = np.zeros((len(PERSISTENCE_THRESHOLDS), len(MAGNITUDE_THRESHOLDS)))
    rates_2020 = np.zeros_like(gaps)
    rates_2024 = np.zeros_like(gaps)

    for i, p_thresh in enumerate(PERSISTENCE_THRESHOLDS):
        for j, m_thresh in enumerate(MAGNITUDE_THRESHOLDS):
            rate_2020 = calculate_detection_rate(data["2020"], p_thresh, m_thresh)
            rate_2024 = calculate_detection_rate(data["2024"], p_thresh, m_thresh)
            gaps[i, j] = rate_2024 - rate_2020
            rates_2020[i, j] = rate_2020
            rates_2024[i, j] = rate_2024

    # Set dark theme
    apply_dark_theme()

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    fig.patch.set_facecolor(DARK_THEME["background"])
    ax.set_facecolor(DARK_THEME["background"])

    # Create SpotGamma-style colormap
    spotgamma_cmap = create_spotgamma_colormap()

    # Create heatmap with SpotGamma colormap
    im = ax.imshow(gaps, cmap=spotgamma_cmap, aspect="auto", vmin=50, vmax=100)

    # Add colorbar with dark theme styling
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Discrimination Gap (pp)\n(2024% - 2020%)", fontsize=11, fontweight="bold", color=DARK_THEME["text"])
    cbar.ax.yaxis.set_tick_params(color=DARK_THEME["text"])
    cbar.outline.set_edgecolor(DARK_THEME["dim"])
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=DARK_THEME["text"])

    # Set ticks and labels
    ax.set_xticks(np.arange(len(MAGNITUDE_THRESHOLDS)))
    ax.set_yticks(np.arange(len(PERSISTENCE_THRESHOLDS)))
    ax.set_xticklabels([f"${m}B" for m in MAGNITUDE_THRESHOLDS], fontsize=11, color=DARK_THEME["text"])
    ax.set_yticklabels([f"{p}%" for p in PERSISTENCE_THRESHOLDS], fontsize=11, color=DARK_THEME["text"])

    # Labels
    ax.set_xlabel("Magnitude Threshold", fontsize=12, fontweight="bold", color=DARK_THEME["text"])
    ax.set_ylabel("Persistence Threshold", fontsize=12, fontweight="bold", color=DARK_THEME["text"])
    ax.set_title(
        "Threshold Sensitivity Analysis:\nDiscrimination Gap Across Parameter Space",
        fontsize=14,
        fontweight="bold",
        pad=15,
        color=DARK_THEME["text"],
    )

    # Add text annotations in each cell
    for i in range(len(PERSISTENCE_THRESHOLDS)):
        for j in range(len(MAGNITUDE_THRESHOLDS)):
            gap = gaps[i, j]
            r2020 = rates_2020[i, j]
            r2024 = rates_2024[i, j]

            # Use dark text on bright cells, white text on dim cells
            text_color = DARK_THEME["background"] if gap > 75 else DARK_THEME["text"]

            # Main gap value
            ax.text(j, i, f"{gap:.0f}pp", ha="center", va="center", fontsize=12, fontweight="bold", color=text_color)

            # Smaller annotation with rates
            ax.text(
                j,
                i + 0.32,
                f"({r2024:.0f}%-{r2020:.0f}%)",
                ha="center",
                va="center",
                fontsize=10,
                color=text_color,
                alpha=0.8,
            )

    # Highlight current parameters (70%, $5B)
    current_i = PERSISTENCE_THRESHOLDS.index(CURRENT_PERSISTENCE)
    current_j = MAGNITUDE_THRESHOLDS.index(CURRENT_MAGNITUDE)

    # Draw rectangle around current parameters with neon cyan
    rect = plt.Rectangle(
        (current_j - 0.5, current_i - 0.5), 1, 1, fill=False, edgecolor=DARK_THEME["accent_neutral"], linewidth=3
    )
    ax.add_patch(rect)

    # Add star marker
    ax.plot(
        current_j,
        current_i,
        "*",
        markersize=25,
        color=DARK_THEME["accent_neutral"],
        markeredgecolor=DARK_THEME["background"],
        markeredgewidth=1.5,
    )

    # Add legend for current parameters
    ax.text(
        0.02,
        0.98,
        "★ Current Parameters\n    (70%, $5B)",
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        verticalalignment="top",
        color=DARK_THEME["accent_neutral"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor=DARK_THEME["panel_bg"],
            edgecolor=DARK_THEME["accent_neutral"],
            alpha=0.95,
        ),
    )

    # Add summary statistics
    min_gap = gaps.min()
    max_gap = gaps.max()
    mean_gap = gaps.mean()
    all_above_50 = (gaps >= 50).all()

    stats_text = (
        f'All combinations >50pp: {"✓" if all_above_50 else "✗"}\n'
        f"Range: {min_gap:.0f}-{max_gap:.0f}pp\n"
        f"Mean: {mean_gap:.0f}pp"
    )
    ax.text(
        0.98,
        0.02,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="bottom",
        horizontalalignment="right",
        color=DARK_THEME["text"],
        bbox=dict(boxstyle="round,pad=0.3", facecolor=DARK_THEME["panel_bg"], edgecolor=DARK_THEME["dim"], alpha=0.95),
        family="monospace",
    )

    # Style spines
    for spine in ax.spines.values():
        spine.set_color(DARK_THEME["dim"])

    plt.tight_layout()

    print(f"\nThreshold Sensitivity Results:")
    print(f"  Parameter combinations tested: {len(PERSISTENCE_THRESHOLDS) * len(MAGNITUDE_THRESHOLDS)}")
    print(f"  All combinations >50pp discrimination: {all_above_50}")
    print(f"  Discrimination range: {min_gap:.1f}pp - {max_gap:.1f}pp")
    print(f"  Mean discrimination: {mean_gap:.1f}pp")
    print(f"\nCurrent parameters (70%, $5B):")
    print(f"  2020 detection: {rates_2020[current_i, current_j]:.1f}%")
    print(f"  2024 detection: {rates_2024[current_i, current_j]:.1f}%")
    print(f"  Discrimination gap: {gaps[current_i, current_j]:.1f}pp")

    # Print full table
    print("\nFull discrimination table:")
    header = "Pers\\Mag"
    print(f"{header:>8}", end="")
    for m in MAGNITUDE_THRESHOLDS:
        print(f"  ${m}B", end="")
    print()
    for i, p in enumerate(PERSISTENCE_THRESHOLDS):
        print(f"{p}%", end="")
        for j in range(len(MAGNITUDE_THRESHOLDS)):
            print(f"  {gaps[i,j]:4.0f}", end="")
        print()

    return fig


def main():
    print("Generating Threshold Sensitivity Heatmap (Issue #210, Dark Theme #216)...")
    print(f"Database: {CACHE_DB}")

    # Query data
    data = query_data()
    print(f"\nData loaded: 2020={len(data['2020'])} windows, 2024={len(data['2024'])} windows")

    # Create heatmap
    fig = create_figure(data)
    save_figure(fig, "fig11_threshold_sensitivity.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
