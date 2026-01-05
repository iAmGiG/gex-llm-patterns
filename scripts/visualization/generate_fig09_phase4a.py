#!/usr/bin/env python3
"""
Generate Figure 9: Phase 4A Detection Rate Temporal Progression

This script creates a temporal analysis figure showing how LLM detection rates
evolved from 2020-2025, revealing gradual 0DTE adoption and the 2023→2024
structural market shift.

Issue #195: Phase 4A Detection Rate Temporal Progression Figure
"""

import matplotlib.pyplot as plt
import numpy as np
import sqlite3

# Query ResearchCache for detection rates by year
db_path = '/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/.cache/research_cache.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

query = '''
SELECT
  SUBSTR(trading_date, 1, 4) as year,
  COUNT(*) as total_windows,
  SUM(CASE WHEN detected = 1 THEN 1 ELSE 0 END) as detected_count,
  ROUND(100.0 * SUM(CASE WHEN detected = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as detection_pct,
  ROUND(AVG(CAST(json_extract(structured_output, '$.avg_magnitude_billions') AS REAL)), 1) as avg_gex_magnitude
FROM llm_detections
WHERE pattern_id = 'regime_30day'
GROUP BY SUBSTR(trading_date, 1, 4)
ORDER BY year
'''

cursor.execute(query)
results = cursor.fetchall()
conn.close()

# Extract data
years = [int(row[0]) for row in results]
total_windows = [row[1] for row in results]
detected_counts = [row[2] for row in results]
detection_rates = [row[3] for row in results]
avg_gex = [row[4] for row in results]

# Create figure with two subplots (detection rate + GEX magnitude)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), dpi=120,
                                gridspec_kw={'height_ratios': [2, 1]})

# ============================================================================
# TOP PLOT: Detection Rate Temporal Progression
# ============================================================================

# Color scheme: professional publication-ready colors
color_baseline = '#2E86AB'      # Blue for pre-regime (2020-2021)
color_growing = '#6A994E'       # Green for growing adoption (2022-2023)
color_structural = '#C73E1D'    # Deep red for structural shift (2024-2025)

# Assign colors based on regime state
colors = [
    color_baseline,     # 2020 - Pre-regime
    color_baseline,     # 2021 - Borderline
    color_growing,      # 2022 - Growing
    color_growing,      # 2023 - Inconsistent
    color_structural,   # 2024 - Structural shift
    color_structural,   # 2025 - Sustained
]

# Plot bars with appropriate colors
bars = ax1.bar(years, detection_rates, color=colors, width=0.7,
               edgecolor='black', linewidth=1.5, alpha=0.85)

# Add detection counts on top of bars
for i, (year, rate, count, total) in enumerate(zip(years, detection_rates, detected_counts, total_windows)):
    ax1.text(year, rate + 3, f'{count}/{total}',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

# Add percentage labels inside bars
for i, (year, rate) in enumerate(zip(years, detection_rates)):
    if rate > 15:  # Only show inside if bar is tall enough
        ax1.text(year, rate/2, f'{rate:.1f}%',
                 ha='center', va='center', fontsize=12, fontweight='bold', color='white')
    else:
        ax1.text(year, rate + 8, f'{rate:.1f}%',
                 ha='center', va='bottom', fontsize=10, fontweight='bold')

# Highlight 2023→2024 structural shift with annotation
ax1.annotate('', xy=(2024, 100), xytext=(2023, 20.2),
             arrowprops=dict(arrowstyle='->', lw=3, color='#FF6B00', linestyle='--'))
ax1.text(2023.5, 60, '2023→2024\nStructural\nShift',
         ha='center', va='center', fontsize=11, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.5', facecolor='#FFF9E6',
                   edgecolor='#FF6B00', linewidth=2))

# Add regime labels
ax1.text(2020.5, 105, 'Pre-Regime', ha='center', fontsize=10,
         fontweight='bold', color=color_baseline)
ax1.text(2022.5, 105, 'Gradual Adoption', ha='center', fontsize=10,
         fontweight='bold', color=color_growing)
ax1.text(2024.5, 105, 'Persistent Regime', ha='center', fontsize=10,
         fontweight='bold', color=color_structural)

# Formatting
ax1.set_xlabel('Year', fontsize=13, fontweight='bold')
ax1.set_ylabel('Detection Rate (%)', fontsize=13, fontweight='bold')
ax1.set_title('Phase 4A: Temporal Progression of Regime Detection (2020-2025)\n' +
              'Gradual 0DTE Adoption with 2023→2024 Structural Market Shift',
              fontsize=14, fontweight='bold', pad=15)
ax1.set_ylim(0, 115)
ax1.set_xticks(years)
ax1.grid(axis='y', alpha=0.3, linestyle='--')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# ============================================================================
# BOTTOM PLOT: Average GEX Magnitude Evolution
# ============================================================================

# Plot GEX magnitude as line chart with markers
ax2.plot(years, avg_gex, marker='o', markersize=10, linewidth=3,
         color='#F18F01', markerfacecolor='#F18F01', markeredgecolor='black',
         markeredgewidth=1.5)

# Add magnitude labels
for year, gex in zip(years, avg_gex):
    ax2.text(year, gex + 0.8, f'${gex:.1f}B',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

# Add threshold line at $5B
ax2.axhline(y=5.0, color='#C73E1D', linestyle='--', linewidth=2, alpha=0.7)
ax2.text(2020.3, 5.5, '$5B Threshold', fontsize=9, fontweight='bold',
         color='#C73E1D', va='bottom')

# Formatting
ax2.set_xlabel('Year', fontsize=13, fontweight='bold')
ax2.set_ylabel('Avg GEX Magnitude (Billions $)', fontsize=12, fontweight='bold')
ax2.set_title('Average GEX Magnitude Evolution (360% Growth 2021→2024)',
              fontsize=12, fontweight='bold', pad=10)
ax2.set_ylim(0, 25)
ax2.set_xticks(years)
ax2.grid(axis='y', alpha=0.3, linestyle='--')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

# ============================================================================
# FOOTER EXPLANATION
# ============================================================================

footer_text = (
    "Key Finding: Detection rates track market evolution precisely. Low rates in 2020-2021 (12.2%, 3.7%) reflect pre-regime baseline.\n"
    "Growing but inconsistent rates in 2022-2023 (32.4%, 20.2%) show gradual 0DTE adoption. Perfect 100% detection in 2024-2025\n"
    "marks structural shift with sustained dealer gamma regimes. GEX magnitude grew 360% ($5B → $23B), far exceeding inflation (20-25%)."
)
fig.text(0.5, 0.02, footer_text, ha='center', va='bottom', fontsize=9,
         style='italic', color='#555555', wrap=True)

plt.tight_layout(rect=[0, 0.06, 1, 1])

# Save publication-quality version (300 DPI)
output_path = '/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns-issue195/docs/papers/paper2/figures/output/fig09_phase4a_detection_progression.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"✅ Figure 9 saved: {output_path}")

# Also save web version (150 DPI)
web_path = '/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns-issue195/docs/papers/paper2/figures/output/fig09_phase4a_detection_progression_web.png'
plt.savefig(web_path, dpi=150, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"✅ Web version saved: {web_path}")

plt.close()

# Print data summary
print("\n" + "="*60)
print("PHASE 4A DETECTION RATES BY YEAR (2020-2025)")
print("="*60)
print(f"{'Year':<6} {'Total':<8} {'Detected':<10} {'Rate':<8} {'Avg GEX':<10}")
print("-"*60)
for year, total, detected, rate, gex in zip(years, total_windows, detected_counts, detection_rates, avg_gex):
    print(f"{year:<6} {total:<8} {detected:<10} {rate:>5.1f}%    ${gex:.1f}B")
print("="*60)
