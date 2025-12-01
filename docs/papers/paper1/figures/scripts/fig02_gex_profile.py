#!/usr/bin/env python3
"""
Figure 2: GEX Profile Example (YAML-BASED REPRESENTATIVE EXAMPLE)

Uses actual net GEX values from validation data to create representative GEX profile.
Shows what negative/positive gamma regimes look like to illustrate input data for LLM.

Data source:
- gamma_positioning_SPY_2024_unbiased.yaml (for realistic net GEX magnitude)
- Synthetic strike distribution calibrated to match actual net GEX value

Note: Full strike-by-strike data not stored in YAML, so we create representative
      distribution that matches the actual net GEX and spot price from validation data.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

# IEEE two-column format
plt.rcParams.update(
    {
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8,
        "figure.titlesize": 11,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
    }
)

# Data paths
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
REPORTS_DIR = BASE_DIR / "reports" / "validation" / "pattern_taxonomy"
OUTPUT_DIR = BASE_DIR / "docs" / "papers" / "paper1" / "figures"

print("=" * 60)
print("FIGURE 4: GEX PROFILE VISUALIZATION (YAML-BASED)")
print("=" * 60)

# Load actual GEX data from validation to get realistic values
filepath = REPORTS_DIR / "gamma_positioning_SPY_2024_unbiased.yaml"
with open(filepath, "r") as f:
    data = yaml.safe_load(f)

# Get first detection with negative GEX
negative_example = None
for detection in data["detections"]:
    if detection["detected"] and detection["quantitative_evidence"]["gex_metrics"]["regime"] == "NEGATIVE_GAMMA":
        negative_example = detection
        break

if negative_example:
    net_gex = negative_example["quantitative_evidence"]["gex_metrics"]["net_gex_usd"]
    spot_price = negative_example["quantitative_evidence"]["gex_metrics"]["spot_price"]
    date = negative_example["date"]
    print(f"\nUsing real data from {date}:")
    print(f"  Spot price: ${spot_price:.2f}")
    print(f"  Net GEX: ${net_gex/1e9:.2f}B")
else:
    # Fallback to synthetic if no negative example found
    net_gex = -32.5e9
    spot_price = 475.0
    date = "representative example"
    print(f"\nUsing representative values:")
    print(f"  Spot price: ${spot_price:.2f}")
    print(f"  Net GEX: ${net_gex/1e9:.2f}B")

# Create strike distribution calibrated to match net_gex
strikes = np.arange(int(spot_price - 30), int(spot_price + 36), 5)
target_net_gex_billions = net_gex / 1e9

# Create realistic negative gamma profile
gex_values = []
for strike in strikes:
    distance_from_spot = abs(strike - spot_price)
    if distance_from_spot < 10:  # ATM region - large negative GEX
        gex = -7.5 + np.random.uniform(-1.5, 0.5)
    elif distance_from_spot < 20:  # Near ATM - moderate negative
        gex = -3.5 + np.random.uniform(-1.5, 0.5)
    else:  # Far OTM - small positive
        gex = 0.5 + np.random.uniform(-0.3, 0.3)
    gex_values.append(gex)

# Scale to match target net GEX
gex_values = np.array(gex_values)
current_sum = np.sum(gex_values)
scale_factor = target_net_gex_billions / current_sum
gex_values = gex_values * scale_factor
actual_net_gex = np.sum(gex_values)

print(f"Generated profile:")
print(f"  Target net GEX: ${target_net_gex_billions:.2f}B")
print(f"  Achieved net GEX: ${actual_net_gex:.2f}B")
print(f"  Scale factor: {scale_factor:.3f}")

# ============================================================================
# VERSION 1: Clean Single Profile with Prominent Annotations
# ============================================================================

fig, ax = plt.subplots(figsize=(11, 6))

# Plot GEX profile (set zorder to render above ATM shading)
colors = ["#E74C3C" if g < 0 else "#27AE60" for g in gex_values]
bars = ax.bar(strikes, gex_values, width=4.5, color=colors, alpha=0.85, edgecolor="black", linewidth=1, zorder=3)

# Zero line
ax.axhline(y=0, color="black", linestyle="-", linewidth=2, alpha=0.6, zorder=2)

# Spot price indicator (higher zorder to render on top)
ax.axvline(x=spot_price, color="#3498DB", linestyle="--", linewidth=4, alpha=0.9, zorder=10)

# Spot price label (top)
ax.text(
    spot_price,
    ax.get_ylim()[1] * 0.95,
    f"Spot: ${spot_price:.0f}",
    ha="center",
    va="top",
    fontsize=13,
    fontweight="bold",
    bbox=dict(boxstyle="round,pad=0.6", facecolor="#3498DB", edgecolor="black", linewidth=2, alpha=0.9),
    color="white",
    zorder=11,
)

# NET GEX ANNOTATION - MOVED TO BOTTOM-LEFT for style consistency
net_gex_text = f"NET GEX:\n${actual_net_gex:.1f}B"
regime_text = "\nNEGATIVE GAMMA"
full_text = net_gex_text + regime_text

ax.text(
    0.02,
    0.05,
    full_text,
    transform=ax.transAxes,
    fontsize=14,
    fontweight="bold",
    color="darkred",
    verticalalignment="bottom",
    horizontalalignment="left",
    bbox=dict(boxstyle="round,pad=0.8", facecolor="#FFE6E6", edgecolor="darkred", linewidth=2.5, alpha=0.95),
    zorder=12,
)

# ATM region shading (behind bars)
atm_left, atm_right = spot_price - 10, spot_price + 10
ax.axvspan(atm_left, atm_right, alpha=0.2, color="yellow", zorder=1, label="ATM Region")

# ATM annotation (after dashed line to render on top)
ax.text(
    (atm_left + atm_right) / 2,
    ax.get_ylim()[0] * 0.85,
    "ATM\nRegion",
    ha="center",
    va="center",
    fontsize=10,
    fontweight="bold",
    style="italic",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="yellow", alpha=0.7, edgecolor="orange", linewidth=2),
    zorder=11,
)

# Dealer constraint explanation box (moved to bottom-right corner)
constraint_text = (
    "Dealer Hedging Constraint:\n"
    "• Negative GEX → SHORT gamma\n"
    "• Must SELL into rallies (delta hedge)\n"
    "• Must BUY into selloffs (delta hedge)\n"
    "→ Amplifies price movements"
)
ax.text(
    0.98,
    0.05,
    constraint_text,
    transform=ax.transAxes,
    fontsize=10,
    verticalalignment="bottom",
    horizontalalignment="right",
    bbox=dict(boxstyle="round,pad=0.8", facecolor="wheat", edgecolor="brown", linewidth=2, alpha=0.95),
    family="monospace",
)

# Labels
ax.set_xlabel("Strike Price ($)", fontsize=13, fontweight="bold")
ax.set_ylabel("Gamma Exposure ($ Billions)", fontsize=13, fontweight="bold")
ax.set_title(
    f"GEX Profile Example: Negative Gamma Regime\n(Representative pattern from {date})",
    fontsize=14,
    fontweight="bold",
    pad=20,
)
ax.grid(axis="y", alpha=0.3, linestyle=":", linewidth=1)
ax.set_xlim(strikes[0] - 3, strikes[-1] + 3)

# Better tick labels
ax.tick_params(axis="both", labelsize=10)

plt.tight_layout()
output1 = OUTPUT_DIR / "../fig02_gex_profile.png"
plt.savefig(output1, dpi=300, bbox_inches="tight")
print(f"✅ Figure 2 (GEX Profile): {output1}")
plt.close()
