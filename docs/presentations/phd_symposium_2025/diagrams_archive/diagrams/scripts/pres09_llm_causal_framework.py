#!/usr/bin/env python3
"""
LLM as Causal Framework Detector - PRESENTATION VERSION

Shows actual example from validation:
- LEFT: What LLM received (obfuscated data only)
- MIDDLE: Causal framework detected (WHO → WHOM → WHAT)
- RIGHT: What happened next (outcome verification)

Uses real data from Jan 2, 2024 (gamma_positioning pattern)
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

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
fig.text(
    0.5, 0.95, "Beyond Prediction: LLMs as Causal Framework Detectors", ha="center", fontsize=30, fontweight="bold"
)

# Subtitle
fig.text(
    0.5,
    0.90,
    'Real example from validation (Jan 2, 2024 - obfuscated as "Day T+0")',
    ha="center",
    fontsize=20,
    color="#003366",
    style="italic",
)

# ============ LEFT COLUMN: WHAT LLM RECEIVED ============
left_x = 2.5
col_width = 4.5
box_height = 6.5

# Header
left_header = FancyBboxPatch(
    (0.25, 7.5),
    col_width,
    0.6,
    boxstyle="round,pad=0.1",
    facecolor="#E8F4F8",
    edgecolor="#003366",
    linewidth=4,
    zorder=2,
)
ax.add_patch(left_header)
ax.text(left_x, 7.75, "What LLM Received", ha="center", fontsize=22, fontweight="bold", color="#003366", zorder=4)

# Content box
left_box = FancyBboxPatch(
    (0.25, 1.0),
    col_width,
    6.2,
    boxstyle="round,pad=0.1",
    facecolor="#f5f5f5",
    edgecolor="#000000",
    linewidth=3,
    zorder=2,
)
ax.add_patch(left_box)

# Data content
data_text = (
    "Obfuscated Data Only:\n\n"
    "Date: Day T+0\n"
    "Ticker: INDEX_1\n\n"
    "Net GEX: -$32.49B\n"
    "Call Γ: -$15.97B\n"
    "Put Γ: -$16.52B\n"
    "Spot: $472.87\n\n"
    "Regime: NEGATIVE_GAMMA\n\n"
    "NO temporal context\n"
    "NO event information\n"
    "NO historical patterns"
)

ax.text(
    left_x,
    4.0,
    data_text,
    ha="center",
    va="center",
    fontsize=16,
    family="monospace",
    color="#000000",
    zorder=4,
    linespacing=1.6,
)

# ============ MIDDLE COLUMN: CAUSAL FRAMEWORK ============
mid_x = 8.0

# Header
mid_header = FancyBboxPatch(
    (5.75, 7.5),
    col_width,
    0.6,
    boxstyle="round,pad=0.1",
    facecolor="#FFE5B4",
    edgecolor="#8B0000",
    linewidth=4,
    zorder=2,
)
ax.add_patch(mid_header)
ax.text(
    mid_x, 7.75, "Causal Framework Detected", ha="center", fontsize=20, fontweight="bold", color="#8B0000", zorder=4
)

# Content box
mid_box = FancyBboxPatch(
    (5.75, 1.0),
    col_width,
    6.2,
    boxstyle="round,pad=0.1",
    facecolor="#fff8e6",
    edgecolor="#000000",
    linewidth=3,
    zorder=2,
)
ax.add_patch(mid_box)

# Causal chain
causal_text = (
    "LLM's Reasoning:\n\n"
    "WHO:\n"
    "Market Makers\n\n"
    "WHOM:\n"
    "Market Participants\n\n"
    "WHAT:\n"
    "Hedging by buying dips\n"
    "and selling rallies\n\n"
    "WHY:\n"
    "Negative gamma forces\n"
    "destabilizing hedging\n\n"
    "Confidence: 90%"
)

ax.text(
    mid_x,
    4.0,
    causal_text,
    ha="center",
    va="center",
    fontsize=17,
    fontweight="bold",
    color="#8B0000",
    zorder=4,
    linespacing=1.5,
)

# ============ RIGHT COLUMN: WHAT HAPPENED ============
right_x = 13.5

# Header
right_header = FancyBboxPatch(
    (11.25, 7.5),
    col_width,
    0.6,
    boxstyle="round,pad=0.1",
    facecolor="#d4edda",
    edgecolor="#28a745",
    linewidth=4,
    zorder=2,
)
ax.add_patch(right_header)
ax.text(right_x, 7.75, "What Happened Next", ha="center", fontsize=22, fontweight="bold", color="#28a745", zorder=4)

# Content box
right_box = FancyBboxPatch(
    (11.25, 1.0),
    col_width,
    6.2,
    boxstyle="round,pad=0.1",
    facecolor="#f5f5f5",
    edgecolor="#000000",
    linewidth=3,
    zorder=2,
)
ax.add_patch(right_box)

# Outcome data
outcome_text = (
    "Outcome Verification:\n"
    "(SPY underlying moves)\n\n"
    "SPY 1-day return:\n"
    "-0.86%\n\n"
    "SPY 3-day return:\n"
    "-0.99%\n\n"
    "Max drawdown:\n"
    "-1.12%\n\n"
    "Prediction verified:\n"
    "✓ TRUE\n\n"
    "Market moved DOWN\n"
    "Dealers amplified move\n"
    "via forced hedging"
)

ax.text(
    right_x,
    4.0,
    outcome_text,
    ha="center",
    va="center",
    fontsize=16,
    fontweight="bold",
    color="#28a745",
    zorder=4,
    linespacing=1.5,
)

# ============ ARROWS CONNECTING COLUMNS ============

# Arrow 1: Left → Middle
arrow1 = FancyArrowPatch(
    (4.9, 4.0), (5.6, 4.0), arrowstyle="->,head_width=0.8,head_length=0.6", color="#333333", linewidth=5, zorder=3
)
ax.add_patch(arrow1)

# Arrow 2: Middle → Right
arrow2 = FancyArrowPatch(
    (10.4, 4.0), (11.1, 4.0), arrowstyle="->,head_width=0.8,head_length=0.6", color="#333333", linewidth=5, zorder=3
)
ax.add_patch(arrow2)

# ============ BOTTOM KEY INSIGHT ============
insight = (
    "This is NOT prediction • This is mechanistic reasoning\n"
    "LLM identified causal constraints without temporal context or historical patterns"
)
fig.text(
    0.5,
    0.05,
    insight,
    ha="center",
    fontsize=20,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#FFE5B4", edgecolor="#8B0000", linewidth=3),
)

plt.tight_layout()

# Save
output_file = OUTPUT_DIR / "llm_causal_detection_1920x1080.png"
plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="white")
print(f"✅ LLM Causal Detection Example: {output_file}")

plt.close()
