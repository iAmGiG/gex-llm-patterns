#!/usr/bin/env python3
"""How the daily GEX series differ: yearly mean |GEX| and daily sign agreement between series, SPY 2008-2026.

Panel (a) draws the yearly mean of |net GEX| of each series (USD billions), with the $5B magnitude criterion of the
classifier for scale.  Panel (b) is a grid of the daily sign agreement between the series pairs that 05_report.py
compares (share of days on which both values are positive or both are not), one row per pair and one column per
year; a blank cell means the pair has no days in that year.

Input  results/series_comparison.csv (05_report.py), yearly rows (scope == 'year') of symbol SPY, columns
    series_a, series_b, symbol, scope, year, n_days, last_date, mean_abs_a_bn, mean_abs_b_bn, sign_agree_pct,
    exact_match_pct
  * a row compares two series on the days both have, so the yearly mean of one series comes from one of its pairs
    (MEAN_SOURCES, first pair present); the pair used is written to the manifest;
  * required pairs: jan2026_phase4a vs new_full and new_full vs new_ex0dte; the other pairs are drawn when present.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

import figdata
import theme

FIG_ID = "fig03_series_comparison"
RESULTS_FILES = ("series_comparison.csv", "report.yaml")
TABLE_KINDS: Sequence[str] = ()
SYMBOL = "SPY"
Pair = Tuple[str, str]
# Row order of panel (b): from the published inputs outward, then the rebuild and the 0DTE effect.
PAIR_ORDER: Tuple[Pair, ...] = (
    ("call_only", "jan2026_phase4a"),
    ("jan2026_phase4a", "new_full"),
    ("old_bs", "jan2026_phase4a"),
    ("old_bs", "new_full"),
    ("new_full", "new_ex0dte"),
)
REQUIRED_PAIRS: Tuple[Pair, ...] = (("jan2026_phase4a", "new_full"), ("new_full", "new_ex0dte"))
# Which comparison supplies the yearly mean |GEX| of a series: (series_a, series_b, column of this series).
MEAN_SOURCES: Dict[str, Tuple[Tuple[str, str, str], ...]] = {
    "jan2026_phase4a": (("jan2026_phase4a", "new_full", "mean_abs_a_bn"), ("call_only", "jan2026_phase4a", "mean_abs_b_bn"),
                        ("old_bs", "jan2026_phase4a", "mean_abs_b_bn")),
    "call_only": (("call_only", "jan2026_phase4a", "mean_abs_a_bn"),),
    "old_bs": (("old_bs", "new_full", "mean_abs_a_bn"), ("old_bs", "jan2026_phase4a", "mean_abs_a_bn")),
    "new_full": (("new_full", "new_ex0dte", "mean_abs_a_bn"), ("old_bs", "new_full", "mean_abs_b_bn"),
                 ("jan2026_phase4a", "new_full", "mean_abs_b_bn")),
    "new_ex0dte": (("new_full", "new_ex0dte", "mean_abs_b_bn"),),
}
SHORT_NAMES: Dict[str, str] = {
    "jan2026_phase4a": "published", "call_only": "call-only", "old_bs": "pre-rebuild", "new_full": "rebuilt",
    "new_ex0dte": "ex-0DTE",
}


def pair_label(pair: Pair) -> str:
    first, second = (SHORT_NAMES[k] for k in pair)
    return f"{first[0].upper()}{first[1:]} vs {second}"


def ordered_pairs(frame: pd.DataFrame) -> List[Pair]:
    """Pairs present in the CSV: the narrative order first, any further pair after it (nothing is dropped)."""
    present = {(a, b) for a, b in frame[["series_a", "series_b"]].drop_duplicates().itertuples(index=False)}
    known = [p for p in PAIR_ORDER if p in present]
    return known + sorted(present - set(known))


def series_means(frame: pd.DataFrame) -> Tuple[Dict[str, pd.Series], Dict[str, str]]:
    """{series: yearly mean |GEX| (USD B)} and {series: pair that supplied it}."""
    means: Dict[str, pd.Series] = {}
    origin: Dict[str, str] = {}
    for key, sources in MEAN_SOURCES.items():
        for series_a, series_b, column in sources:
            rows = frame[(frame["series_a"] == series_a) & (frame["series_b"] == series_b)]
            if not rows.empty:
                means[key] = rows.set_index("year")[column].sort_index()
                origin[key] = f"{series_a} vs {series_b}"
                break
    return means, origin


def grid(frame: pd.DataFrame, pairs: Sequence[Pair], years: Sequence[int]) -> np.ndarray:
    """(pairs x years) matrix of ``sign_agree_pct``; NaN where a pair has no days in the year."""
    values = np.full((len(pairs), len(years)), np.nan)
    column = {y: j for j, y in enumerate(years)}
    for i, (series_a, series_b) in enumerate(pairs):
        rows = frame[(frame["series_a"] == series_a) & (frame["series_b"] == series_b)]
        for year, value in zip(rows["year"], rows["sign_agree_pct"]):
            values[i, column[int(year)]] = value
    return values


def cell_text(value: float) -> str:
    """Whole percent for a cell below 100; a value that only rounds up to 100 prints 99, a full match prints nothing."""
    return "" if value >= 100.0 - 1e-9 else f"{min(round(value), 99):.0f}"


def set_year_ticks(ax, years: Sequence[int], step: int = 2, partial_year: Optional[int] = None) -> None:
    """Every ``step``-th year counted back from the last one, so the (partial) last year is always labelled."""
    shown = list(years)[::-1][::step][::-1]
    ax.set_xlim(years[0] - 0.5, years[-1] + 0.5)
    ax.set_xticks(shown)
    ax.set_xticklabels([theme.year_label(y, partial_year) for y in shown])


def partial_year_note(frame: pd.DataFrame) -> Optional[str]:
    """'* 2026: trading days up to 2026-10-09.' for the last year when its rows stop before 31 December."""
    year = int(frame["year"].max())
    last = frame.loc[frame["year"] == year, "last_date"].max()
    if last >= pd.Timestamp(year=year, month=12, day=24):
        return None
    return f"* {year}: trading days up to {last.date().isoformat()}."


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = theme.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    comparison = figdata.load_series_comparison(inputs)
    spy = comparison[comparison["symbol"] == SYMBOL]
    if spy.empty:
        inputs.fail(f"series_comparison.csv has no yearly rows for {SYMBOL}")
    pairs = ordered_pairs(spy)
    missing = [f"{a} vs {b}" for a, b in REQUIRED_PAIRS if (a, b) not in pairs]
    if missing:
        inputs.fail(f"series_comparison.csv lacks the required pair(s) {missing} for {SYMBOL}")
    criterion = figdata.classifier_thresholds(inputs)["magnitude_bn"]
    means, origin = series_means(spy)
    years = list(range(int(spy["year"].min()), int(spy["year"].max()) + 1))
    values = grid(spy, pairs, years)

    fig = theme.new_figure(4.7)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 3.05], height_ratios=[1.75, 0.2 + 0.2 * len(pairs)])
    ax_a = fig.add_subplot(gs[0, 1])
    ax_b = fig.add_subplot(gs[1, 1], sharex=ax_a)
    ax_key = fig.add_subplot(gs[0, 0])
    ax_row = fig.add_subplot(gs[1, 0], sharey=ax_b)
    ax_key.axis("off")
    ax_row.axis("off")

    # (a) yearly mean |net GEX| per series; the published inputs are drawn last, hollow, so what lies under them shows
    theme.panel_title(ax_a, "a", "Mean |net GEX| by year")
    handles: List[Line2D] = []
    for key in theme.SERIES_ORDER:
        if key not in means:
            continue
        hollow = key == "jan2026_phase4a"
        line = ax_a.plot(means[key].index, means[key].to_numpy(float), color=theme.series_color(key),
                         marker=theme.series_marker(key), markersize=5.2 if hollow else 4.0, markeredgewidth=1.0 if hollow else 0.0,
                         markerfacecolor="none" if hollow else theme.series_color(key), linewidth=1.2,
                         zorder=4 if hollow else 3, label=theme.series_label(key))[0]
        handles.append(line)
    theme.threshold_line(ax_a, criterion)
    handles.append(Line2D([], [], color=theme.THRESHOLD, linewidth=0.8, linestyle=(0, (4, 2)),
                          label=f"{theme.usd_b(criterion)} magnitude criterion"))
    top = max(float(s.max()) for s in means.values())
    ax_a.set_ylim(0, top * 1.06)
    ax_a.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax_a.set_ylabel("Mean |net GEX| (USD billions)")
    ax_a.tick_params(labelbottom=False)
    theme.style_grid(ax_a)
    ax_key.legend(handles=handles, labels=[h.get_label() for h in handles], loc="upper left", borderaxespad=0.0,
                  handlelength=1.8)

    # (b) daily sign agreement, one row per pair
    theme.panel_title(ax_b, "b", "Daily sign agreement between series (%)")
    cmap = theme.sequential_cmap()
    ax_b.pcolormesh(np.arange(years[0] - 0.5, years[-1] + 1.0), np.arange(len(pairs) + 1), np.ma.masked_invalid(values),
                    cmap=cmap, vmin=0.0, vmax=100.0, edgecolors=theme.SURFACE, linewidth=1.0)
    for i in range(len(pairs)):
        for j, year in enumerate(years):
            if np.isfinite(values[i, j]) and cell_text(values[i, j]):
                ax_b.text(year, i + 0.5, cell_text(values[i, j]), ha="center", va="center", fontsize=8,
                          color=theme.ink_on_fill(cmap(values[i, j] / 100.0)))
    ax_b.set_ylim(len(pairs), 0)
    ax_b.set_yticks([])
    for spine in ("left", "bottom"):
        ax_b.spines[spine].set_visible(False)
    ax_b.tick_params(axis="x", length=0)
    note = partial_year_note(spy)
    set_year_ticks(ax_b, years, partial_year=years[-1] if note else None)
    for i, pair in enumerate(pairs):
        ax_row.text(1.0, i + 0.5, pair_label(pair), ha="right", va="center", fontsize=8, transform=ax_row.get_yaxis_transform())

    theme.footnote(fig, f"{SYMBOL}, daily values. (a) Yearly mean over the days a series shares with its comparison partner; "
                        "the published inputs are drawn hollow, on top. (b) Share of days on which both values are positive or "
                        "both are not; dark cells without a number are 100%, blank cells have no days that year."
                        + (f" {note}" if note else ""))

    extra = {"symbol": SYMBOL, "pairs": [f"{a} vs {b}" for a, b in pairs], "years": [years[0], years[-1]],
             "mean_abs_source_pair": origin, "partial_year_note": note}
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
