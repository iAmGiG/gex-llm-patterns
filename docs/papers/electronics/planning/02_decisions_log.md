# Decisions log: Electronics extension (issue #261)

- Status: third revision, 2026-10-29, reconciled with design memo v2, with the pipeline contract of 2026-10-29 (eleven series, eighteen arms, the test-retest and budget conventions) and with the authors' decisions of 2026-10-28 and 2026-10-29; not committed yet. From the first commit on this is a living document: add entries, do not rewrite history.
- Tracking: gex-llm-patterns issue #261 (upstream context: #260; upstream root cause: gex-database-infrastructure #24). The corrections to the published papers are tracked in issue #262 and in [docs/papers/CORRECTIONS.md](../../CORRECTIONS.md). Branch: `paper/electronics`.
- Companion documents: [00_design.md](00_design.md) (design memo v2, authoritative for the plan except for the points listed in section 5), [01_issue_261_archive.md](01_issue_261_archive.md) (issue text), the forensic memos [2026-10-28_memo_published_inputs.md](forensics/2026-10-28_memo_published_inputs.md) and [2026-10-28_memo_second_audit.md](forensics/2026-10-28_memo_second_audit.md) (evidence), [scripts/validation/electronics/README.md](../../../../scripts/validation/electronics/README.md) (the pipeline runbook) and `scripts/validation/electronics/common.py` (the contract; every constant named below lives there unless the entry names another file).

## How to read this log

- **D-nn** entries are decisions already taken. **Q-nn** entries are open and need the authors (Chris and Dr. Xie). A Q-nn entry that the authors have answered stays in place, marked closed, with a pointer to the D-nn entry that records the answer (Q-01 is closed by D-18).
- A protocol change is a deliberate deviation from the published runs. Every protocol change must be disclosed in the paper.
- The date is the day the decision was recorded in this log. The project started on 2026-10-27 (issue opened 21:01 UTC), so every entry dates from 2026-10-27, 2026-10-28 or 2026-10-29. An entry that was revised after its date says so on its Date line.
- After the first commit, a decision is changed by adding a new entry that supersedes the old one; the old entry stays, marked as superseded. Before the first commit, errors in the draft are corrected in place and listed in the change history (section 6).
- Numbers marked "re-run 2026-10-28" or "re-run 2026-10-29" were recomputed read-only on that day; once the series, windows and runs exist, `05_report.py` regenerates the data-derived ones from the stored tables.
- Table and column names: the schema SQL (`scripts/validation/electronics/sql/gex_llm_regime_schema.sql`) is authoritative.

## 1. Summary

| ID | Date | Topic | Decision |
|---|---|---|---|
| D-01 | 2026-10-28 | Model | `gpt-6-luna` through the Batch API; synchronous calls only for the 40-window pilot |
| D-02 | 2026-10-28 | Reasoning effort | `medium` on every request |
| D-03 | 2026-10-28 | Prompt and output format | Prompt text unchanged; strict JSON schema with the nine Phase 4A fields (the protocol change that applies to every arm); `sign_flips` recomputed deterministically beside the model's value |
| D-04 | 2026-10-28 | Series set | Eleven registered series: the six core series (`jan2026_phase4a` the bridge, `call_only` and `old_bs` diagnostic, `new_full` primary, `new_ex0dte`, `intraday_late`), the scaled `new_full_scaled` and the four Phase 3/4 input series |
| D-05 | 2026-10-28 | Bridge and gate | `bridge_jan` (luna on the exact published inputs) is the bridge and carries the kappa gate against the 1,412 published o4-mini answers (all 1,476 reported beside them); `bridge_old` is an optional diagnostic |
| D-06 | 2026-10-28 | Window rules | Rule A (master-calendar series), rule J (series with their own calendar), rule T0 (composite intraday windows); two hole detectors, `calendar_gap_days` above 4 and `missing_master_days`; flagged windows are kept |
| D-07 | 2026-10-28 | Wording for 2026 | "post-publication period", never "out-of-sample" |
| D-08 | 2026-10-28 | Intraday arm | Composite `intraday_t0` windows (rule T0); `final_rush` snapshot; three irregular days excluded |
| D-09 | 2026-10-28 | Test-retest | `bridge_jan` is run twice (one full repeat, keys with `#rep1`); a duplicate sample for other arms is an optional mechanism (Q-07) |
| D-10 | 2026-10-28 | Budget | Hard stop at USD 12.00 on money spent from the current balance; 29,819 requests (USD 8.92 to 11.18) without and 33,160 (USD 9.92 to 12.44) with the scaled QQQ and IWM arms |
| D-11 | 2026-10-28 | Request mechanics | Chunks of at most 1,500; keys in `custom_id`; 4,000 token cap, one retry at 8,000 |
| D-12 | 2026-10-28 | Thresholds and primary label | Fixed Paper 2 thresholds; `regime_detected` is the primary label |
| D-13 | 2026-10-28 | Statistics | Wilson intervals, calendar-quarter block bootstrap (2,000 draws, seed 261) and a non-overlapping 30-day subsample next to every p-value |
| D-14 | 2026-10-28 | Storage | New standalone tables in `backups`; DDL gated on a documentation PR and the maintainer's approval; parquet and raw JSONL copies; archive tables read-only |
| D-15 | 2026-10-28 | Scope and boundaries | SPY, QQQ, IWM; window ends capped at 2026-10-09; Phase 3/4 reruns on SPY 2024 and 2020 |
| D-16 | 2026-10-28 | Reporting and figures | Everything from stored tables; no synthetic fallback ever; the long CSVs of `05_report.py` are the interface to the figures |
| D-17 | 2026-10-28 | Git policy for raw backups | Raw OpenAI batch files and the series and windows parquet stay on disk and are git-ignored; manifests, runs and detections parquet and the report outputs are tracked |
| D-18 | 2026-10-29 | QQQ and IWM, both variants | Run the unscaled arms (the floor effect as it is) and an open-interest-notional scaled variant (inputs scaled, prompt and thresholds unchanged); closes Q-01 |
| D-19 | 2026-10-29 | Phase 3/4 baselines | Four luna arms rerun the November 2025 inputs with Day-T labels and with the dates actually sent (892 requests); the published o4-mini answers are backfilled for comparison |
| D-20 | 2026-10-29 | Publication status and corrections | JRFM is published, so no hold request; the findings are public (`CORRECTIONS.md`, issue #262); notices for AIAI, JRFM, IEEE BigData and arXiv are in preparation |
| D-21 | 2026-10-29 | API keys | Left as they are: no rotation; read from the git-ignored config, never printed or committed |
| Q-01 | closed 2026-10-29 | QQQ and IWM floor effect | Closed by D-18 |
| Q-02 | open | Wording and notices | What the Electronics paper says about the defect; which notices go to which venue and when; the status of AIAI |
| Q-03 | open | Spend | Confirm spend for priority 2 and 3 (and optional 4) once the pilot cost is known; the upper estimate with the scaled arms is above the hard stop |
| Q-04 | open | Call-only diagnostic | Whether and where the paper shows it; whether to add an LLM positive-control arm |
| Q-05 | open | Agreement gate | Fix metric and threshold before the bridge result is seen; confirm the window set (D-05) |
| Q-06 | open | Primary analyses | Window range, primary comparisons, primary cross-asset variant |
| Q-07 | open | Duplicate sample | Add the optional 5% duplicate sample to the other arms, or only the `bridge_jan` repeat |
| Q-08 | open | `bridge_old` | Run the optional priority-4 arm or drop it |
| Q-09 | open | Large artefacts | git-LFS for the raw JSONL and the series and windows parquet, yes or no |

## 2. Decisions taken

### D-01 Model: gpt-6-luna through the Batch API

- Date: 2026-10-28.
- Decision: every arm uses `gpt-6-luna` (an alias with no dated snapshot) through the Batch API. Only the 40-window pilot calls the API synchronously.
- Why: o4-mini (`o4-mini-2025-04-16`, the Phase 4A model) cannot be called any more: inference requests return 404 `model_not_found` on both keys, on the Chat and the Responses endpoints (recorded in issue #261 on 2026-10-27 and 2026-10-28), although `models.retrieve` still returns the model objects (re-run 2026-10-28). Batch prices of luna are USD 0.05 in and 0.25 out per 1M tokens (standard USD 0.10 and 0.50).
- Supersedes: the 2026-10-27 issue text, which planned a pilot of gpt-5-mini, gpt-5.4-mini and gpt-5.5 on the standard API before choosing a model.
- Evidence: probe of 2026-10-28. Strict `json_schema`, `reasoning_effort` and `max_completion_tokens` are accepted on the synchronous endpoint and on Batch; about 1,911 prompt tokens and 814 completion tokens per request at medium effort; the verdict matched the deterministic rule in 31 of 31 probe responses.
- Recording: the alias carries no dated snapshot, so each run stores the model object's `created` timestamp (`runs.model_created_at`; luna was created 2026-09-14 17:15:02 UTC) and each detection stores the response id.
- Encoded in: `MODEL`, `PRICING_USD_PER_MTOK`, `model_created_at()`.

### D-02 Reasoning effort: medium

- Date: 2026-10-28.
- Decision: `reasoning_effort = "medium"` on every request; the value is stored in `runs.reasoning_effort`.
- Why: medium is o4-mini's default effort in the published run (the Phase 4A request bodies set only `model` and `messages`), so the model changes but the nominal effort does not.
- Evidence (probe, mean completion tokens per request and Batch cost per 1,000 requests): low 660 tokens, USD 0.261 (n=6); medium 814 tokens, USD 0.299 (n=12, sd 152, max 1,224); high 1,008 tokens, USD 0.348 (n=6). The API accepts `none`, `low`, `medium`, `high` and `xhigh`; it rejects `minimal` with HTTP 400.
- Encoded in: `REASONING_EFFORT`, `chat_body()`.

### D-03 Prompt unchanged, strict JSON schema (protocol change)

- Date: 2026-10-28.
- Decision: the prompt text is `MechanicsPromptBuilder.build_regime_prompt`, unchanged (`prompt_version = "v2.0_postgresql"`). The answer is forced into a strict JSON schema with the same nine fields Phase 4A asked for (`regime_detected`, `regime_type`, `positive_days`, `negative_days`, `avg_magnitude_billions`, `sign_flips`, `persistence_pct`, `confidence`, `reasoning`). It is the one protocol change that applies to every arm (the second, a scaled input series for two arms, is D-18) and it is disclosed in the paper.
- Why: round 1 lost 64 of 1,476 responses to a greedy-regex parse; the schema removes the free-text parsing step.
- Sign flips: the probe under-counted `sign_flips` in 7 of 32 schema-constrained answers (design memo v2 s5). The classifier's count is therefore stored beside the model's value (`windows.clf_sign_flips` and `detections.sign_flips`), with the difference per metric in `detections.detection_metadata` (`diff_vs_classifier`). `metrics_agree` covers day counts, magnitude and persistence only; the report prints the share of exact `sign_flips` matches (`sign_flips_exact_pct` in `detection_by_year.csv`).
- Parsing: an answer is read as JSON first, with a second `json.loads(..., strict=False)` that accepts raw control characters inside strings (both count as `ok`); if that fails too, `src/utils/json_parser.extract_json` is the fallback and the row is marked `parse_status = 'fallback'` (`failed` or `missing` when nothing can be read).
- Evidence: all 1,476 January prompts are reproduced byte for byte by `obfuscate()` plus `build_prompt()` (re-run 2026-10-28). The schema adds about 112 prompt tokens (1,911 with the schema, 1,799 without, in the probe).
- Encoded in: `PROMPT_VERSION`, `RESPONSE_FORMAT`, `REGIME_JSON_SCHEMA`, `chat_body()`, `parse_llm_content()`, `metrics_agree()`; `classifier_diff()` in `04_llm_runner.py`.

### D-04 Series set

- Date: 2026-10-28 (revised 2026-10-29: `call_only`, `new_full_scaled` and the four Phase 3/4 series are registered).
- Decision: eleven registered series (`common.SERIES`), each answering a different question: the six core series of design memo v2 s3, one scaled series (D-18) and four Phase 3/4 input series (D-19). Every series is stored (parquet always, Postgres after approval), so the numbers shown to the model are never recomputed.

  | key | source | symbols and range | role |
  |---|---|---|---|
  | `jan2026_phase4a` | the surviving Phase 4A batch file (values at 0.01B precision, January calendar) | SPY, 2020-01-02 to 2025-12-31 | exact published inputs; the bridge to the published result |
  | `call_only` | raw `gex.options_chains_partitioned`, call leg of every contract (0DTE included), put leg dropped | SPY, 2020-01-01 to 2026-10-09 (diagnostic) | reproduces the defect from clean data; no LLM arm (Q-04) |
  | `old_bs` | archive `backups.options_daily_summary_pre_rebuild_20261004` (Black-Scholes gamma on integer DTE, same-day expiries zeroed); read-only | SPY, 2008 to 2026-10-02 (with holes) | diagnostic only; put-less from 2023-10 |
  | `new_full` | `gex.options_daily_summary` after the 2026-10-08 rebuild: stored per-contract gamma, 0DTE included | SPY and IWM from 2008, QQQ from 2011, to 2026-10-09 | the primary corrected series |
  | `new_ex0dte` | raw `gex.options_chains_partitioned` with `expiration > trading_date` | as `new_full` | the 0DTE ablation |
  | `intraday_late` | `gex.intraday_gex_summary`, `snapshot_type = 'final_rush'` | SPY, 2026-07-27 to 2026-10-09 | small intraday check (D-08) |
  | `new_full_scaled` | `new_full` of QQQ and IWM times one fixed open-interest-notional factor per symbol | QQQ and IWM, 2020-01-02 to 2026-10-09 (1,699 and 1,700 days) | the scaled cross-asset variant (D-18) |
  | `p3_2024` | the November 2025 Phase 3 input file (`phase3_full_2024_baseline_v2.jsonl`), values verbatim, Day-T labels | SPY, 2024-01-02 to 2024-12-31 (252 values, 223 windows) | obfuscated rerun of the Phase 3 baseline (D-19) |
  | `p3_2024_dated` | the same values with the ISO dates that were actually sent | as `p3_2024` | dated rerun and the published run's labels (D-19) |
  | `p4_2020` | the November 2025 Phase 4 input file (`batch_regime_20251120_104630.jsonl`), values verbatim, Day-T labels | SPY, 2020-01-02 to 2020-12-31 (252 values, 223 windows) | obfuscated rerun of the Phase 4 baseline (D-19) |
  | `p4_2020_dated` | the same values with the ISO dates that were actually sent | as `p4_2020` | dated rerun and the published run's labels (D-19) |

- Registry: all eleven keys are in `common.SERIES` since the contract of 2026-10-29. `call_only` was defined only in `01_build_series.py` before that, so `02_build_windows.py` rejected `--series call_only`; it is registered now and accepts it (re-run 2026-10-29: `--help` lists all eleven keys), so call-only windows can be built at no LLM cost. It is a raw-scan series like `new_ex0dte`: one raw scan per symbol-year, never between 21:50 and 22:45 UTC. Three fields of `common.Series` matter beyond the table: `calendar` (`master` or `self`, which decides rule A or J in D-06), `labels` (`obfuscated` or `dated`) and `scale` (`oi_notional` for the scaled series). The plain and `_dated` keys of one Phase 3/4 input hold the same rows (`01_build_series.py` parses them from the input file with `phase34_daily_series()`) and differ only in `labels`. The composite `intraday_t0` is a set of windows, not a series (D-08).
- Why: the published inputs are not today's data. From 2023-09-29 through 2025-12-31 (565 of 565 days) they equal the call leg of the chain only, 0DTE included, to within 0.005B; through 2023-09-28, 900 of 940 days equal today's full net GEX (calls and puts, 0DTE included), 39 scattered days (first: 2021-09-17) are also call-only, and one day (2022-05-31) matches nothing. The cause is upstream database issue #24: the loader labelled every contract `call` and the unique key discarded the put of each call and put pair (fixed 2026-02-03, raw table reloaded). The frozen archive was built on 2026-01-15 from the same put-less table, so it is put-less on those dates too (put GEX zero on 98 of 249 SPY days in 2023, 251 of 251 in 2024, 249 of 250 in 2025). It also has no QQQ or IWM rows for 2020-12-03 to 2025-12-30 and SPY holes on 2023-07-12, 2024-03-11 and 2026-01-02 to 2026-02-09 (latest date 2026-10-02), so it cannot serve as the bridge.
- Calendar: January's own calendar lacks two real trading days, 2023-07-12 and 2024-03-11, so 58 published windows span 31 trading days with one skipped. This is why `jan2026_phase4a` has its own window rule (rule J, D-06).
- Evidence (re-run 2026-10-28): the deterministic classifier reproduces the stored o4-mini labels on `jan2026_phase4a` (1,412 of 1,412 published labels; 1,476 of 1,476 answers once the 64 recovered ones are included). On `new_full` it gives 10.3% (2024) and 13.6% (2025) against the published 100% for both; on the call leg it gives 90.6% (2020) and 100% (2021 to 2025). Put-leg presence in `new_full` (read-only on `gex.options_daily_summary`): no SPY, QQQ or IWM day up to 2026-10-09 has a zero or missing put leg, and put GEX divided by call GEX in absolute value stays between 0.24 and 9.7 for SPY, 0.32 and 5.3 for QQQ, 0.19 and 12.6 for IWM. This is the put and call balance check that the forensic memo (s8, item 4) asks for before any run; it rules out the total put loss of #24, not a partial one. The full replay table is in design memo v2 s2 and in `detection_by_year.csv` (`05_report.py`).
- Encoded in: `SERIES`, `Series` and `ARCHIVE_DAILY_TABLE` in `common.py`; `load_phase4a_inputs()`, `phase4a_daily_series()`, `load_phase34_inputs()` and `phase34_daily_series()`.

### D-05 Bridge on the exact published inputs, agreement gate

- Date: 2026-10-28 (revised 2026-10-29: the reference is the published subset).
- Decision: the model-agreement bridge is `bridge_jan` (luna on the 1,476 January prompts), with the stored o4-mini answers as the reference (`r1_o4mini`, no LLM cost: 1,412 published answers plus 64 recovered from the raw output file and flagged `recovered_2026` in `detection_metadata`). `05_report.py` reports the reference twice: the published subset (the 1,412 answers without the flag) under the arm label `r1_o4mini`, which every headline number, the gate and the statistics use, and all 1,476 answers under `r1_o4mini_all`. The same pair of labels applies to the Phase 3/4 backfills (`r1_p3_o4mini`, `r1_p4_o4mini`, D-19) when they are present. `bridge_old` (luna on the frozen archive) stays in the registry as an optional priority-4 diagnostic.
- Gate: Cohen's kappa between luna and the stored o4-mini labels on `bridge_jan`, checked before the other arms run. Design memo v2 s5 expects kappa to be high, because both models track a deterministic rule, and says a low value would point at the model, not the data. The "about 0.6" threshold comes from the issue #261 checklist ("kappa >= ~0.6, otherwise discuss"); `05_report.py` carries it as `BRIDGE_GATE_MIN_KAPPA = 0.6`, a working default, and computes the gate on the published subset. The exact metric and threshold, and whether the gate runs on the published subset or on all 1,476 answers, are confirmed in Q-05.
- Why: see D-04. `bridge_jan` isolates the model change from the data change; the archive cannot, because it is put-less on the same dates and also differs in calendar and gamma. The published subset reproduces the published rates (12.2, 3.7, 32.4, 20.2, 100 and 100% for 2020 to 2025); the 64 answers recovered in 2026 are not part of the published result, so they are shown beside it, not inside it.
- Encoded in: `ARMS["bridge_jan"]`, `ARMS["r1_o4mini"]`, `ARMS["bridge_old"]`; `BRIDGE_GATE_MIN_KAPPA` in `05_report.py`.

### D-06 Window rules A, J and T0, and two hole detectors

- Date: 2026-10-28 (revised 2026-10-29: rule codes, the second detector, the threshold of 4 days).
- Decision: a window is 30 consecutive series rows (day T-29 to day T+0), one window per end date, shown to the model as "Day T-29" to "Day T+0" with no tickers. The two `_dated` Phase 3/4 series keep the ISO dates that were sent in November 2025 (`labels = 'dated'`, D-19). The stored `window_rule` is:
  - `A`: every series that follows the symbol's master calendar (`calendar = 'master'`): 30 consecutive rows of the series.
  - `J`: every series with its own calendar (`calendar = 'self'`: `jan2026_phase4a`, `p3_2024`, `p3_2024_dated`, `p4_2020`, `p4_2020_dated`): the series' own consecutive dates. Before anything is written the windows must reproduce the surviving batch input file, otherwise the build stops: the same window ends, dates and values, and the prompt that `common.build_prompt()` renders from them equal to the prompt in the file byte for byte (1,476 January windows; 223 windows for each of the November 2025 runs).
  - `T0`: the composite intraday windows (D-08).
  - `C`: reserved for a strict NYSE calendar, the audit's option C; no window carries it.
- Hole detectors: both are written to `window_metadata` for every rule, and a flagged window is kept, never dropped. `calendar_gap_days` is the widest gap in calendar days between neighbouring rows of the window; it counts as a hole when it exceeds `CALENDAR_GAP_FLAG_DAYS` = 4, because a gap of five or more days is never an ordinary holiday weekend. `missing_master_days` is the number of trading dates of the symbol's master calendar (its dates in `gex.options_daily_summary`) that lie inside the window but are not among its rows; it catches a skipped weekday that leaves no wide gap. `02_build_windows.py` reads the master calendar once per run, from the symbol's `new_full` series parquet or, with `--master-calendar db`, from `gex.options_daily_summary`. `gap_flag` is true when either detector fires.
- Why rule A: it is the Phase 4A convention (consecutive distinct trading dates of the table). On the new series it gives the same windows as the stricter audit option B (no hole against the symbol's master calendar): 4,671 SPY, 4,678 IWM and 3,867 QQQ windows. The audit's option letters are not the stored codes: the audit's option C, a strict NYSE calendar, would give 4,282 SPY windows and would drop windows that Phase 4A kept; the code `C` is reserved for it and the composite windows carry `T0`, so the audit's letters and the stored codes no longer clash.
- Why a threshold of 4: with 3 days the flag fired on 65% of the new-series windows (SPY 3,056 of 4,671, QQQ 2,515 of 3,867, IWM 3,077 of 4,678; re-run 2026-10-29) because every holiday long weekend is a 4-day gap. With 4 it fires on exactly 87 windows per symbol, all ending between 2012-10-31 and 2019-10-14: the 2012 Sandy closure, a hole in the data from 2017-08-24 to 2017-09-11 (SPY) or 2017-09-07 (QQQ and IWM), and the missing 2019-09-03. All 87 are kept; whether they stay in the extended history is Q-06.
- Why the second detector: January's calendar lacks 2023-07-12 (a Wednesday, a 2-day gap) and 2024-03-11 (a Monday, a 4-day gap: the size of any holiday weekend), so the calendar gap is silent on all 58 windows that span them. `missing_master_days` is positive on exactly those 58 of the 1,476 January windows and the calendar gap on none (re-run 2026-10-29). The master calendar is the symbol's own summary-table dates, not an exchange calendar: a session that is missing from both the series and the summary table is not detected, and the strict NYSE option that would is not used.
- Source: data audit of 2026-10-28 (window counts by rule, series and symbol); flag counts re-run 2026-10-29 from the stored series parquet.
- Encoded in: `WINDOW_RULE`, `WINDOW_RULE_COMPOSITE` and `CALENDAR_GAP_FLAG_DAYS` in `common.py`; in `02_build_windows.py`: `RULE_OWN_CALENDAR`, `RULE_COMPOSITE`, `consecutive_windows()`, `gap_metadata()`, `check_fidelity()`. The schema comment on `window_rule` lists A, J, T0 and C.

### D-07 Wording for 2026: post-publication period

- Date: 2026-10-28.
- Decision: windows ending in 2026 are called the "post-publication period" in the paper and in all report labels. They are not called "out-of-sample" or "OOS". Design memo v2 s9 (item 4) lists this wording among the points for the authors; it applies from now on. Which windows belong to the period (all window ends from 2026-01-01, or only windows lying wholly inside 2026) is Q-06.
- Why: luna was created on 2026-09-14 and its training cutoff is undocumented, so nothing shows the model has not seen that period; 173 of the 193 SPY window ends of 2026 (to 2026-10-09) precede the creation date (re-run 2026-10-29). The issue title and the arm table of 2026-10-27 still say "OOS" and "out-of-sample"; the paper must not.
- Encoded in: wording only (report labels, paper text); `POST_PUBLICATION_START` and `post_publication_2026.csv` in `05_report.py`.

### D-08 Intraday arm: composite windows, final_rush snapshot

- Date: 2026-10-28 (revised 2026-10-29: rule code `T0`, window series of the arm).
- Decision: the intraday check uses composite windows (`intraday_t0`, stored with `window_rule = 'T0'`): `new_full` values for days T-29 to T-1 and the `intraday_late` value at T+0. The intraday value is the `final_rush` snapshot (19:55:59 UTC), selected by `snapshot_type`, not by a UTC clock (daylight saving shifts the clock). Window ends (T+0) are no earlier than 2026-07-27; each window starts 29 trading days earlier, on end-of-day data. The irregular days 2026-07-29, 2026-08-03 and 2026-09-14 are excluded: they are dropped when the `intraday_late` series is built and again before windows are cut. At most 51 windows remain (54 intraday days from 2026-07-27 to 2026-10-09, minus these three). The arm `intraday_spy` keeps `series_key = intraday_late` on its runs and detections, while its windows are read from the composite `intraday_t0` (`common.arm_window_series()`).
- Why: equity intraday rows before 2026-07-25 carried the previous day's chain (upstream #64), so an all-intraday 30-day series would give very few windows (25 in the data audit; 5 if every day also needs a snapshot at or after 19:50 UTC). The `market_close` slot (20:00:59 UTC) equals the end-of-day row itself (identical on 51 of 54 days) and is not an independent observation; `final_rush` is the last independent late-session one.
- Encoded in: `INTRADAY_T0_KEY`, `INTRADAY_SNAPSHOT_TYPE`, `INTRADAY_START`, `INTRADAY_EXCLUDE_DAYS`, `WINDOW_RULE_COMPOSITE` and `arm_window_series()` in `common.py`; `composite_windows()` and `drop_irregular_intraday_days()` in `02_build_windows.py`.

### D-09 Test-retest: full repeat of bridge_jan

- Date: 2026-10-28 (revised 2026-10-29: `#rep1` keys, the duplicate sample is optional).
- Decision: `bridge_jan` is run twice. The 1,476 January prompts are sent a second time as a full repeat (1,476 more requests, about USD 0.44), so that run-to-run variation of the same model on identical input is measured and reported next to the luna versus o4-mini agreement (design memo v2 s5). The pass counts as test-retest only; the gate (D-05) uses the first pass.
- Mechanism: `generate --repeat-fraction F` requests round(F x n) of an arm's windows a second time, drawn from those that hold or are about to hold an original answer; `--repeat-fraction 1.0` on `bridge_jan` gives the full repeat. A repeat has the `custom_id` `<arm>|<symbol>|<window_end>#rep1` and is stored under the arm `<arm>#rep1`, because the natural key of the detections has no repeat index. The suffix is defined once in `common.py` (`REPEAT_MARK`, `REPEAT_ARM_SUFFIX`): `custom_id(..., repeat=1)` writes it, `parse_custom_id()` removes it, `custom_id_repeat()` reads the repeat index and `base_arm()` maps `bridge_jan#rep1` back to `bridge_jan`. `04_llm_runner.py` writes and `05_report.py` reads repeats through these functions, so the test-retest pairing depends on no second spelling. `REPEAT_FRACTION = 0.05` is the value of the optional duplicate sample for the other arms (Q-07); until Q-07 is answered those arms are run with `--repeat-fraction 0`.
- Why: the probe shows that identical requests do not return identical answers. Three repeats of one window at medium effort gave the same verdict each time but `sign_flips` of 9, 8 and 9 and `confidence` of 25, 20 and 15.
- Encoded in: `REPEAT_FRACTION`, `REPEAT_MARK`, `REPEAT_ARM_SUFFIX`, `custom_id()`, `parse_custom_id()`, `custom_id_repeat()` and `base_arm()` in `common.py`; the `--repeat-fraction` option of `04_llm_runner.py`.

### D-10 Budget hard stop

- Date: 2026-10-28 (revised 2026-10-29: Phase 3/4 and scaled arms, what counts as spend).
- Decision: the runner refuses to submit when the money already spent by this extension from the current balance (measured cost, or the projection for batches still in flight) plus the projected cost of the chunks to submit would exceed USD 12.00 (`BUDGET_USD_HARD_STOP`). Only runs for which `common.counts_toward_budget()` holds count: the live model (`gpt-6-luna`), an LLM arm and no backfill. The three published o4-mini runs that are backfilled for comparison (`r1_o4mini`, `r1_p3_o4mini`, `r1_p4_o4mini`) are listed separately and are never spend: at o4-mini Batch rates their usage is worth USD 7.90 (January, Phase 4A), USD 1.12 (November, Phase 3) and USD 0.94 (November, Phase 4). The runner also has `--budget` (the ceiling) and `--force` (an override); this log treats the hard stop as binding unless the authors say otherwise. Until a chunk is ingested the guard projects it at 1,911 prompt and 900 completion tokens (USD 0.3206 per 1,000 requests, USD 10.63 for the whole plan of 33,160 requests); the ledger then uses the measured usage.
- Plan and projection (Batch, medium effort; USD per 1,000 requests: 0.299 at the probe mean of 814 completion tokens, 0.375 at the mean plus two standard deviations):

  | priority | arms (requests) | requests | USD at 0.299 | USD at 0.375 |
  |---|---|---|---|---|
  | 1 | `bridge_jan` twice (2 x 1,476), `full_spy` (4,671), `ex0dte_spy` (4,671), the four `p34_*` arms (4 x 223 = 892) | 13,186 | 3.94 | 4.95 |
  | 2 | `full_qqq` (3,867), `full_iwm` (4,678), `full_qqq_scaled` (1,670), `full_iwm_scaled` (1,671) | 11,886 | 3.55 | 4.46 |
  | 3 | `ex0dte_qqq` (1,699), `ex0dte_iwm` (1,700), `intraday_spy` (at most 51) | 3,450 | 1.03 | 1.29 |
  | 4, optional | `bridge_old` (4,638) | 4,638 | 1.39 | 1.74 |
  | all | | 33,160 | 9.92 | 12.44 |
  | all, without the two scaled arms | | 29,819 | 8.92 | 11.18 |
  | all, without priority 4 | | 28,522 | 8.53 | 10.70 |

- Reading: priority 1 is 13,186 requests and about USD 3.9 (USD 4.95 at the upper figure): the 12,294 requests of design memo v2 (about 12,300, USD 3.68) plus the 892 Phase 3/4 rerun requests. Without the two scaled QQQ and IWM arms the whole plan is 29,819 requests (about 29.8k): USD 8.92 at the probe mean and USD 11.18 at the upper figure, which design memo v2 rounds to "about USD 11"; the hard stop leaves USD 0.82 above the upper figure. With the scaled arms (D-18) the plan is 33,160 requests: USD 9.92 at the probe mean and USD 12.44 at the upper figure, USD 0.44 above the hard stop. The whole plan reaches USD 12.00 at USD 0.362 per 1,000 requests, which is a mean completion length of about 1,065 tokens against 814 in the probe (12 medium-effort answers; the upper figure uses the spread of single answers, so it is conservative for a mean over thousands of requests). Priority 4 runs last, so the guard cuts `bridge_old` first if the measured cost is high; without it the plan is 28,522 requests (Q-03, Q-08). The key balance was USD 16.86 on 2026-10-28, so USD 4.86 of it lie outside the hard stop (the pilot and the 8,000-token retries count inside it). Without the bridge repeat the plan is 31,684 requests (USD 9.48 at the probe mean).
- Pilot: 40 windows balanced on the classifier verdict (20 detected, 20 not; `PILOT_WINDOWS`), synchronous at standard prices, about USD 0.024.
- Cost of one request: 1,911 prompt tokens times USD 0.05 per 1M plus 814 completion tokens times USD 0.25 per 1M.
- Encoded in: `BUDGET_USD_HARD_STOP`, `PILOT_WINDOWS`, `estimate_cost_usd()` and `counts_toward_budget()` in `common.py`; `check_budget()`, `run_cost()`, `PROJECTED_PROMPT_TOKENS` and `PROJECTED_COMPLETION_TOKENS` in `04_llm_runner.py`.

### D-11 Request mechanics

- Date: 2026-10-28.
- Decision: Batch jobs hold at most 1,500 requests (`BATCH_MAX_REQUESTS`), are submitted in priority order, and the completion window is 24 hours. Batch bodies accept no per-request metadata and no `service_tier`, so the keys travel in `custom_id` (`<arm>|<symbol>|<window_end>`; a test-retest repeat adds the suffix `#rep1`, D-09). `max_completion_tokens` is 4,000; a row that ends with `finish_reason == "length"` is retried once with 8,000 (`RETRY_MAX_COMPLETION_TOKENS`, the runner's `retry` subcommand).
- Why: reasoning tokens count against `max_completion_tokens`. In the probe a cap of 500 returned `finish_reason = length` with empty content, while the largest completion seen at medium effort was 1,224 tokens, so 4,000 leaves a wide margin.
- Encoded in: `BATCH_MAX_REQUESTS`, `BATCH_COMPLETION_WINDOW`, `MAX_COMPLETION_TOKENS`, `RETRY_MAX_COMPLETION_TOKENS`, `custom_id()`, `parse_custom_id()`.

### D-12 Fixed thresholds and primary label

- Date: 2026-10-28.
- Decision: the Paper 2 criteria stay fixed for every symbol and year: persistence of at least 21 of 30 days with the same sign, mean absolute GEX of at least USD 5B, at most 5 sign flips; USD 3B is the low-conviction floor. `regime_detected` is the primary outcome label. The four-way `regime_type` is a secondary outcome.
- Why: the thresholds are part of the published protocol and are written into the prompt text, so changing them is a protocol change; the scaled QQQ and IWM arms rescale the inputs, not the thresholds (D-18).
- Encoded in: `src/validation/regime_classifier.py`, `classifier()`, `classify()`, `classifier_version()`.

### D-13 Overlap-aware statistics

- Date: 2026-10-28.
- Decision: windows have stride 1, so consecutive windows share 29 of 30 days and are not independent. Every rate and p-value in the Electronics paper is reported with Wilson 95% confidence intervals, a calendar-quarter block bootstrap (2,000 draws, seed 261) and the same comparison on a non-overlapping 30-day subsample (design memo v2 s7). Earlier AIAI and JRFM p-values treated the windows as independent. The exact McNemar p-value on all stride-1 windows (`p_mcnemar_exact`) does the same and is reported only as the naive figure; the bootstrap p-value (`p_boot`) and the exact test on the non-overlapping subsample are separate quantities.
- Encoded in: `05_report.py` (`SEED`, `N_BOOT`, `quarter_ids()`, `nonoverlap_indices()`; options `--seed` and `--n-boot`; output `stats.yaml`).

### D-14 Storage and the database gate

- Date: 2026-10-28.
- Decision: results go to four new standalone tables and one view in schema `backups` (`gex_llm_regime_series`, `_windows`, `_runs`, `_detections`, `_rates_summary`), written only by the scripts in `scripts/validation/electronics/`. The archive tables `backups.*_pre_rebuild_20261004` are only read, in read-only sessions, and never written. The DDL is applied only after a documentation PR in gex-database-infrastructure (`docs/gex-llm-patterns/backup-schema.md`, branch `docs/gex-llm-regime-tables`, against `development`) and the maintainer's approval. Until then every writing script runs with `--parquet-only` or `--rollback` (a transaction that is always rolled back), and no `backups.gex_llm_regime_*` object exists (re-run 2026-10-29). The `runs` row is written at submit time, so the batch id is never lost (design memo v2 s6). Which copies go into git is D-17.
- Why: gex-database-infrastructure `docs/009_PROJECT_BACKUP_STRATEGY.md` (three copies: Postgres, parquet, raw JSONL; documentation before DDL; no foreign keys into core tables). The database maintainer relayed the same constraints on 2026-10-28.
- Encoded in: `sql/gex_llm_regime_schema.sql`, `T_SERIES`, `T_WINDOWS`, `T_RUNS`, `T_DETECTIONS`, `T_RATES_VIEW`, `parquet_path()`, `run_backup_dir()`.

### D-15 Scope and boundaries

- Date: 2026-10-28.
- Decision: symbols are SPY and IWM from 2008 and QQQ from 2011; every window ends on or before 2026-10-09. The index roots (SPX, XSP, NDX, RUT) are out of scope. The ex-0DTE and scaled QQQ and IWM arms start in 2020 (the scaling factor is fitted on 2020 to 2026-10-09, D-18), and the Phase 3/4 reruns cover SPY 2024 and 2020 only (D-19).
- Why: equity options moved from Alpha Vantage to Cboe delayed quotes on 2026-10-12, so later rows are a different source. The index roots hold about 70 days of data (SPX 71 days from 2026-07-20 to 2026-10-27, XSP 66, NDX and RUT 11; re-run 2026-10-28). Nothing here reads theta or vega, so the upstream unit change of 2026-11-03 (#157) does not matter. The database maintainer's "0.47x" figure is not reproduced and is not used (design memo v2 s3).
- Encoded in: `WINDOW_END_CAP`, `SYMBOL_START`.

### D-16 Reporting and figures

- Date: 2026-10-28.
- Decision: tables and figures are built only from the stored results (`docs/papers/electronics/results/`, written by `05_report.py`, and the parquet copies). Figure scripts raise an error when data is missing; there is no synthetic fallback. Each figure writes a provenance manifest (source files with sha256 and row counts, git sha, timestamp) next to the PNG. Figures are 6.14 in wide with 8 to 9 pt text, light theme, Unicode minus. The CSV files that `05_report.py` writes are the interface to the figures, in the long format as built, and the figure loaders read them as written: `detection_by_year.csv` (label_source, arm, arm_role, model, series_key, symbol, scope, year, n_windows, n_parsed, n, n_detect, rate_pct, ci_lo_pct, ci_hi_pct and further columns), `bridge_agreement.csv` (comparison, ref_arm, other_arm, the 2x2 counts n_pairs, n_ref_det_oth_det, n_ref_det_oth_not, n_ref_not_oth_det and n_ref_not_oth_not, agree_pct, kappa and further columns) and `series_comparison.csv` (series_a, series_b, symbol, scope, year, n_days, mean_abs_a_bn, mean_abs_b_bn, sign_agree_pct, exact_match_pct).
- Why: issue #261 (finding 5) records that earlier figure scripts fell back silently to synthetic data and that fig02 queried a column that does not exist.
- Encoded in: `docs/papers/electronics/figures/scripts/`; the CSV writers of `05_report.py`.

### D-17 Git policy for raw backups

- Date: 2026-10-28.
- Decision: the raw OpenAI batch files of a run (`input*.jsonl`, `output*.jsonl` and `errors*.jsonl` in `data/backups/gex_llm/<run_id>/`) and the series and windows parquet copies (`data/backups/gex_llm/tables/series/` and `tables/windows/`) stay on disk and are git-ignored. Tracked in git: each run's `manifest.json` and `batch_<k>.json`, the runs and detections parquet (`tables/runs/`, `tables/detections/`) and the report outputs in `docs/papers/electronics/results/`.
- Why: docs/009 asks for three copies of every result (Postgres, parquet, raw JSONL kept with the project). The raw JSONL is the verbatim record that round 1 did not keep, but it is bulky: the Phase 4A files are 9.9 MB (input) and 2.3 MB (output) for 1,476 requests, so the planned 33,160 requests come to roughly 270 MB. The manifests and the runs rows carry the file hashes (`input_sha256`, `output_sha256`), so tracked metadata detects any change to the files on disk.
- Evidence (re-run 2026-10-29, `git check-ignore`): the JSONL files and the `series/` and `windows/` parquet are ignored; `manifest.json`, `batch_<k>.json`, the `runs/` and `detections/` parquet and `docs/papers/electronics/results/` are not.
- Consequence: until the Postgres tables exist (D-14), the series and windows parquet are stored only on this machine's disk; Q-09 asks whether the large files should go under git-LFS.
- Encoded in: the `.gitignore` block headed "Electronics extension (issue #261)" (lines 310 to 318 of `.gitignore`, committed in e27bdc7), `run_backup_dir()`, `parquet_path()`.

### D-18 QQQ and IWM: run both the unscaled and a scaled variant

- Date: 2026-10-29. Decided by Chris; on 2026-10-28 (evening) he had asked for a disclosed per-symbol scaled variant next to the unscaled one. This closes Q-01.
- Decision: both variants run, as separate series and arms.
  1. Unscaled: `full_qqq` (QQQ from 2011) and `full_iwm` (IWM from 2008) on `new_full`, the fixed USD 5B criterion as published. This is the floor effect as it is (Evidence below).
  2. Scaled: `full_qqq_scaled` and `full_iwm_scaled` on the new series `new_full_scaled`, which starts on 2020-01-02, so the windows end from 2020-02-13 (1,670 QQQ and 1,671 IWM windows). The input series is multiplied by one fixed factor per symbol; the prompt text, the classifier and the thresholds stay unchanged (design memo v2 s9, item 2; option (b) of Q-01). The factor is the median over 2020-01-01 to 2026-10-09 of the daily ratio of SPY to the symbol in open-interest notional, `total_weighted_oi` x 100 x `underlying_price` from `gex.options_daily_summary`; the 100 cancels in the ratio. `01_build_series.py` stores it in the `series_metadata` of every row (`scale = 'oi_notional'`, `factor`, `n_days`).
  3. The scaled-threshold variant of the former Q-01 (b'), which would change the classifier and the prompt text, is not pursued.
- Factors (as stored in the `series_metadata` of the built series, equal to an independent read-only computation of 2026-10-29 from `gex.options_daily_summary`): QQQ 4.2247 over 1,699 days, IWM 11.4309 over 1,700 days. The factor uses open interest and prices only, never GEX values or labels.
- Disclosure: the scaled arms are a protocol change (the numbers shown to the model are not the stored dealer GEX of the symbol) and the paper says so, together with the factors. A single constant per symbol is crude: the daily ratio runs from 0.78 to 38.3 for QQQ (10th to 90th percentile 2.6 to 8.2) and from 1.5 to 110.6 for IWM (5.3 to 22.8).
- Why: the fixed USD 5B threshold is a floor for QQQ and IWM, so the unscaled arms can only show that the model also rejects every window; the scaled arms ask whether the pattern appears once the exposure is put on SPY's scale. Running both keeps the published criterion intact and shows what the criterion hides.
- Evidence (re-run 2026-10-29, `new_full`, every planned window, deterministic classifier): the fixed criteria give zero persistent windows for QQQ (0 of 3,867 windows, 2011 to 2026-10-09) and for IWM (0 of 4,678, 2008 to 2026-10-09); SPY has 606 of 4,671. The largest 30-day mean absolute GEX is USD 4.92B for QQQ and USD 4.98B for IWM, against a USD 5B requirement (SPY: USD 16.00B). For windows ending 2020-02-13 or later the medians are USD 2.16B (QQQ), USD 1.05B (IWM) and USD 5.81B (SPY). Persistence plus at most 5 flips alone would be met by 37.1% of QQQ windows and 71.8% of IWM windows (SPY: 37.7%), so the magnitude criterion is the binding one. With the classifier's own labels, QQQ windows end up as `transitional` (3,711) or `low_conviction` (156) and IWM windows almost all `transitional` (4,661 of 4,678). On the stored scaled windows (ends 2020-02-13 to 2026-10-09) the rule marks 350 of 1,670 QQQ windows (21.0%) and 901 of 1,671 IWM windows (53.9%) as persistent, against 276 of 1,671 (16.5%) for SPY on the same span and none for QQQ and IWM unscaled. One factor does not equalise the rates, and every IWM window ending in 2022 is persistent; Q-06 asks which variant leads the paper.
- Cost: the two scaled arms add 3,341 requests, USD 1.00 at the probe mean and USD 1.25 at the upper figure (D-10, Q-03).
- Encoded in: `Series.scale`, `SERIES["new_full_scaled"]`, `ARMS["full_qqq"]`, `ARMS["full_iwm"]`, `ARMS["full_qqq_scaled"]` and `ARMS["full_iwm_scaled"]` in `common.py`; `01_build_series.py --series new_full_scaled`.

### D-19 Phase 3/4 baselines: obfuscated-versus-dated rerun

- Date: 2026-10-29. Decided by Chris; the arm was asked for on 2026-10-28 (evening).
- Decision: the two November 2025 baseline runs behind the 81.2% versus 12.1% contrast (Phase 3: SPY 2024; Phase 4: SPY 2020; 223 windows each) are rerun with `gpt-6-luna` in four priority-1 arms, with the input values kept verbatim:

  | arm | series | labels in the prompt | windows |
  |---|---|---|---|
  | `p34_dated_2024` | `p3_2024_dated` | the ISO dates that were sent in November 2025 | 223 |
  | `p34_obf_2024` | `p3_2024` | Day T-29 to Day T+0 | 223 |
  | `p34_dated_2020` | `p4_2020_dated` | the ISO dates that were sent in November 2025 | 223 |
  | `p34_obf_2020` | `p4_2020` | Day T-29 to Day T+0 | 223 |

  That is 892 requests, about USD 0.27 at the probe mean (USD 0.33 at the upper figure). The published o4-mini answers of both runs are backfilled as the arms `r1_p3_o4mini` and `r1_p4_o4mini` (series `p3_2024_dated` and `p4_2020_dated`, model `o4-mini`, run ids `r1_p3_o4mini_20251120` and `r1_p4_o4mini_20251120`, batches `batch_691ea7f7b79481909f4667eaff640f26` and `batch_691f37d94ef0819099136e88a69bef82`); `03_backfill_round1.py` copies the two input and two output files into their backup directories with manifests, without an API call. For each of the two runs the comparison has three cells: o4-mini with dates (published), luna with dates and luna without. The date effect is luna dated against luna obfuscated; the model effect is o4-mini dated against luna dated.
- What is kept and what is not: the November 2025 series conventions stay as they were sent, so the rerun answers the date question and nothing else. The 2024 series is the gross call-plus-put magnitude without same-day expiries and with a negative sign imposed (negative on 242 of 252 days; the 10 positive days are backfilled placeholder rows), the 2020 series is magnitude-only (positive on all 252 days). The sign-convention effect is read from the corrected-data arms, where one signed convention covers every year (`full_spy`, which includes 2020 and 2024).
- Why: the second audit verified that the Phase 3 and Phase 4 prompts carried 30 calendar dates each (223 of 223 in both runs), although the papers describe the method as temporally obfuscated, and recommended either rerunning them obfuscated (about USD 1 to 2) or rewording; Chris chose the rerun. The windows use rule J (D-06): the dated prompts rebuilt by `common.obfuscate(values, dates, labels='dated')` and `common.build_prompt()` equal the November 2025 prompts byte for byte (223 of 223 in each run, re-run 2026-10-29), so the dated arms replay what was sent.
- Evidence (re-run 2026-10-29): the deterministic rule on the verbatim series detects 181 of 223 windows for 2024 (81.2%) and 27 of 223 for 2020 (12.1%), and the published o4-mini label equals the rule on 223 of 223 windows in each run. The model tracked its inputs here too, so a date effect, if there is one, has to come from luna.
- Encoded in: `PHASE34_FILES`, `PHASE3_BATCH_ID`, `PHASE4_BATCH_ID`, `load_phase34_inputs()`, `phase34_daily_series()`, `load_phase34_outputs()` and `obfuscate()` in `common.py`; `ARMS["p34_obf_2024"]`, `ARMS["p34_dated_2024"]`, `ARMS["p34_obf_2020"]`, `ARMS["p34_dated_2020"]`, `ARMS["r1_p3_o4mini"]` and `ARMS["r1_p4_o4mini"]`.

### D-20 Publication status and the correction route

- Date: 2026-10-29. Decided by Chris; instructions of 2026-10-28 (evening).
- Decision:
  1. The JRFM article is already published, so there is no hold request; what remains is a correction notice.
  2. The findings are made public now, not after the notices. The corrections page `docs/papers/CORRECTIONS.md` and the evidence in `planning/forensics/` are on the public branch `paper/electronics` (commit e27bdc7 of 2026-10-28, on `origin/paper/electronics`); the corrections are tracked in issue #262 ("Corrections to published results (IEEE BigData 2025, AIAI 2026, JRFM 2026) - tracking", opened 2026-10-28, open).
  3. Notices are in preparation for each venue: a corrigendum for AIAI 2026 (Springer LNCS), a correction for the JRFM article (MDPI), and a note for the IEEE BigData 2025 paper with a new version of arXiv 2512.17923. `CORRECTIONS.md` places the drafts in `docs/papers/corrections/`; that folder does not exist yet.
  4. The tone is factual and technical, because the repository and its issues are public.
- Why: academic integrity. Readers of the papers should not have to find the problems from the code (first paragraph of `CORRECTIONS.md`).
- Supersedes: design memo v2 s9 item 1 and the first form of Q-02, which assumed JRFM was in production and asked whether to request a hold. What the Electronics paper says and when the notices are sent is still open (Q-02).
- Encoded in: wording only (`docs/papers/CORRECTIONS.md`, issue #262).

### D-21 API keys: left as they are

- Date: 2026-10-29. Decided by Chris; instruction of 2026-10-28 (evening).
- Decision: the OpenAI API keys are left as they are; no rotation is planned. The scripts read the key through `common.load_openai_key()` (`OPEN_AI_KEY` in the git-ignored `config/config.json`, else the environment) and never print it. A fresh clone has no key, and the runner then stops with a message that names the file.
- Why: the key lives only in the git-ignored config file and in the environment of this machine. A search of the tracked files and of the new files under `docs/papers/electronics/` and `scripts/validation/electronics/` finds no key-shaped string (re-run 2026-10-29).
- Encoded in: `load_openai_key()` and `openai_client()` in `common.py`; `config/` in `.gitignore`.

### D-22 Pilot outcome and the batch submission of 2026-10-29

- Date: 2026-10-29.
- Pilot (D-10): 40 January windows balanced on the classifier verdict, synchronous, `pilot_bridge_jan_gpt-6-luna_sync_20261029T203454Z`: 40 of 40 answers parsed on the first strategy (no fallback), every `finish_reason` `stop`, verdict agreement 40/40 with the deterministic rule and 40/40 with the published o4-mini answers (kappa 1.00 on both), `regime_type` 35/40 (the five differences are `transitional` against `low_conviction` on windows neither side detects), reported metrics 40/40. Tokens: 1,913 prompt, completion mean 700 (max 1,063), reasoning mean 513. Cost USD 0.0217 at standard rates (USD 0.00054 per request); USD 0.27 per 1,000 requests at Batch rates, below the probe figure of 0.299 used in D-10. The gate of D-05 is passed on the pilot sample; the full `bridge_jan` pass decides.
- Submitted (Batch, `--parquet-only`, 2026-10-29 20:39 to 20:41 UTC), 26 chunks and 26,233 requests, projected USD 8.43 against the USD 12.00 stop:
  - priority 1: `bridge_jan` 1,476 + 1,476 full repeat (`--repeat-fraction 1.0`, D-09), `full_spy` 4,671 + 234, `ex0dte_spy` 4,671 + 234, `p34_obf_2024`, `p34_dated_2024`, `p34_obf_2020`, `p34_dated_2020` (223 + 11 each): 13,698 requests, USD 4.41 projected;
  - priority 2 and the intraday arm: `full_qqq` 3,867 + 193, `full_iwm` 4,678 + 234, `full_qqq_scaled` 1,670 + 84, `full_iwm_scaled` 1,671 + 84, `intraday_spy` 51 + 3: 12,535 requests, USD 4.02 projected.
- Q-07 applied as the runner's default: every arm other than `bridge_jan` carries the 5% duplicate sample (`#rep1`), 1,078 requests in all, about USD 0.30 at the pilot cost. The report pairs them as test-retest; the gate and every rate use the first pass only. D-09's sentence "until Q-07 is answered those arms are run with `--repeat-fraction 0`" is superseded by this entry: the sample was kept because its cost is marginal and the pairing is cheapest when it travels with the original batch.
- Deferred until the measured cost of the chunks above is in the ledger: `ex0dte_qqq` (1,699), `ex0dte_iwm` (1,700) and the optional `bridge_old` (4,638). Their deterministic replays are stored (`02_build_windows.py`), so the figures that need the rule need no LLM pass; the LLM passes are added if the ledger leaves room under the stop after priority 1 and 2 are ingested.
- Before submission the generated inputs were checked: the 2,952 `bridge_jan` requests carry messages byte-identical to `phase4a_postgresql_20260104_184832.jsonl`; `p34_dated_2024` and `p34_dated_2020` carry messages byte-identical to `phase3_full_2024_baseline_v2.jsonl` and `batch_regime_20251120_104630.jsonl` (234 of 234 each, repeats included); the obfuscated Phase 3/4 variants contain no ISO date; every body is `gpt-6-luna`, `reasoning_effort` medium, `max_completion_tokens` 4000, strict `json_schema`.
- Collection: `poll --wait` then `retrieve` then `ingest --parquet-only` per run; the Postgres load follows the database gate (D-14) through `ingest` without `--parquet-only`.
- Encoded in: the runs rows under `data/backups/gex_llm/tables/runs/` (batch ids, file ids, sha256 of every chunk) and `data/backups/gex_llm/<run_id>/batch_<k>.json`.

## 3. Open decisions for the authors

### Q-01 QQQ and IWM floor effect (closed)

- Closed 2026-10-29 by D-18. The options were: (a) report the floor effect as it stands; (b) a disclosed per-symbol scaling of the input series, with the prompt and the thresholds unchanged (design memo v2 s9, item 2); (b') a scaled-threshold variant, which changes the classifier and the prompt text; (c) drop or shrink the QQQ and IWM arms. D-18 runs (a) and (b) side by side; (b') and (c) are not pursued. The facts that framed the question (zero persistent windows for QQQ and IWM under the fixed USD 5B criterion) are in the Evidence of D-18.
- Left to Q-06: which of the two variants leads the paper.

### Q-02 Wording of the data defect, and the notices to the venues

- Fact: the published 2024 and 2025 detection rates (100% for both, 486 of 486 windows) rest on inputs that equal the call leg only (D-04); the same rule on the corrected series gives 10.3% and 13.6% (deterministic replay; no corrected LLM result exists yet). The "USD 5B to USD 23B, +360%" statement matches no stored series: the LLM-reported window means are 3.0, 4.9, 5.5, 9.6, 20.3 and 19.0 billion for 2020 to 2025 (research cache; JRFM Table 5), so 2021 to 2024 is +317% and 2020 to 2024 is +585%, and the 2024 and 2025 magnitudes are call-only in any case (`forensics/published_claim_inventory.md`, rows A27 to A30; second-audit memo, s5).
- Settled (D-20): JRFM is published, so there is no hold request; the findings are public in `docs/papers/CORRECTIONS.md` and tracked in issue #262; the notices are in preparation.
- Question: (a) what the Electronics paper says about the defect and where (introduction, data section, discussion), and how it cites the corrections page and the notices; (b) which notices go to which venue and when: a corrigendum for AIAI 2026 (Springer LNCS), a correction for the JRFM article (MDPI), and a note for the IEEE BigData 2025 paper with a new version of arXiv 2512.17923, and whether the Electronics submission waits for them; (c) the status of AIAI: the forensic memo and commit fd2f8d4 say "in press at Springer", design memo v2 says "published"; confirm with the proceedings contact what is still editable. Issue #260 stays open until (b) is decided.
- Scope: design memo v2 s9 asked for the second audit to finish first. It has (second-audit memo, 2026-10-28). Besides the put-row loss it verifies that the Phase 3 and Phase 4 prompts carried calendar dates, that the 81.2% versus 12.1% contrast rests on two sign conventions, that three figures are synthetic, and that phi is 0.692, not the 0.672 printed in AIAI. The caveat "do not repeat until verified" in design memo v2 s2 predates that audit.
- Framing: design memo v2 s1 frames the paper as a data-integrity correction with a controlled LLM re-test; that is the working framing and the authors confirm it.
- Needs: Chris and Dr. Xie.

### Q-03 Spend confirmation

- Question: after the 40-window pilot gives the measured cost per request, confirm spend for priority 2 (`full_qqq`, `full_iwm`, `full_qqq_scaled`, `full_iwm_scaled`), priority 3 (`ex0dte_qqq`, `ex0dte_iwm`, `intraday_spy`) and the optional priority 4 (`bridge_old`). Priority 1 (`bridge_jan` with its repeat, `full_spy`, `ex0dte_spy` and the four Phase 3/4 rerun arms) runs first and is 13,186 requests, about USD 3.9. The whole plan is 33,160 requests: USD 9.92 at the probe mean and USD 12.44 at the upper figure, against the USD 12.00 hard stop and the USD 16.86 balance (D-10). Without the two scaled arms the upper figure is USD 11.18 (29,819 requests); without priority 4 it is USD 10.70 (28,522 requests). If the pilot shows a higher cost, the options are to drop `bridge_old`, to shrink the scaled arms, or to raise the hard stop (USD 4.86 of the balance lie outside it).
- Needs: Chris, at the checkpoint after the pilot and the bridge gate. Dr. Xie approved the proposal on the earlier framing; the forensic memo (s8, item 5) recommends presenting the changed framing (Q-02) to him before the first paid batch.

### Q-04 Call-only diagnostic series

- Question: the series is registered and costs no LLM budget (D-04). Open: (a) whether the paper shows it, and where (main text as the mechanism behind the published 2024 and 2025 rates, or the appendix); (b) whether to add an LLM arm on it as a positive control that must reproduce the published 100% (suggested in the forensic memo, s8 item 3, as `call_only_spy`). Design memo v2 s5 lists no such arm and `common.ARMS` has none; it would be 1,671 SPY windows (ends from 2020-02-13), about USD 0.50 on Batch. Building the series needs one raw scan per symbol-year, run outside 21:50 to 22:45 UTC (see the `01_build_series.py` docstring).
- Needs: authors' decision; it is tied to Q-02.

### Q-05 Agreement gate details

- Question: fix, before the bridge result is seen: the agreement metric (Cohen's kappa on `regime_detected`, or on the four-way `regime_type`); the threshold (the issue #261 checklist says "about 0.6" and `05_report.py` carries 0.6; design memo v2 s5 sets no number and expects a high kappa); and what happens if the gate fails. The set of windows has a default in D-05: the gate runs on the 1,412 published answers and `05_report.py` shows the same comparison on all 1,476 beside it; say so if the 64 recovered answers should count instead.
- Needs: authors, before `bridge_jan` is submitted.

### Q-06 Primary analyses

- Question: which comparisons are primary (for example `new_full` against `new_ex0dte` by year for SPY, luna against o4-mini on `bridge_jan`, and luna dated against luna obfuscated on the Phase 3/4 baselines, D-19); whether the main text uses 2020 to 2026 for comparability with AIAI and JRFM with 2008 to 2019 as extended history; and which cross-asset variant leads the paper, the unscaled arms (the floor effect as the result) or the scaled arms (D-18), with the other in the appendix. The interval method is fixed (D-13). Also: the range of the post-publication period (D-07), either all window ends from 2026-01-01 (193 SPY windows to 2026-10-09, which is what `post_publication_2026.csv` holds) or only the windows lying wholly inside 2026 (ends from 2026-02-13, 164 windows, which is what the draft Results section describes; the report marks them with a flag); and whether the 87 windows per symbol that the calendar-gap detector flags (all before 2020, D-06) stay in the extended history or are excluded as a sensitivity check.
- Needs: authors, before `05_report.py` is run on full results.

### Q-07 Duplicate sample for the other arms

- Question: the full repeat of `bridge_jan` is decided (D-09). Add the optional 5% duplicate sample (`--repeat-fraction 0.05`, stored as the arm `<arm>#rep1`) to the other arms too? It would measure test-retest on the corrected series and on the Phase 3/4 inputs as well as on the January inputs: about 1,280 requests, about USD 0.38 for all other arms of priorities 1 to 3, or about 470 requests, about USD 0.14 for the two SPY arms only. Until it is answered those arms are run with `--repeat-fraction 0`.
- Needs: Chris; low stakes.

### Q-08 bridge_old

- Question: run the optional priority-4 arm or drop it. It is 4,638 SPY windows under rule A (the count the scripts produce) and 4,551 under the stricter audit option B, which design memo v2 gives as "about 4,550". The 87 windows that differ are the ones with a positive `missing_master_days` (D-06): they span the archive's holes at 2023-07-12, 2024-03-11 and 2026-01-02 to 2026-02-09, 29 windows each (re-run 2026-10-29). The cost is about USD 1.4 on Batch. The archive is put-less for the same dates as the January inputs, so it mostly repeats `bridge_jan` with a different calendar and a Black-Scholes gamma. Priority 4 runs last, so it is also the first arm the budget guard cuts (D-10, Q-03).
- Needs: authors, at the Q-03 checkpoint.

### Q-09 Large artefacts and git-LFS

- Question: keep the raw OpenAI batch files and the series and windows parquet on disk and git-ignored, as in D-17 (design memo v2 s9, item 3), or add git-LFS for them? Sizes: roughly 270 MB of raw JSONL for the planned 33,160 requests (the Phase 4A files are 9.9 MB and 2.3 MB for 1,476 requests; the three published runs together are about 16 MB). The figure loader (`figdata.Inputs.table`) can read the series and windows parquet, so on a fresh clone these files have to be rebuilt with `01_build_series.py` and `02_build_windows.py` (read-only queries, no LLM cost) or restored. The published batch files under `reports/validation/paper2_regime_windows/batch_jobs/` are git-ignored too, and the January OpenAI batch files have expired, so those files and their copies under `data/backups/gex_llm/` are the only exact record of what was sent; the tracked forensics folder keeps the extracted January series and the per-day comparisons. The forensic memo (s9, part D) asks for a durable copy. docs/009 puts the second and third copies "in project repo" (`data/backups/*.parquet` and `*.jsonl`); whether files on disk but outside git satisfy that is for the database maintainer to say.
- Default until decided: D-17 as it stands.
- Needs: Chris; the maintainer's reading of docs/009.

## 4. External gates (not author decisions)

- Documentation PR in gex-database-infrastructure and the maintainer's approval of the DDL. Until both happen the four tables and the view do not exist (no `backups.gex_llm_regime_*` object on 2026-10-29, re-run) and the writing scripts run with `--parquet-only` or `--rollback`.
- OpenAI key balance (USD 16.86 on 2026-10-28). Check the dashboard before any full batch.
- Operational rules for the shared database: raw-chain reads one symbol-year per statement with the index plan, in read-only sessions with a statement timeout of 600 s, and no raw scans or DDL between 21:50 and 22:45 UTC (the daily rebuild of the monitors). `common.in_quiet_window()` and `common.assert_not_quiet()` implement the time window: `01_build_series.py` applies it to raw scans and to database writes, `02_build_windows.py` and `04_llm_runner.py` to database writes (`--ignore-busy-window` overrides it).
- Python environment (design memo v2 s7): the shared AutoGex environment is used as it is, with `PYTHONNOUSERSITE=1` and `PYTHONPATH` set to the repository; nothing is installed or upgraded in it, because the production monitors share it.
- Commits and pushes on `paper/electronics` are allowed (Chris, 2026-10-28) and carry no attribution lines.
- Upstream constraints relayed by the database maintainer on 2026-10-28 (design memo v2 s10): never write the `*_pre_rebuild_20261004` archives; expect the rerun to differ from the published numbers; theta and vega units change on 2026-11-03 (#157) and nothing here reads them.
- Suggestions back to the maintainer, not blocking (design memo v2 s10): a put and call row-balance check in the load; annotate the `*_pre_rebuild_20261004` archives as put-less from 2023-10; confirm the symbols outside the #24 re-collection (upstream #69 says 72 of 108 were redone). The forensic memo (s9, part C) adds documenting the unlogged SQLite-to-PostgreSQL load step.

## 5. Relation to the design memo (v2 supersedes v1)

[00_design.md](00_design.md) is v2 (2026-10-28). It replaced v1 of the same day, which framed the frozen archive as the bridge to the published result and a gamma and 0DTE convention change as the cause. v2 absorbed everything the first draft of this log listed as changes to v1: the data-integrity framing, `jan2026_phase4a` as the bridge, `old_bs` as diagnostic, the `final_rush` snapshot, `bridge_jan` at priority 1 with the gate, and the probe numbers. So v1 is superseded and this log follows v2. Where it differs from v2 or goes beyond it:

- v2 s3 lists six series and v2 s5 an arm table without the Phase 3/4 and scaled arms; the registry now has eleven series and eighteen arms (D-04, D-18, D-19).
- v2 s5 gives priority 1 as about 12,300 requests (USD 3.7) and everything as about USD 11; with the 892 Phase 3/4 requests priority 1 is 13,186, and with the scaled QQQ and IWM arms the whole plan is 33,160 requests with an upper estimate of USD 12.44 (D-10, Q-03).
- v2 s5 gives `bridge_old` as about 4,550 windows (audit option B); the scripts produce 4,638 (rule A, Q-08).
- v2 s5 states no kappa threshold; the "about 0.6" is the issue checklist's (D-05, Q-05).
- v2 s4 flags a window "when a span covers a calendar gap > 3 days"; the contract flags a gap above 4 days and, separately, any missing master-calendar day, and it names the composite windows `T0` (D-06, D-08).
- v2 s1 and s9 call JRFM "in production"; it is published, so v2 s9 item 1 (a hold, a correction or a corrigendum) is overtaken by D-20 and what remains is Q-02. v2 s9 item 2 (QQQ and IWM) is decided in D-18, item 3 (git-LFS) is open as Q-09, and item 4 is D-07.
- v2 s5 says o4-mini is "retired on all endpoints"; what was observed is a 404 `model_not_found` on inference calls, while the model objects are still listed (D-01).
- v2 s2 holds back the figure and lineage findings until verified; the second audit has since verified them (Q-02). v2 s9 calls AIAI "published", the forensic memo "in press" (Q-02).

## 6. Change history

- 2026-10-28: first draft (D-01 to D-16, Q-01 to Q-08), written against design memo v1.
- 2026-10-28: second revision, reconciled with design memo v2 and the pipeline as built. The log had not been committed, so errors were corrected in place:
  - added D-17 (git policy for raw backups) and Q-09 (git-LFS), from v2 s6 and s9;
  - D-04 and Q-04: `call_only` is the sixth series; exact dates and counts for the put-less period (565 of 565, 900 of 940, 39, 2022-05-31); put-leg check on `new_full`; Q-04 reduced to where the paper shows it and whether an LLM positive control is added;
  - D-09 and Q-07: the full repeat of `bridge_jan` is the decision (v2 s5); the 5% duplicate sample is an optional mechanism;
  - D-10 and Q-03: request counts and costs follow v2 s5 (priority 1: 12,294 requests; whole plan: 28,927 requests, USD 8.65 to 10.85), with the headroom to the hard stop;
  - D-13 and Q-06: the interval method is fixed (quarter-block bootstrap), so the block length is no longer a question; Q-06 gained the range of the post-publication period and the 87 windows per symbol with long gaps;
  - Q-01: option (b) is v2's per-symbol scaling of the input series; the scaled-threshold variant is (b'); the floor effect is stated over every planned window, not only those from 2020;
  - D-05 and Q-05: the "about 0.6" threshold is attributed to the issue checklist, v2 only expects a high kappa;
  - D-06: stored rule `C` (composite) is distinct from the audit's option C (strict NYSE), and the gap-flag threshold is described as it behaves (65% of windows); D-08: window-end wording, exclusion of the three irregular days, the audit's wording for the 25 and 5 counts;
  - D-01: o4-mini wording (inference returns 404, the model objects are still listed), an unsourced remark about the model tier removed; D-03: `sign_flips` handling added; D-07 and D-15: sourced counts added;
  - Q-02: sources (claim inventory rows A27 to A30, second-audit memo), v2's three options, AIAI status wording, the framing now rests on v2 s1 (data-integrity correction) instead of the earlier convention framing; Q-08: rule A versus rule B counts;
  - section 4: items for the database maintainer and the operational rules added; section 5 rewritten (the table of changes to v1 is replaced by the differences from v2);
  - the dangling link to the pipeline README is resolved: the README now exists and is linked in the header; D-04 notes that `02_build_windows.py` cannot build call-only windows until `call_only` is registered.
- 2026-10-29: third revision, after the pipeline contract was updated and the authors' decisions of 2026-10-28 and 2026-10-29 were recorded. The log had not been committed, so errors were corrected in place:
  - added D-18 (QQQ and IWM, both variants; closes Q-01), D-19 (obfuscated-versus-dated rerun of the Phase 3/4 baselines), D-20 (JRFM published, findings public, correction route) and D-21 (API keys left as they are);
  - D-04: eleven registered series (`call_only` registered, `new_full_scaled`, four Phase 3/4 series) and the registry note about `call_only` replaced; D-05: the reference is the 1,412 published answers with all 1,476 reported beside them; D-06: rule codes A, J and T0 (the stored `C` is reserved), the second hole detector `missing_master_days`, the threshold of 4 days with re-run flag counts; D-08: `T0` and the window series of the arm; D-09: `#rep1` keys, the duplicate sample stated as optional; D-10: the 892 Phase 3/4 requests and the scaled arms, only money spent from the current balance counts; D-11: the `#rep1` suffix; D-13: the exact McNemar p-value versus the bootstrap; D-15: scope of the new arms; D-16: the long CSVs as the interface to the figures; D-17: the `.gitignore` block is committed (e27bdc7);
  - Q-01 closed; Q-02 reworded for the published JRFM (issue #262, `CORRECTIONS.md`); Q-03: new request counts and costs, the upper estimate above the hard stop; Q-04: `call_only` is registered; Q-05: the window set has a default; Q-06: the primary cross-asset variant; Q-07: `#rep1`; Q-08: `missing_master_days`; Q-09: sizes and the preservation argument;
  - section 4: the quiet-window functions and the commit policy; section 5: the differences from v2 brought up to date.
- 2026-10-29 (later): D-22 added (pilot outcome, the submission of priority 1 and 2 plus the intraday arm, Q-07 applied as the 5% default, the deferred arms); D-09's interim sentence on `--repeat-fraction 0` is superseded by D-22.
