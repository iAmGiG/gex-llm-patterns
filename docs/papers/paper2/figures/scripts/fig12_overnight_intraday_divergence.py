#!/usr/bin/env python3
"""
Generate Figure 12: Intraday vs Overnight Return Divergence ("Great Divergence")

This script creates a "Jaw" chart showing the cumulative divergence between
overnight returns (Close T → Open T+1) and intraday returns (Open T+1 → Close T+1),
demonstrating how alpha shifted from intraday to overnight as 0DTE proliferated.

The divergence supports the "scar tissue" mechanism: dealers forced to carry
overnight positioning create overnight risk premium that didn't exist pre-0DTE.

IEEE Publication Theme (white background).

Output: docs/papers/paper2/figures/output/fig12_overnight_intraday_divergence.png
"""

import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from theme import IEEE_THEME, OUTPUT_DIR, CACHE_DB, save_figure

# Colors for the divergence chart
COLORS = {
    "overnight": "#1565C0",  # Blue for overnight returns
    "intraday": "#C62828",   # Red for intraday returns
    "gap_positive": "#E3F2FD",  # Light blue when overnight > intraday
    "gap_negative": "#FFEBEE",  # Light red when intraday > overnight
    "zero_line": "#757575",  # Grey for zero reference
    "annotation": "#2E7D32",  # Green for 0DTE adoption annotation
    "period_2020": "#BBDEFB",  # Light blue background for 2020
    "period_2024": "#FFCDD2",  # Light red background for 2024
}


def load_data():
    """Load OHLC and GEX data from database."""
    db_path = CACHE_DB.parent / "consolidated_historical.db"
    conn = sqlite3.connect(db_path)

    df = pd.read_sql_query("""
        SELECT date, open, high, low, close, total_gex
        FROM daily_gex_metrics
        WHERE symbol = 'SPY'
          AND open IS NOT NULL
        ORDER BY date
    """, conn)
    conn.close()

    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    return df


def calculate_returns(df):
    """Calculate overnight and intraday returns."""
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Overnight: Close T → Open T+1
    df['overnight_ret'] = (df['open'] / df['close'].shift(1) - 1) * 100

    # Intraday: Open T+1 → Close T+1
    df['intraday_ret'] = (df['close'] / df['open'] - 1) * 100

    # Total: Close T → Close T+1
    df['total_ret'] = (df['close'] / df['close'].shift(1) - 1) * 100

    # Drop first row (no prior close)
    df = df.dropna(subset=['overnight_ret', 'intraday_ret'])

    # Cumulative returns
    df['overnight_cum'] = df['overnight_ret'].cumsum()
    df['intraday_cum'] = df['intraday_ret'].cumsum()
    df['total_cum'] = df['total_ret'].cumsum()

    return df


def create_figure():
    """Create the divergence figure."""

    plt.style.use("default")

    # Load and process data
    print("Loading data...")
    df = load_data()
    print(f"Loaded {len(df)} rows")

    df = calculate_returns(df)
    print(f"Calculated returns for {len(df)} days")

    # Create figure with two panels (Panel B gets more vertical space)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 11), dpi=300,
                                    gridspec_kw={'height_ratios': [1.8, 1.2], 'hspace': 0.28})
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax1.set_facecolor(IEEE_THEME["background"])
    ax2.set_facecolor(IEEE_THEME["background"])

    # Main title
    fig.suptitle(
        'The "Great Divergence": Overnight vs Intraday Returns',
        fontsize=16, fontweight="bold", color=IEEE_THEME["text"],
        y=0.96
    )

    # ========================================================================
    # PANEL A: Cumulative Return "Jaw" Chart (Full Period)
    # ========================================================================

    dates = df.index
    overnight = df['overnight_cum'].values
    intraday = df['intraday_cum'].values

    # Plot the two lines
    ax1.plot(dates, overnight, color=COLORS["overnight"], linewidth=2,
             label="Overnight (Close→Open)", zorder=5)
    ax1.plot(dates, intraday, color=COLORS["intraday"], linewidth=2,
             linestyle="--", label="Intraday (Open→Close)", zorder=5)

    # Fill the gap between lines
    ax1.fill_between(dates, overnight, intraday,
                     where=(overnight >= intraday),
                     color=COLORS["gap_positive"], alpha=0.4,
                     label="Overnight Premium", zorder=2)
    ax1.fill_between(dates, overnight, intraday,
                     where=(overnight < intraday),
                     color=COLORS["gap_negative"], alpha=0.4,
                     label="Intraday Premium", zorder=2)

    # Zero reference line
    ax1.axhline(y=0, color=COLORS["zero_line"], linewidth=1, linestyle="-", alpha=0.5, zorder=1)

    # Mark 0DTE adoption period (2022-2023)
    adoption_start = pd.Timestamp("2022-01-01")
    adoption_end = pd.Timestamp("2023-12-31")
    ax1.axvspan(adoption_start, adoption_end, color="#FFF9C4", alpha=0.3, zorder=0)
    ax1.annotate(
        "0DTE\nAdoption",
        xy=(pd.Timestamp("2023-01-01"), ax1.get_ylim()[1] * 0.85),
        fontsize=9, fontweight="bold", ha="center", va="top",
        color=COLORS["annotation"],
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                  edgecolor=COLORS["annotation"], alpha=0.9)
    )

    # Final values annotation
    final_overnight = overnight[-1]
    final_intraday = intraday[-1]
    gap = final_overnight - final_intraday

    ax1.annotate(
        f"Overnight: +{final_overnight:.1f}%",
        xy=(dates[-1], final_overnight),
        xytext=(10, 5), textcoords="offset points",
        fontsize=10, fontweight="bold", color=COLORS["overnight"],
        ha="left", va="bottom"
    )
    ax1.annotate(
        f"Intraday: +{final_intraday:.1f}%",
        xy=(dates[-1], final_intraday),
        xytext=(10, -5), textcoords="offset points",
        fontsize=10, fontweight="bold", color=COLORS["intraday"],
        ha="left", va="top"
    )

    # Gap annotation
    mid_y = (final_overnight + final_intraday) / 2
    ax1.annotate(
        f"Gap: {gap:+.1f}%",
        xy=(dates[-1], mid_y),
        xytext=(50, 0), textcoords="offset points",
        fontsize=11, fontweight="bold", color=IEEE_THEME["text"],
        ha="left", va="center",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F5E9",
                  edgecolor=COLORS["annotation"], linewidth=1.5)
    )

    # Panel A formatting
    ax1.set_ylabel("Cumulative Return (%)", fontsize=12, fontweight="bold",
                   color=IEEE_THEME["text"])
    ax1.set_title("(A) Cumulative Return Divergence (2020-2025)",
                  fontsize=13, fontweight="bold", color=IEEE_THEME["text"], pad=10)

    ax1.legend(loc="upper left", fontsize=10, framealpha=0.95,
               facecolor="white", edgecolor=IEEE_THEME["dim"])

    ax1.grid(True, alpha=0.3, linestyle="-", color=IEEE_THEME["grid"], zorder=0)
    ax1.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax1.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax1.spines[spine].set_color(IEEE_THEME["dim"])
    ax1.tick_params(colors=IEEE_THEME["text"])

    # ========================================================================
    # PANEL B: Year-by-Year Comparison (Bar Chart)
    # ========================================================================

    years = [2020, 2021, 2022, 2023, 2024, 2025]
    overnight_by_year = []
    intraday_by_year = []

    for year in years:
        year_df = df[df.index.year == year]
        if len(year_df) > 0:
            overnight_by_year.append(year_df['overnight_ret'].sum())
            intraday_by_year.append(year_df['intraday_ret'].sum())
        else:
            overnight_by_year.append(0)
            intraday_by_year.append(0)

    x = np.arange(len(years))
    width = 0.35

    bars1 = ax2.bar(x - width/2, overnight_by_year, width,
                    label="Overnight", color=COLORS["overnight"], alpha=0.8)
    bars2 = ax2.bar(x + width/2, intraday_by_year, width,
                    label="Intraday", color=COLORS["intraday"], alpha=0.8)

    # Add value labels on bars (negative bars positioned inside or just above x-axis to prevent collision)
    for bar, val in zip(bars1, overnight_by_year):
        height = bar.get_height()
        # For negative values, place text inside bar or very close to x-axis
        if height >= 0:
            offset_y = 5
            va_pos = 'bottom'
        else:
            offset_y = -5  # Reduced from -16 to prevent overlap with x-axis
            va_pos = 'center'
        ax2.annotate(f'{val:+.1f}%',
                     xy=(bar.get_x() + bar.get_width()/2, height),
                     xytext=(0, offset_y),
                     textcoords="offset points",
                     ha='center', va=va_pos,
                     fontsize=8, fontweight="bold", color=COLORS["overnight"])

    for bar, val in zip(bars2, intraday_by_year):
        height = bar.get_height()
        # For negative values, place text inside bar or very close to x-axis
        if height >= 0:
            offset_y = 5
            va_pos = 'bottom'
        else:
            offset_y = -5  # Reduced from -16 to prevent overlap with x-axis
            va_pos = 'center'
        ax2.annotate(f'{val:+.1f}%',
                     xy=(bar.get_x() + bar.get_width()/2, height),
                     xytext=(0, offset_y),
                     textcoords="offset points",
                     ha='center', va=va_pos,
                     fontsize=8, fontweight="bold", color=COLORS["intraday"])

    # Zero line
    ax2.axhline(y=0, color=COLORS["zero_line"], linewidth=1, linestyle="-", alpha=0.5)

    # Highlight 0DTE adoption period
    ax2.axvspan(1.5, 3.5, color="#FFF9C4", alpha=0.3, zorder=0)

    # Panel B formatting (no xlabel needed - year labels are self-explanatory)
    ax2.set_ylabel("Annual Return (%)", fontsize=12, fontweight="bold",
                   color=IEEE_THEME["text"])
    ax2.set_title("(B) Annual Breakdown: Overnight vs Intraday Returns",
                  fontsize=13, fontweight="bold", color=IEEE_THEME["text"], pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(years)
    ax2.legend(loc="upper right", fontsize=10, framealpha=0.95,
               facecolor="white", edgecolor=IEEE_THEME["dim"])

    ax2.grid(True, axis='y', alpha=0.3, linestyle="-", color=IEEE_THEME["grid"], zorder=0)
    ax2.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax2.spines[spine].set_visible(False)
    for spine in ["bottom", "left"]:
        ax2.spines[spine].set_color(IEEE_THEME["dim"])
    ax2.tick_params(colors=IEEE_THEME["text"])

    # ========================================================================
    # KEY INSIGHT BOX
    # ========================================================================

    insight_text = (
        "Key Observation: Pre-0DTE (2020-2021), overnight and intraday returns were roughly balanced. "
        "Post-0DTE adoption (2024), overnight returns dominate while intraday returns compressed to near-zero. "
        "This pattern is consistent with the 'scar tissue' hypothesis—dealers carrying overnight positioning "
        "extract risk premium from the overnight session. Correlation shown; causation not established."
    )

    fig.text(
        0.5, 0.035, insight_text,
        fontsize=9, ha="center", va="bottom",
        color=IEEE_THEME["text"],
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF3E0",
                  edgecolor="#E65100", linewidth=1.5, alpha=0.95),
        wrap=True,
        linespacing=1.3
    )

    plt.tight_layout(rect=[0, 0.12, 1, 0.94])

    return fig


def main():
    print("Generating Overnight vs Intraday Divergence Figure...")
    fig = create_figure()
    save_figure(fig, "fig12_overnight_intraday_divergence.png")
    print("\nDone!")


if __name__ == "__main__":
    main()
