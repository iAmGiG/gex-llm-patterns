#!/usr/bin/env python3
"""
Generate GEX Magnitude Distribution by Year Figure (Issue #213)

Creates histogram visualization showing GEX magnitude distributions for
2020 vs 2024 to support the $5B magnitude threshold discrimination claim.

Output: docs/papers/paper2/figures/output/fig_gex_magnitude_distribution.png
"""

import sqlite3
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DB = PROJECT_ROOT / ".cache" / "research_cache.db"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "papers" / "paper2" / "figures" / "output"

def query_magnitude_data():
    """Query magnitude data from ResearchCache by year."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            substr(trading_date, 1, 4) as year,
            json_extract(structured_output, '$.avg_magnitude_billions') as magnitude
        FROM llm_detections
        WHERE structured_output IS NOT NULL
        ORDER BY year
    """)

    rows = cursor.fetchall()
    conn.close()

    # Group by year
    data = {}
    for year, magnitude in rows:
        if year not in data:
            data[year] = []
        if magnitude is not None:
            data[year].append(float(magnitude))

    return data

def create_magnitude_histogram(data, output_path):
    """Create publication-quality histogram comparing 2020 vs 2024."""

    # Extract 2020 and 2024 data
    mag_2020 = np.array(data.get('2020', []))
    mag_2024 = np.array(data.get('2024', []))

    # Calculate statistics
    mean_2020 = np.mean(mag_2020)
    mean_2024 = np.mean(mag_2024)
    pct_above_5b_2020 = (mag_2020 >= 5.0).sum() / len(mag_2020) * 100
    pct_above_5b_2024 = (mag_2024 >= 5.0).sum() / len(mag_2024) * 100

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 7), dpi=200)

    # Define bins - from 0 to 30B in $2B increments
    bins = np.arange(0, 32, 2)

    # Plot histograms
    ax.hist(mag_2020, bins=bins, alpha=0.6, label=f'2020 (n={len(mag_2020)})',
            color='#3274A1', edgecolor='white', linewidth=0.5)
    ax.hist(mag_2024, bins=bins, alpha=0.6, label=f'2024 (n={len(mag_2024)})',
            color='#E1812C', edgecolor='white', linewidth=0.5)

    # Add $5B threshold line
    ax.axvline(x=5.0, color='#2D2D2D', linestyle='--', linewidth=2.5,
               label='$5B Regime Threshold')

    # Add mean lines
    ax.axvline(x=mean_2020, color='#3274A1', linestyle=':', linewidth=2, alpha=0.8)
    ax.axvline(x=mean_2024, color='#E1812C', linestyle=':', linewidth=2, alpha=0.8)

    # Annotations
    y_max = ax.get_ylim()[1]

    # 2020 mean annotation
    ax.annotate(f'2020 Mean\n${mean_2020:.1f}B',
                xy=(mean_2020, y_max * 0.85),
                xytext=(mean_2020 - 3, y_max * 0.92),
                fontsize=11, fontweight='bold', color='#3274A1',
                arrowprops=dict(arrowstyle='->', color='#3274A1', lw=1.5),
                ha='center')

    # 2024 mean annotation
    ax.annotate(f'2024 Mean\n${mean_2024:.1f}B',
                xy=(mean_2024, y_max * 0.65),
                xytext=(mean_2024 + 3, y_max * 0.80),
                fontsize=11, fontweight='bold', color='#E1812C',
                arrowprops=dict(arrowstyle='->', color='#E1812C', lw=1.5),
                ha='center')

    # Threshold annotation
    ax.annotate('Regime\nThreshold',
                xy=(5.0, y_max * 0.5),
                xytext=(8, y_max * 0.55),
                fontsize=10, fontweight='bold', color='#2D2D2D',
                arrowprops=dict(arrowstyle='->', color='#2D2D2D', lw=1.5),
                ha='left')

    # Statistics text box
    stats_text = (
        f'Above $5B Threshold:\n'
        f'  2020: {pct_above_5b_2020:.1f}%\n'
        f'  2024: {pct_above_5b_2024:.1f}%\n\n'
        f'Magnitude Growth:\n'
        f'  +{((mean_2024/mean_2020)-1)*100:.0f}% ({mean_2020:.1f}B → {mean_2024:.1f}B)'
    )
    ax.text(0.98, 0.97, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                      edgecolor='gray', alpha=0.9),
            family='monospace')

    # Labels and title
    ax.set_xlabel('Average GEX Magnitude ($B)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of 30-Day Windows', fontsize=13, fontweight='bold')
    ax.set_title('GEX Magnitude Distribution: Pre-0DTE (2020) vs Post-0DTE (2024)',
                 fontsize=14, fontweight='bold', pad=15)

    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9,
              bbox_to_anchor=(0.99, 0.72))

    # Grid and styling
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_xlim(0, 30)
    ax.set_axisbelow(True)

    # Spine styling
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)

    plt.tight_layout()

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    print(f"Figure saved to: {output_path}")
    print(f"\nStatistics:")
    print(f"  2020: n={len(mag_2020)}, mean=${mean_2020:.2f}B, range=${mag_2020.min():.1f}-${mag_2020.max():.1f}B")
    print(f"  2024: n={len(mag_2024)}, mean=${mean_2024:.2f}B, range=${mag_2024.min():.1f}-${mag_2024.max():.1f}B")
    print(f"  Above $5B: 2020={pct_above_5b_2020:.1f}%, 2024={pct_above_5b_2024:.1f}%")
    print(f"  Magnitude growth: +{((mean_2024/mean_2020)-1)*100:.0f}%")

def main():
    print("Generating GEX Magnitude Distribution Figure (Issue #213)...")
    print(f"Database: {CACHE_DB}")

    # Query data
    data = query_magnitude_data()
    print(f"\nData loaded: {', '.join(f'{y}: {len(v)} windows' for y, v in sorted(data.items()))}")

    # Create histogram
    output_path = OUTPUT_DIR / "fig_gex_magnitude_distribution.png"
    create_magnitude_histogram(data, output_path)

    print("\nDone!")

if __name__ == "__main__":
    main()
