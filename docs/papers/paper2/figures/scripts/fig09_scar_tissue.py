#!/usr/bin/env python3
"""
Generate Figure 9: Scar Tissue Mechanism Diagram

This script creates a visualization showing how 0DTE intraday trading creates
"scar tissue" in overnight open interest positioning, using a gamma decay curve
that illustrates incomplete unwinding at market close.

IEEE Publication Theme (white background).

Issue #168: Add 'Scar Tissue' Mechanism Diagram
Output: docs/papers/paper2/figures/output/fig09_scar_tissue.png
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D
from theme import IEEE_THEME, OUTPUT_DIR, save_figure

# Diagram colors
COLORS = {
    "gamma_curve": "#C62828",  # Red for gamma exposure
    "hedging": "#1565C0",  # Blue for hedging activity
    "residual": "#E65100",  # Orange for residual/scar tissue
    "zero_line": "#757575",  # Grey for zero reference
    "fill_intraday": "#FFCDD2",  # Light red fill
    "fill_residual": "#FFE0B2",  # Light orange fill
    "time_marker": "#2E7D32",  # Green for EOD marker
}


def create_figure():
    """Create scar tissue mechanism diagram with gamma decay curve."""

    plt.style.use("default")

    # Create figure with two panels: curve on top, flow diagram below
    fig = plt.figure(figsize=(12, 8), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])

    # Create grid: main curve takes 60%, flow diagram takes 40%
    gs = fig.add_gridspec(2, 1, height_ratios=[1.4, 1], hspace=0.25)

    ax_curve = fig.add_subplot(gs[0])
    ax_flow = fig.add_subplot(gs[1])

    ax_curve.set_facecolor(IEEE_THEME["background"])
    ax_flow.set_facecolor(IEEE_THEME["background"])

    # ========================================================================
    # TOP PANEL: Gamma Exposure Decay Curve
    # ========================================================================

    # Time axis: 9:30 AM to 4:00 PM (trading hours) + after hours
    # Normalized: 0 = market open, 1 = market close, 1.2 = after hours
    t = np.linspace(0, 1.2, 500)

    # Gamma exposure curve:
    # - Rises during morning as 0DTE positions accumulate
    # - Peaks mid-afternoon as theta accelerates
    # - Partial decay near close as some positions unwind
    # - CRITICAL: Does NOT return to zero - residual remains

    # Morning buildup (0 to 0.3): exponential rise
    # Peak period (0.3 to 0.7): sustained high gamma
    # Partial unwind (0.7 to 1.0): decay but NOT to zero
    # Residual (1.0+): flat residual that persists overnight

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

    gamma = gamma_curve(t)

    # Plot the gamma curve
    ax_curve.plot(t, gamma, color=COLORS["gamma_curve"], linewidth=3, label="Dealer Gamma Exposure", zorder=5)

    # Fill area under curve during trading hours
    trading_mask = t <= 1.0
    ax_curve.fill_between(t[trading_mask], 0, gamma[trading_mask],
                          color=COLORS["fill_intraday"], alpha=0.4, zorder=2)

    # Highlight residual area (scar tissue)
    residual_mask = t >= 1.0
    ax_curve.fill_between(t[residual_mask], 0, gamma[residual_mask],
                          color=COLORS["fill_residual"], alpha=0.6, zorder=3,
                          label='"Scar Tissue" Residual')

    # Also show scar tissue level extending back into trading hours
    ax_curve.axhline(y=6.0, color=COLORS["residual"], linestyle="--", linewidth=1.5,
                     alpha=0.7, zorder=4)
    ax_curve.fill_between([0.85, 1.2], 0, 6.0, color=COLORS["fill_residual"],
                          alpha=0.3, zorder=1)

    # Zero reference line
    ax_curve.axhline(y=0, color=COLORS["zero_line"], linewidth=1, zorder=1)

    # Market close vertical line
    ax_curve.axvline(x=1.0, color=COLORS["time_marker"], linewidth=2, linestyle="-",
                     label="Market Close (4:00 PM)", zorder=4)

    # Annotations - positioned to avoid collisions with legend in upper left
    # Peak gamma annotation - positioned to center-right above curve
    peak_idx = np.argmax(gamma)
    ax_curve.annotate(
        "Peak Gamma",
        xy=(t[peak_idx], gamma[peak_idx]),
        xytext=(0.70, 26),
        fontsize=11,
        fontweight="bold",
        color=COLORS["gamma_curve"],
        ha="center",
        arrowprops=dict(arrowstyle="->", color=COLORS["gamma_curve"], lw=1.5,
                        connectionstyle="arc3,rad=0.2"),
    )

    # Incomplete unwind annotation - arrow points to the declining curve section (around x=0.82, y=14)
    # This is where the curve is actively declining but NOT reaching zero
    ax_curve.annotate(
        "Incomplete Unwind",
        xy=(0.82, gamma_curve(np.array([0.82]))[0]),  # Point directly on the curve
        xytext=(0.55, 4),
        fontsize=10,
        fontweight="bold",
        color=COLORS["hedging"],
        ha="center",
        arrowprops=dict(arrowstyle="->", color=COLORS["hedging"], lw=1.5,
                        connectionstyle="arc3,rad=-0.2"),
    )

    # Residual annotation - text box in the after-hours region
    ax_curve.text(
        1.12, 10,
        '"Scar Tissue"\nResidual\n(EOD OI)',
        fontsize=9,
        fontweight="bold",
        color=COLORS["residual"],
        ha="center",
        va="center",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor=COLORS["residual"], linewidth=1.5, alpha=0.95),
    )
    # Arrow from text box to residual level
    ax_curve.annotate(
        "",
        xy=(1.08, 6.0),
        xytext=(1.10, 8.5),
        arrowprops=dict(arrowstyle="->", color=COLORS["residual"], lw=1.5),
    )

    # X-axis labels (trading hours)
    ax_curve.set_xlim(-0.02, 1.22)
    ax_curve.set_xticks([0, 0.25, 0.5, 0.75, 1.0, 1.1])
    ax_curve.set_xticklabels(["9:30\nOpen", "11:00", "12:30", "2:00", "4:00\nClose", "After\nHours"],
                              fontsize=10)

    # Y-axis
    ax_curve.set_ylim(-1, 28)
    ax_curve.set_ylabel("Gamma Exposure ($B)", fontsize=12, fontweight="bold", color=IEEE_THEME["text"])
    ax_curve.set_xlabel("Trading Day Timeline", fontsize=12, fontweight="bold", color=IEEE_THEME["text"])

    # Title
    ax_curve.set_title("Intraday Gamma Dynamics: Why 0DTE Creates EOD Positioning",
                       fontsize=14, fontweight="bold", color=IEEE_THEME["text"], pad=10)

    # Legend
    legend = ax_curve.legend(loc="upper left", fontsize=10, framealpha=0.95,
                             facecolor="white", edgecolor=IEEE_THEME["dim"])

    # Grid
    ax_curve.grid(True, alpha=0.3, linestyle="-", color=IEEE_THEME["grid"], zorder=0)
    ax_curve.set_axisbelow(True)

    # Spines
    for spine in ["top", "right"]:
        ax_curve.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax_curve.spines[spine].set_color(IEEE_THEME["dim"])
    ax_curve.tick_params(colors=IEEE_THEME["text"])

    # ========================================================================
    # BOTTOM PANEL: Causal Flow Diagram (simplified) - shifted left
    # ========================================================================

    ax_flow.set_xlim(-0.5, 10)
    ax_flow.set_ylim(0, 2.5)
    ax_flow.axis("off")

    # Stage definitions - horizontal flow, shifted left by 0.5
    stages = [
        {"title": "0DTE\nVolume", "x": 0.0, "color": "#1565C0"},
        {"title": "Gamma\nExplosion", "x": 2.0, "color": "#C62828"},
        {"title": "Dealer\nHedging", "x": 4.0, "color": "#757575"},
        {"title": "Incomplete\nUnwind", "x": 6.0, "color": "#E65100"},
        {"title": "EOD OI\n(Measured)", "x": 8.0, "color": "#2E7D32"},
    ]

    box_width = 1.6
    box_height = 1.4
    y_center = 1.4

    for stage in stages:
        x = stage["x"]
        y = y_center - box_height / 2

        # Main box
        box = FancyBboxPatch(
            (x, y),
            box_width,
            box_height,
            boxstyle="round,pad=0.08",
            facecolor=stage["color"],
            edgecolor=stage["color"],
            linewidth=2,
            alpha=0.9,
        )
        ax_flow.add_patch(box)

        # Title
        ax_flow.text(
            x + box_width / 2,
            y + box_height / 2,
            stage["title"],
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="#FFFFFF",
            linespacing=1.1,
        )

    # Draw arrows between stages
    for i in range(len(stages) - 1):
        x_start = stages[i]["x"] + box_width + 0.05
        x_end = stages[i + 1]["x"] - 0.05

        ax_flow.annotate(
            "",
            xy=(x_end, y_center),
            xytext=(x_start, y_center),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=2,
                color=IEEE_THEME["dim"],
                mutation_scale=12,
            ),
        )

    # Label for the flow - centered on shifted diagram
    ax_flow.text(
        4.8, 0.15,
        "Transmission Mechanism: Intraday → Overnight Positioning",
        ha="center", va="center",
        fontsize=11, fontweight="bold",
        color=IEEE_THEME["dim"],
        style="italic",
    )

    plt.tight_layout()

    return fig


def main():
    print("Generating Scar Tissue Mechanism Figure (Redesigned with Decay Curve)...")
    fig = create_figure()
    save_figure(fig, "fig09_scar_tissue.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
