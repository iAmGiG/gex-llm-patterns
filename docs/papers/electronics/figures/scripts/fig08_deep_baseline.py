#!/usr/bin/env python3
"""Pre-0DTE baseline: SPY detection rates by year, 2008-2019, deterministic rule and gpt-6-luna.

Before weekly and daily expirations grew, how often does a 30-day window of SPY dealer GEX meet the Paper 2
criteria (at least 21 of 30 days of one sign, mean |GEX| of at least $5B, at most 5 sign flips)?  Panel (a) draws
the rule as a line and gpt-6-luna as open markers for the rebuilt series with and without 0DTE and, when the
optional archive arm was run, for the pre-rebuild archive.  Panel (b) is the consistency check of the ablation
arm: the gap between the two rebuilt series must vanish while same-day expiries carry (almost) none of the GEX,
which panel (c) shows.  The 2008-2009 financial crisis and the 2018 volatility episode are marked.

Input  results/detection_by_year.csv and results/ex0dte_decomposition.csv (05_report.py)
  * detection_by_year.csv, read by figdata.load_detection_by_year(), symbol SPY: classifier rows of new_full and
    new_ex0dte (required) and old_bs (diagnostic, optional); LLM rows of the arm full_spy (required) and of ex0dte_spy and
    bridge_old (optional: a series without them is drawn as a rule line and the footnote says so); columns n, n_detect,
    n_parsed, the rates with their Wilson intervals and n_indep_30d;
  * ex0dte_decomposition.csv, symbol SPY, scope = year: diff_pp and llm_diff_pp (detection rate of new_full minus
    new_ex0dte on the windows both series have) and abs_0dte_share_pct (share of |GEX| carried by same-day expiries).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import figdata
import figllm
import theme

FIG_ID = "fig08_deep_baseline"
RESULTS_FILES = ("detection_by_year.csv", "ex0dte_decomposition.csv")
TABLE_KINDS: Sequence[str] = ()
SYMBOL = "SPY"
FIRST_YEAR, LAST_YEAR = 2008, 2019
# (series key, LLM arm, rule required, LLM arm required, label of the rule line); drawn in this order
SERIES = (
    (figllm.FULL, "full_spy", True, True, "Rule, rebuilt 0DTE incl."),
    (figllm.EX0DTE, "ex0dte_spy", True, False, "Rule, rebuilt ex-0DTE"),
    (figllm.OLD, "bridge_old", False, False, "Rule, pre-rebuild archive"),
)
LLM_OFFSET = {figllm.FULL: -0.14, figllm.EX0DTE: 0.0, figllm.OLD: 0.14}  # sideways shift of the open markers (years)
EVENTS = (("Financial crisis", 2008, 2009), ("2018\nvolatility", 2018, 2018))
DECOMPOSITION_REQUIRED = ("symbol", "scope", "year", "diff_pp", "llm_diff_pp", "n_matched", "llm_n_matched", "abs_0dte_share_pct")
RANGE = f"{FIRST_YEAR}{theme.ENDASH}{LAST_YEAR}"


def pooled(n: pd.Series, detected: pd.Series) -> Dict[str, float]:
    """Windows and detections summed over the years, and the pooled rate (percent)."""
    total, hits = float(n.sum()), float(detected.sum())
    return {"n": int(total), "n_detect": int(hits), "rate_pct": 100.0 * hits / total if total else float("nan")}


def by_year(years: Sequence[int], rule: pd.DataFrame, rule_column: str, llm: pd.DataFrame, llm_column: str) -> Dict[str, Optional[dict]]:
    """Rule and LLM rate (percent) of each year, for the manifest; the LLM entry is None when the arm has no rows."""
    return {"rule": dict(zip(years, figllm.percent(rule, years, rule_column), strict=True)),
            "llm": dict(zip(years, figllm.percent(llm, years, llm_column), strict=True)) if len(llm) else None}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figllm.parse_args(FIG_ID, __doc__, argv)
    inputs = figllm.open_inputs(FIG_ID, args)
    detection = figdata.load_detection_by_year(inputs)
    detection = detection[detection["symbol"] == SYMBOL]
    decomposition = inputs.csv("ex0dte_decomposition.csv", DECOMPOSITION_REQUIRED)

    # ---- which series and arms exist in the baseline years
    series: List[dict] = []
    for key, arm, rule_required, arm_required, label in SERIES:
        rule = figllm.rule_by_year(inputs, detection, key, SYMBOL)
        rule = rule[(rule.index >= FIRST_YEAR) & (rule.index <= LAST_YEAR)]
        llm = figllm.arm_by_year(inputs, detection, arm)
        llm = llm[(llm.index >= FIRST_YEAR) & (llm.index <= LAST_YEAR)]
        if rule.empty:
            if rule_required:
                inputs.fail(f"detection_by_year.csv has no {SYMBOL} classifier rows for {key} in {RANGE}")
            continue
        if llm.empty and arm_required:
            inputs.fail(f"detection_by_year.csv has no rows of the LLM arm {arm} in {RANGE} (04_llm_runner.py, then 05_report.py)")
        series.append({"key": key, "arm": arm, "label": label, "rule": rule, "llm": llm})
    years = sorted({int(y) for s in series for y in s["rule"].index})
    gap = decomposition[(decomposition["symbol"] == SYMBOL) & (decomposition["scope"] == "year")].copy()
    gap["year"] = pd.to_numeric(gap["year"], errors="coerce")
    gap = gap.dropna(subset=["year"]).assign(year=lambda f: f["year"].astype(int)).set_index("year").reindex(years)
    if gap[["diff_pp", "abs_0dte_share_pct"]].isna().all().all():
        inputs.fail(f"ex0dte_decomposition.csv has no {SYMBOL} yearly rows for {RANGE}")

    # ---- figure: event strip, (a) rates, (b) gap between the rebuilt series, (c) share of |GEX| in same-day expiries
    fig = theme.new_figure(5.35)
    grid = fig.add_gridspec(4, 1, height_ratios=[0.26, 1.0, 0.5, 0.42])
    ax = fig.add_subplot(grid[1])
    strip = fig.add_subplot(grid[0], sharex=ax)
    ax_gap = fig.add_subplot(grid[2], sharex=ax)
    ax_share = fig.add_subplot(grid[3], sharex=ax)
    xlim = (years[0] - 0.6, years[-1] + 0.6)
    spans = [(max(a, years[0]) - 0.5, min(b, years[-1]) + 0.5, name) for name, a, b in EVENTS if b >= years[0] and a <= years[-1]]
    figllm.span_strip(strip, spans, xlim)
    for panel in (ax, ax_gap, ax_share):
        for left, right, _ in spans:
            panel.axvspan(left, right, color=theme.PANEL_BG, zorder=0, linewidth=0)

    top = 0.0
    handles: List[Line2D] = []
    for s in series:
        key = s["key"]
        color, marker = theme.series_color(key), theme.series_marker(key)
        rule_rate = figllm.percent(s["rule"], years, "clf_rate")
        llm_rate = figllm.percent(s["llm"], years, "llm_rate") if len(s["llm"]) else None
        err = None
        if llm_rate is not None:
            if s is series[0]:  # whiskers on the primary series only: three sets of whiskers would bury the rates
                lo, hi, _ = figdata.ci_columns(s["llm"], "llm")
                err = figdata.whiskers(s["llm"].reindex(years), "llm_rate", lo, hi)
                top = max(top, float(np.nanmax(figllm.percent(s["llm"], years, hi))))
            top = max(top, float(np.nanmax(llm_rate)))
        top = max(top, float(np.nanmax(rule_rate)))
        figllm.draw_rate(ax, years, rule_rate, llm_rate, color, marker, LLM_OFFSET[key], err)
        handles.append(figllm.line_handle(color, marker, s["label"]))
        if llm_rate is not None:
            handles.append(figllm.hollow_handle(color, marker, theme.arm_label(s["arm"])))
    ymax = float(min(100.0, max(30.0, np.ceil((top + 2.0) / 10.0) * 10.0)))
    ax.set_ylim(-ymax * 0.04, ymax)
    ax.set_yticks(np.arange(0, ymax + 0.1, 10 if ymax <= 60 else 25))
    ax.set_ylabel("Detection rate (%)")
    theme.panel_title(ax, "a", "Windows detected by year")
    theme.style_grid(ax)

    theme.style_grid(ax_gap)
    ax_gap.axhline(0.0, color=theme.BASELINE, linewidth=0.8, zorder=1)
    gap_rule, gap_llm = gap["diff_pp"].to_numpy(float), gap["llm_diff_pp"].to_numpy(float)
    ax_gap.plot(years, gap_rule, color=theme.INK, marker="o", markersize=3.0, linewidth=1.0, markeredgecolor=theme.SURFACE,
                markeredgewidth=0.5, zorder=3)
    ax_gap.plot(np.asarray(years) + 0.08, gap_llm, **figllm.hollow_style(theme.INK, "o", 3.6))
    reach = float(np.nanmax(np.abs(np.concatenate([gap_rule, gap_llm, [2.0]]))))
    ax_gap.set_ylim(-1.2 * reach, 1.2 * reach)
    ax_gap.set_ylabel("Gap (pp)")
    theme.panel_title(ax_gap, "b", "Rebuilt series with minus without 0DTE")
    ax_gap.legend(handles=[Line2D([0], [0], color=theme.INK, marker="o", markersize=3.0, linewidth=1.0, label="Rule"),
                           Line2D([0], [0], label="gpt-6-luna", **{**figllm.hollow_style(theme.INK, "o", 3.6), "clip_on": True})],
                  loc="upper left", ncol=2, borderaxespad=0.1, handlelength=1.2)

    theme.style_grid(ax_share)
    share = gap["abs_0dte_share_pct"].to_numpy(float)
    ax_share.bar(years, share, width=0.62, color=theme.BASELINE, zorder=2)
    ax_share.set_ylim(0, max(10.0, float(np.nanmax(share)) * 1.25) if np.isfinite(share).any() else 10.0)
    ax_share.set_ylabel("Share (%)")
    theme.panel_title(ax_share, "c", "Share of |GEX| carried by same-day expiries")
    ax_share.set_xticks(years)
    ax_share.set_xlim(*xlim)
    for panel in (strip, ax, ax_gap):
        panel.tick_params(labelbottom=False)
    fig.legend(handles=handles, loc="outside upper center", ncol=len(series), columnspacing=1.4)

    # ---- footnote and manifest
    base = series[0]
    pooled_rule = pooled(base["rule"]["n"], base["rule"]["clf_n_detect"])
    pooled_llm = pooled(base["llm"]["n_parsed"], base["llm"]["llm_n_detect"]) if len(base["llm"]) else None
    independent = int(round(float(pd.concat([s["rule"]["n_indep_30d"] for s in series]).median())))
    max_gap_rule = float(np.nanmax(np.abs(gap_rule))) if np.isfinite(gap_rule).any() else float("nan")
    max_gap_llm = float(np.nanmax(np.abs(gap_llm))) if np.isfinite(gap_llm).any() else float("nan")
    without_llm = [s["arm"] for s in series if s["llm"].empty]
    note = (f"SPY, 30-day windows ending in the year. Lines: deterministic rule; open markers: gpt-6-luna on the same windows "
            f"(shifted sideways for legibility). Whiskers on the first series: Wilson 95% interval, which treats the overlapping windows "
            f"of a year as independent and is too narrow: a year holds about {independent} non-overlapping 30-day windows. "
            f"(b) Detection rate with 0DTE minus without, on the windows both series have. "
            f"Shaded: 2008{theme.ENDASH}2009 financial crisis and 2018 volatility episode.")
    if without_llm:
        note += f" No gpt-6-luna rows for {', '.join(without_llm)}."
    theme.footnote(fig, note)
    extra = {
        "symbol": SYMBOL, "years": years, "series_drawn": [s["key"] for s in series],
        "llm_arms_drawn": [s["arm"] for s in series if len(s["llm"])], "llm_arms_missing": without_llm,
        "pooled_" + base["key"]: {"rule": pooled_rule, "llm": pooled_llm},
        "max_abs_gap_pp": {"rule": max_gap_rule, "llm": max_gap_llm},
        "events": {name.replace("\n", " "): [a, b] for name, a, b in EVENTS},
        "interval": "Wilson 95% (figdata.ci_columns) on the first series' gpt-6-luna rates; overlapping windows treated as independent",
        "median_independent_windows_per_year": independent,
        "rate_pct_by_year": {s["key"]: by_year(years, s["rule"], "clf_rate", s["llm"], "llm_rate") for s in series},
        "gap_pp_by_year": {"rule": dict(zip(years, gap_rule, strict=True)), "llm": dict(zip(years, gap_llm, strict=True))},
        "same_day_share_pct_by_year": dict(zip(years, share, strict=True)),
    }
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
