#!/usr/bin/env python3
"""Tie the numbers added for the stored-data analyses to docs/papers/electronics/results/ (read only).

Covers: Supplement Section S9 (every table row is regenerated from the result files and must appear verbatim in
latex/S9_Stored_Analyses.tex), the sentences of the article that state the 2024-2025 rate, the period shift, the intervals,
the later-date repeat of the hosted model, the direction of its departures, the same-day-expiry ablation and the timeline,
and the counts and the cost of the hosted runs.  It does not cover the rest of the manuscript.

Each check names the file, the row filter and the column it reads.  A mismatch is printed and the exit status is 1.

    ~/miniconda3/envs/AutoGex/bin/python docs/papers/electronics/check_numbers.py            # check
    ~/miniconda3/envs/AutoGex/bin/python docs/papers/electronics/check_numbers.py --emit     # print the S9 table rows
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
TEX = HERE / "latex"
failures: list[str] = []
checked = 0


# ---------------------------------------------------------------- helpers
def rd(name: str) -> pd.DataFrame:
    return pd.read_csv(RES / name)


def pick(df: pd.DataFrame, **flt) -> pd.Series:
    """The single row of df that matches every equality in flt."""
    m = pd.Series(True, index=df.index)
    for k, v in flt.items():
        m &= df[k] == v
    sub = df[m]
    if len(sub) != 1:
        raise SystemExit(f"filter {flt} matched {len(sub)} rows, expected 1")
    return sub.iloc[0]


def check(name, got, want, tol=0.0):
    global checked
    checked += 1
    if isinstance(want, (str, dict, list, tuple)) or isinstance(got, (str, dict, list, tuple)):
        ok = got == want
    else:
        ok = abs(float(got) - float(want)) <= tol
    if not ok:
        failures.append(f"{name}: results give {got!r}, the text says {want!r}")


def f1(x) -> str:
    """One decimal; a negative number is typeset with a math minus."""
    s = f"{abs(float(x)):.1f}"
    return "$-$" + s if float(x) < 0 and s != "0.0" else s


def f2(x) -> str:
    s = f"{abs(float(x)):.2f}"
    return "$-$" + s if float(x) < 0 and s != "0.00" else s


def f3(x) -> str:
    return f"{float(x):.3f}"


def n(x) -> str:
    return f"{int(round(float(x))):,}".replace(",", "{,}")


def ci(lo, hi, fmt=f1) -> str:
    return f"[{fmt(lo)}, {fmt(hi)}]"


PERIOD_TEX = {"2008-2019": "2008--2019", "2020-2023": "2020--2023", "2024-2025": "2024--2025", "2026": "2026", "all": "All windows"}


# ---------------------------------------------------------------- S9 table rows (regenerated from results/)
def rows() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}

    # E1 trivial comparators: stored_e1_comparators.csv, arm=full_spy
    c = rd("stored_e1_comparators.csv")
    r = []
    for p in ("2008-2019", "2020-2023", "2024-2025", "all"):
        x = pick(c, arm="full_spy", period=p)
        r.append(f"{PERIOD_TEX[p]} & {n(x.n_windows)} & {f1(x.arm_agreement_pct)} {ci(x.arm_agreement_lo_pct, x.arm_agreement_hi_pct)}"
                 f" & {f1(x.always_no_agreement_pct)} & {f1(x.flips_only_agreement_pct)} & {f1(x.magnitude_flips_agreement_pct)} \\\\")
    out["e1_comparators"] = r

    # E1 contested windows: stored_e1_contested.csv, arm=full_spy, definition=pivotal
    c = rd("stored_e1_contested.csv")
    r = []
    for p in ("2008-2019", "2020-2023", "2024-2025", "all"):
        x = pick(c, arm="full_spy", period=p, definition="pivotal")
        r.append(f"{PERIOD_TEX[p]} & {n(x.n_contested)} ({f1(x.contested_pct)}) & {f1(x.arm_agree_pct)} {ci(x.arm_agree_lo_pct, x.arm_agree_hi_pct)}"
                 f" & {f1(x.flips_only_agree_pct)} {ci(x.flips_only_agree_lo_pct, x.flips_only_agree_hi_pct)} & {f1(x.always_yes_agree_pct)}"
                 f" & {f1(x.arm_uncontested_agree_pct)} \\\\")
    out["e1_contested"] = r

    # E2 put weight: stored_e2_put_weight_grid.csv (period=2024-2025) and stored_e2_period_shift.csv (threshold_bn=5.0)
    g, s = rd("stored_e2_put_weight_grid.csv"), rd("stored_e2_period_shift.csv")
    r = []
    for w in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.05, 1.1, 1.2):
        rates = [pick(g, put_weight=w, threshold_bn=t, period="2024-2025").rate_pct for t in (3.0, 5.0, 7.0)]
        sh = [pick(s, put_weight=w, threshold_bn=5.0, baseline=b).shift_pp for b in ("2008-2019", "2020-2023")]
        wl = f"{w:g}" + (" (stored)" if w == 1.0 else "")
        r.append(f"{wl} & {f1(rates[0])} & {f1(rates[1])} & {f1(rates[2])} & {f1(sh[0])} & {f1(sh[1])} \\\\")
    out["e2_put_weight"] = r

    # E3 episodes and effective sample size: stored_e3_ess.csv
    e = rd("stored_e3_ess.csv")
    r = []
    for src in ("rule", "gpt-6-luna"):
        x = pick(e, source=src)
        r.append(f"{'Rule' if src == 'rule' else 'gpt-6-luna'} & {n(x.n_detected)} & {n(x.n_episodes)} & {f1(x.windows_per_episode_mean)}"
                 f" & {f1(x.ess_acf)} & {f1(x.ess_batch_30)} & {f1(x.ess_batch_sqrt_n)} \\\\")
    out["e3_ess"] = r

    # E3 intervals: stored_e3_intervals.csv
    iv = rd("stored_e3_intervals.csv")
    r = []
    for label, method, bl in (("Wilson, windows independent (502)", "wilson", 0), ("Calendar-quarter bootstrap (8 blocks)", "quarter_block", 0),
                              ("Moving block, 30 windows", "moving_block", 30), ("Moving block, 60 windows (primary)", "moving_block", 60),
                              ("Moving block, 90 windows", "moving_block", 90), ("Moving block, 120 windows", "moving_block", 120),
                              ("Circular block, 60 windows", "circular_block", 60), ("Episode bootstrap", "episode_bootstrap", 0),
                              ("Wilson at the effective sample size (ACF)", "wilson_ess_acf", 0)):
        a, b = (pick(iv, source=s_, method=method, block_len=bl) for s_ in ("rule", "gpt-6-luna"))
        r.append(f"{label} & {ci(a.ci_lo_pct, a.ci_hi_pct)} & {ci(b.ci_lo_pct, b.ci_hi_pct)} \\\\")
    out["e3_intervals"] = r

    # E4 period shift: stored_e4_shift_margin.csv, threshold_bn=5.0, block_len=60, circular=False
    m = rd("stored_e4_shift_margin.csv")
    r = []
    for ws, bl_ in (("all", "2020-2023"), ("all", "2020-2023 without 2022"), ("all", "2008-2019"), ("all", "2008-2023"),
                    ("shared", "2020-2023"), ("shared", "2020-2023 without 2022")):
        x = pick(m, window_set=ws, baseline=bl_, threshold_bn=5.0, block_len=60, circular=False)
        r.append(f"{ws.capitalize()} & {bl_} & {n(x.n_baseline)} & {f1(x.rate_baseline_pct)} & {f1(x.rate_late_pct)} & {f1(x.shift_pp)}"
                 f" & {ci(x.ci_lo_pp, x.ci_hi_pp)} & {'yes' if x.upper_below_margin else 'no'} \\\\")
    out["e4_shift"] = r

    # E6 scale-free thresholds: stored_e6_scale_free.csv and stored_e6_scale_free_shift.csv (block_len=60, baseline 2020-2023)
    sf, sh = rd("stored_e6_scale_free.csv"), rd("stored_e6_scale_free_shift.csv")
    r = []
    labels = {"fixed_5bn": "Fixed \\$5 billion (stored)", "spot_linear": "Threshold $\\propto$ spot", "spot_squared": "Threshold $\\propto$ spot$^2$",
              "trailing_gross_calibrated": "Share of trailing gross GEX, calibrated", "trailing_gross_12.5pct": "12.5\\% of trailing gross GEX",
              "no_magnitude": "No magnitude criterion"}
    for _, d in sh.iterrows():
        variant, ref = d.variant, d.reference_years
        a = pick(sf, variant=variant, reference_years=ref, period="2020-2023")
        b = pick(sf, variant=variant, reference_years=ref, period="2024-2025")
        refl = {"none": "--", "2024-2025": "2024--2025", "2020": "2020", "2010": "2010"}[ref]
        r.append(f"{labels[variant]} & {refl} & {f1(a.rate_pct)} & {f1(b.rate_pct)} ({n(b.n_detected)}) & {f1(d.shift_pp)} {ci(d.ci_lo_pp, d.ci_hi_pp)} \\\\")
    out["e6_scale_free"] = r

    # E9 same-day expiries by era: stored_e9_pair_by_era.csv
    pe = rd("stored_e9_pair_by_era.csv")
    r = []
    for era in ("2008-2013", "2014-2022", "2023-2026", "2024-2025", "all"):
        x = pick(pe, era=era)
        kap = "--" if pd.isna(x.kappa) else f3(x.kappa)
        r.append(f"{'All windows' if era == 'all' else era.replace('-', '--')} & {n(x.n_windows)} & {f1(x.rate_full_pct)} & {f1(x.rate_ex0dte_pct)}"
                 f" & {n(x.both)} & {n(x.only_full)} & {n(x.only_ex0dte)} & {n(x.discordant)} & {f1(x.gap_pp)} & {kap} \\\\")
    out["e9_era"] = r

    # E9 share of same-day expiries: stored_e9_same_day_share.csv
    sd = rd("stored_e9_same_day_share.csv")
    r = []
    for y in (2019, 2024, 2025, 2026):
        x = sd[sd.year.astype(str) == str(y)].iloc[0]
        r.append(f"{y} & {f1(x.abs_0dte_share_of_abs_net)} & {f1(x.abs_0dte_share_of_gross)} & {f1(x.gross_removed_share)} & {f1(x.sign_flip_pct)} \\\\")
    out["e9_share"] = r

    # E13 lineage by break: stored_e13_lineage_by_break.csv
    lb = rd("stored_e13_lineage_by_break.csv")
    r = []
    names = {"complete": "Complete series", "call_only": "Call-only series", "hybrid": "Hybrid (published, then call-only)"}
    for cand in ("complete", "call_only", "hybrid"):
        for part in ("windows ending before the break", "windows spanning the break", "windows starting on or after the break"):
            x = pick(lb, published_vs=cand, part=part)
            short = {"windows ending before the break": "end before the break", "windows spanning the break": "span the break",
                     "windows starting on or after the break": "start on or after it"}[part]
            r.append(f"{names[cand]} & {short} & {n(x.n_windows)} & {n(x.equal)} & {n(x.different)} \\\\")
    out["e13_lineage"] = r
    return out


# ---------------------------------------------------------------- text checks
def check_tex_rows():
    tex = (TEX / "S9_Stored_Analyses.tex").read_text()
    for table, lines in rows().items():
        for line in lines:
            global checked
            checked += 1
            if line not in tex:
                failures.append(f"S9 table {table}: row not in S9_Stored_Analyses.tex: {line}")


def check_prose():
    # --- E1: trivial comparators and contested windows (S9, Section 4.4)
    cmp_ = rd("stored_e1_comparators.csv")
    x = pick(cmp_, arm="full_spy", period="2024-2025")
    check("E1 flips-only agreement 2024-2025 (stored_e1_comparators.csv arm=full_spy period=2024-2025 flips_only_agreement_pct)", x.flips_only_agreement_pct, 100.0)
    check("E1 best trivial 2024-2025 (best_trivial)", x.best_trivial, "flips_only")
    con = pick(rd("stored_e1_contested.csv"), arm="full_spy", period="all", definition="pivotal")
    check("E1 contested windows (stored_e1_contested.csv pivotal all n_contested)", con.n_contested, 521)
    check("E1 contested share (contested_pct)", round(con.contested_pct, 1), 11.1)
    check("E1 windows (n_windows)", con.n_windows, 4691)
    check("E1 luna inside contested (arm_agree_pct)", round(con.arm_agree_pct, 1), 97.5)
    check("E1 luna outside contested (arm_uncontested_agree_pct)", round(con.arm_uncontested_agree_pct, 1), 99.9)
    check("E1 flips-only inside contested (flips_only_agree_pct)", round(con.flips_only_agree_pct, 1), 71.8)
    check("E1 discordant windows (arm_discordant_total)", con.arm_discordant_total, 16)
    check("E1 discordant in contested (arm_discordant_in_contested)", con.arm_discordant_in_contested, 13)
    check("E1 margin1 contested windows (definition=margin1 n_contested)", pick(rd("stored_e1_contested.csv"), arm="full_spy", period="all", definition="margin1").n_contested, 764)
    check("E1 contested 2024-2025 (period=2024-2025 n_contested)", pick(rd("stored_e1_contested.csv"), arm="full_spy", period="2024-2025", definition="pivotal").n_contested, 76)

    check("E1 windows near on persistence (stored_e1_contested.csv arm=full_spy period=all definition=pivotal n_by_persistence)", con.n_by_persistence, 70)
    check("E1 windows near on magnitude (n_by_magnitude)", con.n_by_magnitude, 256)
    check("E1 windows near on flips (n_by_flips)", con.n_by_flips, 234)
    check("E1 the three counts sum to 560 and the union is 521 (a window near on two criteria counts once)", con.n_by_persistence + con.n_by_magnitude + con.n_by_flips, 560)
    c2425 = pick(rd("stored_e1_contested.csv"), arm="full_spy", period="2024-2025", definition="pivotal")
    check("E1 flips-only agreement on the contested windows of 2024-2025 (period=2024-2025 flips_only_agree_pct)", c2425.flips_only_agree_pct, 100.0)
    check("E1 luna agreement on the contested windows of 2024-2025 (arm_agree_pct)", round(c2425.arm_agree_pct, 1), 96.1)
    # shared windows: years of the windows that the complete series has and the published inputs lack
    ly_ = rd("stored_e13_lineage_by_year.csv"); ly_ = ly_[ly_.comparison == "published vs complete"].set_index(ly_[ly_.comparison == "published vs complete"].year.astype(str))
    dy = rd("detection_by_year.csv"); dy = dy[(dy.label_source == "classifier") & (dy.series_key == "new_full") & (dy.symbol == "SPY") & (dy.scope == "year")]
    full_n = {str(int(y)): int(k) for y, k in zip(dy.year, dy.n)}
    miss = {y: full_n[y] - int(ly_.loc[y].n_common) for y in ("2020", "2021", "2022", "2023", "2024", "2025")}
    check("shared set: windows of the complete series missing from the published inputs by year (detection_by_year.csv new_full n minus stored_e13_lineage_by_year.csv n_common)", miss, {"2020": 29, "2021": 0, "2022": 0, "2023": 1, "2024": 1, "2025": 0})
    check("shared set: baseline windows dropped (1,005 less 975 = 29 + 1)", 1005 - 975, miss["2020"] + miss["2023"])
    check("shared set: late windows dropped (502 less 501)", 502 - 501, miss["2024"])

    # --- E3: episodes, effective sample size, intervals (Section 4.2, Methods 3.8, Discussion)
    ess = pick(rd("stored_e3_ess.csv"), source="rule")
    check("E3 episodes of the rule (stored_e3_ess.csv source=rule n_episodes)", ess.n_episodes, 7)
    check("E3 ESS ACF rule (ess_acf)", round(ess.ess_acf), 32)
    check("E3 ESS batch30 rule (ess_batch_30)", round(ess.ess_batch_30), 29)
    check("E3 ESS sqrt-n rule (ess_batch_sqrt_n)", round(ess.ess_batch_sqrt_n), 42)
    check("E3 detected windows (n_detected)", ess.n_detected, 60)
    iv = rd("stored_e3_intervals.csv")
    mb = pick(iv, source="rule", method="moving_block", block_len=60)
    check("E3 moving block 60 lower (stored_e3_intervals.csv source=rule method=moving_block block_len=60 ci_lo_pct)", round(mb.ci_lo_pct, 1), 3.8)
    check("E3 moving block 60 upper (ci_hi_pct)", round(mb.ci_hi_pct, 1), 24.1)
    check("E3 rate (rate_pct)", round(mb.rate_pct, 1), 12.0)
    w = pick(iv, source="rule", method="wilson", block_len=0)
    check("E3 Wilson lower (method=wilson ci_lo_pct)", round(w.ci_lo_pct, 1), 9.4)
    check("E3 Wilson upper (ci_hi_pct)", round(w.ci_hi_pct, 1), 15.1)
    q = pick(iv, source="rule", method="quarter_block", block_len=0)
    check("E3 quarter block lower (method=quarter_block ci_lo_pct)", round(q.ci_lo_pct, 1), 5.1)
    check("E3 quarter block upper (ci_hi_pct)", round(q.ci_hi_pct, 1), 19.6)
    lm = pick(iv, source="gpt-6-luna", method="moving_block", block_len=60)
    check("E3 luna moving block 60 lower (source=gpt-6-luna ci_lo_pct)", round(lm.ci_lo_pct, 1), 4.4)
    check("E3 luna moving block 60 upper (ci_hi_pct)", round(lm.ci_hi_pct, 1), 23.5)
    check("E3 luna rate (rate_pct)", round(lm.rate_pct, 1), 12.5)
    check("E3 non-overlapping windows (stored_e3_ess.csv n_nonoverlapping_30d)", round(ess.n_nonoverlapping_30d, 1), 16.7)
    check("E3 episodes of luna (source=gpt-6-luna n_episodes)", pick(rd("stored_e3_ess.csv"), source="gpt-6-luna").n_episodes, 11)

    # --- E4: period shift with a margin (Section 4.2, abstract, Introduction, Discussion, Conclusions, S9)
    m = rd("stored_e4_shift_margin.csv")
    a = pick(m, window_set="all", baseline="2020-2023", threshold_bn=5.0, block_len=60, circular=False)
    check("E4 shift all (stored_e4_shift_margin.csv window_set=all baseline=2020-2023 threshold_bn=5 block_len=60 circular=False shift_pp)", round(a.shift_pp, 1), -10.2)
    check("E4 interval lower (ci_lo_pp)", round(a.ci_lo_pp, 1), -20.9)
    check("E4 interval upper (ci_hi_pp)", round(a.ci_hi_pp, 1), 8.5)
    check("E4 margin (margin_pp)", a.margin_pp, 5.0)
    check("E4 upper below margin (upper_below_margin)", bool(a.upper_below_margin), False)
    check("E4 baseline rate (rate_baseline_pct)", round(a.rate_baseline_pct, 1), 22.2)
    check("E4 late rate (rate_late_pct)", round(a.rate_late_pct, 1), 12.0)
    check("E4 late windows (n_late)", a.n_late, 502)
    sh = pick(m, window_set="shared", baseline="2020-2023", threshold_bn=5.0, block_len=60, circular=False)
    check("E4 shift shared (window_set=shared shift_pp)", round(sh.shift_pp, 1), -7.9)
    check("E4 shared interval lower (ci_lo_pp)", round(sh.ci_lo_pp, 1), -20.9)
    check("E4 shared interval upper (ci_hi_pp)", round(sh.ci_hi_pp, 1), 8.6)
    check("E4 shared baseline windows (n_baseline)", sh.n_baseline, 975)
    check("E4 shared baseline rate (rate_baseline_pct)", round(sh.rate_baseline_pct, 1), 19.9)
    check("E4 shared late windows (n_late)", sh.n_late, 501)
    sm = rd("stored_e4_summary.csv")
    s = pick(sm, window_set="all", baseline="2020-2023", block_len=60, circular=False)
    check("E4 thresholds tested (stored_e4_summary.csv n_thresholds)", s.n_thresholds, 12)
    check("E4 thresholds with the upper limit below the margin (n_upper_below_margin)", s.n_upper_below_margin, 1)
    check("E4 largest upper limit (max_ci_hi_pp)", round(s.max_ci_hi_pp, 1), 19.7)
    nine = sm[(sm.block_len == 60) & (~sm.circular)]
    check("E4 baselines at block 60 (rows)", len(nine), 9)
    check("E4 most thresholds below the margin over the baselines (n_upper_below_margin max)", nine.n_upper_below_margin.max(), 1)
    a08 = pick(m, window_set="all", baseline="2008-2019", threshold_bn=5.0, block_len=60, circular=False)
    check("E4 shift against 2008-2019 (baseline=2008-2019 shift_pp)", round(a08.shift_pp, 1), 1.8)
    check("E4 interval against 2008-2019 lower (ci_lo_pp)", round(a08.ci_lo_pp, 1), -7.7)
    check("E4 interval against 2008-2019 upper (ci_hi_pp)", round(a08.ci_hi_pp, 1), 14.6)

    # --- E2: put weight (S9, Section 4.2)
    s2 = rd("stored_e2_period_shift.csv")
    check("E2 shift against 2020-2023 at put weight 0.9 (stored_e2_period_shift.csv threshold_bn=5 baseline=2020-2023 put_weight=0.9 shift_pp)",
          round(pick(s2, put_weight=0.9, threshold_bn=5.0, baseline="2020-2023").shift_pp, 1), -4.8)
    check("E2 shift against 2020-2023 at put weight 0.8 (put_weight=0.8)", round(pick(s2, put_weight=0.8, threshold_bn=5.0, baseline="2020-2023").shift_pp, 1), 4.6)
    sc = rd("stored_e2_sign_crossings.csv")
    c20 = pick(sc, threshold_bn=5.0, baseline="2020-2023")
    check("E2 sign change against 2020-2023 (stored_e2_sign_crossings.csv threshold_bn=5 baseline=2020-2023 put_weight)", round(c20.put_weight, 2), 0.85)
    c08 = sc[(sc.threshold_bn == 5.0) & (sc.baseline == "2008-2019")].sort_values("put_weight")
    check("E2 first sign change against 2008-2019 (put_weight)", round(c08.put_weight.iloc[0], 2), 1.03)
    check("E2 second sign change against 2008-2019 (put_weight)", round(c08.put_weight.iloc[1], 2), 1.10)

    check("E2 rate 2024-2025 at put weight 0.8 (stored_e2_put_weight_grid.csv put_weight=0.8 threshold_bn=5 period=2024-2025 rate_pct)",
          round(pick(rd("stored_e2_put_weight_grid.csv"), put_weight=0.8, threshold_bn=5.0, period="2024-2025").rate_pct, 1), 28.9)
    check("E2 rate 2024-2025 at put weight 0.9 (put_weight=0.9)", round(pick(rd("stored_e2_put_weight_grid.csv"), put_weight=0.9, threshold_bn=5.0, period="2024-2025").rate_pct, 1), 17.9)
    check("E2 rate 2024-2025 at put weight 1.0 (put_weight=1.0)", round(pick(rd("stored_e2_put_weight_grid.csv"), put_weight=1.0, threshold_bn=5.0, period="2024-2025").rate_pct, 1), 12.0)
    check("E4 thresholds whose upper limit is above the margin (n_thresholds - n_upper_below_margin)", s.n_thresholds - s.n_upper_below_margin, 11)
    check("E1 persistence and flips agreement 2024-2025 (stored_e1_comparators.csv arm=full_spy period=2024-2025 persistence_flips_agreement_pct)", x.persistence_flips_agreement_pct, 100.0)
    check("E1 flips-only agreement over all windows (period=all flips_only_agreement_pct)", round(pick(cmp_, arm="full_spy", period="all").flips_only_agreement_pct, 1), 63.7)
    check("E1 magnitude and flips agreement over all windows (magnitude_flips_agreement_pct)", round(pick(cmp_, arm="full_spy", period="all").magnitude_flips_agreement_pct, 1), 97.5)
    check("E1 luna agreement over all windows (arm_agreement_pct)", round(pick(cmp_, arm="full_spy", period="all").arm_agreement_pct, 1), 99.7)
    check("E1 windows 2024-2025 (n_windows)", x.n_windows, 502)

    # --- E6 (S9)
    sf = rd("stored_e6_scale_free.csv")
    check("E6 spot-squared detections 2024-2025 (stored_e6_scale_free.csv variant=spot_squared reference_years=2024-2025 period=2024-2025 n_detected)",
          pick(sf, variant="spot_squared", reference_years="2024-2025", period="2024-2025").n_detected, 57)
    check("E6 spot-squared detections 2024-2025 with the 2020 reference (reference_years=2020)",
          pick(sf, variant="spot_squared", reference_years="2020", period="2024-2025").n_detected, 0)
    shf = rd("stored_e6_scale_free_shift.csv")
    check("E6 largest shift of the variants referenced to 2024-2025 (min shift_pp)", round(shf[shf.reference_years == "2024-2025"].shift_pp.min(), 1), -17.4)
    check("E6 smallest fall of those variants (max shift_pp)", round(shf[(shf.reference_years.isin(["2024-2025", "none"])) & (shf.variant != "fixed_5bn")].shift_pp.max(), 1), -15.3)

    # --- E9: same-day expiries (Section 4.5, S9)
    pe = rd("stored_e9_pair_by_era.csv")
    e24 = pick(pe, era="2024-2025")
    check("E9 windows detected by both in 2024-2025 (stored_e9_pair_by_era.csv era=2024-2025 both)", e24.both, 47)
    check("E9 only full (only_full)", e24.only_full, 13)
    check("E9 only ex-0DTE (only_ex0dte)", e24.only_ex0dte, 27)
    check("E9 discordant (discordant)", e24.discordant, 40)
    check("E9 detected by either (detected_by_either)", e24.detected_by_either, 87)
    check("E9 discordant share of the windows detected by either (discordant_pct_of_either)", round(e24.discordant_pct_of_either, 1), 46.0)
    check("E9 gap in points (gap_pp)", round(e24.gap_pp, 1), -2.8)
    check("E9 kappa (kappa)", round(e24.kappa, 2), 0.66)
    ea = pick(pe, era="all")
    check("E9 gap over all windows (era=all gap_pp)", round(ea.gap_pp, 1), 2.5)
    check("E9 discordant over all windows (era=all discordant)", ea.discordant, 306)
    e1422 = pick(pe, era="2014-2022")
    check("E9 gap 2014-2022 (era=2014-2022 gap_pp)", round(e1422.gap_pp, 1), 7.0)
    e2326 = pick(pe, era="2023-2026")
    check("E9 gap 2023-2026 (era=2023-2026 gap_pp)", round(e2326.gap_pp, 1), -4.2)
    ei = rd("stored_e9_era_interaction.csv")
    i5 = pick(ei, threshold_bn=5.0, block_len=60)
    check("E9 interaction (stored_e9_era_interaction.csv threshold_bn=5 block_len=60 interaction_pp)", round(i5.interaction_pp, 1), -11.2)
    check("E9 interaction lower (ci_lo_pp)", round(i5.ci_lo_pp, 1), -18.3)
    check("E9 interaction upper (ci_hi_pp)", round(i5.ci_hi_pp, 1), -5.0)
    check("E9 thresholds whose interval excludes zero (threshold_bn 3 to 5.5, four block lengths)", int(ei.ci_excludes_zero.sum()), 24)
    check("E9 interaction cells (rows)", len(ei), 36)
    sd = rd("stored_e9_same_day_share.csv")
    s24 = sd[sd.year.astype(str) == "2024"].iloc[0]
    check("E9 share of absolute net 2024 (stored_e9_same_day_share.csv year=2024 abs_0dte_share_of_abs_net)", round(s24.abs_0dte_share_of_abs_net, 1), 45.9)
    check("E9 share of gross 2024 (abs_0dte_share_of_gross)", round(s24.abs_0dte_share_of_gross, 1), 7.6)
    check("E9 gross removed 2024 (gross_removed_share)", round(s24.gross_removed_share, 1), 18.0)
    s25 = sd[sd.year.astype(str) == "2025"].iloc[0]
    check("E9 gross removed 2025 (year=2025 gross_removed_share)", round(s25.gross_removed_share, 1), 20.0)

    # --- E13: lineage (S9; Section 4.1 and the Introduction state the 332 / 46 from published_input_gaps_by_year.csv)
    lb = rd("stored_e13_lineage_by_break.csv")
    check("E13 windows before the break equal to the complete series (stored_e13_lineage_by_break.csv published_vs=complete part=windows ending before the break equal)",
          pick(lb, published_vs="complete", part="windows ending before the break").equal, 865)
    check("E13 windows before the break (n_windows)", pick(lb, published_vs="complete", part="windows ending before the break").n_windows, 911)
    check("E13 windows from the break equal to call-only (published_vs=call_only part=windows starting on or after the break equal)",
          pick(lb, published_vs="call_only", part="windows starting on or after the break").equal, 536)
    check("E13 hybrid equals the published verdicts on the windows before the break (published_vs=hybrid equal)",
          pick(lb, published_vs="hybrid", part="windows ending before the break").equal, 865)
    dm = rd("stored_e13_day_match.csv")
    check("E13 post-break days equal to the call leg (stored_e13_day_match.csv candidate=call_only_call part=from the break n_equal_within_tol)",
          pick(dm, candidate="call_only_call", part="from the break").n_equal_within_tol, 565)
    check("E13 post-break days (n_days)", pick(dm, candidate="call_only_call", part="from the break").n_days, 565)
    check("E13 pre-break days equal to the complete net (candidate=complete_net part=before the break n_equal_within_tol)",
          pick(dm, candidate="complete_net", part="before the break").n_equal_within_tol, 900)
    check("E13 pre-break days (n_days)", pick(dm, candidate="complete_net", part="before the break").n_days, 940)
    ly = rd("stored_e13_lineage_by_year.csv")
    for yr in (2024, 2025):
        x = pick(ly, comparison="published vs call_only", year=str(yr)) if ly.year.dtype == object else pick(ly, comparison="published vs call_only", year=yr)
        check(f"E13 published equals call-only in {yr} (stored_e13_lineage_by_year.csv comparison=published vs call_only year={yr} different)", x.different, 0)

    # --- direction of the departures (Section 4.6): llm_departures.csv, model=gpt-6-luna
    d = rd("llm_departures.csv")
    d = d[d.model == "gpt-6-luna"]
    p = pick(d, scope="pooled", period="all")
    check("departures: pooled disagreements (llm_departures.csv model=gpt-6-luna scope=pooled period=all n_disagree)", p.n_disagree, 45)
    check("departures: model yes, rule no (n_model_yes_rule_no)", p.n_model_yes_rule_no, 29)
    check("departures: model no, rule yes (n_model_no_rule_yes)", p.n_model_no_rule_yes, 16)
    check("departures: arms pooled (n_arms)", p.n_arms, 9)
    check("departures: p_binomial", round(p.p_binomial, 3), 0.072)
    check("departures: share toward detection (share_model_yes_pct)", round(p.share_model_yes_pct, 1), 64.4)
    fs = pick(d, scope="arm", period="all", arm="full_spy")
    check("departures: full_spy yes (arm=full_spy n_model_yes_rule_no)", fs.n_model_yes_rule_no, 12)
    check("departures: full_spy no (n_model_no_rule_yes)", fs.n_model_no_rule_yes, 4)
    check("departures: full_spy disagreements (n_disagree)", fs.n_disagree, 16)
    check("departures: full_spy p_binomial", round(fs.p_binomial, 3), 0.077)

    # --- later-date repeat (Section 4.3): drift_summary.csv, bridge_agreement.csv
    ds = rd("drift_summary.csv")
    r2 = pick(ds, base_arm="full_spy", repeat_index=2)
    check("repeat: windows (drift_summary.csv base_arm=full_spy repeat_index=2 n_windows_compared)", r2.n_windows_compared, 300)
    check("repeat: same verdict (n_same)", r2.n_same, 294)
    check("repeat: percent same (pct_same)", round(r2.pct_same, 1), 98.0)
    check("repeat: kappa", round(r2.kappa, 3), 0.960)
    check("repeat: changed (n_changed)", r2.n_changed, 6)
    check("repeat: yes to no (n_detect_to_not)", r2.n_detect_to_not, 1)
    check("repeat: no to yes (n_not_to_detect)", r2.n_not_to_detect, 5)
    check("repeat: toward the rule (n_toward_rule)", r2.n_toward_rule, 3)
    check("repeat: away from the rule (n_away_from_rule)", r2.n_away_from_rule, 3)
    check("repeat: agreement with the rule, first pass (original_agree_with_rule_pct)", round(r2.original_agree_with_rule_pct, 1), 99.0)
    check("repeat: agreement with the rule, repeat (repeat_agree_with_rule_pct)", round(r2.repeat_agree_with_rule_pct, 1), 99.0)
    check("repeat: first answers (original_answer_first)", r2.original_answer_first, "2026-10-29")
    check("repeat: last first-pass answers (original_answer_last)", r2.original_answer_last, "2026-11-03")
    check("repeat: repeat date (repeat_answer_first)", r2.repeat_answer_first, "2026-11-24")
    check("repeat: same-job repeat windows (same_job_n_windows)", r2.same_job_n_windows, 235)
    check("repeat: same-job percent same (same_job_pct_same)", round(r2.same_job_pct_same, 1), 99.1)
    check("repeat: detection rate of the sample, first pass (original_rate_pct)", round(r2.original_rate_pct, 1), 49.0)
    check("repeat: detection rate of the sample, repeat (repeat_rate_pct)", round(r2.repeat_rate_pct, 1), 50.3)
    from datetime import date
    days = [(date.fromisoformat(r2.repeat_answer_first) - date.fromisoformat(d_)).days for d_ in (r2.original_answer_last, r2.original_answer_first)]
    check("repeat: days between the first answers and the repeat (original_answer_last, original_answer_first to repeat_answer_first)", days, [21, 26])
    ba = rd("bridge_agreement.csv")
    t = pick(ba, comparison="test_retest", ref_arm="full_spy", other_arm="full_spy#rep2", scope="all")
    check("repeat: pairs (bridge_agreement.csv comparison=test_retest other_arm=full_spy#rep2 scope=all n_pairs)", t.n_pairs, 300)
    check("repeat: agreement (agree_pct)", round(t.agree_pct, 1), 98.0)
    check("repeat: kappa (kappa)", round(t.kappa, 3), 0.960)
    check("repeat: agreement interval lower (bridge_agreement.csv full_spy#rep2 scope=all agree_boot_lo_pct)", round(t.agree_boot_lo_pct, 1), 96.4)
    check("repeat: agreement interval upper (agree_boot_hi_pct)", round(t.agree_boot_hi_pct, 1), 99.3)
    check("repeat: kappa interval lower (kappa_boot_lo)", round(t.kappa_boot_lo, 3), 0.927)
    check("repeat: kappa interval upper (kappa_boot_hi)", round(t.kappa_boot_hi, 3), 0.987)
    check("repeat: McNemar exact p (p_mcnemar_exact, not in the text)", round(t.p_mcnemar_exact, 3), 0.219)
    one = pick(ba, comparison="test_retest", ref_arm="full_spy", other_arm="full_spy#rep1", scope="all")
    check("repeat: same-job repeat of full_spy pairs (other_arm=full_spy#rep1 n_pairs)", one.n_pairs, 235)
    check("repeat: same-job repeat of full_spy percent (agree_pct)", round(one.agree_pct, 1), 99.1)
    check("repeat: windows that changed in the same-job repeat of full_spy (n_ref_det_oth_not + n_ref_not_oth_det)", one.n_ref_det_oth_not + one.n_ref_not_oth_det, 2)
    # second later-date repeat: 200 windows of the published inputs (bridge_jan#rep2)
    b2 = pick(ds, base_arm="bridge_jan", repeat_index=2)
    check("second repeat: windows, same, changed (drift_summary.csv base_arm=bridge_jan repeat_index=2)", (int(b2.n_windows_compared), int(b2.n_same), int(b2.n_changed)), (200, 198, 2))
    check("second repeat: percent same and kappa (pct_same, kappa)", (round(b2.pct_same, 1), round(b2.kappa, 3)), (99.0, 0.980))
    check("second repeat: yes to no, no to yes, toward and away from the rule", (int(b2.n_detect_to_not), int(b2.n_not_to_detect), int(b2.n_toward_rule), int(b2.n_away_from_rule)), (0, 2, 1, 1))
    check("second repeat: agreement with the rule in both passes", (round(b2.original_agree_with_rule_pct, 1), round(b2.repeat_agree_with_rule_pct, 1)), (99.5, 99.5))
    check("second repeat: dates of the first answers and of the repeat", (b2.original_answer_first, b2.original_answer_last, b2.repeat_answer_first), ("2026-10-30", "2026-10-30", "2026-11-24"))
    check("second repeat: days between the first answers and the repeat lie within 21 to 26", (date.fromisoformat(b2.repeat_answer_first) - date.fromisoformat(b2.original_answer_first)).days, 25)
    check("second repeat: same-job repeat on the same 200 windows (n_windows_in_both_repeats, same_job_pct_same_on_those)", (int(b2.n_windows_in_both_repeats), round(b2.same_job_pct_same_on_those, 1)), (200, 99.5))
    tb = pick(ba, comparison="test_retest", ref_arm="bridge_jan", other_arm="bridge_jan#rep2", scope="all")
    check("second repeat: pairs and agreement (bridge_agreement.csv other_arm=bridge_jan#rep2 scope=all)", (int(tb.n_pairs), round(tb.agree_pct, 1)), (200, 99.0))
    check("second repeat: agreement interval (agree_boot_lo_pct, agree_boot_hi_pct)", (round(tb.agree_boot_lo_pct, 1), round(tb.agree_boot_hi_pct, 1)), (97.4, 100.0))
    check("second repeat: kappa interval (kappa_boot_lo, kappa_boot_hi)", (round(tb.kappa_boot_lo, 3), round(tb.kappa_boot_hi, 3)), (0.946, 1.0))
    check("both repeats: windows, changed, toward and away from the rule", (int(r2.n_windows_compared + b2.n_windows_compared), int(r2.n_changed + b2.n_changed), int(r2.n_toward_rule + b2.n_toward_rule), int(r2.n_away_from_rule + b2.n_away_from_rule)), (500, 8, 4, 4))
    check("repeat: the repeat run times the windows answered 235", one.n_pairs, 235)

    # --- counts and cost of the hosted runs (Methods, Section S2, Figure 1)
    led = yaml.safe_load((RES / "cost_ledger.yaml").read_text())
    cl = rd("cost_ledger.csv")
    cur = cl[cl.counts_toward_budget.astype(bool)]
    later = cur[cur.run_id.str.contains("20261124T")]
    main = cur[~cur.run_id.str.contains("20261124T")]
    check("runs behind the main results: requests (cost_ledger.csv counts_toward_budget, run_id without a 20261124 timestamp, sum n_requests)", main.n_requests.sum(), 35833)
    check("runs behind the main results: cost in USD (sum est_cost_usd)", round(main.est_cost_usd.sum(), 2), 10.02)
    check("runs behind the main results: cost in USD, exact (sum est_cost_usd)", round(main.est_cost_usd.sum(), 6), 10.020749)
    check("runs behind the main results: jobs (rows)", len(main), 43)
    check("later-date repeat of full_spy: requests (cost_ledger.csv run_id 20261124T045255Z n_requests)", later[later.run_id.str.contains("045255Z")].n_requests.sum(), 300)
    check("later-date repeat of full_spy: cost in USD (est_cost_usd)", round(later[later.run_id.str.contains("045255Z")].est_cost_usd.sum(), 2), 0.09)
    check("later-date repeat of full_spy: status (status)", later[later.run_id.str.contains("045255Z")].status.iloc[0], "ingested")
    ing = cur[cur.status == "ingested"]
    rp = later[later.run_id.str.contains("045255Z")].iloc[0]
    check("S2: later-date repeat prompt tokens (cost_ledger.csv run_id 20261124T045255Z prompt_tokens)", rp.prompt_tokens, 573900)
    check("S2: later-date repeat completion tokens (completion_tokens)", rp.completion_tokens, 231129)
    check("S2: total prompt tokens of the runs behind the results (sum prompt_tokens)", main.prompt_tokens.sum(), 68576609)
    check("S2: total completion tokens of the runs behind the results (sum completion_tokens)", main.completion_tokens.sum(), 26324356)
    check("stored requests of all ingested hosted runs (status=ingested sum n_requests)", ing.n_requests.sum(), 36333)
    check("stored cost in USD of all ingested hosted runs (sum est_cost_usd)", round(ing.est_cost_usd.sum(), 2), 10.16)
    rb = later[later.run_id.str.contains("045259Z")].iloc[0]
    check("second later-date repeat (bridge_jan): requests, prompt and completion tokens, status", (int(rb.n_requests), int(rb.prompt_tokens), int(rb.completion_tokens), rb.status), (200, 382600, 145476, "ingested"))
    check("second later-date repeat: cost in USD (est_cost_usd)", round(rb.est_cost_usd, 2), 0.06)
    check("both later-date repeats: requests and cost in USD", (int(later.n_requests.sum()), round(later.est_cost_usd.sum(), 2)), (500, 0.14))
    check("cost_ledger.yaml budget.spent_usd", round(led["budget"]["spent_usd"], 6), 10.162725)
    check("cost_ledger.yaml hard stop (budget.hard_stop_usd)", led["budget"]["hard_stop_usd"], 12.0)
    check("backfilled o4-mini answers (cost_ledger.yaml totals.backfill.n_requests)", led["totals"]["backfill"]["n_requests"], 1922)
    ps = rd("llm_parse_stats.csv")
    g = ps[ps.model == "gpt-6-luna"]
    rep2 = g[g.arm.str.endswith("#rep2")]
    check("stored gpt-6-luna answers outside the later-date repeat (llm_parse_stats.csv model=gpt-6-luna, arm not ending #rep2, sum n_rows)", g[~g.arm.str.endswith("#rep2")].n_rows.sum(), 34784)
    check("stored answers of the later-date repeats (arm=full_spy#rep2 and bridge_jan#rep2 n_rows)", tuple(int(rep2.set_index("arm").n_rows[a]) for a in ("full_spy#rep2", "bridge_jan#rep2")), (300, 200))
    check("parsed answers of the later-date repeats (n_parsed)", rep2.n_parsed.sum(), 500)
    check("stored gpt-6-luna answers in all (sum n_rows)", g.n_rows.sum(), 35284)
    check("stored answers with the backfills and both repeats", int(g.n_rows.sum()) + 1922, 37206)
    check("repeat answers of the first submission (arm_role=repeat, arm not ending #rep2, sum n_rows)", g[(g.arm_role == "repeat") & ~g.arm.str.endswith("#rep2")].n_rows.sum(), 2992)
    # 1,516 duplicate-sample answers of the arms other than bridge_jan plus the 1,476 of the full repeat of bridge_jan
    check("duplicate sample of the other arms (1,516 = 2,992 less the 1,476 of bridge_jan#rep1)", 2992 - g[g.arm == "bridge_jan#rep1"].n_rows.sum(), 1516)
    check("requests submitted in all (cost_ledger.yaml totals.counted.n_requests)", led["totals"]["counted"]["n_requests"], 36333)
    check("requests sent in all = runs behind the results 35,833 + later-date repeats 500", 35833 + 500, led["totals"]["counted"]["n_requests"])
    dr = rd("drift_runs.csv")
    check("drift runs listed (drift_runs.csv rows)", len(dr), 2)
    check("drift runs ingested (drift_runs.csv status=ingested, sum n_answers_stored)", (int((dr.status == "ingested").sum()), int(dr.n_answers_stored.sum())), (2, 500))
    # Figure 1 (figures/output/fig01_study_design.json extra.cost_usd, extra.other_requests)
    import json
    fj = json.loads((HERE / "figures/output/fig01_study_design.json").read_text())["extra"]
    check("Figure 1 cost (fig01_study_design.json extra.cost_usd)", round(fj["cost_usd"], 2), 10.16)
    check("Figure 1 pilot and repeat requests (extra.other_requests)", fj["other_requests"], 3532)
    check("Figure 1 pilot and repeat requests = pilot 40 + bridge repeat 1,476 + duplicate samples 1,516 + later-date repeats 500", 40 + 1476 + 1516 + 500, 3532)

    # --- timeline (Methods 3.8): jobs submitted before the first bridge answer was complete
    cur2 = main[~main.run_id.str.startswith("pilot_")]
    first_bridge = cur2[cur2.arm == "bridge_jan"].completed_at.min()
    before = cur2[cur2.submitted_at < first_bridge]
    check("timeline: first bridge_jan job completed (cost_ledger.csv arm=bridge_jan min completed_at)", first_bridge, "2026-10-29T23:16:00Z")
    check("timeline: Batch jobs submitted before it (submitted_at < that time, rows)", len(before), 16)
    check("timeline: their requests (sum n_requests)", before.n_requests.sum(), 15106)
    check("timeline: all Batch jobs of the main runs submitted from 2026-10-29 to 2026-11-03 (min submitted_at date)", cur2.submitted_at.min()[:10], "2026-10-29")
    check("timeline: the re-requests of 2026-11-03 (run_id timestamp 20261103, sum n_requests)", cur2[cur2.run_id.str.contains("20261103T")].n_requests.sum(), 1121)


def main():
    if "--emit" in sys.argv:
        for name, lines in rows().items():
            print(f"% ---- {name}")
            print("\n".join(lines))
        return 0
    check_tex_rows()
    check_prose()
    for f in failures:
        print("MISMATCH:", f)
    print(f"{checked} checks, {len(failures)} mismatches")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
