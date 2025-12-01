#!/usr/bin/env python3
"""
Figure 6: Validation Funnel (YAML DATA VERSION)

Shows the progression from total trading days through detection to materialization.
Loads actual validation results from YAML files instead of hardcoded values.

This illustrates the validation methodology and success rates at each stage.

Data sources:
- gamma_positioning_SPY_2024_unbiased.yaml
- stock_pinning_SPY_2024_unbiased.yaml
- 0dte_hedging_SPY_2024_unbiased.yaml
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.patches import FancyBboxPatch

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

print("=" * 60)
print("FIGURE 6: VALIDATION FUNNEL (YAML DATA)")
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
        # Only count high-confidence (>60%) as detected
        "detections": perf["high_confidence_detections"],
    }


# Load data from YAML files
patterns_full = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
patterns_data = {p: load_pattern_data(p) for p in patterns_full}

# Pattern labels for display
pattern_labels = ["Gamma\nPositioning", "Stock\nPinning", "0DTE\nHedging", "Overall\nAverage"]

# Extract per-pattern metrics
detection_rates = [patterns_data[p]["detection_rate"] for p in patterns_full]
accuracies = [patterns_data[p]["accuracy"] for p in patterns_full]
detections_list = [patterns_data[p]["detections"] for p in patterns_full]

# Calculate aggregate metrics
total_days = patterns_data[patterns_full[0]]["sample_size"]
total_tests = total_days * 3  # 3 patterns
total_detected = sum(detections_list)
avg_detection_rate = np.mean(detection_rates)
avg_accuracy = np.mean(accuracies)

# Calculate materialized predictions (detected × accuracy)
materialized_per_pattern = [int(detections_list[i] * (accuracies[i] / 100)) for i in range(len(patterns_full))]
total_materialized = sum(materialized_per_pattern)

# Calculate percentages
detection_pct = (total_detected / total_tests) * 100
materialization_pct = (total_materialized / total_detected) * 100 if total_detected > 0 else 0
overall_success_pct = (total_materialized / total_tests) * 100

# Calculate success rates per pattern (detection × accuracy)
success_rates = [(d / 100) * (a / 100) * 100 for d, a in zip(detection_rates, accuracies)]

print(f"\nLoaded data from YAML files:")
print(f"  Total days per pattern: {total_days}")
print(f"  Total tests: {total_tests}")
print(f"  Total detected: {total_detected} ({detection_pct:.1f}%)")
print(f"  Total materialized: {total_materialized} ({materialization_pct:.1f}% of detected)")
print(f"  Overall success: {overall_success_pct:.1f}%")

print(f"\nPer-pattern breakdown:")
for i, p in enumerate(patterns_full):
    print(f"  {p}: {detection_rates[i]:.1f}% detection, {accuracies[i]:.1f}% accuracy, {success_rates[i]:.1f}% success")

# ============================================================================
# VERSION 1: Traditional Funnel Diagram (IEEE SINGLE-COLUMN SIZE)
# ============================================================================

fig, ax = plt.subplots(figsize=(3, 2.75))  # IEEE single-column width

# Funnel data
stages = ["Total Pattern Tests", "LLM Detection", "Predicted Patterns\nMaterialized"]
values = [total_tests, total_detected, total_materialized]
colors = ["#2E86AB", "#F77F00", "#06A77D"]

# Calculate funnel widths (normalized to max width)
max_width = 3  # Narrower for single-column
widths = [(v / total_tests) * max_width for v in values]

# Y positions for each stage (compact)
y_positions = [2.3, 1.6, 0.9]
height = 0.4

# Draw funnel stages as rectangles
for i, (stage, value, width, y_pos, color) in enumerate(zip(stages, values, widths, y_positions, colors)):
    # Draw rectangle
    rect = FancyBboxPatch(
        (-width / 2, y_pos - height / 2),
        width,
        height,
        boxstyle="round,pad=0.05",
        facecolor=color,
        edgecolor="black",
        linewidth=2,
        alpha=0.8,
    )
    ax.add_patch(rect)

    # Add stage label and value (smaller font for single-column)
    ax.text(0, y_pos, f"{stage}\n{value:,}", ha="center", va="center", fontsize=8, fontweight="bold", color="white")

    # Add percentage annotation to the right (smaller)
    if i == 1:  # Detection stage
        pct_text = f"{detection_pct:.1f}%"
        ax.text(
            width / 2 + 0.25,
            y_pos,
            pct_text,
            ha="left",
            va="center",
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="yellow", alpha=0.8, edgecolor="gray"),
        )
    elif i == 2:  # Materialization stage
        pct_text = f"{materialization_pct:.1f}%"
        ax.text(
            width / 2 + 0.25,
            y_pos,
            pct_text,
            ha="left",
            va="center",
            fontsize=7,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="lightgreen", alpha=0.8, edgecolor="gray"),
        )

# Draw connecting arrows
for i in range(len(y_positions) - 1):
    y_from = y_positions[i] - height / 2
    y_to = y_positions[i + 1] + height / 2
    ax.annotate("", xy=(0, y_to), xytext=(0, y_from), arrowprops=dict(arrowstyle="->", lw=3, color="gray", alpha=0.6))

# Add overall success rate at bottom (very compact)
success_text = f"{overall_success_pct:.1f}% Success\n({total_materialized}/{total_tests})"
ax.text(
    0,
    0.2,
    success_text,
    ha="center",
    va="center",
    fontsize=8,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="lightblue", alpha=0.9, edgecolor="black"),
)

# Configure axes (tight for single-column)
ax.set_xlim(-2, 2)  # Narrow for single-column
ax.set_ylim(0.01, 2.7)
ax.axis("off")

# Title (compact for single-column)
ax.set_title("Validation Funnel\n(Unbiased, 2024)", fontsize=10, fontweight="bold", pad=8)

plt.tight_layout()
output1 = OUTPUT_DIR / "../fig09_validation_funnel.png"
plt.savefig(output1, dpi=300, bbox_inches="tight")
print(f"✅ Figure 6 (Validation Funnel): {output1}")
plt.close()

# ============================================================================

# Alternate versions disabled (not needed for paper)
# VERSION 2 and VERSION 3 code removed to prevent generation of alternate figures

print("=" * 60)
print("FIGURE 6 GENERATION COMPLETE (WITH YAML DATA)")
print("=" * 60)
print("\nKey Improvements:")
print("  • Loaded actual data from unbiased YAML validation files")
print("  • Calculated aggregate statistics from 3 patterns")
print("  • All values now reflect real validation results")
print(f"  • {total_tests} total tests → {total_detected} detected → {total_materialized} materialized")
print(f"  • Overall success rate: {overall_success_pct:.1f}%")
