#!/usr/bin/env python3
"""Inputs and drawing helpers shared by fig07-fig12 (Electronics extension, gex-llm-patterns #261).

``figdata.py`` reads the pipeline files and ``theme.py`` owns the look; this module holds what the six
LLM-labelled figures (fig07-fig12) have in common:

* the command line (``theme.parse_args`` plus the ``--parquet-root`` spelling that ``05_report.py`` uses),
* year-indexed views of ``figdata.load_detection_by_year()`` (one frame per classifier series or per LLM arm),
* window-level joins of the ``detections`` and ``windows`` parquet copies, and
* a few drawing helpers (classifier lines with open LLM markers, span strips, rows of label cells).

Nothing here reads a database or invents values.  Every loader stops with a message that names the missing
file, column or arm; inputs that may legitimately be absent (an LLM arm that has not been run yet) are reported
back to the caller, which has to say so on the figure.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import figdata
import theme
from theme import common

logger = logging.getLogger("electronics.figures")

# Series keys of the registry, spelled once.
FULL, EX0DTE, OLD, JAN = "new_full", "new_ex0dte", "old_bs", "jan2026_phase4a"
PUBLISHED_ARM = "r1_o4mini"
SYMBOLS: Tuple[str, ...] = ("SPY", "QQQ", "IWM")
OK_PARSE = ("ok", "fallback")  # parse_status values that carry an answer
WINDOW_SERIES_ALIAS = {"intraday_late": common.INTRADAY_T0_KEY}  # detections of these series scored these windows


# --------------------------------------------------------------------------- command line and inputs
def parse_args(fig_id: str, doc: Optional[str], argv: Optional[Sequence[str]] = None, configure=None) -> argparse.Namespace:
    """``theme.parse_args`` that also accepts ``--parquet-root`` (the spelling of 05_report.py) for ``--tables-dir``.

    The parsed namespace always carries ``tables_dir`` (what ``figdata.Inputs`` takes) and ``parquet_root``.
    """

    def add_options(parser: argparse.ArgumentParser) -> None:
        try:
            parser.add_argument("--parquet-root", dest="tables_dir", type=Path, default=argparse.SUPPRESS,
                                help="same as --tables-dir (the spelling of 05_report.py)")
        except argparse.ArgumentError:  # theme.parse_args already offers --parquet-root
            pass
        if configure is not None:
            configure(parser)

    args = theme.parse_args(fig_id, doc, argv, add_options)
    if not hasattr(args, "tables_dir"):
        args.tables_dir = args.parquet_root
    args.parquet_root = args.tables_dir
    return args


def open_inputs(fig_id: str, args: argparse.Namespace) -> figdata.Inputs:
    return figdata.Inputs(fig_id, args.results_dir, args.tables_dir)


# --------------------------------------------------------------------------- small conversions
_FLAGS = {True: True, False: False, "True": True, "False": False, "true": True, "false": False}


def as_flag(values: pd.Series) -> pd.Series:
    """Nullable boolean from a CSV column that holds True/False and blanks (pandas reads that as ``object``)."""
    return values.map(_FLAGS).astype("boolean")


# --------------------------------------------------------------------------- detection_by_year.csv (figdata.load_detection_by_year)
def rule_by_year(inputs: figdata.Inputs, detection: pd.DataFrame, series_key: str, symbol: str) -> pd.DataFrame:
    """Classifier rows of one series and symbol indexed by year (empty when the series is absent).

    Columns as in ``figdata.load_detection_by_year``: ``n`` windows, ``clf_n_detect``, ``clf_rate`` (a fraction) with its
    Wilson interval ``clf_ci_lo``/``clf_ci_hi`` and ``n_indep_30d``.
    """
    try:
        rules = figdata.classifier_rates(detection)
    except ValueError as exc:
        inputs.fail(str(exc))
    sel = rules[(rules["series_key"] == series_key) & (rules["symbol"] == symbol)]
    return sel.set_index("year").sort_index()


def arm_by_year(inputs: figdata.Inputs, detection: pd.DataFrame, arm: str) -> pd.DataFrame:
    """Rows of one LLM arm indexed by year (empty when the arm has none); the largest model if several scored it.

    Columns as in ``figdata.load_detection_by_year``: ``n_parsed`` answers, ``llm_n_detect``, ``llm_rate`` (a fraction)
    with ``llm_ci_lo``/``llm_ci_hi``, ``n_compared``, ``agree_pct``, ``kappa``, ``clf_rate_matched`` and ``n_indep_30d``.
    """
    sel = figdata.llm_rates(detection)
    sel = sel[sel["arm"] == arm]
    if len(sel):
        sizes = sel.groupby("model")["n_parsed"].sum().sort_values(ascending=False, kind="stable")
        if len(sizes) > 1:
            logger.warning("arm %s was scored by several models %s; using %s", arm, list(sizes.index), sizes.index[0])
            sel = sel[sel["model"] == sizes.index[0]]
    try:
        return figdata.one_per_year(sel, f"arm {arm}")
    except ValueError as exc:
        inputs.fail(str(exc))


def on_years(frame: pd.DataFrame, years: Sequence[int], column: str, scale: float = 1.0) -> np.ndarray:
    """``column`` of a year-indexed frame aligned to ``years`` (NaN where the frame has no row), times ``scale``."""
    if frame.empty:
        return np.full(len(years), np.nan)
    return frame[column].reindex(list(years)).to_numpy(dtype=float) * scale


def percent(frame: pd.DataFrame, years: Sequence[int], column: str) -> np.ndarray:
    """A fraction column of a year-indexed frame as percent, aligned to ``years``."""
    return on_years(frame, years, column, 100.0)


# --------------------------------------------------------------------------- window level (detections x windows parquet)
ANSWER_COLUMNS = ("arm", "series_key", "symbol", "window_end", "model", "prompt_version", "regime_detected",
                  "avg_magnitude_billions", "sign_flips", "persistence_pct", "parse_status")
CLASSIFIER_COLUMNS = ("series_key", "symbol", "window_end", "clf_should_detect", "clf_avg_magnitude",
                      "clf_persistence_pct", "clf_sign_flips")


def registered_llm_arms() -> List[str]:
    """Arms whose answers the figures may use: the published o4-mini backfill and every registered gpt-6-luna arm."""
    return [PUBLISHED_ARM, *[key for key, arm in common.ARMS.items() if arm.llm]]


def load_answer_pairs(inputs: figdata.Inputs, arms: Sequence[str]) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Parsed answers of ``arms`` joined to the deterministic metrics of the window each one scored.

    Returns the pairs and a count dictionary (answers read, parsed, matched to a window).  Answers of the
    ``intraday_late`` series are joined to the composite ``intraday_t0`` windows, as 05_report.py does.
    """
    det = inputs.table("detections", ANSWER_COLUMNS, arms=arms)
    counts = {"answers": int(len(det))}
    det = det[det["parse_status"].isin(OK_PARSE) & det["regime_detected"].notna()]
    counts["parsed"] = int(len(det))
    det = det.assign(window_series_key=det["series_key"].map(lambda key: WINDOW_SERIES_ALIAS.get(key, key)))
    win = inputs.table("windows", CLASSIFIER_COLUMNS, series_keys=sorted(set(det["window_series_key"])),
                       symbols=sorted(set(det["symbol"])))
    pairs = det.merge(win.rename(columns={"series_key": "window_series_key"}),
                      on=["window_series_key", "symbol", "window_end"], how="inner", validate="many_to_one")
    counts["matched"] = int(len(pairs))
    if counts["matched"] < counts["parsed"]:
        logger.info("%s: %d parsed answers have no stored window and are left out", inputs.fig_id, counts["parsed"] - counts["matched"])
    if pairs.empty:
        inputs.fail("no parsed LLM answer matches a stored window; run 02_build_windows.py for the scored series")
    unknown = sorted({m for m in pairs["model"].unique() if model_group(m) is None})
    if unknown:
        inputs.fail(f"unexpected model(s) {unknown} among the registered arms (expected {common.R1_MODEL} or {common.MODEL})")
    return pairs.assign(regime_detected=pairs["regime_detected"].astype(bool), clf_should_detect=pairs["clf_should_detect"].astype(bool),
                        group=pairs["model"].map(model_group)), counts


def model_group(model: str) -> Optional[str]:
    """'o4-mini' for the published model, 'luna' for gpt-6-luna, None for anything else."""
    if str(model).startswith("o4-mini"):
        return "o4-mini"
    if str(model).startswith(common.MODEL):
        return "luna"
    return None


# --------------------------------------------------------------------------- drawing: rates
def hollow_style(color: str, marker: str, size: float = 4.2) -> Dict[str, Any]:
    """Marker style of an LLM rate: an open marker in the series colour (the classifier is the filled line)."""
    return dict(marker=marker, markersize=size, markerfacecolor=theme.SURFACE, markeredgecolor=color, markeredgewidth=0.9,
                linestyle="none", color=color, clip_on=False, zorder=4)


def draw_rate(ax, years: Sequence[int], rule: np.ndarray, llm: Optional[np.ndarray], color: str, marker: str,
              llm_offset: float = 0.0, llm_err: Optional[np.ndarray] = None, marker_size: float = 3.2) -> None:
    """The classifier rate as a filled line and the LLM rate as open markers (optionally with whiskers) in one series colour."""
    x = np.asarray(years, dtype=float)
    ax.plot(x, rule, color=color, marker=marker, markersize=marker_size, linewidth=1.1, markeredgecolor=theme.SURFACE,
            markeredgewidth=0.5, clip_on=False, zorder=3)
    if llm is not None and (~np.isnan(llm)).any():
        good = ~np.isnan(llm)
        if llm_err is not None:
            ax.errorbar(x[good] + llm_offset, llm[good], yerr=llm_err[:, good], fmt="none", ecolor=color, elinewidth=0.6,
                        capsize=1.2, capthick=0.6, zorder=3.5, clip_on=False)
        ax.plot(x[good] + llm_offset, llm[good], **hollow_style(color, marker, marker_size + 1.0))


def line_handle(color: str, marker: str, label: str) -> Line2D:
    return Line2D([0], [0], color=color, marker=marker, markersize=3.6, linewidth=1.1, markeredgecolor=theme.SURFACE,
                  markeredgewidth=0.5, label=label)


def hollow_handle(color: str, marker: str, label: str) -> Line2D:
    return Line2D([0], [0], label=label, **{**hollow_style(color, marker, 4.4), "clip_on": True})


def patch_handle(color: str, label: str, edge: Optional[str] = None) -> Patch:
    return Patch(facecolor=color, edgecolor=edge or "none", linewidth=0.6 if edge else 0.0, label=label)


# --------------------------------------------------------------------------- drawing: strips of spans and label cells
def span_strip(ax, spans: Sequence[Tuple[float, float, str]], xlim: Tuple[float, float]) -> None:
    """Thin label strip above a panel: grey spans with centred 8 pt captions (events, periods)."""
    ax.set_xlim(*xlim)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for x0, x1, label in spans:
        left, right = max(x0, xlim[0]), min(x1, xlim[1])
        ax.axvspan(left, right, ymin=0.08, ymax=0.92, color=theme.PANEL_BG, linewidth=0, zorder=0)
        ax.text((left + right) / 2, 0.5, label, ha="center", va="center", fontsize=8, color=theme.INK_SECONDARY)


def label_grid(ax, items: Sequence[tuple], colors: Sequence[str], n_cells: int, row_gap: float = 0.16,
               header_gap: float = 0.7) -> float:
    """Rows of coloured cells, one cell per x position, with group headers; returns the height used.

    ``items`` are ``("header", text)`` or ``("row", tick label, codes, height)``; ``codes`` has ``n_cells`` entries,
    0 or NaN is a blank cell and k >= 1 is ``colors[k - 1]``.  Cell i spans x in [i - 0.5, i + 0.5].  Rows run
    downwards (the y axis is inverted) and carry their label as a y tick; headers are left-aligned bold text.
    """
    cmap = ListedColormap([theme.SURFACE, *colors])
    norm = BoundaryNorm(np.arange(-0.5, len(colors) + 1.5), cmap.N)
    x_edges = np.arange(-0.5, n_cells + 0.5)
    y, ticks, labels, started = 0.0, [], [], False
    for item in items:
        if item[0] == "header":
            y += header_gap if started else 0.0
            ax.text(-0.5, y, item[1], ha="left", va="bottom", fontsize=8, fontweight="bold", color=theme.INK, zorder=6,
                    bbox=dict(facecolor=theme.SURFACE, edgecolor="none", pad=0.6))
            y += 0.16
            started = True
            continue
        _, label, codes, height = item
        grid = np.nan_to_num(np.asarray(codes, dtype=float), nan=0.0)[None, :]
        ax.pcolormesh(x_edges, [y, y + height], grid, cmap=cmap, norm=norm, linewidth=0, antialiased=False, rasterized=True)
        ticks.append(y + height / 2)
        labels.append(label)
        y += height + row_gap
    ax.set_ylim(y - row_gap, -0.55)
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels)
    ax.tick_params(axis="y", length=0)
    for side in ("left", "top", "right"):
        ax.spines[side].set_visible(False)
    return y


def month_ticks(ax, dates: Sequence[pd.Timestamp]) -> None:
    """Ticks at the first window end of every calendar month on an axis whose x is the position in ``dates``."""
    first: Dict[Tuple[int, int], int] = {}
    for i, d in enumerate(dates):
        first.setdefault((d.year, d.month), i)
    ax.set_xticks(list(first.values()))
    ax.set_xticklabels([pd.Timestamp(year=yy, month=mm, day=1).strftime("%b") for yy, mm in first])


def week_ticks(ax, dates: Sequence[pd.Timestamp], every_days: int = 14) -> None:
    """Ticks at the first window end of every ``every_days`` calendar days, labelled with that date (``Jul 27``)."""
    first = dates[0]
    positions: List[int] = []
    last_slot = -1
    for i, d in enumerate(dates):
        slot = (d - first).days // every_days
        if slot != last_slot:
            positions.append(i)
            last_slot = slot
    ax.set_xticks(positions)
    ax.set_xticklabels([f"{dates[i].strftime('%b')} {dates[i].day}" for i in positions])
