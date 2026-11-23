#!/usr/bin/env python3
"""Recompute the numbers of the open-weights manuscript from the tracked files and compare them with the text.

Reads only tracked files: docs/papers/electronics/results/ (read only) and data/backups/gex_llm/condensed/.  Each check names the
file it reads; a mismatch is printed and the exit status is 1.  The two pending runs (D-33, D-34) have no numbers yet and are not checked.
Exploratory-run numbers (Section 4.6) need the git-ignored local folder data/backups/gex_llm/exploratory_llama_reorder_20261108/ and are
checked only when it exists (set EXPLORATORY_DIR to point elsewhere).

    ~/miniconda3/envs/AutoGex/bin/python docs/papers/openweights/check_numbers.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "docs/papers/electronics/results"
CON = ROOT / "data/backups/gex_llm/condensed"
BASES = ["bridge_jan", "full_spy", "ex0dte_spy", "p34_obf_2024", "p34_dated_2024", "p34_obf_2020", "p34_dated_2020"]
PREFIX = {"gpt-oss-20b": "oss_", "llama-3.1-8b-instruct": "llama_", "qwen3-8b": "qwen_", "gpt-6-luna": ""}
failures = []
checked = 0


def check(name, got, want, tol=0.0):
    global checked
    checked += 1
    ok = abs(float(got) - float(want)) <= tol if isinstance(want, (int, float)) else got == want
    if not ok:
        failures.append(f"{name}: computed {got!r}, text says {want!r}")


det = pd.read_csv(RES / "detection_by_year.csv")
llm = det[(det.label_source == "llm") & (det.scope == "all") & (det.arm_role == "primary")].set_index("arm")
clf = det[(det.label_source == "classifier") & (det.scope == "all")]
runs = pd.read_csv(CON / "runs.csv.gz")
meta = runs.run_metadata.map(json.loads)
runs["sec"] = meta.map(lambda m: (m.get("local") or {}).get("seconds"))
runs["retry"] = meta.map(lambda m: m.get("retry_of"))
local = runs[runs["mode"] == "local"]

# ---- Table 1 and the abstract: requests, GPU hours, retries, revisions (condensed/runs.csv.gz)
for model, req, hours, retries, chunks in (("gpt-oss-20b", 12398, 10.0, 14, 20), ("llama-3.1-8b-instruct", 12378, 3.3, 0, 15), ("qwen3-8b", 22400, 98.5, 10022, 98)):
    g = local[local.model == model]
    check(f"{model} requests", g.n_requests.sum(), req)
    check(f"{model} GPU hours", round(g.sec.sum() / 3600, 1), hours)
    check(f"{model} retry requests", g[g.retry.notna()].n_requests.sum(), retries)
    check(f"{model} runs", len(g), chunks)
check("total requests", local.n_requests.sum(), 47176)
check("total GPU hours", round(local.sec.sum() / 3600, 1), 111.8)
revs = {m: {json.loads(s)["local"]["model_revision"] for s in runs[runs.model == m].run_metadata} for m in PREFIX if m != "gpt-6-luna"}
check("oss revision", revs["gpt-oss-20b"], {"6cee5e81ee83917806bbde320786a8fb61efebee"})
check("llama revision", revs["llama-3.1-8b-instruct"], {"0e9e39f249a16976918f6564b8830bc894c89659"})
check("qwen revision", revs["qwen3-8b"], {"b968826d9c46dd6066d109eabc6255188de91218"})

# ---- Table 2: windows, agreement, kappa, answered share (detection_by_year.csv)
table2 = {  # arm: (windows, oss agree, oss kappa, llama agree, qwen agree, qwen kappa, qwen answered)
    "bridge_jan": (1476, 99.6, 0.992, 45.2, 98.9, 0.978, 91.1), "full_spy": (4691, 99.7, 0.988, 13.0, 98.7, 0.948, 89.7),
    "ex0dte_spy": (4691, 99.9, 0.992, 10.5, 99.4, 0.973, 92.0), "p34_obf_2024": (223, 98.2, 0.939, 81.2, 98.1, 0.924, 95.1),
    "p34_dated_2024": (223, 99.1, 0.970, 81.2, 95.4, 0.668, 88.3), "p34_obf_2020": (223, 100.0, 1.0, 12.1, 100.0, 1.0, 100.0),
    "p34_dated_2020": (223, 100.0, 1.0, 12.1, 99.5, 0.979, 97.8)}
for arm, (n, oa, ok_, la, qa, qk, qans) in table2.items():
    o, l, q = llm.loc["oss_" + arm], llm.loc["llama_" + arm], llm.loc["qwen_" + arm]
    check(f"{arm} windows", q.n_windows, n)
    check(f"{arm} oss agree", round(o.agree_pct, 1), oa); check(f"{arm} oss kappa", round(o.kappa, 3), ok_)
    check(f"{arm} llama agree", round(l.agree_pct, 1), la); check(f"{arm} llama kappa ~0", abs(l.kappa), 0.0, 1e-3)
    check(f"{arm} qwen agree", round(q.agree_pct, 1), qa); check(f"{arm} qwen kappa", round(q.kappa, 3), qk)
    check(f"{arm} qwen answered", round(100 * q.n_parsed / q.n_windows, 1), qans)
    # reference columns (Paper A): rule rate and gpt-6-luna rate
    rule_key = {"bridge_jan": "jan2026_phase4a", "full_spy": "new_full", "ex0dte_spy": "new_ex0dte", "p34_obf_2024": "p3_2024", "p34_dated_2024": "p3_2024_dated",
                "p34_obf_2020": "p4_2020", "p34_dated_2020": "p4_2020_dated"}[arm]
    rr = clf[(clf.series_key == rule_key) & (clf.symbol == "SPY")].rate_pct
    check(f"{arm} rule rate", round(rr.iloc[0], 1), {"bridge_jan": 45.2, "full_spy": 13.0, "ex0dte_spy": 10.5}.get(arm, 81.2 if "2024" in arm else 12.1))
check("llama full_spy detected", llm.loc["llama_full_spy"].n_detect, 4690)
check("oss unparsed", 11750 - sum(llm.loc["oss_" + a].n_parsed for a in BASES), 2)

# ---- bridge to o4-mini (bridge_agreement.csv)
ba = pd.read_csv(RES / "bridge_agreement.csv")
b = ba[(ba.comparison == "bridge") & (ba.scope == "all") & (ba.ref_arm == "r1_o4mini")].set_index("other_arm")
check("oss vs o4-mini pairs", b.loc["oss_bridge_jan"].n_pairs, 1412)
check("oss vs o4-mini agree", round(b.loc["oss_bridge_jan"].agree_pct, 1), 99.6)
check("oss vs o4-mini kappa", round(b.loc["oss_bridge_jan"].kappa, 3), 0.991)
check("oss vs o4-mini same verdict", b.loc["oss_bridge_jan"].n_ref_det_oth_det + b.loc["oss_bridge_jan"].n_ref_not_oth_not, 1406)
check("luna vs o4-mini same verdict", b.loc["bridge_jan"].n_ref_det_oth_det + b.loc["bridge_jan"].n_ref_not_oth_not, 1407)
check("luna vs o4-mini kappa", round(b.loc["bridge_jan"].kappa, 3), 0.993)
check("qwen vs o4-mini pairs", b.loc["qwen_bridge_jan"].n_pairs, 1287)
check("qwen vs o4-mini same verdict", b.loc["qwen_bridge_jan"].n_ref_det_oth_det + b.loc["qwen_bridge_jan"].n_ref_not_oth_not, 1273)
check("qwen vs o4-mini kappa", round(b.loc["qwen_bridge_jan"].kappa, 3), 0.978)
mp = ba[(ba.comparison == "model_pair") & (ba.scope == "all")].set_index("other_arm")
check("oss vs luna full_spy agree", round(mp.loc["oss_full_spy"].agree_pct, 1), 99.4)
check("oss vs luna full_spy kappa", round(mp.loc["oss_full_spy"].kappa, 3), 0.973)
check("oss vs luna rule sides with oss", mp.loc["oss_full_spy"].n_disagree_other_matches_clf, 16)
check("oss vs luna rule sides with luna", mp.loc["oss_full_spy"].n_disagree_ref_matches_clf, 13)
check("qwen vs luna full_spy agree", round(mp.loc["qwen_full_spy"].agree_pct, 1), 98.5)
check("qwen vs luna full_spy kappa", round(mp.loc["qwen_full_spy"].kappa, 3), 0.941)
tr = ba[(ba.comparison == "test_retest") & (ba.scope == "all")]
tr = tr.assign(base=tr.ref_arm)
for pre, equal, pairs in (("oss_", 593, 594), ("llama_", 588, 588), ("qwen_", 480, 483)):
    g = tr[tr.base.str.startswith(pre)]
    check(f"{pre} retest pairs", g.n_pairs.sum(), pairs)
    check(f"{pre} retest equal", round((g.n_pairs * g.agree_pct / 100).sum()), equal)
check("luna bridge retest agree", round(tr[tr.ref_arm == "bridge_jan"].agree_pct.iloc[0], 1), 99.3)

# ---- parse stats: tokens, unanswered, retries (llm_parse_stats.csv)
ps = pd.read_csv(RES / "llm_parse_stats.csv")
for model, tok, parsed in (("gpt-oss-20b", 1865, 11748), ("llama-3.1-8b-instruct", 170, 11750), ("qwen3-8b", 5368, 10718), ("gpt-6-luna", 758, 11750)):
    g = ps[(ps.model == model) & (ps.arm_role == "primary") & ps.arm.isin([PREFIX[model] + a for a in BASES])]
    check(f"{model} rows", g.n_rows.sum(), 11750); check(f"{model} parsed", g.n_parsed.sum(), parsed)
    check(f"{model} mean completion tokens", round((g.mean_completion_tokens * g.n_rows).sum() / g.n_rows.sum()), tok)
check("qwen finish length", ps[(ps.model == "qwen3-8b") & (ps.arm_role == "primary")].n_finish_length.sum(), 1032)

# ---- Qwen bounds (missing_answer_bounds.csv)
mb = pd.read_csv(RES / "missing_answer_bounds.csv")
q = mb[mb.arm.str.startswith("qwen_") & (mb.period == "all")]
check("qwen unparsed", q.n_unparsed.sum(), 1032); check("qwen unparsed rule rejects", q.n_unparsed_clf_no_detect.sum(), 1011)
f = mb[(mb.arm == "qwen_full_spy") & (mb.period == "all")].iloc[0]
check("qwen full detects answered", round(f.parsed_pct_clf_detect, 1), 98.9); check("qwen full rejects answered", round(f.parsed_pct_clf_no_detect, 1), 88.3)
f = mb[(mb.arm == "qwen_full_spy") & (mb.period == "2024-2025")].iloc[0]
check("qwen 2024-25 lower", round(f.lower_pct, 1), 14.5); check("qwen 2024-25 upper", round(f.upper_pct, 1), 35.1)
check("qwen 2024-25 unanswered", f.n_unparsed, 103); check("qwen 2024-25 answered", f.n_parsed, 399); check("qwen 2024-25 detected", f.n_detected_parsed, 73)
check("rule 2024-25 rate", round(f.clf_rate_pct, 1), 12.0)
f = mb[(mb.arm == "qwen_ex0dte_spy") & (mb.period == "2024-2025")].iloc[0]
check("qwen ex0dte lower", round(f.lower_pct, 1), 15.9); check("qwen ex0dte upper", round(f.upper_pct, 1), 23.3); check("rule ex0dte", round(f.clf_rate_pct, 1), 14.7)
d24 = mb[(mb.period == "all")].set_index("arm")
check("qwen dated 2024 answers rule-rejected", 42 - d24.loc["qwen_p34_dated_2024"].n_unparsed_clf_no_detect, 19)
check("qwen obf 2024 answers rule-rejected", 42 - d24.loc["qwen_p34_obf_2024"].n_unparsed_clf_no_detect, 33)
check("qwen 2024 vs 2020 relative", round(d24.loc["qwen_p34_obf_2024"].lower_pct - llm.loc["qwen_p34_obf_2020"].rate_pct, 1), 70.0)
check("qwen 2024 vs 2020 dated", round(d24.loc["qwen_p34_dated_2024"].lower_pct - d24.loc["qwen_p34_dated_2020"].upper_pct, 1), 69.5)

# ---- stats.yaml
st = yaml.safe_load(open(RES / "stats.yaml"))
def rate(arm, period):
    for e in st["rates"]:
        l = e["labeller"]
        if l.get("arm") == arm and e["period"] == period:
            return e
rr = rate("oss_full_spy", "2024-2025"); check("oss 2024-25 k", rr["k"], 62); check("oss 2024-25 n", rr["n"], 502)
check("oss boot lo", round(rr["bootstrap_quarter"]["ci_pct"][0], 1), 5.7); check("oss boot hi", round(rr["bootstrap_quarter"]["ci_pct"][1], 1), 19.8)
check("luna 2024-25 k", rate("full_spy", "2024-2025")["k"], 63)
check("oss published 2024-25", rate("oss_bridge_jan", "2024-2025")["k"], 501)
check("o4-mini published 2024-25 detected", rate("r1_o4mini", "2024-2025")["k"], 486); check("o4-mini published 2024-25 answered", rate("r1_o4mini", "2024-2025")["n"], 486)
check("qwen published 2024-25 detected", rate("qwen_bridge_jan", "2024-2025")["k"], 501); check("qwen published 2024-25 answered", rate("qwen_bridge_jan", "2024-2025")["n"], 501)
check("llama published 2024-25", rate("llama_bridge_jan", "2024-2025")["k"], 501)
for c in st["contrasts"]:
    if c.get("name") == "series_contrast" and c.get("family") == "label" and c["a"].get("arm") == "oss_p34_obf_2024" and c["b"].get("arm") == "oss_p34_dated_2024":
        check("oss date McNemar", round(c["naive_stride1"]["p_mcnemar_exact"], 3), 0.688)
        check("oss date bootstrap p", round(c["bootstrap_quarter"]["p_two_sided"], 3), 0.633)
    if c.get("name") == "series_contrast" and c.get("family") == "label" and c["a"].get("arm") == "qwen_p34_obf_2024" and c["b"].get("arm") == "qwen_p34_dated_2024":
        check("qwen common windows", c["n_common_windows"], 190); check("qwen date bootstrap p", round(c["bootstrap_quarter"]["p_two_sided"], 3), 0.125)

# ---- disagreements.csv: departures by direction and failing criterion (Figure 4, Section 4.5)
dis = pd.read_csv(RES / "disagreements.csv")
lim = yaml.safe_load(open(RES / "report.yaml"))["diagnostics"]["thresholds"]
want = {"qwen3-8b": (108, 99, 83, 14, 1, 1, 9), "gpt-oss-20b": (32, 29, 26, 2, 1, 0, 3), "gpt-6-luna": (37, 26, 24, 2, 0, 0, 11)}
for model, (tot, det_, flips, mag, per, two, rej) in want.items():
    x = dis[(dis.model == model) & dis.arm.isin([PREFIX[model] + a for a in BASES])]
    d = x[x.llm_detected.astype(str) == "True"]
    fail = pd.DataFrame({"p": d.clf_persistence_pct < 100 * lim["persistence"] - 1e-9, "m": d.clf_avg_magnitude_bn < lim["mean_abs_gex_usd"] / 1e9, "f": d.clf_sign_flips > lim["max_sign_flips"]})
    n = fail.sum(axis=1)
    got = (len(x), len(d), int(((n == 1) & fail.f).sum()), int(((n == 1) & fail.m).sum()), int(((n == 1) & fail.p).sum()), int((n >= 2).sum()), len(x) - len(d))
    check(f"{model} departures", got, (tot, det_, flips, mag, per, two, rej))
qd = dis[(dis.model == "qwen3-8b") & (dis.llm_detected.astype(str) == "True")]
qf = qd[(qd.clf_sign_flips > 5) & (qd.clf_avg_magnitude_bn >= 5) & (qd.clf_persistence_pct >= 70 - 1e-9)]
check("qwen flips-only with six flips", (qf.clf_sign_flips == 6).sum(), 52)
check("qwen flips-only reported 3 to 5", int(qf.llm_sign_flips.between(3, 5).all()), 1)
qm = qd[(qd.clf_avg_magnitude_bn < 5) & (qd.clf_sign_flips <= 5)]
check("qwen magnitude-only just below 5 (4.968 to 5)", int(((qm.clf_avg_magnitude_bn >= 4.9679)).sum()), 9)
qr = dis[(dis.model == "qwen3-8b") & (dis.llm_detected.astype(str) == "False")]
check("qwen rejects/rule detects, reported magnitude below 5 where computed above", int(((qr.llm_avg_magnitude_bn < 5) & (qr.clf_avg_magnitude_bn >= 5)).sum()), 7)

# ---- Llama reported metrics (reported_vs_computed.csv)
rv = pd.read_csv(RES / "reported_vs_computed.csv")
a = rv[(rv.basis == "arm") & (rv.scope == "all")].set_index("arm").ratio_within_5pct_pct
lw = [a["llama_" + x] for x in BASES]
check("llama within 5% min", round(min(lw), 1), 14.3); check("llama within 5% max", round(max(lw), 1), 64.1)
check("luna within 5% min (Paper A)", round(min(a[x] for x in BASES), 1), 98.4)
qw = [a["qwen_" + x] for x in BASES]
check("qwen within 5% min", round(min(qw), 1), 96.9); check("qwen within 5% max", round(max(qw), 1), 99.5)
check("llama bridge within 5%", round(a["llama_bridge_jan"], 1), 41.6); check("llama full within 5%", round(a["llama_full_spy"], 1), 19.1)
check("llama ex0dte within 5%", round(a["llama_ex0dte_spy"], 1), 16.1); check("llama obf2024 within 5%", round(a["llama_p34_obf_2024"], 1), 64.1)
check("llama dated2024 within 5%", round(a["llama_p34_dated_2024"], 1), 62.3); check("llama obf2020 within 5%", round(a["llama_p34_obf_2020"], 1), 14.3)
check("llama dated2020 within 5%", round(a["llama_p34_dated_2020"], 1), 23.8)
sf = llm.sign_flips_exact_pct
check("qwen full flips exact", round(sf["qwen_full_spy"], 1), 87.3); check("luna full flips exact", round(sf["full_spy"], 1), 93.4)
check("llama flips exact min", round(min(sf["llama_" + x] for x in BASES), 1), 2.7); check("llama flips exact max", round(max(sf["llama_" + x] for x in BASES), 1), 13.9)

# ---- Section 4.6: exploratory run and the verdict-first pilot (condensed tables; local folder for the exploratory answers)
w = pd.read_csv(CON / "windows.csv.gz")
w = w[(w.series_key == "jan2026_phase4a") & (w.symbol == "SPY")][["window_end", "clf_should_detect"]]
w["window_end"] = w.window_end.astype(str).str[:10]
dd = pd.read_csv(CON / "detections.csv.gz", low_memory=False)
pil = dd[dd.arm == "pilot_llama_bridge_jan"].copy(); pil["window_end"] = pil.window_end.astype(str).str[:10]
pm = pil.merge(w, on="window_end")
check("pilot windows", len(pm), 40); check("pilot detected", int(pm.regime_detected.sum()), 40); check("pilot agree", int((pm.regime_detected == pm.clf_should_detect).sum()), 20)
expl = Path(os.environ.get("EXPLORATORY_DIR", ROOT / "data/backups/gex_llm/exploratory_llama_reorder_20261108")) / "output.jsonl"
if expl.is_file():
    rows = []
    for line in open(expl):
        o = json.loads(line); we = o["custom_id"].split("|")[2]
        rows.append((we, json.loads(o["response"]["body"]["choices"][0]["message"]["content"])["regime_detected"]))
    x = pd.DataFrame(rows, columns=["window_end", "det"]).merge(w, on="window_end")
    check("exploratory detected", int(x.det.sum()), 32); check("exploratory agree", int((x.det == x.clf_should_detect).sum()), 26)
    check("exploratory rejected-but-detected", int((x.det & ~x.clf_should_detect).sum()), 13); check("exploratory detected-but-missed", int((~x.det & x.clf_should_detect).sum()), 1)
else:
    print(f"note: {expl} not found; the exploratory-run numbers were not checked")

print(f"{checked} checks, {len(failures)} mismatch(es)")
for f_ in failures:
    print("MISMATCH", f_)
sys.exit(1 if failures else 0)
