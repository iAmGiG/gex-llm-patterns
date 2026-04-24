"""Threshold sensitivity sweep for Paper 2 regime-detection framework.

Addresses Reviewer 3 comment R3.4b: "The choice of thresholds
(70% persistence, $5B magnitude, <=5 flips) must be justified or tested
through sensitivity analysis."

Approach. We apply the mechanical three-criterion classifier at a grid of
alternative thresholds to the per-window raw metrics already stored under
reports/validation/paper2_regime_windows/ for Phase 3 (full 2024, N=223)
and Phase 4 (full 2020, N=223). At each threshold triple we compute the
detection rate in 2024, the detection rate in 2020, and the gap --
exactly the headline 69.1pp separation from the paper -- and verify
the gap remains statistically and economically meaningful across the
grid rather than being a point result.

This reuses stored per-window metrics (persistence_pct,
avg_magnitude_billions, sign_flips) and does not re-query the LLM.
No GPU required; completes in seconds.

Grid:
  persistence_pct >= P, P in {60, 65, 70, 75, 80}
  avg_magnitude_billions >= M, M in {3, 5, 7}
  sign_flips <= F, F in {3, 5, 7}
Total: 5 * 3 * 3 = 45 configurations.

Outputs:
  reports/validation/paper2_regime_windows/jrfm_revision_threshold_sensitivity.yaml
  docs/papers/paper2/figures/output/fig09_threshold_sensitivity.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
WINDOWS_DIR = REPO_ROOT / "reports" / "validation" / "paper2_regime_windows"
FIG_DIR = REPO_ROOT / "docs" / "papers" / "paper2" / "figures" / "output"
OUTPUT_YAML = WINDOWS_DIR / "jrfm_revision_threshold_sensitivity.yaml"
OUTPUT_PNG = FIG_DIR / "fig09_threshold_sensitivity.png"

# Default thresholds used in the paper
DEFAULT_P = 70.0
DEFAULT_M = 5.0
DEFAULT_F = 5

# Sweep grid
P_GRID = [60, 65, 70, 75, 80]
M_GRID = [3, 5, 7]
F_GRID = [3, 5, 7]


def load_window_metrics(path: Path) -> list[dict]:
    """Return list of dicts with persistence_pct, avg_magnitude_billions, sign_flips."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    out = []
    for w in data.get("windows", []) or []:
        raw = w.get("raw_response") or {}
        p = raw.get("persistence_pct")
        m = raw.get("avg_magnitude_billions")
        fl = raw.get("sign_flips")
        if p is None or m is None or fl is None:
            continue
        out.append(
            {
                "persistence_pct": float(p),
                "avg_magnitude_billions": float(m),
                "sign_flips": int(fl),
            }
        )
    return out


def classify(metrics: list[dict], p: float, m: float, f: int) -> np.ndarray:
    """Return boolean array: True iff all three criteria pass."""
    arr = np.array(
        [(x["persistence_pct"] >= p and x["avg_magnitude_billions"] >= m and x["sign_flips"] <= f) for x in metrics],
        dtype=bool,
    )
    return arr


def sweep(metrics_2024: list[dict], metrics_2020: list[dict]) -> list[dict]:
    """Run the full grid and return per-config detection rates and gaps."""
    results = []
    for p in P_GRID:
        for m in M_GRID:
            for f in F_GRID:
                d24 = classify(metrics_2024, p, m, f)
                d20 = classify(metrics_2020, p, m, f)
                r24 = float(d24.mean() * 100)
                r20 = float(d20.mean() * 100)
                results.append(
                    {
                        "persistence_pct_threshold": p,
                        "magnitude_threshold_usd_billions": m,
                        "flip_threshold": f,
                        "n_2024": int(len(d24)),
                        "n_2020": int(len(d20)),
                        "k_2024": int(d24.sum()),
                        "k_2020": int(d20.sum()),
                        "rate_2024_pct": round(r24, 2),
                        "rate_2020_pct": round(r20, 2),
                        "gap_pp": round(r24 - r20, 2),
                        "is_default": (p == DEFAULT_P and m == DEFAULT_M and f == DEFAULT_F),
                    }
                )
    return results


def plot_heatmap(results: list[dict]) -> None:
    """Render a 1x3 grid of heatmaps: one per flip threshold.

    X axis: persistence thresholds; Y axis: magnitude thresholds.
    Cell value: 2024-2020 detection gap in percentage points.
    """
    import matplotlib.pyplot as plt

    # Build a (flip, M, P) -> gap lookup
    f_values = sorted(set(r["flip_threshold"] for r in results))
    m_values = sorted(set(r["magnitude_threshold_usd_billions"] for r in results))
    p_values = sorted(set(r["persistence_pct_threshold"] for r in results))

    fig, axes = plt.subplots(1, len(f_values), figsize=(12.5, 4.0), sharey=True, constrained_layout=True)

    # shared color range so panels are comparable
    all_gaps = [r["gap_pp"] for r in results]
    vmin, vmax = min(all_gaps), max(all_gaps)

    for i, f in enumerate(f_values):
        ax = axes[i]
        grid = np.zeros((len(m_values), len(p_values)))
        for r in results:
            if r["flip_threshold"] != f:
                continue
            yi = m_values.index(r["magnitude_threshold_usd_billions"])
            xi = p_values.index(r["persistence_pct_threshold"])
            grid[yi, xi] = r["gap_pp"]
        im = ax.imshow(
            grid,
            origin="lower",
            vmin=vmin,
            vmax=vmax,
            cmap="viridis",
            aspect="auto",
        )
        ax.set_xticks(range(len(p_values)))
        ax.set_xticklabels([f"{p}%" for p in p_values])
        ax.set_yticks(range(len(m_values)))
        ax.set_yticklabels([f"${m}B" for m in m_values])
        ax.set_xlabel("Persistence threshold")
        if i == 0:
            ax.set_ylabel("Magnitude threshold")
        ax.set_title(f"Flips $\\leq$ {f}")

        # annotate cells
        for yi in range(len(m_values)):
            for xi in range(len(p_values)):
                val = grid[yi, xi]
                ax.text(
                    xi,
                    yi,
                    f"{val:.0f}",
                    ha="center",
                    va="center",
                    color="white" if val < (vmin + vmax) / 2 else "black",
                    fontsize=12,
                )

        # mark the paper default with a red box
        if f == DEFAULT_F:
            xi_def = p_values.index(DEFAULT_P)
            yi_def = m_values.index(DEFAULT_M)
            rect = plt.Rectangle(
                (xi_def - 0.5, yi_def - 0.5),
                1,
                1,
                fill=False,
                edgecolor="red",
                linewidth=2.2,
            )
            ax.add_patch(rect)

    cbar = fig.colorbar(im, ax=axes, shrink=0.9, label="2024 - 2020 detection gap (pp)")
    fig.suptitle(
        "Threshold sensitivity: 2024 vs 2020 detection gap across 45 configurations\n"
        "(red box marks the paper default: persistence >= 70%, magnitude >= $5B, flips <= 5)",
        fontsize=13,
    )

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    p3 = WINDOWS_DIR / "phase3_baseline_2024_full_year.yaml"
    p4 = WINDOWS_DIR / "phase4_baseline_2020.yaml"
    if not p3.exists() or not p4.exists():
        print("Missing Phase 3/4 YAMLs", file=sys.stderr)
        return 1

    metrics_2024 = load_window_metrics(p3)
    metrics_2020 = load_window_metrics(p4)
    print(f"Loaded {len(metrics_2024)} 2024 windows and {len(metrics_2020)} 2020 windows")

    results = sweep(metrics_2024, metrics_2020)

    # Summary statistics
    gaps = [r["gap_pp"] for r in results]
    rate_24 = [r["rate_2024_pct"] for r in results]
    rate_20 = [r["rate_2020_pct"] for r in results]
    default_row = next(r for r in results if r["is_default"])

    summary = {
        "n_configs": len(results),
        "gap_min_pp": float(min(gaps)),
        "gap_max_pp": float(max(gaps)),
        "gap_median_pp": float(np.median(gaps)),
        "configs_with_gap_gt_50pp": int(sum(1 for g in gaps if g > 50)),
        "configs_with_gap_gt_60pp": int(sum(1 for g in gaps if g > 60)),
        "rate_2024_range_pct": [float(min(rate_24)), float(max(rate_24))],
        "rate_2020_range_pct": [float(min(rate_20)), float(max(rate_20))],
        "default_config": default_row,
    }

    out = {
        "metadata": {
            "script": "scripts/validation/paper2/jrfm_revision/threshold_sensitivity.py",
            "purpose": "Threshold sensitivity sweep (JRFM R3.4b)",
            "grid_persistence_pct": P_GRID,
            "grid_magnitude_usd_billions": M_GRID,
            "grid_flips": F_GRID,
            "data_sources": [
                "reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml",
                "reports/validation/paper2_regime_windows/phase4_baseline_2020.yaml",
            ],
        },
        "summary": summary,
        "configs": results,
    }
    with OUTPUT_YAML.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, sort_keys=False, default_flow_style=False)

    # Print table
    print()
    print(f"{'P':>4} {'M':>4} {'F':>3} " f"{'2024 det':>10} {'2020 det':>10} {'gap pp':>8}")
    print("-" * 50)
    for r in results:
        marker = "*" if r["is_default"] else " "
        print(
            f"{marker}{r['persistence_pct_threshold']:>3}% "
            f"${r['magnitude_threshold_usd_billions']:>2}B "
            f"<={r['flip_threshold']:>2} "
            f"{r['rate_2024_pct']:>9.1f}% "
            f"{r['rate_2020_pct']:>9.1f}% "
            f"{r['gap_pp']:>7.1f}"
        )

    print()
    print("Summary:")
    print(
        f"  Gap range across {summary['n_configs']} configs: "
        f"[{summary['gap_min_pp']:.1f}, {summary['gap_max_pp']:.1f}] pp "
        f"(median {summary['gap_median_pp']:.1f})"
    )
    print(f"  Configs with gap > 50pp: {summary['configs_with_gap_gt_50pp']}/{summary['n_configs']}")
    print(f"  Configs with gap > 60pp: {summary['configs_with_gap_gt_60pp']}/{summary['n_configs']}")
    print(f"  2024 detection rate range: {summary['rate_2024_range_pct']}")
    print(f"  2020 detection rate range: {summary['rate_2020_range_pct']}")
    print()

    plot_heatmap(results)
    print(f"Wrote {OUTPUT_YAML}")
    print(f"Wrote {OUTPUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
