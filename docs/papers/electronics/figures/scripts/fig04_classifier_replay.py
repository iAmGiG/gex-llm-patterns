#!/usr/bin/env python3
"""Detection rate by year: the published o4-mini labels against the deterministic rule on each GEX convention.

SPY, 2020-2025 (the years with published labels).  One bar per convention and year: the published
o4-mini detection rate, then the Paper 2 criteria (>= 70% same-sign days, mean |GEX| >= $5B, <= 5 sign
flips) replayed on the exact published inputs, on the call leg only, on the pre-rebuild archive, and on
the rebuilt table without and with 0DTE.  No LLM call is needed for any bar except the first.

Input  results/detection_by_year.csv, the long table of 05_report.py, read by figdata.load_detection_by_year():
  * one row per classifier series and year (label_source == 'classifier', arm blank) and one row per LLM arm, model,
    series and year (label_source == 'llm'); the all-years rows (scope == 'all') are not used; a repeated key stops the
    figure;
  * columns used: series_key, symbol, year, n, n_detect, rate_pct, ci_lo_pct, ci_hi_pct (percent, Wilson 95% interval),
    n_windows, n_parsed and arm_role (LLM rows) and n_indep_30d; the loader turns percent into fractions;
  * symbol SPY; published labels: arm r1_o4mini (arm_role backfill), the answers parsed in January 2026: 1,412 of the 1,476
    windows.  The 64 answers recovered later are in the separate arm r1_o4mini_all (arm_role backfill_all); they are not
    drawn, their number is named in the footnote and in the manifest (extra.published).  The rate of the published bar is
    over its parsed windows (n_parsed), a classifier rate over all windows of the series (n);
  * classifier series jan2026_phase4a, new_ex0dte and new_full are required for every year with a published bar,
    call_only and old_bs are drawn when present;
  * a missing required series or year stops the figure; a missing optional series or year is logged, listed in the
    manifest (extra.gaps, extra.absent_optional_series) and named in the footnote, never silently left out.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib.patches import Patch

import figdata
import theme

logger = logging.getLogger("electronics.figures")

FIG_ID = "fig04_classifier_replay"
RESULTS_FILES = ("detection_by_year.csv",)
TABLE_KINDS: Sequence[str] = ()
SYMBOL = "SPY"
PUBLISHED_ARM = figdata.PUBLISHED_ARM  # r1_o4mini: the published answers without the ones recovered in 2026
# (series key, label); drawn left to right inside each year group
CLASSIFIER_SERIES = (
    ("jan2026_phase4a", "Rule on published inputs"),
    ("call_only", "Rule, call leg only"),
    ("old_bs", "Rule, pre-rebuild archive"),
    ("new_ex0dte", "Rule, rebuilt ex-0DTE"),
    ("new_full", "Rule, rebuilt 0DTE incl."),
)
REQUIRED = ("jan2026_phase4a", "new_ex0dte", "new_full")
LABELLED = ("new_ex0dte", "new_full")  # value labels on these two for the years after the convention change
LABEL_YEARS = (2024, 2025)
LEGEND_COLUMNS = 3
BATCH_SERIES = "jan2026_phase4a"  # the windows the published run was made on
COVERAGE_FLOOR = 0.9  # a series with fewer windows than this share of the January batch in a year is reported in the manifest


class Replay(NamedTuple):
    """The classifier bars and what was not drawn."""

    bars: List[Dict[str, Any]]  # one per classifier series present, reindexed to the published years
    gaps: Dict[str, List[int]]  # optional series -> published years in which it has no row
    absent: List[str]  # optional series without any row
    not_shown: Dict[str, List[int]]  # series -> years it has beyond the published years
    thin: Dict[str, Dict[int, List[int]]]  # series -> {year: [windows, windows of the January batch]} below COVERAGE_FLOOR


def published_rows(inputs: figdata.Inputs, detection: pd.DataFrame) -> pd.DataFrame:
    """The published o4-mini rows of SPY indexed by year; the year set of the figure.

    The years are those in which the arm has rows.  A year inside that span without a row, or a row without a parsed
    answer, stops the figure: the reference bar of a year must not disappear quietly.
    """
    rows = detection[detection["arm"] == PUBLISHED_ARM]
    if rows.empty:
        inputs.fail(f"detection_by_year.csv has no {PUBLISHED_ARM} rows for {SYMBOL}: the published labels are the reference")
    roles = sorted(set(rows["arm_role"].dropna().astype(str)))
    if roles != ["backfill"]:
        inputs.fail(f"arm {PUBLISHED_ARM} has arm_role {roles}, expected ['backfill'] (the published answers without the ones recovered "
                    f"in 2026; 05_report.py labels the variant with all of them {PUBLISHED_ARM}{figdata.ALL_SUFFIX})")
    try:
        rows = figdata.one_per_year(rows, f"arm {PUBLISHED_ARM}")
    except ValueError as exc:
        inputs.fail(str(exc))
    span = range(int(rows.index.min()), int(rows.index.max()) + 1)
    absent = [y for y in span if y not in rows.index]
    unanswered = [int(y) for y in rows.index[rows["llm_rate"].isna()]]
    problems = ([f"no row for year(s) {absent}"] if absent else []) + ([f"no parsed answer in year(s) {unanswered}"] if unanswered else [])
    if problems:
        inputs.fail(f"the {PUBLISHED_ARM} rows of {SYMBOL} have " + " and ".join(problems))
    return rows


def classifier_bars(inputs: figdata.Inputs, detection: pd.DataFrame, published: pd.DataFrame) -> Replay:
    """One bar per classifier series, reindexed to the years of the ``published`` rows.

    A required series that is absent, or lacks one of the years, stops the figure.  An optional series that is
    absent, or lacks some years, is kept (with NaN where it has no row) and reported in the returned :class:`Replay`,
    as is a series that has fewer windows in a year than ``COVERAGE_FLOOR`` of the windows of the January batch.
    """
    years = [int(y) for y in published.index]
    try:
        classifier = figdata.classifier_rates(detection)
    except ValueError as exc:
        inputs.fail(str(exc))
    present = set(classifier["series_key"])
    lacking = [k for k in REQUIRED if k not in present]
    if lacking:
        inputs.fail(f"detection_by_year.csv lacks classifier rows for series {lacking} (symbol {SYMBOL}); "
                    "run 02_build_windows.py for them, then 05_report.py")
    batch = classifier[classifier["series_key"] == BATCH_SERIES].set_index("year")["n"].reindex(years)
    bars: List[Dict[str, Any]] = []
    gaps: Dict[str, List[int]] = {}
    absent: List[str] = []
    not_shown: Dict[str, List[int]] = {}
    thin: Dict[str, Dict[int, List[int]]] = {}
    for key, label in CLASSIFIER_SERIES:
        if key not in present:
            absent.append(key)
            logger.warning("%s: no classifier rows for %s (%s); its bar is not drawn", FIG_ID, key, label)
            continue
        rows = classifier[classifier["series_key"] == key].set_index("year").sort_index()
        frame = rows.reindex(list(years))
        missing = figdata.years_without(frame, years, "clf_rate")
        if missing and key in REQUIRED:
            inputs.fail(f"detection_by_year.csv has no {key} classifier row for {SYMBOL} in year(s) {missing}; "
                        f"the published bars cover {years[0]}-{years[-1]}")
        if missing:
            gaps[key] = missing
            logger.warning("%s: %s has no classifier row for year(s) %s; those bars are not drawn", FIG_ID, key, missing)
        beyond = sorted(int(y) for y in rows.index if int(y) not in set(years))
        if beyond:
            not_shown[key] = beyond
        short = {int(y): [int(n), int(r)] for y, n, r in zip(years, frame["n"], batch, strict=True)
                 if pd.notna(n) and n < COVERAGE_FLOOR * r}
        if short:
            thin[key] = short
            logger.warning("%s: %s has fewer windows than the January batch (year: [windows, batch]): %s", FIG_ID, key, short)
        bars.append({"label": label, "color": theme.series_color(key), "key": key, "frame": frame, "rate": "clf_rate",
                     "ci": figdata.ci_columns(classifier, "clf")})
    return Replay(bars, gaps, absent, not_shown, thin)


def footnote_text(inputs: figdata.Inputs, published: pd.DataFrame, bars: Sequence[Dict[str, Any]], ci_label: str,
                  gaps: Dict[str, List[int]], absent: Sequence[str], recovered: Optional[pd.Series] = None) -> str:
    """Footnote under the figure: interval method, effective sample size, what each bar is, and any bar that is not drawn.

    ``recovered`` (answers per year of the ``r1_o4mini_all`` arm beyond the published arm, from
    :func:`figdata.recovered_by_year`) adds how many answers the first bar leaves out.
    """
    independent = pd.concat([b["frame"]["n_indep_30d"] for b in bars]).dropna()
    if independent.empty:
        inputs.fail("detection_by_year.csv has no n_indep_30d for the plotted rows (05_report.py needs the windows table to count "
                    "non-overlapping windows); the intervals cannot be qualified")
    low, high = int(independent.min()), int(independent.max())
    span = str(low) if low == high else f"{low}{theme.ENDASH}{high}"
    # the published result is the answers parsed in January 2026; every window of the batch (the jan2026_phase4a windows) was sent
    parsed = int(published["n_parsed"].sum())
    sent = int(next(b for b in bars if b["key"] == BATCH_SERIES)["frame"]["n"].sum())
    labels = dict(CLASSIFIER_SERIES)
    omitted = [f"{labels[k]} (no windows)" for k in absent]
    omitted += [f"{labels[k]} in {', '.join(map(str, years))}" for k, years in gaps.items()]
    left_out = int(recovered.sum()) if recovered is not None else 0
    recovery = f"; the {left_out:,} answers re-parsed in 2026 are not drawn" if left_out else ""
    text = (f"{SYMBOL}, 30-day windows by year of the window end. Error bars: {ci_label}; a year holds only {span} "
            f"non-overlapping windows. First bar: o4-mini output of January 2026 (parsed answers for {parsed:,} of {sent:,} "
            f"windows{recovery}); other bars: the rule applied to all windows of the series in the legend.")
    if omitted:
        text += " Not drawn: " + "; ".join(omitted) + "."
    return text


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = theme.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    detection = figdata.load_detection_by_year(inputs)
    detection = detection[detection["symbol"] == SYMBOL]

    published = published_rows(inputs, detection)
    years = [int(y) for y in published.index]
    bars: List[Dict[str, Any]] = [{
        "label": "Published o4-mini labels", "color": theme.PUBLISHED_COLOR, "key": PUBLISHED_ARM,
        "frame": published.reindex(years), "rate": "llm_rate", "ci": figdata.ci_columns(published, "llm"),
    }]
    replay = classifier_bars(inputs, detection, published)
    bars += replay.bars
    methods = {bar["ci"][2] for bar in bars}
    if len(methods) > 1:  # the bars come from frames that do not all carry the same interval: draw the one every bar has
        logger.warning("%s: intervals of different kinds %s; drawing the Wilson interval on every bar", FIG_ID, sorted(methods))
        for bar in bars:
            bar["ci"] = figdata.ci_columns(bar["frame"], "llm" if bar["rate"] == "llm_rate" else "clf", method="wilson")
    try:
        recovered = figdata.recovered_by_year(detection, PUBLISHED_ARM, SYMBOL)
    except ValueError as exc:
        inputs.fail(str(exc))
    logger.info("%s: %s %d-%d: %d parsed published answers%s; classifier bars %s", FIG_ID, SYMBOL, years[0], years[-1],
                int(published["n_parsed"].sum()), "" if recovered is None else f" ({int(recovered.sum())} recovered answers not drawn)",
                [b["key"] for b in replay.bars])

    fig = theme.new_figure(3.35)
    ax = fig.add_subplot(1, 1, 1)
    group = 0.84
    width = group / len(bars)
    x0 = np.arange(len(years), dtype=float)
    for i, bar in enumerate(bars):
        offset = (i - (len(bars) - 1) / 2) * width
        frame = bar["frame"]
        y = frame[bar["rate"]].to_numpy(float) * 100.0
        ok = ~np.isnan(y)
        ax.bar(x0[ok] + offset, y[ok], width * 0.88, color=bar["color"], zorder=2)
        lo_col, hi_col, _ = bar["ci"]
        err = figdata.whiskers(frame.loc[ok], bar["rate"], lo_col, hi_col)
        ax.errorbar(x0[ok] + offset, y[ok], yerr=err, fmt="none", ecolor=theme.INK, elinewidth=0.6, capsize=1.1, capthick=0.6,
                    zorder=3)
        if bar["key"] in LABELLED:
            for xi, yi, year in zip(x0[ok] + offset, y[ok], np.array(years)[ok], strict=True):
                if year in LABEL_YEARS:
                    top = float(frame.loc[year, hi_col]) * 100.0
                    ax.text(xi, top + 2.0, f"{yi:.1f}", rotation=90, ha="center", va="bottom", fontsize=8, color=theme.INK)
    ax.set_xticks(x0)
    ax.set_xticklabels([str(y) for y in years])
    ax.set_xlim(-0.55, len(years) - 0.45)
    theme.percent_axis(ax)
    ax.set_ylabel("Detection rate (%)")
    theme.style_grid(ax)
    handles = [Patch(facecolor=bar["color"], edgecolor="none") for bar in bars]
    labels = [bar["label"] for bar in bars]
    fig.legend(*theme.row_major(handles, labels, LEGEND_COLUMNS), loc="outside upper center", ncol=LEGEND_COLUMNS,
               handlelength=1.0, columnspacing=1.6)
    ci_label = bars[0]["ci"][2]
    theme.footnote(fig, footnote_text(inputs, published, bars, ci_label, replay.gaps, replay.absent, recovered))

    extra = {
        "symbol": SYMBOL, "years": years, "bars": [b["key"] for b in bars], "ci": ci_label,
        "published": {"arm": PUBLISHED_ARM, "arm_role": sorted(set(published["arm_role"].astype(str))),
                      "model": sorted(set(published["model"].astype(str))),
                      "n_windows_by_year": {int(y): int(published.loc[y, "n_windows"]) for y in years},
                      "n_parsed_by_year": {int(y): int(published.loc[y, "n_parsed"]) for y in years},
                      "n_parsed_total": int(published["n_parsed"].sum()),
                      "arm_with_recovered_answers": None if recovered is None else PUBLISHED_ARM + figdata.ALL_SUFFIX,
                      "recovered_2026_by_year": None if recovered is None else {int(y): int(n) for y, n in recovered.items()},
                      "recovered_2026_total": None if recovered is None else int(recovered.sum())},
        "classifier_windows_by_year": {b["key"]: {int(y): (None if pd.isna(n) else int(n)) for y, n in b["frame"]["n"].items()}
                                       for b in bars[1:]},
        "n_indep_30d_by_year": {b["key"]: {int(y): (None if pd.isna(n) else int(n)) for y, n in b["frame"]["n_indep_30d"].items()}
                                for b in bars},
        "gaps": replay.gaps, "absent_optional_series": replay.absent, "years_not_shown": replay.not_shown,
        "low_coverage": replay.thin, "coverage_floor": COVERAGE_FLOOR,
    }
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
