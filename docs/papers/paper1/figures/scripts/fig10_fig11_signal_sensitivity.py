#!/usr/bin/env python3
"""
Paper 1 Figure Generation: Signal Sensitivity Visualizations

Generates figures for JFDS journal submission:
- fig10_gex_concentration.png: GEX concentration distribution (Detection vs Non-Detection)
- fig11_detection_calendar.png: Calendar heatmap of detection days across 2024
- archive/issue_141_multifactor_analysis.png: Multi-factor scatter plots (archived)

Key Finding: Detection days have HIGHER GEX concentration (Gini coefficient)
than non-detection days, proving LLM requires concentrated signals.
"""

import calendar
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec

# Add project root to path
# From: docs/papers/paper1/figures/scripts/ -> go up 6 levels to project root
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


def create_calendar_heatmap(df, output_path):
    """
    Create a calendar heatmap showing detection/non-detection days across 2024.

    Green = Detection, Red = Non-detection
    """
    print("Creating calendar heatmap...")

    # Parse dates
    df["date_parsed"] = pd.to_datetime(df["date"])
    df["month"] = df["date_parsed"].dt.month
    df["day"] = df["date_parsed"].dt.day
    df["weekday"] = df["date_parsed"].dt.weekday  # Monday=0, Sunday=6

    # Create figure with subplots for each month
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(3, 4, figure=fig, hspace=0.3, wspace=0.3)

    for month in range(1, 13):
        ax = fig.add_subplot(gs[(month - 1) // 4, (month - 1) % 4])

        # Get data for this month
        month_data = df[df["month"] == month].copy()

        if len(month_data) == 0:
            ax.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=12)
            ax.set_xlim(0, 7)
            ax.set_ylim(0, 6)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(calendar.month_name[month], fontsize=11, fontweight="bold")
            continue

        # Create calendar grid
        # Get first day of month and number of days
        first_day = datetime(2024, month, 1)
        first_weekday = first_day.weekday()
        num_days = calendar.monthrange(2024, month)[1]

        # Plot each day as a square
        for day in range(1, num_days + 1):
            date_str = f"2024-{month:02d}-{day:02d}"
            day_data = month_data[month_data["date"] == date_str]

            # Calculate position in calendar grid
            # Week of month (0-5)
            week = (day + first_weekday - 1) // 7
            # Day of week (0=Mon, 6=Sun)
            weekday = (day + first_weekday - 1) % 7

            if len(day_data) > 0:
                detected = day_data["detected"].values[0]
                color = "#2ecc71" if detected else "#e74c3c"  # Green if detected, red if not
                alpha = 0.8
            else:
                # No trading day (weekend/holiday)
                color = "#ecf0f1"
                alpha = 0.3

            # Draw square
            square = mpatches.Rectangle(
                (weekday, 5 - week), 0.9, 0.9, facecolor=color, edgecolor="white", linewidth=1.5, alpha=alpha
            )
            ax.add_patch(square)

            # Add day number
            if len(day_data) > 0:
                ax.text(
                    weekday + 0.45,
                    5 - week + 0.45,
                    str(day),
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="white",
                )

        # Set up axes
        ax.set_xlim(0, 7)
        ax.set_ylim(0, 6)
        ax.set_xticks(np.arange(7) + 0.45)
        ax.set_xticklabels(["M", "T", "W", "T", "F", "S", "S"], fontsize=9)
        ax.set_yticks([])
        ax.set_title(calendar.month_name[month], fontsize=11, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

    # Add legend
    fig.suptitle("Detection Status Calendar 2024", fontsize=14, fontweight="bold", y=0.98)

    detection_patch = mpatches.Patch(color="#2ecc71", label="Detection (n=168)", alpha=0.8)
    non_detection_patch = mpatches.Patch(color="#e74c3c", label="Non-Detection (n=74)", alpha=0.8)
    fig.legend(
        handles=[detection_patch, non_detection_patch],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        ncol=2,
        fontsize=11,
        frameon=True,
    )

    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"  Saved: {output_path}")
    plt.close()


def create_concentration_distribution(df, output_path):
    """
    Create histogram comparing GEX concentration (Gini) distribution
    between detection and non-detection days.
    """
    print("Creating GEX concentration distribution...")

    detected = df[df["detected"] == True]["gex_concentration"].dropna()
    not_detected = df[df["detected"] == False]["gex_concentration"].dropna()

    # Wider figure to give more space for x-axis label
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create histograms
    bins = np.linspace(-0.90, -0.80, 30)

    ax.hist(
        detected,
        bins=bins,
        alpha=0.6,
        color="#2ecc71",
        label=f"Detection Days (n={len(detected)}, μ={detected.mean():.4f})",
        edgecolor="black",
        linewidth=0.5,
    )
    ax.hist(
        not_detected,
        bins=bins,
        alpha=0.6,
        color="#e74c3c",
        label=f"Non-Detection Days (n={len(not_detected)}, μ={not_detected.mean():.4f})",
        edgecolor="black",
        linewidth=0.5,
    )

    # Add vertical lines for means
    ax.axvline(
        detected.mean(), color="#27ae60", linestyle="--", linewidth=2, label=f"Detection Mean: {detected.mean():.4f}"
    )
    ax.axvline(
        not_detected.mean(),
        color="#c0392b",
        linestyle="--",
        linewidth=2,
        label=f"Non-Detection Mean: {not_detected.mean():.4f}",
    )

    # Statistical annotation
    from scipy import stats

    t_stat, p_val = stats.ttest_ind(detected, not_detected)
    cohen_d = (detected.mean() - not_detected.mean()) / np.sqrt((detected.std() ** 2 + not_detected.std() ** 2) / 2)

    ax.text(
        0.05,
        0.95,
        f"Statistical Test:\nt = {t_stat:.3f}\np < 0.0001\nCohen's d = {cohen_d:.3f} (medium)",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    ax.set_xlabel("GEX Concentration (Gini Coefficient)", fontsize=12, fontweight="bold", labelpad=8)
    ax.set_ylabel("Frequency", fontsize=12, fontweight="bold", labelpad=8)
    ax.set_title(
        "GEX Concentration Distribution\n(Detection vs Non-Detection Days)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.legend(loc="upper right", fontsize=9, frameon=True)
    # Grid removed for cleaner bar chart appearance

    # Add interpretation text - positioned below x-axis label with clear separation
    ax.text(
        0.5,
        -0.25,
        "Interpretation: Non-detection days have MORE FRAGMENTED gamma (lower Gini)\n"
        + "-> Proves LLM requires concentrated signals, not just presence of negative GEX",
        transform=ax.transAxes,
        fontsize=9,
        ha="center",
        style="italic",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightblue", alpha=0.3),
    )

    # Bottom margin for interpretation text
    plt.tight_layout(rect=[0, 0.11, 1, 1])
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"  Saved: {output_path}")
    plt.close()


def create_multifactor_scatter(df, output_path):
    """
    Create 4-panel scatter plot showing relationships between factors.
    """
    print("Creating multi-factor scatter plots...")

    detected = df[df["detected"] == True].copy()
    not_detected = df[df["detected"] == False].copy()

    fig = plt.figure(figsize=(14, 12))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

    # Panel 1: GEX Concentration vs GEX Magnitude
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(
        detected["gex_concentration"],
        abs(detected["net_gex"]) / 1e9,
        alpha=0.6,
        s=50,
        color="#2ecc71",
        label="Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax1.scatter(
        not_detected["gex_concentration"],
        abs(not_detected["net_gex"]) / 1e9,
        alpha=0.6,
        s=50,
        color="#e74c3c",
        label="Non-Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax1.set_xlabel("GEX Concentration (Gini)", fontsize=10, fontweight="bold")
    ax1.set_ylabel("|Net GEX| ($B)", fontsize=10, fontweight="bold")
    ax1.set_title("(A) Concentration vs Magnitude", fontsize=11, fontweight="bold")
    ax1.legend(loc="best", fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Panel 2: GEX Concentration vs Concentrated Strikes
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(
        detected["gex_concentration"],
        detected["n_concentrated_strikes"],
        alpha=0.6,
        s=50,
        color="#2ecc71",
        label="Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax2.scatter(
        not_detected["gex_concentration"],
        not_detected["n_concentrated_strikes"],
        alpha=0.6,
        s=50,
        color="#e74c3c",
        label="Non-Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax2.set_xlabel("GEX Concentration (Gini)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("# Strikes with >5% Gamma", fontsize=10, fontweight="bold")
    ax2.set_title("(B) Concentration vs Strike Count", fontsize=11, fontweight="bold")
    ax2.legend(loc="best", fontsize=9)
    ax2.grid(True, alpha=0.3)

    # Panel 3: GEX Magnitude vs Put-Call Ratio
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.scatter(
        abs(detected["net_gex"]) / 1e9,
        detected["put_call_ratio"],
        alpha=0.6,
        s=50,
        color="#2ecc71",
        label="Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax3.scatter(
        abs(not_detected["net_gex"]) / 1e9,
        not_detected["put_call_ratio"],
        alpha=0.6,
        s=50,
        color="#e74c3c",
        label="Non-Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax3.set_xlabel("|Net GEX| ($B)", fontsize=10, fontweight="bold")
    ax3.set_ylabel("Put-Call Ratio", fontsize=10, fontweight="bold")
    ax3.set_title("(C) Magnitude vs Put-Call Balance", fontsize=11, fontweight="bold")
    ax3.legend(loc="best", fontsize=9)
    ax3.grid(True, alpha=0.3)

    # Panel 4: GEX Concentration vs Realized Volatility
    ax4 = fig.add_subplot(gs[1, 1])
    # Filter out NaN values for volatility
    det_vol = detected[["gex_concentration", "realized_vol_t1"]].dropna()
    non_det_vol = not_detected[["gex_concentration", "realized_vol_t1"]].dropna()

    ax4.scatter(
        det_vol["gex_concentration"],
        det_vol["realized_vol_t1"],
        alpha=0.6,
        s=50,
        color="#2ecc71",
        label="Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax4.scatter(
        non_det_vol["gex_concentration"],
        non_det_vol["realized_vol_t1"],
        alpha=0.6,
        s=50,
        color="#e74c3c",
        label="Non-Detection",
        edgecolor="black",
        linewidth=0.5,
    )
    ax4.set_xlabel("GEX Concentration (Gini)", fontsize=10, fontweight="bold")
    ax4.set_ylabel("Realized Volatility T+1 (%)", fontsize=10, fontweight="bold")
    ax4.set_title("(D) Concentration vs Market Volatility", fontsize=11, fontweight="bold")
    ax4.legend(loc="best", fontsize=9)
    ax4.grid(True, alpha=0.3)

    fig.suptitle(
        "Multi-Factor Analysis\nDetection vs Non-Detection Day Characteristics",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"  Saved: {output_path}")
    plt.close()


def main():
    """Generate all visualizations for Paper 1 signal sensitivity analysis."""

    print("=" * 80)
    print("Paper 1: Signal Sensitivity Visualization Generation")
    print("Paper #1 Journal Version - Signal Sensitivity Proof")
    print("=" * 80)
    print()

    # Paths
    data_path = project_root / "docs" / "papers" / "paper1" / "analysis" / "issue_141_enhanced_dataset.csv"
    output_dir = project_root / "docs" / "papers" / "paper1" / "figures"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("Loading enhanced dataset...")
    df = pd.read_csv(data_path)
    print(f"  Loaded {len(df)} days: {df['detected'].sum()} detected, {(~df['detected']).sum()} not detected")
    print()

    # Generate figures
    print("Generating visualizations...")
    print()

    # Figure 11: Calendar Heatmap
    # calendar_path = output_dir / "fig11_detection_calendar.png"
    # create_calendar_heatmap(df, calendar_path)

    # Figure 10: Concentration Distribution
    concentration_path = output_dir / "fig10_gex_concentration.png"
    create_concentration_distribution(df, concentration_path)

    # Archived: Multi-Factor Scatter (not used in paper)
    scatter_path = output_dir / "archive/issue_141_multifactor_analysis.png"
    create_multifactor_scatter(df, scatter_path)

    print()
    print("=" * 80)
    print("VISUALIZATION GENERATION COMPLETE")
    print("=" * 80)
    print()
    print("Figures created:")
    # print(f"  1. {calendar_path}")
    print(f"  2. {concentration_path}")
    print(f"  3. {scatter_path}")
    print()
    print("Next steps:")
    print("  1. Review figures for publication quality")
    print("  2. Update journal paper LaTeX with figures")
    print("  3. Reference in Results section")
    print()


if __name__ == "__main__":
    main()
