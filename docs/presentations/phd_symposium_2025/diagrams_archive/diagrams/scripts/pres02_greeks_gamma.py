#!/usr/bin/env python3
"""
The Greeks: Why Gamma Matters - PRESENTATION VERSION

Simple explanation of Delta and Gamma:
- Delta = Stock equivalence (how much exposure)
- Gamma = How fast exposure changes (URGENCY of hedging)

Visual: Gamma as "Urgency Beacon"
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
fig.text(0.5, 0.95, 'Options Risk Metrics: The "Greeks"', ha="center", fontsize=32, fontweight="bold")

# Subtitle
fig.text(0.5, 0.90, "Two metrics you need to understand", ha="center", fontsize=22, color="#003366", style="italic")

# ============ LEFT SIDE: DELTA ============
left_x = 4

# Delta header box
delta_header = FancyBboxPatch(
    (1, 7.5), 6, 0.6, boxstyle="round,pad=0.1", facecolor="#E8F4F8", edgecolor="#003366", linewidth=4
)
ax.add_patch(delta_header)
ax.text(left_x, 7.70, "Delta (Δ): Stock Equivalence", ha="center", fontsize=24, fontweight="bold", color="#003366")

# Delta explanation box
delta_box = FancyBboxPatch(
    (1, 4.80), 6, 2.2, boxstyle="round,pad=0.1", facecolor="#f5f5f5", edgecolor="#000000", linewidth=3
)
ax.add_patch(delta_box)

ax.text(left_x, 6.7, "HOW MUCH exposure you have", ha="center", fontsize=20, fontweight="bold", color="#000000")

ax.text(left_x, 6.1, "Range: 0 to 1.0 for calls", ha="center", fontsize=18, color="#333333")

# Example box
example_box = FancyBboxPatch(
    (1.1, 5.3), 5.75, 0.6, boxstyle="round,pad=0.05", facecolor="#fff", edgecolor="#003366", linewidth=2
)
ax.add_patch(example_box)
ax.text(
    left_x,
    5.6,
    "Example: Δ = 0.50 = owning 50 shares",
    ha="center",
    fontsize=18,
    fontweight="bold",
    family="monospace",
    color="#003366",
)

# ============ RIGHT SIDE: GAMMA (URGENCY BEACON) ============
right_x = 12

# Gamma header box
gamma_header = FancyBboxPatch(
    (9, 7.5), 6, 0.6, boxstyle="round,pad=0.1", facecolor="#FFE5B4", edgecolor="#8B0000", linewidth=4
)
ax.add_patch(gamma_header)
ax.text(right_x, 7.70, "Gamma (Γ): Urgency Beacon", ha="center", fontsize=24, fontweight="bold", color="#8B0000")

# Gamma explanation box
gamma_box = FancyBboxPatch(
    (9, 4.8), 6, 2.2, boxstyle="round,pad=0.1", facecolor="#f5f5f5", edgecolor="#000000", linewidth=3
)
ax.add_patch(gamma_box)

ax.text(right_x, 6.7, "HOW FAST exposure changes", ha="center", fontsize=20, fontweight="bold", color="#000000")

ax.text(right_x, 6.1, "High gamma = URGENT rehedging", ha="center", fontsize=18, color="#8B0000", fontweight="bold")

# Example box
example_box2 = FancyBboxPatch(
    (9.3, 5.3), 5.4, 0.6, boxstyle="round,pad=0.05", facecolor="#fff", edgecolor="#8B0000", linewidth=2
)
ax.add_patch(example_box2)
ax.text(
    right_x,
    5.6,
    "Stock moves $1 → Δ changes by Γ",
    ha="center",
    fontsize=18,
    fontweight="bold",
    family="monospace",
    color="#8B0000",
)

# ============ URGENCY SCALE (BOTTOM) ============

urgency_y = 3.0

# Title
ax.text(8, 4.2, "Gamma Urgency Scale", ha="center", fontsize=24, fontweight="bold", color="#000000")

# Three urgency levels
urgency_levels = [
    (2.5, "LOW\nGAMMA", "Leisurely\nrehedging", "#28a745", 1.5),
    (8, "HIGH\nGAMMA", "Urgent\nrehedging", "#FFA500", 2),
    (13.5, "EXTREME\n(0DTE)", "\nCONSTANT\nrehedging", "#dc3545", 2.35),
]

for x, level, desc, color, intensity in urgency_levels:
    # Circle representing urgency (size = intensity)
    circle = Circle((x, urgency_y), 0.4 * intensity, facecolor=color, edgecolor="#000000", linewidth=3, alpha=0.7)
    ax.add_patch(circle)

    # Level label
    ax.text(x, urgency_y, level, ha="center", va="center", fontsize=18, fontweight="bold", color="#000000")

    # Description
    ax.text(x, urgency_y - 1.0, desc, ha="center", va="center", fontsize=16, fontweight="bold", color=color)

# Arrows showing progression
for i in range(len(urgency_levels) - 1):
    x1 = urgency_levels[i][0] + 1.0
    x2 = urgency_levels[i + 1][0] - 1.0
    arrow = FancyArrowPatch(
        (x1, urgency_y), (x2, urgency_y), arrowstyle="->,head_width=0.6,head_length=0.4", color="#000000", linewidth=4
    )
    ax.add_patch(arrow)

# Bottom key insight
insight = (
    "Gamma is the CRITICAL metric for our research\n"
    "High gamma = Dealers must rehedge constantly = Mechanical constraint we detect"
)
fig.text(
    0.5,
    0.08,
    insight,
    ha="center",
    fontsize=20,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFE5B4", edgecolor="#8B0000", linewidth=3),
)

plt.tight_layout()

# Save
output_file = OUTPUT_DIR / "greeks_gamma_urgency_1920x1080.png"
plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✅ Greeks - Gamma Urgency: {output_file}")

plt.close()
