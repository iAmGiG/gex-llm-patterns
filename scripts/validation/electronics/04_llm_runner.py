#!/usr/bin/env python3
"""gpt-6-luna runner for the Electronics extension (gex-llm-patterns issue #261).

Turns the 30-day windows built by ``02_build_windows.py`` into OpenAI Batch API requests, keeps a ledger of
every run and its cost, and parses the answers into ``backups.gex_llm_regime_detections``.

One ``generate`` produces a *run* of up to a few thousand requests, split into chunks of at most
``common.BATCH_MAX_REQUESTS``.  Every chunk is one Batch job and one row in ``backups.gex_llm_regime_runs``
with run_id ``<run_id>_c<k>``; the raw files of the run live in ``data/backups/gex_llm/<run_id>/``
(``input_<k>.jsonl``, ``output_<k>.jsonl``, ``errors_<k>.jsonl``, ``batch_<k>.json``, ``manifest.json``).
Every subcommand that takes ``--run-id`` accepts the run id (all chunks) or a single chunk id.

    generate  --arm ARM     write input chunks + runs rows (status generated); no network, no cost
    submit    --run-id R    upload + create the batches; the only paid step of a batch run (budget guard)
    poll      --run-id R    refresh batch status and usage (--wait loops until every chunk is finished)
    retrieve  --run-id R    download the output and error files verbatim
    ingest    --run-id R    parse into detections (upsert on the natural key) + parquet; idempotent
    pilot     --arm ARM     synchronous calls on a sample balanced on the classifier label (paid)
    retry     --run-id R    new run for the answers cut off by the token limit, at a larger cap
    status                  runs, cost ledger and per-arm detection state

Persistence: parquet copies under ``data/backups/gex_llm/tables/{runs,detections}/`` are always written.
Postgres rows are written as well when ``backups.gex_llm_regime_*`` exist; if they do not, the command warns
and uses parquet only.  ``--parquet-only`` never opens a database connection.  ``--rollback`` applies the
schema inline (BEGIN/COMMIT stripped), performs every database write and rolls the transaction back on exit,
which exercises the SQL without creating anything; files and parquet are still written.

Guards (each refuses before anything is sent or written):

* cost ledger: ``submit`` and ``pilot`` add their projection to the spend recorded for the current balance and
  refuse beyond ``--budget`` unless ``--force``.  Only runs with ``common.counts_toward_budget(run)`` count (live
  model, LLM arm, not a backfill); the January o4-mini backfill ($7.90) and the November Phase 3/4 backfills are
  listed by ``status`` as outside the budget, never as spend;
* in flight: ``generate`` and ``retry`` skip windows that a generated, submitted or not yet ingested run already
  holds (``--include-inflight`` overrides), and ``submit`` refuses a chunk that repeats a request that was already
  sent or answered (``--force`` overrides);
* busy window: no Postgres writes between 21:50 and 22:45 UTC (``common.assert_not_quiet``), while the monitors
  rebuild the daily tables; ``--rollback`` counts as a write because it applies the DDL, even for ``status``;
  ``--parquet-only`` and the parquet fallback are not affected (``--ignore-busy-window`` overrides; ``poll --wait``
  pauses instead of stopping).

Conventions shared with 02, 03 and 05 (all defined in ``common.py``): a test-retest duplicate has the custom_id
``<arm>|<symbol>|<window_end>#rep1`` (``common.custom_id(..., repeat=1)``) and is stored under arm ``<arm>#rep1``
(``common.REPEAT_ARM_SUFFIX``; 05 maps it back with ``common.base_arm``); ``--repeat-fraction`` defaults to
``common.REPEAT_FRACTION`` (5 %, decision D-09) and warns when it is 0.  The windows of an arm are read from
``common.arm_window_series(arm)``, and runs and detections carry that same key, so ``intraday_spy`` rows say
``intraday_t0`` (the composite windows written by ``02_build_windows.py --composite``) and join to their windows
by value in SQL.  Arms
on a series with ``labels='dated'`` (``p34_dated_2024``, ``p34_dated_2020``) need nothing special: their windows
already carry the dated ``gex_sequence``, which is sent verbatim.

Run from the repository root with the AutoGex conda env::

    source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
    PYTHONPATH=$(pwd) python scripts/validation/electronics/04_llm_runner.py --help
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Callable, Collection, Dict, Iterable, Iterator, List, NamedTuple, Optional, Sequence, Tuple

import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg2.extras import Json

import common

log = logging.getLogger("electronics.runner")

# --------------------------------------------------------------------------- constants
EXPERIMENT = "electronics_261"
# Test-retest duplicates (contract in common.py): the custom_id of the request ends with '#rep1' and the arm stored in
# detections is '<arm>#rep1', because their natural key has no repeat index.  05_report.py maps it back with base_arm.
REPEAT_INDEX = 1  # one duplicate per window is ever requested
REPEAT_SUFFIX = common.REPEAT_MARK  # '#rep'; the two names are read by 05_report.py --check-conventions
REPEAT_ARM_SUFFIX = common.REPEAT_ARM_SUFFIX  # '#rep1'
PILOT_ARM_PREFIX = "pilot_"
PROJECTED_PROMPT_TOKENS = 1911  # gpt-6-luna probe (2026-10-28): the prompt is the same length for every window
PROJECTED_COMPLETION_TOKENS = 900  # probe mean 814 at medium effort, rounded up
DEFAULT_SEED = 261
INFRA_REPO = Path("/mnt/bst/a100/yxie2/cregan1/gex-database-infrastructure")
FILE_EXPIRES_AFTER = {"anchor": "created_at", "seconds": 30 * 24 * 3600}  # the longest retention OpenAI accepts
PARSED = ("ok", "fallback")

# OpenAI batch status -> gex_llm_regime_runs.status ('ingested' is set by this script only)
RUN_STATUS = {
    "validating": "submitted",
    "in_progress": "in_progress",
    "finalizing": "in_progress",
    "cancelling": "in_progress",
    "completed": "completed",
    "failed": "failed",
    "expired": "expired",
    "cancelled": "cancelled",
}
TERMINAL_BATCH = frozenset({"completed", "failed", "expired", "cancelled"})
FINISHED = frozenset({"completed", "failed", "expired", "cancelled", "ingested"})
IN_FLIGHT = frozenset({"submitted", "in_progress", "completed"})  # spend not yet measured by ingest
PENDING = frozenset({"generated"}) | IN_FLIGHT  # requests whose answers are not stored yet
STATUS_RANK = {"generated": 0, "submitted": 1, "in_progress": 2, "completed": 3, "failed": 3, "expired": 3,
               "cancelled": 3, "ingested": 4}  # fmt: skip

# --------------------------------------------------------------------------- table layouts (= gex_llm_regime_schema.sql)
_TS = pa.timestamp("us", tz="UTC")
RUN_SCHEMA = pa.schema([
    ("run_id", pa.string()), ("arm", pa.string()), ("series_key", pa.string()), ("symbol", pa.string()),
    ("model", pa.string()), ("model_created_at", _TS), ("prompt_version", pa.string()),
    ("reasoning_effort", pa.string()), ("response_format", pa.string()), ("max_completion_tokens", pa.int32()),
    ("mode", pa.string()), ("openai_batch_id", pa.string()), ("input_file_id", pa.string()),
    ("output_file_id", pa.string()), ("error_file_id", pa.string()), ("input_sha256", pa.string()),
    ("output_sha256", pa.string()), ("backup_dir", pa.string()), ("window_end_min", pa.date32()),
    ("window_end_max", pa.date32()), ("n_requests", pa.int32()), ("n_responses", pa.int32()),
    ("n_parsed", pa.int32()), ("n_failed", pa.int32()), ("prompt_tokens", pa.int64()),
    ("completion_tokens", pa.int64()), ("reasoning_tokens", pa.int64()), ("est_cost_usd", pa.float64()),
    ("status", pa.string()), ("submitted_at", _TS), ("completed_at", _TS), ("ingested_at", _TS),
    ("git_sha", pa.string()), ("run_metadata", pa.string()), ("created_at", _TS),
])  # fmt: skip
DETECTION_SCHEMA = pa.schema([
    ("run_id", pa.string()), ("arm", pa.string()), ("series_key", pa.string()), ("symbol", pa.string()),
    ("window_end", pa.date32()), ("model", pa.string()), ("prompt_version", pa.string()),
    ("custom_id", pa.string()), ("response_id", pa.string()), ("regime_detected", pa.bool_()),
    ("regime_type", pa.string()), ("confidence", pa.float64()), ("positive_days", pa.int32()),
    ("negative_days", pa.int32()), ("avg_magnitude_billions", pa.float64()), ("sign_flips", pa.int32()),
    ("persistence_pct", pa.float64()), ("metrics_agree", pa.bool_()), ("reasoning", pa.string()),
    ("raw_response", pa.string()), ("parse_status", pa.string()), ("finish_reason", pa.string()),
    ("prompt_tokens", pa.int32()), ("completion_tokens", pa.int32()), ("reasoning_tokens", pa.int32()),
    ("detection_metadata", pa.string()), ("created_at", _TS),
])  # fmt: skip
RUN_COLUMNS = tuple(RUN_SCHEMA.names)
DETECTION_COLUMNS = tuple(DETECTION_SCHEMA.names)
DETECTION_KEY = ("arm", "series_key", "symbol", "window_end", "model", "prompt_version")
JSON_COLUMNS = frozenset({"run_metadata", "detection_metadata"})  # jsonb in Postgres, JSON text in parquet
ANSWER_FIELDS = ("regime_detected", "regime_type", "confidence", "positive_days", "negative_days",
                 "avg_magnitude_billions", "sign_flips", "persistence_pct", "reasoning")  # fmt: skip
WINDOW_COLUMNS = ("series_key", "symbol", "window_end", "gex_sequence", "clf_regime_type", "clf_should_detect",
                  "clf_positive_days", "clf_negative_days", "clf_persistence_pct", "clf_avg_magnitude",
                  "clf_sign_flips")  # fmt: skip


class RunnerError(Exception):
    """A condition the operator can fix; reported without a traceback."""


class Seen(NamedTuple):
    """What a stored detection says about one window."""

    parse_status: Optional[str]
    finish_reason: Optional[str]


@dataclass(frozen=True)
class Request:
    """One line of a Batch input file."""

    custom_id: str
    window_end: date
    line: Dict[str, Any]


@dataclass(frozen=True)
class ChunkPaths:
    """Files of one chunk inside the run's backup directory."""

    input: Path
    output: Path
    errors: Path
    batch: Path


# --------------------------------------------------------------------------- small helpers
def _scrub(text: str) -> str:
    """Redact the API key from text that may reach a log or a file."""
    try:
        key = common.load_openai_key()
    except RuntimeError:
        return text
    return text.replace(key, "[REDACTED]")


def to_utc(epoch: Optional[int]) -> Optional[datetime]:
    return datetime.fromtimestamp(epoch, tz=timezone.utc) if epoch else None


_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def run_sort_key(run: Dict[str, Any]) -> Tuple[datetime, str]:
    """Order runs by creation time; rows written without created_at (the backfill) fall back to submit/ingest time."""
    stamp = run.get("created_at") or run.get("submitted_at") or run.get("ingested_at") or _EPOCH
    return (stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)), run["run_id"]


def arm_of_run(run: Dict[str, Any]) -> Optional[common.Arm]:
    """Registered arm behind a runs row (pilot rows are stored as 'pilot_<arm>'); None for a row of another origin."""
    return common.ARMS.get(common.base_arm(run["arm"]).removeprefix(PILOT_ARM_PREFIX))


def run_window_series(run: Dict[str, Any]) -> str:
    """Series key under which the windows behind a run are stored: ``common.arm_window_series`` of its arm."""
    arm = arm_of_run(run)
    if arm is None or arm.series_key != run["series_key"]:  # unknown arm, or a registry that changed since the run
        return run["series_key"]
    return common.arm_window_series(arm)


def usd(amount: float) -> str:
    """Dollar amount for messages: cents normally, enough digits to stay non-zero for a tiny budget."""
    return f"${amount:.2f}" if amount == 0 or abs(amount) >= 0.01 else f"${amount:.6g}"


def write_atomic(path: Path, data: bytes) -> None:
    """Write next to ``path`` and rename, so a reader never sees a partial file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, obj: Any) -> None:
    write_atomic(path, (common.dumps(obj, indent=2, sort_keys=True) + "\n").encode())


def jsonl_bytes(lines: Iterable[Dict[str, Any]]) -> bytes:
    return "".join(common.dumps(line) + "\n" for line in lines).encode()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def package_versions() -> Dict[str, str]:
    versions = {"python": sys.version.split()[0], "psycopg2": psycopg2.__version__.split()[0]}
    for dist in ("openai", "pyarrow", "numpy", "pandas"):
        with contextlib.suppress(importlib_metadata.PackageNotFoundError):
            versions[dist] = importlib_metadata.version(dist)
    return versions


def infra_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(INFRA_REPO), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def code_sha256() -> Dict[str, str]:
    """Hashes of the two files that shape a request, so a run stays reproducible from an uncommitted tree."""
    return {p.name: common.sha256_file(p) for p in (Path(__file__).resolve(), Path(common.__file__).resolve())}


def split_custom_id(cid: str) -> Tuple[str, str, date, int]:
    """(arm, symbol, window_end, repeat index) of a custom_id; the repeat index is 0 for an original request."""
    arm, symbol, window_end = common.parse_custom_id(cid)
    return arm, symbol, window_end, common.custom_id_repeat(cid)


def detection_arm(arm: str, repeat: int) -> str:
    """Arm label stored in detections: the arm itself, or '<arm>#rep<k>' for a test-retest duplicate."""
    return f"{arm}{common.REPEAT_MARK}{repeat}" if repeat else arm


def make_custom_id(arm: str, window: Dict[str, Any], repeat: int = 0) -> str:
    return common.custom_id(arm, window["symbol"], window["window_end"], repeat)


# --------------------------------------------------------------------------- parquet
def write_parquet(path: Path, rows: Sequence[Dict[str, Any]], schema: pa.Schema) -> None:
    """Write dict rows with an explicit schema (atomically); JSON columns become sorted-key JSON text."""
    records = []
    for row in rows:
        record = {name: row.get(name) for name in schema.names}
        for name in JSON_COLUMNS.intersection(schema.names):
            if record[name] is not None and not isinstance(record[name], str):
                record[name] = common.dumps(record[name], sort_keys=True)
        records.append(record)
    tmp = path.with_name(path.name + ".tmp")
    pq.write_table(pa.Table.from_pylist(records, schema=schema), tmp)
    os.replace(tmp, path)


def read_parquet(path: Path, columns: Sequence[str]) -> List[Dict[str, Any]]:
    """Dict rows holding ``columns`` (None where the file lacks one); JSON text is decoded."""
    names = pq.read_schema(path).names
    rows = pq.read_table(path, columns=[c for c in columns if c in names]).to_pylist()
    for row in rows:
        for name in columns:
            value = row.get(name)
            row[name] = json.loads(value) if name in JSON_COLUMNS and isinstance(value, str) else value
    return rows


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _decode_sequence(value: Any) -> List[Dict[str, Any]]:
    """gex_sequence as stored (JSON text, or a list of structs from jsonb/parquet) -> list of day dicts."""
    return [dict(day) for day in (json.loads(value) if isinstance(value, str) else value)]


def _db_values(row: Dict[str, Any], columns: Sequence[str]) -> Tuple[Any, ...]:
    values = []
    for name in columns:
        value = row.get(name)
        if name in JSON_COLUMNS and value is not None:
            value = Json(value, dumps=common.dumps)
        elif isinstance(value, str):
            value = value.replace("\x00", "")  # Postgres text cannot hold NUL
        values.append(value)
    return tuple(values)


def _table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
    return bool(cur.fetchone()[0])


# --------------------------------------------------------------------------- persistence
class Store:
    """Runs, detections and windows: parquet always, Postgres when its tables exist.

    ``mode`` is ``"auto"`` (commit to Postgres if ``backups.gex_llm_regime_*`` exist, else parquet only),
    ``"parquet"`` (never connect) or ``"rollback"`` (apply the schema inline, write, roll everything back).
    """

    ALL_TABLES = (common.T_SERIES, common.T_WINDOWS, common.T_RUNS, common.T_DETECTIONS)

    def __init__(self, mode: str, writes: bool = True, ignore_busy_window: bool = False) -> None:
        self.mode = mode
        self.writes = writes  # False for a read-only command (status): it may read Postgres in the busy window
        self.ignore_busy_window = ignore_busy_window
        self.conn = None
        self.tables: frozenset = frozenset()
        self._preexisting: frozenset = frozenset()

    @property
    def db_ready(self) -> bool:
        return {common.T_RUNS, common.T_DETECTIONS} <= self.tables

    def __enter__(self) -> "Store":
        if self.mode != "parquet":
            self._open_database()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self.conn is None:
            return
        self.conn.rollback()
        if self.mode == "rollback":
            with self.conn.cursor() as cur:
                created = [t for t in self.ALL_TABLES if t not in self._preexisting and _table_exists(cur, t)]
            self.conn.rollback()
            if created:
                log.error("rollback left tables behind: %s", ", ".join(created))
            else:
                log.info("rollback verified: the database is unchanged (no gex_llm_regime table was created)")
        self.conn.close()

    def _refuse_busy_window(self) -> None:
        """Refuse before any Postgres write while the monitors rebuild the daily tables (common.assert_not_quiet).

        A read-only command (status) may read in the window, except under --rollback, which applies the DDL inline.
        """
        if not self.writes and self.mode != "rollback":
            return
        try:
            common.assert_not_quiet(self.ignore_busy_window)
        except RuntimeError as exc:
            raise RunnerError(f"Postgres writes are paused: {exc} (the monitors rebuild the daily tables); "
                              "rerun later or use --parquet-only") from exc

    def wait_out_busy_window(self) -> None:
        """Pause a long loop (poll --wait) while Postgres must not be written, instead of stopping it."""
        if self.conn is None or not self.writes or self.ignore_busy_window:
            return
        (h0, m0), (h1, m1) = common.QUIET_WINDOW_UTC
        while common.in_quiet_window():
            now = common.utcnow()
            end = datetime(now.year, now.month, now.day, h1, m1, tzinfo=timezone.utc) + timedelta(minutes=1)  # minute m1 included
            pause = min(300.0, max(1.0, (end - now).total_seconds() + 1.0))
            log.info("inside the %02d:%02d-%02d:%02d UTC quiet window (daily rebuild of the monitors): no database "
                     "writes, sleeping %.0f s", h0, m0, h1, m1, pause)  # fmt: skip
            time.sleep(pause)

    def _open_database(self) -> None:
        if self.mode == "rollback":
            self._refuse_busy_window()  # the schema is applied inline: refuse before touching the database
        try:
            conn = common.connect()
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '600s'")
                present = frozenset(t for t in self.ALL_TABLES if _table_exists(cur, t))
        except psycopg2.Error as exc:
            if self.mode == "rollback":
                raise RunnerError(f"--rollback needs the database: {exc}") from exc
            log.warning("database unavailable (%s): using parquet only", str(exc).strip())
            return
        self._preexisting = present
        if self.mode == "rollback":
            sql = re.sub(r"^\s*(BEGIN|COMMIT)\s*;\s*$", "", common.SCHEMA_SQL.read_text(), flags=re.M | re.I)
            with conn.cursor() as cur:
                cur.execute(sql)
            present = frozenset(self.ALL_TABLES)
            log.info("--rollback: schema applied inline; every database write is rolled back on exit")
        elif not {common.T_RUNS, common.T_DETECTIONS} <= present:
            conn.rollback()
            conn.close()
            log.warning("%s and %s do not exist yet (DDL awaits approval): using parquet only",
                        common.T_RUNS, common.T_DETECTIONS)  # fmt: skip
            return
        else:
            try:
                self._refuse_busy_window()  # the tables exist, so every write would reach Postgres
            except RunnerError:
                conn.rollback()
                conn.close()
                raise
            conn.commit()
        self.conn, self.tables = conn, present

    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        """Commit the database writes made inside the block (``--rollback`` keeps them open until exit)."""
        try:
            yield
        except BaseException:
            if self.conn is not None and self.mode != "rollback":
                self.conn.rollback()
            raise
        if self.conn is not None and self.mode != "rollback":
            self.conn.commit()

    def _query(self, sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            names = [d[0] for d in cur.description]
            rows = [dict(zip(names, record, strict=True)) for record in cur.fetchall()]
        if self.mode != "rollback":
            self.conn.commit()  # a read must not leave the connection idle in transaction (poll --wait)
        return rows

    @staticmethod
    def _files(kind: str) -> List[Path]:
        directory = common.PARQUET_ROOT / kind
        return sorted(directory.glob("*.parquet")) if directory.is_dir() else []

    # ---- windows
    def load_windows(self, window_series: str, symbol: str, from_db: bool = False) -> List[Dict[str, Any]]:
        """Windows of one series/symbol in date order, ``gex_sequence`` decoded to a list of day dicts.

        ``window_series`` is the key the windows are stored under: ``common.arm_window_series(arm)`` (composite
        arms such as intraday_spy differ from the series key of their runs), or ``run_window_series(run)``.
        """
        if from_db:
            if common.T_WINDOWS not in self.tables:
                raise RunnerError(f"--from-db: {common.T_WINDOWS} does not exist (use the parquet copy)")
            rows = self._query(
                f"SELECT {', '.join(WINDOW_COLUMNS)} FROM {common.T_WINDOWS} "
                "WHERE series_key = %s AND symbol = %s ORDER BY window_end", (window_series, symbol))  # fmt: skip
        else:
            path = common.parquet_path("windows", window_series, symbol)
            if not path.exists():
                raise RunnerError(f"{path} not found: run 02_build_windows.py for {window_series}/{symbol} (or --from-db)")
            missing = set(WINDOW_COLUMNS) - set(pq.read_schema(path).names)
            if missing:
                raise RunnerError(f"{path} lacks columns {sorted(missing)}")
            rows = read_parquet(path, WINDOW_COLUMNS)
        windows = [{**row, "window_end": _as_date(row["window_end"]),
                    "gex_sequence": _decode_sequence(row["gex_sequence"])} for row in rows]  # fmt: skip
        return sorted(windows, key=lambda w: w["window_end"])

    # ---- runs
    def load_runs(self) -> List[Dict[str, Any]]:
        """Every known run once: the most advanced status wins and the parquet copy wins ties."""
        candidates = [(1, row) for path in self._files("runs") for row in read_parquet(path, RUN_COLUMNS)]
        if self.db_ready:
            candidates += [(0, row) for row in self._query(f"SELECT {', '.join(RUN_COLUMNS)} FROM {common.T_RUNS}")]
        best: Dict[str, Tuple[Tuple[int, int], Dict[str, Any]]] = {}
        for prefer_parquet, row in candidates:
            rank = (STATUS_RANK.get(row["status"], 0), prefer_parquet)
            if row["run_id"] not in best or rank > best[row["run_id"]][0]:
                best[row["run_id"]] = (rank, row)
        return sorted((row for _, row in best.values()), key=run_sort_key)

    def save_runs(self, rows: Sequence[Dict[str, Any]]) -> None:
        if self.db_ready:
            update = [c for c in RUN_COLUMNS if c not in ("run_id", "created_at")]
            stamped = [{**r, "created_at": r.get("created_at") or common.utcnow()} for r in rows]  # NOT NULL column
            common.upsert_rows(self.conn, common.T_RUNS, RUN_COLUMNS, [_db_values(r, RUN_COLUMNS) for r in stamped],
                               conflict_cols=("run_id",), update_cols=update)  # fmt: skip
        for row in rows:
            write_parquet(common.parquet_path("runs", row["run_id"]), [row], RUN_SCHEMA)

    # ---- detections
    def detection_index(self, arms: Optional[Collection[str]], model: str,
                        prompt_version: str) -> Dict[Tuple[str, date], List[Seen]]:  # fmt: skip
        """Every stored answer by (arm, window_end), from parquet and the database (all arms if ``arms`` is None)."""
        columns = ("arm", "window_end", "model", "prompt_version", "parse_status", "finish_reason")
        rows = [row for path in self._files("detections") for row in read_parquet(path, columns)]
        if self.db_ready:
            rows += self._query(
                f"SELECT {', '.join(columns)} FROM {common.T_DETECTIONS} WHERE model = %s AND prompt_version = %s",
                (model, prompt_version))  # fmt: skip
        index: Dict[Tuple[str, date], List[Seen]] = {}
        for row in rows:
            if row["model"] == model and row["prompt_version"] == prompt_version and (arms is None or row["arm"] in arms):
                index.setdefault((row["arm"], row["window_end"]), []).append(Seen(row["parse_status"], row["finish_reason"]))
        return index

    def load_detections(self, run_id: str) -> List[Dict[str, Any]]:
        """Detection rows written by one chunk (parquet copy, else the database)."""
        path = common.parquet_path("detections", run_id)
        if path.exists():
            return read_parquet(path, DETECTION_COLUMNS)
        if self.db_ready:
            return self._query(f"SELECT {', '.join(DETECTION_COLUMNS)} FROM {common.T_DETECTIONS} WHERE run_id = %s", (run_id,))
        return []

    def save_detections(self, run_id: str, rows: Sequence[Dict[str, Any]]) -> None:
        if self.db_ready:
            update = [c for c in DETECTION_COLUMNS if c not in DETECTION_KEY and c != "created_at"]
            common.upsert_rows(self.conn, common.T_DETECTIONS, DETECTION_COLUMNS,
                               [_db_values(r, DETECTION_COLUMNS) for r in rows],
                               conflict_cols=DETECTION_KEY, update_cols=update)  # fmt: skip
        write_parquet(common.parquet_path("detections", run_id), rows, DETECTION_SCHEMA)


# --------------------------------------------------------------------------- window selection
def _rank(window_end: date, seed: int, salt: str) -> str:
    return hashlib.sha256(f"{seed}|{salt}|{window_end.isoformat()}".encode()).hexdigest()


def pick(windows: Sequence[Dict[str, Any]], k: int, seed: int, salt: str) -> List[Dict[str, Any]]:
    """The ``k`` windows with the smallest hash rank, in date order: reproducible and independent of any RNG."""
    chosen = sorted(windows, key=lambda w: _rank(w["window_end"], seed, salt))[:k]
    return sorted(chosen, key=lambda w: w["window_end"])


def stratified_by_year(windows: Sequence[Dict[str, Any]], limit: int, seed: int, salt: str) -> List[Dict[str, Any]]:
    """``limit`` windows allocated to calendar years in proportion to their size (largest remainder)."""
    if limit >= len(windows):
        return list(windows)
    by_year: Dict[int, List[Dict[str, Any]]] = {}
    for window in windows:
        by_year.setdefault(window["window_end"].year, []).append(window)
    quota = {year: limit * len(group) / len(windows) for year, group in by_year.items()}
    alloc = {year: int(q) for year, q in quota.items()}
    for year in sorted(quota, key=lambda y: (alloc[y] - quota[y], y))[: limit - sum(alloc.values())]:
        alloc[year] += 1
    chosen = [w for year, group in by_year.items() for w in pick(group, alloc[year], seed, f"{salt}:{year}")]
    return sorted(chosen, key=lambda w: w["window_end"])


def balanced_sample(windows: Sequence[Dict[str, Any]], n: int, seed: int, salt: str) -> List[Dict[str, Any]]:
    """``n`` windows, half with clf_should_detect and half without (topped up from the other class if short)."""
    pos = [w for w in windows if w["clf_should_detect"]]
    neg = [w for w in windows if not w["clf_should_detect"]]
    want_pos, want_neg = n // 2, n - n // 2
    take_pos, take_neg = min(len(pos), want_pos), min(len(neg), want_neg)
    if take_pos < want_pos:
        take_neg = min(len(neg), n - take_pos)
    elif take_neg < want_neg:
        take_pos = min(len(pos), n - take_neg)
    if (take_pos, take_neg) != (want_pos, want_neg):
        log.warning("classifier classes are unbalanced here (%d detect / %d not): sampling %d + %d",
                    len(pos), len(neg), take_pos, take_neg)  # fmt: skip
    sample = pick(pos, take_pos, seed, f"{salt}:pos") + pick(neg, take_neg, seed, f"{salt}:neg")
    return sorted(sample, key=lambda w: w["window_end"])


def window_state(seen: Sequence[Seen]) -> str:
    """'done' = a parsed answer that was not cut off; 'retry' = cut off by the token limit; else 'open'."""
    if any(s.parse_status in PARSED and s.finish_reason != "length" for s in seen):
        return "done"
    return "retry" if any(s.finish_reason == "length" for s in seen) else "open"


# --------------------------------------------------------------------------- work already requested
def holds_answers(run: Dict[str, Any]) -> bool:
    """True while the answers to a run's requests are not in the stored detections.

    A failed, expired or cancelled batch holds answers only if it left an output or error file to ingest; a failed
    batch without files frees its windows at once.
    """
    if run["status"] in PENDING:
        return True
    return run["status"] in ("failed", "expired", "cancelled") and bool(run.get("output_file_id") or run.get("error_file_id"))


def run_requests(run: Dict[str, Any]) -> List[Tuple[str, date]]:
    """(arm label as stored in detections, window_end) of every request in a chunk's input file."""
    try:
        path = chunk_paths(run).input
    except (KeyError, TypeError):  # a row that was not written by this script (no chunk index)
        return []
    if not path.exists():
        log.warning("%s: %s is missing, so its requests cannot be matched against other runs", run["run_id"], path)
        return []
    keys = []
    for line in read_jsonl(path):
        arm, _, window_end, repeat = split_custom_id(line["custom_id"])
        keys.append((detection_arm(arm, repeat), window_end))
    return keys


def pending_requests(store: Store, arms: Optional[Collection[str]], model: str, prompt_version: str, *,
                     sent_only: bool = False, skip: Collection[str] = ()) -> Dict[Tuple[str, date], str]:  # fmt: skip
    """(arm label, window_end) -> run_id for the requests of runs whose answers are not stored yet.

    ``sent_only`` leaves out runs that were only generated; ``skip`` leaves out the given run ids.
    """
    held: Dict[Tuple[str, date], str] = {}
    for run in store.load_runs():
        if arms is not None and run["arm"] not in arms:
            continue
        if run["model"] != model or run["prompt_version"] != prompt_version or run["run_id"] in skip:
            continue
        if not holds_answers(run) or (sent_only and run["status"] == "generated"):
            continue
        for key in run_requests(run):
            held.setdefault(key, run["run_id"])
    return held


def refuse_duplicate_requests(store: Store, todo: Sequence[Dict[str, Any]]) -> None:
    """Refuse chunks that ask again for a window already answered or already requested in a run that was sent."""
    first = todo[0]
    arms = {r["arm"] for r in todo}
    sent = pending_requests(store, arms, first["model"], first["prompt_version"], sent_only=True,
                            skip={r["run_id"] for r in todo})  # fmt: skip
    index = store.detection_index(arms | {a + REPEAT_ARM_SUFFIX for a in arms}, first["model"], first["prompt_version"])
    clashes = []
    for run in todo:
        for key in run_requests(run):
            if key in sent:
                clashes.append((run["run_id"], key, f"already requested in run {sent[key]}"))
            elif window_state(index.get(key, ())) == "done":
                clashes.append((run["run_id"], key, "already answered"))
    if clashes:
        run_id, (label, window_end), why = clashes[0]
        raise RunnerError(f"{len(clashes)} request(s) in {len(todo)} chunk(s) repeat earlier work, e.g. {label} "
                          f"{window_end} in {run_id} is {why} -- refusing (pass --force to send them anyway)")  # fmt: skip


# --------------------------------------------------------------------------- requests and runs
def build_request(custom_id: str, window: Dict[str, Any], max_completion_tokens: int) -> Request:
    """One Batch line: the unchanged Phase 4A prompt for ``window`` in the luna request body."""
    sequence = window["gex_sequence"]
    values = [day.get("net_gex_usd") for day in sequence]
    if len(sequence) != common.WINDOW_DAYS or any(v is None or v != v for v in values):
        raise RunnerError(f"window {window['series_key']}/{window['symbol']}/{window['window_end']} "
                          f"must hold {common.WINDOW_DAYS} numeric daily values")  # fmt: skip
    body = common.chat_body(common.build_prompt(sequence), max_completion_tokens=max_completion_tokens)
    line = {"custom_id": custom_id, "method": "POST", "url": "/v1/chat/completions", "body": body}
    return Request(custom_id, window["window_end"], line)


def split_even(items: Sequence[Request], max_size: int) -> List[Sequence[Request]]:
    """Contiguous chunks of near-equal size, none larger than ``max_size``."""
    n_chunks = math.ceil(len(items) / max_size)
    size, extra = divmod(len(items), n_chunks)
    chunks, start = [], 0
    for k in range(n_chunks):
        end = start + size + (1 if k < extra else 0)
        chunks.append(items[start:end])
        start = end
    return chunks


def unique_run_id(arm: str, mode: str) -> str:
    when = common.utcnow()
    while (common.BACKUP_ROOT / common.make_run_id(arm, common.MODEL, mode, when)).exists():
        when += timedelta(seconds=1)  # run ids have one-second resolution
    return common.make_run_id(arm, common.MODEL, mode, when)


def new_run_row(**fields: Any) -> Dict[str, Any]:
    row = dict.fromkeys(RUN_COLUMNS)
    row.update(fields)
    return row


def chunk_paths(run: Dict[str, Any]) -> ChunkPaths:
    directory, k = Path(run["backup_dir"]), run["run_metadata"]["chunk_index"]
    return ChunkPaths(directory / f"input_{k}.jsonl", directory / f"output_{k}.jsonl",
                      directory / f"errors_{k}.jsonl", directory / f"batch_{k}.json")  # fmt: skip


def chunk_runs(store: Store, run_id: str) -> List[Dict[str, Any]]:
    """Runs rows of a run id (all its chunks) or of a single chunk id, in chunk order."""
    runs = [r for r in store.load_runs() if run_id in (r["run_id"], (r["run_metadata"] or {}).get("parent_run_id"))]
    if not runs:
        raise RunnerError(f"no run {run_id!r} (see the 'status' subcommand)")
    foreign = [r["run_id"] for r in runs if "chunk_index" not in (r["run_metadata"] or {})]
    if foreign:  # e.g. the backfilled o4-mini runs of 03_backfill_round1.py: no chunk files, never to be re-sent
        raise RunnerError(f"{foreign[0]} was not made by this script (a backfill): nothing to submit, poll, retrieve, "
                          "ingest or retry")  # fmt: skip
    return sorted(runs, key=lambda r: r["run_metadata"]["chunk_index"])


def create_run(store: Store, *, arm: str, series_key: str, symbol: str, requests: Sequence[Request], mode: str,
               max_completion_tokens: int, chunk_size: int, metadata: Dict[str, Any],
               model_created_at: Optional[datetime] = None) -> List[Dict[str, Any]]:  # fmt: skip
    """Write ``input_<k>.jsonl`` for ``requests`` and one 'generated' runs row per chunk; returns the rows."""
    base = unique_run_id(arm, mode)
    run_dir = common.run_backup_dir(base)
    pricing = "batch" if mode == "batch" else "standard"
    per_request = common.estimate_cost_usd(common.MODEL, pricing, PROJECTED_PROMPT_TOKENS, PROJECTED_COMPLETION_TOKENS)
    chunks = split_even(requests, chunk_size)
    shared = {
        "parent_run_id": base,
        "n_chunks": len(chunks),
        "projection_basis": {"prompt_tokens": PROJECTED_PROMPT_TOKENS, "completion_tokens": PROJECTED_COMPLETION_TOKENS,
                             "pricing": pricing},
        "package_versions": package_versions(),
        "infra_git_sha": infra_git_sha(),
        "code_sha256": code_sha256(),
        **metadata,
    }
    now, rows = common.utcnow(), []
    for k, chunk in enumerate(chunks):
        path = run_dir / f"input_{k}.jsonl"
        write_atomic(path, jsonl_bytes(r.line for r in chunk))
        rows.append(new_run_row(
            run_id=f"{base}_c{k}", arm=arm, series_key=series_key, symbol=symbol, model=common.MODEL,
            model_created_at=model_created_at, prompt_version=common.PROMPT_VERSION,
            reasoning_effort=common.REASONING_EFFORT, response_format=common.RESPONSE_FORMAT,
            max_completion_tokens=max_completion_tokens, mode=mode, input_sha256=common.sha256_file(path),
            backup_dir=str(run_dir), window_end_min=min(r.window_end for r in chunk),
            window_end_max=max(r.window_end for r in chunk), n_requests=len(chunk), status="generated",
            git_sha=common.git_sha(), created_at=now,
            run_metadata={**shared, "chunk_index": k, "projected_cost_usd": round(per_request * len(chunk), 6),
                          "n_repeat_requests": sum(common.custom_id_repeat(r.custom_id) > 0 for r in chunk)},
        ))  # fmt: skip
    write_json(run_dir / "manifest.json", {
        "run_id": base, "arm": arm, "series_key": series_key, "symbol": symbol, "mode": mode,
        "model": common.MODEL, "prompt_version": common.PROMPT_VERSION, "generated_at": now,
        "max_completion_tokens": max_completion_tokens, "git_sha": common.git_sha(), **shared,
        "chunks": [{"run_id": r["run_id"], "input_file": chunk_paths(r).input.name, "n_requests": r["n_requests"],
                    "input_sha256": r["input_sha256"], "window_end_min": r["window_end_min"],
                    "window_end_max": r["window_end_max"]} for r in rows],
    })  # fmt: skip
    with store.transaction():
        store.save_runs(rows)
    return rows


# --------------------------------------------------------------------------- cost ledger
def run_cost(run: Dict[str, Any]) -> float:
    """USD charged to the ledger for a run: the measured cost once known, else the projection while it is in flight.

    Only runs paid from the current balance count (``common.counts_toward_budget``); the January o4-mini backfill
    and the November Phase 3/4 backfills cost 0.0 here.
    """
    if not common.counts_toward_budget(run):
        return 0.0
    if run.get("est_cost_usd") is not None:
        return float(run["est_cost_usd"])
    meta = run.get("run_metadata") or {}
    projected = float(meta.get("projected_cost_usd") or 0.0)
    if run["status"] in IN_FLIGHT:
        return projected
    if run["status"] in ("expired", "cancelled"):  # no usage reported: charge the share of requests that completed
        counts = (meta.get("batch") or {}).get("request_counts") or {}
        total = counts.get("total") or run.get("n_requests") or 0
        return projected * (counts.get("completed") or 0) / total if total else 0.0
    return 0.0


def check_budget(store: Store, projected: float, budget: float, force: bool, what: str) -> None:
    """Refuse when the ledger of all runs plus ``projected`` would exceed ``budget`` (unless ``force``)."""
    committed = sum(run_cost(r) for r in store.load_runs())
    message = (f"{what}: ledger ${committed:.4f} + projected ${projected:.4f} = ${committed + projected:.4f} "
               f"against a budget of {usd(budget)}")  # fmt: skip
    if committed + projected <= budget:
        log.info(message)
    elif force:
        log.warning("%s -- over budget, continuing because of --force", message)
    else:
        raise RunnerError(f"{message} -- refusing (raise --budget or pass --force)")


# --------------------------------------------------------------------------- batch state
def apply_batch(run: Dict[str, Any], batch: Any) -> Dict[str, Any]:
    """Copy the state of an OpenAI batch object into a runs row (an ingested run stays 'ingested')."""
    snapshot = batch.model_dump(mode="json")
    row = dict(run)
    ingested = row["status"] == "ingested"
    if not ingested:
        row["status"] = RUN_STATUS.get(batch.status, row["status"])
    row.update(openai_batch_id=batch.id, input_file_id=batch.input_file_id, output_file_id=batch.output_file_id,
               error_file_id=batch.error_file_id)  # fmt: skip
    row["submitted_at"] = row["submitted_at"] or to_utc(batch.created_at)
    finished = {"completed": batch.completed_at, "failed": batch.failed_at, "expired": batch.expired_at,
                "cancelled": batch.cancelled_at}.get(batch.status)  # fmt: skip
    row["completed_at"] = to_utc(finished) or row["completed_at"]
    usage = snapshot.get("usage") or {}
    if batch.status in TERMINAL_BATCH and not ingested:  # ingest later replaces these with per-line sums
        if usage:
            row["prompt_tokens"] = usage.get("input_tokens") or 0
            row["completion_tokens"] = usage.get("output_tokens") or 0
            row["reasoning_tokens"] = (usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0
            row["est_cost_usd"] = common.estimate_cost_usd(
                row["model"], "batch", row["prompt_tokens"], row["completion_tokens"])  # fmt: skip
        elif batch.status == "failed":  # rejected before any request ran: nothing is billed
            row.update(prompt_tokens=0, completion_tokens=0, reasoning_tokens=0, est_cost_usd=0.0)
        # else: no usage reported, so est_cost_usd stays empty and the ledger keeps counting the projection
    row["run_metadata"] = {**(row["run_metadata"] or {}), "batch": snapshot}
    return row


def refresh_run(store: Store, client: Any, run: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch the batch of a submitted chunk, store its snapshot next to the input and update the runs row."""
    row = apply_batch(run, client.batches.retrieve(run["openai_batch_id"]))
    write_json(chunk_paths(row).batch, row["run_metadata"]["batch"])
    with store.transaction():
        store.save_runs([row])
    return row


def upload_input(client: Any, path: Path) -> Any:
    """Upload a chunk with a 30-day retention; fall back to the default policy if the SDK or API rejects it."""
    from openai import BadRequestError

    with open(path, "rb") as fh:
        try:
            return client.files.create(file=fh, purpose="batch", expires_after=FILE_EXPIRES_AFTER)
        except (TypeError, BadRequestError) as exc:
            log.warning("expires_after not accepted (%s): uploading with the default retention", type(exc).__name__)
            fh.seek(0)
            return client.files.create(file=fh, purpose="batch")


def find_batch(client: Any, run_id: str) -> Optional[Any]:
    """A batch already created for this chunk (a submit whose answer was lost), found by its metadata."""
    try:
        for batch in client.batches.list(limit=100).data:
            if (batch.metadata or {}).get("run_id") == run_id:
                return batch
    except Exception as exc:  # network or API hiccup: creating a new batch is the lesser evil
        log.warning("could not list existing batches (%s)", _scrub(str(exc)))
    return None


# --------------------------------------------------------------------------- answers -> detections
def payload_in_range(payload: Dict[str, Any]) -> bool:
    """Reject numbers that cannot be stored (NaN, int32 overflow) so one odd answer cannot abort an ingest."""
    numbers = ("positive_days", "negative_days", "sign_flips", "confidence", "avg_magnitude_billions", "persistence_pct")
    return all(payload[n] is None or (math.isfinite(payload[n]) and abs(payload[n]) <= 1e9) for n in numbers)


def classifier_diff(payload: Dict[str, Any], window: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Model-reported metric minus the classifier value, per metric."""
    reference = {"positive_days": window["clf_positive_days"], "negative_days": window["clf_negative_days"],
                 "avg_magnitude_billions": window["clf_avg_magnitude"] / 1e9, "sign_flips": window["clf_sign_flips"],
                 "persistence_pct": window["clf_persistence_pct"]}  # fmt: skip
    return {k: None if payload[k] is None else round(payload[k] - v, 4) for k, v in reference.items()}


def detection_row(run: Dict[str, Any], request: Dict[str, Any], answer: Optional[Dict[str, Any]],
                  windows: Dict[date, Dict[str, Any]]) -> Dict[str, Any]:  # fmt: skip
    """Detections row for one request and its output/error line (``None`` when no line came back)."""
    cid = request["custom_id"]
    arm, symbol, window_end, repeat = split_custom_id(cid)
    prompt = request["body"]["messages"][0]["content"]
    meta: Dict[str, Any] = {"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
    content = finish = response_id = usage = None
    if answer is None:
        meta["no_response_line"] = True
    else:
        response = answer.get("response") or {}
        body = response.get("body") or {}
        choices = body.get("choices") or []
        if response.get("status_code") == 200 and choices:
            message = choices[0].get("message") or {}
            content, finish = message.get("content"), choices[0].get("finish_reason")
            response_id, usage = body.get("id"), body.get("usage")
            meta.update(request_id=response.get("request_id"), batch_request_id=answer.get("id"),
                        model_returned=body.get("model"), created=body.get("created"),
                        service_tier=body.get("service_tier"), refusal=message.get("refusal") or None)  # fmt: skip
        else:
            meta["error"] = {"status_code": response.get("status_code"), "detail": answer.get("error") or body.get("error")}
    payload, status = common.parse_llm_content(content)
    if payload is not None and not payload_in_range(payload):
        payload, status = None, "failed"
        meta["invalid_payload"] = True
    if finish == "length":
        meta["retry_at"] = common.RETRY_MAX_COMPLETION_TOKENS
    prompt_tokens, completion_tokens, reasoning_tokens = common.usage_fields(usage)
    row = dict.fromkeys(DETECTION_COLUMNS)
    row.update(run_id=run["run_id"], arm=detection_arm(arm, repeat), series_key=run["series_key"],
               symbol=symbol, window_end=window_end, model=run["model"], prompt_version=run["prompt_version"],
               custom_id=cid, response_id=response_id, raw_response=content, parse_status=status,
               finish_reason=finish, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
               reasoning_tokens=reasoning_tokens)  # fmt: skip
    if payload is not None:
        row.update({name: payload[name] for name in ANSWER_FIELDS})
        if row["regime_type"] not in common.REGIME_TYPES:
            meta["regime_type_raw"], row["regime_type"] = row["regime_type"], None
        window = windows.get(window_end)
        if window is None:
            log.warning("%s: window not in the windows table, metrics_agree left empty", cid)
        else:
            reference = {"positive_days": window["clf_positive_days"], "negative_days": window["clf_negative_days"],
                         "avg_magnitude": window["clf_avg_magnitude"], "persistence_pct": window["clf_persistence_pct"]}  # fmt: skip
            row["metrics_agree"] = common.metrics_agree(payload, reference)
            meta["diff_vs_classifier"] = classifier_diff(payload, window)
            if prompt != common.build_prompt(window["gex_sequence"]):
                meta["window_changed"] = True  # the stored window no longer matches what was sent
    row["detection_metadata"] = {k: v for k, v in meta.items() if v is not None}
    row["created_at"] = common.utcnow()  # NOT NULL in the table; kept on re-ingest (see save_detections)
    return row


def parse_chunk(run: Dict[str, Any],
                windows: Dict[date, Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:  # fmt: skip
    """Parse one retrieved chunk into (updated runs row, detections rows, summary); pure and repeatable."""
    paths = chunk_paths(run)
    if not paths.input.exists():
        raise RunnerError(f"{paths.input} is missing: the request file is needed to find unanswered windows")
    if common.sha256_file(paths.input) != run["input_sha256"]:
        log.warning("%s: input file differs from the sha256 stored at generate time", paths.input.name)
    requests = read_jsonl(paths.input)
    answers: Dict[str, Dict[str, Any]] = {}
    for path in (paths.errors, paths.output):  # an output line wins over an error line for the same request
        if path.exists():
            answers.update({line["custom_id"]: line for line in read_jsonl(path)})
    stray = sorted(set(answers) - {r["custom_id"] for r in requests})
    if stray:
        log.warning("%s: ignoring %d answers whose custom_id is not in the input (first: %s)",
                    run["run_id"], len(stray), stray[0])  # fmt: skip
    rows = sorted((detection_row(run, r, answers.get(r["custom_id"]), windows) for r in requests),
                  key=lambda r: (r["arm"], r["window_end"], r["custom_id"]))  # fmt: skip
    status = Counter(r["parse_status"] for r in rows)
    n_parsed = sum(status[s] for s in PARSED)
    tokens = [sum(r[k] or 0 for r in rows) for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens")]
    pricing = "batch" if run["mode"] == "batch" else "standard"
    summary = {
        "parse_status": dict(sorted(status.items())),
        "finish_reason": dict(sorted(Counter(r["finish_reason"] or "none" for r in rows).items())),
        "n_retry_pending": sum(r["finish_reason"] == "length" for r in rows),
        "n_metrics_agree": sum(bool(r["metrics_agree"]) for r in rows),
        "n_metrics_checked": sum(r["metrics_agree"] is not None for r in rows),
        "n_window_changed": sum(bool(r["detection_metadata"].get("window_changed")) for r in rows),
        "n_stray_answers": len(stray),
    }
    if len(rows) != run["n_requests"]:
        log.warning("%s: input holds %d requests but the runs row says %d", run["run_id"], len(rows), run["n_requests"])
    updated = dict(run)
    updated.update(
        n_responses=sum(r["finish_reason"] is not None for r in rows), n_parsed=n_parsed, n_failed=len(rows) - n_parsed,
        prompt_tokens=tokens[0], completion_tokens=tokens[1], reasoning_tokens=tokens[2],
        est_cost_usd=common.estimate_cost_usd(run["model"], pricing, tokens[0], tokens[1]), status="ingested",
        ingested_at=run["ingested_at"] or common.utcnow(), output_sha256=common.sha256_file(paths.output) if paths.output.exists() else None,
        run_metadata={**(run["run_metadata"] or {}), "ingest": summary},
    )  # fmt: skip
    return updated, rows, summary


# --------------------------------------------------------------------------- subcommands
def window_range(arm: common.Arm, end_min: Optional[date], end_max: Optional[date]) -> Tuple[date, date]:
    start, end = common.arm_date_range(arm)
    return max(start, end_min or start), min(end, end_max or end)


def cmd_generate(store: Store, args: argparse.Namespace) -> int:
    """Select the windows still to run, write the Batch input chunks and the 'generated' runs rows."""
    arm = common.ARMS[args.arm]
    start, end = window_range(arm, args.end_min, args.end_max)
    window_series = common.arm_window_series(arm)
    pool = [w for w in store.load_windows(window_series, arm.symbol, args.from_db) if start <= w["window_end"] <= end]
    if not pool:
        raise RunnerError(f"no {window_series}/{arm.symbol} windows end between {start} and {end}")
    if args.repeat_fraction == 0:
        log.warning("%s: --repeat-fraction 0 requests no test-retest duplicates, although decision D-09 asks for %g%% "
                    "on every LLM arm; a later generate with a positive fraction can still add them to answered windows",
                    arm.key, 100 * common.REPEAT_FRACTION)  # fmt: skip
    repeat_arm = arm.key + REPEAT_ARM_SUFFIX
    index = store.detection_index([arm.key, repeat_arm], common.MODEL, common.PROMPT_VERSION)
    held = {} if args.include_inflight else pending_requests(store, [arm.key], common.MODEL, common.PROMPT_VERSION)

    def state(window: Dict[str, Any], label: str) -> str:
        """'done', 'retry' (cut off by the token limit), 'inflight' (a pending run holds the request) or 'open'."""
        key = (label, window["window_end"])
        stored = "open" if args.include_done else window_state(index.get(key, ()))  # --include-done ignores answers
        return "inflight" if key in held and stored != "done" else stored

    states = {w["window_end"]: state(w, arm.key) for w in pool}
    in_flight = [w for w in pool if states[w["window_end"]] == "inflight"]
    done = [w for w in pool if states[w["window_end"]] == "done"]
    awaiting = [w for w in pool if states[w["window_end"]] == "retry"]  # the retry subcommand's job
    todo = [w for w in pool if states[w["window_end"]] == "open"]
    if args.limit is None:
        originals = todo
    elif args.sample == "stratified":
        originals = stratified_by_year(todo, args.limit, args.seed, arm.key)
    else:
        originals = todo[: args.limit]
    # Repeats top up to the target share of the windows that hold (or are about to hold) an original answer, so
    # running generate again never adds a second batch of repeats.
    answered = originals + done
    repeat_states = {w["window_end"]: state(w, repeat_arm) for w in answered}
    target = round(args.repeat_fraction * len(answered))
    requested = sum(s != "open" for s in repeat_states.values())  # done, in flight or awaiting retry
    candidates = [w for w in answered if repeat_states[w["window_end"]] == "open"]
    repeats = pick(candidates, max(0, target - requested), args.seed, arm.key + common.REPEAT_MARK)
    log.info("%s: %d windows ending %s..%s | %d done, %d awaiting retry, %d in flight, %d open | selected %d + %d "
             "repeats (repeat target %d, %d already requested)", arm.key, len(pool), pool[0]["window_end"],
             pool[-1]["window_end"], len(done), len(awaiting), len(in_flight), len(todo), len(originals), len(repeats),
             target, requested)  # fmt: skip
    if in_flight:
        status_of = {r["run_id"]: r["status"] for r in store.load_runs()}
        holders = sorted({held[(arm.key, w["window_end"])] for w in in_flight})
        log.info("%d windows are held by runs whose answers are not stored yet (%s): ingest or wait for them, or pass "
                 "--include-inflight to request those windows again",
                 len(in_flight), ", ".join(f"{h} [{status_of.get(h, '?')}]" for h in holders))  # fmt: skip
    if not originals and not repeats:
        log.info("nothing to generate")
        return 0

    requests = [build_request(make_custom_id(arm.key, w), w, common.MAX_COMPLETION_TOKENS) for w in originals]
    requests += [build_request(make_custom_id(arm.key, w, REPEAT_INDEX), w, common.MAX_COMPLETION_TOKENS) for w in repeats]
    created = common.model_created_at(common.openai_client()) if args.online else None
    selection = {"end_min": start, "end_max": end, "limit": args.limit, "sample": args.sample, "seed": args.seed,
                 "repeat_fraction": args.repeat_fraction, "include_done": args.include_done,
                 "include_inflight": args.include_inflight, "n_windows_in_range": len(pool),
                 "pool_window_end_min": pool[0]["window_end"], "pool_window_end_max": pool[-1]["window_end"],
                 "windows_series": window_series, "n_done": len(done),
                 "n_awaiting_retry": len(awaiting), "n_in_flight": len(in_flight), "n_originals": len(originals),
                 "n_repeats": len(repeats), "repeat_target": target, "repeats_already_requested": requested,
                 "windows_source": "db" if args.from_db else str(common.parquet_path("windows", window_series, arm.symbol))}
    rows = create_run(store, arm=arm.key, series_key=window_series, symbol=arm.symbol, requests=requests,
                      mode="batch", max_completion_tokens=common.MAX_COMPLETION_TOKENS, chunk_size=args.chunk_size,
                      metadata={"selection": selection}, model_created_at=created)  # fmt: skip
    print_generated(rows)
    return 0


def print_generated(rows: Sequence[Dict[str, Any]]) -> None:
    run_id = rows[0]["run_metadata"]["parent_run_id"]
    projected = sum(r["run_metadata"]["projected_cost_usd"] for r in rows)
    print(f"{len(rows)} chunk(s), {sum(r['n_requests'] for r in rows)} requests, projected cost ${projected:.4f} "
          f"({rows[0]['mode']} rates, {PROJECTED_PROMPT_TOKENS} prompt + {PROJECTED_COMPLETION_TOKENS} completion tokens each)")  # fmt: skip
    for row in rows:
        print(f"  {row['run_id']}: {row['n_requests']} requests, windows {row['window_end_min']}..{row['window_end_max']}, "
              f"{chunk_paths(row).input} sha256 {row['input_sha256'][:12]}")  # fmt: skip
    print(f"next: {Path(__file__).name} {'submit' if rows[0]['mode'] == 'batch' else 'ingest'} --run-id {run_id}")
    print(f"RUN_ID={run_id}")


def verify_input(run: Dict[str, Any]) -> None:
    """The chunk about to be paid for is the file that was generated (hash and line count)."""
    path = chunk_paths(run).input
    if not path.exists():
        raise RunnerError(f"{path} is missing; regenerate the run")
    if common.sha256_file(path) != run["input_sha256"]:
        raise RunnerError(f"{path} changed since generate (sha256 differs from the runs row); regenerate the run")
    with open(path, "rb") as fh:
        if sum(1 for _ in fh) != run["n_requests"]:
            raise RunnerError(f"{path} does not hold {run['n_requests']} lines")


def cmd_submit(store: Store, args: argparse.Namespace) -> int:
    """Upload each 'generated' chunk and create its batch; every chunk is recorded the moment its batch exists."""
    chunks = chunk_runs(store, args.run_id)
    todo = [r for r in chunks if r["status"] == "generated"]
    for run in chunks:
        if run not in todo:
            log.info("%s is already %s (batch %s): skipping", run["run_id"], run["status"], run["openai_batch_id"])
    if not todo:
        log.info("nothing to submit")
        return 0
    for run in todo:
        verify_input(run)
    if not args.force:
        refuse_duplicate_requests(store, todo)
    projected = sum(r["run_metadata"]["projected_cost_usd"] for r in todo)
    check_budget(store, projected, args.budget, args.force, f"submit {len(todo)} chunk(s) of {args.run_id}")
    if args.dry_run:
        print(f"dry run: would submit {len(todo)} chunk(s) ({sum(r['n_requests'] for r in todo)} requests) for ${projected:.4f}")
        return 0
    client = common.openai_client()
    created = common.model_created_at(client)
    for run in todo:
        batch = find_batch(client, run["run_id"])
        if batch is None:
            uploaded = upload_input(client, chunk_paths(run).input)
            batch = client.batches.create(
                input_file_id=uploaded.id, endpoint="/v1/chat/completions",
                completion_window=common.BATCH_COMPLETION_WINDOW,
                metadata={"run_id": run["run_id"], "arm": run["arm"], "experiment": EXPERIMENT},
            )  # fmt: skip
        else:
            log.warning("%s: adopting batch %s created by an earlier submit", run["run_id"], batch.id)
        row = apply_batch(run, batch)
        row["model_created_at"] = created or row["model_created_at"]
        write_json(chunk_paths(row).batch, row["run_metadata"]["batch"])  # on disk before anything can fail
        with store.transaction():
            store.save_runs([row])
        log.info("%s: batch %s (%s), input file %s", row["run_id"], batch.id, batch.status, batch.input_file_id)
    print(f"submitted {len(todo)} chunk(s); next: {Path(__file__).name} poll --run-id {args.run_id} --wait")
    return 0


def rejected_at_validation(run: Dict[str, Any]) -> Optional[str]:
    """The error code when a batch failed before any request ran (nothing billed), else None.

    The Batch API rejects a whole file when the organisation's enqueued-token quota for the model is full
    (``token_limit_exceeded``); such a chunk is unchanged on disk and can be sent again once room exists.
    """
    if run["status"] != "failed":
        return None
    batch = (run.get("run_metadata") or {}).get("batch") or {}
    counts = batch.get("request_counts") or {}
    if counts.get("completed") or counts.get("failed") or batch.get("output_file_id") or batch.get("error_file_id"):
        return None
    errors = ((batch.get("errors") or {}).get("data") or [])
    return (errors[0].get("code") if errors else None) or "rejected"


def cmd_requeue(store: Store, args: argparse.Namespace) -> int:
    """Send chunks rejected at validation (quota) again, keeping their files; wait for room when asked."""
    from openai import OpenAIError

    client = common.openai_client()
    deadline = time.monotonic() + 3600 * args.max_hours
    while True:
        store.wait_out_busy_window()
        runs = [r for r in store.load_runs() if r["mode"] == "batch" and common.counts_toward_budget(r)]
        if args.run_id:
            runs = [r for r in runs if r["run_id"] == args.run_id or r["run_metadata"].get("parent_run_id") == args.run_id]
        todo = [r for r in runs if rejected_at_validation(r)]
        if not todo:
            log.info("no chunk waits for a new batch")
            return 0
        blocked = False
        for run in todo:
            if run["openai_batch_id"]:  # the retrieve of the rejection may be older than the state on the server
                try:
                    run = refresh_run(store, client, run)
                except OpenAIError as exc:
                    log.warning("%s: %s", run["run_id"], _scrub(str(exc)))
                    continue
                if not rejected_at_validation(run):
                    continue
            verify_input(run)
            history = list(run["run_metadata"].get("superseded_batches") or [])
            history.append({"batch_id": run["openai_batch_id"], "error": rejected_at_validation(run),
                            "failed_at": run["completed_at"]})  # fmt: skip
            input_file_id = run["input_file_id"]
            try:
                client.files.retrieve(input_file_id) if input_file_id else None
            except OpenAIError:
                input_file_id = None
            if not input_file_id:
                input_file_id = upload_input(client, chunk_paths(run).input).id
            batch = client.batches.create(
                input_file_id=input_file_id, endpoint="/v1/chat/completions",
                completion_window=common.BATCH_COMPLETION_WINDOW,
                metadata={"run_id": run["run_id"], "arm": run["arm"], "experiment": EXPERIMENT},
            )  # fmt: skip
            row = dict(run, status="submitted", completed_at=None, est_cost_usd=None, prompt_tokens=None,
                       completion_tokens=None, reasoning_tokens=None, submitted_at=None, output_file_id=None,
                       error_file_id=None)  # fmt: skip
            row = apply_batch(row, batch)
            row["run_metadata"] = {**row["run_metadata"], "superseded_batches": history}
            write_json(chunk_paths(row).batch, row["run_metadata"]["batch"])
            with store.transaction():
                store.save_runs([row])
            log.info("%s: new batch %s (%s) replaces %s", row["run_id"], batch.id, batch.status, history[-1]["batch_id"])
            time.sleep(args.settle)  # validation takes seconds; read the verdict before sending the next chunk
            row = refresh_run(store, client, row)
            if rejected_at_validation(row):
                log.info("%s: rejected again (%s); the queue is full", row["run_id"], rejected_at_validation(row))
                blocked = True
                break
        if not blocked:
            continue  # look for further rejected chunks (or finish)
        if not args.wait or time.monotonic() > deadline:
            print("queue full: run again later (or with --wait)")
            return 1
        log.info("waiting %d s for room in the queue", args.interval)
        time.sleep(args.interval)


def describe(run: Dict[str, Any]) -> str:
    batch = (run["run_metadata"] or {}).get("batch") or {}
    counts = batch.get("request_counts") or {}
    return (f"{run['run_id']}  {run['status']:<11} {run['openai_batch_id'] or '-':<40} "
            f"done {counts.get('completed', 0)}/{counts.get('total', run['n_requests'])} failed {counts.get('failed', 0)}")  # fmt: skip


def cmd_poll(store: Store, args: argparse.Namespace) -> int:
    """Refresh status, counts and usage of the submitted chunks; with --wait, until every chunk has finished."""
    from openai import OpenAIError

    chunk_runs(store, args.run_id)  # an unknown run id (or a backfill) fails here, before the API key is read
    client = common.openai_client()
    while True:
        store.wait_out_busy_window()
        chunks = chunk_runs(store, args.run_id)
        for i, run in enumerate(chunks):
            if run["openai_batch_id"] and run["status"] != "ingested":
                try:
                    chunks[i] = refresh_run(store, client, run)
                except OpenAIError as exc:
                    log.warning("%s: %s", run["run_id"], _scrub(str(exc)))
            print(describe(chunks[i]))
        if not args.wait or all(r["status"] in FINISHED or not r["openai_batch_id"] for r in chunks):
            return 0
        time.sleep(args.interval)


def cmd_retrieve(store: Store, args: argparse.Namespace) -> int:
    """Download the output and error files of finished batches verbatim (existing local files are kept)."""
    chunks = chunk_runs(store, args.run_id)  # validated before the API key is read
    client = common.openai_client()
    for chunk in chunks:
        if not chunk["openai_batch_id"]:
            log.info("%s was never submitted", chunk["run_id"])
            continue
        run = refresh_run(store, client, chunk)
        if run["status"] in ("submitted", "in_progress"):
            log.info("%s is still %s", run["run_id"], run["status"])
            continue
        paths = chunk_paths(run)
        for file_id, target in ((run["output_file_id"], paths.output), (run["error_file_id"], paths.errors)):
            if file_id and not target.exists():
                write_atomic(target, client.files.content(file_id).content)
                log.info("%s: downloaded %s (%d bytes)", run["run_id"], target.name, target.stat().st_size)
        if run["status"] == "failed":
            log.error("%s: batch failed: %s", run["run_id"], run["run_metadata"]["batch"].get("errors"))
        if paths.output.exists():
            run["output_sha256"] = common.sha256_file(paths.output)
            lines = len(read_jsonl(paths.output)) + (len(read_jsonl(paths.errors)) if paths.errors.exists() else 0)
            if lines != run["n_requests"]:
                log.warning("%s: %d output+error lines for %d requests", run["run_id"], lines, run["n_requests"])
        with store.transaction():
            store.save_runs([run])
    return 0


def ingest_chunks(store: Store, runs: Sequence[Dict[str, Any]],
                  from_db: bool) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:  # fmt: skip
    """Parse retrieved chunks, upsert detections and update the runs rows (one transaction per chunk)."""
    cache: Dict[Tuple[str, str], Dict[date, Dict[str, Any]]] = {}
    results = []
    for run in runs:
        key = (run_window_series(run), run["symbol"])
        if key not in cache:
            cache[key] = {w["window_end"]: w for w in store.load_windows(*key, from_db)}
        updated, rows, summary = parse_chunk(run, cache[key])
        with store.transaction():
            store.save_detections(updated["run_id"], rows)
            store.save_runs([updated])
        print(f"{updated['run_id']}: {updated['n_requests']} requests, {updated['n_responses']} answers | "
              f"parse {summary['parse_status']} | finish {summary['finish_reason']} | "
              f"retry pending {summary['n_retry_pending']} | metrics agree "
              f"{summary['n_metrics_agree']}/{summary['n_metrics_checked']} | "
              f"tokens in/out {updated['prompt_tokens']:,}/{updated['completion_tokens']:,} | "
              f"cost ${updated['est_cost_usd']:.4f}")  # fmt: skip
        results.append((updated, rows))
    return results


def cmd_ingest(store: Store, args: argparse.Namespace) -> int:
    chunks = chunk_runs(store, args.run_id)
    ready = [r for r in chunks if any(p.exists() for p in (chunk_paths(r).output, chunk_paths(r).errors))]
    for run in chunks:
        if run not in ready:
            log.warning("%s: no output or error file yet (run retrieve)", run["run_id"])
    if not ready:
        raise RunnerError(f"nothing to ingest for {args.run_id}: run 'retrieve' first")
    ingest_chunks(store, ready, args.from_db)
    return 0


def sync_call(client: Any, request: Request) -> Dict[str, Any]:
    """One chat completion, returned in the shape of a Batch output line so that ingest treats both alike."""
    try:
        response = client.chat.completions.create(**request.line["body"])
    except Exception as exc:  # deliberate: any API failure becomes an error line and the other calls go on
        error = {"type": type(exc).__name__, "status_code": getattr(exc, "status_code", None),
                 "message": _scrub(str(exc))[:2000]}  # fmt: skip
        return {"custom_id": request.custom_id, "response": None, "error": error}
    return {"custom_id": request.custom_id, "error": None,
            "response": {"status_code": 200, "request_id": getattr(response, "_request_id", None),
                         "body": response.model_dump(mode="json")}}  # fmt: skip


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> Optional[float]:
    if not a:
        return None
    p_obs = sum(x == y for x, y in zip(a, b, strict=True)) / len(a)
    p_a, p_b = sum(a) / len(a), sum(b) / len(b)
    p_exp = p_a * p_b + (1 - p_a) * (1 - p_b)
    return None if p_exp == 1 else (p_obs - p_exp) / (1 - p_exp)


def r1_labels() -> Dict[date, bool]:
    """regime_detected of the published o4-mini answers, recovered from the surviving January output file."""
    labels = {}
    for end, line in common.load_phase4a_outputs().items():
        try:
            content = line["response"]["body"]["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            continue
        payload, _ = common.parse_llm_content(content)
        if payload is not None and payload["regime_detected"] is not None:
            labels[end] = payload["regime_detected"]
    return labels


def print_pilot_summary(run: Dict[str, Any], rows: Sequence[Dict[str, Any]], windows: Dict[date, Dict[str, Any]],
                        series_key: str) -> None:  # fmt: skip
    n = len(rows)
    parsed = [r for r in rows if r["parse_status"] in PARSED]
    stat = Counter(r["parse_status"] for r in rows)

    def mean_max(name: str) -> str:
        values = [r[name] for r in rows if r[name] is not None]
        return f"mean {sum(values) / len(values):,.0f} max {max(values):,}" if values else "n/a"

    print(f"\nPILOT SUMMARY  arm {run['arm']}  run {run['run_id']}  model {run['model']}")
    print(f"  requests {n} | parse ok {stat['ok']} fallback {stat['fallback']} failed {stat['failed']} "
          f"missing {stat['missing']} (parse rate {100 * len(parsed) / n:.1f}%)")  # fmt: skip
    print(f"  tokens: prompt {mean_max('prompt_tokens')} | completion {mean_max('completion_tokens')} | "
          f"reasoning {mean_max('reasoning_tokens')}")  # fmt: skip
    per_request = run["est_cost_usd"] / n
    mean_in = run["prompt_tokens"] / n
    mean_out = run["completion_tokens"] / n
    batch_cost = common.estimate_cost_usd(run["model"], "batch", mean_in, mean_out)
    print(f"  cost: ${run['est_cost_usd']:.4f} at standard rates (${per_request:.5f} per request); "
          f"batch rates ${batch_cost:.5f} per request = ${1000 * batch_cost:.2f} per 1,000")  # fmt: skip
    pairs = [(r["regime_detected"], windows[r["window_end"]]["clf_should_detect"]) for r in parsed
             if r["window_end"] in windows]  # fmt: skip
    if pairs:
        llm, clf = [p[0] for p in pairs], [p[1] for p in pairs]
        kappa = cohen_kappa(llm, clf)
        types = sum(r["regime_type"] == windows[r["window_end"]]["clf_regime_type"] for r in parsed if r["window_end"] in windows)
        print(f"  vs deterministic classifier: verdict agrees {sum(x == y for x, y in pairs)}/{len(pairs)}, "
              f"kappa {'n/a' if kappa is None else f'{kappa:.2f}'}, regime_type agrees {types}/{len(pairs)}, "
              f"reported metrics agree {sum(bool(r['metrics_agree']) for r in parsed)}/{len(parsed)}")  # fmt: skip
    if series_key == "jan2026_phase4a":
        old = r1_labels()
        shared = [(r["regime_detected"], old[r["window_end"]]) for r in parsed if r["window_end"] in old]
        kappa = cohen_kappa([p[0] for p in shared], [p[1] for p in shared])
        print(f"  vs r1_o4mini (published): verdict agrees {sum(x == y for x, y in shared)}/{len(shared)}, "
              f"kappa {'n/a' if kappa is None else f'{kappa:.2f}'}")  # fmt: skip


def cmd_pilot(store: Store, args: argparse.Namespace) -> int:
    """Synchronous calls on a sample balanced on clf_should_detect, recorded and ingested like a batch run."""
    arm = common.ARMS[args.arm]
    pilot_arm = PILOT_ARM_PREFIX + arm.key
    start, end = common.arm_date_range(arm)
    window_series = common.arm_window_series(arm)
    windows = [w for w in store.load_windows(window_series, arm.symbol, args.from_db) if start <= w["window_end"] <= end]
    sample = balanced_sample(windows, args.n, args.seed, pilot_arm)
    if not sample:
        raise RunnerError(f"no {window_series}/{arm.symbol} windows to sample")
    requests = [build_request(make_custom_id(pilot_arm, w), w, common.MAX_COMPLETION_TOKENS) for w in sample]
    per_request = common.estimate_cost_usd(common.MODEL, "standard", PROJECTED_PROMPT_TOKENS, PROJECTED_COMPLETION_TOKENS)
    check_budget(store, per_request * len(requests), args.budget, args.force, f"pilot of {len(requests)} synchronous calls")
    client = common.openai_client()
    run = create_run(store, arm=pilot_arm, series_key=window_series, symbol=arm.symbol, requests=requests, mode="sync",
                     max_completion_tokens=common.MAX_COMPLETION_TOKENS, chunk_size=len(requests),
                     metadata={"selection": {"n": len(requests), "seed": args.seed, "workers": args.workers,
                                             "balanced_on": "clf_should_detect"}},
                     model_created_at=common.model_created_at(client))[0]  # fmt: skip
    paths = chunk_paths(run)
    started = common.utcnow()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        answers = list(pool.map(lambda r: sync_call(client, r), requests))
    failed = [a for a in answers if a["error"] is not None]
    write_atomic(paths.output, jsonl_bytes(a for a in answers if a["error"] is None))
    if failed:
        write_atomic(paths.errors, jsonl_bytes(failed))
    run.update(status="completed", submitted_at=started, completed_at=common.utcnow(),
               output_sha256=common.sha256_file(paths.output))  # fmt: skip
    with store.transaction():
        store.save_runs([run])
    if failed:
        log.warning("%d of %d calls failed, e.g. %s", len(failed), len(requests), failed[0]["error"])
    [(updated, rows)] = ingest_chunks(store, [run], args.from_db)
    by_end = {w["window_end"]: w for w in windows}
    print_pilot_summary(updated, rows, by_end, arm.series_key)
    print(f"RUN_ID={updated['run_metadata']['parent_run_id']}")
    return 0


def cmd_retry(store: Store, args: argparse.Namespace) -> int:
    """New run for the answers of a run that were cut off by the token limit, at RETRY_MAX_COMPLETION_TOKENS."""
    chunks = chunk_runs(store, args.run_id)
    first = chunks[0]
    cut_off = [row for run in chunks for row in store.load_detections(run["run_id"]) if row["finish_reason"] == "length"]
    if cut_off:
        index = store.detection_index({r["arm"] for r in cut_off}, first["model"], first["prompt_version"])
        cut_off = [r for r in cut_off if window_state(index.get((r["arm"], r["window_end"]), ())) == "retry"]
    if cut_off and not args.include_inflight:
        held = pending_requests(store, {first["arm"]}, first["model"], first["prompt_version"])
        covered = [r for r in cut_off if (r["arm"], r["window_end"]) in held]
        if covered:
            log.info("%d cut-off answer(s) are already requested again by %s: skipping them "
                     "(--include-inflight requests them anyway)",
                     len(covered), ", ".join(sorted({held[(r["arm"], r["window_end"])] for r in covered})))  # fmt: skip
            cut_off = [r for r in cut_off if (r["arm"], r["window_end"]) not in held]
    if not cut_off:
        log.info("no answers of %s still wait for a retry", args.run_id)
        return 0
    windows = {w["window_end"]: w for w in store.load_windows(run_window_series(first), first["symbol"], args.from_db)}
    vanished = sorted({str(r["window_end"]) for r in cut_off if r["window_end"] not in windows})
    if vanished:
        raise RunnerError(f"windows {vanished[:3]} are no longer in the windows table")
    requests = [build_request(r["custom_id"], windows[r["window_end"]], common.RETRY_MAX_COMPLETION_TOKENS)
                for r in sorted(cut_off, key=lambda r: (r["window_end"], r["custom_id"]))]  # fmt: skip
    rows = create_run(store, arm=first["arm"], series_key=first["series_key"], symbol=first["symbol"],
                      requests=requests, mode="batch", max_completion_tokens=common.RETRY_MAX_COMPLETION_TOKENS,
                      chunk_size=args.chunk_size,
                      metadata={"retry_of": [r["run_id"] for r in chunks], "reason": "finish_reason=length"})  # fmt: skip
    print_generated(rows)
    return 0


def cmd_status(store: Store, args: argparse.Namespace) -> int:
    """Runs, cost ledger and per-arm detection state."""
    every = store.load_runs()
    runs = [r for r in every if args.run_id in (None, r["run_id"], (r["run_metadata"] or {}).get("parent_run_id"))]
    print(f"{'run_id':<58} {'arm':<16} {'mode':<5} {'status':<11} {'req':>5} {'parsed':>6} {'cost $':>9}  window_end")
    for r in runs:
        counted = common.counts_toward_budget(r)
        cost = run_cost(r) if counted else float(r["est_cost_usd"] or 0.0)
        print(f"{r['run_id']:<58} {r['arm']:<16} {r['mode']:<5} {r['status']:<11} "
              f"{'-' if r['n_requests'] is None else r['n_requests']:>5} "
              f"{'-' if r['n_parsed'] is None else r['n_parsed']:>6} {cost:>8.4f}{' ' if counted else '*'}  "
              f"{r['window_end_min']}..{r['window_end_max']}")  # fmt: skip
    counted_runs = [r for r in every if common.counts_toward_budget(r)]
    spent = sum(run_cost(r) for r in counted_runs)
    print(f"\ncost ledger: ${spent:.4f} committed over {len(counted_runs)} run(s); budget {usd(args.budget)}, "
          f"${args.budget - spent:.4f} left")  # fmt: skip
    outside = [r for r in every if not common.counts_toward_budget(r)]
    if outside:
        total = sum(float(r["est_cost_usd"] or 0.0) for r in outside)
        print(f"* outside the budget, paid before the current balance and never counted (${total:.4f} over "
              f"{len(outside)} backfilled run(s)): "
              + ", ".join(f"{r['run_id']} ${float(r['est_cost_usd'] or 0.0):.4f}" for r in outside))  # fmt: skip
    index = store.detection_index(None, common.MODEL, common.PROMPT_VERSION)
    held = pending_requests(store, None, common.MODEL, common.PROMPT_VERSION)
    states: Dict[str, Counter] = {}
    for key in sorted(set(index) | set(held)):
        stored = window_state(index.get(key, ()))
        states.setdefault(key[0], Counter())["inflight" if key in held and stored != "done" else stored] += 1
    if states:
        print(f"\n{'arm':<20} {'windows':>8} {'done':>6} {'retry':>6} {'inflight':>8} {'open':>6}   "
              "(state of each window across all runs)")  # fmt: skip
        for arm, count in sorted(states.items()):
            print(f"{arm:<20} {sum(count.values()):>8} {count['done']:>6} {count['retry']:>6} "
                  f"{count['inflight']:>8} {count['open']:>6}")  # fmt: skip
    return 0


# --------------------------------------------------------------------------- command line
def _bounded_int(low: int, high: Optional[int] = None):
    def parse(text: str) -> int:
        value = int(text)
        if value < low or (high is not None and value > high):
            raise argparse.ArgumentTypeError(f"must be between {low} and {high if high is not None else 'infinity'}")
        return value

    return parse


def _fraction(text: str) -> float:
    value = float(text)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="gpt-6-luna runner for the Electronics extension: generate -> submit -> poll -> retrieve -> ingest.",
        epilog=("Typical run: generate --arm full_spy; submit --run-id R; poll --run-id R --wait; "
                "retrieve --run-id R; ingest --run-id R.  Windows come from 02_build_windows.py "
                "(tables/windows/<series>_<symbol>.parquet)."),
    )
    storage = argparse.ArgumentParser(add_help=False)
    group = storage.add_argument_group("storage")
    group.add_argument("--parquet-only", action="store_true", help="never connect to Postgres; parquet and files only")
    group.add_argument("--rollback", action="store_true",
                       help="apply the schema inline, run every database write, then roll the transaction back (testing)")  # fmt: skip
    group.add_argument("--backup-root", type=Path,
                       help="alternative root for raw run backups and parquet copies (default: data/backups/gex_llm)")  # fmt: skip
    group.add_argument("--ignore-busy-window", action="store_true",
                       help="allow Postgres writes between 21:50 and 22:45 UTC (the monitors rebuild the daily tables)")  # fmt: skip
    group.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    source = argparse.ArgumentParser(add_help=False)
    source.add_argument("--from-db", action="store_true", help="read windows from Postgres instead of parquet")
    budget = argparse.ArgumentParser(add_help=False)
    budget.add_argument("--budget", type=float, default=common.BUDGET_USD_HARD_STOP,
                        help="USD ceiling for ledger + projected cost (default: %(default)s)")  # fmt: skip
    spend = argparse.ArgumentParser(add_help=False, parents=[budget])
    spend.add_argument("--force", action="store_true",
                       help="go ahead although the budget would be exceeded or a chunk repeats requests that were "
                            "already sent or answered")  # fmt: skip
    arms = sorted(a.key for a in common.ARMS.values() if a.llm)
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    def command(name: str, func: Callable[[Store, argparse.Namespace], int], help_text: str,
                *parents: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p = sub.add_parser(name, parents=[storage, *parents], help=help_text, description=help_text)
        p.set_defaults(func=func)
        return p

    p = command("generate", cmd_generate, "write Batch input chunks and 'generated' runs rows (no network, no cost)", source)
    p.add_argument("--arm", required=True, choices=arms)
    p.add_argument("--end-min", type=date.fromisoformat, help="first window_end to run (default: arm start)")
    p.add_argument("--end-max", type=date.fromisoformat, help="last window_end to run (default: arm end)")
    p.add_argument("--limit", type=_bounded_int(1), help="run at most N windows (first N, or see --sample)")
    p.add_argument("--sample", choices=("all", "stratified"), default="all",
                   help="with --limit: 'all' = the first N windows; 'stratified' = N spread over calendar years")  # fmt: skip
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help="seed of the reproducible hash-rank sampling")
    p.add_argument("--repeat-fraction", type=_fraction, default=common.REPEAT_FRACTION,
                   help="also send this fraction of the windows a second time for test-retest, stored under arm "
                        "'<arm>#rep1' (default: %(default)s, decision D-09; 0 turns it off and logs a warning)")  # fmt: skip
    p.add_argument("--chunk-size", type=_bounded_int(1, common.BATCH_MAX_REQUESTS), default=common.BATCH_MAX_REQUESTS,
                   help="maximum requests per Batch job (default: %(default)s)")  # fmt: skip
    p.add_argument("--include-done", action="store_true", help="also run windows that already have an answer")
    p.add_argument("--include-inflight", action="store_true",
                   help="also run windows that a generated, submitted or not yet ingested run already holds")  # fmt: skip
    p.add_argument("--online", action="store_true", help="record the model object's created timestamp (free API call)")

    p = command("submit", cmd_submit, "upload and create the batches of a run (spends money; budget-guarded)", spend)
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true", help="show the ledger check and the plan, call nothing")

    p = command("poll", cmd_poll, "refresh the status and usage of submitted batches")
    p.add_argument("--run-id", required=True)
    p.add_argument("--wait", action="store_true", help="keep polling until every chunk has finished")
    p.add_argument("--interval", type=_bounded_int(1), default=60, help="seconds between polls (default: %(default)s)")

    command("retrieve", cmd_retrieve, "download output and error files verbatim").add_argument("--run-id", required=True)
    command("ingest", cmd_ingest, "parse retrieved answers into detections (idempotent)", source).add_argument(
        "--run-id", required=True)  # fmt: skip

    p = command("pilot", cmd_pilot, "synchronous calls on a classifier-balanced sample (spends money)", source, spend)
    p.add_argument("--arm", required=True, choices=arms)
    p.add_argument("--n", type=_bounded_int(2), default=common.PILOT_WINDOWS, help="windows (default: %(default)s)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--workers", type=_bounded_int(1, 16), default=4, help="parallel calls (default: %(default)s)")

    p = command("requeue", cmd_requeue, "send chunks rejected at validation (quota) again, same files", budget)
    p.add_argument("--run-id", help="restrict to this run (default: every rejected chunk that counts as spend)")
    p.add_argument("--wait", action="store_true", help="keep trying until every rejected chunk is accepted")
    p.add_argument("--interval", type=_bounded_int(1), default=300, help="seconds between tries (default: %(default)s)")
    p.add_argument("--settle", type=_bounded_int(1), default=20, help="seconds before reading the validation verdict")
    p.add_argument("--max-hours", type=float, default=24.0, help="give up waiting after this long")
    p = command("retry", cmd_retry, "regenerate answers cut off by the token limit at a larger cap", source)
    p.add_argument("--run-id", required=True)
    p.add_argument("--include-inflight", action="store_true",
                   help="also retry answers that a pending retry run already asks for")  # fmt: skip
    p.add_argument("--chunk-size", type=_bounded_int(1, common.BATCH_MAX_REQUESTS), default=common.BATCH_MAX_REQUESTS)

    p = command("status", cmd_status, "runs, cost ledger and per-arm detection state", budget)
    p.add_argument("--run-id", help="restrict the run list to this run or chunk")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.parquet_only and args.rollback:
        parser.error("--parquet-only and --rollback are mutually exclusive")
    if args.command == "generate" and args.sample == "stratified" and args.limit is None:
        parser.error("--sample stratified needs --limit")
    common.setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    if args.backup_root is not None:  # common reads these module globals at call time
        common.BACKUP_ROOT, common.PARQUET_ROOT = args.backup_root, args.backup_root / "tables"
    mode = "parquet" if args.parquet_only else "rollback" if args.rollback else "auto"
    try:
        with Store(mode, writes=args.command != "status", ignore_busy_window=args.ignore_busy_window) as store:
            return args.func(store, args)
    except RunnerError as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
