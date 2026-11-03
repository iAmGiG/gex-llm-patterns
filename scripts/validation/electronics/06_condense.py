#!/usr/bin/env python
"""Write the condensed copies that the repository tracks (gex-llm-patterns #261).

Nothing raw goes to the remote: the OpenAI batch files (JSONL) and the full tables (series, windows,
detections with the model's text) stay on disk under data/backups/gex_llm/ and are loaded into the
research database (backups.gex_llm_regime_*).  Git keeps, besides docs/papers/electronics/results/
and the run provenance (tables/runs, manifests, batch objects), the three files written here:

  data/backups/gex_llm/condensed/detections.csv.gz   one row per stored model answer: verdict, type,
                                                      confidence, the five reported metrics, parse status,
                                                      token counts, custom_id -- no reasoning, no raw text
  data/backups/gex_llm/condensed/windows.csv.gz      one row per window: calendar, rule, input sha256 and
                                                      the deterministic classifier columns -- no sequences
  data/backups/gex_llm/condensed/series_index.csv    one row per (series_key, symbol): rows, range, source,
                                                      builder version -- no values

Every detection rate and agreement figure of the paper can be recomputed from the condensed detections
and windows (join on series_key, symbol, window_end); the other numbers are in results/, and the daily
values behind them are in the full tables (database, Zenodo deposit).  Run after every ingest:  python scripts/validation/electronics/06_condense.py
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

OUT = common.PARQUET_ROOT.parent / "condensed"
DETECTION_COLUMNS = [
    "run_id", "arm", "series_key", "symbol", "window_end", "model", "prompt_version", "custom_id",
    "regime_detected", "regime_type", "confidence", "positive_days", "negative_days", "avg_magnitude_billions",
    "sign_flips", "persistence_pct", "metrics_agree", "parse_status", "finish_reason", "prompt_tokens",
    "completion_tokens", "reasoning_tokens",
]
WINDOW_COLUMNS = [
    "series_key", "symbol", "window_end", "window_start", "n_days", "window_rule", "input_sha256",
    "clf_regime_type", "clf_should_detect", "clf_positive_days", "clf_negative_days", "clf_persistence_pct",
    "clf_avg_magnitude", "clf_sign_flips", "clf_version",
]


def load(kind: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(common.PARQUET_ROOT / kind / "*.parquet")))
    if not files:
        raise SystemExit(f"no {kind} parquet under {common.PARQUET_ROOT / kind}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def meta(text):
    return text if isinstance(text, dict) else json.loads(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT, help=f"output folder (default: {OUT})")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    detections = load("detections")
    # A window re-asked after its inputs changed has an older and a newer answer; keep the latest, as 05 and 07 do.
    key = ["arm", "series_key", "symbol", "window_end", "model", "prompt_version"]
    n_all = len(detections)
    detections = detections.sort_values("created_at", kind="stable", na_position="first").drop_duplicates(key, keep="last")
    if len(detections) < n_all:
        print(f"detections: {n_all - len(detections):,} superseded answer(s) dropped (latest created_at kept)")
    d = detections[DETECTION_COLUMNS].sort_values(["arm", "symbol", "window_end", "custom_id"], kind="stable")
    d.to_csv(args.out / "detections.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

    windows = load("windows")
    w = windows[WINDOW_COLUMNS].copy()
    w["calendar_gap_days"] = windows["window_metadata"].map(lambda m: meta(m).get("calendar_gap_days"))
    w["missing_master_days"] = windows["window_metadata"].map(lambda m: meta(m).get("missing_master_days"))
    w["nyse_missing_days"] = windows["window_metadata"].map(lambda m: meta(m).get("nyse_missing_days"))
    w = w.sort_values(["series_key", "symbol", "window_end"], kind="stable")
    w.to_csv(args.out / "windows.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})

    series = load("series")
    g = series.groupby(["series_key", "symbol"], as_index=False).agg(
        n_rows=("trading_date", "size"), first_date=("trading_date", "min"), last_date=("trading_date", "max"),
        source_table=("source_table", "first"),
    )
    g["builder_sha256"] = series.groupby(["series_key", "symbol"])["series_metadata"].first().map(
        lambda m: meta(m).get("builder_sha256")).values
    g.to_csv(args.out / "series_index.csv", index=False)

    for path in sorted(args.out.iterdir()):
        print(f"{path.stat().st_size:>10,d}  {path.relative_to(common.REPO_ROOT)}")
    print(f"detections {len(d):,} rows ({d['arm'].nunique()} arms) | windows {len(w):,} rows | series {len(g)} (series, symbol) pairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
