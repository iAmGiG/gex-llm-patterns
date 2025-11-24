#!/usr/bin/env python3
"""
Methodology Overview - PRESENTATION VERSION

Shows the novel obfuscation testing methodology (before/after comparison).
This is your key academic contribution.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# PRESENTATION SETTINGS
plt.rcParams.update(
    {
        "font.size": 16,
        "font.weight": "normal",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)

OUTPUT_DIR = Path("/mnt/bst/yxie2/cregan1/gex-llm-patterns/docs/presentations/oct22_research/diagrams")

# Create figure (16:9)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 9), dpi=120)

# Colors
removed_color = "#ffcccc"  # Light red for removed
kept_color = "#ccffcc"  # Light green for kept
edge_color = "#000000"


def draw_data_box(ax, title, items, colors):
    """Draw a data representation box"""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(5, 9, title, ha="center", fontsize=24, fontweight="bold")

    # Draw items
    y_pos = 7.5
    for item, color in zip(items, colors):
        # Box
        box = Rectangle((1, y_pos - 0.4), 8, 0.8, facecolor=color, edgecolor=edge_color, linewidth=2)
        ax.add_patch(box)

        # Text
        ax.text(5, y_pos, item, ha="center", va="center", fontsize=18, fontweight="bold", color="#000000")

        y_pos -= 1.2


# LEFT: Before Obfuscation (Standard LLM Input)
before_items = [
    "Date: 2024-01-02",
    "Ticker: SPY",
    "Event: Post-holiday trading",
    "Net GEX: -$32.5B",
    "Spot: $472.87",
]
before_colors = [removed_color, removed_color, removed_color, kept_color, kept_color]

draw_data_box(ax1, "BEFORE\nObfuscation", before_items, before_colors)

# Add "REMOVED" and "KEPT" labels on left side
ax1.text(0.5, 7.5, "X\nREMOVED", ha="center", va="center", fontsize=16, fontweight="bold", color="#8B0000")
ax1.text(0.5, 4.3, "✓\nKEPT", ha="center", va="center", fontsize=16, fontweight="bold", color="#006400")

# RIGHT: After Obfuscation (Novel Methodology)
after_items = [
    "Date: T+0",
    "Ticker: INDEX_1",
    "Event: [REDACTED]",
    "Net GEX: -$32.5B",
    "Spot: $472.87",
]
after_colors = [removed_color, removed_color, removed_color, kept_color, kept_color]

draw_data_box(ax2, "AFTER\nObfuscation", after_items, after_colors)

# Add arrow between panels
fig.text(0.5, 0.5, "→", ha="center", va="center", fontsize=100, fontweight="bold", color="#003366")

# Main title
fig.suptitle("Obfuscation Testing: Isolating Structural Pattern Detection", fontsize=28, fontweight="bold", y=0.98)

# Bottom explanation
explanation = (
    "REMOVES temporal/contextual cues  |  PRESERVES market microstructure\n"
    "Result: LLM detects patterns via GEX mechanics, not memorization"
)
fig.text(
    0.5,
    0.08,
    explanation,
    ha="center",
    fontsize=18,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.8", facecolor="#fff3cd", edgecolor="#856404", linewidth=2.5),
)

# Validation result
result = "✓ All 3 patterns passed: 67-78% detection (>60% threshold)"
fig.text(0.5, 0.02, result, ha="center", fontsize=20, fontweight="bold", color="#006400")

plt.tight_layout(rect=[0, 0.12, 1, 0.95])

# Save
output_file = OUTPUT_DIR / "methodology_presentation_1920x1080.png"
plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✅ Methodology: {output_file}")

plt.close()
