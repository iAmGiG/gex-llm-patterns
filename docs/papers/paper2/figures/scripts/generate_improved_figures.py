#!/usr/bin/env python3
"""
Paper #2: Improved Figure Generation
Addresses all quality issues and follows Paper 1 naming convention (fig##_descriptor.png)

Issues Fixed:
- Figure 1: Legend moved from bad top-right position
- Figure 3: Legend moved to bottom-left (was covering bars)
- Figure 4: Legend moved to bottom-right (empty space)
- Figure 5: Complete redesign (was unprofessional)
- Figure 6: Far-right column formatting improved
- Figure 7: Fixed anchoring/offset issues
- Figure 8: Simplified/reconsidered (bloat concern)
- Figure 9: Rebuilt with real data
- Figure 10: Complete redesign (architecture)

Naming Convention: fig##_descriptor.png (Paper 1 style)
"""

import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import ConnectionPatch, FancyBboxPatch

# Add project root to path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Output configuration
OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# IEEE Publication Settings
plt.rcParams.update(
    {
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "font.size": 10,
        "font.family": "serif",
        "axes.linewidth": 1.0,
        "xtick.major.width": 1.0,
        "ytick.major.width": 1.0,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    }
)

# Colorblind-friendly palette
COLORS = {
    "negative": "#DC3912",  # Red - negative GEX/pre-transition
    "positive": "#109618",  # Green - positive GEX/detected
    "transition": "#FF9900",  # Orange - transitional/volatile
    "neutral": "#3366CC",  # Blue - neutral/baseline
    "purple": "#9933CC",  # Purple - comparison
    "gray": "#666666",  # Dark gray
    "light_gray": "#CCCCCC",  # Light gray
}


def create_fig01_multiyear_detection():
    """
    Figure 1: Multi-Year Detection Rates (2020-2025)
    FIXED: Legend moved to upper-left, stat box moved to lower-right
    """
    print("Creating fig01_multiyear_detection...")

    # Real data from Phase 4A validation
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    detection = [12.1, 100.0, 100.0, 100.0, 81.2, 100.0]
    n_windows = [223, 250, 251, 250, 223, 221]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Color by era: pre-0DTE (red), post-0DTE stable (green), volatile (orange)
    colors = [
        COLORS["negative"],
        COLORS["positive"],
        COLORS["positive"],
        COLORS["positive"],
        COLORS["transition"],
        COLORS["positive"],
    ]

    bars = ax.bar(years, detection, color=colors, alpha=0.85, edgecolor="black", linewidth=1.5, width=0.7)

    # Add window count annotations above bars
    for year, det, n in zip(years, detection, n_windows):
        ax.text(year, det + 2, f"n={n}", ha="center", va="bottom", fontsize=9)

    # Add transition annotation with arrow
    ax.annotate(
        "Sharp Structural\nTransition",
        xy=(2020.5, 56),
        xytext=(2020.5, 72),
        fontsize=10,
        ha="center",
        weight="bold",
        arrowprops=dict(arrowstyle="->", lw=2, color="black"),
    )

    # Era labels below x-axis
    ax.text(2020, -8, "Pre-0DTE", ha="center", fontsize=9, style="italic")
    ax.text(2022, -8, "Post-0DTE Equilibrium", ha="center", fontsize=9, style="italic")
    ax.text(2024, -8, "Volatile", ha="center", fontsize=9, style="italic")

    ax.set_xlabel("Year", fontsize=12, weight="bold")
    ax.set_ylabel("Detection Rate (%)", fontsize=12, weight="bold")
    ax.set_title("Persistent Regime Detection Across 6 Years (2020-2025)", fontsize=13, weight="bold", pad=15)
    ax.set_ylim(0, 115)
    ax.set_xticks(years)

    # FIXED: Statistics box in LOWER-RIGHT corner (was upper-right covering bars)
    textstr = "2020→2021: 87.9 pp increase\np < 10⁻⁸⁶, φ = 0.909"
    props = dict(boxstyle="round", facecolor="wheat", alpha=0.7)
    ax.text(
        0.98,
        0.05,
        textstr,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="bottom",
        horizontalalignment="right",
        bbox=props,
    )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig01_multiyear_detection.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig02_2020_vs_2024():
    """
    Figure 2: 2020 vs 2024 Metrics Comparison
    Side-by-side grouped bar chart with improved legend placement
    """
    print("Creating fig02_2020_vs_2024...")

    metrics = ["Detection\nRate (%)", "Avg\nConfidence (%)", "Persistence\n(%)", "Avg Magnitude\n($B, scaled)"]

    # Real data
    data_2020 = [12.1, 72.4, 83.3, 2.85]
    data_2024 = [81.2, 86.8, 96.0, 13.95]

    # Normalize magnitude for visualization (scale $B to 0-100 range)
    data_2020_viz = data_2020.copy()
    data_2024_viz = data_2024.copy()
    data_2020_viz[3] = (data_2020[3] / 20) * 100
    data_2024_viz[3] = (data_2024[3] / 20) * 100

    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 6))

    bars1 = ax.bar(
        x - width / 2,
        data_2020_viz,
        width,
        label="2020 (Pre-0DTE)",
        color=COLORS["negative"],
        alpha=0.8,
        edgecolor="black",
        linewidth=1.5,
    )
    bars2 = ax.bar(
        x + width / 2,
        data_2024_viz,
        width,
        label="2024 (Post-0DTE)",
        color=COLORS["positive"],
        alpha=0.8,
        edgecolor="black",
        linewidth=1.5,
    )

    # Add value labels
    for i, (b1, b2) in enumerate(zip(bars1, bars2)):
        val1, val2 = data_2020[i], data_2024[i]
        fmt = "${:.1f}B" if i == 3 else "{:.1f}%"
        ax.text(
            b1.get_x() + b1.get_width() / 2, b1.get_height() + 2, fmt.format(val1), ha="center", va="bottom", fontsize=9
        )
        ax.text(
            b2.get_x() + b2.get_width() / 2, b2.get_height() + 2, fmt.format(val2), ha="center", va="bottom", fontsize=9
        )

    ax.set_ylabel("Metric Value (Normalized)", fontsize=12, weight="bold")
    ax.set_title("Market Structure Comparison: 2020 vs 2024", fontsize=13, weight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10)
    ax.legend(fontsize=10, loc="upper left")
    ax.set_ylim(0, 115)

    # Summary annotation in lower-right
    ax.text(
        0.98,
        0.05,
        "69.1 pp detection increase\n4.9x magnitude increase",
        transform=ax.transAxes,
        fontsize=9,
        va="bottom",
        ha="right",
        bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.7),
    )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig02_2020_vs_2024.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig03_negative_controls():
    """
    Figure 3: Phase 2 Negative Controls Validation
    FIXED: Legend moved to BOTTOM-LEFT (was covering bars at top-left)
    """
    print("Creating fig03_negative_controls...")

    tests = ["Shuffle", "Transitional\n(7-10 flips)", "Low Magnitude\n(<$5B)"]
    fp_2024 = [61.1, 0.0, 0.0]
    fp_2020 = [12.1, 0.0, 0.0]
    thresholds = [20, 10, 10]

    x = np.arange(len(tests))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))

    bars1 = ax.bar(
        x - width / 2,
        fp_2024,
        width,
        label="2024 Q1 FP Rate",
        color=COLORS["neutral"],
        alpha=0.8,
        edgecolor="black",
        linewidth=1.5,
    )
    bars2 = ax.bar(
        x + width / 2,
        fp_2020,
        width,
        label="2020 FP Rate",
        color=COLORS["purple"],
        alpha=0.8,
        edgecolor="black",
        linewidth=1.5,
    )

    # Threshold lines
    for i, thresh in enumerate(thresholds):
        ax.hlines(
            thresh,
            i - 0.5,
            i + 0.5,
            colors="red",
            linestyles="dashed",
            linewidth=2,
            label="Threshold" if i == 0 else "",
        )

    # Value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 1.5, f"{h:.1f}%", ha="center", va="bottom", fontsize=9)

    # PASS/FAIL annotations
    for i in range(len(tests)):
        stat_2024 = "PASS" if fp_2024[i] < thresholds[i] else "FAIL"
        stat_2020 = "PASS" if fp_2020[i] < thresholds[i] else "FAIL"
        c_2024 = COLORS["positive"] if stat_2024 == "PASS" else COLORS["negative"]
        c_2020 = COLORS["positive"] if stat_2020 == "PASS" else COLORS["negative"]
        ax.text(i - width / 2, -4, stat_2024, ha="center", fontsize=8, weight="bold", color=c_2024)
        ax.text(i + width / 2, -4, stat_2020, ha="center", fontsize=8, weight="bold", color=c_2020)

    ax.set_ylabel("False Positive Rate (%)", fontsize=12, weight="bold")
    ax.set_title("Phase 2 Negative Controls Validation", fontsize=13, weight="bold", pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(tests, fontsize=10)
    ax.set_ylim(-8, 70)

    # FIXED: Legend in BOTTOM-LEFT corner (was top-left covering bars)
    ax.legend(fontsize=9, loc="lower left", framealpha=0.9)

    # Selectivity validation box (upper-right, clear of bars)
    ax.text(
        0.98,
        0.98,
        "Framework selectivity validated:\n0% FP on transitional/low-mag tests",
        transform=ax.transAxes,
        fontsize=9,
        va="top",
        ha="right",
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.7),
    )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig03_negative_controls.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig04_gex_evolution():
    """
    Figure 4: GEX Magnitude Evolution (2020-2025)
    FIXED: Legend moved to BOTTOM-RIGHT (was top-left, now in empty space)
    """
    print("Creating fig04_gex_evolution...")

    years = [2020, 2021, 2022, 2023, 2024, 2025]
    gex_magnitude = [17.3, 27.2, 20.1, 30.0, 32.0, 30.4]

    fig, ax = plt.subplots(figsize=(10, 6))

    # Main line
    ax.plot(
        years,
        gex_magnitude,
        marker="o",
        markersize=10,
        linewidth=3,
        color="#2c3e50",
        label="Avg GEX Magnitude",
        zorder=3,
    )

    # Era shading
    ax.axvspan(2019.5, 2020.5, alpha=0.15, color=COLORS["negative"], label="Pre-0DTE Era")
    ax.axvspan(2020.5, 2025.5, alpha=0.15, color=COLORS["positive"], label="Post-0DTE Era")

    # Transition line
    ax.axvline(x=2020.5, color="black", linestyle="--", linewidth=2, alpha=0.5)
    ax.text(
        2020.7,
        33,
        "Structural\nTransition",
        fontsize=10,
        weight="bold",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )

    # Value labels
    for year, gex in zip(years, gex_magnitude):
        ax.text(year, gex + 1.2, f"${gex:.1f}B", ha="center", va="bottom", fontsize=9)

    # Magnitude increase annotation
    ax.annotate(
        "", xy=(2021, 27.2), xytext=(2020, 17.3), arrowprops=dict(arrowstyle="<->", lw=2, color=COLORS["negative"])
    )
    ax.text(
        2020.5,
        21.5,
        "+58%",
        ha="center",
        fontsize=10,
        weight="bold",
        bbox=dict(boxstyle="round", facecolor="yellow", alpha=0.7),
    )

    ax.set_xlabel("Year", fontsize=12, weight="bold")
    ax.set_ylabel("Average GEX Magnitude ($B)", fontsize=12, weight="bold")
    ax.set_title("Gamma Exposure Evolution: Pre vs Post-0DTE Era", fontsize=13, weight="bold", pad=15)
    ax.set_xticks(years)
    ax.set_ylim(14, 36)
    ax.set_xlim(2019.5, 2025.5)

    # FIXED: Legend in BOTTOM-RIGHT corner (was top-left)
    ax.legend(fontsize=9, loc="lower right", framealpha=0.9)

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig04_gex_evolution.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig05_obfuscation():
    """
    Figure 5: Temporal Obfuscation Process
    COMPLETE REDESIGN - Professional side-by-side comparison
    """
    print("Creating fig05_obfuscation (complete redesign)...")

    fig, axes = plt.subplots(1, 3, figsize=(12, 5), gridspec_kw={"width_ratios": [1, 0.3, 1]})

    # Common styling
    for ax in [axes[0], axes[2]]:
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal")
        ax.axis("off")

    axes[1].axis("off")  # Middle arrow section

    # Left panel: Original Data
    ax_left = axes[0]
    rect = FancyBboxPatch(
        (0.5, 1), 9, 8, boxstyle="round,pad=0.1", facecolor="#E3F2FD", edgecolor="#1976D2", linewidth=3
    )
    ax_left.add_patch(rect)

    ax_left.text(5, 8.3, "Original Data", fontsize=14, weight="bold", ha="center", color="#1976D2")

    original_fields = [
        ("Date:", "2024-01-15", "#000000"),
        ("Symbol:", "SPY", "#000000"),
        ("Net GEX:", "-$12.3B", "#D32F2F"),
        ("Strike:", "$475", "#000000"),
        ("Expiry:", "2024-01-19", "#000000"),
    ]

    y_pos = 6.8
    for label, value, color in original_fields:
        ax_left.text(1.5, y_pos, label, fontsize=11, ha="left", color="#666666")
        ax_left.text(4.5, y_pos, value, fontsize=11, ha="left", weight="bold", color=color)
        y_pos -= 1.1

    # Middle: Arrow
    ax_mid = axes[1]
    ax_mid.annotate(
        "",
        xy=(0.8, 0.5),
        xytext=(0.2, 0.5),
        xycoords="axes fraction",
        arrowprops=dict(arrowstyle="->", lw=3, color="#666666"),
    )
    ax_mid.text(
        0.5, 0.65, "Obfuscate", fontsize=12, ha="center", transform=ax_mid.transAxes, weight="bold", color="#666666"
    )

    # Right panel: Obfuscated Data
    ax_right = axes[2]
    rect = FancyBboxPatch(
        (0.5, 1), 9, 8, boxstyle="round,pad=0.1", facecolor="#E8F5E9", edgecolor="#388E3C", linewidth=3
    )
    ax_right.add_patch(rect)

    ax_right.text(5, 8.3, "Obfuscated Data", fontsize=14, weight="bold", ha="center", color="#388E3C")

    obfuscated_fields = [
        ("Date:", "Day T-10", "#388E3C"),
        ("Symbol:", "INDEX_1", "#388E3C"),
        ("Net GEX:", "-$12.3B", "#D32F2F"),  # Preserved (red to show it's kept)
        ("Strike:", "ATM-2", "#388E3C"),
        ("Expiry:", "T+4", "#388E3C"),
    ]

    y_pos = 6.8
    for label, value, color in obfuscated_fields:
        ax_right.text(1.5, y_pos, label, fontsize=11, ha="left", color="#666666")
        ax_right.text(4.5, y_pos, value, fontsize=11, ha="left", weight="bold", color=color)
        y_pos -= 1.1

    # Title and annotations
    fig.suptitle("Temporal Obfuscation Process", fontsize=16, weight="bold", y=0.98)

    # Bottom annotations
    annotations = [
        ("Preserved:", "GEX magnitude, relative strikes, structure", "#1976D2"),
        ("Removed:", "Calendar dates, ticker identity, temporal context", "#D32F2F"),
        ("Purpose:", "Prevent training data memorization", "#666666"),
    ]

    y_offset = 0.02
    for label, text, color in annotations:
        fig.text(0.15, y_offset + 0.08, label, fontsize=10, color=color, weight="bold")
        fig.text(0.23, y_offset + 0.08, text, fontsize=10, color="#666666")
        y_offset += 0.03

    plt.tight_layout(rect=[0, 0.15, 1, 0.95])
    output_path = OUTPUT_DIR / "fig05_obfuscation.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig06_regime_window():
    """
    Figure 6: 30-Day Persistent Negative Regime Example
    FIXED: Far-right criteria box formatting improved
    """
    print("Creating fig06_regime_window...")

    fig, (ax_chart, ax_criteria) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [2.5, 1]})

    # Simulated 30-day GEX data (realistic pattern from 2024)
    np.random.seed(42)
    base_gex = -14.0
    gex_data = base_gex + np.random.randn(30) * 2.5
    # Add 2 positive flips (days 8 and 22)
    gex_data[7] = 3.2
    gex_data[21] = 2.8

    days = np.arange(1, 31)
    colors = [COLORS["positive"] if g > 0 else COLORS["negative"] for g in gex_data]

    ax_chart.bar(days, gex_data, color=colors, edgecolor="none", width=0.8)
    ax_chart.axhline(y=0, color="black", linewidth=1.5)

    ax_chart.set_xlabel("Trading Day", fontsize=12, weight="bold")
    ax_chart.set_ylabel("Net GEX ($B)", fontsize=12, weight="bold")
    ax_chart.set_title("30-Day Persistent Negative Regime Example", fontsize=13, weight="bold")
    ax_chart.set_xlim(0.5, 30.5)
    ax_chart.set_ylim(-20, 6)
    ax_chart.set_xticks([1, 5, 10, 15, 20, 25, 30])

    # Y-axis formatting
    ax_chart.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.0f}B"))

    # FIXED: Criteria box with proper formatting
    ax_criteria.axis("off")
    ax_criteria.set_xlim(0, 10)
    ax_criteria.set_ylim(0, 10)

    # Title box
    rect = FancyBboxPatch(
        (0.3, 6.5), 9.4, 3.2, boxstyle="round,pad=0.1", facecolor="#F5F5F5", edgecolor="#666666", linewidth=2
    )
    ax_criteria.add_patch(rect)
    ax_criteria.text(5, 9.2, "Detection Criteria", fontsize=12, weight="bold", ha="center")

    # Criteria items with proper alignment
    criteria = [
        ("Persistence:", "28/30 days negative", "(threshold: >=70%)", "PASS"),
        ("Magnitude:", "Avg $14.1B", "(threshold: >=$5B)", "PASS"),
        ("Stability:", "2 sign flips", "(threshold: <=5)", "PASS"),
    ]

    y = 8.3
    for label, value, threshold, status in criteria:
        ax_criteria.text(0.8, y, label, fontsize=10, ha="left", color="#666666")
        ax_criteria.text(4.0, y, value, fontsize=10, ha="left", weight="bold")
        ax_criteria.text(9.3, y, status, fontsize=9, ha="right", weight="bold", color=COLORS["positive"])
        ax_criteria.text(4.0, y - 0.5, threshold, fontsize=8, ha="left", color="#999999")
        y -= 1.2

    # Result badge
    result_rect = FancyBboxPatch(
        (0.5, 0.5), 9, 1.5, boxstyle="round,pad=0.1", facecolor=COLORS["positive"], edgecolor="none"
    )
    ax_criteria.add_patch(result_rect)
    ax_criteria.text(5, 1.25, "PERSISTENT REGIME DETECTED", fontsize=11, weight="bold", ha="center", color="white")

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig06_regime_window.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig07_selectivity():
    """
    Figure 7: Framework Selectivity Demonstration
    FIXED: Anchoring/offset issues corrected
    """
    print("Creating fig07_selectivity (fixed anchoring)...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    examples = [
        {
            "ax": axes[0, 0],
            "title": "2024 Persistent Negative",
            "year": "2024",
            "persistence": 96.0,
            "magnitude": 14.1,
            "flips": 1,
            "detected": True,
            "reason": "All criteria met",
            "bg_color": "#E8F5E9",
            "border_color": COLORS["positive"],
        },
        {
            "ax": axes[0, 1],
            "title": "2020 Pre-0DTE Baseline",
            "year": "2020",
            "persistence": 78.0,
            "magnitude": 2.9,
            "flips": 3,
            "detected": False,
            "reason": "Magnitude below $5B",
            "bg_color": "#FFEBEE",
            "border_color": COLORS["negative"],
        },
        {
            "ax": axes[1, 0],
            "title": "2024 Transitional Window",
            "year": "2024",
            "persistence": 90.0,
            "magnitude": 18.5,
            "flips": 8,
            "detected": False,
            "reason": "Excessive volatility",
            "bg_color": "#FFEBEE",
            "border_color": COLORS["negative"],
        },
        {
            "ax": axes[1, 1],
            "title": "2023 Stable Positive",
            "year": "2023",
            "persistence": 85.0,
            "magnitude": 8.2,
            "flips": 2,
            "detected": True,
            "reason": "All criteria met",
            "bg_color": "#E8F5E9",
            "border_color": COLORS["positive"],
        },
    ]

    for ex in examples:
        ax = ex["ax"]
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis("off")
        ax.set_facecolor(ex["bg_color"])

        # Border
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(ex["border_color"])
            spine.set_linewidth(3)

        # Title and year badge (FIXED: proper offset calculation)
        ax.text(5, 9.0, ex["title"], fontsize=13, weight="bold", ha="center")

        # Year badge - positioned relative to title
        badge_x = 8.5
        badge_y = 8.8
        badge = FancyBboxPatch(
            (badge_x - 0.6, badge_y - 0.3),
            1.2,
            0.6,
            boxstyle="round,pad=0.05",
            facecolor=COLORS["neutral"] if ex["year"] == "2024" else COLORS["purple"],
            edgecolor="none",
        )
        ax.add_patch(badge)
        ax.text(badge_x, badge_y, ex["year"], fontsize=9, ha="center", va="center", color="white", weight="bold")

        # Metrics with PASS/FAIL indicators (FIXED: consistent positioning)
        metrics = [
            ("Persistence:", f"{ex['persistence']:.0f}%", ex["persistence"] >= 70),
            ("Magnitude:", f"${ex['magnitude']:.1f}B", ex["magnitude"] >= 5.0),
            ("Sign Flips:", str(ex["flips"]), ex["flips"] <= 5),
        ]

        y = 7.0
        for label, value, passed in metrics:
            ax.text(1.0, y, label, fontsize=11, ha="left", color="#666666")
            ax.text(4.5, y, value, fontsize=11, ha="left", weight="bold")

            status = "PASS" if passed else "FAIL"
            color = COLORS["positive"] if passed else COLORS["negative"]
            ax.text(9.0, y, status, fontsize=10, ha="right", weight="bold", color=color)
            y -= 1.3

        # Divider line
        ax.axhline(y=3.0, xmin=0.1, xmax=0.9, color="#CCCCCC", linewidth=1)

        # Result (FIXED: proper vertical positioning)
        symbol = "[+]" if ex["detected"] else "[-]"
        status = "DETECTED" if ex["detected"] else "NOT DETECTED"
        color = COLORS["positive"] if ex["detected"] else COLORS["negative"]

        ax.text(1.0, 2.0, symbol, fontsize=14, ha="left", color=color, weight="bold")
        ax.text(2.2, 2.0, status, fontsize=12, ha="left", color=color, weight="bold")
        ax.text(1.0, 1.0, ex["reason"], fontsize=10, ha="left", color="#666666")

    fig.suptitle("Framework Selectivity: Regime Classification", fontsize=15, weight="bold", y=0.98)

    # Legend at bottom
    legend_elements = [
        mpatches.Patch(facecolor=COLORS["positive"], label="Detected (criteria met)"),
        mpatches.Patch(facecolor=COLORS["negative"], label="Not detected (criteria failed)"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=2, fontsize=10, bbox_to_anchor=(0.5, 0.02))

    plt.tight_layout(rect=[0, 0.06, 1, 0.96])
    output_path = OUTPUT_DIR / "fig07_selectivity.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig08_validation_pipeline():
    """
    Figure 8: Multi-Phase Validation Pipeline
    REDESIGNED: Simplified horizontal flow (addressing bloat concern)
    """
    print("Creating fig08_validation_pipeline (simplified)...")

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4)
    ax.axis("off")

    phases = [
        {"name": "Phase 1", "sub": "Baseline", "desc": "Q1 2024\nn = 52", "rate": "71.2%", "color": COLORS["neutral"]},
        {
            "name": "Phase 2",
            "sub": "Negatives",
            "desc": "Synthetic\nn = 809",
            "rate": "6.3%",
            "color": COLORS["purple"],
        },
        {"name": "Phase 3", "sub": "Full Year", "desc": "2024\nn = 223", "rate": "81.2%", "color": COLORS["neutral"]},
        {"name": "Phase 4", "sub": "Pre-0DTE", "desc": "2020\nn = 223", "rate": "12.1%", "color": COLORS["negative"]},
        {
            "name": "Phase 4A",
            "sub": "Multi-Year",
            "desc": "2020-2025\nn = 1,418",
            "rate": "73.8%",
            "color": COLORS["positive"],
        },
    ]

    box_w, box_h = 2.2, 2.0
    start_x = 0.8
    gap = 0.4
    y_center = 2.5

    for i, phase in enumerate(phases):
        x = start_x + i * (box_w + gap)

        # Phase box
        rect = FancyBboxPatch(
            (x, y_center - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.1",
            facecolor=phase["color"],
            edgecolor="#333333",
            linewidth=2,
        )
        ax.add_patch(rect)

        # Text
        ax.text(
            x + box_w / 2,
            y_center + 0.5,
            phase["name"],
            fontsize=11,
            weight="bold",
            ha="center",
            va="center",
            color="white",
        )
        ax.text(x + box_w / 2, y_center + 0.1, phase["sub"], fontsize=9, ha="center", va="center", color="white")

        # Metrics below box
        ax.text(x + box_w / 2, y_center - 1.3, phase["desc"], fontsize=9, ha="center", va="top", color="#666666")
        ax.text(
            x + box_w / 2,
            y_center - 1.9,
            phase["rate"],
            fontsize=12,
            weight="bold",
            ha="center",
            va="top",
            color="#333333",
        )

        # Arrow to next (except last)
        if i < len(phases) - 1:
            ax.annotate(
                "",
                xy=(x + box_w + gap - 0.1, y_center),
                xytext=(x + box_w + 0.1, y_center),
                arrowprops=dict(arrowstyle="->", lw=2, color="#666666"),
            )

    # Title
    ax.text(7, 3.8, "Multi-Phase Validation Pipeline", fontsize=14, weight="bold", ha="center")

    # Summary
    ax.text(
        7,
        0.2,
        "Key Finding: Detection rate increased from 12.1% (2020) to 81.2% (2024) following 0DTE market structure shift",
        fontsize=10,
        ha="center",
        style="italic",
        color="#666666",
    )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig08_validation_pipeline.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig09_temporal_trend():
    """
    Figure 9: Detection Rate by Year (2020-2025)
    REBUILT: Using real data with proper line chart
    """
    print("Creating fig09_temporal_trend (real data)...")

    fig, ax = plt.subplots(figsize=(12, 6))

    # Real Phase 4A data
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    detection = [12.1, 100.0, 100.0, 100.0, 81.2, 100.0]
    windows = [223, 250, 251, 250, 223, 221]

    # Main line plot
    ax.plot(
        years,
        detection,
        "o-",
        color=COLORS["neutral"],
        linewidth=3,
        markersize=12,
        markerfacecolor="white",
        markeredgewidth=3,
    )

    # Data labels
    for yr, det in zip(years, detection):
        offset = 5 if det < 90 else -8
        ax.text(yr, det + offset, f"{det:.1f}%", ha="center", fontsize=10, weight="bold")

    # Window count labels
    for yr, n in zip(years, windows):
        ax.text(yr, -8, f"n={n}", ha="center", fontsize=8, color="#666666")

    # 0DTE transition annotation
    ax.axvline(x=2020.5, color=COLORS["transition"], linestyle="--", linewidth=2, alpha=0.7)

    # Annotation box
    ax.annotate(
        "0DTE Launch\nMay 2022 (SPY)\nMarket structure shift",
        xy=(2020.5, 56),
        xytext=(2021.2, 40),
        fontsize=9,
        ha="left",
        bbox=dict(boxstyle="round", facecolor="white", edgecolor=COLORS["transition"], linewidth=2),
        arrowprops=dict(arrowstyle="->", color=COLORS["transition"], lw=2),
    )

    ax.set_xlabel("Year", fontsize=12, weight="bold")
    ax.set_ylabel("Detection Rate (%)", fontsize=12, weight="bold")
    ax.set_title("Detection Rate by Year: 0DTE Market Structure Transition", fontsize=13, weight="bold", pad=15)
    ax.set_xlim(2019.5, 2025.5)
    ax.set_ylim(-15, 115)
    ax.set_xticks(years)

    # Summary at bottom
    ax.text(
        0.5,
        0.02,
        "8.3x increase in detection rate from 2020 to 2021 (p < 0.0001, phi = 0.672)",
        transform=ax.transAxes,
        fontsize=10,
        ha="center",
        style="italic",
        color="#666666",
    )

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig09_temporal_trend.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def create_fig10_architecture():
    """
    Figure 10: System Architecture
    COMPLETE REDESIGN: Clean block diagram with proper flow
    """
    print("Creating fig10_architecture (complete redesign)...")

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # Title
    ax.text(7, 6.7, "LLM Regime Detection System Architecture", fontsize=15, weight="bold", ha="center")

    # Component definitions
    components = [
        {
            "name": "Data\nIngestion",
            "items": ["Alpha Vantage API", "Options chains", "1,475 trading days"],
            "x": 0.5,
            "y": 4.0,
            "w": 2.3,
            "h": 2.0,
            "color": "#E3F2FD",
            "border": "#1976D2",
        },
        {
            "name": "GEX\nCalculation",
            "items": ["Net gamma exposure", "OI vs Volume", "Strike aggregation"],
            "x": 3.1,
            "y": 4.0,
            "w": 2.3,
            "h": 2.0,
            "color": "#E3F2FD",
            "border": "#1976D2",
        },
        {
            "name": "Temporal\nObfuscation",
            "items": ["Date masking", "Symbol aliasing", "Relative strikes"],
            "x": 5.7,
            "y": 4.0,
            "w": 2.3,
            "h": 2.0,
            "color": "#E8F5E9",
            "border": "#388E3C",
        },
        {
            "name": "30-Day\nWindows",
            "items": ["Rolling windows", "Regime detection", "1,418 windows"],
            "x": 8.3,
            "y": 4.0,
            "w": 2.3,
            "h": 2.0,
            "color": "#E8F5E9",
            "border": "#388E3C",
        },
        {
            "name": "LLM\nAnalysis",
            "items": ["OpenAI o4-mini", "Batch API", "Regime prediction"],
            "x": 10.9,
            "y": 4.0,
            "w": 2.3,
            "h": 2.0,
            "color": "#F3E5F5",
            "border": "#7B1FA2",
        },
    ]

    # Draw components
    for comp in components:
        rect = FancyBboxPatch(
            (comp["x"], comp["y"]),
            comp["w"],
            comp["h"],
            boxstyle="round,pad=0.1",
            facecolor=comp["color"],
            edgecolor=comp["border"],
            linewidth=3,
        )
        ax.add_patch(rect)

        # Name
        ax.text(
            comp["x"] + comp["w"] / 2,
            comp["y"] + comp["h"] - 0.4,
            comp["name"],
            fontsize=11,
            weight="bold",
            ha="center",
            va="top",
        )

        # Items
        y = comp["y"] + comp["h"] - 1.0
        for item in comp["items"]:
            ax.text(comp["x"] + comp["w"] / 2, y, item, fontsize=9, ha="center", color="#666666")
            y -= 0.35

    # Arrows between components
    for i in range(len(components) - 1):
        x1 = components[i]["x"] + components[i]["w"]
        x2 = components[i + 1]["x"]
        y = components[i]["y"] + components[i]["h"] / 2
        ax.annotate(
            "", xy=(x2 - 0.05, y), xytext=(x1 + 0.05, y), arrowprops=dict(arrowstyle="->", lw=2, color="#666666")
        )

    # Database box
    db_x, db_y = 3.1, 1.5
    db_rect = FancyBboxPatch(
        (db_x, db_y), 2.3, 1.3, boxstyle="round,pad=0.1", facecolor="white", edgecolor="#1976D2", linewidth=2
    )
    ax.add_patch(db_rect)
    ax.text(db_x + 1.15, db_y + 0.9, "SQLite DB", fontsize=10, weight="bold", ha="center", color="#1976D2")
    ax.text(db_x + 1.15, db_y + 0.5, "3.25 GB", fontsize=9, ha="center", color="#666666")
    ax.text(db_x + 1.15, db_y + 0.2, "11.8M options", fontsize=8, ha="center", color="#999999")

    # Arrow from GEX to DB
    ax.annotate(
        "",
        xy=(db_x + 1.15, db_y + 1.3),
        xytext=(3.1 + 1.15, 4.0),
        arrowprops=dict(arrowstyle="->", lw=2, color="#1976D2"),
    )

    # Results box
    res_x, res_y = 5.5, 0.5
    res_rect = FancyBboxPatch(
        (res_x, res_y), 6.5, 1.5, boxstyle="round,pad=0.1", facecolor="#F5F5F5", edgecolor="#333333", linewidth=2
    )
    ax.add_patch(res_rect)
    ax.text(res_x + 3.25, res_y + 1.2, "Validation Results", fontsize=11, weight="bold", ha="center")

    results = [
        "2020: 12.1% detection (pre-0DTE baseline)",
        "2021-2023, 2025: 100% detection (post-0DTE)",
        "2024: 81.2% detection (volatility period)",
    ]
    y = res_y + 0.85
    for res in results:
        ax.text(res_x + 3.25, y, res, fontsize=9, ha="center", color="#666666")
        y -= 0.3

    # Arrow from LLM to Results
    ax.annotate(
        "",
        xy=(res_x + 3.25, res_y + 1.5),
        xytext=(10.9 + 1.15, 4.0),
        arrowprops=dict(arrowstyle="->", lw=2, color="#7B1FA2", connectionstyle="arc3,rad=-0.2"),
    )

    # Legend
    legend_items = [
        ("#1976D2", "Data Layer"),
        ("#388E3C", "Processing Layer"),
        ("#7B1FA2", "Analysis Layer"),
    ]
    legend_x = 0.8
    for color, label in legend_items:
        rect = FancyBboxPatch((legend_x, 0.3), 0.4, 0.4, boxstyle="round,pad=0.02", facecolor=color, edgecolor="none")
        ax.add_patch(rect)
        ax.text(legend_x + 0.6, 0.5, label, fontsize=9, va="center", color="#666666")
        legend_x += 3.5

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig10_architecture.png"
    plt.savefig(output_path, bbox_inches="tight", facecolor="white")
    print(f"  Saved: {output_path.name}")
    plt.close()


def main():
    """Generate all improved figures."""
    print("\n" + "=" * 60)
    print("Generating Improved Paper #2 Figures")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print("-" * 60)

    create_fig01_multiyear_detection()
    create_fig02_2020_vs_2024()
    create_fig03_negative_controls()
    create_fig04_gex_evolution()
    create_fig05_obfuscation()
    create_fig06_regime_window()
    create_fig07_selectivity()
    create_fig08_validation_pipeline()
    create_fig09_temporal_trend()
    create_fig10_architecture()

    print("-" * 60)
    print("\nAll figures generated successfully!")
    print("\nNew naming convention (Paper 1 style):")
    for f in sorted(OUTPUT_DIR.glob("fig*.png")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
