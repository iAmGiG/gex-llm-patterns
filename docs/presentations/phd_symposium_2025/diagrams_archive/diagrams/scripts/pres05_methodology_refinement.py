#!/usr/bin/env python3
"""
Methodology Refinement Slide - PRESENTATION VERSION

Shows the evolution from biased to unbiased prompts:
- Initial approach: Included regime labels (100% detection - but circular?)
- Refined approach: Removed all hints (71.5% detection - proves true reasoning)
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

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
fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(16, 9), dpi=120)

for ax in [ax_left, ax_right]:
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

# Colors
biased_color = "#FFA500"  # Orange (warning)
unbiased_color = "#28a745"  # Green (good)
problem_color = "#dc3545"  # Red
box_bg = "#f5f5f5"  # Light gray

# ============ LEFT COLUMN: BIASED APPROACH ============

# Header
ax_left.text(
    5,
    9.2,
    "Initial Approach (Biased)",
    ha="center",
    fontsize=24,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFE5B4", edgecolor=biased_color, linewidth=4),
)

# Problem statement
problem_box = FancyBboxPatch(
    (1, 7.5), 8, 1.2, boxstyle="round,pad=0.1", facecolor="#ffe6e6", edgecolor=problem_color, linewidth=3
)
ax_left.add_patch(problem_box)
ax_left.text(5, 8.1, "Prompt included regime labels", ha="center", fontsize=20, fontweight="bold", color=problem_color)

# Example prompt box
example_box = FancyBboxPatch(
    (0.5, 5.0), 9, 2.2, boxstyle="round,pad=0.1", facecolor=box_bg, edgecolor="#000000", linewidth=3
)
ax_left.add_patch(example_box)

ax_left.text(5, 6.8, "Example Prompt:", ha="center", fontsize=18, fontweight="bold", style="italic")

# Highlight the problem
prompt_text = '"Given NEGATIVE gamma regime...\n' "Net GEX: -$8.95B\n" 'What pattern do you detect?"'
ax_left.text(
    5,
    5.8,
    prompt_text,
    ha="center",
    va="center",
    fontsize=18,
    family="monospace",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff", edgecolor=problem_color, linewidth=2),
)

# Highlight the bias
ax_left.annotate(
    "",
    xy=(8.5, 6.5),
    xytext=(10, 7.0),
    arrowprops=dict(arrowstyle="->,head_width=0.5,head_length=0.4", color=problem_color, linewidth=4),
)
ax_left.text(
    10.5, 7.0, "Tells LLM\nthe answer!", ha="left", va="center", fontsize=16, fontweight="bold", color=problem_color
)

# Result box
result_box = FancyBboxPatch(
    (1.5, 2.5), 7, 2.0, boxstyle="round,pad=0.1", facecolor="#ffe6e6", edgecolor=problem_color, linewidth=4
)
ax_left.add_patch(result_box)

ax_left.text(5, 3.8, "Result:", ha="center", fontsize=20, fontweight="bold")
ax_left.text(5, 3.2, "100% Detection Rate", ha="center", fontsize=22, fontweight="bold", color=problem_color)

# Question mark
ax_left.text(
    5,
    1.8,
    "(But is this circular reasoning?)",
    ha="center",
    fontsize=18,
    fontweight="bold",
    color=problem_color,
    style="italic",
)

# X mark at bottom
ax_left.text(5, 0.8, "⚠️ POTENTIAL BIAS", ha="center", fontsize=20, fontweight="bold", color=problem_color)

# ============ RIGHT COLUMN: UNBIASED APPROACH ============

# Header
ax_right.text(
    5,
    9.2,
    "Refined Approach (Unbiased)",
    ha="center",
    fontsize=24,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#d4edda", edgecolor=unbiased_color, linewidth=4),
)

# Solution statement
solution_box = FancyBboxPatch(
    (1, 7.5), 8, 1.2, boxstyle="round,pad=0.1", facecolor="#d4edda", edgecolor=unbiased_color, linewidth=3
)
ax_right.add_patch(solution_box)
ax_right.text(5, 8.1, "Removed all regime hints", ha="center", fontsize=20, fontweight="bold", color=unbiased_color)

# Example prompt box
example_box2 = FancyBboxPatch(
    (0.5, 5.0), 9, 2.2, boxstyle="round,pad=0.1", facecolor=box_bg, edgecolor="#000000", linewidth=3
)
ax_right.add_patch(example_box2)

ax_right.text(5, 6.8, "Example Prompt:", ha="center", fontsize=18, fontweight="bold", style="italic")

# Clean prompt
prompt_text2 = '"Given these GEX metrics:\n' "Net GEX: -$8.95B\n" 'What pattern do you detect?"'
ax_right.text(
    5,
    5.8,
    prompt_text2,
    ha="center",
    va="center",
    fontsize=18,
    family="monospace",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff", edgecolor=unbiased_color, linewidth=2),
)

# Highlight the fix
ax_right.annotate(
    "",
    xy=(8.5, 6.5),
    xytext=(10, 7.0),
    arrowprops=dict(arrowstyle="->,head_width=0.5,head_length=0.4", color=unbiased_color, linewidth=4),
)
ax_right.text(
    10.5, 7.0, "LLM must\nreason!", ha="left", va="center", fontsize=16, fontweight="bold", color=unbiased_color
)

# Result box
result_box2 = FancyBboxPatch(
    (1.5, 2.5), 7, 2.0, boxstyle="round,pad=0.1", facecolor="#d4edda", edgecolor=unbiased_color, linewidth=4
)
ax_right.add_patch(result_box2)

ax_right.text(5, 3.8, "Result:", ha="center", fontsize=20, fontweight="bold")
ax_right.text(5, 3.2, "71.5% Detection Rate", ha="center", fontsize=22, fontweight="bold", color=unbiased_color)

# Check mark
ax_right.text(
    5,
    1.8,
    "(Proves true structural reasoning)",
    ha="center",
    fontsize=18,
    fontweight="bold",
    color=unbiased_color,
    style="italic",
)

# Checkmark at bottom
ax_right.text(5, 0.8, "✓ RIGOROUS METHODOLOGY", ha="center", fontsize=20, fontweight="bold", color=unbiased_color)

# Main title
fig.suptitle("Testing for Prompt Bias: Methodology Refinement", fontsize=32, fontweight="bold", y=0.98)

# Bottom explanation
explanation = (
    "Lower detection rate (71.5% vs 100%) actually STRENGTHENS the finding:\n"
    "Proves LLM is reasoning about GEX structure, not just echoing prompt labels"
)
fig.text(
    0.5,
    0.04,
    explanation,
    ha="center",
    fontsize=18,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.5", facecolor="#E8F4F8", edgecolor="#003366", linewidth=3),
)

plt.tight_layout(rect=[0, 0.08, 1, 0.95])

# Save
output_file = OUTPUT_DIR / "methodology_refinement_1920x1080.png"
plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✅ Methodology Refinement: {output_file}")

plt.close()
