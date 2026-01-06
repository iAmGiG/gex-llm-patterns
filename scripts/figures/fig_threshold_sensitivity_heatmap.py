#!/usr/bin/env python3
"""
Generate Threshold Sensitivity Heatmap (Issue #210)

Creates 2D heatmap showing discrimination gap across parameter space
to demonstrate framework robustness to threshold selection.

Output: docs/papers/paper2/figures/output/fig_threshold_sensitivity_heatmap.png
"""

import sqlite3
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CACHE_DB = PROJECT_ROOT / ".cache" / "research_cache.db"
OUTPUT_DIR = PROJECT_ROOT / "docs" / "papers" / "paper2" / "figures" / "output"

# Parameter ranges to test
PERSISTENCE_THRESHOLDS = [60, 65, 70, 75, 80]
MAGNITUDE_THRESHOLDS = [3, 4, 5, 6, 7]
STABILITY_THRESHOLD = 5  # Fixed at ≤5 flips

# Current paper parameters
CURRENT_PERSISTENCE = 70
CURRENT_MAGNITUDE = 5


def query_data():
    """Query window data from ResearchCache."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            substr(trading_date, 1, 4) as year,
            json_extract(structured_output, '$.persistence_pct') as persistence,
            json_extract(structured_output, '$.avg_magnitude_billions') as magnitude,
            json_extract(structured_output, '$.sign_flips') as flips
        FROM llm_detections
        WHERE structured_output IS NOT NULL
          AND substr(trading_date, 1, 4) IN ('2020', '2024')
    """)

    rows = cursor.fetchall()
    conn.close()

    data = {'2020': [], '2024': []}
    for year, persistence, magnitude, flips in rows:
        if all(v is not None for v in [persistence, magnitude, flips]):
            data[year].append({
                'persistence': float(persistence),
                'magnitude': float(magnitude),
                'flips': int(flips)
            })

    return data


def calculate_detection_rate(windows, persistence_thresh, magnitude_thresh, stability_thresh=5):
    """Calculate detection rate for given thresholds."""
    if not windows:
        return 0.0

    detected = sum(
        1 for w in windows
        if w['persistence'] >= persistence_thresh
        and w['magnitude'] >= magnitude_thresh
        and w['flips'] <= stability_thresh
    )
    return detected / len(windows) * 100


def create_heatmap(data, output_path):
    """Create threshold sensitivity heatmap."""

    # Calculate discrimination gaps for each parameter combination
    gaps = np.zeros((len(PERSISTENCE_THRESHOLDS), len(MAGNITUDE_THRESHOLDS)))
    rates_2020 = np.zeros_like(gaps)
    rates_2024 = np.zeros_like(gaps)

    for i, p_thresh in enumerate(PERSISTENCE_THRESHOLDS):
        for j, m_thresh in enumerate(MAGNITUDE_THRESHOLDS):
            rate_2020 = calculate_detection_rate(data['2020'], p_thresh, m_thresh)
            rate_2024 = calculate_detection_rate(data['2024'], p_thresh, m_thresh)
            gaps[i, j] = rate_2024 - rate_2020
            rates_2020[i, j] = rate_2020
            rates_2024[i, j] = rate_2024

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8), dpi=200)

    # Create heatmap
    im = ax.imshow(gaps, cmap='RdYlGn', aspect='auto', vmin=50, vmax=100)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Discrimination Gap (pp)\n(2024% - 2020%)', fontsize=11, fontweight='bold')

    # Set ticks and labels
    ax.set_xticks(np.arange(len(MAGNITUDE_THRESHOLDS)))
    ax.set_yticks(np.arange(len(PERSISTENCE_THRESHOLDS)))
    ax.set_xticklabels([f'${m}B' for m in MAGNITUDE_THRESHOLDS], fontsize=11)
    ax.set_yticklabels([f'{p}%' for p in PERSISTENCE_THRESHOLDS], fontsize=11)

    # Labels
    ax.set_xlabel('Magnitude Threshold', fontsize=12, fontweight='bold')
    ax.set_ylabel('Persistence Threshold', fontsize=12, fontweight='bold')
    ax.set_title('Threshold Sensitivity Analysis:\nDiscrimination Gap Across Parameter Space',
                 fontsize=14, fontweight='bold', pad=15)

    # Add text annotations in each cell
    for i in range(len(PERSISTENCE_THRESHOLDS)):
        for j in range(len(MAGNITUDE_THRESHOLDS)):
            gap = gaps[i, j]
            r2020 = rates_2020[i, j]
            r2024 = rates_2024[i, j]

            # Choose text color based on background
            text_color = 'white' if gap < 70 else 'black'

            # Main gap value
            ax.text(j, i, f'{gap:.0f}pp',
                    ha='center', va='center', fontsize=12, fontweight='bold',
                    color=text_color)

            # Smaller annotation with rates
            ax.text(j, i + 0.32, f'({r2024:.0f}%-{r2020:.0f}%)',
                    ha='center', va='center', fontsize=8,
                    color=text_color, alpha=0.8)

    # Highlight current parameters (70%, $5B)
    current_i = PERSISTENCE_THRESHOLDS.index(CURRENT_PERSISTENCE)
    current_j = MAGNITUDE_THRESHOLDS.index(CURRENT_MAGNITUDE)

    # Draw rectangle around current parameters
    rect = plt.Rectangle((current_j - 0.5, current_i - 0.5), 1, 1,
                          fill=False, edgecolor='blue', linewidth=3)
    ax.add_patch(rect)

    # Add marker
    ax.plot(current_j, current_i, 'b*', markersize=20, markeredgecolor='white',
            markeredgewidth=1.5)

    # Add legend for current parameters
    ax.text(0.02, 0.98, '★ Current Parameters\n    (70%, $5B)',
            transform=ax.transAxes, fontsize=10, fontweight='bold',
            verticalalignment='top', color='blue',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor='blue', alpha=0.9))

    # Add summary statistics
    min_gap = gaps.min()
    max_gap = gaps.max()
    mean_gap = gaps.mean()
    all_above_50 = (gaps >= 50).all()

    stats_text = (
        f'All combinations >50pp: {"✓" if all_above_50 else "✗"}\n'
        f'Range: {min_gap:.0f}-{max_gap:.0f}pp\n'
        f'Mean: {mean_gap:.0f}pp'
    )
    ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor='gray', alpha=0.9),
            family='monospace')

    plt.tight_layout()

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()

    print(f"Figure saved to: {output_path}")
    print(f"\nThreshold Sensitivity Results:")
    print(f"  Parameter combinations tested: {len(PERSISTENCE_THRESHOLDS) * len(MAGNITUDE_THRESHOLDS)}")
    print(f"  All combinations >50pp discrimination: {all_above_50}")
    print(f"  Discrimination range: {min_gap:.1f}pp - {max_gap:.1f}pp")
    print(f"  Mean discrimination: {mean_gap:.1f}pp")
    print(f"\nCurrent parameters (70%, $5B):")
    print(f"  2020 detection: {rates_2020[current_i, current_j]:.1f}%")
    print(f"  2024 detection: {rates_2024[current_i, current_j]:.1f}%")
    print(f"  Discrimination gap: {gaps[current_i, current_j]:.1f}pp")

    # Print full table
    print("\nFull discrimination table:")
    header = "Pers\\Mag"
    print(f"{header:>8}", end='')
    for m in MAGNITUDE_THRESHOLDS:
        print(f'  ${m}B', end='')
    print()
    for i, p in enumerate(PERSISTENCE_THRESHOLDS):
        print(f'{p}%', end='')
        for j in range(len(MAGNITUDE_THRESHOLDS)):
            print(f'  {gaps[i,j]:4.0f}', end='')
        print()


def main():
    print("Generating Threshold Sensitivity Heatmap (Issue #210)...")
    print(f"Database: {CACHE_DB}")

    # Query data
    data = query_data()
    print(f"\nData loaded: 2020={len(data['2020'])} windows, 2024={len(data['2024'])} windows")

    # Create heatmap
    output_path = OUTPUT_DIR / "fig_threshold_sensitivity_heatmap.png"
    create_heatmap(data, output_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
