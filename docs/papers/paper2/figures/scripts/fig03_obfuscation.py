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
from theme import IEEE_THEME, OUTPUT_DIR, save_figure

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

    # Create figure - slightly taller to fit legend
    fig, ax = plt.subplots(figsize=(10, 7.0), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.3, 6.7)
    ax.axis("off")

    # Title - nudged upward (with BEFORE/AFTER callouts bumped to fontsize 17,
    # the previous layout clipped this subtitle horizontally against the
    # callout labels; +0.5 units of vertical breathing room fixes it).
    ax.text(
        5,
        6.4,
        "Temporal Obfuscation Process",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="top",
        color=IEEE_THEME["text"],
    )
    ax.text(
        5,
        5.95,
        "Preventing LLM Memorization While Preserving Structural Information",
        fontsize=12,
        ha="center",
        va="top",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # ============================================================================
    # LEFT SIDE: BEFORE (Original Data)
    # ============================================================================

    before_x = 0.3
    before_y = 4.5

    # Before header - positioned above the box
    ax.text(
        before_x + 1.6,
        before_y + 0.65,
        "BEFORE",
        fontsize=17,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=OBFUSCATION_COLORS["before"],
    )
    ax.text(
        before_x + 1.6,
        before_y + 0.35,
        "Original Data",
        fontsize=13,
        ha="center",
        va="bottom",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # Before data box - compact
    before_box = FancyBboxPatch(
        (before_x, before_y - 2.8),
        3.2,
        2.6,
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

    data_y = before_y - 0.5
    for label, value, is_redacted in original_data:
        ax.text(
            before_x + 0.2, data_y, label, fontsize=12, ha="left", va="top", color=IEEE_THEME["dim"], family="monospace"
        )
        color = OBFUSCATION_COLORS["redact"] if is_redacted else OBFUSCATION_COLORS["preserve"]
        ax.text(
            before_x + 1.5,
            data_y,
            value,
            fontsize=12,
            ha="left",
            va="top",
            fontweight="bold",
            color=color,
            family="monospace",
        )
        data_y -= 0.40

    # ============================================================================
    # CENTER: TRANSFORMATION ARROW
    # ============================================================================

    # Main arrow - repositioned for compact layout
    ax.annotate(
        "",
        xy=(6.3, 3.0),
        xytext=(3.7, 3.0),
        arrowprops=dict(arrowstyle="->", lw=3, color=IEEE_THEME["accent_warning"], connectionstyle="arc3,rad=0"),
    )

    # Transformation label
    ax.text(
        5.0,
        3.7,
        "OBFUSCATION",
        fontsize=12,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=IEEE_THEME["accent_warning"],
    )

    # What happens - compact bullet list
    transform_text = (
        "• Remove calendar dates\n"
        "• Strip ticker symbols\n"
        "• Remove day-of-week\n"
        "• Preserve magnitudes\n"
        "• Keep structure intact"
    )
    ax.text(
        5.0,
        2.3,
        transform_text,
        fontsize=12,
        ha="center",
        va="top",
        color=IEEE_THEME["text"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["accent_warning"],
            linewidth=1.5,
            alpha=0.9,
        ),
    )

    # ============================================================================
    # RIGHT SIDE: AFTER (Obfuscated Data)
    # ============================================================================

    after_x = 6.5
    after_y = 4.5

    # After header - positioned above the box
    ax.text(
        after_x + 1.6,
        after_y + 0.65,
        "AFTER",
        fontsize=17,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=OBFUSCATION_COLORS["after"],
    )
    ax.text(
        after_x + 1.6,
        after_y + 0.35,
        "Obfuscated Data",
        fontsize=13,
        ha="center",
        va="bottom",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # After data box - compact
    after_box = FancyBboxPatch(
        (after_x, after_y - 2.8),
        3.2,
        2.6,
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

    data_y = after_y - 0.5
    for label, value, is_placeholder in obfuscated_data:
        ax.text(
            after_x + 0.2, data_y, label, fontsize=12, ha="left", va="top", color=IEEE_THEME["dim"], family="monospace"
        )
        if is_placeholder:
            color = IEEE_THEME["dim"]
            style = "italic"
        else:
            color = OBFUSCATION_COLORS["preserve"]
            style = "normal"
        ax.text(
            after_x + 1.5,
            data_y,
            value,
            fontsize=12,
            ha="left",
            va="top",
            fontweight="bold",
            color=color,
            family="monospace",
            style=style,
        )
        data_y -= 0.40

    # ============================================================================
    # BOTTOM: LEGEND (explanation moved to caption)
    # ============================================================================

    # Legend - compact horizontal layout
    legend_y = 0.5

    # Redacted legend
    ax.add_patch(
        FancyBboxPatch(
            (1.0, legend_y - 0.15),
            0.3,
            0.3,
            boxstyle="round,pad=0.05",
            facecolor=OBFUSCATION_COLORS["redact"],
            alpha=0.8,
        )
    )
    ax.text(
        1.45,
        legend_y,
        "REMOVED: Temporal identifiers that could enable memorization",
        fontsize=12,
        ha="left",
        va="center",
        color=IEEE_THEME["text"],
    )

    # Preserved legend
    ax.add_patch(
        FancyBboxPatch(
            (1.0, legend_y - 0.55),
            0.3,
            0.3,
            boxstyle="round,pad=0.05",
            facecolor=OBFUSCATION_COLORS["preserve"],
            alpha=0.8,
        )
    )
    ax.text(
        1.45,
        legend_y - 0.4,
        "PRESERVED: Structural metrics required for regime detection",
        fontsize=12,
        ha="left",
        va="center",
        color=IEEE_THEME["text"],
    )

    # Note: Detailed explanation moved to LaTeX caption for space efficiency

    plt.tight_layout()

    return fig


def main():
    print("Generating Obfuscation Figure (IEEE Theme)...")
    fig = create_figure()
    save_figure(fig, "fig03_obfuscation.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
