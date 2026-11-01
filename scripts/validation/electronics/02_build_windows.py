#!/usr/bin/env python3
"""Build the 30-day windows and their deterministic Paper 2 verdicts (Electronics extension, step 02).

Cuts one daily GEX series (written by 01_build_series.py) into 30-day windows, one per end date.  Each window
is labelled the way its arm will show it to the model, hashed, and classified by the deterministic classifier
(src/validation/regime_classifier.py).  Labels are "Day T-29" .. "Day T+0" with no dates and no ticker, exactly
as in Phase 4A; the series p3_2024_dated and p4_2020_dated keep the ISO dates the Nov-2025 runs actually sent
(``common.Series.labels``).  No LLM is involved, so the step is free and can be re-run at any time.

Window rules (column ``window_rule``)
    A   30 consecutive rows of a series that follows the master calendar (every series not listed below).
    J   30 consecutive rows of a series with its own calendar (``common.Series.calendar == "self"``):
        jan2026_phase4a, p3_2024, p3_2024_dated, p4_2020, p4_2020_dated.  Before anything is written the windows
        must reproduce the surviving batch input file, otherwise FidelityError: the same window_end set, the
        same dates and 30 values per window, and the prompt that common.build_prompt() renders from them
        (labels as published: Day T-29 for January 2026, ISO dates for November 2025) equal to the prompt in the
        file byte for byte.
    T0  ``--composite intraday_t0``: new_full rows for T-29..T-1 plus the intraday_late (final_rush) row at T+0,
        for every intraday day with 29 earlier new_full rows; stored under series key intraday_t0.  Intraday days
        in ``common.INTRADAY_EXCLUDE_DAYS`` are dropped first.  (``intraday_late`` alone has no 30-row windows.)
    C   is reserved for a strict NYSE calendar and is not produced here.
    Windows never end after the series' own cap (``common.WINDOW_END_CAP`` = 2026-10-09 for the live series).

Holes (``window_metadata``, every rule; flagged windows are kept, never dropped)
    calendar_gap_days    widest gap in calendar days between neighbouring rows of the window
    missing_master_days  trading dates of the symbol's master calendar (gex.options_daily_summary) that lie
                         inside the window but are not among its rows (a skipped weekday leaves no calendar gap)
    gap_flag             true when calendar_gap_days > common.CALENDAR_GAP_FLAG_DAYS (4) or missing_master_days > 0
    The master calendar is read once per run: from the new_full series parquet of the symbol (default), or from
    gex.options_daily_summary with --master-calendar db (the default with --from-db).  It must cover every window.
    Composite windows add snapshot_timestamp, snapshot_type, t0_series and base_series.

Output
    ``<parquet root>/windows/<series_key>_<symbol>.parquet`` (default root data/backups/gex_llm/tables) and, only
    with --db, an upsert into backups.gex_llm_regime_windows.  Both hold the columns of that table (the surrogate
    key window_id is omitted) and both are upserts on (series_key, symbol, window_end): a run limited by
    --end-min/--end-max replaces the windows in its range and keeps the rest (a file written by an earlier version
    of this script, whose window_metadata lacks missing_master_days, is refused instead of mixed).  In parquet the
    JSON columns gex_sequence and window_metadata are JSON text; ``input_sha256`` is the SHA-256 of the stored
    gex_sequence text.  A series parquet that stops more than a week before the last requested window_end is
    refused (a partial build of step 01); pass --end-max to build from it anyway.

Safety
    The tables are created by the maintainer-approved schema file, never by this script: --db stops when the
    table is missing, and --rollback applies the schema inline inside a transaction that is always rolled back,
    so it can be used before the tables exist.  The schema file is run with its one BEGIN; and one COMMIT; line
    stripped and is refused when any other transaction-control statement remains.  --db and --rollback do not run
    between 21:50 and 22:45 UTC (``common.assert_not_quiet``; --ignore-busy-window overrides).

Examples (repository root, AutoGex env)::

    PYTHONPATH=$(pwd) python scripts/validation/electronics/02_build_windows.py --series jan2026_phase4a --symbol SPY
    PYTHONPATH=$(pwd) python scripts/validation/electronics/02_build_windows.py --series p3_2024_dated --symbol SPY
    PYTHONPATH=$(pwd) python scripts/validation/electronics/02_build_windows.py --series new_full --symbol SPY --end-min 2024-01-01
    PYTHONPATH=$(pwd) python scripts/validation/electronics/02_build_windows.py --composite intraday_t0 --symbol SPY
    PYTHONPATH=$(pwd) python scripts/validation/electronics/02_build_windows.py --series new_full --symbol SPY --rollback
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import common

logger = logging.getLogger("electronics.windows")

JANUARY_SERIES = "jan2026_phase4a"
BASE_SERIES = "new_full"  # supplies T-29..T-1 of the composite windows
LATE_SERIES = "intraday_late"  # supplies T+0 of the composite windows
RULE_OWN_CALENDAR = "J"  # series with their own calendar (common.Series.calendar == "self")
RULE_JANUARY = RULE_OWN_CALENDAR  # earlier name, still cited by planning/02_decisions_log.md
RULE_COMPOSITE = common.WINDOW_RULE_COMPOSITE  # "T0"
MASTER_TABLE = "gex.options_daily_summary"  # the master calendar: one row per symbol and trading date
STATEMENT_TIMEOUT = "600s"
END_SLACK_DAYS = 7  # a series may stop this many calendar days before the last requested window_end
START_SLACK_DAYS = 100  # ... and may start this many days after its registry start (QQQ: 81) without a warning

# One definition of the output columns for parquet and Postgres (window_id and the table defaults aside).
PARQUET_SCHEMA = pa.schema([
    ("series_key", pa.string()),
    ("symbol", pa.string()),
    ("window_end", pa.date32()),
    ("window_start", pa.date32()),
    ("n_days", pa.int32()),
    ("window_rule", pa.string()),
    ("gex_sequence", pa.string()),  # canonical JSON text of the labelled sequence; jsonb in Postgres
    ("input_sha256", pa.string()),
    ("clf_regime_type", pa.string()),
    ("clf_should_detect", pa.bool_()),
    ("clf_positive_days", pa.int32()),
    ("clf_negative_days", pa.int32()),
    ("clf_persistence_pct", pa.float64()),
    ("clf_avg_magnitude", pa.float64()),
    ("clf_sign_flips", pa.int32()),
    ("clf_version", pa.string()),
    ("window_metadata", pa.string()),  # JSON text; jsonb in Postgres
    ("created_at", pa.timestamp("us", tz="UTC")),
])
WINDOW_COLUMNS = tuple(PARQUET_SCHEMA.names)
CONFLICT_COLUMNS = ("series_key", "symbol", "window_end")
# Columns compared one-to-one when the rows are read back from Postgres (the JSON columns are checked separately).
READBACK_COLUMNS = tuple(c for c in WINDOW_COLUMNS
                         if c not in ("series_key", "symbol", "window_end", "gex_sequence", "window_metadata", "created_at"))

# The schema file wraps itself in one BEGIN; ... COMMIT; pair (each alone on its line); the rollback test strips
# exactly those two lines.  Everything else that ends or nests a transaction must not be there.
_BEGIN_LINE = re.compile(r"^[ \t]*BEGIN[ \t]*;[ \t]*$", re.IGNORECASE | re.MULTILINE)
_COMMIT_LINE = re.compile(r"^[ \t]*COMMIT[ \t]*;[ \t]*$", re.IGNORECASE | re.MULTILINE)
# What is not SQL code: comments, quoted strings and identifiers, dollar-quoted bodies.
_SQL_NOISE = re.compile(r"--[^\n]*|/\*.*?\*/|'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|\$(\w*)\$.*?\$\1\$", re.DOTALL)
_TRANSACTION_STATEMENT = re.compile(
    r"^(?:BEGIN|START|COMMIT|END|ABORT|ROLLBACK|SAVEPOINT|RELEASE|PREPARE\s+TRANSACTION"
    r"|SET\s+(?:SESSION\s+CHARACTERISTICS|TRANSACTION))\b", re.IGNORECASE)


class WindowBuildError(RuntimeError):
    """An input or an output cannot be used; the message says what to fix."""


class FidelityError(WindowBuildError):
    """The windows of a series with its own calendar differ from the surviving batch input file."""


@dataclass(frozen=True)
class WindowSpec:
    """One 30-day window before labelling and classification."""

    start: date
    end: date
    dates: Tuple[date, ...]  # the 30 trading dates, oldest first
    values: List[float]  # net GEX in USD, one per date
    extra: Dict[str, Any] = field(default_factory=dict)  # metadata of the builder (composites: the snapshot)


# --------------------------------------------------------------------------- database helpers
def open_connection(readonly: bool):
    """Connect to gex_options with the project statement timeout; ``readonly`` makes every write fail."""
    conn = common.connect()
    conn.set_session(readonly=readonly)
    with conn.cursor() as cur:
        cur.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT}'")
    conn.commit()
    return conn


def table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
        return bool(cur.fetchone()[0])


def transaction_statements(sql: str) -> List[str]:
    """Statements of ``sql`` that start with a transaction-control keyword (comments and quoted text ignored)."""
    code = _SQL_NOISE.sub(" ", sql)
    statements = (" ".join(part.split()) for part in code.split(";"))
    return [statement[:40] for statement in statements if statement and _TRANSACTION_STATEMENT.match(statement)]


def schema_sql_without_transaction_control() -> str:
    """The schema file minus its own BEGIN; and COMMIT; lines, so it can run inside a transaction that gets rolled back.

    Refuses when the file does not have exactly one of each, or when any other transaction-control statement is
    left (a stray COMMIT or ROLLBACK TO would make the dry run permanent or end it early).
    """
    sql, n_begin = _BEGIN_LINE.subn("", common.SCHEMA_SQL.read_text())
    sql, n_commit = _COMMIT_LINE.subn("", sql)
    if (n_begin, n_commit) != (1, 1):
        raise WindowBuildError(f"{common.SCHEMA_SQL.name}: expected one 'BEGIN;' and one 'COMMIT;' line, found {n_begin} and "
                               f"{n_commit}; not running it in a rollback test")
    left = transaction_statements(sql)
    if left:
        raise WindowBuildError(f"{common.SCHEMA_SQL.name}: transaction-control statement(s) remain after stripping BEGIN/COMMIT "
                               f"({'; '.join(left)}); not running it in a rollback test")
    return sql


# --------------------------------------------------------------------------- series input
def table_path(root: Path, kind: str, series_key: str, symbol: str) -> Path:
    """<root>/<kind>/<series_key>_<symbol>.parquet, the layout of common.parquet_path without creating folders."""
    return root / kind / f"{series_key}_{symbol}.parquet"


def clean_series(raw: pd.DataFrame, series_key: str, symbol: str, origin: str) -> pd.DataFrame:
    """Validate raw series rows; return trading_date, net_gex (and source_timestamp if present), by date."""
    missing = {"trading_date", "net_gex"} - set(raw.columns)
    if missing:
        raise WindowBuildError(f"{origin}: missing column(s) {sorted(missing)}")
    if {"series_key", "symbol"} <= set(raw.columns):
        raw = raw[(raw["series_key"] == series_key) & (raw["symbol"] == symbol)]
    if raw.empty:
        raise WindowBuildError(f"{origin}: no rows for {series_key}/{symbol}")
    frame = raw[[c for c in ("trading_date", "net_gex", "source_timestamp") if c in raw.columns]].copy()
    frame["trading_date"] = pd.to_datetime(frame["trading_date"]).dt.date
    frame["net_gex"] = frame["net_gex"].astype(float)
    if "source_timestamp" in frame:
        frame["source_timestamp"] = pd.to_datetime(frame["source_timestamp"], utc=True)
    frame = frame.sort_values("trading_date").reset_index(drop=True)
    if frame["trading_date"].duplicated().any():
        raise WindowBuildError(f"{origin}: duplicate trading_date for {series_key}/{symbol}")
    if not np.isfinite(frame["net_gex"].to_numpy()).all():
        raise WindowBuildError(f"{origin}: net_gex is missing or not finite on "
                               f"{int((~np.isfinite(frame['net_gex'].to_numpy())).sum())} row(s) of {series_key}/{symbol}")
    return frame


def read_series(series_key: str, symbol: str, conn=None, root: Path = common.PARQUET_ROOT) -> pd.DataFrame:
    """Series rows from the series parquet of step 01, or from backups.gex_llm_regime_series when ``conn`` is given."""
    if conn is None:
        path = table_path(root, "series", series_key, symbol)
        if not path.exists():
            raise WindowBuildError(f"series parquet not found: {path} (run 01_build_series.py, or pass --from-db)")
        return clean_series(pd.read_parquet(path), series_key, symbol, str(path))
    if not table_exists(conn, common.T_SERIES):
        raise WindowBuildError(f"{common.T_SERIES} does not exist yet; read the series parquet instead")
    with conn.cursor() as cur:
        cur.execute(f"SELECT series_key, symbol, trading_date, net_gex, source_timestamp FROM {common.T_SERIES} "
                    "WHERE series_key = %s AND symbol = %s", (series_key, symbol))
        raw = pd.DataFrame(cur.fetchall(), columns=[col.name for col in cur.description])
    return clean_series(raw, series_key, symbol, common.T_SERIES)


def check_series_coverage(frame: pd.DataFrame, series_key: str, symbol: str, end_max: date) -> None:
    """A series that stops long before the last requested window_end is a partial build of step 01: refuse it."""
    first, last = frame["trading_date"].iloc[0], frame["trading_date"].iloc[-1]
    if last < end_max - timedelta(days=END_SLACK_DAYS):
        raise WindowBuildError(f"{series_key}/{symbol} ends {last}, more than {END_SLACK_DAYS} days before the last window_end "
                               f"requested ({end_max}): the series looks incomplete (partial 01_build_series.py run); "
                               f"rebuild it, or pass --end-max {last} to build the windows it can support")
    start = common.SERIES[series_key].start or common.SYMBOL_START[symbol]
    if first > start + timedelta(days=START_SLACK_DAYS):
        logger.warning("%s/%s starts %s, %d days after its registry start %s: earlier windows are not built",
                       series_key, symbol, first, (first - start).days, start)


def read_master_calendar(symbol: str, source: str, root: Path) -> Tuple[List[date], str]:
    """Sorted trading dates of ``symbol`` in the master calendar (gex.options_daily_summary), read once per run.

    ``source`` 'parquet' takes them from the new_full series parquet of step 01 (one row per master date), 'db'
    from gex.options_daily_summary itself (a plain read-only SELECT of at most a few thousand dates).
    Returns the dates and a label of where they came from.
    """
    if source == "db":
        conn = open_connection(readonly=True)
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT DISTINCT trading_date FROM {MASTER_TABLE} WHERE symbol = %s "
                            "ORDER BY trading_date", (symbol,))
                dates = [row[0] for row in cur.fetchall()]
        finally:
            conn.close()
        origin = MASTER_TABLE
    else:
        path = table_path(root, "series", BASE_SERIES, symbol)
        if not path.exists():
            raise WindowBuildError(f"master calendar: {path} not found (run 01_build_series.py --series {BASE_SERIES} "
                                   f"--symbol {symbol}, or pass --master-calendar db)")
        dates = clean_series(pd.read_parquet(path), BASE_SERIES, symbol, str(path))["trading_date"].tolist()
        origin = f"{BASE_SERIES}/{symbol} series parquet"
    if not dates:
        raise WindowBuildError(f"master calendar of {symbol} is empty ({origin})")
    return dates, origin


def check_master_covers(master: Sequence[date], specs: Sequence[WindowSpec], origin: str) -> None:
    """The master calendar must span every window, or missing_master_days would silently count too few days."""
    first, last = min(spec.start for spec in specs), max(spec.end for spec in specs)
    if master[0] > first or master[-1] < last:
        raise WindowBuildError(f"master calendar ({origin}) covers {master[0]} .. {master[-1]} but the windows span "
                               f"{first} .. {last}; rebuild the {BASE_SERIES} series (01_build_series.py) "
                               f"or pass --master-calendar db")


def drop_irregular_intraday_days(late: pd.DataFrame) -> pd.DataFrame:
    """Remove the intraday days the data audit flagged as irregular (``common.INTRADAY_EXCLUDE_DAYS``)."""
    irregular = late["trading_date"].isin(common.INTRADAY_EXCLUDE_DAYS)
    if irregular.any():
        logger.info("dropping %d irregular intraday day(s): %s", int(irregular.sum()),
                    ", ".join(d.isoformat() for d in late.loc[irregular, "trading_date"]))
    return late.loc[~irregular].reset_index(drop=True)


def load_inputs(series_keys: Sequence[str], symbol: str, from_db: bool, root: Path, end_max: date) -> Dict[str, pd.DataFrame]:
    """Read every series a run needs from one source (parquet by default, Postgres with --from-db)."""
    conn = open_connection(readonly=True) if from_db else None
    try:
        frames = {key: read_series(key, symbol, conn, root) for key in series_keys}
    finally:
        if conn is not None:
            conn.close()
    if LATE_SERIES in frames:
        frames[LATE_SERIES] = drop_irregular_intraday_days(frames[LATE_SERIES])
    for key, frame in frames.items():
        logger.info("series %s/%s: %d rows, %s .. %s", key, symbol, len(frame),
                    frame["trading_date"].iloc[0], frame["trading_date"].iloc[-1])
        check_series_coverage(frame, key, symbol, end_max)
    return frames


# --------------------------------------------------------------------------- window construction
def gap_metadata(dates: Sequence[date], master: Sequence[date]) -> Dict[str, Any]:
    """The hole detectors for the dates of one window (``master``: sorted master trading dates of the symbol).

    calendar_gap_days is the widest gap between neighbouring rows; missing_master_days counts the master dates
    inside the window that it lacks.  gap_flag is set when either detector fires.
    """
    widest = max((later - earlier).days for earlier, later in zip(dates, dates[1:]))
    inside = master[bisect_left(master, dates[0]): bisect_right(master, dates[-1])]
    missing = len(set(inside) - set(dates))
    return {"calendar_gap_days": widest, "missing_master_days": missing,
            "gap_flag": widest > common.CALENDAR_GAP_FLAG_DAYS or missing > 0}


def consecutive_windows(series: pd.DataFrame, end_min: Optional[date], end_max: Optional[date]) -> List[WindowSpec]:
    """Rules A and J: every run of 30 consecutive series rows, ending inside [end_min, end_max]."""
    dates = series["trading_date"].tolist()
    values = series["net_gex"].tolist()
    position = {day: i for i, day in enumerate(dates)}
    return [WindowSpec(start, end, tuple(dates[position[start]: position[end] + 1]), vals)
            for start, end, vals in common.windows_over(dates, values, dates, end_min, end_max)]


def composite_windows(base: pd.DataFrame, late: pd.DataFrame,
                      end_min: Optional[date], end_max: Optional[date]) -> List[WindowSpec]:
    """Rule T0: the 29 base rows before each intraday day, followed by that day's intraday value."""
    if "source_timestamp" not in late or late["source_timestamp"].isna().any():
        raise WindowBuildError(f"{LATE_SERIES} rows need source_timestamp (the snapshot time recorded in window_metadata)")
    base_dates = base["trading_date"].tolist()
    base_values = base["net_gex"].tolist()
    history = common.WINDOW_DAYS - 1
    specs: List[WindowSpec] = []
    for day, value, stamp in zip(late["trading_date"], late["net_gex"], late["source_timestamp"]):
        if (end_min and day < end_min) or (end_max and day > end_max):
            continue
        cut = bisect_left(base_dates, day)  # base rows strictly before the intraday day
        if cut < history:
            logger.info("no composite window for %s: only %d earlier %s rows", day, cut, BASE_SERIES)
            continue
        dates = tuple(base_dates[cut - history: cut]) + (day,)
        extra = {"snapshot_timestamp": stamp.isoformat(), "snapshot_type": common.INTRADAY_SNAPSHOT_TYPE,
                 "t0_series": LATE_SERIES, "base_series": BASE_SERIES}
        specs.append(WindowSpec(dates[0], day, dates, base_values[cut - history: cut] + [value], extra))
    return specs


# --------------------------------------------------------------------------- fidelity to the surviving batch files
def load_batch_prompts(path: Path) -> Dict[date, str]:
    """{window_end: prompt text} of a batch input JSONL (custom_id 'window-YYYY-MM-DD')."""
    prompts: Dict[date, str] = {}
    with open(path) as fh:
        for line in fh:
            row = json.loads(line)
            prompts[date.fromisoformat(row["custom_id"].replace("window-", ""))] = row["body"]["messages"][0]["content"]
    return prompts


def published_inputs(series_key: str) -> Tuple[Path, str, Dict[date, Tuple[Optional[Tuple[date, ...]], List[float]]]]:
    """(batch input file, labels its prompts carry, {window_end: (dates or None, values)}) for a series with its own calendar.

    The January 2026 file shows "Day T-n" labels and so holds no dates; the November 2025 files show ISO dates.
    """
    if series_key == JANUARY_SERIES:
        return (common.PHASE4A_INPUT_JSONL, "obfuscated",
                {end: (None, values) for end, values in common.load_phase4a_inputs().items()})
    base = series_key.replace("_dated", "")
    if base not in common.PHASE34_FILES:
        raise WindowBuildError(f"{series_key}: no surviving batch input file is registered for this series")
    rows = common.load_phase34_inputs(base)
    return (common.PHASE34_FILES[base][0], "dated",
            {end: (tuple(day for day, _ in pairs), [value for _, value in pairs]) for end, pairs in rows.items()})


def same_dates_and_values(spec: WindowSpec, dates: Optional[Tuple[date, ...]], values: List[float]) -> bool:
    """The built window has the published values and, where the file shows dates, the published dates."""
    return spec.values == values and (dates is None or spec.dates == dates)


def describe_difference(spec: WindowSpec, dates: Optional[Tuple[date, ...]], values: List[float]) -> str:
    """Where a built window first departs from the published one (a date, or a value)."""
    for j in range(common.WINDOW_DAYS):
        if dates is not None and spec.dates[j] != dates[j]:
            return f"day {j - common.WINDOW_DAYS + 1:+d}: built date {spec.dates[j]}, published {dates[j]}"
        if spec.values[j] != values[j]:
            return f"day {j - common.WINDOW_DAYS + 1:+d}: built {spec.values[j]!r}, published {values[j]!r}"
    return "no difference"


def check_fidelity(series_key: str, specs: Sequence[WindowSpec], end_min: Optional[date], end_max: Optional[date]) -> None:
    """The fidelity test of rule J: the windows must reproduce the surviving batch input file.

    Same window_end set; same dates (Nov 2025 files) and the same 30 values per window; and the prompt rendered by
    common.build_prompt() from those dates and values, labelled as the file labels them, equal to the file's prompt
    byte for byte (a changed prompt template would otherwise go unnoticed).  The obfuscated twins p3_2024 and
    p4_2020 are held to the same file: only their stored labels differ from the dated series.
    """
    path, labels, everything = published_inputs(series_key)
    published = {end: item for end, item in everything.items()
                 if (end_min is None or end >= end_min) and (end_max is None or end <= end_max)}
    built = {spec.end: spec for spec in specs}
    absent = sorted(published.keys() - built.keys())
    unexpected = sorted(built.keys() - published.keys())
    if absent or unexpected:
        raise FidelityError(f"{series_key}: window_end set differs from {path.name}; "
                            f"{len(absent)} missing (first {absent[:3]}), {len(unexpected)} unexpected (first {unexpected[:3]})")
    differing = [end for end in sorted(published) if not same_dates_and_values(built[end], *published[end])]
    if differing:
        first = differing[0]
        raise FidelityError(f"{series_key}: {len(differing)} window(s) differ from {path.name} in their dates or values; first "
                            f"{first} {describe_difference(built[first], *published[first])}")
    prompts = load_batch_prompts(path)
    differing = [end for end in sorted(published)
                 if common.build_prompt(common.obfuscate(built[end].values, built[end].dates, labels)) != prompts.get(end)]
    if differing:
        raise FidelityError(f"{series_key}: dates and values equal {path.name} but {len(differing)} prompt(s) differ from the "
                            f"file (first {differing[0]}); the prompt template (src/llm/mechanics_prompt_builder.py) has "
                            f"changed since that batch was written")
    logger.info("fidelity ok: %d windows, window_end set, every date and value and every prompt (byte for byte) equal to %s",
                len(published), path.name)


def check_phase4a_fidelity(specs: Sequence[WindowSpec], end_min: Optional[date], end_max: Optional[date]) -> None:
    """The January 2026 case of check_fidelity (the name planning/02_decisions_log.md cites)."""
    check_fidelity(JANUARY_SERIES, specs, end_min, end_max)


# --------------------------------------------------------------------------- records
def build_records(series_key: str, symbol: str, rule: str, labels: str, specs: Sequence[WindowSpec],
                  master: Sequence[date]) -> List[Dict[str, Any]]:
    """Label, hash and classify every window; one dict per row of backups.gex_llm_regime_windows."""
    version = common.classifier_version()
    created_at = common.utcnow()
    records = []
    for spec in specs:
        sequence_json = json.dumps(common.obfuscate(spec.values, spec.dates, labels), separators=(",", ":"), sort_keys=True)
        verdict = common.classify(spec.values)
        records.append({
            "series_key": series_key,
            "symbol": symbol,
            "window_end": spec.end,
            "window_start": spec.start,
            "n_days": common.WINDOW_DAYS,
            "window_rule": rule,
            "gex_sequence": sequence_json,
            "input_sha256": hashlib.sha256(sequence_json.encode("utf-8")).hexdigest(),
            "clf_regime_type": verdict["regime_type"],
            "clf_should_detect": verdict["should_detect"],
            "clf_positive_days": verdict["positive_days"],
            "clf_negative_days": verdict["negative_days"],
            "clf_persistence_pct": verdict["persistence_pct"],
            "clf_avg_magnitude": verdict["avg_magnitude"],
            "clf_sign_flips": verdict["sign_flips"],
            "clf_version": version,
            "window_metadata": json.dumps({**gap_metadata(spec.dates, master), **spec.extra}, sort_keys=True),
            "created_at": created_at,
        })
    return records


# --------------------------------------------------------------------------- outputs
def warn_stale(stale: Sequence[date], where: str) -> None:
    """Stored windows in the rebuilt range that the series no longer yields are kept, but reported."""
    if stale:
        logger.warning("%s keeps %d window(s) between %s and %s that the series no longer produces; they stay as "
                       "records of earlier inputs (delete them by hand for a clean rebuild)",
                       where, len(stale), stale[0], stale[-1])


def has_hole_fields(metadata: Optional[str]) -> bool:
    """True for window_metadata written by this version of the script (it always carries missing_master_days)."""
    try:
        return "missing_master_days" in json.loads(metadata)
    except (TypeError, ValueError):
        return False


def write_parquet(records: Sequence[Dict[str, Any]], path: Path, span: Tuple[date, date]) -> int:
    """Upsert ``records`` into the parquet file on window_end; ``span`` is the window_end range this run covers.

    Returns the rows in the file afterwards.
    """
    merged = pa.Table.from_pylist(list(records), schema=PARQUET_SCHEMA)
    if path.exists():
        try:
            old = pq.read_table(path).cast(PARQUET_SCHEMA)
        except (KeyError, ValueError, pa.ArrowException) as exc:
            raise WindowBuildError(f"{path} does not have the windows schema ({exc}); delete it and rebuild") from exc
        rebuilt = {r["window_end"] for r in records}
        old_ends = old["window_end"].to_pylist()
        keep = pa.array([end not in rebuilt for end in old_ends], pa.bool_())
        kept = old.filter(keep)
        outdated = sum(not has_hole_fields(text) for text in kept["window_metadata"].to_pylist())
        if outdated:
            raise WindowBuildError(f"{path} holds {outdated} window(s) from an earlier version of this script (window_metadata "
                                   f"without missing_master_days) that this run would keep; "
                                   f"delete the file and rebuild the full range")
        warn_stale([end for end in old_ends if end not in rebuilt and span[0] <= end <= span[1]], path.name)
        merged = pa.concat_tables([kept, merged])
    merged = merged.sort_by("window_end")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".tmp")
    pq.write_table(merged, partial)
    partial.replace(path)
    return merged.num_rows


def verify_db_rows(conn, records: Sequence[Dict[str, Any]]) -> None:
    """Read the upserted rows back and compare them with ``records`` (sequence hash recomputed from the jsonb)."""
    first = records[0]
    columns = ", ".join(("window_end", "gex_sequence", "window_metadata") + READBACK_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(f"SELECT {columns} FROM {common.T_WINDOWS} "
                    "WHERE series_key = %s AND symbol = %s AND window_end = ANY(%s)",
                    (first["series_key"], first["symbol"], [r["window_end"] for r in records]))
        stored = {row[0]: dict(zip(("gex_sequence", "window_metadata") + READBACK_COLUMNS, row[1:])) for row in cur.fetchall()}
    problems = []
    if len(stored) != len(records):
        problems.append(f"{len(records)} windows sent, {len(stored)} found")
    for record in records:
        row = stored.get(record["window_end"])
        if row is None:
            continue
        resent = hashlib.sha256(json.dumps(row["gex_sequence"], separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        wrong = [c for c in READBACK_COLUMNS if row[c] != record[c]]
        if row["gex_sequence"] != json.loads(record["gex_sequence"]) or resent != record["input_sha256"]:
            wrong.append("gex_sequence")
        if row["window_metadata"] != (json.loads(record["window_metadata"]) if record["window_metadata"] else None):
            wrong.append("window_metadata")
        if wrong:
            problems.append(f"{record['window_end']}: {', '.join(wrong)}")
    if problems:
        raise WindowBuildError(f"read-back of {common.T_WINDOWS} differs from the built windows: "
                               f"{len(problems)} problem(s), first: {problems[:3]}")


def report_stale_db_rows(conn, records: Sequence[Dict[str, Any]], span: Tuple[date, date]) -> None:
    """Warn about stored windows in ``span`` that the series no longer produces."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT window_end FROM {common.T_WINDOWS} WHERE series_key = %s AND symbol = %s "
                    "AND window_end BETWEEN %s AND %s AND NOT (window_end = ANY(%s)) ORDER BY window_end",
                    (records[0]["series_key"], records[0]["symbol"], span[0], span[1], [r["window_end"] for r in records]))
        warn_stale([row[0] for row in cur.fetchall()], common.T_WINDOWS)


def write_windows_db(records: Sequence[Dict[str, Any]], span: Tuple[date, date], rollback: bool) -> None:
    """Upsert into backups.gex_llm_regime_windows, verify, then commit (--db) or roll everything back (--rollback)."""
    from psycopg2.extensions import TRANSACTION_STATUS_INTRANS

    schema_sql = schema_sql_without_transaction_control() if rollback else None  # refuses before any connection is made
    rows = [tuple(r[c] for c in WINDOW_COLUMNS) for r in records]
    conn = open_connection(readonly=False)
    try:
        existed = table_exists(conn, common.T_WINDOWS)
        if rollback:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            if conn.get_transaction_status() != TRANSACTION_STATUS_INTRANS:
                raise WindowBuildError("the schema file ended the transaction; the rollback test cannot guarantee a clean "
                                       "database")
        elif not existed:
            raise WindowBuildError(f"{common.T_WINDOWS} does not exist: the schema file is applied by the maintainer "
                                   f"after the documentation PR; use --parquet-only until then")
        common.upsert_rows(conn, common.T_WINDOWS, WINDOW_COLUMNS, rows, CONFLICT_COLUMNS)
        verify_db_rows(conn, records)
        report_stale_db_rows(conn, records, span)
        if not rollback:
            conn.commit()
            logger.info("upserted %d windows into %s", len(rows), common.T_WINDOWS)
            return
        common.upsert_rows(conn, common.T_WINDOWS, WINDOW_COLUMNS, rows, CONFLICT_COLUMNS)  # a repeat must change nothing
        verify_db_rows(conn, records)
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {common.T_WINDOWS} WHERE series_key = %s AND symbol = %s",
                        (records[0]["series_key"], records[0]["symbol"]))
            stored = cur.fetchone()[0]
        conn.rollback()
        if table_exists(conn, common.T_WINDOWS) != existed:
            raise WindowBuildError("rollback left a trace: table existence changed")
        logger.info("rollback test passed: schema applied, %d windows upserted twice (%d rows after the repeat), "
                    "read back identical, rolled back (table %s before and after)",
                    len(rows), stored, "present" if existed else "absent")
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------- reporting
def detection_by_year(records: Sequence[Dict[str, Any]]) -> pd.DataFrame:
    """Windows, deterministic detections, mean |GEX| and hole counts per window_end year, plus a total.

    cal_gap counts windows with calendar_gap_days above the flag threshold, missing_master with
    missing_master_days > 0, gap_flagged those with either.
    """
    metadata = [json.loads(r["window_metadata"]) for r in records]
    frame = pd.DataFrame({
        "year": [r["window_end"].year for r in records],
        "detected": [r["clf_should_detect"] for r in records],
        "mean_abs_gex_bn": [r["clf_avg_magnitude"] / 1e9 for r in records],
        "cal_gap": [m["calendar_gap_days"] > common.CALENDAR_GAP_FLAG_DAYS for m in metadata],
        "missing_master": [m["missing_master_days"] > 0 for m in metadata],
        "gap_flagged": [bool(m["gap_flag"]) for m in metadata],
    })
    table = frame.groupby("year").agg(windows=("detected", "size"), detected=("detected", "sum"),
                                      mean_abs_gex_bn=("mean_abs_gex_bn", "mean"), cal_gap=("cal_gap", "sum"),
                                      missing_master=("missing_master", "sum"), gap_flagged=("gap_flagged", "sum"))
    total = pd.DataFrame([[len(frame), frame["detected"].sum(), frame["mean_abs_gex_bn"].mean(), frame["cal_gap"].sum(),
                           frame["missing_master"].sum(), frame["gap_flagged"].sum()]], columns=table.columns, index=["all"])
    table = pd.concat([table, total])
    table.insert(2, "detected_pct", (100.0 * table["detected"] / table["windows"]).round(1))
    table["mean_abs_gex_bn"] = table["mean_abs_gex_bn"].round(2)
    return table.astype({"windows": int, "detected": int, "cal_gap": int, "missing_master": int, "gap_flagged": int})


# --------------------------------------------------------------------------- command line
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build 30-day windows with deterministic classifier labels from a daily GEX series.",
        epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--series", choices=list(common.SERIES),
                        help=f"series key (common.SERIES); {LATE_SERIES} is refused, use --composite {common.INTRADAY_T0_KEY}")
    source.add_argument("--composite", choices=[common.INTRADAY_T0_KEY],
                        help="composite windows: new_full for T-29..T-1, intraday_late (final_rush) at T+0")
    parser.add_argument("--symbol", required=True, choices=sorted(common.SYMBOL_START))
    parser.add_argument("--end-min", type=date.fromisoformat, metavar="YYYY-MM-DD", help="first window_end to build")
    parser.add_argument("--end-max", type=date.fromisoformat, metavar="YYYY-MM-DD",
                        help="last window_end to build (never later than the series cap)")
    parser.add_argument("--parquet-root", type=Path, default=common.PARQUET_ROOT, metavar="DIR",
                        help="folder holding series/ (read) and windows/ (written) (default: %(default)s)")
    parser.add_argument("--from-db", action="store_true",
                        help="read the series from backups.gex_llm_regime_series instead of the series parquet")
    parser.add_argument("--master-calendar", choices=("parquet", "db"), default=None,
                        help="where the symbol's master calendar for missing_master_days comes from: the new_full series "
                             "parquet, or gex.options_daily_summary (default: db with --from-db, otherwise parquet)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--db", action="store_true", help="also upsert the windows into backups.gex_llm_regime_windows")
    output.add_argument("--parquet-only", action="store_true", help="write the parquet file only (the default)")
    output.add_argument("--rollback", action="store_true",
                        help="test the Postgres path: apply the schema inline, upsert twice, verify, roll back; writes nothing")
    parser.add_argument("--ignore-busy-window", action="store_true",
                        help="allow --db/--rollback between 21:50 and 22:45 UTC (the daily ingest and summary cron)")
    args = parser.parse_args(argv)
    if args.series == LATE_SERIES:
        parser.error(f"{LATE_SERIES} holds one row per intraday day, so it has no 30-row windows; use --composite "
                     f"{common.INTRADAY_T0_KEY} (new_full T-29..T-1 plus the {LATE_SERIES} value at T+0)")
    for key in ((BASE_SERIES, LATE_SERIES) if args.composite else (args.series,)):
        if args.symbol not in common.SERIES[key].symbols:
            parser.error(f"series {key} is defined for {', '.join(common.SERIES[key].symbols)} only")
    if args.end_min and args.end_max and args.end_min > args.end_max:
        parser.error("--end-min is after --end-max")
    if args.master_calendar is None:
        args.master_calendar = "db" if args.from_db else "parquet"
    return args


def run(args: argparse.Namespace) -> int:
    if args.db or args.rollback:
        try:
            common.assert_not_quiet(args.ignore_busy_window)
        except RuntimeError as exc:
            raise WindowBuildError(str(exc)) from None
    series_key = common.INTRADAY_T0_KEY if args.composite else args.series
    inputs = (BASE_SERIES, LATE_SERIES) if args.composite else (series_key,)
    end_max = min([common.SERIES[key].end for key in inputs] + ([args.end_max] if args.end_max else []))

    frames = load_inputs(inputs, args.symbol, args.from_db, args.parquet_root, end_max)
    if args.composite:
        rule, labels = RULE_COMPOSITE, "obfuscated"
        specs = composite_windows(frames[BASE_SERIES], frames[LATE_SERIES], args.end_min, end_max)
    else:
        series = common.SERIES[series_key]
        rule, labels = (RULE_OWN_CALENDAR if series.calendar == "self" else common.WINDOW_RULE), series.labels
        specs = consecutive_windows(frames[series_key], args.end_min, end_max)
    if not specs:
        raise WindowBuildError(f"no {series_key}/{args.symbol} window ends between {args.end_min or 'the start'} and {end_max}")
    if rule == RULE_OWN_CALENDAR:
        check_fidelity(series_key, specs, args.end_min, end_max)

    master, origin = read_master_calendar(args.symbol, args.master_calendar, args.parquet_root)
    check_master_covers(master, specs, origin)
    logger.info("master calendar %s: %d dates, %s .. %s", origin, len(master), master[0], master[-1])

    records = build_records(series_key, args.symbol, rule, labels, specs, master)
    by_year = detection_by_year(records)
    logger.info("built %d windows (rule %s, labels %s) ending %s .. %s; calendar_gap_days > %d: %d, missing_master_days > 0: %d, "
                "gap_flag: %d", len(records), rule, labels, records[0]["window_end"], records[-1]["window_end"],
                common.CALENDAR_GAP_FLAG_DAYS, by_year.loc["all", "cal_gap"], by_year.loc["all", "missing_master"],
                by_year.loc["all", "gap_flagged"])

    span = (args.end_min or date.min, end_max)
    if args.rollback:
        write_windows_db(records, span, rollback=True)
    else:
        if args.db:
            write_windows_db(records, span, rollback=False)
        path = table_path(args.parquet_root, "windows", series_key, args.symbol)
        logger.info("parquet %s: %d rows", path, write_parquet(records, path, span))

    print(f"\nDetection rate by window_end year (clf_should_detect), {series_key}/{args.symbol}, rule {rule}:")
    print(by_year.to_string())
    print(f"cal_gap = calendar_gap_days > {common.CALENDAR_GAP_FLAG_DAYS}; missing_master = missing_master_days > 0; "
          f"gap_flagged = either (windows are kept)")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    common.setup_logging()
    try:
        return run(args)
    except WindowBuildError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
