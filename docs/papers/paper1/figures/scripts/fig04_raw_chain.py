#!/usr/bin/env python3
"""
Paper 1 Figure Generation: Raw Chain Validation (fig04)

Bar chart showing Raw Chain (92.3%) outperforms GEX-assisted baseline (61.5%)
by 30.8 percentage points.

Output: fig04_raw_chain.png

This is the "Nuclear Option" - definitive proof the LLM performs
structural analysis from first principles without pre-calculated GEX.
"""

import os

os.environ["MPLBACKEND"] = "Agg"
import matplotlib

matplotlib.use("Agg")
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Reset to default style to avoid any inherited styling
plt.style.use("default")
plt.rcdefaults()

# Paths - script is in docs/papers/paper1/figures/scripts/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
OUTPUT_DIR = Path(__file__).parent.parent  # docs/papers/paper1/figures/


def create_figure_3():
    """Create the Raw Chain bar chart."""

    # Data from validated results
    methods = ["GEX-Assisted\nBaseline", "Raw Chain\n(No GEX)"]
    detection_rates = [61.5, 92.3]  # Percentages
    counts = ["8/13", "12/13"]  # Raw counts
    colors = ["#6b7280", "#2563eb"]  # Gray for baseline, blue for raw chain

    # Create figure with explicit white background
    fig, ax = plt.subplots(figsize=(6, 5), dpi=300, facecolor="white")
    ax.set_facecolor("white")

    # Create bars - SIMPLE VERSION
    x = np.arange(len(methods))
    bars = ax.bar(x, detection_rates, width=0.6, color=colors)

    # Add value labels on bars
    for bar, rate, count in zip(bars, detection_rates, counts):
        height = bar.get_height()
        # Percentage label
        ax.annotate(
            f"{rate}%",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=16,
            fontweight="bold",
            color=bar.get_facecolor(),
        )
        # Count label - white text for visibility on colored bars
        ax.annotate(
            f"({count})",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, -20),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=11,
            fontweight="bold",
            color="white",
        )

    # Add improvement arrow back
    ax.annotate(
        "",
        xy=(1, 92.3),
        xytext=(0, 61.5),
        arrowprops=dict(arrowstyle="->", color="#059669", lw=2.5, connectionstyle="arc3,rad=0.2"),
    )
    ax.text(
        0.5,
        78,
        "+30.8 pp",
        ha="center",
        fontsize=14,
        color="#059669",
        fontweight="bold",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9, edgecolor="#059669", linewidth=1.5),
    )

    # Labels
    ax.set_ylabel("Detection Rate (%)", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=11)
    ax.set_title(
        "Raw Chain Validation: LLM Outperforms GEX-Assisted Baseline\n"
        "(Same 13 Test Dates, Identical Temporal Obfuscation)",
        fontsize=11,
        fontweight="bold",
    )

    # Axis limits
    ax.set_ylim(0, 110)
    ax.set_xlim(-0.5, 1.5)

    # Add key finding box
    textstr = "\n".join(
        [
            "Key Finding: Structural Analyst",
            "─" * 28,
            "Without ANY pre-calculated GEX,",
            "the LLM achieves HIGHER detection",
            "by performing gamma integration",
            "from strike-level OI distribution.",
            "",
            "Net GEX is lossy compression.",
        ]
    )
    props = dict(boxstyle="round", facecolor="#f0fdf4", alpha=0.95, edgecolor="#059669", linewidth=1.5)
    ax.text(
        0.98,
        0.35,
        textstr,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=props,
        family="monospace",
    )

    # Grid
    ax.grid(True, axis="y", alpha=0.3, linestyle="-", linewidth=0.5)
    ax.set_axisbelow(True)

    # Remove top/right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    png_path = OUTPUT_DIR / "fig04_raw_chain.png"
    plt.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"Saved: {png_path}")

    plt.close()

    return png_path


if __name__ == "__main__":
    print("=" * 60)
    print("Paper 1 Figure 4: Raw Chain Validation")
    print("=" * 60)

    png_path = create_figure_3()

    print("\n" + "=" * 60)
    print("Figure 4 Generation Complete")
    print("=" * 60)
    print(f"\nKey Statistics:")
    print(f"  - GEX-Assisted: 61.5% (8/13)")
    print(f"  - Raw Chain: 92.3% (12/13)")
    print(f"  - Improvement: +30.8 pp")
    print(f"\nOutput: {png_path}")
