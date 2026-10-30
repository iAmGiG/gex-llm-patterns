#!/usr/bin/env python3
"""Bridge to the published result: gpt-6-luna against the published o4-mini labels on the identical inputs.

Both models labelled the 30-day windows of the recovered Phase 4A inputs (arms ``r1_o4mini`` and ``bridge_jan``).
Panel (a) is the confusion matrix of the two verdicts (persistent regime detected or not) with the overall
agreement and Cohen's kappa; (b) and (c) give the agreement and kappa by year, with an extra column for all years.
Kappa is not drawn for a year in which either model gives the same verdict on every window, because it is then 0
or undefined whatever the agreement.  Dashed references: the gpt-6-luna test-retest (the arm against its own repeat
requests, when 05_report.py has them) and the agreement gate from ``bridge_agreement.yaml``.

Input  results/bridge_agreement.csv (05_report.py), rows comparison == 'bridge' with ref_arm r1_o4mini and
  other_arm bridge_jan (scope 'year' and 'all'); optional rows comparison == 'test_retest' of bridge_jan against its
  repeats.  Columns: the four 2x2 counts n_ref_det_oth_det, n_ref_det_oth_not, n_ref_not_oth_det,
  n_ref_not_oth_not, agree_pct with its Wilson interval, kappa, and on the 'all' row the quarter-block bootstrap
  intervals agree_boot_lo_pct/hi_pct and kappa_boot_lo/hi.
  results/bridge_agreement.yaml (05_report.py): gate.threshold for the kappa reference line, when a gate was formed.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

import figdata
import theme

FIG_ID = "fig06_bridge_agreement"
RESULTS_FILES = ("bridge_agreement.csv", "bridge_agreement.yaml")
TABLE_KINDS: Sequence[str] = ()
REFERENCE_ARM = "r1_o4mini"  # the published labels
BRIDGE_ARM = "bridge_jan"  # gpt-6-luna on the same windows
ALL_GAP = 1.9  # the all-years column sits this far (in years) to the right of the last year
CELL_LABELS = ("Detected", "Not detected")
RETEST_STYLE = dict(color=theme.INK_SECONDARY, linewidth=1.0, linestyle=(0, (1, 1.6)))  # the model against its own repeats
GATE_STYLE = dict(color=theme.THRESHOLD, linewidth=0.8, linestyle=(0, (4, 2)))  # the agreement gate


def select(frame: pd.DataFrame, inputs: figdata.Inputs) -> Tuple[pd.DataFrame, pd.Series, Optional[pd.Series]]:
    """(yearly rows, all-years row, test-retest all-years row or None) of the bridge comparison."""
    bridge = frame[(frame["comparison"] == "bridge") & (frame["ref_arm"] == REFERENCE_ARM) & (frame["other_arm"] == BRIDGE_ARM)]
    if bridge.empty:
        inputs.fail(f"bridge_agreement.csv has no 'bridge' rows for {REFERENCE_ARM} vs {BRIDGE_ARM}")
    overall = bridge[bridge["scope"] == "all"]
    yearly = bridge[bridge["scope"] == "year"].sort_values("year")
    if len(overall) != 1 or yearly.empty:
        inputs.fail(f"expected one all-years row and yearly rows for {REFERENCE_ARM} vs {BRIDGE_ARM}, found {len(overall)} and {len(yearly)}")
    retest = frame[(frame["comparison"] == "test_retest") & (frame["ref_arm"] == BRIDGE_ARM) & (frame["scope"] == "all")]
    return yearly, overall.iloc[0], (retest.sort_values("n_pairs").iloc[-1] if not retest.empty else None)


def interval(row: pd.Series, boot: Tuple[str, str], wilson: Optional[Tuple[str, str]] = None) -> Tuple[float, float, str]:
    """(lo, hi, which) of the all-years interval: bootstrap if the row has one, else Wilson, else (NaN, NaN, 'none')."""
    for columns, which in ((boot, "bootstrap"), (wilson, "wilson")):
        if columns is not None and np.isfinite(row[columns[0]]) and np.isfinite(row[columns[1]]):
            return float(row[columns[0]]), float(row[columns[1]]), which
    return math.nan, math.nan, "none"


def bracket(lo: float, hi: float, digits: int) -> str:
    """' (lo–hi)', or nothing when the interval is missing."""
    return f" ({lo:.{digits}f}–{hi:.{digits}f})" if np.isfinite(lo) and np.isfinite(hi) else ""


def draw_matrix(ax, overall: pd.Series) -> None:
    cells = np.array([[overall["n_ref_det_oth_det"], overall["n_ref_det_oth_not"]],
                      [overall["n_ref_not_oth_det"], overall["n_ref_not_oth_not"]]], dtype=float)
    totals = cells.sum(axis=1, keepdims=True)
    share = np.divide(cells, totals, out=np.full_like(cells, np.nan), where=totals > 0)
    cmap = theme.sequential_cmap()
    ax.pcolormesh([0, 1, 2], [0, 1, 2], np.ma.masked_invalid(share), cmap=cmap, vmin=0.0, vmax=1.0, edgecolors=theme.SURFACE,
                  linewidth=2.0)
    for i in range(2):
        for j in range(2):
            if np.isfinite(share[i, j]):
                ax.text(j + 0.5, i + 0.5, f"{int(cells[i, j]):,}\n{share[i, j] * 100.0:.1f}%", ha="center", va="center",
                        fontsize=8, color=theme.ink_on_fill(cmap(share[i, j])))
    ax.set_xlim(0, 2)
    ax.set_ylim(2, 0)
    ax.set_xticks([0.5, 1.5])
    ax.set_xticklabels(CELL_LABELS)
    ax.set_yticks([0.5, 1.5])
    ax.set_yticklabels(CELL_LABELS, rotation=90, va="center")
    ax.set_xlabel("gpt-6-luna")
    ax.set_ylabel("o4-mini (published)")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)
    ax.set_aspect("equal")


def draw_year_dots(ax, x: np.ndarray, y: np.ndarray, lo: np.ndarray, hi: np.ndarray, color: str) -> None:
    """Dots with interval whiskers; a missing interval (NaN) leaves the dot without a whisker."""
    lower = np.where(np.isfinite(lo), np.clip(y - lo, 0, None), 0.0)
    upper = np.where(np.isfinite(hi), np.clip(hi - y, 0, None), 0.0)
    ax.errorbar(x, y, yerr=np.vstack([lower, upper]), fmt="none", ecolor=color, elinewidth=0.9, capsize=1.3, capthick=0.9,
                zorder=3)
    ax.plot(x, y, linestyle="none", marker="o", markersize=3.8, markerfacecolor=color, markeredgecolor=theme.SURFACE,
            markeredgewidth=0.5, zorder=5)


def undefined_runs(years: Sequence[int], defined: Sequence[bool]) -> List[Tuple[float, float]]:
    """(first, last) year of each run of consecutive years in which kappa is undefined."""
    runs: List[Tuple[float, float]] = []
    for year, ok in zip(years, defined):
        if ok:
            continue
        if runs and runs[-1][1] == year - 1:
            runs[-1] = (runs[-1][0], float(year))
        else:
            runs.append((float(year), float(year)))
    return runs


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = theme.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    bridge = figdata.load_bridge_agreement(inputs)
    gate = (inputs.yaml("bridge_agreement.yaml").get("gate") or {}).get("threshold")
    yearly, overall, retest = select(bridge, inputs)

    years = yearly["year"].astype(int).to_numpy()
    all_x = float(years.max()) + ALL_GAP
    color = theme.series_color("jan2026_phase4a")
    fig = theme.new_figure(3.9)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.85])
    ax_matrix = fig.add_subplot(gs[:, 0])
    ax_agree = fig.add_subplot(gs[0, 1])
    ax_kappa = fig.add_subplot(gs[1, 1], sharex=ax_agree)

    # (a) confusion matrix, all years
    draw_matrix(ax_matrix, overall)
    theme.panel_title(ax_matrix, "a", f"Same windows (n = {int(overall['n_pairs']):,})")
    a_lo, a_hi, a_how = interval(overall, ("agree_boot_lo_pct", "agree_boot_hi_pct"), ("agree_ci_lo_pct", "agree_ci_hi_pct"))
    k_lo, k_hi, k_how = interval(overall, ("kappa_boot_lo", "kappa_boot_hi"))
    ax_matrix.text(0.5, -0.26, f"Agreement {overall['agree_pct']:.1f}%{bracket(a_lo, a_hi, 1)}\n"
                               f"κ = {overall['kappa']:.2f}{bracket(k_lo, k_hi, 2)}", transform=ax_matrix.transAxes,
                   ha="center", va="top", fontsize=8, color=theme.INK)

    # (b) agreement by year
    theme.panel_title(ax_agree, "b", "Agreement of the labels by year (%)")
    y = yearly["agree_pct"].to_numpy(float)
    draw_year_dots(ax_agree, years.astype(float), y, yearly["agree_ci_lo_pct"].to_numpy(float), yearly["agree_ci_hi_pct"].to_numpy(float), color)
    draw_year_dots(ax_agree, np.array([all_x]), np.array([float(overall["agree_pct"])]), np.array([a_lo]), np.array([a_hi]), color)
    retest_agree = retest_kappa = None
    if retest is not None:
        retest_agree, retest_kappa = float(retest["agree_pct"]), float(retest["kappa"])
        ax_agree.axhline(retest_agree, zorder=1.5, **RETEST_STYLE)
    lowest = min(float(yearly["agree_ci_lo_pct"].min()), a_lo if np.isfinite(a_lo) else 100.0,
                 retest_agree if retest_agree is not None else 100.0)
    ax_agree.set_ylim(max(0.0, np.floor((lowest - 1.0) / 5.0) * 5.0), 100.5)
    ax_agree.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 5, 10]))
    ax_agree.set_ylabel("Agreement (%)")
    ax_agree.tick_params(labelbottom=False)
    theme.style_grid(ax_agree)

    # (c) kappa by year, only where both models vary
    theme.panel_title(ax_kappa, "c", "Cohen’s κ by year")
    defined = figdata.kappa_defined(yearly).to_numpy()
    kappa = yearly["kappa"].to_numpy(float)
    ok = defined & np.isfinite(kappa)
    ax_kappa.plot(years[ok], kappa[ok], linestyle="none", marker="o", markersize=3.8, markerfacecolor=color,
                  markeredgecolor=theme.SURFACE, markeredgewidth=0.5, zorder=5)
    draw_year_dots(ax_kappa, np.array([all_x]), np.array([float(overall["kappa"])]), np.array([k_lo]), np.array([k_hi]), color)
    for first, last in undefined_runs(years, defined):
        ax_kappa.text((first + last) / 2.0, 0.28, "κ undefined:\none model labels\nevery window alike", ha="center", va="center",
                      fontsize=8, color=theme.MUTED)
    if gate is not None:
        ax_kappa.axhline(float(gate), zorder=1.5, **GATE_STYLE)
    if retest_kappa is not None and np.isfinite(retest_kappa):
        ax_kappa.axhline(retest_kappa, zorder=1.5, **RETEST_STYLE)
    ax_kappa.set_ylim(min(0.0, float(np.nanmin(kappa[ok])) - 0.05) if ok.any() else 0.0, 1.05)
    ax_kappa.yaxis.set_major_locator(MaxNLocator(nbins=4, steps=[1, 2, 5, 10]))
    ax_kappa.set_ylabel("κ")
    theme.style_grid(ax_kappa)
    ax_kappa.set_xlim(years.min() - 0.6, all_x + 0.6)
    ticks = [float(v) for v in years] + [all_x]
    ax_kappa.set_xticks(ticks)
    ax_kappa.set_xticklabels([str(v) for v in years] + ["All"])
    for ax in (ax_agree, ax_kappa):
        ax.axvline(float(years.max()) + ALL_GAP / 2.0, color=theme.GRID, linewidth=0.6, zorder=1)

    handles = [Line2D([], [], linestyle="none", marker="o", markersize=3.8, color=color)]
    labels = ["o4-mini vs gpt-6-luna, 95% interval"]
    if retest is not None:
        handles.append(Line2D([], [], **RETEST_STYLE))
        labels.append(f"gpt-6-luna vs its repeat requests (n = {int(retest['n_pairs'])})")
    if gate is not None:
        handles.append(Line2D([], [], **GATE_STYLE))
        labels.append(f"Agreement gate κ = {float(gate):g}")
    fig.legend(handles, labels, loc="outside upper center", ncol=len(handles), handlelength=1.6, columnspacing=1.6)

    bootstrap = "quarter-block bootstrap" if "bootstrap" in (a_how, k_how) else "Wilson"
    theme.footnote(fig, f"SPY windows of the recovered Phase 4A inputs, window ends {years.min()}–{years.max()}. Whiskers on "
                        f"years: Wilson 95% intervals, which treat overlapping windows as independent; All: {bootstrap} "
                        "95% interval. In (a) the percentage is the share of the row.")
    extra = {"reference_arm": REFERENCE_ARM, "bridge_arm": BRIDGE_ARM, "n_pairs": int(overall["n_pairs"]), "years": [int(v) for v in years],
             "kappa_undefined_years": [int(v) for v, d in zip(years, defined) if not d], "gate_threshold": gate,
             "test_retest_arm": None if retest is None else str(retest["other_arm"]), "interval_all": [a_how, k_how]}
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
