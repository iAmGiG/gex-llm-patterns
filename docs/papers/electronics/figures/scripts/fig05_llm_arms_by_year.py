#!/usr/bin/env python3
"""gpt-6-luna detection rate by year on each SPY series, with the deterministic classifier as reference.

One panel per SPY arm, from the exact published inputs (``bridge_jan``) to the rebuilt series (``full_spy``, then
the ex-0DTE ablation ``ex0dte_spy``) and, when it was run, the pre-rebuild archive (``bridge_old``).  A dot is the
share of 30-day windows ending in the year that the model labelled as a persistent regime, with its Wilson 95%
interval; the dark dash is the share the deterministic criteria give on exactly the windows the model answered.
A dot on its dash means the model reproduced the rule.  The grey band is 2026, the post-publication period.

Input  results/detection_by_year.csv (05_report.py), yearly rows (scope == 'year'); the LLM rows (label_source ==
  'llm') of symbol SPY, model gpt-6-luna, for the arms
  * bridge_jan, full_spy, ex0dte_spy (required) and bridge_old (drawn when present), with
  * n_parsed answers, llm_rate and Wilson interval llm_ci_lo/llm_ci_hi, clf_rate_matched (classifier rate on the
    answered windows) and n_indep_30d (non-overlapping 30-day windows behind the year).
  Rates are percent in the file and fractions after figdata.load_detection_by_year().
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import figdata
import theme

FIG_ID = "fig05_llm_arms_by_year"
RESULTS_FILES = ("detection_by_year.csv",)
TABLE_KINDS: Sequence[str] = ()
SYMBOL = "SPY"
PANEL_HEIGHT_IN = 1.3
LABEL_YEARS = (2024, 2025)  # the years after the change of convention carry value labels
DASH_HALF_WIDTH = 0.32  # of a year
SERIES_OF_ARMS = {"jan2026_phase4a", "old_bs", "new_full", "new_ex0dte"}  # SPY series whose arms this figure draws


def spy_arms() -> List[str]:
    """Registered SPY arms that call a model on a daily series (registry order); the intraday check has its own figure."""
    return [a.key for a in theme.common.ARMS.values() if a.llm and a.symbol == SYMBOL and a.series_key in SERIES_OF_ARMS]


def required_arms() -> List[str]:
    return [key for key in spy_arms() if theme.common.ARMS[key].priority <= 1]


def arm_frame(llm: pd.DataFrame, arm: str, inputs: figdata.Inputs, required: bool) -> Optional[pd.DataFrame]:
    """Yearly rows of one arm for the production model, indexed by year; None for an optional arm that was not run."""
    rows = llm[(llm["arm"] == arm) & (llm["symbol"] == SYMBOL)]
    if rows.empty:
        if required:
            inputs.fail(f"detection_by_year.csv has no LLM rows for arm {arm} (symbol {SYMBOL}); run the arm or drop it from the registry")
        return None
    own = rows[rows["model"] == theme.common.MODEL]
    if own.empty:
        inputs.fail(f"arm {arm} has no rows for model {theme.common.MODEL} (found {sorted(rows['model'].dropna().unique())})")
    if own["clf_rate_matched"].isna().all():
        inputs.fail(f"arm {arm} has no classifier reference (n_compared is 0 in every year): its windows are not in the windows table")
    if own["year"].duplicated().any():
        inputs.fail(f"arm {arm} has several rows for the same year (model {theme.common.MODEL}, symbol {SYMBOL})")
    return own.sort_values("year").set_index("year")


def value_label(ax, x: float, row: pd.Series) -> None:
    """Rate of the year as a number above the whisker, below it when the whisker reaches the top of the axes."""
    high = row["llm_ci_hi"] * 100.0
    if high > 80.0:
        ax.text(x, row["llm_ci_lo"] * 100.0 - 3.0, f"{row['llm_rate'] * 100.0:.0f}", ha="center", va="top", fontsize=8,
                color=theme.INK)
    else:
        ax.text(x, high + 3.0, f"{row['llm_rate'] * 100.0:.1f}", ha="center", va="bottom", fontsize=8, color=theme.INK)


def draw_arm(ax, arm: str, rows: pd.DataFrame) -> None:
    color = theme.arm_color(arm)
    x = rows.index.to_numpy(float)
    y = rows["llm_rate"].to_numpy(float) * 100.0
    lo, hi = figdata.ci_columns(rows, "llm")[:2]
    continuous = rows.reindex(range(int(x.min()), int(x.max()) + 1))  # a missing year breaks the connecting line
    ax.plot(continuous.index, continuous["llm_rate"] * 100.0, color=color, linewidth=0.6, alpha=0.55, zorder=2)
    ax.errorbar(x, y, yerr=figdata.whiskers(rows, "llm_rate", lo, hi), fmt="none", ecolor=color, elinewidth=0.9, capsize=1.3,
                capthick=0.9, zorder=3)
    reference = rows["clf_rate_matched"].to_numpy(float) * 100.0
    ok = np.isfinite(reference)
    ax.hlines(reference[ok], x[ok] - DASH_HALF_WIDTH, x[ok] + DASH_HALF_WIDTH, color=theme.INK, linewidth=1.0, zorder=4)
    ax.plot(x, y, linestyle="none", marker="o", markersize=3.8, markerfacecolor=color, markeredgecolor=theme.SURFACE,
            markeredgewidth=0.5, zorder=5)
    for year in LABEL_YEARS:
        if year in rows.index:
            value_label(ax, float(year), rows.loc[year])


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = theme.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    detection = figdata.load_detection_by_year(inputs)
    llm = figdata.llm_rates(detection)
    required = set(required_arms())
    frames: Dict[str, pd.DataFrame] = {}
    for arm in spy_arms():
        frame = arm_frame(llm, arm, inputs, arm in required)
        if frame is not None:
            frames[arm] = frame
    years = list(range(min(int(f.index.min()) for f in frames.values()), max(int(f.index.max()) for f in frames.values()) + 1))
    partial = theme.PARTIAL_YEAR if theme.PARTIAL_YEAR in years else None

    height = 1.15 + PANEL_HEIGHT_IN * len(frames)
    fig = theme.new_figure(height)
    axes = fig.subplots(len(frames), 1, sharex=True)
    axes = np.atleast_1d(axes)
    for letter, ax, (arm, rows) in zip("abcdefgh", axes, frames.items()):
        draw_arm(ax, arm, rows)
        theme.panel_title(ax, letter, theme.arm_label(arm))
        theme.percent_axis(ax, ticks=(0, 50, 100))
        theme.style_grid(ax)
        if partial is not None:
            theme.shade_span(ax, partial - 0.5, partial + 0.5)
        ax.set_xlim(years[0] - 0.6, years[-1] + 0.6)
    shown = years[::-1][::2][::-1]  # every second year counted back from the last, so the partial year is labelled
    axes[-1].set_xticks(shown)
    axes[-1].set_xticklabels([theme.year_label(y, partial) for y in shown])
    fig.supylabel("Detection rate (%)", fontsize=8)
    handles = [Line2D([], [], linestyle="none", marker="o", markersize=3.8, color=theme.INK),
               Line2D([], [], color=theme.INK, linewidth=1.0)]
    fig.legend(handles, ["gpt-6-luna rate with Wilson 95% interval", "Classifier on the same windows"],
               loc="outside upper center", ncol=2, handlelength=1.6, columnspacing=2.0)

    answered = pd.concat(frames.values())
    unparsed = int((answered["n_windows"] - answered["n_parsed"]).sum())
    independent = int(round(float(answered["n_indep_30d"].median())))
    sentences = [f"{SYMBOL}, 30-day windows ending in the year. Whiskers are Wilson intervals that treat the overlapping "
                 f"windows of a year as independent, so they are too narrow: a year holds about {independent} "
                 "non-overlapping 30-day windows."]
    if partial is not None:
        sentences.append(f"Grey band: {partial}, the post-publication period (windows ending up to {theme.common.WINDOW_END_CAP.isoformat()}).")
    if unparsed:
        sentences.append(f"{unparsed:,} answers could not be parsed and are left out.")
    theme.footnote(fig, " ".join(sentences))

    extra = {"symbol": SYMBOL, "model": theme.common.MODEL, "arms": list(frames), "years": [years[0], years[-1]],
             "windows_by_arm": {arm: int(f["n_windows"].sum()) for arm, f in frames.items()},
             "unparsed_answers": unparsed, "median_independent_windows_per_year": independent}
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
