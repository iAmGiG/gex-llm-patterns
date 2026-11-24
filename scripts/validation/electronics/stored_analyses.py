#!/usr/bin/env python3
"""Stored-data analyses that the pre-submission review asked for (gex-llm-patterns issue #289).

Everything here is computed from the stored tables (series, windows, detections, runs): no database, no API, no
GPU and no new model call.  The functions are pure (DataFrames and arrays in, DataFrames and plain Python types
out), deterministic (every resampling draws from a generator seeded from ``--seed`` and a stable tag) and take
the rule's thresholds and the resampling settings as parameters, so a report section can call them directly.

Analyses (SPY unless stated; the review's numbering, E5 is done inside 05_report.py):

* E1  trivial comparators and contested windows
* E2  put weight by magnitude-threshold grid
* E3  episodes and dependence-aware intervals for the 2024-2025 rate
* E4  which rise after 2023 can be ruled out (period shift, moving-block intervals, margin)
* E6  scale-free magnitude thresholds
* E9  same-day-expiry ablation detail
* E13 falsification of the lineage claim (call-only series, hybrid series, put leg)

Definitions shared by every analysis
------------------------------------
The rule (src/validation/regime_classifier.py, ``RegimeClassifier._classify_regime_type``) labels a window of 30
consecutive daily net GEX values ``v_1..v_30`` (USD) as detected when all of

* persistence: ``max(pos, neg) >= persistence_days`` (21 = int(30 * 0.70)), with ``pos`` the number of values
  ``> 0`` and ``neg = 30 - pos`` (a value of exactly zero counts as negative here);
* magnitude: ``mean(|v|) >= magnitude_usd`` (5e9, boundary included);
* stability: ``flips <= max_flips`` (5), with ``flips`` the number of ``i`` where ``sign(v_i) != sign(v_{i-1})``
  (``np.sign``, so a zero differs from both signs);

hold.  A window ends on a series row and starts 29 rows earlier (``window_end`` is the date of the last row).
The periods are calendar years of ``window_end``: 2008-2019, 2020-2023, 2024-2025, 2026 and all.

Resampling.  A moving-block bootstrap draws ``ceil(n / L)`` blocks of ``L`` consecutive windows (start positions
uniform over the ``n - L + 1`` blocks that fit, or over all ``n`` positions with wrap-around for the circular
variant), joins them and cuts the result to ``n`` windows; a statistic is recomputed on each resample and the 95
percent interval is the 2.5th and 97.5th percentile of the draws.  For two periods the two samples are
resampled independently.  Wilson intervals and the quarter-block bootstrap are those of 05_report.py (imported,
not copied).

Usage (repository root, AutoGex env, ``PYTHONNOUSERSITE=1 PYTHONPATH=$(pwd)``)::

    python scripts/validation/electronics/stored_analyses.py --parquet-root <tables> --out <dir> [--only E2,E3]
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import logging
import math
import sys
import time
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import yaml
from numpy.lib.stride_tricks import sliding_window_view

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import common  # noqa: E402  (the pipeline contract, same folder)

logger = logging.getLogger("electronics.stored_analyses")

# --------------------------------------------------------------------------- constants
SEED = 261
N_BOOT = 5000
CI_LEVEL = 0.95
WINDOW = common.WINDOW_DAYS
PERSISTENCE_DAYS = int(WINDOW * 0.70)  # 21, as RegimeClassifier._classify_regime_type computes it
MAGNITUDE_USD = 5e9
MAX_FLIPS = 5
PAPER_THRESHOLD_BN = 5.0

PERIOD_SPANS: Dict[str, Tuple[Optional[int], Optional[int]]] = {
    "2008-2019": (2008, 2019), "2020-2023": (2020, 2023), "2024-2025": (2024, 2025), "2026": (2026, 2026),
    "all": (None, None)}
LATE = "2024-2025"
PUT_WEIGHTS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.05, 1.1, 1.2)
GRID_BN = (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0)
SHIFT_GRID_BN = (3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.4, 6.5, 7.0, 8.0, 10.0)
BLOCK_LENGTHS = (30, 60, 90, 120)
PRIMARY_BLOCK = 60
MARGIN_PP = 5.0
BREAK_DATE = pd.Timestamp("2023-09-29")  # first day without put rows in the published inputs (upstream issue #24)
FULL, EX0DTE, CALL_ONLY, PUBLISHED = "new_full", "new_ex0dte", "call_only", "jan2026_phase4a"
# Contested-window margins (days of the majority sign, billions of USD of mean |GEX|, flips above / below the limit):
# margin1 = one unit on each criterion, either side of its threshold; pivotal = the review's scratch definition
# (one day, half a billion, flips 5 and 6 only).
CONTESTED_DEFINITIONS = {"margin1": {"days": 1, "billions": 1.0, "flips": 1, "flips_below": 1},
                         "pivotal": {"days": 1, "billions": 0.5, "flips": 1, "flips_below": 0}}
ANALYSES = ("E1", "E2", "E3", "E4", "E6", "E9", "E13")

_report_module = None


def report():
    """The 05_report.py module (loaded once by path; its statistics are reused, not copied)."""
    global _report_module
    if _report_module is None:
        spec = importlib.util.spec_from_file_location("electronics_report_05", HERE / "05_report.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["electronics_report_05"] = module
        spec.loader.exec_module(module)
        _report_module = module
    return _report_module


# --------------------------------------------------------------------------- the rule, vectorised
def window_metrics(values: Sequence[float], window: int = WINDOW) -> pd.DataFrame:
    """Rule inputs of every window of ``window`` consecutive values (row ``i`` covers values ``i..i+window-1``).

    Columns: ``pos`` (values > 0), ``neg`` (window - pos, zeros included), ``flips`` (sign changes of np.sign
    between neighbours), ``mean_abs`` (mean absolute value, USD).  Empty frame when fewer than ``window`` values.
    """
    x = np.asarray(values, dtype=float)
    if x.size < window:
        return pd.DataFrame({"pos": [], "neg": [], "flips": [], "mean_abs": []})
    w = sliding_window_view(x, window)
    pos = (w > 0).sum(axis=1)
    s = np.sign(w)
    return pd.DataFrame({"pos": pos.astype(int), "neg": (window - pos).astype(int),
                         "flips": (s[:, 1:] != s[:, :-1]).sum(axis=1).astype(int), "mean_abs": np.abs(w).mean(axis=1)})


def rule_verdict(metrics: pd.DataFrame, persistence_days: int = PERSISTENCE_DAYS, magnitude_usd: float = MAGNITUDE_USD,
                 max_flips: int = MAX_FLIPS) -> np.ndarray:
    """Boolean verdict of the rule: max(pos, neg) >= persistence_days, mean_abs >= magnitude_usd, flips <= max_flips."""
    return ((np.maximum(metrics["pos"], metrics["neg"]).to_numpy() >= persistence_days)
            & (metrics["mean_abs"].to_numpy() >= magnitude_usd) & (metrics["flips"].to_numpy() <= max_flips))


def series_frame(series: pd.DataFrame, key: str, symbol: str = "SPY") -> pd.DataFrame:
    """The rows of one stored series ordered by trading_date (columns of the series table)."""
    out = series[(series["series_key"] == key) & (series["symbol"] == symbol)].sort_values("trading_date")
    return out.reset_index(drop=True)


def window_frame(days: pd.DataFrame, values: Optional[Sequence[float]] = None, window: int = WINDOW) -> pd.DataFrame:
    """Windows over the rows of ``days`` (consecutive rows): window_start, window_end, year and the rule inputs.

    ``values`` defaults to the stored ``net_gex``; a window whose ``window`` rows are all present ends on row
    ``window - 1`` or later.  Row ``i`` of the result ends on ``days.trading_date[i + window - 1]``.
    """
    x = days["net_gex"].to_numpy(float) if values is None else np.asarray(values, float)
    m = window_metrics(x, window)
    dates = pd.to_datetime(days["trading_date"]).reset_index(drop=True)
    m.insert(0, "window_end", dates.iloc[window - 1:].reset_index(drop=True))
    m.insert(0, "window_start", dates.iloc[: len(m)].reset_index(drop=True))
    m["year"] = m["window_end"].dt.year
    return m


def period_mask(window_end: pd.Series, period: str) -> np.ndarray:
    """Windows of ``period`` (a key of PERIOD_SPANS) by the calendar year of ``window_end``."""
    first, last = PERIOD_SPANS[period]
    year = pd.to_datetime(window_end).dt.year.to_numpy()
    if first is None:
        return np.ones(len(year), bool)
    return (year >= first) & (year <= last)


def weekday_name(i: int) -> str:
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[int(i)]


# --------------------------------------------------------------------------- resampling
def make_rng(seed: int, *tags: Any) -> np.random.Generator:
    """Generator seeded from ``seed`` and the CRC32 of each tag: the same tags always give the same stream."""
    return np.random.default_rng([int(seed)] + [zlib.crc32(str(t).encode()) for t in tags])


def segment_ids(positions: Sequence[int]) -> np.ndarray:
    """Segment index of each position of a sorted subset: a new segment starts wherever the position jumps by more than one."""
    p = np.asarray(positions)
    return np.concatenate([[0], np.cumsum(np.diff(p) > 1)]) if p.size else np.zeros(0, int)


def mbb_sums(values: np.ndarray, block_len: int, n_boot: int, rng: np.random.Generator, circular: bool = False,
             segments: Optional[np.ndarray] = None) -> np.ndarray:
    """Column sums of ``n_boot`` moving-block resamples of the rows of ``values`` (shape (n_boot, m)).

    Each resample has ``n`` rows: ``ceil(n / L)`` blocks of ``L`` consecutive rows (the last one cut to fit).
    Non-circular blocks start anywhere a whole block fits; with ``segments`` (one id per row) only where the block
    stays inside one segment (falls back to every start when no block does).  Circular blocks start at any row
    and wrap around the end.  Sums come from a cumulative-sum table, so a draw costs ``ceil(n / L)`` lookups.
    """
    v = np.asarray(values, dtype=float)
    if v.ndim == 1:
        v = v[:, None]
    n, m = v.shape
    if n == 0:
        return np.full((n_boot, m), np.nan)
    length = int(min(max(block_len, 1), n))
    n_blocks = -(-n // length)
    last = n - (n_blocks - 1) * length
    if circular:
        ext, pool = np.vstack([v, v[:length]]), np.arange(n)
    else:
        ext, pool = v, np.arange(n - length + 1)
        if segments is not None:
            seg = np.asarray(segments)
            ok = seg[pool] == seg[pool + length - 1]
            if ok.any():
                pool = pool[ok]
    cs = np.vstack([np.zeros((1, m)), np.cumsum(ext, axis=0)])
    starts = pool[rng.integers(0, len(pool), size=(n_boot, n_blocks))]
    body = (cs[starts[:, : n_blocks - 1] + length] - cs[starts[:, : n_blocks - 1]]).sum(axis=1)
    return body + (cs[starts[:, -1] + last] - cs[starts[:, -1]])


def percentile_ci(draws: np.ndarray, level: float = CI_LEVEL) -> Tuple[float, float]:
    """Percentile interval (numpy linear rule) of the finite draws; NaN, NaN when there are none."""
    d = np.asarray(draws, float)
    d = d[np.isfinite(d)]
    if d.size == 0:
        return math.nan, math.nan
    lo, hi = np.percentile(d, [50.0 * (1.0 - level), 50.0 * (1.0 + level)])
    return float(lo), float(hi)


def rate_interval(flags: np.ndarray, block_len: int, n_boot: int, rng: np.random.Generator, circular: bool = False,
                  segments: Optional[np.ndarray] = None) -> Tuple[float, float, float]:
    """(rate, lo, hi) in percent of a 0/1 sequence by moving-block bootstrap."""
    f = np.asarray(flags, float)
    sums = mbb_sums(f, block_len, n_boot, rng, circular, segments)[:, 0]
    lo, hi = percentile_ci(100.0 * sums / len(f))
    return 100.0 * float(f.mean()), lo, hi


def shift_interval(late: np.ndarray, early: np.ndarray, block_len: int, n_boot: int, rng: np.random.Generator,
                   circular: bool = False, early_segments: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Late minus early rate in percentage points with a moving-block interval (the two samples resampled independently)."""
    late, early = np.asarray(late, float), np.asarray(early, float)
    sl = mbb_sums(late, block_len, n_boot, rng, circular)[:, 0] / len(late)
    se = mbb_sums(early, block_len, n_boot, rng, circular, early_segments)[:, 0] / len(early)
    lo, hi = percentile_ci(100.0 * (sl - se))
    return {"shift_pp": 100.0 * float(late.mean() - early.mean()), "ci_lo_pp": lo, "ci_hi_pp": hi}


def ratio_interval(components: np.ndarray, num: Sequence[int], den: Sequence[int], block_len: int, n_boot: int,
                   rng: np.random.Generator, circular: bool = False) -> Tuple[float, float, float]:
    """Point and moving-block interval of a ratio of sums ``sum(components[:, num]) / sum(components[:, den])`` (fractions).

    ``components`` has one row per window in order and one column per additive component (for example
    contested & agree and contested); a resample with an empty denominator gives NaN and is left out of the interval.
    """
    c = np.asarray(components, float)
    point = c[:, list(num)].sum() / c[:, list(den)].sum() if c[:, list(den)].sum() > 0 else math.nan
    if len(c) == 0:
        return math.nan, math.nan, math.nan
    s = mbb_sums(c, block_len, n_boot, rng, circular)
    with np.errstate(divide="ignore", invalid="ignore"):
        draws = s[:, list(num)].sum(axis=1) / s[:, list(den)].sum(axis=1)
    lo, hi = percentile_ci(draws)
    return float(point), lo, hi


# --------------------------------------------------------------------------- episodes and effective sample size
def find_episodes(window_end: Sequence[Any], flags: Sequence[bool]) -> pd.DataFrame:
    """Runs of consecutive detected windows of an ordered sequence: ``start`` and ``end`` (window_end of the first and
    last window of the run), ``length`` (number of windows) and ``gap_before`` (non-detected windows since the
    previous run, or since the first window of the sequence)."""
    f = np.asarray(flags, bool)
    dates = pd.to_datetime(pd.Series(list(window_end))).reset_index(drop=True)
    rows = []
    i, previous_end = 0, -1
    while i < len(f):
        if f[i]:
            j = i
            while j + 1 < len(f) and f[j + 1]:
                j += 1
            rows.append({"start": dates.iloc[i].date().isoformat(), "end": dates.iloc[j].date().isoformat(),
                         "length": j - i + 1, "gap_before": i - previous_end - 1})
            previous_end, i = j, j + 1
        else:
            i += 1
    return pd.DataFrame(rows, columns=["start", "end", "length", "gap_before"])


def autocorrelation(x: np.ndarray, max_lag: int) -> np.ndarray:
    """Sample autocorrelations at lags 1..max_lag (biased estimator, divided by n times the variance)."""
    x = np.asarray(x, float)
    n = len(x)
    d = x - x.mean()
    var = float((d * d).sum())
    if var == 0.0:
        return np.full(max_lag, np.nan)
    f = np.fft.rfft(d, 2 * n)
    acov = np.fft.irfft(f * np.conj(f))[:n]
    return acov[1: max_lag + 1] / acov[0]


def ess_acf(x: np.ndarray) -> float:
    """Effective sample size ``n / (1 + 2 * sum_k rho_k)`` with Geyer's initial positive sequence: the autocorrelations
    are summed in pairs ``rho_{2j-1} + rho_{2j}`` until a pair is not positive.  NaN for a constant sequence."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 4:
        return math.nan
    rho = autocorrelation(x, n - 1)
    if np.isnan(rho).any():
        return math.nan
    total = 0.0
    for j in range(0, len(rho) - 1, 2):
        pair = rho[j] + rho[j + 1]
        if pair <= 0:
            break
        total += pair
    return float(min(n / (1.0 + 2.0 * total), n))


def ess_batch_means(x: np.ndarray, batch: int) -> float:
    """Effective sample size from non-overlapping batch means: ``var(x) / var(mean estimate)`` where the variance of the
    overall mean is ``var(batch means) / n_batches`` (the last incomplete batch is dropped).  NaN when fewer than
    two batches or a constant sequence."""
    x = np.asarray(x, float)
    k = len(x) // batch
    if k < 2 or x.std() == 0.0:
        return math.nan
    means = x[: k * batch].reshape(k, batch).mean(axis=1)
    var_mean = means.var(ddof=1) / k
    return float(min(x.var(ddof=1) / var_mean, len(x))) if var_mean > 0 else float(len(x))


def episode_bootstrap_rate(flags: np.ndarray, n_boot: int, rng: np.random.Generator) -> Tuple[float, float, float]:
    """Rate in percent with an interval from resampling whole cycles.

    The sequence is cut into cycles: a run of non-detected windows followed by the run of detected windows that
    ends it (the last cycle may have no detected run).  ``U`` cycles are drawn with replacement and the rate of a
    resample is ``sum(detected windows) / sum(all windows)`` over the drawn cycles (a ratio estimator, so the
    resampled length varies).
    """
    f = np.asarray(flags, bool)
    lengths, detected = [], []
    i = 0
    while i < len(f):
        j = i
        while j < len(f) and not f[j]:
            j += 1
        k = j
        while k < len(f) and f[k]:
            k += 1
        lengths.append(k - i)
        detected.append(k - j)
        i = k
    cyc = np.column_stack([lengths, detected]).astype(float)
    u = len(cyc)
    idx = rng.integers(0, u, size=(n_boot, u))
    sums = cyc[idx].sum(axis=1)
    lo, hi = percentile_ci(100.0 * sums[:, 1] / sums[:, 0])
    return 100.0 * float(f.mean()), lo, hi


# --------------------------------------------------------------------------- contested windows
def contested_mask(pos, neg, mean_abs, flips, margin_days: int = 1, margin_bn: float = 1.0, margin_flips: int = 1,
                   margin_flips_below: Optional[int] = None, persistence_days: int = PERSISTENCE_DAYS,
                   magnitude_usd: float = MAGNITUDE_USD, max_flips: int = MAX_FLIPS) -> pd.DataFrame:
    """Contested windows: one criterion is within its margin of its threshold while the other two pass.

    * persistence is near when ``|max(pos, neg) - persistence_days| <= margin_days`` (days);
    * magnitude is near when ``|mean_abs - magnitude_usd| <= margin_bn * 1e9`` (billions of USD);
    * stability is near when ``max_flips - margin_flips_below <= flips <= max_flips + margin_flips`` (flips;
      ``margin_flips_below`` defaults to ``margin_flips``).

    ``by_persistence`` is near-persistence and magnitude passes and flips pass; likewise ``by_magnitude`` and
    ``by_flips``; ``contested`` is their union.  Passing means the rule's own condition holds (boundary included).
    """
    below = margin_flips if margin_flips_below is None else margin_flips_below
    dom = np.maximum(np.asarray(pos), np.asarray(neg))
    mag, fl = np.asarray(mean_abs, float), np.asarray(flips)
    ok_p, ok_m, ok_f = dom >= persistence_days, mag >= magnitude_usd, fl <= max_flips
    near_p = np.abs(dom - persistence_days) <= margin_days
    near_m = np.abs(mag - magnitude_usd) <= margin_bn * 1e9
    near_f = (fl >= max_flips - below) & (fl <= max_flips + margin_flips)
    by_p, by_m, by_f = near_p & ok_m & ok_f, near_m & ok_p & ok_f, near_f & ok_p & ok_m
    return pd.DataFrame({"contested": by_p | by_m | by_f, "by_persistence": by_p, "by_magnitude": by_m, "by_flips": by_f})


def comparator_labels(pos, neg, mean_abs, flips, persistence_days: int = PERSISTENCE_DAYS,
                      magnitude_usd: float = MAGNITUDE_USD, max_flips: int = MAX_FLIPS) -> Dict[str, np.ndarray]:
    """Trivial predictors of the rule's verdict, as boolean arrays: always_no, always_yes, flips_only (flips <=
    max_flips), magnitude_only, persistence_only and the three two-criterion rules (persistence_magnitude,
    persistence_flips, magnitude_flips)."""
    dom = np.maximum(np.asarray(pos), np.asarray(neg))
    p, m, f = dom >= persistence_days, np.asarray(mean_abs, float) >= magnitude_usd, np.asarray(flips) <= max_flips
    n = len(dom)
    return {"always_no": np.zeros(n, bool), "always_yes": np.ones(n, bool), "flips_only": f, "magnitude_only": m,
            "persistence_only": p, "persistence_magnitude": p & m, "persistence_flips": p & f, "magnitude_flips": m & f}


def confusion_components(y: np.ndarray, r: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Per-window 0/1 components inside ``mask``: [agree, n, tp, rule_pos, tn, rule_neg, predicted_pos] (y = predictor,
    r = rule verdict), so that agreement = col0/col1, sensitivity = tp/rule_pos, specificity = tn/rule_neg and
    PPV = tp/predicted_pos."""
    y, r, c = np.asarray(y, bool), np.asarray(r, bool), np.asarray(mask, bool)
    return np.column_stack([c & (y == r), c, c & y & r, c & r, c & ~y & ~r, c & ~r, c & y]).astype(float)


CONFUSION_METRICS = {"agree": ((0,), (1,)), "sens": ((2,), (3,)), "spec": ((4,), (5,)), "ppv": ((2,), (6,))}


def confusion_summary(y: np.ndarray, r: np.ndarray, mask: np.ndarray, block_len: int, n_boot: int,
                      rng_seed: Tuple[int, Tuple[Any, ...]]) -> Dict[str, float]:
    """Agreement, sensitivity, specificity and PPV (percent) of predictor ``y`` against rule ``r`` on the windows in
    ``mask``, each with a moving-block interval (blocks over the whole ordered sequence; the statistic is recomputed
    on the windows of ``mask`` that the resample contains)."""
    comp = confusion_components(y, r, mask)
    out: Dict[str, float] = {"n": int(comp[:, 1].sum())}
    seed, tags = rng_seed
    for name, (num, den) in CONFUSION_METRICS.items():
        p, lo, hi = ratio_interval(comp, num, den, block_len, n_boot, make_rng(seed, *tags, name))
        out[f"{name}_pct"], out[f"{name}_lo_pct"], out[f"{name}_hi_pct"] = 100 * p, 100 * lo, 100 * hi
    return out


# --------------------------------------------------------------------------- E2 put weight by threshold
def put_weight_grid(days: pd.DataFrame, weights: Sequence[float] = PUT_WEIGHTS, thresholds_bn: Sequence[float] = GRID_BN,
                    periods: Sequence[str] = ("2008-2019", "2020-2023", "2024-2025"), window: int = WINDOW,
                    persistence_days: int = PERSISTENCE_DAYS, max_flips: int = MAX_FLIPS) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Rule rate by put weight and magnitude threshold on the stored call and put legs.

    The daily value is ``call_gex + w * put_gex`` (put_gex is stored negative); the rule then runs unchanged with
    the magnitude threshold ``thr`` billion.  Returns (cells, shifts): ``cells`` has one row per (put_weight,
    threshold_bn, period) with n_windows, n_detected, rate_pct; ``shifts`` one row per (put_weight, threshold_bn,
    baseline) with the rate of 2024-2025 minus the rate of the baseline period in points and its sign.
    """
    cells, shifts = [], []
    for w in weights:
        net = days["call_gex"].to_numpy(float) + float(w) * days["put_gex"].to_numpy(float)
        win = window_frame(days, net, window)
        for thr in thresholds_bn:
            verdict = rule_verdict(win, persistence_days, thr * 1e9, max_flips)
            rate = {}
            for period in periods:
                sel = period_mask(win["window_end"], period)
                n, k = int(sel.sum()), int(verdict[sel].sum())
                rate[period] = 100.0 * k / n if n else math.nan
                cells.append({"put_weight": float(w), "threshold_bn": float(thr), "period": period, "n_windows": n,
                              "n_detected": k, "rate_pct": rate[period]})
            for base in periods:
                if base != LATE and LATE in rate:
                    diff = rate[LATE] - rate[base]
                    shifts.append({"put_weight": float(w), "threshold_bn": float(thr), "baseline": base,
                                   "rate_late_pct": rate[LATE], "rate_baseline_pct": rate[base], "shift_pp": diff,
                                   "sign": int(np.sign(diff))})
    return pd.DataFrame(cells), pd.DataFrame(shifts)


def sign_crossings(shifts: pd.DataFrame) -> pd.DataFrame:
    """Put weights at which the period shift changes sign (linear interpolation between neighbouring grid weights),
    per threshold and baseline; empty when the sign never changes."""
    rows = []
    for (thr, base), g in shifts.groupby(["threshold_bn", "baseline"]):
        g = g.sort_values("put_weight")
        w, d = g["put_weight"].to_numpy(), g["shift_pp"].to_numpy()
        for i in range(len(w) - 1):
            if d[i] != d[i + 1] and d[i] * d[i + 1] <= 0 and not (d[i] == 0 and d[i + 1] == 0):
                at = w[i] if d[i] == 0 else w[i] + (w[i + 1] - w[i]) * d[i] / (d[i] - d[i + 1])
                rows.append({"threshold_bn": thr, "baseline": base, "put_weight": float(at),
                             "from_sign": int(np.sign(d[i])), "to_sign": int(np.sign(d[i + 1]))})
    return pd.DataFrame(rows, columns=["threshold_bn", "baseline", "put_weight", "from_sign", "to_sign"])


# --------------------------------------------------------------------------- E3
def interval_table(flags: np.ndarray, window_end: pd.Series, window_start: pd.Series, ctx, block_lengths: Sequence[int],
                   n_boot: int, seed: int, tag: str) -> pd.DataFrame:
    """Rate in percent and 95 percent intervals by every method, for one ordered 0/1 sequence of windows.

    Methods: ``wilson`` (treats the n windows as independent), ``quarter_block`` (05_report.py: calendar quarters as
    blocks), ``moving_block`` and ``circular_block`` for each block length, ``episode_bootstrap`` (cycles of
    non-detected and detected runs, see ``episode_bootstrap_rate``), ``wilson_ess_acf`` and ``wilson_ess_batch30``
    (Wilson interval with n replaced by the effective sample size, k scaled to keep the rate).
    """
    R = report()
    f = np.asarray(flags, bool)
    n, k = len(f), int(f.sum())
    rows = []

    def add(method, block, lo, hi, n_eff=math.nan):
        rows.append({"method": method, "block_len": block, "rate_pct": 100.0 * k / n, "ci_lo_pct": lo, "ci_hi_pct": hi,
                     "n_effective": n_eff})

    lo, hi = R.wilson_pct(k, n)
    add("wilson", 0, lo, hi, float(n))
    frame = pd.DataFrame({"window_end": pd.to_datetime(window_end).to_numpy(), "window_start": pd.to_datetime(window_start).to_numpy(),
                          "label": f.astype(int)})
    q = R.rate_entry(frame, ctx)["bootstrap_quarter"]
    add("quarter_block", 0, q["ci_pct"][0], q["ci_pct"][1], float(q["n_blocks"]))
    for L in block_lengths:
        for circular in (False, True):
            _, lo, hi = rate_interval(f, L, n_boot, make_rng(seed, tag, "mbb", L, circular), circular)
            add("circular_block" if circular else "moving_block", L, lo, hi)
    _, lo, hi = episode_bootstrap_rate(f, n_boot, make_rng(seed, tag, "episode"))
    add("episode_bootstrap", 0, lo, hi)
    for name, ess in (("wilson_ess_acf", ess_acf(f.astype(float))), ("wilson_ess_batch30", ess_batch_means(f.astype(float), 30))):
        if np.isfinite(ess):
            lo, hi = R.wilson_pct(int(round(k / n * ess)), int(round(ess)))
            add(name, 0, lo, hi, ess)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- E4
def baseline_masks(window_end: pd.Series) -> Dict[str, np.ndarray]:
    """Baseline periods for the shift: 2020-2023, 2008-2019, 2008-2023 and the 2020-2023 / 2008-2023 baselines
    without the year 2022 (windows by the year of window_end)."""
    y = pd.to_datetime(window_end).dt.year.to_numpy()
    return {"2020-2023": (y >= 2020) & (y <= 2023), "2008-2019": (y >= 2008) & (y <= 2019),
            "2008-2023": (y >= 2008) & (y <= 2023), "2020-2023 without 2022": (y >= 2020) & (y <= 2023) & (y != 2022),
            "2008-2023 without 2022": (y >= 2008) & (y <= 2023) & (y != 2022)}


def shift_margin_table(win: pd.DataFrame, thresholds_bn: Sequence[float], block_lengths: Sequence[int], n_boot: int,
                       seed: int, margin_pp: float = MARGIN_PP, shared_end: Optional[Sequence[Any]] = None, ctx=None,
                       persistence_days: int = PERSISTENCE_DAYS, max_flips: int = MAX_FLIPS) -> pd.DataFrame:
    """Rise of the 2024-2025 rate over each baseline, with moving-block intervals and the margin test.

    ``win`` is a window_frame of the complete series.  For each window set (``all`` windows, and ``shared`` windows
    whose window_end is in ``shared_end``, the windows the published inputs also have), baseline, threshold and
    block length: ``shift_pp`` = late rate minus baseline rate (points), a moving-block interval of both periods
    resampled independently (blocks inside one run of consecutive windows, so a removed year is never bridged),
    ``upper_below_margin`` = interval upper bound < ``margin_pp`` and ``lower_above_minus_margin`` = lower bound >
    -``margin_pp``.  When ``ctx`` is given the quarter-block interval of 05_report.py (``R.shift_entry``) is added.
    """
    R = report()
    sets = {"all": np.ones(len(win), bool)}
    if shared_end is not None:
        sets["shared"] = win["window_end"].isin(pd.to_datetime(pd.Series(list(shared_end)))).to_numpy()
    rows = []
    for set_name, in_set in sets.items():
        for base_name, base_all in baseline_masks(win["window_end"]).items():
            for thr in thresholds_bn:
                verdict = rule_verdict(win, persistence_days, thr * 1e9, max_flips)
                late_sel = period_mask(win["window_end"], LATE) & in_set
                base_sel = base_all & in_set
                if late_sel.sum() == 0 or base_sel.sum() == 0:
                    continue
                late, early = verdict[late_sel].astype(float), verdict[base_sel].astype(float)
                seg = segment_ids(np.flatnonzero(base_sel))
                quarter = (math.nan, math.nan)
                if ctx is not None:
                    def frame(sel):
                        return pd.DataFrame({"window_start": win.loc[sel, "window_start"], "window_end": win.loc[sel, "window_end"],
                                             "label": verdict[sel].astype(int)})
                    lab = R.Labeller("classifier", FULL, "SPY")
                    quarter = tuple(R.shift_entry(lab, frame(base_sel), frame(late_sel), ctx)["bootstrap_quarter"]["diff_ci_pp"])
                for L, circular in itertools.product(block_lengths, (False, True)):
                    r = shift_interval(late, early, L, n_boot, make_rng(seed, "E4", set_name, base_name, thr, L, circular), circular, seg)
                    rows.append({"window_set": set_name, "baseline": base_name, "threshold_bn": float(thr), "block_len": int(L),
                                 "circular": circular,
                                 "n_late": int(late_sel.sum()), "n_baseline": int(base_sel.sum()),
                                 "rate_late_pct": 100 * float(late.mean()), "rate_baseline_pct": 100 * float(early.mean()),
                                 **r, "margin_pp": float(margin_pp),
                                 "upper_below_margin": bool(r["ci_hi_pp"] < margin_pp),
                                 "lower_above_minus_margin": bool(r["ci_lo_pp"] > -margin_pp),
                                 "quarter_ci_lo_pp": quarter[0], "quarter_ci_hi_pp": quarter[1]})
    return pd.DataFrame(rows)


def margin_summary(table: pd.DataFrame, block_len: int = PRIMARY_BLOCK, circular: bool = False) -> pd.DataFrame:
    """Per window set and baseline at one block length and block type: thresholds tested, thresholds with an upper
    bound below the margin, with a positive point estimate, and the largest upper bound."""
    t = table[(table["block_len"] == block_len) & (table["circular"] == circular)]
    g = t.groupby(["window_set", "baseline"], sort=True)
    return g.agg(n_thresholds=("threshold_bn", "size"), n_upper_below_margin=("upper_below_margin", "sum"),
                 n_positive_shift=("shift_pp", lambda s: int((s > 0).sum())), max_ci_hi_pp=("ci_hi_pp", "max")).reset_index()


# --------------------------------------------------------------------------- E6
def scale_free_variants(days: pd.DataFrame, win: pd.DataFrame, reference: Tuple[int, int], gross_days: int = 252,
                        gross_min_days: int = 120, fixed_share: float = 0.125) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """Rule verdicts under scale-free magnitude thresholds: {variant: (verdict, threshold in USD per window)}.

    ``days`` is the complete series sorted by date (columns net_gex, call_gex, put_gex, spot) and ``win`` its
    window_frame.  Spot is the stored ``spot`` of each trading day (the underlying price of the series row; days
    filled from the spot-fill log are included as stored); the spot of a window is the mean over its 30 days.  The
    reference spot is the median daily spot over the reference years ``reference`` (first, last).  Variants:

    * ``fixed_5bn``: 5e9 (the paper);
    * ``spot_linear``: 5e9 * window_spot / reference_spot;
    * ``spot_squared``: 5e9 * (window_spot / reference_spot) ** 2;
    * ``trailing_gross_calibrated``: share * trailing_gross where trailing_gross is the mean of call + |put| over the
      ``gross_days`` rows ending on the window's last day (at least ``gross_min_days`` rows, else the window is
      dropped, NaN threshold) and share = 5e9 / mean gross over the reference years;
    * ``trailing_gross_12.5pct``: the same with a fixed share of ``fixed_share``;
    * ``no_magnitude``: threshold 0 (persistence and flips only).
    """
    year = pd.to_datetime(days["trading_date"]).dt.year
    spot = days["spot"].to_numpy(float)
    gross = days["call_gex"].to_numpy(float) + np.abs(days["put_gex"].to_numpy(float))
    ref = (year >= reference[0]) & (year <= reference[1])
    ref_spot = float(np.median(spot[ref.to_numpy()]))
    share = MAGNITUDE_USD / float(gross[ref.to_numpy()].mean())
    win_spot = pd.Series(spot).rolling(WINDOW).mean().to_numpy()[WINDOW - 1:]
    trailing = pd.Series(gross).rolling(gross_days, min_periods=gross_min_days).mean().to_numpy()[WINDOW - 1:]
    thresholds = {
        "fixed_5bn": np.full(len(win), MAGNITUDE_USD),
        "spot_linear": MAGNITUDE_USD * win_spot / ref_spot,
        "spot_squared": MAGNITUDE_USD * (win_spot / ref_spot) ** 2,
        "trailing_gross_calibrated": share * trailing,
        "trailing_gross_12.5pct": fixed_share * trailing,
        "no_magnitude": np.zeros(len(win)),
    }
    out = {}
    for name, thr in thresholds.items():
        ok = rule_verdict(win, magnitude_usd=0.0) & (win["mean_abs"].to_numpy() >= np.nan_to_num(thr, nan=np.inf))
        out[name] = (np.where(np.isnan(thr), False, ok), thr)
    out["_share"] = (np.array([share]), np.array([ref_spot]))
    return out


def scale_by_year(days: pd.DataFrame) -> pd.DataFrame:
    """Per calendar year of the complete series: days, mean spot, mean |net GEX| (billions), mean gross (call + |put|, billions)."""
    d = days.assign(year=pd.to_datetime(days["trading_date"]).dt.year, abs_net=days["net_gex"].abs() / 1e9,
                    gross=(days["call_gex"] + days["put_gex"].abs()) / 1e9)
    g = d.groupby("year").agg(n_days=("spot", "size"), mean_spot=("spot", "mean"), mean_abs_net_bn=("abs_net", "mean"),
                              mean_gross_bn=("gross", "mean")).reset_index()
    return g


def fold_ratio(by_year: pd.DataFrame, first: int, last: int) -> Dict[str, float]:
    """last-year over first-year ratios of mean spot, its square, mean |net| and mean gross (annual means in ``by_year``)."""
    a, b = by_year.set_index("year").loc[first], by_year.set_index("year").loc[last]
    spot = float(b["mean_spot"] / a["mean_spot"])
    return {"first_year": first, "last_year": last, "spot": spot, "spot_squared": spot ** 2,
            "abs_net": float(b["mean_abs_net_bn"] / a["mean_abs_net_bn"]), "gross": float(b["mean_gross_bn"] / a["mean_gross_bn"])}


# --------------------------------------------------------------------------- E9
ERAS = (("2008-2013", 2008, 2013), ("2014-2022", 2014, 2022), ("2023-2026", 2023, 2026), ("2024-2025", 2024, 2025),
        ("all", 2008, 2026))


def paired_labels(full: pd.DataFrame, ex: pd.DataFrame, threshold_bn: float = PAPER_THRESHOLD_BN) -> pd.DataFrame:
    """Verdicts of two window frames on the windows (by window_end) they share: window_end, full, ex (bool)."""
    a = full.assign(full=rule_verdict(full, magnitude_usd=threshold_bn * 1e9))[["window_end", "full"]]
    b = ex.assign(ex=rule_verdict(ex, magnitude_usd=threshold_bn * 1e9))[["window_end", "ex"]]
    return a.merge(b, on="window_end").sort_values("window_end").reset_index(drop=True)


def discordance_row(full: np.ndarray, ex: np.ndarray) -> Dict[str, Any]:
    """Counts and rates of a pair of verdicts: n, rates, both/only/neither counts, discordant windows (share of all
    windows and of the windows either series detects), gap = rate_full - rate_ex (points), Cohen's kappa."""
    f, e = np.asarray(full, bool), np.asarray(ex, bool)
    n = len(f)
    both, only_f, only_e, neither = int((f & e).sum()), int((f & ~e).sum()), int((~f & e).sum()), int((~f & ~e).sum())
    either = both + only_f + only_e
    po = (both + neither) / n if n else math.nan
    pe = (f.mean() * e.mean() + (1 - f.mean()) * (1 - e.mean())) if n else math.nan
    kappa = (po - pe) / (1 - pe) if n and pe < 1 else math.nan
    return {"n_windows": n, "rate_full_pct": 100 * f.mean() if n else math.nan, "rate_ex0dte_pct": 100 * e.mean() if n else math.nan,
            "both": both, "only_full": only_f, "only_ex0dte": only_e, "neither": neither, "discordant": only_f + only_e,
            "discordant_pct_of_windows": 100 * (only_f + only_e) / n if n else math.nan, "detected_by_either": either,
            "discordant_pct_of_either": 100 * (only_f + only_e) / either if either else math.nan,
            "gap_pp": 100 * (f.mean() - e.mean()) if n else math.nan, "kappa": kappa}


def era_interaction(pair: pd.DataFrame, era_a: Tuple[int, int], era_b: Tuple[int, int], block_len: int, n_boot: int,
                    rng: np.random.Generator, circular: bool = False) -> Dict[str, float]:
    """Interaction = gap(era b) - gap(era a) in points, with gap = rate(full) - rate(ex0dte) among the windows of the era,
    and a moving-block interval from resampling the whole ordered paired sequence (the gap of each era is
    recomputed from the windows of that era in the resample)."""
    y = pair["window_end"].dt.year.to_numpy()
    d = pair["full"].to_numpy(float) - pair["ex"].to_numpy(float)
    a, b = (y >= era_a[0]) & (y <= era_a[1]), (y >= era_b[0]) & (y <= era_b[1])
    comp = np.column_stack([d * a, a, d * b, b]).astype(float)
    point = 100 * (comp[:, 2].sum() / comp[:, 3].sum() - comp[:, 0].sum() / comp[:, 1].sum())
    s = mbb_sums(comp, block_len, n_boot, rng, circular)
    with np.errstate(divide="ignore", invalid="ignore"):
        draws = 100 * (s[:, 2] / s[:, 3] - s[:, 0] / s[:, 1])
    lo, hi = percentile_ci(draws)
    return {"gap_a_pp": 100 * comp[:, 0].sum() / comp[:, 1].sum(), "gap_b_pp": 100 * comp[:, 2].sum() / comp[:, 3].sum(),
            "interaction_pp": float(point), "ci_lo_pp": lo, "ci_hi_pp": hi}


def same_day_shares(days: pd.DataFrame) -> pd.DataFrame:
    """Per year, the same-day-expiry (0DTE) part of the complete series against two denominators.

    ``days`` has one row per trading day with net_full, net_ex0dte, call_full, put_full, call_ex, put_ex and
    gex_0dte (the stored same-day leg, else net_full - net_ex0dte).  Columns (percent unless noted):
    ``abs_0dte_share_of_abs_net`` = sum|gex_0dte| / sum|net_full| (what 05_report.py prints as abs_0dte_share_pct),
    ``abs_0dte_share_of_gross`` = sum|gex_0dte| / sum(call_full + |put_full|), ``gross_removed_share`` =
    (gross_full - gross_ex0dte) / gross_full with gross = call + |put|, ``net_removed_share_of_abs_net`` =
    sum|net_full - net_ex0dte| / sum|net_full|, and ``sign_flip_pct`` = share of days whose net sign differs.
    """
    d = days.assign(year=pd.to_datetime(days["trading_date"]).dt.year)
    d["gross_full"] = d["call_full"] + d["put_full"].abs()
    d["gross_ex"] = d["call_ex"] + d["put_ex"].abs()
    rows = []
    for year, g in list(d.groupby("year")) + [("all", d)]:
        rows.append({"year": year, "n_days": len(g),
                     "abs_0dte_share_of_abs_net": 100 * g["gex_0dte"].abs().sum() / g["net_full"].abs().sum(),
                     "abs_0dte_share_of_gross": 100 * g["gex_0dte"].abs().sum() / g["gross_full"].sum(),
                     "gross_removed_share": 100 * (g["gross_full"].sum() - g["gross_ex"].sum()) / g["gross_full"].sum(),
                     "net_removed_share_of_abs_net": 100 * (g["net_full"] - g["net_ex0dte"]).abs().sum() / g["net_full"].abs().sum(),
                     "sign_flip_pct": 100 * float(((g["net_full"] > 0) != (g["net_ex0dte"] > 0)).mean())})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- E13
def lineage_counts(a: pd.DataFrame, b: pd.DataFrame, a_name: str, b_name: str) -> pd.DataFrame:
    """Windows with the same and with different verdicts between two label sets, per year of window_end.

    ``a`` and ``b`` have window_end and a boolean ``label``; the join is on window_end.  Columns: comparison, year
    (or ``all``), n_common, equal, different, only_a (a yes, b no), only_b, rate_a_pct, rate_b_pct.
    """
    m = a[["window_end", "label"]].merge(b[["window_end", "label"]], on="window_end", suffixes=("_a", "_b"))
    m["year"] = m["window_end"].dt.year
    rows = []
    for year, g in list(m.groupby("year")) + [("all", m)]:
        x, y = g["label_a"].to_numpy(bool), g["label_b"].to_numpy(bool)
        rows.append({"comparison": f"{a_name} vs {b_name}", "year": year, "n_common": len(g), "equal": int((x == y).sum()),
                     "different": int((x != y).sum()), "only_a": int((x & ~y).sum()), "only_b": int((~x & y).sum()),
                     "rate_a_pct": 100 * float(x.mean()), "rate_b_pct": 100 * float(y.mean())})
    return pd.DataFrame(rows)


def hybrid_values(published_dates: pd.Series, complete: pd.DataFrame, call_only: pd.DataFrame,
                  break_date: pd.Timestamp = BREAK_DATE) -> pd.Series:
    """The lineage hypothesis as a daily series on ``published_dates``: the complete net value before ``break_date``
    and the call leg of the call-only series from ``break_date`` on (NaN where the source has no row)."""
    comp = complete.set_index(pd.to_datetime(complete["trading_date"]))["net_gex"]
    call = call_only.set_index(pd.to_datetime(call_only["trading_date"]))["call_gex"]
    d = pd.to_datetime(published_dates)
    before = d.map(comp)
    after = d.map(call)
    return pd.Series(np.where(d < break_date, before, after), index=published_dates.index)


# --------------------------------------------------------------------------- loading
def load_inputs(parquet_root: Path):
    """(Data, series_by_key) from the parquet copies with the loaders of 05_report.py (typed, latest answer per key)."""
    R = report()
    raw, source = R.read_parquet_tables(Path(parquet_root))
    data = R.build_data(raw, source)
    return data


def make_context(data, seed: Optional[int] = None, n_boot: Optional[int] = None):
    """05_report.Context for the quarter-block bootstrap; defaults to the report's own seed and draws, so that the
    quarter-block intervals equal the ones the paper prints (stats.yaml)."""
    R = report()
    return R.Context(data=data, results_dir=Path("."), seed=R.SEED if seed is None else seed,
                     n_boot=R.N_BOOT if n_boot is None else n_boot)


def stored_window_frame(data, key: str, symbol: str = "SPY") -> pd.DataFrame:
    """Stored windows of a series ordered by window_end (clf_* columns)."""
    w = data.windows[(data.windows["series_key"] == key) & (data.windows["symbol"] == symbol)]
    return w.sort_values("window_end").reset_index(drop=True)


# --------------------------------------------------------------------------- analysis drivers
class Output:
    """Writes the result files of a run with a stable layout (sorted rows are the caller's job; floats rounded to 6 decimals)."""

    def __init__(self, out: Path):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.files: Dict[str, Dict[str, Any]] = {}

    def csv(self, name: str, frame: pd.DataFrame) -> None:
        frame.round(6).to_csv(self.out / name, index=False, lineterminator="\n")
        self.files[name] = {"rows": int(len(frame)), "columns": list(frame.columns)}
        logger.info("wrote %s (%d rows)", name, len(frame))

    def yaml(self, name: str, payload: Dict[str, Any]) -> None:
        with open(self.out / name, "w") as fh:
            yaml.safe_dump(report().to_native(payload), fh, sort_keys=False, default_flow_style=False, width=110)
        self.files[name] = {"keys": list(payload)}
        logger.info("wrote %s", name)


def round_native(obj: Any, digits: int = 6) -> Any:
    """Plain Python types with floats rounded, for YAML."""
    return report().to_native(_round(obj, digits))


def _round(obj: Any, digits: int) -> Any:
    if isinstance(obj, dict):
        return {k: _round(v, digits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round(v, digits) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return None if not math.isfinite(float(obj)) else round(float(obj), digits)
    return obj


def complete_windows(data) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """(complete series rows, its window_frame) for SPY new_full."""
    days = series_frame(data.series, FULL)
    return days, window_frame(days)


def gate_rule(data, notes: List[str]) -> Dict[str, Any]:
    """Gate: the vectorised rule over the stored series reproduces clf_should_detect on every stored window, for every
    series that has windows (SPY), from the daily series and (new_full) from call_gex + put_gex."""
    out: Dict[str, Any] = {}
    for key in sorted(data.windows["series_key"].unique()):
        stored = stored_window_frame(data, key)
        days = series_frame(data.series, key)
        if stored.empty or days.empty or key in ("intraday_t0",):
            continue
        win = window_frame(days)
        merged = stored[["window_end", "window_start", "clf_should_detect"]].merge(
            win.assign(recomputed=rule_verdict(win))[["window_end", "window_start", "recomputed"]], on="window_end", how="outer",
            suffixes=("", "_series"), indicator=True)
        both = merged[merged["_merge"] == "both"]
        out[key] = {"stored_windows": int(len(stored)), "series_windows": int(len(win)), "matched": int(len(both)),
                    "equal": int((both["clf_should_detect"].astype(bool) == both["recomputed"]).sum()),
                    "start_equal": int((both["window_start"] == both["window_start_series"]).sum())}
        if out[key]["equal"] != out[key]["matched"] or out[key]["matched"] != len(stored):
            notes.append(f"gate: {key} recomputed verdicts differ on {out[key]['matched'] - out[key]['equal']} of "
                         f"{out[key]['matched']} matched windows ({len(stored)} stored)")
    return out


def run_e2(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    days, win = complete_windows(data)
    stored = stored_window_frame(data, FULL)
    # gate: w = 1 and 5bn on call + put, and on the stored net, against the stored verdict
    net_cp = days["call_gex"].to_numpy(float) + days["put_gex"].to_numpy(float)
    v_cp = rule_verdict(window_frame(days, net_cp))
    v_net = rule_verdict(win)
    ref = stored.set_index("window_end")["clf_should_detect"].astype(bool)
    idx = win["window_end"]
    s = ref.reindex(idx).to_numpy()
    gate = {"stored_windows": int(len(stored)), "recomputed_windows": int(len(win)),
            "equal_call_plus_put": int((v_cp == s).sum()), "equal_stored_net": int((v_net == s).sum()),
            "max_abs_net_minus_call_plus_put_usd": float(np.abs(days["net_gex"].to_numpy(float) - net_cp).max()),
            "pass": bool((v_cp == s).all() and (v_net == s).all() and len(stored) == len(win))}
    if not gate["pass"]:
        notes.append(f"E2 gate failed: call+put equals stored on {gate['equal_call_plus_put']} of {len(win)} windows")
    cells, shifts = put_weight_grid(days, params["put_weights"], params["grid_bn"])
    out.csv("e2_put_weight_grid.csv", cells.sort_values(["put_weight", "threshold_bn", "period"]))
    out.csv("e2_period_shift.csv", shifts.sort_values(["baseline", "threshold_bn", "put_weight"]))
    cross = sign_crossings(shifts)
    out.csv("e2_sign_crossings.csv", cross.sort_values(["baseline", "threshold_bn", "put_weight"]))
    out.yaml("e2_gate.yaml", round_native(gate))
    return gate


def run_e3(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    days, win = complete_windows(data)
    ctx = make_context(data)
    sel = period_mask(win["window_end"], LATE)
    sources = {"rule": rule_verdict(win)[sel]}
    llm = data.detections
    llm = llm[(llm["arm"] == "full_spy") & llm["parsed"] & (llm["repeat_index"] == 0) & (llm["symbol"] == "SPY")]
    luna = win.loc[sel, ["window_end"]].merge(llm[["window_end", "regime_detected"]], on="window_end", how="left")
    if luna["regime_detected"].notna().all():
        sources["gpt-6-luna"] = luna["regime_detected"].astype(bool).to_numpy()
    ep_rows, int_rows, ess_rows = [], [], []
    w = win.loc[sel].reset_index(drop=True)
    for name, flags in sources.items():
        eps = find_episodes(w["window_end"], flags)
        eps.insert(0, "source", name)
        ep_rows.append(eps)
        interval = interval_table(flags, w["window_end"], w["window_start"], ctx, params["block_lengths"], params["n_boot"],
                                  params["seed"], name)
        interval.insert(0, "source", name)
        int_rows.append(interval)
        x = flags.astype(float)
        row = {"source": name, "n_windows": len(x), "n_detected": int(x.sum()), "rate_pct": 100 * float(x.mean()),
               "n_episodes": int(len(eps)), "windows_per_episode_mean": float(eps["length"].mean()) if len(eps) else math.nan,
               "ess_acf": ess_acf(x), "ess_batch_30": ess_batch_means(x, 30),
               "ess_batch_sqrt_n": ess_batch_means(x, max(2, int(math.isqrt(len(x))))),
               "n_nonoverlapping_30d": len(x) / WINDOW}
        ess_rows.append(row)
    out.csv("e3_episodes.csv", pd.concat(ep_rows, ignore_index=True))
    out.csv("e3_intervals.csv", pd.concat(int_rows, ignore_index=True))
    ess = pd.DataFrame(ess_rows)
    out.csv("e3_ess.csv", ess)
    return {"sources": list(sources), "episodes_rule": int(len(ep_rows[0]))}


def run_e4(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    days, win = complete_windows(data)
    published = stored_window_frame(data, PUBLISHED)
    ctx = make_context(data)
    table = shift_margin_table(win, params["shift_grid_bn"], params["block_lengths"], params["n_boot"], params["seed"],
                               params["margin_pp"], published["window_end"], ctx)
    table = table.sort_values(["window_set", "baseline", "threshold_bn", "block_len", "circular"])
    out.csv("e4_shift_margin.csv", table)
    summary = pd.concat([margin_summary(table, L, c).assign(block_len=L, circular=c) for L in params["block_lengths"]
                         for c in (False, True)], ignore_index=True)
    out.csv("e4_summary.csv", summary[["window_set", "baseline", "block_len", "circular", "n_thresholds", "n_upper_below_margin",
                                       "n_positive_shift", "max_ci_hi_pp"]])
    n_pub = int(win["window_end"].isin(published["window_end"]).sum())
    return {"shared_windows_in_complete": n_pub, "published_windows": int(len(published))}


def arm_frames(data) -> pd.DataFrame:
    """Scored answers of every SPY arm with a stored window: one row per (arm, window), repeats and recovered rows out.

    Columns: arm, model, series_key, arm_role, window_end, label (bool) and the stored clf_* inputs of the window.
    """
    R = report()
    det = data.detections
    det = det[(det["symbol"] == "SPY") & det["parsed"] & (det["repeat_index"] == 0) & det["arm_role"].isin(["primary", "backfill"])
              & det["clf_should_detect"].notna()]
    det = R.published_rows(det).drop_duplicates(["arm", "window_end"], keep="last")
    cols = ["arm", "model", "series_key", "arm_role", "window_end", "regime_detected", "clf_should_detect",
            "clf_positive_days", "clf_negative_days", "clf_avg_magnitude", "clf_sign_flips"]
    out = det[cols].rename(columns={"regime_detected": "label"})
    out["label"] = out["label"].astype(bool)
    out["clf_should_detect"] = out["clf_should_detect"].astype(bool)
    return out.sort_values(["arm", "window_end"]).reset_index(drop=True)


def run_e1(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    arms = arm_frames(data)
    luna = arms[(arms["model"] == "gpt-6-luna") & (arms["arm_role"] == "primary")].set_index(["series_key", "window_end"])["label"]
    luna = luna[~luna.index.duplicated(keep="last")]
    comp_rows, cont_rows = [], []
    for (arm, model, series_key), g in arms.groupby(["arm", "model", "series_key"], sort=True):
        g = g.sort_values("window_end").reset_index(drop=True)
        lun = luna.reindex(pd.MultiIndex.from_arrays([[series_key] * len(g), g["window_end"]])).to_numpy()
        for period in ("2008-2019", "2020-2023", "2024-2025", "2026", "all"):
            sel = period_mask(g["window_end"], period)
            if sel.sum() == 0:
                continue
            h = g[sel].reset_index(drop=True)
            r, y = h["clf_should_detect"].to_numpy(bool), h["label"].to_numpy(bool)
            pos, neg, mag, fl = (h[c].to_numpy() for c in ("clf_positive_days", "clf_negative_days", "clf_avg_magnitude", "clf_sign_flips"))
            comps = comparator_labels(pos, neg, mag, fl)
            row = {"arm": arm, "model": model, "series_key": series_key, "period": period, "n_windows": len(h),
                   "rule_rate_pct": 100 * float(r.mean()), "arm_rate_pct": 100 * float(y.mean()),
                   "arm_agreement_pct": 100 * float((y == r).mean())}
            lo_hi = rate_interval((y == r), params["primary_block"], params["n_boot"], make_rng(params["seed"], "E1", arm, period, "arm"))
            row["arm_agreement_lo_pct"], row["arm_agreement_hi_pct"] = lo_hi[1], lo_hi[2]
            for name, label in comps.items():
                row[f"{name}_agreement_pct"] = 100 * float((label == r).mean())
            fl_ci = rate_interval((comps["flips_only"] == r), params["primary_block"], params["n_boot"],
                                  make_rng(params["seed"], "E1", arm, period, "flips"))
            row["flips_only_agreement_lo_pct"], row["flips_only_agreement_hi_pct"] = fl_ci[1], fl_ci[2]
            best = max(comps, key=lambda k: float((comps[k] == r).mean()))
            row["best_trivial"], row["best_trivial_agreement_pct"] = best, 100 * float((comps[best] == r).mean())
            if model != "gpt-6-luna":
                lv = lun[sel]
                ok = pd.notna(lv)
                row["luna_n_common"] = int(ok.sum())
                row["luna_agreement_pct"] = 100 * float((lv[ok].astype(bool) == r[ok]).mean()) if ok.any() else math.nan
            comp_rows.append(row)
            if period in ("2008-2019", "2020-2023", "2024-2025", "all"):
                for dname, mg in params["contested_definitions"].items():
                    cm = contested_mask(pos, neg, mag, fl, mg["days"], mg["billions"], mg["flips"], mg["flips_below"])
                    c = cm["contested"].to_numpy()
                    crow = {"arm": arm, "model": model, "series_key": series_key, "period": period, "definition": dname,
                            "n_windows": len(h), "n_contested": int(c.sum()), "contested_pct": 100 * float(c.mean()),
                            "n_by_persistence": int(cm["by_persistence"].sum()), "n_by_magnitude": int(cm["by_magnitude"].sum()),
                            "n_by_flips": int(cm["by_flips"].sum()), "rule_yes_in_contested": int((c & r).sum()),
                            "arm_discordant_total": int((y != r).sum()), "arm_discordant_in_contested": int((c & (y != r)).sum())}
                    predictors = {"arm": y, "flips_only": comps["flips_only"], "always_yes": comps["always_yes"]}
                    for pname, pred in predictors.items():
                        sm = confusion_summary(pred, r, c, params["primary_block"], params["n_boot"],
                                               (params["seed"], ("E1c", arm, period, dname, pname)))
                        for k, v in sm.items():
                            if k != "n":
                                crow[f"{pname}_{k}"] = v
                    s_un = confusion_summary(y, r, ~c, params["primary_block"], params["n_boot"],
                                             (params["seed"], ("E1u", arm, period, dname)))
                    crow["arm_uncontested_agree_pct"] = s_un["agree_pct"]
                    cont_rows.append(crow)
    out.csv("e1_comparators.csv", pd.DataFrame(comp_rows).sort_values(["arm", "period"]))
    out.csv("e1_contested.csv", pd.DataFrame(cont_rows).sort_values(["definition", "arm", "period"]))
    return {"arms": int(arms["arm"].nunique())}


def run_e6(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    days, win = complete_windows(data)
    rows, shift_rows = [], []
    refs = {"2024-2025": (2024, 2025), "2020": (2020, 2020), "2010": (2010, 2010)}
    extra: Dict[str, Any] = {}
    for ref_name, ref in refs.items():
        variants = scale_free_variants(days, win, ref)
        share, ref_spot = variants.pop("_share")
        extra[ref_name] = {"reference_spot": float(ref_spot[0]), "calibrated_gross_share": float(share[0])}
        for name, (verdict, thr) in variants.items():
            if name in ("fixed_5bn", "no_magnitude") and ref_name != "2024-2025":
                continue  # reference-independent variants once
            usable = ~np.isnan(thr)
            for period in PERIOD_SPANS:
                sel = period_mask(win["window_end"], period) & usable
                n, k = int(sel.sum()), int(verdict[sel].sum())
                rows.append({"variant": name, "reference_years": ref_name if name not in ("fixed_5bn", "no_magnitude") else "none",
                             "period": period, "n_windows": n, "n_detected": k, "rate_pct": 100.0 * k / n if n else math.nan,
                             "mean_threshold_bn": float(np.nanmean(thr[sel])) / 1e9 if n else math.nan})
            late_sel, base_sel = period_mask(win["window_end"], LATE) & usable, period_mask(win["window_end"], "2020-2023") & usable
            r = shift_interval(verdict[late_sel].astype(float), verdict[base_sel].astype(float), params["primary_block"],
                               params["n_boot"], make_rng(params["seed"], "E6", name, ref_name))
            shift_rows.append({"variant": name, "reference_years": ref_name if name not in ("fixed_5bn", "no_magnitude") else "none",
                               "baseline": "2020-2023", "block_len": params["primary_block"], **r})
    out.csv("e6_scale_free.csv", pd.DataFrame(rows).drop_duplicates())
    out.csv("e6_scale_free_shift.csv", pd.DataFrame(shift_rows).drop_duplicates(["variant", "reference_years"]))
    by_year = scale_by_year(days)
    out.csv("e6_scale_by_year.csv", by_year)
    folds = {f"{a}_to_{b}": fold_ratio(by_year, a, b) for a, b in ((2009, 2026), (2010, 2026), (2010, 2025))}
    out.yaml("e6_scale_facts.yaml", round_native({"reference": extra, "fold_ratios": folds,
             "spot_source": "series.spot of each trading day (underlying_price; the 19 days in series_metadata.spot_fill are as stored); "
                            "window spot = mean over its 30 days; reference spot = median daily spot over the reference years"}))
    return {}


def run_e9(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    R = report()
    dfull, wfull = complete_windows(data)
    dex = series_frame(data.series, EX0DTE)
    wex = window_frame(dex)
    pair = paired_labels(wfull, wex)
    stored = stored_window_frame(data, FULL).merge(stored_window_frame(data, EX0DTE), on="window_end", suffixes=("_f", "_x"))
    chk = pair.merge(stored[["window_end", "clf_should_detect_f", "clf_should_detect_x"]], on="window_end")
    gate = {"windows_paired": int(len(pair)), "windows_checked": int(len(chk)),
            "full_equals_stored": int((chk["full"] == chk["clf_should_detect_f"].astype(bool)).sum()),
            "ex_equals_stored": int((chk["ex"] == chk["clf_should_detect_x"].astype(bool)).sum())}
    if gate["full_equals_stored"] != len(pair) or gate["ex_equals_stored"] != len(pair):
        notes.append(f"E9 gate: recomputed verdicts differ from stored ({gate})")
    rows, wd_rows = [], []
    for era, first, last in ERAS:
        e = pair[(pair["window_end"].dt.year >= first) & (pair["window_end"].dt.year <= last)]
        rows.append({"era": era, **discordance_row(e["full"].to_numpy(), e["ex"].to_numpy())})
        if era in ("2014-2022", "2023-2026", "2024-2025"):
            for wd, g in e.groupby(e["window_end"].dt.dayofweek):
                wd_rows.append({"era": era, "weekday": weekday_name(wd), **discordance_row(g["full"].to_numpy(), g["ex"].to_numpy())})
    out.csv("e9_pair_by_era.csv", pd.DataFrame(rows))
    out.csv("e9_pair_by_weekday.csv", pd.DataFrame(wd_rows))
    # shares
    s = data.series
    full = s[(s["series_key"] == FULL) & (s["symbol"] == "SPY")]
    ex = s[(s["series_key"] == EX0DTE) & (s["symbol"] == "SPY")]
    zd = R.zero_dte_days(s)
    zd = zd[zd["symbol"] == "SPY"][["trading_date", "net_full", "net_ex0dte", "gex_0dte"]]
    days = zd.merge(full[["trading_date", "call_gex", "put_gex"]].rename(columns={"call_gex": "call_full", "put_gex": "put_full"}),
                    on="trading_date").merge(ex[["trading_date", "call_gex", "put_gex"]].rename(
                        columns={"call_gex": "call_ex", "put_gex": "put_ex"}), on="trading_date")
    out.csv("e9_same_day_share.csv", same_day_shares(days).astype({"year": str}))
    # era interaction over the threshold grid and block lengths
    ia_rows = []
    for thr in params["grid_bn"]:
        p = paired_labels(wfull, wex, thr)
        for L in params["block_lengths"]:
            r = era_interaction(p, (2014, 2022), (2023, 2026), L, params["n_boot"], make_rng(params["seed"], "E9", thr, L))
            ia_rows.append({"threshold_bn": float(thr), "block_len": int(L), "era_a": "2014-2022", "era_b": "2023-2026", **r,
                            "ci_excludes_zero": bool(r["ci_lo_pp"] > 0 or r["ci_hi_pp"] < 0)})
    out.csv("e9_era_interaction.csv", pd.DataFrame(ia_rows))
    out.yaml("e9_gate.yaml", round_native(gate))
    return gate


def run_e13(data, out: Output, params: Dict[str, Any], notes: List[str]) -> Dict[str, Any]:
    R = report()
    full_days = series_frame(data.series, FULL)
    call_days = series_frame(data.series, CALL_ONLY)
    pub_days = series_frame(data.series, PUBLISHED)
    pub_win = stored_window_frame(data, PUBLISHED)
    full_win = stored_window_frame(data, FULL)
    call_win = stored_window_frame(data, CALL_ONLY)

    def labelled(frame: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"window_end": frame["window_end"], "label": frame["clf_should_detect"].astype(bool)})

    pub, comp, call = labelled(pub_win), labelled(full_win), labelled(call_win)
    # hybrid: complete before the break, call leg of the call-only series from it on; rule on the published calendar
    pub_dates = pub_days["trading_date"]
    hyb = hybrid_values(pub_dates, full_days, call_days, params["break_date"])
    hyb_win = window_frame(pub_days, hyb.to_numpy())
    hyb_rounded = window_frame(pub_days, np.round(hyb.to_numpy() / 1e7) * 1e7)  # the prompt carried 0.01B precision
    hybrid = pd.DataFrame({"window_end": hyb_win["window_end"], "label": rule_verdict(hyb_win)})
    hybrid_r = pd.DataFrame({"window_end": hyb_rounded["window_end"], "label": rule_verdict(hyb_rounded)})
    # call-only call leg + the put leg of the complete series, on the call-only calendar
    putc = call_days[["trading_date", "call_gex"]].merge(full_days[["trading_date", "put_gex"]], on="trading_date", how="left")
    cp_win = window_frame(call_days, (putc["call_gex"] + putc["put_gex"]).to_numpy())
    callput = pd.DataFrame({"window_end": cp_win["window_end"], "label": rule_verdict(cp_win)})
    parts = [lineage_counts(pub, call, "published", "call_only"), lineage_counts(pub, comp, "published", "complete"),
             lineage_counts(pub, hybrid, "published", "hybrid"), lineage_counts(pub, hybrid_r, "published", "hybrid_rounded_0.01bn"),
             lineage_counts(callput, comp, "call_only_call_plus_complete_put", "complete"),
             lineage_counts(call, comp, "call_only", "complete")]
    table = pd.concat(parts, ignore_index=True)
    out.csv("e13_lineage_by_year.csv", table.astype({"year": str}))
    # split the published windows at the break: windows that start on/after the break, windows that end before it
    split_rows = []
    for name, other in (("call_only", call), ("complete", comp), ("hybrid", hybrid)):
        m = pub_win[["window_end", "window_start"]].assign(a=pub["label"].to_numpy()).merge(
            other.rename(columns={"label": "b"}), on="window_end")
        for part, mask in (("windows ending before the break", m["window_end"] < params["break_date"]),
                           ("windows spanning the break", (m["window_start"] < params["break_date"]) & (m["window_end"] >= params["break_date"])),
                           ("windows starting on or after the break", m["window_start"] >= params["break_date"])):
            g = m[mask]
            split_rows.append({"published_vs": name, "part": part, "n_windows": len(g), "equal": int((g["a"] == g["b"]).sum()),
                               "different": int((g["a"] != g["b"]).sum())})
    out.csv("e13_lineage_by_break.csv", pd.DataFrame(split_rows))
    # day level: how many published values equal each candidate
    tol = R.EXACT_MATCH_TOL_USD
    d = pub_days[["trading_date", "net_gex"]].rename(columns={"net_gex": "published"}).copy()
    for name, src, col in (("complete_net", full_days, "net_gex"), ("call_only_call", call_days, "call_gex"), ("hybrid", None, None)):
        if src is not None:
            d[name] = d["trading_date"].map(src.set_index("trading_date")[col])
        else:
            d[name] = hyb.to_numpy()
    day_rows = []
    pre = pd.to_datetime(d["trading_date"]) < params["break_date"]
    for name in ("complete_net", "call_only_call", "hybrid"):
        for part, mask in (("before the break", pre), ("from the break", ~pre)):
            g = d[mask]
            ok = (g["published"] - g[name]).abs() <= tol
            day_rows.append({"candidate": name, "part": part, "n_days": len(g), "n_equal_within_tol": int(ok.sum()),
                             "n_missing": int(g[name].isna().sum())})
    out.csv("e13_day_match.csv", pd.DataFrame(day_rows))
    return {"break_date": str(params["break_date"].date()), "tolerance_usd": tol}


RUNNERS = {"E1": run_e1, "E2": run_e2, "E3": run_e3, "E4": run_e4, "E6": run_e6, "E9": run_e9, "E13": run_e13}


def default_params() -> Dict[str, Any]:
    return {"seed": SEED, "n_boot": N_BOOT, "block_lengths": BLOCK_LENGTHS, "primary_block": PRIMARY_BLOCK, "margin_pp": MARGIN_PP,
            "put_weights": PUT_WEIGHTS, "grid_bn": GRID_BN, "shift_grid_bn": SHIFT_GRID_BN, "break_date": BREAK_DATE,
            "contested_definitions": CONTESTED_DEFINITIONS}


def run(data, out_dir: Path, only: Optional[Sequence[str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run the analyses (all, or the keys of ``only``) and write one file per table into ``out_dir``; returns the meta dict."""
    p = default_params() if params is None else params
    out = Output(out_dir)
    notes: List[str] = []
    chosen = [a for a in ANALYSES if only is None or a in only]
    meta: Dict[str, Any] = {"parameters": {k: (str(v.date()) if isinstance(v, pd.Timestamp) else v) for k, v in p.items()}}
    meta["gate_rule_vs_stored_windows"] = gate_rule(data, notes)
    timings = {}
    for name in chosen:
        t0 = time.time()
        meta[name] = RUNNERS[name](data, out, p, notes)
        timings[name] = round(time.time() - t0, 1)
        logger.info("%s done in %.1f s", name, timings[name])
    meta["notes"] = notes
    meta["files"] = out.files
    out.yaml("stored_analyses_meta.yaml", round_native(meta))
    meta["timings_s"] = timings  # not written: wall-clock times would make the files differ between runs
    return meta


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Stored-data analyses E1-E13 for Paper A (no model calls).")
    ap.add_argument("--parquet-root", type=Path, default=common.PARQUET_ROOT, help="folder with series/ windows/ detections/ runs/")
    ap.add_argument("--out", type=Path, required=True, help="output folder")
    ap.add_argument("--only", default=None, help="comma-separated analyses, for example E2,E3 (default: all of %s)" % ",".join(ANALYSES))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--margin-pp", type=float, default=MARGIN_PP, help="margin of the E4 non-inferiority test, points")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")
    only = None if args.only is None else [s.strip().upper() for s in args.only.split(",") if s.strip()]
    bad = [s for s in (only or []) if s not in ANALYSES]
    if bad:
        raise SystemExit(f"unknown analysis {bad}; choose from {ANALYSES}")
    params = {**default_params(), "seed": args.seed, "n_boot": args.n_boot, "margin_pp": args.margin_pp}
    t0 = time.time()
    data = load_inputs(args.parquet_root)
    meta = run(data, args.out, only, params)
    logger.info("total %.1f s; timings %s", time.time() - t0, meta["timings_s"])
    for line in meta["notes"]:
        logger.warning("%s", line)
    return 1 if meta["notes"] else 0


if __name__ == "__main__":
    sys.exit(main())
