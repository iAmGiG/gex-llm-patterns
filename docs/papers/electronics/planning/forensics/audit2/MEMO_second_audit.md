# Second audit of the F3 impact claims (Paper 1, AIAI 2026, JRFM)

To: C. Regan, Y. Xie. Scope: the single-auditor F3 claims on parts of the papers other than the call-only Phase 4A/5 finding (upstream issue #24), which is taken as given.
Rule applied: a claim is VERIFIED only if I reproduced the key evidence myself from primary sources. Everything was read-only. My scripts and outputs are in `.../scratchpad/audit2/` with a `v2_` prefix: `v2_raw.py`, `v2_p3.py`, `v2_p3b.py`, `v2_hn.py`, `v2_raw_2020.csv`, `v2_raw_2024.csv`, `v2img/` (embedded PDF images), `v2_fig08_jan8.png`.
Repo root below: `R=/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns`.

Method note: PostgreSQL raw GEX = sum(gamma * open_interest * 100 * underlying_price^2 * 0.01), SPY, one year per scan, `enable_seqscan=off`, `statement_timeout=600s`. "ex0" excludes same-day expiries. "Signed net" is call minus put.

Verdict key: VERIFIED = reproduced as stated. PARTLY = core reproduced, a part is wrong or unsupported. REFUTED. OPEN = cannot be settled from available files.

---

## 1. Phase 3 / Phase 4 prompts and dates

### 1.1 The Phase 3 (2024) and Phase 4 (2020) prompts carried calendar dates. VERIFIED
Evidence, all reproduced:
- `R/reports/validation/paper2_regime_windows/batch_jobs/phase3_full_2024_baseline_v2.jsonl` and `batch_regime_20251120_104630.jsonl` each hold 223 requests. Each is a single user message to `o4-mini`.
  - Every prompt has exactly 30 lines of the form `2024-01-02: -33.01B` (regex `\d{4}-\d{2}-\d{2}`: min 30, max 30). Regex `Day T` finds 0 in either file.
  - Neither prompt contains SPY, a ticker, spot or DTE (checked on the Phase 3 prompt).
  - `phase3_full_2024_baseline.jsonl` and `_v2.jsonl` are identical (md5 900eb1037440a752ae1d213c25ac18e2).
- The batch metadata files link the two files to the batches named in the result YAMLs:
  - `batch_691ea7f7...` ("Phase 3: Full 2024 baseline validation (223 windows)") uses `phase3_full_2024_baseline_v2.jsonl`.
  - `batch_691f37d9...` ("Phase 4: 2020 baseline (0DTE hypothesis)") uses `batch_regime_20251120_104630.jsonl`.
- I scanned every input JSONL in `batch_jobs/`. Only these three files contain dates (223/223 prompts each, 0 with `Day T`).
  - All Phase 1 files, the Phase 2 controls (`batch_regime_20251119_2306xx`), the Nov-22 multi-year files (221-251 windows each) and the four `phase4a_postgresql_20260104_*.jsonl` files (1,476 prompts in the largest) use `Day T-k` and contain 0 dates.
- Model use: the Phase 3 response for `window-2024-06-05` writes "neg->pos on 2024-06-04 and pos->neg on 2024-06-05" (the only response in that file that quotes a date). This shows the dates were visible to the model. It does not show that they influenced the label. See 5.1.

Papers' statements that are false for these two runs:
- AIAI `03_Methodology.tex:33`: "calendar dates become relative labels ('Day T-29' through 'Day T+0') ... ticker ... INDEX_1".
- JRFM `03_Methodology.tex:6, 57` and the Fig. 1 caption. JRFM `07_Appendix_A_Prompts.tex` (~line 73) shows the placeholder filled in `Day T-29: +3.42B` format.
- The abstracts and conclusions ("stripping calendar dates ...").

Correction wording:
> "The Phase 1 baseline, the Phase 2 synthetic controls and the Phase 5 multi-year windows were presented with relative labels (Day T-29 ... Day T+0). The 2024 full-year baseline (Phase 3, 223 windows) and the 2020 baseline (Phase 4, 223 windows) were presented with calendar dates (YYYY-MM-DD, 30 per prompt) and no ticker or other identifier. The dates were therefore visible to the model in these two runs, and the 81.2% vs 12.1% contrast is not an obfuscated result."

### 1.2 Cause and code path. PARTLY (code path VERIFIED, cause OPEN)
- `R/scripts/validation/paper2/05_validate_regime_windows_batch.py` lines ~163-176 does replace each date by `Day T{offset}` ("CRITICAL: Apply obfuscation ..."). `src/llm/mechanics_prompt_builder.py:374` uses `day["date"]` verbatim ("Already obfuscated").
- I found no script or commit that produced the two dated files. `git log -S phase3_full_2024_baseline` returns only the merges 477bb41 and e58f7d6. The generator is not in the repo (a doc page `docs/papers/paper2/results/phase3_results.md` mentions the file name only).
- Why they are dated is not documented. That is speculation, not a finding.

Wording: "The input files for Phase 3 and 4 were not produced by the committed obfuscating script, and their generating code is not preserved." Do not write that the pipeline always obfuscated.

### 1.3 The headline contrast (81.2% vs 12.1%) rests on dated prompts. VERIFIED, with two numeric corrections
- YAML counts: `phase3_baseline_2024_full_year.yaml` has 181/223 = 81.2%; `phase4_baseline_2020.yaml` has 27/223 = 12.1% (gap 69.06 pp).
- Phi from the 2x2 table [[181,42],[27,196]]: 0.6922 (no continuity correction; 0.688 with Yates). Fisher exact p = 1.82e-52. JRFM's phi = 0.69 and p = 1.8e-52 reproduce.
- AIAI's phi = 0.672 does NOT reproduce from these counts. It appears in AIAI abstract (`Regan_Xie_AIAI.tex:27`), `04_Results.tex:59`, `research_summary.tex:34` and the Fig. 3 footer (`fig04_validation_pipeline.py:197`). Correct to 0.69 (0.692).
- Causal effect of dates on the outcome: untestable with local data. No Day-T rerun of the 2024 full-year or 2020 baseline exists. See OPEN-1.
- AIAI `03_Methodology.tex:33` says the LLM receives "GEX magnitudes, spot prices, and days to expiration". The Phase 3 prompt has none of spot or DTE, only `date: net GEX in billions`. Correct this.

Correction wording: "81.2% (181/223) vs 12.1% (27/223); phi = 0.69, Fisher p = 1.8e-52; both runs used calendar-dated prompts." Delete "spot prices and days to expiration" for the regime task.

---

## 2. Phase 3 / Phase 4 series lineage

### 2.1 The Phase 3 (2024) series is -(call + put), ex-0DTE, with the sign imposed. PARTLY
Reproduced:
- All 6,690 dated values in the 223 Phase 3 prompts (252 unique dates) match `R/.cache/gex_database.db` `daily_gex_metrics.total_gex` (SPY, 2024) within 0.006B (0 mismatches).
- On the 242 rows with `options_count` not NULL, DB `net_call_gex` < 0 and `net_put_gex` < 0 on every row, and `total_gex` = their sum (max abs deviation 1.5e-5).
- Against PostgreSQL raw chains (own recomputation): `total_gex` = -(call_ex0DTE + put_ex0DTE), median relative error 0.31%, p90 1.07%, 242/242 within 5%, corr 0.9989. Including same-day expiries: median error 16.3%, 2/242 within 5%. Spot checks: 2024-01-02 raw 16.21 + 16.60 = 32.82 vs DB -33.01; 2024-03-15 12.65 + 17.15 = 29.80 vs -29.84.
- Not "negative on every day". 242 of 252 dates are negative. 6,399 of 6,690 window values are negative. The 291 positive values (all from 10 dates) are placeholder rows:
  - Dates: 2024-02-02, 02-09, 02-16, 02-23, 03-01, 03-08, 03-22, 03-28, 06-04, 06-06.
  - Placeholder signature: `net_call_gex = net_put_gex = 0`, `options_count` NULL, `total_gex` = +10.6 to +13.8B, `spot_price` a round 461-495 (e.g. 461.0, 467.0, 482.75).
  - All ten were created 2025-11-03 15:32:55 to 15:33:28. The other rows were created in Oct 2025.
  - Raw chains for these dates exist in PostgreSQL today (ex0 gross 27-33B). Only 2024-03-15 has a `.cache/gex_data/SPY/<date>` folder among the dates I tested.
- The 42 rejected windows:
  - All are labelled "transitional"; window ends 2024-02-20 to 2024-04-18.
  - Each contains 3 (7 windows), 4 (10), 5 (16) or 6 (9) placeholders. All placeholders are from the eight Feb-Mar dates; none from the June dates.
  - Sign flips in rejected windows: 6-12. In detected windows: 0-5. Detected windows contain 0 (130), 1 (8), 2 (41) or 3 (2) placeholders.
- Rule replay on the exact prompt numbers (>=21 same-sign days, mean |GEX| >= 5B, <=5 sign flips): reproduces the YAML label in 223/223 windows (same with >=22). Replacing the ten placeholder values by -(ex0 raw gross) makes 223/223 windows detected.

Not VERIFIED as phrased: "negative on every day by construction". The sign is imposed by the formula, but ten days are positive placeholders. "Sign-stripped" is the wrong label for 2024 (it is sign-forced).

Correction wording:
> "The Phase 3 input series is the gross (call + put) dollar gamma, excluding same-day expiries, with a negative sign imposed; it is not a signed net. Ten of the 252 dates are backfilled placeholder rows (zero call/put components, no option count, off-market spot) carrying +10.6 to +13.8B. All 42 'transitional' rejections contain 3-6 of the eight Feb-Mar placeholders; with those values replaced by the gross series from the raw chains, every one of the 223 windows meets the detection rule."

Withdraw the sentence in AIAI `04_Results.tex:15` and JRFM `04_Results.tex:80`: "The framework correctly rejected 42 windows (18.8%) exhibiting February-March volatility (6-10 sign flips)". Flips are 6-12 and they come from the placeholder rows, not market volatility. Also JRFM `04_Results.tex:125` ("rejection is driven by stability (sign flips)... consistent with the February-March volatility") and the Fig. 4 caption's "February 2024 window rejected for stability".

### 2.2 The Phase 4 (2020) series is positive on 252/252 days; it is magnitude-only. VERIFIED
- `batch_regime_20251120_104630.jsonl`: 252 unique dates, min +0.01B, max +11.23B, 0 negative, 0 zero, mean 2.853B.
- Today's signed net for 2020 (PostgreSQL raw call minus put): negative on 93 of 252 days. The same count results with or without 0DTE.
- Against `R/.cache/consolidated_historical.db` `daily_gex_metrics.gex_oi` (SPY 2020, 250 non-null days):
  - corr(Phase 4, |gex_oi|) = 0.9959.
  - corr(Phase 4, signed gex_oi) = -0.795.
  - Phase 4 is not exactly |gex_oi|: median abs diff 0.062B, p90 0.40B, max 1.21B, within 0.006B on only 14 of 250 days.
- corr(Phase 4, today's signed net) = 0.70; with |net| = 0.81.

Correction wording: "The 2020 comparison series is a positive, OI-based magnitude series (corr 0.996 with |gex_oi|, median deviation 0.06B, max 1.2B); the signed net is negative on 93 of 252 days in 2020. The 12.1% therefore reflects only the $5B magnitude gate." Do not say "= |gex_oi|".

### 2.3 "Persistent negative (2024) vs positive (2020)" in Table 3 is a sign-convention artifact. VERIFIED
- 2024 = gross magnitude forced negative; 2020 = absolute-value magnitude. Under one definition (signed net from the same raw table): 2024 positive on 157 of 252 days, negative on 95 (mean +1.46B); 2020 negative on 93 of 252. Neither year is a single-sign regime.
- Table 3: AIAI `04_Results.tex:53` ("Dominant Sign: Negative | Positive | Flip"); JRFM has the same table (JRFM `04_Results.tex:~119`).
- Corroboration: Phase 1 (same Q1-2024 period, relative labels) has first-window values mixing +6.3B and -1.9B, and labels 37 "persistent_positive" and 15 "transitional" windows. Phase 3 labels 181 "persistent_negative". Phase 4A/5 labels all 2024 windows persistent_positive.
- Limits: I did not rerun the LLM. The inference rests on series construction and on the rule replay (rule = label in 223/223).

Correction wording: drop the "Dominant Sign" row and the "persistent negative regime" narrative, or say "the sign of the series is set by the input convention (gross forced negative in 2024; absolute value in 2020) and carries no market information". Persistence figures in Table 3 (96.0% vs 83.3%) and the "$13.95B" 2024 magnitude need recomputation from one consistent signed series. (Side note: the Phase 3 prompt values are ~30B, so $13.95B in Table 3 does not come from the Phase 3 input; source unchecked, see OPEN-4.)

---

## 3. Paper 1 scalar sign

### 3.1 The 242-day scalar is -(call+put) ex-0DTE and negative by construction. VERIFIED
- `R/reports/validation/paper1_pattern_taxonomy/gamma_positioning_SPY_2024_unbiased.yaml` (242 detections): `call_gamma` < 0 and `put_gamma` < 0 on 242/242; `net_gex_usd` = call + put to 1.4e-14; `net_gex_usd` < -$2B on 242/242; mean -31.35B, min -44.49B, max -20.66B.
- Against PostgreSQL raw chains: corr 0.9974 with -(ex0 gross) (median relative error 1.96%) vs corr 0.80 with all-expiry gross (median error 18.2%).
- Post-rebuild `gex.options_daily_summary` (signed net) on the same 242 dates: negative on 93, below -$2B on 75, mean +1.26B, corr with the Paper 1 series -0.07. Over all 252 days: 95 negative, mean +1.46B.
- 71.5% reproduces: detected 168 + 163 + 188 = 519 of 726 (gamma_positioning, stock_pinning, 0dte_hedging). Gamma_positioning alone is 168/242 = 69.4%.
- Caveat (analytic): -(call+put) is a dealer-positioning assumption (dealers short all options), not a data error. The inconsistency is with the paper's stated calls-positive/puts-negative convention (`04_Experimental_setup.tex:15`).

Correction wording:
> "The daily GEX scalar given to the model is the negative of the unsigned sum of call and put dollar gamma (same-day expiries excluded), i.e. it assumes dealers are short all open interest. It is therefore negative on all 242 days by construction and carries no information about regime. Under the calls-positive/puts-negative convention, the same dates are negative on 93 days with mean +$1.26B."

Qualify "persistent negative gamma regime driven by 0DTE" (IEEE `05_Results.tex:161,180,182`; journal `05_Results.tex:190`, `06_Discussion.tex:19`; JRFM equivalents).

### 3.2 "mean -$19.87B, range -$40.69B to -$4.75B is not reproducible". PARTLY
- The figures in the text (-19.8657B mean, -40.6892B min, -4.7506B max) reproduce exactly from the four quarterly files `paper1_pattern_taxonomy/biased_2024/gamma_positioning_SPY_2024Q1..Q4.yaml` (242 days).
- Quarterly means: Q1 -34.23B (53 days), Q2 -30.50B (61), Q3 -9.91B (64), Q4 -7.79B (64). Q1 and Q2 equal the unbiased series (ratio 1.000); Q3 and Q4 are 0.36x and 0.25x of it on the same dates.
- The series behind the 71.5% result, the CSV (`reports/statistical_validation/gamma_positioning_timeseries_2024.csv`, 242 rows) and the Granger analysis has mean -31.35B, range -44.49B to -20.66B.
- The cause of the Q3/Q4 difference is not documented (OPEN-5).
- Inventory wording "not reproducible" is wrong.

Correction wording: replace with "mean -$31.35B (range -$44.49B to -$20.66B)" or disclose that the text mixes two scalar computations. Locations: IEEE `05_Results.tex:161`, journal `05_Results.tex:190`.

### 3.3 The 13-date raw-chain test: the baseline arm saw the same scalar. VERIFIED, with an added design finding
- The 13 dates come from `paper1_raw_chain/batch_raw_chain_20251125_153842.jsonl`: 2024-01-02, 01-09, 01-17, 01-18, 01-19, 03-05, 03-06, 03-13, 03-15, 06-05, 06-07, 06-21, 06-28.
- The unbiased YAML scalar on these dates runs -25.13B (01-19) to -38.83B (01-17).
- Baseline detections: 8/13 = 61.5% (8 detected with confidence 80-85; 5 not detected with confidence 0: 01-09, 06-05, 06-07, 06-21, 06-28). The 12/13 raw-chain count is from `RESULTS_SUMMARY.txt`; I did not rerun the LLM. `RESULTS_SUMMARY.txt` states the baseline includes "-$32B GEX".
- Signed net on those dates (PostgreSQL): negative on 7, below -$2B on 5, range -15.35B (2024-03-15) to +14.88B (2024-01-19).
- Selection design: `scripts/validation/paper1/01_validate_raw_options_chain.py` `get_test_sample` is documented as "high-detection and low-detection from baseline" (detected and confidence >= 80, or not detected). The 13 dates are 8 high, 5 low. The rule that picked exactly these 13 is not recorded (the default seed-42 25+25 sampler does not reproduce them). Whether they were chosen on baseline outcome is therefore an inference from design plus composition (VERIFIED for the sampler; the 13-date selection itself is OPEN-6).
- Full-year baseline detection is 168/242 = 69.4%.

Correction wording: "The baseline arm was given the -(call+put) ex-0DTE scalar (-$25.1B to -$38.8B on these 13 dates); the 13 dates comprise 8 baseline detections and 5 misses, so 8/13 = 61.5% is not an unbiased estimate of baseline detection (full-year 69.4%). With n = 13 the comparison is 12/13 vs 8/13." Soften "GEX loses information" and "directly refutes the pattern-matching critique".

### 3.4 Illustrative values (-$32.9B on 2024-03-15; -$32.5B). PARTLY
- 2024-03-15 values: Paper 1 scalar -29.29B; Phase 3 DB -29.84B; PostgreSQL signed net -15.35B. "-$32.9B on 2024-03-15" matches none of them. It appears paired with that date only in JRFM `03_Methodology.tex:15`. In Paper 1 (journal `05_Results.tex:93`, IEEE `05_Results.tex:70`) "-$32.9B, Flip $485.00" is an undated format example.
- -$32.5B is the Paper 1 value for 2024-01-02 (-32.4905B). The inventory claim that it "matches no stored series" is wrong. It is in the IEEE Fig. 2 caption (`04_Experimental_setup.tex:35`) and journal `04B_Methodology_Validation.tex:99`.

Correction wording: in JRFM `03_Methodology.tex:15` use -$29.3B for 2024-03-15 (or remove the date and call the row synthetic). Keep -$32.5B but name the date (2024-01-02) and the scalar definition.

### 3.5 "The raw-chain arm can only be run on the 72 dates in the sqlite cache". PARTLY
- `R/.cache/consolidated_historical.db` `raw_options_chain` has exactly 72 SPY dates in 2024 (list verified; includes all 13 test dates; none in Apr-May).
- The script reads only that file.
- PostgreSQL `gex.options_chains_partitioned` has raw SPY chains on all 252 2024 dates, including dates absent from the cache (2024-02-02: 8,422 rows; 04-15: 8,310; 05-15: 9,060; 09-16: 9,942).
- So the cache is the limit, not the data.

Correction wording: "Raw-chain results exist for 13 of 242 dates (5.4%), all in Jan, Mar and Jun, because the script reads a 72-date cache; full 2024 chains exist in PostgreSQL."

---

## 4. Figures

### 4.1 AIAI Fig. 6 = JRFM Fig. 8 (fig08_detection_progression) shows the script's synthetic fallback. VERIFIED
- My extraction with PyMuPDF: AIAI p11 and JRFM p18 images are `np.array_equal` to `docs/papers/paper2/figures/output/fig08_detection_progression.png` and `docs/papers/jrfm/figures/fig06_detection_progression.png` (3570x2661).
- I viewed it. Bars read 27/223, 8/223, 72/223, 45/223, 223/223, 74/74; line values $4.2B, $5.1B, $8.7B, $12.3B, $18.5B, $22.8B; title "360% Growth 2021->2024"; footer "360% (5B->23B)". These equal `generate_synthetic_data()` in `fig08_detection_progression.py` lines 29-40.
- Real data (read-only `R/.cache/research_cache.db`, `llm_detections`, pattern `regime_30day`, 1,412 rows, 646 detected): 2020 26/213 (12.2%, $2.97B); 2021 9/241 (3.7%, $4.88B); 2022 79/244 (32.4%, $5.52B); 2023 46/228 (20.2%, $9.58B); 2024 241/241 ($20.35B); 2025 245/245 ($18.97B).
- History: commit 01a3bcd (2026-01-08) PNG shows the real values (viewed). Commit bfb7764 (2026-01-14) added `generate_synthetic_data()` and the try/except; the committed PNG (md5 7791778c...) is the synthetic render and is the last commit touching it. Why the synthetic branch ran on Jan 14 is unknown (OPEN-7). I did not re-render the fallback, so the pixel-level "identical to a fresh render" claim is not tested; the decisive evidence is that every printed value matches the fallback and none matches the data.

Correction wording: replace the figure in AIAI and JRFM with a render from the cache (labels 26/213, 9/241, 79/244, 46/228, 241/241, 245/245; GEX $3.0, 4.9, 5.5, 9.6, 20.3, 19.0B). Fix title and footer: 2021 to 2024 is +317%, 2020 to 2024 is +585%, and 2025 is $19.0B not $23B. The footer's own rates (12.2%, 3.7%, 32.4%) contradict the bars (12.1, 3.6, 32.3). JRFM's text and Table 5 already use the real values.

### 4.2 AIAI Fig. 4 = JRFM Fig. 4 (selectivity) is synthetic; the JRFM caption cites real windows. VERIFIED (JRFM caption); AIAI caption is generic
- `fig05_selectivity_demo.py` generates all values with `np.random.uniform` after `np.random.seed(42)` and hard-codes persistence/flips. Running its generator gives panel means 13.7B (93.3%, 2 flips, DETECTED), 19.0B (90%, 3 flips, DETECTED), 3.0B (93.3%, REJECTED), 12.1B (50%, 8 flips, REJECTED). Embedded images in AIAI p8 and JRFM p14 are equal to the PNGs.
- JRFM Fig. 4 caption (p14): "2024-Q2 ... 28/30 days negative, $30B, 3 sign flips", "2024-Q4 ... 27/30, $25B, 2 flips", "February 2024 ... 55% persistence with 8 sign flips", "2020-Q2 ... 90% persistence but only $2.8B". None matches the panels.

Correction wording: label both as "schematic / synthetic illustration (random draws, seed 42)" and delete the dated numbers from the JRFM caption, or replace panels with four real windows and keep the numbers.

### 4.3 JRFM Fig. 2 (regime window) is synthetic by construction. VERIFIED
- `fig02_regime_window_example.py:85`: `create_figure` sets `data = generate_synthetic_example()` (uniform draws, seed 42) and never uses its `example_data` argument. `main()` prints "Using real example from database" at line ~170.
- JRFM p8 image equals the repo PNG. Caption says "30-day persistent negative regime example", with no "illustrative".

Correction wording: caption "Illustrative synthetic window". Remove the misleading print.

### 4.4 Fig. 3 (validation pipeline) is hard-coded and 6.3% is not reproducible. VERIFIED
- `fig04_validation_pipeline.py` lines ~40-70 hard-code 71.2 (n=52), 6.3 (n=52), 81.2 (n=223), 12.1 (n=223); line 197 hard-codes "phi = 0.672". I viewed the image: "Negative Control, Shuffled, 6.3%, n=52". AIAI p7 and JRFM p12 are equal to the PNG.
- Recomputed from the YAMLs: phase1 37/52 = 71.2%; shuffle 2024Q1 33/54 = 61.1%; shuffle 2020 27/223 = 12.1%; transitional 0/223 (2020) and 0/32 (2024Q1); low magnitude 0/223 and 0/54; pooled false positives of the three controls: 60 of 809 = 7.4%. No file has 6.3% or n=52 for a Phase 2 control.
- JRFM Fig. 3 caption promises "95% bootstrap confidence interval" and "Phase 5"; the image has neither (viewed).
- The "0% false positives" statement holds for the transitional and low-magnitude controls only. The shuffle control gave 33/54 (61.1%) and 27/223 (12.1%).

Correction wording: "False-positive rates on negative controls: shuffle 60/277 (21.7%; 33/54 in 2024Q1, 27/223 in 2020), transitional 0/255, low-magnitude 0/277." Then correct the figure panel and phi (0.69).

### 4.5 Fig. 5 (GEX magnitude distribution): real data. VERIFIED, with caveats
- The viewed image (AIAI p9, JRFM p15): title "+585% Growth (2020 -> 2024)", n = 213 / 241, means $3.0B / $20.3B, "Above $5B: 14% / 100%". These equal the cache values I recomputed. 2024 histogram range ~$15-26B.
- The 2024 data are the call-only Phase 4A series (premise), so the histogram needs regeneration after the put fix.
- JRFM `04_Results.tex:164` says "roughly 577%", which equals (20.3/3.0 - 1) on rounded values. Unrounded is +585%. Use one number.

---

## 5. Headline numbers

### 5.1 "$23B" in 2024-25. PARTLY
- Recomputed from `phase4a_postgresql_20260104_184832.jsonl` (1,476 prompts, 30 values each) joined to the cache (1,412 windows): mean window |GEX| by year 2.97, 4.88, 5.52, 9.58, 20.35, 18.97 B; the LLM `avg_magnitude_billions` means are identical to 2 dp. 2024 median 19.91B. 2024-25 pooled mean 19.65B; only 99 of 486 windows have mean >= 23B. No stored series gives 23B.
- Where $23B appears: AIAI `04_Results.tex:85-86` ($23B for 2024 and 2025), `04_Results.tex:93`, `05_Discussion.tex:23` caption, AIAI PDF text (4 matches), and the Fig. 8 image in both PDFs. The JRFM tex has no "$23B"; the JRFM PDF text has none either. JRFM Table 5 already uses $3.0/4.9/5.5/9.6/20.3/19.0B. JRFM `CoverLetter.tex:26` carries "360%".
- Scope the claim as AIAI text and the Fig. 8 image in both papers, not "JRFM text".

Correction wording: AIAI Table 4 Avg GEX = $3.0B, $4.9B, $5.5B, $9.6B, $20.3B, $19.0B. Flag that the 2024-25 values are call-only.

### 5.2 "+360% ($5B to $23B)" and "+577%". PARTLY
- Recomputed: 2021 to 2024 +317.0%; 2021 to 2025 +288.7%; 2020 to 2024 +585.2%; 2020 to 2025 +538.7%. (23/5 - 1) = 360% on numbers not in any series.
- JRFM "+577%" is (20.3 - 3.0)/3.0 = 576.7% on rounded table values. Unrounded: +585%.
- "360%": AIAI `04_Results.tex:93`, `05_Discussion.tex:23`, JRFM `CoverLetter.tex:26`, the Fig. 8 title and footer, and `fig08_detection_progression.py` lines ~231 and ~250.

Correction wording: "+317% (2021 to 2024: $4.9B to $20.3B)" or "+585% (2020 to 2024: $3.0B to $20.3B)". Mark all post-2023-09-29 values as call-only.

### 5.3 Phase 5 totals and the pre/post-break split. VERIFIED
- Cache: 1,412 rows, 646 detected = 45.75%. Wilson 95% CI [43.2, 48.4]% (matches JRFM Table 5 total row).
- Per-year n/detected equals Table 5: 213/26, 241/9, 244/79, 228/46, 241/241, 245/245.
- Split by window end date: before 2023-09-29: 866 windows, 117 detected = 13.5%. On or after 2023-09-29: 546 windows, 529 detected = 96.9% (81.9% of all 646 detections). Windows ending in 2024-25: 486 detected = 75.2% of detections.
- Windows ending on or after the break include 226 negative days in total (partial overlap with the pre-break signed period), so "call-only" is exact only for windows starting after the break.

Correction wording: "The pooled 45.8% mixes two input series; windows ending before 2023-09-29 (signed net) detect 117/866 = 13.5%, windows ending on or after it (call-only) 529/546 = 96.9%."

### 5.4 LLM label equals the deterministic rule. VERIFIED
- On the numbers actually sent (1,476 prompts), rule = (>=21 same-sign days) and (mean |GEX| >= 5B) and (<=5 sign flips): 1,412/1,412 cache labels match, 0 mismatches. The first auditor also reports 1,476/1,476 on the output file with tolerant parsing; I reproduced the 1,412 and the Phase 3 (223/223) match, not the output-file parse (OPEN-8, minor).
- Consequence: every Phase 3 and Phase 5 rate is a pure function of the input series.

---

## 6. What this means for the JRFM production proof and the AIAI paper (VERIFIED items only)

1. Phase 3 and Phase 4 were run with calendar dates visible (30 per prompt, no ticker). Both papers say all inputs were relabelled "Day T-k". The sentence and its appendix example must change, or the two runs must be redone with relabelled input. The memorization-control claim cannot rest on these two runs.
2. The Phase 3 (2024) series is a sign-forced gross magnitude. It has ten placeholder rows. All 42 rejections are explained by those rows, so "42 windows exhibiting Feb-Mar volatility (6-10 flips)" and the "18.8% principled rejection" claim are unsupported (JRFM `04_Results.tex:80, 125`, Fig. 4 caption; AIAI `04_Results.tex:15`).
3. The Phase 4 (2020) series is a positive magnitude series. Table 3 "Dominant Sign" (and the "persistent negative" narrative) is a convention artifact and should be dropped or reworded.
4. Paper 1's 242-day scalar is negative by construction. The "-$19.87B / -$40.69B / -$4.75B" figures come from the quarterly biased files; the series behind the 71.5% has mean -$31.35B (range -$44.49B to -$20.66B). The 13-date raw-chain comparison used the same scalar and 13 dates with 8 baseline hits and 5 misses.
5. Figures: Fig. 8 in both papers (AIAI Fig. 6, JRFM Fig. 8) is a synthetic fallback with $23B and 360% labels. Fig. 4 (selectivity) in both papers and JRFM Fig. 2 are synthetic; JRFM Figs. 2 and 4 captions cite or imply real windows. Fig. 3 hard-codes a 6.3% control rate and phi 0.672. Fig. 5 is real data (call-only in 2024).
6. Numbers: phi is 0.69, not 0.672 (AIAI abstract, `04_Results.tex:59`, `research_summary.tex:34`, figure footer). AIAI Table 4 should read $3.0/4.9/5.5/9.6/20.3/19.0B. Growth is +317% (2021 to 2024) or +585% (2020 to 2024); JRFM's 577% should be 585%. The pooled 45.8% mixes two series (13.5% before the break, 96.9% on or after).
7. For JRFM: the production tex (`jrfm-4256551-production-CORRECTED.tex`) has no "$23B", but the Fig. 8 image, `CoverLetter.tex:26` ("360%") and the Phase 3 / Phase 4 / Fig. 2 / Fig. 4 text above are affected. For AIAI (published): the items above that touch AIAI text and figures (relabelling statement, Table 3, Table 4, Fig. 4, Fig. 6, phi, "42 windows") would need an erratum or a revised version.

---

## 7. OPEN items and the file that would settle each

| # | Question | File / run that would settle it |
|---|---|---|
| OPEN-1 | Do calendar dates change the Phase 3 / Phase 4 labels? | A Day-T rerun of `phase3_full_2024_baseline_v2.jsonl` and `batch_regime_20251120_104630.jsonl` (about 446 requests, a few dollars at o4-mini). Since label = rule on the sent numbers, a deterministic replay already predicts the outcome; only the LLM run answers the memorization question. |
| OPEN-2 | Which script produced the dated Phase 3/4 inputs, and why? | The script or notebook is not in git. Check `~/.bash_history`, notebooks, or the author's working tree for something that wrote `phase3_full_2024_baseline*.jsonl` and `batch_regime_20251120_104630.jsonl`. |
| OPEN-3 | Where does AIAI's phi = 0.672 come from? | The notebook or script that first computed the effect size; not in the repo. |
| OPEN-4 | Where do the Table 3 values (persistence 96.0% / 83.3%, magnitude $13.95B, 0DTE share 48% / <5%) come from? | Not traced by me. $13.95B does not match the Phase 3 input (about $30B). Compare with `phase3_baseline_2024_full_year.yaml` `raw_response` fields. |
| OPEN-5 | Why are the Q3/Q4 `biased_2024` quarterly scalars 0.36x and 0.25x of the unbiased series? | The code and DB state that wrote `biased_2024/gamma_positioning_SPY_2024Q3/Q4.yaml` (`scripts/validation/paper1/02_validate_pattern_taxonomy.py` and the git history of the `gex_metrics` computation). |
| OPEN-6 | Which rule selected the 13 raw-chain dates? | A selection record for batch `batch_692613d891248190a19cfbb46d8b6c8b` (the input JSONL has the dates but not the rule). |
| OPEN-7 | Why did the Jan 14 regeneration of fig08 use the synthetic branch? | The shell session or environment of commit bfb7764 (probably a missing, gitignored `research_cache.db`); only a rerun in that environment would show it. I did not re-render the fallback. |
| OPEN-8 | Does the LLM response file agree with the rule on all 1,476 windows (tolerant parsing)? | `results_phase4a_postgresql_20260104_193513.jsonl`; reported by the first auditor, not re-run by me. |
| OPEN-9 | Signed-net versions of Phase 3/4/5 after the put-fix. | Pending upstream issue #24 rebuild; needs the fixed `gex.options_daily_summary` and a new batch. |
