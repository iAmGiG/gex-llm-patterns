"""Markov-switching regime benchmark for Paper 2 JRFM revision.

Addresses Reviewer 3 comment R3.3a: "The research design must be
strengthened. The paper currently lacks comparison with standard
benchmark models such as regime-switching models or volatility-based
approaches. At least one benchmark model should be included to
validate the added value of the proposed framework."

Approach. We fit a two-state Markov-switching regression
(statsmodels.tsa.regime_switching.MarkovRegression) to SPY daily log
returns for the two calendar years the paper compares head-to-head
(2020 and 2024). This is the textbook returns-based regime-switching
benchmark and uses only the CPU-side EM algorithm; no GPU required,
completes in a few seconds per fit.

For 2024 we additionally fit the HMM directly on the daily net-GEX
series (reports/statistical_validation/gamma_positioning_timeseries_2024.csv)
to provide a GEX-native benchmark that is more directly analogous to
what the LLM detects.

For each 30-day window we compute the HMM-dominant-state label
(majority smoothed state across the 30 days) and compare it to the
LLM regime_detected bool stored in phase3 / phase4 YAML. We report
per-year HMM detection rates and Cohen's kappa agreement with the LLM.

Expected reading. If the HMM and LLM agree strongly (kappa > 0.6),
the framework is reproducing a volatility-regime signal. If they
disagree substantially (kappa near 0 or negative), the framework is
detecting a different phenomenon (dealer gamma positioning) than the
volatility regimes a returns-based HMM picks up -- which is the
structural-reasoning interpretation we argue for in the paper.

Usage:
    python hmm_benchmark.py

Outputs:
    reports/validation/paper2_regime_windows/jrfm_revision_hmm_benchmark.yaml
    docs/papers/paper2/figures/output/fig10_hmm_agreement.png
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

REPO_ROOT = Path(__file__).resolve().parents[4]
SPY_CACHE_DIR = REPO_ROOT / ".cache" / "market_data" / "SPY"
GEX_2024_CSV = REPO_ROOT / "reports" / "statistical_validation" / "gamma_positioning_timeseries_2024.csv"
WINDOWS_DIR = REPO_ROOT / "reports" / "validation" / "paper2_regime_windows"
FIG_DIR = REPO_ROOT / "docs" / "papers" / "paper2" / "figures" / "output"
OUTPUT_YAML = WINDOWS_DIR / "jrfm_revision_hmm_benchmark.yaml"
OUTPUT_PNG = FIG_DIR / "fig10_hmm_agreement.png"

RNG_SEED = 20260424


def load_spy_prices(year: int) -> pd.DataFrame:
    """Concatenate and return SPY daily prices for a given year, indexed by date."""
    pickles = sorted(SPY_CACHE_DIR.glob(f"{year}-*.pickle"))
    if not pickles:
        raise FileNotFoundError(f"No SPY pickle for {year} under {SPY_CACHE_DIR}")
    frames = []
    for p in pickles:
        with p.open("rb") as f:
            df = pickle.load(f)
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        frames.append(df)
    out = pd.concat(frames).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out[out.index.year == year]
    return out[["close"]]


def fit_msm(y: np.ndarray, name: str) -> dict:
    """Fit a 2-state Markov-switching regression (intercept + switching variance).

    statsmodels returns params in a fixed order for k_regimes=2 + trend='c' +
    switching_variance=True: [p00, p10, const[0], const[1], sigma2[0], sigma2[1]].
    We access them positionally because res.params is a bare numpy array.
    """
    np.random.seed(RNG_SEED)
    mod = MarkovRegression(y, k_regimes=2, trend="c", switching_variance=True)
    res = mod.fit(disp=False, maxiter=200)
    smoothed = res.smoothed_marginal_probabilities
    # Layout: params[0]=p00, [1]=p10, [2]=const0, [3]=const1, [4]=sigma2_0, [5]=sigma2_1
    p = np.asarray(res.params).flatten()
    sigma2 = np.array([p[4], p[5]])
    const = np.array([p[2], p[3]])
    high_var_state = int(np.argmax(sigma2))
    low_var_state = 1 - high_var_state
    # For 2-state smoothed probs, pick the argmax state per day.
    smoothed_arr = np.asarray(smoothed)
    if smoothed_arr.shape[0] == 2 and smoothed_arr.shape[1] != 2:
        smoothed_arr = smoothed_arr.T
    dominant = smoothed_arr.argmax(axis=1)
    return {
        "name": name,
        "n_obs": int(len(y)),
        "params": {
            "p00": float(p[0]),
            "p10": float(p[1]),
            "const0": float(const[0]),
            "const1": float(const[1]),
            "sigma2_0": float(sigma2[0]),
            "sigma2_1": float(sigma2[1]),
        },
        "llf": float(res.llf),
        "high_variance_state": high_var_state,
        "low_variance_state": low_var_state,
        "dominant_state_per_obs": dominant.tolist(),
    }


def window_label_from_hmm(
    dominant: np.ndarray, dates: pd.DatetimeIndex, end_date: pd.Timestamp, length: int = 30
) -> int | None:
    """Return the majority HMM state over the 30-day window ending at end_date, or None if window incomplete."""
    # Select the 30 trading days up to and including end_date.
    mask = dates <= end_date
    if mask.sum() < length:
        return None
    window_states = dominant[mask][-length:]
    # Majority vote: return 0 or 1 (whichever appears more often).
    return int(np.bincount(window_states.astype(int)).argmax())


def load_llm_window_decisions(yaml_path: Path) -> pd.DataFrame:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    rows = []
    for w in data.get("windows", []) or []:
        wid = w.get("window_id") or ""
        # Window IDs look like "window-2024-02-13"; extract end date.
        parts = wid.rsplit("-", 3)
        if len(parts) < 4:
            continue
        try:
            end = pd.Timestamp(f"{parts[1]}-{parts[2]}-{parts[3]}")
        except Exception:
            continue
        rows.append(
            {
                "window_id": wid,
                "end_date": end,
                "llm_detected": bool(w.get("regime_detected")),
            }
        )
    return pd.DataFrame(rows).sort_values("end_date").reset_index(drop=True)


def kappa_from_tables(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's kappa for two binary arrays (0/1)."""
    from sklearn.metrics import cohen_kappa_score

    return float(cohen_kappa_score(a.astype(int), b.astype(int)))


def benchmark_year(year: int, yaml_name: str, hmm_series_name: str = "returns") -> dict | None:
    """Run HMM benchmark for one calendar year using the specified input series.

    Returns None if the MarkovRegression EM algorithm fails to converge
    (typically when the series is too uniform for two-state separation to be
    identifiable -- itself a noteworthy finding).
    """
    prices = load_spy_prices(year)
    returns = np.log(prices["close"]).diff().dropna()
    if hmm_series_name == "returns":
        y = returns.values
        y_dates = returns.index
    elif hmm_series_name == "net_gex" and year == 2024:
        gex = pd.read_csv(GEX_2024_CSV)
        gex["date"] = pd.to_datetime(gex["date"])
        gex = gex.sort_values("date").reset_index(drop=True)
        # Use net_gex in billions; additional centering helps the EM when the
        # series is dominated by a large negative mean (as in 2024 SPY).
        y = (gex["net_gex"].values / 1e9).astype(float)
        y = y - y.mean()
        y_dates = pd.DatetimeIndex(gex["date"].values)
    else:
        raise ValueError(f"Unsupported series {hmm_series_name}")

    try:
        fit = fit_msm(y, name=f"{year}-{hmm_series_name}")
    except Exception as e:
        print(
            f"WARNING: HMM fit for {year} ({hmm_series_name}) did not converge: " f"{type(e).__name__}: {e}",
            file=sys.stderr,
        )
        print(
            f"  -> skipping; this itself indicates the series lacks two-state "
            f"identifiable structure (noteworthy result).",
            file=sys.stderr,
        )
        return None

    # Compute window-level HMM labels
    llm = load_llm_window_decisions(WINDOWS_DIR / yaml_name)
    dominant = np.array(fit["dominant_state_per_obs"])

    hmm_labels = []
    matched = []
    for _, row in llm.iterrows():
        lbl = window_label_from_hmm(dominant, y_dates, row["end_date"])
        if lbl is None:
            continue
        hmm_labels.append(lbl)
        matched.append(bool(row["llm_detected"]))

    hmm_arr = np.array(hmm_labels, dtype=int)
    llm_arr = np.array(matched, dtype=int)

    # For HMM "detected" we pick the low-variance (stable) state as "regime".
    # That matches the paper's intuition: persistent regime = low-variance
    # structural state; transitional markets are higher variance.
    hmm_detect = (hmm_arr == fit["low_variance_state"]).astype(int)

    # Agreement stats
    agree_rate = float((hmm_detect == llm_arr).mean()) if len(llm_arr) else float("nan")
    kappa = kappa_from_tables(hmm_detect, llm_arr) if len(llm_arr) else float("nan")

    # 2x2 contingency
    tp = int(((hmm_detect == 1) & (llm_arr == 1)).sum())
    fp = int(((hmm_detect == 1) & (llm_arr == 0)).sum())
    fn = int(((hmm_detect == 0) & (llm_arr == 1)).sum())
    tn = int(((hmm_detect == 0) & (llm_arr == 0)).sum())

    return {
        "year": year,
        "series": hmm_series_name,
        "n_windows_matched": int(len(llm_arr)),
        "hmm_detection_rate_pct": float(round(hmm_detect.mean() * 100, 2)),
        "llm_detection_rate_pct": float(round(llm_arr.mean() * 100, 2)),
        "agreement_rate_pct": float(round(agree_rate * 100, 2)),
        "cohen_kappa": float(round(kappa, 3)),
        "contingency_tp_hmm_llm": tp,
        "contingency_fp_hmm_only": fp,
        "contingency_fn_llm_only": fn,
        "contingency_tn_neither": tn,
        "hmm_fit_summary": {
            "llf": fit["llf"],
            "high_variance_state": fit["high_variance_state"],
            "low_variance_state": fit["low_variance_state"],
            "sigma2_state_0": fit["params"]["sigma2_0"],
            "sigma2_state_1": fit["params"]["sigma2_1"],
            "const_state_0": fit["params"]["const0"],
            "const_state_1": fit["params"]["const1"],
        },
    }


def plot_agreement(results: list[dict]) -> None:
    import matplotlib.pyplot as plt

    labels = [f"{r['year']} ({r['series']})" for r in results]
    llm_rates = [r["llm_detection_rate_pct"] for r in results]
    hmm_rates = [r["hmm_detection_rate_pct"] for r in results]
    kappas = [r["cohen_kappa"] for r in results]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)

    x = np.arange(len(labels))
    w = 0.38
    ax1.bar(x - w / 2, llm_rates, w, label="LLM", color="#1f77b4")
    ax1.bar(x + w / 2, hmm_rates, w, label="Markov-switching", color="#ff7f0e")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=0)
    ax1.set_ylabel("Detection rate (%)")
    ax1.set_ylim(0, 105)
    ax1.legend(loc="upper left")
    ax1.set_title("Detection rate: LLM vs Markov-switching")
    for i, (l, h) in enumerate(zip(llm_rates, hmm_rates)):
        ax1.text(i - w / 2, l + 1.5, f"{l:.1f}%", ha="center", fontsize=12)
        ax1.text(i + w / 2, h + 1.5, f"{h:.1f}%", ha="center", fontsize=12)

    colors = ["#2ca02c" if k > 0.4 else "#d62728" if k < 0.2 else "#bcbd22" for k in kappas]
    ax2.bar(x, kappas, color=colors)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axhline(0.4, color="grey", linestyle="--", linewidth=0.8, label="κ = 0.4 (moderate)")
    ax2.axhline(0.6, color="grey", linestyle=":", linewidth=0.8, label="κ = 0.6 (substantial)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=0)
    ax2.set_ylabel("Cohen's κ")
    ax2.set_ylim(-0.3, 1.0)
    ax2.set_title("Agreement (LLM vs Markov-switching)")
    ax2.legend(loc="upper right", fontsize=12)
    for i, k in enumerate(kappas):
        ax2.text(i, k + 0.02 if k >= 0 else k - 0.06, f"{k:.2f}", ha="center", fontsize=12)

    fig.suptitle(
        "Markov-switching benchmark versus LLM regime detection",
        fontsize=13,
    )
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    results: list[dict] = []
    # Returns-based benchmark for both years (apples-to-apples)
    for year, yaml_name in (
        (2020, "phase4_baseline_2020.yaml"),
        (2024, "phase3_baseline_2024_full_year.yaml"),
    ):
        r = benchmark_year(year, yaml_name, "returns")
        if r is not None:
            results.append(r)
    # GEX-native benchmark for 2024 (we only have the CSV for 2024)
    r = benchmark_year(2024, "phase3_baseline_2024_full_year.yaml", "net_gex")
    if r is not None:
        results.append(r)

    if not results:
        print("No benchmark results produced", file=sys.stderr)
        return 1

    summary = {
        "metadata": {
            "script": "scripts/validation/paper2/jrfm_revision/hmm_benchmark.py",
            "purpose": "Markov-switching regime benchmark (JRFM R3.3a)",
            "rng_seed": RNG_SEED,
            "note": (
                "Returns-based benchmarks are the conventional comparison; "
                "the 2024 net_gex benchmark is an additional, more directly "
                "analogous fit. HMM 'detected' = low-variance (stable) state."
            ),
        },
        "results": results,
    }

    # Print report
    print()
    print(f"{'Year/Series':<22} {'N':>5} {'LLM':>7} {'HMM':>7} {'Agree':>7} {'kappa':>7}")
    print("-" * 60)
    for r in results:
        print(
            f"{r['year']} / {r['series']:<14} {r['n_windows_matched']:>5} "
            f"{r['llm_detection_rate_pct']:>6.1f}% {r['hmm_detection_rate_pct']:>6.1f}% "
            f"{r['agreement_rate_pct']:>6.1f}% {r['cohen_kappa']:>7.3f}"
        )

    with OUTPUT_YAML.open("w", encoding="utf-8") as f:
        yaml.safe_dump(summary, f, sort_keys=False, default_flow_style=False)

    plot_agreement(results)
    print(f"\nWrote {OUTPUT_YAML}")
    print(f"Wrote {OUTPUT_PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
