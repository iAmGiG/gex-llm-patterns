#!/usr/bin/env python3
"""One SPY window under four GEX conventions: the same 30 trading days, four sets of daily values.

Grouped daily bars of the net GEX (USD billions) of the 30-day window that ends on ``--window-end`` (default
2024-03-15) under the published Phase 4A inputs, the call leg alone (the put-less table that produced them), and
the rebuilt series with and without same-day expiries.  Dashed lines mark the +/-$5B magnitude criterion of the
deterministic classifier; the table under the bars gives the three criteria and the verdict for each window.

Input  <tables-dir>/windows/*.parquet (02_build_windows.py), the window of series jan2026_phase4a, call_only,
    new_ex0dte and new_full (symbol SPY) that ends on the chosen day: gex_sequence (the 30 values the model saw),
    window_start, clf_regime_type, clf_should_detect, clf_positive_days, clf_avg_magnitude, clf_sign_flips;
  <tables-dir>/series/*.parquet (01_build_series.py), the same four series: trading_date and net_gex, which date the
    30 values (the published inputs use their own calendar, which lacks 2024-03-11) and are checked against the
    window values;
  results/report.yaml (05_report.py): diagnostics.thresholds for the +/- magnitude lines.
  When no call_only window exists, it is derived from the stored call_gex of the new_full series on the dates of the
  new_full window (as 05_report.py derives the call_only series) and the manifest says so.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import figdata
import theme

FIG_ID = "fig02_convention_window"
RESULTS_FILES = ("report.yaml",)
TABLE_KINDS: Sequence[str] = ("windows", "series")
SYMBOL = "SPY"
DEFAULT_WINDOW_END = date(2024, 3, 15)
SERIES: Tuple[str, ...] = tuple(k for k in theme.SERIES_ORDER if k in ("jan2026_phase4a", "call_only", "new_full", "new_ex0dte"))
DERIVED_FROM = "new_full"  # call_only is derived from the call leg of this series when it has no window of its own
WINDOW_COLUMNS = ("series_key", "symbol", "window_end", "window_start", "gex_sequence", "clf_regime_type", "clf_should_detect",
                  "clf_positive_days", "clf_avg_magnitude", "clf_sign_flips")
GROUP_WIDTH = 0.86  # share of a trading-day slot taken by the bars of one day
TICK_EVERY = 5  # trading days between date labels, counted back from the last day
VALUE_TOLERANCE_USD = 1.0  # window values and series values must agree to the dollar
TABLE_COLUMNS = (0.045, 0.285, 0.425, 0.535, 0.635)  # left edge (axes fraction) of series, mean, days, flips, verdict
ROW_HEIGHT = 0.17  # inches


@dataclass
class Window:
    """The 30 values of one series for one window, with their calendar dates and the classifier verdict."""

    key: str
    start: pd.Timestamp
    dates: List[pd.Timestamp]
    values_bn: np.ndarray
    regime_type: str
    detected: bool
    positive_days: int
    mean_abs_bn: float
    sign_flips: int
    origin: str  # 'windows' or 'derived'


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--window-end", type=date.fromisoformat, default=DEFAULT_WINDOW_END, metavar="YYYY-MM-DD",
                        help="last day (T+0) of the window to draw (default: %(default)s)")


def dated_values(series: pd.DataFrame, key: str, start: pd.Timestamp, end: pd.Timestamp, column: str,
                 inputs: figdata.Inputs) -> Tuple[List[pd.Timestamp], np.ndarray]:
    """The 30 (date, value) rows of ``series_key == key`` between the window's first and last day."""
    rows = series[(series["series_key"] == key) & (series["trading_date"] >= start) & (series["trading_date"] <= end)]
    rows = rows.sort_values("trading_date")
    if len(rows) != theme.common.WINDOW_DAYS:
        inputs.fail(f"series parquet has {len(rows)} {key} rows between {start.date()} and {end.date()}, expected "
                    f"{theme.common.WINDOW_DAYS}; rebuild the series with 01_build_series.py")
    return list(rows["trading_date"]), rows[column].to_numpy(float)


def load_windows(inputs: figdata.Inputs, window_end: date) -> Dict[str, Window]:
    end = pd.Timestamp(window_end)
    stored = inputs.table("windows", WINDOW_COLUMNS, series_keys=SERIES, symbols=[SYMBOL])
    stored = stored[stored["window_end"] == end]
    present = [k for k in SERIES if k in set(stored["series_key"])]
    required = [k for k in SERIES if k != "call_only"]
    missing = [k for k in required if k not in present]
    if missing:
        inputs.fail(f"no {SYMBOL} window ending {window_end.isoformat()} for series {missing} in the windows parquet files "
                    f"(02_build_windows.py writes them)")
    series = inputs.table("series", ("series_key", "trading_date", "net_gex", "call_gex"), series_keys=SERIES, symbols=[SYMBOL])
    windows: Dict[str, Window] = {}
    for key in present:
        row = stored[stored["series_key"] == key].iloc[0]
        values = figdata.sequence_values(row["gex_sequence"])
        dates, from_series = dated_values(series, key, row["window_start"], end, "net_gex", inputs)
        if not np.allclose(values, from_series, rtol=0.0, atol=VALUE_TOLERANCE_USD):
            worst = float(np.abs(values - from_series).max())
            inputs.fail(f"{key}: window values differ from the series rows by up to USD {worst:,.0f}; the windows and series "
                        f"parquet files come from different builds")
        windows[key] = Window(key, row["window_start"], dates, values / 1e9, str(row["clf_regime_type"]),
                              bool(row["clf_should_detect"]), int(row["clf_positive_days"]),
                              float(row["clf_avg_magnitude"]) / 1e9, int(row["clf_sign_flips"]), "windows")
    if "call_only" not in windows:
        windows["call_only"] = derive_call_only(windows[DERIVED_FROM], series, end, inputs)
    return {k: windows[k] for k in SERIES}


def derive_call_only(base: Window, series: pd.DataFrame, end: pd.Timestamp, inputs: figdata.Inputs) -> Window:
    """call_only window from the stored call_gex of ``base``'s series on ``base``'s dates, classified like any window."""
    theme.logger.warning("%s: no call_only window ending %s; deriving it from the stored call_gex of %s", FIG_ID, end.date(),
                         base.key)
    dates, call = dated_values(series, base.key, base.start, end, "call_gex", inputs)
    if not np.isfinite(call).all():
        inputs.fail(f"{base.key} series rows have no call_gex, so no call_only window can be derived; build the call_only "
                    f"series and windows (01_build_series.py, 02_build_windows.py)")
    verdict = theme.common.classify(list(call))
    return Window("call_only", base.start, dates, call / 1e9, verdict["regime_type"], verdict["should_detect"],
                  verdict["positive_days"], verdict["avg_magnitude"] / 1e9, verdict["sign_flips"], "derived")


def verdict_text(window: Window) -> str:
    kind = window.regime_type.replace("persistent_", "").replace("_", " ")
    return f"Detected, {kind}" if window.detected else f"Not detected, {kind}"


def calendar_of(windows: Dict[str, Window]) -> List[pd.Timestamp]:
    return sorted({d for w in windows.values() for d in w.dates})


def skipped_by(window: Window, calendar: Sequence[pd.Timestamp]) -> List[pd.Timestamp]:
    """Calendar days between the window's first and last day that the window has no value for."""
    own = set(window.dates)
    return [d for d in calendar if window.dates[0] < d < window.dates[-1] and d not in own]


def calendar_note(windows: Dict[str, Window], calendar: Sequence[pd.Timestamp]) -> Optional[str]:
    """One sentence on series whose calendar skips a trading day the others have, so their window starts earlier."""
    parts: List[str] = []
    for key, window in windows.items():
        skipped = skipped_by(window, calendar)
        if skipped:
            days = ", ".join(d.date().isoformat() for d in skipped)
            parts.append(f"{theme.series_label(key)}: no row for {days}, which the other series have, so its window starts on "
                         f"{window.dates[0].date().isoformat()}")
    return ("; ".join(parts) + ".") if parts else None


def draw_bars(ax, windows: Dict[str, Window], calendar: Sequence[pd.Timestamp], criterion: float) -> None:
    position = {d: i for i, d in enumerate(calendar)}
    slot = GROUP_WIDTH / len(windows)
    for k, (key, window) in enumerate(windows.items()):
        offset = (k - (len(windows) - 1) / 2.0) * slot
        x = np.array([position[d] + offset for d in window.dates])
        ax.bar(x, window.values_bn, width=slot * 0.9, color=theme.series_color(key), zorder=3)
    last = len(calendar) - 1
    ax.axvspan(last - 0.5, last + 0.5, color=theme.PANEL_BG, zorder=0, linewidth=0)
    ax.axhline(0.0, color=theme.INK_SECONDARY, linewidth=0.6, zorder=2)
    theme.threshold_line(ax, criterion, f"+{theme.usd_b(criterion)}", va="bottom")
    theme.threshold_line(ax, -criterion, f"{theme.MINUS}{theme.usd_b(criterion)}", va="top")
    ticks = list(range(last, -1, -TICK_EVERY))[::-1]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{calendar[i]:%b} {calendar[i].day}" + ("\nT+0" if i == last else "") for i in ticks])
    ax.set_xlim(-0.8, last + 3.4)  # room on the right for the criterion labels
    ax.set_ylabel("Net GEX (USD billions)")
    years = sorted({d.year for d in calendar})
    ax.set_xlabel("Trading day, " + (str(years[0]) if len(years) == 1 else f"{years[0]}–{years[-1]}"))
    theme.style_grid(ax)


def draw_table(ax, windows: Dict[str, Window]) -> List[Any]:
    """Criteria and verdict of each window; returns the text artists (for the layout check)."""
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    texts: List[Any] = []
    header_y = 1.0
    heads = ("Series, in bar order", "Mean |GEX|\n(USD billions)", "Days\npositive", "Sign\nflips", "Rule verdict")
    for x, head in zip(TABLE_COLUMNS, heads):
        texts.append(ax.text(x, header_y, head, ha="left", va="top", fontsize=8, fontweight="bold", color=theme.INK))
    rows = len(windows)
    row_step = (1.0 - 0.34) / rows
    for i, (key, window) in enumerate(windows.items()):
        y = 1.0 - 0.34 - (i + 0.5) * row_step
        ax.plot([TABLE_COLUMNS[0] - 0.02], [y], marker="s", markersize=5.5, color=theme.series_color(key), clip_on=False,
                linestyle="none")
        cells = (theme.series_label(key), f"{window.mean_abs_bn:.1f}", f"{window.positive_days} of {theme.common.WINDOW_DAYS}",
                 str(window.sign_flips), verdict_text(window))
        for x, cell in zip(TABLE_COLUMNS, cells):
            texts.append(ax.text(x, y, cell, ha="left", va="center", fontsize=8, color=theme.INK))
    return texts


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = theme.parse_args(FIG_ID, __doc__, argv, configure=add_arguments)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    criterion = figdata.classifier_thresholds(inputs)["magnitude_bn"]
    windows = load_windows(inputs, args.window_end)
    calendar = calendar_of(windows)

    table_height = 0.34 + ROW_HEIGHT * len(windows)
    fig = theme.new_figure(2.9 + table_height + 0.55)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.9, table_height])
    ax = fig.add_subplot(gs[0])
    ax_table = fig.add_subplot(gs[1])
    draw_bars(ax, windows, calendar, criterion)
    ax.set_title(f"{SYMBOL}, 30 trading days ending {args.window_end.isoformat()} (day T+0)", loc="left", fontsize=9,
                 fontweight="bold")
    texts = draw_table(ax_table, windows)
    problems = theme.text_collisions(fig, texts) + theme.text_outside(fig, texts, ax_table)
    if problems:
        raise ValueError(f"{FIG_ID}: table layout problems:\n  " + "\n  ".join(problems))

    sentences = [f"Dashed lines: the {theme.usd_b(criterion)} magnitude criterion of the classifier (mean |GEX| of the 30 days)."]
    note = calendar_note(windows, calendar)
    if note:
        sentences.append(note)
    derived = [theme.series_label(k) for k, w in windows.items() if w.origin == "derived"]
    if derived:
        sentences.append(f"{derived[0]}: derived from the stored call leg of {theme.series_label(DERIVED_FROM)} (no stored window).")
    theme.footnote(fig, " ".join(sentences))

    extra = {"symbol": SYMBOL, "window_end": args.window_end.isoformat(), "series": list(windows),
             "window_start": {k: w.dates[0].date().isoformat() for k, w in windows.items()},
             "origin": {k: w.origin for k, w in windows.items()}, "calendar_days": len(calendar),
             "skipped_days": {k: [d.date().isoformat() for d in skipped_by(w, calendar)] for k, w in windows.items()},
             "detected": {k: w.detected for k, w in windows.items()}, "magnitude_criterion_bn": criterion}
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
