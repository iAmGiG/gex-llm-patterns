#!/usr/bin/env python3
"""Shared contract for the Electronics-extension pipeline (gex-llm-patterns issue #261).

Everything the numbered scripts in this folder agree on lives here: database
connection, the registry of daily GEX series and LLM arms, the model
configuration, the obfuscation + prompt + classifier bridge to ``src/``, the
strict JSON schema for the model answer, cost accounting and the raw-backup
layout.  Keep this module free of side effects on import.

Run from the repository root with the AutoGex conda env::

    source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
    PYTHONPATH=$(pwd) python scripts/validation/electronics/<script>.py --help
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- paths
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCRIPT_DIR = Path(__file__).resolve().parent
SQL_DIR = SCRIPT_DIR / "sql"
SCHEMA_SQL = SQL_DIR / "gex_llm_regime_schema.sql"
PAPER_DIR = REPO_ROOT / "docs" / "papers" / "electronics"
RESULTS_DIR = PAPER_DIR / "results"
FIGURE_OUTPUT_DIR = PAPER_DIR / "figures" / "output"
BACKUP_ROOT = REPO_ROOT / "data" / "backups" / "gex_llm"
CONFIG_PATH = REPO_ROOT / "config" / "config.json"
RESEARCH_CACHE_DB = REPO_ROOT / ".cache" / "research_cache.db"

# Exact Phase 4A artefacts from the published run (2026-01-04, o4-mini).
PHASE4A_DIR = REPO_ROOT / "reports" / "validation" / "paper2_regime_windows" / "batch_jobs"
PHASE4A_INPUT_JSONL = PHASE4A_DIR / "phase4a_postgresql_20260104_184832.jsonl"
PHASE4A_OUTPUT_JSONL = PHASE4A_DIR / "results_phase4a_postgresql_20260104_193513.jsonl"
PHASE4A_BATCH_ID = "batch_695ab77d2fe8819084e397a55f10e6bc"

logger = logging.getLogger("electronics")

# --------------------------------------------------------------------------- database
DB_PARAMS: Dict[str, Any] = {"host": "127.0.0.1", "dbname": "gex_options", "user": "cregan1"}

# Archive snapshots of the pre-rebuild daily tables. READ ONLY, never written.
ARCHIVE_DAILY_TABLE = "backups.options_daily_summary_pre_rebuild_20261004"
ARCHIVE_INTRADAY_TABLE = "backups.intraday_gex_summary_pre_rebuild_20261004"

T_SERIES = "backups.gex_llm_regime_series"
T_WINDOWS = "backups.gex_llm_regime_windows"
T_RUNS = "backups.gex_llm_regime_runs"
T_DETECTIONS = "backups.gex_llm_regime_detections"


def connect(autocommit: bool = False):
    """Open a psycopg2 connection to gex_options (local socket-less TCP, trust auth)."""
    import psycopg2

    conn = psycopg2.connect(**DB_PARAMS)
    conn.autocommit = autocommit
    return conn


def ensure_schema(conn) -> None:
    """Apply the idempotent schema file (CREATE IF NOT EXISTS only)."""
    sql = SCHEMA_SQL.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def upsert_rows(conn, table: str, columns: Sequence[str], rows: Iterable[Sequence[Any]],
                conflict_cols: Sequence[str], update_cols: Optional[Sequence[str]] = None,
                page_size: int = 1000) -> int:
    """INSERT ... ON CONFLICT DO UPDATE for a batch of rows. Returns rows sent."""
    from psycopg2.extras import execute_values

    rows = list(rows)
    if not rows:
        return 0
    update_cols = list(update_cols) if update_cols is not None else [c for c in columns if c not in conflict_cols]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols) or None
    conflict = ", ".join(conflict_cols)
    action = f"DO UPDATE SET {set_clause}" if set_clause else "DO NOTHING"
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES %s ON CONFLICT ({conflict}) {action}"
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, page_size=page_size)
    return len(rows)


# --------------------------------------------------------------------------- study design
WINDOW_DAYS = 30
# Equity options moved from Alpha Vantage to Cboe delayed quotes on 2026-10-12.
WINDOW_END_CAP = date(2026, 10, 9)
SYMBOL_START: Dict[str, date] = {"SPY": date(2008, 1, 1), "IWM": date(2008, 1, 1), "QQQ": date(2011, 1, 1)}
INTRADAY_START = date(2026, 7, 27)  # equity intraday rows before 07-25 carried the prior day's chain (#64)
# The market_close slot (20:00:59 UTC) is the EOD row itself; final_rush (19:55:59 UTC) is the last
# independent late-session observation.  Filter on snapshot_type, not on a UTC clock (DST shifts it).
INTRADAY_SNAPSHOT_TYPE = "final_rush"
INTRADAY_EXCLUDE_DAYS = (date(2026, 7, 29), date(2026, 8, 3), date(2026, 9, 14))  # irregular days (data audit)
BATCH_MAX_REQUESTS = 1500  # chunk size shown to be accepted by the Batch endpoint


@dataclass(frozen=True)
class Series:
    key: str
    description: str
    source_table: str
    symbols: Tuple[str, ...]
    calendar: str = "master"  # 'master' = gex.options_daily_summary dates; 'self' = the series' own dates
    start: Optional[date] = None  # overrides SYMBOL_START when set
    end: date = WINDOW_END_CAP
    labels: str = "obfuscated"  # 'obfuscated' = Day T-29..T+0 (Phase 4A); 'dated' = ISO dates as in the Nov-2025 Phase 3/4 runs
    scale: Optional[str] = None  # 'oi_notional' = multiply by the SPY/symbol open-interest-notional ratio (QQQ/IWM only)


# November 2025 Phase 3 (2024 full year) and Phase 4 (2020 baseline) runs: the inputs behind the
# published 81.2% vs 12.1% contrast.  Their prompts carried calendar dates (not obfuscated); the
# 2024 series is the gross magnitude (call+put, ex-0DTE) with a negative sign imposed and the 2020
# series is magnitude-only.  Kept verbatim so the date effect can be measured.
PHASE3_INPUT_JSONL = PHASE4A_DIR / "phase3_full_2024_baseline_v2.jsonl"
PHASE3_OUTPUT_JSONL = PHASE4A_DIR / "results_batch_691ea7f7b79481909f4667eaff640f26.jsonl"
PHASE3_BATCH_ID = "batch_691ea7f7b79481909f4667eaff640f26"
PHASE4_INPUT_JSONL = PHASE4A_DIR / "batch_regime_20251120_104630.jsonl"
PHASE4_OUTPUT_JSONL = PHASE4A_DIR / "results_batch_691f37d94ef0819099136e88a69bef82.jsonl"
PHASE4_BATCH_ID = "batch_691f37d94ef0819099136e88a69bef82"
PHASE34_FILES = {  # series_key -> (input, output, batch id)
    "p3_2024": (PHASE3_INPUT_JSONL, PHASE3_OUTPUT_JSONL, PHASE3_BATCH_ID),
    "p4_2020": (PHASE4_INPUT_JSONL, PHASE4_OUTPUT_JSONL, PHASE4_BATCH_ID),
}


SERIES: Dict[str, Series] = {
    "jan2026_phase4a": Series(
        key="jan2026_phase4a",
        description="Exact Phase 4A inputs (SPY, o4-mini batch of 2026-01-04), recovered from the surviving batch file",
        source_table=str(PHASE4A_INPUT_JSONL.relative_to(REPO_ROOT)),
        symbols=("SPY",), calendar="self", start=date(2020, 1, 2), end=date(2025, 12, 31),
    ),
    "old_bs": Series(
        key="old_bs",
        description="Pre-rebuild daily table (Black-Scholes gamma on integer DTE, same-day expiries zeroed); archive snapshot of 2026-10-04",
        source_table=ARCHIVE_DAILY_TABLE, symbols=("SPY",), end=date(2026, 10, 3),
    ),
    "new_full": Series(
        key="new_full",
        description="gex.options_daily_summary after the 2026-10-08 rebuild: stored per-contract gamma, 0DTE included",
        source_table="gex.options_daily_summary", symbols=("SPY", "QQQ", "IWM"),
    ),
    "new_ex0dte": Series(
        key="new_ex0dte",
        description="Recomputed from raw gex.options_chains_partitioned with expiration > trading_date (0DTE removed)",
        source_table="gex.options_chains_partitioned", symbols=("SPY", "QQQ", "IWM"),
    ),
    "intraday_late": Series(
        key="intraday_late",
        description="gex.intraday_gex_summary snapshot_type=final_rush (19:55:59 UTC), the last independent late-session observation",
        source_table="gex.intraday_gex_summary", symbols=("SPY",), start=INTRADAY_START,
    ),
    "call_only": Series(
        key="call_only",
        description="Diagnostic: call leg only (0DTE included) from raw chains; reproduces the put-less published inputs from clean data",
        source_table="gex.options_chains_partitioned", symbols=("SPY",), start=date(2020, 1, 1),
    ),
    "new_full_scaled": Series(
        key="new_full_scaled",
        description="new_full multiplied by a fixed per-symbol factor = median(2020-01..2026-10-09) of SPY / symbol open-interest notional (total_weighted_oi * 100 * underlying_price); makes the $5B criterion comparable across ETFs without touching the prompt",
        source_table="gex.options_daily_summary", symbols=("QQQ", "IWM"), start=date(2020, 1, 1), scale="oi_notional",
    ),
    "p3_2024": Series(
        key="p3_2024",
        description="Nov-2025 Phase 3 input series (SPY 2024, 252 values): gross call+put magnitude ex-0DTE with a negative sign imposed; obfuscated labels",
        source_table=str(PHASE3_INPUT_JSONL.relative_to(REPO_ROOT)), symbols=("SPY",), calendar="self",
        start=date(2024, 1, 2), end=date(2024, 12, 31),
    ),
    "p3_2024_dated": Series(
        key="p3_2024_dated",
        description="Same values as p3_2024 with the calendar-date labels actually sent in Nov 2025",
        source_table=str(PHASE3_INPUT_JSONL.relative_to(REPO_ROOT)), symbols=("SPY",), calendar="self",
        start=date(2024, 1, 2), end=date(2024, 12, 31), labels="dated",
    ),
    "p4_2020": Series(
        key="p4_2020",
        description="Nov-2025 Phase 4 input series (SPY 2020, 252 values): magnitude-only (always positive); obfuscated labels",
        source_table=str(PHASE4_INPUT_JSONL.relative_to(REPO_ROOT)), symbols=("SPY",), calendar="self",
        start=date(2020, 1, 2), end=date(2020, 12, 31),
    ),
    "p4_2020_dated": Series(
        key="p4_2020_dated",
        description="Same values as p4_2020 with the calendar-date labels actually sent in Nov 2025",
        source_table=str(PHASE4_INPUT_JSONL.relative_to(REPO_ROOT)), symbols=("SPY",), calendar="self",
        start=date(2020, 1, 2), end=date(2020, 12, 31), labels="dated",
    ),
}


@dataclass(frozen=True)
class Arm:
    key: str
    series_key: str
    symbol: str
    priority: int
    description: str
    start: Optional[date] = None
    end: Optional[date] = None
    llm: bool = True  # False = classifier/backfill only, never submitted to a model
    window_series_key: Optional[str] = None  # windows are read from this series when it differs (composites)


def arm_window_series(arm: "Arm") -> str:
    """Series key under which the arm's windows are stored (composites differ from the detection series)."""
    return arm.window_series_key or arm.series_key


ARMS: Dict[str, Arm] = {
    "r1_o4mini": Arm("r1_o4mini", "jan2026_phase4a", "SPY", 0,
                     "Published Phase 4A results (o4-mini, Jan 2026) backfilled from the original batch output", llm=False),
    "r1_p3_o4mini": Arm("r1_p3_o4mini", "p3_2024_dated", "SPY", 0,
                        "Published Phase 3 results (o4-mini, Nov 2025, dated prompts) backfilled from the batch output", llm=False),
    "r1_p4_o4mini": Arm("r1_p4_o4mini", "p4_2020_dated", "SPY", 0,
                        "Published Phase 4 results (o4-mini, Nov 2025, dated prompts) backfilled from the batch output", llm=False),
    "bridge_jan": Arm("bridge_jan", "jan2026_phase4a", "SPY", 1,
                      "gpt-6-luna on the exact published inputs: model-agreement bridge to o4-mini"),
    "full_spy": Arm("full_spy", "new_full", "SPY", 1, "Rebuilt 0DTE-inclusive series, SPY 2008-2026"),
    "ex0dte_spy": Arm("ex0dte_spy", "new_ex0dte", "SPY", 1, "0DTE-excluded ablation, SPY 2008-2026"),
    "p34_obf_2024": Arm("p34_obf_2024", "p3_2024", "SPY", 1, "Phase 3 inputs with Day-T labels (obfuscated rerun)"),
    "p34_dated_2024": Arm("p34_dated_2024", "p3_2024_dated", "SPY", 1, "Phase 3 inputs with the dates actually sent"),
    "p34_obf_2020": Arm("p34_obf_2020", "p4_2020", "SPY", 1, "Phase 4 inputs with Day-T labels (obfuscated rerun)"),
    "p34_dated_2020": Arm("p34_dated_2020", "p4_2020_dated", "SPY", 1, "Phase 4 inputs with the dates actually sent"),
    "full_qqq": Arm("full_qqq", "new_full", "QQQ", 2, "Cross-asset, QQQ 2011-2026 (unscaled; floor effect expected)"),
    "full_iwm": Arm("full_iwm", "new_full", "IWM", 2, "Cross-asset, IWM 2008-2026 (unscaled; floor effect expected)"),
    "full_qqq_scaled": Arm("full_qqq_scaled", "new_full_scaled", "QQQ", 2, "Cross-asset, QQQ 2020-2026, OI-notional scaled"),
    "full_iwm_scaled": Arm("full_iwm_scaled", "new_full_scaled", "IWM", 2, "Cross-asset, IWM 2020-2026, OI-notional scaled"),
    "ex0dte_qqq": Arm("ex0dte_qqq", "new_ex0dte", "QQQ", 3, "0DTE-excluded, QQQ 2020-2026", start=date(2020, 1, 1)),
    "ex0dte_iwm": Arm("ex0dte_iwm", "new_ex0dte", "IWM", 3, "0DTE-excluded, IWM 2020-2026", start=date(2020, 1, 1)),
    "intraday_spy": Arm("intraday_spy", "intraday_late", "SPY", 3, "Late-session intraday snapshot at T+0 vs EOD, SPY 2026",
                        window_series_key="intraday_t0"),
    "bridge_old": Arm("bridge_old", "old_bs", "SPY", 4, "Optional: pre-rebuild daily-table convention, SPY"),
}


def arm_date_range(arm: Arm) -> Tuple[date, date]:
    series = SERIES[arm.series_key]
    start = arm.start or series.start or SYMBOL_START[arm.symbol]
    end = arm.end or series.end
    return start, end


# --------------------------------------------------------------------------- model configuration
MODEL = "gpt-6-luna"
REASONING_EFFORT = "medium"  # o4-mini's default effort in the published run; probe: 31/31 verdicts correct
MAX_COMPLETION_TOKENS = 4000  # probe: medium effort averaged 814 completion tokens, max ~1,200
RETRY_MAX_COMPLETION_TOKENS = 8000  # for finish_reason == 'length' rows
PROMPT_VERSION = "v2.0_postgresql"  # same prompt text as Phase 4A (MechanicsPromptBuilder.build_regime_prompt)
RESPONSE_FORMAT = "json_schema"  # the one protocol change vs Phase 4A; disclosed in the paper
BATCH_COMPLETION_WINDOW = "24h"
R1_MODEL = "o4-mini-2025-04-16"

# USD per 1M tokens: (input, output). Batch is 50% of standard.
PRICING_USD_PER_MTOK: Dict[str, Dict[str, Tuple[float, float]]] = {
    "gpt-6-luna": {"standard": (0.10, 0.50), "batch": (0.05, 0.25)},
    "o4-mini": {"standard": (1.10, 4.40), "batch": (0.55, 2.20)},
    "o4-mini-2025-04-16": {"standard": (1.10, 4.40), "batch": (0.55, 2.20)},
}

REGIME_TYPES = ("persistent_positive", "persistent_negative", "transitional", "low_conviction")

REGIME_JSON_SCHEMA: Dict[str, Any] = {
    "name": "regime_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "regime_detected": {"type": "boolean"},
            "regime_type": {"type": "string", "enum": list(REGIME_TYPES)},
            "positive_days": {"type": "integer"},
            "negative_days": {"type": "integer"},
            "avg_magnitude_billions": {"type": "number"},
            "sign_flips": {"type": "integer"},
            "persistence_pct": {"type": "number"},
            "confidence": {"type": "integer"},
            "reasoning": {"type": "string"},
        },
        "required": ["regime_detected", "regime_type", "positive_days", "negative_days",
                     "avg_magnitude_billions", "sign_flips", "persistence_pct", "confidence", "reasoning"],
    },
}


def estimate_cost_usd(model: str, mode: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = PRICING_USD_PER_MTOK[model][mode]
    return (prompt_tokens * inp + completion_tokens * out) / 1e6


# --------------------------------------------------------------------------- obfuscation / prompt / classifier
def obfuscate(values_usd: Sequence[float], dates: Optional[Sequence[date]] = None,
              labels: str = "obfuscated") -> List[Dict[str, Any]]:
    """Build the prompt-builder input for a 30-day sequence.

    labels='obfuscated' relabels exactly as Phase 4A did ("Day T-29" .. "Day T+0");
    labels='dated' reproduces the Nov-2025 Phase 3/4 prompts (ISO dates as labels) and needs ``dates``.
    """
    if len(values_usd) != WINDOW_DAYS:
        raise ValueError(f"expected {WINDOW_DAYS} values, got {len(values_usd)}")
    if labels == "dated" and (dates is None or len(dates) != WINDOW_DAYS):
        raise ValueError("labels='dated' needs the 30 dates")
    seq = []
    for j, v in enumerate(values_usd):
        if v is None or v != v:  # None / NaN would reach the model as the text 'nanB'
            raise ValueError(f"value {j} is missing or NaN")
        if labels == "dated":
            label = dates[j].isoformat()
        else:
            offset = j - (WINDOW_DAYS - 1)
            label = f"Day T{offset:+d}" if offset != 0 else "Day T+0"
        seq.append({"date": label, "net_gex_usd": float(v)})
    return seq


def build_prompt(gex_sequence: List[Dict[str, Any]]) -> str:
    from src.llm.mechanics_prompt_builder import MechanicsPromptBuilder

    return MechanicsPromptBuilder.build_regime_prompt(gex_sequence=gex_sequence)


_classifier = None


def classifier():
    """Shared RegimeClassifier instance.

    Thresholds come from the class constants (persistence 0.70 -> 21 of 30 days, $5B mean
    magnitude, <= 5 flips, $3B low-conviction floor); the config lookup in the constructor
    finds no regime_classification.* keys in the shipped YAML.
    """
    global _classifier
    if _classifier is None:
        from src.validation.regime_classifier import RegimeClassifier

        _classifier = RegimeClassifier()
    return _classifier


def classifier_version() -> str:
    c = classifier()
    return (f"regime_classifier@{git_sha()[:12]} persistence={c.persistence_threshold} "
            f"magnitude={c.magnitude_threshold:.0f} max_flips={c.max_sign_flips} low_conviction={c.low_conviction_mag:.0f}")


def classify(values_usd: Sequence[float]) -> Dict[str, Any]:
    """Deterministic Paper 2 verdict for a 30-day sequence (USD)."""
    result = classifier().classify_window([{"net_gex": float(v)} for v in values_usd])
    m = result["metrics"]
    return {
        "regime_type": result["regime_type"],
        "should_detect": bool(result["should_detect"]),
        "positive_days": int(m.positive_days),
        "negative_days": int(m.negative_days),
        "persistence_pct": float(m.persistence_pct),
        "avg_magnitude": float(m.avg_magnitude),
        "sign_flips": int(m.sign_flips),
    }


# --------------------------------------------------------------------------- windows
def windows_over(dates: Sequence[date], values: Sequence[float], calendar: Sequence[date],
                 end_min: Optional[date] = None, end_max: Optional[date] = None):
    """Yield (window_start, window_end, values[30]) for every end date whose 30 calendar days all have values.

    ``calendar`` is the complete trading-day list to build windows on; a window is valid only when
    every one of its 30 calendar days is present in ``dates`` (missing days drop the window, as in Phase 4A).
    """
    lookup = dict(zip(dates, values))
    cal = list(calendar)
    for i in range(WINDOW_DAYS - 1, len(cal)):
        end = cal[i]
        if end_min and end < end_min:
            continue
        if end_max and end > end_max:
            break
        span = cal[i - WINDOW_DAYS + 1: i + 1]
        vals = [lookup.get(d) for d in span]
        if any(v is None for v in vals):
            continue
        yield span[0], end, vals


# --------------------------------------------------------------------------- ids, keys, hashing
REPEAT_MARK = "#rep"  # test-retest repeats: arm '<arm>#rep1' and custom_id '<arm>|SYM|DATE#rep1' (04 writes, 05 reads)
REPEAT_ARM_SUFFIX = REPEAT_MARK + "1"


def custom_id(arm: str, symbol: str, window_end: date, repeat: int = 0) -> str:
    base = f"{arm}|{symbol}|{window_end.isoformat()}"
    return f"{base}{REPEAT_MARK}{repeat}" if repeat else base


def parse_custom_id(cid: str) -> Tuple[str, str, date]:
    """(arm, symbol, window_end); a trailing '#rep<k>' is removed (use custom_id_repeat for k)."""
    arm, symbol, d = cid.split("|")
    d = d.split(REPEAT_MARK)[0]
    return arm, symbol, date.fromisoformat(d)


def custom_id_repeat(cid: str) -> int:
    """Repeat index k of '<...>#rep<k>' (0 for an original request)."""
    return int(cid.rsplit(REPEAT_MARK, 1)[1] or 1) if REPEAT_MARK in cid else 0


def base_arm(arm: str) -> str:
    """'bridge_jan#rep1' -> 'bridge_jan'."""
    return arm.split(REPEAT_MARK)[0]


def counts_toward_budget(run: Dict[str, Any]) -> bool:
    """Only runs paid from the current balance count: live model, LLM arm, not a backfill."""
    arm = ARMS.get(base_arm(str(run.get("arm", ""))))
    if arm is not None and not arm.llm:
        return False
    if str(run.get("model", "")) != MODEL:
        return False
    meta = run.get("run_metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    return not bool(meta.get("backfill"))


def make_run_id(arm: str, model: str, mode: str, when: Optional[datetime] = None) -> str:
    when = when or datetime.now(timezone.utc)
    return f"{arm}_{model.replace('.', '')}_{mode}_{when.strftime('%Y%m%dT%H%M%SZ')}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # pragma: no cover - git missing
        return "unknown"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_backup_dir(run_id: str) -> Path:
    d = BACKUP_ROOT / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


class JSONEncoder(json.JSONEncoder):
    def default(self, o):  # noqa: D401
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        try:
            import numpy as np

            if isinstance(o, np.generic):
                return o.item()
        except ImportError:  # pragma: no cover
            pass
        return super().default(o)


def dumps(obj: Any, **kw) -> str:
    return json.dumps(obj, cls=JSONEncoder, **kw)


# --------------------------------------------------------------------------- OpenAI
def load_openai_key() -> str:
    """Read OPEN_AI_KEY from config/config.json (fallback: env). Never log the value."""
    try:
        with open(CONFIG_PATH) as fh:
            cfg = json.load(fh)
        key = cfg.get("OPEN_AI_KEY")
        if key:
            return key
    except FileNotFoundError:
        pass
    key = os.environ.get("OPEN_AI_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OpenAI key not found (config/config.json OPEN_AI_KEY or env OPEN_AI_KEY)")
    return key


def openai_client():
    from openai import OpenAI

    return OpenAI(api_key=load_openai_key())


def model_created_at(client, model: str = MODEL) -> Optional[datetime]:
    """created timestamp of the model object (the alias carries no dated snapshot)."""
    try:
        m = client.models.retrieve(model)
        return datetime.fromtimestamp(m.created, tz=timezone.utc)
    except Exception as exc:  # pragma: no cover - network
        logger.warning("models.retrieve(%s) failed: %s", model, exc)
        return None


def metrics_agree(llm: Dict[str, Any], clf: Dict[str, Any]) -> bool:
    """Model-reported counts/magnitude/persistence equal the classifier values within tolerance."""
    try:
        return (abs(llm["positive_days"] - clf["positive_days"]) <= 0.5
                and abs(llm["negative_days"] - clf["negative_days"]) <= 0.5
                and abs(llm["avg_magnitude_billions"] - clf["avg_magnitude"] / 1e9) <= 0.05
                and abs(llm["persistence_pct"] - clf["persistence_pct"]) <= 0.5)
    except (KeyError, TypeError):
        return False


T_RATES_VIEW = "backups.gex_llm_regime_rates_summary"


def chat_body(prompt: str, model: str = MODEL, reasoning_effort: str = REASONING_EFFORT,
              max_completion_tokens: int = MAX_COMPLETION_TOKENS, response_format: str = RESPONSE_FORMAT) -> Dict[str, Any]:
    """Request body shared by the Batch JSONL and the synchronous pilot."""
    body: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": max_completion_tokens,
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    if response_format == "json_schema":
        body["response_format"] = {"type": "json_schema", "json_schema": REGIME_JSON_SCHEMA}
    return body


# --------------------------------------------------------------------------- response parsing
_INT_FIELDS = ("positive_days", "negative_days", "sign_flips", "confidence")
_NUM_FIELDS = ("avg_magnitude_billions", "persistence_pct")


def normalize_payload(d: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce a parsed answer into the detection columns; raises on structural problems."""
    out: Dict[str, Any] = {}
    rd = d.get("regime_detected")
    if isinstance(rd, str):
        rd = rd.strip().lower() in ("true", "yes", "1")
    out["regime_detected"] = bool(rd) if rd is not None else None
    rt = d.get("regime_type")
    out["regime_type"] = str(rt).strip().lower() if rt is not None else None
    for f in _INT_FIELDS:
        v = d.get(f)
        out[f] = int(round(float(v))) if v is not None and str(v).strip() != "" else None
    for f in _NUM_FIELDS:
        v = d.get(f)
        out[f] = float(v) if v is not None and str(v).strip() != "" else None
    out["confidence"] = float(out["confidence"]) if out["confidence"] is not None else None
    out["reasoning"] = d.get("reasoning") if isinstance(d.get("reasoning"), str) else dumps(d.get("reasoning"))
    return out


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


def strip_json_fence(content: str) -> str:
    """The body of a ```json ... ``` fence when the whole answer is one fence; otherwise the answer unchanged."""
    match = _FENCE.match(content)
    return match.group(1) if match else content


def parse_llm_content(content: Optional[str]) -> Tuple[Optional[Dict[str, Any]], str]:
    """Return (normalized payload or None, parse_status in {ok, fallback, failed, missing})."""
    if content is None or not str(content).strip():
        return None, "missing"
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return normalize_payload(data), "ok"
    except Exception:
        pass
    for text in (content, strip_json_fence(content)):  # raw control characters inside strings (one Phase 4A answer,
        try:  # which is also fenced); still a direct parse of the whole answer
            data = json.loads(text, strict=False)
            if isinstance(data, dict):
                return normalize_payload(data), "ok"
        except Exception:
            pass
    try:
        from src.utils.json_parser import extract_json

        data = extract_json(content)
        if isinstance(data, dict):
            return normalize_payload(data), "fallback"
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("fallback parse failed: %s", exc)
    return None, "failed"


def usage_fields(usage: Optional[Dict[str, Any]]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    if not usage:
        return None, None, None
    pt = usage.get("prompt_tokens")
    ct = usage.get("completion_tokens")
    rt = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    return pt, ct, rt


# --------------------------------------------------------------------------- window rules, composites, budget
# A = 30 consecutive series rows (Phase 4A convention) with a flag when a span covers a calendar gap;
# J = the January 2026 calendar (jan2026_phase4a only).  Rule B of the data audit equals A for the new series.
WINDOW_RULE = "A"
WINDOW_RULE_COMPOSITE = "T0"  # composite windows (intraday_t0); 'C' is reserved for a strict NYSE calendar
# Two complementary hole detectors: calendar_gap_days > 4 (a 5+ day gap is never a plain holiday
# weekend) and missing_master_days (trading dates of gex.options_daily_summary absent from the series,
# which catches a single skipped weekday such as 2023-07-12 in the January calendar).
CALENDAR_GAP_FLAG_DAYS = 4
INTRADAY_T0_KEY = "intraday_t0"  # composite windows: new_full for T-29..T-1, intraday_late (final_rush) at T+0

QUIET_WINDOW_UTC = ((21, 50), (22, 45))  # daily ingest + daily-summary cron; no DDL, loads or raw scans inside it


def in_quiet_window(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    (h0, m0), (h1, m1) = QUIET_WINDOW_UTC
    t = now.hour * 60 + now.minute
    return h0 * 60 + m0 <= t <= h1 * 60 + m1


def assert_not_quiet(ignore: bool = False) -> None:
    """Refuse DB writes / raw scans during the upstream cron window unless explicitly overridden."""
    if in_quiet_window() and not ignore:
        raise RuntimeError("inside the 21:50-22:45 UTC quiet window; pass --ignore-busy-window to override")
BUDGET_USD_HARD_STOP = 12.0  # refuse to submit when projected + ledger spend would exceed this (balance $16.86 on 2026-10-28)
PILOT_WINDOWS = 40  # balanced on clf_should_detect
REPEAT_FRACTION = 0.05  # duplicate windows per arm for test-retest (or a full repeat of bridge_jan)

# Parquet copies (second copy per docs/009; the third is the raw JSONL per run).
PARQUET_ROOT = BACKUP_ROOT / "tables"


def parquet_path(kind: str, *parts: str) -> Path:
    """data/backups/gex_llm/tables/<kind>/<part>_<part>.parquet  (kind: series | windows | detections | runs)."""
    d = PARQUET_ROOT / kind
    d.mkdir(parents=True, exist_ok=True)
    return d / ("_".join(parts) + ".parquet")


# --------------------------------------------------------------------------- Phase 4A (published run) artefacts
_DAY_LINE = None


def load_phase4a_inputs() -> Dict[date, List[float]]:
    """{window_end: [30 values in USD]} parsed from the surviving January batch file (1,476 windows)."""
    import re

    global _DAY_LINE
    if _DAY_LINE is None:
        _DAY_LINE = re.compile(r"^Day T[-+]\d+: ([+-]?\d+\.\d+)B$", re.M)
    out: Dict[date, List[float]] = {}
    with open(PHASE4A_INPUT_JSONL) as fh:
        for line in fh:
            j = json.loads(line)
            end = date.fromisoformat(j["custom_id"].replace("window-", ""))
            vals = [float(v) * 1e9 for v in _DAY_LINE.findall(j["body"]["messages"][0]["content"])]
            if len(vals) != WINDOW_DAYS:
                raise ValueError(f"{j['custom_id']}: parsed {len(vals)} values")
            out[end] = vals
    return out


def phase4a_daily_series(raw_calendar: Sequence[date]) -> Dict[date, float]:
    """Reconstruct the January daily series on January's own calendar.

    Window ends are January's trading days from the 30th day on; the first window supplies the 29
    earlier days, which are taken from ``raw_calendar`` (today's raw-table dates) immediately before
    the first end.  Consecutive windows are checked for consistency.
    """
    wins = load_phase4a_inputs()
    ends = sorted(wins)
    series: Dict[date, float] = {}
    for k in range(1, len(ends)):
        if wins[ends[k]][:-1] != wins[ends[k - 1]][1:]:
            raise ValueError(f"non-consecutive windows between {ends[k-1]} and {ends[k]}")
    i0 = list(raw_calendar).index(ends[0])
    for d, v in zip(list(raw_calendar)[i0 - (WINDOW_DAYS - 1): i0], wins[ends[0]][:-1]):
        series[d] = v
    for e in ends:
        series[e] = wins[e][-1]
    return series


_DATED_LINE = None


def load_phase34_inputs(series_key: str) -> Dict[date, List[Tuple[date, float]]]:
    """{window_end: [(date, value_usd) x 30]} parsed from a Nov-2025 Phase 3/4 input file (dated prompts)."""
    import re

    global _DATED_LINE
    if _DATED_LINE is None:
        _DATED_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2}): ([+-]?\d+\.\d+)B$", re.M)
    base = series_key.replace("_dated", "")
    path = PHASE34_FILES[base][0]
    out: Dict[date, List[Tuple[date, float]]] = {}
    with open(path) as fh:
        for line in fh:
            j = json.loads(line)
            end = date.fromisoformat(j["custom_id"].replace("window-", ""))
            rows = [(date.fromisoformat(d), float(v) * 1e9)
                    for d, v in _DATED_LINE.findall(j["body"]["messages"][0]["content"])]
            if len(rows) != WINDOW_DAYS:
                raise ValueError(f"{path.name} {j['custom_id']}: parsed {len(rows)} values")
            out[end] = rows
    return out


def phase34_daily_series(series_key: str) -> Dict[date, float]:
    """Daily series (USD) implied by a Phase 3/4 input file; consecutive windows are checked for consistency."""
    wins = load_phase34_inputs(series_key)
    series: Dict[date, float] = {}
    for end, rows in wins.items():
        for d, v in rows:
            if d in series and abs(series[d] - v) > 0.006e9:
                raise ValueError(f"{series_key}: inconsistent value for {d} ({series[d]} vs {v})")
            series[d] = v
    return series


def load_phase34_outputs(series_key: str) -> Dict[date, Dict[str, Any]]:
    """{window_end: raw batch output line} of the Nov-2025 Phase 3/4 o4-mini run."""
    base = series_key.replace("_dated", "")
    out: Dict[date, Dict[str, Any]] = {}
    with open(PHASE34_FILES[base][1]) as fh:
        for line in fh:
            j = json.loads(line)
            out[date.fromisoformat(j["custom_id"].replace("window-", ""))] = j
    return out


def load_phase4a_outputs() -> Dict[date, Dict[str, Any]]:
    """{window_end: raw batch output line} from the surviving January output file (1,476 lines)."""
    out: Dict[date, Dict[str, Any]] = {}
    with open(PHASE4A_OUTPUT_JSONL) as fh:
        for line in fh:
            j = json.loads(line)
            out[date.fromisoformat(j["custom_id"].replace("window-", ""))] = j
    return out


# --------------------------------------------------------------------------- misc
def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
