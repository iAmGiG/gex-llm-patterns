#!/usr/bin/env python
"""Package the four full result tables for the Zenodo deposit (gex-llm-patterns #261).

Writes data/backups/gex_llm/release/regan_xie_electronics_tables_<date>.zip with one parquet file per table
(gex_llm_regime_series, _windows, _runs and _detections, one row per natural key), a second detections file with the
answers that a later answer replaced, a README describing them, and SHA-256 checksums. The detections file holds
exactly the answers the article counts (the latest per natural key, the rule of common.latest_answers that
05_report.py, 06_condense.py and 07_load_tables.py use); `detections_replaced.parquet` keeps the 1,049 answers that
the re-run of 2026-11-03 replaced and the open-weights answers cut off at the token limit that a retry replaced,
each with the run that replaced it, so both can be audited.
The Batch and local JSONL files are not included: the detections hold every parsed answer and its raw text.
The zip stays out of git (nothing raw goes to the GitHub remote); an author publishes it on Zenodo.

Local paths are made relative to the repository. The package is refused if any text cell still holds an absolute
local path, looks like a credential (OpenAI keys, bearer tokens, "key/secret/token/password = value" pairs) or
contains one of the secret values of config/config.json. Run after the last ingest:
    python scripts/validation/electronics/08_package_release.py
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

KINDS = ("series", "windows", "runs", "detections")
KEYS = {
    "series": ("series_key", "symbol", "trading_date"),
    "windows": ("series_key", "symbol", "window_end"),
    "runs": ("run_id",),
    "detections": ("arm", "series_key", "symbol", "window_end", "model", "prompt_version"),
}
SORT = {
    "series": ["series_key", "symbol", "trading_date"],
    "windows": ["series_key", "symbol", "window_end"],
    "runs": ["run_id"],
    "detections": ["arm", "series_key", "symbol", "window_end", "model", "prompt_version", "run_id"],
}
# OpenAI keys (not inside words such as "risk-adjusted"), bearer tokens, and key/secret/token/password = value pairs
# in JSON, YAML or shell form (a field name ending in "_tokens", such as prompt_tokens, does not match).
SECRET = re.compile(
    r"(?<![A-Za-z0-9])sk-(?:proj-)?(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{20,}"
    r"|Bearer\s+[A-Za-z0-9._-]{20,}"
    r"|[\"']?\b[\w-]*(?:api[_-]?key|[_-]key|secret|token|password|passwd)[\"']?\s*[:=]\s*[\"']?[^\s\"',}]{8,}",
    re.IGNORECASE,
)
LOCAL_PATH = re.compile(r"/(?:mnt|home|tmp|Users)/[^\s\"',]+")
# the repository under any mount it has had (the backfills of 2025 recorded /mnt/bst/yxie2/..., today /mnt/bst/a100/...)
REPO_PREFIX = re.compile(r"/(?:mnt|home|Users)/[^\s\"',]*?/gex-llm-patterns(?=/|\b)/?")
ZIP_TIME = (2026, 1, 1, 0, 0, 0)  # fixed member timestamps, so the same tables give the same zip

README = """# Daily GEX series, 30-day windows, model runs and answers: Persistent Dealer-Gamma Regimes Under Temporal Obfuscation

Data deposit for: Regan, C.; Xie, Y. "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on
Complete Inputs with a Controlled LLM Re-Test" (submitted to Electronics, MDPI).
Code, condensed tables and result files: https://github.com/iAmGiG/gex-llm-patterns

## Files

{table}

`SHA256SUMS` holds the checksum of every file.

- `series.parquet`: one row per series, symbol and trading day: the daily GEX number shown to the model.
- `windows.parquet`: one row per series, symbol and window end: the 30 values as shown to the model, their sha256
  and the verdict of the deterministic rule (`clf_*`).
- `runs.parquet`: one row per Batch job, local run, pilot or backfilled run: identifiers, file hashes, token counts and
  cost (a local run also records its engine, weights revision and GPU in `run_metadata.local`).
- `detections.parquet`: one row per natural key (`arm`, `series_key`, `symbol`, `window_end`, `model`,
  `prompt_version`): the answer the article counts. Verdict, reported metrics, reasoning, raw response, parse status.
  An answer that replaced an earlier one names it in `detection_metadata.supersedes`.
- `detections_replaced.parquet`: the answers that a later answer to the same key replaced ({n_replaced:,} rows:
  {n_rerun:,} replaced by the re-run of 2026-11-03 after the database added missing trading days, and {n_retry:,}
  open-weights answers cut off at the limit of 4,000 completion tokens and replaced by a retry at 8,000), with
  `replaced_by_run_id`.
  They are kept for audit and are not counted anywhere in the article.

The current answer of a key is the one with the latest `created_at`; an answer without one (stored before the
column existed) is dated by its run's `ingested_at`. Join detections to windows on `series_key` (for arm
`intraday_spy` the windows are `intraday_t0`), `symbol` and `window_end`. The arm `r1_o4mini` holds the published
o4-mini answers; the 64 answers flagged `detection_metadata.recovered_2026` are not part of the published result.
Repeats (test-retest) are stored as arms ending in `#rep1`. Arms that begin with `oss_` hold the answers of the
open-weights model gpt-oss-20b and arms that begin with `llama_` those of Llama 3.1 8B Instruct, both run locally with
vLLM at a pinned revision; the rest of their name is the gpt-6-luna arm that answered the same windows. The series keys and arms are defined in Tables 1 and 3
of the article, and the column definitions are in `scripts/validation/electronics/sql/gex_llm_regime_schema.sql`
of the repository. Paths in `runs` are relative to the repository root.

## What is not here

The raw option chains are not included because of their size; the series keep the daily aggregates that every label
and answer depends on. The verbatim Batch and local input and output files are not included either.

## Licence and source

The tables are released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0). The options data
behind the series come from Alpha Vantage under a premium API subscription whose terms permit this use.

## Note on two series

`jan2026_phase4a` holds the exact inputs of the January 2026 run as they were sent, and `old_bs` holds the pre-rebuild
archive table. Both carry the call leg only for SPY from late 2023; they are kept as they were so that the published
rates stay reproducible. See Sections 3.3 and 4.1 of the article.
"""


def load(kind: str) -> pd.DataFrame:
    found = sorted((common.PARQUET_ROOT / kind).glob("*.parquet"))
    if not found:
        raise SystemExit(f"no parquet under {common.PARQUET_ROOT / kind}")
    return pd.concat([pd.read_parquet(path) for path in found], ignore_index=True)


def text_columns(frame: pd.DataFrame) -> List[str]:
    return [c for c in frame.columns if frame[c].dtype == object or str(frame[c].dtype) in ("string", "category")]


def relativize(frame: pd.DataFrame) -> pd.DataFrame:
    """Local absolute paths under the repository (any mount) become repository-relative, in plain and JSON text."""
    out = frame.copy()
    for col in text_columns(out):
        mask = out[col].notna()
        out.loc[mask, col] = out.loc[mask, col].astype(str).str.replace(REPO_PREFIX, "", regex=True)
    return out


def config_secrets() -> List[str]:
    """String values of config/config.json whose key names a key, token, secret or password (never printed)."""
    path = common.REPO_ROOT / "config" / "config.json"
    try:
        config = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    found: List[str] = []

    def walk(node, name: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, str(k))
        elif isinstance(node, list):
            for v in node:
                walk(v, name)
        elif isinstance(node, str) and len(node) >= 12 and re.search(r"key|token|secret|pass", name, re.IGNORECASE):
            found.append(node)

    walk(config)
    return found


def check_clean(name: str, frame: pd.DataFrame, secrets: List[str]) -> None:
    """Refuse the package if a text cell holds a local path or anything that looks like a credential."""
    known = re.compile("|".join(re.escape(s) for s in secrets)) if secrets else None
    for col in text_columns(frame):
        cells = frame[col].dropna().astype(str)
        for label, pattern in (("an absolute local path", LOCAL_PATH), ("a credential", SECRET), ("a config secret", known)):
            if pattern is None:
                continue
            hits = int(cells.str.contains(pattern).sum())
            if hits:
                raise SystemExit(f"{name}: column {col} has {hits} value(s) holding {label}; not packaged")


def split_detections(detections: pd.DataFrame, run_times: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """(current answers, one per natural key; replaced answers with the run that replaced each)."""
    key = list(KEYS["detections"])
    current = common.latest_answers(detections, key, run_times)
    replaced = detections.drop(index=current.index)
    by_key = current.set_index(key)["run_id"]
    replaced = replaced.assign(replaced_by_run_id=[by_key.get(tuple(row)) for row in replaced[key].itertuples(index=False)])
    return current, replaced


def retry_runs(runs: pd.DataFrame) -> set:
    """run_ids of the retry runs (run_metadata.retry_of, written by 04_llm_runner.py retry)."""
    found = set()
    for run_id, meta in zip(runs["run_id"], runs["run_metadata"]):
        if isinstance(meta, (bytes, bytearray)):
            meta = meta.decode()
        if isinstance(meta, str):
            meta = json.loads(meta) if meta else {}
        if isinstance(meta, dict) and meta.get("retry_of"):
            found.add(run_id)
    return found


def parquet_bytes(frame: pd.DataFrame, order: List[str]) -> bytes:
    buffer = io.BytesIO()
    frame.sort_values([c for c in order if c in frame.columns], kind="stable").reset_index(drop=True).to_parquet(
        buffer, index=False)
    return buffer.getvalue()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=common.PARQUET_ROOT.parent / "release", help="output folder")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    secrets = config_secrets()
    tables: Dict[str, pd.DataFrame] = {kind: load(kind) for kind in KINDS}
    run_times = common.run_ingest_times(tables["runs"])
    for kind in ("series", "windows", "runs"):
        tables[kind] = common.latest_answers(tables[kind], list(KEYS[kind]))
    tables["detections"], tables["detections_replaced"] = split_detections(tables["detections"], run_times)
    missing = tables["detections_replaced"]["replaced_by_run_id"].isna().sum()
    if missing:
        raise SystemExit(f"{missing} replaced answer(s) without a current answer for their key; not packaged")
    files: List[Tuple[str, bytes]] = []
    listing = []
    for name, frame in tables.items():
        frame = relativize(frame)
        check_clean(name, frame, secrets)
        data = parquet_bytes(frame, SORT.get(name, SORT["detections"]))
        files.append((f"{name}.parquet", data))
        listing.append(f"| `{name}.parquet` | {len(frame):,} | {len(data) / 1e6:.1f} MB |")
    table = "| File | Rows | Size |\n|---|---|---|\n" + "\n".join(listing)
    replaced = tables["detections_replaced"]
    n_retry = int(replaced["replaced_by_run_id"].isin(retry_runs(tables["runs"])).sum())
    readme = README.format(table=table, n_replaced=len(replaced), n_rerun=len(replaced) - n_retry,
                           n_retry=n_retry).encode()
    sums = [f"{hashlib.sha256(readme).hexdigest()}  README.md"]
    target = args.out / f"regan_xie_electronics_tables_{date.today():%Y%m%d}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("README.md", ZIP_TIME), readme, zipfile.ZIP_DEFLATED)
        for name, data in files:
            z.writestr(zipfile.ZipInfo(name, ZIP_TIME), data, zipfile.ZIP_DEFLATED)
            sums.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
        z.writestr(zipfile.ZipInfo("SHA256SUMS", ZIP_TIME), "\n".join(sums) + "\n", zipfile.ZIP_DEFLATED)
    print(f"{target} ({target.stat().st_size / 1e6:.1f} MB)")
    print("rows:", {name: f"{len(frame):,}" for name, frame in tables.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
