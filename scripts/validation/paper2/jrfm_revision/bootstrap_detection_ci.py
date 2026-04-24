"""Bootstrap 95% confidence intervals for every detection rate reported in
the Paper 2 JRFM revision.

Addresses Reviewer 3 comment R3.5a: "The paper relies heavily on percentages
without reporting statistical significance, confidence intervals, or
robustness tests. These must be added."

For phases where per-window records exist (Phase 1, 3, 4, and Phase 2
negative controls), we compute a 95% percentile bootstrap CI using 10,000
resamples with replacement at the window level. For Phase 5 multi-year
per-year rates where only aggregate counts are available in the published
manuscript, we fall back to Wilson score confidence intervals, which give
equivalent coverage properties for binomial proportions and are standard
in medical / survey statistics (Brown, Cai & DasGupta, Statistical
Science, 2001).

Usage:
    python bootstrap_detection_ci.py

Outputs:
    reports/validation/paper2_regime_windows/jrfm_revision_ci.yaml
    (written next to the input YAMLs for reproducibility)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import yaml
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[4]
WINDOWS_DIR = REPO_ROOT / "reports" / "validation" / "paper2_regime_windows"
OUTPUT_YAML = WINDOWS_DIR / "jrfm_revision_ci.yaml"

N_BOOTSTRAP = 10_000
RNG_SEED = 20260424  # deterministic replication


def wilson_ci(successes: int, total: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion (returns lo, hi in [0, 1])."""
    if total == 0:
        return (0.0, 1.0)
    z = stats.norm.ppf(1 - alpha / 2)
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(outcomes: np.ndarray, alpha: float = 0.05, n_boot: int = N_BOOTSTRAP) -> tuple[float, float]:
    """95% percentile bootstrap interval on the mean of binary outcomes."""
    rng = np.random.default_rng(RNG_SEED)
    idx = rng.integers(0, len(outcomes), size=(n_boot, len(outcomes)))
    boot_means = outcomes[idx].mean(axis=1)
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(lo), float(hi))


def load_windows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("windows", []) or []


def outcomes_from_windows(windows: list[dict]) -> np.ndarray:
    """Extract binary regime_detected outcomes as a 0/1 numpy array."""
    return np.array([int(bool(w.get("regime_detected"))) for w in windows], dtype=int)


def summarise(label: str, outcomes: np.ndarray) -> dict:
    n = len(outcomes)
    k = int(outcomes.sum())
    rate = k / n if n else float("nan")
    boot_lo, boot_hi = bootstrap_ci(outcomes)
    wil_lo, wil_hi = wilson_ci(k, n)
    return {
        "label": label,
        "n": int(n),
        "k": int(k),
        "rate_pct": float(round(rate * 100, 2)),
        "bootstrap_ci_pct": [float(round(boot_lo * 100, 2)), float(round(boot_hi * 100, 2))],
        "wilson_ci_pct": [float(round(wil_lo * 100, 2)), float(round(wil_hi * 100, 2))],
    }


def summarise_counts_only(label: str, k: int, n: int) -> dict:
    """For sources where only aggregate counts are available (Phase 5 per-year)."""
    rate = k / n if n else float("nan")
    wil_lo, wil_hi = wilson_ci(k, n)
    return {
        "label": label,
        "n": int(n),
        "k": int(k),
        "rate_pct": float(round(rate * 100, 2)),
        "bootstrap_ci_pct": None,
        "wilson_ci_pct": [float(round(wil_lo * 100, 2)), float(round(wil_hi * 100, 2))],
        "note": "Wilson CI only (per-window records not retained at publication time).",
    }


def main() -> int:
    # 1. Phases with per-window YAML records
    phase_specs = [
        ("Phase 1 baseline (2024 Q1)", WINDOWS_DIR / "phase1_baseline_2024Q1.yaml"),
        ("Phase 3 full 2024", WINDOWS_DIR / "phase3_baseline_2024_full_year.yaml"),
        ("Phase 4 full 2020", WINDOWS_DIR / "phase4_baseline_2020.yaml"),
        ("Phase 2a shuffle 2024 Q1", WINDOWS_DIR / "phase2a_shuffle_2024Q1.yaml"),
        ("Phase 2a shuffle 2020", WINDOWS_DIR / "phase2a_shuffle_2020.yaml"),
        ("Phase 2b transitional 2024 Q1", WINDOWS_DIR / "phase2b_transitional_2024Q1.yaml"),
        ("Phase 2b transitional 2020", WINDOWS_DIR / "phase2b_transitional_2020.yaml"),
        ("Phase 2c low-magnitude 2024 Q1", WINDOWS_DIR / "phase2c_low_magnitude_2024Q1.yaml"),
        ("Phase 2c low-magnitude 2020", WINDOWS_DIR / "phase2c_low_magnitude_2020.yaml"),
    ]

    summaries = []
    for label, path in phase_specs:
        if not path.exists():
            print(f"WARNING: {path} missing, skipping", file=sys.stderr)
            continue
        windows = load_windows(path)
        outcomes = outcomes_from_windows(windows)
        summaries.append(summarise(label, outcomes))

    # 2. Phase 5 multi-year per-year rates (counts from published Table 3)
    phase5_counts = [
        ("Phase 5 2020", 26, 213),
        ("Phase 5 2021", 9, 241),
        ("Phase 5 2022", 79, 244),
        ("Phase 5 2023", 46, 228),
        ("Phase 5 2024", 241, 241),
        ("Phase 5 2025", 245, 245),
        ("Phase 5 total", 646, 1412),
    ]
    for label, k, n in phase5_counts:
        summaries.append(summarise_counts_only(label, k, n))

    # 3. Write output YAML
    out = {
        "metadata": {
            "script": "scripts/validation/paper2/jrfm_revision/bootstrap_detection_ci.py",
            "purpose": "95% CIs on Paper 2 detection rates (JRFM R3.5a)",
            "n_bootstrap": N_BOOTSTRAP,
            "rng_seed": RNG_SEED,
        },
        "summaries": summaries,
    }
    with OUTPUT_YAML.open("w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, sort_keys=False, default_flow_style=False)

    # 4. Print a concise table for pasting into the manuscript
    print(f"{'Phase':<36} {'n':>5} {'k':>4} {'rate':>7} {'bootstrap 95% CI':>22} {'Wilson 95% CI':>22}")
    print("-" * 100)
    for s in summaries:
        boot = (
            f"[{s['bootstrap_ci_pct'][0]:5.1f}, {s['bootstrap_ci_pct'][1]:5.1f}]%"
            if s["bootstrap_ci_pct"] is not None
            else "n/a"
        )
        wil = f"[{s['wilson_ci_pct'][0]:5.1f}, {s['wilson_ci_pct'][1]:5.1f}]%"
        print(f"{s['label']:<36} {s['n']:>5} {s['k']:>4} {s['rate_pct']:>6.1f}% {boot:>22} {wil:>22}")
    print(f"\nWrote {OUTPUT_YAML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
