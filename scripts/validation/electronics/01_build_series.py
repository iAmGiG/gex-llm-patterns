#!/usr/bin/env python3
"""Build the daily GEX series behind the Electronics extension (gex-llm-patterns issue #261).

One run builds one (series, symbol) pair: one row per trading date with exactly the columns of
``backups.gex_llm_regime_series``.  The 30-day windows the model sees (``02_build_windows.py``) are cut from
these rows, so every number is stored once instead of being recomputed.

Series (``common.SERIES``)::

    jan2026_phase4a  daily values recovered from the 2026-01-04 o4-mini batch file (SPY, January calendar)
    old_bs           archive of the daily table as it was before the 2026-10-08 rebuild (SPY)
    new_full         gex.options_daily_summary after the 2026-10-08 rebuild: stored gamma, 0DTE included
    new_full_scaled  new_full of QQQ and IWM (2020 onwards) times one fixed per-symbol factor: the median ratio of
                     SPY to symbol open-interest notional (total_weighted_oi * 100 * underlying_price)
    new_ex0dte       raw gex.options_chains_partitioned with expiration > trading_date (0DTE removed)
    intraday_late    gex.intraday_gex_summary, snapshot_type final_rush, one row per ET date (SPY)
    call_only        diagnostic (SPY, 2020 onwards): call leg incl. 0DTE of the raw chains; like the January inputs
                     it has no put leg
    p3_2024          the November-2025 Phase 3 inputs (SPY 2024, 252 values), parsed from the surviving batch file
    p3_2024_dated    the same values; labels='dated' makes 02_build_windows show the real dates, as the 2025 prompts did
    p4_2020          the November-2025 Phase 4 inputs (SPY 2020, 252 values), parsed from the surviving batch file
    p4_2020_dated    the same values, dated labels

Output modes (at most one; without a flag the run is --parquet-only)::

    --parquet-only   write no database row (the default)
    --db             upsert into backups.gex_llm_regime_series on (series_key, symbol, trading_date); the
                     tables must already exist (apply sql/gex_llm_regime_schema.sql after maintainer approval)
    --rollback       dry run: run the schema SQL (BEGIN/COMMIT stripped) and the upsert in one transaction,
                     report the row count that WOULD have been written, roll back (works before the tables exist)

The parquet copy ``data/backups/gex_llm/tables/series/<series_key>_<symbol>.parquet`` is written in every mode.
A partial build (``--years``/``--start``/``--end``) replaces only its own dates in that file, as the upsert does;
rows it keeps from another version of this script (builder_sha256 in series_metadata) are reported.

Conventions
    * Values are USD, calls positive, puts negative.  ``call_gex``/``put_gex``/``gex_0dte``/``n_*`` are NULL
      where the source does not expose them (all of them for the file-based series jan2026_phase4a and
      p3_2024*/p4_2020*, which hold the printed total only).
    * Phase 3/4 series keep the printed values verbatim (0.01B precision, no sign correction): p3_2024 is negative on
      242 of 252 dates and p4_2020 positive on all 252 (series_metadata records the counts and the batch id).  The
      plain and ``_dated`` keys of one phase hold identical rows; ``series_metadata.labels`` says how the November
      2025 prompts labelled the days ('dated') or how the rerun will ('obfuscated').
    * new_full_scaled multiplies net/call/put GEX of new_full by one factor per symbol, computed over the whole
      registry range (2020-01-01 .. 2026-10-09) whatever dates are built, and stored in every row's
      series_metadata (scale, factor, n_days); ``spot`` stays the symbol's own price.  The factor is the median of
      the daily SPY/symbol ratios of total_weighted_oi * 100 * underlying_price, both columns widened exactly with
      ::float8, so SQL percentile_cont(0.5) over the same expression returns it bit for bit.
    * Raw chains: sign * gamma * open_interest * 100 * underlying_price^2 * 0.01 over contracts with
      gamma IS NOT NULL AND open_interest > 0 AND underlying_price > 0, summed in float8.  new_ex0dte keeps
      expiration > trading_date for net/call/put/n_contracts; gex_0dte/n_0dte are the same-day expiries
      (0.0/0 on days without any).  SPY, QQQ and IWM hold no expiration < trading_date rows through
      2026-10-09, so ex-0DTE + 0DTE is the whole chain; a day that breaks this is flagged in series_metadata.
    * gex.options_daily_summary (and the archive) store float4: total/call/put GEX are widened exactly with
      ::float8, ``spot`` is the decimal text of the real column (509.83, not 509.8299865722656).  new_full therefore
      matches new_ex0dte + gex_0dte to about 1e-7 of the day's gross exposure |call| + |put|; relative to |net| the
      gap reaches ~5e-5 on near-flat days.
    * Every series stops at its registry end (common.WINDOW_END_CAP unless the registry says otherwise).
    * Raw chains (new_ex0dte, call_only and the calendar of jan2026_phase4a) are read one symbol-year per statement
      with the index plan and without parallel workers (SET LOCAL enable_seqscan = off, SET LOCAL
      max_parallel_workers_per_gather = 0: partial sums combined in a varying order would change the last digits
      of the float8 sums from run to run), and never between 21:50 and 22:45 UTC; --db and --rollback obey the
      same window.  Every source read uses a read-only session.

Run from the repository root with the AutoGex conda env::

    source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
    PYTHONPATH=$(pwd) python scripts/validation/electronics/01_build_series.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

import common

log = logging.getLogger("electronics.build_series")

SCRIPT_NAME = Path(__file__).name
APPLICATION_NAME = "gex-llm-patterns 01_build_series"
STATEMENT_TIMEOUT = "600s"
JAN_CALENDAR_LOOKBACK_DAYS = 90  # 29 trading days span ~45 calendar days; the slack covers holiday clusters

# --------------------------------------------------------------------------- table layout (the contract)
COLUMNS: Tuple[str, ...] = (
    "series_key",
    "symbol",
    "trading_date",
    "net_gex",
    "call_gex",
    "put_gex",
    "gex_0dte",
    "n_contracts",
    "n_0dte",
    "spot",
    "source_table",
    "source_timestamp",
    "series_metadata",
    "created_at",
)
NATURAL_KEY: Tuple[str, ...] = ("series_key", "symbol", "trading_date")
FLOAT_COLUMNS: Tuple[str, ...] = ("net_gex", "call_gex", "put_gex", "gex_0dte", "spot")
INT_COLUMNS: Tuple[str, ...] = ("n_contracts", "n_0dte")
VALUE_COLUMNS: Tuple[str, ...] = FLOAT_COLUMNS + INT_COLUMNS + ("source_timestamp",)

# Every series, including call_only (SPY, from 2020-01-01), new_full_scaled and the Phase 3/4 inputs, is defined in the
# shared contract; this script only supplies the builders.
SERIES_REGISTRY: Dict[str, common.Series] = dict(common.SERIES)
# Series that read gex.options_chains_partitioned (jan2026_phase4a only its trading-date calendar): quiet-window rule.
RAW_SCAN_SERIES = ("jan2026_phase4a", "new_ex0dte", "call_only")
# Planner settings applied (SET LOCAL) to every raw-chain statement and recorded in series_metadata.
RAW_PLANNER_SETTINGS: Dict[str, str] = {"enable_seqscan": "off", "max_parallel_workers_per_gather": "0"}

Span = Tuple[date, date]  # inclusive, inside one calendar year

# --------------------------------------------------------------------------- SQL
SQL_DAILY_SUMMARY = """
SELECT trading_date,
       total_gex::float8    AS net_gex,
       net_call_gex::float8 AS call_gex,
       net_put_gex::float8  AS put_gex,
       underlying_price     AS spot
FROM {table}
WHERE symbol = %(symbol)s AND trading_date BETWEEN %(lo)s AND %(hi)s
ORDER BY trading_date
"""

SQL_OI_NOTIONAL_INPUTS = """
SELECT trading_date,
       total_weighted_oi::float8 AS open_interest,
       underlying_price::float8  AS price
FROM gex.options_daily_summary
WHERE symbol = %(symbol)s AND trading_date BETWEEN %(lo)s AND %(hi)s
ORDER BY trading_date
"""

SQL_RAW_GEX = """
SELECT trading_date,
       sum(gex) FILTER (WHERE expiration > trading_date)                                           AS net_gex,
       coalesce(sum(gex) FILTER (WHERE option_type = 'call' AND expiration > trading_date), 0.0::float8) AS call_gex,
       coalesce(sum(gex) FILTER (WHERE option_type = 'put'  AND expiration > trading_date), 0.0::float8) AS put_gex,
       count(*)  FILTER (WHERE expiration > trading_date)                                          AS n_contracts,
       coalesce(sum(gex) FILTER (WHERE expiration = trading_date), 0.0::float8)                    AS gex_0dte,
       count(*)  FILTER (WHERE expiration = trading_date)                                          AS n_0dte,
       sum(gex)  FILTER (WHERE option_type = 'call')                                               AS call_all,
       count(*)  FILTER (WHERE option_type = 'call')                                               AS n_call_all,
       coalesce(sum(gex) FILTER (WHERE option_type = 'call' AND expiration = trading_date), 0.0::float8) AS call_0dte,
       count(*)  FILTER (WHERE option_type = 'call' AND expiration = trading_date)                 AS n_call_0dte,
       count(*)  FILTER (WHERE expiration < trading_date)                                          AS n_expired,
       max(underlying_price)                                                                       AS spot
FROM (SELECT trading_date, expiration, option_type, underlying_price,
             CASE WHEN option_type = 'call' THEN 1.0 ELSE -1.0 END
               * gamma::float8 * open_interest::float8 * 100.0
               * underlying_price::float8 * underlying_price::float8 * 0.01 AS gex
      FROM gex.options_chains_partitioned
      WHERE symbol = %(symbol)s AND trading_date BETWEEN %(lo)s AND %(hi)s
        AND gamma IS NOT NULL AND open_interest > 0 AND underlying_price > 0) AS t
GROUP BY trading_date
ORDER BY trading_date
"""

SQL_RAW_CALENDAR = """
SELECT DISTINCT trading_date
FROM gex.options_chains_partitioned
WHERE symbol = %(symbol)s AND trading_date BETWEEN %(lo)s AND %(hi)s
ORDER BY trading_date
"""

SQL_MASTER_CALENDAR = """
SELECT trading_date
FROM gex.options_daily_summary
WHERE symbol = %(symbol)s AND trading_date BETWEEN %(lo)s AND %(hi)s
ORDER BY trading_date
"""

SQL_INTRADAY = """
SELECT DISTINCT ON (et_date)
       et_date                  AS trading_date,
       snapshot_timestamp       AS source_timestamp,
       total_gex::float8        AS net_gex,
       net_call_gex::float8     AS call_gex,
       net_put_gex::float8      AS put_gex,
       underlying_price::float8 AS spot,
       total_contracts          AS n_contracts
FROM (SELECT *, (snapshot_timestamp AT TIME ZONE 'America/New_York')::date AS et_date
      FROM gex.intraday_gex_summary
      WHERE symbol = %(symbol)s AND snapshot_type = %(snapshot_type)s
        AND snapshot_timestamp >= %(ts_lo)s AND snapshot_timestamp < %(ts_hi)s) AS s
WHERE et_date BETWEEN %(lo)s AND %(hi)s
ORDER BY et_date, snapshot_timestamp DESC
"""

RAW_GEX_FORMULA = "sign * gamma * open_interest * 100 * underlying_price^2 * 0.01 in float8, call +, put -"
RAW_ROW_FILTER = "gamma IS NOT NULL AND open_interest > 0 AND underlying_price > 0"
OLD_BS_CAVEAT = (
    "Archive computed 2026-01-15 from a raw table whose put rows were missing from about 2023-10 to "
    "2025-12 (upstream issue #24): put_gex is incomplete there and net_gex is call-only"
)


# --------------------------------------------------------------------------- database access
def open_source():
    """Connection for every source read: read-only session, long statement timeout, labelled for the DBA."""
    conn = common.connect()
    conn.set_session(readonly=True)
    with conn.cursor() as cur:
        cur.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT}'")
        cur.execute(f"SET application_name = '{APPLICATION_NAME}'")
    conn.commit()
    return conn


def query(conn, sql: str, params: Dict[str, Any], *, index_scan: bool = False) -> pd.DataFrame:
    """Run one SELECT in its own transaction.

    ``index_scan`` (raw-chain statements) applies RAW_PLANNER_SETTINGS to that transaction only: the index plan, and
    no parallel workers so that the float8 sums are accumulated in a fixed order (bit-reproducible results).
    """
    try:
        with conn.cursor() as cur:
            if index_scan:
                for name, value in RAW_PLANNER_SETTINGS.items():
                    cur.execute(f"SET LOCAL {name} = {value}")
            cur.execute(sql, params)
            columns = [c.name for c in cur.description]
            rows = cur.fetchall()
    finally:
        conn.rollback()
    return pd.DataFrame(rows, columns=columns)


def query_spans(
    conn, sql: str, symbol: str, spans: Sequence[Span], label: str, *, index_scan: bool = False
) -> pd.DataFrame:
    """Run ``sql`` once per span (one symbol-year per statement) and log the timing of each."""
    frames = []
    for lo, hi in spans:
        started = time.perf_counter()
        frame = query(conn, sql, {"symbol": symbol, "lo": lo, "hi": hi}, index_scan=index_scan)
        log.info("%s %s %d: %d days in %.2f s", label, symbol, lo.year, len(frame), time.perf_counter() - started)
        frames.append(frame)
    non_empty = [f for f in frames if len(f)]
    return pd.concat(non_empty, ignore_index=True) if non_empty else frames[-1]


def raw_calendar(conn, symbol: str, lo: date, hi: date) -> List[date]:
    """Distinct trading dates of the raw chains (one symbol-year per statement, index plan)."""
    days: List[date] = []
    for span_lo, span_hi in year_spans(lo, hi):
        frame = query(conn, SQL_RAW_CALENDAR, {"symbol": symbol, "lo": span_lo, "hi": span_hi}, index_scan=True)
        days.extend(frame["trading_date"])
    return days


def master_calendar(conn, symbol: str, spans: Sequence[Span]) -> List[date]:
    """Trading dates of ``symbol`` in gex.options_daily_summary (the 'master' calendar) inside the spans."""
    days: List[date] = []
    for lo, hi in spans:
        days.extend(query(conn, SQL_MASTER_CALENDAR, {"symbol": symbol, "lo": lo, "hi": hi})["trading_date"])
    return days


# --------------------------------------------------------------------------- ranges
def year_spans(start: date, end: date, years: Optional[Sequence[int]] = None) -> List[Span]:
    """Split [start, end] into one inclusive span per calendar year, optionally only the given years."""
    return [
        (max(start, date(y, 1, 1)), min(end, date(y, 12, 31)))
        for y in range(start.year, end.year + 1)
        if not years or y in years
    ]


def resolve_spans(
    series: common.Series, symbol: str, start: Optional[date], end: Optional[date], years: Optional[Sequence[int]]
) -> List[Span]:
    """Requested range clipped to the series' validity window (registry start/end, symbol start, cap)."""
    floor = series.start or common.SYMBOL_START[symbol]
    if start and start < floor:
        log.warning("--start %s is before %s data begin (%s); clipped", start, series.key, floor)
    if end and end > series.end:
        log.warning("--end %s is after the %s cap (%s); clipped", end, series.key, series.end)
    lo, hi = max(start or floor, floor), min(end or series.end, series.end)
    spans = year_spans(lo, hi, years) if lo <= hi else []
    if not spans:
        raise SystemExit(
            f"nothing to build: {series.key} {symbol} has no dates in {lo}..{hi}"
            + (f" for years {sorted(years)}" if years else "")
        )
    return spans


def keep_spans(frame: pd.DataFrame, spans: Sequence[Span]) -> pd.DataFrame:
    """Rows whose date (the index) lies in one of the spans."""
    inside = [any(lo <= d <= hi for lo, hi in spans) for d in frame.index]
    return frame[inside]


def check_quiet_window(series_key: str, writes_db: bool, override: bool, now: Optional[datetime] = None) -> None:
    """Refuse heavy raw scans and DDL/upserts while the monitors rebuild the daily tables (common.in_quiet_window)."""
    if override or not (series_key in RAW_SCAN_SERIES or writes_db):
        return
    if common.in_quiet_window(now):
        (h0, m0), (h1, m1) = common.QUIET_WINDOW_UTC
        raise SystemExit(
            f"refusing to run between {h0:02d}:{m0:02d} and {h1:02d}:{m1:02d} UTC "
            f"(daily rebuild of the monitors); rerun later or pass --ignore-busy-window"
        )


# --------------------------------------------------------------------------- builders
@dataclass
class Built:
    """What a builder returns: per-day values (index = trading date) and the provenance shared by all rows.

    ``frame`` holds a subset of VALUE_COLUMNS plus, optionally, ``flags``: a dict of per-day notes (or None)
    that is merged into series_metadata.
    """

    frame: pd.DataFrame
    meta: Dict[str, Any]


Builder = Callable[[Any, common.Series, str, List[Span]], Built]


def base_meta(series: common.Series, sql_id: str, sql: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    """Build parameters stored in every row's series_metadata (source identity, caps, convention, label style).

    ``sql`` is the text of the statements the builder runs (hashed with whitespace collapsed); file-based
    builders pass none and record the hash of their input file instead.
    """
    meta: Dict[str, Any] = {
        "builder": SCRIPT_NAME,
        "builder_sha256": common.sha256_file(Path(__file__))[:12],
        "git_sha": common.git_sha()[:12],
        "sql_id": sql_id,
        "end_cap": series.end,
        "convention": series.description,
        "labels": series.labels,
    }
    if sql is not None:
        meta["sql_sha256"] = hashlib.sha256(" ".join(sql.split()).encode()).hexdigest()[:16]
    if series.scale:
        meta["scale"] = series.scale
    meta.update(extra)
    return meta


def drop_non_finite(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """Drop days without a finite net_gex (the column is NOT NULL and a NaN would reach the model as text)."""
    bad = ~np.isfinite(frame["net_gex"].astype("float64"))
    if bad.any():
        log.warning(
            "%s: dropping %d day(s) without a finite net_gex: %s", label, int(bad.sum()), fmt_dates(frame.index[bad])
        )
    return frame[~bad]


def fmt_dates(dates: Sequence[date], limit: int = 6) -> str:
    shown = ", ".join(d.isoformat() for d in list(dates)[:limit])
    return shown + (f" ... (+{len(dates) - limit} more)" if len(dates) > limit else "")


def build_jan2026(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """Daily values of the published run: the window ends of the batch file plus the 29 days before the first.

    The batch file holds 30-day windows, so the days before the first window end are dated from today's raw
    calendar (verified identical to the summary calendar there).  Later dates are the window ends themselves,
    which is why the series lacks the days the January table lacked.
    """
    windows = common.load_phase4a_inputs()
    first_end = min(windows)
    lookback_start = first_end - timedelta(days=JAN_CALENDAR_LOOKBACK_DAYS)
    started = time.perf_counter()
    calendar = raw_calendar(conn, symbol, lookback_start, first_end)
    summary_calendar = master_calendar(conn, symbol, year_spans(lookback_start, first_end))
    log.info(
        "%s %s: calendar before the first window end read in %.2f s", series.key, symbol, time.perf_counter() - started
    )
    if first_end not in calendar or calendar.index(first_end) < common.WINDOW_DAYS - 1:
        raise RuntimeError(f"raw calendar of {symbol} lacks {common.WINDOW_DAYS - 1} trading days before {first_end}")
    if calendar != summary_calendar:
        raise RuntimeError(
            f"raw and summary calendars of {symbol} differ in {lookback_start}..{first_end}; "
            f"the dates of the first {common.WINDOW_DAYS - 1} values would be ambiguous"
        )
    daily = common.phase4a_daily_series(calendar)
    expected = len(windows) + common.WINDOW_DAYS - 1
    if len(daily) != expected:
        raise RuntimeError(
            f"expected {expected} daily values ({len(windows)} windows + {common.WINDOW_DAYS - 1}), "
            f"got {len(daily)}"
        )
    absent = sorted(set(master_calendar(conn, symbol, year_spans(min(daily), max(daily)))) - set(daily))
    meta = base_meta(
        series,
        "phase4a_batch_v1",
        SQL_RAW_CALENDAR + SQL_MASTER_CALENDAR,
        batch_id=common.PHASE4A_BATCH_ID,
        windows_in_batch=len(windows),
        first_window_end=first_end,
        dates_before_first_window_end="trading dates of gex.options_chains_partitioned (equal to the summary calendar)",
        calendar_absent_vs_summary=absent,
        precision="values were printed at 0.01B; net_gex = float(text) * 1e9 as parsed by common.load_phase4a_inputs",
    )
    return Built(pd.DataFrame({"net_gex": pd.Series(daily, dtype="float64")}), meta)


DAILY_SUMMARY_COLUMNS: Dict[str, str] = {
    "net_gex": "total_gex",
    "call_gex": "net_call_gex",
    "put_gex": "net_put_gex",
    "spot": "underlying_price",
}
SCALED_COLUMNS: Tuple[str, ...] = ("net_gex", "call_gex", "put_gex")  # spot is a price and stays unscaled
PHASE34_NOTES: Dict[str, str] = {  # what the November-2025 prompts printed (second-audit memo, 2026-10-28)
    "p3_2024": (
        "gross call+put magnitude ex-0DTE with a negative sign imposed; the non-negative dates are placeholder "
        "rows backfilled into the November 2025 database"
    ),
    "p4_2020": "magnitude-only open-interest based series, positive on every date",
}


def build_daily_summary(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """old_bs (archive) and new_full (live table): both read total/call/put GEX and the underlying price."""
    sql = SQL_DAILY_SUMMARY.format(table=series.source_table)
    frame = query_spans(conn, sql, symbol, spans, series.key).set_index("trading_date")
    extra: Dict[str, Any] = {"columns": DAILY_SUMMARY_COLUMNS}
    if series.key == "old_bs":
        extra["caveat"] = OLD_BS_CAVEAT
    return Built(drop_non_finite(frame, f"{series.key} {symbol}"), base_meta(series, "daily_summary_v1", sql, **extra))


def oi_notional_factor(conn, series: common.Series, symbol: str) -> Dict[str, Any]:
    """Median over the series' whole registry range of the daily SPY / symbol open-interest notional ratio.

    Notional = total_weighted_oi * 100 * underlying_price of gex.options_daily_summary; a day counts when both
    symbols have a positive notional.  The window is the registry range, not the dates being built, so a partial
    build carries the factor of a full one.
    """
    if series.scale != "oi_notional":
        raise ValueError(f"{series.key}: unsupported scale {series.scale!r}")
    lo, hi = series.start or common.SYMBOL_START[symbol], series.end
    spans = year_spans(lo, hi)
    notional: Dict[str, pd.Series] = {}
    for name in ("SPY", symbol):
        frame = query_spans(conn, SQL_OI_NOTIONAL_INPUTS, name, spans, f"{series.key} oi_notional")
        oi = pd.to_numeric(frame["open_interest"], errors="coerce").astype("float64").to_numpy()
        price = pd.to_numeric(frame["price"], errors="coerce").astype("float64").to_numpy()
        notional[name] = pd.Series(oi * 100.0 * price, index=pd.Index(list(frame["trading_date"]), dtype=object))
    joined = pd.concat({"spy": notional["SPY"], "symbol": notional[symbol]}, axis=1, join="inner")
    usable = (joined["spy"] > 0) & (joined["symbol"] > 0) & np.isfinite(joined["spy"]) & np.isfinite(joined["symbol"])
    ratio = (joined["spy"] / joined["symbol"])[usable]
    if ratio.empty:
        raise RuntimeError(
            f"{series.key} {symbol}: no day in {lo}..{hi} with a positive open-interest notional for SPY and {symbol}"
        )
    q_min, q25, q75, q_max = (float(x) for x in np.quantile(ratio.to_numpy(), [0.0, 0.25, 0.75, 1.0]))
    out = {
        "factor": float(np.median(ratio.to_numpy())),
        "n_days": int(len(ratio)),
        "n_days_dropped": int(len(joined) - len(ratio)),
        "factor_window": [lo, hi],
        "factor_first_day": min(ratio.index),
        "factor_last_day": max(ratio.index),
        "factor_definition": (
            "median over the days present for both symbols of (SPY total_weighted_oi * 100 * underlying_price) / "
            "(symbol total_weighted_oi * 100 * underlying_price), gex.options_daily_summary"
        ),
        "ratio_min": q_min,
        "ratio_p25": q25,
        "ratio_p75": q75,
        "ratio_max": q_max,
    }
    log.info(
        "%s %s: oi_notional factor %.6f = median of %d daily SPY/%s ratios (%s .. %s; "
        "min %.3f p25 %.3f p75 %.3f max %.3f)",
        series.key,
        symbol,
        out["factor"],
        out["n_days"],
        symbol,
        out["factor_first_day"],
        out["factor_last_day"],
        q_min,
        q25,
        q75,
        q_max,
    )
    return out


def build_scaled_daily_summary(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """new_full of the symbol times its fixed open-interest-notional factor (net/call/put GEX only).

    The summary table has no 0DTE split or contract counts, so those columns stay NULL as in new_full.
    """
    scale = oi_notional_factor(conn, series, symbol)
    sql = SQL_DAILY_SUMMARY.format(table=series.source_table)
    frame = query_spans(conn, sql, symbol, spans, series.key).set_index("trading_date")
    for column in SCALED_COLUMNS:
        frame[column] = frame[column] * scale["factor"]
    meta = base_meta(
        series,
        "daily_summary_scaled_v1",
        sql + SQL_OI_NOTIONAL_INPUTS,
        base_series="new_full",
        columns=DAILY_SUMMARY_COLUMNS,
        scaled_columns=list(SCALED_COLUMNS),
        spot_note="the symbol's own underlying_price, not scaled",
        **scale,
    )
    return Built(drop_non_finite(frame, f"{series.key} {symbol}"), meta)


def build_phase34(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """Daily values of a November-2025 Phase 3/4 input file (SPY): the days of the windows sent to o4-mini.

    The batch file holds one prompt per window end with its 30 dated values at 0.01B precision.  Consecutive
    windows overlap in 29 days, so their union is one daily series of ``windows + 29`` values (checked); values
    printed twice must agree (common.phase34_daily_series).  The plain and the ``_dated`` key hold identical
    rows; they differ in series_metadata.labels only.
    """
    base_key = series.key.removesuffix("_dated")
    input_path, _output_path, batch_id = common.PHASE34_FILES[base_key]
    if not input_path.is_file():
        raise SystemExit(f"{series.key}: input file {input_path.relative_to(common.REPO_ROOT)} not found")
    windows = common.load_phase34_inputs(series.key)
    daily = common.phase34_daily_series(series.key)
    expected = len(windows) + common.WINDOW_DAYS - 1
    if len(daily) != expected:
        raise RuntimeError(
            f"{series.key}: expected {expected} daily values ({len(windows)} windows + {common.WINDOW_DAYS - 1}), "
            f"got {len(daily)}; the windows of {input_path.name} are not consecutive"
        )
    lo = series.start or common.SYMBOL_START[symbol]
    beyond = sorted(d for d in daily if not lo <= d <= series.end)
    if beyond:
        raise RuntimeError(
            f"{series.key}: {len(beyond)} date(s) of {input_path.name} lie outside the registry range "
            f"{lo}..{series.end}: {fmt_dates(beyond)}"
        )
    values = pd.Series(daily, dtype="float64")
    master = set(master_calendar(conn, symbol, year_spans(min(daily), max(daily))))
    meta = base_meta(
        series,
        "phase34_batch_v1",
        batch_id=batch_id,
        source_file=str(input_path.relative_to(common.REPO_ROOT)),
        source_file_sha256=common.sha256_file(input_path),
        windows_in_batch=len(windows),
        first_window_end=min(windows),
        last_window_end=max(windows),
        n_values=len(daily),
        n_negative=int((values < 0).sum()),
        n_positive=int((values > 0).sum()),
        n_zero=int((values == 0).sum()),
        sign_convention=PHASE34_NOTES[base_key],
        same_values_as=base_key if series.key.endswith("_dated") else base_key + "_dated",
        precision="values were printed at 0.01B; net_gex = float(text) * 1e9 as parsed by common.load_phase34_inputs; "
        "values printed in several windows agree within 0.006B",
        calendar_absent_vs_summary=sorted(master - set(daily)),
        calendar_outside_summary=sorted(set(daily) - master),
    )
    return Built(pd.DataFrame({"net_gex": values}), meta)


def fetch_raw(conn, series: common.Series, symbol: str, spans: List[Span]) -> pd.DataFrame:
    """Per-day aggregates of the raw chains for every leg either raw series needs (one statement per symbol-year)."""
    raw = query_spans(conn, SQL_RAW_GEX, symbol, spans, series.key, index_scan=True).set_index("trading_date")
    expired = raw["n_expired"] > 0
    if expired.any():
        log.warning(
            "%s %s: %d day(s) hold contracts with expiration < trading_date, which belong to neither the "
            "ex-0DTE nor the 0DTE leg: %s",
            series.key,
            symbol,
            int(expired.sum()),
            fmt_dates(raw.index[expired]),
        )
    raw["flags"] = pd.Series(
        [{"n_expired_contracts": int(n)} if n else None for n in raw["n_expired"]], index=raw.index, dtype=object
    )
    return raw


def raw_meta(series: common.Series, **extra: Any) -> Dict[str, Any]:
    return base_meta(
        series,
        "raw_gex_v1",
        SQL_RAW_GEX,
        source_scan="one symbol-year per statement",
        planner=dict(RAW_PLANNER_SETTINGS),
        gex_formula=RAW_GEX_FORMULA,
        row_filter=RAW_ROW_FILTER,
        **extra,
    )


def build_new_ex0dte(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """Net/call/put GEX of the contracts expiring after the trading date; the same-day expiries sit in gex_0dte."""
    raw = fetch_raw(conn, series, symbol, spans)
    frame = raw[["net_gex", "call_gex", "put_gex", "gex_0dte", "n_contracts", "n_0dte", "spot", "flags"]]
    meta = raw_meta(
        series,
        ex0dte_rule="net/call/put/n_contracts over expiration > trading_date; "
        "gex_0dte/n_0dte over expiration = trading_date",
    )
    return Built(drop_non_finite(frame, f"{series.key} {symbol}"), meta)


def build_call_only(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """Call leg of every contract (0DTE included) with the put leg dropped: the shape of the January inputs."""
    raw = fetch_raw(conn, series, symbol, spans)
    frame = pd.DataFrame(
        {
            "net_gex": raw["call_all"],
            "call_gex": raw["call_all"],
            "gex_0dte": raw["call_0dte"],
            "n_contracts": raw["n_call_all"],
            "n_0dte": raw["n_call_0dte"],
            "spot": raw["spot"],
            "flags": raw["flags"],
        }
    )
    meta = raw_meta(
        series,
        leg="call rows only, all expirations incl. 0DTE; put_gex NULL; "
        "gex_0dte/n_0dte/n_contracts count call rows only",
    )
    return Built(drop_non_finite(frame, f"{series.key} {symbol}"), meta)


def build_intraday(conn, series: common.Series, symbol: str, spans: List[Span]) -> Built:
    """Last independent late-session snapshot (final_rush) of each ET date, minus the audited irregular days."""
    lo, hi = spans[0][0], spans[-1][1]
    params = {
        "symbol": symbol,
        "snapshot_type": common.INTRADAY_SNAPSHOT_TYPE,
        "lo": lo,
        "hi": hi,
        "ts_lo": datetime.combine(lo - timedelta(days=1), dtime.min, tzinfo=timezone.utc),
        "ts_hi": datetime.combine(hi + timedelta(days=2), dtime.min, tzinfo=timezone.utc),
    }
    started = time.perf_counter()
    frame = query(conn, SQL_INTRADAY, params)
    log.info("%s %s: %d ET dates in %.2f s", series.key, symbol, len(frame), time.perf_counter() - started)
    irregular = frame["trading_date"].isin(common.INTRADAY_EXCLUDE_DAYS)
    if irregular.any():
        log.info(
            "%s %s: excluding irregular days %s", series.key, symbol, fmt_dates(list(frame["trading_date"][irregular]))
        )
    frame = frame[~irregular].set_index("trading_date")
    meta = base_meta(
        series,
        "intraday_final_rush_v1",
        SQL_INTRADAY,
        snapshot_type=common.INTRADAY_SNAPSHOT_TYPE,
        date_basis="America/New_York date of snapshot_timestamp; latest snapshot of that type per date",
        excluded_irregular_days=list(common.INTRADAY_EXCLUDE_DAYS),
    )
    return Built(drop_non_finite(frame, f"{series.key} {symbol}"), meta)


BUILDERS: Dict[str, Builder] = {
    "jan2026_phase4a": build_jan2026,
    "old_bs": build_daily_summary,
    "new_full": build_daily_summary,
    "new_full_scaled": build_scaled_daily_summary,
    "new_ex0dte": build_new_ex0dte,
    "intraday_late": build_intraday,
    "call_only": build_call_only,
    "p3_2024": build_phase34,
    "p3_2024_dated": build_phase34,
    "p4_2020": build_phase34,
    "p4_2020_dated": build_phase34,
}


# --------------------------------------------------------------------------- frame assembly and persistence
def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Column order and dtypes of backups.gex_llm_regime_series; parquet and database rows both start here."""
    out = df.reindex(columns=COLUMNS).copy()
    out["trading_date"] = pd.to_datetime(out["trading_date"]).dt.date
    out[list(FLOAT_COLUMNS)] = out[list(FLOAT_COLUMNS)].astype("float64")
    out[list(INT_COLUMNS)] = out[list(INT_COLUMNS)].astype("Int64")
    for column in ("source_timestamp", "created_at"):
        out[column] = pd.to_datetime(out[column], utc=True).astype("datetime64[us, UTC]")
    return out


def assemble(
    series: common.Series, symbol: str, built: Built, spans: Sequence[Span], created_at: datetime
) -> pd.DataFrame:
    """Turn a builder's output into rows with exactly the table's columns, restricted to the requested spans."""
    frame = keep_spans(built.frame, spans).sort_index()
    if frame.empty:
        raise SystemExit(f"{series.key} {symbol}: the source returned no rows in {spans[0][0]}..{spans[-1][1]}")
    if not frame.index.is_unique:
        raise ValueError(f"{series.key} {symbol}: duplicate trading dates in the source")
    flags = frame["flags"].tolist() if "flags" in frame else [None] * len(frame)
    out = frame.reindex(columns=VALUE_COLUMNS).rename_axis("trading_date").reset_index()
    out["series_key"] = series.key
    out["symbol"] = symbol
    out["source_table"] = series.source_table
    out["series_metadata"] = [
        common.dumps({**built.meta, **(f if isinstance(f, dict) else {})}, sort_keys=True) for f in flags
    ]
    out["created_at"] = created_at
    return coerce_types(out)


def metadata_builder_sha(metadata: Any) -> Optional[str]:
    """builder_sha256 recorded in one row's series_metadata (None when absent or unreadable)."""
    try:
        return json.loads(metadata).get("builder_sha256")
    except (TypeError, ValueError, AttributeError):
        return None


def write_parquet(frame: pd.DataFrame, spans: Sequence[Span]) -> Tuple[Path, pd.DataFrame]:
    """Merge the rows into the (series_key, symbol) parquet file, keyed like the table; returns (path, file content).

    A partial build leaves the other dates of the file untouched, so the caller reports the range of the whole file.
    Rows of the file inside the requested ``spans`` that the source no longer yields are kept (as an upsert would
    keep them) but reported, and so are kept rows written by another version of this script (a file that mixes
    versions, or an incomplete one from an interrupted run, is rebuilt over its whole range).
    """
    path = common.parquet_path("series", frame["series_key"].iat[0], frame["symbol"].iat[0])
    merged = frame
    if path.exists():
        previous = coerce_types(pd.read_parquet(path))
        rebuilt = previous["trading_date"].isin(frame["trading_date"])
        stale = [d for d in previous.loc[~rebuilt, "trading_date"] if any(lo <= d <= hi for lo, hi in spans)]
        if stale:
            log.warning(
                "%s keeps %d row(s) inside the rebuilt range that the source no longer yields: %s "
                "(delete the file for a clean rebuild)",
                path.name,
                len(stale),
                fmt_dates(stale),
            )
        kept = previous[~rebuilt]
        if len(kept):
            current = metadata_builder_sha(frame["series_metadata"].iat[0])
            by_hash = {text: metadata_builder_sha(text) for text in kept["series_metadata"].unique()}
            foreign = int((kept["series_metadata"].map(by_hash) != current).sum())
            if foreign:
                log.warning(
                    "%s keeps %d row(s) written by another version of this script (builder_sha256 %s; this build %s): "
                    "rebuild the whole range for a uniform file",
                    path.name,
                    foreign,
                    ", ".join(sorted({str(by_hash[text]) for text in by_hash if by_hash[text] != current})),
                    current,
                )
        merged = pd.concat([kept, frame], ignore_index=True) if len(kept) else frame
    merged = merged.sort_values("trading_date", kind="stable").reset_index(drop=True)
    partial = path.with_name(path.name + ".tmp")
    merged.to_parquet(partial, index=False)
    partial.replace(path)
    return path, merged


_TRANSACTION_CONTROL = re.compile(r"^[ \t]*(?:BEGIN|COMMIT)[ \t]*;[ \t]*$", re.IGNORECASE | re.MULTILINE)


def schema_sql_without_transaction_control() -> str:
    """The schema file minus its own BEGIN;/COMMIT; so it can run inside the dry-run transaction."""
    sql, removed = _TRANSACTION_CONTROL.subn("", common.SCHEMA_SQL.read_text())
    if removed != 2:
        raise RuntimeError(f"{common.SCHEMA_SQL.name}: expected one BEGIN; and one COMMIT;, found {removed} statements")
    return sql


def db_rows(frame: pd.DataFrame) -> List[Tuple[Any, ...]]:
    """Python-native tuples in COLUMNS order for psycopg2 (NaN/NaT/NA become None)."""
    columns = frame[list(COLUMNS)]
    return list(columns.astype(object).where(columns.notna(), None).itertuples(index=False, name=None))


def write_db(frame: pd.DataFrame, *, rollback: bool) -> Tuple[int, int]:
    """Upsert the rows; with ``rollback`` create the schema inside the transaction and discard everything.

    Returns (rows sent, rows of this series_key/symbol in the table at the end of the transaction).
    """
    series_key, symbol = frame["series_key"].iat[0], frame["symbol"].iat[0]
    dst = common.connect()
    try:
        with dst.cursor() as cur:
            cur.execute(f"SET statement_timeout = '{STATEMENT_TIMEOUT}'")
            cur.execute(f"SET application_name = '{APPLICATION_NAME}'")
            if rollback:
                cur.execute(schema_sql_without_transaction_control())
            else:
                cur.execute("SELECT to_regclass(%s)", (common.T_SERIES,))
                if cur.fetchone()[0] is None:
                    raise SystemExit(
                        f"{common.T_SERIES} does not exist: apply {common.SCHEMA_SQL.relative_to(common.REPO_ROOT)} "
                        f"after maintainer approval, or use --rollback / --parquet-only"
                    )
        sent = common.upsert_rows(dst, common.T_SERIES, COLUMNS, db_rows(frame), NATURAL_KEY)
        with dst.cursor() as cur:
            cur.execute(
                f"SELECT count(*) FROM {common.T_SERIES} WHERE series_key = %s AND symbol = %s", (series_key, symbol)
            )
            stored = cur.fetchone()[0]
        if rollback:
            dst.rollback()
        else:
            dst.commit()
        return sent, stored
    except BaseException:
        dst.rollback()
        raise
    finally:
        dst.close()


# --------------------------------------------------------------------------- command line
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    listing = "\n".join(f"  {key:16s} {s.description}" for key, s in SERIES_REGISTRY.items())
    parser = argparse.ArgumentParser(
        description="Build one daily GEX series for backups.gex_llm_regime_series (gex-llm-patterns #261).",
        epilog=(
            "series:\n" + listing + "\n\nexamples:\n"
            "  01_build_series.py --series new_full --symbol SPY --parquet-only\n"
            "  01_build_series.py --series new_full_scaled --symbol QQQ\n"
            "  01_build_series.py --series p3_2024_dated --symbol SPY\n"
            "  01_build_series.py --series new_ex0dte --symbol QQQ --years 2024 2025 --rollback\n"
            "  01_build_series.py --series intraday_late --symbol SPY --db"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--series", required=True, choices=list(SERIES_REGISTRY), help="series to build")
    parser.add_argument(
        "--symbol", required=True, type=str.upper, help="SPY, QQQ or IWM (the symbols a series supports are checked)"
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="first trading date (default: start of the series for the symbol)",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="last trading date (default and maximum: the series' cap)",
    )
    parser.add_argument("--years", type=int, nargs="+", metavar="YYYY", help="only these calendar years")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--parquet-only", action="store_true", help="write the parquet copy only (the default when no mode is given)"
    )
    mode.add_argument(
        "--db", action="store_true", help="also upsert into backups.gex_llm_regime_series (the table must exist)"
    )
    mode.add_argument(
        "--rollback",
        action="store_true",
        help="dry run: schema SQL + upsert in one transaction, print the row count, roll back",
    )
    parser.add_argument(
        "--ignore-busy-window",
        action="store_true",
        help="allow raw scans and database writes between 21:50 and 22:45 UTC",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args(argv)
    if args.series not in BUILDERS:
        parser.error(f"{args.series} is in common.SERIES but this script has no builder for it")
    supported = SERIES_REGISTRY[args.series].symbols
    if args.symbol not in supported:
        parser.error(f"{args.series} supports {', '.join(supported)}, not {args.symbol}")
    return args


def log_coverage(conn, series: common.Series, symbol: str, frame: pd.DataFrame, spans: Sequence[Span]) -> None:
    """Compare the built dates with the gex.options_daily_summary calendar of the same spans."""
    dates = list(frame["trading_date"])
    master = set(master_calendar(conn, symbol, spans))
    absent, outside = sorted(master - set(dates)), sorted(set(dates) - master)
    log.info("%s %s: %d rows, %s .. %s", series.key, symbol, len(dates), dates[0], dates[-1])
    log.info(
        "%s %s: %d summary-calendar days absent%s; %d rows outside that calendar%s",
        series.key,
        symbol,
        len(absent),
        f" ({fmt_dates(absent)})" if absent else "",
        len(outside),
        f" ({fmt_dates(outside)})" if outside else "",
    )


def run_mode(args: argparse.Namespace) -> str:
    """Output mode of the run: the parquet copy is written in every mode; no flag means --parquet-only."""
    if args.db:
        return "db"
    if args.rollback:
        return "rollback"
    return "parquet-only" if args.parquet_only else "parquet-only (default)"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    common.setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    series = SERIES_REGISTRY[args.series]
    spans = resolve_spans(series, args.symbol, args.start, args.end, args.years)
    check_quiet_window(series.key, args.db or args.rollback, args.ignore_busy_window)
    started = time.perf_counter()
    log.info(
        "%s %s: mode %s, %d span(s) %s .. %s",
        series.key,
        args.symbol,
        run_mode(args),
        len(spans),
        spans[0][0],
        spans[-1][1],
    )

    source = open_source()
    try:
        built = BUILDERS[series.key](source, series, args.symbol, spans)
        frame = assemble(series, args.symbol, built, spans, common.utcnow())
        log_coverage(source, series, args.symbol, frame, spans)
    finally:
        source.close()

    path, in_file = write_parquet(frame, spans)
    first, last = frame["trading_date"].iat[0], frame["trading_date"].iat[-1]
    file_first, file_last = in_file["trading_date"].iat[0], in_file["trading_date"].iat[-1]
    print(
        f"{series.key} {args.symbol}: {len(frame)} rows {first} .. {last}"
        f" -> {path} ({len(in_file)} rows in file, {file_first} .. {file_last})"
    )
    if "factor" in built.meta:
        window = built.meta["factor_window"]
        print(
            f"{series.key} {args.symbol}: {built.meta['scale']} factor {built.meta['factor']!r} = median of "
            f"{built.meta['n_days']} daily SPY/{args.symbol} ratios ({window[0]} .. {window[1]})"
        )
    if args.db or args.rollback:
        sent, stored = write_db(frame, rollback=args.rollback)
        if args.rollback:
            print(
                f"ROLLBACK: {sent} rows WOULD have been written to {common.T_SERIES} "
                f"({stored} rows for this series/symbol inside the transaction); nothing was committed"
            )
        else:
            print(f"DB: upserted {sent} rows into {common.T_SERIES} ({stored} rows now for this series/symbol)")
    log.info("done in %.1f s", time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())
