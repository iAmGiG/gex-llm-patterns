"""
Generate sensitivity analysis figure for IEEE Access paper.

Creates a 2x2 panel figure showing detection rate stability across
threshold variations for all four sensitivity tests.

Output: docs/papers/ieee_access/figures/fig14_sensitivity.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = PROJECT_ROOT / "reports" / "validation" / "sensitivity_analysis" / "threshold_sensitivity.yaml"
OUTPUT_PATH = PROJECT_ROOT / "docs" / "papers" / "ieee_access" / "figures" / "fig14_sensitivity.png"

# IEEE-friendly colors
COLORS = {
    2020: "#757575",
    2021: "#9E9E9E",
    2022: "#FF9800",
    2023: "#4CAF50",
    2024: "#1565C0",
    2025: "#0D47A1",
}
YEAR_LABELS = {
    2020: "2020",
    2021: "2021",
    2022: "2022",
    2023: "2023",
    2024: "2024",
    2025: "2025",
}


def load_results():
    with open(RESULTS_PATH) as f:
        return yaml.safe_load(f)


def plot_test(ax, test_data, param_label, default_val, xlabel):
    """Plot a single sensitivity test panel."""
    labels = list(test_data["values"].keys())
    years_to_plot = [2020, 2022, 2023, 2024]

    for year in years_to_plot:
        rates = []
        for label in labels:
            by_year = test_data["values"][label]["by_year"]
            rate = by_year.get(year, by_year.get(str(year), {})).get("rate", 0)
            rates.append(rate)
        ax.plot(range(len(labels)), rates, 'o-', color=COLORS[year],
                label=YEAR_LABELS[year], linewidth=1.5, markersize=4)

    # Mark default threshold
    if default_val in labels:
        idx = labels.index(default_val)
        ax.axvline(x=idx, color='#C62828', linestyle='--', alpha=0.6,
                   linewidth=1, label=f'Default ({default_val})')

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8, rotation=45 if len(labels) > 6 else 0)
    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel('Detection Rate (%)', fontsize=9)
    ax.set_ylim(-5, 105)
    ax.grid(True, alpha=0.3, linewidth=0.5)
    ax.legend(fontsize=7, loc='center left')
    ax.tick_params(labelsize=8)


def main():
    results = load_results()

    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), dpi=300)
    fig.patch.set_facecolor('white')

    # Test 1: Persistence
    plot_test(axes[0, 0], results["test1_persistence"],
              "persistence", "70%", "Persistence Threshold")
    axes[0, 0].set_title("(a) Persistence Threshold", fontsize=10, fontweight='bold')

    # Test 2: Magnitude
    plot_test(axes[0, 1], results["test2_magnitude"],
              "magnitude", "$5B", "Magnitude Threshold")
    axes[0, 1].set_title("(b) Magnitude Threshold", fontsize=10, fontweight='bold')

    # Test 3: Stability (flips)
    plot_test(axes[1, 0], results["test3_stability"],
              "flips", "5 flips", "Max Sign Flips")
    axes[1, 0].set_title("(c) Stability (Max Flips)", fontsize=10, fontweight='bold')

    # Test 4: Combined — bar chart
    ax = axes[1, 1]
    test4 = results["test4_combined"]
    labels = list(test4["values"].keys())
    def get_rate(val_dict, year):
        by_year = val_dict["by_year"]
        return by_year.get(year, by_year.get(str(year), {})).get("rate", 0)

    rates_2020 = [get_rate(test4["values"][l], 2020) for l in labels]
    rates_2024 = [get_rate(test4["values"][l], 2024) for l in labels]

    x = np.arange(len(labels))
    width = 0.35
    ax.bar(x - width / 2, rates_2020, width, label='2020', color=COLORS[2020])
    ax.bar(x + width / 2, rates_2024, width, label='2024', color=COLORS[2024])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel("Combined Threshold Shift", fontsize=9)
    ax.set_ylabel("Detection Rate (%)", fontsize=9)
    ax.set_ylim(0, 110)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, linewidth=0.5, axis='y')
    ax.tick_params(labelsize=8)
    ax.set_title("(d) Combined Threshold Shift", fontsize=10, fontweight='bold')

    # Add effect size annotations on bars
    for i, (r20, r24) in enumerate(zip(rates_2020, rates_2024)):
        effect = r24 - r20
        ax.annotate(f'+{effect:.0f}pp', xy=(i, r24 + 2),
                    ha='center', fontsize=7, color=COLORS[2024])

    fig.suptitle("Threshold Sensitivity Analysis: Detection Rate Robustness",
                 fontsize=12, fontweight='bold', y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"Figure saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
