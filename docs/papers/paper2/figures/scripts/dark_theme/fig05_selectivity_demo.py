#!/usr/bin/env python3
"""
Generate Figure 5: Framework Selectivity Demonstration

Creates a 2x2 panel showing four example windows illustrating regime
classification: detected windows meet all three criteria, while rejected
windows fail on magnitude or stability.

Updated with SpotGamma-inspired dark theme (Issue #216).

Output: docs/papers/paper2/figures/output/fig05_selectivity.png
"""

import matplotlib.pyplot as plt
import numpy as np
from theme import DARK_THEME, OUTPUT_DIR, apply_dark_theme, reset_theme, save_figure


def generate_example_windows():
    """Generate four example windows for selectivity demonstration."""
    np.random.seed(42)

    windows = {}

    # Window 1: DETECTED - 2024 Persistent Negative (meets all criteria)
    # High magnitude (~15B), high persistence (90%), few flips (2)
    gex_2024_persistent = []
    for i in range(30):
        if i in [10, 22]:  # 2 positive days
            gex_2024_persistent.append(np.random.uniform(4, 8))
        else:
            gex_2024_persistent.append(np.random.uniform(-18, -10))
    windows["2024_persistent"] = {
        "gex": gex_2024_persistent,
        "label": "2024 Persistent Negative",
        "status": "DETECTED",
        "persistence": 93.3,
        "magnitude": np.mean(np.abs(gex_2024_persistent)),
        "flips": 2,
        "reason": "All criteria met",
    }

    # Window 2: DETECTED - 2024 Strong Negative (meets all criteria)
    # Very high magnitude (~20B), high persistence (87%), few flips (3)
    gex_2024_strong = []
    for i in range(30):
        if i in [5, 15, 25]:  # 3 positive days
            gex_2024_strong.append(np.random.uniform(3, 7))
        else:
            gex_2024_strong.append(np.random.uniform(-25, -15))
    windows["2024_strong"] = {
        "gex": gex_2024_strong,
        "label": "2024 Strong Negative",
        "status": "DETECTED",
        "persistence": 90.0,
        "magnitude": np.mean(np.abs(gex_2024_strong)),
        "flips": 3,
        "reason": "All criteria met",
    }

    # Window 3: REJECTED - 2020 Low Magnitude (fails magnitude threshold)
    # Low magnitude (~3B), high persistence (90%), few flips (2)
    gex_2020_low = []
    for i in range(30):
        if i in [8, 20]:  # 2 positive days
            gex_2020_low.append(np.random.uniform(1, 3))
        else:
            gex_2020_low.append(np.random.uniform(-4, -2))
    windows["2020_low_mag"] = {
        "gex": gex_2020_low,
        "label": "2020 Low Magnitude",
        "status": "REJECTED",
        "persistence": 93.3,
        "magnitude": np.mean(np.abs(gex_2020_low)),
        "flips": 2,
        "reason": "Magnitude < $5B",
    }

    # Window 4: REJECTED - 2024 Transitional (fails stability)
    # High magnitude (~12B), low persistence (50%), many flips (8)
    gex_2024_unstable = []
    flip_days = [3, 6, 9, 12, 15, 18, 21, 24]  # Alternating pattern
    for i in range(30):
        if i in flip_days or (i % 2 == 0 and i < 15):
            gex_2024_unstable.append(np.random.uniform(8, 15))
        else:
            gex_2024_unstable.append(np.random.uniform(-18, -10))
    windows["2024_unstable"] = {
        "gex": gex_2024_unstable,
        "label": "2024 Transitional",
        "status": "REJECTED",
        "persistence": 50.0,
        "magnitude": np.mean(np.abs(gex_2024_unstable)),
        "flips": 8,
        "reason": "Too many sign flips",
    }

    return windows


def create_figure(windows):
    """Create selectivity demonstration figure with dark theme."""

    # Set dark theme
    apply_dark_theme()

    # Create 2x2 subplot grid
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    fig.patch.set_facecolor(DARK_THEME["background"])

    # Flatten for easier iteration
    axes_flat = axes.flatten()
    window_keys = ["2024_persistent", "2024_strong", "2020_low_mag", "2024_unstable"]

    for ax, key in zip(axes_flat, window_keys):
        window = windows[key]
        gex = window["gex"]

        ax.set_facecolor(DARK_THEME["background"])

        # Create bar colors based on sign
        colors = [DARK_THEME["accent_positive"] if v > 0 else DARK_THEME["accent_negative"] for v in gex]

        # Plot bars
        days = np.arange(1, 31)
        bars = ax.bar(days, gex, color=colors, width=0.8, edgecolor=DARK_THEME["background"], linewidth=0.3, alpha=0.9)

        # Add zero line
        ax.axhline(0, color=DARK_THEME["dim"], linestyle="-", linewidth=1)

        # Add $5B threshold lines
        ax.axhline(-5, color=DARK_THEME["accent_warning"], linestyle="--", linewidth=1.2, alpha=0.6)
        ax.axhline(5, color=DARK_THEME["accent_warning"], linestyle="--", linewidth=1.2, alpha=0.6)

        # Status badge color
        if window["status"] == "DETECTED":
            badge_color = DARK_THEME["detected_border"]
            border_color = DARK_THEME["detected_border"]
        else:
            badge_color = DARK_THEME["rejected_border"]
            border_color = DARK_THEME["rejected_border"]

        # Add border to indicate status
        for spine in ax.spines.values():
            spine.set_color(border_color)
            spine.set_linewidth(3)

        # Title with status badge
        ax.set_title(
            f"{window['label']}\n[{window['status']}]", fontsize=12, fontweight="bold", color=badge_color, pad=10
        )

        # Stats annotation
        stats_text = (
            f"Persistence: {window['persistence']:.1f}%\n"
            f"Magnitude: ${window['magnitude']:.1f}B\n"
            f"Sign Flips: {window['flips']}\n"
            f"─────────────\n"
            f"{window['reason']}"
        )

        # Position stats box
        ax.text(
            0.98,
            0.98,
            stats_text,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment="top",
            horizontalalignment="right",
            color=DARK_THEME["text"],
            bbox=dict(
                boxstyle="round,pad=0.4",
                facecolor=DARK_THEME["panel_bg"],
                edgecolor=badge_color,
                linewidth=1.5,
                alpha=0.95,
            ),
            family="monospace",
        )

        # Axis formatting
        ax.set_xlim(0, 31)
        ax.set_xticks([1, 10, 20, 30])
        ax.tick_params(colors=DARK_THEME["text"], labelsize=10)
        ax.grid(axis="y", alpha=0.2, color=DARK_THEME["grid"], linestyle="-")

        # Labels
        ax.set_xlabel("Day", fontsize=11, color=DARK_THEME["text"])
        ax.set_ylabel("GEX ($B)", fontsize=11, color=DARK_THEME["text"])

    # Main title
    fig.suptitle(
        "Framework Selectivity Demonstration\n" "Detected Windows (Green Border) vs Rejected Windows (Red Border)",
        fontsize=14,
        fontweight="bold",
        color=DARK_THEME["text"],
        y=0.98,
    )

    # Criteria legend at bottom
    criteria_text = "Detection Criteria: Persistence > 70% same sign  |  " "Avg Magnitude > $5B  |  ≤5 Sign Flips"
    fig.text(0.5, 0.02, criteria_text, ha="center", va="bottom", fontsize=10, color=DARK_THEME["dim"], style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 0.95])

    return fig


def main():
    print("Generating Selectivity Demonstration Figure (Dark Theme #216)...")

    windows = generate_example_windows()
    fig = create_figure(windows)
    save_figure(fig, "fig05_selectivity.png")

    print("\nWindow Summary:")
    for key, window in windows.items():
        print(f"  {window['label']}: {window['status']} - {window['reason']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
