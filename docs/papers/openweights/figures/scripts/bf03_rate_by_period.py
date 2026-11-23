#!/usr/bin/env python3
"""Detection rate by period on the complete SPY series, with the bounds of Qwen3-8B, and who goes unanswered.

(a) Detection rate (%) of each model on arm ``full_spy`` in four periods.  The rule is a black tick and gpt-6-luna a
hollow grey diamond (both are results of the companion paper, Paper A, drawn for orientation).  gpt-oss-20b and Llama
3.1 8B answered every window but two (a dot).  Qwen3-8B left windows unanswered, so its rate is a range: the lower end
counts every unanswered window as not detected and the upper end as detected; the dot is the rate over the windows it
answered.  (b) Share of windows answered by Qwen3-8B on each arm, for the windows that the rule detects and for those that
it rejects: the unanswered windows are not a random subset.  gpt-oss-20b answered all windows of every arm except two of
``full_spy`` and Llama 3.1 8B all of them; neither is drawn.

Input  results/missing_answer_bounds.csv (period, n_windows, n_parsed, rate_parsed_pct, lower_pct, upper_pct, clf_rate_pct,
  parsed_pct_clf_detect, parsed_pct_clf_no_detect; period all rows); results/detection_by_year.csv (yearly n_detect and
  n_parsed of the rule, gpt-6-luna, gpt-oss-20b and Llama 3.1 8B on full_spy, summed over the years of each period).
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import figopen  # first: it puts the Electronics figure modules on sys.path
import figdata  # noqa: E402
import theme  # noqa: E402

FIG_ID = "bf03_rate_by_period"
RESULTS_FILES = ("missing_answer_bounds.csv", "detection_by_year.csv")
TABLE_KINDS: Sequence[str] = ()
HEIGHT_IN = 3.1
BOUND_COLUMNS = ["arm", "period", "n_windows", "n_parsed", "rate_parsed_pct", "n_unparsed", "parsed_pct_clf_detect",
                 "parsed_pct_clf_no_detect", "lower_pct", "upper_pct", "clf_rate_pct"]


def period_rate(frame, first: int, last: int, detected: str, total: str) -> float:
    """Rate (%) over the windows of the years ``first``..``last``: summed detections over summed windows."""
    rows = frame[(frame.index >= first) & (frame.index <= last)]
    return 100.0 * float(rows[detected].sum()) / float(rows[total].sum())


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figopen.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    bounds = inputs.csv("missing_answer_bounds.csv", BOUND_COLUMNS, key=["arm", "period"])
    detection = figopen.load_detection(inputs)
    rule = figopen.rule_years(detection, "new_full")
    years = {key: figopen.llm_years(detection, arm) for key, arm in
             (("luna", "full_spy"), ("oss", "oss_full_spy"), ("llama", "llama_full_spy"))}
    qwen = bounds[bounds["arm"] == "qwen_full_spy"].set_index("period")
    if qwen.empty:
        inputs.fail("missing_answer_bounds.csv has no rows for qwen_full_spy")

    fig = theme.new_figure(HEIGHT_IN)
    ax_rate, ax_share = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.3, 1.0]})
    values: Dict[str, Dict[str, float]] = {}
    x = np.arange(len(figopen.PERIODS), dtype=float)
    slots = {"rule": -0.27, "luna": -0.135, "oss": 0.0, "llama": 0.135, "qwen": 0.27}
    for i, (label, key, first, last) in enumerate(figopen.PERIODS):
        rates = {"rule": period_rate(rule, first, last, "n_detect", "n"),
                 "luna": period_rate(years["luna"], first, last, "n_detect", "n_parsed"),
                 "oss": period_rate(years["oss"], first, last, "n_detect", "n_parsed"),
                 "llama": period_rate(years["llama"], first, last, "n_detect", "n_parsed")}
        ax_rate.plot([x[i] + slots["rule"] - 0.05, x[i] + slots["rule"] + 0.05], [rates["rule"]] * 2, color=theme.INK, linewidth=2.0,
                     solid_capstyle="butt", zorder=4)
        ax_rate.plot([x[i] + slots["luna"]], [rates["luna"]], linestyle="none", marker="d", markersize=4.8, markerfacecolor=theme.SURFACE,
                     markeredgecolor=figopen.HOSTED_COLOR, markeredgewidth=0.9, zorder=4, clip_on=False)
        for model in ("oss", "llama"):
            spec = figopen.MODEL_BY_KEY[model]
            ax_rate.plot([x[i] + slots[model]], [rates[model]], linestyle="none", marker=spec.marker, markersize=4.2,
                         markerfacecolor=spec.color, markeredgecolor=theme.SURFACE, markeredgewidth=0.5, zorder=4, clip_on=False)
        q = qwen.loc[key]
        spec = figopen.MODEL_BY_KEY["qwen"]
        ax_rate.plot([x[i] + slots["qwen"]] * 2, [q["lower_pct"], q["upper_pct"]], color=spec.color, linewidth=1.4, solid_capstyle="butt",
                     zorder=3)
        ax_rate.plot([x[i] + slots["qwen"]], [q["rate_parsed_pct"]], linestyle="none", marker=spec.marker, markersize=4.2,
                     markerfacecolor=spec.color, markeredgecolor=theme.SURFACE, markeredgewidth=0.5, zorder=4)
        values[key] = {**{k: round(v, 3) for k, v in rates.items()}, "qwen_lower": round(float(q["lower_pct"]), 3),
                       "qwen_upper": round(float(q["upper_pct"]), 3), "qwen_answered": round(float(q["rate_parsed_pct"]), 3),
                       "rule_check_clf_rate_pct": round(float(q["clf_rate_pct"]), 3)}
    ax_rate.set_xticks(x)
    ax_rate.set_xticklabels([p[0].replace("–", "–\n") for p in figopen.PERIODS])
    ax_rate.set_xlim(-0.5, len(x) - 0.5)
    theme.percent_axis(ax_rate, "y", ticks=(0, 25, 50, 75, 100))
    ax_rate.set_ylabel("Windows detected (%)")
    ax_rate.grid(axis="y", color=theme.GRID, linewidth=0.5)
    theme.panel_title(ax_rate, "a", "Complete SPY series")

    # (b) answered share of Qwen3-8B by the verdict of the rule
    arms = [a for a in figopen.ARMS if f"qwen_{a}" in set(bounds["arm"])]
    pos = np.arange(len(arms), dtype=float)
    detect = [float(bounds[(bounds["arm"] == f"qwen_{a}") & (bounds["period"] == "all")]["parsed_pct_clf_detect"].iloc[0]) for a in arms]
    reject = [float(bounds[(bounds["arm"] == f"qwen_{a}") & (bounds["period"] == "all")]["parsed_pct_clf_no_detect"].iloc[0]) for a in arms]
    width = 0.38
    ax_share.barh(pos - width / 2, detect, height=width, color=theme.POSITIVE, zorder=3)
    ax_share.barh(pos + width / 2, reject, height=width, color=theme.NEGATIVE, zorder=3)
    ax_share.set_yticks(pos)
    ax_share.set_yticklabels([figopen.ARM_LABELS[a].replace(", ", ",\n").replace("Complete, no", "Complete, no") for a in arms], fontsize=8)
    ax_share.invert_yaxis()
    theme.percent_axis(ax_share, "x", ticks=(0, 25, 50, 75, 100))
    ax_share.set_xlabel("Windows answered by qwen3-8b (%)")
    ax_share.grid(axis="x", color=theme.GRID, linewidth=0.5)
    theme.panel_title(ax_share, "b", "Answered share")
    values["answered_pct_rule_detects"] = {a: round(v, 3) for a, v in zip(arms, detect, strict=True)}
    values["answered_pct_rule_rejects"] = {a: round(v, 3) for a, v in zip(arms, reject, strict=True)}

    qwen_spec = figopen.MODEL_BY_KEY["qwen"]
    handles = [Line2D([0], [0], color=theme.INK, linewidth=2.0, label="Rule (Paper A)"),
               Line2D([0], [0], linestyle="none", marker="d", markersize=4.8, markerfacecolor=theme.SURFACE,
                      markeredgecolor=figopen.HOSTED_COLOR, markeredgewidth=0.9, label=figopen.LUNA.label)]
    handles += [Line2D([0], [0], linestyle="none", marker=figopen.MODEL_BY_KEY[k].marker, markersize=4.4,
                       markerfacecolor=figopen.MODEL_BY_KEY[k].color, markeredgecolor=theme.SURFACE, markeredgewidth=0.5,
                       label=figopen.MODEL_BY_KEY[k].label) for k in ("oss", "llama")]
    handles += [Line2D([0], [0], color=qwen_spec.color, linewidth=1.4, marker=qwen_spec.marker, markersize=4.2, label="qwen3-8b: range and answered rate"),
                Patch(facecolor=theme.POSITIVE, label="Rule detects"), Patch(facecolor=theme.NEGATIVE, label="Rule rejects")]
    fig.legend(handles=handles, loc="outside lower center", ncol=4, frameon=False, fontsize=8)
    figopen.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, {"arm": "full_spy", "rates_by_period": values})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
