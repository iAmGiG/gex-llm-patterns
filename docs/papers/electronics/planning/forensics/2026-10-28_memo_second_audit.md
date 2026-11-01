# Second-audit memo: published-paper items beyond the put-row loss

**For:** Christopher Regan, Ying Xie · **Date:** 2026-10-28 · **Status:** each item below was tested by an independent skeptic against primary sources (batch files, result YAMLs, sqlite caches, the live database, the figure scripts, the compiled PDFs). Verdicts: VERIFIED (reproduced), PARTLY (true with the stated correction), OPEN. Nothing here was re-run through an LLM.

This memo complements `2026-10-28_memo_published_inputs.md` (the put-row loss in the Phase 4A/5 inputs, upstream issue #24). Evidence scripts and outputs: `audit2/` in this folder.

## 1. Phase 3 / Phase 4 prompts carried calendar dates — VERIFIED

- The two runs behind the headline contrast (Phase 3, 2024, 223 windows, 81.2%; Phase 4, 2020, 223 windows, 12.1%; OpenAI batches `batch_691ea7f7…` and `batch_691f37d9…`, 2025-11-20) used input files `phase3_full_2024_baseline_v2.jsonl` and `batch_regime_20251120_104630.jsonl`. **223/223 prompts in each contain 30 ISO dates (`2024-01-02: -33.01B` …) and no "Day T-k" label**; no ticker. The model used them (one Phase 3 response quotes "pos→neg on 2024-06-05").
- All other runs were obfuscated as described: Phase 1, the Phase 2 controls, the multi-year 2021/2022/2023/2025 runs, and Phase 4A/5 (January 2026).
- The script that produced the two dated files is not in the repository (the committed `04_/05_validate_regime_windows*.py` do relabel); the files were built by an unpreserved step.
- The prompts contained only daily net GEX; AIAI Methodology ("receives GEX magnitudes, spot prices, and days to expiration") does not describe them.
- φ recomputed from 181/223 vs 27/223 is **0.692** (Fisher p = 1.8e-52), as JRFM prints; **AIAI's 0.672 does not reproduce**.

**Correction:** state that the 2024 full-year and 2020 baseline runs were made with dates visible (so they cannot support the memorization-control claim), that the obfuscation claim holds for the other runs, and correct φ in AIAI. Either rerun Phases 3/4 obfuscated (~$1–2) or reword the abstract/Methods.

## 2. The 2024 and 2020 series behind that contrast used different sign conventions — VERIFIED / PARTLY

- **Phase 3 (2024):** every prompt value equals `.cache/gex_database.db daily_gex_metrics.total_gex`, which is the **gross** magnitude (call + put dollar gamma, same-day expiries excluded) **with a negative sign imposed** (both components stored negative). Negative on 242 of 252 dates; the 10 non-negative dates are backfilled placeholder rows (inserted 2025-11-03; zero components, NULL option count, off-market spot) carrying +10.6 … +13.8 B, and every one of the 42 "rejected for Feb–Mar volatility" windows contains 3–6 of them.
- **Phase 4 (2020):** every prompt value is positive (252/252), a magnitude-only OI-based series (r = 0.996 with |gex_oi| but not identical: median deviation 0.06 B, max 1.2 B); the signed net for 2020 is negative on 93/252 days.
- Under one consistent signed definition (today's calls − puts), 2024 is positive on 157 and negative on 95 days; 2020 positive on 159, negative on 93. **Neither year is a single-sign regime, and the 2020-vs-2024 sign difference does not appear.**

**Correction:** drop or restate the "Dominant sign: Negative (2024) vs Positive (2020)" row of Table 3 and the "persistent negative regime" narrative; recompute any persistence comparison from one signed series; describe the Phase 3 input as "gross magnitude with a negative sign imposed, negative on 242/252 dates" and disclose the placeholder rows.

## 3. Paper 1 scalar GEX — VERIFIED / PARTLY

- The 242-day scalar behind the single-day results (71.5% detection; "all 242 days negative, < −$2B") is **−(call + put) excluding same-day expiries**, both legs negative (`gamma_positioning_SPY_2024_unbiased.yaml`: call + put = net on every day, max rel. error 4e-16; r = 0.997 with the raw ex-0DTE gross). "GEX < −$2B on 242/242 days" therefore **holds by construction**. Under the calls-positive/puts-negative convention the paper states, the same dates have 93 negative days, 75 below −$2B, mean +$1.26 B.
- The printed "mean −$19.87B, range −$40.69 to −$4.75B" reproduces from the quarterly `biased_2024` run files, whose Q3/Q4 scalars are on a different, smaller scale (≈0.36× and 0.24× of the unbiased series on the same dates). The unbiased series behind 71.5% has mean **−$31.35 B** (range −44.49 … −20.66). The paper mixes two scalars.
- The 13-date raw-chain test (92.3% vs 61.5%) fed its GEX arm the same scalar (−25.1 … −38.8 B on those dates), and the 13 dates were stratified on the baseline outcome (8 detections, 5 misses), so 61.5% is not an unbiased baseline (full-year 69.4%).
- "−$32.9B on 2024-03-15" (JRFM Methodology) matches no stored value for that date (Paper 1 scalar −29.29 B; Phase 3 −29.84 B; current signed net −15.35 B). "−$32.5B" is the 2024-01-02 scalar.
- The raw-chain arm ran on 13 of the 72 dates in the sqlite cache; full 2024 chains exist in PostgreSQL, so "can only be run on 72 dates" is a cache limitation, not a data limitation.

**Correction:** state the scalar's definition, drop "negative on 242/242 days" as a finding, report −$31.35 B for the series actually used (or disclose the two scalars), label the baseline arm's input, and soften the "GEX loses information" conclusion to what 12/13 vs 8/13 on a stratified sample supports.

## 4. Figures — VERIFIED

- **AIAI Fig 6 = JRFM Fig 8** (detection progression): the image embedded in both PDFs is identical to the repo PNGs and shows the script's synthetic fallback values (27/223, 8/223, 72/223, 45/223, 223/223, 74/74; $4.2–22.8 B; "360% Growth 2021→2024"). The real Phase 4A data are 213/26, 241/9, 244/79, 228/46, 241/241, 245/245 and $2.97 … 18.97 B. The DB path of the script works today; the fallback was what got rendered.
- **AIAI Fig 4 = JRFM Fig 4** (selectivity): synthetic (`np.random.seed(42)`, `np.random.uniform`); the JRFM caption cites specific 2024-Q2/Q4/Feb-2024/2020-Q2 windows and statistics that match none of the panels. AIAI's caption is generic but the figure is still undisclosed synthetic.
- **JRFM Fig 2** (regime window): synthetic by construction; the script ignores the database result and prints "Using real example from database".
- **AIAI Fig 3 = JRFM Fig 3** (validation pipeline): hard-coded 71.2 / **6.3 (n = 52)** / 81.2 / 12.1 and φ = 0.672. "6.3%" and n = 52 exist in no result file; the Phase 2 controls give shuffle 33/54 = 61.1% (2024-Q1) and 27/223 = 12.1% (2020), transitional 0/255, low-magnitude 0/277, pooled 60/809 = 7.4%. "0% false positives" holds only for the transitional and low-magnitude controls.
- **AIAI Fig 5 = JRFM Fig 5** (magnitude distribution): real Phase 4A data, so no synthetic issue, but the 2024 histogram is the call-only series and must be regenerated; its title says +585% while JRFM text says +577%.

**Correction:** regenerate Fig 6/8 from the real query; label Fig 4 and JRFM Fig 2 as synthetic illustrations or replace them with real windows and fix the captions; replace 6.3%/n = 52 with the per-control results and φ with 0.692.

## 5. Headline numbers — VERIFIED / PARTLY

- "$23B" (AIAI Table 4, text, Fig 6 caption) matches no stored series; the window means are $3.0 / 4.9 / 5.5 / 9.6 / 20.3 / 19.0 B (JRFM Table 5 already prints these).
- "+360% ($5B → $23B)" is arithmetic on two numbers that are not in the data; 2021→2024 is **+317%** ($4.9 → 20.3 B), 2020→2024 **+585%** (JRFM's +577% is the same ratio on rounded values). All 2024–2025 magnitudes are call-only GEX, so the growth is a data artifact in any case.
- 646/1,412 = 45.8% and its Wilson CI reproduce, but the pooled rate mixes two input series: pre-break windows 117/866 = 13.5%, windows ending on/after 2023-09-29 529/546 = 96.9%.
- The o4-mini labels equal the deterministic rule (≥ 21 same-sign days, mean |GEX| ≥ $5 B, ≤ 5 flips) on 1,412/1,412 cached windows and on all 1,476 responses (tolerant parsing; strict JSON parses only 445; the pipeline dropped 64, of which 21 are rule-detected).

## What this means (verified items only)

- AIAI 2026 and JRFM: the 2024–2025 rows (Table 4/5, the pooled 45.8%, the growth claim, Figs 5–6/8) rest on call-only inputs; the 81.2% vs 12.1% contrast rests on dated prompts and two sign conventions; φ = 0.692; three figures are synthetic, one of them the headline progression figure. JRFM is in production, so this is the moment to tell the handling editor.
- Paper 1 (IEEE BigData 2025 / journal draft): the "negative on 242/242 days" statement and the −$19.87 B magnitude need correction; the 13-date raw-chain comparison needs its stratification and the baseline-arm input disclosed. The put-row loss does not touch Paper 1.
- The Electronics extension becomes the vehicle for the corrected analysis: exact recovered inputs, a complete signed series, obfuscated prompts throughout, every input and label stored, and the deterministic rule reported next to every LLM rate.

## Open items

- The generating script for the dated Phase 3/4 files; the SQLite→PostgreSQL copy step of 2026-01-02; why 2022-05-31 matches no candidate series; the 31 of 635 "need collection" dates not seen in the writer log; the archive's 2025-12-31 put value; whether QQQ/IWM and pre-2020 raw data outside the #24 re-collection (upstream #69: 72 of 108 symbols) are complete.
