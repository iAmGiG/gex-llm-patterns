#!/usr/bin/env python3
"""
Generate Borderline Persistence Region Detail Figure (Issue #212)

Creates multi-panel visualization showing confidence discrimination
in the borderline persistence region (68-72%).

Updated with SpotGamma-inspired dark theme (Issue #216).

Output: docs/papers/paper2/figures/output/fig10_borderline_persistence.png
"""

import json
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from theme import CACHE_DB, DARK_THEME, OUTPUT_DIR, apply_dark_theme, reset_theme, save_figure


def query_data():
    """Query persistence and confidence data from ResearchCache."""
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
    """Create multi-panel borderline persistence figure with dark theme."""

    # Filter borderline region (68-72%)
    borderline_mask = (data["persistence"] >= 68) & (data["persistence"] <= 72)
    bl_persistence = data["persistence"][borderline_mask]
    bl_confidence = data["confidence"][borderline_mask]
    bl_detected = data["detected"][borderline_mask]

    # Wider region for scatterplot (65-75%)
    wide_mask = (data["persistence"] >= 65) & (data["persistence"] <= 75)
    wide_persistence = data["persistence"][wide_mask]
    wide_confidence = data["confidence"][wide_mask]
    wide_detected = data["detected"][wide_mask]
    wide_magnitude = data["magnitude"][wide_mask]

    # Statistics
    bl_detected_mask = bl_detected == 1
    bl_rejected_mask = bl_detected == 0
    n_detected = bl_detected_mask.sum()
    n_rejected = bl_rejected_mask.sum()
    mean_conf_detected = bl_confidence[bl_detected_mask].mean() if n_detected > 0 else 0
    mean_conf_rejected = bl_confidence[bl_rejected_mask].mean() if n_rejected > 0 else 0
    std_conf_detected = bl_confidence[bl_detected_mask].std() if n_detected > 0 else 0
    std_conf_rejected = bl_confidence[bl_rejected_mask].std() if n_rejected > 0 else 0

    # Set dark theme
    apply_dark_theme()

    # Create figure with 3 panels
    fig = plt.figure(figsize=(16, 6), dpi=300)
    fig.patch.set_facecolor(DARK_THEME["background"])

    # Panel A: Confidence Distribution Histogram
    ax1 = fig.add_subplot(131)
    ax1.set_facecolor(DARK_THEME["background"])

    bins = np.arange(0, 105, 10)
    ax1.hist(
        bl_confidence[bl_rejected_mask],
        bins=bins,
        alpha=0.7,
        label=f"Rejected (n={n_rejected})",
        color=DARK_THEME["accent_negative"],
        edgecolor=DARK_THEME["background"],
        linewidth=0.8,
    )
    ax1.hist(
        bl_confidence[bl_detected_mask],
        bins=bins,
        alpha=0.7,
        label=f"Detected (n={n_detected})",
        color=DARK_THEME["accent_positive"],
        edgecolor=DARK_THEME["background"],
        linewidth=0.8,
    )

    # Mean lines
    ax1.axvline(
        mean_conf_rejected,
        color=DARK_THEME["accent_negative"],
        linestyle="--",
        linewidth=2,
        label=f"Rejected Mean: {mean_conf_rejected:.1f}%",
    )
    ax1.axvline(
        mean_conf_detected,
        color=DARK_THEME["accent_positive"],
        linestyle="--",
        linewidth=2,
        label=f"Detected Mean: {mean_conf_detected:.1f}%",
    )

    ax1.set_xlabel("LLM Confidence (%)", fontsize=11, fontweight="bold", color=DARK_THEME["text"])
    ax1.set_ylabel("Count", fontsize=11, fontweight="bold", color=DARK_THEME["text"])
    ax1.set_title(
        "A: Confidence Distribution\n(Borderline 68-72% Persistence)",
        fontsize=12,
        fontweight="bold",
        color=DARK_THEME["text"],
    )
    legend1 = ax1.legend(loc="upper left", fontsize=11, facecolor=DARK_THEME["background"], edgecolor=DARK_THEME["dim"])
    for text in legend1.get_texts():
        text.set_color(DARK_THEME["text"])
    ax1.set_xlim(0, 100)
    ax1.grid(True, alpha=0.3, color=DARK_THEME["grid"])
    ax1.tick_params(colors=DARK_THEME["text"])
    for spine in ax1.spines.values():
        spine.set_color(DARK_THEME["dim"])

    # Panel B: Zoomed Scatterplot
    ax2 = fig.add_subplot(132)
    ax2.set_facecolor(DARK_THEME["background"])

    # Size based on magnitude (normalized)
    sizes = (wide_magnitude / wide_magnitude.max()) * 150 + 20

    # Plot rejected first (background)
    rejected_mask = wide_detected == 0
    ax2.scatter(
        wide_persistence[rejected_mask],
        wide_confidence[rejected_mask],
        s=sizes[rejected_mask],
        c=DARK_THEME["accent_negative"],
        alpha=0.6,
        label="Rejected",
        edgecolors=DARK_THEME["background"],
        linewidths=0.5,
    )

    # Plot detected on top
    detected_mask = wide_detected == 1
    ax2.scatter(
        wide_persistence[detected_mask],
        wide_confidence[detected_mask],
        s=sizes[detected_mask],
        c=DARK_THEME["accent_positive"],
        alpha=0.8,
        label="Detected",
        edgecolors=DARK_THEME["background"],
        linewidths=0.5,
    )

    # 70% threshold line
    ax2.axvline(70, color=DARK_THEME["accent_neutral"], linestyle="--", linewidth=2.5, label="70% Threshold", zorder=10)

    # Highlight borderline region
    ax2.axvspan(68, 72, alpha=0.2, color=DARK_THEME["accent_warning"], label="Borderline Region")

    ax2.set_xlabel("Persistence (%)", fontsize=11, fontweight="bold", color=DARK_THEME["text"])
    ax2.set_ylabel("LLM Confidence (%)", fontsize=11, fontweight="bold", color=DARK_THEME["text"])
    ax2.set_title(
        "B: Threshold Crossing Detail\n(65-75% Persistence Range)",
        fontsize=12,
        fontweight="bold",
        color=DARK_THEME["text"],
    )
    legend2 = ax2.legend(
        loc="upper right", fontsize=11, facecolor=DARK_THEME["background"], edgecolor=DARK_THEME["dim"]
    )
    for text in legend2.get_texts():
        text.set_color(DARK_THEME["text"])
    ax2.set_xlim(64, 76)
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3, color=DARK_THEME["grid"])
    ax2.tick_params(colors=DARK_THEME["text"])
    for spine in ax2.spines.values():
        spine.set_color(DARK_THEME["dim"])

    # Panel C: Statistical Summary
    ax3 = fig.add_subplot(133)
    ax3.set_facecolor(DARK_THEME["background"])
    ax3.axis("off")

    # Calculate gap
    gap = mean_conf_detected - mean_conf_rejected

    # Get full-spectrum stats for comparison
    all_detected = data["detected"] == 1
    all_rejected = data["detected"] == 0
    full_gap = data["confidence"][all_detected].mean() - data["confidence"][all_rejected].mean()

    summary_text = f"""
    BORDERLINE PERSISTENCE REGION (68-72%)
    ══════════════════════════════════════

    Total Windows:           {len(bl_persistence):>6}
    ├─ Detected:             {n_detected:>6}  ({n_detected/len(bl_persistence)*100:.1f}%)
    └─ Rejected:             {n_rejected:>6}  ({n_rejected/len(bl_persistence)*100:.1f}%)


    CONFIDENCE DISCRIMINATION
    ─────────────────────────────────────

    Detected Mean:       {mean_conf_detected:>6.1f}%  (±{std_conf_detected:.1f}%)
    Rejected Mean:       {mean_conf_rejected:>6.1f}%  (±{std_conf_rejected:.1f}%)
    ─────────────────────────────────────
    Borderline Gap:      {gap:>+6.1f} pp


    COMPARISON TO FULL SPECTRUM
    ─────────────────────────────────────

    Full-Spectrum Gap:   {full_gap:>+6.1f} pp
    Borderline Gap:      {gap:>+6.1f} pp

    → Discrimination persists at threshold
    → Confidence tracks regime quality
      even in ambiguous cases
    """

    ax3.text(
        0.05,
        0.95,
        summary_text,
        transform=ax3.transAxes,
        fontsize=11,
        fontfamily="monospace",
        verticalalignment="top",
        color=DARK_THEME["text"],
        bbox=dict(boxstyle="round,pad=0.5", facecolor=DARK_THEME["panel_bg"], edgecolor=DARK_THEME["dim"], linewidth=1),
    )

    ax3.set_title("C: Statistical Summary", fontsize=12, fontweight="bold", x=0.5, y=0.98, color=DARK_THEME["text"])

    plt.tight_layout()

    print(f"\nBorderline Statistics (68-72% persistence):")
    print(f"  Total: {len(bl_persistence)} windows")
    print(f"  Detected: {n_detected} ({n_detected/len(bl_persistence)*100:.1f}%)")
    print(f"  Rejected: {n_rejected} ({n_rejected/len(bl_persistence)*100:.1f}%)")
    print(f"  Mean confidence - Detected: {mean_conf_detected:.1f}% (±{std_conf_detected:.1f}%)")
    print(f"  Mean confidence - Rejected: {mean_conf_rejected:.1f}% (±{std_conf_rejected:.1f}%)")
    print(f"  Discrimination gap: {gap:+.1f} pp")
    print(f"  Full-spectrum gap: {full_gap:+.1f} pp")

    return fig


def main():
    print("Generating Borderline Persistence Region Figure (Issue #212, Dark Theme #216)...")
    print(f"Database: {CACHE_DB}")

    # Query data
    data = query_data()
    print(f"\nData loaded: {len(data['persistence'])} total windows")

    # Create figure
    fig = create_figure(data)
    save_figure(fig, "fig10_borderline_persistence.png")

    print("\nDone!")


if __name__ == "__main__":
    main()
