#!/usr/bin/env python3
"""Backfill the three published o4-mini batch runs of Paper 2 as the arms r1_o4mini, r1_p3_o4mini and r1_p4_o4mini.

All three were OpenAI Batch runs whose raw output survives next to the input file, but the pipeline of the time kept
only a parsed copy of the answers: the ResearchCache rows (r1_o4mini) or a result YAML (the other two).  Each arm is
rebuilt from the batch output itself:

* ``r1_o4mini``     Phase 4A, batch of 2026-01-04: SPY 2020-2025, 1,476 windows, "Day T-k" labels.  The January
  ingestion kept only the 1,412 answers that a greedy ``{.*}`` regex plus a strict ``json.loads`` could read, in the
  SQLite ResearchCache (``.cache/research_cache.db``, pattern ``regime_30day``): 12.2 / 3.7 / 32.4 / 20.2 / 100 / 100 %
  detected for 2020-2025.  The 64 windows the ingestion lost are kept and flagged
  ``detection_metadata = {"recovered_2026": true}``; they are not part of the published result.
* ``r1_p3_o4mini``  Phase 3, batch of 2025-11-20: SPY 2024, 223 windows, calendar dates as labels in the prompt:
  181 of 223 detected (81.2%).  Published record: ``reports/validation/paper2_regime_windows/
  phase3_baseline_2024_full_year.yaml``.
* ``r1_p4_o4mini``  Phase 4, batch of 2025-11-20: SPY 2020, 223 windows, dates as labels: 27 of 223 detected (12.1%),
  ``phase4_baseline_2020.yaml``.  Three answers wrote the confidence as a word ("ninety-five"); the November ingestion
  recorded them as parse errors and counted them as not detected, the shared parser reads them (verdict false).

For every arm:

1. each output line is parsed with ``common.parse_llm_content`` (``parse_status`` ok / fallback); one January
   answer (2023-08-07) is a fenced JSON with a raw newline inside a string, which the shared parser's
   ``strict=False`` retry cannot reach through the fence: its bare JSON text is handed to it and the row is flagged
   ``lenient_json``;
2. the parse is cross-checked field by field against the published record (ResearchCache opened read-only, or the
   result YAML when it is present), and the prompt of every request is rebuilt with ``common.build_prompt`` and
   compared with the recorded request text;
3. nothing is written for any arm unless the published yearly detection rates (and, for the November runs, the
   headline counts 181/223 and 27/223) are reproduced from the published windows;
4. the two JSONL files are copied to ``data/backups/gex_llm/<run_id>/`` with a manifest, and parquet copies of the
   ``runs`` / ``detections`` rows are written (``common.parquet_path``, ``tables/<kind>/<arm>.parquet``);
5. optionally the rows are upserted into ``backups.gex_llm_regime_runs`` / ``_detections``.

``metrics_agree`` compares the metrics the model reported with ``common.classify`` of the 30 values shown to it (the
dated values for the November runs).  ``model`` is ``o4-mini-2025-04-16`` for r1_o4mini, as the responses report it,
and ``o4-mini`` (the alias the November requests asked for) for the other two; the responses of those report
``o4-mini-2025-04-16``, see ``run_metadata.response``.  ``prompt_version`` is ``v2.0_postgresql`` for all three: the
prompt rebuilt with the shared builder equals the recorded request text (``run_metadata.request.prompt_check``).

Modes (mutually exclusive)::

    (no flag)       the same as --parquet-only
    --parquet-only  raw backup + manifest + parquet copies; never connects to Postgres (the default)
    --dry-run       parse, cross-check and report; writes nothing and never connects to Postgres
    --rollback      schema SQL + upserts inside ONE transaction, rows read back, then ROLLBACK; nothing persists
                    and no file is written (works before the tables exist)
    --db            raw backup + manifest + parquet copies, then upsert and COMMIT; the tables must already
                    exist, this script never creates them

``--rollback`` and ``--db`` refuse to run between 21:50 and 22:45 UTC (the monitors rebuild the daily tables) unless
``--ignore-busy-window`` is given.  ``--arm`` limits the run to some arms (default: all three).

The published set is the rows without the recovered flag; the November arms have none, so it is every row::

    WHERE arm = 'r1_o4mini' AND detection_metadata ->> 'recovered_2026' IS NULL

Times are UTC.  A batch's creation time is decoded from its id (the leading 8 hex digits are Unix seconds); the
``batch_*_metadata.json`` files of the November batches hold a client-side ``created_at`` as a naive US/Eastern
timestamp, which is converted and must agree within 2 s.

Run from the repository root with the AutoGex conda env::

    source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
    PYTHONPATH=$(pwd) python scripts/validation/electronics/03_backfill_round1.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
import textwrap
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

import common

logger = logging.getLogger("electronics.backfill_round1")


class BackfillError(RuntimeError):
    """The batch output does not reproduce the published run, or its published record is unusable."""


# --------------------------------------------------------------------------- the backfilled runs
# Yearly detection rate (% of the cached windows) reported in Paper 2, AIAI 2026 and JRFM for Phase 4A.
PHASE4A_RATES_PCT = {2020: 12.2, 2021: 3.7, 2022: 32.4, 2023: 20.2, 2024: 100.0, 2025: 100.0}
# First commit holding phase4a_postgresql_batch.py.  The batch was submitted on 2026-01-04 18:54Z, about 7.5 hours
# before this commit was made (2026-01-05 02:24Z), so the run itself came from an uncommitted tree.
GENERATING_COMMIT = "e58f7d607c42e3880a6b92b250c2035bb946ad7c"
# The two OpenAI files of the January batch (both expired); which was the input and which the output was not recorded.
EXPIRED_FILE_IDS = ("file-46GWLecWpzfrCTU6fQtcsh", "file-NUB1tA83KVboBvCJqcMEkU")
RESULT_DIR = common.PHASE4A_DIR.parent  # reports/validation/paper2_regime_windows
# The commit that added both result YAMLs (2025-11-30); the working copies are unmodified.
RESULT_YAML_COMMIT = "477bb41"
# Contract decision 9: the November arms store the alias their requests asked for.  The responses report the dated
# snapshot (common.R1_MODEL, the value of the January arm); run_metadata.response keeps what each response said.
R1_PHASE34_MODEL = "o4-mini"
PHASE34_GIT_NOTE = (
    "the script that generated the dated Phase 3/4 input files is not identified (second audit, open items); "
    f"the result YAML was added to the repository in {RESULT_YAML_COMMIT}"
)
PARSED = ("ok", "fallback")  # parse_status values that carry a verdict
RECOVERED_FLAG = "recovered_2026"  # detection_metadata key; 05_report.py reads it
BATCH_CLOCK_TOLERANCE_S = 2.0  # decoded batch id vs the client-side created_at of the batch metadata file
CLIENT_CLOCK = "America/New_York"  # the client wrote naive local timestamps


@dataclass(frozen=True)
class Backfill:
    """One published OpenAI Batch run and where its published result is recorded."""

    arm: common.Arm
    run_id: str
    model: str  # runs.model / detections.model
    batch_id: str
    input_path: Path
    output_path: Path
    published_pct: Dict[int, float]  # yearly detection rate (%, one decimal) of the published result
    record_kind: str  # "research_cache" (SQLite, mandatory) or "result_yaml" (compared when the file exists)
    record_path: Path
    headline: Optional[Tuple[int, int]] = None  # (windows detected, windows) as printed in the papers
    metadata_path: Optional[Path] = None  # batch_<id>_metadata.json written by the submitting script
    git_sha: Optional[str] = None
    git_sha_note: str = ""
    expired_file_ids: Tuple[str, ...] = ()


def batch_metadata_path(batch_id: str) -> Path:
    return common.PHASE4A_DIR / f"batch_{batch_id}_metadata.json"


SPECS: Dict[str, Backfill] = {
    spec.arm.key: spec
    for spec in (
        Backfill(
            arm=common.ARMS["r1_o4mini"],
            run_id="r1_o4mini_phase4a_20260104",
            model=common.R1_MODEL,
            batch_id=common.PHASE4A_BATCH_ID,
            input_path=common.PHASE4A_INPUT_JSONL,
            output_path=common.PHASE4A_OUTPUT_JSONL,
            published_pct=PHASE4A_RATES_PCT,
            record_kind="research_cache",
            record_path=common.RESEARCH_CACHE_DB,
            git_sha=GENERATING_COMMIT[:7],
            git_sha_note="first commit holding the generating script; the batch was submitted before it was made",
            expired_file_ids=EXPIRED_FILE_IDS,
        ),
        Backfill(
            arm=common.ARMS["r1_p3_o4mini"],
            run_id="r1_p3_o4mini_20251120",
            model=R1_PHASE34_MODEL,
            batch_id=common.PHASE3_BATCH_ID,
            input_path=common.PHASE3_INPUT_JSONL,
            output_path=common.PHASE3_OUTPUT_JSONL,
            published_pct={2024: 81.2},
            headline=(181, 223),
            record_kind="result_yaml",
            record_path=RESULT_DIR / "phase3_baseline_2024_full_year.yaml",
            metadata_path=batch_metadata_path(common.PHASE3_BATCH_ID),
            git_sha_note=PHASE34_GIT_NOTE,
        ),
        Backfill(
            arm=common.ARMS["r1_p4_o4mini"],
            run_id="r1_p4_o4mini_20251120",
            model=R1_PHASE34_MODEL,
            batch_id=common.PHASE4_BATCH_ID,
            input_path=common.PHASE4_INPUT_JSONL,
            output_path=common.PHASE4_OUTPUT_JSONL,
            published_pct={2020: 12.1},
            headline=(27, 223),
            record_kind="result_yaml",
            record_path=RESULT_DIR / "phase4_baseline_2020.yaml",
            metadata_path=batch_metadata_path(common.PHASE4_BATCH_ID),
            git_sha_note=PHASE34_GIT_NOTE,
        ),
    )
}


@dataclass
class PublishedRecord:
    """What the pipeline of the time stored about a run: the ResearchCache rows or the result YAML."""

    source: str  # "research_cache" | "result_yaml"
    path: Path
    sha256: str
    fields: Dict[date, Dict[str, Any]]  # per window: the stored values that can be compared with a parsed answer
    errors: Dict[date, str]  # windows the record lists as parse errors (result YAML only)
    summary: Dict[str, Any]  # statistics the record states about itself (result YAML only)


@dataclass
class Prepared:
    """One backfill that parsed, cross-checked and verified: the rows are ready to be written."""

    spec: Backfill
    records: List[Dict[str, Any]]
    run_row: Dict[str, Any]
    published: Dict[int, Tuple[int, int]]  # year -> (parsed windows, windows detected) over the published windows
    everything: Dict[int, Tuple[int, int]]  # the same over every window
    check: Dict[str, Any]
    files: Dict[str, Dict[str, Any]]
    backup_dir: Path


# --------------------------------------------------------------------------- ResearchCache layout
CACHE_PATTERN_ID = "regime_30day"
CACHE_RAW_LIMIT = 5000  # ResearchCache.record_detection(raw_response=content[:5000])
STRUCTURED_FIELDS = (
    "regime_type",
    "positive_days",
    "negative_days",
    "avg_magnitude_billions",
    "sign_flips",
    "persistence_pct",
)
PAYLOAD_FIELDS = ("regime_detected", "confidence", "reasoning") + STRUCTURED_FIELDS
CROSSCHECK_FIELDS = PAYLOAD_FIELDS + ("token_count", "raw_response")

# --------------------------------------------------------------------------- row layout (sql/gex_llm_regime_schema.sql)
_STR, _BOOL, _INT, _FLOAT = pa.string(), pa.bool_(), pa.int64(), pa.float64()
_DATE, _TS = pa.date32(), pa.timestamp("us", tz="UTC")

# Column names and order follow the CREATE TABLE statements.  The serial key is left to the database; created_at is
# written explicitly (the column is NOT NULL and 04_llm_runner.py orders runs by it): the insert time of a runs row,
# kept by a re-run, and the insert/update time of a detections row, refreshed by every upsert.  JSONB travels as text.
DETECTION_COLUMNS = {
    "run_id": _STR,
    "arm": _STR,
    "series_key": _STR,
    "symbol": _STR,
    "window_end": _DATE,
    "model": _STR,
    "prompt_version": _STR,
    "custom_id": _STR,
    "response_id": _STR,
    "regime_detected": _BOOL,
    "regime_type": _STR,
    "confidence": _FLOAT,
    "positive_days": _INT,
    "negative_days": _INT,
    "avg_magnitude_billions": _FLOAT,
    "sign_flips": _INT,
    "persistence_pct": _FLOAT,
    "metrics_agree": _BOOL,
    "reasoning": _STR,
    "raw_response": _STR,
    "parse_status": _STR,
    "finish_reason": _STR,
    "prompt_tokens": _INT,
    "completion_tokens": _INT,
    "reasoning_tokens": _INT,
    "detection_metadata": _STR,
    "created_at": _TS,
}
DETECTION_KEY = ["arm", "series_key", "symbol", "window_end", "model", "prompt_version"]

RUN_COLUMNS = {
    "run_id": _STR,
    "arm": _STR,
    "series_key": _STR,
    "symbol": _STR,
    "model": _STR,
    "model_created_at": _TS,
    "prompt_version": _STR,
    "reasoning_effort": _STR,
    "response_format": _STR,
    "max_completion_tokens": _INT,
    "mode": _STR,
    "openai_batch_id": _STR,
    "input_file_id": _STR,
    "output_file_id": _STR,
    "error_file_id": _STR,
    "input_sha256": _STR,
    "output_sha256": _STR,
    "backup_dir": _STR,
    "window_end_min": _DATE,
    "window_end_max": _DATE,
    "n_requests": _INT,
    "n_responses": _INT,
    "n_parsed": _INT,
    "n_failed": _INT,
    "prompt_tokens": _INT,
    "completion_tokens": _INT,
    "reasoning_tokens": _INT,
    "est_cost_usd": _FLOAT,
    "status": _STR,
    "submitted_at": _TS,
    "completed_at": _TS,
    "ingested_at": _TS,
    "git_sha": _STR,
    "run_metadata": _STR,
    "created_at": _TS,
}

SCHEMA_OBJECTS = (common.T_SERIES, common.T_WINDOWS, common.T_RUNS, common.T_DETECTIONS, common.T_RATES_VIEW)


# --------------------------------------------------------------------------- parsing
def response_body(line: Dict[str, Any]) -> Dict[str, Any]:
    """Chat-completion body of a batch output line ({} when the line carries no response)."""
    return (line.get("response") or {}).get("body") or {}


FENCE = re.compile(r"\A\s*```(?:json)?[ \t]*\r?\n?(.*?)\s*```\s*\Z", re.DOTALL | re.IGNORECASE)


def unfence(content: str) -> str:
    """The text inside a markdown code fence (the message itself when it has none)."""
    match = FENCE.match(content)
    return match.group(1) if match else content


def lenient_text(content: Optional[str]) -> Optional[str]:
    """The JSON text of an answer that only ``json.loads(strict=False)`` accepts, else None.

    That is an object with a raw control character (a literal newline) inside a string.  One January answer
    (2023-08-07) is of this kind.
    """
    if not isinstance(content, str) or not content.strip():
        return None
    text = unfence(content).strip()
    try:
        json.loads(text)
        return None
    except ValueError:
        pass
    try:
        data = json.loads(text, strict=False)
    except ValueError:
        return None
    return text if isinstance(data, dict) else None


def parse_response(content: Optional[str]) -> Tuple[Optional[Dict[str, Any]], str, bool]:
    """Parse one assistant message into (payload or None, parse_status, lenient).

    ``common.parse_llm_content`` does the parsing.  Its ``json.loads(strict=False)`` retry looks at the whole message,
    so it cannot read an answer that is wrapped in a markdown fence AND holds a raw control character in a string
    (2023-08-07); the bare JSON text of such an answer is handed to it instead, the result is reported as ``fallback``
    (the fence had to go) and ``lenient`` is set.  Nothing here calls ``common.normalize_payload`` directly: a
    structurally bad answer comes back as ``failed`` and cannot abort the backfill.
    """
    text = lenient_text(content)
    if text is None:
        payload, status = common.parse_llm_content(content)
        return payload, status, False
    payload, status = common.parse_llm_content(text)
    if payload is None:
        return None, status, False
    return payload, (status if text == (content or "").strip() else "fallback"), True


def january_parse_ok(content: Optional[str]) -> bool:
    """Replay of the January ingestion: greedy ``{.*}`` regex followed by a strict ``json.loads``."""
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    if not match:
        return False
    try:
        json.loads(match.group(0))
    except ValueError:
        return False
    return True


def window_date(custom_id: str) -> date:
    """Window end of a batch custom_id ('window-2024-02-13')."""
    return date.fromisoformat(custom_id.replace("window-", ""))


# --------------------------------------------------------------------------- the batch files
Inputs = Dict[date, Tuple[Optional[List[date]], List[float]]]


def load_inputs(spec: Backfill) -> Inputs:
    """{window_end: (dates or None, 30 values in USD)}: the values shown to the model, parsed from the input file."""
    series = common.SERIES[spec.arm.series_key]
    if series.labels == "dated":
        parsed = common.load_phase34_inputs(series.key)
        return {end: ([d for d, _ in rows], [v for _, v in rows]) for end, rows in parsed.items()}
    return {end: (None, values) for end, values in common.load_phase4a_inputs().items()}


def load_outputs(spec: Backfill) -> Dict[date, Dict[str, Any]]:
    """{window_end: raw batch output line}."""
    series = common.SERIES[spec.arm.series_key]
    if series.labels == "dated":
        return common.load_phase34_outputs(series.key)
    return common.load_phase4a_outputs()


def read_requests(path: Path) -> Dict[date, Dict[str, Any]]:
    """{window_end: request line} of a batch input file."""
    requests = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                request = json.loads(line)
                requests[window_date(request["custom_id"])] = request
    return requests


def raw_files(spec: Backfill) -> Dict[str, Path]:
    return {"input.jsonl": spec.input_path, "output.jsonl": spec.output_path}


def build_detections(
    spec: Backfill,
    inputs: Inputs,
    outputs: Dict[date, Dict[str, Any]],
    published: Set[date],
    parse_errors: Dict[date, str],
    now: datetime,
) -> List[Dict[str, Any]]:
    """One detections row per batch output line, ordered by window_end.

    Besides the table columns each record carries the working flags ``recovered`` (window missing from the published
    record) and ``lenient``; ``as_rows`` and the parquet writer ignore them.
    """
    records = []
    for end, line in sorted(outputs.items()):
        body = response_body(line)
        choice = (body.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content")
        payload, status, lenient = parse_response(content)
        if lenient:
            logger.info("%s %s: parsed leniently (raw control character in a JSON string)", spec.arm.key, end)
        recovered = end not in published
        metadata: Dict[str, Any] = {RECOVERED_FLAG: True} if recovered else {}
        if lenient:
            metadata["lenient_json"] = True
        if end in parse_errors:
            metadata["published_parse_error"] = parse_errors[end]
        prompt_tokens, completion_tokens, reasoning_tokens = common.usage_fields(body.get("usage"))
        records.append(
            {
                "run_id": spec.run_id,
                "arm": spec.arm.key,
                "series_key": spec.arm.series_key,
                "symbol": spec.arm.symbol,
                "window_end": end,
                "model": spec.model,
                "prompt_version": common.PROMPT_VERSION,
                "custom_id": line["custom_id"],
                "response_id": body.get("id"),
                **{field: (payload or {}).get(field) for field in PAYLOAD_FIELDS},
                "metrics_agree": common.metrics_agree(payload, common.classify(inputs[end][1])) if payload else None,
                "raw_response": content,
                "parse_status": status,
                "finish_reason": choice.get("finish_reason"),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "reasoning_tokens": reasoning_tokens,
                "detection_metadata": common.dumps(metadata, sort_keys=True) if metadata else None,
                "created_at": now,
                "recovered": recovered,
                "lenient": lenient,
            }
        )
    return records


# --------------------------------------------------------------------------- the published records
def read_cache(path: Path) -> PublishedRecord:
    """Cached regime_30day rows of the January run keyed by window_end (SQLite opened read-only)."""
    if not path.exists():
        raise BackfillError(f"research cache not found: {path} (read-only source of the January cross-check)")
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT trading_date, detected, confidence, llm_model, prompt_version, reasoning_chain, "
            "raw_llm_response, token_count, structured_output "
            "FROM llm_detections WHERE pattern_id = ? AND symbol = ?",
            (CACHE_PATTERN_ID, common.ARMS["r1_o4mini"].symbol),
        ).fetchall()
    identity = {(r["llm_model"], r["prompt_version"]) for r in rows}
    if identity != {(common.R1_MODEL, common.PROMPT_VERSION)}:
        raise BackfillError(f"cache rows carry unexpected model / prompt_version: {sorted(identity)}")
    fields = {}
    for row in rows:
        structured = json.loads(row["structured_output"])
        fields[date.fromisoformat(row["trading_date"])] = {
            "regime_detected": bool(row["detected"]),
            "confidence": row["confidence"],
            "reasoning": row["reasoning_chain"],
            "token_count": row["token_count"],
            "raw_response": row["raw_llm_response"],
            **{field: structured[field] for field in STRUCTURED_FIELDS},
        }
    return PublishedRecord("research_cache", path, common.sha256_file(path), fields, {}, {})


def read_result_yaml(path: Path) -> PublishedRecord:
    """Windows and summary of a Phase 3/4 result YAML; a window with an ``error`` entry has only its verdict."""
    with open(path, encoding="utf-8") as fh:
        doc = yaml.load(fh, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    try:
        windows, summary, meta = doc["windows"], doc["summary_statistics"], doc["validation_metadata"]
    except (KeyError, TypeError) as exc:
        raise BackfillError(f"{path.name}: unexpected layout, missing key {exc}") from exc
    fields: Dict[date, Dict[str, Any]] = {}
    errors: Dict[date, str] = {}
    for window in windows:
        try:
            end = window_date(window["window_id"])
            if "error" in window:  # the answer could not be read in November: stored as 'not detected'
                entry = {"regime_detected": bool(window["regime_detected"])}
                errors[end] = str(window["error"])
            else:
                raw = window["raw_response"]
                entry = {
                    **{f: window[f] for f in ("regime_detected", "regime_type", "confidence", "reasoning")},
                    **{f: raw[f] for f in STRUCTURED_FIELDS if f != "regime_type"},
                }
        except (KeyError, TypeError, ValueError) as exc:
            raise BackfillError(f"{path.name}: unreadable window entry {window!r:.120} ({exc!r})") from exc
        if end in fields:
            raise BackfillError(f"{path.name}: window {end} is listed twice")
        fields[end] = entry
    if not fields:
        raise BackfillError(f"{path.name}: no windows")
    stated = {**summary, "batch_id": meta.get("batch_id"), "windows_tested": meta.get("windows_tested")}
    stated["timestamp_naive_us_eastern"] = meta.get("timestamp")
    return PublishedRecord("result_yaml", path, common.sha256_file(path), fields, errors, stated)


def read_record(spec: Backfill) -> Optional[PublishedRecord]:
    """The published record of a run; only the result YAMLs may be absent (then the headline counts still apply)."""
    if spec.record_kind == "research_cache":
        return read_cache(spec.record_path)
    if not spec.record_path.exists():
        logger.warning("%s: %s not found; the field-level cross-check is skipped", spec.arm.key, spec.record_path)
        return None
    return read_result_yaml(spec.record_path)


def comparison_view(rec: Dict[str, Any]) -> Dict[str, Any]:
    """The values of a parsed record in the layout of the published records."""
    view = {field: rec[field] for field in PAYLOAD_FIELDS}
    view["token_count"] = (rec["prompt_tokens"] or 0) + (rec["completion_tokens"] or 0)
    view["raw_response"] = (rec["raw_response"] or "")[:CACHE_RAW_LIMIT]
    return view


def crosscheck(records: Sequence[Dict[str, Any]], record: Optional[PublishedRecord]) -> Dict[str, Any]:
    """Field-by-field agreement between the parsed batch output and the published record."""
    check: Dict[str, Any] = {
        "source": record.source if record else None,
        "published_windows": len(record.fields) if record else None,
        "matched": 0,
        "published_only": [],
        "recovered_windows": [],
        "agreement": {},
        "compared": {},
        "problems": [],
    }
    if record is None:
        return check
    by_end = {r["window_end"]: r for r in records}
    matched = sorted(set(record.fields) & set(by_end))
    agree: Counter = Counter()
    compared: Counter = Counter()
    for end in matched:
        view = comparison_view(by_end[end])
        for field, stored in record.fields[end].items():
            compared[field] += 1
            agree[field] += stored == view[field]
    check.update(
        matched=len(matched),
        published_only=sorted(d.isoformat() for d in set(record.fields) - set(by_end)),
        recovered_windows=sorted(d.isoformat() for d in set(by_end) - set(record.fields)),
        agreement={field: agree[field] for field in CROSSCHECK_FIELDS if field in compared},
        compared={field: compared[field] for field in CROSSCHECK_FIELDS if field in compared},
    )
    if record.source == "research_cache":
        january_ok = {end for end, rec in by_end.items() if january_parse_ok(rec["raw_response"])}
        check["january_parser_reproduces_cache"] = january_ok == set(record.fields)
    else:
        check["result_yaml"] = yaml_summary_check(record, by_end, check["problems"])
        check["parse_error_windows"] = sorted(d.isoformat() for d in record.errors)
    return check


def yaml_summary_check(
    record: PublishedRecord, by_end: Dict[date, Dict[str, Any]], problems: List[str]
) -> Dict[str, Any]:
    """Recompute the statistics a result YAML states about itself; mismatches are appended to ``problems``."""
    published = [by_end[end] for end in sorted(record.fields) if end in by_end]
    n_windows = len(record.fields)
    n_detected = sum(r["regime_detected"] is True for r in published)
    stated = record.summary
    # the pipeline of the time averaged the confidence over all windows, a parse error counting as 0
    confidence = sum(r["confidence"] or 0.0 for r in published if r["window_end"] not in record.errors) / n_windows
    facts = {
        "windows": n_windows,
        "detected": n_detected,
        "stated_windows": stated.get("total_windows"),
        "stated_detected": stated.get("regimes_detected"),
        "stated_rate_pct": stated.get("detection_rate_pct"),
        "stated_confidence_avg": stated.get("confidence_avg"),
        "confidence_avg_reproduced": abs(confidence - stated.get("confidence_avg", float("nan"))) < 1e-9,
    }
    if (stated.get("total_windows"), stated.get("windows_tested")) != (n_windows, n_windows):
        problems.append(f"{record.path.name} lists {n_windows} windows but states {facts['stated_windows']}")
    if stated.get("regimes_detected") != n_detected:
        problems.append(
            f"{n_detected} published windows detected, {record.path.name} states {facts['stated_detected']}"
        )
    if abs(stated.get("detection_rate_pct", float("nan")) - 100.0 * n_detected / n_windows) > 1e-9:
        problems.append(f"the detection rate stated in {record.path.name} is not {n_detected}/{n_windows}")
    if not facts["confidence_avg_reproduced"]:
        logger.warning(
            "%s: confidence_avg %s not reproduced (%.6f)", record.path.name, stated.get("confidence_avg"), confidence
        )
    return facts


def pct(detected: int, n: int) -> float:
    """Detection rate in percent, one decimal (the precision of the published tables)."""
    return round(100.0 * detected / n, 1)


def yearly_rates(records: Sequence[Dict[str, Any]]) -> Dict[int, Tuple[int, int]]:
    """{year: (parsed windows, windows with regime_detected)} over the rows that carry a verdict."""
    parsed: Counter = Counter()
    detected: Counter = Counter()
    for r in records:
        if r["parse_status"] in PARSED:
            parsed[r["window_end"].year] += 1
            detected[r["window_end"].year] += r["regime_detected"] is True
    return {year: (parsed[year], detected[year]) for year in sorted(parsed)}


# --------------------------------------------------------------------------- provenance
def batch_created_at(batch_id: str) -> datetime:
    """Creation time encoded in an OpenAI batch id (the leading 8 hex digits are Unix seconds).

    Checked against the client-side ``created_at`` of the 21 batches in ``batch_jobs/*_metadata.json``, which are naive
    US/Eastern timestamps: after conversion they agree with the decoded id within 1.4 s (read as UTC they would be
    5 h off).  The batch object itself was not queried.
    """
    return datetime.fromtimestamp(int(batch_id.split("_", 1)[1][:8], 16), tz=timezone.utc)


def describe_file(path: Path) -> Dict[str, Any]:
    """Repo-relative original path, size, line count and sha256 of a raw artefact."""
    with open(path, "rb") as fh:
        lines = sum(1 for line in fh if line.strip())
    return {
        "original_path": relative(path),
        "bytes": path.stat().st_size,
        "lines": lines,
        "sha256": common.sha256_file(path),
    }


def request_profile(requests: Dict[date, Dict[str, Any]]) -> Dict[str, Any]:
    """What the requests carried: endpoint, requested model alias and body keys."""
    models: Counter = Counter()
    keys, urls = set(), set()
    for request in requests.values():
        models[request["body"]["model"]] += 1
        keys.update(request["body"])
        urls.add(request["url"])
    return {"urls": sorted(urls), "requested_models": dict(models), "body_keys": sorted(keys)}


def check_prompts(spec: Backfill, requests: Dict[date, Dict[str, Any]], inputs: Inputs) -> Dict[str, Any]:
    """Rebuild every prompt with the shared builder and compare it with the recorded request text."""
    labels = common.SERIES[spec.arm.series_key].labels
    differing, wrong_end = [], []
    for end, (dates, values) in sorted(inputs.items()):
        sent = requests[end]["body"]["messages"][0]["content"] if end in requests else None
        if common.build_prompt(common.obfuscate(values, dates=dates, labels=labels)) != sent:
            differing.append(end.isoformat())
        if dates is not None and dates[-1] != end:
            wrong_end.append(end.isoformat())
    return {
        "labels": labels,
        "windows": len(inputs),
        "identical": len(inputs) - len(differing),
        "differing": differing[:20],
        "last_label_is_window_end": not wrong_end,
    }


def response_profile(outputs: Dict[date, Dict[str, Any]]) -> Dict[str, Any]:
    """Models and creation times reported by the output lines."""
    bodies = [response_body(line) for line in outputs.values()]
    created = [datetime.fromtimestamp(b["created"], tz=timezone.utc) for b in bodies if "created" in b]
    return {
        "models": dict(Counter(b.get("model") for b in bodies)),
        "first_created": min(created),
        "last_created": max(created),
    }


def read_batch_metadata(spec: Backfill) -> Optional[Dict[str, Any]]:
    """The batch_<id>_metadata.json the submitting script wrote (November batches), with its client clock in UTC."""
    path = spec.metadata_path
    if path is None:
        return None
    if not path.exists():
        logger.warning("%s: %s not found; the creation time rests on the batch id alone", spec.arm.key, path)
        return None
    content = json.loads(path.read_text(encoding="utf-8"))
    info: Dict[str, Any] = {
        "path": relative(path),
        "sha256": common.sha256_file(path),
        "content": content,
    }
    try:  # the client wrote naive local (US/Eastern) timestamps
        client = datetime.fromisoformat(content["created_at"]).replace(tzinfo=ZoneInfo(CLIENT_CLOCK))
        info["client_created_at_utc"] = client.astimezone(timezone.utc)
    except (KeyError, ValueError, ZoneInfoNotFoundError) as exc:
        logger.warning("%s: client-side created_at not converted (%s: %s)", path.name, type(exc).__name__, exc)
    return info


def collect_provenance(
    spec: Backfill, requests: Dict[date, Dict[str, Any]], inputs: Inputs, outputs: Dict[date, Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "files": {name: describe_file(path) for name, path in raw_files(spec).items()},
        "request": {**request_profile(requests), "prompt_check": check_prompts(spec, requests, inputs)},
        "response": response_profile(outputs),
        "submitted_at": batch_created_at(spec.batch_id),
        "batch_metadata": read_batch_metadata(spec),
    }


def metadata_problems(spec: Backfill, provenance: Dict[str, Any]) -> List[str]:
    """Contradictions between the batch metadata file and the batch this arm claims to be."""
    info = provenance["batch_metadata"]
    if info is None:
        return []
    content, problems = info["content"], []
    if content.get("batch_id") != spec.batch_id:
        problems.append(
            f"{Path(info['path']).name} is the metadata of {content.get('batch_id')}, not of {spec.batch_id}"
        )
    if Path(str(content.get("input_file", ""))).name != spec.input_path.name:
        problems.append(
            f"the batch metadata names the input file {content.get('input_file')}, not {spec.input_path.name}"
        )
    client = info.get("client_created_at_utc")
    if client is not None and abs((client - provenance["submitted_at"]).total_seconds()) > BATCH_CLOCK_TOLERANCE_S:
        problems.append(
            f"the client-side created_at {client:%Y-%m-%dT%H:%M:%SZ} is not the time decoded from the batch id"
        )
    return problems


def verification_problems(
    spec: Backfill,
    check: Dict[str, Any],
    published: Dict[int, Tuple[int, int]],
    provenance: Dict[str, Any],
    n_windows: int,
) -> List[str]:
    """Reasons not to write anything (empty when the batch output reproduces the published run)."""
    problems = list(check["problems"])
    for name, file in provenance["files"].items():
        if file["lines"] != n_windows:
            problems.append(f"{name} has {file['lines']} lines for {n_windows} distinct windows")
    models = provenance["response"]["models"]
    if set(models) != {common.R1_MODEL}:
        problems.append(f"output lines report the models {models}")
    if check["published_only"]:
        problems.append(f"{len(check['published_only'])} published windows have no batch output line")
    agreement, compared = check["agreement"], check["compared"]
    if check["source"] and compared.get("regime_detected", 0) != check["matched"]:
        problems.append(
            f"the verdict of {check['matched'] - compared.get('regime_detected', 0)} matched windows is not recorded"
        )
    for field in ("regime_detected", "regime_type"):
        if agreement.get(field, 0) != compared.get(field, 0):
            problems.append(
                f"{field} differs from the published record on {compared[field] - agreement[field]} windows"
            )
    rates = {year: pct(k, n) for year, (n, k) in published.items()}
    if rates != spec.published_pct:
        problems.append(f"yearly rates {rates} differ from the published {spec.published_pct}")
    if spec.headline is not None:
        counted = (sum(k for _, k in published.values()), sum(n for n, _ in published.values()))
        if counted != spec.headline:
            problems.append(
                f"{counted[0]} of {counted[1]} published windows detected, the papers state {spec.headline}"
            )
    if provenance["submitted_at"] > provenance["response"]["first_created"]:
        problems.append(f"the batch id decodes to {provenance['submitted_at']}, after the first response")
    return problems + metadata_problems(spec, provenance)


# --------------------------------------------------------------------------- the runs row
def relative(path: Path) -> str:
    """Repo-relative POSIX path (the path itself when it lies outside the repository)."""
    try:
        return path.relative_to(common.REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def build_run_row(
    spec: Backfill,
    records: Sequence[Dict[str, Any]],
    provenance: Dict[str, Any],
    record: Optional[PublishedRecord],
    check: Dict[str, Any],
    published: Dict[int, Tuple[int, int]],
    backup_dir: Path,
    now: datetime,
) -> Dict[str, Any]:
    """The single runs row of the backfill.

    Request fields the original body did not carry (reasoning_effort, max_completion_tokens) and values that were
    never recorded (model_created_at, output / error file ids, completed_at, and for the January run the input file
    id) stay NULL.  ``created_at`` is the insert time of the row.
    """
    files, response, request = provenance["files"], provenance["response"], provenance["request"]
    statuses = Counter(r["parse_status"] for r in records)
    n_parsed = sum(statuses[status] for status in PARSED)
    tokens = {f: sum(r[f] or 0 for r in records) for f in ("prompt_tokens", "completion_tokens", "reasoning_tokens")}
    client = provenance["batch_metadata"]
    batch: Dict[str, Any] = {
        "created_at": provenance["submitted_at"],
        "created_at_source": "decoded from the batch id; the batch object was not queried",
        "first_response_created_at": response["first_created"],
        "last_response_created_at": response["last_created"],
        "completed_at_note": "not recorded; the batch finished after last_response_created_at",
    }
    if spec.expired_file_ids:
        batch["expired_file_ids"] = list(spec.expired_file_ids)
    if client is not None:
        batch["client_metadata"] = client
        batch["input_file_id_source"] = "'file_id' of the batch metadata file written when the batch was created"
    metadata: Dict[str, Any] = {
        "backfill": {
            "script": relative(Path(__file__).resolve()),
            "classifier": common.classifier_version(),
            "git_sha_note": spec.git_sha_note,
        },
        "batch": batch,
        "request": {
            **request,
            "reasoning_effort": (
                "sent" if "reasoning_effort" in request["body_keys"] else "not sent; the o4-mini API default is medium"
            ),
            "response_format": (
                "sent"
                if "response_format" in request["body_keys"]
                else "not sent; free text, most answers arrive wrapped in markdown fences"
            ),
        },
        "response": {"models": response["models"]},
        "parse": {
            "status_counts": dict(statuses),
            RECOVERED_FLAG: sum(r["recovered"] for r in records),
            "lenient_json": [r["window_end"].isoformat() for r in records if r["lenient"]],
            "published_parse_error": check.get("parse_error_windows", []),
        },
        "published_set": {
            "sql_filter": f"detection_metadata ->> '{RECOVERED_FLAG}' IS NULL",
            "windows": sum(n for n, _ in published.values()),
            "detected": sum(k for _, k in published.values()),
            "yearly": {str(y): {"n": n, "detected": k, "pct": pct(k, n)} for y, (n, k) in published.items()},
        },
    }
    if record is None:
        metadata["result_yaml"] = {"path": relative(spec.record_path), "present": False}
    elif record.source == "research_cache":
        metadata["research_cache"] = {
            "path": relative(record.path),
            "sha256": record.sha256,
            "cache_rows": check["published_windows"],
            "matched": check["matched"],
            "agreement": check["agreement"],
            "january_parser_reproduces_cache": check["january_parser_reproduces_cache"],
            "recovered_windows": check["recovered_windows"],
        }
    else:
        metadata["result_yaml"] = {
            "path": relative(record.path),
            "sha256": record.sha256,
            "first_commit": RESULT_YAML_COMMIT,
            "windows": check["published_windows"],
            "matched": check["matched"],
            "agreement": check["agreement"],
            "compared": check["compared"],
            "parse_error_windows": check["parse_error_windows"],
            "summary": check["result_yaml"],
            "timestamp_naive_us_eastern": record.summary["timestamp_naive_us_eastern"],
        }
    return {
        "run_id": spec.run_id,
        "arm": spec.arm.key,
        "series_key": spec.arm.series_key,
        "symbol": spec.arm.symbol,
        "model": spec.model,
        "prompt_version": common.PROMPT_VERSION,
        "response_format": "none",
        "mode": "batch",
        "openai_batch_id": spec.batch_id,
        "input_file_id": ((client or {}).get("content") or {}).get("file_id"),
        "input_sha256": files["input.jsonl"]["sha256"],
        "output_sha256": files["output.jsonl"]["sha256"],
        "backup_dir": str(backup_dir),
        "window_end_min": records[0]["window_end"],
        "window_end_max": records[-1]["window_end"],
        "n_requests": files["input.jsonl"]["lines"],
        "n_responses": len(records),
        "n_parsed": n_parsed,
        "n_failed": len(records) - n_parsed,
        **tokens,
        "est_cost_usd": common.estimate_cost_usd(
            spec.model, "batch", tokens["prompt_tokens"], tokens["completion_tokens"]
        ),
        "status": "ingested",
        "submitted_at": provenance["submitted_at"],
        "ingested_at": now,
        "git_sha": spec.git_sha,
        "run_metadata": common.dumps(metadata, sort_keys=True),
        "created_at": now,
    }


def prepare(spec: Backfill, now: datetime) -> Prepared:
    """Parse, cross-check and verify one backfill; nothing is written."""
    inputs, outputs = load_inputs(spec), load_outputs(spec)
    if set(inputs) != set(outputs):
        raise BackfillError(f"{spec.arm.key}: the input and output files do not cover the same windows")
    requests = read_requests(spec.input_path)
    record = read_record(spec)
    published_windows = set(record.fields) if record else set(outputs)
    records = build_detections(spec, inputs, outputs, published_windows, record.errors if record else {}, now)
    check = crosscheck(records, record)
    published = yearly_rates([r for r in records if not r["recovered"]])
    provenance = collect_provenance(spec, requests, inputs, outputs)
    problems = verification_problems(spec, check, published, provenance, len(records))
    if problems:
        raise BackfillError(
            f"{spec.arm.key}: the batch output does not reproduce the published run: " + "; ".join(problems)
        )
    differing = provenance["request"]["prompt_check"]["differing"]
    if differing:
        logger.warning("%s: the rebuilt prompt differs from the recorded request for %s", spec.arm.key, differing)
    backup_dir = common.BACKUP_ROOT / spec.run_id
    run_row = build_run_row(spec, records, provenance, record, check, published, backup_dir, now)
    check["prompt_check"] = provenance["request"]["prompt_check"]
    return Prepared(spec, records, run_row, published, yearly_rates(records), check, provenance["files"], backup_dir)


# --------------------------------------------------------------------------- files
def write_raw_backup(item: Prepared) -> None:
    """Copy the batch JSONL files next to a manifest; an existing copy must be byte-identical."""
    spec, files, run_row = item.spec, item.files, item.run_row
    item.backup_dir.mkdir(parents=True, exist_ok=True)
    for name, source in raw_files(spec).items():
        dest = item.backup_dir / name
        if dest.exists():
            if common.sha256_file(dest) != files[name]["sha256"]:
                raise BackfillError(f"{dest} exists and differs from {source}; refusing to overwrite it")
            logger.info("raw backup already in place: %s", dest)
            continue
        part = dest.with_name(dest.name + ".part")
        shutil.copy2(source, part)
        if common.sha256_file(part) != files[name]["sha256"]:
            part.unlink()
            raise BackfillError(f"the copy of {source} does not match its sha256")
        os.replace(part, dest)
        logger.info("copied %s -> %s (%d bytes)", source.name, dest, files[name]["bytes"])
    manifest = {
        "run_id": run_row["run_id"],
        "arm": run_row["arm"],
        "openai_batch_id": run_row["openai_batch_id"],
        "n_windows": run_row["n_responses"],
        "window_end_min": run_row["window_end_min"],
        "window_end_max": run_row["window_end_max"],
        "files": files,
    }
    if run_row["input_file_id"]:
        manifest["input_file_id"] = run_row["input_file_id"]
    target = item.backup_dir / "manifest.json"
    part = target.with_name(target.name + ".part")
    part.write_text(common.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(part, target)  # a reader never sees half a file


def keep_created_at(run_row: Dict[str, Any], path: Path) -> None:
    """A re-run keeps the insert time of the runs row it replaces (older copies without the column are stamped now)."""
    if not path.exists():
        return
    try:
        old = pq.read_table(path, columns=["run_id", "created_at"]).to_pylist()
    except (OSError, KeyError, ValueError, pa.ArrowException):
        return
    for row in old:
        if row["run_id"] == run_row["run_id"] and row["created_at"] is not None:
            run_row["created_at"] = row["created_at"]


def write_parquet(item: Prepared) -> None:
    """Write the detections and runs parquet copies and read them back to check the row counts."""
    for kind, columns, rows in (("detections", DETECTION_COLUMNS, item.records), ("runs", RUN_COLUMNS, [item.run_row])):
        path = common.parquet_path(kind, item.spec.arm.key)
        if kind == "runs":
            keep_created_at(item.run_row, path)
        part = path.with_name(path.name + ".part")  # not matched by the *.parquet globs of 04 and 05
        pq.write_table(pa.Table.from_pylist(list(rows), schema=pa.schema(columns)), part)
        os.replace(part, path)
        if pq.read_table(path).num_rows != len(rows):
            raise BackfillError(f"{path} does not hold the {len(rows)} rows that were written")
        logger.info("wrote %s (%d rows)", path, len(rows))


# --------------------------------------------------------------------------- Postgres
def existing_objects(conn) -> List[str]:
    """The gex_llm_regime tables / view that exist (SELECT only)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT name FROM unnest(%s::text[]) AS name WHERE to_regclass(name) IS NOT NULL ORDER BY 1",
            (list(SCHEMA_OBJECTS),),
        )
        return [row[0] for row in cur.fetchall()]


def apply_schema_in_transaction(conn) -> None:
    """Run the schema SQL inside the caller's transaction (its BEGIN / COMMIT lines stripped)."""
    sql = re.sub(r"^[ \t]*(?:BEGIN|COMMIT);[ \t]*$", "", common.SCHEMA_SQL.read_text(), flags=re.M | re.I)
    if re.search(r"^[ \t]*(?:COMMIT|END|ROLLBACK)[ \t]*;", sql, flags=re.M | re.I):
        raise BackfillError("the schema SQL ends a transaction somewhere else; refusing to run it")
    with conn.cursor() as cur:
        cur.execute(sql)


def as_rows(rows: Sequence[Dict[str, Any]], columns: Dict[str, pa.DataType]) -> List[Tuple[Any, ...]]:
    return [tuple(row.get(name) for name in columns) for row in rows]


def read_back(conn, spec: Backfill) -> Tuple[Tuple[int, int, int], Dict[int, Tuple[int, int]]]:
    """Row counts and published-set yearly rates of the arm as SQL sees them (inside the open transaction)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*), COUNT(*) FILTER (WHERE parse_status IN ('ok', 'fallback')), "
            f"COUNT(*) FILTER (WHERE detection_metadata ->> '{RECOVERED_FLAG}' = 'true') "
            f"FROM {common.T_DETECTIONS} WHERE arm = %s AND run_id = %s",
            (spec.arm.key, spec.run_id),
        )
        counts = tuple(cur.fetchone())
        cur.execute(
            "SELECT EXTRACT(YEAR FROM window_end)::int, COUNT(*), COUNT(*) FILTER (WHERE regime_detected) "
            f"FROM {common.T_DETECTIONS} WHERE arm = %s AND parse_status IN ('ok', 'fallback') "
            f"AND detection_metadata ->> '{RECOVERED_FLAG}' IS NULL GROUP BY 1 ORDER BY 1",
            (spec.arm.key,),
        )
        rates = {year: (n, k) for year, n, k in cur.fetchall()}
    return counts, rates


def write_postgres(items: Sequence[Prepared], rollback: bool) -> None:
    """Upsert the runs rows and the detections in one transaction, then COMMIT (or ROLLBACK when ``rollback``).

    With ``rollback`` the schema SQL runs inside the same transaction first, so the test works before the tables
    exist and leaves nothing behind (checked afterwards).  Otherwise the tables must already exist.
    """
    conn = common.connect(autocommit=False)
    try:  # closing the connection discards an open transaction, whatever raised
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '600s'")
        before = existing_objects(conn)
        if rollback:
            apply_schema_in_transaction(conn)
        elif not {common.T_RUNS, common.T_DETECTIONS} <= set(before):
            raise SystemExit(
                f"{common.T_RUNS} / {common.T_DETECTIONS} do not exist and this script never creates them. Apply "
                f"{common.SCHEMA_SQL.relative_to(common.REPO_ROOT)} once the documentation PR is approved, or use "
                "--rollback to test the load."
            )
        update_runs = [c for c in RUN_COLUMNS if c not in ("run_id", "created_at")]  # created_at: insert time stays
        for item in items:
            spec, records = item.spec, item.records
            common.upsert_rows(
                conn, common.T_RUNS, list(RUN_COLUMNS), as_rows([item.run_row], RUN_COLUMNS), ["run_id"], update_runs
            )
            common.upsert_rows(
                conn, common.T_DETECTIONS, list(DETECTION_COLUMNS), as_rows(records, DETECTION_COLUMNS), DETECTION_KEY
            )
            counts, rates = read_back(conn, spec)
            expected = (len(records), item.run_row["n_parsed"], sum(r["recovered"] for r in records))
            if counts != expected or rates != item.published:
                raise BackfillError(
                    f"{spec.arm.key}: read-back differs from the rows written: {counts} vs {expected}, "
                    f"{rates} vs {item.published}"
                )
            logger.info(
                "%s read-back in the transaction: %d detections, %d parsed, %d recovered; published-set rates %s",
                spec.arm.key,
                *counts,
                {year: pct(k, n) for year, (n, k) in rates.items()},
            )
        if rollback:
            conn.rollback()
            if existing_objects(conn) != before:
                raise BackfillError("objects remain after ROLLBACK")
            logger.info("ROLLBACK done; gex_llm_regime objects before and after: %s", before or "none")
        else:
            conn.commit()
            logger.info(
                "COMMIT done: %d run rows and %d detections upserted", len(items), sum(len(i.records) for i in items)
            )
    finally:
        conn.close()


# --------------------------------------------------------------------------- report
def format_counts(records: Sequence[Dict[str, Any]]) -> str:
    counts = Counter(r["parse_status"] for r in records)
    return " | ".join(f"{status} {n}" for status, n in sorted(counts.items())) or "none"


def format_rates(published: Dict[int, Tuple[int, int]], everything: Dict[int, Tuple[int, int]]) -> List[str]:
    lines = ["  year  published windows            all parsed windows"]
    for year, (n, k) in published.items():
        all_n, all_k = everything.get(year, (0, 0))
        lines.append(
            f"  {year}  {k:>4}/{n:<4} = {pct(k, n):5.1f}%          {all_k:>4}/{all_n:<4} = {pct(all_k, all_n):5.1f}%"
        )
    return lines


def report(item: Prepared) -> None:
    """Log the parse statistics, the cross-check against the published record and the yearly detection rates."""
    spec, records, check, run_row = item.spec, item.records, item.check, item.run_row
    cached = [r for r in records if not r["recovered"]]
    recovered = [r for r in records if r["recovered"]]
    compared = check["compared"]
    agreement = ", ".join(f"{field} {check['agreement'][field]}/{compared[field]}" for field in compared)
    regime_types = Counter(r["regime_type"] for r in records if r["parse_status"] in PARSED)
    agree_counts = dict(Counter(r["metrics_agree"] for r in records))
    prompts = check["prompt_check"]
    lines = [
        f"{spec.arm.key} ({spec.run_id}): {run_row['n_requests']} input lines, {run_row['n_responses']} output lines, "
        f"windows {run_row['window_end_min']} .. {run_row['window_end_max']}",
        f"parse_status  all: {format_counts(records)}  |  published: {format_counts(cached)}  |  "
        f"recovered: {format_counts(recovered)}",
    ]
    if check["source"]:
        lines += [
            f"published record {spec.record_path.name} ({check['source']}): {check['published_windows']} windows, "
            f"{check['matched']} matched to an output line, {len(check['published_only'])} record-only, "
            f"{len(recovered)} output-only",
            f"  agreement on the matched windows: {agreement}",
        ]
    else:
        lines.append(f"published record {spec.record_path.name}: not found, no field-level cross-check")
    if "january_parser_reproduces_cache" in check:
        lines.append(
            "  the January parser (greedy regex + strict json.loads) reproduces the cache membership: "
            f"{check['january_parser_reproduces_cache']}"
        )
    if "result_yaml" in check:
        stated = check["result_yaml"]
        lines += [
            f"  the YAML states {stated['stated_detected']} of {stated['stated_windows']} windows detected "
            f"({stated['stated_rate_pct']:.1f}%); recomputed from the batch output: {stated['detected']} of "
            f"{stated['windows']}; confidence_avg {stated['stated_confidence_avg']:.4f} reproduced: "
            f"{stated['confidence_avg_reproduced']}",
            f"  windows the YAML lists as parse errors (read here, verdict not detected): "
            f"{check['parse_error_windows'] or 'none'}",
        ]
    if recovered:
        lines += [
            f"recovered beyond the record ({len(recovered)} windows, detection_metadata {RECOVERED_FLAG}=true):",
            textwrap.fill(
                ", ".join(check["recovered_windows"]), width=118, initial_indent="  ", subsequent_indent="  "
            ),
        ]
    lines += [
        f"prompts rebuilt with common.build_prompt ({prompts['labels']} labels): {prompts['identical']} of "
        f"{prompts['windows']} identical to the recorded requests",
        "yearly detection rate:",
        *format_rates(item.published, item.everything),
        f"regime_type (parsed): {dict(regime_types)}",
        f"metrics_agree against common.classify of the input values: {agree_counts}",
        f"tokens: prompt {run_row['prompt_tokens']:,}, completion {run_row['completion_tokens']:,} "
        f"(reasoning {run_row['reasoning_tokens']:,}); estimated cost at batch prices ${run_row['est_cost_usd']:.2f} "
        f"(history, not spend); submitted_at {run_row['submitted_at']:%Y-%m-%dT%H:%M:%SZ}",
    ]
    logger.info("\n".join(lines))


def summary_table(items: Sequence[Prepared]) -> str:
    """One line per arm: windows, parsed, published windows, detected, rate and the reproduction verdict."""
    lines = [f"{'arm':<14} {'windows':>7} {'parsed':>6} {'published':>9} {'detected':>8} {'rate':>6}  published rates"]
    for item in items:
        n = sum(n for n, _ in item.published.values())
        k = sum(k for _, k in item.published.values())
        rates = " / ".join(f"{pct(k_, n_):.1f}" for n_, k_ in item.published.values())
        reproduced = (
            "reproduced"
            if {y: pct(k_, n_) for y, (n_, k_) in item.published.items()} == item.spec.published_pct
            else "NOT reproduced"
        )
        lines.append(
            f"{item.spec.arm.key:<14} {len(item.records):>7} {item.run_row['n_parsed']:>6} {n:>9} {k:>8} "
            f"{pct(k, n):>5.1f}%  {rates} ({reproduced})"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- CLI
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--parquet-only",
        action="store_true",
        help="write the raw backup, manifest and parquet copies; do not connect to Postgres (the default)",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="parse, cross-check and report; write nothing and do not connect to Postgres",
    )
    mode.add_argument(
        "--rollback",
        action="store_true",
        help="test the Postgres load: schema SQL and upserts in one transaction that is rolled back; no files",
    )
    mode.add_argument(
        "--db",
        action="store_true",
        help="write the files, then upsert into Postgres and COMMIT (the tables must already exist)",
    )
    parser.add_argument(
        "--arm",
        action="append",
        choices=list(SPECS),
        metavar="ARM",
        help=f"backfill only this arm (repeatable; default: all of {', '.join(SPECS)})",
    )
    parser.add_argument(
        "--ignore-busy-window",
        action="store_true",
        help="allow --rollback / --db between 21:50 and 22:45 UTC (the monitors rebuild the daily tables)",
    )
    parser.add_argument(
        "--backup-root",
        type=Path,
        help="alternative root for the raw backups and parquet copies (default: data/backups/gex_llm)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    common.setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    if args.backup_root is not None:  # common reads these module globals at call time
        common.BACKUP_ROOT, common.PARQUET_ROOT = args.backup_root, args.backup_root / "tables"
    writes_db = args.db or args.rollback
    if writes_db:  # before anything is read or written
        try:
            common.assert_not_quiet(args.ignore_busy_window)
        except RuntimeError as exc:
            raise SystemExit(f"{exc} (the monitors rebuild the daily tables then: no DDL, no upserts)") from exc
    write_files = not (args.dry_run or args.rollback)
    now = common.utcnow()

    try:
        # every arm is parsed, cross-checked and verified before the first file is written
        items = [prepare(SPECS[key], now) for key in dict.fromkeys(args.arm or SPECS)]
        for item in items:
            report(item)
        if write_files:
            for item in items:
                write_raw_backup(item)
                write_parquet(item)
        if writes_db:
            write_postgres(items, rollback=args.rollback)
    except BackfillError as exc:
        logger.error("%s", exc)
        return 1
    if not (write_files or args.rollback):
        logger.info("dry run, nothing written (the default mode writes the raw backups and parquet copies)")
    print(summary_table(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
