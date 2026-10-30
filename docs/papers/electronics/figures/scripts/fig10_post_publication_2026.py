#!/usr/bin/env python3
"""Post-publication period: per-window labels of the deterministic rule and of gpt-6-luna, 2026.

Every 30-day window that ends in 2026, one cell per window: the label of the Paper 2 rule, the label of
gpt-6-luna on the same window and, below them, the windows on which the two differ.  A cell is blue for a
persistent regime of positive GEX, red for one of negative GEX, dark grey for a detection of another type,
and light grey for a rejected window (mid grey: transitional, pale grey: low conviction).  The panel above
shows the 30-day mean |GEX| that the magnitude test compares with $5B.  2026 is called the post-publication
period, not out-of-sample: gpt-6-luna was created on 2026-09-14.

Input  results/post_publication_2026.csv (05_report.py) and the windows parquet copies (window_start only)
  * post_publication_2026.csv: one row per window ending on or after 2026-01-01 and per (series_key, symbol) with
    clf_regime_type, clf_should_detect, clf_avg_magnitude_bn and, for every LLM arm that scored the series,
    llm_<arm> (regime_detected) and llm_type_<arm> (regime_type); a blank cell is a window the arm did not score;
  * windows parquet (series, symbol): window_start decides which windows still contain days of 2025 (their window
    began before 2026-01-01).  Without those files the first 29 windows of each series are taken to be those windows,
    which is exact for 30 consecutive series rows.
  Defaults: SPY, series new_full and new_ex0dte (--symbols and --series change that; the paper caption is SPY only).
"""

from __future__ import annotations

import argparse
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import figdata
import figllm
import theme
from theme import common

FIG_ID = "fig10_post_publication_2026"
RESULTS_FILES = ("post_publication_2026.csv",)
TABLE_KINDS: Sequence[str] = ("windows",)
DEFAULT_SYMBOLS = ("SPY",)
DEFAULT_SERIES = (figllm.FULL, figllm.EX0DTE)
YEAR_START = pd.Timestamp("2026-01-01")
CORE_COLUMNS = ("window_end", "series_key", "symbol", "clf_regime_type", "clf_should_detect", "clf_avg_magnitude_bn")

# cell codes of the label strips (colour index); 0 is a window without a label and stays white
CELLS = (
    ("persistent_positive", "Persistent, positive GEX", theme.POSITIVE),
    ("persistent_negative", "Persistent, negative GEX", theme.NEGATIVE),
    ("detected_other", "Detected, other type", theme.INK_SECONDARY),
    ("transitional", "Rejected: transitional", "#B5B5B5"),
    ("low_conviction", "Rejected: low conviction", "#E2E2E2"),
    ("differs", "gpt-6-luna differs from the rule", theme.INK),
)
CODE = {name: i + 1 for i, (name, _, _) in enumerate(CELLS)}
SYMBOL_LINESTYLE = {"SPY": "-", "QQQ": (0, (5, 2)), "IWM": (0, (1, 1.5))}
SERIES_TITLE = {figllm.FULL: "Rebuilt, 0DTE incl.", figllm.EX0DTE: "Rebuilt, ex-0DTE"}
SERIES_LEGEND = {figllm.FULL: "rebuilt 0DTE incl.", figllm.EX0DTE: "rebuilt ex-0DTE"}


def add_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS), choices=figllm.SYMBOLS, metavar="SYMBOL",
                        help="symbols to draw (default: %(default)s)")
    parser.add_argument("--series", nargs="+", default=list(DEFAULT_SERIES), metavar="SERIES_KEY",
                        help="window series to draw (default: %(default)s)")


def cell_code(detected, regime_type) -> int:
    """Colour code of one label: the detection flag decides, the regime type colours it."""
    if detected is pd.NA or detected is None or pd.isna(detected):
        return 0
    kind = None if regime_type is None or pd.isna(regime_type) else str(regime_type)
    if detected:
        return CODE[kind] if kind in ("persistent_positive", "persistent_negative") else CODE["detected_other"]
    return CODE["low_conviction"] if kind == "low_conviction" else CODE["transitional"]


def llm_column(group: pd.DataFrame, flag_columns: Sequence[str]) -> Optional[str]:
    """The ``llm_<arm>`` column that scored the most windows of this (series, symbol); None when no arm did."""
    counts = {c: int(group[c].notna().sum()) for c in flag_columns}
    best = max(counts, key=lambda c: (counts[c], c), default=None)
    return best if best is not None and counts[best] > 0 else None


def first_whole_year_window(inputs: figdata.Inputs, groups: Sequence[dict], dates: Sequence[pd.Timestamp]) -> Tuple[Optional[pd.Timestamp], str]:
    """First window end whose window starts in 2026 (stored window_start), else the 30th window of the year."""
    directory = inputs.tables_dir / "windows"
    if directory.is_dir() and any(directory.glob("*.parquet")):
        win = inputs.table("windows", ("series_key", "symbol", "window_start", "window_end"),
                           series_keys=sorted({g["series_key"] for g in groups}), symbols=sorted({g["symbol"] for g in groups}))
        whole = win[(win["window_start"] >= YEAR_START) & (win["window_end"] >= YEAR_START)]
        if len(whole):
            return whole["window_end"].min(), "windows parquet (window_start)"
    position = common.WINDOW_DAYS - 1
    return (dates[position] if len(dates) > position else None), "position (30th window of the year)"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figllm.parse_args(FIG_ID, __doc__, argv, add_options)
    inputs = figllm.open_inputs(FIG_ID, args)
    frame = inputs.csv("post_publication_2026.csv", CORE_COLUMNS)
    frame["window_end"] = pd.to_datetime(frame["window_end"])
    frame["clf_should_detect"] = figllm.as_flag(frame["clf_should_detect"])
    flag_columns = [c for c in frame.columns if c.startswith("llm_") and not c.startswith("llm_type_")]
    for column in flag_columns:
        frame[column] = figllm.as_flag(frame[column])

    # ---- one group per (symbol, series): rule labels, the LLM arm that scored it, magnitude
    groups: List[dict] = []
    for symbol in args.symbols:
        for key in args.series:
            part = frame[(frame["symbol"] == symbol) & (frame["series_key"] == key)].sort_values("window_end")
            if part.empty:
                inputs.fail(f"post_publication_2026.csv has no windows for {symbol} {key} (05_report.py writes the windows of 2026)")
            column = llm_column(part, flag_columns)
            groups.append({"symbol": symbol, "series_key": key, "frame": part.set_index("window_end"), "llm_column": column,
                           "arm": column[len("llm_"):] if column else None})
    dates = sorted({d for g in groups for d in g["frame"].index})
    n_dates = len(dates)

    # ---- label grid
    rows: List[dict] = []
    summary: List[dict] = []
    for g in groups:
        part = g["frame"].reindex(dates)
        rule = np.array([cell_code(d, t) for d, t in zip(part["clf_should_detect"], part["clf_regime_type"], strict=True)], dtype=float)
        rows.append({"group": g, "kind": "rule", "codes": rule})
        entry = {"symbol": g["symbol"], "series_key": g["series_key"], "arm": g["arm"], "windows": int(part["clf_should_detect"].notna().sum()),
                 "rule_detects": int(part["clf_should_detect"].fillna(False).sum())}
        if g["llm_column"]:
            type_column = f"llm_type_{g['arm']}"
            types = part[type_column] if type_column in part.columns else pd.Series([None] * n_dates, index=part.index)
            llm = np.array([cell_code(d, t) for d, t in zip(part[g["llm_column"]], types, strict=True)], dtype=float)
            both = part["clf_should_detect"].notna() & part[g["llm_column"]].notna()
            differs = both & (part["clf_should_detect"] != part[g["llm_column"]])
            rows.append({"group": g, "kind": "llm", "codes": llm})
            rows.append({"group": g, "kind": "differs", "codes": np.where(differs, CODE["differs"], np.nan)})
            entry.update({"scored": int(both.sum()), "llm_detects": int(part[g["llm_column"]].fillna(False).sum()),
                          "differs": int(differs.sum()), "agree_pct": 100.0 * (1.0 - differs.sum() / both.sum()) if both.any() else None})
        summary.append(entry)
    boundary, boundary_source = first_whole_year_window(inputs, groups, dates)
    # windows before this index contain days of 2025
    cut = int(np.searchsorted(np.array(dates, dtype="datetime64[ns]"), np.datetime64(boundary))) if boundary is not None else 0

    # ---- figure
    n_label_rows = len(rows)
    label_height = 0.2 * n_label_rows + 0.36 * len(groups) + 0.35  # inches: rows, group headers, tick labels
    fig = theme.new_figure(1.2 + 1.3 + label_height + 0.9)
    grid = fig.add_gridspec(3, 1, height_ratios=[0.3, 1.3, label_height], hspace=0.0)
    ax_strip = fig.add_subplot(grid[0])
    ax_mag = fig.add_subplot(grid[1], sharex=ax_strip)
    ax_lab = fig.add_subplot(grid[2], sharex=ax_strip)
    xlim = (-0.5, n_dates - 0.5)
    spans = []
    if cut > 0:
        spans.append((-0.5, cut - 0.5, "Includes\n2025 days"))
    spans.append((cut - 0.5 if cut > 0 else -0.5, n_dates - 0.5, "Windows entirely in 2026: post-publication period"))
    figllm.span_strip(ax_strip, [(a, b, t) for a, b, t in spans], xlim)
    for ax in (ax_mag, ax_lab):
        if cut > 0:
            ax.axvline(cut - 0.5, color=theme.INK_SECONDARY, linewidth=0.7, linestyle=(0, (2, 2)), zorder=1.5)

    # magnitude panel
    peak = 0.0
    for g in groups:
        part = g["frame"].reindex(dates)
        y = part["clf_avg_magnitude_bn"].to_numpy(float)
        peak = max(peak, float(np.nanmax(y)))
        ax_mag.plot(np.arange(n_dates), y, color=theme.series_color(g["series_key"]), linewidth=1.1,
                    linestyle=SYMBOL_LINESTYLE.get(g["symbol"], "-"), zorder=3)
    threshold = common.classifier().magnitude_threshold / 1e9
    theme.threshold_line(ax_mag, threshold)
    ax_mag.text(1.012, threshold, theme.usd_b(threshold), transform=ax_mag.get_yaxis_transform(), ha="left", va="center", fontsize=8,
                color=theme.INK_SECONDARY)
    ax_mag.set_ylim(0, max(peak, threshold) * 1.1)
    ax_mag.set_ylabel("Mean |GEX| (\\$B)")
    theme.panel_title(ax_mag, "a", "30-day mean |GEX| of the window")
    theme.style_grid(ax_mag)

    # label strips
    items: List[tuple] = []
    last = None
    for row in rows:
        g = row["group"]
        if g is not last:
            entry = next(e for e in summary if (e["symbol"], e["series_key"]) == (g["symbol"], g["series_key"]))
            title = SERIES_TITLE.get(g["series_key"], g["series_key"]) + (f", {g['symbol']}" if len(args.symbols) > 1 else "")
            if "differs" in entry:
                title += f":  gpt-6-luna differs from the rule in {entry['differs']} of {entry['scored']} windows"
            elif not g["llm_column"]:
                title += ":  no gpt-6-luna labels"
            items.append(("header", title))
            last = g
        items.append(("row", {"rule": "Rule", "llm": "gpt-6-luna", "differs": "Differs"}[row["kind"]], row["codes"],
                      0.5 if row["kind"] == "differs" else 1.0))
    figllm.label_grid(ax_lab, items, [color for _, _, color in CELLS], n_dates)
    figllm.month_ticks(ax_lab, dates)
    ax_lab.tick_params(axis="x", length=2.5)
    ax_lab.set_xlabel(f"Window end date, {dates[0].year}")
    ax_lab.set_xlim(*xlim)
    theme.panel_title(ax_lab, "b", "Label of each window")
    for ax in (ax_strip, ax_mag):
        ax.tick_params(labelbottom=False)

    present = {int(v) for r in rows for v in np.unique(r["codes"][~np.isnan(r["codes"])])}
    handles = [figllm.patch_handle(color, label) for name, label, color in CELLS if CODE[name] in present]
    handles += [Line2D([0], [0], color=theme.series_color(k), linewidth=1.1, label=f"Mean |GEX|, {SERIES_LEGEND.get(k, k)}")
                for k in args.series]
    fig.legend(handles=handles, loc="outside upper center", ncol=3, columnspacing=1.2)
    missing_llm = [f"{g['series_key']}/{g['symbol']}" for g in groups if not g["llm_column"]]
    note = (f"Each cell is a 30-day window ending on that trading day ({n_dates} window ends). The dotted line marks the first window that lies "
            f"entirely in 2026; earlier windows still contain days of 2025. Dashed horizontal line in (a): the fixed "
            f"{theme.usd_b(threshold)} magnitude threshold.")
    if missing_llm:
        note += f" No gpt-6-luna labels in the results for {', '.join(missing_llm)}."
    theme.footnote(fig, note)

    extra = {
        "symbols": list(args.symbols), "series": list(args.series), "window_ends": [dates[0], dates[-1]], "n_window_ends": n_dates,
        "first_window_entirely_in_2026": boundary, "boundary_source": boundary_source, "windows_with_2025_days": cut,
        "groups": summary, "llm_missing": missing_llm, "wording": "post-publication period (not out-of-sample)",
    }
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
