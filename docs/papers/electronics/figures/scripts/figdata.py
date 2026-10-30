#!/usr/bin/env python3
"""Input loading for the Electronics figure scripts.

Figures read only what the pipeline wrote: the CSV/YAML summaries of ``05_report.py`` under
``docs/papers/electronics/results/`` and the parquet copies of the result tables under
``data/backups/gex_llm/tables/{series,windows,detections,runs}/``.  The long CSV schemas that 05_report.py documents in
its docstring are the contract (``detection_by_year.csv``, ``bridge_agreement.csv``, ``series_comparison.csv``); the loaders
below require exactly their columns and turn percent into fractions in one place.  There is no database access,
no sqlite and no synthetic fallback: a missing file or column stops the figure with a message that
names the file and the script that has to write it.

Every file a figure reads is recorded by :class:`Inputs` (path and row count) so the figure's
manifest lists exactly what went into it.  Every read is also guarded against repeated keys: a CSV against its
natural key (or, when the caller names none, against fully identical rows), a parquet table against the UNIQUE
constraint of its table, a YAML file against a key repeated in one mapping, so a window can never be counted twice
without the figure stopping.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, NoReturn, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

import theme
from theme import common

logger = logging.getLogger("electronics.figures")

# Natural keys of the parquet tables (the UNIQUE constraints of gex_llm_regime_schema.sql); duplicates would
# silently double-count windows, so the loader refuses them.
NATURAL_KEYS: Dict[str, Tuple[str, ...]] = {
    "series": ("series_key", "symbol", "trading_date"),
    "windows": ("series_key", "symbol", "window_end"),
    "detections": ("arm", "series_key", "symbol", "window_end", "model", "prompt_version"),
    "runs": ("run_id",),
}
PRODUCERS: Dict[str, str] = {
    "series": "01_build_series.py", "windows": "02_build_windows.py", "detections": "03_backfill_round1.py / 04_llm_runner.py",
    "runs": "04_llm_runner.py",
}
DATE_COLUMNS = ("trading_date", "window_end", "window_start")


class _UniqueKeyLoader(yaml.SafeLoader):
    """``yaml.safe_load`` that refuses a key repeated inside one mapping (the plain loader keeps the last one silently)."""

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        seen = set()
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":  # '<<: *anchor' is resolved by the plain loader below
                continue
            key = self.construct_object(key_node, deep=deep)
            try:
                repeated = key in seen
                seen.add(key)
            except TypeError:  # an unhashable key: the plain loader refuses it with its own message below
                break
            if repeated:
                raise yaml.constructor.ConstructorError("while constructing a mapping", node.start_mark,
                                                        f"found the key {key!r} twice", key_node.start_mark)
        return super().construct_mapping(node, deep)


class Inputs:
    """Reads the figure's inputs and remembers each file (path, rows) for the provenance manifest."""

    def __init__(self, fig_id: str, results_dir: Path, tables_dir: Path) -> None:
        self.fig_id = fig_id
        self.results_dir = Path(results_dir)
        self.tables_dir = Path(tables_dir)
        self._rows: Dict[Path, int] = {}
        self._yaml: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ bookkeeping
    def fail(self, message: str) -> NoReturn:
        raise SystemExit(f"{self.fig_id}: {message}")

    def _record(self, path: Path, rows: int) -> None:
        self._rows[path] = self._rows.get(path, 0) + rows

    @property
    def sources(self) -> List[Path]:
        return sorted(self._rows)

    @property
    def rows(self) -> Dict[str, int]:
        return {theme.display_path(p): n for p, n in sorted(self._rows.items())}

    # ------------------------------------------------------------------ results/ (05_report.py)
    def csv(self, name: str, required: Sequence[str], key: Optional[Sequence[str]] = None) -> pd.DataFrame:
        """``results_dir/name`` with the ``required`` columns; stops on a missing file or column, an empty file and a repeated key.

        ``key`` is the natural key of the file (its columns are required too): two rows with the same key stop the figure,
        blanks count as equal, so a classifier row (blank arm and model) cannot repeat either.  Without a ``key`` rows that
        are identical in every column are refused.
        """
        path = self.results_dir / name
        if not path.is_file():
            self.fail(f"missing input {path} (written by 05_report.py; pass --results-dir to point elsewhere)")
        frame = pd.read_csv(path)
        frame.columns = [str(c).strip() for c in frame.columns]
        key = list(key or ())
        missing = [c for c in dict.fromkeys([*required, *key]) if c not in frame.columns]
        if missing:
            self.fail(f"{path.name} lacks column(s) {missing}; it has {list(frame.columns)}")
        if frame.empty:
            self.fail(f"{path.name} has no rows")
        columns = key or list(frame.columns)
        repeated = frame.duplicated(columns, keep=False)
        if repeated.any():
            sample = frame.loc[repeated, columns].head(2).to_dict("records")
            self.fail(f"{path.name} repeats {int(frame.duplicated(columns).sum())} row(s) of "
                      f"{'the key ' + str(tuple(key)) if key else 'identical rows'}, e.g. {sample}; 05_report.py writes one row per key, "
                      f"rerun it on the complete tables")
        self._record(path, len(frame))
        return frame

    def yaml(self, name: str = "report.yaml") -> Dict[str, Any]:
        if name in self._yaml:
            return self._yaml[name]
        path = self.results_dir / name
        if not path.is_file():
            self.fail(f"missing input {path} (written by 05_report.py; pass --results-dir to point elsewhere)")
        try:
            with open(path) as handle:
                data = yaml.load(handle, Loader=_UniqueKeyLoader)
        except yaml.YAMLError as exc:
            self.fail(f"{path.name} cannot be read as YAML ({' '.join(str(exc).split())[:300] or type(exc).__name__}); "
                      f"05_report.py writes valid YAML with one value per key, rerun it")
        if not isinstance(data, dict) or not data:
            self.fail(f"{path.name} is empty or not a mapping")
        self._record(path, len(data))
        self._yaml[name] = data
        return data

    # ------------------------------------------------------------------ parquet copies
    def table(self, kind: str, columns: Sequence[str], series_keys: Optional[Iterable[str]] = None,
              symbols: Optional[Iterable[str]] = None, arms: Optional[Iterable[str]] = None) -> pd.DataFrame:
        """Rows of ``<tables-dir>/<kind>/*.parquet`` restricted to the given keys, with ``columns`` only.

        ``series_key``/``symbol``/``arm`` filters are pushed into the parquet read; date columns come back as
        tz-naive ``datetime64``.  Filter columns that a table does not have are ignored for that file.  The whole
        natural key of the table is read whatever ``columns`` asks for, so a repeated key (a window counted twice) is
        refused even when the caller only wants a value column; only ``columns`` are returned.
        """
        directory = self.tables_dir / kind
        files = sorted(directory.glob("*.parquet")) if directory.is_dir() else []
        if not files:
            self.fail(f"no parquet files in {directory} ({PRODUCERS.get(kind, 'the pipeline')} writes them; "
                      f"pass --tables-dir to point elsewhere)")
        wanted = {"series_key": series_keys, "symbol": symbols, "arm": arms}
        key = NATURAL_KEYS.get(kind, ())
        requested = list(dict.fromkeys(columns))
        read_columns = list(dict.fromkeys([*requested, *key]))
        frames: List[pd.DataFrame] = []
        for path in files:
            names = set(pq.read_schema(path).names)
            missing = [c for c in read_columns if c not in names]
            if missing:
                self.fail(f"{theme.display_path(path)} lacks column(s) {missing}")
            filters = [(c, "in", sorted(set(v))) for c, v in wanted.items() if v is not None and c in names]
            part = pq.read_table(path, columns=read_columns, filters=filters or None).to_pandas()
            if part.empty:
                continue
            self._record(path, len(part))
            frames.append(part)
        if not frames:
            self.fail(f"{kind} parquet files hold no rows for series_key={_fmt(series_keys)} symbol={_fmt(symbols)} "
                      f"arm={_fmt(arms)}")
        frame = pd.concat(frames, ignore_index=True)
        for column in DATE_COLUMNS:
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column]).dt.tz_localize(None).dt.normalize()
        if key and frame.duplicated(list(key)).any():
            clash = int(frame.duplicated(list(key)).sum())
            sample = frame.loc[frame.duplicated(list(key), keep=False), list(key)].head(2).to_dict("records")
            self.fail(f"{kind} parquet files contain {clash} duplicate rows for the natural key {key}, e.g. {sample}; "
                      f"export one row per key (a repeat run needs its own arm name) before plotting")
        return frame[requested]


def _fmt(values: Optional[Iterable[str]]) -> str:
    return "any" if values is None else ",".join(sorted(set(values)))


# --------------------------------------------------------------------------- stored GEX windows
def sequence_values(stored: Any) -> np.ndarray:
    """The 30 daily net GEX values (USD) of a window, from any stored form of ``gex_sequence``.

    Accepts the JSON text written by the pipeline, a list/array of ``{"date", "net_gex_usd"}`` objects
    (what parquet returns for a JSONB column) or a plain list of numbers.
    """
    if isinstance(stored, (bytes, str)):
        stored = json.loads(stored)
    values = [float(d["net_gex_usd"]) if isinstance(d, Mapping) else float(d) for d in list(stored)]
    if len(values) != common.WINDOW_DAYS:
        raise ValueError(f"gex_sequence has {len(values)} values, expected {common.WINDOW_DAYS}")
    return np.asarray(values, dtype=float)


def sequence_matrix(frame: pd.DataFrame) -> np.ndarray:
    """(n_windows, 30) matrix of USD values from the ``gex_sequence`` column."""
    return np.vstack([sequence_values(s) for s in frame["gex_sequence"]])


# --------------------------------------------------------------------------- 05_report.py summaries
# 05_report.py scores the detections of these series against the windows of another series (composite windows).
WINDOW_SERIES: Dict[str, str] = {"intraday_late": common.INTRADAY_T0_KEY}

# The published results are the registered arms that no model is run for (common.ARMS, llm=False): r1_o4mini (Phase 4A,
# January 2026) and the dated Nov-2025 baselines r1_p3_o4mini and r1_p4_o4mini.  05_report.py reports each of them twice:
# under its own name WITHOUT the answers flagged detection_metadata.recovered_2026 (the published subset: 1,412 of the 1,476
# Phase 4A windows) and, when some rows carry the flag, under '<arm>_all' (arm_role backfill_all) with every stored answer.
# Headline numbers, gates and figures use the arm under its own name; the '_all' arm is a different arm, never a prefix match.
PUBLISHED_ARM = "r1_o4mini"
PUBLISHED_ARMS: Tuple[str, ...] = tuple(key for key, arm in common.ARMS.items() if not arm.llm)
ALL_SUFFIX = theme.ALL_SUFFIX

PERCENT_COLUMNS = ("rate_pct", "ci_lo_pct", "ci_hi_pct", "clf_rate_matched_pct")
BOOT_PERCENT_COLUMNS = ("rate_boot_lo_pct", "rate_boot_hi_pct")  # optional: a by-year quarter-block bootstrap interval, if 05 writes one
DETECTION_KEY = ("label_source", "arm", "model", "series_key", "symbol", "scope", "year")
DETECTION_REQUIRED = (
    "label_source", "arm", "arm_role", "model", "series_key", "symbol", "scope", "year", "n_windows", "n_parsed", "n", "n_detect",
    *PERCENT_COLUMNS, "n_indep_30d", "n_compared", "agree_pct", "kappa",
)  # fmt: skip
DETECTION_COLUMNS = (
    "series_key", "symbol", "year", "n", "clf_n_detect", "clf_rate", "clf_ci_lo", "clf_ci_hi", "arm", "arm_role", "model",
    "n_windows", "n_parsed", "llm_n_detect", "llm_rate", "llm_ci_lo", "llm_ci_hi", "n_compared", "clf_rate_matched",
    "agree_pct", "kappa", "n_indep_30d", "window_series_key",
)  # fmt: skip
WILSON_LABEL = "Wilson 95% CI (overlapping windows treated as independent, so optimistic)"
BOOTSTRAP_LABEL = "quarter-block bootstrap 95% CI"


def window_series_of(arm: str, series_key: str) -> str:
    """Series whose stored windows the answers of ``arm`` (series ``series_key``) were scored against, as in 05_report.py.

    The windows of a registered arm are those of ``common.arm_window_series(arm)`` (arm ``intraday_spy`` reads series
    ``intraday_late`` and is scored on the composite ``intraday_t0`` windows) while the detections keep
    ``series_key = arm.series_key``.  Repeats and ``_all`` variants resolve to their registered arm; arms outside the registry
    (pilots) use their own series, or ``WINDOW_SERIES`` for a composite.
    """
    registered = theme.registered_arm(arm)
    if registered is not None and registered.series_key == series_key:
        return common.arm_window_series(registered)
    return WINDOW_SERIES.get(series_key, series_key)


def _numeric(inputs: "Inputs", frame: pd.DataFrame, columns: Sequence[str], name: str) -> None:
    """Convert ``columns`` of ``frame`` to numbers in place; a value that is not a number stops the figure."""
    for column in columns:
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (ValueError, TypeError) as exc:
            inputs.fail(f"{name}: column {column!r} holds values that are not numbers ({exc})")


def load_detection_by_year(inputs: Inputs) -> pd.DataFrame:
    """The yearly rows of ``detection_by_year.csv``: classifier rows and LLM rows, rates as fractions in [0, 1].

    05_report.py writes one long table (``label_source`` is ``classifier`` or ``llm``, ``scope`` is ``year`` or
    ``all``, rates in percent).  The all-years rows are dropped here and the rest comes back as

    * classifier rows (``arm`` is NaN): ``n`` windows of a (series, symbol, year), ``clf_n_detect`` of them
      detected, ``clf_rate`` with its Wilson interval ``clf_ci_lo``/``clf_ci_hi``;
    * LLM rows: ``arm``, ``arm_role``, ``model``, ``n_windows`` requested, ``n_parsed`` answers, ``llm_n_detect``
      detections, ``llm_rate`` with ``llm_ci_lo``/``llm_ci_hi``, ``n_compared`` answers that have a classifier
      label, ``clf_rate_matched`` (the classifier rate on exactly those windows), ``agree_pct`` and ``kappa``
      against the classifier, and the classifier columns of the series the arm read (``intraday_late`` arms
      read the ``intraday_t0`` windows).

    Both kinds carry ``n_indep_30d``, the number of non-overlapping 30-day windows behind the rate, and
    ``window_series_key``, the series whose windows the row was scored on (the row's own series for a classifier row).

    Which count is the base of a rate: ``clf_rate`` is over ``n`` (all windows of the series, symbol and year, also on
    an LLM row, where it repeats the classifier row of the windows the arm read); ``llm_rate`` is over ``n_parsed``
    (the windows with a parsed answer; ``n_windows`` counts every window the arm has a row for).  The percent columns
    of the file are divided by 100 here and nowhere else, and the loader proves the unit instead of guessing it:
    ``rate_pct`` must equal 100 * ``n_detect`` / ``n`` inside its own interval, otherwise it stops.

    The published results come in two arms (see ``PUBLISHED_ARMS``): ``r1_o4mini`` is the published subset (answers not
    flagged ``recovered_2026``), ``r1_o4mini_all`` (``arm_role`` ``backfill_all``) holds every stored answer.  Both are kept
    as rows of their own; select one by equality of ``arm`` and use :func:`recovered_by_year` for the difference.  A repeat
    ``<arm>#rep1`` is a row of its own (``arm_role`` ``repeat``), a pilot ``pilot_<arm>`` too.

    When the file also has ``rate_boot_lo_pct`` and ``rate_boot_hi_pct`` (a by-year quarter-block bootstrap interval) they
    come back as ``clf_boot_lo``/``clf_boot_hi`` and ``llm_boot_lo``/``llm_boot_hi`` fractions, and :func:`ci_columns` then
    draws and names that interval; 05_report.py writes none today (the bootstrap is in ``stats.yaml``).
    """
    frame = inputs.csv("detection_by_year.csv", DETECTION_REQUIRED, key=DETECTION_KEY)
    unknown = sorted(set(frame["label_source"].dropna()) - {"classifier", "llm"})
    if unknown:
        inputs.fail(f"detection_by_year.csv has label_source value(s) {unknown}; expected 'classifier' or 'llm'")
    scopes = sorted(set(frame["scope"].dropna()) - {"year", "all"})
    if scopes:
        inputs.fail(f"detection_by_year.csv has scope value(s) {scopes}; expected 'year' or 'all'")
    boot = [c for c in BOOT_PERCENT_COLUMNS if c in frame.columns]
    if boot and len(boot) != len(BOOT_PERCENT_COLUMNS):
        inputs.fail(f"detection_by_year.csv has {boot} without {sorted(set(BOOT_PERCENT_COLUMNS) - set(boot))}; "
                    "a bootstrap interval needs both ends")
    yearly = frame[frame["scope"] == "year"].copy()
    if yearly.empty:
        inputs.fail("detection_by_year.csv has no yearly rows (scope == 'year')")
    years = pd.to_numeric(yearly["year"], errors="coerce")
    if years.isna().any():
        inputs.fail(f"detection_by_year.csv has {int(years.isna().sum())} yearly row(s) without a year")
    yearly["year"] = years.astype(int)
    _numeric(inputs, yearly, ["n_windows", "n_parsed", "n", "n_detect", "n_indep_30d", "n_compared", "agree_pct", "kappa",
                              *PERCENT_COLUMNS, *boot], "detection_by_year.csv")
    named = yearly["arm"].notna() & (yearly["arm"].astype(str).str.strip() != "")
    if (named != (yearly["label_source"] == "llm")).any():
        bad = yearly.loc[named != (yearly["label_source"] == "llm"), ["label_source", "arm", "series_key", "year"]]
        inputs.fail("detection_by_year.csv: a classifier row has an arm or an llm row has none (05_report.py leaves the arm of a "
                    f"classifier row blank), e.g. {bad.head(2).values.tolist()}")
    percent = [*PERCENT_COLUMNS, *boot]
    top, bottom = float(yearly[percent].max().max()), float(yearly[percent].min().min())
    if top > 100.0 + 1e-6 or bottom < -1e-6:
        inputs.fail(f"detection_by_year.csv has a rate of {top if top > 100 else bottom:g}; 05_report.py writes percent in [0, 100]")
    # The columns are named *_pct and are divided by 100 below, never guessed from their size.  This check proves the
    # unit instead: rate_pct must be 100 * n_detect / n and sit inside its own interval (the file is rounded to 6 digits).
    counted = yearly["n"] > 0
    adrift = (yearly["rate_pct"] - 100.0 * yearly["n_detect"] / yearly["n"]).abs() > 1e-4
    outside = (yearly["ci_lo_pct"] > yearly["rate_pct"] + 1e-4) | (yearly["rate_pct"] > yearly["ci_hi_pct"] + 1e-4)
    if (counted & (adrift | outside)).any():
        bad = yearly.loc[counted & (adrift | outside), ["label_source", "arm", "series_key", "year", "rate_pct", "n_detect", "n"]]
        inputs.fail("detection_by_year.csv: rate_pct is not 100 * n_detect / n inside [ci_lo_pct, ci_hi_pct] (did the units of "
                    f"05_report.py change?), e.g. {bad.head(2).values.tolist()}")
    yearly[percent] = yearly[percent] / 100.0
    is_classifier = yearly["label_source"] == "classifier"
    extra_names = {"rate_boot_lo_pct": "boot_lo", "rate_boot_hi_pct": "boot_hi"}
    clf = yearly[is_classifier].rename(
        columns={"rate_pct": "clf_rate", "ci_lo_pct": "clf_ci_lo", "ci_hi_pct": "clf_ci_hi", "n_detect": "clf_n_detect",
                 **{k: f"clf_{v}" for k, v in extra_names.items()}})
    llm = yearly[~is_classifier].rename(
        columns={"rate_pct": "llm_rate", "ci_lo_pct": "llm_ci_lo", "ci_hi_pct": "llm_ci_hi", "n_detect": "llm_n_detect",
                 "clf_rate_matched_pct": "clf_rate_matched", "n": "n_answered", **{k: f"llm_{v}" for k, v in extra_names.items()}})
    reference = clf[["series_key", "symbol", "year", "n", "clf_rate", "clf_ci_lo", "clf_ci_hi"]].rename(
        columns={"series_key": "window_series_key"})
    llm = llm.assign(window_series_key=[window_series_of(a, s) for a, s in zip(llm["arm"], llm["series_key"], strict=True)]).merge(
        reference, on=["window_series_key", "symbol", "year"], how="left")
    llm["n"] = llm["n"].fillna(llm["n_windows"])  # an arm without a classifier row still reports its own count
    clf = clf.assign(window_series_key=clf["series_key"])
    columns = [*DETECTION_COLUMNS, *(f"{p}_{v}" for p in ("clf", "llm") for v in extra_names.values() if boot)]
    out = pd.concat([clf.reindex(columns=columns), llm.reindex(columns=columns)], ignore_index=True)
    out["arm"] = out["arm"].where(out["arm"].notna() & (out["arm"].astype(str).str.strip() != ""), np.nan)
    return out


def classifier_rates(detection: pd.DataFrame) -> pd.DataFrame:
    """The deterministic classifier rows (``arm`` is NaN), one per (series_key, symbol, year).

    The classifier columns that LLM rows carry for comparison are not rows of their own and are left out.
    """
    frame = detection[detection["arm"].isna()]
    twice = frame[frame.duplicated(["series_key", "symbol", "year"], keep=False)]
    if not twice.empty:
        example = twice[["series_key", "symbol", "year"]].head(2).values.tolist()
        raise ValueError(f"several classifier rows per (series_key, symbol, year), e.g. {example}")
    return frame.copy()


def llm_rates(detection: pd.DataFrame, roles: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """The LLM rows that carry a rate: one per (arm, model, series_key, symbol, year), none dropped.

    An arm scored by several models, or on several symbols, keeps one row for each of them; select the model and the
    symbol the figure means, then index by year with :func:`one_per_year`.  The published o4-mini result is the arm
    ``r1_o4mini`` (answers parsed in January 2026); ``r1_o4mini_all`` adds the windows recovered later and is a
    different arm, so select by equality, not by prefix.  Test-retest repeats (``<arm>#rep1``) and pilots are rows of
    their own arms too; ``roles`` keeps only the rows whose ``arm_role`` is one of the given roles (``primary``,
    ``backfill``, ``backfill_all``, ``repeat``, ``pilot``, ``other``).
    """
    rows = detection.dropna(subset=["arm", "llm_rate"])
    if roles is not None:
        rows = rows[rows["arm_role"].isin(set(roles))]
    return rows.copy()


def recovered_by_year(detection: pd.DataFrame, arm: str = PUBLISHED_ARM, symbol: str = "SPY") -> Optional[pd.Series]:
    """Answers per year that ``<arm>_all`` holds beyond the published arm ``arm``, for one symbol; None without an ``_all`` arm.

    For ``r1_o4mini`` these are the answers re-parsed in 2026 that the published result (1,412 of 1,476 windows) does not
    contain; the series is indexed by year and counts parsed answers (``n_parsed``).
    """
    rows = llm_rates(detection)
    rows = rows[rows["symbol"] == symbol]
    wide = rows[rows["arm"] == arm + ALL_SUFFIX]
    if wide.empty:
        return None
    narrow = rows[rows["arm"] == arm]
    both = one_per_year(wide, f"arm {arm + ALL_SUFFIX}")["n_parsed"]
    base = one_per_year(narrow, f"arm {arm}")["n_parsed"] if len(narrow) else pd.Series(dtype=float)
    extra = both.sub(base, fill_value=0)
    if (extra < 0).any():
        raise ValueError(f"arm {arm} has more answers than {arm + ALL_SUFFIX} in year(s) {[int(y) for y in extra.index[extra < 0]]}; "
                         "the variant with the recovered answers must contain the published ones")
    return extra.astype(int)


def one_per_year(frame: pd.DataFrame, what: str) -> pd.DataFrame:
    """``frame`` sorted and indexed by ``year``; ValueError when a year occurs twice (select a model or symbol first)."""
    twice = frame[frame.duplicated("year", keep=False)]
    if not twice.empty:
        found = sorted(set(zip(twice["model"].astype(str), twice["symbol"].astype(str), strict=True)))
        raise ValueError(f"{what}: several rows per year for (model, symbol) {found}; select one before indexing by year")
    return frame.sort_values("year").set_index("year")


def years_without(frame: pd.DataFrame, years: Sequence[int], column: str) -> List[int]:
    """The ``years`` for which the year-indexed ``frame`` has no value in ``column`` (no row, or NaN)."""
    have = {int(y) for y in frame[column].dropna().index} if len(frame) else set()
    return [int(y) for y in years if int(y) not in have]


def ci_columns(frame: pd.DataFrame, prefix: str, method: str = "auto") -> Tuple[str, str, str]:
    """(lo column, hi column, label) of the interval to draw for ``prefix`` in {'clf', 'llm'}.

    ``detection_by_year.csv`` carries Wilson intervals; stride-1 windows overlap, so they are descriptive and too narrow
    (the overlap-aware bootstrap and the non-overlapping subsample are in ``stats.yaml``).  Only when ``frame`` has a
    quarter-block bootstrap interval for ``prefix`` (``<prefix>_boot_lo``/``<prefix>_boot_hi``, see
    :func:`load_detection_by_year`) with a value on every row, that interval is returned and named; the label always says
    which interval the columns hold.  ``method='wilson'`` asks for the Wilson columns whatever else the frame has (a
    figure whose bars come from different frames uses it when the frames do not all have the bootstrap interval).
    """
    if method not in ("auto", "wilson"):
        raise ValueError(f"method must be 'auto' or 'wilson', not {method!r}")
    boot = (f"{prefix}_boot_lo", f"{prefix}_boot_hi")
    if method == "auto" and all(c in frame.columns for c in boot) and len(frame) and frame[list(boot)].notna().all().all():
        return boot[0], boot[1], BOOTSTRAP_LABEL
    lo, hi = f"{prefix}_ci_lo", f"{prefix}_ci_hi"
    missing = [c for c in (lo, hi) if c not in frame.columns]
    if missing:
        raise KeyError(f"no interval columns {missing} in the detection frame")
    return lo, hi, WILSON_LABEL


def whiskers(frame: pd.DataFrame, rate: str, lo: str, hi: str) -> np.ndarray:
    """Asymmetric error-bar array (2, n) in percent points from a rate and its interval columns."""
    y = frame[rate].to_numpy(float) * 100.0
    return np.vstack([np.clip(y - frame[lo].to_numpy(float) * 100.0, 0, None),
                      np.clip(frame[hi].to_numpy(float) * 100.0 - y, 0, None)])


SERIES_COMPARISON_REQUIRED = (
    "series_a", "series_b", "symbol", "scope", "year", "n_days", "last_date", "mean_abs_a_bn", "mean_abs_b_bn",
    "sign_agree_pct", "exact_match_pct",
)  # fmt: skip
SERIES_COMPARISON_KEY = ("series_a", "series_b", "symbol", "scope", "year")


def load_series_comparison(inputs: Inputs) -> pd.DataFrame:
    """The yearly rows of ``series_comparison.csv``, one per (series_a, series_b, symbol, year).

    ``year`` is an int, ``last_date`` a Timestamp and ``pair`` the label ``'<series_a>_vs_<series_b>'``.  ``mean_abs_a_bn``
    and ``mean_abs_b_bn`` are means of |net GEX| over the daily values the two series share (USD billions),
    ``sign_agree_pct`` is the share of those days on which both values are positive or both are not, ``exact_match_pct`` the
    share equal within USD 6M.
    """
    frame = inputs.csv("series_comparison.csv", SERIES_COMPARISON_REQUIRED, key=SERIES_COMPARISON_KEY)
    unknown = sorted(set(frame["scope"].dropna()) - {"year", "all"})
    if unknown:
        inputs.fail(f"series_comparison.csv has scope value(s) {unknown}; expected 'year' or 'all'")
    yearly = frame[frame["scope"] == "year"].copy()
    years = pd.to_numeric(yearly["year"], errors="coerce")
    if yearly.empty or years.isna().any():
        inputs.fail("series_comparison.csv has no usable yearly rows (scope == 'year' with a year)")
    yearly["year"] = years.astype(int)
    yearly["last_date"] = pd.to_datetime(yearly["last_date"])
    yearly["pair"] = yearly["series_a"].astype(str) + "_vs_" + yearly["series_b"].astype(str)
    return yearly.reset_index(drop=True)


BRIDGE_CELLS = ("n_ref_det_oth_det", "n_ref_det_oth_not", "n_ref_not_oth_det", "n_ref_not_oth_not")
BRIDGE_KEY = ("comparison", "ref_arm", "other_arm", "series_key", "symbol", "scope", "year")
BRIDGE_REQUIRED = (
    "comparison", "ref_arm", "other_arm", "series_key", "symbol", "scope", "year", "n_pairs", *BRIDGE_CELLS, "agree_pct",
    "agree_ci_lo_pct", "agree_ci_hi_pct", "agree_boot_lo_pct", "agree_boot_hi_pct", "kappa", "kappa_boot_lo", "kappa_boot_hi",
)  # fmt: skip


def load_bridge_agreement(inputs: Inputs) -> pd.DataFrame:
    """``bridge_agreement.csv`` with ``year`` as a nullable integer (empty on the all-years rows).

    ``comparison == 'bridge'`` compares a reference arm (the published o4-mini labels, arm ``r1_o4mini``) with another
    arm on the same windows; ``'bridge_incl_recovered'`` repeats that with the answers recovered in 2026 added to the
    reference (arm ``r1_o4mini_all``); ``'test_retest'`` compares an arm with its own repeated requests.  The 2x2 counts are
    ``n_ref_det_oth_det`` (both detect), ``n_ref_det_oth_not`` (only the reference), ``n_ref_not_oth_det`` (only the
    other arm) and ``n_ref_not_oth_not``.  Yearly rows have Wilson intervals; the all-years rows add quarter-block
    bootstrap intervals for the agreement and kappa.
    """
    frame = inputs.csv("bridge_agreement.csv", BRIDGE_REQUIRED, key=BRIDGE_KEY)
    unknown = sorted(set(frame["scope"].dropna()) - {"year", "all"})
    if unknown:
        inputs.fail(f"bridge_agreement.csv has scope value(s) {unknown}; expected 'year' or 'all'")
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    if frame.loc[frame["scope"] == "year", "year"].isna().any():
        inputs.fail("bridge_agreement.csv has yearly rows without a year")
    # The comparison types fix which reference arm a row has: the published answers, the variant with the recovered answers,
    # the arm itself.  A row that breaks this would put the wrong 1,412 / 1,476 windows behind a headline number.
    ref, other = frame["ref_arm"].astype(str), frame["other_arm"].astype(str)
    repeat_of = pd.Series([o.startswith(r + common.REPEAT_MARK) for r, o in zip(ref, other, strict=True)], index=frame.index, dtype=bool)
    mixed = {
        "bridge with an '_all' reference": (frame["comparison"] == "bridge") & ref.str.endswith(ALL_SUFFIX),
        "bridge_incl_recovered without an '_all' reference": (frame["comparison"] == "bridge_incl_recovered") & ~ref.str.endswith(ALL_SUFFIX),
        f"test_retest whose other arm is not a '{common.REPEAT_MARK}<k>' repeat of the reference": (frame["comparison"] == "test_retest") & ~repeat_of,
    }
    for what, rows in mixed.items():
        if rows.any():
            inputs.fail(f"bridge_agreement.csv has {int(rows.sum())} row(s) of {what}, e.g. "
                        f"{frame.loc[rows, ['comparison', 'ref_arm', 'other_arm']].head(2).values.tolist()}")
    return frame


def kappa_defined(frame: pd.DataFrame) -> pd.Series:
    """True where both raters of the 2x2 counts answer both ways at least once.

    When one rater is constant (for example every published label of a year is 'detected'), Cohen's kappa is 0 or
    undefined whatever the raw agreement, so it says nothing about the pair.
    """
    ref_det = frame["n_ref_det_oth_det"] + frame["n_ref_det_oth_not"]
    ref_not = frame["n_ref_not_oth_det"] + frame["n_ref_not_oth_not"]
    oth_det = frame["n_ref_det_oth_det"] + frame["n_ref_not_oth_det"]
    oth_not = frame["n_ref_det_oth_not"] + frame["n_ref_not_oth_not"]
    return (ref_det > 0) & (ref_not > 0) & (oth_det > 0) & (oth_not > 0)


def cohen_kappa(both: float, only_a: float, only_b: float, neither: float) -> float:
    """Cohen's kappa of a 2x2 table (NaN when chance agreement is 1)."""
    n = both + only_a + only_b + neither
    if n == 0:
        return float("nan")
    observed = (both + neither) / n
    expected = ((both + only_a) * (both + only_b) + (neither + only_a) * (neither + only_b)) / n**2
    return float("nan") if expected >= 1 else (observed - expected) / (1 - expected)


# --------------------------------------------------------------------------- report.yaml
def classifier_thresholds(inputs: Inputs) -> Dict[str, float]:
    """The classifier thresholds the stored labels were made with (``report.yaml`` ``diagnostics.thresholds``).

    Keys: ``persistence`` (fraction of days with the same sign), ``magnitude_bn`` (mean |GEX|, USD billions),
    ``max_sign_flips`` and ``low_conviction_bn``.
    """
    try:
        found = inputs.yaml("report.yaml")["diagnostics"]["thresholds"]
        return {"persistence": float(found["persistence"]), "magnitude_bn": float(found["mean_abs_gex_usd"]) / 1e9,
                "max_sign_flips": int(found["max_sign_flips"]), "low_conviction_bn": float(found["low_conviction_usd"]) / 1e9}
    except (KeyError, TypeError, ValueError):
        inputs.fail("report.yaml has no diagnostics.thresholds (05_report.py writes it when the windows table has rows)")


def report_coverage(inputs: Inputs, report: Mapping[str, Any], kind: str) -> pd.DataFrame:
    """``inputs.<kind>.coverage`` of ``report.yaml`` as a frame (kind: series, windows or detections).

    One row per (series_key, symbol), or per (arm, model, series_key, symbol) for detections, with ``rows`` and the
    ``first``/``last`` date (Timestamps) of the stored rows.
    """
    try:
        rows = report["inputs"][kind]["coverage"]
    except (KeyError, TypeError):
        inputs.fail(f"report.yaml has no inputs.{kind}.coverage (05_report.py writes it)")
    frame = pd.DataFrame(rows)
    if frame.empty:
        inputs.fail(f"report.yaml inputs.{kind}.coverage is empty: no {kind} rows were stored")
    needed = {"series_key", "symbol", "rows", "first", "last"} | ({"arm", "model"} if kind == "detections" else set())
    missing = sorted(needed - set(frame.columns))
    if missing:
        inputs.fail(f"report.yaml inputs.{kind}.coverage lacks column(s) {missing}")
    frame["first"] = pd.to_datetime(frame["first"])
    frame["last"] = pd.to_datetime(frame["last"])
    return frame
