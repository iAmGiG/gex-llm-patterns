# Published-claim inventory: what depends on SPY 2024-2025 GEX values and 2024-2025 regime detection

Task F3 (impact on published claims) | prepared 2026-10-28 | read-only: no table writes, no repo edits, no commits | branch `paper/electronics`

**Sources read.** AIAI: `docs/papers/paper2/aiai/*.tex`. JRFM: `docs/papers/jrfm/Regan_Xie_JRFM.tex` + `01..07` (line numbers below are in these section files; the MDPI production file `jrfm-4256551-production-CORRECTED.tex` is cross-referenced as `prod N`). Paper 1: IEEE BigData 2025 (`docs/papers/paper1/ieee_bigdata_2025/latex/`, frozen) and the journal draft (`docs/papers/paper1/journal_version/`).

**How the inventory was built.** Every quantitative statement was traced to a stored artifact (batch input/output JSONL, result YAMLs, research cache, SQLite and PostgreSQL tables, figure scripts) and, where possible, recomputed. All 168 `file:line` anchors were machine-checked: the quoted snippet occurs on that line (`f3/f3_validate_entries.py`, 0 mismatches). The recomputation log is section 11 and `f3/f3_evidence_output.txt`.

**Evidence labels.** **[V]** verified by a command in section 11. **[D]** diagnostic replay: the paper's deterministic criteria (>=21/30 same-sign days, mean |GEX| >= $5B, <=5 sign flips) applied to a different input series; these are not LLM re-runs. **[S]** speculation or not verified. Lineage tags (L-P1 .. L-RAW13) are defined in section 3.

**Caveat that applies to every [V] fit to "today's raw table".** `gex.options_chains_partitioned` was reloaded 2026-02-03, after the January run, so the published inputs cannot be regenerated bit for bit. The January extract equals today's table to the cent on every day of 2020 and on 99% of days in 2021-2022, so the table is an excellent proxy before the 2023-09-29 break; after it only the call-only relationship is established (501/501 days in 2024-25).

---

## 1. Bottom line

1. **"2024" is not one dataset in these papers.** Four series carry the label SPY 2024 GEX (L-P1, L-P3, L-PAPER1, L-P5). They fall into three conventions that disagree in sign and scale on the same dates [V]: puts-positive/calls-negative (Phase 1/2), -(call+put) (Phase 3 and Paper 1) and the January extract (signed net until 2023-09-28, call-only after). For the 53 Q1-2024 dates shared by Phase 1 and Phase 3 the sign differs on 53/53 (Phase 1 mean +14.2B, Phase 3 mean -34.9B, January extract mean +22.5B). The four headline results (Phase 1/2, Phase 3/4, Phase 5, Paper 1) therefore rest on different inputs, and only the January extract matches today's signed net before the 2023-09-29 break.
2. **Everything reported as "100% in 2024-2025" is the January extract, which from 2023-09-29 contains call-only GEX** [V]. From 2023-09-29 to 2025-12-31 (565/565 trading days) the value equals call_ex + call_0 and never the signed net. All 486 detections in 2024-25 are `persistent_positive` with 30/30 positive days and 0 sign flips. LLM labels equal the deterministic rule on the numbers sent in 1,412/1,412 windows [V], so the result is a property of the input series. Replaying the same criteria on today's signed net gives 2024 = 10.3% and 2025 = 13.6% [D]; mean daily |GEX| in 2024 is $6.5B (signed net) versus $20.2B (January extract) [D], so "$3.0B to $20.3B, +577%" becomes roughly $3.2B to $6.5B (about +99%).
3. **The step in Table 5 is a series break, not a 2023/2024 boundary.** 546 of the 1,412 parsed windows (38.7%) end on or after 2023-09-29 and hold 529 of the 646 detections (81.9%); the 866 earlier windows detect 117 (13.5%), not 45.8%. Within 2023, windows ending before 2023-09-29 detect 3/168 (1.8%); those ending on or after detect 43/60 (71.7%). The "non-monotonic 32.4% to 20.2%" pattern and its volatility explanation sit on this break.
4. **The 81.2% (2024) vs 12.1% (2020) headline, the 69.1 pp gap, phi, Fisher p, the bootstrap CIs, the 45-configuration sweep, the HMM benchmark and the ablation (n=84) do not use Phase 5 at all, and neither does the 50-response manual review (25 + 25 from 2024 and 2020 per the full-length draft).** They use the November-2025 pipeline: the 2024 series is `.cache/gex_database.db` `total_gex` (252/252 dates match [V]); 242 of those rows equal -(call+put) excluding same-day expiries (negative every day by construction; median error 0.3% against today's raw table) and 10 rows are placeholders (call and put components 0, no option count, spot price 6-7.5% below SPY). **All 42 rejected windows contain 3-6 of the 10 placeholder rows and none is free of them** [V]; with the 10 rows removed the series is negative every day and 2024 is 223/223. The same 10 dates are the "missing days" that Paper 1 dropped (242 of 252). The 2020 comparison series has 252/252 positive values although today's signed net is negative on 93 of 252 days (it tracks |gex_oi|, corr 0.996 [V]). The phase 3/4 prompts carried calendar dates (all 223 + 223 windows [V]).
5. **Paper 1 (and its imports into JRFM) rests on the same -(call+put) scalar.** The 242-day CSV correlates 0.997 with -(call+put) ex-0DTE (median error 2%) [V]. "All 242 days negative" is therefore by construction: today's signed net on those dates is negative on 93 days (75 below -$2B, mean +$1.26B). The raw-chain comparison (92.3% vs 61.5%) fed its GEX arm this scalar (-$25B to -$39B on all 13 dates); today's signed net on the same 13 dates is negative on 7 and below -$2B on 5. The text values "mean -$19.87B, range -$40.69B to -$4.75B" are not reproducible from the stored series (mean -$31.35B, range -$44.49B to -$20.66B).
6. **Two published figures do not show the data in their tables.** `fig08_detection_progression.png` (AIAI Fig. 6 = JRFM Fig. 8) is the hard-coded synthetic fallback (bars 27/223, 8/223, 72/223, 45/223, 223/223, 74/74; GEX $4.2B-$22.8B), not Phase 5 (213/241/244/228/241/245 windows; $3.0B-$19.0B). The compiled AIAI and JRFM PDFs embed pixel-identical copies [V]. `fig04_selectivity.png` and `fig02_regime_window.png` are synthetic by construction; `fig04_validation_pipeline.png` hard-codes "Phase 2 = 6.3%" and "phi = 0.672".
7. **What is not affected** (section 9): the 2020 and 2021 Phase 5 rows (window-level classification agreement with signed net 98-100%), 2022 approximately, the criteria and prompt definitions, external 0DTE statistics, the returns-based HMM rates, test arithmetic, literature and limitation text.

---

## 2. Headline map

| Headline claim | Where | Lineage | What the checks show |
|---|---|---|---|
| 100% detection 2024 and 2025, 486/486, Wilson CIs [98.4, 100], phi 0.82, total 45.8% | AIAI abstract, Table 4, Discussion; JRFM abstract, Table 5, Sec. 4.5, Conclusion | L-P5 | Call-only inputs from 2023-09-29 [V]; signed-net replay 10.3% / 13.6% [D]; 13.5% on the 866 windows before the break [V] |
| GEX magnitude $3.0B to $20.3B (+577%, JRFM) or $5B to $23B (+360%, AIAI) | AIAI Table 4, Discussion; JRFM abstract, Table 5 | L-P5 | Window means 2.97 / 4.88 / 5.52 / 9.58 / 20.35 / 18.97 [V]; $5B and $23B match no series; signed net |GEX| 3.24 / 4.99 / 5.46 / 6.10 / 6.46 / 7.13 [D] |
| 81.2% (2024) vs 12.1% (2020), 69.1 pp, phi, Fisher p, CIs, 42 rejections | AIAI abstract, Tables 2-3; JRFM abstract, Table 3, Sec. 4.3-4.4 | L-P3, L-P4 | Rejections come from 10 placeholder rows [V]; 2020 series sign-stripped [V]; dated prompts [V]; phi recomputes to 0.692 (AIAI prints 0.672) |
| 0% false positives on transitional and low-magnitude controls | AIAI abstract; JRFM abstract, Table 2 | L-P2 | Controls are x0.25 and 7-10 sign flips of one series per year; low-magnitude arm cannot reach $5B by construction |
| Threshold sensitivity | AIAI Discussion (25 combos, >72 pp); JRFM Sec. 4.6 (45 configs, 34.1-85.2 pp) | AIAI: L-P5; JRFM: L-P3, L-P4 | Two different datasets under one claim; AIAI min gap 72.8 pp on Phase 5 [V]; 2024 is 100% under every threshold |
| HMM benchmark (kappa 0.045, -0.178, 0.610) | JRFM Sec. 4.7, Fig. 7 | L-P3, L-P4, L-PAPER1 | Labels from Phase 3/4; GEX-native HMM fitted on the 242-day CSV that excludes the placeholder rows the LLM saw |
| Confidence analysis (92.8 vs 52.1; r = +0.719 / -0.705) | JRFM Sec. 4.8; AIAI Sec. 4.6 (r = +0.501 / -0.549) | L-P5 | JRFM values reproduce on 1,412 windows; excluding 2024-25: 85.8 vs 52.1, r = +0.511 / -0.477 [V]; AIAI r values do not reproduce |
| 98% / 96% / 100% mechanical accuracy (50 responses) | AIAI 4.6; JRFM 4.8 | L-P3, L-P4 | 25 from 2024 + 25 from 2020 per the full-length draft; no audit artifact in the repo |
| Ablation n=84 | AIAI Discussion | L-P3 | 2024 Phase 3 windows only; 100% in both arms |
| 71.5% detection, 91.2% accuracy, Sharpe 1.8 to 0.1, all 242 days negative | Paper 1; JRFM abstract/Intro/Sec. 4.1/Conclusion | L-PAPER1 | Scalar is -(call+put) [V]; 91.2% also carries the separate Issue #187 erratum (41.6%) |
| 92.3% (raw chain) vs 61.5% (GEX baseline), +30.8 pp | Paper 1; JRFM abstract, Sec. 4.2, Discussion | L-RAW13 | GEX arm fed the gross-negative scalar; confounded [V] |

---

## 3. Data lineages (what each published number is computed from)

All lineage facts below are [V] unless marked.

| Tag | Used for | Surviving input / result artifacts | What the series is |
|---|---|---|---|
| **L-P1** | Phase 1 (71.2%, 37/52); the 2024Q1 arms of Phase 2; AIAI Table 3 2024 persistence/magnitude (inferred) | `batch_jobs/batch_regime_20251106_184057.jsonl` (54 windows, Day T-k labels); `phase1_baseline_2024Q1.yaml` (52 windows, batch_690d320b...) | File cache `.cache/gex_data/SPY/<date>/gex_summary.json`, 2024 "full" format `total_gex` (calls negative, puts positive; spot_price field 434.0 / 468.0, not the SPY price). 53 of 54 window-end values equal the cache value (the 54th is the 2024-01-15 "mini" file; 2024-01-15 was an exchange holiday). Values +0.8B to +22B, mean +14.2B; all 37 detections `persistent_positive`. Cannot be reconciled with the raw table (2024-01-02: cache +10.01B, signed net -0.48B, gross 39.7B). |
| **L-P2** | Phase 2 controls (809 = 54+223 shuffle, 32+223 transitional, 54+223 low-magnitude) | `batch_regime_20251119_*.jsonl`; `phase2*_*.yaml` | Transformations of one series per year: shuffle day order; flip signs of 7-10 random days of windows with <=2 flips; multiply by 0.25 (`05_validate_regime_windows_batch.py`). 2024Q1 arms derive from L-P1; the 2020 arms derive from L-P4 (223/223 windows reproduced exactly). |
| **L-P3** | Phase 3 (81.2%, 181/223); Table 3/4 2024 column; Fisher/chi2/phi; bootstrap CIs; 45-config sweep; HMM labels; ablation (n=84); manual review (25 of 50) | `batch_jobs/phase3_full_2024_baseline_v2.jsonl` (223 windows, **calendar dates in every prompt**); `phase3_baseline_2024_full_year.yaml` (batch_691ea7f7...) | `.cache/gex_database.db` `daily_gex_metrics.total_gex`, created 2025-10-11..11-03: 252/252 dates equal. 242 rows: `net_call_gex` < 0 and `net_put_gex` < 0, value = -(call+put) excluding same-day expiries (best fit to today's raw table on 242/252 days, median error 0.3%; full gross 19.9%). 10 rows (2024-02-02, 02-09, 02-16, 02-23, 03-01, 03-08, 03-22, 03-28, 06-04, 06-06): total_gex +10.6B to +13.8B, call and put components 0, option count NaN, spot 461-495 vs SPY 494-535. |
| **L-P4** | Phase 4 (12.1%, 27/223); 2020 side of every 2024-vs-2020 statistic; the 2020 Phase 2 arms; the 2020 HMM labels | `batch_jobs/batch_regime_20251120_104630.jsonl` (223 windows, **calendar dates**); `phase4_baseline_2020.yaml` (batch_691f37d9...) | 252 daily values, **all positive** (0.01 to 11.23). Today's signed net (and the January extract) is negative on 93 of those 252 days. Correlation 0.996 with \|gex_oi\| in `consolidated_historical.db`; 0.62 with \|total_gex\|. Every window therefore has persistence 100% and 0 flips; detection is a magnitude test only (27 windows >= $5B). |
| **L-P5** | Phase 5 / Phase 4A: Tables 4 and 5, all per-year rates and CIs, GEX magnitudes, the 2023-to-2024 statistics, confidence analysis, AIAI 25-grid, fig06/fig08 | `batch_jobs/phase4a_postgresql_20260104_184832.jsonl` (1,476 windows, Day T-k labels); `results_phase4a_postgresql_20260104_193513.jsonl`; `.cache/research_cache.db` (1,412 rows) | PostgreSQL extract of 2026-01-04. Equals today's signed full net on 252/252 days in 2020, 250/252 in 2021, 247/251 in 2022, 151/249 in 2023 (98 call-only days), **0/501 in 2024-25 where it equals call_ex + call_0 on 501/501**. Last day equal to signed net: 2023-09-28; call-only on all 565 days from 2023-09-29. 1,476 windows sent, 1,412 parsed (64 invalid JSON, by year 10/11/7/21/10/5). Labels equal the deterministic rule on the numbers sent in 1,412/1,412. |
| **L-PAPER1** | Paper 1 (IEEE and journal draft) and every Paper 1 number imported into JRFM | `reports/statistical_validation/gamma_positioning_timeseries_2024.csv` (242 rows); `reports/validation/paper1_pattern_taxonomy/*_SPY_2024_*.yaml` (runs of 2025-10-16) | Same family as L-P3: -(call+put) ex-0DTE (corr 0.997, median error 2%). `net_gex_usd` -32.49B on 2024-01-02 with `call_gamma` -15.97B and `put_gamma` -16.52B. 242/242 negative (mean -31.35B, min -44.49B, max -20.66B). It omits exactly the 10 placeholder dates. |
| **L-RAW13** | 92.3% vs 61.5% | `reports/validation/paper1_raw_chain/` (batch 2025-11-25; 13 dates) | Raw strike tables only (no GEX) vs the L-PAPER1 baseline prompts for the same dates (GEX shown -$25.1B to -$38.8B). Today's signed net on these dates ranges -15.4 to +14.9B (negative on 7). |

**Other earlier-pipeline evidence in the repo.** `reports/validation/paper2_regime_windows/FINDINGS_SUMMARY.md` (2025-11-22) reports 2021-2025 as 100% / 100% / 100% / 81.2% / 100% persistent-negative; its average-GEX column (17.3, 27.2, 20.1, 30.0, 32.0, 30.4 $B) equals the yearly means of `consolidated_historical.db` `total_gex` (17.2, 27.2, 20.1, 30.0, 32.0, 30.4; negative on 1,473 of 1,475 days); the stored 2021-2023 batch outputs of that date are the all-zero-input runs described in `BUG_REPORT_zero_gex.md` (0% detection, mean magnitude $0.0-0.2B). `docs/papers/paper2/results/phase4a_results.md` records the pre-run expectation (2020 ~12%, 2021-2023 ~100%, 2024 ~81%, 2025 ~100%) from that earlier pipeline; the January run produced a different 2021-2023 pattern and the narrative was rewritten from "2020-2021 shift" to "gradual adoption, 2023-2024 shift".

---

## 4. Diagnostic replay: the paper's criteria on alternative input series [D]

Windows: 30 consecutive trading days ending 2020-02-13 .. 2025-12-31 in each series' own calendar. First row is the January extract the LLM was shown; its replay reproduces the published pattern (12.2 / 3.7 / 32.4 / 20.2 / 100 / 100) within a few points. Other rows apply the identical rule to today's raw table.

| Input series (30-day windows ending 2020-02-13..2025-12-31, deterministic criteria) | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Jan-2026 extract (published input) | 12.1 | 4.0 | 32.3 | 19.3 | 100.0 | 100.0 |
| today signed net, 0DTE incl. | 12.1 | 3.6 | 40.6 | 22.4 | 10.3 | 13.6 |
| today signed net, ex-0DTE | 2.7 | 0.0 | 36.7 | 25.2 | 13.1 | 16.4 |
| today call-only, 0DTE incl. | 90.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| today -(call+put) ex-0DTE [Nov-2025 convention] | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| today |net| [sign stripped] | 13.9 | 47.2 | 70.1 | 62.0 | 97.6 | 96.4 |

Window-level agreement between the January-extract classification and today's signed net, by quarter (percent of windows with the same detected/not-detected label): 2020 Q1-Q4 100/100/100/100; 2021 100/100/98.4/100; 2022 100/93.5/89.1/84.1; 2023 93.5/90.3/77.4/68.3; 2024 6.7/14.3/0.0/20.3; 2025 18.3/32.3/0.0/4.7 (`f3/f3_replay_quarterly_agreement.csv`).

Reading: the 2023-to-2024 jump exists only in the January extract. Under today's signed net the series is low and flat in 2024-25 (10-14%); under the November-2025 gross-negative convention every year including 2020 is 100% (no shift at all); under a sign-stripped |net| the 2024-25 rates are 96-98% but 2022-2023 are 62-70%.

---

## 5. AIAI claim inventory (48 anchors)

File paths are relative to `docs/papers/paper2/aiai/`. Dependency tags are defined in section 3.

| ID | Location | Claim | Depends on | Note |
|---|---|---|---|---|
| A01 | `Regan_Xie_AIAI.tex:27` | 1,412 real windows + 809 synthetic controls (2,221 evaluations) | L-P5 (1,412 = parsed Phase 4A windows, 486 of them in 2024-25; 64 of 1,476 dropped as unparseable) plus L-P2 (809 controls built from Q1-2024/L-P1 and 2020/L-P4 windows). The 498 Phase 1/3/4 real-window evaluations are not in the 1,412. [L-P5, L-P2] | Count bookkeeping: 1,412+809=2,221 excludes Phase 1/3/4 evaluations; $11.07 is the Phase 4A batch cost only (see JRFM 03_Methodology.tex:125). |
| A02 | `Regan_Xie_AIAI.tex:27` | 81.2% (2024) vs 12.1% (2020); 69.1 pp separation; phi = 0.672 | L-P3 (181/223, 2024) vs L-P4 (27/223, 2020). Not Phase 5. L-P3 = gex_database.db 2024 series (-(call+put), 10 placeholder rows); L-P4 = sign-stripped 2020 series; both with calendar dates in the prompt. [L-P3, L-P4] | phi recomputed from 181/223 vs 27/223 = 0.692 (JRFM prints 0.69). Phase 5 (same paper) gives 2024 = 100%. |
| A03 | `Regan_Xie_AIAI.tex:27` | 0% false positives on transitional and low-magnitude controls | L-P2: transformations (flip 7-10 signs; x0.25) of the Q1-2024 L-P1 series (+6..+15B) and the L-P4 2020 series. Low-magnitude arm scales ~$14B (2024Q1) / ~$2.6B (2020) down to ~$3.5B / ~$0.65B, so it cannot exceed the $5B criterion by construction. [L-P2] |  |
| A04 | `Regan_Xie_AIAI.tex:27` | Multi-year analysis shows gradual regime evolution tracking 0DTE adoption | L-P5, whole Table 4. The step to 100% coincides with a break in the January series: the last day equal to the signed full net is 2023-09-28; 2023-09-29 to 2025-12-31 (565/565 days) equals call-only GEX. [L-P5] | Diagnostic replay (deterministic criteria on today's signed net): 2024 = 10.3%, 2025 = 13.6%. |
| A05 | `01_Introduction.tex:16` | six years, 2,221 evaluations (1,412 real, 809 synthetic) | Same as A01. [L-P5, L-P2] |  |
| A06 | `01_Introduction.tex:17` | 69.1 pp discrimination: 2024 81.2% vs 2020 12.1%; 0% FP on synthetic controls | Same as A02/A03. [L-P3, L-P4, L-P2] |  |
| A07 | `02_Related_work.tex:22` | Paper 1: 71.5% detection, 91.2% predictive accuracy | Paper 1 (L-PAPER1): SPY 2024, 242 days. [L-PAPER1] | 91.2% is the IEEE pre-erratum materialization; Paper 1 journal/arXiv v2 replace it with 41.6% (Issue #187) - separate from the GEX issue. |
| A08 | `03_Methodology.tex:29` | Phase 2 controls validate robustness to GEX measurement method | L-P2 only transforms one series per year; no run compares two GEX conventions. The text also states call gamma + / put gamma -, while the 2024 series in L-P3/Paper 1 is -(call+put) (both negative) and L-P5 2024-25 is call-only. [L-P2, L-P3, L-P5] | Unsupported as stated. |
| A09 | `03_Methodology.tex:33` | Calendar dates become relative labels (Day T-29..T+0); LLM sees only GEX sequence | Phase 3 (2024) and Phase 4 (2020) input JSONL files (batch_jobs/phase3_full_2024_baseline_v2.jsonl, batch_regime_20251120_104630.jsonl) carry calendar dates (e.g. "2024-05-24: -30.67B") in all 223+223 prompts; one Phase 3 response quotes "2024-06-04". Phase 1, Phase 2 and Phase 5 prompts use Day T-k labels. [L-P3, L-P4] | Bears on the 81.2% vs 12.1% headline: the prompts for the two years being compared kept calendar dates (no ticker appears). |
| A10 | `03_Methodology.tex:44` | Primary dataset 2024 (252 days, 223 windows); comparison 2020 (252 days, 223 windows); multi-year 1,412 windows | L-P3 (252 rows, 10 of them placeholders), L-P4, L-P5. Phase 5 2024 has 241 parsed windows (251 sent); Phase 3 2024 has 223. [L-P3, L-P4, L-P5] | Two different 2024 window sets (223 and 241) give 81.2% and 100% in the same paper. |
| A11 | `03_Methodology.tex:52` | Phase 1: Q1 2024, 52 windows | L-P1 (.cache/gex_data gex_summary.json total_gex; positive, +6..+15B). [L-P1] |  |
| A12 | `03_Methodology.tex:54` | Phase 2: 809 windows = shuffle 404 / transitional 202 / low-magnitude 203 | L-P2. Stored YAMLs give 277 (54 + 223) / 255 (32 + 223) / 277 (54 + 223) = 809; JRFM uses these counts. [L-P2] | AIAI counts (404/202/203) are not supported by the stored files. |
| A13 | `04_Results.tex:9` | Validation-pipeline figure (fig04_validation_pipeline.png) caption: Phase 1 71.2%, negative controls 6.3%, full 2024 81.2%, 2020 12.1% | L-P1, L-P2, L-P3, L-P4 (figure values are hard-coded in fig04_validation_pipeline.py). [L-P1, L-P2, L-P3, L-P4, synthetic/hard-coded] | 6.3% not reproducible: shuffle-2024 = 61.1% (33/54), pooled false positives over the 809 controls = 60/809 = 7.4%. The "6.3% / 809 win" label comes from older figure scripts. |
| A14 | `04_Results.tex:15` | Phase 1: 71.2% (37/52); persistence 96.0% vs 57.0%; magnitude $11.66B vs $4.82B | L-P1 (phase1_baseline_2024Q1.yaml, batch_690d320b...). [L-P1] | YAML recomputation: 95.77% vs 58.00% persistence, $13.08B vs $5.86B (these are the JRFM values); AIAI persistence/magnitude values are not reproducible. All 37 detections are persistent_positive. |
| A15 | `04_Results.tex:15` | Phase 3: 81.2% (223 windows), 100% persistent negative | L-P3 (phase3_baseline_2024_full_year.yaml; input phase3_full_2024_baseline_v2.jsonl; series = gex_database.db daily_gex_metrics.total_gex, 252/252 dates match). [L-P3] | Contradicts Phase 1 (same Jan-Mar 2024 dates: P1 positive, P3 negative on 53/53 shared window-end dates) and Phase 5 (2024: 241/241 persistent_positive). |
| A16 | `04_Results.tex:15` | 42 windows (18.8%) rejected for Feb-Mar volatility (6-10 sign flips) | L-P3. Every one of the 42 rejected windows contains 3-6 of the 10 placeholder rows (2024-02-02, 02-09, 02-16, 02-23, 03-01, 03-08, 03-22, 03-28, 06-04, 06-06: total_gex +10.6..+13.8B, net_call_gex = net_put_gex = 0, options_count NaN, spot 6-7.5% below SPY); none is free of them (44 windows hold >=3 placeholders: 42 rejected, 2 detected; 130 detected windows hold none). [L-P3] | Without the 10 rows, 2024 = 223/223. The same 10 dates are the "missing days" in Paper 1 (242 of 252). |
| A17 | `04_Results.tex:29` | Table 2 shuffle: 2024 FP 61.1%, 2020 FP 12.1% | L-P2 (2024Q1: 33/54; 2020: 27/223). [L-P2] |  |
| A18 | `04_Results.tex:30` | Table 2 transitional: 0% / 0% | L-P2 (0/32 and 0/223). [L-P2] |  |
| A19 | `04_Results.tex:31` | Table 2 low-magnitude: 0% / 0% | L-P2 (0/54 and 0/223; x0.25 scaling). [L-P2] |  |
| A20 | `04_Results.tex:36` | 2024 regimes have 96% same-sign dominance; 5x difference 2024 vs 2020 shuffle | L-P1 (Q1-2024 persistence 95.8% for detected windows), L-P2. [L-P1, L-P2] |  |
| A21 | `04_Results.tex:50` | Table 3: detection 81.2% vs 12.1% (+69.1 pp) | L-P3 / L-P4. [L-P3, L-P4] |  |
| A22 | `04_Results.tex:51` | Table 3: avg persistence 96.0% (2024) vs 83.3% (2020) | Not reproducible from stored YAMLs: Phase 3 mean persistence 95.65%; Phase 4 persistence = 100% in every window (series has no negative values). [L-P3, L-P4] |  |
| A23 | `04_Results.tex:52` | Table 3: avg magnitude $13.95B (2024) vs $2.85B (2020) | Phase 3 YAML mean magnitude = $30.7B (detected $30.5B), so $13.95B matches the Q1-2024 L-P1 level (~$14B), not L-P3. $2.85B = mean \|value\| of the L-P4 series. [L-P1, L-P3, L-P4] | Mixes series within one row. |
| A24 | `04_Results.tex:53` | Table 3: dominant sign Negative (2024) vs Positive (2020), "Flip" | 2024 Negative = L-P3 by construction (-(call+put) is negative every day); 2020 Positive = L-P4 (252/252 days positive, but today's signed net is negative on 93 of 252 days in 2020). Phase 5 2024-25 detections are 486/486 persistent_positive. [L-P3, L-P4, L-P5] | Sign contradiction between phases. |
| A25 | `04_Results.tex:59` | phi = 0.672, p < 0.0001 for 2024 vs 2020 | L-P3 / L-P4 counts. [L-P3, L-P4] | Recomputed phi = 0.692. |
| A26 | `04_Results.tex:84` | Table 4 2023: 46/228 = 20.2%, avg GEX $10-15B | L-P5. Partly affected: 3/168 windows ending before 2023-09-29 (1.8%) vs 43/60 windows ending on/after 2023-09-29 (71.7%, all persistent_positive, call-only series). [L-P5] | Avg GEX column: LLM-reported mean \|GEX\| per window = $9.58B (2023), $2.97B (2020), $4.88B (2021), $5.52B (2022); AIAI values do not match any stored mean. |
| A27 | `04_Results.tex:85` | Table 4 2024: 241/241 = 100%, avg GEX $23B | L-P5: every 2024 window is 30/30 positive days, 0 flips, mean \|GEX\| $20.35B (call-only series). 241 of 251 windows parsed. [L-P5] | Replay under today's signed net: 10.3%. $23B is not in any series (2024 mean 20.35). |
| A28 | `04_Results.tex:86` | Table 4 2025: 245/245 = 100%, avg GEX $23B | L-P5: 245 windows, all 30/30 positive, mean $18.97B. [L-P5] | Replay under today's signed net: 13.6%. |
| A29 | `04_Results.tex:88` | Table 4 total: 646/1,412 = 45.8% | L-P5: 486 of the 646 detections (75.2%) are 2024-25; 529 of 646 (81.9%) are in windows ending on/after 2023-09-29; 520/520 windows ending on/after 2023-11-09 (fully call-only) are detected. [L-P5] | Detection on the 866 windows ending before 2023-09-29 = 117/866 = 13.5%. |
| A30 | `04_Results.tex:93` | GEX magnitude grew 360% ($5B to $23B), far exceeding inflation | L-P5 magnitudes (call-only in 2024-25). Window means: 2021 4.88, 2024 20.35, 2025 18.97 ($B). [L-P5] | Data give +317% (2021->2024) or +585% (2020->2024); $5B and $23B are approximate figures that do not match the stored means. |
| A31 | `04_Results.tex:93` | 2023->2024 transition p < 0.0001, phi = 0.783 | L-P5 counts (46/228 vs 241/241). [L-P5] | Recomputed phi = 0.819 (JRFM prints 0.82). |
| A32 | `04_Results.tex:93` | Sustained 100% detection 2024-2025 (486/486 windows) | L-P5. [L-P5] | Deterministic: 486/486 windows are call-only values, all positive. |
| A33 | `04_Results.tex:98` | GEX-magnitude figure (fig06_gex_magnitude_distribution.png) caption: 2020 mean $3.0B, 2024 mean $20.3B; $5B threshold discriminates eras | L-P5 (research_cache.db llm_detections: 2020 n=213 mean 2.97; 2024 n=241 mean 20.35). [L-P5] | Figure is real Phase 4A data (n=213 / n=241 on the plot). |
| A34 | `04_Results.tex:104` | 98% / 96% / 100% mechanical accuracy on 50 sampled detections; 88% step-by-step | Per the full-length draft (docs/papers/paper2/latex/05_Results.tex:365) the 50 = 25 from 2024 + 25 from 2020, i.e. Phase 3 (L-P3) and Phase 4 (L-P4) detections. No per-window audit artifact found in the repo. [L-P3, L-P4] | On Phase 5 the check can be automated: LLM labels = deterministic rule on the numbers sent for 1,412/1,412 windows; persistence within 2 pp 99.9%, magnitude within $0.5B 99.9%, flips exact 100%. |
| A35 | `04_Results.tex:104` | Confidence 92.8% (detected) vs 52.1% (rejected), 40.7 pp gap | L-P5, all 1,412 windows (reproduces exactly). 486 of 646 detections are 2024-25 (mean confidence ~95). [L-P5] | Excluding 2024-25 windows: detected 85.8% vs rejected 52.1%. |
| A36 | `04_Results.tex:104` | Confidence correlates r = +0.501 (persistence), r = -0.549 (stability) | Not reproducible. L-P5 gives +0.719 / -0.705 (JRFM values); excluding 2024-25: +0.511 / -0.477; Phase 3 alone +0.681 / -0.688. [L-P5] |  |
| A37 | `05_Discussion.tex:6` | 69.1 pp discrimination; "5.7x separation" | L-P3 / L-P4. [L-P3, L-P4] | 81.2/12.1 = 6.7x (JRFM prints 6.7x); 5.7x is an arithmetic slip. |
| A38 | `05_Discussion.tex:8` | 98% mechanical accuracy; 0% FP on controls; confidence r > 0.4 | L-P3/L-P4 manual sample (accuracy), L-P2 (controls), L-P5 (confidence). [L-P3, L-P4, L-P2, L-P5] |  |
| A39 | `05_Discussion.tex:14` | 69.1 pp is a property of the data, reproducible by any classifier applying the thresholds | Verified: LLM label = deterministic rule on the sent numbers in 223/223 Phase 3 windows and 1,412/1,412 Phase 5 windows. So every detection rate is a function of the input series (L-P3, L-P4, L-P5). [L-P3, L-P4, L-P5] | This is why zero-cost replays of the criteria are a valid impact test. |
| A40 | `05_Discussion.tex:18` | Detection 12.2% (2020), 3.7% (2021), 32.4% (2022), 100% (2024-25); GEX +360% ($5B to $23B) | L-P5. [L-P5] |  |
| A41 | `05_Discussion.tex:23` | Detection-progression figure (fig08_detection_progression.png) caption: temporal progression 2020-2025; 360% growth | Figure fig08_detection_progression.png: plotted values are the hard-coded synthetic fallback, not Phase 5 (see section 8). [L-P5, synthetic/hard-coded] |  |
| A42 | `05_Discussion.tex:27` | Non-monotonic 32.4% -> 20.2% -> 100%; 2023 volatility "disrupted regime formation" | L-P5. 2023 = 1.8% before 2023-09-29 and 71.7% after (series becomes call-only). 2022 detections are persistent_negative (79/79), 2023-Q4 and 2024-25 are persistent_positive. [L-P5] | The FOMC/banking-stress explanation is interpretation; the series break is a simpler explanation of the 2023 pattern. |
| A43 | `05_Discussion.tex:29` | Detection flat through 2023 then jumped discontinuously in 2024 (0DTE saturation ~48%) | L-P5. The discontinuity is at 2023-09-29 in the January series, not at the 2023/2024 boundary. [L-P5] |  |
| A44 | `05_Discussion.tex:47` | Ablation (n=84): identical accuracy with and without narrative scaffolding | Uses 2024 windows only: balanced sample from Phase 3 (L-P3); window ends 2024-02-14..2024-12-27; 80 (narrative) / 81 (data-only) windows evaluated, 100% accuracy in both arms; ground truth = Phase 3 labels (including the placeholder-driven rejections). [L-P3] | reports/validation/paper2_regime_windows/ablation_full_n84.yaml |
| A45 | `05_Discussion.tex:49` | All 25 threshold combinations maintain >72 pp (2024 vs 2020) | L-P5 (Phase 4A: 2024 n=241 vs 2020 n=213; 5x5 persistence x magnitude grid, flips <=5; reports/validation/sensitivity_analysis/threshold_sensitivity.yaml and fig11 script read research_cache.db). [L-P5] | Recomputed min gap = 72.8 pp. 2024 is 100% under every threshold because all 241 windows are 30/30 positive, 0 flips, $20B; the result tests the 2020 side only. JRFM's 45-config sweep uses L-P3/L-P4 and gives min 34.1 pp. |
| A46 | `06_Conclusion.tex:4` | Conclusion: 2,221 evaluations (1,412 real, 809 synthetic) | Same as A01. [L-P5, L-P2] |  |
| A47 | `06_Conclusion.tex:7` | Conclusion: 69.1 pp (2024 81.2% vs 2020 12.1%); 0% FP; 98% mechanical accuracy | L-P3/L-P4/L-P2 and the manual sample (A34). [L-P3, L-P4, L-P2] |  |
| A48 | `06_Conclusion.tex:9` | Selective 12-81% detection (persistence >=70%, magnitude >=$5B, flips <=5) | L-P3/L-P4 only; Phase 5 reports 100% for 2024-25. [L-P3, L-P4, L-P5] |  |


---

## 6. JRFM claim inventory (92 anchors)

File paths are relative to `docs/papers/jrfm/`; `prod N` is the matching line in `jrfm-4256551-production-CORRECTED.tex`.

| ID | Location (section file:line; production tex line) | Claim | Depends on | Note |
|---|---|---|---|---|
| J01 | `Regan_Xie_JRFM.tex:52`; prod `67-68` | Abstract: 2,221 evaluations = 1,412 real windows + 809 synthetic controls, 2020-2025 | L-P5 (1,412 parsed of 1,476 Phase 4A windows; 486 are 2024-25) and L-P2 (809 controls from L-P1 2024Q1 and L-P4 2020). [L-P5, L-P2] | Phase 1/3/4 real-window evaluations (52+223+223) are not counted; $11.07 is the Phase 4A cost. |
| J02 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: single-day 71.5% detection, 91.2% predictive accuracy | Paper 1 (L-PAPER1): SPY 2024, 242 days x 3 patterns, GEX scalar = -(call+put) ex-0DTE. [L-PAPER1] | 91.2% is the IEEE pre-erratum materialization (Paper 1 journal/arXiv v2: 41.6%, Issue #187); separate from the GEX issue. |
| J03 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: raw strike-level data beats pre-calculated GEX by 30.8 pp (92.3% vs 61.5%) | Paper 1 raw-chain test (L-RAW13): 13 Q1-Q2 2024 dates; the GEX-assisted arm was fed the -(call+put) scalar (-$25B to -$39B on all 13 dates). [L-RAW13] | Today's signed net on the same 13 dates is negative on 7 and below -$2B on 5. The comparison is confounded by what the GEX arm was shown. |
| J04 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: 81.2% 2024 (CI 75.8-86.1) vs 12.1% 2020 (CI 8.1-16.6); 69.1 pp | L-P3 (181/223) and L-P4 (27/223); percentile-bootstrap CIs from scripts/validation/paper2/jrfm_revision/bootstrap_detection_ci.py over the Phase 3/4 YAMLs. [L-P3, L-P4] | CI arithmetic reproduces (reports/.../jrfm_revision_ci.yaml). |
| J05 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: phi = 0.69, Fisher exact p = 1.8e-52 | L-P3 / L-P4 counts. [L-P3, L-P4] | Reproduces: chi2 213.67, Yates 210.90, Fisher 1.82e-52, OR 31.3, phi 0.692, RD CI [62.4, 75.7]. |
| J06 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: 0% false positives on synthetic controls | L-P2. [L-P2] | Shuffle control is excluded from the 0% (61.1% in 2024, 12.1% in 2020). |
| J07 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: detection 3.7% (2021) -> 100% (2024); GEX magnitude $3.0B -> $20.3B | L-P5 (2024: 241/241, call-only series; 2020 mean 2.97, 2024 mean 20.35). [L-P5] | Replay under today's signed net: 2024 = 10.3%. |
| J08 | `Regan_Xie_JRFM.tex:52`; prod `68` | Abstract: stable detection despite collapsing profitability (Sharpe 1.8 -> 0.1) | Paper 1 (L-PAPER1) 2024 quarterly detection and strategy returns. [L-PAPER1] |  |
| J09 | `01_Introduction.tex:6`; prod `83` | Design premise: 2020 episodic vs 2024 sustained dealer positioning | L-P3/L-P4 and L-P5 (the contrast is built on these series). [L-P3, L-P4, L-P5] |  |
| J10 | `01_Introduction.tex:16`; prod `94` | Single-day: 242 days, 71.5% detection, 91.2% materialize, raw chain 92.3% (+30.8 pp) | Paper 1 (L-PAPER1, L-RAW13). [L-PAPER1, L-RAW13] |  |
| J11 | `01_Introduction.tex:18`; prod `97` | Multi-day: 81.2% (CI) vs 12.1% (CI), 69.1 pp, phi 0.69, Fisher p; 3.7% (2021) -> 100% (2024); $3.0B -> $20.3B | L-P3/L-P4 (81.2 vs 12.1) and L-P5 (3.7 -> 100; $3.0B -> $20.3B). [L-P3, L-P4, L-P5] |  |
| J12 | `01_Introduction.tex:32`; prod `111` | Contributions: 92.3 vs 61.5; 69.1 pp; 0% FP; 68-74% quarterly detection; Sharpe 1.8 -> 0.1 | Paper 1, L-RAW13, L-P3/L-P4, L-P2. [L-PAPER1, L-RAW13, L-P3, L-P4, L-P2] |  |
| J13 | `01_Introduction.tex:37`; prod `116` | Findings: 69.1 pp gap, 0% FP, gradual 2021-2024 regime evolution (presented as downstream evidence) | L-P3/L-P4/L-P2/L-P5. [L-P3, L-P4, L-P2, L-P5] |  |
| J14 | `02_Related_Work.tex:14`; prod `138` | Panel consistent with 0DTE: 3.7% (2021) -> 100% (2024-2025) | L-P5. [L-P5] |  |
| J15 | `02_Related_Work.tex:34`; prod `158` | Companion paper: 71.5% detection, 91.2% predictive accuracy | Paper 1. [L-PAPER1] |  |
| J16 | `03_Methodology.tex:6`; prod `180` | Obfuscation: dates mapped to relative labels; tickers replaced | Phase 3 and Phase 4 prompts (L-P3/L-P4) kept calendar dates (verified in input JSONL). [L-P3, L-P4] | Bears on the 81.2% vs 12.1% headline. |
| J17 | `03_Methodology.tex:15`; prod `192` | Illustrative row: SPY 2024-03-15 Net GEX -$32.9B, Flip $485.00 | Not any stored value for that date (Paper 1 -29.29B, Phase 3 -29.84B, cache +12.30B, Jan +14.61B, today's signed net -15.35B). The obfuscation figure (fig01_obfuscation.png) shows -$12.3B for the same date. [synthetic/hard-coded] | Illustrative; the -$32.9B level is the Paper 1 (-(call+put)) scale. |
| J18 | `03_Methodology.tex:57`; prod `235` | ~220 windows per year from ~250 days, yielding 1,412 real windows | L-P5 (1,476 windows generated, 64 dropped for unparseable JSON, 486 in 2024-25). [L-P5] | Per-year parsed windows: 213/241/244/228/241/245. |
| J19 | `03_Methodology.tex:93`; prod `271` | GEX sign convention: calls +, puts - | Not the convention of the 2024 series in L-P3 / Paper 1 (-(call+put), both negative) nor of L-P5 2024-25 (call-only). [L-P3, L-P5, L-PAPER1] |  |
| J20 | `03_Methodology.tex:95`; prod `273` | 30.8 pp improvement over the net GEX baseline implies scalar aggregation discards signal | L-RAW13. [L-RAW13] |  |
| J21 | `03_Methodology.tex:105`; prod `283` | Phase 1: Q1 2024 baseline, 52 windows | L-P1. [L-P1] |  |
| J22 | `03_Methodology.tex:107`; prod `285` | Phase 2: 809 windows (shuffled 277, transitional 255, low-magnitude 277) | L-P2 (counts reproduce: 54+223, 32+223, 54+223). [L-P2] | Implementation differs from the text: transitional = flip signs of 7-10 random days of windows with <=2 flips; low-magnitude = multiply by 0.25 (not "magnitude below $3B" generation). |
| J23 | `03_Methodology.tex:115`; prod `295` | Phase 3: full 2024, 223 windows | L-P3. [L-P3] |  |
| J24 | `03_Methodology.tex:117`; prod `297` | Phase 4: 2020, 223 windows; 0DTE share <5% vs ~46% (SPY) | L-P4 (0DTE share is external). [L-P4] |  |
| J25 | `03_Methodology.tex:119`; prod `299` | Phase 5: multi-year 2020-2025, 1,412 windows | L-P5. [L-P5] |  |
| J26 | `03_Methodology.tex:125`; prod `305` | Total cost $11.07 across 2,221 evaluations | Phase 4A batch cost ($11.07 per docs/papers/paper2/results/phase4a_results.md, 1,476 requests). [L-P5] | Not tied to 2024-25 values; count basis inconsistent (see J01). |
| J27 | `03_Methodology.tex:139`; prod `319` | HMM benchmark scored on the Phase 3 (2024) and Phase 4 (2020) windows | LLM labels from L-P3 / L-P4 YAMLs (not Phase 5). [L-P3, L-P4] |  |
| J28 | `03_Methodology.tex:146`; prod `326` | GEX-native HMM fitted on the daily 2024 net-GEX series | reports/statistical_validation/gamma_positioning_timeseries_2024.csv = Paper 1 242-day series (-(call+put) ex-0DTE; r = 0.997). It excludes the 10 placeholder dates that are present in the Phase 3 series the LLM labels were generated on. [L-PAPER1, L-P3] |  |
| J29 | `04_Results.tex:8`; prod `94` | 242 days: 71.5% detection, 91.2% predictive accuracy; >90% WHO/WHOM/WHAT | Paper 1. [L-PAPER1] |  |
| J30 | `04_Results.tex:10`; prod `349` | Quarterly detection 68.2/70.5/72.8/73.6%, no seasonal variation (p = 0.84) | Paper 1 quarterly runs (L-PAPER1). [L-PAPER1] | Paper 1 reports Cochran-Armitage p = 0.42; JRFM prints p = 0.84. |
| J31 | `04_Results.tex:15`; prod `354` | Raw chain 92.3% vs GEX-assisted baseline 61.5% (+30.8 pp) | L-RAW13. [L-RAW13] |  |
| J32 | `04_Results.tex:26`; prod `368` | Table 1: 12/13 vs 8/13 on 13 identical test dates; reasoning scores | L-RAW13: dates 2024-01-02, 01-09, 01-17, 01-18, 01-19, 03-05, 03-06, 03-13, 03-15, 06-05, 06-07, 06-21, 06-28. [L-RAW13] | The baseline arm's 5 misses (confidence 0) occurred with the scalar at -$25.5B to -$35.6B. |
| J33 | `04_Results.tex:39`; prod `356` | Parametric GEX is lossy compression of structural signal (RQ2) | Inference from L-RAW13; assumes the GEX scalar in the baseline was a correct compression of the chain. [L-RAW13] |  |
| J34 | `04_Results.tex:43`; prod `385` | Detection stable 68-74% while Sharpe 1.8 -> 0.1 | Paper 1 (L-PAPER1) quarterly detection + forward returns. [L-PAPER1] |  |
| J35 | `04_Results.tex:47`; prod `389` | Inverse p-hacking: 519 detection days vs 100-day baseline; 33% lower range (lift 0.67, chi2 = 4.53, p = 0.033) | Paper 1 detection days (L-PAPER1) and 2024 intraday ranges. [L-PAPER1] |  |
| J36 | `04_Results.tex:60`; prod `402` | CIs: bootstrap over windows for Phases 1-4 and Phase 2; Wilson for Phase 5 | L-P1..L-P4 per-window YAMLs; Phase 5 counts hard-coded in bootstrap_detection_ci.py (per-window Phase 5 records were not used). [L-P1, L-P2, L-P3, L-P4, L-P5] |  |
| J37 | `04_Results.tex:74`; prod `416` | fig03_validation_pipeline.png caption: Phase 1 71.2%; Phase 3 81.2%; Phase 4 12.1%; "95% bootstrap CI" boxes | fig03_validation_pipeline.png = fig04_validation_pipeline.py (hard-coded). [L-P1, L-P3, L-P4, synthetic/hard-coded] | The PNG has no CI boxes and no Phase 5; shows Phase 2 = 6.3% (n=52) and phi = 0.672. |
| J38 | `04_Results.tex:80`; prod `423` | Phase 1: 71.2% (37/52, CI 57.7-82.7); persistence 95.8% vs 58.0%; $13.1B vs $5.9B | L-P1 (reproduces from phase1 YAML). [L-P1] | All 37 detections persistent_positive; Phase 3 (same Q1 dates) is persistent_negative. |
| J39 | `04_Results.tex:80`; prod `423` | Phase 3: 81.2% (181/223, CI 75.8-86.1), 100% persistent negative | L-P3. [L-P3] |  |
| J40 | `04_Results.tex:80`; prod `423` | 42 windows (18.8%) rejected for Feb-Mar volatility (6-10 flips); "criterion-based discrimination, not base-rate guessing" | L-P3: every one of the 42 rejected windows contains 3-6 of the 10 placeholder rows and none is free of them (verified); with the 10 rows removed the series is all negative, 0 flips, i.e. 223/223 detected. [L-P3] |  |
| J41 | `04_Results.tex:94`; prod `437` | Table 2 shuffle: 2024 61.1% (33/54), 2020 12.1% (27/223) | L-P2 (2024Q1 from L-P1; 2020 from L-P4). [L-P2] |  |
| J42 | `04_Results.tex:95`; prod `438` | Table 2 transitional: 0/32 (2024) and 0/223 (2020) | L-P2. [L-P2] |  |
| J43 | `04_Results.tex:96`; prod `439` | Table 2 low-magnitude: 0/54 (2024) and 0/223 (2020) | L-P2 (x0.25 of ~$14B and ~$2.6B series: cannot reach $5B). [L-P2] |  |
| J44 | `04_Results.tex:101`; prod `444` | 2024 regimes show extreme persistence (96% same-sign); shuffle FP 61% vs 12%; 5x | L-P1/L-P2. [L-P1, L-P2] |  |
| J45 | `04_Results.tex:115`; prod `459` | Table 3 detection 81.2% vs 12.1% (+69.1 pp) | L-P3 / L-P4. [L-P3, L-P4] |  |
| J46 | `04_Results.tex:116`; prod `460` | Table 3 persistence of detected windows: 98.2% (2024) vs 100.0% (2020) | L-P3 / L-P4 YAMLs (reproduces). [L-P3, L-P4] | 2020 = 100% in all 220 windows because the Phase 4 series has no negative values. |
| J47 | `04_Results.tex:117`; prod `461` | Table 3 magnitude detected: $30.5B (2024) vs $5.5B (2020); rejected $31.8B vs $2.2B | L-P3 (30.46 / 31.77) and L-P4 (5.47 / 2.17) YAMLs (reproduce). [L-P3, L-P4] | 2024 here is $30.5B; Table 5 and the fig05 histogram give $20.3B for 2024 (different series). |
| J48 | `04_Results.tex:119`; prod `463` | Table 3 dominant sign Negative (2024) vs Positive (2020), "Flip" | L-P3 (negative by construction) vs L-P4 (sign-stripped). [L-P3, L-P4, L-P5] | Phase 5 2024-25: 486/486 persistent_positive. |
| J49 | `04_Results.tex:125`; prod `470` | Rejected 2024 windows have higher magnitude ($31.8B) than detected ($30.5B): rejection driven by stability | L-P3: rejected windows are the placeholder-containing ones (verified). [L-P3] |  |
| J50 | `04_Results.tex:126`; prod `471` | chi2 = 213.67, Yates 210.90, Fisher p = 1.8e-52, OR 31.3, phi 0.69, risk difference 69.1 pp [62.4, 75.7] | L-P3 / L-P4 counts (arithmetic reproduces). [L-P3, L-P4] |  |
| J51 | `04_Results.tex:135`; prod `481` | fig04_selectivity.png caption: four example windows (2024-Q2, 2024-Q4, Feb 2024, 2020-Q2) with stated persistence/magnitude/flips | fig04_selectivity.png = fig05_selectivity_demo.py: np.random.uniform windows with seed 42 (synthetic). [synthetic/hard-coded] | Caption numbers (e.g. $30B, 55%/8 flips) do not match the plotted panels ($14B, $20B, 50%/8 flips). |
| J52 | `04_Results.tex:141`; prod `491` | Phase 5: 1,412 windows across six years | L-P5. [L-P5] |  |
| J53 | `04_Results.tex:152`; prod `502` | Table 5 2020: 213 windows, 26 detections, 12.2%, avg GEX $3.0B | L-P5 2020 (signed net; Jan series equals today's net on 252/252 days). [L-P5] | Not affected by the call-only break (listed for completeness; see section 9, U01). |
| J54 | `04_Results.tex:155`; prod `505` | Table 5 2023: 46/228 = 20.2%, $9.6B | L-P5. Partly affected: 3/168 before 2023-09-29, 43/60 after. [L-P5] |  |
| J55 | `04_Results.tex:156`; prod `506` | Table 5 2024: 241/241 = 100% (Wilson CI 98.4-100), $20.3B | L-P5 (call-only series). [L-P5] | Replay under today's signed net: 10.3%. |
| J56 | `04_Results.tex:157`; prod `507` | Table 5 2025: 245/245 = 100% (Wilson CI 98.5-100), $19.0B | L-P5 (call-only series). [L-P5] | Replay under today's signed net: 13.6%. |
| J57 | `04_Results.tex:159`; prod `510` | Table 5 total: 646/1,412 = 45.8% (CI 43.2-48.4) | L-P5: 486/646 detections are 2024-25; 529/646 in windows ending on/after 2023-09-29; 13.5% (117/866) on earlier windows. [L-P5] |  |
| J58 | `04_Results.tex:164`; prod `515` | Magnitude $3.0B -> $20.3B (~577%); 2023->2024: chi2 = 314.4, Fisher p = 9.9e-87, phi = 0.82; 486/486 | L-P5. [L-P5] | Arithmetic reproduces (phi 0.819). The "step" is the series break at 2023-09-29 (call-only), not a 2023/2024 boundary. The fig05 PNG title says +585%. |
| J59 | `04_Results.tex:169`; prod `521` | fig05_gex_magnitude_distribution.png caption: 2020 mean $3.0B, 2024 mean $20.3B; $5B threshold in the trough | fig05_gex_magnitude_distribution.png = Phase 4A real data (n=213 / n=241). [L-P5] |  |
| J60 | `04_Results.tex:179`; prod `532` | Threshold sensitivity: re-scored 223 Phase 3 (2024) and 220 Phase 4 (2020) windows, 45 configs | L-P3 / L-P4 YAMLs (phase3_baseline_2024_full_year.yaml, phase4_baseline_2020.yaml). [L-P3, L-P4] | Not Phase 5. |
| J61 | `04_Results.tex:193`; prod `543` | Gap 34.1-85.2 pp (median 63.2); >50 pp in 40 of 45 configurations | L-P3 / L-P4 (jrfm_revision_threshold_sensitivity.yaml). [L-P3, L-P4] | Arithmetic reproduces from the YAMLs; sensitivity is on series with the placeholder rows and sign-stripped 2020. |
| J62 | `04_Results.tex:200`; prod `550` | Persistence threshold has no binding effect; 2020 windows "rarely clear any persistence bar" | L-P3 / L-P4. [L-P3, L-P4] | Contradicted by the Phase 4 YAML: persistence = 100% in every 2020 window (they fail on magnitude only). |
| J63 | `04_Results.tex:209`; prod `559-561` | fig09_threshold_sensitivity.png: 45-cell heatmap of 2024-minus-2020 gap | fig09_threshold_sensitivity.png from threshold_sensitivity.py (L-P3 / L-P4). [L-P3, L-P4] |  |
| J64 | `04_Results.tex:250`; prod `601` | HMM Table: 2020 returns-HMM vs LLM (N=201, LLM 8.5%, HMM 80.1%, kappa 0.045) | HMM rates depend only on SPY returns; LLM labels from L-P4 (Phase 4 YAML). [L-P4] | HMM detection rate 80.1% itself is independent of GEX data. |
| J65 | `04_Results.tex:251`; prod `602` | HMM Table: 2024 returns-HMM vs LLM (N=222, LLM 81.1%, HMM 87.4%, kappa -0.178) | LLM labels from L-P3 (Phase 3 YAML); HMM from SPY returns. [L-P3] |  |
| J66 | `04_Results.tex:252`; prod `603` | HMM Table: GEX-native HMM on 2024 net GEX vs LLM (N=221, agreement 84.2%, kappa 0.610) | HMM fitted on the 242-day Paper 1 CSV (-(call+put); no placeholder rows); LLM labels from the 252-day Phase 3 series (with placeholders). The two detectors saw different series. [L-PAPER1, L-P3] | kappa 0.61 cannot be read as the LLM tracking "dealer-gamma structure": all 42 LLM rejections come from rows the HMM never saw. |
| J67 | `04_Results.tex:260`; prod `613` | fig10_hmm_agreement.png caption: returns-HMM kappa near 0 / negative; GEX-native kappa 0.61 | fig10_hmm_agreement.png from hmm_benchmark.py (Phase 3/4 YAML + SPY returns + Paper 1 CSV). [L-P3, L-P4, L-PAPER1] |  |
| J68 | `04_Results.tex:266`; prod `619` | Text: returns-based HMM detects a different signal; kappa 0.045 / -0.178 | As J64/J65. [L-P3, L-P4] |  |
| J69 | `04_Results.tex:275`; prod `628` | Text: GEX-native HMM kappa 0.610; agreement 84.2% of windows | As J66. [L-PAPER1, L-P3] |  |
| J70 | `04_Results.tex:293`; prod `646` | 98% / 96% / 100% mechanical accuracy; 88% step-by-step (50 sampled detections) | 25 from 2024 (L-P3) + 25 from 2020 (L-P4) per the full-length draft; no audit artifact. [L-P3, L-P4] | Phase 5: 100% label agreement with the deterministic rule on all 1,412 windows. |
| J71 | `04_Results.tex:295`; prod `648` | Confidence: detected 92.8% vs rejected 52.1%; r = +0.719 / -0.705; n = 1,412 | L-P5 (reproduces exactly on all 1,412). [L-P5] | Excluding 2024-25: detected 85.8%, r = +0.511 / -0.477. 486 of 646 detections are 2024-25. |
| J72 | `04_Results.tex:300`; prod `654` | fig06_detection_progression.png caption: step-change in 2024 to 100% detection and $20.3B average GEX, 2025 remains | fig06_detection_progression.png (= AIAI fig08) is the synthetic fallback: bars 27/223, 8/223, 72/223, 45/223, 223/223, 74/74; $4.2B..$22.8B. [L-P5, synthetic/hard-coded] | Caption values ($20.3B, $19.0B) are Phase 5; the plotted values are not. |
| J73 | `05_Discussion.tex:6`; prod `663` | Bridging: 71.5% and 81.2%; raw chain 92.3%; Sharpe 1.8 -> 0.1 | Paper 1 + L-P3. [L-PAPER1, L-RAW13, L-P3] |  |
| J74 | `05_Discussion.tex:10`; prod `667` | 69.1 pp gap; 6.7x separation; 98% mechanical accuracy; confidence r = +0.719 / -0.705 | L-P3/L-P4, manual sample, L-P5. [L-P3, L-P4, L-P5] |  |
| J75 | `05_Discussion.tex:15`; prod `672` | Detection 12.2% (2020), 3.7% (2021), 32.4% (2022), 100% (2024-25); $3.0B -> $20.3B | L-P5. [L-P5] |  |
| J76 | `05_Discussion.tex:17`; prod `675` | Non-monotonic 32.4% -> 20.2% -> 100%; 2023 volatility disrupted regime formation | L-P5; 2023 = 1.8% before 2023-09-29, 71.7% after. [L-P5] |  |
| J77 | `05_Discussion.tex:19`; prod `677` | Detection low through 2023, jumped discontinuously in 2024 (~46% SPY 0DTE share) | L-P5; the jump is the series break at 2023-09-29. [L-P5] |  |
| J78 | `05_Discussion.tex:23`; prod `681` | Raw-chain superiority; 30.8 pp gap is "not a measurement artefact" (Hayek reading) | L-RAW13. [L-RAW13] |  |
| J79 | `05_Discussion.tex:37`; prod `695` | Stable detection 68-74% as Sharpe collapses 1.8 -> 0.1 | Paper 1. [L-PAPER1] |  |
| J80 | `05_Discussion.tex:81`; prod `739` | Practitioner design implication from 92.3% vs 61.5% | L-RAW13. [L-RAW13] |  |
| J81 | `05_Discussion.tex:95`; prod `753` | Practical implication: 2022-2024 regime change requires model recalibration | L-P5. [L-P5] |  |
| J82 | `05_Discussion.tex:131`; prod `791` | Limitation: ground-truth metrics computed from the same Alpha Vantage feed; no external cross-check | All phases; this limitation is the exposure that materialised (series disagree across phases). [L-P1, L-P3, L-P4, L-P5, L-PAPER1] |  |
| J83 | `05_Discussion.tex:160`; prod `820` | Shuffle FP 61% (2024) vs 12.1% (2020) reflects extreme persistence | L-P2 (2024Q1 L-P1 series). [L-P2] |  |
| J84 | `05_Discussion.tex:170`; prod `830` | All tested configurations maintain substantial 2024-vs-2020 discrimination | L-P3 / L-P4 (45 configs). [L-P3, L-P4] |  |
| J85 | `06_Conclusion.tex:17`; prod `856` | Conclusion: 2,221 evaluations 2020-2025 | See J01. [L-P5, L-P2] |  |
| J86 | `06_Conclusion.tex:21`; prod `860` | Conclusion 1: 71.5%, 91.2%, raw chain 92.3% vs 61.5% | Paper 1, L-RAW13. [L-PAPER1, L-RAW13] |  |
| J87 | `06_Conclusion.tex:23`; prod `862` | Conclusion 2: 69.1 pp, CIs, Fisher p, phi 0.69, 0% FP, 98% accuracy, >50 pp in 40 of 45 configs | L-P3/L-P4/L-P2. [L-P3, L-P4, L-P2] |  |
| J88 | `06_Conclusion.tex:25`; prod `864` | Conclusion 3: 1,412 windows; 3.7% -> 100%; $3.0B -> $20.3B | L-P5. [L-P5] |  |
| J89 | `06_Conclusion.tex:27`; prod `866` | Conclusion 4: detection 68-74% quarterly, Sharpe 1.8 -> 0.1 | Paper 1. [L-PAPER1] |  |
| J90 | `07_Appendix_A_Prompts.tex:26`; prod `946` | Appendix: all 2,221 evaluations via Batch API, 100% completion rate | L-P5 batch (1,476 sent; 64 unparseable responses dropped). [L-P5] |  |
| J91 | `07_Appendix_A_Prompts.tex:40`; prod `962` | Completion lengths 2,457-5,924 tokens, none truncated | L-P5 usage: completion_tokens 658-4,125; prompt 1,799; 2,457 and 5,924 are prompt+completion totals. [L-P5] | Mislabelled as completion length; finish_reason = stop for all 1,476. |
| J92 | `07_Appendix_A_Prompts.tex:294`; prod `1217` | Schema-validation failure rate 0% among retained responses | L-P5: 64 of 1,476 responses were dropped before the retained set. [L-P5] |  |


---

## 7. Paper 1 claim inventory (28 anchors; IEEE rows P01-P15, journal rows P16-P28)

File paths are relative to `docs/papers/paper1/`. **Every numeric result in Paper 1 depends on the 2024 sample** (L-PAPER1 or L-RAW13). The rows below are the claims whose dependence on the GEX scalar is direct or whose text disagrees with the stored series; the other Paper 1 lines that carry the same numbers (auto-listed by token search: 71.5, 91.2, 90.9, 92.3, 61.5, 30.8, 242, 69.4, 77.7, 67.4, Sharpe, 68-74, negative-gamma wording, -$32, 19.87) are: **IEEE** `Main.tex`: 26; `01_Introduction.tex`: 5,9; `02_Related_work.tex`: 16; `03_Methodology.tex`: 47,55,71,114,124,131; `04_Experimental_setup.tex`: 6,20,24,30,35,95; `05_Results.tex`: 6,17,18,19,21,26,31,63,70,83,88,96,101,105,127,157,161,171,175,180,182; `06_Discussion.tex`: 3,7,9,11,18; `07_Conclusion.tex`: 5,7,9. **journal** `Regan_ObfuscationTesting.tex`: 34,43,44,45; `01_Introduction.tex`: 5,7,9,11,13; `02_Related_work.tex`: 12,18,29,47; `03_Methodology.tex`: 48,56,72,118,128,135; `04_Experimental_setup.tex`: 6,18,22,28,34,107; `04B_Methodology_Validation.tex`: 41,42,44,49,54,88,99,108,115; `05_Results.tex`: 6,18,19,20,22,27,32,42,75,82,84,86,93,97,111,116,124,129,134,186,190,201,205,210,212,324; `06_Discussion.tex`: 3,7,9,11,19,25,35,52,54,64,72,76,78,80,88; `07_Conclusion.tex`: 5,11,13,15,26,30,39.

| ID | Location | Claim | Depends on | Note |
|---|---|---|---|---|
| P01 | `ieee_bigdata_2025/latex/Main.tex:26` | Abstract: 242 trading days (95.6% coverage); 71.5% unbiased detection; 91.2% accuracy; 100% with regime labels | L-PAPER1: 242-day 2024 series (gamma_positioning_timeseries_2024.csv = -(call+put) ex-0DTE, r = 0.997 with today's raw), three-pattern LLM runs of Oct 2025 (reports/validation/paper1_pattern_taxonomy/*_SPY_2024_unbiased.yaml), forward returns. [L-PAPER1] | Biased prompts add the label NEGATIVE_GAMMA; every day carries it under this series. |
| P02 | `ieee_bigdata_2025/latex/04_Experimental_setup.tex:6` | Coverage: 242 of 253 trading days; ~11 missing days "uniformly distributed across quarters due to a temporary data ingestion issue in Q2" | The 10 absent 2024 dates (2024-02-02, 02-09, 02-16, 02-23, 03-01, 03-08, 03-22, 03-28, 06-04, 06-06) are the 10 placeholder rows of gex_database.db (the same rows that drive Phase 3's 42 rejections). 8 of 10 fall in Q1, 2 in Q2; 2024 had 252 trading days, not 253. [L-PAPER1, L-P3] |  |
| P03 | `ieee_bigdata_2025/latex/04_Experimental_setup.tex:15` | GEX formula: call gamma positive, put gamma negative; dealers short gamma when net GEX negative | The series actually used is the negative of call+put (both negative): Paper 1 prompt YAML shows call_gamma -15.97B and put_gamma -16.52B on 2024-01-02, net -32.49B. [L-PAPER1] |  |
| P04 | `ieee_bigdata_2025/latex/04_Experimental_setup.tex:24` | Pattern 1 criteria: Net GEX < -$2B, spot within 2% of flip, call-gamma concentration > 70% | Criterion 1 holds on all 242 days by construction of the scalar (-$20.7B to -$44.5B). [L-PAPER1] |  |
| P05 | `ieee_bigdata_2025/latex/05_Results.tex:6` | Unbiased average detection 71.5% (CI 68.2-74.8), above 60% threshold | L-PAPER1. [L-PAPER1] |  |
| P06 | `ieee_bigdata_2025/latex/05_Results.tex:17` | Table 1: gamma positioning 69.4% / 100% / 92.5%; stock pinning 67.4% / 90.4%; 0DTE hedging 77.7% / 90.8%; average 71.5% / 91.2% | L-PAPER1. The 0DTE-hedging pattern (highest, 77.7%) was run on a scalar that fits the ex-0DTE gross sum (median error 0.3-2%) rather than the full gross sum (20-22%). [L-PAPER1] |  |
| P07 | `ieee_bigdata_2025/latex/05_Results.tex:39` | Net alpha +21 bps (Q1) -> -1 bp (Q4); Sharpe 1.8 -> 0.1 (elsewhere) | L-PAPER1 detection days x SPY forward returns. [L-PAPER1] | Table 2 prints +16 bps (Q1) and 0 bps (Q4); text prints +21 / -1. |
| P08 | `ieee_bigdata_2025/latex/05_Results.tex:58` | Quarterly table: Q1 53 days 68.2%; Q2 61 / 70.5%; Q3 64 / 72.8%; Q4 64 / 73.6%; full year 242 / 71.5% / 91.2% | L-PAPER1; day counts 53/61/64/64 = the 242-day series (Q1 lacks 8 dates, Q2 lacks 2). [L-PAPER1] | Cochran-Armitage p = 0.42 (JRFM prints p = 0.84). |
| P09 | `ieee_bigdata_2025/latex/05_Results.tex:96` | Funnel: 726 tests -> 519 detections (71.5%) -> 472 materialized (90.9%) -> 65.0% overall | L-PAPER1. [L-PAPER1] | Materialization rates in Table 3 (89.2 / 85.7 / 93.4 / 91.1; overall 91.2%) were corrected in arXiv v2 / journal draft to 41.6% (C1 U C4), Issue #187. |
| P10 | `ieee_bigdata_2025/latex/05_Results.tex:145` | Granger GEX -> realized volatility: lag 2 F = 3.22, p = 0.042 (significant); other lags not | Paper 1 2024 series (first-differenced -(call+put) scalar) and realized volatility. granger_robustness_results.csv lists six specifications: four marked SIGNIFICANT (three are the same differenced-GEX vs level-volatility model at maxlag 3/5/10, min p 0.042; one both-differenced, p 0.021) and two NULL (both levels p 0.137; percentage changes p 0.232). [L-PAPER1] | reports/statistical_validation/statistical_validation_summary.md (Oct 29 2025) lists the Granger table as a null result and recommends not including it. |
| P11 | `ieee_bigdata_2025/latex/05_Results.tex:157` | Within-regime Pearson r = -0.01 between GEX magnitude and volatility ("threshold effect") | Paper 1 2024 series. [L-PAPER1] |  |
| P12 | `ieee_bigdata_2025/latex/05_Results.tex:161` | All 242 days negative (< -$2B); mean -$19.87B (range -$40.69B to -$4.75B); Table: 242 / 0 / 0 | Negative on every day because the scalar is -(call+put). Stored 242-day series: mean -$31.35B, range -$44.49B to -$20.66B (the -$19.87B / -$40.69B / -$4.75B figures are not reproducible from it). Today's signed net on the same dates: 93 negative days, 75 below -$2B, mean +$1.26B. [L-PAPER1] | This is the "persistent negative gamma regime driven by 0DTE" claim (also IEEE 05_Results.tex:180,182; 06_Discussion.tex:3,15; 07_Conclusion.tex:9). |
| P13 | `ieee_bigdata_2025/latex/05_Results.tex:180` | Structural shift: persistent negative gamma regime driven by 0DTE growth; single-regime environment | L-PAPER1 (same series). [L-PAPER1] |  |
| P14 | `ieee_bigdata_2025/latex/06_Discussion.tex:3` | Discussion: dealers structurally short gamma in 2024; detection 69.4%; Granger p = 0.042; 91.2% materialization | L-PAPER1. [L-PAPER1] |  |
| P15 | `ieee_bigdata_2025/latex/07_Conclusion.tex:9` | Conclusion: structural market regime shift - all 242 days negative gamma; Granger p = 0.042 at lag 2 | L-PAPER1. [L-PAPER1] |  |
| P16 | `journal_version/Regan_ObfuscationTesting.tex:34` | Abstract: raw chain 92.3%, +30.8 pp over pre-calculated Net GEX; 242 days; 91.2%; 68-74% stable; 33% lower range expansion | L-RAW13 (13 dates) and L-PAPER1. [L-RAW13, L-PAPER1] | Abstract still quotes 91.2% while the Results table in the same draft (05_Results.tex:149-154) shows 41.6%. |
| P17 | `journal_version/04B_Methodology_Validation.tex:24` | Raw chain: 13 dates (Q1-Q2 2024) where raw chains exist in the database; o4-mini; baseline = same 13 dates with GEX | 13 dates: 2024-01-02, 01-09, 01-17, 01-18, 01-19, 03-05, 03-06, 03-13, 03-15, 06-05, 06-07, 06-21, 06-28 (reports/validation/paper1_raw_chain/). Baseline arm scalar -$25.1B to -$38.8B (L-PAPER1 series); today's signed net on these dates: negative on 7, below -$2B on 5, range -15.4 to +14.9B. [L-RAW13] |  |
| P18 | `journal_version/04B_Methodology_Validation.tex:41` | Raw chain 92.3% (12/13) vs baseline 61.5% (8/13); +30.8 pp; confidence 71.2 vs 77.5 | L-RAW13. [L-RAW13] | Baseline 5 misses (confidence 0) on 2024-01-09, 06-05, 06-07, 06-21, 06-28; raw-chain miss on 2024-01-02 (confidence 55). |
| P19 | `journal_version/04B_Methodology_Validation.tex:99` | GEX-assisted prompt = single number (-$32.5B); "lossy compression" interpretation | The single number is the -(call+put) scalar (not a signed net). [L-RAW13] |  |
| P20 | `journal_version/05_Results.tex:70` | Quarterly detection/accuracy/alpha table (journal) | L-PAPER1. [L-PAPER1] |  |
| P21 | `journal_version/05_Results.tex:93` | Obfuscated prompt example: Net GEX -$32.9B, Flip $485.00 | Illustrative; scale = L-PAPER1 scalar. [synthetic/hard-coded] |  |
| P22 | `journal_version/05_Results.tex:149` | Materialization table (corrected): C1 41.6%, C2 N/A, C3 N/A, C4 21.6%, overall 41.6% | L-PAPER1 detection days (519) x 2024 forward returns. [L-PAPER1] | Conflicts with 91.2% / 90.9% quoted in the same draft (abstract, 03_Methodology.tex:72, 05_Results.tex:124, 06_Discussion.tex:3,9,52-54, 07_Conclusion.tex:13). |
| P23 | `journal_version/05_Results.tex:190` | Regime table: all 242 days negative; mean -$19.87B | As P12. [L-PAPER1] |  |
| P24 | `journal_version/05_Results.tex:242` | Non-detection analysis: GEX magnitude 31.8 (detect) vs 30.3 (non-detect); Gini -0.853 vs -0.866 (d = 0.68) | L-PAPER1 series (reproduces from the CSV: 31.83 vs 30.26). [L-PAPER1] | Contradicts 07_Conclusion.tex:22 ("3.72x lower mean GEX magnitude, $5.4B vs $20.1B") and the -$19.87B mean. |
| P25 | `journal_version/05_Results.tex:270` | Inverse p-hacking: range expansion 21.6% vs 32.0% (lift 0.67, p = 0.03); chi2 = 4.53 | L-PAPER1 detection days and 2024 intraday ranges. [L-PAPER1] |  |
| P26 | `journal_version/05_Results.tex:315` | EOD logistic baseline AUC = 0.681 (167 detection days; gex_oi p = 0.0075); LLM confidence AUC 0.488 | L-PAPER1 features (total_gex, gex_oi, ...) x T+1 outcomes. [L-PAPER1] |  |
| P27 | `journal_version/06_Discussion.tex:19` | Single-regime environment: all 242 days negative gamma; no regime-transition analysis | L-PAPER1. [L-PAPER1] |  |
| P28 | `journal_version/07_Conclusion.tex:22` | Sensitivity defense: non-detection days 3.72x lower GEX magnitude ($5.4B vs $20.1B) | Not reproducible from the stored 2024 series (31.8 vs 30.3 $B). [L-PAPER1] |  |


Paper 1 claims that do **not** need the GEX scalar: the WHO-WHOM-WHAT framework definition, the three validation-level thresholds (60% / 80% / 90%), the obfuscation protocol as a procedure, and the SPY price, forward-return and realized-volatility inputs. Their *use* (which days count as detections) does depend on it.

---

## 8. Figures

LaTeX numbering is by order of appearance. **Pixel identity [V]:** the images embedded in the compiled `Regan_Xie_AIAI.pdf` (p.4,7,8,9,11) and `Regan_Xie_JRFM.pdf` (p.8,12,14,15,16,17,18) are pixel-identical to the repo PNGs named below; the obfuscation figure in both PDFs is an earlier render than the current PNG (regenerated 2026-05-30). The MDPI production PDF is not in the repo; the production commit `369bec9` changed only `fig01_obfuscation.png` / `fig03_obfuscation.png` (`git show --stat 369bec9`), so the other JRFM figures in production are the files named below.

| Paper / Fig. | File (under `docs/papers/paper2/figures/output/` unless noted) | Anchor | Data source | Depends on 2024-25 GEX / detection? |
|---|---|---|---|---|
| AIAI 1 | `fig01_architecture.png` | `03_Methodology.tex:8` | conceptual | No |
| AIAI 2 / JRFM 1 | `fig03_obfuscation.png` (JRFM: `jrfm/figures/fig01_obfuscation.png`) | AIAI `03:37`; JRFM `03:10` | conceptual; example row 2024-03-15, GEX -$12.3B, persistence 93%, 2 flips | Illustrative only; -$12.3B matches no stored series (Paper 1 -29.29B, Phase 3 -29.84B, January +14.61B, signed net -15.35B) |
| AIAI 3 / JRFM 3 | `fig04_validation_pipeline.png` (JRFM `fig03_validation_pipeline.png`) | AIAI `04_Results.tex:8`; JRFM `04_Results.tex:73` | hard-coded in `fig04_validation_pipeline.py`: 71.2% (n=52), "Negative Control, Shuffled" 6.3% (n=52), 81.2% (n=223), 12.1% (n=223), "phi = 0.672" | Yes: L-P1..L-P4 values. 6.3% is not reproducible (shuffle-2024 61.1%; pooled controls 60/809 = 7.4%); phi recomputes to 0.692; JRFM caption promises bootstrap-CI boxes and Phase 5 that the PNG lacks |
| AIAI 4 / JRFM 4 | `fig05_selectivity.png` (JRFM `fig04_selectivity.png`) | AIAI `04:63`; JRFM `04:134` | synthetic: `np.random.uniform`, seed 42, in `fig05_selectivity_demo.py` | No data; JRFM caption describes four specific windows (2024-Q2 "$30B, 3 flips", 2024-Q4 "$25B", Feb 2024 "55% / 8 flips", 2020-Q2 "$2.8B") that do not match the plotted panels (~$14B, ~$20B, 50% / 8 flips, ~$3B) |
| AIAI 5 / JRFM 5 | `fig06_gex_magnitude_distribution.png` (JRFM `fig05_gex_magnitude_distribution.png`) | AIAI `04:97`; JRFM `04:168` | `.cache/research_cache.db` (Phase 4A): n = 213 (2020, mean $3.0B), n = 241 (2024, mean $20.3B); PNG title says +585% | **Yes, L-P5**: 2024 histogram is the call-only series |
| AIAI 6 / JRFM 8 | `fig08_detection_progression.png` (JRFM `fig06_detection_progression.png`) | AIAI `05_Discussion.tex:22`; JRFM `04_Results.tex:299` | **synthetic fallback** `generate_synthetic_data()`: 27/223, 8/223, 72/223, 45/223, 223/223, 74/74; $4.2B, $5.1B, $8.7B, $12.3B, $18.5B, $22.8B; footer and panel title hard-coded "360% ($5B to $23B)" | The plotted values are not Phase 5. The script's own query returns 213/26, 241/9, 244/79, 228/46, 241/241, 245/245 and $3.0B..$19.0B; the published PNG predates or bypassed it |
| JRFM 2 | `fig02_regime_window.png` | JRFM `03_Methodology.tex:80` | synthetic by construction: `create_figure()` ignores the database result and calls `generate_synthetic_example()` | No data; caption does not say it is illustrative |
| JRFM 6 | `fig09_threshold_sensitivity.png` | JRFM `04:208` | `threshold_sensitivity.py` on `phase3_baseline_2024_full_year.yaml` + `phase4_baseline_2020.yaml` | Yes: L-P3 (2024), L-P4 (2020) |
| JRFM 7 | `fig10_hmm_agreement.png` | JRFM `04:259` | `hmm_benchmark.py`: Phase 3/4 YAML labels, SPY returns, Paper 1 CSV | Yes: L-P3, L-P4, L-PAPER1 (the returns-HMM bars depend only on SPY returns) |

Paper 1 figures (all depend on the 2024 sample). IEEE, by order of appearance: Fig. 1 `fig1_obfuscation_example.png` (conceptual, `03_Methodology.tex:22`); Fig. 2 `fig2_gex_profile.png` (net GEX -$32.5B = first detection day of the L-PAPER1 series, strike distribution synthetic, `04_Experimental_setup.tex:34`); Fig. 3 `fig3_validation_pipeline.png` (conceptual); Fig. 4 `fig8_performance_matrix.png` (`05_Results.tex:30`); Fig. 5 `fig5_quarterly_stability.png` (`:43`); Fig. 6 `fig7_confidence_distribution.png` (`:78`); Fig. 7 `fig6_validation_funnel.png` (`:100`). Journal draft (`docs/papers/paper1/figures/`): `fig01_obfuscation_example.png`, `fig02_gex_profile.png`, `fig03_validation_pipeline.png`, `fig04_raw_chain.png` (L-RAW13), `fig05_performance_matrix.png`, `fig06_bias_comparison.png`, `fig07_quarterly_stability.png`, `fig08_confidence_distribution.png`, `fig09_validation_funnel.png`, `fig10_gex_concentration.png`, `fig11_detection_calendar.png`, `fig12_inverse_phacking.png`.

Figures in the full-length Paper 2 draft (`docs/papers/paper2/latex/`, `jfqa/`) but not in AIAI or JRFM, all reading `.cache/research_cache.db` (Phase 4A) or hard-coded values: `fig07_confidence_discrimination.png`, `fig09_scar_tissue.png`, `fig10_borderline_persistence.png`, `fig11_threshold_sensitivity.png`, `fig12_overnight_intraday_divergence.png`.

---

## 9. Claims that do NOT depend on 2024-2025 data

| ID | Claim | Where | Why it is independent (and any caveat) |
|---|---|---|---|
| U01 | Phase 5 2020 row: 213 windows, 26 detected, 12.2%, avg GEX $3.0B | AIAI `04_Results.tex:81`; JRFM `04_Results.tex:152` | January extract equals signed net on 252/252 days of 2020; replay 12.1%; window-level agreement 100% in all four quarters [V][D] |
| U02 | Phase 5 2021 row: 241 / 9 / 3.7%, $4.9B | AIAI `:82`; JRFM `:153` | 250/252 days equal; agreement 98.4-100%; replay 4.0% vs 3.6% [V][D] |
| U03 | Phase 5 2022 row: 244 / 79 / 32.4%, $5.5B | AIAI `:83`; JRFM `:154` | 247/251 days equal; agreement 84-100% by quarter; replay 32.3% (January) vs 40.6% (signed net). Approximately unaffected; the 3 call-only days move some windows. All 79 detections are `persistent_negative`, unlike 2020, 2021, 2023-Q4 and 2024-25 [V] |
| U04 | Phase 4 2020 detection (12.1%) and the 2020 Phase 2 controls (0/223, 27/223) | AIAI Tables 2-3; JRFM Tables 2-3 | Contain no 2024-25 value. Not independent of the sign-stripping in L-P4 |
| U05 | Criteria and procedure: persistence >= 70%, mean |GEX| >= $5B, flips <= 5; regime taxonomy; prompt text and output schema; o4-mini snapshot; Batch API; "2.2 sigma" (z = (21-15)/sqrt(7.5) = 2.19) | AIAI `03_Methodology.tex:15-19`; JRFM `03:54-76`, `07_Appendix_A_Prompts.tex` | Definitions, not data. The $5B level's meaning depends on which GEX convention is used |
| U06 | 0DTE share statistics (about 48% of volume in 2024; <5% in 2020; JRFM: about 46% SPY, 59% SPX 2025, 43% SPX 2023) | AIAI `02_Related_work.tex:14`; JRFM `01_Introduction.tex:12`, `02:14` | External sources (Cboe, Dim et al., Adams et al.), not computed from GEX |
| U07 | Returns-based Markov-switching detection rates 80.1% (2020) and 87.4% (2024) | JRFM `04_Results.tex:250-251` | Depend only on SPY returns. The kappa values and LLM rates beside them do depend on L-P3/L-P4 labels |
| U08 | Test arithmetic given the stated counts (chi2, Yates, Fisher, odds ratio, risk difference, Wilson, bootstrap procedure) | JRFM `04_Results.tex:56-67,126-129,164` | Reproduces [V]; the counts it is applied to are not independent |
| U09 | Related work, positioning, limitations text (single asset, single LLM, end-of-day measurement, causal attribution) | AIAI `02`, `05:37-49`; JRFM `02`, `05:102-177` | Qualitative. The JRFM limitation "lack of independent external validation" (`05_Discussion.tex:131`) is the exposure that materialised |
| U10 | Batch mechanics: 1,476 windows sent, o4-mini, 50% batch discount, $11.07 | JRFM `03_Methodology.tex:125`; `07_Appendix_A_Prompts.tex:26` | Cost and protocol, not GEX values. Notes: $11.07 is the Phase 4A batch only; AIAI `03:46` states temperature = 1.0 and max tokens = 16,384 but the request bodies contain only `model` and `messages` (JRFM corrected this) |
| U11 | Paper 1 definitions: WHO-WHOM-WHAT, validation levels 60/80/90%, obfuscation protocol, market inputs (SPY returns, realized volatility) | Paper 1 `03_Methodology.tex` | Procedure and market data; see section 7 for the dependent use |

---

## 10. Other findings made while tracing (not requested; included because they bear on the same claims)

1. **Calendar dates in the Phase 3 and Phase 4 prompts [V].** `phase3_full_2024_baseline_v2.jsonl` and `batch_regime_20251120_104630.jsonl` contain lines such as `2024-05-24: -30.67B` in all 223 + 223 windows; no `Day T-k` label and no ticker. Batch metadata links these files to the Phase 3 and Phase 4 batch IDs in the result YAMLs, and one Phase 3 response quotes "2024-06-04". The methodology sections (AIAI `03:33`; JRFM `03:6`) state that dates become relative labels, and the papers present the 81.2% vs 12.1% contrast as detection under temporal obfuscation. Phases 1, 2 and 5 do use `Day T-k`. [S] I did not locate the code path that produced the dated files.
2. **Sign contradictions inside the papers [V].** Phase 1 (Q1 2024) detections are all `persistent_positive`; Phase 3 (full 2024, same Q1 dates) are all `persistent_negative`; Phase 5 2024 is 241/241 `persistent_positive`. AIAI Table 3 and JRFM Table 3 print "Dominant sign: Negative (2024) vs Positive (2020), Flip"; the JRFM `fig04_selectivity.png` caption and Discussion (`05_Discussion.tex:43-57`) describe 2024 as a persistent negative regime; Paper 1 states all 242 days negative. Phase 5's 2022 detections are negative (79/79) and 2020, 2021, 2023-Q4, 2024, 2025 are positive; the Phase 5 narrative does not mention sign.
3. **AIAI and JRFM disagree on numbers that can be recomputed [V]; the JRFM values reproduce and the AIAI values do not:** phi 0.672 vs 0.69 (0.692); phi 0.783 vs 0.82 (0.819); confidence r +0.501 / -0.549 vs +0.719 / -0.705 (Phase 5 gives the latter); Phase 1 persistence/magnitude 96.0 / 57.0 and $11.66B / $4.82B vs 95.8 / 58.0 and $13.1B / $5.9B (YAML gives the latter); Phase 2 control sizes 404 / 202 / 203 vs 277 / 255 / 277 (YAMLs give the latter); "5.7x" vs "6.7x" (81.2/12.1 = 6.7); Table 4 average GEX $5B / $5B / $8-12B / $10-15B / $23B / $23B vs 3.0 / 4.9 / 5.5 / 9.6 / 20.3 / 19.0. AIAI Table 3's 2024 persistence (96.0%) and magnitude ($13.95B) match neither Phase 3 ($30.5B detected, 98.2%) nor Phase 5 ($20.3B).
4. **Bookkeeping.** "2,221 evaluations = 1,412 + 809" omits the 498 real-window evaluations of Phases 1, 3 and 4 (which are separate LLM calls on separate series) and counts parsed windows only (64 of 1,476 dropped). JRFM Appendix `07:40` reports "completion lengths 2,457 to 5,924 tokens"; the stored usage shows completion tokens 658-4,125 and a constant prompt of 1,799 tokens, so those are prompt+completion totals.
5. **HMM benchmark [V].** `hmm_benchmark.py` fits the GEX-native HMM on the 242-day Paper 1 CSV, while the LLM labels it is compared with were generated on the 252-day series that includes the placeholder rows. All 42 rejections arise from rows the HMM never saw, so kappa = 0.61 is not evidence that both detectors track the same dealer-gamma structure. [S] why the two nevertheless agree on 84% of windows was not investigated.
6. **Paper 1 internal inconsistencies [V].** Mean GEX -$19.87B vs stored -$31.35B; "3.72x lower GEX magnitude ($5.4B vs $20.1B)" (journal `07_Conclusion.tex:22`) vs Table 18 (`05_Results.tex:242`, 31.8 vs 30.3); Granger table significant at lag 2 while `statistical_validation_summary.md` (2025-10-29) reports all p > 0.3 and recommends omitting it, and `granger_robustness_results.csv` lists two NULL specifications of six; quarterly p = 0.42 (Paper 1) vs 0.84 (JRFM); 2024 had 252 trading days, not 253; the 10 absent dates are 8 in Q1 and 2 in Q2 (not "uniformly distributed ... Q2 ingestion issue"); 91.2% vs 41.6% materialization (Issue #187, known).

---

## 11. Evidence log

Scripts (all read-only, in `forensics2/f3/`): `f3_recon_series.py`, `f3_t0_compare.py`, `f3_parse_4a.py`, `f3_replay.py`, `f3_mech_accuracy.py`, `f3_evidence.py` (consolidates everything below), `f3_validate_entries.py`, `f3_build_inventory.py`. Run with `source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex && python f3_evidence.py`. Inputs produced elsewhere and reused read-only: `forensics2/raw_daily_today.json` (per-day call/put, same-day/forward-dated decomposition of today's raw table with the January script's formula and filters, written by a sibling forensics task) and `forensics2/f3/f3_phase4a_parsed.pkl`, `f3_replay_*.csv` (written by `f3_parse_4a.py` and `f3_replay.py`). PostgreSQL use: one SELECT of 10 SPY `underlying_price` averages (partition-pruned, `statement_timeout 300s`). SQLite files opened with `mode=ro`.

```text

====================================================================================================
1. PROMPT LABELS IN EACH SURVIVING INPUT FILE (dated vs Day T-k)
====================================================================================================
Phase 1 (Q1 2024) batch_regime_20251106_184057.jsonl           windows=   54 dated_prompts=    0  first label='Day T-29'  last label='Day T+0'
Phase 2 shuffle 2024Q1 batch_regime_20251119_221706.jsonl      windows=   54 dated_prompts=    0  first label='Day T-29'  last label='Day T+0'
Phase 2 shuffle 2020 batch_regime_20251119_230659.jsonl        windows=  223 dated_prompts=    0  first label='Day T-29'  last label='Day T+0'
Phase 3 (2024) phase3_full_2024_baseline_v2.jsonl              windows=  223 dated_prompts=  223  first label='2024-01-02'  last label='2024-02-13'
Phase 4 (2020) batch_regime_20251120_104630.jsonl              windows=  223 dated_prompts=  223  first label='2020-01-02'  last label='2020-02-13'
Phase 5/4A phase4a_postgresql_20260104_184832.jsonl            windows= 1476 dated_prompts=    0  first label='Day T-29'  last label='Day T+0'
Phase 3 responses that quote a calendar date in their reasoning: [('window-2024-06-05', [' 2 sign flips (one neg→pos on 2024-06-04 and pos→neg on 2024'])]
batch metadata: batch_691ea7f7... -> phase3_full_2024_baseline_v2.jsonl ; batch_691f37d9... -> batch_regime_20251120_104630.jsonl (see batch_jobs/*_metadata.json)

====================================================================================================
2. PHASE 3 (2024) SERIES == .cache/gex_database.db daily_gex_metrics.total_gex
====================================================================================================
rows in gex_database.db: 252 | rows equal to Phase 3 series within 0.0051B: 252 | created_at 2025-10-11 .. 2025-11-03
rows with net_call_gex<0 and net_put_gex<0: 242 | rows with total_gex>0: 10
            total_gex  net_call_gex  net_put_gex  spot_price  options_count  spy_underlying_today  spot_gap_pct
date                                                                                                           
2024-02-02      12.31           0.0          0.0      461.00            NaN                494.35          -6.7
2024-02-09      13.07           0.0          0.0      467.00            NaN                501.20          -6.8
2024-02-16      13.07           0.0          0.0      469.00            NaN                499.51          -6.1
2024-02-23      13.29           0.0          0.0      470.00            NaN                507.85          -7.5
2024-03-01      10.61           0.0          0.0      477.00            NaN                512.85          -7.0
2024-03-08      13.76           0.0          0.0      478.00            NaN                511.72          -6.6
2024-03-22      12.36           0.0          0.0      482.75            NaN                521.21          -7.4
2024-03-28      11.36           0.0          0.0      487.00            NaN                523.07          -6.9
2024-06-04      12.49           0.0          0.0      491.00            NaN                528.39          -7.1
2024-06-06      12.33           0.0          0.0      495.00            NaN                534.66          -7.4
dates in gex_database.db but absent from Paper 1 242-day CSV: ['2024-02-02', '2024-02-09', '2024-02-16', '2024-02-23', '2024-03-01', '2024-03-08', '2024-03-22', '2024-03-28', '2024-06-04', '2024-06-06']
placeholder dates by quarter: Counter({1: 8, 2: 2})

====================================================================================================
3. PHASE 3 REJECTIONS vs PLACEHOLDER ROWS
====================================================================================================
LLM label == deterministic rule on the numbers sent: 223 of 223
       count  min  max
llm                   
False     42    3    6
True     181    0    3
windows with >=3 placeholders: 44 | of which rejected 42 | rejected windows with zero placeholders: 0
with the 10 rows removed the 242-day series is negative every day (min |x|, max x): 20.83 -20.83 => every 30-day window: persistence 100%, flips 0, magnitude >= $20B => 223/223 detected

====================================================================================================
4. WHICH FORMULA REPRODUCES EACH 2024 SERIES? (fit to today's raw table; 0DTE = expiration == trading_date)
====================================================================================================
Phase 3 series (252 rows): n=252; best candidate within 5%: {'gross_neg_ex0': 242, 'net_full': 1}
   median relative error: {'net_full': 1.064, 'net_ex0': 1.023, 'gross_neg_ex0': 0.003, 'gross_neg_full': 0.199, 'callonly': 1.636}
Paper 1 CSV (242 rows): n=242; best candidate within 5%: {'gross_neg_ex0': 241}
   median relative error: {'net_full': 1.074, 'net_ex0': 1.034, 'gross_neg_ex0': 0.02, 'gross_neg_full': 0.222, 'callonly': 1.655}
corr(Paper 1 CSV, gross_neg_ex0) = 0.9974 ; ratio median 0.980 (min 0.945 max 1.015)
   paper1    mean  -31.35 median  -30.68 min  -44.49 max  -20.66 negative days 242 below -2B 242 above +2B 0
   net_full  mean    1.26 median    2.48 min  -18.36 max   18.13 negative days 93 below -2B 75 above +2B 125
   net_ex0   mean    0.36 median    1.07 min  -12.45 max   12.27 negative days 101 below -2B 73 above +2B 104
Paper 1 text: mean -$19.87B, range -$40.69B..-$4.75B (not the stored CSV).

====================================================================================================
5. PHASE 4 (2020) SERIES
====================================================================================================
days 252 | negative values: 0 | min/max 0.01 11.23
today signed net 2020: negative on 93 of 252 days; Jan series negative on 93
corr(Phase 4, |gex_oi| consolidated_historical.db) = 0.996 ; corr(Phase 4, |total_gex|) = 0.621 ; consolidated 2020 total_gex mean -17.2B (negative on 250 days)
2020 Phase 2 shuffle: windows built from the Phase 4 window: 223/223
2020 Phase 2 transitional: windows built from the Phase 4 window: 223/223
2020 Phase 2 low-magnitude: windows built from the Phase 4 window: 223/223

====================================================================================================
5b. PHASE 2 CONTROL CONSTRUCTION (from the stored inputs)
====================================================================================================
2020 transitional: days with sign flipped vs the Phase 4 window -> {7: 64, 8: 61, 9: 40, 10: 58}
2024Q1 transitional: days with sign flipped vs the Phase 1 window -> {7: 8, 8: 14, 9: 4, 10: 6} ( 32 windows )
2024Q1 low-magnitude == 0.25 x Phase 1 window: 54 of 54

====================================================================================================
6. PHASE 1 (Q1 2024) SERIES
====================================================================================================
Phase 1 window-end values equal to file-cache gex_summary.json total_gex: 53 of 54 (the non-match is the 2024-01-15 "mini" cache file; 2024-01-15 was an exchange holiday)
cache 2024-01-02: {'spot_price': 434.0, 'total_gex': 10012842994.247683, 'call_gex': -5139425662.129274, 'put_gex': 15152268656.376957, 'net_gex': 10012842994.247683}  vs today signed net -0.48B, gross 39.7B, SPY close 472.65
same 53 dates: sign(Phase 1) != sign(Phase 3) on 53; means: Phase 1 14.18, Phase 3 -34.85, Jan series 22.50
Phase 1 YAML regime types: Counter({'persistent_positive': 37, 'transitional': 15})

====================================================================================================
7. JANUARY (PHASE 4A) SERIES vs TODAY'S RAW TABLE
====================================================================================================
      days  equal_signed_full_net  equal_call_only
y                                                 
2020   252                    252                0
2021   252                    250                2
2022   251                    247                3
2023   249                    151               98
2024   251                      0              251
2025   250                      0              250
last day equal to signed full net but not call-only: 2023-09-28 | days after: 565 | all call-only and none equal full net: True
Jan calendar lacks 2023-07-12 and 2024-03-11 (present in today's raw table).

====================================================================================================
8. PHASE 5 / PHASE 4A RESULTS (raw o4-mini output, 2026-01-04 batch)
====================================================================================================
responses 1,476 | parsed 1412 | unparsed 64 (by year {'2020': 10, '2021': 11, '2022': 7, '2023': 21, '2024': 10, '2025': 5})
      windows  detected  mean_abs_gex_bn  rate_pct
year                                              
2020      213        26             2.97      12.2
2021      241         9             4.88       3.7
2022      244        79             5.52      32.4
2023      228        46             9.58      20.2
2024      241       241            20.35     100.0
2025      245       245            18.97     100.0
regime_type  low_conviction  persistent_negative  persistent_positive  transitional
year                                                                               
2020                     94                    0                   26            93
2021                     82                    0                    9           150
2022                     32                   79                    0           133
2023                     12                    3                   43           170
2024                      0                    0                  241             0
2025                      0                    0                  245             0
2024-25: positive_days==30 in 486 of 486 | sign_flips==0 in 486
windows ending >= 2023-09-29: 546 of 1412 (38.7%), detections 529 of 646 (81.9%); windows ending earlier: 866, detections 117, rate 13.5%
2023: before 2023-09-29 3/168 (1.8%); on/after 43/60 (71.7%)
2024-25 detections = 486 of 646 (75.2%)
LLM label == deterministic rule on numbers sent: 1412/1412 ; persistence within 2pp 1410 ; magnitude within $0.5B 1411 ; flips exact 1412

====================================================================================================
9. DETERMINISTIC REPLAY OF THE PAPER CRITERIA (persistence>=21/30 same sign, mean|GEX|>=5, flips<=5) ON EACH CONVENTION (diagnostic, today's raw table)
====================================================================================================
,2020,2021,2022,2023,2024,2025
Jan-2026 extract (published input),12.1,4.0,32.3,19.3,100.0,100.0
"today signed net, 0DTE incl.",12.1,3.6,40.6,22.4,10.3,13.6
"today signed net, ex-0DTE",2.7,0.0,36.7,25.2,13.1,16.4
"today call-only, 0DTE incl.",90.6,100.0,100.0,100.0,100.0,100.0
today -(call+put) ex-0DTE [Nov-2025 convention],100.0,100.0,100.0,100.0,100.0,100.0
today |net| [sign stripped],13.9,47.2,70.1,62.0,97.6,96.4

end,end,n,agree,det_jan,det_new
2020,1,33,100.0,24.2,24.2
2020,2,62,100.0,0.0,0.0
2020,3,64,100.0,0.0,0.0
2020,4,64,100.0,29.7,29.7
2021,1,61,100.0,8.2,8.2
2021,2,63,100.0,0.0,0.0
2021,3,64,98.4,4.7,3.1
2021,4,64,100.0,3.1,3.1
2022,1,62,100.0,19.4,19.4
2022,2,62,93.5,62.9,69.4
2022,3,64,89.1,15.6,26.6
2022,4,63,84.1,31.7,47.6
2023,1,62,93.5,3.2,9.7
2023,2,62,90.3,1.6,11.3
2023,3,62,77.4,0.0,22.6
2023,4,63,68.3,71.4,46.0
2024,1,60,6.7,100.0,6.7
2024,2,63,14.3,100.0,14.3
2024,3,64,0.0,100.0,0.0
2024,4,64,20.3,100.0,20.3
2025,1,60,18.3,100.0,18.3
2025,2,62,32.3,100.0,32.3
2025,3,64,0.0,100.0,0.0
2025,4,64,4.7,100.0,4.7


====================================================================================================
10. TEST STATISTICS RECOMPUTED FROM THE STATED COUNTS
====================================================================================================
Phase 3 2024 181/223 vs Phase 4 2020 27/223: chi2=213.67 p=2.18e-48; Yates=210.90 p=8.74e-48; Fisher p=1.82e-52; OR=31.3; phi=0.692; RD=69.1pp [62.4,75.7]
Phase 5 2024 241/241 vs 2023 46/228: chi2=314.37 p=2.44e-70; Yates=311.02 p=1.31e-69; Fisher p=9.88e-87; OR=inf; phi=0.819; RD=79.8pp [74.6,85.0]
corr(confidence,persistence_pct) all 1,412: +0.719 ; 2020-2023 only: +0.511
corr(confidence,sign_flips) all 1,412: -0.705 ; 2020-2023 only: -0.477
mean confidence detected 92.8 rejected 52.1 ; excluding 2024-25: detected 85.8 rejected 52.1
AIAI 25-grid (P x M, flips<=5) on Phase 5: min gap 72.8 max 100.0 pp
JRFM 45-config sweep on Phase 3/4 YAMLs: gap min 34.14 max 85.20 median 63.23; >50pp in 40

====================================================================================================
11. PAPER 1 RAW-CHAIN TEST (13 dates)
====================================================================================================
      date  raw_det  raw_conf  base_det  base_conf  base_gex_shown  today_signed_net  today_gross_neg_ex0
2024-01-02    False        55      True         80          -32.49             -0.48               -32.82
2024-01-09     True        85     False          0          -35.61              3.49               -36.09
2024-01-17     True        75      True         80          -38.83             -9.63               -39.40
2024-01-18     True        70      True         80          -38.32              5.43               -38.72
2024-01-19     True        60      True         80          -25.13             14.88               -25.55
2024-03-05     True        75      True         80          -37.61             -8.03               -38.12
2024-03-06     True        65      True         80          -36.22              4.72               -37.10
2024-03-13     True        75      True         80          -37.79             -0.58               -38.45
2024-03-15     True        70      True         85          -29.29            -15.35               -29.80
2024-06-05     True        80     False          0          -27.84              6.84               -27.99
2024-06-07     True        65     False          0          -28.73              2.87               -29.01
2024-06-21     True        75     False          0          -26.66             -5.20               -27.40
2024-06-28     True        70     False          0          -25.49             -7.82               -26.10
raw detected 12 /13; baseline detected 8 /13; today signed net negative on 7 dates, below -2B on 5
baseline prompt on 2024-01-02 (Paper 1 YAML): call_gamma -15.97B put_gamma -16.52B net -32.49B

====================================================================================================
12. FIGURE DATA SOURCES
====================================================================================================
fig08 script query against research_cache.db returns:
   ('2020', 213, 26, 12.2, 3.0)
   ('2021', 241, 9, 3.7, 4.9)
   ('2022', 244, 79, 32.4, 5.5)
   ('2023', 228, 46, 20.2, 9.6)
   ('2024', 241, 241, 100.0, 20.3)
   ('2025', 245, 245, 100.0, 19.0)
fig08 PNG as published shows (hard-coded generate_synthetic_data()): 2020 27/223 12.1% $4.2B | 2021 8/223 3.6% $5.1B | 2022 72/223 32.3% $8.7B | 2023 45/223 20.2% $12.3B | 2024 223/223 100% $18.5B | 2025 74/74 100% $22.8B
fig06 PNG shows n=213 (2020, mean $3.0B) and n=241 (2024, mean $20.3B) = Phase 4A data (matches research_cache.db).
  jrfm/figures/fig01_obfuscation.png                      == paper2/figures/output/fig03_obfuscation.png            : True (0a95743c3d30)
  jrfm/figures/fig02_regime_window.png                    == paper2/figures/output/fig02_regime_window.png          : True (ebd77291f7b3)
  jrfm/figures/fig03_validation_pipeline.png              == paper2/figures/output/fig04_validation_pipeline.png    : True (1341e43fa30e)
  jrfm/figures/fig04_selectivity.png                      == paper2/figures/output/fig05_selectivity.png            : True (3766e61415ce)
  jrfm/figures/fig05_gex_magnitude_distribution.png       == paper2/figures/output/fig06_gex_magnitude_distribution.png: True (e89abddcaf72)
  jrfm/figures/fig06_detection_progression.png            == paper2/figures/output/fig08_detection_progression.png  : True (dbc84c2b128d)
  jrfm/figures/fig09_threshold_sensitivity.png            == paper2/figures/output/fig09_threshold_sensitivity.png  : True (1cd1822352ea)
  jrfm/figures/fig10_hmm_agreement.png                    == paper2/figures/output/fig10_hmm_agreement.png          : True (49255aa6bbae)

====================================================================================================
13. IMAGES EMBEDDED IN THE COMPILED PDFs vs REPO PNGs (PyMuPDF; pixel equality)
====================================================================================================
AIAI Regan_Xie_AIAI.pdf pages 14
  page  4  4167x1770  identical to: ['paper2/figures/output/fig01_architecture.png']
  page  5  2970x1920  identical to: no current repo PNG (earlier render)
  page  7  4170x2070  identical to: ['paper2/figures/output/fig04_validation_pipeline.png', 'jrfm/figures/fig03_validation_pipeline.png']
  page  8  3570x2391  identical to: ['paper2/figures/output/fig05_selectivity.png', 'jrfm/figures/fig04_selectivity.png']
  page  9  3570x1485  identical to: ['paper2/figures/output/fig06_gex_magnitude_distribution.png', 'jrfm/figures/fig05_gex_magnitude_distribution.png']
  page 11  3570x2661  identical to: ['paper2/figures/output/fig08_detection_progression.png', 'jrfm/figures/fig06_detection_progression.png']
JRFM Regan_Xie_JRFM.pdf pages 29
  page  6  2970x1920  identical to: no current repo PNG (earlier render)
  page  8  3570x1485  identical to: ['paper2/figures/output/fig02_regime_window.png', 'jrfm/figures/fig02_regime_window.png']
  page 12  4170x2070  identical to: ['paper2/figures/output/fig04_validation_pipeline.png', 'jrfm/figures/fig03_validation_pipeline.png']
  page 14  3570x2391  identical to: ['paper2/figures/output/fig05_selectivity.png', 'jrfm/figures/fig04_selectivity.png']
  page 15  3570x1485  identical to: ['paper2/figures/output/fig06_gex_magnitude_distribution.png', 'jrfm/figures/fig05_gex_magnitude_distribution.png']
  page 16  1888x 617  identical to: ['paper2/figures/output/fig09_threshold_sensitivity.png', 'jrfm/figures/fig09_threshold_sensitivity.png']
  page 17  1592x 647  identical to: ['paper2/figures/output/fig10_hmm_agreement.png', 'jrfm/figures/fig10_hmm_agreement.png']
  page 18  3570x2661  identical to: ['paper2/figures/output/fig08_detection_progression.png', 'jrfm/figures/fig06_detection_progression.png']

```

---

## 12. Not verified / speculation

- **[S]** Why the January extract becomes call-only on 2023-09-29 (missing put gamma at extraction time is one reading; not investigated here; see the other forensics tasks).
- **[S]** Who created the 10 placeholder rows and why the Phase 3/4 files carry calendar dates; the builders are `src/data_sources/historical_gex_builder.py` and the batch scripts, but I did not trace which run wrote them.
- **[S]** The -(call+put) convention may reflect an assumption that dealers are short both calls and puts; the manuscripts state the opposite sign for puts.
- **[S]** The origin of AIAI's "$23B", "6.3%", "r = +0.501 / -0.549" and "404 / 202 / 203" values (older drafts or earlier runs); no artifact reproduces them.
- The manual-review sample (98/96/100/88%) has no per-window audit file in the repo; its composition comes from the full-length draft (`docs/papers/paper2/latex/05_Results.tex:365`).
- All [D] replays use today's reloaded raw table and are not substitutes for LLM re-runs.

## 13. Artifacts

`forensics2/published_claim_inventory.md` (this file); `forensics2/f3/` (scripts above plus `f3_evidence_output.txt`, `f3_series_*.json` reconstructed input series, `f3_phase4a_parsed.pkl`, `f3_phase4a_mech_accuracy.csv`, `f3_replay_detection_by_year.csv`, `f3_replay_quarterly_agreement.csv`, `f3_entries_all.json`).
