#!/usr/bin/env python3
"""
Generate Figure 1: Obfuscation Example (REBUILT FROM SCRATCH)

Shows before/after comparison of data obfuscation.
Demonstrates how temporal context is stripped to prevent training data memorization.

Before: Real dates, tickers, context
After: Day T+N format, INDEX_1, no context
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# IEEE two-column format
plt.rcParams.update(
    {
        "font.size": 9,
        "axes.labelsize": 10,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
    }
)

OUTPUT_DIR = Path(__file__).parent


def create_figure():
    """Create before/after obfuscation comparison - rebuilt from scratch."""

    fig = plt.figure(figsize=(12, 6), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Colors
    color_before = "#FFE6E6"  # Light red
    color_after = "#E6FFE6"  # Light green

    # BEFORE panel (left side)
    # Main box
    before_box = FancyBboxPatch(
        (0.5, 2.5),
        4.5,
        4,
        boxstyle="round,pad=0.1",
        edgecolor="darkred",
        facecolor=color_before,
        linewidth=2.5,
        zorder=1,
    )
    ax.add_patch(before_box)

    # Title
    ax.text(
        2.75,
        7.3,
        "BEFORE Obfuscation",
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="darkred",
        zorder=10,
    )

    # Content
    before_lines = [
        "Date: 2024-01-16",
        "Ticker: SPY",
        "Spot: $476.32",
        "",
        "Net GEX: -$32.9B",
        "Call Gamma: -$17.3B",
        "Put Gamma: -$15.6B",
        "Flip: $475.20",
        "",
        "Context:",
        '"Fed meeting tomorrow"',
        '"VIX at 14.2"',
        '"Earnings starting"',
    ]

    content_y = 6.2
    for line in before_lines:
        ax.text(2.75, content_y, line, ha="center", va="top", fontsize=8, family="monospace", zorder=2)
        content_y -= 0.28

    # Bottom annotation
    ax.text(
        2.75,
        1.8,
        "Contains Temporal Context",
        ha="center",
        va="top",
        fontsize=9,
        style="italic",
        color="darkred",
        fontweight="bold",
        zorder=10,
    )
    ax.text(
        2.75,
        1.3,
        "(Enables training data memorization)",
        ha="center",
        va="top",
        fontsize=8,
        style="italic",
        color="darkred",
        zorder=10,
    )

    # AFTER panel (right side)
    # Main box
    after_box = FancyBboxPatch(
        (7, 2.5),
        4.5,
        4,
        boxstyle="round,pad=0.1",
        edgecolor="darkgreen",
        facecolor=color_after,
        linewidth=2.5,
        zorder=1,
    )
    ax.add_patch(after_box)

    # Title
    ax.text(
        9.25,
        7.3,
        "AFTER Obfuscation",
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        color="darkgreen",
        zorder=10,
    )

    # Content
    after_lines = [
        "Day: T+0",
        "Asset: INDEX_1",
        "Spot: $476.32",
        "",
        "Net GEX: -$32.9B",
        "Call Gamma: -$17.3B",
        "Put Gamma: -$15.6B",
        "Flip: $475.20",
        "",
        "Context: [REMOVED]",
        "",
        "",
        "",
    ]

    content_y = 6.2
    for line in after_lines:
        ax.text(9.25, content_y, line, ha="center", va="top", fontsize=8, family="monospace", zorder=2)
        content_y -= 0.28

    # Bottom annotation
    ax.text(
        9.25,
        1.8,
        "Temporal Context Removed",
        ha="center",
        va="top",
        fontsize=9,
        style="italic",
        color="darkgreen",
        fontweight="bold",
        zorder=10,
    )
    ax.text(
        9.25,
        1.3,
        "(Forces reasoning from structure)",
        ha="center",
        va="top",
        fontsize=8,
        style="italic",
        color="darkgreen",
        zorder=10,
    )

    # Arrow connecting panels (behind boxes)
    arrow = FancyArrowPatch(
        (5.2, 4.5), (6.8, 4.5), arrowstyle="->", mutation_scale=25, linewidth=3, color="#333333", zorder=0
    )
    ax.add_patch(arrow)

    # Legend boxes at bottom
    ax.text(
        6,
        0.7,
        "PRESERVED: GEX values, spot prices (quantitative structure)",
        ha="center",
        va="center",
        fontsize=8.5,
        style="italic",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightblue", edgecolor="blue", linewidth=1.5, alpha=0.8),
    )

    ax.text(
        6,
        0.15,
        "REMOVED: Dates, tickers, event context (temporal/narrative info)",
        ha="center",
        va="center",
        fontsize=8.5,
        style="italic",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightcoral", edgecolor="red", linewidth=1.5, alpha=0.8),
    )

    # Main title
    fig.text(
        0.515,
        0.85,
        "Obfuscation Testing: Preventing Training Data Memorization",
        ha="center",
        fontsize=13,
        fontweight="bold",
    )

    return fig


def main():
    """Generate Figure 1."""
    print("=" * 60)
    print("GENERATING FIGURE 1: OBFUSCATION METHODOLOGY")
    print("=" * 60)

    fig = create_figure()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "../fig01_obfuscation_example.png"
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✅ Saved: {output_file}")

    plt.close()

    print("✅ Figure 1 complete!")
    print("Shows before/after obfuscation - key methodological contribution")
    print("=" * 60)


if __name__ == "__main__":
    main()
