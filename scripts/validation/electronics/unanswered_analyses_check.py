#!/usr/bin/env python3
"""Known-answer checks for unanswered_analyses.py (run: python unanswered_analyses_check.py; no pytest needed).

The file is not called test_*.py because .gitignore ignores that pattern.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unanswered_analyses as ua  # noqa: E402

FAILED = []


def check(name: str, cond: bool) -> None:
    if not cond:
        FAILED.append(name)
    print(("ok   " if cond else "FAIL ") + name)


def near(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


# ---- extractor
complete = '{"regime_detected": true, "regime_type": "persistent_positive", "reasoning": "all good"}'
r = ua.scan_answer(complete)
check("complete json: state complete, verdict True", r["state"] == "complete" and r["verdict"] is True)

r = ua.scan_answer('{\n\n    "regime_detected": false,\n    "regime_type": "transitional",\n    "positive_days": 14,\n'
                   '    "reasoning": "Step 1: 14 positive days. Step 2: the flips are 4 and')
check("cut inside the reasoning string: verdict False, cut after verdict",
      r["state"] == "cut_after_verdict" and r["verdict"] is False and r["last_key"] == "reasoning")

r = ua.scan_answer('{\n\n    "regime_detected": tr')
check("cut inside the word true: no verdict, cut before verdict", r["state"] == "cut_before_verdict" and r["verdict"] is None)

r = ua.scan_answer('{\n    "regime_detected": true')
check("literal at the end of the text without a delimiter is not complete", r["verdict"] is None)

r = ua.scan_answer('{\n    "regime_det')
check("cut inside the key", r["state"] == "cut_before_verdict" and r["verdict"] is None)

r = ua.scan_answer('{\n    "regime_type": "transitional",\n    "positive_days": 17,\n    "negative_')
check("cut before the verdict key appears", r["state"] == "cut_before_verdict" and r["verdict"] is None)

r = ua.scan_answer('{"regime_detected": true, "regime_type": "persistent_positive", "positive_days": 23, "reasoning": "x')
check("verdict present, JSON unterminated", r["state"] == "cut_after_verdict" and r["verdict"] is True)

r = ua.scan_answer('{"regime_type": "transitional", "reasoning": "the word true and regime_detected: true appear here, '
                   'also \\"regime_detected\\": true')
check("the word true and the key inside a reasoning string never match", r["verdict"] is None)

r = ua.scan_answer('{"regime_type": "x", "reasoning": "says \\"regime_detected\\": true", "regime_detected": false}')
check("an escaped key inside a string is skipped, the real key is read", r["verdict"] is False and r["state"] == "complete")

r = ua.scan_answer('{"detail": {"regime_detected": true}, "regime_detected": false, "regime_detected": true}')
check("nested keys are ignored, a repeated key keeps the first value", r["verdict"] is False)

r = ua.scan_answer('{"regime_detected": "true", "x": 1}')
check("a string value is not a boolean verdict", r["verdict"] is None and r["state"] == "complete_no_verdict")

check("empty content", ua.scan_answer(None)["state"] == "empty" and ua.scan_answer("  \n")["state"] == "empty")
check("text that is not an object", ua.scan_answer("Okay, so the user wants")["state"] == "not_object")
check("malformed object", ua.scan_answer("{regime_detected: true}")["state"] == "malformed")

# ---- agreement variants: 10 windows; rule yes on 1-4; answered 1..8 (8 and 9, 10 unanswered)
clf = [True, True, True, True, False, False, False, False, False, True]
answered = [True] * 8 + [False, False]
verdict = [True, True, True, False, False, False, True, False, None, None]  # window 4 misses, window 7 false alarm
rec = [None] * 8 + [True, None]  # window 9 recoverable true (rule no: an error), window 10 not recoverable
a = ua.agreement_variants(clf, answered, verdict, rec)
check("answered only: 6 of 8 agree", a["n_answered"] == 8 and a["agree_answered"] == 6 and near(a["agree_pct_answered"], 75.0))
# cells (rule yes/llm yes, rule yes/llm no, rule no/llm yes, both no) = 3, 1, 1, 3
check("answered only: kappa from the 3,1,1,3 table", near(a["kappa_answered"], 0.5))
# unanswered as no: window 9 (rule no) agrees, window 10 (rule yes) disagrees -> 7 of 10
check("unanswered as no: 7 of 10, kappa from 3,2,1,4",
      a["n_unans_no"] == 10 and a["agree_unans_no"] == 7 and near(a["kappa_unans_no"], float(ua.REPORT.binary_kappa(3, 2, 1, 4))))
check("unanswered as error: 6 of 10, kappa undefined", a["agree_unans_error"] == 6 and math.isnan(a["kappa_unans_error"]))
# with recoverable: windows 1..9 -> window 9 verdict True vs rule False: 6 agree of 9
check("with recoverable: 6 of 9", a["n_rec"] == 9 and a["agree_rec"] == 6 and a["n_recoverable"] == 1)
check("recoverable, rest as error: 6 of 10", a["n_rec_error"] == 10 and a["agree_rec_error"] == 6)
b = ua.agreement_variants(clf, answered, verdict)
check("no recoverable verdicts: the rec variant equals answered", b["agree_rec"] == b["agree_answered"] and b["n_rec"] == 8)
c = ua.agreement_variants([True, False], [True, True], [True, False])
check("all answered: the four variants coincide", c["agree_pct_answered"] == c["agree_pct_unans_no"] == c["agree_pct_unans_error"] == 100.0)

# ---- contested windows (the definition is stored_analyses.contested_mask, 'pivotal' by default)
cw = pd.DataFrame({
    "clf_positive_days": [22, 22, 25, 25, 20, 20, 22, 28],
    "clf_negative_days": [8, 8, 5, 5, 10, 10, 8, 2],
    "clf_avg_magnitude": [20e9, 20e9, 5.4e9, 20e9, 20e9, 3e9, 20e9, 5.6e9],
    "clf_sign_flips": [2, 5, 2, 7, 2, 2, 6, 2]})
w = ua.contested_windows(cw)
check("22 days (one above 21), others met: contested by persistence", bool(w.loc[0, "contested"]) and bool(w.loc[0, "by_persistence"]))
check("flips 5 at the limit with others met: contested by flips", bool(w.loc[1, "contested"]) and bool(w.loc[1, "by_flips"]))
check("magnitude 5.4 (within 0.5), others met: contested by magnitude", bool(w.loc[2, "contested"]) and bool(w.loc[2, "by_magnitude"]))
check("flips 7 and 25 days: not contested", not bool(w.loc[3, "contested"]))
check("20 days (one below 21) misses persistence: contested, the other two met", bool(w.loc[4, "contested"]))
check("magnitude 3 is a far miss: not contested", not bool(w.loc[5, "contested"]))
check("flips 6 (one above the limit), others met: contested", bool(w.loc[6, "contested"]))
check("magnitude 5.6 is outside the pivotal half billion: not contested; margin1 contests it",
      not bool(w.loc[7, "contested"]) and bool(ua.contested_windows(cw, "margin1").loc[7, "contested"]))
check("pivotal margin on flips: 4 flips is not contested, margin1 contests it",
      not bool(ua.contested_windows(cw.assign(clf_sign_flips=4)).loc[0, "by_flips"])
      and bool(ua.contested_windows(cw.assign(clf_sign_flips=4), "margin1").loc[0, "by_flips"]))
check("narrow definition drops the 22-day window", not bool(ua.contested_windows(cw, "narrow").loc[0, "contested"]))
check("the module uses the very function of stored_analyses", ua.sa.contested_mask is ua.sa.contested_mask
      and ua.CONTESTED_SETS["pivotal"] == ua.sa.CONTESTED_DEFINITIONS["pivotal"] and ua.CONTESTED_DEFAULT == "pivotal")

# ---- logistic fit and AUC
rng = np.random.default_rng(1)
x = rng.normal(size=4000)
yy = (rng.random(4000) < 1 / (1 + np.exp(-(0.5 + 1.2 * x)))).astype(float)
beta, se = ua.logistic_fit(np.column_stack([np.ones(4000), x]), yy)
check("logistic fit recovers the coefficients", abs(beta[0] - 0.5) < 0.15 and abs(beta[1] - 1.2) < 0.15 and (se > 0).all())
check("auc of a perfect and a reversed score", ua.auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == 1.0
      and ua.auc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([0, 0, 1, 1])) == 0.0)

# ---- repeat stability on a toy frame
def row(arm, base, rep, parsed, verdict):
    return {"arm": arm, "base_arm": base, "repeat_index": rep, "series_key": "s", "symbol": "SPY",
            "window_end": pd.Timestamp("2024-01-0%d" % (1 + len(rows))), "model": "m", "prompt_version": "v",
            "parsed": parsed, "regime_detected": verdict}


rows = []
pairs = [(True, True, True, True), (True, True, True, False), (True, False, True, None), (False, True, None, True),
         (False, False, None, None)]
orig_rows, rep_rows = [], []
for i, (po, pr, vo, vr) in enumerate(pairs):
    d = pd.Timestamp("2024-01-%02d" % (i + 1))
    orig_rows.append({"arm": "a", "base_arm": "a", "repeat_index": 0, "series_key": "s", "symbol": "SPY", "window_end": d,
                      "model": "m", "prompt_version": "v", "parsed": po, "regime_detected": vo})
    rep_rows.append({"arm": "a#rep1", "base_arm": "a", "repeat_index": 1, "series_key": "s", "symbol": "SPY", "window_end": d,
                     "model": "m", "prompt_version": "v", "parsed": pr, "regime_detected": vr})
rs = ua.repeat_stability(pd.DataFrame(orig_rows + rep_rows)).iloc[0]
check("repeat stability counts", (rs["n_repeated"], rs["n_both"], rs["n_original_only"], rs["n_repeat_only"], rs["n_neither"],
                                  rs["n_one_pass_only"], rs["n_same_verdict"]) == (5, 2, 1, 1, 1, 2, 1))

# ---- union of intervals
t = pd.Timestamp("2026-01-01", tz="UTC")
h = pd.Timedelta(hours=1)
check("union of overlapping intervals", near(ua._union_seconds([t, t + h, t + 5 * h], [t + 2 * h, t + 3 * h, t + 6 * h]), 4 * 3600.0))
check("max concurrent", ua._max_concurrent([t, t + h, t + 5 * h], [t + 2 * h, t + 3 * h, t + 6 * h]) == 2)

print()
print("FAILED: %s" % FAILED if FAILED else "all checks passed")
sys.exit(1 if FAILED else 0)
