#!/usr/bin/env python
"""Load the parquet copies of the four result tables into backups.gex_llm_regime_* (gex-llm-patterns #261).

Straight upserts of the stored rows (copy 2) into the Postgres tables (copy 1): no source table is read, no
DDL is run (the tables must exist: documentation PR gex-database-infrastructure #165, applied 2026-10-30).
Idempotent on the natural keys; re-run after every ingest.  Refuses to write inside the monitors' quiet window
unless --ignore-busy-window is given.

  python scripts/validation/electronics/07_load_tables.py            # all four tables, then ANALYZE
  python scripts/validation/electronics/07_load_tables.py --tables detections runs
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import sys
import time
from pathlib import Path

import pandas as pd
from psycopg2.extras import Json

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common  # noqa: E402

TABLES = {  # kind -> (table, natural key)
    "series": (common.T_SERIES, ("series_key", "symbol", "trading_date")),
    "windows": (common.T_WINDOWS, ("series_key", "symbol", "window_end")),
    "runs": (common.T_RUNS, ("run_id",)),
    "detections": (common.T_DETECTIONS, ("arm", "series_key", "symbol", "window_end", "model", "prompt_version")),
}
SERIAL = {"series_id", "window_id", "detection_id"}


def table_columns(conn, table: str):
    schema, name = table.split(".")
    with conn.cursor() as cur:
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema=%s AND table_name=%s "
                    "ORDER BY ordinal_position", (schema, name))
        return cur.fetchall()


def cell(value, data_type: str):
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if not isinstance(value, (str, bytes, bytearray, dict, list)):
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
    if data_type == "jsonb":
        if isinstance(value, (bytes, bytearray)):
            value = value.decode()
        if isinstance(value, str):
            return Json(json.loads(value))
        return Json(value)
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):  # numpy scalar
        return value.item()
    return value


def load(conn, kind: str) -> int:
    table, key = TABLES[kind]
    cols = table_columns(conn, table)
    files = sorted(glob.glob(str(common.PARQUET_ROOT / kind / "*.parquet")))
    if not files:
        raise SystemExit(f"no parquet under {common.PARQUET_ROOT / kind}")
    frame = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    use = [(c, t) for c, t in cols if c in frame.columns and c not in SERIAL]
    missing = [c for c, _ in cols if c not in frame.columns and c not in SERIAL]
    if missing:
        print(f"  {kind}: table columns absent from the parquet (left at their defaults): {missing}")
    names = [c for c, _ in use]
    if "created_at" in frame.columns:  # NOT NULL with a default: an explicit NULL would override the default
        frame["created_at"] = frame["created_at"].where(frame["created_at"].notna(), pd.Timestamp(common.utcnow()))
    rows = ([cell(v, t) for v, (_, t) in zip(rec, use)] for rec in frame[names].itertuples(index=False, name=None))
    before = time.perf_counter()
    sent = common.upsert_rows(conn, table, names, rows, key, page_size=500)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(f"ANALYZE {table}")
        cur.execute(f"SELECT count(*) FROM {table}")
        stored = cur.fetchone()[0]
    conn.commit()
    print(f"  {kind}: {sent:,} rows sent from {len(files)} file(s) -> {stored:,} rows in {table} ({time.perf_counter() - before:.1f} s)")
    return sent


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tables", nargs="+", choices=list(TABLES), default=list(TABLES))
    parser.add_argument("--ignore-busy-window", action="store_true")
    args = parser.parse_args(argv)
    common.setup_logging()
    common.assert_not_quiet(args.ignore_busy_window)
    conn = common.connect()
    try:
        for kind in [k for k in TABLES if k in args.tables]:
            load(conn, kind)
        with conn.cursor() as cur:
            cur.execute(f"SELECT arm, symbol, year, n_windows, llm_detect_pct, clf_detect_pct FROM {common.T_RATES_VIEW} "
                        "WHERE arm IN ('bridge_jan','full_spy') AND year IN (2024, 2025) ORDER BY 1, 3")
            for row in cur.fetchall():
                print("  view:", row)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
