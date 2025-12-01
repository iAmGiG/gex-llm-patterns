#!/usr/bin/env python3
"""
GEX ≠ Gamma (The Greek) - APPENDIX SLIDE

Clarifies the critical distinction between:
- Gamma (individual option metric)
- GEX (aggregate market exposure metric)

For CS/ML audience unfamiliar with options trading terminology.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

# PRESENTATION SETTINGS
plt.rcParams.update(
    {
        "font.size": 18,
        "font.weight": "bold",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)

OUTPUT_DIR = Path("/mnt/bst/yxie2/cregan1/gex-llm-patterns/docs/presentations/oct22_research/diagrams")

# Create figure (16:9)
fig = plt.figure(figsize=(16, 9), dpi=120)
ax = fig.add_subplot(111)
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")

# Main title
fig.text(0.5, 0.95, "GEX ≠ Gamma (The Greek)", ha="center", fontsize=32, fontweight="bold")

# Subtitle
fig.text(0.5, 0.90, "Understanding the critical distinction", ha="center", fontsize=20, color="#003366", style="italic")

# ============ LEFT SIDE: GAMMA (THE GREEK) ============
left_x = 3.5
col_width = 5.5
box_height = 5.5

# Header
left_header = FancyBboxPatch(
    (0.75, 7.5),
    col_width,
    0.6,
    boxstyle="round,pad=0.1",
    facecolor="#E8F4F8",
    edgecolor="#003366",
    linewidth=4,
    zorder=2,
)
ax.add_patch(left_header)
ax.text(left_x, 7.75, "Gamma (Γ) - The Greek", ha="center", fontsize=24, fontweight="bold", color="#003366", zorder=4)

# Content box
left_box = FancyBboxPatch(
    (0.75, 2.0),
    col_width,
    5.2,
    boxstyle="round,pad=0.1",
    facecolor="#f5f5f5",
    edgecolor="#000000",
    linewidth=3,
    zorder=2,
)
ax.add_patch(left_box)

# Content
gamma_text = (
    "Individual Option Metric\n\n"
    "Measures:\n"
    "Rate of delta change\n\n"
    "Units:\n"
    "Delta per $1 move\n\n"
    "Scale:\n"
    "0 to ~1.0 per contract\n\n"
    "Who uses it:\n"
    "Individual traders\n"
    "sizing positions"
)

ax.text(left_x, 4.5, gamma_text, ha="center", va="center", fontsize=17, color="#000000", zorder=4, linespacing=1.6)

# Small circle visual
small_circle = Circle((left_x, 8.6), 0.3, facecolor="#003366", edgecolor="#000000", linewidth=2, alpha=0.7, zorder=3)
ax.add_patch(small_circle)
ax.text(left_x, 8.6, "γ", ha="center", va="center", fontsize=20, color="white", fontweight="bold", zorder=4)

# ============ MIDDLE: TRANSFORMATION ============

# Arrow showing aggregation
arrow = FancyArrowPatch(
    (6.5, 4.5), (9.5, 4.5), arrowstyle="->,head_width=0.8,head_length=0.6", color="#8B0000", linewidth=6, zorder=3
)
ax.add_patch(arrow)

# Formula box
formula_text = "Σ (Γ × OI × S²)"
ax.text(
    8.0,
    5.3,
    formula_text,
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    family="monospace",
    color="#8B0000",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFE5B4", edgecolor="#8B0000", linewidth=2),
    zorder=4,
)

ax.text(
    8.0,
    3.8,
    "Aggregate\nacross ALL\nstrikes",
    ha="center",
    va="center",
    fontsize=14,
    color="#8B0000",
    fontweight="bold",
    style="italic",
    zorder=4,
)

# ============ RIGHT SIDE: GEX (GAMMA EXPOSURE) ============
right_x = 12.5

# Header
right_header = FancyBboxPatch(
    (9.75, 7.5),
    col_width,
    0.6,
    boxstyle="round,pad=0.1",
    facecolor="#FFE5B4",
    edgecolor="#8B0000",
    linewidth=4,
    zorder=2,
)
ax.add_patch(right_header)
ax.text(right_x, 7.75, "GEX - Gamma Exposure", ha="center", fontsize=24, fontweight="bold", color="#8B0000", zorder=4)

# Content box
right_box = FancyBboxPatch(
    (9.75, 2.0),
    col_width,
    5.2,
    boxstyle="round,pad=0.1",
    facecolor="#fff8e6",
    edgecolor="#000000",
    linewidth=3,
    zorder=2,
)
ax.add_patch(right_box)

# Content
gex_text = (
    "Aggregate Market Metric\n\n"
    "Measures:\n"
    "Total dealer gamma position\n\n"
    "Units:\n"
    "Dollars of hedging flow\n"
    "per 1% move\n\n"
    "Scale:\n"
    "Billions of dollars\n"
    "(-$50B\\ to +$50B)\n\n"
    "Who uses it:\n"
    "Market structure analysts"
)

ax.text(
    right_x,
    4.6,
    gex_text,
    ha="center",
    va="center",
    fontsize=17,
    color="#8B0000",
    fontweight="bold",
    zorder=4,
    linespacing=1.6,
)

# Large circle visual
large_circle = Circle((right_x, 8.62), 0.37, facecolor="#8B0000", edgecolor="#000000", linewidth=2, alpha=0.7, zorder=3)
ax.add_patch(large_circle)
ax.text(right_x, 8.62, "GEX", ha="center", va="center", fontsize=20, color="white", fontweight="bold", zorder=4)

# ============ BOTTOM: KEY INSIGHT ============

insight = (
    "GEX tells us: How many billions must dealers trade if SPY moves 1%?\n\n"
    "Negative GEX (-$32B): Dealers AMPLIFY moves (buy rallies, sell dips)\n"
    "Positive GEX (+$20B): Dealers DAMPEN moves (sell rallies, buy dips)"
)

fig.text(
    0.5,
    0.08,
    insight,
    ha="center",
    fontsize=18,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#e6f3ff", edgecolor="#003366", linewidth=3),
)

plt.tight_layout()

# Save
output_file = OUTPUT_DIR / "gex_vs_gamma_appendix_1920x1080.png"
plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✅ GEX vs Gamma Appendix: {output_file}")

plt.close()
