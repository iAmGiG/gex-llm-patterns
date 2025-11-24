#!/usr/bin/env python3
"""
Results: From Initial to Validated - PRESENTATION VERSION

Shows the progression from biased prompts to validated methodology:
- Initial (Biased): 100% detection, 96-98% accuracy - but circular?
- Refined (Unbiased): 71.5% detection, 91-92% accuracy - validated!
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# PRESENTATION SETTINGS
plt.rcParams.update(
    {
        "font.size": 20,
        "font.weight": "bold",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    }
)

OUTPUT_DIR = Path("/mnt/bst/yxie2/cregan1/gex-llm-patterns/docs/presentations/oct22_research/diagrams")

# Create figure (16:9)
fig, ax = plt.subplots(figsize=(16, 9), dpi=120)
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")

# Title
fig.text(0.5, 0.93, "Results: From Initial to Validated", ha="center", fontsize=32, fontweight="bold")

# Subtitle
fig.text(
    0.5,
    0.87,
    "Methodology refinement strengthens confidence in structural detection",
    ha="center",
    fontsize=20,
    fontweight="bold",
    color="#003366",
    style="italic",
)

# Table parameters
table_top = 7.3
row_height = 1.4
col_widths = [4.5, 3.5, 4.0, 4.0]
col_positions = [3.5, 6.8, 10.0, 13.0]  # X positions - shifted left more

# Colors
header_color = "#003366"  # Dark blue
header_text = "#FFFFFF"  # White
warning_color = "#FFA500"  # Orange (biased)
validated_color = "#28a745"  # Green (validated)
row_bg_1 = "#fff8e6"  # Light orange background
row_bg_2 = "#e6f7ed"  # Light green background

# Draw header row
header_y = table_top
header_box = Rectangle(
    (1.0, header_y - 0.6), 13.5, row_height - 0.3, facecolor=header_color, edgecolor="#000000", linewidth=3, zorder=2
)
ax.add_patch(header_box)

# Header text
headers = ["Configuration", "Detection Rate", "Predictive Accuracy", "Status"]
for i, (header, x_pos) in enumerate(zip(headers, col_positions)):
    ax.text(
        x_pos, header_y, header, ha="center", va="center", fontsize=20, fontweight="bold", color=header_text, zorder=3
    )

# Row 1: Initial (Biased Prompts)
y_pos_1 = header_y - row_height - 0.2

# Row background
row_bg = Rectangle(
    (1.0, y_pos_1 - 0.6), 13.5, row_height - 0.3, facecolor=row_bg_1, edgecolor="#000000", linewidth=2, zorder=2
)
ax.add_patch(row_bg)

# Configuration
ax.text(
    col_positions[0],
    y_pos_1,
    "Initial\n(Biased Prompts)",
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    color="#000000",
    zorder=3,
)

# Detection Rate
ax.text(
    col_positions[1],
    y_pos_1,
    "100%\n(181/181)",
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    color=warning_color,
    zorder=3,
)

# Accuracy
ax.text(
    col_positions[2],
    y_pos_1,
    "96-98%",
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    color=warning_color,
    zorder=3,
)

# Status - reduced font size to prevent overflow
status_text = "⚠️ Potential\ncircular reasoning"
ax.text(
    col_positions[3],
    y_pos_1,
    status_text,
    ha="center",
    va="center",
    fontsize=17,
    fontweight="bold",
    color=warning_color,
    zorder=3,
)

# Row 2: Refined (Unbiased Prompts)
y_pos_2 = y_pos_1 - row_height - 0.2

# Row background
row_bg2 = Rectangle(
    (1.0, y_pos_2 - 0.6), 13.5, row_height - 0.3, facecolor=row_bg_2, edgecolor="#000000", linewidth=2, zorder=2
)
ax.add_patch(row_bg2)

# Configuration
ax.text(
    col_positions[0],
    y_pos_2,
    "Refined\n(Unbiased Prompts)",
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    color="#000000",
    zorder=3,
)

# Detection Rate
ax.text(
    col_positions[1],
    y_pos_2,
    "71.5%\n(173/242)",
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    color=validated_color,
    zorder=3,
)

# Accuracy
ax.text(
    col_positions[2],
    y_pos_2,
    "91-92%",
    ha="center",
    va="center",
    fontsize=22,
    fontweight="bold",
    color=validated_color,
    zorder=3,
)

# Status - consistent font size
status_text2 = "✓ Validated\nreasoning"
ax.text(
    col_positions[3],
    y_pos_2,
    status_text2,
    ha="center",
    va="center",
    fontsize=17,
    fontweight="bold",
    color=validated_color,
    zorder=3,
)

# Arrow showing progression
arrow_x = 0.5
arrow_y_start = y_pos_1 - 0.3
arrow_y_end = y_pos_2 + 0.3

ax.annotate(
    "",
    xy=(arrow_x, arrow_y_end),
    xytext=(arrow_x, arrow_y_start),
    arrowprops=dict(arrowstyle="->,head_width=0.8,head_length=0.6", color="#003366", linewidth=6),
)
ax.text(
    arrow_x - 0.3,
    (arrow_y_start + arrow_y_end) / 2,
    "Refinement",
    ha="right",
    va="center",
    fontsize=18,
    fontweight="bold",
    color="#003366",
    rotation=90,
)

# Key insights box
insights = (
    "✓ Lower detection rate (71.5% vs 100%) = LLM reasoning, not echoing\n"
    "✓ High accuracy (91-92%) maintained = Predictions still materialize\n"
    "✓ Large sample size (242 days) = Statistically robust"
)
fig.text(
    0.5,
    0.12,
    insights,
    ha="center",
    va="center",
    fontsize=19,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#E8F4F8", edgecolor="#003366", linewidth=3),
)

plt.tight_layout()

# Save
output_file = OUTPUT_DIR / "results_initial_to_validated_1920x1080.png"
plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✅ Results Initial to Validated: {output_file}")

plt.close()
