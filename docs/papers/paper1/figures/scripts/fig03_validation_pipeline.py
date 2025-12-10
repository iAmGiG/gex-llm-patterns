#!/usr/bin/env python3
"""
Generate Figure 3: Validation Pipeline Architecture

Shows the validation pipeline flow from raw options data through to statistical validation.

Components:
1. Options Data → 2. GEX Calculator → 3. Data Obfuscator → 4. LLM Agent →
5. Outcome Calculator → 6. Statistical Validator

With example outputs at each stage.
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# JFDS single-column format (larger for readability)
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.labelsize": 12,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
    }
)

OUTPUT_DIR = Path(__file__).parent


def create_figure():
    """Create system architecture flowchart."""

    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(1.5, 8)
    ax.axis("off")

    # Define colors
    color_data = "#E8F4F8"  # Light blue
    color_process = "#FFF4E6"  # Light orange
    color_llm = "#F0E6FF"  # Light purple
    color_output = "#E6FFE6"  # Light green

    # Component positions (x, y, width, height)
    # Top row - main pipeline components
    components = {
        "options_data": (0.5, 6.5, 1.8, 0.8),
        "gex_calc": (2.8, 6.5, 1.8, 0.8),
        "obfuscator": (5.1, 6.5, 1.8, 0.8),
        "llm_agent": (7.4, 6.5, 1.8, 0.8),
        "outcome_calc": (2.8, 4.2, 1.8, 0.8),  # Moved down for spacing
        "stat_validator": (5.1, 4.2, 1.8, 0.8),  # Moved down for spacing
    }

    # Output boxes (below each component with proper spacing)
    outputs = {
        "opts_out": (0.5, 5.4, 1.8, 0.8),  # 0.3 gap below component
        "gex_out": (2.8, 5.4, 1.8, 0.8),  # 0.3 gap below component
        "obf_out": (5.1, 5.4, 1.8, 0.8),  # 0.3 gap below component
        "llm_out": (7.4, 5.4, 1.8, 0.8),  # 0.3 gap below component
        "outcome_out": (2.8, 3.1, 1.8, 0.8),  # 0.3 gap below component
        "stat_out": (5.1, 3.1, 1.8, 0.8),  # 0.3 gap below component
    }

    # Draw component boxes
    def draw_box(pos, color, title, subtitle=""):
        x, y, w, h = pos
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", edgecolor="black", facecolor=color, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + w / 2, y + h / 2 + 0.15, title, ha="center", va="center", fontweight="bold", fontsize=12)
        if subtitle:
            ax.text(x + w / 2, y + h / 2 - 0.15, subtitle, ha="center", va="center", fontsize=10, style="italic")

    # Draw components
    draw_box(components["options_data"], color_data, "Options Data", "Raw SPY chain")
    draw_box(components["gex_calc"], color_process, "GEX\nCalculator")
    draw_box(components["obfuscator"], color_process, "Data\nObfuscator")
    draw_box(components["llm_agent"], color_llm, "LLM Agent", "GPT-o3-mini")
    draw_box(components["outcome_calc"], color_process, "Outcome\nCalculator")
    draw_box(components["stat_validator"], color_output, "Statistical\nValidator")

    # Draw output boxes (smaller, different style)
    def draw_output(pos, text, color="#FFFACD"):
        x, y, w, h = pos
        box = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.03", edgecolor="gray", facecolor=color, linewidth=0.8, linestyle="--"
        )
        ax.add_patch(box)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9, family="monospace")

    # Output examples
    draw_output(outputs["opts_out"], "Strike: 480\nOI: 12,500\nIV: 14.2%")
    draw_output(outputs["gex_out"], "Net GEX:\n-$32.9B\nFlip: 475")
    draw_output(outputs["obf_out"], "Day T+0\nINDEX_1\n-$32.9B")
    draw_output(outputs["llm_out"], "WHO/WHOM/\nWHAT\nConf: 80%")
    draw_output(outputs["outcome_out"], "T+1 Return:\n-0.86%\nVol: 0.50%")
    draw_output(outputs["stat_out"], "Detection:\n71.5%\nN=242")

    # Draw arrows between components (horizontal flow)
    arrow_style = dict(arrowstyle="->", lw=2, color="#333333")

    def draw_arrow(from_box, to_box):
        x1 = from_box[0] + from_box[2]  # right edge of from_box
        y1 = from_box[1] + from_box[3] / 2  # middle height
        x2 = to_box[0]  # left edge of to_box
        y2 = to_box[1] + to_box[3] / 2
        arrow = FancyArrowPatch((x1, y1), (x2, y2), **arrow_style)
        ax.add_patch(arrow)

    # Horizontal flow arrows
    draw_arrow(components["options_data"], components["gex_calc"])
    draw_arrow(components["gex_calc"], components["obfuscator"])
    draw_arrow(components["obfuscator"], components["llm_agent"])

    # Custom routed arrow from LLM Agent to Outcome Calculator
    # Routes around the obfuscator output box to avoid overlap
    def draw_routed_arrow(from_box, to_box):
        """Draw arrow with waypoints to route around obstacles."""
        # Start point: center-right of LLM Agent (instead of bottom-center)
        x1 = from_box[0] + from_box[2]  # Right edge
        y1 = from_box[1] + from_box[3] / 2  # Middle height

        # End point: top center of Outcome Calculator
        x_end = to_box[0] + to_box[2] / 2
        y_end = to_box[1] + to_box[3]

        # Waypoints to route around obfuscator output box
        # Go right first, then down, then left
        waypoint1_x = from_box[0] + from_box[2] + 0.3  # Right of LLM Agent
        waypoint1_y = y1  # Same height as start

        waypoint2_x = waypoint1_x
        waypoint2_y = to_box[1] + to_box[3] + 0.3  # Above Outcome Calculator

        waypoint3_x = x_end
        waypoint3_y = waypoint2_y

        # Draw the path segments
        path_style = dict(lw=2, color="#333333")

        # Segment 1: right from LLM center-right to waypoint1
        ax.plot([x1, waypoint1_x], [y1, waypoint1_y], **path_style)

        # Segment 2: down from waypoint1 to waypoint2
        ax.plot([waypoint1_x, waypoint2_x], [waypoint1_y, waypoint2_y], **path_style)

        # Segment 3: left from waypoint2 to waypoint3
        ax.plot([waypoint2_x, waypoint3_x], [waypoint2_y, waypoint3_y], **path_style)

        # Segment 4: down to final destination with arrow
        arrow = FancyArrowPatch((waypoint3_x, waypoint3_y), (x_end, y_end), **arrow_style)
        ax.add_patch(arrow)

    draw_routed_arrow(components["llm_agent"], components["outcome_calc"])
    draw_arrow(components["outcome_calc"], components["stat_validator"])

    # Add title
    ax.text(5, 7.7, "Pattern Validation Pipeline Architecture", ha="center", fontsize=16, fontweight="bold")

    # Add legend for colors
    legend_y = 0.8
    legend_elements = [
        mpatches.Rectangle((0, 0), 1, 1, fc=color_data, ec="black", label="Data Source"),
        mpatches.Rectangle((0, 0), 1, 1, fc=color_process, ec="black", label="Processing"),
        mpatches.Rectangle((0, 0), 1, 1, fc=color_llm, ec="black", label="LLM Analysis"),
        mpatches.Rectangle((0, 0), 1, 1, fc=color_output, ec="black", label="Validation"),
    ]
    ax.legend(handles=legend_elements, loc="lower center", ncol=4, frameon=True, fontsize=10)

    # Add note about obfuscation (moved down to accommodate new spacing)
    ax.text(
        5,
        2.5,
        'Obfuscation prevents training data leakage: dates → "Day T+N", tickers → "INDEX_1"',
        ha="center",
        fontsize=10,
        style="italic",
        color="#666666",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.7),
    )

    plt.tight_layout()
    return fig


def main():
    """Generate Figure 1."""
    print("Generating system architecture diagram...")

    fig = create_figure()

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "../fig03_validation_pipeline.png"
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Saved: {output_file}")

    plt.close()

    print("Figure 3 complete!")
    print("Shows complete validation pipeline from raw data to statistical results")


if __name__ == "__main__":
    main()
