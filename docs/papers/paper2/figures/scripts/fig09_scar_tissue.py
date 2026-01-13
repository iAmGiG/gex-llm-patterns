#!/usr/bin/env python3
"""
Generate Figure 9: Scar Tissue Mechanism Diagram

This script creates a conceptual diagram illustrating how 0DTE intraday trading
creates "scar tissue" in overnight open interest positioning.

IEEE Publication Theme (white background).

Issue #168: Add 'Scar Tissue' Mechanism Diagram
Output: docs/papers/paper2/figures/output/fig09_scar_tissue.png
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
    "accent_warning": "#E65100",
    "accent_negative": "#C62828",
}

# Diagram colors for IEEE theme
DIAGRAM_COLORS = {
    "intraday": "#1565C0",  # Blue
    "gamma": "#C62828",  # Red
    "hedging": "#757575",  # Grey
    "volatility": "#E65100",  # Orange
    "transition": "#9E9E9E",  # Light grey
    "positioning": "#1565C0",  # Blue
    "measurement": "#F5F5F5",  # Light bg
}


def create_figure():
    """Create scar tissue mechanism diagram with IEEE theme."""

    plt.style.use("default")

    # Create figure and axis
    fig, ax = plt.subplots(1, 1, figsize=(14, 9), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    title_text = "Scar Tissue Mechanism: How 0DTE Trading Creates Overnight Positioning"
    ax.text(
        5,
        9.5,
        title_text,
        fontsize=22,
        fontweight="bold",
        ha="center",
        va="top",
        family="sans-serif",
        color=IEEE_THEME["text"],
    )

    # Subtitle
    subtitle = "Bridging Intraday 0DTE Effects with End-of-Day Open Interest Measurement"
    ax.text(
        5,
        9.0,
        subtitle,
        fontsize=15,
        style="italic",
        ha="center",
        va="top",
        family="sans-serif",
        color=IEEE_THEME["dim"],
    )

    # Define positions
    y_start = 8.0
    box_width = 2.5
    box_height = 0.8

    # Box 1: 0DTE Intraday Trading
    box1_x, box1_y = 1.0, y_start
    box1 = FancyBboxPatch(
        (box1_x, box1_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["intraday"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box1)
    ax.text(
        box1_x + box_width / 2,
        box1_y + box_height / 2,
        "0DTE Intraday\nTrading\n(Expiring Today)",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["background"],
        family="sans-serif",
    )

    # Arrow 1 -> 2
    arrow1_y = box1_y - 0.5
    ax.annotate(
        "",
        xy=(box1_x + box_width / 2, arrow1_y - 0.3),
        xytext=(box1_x + box_width / 2, box1_y),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"]),
    )

    # Box 2: Gamma Explosion
    box2_x, box2_y = 1.0, arrow1_y - 0.8
    box2 = FancyBboxPatch(
        (box2_x, box2_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["gamma"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box2)
    ax.text(
        box2_x + box_width / 2,
        box2_y + box_height / 2,
        "Gamma\nExplosion\n(Near Expiry)",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["background"],
        family="sans-serif",
    )

    # Arrow 2 -> 3
    arrow2_y = box2_y - 0.5
    ax.annotate(
        "",
        xy=(box2_x + box_width / 2, arrow2_y - 0.3),
        xytext=(box2_x + box_width / 2, box2_y),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"]),
    )

    # Box 3: Dealer Hedging Pressure
    box3_x, box3_y = 1.0, arrow2_y - 0.8
    box3 = FancyBboxPatch(
        (box3_x, box3_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["hedging"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box3)
    ax.text(
        box3_x + box_width / 2,
        box3_y + box_height / 2,
        "Dealer\nHedging\nPressure",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["background"],
        family="sans-serif",
    )

    # Arrow 3 -> 4
    arrow3_y = box3_y - 0.5
    ax.annotate(
        "",
        xy=(box3_x + box_width / 2, arrow3_y - 0.3),
        xytext=(box3_x + box_width / 2, box3_y),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"]),
    )

    # Box 4: Intraday Volatility
    box4_x, box4_y = 1.0, arrow3_y - 0.8
    box4 = FancyBboxPatch(
        (box4_x, box4_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["volatility"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box4)
    ax.text(
        box4_x + box_width / 2,
        box4_y + box_height / 2,
        "Price Swings\n& Volatility",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["background"],
        family="sans-serif",
    )

    # RIGHT SIDE: MEASUREMENT FLOW
    # Box 5: Market Close
    box5_x, box5_y = 6.5, y_start
    box5 = FancyBboxPatch(
        (box5_x, box5_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["transition"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box5)
    ax.text(
        box5_x + box_width / 2,
        box5_y + box_height / 2,
        "Market\nClose",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["text"],
        family="sans-serif",
    )

    # Cross arrow 4 -> 5
    ax.annotate(
        "",
        xy=(box5_x, box4_y + box_height / 2),
        xytext=(box1_x + box_width, box4_y + box_height / 2),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"], linestyle="dashed"),
    )

    # Box 6: Incomplete Unwinding
    box6_x, box6_y = 6.5, y_start - 1.3
    box6 = FancyBboxPatch(
        (box6_x, box6_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["positioning"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box6)
    ax.text(
        box6_x + box_width / 2,
        box6_y + box_height / 2,
        "Incomplete\nUnwinding\n(Liquidity, Risk)",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["background"],
        family="sans-serif",
    )

    # Arrow 5 -> 6
    arrow6_y = box5_y - 0.5
    ax.annotate(
        "",
        xy=(box6_x + box_width / 2, box6_y + box_height),
        xytext=(box5_x + box_width / 2, arrow6_y - 0.3),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"]),
    )

    # Box 7: Residual Positioning
    box7_x, box7_y = 6.5, y_start - 2.6
    box7 = FancyBboxPatch(
        (box7_x, box7_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["positioning"],
        edgecolor=IEEE_THEME["background"],
        linewidth=2,
        alpha=0.9,
    )
    ax.add_patch(box7)
    ax.text(
        box7_x + box_width / 2,
        box7_y + box_height / 2,
        "Residual\nDealer\nPositioning",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["background"],
        family="sans-serif",
    )

    # Arrow 6 -> 7
    arrow7_y = box6_y - 0.5
    ax.annotate(
        "",
        xy=(box7_x + box_width / 2, box7_y + box_height),
        xytext=(box6_x + box_width / 2, arrow7_y - 0.3),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"]),
    )

    # Box 8: EOD OI
    box8_x, box8_y = 6.5, y_start - 3.9
    box8 = FancyBboxPatch(
        (box8_x, box8_y),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=DIAGRAM_COLORS["measurement"],
        edgecolor=IEEE_THEME["accent_negative"],
        linewidth=2.5,
        alpha=0.95,
    )
    ax.add_patch(box8)
    ax.text(
        box8_x + box_width / 2,
        box8_y + box_height / 2,
        "EOD Open\nInterest\n(Observable)",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=IEEE_THEME["text"],
        family="sans-serif",
    )

    # Arrow 7 -> 8
    arrow8_y = box7_y - 0.5
    ax.annotate(
        "",
        xy=(box8_x + box_width / 2, box8_y + box_height),
        xytext=(box7_x + box_width / 2, arrow8_y - 0.3),
        arrowprops=dict(arrowstyle="->", lw=2.5, color=IEEE_THEME["dim"]),
    )

    # "Scar Tissue" annotation box
    scar_box_x, scar_box_y = 3.5, 0.3
    scar_width, scar_height = 3, 0.9
    scar_box = FancyBboxPatch(
        (scar_box_x, scar_box_y),
        scar_width,
        scar_height,
        boxstyle="round,pad=0.1",
        facecolor=IEEE_THEME["panel_bg"],
        edgecolor=IEEE_THEME["accent_warning"],
        linewidth=2.5,
        linestyle="--",
    )
    ax.add_patch(scar_box)
    ax.text(
        scar_box_x + scar_width / 2,
        scar_box_y + scar_height / 2,
        '"Scar Tissue": Cumulative effect of daily intraday 0DTE hedging\nforcing persistent overnight dealer positioning',
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color=IEEE_THEME["text"],
        family="sans-serif",
    )

    # Side annotations
    ax.text(
        0.3,
        6.2,
        "INTRADAY\nMECHANISM",
        fontsize=15,
        fontweight="bold",
        ha="center",
        va="center",
        color=DIAGRAM_COLORS["intraday"],
        rotation=90,
        family="sans-serif",
    )

    ax.text(
        9.2,
        6.0,
        "MEASUREMENT\nLAYER",
        fontsize=15,
        fontweight="bold",
        ha="center",
        va="center",
        color=IEEE_THEME["dim"],
        rotation=90,
        family="sans-serif",
    )

    # Footer
    footer_text = (
        "How it works: High-frequency intraday 0DTE trading creates gamma exposure that dealers must hedge aggressively.\n"
        "When positions cannot be fully unwound by market close due to liquidity constraints, this creates residual positioning.\n"
        "Our EOD GEX measurement captures the cumulative effect of this daily hedging - the 'scar tissue' left behind."
    )
    ax.text(
        5,
        -0.8,
        footer_text,
        fontsize=15,
        ha="center",
        va="top",
        family="sans-serif",
        color=IEEE_THEME["dim"],
        wrap=True,
        style="italic",
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
