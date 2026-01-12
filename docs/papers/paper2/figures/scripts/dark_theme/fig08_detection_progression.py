#!/usr/bin/env python3
"""
Generate Figure 8: Phase 4A Detection Rate Temporal Progression

This script creates a temporal analysis figure showing how LLM detection rates
evolved from 2020-2025, revealing gradual 0DTE adoption and the 2023→2024
structural market shift.

Updated with SpotGamma-inspired dark theme (Issue #216).

Issue #195: Phase 4A Detection Rate Temporal Progression Figure
Output: docs/papers/paper2/figures/output/fig08_detection_progression.png
"""

import sqlite3

import matplotlib.pyplot as plt
import numpy as np
from theme import CACHE_DB, DARK_THEME, OUTPUT_DIR, YEAR_COLORS, apply_dark_theme, reset_theme, save_figure


def query_data():
    """Query ResearchCache for detection rates by year."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    query = """
    SELECT
      SUBSTR(trading_date, 1, 4) as year,
      COUNT(*) as total_windows,
      SUM(CASE WHEN detected = 1 THEN 1 ELSE 0 END) as detected_count,
      ROUND(100.0 * SUM(CASE WHEN detected = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as detection_pct,
      ROUND(AVG(CAST(json_extract(structured_output, '$.avg_magnitude_billions') AS REAL)), 1) as avg_gex_magnitude
    FROM llm_detections
    WHERE pattern_id = 'regime_30day'
    GROUP BY SUBSTR(trading_date, 1, 4)
    ORDER BY year
    """

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    return results


def create_figure(results):
    """Create detection progression figure with dark theme."""

    # Extract data
    years = [int(row[0]) for row in results]
    total_windows = [row[1] for row in results]
    detected_counts = [row[2] for row in results]
    detection_rates = [row[3] for row in results]
    avg_gex = [row[4] for row in results]

    # Set dark theme
    apply_dark_theme()

    # Create figure with two subplots (detection rate + GEX magnitude)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), dpi=300, gridspec_kw={"height_ratios": [2, 1]})
    fig.patch.set_facecolor(DARK_THEME["background"])
    ax1.set_facecolor(DARK_THEME["background"])
    ax2.set_facecolor(DARK_THEME["background"])

    # ============================================================================
    # TOP PLOT: Detection Rate Temporal Progression
    # ============================================================================

    # Assign colors based on regime state
    colors = [
        YEAR_COLORS["pre_regime"],  # 2020 - Pre-regime
        YEAR_COLORS["pre_regime"],  # 2021 - Borderline
        YEAR_COLORS["growing"],  # 2022 - Growing
        YEAR_COLORS["growing"],  # 2023 - Inconsistent
        YEAR_COLORS["structural"],  # 2024 - Structural shift
        YEAR_COLORS["structural"],  # 2025 - Sustained
    ]

    # Plot bars with appropriate colors
    bars = ax1.bar(
        years, detection_rates, color=colors, width=0.7, edgecolor=DARK_THEME["background"], linewidth=1.5, alpha=0.9
    )

    # Add detection counts on top of bars
    for i, (year, rate, count, total) in enumerate(zip(years, detection_rates, detected_counts, total_windows)):
        ax1.text(
            year,
            rate + 3,
            f"{count}/{total}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=DARK_THEME["text"],
        )

    # Add percentage labels inside bars
    for i, (year, rate) in enumerate(zip(years, detection_rates)):
        if rate > 15:  # Only show inside if bar is tall enough
            ax1.text(
                year,
                rate / 2,
                f"{rate:.1f}%",
                ha="center",
                va="center",
                fontsize=12,
                fontweight="bold",
                color=DARK_THEME["background"],
            )
        else:
            ax1.text(
                year,
                rate + 8,
                f"{rate:.1f}%",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
                color=DARK_THEME["text"],
            )

    # Highlight 2023→2024 structural shift with annotation
    ax1.annotate(
        "",
        xy=(2024, 100),
        xytext=(2023, 20.2),
        arrowprops=dict(arrowstyle="->", lw=3, color=DARK_THEME["accent_warning"], linestyle="--"),
    )
    ax1.text(
        2023.5,
        60,
        "2023→2024\nStructural\nShift",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=DARK_THEME["text"],
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor=DARK_THEME["panel_bg"],
            edgecolor=DARK_THEME["accent_warning"],
            linewidth=2,
        ),
    )

    # Add regime labels
    ax1.text(2020.5, 108, "Pre-Regime", ha="center", fontsize=10, fontweight="bold", color=YEAR_COLORS["pre_regime"])
    ax1.text(2022.5, 108, "Gradual Adoption", ha="center", fontsize=10, fontweight="bold", color=YEAR_COLORS["growing"])
    ax1.text(
        2024.5, 108, "Persistent Regime", ha="center", fontsize=10, fontweight="bold", color=YEAR_COLORS["structural"]
    )

    # Formatting
    ax1.set_xlabel("Year", fontsize=13, fontweight="bold", color=DARK_THEME["text"])
    ax1.set_ylabel("Detection Rate (%)", fontsize=13, fontweight="bold", color=DARK_THEME["text"])
    ax1.set_title(
        "Phase 4A: Temporal Progression of Regime Detection (2020-2025)\n"
        + "Gradual 0DTE Adoption with 2023→2024 Structural Market Shift",
        fontsize=14,
        fontweight="bold",
        pad=15,
        color=DARK_THEME["text"],
    )
    ax1.set_ylim(0, 118)
    ax1.set_xticks(years)
    ax1.tick_params(colors=DARK_THEME["text"])
    ax1.grid(axis="y", alpha=0.3, linestyle="--", color=DARK_THEME["grid"])
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    for spine in ["bottom", "left"]:
        ax1.spines[spine].set_color(DARK_THEME["dim"])

    # ============================================================================
    # BOTTOM PLOT: Average GEX Magnitude Evolution
    # ============================================================================

    # Plot GEX magnitude as line chart with markers
    ax2.plot(
        years,
        avg_gex,
        marker="o",
        markersize=10,
        linewidth=3,
        color=DARK_THEME["accent_warning"],
        markerfacecolor=DARK_THEME["accent_warning"],
        markeredgecolor=DARK_THEME["background"],
        markeredgewidth=1.5,
    )

    # Add magnitude labels
    for year, gex in zip(years, avg_gex):
        ax2.text(
            year,
            gex + 0.8,
            f"${gex:.1f}B",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
            color=DARK_THEME["text"],
        )

    # Add threshold line at $5B
    ax2.axhline(y=5.0, color=DARK_THEME["accent_positive"], linestyle="--", linewidth=2, alpha=0.8)
    ax2.text(
        2020.3, 5.8, "$5B Threshold", fontsize=9, fontweight="bold", color=DARK_THEME["accent_positive"], va="bottom"
    )

    # Formatting
    ax2.set_xlabel("Year", fontsize=13, fontweight="bold", color=DARK_THEME["text"])
    ax2.set_ylabel("Avg GEX Magnitude ($B)", fontsize=12, fontweight="bold", color=DARK_THEME["text"])
    ax2.set_title(
        "Average GEX Magnitude Evolution (360% Growth 2021→2024)",
        fontsize=12,
        fontweight="bold",
        pad=10,
        color=DARK_THEME["text"],
    )
    ax2.set_ylim(0, 25)
    ax2.set_xticks(years)
    ax2.tick_params(colors=DARK_THEME["text"])
    ax2.grid(axis="y", alpha=0.3, linestyle="--", color=DARK_THEME["grid"])
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    for spine in ["bottom", "left"]:
        ax2.spines[spine].set_color(DARK_THEME["dim"])

    # ============================================================================
    # FOOTER EXPLANATION
    # ============================================================================

    footer_text = (
        "Key Finding: Detection rates track market evolution precisely. Low rates in 2020-2021 (12.2%, 3.7%) reflect pre-regime baseline.\n"
        "Growing but inconsistent rates in 2022-2023 (32.4%, 20.2%) show gradual 0DTE adoption. Perfect 100% detection in 2024-2025\n"
        "marks structural shift with sustained dealer gamma regimes. GEX magnitude grew 360% ($5B → $23B), far exceeding inflation (20-25%)."
    )
    fig.text(
        0.5,
        0.02,
        footer_text,
        ha="center",
        va="bottom",
        fontsize=10,
        style="italic",
        color=DARK_THEME["dim"],
        wrap=True,
    )

    plt.tight_layout(rect=[0, 0.06, 1, 1])

    # Print data summary
    print("\n" + "=" * 60)
    print("PHASE 4A DETECTION RATES BY YEAR (2020-2025)")
    print("=" * 60)
    print(f"{'Year':<6} {'Total':<8} {'Detected':<10} {'Rate':<8} {'Avg GEX':<10}")
    print("-" * 60)
    for year, total, detected, rate, gex in zip(years, total_windows, detected_counts, detection_rates, avg_gex):
        print(f"{year:<6} {total:<8} {detected:<10} {rate:>5.1f}%    ${gex:.1f}B")
    print("=" * 60)

    return fig


def main():
    print("Generating Detection Progression Figure (Issue #195, Dark Theme #216)...")
    print(f"Database: {CACHE_DB}")

    results = query_data()
    fig = create_figure(results)
    save_figure(fig, "fig08_detection_progression.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
