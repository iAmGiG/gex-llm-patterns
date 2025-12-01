#!/usr/bin/env python3
"""
Generate Figure 7: Confidence Score Distribution

Shows distribution of LLM confidence scores across three patterns (N=242 days each).
Demonstrates that all patterns show strong concentration above the 60% threshold.

Data sources:
- gamma_positioning_SPY_2024_unbiased.yaml
- stock_pinning_SPY_2024_unbiased.yaml
- 0dte_hedging_SPY_2024_unbiased.yaml
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

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
OUTPUT_DIR = Path(__file__).parent.parent


def load_confidence_scores(pattern_name):
    """Extract confidence scores from validation YAML file."""
    filepath = REPORTS_DIR / f"{pattern_name}_SPY_2024_unbiased.yaml"

    if not filepath.exists():
        print(f"WARNING: {filepath} not found")
        return []

    with open(filepath, "r") as f:
        data = yaml.safe_load(f)

    # Extract confidence scores from all detections
    confidences = []
    for detection in data.get("detections", []):
        if detection.get("detected", False):
            conf = detection["narrative"].get("confidence", 0)
            confidences.append(conf)

    return confidences


def create_figure(confidence_data):
    """Create grouped bar chart showing confidence distributions for all three patterns."""

    # Create figure (reduced height to eliminate white space)
    fig, ax = plt.subplots(figsize=(10, 4), dpi=300)

    # Define bins (0-100% in 10% intervals)
    bins = np.arange(0, 105, 10)
    bin_centers = bins[:-1] + 5  # Center of each bin

    # Colors for each pattern
    colors = {
        "gamma_positioning": "#2E86AB",  # Blue
        "stock_pinning": "#A23B72",  # Purple
        "0dte_hedging": "#F18F01",  # Orange
    }

    labels = {
        "gamma_positioning": "Gamma Positioning",
        "stock_pinning": "Stock Pinning",
        "0dte_hedging": "0DTE Hedging",
    }

    # Calculate histograms for each pattern
    pattern_order = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
    bar_width = 2.5  # Width of each bar
    x_positions = {}

    for i, pattern in enumerate(pattern_order):
        confidences = confidence_data.get(pattern, [])
        if not confidences:
            continue

        # Calculate histogram
        counts, _ = np.histogram(confidences, bins=bins)

        # Position bars side-by-side
        x_offset = (i - 1) * bar_width  # -1, 0, 1 positions
        x_pos = bin_centers + x_offset

        ax.bar(
            x_pos,
            counts,
            width=bar_width,
            label=f"{labels[pattern]} (N={len(confidences)})",
            color=colors[pattern],
            alpha=0.85,
            edgecolor="black",
            linewidth=0.8,
            zorder=3,
        )

    # Add vertical line at 60% threshold (render behind bars)
    ax.axvline(
        x=60, color="red", linestyle="--", linewidth=2.5, label="Mechanical Threshold (60%)", zorder=2, alpha=0.8
    )

    # Labels and title (increased font sizes)
    ax.set_xlabel("Confidence Score (%)", fontweight="bold", fontsize=11)
    ax.set_ylabel("Frequency (Number of Days)", fontweight="bold", fontsize=11)
    ax.set_title(
        "Distribution of Detection Confidence Scores Across Three Patterns", fontweight="bold", pad=15, fontsize=12
    )

    # Grid
    ax.grid(True, alpha=0.3, axis="y", zorder=0)

    # Legend (upper left since data is sparse there) - increased font
    ax.legend(loc="upper left", framealpha=0.98, edgecolor="gray", fontsize=10)

    # Add statistics text box
    stats_text = []
    for pattern in pattern_order:
        confidences = confidence_data.get(pattern, [])
        if confidences:
            mean_conf = np.mean(confidences)
            above_60 = sum(1 for c in confidences if c >= 60)
            pct_above = (above_60 / len(confidences)) * 100
            stats_text.append(f"{labels[pattern]}: {mean_conf:.1f}% mean, {pct_above:.1f}% ≥60%")

    stats_str = "\n".join(stats_text)
    # Positioned in mid-right where there's empty space - increased font
    ax.text(
        0.98,
        0.55,
        stats_str,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="center",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.95, edgecolor="gray"),
        zorder=5,
    )

    # Set x-axis limits (focus on data range)
    ax.set_xlim(55, 100)

    plt.tight_layout()

    return fig


def create_kde_figure(confidence_data):
    """Create smooth KDE plot as alternative visualization."""
    from scipy.stats import gaussian_kde

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)

    colors = {"gamma_positioning": "#2E86AB", "stock_pinning": "#A23B72", "0dte_hedging": "#F18F01"}

    labels = {
        "gamma_positioning": "Gamma Positioning",
        "stock_pinning": "Stock Pinning",
        "0dte_hedging": "0DTE Hedging",
    }

    x = np.linspace(0, 100, 200)

    for pattern, confidences in confidence_data.items():
        if not confidences or len(confidences) < 2:
            continue

        # Create KDE
        kde = gaussian_kde(confidences)
        density = kde(x)

        ax.plot(x, density, linewidth=2.5, label=f"{labels[pattern]} (N={len(confidences)})", color=colors[pattern])
        ax.fill_between(x, 0, density, alpha=0.2, color=colors[pattern])

    # Add vertical line at 60% threshold
    ax.axvline(x=60, color="red", linestyle="--", linewidth=2, label="Mechanical Threshold (60%)", zorder=10)

    ax.set_xlabel("Confidence Score (%)", fontweight="bold")
    ax.set_ylabel("Probability Density", fontweight="bold")
    ax.set_title("Probability Density of Detection Confidence Scores", fontweight="bold", pad=15)

    ax.grid(True, alpha=0.3, axis="y")
    ax.legend(loc="upper right", framealpha=0.95, edgecolor="gray")
    # Truncate x-axis to focus on data range
    ax.set_xlim(50, 100)

    plt.tight_layout()

    return fig


def main():
    """Generate Figure 7."""
    print("Loading confidence scores from validation data...")

    patterns = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
    confidence_data = {}

    for pattern in patterns:
        confidences = load_confidence_scores(pattern)
        confidence_data[pattern] = confidences

        if confidences:
            print(
                f"  {pattern}: {len(confidences)} detections, "
                f"mean={np.mean(confidences):.1f}%, "
                f"{sum(1 for c in confidences if c >= 60)}/{len(confidences)} ≥60%"
            )
        else:
            print(f"  {pattern}: No data found")

    if not any(confidence_data.values()):
        print("ERROR: No confidence data found")
        return

    print("\nGenerating histogram figure...")
    fig_hist = create_figure(confidence_data)

    # Save histogram
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "../fig08_confidence_distribution.png"
    fig_hist.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✅ Saved: {output_file}")
    plt.close(fig_hist)

    # KDE version disabled - not needed for paper
    if False:
        print("\nGenerating KDE (smooth) figure...")
        fig_kde = create_kde_figure(confidence_data)

        # Save KDE version
        output_file_kde = OUTPUT_DIR / "fig7_confidence_kde_alternate.png"
        fig_kde.savefig(output_file_kde, dpi=300, bbox_inches="tight")
        print(f"✅ Saved KDE version: {output_file_kde}")
        plt.close(fig_kde)

    print("\n✅ Figure 7 complete!")
    print("Shows all three patterns concentrated above 60% threshold")


if __name__ == "__main__":
    main()
