#!/usr/bin/env python3
"""Light MDPI figure theme and output helpers for the Electronics extension (gex-llm-patterns #261).

Every figure script in this folder imports this module.  It owns

* the page geometry (figures are authored at the printed text width of the MDPI class,
  6.14 in, so 8-9 pt text is true print size),
* the colour tokens (one fixed colour, marker and label per GEX series and per model arm, so a series keeps its
  identity in every figure; they cover every series and arm of the contract in ``common.py``, ``registry_gaps()``
  lists what is missing when the contract grows),
* the PNG (300 dpi, RGB) + PDF writer with a typography lint (typographic minus, en-dash number and year
  ranges, 8-9 pt text only), and
* the provenance manifest written next to every figure (``<fig_id>.json``: source files with sha256 and
  row counts, what ``report.yaml`` of 05_report.py says about them, the code that drew the figure with sha256 and
  git state, git sha and dirty flags, command line, timestamp, library versions).

Nothing here reads data.  Data access lives in ``figdata.py`` and never falls back to synthetic
values: a missing input stops the figure with a clear message.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import platform
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, to_rgb  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.text import Text  # noqa: E402
from PIL import Image, PngImagePlugin  # noqa: E402

# --------------------------------------------------------------------------- paths and the pipeline contract
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[4]  # docs/papers/electronics/figures/scripts -> repository root
PIPELINE_DIR = REPO_ROOT / "scripts" / "validation" / "electronics"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

import common  # noqa: E402  (the shared contract: registries, paths, git sha, logging)

if Path(common.__file__).resolve().parent != PIPELINE_DIR.resolve():  # a different 'common' module won the import
    raise ImportError(f"expected the pipeline contract at {PIPELINE_DIR / 'common.py'}, imported {common.__file__}")

logger = logging.getLogger("electronics.figures")

RESULTS_DIR: Path = common.RESULTS_DIR  # docs/papers/electronics/results (CSV/YAML written by 05_report.py)
TABLES_DIR: Path = common.PARQUET_ROOT  # data/backups/gex_llm/tables/{series,windows,detections,runs}/*.parquet
OUTPUT_DIR: Path = common.FIGURE_OUTPUT_DIR  # docs/papers/electronics/figures/output

# --------------------------------------------------------------------------- geometry and type
TEXT_WIDTH_IN = 443.86319 / 72.27  # \textwidth of the MDPI class on A4 (156 mm); measured from the compiled skeleton
FIG_WIDTH_IN = 6.14
DPI = 300
FONT_MIN_PT, FONT_MAX_PT = 8.0, 9.0  # every visible text object must sit in this range (lint)
FONT_SANS = ["Nimbus Sans", "Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"]

MINUS = "−"  # typographic minus; MDPI production asked for it inside figure bitmaps
ENDASH = "–"  # year ranges are written 2008–2019

# --------------------------------------------------------------------------- colour tokens
# Light surface.  The six first hues are Okabe-Ito; violet (the November-2025 baselines) and dark vermilion (the scaled
# series) were added when the contract grew to eleven series.  Validated with the dataviz palette validator on the
# white surface (python validate_palette.py "#0072B2,#CC79A7,#56B4E9,#D55E00,#009E73,#E69F00,#682F9C,#8C2F1F"
# --mode light --surface "#FFFFFF"): lightness band and chroma floor pass for all eight hues; compared neighbour by
# neighbour the worst pair is dE 9.6 (CVD) and 20.0 (normal vision); with every pair compared the normal-vision floor
# passes (worst pair orange / vermilion, dE 15.6) and the worst colour-vision-deficiency pair (bluish green / reddish
# purple, dE 7.6) is in the floor band; sky blue and orange sit below 3:1 contrast on white.  Both warnings are covered
# by secondary encodings that every figure uses: a fixed marker per series, direct labels or a legend, and the numbers
# themselves in results/*.csv.
INK = "#1A1A1A"  # primary text and the deterministic classifier
INK_SECONDARY = "#4D4D4D"
MUTED = "#767676"  # axis text of secondary importance, footnotes
GRID = "#E3E3E3"
BASELINE = "#B8B8B8"
SURFACE = "#FFFFFF"
PANEL_BG = "#F4F4F4"  # shaded spans (post-publication period, partial year)

SERIES_COLORS: Dict[str, str] = {
    "jan2026_phase4a": "#0072B2",  # the exact published inputs (blue)
    "call_only": "#CC79A7",  # diagnostic: call leg only, the put-less January table (reddish purple)
    "old_bs": "#56B4E9",  # archive of the pre-rebuild daily table (sky blue)
    "new_full": "#D55E00",  # rebuilt table, stored gamma, 0DTE included: the primary corrected series (vermilion)
    "new_ex0dte": "#009E73",  # raw chains, expiration > trading date (bluish green)
    "intraday": "#E69F00",  # final-rush intraday snapshot at T+0 (orange)
    "new_full_scaled": "#8C2F1F",  # new_full of QQQ and IWM times one fixed factor: the dark shade of its parent (dark vermilion)
    "p3_2024": "#682F9C",  # the November-2025 baselines (Phase 3 = SPY 2024, Phase 4 = SPY 2020) are one family (violet) ...
    "p3_2024_dated": "#682F9C",  # ... and a series keeps its colour when only the day labels differ (ISO dates instead of Day T)
    "p4_2020": "#682F9C",
    "p4_2020_dated": "#682F9C",
}
SERIES_ALIASES: Dict[str, str] = {"intraday_late": "intraday", "intraday_t0": "intraday"}
SERIES_MARKERS: Dict[str, str] = {
    "jan2026_phase4a": "o", "call_only": "P", "old_bs": "s", "new_full": "^", "new_ex0dte": "D", "intraday": "v",
    "new_full_scaled": "*", "p3_2024": "p", "p3_2024_dated": "p", "p4_2020": "h", "p4_2020_dated": "h",
}  # fmt: skip
SERIES_LABELS: Dict[str, str] = {
    "jan2026_phase4a": "Published inputs",
    "call_only": "Call leg only",
    "old_bs": "Pre-rebuild (BS)",
    "new_full": "Rebuilt, 0DTE incl.",
    "new_ex0dte": "Rebuilt, ex-0DTE",
    "intraday": "Intraday T+0",
    "new_full_scaled": "Rebuilt, scaled",
    "p3_2024": "2024 baseline, Day-T labels",
    "p3_2024_dated": "2024 baseline, dated labels",
    "p4_2020": "2020 baseline, Day-T labels",
    "p4_2020_dated": "2020 baseline, dated labels",
}
# SERIES_ORDER: the six daily GEX series of the main analysis, in the order of the colour legend (fig01-fig03 are laid out
# for exactly these).  SERIES_ORDER_ALL: every registered series in the order of the paper's Table 1 (common.SERIES), the
# scaled and the November-2025 baseline series last, for figures that have room for them.
SERIES_ORDER: Tuple[str, ...] = ("jan2026_phase4a", "call_only", "old_bs", "new_full", "new_ex0dte", "intraday")
SERIES_ORDER_ALL: Tuple[str, ...] = (*SERIES_ORDER, "new_full_scaled", "p3_2024", "p3_2024_dated", "p4_2020", "p4_2020_dated")

PUBLISHED_COLOR = "#7A7A7A"  # the published o4-mini labels (grey: a result, not a data convention)
LUNA_COLOR = INK  # gpt-6-luna when arms of several series are pooled
POSITIVE = "#2166AC"  # positive sign / agreement / detected
NEGATIVE = "#B2182B"  # negative sign / disagreement / rejected
THRESHOLD = "#555555"  # dashed reference lines (classifier thresholds)

ARM_LABELS: Dict[str, str] = {
    "r1_o4mini": "o4-mini, published inputs",
    "r1_p3_o4mini": "o4-mini, 2024 baseline, dated",
    "r1_p4_o4mini": "o4-mini, 2020 baseline, dated",
    "bridge_jan": "luna, published inputs",
    "bridge_old": "luna, pre-rebuild (BS)",
    "full_spy": "luna, rebuilt, SPY",
    "ex0dte_spy": "luna, ex-0DTE, SPY",
    "p34_obf_2024": "luna, 2024 baseline, Day-T labels",
    "p34_dated_2024": "luna, 2024 baseline, dated",
    "p34_obf_2020": "luna, 2020 baseline, Day-T labels",
    "p34_dated_2020": "luna, 2020 baseline, dated",
    "full_qqq": "luna, rebuilt, QQQ",
    "ex0dte_qqq": "luna, ex-0DTE, QQQ",
    "full_iwm": "luna, rebuilt, IWM",
    "ex0dte_iwm": "luna, ex-0DTE, IWM",
    "full_qqq_scaled": "luna, rebuilt, QQQ, scaled",
    "full_iwm_scaled": "luna, rebuilt, IWM, scaled",
    "intraday_spy": "luna, intraday T+0, SPY",
}

SEQUENTIAL_BLUE = ["#F3F7FC", "#CDE2FB", "#86B6EF", "#3987E5", "#1C5CAB", "#0D366B"]  # one hue, light to dark


def series_key(key: str) -> str:
    """Resolve a registry series key (intraday_late, intraday_t0) to its colour-token key."""
    return SERIES_ALIASES.get(key, key)


def _token(table: Mapping[str, Any], key: str, what: str) -> Any:
    try:
        return table[series_key(key)]
    except KeyError:
        raise KeyError(f"series {key!r} has no {what} token in theme.py (it has {sorted(table)}); add it to the {what} table next to "
                       f"the others") from None


def series_color(key: str) -> str:
    return _token(SERIES_COLORS, key, "colour")


def series_label(key: str) -> str:
    return _token(SERIES_LABELS, key, "label")


def series_marker(key: str) -> str:
    return _token(SERIES_MARKERS, key, "marker")


ALL_SUFFIX = "_all"  # 05_report.py labels a published arm with the answers recovered in 2026 added '<arm>_all'


def registered_arm(arm: str) -> Optional["common.Arm"]:
    """Registry entry (common.ARMS) behind an arm label of 05_report.py; None for any other name (pilots, strangers).

    A test-retest repeat ``<arm>#rep<k>`` (common.REPEAT_MARK, split with common.base_arm) and the variant
    ``<arm>_all`` resolve to their registered arm.
    """
    name = common.base_arm(str(arm))
    found = common.ARMS.get(name)
    if found is None and name.endswith(ALL_SUFFIX):
        found = common.ARMS.get(name[: -len(ALL_SUFFIX)])
    return found


def base_arm(arm: str) -> str:
    """The registered arm behind ``arm`` (see :func:`registered_arm`); any other name only loses a repeat mark."""
    found = registered_arm(arm)
    return found.key if found is not None else common.base_arm(str(arm))


def arm_color(arm: str) -> str:
    """Colour of an LLM arm: the colour of the series it reads; the published o4-mini labels (arms with llm=False) are grey.

    Variants of a registered arm (``r1_o4mini_all``, repeats) keep its colour; an unknown arm is a KeyError.
    """
    found = registered_arm(arm)
    if found is None:
        raise KeyError(f"arm {arm!r} is not a registered arm (common.ARMS) nor a repeat '<arm>{common.REPEAT_MARK}<k>' or "
                       f"'<arm>{ALL_SUFFIX}' variant of one")
    return series_color(found.series_key) if found.llm else PUBLISHED_COLOR


def arm_label(arm: str) -> str:
    """Legend label of an arm; variants add what makes them different, unknown names are returned as they are."""
    if arm in ARM_LABELS:
        return ARM_LABELS[arm]
    found = registered_arm(arm)
    if found is None or found.key not in ARM_LABELS:
        return arm
    label = ARM_LABELS[found.key]
    if common.REPEAT_MARK in arm:
        index = arm.split(common.REPEAT_MARK, 1)[1]
        return f"{label} (repeat{'' if index in ('', '1') else ' ' + index})"
    return f"{label}, incl. recovered" if arm.endswith(ALL_SUFFIX) else label


def registry_gaps() -> Dict[str, List[str]]:
    """Registered series and arms (common.SERIES, common.ARMS) that the tokens above do not cover, by missing token.

    Empty lists mean every figure may ask for the colour, marker and label of any series or arm of the contract.
    """
    gaps: Dict[str, List[str]] = {"series_color": [], "series_marker": [], "series_label": [], "arm_color": [], "arm_label": []}
    for key in common.SERIES:
        for name, table in (("series_color", SERIES_COLORS), ("series_marker", SERIES_MARKERS), ("series_label", SERIES_LABELS)):
            if series_key(key) not in table:
                gaps[name].append(key)
    for key, arm in common.ARMS.items():
        if arm.llm and series_key(arm.series_key) not in SERIES_COLORS:
            gaps["arm_color"].append(key)
        if key not in ARM_LABELS:
            gaps["arm_label"].append(key)
    return gaps


_UNCOVERED = {name: keys for name, keys in registry_gaps().items() if keys}
if _UNCOVERED:  # a series or arm was added to common.py without tokens: say so at import, the first figure that needs one fails
    logger.warning("theme.py has no tokens for %s", "; ".join(f"{name}: {keys}" for name, keys in _UNCOVERED.items()))


def sequential_cmap() -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list("sequential_blue", SEQUENTIAL_BLUE)


def relative_luminance(color: Any) -> float:
    """WCAG relative luminance (0 black, 1 white) of any matplotlib colour."""
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink_on_fill(fill: Any) -> str:
    """Text colour for a label set inside a coloured cell: the surface colour or the ink, whichever contrasts more."""
    cell = relative_luminance(fill) + 0.05
    on_light = cell / (relative_luminance(INK) + 0.05)
    on_dark = (relative_luminance(SURFACE) + 0.05) / cell
    return INK if on_light >= on_dark else SURFACE


# --------------------------------------------------------------------------- matplotlib style
def apply_style() -> None:
    """Install the paper style (idempotent)."""
    plt.rcdefaults()
    mpl.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": DPI,
            "figure.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "font.family": "sans-serif",
            "font.sans-serif": FONT_SANS,
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.titleweight": "bold",
            "axes.titlepad": 5,
            "axes.labelsize": 8,
            "axes.labelpad": 2.5,
            "axes.labelcolor": INK,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.titlesize": 9,
            "text.color": INK,
            "axes.unicode_minus": True,
            "axes.linewidth": 0.6,
            "axes.edgecolor": INK_SECONDARY,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": INK_SECONDARY,
            "ytick.color": INK_SECONDARY,
            "xtick.labelcolor": INK,
            "ytick.labelcolor": INK,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "xtick.major.pad": 2,
            "ytick.major.pad": 2,
            "lines.linewidth": 1.2,
            "lines.markersize": 4,
            "patch.linewidth": 0.0,
            "grid.color": GRID,
            "grid.linewidth": 0.5,
            "grid.linestyle": "-",
            "legend.frameon": False,
            "legend.handlelength": 1.5,
            "legend.handletextpad": 0.5,
            "legend.columnspacing": 1.3,
            "legend.borderaxespad": 0.2,
            "figure.constrained_layout.use": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "mathtext.default": "regular",
        }
    )


def new_figure(height_in: float, **kwargs: Any) -> Figure:
    """Constrained-layout figure of the printed text width; ``kwargs`` go to ``plt.figure``."""
    apply_style()
    return plt.figure(figsize=(FIG_WIDTH_IN, height_in), layout="constrained", **kwargs)


# --------------------------------------------------------------------------- typography helpers
_HYPHEN_BEFORE_DIGIT = re.compile(r"(?<![\w−])-(?=\d)")


def um(text: str) -> str:
    """Typographic minus for literal labels: ``'Day T-29'`` -> ``'Day T−29'``; model names keep their hyphen."""
    text = re.sub(r"(?<=\bT)-(?=\d)", MINUS, text)
    return _HYPHEN_BEFORE_DIGIT.sub(MINUS, text)


def signed(value: float, digits: int = 1) -> str:
    """'+12.6' / '−4.5' (explicit sign, typographic minus); a value that rounds to zero carries no sign ('0.0')."""
    text = f"{value:+.{digits}f}"
    if float(text) == 0:
        return text[1:]
    return text.replace("-", MINUS)


def usd_b(value: float, digits: Optional[int] = None) -> str:
    """'\\$5B' / '−\\$12.5B': the dollar sign is escaped for matplotlib's mathtext parser; a negative value carries
    its typographic minus in front of the currency sign."""
    body = f"{abs(value):g}" if digits is None else f"{abs(value):.{digits}f}"
    sign = MINUS if value < 0 and float(body) != 0 else ""
    return f"{sign}\\${body}B"


def year_label(year: int, partial_year: Optional[int] = None) -> str:
    return f"{year}*" if partial_year is not None and year == partial_year else str(year)


PARTIAL_YEAR = common.WINDOW_END_CAP.year  # windows end on or before 2026-10-09, so 2026 is a partial year
PARTIAL_YEAR_NOTE = f"* {PARTIAL_YEAR}: windows ending up to {common.WINDOW_END_CAP.isoformat()}."


# Hyphens that are part of a name rather than a minus sign or a range.  "Day T-29" is deliberately not listed: that
# hyphen is a minus and is typed with um().  A listed name is replaced by a letter before the text is searched, so the
# characters around it keep their context ("o4-mini-2025-04-16" -> "X-2025-04-16", an ISO date after a name).
_HYPHEN_WHITELIST = ("gpt-6", "o4-mini", "ex-0DTE", "non-")
_NAME_PLACEHOLDER = "X"
_ASCII_MINUS = re.compile(r"(?<![\d\w])-\d|(?<=\bT)-\d")  # -5, (-5), T-29 (a hyphen where U+2212 belongs)
_YEAR_RANGE = re.compile(r"\b(?:19|20)\d\d-(?:19|20)\d\d\b")  # 2008-2019
_NUMERIC_RANGE = re.compile(r"\d+(?:\.\d+)?(?:%|pp|bn|B)?-\d+(?:\.\d+)?")  # 0-100%, 5-7B, 2-4pp, 10%-20%, 21-30 days: an en dash belongs there
_ISO_DATE = re.compile(r"\b\d{4}-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?\b")  # 2026-10-09 and 2026-10 are dates and keep their hyphens


def ascii_ranges(text: str) -> List[str]:
    """Numeric ranges typed with a hyphen (``'0-100'``); ISO dates are left alone."""
    iso = [m.span() for m in _ISO_DATE.finditer(text)]
    return [m.group(0) for m in _NUMERIC_RANGE.finditer(text)
            if not any(a <= m.start() and m.end() <= b for a, b in iso)]


def lint_figure(fig: Figure) -> List[str]:
    """Problems MDPI copy-editing flagged on the JRFM figures, plus the 8-9 pt rule; empty list = clean."""
    fig.canvas.draw()
    problems: List[str] = []
    for obj in fig.findobj(Text):
        text = obj.get_text()
        if not text.strip() or not obj.get_visible():
            continue
        scrubbed = text
        for token in _HYPHEN_WHITELIST:
            scrubbed = scrubbed.replace(token, _NAME_PLACEHOLDER)
        if _ASCII_MINUS.search(scrubbed) or _YEAR_RANGE.search(text) or ascii_ranges(scrubbed):
            problems.append(f"hyphen where a minus sign or en dash belongs: {text!r}")
        size = obj.get_fontsize()
        if not FONT_MIN_PT - 0.01 <= size <= FONT_MAX_PT + 0.01:
            problems.append(f"font size {size:g} pt outside {FONT_MIN_PT:g}-{FONT_MAX_PT:g} pt: {text!r}")
    return problems


# --------------------------------------------------------------------------- axes helpers
def panel_title(ax, letter: str, text: str) -> None:
    ax.set_title(f"({letter}) {text}", loc="left", fontsize=9, fontweight="bold")


def style_grid(ax, axis: str = "y") -> None:
    ax.grid(True, axis=axis, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)


def threshold_line(ax, value: float, label: Optional[str] = None, orientation: str = "h", label_x: float = 0.995,
                   va: str = "bottom", label_y: float = 0.995, ha: str = "left") -> None:
    """Dashed reference line for a classifier threshold, optionally labelled.

    A horizontal line (``orientation='h'``) is labelled at its right end (``label_x`` in axes fraction, ``va`` above
    or below the line); a vertical line (``'v'``) at the top of the axes (``label_y`` in axes fraction), on the ``ha``
    side of the line.
    """
    if orientation == "h":
        ax.axhline(value, color=THRESHOLD, linewidth=0.8, linestyle=(0, (4, 2)), zorder=1.5)
        if label:
            ax.text(label_x, value, label, transform=ax.get_yaxis_transform(), ha="right", va=va, fontsize=8,
                    color=INK_SECONDARY)
    elif orientation == "v":
        ax.axvline(value, color=THRESHOLD, linewidth=0.8, linestyle=(0, (4, 2)), zorder=1.5)
        if label:
            ax.annotate(label, xy=(value, label_y), xycoords=ax.get_xaxis_transform(),
                        xytext=(3 if ha == "left" else -3, 0), textcoords="offset points", ha=ha, va="top", fontsize=8,
                        color=INK_SECONDARY)
    else:
        raise ValueError(f"orientation must be 'h' or 'v', not {orientation!r}")


def percent_axis(ax, axis: str = "y", ticks: Sequence[int] = (0, 25, 50, 75, 100), headroom: float = 6.0) -> None:
    """0-100 percent axis with a little headroom so 100% bars and their whiskers are not cut by the frame."""
    if axis == "y":
        ax.set_ylim(0, 100 + headroom)
        ax.set_yticks(list(ticks))
    else:
        ax.set_xlim(0, 100 + headroom)
        ax.set_xticks(list(ticks))


def year_axis(ax, years: Sequence[int], step: int = 1, partial_year: Optional[int] = PARTIAL_YEAR, pad: float = 0.6) -> None:
    years = sorted(set(int(y) for y in years))
    ax.set_xlim(years[0] - pad, years[-1] + pad)
    shown = [y for y in years if (y - years[0]) % step == 0]
    ax.set_xticks(shown)
    ax.set_xticklabels([year_label(y, partial_year) for y in shown])


def shade_span(ax, x0: float, x1: float, label: Optional[str] = None, label_y: float = 1.0) -> None:
    """Light grey background span (post-publication period); the label sits above the axes frame."""
    ax.axvspan(x0, x1, color=PANEL_BG, zorder=0, linewidth=0)
    if label:
        ax.text((x0 + x1) / 2, label_y, label, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=8, color=MUTED)


def wrap_to_width(text: str, fig: Figure, width_in: float = FIG_WIDTH_IN - 0.15, fontsize: float = 8.0) -> str:
    """Greedy word wrap measured with the renderer (footnotes are laid out by hand)."""
    renderer = fig.canvas.get_renderer()
    prop = mpl.font_manager.FontProperties(size=fontsize)
    limit = width_in * fig.dpi
    lines: List[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            width, _, _ = renderer.get_text_width_height_descent(trial, prop, ismath=False)
            if width > limit and current:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    return "\n".join(lines)


def text_collisions(fig: Figure, texts: Sequence[Text], pad_px: float = 1.0) -> List[str]:
    """Pairs of visible texts whose boxes overlap (drawn once to measure); empty list = no collision."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    shown = [(t, t.get_window_extent(renderer)) for t in texts if t.get_visible() and t.get_text().strip()]
    problems: List[str] = []
    for i, (first, a) in enumerate(shown):
        for second, b in shown[i + 1:]:
            if a.x0 < b.x1 - pad_px and b.x0 < a.x1 - pad_px and a.y0 < b.y1 - pad_px and b.y0 < a.y1 - pad_px:
                problems.append(f"text overlap: {first.get_text()!r} and {second.get_text()!r}")
    return problems


def text_outside(fig: Figure, texts: Sequence[Text], container: Any, pad_px: float = 1.0) -> List[str]:
    """Texts that stick out of ``container`` (a patch or an Axes; its window extent is the limit)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    limit = container.get_window_extent(renderer)
    problems: List[str] = []
    for text in texts:
        if not text.get_visible() or not text.get_text().strip():
            continue
        box = text.get_window_extent(renderer)
        if box.x0 < limit.x0 - pad_px or box.x1 > limit.x1 + pad_px or box.y0 < limit.y0 - pad_px or box.y1 > limit.y1 + pad_px:
            problems.append(f"text outside its box: {text.get_text()!r}")
    return problems


def footnote(fig: Figure, text: str) -> None:
    """Muted note under the figure, wrapped to the page width and included in the constrained layout."""
    fig.supxlabel(wrap_to_width(text, fig), x=0.004, ha="left", fontsize=8, color=MUTED, fontweight="normal")


def row_major(handles: Sequence[Any], labels: Sequence[str], ncol: int) -> Tuple[List[Any], List[str]]:
    """Reorder legend entries so that matplotlib's column-by-column fill reads row by row in the given order.

    ``fig.legend(*theme.row_major(handles, labels, ncol), ncol=ncol)`` then shows entry 1, 2, 3 on the first row,
    4, 5, 6 on the second, which is the left-to-right order of the bars or lines they stand for.
    """
    if len(handles) != len(labels):
        raise ValueError(f"{len(handles)} handles for {len(labels)} labels")
    n, rows = len(handles), -(-len(handles) // max(ncol, 1))
    order = [r * ncol + c for c in range(ncol) for r in range(rows) if r * ncol + c < n]
    return [handles[i] for i in order], [labels[i] for i in order]


# --------------------------------------------------------------------------- command line
def parse_args(fig_id: str, doc: Optional[str], argv: Optional[Sequence[str]] = None,
               configure: Optional[Callable[[argparse.ArgumentParser], None]] = None) -> argparse.Namespace:
    """Common CLI of every figure script; ``doc`` is the module docstring (first paragraph = summary)."""
    summary, _, rest = (doc or fig_id).strip().partition("\n\n")
    parser = argparse.ArgumentParser(prog=f"{fig_id}.py", description=summary, epilog=rest,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR,
                        help="folder with the CSV/YAML written by 05_report.py (default: %(default)s)")
    parser.add_argument("--tables-dir", type=Path, default=TABLES_DIR,
                        help="folder with the parquet copies series/ windows/ detections/ (default: %(default)s)")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="where to write <fig>.png/.pdf/.json (default: %(default)s)")
    parser.add_argument("--no-pdf", action="store_true", help="write the PNG and the manifest only")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    if configure is not None:
        configure(parser)
    args = parser.parse_args(argv)
    common.setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    for noisy in ("fontTools", "matplotlib", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return args


# --------------------------------------------------------------------------- output and provenance
def display_path(path: Path) -> str:
    """Repo-relative path when the file lives in the repository, absolute otherwise."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def save_figure(fig: Figure, fig_id: str, output_dir: Path, pdf: bool = True,
                metadata: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Lint, then write ``<fig_id>.png`` (RGB, 300 dpi, text chunks) and ``<fig_id>.pdf`` to ``output_dir``."""
    width, height = fig.get_size_inches()
    if abs(width - FIG_WIDTH_IN) > 0.005:
        raise ValueError(f"{fig_id}: figure width {width:.3f} in, expected {FIG_WIDTH_IN} in")
    problems = lint_figure(fig)
    if problems:
        raise ValueError(f"{fig_id}: typography lint failed:\n  " + "\n  ".join(problems))
    output_dir.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI)
    buffer.seek(0)
    info = PngImagePlugin.PngInfo()
    for key, value in {"Title": fig_id, "Software": f"matplotlib {mpl.__version__}", **(metadata or {})}.items():
        info.add_text(key, str(value))
    outputs = {"png": output_dir / f"{fig_id}.png"}
    Image.open(buffer).convert("RGB").save(outputs["png"], "PNG", dpi=(DPI, DPI), pnginfo=info)
    if pdf:
        outputs["pdf"] = output_dir / f"{fig_id}.pdf"
        fig.savefig(outputs["pdf"], format="pdf", metadata={"Title": fig_id, "Creator": "gex-llm-patterns figures", "CreationDate": None})
    plt.close(fig)
    return outputs


MANIFEST_PACKAGES = ("numpy", "pandas", "pyarrow", "PyYAML", "Pillow")  # what the data and the PNG pass through


def to_native(obj: Any) -> Any:
    """JSON-ready copy of nested values: numpy scalars unwrapped, NaN and inf -> null, dates and paths as text."""
    if isinstance(obj, Mapping):
        return {str(k): to_native(v) for k, v in obj.items()}
    if isinstance(obj, (set, frozenset)):
        return [to_native(v) for v in sorted(obj, key=str)]
    if isinstance(obj, (list, tuple)):
        return [to_native(v) for v in obj]
    if hasattr(obj, "tolist"):  # numpy scalars and arrays
        return to_native(obj.tolist())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if hasattr(obj, "isoformat"):  # date, datetime, Timestamp
        return obj.isoformat()
    return str(obj)


def _git(*args: str, timeout: float = 30.0) -> Optional[str]:
    """stdout of ``git -C <repo> <args>``; None when git is missing or fails (the manifest then says unknown)."""
    try:
        done = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, timeout=timeout, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("git %s failed: %s", args[0], exc)
        return None
    return done.stdout


def code_files() -> List[Path]:
    """Python files of this run that sit in the figure folder or the pipeline folder: the figure script, theme.py,
    figdata.py, any helper module next to them and the shared contract common.py."""
    folders = {SCRIPTS_DIR, PIPELINE_DIR}
    found = set()
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        if file and str(file).endswith(".py"):
            path = Path(file).resolve()
            if path.parent in folders:
                found.add(path)
    return sorted(found)


def git_states(paths: Sequence[Path]) -> Dict[Path, str]:
    """``clean`` | ``modified`` | ``untracked`` | ``ignored`` for each file; ``unknown`` when git cannot say."""
    paths = [Path(p).resolve() for p in paths]
    if not paths:
        return {}
    status = _git("status", "--porcelain", "--", *map(str, paths))
    tracked = _git("ls-files", "--", *map(str, paths))
    if status is None or tracked is None:
        return {p: "unknown" for p in paths}
    changed = {(REPO_ROOT / line[3:]).resolve(): line[:2] for line in status.splitlines() if len(line) > 3}
    tracked_set = {(REPO_ROOT / name).resolve() for name in tracked.splitlines()}
    states: Dict[Path, str] = {}
    for path in paths:
        code = next((c for listed, c in changed.items() if path == listed or listed in path.parents), None)
        if code == "??":
            states[path] = "untracked"
        elif code:
            states[path] = "modified"
        else:
            states[path] = "clean" if path in tracked_set else "ignored"
    return states


def library_versions() -> Dict[str, str]:
    versions = {"python": platform.python_version(), "matplotlib": mpl.__version__}
    for name in MANIFEST_PACKAGES:
        try:
            versions[name.lower()] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name.lower()] = "not installed"
    return versions


def results_provenance(results_dir: Optional[Path], sources: Sequence[Path]) -> Optional[Dict[str, Any]]:
    """Where the files of ``results_dir`` that a figure read came from, as ``report.yaml`` of 05_report.py records it.

    For the ``report.yaml`` itself: sha256, ``generated_at`` and ``inputs_fingerprint`` (the fingerprint of the result
    tables that 05_report.py read, which ties the figure to the table copies without the figure reading them).  For every
    source file that lies in ``results_dir``: its sha256, whether report.yaml lists it, whether the sha256 it recorded is
    the one the figure read (``matches_report``; false means the file was changed after 05_report.py wrote it), the
    ``inputs_fingerprint`` it was produced with and, for a file carried over from an earlier run (``--only``), the
    ``stale`` flag.  None when ``results_dir`` has no report.yaml; a report.yaml that cannot be read is recorded as an error,
    it never stops the figure.
    """
    report_path = Path(results_dir) / "report.yaml" if results_dir is not None else None
    if report_path is None or not report_path.is_file():
        return None
    try:
        import yaml

        with open(report_path) as handle:
            report = yaml.safe_load(handle) or {}
        listed = report.get("files") or {}
        record: Dict[str, Any] = {
            "report_yaml": {"path": display_path(report_path), "sha256": common.sha256_file(report_path),
                            "generated_at": report.get("generated_at"), "inputs_fingerprint": report.get("inputs_fingerprint"),
                            "script_sha256": (report.get("script") or {}).get("sha256")},
            "files": {},
        }
        for source in sources:
            source = Path(source)
            if source.resolve().parent != Path(results_dir).resolve() or source.name == report_path.name:
                continue
            entry = listed.get(source.name)
            actual = common.sha256_file(source)
            item: Dict[str, Any] = {"sha256": actual, "listed_in_report": entry is not None}
            if entry is not None:
                item["matches_report"] = entry.get("sha256") == actual
                item["inputs_fingerprint"] = (entry.get("produced_with") or {}).get("inputs_fingerprint")
                for flag in ("carried_over", "stale", "stale_reasons"):
                    if flag in entry:
                        item[flag] = entry[flag]
                if not item["matches_report"]:
                    logger.warning("%s differs from the file report.yaml describes: it was changed after 05_report.py wrote it", source.name)
                if entry.get("stale"):
                    logger.warning("%s is carried over from an earlier run of 05_report.py and marked stale: %s", source.name,
                                   entry.get("stale_reasons"))
            record["files"][source.name] = item
        return record
    except Exception as exc:  # noqa: BLE001  (provenance extras must not stop a figure)
        logger.warning("could not read %s for the provenance: %s: %s", report_path, type(exc).__name__, exc)
        return {"error": f"{type(exc).__name__}: {exc}"}


def write_manifest(fig_id: str, sources: Sequence[Path], rows: Mapping[str, int], extra: Optional[Mapping[str, Any]] = None,
                   output_dir: Optional[Path] = None, outputs: Optional[Mapping[str, Path]] = None,
                   results_dir: Optional[Path] = None) -> Path:
    """Write ``<fig_id>.json`` next to the figure.

    It records the git sha and whether the working tree has uncommitted changes (``git_dirty``: ``git status --porcelain``
    is not empty, untracked files included; ``git_dirty_tracked``: a tracked file differs from HEAD; both null when git is
    not available), the code that drew the figure (``code``: path, sha256 and git state of the figure script, theme.py,
    figdata.py, any helper module and common.py), the command line, the library versions, the source files (sha256, bytes)
    with row counts, the output files, and the figure's own ``extra`` facts.  The sha256 of the code files, not the git
    sha, ties a figure to the code that drew it while the figure scripts are not committed.  With ``results_dir`` the
    manifest also holds ``results``: what report.yaml of 05_report.py says about the files that were read
    (:func:`results_provenance`), which ties the figure to the result tables behind them.
    """
    output_dir = output_dir or OUTPUT_DIR
    tree = _git("status", "--porcelain")
    tracked_changes = _git("status", "--porcelain", "--untracked-files=no")
    code = code_files()
    states = git_states(code)
    manifest: Dict[str, Any] = {
        "figure": fig_id,
        "generated_utc": common.utcnow().isoformat(timespec="seconds"),
        "git_sha": common.git_sha(),
        "git_dirty": None if tree is None else bool(tree.strip()),
        "git_dirty_tracked": None if tracked_changes is None else bool(tracked_changes.strip()),
        "argv": [Path(sys.argv[0]).name, *sys.argv[1:]],
        "code": [{"path": display_path(p), "sha256": common.sha256_file(p), "git": states[p.resolve()]} for p in code],
        "versions": library_versions(),
        "outputs": {},
        "sources": [],
        "results": results_provenance(results_dir, sources),
        "rows": dict(rows),
        "extra": dict(extra or {}),
    }
    for kind, path in (outputs or {}).items():
        manifest["outputs"][kind] = {"path": display_path(path), "sha256": common.sha256_file(path), "bytes": path.stat().st_size}
    if "png" in manifest["outputs"]:
        with Image.open((outputs or {})["png"]) as img:
            manifest["outputs"]["png"]["pixels"] = list(img.size)
    for path in sources:
        manifest["sources"].append({"path": display_path(path), "sha256": common.sha256_file(path), "bytes": path.stat().st_size})
    target = output_dir / f"{fig_id}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(to_native(manifest), indent=2, sort_keys=True, allow_nan=False) + "\n")
    tmp.replace(target)
    return target


def finish(fig: Figure, fig_id: str, args: argparse.Namespace, sources: Sequence[Path], rows: Mapping[str, int],
           extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Path]:
    """Save the figure, write its manifest and log where everything went; returns the written paths."""
    description = f"{fig_id}; sources: " + ", ".join(display_path(p) for p in sources)
    outputs = save_figure(fig, fig_id, args.output_dir, pdf=not args.no_pdf, metadata={"Description": description})
    manifest = write_manifest(fig_id, sources, rows, extra, args.output_dir, outputs, getattr(args, "results_dir", None))
    outputs["json"] = manifest
    logger.info("%s: wrote %s", fig_id, ", ".join(p.name for p in outputs.values()))
    return outputs
