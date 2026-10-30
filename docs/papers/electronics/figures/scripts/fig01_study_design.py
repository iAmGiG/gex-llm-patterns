#!/usr/bin/env python3
"""Study design: daily GEX series, 30-day windows, deterministic labels and gpt-6-luna arms, with the stored counts.

A left-to-right schematic.  Each daily series of the study is cut into 30-trading-day windows; every window gets
the deterministic label of the Paper 2 criteria (no model, no cost) and, for each arm, a label from the model;
the two sets of labels are compared in the result tables.  Boxes carry the counts that were actually stored: daily
rows per series, windows, and the windows each arm answered, with the total cost of the model runs.

Input  results/report.yaml (05_report.py):
  * inputs.series.coverage, inputs.windows.coverage, inputs.detections.coverage: rows and first/last date per
    (series_key, symbol) and per (arm, model, series_key, symbol);
  * diagnostics.thresholds: the classifier criteria in force when the labels were made;
  * headline.cost.est_cost_usd: total cost of the runs (the cost_ledger section must have been written);
  * sections: which result files exist.
  Series and arms are listed in registry order (common.SERIES / common.ARMS); only those that have rows are drawn.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, Rectangle

import figdata
import theme

FIG_ID = "fig01_study_design"
RESULTS_FILES = ("report.yaml",)
TABLE_KINDS: Sequence[str] = ()

HEIGHT_IN = 4.62
PAD = 0.09  # inner padding of a box, inches
LINE = 0.128  # distance between text lines, inches
ARM_LINE = 0.13  # distance between arm rows, inches
STRIPE = 0.07  # colour stripe of a series box
COLUMNS = {"series": (0.04, 1.96), "windows": (2.20, 3.46), "labels": (3.70, 6.10)}  # x extent per column, inches
GROUP_PAD = 0.06  # the two label boxes sit inside a frame this much smaller than the column
SYMBOL_ORDER = ("SPY", "QQQ", "IWM")
TOP = 0.36  # y of the first box, below the column headers
SERIES_BOX_H, SERIES_GAP = 0.47, 0.05
RULE_BOX_H = 0.78  # the deterministic-rule box: five lines of text
RESULT_LABELS: Dict[str, str] = {
    "detection_by_year": "detection rate by year", "bridge_agreement": "model agreement (κ)",
    "series_comparison": "series comparison", "ex0dte_decomposition": "0DTE ablation",
    "post_publication_2026": "post-publication period", "intraday": "intraday check", "stats": "overlap-aware inference",
    "cost_ledger": "cost ledger",
}
STORED_IN = ("Every series value, window, label and answer is stored in backups.gex_llm_regime_series, _windows, _runs and "
             "_detections, with parquet copies and the raw Batch files. Counts from results/report.yaml.")


# --------------------------------------------------------------------------- data
def year_span(first: pd.Timestamp, last: pd.Timestamp) -> str:
    return f"{first.year}" if first.year == last.year else f"{first.year}–{last.year}"


def symbol_list(symbols: Sequence[str]) -> List[str]:
    """Symbols in the order the paper uses; any other symbol follows alphabetically."""
    known = [s for s in SYMBOL_ORDER if s in symbols]
    return known + sorted(set(symbols) - set(known))


def series_summary(coverage: pd.DataFrame, windows: pd.DataFrame) -> List[Dict[str, Any]]:
    """One entry per series key, in the order of the colour tokens: symbols, daily rows, year span and windows built."""
    out: List[Dict[str, Any]] = []
    for key in theme.SERIES_ORDER:
        rows = coverage[coverage["series_key"].map(theme.series_key) == key]
        if rows.empty:
            continue
        built = windows[windows["series_key"].map(theme.series_key) == key]
        out.append({"key": rows["series_key"].iloc[0], "label": theme.series_label(key),
                    "symbols": symbol_list(list(rows["symbol"].unique())), "rows": int(rows["rows"].sum()),
                    "span": year_span(rows["first"].min(), rows["last"].max()), "windows": int(built["rows"].sum())})
    return out


def wrap_items(items: Sequence[str], separator: str, fig, width_in: float, fontsize: float = 8.0) -> str:
    """Join ``items`` with ``separator`` and break lines between items only (an item never splits)."""
    renderer = fig.canvas.get_renderer()
    prop = FontProperties(size=fontsize)
    limit = width_in * fig.dpi
    lines: List[str] = []
    current = ""
    for item in items:
        trial = item if not current else current + separator + item
        if current and renderer.get_text_width_height_descent(trial, prop, ismath=False)[0] > limit:
            lines.append(current)
            current = item
        else:
            current = trial
    return "\n".join(lines + [current])


def arm_summary(coverage: pd.DataFrame) -> Tuple[List[Dict[str, Any]], int]:
    """Registered arms with rows (registry order), and the number of other requests (pilot, repeats)."""
    registered = [a for a in theme.common.ARMS if a in set(coverage["arm"])]
    arms = [{"key": a, "label": theme.arm_label(a), "rows": int(coverage.loc[coverage["arm"] == a, "rows"].sum()),
             "models": sorted(coverage.loc[coverage["arm"] == a, "model"].unique())} for a in registered]
    other = int(coverage.loc[~coverage["arm"].isin(registered), "rows"].sum())
    return arms, other


def written_results(report: Dict[str, Any]) -> List[str]:
    sections = report.get("sections") or {}
    return [RESULT_LABELS[name] for name in RESULT_LABELS if (sections.get(name) or {}).get("status") == "written"]


def total_cost(inputs: figdata.Inputs, report: Dict[str, Any]) -> float:
    try:
        return float(report["headline"]["cost"]["est_cost_usd"])
    except (KeyError, TypeError, ValueError):
        inputs.fail("report.yaml has no headline.cost.est_cost_usd: the cost_ledger section was not written (runs table is empty)")


# --------------------------------------------------------------------------- drawing helpers
class Canvas:
    """One axes spanning the figure; data coordinates are inches from the top-left corner (y grows downwards)."""

    def __init__(self, fig, width: float, height: float) -> None:
        fig.set_layout_engine("none")  # nothing here is laid out by constrained layout
        self.fig = fig
        self.ax = fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(height, 0)
        self.ax.axis("off")
        self.texts: List[Tuple[Any, Any]] = []  # (text artist, box it must stay inside or None)

    def box(self, x0: float, y0: float, x1: float, y1: float, face: str = theme.SURFACE, stripe: Optional[str] = None) -> Rectangle:
        patch = Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=face, edgecolor=theme.BASELINE, linewidth=0.8, zorder=1)
        self.ax.add_patch(patch)
        if stripe is not None:
            self.ax.add_patch(Rectangle((x0, y0), STRIPE, y1 - y0, facecolor=stripe, edgecolor="none", zorder=2))
        return patch

    def text(self, x: float, y: float, s: str, bold: bool = False, ha: str = "left", color: str = theme.INK,
             container: Any = None, size: float = 8.0) -> Any:
        artist = self.ax.text(x, y, s, ha=ha, va="top", fontsize=size, fontweight="bold" if bold else "normal", color=color,
                              zorder=3)
        self.texts.append((artist, container))
        return artist

    def lines(self, x: float, y: float, rows: Sequence[Tuple[str, bool]], container: Any = None) -> float:
        """Stack text lines from ``y`` downwards; returns the y below the last line."""
        for s, bold in rows:
            self.text(x, y, s, bold=bold, container=container)
            y += LINE
        return y

    def swatch(self, x: float, y: float, color: str) -> None:
        self.ax.add_patch(Rectangle((x, y + 0.012), 0.085, 0.085, facecolor=color, edgecolor="none", zorder=3))

    def arrow(self, start: Tuple[float, float], end: Tuple[float, float]) -> None:
        self.ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=7, linewidth=0.9,
                                          color=theme.INK_SECONDARY, shrinkA=0, shrinkB=0, zorder=2))

    def check(self) -> None:
        """Every text stays inside its box and no two texts overlap; raises with the offenders otherwise."""
        problems: List[str] = []
        for artist, container in self.texts:
            if container is not None:
                problems += theme.text_outside(self.fig, [artist], container)
        problems += theme.text_collisions(self.fig, [artist for artist, _ in self.texts])
        if problems:
            raise ValueError(f"{FIG_ID}: layout problems:\n  " + "\n  ".join(problems))


# --------------------------------------------------------------------------- the four parts of the schematic
def draw_series(canvas: Canvas, series: Sequence[Dict[str, Any]]) -> float:
    """One box per series with the rows stored and the windows cut from them; returns the y of the bottom edge."""
    x0, x1 = COLUMNS["series"]
    y = TOP
    for entry in series:
        box = canvas.box(x0, y, x1, y + SERIES_BOX_H, stripe=theme.series_color(entry["key"]))
        built = f"{entry['windows']:,} windows" if entry["windows"] else "no windows"
        canvas.lines(x0 + STRIPE + PAD, y + 0.045, [
            (entry["label"], True), (f"{', '.join(entry['symbols'])}, {entry['span']}", False),
            (f"{entry['rows']:,} rows, {built}", False)], container=box)
        y += SERIES_BOX_H + SERIES_GAP
    return y - SERIES_GAP


def draw_windows(canvas: Canvas, n_windows: int, last_end: str, middle: float) -> None:
    """What a window is: a compact box at mid height, between the series and the labels."""
    x0, x1 = COLUMNS["windows"]
    block = [("30 trading days", True), (f"Day T{theme.MINUS}29 … Day T+0", False), ("stride 1", False),
             ("no dates, no tickers", False), ("", False), (f"{n_windows:,} windows", True), (f"last end {last_end}", False)]
    half = (LINE * len(block) + 2 * PAD) / 2
    box = canvas.box(x0, middle - half, x1, middle + half, face=theme.PANEL_BG)
    canvas.lines(x0 + PAD, middle - half + PAD, block, container=box)
    canvas.arrow((COLUMNS["series"][1] + 0.03, middle), (x0 - 0.03, middle))


def draw_labels(canvas: Canvas, thresholds: Dict[str, float], n_windows: int, models: Sequence[str],
                arms: Sequence[Dict[str, Any]], other_requests: int, cost: float, bottom: float, middle: float) -> None:
    """A frame around the two label sources: the deterministic rule and the model arms with their counts and cost."""
    x0, x1 = COLUMNS["labels"]
    canvas.box(x0, TOP, x1, bottom)
    ix0, ix1 = x0 + GROUP_PAD, x1 - GROUP_PAD
    rule = canvas.box(ix0, TOP + GROUP_PAD, ix1, TOP + GROUP_PAD + RULE_BOX_H, face=theme.PANEL_BG)
    canvas.lines(ix0 + PAD, TOP + GROUP_PAD + 0.06, [
        ("Deterministic rule, no model", True),
        (f"≥ {thresholds['persistence'] * 100:.0f}% of days with the same sign", False),
        (f"mean |GEX| ≥ {theme.usd_b(thresholds['magnitude_bn'])}", False),
        (f"≤ {thresholds['max_sign_flips']} sign flips", False),
        (f"all {n_windows:,} windows", False)], container=rule)
    top = TOP + GROUP_PAD + RULE_BOX_H + 0.10
    box = canvas.box(ix0, top, ix1, bottom - GROUP_PAD, face=theme.PANEL_BG)
    y = canvas.lines(ix0 + PAD, top + 0.06, [
        (f"{', '.join(models)}, Batch API", True),
        (f"reasoning effort {theme.common.REASONING_EFFORT}, strict JSON", False)], container=box)
    y += 0.04
    for arm in arms:
        canvas.swatch(ix0 + PAD, y, theme.arm_color(arm["key"]))
        canvas.text(ix0 + PAD + 0.14, y, arm["label"], container=box)
        canvas.text(ix1 - PAD, y, f"{arm['rows']:,}", ha="right", container=box)
        y += ARM_LINE
    if other_requests:
        canvas.text(ix0 + PAD + 0.14, y, "pilot and repeat requests", color=theme.INK_SECONDARY, container=box)
        canvas.text(ix1 - PAD, y, f"{other_requests:,}", ha="right", color=theme.INK_SECONDARY, container=box)
        y += ARM_LINE
    canvas.text(ix0 + PAD, y + 0.04, f"Cost of all runs: USD {cost:,.2f}", bold=True, container=box)
    canvas.arrow((COLUMNS["windows"][1] + 0.03, middle), (x0 - 0.03, middle))


def draw_results(canvas: Canvas, results: Sequence[str], bottom: float) -> None:
    """The result tables the labels flow into, and where everything is stored."""
    left, right = COLUMNS["series"][0], COLUMNS["labels"][1]
    top = bottom + 0.26
    listing = wrap_items(results, "  ·  ", canvas.fig, width_in=right - left - 2 * PAD)
    height = 2 * PAD + LINE * (2 + listing.count("\n"))
    box = canvas.box(left, top, right, top + height)
    centre = sum(COLUMNS["labels"]) / 2
    canvas.arrow((centre, bottom + 0.03), (centre, top - 0.03))
    canvas.text(left + PAD, top + PAD, "Compared in the result tables", bold=True, container=box)
    canvas.text(left + PAD, top + PAD + LINE, listing, container=box)
    canvas.text(left, top + height + 0.10, theme.wrap_to_width(STORED_IN, canvas.fig, width_in=right - left), color=theme.MUTED)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = theme.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    report = inputs.yaml("report.yaml")
    windows = figdata.report_coverage(inputs, report, "windows")
    series = series_summary(figdata.report_coverage(inputs, report, "series"), windows)
    arms, other_requests = arm_summary(figdata.report_coverage(inputs, report, "detections"))
    models = sorted({m for a in arms for m in a["models"] if not m.startswith("o4-mini")})
    if not series or not models:
        inputs.fail("report.yaml lists no series, or no registered arm answered by a current model")
    thresholds = figdata.classifier_thresholds(inputs)
    cost = total_cost(inputs, report)
    results = written_results(report)
    n_windows = int(windows["rows"].sum())
    last_end = windows["last"].max().date().isoformat()

    # The label frame must hold the rule box plus one row per arm; when that needs more height than the
    # series column gives, the frame (and the figure) grow by the difference.
    series_bottom = TOP + len(series) * (SERIES_BOX_H + SERIES_GAP) - SERIES_GAP
    labels_bottom = (TOP + GROUP_PAD + RULE_BOX_H + 0.10 + 0.06 + 2 * LINE + 0.04
                     + (len(arms) + (1 if other_requests else 0)) * ARM_LINE + 0.04 + LINE + PAD + GROUP_PAD)
    extra_height = max(0.0, labels_bottom - series_bottom)
    height = HEIGHT_IN + extra_height
    fig = theme.new_figure(height)
    canvas = Canvas(fig, theme.FIG_WIDTH_IN, height)
    for (x0, x1), title in zip(COLUMNS.values(), ("Daily GEX series", "30-day windows", "Labels")):
        canvas.text((x0 + x1) / 2, 0.03, title, bold=True, ha="center", size=9)
    bottom = draw_series(canvas, series) + extra_height
    middle = (TOP + bottom) / 2
    draw_windows(canvas, n_windows, last_end, middle)
    draw_labels(canvas, thresholds, n_windows, models, arms, other_requests, cost, bottom, middle)
    draw_results(canvas, results, bottom)
    canvas.check()

    extra = {"series": {e["key"]: {"symbols": e["symbols"], "rows": e["rows"], "span": e["span"], "windows": e["windows"]}
                        for e in series},
             "windows": n_windows, "last_window_end": last_end, "arms": {a["key"]: a["rows"] for a in arms},
             "other_requests": other_requests, "cost_usd": cost, "results_written": results, "thresholds": thresholds}
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
