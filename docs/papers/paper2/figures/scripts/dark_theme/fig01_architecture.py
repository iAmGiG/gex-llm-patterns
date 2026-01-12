#!/usr/bin/env python3
"""
Generate Figure 1: LLM Regime Detection System Architecture

Creates a pipeline diagram showing the 5 stages:
1. Data Ingestion (Alpha Vantage API)
2. GEX Calculation (OI/Volume aggregation)
3. Temporal Obfuscation
4. 30-Day Window Generation
5. LLM Analysis (OpenAI o4-mini)

Output: ../output/fig01_architecture.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from theme import DARK_THEME, OUTPUT_DIR, STAGE_COLORS, apply_dark_theme, reset_theme, save_figure


def create_figure():
    """Create architecture diagram with dark theme."""
    apply_dark_theme()

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor(DARK_THEME["background"])
    ax.set_facecolor(DARK_THEME["background"])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Title
    ax.text(
        8,
        8.6,
        "LLM Regime Detection System Architecture",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="top",
        color=DARK_THEME["text"],
    )
    ax.text(
        8,
        8.1,
        "Five-Stage Pipeline: From Raw Options Data to Regime Classification",
        fontsize=11,
        ha="center",
        va="top",
        color=DARK_THEME["dim"],
        style="italic",
    )

    # Stage definitions
    stages = [
        {
            "num": "1",
            "title": "Data Ingestion",
            "subtitle": "Alpha Vantage API",
            "color": STAGE_COLORS["stage1"],
            "x": 0.5,
            "details": ["SPY options chains", "OI + Volume data", "2020-2025 historical"],
        },
        {
            "num": "2",
            "title": "GEX Calculation",
            "subtitle": "Gamma Exposure",
            "color": STAGE_COLORS["stage2"],
            "x": 3.5,
            "details": ["Call/Put aggregation", "Strike-level gamma", "Daily net GEX ($B)"],
        },
        {
            "num": "3",
            "title": "Temporal Obfuscation",
            "subtitle": "Anti-Memorization",
            "color": STAGE_COLORS["stage3"],
            "x": 6.5,
            "details": ["Remove dates/tickers", "Preserve structure", "Sequential Day N"],
        },
        {
            "num": "4",
            "title": "Window Generation",
            "subtitle": "30-Day Rolling",
            "color": STAGE_COLORS["stage4"],
            "x": 9.5,
            "details": ["30-day windows", "Weekly sliding", "223+ windows/year"],
        },
        {
            "num": "5",
            "title": "LLM Analysis",
            "subtitle": "OpenAI o4-mini",
            "color": STAGE_COLORS["stage5"],
            "x": 12.5,
            "details": ["Batch API (50% cost)", "Chain-of-thought", "Regime classification"],
        },
    ]

    box_width = 2.5
    box_height = 4.0
    y_center = 4.5

    # Draw stages
    for stage in stages:
        x = stage["x"]
        y = y_center - box_height / 2

        # Main box with rounded corners
        box = FancyBboxPatch(
            (x, y),
            box_width,
            box_height,
            boxstyle="round,pad=0.15",
            facecolor=DARK_THEME["panel_bg"],
            edgecolor=stage["color"],
            linewidth=2.5,
            alpha=0.95,
        )
        ax.add_patch(box)

        # Stage number circle
        circle = plt.Circle(
            (x + 0.4, y + box_height - 0.4),
            0.25,
            facecolor=stage["color"],
            edgecolor=DARK_THEME["background"],
            linewidth=2,
            zorder=5,
        )
        ax.add_patch(circle)
        ax.text(
            x + 0.4,
            y + box_height - 0.4,
            stage["num"],
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color=DARK_THEME["background"],
            zorder=6,
        )

        # Title
        ax.text(
            x + box_width / 2,
            y + box_height - 0.8,
            stage["title"],
            ha="center",
            va="top",
            fontsize=12,
            fontweight="bold",
            color=DARK_THEME["text"],
        )

        # Subtitle
        ax.text(
            x + box_width / 2,
            y + box_height - 1.2,
            stage["subtitle"],
            ha="center",
            va="top",
            fontsize=9,
            color=stage["color"],
            style="italic",
        )

        # Details list
        detail_y = y + box_height - 1.8
        for detail in stage["details"]:
            ax.text(x + 0.3, detail_y, f"• {detail}", ha="left", va="top", fontsize=9, color=DARK_THEME["text"])
            detail_y -= 0.5

    # Draw arrows between stages
    arrow_y = y_center
    for i in range(len(stages) - 1):
        x_start = stages[i]["x"] + box_width
        x_end = stages[i + 1]["x"]

        ax.annotate(
            "",
            xy=(x_end - 0.1, arrow_y),
            xytext=(x_start + 0.1, arrow_y),
            arrowprops=dict(arrowstyle="->", lw=2.5, color=STAGE_COLORS["arrow"], connectionstyle="arc3,rad=0"),
        )

    # Data flow examples (bottom)
    flow_y = 1.2
    flow_box_width = 2.3

    examples = [
        {"x": 0.6, "text": "Raw Chain:\n2024-03-15\nSPY 510C\nOI: 45,231"},
        {"x": 3.6, "text": "Daily GEX:\nDay: 2024-03-15\nGEX: -$12.3B\nNet Gamma: -0.8"},
        {"x": 6.6, "text": "Obfuscated:\nDay 15\nGEX: -$12.3B\n(No dates/tickers)"},
        {"x": 9.6, "text": "30-Day Window:\nDay 1: -$8.2B\n...\nDay 30: -$15.1B"},
        {"x": 12.6, "text": "Classification:\nPERSISTENT_NEG\nConf: 94%\nFlips: 2"},
    ]

    for ex in examples:
        data_box = FancyBboxPatch(
            (ex["x"], flow_y - 0.9),
            flow_box_width,
            1.5,
            boxstyle="round,pad=0.1",
            facecolor=STAGE_COLORS["data_flow"],
            edgecolor=DARK_THEME["dim"],
            linewidth=1,
            alpha=0.8,
        )
        ax.add_patch(data_box)
        ax.text(
            ex["x"] + flow_box_width / 2,
            flow_y - 0.15,
            ex["text"],
            ha="center",
            va="center",
            fontsize=7,
            color=DARK_THEME["text"],
            family="monospace",
        )

    ax.text(
        0.3,
        flow_y - 0.15,
        "Data\nFlow:",
        ha="right",
        va="center",
        fontsize=8,
        fontweight="bold",
        color=DARK_THEME["dim"],
    )

    # Output summary (right side)
    output_text = (
        "Output:\n" "• Regime Type\n" "• Confidence %\n" "• Persistence %\n" "• Sign Flips\n" "• Chain-of-Thought"
    )
    ax.text(
        15.5,
        4.5,
        output_text,
        ha="left",
        va="center",
        fontsize=9,
        color=DARK_THEME["text"],
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=DARK_THEME["panel_bg"],
            edgecolor=DARK_THEME["accent_positive"],
            linewidth=2,
            alpha=0.9,
        ),
    )

    plt.tight_layout()
    return fig


def main():
    print("Generating Figure 1: Architecture Diagram...")
    fig = create_figure()
    save_figure(fig, "fig01_architecture.png")
    print("Done!")


if __name__ == "__main__":
    main()
