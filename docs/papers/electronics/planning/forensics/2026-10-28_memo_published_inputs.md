# Forensic memo: the inputs behind the published Paper 2 results (Phase 4A, January 2026)

To: Christopher Regan, Ying Xie, database maintainer (gex-database-infrastructure)
Date: 2026-10-28
Scope: AIAI 2026 (in press, Springer) and JRFM (in production, last repo commit 369bec9), Paper 2 Phase 4A inputs, plus Paper 1 exposure
Status: read-only forensics. No table written, nothing installed, no repo file edited, nothing committed.

Labels used on every statement:
- VERIFIED (source): established by a command or artifact; the source is named.
- LIKELY (reason): best explanation, not directly observable.
- OPEN: not established.

Source codes: F1 = series-matching audit; F2 = root-cause / provenance audit; F3 = published-claim inventory; SK1-SK3 = three independent skeptics who tried to refute the explanation (none could); ME = checks I re-ran while writing this memo on `jan_vs_candidates_daily.csv`.
Important limit: SK1-SK3 reviewed the forensic explanation (sections 2-5). Nobody has adversarially reviewed the F3 impact inventory (section 6.2-6.4); those items are single-auditor and should get a second pass before anything is sent to an editor.

---

## 0. Headline

The "100% detection in 2024-2025" in Paper 2 (486 of 486 windows; AIAI Table 4, JRFM Table 5), and the "structural shift" and "+360% GEX growth" built on it, were produced by input data that contained only the call side of the options chain. From 2023-09-29 through 2025-12-31 (565 of 565 trading days) the daily GEX value shown to o4-mini equals the sum of call-contract GEX (0DTE included) to within 0.005B, with puts contributing exactly nothing. The cause is a bug in the PostgreSQL writer used by the 2026-01-02 Alpha Vantage collection: it read a column named `option_type` that Alpha Vantage calls `type`, labelled every contract "call", and the table's unique key silently discarded the put of every call/put pair (upstream issue #24, fixed 2026-02-03, all years then re-collected). Replaying the paper's own deterministic criteria on the exact January input series reproduces the published detection rates within 0.9 pp in every year (100% and 100% for 2024 and 2025), while the same criteria on the complete net-GEX series give 10.3% (2024) and 13.6% (2025). The language model is not the source of the artifact: it tracked its inputs. The 2020-2022 rows of Phase 4A are largely unaffected (2022 may differ by up to about 8 pp, see 6.1). Separately, the F3 audit found that the headline 81.2% vs 12.1% contrast and the Paper 1 results rest on other series with their own integrity problems (6.2, 6.4); these are not consequences of the put-loss bug and need independent confirmation.

---

## 1. Evidence base

- Exact Phase 4A input file (1,476 requests, 2026-01-04): `/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns/reports/validation/paper2_regime_windows/batch_jobs/phase4a_postgresql_20260104_184832.jsonl`; raw o4-mini output beside it (`results_phase4a_postgresql_20260104_193513.jsonl`). The Day T+0 value of each window gives the daily series (1,505 distinct days, 2020-01-02 to 2025-12-31); all 1,475 consecutive window pairs are mutually consistent. (VERIFIED: established facts of this workflow; SK1, SK3 re-extracted values themselves.)
- Today's database: `gex.options_chains_partitioned` (raw; all SPY rows `created_at` 2026-02-03, i.e. reloaded after the fix), `gex.options_daily_summary` (rebuilt 2026-10-08), and read-only archives `backups.options_daily_summary_pre_rebuild_20261004` / `backups.intraday_gex_summary_pre_rebuild_20261004`.
- The pre-reload raw table no longer exists, so the January put rows cannot be inspected directly. The conclusion rests on the numerical match, the code, the fix commit, the collection log, and a date-level join (VERIFIED limitation).
- Per-day comparison table (1,505 rows): `docs/papers/electronics/planning/forensics/jan_vs_candidates_daily.csv`.

---

## 2. Verified facts

V1. January series = call-only GEX from 2023-09-29 on. For all 565 days from 2023-09-29 to 2025-12-31 the January value matches today's call-only GEX (all expirations, 0DTE included) within 0.006B (max difference 0.00499B); 0 of 565 match full net GEX (closest approach 7.66B, median distance 18.7B). VERIFIED (F1; SK3 recomputed from the JSONL and an independent SQL query; ME recount: 565/565 call_all, 0 full).
Examples (billions; January / full net / call-only): 2023-12-15 18.56 / 1.56 / 18.56; 2024-03-15 14.61 / -15.35 / 14.61; 2025-06-16 22.12 / 6.16 / 22.12.

V2. January series = full net GEX before the step, on 900 of the 940 days up to 2023-09-28 (within 0.006B, max difference 0.0050B). VERIFIED (F1; ME: 900 full, 39 call-only, 1 none among the 940 days before 2023-09-29).
- 419 of 419 days before 2021-09 match full and none match call-only (SK2).
- Consequence: the raw data re-fetched in February 2026 reproduces the January values to the cent on 900 days of 2020-2023, so vendor revisions or the later reload are not a material source of difference. VERIFIED by the same match.

V3. Day classification over all 1,505 days: 900 full only, 604 call-only only, 0 both, 1 neither. VERIFIED (F1; ME: 604 call-only, of which 565 are the permanent regime and 39 are sporadic days before it).

V4. No match from the archive tables. `backups.options_daily_summary_pre_rebuild_20261004` never matches the January series within 0.006B on any of 1,505 days (median difference of its total -0.75B, correlation 0.975). VERIFIED (F1).
- Ratio January / archive call GEX, median by year: 2024 1.22, 2025 1.27 (ME). Consistent with January = stored gamma including 0DTE and the archive = a call-only table with 0DTE zeroed. LIKELY (ratio is as stated; the attribution to 0DTE share is a reading of the series, not separately proven).
- Archive put GEX is exactly zero on 98 of 249 SPY days in 2023 (all of Oct-Dec), 251 of 251 in 2024, 249 of 250 in 2025 (only 2025-12-31 is nonzero, -20.0B); zero on 0 (2020), 2 (2021) and 3 (2022) days. VERIFIED (F2 psql on the archive, archive created 2026-01-15).
- Therefore the frozen archive is itself put-less from 2023-10 on. It is not a "Black-Scholes convention" series that merely differs from today's; this changes the framing of the electronics design memo (section 8).

V5. The sporadic lead-in. 39 call-only days occur before 2023-09-29 (ME; F1's text says 36, which is a miscount: its listed dates include 2023-09-29 and omit three). Per year: 2021: 2, 2022: 3, 2023: 34. First one 2021-09-17. Per quarter: 2021 Q3 1, Q4 1, 2022 Q2 1, Q3 1, Q4 1, 2023 Q1 9, Q2 11, Q3 14 (to 09-28). VERIFIED (F1, ME).
The exact set of 604 January call-only days equals the exact set of 604 SPY dates that the collection log shows were written through `postgresql_options_manager` on 2026-01-02 (2021: 2, 2022: 3, 2023: 98, 2024: 251, 2025: 250). The other 901 days were written through SQLite and have puts. VERIFIED (SK2 date-level join of log, January series, and archive put-zero days: 603 of the 604 also have zero archive put GEX; the exception is 2025-12-31).

V6. Replay of the paper's criteria (persistence = larger sign count >= 21 of 30; mean |GEX| >= 5B; sign flips <= 5; windows of 30 consecutive points of each series' own calendar, grouped by end-date year, 1,476 windows). VERIFIED as deterministic replay (F1; not an LLM re-run):

| Series | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Published (o4-mini) | 12.2 | 3.7 | 32.4 | 20.2 | 100 | 100 |
| January series (published input) | 12.1 | 4.0 | 32.3 | 19.3 | 100 | 100 |
| Today's full net, 0DTE included (`options_daily_summary`) | 12.1 | 3.6 | 40.6 | 22.4 | 10.3 | 13.6 |
| Today's full net, ex-0DTE | 2.7 | 0.0 | 36.7 | 25.2 | 13.1 | 16.4 |
| Today's call-only, 0DTE included | 90.6 | 100 | 100 | 100 | 100 | 100 |

(Last two rows from F3 `f3_replay_detection_by_year.csv`.) Mean |GEX| on the January series by year: 3.0 / 4.9 / 5.5 / 9.5 / 20.3 / 19.0 B; on today's full series 2024 6.5B and 2025 7.1B (F1).
Reading: call-only GEX is persistently positive and large in every year; the full net series is not. Truncating the January series at 2023-09-28 gives 1.6% for 2023 (185 windows) with 2020-2022 unchanged (F1).

V7. The LLM faithfully applies the rule. F3 reports that on Phase 5 the model's regime labels equal the deterministic rule in 1,412 of 1,412 parsed windows. VERIFIED by F3 only (single auditor). If correct, the published 100% reflects the inputs, not LLM reasoning error.

V8. Windows after the break. 565 of the 1,476 windows (ME) end on or after 2023-09-29; F3 counts 546 of the 1,412 parsed ones, holding 529 of the 646 detections (81.9%); the 866 earlier windows detect 13.5%, not the published 45.8% overall. VERIFIED (F3; the 565 count reproduced by ME).

V9. Published table values match the repository text. AIAI `04_Results.tex` lines 80-88 show 2020 213/26/12.2%, 2021 241/9/3.7%, 2022 244/79/32.4%, 2023 228/46/20.2%, 2024 241/241/100%, 2025 245/245/100%, total 1,412/646/45.8%. VERIFIED (ME read).

---

## 3. Exact transition date

- Last day on which the January series equals full net GEX: 2023-09-28 (-8.93 vs full -8.925). VERIFIED (F1, ME).
- First day of the permanent call-only regime: 2023-09-29 (13.47 vs call-only 13.473 and full -10.67). Every one of the 565 days from there to 2025-12-31 is call-only. VERIFIED (F1, ME).
- 2023-09-27 is a sporadic call-only day (10.87 vs call-only 10.870, full -13.37), then 2023-09-28 is full again, then call-only forever. Auditors sometimes quote "2023-10-02" or "October 2023" as the break; the correct date is 2023-09-29.
- First ever call-only day: 2021-09-17 (sporadic outlier). VERIFIED (F1).
- Coincidence with the pipeline: SQLite storage covered SPY 2020-01-02 to 2023-09-28 (900 dates); everything the PostgreSQL path wrote starts the day after. LIKELY that the cutoff is a hand-off between the two storage paths (SQLite-collected dates kept puts; dates collected via PG did not). The SQLite-to-PG load step that put the 900 SQLite dates into PG is unlogged and not in either repo: OPEN.

---

## 4. Mechanism

VERIFIED (F2, SK1, SK2 read the code and diff):
- `src/cache/postgresql_options_manager.py` at e58f7d6 (2026-01-04) has `option_type = row.get('option_type', 'call')` (I re-read this line). Alpha Vantage's column is `type`. Every contract defaulted to "call".
- The insert is `ON CONFLICT (symbol, trading_date, strike, option_type, expiration) DO NOTHING`, so the second row of each (strike, expiration) pair (the put) was discarded. In today's reloaded table, ids interleave call, put at each strike with the call first, which is why first-wins kept the call.
- Fix: gex-database-infrastructure commit 2c16a4d, 2026-02-03 04:34, "Correct option_type column mapping", fixes issue #24 (opened and closed 2026-02-03; issue states puts stored per year: 2020 6.1M, 2021 1.7M, 2022 1.1M, 2023 584K, 2024 0, 2025 0 across all symbols, and that all years were truncated and re-collected). After the fix SPY 2024-12-31 stores 4,823 calls and 4,823 puts.
- The Phase 4A script (e58f7d6:scripts/validation/paper2/phase4a_postgresql_batch.py) has no option_type filter, and `GEXCalculator.calculate_net_gex_from_raw` subtracts every non-'call' row; so a call-only output means no put rows reached it. The script and formula are identical on all 1,505 days, yet the series switches convention by date, which rules out a script bug (SK2).
- Alternatives rejected: put gamma sign cancelling (would give call+|put|, not call), a different spot per type, an Alpha Vantage row limit/pagination/endpoint change (no such code; API returned both types in the February 2026 test; the cutoff date coincides with the storage hand-off), coincidence (SK3 permutation test: about 1.4 expected matches vs 565 observed; put GEX is at least 7.7B and median 18.7B on those days, so a zero put leg is not a fluke).

LIKELY: why the PG path handled the 39 sporadic dates before 2023-09-29. They are dates that were missing from the SQLite set and were collected later through the PG path (the log shows "[SPY] Found 1536 trading dates, 635 need collection" on 2026-01-02). Direct support is the 604-date join in V5; the reason those particular dates were missing from SQLite is not shown.

OPEN:
- The unlogged SQLite-to-PG load of the 900 early dates.
- 2022-05-31 is the only day matching no candidate: January -1.33, today's full -1.2275 (0.10B off), archive total -1.3130 (0.017B off); neighbouring days match to 0.004B. Speculation: a slightly different row set in the January database on that day.
- 2025-12-31: January is call-only (and the logged PG path wrote it), but the archive row has a nonzero put (-20.0B, archive total -5.39B vs call 14.64B). Possibly rewritten by another process after the PG write; unexplained and immaterial to the conclusion.
- 635 dates "need collection" in the log vs 604 PG-written SPY dates: the difference of 31 is unaccounted for (failures such as the two calendar gaps, or other causes).
- Whether symbols other than SPY used in any extension (QQQ, IWM) and any pre-2020 data carry the same loss: see 8 and 9. Issue #69 mentions that the #24 re-collection covered 72 of 108 symbols, and IEF/LQD archive rows are also put-zero (501 of 502). Today's reloaded SPY table is 50/50 calls/puts (VERIFIED F2); other symbols not checked.

---

## 5. The two calendar gaps

- The January series lacks 2023-07-12 and 2024-03-11. Both are real trading days. VERIFIED (F1): today's raw table has normal SPY counts on them (2023-07-12: 7,974 rows, 5,803 valid; 2024-03-11: 8,586 rows, 7,191 valid; neighbours similar), and both dates are in today's `options_daily_summary` (2023-07-12 total 17.13B; 2024-03-11 total 0.053B).
- Why January lacked them: the collection log shows a SQLite "database is locked" error followed by "No options data returned" for 2023-07-12, and "Invalid data ... Empty DataFrame" for 2024-03-11. The archive built 2026-01-15 also lacks both dates, so the January database lacked them. VERIFIED (SK2 log grep and psql). The February 2026 reload filled them.
- Effect on published windows: each 30-point window spanning a gap covers 31 real trading days with one day skipped. 29 windows around each gap (end dates 2023-07-13 to 2023-08-22 and 2024-03-12 to 2024-04-22), 58 of 1,476 in total, ranges do not overlap. VERIFIED (F1). The published description "30 consecutive trading days" is therefore not literally true for these 58 windows. Impact on detection is small and not quantified separately (OPEN; a replay with the missing days inserted would answer it).
- Not a symptom of the put bug: these dates are absent, not call-only. Interaction: both gaps sit in the call-only regime for 2024-03-11 and the sporadic-call-only period for 2023-07-12.
- Observation, not followed up: `.cache/gex_data/SPY/` has directories for both gap dates but lacks 2024-03-08, which is in the January series. The cache calendar and the January query calendar differ (OPEN, immaterial).

---

## 6. Impact inventory

Lineage tags (from F3): L-P5 = Phase 4A/Phase 5 January extract (this memo). L-P3 = Phase 3 2024 series from `.cache/gex_database.db` (-(call+put), ex-0DTE, with 10 placeholder rows). L-P4 = Phase 4 2020 series. L-P1 = Phase 1 Q1-2024 file-cache series. L-P2 = Phase 2 controls built from L-P1/L-P4. L-PAPER1 = Paper 1's 242-day -(call+put) series. L-RAW13 = Paper 1's 13-date raw-chain test.
Full inventory with 168 file:line anchors: `docs/papers/electronics/planning/forensics/published_claim_inventory.md`.

### 6.1 Claims that depend on the January (call-only) extract, L-P5 (VERIFIED by F3 and the replay; table values re-read by ME)

| Claim | Where | Status |
|---|---|---|
| 2024 241/241 = 100%, 2025 245/245 = 100% (486/486) | AIAI Table 4 (`04_Results.tex:85-86`); JRFM Table 5 | Artifact of call-only inputs. Replay on full net: 10.3% / 13.6%. |
| Total 646/1,412 = 45.8% | AIAI `:88`; JRFM Table 5 | Invalid as stated; 529 of 646 detections are in windows ending on/after the break; earlier windows 13.5%. |
| 2023 46/228 = 20.2% | AIAI `:84` | Contaminated: 3 of 168 pre-break windows detect (1.8%), 43 of 60 post-break (71.7%). The 20.2% agrees numerically with today's full-series 22.4% but by a different composition (LIKELY coincidence; no window-level comparison done: OPEN). |
| 2022 244/79/32.4% | AIAI `:83` | Mostly unaffected (all 79 detections are persistent_negative; only 3 call-only days + 1 unexplained in 2022), but replay on today's full net gives 40.6% (up to 8 pp different). LIKELY that the 4 flagged days flip borderline windows; window-level diff not done: OPEN. |
| 2020 (12.2%), 2021 (3.7%) | AIAI `:81-82` | Not materially affected (2020: 252/252 full-match days; 2021: 250/252). |
| Gradual regime evolution, "detection jumped discontinuously in 2024", non-monotonic 32.4 -> 20.2 -> 100 | Abstract, 05_Discussion | Not supported: the step is the data break at 2023-09-29, not the 2023/2024 boundary. |
| GEX magnitude +360% ($5B -> $23B); JRFM ~577% ($3.0B -> $20.3B); fig05 title +585% | AIAI `04:93`; JRFM `04:164` | Driven by call-only 2024-25 values. $5B and $23B appear in no series (F3). Signed net mean |GEX| 3.24 -> 6.46 (+99%) by replay. |
| 2023->2024 transition chi2/Fisher/phi (0.783 AIAI, 0.82 JRFM) | AIAI `04:93`; JRFM `04:164` | Arithmetic reproduces (phi recomputes to 0.819) but compares the pre-break regime with the call-only regime. |
| Confidence 92.8% vs 52.1% (40.7 pp), r = +0.719/-0.705 (JRFM) / +0.501/-0.549 (AIAI) | AIAI `04:104`; JRFM `04:293` | 486 of 646 detections are 2024-25. Excluding them: 85.8 vs 52.1, r +0.511/-0.477. AIAI's r values do not reproduce (F3). |
| 25-grid threshold robustness (>72 pp) | AIAI `05:49` | 2024 = 100% at every threshold because the input is call-only; not evidence of robustness. |
| Fig 5/6 (GEX magnitude distribution), fig08 (detection progression) | see 6.5 | 2024 histogram is the call-only series; fig08 is a hard-coded synthetic fallback. |
| Phase 5 completion-token and schema-failure statements | JRFM `07_Appendix_A:40,294` | 64 of 1,476 responses dropped before "retained"; 2,457/5,924 are prompt+completion totals (F3). Minor. |

### 6.2 Headline claims that do NOT use Phase 5 but have their own lineage problems (single auditor F3; not caused by the put bug)

- 81.2% (2024, 181/223) vs 12.1% (2020, 27/223), 69.1 pp, phi = 0.672 (JRFM prints 0.69; recomputes to 0.692), Fisher p, CIs, 45-config sweep, HMM, ablation n = 84, manual review of 50. These come from L-P3 (2024) and L-P4 (2020), not Phase 5. F3 reports: the 2024 series is -(call+put) ex-0DTE, which is negative every day by construction; 10 of its 252 rows are placeholders (call/put components 0, spot 6-7.5% below SPY), and all 42 rejected 2024 windows contain 3-6 of these placeholders (2024 = 223/223 without them); the 2020 series is sign-stripped (252/252 positive although signed net is negative on 93 days). The "Persistent negative vs persistent positive, flip" contrast in Table 3 is therefore a convention artifact, not an observation. Both prompt sets carry calendar dates (all 446 prompts), contradicting the stated obfuscation ("Calendar dates become relative labels", AIAI `03:33`, JRFM `03:6`). The Phase 1/2/5 prompts use Day T-k labels.
- Phase 2 controls (0% false positives on transitional / low-magnitude, shuffle 61.1% vs 12.1%): built from L-P1 and L-P4; the low-magnitude arm scales ~$14B/~$2.6B by 0.25 so it cannot reach $5B by construction. Table 2 sizes do not match stored YAMLs (277/255/277 vs 404/202/203 in AIAI).
- Figure and caption mismatches (F3): fig08 synthetic; JRFM fig04 selectivity synthetic with captions citing specific windows; fig03/fig04 pipeline figure hard-codes 6.3% and phi that do not reproduce (shuffle 61.1%, pooled controls 7.4%).
- Because these are single-source and arithmetically intricate, treat them as findings to confirm, not as established, before external communication. (OPEN: second-auditor confirmation.)

### 6.3 Claims not dependent on the affected inputs (F3)

- Phase 5 2020 row (213 windows, 12.2%, $3.0B): January extract equals signed net on 252/252 days. 2021 row: 250/252 days, window agreement 98-100%.
- Criteria and procedure definitions (>=70% persistence, mean |GEX| >= $5B, <=5 flips, regime taxonomy, prompt text and schema in JRFM Appendix A, o4-mini/Batch API); external 0DTE share statistics; returns-based Markov-switching rates (80.1%, 87.4%); test arithmetic given counts; related work and limitation text; batch cost $11.07 (Phase 4A only; 2,221 evaluations omit the 498 Phase 1/3/4 evaluations).

### 6.4 Paper 1 exposure

- Put-loss bug: NOT exposed. VERIFIED (F2). Paper 1's raw-chain script (`scripts/validation/paper1/01_validate_raw_options_chain.py`) read the SQLite file `.cache/consolidated_historical.db` (built 2025-11-23, before the 2026-01-02 PostgreSQL collection). It has 11,820,580 SPY rows, exactly 5,910,290 calls and 5,910,290 puts; its 2024 slice has 308,961 of each over 72 dates; the four Issue #143 sample prompt dates are inside the 72, and the 2024-03-15 prompt visibly contains Put rows. 2024-03-15 totals from that file (call_ex 12.60B, put_ex 17.19B) match the reloaded PostgreSQL (12.65B, 17.15B). The raw-chain arm can only be run on those 72 dates (coverage limit).
- Different exposure, F3 only (not adversarially reviewed): Paper 1's scalar GEX arm uses -(call+put) ex-0DTE (stored call and put gamma both negative; r = 0.997 with the 242-day series), not the stated "calls positive, puts negative" formula. Consequences listed by F3: "all 242 days negative / persistent negative regime" is true by construction (today's signed net on those dates is negative on only 93 days, mean +$1.26B); the 13-date "92.3% raw chain vs 61.5% GEX-assisted" comparison fed the GEX arm that scalar (baseline -$25.1B to -$38.8B; today's signed net is negative on 7 of 13); the 242 vs 253 missing days are the 10 placeholder rows; 91.2% materialization carries a separate Issue #187 erratum (41.6%); Granger lag-2 p = 0.042 conflicts with all p > 0.3 in `statistical_validation_summary.md`. The independent items are the WHO-WHOM-WHAT definition, validation levels, and the obfuscation protocol as a procedure.
- JRFM imports these Paper 1 numbers (71.5%, 91.2%, 92.3% vs 61.5%, Sharpe 1.8 -> 0.1, "all 242 days negative"), so JRFM inherits whatever applies to them.

### 6.5 Figures (F3)

| Figure | Status |
|---|---|
| AIAI Fig 6 = JRFM Fig 8 (`fig08_detection_progression.png`) | Hard-coded synthetic fallback (27/223, 8/223, 72/223, 45/223, 223/223, 74/74; $4.2B-$22.8B), not Table 4/5 data. The script `docs/papers/paper2/figures/scripts/fig08*.py` has `generate_synthetic_data()` returned when the database query fails (ME confirmed the fallback exists; that the compiled PDFs embed it is F3's claim, pixel-identical). |
| AIAI Fig 5 = JRFM Fig 5 (GEX magnitude distribution) | Real Phase 4A data (n = 213 mean $3.0B; n = 241 mean $20.3B); the 2024 histogram is the call-only series. |
| AIAI Fig 3 = JRFM Fig 3 (validation pipeline) | Hard-coded values; 6.3% and phi not reproducible; JRFM caption promises CI boxes and Phase 5 absent from the PNG. |
| AIAI Fig 4 = JRFM Fig 4 (selectivity) | Synthetic (`np.random.uniform`, seed 42) with data-like caption. |
| JRFM Fig 2 (regime window) | Synthetic by construction. |
| JRFM Fig 6, 7 (threshold heatmap, HMM agreement) | L-P3/L-P4 based (6.2). |
| AIAI Fig 1, AIAI Fig 2 = JRFM Fig 1 | Conceptual; example 2024-03-15 GEX -$12.3B matches no stored series. |

---

## 7. Reconciling the auditors; statements not to repeat

- Pre-step call-only day count is 39 (ME), not 36 (F1 text).
- Break date is 2023-09-29, not "2023-10-02" (F2/SK1 phrasing).
- F3 calls 2022 "approximately unaffected"; the replay difference (32.3 on the January series vs 40.6 on today's full net) means "up to ~8 pp" is the defensible statement.
- F1/F2: "archive_call == archive_total from 2023-10": consistent with V4 (put zero).
- The earlier chat figure "0.47x" is not reproduced; do not use it (project memory).
- The 1.25x factor between LLM-reported magnitudes and the frozen table is now explained as LIKELY 0DTE call GEX being present in January but zero in the archive (V4); the JRFM-era statement that January equals today's table "to the cent through 2023-09" is correct only on the 900 full-match days.
- Do not state that the structural shift is "disproven". Verified: the published shift is produced by missing puts. Call-side GEX alone is persistently large and positive in every year (V6 last row) and may be of interest in itself, but it is not the net GEX the paper defines. A corrected LLM result does not yet exist; the 10.3% / 13.6% are deterministic replays.

---

## 8. How the extension study (issue #261) should now be framed

The design memo (`docs/papers/electronics/planning/00_design.md`, section 2) frames the headline as "the 2023-2024 shift lives in non-0DTE gamma; including 0DTE reverses the conclusion", with the cause a Black-Scholes-vs-stored-gamma / 0DTE-zeroing convention change. The forensics supersede that:

1. The published 2024-25 result is explained by missing put contracts in the inputs (call-only series), not by a convention difference in gamma or 0DTE treatment. The frozen archive is also put-less from 2023-10 (put GEX exactly zero), so the old-vs-new comparison conflates three effects: put loss (dominant), BS vs stored gamma, and 0DTE. Section 2 and the `old_bs` row of the run matrix need rewriting. The 100% replay on the archive in the design table is real but means "call-only", not "old convention".
2. Recommended headline of the extension: a data-integrity result. A silent upstream storage fault turned a call-only series into an apparent regime shift; an LLM regime detector reproduced it faithfully; the corrected series do not show it. The contribution is (a) the audit method (exact-input recovery, candidate-series matching to the cent, deterministic replay), (b) a controlled re-test of the LLM on corrected inputs, and (c) input-provenance invariants (put/call balance, OI-weighted sign checks) as a required pipeline stage.
3. Suggested arms (replacing/reordering the matrix; for the authors to decide):
   - `bridge_jan`: luna on the exact January prompts (the series is preserved in the JSONL and in `.../forensics2/../jan2026_phase4a_spy_daily_gex_bn.json`) as the model-agreement bridge to o4-mini. This is an exact bridge, better than the frozen table, which is only a proxy (LLM magnitudes 1.25x it; persistence agrees on ~63% of windows).
   - `full_spy` (priority 1, today's complete net GEX, 0DTE included) and `ex0dte_spy` (ablation).
   - `call_only_spy` (today's raw, calls only, 0DTE included) as a positive control that must reproduce the published 100%. This directly tests that the LLM tracks the data.
   - Rename `old_bs` to "frozen archive (put-less after 2023-10)" or demote it to a diagnostic.
4. Prerequisites before any new run: a put/call-balance check by symbol and day over the full planned range (SPY 2008+, QQQ 2011+, IWM 2008+), because the #24 re-collection covered 72 of 108 symbols and pre-2020 collection history is not documented here (OPEN). A window must not silently skip a trading day: the 58-window calendar issue shows that "any missing day drops the window" must also check against the exchange calendar.
5. Dr. Xie approved the proposal on the earlier framing; the changed headline should be presented to him before spending (key balance $16.86 per project memory).
6. Expect rerun != published. Do not write the `*_pre_rebuild_20261004` archives (maintainer constraint).

---

## 9. Recommended next actions

A. Decisions for the authors (time-sensitive, listed in order):
1. Decide the correction route for JRFM (in production; last commit 369bec9). The 2024-25 100% rows, +577%/+360% growth, the 646/1,412 = 45.8% total, the fig05/fig08 captions and discussion built on them are affected (6.1). Contact the handling editor before publication rather than after.
2. Decide the route for AIAI 2026 (marked in press at Springer): erratum/corrigendum or camera-ready replacement if still possible; confirm with the proceedings contact what is still editable.
3. Decide how to treat the F3 findings in 6.2/6.4 (Phase 3/4 series, placeholder rows, obfuscation wording, synthetic figures, Paper 1 sign convention). They are potentially larger in scope than the put bug and are not yet double-checked.
4. Decide the framing of #261 as in section 8.

B. Verification work before anything is sent externally (all read-only, cheap):
1. Second-auditor pass on F3's 6.2 and 6.4 (placeholder rows, -(call+put) scalar, prompts with dates, synthetic figure embedding in compiled PDFs).
2. Window-level comparison: LLM output vs deterministic rule vs January series for all 1,476 windows (V7 is F3-only), including 2022 (the 8 pp gap) and 2023.
3. Replay the January series with the two missing days inserted (quantify the 58-window effect).
4. Re-extract the surviving results file (`results_phase4a_postgresql_20260104_193513.jsonl`) to tabulate LLM-reported magnitudes against the January series per year.

C. For the database maintainer:
1. Add an ingestion invariant: per symbol/day, put rows must be within a tolerance of call rows; fail the load otherwise.
2. Annotate (documentation, not data change) the `*_pre_rebuild_20261004` archives as put-less for SPY from 2023-10 (and mostly for 2024-25), and check the other symbols in them (IEF and LQD are 501/502 put-zero).
3. Confirm the 36 symbols not covered by the #24 re-collection (72 of 108 done per #69) are either re-collected or flagged.
4. Document the SQLite-to-PostgreSQL load step (unlogged) so the provenance of the 900 early SPY dates is recoverable.

D. Preservation: copy the Phase 4A input/output JSONL and `jan_vs_candidates_daily.csv` to a durable location (the January OpenAI batch files have expired; the repo copies are the only exact inputs).

---

## 10. Open questions (consolidated)

1. Exact mechanism that copied SQLite-collected dates into PostgreSQL (unlogged).
2. Why the 2022-05-31 value matches no candidate (0.017B from the archive total).
3. Why 2025-12-31 differs between the January call-only value and the archive (put -20.0B).
4. The 31-date difference between 635 "need collection" and 604 PG-stored SPY dates.
5. Window-level agreement of the LLM with the rule and the January series (V7 single-source).
6. Effect size of the two calendar gaps on the 58 windows.
7. Pre-2020 data and non-SPY symbols: same defect or not.
8. Whether F3's Phase 3/4 and Paper 1 findings (6.2, 6.4) hold under a second audit.

---

## 11. Reproduction and artifact index

Directory: `docs/papers/electronics/planning/forensics/ (copies of the scratch outputs)`
- `jan_vs_candidates_daily.csv`: 1,505 rows; columns date, jan, full, full_agg, call_all, call_ex0dte, ex0dte, archive_total, archive_call, best_match, abs_diff (tolerance 0.006B).
- `month_match_table.csv`, `agg_candidates.csv`, `agg.py`, `cmp.py`, `an*.py`, `replay.py` (F1).
- `cache_scan.py`, `cache_compare.py`, `raw_daily.py`, `issue24_full.txt`, `issues_22_69.txt`, `archive_*.txt`, `sqlite_*.txt`, `pgdates_sk2.txt`, `archive_putzero_sk2.txt` (F2, SK2).
- `sk1/rep.py` (SK1 random-date check: 10 pre and 15 post dates, 10 full, 15 call-only, 0 none).
- `published_claim_inventory.md`, `f3/` (F3: evidence script and output, replay CSVs).
- January series: `docs/papers/electronics/planning/forensics/jan2026_phase4a_spy_daily_gex_bn.json`.

Key commands (AutoGex env; `psql -h 127.0.0.1 -d gex_options -X`, `SET statement_timeout='600s'`):
- Per symbol-year aggregate on `gex.options_chains_partitioned` with filters `gamma IS NOT NULL AND open_interest>0 AND underlying_price>0`, `sign = CASE WHEN option_type='call' THEN 1 ELSE -1 END`, GEX = `sign*gamma*open_interest*100*underlying_price^2*0.01`, computing full net, calls only (all expirations), calls with `expiration>trading_date`, one statement per year (F1 `agg.py`).
- `git -C gex-llm-patterns show e58f7d6:src/cache/postgresql_options_manager.py | grep -n option_type` (line 104) and `git -C gex-database-infrastructure show 2c16a4d`.
- Archive put-zero counts: `SELECT extract(year from trading_date), count(*) FILTER (WHERE net_put_gex=0) ... FROM backups.options_daily_summary_pre_rebuild_20261004 WHERE symbol='SPY' GROUP BY 1` (F2).
- ME recheck: pandas on `jan_vs_candidates_daily.csv`: `best_match` counts, post-2023-09-29 all `call_all`, 39 call-only before 2023-09-29, last full 2023-09-28, ratio January / archive_call by year.
