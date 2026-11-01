#!/usr/bin/env python3
"""Cross-asset replication: SPY, QQQ and IWM detection rates by year, with and without 0DTE, and the floor effect.

The Paper 2 criteria are fixed dollar thresholds (mean |GEX| of at least $5B).  QQQ and IWM carry far less dollar
gamma than SPY, so the magnitude test can be unreachable for them whatever the model does.  Row 1 draws, for each
symbol, the deterministic rule (lines) and gpt-6-luna (open markers) on the rebuilt series with and without 0DTE,
plus the share of windows that pass the persistence and sign-flip tests alone (dotted).  Row 2 draws the
quantity the magnitude test compares with $5B: the yearly median and the largest 30-day mean |GEX|.  Nothing is
rescaled: a symbol without a persistent window is shown as it is, and an LLM arm that has not been run says so
on the panel.

Input  results/detection_by_year.csv (05_report.py) and the windows parquet copies (02_build_windows.py)
  * detection_by_year.csv, read by figdata.load_detection_by_year(), symbols SPY, QQQ, IWM: classifier rows of new_full for all three symbols
    and of new_ex0dte for SPY (required; QQQ starts in 2011; the ex-0DTE series of QQQ and IWM, from 2020, are drawn
    when they exist); LLM rows of the arms full_<symbol> and ex0dte_<symbol> (optional: the priority-2 and
    priority-3 arms wait for the authors' go-ahead);
  * windows parquet, series new_full and new_ex0dte: clf_should_detect, clf_avg_magnitude, clf_positive_days,
    clf_negative_days, clf_sign_flips (the gex_sequence column is not read).  The persistence, magnitude and flip
    thresholds come from results/report.yaml (diagnostics.thresholds) and must reproduce every stored verdict, else the
    figure stops.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import figdata
import figllm
import theme
from theme import common

FIG_ID = "fig09_cross_asset"
RESULTS_FILES = ("detection_by_year.csv",)
TABLE_KINDS: Sequence[str] = ("windows",)
SERIES = (figllm.FULL, figllm.EX0DTE)
RULE_LABELS = {figllm.FULL: "Rule, rebuilt 0DTE incl.", figllm.EX0DTE: "Rule, rebuilt ex-0DTE"}
LLM_LABELS = {figllm.FULL: "gpt-6-luna, rebuilt", figllm.EX0DTE: "gpt-6-luna, ex-0DTE"}
LLM_OFFSET = {figllm.FULL: -0.12, figllm.EX0DTE: 0.12}  # sideways shift of the open markers (years)
WINDOW_COLUMNS = ("series_key", "symbol", "window_end", "clf_should_detect", "clf_avg_magnitude", "clf_positive_days",
                  "clf_negative_days", "clf_sign_flips")
MAGNITUDE_FREE = (0, (1, 1.6))  # dotted line: persistence and flips only
LARGEST = (0, (4, 2))  # dashed line: largest window mean
YEAR_TICK_STEP = 6


def arm_name(series_key: str, symbol: str) -> str:
    return f"{'full' if series_key == figllm.FULL else 'ex0dte'}_{symbol.lower()}"


def window_summary(windows: pd.DataFrame, years: Sequence[int], rule: Dict[str, float]) -> pd.DataFrame:
    """Per year: windows, detections, median and largest mean |GEX| (USD billions), windows passing persistence and flips only."""
    same_sign = np.maximum(windows["clf_positive_days"], windows["clf_negative_days"])
    frame = windows.assign(
        year=windows["window_end"].dt.year, magnitude_bn=windows["clf_avg_magnitude"] / 1e9,
        passes_without_magnitude=(same_sign >= rule["min_days"]) & (windows["clf_sign_flips"] <= rule["max_sign_flips"]))
    grouped = frame.groupby("year").agg(n=("magnitude_bn", "size"), n_detect=("clf_should_detect", "sum"),
                                         median_bn=("magnitude_bn", "median"), max_bn=("magnitude_bn", "max"),
                                         n_no_magnitude=("passes_without_magnitude", "sum"))
    grouped["share_no_magnitude"] = 100.0 * grouped["n_no_magnitude"] / grouped["n"]
    reproduced = frame["passes_without_magnitude"] & (frame["magnitude_bn"] >= rule["magnitude_bn"])
    return grouped.reindex(list(years)), int((reproduced != windows["clf_should_detect"].astype(bool)).sum())


def collect(inputs: figdata.Inputs, detection: pd.DataFrame, windows: pd.DataFrame,
            rule: Dict[str, float]) -> Tuple[Dict[str, Dict[str, dict]], List[int]]:
    """({symbol: {series: rule rows, LLM rows, windows, yearly summary}}, years); new_full and every SPY series are required."""
    panels: Dict[str, Dict[str, dict]] = {}
    for symbol in figllm.SYMBOLS:
        panels[symbol] = {}
        for key in SERIES:
            rows = figllm.rule_by_year(inputs, detection, key, symbol)
            win = windows[(windows["series_key"] == key) & (windows["symbol"] == symbol)]
            if rows.empty or win.empty:
                if key == figllm.FULL or symbol == "SPY":
                    inputs.fail(f"no {symbol} {key} windows or classifier rows (windows parquet, detection_by_year.csv); "
                                "02_build_windows.py and 05_report.py must cover SPY, QQQ and IWM")
                continue
            panels[symbol][key] = {"rule": rows, "llm": figllm.arm_by_year(inputs, detection, arm_name(key, symbol)), "windows": win,
                                   "arm": arm_name(key, symbol)}
    years = sorted({int(y) for p in panels.values() for s in p.values() for y in s["rule"].index})
    for symbol, p in panels.items():
        for key, s in p.items():
            s["summary"], wrong = window_summary(s["windows"], years, rule)
            if wrong:
                inputs.fail(f"the thresholds of report.yaml ({rule['min_days']} days, {theme.usd_b(rule['magnitude_bn'])}, "
                            f"{rule['max_sign_flips']} flips) do not reproduce the stored verdict of {wrong} {symbol} {key} window(s)")
    return panels, years


def draw_symbol(ax_rate, ax_size, symbol: str, series: Dict[str, dict], years: Sequence[int], threshold_bn: float, ymax_bn: float) -> dict:
    """One column: detection rates on top, the window magnitudes the threshold is compared with below."""
    for key, s in series.items():
        color, marker = theme.series_color(key), theme.series_marker(key)
        llm_rate = figllm.percent(s["llm"], years, "llm_rate") if len(s["llm"]) else None
        figllm.draw_rate(ax_rate, years, figllm.percent(s["rule"], years, "clf_rate"), llm_rate, color, marker, LLM_OFFSET[key],
                         marker_size=2.6)
        ax_size.plot(years, s["summary"]["median_bn"].to_numpy(float), color=color, marker=marker, markersize=2.6, linewidth=1.1,
                     markeredgecolor=theme.SURFACE, markeredgewidth=0.4, clip_on=False, zorder=3)
        ax_size.plot(years, s["summary"]["max_bn"].to_numpy(float), color=color, linewidth=0.9, linestyle=LARGEST, alpha=0.9, zorder=2)
    full = series[figllm.FULL]
    ax_rate.plot(years, full["summary"]["share_no_magnitude"].to_numpy(float), color=theme.INK_SECONDARY, linestyle=MAGNITUDE_FREE,
                 linewidth=1.1, zorder=2)
    n_all, k_all = int(full["summary"]["n"].sum()), int(full["summary"]["n_detect"].sum())
    largest = float(full["summary"]["max_bn"].max())
    notes: List[str] = []
    if k_all == 0:
        notes += [f"0 of {n_all:,} detected", f"largest mean |GEX| {theme.usd_b(largest, 2)}"]
    missing = [s["arm"] for s in series.values() if s["llm"].empty]
    if missing:
        notes.append("gpt-6-luna not run" if len(missing) == len(series) else f"not run: {', '.join(missing)}")
    if notes:
        ax_rate.text(0.03, 0.97, "\n".join(notes), transform=ax_rate.transAxes, ha="left", va="top", fontsize=8, color=theme.INK_SECONDARY)
    ax_rate.set_ylim(-5, 105)
    ax_rate.set_yticks([0, 50, 100])
    ax_size.set_ylim(0, ymax_bn)
    theme.threshold_line(ax_size, threshold_bn)
    for ax in (ax_rate, ax_size):
        theme.style_grid(ax)
    theme.year_axis(ax_size, years, step=YEAR_TICK_STEP)
    ax_rate.tick_params(labelbottom=False)
    return {"windows_new_full": n_all, "detected_new_full": k_all, "largest_mean_abs_gex_bn_new_full": largest,
            "median_mean_abs_gex_bn_new_full": float(full["windows"]["clf_avg_magnitude"].median() / 1e9),
            "share_persistence_and_flips_only_pct": 100.0 * float(full["summary"]["n_no_magnitude"].sum()) / n_all,
            "series_drawn": list(series), "llm_arms_missing": missing}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figllm.parse_args(FIG_ID, __doc__, argv)
    inputs = figllm.open_inputs(FIG_ID, args)
    detection = figdata.load_detection_by_year(inputs)
    windows = inputs.table("windows", WINDOW_COLUMNS, series_keys=SERIES, symbols=figllm.SYMBOLS)
    thresholds = figdata.classifier_thresholds(inputs)
    rule = {"min_days": int(common.WINDOW_DAYS * thresholds["persistence"]), "magnitude_bn": thresholds["magnitude_bn"],
            "max_sign_flips": thresholds["max_sign_flips"]}
    panels, years = collect(inputs, detection, windows, rule)

    fig = theme.new_figure(4.75)
    grid = fig.add_gridspec(2, len(figllm.SYMBOLS), height_ratios=[1.0, 0.82])
    top = [fig.add_subplot(grid[0, j]) for j in range(len(figllm.SYMBOLS))]
    bottom = [fig.add_subplot(grid[1, j], sharex=top[j]) for j in range(len(figllm.SYMBOLS))]
    largest_bn = max(float(s["summary"]["max_bn"].max()) for p in panels.values() for s in p.values())
    ymax_bn = float(np.ceil(max(largest_bn, rule["magnitude_bn"]) * 1.08 / 2.0) * 2.0)
    status = {symbol: draw_symbol(top[j], bottom[j], symbol, panels[symbol], years, rule["magnitude_bn"], ymax_bn)
              for j, symbol in enumerate(figllm.SYMBOLS)}
    for j, symbol in enumerate(figllm.SYMBOLS):
        theme.panel_title(top[j], "abc"[j], symbol)
        theme.panel_title(bottom[j], "def"[j], symbol)
        if j:
            top[j].tick_params(labelleft=False)
            bottom[j].tick_params(labelleft=False)
    top[0].set_ylabel("Windows detected (%)")
    bottom[0].set_ylabel("Window mean |GEX| (\\$B)")
    bottom[-1].text(1.03, rule["magnitude_bn"], theme.usd_b(rule["magnitude_bn"]), transform=bottom[-1].get_yaxis_transform(),
                    ha="left", va="center", fontsize=8, color=theme.INK_SECONDARY)
    bottom[0].legend(handles=[Line2D([0], [0], color=theme.INK_SECONDARY, linewidth=1.1, label="Median"),
                              Line2D([0], [0], color=theme.INK_SECONDARY, linewidth=0.9, linestyle=LARGEST, label="Largest")],
                     loc="upper left", ncol=1, borderaxespad=0.2, handlelength=1.6)

    handles = [figllm.line_handle(theme.series_color(k), theme.series_marker(k), RULE_LABELS[k]) for k in SERIES]
    handles += [figllm.hollow_handle(theme.series_color(k), theme.series_marker(k), LLM_LABELS[k]) for k in SERIES]
    handles.append(Line2D([0], [0], color=theme.INK_SECONDARY, linestyle=MAGNITUDE_FREE, linewidth=1.1,
                          label="Persistence and flips only (rebuilt 0DTE incl.)"))
    fig.legend(handles=handles, loc="outside upper center", ncol=3, columnspacing=1.2)
    theme.footnote(fig, f"30-day windows ending in the year (QQQ from 2011; ex-0DTE series of QQQ and IWM from 2020). Row 1: lines are the "
                        f"deterministic rule, open markers gpt-6-luna on the same windows; the dotted line is the share of windows that "
                        f"meet the persistence ({rule['min_days']} of {common.WINDOW_DAYS} days) and sign-flip ({rule['max_sign_flips']}) "
                        f"tests, whatever their magnitude; the notes count the rebuilt 0DTE-incl. series. Row 2: median and largest mean |GEX| of the windows ending in "
                        f"the year; the dashed horizontal line is the fixed {theme.usd_b(rule['magnitude_bn'])} magnitude threshold. "
                        f"{theme.PARTIAL_YEAR_NOTE}")
    extra = {
        "years": years, "symbols": status,
        "thresholds": {"persistence_days": rule["min_days"], "magnitude_bn": rule["magnitude_bn"], "max_sign_flips": rule["max_sign_flips"],
                       "source": "report.yaml diagnostics.thresholds; reproduce every stored verdict"},
        "llm_arms_present": sorted(s["arm"] for p in panels.values() for s in p.values() if len(s["llm"])),
        "rate_pct_by_year": {symbol: {key: {"rule": dict(zip(years, figllm.percent(s["rule"], years, "clf_rate"), strict=True)),
                                            "llm": dict(zip(years, figllm.percent(s["llm"], years, "llm_rate"), strict=True))
                                            if len(s["llm"]) else None}
                                      for key, s in p.items()} for symbol, p in panels.items()},
    }
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
