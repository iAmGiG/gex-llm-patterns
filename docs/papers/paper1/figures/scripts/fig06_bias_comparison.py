#!/usr/bin/env python3
"""
Figure 4: Detection Rate Comparison - Biased vs Unbiased (YAML DATA VERSION)

Loads actual validation results from YAML files instead of hardcoded values.
Compares biased prompts (Q2 2024, 100% detection) vs unbiased prompts (full 2024).

Data sources:
Biased (Q3+Q4 2024 average - both used biased prompts):
- gamma_positioning_SPY_2024Q3.yaml & 2024Q4.yaml
- stock_pinning_SPY_2024Q3.yaml & 2024Q4.yaml
- 0dte_hedging_SPY_2024Q3.yaml & 2024Q4.yaml
Note: Q2 data incomplete for stock_pinning and 0dte_hedging (failed fetches)

Unbiased (Full 2024):
- gamma_positioning_SPY_2024_unbiased.yaml
- stock_pinning_SPY_2024_unbiased.yaml
- 0dte_hedging_SPY_2024_unbiased.yaml
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
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

print("=" * 60)
print("FIGURE 7: BIASED VS UNBIASED COMPARISON (YAML DATA)")
print("=" * 60)


def load_pattern_data(pattern_name, suffix):
    """Load validation metrics from YAML file."""
    filepath = REPORTS_DIR / f"{pattern_name}_SPY_{suffix}.yaml"

    if not filepath.exists():
        print(f"ERROR: {filepath} not found")
        return None

    with open(filepath, "r") as f:
        data = yaml.safe_load(f)

    perf = data["performance_metrics"]
    if perf["total_tested"] == 0:
        print(f"WARNING: {filepath} has no test data (failed fetches)")
        return None

    return {
        "detection_rate": perf["detection_rate_pct"],
        "accuracy": perf["predictive_accuracy_pct"],
        "sample_size": perf["total_tested"],
    }


def load_biased_avg(pattern_name):
    """Load and average Q3 & Q4 data for biased comparison (both are biased prompts)."""
    q3_data = load_pattern_data(pattern_name, "2024Q3")
    q4_data = load_pattern_data(pattern_name, "2024Q4")

    if not q3_data or not q4_data:
        print(f"ERROR: Missing Q3 or Q4 data for {pattern_name}")
        return None

    # Average the two quarters
    return {
        "detection_rate": (q3_data["detection_rate"] + q4_data["detection_rate"]) / 2,
        "accuracy": (q3_data["accuracy"] + q4_data["accuracy"]) / 2,
        "sample_size": q3_data["sample_size"] + q4_data["sample_size"],
    }


# Load data from YAML files
patterns = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
pattern_labels = ["Gamma\nPositioning", "Stock\nPinning", "0DTE\nHedging"]

# Biased = average of Q3 & Q4 (both biased prompts with full data)
biased_data = {p: load_biased_avg(p) for p in patterns}
unbiased_data = {p: load_pattern_data(p, "2024_unbiased") for p in patterns}

# Extract metrics
biased_detection = [biased_data[p]["detection_rate"] for p in patterns]
unbiased_detection = [unbiased_data[p]["detection_rate"] for p in patterns]
biased_accuracy = [biased_data[p]["accuracy"] for p in patterns]
unbiased_accuracy = [unbiased_data[p]["accuracy"] for p in patterns]

# Calculate 95% CI for unbiased (using Wilson score interval approximation)
n_unbiased = unbiased_data[patterns[0]]["sample_size"]
ci_lower = []
ci_upper = []
for rate in unbiased_detection:
    p = rate / 100
    z = 1.96  # 95% CI
    margin = z * np.sqrt(p * (1 - p) / n_unbiased) * 100
    ci_lower.append(max(0, rate - margin))
    ci_upper.append(min(100, rate + margin))

ci_error_lower = [unbiased_detection[i] - ci_lower[i] for i in range(len(patterns))]
ci_error_upper = [ci_upper[i] - unbiased_detection[i] for i in range(len(patterns))]

print(f"\nLoaded biased data (Q3+Q4 2024 avg, N={biased_data[patterns[0]]['sample_size']}):")
for i, p in enumerate(patterns):
    print(f"  {p}: {biased_detection[i]:.1f}% detection, {biased_accuracy[i]:.1f}% accuracy")

print(f"\nLoaded unbiased data (Full 2024, N={n_unbiased}):")
for i, p in enumerate(patterns):
    print(f"  {p}: {unbiased_detection[i]:.1f}% detection, {unbiased_accuracy[i]:.1f}% accuracy")

# ============================================================================
# VERSION 1: Clean Detection Comparison (REBUILT FROM SCRATCH)
# ============================================================================

fig, ax = plt.subplots(figsize=(12, 7))

x = np.arange(len(pattern_labels))
width = 0.35

# Plot bars
bars1 = ax.bar(
    x - width / 2,
    biased_detection,
    width,
    label="Biased Prompts (with regime hints)",
    color="#2E86AB",
    alpha=0.9,
    edgecolor="black",
    linewidth=1.5,
)
bars2 = ax.bar(
    x + width / 2,
    unbiased_detection,
    width,
    label="Unbiased Prompts (raw GEX only)",
    color="#F77F00",
    alpha=0.9,
    edgecolor="black",
    linewidth=1.5,
)

# Add 60% threshold line
ax.axhline(y=60, color="red", linestyle="--", linewidth=2.5, alpha=0.7, zorder=0)

# Configure axes
ax.set_xlabel("Pattern Type", fontsize=14, fontweight="bold")
ax.set_ylabel("Detection Rate (%)", fontsize=14, fontweight="bold")
ax.set_title("Impact of Prompt Bias on Detection Rates", fontsize=16, fontweight="bold", pad=20)
ax.set_xticks(x)
ax.set_xticklabels(pattern_labels, fontsize=13)
ax.set_ylim(0, 115)
ax.grid(axis="y", alpha=0.3, linestyle=":", linewidth=1)

# Legend with threshold explanation and sample sizes
legend_elements = [
    plt.Rectangle(
        (0, 0),
        1,
        1,
        facecolor="#2E86AB",
        edgecolor="black",
        alpha=0.9,
        linewidth=1.5,
        label=f'Biased Prompts (Q3+Q4, N={biased_data[patterns[0]]["sample_size"]})',
    ),
    plt.Rectangle(
        (0, 0),
        1,
        1,
        facecolor="#F77F00",
        edgecolor="black",
        alpha=0.9,
        linewidth=1.5,
        label=f"Unbiased Prompts (Full 2024, N={n_unbiased})",
    ),
    Line2D([0], [0], color="red", linestyle="--", linewidth=2.5, alpha=0.7, label="60% Mechanical Threshold"),
]
ax.legend(handles=legend_elements, loc="lower right", fontsize=10, framealpha=0.95, edgecolor="black")

# Add value labels on bars
for bar1, bar2 in zip(bars1, bars2):
    height1 = bar1.get_height()
    height2 = bar2.get_height()
    ax.text(
        bar1.get_x() + bar1.get_width() / 2.0,
        height1 + 1.5,
        f"{height1:.0f}%",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )
    ax.text(
        bar2.get_x() + bar2.get_width() / 2.0,
        height2 + 1.5,
        f"{height2:.1f}%",
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )

# Add delta annotations (cleaner, smaller)
for i in range(len(pattern_labels)):
    delta = unbiased_detection[i] - biased_detection[i]
    y_pos = max(biased_detection[i], unbiased_detection[i]) + 10
    ax.text(
        x[i],
        y_pos,
        f"Δ={delta:.1f}%",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        style="italic",
        color="darkred",
    )

plt.tight_layout()
output1 = OUTPUT_DIR / "../fig06_bias_comparison.png"
plt.savefig(output1, dpi=300, bbox_inches="tight")
print(f"✅ Figure 4 (Detection Comparison): {output1}")
plt.close()

# ============================================================================
# VERSION 2: Minimal Version (Publication Ready)
# ============================================================================

fig, ax = plt.subplots(figsize=(8, 5))

x = np.arange(len(pattern_labels))
width = 0.35

# Plot bars
bars1 = ax.bar(
    x - width / 2, biased_detection, width, label="Biased", color="#4A90E2", alpha=0.95, edgecolor="black", linewidth=1
)
bars2 = ax.bar(
    x + width / 2,
    unbiased_detection,
    width,
    label="Unbiased",
    color="#E67E22",
    alpha=0.95,
    edgecolor="black",
    linewidth=1,
)

# Threshold line
ax.axhline(y=60, color="#E74C3C", linestyle="--", linewidth=2, alpha=0.8)

# Labels and formatting
ax.set_xlabel("Pattern", fontsize=11, fontweight="bold")
ax.set_ylabel("Detection Rate (%)", fontsize=11, fontweight="bold")
ax.set_title("Prompt Bias Impact on Detection Rates", fontsize=12, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(pattern_labels, fontsize=10)
ax.set_ylim(0, 110)
ax.legend(fontsize=10, framealpha=0.9, loc="lower right")
ax.grid(axis="y", alpha=0.25, linestyle=":", linewidth=0.8)

# Minimal value labels (only unbiased)
for bar in bars2:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2.0,
        height + 3,
        f"{height:.1f}%",
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
    )

plt.tight_layout()
output3 = OUTPUT_DIR / "fig4_minimal_alternate.png"
plt.savefig(output3, dpi=300, bbox_inches="tight")
print(f"✅ Alternate (minimal): {output3}")
plt.close()

print("=" * 60)
print("FIGURE 4 GENERATION COMPLETE (WITH YAML DATA)")
print("=" * 60)
print("\nKey Improvements:")
print("  • Loaded actual data from biased (Q2) and unbiased (full 2024) YAML files")
print("  • Fixed delta label positioning (above bars, not overlapping error bars)")
print("  • Reduced summary box size to minimize chart clutter")
print("  • All values now reflect real validation results")
