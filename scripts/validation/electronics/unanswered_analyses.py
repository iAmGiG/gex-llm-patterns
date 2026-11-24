#!/usr/bin/env python3
"""What the unanswered answers do to the results (issue #298, audit items E7, C149, B030, C031).

Everything is computed from the stored tables (``data/backups/gex_llm/tables``); no model, database or API call.
The functions are pure (DataFrames in, DataFrames or dicts out); ``main`` loads the tables, runs them and writes
sorted CSV files and ``summary.yaml`` into ``--out``.  The module reuses 05_report.py (loading, typing, parse flag,
window join, kappa) by import and does not copy it.

Vocabulary
----------
answer rows
    Every stored row of ``tables/detections``.  A window (key: arm, series_key, symbol, window_end, model,
    prompt_version) can have several: the first pass and the retry at the higher cap (or a re-run of a changed
    window).  ``pass_no`` numbers them by ``created_at`` (1 = first stored).
final row
    The latest row of a key: the one rule of ``common.latest_answers``, which 05_report, 06_condense and
    07_load_tables share.  05_report's ``parsed`` flag is applied to it: ``parse_status`` in (ok, fallback), a
    boolean ``regime_detected`` and a ``finish_reason`` that is neither ``length`` nor ``content_filter``.
unanswered window
    A final row that is not ``parsed``.  Three kinds: ``missing`` (empty content, the reasoning used up the cap),
    ``failed`` (content is a JSON object cut at the cap) and ``complete_at_cap`` (the object is complete, parse ok,
    but ``finish_reason`` is ``length``; 05_report counts it as unparsed).
recoverable verdict
    The boolean ``regime_detected`` of an unanswered window that ``scan_answer`` reads out of the final content
    (``raw_response``) with a strict scanner, see ``scan_answer``.  ``raw_response`` holds only the final content:
    vLLM's reasoning parser (``--reasoning-parser``) puts the thinking into a separate field that the tables never
    stored, so the thinking text cannot contain a match.  An empty ``raw_response`` (kind ``missing``) has no verdict.
rule verdict
    ``clf_should_detect`` of the stored window the answer was scored against (the deterministic rule).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import common  # noqa: E402
import stored_analyses as sa  # noqa: E402


def load_report_module():
    """05_report.py as a module (its file name starts with a digit, so it cannot be imported by name)."""
    if "report05" in sys.modules:
        return sys.modules["report05"]
    spec = importlib.util.spec_from_file_location("report05", HERE / "05_report.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["report05"] = module
    spec.loader.exec_module(module)
    return module


REPORT = load_report_module()
PERIODS = REPORT.PERIODS

# The rule (src/validation/regime_classifier.py): at least 21 of 30 days (70%) of one sign, mean |GEX| of at least
# USD 5 billion, at most 5 sign flips.  The prompt states the same numbers.
PERSISTENCE_MIN_PCT = 70.0
MAGNITUDE_MIN_BN = 5.0
FLIPS_MAX = 5

STATE_EMPTY = "empty"
STATE_NOT_OBJECT = "not_object"
STATE_MALFORMED = "malformed"
STATE_COMPLETE = "complete"
STATE_COMPLETE_NO_VERDICT = "complete_no_verdict"
STATE_CUT_WITH_VERDICT = "cut_after_verdict"
STATE_CUT_BEFORE_VERDICT = "cut_before_verdict"
VERDICT_KEY = "regime_detected"
_WS = " \t\r\n"
_TOKEN_END = _WS + ",}]"


# --------------------------------------------------------------------------- strict extractor
def _read_string(text: str, i: int) -> Tuple[Optional[str], int]:
    """Read the JSON string whose opening quote is at ``text[i]``; (value, index after the closing quote), or
    (None, len(text)) when the text ends inside it.  Escapes are skipped, not decoded."""
    j = i + 1
    n = len(text)
    while j < n:
        c = text[j]
        if c == "\\":
            j += 2
            continue
        if c == '"':
            return text[i + 1:j], j + 1
        j += 1
    return None, n


def _skip_nested(text: str, i: int) -> Optional[int]:
    """Index after the object or array that starts at ``text[i]`` (string-aware); None when the text ends inside it."""
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            _, i = _read_string(text, i)
            if _ is None:
                return None
            continue
        if c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def scan_answer(content: Optional[str]) -> Dict[str, Any]:
    """Read the top-level keys of a (possibly cut) JSON object without parsing it as a whole.

    Returns ``{"state", "verdict", "last_key", "n_keys"}``.  ``verdict`` is the value of the top-level key
    ``regime_detected`` when it is the bare literal ``true`` or ``false`` and is complete: followed by a delimiter
    (comma, closing brace or whitespace), so that a cut inside the word never counts.  Only top-level keys are read:
    the scanner walks strings as strings, so the words true, false or ``regime_detected`` inside the ``reasoning``
    string (or inside a nested value) are never matched.  A repeated key keeps its first value.

    ``state``: ``empty`` (no content), ``not_object`` (text that does not start with an opening brace),
    ``malformed`` (a character where a key or value is expected that JSON does not allow), ``complete`` (the object
    is closed and has the verdict), ``complete_no_verdict`` (closed, no usable verdict), ``cut_after_verdict`` (the
    text ends inside the object after the verdict was read), ``cut_before_verdict`` (it ends before).  ``last_key`` is
    the key whose value (or name) was open when the text ended, or the last key read.
    """
    if content is None or not str(content).strip():
        return {"state": STATE_EMPTY, "verdict": None, "last_key": None, "n_keys": 0}
    text = str(content)
    n = len(text)
    i = 0
    while i < n and text[i] in _WS:
        i += 1
    if i >= n or text[i] != "{":
        return {"state": STATE_NOT_OBJECT, "verdict": None, "last_key": None, "n_keys": 0}
    i += 1
    verdict: Optional[bool] = None
    seen_verdict = False
    last_key: Optional[str] = None
    n_keys = 0
    closed = False
    cut = False
    while True:
        while i < n and text[i] in _WS + ",":
            i += 1
        if i >= n:
            cut = True
            break
        if text[i] == "}":
            closed = True
            break
        if text[i] != '"':
            return {"state": STATE_MALFORMED, "verdict": verdict, "last_key": last_key, "n_keys": n_keys}
        key, i = _read_string(text, i)
        if key is None:
            cut = True
            break
        last_key = key
        n_keys += 1
        while i < n and text[i] in _WS:
            i += 1
        if i >= n:
            cut = True
            break
        if text[i] != ":":
            return {"state": STATE_MALFORMED, "verdict": verdict, "last_key": last_key, "n_keys": n_keys}
        i += 1
        while i < n and text[i] in _WS:
            i += 1
        if i >= n:
            cut = True
            break
        c = text[i]
        if c == '"':
            value, i = _read_string(text, i)
            if value is None:
                cut = True
                break
        elif c in "{[":
            nxt = _skip_nested(text, i)
            if nxt is None:
                cut = True
                break
            i = nxt
        else:
            j = i
            while j < n and text[j] not in _TOKEN_END:
                j += 1
            if j >= n:  # the token runs to the end of the text: not known to be complete
                cut = True
                break
            token = text[i:j]
            i = j
            if key == VERDICT_KEY and not seen_verdict and token in ("true", "false"):
                verdict = token == "true"
                seen_verdict = True
            continue
        if key == VERDICT_KEY and not seen_verdict:
            seen_verdict = True  # present but not a boolean: no verdict, and a later repeat does not replace it
    if closed:
        return {"state": STATE_COMPLETE if verdict is not None else STATE_COMPLETE_NO_VERDICT, "verdict": verdict,
                "last_key": last_key, "n_keys": n_keys}
    state = STATE_CUT_WITH_VERDICT if verdict is not None else STATE_CUT_BEFORE_VERDICT
    return {"state": state if cut else STATE_MALFORMED, "verdict": verdict, "last_key": last_key, "n_keys": n_keys}


# --------------------------------------------------------------------------- loading
DETECTION_COLUMNS = ["run_id", "arm", "series_key", "symbol", "window_end", "model", "prompt_version", "custom_id",
                     "regime_detected", "regime_type", "confidence", "positive_days", "negative_days",
                     "avg_magnitude_billions", "sign_flips", "persistence_pct", "metrics_agree", "parse_status",
                     "finish_reason", "prompt_tokens", "completion_tokens", "reasoning_tokens", "created_at",
                     "raw_response", "detection_metadata"]
KEY = ["arm", "series_key", "symbol", "window_end", "model", "prompt_version"]


def read_all_answer_rows(root: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Every stored detection row (all passes), typed as 05_report types them, plus ``raw_response`` and ``pass_no``.

    ``pass_no`` is 1 for the first stored row of a key (by ``created_at``; a row without one takes its run's ingestion
    time), 2 for the next, and so on; ``n_passes`` is the number of stored rows of the key and ``is_final`` marks the row
    ``common.latest_answers`` keeps.  ``parsed``, ``arm_role``, ``repeat_index`` and the stored window's ``clf_*``
    columns are added by 05_report's ``enrich_detections``.  Returns (answer rows, runs, windows).
    """
    raw_tables, _ = REPORT.read_parquet_tables(root)
    runs = REPORT.prepare_table("runs", raw_tables["runs"], [])
    windows = REPORT.prepare_table("windows", raw_tables["windows"], [])
    frames = []
    # The Zenodo deposit (08_package_release.py) keeps the answers that a later answer replaced in detections_replaced.parquet
    # next to the four table folders; the repository's tables hold every answer under detections/.
    replaced = root / "detections_replaced.parquet"
    paths = sorted((root / "detections").rglob("*.parquet")) + ([replaced] if replaced.exists() else [])
    for path in paths:
        wanted = [c for c in pq.read_schema(path).names if c in DETECTION_COLUMNS]
        frames.append(pd.read_parquet(path, columns=wanted))
    raw = pd.concat(frames, ignore_index=True, sort=False)
    typed = REPORT.coerce_table("detections", raw)
    typed["raw_response"] = raw["raw_response"] if "raw_response" in raw.columns else None
    typed["created_at"] = typed["created_at"].fillna(typed["run_id"].map(REPORT.run_timestamps(runs)))
    typed = typed[typed["window_end"].notna()]
    enriched = REPORT.enrich_detections(typed, windows)
    enriched = enriched.assign(_order=np.arange(len(enriched)))
    enriched = enriched.sort_values(["created_at", "_order"], kind="stable", na_position="first")
    grp = enriched.groupby(KEY, sort=False)
    enriched["pass_no"] = grp.cumcount() + 1
    enriched["n_passes"] = grp["pass_no"].transform("max")
    enriched["is_final"] = enriched["pass_no"] == enriched["n_passes"]
    cap = runs.set_index("run_id")["max_completion_tokens"] if len(runs) else pd.Series(dtype=float)
    enriched["request_cap"] = enriched["run_id"].map(cap)
    return enriched.drop(columns="_order").reset_index(drop=True), runs, windows


def check_final_rows(rows: pd.DataFrame, root: Path) -> Dict[str, Any]:
    """The final rows here equal the detections table 05_report builds (same keys, same run, same parsed flag)."""
    data = REPORT.load_data("parquet", root)
    mine = rows[rows["is_final"]]
    theirs = data.detections
    cols = ["arm", "series_key", "symbol", "window_end", "model", "prompt_version"]
    merged = mine[cols + ["run_id", "parsed"]].merge(theirs[cols + ["run_id", "parsed"]], on=cols, how="outer",
                                                     suffixes=("_mine", "_report"), indicator=True)
    both = merged[merged["_merge"] == "both"]
    return {"final_rows_here": int(len(mine)), "rows_in_report": int(len(theirs)),
            "only_here": int((merged["_merge"] == "left_only").sum()),
            "only_in_report": int((merged["_merge"] == "right_only").sum()),
            "run_id_differs": int((both["run_id_mine"] != both["run_id_report"]).sum()),
            "parsed_differs": int((both["parsed_mine"] != both["parsed_report"]).sum())}


# --------------------------------------------------------------------------- helpers
def rule_label(clf: pd.Series) -> pd.Series:
    """'detect', 'reject' or 'no_window' from clf_should_detect."""
    return pd.Series(np.where(clf.isna(), "no_window", np.where(clf.fillna(False).astype(bool), "detect", "reject")),
                     index=clf.index)


def with_scan(rows: pd.DataFrame) -> pd.DataFrame:
    """Add ``scan_state``, ``scan_verdict`` (True, False or NA) and ``scan_last_key`` from ``raw_response``."""
    scans = [scan_answer(v) for v in rows["raw_response"]]
    return rows.assign(scan_state=[s["state"] for s in scans],
                       scan_verdict=pd.array([s["verdict"] for s in scans], dtype="boolean"),
                       scan_last_key=[s["last_key"] for s in scans])


def unanswered_kind(rows: pd.DataFrame) -> pd.Series:
    """'answered', 'missing', 'failed' or 'complete_at_cap' (see the module docstring) for every row."""
    kind = np.where(rows["parsed"], "answered",
                    np.where(rows["parse_status"] == "missing", "missing",
                             np.where(rows["parse_status"] == "failed", "failed",
                                      np.where(rows["parse_status"].isin(["ok", "fallback"]), "complete_at_cap",
                                               "other"))))
    return pd.Series(kind, index=rows.index)


def recoverable_verdict(rows: pd.DataFrame) -> pd.Series:
    """Verdict (True, False, NA) of an unanswered final row: the scanner's, from ``raw_response``.

    For a ``complete_at_cap`` row the stored ``regime_detected`` is the verdict (the scanner returns the same).  An
    answered row has no recoverable verdict (NA): its verdict is ``regime_detected``.
    """
    if "scan_verdict" not in rows.columns:
        rows = with_scan(rows)
    out = rows["scan_verdict"].copy()
    out[rows["parsed"]] = pd.NA
    return out.astype("boolean")


def pct(k: float, n: float) -> float:
    return 100.0 * k / n if n else math.nan


def round_frame(frame: pd.DataFrame, digits: int = 6) -> pd.DataFrame:
    out = frame.copy()
    for col in out.columns:
        if pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].round(digits)
    return out


def in_years(window_end: pd.Series, first: Optional[int], last: Optional[int]) -> pd.Series:
    years = window_end.dt.year
    return years.between(first if first is not None else years.min(), last if last is not None else years.max())


# --------------------------------------------------------------------------- 1. census
def census(final: pd.DataFrame) -> pd.DataFrame:
    """Final rows by model, arm, request cap, parse kind, finish reason and the rule's verdict (count ``n``).

    ``request_cap`` is the ``max_completion_tokens`` of the run that produced the final row (4,000 for a first pass,
    8,000 for the retry run of Qwen3-8B).  ``cap_reached`` is True when ``completion_tokens`` equals it.  ``kind`` is
    ``unanswered_kind``; answered rows are included, so shares can be read from the same table.
    """
    f = final.assign(kind=unanswered_kind(final), rule=rule_label(final["clf_should_detect"]),
                     cap_reached=(final["completion_tokens"] >= final["request_cap"]).where(final["request_cap"].notna()))
    f["finish_reason"] = f["finish_reason"].fillna("unknown")
    f["request_cap"] = f["request_cap"].astype("Float64")
    out = (f.groupby(["model", "arm", "arm_role", "request_cap", "kind", "finish_reason", "cap_reached", "rule"],
                     dropna=False).size().rename("n").reset_index())
    out["request_cap"] = out["request_cap"].astype(float)
    return out.sort_values(["model", "arm", "request_cap", "kind", "finish_reason", "rule"], na_position="first",
                           kind="stable").reset_index(drop=True)


def reconcile_with_results(final: pd.DataFrame, parse_stats: pd.DataFrame, bounds: pd.DataFrame) -> Dict[str, Any]:
    """Compare unanswered counts of the final rows with results/llm_parse_stats.csv and missing_answer_bounds.csv.

    parse_stats: per (arm, model, series_key, symbol), ``n_rows - n_parsed`` equals the unanswered count here and
    ``n_finish_length`` the number of final rows with finish_reason length (which includes ``complete_at_cap``).
    bounds: ``n_unparsed`` of period ``all`` equals the unanswered count of the primary rows of that arm.
    Returns the list of differences (empty when everything matches) and the totals.
    """
    keys = ["arm", "model", "series_key", "symbol"]
    mine = final.assign(unans=~final["parsed"], length=final["finish_reason"].eq("length")).groupby(keys).agg(
        n_rows=("parsed", "size"), n_unanswered=("unans", "sum"), n_length=("length", "sum")).reset_index()
    stats = parse_stats.assign(n_unanswered_stored=parse_stats["n_rows"] - parse_stats["n_parsed"])
    m = mine.merge(stats[keys + ["n_rows", "n_unanswered_stored", "n_finish_length"]], on=keys, how="outer",
                   suffixes=("", "_stored"), indicator="src")
    diffs: List[Dict[str, Any]] = []
    for r in m.itertuples(index=False):
        if r.src != "both":
            diffs.append({"file": "llm_parse_stats.csv", "key": [r.arm, r.model, r.series_key, r.symbol],
                          "issue": str(r.src)})
            continue
        for mine_col, stored_col in (("n_rows", "n_rows_stored"), ("n_unanswered", "n_unanswered_stored"),
                                     ("n_length", "n_finish_length")):
            if int(getattr(r, mine_col)) != int(getattr(r, stored_col)):
                diffs.append({"file": "llm_parse_stats.csv", "key": [r.arm, r.model, r.series_key, r.symbol],
                              "column": mine_col, "here": int(getattr(r, mine_col)),
                              "stored": int(getattr(r, stored_col))})
    prim = final[final["arm_role"] == "primary"]
    mine_b = prim.assign(unans=~prim["parsed"]).groupby(keys)["unans"].sum().rename("n_unanswered").reset_index()
    stored_b = bounds[bounds["period"] == "all"][keys + ["n_unparsed"]]
    mb = mine_b[mine_b["n_unanswered"] > 0].merge(stored_b, on=keys, how="outer", indicator="src")
    for r in mb.itertuples(index=False):
        if r.src != "both" or int(r.n_unanswered) != int(r.n_unparsed):
            diffs.append({"file": "missing_answer_bounds.csv", "key": [r.arm, r.model, r.series_key, r.symbol],
                          "here": None if pd.isna(r.n_unanswered) else int(r.n_unanswered),
                          "stored": None if pd.isna(r.n_unparsed) else int(r.n_unparsed)})
    return {"n_differences": len(diffs), "differences": diffs,
            "unanswered_all_arms": int((~final["parsed"]).sum()),
            "unanswered_primary": int((~prim["parsed"]).sum()),
            "bounds_n_unparsed_total": int(stored_b["n_unparsed"].sum())}


# --------------------------------------------------------------------------- 2. recoverable verdicts
POPULATIONS = (
    ("all_failed_rows", "every stored row with parse_status failed, all passes and all arm roles"),
    ("first_pass_failed_rows", "stored rows with parse_status failed and pass_no 1 (later retried or not)"),
    ("final_failed_rows", "final rows with parse_status failed (arm roles primary, repeat and pilot)"),
    ("final_unanswered", "final rows that are not parsed (failed, missing and complete_at_cap)"),
    ("final_unanswered_primary", "as final_unanswered, primary arms only (the 11,750 windows of the paper)"),
)


def recoverable_table(rows: pd.DataFrame) -> pd.DataFrame:
    """Per model, arm and population: what a truncated answer still says (see ``POPULATIONS``).

    Columns: ``n_rows``; ``n_with_text`` (non-empty ``raw_response``); ``n_verdict`` (the scanner finds a complete
    boolean ``regime_detected``), split into ``n_verdict_true`` / ``n_verdict_false``; ``n_cut_after_verdict`` (object
    cut later) and ``n_cut_before_verdict``; ``n_complete`` (object closed: only for ``complete_at_cap`` rows);
    ``n_verdict_rule_detect`` and ``n_verdict_rule_reject`` (verdict rows by the rule's verdict) and
    ``n_verdict_agrees_rule``.
    """
    r = with_scan(rows)
    r = r.assign(kind=unanswered_kind(r), rule=rule_label(r["clf_should_detect"]))
    masks = {
        "all_failed_rows": r["parse_status"] == "failed",
        "first_pass_failed_rows": (r["parse_status"] == "failed") & (r["pass_no"] == 1),
        "final_failed_rows": r["is_final"] & (r["parse_status"] == "failed"),
        "final_unanswered": r["is_final"] & ~r["parsed"],
        "final_unanswered_primary": r["is_final"] & ~r["parsed"] & (r["arm_role"] == "primary"),
    }
    out = []
    for name, mask in masks.items():
        sub = r[mask]
        for (model, arm), g in sub.groupby(["model", "arm"], sort=True):
            has_v = g["scan_verdict"].notna()
            v = g["scan_verdict"].astype("boolean")
            known = g["rule"] != "no_window"
            out.append({
                "population": name, "model": model, "arm": arm, "n_rows": len(g),
                "n_with_text": int(g["raw_response"].fillna("").str.strip().ne("").sum()),
                "n_verdict": int(has_v.sum()), "n_verdict_true": int((v == True).sum()),  # noqa: E712
                "n_verdict_false": int((v == False).sum()),  # noqa: E712
                "n_cut_after_verdict": int((g["scan_state"] == STATE_CUT_WITH_VERDICT).sum()),
                "n_cut_before_verdict": int((g["scan_state"] == STATE_CUT_BEFORE_VERDICT).sum()),
                "n_complete": int((g["scan_state"] == STATE_COMPLETE).sum()),
                "n_verdict_rule_detect": int((has_v & (g["rule"] == "detect")).sum()),
                "n_verdict_rule_reject": int((has_v & (g["rule"] == "reject")).sum()),
                "n_verdict_agrees_rule": int((has_v & known & (v.fillna(False).astype(bool)
                                                              == (g["rule"] == "detect"))).sum())})
    cols = ["population", "model", "arm", "n_rows", "n_with_text", "n_verdict", "n_verdict_true", "n_verdict_false",
            "n_cut_after_verdict", "n_cut_before_verdict", "n_complete", "n_verdict_rule_detect",
            "n_verdict_rule_reject", "n_verdict_agrees_rule"]
    return pd.DataFrame(out, columns=cols).sort_values(["population", "model", "arm"]).reset_index(drop=True)


def scanner_check_on_answered(rows: pd.DataFrame) -> Dict[str, Any]:
    """The scanner against the parser on rows that parsed: same verdict on every answered row (per model)."""
    r = with_scan(rows[rows["parsed"]])
    same = r["scan_verdict"].astype("boolean") == r["regime_detected"].astype("boolean")
    res = {"n_answered_rows": int(len(r)), "n_same_verdict": int(same.fillna(False).sum()),
           "n_scanner_no_verdict": int(r["scan_verdict"].isna().sum())}
    by_model = r.assign(ok=same.fillna(False)).groupby("model")["ok"].agg(["size", "sum"])
    res["by_model"] = {m: {"n": int(x["size"]), "n_same": int(x["sum"])} for m, x in by_model.iterrows()}
    return res


def retry_stability_of_cut_verdicts(rows: pd.DataFrame) -> pd.DataFrame:
    """For windows whose first pass was cut after the verdict and whose retry answered: does the retry say the same?

    One row per model: ``n`` windows, ``n_same`` (same verdict), ``n_first_agrees_rule`` and ``n_retry_agrees_rule``.
    """
    r = with_scan(rows)
    first = r[(r["pass_no"] == 1) & r["scan_verdict"].notna() & (~r["parsed"])]
    final = r[r["is_final"] & r["parsed"] & (r["pass_no"] > 1)]
    m = first.merge(final, on=KEY, suffixes=("_first", "_final"))
    if m.empty:
        return pd.DataFrame(columns=["model", "n", "n_same", "n_first_agrees_rule", "n_retry_agrees_rule"])
    m = m.assign(same=m["scan_verdict_first"].astype(bool) == m["regime_detected_final"].astype(bool))
    known = m["clf_should_detect_final"].notna()
    clf = m["clf_should_detect_final"].fillna(False).astype(bool)
    m = m.assign(fa=known & (m["scan_verdict_first"].astype(bool) == clf),
                 ra=known & (m["regime_detected_final"].astype(bool) == clf))
    return (m.groupby("model").agg(n=("same", "size"), n_same=("same", "sum"), n_first_agrees_rule=("fa", "sum"),
                                   n_retry_agrees_rule=("ra", "sum")).astype(int).reset_index())


# --------------------------------------------------------------------------- 3. bounds
def bounds_with_recoverable(final: pd.DataFrame) -> pd.DataFrame:
    """The stored bounds of missing_answer_bounds.csv (same arms, periods and columns) and the bounds that use the
    recoverable verdicts.

    ``lower_pct`` / ``upper_pct``: every unanswered window counted as not detected / detected, over all windows of the
    arm and period.  ``n_recoverable`` unanswered windows hold a verdict (``n_recoverable_true`` of them true).
    ``lower_rec_pct`` = (answered detections + recoverable true) / n_windows (unrecoverable windows still count as not
    detected); ``upper_rec_pct`` = (answered detections + recoverable true + unrecoverable windows) / n_windows;
    ``rate_with_rec_pct`` is the rate over the answered plus recoverable windows.  ``width_pp`` and ``width_rec_pp``
    are the widths of the two intervals.
    """
    f = with_scan(final[final["arm_role"] == "primary"])
    f = f.assign(rec=recoverable_verdict(f))
    arms = sorted(set(f.loc[~f["parsed"], "arm"]))
    rows = []
    for (arm, model, series_key, symbol), g in f[f["arm"].isin(arms)].groupby(["arm", "model", "series_key", "symbol"], sort=True):
        for period, first, last in PERIODS:
            sub = g[in_years(g["window_end"], first, last)]
            if sub.empty:
                continue
            n = len(sub)
            parsed = sub["parsed"]
            k = int(sub.loc[parsed, "regime_detected"].astype(bool).sum())
            n_un = int((~parsed).sum())
            rec = sub["rec"]
            n_rec = int(rec.notna().sum())
            rec_true = int((rec == True).sum())  # noqa: E712
            n_rest = n_un - n_rec
            rows.append({
                "arm": arm, "model": model, "series_key": series_key, "symbol": symbol, "period": period,
                "n_windows": n, "n_parsed": int(parsed.sum()), "n_detected_parsed": k,
                "rate_parsed_pct": pct(k, int(parsed.sum())), "n_unparsed": n_un,
                "lower_pct": pct(k, n), "upper_pct": pct(k + n_un, n),
                "n_recoverable": n_rec, "n_recoverable_true": rec_true, "n_unrecoverable": n_rest,
                "lower_rec_pct": pct(k + rec_true, n), "upper_rec_pct": pct(k + rec_true + n_rest, n),
                "rate_with_rec_pct": pct(k + rec_true, int(parsed.sum()) + n_rec),
                "width_pp": pct(n_un, n), "width_rec_pp": pct(n_rest, n)})
    return round_frame(pd.DataFrame(rows).sort_values(["arm", "series_key", "symbol", "period"]).reset_index(drop=True))


# --------------------------------------------------------------------------- 4. agreement
def _cells(clf: np.ndarray, llm: np.ndarray) -> Tuple[int, int, int, int]:
    """(rule yes and llm yes, rule yes llm no, rule no llm yes, both no)."""
    clf = np.asarray(clf, dtype=bool)
    llm = np.asarray(llm, dtype=bool)
    return int((clf & llm).sum()), int((clf & ~llm).sum()), int((~clf & llm).sum()), int((~clf & ~llm).sum())


def _record(name: str, n_total: int, tt: int, tf: int, ft: int, ff: int, with_kappa: bool = True) -> Dict[str, Any]:
    n = tt + tf + ft + ff
    return {f"n_{name}": n_total, f"agree_{name}": tt + ff, f"agree_pct_{name}": pct(tt + ff, n_total),
            f"kappa_{name}": float(REPORT.binary_kappa(tt, tf, ft, ff)) if with_kappa and n else math.nan}


def agreement_variants(clf: Sequence[bool], answered: Sequence[bool], verdict: Sequence[Any],
                       recoverable: Optional[Sequence[Any]] = None) -> Dict[str, Any]:
    """Agreement of an arm's verdicts with the rule on windows that have a rule verdict, in five ways.

    Inputs are aligned vectors over the windows: ``clf`` (rule verdict, bool), ``answered`` (bool), ``verdict`` (the
    answer's verdict where answered, ignored elsewhere), ``recoverable`` (True, False or NA/None where the
    unanswered window holds a verdict; None as a whole means none).

    * ``answered``: answered windows only (what the paper prints).  ``agree_pct`` = agreeing / answered.
    * ``unans_no``: all windows; an unanswered window counts as verdict not detected.  Kappa from that 2x2 table.
    * ``unans_error``: all windows; an unanswered window is a disagreement whatever the rule says.  ``agree_pct`` =
      agreeing answered windows / all windows.  Kappa is undefined (NaN): a disagreement that is both a yes and a no.
    * ``rec``: answered windows plus unanswered windows with a recoverable verdict; the rest left out.
    * ``rec_error``: all windows; unanswered windows with a recoverable verdict use it, the rest are disagreements.
    Counts ``n_<variant>`` are the denominators.
    """
    clf = np.asarray(clf, dtype=bool)
    answered = np.asarray(answered, dtype=bool)
    ver = np.array([bool(v) if (a and v is not None and not pd.isna(v)) else False for v, a in zip(verdict, answered)])
    rec = np.full(len(clf), np.nan)
    if recoverable is not None:
        rec = np.array([np.nan if (v is None or pd.isna(v)) else float(bool(v)) for v in recoverable])
    has_rec = (~answered) & ~np.isnan(rec)
    out: Dict[str, Any] = {"n_windows": int(len(clf)), "n_unanswered": int((~answered).sum()),
                           "n_recoverable": int(has_rec.sum())}
    out.update(_record("answered", int(answered.sum()), *_cells(clf[answered], ver[answered])))
    out.update(_record("unans_no", len(clf), *_cells(clf, np.where(answered, ver, False))))
    tt, tf, ft, ff = _cells(clf[answered], ver[answered])
    out.update(_record("unans_error", len(clf), tt, tf, ft, ff, with_kappa=False))
    use = answered | has_rec
    both = np.where(answered, ver, rec == 1.0)
    out.update(_record("rec", int(use.sum()), *_cells(clf[use], both[use])))
    # recoverable-and-wrong windows are in the 2x2 above; unrecoverable ones are errors here
    tt, tf, ft, ff = _cells(clf[use], both[use])
    out.update(_record("rec_error", len(clf), tt, tf, ft, ff, with_kappa=False))
    return out


def agreement_table(final: pd.DataFrame, periods: Sequence[Tuple[str, Optional[int], Optional[int]]] = (("all", None, None),
                                                                                        ("2024-2025", 2024, 2025))
                    ) -> pd.DataFrame:
    """``agreement_variants`` per primary arm (and period) for the windows that have a stored rule verdict."""
    f = with_scan(final[(final["arm_role"] == "primary") & final["clf_should_detect"].notna()])
    f = f.assign(rec=recoverable_verdict(f))
    rows = []
    for (arm, model, series_key, symbol), g in f.groupby(["arm", "model", "series_key", "symbol"], sort=True):
        for period, first, last in periods:
            sub = g[in_years(g["window_end"], first, last)]
            if sub.empty:
                continue
            rec = {"arm": arm, "model": model, "series_key": series_key, "symbol": symbol, "period": period}
            rec.update(agreement_variants(sub["clf_should_detect"].astype(bool), sub["parsed"],
                                          sub["regime_detected"].astype("object"), sub["rec"].astype("object")))
            rows.append(rec)
    return round_frame(pd.DataFrame(rows).sort_values(["arm", "series_key", "symbol", "period"]).reset_index(drop=True))


# --------------------------------------------------------------------------- 5. contested windows
CONTESTED_DEFAULT = "pivotal"
# One definition for both papers: stored_analyses.contested_mask with the 'pivotal' margins (persistence within 1 day of
# 21 of 30, mean |GEX| within 0.5 billion of 5, flips 5 or 6) is the default; margin1 is the other definition of that module;
# narrow and wide only bracket the default in the sensitivity table.
CONTESTED_SETS = {**{name: dict(m) for name, m in sa.CONTESTED_DEFINITIONS.items()},
                  "narrow": {"days": 0, "billions": 0.5, "flips": 0, "flips_below": 0},
                  "wide": {"days": 3, "billions": 2.0, "flips": 2, "flips_below": 2}}


def contested_windows(frame: pd.DataFrame, definition: str = CONTESTED_DEFAULT) -> pd.DataFrame:
    """Which stored windows are contested, and by which criterion, by ``stored_analyses.contested_mask``.

    ``frame`` holds the stored windows' ``clf_positive_days``, ``clf_negative_days``, ``clf_avg_magnitude`` (USD) and
    ``clf_sign_flips``.  ``definition`` names a margin set of ``CONTESTED_SETS`` ('pivotal' by default: one day of the
    majority sign around 21, half a billion around 5, flips 5 or 6).  A window is contested when one criterion is within
    its margin of its threshold while the other two pass.  Returns ``contested`` and ``by_persistence`` / ``by_magnitude`` /
    ``by_flips`` (a window can be contested by more than one criterion); rows with a missing metric are not contested.
    """
    m = CONTESTED_SETS[definition]
    cols = ["clf_positive_days", "clf_negative_days", "clf_avg_magnitude", "clf_sign_flips"]
    known = frame[cols].notna().all(axis=1).to_numpy()
    out = sa.contested_mask(frame["clf_positive_days"].fillna(0).to_numpy(), frame["clf_negative_days"].fillna(0).to_numpy(),
                            frame["clf_avg_magnitude"].fillna(0).to_numpy(), frame["clf_sign_flips"].fillna(0).to_numpy(),
                            m["days"], m["billions"], m["flips"], m["flips_below"])
    out = out.mul(known, axis=0).astype(bool)
    out.index = frame.index
    return out


def contested_table(final: pd.DataFrame, definition: str = CONTESTED_DEFAULT) -> pd.DataFrame:
    """Agreement and answered share by stratum for every primary arm.

    ``stratum``: ``contested``, ``not_contested`` or ``all`` (windows with a rule verdict).  Columns: ``n_windows``,
    ``n_answered``, ``answered_pct``, ``n_rule_detect``, ``agree_pct_answered`` (agreeing / answered),
    ``agree_pct_unans_error`` (agreeing / all windows) and ``kappa_answered``.  The margins are those of
    ``contested_windows``.
    """
    f = final[(final["arm_role"] == "primary") & final["clf_should_detect"].notna()].copy()
    f = f.join(contested_windows(f, definition))
    rows = []
    for (arm, model, series_key, symbol), g in f.groupby(["arm", "model", "series_key", "symbol"], sort=True):
        strata = [("all", g), ("contested", g[g["contested"]]), ("not_contested", g[~g["contested"]])]
        strata += [(f"contested_{c}", g[g[f"by_{c}"]]) for c in ("persistence", "magnitude", "flips")]
        for name, sub in strata:
            if sub.empty:
                continue
            ans = sub[sub["parsed"]]
            clf = ans["clf_should_detect"].astype(bool).to_numpy()
            llm = ans["regime_detected"].astype(bool).to_numpy()
            tt, tf, ft, ff = _cells(clf, llm)
            rows.append({"arm": arm, "model": model, "series_key": series_key, "symbol": symbol, "stratum": name,
                         "n_windows": len(sub), "n_answered": len(ans), "answered_pct": pct(len(ans), len(sub)),
                         "n_rule_detect": int(sub["clf_should_detect"].astype(bool).sum()),
                         "agree_pct_answered": pct(tt + ff, len(ans)),
                         "agree_pct_unans_error": pct(tt + ff, len(sub)),
                         "kappa_answered": float(REPORT.binary_kappa(tt, tf, ft, ff)) if len(ans) else math.nan})
    return round_frame(pd.DataFrame(rows).sort_values(["arm", "series_key", "symbol", "stratum"]).reset_index(drop=True))


def contested_sensitivity(final: pd.DataFrame) -> pd.DataFrame:
    """The contested and not-contested strata of ``contested_table`` under every margin set of ``CONTESTED_SETS``
    (``margin_set``; the default is ``pivotal``), with the set's margins in days, billions and flips."""
    parts = []
    for name, m in CONTESTED_SETS.items():
        t = contested_table(final, name)
        parts.append(t[t["stratum"].isin(["contested", "not_contested"])].assign(
            margin_set=name, margin_days=m["days"], margin_billions=m["billions"], margin_flips_above=m["flips"],
            margin_flips_below=m["flips_below"], is_default=name == CONTESTED_DEFAULT))
    return pd.concat(parts, ignore_index=True).sort_values(["arm", "series_key", "symbol", "margin_set", "stratum"]
                                                           ).reset_index(drop=True)


# --------------------------------------------------------------------------- 6. predictors of non-response
BANDS = {
    "persistence_pct": ([0, 60, 70, 80, 90, 100.0001], ["<60", "60-<70", "70-<80", "80-<90", "90-100"]),
    "avg_magnitude_bn": ([0, 1, 3, 5, 10, 20, np.inf], ["<1", "1-<3", "3-<5", "5-<10", "10-<20", ">=20"]),
    "sign_flips": ([-1, 1, 3, 5, 7, 10, np.inf], ["0-1", "2-3", "4-5", "6-7", "8-10", ">=11"]),
}


def answering_bands(final: pd.DataFrame, model: str) -> pd.DataFrame:
    """Answered share by band of the rule's metrics, for the primary windows of ``model``.

    ``variable``: persistence_pct (``clf_persistence_pct``), avg_magnitude_bn (``clf_avg_magnitude``), sign_flips
    (``clf_sign_flips``), dominant_sign (positive when more positive than negative days), rule (the rule's verdict),
    contested (``contested_windows``, default definition).  ``scope``: ``all_primary_arms`` (every primary arm of
    the model; the same window appears in several arms) or ``full_spy`` (the complete-series arm).
    """
    f = final[(final["arm_role"] == "primary") & (final["model"] == model) & final["clf_should_detect"].notna()].copy()
    f["answered"] = f["parsed"]
    f["dominant_sign"] = np.where(f["clf_positive_days"] >= f["clf_negative_days"], "positive", "negative")
    f["rule"] = rule_label(f["clf_should_detect"])
    f["contested"] = np.where(contested_windows(f)["contested"], "contested", "not_contested")
    srcs = {"persistence_pct": "clf_persistence_pct", "avg_magnitude_bn": "clf_avg_magnitude", "sign_flips": "clf_sign_flips"}
    rows = []
    scopes = {"all_primary_arms": f, "full_spy": f[f["arm"].str.endswith("full_spy")]}
    for scope, g in scopes.items():
        if g.empty:
            continue
        for var, (edges, labels) in BANDS.items():
            band = pd.cut(g[srcs[var]], bins=edges, labels=labels, right=False)
            for label in labels:
                sub = g[band == label]
                if len(sub):
                    rows.append({"model": model, "scope": scope, "variable": var, "band": label, "n_windows": len(sub),
                                 "n_answered": int(sub["answered"].sum()), "answered_pct": pct(sub["answered"].sum(), len(sub)),
                                 "n_rule_detect": int(sub["clf_should_detect"].astype(bool).sum())})
        for var in ("dominant_sign", "rule", "contested"):
            for label, sub in g.groupby(var):
                rows.append({"model": model, "scope": scope, "variable": var, "band": label, "n_windows": len(sub),
                             "n_answered": int(sub["answered"].sum()), "answered_pct": pct(sub["answered"].sum(), len(sub)),
                             "n_rule_detect": int(sub["clf_should_detect"].astype(bool).sum())})
    return round_frame(pd.DataFrame(rows).sort_values(["scope", "variable", "band"]).reset_index(drop=True))


def logistic_fit(X: np.ndarray, y: np.ndarray, ridge: float = 1e-6, iters: int = 100) -> Tuple[np.ndarray, np.ndarray]:
    """Logistic regression by Newton steps (IRLS) with a tiny ridge on the slopes; returns (coefficients, standard
    errors from the inverse Hessian).  ``X`` includes the intercept column first."""
    beta = np.zeros(X.shape[1])
    pen = ridge * np.eye(X.shape[1])
    pen[0, 0] = 0.0
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        p = 1.0 / (1.0 + np.exp(-eta))
        w = p * (1 - p)
        grad = X.T @ (y - p) - pen @ beta
        hess = (X * w[:, None]).T @ X + pen
        step = np.linalg.solve(hess, grad)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    eta = np.clip(X @ beta, -30, 30)
    p = 1.0 / (1.0 + np.exp(-eta))
    cov = np.linalg.inv((X * (p * (1 - p))[:, None]).T @ X + pen)
    return beta, np.sqrt(np.diag(cov))


def auc(score: np.ndarray, y: np.ndarray) -> float:
    """Area under the ROC curve of ``score`` for the binary ``y`` (rank formula, ties averaged)."""
    ranks = pd.Series(score).rank(method="average").to_numpy()
    n1 = int((y == 1).sum())
    n0 = len(y) - n1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else math.nan


FEATURES = ("persistence_per_10pp", "log10_magnitude_bn", "sign_flips", "positive_dominant", "rule_detects")


def answering_logit(final: pd.DataFrame, model: str) -> pd.DataFrame:
    """Logistic fit of 'answered' (1) on the rule's metrics for the primary windows of ``model``.

    Predictors: persistence per 10 points, log10 of mean |GEX| in billions, sign flips, positive-dominant sign (1/0)
    and the rule's verdict (1 = detect).  Fitted on the complete-series arm (``full_spy``) and on all primary arms
    pooled.  The standard errors assume independent windows; the 30-day windows overlap at stride one and the pooled
    fit repeats windows across arms, so read them as indicative, not as tests.  Columns: ``coef``, ``se``,
    ``odds_ratio``, ``auc`` (in sample), ``n``, ``n_answered``.
    """
    f = final[(final["arm_role"] == "primary") & (final["model"] == model) & final["clf_should_detect"].notna()].copy()
    f = f[f["clf_avg_magnitude"] > 0]
    rows = []
    for scope, g in {"full_spy": f[f["arm"].str.endswith("full_spy")], "all_primary_arms": f}.items():
        if len(g) < 50 or g["parsed"].nunique() < 2:
            continue
        X = np.column_stack([np.ones(len(g)), g["clf_persistence_pct"] / 10.0, np.log10(g["clf_avg_magnitude"]),
                             g["clf_sign_flips"], (g["clf_positive_days"] >= g["clf_negative_days"]).astype(float),
                             g["clf_should_detect"].astype(bool).astype(float)])
        y = g["parsed"].astype(float).to_numpy()
        beta, se = logistic_fit(X, y)
        a = auc(X @ beta, y)
        for name, b, s in zip(("intercept",) + FEATURES, beta, se):
            rows.append({"model": model, "scope": scope, "term": name, "coef": b, "se": s,
                         "odds_ratio": math.exp(b) if abs(b) < 50 else math.nan, "auc": a, "n": len(g),
                         "n_answered": int(y.sum())})
    return round_frame(pd.DataFrame(rows))


# --------------------------------------------------------------------------- 7. repeats
def repeat_stability(final: pd.DataFrame) -> pd.DataFrame:
    """Windows run twice (arm '<arm>#rep1' against the original arm): answered in both, one or neither pass.

    Per model and base arm: ``n_repeated`` windows with a final row in both passes; ``n_both`` answered in both;
    ``n_original_only`` and ``n_repeat_only`` answered in one; ``n_neither``; ``n_one_pass_only`` their sum;
    ``n_same_verdict`` / ``agree_pct`` among the windows answered in both, and ``kappa`` of the two verdicts.
    """
    rep = final[final["repeat_index"] == 1]  # the same-job repeat; later-date repeats (#rep2 and up) are in drift_summary.csv
    orig = final[final["repeat_index"] == 0]
    cols = ["base_arm", "series_key", "symbol", "window_end", "model", "prompt_version"]
    keep = ["parsed", "regime_detected"]
    m = rep[cols + keep].merge(orig[cols + keep], on=cols, suffixes=("_rep", "_orig"))
    rows = []
    for (model, arm), g in m.groupby(["model", "base_arm"], sort=True):
        both = g[g["parsed_rep"] & g["parsed_orig"]]
        a = both["regime_detected_orig"].astype(bool).to_numpy()
        b = both["regime_detected_rep"].astype(bool).to_numpy()
        tt, tf, ft, ff = _cells(a, b)
        only_o = int((g["parsed_orig"] & ~g["parsed_rep"]).sum())
        only_r = int((~g["parsed_orig"] & g["parsed_rep"]).sum())
        rows.append({"model": model, "base_arm": arm, "n_repeated": len(g), "n_both": len(both),
                     "n_original_only": only_o, "n_repeat_only": only_r,
                     "n_neither": int((~g["parsed_orig"] & ~g["parsed_rep"]).sum()),
                     "n_one_pass_only": only_o + only_r, "n_same_verdict": tt + ff,
                     "agree_pct": pct(tt + ff, len(both)),
                     "kappa": float(REPORT.binary_kappa(tt, tf, ft, ff)) if len(both) else math.nan})
    out = pd.DataFrame(rows).sort_values(["model", "base_arm"]).reset_index(drop=True)
    return round_frame(out)


# --------------------------------------------------------------------------- 8. GPU time
def gpu_runs(runs: pd.DataFrame) -> pd.DataFrame:
    """One row per local run: model, run_id, gpu index, ``seconds`` (run_metadata.local.seconds), start and end."""
    out = []
    for r in runs.itertuples(index=False):
        local = (r.run_metadata or {}).get("local") if isinstance(r.run_metadata, Mapping) else None
        if not local:
            continue
        out.append({"model": r.model, "run_id": r.run_id, "gpu": (local.get("gpu") or {}).get("index"),
                    "seconds": float(local["seconds"]) if local.get("seconds") is not None else math.nan,
                    "started_at": pd.to_datetime(local.get("started_at"), utc=True),
                    "completed_at": pd.to_datetime(local.get("completed_at"), utc=True)})
    frame = pd.DataFrame(out)
    return frame.sort_values(["model", "started_at", "run_id"]).reset_index(drop=True) if len(frame) else frame


def _union_seconds(starts: Sequence[pd.Timestamp], ends: Sequence[pd.Timestamp]) -> float:
    spans = sorted(zip(starts, ends))
    total = 0.0
    cur_s, cur_e = None, None
    for s, e in spans:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return total


def _max_concurrent(starts: Sequence[pd.Timestamp], ends: Sequence[pd.Timestamp]) -> int:
    events = sorted([(s, 1) for s in starts] + [(e, -1) for e in ends], key=lambda x: (x[0], x[1]))
    cur = best = 0
    for _, d in events:
        cur += d
        best = max(best, cur)
    return best


def gpu_time_summary(local: pd.DataFrame) -> pd.DataFrame:
    """Per model: the sum of ``seconds`` over runs (the paper's GPU-hours), against the elapsed time.

    ``seconds_sum`` / ``hours_sum``: sum of run_metadata.local.seconds.  ``union_hours``: time covered by at least
    one run (overlaps counted once); ``span_hours``: first start to last end.  ``max_concurrent``: most runs active at
    once; ``gpu_busy_hours``: per GPU index the time covered by at least one run, summed over GPUs (device occupancy
    by this model); ``max_engines_per_gpu``: most runs of the model active on one GPU index at once;
    ``n_same_gpu_overlaps``: pairs of runs of the model on the same GPU index whose intervals overlap (more than zero:
    several engines shared a device, so ``seconds_sum`` is engine wall-clock and exceeds both the elapsed time and the
    device-busy time; runs on different GPUs also ran at the same time).  ``seconds_vs_interval_max_abs``: largest gap between ``seconds`` and completed minus started.
    """
    rows = []
    for model, g in local.groupby("model", sort=True):
        s, e = list(g["started_at"]), list(g["completed_at"])
        overlaps = 0
        busy = 0.0
        max_per_gpu = 0
        for _, gg in g.dropna(subset=["gpu"]).groupby("gpu"):
            busy += _union_seconds(list(gg["started_at"]), list(gg["completed_at"]))
            max_per_gpu = max(max_per_gpu, _max_concurrent(list(gg["started_at"]), list(gg["completed_at"])))
            gs = sorted(zip(gg["started_at"], gg["completed_at"]))
            for i in range(len(gs)):
                for j in range(i + 1, len(gs)):
                    if gs[j][0] < gs[i][1]:
                        overlaps += 1
        interval = (g["completed_at"] - g["started_at"]).dt.total_seconds()
        rows.append({"model": model, "n_runs": len(g), "n_gpus": int(g["gpu"].nunique()),
                     "seconds_sum": float(g["seconds"].sum()), "hours_sum": float(g["seconds"].sum()) / 3600.0,
                     "union_hours": _union_seconds(s, e) / 3600.0, "gpu_busy_hours": busy / 3600.0,
                     "max_engines_per_gpu": max_per_gpu,
                     "span_hours": (max(e) - min(s)).total_seconds() / 3600.0,
                     "max_concurrent": _max_concurrent(s, e), "n_same_gpu_overlaps": overlaps,
                     "seconds_vs_interval_max_abs": float((g["seconds"] - interval).abs().max())})
    return round_frame(pd.DataFrame(rows).reset_index(drop=True), 3)


# --------------------------------------------------------------------------- writers and runner
def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_all(parquet_root: Path, results_dir: Path, focus_models: Sequence[str]) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Compute every table without writing: (name -> frame, summary).  Names are the file names ``run_all`` writes.

    ``results_dir`` supplies llm_parse_stats.csv and missing_answer_bounds.csv, which the census and the bounds reconcile
    with.  The summary holds no paths, clocks or other run-specific values, so it is the same on every run.
    """
    frames: Dict[str, pd.DataFrame] = {}
    rows, runs, _windows = read_all_answer_rows(parquet_root)
    final = rows[rows["is_final"]].reset_index(drop=True)
    summary: Dict[str, Any] = {"n_answer_rows": int(len(rows)), "n_final_rows": int(len(final)),
                               "final_rows_check": check_final_rows(rows, parquet_root)}
    frames["census_unanswered.csv"] = round_frame(census(final))
    parse_stats = pd.read_csv(results_dir / "llm_parse_stats.csv")
    bounds_stored = pd.read_csv(results_dir / "missing_answer_bounds.csv")
    summary["reconciliation"] = reconcile_with_results(final, parse_stats, bounds_stored)
    frames["recoverable_verdicts.csv"] = recoverable_table(rows)
    summary["scanner_on_answered_rows"] = scanner_check_on_answered(rows)
    frames["recoverable_first_pass_vs_retry.csv"] = retry_stability_of_cut_verdicts(rows)
    bwr = bounds_with_recoverable(final)
    frames["bounds_with_recoverable.csv"] = bwr
    cmp_cols = ["arm", "model", "series_key", "symbol", "period"]
    chk = bwr.merge(bounds_stored[cmp_cols + ["n_windows", "n_parsed", "n_unparsed", "lower_pct", "upper_pct"]], on=cmp_cols,
                    how="outer", suffixes=("", "_stored"), indicator=True)
    summary["bounds_reconciliation"] = {
        "rows_here": int(len(bwr)), "rows_stored": int(len(bounds_stored)),
        "unmatched": int((chk["_merge"] != "both").sum()),
        "max_abs_diff_lower_pct": float((chk["lower_pct"] - chk["lower_pct_stored"]).abs().max()),
        "max_abs_diff_upper_pct": float((chk["upper_pct"] - chk["upper_pct_stored"]).abs().max()),
        "count_mismatch": int(((chk["n_windows"] != chk["n_windows_stored"]) | (chk["n_parsed"] != chk["n_parsed_stored"])
                               | (chk["n_unparsed"] != chk["n_unparsed_stored"])).sum())}
    frames["agreement_variants.csv"] = agreement_table(final)
    frames["contested_agreement.csv"] = contested_table(final)
    frames["contested_sensitivity.csv"] = contested_sensitivity(final)
    bands, logits = [], []
    for model in focus_models:
        bands.append(answering_bands(final, model))
        logits.append(answering_logit(final, model))
    frames["answering_bands.csv"] = pd.concat(bands, ignore_index=True)
    frames["answering_logit.csv"] = pd.concat(logits, ignore_index=True)
    frames["repeat_stability.csv"] = repeat_stability(final)
    local = gpu_runs(runs)
    frames["gpu_time.csv"] = gpu_time_summary(local)
    frames["gpu_time_runs.csv"] = round_frame(local.assign(started_at=local["started_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                           completed_at=local["completed_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")), 1)
    summary["files"] = sorted(frames)
    return frames, summary


def run_all(parquet_root: Path, results_dir: Path, out: Path, focus_models: Sequence[str]) -> Dict[str, Any]:
    """Compute every table, write the files to ``out`` and return the summary (also written as summary.yaml)."""
    out.mkdir(parents=True, exist_ok=True)
    frames, summary = compute_all(parquet_root, results_dir, focus_models)
    for name, frame in frames.items():
        write_csv(frame, out / name)
    summary = {"parquet_root": str(parquet_root), **summary}
    with open(out / "summary.yaml", "w") as fh:
        yaml.safe_dump(json.loads(json.dumps(summary, default=str)), fh, sort_keys=True)
    return summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--parquet-root", type=Path, required=True, help="data/backups/gex_llm/tables")
    ap.add_argument("--out", type=Path, required=True, help="directory for the CSV and YAML files")
    ap.add_argument("--results-dir", type=Path, default=HERE.parents[2] / "docs" / "papers" / "electronics" / "results",
                    help="stored results (llm_parse_stats.csv, missing_answer_bounds.csv) to reconcile with")
    ap.add_argument("--focus-models", nargs="+", default=["qwen3-8b"], help="models for the predictor tables")
    args = ap.parse_args(argv)
    summary = run_all(args.parquet_root, args.results_dir, args.out, args.focus_models)
    print(yaml.safe_dump({k: summary[k] for k in ("n_answer_rows", "n_final_rows", "final_rows_check")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
