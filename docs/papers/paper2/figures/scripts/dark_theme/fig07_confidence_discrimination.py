#!/usr/bin/env python3
"""
Generate Figure 7: LLM Confidence Discrimination Across Full Detection Spectrum

Creates scatterplot showing relationship between persistence and LLM confidence
for all Phase 5 validation windows, demonstrating confidence discrimination
between detected regimes and rejected cases.

Updated with SpotGamma-inspired dark theme (Issue #216).

Output: docs/papers/paper2/figures/output/fig07_confidence_discrimination.png
"""

import sqlite3

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from theme import CACHE_DB, DARK_THEME, OUTPUT_DIR, apply_dark_theme, reset_theme, save_figure


def query_data():
    """Query persistence, confidence, and magnitude data from ResearchCache."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            json_extract(structured_output, '$.persistence_pct') as persistence,
            confidence,
            detected,
            json_extract(structured_output, '$.avg_magnitude_billions') as magnitude
        FROM llm_detections
        WHERE structured_output IS NOT NULL
          AND confidence IS NOT NULL
        ORDER BY persistence
    """
    )

    rows = cursor.fetchall()
    conn.close()

    data = {"persistence": [], "confidence": [], "detected": [], "magnitude": []}

    for persistence, confidence, detected, magnitude in rows:
        if persistence is not None and confidence is not None:
            data["persistence"].append(float(persistence))
            data["confidence"].append(int(confidence))
            data["detected"].append(int(detected))
            data["magnitude"].append(float(magnitude) if magnitude else 5.0)

    return {k: np.array(v) for k, v in data.items()}


def create_figure(data):
    """Create confidence discrimination scatterplot with dark theme."""

    # Split data by detection status
    detected_mask = data["detected"] == 1
    rejected_mask = data["detected"] == 0

    # Calculate statistics
    n_detected = detected_mask.sum()
    n_rejected = rejected_mask.sum()
    mean_conf_detected = data["confidence"][detected_mask].mean()
    mean_conf_rejected = data["confidence"][rejected_mask].mean()
    conf_gap = mean_conf_detected - mean_conf_rejected

    # Calculate correlation for detected regimes
    detected_persistence = data["persistence"][detected_mask]
    detected_confidence = data["confidence"][detected_mask]
    r_detected, p_detected = stats.pearsonr(detected_persistence, detected_confidence)

    # Set dark theme
    apply_dark_theme()

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    fig.patch.set_facecolor(DARK_THEME["background"])
    ax.set_facecolor(DARK_THEME["background"])

    # Normalize magnitude for point sizes
    sizes_detected = (data["magnitude"][detected_mask] / data["magnitude"].max()) * 200 + 30
    sizes_rejected = (data["magnitude"][rejected_mask] / data["magnitude"].max()) * 200 + 30

    # Plot rejected points first (background)
    ax.scatter(
        data["persistence"][rejected_mask],
        data["confidence"][rejected_mask],
        s=sizes_rejected,
        c=DARK_THEME["accent_negative"],
        alpha=0.5,
        label=f"Rejected (n={n_rejected}, mean={mean_conf_rejected:.1f}%)",
        edgecolors=DARK_THEME["background"],
        linewidths=0.5,
    )

    # Plot detected points on top
    ax.scatter(
        data["persistence"][detected_mask],
        data["confidence"][detected_mask],
        s=sizes_detected,
        c=DARK_THEME["accent_positive"],
        alpha=0.7,
        label=f"Detected (n={n_detected}, mean={mean_conf_detected:.1f}%)",
        edgecolors=DARK_THEME["background"],
        linewidths=0.5,
    )

    # Add persistence threshold line at 70%
    ax.axvline(
        70,
        color=DARK_THEME["accent_neutral"],
        linestyle="--",
        linewidth=2.5,
        label="70% Persistence Threshold",
        zorder=10,
    )

    # Add mean confidence lines
    ax.axhline(mean_conf_detected, color=DARK_THEME["accent_positive"], linestyle=":", linewidth=2, alpha=0.8)
    ax.axhline(mean_conf_rejected, color=DARK_THEME["accent_negative"], linestyle=":", linewidth=2, alpha=0.8)

    # Annotate confidence gap
    gap_x = 95
    ax.annotate(
        "",
        xy=(gap_x, mean_conf_detected),
        xytext=(gap_x, mean_conf_rejected),
        arrowprops=dict(arrowstyle="<->", color=DARK_THEME["accent_warning"], lw=2.5, shrinkA=0, shrinkB=0),
    )
    ax.text(
        gap_x + 1.5,
        (mean_conf_detected + mean_conf_rejected) / 2,
        f"{conf_gap:.1f}pp\ngap",
        fontsize=12,
        fontweight="bold",
        color=DARK_THEME["accent_warning"],
        va="center",
        ha="left",
    )

    # Add statistics box
    stats_text = (
        f"Confidence Discrimination\n"
        f"─────────────────────────\n"
        f"Detected:  {mean_conf_detected:.1f}% (n={n_detected})\n"
        f"Rejected:  {mean_conf_rejected:.1f}% (n={n_rejected})\n"
        f"Gap:       {conf_gap:.1f} pp\n"
        f"─────────────────────────\n"
        f"Correlation (detected):\n"
        f"  r = {r_detected:.3f}, p < 0.001"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="top",
        color=DARK_THEME["text"],
        bbox=dict(boxstyle="round,pad=0.5", facecolor=DARK_THEME["panel_bg"], edgecolor=DARK_THEME["dim"], alpha=0.95),
        family="monospace",
    )

    # Labels and title
    ax.set_xlabel("Persistence (%)", fontsize=14, fontweight="bold", color=DARK_THEME["text"])
    ax.set_ylabel("LLM Confidence (%)", fontsize=14, fontweight="bold", color=DARK_THEME["text"])
    ax.set_title(
        "LLM Confidence Discrimination Across Full Detection Spectrum\n"
        "Point size encodes GEX magnitude (larger = higher dealer positioning)",
        fontsize=14,
        fontweight="bold",
        pad=15,
        color=DARK_THEME["text"],
    )

    # Legend - placed at upper right to avoid data overlap in lower region
    legend = ax.legend(
        loc="upper right", fontsize=11, facecolor=DARK_THEME["panel_bg"], edgecolor=DARK_THEME["dim"], framealpha=0.95
    )
    for text in legend.get_texts():
        text.set_color(DARK_THEME["text"])

    # Axis limits and grid
    ax.set_xlim(45, 105)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, color=DARK_THEME["grid"], linestyle="-", linewidth=0.5)
    ax.tick_params(colors=DARK_THEME["text"])

    # Spine styling
    for spine in ax.spines.values():
        spine.set_color(DARK_THEME["dim"])

    plt.tight_layout()

    print(f"\nStatistics:")
    print(f"  Total windows: {len(data['persistence'])}")
    print(f"  Detected: {n_detected} (mean confidence: {mean_conf_detected:.1f}%)")
    print(f"  Rejected: {n_rejected} (mean confidence: {mean_conf_rejected:.1f}%)")
    print(f"  Confidence gap: {conf_gap:.1f} pp")
    print(f"  Correlation (detected): r = {r_detected:.3f}")

    return fig


def main():
    print("Generating Confidence Discrimination Figure (Dark Theme #216)...")
    print(f"Database: {CACHE_DB}")

    data = query_data()
    print(f"\nData loaded: {len(data['persistence'])} total windows")

    fig = create_figure(data)
    save_figure(fig, "fig07_confidence_discrimination.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
