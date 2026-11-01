#!/usr/bin/env python3
"""Late-session intraday snapshot versus end-of-day GEX: the T+0 value, the window and the labels it changes.

The composite window ``intraday_t0`` keeps the end-of-day GEX of days T-29 to T-1 and replaces day T+0 by the last
independent late-session observation (``final_rush``, 19:55:59 UTC).  Panel (a) draws that value next to the
end-of-day value for every window end, panel (b) the 30-day mean |GEX| of the two windows against the $5B magnitude
threshold, and panel (c) the labels of the deterministic rule and of gpt-6-luna on the end-of-day and the composite
window.  With a few dozen days the figure reports counts, not p-values.  Irregular days (data audit) are drawn
hollow and are not counted.

Input  results/intraday.csv (05_report.py), one row per composite window end of the chosen symbol (SPY)
  window_end, irregular_day, gex_t0_final_rush_bn, gex_t0_eod_bn, mean_abs_gex_intraday_bn, mean_abs_gex_full_bn,
  clf_intraday, clf_full (rule labels of the composite and of the end-of-day window) and llm_intraday, llm_full
  (gpt-6-luna labels of the same two windows; blank when the arm intraday_spy or full_spy has not scored the window).
"""

from __future__ import annotations

import argparse
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import figllm
import theme
from theme import common

FIG_ID = "fig11_intraday_vs_eod"
RESULTS_FILES = ("intraday.csv",)
TABLE_KINDS: Sequence[str] = ()
REQUIRED = ("window_end", "symbol", "irregular_day", "gex_t0_final_rush_bn", "gex_t0_eod_bn", "mean_abs_gex_intraday_bn",
            "mean_abs_gex_full_bn", "clf_intraday", "clf_full", "llm_intraday", "llm_full")
EOD_COLOR = theme.series_color(figllm.FULL)
INTRADAY_COLOR = theme.series_color("intraday_t0")
REJECTED = "#E6E6E6"
DIFFERS = theme.INK
# colour index of the label cells: 1 detected end-of-day window, 2 detected composite window, 3 rejected, 4 differs
CELL_COLORS = (EOD_COLOR, INTRADAY_COLOR, REJECTED, DIFFERS)


def add_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbol", default="SPY", choices=figllm.SYMBOLS, help="symbol to draw (default: %(default)s)")


def label_codes(flags: pd.Series, detected_code: int, usable: pd.Series) -> np.ndarray:
    """Cell codes of a boolean label column: detected colour, rejected grey, blank where unknown or not counted."""
    out = np.where(flags.fillna(False).astype(bool), detected_code, 3).astype(float)
    return np.where(flags.notna() & usable, out, np.nan)


def differs_codes(a: pd.Series, b: pd.Series, usable: pd.Series) -> np.ndarray:
    both = a.notna() & b.notna() & usable
    return np.where(both & (a != b), 4.0, np.nan)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figllm.parse_args(FIG_ID, __doc__, argv, add_options)
    inputs = figllm.open_inputs(FIG_ID, args)
    frame = inputs.csv("intraday.csv", REQUIRED)
    frame = frame[frame["symbol"] == args.symbol].copy()
    if frame.empty:
        inputs.fail(f"intraday.csv has no rows for {args.symbol}")
    frame["window_end"] = pd.to_datetime(frame["window_end"])
    frame = frame.sort_values("window_end").reset_index(drop=True)
    for column in ("irregular_day", "clf_intraday", "clf_full", "llm_intraday", "llm_full"):
        frame[column] = figllm.as_flag(frame[column])
    irregular = frame["irregular_day"].fillna(False).astype(bool)
    regular = ~irregular
    values = frame[["gex_t0_final_rush_bn", "gex_t0_eod_bn", "mean_abs_gex_intraday_bn", "mean_abs_gex_full_bn"]]
    if values.isna().any().any():
        inputs.fail(f"intraday.csv has {int(values.isna().any(axis=1).sum())} row(s) without a T+0 value or window mean; "
                    "05_report.py needs both new_full and intraday_late series rows for every composite window")
    dates = list(frame["window_end"])
    n = len(dates)
    x = np.arange(n)
    snap, eod = frame["gex_t0_final_rush_bn"].to_numpy(float), frame["gex_t0_eod_bn"].to_numpy(float)

    # ---- counts on the regular days (what the paper table quotes)
    same_sign = (np.sign(snap) == np.sign(eod))
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = np.abs(snap - eod) / np.abs(eod)
    clf_pair = frame["clf_intraday"].notna() & frame["clf_full"].notna() & regular
    llm_pair = frame["llm_intraday"].notna() & frame["llm_full"].notna() & regular
    counts = {
        "windows": n, "irregular_days": int(irregular.sum()), "regular_days": int(regular.sum()),
        "same_sign": int(same_sign[regular.to_numpy()].sum()),
        "median_relative_difference_pct": float(100.0 * np.nanmedian(relative[regular.to_numpy()])) if regular.any() else None,
        "rule_pairs": int(clf_pair.sum()), "rule_equal": int((frame["clf_intraday"][clf_pair] == frame["clf_full"][clf_pair]).sum()),
        "llm_pairs": int(llm_pair.sum()), "llm_equal": int((frame["llm_intraday"][llm_pair] == frame["llm_full"][llm_pair]).sum()),
    }

    # ---- figure
    items: List[tuple] = [("header", "Deterministic rule"),
                          ("row", "End of day", label_codes(frame["clf_full"], 1, regular), 1.0),
                          ("row", "Composite", label_codes(frame["clf_intraday"], 2, regular), 1.0),
                          ("row", "Differs", differs_codes(frame["clf_intraday"], frame["clf_full"], regular), 0.5)]
    llm_full_known, llm_composite_known = frame["llm_full"].notna().any(), frame["llm_intraday"].notna().any()
    llm_note = ""
    if llm_full_known or llm_composite_known:
        items += [("header", "gpt-6-luna"),
                  ("row", "End of day", label_codes(frame["llm_full"], 1, regular), 1.0),
                  ("row", "Composite", label_codes(frame["llm_intraday"], 2, regular), 1.0),
                  ("row", "Differs", differs_codes(frame["llm_intraday"], frame["llm_full"], regular), 0.5)]
        if not llm_composite_known:
            llm_note = " gpt-6-luna has not scored the composite windows (arm intraday_spy)."
        elif not llm_full_known:
            llm_note = " gpt-6-luna has not scored the end-of-day windows (arm full_spy)."
    else:
        llm_note = " No gpt-6-luna labels in intraday.csv (arms full_spy and intraday_spy)."
    n_rows = sum(1 for item in items if item[0] == "row")
    n_headers = len(items) - n_rows
    fig = theme.new_figure(5.4)
    grid = fig.add_gridspec(3, 1, height_ratios=[1.25, 1.0, 0.15 * n_rows + 0.2 * n_headers + 0.25])
    ax_t0 = fig.add_subplot(grid[0])
    ax_mean = fig.add_subplot(grid[1], sharex=ax_t0)
    ax_lab = fig.add_subplot(grid[2], sharex=ax_t0)
    for ax in (ax_t0, ax_mean, ax_lab):
        ax.set_xlim(-0.8, n - 0.2)
    for ax in (ax_t0, ax_mean):
        for i in np.flatnonzero(irregular.to_numpy()):
            ax.axvspan(i - 0.5, i + 0.5, color=theme.PANEL_BG, zorder=0, linewidth=0)
        theme.style_grid(ax)
        ax.tick_params(labelbottom=False)

    # (a) T+0 value: end of day versus final_rush
    ax_t0.axhline(0.0, color=theme.BASELINE, linewidth=0.8, zorder=1)
    for i in range(n):
        ax_t0.plot([i, i], [eod[i], snap[i]], color=theme.MUTED if regular[i] else theme.BASELINE, linewidth=0.8, zorder=2)
    for mask, hollow in ((regular.to_numpy(), False), (irregular.to_numpy(), True)):
        for values_, marker, color in ((eod, "^", EOD_COLOR), (snap, "v", INTRADAY_COLOR)):
            face = theme.SURFACE if hollow else color
            ax_t0.plot(x[mask], values_[mask], linestyle="none", marker=marker, markersize=3.6, markerfacecolor=face,
                       markeredgecolor=color, markeredgewidth=0.9 if hollow else 0.4, zorder=4)
    ax_t0.set_ylabel("Net GEX at T+0 (\\$B)")
    theme.panel_title(ax_t0, "a", "GEX of day T+0: end of day and late-session snapshot")

    # (b) window mean |GEX|
    mean_eod, mean_snap = frame["mean_abs_gex_full_bn"].to_numpy(float), frame["mean_abs_gex_intraday_bn"].to_numpy(float)
    ax_mean.plot(x, mean_eod, color=EOD_COLOR, linewidth=1.1, zorder=3)
    ax_mean.plot(x, mean_snap, color=INTRADAY_COLOR, linewidth=1.1, linestyle=(0, (4, 1.6)), zorder=3)
    threshold = common.classifier().magnitude_threshold / 1e9
    theme.threshold_line(ax_mean, threshold)
    ax_mean.text(1.012, threshold, theme.usd_b(threshold), transform=ax_mean.get_yaxis_transform(), ha="left", va="center", fontsize=8,
                 color=theme.INK_SECONDARY)
    low, high = float(min(mean_eod.min(), mean_snap.min(), threshold)), float(max(mean_eod.max(), mean_snap.max(), threshold))
    pad = 0.15 * (high - low if high > low else 1.0)
    ax_mean.set_ylim(max(0.0, low - pad), high + pad)
    ax_mean.set_ylabel("Mean |GEX| (\\$B)")
    theme.panel_title(ax_mean, "b", "30-day mean |GEX| of the window")

    # (c) labels
    figllm.label_grid(ax_lab, items, CELL_COLORS, n, row_gap=0.12)
    figllm.week_ticks(ax_lab, dates)
    ax_lab.tick_params(axis="x", length=2.5)
    ax_lab.set_xlabel(f"Window end date, {dates[0].year}")
    ax_lab.set_xlim(-0.8, n - 0.2)
    theme.panel_title(ax_lab, "c", "Label of the end-of-day and of the composite window")

    handles = [
        Line2D([0], [0], linestyle="none", marker="^", markersize=4.4, markerfacecolor=EOD_COLOR, markeredgecolor=EOD_COLOR,
               label="End of day (new_full)"),
        Line2D([0], [0], linestyle="none", marker="v", markersize=4.4, markerfacecolor=INTRADAY_COLOR, markeredgecolor=INTRADAY_COLOR,
               label="Late-session snapshot (final_rush)"),
        figllm.patch_handle(EOD_COLOR, "Detected, end-of-day window"),
        figllm.patch_handle(INTRADAY_COLOR, "Detected, composite window"),
        figllm.patch_handle(REJECTED, "Rejected"),
        figllm.patch_handle(DIFFERS, "Composite label differs"),
    ]
    if irregular.any():
        handles.insert(2, Line2D([0], [0], linestyle="none", marker="o", markersize=4.4, markerfacecolor=theme.SURFACE,
                                 markeredgecolor=theme.MUTED, markeredgewidth=0.9, label="Irregular day (not counted)"))
    fig.legend(handles=handles, loc="outside upper center", ncol=3, columnspacing=1.2)
    irregular_text = f" ({counts['irregular_days']} irregular, not counted)" if irregular.any() else ""
    parts = [f"{args.symbol}, {n} composite window ends{irregular_text}. On the {counts['regular_days']} regular days the "
             f"two T+0 values have the same sign on {counts['same_sign']}; the median relative difference is "
             f"{counts['median_relative_difference_pct']:.1f}%." if regular.any() else f"{args.symbol}, {n} composite window ends."]
    parts.append(f"The rule gives the same label for the composite and the end-of-day window on {counts['rule_equal']} of {counts['rule_pairs']} days"
                 + (f", gpt-6-luna on {counts['llm_equal']} of {counts['llm_pairs']}." if counts["llm_pairs"] else "."))
    theme.footnote(fig, " ".join(parts) + llm_note + f" Dashed line in (b): the fixed {theme.usd_b(threshold)} threshold.")
    extra = {"symbol": args.symbol, "window_ends": [dates[0], dates[-1]], "counts": counts,
                           "irregular_dates": [d for d, flag in zip(dates, irregular, strict=True) if flag],
                           "llm_labels_present": {"end_of_day": bool(llm_full_known), "composite": bool(llm_composite_known)}}
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
