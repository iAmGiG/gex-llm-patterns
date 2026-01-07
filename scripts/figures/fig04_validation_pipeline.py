#!/usr/bin/env python3
"""
Generate Figure 4: Multi-Phase Validation Pipeline

Creates a flow diagram showing the validation phases with detection rates:
Phase 1 (71.2%) → Phase 2 (6.3%) → Phase 3 (81.2%) → Phase 4 (12.1%)

Updated with SpotGamma-inspired dark theme (Issue #216).

Output: docs/papers/paper2/figures/output/fig04_validation_pipeline.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "docs" / "papers" / "paper2" / "figures" / "output"

# SpotGamma-inspired Dark Theme (Issue #216)
DARK_THEME = {
    'background': '#1a1a2e',      # Deep navy/black
    'text': '#ffffff',             # White text
    'grid': '#2d2d44',            # Subtle grid
    'accent_positive': '#00ff88', # Neon green
    'accent_negative': '#ff4444', # Neon red
    'accent_neutral': '#00d4ff',  # Cyan
    'accent_warning': '#ffaa00',  # Orange/amber
    'dim': '#666666',             # Grey for low values
    'panel_bg': '#252540',        # Slightly lighter for panels
    # Phase-specific colors
    'phase1': '#00d4ff',          # Cyan - baseline
    'phase2': '#ff4444',          # Red - negative control
    'phase3': '#00ff88',          # Green - full validation
    'phase4': '#a855f7',          # Purple - temporal comparison
    'arrow': '#666666',           # Grey arrows
}


def create_figure(output_path):
    """Create validation pipeline figure with dark theme."""

    # Set dark theme
    plt.style.use('dark_background')

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    fig.patch.set_facecolor(DARK_THEME['background'])
    ax.set_facecolor(DARK_THEME['background'])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Title
    ax.text(7, 9.5, 'Multi-Phase Validation Pipeline',
            fontsize=18, fontweight='bold', ha='center', va='top',
            color=DARK_THEME['text'])
    ax.text(7, 8.9, 'Progressive Validation with Negative Controls',
            fontsize=12, ha='center', va='top', color=DARK_THEME['dim'],
            style='italic')

    # Phase definitions
    phases = [
        {
            'name': 'Phase 1',
            'title': 'Baseline',
            'subtitle': 'Q1 2024',
            'detection': '71.2%',
            'windows': '52 windows',
            'color': DARK_THEME['phase1'],
            'x': 1.5,
            'description': 'Initial detection\nrate establishes\nbaseline capability'
        },
        {
            'name': 'Phase 2',
            'title': 'Negative Control',
            'subtitle': 'Shuffled Data',
            'detection': '6.3%',
            'windows': '52 windows',
            'color': DARK_THEME['phase2'],
            'x': 4.5,
            'description': 'Randomized temporal\nstructure destroys\nregime patterns'
        },
        {
            'name': 'Phase 3',
            'title': 'Full Validation',
            'subtitle': '2024 Full Year',
            'detection': '81.2%',
            'windows': '223 windows',
            'color': DARK_THEME['phase3'],
            'x': 7.5,
            'description': 'Extended validation\nconfirms consistent\nregime detection'
        },
        {
            'name': 'Phase 4',
            'title': 'Temporal Comparison',
            'subtitle': '2020 Pre-0DTE',
            'detection': '12.1%',
            'windows': '223 windows',
            'color': DARK_THEME['phase4'],
            'x': 10.5,
            'description': 'Pre-0DTE era shows\nminimal regime\npresence'
        },
    ]

    box_width = 2.2
    box_height = 3.5
    y_center = 5.0

    # Draw phases
    for phase in phases:
        x = phase['x']
        y = y_center - box_height/2

        # Main box
        box = FancyBboxPatch((x, y), box_width, box_height,
                             boxstyle="round,pad=0.1",
                             facecolor=DARK_THEME['panel_bg'],
                             edgecolor=phase['color'],
                             linewidth=3, alpha=0.95)
        ax.add_patch(box)

        # Phase name header
        ax.text(x + box_width/2, y + box_height - 0.3, phase['name'],
                ha='center', va='top', fontsize=10, fontweight='bold',
                color=phase['color'])

        # Title
        ax.text(x + box_width/2, y + box_height - 0.7, phase['title'],
                ha='center', va='top', fontsize=12, fontweight='bold',
                color=DARK_THEME['text'])

        # Subtitle
        ax.text(x + box_width/2, y + box_height - 1.1, phase['subtitle'],
                ha='center', va='top', fontsize=9,
                color=DARK_THEME['dim'], style='italic')

        # Detection rate (large, prominent)
        ax.text(x + box_width/2, y + box_height/2 - 0.2, phase['detection'],
                ha='center', va='center', fontsize=24, fontweight='bold',
                color=phase['color'])

        # Windows count
        ax.text(x + box_width/2, y + box_height/2 - 0.8, phase['windows'],
                ha='center', va='center', fontsize=9,
                color=DARK_THEME['dim'])

        # Description
        ax.text(x + box_width/2, y + 0.6, phase['description'],
                ha='center', va='center', fontsize=8,
                color=DARK_THEME['text'], linespacing=1.2)

    # Draw arrows between phases
    arrow_y = y_center
    arrow_style = dict(arrowstyle='->', lw=2.5, color=DARK_THEME['arrow'],
                       connectionstyle='arc3,rad=0')

    for i in range(len(phases) - 1):
        x_start = phases[i]['x'] + box_width
        x_end = phases[i + 1]['x']
        ax.annotate('', xy=(x_end, arrow_y), xytext=(x_start, arrow_y),
                    arrowprops=arrow_style)

    # Key findings box at bottom
    findings_y = 0.8
    findings_box = FancyBboxPatch((1.5, findings_y - 0.6), 11.2, 1.2,
                                   boxstyle="round,pad=0.1",
                                   facecolor=DARK_THEME['panel_bg'],
                                   edgecolor=DARK_THEME['accent_warning'],
                                   linewidth=2, linestyle='--', alpha=0.9)
    ax.add_patch(findings_box)

    findings_text = (
        "Key Result: 69.1 percentage point discrimination (81.2% vs 12.1%) between 2024 and 2020 "
        "(p < 0.0001, φ = 0.672)\n"
        "Negative control (6.3%) confirms detection requires temporal structure, not just statistical distribution"
    )
    ax.text(7.1, findings_y, findings_text,
            ha='center', va='center', fontsize=10,
            color=DARK_THEME['text'], wrap=True)

    # Phase 4A expansion note (top right)
    expansion_text = (
        "Phase 4A Expansion (2020-2025):\n"
        "1,412 total windows validated\n"
        "2023→2024 structural shift identified"
    )
    ax.text(13.5, 8.5, expansion_text,
            ha='right', va='top', fontsize=9,
            color=DARK_THEME['dim'],
            bbox=dict(boxstyle='round,pad=0.4',
                      facecolor=DARK_THEME['panel_bg'],
                      edgecolor=DARK_THEME['dim'],
                      linewidth=1, alpha=0.8))

    plt.tight_layout()

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight',
                facecolor=DARK_THEME['background'], edgecolor='none')
    plt.close()

    # Reset style
    plt.style.use('default')

    print(f"Figure saved: {output_path}")


def main():
    print("Generating Validation Pipeline Figure (Dark Theme #216)...")
    output_path = OUTPUT_DIR / "fig04_validation_pipeline.png"
    create_figure(output_path)
    print("\nDone!")


if __name__ == "__main__":
    main()
