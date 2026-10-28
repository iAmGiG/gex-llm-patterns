#!/usr/bin/env python3
"""
Generate Figure 9: Scar Tissue Mechanism Diagram (Combined View)

This script creates a two-panel figure showing:
- Panel A (top): Time-series gamma decay curve showing intraday dynamics
- Panel B (bottom): "Phase Change" Before/After schematic at 4:00 PM

Together they tell the complete story of how 0DTE expiration creates
residual overnight positioning ("scar tissue").

IEEE Publication Theme (white background).

Issue #168: Add 'Scar Tissue' Mechanism Diagram
Output: docs/papers/paper2/figures/output/fig09_scar_tissue.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from theme import IEEE_THEME, OUTPUT_DIR, save_figure

# Diagram colors
COLORS = {
    "gamma": "#C62828",  # Red for gamma exposure (0DTE options)
    "hedge": "#1565C0",  # Blue for hedge position (stock)
    "scar_tissue": "#1565C0",  # Blue for scar tissue (matches hedge)
    "expired": "#BDBDBD",  # Grey for expired/vanished
    "time_marker": "#2E7D32",  # Green for 4:00 PM marker
    "background_panel": "#F5F5F5",  # Light grey panel background
    "arrow": "#424242",  # Dark grey for arrows
    "fill_intraday": "#FFCDD2",  # Light red fill
    "fill_scar_tissue": "#BBDEFB",  # Light blue fill (matches hedge)
}


def gamma_curve(t):
    """Generate gamma exposure curve with incomplete unwind."""
    result = np.zeros_like(t)

    for i, ti in enumerate(t):
        if ti <= 0.25:
            # Morning buildup - exponential rise
            result[i] = 15 * (1 - np.exp(-8 * ti))
        elif ti <= 0.65:
            # Peak period - sustained high with slight increase
            result[i] = 15 + 8 * np.sin(np.pi * (ti - 0.25) / 0.8)
        elif ti <= 1.0:
            # Partial unwind - decay but NOT to zero
            peak_val = 15 + 8 * np.sin(np.pi * 0.4 / 0.8)  # Value at ti=0.65
            decay_factor = np.exp(-3.5 * (ti - 0.65))
            # Floor at residual level (scar tissue)
            residual = 6.0
            result[i] = residual + (peak_val - residual) * decay_factor
        else:
            # After close - flat residual (scar tissue)
            result[i] = 6.0

    return result


def create_figure():
    """Create combined scar tissue mechanism diagram."""

    plt.style.use("default")

    # Create figure with two panels
    fig = plt.figure(figsize=(12, 10), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])

    # Create grid: Panel A (curve) on top, Panel B (schematic) on bottom
    gs = GridSpec(2, 1, height_ratios=[1, 1.1], hspace=0.28)

    ax_curve = fig.add_subplot(gs[0])
    ax_schematic = fig.add_subplot(gs[1])

    ax_curve.set_facecolor(IEEE_THEME["background"])
    ax_schematic.set_facecolor(IEEE_THEME["background"])

    # Main title
    fig.suptitle('The "Scar Tissue" Mechanism', fontsize=18, fontweight="bold", color=IEEE_THEME["text"], y=0.97)

    # ========================================================================
    # PANEL A: INTRADAY GAMMA DYNAMICS (Time-Series Curve)
    # ========================================================================

    # Time axis: 0 = market open, 1 = market close, 1.2 = after hours
    t = np.linspace(0, 1.2, 500)
    gamma = gamma_curve(t)

    # Plot the gamma curve
    ax_curve.plot(t, gamma, color=COLORS["gamma"], linewidth=3, label="Dealer Gamma Exposure", zorder=5)

    # Fill area under curve during trading hours
    trading_mask = t <= 1.0
    ax_curve.fill_between(t[trading_mask], 0, gamma[trading_mask], color=COLORS["fill_intraday"], alpha=0.4, zorder=2)

    # Highlight residual area (scar tissue)
    residual_mask = t >= 1.0
    ax_curve.fill_between(
        t[residual_mask],
        0,
        gamma[residual_mask],
        color=COLORS["fill_scar_tissue"],
        alpha=0.6,
        zorder=3,
        label='"Scar Tissue" Residual',
    )

    # Scar tissue level line
    ax_curve.axhline(y=6.0, color=COLORS["scar_tissue"], linestyle="--", linewidth=1.5, alpha=0.7, zorder=4)
    ax_curve.fill_between([0.85, 1.2], 0, 6.0, color=COLORS["fill_scar_tissue"], alpha=0.3, zorder=1)

    # Zero reference line
    ax_curve.axhline(y=0, color=IEEE_THEME["dim"], linewidth=1, zorder=1)

    # Market close vertical line
    ax_curve.axvline(
        x=1.0, color=COLORS["time_marker"], linewidth=2.5, linestyle="-", label="Market Close (4:00 PM)", zorder=4
    )

    # Annotations
    peak_idx = np.argmax(gamma)
    ax_curve.annotate(
        "Peak Gamma\n~$23B",
        xy=(t[peak_idx], gamma[peak_idx]),
        xytext=(0.72, 26),
        fontsize=10,
        fontweight="bold",
        color=COLORS["gamma"],
        ha="center",
        arrowprops=dict(arrowstyle="->", color=COLORS["gamma"], lw=1.5, connectionstyle="arc3,rad=0.2"),
    )

    ax_curve.annotate(
        "Incomplete\nUnwind",
        xy=(0.82, gamma_curve(np.array([0.82]))[0]),
        xytext=(0.58, 5),
        fontsize=10,
        fontweight="bold",
        color=COLORS["hedge"],
        ha="center",
        arrowprops=dict(arrowstyle="->", color=COLORS["hedge"], lw=1.5, connectionstyle="arc3,rad=-0.2"),
    )

    # Residual annotation
    ax_curve.text(
        1.12,
        10,
        '"Scar Tissue"\nResidual\n~$6B',
        fontsize=9,
        fontweight="bold",
        color=COLORS["scar_tissue"],
        ha="center",
        va="center",
        bbox=dict(
            boxstyle="round,pad=0.3", facecolor="white", edgecolor=COLORS["scar_tissue"], linewidth=1.5, alpha=0.95
        ),
    )
    ax_curve.annotate(
        "",
        xy=(1.08, 6.0),
        xytext=(1.10, 8.5),
        arrowprops=dict(arrowstyle="->", color=COLORS["scar_tissue"], lw=1.5),
    )

    # X-axis labels
    ax_curve.set_xlim(-0.02, 1.22)
    ax_curve.set_xticks([0, 0.25, 0.5, 0.75, 1.0, 1.1])
    ax_curve.set_xticklabels(["9:30\nOpen", "11:00", "12:30", "2:00", "4:00\nClose", "After\nHours"], fontsize=10)

    # Y-axis
    ax_curve.set_ylim(-1, 28)
    ax_curve.set_ylabel("Gamma Exposure ($B)", fontsize=12, fontweight="bold", color=IEEE_THEME["text"])
    ax_curve.set_xlabel("Trading Day Timeline", fontsize=12, fontweight="bold", color=IEEE_THEME["text"])

    # Panel A title
    ax_curve.set_title(
        "(A) Intraday Gamma Dynamics: Why Residual Positioning Accumulates",
        fontsize=13,
        fontweight="bold",
        color=IEEE_THEME["text"],
        pad=10,
    )

    # Legend
    ax_curve.legend(loc="upper left", fontsize=10, framealpha=0.95, facecolor="white", edgecolor=IEEE_THEME["dim"])

    # Grid and spines
    ax_curve.grid(True, alpha=0.3, linestyle="-", color=IEEE_THEME["grid"], zorder=0)
    ax_curve.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax_curve.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax_curve.spines[spine].set_color(IEEE_THEME["dim"])
    ax_curve.tick_params(colors=IEEE_THEME["text"])

    # ========================================================================
    # PANEL B: PHASE CHANGE SCHEMATIC (Before/After 4:00 PM)
    # ========================================================================

    ax_schematic.set_xlim(0, 12)
    ax_schematic.set_ylim(0, 7.8)
    ax_schematic.axis("off")

    # Panel B title - positioned to avoid overlap with 4:00 PM marker
    ax_schematic.text(
        6,
        7.3,
        "(B) The Expiration Event: What Happens at 4:00 PM",
        fontsize=13,
        fontweight="bold",
        ha="center",
        va="top",
        color=IEEE_THEME["text"],
    )

    # Common parameters
    bar_width = 1.0
    bar_base_y = 1.5
    bar_height = 3.2

    # --- LEFT PANEL: BEFORE (3:55 PM) ---
    left_center_x = 2.5

    # Panel background
    left_panel = FancyBboxPatch(
        (0.3, 0.6),
        4.4,
        5.5,
        boxstyle="round,pad=0.1",
        facecolor=COLORS["background_panel"],
        edgecolor=IEEE_THEME["dim"],
        linewidth=1.5,
        alpha=0.5,
    )
    ax_schematic.add_patch(left_panel)

    # Panel header
    ax_schematic.text(
        left_center_x,
        5.5,
        "3:55 PM ET",
        fontsize=13,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=IEEE_THEME["text"],
    )
    ax_schematic.text(
        left_center_x,
        5.2,
        "Before Expiration",
        fontsize=10,
        ha="center",
        va="bottom",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # Gamma Exposure Bar (red)
    gamma_bar = FancyBboxPatch(
        (left_center_x - bar_width - 0.3, bar_base_y),
        bar_width,
        bar_height,
        boxstyle="round,pad=0.05",
        facecolor=COLORS["gamma"],
        edgecolor=COLORS["gamma"],
        linewidth=2,
        alpha=0.9,
    )
    ax_schematic.add_patch(gamma_bar)
    ax_schematic.text(
        left_center_x - bar_width / 2 - 0.3,
        1.2,
        "Gamma\nExposure",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="top",
        color=COLORS["gamma"],
    )
    ax_schematic.text(
        left_center_x - bar_width / 2 - 0.3,
        bar_base_y + bar_height / 2,
        "$15B",
        fontsize=11,
        fontweight="bold",
        ha="center",
        va="center",
        color="white",
    )

    # Hedge Position Bar (blue)
    hedge_bar = FancyBboxPatch(
        (left_center_x + 0.3, bar_base_y),
        bar_width,
        bar_height,
        boxstyle="round,pad=0.05",
        facecolor=COLORS["hedge"],
        edgecolor=COLORS["hedge"],
        linewidth=2,
        alpha=0.9,
    )
    ax_schematic.add_patch(hedge_bar)
    ax_schematic.text(
        left_center_x + bar_width / 2 + 0.3,
        1.2,
        "Hedge\nPosition",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="top",
        color=COLORS["hedge"],
    )
    ax_schematic.text(
        left_center_x + bar_width / 2 + 0.3,
        bar_base_y + bar_height / 2,
        "~$15B\nStock",
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="center",
        color="white",
        linespacing=1.0,
    )

    # --- CENTER: 4:00 PM MARKER ---
    center_x = 6.0

    # Vertical dashed line
    ax_schematic.axvline(
        x=center_x, ymin=0.10, ymax=0.80, color=COLORS["time_marker"], linewidth=3, linestyle="--", alpha=0.8
    )

    # Time marker label - positioned below the title
    ax_schematic.text(
        center_x,
        5.7,
        "4:00 PM ET",
        fontsize=12,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=COLORS["time_marker"],
        bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=COLORS["time_marker"], linewidth=2),
    )

    # Expiration event annotation
    ax_schematic.text(
        center_x,
        0.55,
        "0DTE OPTIONS EXPIRE",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="center",
        color=COLORS["time_marker"],
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#E8F5E9", edgecolor=COLORS["time_marker"], linewidth=1.5),
    )

    # Transformation arrow
    ax_schematic.annotate(
        "",
        xy=(7.5, 3.2),
        xytext=(4.8, 3.2),
        arrowprops=dict(
            arrowstyle="-|>", lw=2.5, color=COLORS["arrow"], mutation_scale=15, connectionstyle="arc3,rad=0"
        ),
    )

    # --- RIGHT PANEL: AFTER (4:05 PM) ---
    right_center_x = 9.5

    # Panel background
    right_panel = FancyBboxPatch(
        (7.3, 0.6),
        4.4,
        5.5,
        boxstyle="round,pad=0.1",
        facecolor=COLORS["background_panel"],
        edgecolor=IEEE_THEME["dim"],
        linewidth=1.5,
        alpha=0.5,
    )
    ax_schematic.add_patch(right_panel)

    # Panel header
    ax_schematic.text(
        right_center_x,
        5.5,
        "4:05 PM ET",
        fontsize=13,
        fontweight="bold",
        ha="center",
        va="bottom",
        color=IEEE_THEME["text"],
    )
    ax_schematic.text(
        right_center_x,
        5.2,
        "After Expiration",
        fontsize=10,
        ha="center",
        va="bottom",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    # Gamma Exposure Bar - VANISHED (ghosted)
    gamma_ghost = FancyBboxPatch(
        (right_center_x - bar_width - 0.3, bar_base_y),
        bar_width,
        bar_height,
        boxstyle="round,pad=0.05",
        facecolor="none",
        edgecolor=COLORS["expired"],
        linewidth=2,
        linestyle="--",
        alpha=0.6,
    )
    ax_schematic.add_patch(gamma_ghost)
    ax_schematic.text(
        right_center_x - bar_width / 2 - 0.3,
        1.2,
        "Gamma\n(Expired)",
        fontsize=9,
        ha="center",
        va="top",
        color=COLORS["expired"],
        style="italic",
    )
    ax_schematic.text(
        right_center_x - bar_width / 2 - 0.3,
        bar_base_y + bar_height / 2,
        "EXPIRED\n$0",
        fontsize=10,
        fontweight="bold",
        ha="center",
        va="center",
        color=COLORS["expired"],
    )

    # Hedge Position Bar - STILL PRESENT (orange for scar tissue)
    residual_bar = FancyBboxPatch(
        (right_center_x + 0.3, bar_base_y),
        bar_width,
        bar_height,
        boxstyle="round,pad=0.05",
        facecolor=COLORS["scar_tissue"],
        edgecolor=COLORS["scar_tissue"],
        linewidth=2,
        alpha=0.9,
    )
    ax_schematic.add_patch(residual_bar)
    ax_schematic.text(
        right_center_x + bar_width / 2 + 0.3,
        1.2,
        '"Scar Tissue"',
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="top",
        color=COLORS["scar_tissue"],
    )
    ax_schematic.text(
        right_center_x + bar_width / 2 + 0.3,
        bar_base_y + bar_height / 2,
        "~$15B\nStock\nRemainder",
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="center",
        color="white",
        linespacing=1.0,
    )

    # ========================================================================
    # BOTTOM: KEY INSIGHT BOX
    # ========================================================================

    insight_text = (
        "Key Insight: The hedge position (~$15B stock) does NOT automatically unwind when options expire.\n"
        "This 'Scar Tissue' must be unwound during overnight/T+1, creating the residual positioning detected in EOD open interest."
    )

    fig.text(
        0.5,
        0.02,
        insight_text,
        fontsize=10,
        ha="center",
        va="bottom",
        color=IEEE_THEME["text"],
        bbox=dict(
            boxstyle="round,pad=0.5", facecolor="#E3F2FD", edgecolor=COLORS["scar_tissue"], linewidth=1.5, alpha=0.95
        ),
        linespacing=1.4,
    )

    plt.tight_layout(rect=[0, 0.06, 1, 0.95])

    return fig


def main():
    print("Generating Scar Tissue Mechanism Figure (Combined Two-Panel View)...")
    fig = create_figure()
    save_figure(fig, "fig09_scar_tissue.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
