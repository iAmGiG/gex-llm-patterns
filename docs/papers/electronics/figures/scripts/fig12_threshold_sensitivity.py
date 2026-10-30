#!/usr/bin/env python3
"""Threshold sensitivity of the 2024-2025 detection rate: published inputs against the rebuilt series.

The Paper 2 criteria have three thresholds: at least 21 of 30 days of one sign (persistence 70%), a mean |GEX| of
at least $5B and at most 5 sign flips.  Every SPY window ending in 2024 or 2025 is re-classified from its stored
30-day sequence under 45 threshold sets (persistence 60-80% in steps of 5, magnitude $3B/$5B/$7B, at most 3/5/7
flips), once for the exact published inputs (``jan2026_phase4a``, the put-less January table) and once for the
rebuilt series (``new_full``).  If the published 100% against the rebuilt ~10-14% were a quirk of one threshold
choice, some panel would show the two lines meeting.  The panel with a heavy frame holds the published
thresholds; a ring marks the published persistence there.

Input  windows parquet copies (02_build_windows.py), symbol SPY, series jan2026_phase4a and new_full
  gex_sequence (the 30 values shown to the model, USD), clf_should_detect, clf_positive_days, clf_negative_days,
  clf_avg_magnitude, clf_sign_flips for window_end in 2024-2025.  The metrics are recomputed from gex_sequence by
  the repository's classifier and must equal the stored clf_* columns, and the published thresholds must
  reproduce the stored verdict, else the figure stops.  Persistence thresholds are applied as the classifier does,
  int(30 * threshold) days: 60/65/70/75/80% need 18/19/21/22/24 days.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

import figdata
import figllm
import theme
from theme import common

FIG_ID = "fig12_threshold_sensitivity"
RESULTS_FILES: Sequence[str] = ()
TABLE_KINDS: Sequence[str] = ("windows",)
SYMBOL = "SPY"
SERIES = (figllm.JAN, figllm.FULL)
YEARS = (2024, 2025)
PERSISTENCE_PCT = (60, 65, 70, 75, 80)
MAGNITUDE_BN = (3.0, 5.0, 7.0)
MAX_FLIPS = (3, 5, 7)
PUBLISHED = {"persistence_pct": 70, "magnitude_bn": 5.0, "max_flips": 5}  # the criteria of Paper 2
WINDOW_COLUMNS = ("series_key", "symbol", "window_end", "gex_sequence", "clf_should_detect", "clf_positive_days",
                  "clf_negative_days", "clf_avg_magnitude", "clf_sign_flips")
LABELS = {figllm.JAN: "Published inputs (call leg only)", figllm.FULL: "Rebuilt, 0DTE incl."}


def min_days(persistence_pct: int) -> int:
    """Days of one sign a threshold needs, computed exactly as RegimeClassifier does (``int(30 * threshold)``)."""
    return int(common.WINDOW_DAYS * (persistence_pct / 100.0))


def recompute_metrics(frame: pd.DataFrame, inputs: figdata.Inputs) -> pd.DataFrame:
    """Metrics of every window from its stored sequence (by the repository's classifier), checked against the stored columns."""
    rows = []
    for stored in frame["gex_sequence"]:
        result = common.classify(list(figdata.sequence_values(stored)))
        rows.append((result["positive_days"], result["negative_days"], result["avg_magnitude"], result["sign_flips"]))
    metrics = pd.DataFrame(rows, columns=["pos", "neg", "magnitude", "flips"], index=frame.index)
    wrong = ((metrics["pos"] != frame["clf_positive_days"]) | (metrics["neg"] != frame["clf_negative_days"])
             | (metrics["flips"] != frame["clf_sign_flips"])
             | ~np.isclose(metrics["magnitude"], frame["clf_avg_magnitude"], rtol=1e-9, atol=1.0))
    if wrong.any():
        first = frame.loc[wrong, ["series_key", "window_end"]].head(3).astype(str).agg(" ".join, axis=1).tolist()
        inputs.fail(f"{int(wrong.sum())} window(s) whose stored clf_* columns differ from the metrics of their stored gex_sequence "
                    f"(first: {first}); rebuild the windows with 02_build_windows.py")
    return metrics


def detections(metrics: pd.DataFrame, persistence_pct: int, magnitude_bn: float, max_flips: int) -> np.ndarray:
    """Boolean verdict per window: the decision rule of RegimeClassifier._classify_regime_type for one threshold set."""
    days = min_days(persistence_pct)
    return (((metrics["pos"] >= days) | (metrics["neg"] >= days)) & (metrics["magnitude"] >= magnitude_bn * 1e9)
            & (metrics["flips"] <= max_flips)).to_numpy()


def threshold_grid(inputs: figdata.Inputs, windows: pd.DataFrame) -> tuple[pd.DataFrame, Dict[str, Dict[str, int]]]:
    """Detection rate of every series under the 45 threshold sets (pooled and per year), and the windows behind it."""
    rows: List[dict] = []
    counts: Dict[str, Dict[str, int]] = {}
    for key in SERIES:
        part = windows[windows["series_key"] == key].reset_index(drop=True)
        if part.empty:
            inputs.fail(f"no {SYMBOL} {key} windows ending in {YEARS[0]}{theme.ENDASH}{YEARS[-1]} in the windows parquet files")
        metrics = recompute_metrics(part, inputs)
        year = part["window_end"].dt.year.to_numpy()
        counts[key] = {**{str(y): int((year == y).sum()) for y in YEARS}, "all": int(len(part))}
        reproduced = detections(metrics, **PUBLISHED)
        stored = part["clf_should_detect"].astype(bool).to_numpy()
        if (reproduced != stored).any():
            inputs.fail(f"the published thresholds do not reproduce the stored verdict of {int((reproduced != stored).sum())} {key} window(s); "
                        "the windows were labelled with other thresholds (clf_version) or the classifier changed")
        for p in PERSISTENCE_PCT:
            for m in MAGNITUDE_BN:
                for f in MAX_FLIPS:
                    hit = detections(metrics, p, m, f)
                    rows.append({"series_key": key, "persistence_pct": p, "min_days": min_days(p), "magnitude_bn": m, "max_flips": f,
                                 "rate_pct": 100.0 * hit.mean(), **{f"rate_pct_{y}": 100.0 * hit[year == y].mean() for y in YEARS}})
    return pd.DataFrame(rows), counts


def draw_grid(axes: np.ndarray, table: pd.DataFrame) -> None:
    """One panel per (flip limit, magnitude threshold): detection rate against the persistence threshold, one line per series."""
    x = np.asarray(PERSISTENCE_PCT)
    for r, f in enumerate(MAX_FLIPS):
        for c, m in enumerate(MAGNITUDE_BN):
            ax = axes[r, c]
            cell = table[(table["magnitude_bn"] == m) & (table["max_flips"] == f)]
            for key in SERIES:
                line = cell[cell["series_key"] == key].sort_values("persistence_pct")
                ax.plot(x, line["rate_pct"], color=theme.series_color(key), marker=theme.series_marker(key), markersize=3.4,
                        linewidth=1.2, markeredgecolor=theme.SURFACE, markeredgewidth=0.4, clip_on=False, zorder=3)
            theme.style_grid(ax)
            ax.set_ylim(-5, 105)
            ax.set_yticks([0, 50, 100])
            ax.set_xlim(58, 82)
            ax.set_xticks(x)
            if r == 0:
                ax.set_title(f"Magnitude ≥ {theme.usd_b(m)}", fontsize=9, fontweight="bold", loc="left")
            if c == len(MAGNITUDE_BN) - 1:
                ax.text(1.04, 0.5, f"≤ {f} flips", transform=ax.transAxes, rotation=270, ha="left", va="center", fontsize=9,
                        fontweight="bold", color=theme.INK)
            if r == len(MAX_FLIPS) - 1:
                ax.set_xticklabels([f"{p}\n{min_days(p)}" for p in PERSISTENCE_PCT])
            if (m, f) == (PUBLISHED["magnitude_bn"], PUBLISHED["max_flips"]):
                mark_published(ax, cell)


def mark_published(ax, cell: pd.DataFrame) -> None:
    """Heavy frame around the published thresholds, a ring and the value on each line at the published persistence."""
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.3)
        spine.set_edgecolor(theme.INK)
    p = PUBLISHED["persistence_pct"]
    for key in SERIES:
        value = float(cell[(cell["series_key"] == key) & (cell["persistence_pct"] == p)]["rate_pct"].iloc[0])
        ax.plot([p], [value], marker="o", markersize=7.0, markerfacecolor="none", markeredgecolor=theme.INK, markeredgewidth=0.9,
                zorder=5, clip_on=False)
        ax.annotate(f"{value:.1f}", (p, value), xytext=(6, -3 if value > 50 else 6), textcoords="offset points", fontsize=8,
                    color=theme.INK, ha="left", va="top" if value > 50 else "bottom")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figllm.parse_args(FIG_ID, __doc__, argv)
    inputs = figllm.open_inputs(FIG_ID, args)
    windows = inputs.table("windows", WINDOW_COLUMNS, series_keys=SERIES, symbols=[SYMBOL])
    windows = windows[windows["window_end"].dt.year.isin(YEARS)].reset_index(drop=True)
    table, counts = threshold_grid(inputs, windows)

    fig = theme.new_figure(5.15)
    axes = fig.subplots(len(MAX_FLIPS), len(MAGNITUDE_BN), sharex=True, sharey=True)
    draw_grid(axes, table)
    axes[1, 0].set_ylabel(f"Windows detected, {YEARS[0]}{theme.ENDASH}{YEARS[-1]} (%)")
    axes[-1, 1].set_xlabel("Persistence threshold: % of the 30 days (second line: days of one sign required)")
    fig.legend(handles=[figllm.line_handle(theme.series_color(k), theme.series_marker(k), LABELS[k]) for k in SERIES],
               loc="outside upper center", ncol=2, columnspacing=1.6)
    wide = table.pivot_table(index=["persistence_pct", "magnitude_bn", "max_flips"], columns="series_key", values="rate_pct")
    gap = wide[figllm.JAN] - wide[figllm.FULL]
    published = f"{PUBLISHED['persistence_pct']}%, {theme.usd_b(PUBLISHED['magnitude_bn'])}, {PUBLISHED['max_flips']} flips"
    theme.footnote(fig, f"SPY windows ending in {YEARS[0]} or {YEARS[-1]} ({counts[figllm.JAN]['all']} on the published inputs, "
                        f"{counts[figllm.FULL]['all']} on the rebuilt series), each re-classified from its stored 30-day sequence. "
                        f"Heavy frame and rings: the published thresholds ({published}). Across the {len(wide)} threshold sets the "
                        f"published-input rate exceeds the rebuilt rate by {gap.min():.1f} to {gap.max():.1f} percentage points.")
    extra = {
        "symbol": SYMBOL, "years": list(YEARS), "windows": counts, "thresholds_published": PUBLISHED,
        "grid": {"persistence_pct": list(PERSISTENCE_PCT), "min_days": [min_days(p) for p in PERSISTENCE_PCT],
                 "magnitude_bn": list(MAGNITUDE_BN), "max_flips": list(MAX_FLIPS), "n_configurations": len(wide)},
        "consistency": {"stored_clf_columns_equal_recomputed": True, "published_thresholds_reproduce_stored_verdicts": counts},
        "gap_pp_published_minus_rebuilt": {"min": float(gap.min()), "max": float(gap.max())},
        "rates": table.round(4).to_dict("records"),
    }
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
