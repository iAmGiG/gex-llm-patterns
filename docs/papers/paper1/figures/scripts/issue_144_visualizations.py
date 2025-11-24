#!/usr/bin/env python3
"""
Issue #144: P-Hacking Defense Visualizations
Paper #1 Journal Version - Materialization Specificity Proof

Generates 3 key figures for journal paper:
1. Materialization rates comparison (detection vs baseline)
2. Pattern-specific lift analysis (bar chart)
3. Chi-square contingency tables (heatmap)

Author: Research Team (Chat C)
Date: 2025-11-22
GitHub Issue: https://github.com/iAmGiG/gex-llm-patterns/issues/144
"""

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # Non-interactive backend for HPCC
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import yaml
from matplotlib.gridspec import GridSpec

# Add project root to path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set publication-quality parameters
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["font.size"] = 10
plt.rcParams["font.family"] = "serif"
plt.rcParams["axes.linewidth"] = 1.0
plt.rcParams["xtick.major.width"] = 1.0
plt.rcParams["ytick.major.width"] = 1.0


def load_phase2_results():
    """Load Phase 2 YAML results."""
    yaml_path = project_root / "docs" / "papers" / "paper1" / "analysis" / "issue_144_phase2_summary.yaml"

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    print(f"Loaded Phase 2 results from: {yaml_path}")
    return data


def create_materialization_comparison(data, output_path):
    """
    Figure 1: Materialization rates comparison (detection vs baseline).

    Bar chart showing C1 and C4 rates for detection vs baseline.
    """
    print("\nCreating Figure 1: Materialization rates comparison...")

    fig, ax = plt.subplots(figsize=(10, 6))

    # Extract data
    det_c1 = data["detection"]["overall"]["c1_rate"]
    det_c4 = data["detection"]["overall"]["c4_rate"]
    base_c1 = data["baseline"]["overall"]["c1_rate"]
    base_c4 = data["baseline"]["overall"]["c4_rate"]

    # Bar positions
    x = np.arange(2)
    width = 0.35

    # Create bars
    det_bars = ax.bar(
        x - width / 2,
        [det_c1, det_c4],
        width,
        label="Detection Days (n=519)",
        color="#2ecc71",
        alpha=0.8,
        edgecolor="black",
        linewidth=1.0,
    )
    base_bars = ax.bar(
        x + width / 2,
        [base_c1, base_c4],
        width,
        label="Baseline (Non-Detection, n=100)",
        color="#e74c3c",
        alpha=0.8,
        edgecolor="black",
        linewidth=1.0,
    )

    # Add value labels on bars
    for bars in [det_bars, base_bars]:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 1,
                f"{height:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    # Add significance markers
    # C4 is significant (p=0.033)
    ax.text(1, max(det_c4, base_c4) + 5, "*", ha="center", fontsize=20, fontweight="bold")
    ax.text(1, max(det_c4, base_c4) + 8, "p=0.033", ha="center", fontsize=8)

    # Labels and formatting
    ax.set_ylabel("Materialization Rate (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Issue #144: Detection vs Baseline Materialization Rates\n(Inverse Relationship Refutes P-Hacking)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(["C1: Volatility\nAmplification", "C4: Range\nExpansion"], fontsize=11)
    ax.legend(loc="upper right", fontsize=10, frameon=True)
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")
    ax.set_ylim(0, max(det_c1, det_c4, base_c1, base_c4) + 15)

    # Add interpretation text
    ax.text(
        0.5,
        -0.18,
        "Key Finding: Detection days show LOWER materialization for C4 (21.6% vs 32.0%)\n"
        + "→ Proves LLM detects dampening mechanisms, not universal volatility spikes",
        transform=ax.transAxes,
        fontsize=9,
        ha="center",
        style="italic",
        bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.3),
    )

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"  Saved: {output_path}")
    plt.close()


def create_pattern_lift_analysis(data, output_path):
    """
    Figure 2: Pattern-specific lift analysis.

    Bar chart showing lift for each pattern × criterion combination.
    """
    print("\nCreating Figure 2: Pattern-specific lift analysis...")

    fig, ax = plt.subplots(figsize=(12, 7))

    # Extract pattern-specific lifts
    patterns = ["gamma_positioning", "stock_pinning", "0dte_hedging"]
    pattern_labels = ["Gamma\nPositioning", "Stock\nPinning", "0DTE\nHedging"]

    c1_lifts = [data["lift"][p]["c1_lift"] for p in patterns]
    c4_lifts = [data["lift"][p]["c4_lift"] for p in patterns]

    # Bar positions
    x = np.arange(len(patterns))
    width = 0.35

    # Create bars
    c1_bars = ax.bar(
        x - width / 2,
        c1_lifts,
        width,
        label="C1: Volatility Amplification",
        color="#3498db",
        alpha=0.8,
        edgecolor="black",
        linewidth=1.0,
    )
    c4_bars = ax.bar(
        x + width / 2,
        c4_lifts,
        width,
        label="C4: Range Expansion",
        color="#9b59b6",
        alpha=0.8,
        edgecolor="black",
        linewidth=1.0,
    )

    # Add value labels on bars
    for bars in [c1_bars, c4_bars]:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.05,
                f"{height:.2f}x",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    # Add reference line at 1.0 (no lift)
    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1.5, alpha=0.7, label="No Lift (1.0x)")

    # Labels and formatting
    ax.set_ylabel("Lift (Detection / Baseline)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Issue #144: Pattern-Specific Lift Analysis\n(Differential Behavior Proves Selectivity)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(pattern_labels, fontsize=11)
    ax.legend(loc="upper right", fontsize=10, frameon=True)
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")
    ax.set_ylim(0, max(c1_lifts + c4_lifts) + 0.3)

    # Add interpretation text
    ax.text(
        0.5,
        -0.18,
        "Key Finding: Patterns show OPPOSITE lift directions (gamma >1.0x, pinning/hedging <1.0x)\n"
        + "→ Proves LLM assesses pattern-specific constraints, not base rates",
        transform=ax.transAxes,
        fontsize=9,
        ha="center",
        style="italic",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.3),
    )

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"  Saved: {output_path}")
    plt.close()


def create_contingency_heatmap(data, output_path):
    """
    Figure 3: Chi-square contingency tables (heatmap).

    2x2 grid showing contingency tables for C1 and C4.
    """
    print("\nCreating Figure 3: Chi-square contingency tables...")

    fig = plt.figure(figsize=(14, 6))
    gs = GridSpec(1, 2, figure=fig, wspace=0.3)

    # C1 Contingency Table
    ax1 = fig.add_subplot(gs[0, 0])
    c1_table = np.array(data["chi_square"]["c1"]["table"])
    c1_p = data["chi_square"]["c1"]["p_value"]

    im1 = ax1.imshow(c1_table, cmap="Blues", aspect="auto")

    # Add text annotations
    for i in range(2):
        for j in range(2):
            text = ax1.text(
                j, i, c1_table[i, j], ha="center", va="center", color="black", fontsize=16, fontweight="bold"
            )

    ax1.set_xticks([0, 1])
    ax1.set_yticks([0, 1])
    ax1.set_xticklabels(["Materialized", "Not Materialized"], fontsize=11)
    ax1.set_yticklabels(["Detection\n(n=519)", "Baseline\n(n=100)"], fontsize=11)
    ax1.set_title(f"C1: Volatility Amplification\nχ²=0.267, p={c1_p:.3f} (ns)", fontsize=12, fontweight="bold", pad=10)

    # Add colorbar
    cbar1 = plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    cbar1.set_label("Count", fontsize=10)

    # C4 Contingency Table
    ax2 = fig.add_subplot(gs[0, 1])
    c4_table = np.array(data["chi_square"]["c4"]["table"])
    c4_p = data["chi_square"]["c4"]["p_value"]

    im2 = ax2.imshow(c4_table, cmap="Reds", aspect="auto")

    # Add text annotations
    for i in range(2):
        for j in range(2):
            text = ax2.text(
                j, i, c4_table[i, j], ha="center", va="center", color="black", fontsize=16, fontweight="bold"
            )

    ax2.set_xticks([0, 1])
    ax2.set_yticks([0, 1])
    ax2.set_xticklabels(["Materialized", "Not Materialized"], fontsize=11)
    ax2.set_yticklabels(["Detection\n(n=519)", "Baseline\n(n=100)"], fontsize=11)
    ax2.set_title(f"C4: Range Expansion\nχ²=4.533, p={c4_p:.3f} *", fontsize=12, fontweight="bold", pad=10)

    # Add colorbar
    cbar2 = plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    cbar2.set_label("Count", fontsize=10)

    # Add main title
    fig.suptitle(
        "Issue #144: Chi-Square Contingency Tables\n(C4 Shows Significant Inverse Relationship)",
        fontsize=14,
        fontweight="bold",
        y=1.00,
    )

    # Add interpretation text
    fig.text(
        0.5,
        -0.05,
        "Key Finding: C4 shows significant inverse relationship (detection < baseline, p=0.033)\n"
        + "→ Detection days have LOWER range expansion than random days (dampening mechanisms)",
        fontsize=9,
        ha="center",
        style="italic",
        bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.4),
    )

    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"  Saved: {output_path}")
    plt.close()


def main():
    """Generate all visualizations for Issue #144."""

    print("=" * 80)
    print("Issue #144: Visualization Generation")
    print("Paper #1 Journal Version - P-Hacking Defense")
    print("=" * 80)
    print()

    # Paths
    output_dir = project_root / "docs" / "papers" / "paper1" / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load Phase 2 results
    print("Loading Phase 2 results...")
    data = load_phase2_results()

    # Generate figures
    print("\nGenerating visualizations...")

    # Figure 1: Materialization rates comparison
    fig1_path = output_dir / "issue_144_materialization_comparison.png"
    create_materialization_comparison(data, fig1_path)

    # Figure 2: Pattern-specific lift analysis
    fig2_path = output_dir / "issue_144_pattern_lift_analysis.png"
    create_pattern_lift_analysis(data, fig2_path)

    # Figure 3: Chi-square contingency tables
    fig3_path = output_dir / "issue_144_contingency_tables.png"
    create_contingency_heatmap(data, fig3_path)

    print()
    print("=" * 80)
    print("VISUALIZATION GENERATION COMPLETE")
    print("=" * 80)
    print()
    print("Figures created:")
    print(f"  1. {fig1_path}")
    print(f"  2. {fig2_path}")
    print(f"  3. {fig3_path}")
    print()
    print("Next steps:")
    print("  1. Review figures for publication quality")
    print("  2. Update journal paper LaTeX with figures")
    print("  3. Reference in Results section")
    print()


if __name__ == "__main__":
    main()
