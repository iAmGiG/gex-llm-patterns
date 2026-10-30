#!/usr/bin/env python3
"""
Generate Figure 1: LLM Regime Detection System Architecture

Creates a clean, modern pipeline diagram showing the 5 stages:
1. Data Ingestion (Alpha Vantage API)
2. GEX Calculation (OI/Volume aggregation)
3. Temporal Obfuscation
4. 30-Day Window Generation
5. LLM Analysis (OpenAI o4-mini)

IEEE Publication Theme (white background).

Output: ../output/fig01_architecture.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from theme import IEEE_THEME, OUTPUT_DIR, save_figure

# Stage colors - professional palette
STAGE_COLORS = {
    "stage1": "#1565C0",  # Blue
    "stage2": "#2E7D32",  # Green
    "stage3": "#EF6C00",  # Orange
    "stage4": "#7B1FA2",  # Purple
    "stage5": "#C62828",  # Red
    "arrow": "#616161",
}


def create_figure():
    """Create architecture diagram with IEEE theme."""
    plt.style.use("default")

    # Create figure - wider aspect ratio for horizontal flow
    fig, ax = plt.subplots(figsize=(14, 6), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Stage definitions - cleaner, minimal
    stages = [
        {
            "num": "1",
            "title": "Data\nIngestion",
            "detail": "Alpha Vantage API\nSPY options 2020-2025",
            "color": STAGE_COLORS["stage1"],
            "x": 0.3,
        },
        {
            "num": "2",
            "title": "GEX\nCalculation",
            "detail": "Daily aggregation\nNet gamma ($B)",
            "color": STAGE_COLORS["stage2"],
            "x": 2.9,
        },
        {
            "num": "3",
            "title": "Temporal\nObfuscation",
            "detail": "Remove dates/tickers\nPrevent memorization",
            "color": STAGE_COLORS["stage3"],
            "x": 5.5,
        },
        {
            "num": "4",
            "title": "Window\nGeneration",
            "detail": "30-day rolling\n223+ windows/year",
            "color": STAGE_COLORS["stage4"],
            "x": 8.1,
        },
        {
            "num": "5",
            "title": "LLM\nAnalysis",
            "detail": "o4-mini batch API\nRegime classification",
            "color": STAGE_COLORS["stage5"],
            "x": 10.7,
        },
    ]

    box_width = 2.2
    box_height = 3.2
    y_center = 3.2

    # Draw stages
    for stage in stages:
        x = stage["x"]
        y = y_center - box_height / 2

        # Main box with colored top bar
        # White box
        box = FancyBboxPatch(
            (x, y),
            box_width,
            box_height,
            boxstyle="round,pad=0.08",
            facecolor=IEEE_THEME["background"],
            edgecolor=stage["color"],
            linewidth=2,
        )
        ax.add_patch(box)

        # Colored header bar - extends slightly beyond box top to cover rounding
        header_height = 0.7
        header = FancyBboxPatch(
            (x, y + box_height - header_height + 0.08),
            box_width,
            header_height,
            boxstyle="round,pad=0.08,rounding_size=0.15",
            facecolor=stage["color"],
            edgecolor=stage["color"],
            linewidth=0,
        )
        ax.add_patch(header)

        # Cover bottom corners of header
        cover = Rectangle(
            (x, y + box_height - header_height + 0.08),
            box_width,
            header_height * 0.35,
            facecolor=stage["color"],
            edgecolor="none",
        )
        ax.add_patch(cover)

        # Stage number in header
        ax.text(
            x + box_width / 2,
            y + box_height - header_height / 2 + 0.12,
            f"Stage {stage['num']}",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color="#FFFFFF",
        )

        # Title
        ax.text(
            x + box_width / 2,
            y + box_height - header_height - 0.5,
            stage["title"],
            ha="center",
            va="top",
            fontsize=13,
            fontweight="bold",
            color=IEEE_THEME["text"],
            linespacing=1.1,
        )

        # Detail
        ax.text(
            x + box_width / 2,
            y + 0.6,
            stage["detail"],
            ha="center",
            va="center",
            fontsize=10,
            color=IEEE_THEME["dim"],
            linespacing=1.2,
        )

    # Draw arrows between stages
    arrow_y = y_center
    for i in range(len(stages) - 1):
        x_start = stages[i]["x"] + box_width + 0.05
        x_end = stages[i + 1]["x"] - 0.05

        ax.annotate(
            "",
            xy=(x_end, arrow_y),
            xytext=(x_start, arrow_y),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=2,
                color=STAGE_COLORS["arrow"],
                connectionstyle="arc3,rad=0",
                mutation_scale=15,
            ),
        )

    # Output box on the right
    output_x = 13.2
    output_y = y_center - 1.2
    output_width = 0.6
    output_height = 2.4

    # Output arrow from stage 5
    ax.annotate(
        "",
        xy=(output_x - 0.05, y_center),
        xytext=(stages[-1]["x"] + box_width + 0.05, y_center),
        arrowprops=dict(
            arrowstyle="-|>",
            lw=2,
            color=STAGE_COLORS["arrow"],
            mutation_scale=15,
        ),
    )

    # Output box
    output_box = FancyBboxPatch(
        (output_x, output_y),
        output_width,
        output_height,
        boxstyle="round,pad=0.1",
        facecolor=IEEE_THEME["accent_positive"],
        edgecolor=IEEE_THEME["accent_positive"],
        linewidth=2,
    )
    ax.add_patch(output_box)

    # Output text (vertical)
    ax.text(
        output_x + output_width / 2,
        output_y + output_height / 2,
        "OUTPUT",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#FFFFFF",
        rotation=90,
    )

    # Output labels on far right
    output_labels = [
        "Regime Type",
        "Confidence %",
        "Persistence %",
        "Reasoning",
    ]
    label_y = output_y + output_height - 0.3
    for label in output_labels:
        ax.text(
            output_x + output_width + 0.15,
            label_y,
            f"• {label}",
            ha="left",
            va="center",
            fontsize=9,
            color=IEEE_THEME["text"],
        )
        label_y -= 0.55

    plt.tight_layout()
    return fig


def main():
    print("Generating Figure 1: Architecture Diagram (IEEE Theme)...")
    fig = create_figure()
    save_figure(fig, "fig01_architecture.png")
    print("Done!")


if __name__ == "__main__":
    main()
