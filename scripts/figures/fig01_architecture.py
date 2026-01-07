#!/usr/bin/env python3
"""
Generate Figure 1: LLM Regime Detection System Architecture

Creates a pipeline diagram showing the 5 stages:
1. Data Ingestion (Alpha Vantage API)
2. GEX Calculation (OI/Volume aggregation)
3. Temporal Obfuscation
4. 30-Day Window Generation
5. LLM Analysis (OpenAI o4-mini)

Updated with SpotGamma-inspired dark theme (Issue #216).

Output: docs/papers/paper2/figures/output/fig01_architecture.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
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
    # Stage-specific colors
    'stage1': '#00d4ff',          # Cyan - Data Ingestion
    'stage2': '#00ff88',          # Green - GEX Calculation
    'stage3': '#ffaa00',          # Amber - Obfuscation
    'stage4': '#a855f7',          # Purple - Window Generation
    'stage5': '#ff6b6b',          # Coral - LLM Analysis
    'arrow': '#888888',           # Grey arrows
    'data_flow': '#4a4a6a',       # Muted for data examples
}


def create_figure(output_path):
    """Create architecture diagram with dark theme."""

    # Set dark theme
    plt.style.use('dark_background')

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor(DARK_THEME['background'])
    ax.set_facecolor(DARK_THEME['background'])
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis('off')

    # Title
    ax.text(8, 8.6, 'LLM Regime Detection System Architecture',
            fontsize=18, fontweight='bold', ha='center', va='top',
            color=DARK_THEME['text'])
    ax.text(8, 8.1, 'Five-Stage Pipeline: From Raw Options Data to Regime Classification',
            fontsize=11, ha='center', va='top', color=DARK_THEME['dim'],
            style='italic')

    # Stage definitions
    stages = [
        {
            'num': '1',
            'title': 'Data Ingestion',
            'subtitle': 'Alpha Vantage API',
            'color': DARK_THEME['stage1'],
            'x': 0.5,
            'details': [
                'SPY options chains',
                'OI + Volume data',
                '2020-2025 historical'
            ],
            'icon': '📊'
        },
        {
            'num': '2',
            'title': 'GEX Calculation',
            'subtitle': 'Gamma Exposure',
            'color': DARK_THEME['stage2'],
            'x': 3.5,
            'details': [
                'Call/Put aggregation',
                'Strike-level gamma',
                'Daily net GEX ($B)'
            ],
            'icon': '∑'
        },
        {
            'num': '3',
            'title': 'Temporal Obfuscation',
            'subtitle': 'Anti-Memorization',
            'color': DARK_THEME['stage3'],
            'x': 6.5,
            'details': [
                'Remove dates/tickers',
                'Preserve structure',
                'Sequential Day N'
            ],
            'icon': '🔒'
        },
        {
            'num': '4',
            'title': 'Window Generation',
            'subtitle': '30-Day Rolling',
            'color': DARK_THEME['stage4'],
            'x': 9.5,
            'details': [
                '30-day windows',
                'Weekly sliding',
                '223+ windows/year'
            ],
            'icon': '📅'
        },
        {
            'num': '5',
            'title': 'LLM Analysis',
            'subtitle': 'OpenAI o4-mini',
            'color': DARK_THEME['stage5'],
            'x': 12.5,
            'details': [
                'Batch API (50% cost)',
                'Chain-of-thought',
                'Regime classification'
            ],
            'icon': '🤖'
        },
    ]

    box_width = 2.5
    box_height = 4.0
    y_center = 4.5

    # Draw stages
    for stage in stages:
        x = stage['x']
        y = y_center - box_height/2

        # Main box with rounded corners
        box = FancyBboxPatch((x, y), box_width, box_height,
                             boxstyle="round,pad=0.15",
                             facecolor=DARK_THEME['panel_bg'],
                             edgecolor=stage['color'],
                             linewidth=2.5, alpha=0.95)
        ax.add_patch(box)

        # Stage number circle
        circle = plt.Circle((x + 0.4, y + box_height - 0.4), 0.25,
                            facecolor=stage['color'], edgecolor=DARK_THEME['background'],
                            linewidth=2, zorder=5)
        ax.add_patch(circle)
        ax.text(x + 0.4, y + box_height - 0.4, stage['num'],
                ha='center', va='center', fontsize=11, fontweight='bold',
                color=DARK_THEME['background'], zorder=6)

        # Title
        ax.text(x + box_width/2, y + box_height - 0.8, stage['title'],
                ha='center', va='top', fontsize=12, fontweight='bold',
                color=DARK_THEME['text'])

        # Subtitle
        ax.text(x + box_width/2, y + box_height - 1.2, stage['subtitle'],
                ha='center', va='top', fontsize=9,
                color=stage['color'], style='italic')

        # Details list
        detail_y = y + box_height - 1.8
        for detail in stage['details']:
            ax.text(x + 0.3, detail_y, f"• {detail}",
                    ha='left', va='top', fontsize=9,
                    color=DARK_THEME['text'])
            detail_y -= 0.5

    # Draw arrows between stages
    arrow_y = y_center
    for i in range(len(stages) - 1):
        x_start = stages[i]['x'] + box_width
        x_end = stages[i + 1]['x']

        # Arrow
        ax.annotate('', xy=(x_end - 0.1, arrow_y),
                    xytext=(x_start + 0.1, arrow_y),
                    arrowprops=dict(arrowstyle='->', lw=2.5,
                                    color=DARK_THEME['arrow'],
                                    connectionstyle='arc3,rad=0'))

    # Data flow examples (bottom)
    flow_y = 1.2
    flow_box_width = 2.3

    # Example data at each stage
    examples = [
        {'x': 0.6, 'text': 'Raw Chain:\n2024-03-15\nSPY 510C\nOI: 45,231'},
        {'x': 3.6, 'text': 'Daily GEX:\nDay: 2024-03-15\nGEX: -$12.3B\nNet Gamma: -0.8'},
        {'x': 6.6, 'text': 'Obfuscated:\nDay 15\nGEX: -$12.3B\n(No dates/tickers)'},
        {'x': 9.6, 'text': '30-Day Window:\nDay 1: -$8.2B\n...\nDay 30: -$15.1B'},
        {'x': 12.6, 'text': 'Classification:\nPERSISTENT_NEG\nConf: 94%\nFlips: 2'},
    ]

    for ex in examples:
        # Small data box
        data_box = FancyBboxPatch((ex['x'], flow_y - 0.9), flow_box_width, 1.5,
                                   boxstyle="round,pad=0.1",
                                   facecolor=DARK_THEME['data_flow'],
                                   edgecolor=DARK_THEME['dim'],
                                   linewidth=1, alpha=0.8)
        ax.add_patch(data_box)
        ax.text(ex['x'] + flow_box_width/2, flow_y - 0.15, ex['text'],
                ha='center', va='center', fontsize=7,
                color=DARK_THEME['text'], family='monospace')

    # Data flow label
    ax.text(0.3, flow_y - 0.15, 'Data\nFlow:', ha='right', va='center',
            fontsize=8, fontweight='bold', color=DARK_THEME['dim'])

    # Output summary (right side)
    output_text = (
        "Output:\n"
        "• Regime Type\n"
        "• Confidence %\n"
        "• Persistence %\n"
        "• Sign Flips\n"
        "• Chain-of-Thought"
    )
    ax.text(15.5, 4.5, output_text,
            ha='left', va='center', fontsize=9,
            color=DARK_THEME['text'],
            bbox=dict(boxstyle='round,pad=0.4',
                      facecolor=DARK_THEME['panel_bg'],
                      edgecolor=DARK_THEME['accent_positive'],
                      linewidth=2, alpha=0.9))

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
    print("Generating Architecture Figure (Dark Theme #216)...")
    output_path = OUTPUT_DIR / "fig01_architecture.png"
    create_figure(output_path)
    print("\nDone!")


if __name__ == "__main__":
    main()
