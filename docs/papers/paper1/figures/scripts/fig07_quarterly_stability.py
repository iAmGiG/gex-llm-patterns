#!/usr/bin/env python3
"""
Generate Figure 5: Quarterly Stability Analysis

THE MOST CRITICAL FIGURE in Paper #1.

Shows detection rate (stable) vs net alpha (declining) across Q1-Q4 2024,
proving the LLM detects STRUCTURE not PROFITS.

Data sources:
- Q1: gamma_positioning_SPY_2024Q1.yaml
- Q2: gamma_positioning_SPY_2024Q2.yaml
- Q3: gamma_positioning_SPY_2024Q3.yaml
- Q4: gamma_positioning_SPY_2024Q4.yaml
- Unbiased: gamma_positioning_SPY_2024_unbiased.yaml
"""

from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib.lines import Line2D

# IEEE two-column format
plt.rcParams.update(
    {
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "figure.titlesize": 11,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
    }
)

# Data paths
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "validation" / "pattern_taxonomy"
OUTPUT_DIR = BASE_DIR / "docs" / "papers" / "paper1" / "figures"


def load_quarterly_data():
    """Load quarterly validation data for gamma_positioning pattern."""
    quarters = {
        "Q1 2024": "gamma_positioning_SPY_2024Q1.yaml",
        "Q2 2024": "gamma_positioning_SPY_2024Q2.yaml",
        "Q3 2024": "gamma_positioning_SPY_2024Q3.yaml",
        "Q4 2024": "gamma_positioning_SPY_2024Q4.yaml",
    }

    data = {}
    for quarter, filename in quarters.items():
        filepath = REPORTS_DIR / filename
        if not filepath.exists():
            print(f"WARNING: {filename} not found at {filepath}")
            continue

        with open(filepath, "r") as f:
            yaml_data = yaml.safe_load(f)

        # Extract metrics
        perf = yaml_data["performance_metrics"]
        data[quarter] = {
            "detection_rate": perf["detection_rate_pct"],
            "accuracy": perf["predictive_accuracy_pct"],
            "net_alpha": perf["net_alpha_pct"] * 100,  # Convert to bps
            "sample_size": perf["total_tested"],
        }

    return data


def load_unbiased_data():
    """Load unbiased full-year validation data."""
    filepath = REPORTS_DIR / "gamma_positioning_SPY_2024_unbiased.yaml"

    if not filepath.exists():
        print(f"WARNING: Unbiased data not found")
        return None

    with open(filepath, "r") as f:
        yaml_data = yaml.safe_load(f)

    perf = yaml_data["performance_metrics"]
    return {
        "detection_rate": perf["detection_rate_pct"],
        "accuracy": perf["predictive_accuracy_pct"],
        "net_alpha": perf["net_alpha_pct"] * 100,  # Convert to bps
        "sample_size": perf["total_tested"],
    }


def create_figure(quarterly_data, unbiased_data):
    """Create dual-axis chart showing detection vs profitability divergence."""

    # Create figure with increased height to use more y-axis space
    fig, ax1 = plt.subplots(figsize=(7, 5.5), dpi=300)

    quarters = list(quarterly_data.keys())
    detection_rates = [quarterly_data[q]["detection_rate"] for q in quarters]
    net_alphas = [quarterly_data[q]["net_alpha"] for q in quarters]

    # Primary y-axis: Detection Rate
    color_detection = "#2E86AB"  # Blue
    ax1.set_xlabel("Quarter", fontweight="bold")
    ax1.set_ylabel("Detection Rate (%)", fontweight="bold", color=color_detection)
    line1 = ax1.plot(
        quarters,
        detection_rates,
        "o-",
        color=color_detection,
        linewidth=2.5,
        markersize=8,
        label="Detection Rate (Biased Prompts)",
        zorder=3,
    )
    ax1.tick_params(axis="y", labelcolor=color_detection)

    # Set y-axis range to maximize use of space while keeping threshold visible
    # Use actual QUARTERLY data range (not unbiased) to determine zoom
    min_det_quarterly = min(detection_rates)
    max_det = max(detection_rates)

    # More aggressive zoom to use vertical space better
    # Start slightly above 60% threshold, end slightly above max detection
    y_min = 60  # Keep 60% threshold visible
    y_max = max_det + 3  # Small padding above highest point

    ax1.set_ylim(y_min, y_max)

    ax1.grid(True, alpha=0.3, axis="y")

    # Add horizontal line for unbiased detection rate with label
    if unbiased_data:
        unbiased_line = ax1.axhline(
            y=unbiased_data["detection_rate"], color=color_detection, linestyle="--", linewidth=1.5, alpha=0.7, zorder=2
        )
        # Add text label on the line
        ax1.text(
            0.02,
            unbiased_data["detection_rate"] + 1,
            f"Unbiased: {unbiased_data['detection_rate']:.1f}%",
            fontsize=7,
            color=color_detection,
            style="italic",
            transform=ax1.get_yaxis_transform(),
        )

    # Add 60% threshold line with label positioned near left
    threshold_line = ax1.axhline(y=60, color="red", linestyle=":", linewidth=1.5, alpha=0.6, zorder=1)
    # Add text label on the line (left side, slightly above line)
    ax1.text(
        0.02,
        60 + 0.5,
        "60% Threshold",
        fontsize=7,
        color="red",
        style="italic",
        ha="left",
        transform=ax1.get_yaxis_transform(),
    )

    # Secondary y-axis: Net Alpha
    ax2 = ax1.twinx()
    color_alpha = "#A23B72"  # Purple/Maroon
    ax2.set_ylabel("Net Alpha (bps)", fontweight="bold", color=color_alpha)
    line2 = ax2.plot(
        quarters, net_alphas, "s-", color=color_alpha, linewidth=2.5, markersize=8, label="Net Alpha", zorder=4
    )
    ax2.tick_params(axis="y", labelcolor=color_alpha)

    # Set y-axis range for alpha to show decline clearly
    min_alpha = min(net_alphas)
    max_alpha = max(net_alphas)
    padding = (max_alpha - min_alpha) * 0.2
    ax2.set_ylim(min_alpha - padding, max_alpha + padding)

    # Add zero line for alpha
    ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.8, alpha=0.5)

    # Annotate the divergence
    # Calculate actual detection change
    det_first = detection_rates[0]
    det_last = detection_rates[-1]
    alpha_first = net_alphas[0]
    alpha_last = net_alphas[-1]

    # Add key statistics as subtitle/annotation at bottom instead of on-chart boxes
    # This avoids blocking the flat 100% detection line in Q1-Q3
    fig.text(
        0.5,
        0.08,
        f"Detection: {det_first:.0f}% → {det_last:.0f}% (remains above 60% threshold)  |  "
        f"Net Alpha: {alpha_first:+.0f} → {alpha_last:+.0f} bps (profitability declines)",
        ha="center",
        fontsize=9,
        style="italic",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f0f0f0", edgecolor="gray", linewidth=1, alpha=0.9),
    )

    # Title
    plt.title("Pattern Detection Persists Above Threshold Despite Declining Profitability", fontweight="bold", pad=15)

    # Combined legend - only show actual plotted lines (not reference lines)
    legend_elements = [
        Line2D(
            [0], [0], color=color_detection, linewidth=2.5, marker="o", markersize=8, label="Detection Rate (Biased)"
        ),
        Line2D([0], [0], color=color_alpha, linewidth=2.5, marker="s", markersize=8, label="Net Alpha (bps)"),
    ]

    # Position legend to avoid Q3 data point at (Q3 2024, 100%)
    # Use 'center right' or specific coordinates
    ax1.legend(handles=legend_elements, loc="center right", framealpha=0.95, edgecolor="gray", fontsize=9)

    # Add sample sizes as text at very bottom (below statistics box)
    sample_text = " | ".join([f"{q}: N={quarterly_data[q]['sample_size']}" for q in quarters])
    fig.text(0.5, 0.01, sample_text, ha="center", fontsize=7, style="italic", color="gray")

    # Use tight_layout with space for bottom annotation
    # Extra bottom space for statistics box
    plt.tight_layout(rect=[0, 0.12, 1, 0.98])

    return fig


def main():
    """Generate Figure 3."""
    print("Loading quarterly data...")
    quarterly_data = load_quarterly_data()

    print("Loading unbiased data...")
    unbiased_data = load_unbiased_data()

    if not quarterly_data:
        print("ERROR: No quarterly data found")
        return

    print(f"Loaded {len(quarterly_data)} quarters")
    for quarter, metrics in quarterly_data.items():
        print(f"  {quarter}: {metrics['detection_rate']:.1f}% detection, " f"{metrics['net_alpha']:+.1f} bps alpha")

    if unbiased_data:
        print(
            f"  Unbiased: {unbiased_data['detection_rate']:.1f}% detection, "
            f"{unbiased_data['net_alpha']:+.1f} bps alpha"
        )

    print("\nGenerating figure...")
    fig = create_figure(quarterly_data, unbiased_data)

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "../fig07_quarterly_stability.png"
    fig.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✅ Saved: {output_file}")

    plt.close()

    print("\n⭐ CRITICAL FIGURE COMPLETE ⭐")
    print("This is THE visual anchor of the paper's main finding:")
    det_range = f"{quarterly_data[list(quarterly_data.keys())[0]]['detection_rate']:.0f}% → {quarterly_data[list(quarterly_data.keys())[-1]]['detection_rate']:.0f}%"
    alpha_range = f"{quarterly_data[list(quarterly_data.keys())[0]]['net_alpha']:+.0f} → {quarterly_data[list(quarterly_data.keys())[-1]]['net_alpha']:+.0f} bps"
    print(f"  Detection: {det_range} (stays above threshold)")
    print(f"  Profitability: {alpha_range} (declines to unprofitable)")
    print("  Proves LLM detects STRUCTURE not PROFITS")


if __name__ == "__main__":
    main()
