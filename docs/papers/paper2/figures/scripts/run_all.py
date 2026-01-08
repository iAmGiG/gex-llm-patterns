#!/usr/bin/env python3
"""
Run All Paper 2 Figure Generation Scripts

Generates all 11 publication-quality figures for Paper #2.

Usage:
    python run_all.py              # Generate all figures
    python run_all.py --check      # Check which figures exist
    python run_all.py fig01 fig05  # Generate specific figures

Output: ../output/fig01_*.png through fig11_*.png
"""

import argparse
import importlib
import sys
import time
from pathlib import Path

# Add script directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from theme import OUTPUT_DIR

# Figure definitions
FIGURES = {
    'fig01': {
        'module': 'fig01_architecture',
        'output': 'fig01_architecture.png',
        'description': 'LLM Regime Detection System Architecture',
        'deps': [],  # No database dependencies
    },
    'fig02': {
        'module': 'fig02_regime_window_example',
        'output': 'fig02_regime_window.png',
        'description': '30-Day Persistent Negative Regime Example',
        'deps': ['database'],  # Optional database
    },
    'fig03': {
        'module': 'fig03_obfuscation',
        'output': 'fig03_obfuscation.png',
        'description': 'Temporal Obfuscation Process',
        'deps': [],
    },
    'fig04': {
        'module': 'fig04_validation_pipeline',
        'output': 'fig04_validation_pipeline.png',
        'description': 'Multi-Phase Validation Pipeline',
        'deps': [],
    },
    'fig05': {
        'module': 'fig05_selectivity_demo',
        'output': 'fig05_selectivity.png',
        'description': 'Framework Selectivity Demonstration',
        'deps': [],
    },
    'fig06': {
        'module': 'fig06_gex_magnitude_distribution',
        'output': 'fig06_gex_magnitude_distribution.png',
        'description': 'GEX Magnitude Distribution (2020 vs 2024)',
        'deps': ['database'],
    },
    'fig07': {
        'module': 'fig07_confidence_discrimination',
        'output': 'fig07_confidence_discrimination.png',
        'description': 'Confidence vs Persistence Discrimination',
        'deps': ['database'],
    },
    'fig08': {
        'module': 'fig08_detection_progression',
        'output': 'fig08_detection_progression.png',
        'description': 'Detection Rate Temporal Progression (2020-2025)',
        'deps': ['database'],
    },
    'fig09': {
        'module': 'fig09_scar_tissue',
        'output': 'fig09_scar_tissue.png',
        'description': 'Scar Tissue Mechanism Diagram',
        'deps': [],
    },
    'fig10': {
        'module': 'fig10_borderline_persistence',
        'output': 'fig10_borderline_persistence.png',
        'description': 'Borderline Persistence Region Analysis',
        'deps': ['database'],
    },
    'fig11': {
        'module': 'fig11_threshold_sensitivity_heatmap',
        'output': 'fig11_threshold_sensitivity.png',
        'description': 'Threshold Sensitivity Heatmap',
        'deps': ['database'],
    },
}


def check_figures():
    """Check which figures exist in output directory."""
    print("=" * 60)
    print("Figure Status Check")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for fig_id, info in FIGURES.items():
        output_path = OUTPUT_DIR / info['output']
        exists = output_path.exists()
        status = "EXISTS" if exists else "MISSING"
        symbol = "[x]" if exists else "[ ]"

        if exists:
            size = output_path.stat().st_size / 1024
            mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(output_path.stat().st_mtime))
            print(f"{symbol} {fig_id}: {info['description'][:40]:<40} ({size:.0f} KB, {mtime})")
        else:
            print(f"{symbol} {fig_id}: {info['description'][:40]:<40} (MISSING)")

    print("=" * 60)

    existing = sum(1 for info in FIGURES.values() if (OUTPUT_DIR / info['output']).exists())
    print(f"Total: {existing}/{len(FIGURES)} figures generated")


def generate_figure(fig_id: str) -> bool:
    """Generate a single figure by ID."""
    if fig_id not in FIGURES:
        print(f"Unknown figure: {fig_id}")
        return False

    info = FIGURES[fig_id]
    print(f"\n{'='*60}")
    print(f"Generating {fig_id}: {info['description']}")
    print(f"{'='*60}")

    try:
        # Import the module
        module = importlib.import_module(info['module'])

        # Run main()
        start_time = time.time()
        module.main()
        elapsed = time.time() - start_time

        # Verify output
        output_path = OUTPUT_DIR / info['output']
        if output_path.exists():
            size = output_path.stat().st_size / 1024
            print(f"Success: {output_path.name} ({size:.0f} KB) in {elapsed:.1f}s")
            return True
        else:
            print(f"Warning: Script ran but output not found at {output_path}")
            return False

    except Exception as e:
        print(f"Error generating {fig_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_all():
    """Generate all figures."""
    print("=" * 60)
    print("Paper #2 Figure Generation")
    print("SpotGamma Dark Theme")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    total_start = time.time()

    for fig_id in FIGURES:
        success = generate_figure(fig_id)
        results[fig_id] = success

    total_elapsed = time.time() - total_start

    # Summary
    print("\n" + "=" * 60)
    print("Generation Summary")
    print("=" * 60)

    succeeded = sum(1 for v in results.values() if v)
    failed = len(results) - succeeded

    for fig_id, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {fig_id}: {status}")

    print(f"\nTotal: {succeeded}/{len(results)} succeeded, {failed} failed")
    print(f"Time: {total_elapsed:.1f}s")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description='Generate Paper #2 figures',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_all.py              # Generate all figures
    python run_all.py --check      # Check which figures exist
    python run_all.py fig01 fig05  # Generate specific figures
    python run_all.py --list       # List all available figures
        """
    )

    parser.add_argument('figures', nargs='*', help='Specific figures to generate (e.g., fig01 fig05)')
    parser.add_argument('--check', action='store_true', help='Check which figures exist')
    parser.add_argument('--list', action='store_true', help='List all available figures')

    args = parser.parse_args()

    if args.list:
        print("Available figures:")
        for fig_id, info in FIGURES.items():
            deps = ', '.join(info['deps']) if info['deps'] else 'none'
            print(f"  {fig_id}: {info['description']} (deps: {deps})")
        return

    if args.check:
        check_figures()
        return

    if args.figures:
        # Generate specific figures
        success = True
        for fig_id in args.figures:
            if not generate_figure(fig_id):
                success = False
        sys.exit(0 if success else 1)
    else:
        # Generate all figures
        success = generate_all()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
