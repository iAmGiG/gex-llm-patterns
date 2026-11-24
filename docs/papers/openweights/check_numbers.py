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
three = local[local.model.isin(["gpt-oss-20b", "llama-3.1-8b-instruct", "qwen3-8b"])]
check("total requests (three models)", three.n_requests.sum(), 47176)
check("total GPU hours (three models)", round(three.sec.sum() / 3600, 1), 111.8)
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


# ---- the variants (decisions D-33 and D-34): llamarf_*, osst0_bridge_jan, llamat0_bridge_jan
VAR = {"llama-3.1-8b-instruct-rf": (12379, 2.3, 1, 16), "gpt-oss-20b-t0": (1614, 0.5, 24, 4), "llama-3.1-8b-instruct-t0": (1590, 0.3, 0, 3)}
for model, (req, hours, retries, chunks) in VAR.items():
    g = local[local.model == model]
    check(f"{model} requests", g.n_requests.sum(), req); check(f"{model} GPU hours", round(g.sec.sum() / 3600, 1), hours)
    check(f"{model} retry requests", g[g.retry.notna()].n_requests.sum(), retries); check(f"{model} runs", len(g), chunks)
check("rf GPU seconds", round(local[local.model == "llama-3.1-8b-instruct-rf"].sec.sum(), 1), 8459.0)
check("osst0 GPU seconds", round(local[local.model == "gpt-oss-20b-t0"].sec.sum(), 1), 1788.9)
check("llamat0 GPU seconds", round(local[local.model == "llama-3.1-8b-instruct-t0"].sec.sum(), 1), 952.6)
vloc = local[local.model.isin(VAR)]
check("variant requests", vloc.n_requests.sum(), 15583); check("variant GPU hours", round(vloc.sec.sum() / 3600, 1), 3.1)
check("all local requests", local.n_requests.sum(), 62759); check("all local GPU hours", round(local.sec.sum() / 3600, 1), 114.9)
check("all retries", local[local.retry.notna()].n_requests.sum(), 10061)


def sampling(model):
    return {(json.dumps(json.loads(s)["local"].get("request_sampling")), json.dumps(json.loads(s)["local"].get("schema_property_order"))) for s in runs[runs.model == model].run_metadata}


rf_order = ["reasoning", "positive_days", "negative_days", "avg_magnitude_billions", "sign_flips", "persistence_pct", "regime_type", "regime_detected", "confidence"]
check("rf sampling and order", sampling("llama-3.1-8b-instruct-rf"), {("{}", json.dumps(rf_order))})
check("t0 sampling oss", {x[0] for x in sampling("gpt-oss-20b-t0")}, {'{"temperature": 0.0}'})
check("t0 sampling llama", {x[0] for x in sampling("llama-3.1-8b-instruct-t0")}, {'{"temperature": 0.0}'})
check("earlier runs record no sampling", sampling("qwen3-8b"), {("null", "null")})
check("earlier llama record no sampling", sampling("llama-3.1-8b-instruct"), {("null", "null")})
RF = {"bridge_jan": (972, 67.0, 0.360, 38.7), "full_spy": (2210, 56.7, 0.096, 17.4), "ex0dte_spy": (2244, 55.7, 0.083, 17.3), "p34_obf_2024": (112, 54.7, 0.092, 37.2),
      "p34_dated_2024": (110, 52.0, 0.048, 35.9), "p34_obf_2020": (167, 35.4, 0.062, 14.8), "p34_dated_2020": (147, 41.7, 0.061, 23.3)}
for arm, (nd, ag, ka, w5) in RF.items():
    x = llm.loc["llamarf_" + arm]
    check(f"rf {arm} windows", x.n_windows, table2[arm][0]); check(f"rf {arm} parsed", x.n_parsed, x.n_windows); check(f"rf {arm} detected", x.n_detect, nd)
    check(f"rf {arm} agree", round(x.agree_pct, 1), ag); check(f"rf {arm} kappa", round(x.kappa, 3), ka); check(f"rf {arm} within 5%", round(a["llamarf_" + arm], 1), w5)
    check(f"rf {arm} metrics_agree under 0.5%", int(x.metrics_agree_pct < 0.5), 1)
x = llm.loc["llamarf_full_spy"]; check("rf full rate", round(x.rate_pct, 1), 47.1)
check("rf bridge rate", round(llm.loc["llamarf_bridge_jan"].rate_pct, 1), 65.9)
ys = det[(det.label_source == "llm") & (det.scope == "year") & (det.arm == "llamarf_full_spy") & det.year.isin([2024, 2025])]
check("rf 2024-25 detected", ys.n_detect.sum(), 279); check("rf 2024-25 windows", ys.n_parsed.sum(), 502)
check("rf baseline agree range", (round(min(llm.loc["llamarf_" + k].agree_pct for k in BASES[3:]), 1), round(max(llm.loc["llamarf_" + k].agree_pct for k in BASES[3:]), 1)), (35.4, 54.7))
check("rf baseline kappa range", (round(min(llm.loc["llamarf_" + k].kappa for k in BASES[3:]), 3), round(max(llm.loc["llamarf_" + k].kappa for k in BASES[3:]), 3)), (0.048, 0.092))
check("rf within 5% range", (round(min(a["llamarf_" + k] for k in BASES), 1), round(max(a["llamarf_" + k] for k in BASES), 1)), (14.8, 38.7))
check("rf metrics_agree max under 0.5", int(max(llm.loc["llamarf_" + k].metrics_agree_pct for k in BASES) < 0.5), 1)
check("rf vs o4-mini pairs", b.loc["llamarf_bridge_jan"].n_pairs, 1412); check("rf vs o4-mini agree", round(b.loc["llamarf_bridge_jan"].agree_pct, 1), 67.2)
check("rf vs o4-mini kappa", round(b.loc["llamarf_bridge_jan"].kappa, 3), 0.361)
ps2 = ps[ps.arm.isin(["llamarf_" + k for k in BASES]) & (ps.arm_role == "primary")]
check("rf rows equal parsed", int((ps2.n_rows == ps2.n_parsed).all()), 1); check("rf retry answers", ps2.n_rerun_at_retry_cap.sum(), 1)
check("rf mean tokens", round((ps2.mean_completion_tokens * ps2.n_rows).sum() / ps2.n_rows.sum(), 1), 160.0)


def sametab(x_, y_):
    A = dd[(dd.arm == x_) & dd.parse_status.isin(["ok", "fallback"])][["window_end", "regime_detected"]]
    B = dd[(dd.arm == y_) & dd.parse_status.isin(["ok", "fallback"])][["window_end", "regime_detected"]]
    m = A.merge(B, on="window_end")
    return len(m), int((m.regime_detected_x == m.regime_detected_y).sum())


check("rf vs verdict first bridge", sametab("llamarf_bridge_jan", "llama_bridge_jan"), (1476, 972))
check("rf vs verdict first full", sametab("llamarf_full_spy", "llama_full_spy"), (4691, 2211))
check("rf vs verdict first ex0dte", sametab("llamarf_ex0dte_spy", "llama_ex0dte_spy"), (4691, 2245))
rt = tr[tr.ref_arm.str.startswith("llamarf_")]
check("rf retest pairs", rt.n_pairs.sum(), 588); check("rf retest equal", int((rt.n_ref_det_oth_det + rt.n_ref_not_oth_not).sum()), 353)
f = rt[rt.ref_arm == "llamarf_full_spy"].iloc[0]
check("rf retest full agree", round(f.agree_pct, 1), 55.7); check("rf retest full kappa", round(f.kappa, 3), 0.113); check("rf retest full pairs", f.n_pairs, 235)
# temperature 0
o = llm.loc["osst0_bridge_jan"]; l0 = llm.loc["llamat0_bridge_jan"]
check("osst0 parsed", o.n_parsed, 1475); check("osst0 detected", o.n_detect, 669); check("osst0 agree", round(o.agree_pct, 1), 99.7); check("osst0 kappa", round(o.kappa, 3), 0.995)
check("llamat0 detected", l0.n_detect, 1476); check("llamat0 agree", round(l0.agree_pct, 1), 45.2); check("llamat0 kappa", abs(l0.kappa), 0.0, 1e-9)
check("osst0 vs o4-mini pairs", b.loc["osst0_bridge_jan"].n_pairs, 1411); check("osst0 vs o4-mini agree", round(b.loc["osst0_bridge_jan"].agree_pct, 1), 99.7)
check("osst0 vs o4-mini kappa", round(b.loc["osst0_bridge_jan"].kappa, 3), 0.994)
check("osst0 vs luna pairs", mp.loc["osst0_bridge_jan"].n_pairs, 1475); check("osst0 vs luna agree", round(mp.loc["osst0_bridge_jan"].agree_pct, 1), 99.3)
check("osst0 vs luna kappa", round(mp.loc["osst0_bridge_jan"].kappa, 3), 0.986)
check("osst0 vs default", sametab("osst0_bridge_jan", "oss_bridge_jan"), (1475, 1465)); check("llamat0 vs default", sametab("llamat0_bridge_jan", "llama_bridge_jan"), (1476, 1476))
po = ps[ps.arm == "osst0_bridge_jan"].iloc[0]
check("osst0 retry answers", po.n_rerun_at_retry_cap, 24); check("osst0 unanswered", po.n_rows - po.n_parsed, 1)
check("osst0 mean tokens", round(po.mean_completion_tokens), 1811); check("llamat0 mean tokens", round(ps[ps.arm == "llamat0_bridge_jan"].iloc[0].mean_completion_tokens), 176)
for arm_, pairs_, eq_ in (("osst0_bridge_jan", 73, 73), ("llamat0_bridge_jan", 74, 74), ("oss_bridge_jan", 74, 74), ("llama_bridge_jan", 74, 74)):
    r_ = tr[tr.ref_arm == arm_].iloc[0]
    check(f"{arm_} retest pairs", r_.n_pairs, pairs_); check(f"{arm_} retest agree", round(r_.agree_pct * r_.n_pairs / 100), eq_)
check("oss default detected (bridge)", llm.loc["oss_bridge_jan"].n_detect, 673)
for arm_, det_, eq_ in (("pilot_llamarf_bridge_jan", 27, 27), ("pilot_llamat0_bridge_jan", 40, 20)):
    pp = dd[dd.arm == arm_].copy(); pp["window_end"] = pp.window_end.astype(str).str[:10]; pm2 = pp.merge(w, on="window_end")
    check(f"{arm_} detected", int(pm2.regime_detected.sum()), det_); check(f"{arm_} equal to rule", int((pm2.regime_detected == pm2.clf_should_detect).sum()), eq_)

# ---- unanswered windows of Qwen3-8B, contested windows, GPU time (unanswered_*.csv, unanswered_analyses.yaml; issue #298)
UA = yaml.safe_load(open(RES / "unanswered_analyses.yaml"))
cen = pd.read_csv(RES / "unanswered_census_unanswered.csv")
cq = cen[(cen.model == "qwen3-8b") & (cen.arm_role == "primary")].groupby("kind").n.sum()
check("qwen census missing", int(cq["missing"]), 884); check("qwen census failed", int(cq["failed"]), 147); check("qwen census complete_at_cap", int(cq["complete_at_cap"]), 1)
check("qwen census unanswered", int(cq[["missing", "failed", "complete_at_cap"]].sum()), 1032)
rv = pd.read_csv(RES / "unanswered_recoverable_verdicts.csv")
rq = rv[(rv.population == "final_unanswered_primary") & (rv.model == "qwen3-8b")].set_index("arm")
for col, want_ in (("n_rows", 1032), ("n_with_text", 148), ("n_cut_after_verdict", 144), ("n_cut_before_verdict", 3), ("n_complete", 1), ("n_verdict", 145), ("n_verdict_agrees_rule", 143)):
    check(f"qwen unanswered {col}", int(rq[col].sum()), want_)
check("qwen unanswered no JSON text", int((rq.n_rows - rq.n_with_text).sum()), 884)
S7 = {"qwen_bridge_jan": (131, 114, 17, 0, 0, 17, 15), "qwen_full_spy": (485, 421, 62, 2, 0, 62, 62), "qwen_ex0dte_spy": (374, 315, 57, 1, 1, 58, 58),
      "qwen_p34_obf_2024": (11, 8, 3, 0, 0, 3, 3), "qwen_p34_dated_2024": (26, 21, 5, 0, 0, 5, 5), "qwen_p34_dated_2020": (5, 5, 0, 0, 0, 0, 0)}
for arm_, want_ in S7.items():
    x = rq.loc[arm_]
    check(f"Table S7 {arm_}", (int(x.n_rows), int(x.n_rows - x.n_with_text), int(x.n_cut_after_verdict), int(x.n_cut_before_verdict), int(x.n_complete), int(x.n_verdict), int(x.n_verdict_agrees_rule)), want_)
check("Table S7 arms with unanswered windows", sorted(rq.index[rq.n_rows > 0]), sorted(S7))
fr = pd.read_csv(RES / "unanswered_recoverable_first_pass_vs_retry.csv").set_index("model").loc["qwen3-8b"]
check("qwen first pass vs retry windows", int(fr.n), 316); check("qwen first pass vs retry same", int(fr.n_same), 313)
sc = UA["scanner_on_answered_rows"]
check("scanner answered rows", sc["n_answered_rows"], 89656); check("scanner same verdict", sc["n_same_verdict"], 88362); check("scanner no verdict", sc["n_scanner_no_verdict"], 1294)
av = pd.read_csv(RES / "unanswered_agreement_variants.csv").set_index(["arm", "period"])
f = av.loc[("qwen_full_spy", "all")]
check("qwen full windows", int(f.n_windows), 4691); check("qwen full unanswered", int(f.n_unanswered), 485); check("qwen full answered", int(f.n_answered), 4206)
check("qwen full agree answered (98.7)", round(f.agree_pct_answered, 1), 98.7); check("qwen full agree answered count", int(f.agree_answered), 4151)
check("qwen full agree unanswered not detected (98.7)", round(f.agree_pct_unans_no, 1), 98.7); check("qwen full agree unanswered not detected count", int(f.agree_unans_no), 4629)
check("qwen full agree unanswered errors (88.5)", round(f.agree_pct_unans_error, 1), 88.5); check("qwen full agree unanswered errors count", int(f.agree_unans_error), 4151)
check("qwen full recoverable", int(f.n_recoverable), 62)
T8 = {("qwen_full_spy", "all"): (4691, 485, 98.7, 98.7, 88.5, 98.7, 89.8), ("qwen_full_spy", "2024-2025"): (502, 103, 96.0, 96.2, 76.3, 96.1, 78.5),
      ("qwen_ex0dte_spy", "all"): (4691, 374, 99.4, 99.3, 91.5, 99.5, 92.8), ("qwen_ex0dte_spy", "2024-2025"): (502, 37, 98.7, 98.8, 91.4, 98.7, 93.0),
      ("qwen_bridge_jan", "all"): (1476, 131, 98.9, 98.9, 90.1, 98.8, 91.1)}
for key_, want_ in T8.items():
    x = av.loc[key_]
    check(f"Table S8 agreement {key_}", (int(x.n_windows), int(x.n_unanswered), round(x.agree_pct_answered, 1), round(x.agree_pct_unans_no, 1), round(x.agree_pct_unans_error, 1), round(x.agree_pct_rec, 1), round(x.agree_pct_rec_error, 1)), want_)
bw = pd.read_csv(RES / "unanswered_bounds_with_recoverable.csv").set_index(["arm", "period"])
T8B = {("qwen_full_spy", "all"): (13.8, 24.2, 13.8, 22.9, 62), ("qwen_full_spy", "2024-2025"): (14.5, 35.1, 14.5, 32.9, 11), ("qwen_ex0dte_spy", "all"): (10.7, 18.7, 10.7, 17.5, 58),
       ("qwen_ex0dte_spy", "2024-2025"): (15.9, 23.3, 15.9, 21.7, 8), ("qwen_bridge_jan", "all"): (45.9, 54.7, 45.9, 53.7, 17)}
for key_, want_ in T8B.items():
    x = bw.loc[key_]
    check(f"Table S8 bounds {key_}", (round(x.lower_pct, 1), round(x.upper_pct, 1), round(x.lower_rec_pct, 1), round(x.upper_rec_pct, 1), int(x.n_recoverable)), want_)
x = bw.loc[("qwen_full_spy", "2024-2025")]
check("qwen 2024-25 recoverable all not detected", int(x.n_recoverable_true), 0); check("qwen 2024-25 unreadable", int(x.n_unrecoverable), 92)
check("qwen 2024-25 bounds equal missing_answer_bounds", (round(x.lower_pct, 6), round(x.upper_pct, 6)), (round(mb[(mb.arm == "qwen_full_spy") & (mb.period == "2024-2025")].iloc[0].lower_pct, 6), round(mb[(mb.arm == "qwen_full_spy") & (mb.period == "2024-2025")].iloc[0].upper_pct, 6)))
ca = pd.read_csv(RES / "unanswered_contested_agreement.csv").set_index(["arm", "stratum"])
c = ca.loc[("qwen_full_spy", "contested")]
check("contested windows", int(c.n_windows), 521); check("qwen contested answered", int(c.n_answered), 454); check("qwen contested answered share", round(c.answered_pct, 1), 87.1)
check("qwen contested agree", round(c.agree_pct_answered, 1), 92.3); check("qwen contested kappa", round(c.kappa_answered, 3), 0.845)
c = ca.loc[("qwen_full_spy", "not_contested")]
check("qwen contested agree, unanswered as errors", round(ca.loc[("qwen_full_spy", "contested")].agree_pct_unans_error, 1), 80.4)
ab = pd.read_csv(RES / "unanswered_answering_bands.csv").set_index(["model", "scope", "variable", "band"])
check("qwen answered share at 11 or more flips", round(ab.loc[("qwen3-8b", "full_spy", "sign_flips", ">=11")].answered_pct, 1), 85.5)
check("qwen not contested answered", int(c.n_answered), 3752); check("qwen not contested agree", round(c.agree_pct_answered, 1), 99.5)
check("oss contested answered", int(ca.loc[("oss_full_spy", "contested")].n_answered), 521); check("oss contested agree", round(ca.loc[("oss_full_spy", "contested")].agree_pct_answered, 1), 98.3)
check("luna contested agree (Paper A)", round(ca.loc[("full_spy", "contested")].agree_pct_answered, 1), 97.5)
ec = pd.read_csv(RES / "stored_e1_contested.csv").set_index(["arm", "period", "definition"]).loc[("full_spy", "all", "pivotal")]
check("contested windows stored_e1", int(ec.n_contested), 521); check("contested share", round(ec.contested_pct, 1), 11.1)
check("pivotal definition", UA["parameters"]["contested_sets"]["pivotal"], {"days": 1, "billions": 0.5, "flips": 1, "flips_below": 0})
cs = pd.read_csv(RES / "unanswered_contested_sensitivity.csv")
cs = cs[cs.stratum == "contested"].set_index(["margin_set", "arm"])
T10 = {"narrow": (0, 0.5, 0, 0, 346, 94.2, 97.5, 100.0, 99.1), "pivotal": (1, 0.5, 0, 1, 521, 87.1, 92.3, 98.3, 97.5), "margin1": (1, 1.0, 1, 1, 764, 90.6, 94.8, 98.7, 98.2),
       "wide": (3, 2.0, 2, 2, 1204, 90.0, 95.6, 99.1, 98.8)}
for set_, want_ in T10.items():
    q_ = cs.loc[(set_, "qwen_full_spy")]
    check(f"Table S10 {set_}", (int(q_.margin_days), float(q_.margin_billions), int(q_.margin_flips_below), int(q_.margin_flips_above), int(q_.n_windows), round(q_.answered_pct, 1), round(q_.agree_pct_answered, 1),
                                round(cs.loc[(set_, "oss_full_spy")].agree_pct_answered, 1), round(cs.loc[(set_, "full_spy")].agree_pct_answered, 1)), want_)
check("qwen contested agreement range over margin sets", (round(min(cs.loc[(s_, "qwen_full_spy")].agree_pct_answered for s_ in T10), 1), round(max(cs.loc[(s_, "qwen_full_spy")].agree_pct_answered for s_ in T10), 1)), (92.3, 97.5))
bd = pd.read_csv(RES / "unanswered_answering_bands.csv")
bd = bd[(bd.model == "qwen3-8b") & (bd.scope == "full_spy")].set_index(["variable", "band"])
T9 = {("rule", "detect"): (609, 602, 98.9), ("rule", "reject"): (4082, 3604, 88.3), ("persistence_pct", "<60"): (872, 822, 94.3), ("persistence_pct", "60-<70"): (951, 880, 92.5),
      ("persistence_pct", "70-<80"): (954, 761, 79.8), ("persistence_pct", "80-<90"): (842, 693, 82.3), ("persistence_pct", "90-100"): (1072, 1050, 97.9),
      ("sign_flips", "0-1"): (332, 332, 100.0), ("sign_flips", "2-3"): (593, 573, 96.6), ("sign_flips", "4-5"): (919, 849, 92.4), ("sign_flips", "6-7"): (994, 883, 88.8),
      ("sign_flips", "8-10"): (1182, 995, 84.2), ("sign_flips", ">=11"): (671, 574, 85.5), ("dominant_sign", "negative"): (2513, 2374, 94.5), ("dominant_sign", "positive"): (2178, 1832, 84.1)}
for key_, want_ in T9.items():
    x = bd.loc[key_]
    check(f"Table S9 {key_}", (int(x.n_windows), int(x.n_answered), round(x.answered_pct, 1)), want_)
lg = pd.read_csv(RES / "unanswered_answering_logit.csv")
lg = lg[(lg.model == "qwen3-8b") & (lg.scope == "full_spy")].set_index("term")
check("answering AUC", round(lg.auc.iloc[0], 3), 0.744)
for term_, want_ in (("persistence_per_10pp", 0.64), ("log10_magnitude_bn", 0.65), ("sign_flips", 0.86), ("positive_dominant", 0.29), ("rule_detects", 15.84)):
    check(f"answering odds ratio {term_}", round(lg.loc[term_].odds_ratio, 2), want_)
rs = pd.read_csv(RES / "unanswered_repeat_stability.csv").set_index(["model", "base_arm"])
rq_ = rs.loc["qwen3-8b"]
check("qwen repeated windows", int(rq_.n_repeated.sum()), 588); check("qwen repeated answered in both", int(rq_.n_both.sum()), 483)
check("qwen repeated one pass only", int(rq_.n_one_pass_only.sum()), 92); check("qwen repeated neither pass", int(rq_.n_neither.sum()), 13)
check("qwen repeated same verdict (both answered)", int(rq_.n_same_verdict.sum()), 480)
gt = pd.read_csv(RES / "unanswered_gpu_time.csv").set_index("model")
GT = {"gpt-oss-20b": (3, 10.0, 4.9), "llama-3.1-8b-instruct": (5, 3.3, 2.2), "qwen3-8b": (4, 98.5, 31.7), "llama-3.1-8b-instruct-rf": (2, 2.3, 1.4),
      "gpt-oss-20b-t0": (2, 0.5, 0.5), "llama-3.1-8b-instruct-t0": (2, 0.3, 0.3)}
for model_, want_ in GT.items():
    g_ = gt.loc[model_]
    check(f"GPU time {model_}", (int(g_.n_gpus), round(g_.seconds_sum / 3600, 1), round(g_.union_hours, 1)), want_)
    check(f"GPU summed hours equal runs.csv.gz {model_}", round(g_.seconds_sum / 3600, 1), round(local[local.model == model_].sec.sum() / 3600, 1))
check("qwen GPU busy hours", round(gt.loc["qwen3-8b"].gpu_busy_hours, 1), 82.3)
check("three models summed GPU hours", round(gt.loc[["gpt-oss-20b", "llama-3.1-8b-instruct", "qwen3-8b"]].hours_sum.sum(), 1), 111.8)

print(f"{checked} checks, {len(failures)} mismatch(es)")
for f_ in failures:
    print("MISMATCH", f_)
sys.exit(1 if failures else 0)
