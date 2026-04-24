#!/usr/bin/env python3
"""
Generate Figure 4: Multi-Phase Validation Pipeline

Creates a clean horizontal comparison showing the validation phases with detection rates:
Phase 1 (71.2%) → Phase 2 (6.3%) → Phase 3 (81.2%) → Phase 4 (12.1%)

IEEE Publication Theme (white background).

Output: docs/papers/paper2/figures/output/fig04_validation_pipeline.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle
from theme import IEEE_THEME, OUTPUT_DIR, save_figure

# Phase colors for IEEE theme
PHASE_COLORS = {
    "phase1": "#1565C0",  # Blue
    "phase2": "#C62828",  # Red
    "phase3": "#2E7D32",  # Green
    "phase4": "#6A1B9A",  # Purple
}


def create_figure():
    """Create validation pipeline figure with IEEE theme."""

    plt.style.use("default")

    # Create figure - horizontal layout
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # Phase definitions
    phases = [
        {
            "name": "Phase 1",
            "title": "Baseline",
            "data": "Q1 2024",
            "detection": 71.2,
            "windows": 52,
            "color": PHASE_COLORS["phase1"],
        },
        {
            "name": "Phase 2",
            "title": "Negative Control",
            "data": "Shuffled",
            "detection": 6.3,
            "windows": 52,
            "color": PHASE_COLORS["phase2"],
        },
        {
            "name": "Phase 3",
            "title": "Full Validation",
            "data": "2024 Full",
            "detection": 81.2,
            "windows": 223,
            "color": PHASE_COLORS["phase3"],
        },
        {
            "name": "Phase 4",
            "title": "Pre-0DTE",
            "data": "2020",
            "detection": 12.1,
            "windows": 223,
            "color": PHASE_COLORS["phase4"],
        },
    ]

    # Layout parameters
    bar_height = 3.5
    bar_spacing = 3.2
    start_x = 1.0
    bar_width = 2.8
    max_rate = 100

    # Draw phases as horizontal bars with detection rate
    for i, phase in enumerate(phases):
        x = start_x + i * bar_spacing
        y_base = 2.5

        # Phase header box
        header = FancyBboxPatch(
            (x, y_base + bar_height - 0.1),
            bar_width,
            0.8,
            boxstyle="round,pad=0.05",
            facecolor=phase["color"],
            edgecolor=phase["color"],
            linewidth=0,
        )
        ax.add_patch(header)

        # Phase name in header
        ax.text(
            x + bar_width / 2,
            y_base + bar_height + 0.3,
            phase["name"],
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#FFFFFF",
        )

        # Background bar (empty)
        bg_bar = FancyBboxPatch(
            (x, y_base),
            bar_width,
            bar_height - 0.1,
            boxstyle="round,pad=0.05",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["dim"],
            linewidth=1,
        )
        ax.add_patch(bg_bar)

        # Filled bar (detection rate)
        fill_height = (phase["detection"] / max_rate) * (bar_height - 0.1)
        fill_bar = Rectangle(
            (x + 0.05, y_base + 0.05),
            bar_width - 0.1,
            fill_height - 0.1,
            facecolor=phase["color"],
            alpha=0.3,
        )
        ax.add_patch(fill_bar)

        # Detection rate - large centered number
        ax.text(
            x + bar_width / 2,
            y_base + bar_height / 2,
            f"{phase['detection']}%",
            ha="center",
            va="center",
            fontsize=26,
            fontweight="bold",
            color=phase["color"],
        )

        # Title below phase name
        ax.text(
            x + bar_width / 2,
            y_base - 0.25,
            phase["title"],
            ha="center",
            va="top",
            fontsize=14,
            fontweight="bold",
            color=IEEE_THEME["text"],
        )

        # Data label
        ax.text(
            x + bar_width / 2,
            y_base - 0.65,
            phase["data"],
            ha="center",
            va="top",
            fontsize=12,
            color=IEEE_THEME["dim"],
            style="italic",
        )

        # Window count
        ax.text(
            x + bar_width / 2,
            y_base - 1.0,
            f"n={phase['windows']}",
            ha="center",
            va="top",
            fontsize=12,
            color=IEEE_THEME["dim"],
        )

    # Arrows between phases
    arrow_y = 2.5 + bar_height / 2
    for i in range(len(phases) - 1):
        x_start = start_x + i * bar_spacing + bar_width + 0.1
        x_end = start_x + (i + 1) * bar_spacing - 0.1

        ax.annotate(
            "",
            xy=(x_end, arrow_y),
            xytext=(x_start, arrow_y),
            arrowprops=dict(arrowstyle="-|>", lw=2, color=IEEE_THEME["dim"], mutation_scale=12),
        )

    # Key finding at bottom
    finding_text = (
        "Key Result: 69.1pp discrimination between 2024 (81.2%) and 2020 (12.1%)  •  " "p < 0.0001  •  φ = 0.672"
    )
    ax.text(
        7,
        0.6,
        finding_text,
        ha="center",
        va="center",
        fontsize=13,
        color=IEEE_THEME["text"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["accent_positive"],
            linewidth=1.5,
        ),
    )

    plt.tight_layout()

    return fig


def main():
    print("Generating Validation Pipeline Figure (IEEE Theme)...")
    fig = create_figure()
    save_figure(fig, "fig04_validation_pipeline.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
