#!/usr/bin/env python3
"""Paper tables for the Electronics extension (gex-llm-patterns issue #261).

Reads the four result tables of the pipeline (``backups.gex_llm_regime_series``, ``_windows``,
``_detections`` and ``_runs``) from Postgres or from their parquet copies and writes every number
the manuscript quotes to ``docs/papers/electronics/results/``.  Nothing is written to Postgres and
nothing is invented: a section whose inputs are absent is skipped with a warning, and the output
files of an earlier run for that section are removed, so a full run never mixes fresh and old
numbers.  With ``--only`` the files of the sections that are not rerun stay on disk; report.yaml
lists each of them under ``files`` as ``carried_over`` with its sha256, size and modification time, a
``stale`` flag and ``stale_reasons`` (the result tables, 05_report.py, common.py, the seed or the file
itself changed since it was written, or the previous report.yaml does not list it), and any other file of
the results folder under ``untracked_files``.  Any subset of series, arms and tables is accepted.

Usage (repository root, AutoGex env)::

    source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
    PYTHONPATH=$(pwd) python scripts/validation/electronics/05_report.py            # auto: DB if the tables exist
    PYTHONPATH=$(pwd) python scripts/validation/electronics/05_report.py --source parquet
    PYTHONPATH=$(pwd) python scripts/validation/electronics/05_report.py --only stats cost_ledger
    PYTHONPATH=$(pwd) python scripts/validation/electronics/05_report.py --check-conventions   # repeat labels vs the contract and 04

Exit status: 0 = at least one section was written and none failed; 1 = a section failed; 2 = nothing was produced: no
section wrote a file (empty tables, or every requested section was skipped for want of inputs), or the tables could not be
opened at all (a ``--parquet-root`` that does not exist, an unreadable parquet file, ``--source db`` without the four
tables), which stops at once with a message (``InputError``, a SystemExit).

Outputs (CSV rows are sorted; for fixed inputs every file but ``report.yaml`` is byte-identical).  The LONG schemas
below are authoritative (the figure scripts read them; the spec's wide shapes are derived copies)::

    detection_by_year.csv       LONG table, one row per classifier (series_key, symbol, year) and per LLM (arm, model,
                                series_key, symbol, year), plus the 'all'-years rows.  Columns: label_source (classifier |
                                llm), arm, arm_role (primary | backfill | backfill_all | repeat | pilot | other), model,
                                series_key, symbol, scope (year | all), year, n_windows, n_parsed, n (the rate base: windows
                                for the classifier, parsed answers for an LLM), n_detect, rate_pct, ci_lo_pct, ci_hi_pct
                                (Wilson 95%, percent), n_indep_30d, mean_abs_gex_bn, n_compared (answers with a stored
                                window), clf_rate_matched_pct, clf_mean_abs_gex_bn_matched, agree_pct and kappa (against the
                                classifier on those windows), metrics_agree_pct, sign_flips_exact_pct,
                                median_ratio_reported_to_computed.
    detection_by_year_wide.csv  derived copy of the yearly rows in the shape of the written spec (no figure reads it):
                                series_key, symbol, year, n, clf_rate, clf_ci_lo, clf_ci_hi, arm, model, n_parsed,
                                llm_rate, llm_ci_lo, llm_ci_hi, agree_pct, kappa, arm_role, n_windows, n_compared,
                                clf_rate_matched, n_indep_30d.  Rates are FRACTIONS in [0, 1]; a classifier row has an
                                empty arm; an LLM row repeats the classifier columns of the windows it scored.
    bridge_agreement.csv/yaml   published o4-mini answers (a registered arm with llm=False) against every gpt-6-luna arm that
                                read the same series: r1_o4mini vs bridge_jan on jan2026_phase4a (the gate), r1_p3_o4mini /
                                r1_p4_o4mini vs the dated p34_* arms.  Columns: comparison (bridge = published answers;
                                bridge_incl_recovered = reference <arm>_all with the recovered answers; test_retest = an arm
                                against its own '#rep<k>' repeats), ref_arm, ref_model, other_arm, other_model, series_key,
                                symbol, scope, year, n_pairs, n_ref_det_oth_det, n_ref_det_oth_not, n_ref_not_oth_det,
                                n_ref_not_oth_not (2x2 counts of regime_detected), agree_pct, agree_ci_lo_pct, agree_ci_hi_pct,
                                agree_boot_lo_pct, agree_boot_hi_pct, kappa, kappa_boot_lo, kappa_boot_hi, type_agree_pct,
                                n_disagree_with_clf, n_disagree_ref_matches_clf, n_disagree_other_matches_clf, rate_ref_pct,
                                rate_other_pct, rate_diff_pp, rate_diff_boot_lo_pp, rate_diff_boot_hi_pp, p_mcnemar_exact,
                                p_boot, ref_clf_agree_pct, other_clf_agree_pct, median_ratio_ref, median_ratio_other, then
                                n, both_detect, only_r1, only_luna, neither (the spec's names for the same counts).  The
                                yaml adds the gate (met = null when kappa is undefined) and the confusion matrices.
    series_comparison.csv       per series pair, symbol and year: series_a, series_b, pair ('<a>_vs_<b>'), symbol, scope,
                                year, n_days, first_date, last_date, mean_abs_a_bn, mean_abs_b_bn, mean_abs_diff_bn,
                                median_ratio_a_over_b, sign_agree_pct, exact_match_pct
    ex0dte_decomposition.csv    per (symbol, year): new_full vs new_ex0dte rates and the share of |gex_0dte| in |net|
    post_publication_2026.csv   per-window classifier and LLM labels for window_end >= 2026-01-01, with window_start and
                                entirely_2026 (window_start >= 2026-01-01)
    post_publication_2026_summary.csv
                                rates (classifier and every LLM label) per series and symbol under both definitions of the
                                period.  Columns: definition (ends_in_2026 = window_end on or after 2026-01-01 | entirely_2026
                                = window_start too), series_key, symbol, label_source, arm, model, n_windows, n_scored,
                                n_detect, rate_pct, ci_lo_pct, ci_hi_pct, agree_with_clf_pct (LLM rows), window_end_first,
                                window_end_last, mean_abs_gex_bn
    intraday.csv                intraday_t0 vs new_full windows on the same window_end
    disagreements.csv           every parsed answer whose regime_detected differs from the classifier on its window
    llm_parse_stats.csv         parse_status and finish_reason counts, answers rerun at the retry cap, token use per arm
    reported_vs_computed.csv    model-reported mean |GEX| over the computed one (the classifier's), only where the computed mean
                                is positive.  Columns: basis (arm = all parsed answers of an arm | bridge_pairs = the windows
                                both raters of a bridge comparison answered, one row per rater), comparison, rater (reference |
                                other), ref_arm, arm, arm_role, model, series_key, symbol, scope, year, n, median_ratio,
                                q25_ratio, q75_ratio, ratio_within_5pct_pct, median_abs_diff_bn, median_reported_bn,
                                median_computed_bn
    stats.yaml                  overlap-aware inference: rates per label source and period, series / label / scale contrasts,
                                period shifts, Phase 3 vs Phase 4, and headline_contrasts (the ones the text quotes)
    cost_ledger.csv/yaml        per run, arm and model, reconciled with per-request token usage; budget counts only runs for
                                which common.counts_toward_budget holds, the backfills are listed apart (not_spend)
    report.yaml                 row counts, data provenance (inputs_fingerprint, per-file produced_with), warnings, caveats,
                                diagnostics and headline numbers

Conventions
-----------
* The primary label is ``regime_detected`` (LLM) / ``clf_should_detect`` (deterministic classifier).
  A year is the year of ``window_end``.  Rates are percentages of parsed windows.
* Windows have stride 1, so consecutive windows share 29 of 30 days.  Wilson intervals treat windows as
  independent and are therefore too narrow; ``n_indep_30d`` (non-overlapping 30-day windows) shows how many
  independent observations back a rate.  ``stats.yaml`` adds a calendar-quarter block bootstrap
  (2,000 draws, seed 261) and a non-overlapping 30-day subsample next to every p-value.
* The published result is arm ``r1_o4mini`` WITHOUT the answers flagged ``detection_metadata.recovered_2026``
  (``WHERE detection_metadata ->> 'recovered_2026' IS NULL``): 1,412 windows, 12.2 / 3.7 / 32.4 / 20.2 / 100 / 100
  percent by year 2020-2025.  Those rates, the bridge gate and ``stats.yaml`` use that subset; the cost ledger and
  the parse statistics cover every stored row; ``r1_o4mini_all`` (all 1,476 windows) and ``bridge_incl_recovered``
  show the effect of the 64 recovered answers.  The backfills ``r1_p3_o4mini`` and ``r1_p4_o4mini`` (o4-mini on the
  dated Nov-2025 prompts) follow the same rule: an ``_all`` variant exists when some of their rows carry the flag.
* Windows of an arm are read from ``common.arm_window_series(arm)`` (arm ``intraday_spy`` reads series
  ``intraday_late`` and is scored on the composite ``intraday_t0`` windows) while detections keep
  ``series_key = arm.series_key``.
* Repeats (test-retest) are stored by 04_llm_runner.py as arm ``<arm>#rep1`` with a custom_id ending in ``#rep1``
  (``common.REPEAT_ARM_SUFFIX``, ``common.custom_id(..., repeat=1)``); this report reads them with ``common.base_arm`` and
  ``common.custom_id_repeat`` and compares a repeat only with its original arm (``comparison = test_retest``).  The
  detections UNIQUE key has no repeat index.
* ``call_only`` is derived in memory from ``new_full.call_gex`` when the series table has no such series.
* Spend (cost_ledger.*) counts only runs for which ``common.counts_toward_budget`` holds; the January o4-mini
  backfill is reported as ``budget.not_spend.historical_backfill_usd``, never as spend.  ``headline.cost.est_cost_usd`` is the
  spend.
* The 2026 windows are called the post-publication period, not out-of-sample: the model object was
  created on 2026-09-14.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import logging
import math
import os
import platform
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy
import yaml
from scipy import stats as sps

import common

logger = logging.getLogger("electronics.report")

# --------------------------------------------------------------------------- constants
SEED = 261
N_BOOT = 2000
CI_LEVEL = 0.95
Z95 = float(sps.norm.ppf(0.975))
EXACT_MATCH_TOL_USD = 0.006e9  # |difference| <= $6M counts as the same value (January inputs carry 0.01B precision)
# Repeats (test-retest): a repeated request is stored under arm '<arm>#rep<k>' (common.REPEAT_ARM_SUFFIX
# for k = 1) with a custom_id ending '#rep<k>' (a bare trailing '#rep' counts as k = 1).  04_llm_runner.py writes them; this
# report reads them only through common.base_arm and common.custom_id_repeat, so there is one definition of the spelling.
# ``--check-conventions`` probes the helpers and, when it exports the names, the runner.
REPEAT_MARK = common.REPEAT_MARK
RECOVERED_FLAG = "recovered_2026"  # detection_metadata key written by 03_backfill_round1.py
ALL_SUFFIX = "_all"  # arm r1_o4mini_all = the backfill arm with the recovered windows included
POST_PUBLICATION_START = pd.Timestamp("2026-01-01")
BRIDGE_SERIES = "jan2026_phase4a"
BRIDGE_REFERENCE_ARM = "r1_o4mini"
BRIDGE_GATE_MIN_KAPPA = 0.6  # planning/00_design.md section 5: kappa(luna, o4-mini) on the published inputs
# Published o4-mini results (registered arms with llm=False) and the series whose prompts they answered: r1_o4mini on the
# January Phase 4A inputs, r1_p3_o4mini / r1_p4_o4mini on the dated Nov-2025 inputs.  Each is compared with the gpt-6-luna
# arms that read the same series (identical prompts) in bridge_agreement; only BRIDGE_REFERENCE_ARM feeds the gate.
BACKFILL_ARMS = tuple(arm.key for arm in common.ARMS.values() if not arm.llm)
BRIDGE_REFERENCES = tuple((arm.key, arm.series_key) for arm in common.ARMS.values() if not arm.llm)
CALL_ONLY = "call_only"
ZERO_DTE_SERIES = "new_ex0dte"
FULL_SERIES = "new_full"
INTRADAY_COMPOSITE = common.INTRADAY_T0_KEY
WINDOW_SERIES_ALIAS = {"intraday_late": INTRADAY_COMPOSITE}  # detections of these series are joined to these windows
OK_PARSE = ("ok", "fallback")

SERIES_ORDER = [BRIDGE_SERIES, "old_bs", FULL_SERIES, ZERO_DTE_SERIES, "intraday_late", INTRADAY_COMPOSITE, CALL_ONLY]
SERIES_ORDER += [key for key in common.SERIES if key not in SERIES_ORDER]  # new_full_scaled, p3_2024*, p4_2020*, ...
ARM_ORDER = list(common.ARMS)
SERIES_PAIRS = (  # (a, b): per-day comparison of the values shown to the model
    (BRIDGE_SERIES, FULL_SERIES),
    (CALL_ONLY, BRIDGE_SERIES),
    (FULL_SERIES, ZERO_DTE_SERIES),
    ("old_bs", FULL_SERIES),
    ("old_bs", BRIDGE_SERIES),
)

PERIODS = (("2024", 2024, 2024), ("2025", 2025, 2025), ("2020-2023", 2020, 2023), ("2024-2025", 2024, 2025),
           ("2008-2019", 2008, 2019), ("2026", 2026, 2026), ("all", None, None))  # (name, first year, last year); None = unbounded
SERIES_CONTRAST_PERIODS = ("2024", "2025", "2024-2025", "2008-2019", "2020-2023", "2026")
# (series a, series b, family, periods): rate of a minus rate of b on the windows both series have, per label source.
#   series : data lineage (published inputs vs rebuilt series, 0DTE removed, archive);
#   label  : the Nov-2025 values with Day-T labels (a) against the same values with the ISO dates that were sent (b);
#   scale  : the QQQ/IWM series multiplied by the open-interest-notional factor (a) against the stored values (b).
SERIES_CONTRASTS = (
    (BRIDGE_SERIES, FULL_SERIES, "series", SERIES_CONTRAST_PERIODS),
    (FULL_SERIES, ZERO_DTE_SERIES, "series", SERIES_CONTRAST_PERIODS),
    ("old_bs", FULL_SERIES, "series", SERIES_CONTRAST_PERIODS),
    ("p3_2024", "p3_2024_dated", "label", ("all",)),
    ("p4_2020", "p4_2020_dated", "label", ("all",)),
    ("new_full_scaled", FULL_SERIES, "scale", ("all",)),
)
# (later series, earlier series): Phase 3 (2024) against Phase 4 (2020), unpaired, per label source and, for a model, per model.
PHASE_CONTRASTS = (("p3_2024_dated", "p4_2020_dated"), ("p3_2024", "p4_2020"))
SHIFT_EARLY, SHIFT_LATE = "2020-2023", "2024-2025"

# --------------------------------------------------------------------------- table schema
_STR, _DAY, _TS, _NUM, _BOOL, _JSON = "str", "day", "ts", "num", "bool", "json"
KINDS = ("series", "windows", "detections", "runs")
DB_TABLES = {"series": common.T_SERIES, "windows": common.T_WINDOWS,
             "detections": common.T_DETECTIONS, "runs": common.T_RUNS}

# Columns the report reads (a subset of gex_llm_regime_schema.sql).  The large payload columns (gex_sequence, reasoning,
# raw_response, detection_metadata) are never loaded; the small per-row JSON documents (series_metadata, window_metadata,
# run_metadata) are read as mappings, and detection_metadata only as the boolean flag of JSON_FLAGS.
TABLE_SCHEMA: Dict[str, Dict[str, str]] = {
    "series": {
        "series_key": _STR, "symbol": _STR, "trading_date": _DAY, "net_gex": _NUM, "call_gex": _NUM,
        "put_gex": _NUM, "gex_0dte": _NUM, "n_contracts": _NUM, "n_0dte": _NUM, "spot": _NUM,
        "source_table": _STR, "series_metadata": _JSON, "created_at": _TS,
    },
    "windows": {
        "series_key": _STR, "symbol": _STR, "window_end": _DAY, "window_start": _DAY, "window_rule": _STR,
        "clf_regime_type": _STR, "clf_should_detect": _BOOL, "clf_positive_days": _NUM,
        "clf_negative_days": _NUM, "clf_persistence_pct": _NUM, "clf_avg_magnitude": _NUM,
        "clf_sign_flips": _NUM, "clf_version": _STR, "window_metadata": _JSON, "created_at": _TS,
    },
    "detections": {
        "run_id": _STR, "arm": _STR, "series_key": _STR, "symbol": _STR, "window_end": _DAY, "model": _STR,
        "prompt_version": _STR, "custom_id": _STR, "regime_detected": _BOOL, "regime_type": _STR,
        "confidence": _NUM, "positive_days": _NUM, "negative_days": _NUM, "avg_magnitude_billions": _NUM,
        "sign_flips": _NUM, "persistence_pct": _NUM, "metrics_agree": _BOOL, "parse_status": _STR,
        "finish_reason": _STR, "prompt_tokens": _NUM, "completion_tokens": _NUM, "reasoning_tokens": _NUM,
        "recovered_2026": _BOOL, "created_at": _TS,
    },
    "runs": {
        "run_id": _STR, "arm": _STR, "series_key": _STR, "symbol": _STR, "model": _STR,
        "model_created_at": _TS, "prompt_version": _STR, "reasoning_effort": _STR, "response_format": _STR,
        "max_completion_tokens": _NUM, "mode": _STR, "openai_batch_id": _STR, "window_end_min": _DAY, "window_end_max": _DAY,
        "n_requests": _NUM, "n_responses": _NUM, "n_parsed": _NUM, "n_failed": _NUM, "prompt_tokens": _NUM,
        "completion_tokens": _NUM, "reasoning_tokens": _NUM, "est_cost_usd": _NUM, "status": _STR,
        "submitted_at": _TS, "completed_at": _TS, "ingested_at": _TS, "git_sha": _STR, "run_metadata": _JSON,
        "created_at": _TS,
    },
}
REQUIRED_COLUMNS = {
    "series": ("series_key", "symbol", "trading_date", "net_gex"),
    "windows": ("series_key", "symbol", "window_end", "window_start", "clf_should_detect"),
    "detections": ("arm", "series_key", "symbol", "window_end", "model", "regime_detected", "parse_status"),
    "runs": ("run_id", "arm"),
}
NATURAL_KEYS = {
    "series": ["series_key", "symbol", "trading_date"],
    "windows": ["series_key", "symbol", "window_end"],
    "detections": ["arm", "series_key", "symbol", "window_end", "model", "prompt_version"],
    "runs": ["run_id"],
}
# Boolean columns taken from a key of a JSON column while reading (the JSON document itself is never kept):
# table -> {column: (JSON column, key)}.  detection_metadata carries {"recovered_2026": true} on the 64 January answers
# that only 03_backfill_round1.py could read; they are not part of the published result.  In Postgres only the key is
# fetched (``detection_metadata ->> 'recovered_2026'``); in parquet the column holds the JSON text.
JSON_FLAGS: Dict[str, Dict[str, Tuple[str, str]]] = {
    "detections": {"recovered_2026": ("detection_metadata", RECOVERED_FLAG)},
}


# --------------------------------------------------------------------------- statistics
def wilson_interval(k, n, z: float = Z95) -> Tuple[np.ndarray, np.ndarray]:
    """Wilson score interval for k successes in n trials, as fractions (arrays or scalars; NaN where n == 0)."""
    k = np.asarray(k, dtype=float)
    n = np.asarray(n, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = k / n
        denom = 1.0 + z * z / n
        centre = (p + z * z / (2.0 * n)) / denom
        half = z * np.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    lo = np.where(n > 0, np.clip(centre - half, 0.0, 1.0), np.nan)
    hi = np.where(n > 0, np.clip(centre + half, 0.0, 1.0), np.nan)
    return lo, hi


def wilson_pct(k: int, n: int) -> Tuple[float, float]:
    """Wilson interval in percent for scalar counts."""
    lo, hi = wilson_interval(k, n)
    return float(100.0 * lo), float(100.0 * hi)


def rate_fields(k: int, n: int) -> Dict[str, float]:
    """n, detections, rate and Wilson 95% interval (percent) of a binary outcome."""
    lo, hi = wilson_pct(k, n)
    return {"n": n, "n_detect": k, "rate_pct": 100.0 * k / n if n else math.nan, "ci_lo_pct": lo, "ci_hi_pct": hi}


def binary_kappa(tt, tf, ft, ff) -> np.ndarray:
    """Cohen's kappa from the cells of a 2x2 table (scalars or arrays); NaN when n == 0 or chance agreement is 1."""
    tt, tf, ft, ff = (np.asarray(x, dtype=float) for x in (tt, tf, ft, ff))
    n = tt + tf + ft + ff
    with np.errstate(divide="ignore", invalid="ignore"):
        observed = (tt + ff) / n
        chance = ((tt + tf) * (tt + ft) + (ft + ff) * (tf + ff)) / (n * n)
        kappa = (observed - chance) / (1.0 - chance)
    return np.where((n > 0) & (chance < 1.0), kappa, np.nan)


def confusion_counts(a, b) -> Tuple[int, int, int, int]:
    """(both true, a only, b only, both false) of two boolean vectors."""
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    return int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum()), int((~a & ~b).sum())


def mcnemar_exact(only_a: int, only_b: int) -> float:
    """Exact two-sided McNemar p-value from the two discordant counts."""
    discordant = only_a + only_b
    return 1.0 if discordant == 0 else float(sps.binomtest(min(only_a, only_b), discordant, 0.5).pvalue)


def fisher_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided Fisher exact p-value for k1/n1 vs k2/n2."""
    return float(sps.fisher_exact([[k1, n1 - k1], [k2, n2 - k2]])[1])


def phi_coefficient(k1: int, n1: int, k2: int, n2: int) -> float:
    """Signed phi of the 2x2 table (group 1, group 2) x (detected, not detected)."""
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    margin = (a + b) * (c + d) * (a + c) * (b + d)
    return float((a * d - b * c) / math.sqrt(margin)) if margin > 0 else math.nan


def newcombe_difference(k1: int, n1: int, k2: int, n2: int) -> Tuple[float, float]:
    """Newcombe-Wilson hybrid interval (percentage points) for p1 - p2 of two independent proportions."""
    l1, u1 = (float(x) for x in wilson_interval(k1, n1))
    l2, u2 = (float(x) for x in wilson_interval(k2, n2))
    p1, p2 = k1 / n1, k2 / n2
    diff = p1 - p2
    return (100.0 * (diff - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)),
            100.0 * (diff + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)))


def quarter_ids(dates: pd.Series) -> np.ndarray:
    """Calendar-quarter index of each date (the resampling block of the bootstrap)."""
    return (dates.dt.year * 4 + (dates.dt.month - 1) // 3).to_numpy()


def block_sums(frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    """Per-quarter sums of ``columns`` (one row per quarter present in ``frame['window_end']``)."""
    return frame[list(columns)].astype(float).groupby(quarter_ids(frame["window_end"])).sum().to_numpy()


def resample_block_sums(blocks: np.ndarray, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    """``n_boot`` bootstrap sums of the block matrix: as many blocks as there are, drawn with replacement."""
    n_blocks = blocks.shape[0]
    idx = rng.integers(0, n_blocks, size=(n_boot, n_blocks))
    return blocks[idx].sum(axis=1)


def percentile_interval(draws: np.ndarray) -> Tuple[float, float]:
    finite = draws[np.isfinite(draws)]
    if finite.size == 0:
        return math.nan, math.nan
    lo, hi = np.percentile(finite, [50.0 * (1.0 - CI_LEVEL), 50.0 * (1.0 + CI_LEVEL)])
    return float(lo), float(hi)


def bootstrap_p_value(draws: np.ndarray) -> float:
    """Two-sided percentile-bootstrap p-value for H0: difference = 0, bounded below by 1 / (draws + 1)."""
    finite = draws[np.isfinite(draws)]
    if finite.size == 0:
        return math.nan
    p = 2.0 * min(float((finite <= 0).mean()), float((finite >= 0).mean()))
    return min(1.0, max(p, 1.0 / (finite.size + 1)))


def nonoverlap_indices(starts: np.ndarray, ends: np.ndarray, first: int = 0) -> np.ndarray:
    """Greedy chain of windows (ordered by end) that share no day, beginning at position ``first``."""
    chosen = [first]
    last_end = ends[first]
    for i in range(first + 1, len(ends)):
        if starts[i] > last_end:
            chosen.append(i)
            last_end = ends[i]
    return np.asarray(chosen)


def independent_count(frame: pd.DataFrame) -> float:
    """Number of non-overlapping 30-day windows in ``frame`` (columns window_start, window_end); NaN if unknown."""
    f = frame[["window_start", "window_end"]].dropna().sort_values("window_end")
    if f.empty:
        return math.nan
    chain = nonoverlap_indices(f["window_start"].to_numpy("datetime64[D]"), f["window_end"].to_numpy("datetime64[D]"))
    return float(len(chain))


# --------------------------------------------------------------------------- loading
@dataclass
class Data:
    """The four tables (typed, de-duplicated; detections enriched) plus where they came from."""

    series: pd.DataFrame
    windows: pd.DataFrame
    detections: pd.DataFrame
    runs: pd.DataFrame
    source: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)


class InputError(SystemExit):
    """The tables cannot be read at all (a --parquet-root that does not exist, an unreadable parquet file, ``--source db``
    without the four tables).  A SystemExit with exit status 2 ("nothing produced"); ``main`` prints the message."""

    def __init__(self, message: str):
        super().__init__(2)
        self.message = message

    def __str__(self) -> str:
        return self.message


def note(sink: List[str], message: str) -> None:
    """Log a warning and keep it for report.yaml."""
    logger.warning(message)
    sink.append(message)


def truthy(value: Any) -> bool:
    """True for a true JSON/SQL flag: a boolean, or the text 'true' (any case); null and anything else are False."""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return isinstance(value, str) and value.strip().lower() in ("true", "t")


def as_mapping(value: Any) -> Dict[str, Any]:
    """The JSON object in ``value`` (a dict from a jsonb column, or the JSON text/bytes of a parquet copy); {} when the
    value is absent, null, not an object or unreadable."""
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value).decode("utf-8", "replace")
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
        except ValueError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    return {}


def json_flag(value: Any, key: str) -> bool:
    """``key`` of a JSON object (text, bytes or mapping) is true; absent, null, empty or unreadable JSON is False."""
    return truthy(as_mapping(value).get(key))


def derived_flag(raw: pd.DataFrame, column: str, source: str, key: str) -> pd.Series:
    """Flag column from a column that already holds it (the SQL ``->>`` result), else from the JSON column ``source``."""
    if column in raw.columns:
        values = raw[column].map(truthy)
    elif source in raw.columns:
        values = raw[source].map(lambda v: json_flag(v, key))
    else:
        values = pd.Series(False, index=raw.index)
    return values.astype(bool)


def read_parquet_tables(root: Path) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """Concatenate every parquet file under ``root/<kind>/`` (only the columns the report reads)."""
    if not root.is_dir():
        raise InputError(f"parquet root {root} does not exist or is not a directory (--parquet-root); "
                         f"01-04 write the table copies under {common.PARQUET_ROOT}")
    raw: Dict[str, pd.DataFrame] = {}
    files: List[Dict[str, Any]] = []
    for kind in KINDS:
        frames = []
        sources = {source for source, _ in JSON_FLAGS.get(kind, {}).values()}
        for path in sorted((root / kind).rglob("*.parquet")):
            try:  # a file that is half-written (a run being ingested) or corrupt stops the report; it is never skipped silently
                wanted = [c for c in pq.read_schema(path).names if c in TABLE_SCHEMA[kind] or c in sources]
                frame = pd.read_parquet(path, columns=wanted)
            except Exception as exc:
                raise InputError(f"cannot read {path}: {type(exc).__name__}: {exc}") from exc
            files.append({"kind": kind, "path": str(path), "rows": int(len(frame)), "sha256": common.sha256_file(path)})
            if len(frame):
                frames.append(frame)
        raw[kind] = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    if not files:
        logger.warning("no parquet file under %s/{%s}: every section will be skipped", root, ",".join(KINDS))
    return raw, {"kind": "parquet", "parquet_root": str(root), "files": files}


def db_tables_exist(conn) -> bool:
    """True when all four result tables exist (the DDL is applied all at once or not at all)."""
    with conn.cursor() as cur:
        for table in DB_TABLES.values():
            cur.execute("SELECT to_regclass(%s)", (table,))
            if cur.fetchone()[0] is None:
                return False
    return True


def read_db_tables(conn) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Any]]:
    """SELECT the columns the report reads from the four tables (never the JSON/text payload columns)."""
    raw: Dict[str, pd.DataFrame] = {}
    tables: List[Dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout = '600s'")
        for kind, table in DB_TABLES.items():
            schema, name = table.split(".")
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s",
                        (schema, name))
            present = {row[0] for row in cur.fetchall()}
            flags = JSON_FLAGS.get(kind, {})
            names: List[str] = []
            expressions: List[str] = []
            for column in TABLE_SCHEMA[kind]:
                if column in flags:  # a flag out of a JSON column: only the key is fetched, not the document
                    source, key = flags[column]
                    if source in present:
                        names.append(column)
                        expressions.append(f"{source} ->> '{key}'")
                elif column in present:
                    names.append(column)
                    expressions.append(column)
            if expressions:
                cur.execute(f"SELECT {', '.join(expressions)} FROM {table}")
                raw[kind] = pd.DataFrame(cur.fetchall(), columns=names)
            else:
                raw[kind] = pd.DataFrame()
            tables.append({"kind": kind, "table": table, "rows": int(len(raw[kind]))})
    return raw, {"kind": "db", "host": common.DB_PARAMS["host"], "dbname": common.DB_PARAMS["dbname"], "tables": tables}


def coerce_table(kind: str, raw: pd.DataFrame) -> pd.DataFrame:
    """Typed frame with every column of TABLE_SCHEMA[kind]; optional columns that are absent are filled with NA."""
    out = pd.DataFrame(index=raw.index)
    flags = JSON_FLAGS.get(kind, {})
    for column, tag in TABLE_SCHEMA[kind].items():
        if column in flags:
            out[column] = derived_flag(raw, column, *flags[column])
            continue
        values = raw[column] if column in raw.columns else pd.Series(pd.NA, index=raw.index, dtype="object")
        if tag == _DAY:
            values = pd.to_datetime(values, errors="coerce")
            if values.dt.tz is not None:
                values = values.dt.tz_convert(None)
            values = values.dt.normalize()
        elif tag == _TS:
            values = pd.to_datetime(values, errors="coerce", utc=True)
        elif tag == _NUM:
            values = pd.to_numeric(values, errors="coerce")
        elif tag == _BOOL:
            values = values.astype("boolean")
        elif tag == _JSON:
            values = values.map(as_mapping).astype("object")
        else:
            values = values.astype("object")
        out[column] = values
    return out


def run_timestamps(runs: pd.DataFrame) -> pd.Series:
    """{run_id: ingested_at, else submitted_at, else created_at}: when the answers of a run reached the table."""
    if runs.empty:
        return pd.Series(dtype="datetime64[ns, UTC]")
    when = runs["ingested_at"].fillna(runs["submitted_at"]).fillna(runs["created_at"])
    return pd.Series(when.to_numpy(), index=runs["run_id"].to_numpy())


def prepare_table(kind: str, raw: pd.DataFrame, notes: List[str], run_times: Optional[pd.Series] = None) -> pd.DataFrame:
    """Typed, key-unique table; a table with a missing required column is ignored with a warning.

    A duplicated natural key keeps the row with the latest ``created_at``.  Per-run detection parquet from
    04_llm_runner.py has no such column, so ``run_times`` (the run's ingestion time) orders the rows instead of
    the file name.
    """
    if raw.empty:
        return coerce_table(kind, pd.DataFrame())
    missing = [c for c in REQUIRED_COLUMNS[kind] if c not in raw.columns]
    if missing:
        note(notes, f"{kind}: required column(s) {missing} missing, table ignored")
        return coerce_table(kind, pd.DataFrame())
    df = coerce_table(kind, raw)
    unusable = df[list(REQUIRED_COLUMNS[kind])].isna().any(axis=1) if kind != "detections" else df["window_end"].isna()
    if unusable.any():
        note(notes, f"{kind}: dropped {int(unusable.sum())} row(s) with a null in a required column")
        df = df[~unusable]
    if kind == "detections" and run_times is not None and len(run_times):
        df = df.assign(created_at=df["created_at"].fillna(df["run_id"].map(run_times)))
    if df["created_at"].notna().any():
        df = df.sort_values("created_at", kind="stable", na_position="first")
    unique = df.drop_duplicates(NATURAL_KEYS[kind], keep="last")
    if len(unique) < len(df):
        logger.info("%s: %d duplicate natural-key row(s) collapsed (latest created_at kept)", kind, len(df) - len(unique))
    return unique.reset_index(drop=True)


def registered_arm(arm: str) -> Optional["common.Arm"]:
    """Registry entry (common.ARMS) of an arm label; a repeat '<arm>#rep<k>' and an '<arm>_all' variant resolve to their arm."""
    base = common.base_arm(str(arm))
    found = common.ARMS.get(base)
    if found is None and base.endswith(ALL_SUFFIX):
        found = common.ARMS.get(base[: -len(ALL_SUFFIX)])
    return found


def window_series_of(arm: str, series_key: str) -> str:
    """Series whose stored windows the answers of ``arm`` (series ``series_key``) were scored against.

    The windows of a registered arm are those of common.arm_window_series(arm) (arm intraday_spy reads
    series intraday_late and is scored on the composite intraday_t0 windows) while the detections keep series_key =
    arm.series_key.  Arms outside the registry (pilots) use their own series, or WINDOW_SERIES_ALIAS for a composite.
    """
    registered = registered_arm(arm)
    if registered is not None and registered.series_key == series_key:
        return common.arm_window_series(registered)
    return WINDOW_SERIES_ALIAS.get(series_key, series_key)


def arm_role(arm: str) -> str:
    """backfill (published results), backfill_all (the same with the recovered windows), primary (registered LLM arm),
    repeat, pilot or other."""
    if REPEAT_MARK in arm:
        return "repeat"
    registered = common.ARMS.get(arm)
    if registered is not None:
        return "primary" if registered.llm else "backfill"
    if arm.endswith(ALL_SUFFIX) and arm_role(arm[: -len(ALL_SUFFIX)]) == "backfill":
        return "backfill_all"
    return "pilot" if arm.startswith("pilot") else "other"


def repeat_index(label: str) -> int:
    """k of a '<...>#rep<k>' arm label or custom_id (common.custom_id_repeat): 0 for an original, 1 for a bare '#rep'.

    Text after the mark that is not a number still marks a repeat (k = 1) rather than raising.
    """
    try:
        return common.custom_id_repeat(label)
    except ValueError:
        return 1


def tag_repeats(det: pd.DataFrame) -> pd.DataFrame:
    """Add ``base_arm`` and ``repeat_index`` (0 = original run) and rename every repeat arm to '<arm>#rep<k>'.

    A repeat is recognised by its arm label ('<arm>#rep<k>' as 04_llm_runner.py stores it) or, failing
    that, by a custom_id ending in '#rep<k>'.  The arm is split with common.base_arm and the index read with
    common.custom_id_repeat; a bare '#rep' counts as k = 1.
    """
    arm = det["arm"].astype(str)
    custom = det["custom_id"].fillna("").astype(str)
    from_arm = arm.map(repeat_index).astype(int)
    from_custom = custom.map(repeat_index).astype(int)
    index = from_arm.where(from_arm > 0, from_custom)
    base = arm.map(common.base_arm)
    return det.assign(base_arm=base, repeat_index=index, arm=arm.where(index == 0, base + REPEAT_MARK + index.astype(str)))


def published_rows(det: pd.DataFrame) -> pd.DataFrame:
    """Rows that belong to the published result: everything except the answers flagged ``recovered_2026``."""
    return det[~det["recovered_2026"]]


def with_recovered_variants(det: pd.DataFrame) -> pd.DataFrame:
    """Detections as the rate tables score them: a flagged row is left out of its arm (the published result) and every
    arm that has flagged rows is added once more, whole, under ``<arm>_all``."""
    flagged_arms = sorted(set(det.loc[det["recovered_2026"], "arm"]))
    if not flagged_arms:
        return det
    whole = det[det["arm"].isin(flagged_arms)]
    return pd.concat([published_rows(det), whole.assign(arm=whole["arm"] + ALL_SUFFIX)], ignore_index=True)


def attach_windows(det: pd.DataFrame, win: pd.DataFrame) -> pd.DataFrame:
    """Add ``window_series_key``, ``window_start`` and the classifier columns of the window each detection scored."""
    keys = ["series_key", "symbol", "window_end"]
    columns = ["window_start", "clf_regime_type", "clf_should_detect", "clf_positive_days", "clf_negative_days",
               "clf_persistence_pct", "clf_avg_magnitude", "clf_sign_flips"]
    lookup = {(arm, series): window_series_of(arm, series)
              for arm, series in det[["arm", "series_key"]].drop_duplicates().itertuples(index=False)}
    window_series = pd.Series([lookup[pair] for pair in zip(det["arm"], det["series_key"], strict=True)], index=det.index,
                              dtype="object")
    out = det.assign(window_series_key=window_series)
    right = win[keys + columns].rename(columns={"series_key": "window_series_key"})
    return out.merge(right, on=["window_series_key", "symbol", "window_end"], how="left")


def enrich_detections(det: pd.DataFrame, win: pd.DataFrame) -> pd.DataFrame:
    """Detections plus arm bookkeeping, a ``parsed`` flag, the year and the matching classifier window."""
    det = tag_repeats(det)
    det = det.assign(arm_role=det["arm"].map(arm_role),
                     parsed=det["parse_status"].isin(OK_PARSE) & det["regime_detected"].notna(),
                     year=det["window_end"].dt.year)
    return attach_windows(det, win)


def check_classifier_versions(win: pd.DataFrame, notes: List[str]) -> None:
    """Warn when windows were labelled with different classifier thresholds (labels would not be comparable)."""
    thresholds = {v.split(" ", 1)[1] if " " in v else v for v in win["clf_version"].dropna().unique()}
    if len(thresholds) > 1:
        note(notes, f"windows carry {len(thresholds)} different classifier threshold sets: {sorted(thresholds)}")


def check_window_coverage(det: pd.DataFrame, notes: List[str]) -> None:
    """Warn for each arm whose parsed answers include windows that are not stored (the classifier label is then missing)."""
    parsed = det[det["parsed"]]
    missing = parsed[parsed["clf_should_detect"].isna()]
    for (arm, series_key, window_series), group in missing.groupby(["arm", "series_key", "window_series_key"]):
        total = int(((parsed["arm"] == arm) & (parsed["series_key"] == series_key)).sum())
        note(notes, f"{arm}: {len(group)} of {total} parsed answers have no stored window in series {window_series} "
                    "(02_build_windows.py); they have no classifier label")


def build_data(raw: Dict[str, pd.DataFrame], source: Dict[str, Any]) -> Data:
    """Type, de-duplicate and enrich the raw tables."""
    notes: List[str] = []
    tables: Dict[str, pd.DataFrame] = {}
    for kind in ("runs", "series", "windows", "detections"):  # runs first: their timestamps order duplicate detections
        extra = {"run_times": run_timestamps(tables["runs"])} if kind == "detections" else {}
        tables[kind] = prepare_table(kind, raw.get(kind, pd.DataFrame()), notes, **extra)
    check_classifier_versions(tables["windows"], notes)
    backfilled = sorted(set(tables["detections"]["arm"]) & set(BACKFILL_ARMS))
    if backfilled and not ({"detection_metadata", RECOVERED_FLAG} & set(raw.get("detections", pd.DataFrame()).columns)):
        note(notes, "detections have no detection_metadata column: the answers recovered in 2026 cannot be told apart, "
                    f"so every row of {', '.join(backfilled)} counts as published")
    detections = enrich_detections(tables["detections"], tables["windows"])
    check_window_coverage(detections, notes)
    enriched = {**tables, "detections": detections}
    stamps = {kind: (enriched[kind]["created_at"].max().isoformat() if enriched[kind]["created_at"].notna().any() else None)
              for kind in KINDS}
    return Data(tables["series"], tables["windows"], detections, tables["runs"],
                {**source, "max_created_at": stamps}, notes)


def open_result_connection():
    """(read-only connection, None) when Postgres is reachable and holds the four tables, else (None, reason)."""
    try:
        conn = common.connect()
    except Exception as exc:  # connection refused, unknown host, ...
        return None, f"Postgres unavailable ({type(exc).__name__}: {exc})"
    try:
        conn.set_session(readonly=True)
        if db_tables_exist(conn):
            return conn, None
        reason = "the backups.gex_llm_regime_* tables do not exist"
    except Exception as exc:  # permission denied, ...
        reason = f"Postgres unusable ({type(exc).__name__}: {exc})"
    conn.close()
    return None, reason


def load_data(source: str, parquet_root: Path) -> Data:
    """Load from Postgres (``db``), from parquet, or ``auto``: Postgres when all four tables exist, else parquet."""
    reason = "--source parquet"
    if source != "parquet":
        conn, reason = open_result_connection()
        if conn is not None:
            try:
                logger.info("reading the result tables from Postgres (%s)", common.DB_PARAMS["dbname"])
                return build_data(*read_db_tables(conn))
            finally:
                conn.close()
        if source == "db":
            raise InputError(f"--source db requested but {reason}")
    logger.info("%s: reading the parquet copies under %s", reason, parquet_root)
    return build_data(*read_parquet_tables(parquet_root))


# --------------------------------------------------------------------------- context and writers
class SectionSkipped(Exception):
    """Raised by a section whose inputs are absent; the message becomes a warning in report.yaml."""


def rounded(value: float) -> float:
    """6 decimals, but 6 significant digits below 0.001, so that a tiny p-value is not written as 0.0."""
    return float(f"{value:.6g}") if 0.0 < abs(value) < 1e-3 else round(value, 6)


def native_key(key: Any) -> Any:
    """YAML mapping key: strings stay; an integral float (a year read from a float column) becomes an int."""
    key = key if isinstance(key, str) else to_native(key)
    return int(key) if isinstance(key, float) and key.is_integer() else key


def to_native(obj: Any) -> Any:
    """Plain-Python copy of nested results for YAML: numpy scalars unwrapped, NaN/inf -> null, timestamps -> ISO."""
    if isinstance(obj, dict):
        return {native_key(k): to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_native(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [to_native(v) for v in obj.tolist()]
    if obj is None or obj is pd.NaT or obj is pd.NA:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        value = float(obj)
        return rounded(value) if math.isfinite(value) else None
    if isinstance(obj, pd.Timestamp):
        return obj.date().isoformat() if obj.tzinfo is None and obj == obj.normalize() else obj.isoformat()
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return obj


@dataclass
class Context:
    """Inputs, run parameters and the bookkeeping that ends up in report.yaml."""

    data: Data
    results_dir: Path
    seed: int = SEED
    n_boot: int = N_BOOT
    warnings: List[str] = field(default_factory=list)
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def warn(self, message: str) -> None:
        note(self.warnings, message)

    def write_csv(self, name: str, frame: pd.DataFrame, int_columns: Sequence[str] = (), decimals: int = 6) -> None:
        out = frame.copy()
        for column in int_columns:
            out[column] = out[column].astype("Int64")
        text = out.round(decimals)
        for column in out.columns:  # p-values keep 6 significant digits instead of 6 decimals
            if column.startswith("p_") and pd.api.types.is_float_dtype(out[column]):
                text[column] = out[column].map(lambda v: v if pd.isna(v) else rounded(float(v)))
        text.to_csv(self.results_dir / name, index=False)
        self.files[name] = {"rows": int(len(out)), "columns": list(out.columns)}
        logger.info("wrote %s (%d rows)", name, len(out))

    def write_yaml(self, name: str, payload: Dict[str, Any]) -> None:
        with open(self.results_dir / name, "w") as fh:
            yaml.safe_dump(to_native(payload), fh, sort_keys=False, default_flow_style=False, allow_unicode=True, width=110)
        self.files[name] = {"keys": list(payload)}
        logger.info("wrote %s", name)


def _rank(value: Any, order: Sequence[str]) -> str:
    """Sort key: position of the registered name (a repeat '<arm>#rep<k>' and '<arm>_all' rank with their arm), then the name."""
    base = str(value).split(REPEAT_MARK)[0]
    if base not in order and base.endswith(ALL_SUFFIX):
        base = base[: -len(ALL_SUFFIX)]
    return f"{order.index(base) if base in order else len(order):03d}|{value}"


def sort_rows(frame: pd.DataFrame, by: Sequence[str]) -> pd.DataFrame:
    """Stable sort: registry order for series and arms, classifier before llm, 'year' scopes before 'all'."""
    def key(column: pd.Series) -> pd.Series:
        if column.name in ("series_key", "series_a", "series_b"):
            return column.map(lambda v: _rank(v, SERIES_ORDER))
        if column.name in ("arm", "ref_arm", "other_arm", "base_arm"):
            return column.map(lambda v: _rank(v, ARM_ORDER))
        if column.name == "scope":
            return column.map({"year": 0, "all": 1})
        if column.name == "label_source":
            return column.map({"classifier": 0, "llm": 1})
        return column

    return frame.sort_values(list(by), key=key, kind="stable").reset_index(drop=True)


def iter_scopes(frame: pd.DataFrame, column: str) -> Iterator[Tuple[str, Optional[int], pd.DataFrame]]:
    """Yield ('year', y, rows of year y) for every year present in ``column``, then ('all', None, every row)."""
    years = frame[column].dt.year
    for year in sorted(years.dropna().unique()):
        yield "year", int(year), frame[years == year]
    yield "all", None, frame


def nest(frame: pd.DataFrame, keys: Sequence[str], value: str) -> Dict[Any, Any]:
    """{k1: {k2: ... value}} from rows; rows whose value is NaN are left out."""
    out: Dict[Any, Any] = {}
    for row in frame.dropna(subset=[value]).to_dict("records"):
        node = out
        for k in keys[:-1]:
            node = node.setdefault(row[k], {})
        node[row[keys[-1]]] = row[value]
    return out


# --------------------------------------------------------------------------- 1. detection_by_year.csv
DETECTION_COLUMNS = [
    "label_source", "arm", "arm_role", "model", "series_key", "symbol", "scope", "year",
    "n_windows", "n_parsed", "n", "n_detect", "rate_pct", "ci_lo_pct", "ci_hi_pct", "n_indep_30d",
    "mean_abs_gex_bn", "n_compared", "clf_rate_matched_pct", "clf_mean_abs_gex_bn_matched",
    "agree_pct", "kappa", "metrics_agree_pct", "sign_flips_exact_pct", "median_ratio_reported_to_computed",
]
DETECTION_INT_COLUMNS = ["year", "n_windows", "n_parsed", "n", "n_detect", "n_indep_30d", "n_compared"]
WIDE_COLUMNS = [
    "series_key", "symbol", "year", "n", "clf_rate", "clf_ci_lo", "clf_ci_hi", "arm", "model", "n_parsed",
    "llm_rate", "llm_ci_lo", "llm_ci_hi", "agree_pct", "kappa",
    "arm_role", "n_windows", "n_compared", "clf_rate_matched", "n_indep_30d",
]
WIDE_INT_COLUMNS = ["year", "n", "n_parsed", "n_windows", "n_compared", "n_indep_30d"]


def ratio_summary(reported_bn: pd.Series, computed_usd: pd.Series) -> Dict[str, Any]:
    """Distribution of reported / computed mean |GEX| (reported in USD billions, computed in USD).

    Only rows where both exist and the computed mean is positive count.  ``n`` is 0 and the rest absent when none qualifies;
    ``ratio_within_5pct_pct`` is the share (percent) of rows whose ratio lies within 5 percent of 1.
    """
    reported = pd.to_numeric(reported_bn, errors="coerce").to_numpy(float)
    computed = pd.to_numeric(computed_usd, errors="coerce").to_numpy(float) / 1e9
    ok = np.isfinite(reported) & np.isfinite(computed) & (computed > 0)
    if not ok.any():
        return {"n": 0}
    ratio = reported[ok] / computed[ok]
    q25, median, q75 = np.percentile(ratio, [25, 50, 75])
    return {"n": int(ok.sum()), "median_ratio": float(median), "q25_ratio": float(q25), "q75_ratio": float(q75),
            "ratio_within_5pct_pct": 100.0 * float((np.abs(ratio - 1.0) <= 0.05).mean()),
            "median_abs_diff_bn": float(np.median(np.abs(reported[ok] - computed[ok]))),
            "median_reported_bn": float(np.median(reported[ok])), "median_computed_bn": float(np.median(computed[ok]))}


def median_ratio(reported_bn: pd.Series, computed_usd: pd.Series) -> float:
    """Median of reported / computed mean |GEX| (see ratio_summary); NaN when no row qualifies."""
    return ratio_summary(reported_bn, computed_usd).get("median_ratio", math.nan)


def classifier_rows(win: pd.DataFrame) -> List[Dict[str, Any]]:
    rows = []
    for (series_key, symbol), group in win.groupby(["series_key", "symbol"], sort=True):
        for scope, year, sub in iter_scopes(group, "window_end"):
            n = len(sub)
            rows.append({
                "label_source": "classifier", "arm": "", "arm_role": "", "model": "",
                "series_key": series_key, "symbol": symbol, "scope": scope, "year": year, "n_windows": n,
                **rate_fields(int(sub["clf_should_detect"].sum()), n),
                "n_indep_30d": independent_count(sub),
                "mean_abs_gex_bn": sub["clf_avg_magnitude"].mean() / 1e9,
            })
    return rows


def llm_rows(det: pd.DataFrame) -> List[Dict[str, Any]]:
    rows = []
    for (arm, model, series_key, symbol), group in det.groupby(["arm", "model", "series_key", "symbol"], sort=True):
        for scope, year, sub in iter_scopes(group, "window_end"):
            parsed = sub[sub["parsed"]]
            matched = parsed[parsed["clf_should_detect"].notna()]
            n = len(parsed)
            row: Dict[str, Any] = {
                "label_source": "llm", "arm": arm, "arm_role": arm_role(arm), "model": model,
                "series_key": series_key, "symbol": symbol, "scope": scope, "year": year,
                "n_windows": len(sub), "n_parsed": n, **rate_fields(int(parsed["regime_detected"].sum()), n),
                "n_indep_30d": independent_count(parsed),
                "mean_abs_gex_bn": parsed["avg_magnitude_billions"].mean(),
                "n_compared": len(matched),
                "metrics_agree_pct": 100.0 * parsed["metrics_agree"].dropna().astype(bool).mean(),
            }
            if len(matched):
                tt, tf, ft, ff = confusion_counts(matched["regime_detected"], matched["clf_should_detect"])
                both = matched["sign_flips"].notna() & matched["clf_sign_flips"].notna()
                row.update({
                    "clf_rate_matched_pct": 100.0 * (tt + ft) / len(matched),
                    "clf_mean_abs_gex_bn_matched": matched["clf_avg_magnitude"].mean() / 1e9,
                    "agree_pct": 100.0 * (tt + ff) / len(matched),
                    "kappa": float(binary_kappa(tt, tf, ft, ff)),
                    "sign_flips_exact_pct": (100.0 * (matched.loc[both, "sign_flips"] == matched.loc[both, "clf_sign_flips"]).mean()
                                             if both.any() else math.nan),
                    "median_ratio_reported_to_computed": median_ratio(matched["avg_magnitude_billions"], matched["clf_avg_magnitude"]),
                })
            rows.append(row)
    return rows


def wide_detection_frame(long: pd.DataFrame) -> pd.DataFrame:
    """The yearly rows of the long table in the shape of the written spec (rates as fractions in [0, 1]).

    Classifier rows have an empty arm.  An LLM row repeats the classifier columns (n, clf_rate, clf_ci_lo, clf_ci_hi)
    of the windows the arm scored (``window_series_of``: ``intraday_t0`` for arm ``intraday_spy``, else its own series).
    """
    yearly = long[long["scope"] == "year"].assign(year=lambda f: f["year"].astype(int))
    clf = yearly[yearly["label_source"] == "classifier"]
    llm = yearly[yearly["label_source"] == "llm"]
    reference = pd.DataFrame({
        "window_series_key": clf["series_key"], "symbol": clf["symbol"], "year": clf["year"], "clf_n": clf["n"],
        "clf_rate": clf["rate_pct"] / 100.0, "clf_ci_lo": clf["ci_lo_pct"] / 100.0, "clf_ci_hi": clf["ci_hi_pct"] / 100.0})
    classifier_part = reference.rename(columns={"window_series_key": "series_key", "clf_n": "n"}).assign(
        arm="", model="", arm_role="", n_windows=clf["n_windows"], n_indep_30d=clf["n_indep_30d"])
    scored_on = [window_series_of(arm, key) for arm, key in zip(llm["arm"], llm["series_key"], strict=True)]
    merged = llm.assign(window_series_key=scored_on).merge(reference, on=["window_series_key", "symbol", "year"], how="left")
    llm_part = pd.DataFrame({
        "series_key": merged["series_key"], "symbol": merged["symbol"], "year": merged["year"],
        "n": merged["clf_n"].fillna(merged["n_windows"]), "clf_rate": merged["clf_rate"], "clf_ci_lo": merged["clf_ci_lo"],
        "clf_ci_hi": merged["clf_ci_hi"], "arm": merged["arm"], "model": merged["model"], "n_parsed": merged["n_parsed"],
        "llm_rate": merged["rate_pct"] / 100.0, "llm_ci_lo": merged["ci_lo_pct"] / 100.0, "llm_ci_hi": merged["ci_hi_pct"] / 100.0,
        "agree_pct": merged["agree_pct"], "kappa": merged["kappa"], "arm_role": merged["arm_role"],
        "n_windows": merged["n_windows"], "n_compared": merged["n_compared"],
        "clf_rate_matched": merged["clf_rate_matched_pct"] / 100.0, "n_indep_30d": merged["n_indep_30d"]})
    wide = pd.concat([classifier_part.assign(_llm=0), llm_part.assign(_llm=1)], ignore_index=True)
    wide = sort_rows(wide, ["series_key", "symbol", "year", "_llm", "arm", "model"])
    return wide.reindex(columns=WIDE_COLUMNS)


def section_detection_by_year(ctx: Context) -> Dict[str, Any]:
    data = ctx.data
    if data.windows.empty and data.detections.empty:
        raise SectionSkipped("no windows and no detections")
    scored = with_recovered_variants(data.detections)
    rows = classifier_rows(data.windows) + llm_rows(scored)
    frame = sort_rows(pd.DataFrame(rows, columns=DETECTION_COLUMNS),
                      ["label_source", "series_key", "symbol", "arm", "model", "scope", "year"])
    ctx.write_csv("detection_by_year.csv", frame, DETECTION_INT_COLUMNS)
    ctx.write_csv("detection_by_year_wide.csv", wide_detection_frame(frame), WIDE_INT_COLUMNS, decimals=8)  # fractions: 8 = 6 of percent
    yearly = frame[frame["scope"] == "year"]
    llm = frame[(frame["label_source"] == "llm") & frame["arm_role"].isin(["primary", "backfill"])]
    recovered = data.detections[data.detections["recovered_2026"]]
    return {
        "rows": len(frame),
        "classifier_rate_pct_by_year": nest(yearly[yearly["label_source"] == "classifier"],
                                            ["series_key", "symbol", "year"], "rate_pct"),
        "llm_rate_pct_by_year": nest(llm[llm["scope"] == "year"], ["arm", "model", "year"], "rate_pct"),
        "llm_vs_classifier_all_years": llm[llm["scope"] == "all"][
            ["arm", "model", "series_key", "symbol", "n_parsed", "n_compared", "agree_pct", "kappa"]
        ].to_dict("records"),
        "recovered_2026": {"windows": len(recovered), "arms": sorted(set(recovered["arm"])),
                           "note": f"left out of the {BRIDGE_REFERENCE_ARM} rows (the published result); "
                                   f"{BRIDGE_REFERENCE_ARM}{ALL_SUFFIX} rows include them"},
    }


# --------------------------------------------------------------------------- 2. bridge_agreement.csv / .yaml
BRIDGE_COLUMNS = [
    "comparison", "ref_arm", "ref_model", "other_arm", "other_model", "series_key", "symbol", "scope", "year",
    "n_pairs", "n_ref_det_oth_det", "n_ref_det_oth_not", "n_ref_not_oth_det", "n_ref_not_oth_not",
    "agree_pct", "agree_ci_lo_pct", "agree_ci_hi_pct", "agree_boot_lo_pct", "agree_boot_hi_pct",
    "kappa", "kappa_boot_lo", "kappa_boot_hi", "type_agree_pct",
    "n_disagree_with_clf", "n_disagree_ref_matches_clf", "n_disagree_other_matches_clf",
    "rate_ref_pct", "rate_other_pct", "rate_diff_pp", "rate_diff_boot_lo_pp", "rate_diff_boot_hi_pp",
    "p_mcnemar_exact", "p_boot", "ref_clf_agree_pct", "other_clf_agree_pct", "median_ratio_ref", "median_ratio_other",
    "n", "both_detect", "only_r1", "only_luna", "neither",  # the names of the written spec: same counts as the n_* columns
]
BRIDGE_INT_COLUMNS = ["year", "n_pairs", "n_ref_det_oth_det", "n_ref_det_oth_not", "n_ref_not_oth_det",
                      "n_ref_not_oth_not", "n_disagree_with_clf", "n_disagree_ref_matches_clf",
                      "n_disagree_other_matches_clf", "n", "both_detect", "only_r1", "only_luna", "neither"]
BRIDGE_COMPARISONS = ("bridge", "bridge_incl_recovered", "test_retest")


def pair_frame(ref: pd.DataFrame, oth: pd.DataFrame, keys: Sequence[str]) -> pd.DataFrame:
    """Inner join of two parsed detection sets on the window keys, as ref/oth boolean pair columns."""
    keys = list(keys)
    left = ref[keys + ["regime_detected", "regime_type", "clf_should_detect", "avg_magnitude_billions", "clf_avg_magnitude"]].rename(
        columns={"regime_detected": "ref", "regime_type": "type_ref", "clf_should_detect": "clf",
                 "avg_magnitude_billions": "mag_ref", "clf_avg_magnitude": "clf_mag"})
    right = oth[keys + ["regime_detected", "regime_type", "avg_magnitude_billions"]].rename(
        columns={"regime_detected": "oth", "regime_type": "type_oth", "avg_magnitude_billions": "mag_oth"})
    merged = left.merge(right, on=keys, how="inner")
    return merged.assign(ref=merged["ref"].astype(bool), oth=merged["oth"].astype(bool))


def agreement_record(pairs: pd.DataFrame, ctx: Optional[Context]) -> Dict[str, Any]:
    """Confusion matrix on regime_detected, agreement, kappa, McNemar tests and, with ``ctx``, block-bootstrap intervals.

    ``rate_diff_pp`` is the detection rate of the reference minus that of the other arm on the paired windows (the
    discordant counts decide it); ``p_mcnemar_exact`` treats the stride-1 windows as independent, ``p_boot`` (all-years
    row only) resamples calendar quarters.
    """
    ref, oth = pairs["ref"].to_numpy(bool), pairs["oth"].to_numpy(bool)
    tt, tf, ft, ff = confusion_counts(ref, oth)
    n = len(pairs)
    lo, hi = wilson_pct(tt + ff, n)
    typed = pairs["type_ref"].notna() & pairs["type_oth"].notna()
    labelled = pairs[(pairs["ref"] != pairs["oth"]) & pairs["clf"].notna()]
    ref_right = int((labelled["ref"] == labelled["clf"]).sum())
    with_clf = pairs[pairs["clf"].notna()]
    record: Dict[str, Any] = {
        "n_pairs": n, "n_ref_det_oth_det": tt, "n_ref_det_oth_not": tf, "n_ref_not_oth_det": ft, "n_ref_not_oth_not": ff,
        "agree_pct": 100.0 * (tt + ff) / n, "agree_ci_lo_pct": lo, "agree_ci_hi_pct": hi,
        "kappa": float(binary_kappa(tt, tf, ft, ff)),
        "type_agree_pct": (100.0 * (pairs.loc[typed, "type_ref"] == pairs.loc[typed, "type_oth"]).mean()
                           if typed.any() else math.nan),
        "n_disagree_with_clf": len(labelled), "n_disagree_ref_matches_clf": ref_right,
        "n_disagree_other_matches_clf": len(labelled) - ref_right,
        "rate_ref_pct": 100.0 * (tt + tf) / n, "rate_other_pct": 100.0 * (tt + ft) / n, "rate_diff_pp": 100.0 * (tf - ft) / n,
        "p_mcnemar_exact": mcnemar_exact(tf, ft),
        "ref_clf_agree_pct": (100.0 * (with_clf["ref"] == with_clf["clf"].astype(bool)).mean() if len(with_clf) else math.nan),
        "other_clf_agree_pct": (100.0 * (with_clf["oth"] == with_clf["clf"].astype(bool)).mean() if len(with_clf) else math.nan),
        "median_ratio_ref": median_ratio(pairs["mag_ref"], pairs["clf_mag"]),
        "median_ratio_other": median_ratio(pairs["mag_oth"], pairs["clf_mag"]),
        "n": n, "both_detect": tt, "only_r1": tf, "only_luna": ft, "neither": ff,
    }
    if ctx is not None and n:
        cells = pd.DataFrame({"window_end": pairs["window_end"], "tt": ref & oth, "tf": ref & ~oth,
                              "ft": ~ref & oth, "ff": ~ref & ~oth})
        sums = resample_block_sums(block_sums(cells, ["tt", "tf", "ft", "ff"]), ctx.n_boot, np.random.default_rng(ctx.seed))
        record["kappa_boot_lo"], record["kappa_boot_hi"] = percentile_interval(binary_kappa(*sums.T))
        record["agree_boot_lo_pct"], record["agree_boot_hi_pct"] = (
            100.0 * x for x in percentile_interval((sums[:, 0] + sums[:, 3]) / sums.sum(axis=1)))
        diff = 100.0 * (sums[:, 1] - sums[:, 2]) / sums.sum(axis=1)
        record["rate_diff_boot_lo_pp"], record["rate_diff_boot_hi_pp"] = percentile_interval(diff)
        record["p_boot"] = bootstrap_p_value(diff)
    return record


def compare_detections(ctx: Context, comparison: str, ref: pd.DataFrame, oth: pd.DataFrame,
                       keys: Sequence[str]) -> Optional[Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
    """CSV rows (all years + each year) and the YAML block for one reference-vs-other comparison."""
    pairs = pair_frame(ref, oth, keys)
    if pairs.empty:
        ctx.warn(f"bridge: no common parsed windows for {ref['arm'].iloc[0]} vs {oth['arm'].iloc[0]}")
        return None
    meta = {"comparison": comparison, "ref_arm": ref["arm"].iloc[0], "ref_model": ref["model"].iloc[0],
            "other_arm": oth["arm"].iloc[0], "other_model": oth["model"].iloc[0],
            "series_key": oth["series_key"].iloc[0], "symbol": oth["symbol"].iloc[0]}
    rows, by_year, overall = [], [], {}
    for scope, year, sub in iter_scopes(pairs, "window_end"):
        record = agreement_record(sub, ctx if scope == "all" else None)
        rows.append({**meta, "scope": scope, "year": year, **record})
        if scope == "year":
            by_year.append({"year": year, **record})
        else:
            overall = record
    block = {**meta, "confusion_matrix": {
        "rows": f"{meta['ref_arm']} regime_detected (true, false)", "cols": f"{meta['other_arm']} regime_detected (true, false)",
        "matrix": [[overall["n_ref_det_oth_det"], overall["n_ref_det_oth_not"]],
                   [overall["n_ref_not_oth_det"], overall["n_ref_not_oth_not"]]]},
        **overall, "by_year": by_year}
    return rows, block


def bridge_gate(bridge: List[Dict[str, Any]], incl: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The agreement gate on the published reference and the first (non-repeat) luna arm with the most pairs.

    ``met`` is None, not False, when kappa is undefined (one rater is constant over all pairs); ``agree_pct`` is then
    the number to read.  The same comparison with the recovered answers added is reported next to it.
    """
    primary = [b for b in bridge if b["ref_arm"] == BRIDGE_REFERENCE_ARM and arm_role(b["other_arm"]) == "primary"]
    if not primary:
        return None
    best = max(primary, key=lambda b: b["n_pairs"])
    kappa = best["kappa"]
    defined = kappa is not None and math.isfinite(kappa)
    twin = next((b for b in incl if b["ref_arm"] == BRIDGE_REFERENCE_ARM + ALL_SUFFIX
                 and (b["other_arm"], b["other_model"], b["symbol"]) == (best["other_arm"], best["other_model"], best["symbol"])),
                None)
    gate: Dict[str, Any] = {
        "comparison": f"{best['ref_arm']} vs {best['other_arm']}", "metric": "cohen_kappa",
        "threshold": BRIDGE_GATE_MIN_KAPPA, "source": "planning/00_design.md section 5",
        "window_set": f"published answers ({BRIDGE_REFERENCE_ARM} without detection_metadata {RECOVERED_FLAG})",
        "kappa": kappa if defined else None, "kappa_defined": bool(defined), "agree_pct": best["agree_pct"],
        "n_pairs": best["n_pairs"], "met": bool(kappa >= BRIDGE_GATE_MIN_KAPPA) if defined else None,
        "incl_recovered": (None if twin is None else
                           {"n_pairs": twin["n_pairs"], "agree_pct": twin["agree_pct"], "kappa": twin["kappa"]}),
    }
    if not defined:
        gate["note"] = ("kappa is undefined (one rater gives the same verdict on every pair, so chance agreement is 1): "
                        "the gate cannot be evaluated; read agree_pct")
    return gate


def bridge_pairs(parsed: pd.DataFrame) -> Iterator[Tuple[str, pd.DataFrame, pd.DataFrame]]:
    """(comparison, reference rows, other rows) for every published o4-mini arm against each gpt-6-luna arm on the same series.

    ``bridge`` uses the published answers of the reference arm (the rows without ``recovered_2026``); when the arm holds
    recovered answers as well, ``bridge_incl_recovered`` repeats the comparison with all of them (reference label
    ``<arm>_all``).  Repeats ('<arm>#rep<k>', role repeat) are not luna arms here; they go to the test-retest block.
    """
    for ref_arm, series_key in BRIDGE_REFERENCES:
        on_series = parsed[parsed["series_key"] == series_key]
        reference_all = on_series[on_series["arm"] == ref_arm]
        reference = published_rows(reference_all)
        others = on_series[on_series["arm_role"] == "primary"]
        if reference.empty or others.empty:
            continue
        variants = [("bridge", reference)]
        if len(reference_all) > len(reference):
            variants.append(("bridge_incl_recovered", reference_all.assign(arm=ref_arm + ALL_SUFFIX)))
        for comparison, ref_frame in variants:
            for (_, symbol), ref_group in ref_frame.groupby(["model", "symbol"]):
                for _, oth_group in others[others["symbol"] == symbol].groupby(["arm", "model"]):
                    yield comparison, ref_group, oth_group


def section_bridge_agreement(ctx: Context) -> Dict[str, Any]:
    parsed = ctx.data.detections[ctx.data.detections["parsed"]]
    rows: List[Dict[str, Any]] = []
    bridge: List[Dict[str, Any]] = []
    incl: List[Dict[str, Any]] = []
    retest: List[Dict[str, Any]] = []
    for comparison, ref_group, oth_group in bridge_pairs(parsed):
        result = compare_detections(ctx, comparison, ref_group, oth_group, ["symbol", "window_end"])
        if result:
            rows += result[0]
            (bridge if comparison == "bridge" else incl).append(result[1])
    if not any(b["ref_arm"] == BRIDGE_REFERENCE_ARM for b in bridge):
        ctx.warn(f"bridge: no comparison of {BRIDGE_REFERENCE_ARM} with a luna arm on {BRIDGE_SERIES} (it needs parsed answers "
                 "of both, with a window in common): the agreement gate is not evaluated")
    for (base, arm, series_key, symbol, model), group in parsed[parsed["repeat_index"] > 0].groupby(
            ["base_arm", "arm", "series_key", "symbol", "model"]):
        original = parsed[(parsed["arm"] == base) & (parsed["series_key"] == series_key)
                          & (parsed["symbol"] == symbol) & (parsed["model"] == model)]
        if original.empty:
            ctx.warn(f"bridge: repeat arm {arm} has no parsed original arm {base}; test-retest skipped")
            continue
        result = compare_detections(ctx, "test_retest", original, group, ["series_key", "symbol", "window_end", "model"])
        if result:
            rows += result[0]
            retest.append(result[1])
    if not rows:
        raise SectionSkipped("no published-o4-mini/luna pairs (r1_o4mini on jan2026_phase4a, r1_p3_o4mini, r1_p4_o4mini) and no "
                             "repeat arms")
    frame = sort_rows(pd.DataFrame(rows, columns=BRIDGE_COLUMNS),
                      ["comparison", "ref_arm", "other_arm", "symbol", "scope", "year"])
    ctx.write_csv("bridge_agreement.csv", frame, BRIDGE_INT_COLUMNS)
    gate = bridge_gate(bridge, incl)
    ctx.write_yaml("bridge_agreement.yaml", {
        "reference_arm": BRIDGE_REFERENCE_ARM, "reference_set": f"published answers (detection_metadata {RECOVERED_FLAG} absent)",
        "series_key": BRIDGE_SERIES, "primary_label": "regime_detected",
        "references": [{"arm": arm, "series_key": series_key, "role": "gate" if arm == BRIDGE_REFERENCE_ARM else "descriptive"}
                       for arm, series_key in BRIDGE_REFERENCES],
        "gate": gate, "bridge": bridge, "bridge_incl_recovered": incl, "test_retest": retest,
        "notes": ["Pairs are windows parsed in both arms; the classifier label comes from the shared window.",
                  f"bridge_incl_recovered repeats the comparison with the answers recovered in 2026 added to the reference "
                  f"(reference arm <arm>{ALL_SUFFIX}); the gate uses the published answers only.",
                  f"Only {BRIDGE_REFERENCE_ARM} on {BRIDGE_SERIES} feeds the gate; r1_p3_o4mini / r1_p4_o4mini (dated Nov-2025 "
                  "prompts) are compared with the gpt-6-luna arms that read the same series, for description.",
                  "test_retest compares an arm with its own repeated requests ('<arm>#rep<k>'); it is not part of the gate.",
                  "Bootstrap intervals resample calendar quarters of window_end (see stats.yaml meta).",
                  "rate_diff_pp = detection rate of the reference minus that of the other arm on the paired windows; "
                  "p_mcnemar_exact is the exact McNemar test on the discordant counts (stride-1 windows treated as independent), "
                  "p_boot the quarter-block bootstrap p-value of the same difference (all-years row only).",
                  "median_ratio_ref / median_ratio_other: median of the model-reported mean |GEX| over the computed mean on the pairs "
                  "(reported_vs_computed.csv has the full distribution).",
                  "kappa is null when one rater is constant and chance agreement is 1; the gate's met is then null."]})

    def brief(blocks: List[Dict[str, Any]], extra: Sequence[str] = ()) -> List[Dict[str, Any]]:
        return [{k: b[k] for k in ("ref_arm", "other_arm", "n_pairs", "agree_pct", "kappa", *extra)} for b in blocks]

    return {"rows": len(frame), "gate": gate, "bridge": brief(bridge, ("rate_diff_pp", "p_mcnemar_exact")),
            "bridge_incl_recovered": brief(incl),
            "test_retest": [{k: r[k] for k in ("ref_arm", "other_arm", "n_pairs", "agree_pct", "kappa")} for r in retest]}


# --------------------------------------------------------------------------- 3. series_comparison.csv
COMPARISON_COLUMNS = [
    "series_a", "series_b", "pair", "symbol", "scope", "year", "n_days", "first_date", "last_date",
    "mean_abs_a_bn", "mean_abs_b_bn", "mean_abs_diff_bn", "median_ratio_a_over_b", "sign_agree_pct", "exact_match_pct",
]


def with_call_only(series: pd.DataFrame) -> pd.DataFrame:
    """Add the derived ``call_only`` series (the call leg of new_full) unless the table already stores one."""
    if (series["series_key"] == CALL_ONLY).any():
        return series
    full = series[(series["series_key"] == FULL_SERIES) & series["call_gex"].notna()]
    if full.empty:
        return series
    derived = full.assign(series_key=CALL_ONLY, net_gex=full["call_gex"], put_gex=np.nan, gex_0dte=np.nan,
                          source_table=f"derived: {FULL_SERIES}.call_gex")
    return pd.concat([series, derived], ignore_index=True)


def pair_day_stats(days: pd.DataFrame) -> Dict[str, Any]:
    """Daily agreement of two series (columns net_gex_a, net_gex_b); sign is 'positive' vs 'not positive'."""
    a, b = days["net_gex_a"].to_numpy(float), days["net_gex_b"].to_numpy(float)
    gap = np.abs(a - b)
    nonzero = b != 0
    return {
        "n_days": len(days),
        "first_date": days["trading_date"].min().date().isoformat(), "last_date": days["trading_date"].max().date().isoformat(),
        "mean_abs_a_bn": np.abs(a).mean() / 1e9, "mean_abs_b_bn": np.abs(b).mean() / 1e9,
        "mean_abs_diff_bn": gap.mean() / 1e9,
        "median_ratio_a_over_b": float(np.median(a[nonzero] / b[nonzero])) if nonzero.any() else math.nan,
        "sign_agree_pct": 100.0 * float(((a > 0) == (b > 0)).mean()),
        "exact_match_pct": 100.0 * float((gap <= EXACT_MATCH_TOL_USD).mean()),
    }


def section_series_comparison(ctx: Context) -> Dict[str, Any]:
    if ctx.data.series.empty:
        raise SectionSkipped("no series rows")
    series = with_call_only(ctx.data.series)
    present = set(series["series_key"])
    rows: List[Dict[str, Any]] = []
    for a, b in SERIES_PAIRS:
        absent = [s for s in (a, b) if s not in present]
        if absent:
            ctx.warn(f"series_comparison: {a} vs {b} skipped, series {absent} absent"
                     + (f" (no {FULL_SERIES}.call_gex to derive {CALL_ONLY} from)" if CALL_ONLY in absent else ""))
            continue
        columns = ["symbol", "trading_date", "net_gex"]
        days = series.loc[series["series_key"] == a, columns].merge(
            series.loc[series["series_key"] == b, columns], on=["symbol", "trading_date"], suffixes=("_a", "_b"))
        if days.empty:
            ctx.warn(f"series_comparison: {a} and {b} share no (symbol, day)")
            continue
        for symbol, group in days.groupby("symbol", sort=True):
            for scope, year, sub in iter_scopes(group, "trading_date"):
                rows.append({"series_a": a, "series_b": b, "pair": f"{a}_vs_{b}", "symbol": symbol, "scope": scope,
                             "year": year, **pair_day_stats(sub)})
    if not rows:
        raise SectionSkipped("no series pair with both series present")
    frame = sort_rows(pd.DataFrame(rows, columns=COMPARISON_COLUMNS), ["series_a", "series_b", "symbol", "scope", "year"])
    ctx.write_csv("series_comparison.csv", frame, ["year", "n_days"])
    yearly = frame[frame["scope"] == "year"]

    def by_pair(column: str) -> Dict[str, Any]:
        return {f"{a}__vs__{b}": nest(sub, ["symbol", "year"], column)
                for (a, b), sub in yearly.groupby(["series_a", "series_b"], sort=False)}

    return {"rows": len(frame), "exact_match_pct_by_year": by_pair("exact_match_pct"),
            "sign_agree_pct_by_year": by_pair("sign_agree_pct")}


# --------------------------------------------------------------------------- shared LLM label lookup
def primary_llm_labels(ctx: Context, window_series_key: str, symbol: Optional[str] = None) -> pd.DataFrame:
    """Parsed detections of the registered LLM arm that scored ``window_series_key`` windows (largest arm/model)."""
    det = ctx.data.detections
    sel = det[det["parsed"] & (det["repeat_index"] == 0) & (det["arm_role"] == "primary")
              & (det["window_series_key"] == window_series_key)]
    if symbol is not None:
        sel = sel[sel["symbol"] == symbol]
    if sel.empty:
        return sel
    sizes = sel.groupby(["arm", "model"]).size().sort_values(ascending=False, kind="stable")
    if len(sizes) > 1:
        ctx.warn(f"{window_series_key}/{symbol or 'all'}: several LLM arm/model groups {list(sizes.index)}; using the largest")
    arm, model = sizes.index[0]
    return sel[(sel["arm"] == arm) & (sel["model"] == model)]


# --------------------------------------------------------------------------- 4. ex0dte_decomposition.csv
DECOMPOSITION_COLUMNS = [
    "symbol", "scope", "year", "n_days", "mean_abs_net_full_bn", "mean_abs_net_ex0dte_bn", "abs_0dte_share_pct",
    "sign_flip_by_0dte_pct", "n_windows_full", "n_windows_ex0dte", "n_matched", "rate_full_pct",
    "rate_full_ci_lo_pct", "rate_full_ci_hi_pct", "rate_ex0dte_pct", "rate_ex0dte_ci_lo_pct", "rate_ex0dte_ci_hi_pct",
    "diff_pp", "n_full_only", "n_ex0dte_only", "llm_n_matched", "llm_rate_full_pct", "llm_rate_ex0dte_pct", "llm_diff_pp",
]
DECOMPOSITION_INT_COLUMNS = ["year", "n_days", "n_windows_full", "n_windows_ex0dte", "n_matched", "n_full_only",
                             "n_ex0dte_only", "llm_n_matched"]


def zero_dte_days(series: pd.DataFrame) -> pd.DataFrame:
    """Per (symbol, day) both net values and the 0DTE leg: the stored gex_0dte, else new_full - new_ex0dte."""
    full = series[series["series_key"] == FULL_SERIES][["symbol", "trading_date", "net_gex", "gex_0dte"]].rename(
        columns={"net_gex": "net_full", "gex_0dte": "zero_dte_full_row"})
    ex = series[series["series_key"] == ZERO_DTE_SERIES][["symbol", "trading_date", "net_gex", "gex_0dte"]].rename(
        columns={"net_gex": "net_ex0dte", "gex_0dte": "zero_dte_ex_row"})
    days = full.merge(ex, on=["symbol", "trading_date"])
    stored = days["zero_dte_ex_row"].fillna(days["zero_dte_full_row"])
    return days.assign(gex_0dte=stored.fillna(days["net_full"] - days["net_ex0dte"]),
                       gex_0dte_origin=np.where(stored.notna(), "stored", "difference"))


def decomposition_row(days: pd.DataFrame, win: pd.DataFrame, llm: pd.DataFrame, n_full: int, n_ex0dte: int) -> Dict[str, Any]:
    """One (symbol, scope) row: daily 0DTE share, matched-window classifier rates and matched LLM rates."""
    row: Dict[str, Any] = {"n_days": len(days), "n_windows_full": n_full, "n_windows_ex0dte": n_ex0dte, "n_matched": len(win)}
    if len(days):
        total = days["net_full"].abs().sum()
        row.update({
            "mean_abs_net_full_bn": days["net_full"].abs().mean() / 1e9,
            "mean_abs_net_ex0dte_bn": days["net_ex0dte"].abs().mean() / 1e9,
            "abs_0dte_share_pct": 100.0 * days["gex_0dte"].abs().sum() / total if total > 0 else math.nan,
            "sign_flip_by_0dte_pct": 100.0 * float(((days["net_full"] > 0) != (days["net_ex0dte"] > 0)).mean()),
        })
    if len(win):
        full, ex = win["clf_should_detect_full"].astype(bool), win["clf_should_detect_ex0dte"].astype(bool)
        for name, flags in (("full", full), ("ex0dte", ex)):
            fields = rate_fields(int(flags.sum()), len(flags))
            row.update({f"rate_{name}_pct": fields["rate_pct"], f"rate_{name}_ci_lo_pct": fields["ci_lo_pct"],
                        f"rate_{name}_ci_hi_pct": fields["ci_hi_pct"]})
        row.update({"diff_pp": 100.0 * (full.mean() - ex.mean()), "n_full_only": int((full & ~ex).sum()),
                    "n_ex0dte_only": int((~full & ex).sum())})
    if len(llm):
        full, ex = llm["label_full"].astype(bool), llm["label_ex0dte"].astype(bool)
        row.update({"llm_n_matched": len(llm), "llm_rate_full_pct": 100.0 * full.mean(),
                    "llm_rate_ex0dte_pct": 100.0 * ex.mean(), "llm_diff_pp": 100.0 * (full.mean() - ex.mean())})
    return row


def section_ex0dte_decomposition(ctx: Context) -> Dict[str, Any]:
    data = ctx.data
    series = data.series
    if not (series["series_key"] == ZERO_DTE_SERIES).any() and not (data.windows["series_key"] == ZERO_DTE_SERIES).any():
        raise SectionSkipped(f"no {ZERO_DTE_SERIES} series or windows")
    days = zero_dte_days(series)
    if days.empty:
        ctx.warn(f"ex0dte_decomposition: {FULL_SERIES} and {ZERO_DTE_SERIES} share no day; the 0DTE share columns are empty")
    elif (days["gex_0dte_origin"] == "difference").any():
        ctx.warn(f"ex0dte_decomposition: gex_0dte not stored on {int((days['gex_0dte_origin'] == 'difference').sum())} day(s); "
                 f"derived as {FULL_SERIES} - {ZERO_DTE_SERIES}")
    win = data.windows
    wfull = win[win["series_key"] == FULL_SERIES]
    wex = win[win["series_key"] == ZERO_DTE_SERIES]
    matched = wfull[["symbol", "window_end", "clf_should_detect"]].merge(
        wex[["symbol", "window_end", "clf_should_detect"]], on=["symbol", "window_end"], suffixes=("_full", "_ex0dte"))
    symbols = sorted(set(days["symbol"]) | set(wfull["symbol"]) | set(wex["symbol"]))
    rows: List[Dict[str, Any]] = []
    for symbol in symbols:
        llm_full = primary_llm_labels(ctx, FULL_SERIES, symbol)
        llm_ex = primary_llm_labels(ctx, ZERO_DTE_SERIES, symbol)
        llm = llm_full[["window_end", "regime_detected"]].merge(
            llm_ex[["window_end", "regime_detected"]], on="window_end", suffixes=("_full", "_ex0dte")).rename(
            columns={"regime_detected_full": "label_full", "regime_detected_ex0dte": "label_ex0dte"})
        parts = {"days": (days[days["symbol"] == symbol], "trading_date"), "win": (matched[matched["symbol"] == symbol], "window_end"),
                 "llm": (llm, "window_end"), "full": (wfull[wfull["symbol"] == symbol], "window_end"),
                 "ex": (wex[wex["symbol"] == symbol], "window_end")}
        years = sorted({int(y) for frame, col in parts.values() for y in frame[col].dt.year.dropna().unique()})
        for scope, year in [("year", y) for y in years] + [("all", None)]:
            sel = {name: (frame if year is None else frame[frame[col].dt.year == year]) for name, (frame, col) in parts.items()}
            rows.append({"symbol": symbol, "scope": scope, "year": year,
                         **decomposition_row(sel["days"], sel["win"], sel["llm"], len(sel["full"]), len(sel["ex"]))})
    if not rows:
        raise SectionSkipped("no symbol has new_full/new_ex0dte data")
    frame = sort_rows(pd.DataFrame(rows, columns=DECOMPOSITION_COLUMNS), ["symbol", "scope", "year"])
    ctx.write_csv("ex0dte_decomposition.csv", frame, DECOMPOSITION_INT_COLUMNS)
    yearly = frame[frame["scope"] == "year"]
    return {
        "rows": len(frame),
        "classifier_rate_pct_matched_by_year": {
            name: nest(yearly, ["symbol", "year"], column)
            for name, column in (("new_full", "rate_full_pct"), ("new_ex0dte", "rate_ex0dte_pct"))},
        "abs_0dte_share_pct_by_year": nest(yearly, ["symbol", "year"], "abs_0dte_share_pct"),
        "gex_0dte_origin": {k: int(v) for k, v in days["gex_0dte_origin"].value_counts().items()} if len(days) else {},
    }


# --------------------------------------------------------------------------- 5. post_publication_2026.csv
def post_publication_entry(group: pd.DataFrame, llm_columns: Sequence[str]) -> Dict[str, Any]:
    """Window count, window-end range, classifier rate, mean |GEX| and the LLM rates of one block of windows."""
    entry: Dict[str, Any] = {
        "n_windows": len(group), "window_end_first": group["window_end"].min(), "window_end_last": group["window_end"].max(),
        "clf_rate_pct": 100.0 * float(group["clf_should_detect"].astype(bool).mean()),
        "mean_abs_gex_bn": float(group["clf_avg_magnitude_bn"].mean())}
    for name in llm_columns:
        scored = group[group[f"llm_{name}"].notna()]
        if len(scored):
            entry[f"llm_{name}"] = {"n": len(scored), "rate_pct": 100.0 * float(scored[f"llm_{name}"].astype(bool).mean()),
                                    "agree_with_clf_pct": 100.0 * float((scored[f"llm_{name}"].astype(bool)
                                                                        == scored["clf_should_detect"].astype(bool)).mean())}
    return entry


POST_SUMMARY_COLUMNS = [
    "definition", "series_key", "symbol", "label_source", "arm", "model", "n_windows", "n_scored", "n_detect", "rate_pct",
    "ci_lo_pct", "ci_hi_pct", "agree_with_clf_pct", "window_end_first", "window_end_last", "mean_abs_gex_bn",
]
POST_SUMMARY_INT_COLUMNS = ["n_windows", "n_scored", "n_detect"]
# The two ways to delimit the post-publication windows (decision D-07): by the end of the window, or by its start as well.
POST_DEFINITIONS = ("ends_in_2026", "entirely_2026")


def post_summary_rows(series_key: str, symbol: str, group: pd.DataFrame,
                      labels: Mapping[str, Tuple[str, str]]) -> List[Dict[str, Any]]:
    """Classifier and LLM rates of one (series, symbol) block of 2026 windows under both definitions of the period.

    ``ends_in_2026`` = every window whose end is on or after 2026-01-01; ``entirely_2026`` = those that also start in 2026.
    ``labels`` maps the llm_<name> column of ``group`` to its (arm, model).
    """
    rows: List[Dict[str, Any]] = []
    for definition in POST_DEFINITIONS:
        sub = group if definition == "ends_in_2026" else group[group["entirely_2026"]]
        if sub.empty:
            continue
        shared = {"definition": definition, "series_key": series_key, "symbol": symbol, "n_windows": len(sub),
                  "window_end_first": sub["window_end"].min().date().isoformat(),
                  "window_end_last": sub["window_end"].max().date().isoformat(),
                  "mean_abs_gex_bn": float(sub["clf_avg_magnitude_bn"].mean())}
        clf = rate_fields(int(sub["clf_should_detect"].astype(bool).sum()), len(sub))
        rows.append({**shared, "label_source": "classifier", "arm": "", "model": "", "n_scored": clf["n"],
                     **{k: clf[k] for k in ("n_detect", "rate_pct", "ci_lo_pct", "ci_hi_pct")}})
        for name, (arm, model) in labels.items():
            scored = sub[sub[f"llm_{name}"].notna()]
            if scored.empty:
                continue
            label = scored[f"llm_{name}"].astype(bool)
            fields = rate_fields(int(label.sum()), len(scored))
            rows.append({**shared, "label_source": "llm", "arm": arm, "model": model, "n_scored": fields["n"],
                         **{k: fields[k] for k in ("n_detect", "rate_pct", "ci_lo_pct", "ci_hi_pct")},
                         "agree_with_clf_pct": 100.0 * float((label == scored["clf_should_detect"].astype(bool)).mean())})
    return rows


def section_post_publication(ctx: Context) -> Dict[str, Any]:
    win, det = ctx.data.windows, ctx.data.detections
    post = win[win["window_end"] >= POST_PUBLICATION_START]
    if post.empty:
        raise SectionSkipped(f"no windows ending on or after {POST_PUBLICATION_START.date()}")
    out = post.assign(clf_avg_magnitude_bn=post["clf_avg_magnitude"] / 1e9,
                      entirely_2026=post["window_start"] >= POST_PUBLICATION_START)[
        ["window_end", "window_start", "entirely_2026", "series_key", "symbol", "clf_regime_type", "clf_should_detect",
         "clf_avg_magnitude_bn", "clf_persistence_pct", "clf_sign_flips"]]
    labels = published_rows(det[det["parsed"] & det["arm_role"].isin(["primary", "backfill"])
                                & (det["window_end"] >= POST_PUBLICATION_START)])
    skipped_arms = sorted(set(det.loc[det["window_end"] >= POST_PUBLICATION_START, "arm"]) - set(labels["arm"]))
    models_per_arm = labels.groupby("arm")["model"].nunique()
    llm_columns: List[str] = []
    label_meta: Dict[str, Tuple[str, str]] = {}
    for (arm, model), group in sorted(labels.groupby(["arm", "model"]), key=lambda kv: _rank(kv[0][0], ARM_ORDER)):
        name = arm if models_per_arm[arm] == 1 else f"{arm}:{model}"
        renamed = group[["window_series_key", "symbol", "window_end", "regime_detected", "regime_type"]].rename(
            columns={"window_series_key": "series_key", "regime_detected": f"llm_{name}", "regime_type": f"llm_type_{name}"})
        out = out.merge(renamed, on=["series_key", "symbol", "window_end"], how="left")
        llm_columns.append(name)
        label_meta[name] = (arm, model)
    out = sort_rows(out, ["series_key", "symbol", "window_end"])
    blocks: List[Dict[str, Any]] = []
    summary_rows: List[Dict[str, Any]] = []
    for (series_key, symbol), group in out.groupby(["series_key", "symbol"], sort=False):
        entry: Dict[str, Any] = {"series_key": series_key, "symbol": symbol, **post_publication_entry(group, llm_columns)}
        whole = group[group["entirely_2026"]]
        entry["entirely_2026"] = post_publication_entry(whole, llm_columns) if len(whole) else None
        blocks.append(entry)
        summary_rows += post_summary_rows(series_key, symbol, group, label_meta)
    out = out.assign(window_end=out["window_end"].dt.strftime("%Y-%m-%d"), window_start=out["window_start"].dt.strftime("%Y-%m-%d"))
    ctx.write_csv("post_publication_2026.csv", out, ["clf_sign_flips"])
    summary = sort_rows(pd.DataFrame(summary_rows, columns=POST_SUMMARY_COLUMNS),
                        ["series_key", "symbol", "definition", "label_source", "arm", "model"])
    ctx.write_csv("post_publication_2026_summary.csv", summary, POST_SUMMARY_INT_COLUMNS)
    return {"rows": len(out), "label": "post-publication period (not out-of-sample: gpt-6-luna was created 2026-09-14)",
            "definition": f"window_end on or after {POST_PUBLICATION_START.date()} (ends_in_2026); entirely_2026 = window_start on "
                          f"or after {POST_PUBLICATION_START.date()} as well (the windows the paper tabulates); "
                          "post_publication_2026_summary.csv has the rates under both definitions",
            "by_series": blocks, "arms_excluded_from_columns": skipped_arms}


# --------------------------------------------------------------------------- 6. intraday.csv
INTRADAY_COLUMNS = [
    "window_end", "symbol", "irregular_day", "gex_t0_final_rush_bn", "gex_t0_eod_bn", "gex_t0_diff_bn",
    "clf_intraday", "clf_full", "clf_agree", "clf_type_intraday", "clf_type_full",
    "mean_abs_gex_intraday_bn", "mean_abs_gex_full_bn", "llm_intraday", "llm_full", "llm_agree",
]


def section_intraday(ctx: Context) -> Dict[str, Any]:
    data = ctx.data
    win = data.windows
    t0 = win[win["series_key"] == INTRADAY_COMPOSITE]
    if t0.empty:
        raise SectionSkipped(f"no {INTRADAY_COMPOSITE} windows")
    full = win[win["series_key"] == FULL_SERIES]
    frame = t0[["symbol", "window_end", "clf_should_detect", "clf_regime_type", "clf_avg_magnitude"]].rename(columns={
        "clf_should_detect": "clf_intraday", "clf_regime_type": "clf_type_intraday",
        "clf_avg_magnitude": "mean_abs_gex_intraday_bn"}).merge(
        full[["symbol", "window_end", "clf_should_detect", "clf_regime_type", "clf_avg_magnitude"]].rename(columns={
            "clf_should_detect": "clf_full", "clf_regime_type": "clf_type_full", "clf_avg_magnitude": "mean_abs_gex_full_bn"}),
        on=["symbol", "window_end"], how="left")
    if frame["clf_full"].isna().all():
        raise SectionSkipped(f"{INTRADAY_COMPOSITE} and {FULL_SERIES} windows share no window_end")
    frame[["mean_abs_gex_intraday_bn", "mean_abs_gex_full_bn"]] /= 1e9
    for column, key in (("gex_t0_final_rush_bn", "intraday_late"), ("gex_t0_eod_bn", FULL_SERIES)):
        values = data.series[data.series["series_key"] == key][["symbol", "trading_date", "net_gex"]].rename(
            columns={"trading_date": "window_end", "net_gex": column})
        frame = frame.merge(values, on=["symbol", "window_end"], how="left")
    frame[["gex_t0_final_rush_bn", "gex_t0_eod_bn"]] /= 1e9
    frame["gex_t0_diff_bn"] = frame["gex_t0_final_rush_bn"] - frame["gex_t0_eod_bn"]
    frame["irregular_day"] = frame["window_end"].isin(pd.to_datetime(list(common.INTRADAY_EXCLUDE_DAYS)))
    frame["clf_agree"] = frame["clf_intraday"] == frame["clf_full"]
    symbols = sorted(frame["symbol"].unique())
    for column, key in (("llm_intraday", INTRADAY_COMPOSITE), ("llm_full", FULL_SERIES)):
        scored = pd.concat([primary_llm_labels(ctx, key, s) for s in symbols], ignore_index=True)
        frame = frame.merge(scored[["symbol", "window_end", "regime_detected"]].rename(columns={"regime_detected": column}),
                            on=["symbol", "window_end"], how="left")
    frame["llm_agree"] = frame["llm_intraday"] == frame["llm_full"]
    frame = sort_rows(frame, ["symbol", "window_end"])[INTRADAY_COLUMNS]
    ctx.write_csv("intraday.csv", frame.assign(window_end=frame["window_end"].dt.strftime("%Y-%m-%d")), [])
    regular = frame[~frame["irregular_day"]]
    clf = regular["clf_agree"].dropna().astype(bool)
    llm = regular["llm_agree"].dropna().astype(bool)
    values = regular.dropna(subset=["gex_t0_diff_bn"])
    return {
        "rows": len(frame), "irregular_days": [d.isoformat() for d in common.INTRADAY_EXCLUDE_DAYS],
        "n_irregular_flagged": int(frame["irregular_day"].sum()), "n_regular_windows": len(regular),
        "n_clf_compared": len(clf), "clf_agree_pct": 100.0 * clf.mean() if len(clf) else None,
        "n_llm_compared": len(llm), "llm_agree_pct": 100.0 * llm.mean() if len(llm) else None,
        "n_t0_values": len(values),
        "t0_mean_abs_diff_bn": values["gex_t0_diff_bn"].abs().mean() if len(values) else None,
        "t0_sign_agree_pct": (100.0 * ((values["gex_t0_final_rush_bn"] > 0) == (values["gex_t0_eod_bn"] > 0)).mean()
                              if len(values) else None),
    }


# --------------------------------------------------------------------------- 7. stats.yaml
@dataclass(frozen=True)
class Labeller:
    """A source of window labels: the deterministic classifier on one series, or one LLM arm/model."""

    kind: str  # "classifier" or "llm"
    series_key: str
    symbol: str
    arm: str = ""
    model: str = ""

    def describe(self) -> Dict[str, Any]:
        return {"kind": self.kind, "series_key": self.series_key, "symbol": self.symbol,
                "arm": self.arm or None, "model": self.model or None}

    def sort_key(self) -> Tuple[str, str, str, str, str]:
        return (self.kind, _rank(self.series_key, SERIES_ORDER), self.symbol, _rank(self.arm, ARM_ORDER), self.model)


def labelled_windows(data: Data) -> Dict[Labeller, pd.DataFrame]:
    """{labeller: windows ordered by window_end with columns window_start, window_end, label (0/1)}.

    Classifier labels come from the windows table; LLM labels from parsed, non-repeat detections of registered
    (primary) arms and of the published r1_o4mini backfill (the answers recovered in 2026 are left out).  A detection
    without a stored window has no window_start.
    """
    out: Dict[Labeller, pd.DataFrame] = {}
    for (series_key, symbol), group in data.windows.groupby(["series_key", "symbol"]):
        out[Labeller("classifier", series_key, symbol)] = pd.DataFrame({
            "window_start": group["window_start"], "window_end": group["window_end"],
            "label": group["clf_should_detect"].astype(int)}).sort_values("window_end").reset_index(drop=True)
    det = data.detections
    scored = published_rows(det[det["parsed"] & (det["repeat_index"] == 0) & det["arm_role"].isin(["primary", "backfill"])])
    for (arm, model, series_key, symbol), group in scored.groupby(["arm", "model", "series_key", "symbol"]):
        out[Labeller("llm", series_key, symbol, arm, model)] = pd.DataFrame({
            "window_start": group["window_start"], "window_end": group["window_end"],
            "label": group["regime_detected"].astype(int)}).sort_values("window_end").reset_index(drop=True)
    return out


def slice_years(frame: pd.DataFrame, first: Optional[int], last: Optional[int]) -> pd.DataFrame:
    """Windows whose end falls in years first..last; ``None`` for both keeps every window (period 'all')."""
    if first is None or last is None:
        return frame
    years = frame["window_end"].dt.year
    return frame[(years >= first) & (years <= last)]


def nonoverlap_summary(frame: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Rate on windows that share no day (greedy from the first window) and its spread over the 30 possible starts."""
    f = frame.dropna(subset=["window_start"]).sort_values("window_end")
    if f.empty:
        return None
    starts, ends = (f[c].to_numpy("datetime64[D]") for c in ("window_start", "window_end"))
    labels = f["label"].to_numpy()
    chains = [nonoverlap_indices(starts, ends, first) for first in range(min(common.WINDOW_DAYS, len(f)))]
    rates = [100.0 * labels[chain].mean() for chain in chains]
    n, k = len(chains[0]), int(labels[chains[0]].sum())
    lo, hi = wilson_pct(k, n)
    return {"n": n, "k": k, "rate_pct": 100.0 * k / n, "wilson_ci_pct": [lo, hi],
            "n_starts": len(chains), "rate_pct_range_over_starts": [min(rates), max(rates)]}


def rate_entry(frame: pd.DataFrame, ctx: Context) -> Dict[str, Any]:
    """Rate of a label over a set of windows with Wilson, quarter-block bootstrap and non-overlapping subsample."""
    n, k = len(frame), int(frame["label"].sum())
    fields = rate_fields(k, n)
    blocks = block_sums(frame.assign(n=1), ["n", "label"])
    sums = resample_block_sums(blocks, ctx.n_boot, np.random.default_rng(ctx.seed))
    lo, hi = percentile_interval(100.0 * sums[:, 1] / sums[:, 0])
    return {"n": n, "k": k, "rate_pct": fields["rate_pct"], "wilson_ci_pct": [fields["ci_lo_pct"], fields["ci_hi_pct"]],
            "bootstrap_quarter": {"n_blocks": int(blocks.shape[0]), "n_draws": ctx.n_boot, "ci_pct": [lo, hi]},
            "nonoverlap_30d": nonoverlap_summary(frame)}


def paired_entry(lab_a: Labeller, lab_b: Labeller, fa: pd.DataFrame, fb: pd.DataFrame, period: str,
                 ctx: Context, family: str = "series") -> Optional[Dict[str, Any]]:
    """Difference in detection rate between two series on the windows they share (a minus b), paired by window.

    ``family`` says what the two series differ in: series (data lineage), label (Day-T labels vs dates) or scale.
    """
    pair = fa.merge(fb, on="window_end", suffixes=("_a", "_b")).sort_values("window_end").reset_index(drop=True)
    if pair.empty:
        return None
    a, b = pair["label_a"].to_numpy(bool), pair["label_b"].to_numpy(bool)
    n, only_a, only_b = len(pair), int((a & ~b).sum()), int((~a & b).sum())
    cells = pair.assign(n=1, ka=a.astype(int), kb=b.astype(int))
    blocks = block_sums(cells, ["n", "ka", "kb"])
    sums = resample_block_sums(blocks, ctx.n_boot, np.random.default_rng(ctx.seed))
    diff_draws = 100.0 * (sums[:, 1] - sums[:, 2]) / sums[:, 0]
    lo, hi = percentile_interval(diff_draws)
    entry: Dict[str, Any] = {
        "name": "series_contrast", "family": family, "design": "paired by window_end (windows present in both series)",
        "period": period,
        "a": lab_a.describe(), "b": lab_b.describe(), "n_common_windows": n,
        "rate_a_pct": 100.0 * a.mean(), "rate_a_wilson_ci_pct": list(wilson_pct(int(a.sum()), n)),
        "rate_b_pct": 100.0 * b.mean(), "rate_b_wilson_ci_pct": list(wilson_pct(int(b.sum()), n)),
        "diff_pp": 100.0 * (a.mean() - b.mean()), "windows_only_a": only_a, "windows_only_b": only_b,
        "naive_stride1": {"p_mcnemar_exact": mcnemar_exact(only_a, only_b),
                          "caveat": "treats overlapping windows as independent; anti-conservative"},
        "bootstrap_quarter": {"n_blocks": int(blocks.shape[0]), "n_draws": ctx.n_boot, "diff_ci_pp": [lo, hi],
                              "p_two_sided": bootstrap_p_value(diff_draws)},
        "nonoverlap_30d": None,
    }
    chain_frame = pair.assign(window_start=pair[["window_start_a", "window_start_b"]].min(axis=1)).dropna(subset=["window_start"])
    if len(chain_frame):
        chain = nonoverlap_indices(chain_frame["window_start"].to_numpy("datetime64[D]"),
                                   chain_frame["window_end"].to_numpy("datetime64[D]"))
        sa, sb = chain_frame["label_a"].to_numpy(bool)[chain], chain_frame["label_b"].to_numpy(bool)[chain]
        entry["nonoverlap_30d"] = {
            "n": len(chain), "rate_a_pct": 100.0 * sa.mean(), "rate_b_pct": 100.0 * sb.mean(),
            "diff_pp": 100.0 * (sa.mean() - sb.mean()), "windows_only_a": int((sa & ~sb).sum()),
            "windows_only_b": int((~sa & sb).sum()),
            "p_mcnemar_exact": mcnemar_exact(int((sa & ~sb).sum()), int((~sa & sb).sum()))}
    return entry


def shift_entry(lab: Labeller, early: pd.DataFrame, late: pd.DataFrame, ctx: Context, name: str = "period_shift",
                early_name: str = SHIFT_EARLY, late_name: str = SHIFT_LATE,
                extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Difference in detection rate between two groups of windows (late minus early), unpaired.

    ``period_shift`` compares two periods of one label source; ``phase_contrast`` (``extra`` names both labellers) compares
    two series, for example Phase 3 (2024) against Phase 4 (2020), with the same kind of label source and model.
    """
    n0, k0, n1, k1 = len(early), int(early["label"].sum()), len(late), int(late["label"].sum())
    rng = np.random.default_rng(ctx.seed)
    blocks0, blocks1 = (block_sums(f.assign(n=1), ["n", "label"]) for f in (early, late))
    s0, s1 = (resample_block_sums(blocks, ctx.n_boot, rng) for blocks in (blocks0, blocks1))
    diff_draws = 100.0 * (s1[:, 1] / s1[:, 0] - s0[:, 1] / s0[:, 0])
    lo, hi = percentile_interval(diff_draws)
    new_lo, new_hi = newcombe_difference(k1, n1, k0, n0)
    sub0, sub1 = nonoverlap_summary(early), nonoverlap_summary(late)
    return {
        "name": name, "design": "unpaired", "period": f"{late_name} vs {early_name}",
        "early": early_name, "late": late_name, **(extra if extra is not None else {"labeller": lab.describe()}),
        "n_early": n0, "rate_early_pct": 100.0 * k0 / n0, "rate_early_wilson_ci_pct": list(wilson_pct(k0, n0)),
        "n_late": n1, "rate_late_pct": 100.0 * k1 / n1, "rate_late_wilson_ci_pct": list(wilson_pct(k1, n1)),
        "diff_pp": 100.0 * (k1 / n1 - k0 / n0), "newcombe_wilson_ci_pp": [new_lo, new_hi],
        "phi": phi_coefficient(k1, n1, k0, n0),
        "naive_stride1": {"p_fisher_exact": fisher_p(k1, n1, k0, n0),
                          "caveat": "treats overlapping windows as independent; anti-conservative"},
        "bootstrap_quarter": {"n_blocks_early": int(blocks0.shape[0]), "n_blocks_late": int(blocks1.shape[0]),
                              "n_draws": ctx.n_boot, "diff_ci_pp": [lo, hi], "p_two_sided": bootstrap_p_value(diff_draws)},
        "nonoverlap_30d": None if sub0 is None or sub1 is None else {
            "n_early": sub0["n"], "n_late": sub1["n"], "rate_early_pct": sub0["rate_pct"], "rate_late_pct": sub1["rate_pct"],
            "diff_pp": sub1["rate_pct"] - sub0["rate_pct"],
            "p_fisher_exact": fisher_p(sub1["k"], sub1["n"], sub0["k"], sub0["n"])},
    }


def matched_labellers(ordered: Sequence[Labeller], series_a: str, series_b: str) -> Iterator[Tuple[Labeller, Labeller]]:
    """(label source on series a, the same kind of label source on series b) for the same symbol.

    A classifier pairs with the classifier; an LLM arm pairs with an LLM arm of the same model, so a contrast holds the
    labeller fixed and changes only the windows.
    """
    for lab_a in (lab for lab in ordered if lab.series_key == series_a):
        for lab_b in (lab for lab in ordered if (lab.series_key, lab.symbol, lab.kind) == (series_b, lab_a.symbol, lab_a.kind)):
            if lab_a.kind == "llm" and lab_a.model != lab_b.model:
                continue
            yield lab_a, lab_b


def headline_entry(contrast: Dict[str, Any]) -> Dict[str, Any]:
    """The line of a contrast that the abstract and the results tables quote."""
    nonoverlap = contrast["nonoverlap_30d"] or {}
    return {"name": contrast["name"], "family": contrast.get("family"), "period": contrast["period"],
            "a": contrast.get("a") or contrast["labeller"], "b": contrast.get("b"), "diff_pp": contrast["diff_pp"],
            "bootstrap_diff_ci_pp": contrast["bootstrap_quarter"]["diff_ci_pp"],
            "p_bootstrap": contrast["bootstrap_quarter"]["p_two_sided"],
            "p_nonoverlap": nonoverlap.get("p_mcnemar_exact", nonoverlap.get("p_fisher_exact"))}


def is_headline(contrast: Dict[str, Any]) -> bool:
    """Period shifts, Phase 3 vs 4, the label (date) and scale contrasts, and the data-lineage contrasts for 2024-2025."""
    return (contrast["name"] in ("period_shift", "phase_contrast") or contrast.get("family") in ("label", "scale")
            or contrast["period"] == "2024-2025")


def section_stats(ctx: Context) -> Dict[str, Any]:
    labelled = labelled_windows(ctx.data)
    if not labelled:
        raise SectionSkipped("no windows and no parsed detections")
    ordered = sorted(labelled, key=Labeller.sort_key)
    spans = {name: (first, last) for name, first, last in PERIODS}
    rates: List[Dict[str, Any]] = []
    for lab in ordered:
        for period, (first, last) in spans.items():
            frame = slice_years(labelled[lab], first, last)
            if len(frame):
                rates.append({"labeller": lab.describe(), "period": period, **rate_entry(frame, ctx)})
    contrasts: List[Dict[str, Any]] = []
    for series_a, series_b, family, periods in SERIES_CONTRASTS:
        for lab_a, lab_b in matched_labellers(ordered, series_a, series_b):
            for period in periods:
                first, last = spans[period]
                entry = paired_entry(lab_a, lab_b, slice_years(labelled[lab_a], first, last),
                                     slice_years(labelled[lab_b], first, last), period, ctx, family)
                if entry:
                    contrasts.append(entry)
    for lab in ordered:
        early, late = (slice_years(labelled[lab], *spans[p]) for p in (SHIFT_EARLY, SHIFT_LATE))
        if len(early) and len(late):
            contrasts.append(shift_entry(lab, early, late, ctx))
    for late_series, early_series in PHASE_CONTRASTS:
        for lab_late, lab_early in matched_labellers(ordered, late_series, early_series):
            late, early = labelled[lab_late], labelled[lab_early]
            if len(late) and len(early):
                contrasts.append(shift_entry(lab_late, early, late, ctx, name="phase_contrast", early_name=early_series,
                                             late_name=late_series,
                                             extra={"a": lab_late.describe(), "b": lab_early.describe()}))
    if not rates:
        raise SectionSkipped("no window ends in 2020-2025")
    if not contrasts:
        ctx.warn("stats: no series contrast or period shift could be formed from the available windows")
    headline = [headline_entry(c) for c in contrasts if is_headline(c)]
    ctx.write_yaml("stats.yaml", {
        "meta": {
            "seed": ctx.seed, "n_boot": ctx.n_boot, "ci_level": CI_LEVEL, "primary_label": "regime_detected / clf_should_detect",
            "periods": {name: ("every window" if first is None else f"window_end years {first}-{last}")
                        for name, (first, last) in spans.items()},
            "wilson": "Wilson score interval; treats stride-1 windows as independent, so it is too narrow",
            "bootstrap_quarter": "resamples calendar quarters of window_end with replacement (paired contrasts resample the same "
                                 "quarters for both series); percentile interval; p = 2 min(P(d<=0), P(d>=0)), bounded below by 1/(draws+1); "
                                 "intervals from fewer than ~8 blocks are coarse",
            "nonoverlap_30d": "greedy chain of windows that share no day, from the first window of the period; "
                              "rate_pct_range_over_starts is the min/max over the 30 possible first windows",
            "series_contrast": "a minus b on windows present in both series; LLM contrasts hold the model fixed; family = series "
                               "(data lineage), label (a: Day-T labels, b: the dates sent in Nov 2025, same values) or scale "
                               "(a: OI-notional-scaled values, b: stored values)",
            "period_shift": f"{SHIFT_LATE} minus {SHIFT_EARLY} for one label source; phi is signed (late vs early)",
            "phase_contrast": "Phase 3 (2024) minus Phase 4 (2020) for one kind of label source and model, unpaired "
                              "(late = a, early = b); phi is signed",
            "headline_contrasts": "the contrasts the text quotes: period shifts, Phase 3 vs 4, label and scale contrasts, and "
                                  "the series contrasts for 2024-2025",
        },
        "headline_contrasts": headline, "rates": rates, "contrasts": contrasts})
    return {"rates": len(rates), "contrasts": len(contrasts), "headline_contrasts": headline}


# --------------------------------------------------------------------------- 8. cost_ledger.csv / .yaml
COST_COLUMNS = [
    "run_id", "arm", "series_key", "symbol", "model", "mode", "status", "budget_class", "counts_toward_budget", "n_requests",
    "n_responses", "n_parsed", "n_failed", "prompt_tokens", "completion_tokens", "reasoning_tokens", "est_cost_usd",
    "recomputed_cost_usd", "cost_gap_usd", "cost_per_request_usd", "prompt_tokens_per_response",
    "completion_tokens_per_response", "reasoning_tokens_per_response", "n_detections", "detection_prompt_tokens",
    "detection_completion_tokens", "prompt_token_gap", "completion_token_gap", "submitted_at", "completed_at", "ingested_at",
    "git_sha",
]
COST_INT_COLUMNS = ["n_requests", "n_responses", "n_parsed", "n_failed", "prompt_tokens", "completion_tokens",
                    "reasoning_tokens", "n_detections", "detection_prompt_tokens", "detection_completion_tokens",
                    "prompt_token_gap", "completion_token_gap"]
BUDGET_CLASSES = ("current", "generated", "backfill", "other_model")
IN_FLIGHT_STATUSES = ("submitted", "in_progress", "completed")  # as 04_llm_runner.IN_FLIGHT: the batch is out, spend not yet measured


def recompute_cost(run: pd.Series) -> float:
    """Token usage priced with common.PRICING_USD_PER_MTOK (batch for batch runs, standard for sync); NaN if unknown."""
    if pd.isna(run["prompt_tokens"]) or pd.isna(run["completion_tokens"]):
        return math.nan
    try:
        return common.estimate_cost_usd(run["model"], "batch" if run["mode"] == "batch" else "standard",
                                        run["prompt_tokens"], run["completion_tokens"])
    except KeyError:
        return math.nan


def budget_class(run: pd.Series) -> str:
    """How a run enters the budget ledger (common.counts_toward_budget decides what counts).

    * ``current``     - counted and sent: spend from the present OpenAI balance (measured ``est_cost_usd``);
    * ``generated``   - counted but only generated: no request left the machine, no cost;
    * ``backfill``    - a backfilled published run (arm with llm=False, or run_metadata ``backfill``): an earlier billing
                        period, shown separately and never counted as spend;
    * ``other_model`` - any other run that ``counts_toward_budget`` refuses (a model other than ``common.MODEL``).
    """
    meta = as_mapping(run["run_metadata"])
    if common.counts_toward_budget({"arm": run["arm"], "model": run["model"], "run_metadata": meta}):
        return "generated" if run["status"] == "generated" else "current"
    registered = registered_arm(run["arm"])
    return "backfill" if (registered is not None and not registered.llm) or meta.get("backfill") else "other_model"


def totals_of(frame: pd.DataFrame) -> Dict[str, Any]:
    """Run, request, token and cost totals of a block of ledger rows (cost per request over the rows that have a cost)."""
    costed = frame[frame["est_cost_usd"].notna()]
    requests = costed["n_requests"].sum()
    return {"runs": len(frame), "n_requests": frame["n_requests"].sum(), "prompt_tokens": frame["prompt_tokens"].sum(),
            "completion_tokens": frame["completion_tokens"].sum(), "reasoning_tokens": frame["reasoning_tokens"].sum(),
            "est_cost_usd": frame["est_cost_usd"].sum(),
            "cost_per_request_usd": float(costed["est_cost_usd"].sum() / requests) if requests else None}


def cost_groups(ledger: pd.DataFrame, key: str) -> List[Dict[str, Any]]:
    """Runs, requests, tokens and cost per value of ``key``; ``est_cost_usd_counted`` is the part that counts as spend."""
    frame = ledger.assign(counted_cost=ledger["est_cost_usd"].where(ledger["budget_class"] == "current"))
    grouped = frame.groupby(key, sort=True, dropna=False).agg(
        runs=("run_id", "size"), n_requests=("n_requests", "sum"), prompt_tokens=("prompt_tokens", "sum"),
        completion_tokens=("completion_tokens", "sum"), est_cost_usd=("est_cost_usd", lambda s: s.sum(min_count=1)),
        est_cost_usd_counted=("counted_cost", lambda s: s.sum(min_count=1)))
    grouped["cost_per_request_usd"] = grouped["est_cost_usd"] / grouped["n_requests"].where(grouped["n_requests"] > 0)
    return grouped.reset_index().to_dict("records")


def section_cost_ledger(ctx: Context) -> Dict[str, Any]:
    runs = ctx.data.runs
    if runs.empty:
        raise SectionSkipped("no runs rows")
    det = ctx.data.detections
    usage = det.groupby("run_id").agg(
        n_detections=("arm", "size"), detection_prompt_tokens=("prompt_tokens", lambda s: s.sum(min_count=1)),
        detection_completion_tokens=("completion_tokens", lambda s: s.sum(min_count=1))).reset_index()
    ledger = runs.merge(usage, on="run_id", how="left")
    responded = ledger["n_responses"].where(ledger["n_responses"] > 0)
    ledger = ledger.assign(
        budget_class=ledger.apply(budget_class, axis=1),
        recomputed_cost_usd=ledger.apply(recompute_cost, axis=1),
        cost_per_request_usd=ledger["est_cost_usd"] / ledger["n_requests"].where(ledger["n_requests"] > 0),
        prompt_tokens_per_response=ledger["prompt_tokens"] / responded,
        completion_tokens_per_response=ledger["completion_tokens"] / responded,
        reasoning_tokens_per_response=ledger["reasoning_tokens"] / responded,
        prompt_token_gap=ledger["prompt_tokens"] - ledger["detection_prompt_tokens"],
        completion_token_gap=ledger["completion_tokens"] - ledger["detection_completion_tokens"])
    ledger["counts_toward_budget"] = ledger["budget_class"].isin(["current", "generated"])
    ledger["cost_gap_usd"] = ledger["est_cost_usd"] - ledger["recomputed_cost_usd"]
    projected = pd.to_numeric(ledger["run_metadata"].map(lambda meta: as_mapping(meta).get("projected_cost_usd")), errors="coerce")
    stamps = ledger.assign(**{c: ledger[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ") for c in ("submitted_at", "completed_at", "ingested_at")})
    frame = sort_rows(stamps, ["arm", "submitted_at", "run_id"])[COST_COLUMNS]
    ctx.write_csv("cost_ledger.csv", frame, COST_INT_COLUMNS)
    block = {name: ledger[ledger["budget_class"] == name] for name in BUDGET_CLASSES}
    spent = float(block["current"]["est_cost_usd"].sum())
    flying = block["current"][block["current"]["status"].isin(IN_FLIGHT_STATUSES) & block["current"]["est_cost_usd"].isna()]
    in_flight = float(projected[flying.index].sum())
    generated = float(projected[block["generated"].index].sum())
    no_cost = runs.loc[runs["est_cost_usd"].isna(), "run_id"].tolist()
    reconciled = frame.dropna(subset=["prompt_token_gap", "completion_token_gap"])
    payload = {
        "currency": "USD",
        "pricing_usd_per_mtok": {m: {mode: {"input": p[0], "output": p[1]} for mode, p in modes.items()}
                                 for m, modes in common.PRICING_USD_PER_MTOK.items()},
        "budget": {
            "rule": f"a run is spend when common.counts_toward_budget(run) holds (model {common.MODEL}, an LLM arm or an arm "
                    "outside the registry, no run_metadata 'backfill') and it has left the machine (status not 'generated'); "
                    "the backfill of the published o4-mini batch of January 2026 (arm r1_o4mini; likewise r1_p3_o4mini and "
                    "r1_p4_o4mini) is shown separately under not_spend and is never counted",
            "hard_stop_usd": common.BUDGET_USD_HARD_STOP,
            "spent_usd": spent, "in_flight_projected_usd": in_flight, "committed_usd": spent + in_flight,
            "remaining_to_hard_stop_usd": common.BUDGET_USD_HARD_STOP - spent - in_flight,
            "generated_not_sent_projected_usd": generated,
            "not_spend": {
                "historical_backfill_usd": float(block["backfill"]["est_cost_usd"].sum()),
                "historical_backfill_runs": sorted(block["backfill"]["run_id"]),
                "other_model_usd": float(block["other_model"]["est_cost_usd"].sum()),
                "other_model_runs": sorted(block["other_model"]["run_id"])},
        },
        "totals": {"counted": totals_of(block["current"]), "backfill": totals_of(block["backfill"]),
                   "other_model": totals_of(block["other_model"]), "all_stored_runs": totals_of(ledger)},
        "by_arm": cost_groups(ledger, "arm"), "by_model": cost_groups(ledger, "model"),
        "by_mode": cost_groups(ledger, "mode"), "by_status": cost_groups(ledger, "status"),
        "runs_without_est_cost": no_cost,
        "reconciliation": {
            "runs_compared_with_detection_usage": len(reconciled),
            "runs_with_token_gap": int(((reconciled["prompt_token_gap"] != 0) | (reconciled["completion_token_gap"] != 0)).sum()),
            "max_abs_cost_gap_usd": frame["cost_gap_usd"].abs().max() if frame["cost_gap_usd"].notna().any() else None,
            "note": "gaps compare the run totals with the sum over that run's detection rows; cost_gap_usd compares "
                    "est_cost_usd with the token usage priced by common.PRICING_USD_PER_MTOK",
        },
    }
    ctx.write_yaml("cost_ledger.yaml", payload)
    counted = payload["totals"]["counted"]
    return {"rows": len(frame), "est_cost_usd": spent, "spent_usd": spent, "committed_usd": spent + in_flight,
            "remaining_to_hard_stop_usd": payload["budget"]["remaining_to_hard_stop_usd"],
            "historical_backfill_usd": payload["budget"]["not_spend"]["historical_backfill_usd"],
            "est_cost_usd_all_stored_runs": payload["totals"]["all_stored_runs"]["est_cost_usd"],
            "cost_per_request_usd": counted["cost_per_request_usd"]}


# --------------------------------------------------------------------------- 9. disagreements.csv
DISAGREEMENT_COLUMNS = [
    "arm", "arm_role", "model", "series_key", "symbol", "window_end", "window_start", "llm_detected", "clf_detected",
    "llm_type", "clf_type", "confidence", "llm_positive_days", "clf_positive_days", "llm_avg_magnitude_bn",
    "clf_avg_magnitude_bn", "llm_persistence_pct", "clf_persistence_pct", "llm_sign_flips", "clf_sign_flips",
    "metrics_agree", "finish_reason",
]
DISAGREEMENT_INT_COLUMNS = ["llm_positive_days", "clf_positive_days", "llm_sign_flips", "clf_sign_flips"]


def section_disagreements(ctx: Context) -> Dict[str, Any]:
    """Every parsed answer of a registered arm (and of the published backfill) whose verdict differs from the classifier's."""
    det = ctx.data.detections
    scored = published_rows(det[det["parsed"] & (det["repeat_index"] == 0) & det["arm_role"].isin(["primary", "backfill"])
                                & det["clf_should_detect"].notna()])
    if scored.empty:
        raise SectionSkipped("no parsed answer of a registered arm has a stored window to compare with")
    differs = scored["regime_detected"].astype(bool) != scored["clf_should_detect"].astype(bool)
    wrong = scored[differs]
    out = pd.DataFrame({
        "arm": wrong["arm"], "arm_role": wrong["arm_role"], "model": wrong["model"], "series_key": wrong["series_key"],
        "symbol": wrong["symbol"], "window_end": wrong["window_end"], "window_start": wrong["window_start"],
        "llm_detected": wrong["regime_detected"].astype(bool), "clf_detected": wrong["clf_should_detect"].astype(bool),
        "llm_type": wrong["regime_type"], "clf_type": wrong["clf_regime_type"], "confidence": wrong["confidence"],
        "llm_positive_days": wrong["positive_days"], "clf_positive_days": wrong["clf_positive_days"],
        "llm_avg_magnitude_bn": wrong["avg_magnitude_billions"], "clf_avg_magnitude_bn": wrong["clf_avg_magnitude"] / 1e9,
        "llm_persistence_pct": wrong["persistence_pct"], "clf_persistence_pct": wrong["clf_persistence_pct"],
        "llm_sign_flips": wrong["sign_flips"], "clf_sign_flips": wrong["clf_sign_flips"],
        "metrics_agree": wrong["metrics_agree"], "finish_reason": wrong["finish_reason"]}, columns=DISAGREEMENT_COLUMNS)
    out = sort_rows(out, ["arm", "series_key", "symbol", "window_end"])
    ctx.write_csv("disagreements.csv", out.assign(window_end=out["window_end"].dt.strftime("%Y-%m-%d"),
                                                  window_start=out["window_start"].dt.strftime("%Y-%m-%d")),
                  DISAGREEMENT_INT_COLUMNS)
    per_arm = scored.assign(disagree=differs).groupby(["arm", "model", "series_key", "symbol"], sort=True)["disagree"].agg(
        n_scored="size", n_disagree="sum").reset_index()
    per_arm["disagree_pct"] = 100.0 * per_arm["n_disagree"] / per_arm["n_scored"]
    return {"rows": len(out), "by_arm": sort_rows(per_arm, ["arm", "series_key", "symbol"]).to_dict("records")}


# --------------------------------------------------------------------------- 10. llm_parse_stats.csv
PARSE_COLUMNS = [
    "arm", "arm_role", "model", "series_key", "symbol", "n_rows", "n_parsed", "parsed_pct", "n_ok", "n_fallback", "n_failed",
    "n_missing", "n_other_status", "n_finish_stop", "n_finish_length", "n_finish_other", "n_finish_unknown",
    "n_rerun_at_retry_cap", "n_recovered_2026", "mean_prompt_tokens", "mean_completion_tokens",
    "max_completion_tokens_used", "mean_reasoning_tokens",
]
PARSE_INT_COLUMNS = ["n_rows", "n_parsed", "n_ok", "n_fallback", "n_failed", "n_missing", "n_other_status", "n_finish_stop",
                     "n_finish_length", "n_finish_other", "n_finish_unknown", "n_rerun_at_retry_cap", "n_recovered_2026"]


def section_llm_parse_stats(ctx: Context) -> Dict[str, Any]:
    """Parse status, finish reason and token use of every stored answer, per arm (repeats and the backfill included).

    ``n_rerun_at_retry_cap`` counts the stored answers whose run asked for ``RETRY_MAX_COMPLETION_TOKENS``: the
    answers that were cut off at the first cap and regenerated by the runner's ``retry`` command (empty when the
    runs table does not say).
    """
    det = ctx.data.detections
    if det.empty:
        raise SectionSkipped("no detections")
    runs = ctx.data.runs
    cap = runs.set_index("run_id")["max_completion_tokens"] if len(runs) else pd.Series(dtype=float)
    det = det.assign(request_cap=det["run_id"].map(cap))
    rows = []
    for (arm, model, series_key, symbol), group in det.groupby(["arm", "model", "series_key", "symbol"], sort=True):
        status = group["parse_status"].value_counts()
        finish = group["finish_reason"]
        counts = {name: int(status.get(name, 0)) for name in ("ok", "fallback", "failed", "missing")}
        rows.append({
            "arm": arm, "arm_role": arm_role(arm), "model": model, "series_key": series_key, "symbol": symbol,
            "n_rows": len(group), "n_parsed": int(group["parsed"].sum()), "parsed_pct": 100.0 * float(group["parsed"].mean()),
            "n_ok": counts["ok"], "n_fallback": counts["fallback"], "n_failed": counts["failed"], "n_missing": counts["missing"],
            "n_other_status": len(group) - sum(counts.values()),
            "n_finish_stop": int((finish == "stop").sum()), "n_finish_length": int((finish == "length").sum()),
            "n_finish_other": int((finish.notna() & ~finish.isin(["stop", "length"])).sum()),
            "n_finish_unknown": int(finish.isna().sum()),
            "n_rerun_at_retry_cap": (int((group["request_cap"] == common.RETRY_MAX_COMPLETION_TOKENS).sum())
                                     if group["request_cap"].notna().any() else None),
            "n_recovered_2026": int(group["recovered_2026"].sum()),
            "mean_prompt_tokens": group["prompt_tokens"].mean(), "mean_completion_tokens": group["completion_tokens"].mean(),
            "max_completion_tokens_used": group["completion_tokens"].max(),
            "mean_reasoning_tokens": group["reasoning_tokens"].mean()})
    frame = sort_rows(pd.DataFrame(rows, columns=PARSE_COLUMNS), ["arm", "series_key", "symbol", "model"])
    ctx.write_csv("llm_parse_stats.csv", frame, PARSE_INT_COLUMNS)
    luna = frame[frame["arm_role"].isin(["primary", "repeat"])]
    return {"rows": len(frame), "luna_rows": int(luna["n_rows"].sum()), "luna_parsed": int(luna["n_parsed"].sum()),
            "luna_finish_length": int(luna["n_finish_length"].sum()),
            "luna_rerun_at_retry_cap": (int(luna["n_rerun_at_retry_cap"].sum()) if luna["n_rerun_at_retry_cap"].notna().any() else None)}


# --------------------------------------------------------------------------- 11. reported_vs_computed.csv
REPORTED_COLUMNS = [
    "basis", "comparison", "rater", "ref_arm", "arm", "arm_role", "model", "series_key", "symbol", "scope", "year", "n",
    "median_ratio", "q25_ratio", "q75_ratio", "ratio_within_5pct_pct", "median_abs_diff_bn", "median_reported_bn",
    "median_computed_bn",
]
REPORTED_INT_COLUMNS = ["year", "n"]


def section_reported_vs_computed(ctx: Context) -> Dict[str, Any]:
    """Model-reported mean |GEX| against the computed one (the classifier's), per arm and on the bridge windows.

    basis ``arm``: every parsed answer of an arm that has a stored window (``r1_*`` = the published answers, ``r1_*_all``
    with the recovered ones).  basis ``bridge_pairs``: only the windows parsed by both raters of a bridge comparison
    (published o4-mini against a gpt-6-luna arm on the same series), one row per rater, so the two medians describe the
    same windows (the 'median reported / computed mean |GEX|' row of the bridge table).
    """
    det = ctx.data.detections
    scored = with_recovered_variants(det)
    scored = scored[scored["parsed"] & scored["clf_avg_magnitude"].notna()]
    rows: List[Dict[str, Any]] = []
    for (arm, model, series_key, symbol), group in scored.groupby(["arm", "model", "series_key", "symbol"], sort=True):
        for scope, year, sub in iter_scopes(group, "window_end"):
            rows.append({"basis": "arm", "comparison": "", "rater": "", "ref_arm": "", "arm": arm, "arm_role": arm_role(arm),
                         "model": model, "series_key": series_key, "symbol": symbol, "scope": scope, "year": year,
                         **ratio_summary(sub["avg_magnitude_billions"], sub["clf_avg_magnitude"])})
    for comparison, ref_group, oth_group in bridge_pairs(det[det["parsed"]]):
        pairs = pair_frame(ref_group, oth_group, ["symbol", "window_end"])
        for scope, year, sub in iter_scopes(pairs, "window_end"):
            for rater, group, column in (("reference", ref_group, "mag_ref"), ("other", oth_group, "mag_oth")):
                arm = group["arm"].iloc[0]
                rows.append({"basis": "bridge_pairs", "comparison": comparison, "rater": rater, "ref_arm": ref_group["arm"].iloc[0],
                             "arm": arm, "arm_role": arm_role(arm), "model": group["model"].iloc[0],
                             "series_key": group["series_key"].iloc[0], "symbol": group["symbol"].iloc[0],
                             "scope": scope, "year": year, **ratio_summary(sub[column], sub["clf_mag"])})
    if not rows:
        raise SectionSkipped("no parsed answer has both a reported magnitude and a stored window")
    frame = sort_rows(pd.DataFrame(rows, columns=REPORTED_COLUMNS),
                      ["basis", "comparison", "rater", "ref_arm", "arm", "series_key", "symbol", "scope", "year"])
    ctx.write_csv("reported_vs_computed.csv", frame, REPORTED_INT_COLUMNS)
    overall = frame[(frame["scope"] == "all") & (frame["basis"] == "bridge_pairs")]
    arms = frame[(frame["scope"] == "all") & (frame["basis"] == "arm") & frame["arm_role"].isin(["primary", "backfill"])]
    keep = ["comparison", "ref_arm", "rater", "arm", "model", "series_key", "symbol", "n", "median_ratio"]
    return {"rows": len(frame), "bridge_pairs": overall[keep].to_dict("records"),
            "median_ratio_by_arm": arms[["arm", "model", "series_key", "symbol", "n", "median_ratio"]].to_dict("records")}


# --------------------------------------------------------------------------- sections and orchestration
class Section:
    """A named report section, its output files and the function that produces them."""

    def __init__(self, name: str, outputs: Tuple[str, ...], run: Callable[[Context], Dict[str, Any]]):
        self.name, self.outputs, self.run = name, outputs, run


SECTIONS = (
    Section("detection_by_year", ("detection_by_year.csv", "detection_by_year_wide.csv"), section_detection_by_year),
    Section("bridge_agreement", ("bridge_agreement.csv", "bridge_agreement.yaml"), section_bridge_agreement),
    Section("series_comparison", ("series_comparison.csv",), section_series_comparison),
    Section("ex0dte_decomposition", ("ex0dte_decomposition.csv",), section_ex0dte_decomposition),
    Section("post_publication_2026", ("post_publication_2026.csv", "post_publication_2026_summary.csv"),
            section_post_publication),
    Section("intraday", ("intraday.csv",), section_intraday),
    Section("stats", ("stats.yaml",), section_stats),
    Section("cost_ledger", ("cost_ledger.csv", "cost_ledger.yaml"), section_cost_ledger),
    Section("disagreements", ("disagreements.csv",), section_disagreements),
    Section("llm_parse_stats", ("llm_parse_stats.csv",), section_llm_parse_stats),
    Section("reported_vs_computed", ("reported_vs_computed.csv",), section_reported_vs_computed),
)


def run_sections(ctx: Context, only: Optional[Sequence[str]]) -> Dict[str, Dict[str, Any]]:
    """Run the selected sections; a section that cannot run leaves no output file, a failing one does not stop the rest.

    A section that is not requested (``--only``) keeps whatever it wrote earlier; ``files_on_disk`` names those files so
    that report.yaml can list them as carried over.
    """
    status: Dict[str, Dict[str, Any]] = {}
    for section in SECTIONS:
        if only and section.name not in only:
            status[section.name] = {"status": "not_requested",
                                    "files_on_disk": [name for name in section.outputs if (ctx.results_dir / name).exists()]}
            continue
        for name in section.outputs:
            stale = ctx.results_dir / name
            if stale.exists():
                stale.unlink()
        try:
            summary = section.run(ctx)
        except SectionSkipped as exc:
            ctx.warn(f"section {section.name} skipped: {exc}")
            status[section.name] = {"status": "skipped", "reason": str(exc)}
        except Exception as exc:  # keep the other sections; the exit code reports the failure
            logger.exception("section %s failed", section.name)
            status[section.name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
        else:
            status[section.name] = {"status": "written", "files": list(section.outputs), "summary": summary}
    return status


# --------------------------------------------------------------------------- 11. report.yaml
CAVEATS = (
    "Windows have stride 1 and overlap; Wilson intervals in detection_by_year.csv are descriptive. Inference is in stats.yaml "
    "(quarter-block bootstrap and non-overlapping 30-day subsample next to every p-value).",
    "Rates are shares of parsed windows; parse failures are counted in n_windows but not in n.",
    "The fixed persistence/magnitude/flip thresholds are a pre-registered design decision; a scaled-threshold variant is a "
    "protocol change the authors must approve.",
    "2026 windows are the post-publication period, not out-of-sample (gpt-6-luna was created 2026-09-14). "
    "post_publication_2026_summary.csv gives the rates for windows that end in 2026 and for those that lie entirely in 2026.",
    "call_only is derived from new_full.call_gex when the series table does not store it.",
    "Arm r1_o4mini in every table is the published result: the answers without detection_metadata recovered_2026 (1,412 "
    "windows). r1_o4mini_all and bridge_incl_recovered add the 64 answers that only the 2026 backfill could read; the cost "
    "ledger and llm_parse_stats.csv cover every stored row. The backfilled Nov-2025 arms r1_p3_o4mini and r1_p4_o4mini follow "
    "the same rule (an '_all' variant exists only when some of their rows carry the flag).",
    "Repeat arms ('<arm>#rep<k>') are compared only with their original arm (test_retest); the bridge gate uses the first pass.",
    "Spend in cost_ledger.* counts only runs for which common.counts_toward_budget holds (current model, not a backfill); the "
    "backfilled o4-mini runs are listed under budget.not_spend and are never added to the spend.",
)

# What the figure scripts can rely on (the as-built LONG schemas are authoritative); echoed into report.yaml.
CONTRACT = {
    "detection_by_year.csv": "long format: label_source classifier|llm, scope year|all, rates in percent (rate_pct, ci_lo_pct, "
                             "ci_hi_pct); arm r1_o4mini = published subset, r1_o4mini_all = with the recovered windows",
    "detection_by_year_wide.csv": "derived copy of the yearly rows in the shape of the written spec: clf_rate, clf_ci_lo, "
                                  "clf_ci_hi, llm_rate, llm_ci_lo, llm_ci_hi as FRACTIONS in [0, 1]; agree_pct in percent "
                                  "(no figure reads it)",
    "bridge_agreement.csv": "n_pairs and n_ref_det_oth_det / _not, n_ref_not_oth_det / _not; the columns n, both_detect, "
                            "only_r1, only_luna, neither repeat the same counts under the names of the written spec",
    "series_comparison.csv": "series_a and series_b; 'pair' repeats '<series_a>_vs_<series_b>' (the written spec's column)",
    "reported_vs_computed.csv": "basis arm | bridge_pairs; median of model-reported mean |GEX| over the computed mean",
    "post_publication_2026_summary.csv": "definition ends_in_2026 | entirely_2026, label_source classifier | llm",
}


def coverage(df: pd.DataFrame, keys: Sequence[str], date_column: str, flag_column: Optional[str] = None) -> List[Dict[str, Any]]:
    """Row count and date range per key combination (and, with ``flag_column``, how many rows carry the flag)."""
    if df.empty:
        return []
    spec: Dict[str, Tuple[str, str]] = {"rows": (date_column, "size"), "first": (date_column, "min"), "last": (date_column, "max")}
    if flag_column is not None:
        spec["recovered_2026_rows"] = (flag_column, "sum")
    grouped = df.groupby(list(keys), sort=True, dropna=False).agg(**spec).reset_index()
    return grouped.to_dict("records")


def classifier_diagnostics(win: pd.DataFrame) -> Dict[str, Any]:
    """Thresholds in force and the (series, symbol) groups where no window can reach the magnitude threshold."""
    if win.empty:
        return {}
    clf = common.classifier()
    grouped = win.groupby(["series_key", "symbol"]).agg(
        n_windows=("clf_should_detect", "size"), n_detect=("clf_should_detect", "sum"),
        max_mean_abs_gex_usd=("clf_avg_magnitude", "max")).reset_index()
    floor = grouped[(grouped["n_detect"] == 0) & (grouped["max_mean_abs_gex_usd"] < clf.magnitude_threshold)]
    return {
        "thresholds": {"persistence": clf.persistence_threshold, "mean_abs_gex_usd": clf.magnitude_threshold,
                       "max_sign_flips": clf.max_sign_flips, "low_conviction_usd": clf.low_conviction_mag},
        "floor_effect": [{"series_key": r.series_key, "symbol": r.symbol, "n_windows": int(r.n_windows),
                          "max_window_mean_abs_gex_bn": r.max_mean_abs_gex_usd / 1e9} for r in floor.itertuples()],
        "floor_effect_note": "no window of these groups reaches the fixed magnitude threshold, so the classifier "
                             "detects nothing there in any year (pre-registered thresholds; not a modelling result)",
        "clf_versions": sorted(win["clf_version"].dropna().unique()),
        "window_rules": {f"{k[0]}:{k[1]}": int(v) for k, v in win.groupby(["series_key", "window_rule"]).size().items()},
    }


def headline(status: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Numbers the abstract and conclusions quote, lifted from the section summaries that were written."""
    def summary(name: str) -> Dict[str, Any]:
        return status.get(name, {}).get("summary", {})

    detection = summary("detection_by_year")
    out: Dict[str, Any] = {}
    if detection:
        out["classifier_rate_pct_by_year_spy"] = {s: v["SPY"] for s, v in detection["classifier_rate_pct_by_year"].items() if "SPY" in v}
        out["llm_rate_pct_by_year"] = detection["llm_rate_pct_by_year"]
        out["llm_vs_classifier_all_years"] = detection["llm_vs_classifier_all_years"]
    if summary("bridge_agreement"):
        out["bridge"] = {k: summary("bridge_agreement")[k] for k in ("gate", "bridge", "bridge_incl_recovered", "test_retest")}
    if summary("series_comparison"):
        out["series_exact_match_pct_by_year"] = summary("series_comparison")["exact_match_pct_by_year"]
    if summary("ex0dte_decomposition"):
        out["ex0dte"] = {k: v for k, v in summary("ex0dte_decomposition").items() if k != "rows"}
    if summary("stats"):
        out["contrasts"] = summary("stats")["headline_contrasts"]
    if summary("post_publication_2026"):
        out["post_publication"] = {k: summary("post_publication_2026")[k] for k in ("definition", "by_series")}
    if summary("intraday"):
        out["intraday"] = {k: v for k, v in summary("intraday").items() if k != "rows"}
    if summary("reported_vs_computed"):
        out["reported_vs_computed"] = {k: v for k, v in summary("reported_vs_computed").items() if k != "rows"}
    if summary("cost_ledger"):
        out["cost"] = {k: v for k, v in summary("cost_ledger").items() if k != "rows"}
    return out


def inputs_fingerprint(source: Mapping[str, Any]) -> str:
    """sha256 of what the tables held: the parquet file digests, or per table the row count and the newest created_at."""
    if source.get("kind") == "parquet":
        root = str(source.get("parquet_root") or "")
        material: Any = sorted((f["kind"], os.path.relpath(f["path"], root) if root else f["path"], f["sha256"])
                               for f in source.get("files", []))
    else:
        material = [sorted((t["table"], t["rows"]) for t in source.get("tables", [])), source.get("max_created_at")]
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()


def provenance(ctx: Context) -> Dict[str, Any]:
    """What the files written by this run were made from; kept per file in report.yaml and compared by a later ``--only`` run."""
    return {"inputs_fingerprint": inputs_fingerprint(ctx.data.source), "script_sha256": common.sha256_file(Path(__file__)),
            "common_sha256": common.sha256_file(Path(common.__file__)), "seed": ctx.seed, "n_boot": ctx.n_boot,
            "generated_at": common.utcnow().isoformat(timespec="seconds")}


STALE_CHECKS = (  # key of ``provenance`` -> why a file written with another value is stale
    ("inputs_fingerprint", "the result tables changed since the file was written"),
    ("script_sha256", "05_report.py changed since the file was written"),
    ("common_sha256", "common.py changed since the file was written"),
    ("seed", "the bootstrap seed differs"),
    ("n_boot", "the number of bootstrap draws differs"),
)


def stale_reasons(sha256: str, earlier: Any, produced: Mapping[str, Any]) -> List[str]:
    """Why a file left on disk by an earlier run cannot be trusted to match the tables and code of this run (empty = fresh).

    ``earlier`` is the record of the file in the previous report.yaml.  A file the previous report does not list, one whose
    digest differs from the recorded one, and one written from other tables, code or parameters are all stale.
    """
    if not isinstance(earlier, dict):
        return ["not listed in the previous report.yaml (no provenance)"]
    reasons = []
    if earlier.get("sha256") != sha256:
        reasons.append("the file differs from the one the previous report.yaml recorded")
    then = earlier.get("produced_with")
    if not isinstance(then, dict):
        return reasons + ["the previous report.yaml recorded no inputs fingerprint for it"]
    return reasons + [why for key, why in STALE_CHECKS if then.get(key) != produced.get(key)]


def carried_over(ctx: Context, status: Dict[str, Dict[str, Any]], produced: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Files of sections that were not rerun (``--only``) but are still in the results folder.

    Each gets its sha256, size and modification time and a ``stale`` flag with ``stale_reasons`` (see ``stale_reasons``);
    rows, columns and the ``produced_with`` record are copied from the previous report.yaml when its sha256 still matches.
    """
    previous: Dict[str, Any] = {}
    report = ctx.results_dir / "report.yaml"
    if report.exists():
        try:
            with open(report) as fh:
                previous = (yaml.safe_load(fh) or {}).get("files") or {}
        except (OSError, yaml.YAMLError, AttributeError):
            previous = {}
    carried: Dict[str, Dict[str, Any]] = {}
    for info in status.values():
        for name in info.get("files_on_disk", []):
            path = ctx.results_dir / name
            stat = path.stat()
            record: Dict[str, Any] = {"carried_over": True, "bytes": stat.st_size, "sha256": common.sha256_file(path),
                                      "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")}
            earlier = previous.get(name) if isinstance(previous, dict) else None
            reasons = stale_reasons(record["sha256"], earlier, produced)
            record.update(stale=bool(reasons), stale_reasons=reasons)
            if isinstance(earlier, dict) and earlier.get("sha256") == record["sha256"]:
                record = {**{k: earlier[k] for k in ("rows", "columns", "keys", "produced_with") if k in earlier}, **record}
            carried[name] = record
    return carried


def untracked_files(ctx: Context, known: Collection[str]) -> List[Dict[str, Any]]:
    """Files in the results folder that no section of this script writes (and that are not report.yaml)."""
    out = []
    for path in sorted(ctx.results_dir.iterdir()):
        if path.is_file() and path.name != "report.yaml" and path.name not in known:
            stat = path.stat()
            out.append({"name": path.name, "bytes": stat.st_size, "sha256": common.sha256_file(path),
                        "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds")})
    return out


def input_diagnostics(data: Data) -> Dict[str, Any]:
    """Facts about the stored inputs that the text quotes: the factor of each scaled series, windows flagged for calendar holes.

    ``scaling``: per scaled series (common.Series.scale) and symbol, the factor recorded in series_metadata by
    01_build_series.py.  ``flagged_windows``: windows whose window_metadata marks a calendar gap longer than
    ``common.CALENDAR_GAP_FLAG_DAYS`` (gap_flag / calendar_gap_days) or master-calendar days missing from the series
    (missing_master_days), per series and symbol.
    """
    out: Dict[str, Any] = {}
    scaled: Dict[str, Any] = {}
    for (key, symbol), group in data.series.groupby(["series_key", "symbol"]):
        registered = common.SERIES.get(key)
        if registered is None or registered.scale is None:
            continue
        metas = list(group["series_metadata"])
        factors = sorted({m["factor"] for m in metas if m.get("factor") is not None})
        days = sorted({m["n_days"] for m in metas if m.get("n_days") is not None})
        scaled[f"{key}:{symbol}"] = {"scale": registered.scale, "rows": len(group),
                                     "factor": factors[0] if len(factors) == 1 else (factors or None),
                                     "n_days_in_factor": days[0] if len(days) == 1 else (days or None)}
    if scaled:
        out["scaling"] = scaled
    win = data.windows
    if len(win):
        meta = win["window_metadata"]
        gap_days = pd.to_numeric(meta.map(lambda m: m.get("calendar_gap_days")), errors="coerce")
        gap = meta.map(lambda m: truthy(m.get("gap_flag"))) | (gap_days > common.CALENDAR_GAP_FLAG_DAYS)
        missing = pd.to_numeric(meta.map(lambda m: m.get("missing_master_days")), errors="coerce").fillna(0) > 0
        grouped = win.assign(gap=gap, missing=missing).groupby(["series_key", "symbol"]).agg(
            n_windows=("gap", "size"), n_calendar_gap=("gap", "sum"), n_missing_master_days=("missing", "sum")).reset_index()
        flagged = grouped[(grouped["n_calendar_gap"] > 0) | (grouped["n_missing_master_days"] > 0)]
        if len(flagged):
            out["flagged_windows"] = flagged.astype({"n_calendar_gap": int, "n_missing_master_days": int}).to_dict("records")
    return out


def write_report(ctx: Context, status: Dict[str, Dict[str, Any]], args_view: Dict[str, Any]) -> None:
    data = ctx.data
    produced = provenance(ctx)
    files = {}
    for name, info in sorted(ctx.files.items()):
        path = ctx.results_dir / name
        files[name] = {**info, "bytes": path.stat().st_size, "sha256": common.sha256_file(path), "produced_with": produced}
    carried = carried_over(ctx, status, produced)
    if carried:
        stale = sorted(name for name, record in carried.items() if record["stale"])
        ctx.warn(f"--only: {len(carried)} output file(s) of sections that were not rerun stay on disk from an earlier run "
                 f"(carried_over in files): {', '.join(sorted(carried))}"
                 + (f"; STALE (tables, code or parameters changed since they were written): {', '.join(stale)}" if stale else ""))
    untracked = untracked_files(ctx, set(files) | set(carried))
    if untracked:
        ctx.warn(f"the results folder holds {len(untracked)} file(s) that no section of this script writes "
                 f"(untracked_files): {', '.join(item['name'] for item in untracked)}")
    files = dict(sorted({**files, **carried}.items()))
    ctx.write_yaml("report.yaml", {
        "generated_at": produced["generated_at"],
        "script": {"path": "scripts/validation/electronics/05_report.py", "sha256": produced["script_sha256"],
                   "common_sha256": produced["common_sha256"], "git_sha": common.git_sha()},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                        "scipy": scipy.__version__, "pyyaml": yaml.__version__},
        "parameters": args_view,
        "contract": CONTRACT,
        "source": data.source,
        "inputs_fingerprint": produced["inputs_fingerprint"],
        "inputs": {
            "series": {"rows": len(data.series), "coverage": coverage(data.series, ["series_key", "symbol"], "trading_date")},
            "windows": {"rows": len(data.windows), "coverage": coverage(data.windows, ["series_key", "symbol"], "window_end")},
            "detections": {"rows": len(data.detections),
                           "coverage": coverage(data.detections, ["arm", "model", "series_key", "symbol"], "window_end",
                                                flag_column="recovered_2026"),
                           "parsed_rows": int(data.detections["parsed"].sum()) if len(data.detections) else 0,
                           "recovered_2026_rows": int(data.detections["recovered_2026"].sum()) if len(data.detections) else 0},
            "runs": {"rows": len(data.runs)},
        },
        "sections": status,
        "files": files,
        "untracked_files": untracked,
        "warnings": ctx.warnings,
        "diagnostics": {**classifier_diagnostics(data.windows), **input_diagnostics(data)},
        "headline": headline(status),
        "caveats": list(CAVEATS),
    })


def generate(data: Data, results_dir: Path, seed: int = SEED, n_boot: int = N_BOOT,
             only: Optional[Sequence[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Run the selected sections on ``data``, write report.yaml and return the per-section status."""
    results_dir.mkdir(parents=True, exist_ok=True)
    ctx = Context(data, results_dir, seed, n_boot, warnings=list(data.warnings))
    status = run_sections(ctx, only)
    write_report(ctx, status, {"seed": seed, "n_boot": n_boot, "results_dir": str(results_dir), "only": list(only) if only else None})
    return status


# --------------------------------------------------------------------------- command line
def load_runner() -> Tuple[Any, Optional[str]]:
    """(04_llm_runner module, None) or (None, reason): the runner needs psycopg2 and pyarrow, so failing to load is a finding."""
    path = common.SCRIPT_DIR / "04_llm_runner.py"
    name = "electronics_runner_04"
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        runner = importlib.util.module_from_spec(spec)
        sys.modules[name] = runner  # @dataclass looks its module up in sys.modules while the module executes
        spec.loader.exec_module(runner)
    except Exception as exc:
        return None, f"cannot load {path.name}: {type(exc).__name__}: {exc}"
    finally:
        sys.modules.pop(name, None)
    return runner, None


def check_runner_conventions() -> List[str]:
    """Differences between the repeat labels this report reads and the ones the contract and 04_llm_runner.py write.

    An empty list means consistent.  The probes spell a repeat the way the contract does (common.custom_id(..., repeat=1),
    common.REPEAT_ARM_SUFFIX) and check that ``tag_repeats`` reads them; for each name that 04_llm_runner.py exports
    (``REPEAT_SUFFIX``, ``REPEAT_ARM_SUFFIX``, ``split_custom_id``) the runner's own spelling is compared as well.
    """
    problems: List[str] = []
    day = date(2024, 1, 2)
    original = common.custom_id("bridge_jan", "SPY", day)
    repeat = common.custom_id("bridge_jan", "SPY", day, repeat=1)
    second = common.custom_id("bridge_jan", "SPY", day, repeat=2)
    bare = original + REPEAT_MARK  # an older runner ended the custom_id with the bare mark
    labelled = "bridge_jan" + common.REPEAT_ARM_SUFFIX
    if common.parse_custom_id(repeat) != ("bridge_jan", "SPY", day) or common.custom_id_repeat(repeat) != 1:
        problems.append(f"common.parse_custom_id / custom_id_repeat do not read {repeat!r} as repeat 1 of bridge_jan")
    probe = pd.DataFrame({"arm": ["bridge_jan", labelled, "bridge_jan", "bridge_jan", "bridge_jan"],
                          "custom_id": [original, repeat, bare, second, repeat]})
    tagged = tag_repeats(probe)
    expected = (["bridge_jan", labelled, labelled, "bridge_jan" + REPEAT_MARK + "2", labelled], ["bridge_jan"] * 5, [0, 1, 1, 2, 1])
    found = (tagged["arm"].tolist(), tagged["base_arm"].tolist(), tagged["repeat_index"].tolist())
    if found != expected:
        problems.append(f"tag_repeats reads the contract's repeat labels as (arm, base_arm, repeat_index) = {found}, expected {expected}")
    if common.REPEAT_ARM_SUFFIX != REPEAT_MARK + "1":
        problems.append(f"common.REPEAT_ARM_SUFFIX is {common.REPEAT_ARM_SUFFIX!r}, expected {REPEAT_MARK + '1'!r}")
    runner, reason = load_runner()
    if runner is None:
        return problems + [reason]
    for attribute, wanted in (("REPEAT_SUFFIX", common.REPEAT_MARK), ("REPEAT_ARM_SUFFIX", common.REPEAT_ARM_SUFFIX)):
        if hasattr(runner, attribute) and getattr(runner, attribute) != wanted:
            problems.append(f"04_llm_runner.{attribute} is {getattr(runner, attribute)!r}, the contract spells {wanted!r}")
    if hasattr(runner, "split_custom_id"):
        try:
            parts = runner.split_custom_id(repeat)
        except Exception as exc:
            problems.append(f"04_llm_runner.split_custom_id cannot read the contract's repeat custom_id: {type(exc).__name__}: {exc}")
        else:
            if parts[0] != "bridge_jan" or (len(parts) > 3 and not parts[3]):
                problems.append(f"04_llm_runner.split_custom_id({repeat!r}) = {parts!r}: not read as a repeat of bridge_jan")
    return problems


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write the Electronics paper tables from backups.gex_llm_regime_* (Postgres or parquet copies).",
        epilog="Sections: " + ", ".join(s.name for s in SECTIONS) + ". Nothing is written to Postgres.")
    parser.add_argument("--source", choices=("auto", "db", "parquet"), default="auto",
                        help="auto = Postgres when all four tables exist, otherwise parquet (default)")
    parser.add_argument("--parquet-root", type=Path, default=common.PARQUET_ROOT,
                        help="folder holding series/ windows/ detections/ runs/ parquet files (default: %(default)s)")
    parser.add_argument("--results-dir", type=Path, default=common.RESULTS_DIR,
                        help="output folder (default: %(default)s); required with a non-default --parquet-root")
    parser.add_argument("--only", nargs="+", choices=[s.name for s in SECTIONS], metavar="SECTION",
                        help="run only these sections (report.yaml is always written; files of the other sections stay "
                             "on disk and are listed as carried_over with sha256 and a stale flag)")
    parser.add_argument("--seed", type=int, default=SEED, help="bootstrap seed (default: %(default)s)")
    parser.add_argument("--n-boot", type=int, default=N_BOOT, help="bootstrap draws (default: %(default)s)")
    parser.add_argument("--check-conventions", action="store_true",
                        help="compare the repeat labels read here with the contract (common.py) and 04_llm_runner.py "
                             "and exit (0 = consistent)")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    args = parser.parse_args(argv)
    if args.parquet_root != common.PARQUET_ROOT and args.results_dir == common.RESULTS_DIR:
        parser.error("a non-default --parquet-root needs an explicit --results-dir (keeps test data out of the paper results)")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    common.setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    if args.check_conventions:
        problems = check_runner_conventions()
        for line in problems:
            print(f"MISMATCH {line}")
        print("repeat labels: consistent with common.py and 04_llm_runner.py" if not problems
              else f"{len(problems)} mismatch(es)")
        return 1 if problems else 0
    try:
        data = load_data(args.source, args.parquet_root)
    except InputError as exc:
        logger.error("%s", exc.message)
        return 2
    status = generate(data, args.results_dir, args.seed, args.n_boot, args.only)
    for name, info in status.items():
        logger.info("%-22s %s", name, info["status"])
    failed = [name for name, info in status.items() if info["status"] == "failed"]
    if failed:
        logger.error("failed sections: %s", ", ".join(failed))
        return 1
    if not any(info["status"] == "written" for info in status.values()):
        logger.error("no section wrote a file (empty tables, or every requested section was skipped): see the warnings "
                     "in %s", args.results_dir / "report.yaml")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
