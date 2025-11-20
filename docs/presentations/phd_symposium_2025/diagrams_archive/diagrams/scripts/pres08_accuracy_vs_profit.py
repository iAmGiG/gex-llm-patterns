#!/usr/bin/env python3
"""
Detection ≠ Profitability: The Divergence - PRESENTATION VERSION

Dual-axis chart showing:
- LEFT Y-axis: Detection Rate (%) - FLAT at ~71%
- RIGHT Y-axis: Net Alpha (bps) - DECLINING from +70 to -1

This divergence is our strongest evidence:
- Not overfitting (both would decline together)
- Not cherry-picking (we'd hide Q4)
- Detection measures UNDERSTANDING, not trading edge
"""

import matplotlib.pyplot as plt
from pathlib import Path

# PRESENTATION SETTINGS
plt.rcParams.update({
    'font.size': 18,
    'font.weight': 'bold',
    'figure.facecolor': 'white',
    'savefig.facecolor': 'white',
})

OUTPUT_DIR = Path(
    '/mnt/bst/yxie2/cregan1/gex-llm-patterns/docs/presentations/oct22_research/diagrams')

# Data - ACTUAL from gamma_positioning quarterly YAMLs (biased prompts)
quarters = ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024']
accuracy_rates = [84.9, 91.7, 96.9, 96.8]  # INCREASING accuracy
net_alpha = [20.8, 1.6, 4.6, -0.7]  # DECLINING profitability

# Create figure with dual axes
fig, ax1 = plt.subplots(figsize=(16, 9), dpi=120)

# Main title
# fig.text(0.5, 0.96, 'Detection ≠ Profitability (This Is Our Strongest Evidence)',
#          ha='center', fontsize=30, fontweight='bold')

# LEFT Y-axis: Predictive Accuracy
color_accuracy = '#28a745'  # Green (increasing)
ax1.set_xlabel('Quarter', fontsize=24, fontweight='bold')
ax1.set_ylabel('Predictive Accuracy (%)', fontsize=24,
               fontweight='bold', color=color_accuracy)
ax1.plot(quarters, accuracy_rates, 'o-', color=color_accuracy,
         linewidth=6, markersize=20, label='Predictive Accuracy (improving)', zorder=3)
ax1.tick_params(axis='y', labelcolor=color_accuracy, labelsize=20)
ax1.tick_params(axis='x', labelsize=20)
ax1.set_ylim(75, 100)
ax1.grid(True, alpha=0.3, zorder=1)

# Add annotation showing improvement
ax1.annotate('', xy=(3, 96.8), xytext=(0, 84.9),
             arrowprops=dict(arrowstyle='->,head_width=0.8,head_length=0.6',
                             color=color_accuracy, linewidth=5, alpha=0.2))
ax1.text(1.5, 90, 'IMPROVING\n84.9% → 96.8%', fontsize=18, color=color_accuracy,
         ha='center', fontweight='bold', style='italic')

# RIGHT Y-axis: Net Alpha
ax2 = ax1.twinx()
color_alpha = '#dc3545'  # Red (declining)
ax2.set_ylabel('Net Alpha (basis points)', fontsize=24,
               fontweight='bold', color=color_alpha)
ax2.plot(quarters, net_alpha, 's-', color=color_alpha,
         linewidth=6, markersize=20, label='Net Alpha (declining)', zorder=3)
ax2.tick_params(axis='y', labelcolor=color_alpha, labelsize=20)
ax2.set_ylim(-5, 25)

# Add declining arrow annotation
ax2.annotate('', xy=(3, -0.5), xytext=(0, 20.8),
             arrowprops=dict(arrowstyle='->,head_width=0.8,head_length=0.6',
                             color=color_alpha, linewidth=5, alpha=0.2))
ax2.text(2.5, 6, 'DECLINING\n+20.8 → -0.7 bps', fontsize=18, color=color_alpha,
         ha='center', fontweight='bold', style='italic')

# Three callout boxes at bottom
callout_y = -0.10
box_width = 0.20

# Box 1: If overfitting
fig.text(0.15, callout_y,
         '"If we were overfitting..."\n\n→ Both lines would\ndecline together',
         ha='center', va='center', fontsize=17, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#ffe6e6',
                   edgecolor='#dc3545', linewidth=3))

# Box 2: If cherry-picking
fig.text(0.5, callout_y,
         '"If we were cherry-picking..."\n\n→ We\'d hide Q4 results\n(the unprofitable quarter)',
         ha='center', va='center', fontsize=17, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#fff8e6',
                   edgecolor='#FFA500', linewidth=3))

# Box 3: Instead (the truth)
fig.text(0.85, callout_y,
         '"Instead..."\n\n→ Accuracy IMPROVES while\nprofits vanish\n✓ Proves UNDERSTANDING\n   not trading edge',
         ha='center', va='center', fontsize=17, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#e6f7ed',
                   edgecolor='#28a745', linewidth=3))

# Legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower right',
           fontsize=18, frameon=True, edgecolor='#000000', fancybox=True)

plt.tight_layout(rect=[0, 0.1, 1, 1])

# Save
output_file = OUTPUT_DIR / 'detection_vs_profitability_divergence_1920x1080.png'
plt.savefig(output_file, dpi=120, bbox_inches='tight', facecolor='white')
print(f"✅ Detection vs Profitability Divergence: {output_file}")

plt.close()
