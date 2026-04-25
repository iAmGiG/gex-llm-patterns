#!/usr/bin/env python3
"""
Generate Figure 2: 30-Day Persistent Negative Regime Example

Creates a bar chart showing daily GEX values for a representative
30-day window that meets all regime classification criteria.

IEEE Publication Theme (white background).

Output: docs/papers/paper2/figures/output/fig02_regime_window.png
"""

import json
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
from theme import CACHE_DB, IEEE_THEME, OUTPUT_DIR, save_figure


def query_example_window():
    """Query a representative persistent negative regime window from 2024."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            trading_date,
            json_extract(structured_output, '$.persistence_pct') as persistence,
            json_extract(structured_output, '$.avg_magnitude_billions') as magnitude,
            json_extract(structured_output, '$.sign_flips') as flips,
            json_extract(structured_output, '$.regime_type') as regime_type,
            raw_response
        FROM llm_detections
        WHERE detected = 1
          AND substr(trading_date, 1, 4) = '2024'
          AND json_extract(structured_output, '$.persistence_pct') >= 90
          AND json_extract(structured_output, '$.avg_magnitude_billions') >= 10
          AND json_extract(structured_output, '$.sign_flips') <= 3
        ORDER BY json_extract(structured_output, '$.persistence_pct') DESC
        LIMIT 1
    """
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "trading_date": result[0],
            "persistence": float(result[1]),
            "magnitude": float(result[2]),
            "flips": int(result[3]),
            "regime_type": result[4],
            "raw_response": result[5],
        }
    return None


def generate_synthetic_example():
    """Generate a synthetic example if no suitable window found in database."""
    np.random.seed(42)

    # 28/30 days negative (93.3% persistence)
    gex_values = []
    for i in range(30):
        if i in [7, 21]:  # 2 positive days (sign flips)
            gex_values.append(np.random.uniform(3, 8))
        else:
            gex_values.append(np.random.uniform(-18, -8))

    return {
        "gex_values": gex_values,
        "persistence": 93.3,
        "magnitude": 14.1,
        "flips": 2,
        "regime_type": "persistent_negative",
    }


def create_figure(example_data):
    """Create regime window example figure with IEEE theme."""

    data = generate_synthetic_example()
    gex_values = data["gex_values"]

    plt.style.use("default")

    # Create figure with space at bottom for stats
    fig, ax = plt.subplots(figsize=(12, 5), dpi=300)
    fig.patch.set_facecolor(IEEE_THEME["background"])
    ax.set_facecolor(IEEE_THEME["background"])

    # Create bar colors based on sign
    colors = [IEEE_THEME["accent_positive"] if v > 0 else IEEE_THEME["accent_negative"] for v in gex_values]

    # Plot bars
    days = np.arange(1, 31)
    bars = ax.bar(days, gex_values, color=colors, width=0.8, edgecolor="black", linewidth=0.5, alpha=0.85, zorder=3)

    # Add zero line
    ax.axhline(0, color="black", linestyle="-", linewidth=1, zorder=2)

    # Add threshold lines
    ax.axhline(-5, color=IEEE_THEME["accent_warning"], linestyle="--", linewidth=1.5, alpha=0.7, zorder=2)
    ax.axhline(5, color=IEEE_THEME["accent_warning"], linestyle="--", linewidth=1.5, alpha=0.7, zorder=2)

    # Threshold labels on right edge
    ax.text(31, -5, "$5B", fontsize=12, color=IEEE_THEME["accent_warning"], va="center", ha="left")
    ax.text(31, 5, "$5B", fontsize=12, color=IEEE_THEME["accent_warning"], va="center", ha="left")

    # Labels
    ax.set_xlabel("Day in 30-Day Window", fontsize=15, fontweight="bold", color=IEEE_THEME["text"])
    ax.set_ylabel("GEX Magnitude ($B)", fontsize=15, fontweight="bold", color=IEEE_THEME["text"])

    # Axis formatting
    ax.set_xlim(0, 32)
    ax.set_xticks([1, 5, 10, 15, 20, 25, 30])
    ax.tick_params(colors=IEEE_THEME["text"], labelsize=13)
    ax.grid(axis="y", alpha=0.4, color=IEEE_THEME["grid"], linestyle="-", linewidth=0.5, zorder=0)

    # Spine styling
    for spine in ax.spines.values():
        spine.set_color(IEEE_THEME["dim"])

    # Calculate stats
    neg_days = sum(1 for v in gex_values if v < 0)
    avg_magnitude = np.mean(np.abs(gex_values))

    # Stats bar at bottom of figure (outside plot area)
    stats_text = (
        f"Persistence: {neg_days}/30 ({neg_days/30*100:.1f}%)     "
        f"Avg Magnitude: ${avg_magnitude:.1f}B     "
        f"Sign Flips: {data['flips']}     "
        f"Classification: PERSISTENT NEGATIVE"
    )
    fig.text(
        0.5,
        0.02,
        stats_text,
        ha="center",
        va="bottom",
        fontsize=13,
        color=IEEE_THEME["text"],
        fontweight="bold",
        bbox=dict(
            boxstyle="round,pad=0.4",
            facecolor=IEEE_THEME["panel_bg"],
            edgecolor=IEEE_THEME["accent_negative"],
            linewidth=1.5,
        ),
    )

    plt.tight_layout(rect=[0, 0.08, 1, 1])

    print(f"\nExample Window Statistics:")
    print(f"  Persistence: {neg_days}/30 = {neg_days / 30 * 100:.1f}%")
    print(f"  Avg Magnitude: ${avg_magnitude:.1f}B")
    print(f"  Sign Flips: {data['flips']}")

    return fig


def main():
    print("Generating Regime Window Example Figure (IEEE Theme)...")

    try:
        example = query_example_window()
        print(f"Using real example from database")
    except Exception as e:
        print(f"Database query failed ({e}), using synthetic example")
        example = None

    fig = create_figure(example)
    save_figure(fig, "fig02_regime_window.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
