#!/usr/bin/env python
"""Package the four full result tables for the Zenodo deposit (gex-llm-patterns #261).

Writes data/backups/gex_llm/release/regan_xie_electronics_tables_<date>.zip with one parquet file per table
(gex_llm_regime_series, _windows, _runs and _detections, one row per natural key) in the folder layout that
05_report.py reads (series/, windows/, runs/, detections/), a second detections file with the
answers that a later answer replaced, a README describing them, and SHA-256 checksums. The detections file holds
exactly the answers the article counts (the latest per natural key, the rule of common.latest_answers that
05_report.py, 06_condense.py and 07_load_tables.py use); `detections_replaced.parquet` keeps the 1,049 answers that
the re-run of 2026-11-03 replaced and the open-weights answers cut off at the token limit that a retry replaced,
each with the run that replaced it, so both can be audited.
The Batch and local JSONL files of the model runs are not included (the detections hold every parsed answer and its
raw text, and `runs` holds the sha256 of every file), with one exception: the input and output files of the three
backfilled o4-mini runs (r1_o4mini, r1_p3_o4mini, r1_p4_o4mini), which exist in one copy only and which the published
lineage rests on, are copied byte for byte into `raw_backfill/` with a hashed `MANIFEST.csv` (about 16 MB, prompts that
hold daily aggregates only). Each file is checked against its manifest.json and the runs table before it is packaged.
The zip stays out of git (nothing raw goes to the GitHub remote); an author publishes it on Zenodo.

Local paths are made relative to the repository. The package is refused if any text cell still holds an absolute
local path, looks like a credential (OpenAI keys, bearer tokens, "key/secret/token/password = value" pairs) or
contains one of the secret values of config/config.json. Booleans, dates and numbers keep their types (only text
cells are rewritten). Run after the last ingest:
    python scripts/validation/electronics/08_package_release.py
    python scripts/validation/electronics/08_package_release.py --check <zip>   # regenerate results/ from the zip
--check unzips into a temporary folder, runs 05_report.py --source parquet on it and compares every result file with
docs/papers/electronics/results/ (report.yaml is compared without its provenance block, which names local files).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
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

Data deposit for two companion papers by Regan, C. and Xie, Y., both planned for Electronics (MDPI); the titles may
still change:

- Paper A: "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on Inputs with Both Option Legs and a
  Rule-Following Test of a Current LLM". It uses the arms answered by hosted models: the gpt-6-luna Batch arms and the
  three backfills of the published o4-mini answers (`r1_*`).
- Paper B: "Reproducing an LLM Evaluation After Its Hosted Model Is Retired: Open-Weights Models on Stored Requests".
  It uses the arms of the local models and their variants: the arms that begin with `oss_`, `osst0_`, `llama_`,
  `llamarf_`, `llamat0_` and `qwen_` (described below).

Both papers read the same four tables, so one deposit serves both. Code, condensed tables and result files:
https://github.com/iAmGiG/gex-llm-patterns

## Files

{table}

The four tables sit in the folder layout that the repository's `05_report.py` reads, so the article's result files
can be regenerated from this deposit alone (see "Regenerate the results" below).

`SHA256SUMS` holds the checksum of every file.

- `series/series.parquet`: one row per series, symbol and trading day: the daily GEX number shown to the model.
- `windows/windows.parquet`: one row per series, symbol and window end: the 30 values as shown to the model, their sha256
  and the verdict of the deterministic rule (`clf_*`).
- `runs/runs.parquet`: one row per Batch job, local run, pilot or backfilled run: identifiers, file hashes, token counts and
  cost (a local run also records its engine, weights revision and GPU in `run_metadata.local`).
- `detections/detections.parquet`: one row per natural key (`arm`, `series_key`, `symbol`, `window_end`, `model`,
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
open-weights model gpt-oss-20b, arms that begin with `llama_` those of Llama 3.1 8B Instruct and arms that begin with
`qwen_` those of Qwen3-8B, all run locally with vLLM at a pinned revision; the rest of their name is the gpt-6-luna arm that answered the same windows. Three protocol variants use the same weights under their own model label: arms that begin with `llamarf_` (model `llama-3.1-8b-instruct-rf`) are Llama 3.1 8B with the reasoning field first in the JSON schema, and the arms `osst0_bridge_jan` (model `gpt-oss-20b-t0`) and `llamat0_bridge_jan` (model `llama-3.1-8b-instruct-t0`) are gpt-oss-20b and Llama 3.1 8B with temperature 0 in every request. The series keys and arms are defined in Tables 1 and 3
of the article, and the column definitions are in `scripts/validation/electronics/sql/gex_llm_regime_schema.sql`
of the repository. Paths in `runs` are relative to the repository root.

## Regenerate the results

With a clone of the repository (Python 3.10 or later, pandas, pyarrow, scipy, PyYAML) and this zip unzipped into
`deposit/`:

    python scripts/validation/electronics/05_report.py --source parquet --parquet-root deposit --results-dir out

Every file in `out/` then equals the one in `docs/papers/electronics/results/` of the repository, except the
provenance block of `report.yaml` (date, commit, local file list and the fingerprint of the author-side files the
tables were read from). `detections_replaced.parquet` stays outside the four folders: the report does not read it.

## What is not here

The raw option chains are not included because of their size; the series keep the daily aggregates that every label
and answer depends on. The verbatim Batch and local input and output files of the gpt-6-luna and open-weights runs are
not included either (they total several hundred megabytes); `runs` gives the sha256 and size of each, and the
detections hold every parsed answer with its raw text.

What is deposited as files: the input and output of the three backfilled o4-mini runs, in `raw_backfill/` (the
January 2026 Phase 4A run, 1,476 requests; the 2024 baseline, 223; the 2020 baseline, 223). They are the only copies of
the published run on record, so they are kept verbatim; `raw_backfill/MANIFEST.csv` lists file, run, bytes, lines and
sha256, and `SHA256SUMS` covers them too. The sha256 values of the stored files, not the git commit ids that some
provenance fields name, are the binding record; the commit ids that cannot be reached from a branch are listed in
`docs/papers/electronics/planning/stamped_commits.md` of the repository.

## Licence and source

The tables are released under the Creative Commons Attribution 4.0 International licence (CC BY 4.0). The options data
behind the series come from Alpha Vantage under a premium API subscription whose terms permit this use.

## Note on two series

`jan2026_phase4a` holds the exact inputs of the January 2026 run as they were sent, and `old_bs` holds the pre-rebuild
archive table. Both carry the call leg only for SPY from late 2023; they are kept as they were so that the published
rates stay reproducible. See Sections 3.3 and 4.1 of the article.
"""


# the backfilled runs whose input and output exist in one copy only (folder under the raw root, run_id in the runs table)
BACKFILL_RUNS = {
    "r1_o4mini_phase4a_20260104": "r1_o4mini",
    "r1_p3_o4mini_20251120": "r1_p3_o4mini",
    "r1_p4_o4mini_20251120": "r1_p4_o4mini",
}
TABLES_ROOT = common.PARQUET_ROOT


def load(kind: str) -> pd.DataFrame:
    found = sorted((TABLES_ROOT / kind).glob("*.parquet"))
    if not found:
        raise SystemExit(f"no parquet under {TABLES_ROOT / kind}")
    return pd.concat([pd.read_parquet(path) for path in found], ignore_index=True)


def text_columns(frame: pd.DataFrame) -> List[str]:
    return [c for c in frame.columns if frame[c].dtype == object or str(frame[c].dtype) in ("string", "category")]


def relativize(frame: pd.DataFrame) -> pd.DataFrame:
    """Local absolute paths under the repository (any mount) become repository-relative, in plain and JSON text.

    Only str cells are rewritten. An object column can also hold booleans with gaps (regime_detected, metrics_agree
    once the per-run files are concatenated) or dates; casting those to str stored 'True'/'False' and '2024-01-02'
    as text in the deposits up to 20261110, which 05_report.py could not read."""
    out = frame.copy()
    for col in text_columns(out):
        mask = out[col].map(lambda v: isinstance(v, str)).astype(bool)
        if mask.any():
            out.loc[mask, col] = out.loc[mask, col].str.replace(REPO_PREFIX, "", regex=True)
    return out


def check_types(name: str, before: pd.DataFrame, after: pd.DataFrame) -> None:
    """Refuse the package if relativize changed the type of any non-text cell (booleans and dates stay typed)."""
    for col in before.columns:
        kinds_before = before[col].map(lambda v: type(v).__name__).value_counts().to_dict()
        kinds_after = after[col].map(lambda v: type(v).__name__).value_counts().to_dict()
        if kinds_before != kinds_after:
            raise SystemExit(f"{name}: column {col} changed type ({kinds_before} -> {kinds_after}); not packaged")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def backfill_files(raw_root: Path, runs: pd.DataFrame, secrets: List[str]) -> List[Tuple[str, bytes]]:
    """The input/output pairs of the backfilled runs, verbatim, plus raw_backfill/MANIFEST.csv.

    Every file is checked against the sha256 in its manifest.json and in the runs table and scanned for local paths and
    credentials; any mismatch refuses the package (the bytes are never rewritten, so the hashes stay those of the
    files the lineage rests on)."""
    known = re.compile("|".join(re.escape(s) for s in secrets)) if secrets else None
    by_run = runs.set_index("run_id")
    members: List[Tuple[str, bytes]] = []
    rows = ["run_id,arm,file,bytes,lines,sha256,what"]
    for folder, arm in BACKFILL_RUNS.items():
        manifest = json.loads((raw_root / folder / "manifest.json").read_text())
        run_id = manifest["run_id"]
        for name, what in (("input.jsonl", "requests as sent to the OpenAI Batch API"),
                           ("output.jsonl", "responses as returned by the OpenAI Batch API")):
            path = raw_root / folder / name
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            column = "input_sha256" if name.startswith("input") else "output_sha256"
            stored = (manifest["files"][name]["sha256"], by_run.loc[run_id, column])
            if digest != stored[0] or digest != stored[1]:
                raise SystemExit(f"{path}: sha256 {digest} differs from manifest/runs table {stored}; not packaged")
            text = data.decode("utf-8")
            for label, pattern in (("an absolute local path", LOCAL_PATH), ("a credential", SECRET),
                                   ("a config secret", known)):
                if pattern is not None and pattern.search(text):
                    raise SystemExit(f"{path} holds {label}; not packaged")
            members.append((f"raw_backfill/{run_id}/{name}", data))
            rows.append(f"{run_id},{arm},raw_backfill/{run_id}/{name},{len(data)},{text.count(chr(10))},{digest},{what}")
    members.append(("raw_backfill/MANIFEST.csv", ("\n".join(rows) + "\n").encode()))
    return members


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


MEMBER = {"series": "series/series.parquet", "windows": "windows/windows.parquet", "runs": "runs/runs.parquet",
          "detections": "detections/detections.parquet", "detections_replaced": "detections_replaced.parquet"}


PROVENANCE = {"generated_at", "git_sha", "results_dir", "source", "inputs_fingerprint", "parquet_root"}


def strip_provenance(node):
    """report.yaml without the keys that name the run rather than the results (date, commit, local files)."""
    if isinstance(node, dict):
        return {k: strip_provenance(v) for k, v in node.items() if k not in PROVENANCE}
    if isinstance(node, list):
        return [strip_provenance(v) for v in node]
    return node


def differences(a, b, where: str = "") -> List[str]:
    """Paths at which two parsed YAML documents differ (at most 20)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out: List[str] = []
        for k in sorted(set(a) | set(b), key=str):
            out += differences(a.get(k), b.get(k), f"{where}/{k}") if k in a and k in b else [f"{where}/{k}"]
        return out[:20]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += differences(x, y, f"{where}[{i}]")
        return out[:20]
    return [] if a == b else [where or "/"]


def check_zip(target: Path) -> int:
    """Unzip into a temporary folder, run 05_report.py on it and compare the result files with results/."""
    import yaml
    with tempfile.TemporaryDirectory() as tmp:
        root, out = Path(tmp) / "deposit", Path(tmp) / "out"
        with zipfile.ZipFile(target) as z:
            z.extractall(root)
        done = subprocess.run([sys.executable, str(HERE / "05_report.py"), "--source", "parquet", "--parquet-root",
                               str(root), "--results-dir", str(out)], capture_output=True, text=True)
        if done.returncode != 0:
            print(done.stdout[-2000:], done.stderr[-2000:], sep="\n")
            print(f"CHECK FAILED: 05_report.py exited with {done.returncode} on {target.name}")
            return 1
        bad = []
        for ref in sorted(common.RESULTS_DIR.iterdir()):
            new = out / ref.name
            if not ref.is_file():
                continue
            if not new.exists():
                bad.append(f"{ref.name}: not produced")
            elif ref.name == "report.yaml":
                a, b = (strip_provenance(yaml.safe_load(p.read_text())) for p in (ref, new))
                bad.extend(f"report.yaml: {where} differs" for where in differences(a, b))
            elif ref.read_bytes() != new.read_bytes():
                bad.append(f"{ref.name}: differs")
        for line in bad:
            print("  " + line)
        print(f"CHECK {'FAILED' if bad else 'ok'}: {target.name} regenerates {'not all of' if bad else 'all of'} "
              f"{common.RESULTS_DIR}")
        return 1 if bad else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=common.PARQUET_ROOT.parent / "release", help="output folder")
    parser.add_argument("--tables", type=Path, default=common.PARQUET_ROOT,
                        help="folder with series/ windows/ runs/ detections/ (default: data/backups/gex_llm/tables)")
    parser.add_argument("--raw-root", type=Path, default=common.BACKUP_ROOT,
                        help="folder with the r1_* run folders (default: data/backups/gex_llm)")
    parser.add_argument("--check", type=Path, metavar="ZIP", help="only check that ZIP regenerates results/")
    args = parser.parse_args(argv)
    if args.check:
        return check_zip(args.check)
    global TABLES_ROOT
    TABLES_ROOT = args.tables
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
        clean = relativize(frame)
        check_types(name, frame, clean)
        check_clean(name, clean, secrets)
        data = parquet_bytes(clean, SORT.get(name, SORT["detections"]))
        files.append((MEMBER[name], data))
        listing.append(f"| `{MEMBER[name]}` | {len(clean):,} | {len(data) / 1e6:.1f} MB |")
    raw = backfill_files(args.raw_root, tables["runs"], secrets)
    files.extend(raw)
    for name, data in raw:
        listing.append(f"| `{name}` | | {len(data) / 1e6:.1f} MB |")
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
    print(f"check it with: python {Path(__file__).relative_to(common.REPO_ROOT)} --check {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
