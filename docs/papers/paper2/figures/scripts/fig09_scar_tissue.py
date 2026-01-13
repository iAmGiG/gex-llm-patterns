#!/usr/bin/env python3
"""
Generate Figure 9: Scar Tissue Mechanism Diagram

This script creates a conceptual diagram illustrating how 0DTE intraday trading
creates "scar tissue" in overnight open interest positioning.

IEEE Publication Theme (white background).

Issue #168: Add 'Scar Tissue' Mechanism Diagram
Output: docs/papers/paper2/figures/output/fig09_scar_tissue.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from theme import IEEE_THEME, OUTPUT_DIR, save_figure

# Diagram colors
COLORS = {
    "intraday": "#1565C0",  # Blue
    "gamma": "#C62828",  # Red
    "hedging": "#757575",  # Grey
    "residual": "#E65100",  # Orange
    "measurement": "#2E7D32",  # Green
}


def create_figure():
    """Create scar tissue mechanism diagram with IEEE theme."""

    plt.style.use("default")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # ========================================================================
    # HORIZONTAL FLOW: Left to Right
    # ========================================================================

    box_width = 2.2
    box_height = 2.4
    y_center = 4.0
    arrow_y = y_center

    # Stage definitions
    stages = [
        {
            "title": "0DTE\nTrading",
            "subtitle": "Intraday",
            "color": COLORS["intraday"],
            "x": 0.5,
        },
        {
            "title": "Gamma\nExplosion",
            "subtitle": "Near Expiry",
            "color": COLORS["gamma"],
            "x": 3.0,
        },
        {
            "title": "Dealer\nHedging",
            "subtitle": "Pressure",
            "color": COLORS["hedging"],
            "x": 5.5,
        },
        {
            "title": "Incomplete\nUnwind",
            "subtitle": "At Close",
            "color": COLORS["residual"],
            "x": 8.0,
        },
        {
            "title": "EOD Open\nInterest",
            "subtitle": "Observable",
            "color": COLORS["measurement"],
            "x": 10.5,
        },
    ]

    # Draw stages
    for stage in stages:
        x = stage["x"]
        y = y_center - box_height / 2

        # Main box
        box = FancyBboxPatch(
            (x, y),
            box_width,
            box_height,
            boxstyle="round,pad=0.1",
            facecolor=stage["color"],
            edgecolor=stage["color"],
            linewidth=2,
            alpha=0.9,
        )
        ax.add_patch(box)

        # Title
        ax.text(
            x + box_width / 2,
            y + box_height / 2 + 0.2,
            stage["title"],
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color="#FFFFFF",
            linespacing=1.1,
        )

        # Subtitle
        ax.text(
            x + box_width / 2,
            y + 0.4,
            stage["subtitle"],
            ha="center",
            va="center",
            fontsize=11,
            color="#FFFFFF",
            alpha=0.9,
            style="italic",
        )

    # Draw arrows between stages
    for i in range(len(stages) - 1):
        x_start = stages[i]["x"] + box_width + 0.05
        x_end = stages[i + 1]["x"] - 0.05

        ax.annotate(
            "",
            xy=(x_end, arrow_y),
            xytext=(x_start, arrow_y),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=2.5,
                color=IEEE_THEME["dim"],
                mutation_scale=15,
            ),
        )

    # ========================================================================
    # SCAR TISSUE ANNOTATION
    # ========================================================================

    # Bracket under the flow
    bracket_y = y_center - box_height / 2 - 0.4
    bracket_left = stages[0]["x"]
    bracket_right = stages[-2]["x"] + box_width  # Up to "Incomplete Unwind"

    # Draw bracket lines
    ax.plot(
        [bracket_left, bracket_left],
        [bracket_y, bracket_y - 0.3],
        color=IEEE_THEME["accent_warning"],
        linewidth=2,
    )
    ax.plot(
        [bracket_right, bracket_right],
        [bracket_y, bracket_y - 0.3],
        color=IEEE_THEME["accent_warning"],
        linewidth=2,
    )
    ax.plot(
        [bracket_left, bracket_right],
        [bracket_y - 0.3, bracket_y - 0.3],
        color=IEEE_THEME["accent_warning"],
        linewidth=2,
    )

    # Scar tissue label
    ax.text(
        (bracket_left + bracket_right) / 2,
        bracket_y - 0.7,
        '"Scar Tissue" Formation',
        ha="center",
        va="top",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["accent_warning"],
    )

    # ========================================================================
    # EXPLANATION BOX
    # ========================================================================

    explanation = (
        "Mechanism: High-frequency 0DTE trading creates gamma exposure that dealers must hedge aggressively.\n"
        "When positions cannot be fully unwound by market close, the residual positioning is captured in EOD OI.\n"
        "This cumulative effect over time creates the persistent negative GEX regimes we detect."
    )

    ax.text(
        7,
        0.8,
        explanation,
        ha="center",
        va="center",
        fontsize=10,
        color=IEEE_THEME["dim"],
        style="italic",
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["dim"],
            linewidth=1,
            alpha=0.9,
        ),
    )

    # ========================================================================
    # LABELS
    # ========================================================================

    # "INTRADAY MECHANISM" label
    ax.text(
        (stages[0]["x"] + stages[2]["x"] + box_width) / 2,
        y_center + box_height / 2 + 0.5,
        "INTRADAY MECHANISM",
        ha="center",
        va="bottom",
        fontsize=12,
        fontweight="bold",
        color=COLORS["intraday"],
    )

    # "MEASUREMENT" label
    ax.text(
        stages[-1]["x"] + box_width / 2,
        y_center + box_height / 2 + 0.5,
        "MEASUREMENT",
        ha="center",
        va="bottom",
        fontsize=12,
        fontweight="bold",
        color=COLORS["measurement"],
    )

    plt.tight_layout()

    return fig


def main():
    print("Generating Scar Tissue Mechanism Figure (IEEE Theme)...")
    fig = create_figure()
    save_figure(fig, "fig09_scar_tissue.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
