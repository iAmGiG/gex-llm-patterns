#!/usr/bin/env python3
"""
Generate Figure 3: Temporal Obfuscation Process

Creates a before/after diagram showing how calendar dates, ticker symbols,
and temporal context are removed while preserving GEX magnitude and
structural relationships.

IEEE Publication Theme (white background).

Output: docs/papers/paper2/figures/output/fig03_obfuscation.png
"""

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from theme import OUTPUT_DIR, save_figure

# IEEE Publication Theme
IEEE_THEME = {
    "background": "#FFFFFF",
    "text": "#000000",
    "dim": "#444444",
    "panel_bg": "#F5F5F5",
    "accent_warning": "#E65100",  # Deep Orange
}

# Obfuscation colors for IEEE theme
OBFUSCATION_COLORS = {
    "before": "#1565C0",  # Blue
    "after": "#2E7D32",  # Green
    "redact": "#C62828",  # Red
    "preserve": "#2E7D32",  # Green
}


def create_figure():
    """Create obfuscation diagram with IEEE theme."""

    plt.style.use("default")

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(
        6,
        9.6,
        "Temporal Obfuscation Process",
        fontsize=22,
        fontweight="bold",
        ha="center",
        va="top",
        color=IEEE_THEME["text"],
    )
    ax.text(
        6,
        9.0,
        "Preventing LLM Memorization While Preserving Structural Information",
        fontsize=14,
        ha="center",
        va="top",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # ============================================================================
    # LEFT SIDE: BEFORE (Original Data)
    # ============================================================================

    before_x = 0.5
    before_y = 7.5

    # Before header
    ax.text(
        before_x + 2,
        before_y + 0.3,
        "BEFORE",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=OBFUSCATION_COLORS["before"],
    )
    ax.text(
        before_x + 2,
        before_y - 0.1,
        "Original Data",
        fontsize=13,
        ha="center",
        va="top",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # Before data box
    before_box = FancyBboxPatch(
        (before_x, before_y - 3.5),
        4,
        3.2,
        boxstyle="round,pad=0.1",
        facecolor=IEEE_THEME["panel_bg"],
        edgecolor=OBFUSCATION_COLORS["before"],
        linewidth=2.5,
        alpha=0.95,
    )
    ax.add_patch(before_box)

    # Original data content
    original_data = [
        ("Date:", "2024-03-15", True),
        ("Ticker:", "SPY", True),
        ("Day Type:", "Friday", True),
        ("GEX:", "-$12.3B", False),
        ("Persistence:", "93%", False),
        ("Sign Flips:", "2", False),
    ]

    data_y = before_y - 0.7
    for label, value, is_redacted in original_data:
        ax.text(
            before_x + 0.3, data_y, label, fontsize=13, ha="left", va="top", color=IEEE_THEME["dim"], family="monospace"
        )
        color = OBFUSCATION_COLORS["redact"] if is_redacted else OBFUSCATION_COLORS["preserve"]
        ax.text(
            before_x + 1.8,
            data_y,
            value,
            fontsize=13,
            ha="left",
            va="top",
            fontweight="bold",
            color=color,
            family="monospace",
        )
        data_y -= 0.5

    # ============================================================================
    # CENTER: TRANSFORMATION ARROW
    # ============================================================================

    # Main arrow
    ax.annotate(
        "",
        xy=(7.5, 5.5),
        xytext=(4.8, 5.5),
        arrowprops=dict(arrowstyle="->", lw=4, color=IEEE_THEME["accent_warning"], connectionstyle="arc3,rad=0"),
    )

    # Transformation label
    ax.text(
        6.15,
        6.3,
        "OBFUSCATION",
        fontsize=15,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=IEEE_THEME["accent_warning"],
    )

    # What happens
    transform_text = (
        "• Remove calendar dates\n"
        "• Strip ticker symbols\n"
        "• Remove day-of-week\n"
        "• Preserve magnitudes\n"
        "• Keep structure intact"
    )
    ax.text(
        6.15,
        4.6,
        transform_text,
        fontsize=12,
        ha="center",
        va="top",
        color=IEEE_THEME["text"],
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["accent_warning"],
            linewidth=1.5,
            alpha=0.9,
        ),
    )

    # ============================================================================
    # RIGHT SIDE: AFTER (Obfuscated Data)
    # ============================================================================

    after_x = 7.5
    after_y = 7.5

    # After header
    ax.text(
        after_x + 2,
        after_y + 0.3,
        "AFTER",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=OBFUSCATION_COLORS["after"],
    )
    ax.text(
        after_x + 2,
        after_y - 0.1,
        "Obfuscated Data",
        fontsize=13,
        ha="center",
        va="top",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # After data box
    after_box = FancyBboxPatch(
        (after_x, after_y - 3.5),
        4,
        3.2,
        boxstyle="round,pad=0.1",
        facecolor=IEEE_THEME["panel_bg"],
        edgecolor=OBFUSCATION_COLORS["after"],
        linewidth=2.5,
        alpha=0.95,
    )
    ax.add_patch(after_box)

    # Obfuscated data content
    obfuscated_data = [
        ("Date:", "Day 15", False),
        ("Ticker:", "[REDACTED]", True),
        ("Day Type:", "[REMOVED]", True),
        ("GEX:", "-$12.3B", False),
        ("Persistence:", "93%", False),
        ("Sign Flips:", "2", False),
    ]

    data_y = after_y - 0.7
    for label, value, is_placeholder in obfuscated_data:
        ax.text(
            after_x + 0.3, data_y, label, fontsize=13, ha="left", va="top", color=IEEE_THEME["dim"], family="monospace"
        )
        if is_placeholder:
            color = IEEE_THEME["dim"]
            style = "italic"
        else:
            color = OBFUSCATION_COLORS["preserve"]
            style = "normal"
        ax.text(
            after_x + 1.8,
            data_y,
            value,
            fontsize=13,
            ha="left",
            va="top",
            fontweight="bold",
            color=color,
            family="monospace",
            style=style,
        )
        data_y -= 0.5

    # ============================================================================
    # BOTTOM: LEGEND AND EXPLANATION
    # ============================================================================

    # Legend
    legend_y = 2.8

    # Redacted legend
    ax.add_patch(
        FancyBboxPatch(
            (1, legend_y - 0.3), 0.4, 0.4, boxstyle="round,pad=0.05", facecolor=OBFUSCATION_COLORS["redact"], alpha=0.8
        )
    )
    ax.text(
        1.6,
        legend_y - 0.1,
        "REMOVED: Temporal identifiers that could enable memorization",
        fontsize=12,
        ha="left",
        va="center",
        color=IEEE_THEME["text"],
    )

    # Preserved legend
    ax.add_patch(
        FancyBboxPatch(
            (1, legend_y - 0.9),
            0.4,
            0.4,
            boxstyle="round,pad=0.05",
            facecolor=OBFUSCATION_COLORS["preserve"],
            alpha=0.8,
        )
    )
    ax.text(
        1.6,
        legend_y - 0.7,
        "PRESERVED: Structural metrics required for regime detection",
        fontsize=12,
        ha="left",
        va="center",
        color=IEEE_THEME["text"],
    )

    # Explanation box at bottom
    explanation = (
        "Why Obfuscation Matters: LLMs trained on financial data could memorize that "
        '"March 2024 had negative gamma" without understanding the mechanics. '
        "By removing temporal anchors, we force the model to reason from structural "
        "patterns (persistence, magnitude, sign flips) rather than recalling specific dates."
    )
    ax.text(
        6,
        0.8,
        explanation,
        ha="center",
        va="center",
        fontsize=11,
        color=IEEE_THEME["dim"],
        style="italic",
        wrap=True,
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["dim"],
            linewidth=1,
            alpha=0.8,
        ),
    )

    plt.tight_layout()

    return fig


def main():
    print("Generating Obfuscation Figure (IEEE Theme)...")
    fig = create_figure()
    save_figure(fig, "fig03_obfuscation.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
