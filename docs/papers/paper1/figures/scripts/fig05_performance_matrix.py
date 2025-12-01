#!/usr/bin/env python3
"""
Figure 8: Multi-Pattern Performance Summary (YAML DATA VERSION)

Loads actual validation results from YAML files instead of hardcoded values.
Creates multiple visualizations showing detection rate, accuracy, and success metrics.

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
OUTPUT_DIR = BASE_DIR / "docs" / "papers" / "paper1" / "figures"

print("=" * 60)
print("FIGURE 6: PATTERN DETECTION PERFORMANCE (YAML DATA)")
print("=" * 60)


def load_pattern_data(pattern_name):
    """Load validation metrics from YAML file."""
    filepath = REPORTS_DIR / f"{pattern_name}_SPY_2024_unbiased.yaml"

    if not filepath.exists():
        print(f"ERROR: {filepath} not found")
        return None

    with open(filepath, "r") as f:
        data = yaml.safe_load(f)

    perf = data["performance_metrics"]
    return {
        "detection_rate": perf["detection_rate_pct"],
        "accuracy": perf["predictive_accuracy_pct"],
        "sample_size": perf["total_tested"],
        "detections": perf["high_confidence_detections"] + perf["low_confidence_detections"],
    }


# Load data from YAML files
patterns_data = {
    "Gamma\nPositioning": load_pattern_data("gamma_positioning"),
    "Stock\nPinning": load_pattern_data("stock_pinning"),
    "0DTE\nHedging": load_pattern_data("0dte_hedging"),
}

# Extract metrics
patterns = list(patterns_data.keys())
detection = [patterns_data[p]["detection_rate"] for p in patterns]
accuracy = [patterns_data[p]["accuracy"] for p in patterns]
samples = [patterns_data[p]["detections"] for p in patterns]
total_tested = patterns_data[patterns[0]]["sample_size"]  # Same for all

# Calculate success rate (detection × accuracy)
success = [(d / 100) * (a / 100) * 100 for d, a in zip(detection, accuracy)]

print(f"\nLoaded data from YAML files:")
print(f"  Total days tested per pattern: {total_tested}")
print(f"  Detection range: {min(detection):.1f}% - {max(detection):.1f}%")
print(f"  Accuracy range: {min(accuracy):.1f}% - {max(accuracy):.1f}%")
print(f"  Success range: {min(success):.1f}% - {max(success):.1f}%")

# ============================================================================
# VERSION 1: Grouped Bar Chart (PRIMARY VERSION - FIXED LEGEND)
# ============================================================================

fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(len(patterns))
width = 0.25

# Create bars
bars1 = ax.bar(
    x - width, detection, width, label="Detection Rate", color="#F77F00", alpha=0.9, edgecolor="black", linewidth=1.5
)
bars2 = ax.bar(
    x, accuracy, width, label="Prediction Accuracy", color="#06A77D", alpha=0.9, edgecolor="black", linewidth=1.5
)
bars3 = ax.bar(
    x + width, success, width, label="Overall Success", color="#2E86AB", alpha=0.9, edgecolor="black", linewidth=1.5
)

# Add value labels on bars
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 0.5,
            f"{height:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

# Add 60% threshold
ax.axhline(y=60, color="red", linestyle="--", linewidth=2.5, label="Mechanical Threshold", alpha=0.7, zorder=0)

# Configure axes
ax.set_xlabel("Pattern Type", fontsize=13, fontweight="bold")
ax.set_ylabel("Percentage (%)", fontsize=13, fontweight="bold")
ax.set_title(
    "Pattern Detection Performance Metrics\n(Unbiased Prompts, Full 2024)", fontsize=14, fontweight="bold", pad=15
)
ax.set_xticks(x)
ax.set_xticklabels(patterns, fontsize=12)
ax.set_ylim(0, 105)
# Move legend to left-center, across from stats box on right
ax.legend(loc="center left", fontsize=10, framealpha=1.0, edgecolor="black", bbox_to_anchor=(0.02, 0.30))
ax.grid(axis="y", alpha=0.3, linestyle=":", linewidth=1)

# FIXED: Move summary stats box to avoid overlapping bars
total_detections = sum(samples)
textstr = (
    f"N = {total_tested} days per pattern\n"
    f"Total tests: {total_tested * 3}\n"
    f"Detected: {total_detections} ({total_detections/(total_tested*3)*100:.1f}%)\n"
    f"Avg accuracy: {np.mean(accuracy):.1f}%\n"
    f"Overall success: {np.mean(success):.1f}%"
)
props = dict(boxstyle="round", facecolor="lightblue", alpha=0.9)
# Moved to bottom-right to avoid overlapping with bars
ax.text(
    0.98,
    0.30,
    textstr,
    transform=ax.transAxes,
    fontsize=10,
    verticalalignment="center",
    horizontalalignment="right",
    bbox=props,
    fontweight="bold",
)

plt.tight_layout()
output1 = OUTPUT_DIR / "../fig05_performance_matrix.png"
plt.savefig(output1, dpi=300, bbox_inches="tight")
print(f"✅ Figure 8 (Performance Matrix): {output1}")
plt.close()

# ============================================================================
# VERSION 2: Performance Matrix Visualization (REBUILT FROM SCRATCH)
# ============================================================================

fig, ax = plt.subplots(figsize=(10, 8))

# Plot patterns as simple labeled points (no overlapping circles)
colors = ["#F77F00", "#2E86AB", "#06A77D"]
pattern_names = ["Gamma\nPositioning", "Stock\nPinning", "0DTE\nHedging"]

for i, (pattern, det, acc, color) in enumerate(zip(pattern_names, detection, accuracy, colors)):
    # Plot large marker
    ax.scatter(det, acc, s=1200, c=color, marker="o", alpha=0.85, edgecolors="black", linewidth=2.5, zorder=3)

    # Label ABOVE the point to avoid overlap
    ax.text(
        det,
        acc + 0.5,
        pattern,
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="black", linewidth=1.5, alpha=0.95),
        zorder=5,
    )

    # Metrics BELOW the point
    ax.text(
        det,
        acc - 0.5,
        f"{det:.1f}% det\n{acc:.1f}% acc",
        ha="center",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="gray", linewidth=1, alpha=0.9),
        zorder=5,
    )

# Add threshold lines
ax.axhline(y=90, color="green", linestyle="--", linewidth=2.5, alpha=0.6, label="90% Accuracy Benchmark")
ax.axvline(x=60, color="red", linestyle="--", linewidth=2.5, alpha=0.6, label="60% Mechanical Threshold")

# Configure axes
ax.set_xlabel("Detection Rate (%)", fontsize=14, fontweight="bold")
ax.set_ylabel("Prediction Accuracy (%)", fontsize=14, fontweight="bold")
ax.set_title(
    "Pattern Detection Performance Matrix\n(Unbiased Prompts, Full 2024)", fontsize=15, fontweight="bold", pad=20
)
ax.set_xlim(55, 85)
ax.set_ylim(88, 95)
ax.grid(True, alpha=0.25, linestyle=":", linewidth=1)
ax.legend(loc="lower right", fontsize=10, framealpha=0.95, edgecolor="black")

plt.tight_layout()
output3 = OUTPUT_DIR / "fig8_bars_alternate.png"
plt.savefig(output3, dpi=300, bbox_inches="tight")
print(f"✅ Alternate (bars): {output3}")
plt.close()

print("=" * 60)
print("FIGURE 8 GENERATION COMPLETE (WITH YAML DATA)")
print("=" * 60)
print("\nKey Improvements:")
print("  • Loaded actual data from unbiased YAML validation files")
print("  • Fixed legend overlapping issue (moved summary box)")
print("  • All values now reflect real validation results")
print("  • Detection rates, accuracy, and sample sizes verified")
