#!/usr/bin/env python
"""Package the four full result tables for the Zenodo deposit (gex-llm-patterns #261).

Writes data/backups/gex_llm/release/regan_xie_electronics_tables_<date>.zip with the parquet copies of
gex_llm_regime_series, _windows, _runs and _detections, a README describing them, and SHA-256 checksums.
The Batch JSONL files are not included: the detections hold every parsed answer and its raw text.
The zip stays out of git (nothing raw goes to the GitHub remote); an author publishes it on Zenodo.

Stops if any file looks like it holds a credential.  Run after the last ingest:
    python scripts/validation/electronics/08_package_release.py
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

KINDS = ("series", "windows", "runs", "detections")
# OpenAI keys, bearer tokens and local home paths; "sk-" alone would match words such as "risk-".
SECRET = re.compile(r"sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}|api[_-]?key\s*[:=]\s*\S{12,}", re.IGNORECASE)

README = """# Daily GEX series, 30-day windows, model runs and answers: Persistent Dealer-Gamma Regimes Under Temporal Obfuscation

Data deposit for: Regan, C.; Xie, Y. "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on
Complete Inputs with a Controlled LLM Re-Test" (submitted to Electronics, MDPI).
Code, condensed tables and result files: https://github.com/iAmGiG/gex-llm-patterns

## Files

{table}

Each file is one parquet slice of a table; the slices of a table have the same columns and can be concatenated.
`SHA256SUMS` holds the checksum of every file.

- `tables/series/`: one row per series, symbol and trading day: the daily GEX number shown to the model.
- `tables/windows/`: one row per series, symbol and window end: the 30 values as shown to the model, their
  sha256 and the verdict of the deterministic rule (`clf_*`).
- `tables/runs/`: one row per Batch job, pilot or backfilled run: identifiers, file hashes, token counts and cost.
- `tables/detections/`: one row per model answer: verdict, reported metrics, reasoning, raw response, parse status.

Join detections to windows on `series_key`, `symbol`, `window_end`. The series keys and arms are defined in Tables 1
and 3 of the article, and the column definitions are in `scripts/validation/electronics/sql/gex_llm_regime_schema.sql`
of the repository.

## What is not here

The raw option chains are not included: they come from a licensed vendor and are not redistributed. The series keep
daily aggregates only. The verbatim Batch input and output files are not included either.

## Note on two series

`jan2026_phase4a` holds the exact inputs of the January 2026 run as they were sent, and `old_bs` holds the pre-rebuild
archive table. Both carry the call leg only for SPY from late 2023; they are kept as they were so that the published
rates stay reproducible. See Sections 3.3 and 4.1 of the article.
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=common.PARQUET_ROOT.parent / "release", help="output folder")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    rows, sums, listing = {}, [], []
    files = []
    for kind in KINDS:
        found = sorted((common.PARQUET_ROOT / kind).glob("*.parquet"))
        if not found:
            raise SystemExit(f"no parquet under {common.PARQUET_ROOT / kind}")
        n = 0
        for path in found:
            frame = pd.read_parquet(path)
            n += len(frame)
            for col in frame.columns:
                if frame[col].dtype == object:
                    hit = frame[col].dropna().astype(str).str.contains(SECRET).sum()
                    if hit:
                        raise SystemExit(f"{path.name}: column {col} has {hit} value(s) that look like a credential; not packaged")
            files.append((f"tables/{kind}/{path.name}", path))
        rows[kind] = n
        size = sum(p.stat().st_size for _, p in files if p.parent.name == kind)
        listing.append(f"| `tables/{kind}/` | {len(found)} | {n:,} | {size / 1e6:.1f} MB |")
    table = "| Folder | Files | Rows | Size |\n|---|---|---|---|\n" + "\n".join(listing)
    readme = README.format(table=table).encode()
    target = args.out / f"regan_xie_electronics_tables_{date.today():%Y%m%d}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.md", readme)
        sums.append(f"{hashlib.sha256(readme).hexdigest()}  README.md")
        for name, path in files:
            z.write(path, name)
            sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}")
        z.writestr("SHA256SUMS", "\n".join(sums) + "\n")
    print(f"{target} ({target.stat().st_size / 1e6:.1f} MB, {len(files)} tables files)")
    print("rows:", {k: f"{v:,}" for k, v in rows.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
