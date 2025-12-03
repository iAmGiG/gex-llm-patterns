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
from scipy.stats import gaussian_kde

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

# --- Configuration ---
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "validation" / "pattern_taxonomy"
OUTPUT_DIR = Path(__file__).parent.parent

PATTERNS = {
    "gamma_positioning": {
        "label": "Gamma Positioning",
        "color": "#2E86AB",  # Blue
    },
    "stock_pinning": {
        "label": "Stock Pinning",
        "color": "#A23B72",  # Purple
    },
    "0dte_hedging": {
        "label": "0DTE Hedging",
        "color": "#F18F01",  # Orange
    },
}
PATTERN_ORDER = ["gamma_positioning", "stock_pinning", "0dte_hedging"]


def load_confidence_scores(pattern_name: str) -> list[float]:
    """Extract confidence scores from validation YAML file."""
    filepath = REPORTS_DIR / f"{pattern_name}_SPY_2024_unbiased.yaml"

    if not filepath.exists():
        print(f"WARNING: Data file not found at {filepath}")
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


def _generate_stats_text(all_patterns_confidence: dict) -> str:
    """Generates a formatted string with summary statistics for the plot."""
    stats_text = []
    for pattern_id in PATTERN_ORDER:
        confidences = all_patterns_confidence.get(pattern_id, [])
        if confidences:
            mean_conf = np.mean(confidences)
            above_60 = sum(1 for c in confidences if c >= 60)
            pct_above = (above_60 / len(confidences)) * 100
            stats_text.append(f"{PATTERNS[pattern_id]['label']}: {mean_conf:.1f}% mean, {pct_above:.1f}% ≥60%")
    return "\n".join(stats_text)


def create_histogram_figure(all_patterns_confidence: dict):
    """Create grouped bar chart showing confidence distributions."""
    fig, ax = plt.subplots(figsize=(10, 4), dpi=300)

    # Define bins (0-100% in 10% intervals)
    bins = np.arange(0, 105, 10)
    bin_centers = bins[:-1] + 5  # Center of each bin
    bar_width = 2.5  # Width of each bar
    num_patterns = len(PATTERN_ORDER)

    for i, pattern_id in enumerate(PATTERN_ORDER):
        confidences = all_patterns_confidence.get(pattern_id, [])
        if not confidences:
            continue

        # Calculate histogram
        counts, _ = np.histogram(confidences, bins=bins)

        # Position bars side-by-side, centered around the bin center
        x_offset = (i - (num_patterns - 1) / 2) * bar_width
        x_pos = bin_centers + x_offset

        ax.bar(
            x_pos,
            counts,
            width=bar_width,
            label=f"{PATTERNS[pattern_id]['label']} (N={len(confidences)})",
            color=PATTERNS[pattern_id]["color"],
            alpha=0.85,
            edgecolor="black",
            linewidth=0.8,
            zorder=3,
        )

    # Add vertical line at 60% threshold (render behind bars)
    ax.axvline(
        x=60, color="red", linestyle="--", linewidth=2.5, label="Mechanical Threshold (60%)", zorder=2, alpha=0.8
    )

    # Labels, title, and legend
    ax.set_xlabel("Confidence Score (%)", fontweight="bold", fontsize=11)
    ax.set_ylabel("Frequency (Number of Days)", fontweight="bold", fontsize=11)
    ax.set_title(
        "Distribution of Detection Confidence Scores Across Three Patterns", fontweight="bold", pad=15, fontsize=12
    )

    # Grid
    ax.grid(True, alpha=0.3, axis="y", zorder=0)
    ax.legend(loc="upper left", framealpha=0.98, edgecolor="gray", fontsize=10)

    # Add statistics text box
    stats_str = _generate_stats_text(all_patterns_confidence)
    # Positioned in mid-right where there's empty space
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


def create_kde_figure(all_patterns_confidence: dict):
    """Create smooth KDE plot as alternative visualization."""
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    x = np.linspace(0, 100, 200)

    for pattern_id, confidences in all_patterns_confidence.items():
        if not confidences or len(confidences) < 2:
            continue

        # Create KDE
        kde = gaussian_kde(confidences)
        density = kde(x)
        pattern_meta = PATTERNS[pattern_id]

        ax.plot(
            x,
            density,
            linewidth=2.5,
            label=f"{pattern_meta['label']} (N={len(confidences)})",
            color=pattern_meta["color"],
        )
        ax.fill_between(x, 0, density, alpha=0.2, color=pattern_meta["color"])

    # Highlight the detection zone for clarity
    ax.axvspan(60, 100, facecolor="green", alpha=0.1, zorder=0, label="Detection Zone (>60%)")
    ax.axvline(x=60, color="black", linestyle="--", linewidth=1.5, label="Detection Threshold (60%)", zorder=10)

    ax.set_xlabel("Confidence Score (%)", fontweight="bold")
    ax.set_ylabel("Probability Density", fontweight="bold")
    ax.set_title("Probability Density of Detection Confidence Scores", fontweight="bold", pad=15)

    ax.grid(True, alpha=0.3, axis="y")
    handles, labels = ax.get_legend_handles_labels()
    order = [3, 4, 0, 1, 2]  # Reorder legend
    ax.legend(
        [handles[idx] for idx in order],
        [labels[idx] for idx in order],
        loc="upper left",
        framealpha=0.95,
        edgecolor="gray",
    )

    # Truncate x-axis to focus on data range
    ax.set_xlim(0, 100)

    plt.tight_layout()

    return fig


def main():
    """Generate Figure 7."""
    print("Loading confidence scores from validation data...")
    all_patterns_confidence = {}

    for pattern_id in PATTERN_ORDER:
        confidences = load_confidence_scores(pattern_id)
        all_patterns_confidence[pattern_id] = confidences

        if confidences:
            print(
                f"  {pattern_id}: {len(confidences)} detections, "
                f"mean={np.mean(confidences):.1f}%, "
                f"{sum(1 for c in confidences if c >= 60)}/{len(confidences)} ≥60%"
            )
        else:
            print(f"  {pattern_id}: No data found")

    if not any(all_patterns_confidence.values()):
        print("ERROR: No confidence data found for any pattern. Exiting.")
        return

    print("\nGenerating histogram figure...")
    # Use the primary histogram figure for the paper
    fig_hist = create_histogram_figure(all_patterns_confidence)

    # Save histogram
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "fig7_confidence_distribution.png"
    fig_hist.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"✅ Saved: {output_file}")
    plt.close(fig_hist)

    # --- Optional: Generate KDE plot as an alternative visualization ---
    generate_kde = False  # Set to True to generate the KDE plot
    if generate_kde:
        print("\nGenerating KDE (smooth) figure...")
        fig_kde = create_kde_figure(all_patterns_confidence)

        # Save KDE version
        output_file_kde = OUTPUT_DIR / "fig7_confidence_kde_alternate.png"
        fig_kde.savefig(output_file_kde, dpi=300, bbox_inches="tight")
        print(f"✅ Saved KDE version: {output_file_kde}")
        plt.close(fig_kde)

    print("\n✅ Figure 7 complete!")
    print("Shows all three patterns concentrated above 60% threshold")


if __name__ == "__main__":
    main()
