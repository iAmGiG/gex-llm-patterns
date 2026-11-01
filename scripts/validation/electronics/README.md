# Electronics extension pipeline (gex-llm-patterns #261)

Scripts, SQL and conventions behind the extended Paper 2 study for the MDPI *Electronics* Special Issue
("Timely AI Advancements and Interdisciplinary Synergies for Intelligent Modeling").
Tracking issue: [iAmGiG/gex-llm-patterns#261](https://github.com/iAmGiG/gex-llm-patterns/issues/261)
(context: #260; upstream root cause: gex-database-infrastructure #24). Working branch: `paper/electronics`.

## 1. Purpose and at a glance

**Why this exists.** The exact inputs of the published Paper 2 Phase 4A run (SPY, o4-mini, batch of 2026-01-04) were
recovered from the surviving batch file and found to contain the call leg of dealer gamma exposure (GEX) only from
2023-09-29 on (565 of 565 days; upstream issue #24 dropped the put rows), so the published 100 % detection rate for
2024 and 2025 was measured on defective inputs. The Phase 3 and Phase 4 runs of November 2025 behind the
81.2 % versus 12.1 % contrast used dated prompts and two different sign conventions. The extension is therefore a
**re-run on the complete data with a controlled LLM re-test and a plain data statement** (the authors file no
correction notices and the paper does not present itself as a correction), and this folder is the machinery for it. The pipeline

1. recovers the exact inputs of the published runs (Phase 4A of January 2026; Phase 3 and Phase 4 of November 2025)
   and rebuilds the daily GEX series the extension needs;
2. cuts every series into 30-day windows and labels each window with the deterministic Paper 2 rule (no LLM, no cost);
3. backfills the published o4-mini answers as the arms `r1_o4mini`, `r1_p3_o4mini` and `r1_p4_o4mini` (no API call);
4. re-runs the test with `gpt-6-luna` through the OpenAI Batch API (o4-mini is retired on every endpoint), among
   others on the Phase 3/4 inputs with and without dates (the `p34_*` arms) and on the OI-notional-scaled QQQ and IWM
   series (the `*_scaled` arms); and
5. stores every input, label and answer, so that each number in the manuscript can be regenerated from stored tables.

Written against the scripts and the contract on 2026-10-29 and brought up to date on 2026-10-31 (HEAD `9088874` plus the working tree).
The `--help` of each script is authoritative for flags. Read
[00_design.md](../../../docs/papers/electronics/planning/00_design.md) for the reasoning,
[02_decisions_log.md](../../../docs/papers/electronics/planning/02_decisions_log.md) for decisions (D-nn) and open
questions (Q-nn), and this file for how to run things. `common.py` and `sql/gex_llm_regime_schema.sql` are the contract
between the scripts: every table, DataFrame and parquet file uses the column names of that SQL file.

> **State on 2026-10-31** (re-check with `00_env_check.py --require-tables` and `04_llm_runner.py status` instead of
> trusting this paragraph): the tables `backups.gex_llm_regime_*` exist (documentation PR #165 of the database
> repository merged and the schema applied by its maintainer on 2026-10-30 20:32 UTC) and hold the parquet copies
> (`07_load_tables.py`, 21:02 UTC: 38,936 series rows, 38,501 windows, 38 runs, 31,523 detections). All 18 arms were
> submitted (34 Batch chunks, 34,672 requests); 33 chunks are stored and the last QQQ ex-0DTE chunk is finishing.
> Re-run `07_load_tables.py` after every ingest, outside 21:50 to 22:57 UTC and outside market hours (weekdays
> 13:25 to 20:20 UTC; 14:25 to 21:20 UTC from 2026-11-02), the maintainer's windows. The bridge gate is passed
> (agreement 99.6 %, kappa 0.99 against the published o4-mini labels).

| Step | Script | Cost | Reads | Writes by default |
|------|--------|------|-------|-------------------|
| 0 | `00_env_check.py` | free (one `models.retrieve` unless `--skip-model-check`) | database (read-only session), Phase 4A files, research cache, OpenAI model object | nothing (`--write`: `docs/papers/electronics/results/env_check_<UTC stamp>.json`) |
| 1 | `01_build_series.py` | free | `gex.options_daily_summary`, raw chains, intraday summary, archive table (all read-only), the January and November batch files | `data/backups/gex_llm/tables/series/<series>_<symbol>.parquet` |
| 2 | `02_build_windows.py` | free | series parquet (or `--from-db`) | `data/backups/gex_llm/tables/windows/<series>_<symbol>.parquet` |
| 3 | `03_backfill_round1.py` | free | January and November batch files, `.cache/research_cache.db` (read-only), the Phase 3/4 result YAMLs | `r1_o4mini_phase4a_20260104/`, `r1_p3_o4mini_20251120/`, `r1_p4_o4mini_20251120/` and `tables/{runs,detections}/r1_*.parquet` |
| 4 | `04_llm_runner.py` | `pilot` and `submit` spend money, every other subcommand is free | windows parquet (or `--from-db`) | run directories and `tables/{runs,detections}/<run_id>_c<k>.parquet` |
| 5 | `05_report.py` | free | the four tables (parquet or Postgres) | `docs/papers/electronics/results/*.csv\|yaml` |
| 6 | `06_condense.py` | free | the parquet tables | `data/backups/gex_llm/condensed/{detections.csv.gz,windows.csv.gz,series_index.csv}` (the copies git tracks) |
| 7 | `07_load_tables.py` | free | the parquet tables | `backups.gex_llm_regime_{series,windows,runs,detections}` (upsert, ANALYZE; tables created 2026-10-30, PR #165) |

Later steps: figures (`docs/papers/electronics/figures/scripts/`) and the manuscript
(`docs/papers/electronics/build.sh`) read only what step 5 and the parquet copies hold.

To reproduce the free numbers of section 3.5 for the rows that need no raw scan (a minute or so, no spend, nothing
written to Postgres), after the environment block of section 2:

```bash
python $E/00_env_check.py
python $E/01_build_series.py --series jan2026_phase4a --symbol SPY   # reads raw dates: not 21:50-22:45 UTC
python $E/01_build_series.py --series new_full --symbol SPY
python $E/01_build_series.py --series old_bs --symbol SPY
for s in p3_2024 p3_2024_dated p4_2020 p4_2020_dated; do python $E/01_build_series.py --series $s --symbol SPY; done
for s in jan2026_phase4a new_full old_bs p3_2024 p3_2024_dated p4_2020 p4_2020_dated; do python $E/02_build_windows.py --series $s --symbol SPY; done
python $E/03_backfill_round1.py
```

The full list of series, arms and recipes is in sections 3 and 4.

---

## 2. Environment

```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
export PYTHONNOUSERSITE=1 PYTHONPATH=/mnt/bst/a100/yxie2/cregan1/gex-llm-patterns
cd /mnt/bst/a100/yxie2/cregan1/gex-llm-patterns
export E=scripts/validation/electronics        # shorthand used in the examples below
```

* Audited baseline (`00_env_check.py` warns when a version drifts): Python 3.12.12, numpy 2.4.0, pandas 2.3.3,
  pyarrow 23.0.0, psycopg2 2.9.11, openai 2.14.0, scipy 1.16.3, statsmodels 0.14.6, matplotlib 3.10.8, pyyaml 6.0.3.
* **Never install or upgrade packages.** The AutoGex env is shared with the production monitors. `json_repair` is
  deliberately absent (section 8).
* Database: PostgreSQL 18.1, database `gex_options` on `127.0.0.1`, user `cregan1` (trust authentication,
  `common.DB_PARAMS`). `psql` and `gh` exist only inside the AutoGex env.
* OpenAI key: `OPEN_AI_KEY` in `config/config.json`, else the environment variable `OPEN_AI_KEY` or `OPENAI_API_KEY`
  (`common.load_openai_key()`). `config/` is git-ignored. The key is never printed or logged; keep it out of shell
  history, command lines and pasted output.
* Run every script from the repository root as `python $E/<script>.py` (they import `common` from their own folder).
  The root is derived from the location of `common.py`, so a second checkout reads and writes its own `data/` and
  `config/`, and it needs its own copy of the git-ignored `config/`, of the January and November batch files in
  `reports/validation/paper2_regime_windows/batch_jobs/` and of `.cache/research_cache.db`.

---

## 3. Study design reference

### 3.1 Daily series (`common.SERIES`: 11 keys)

All values are net dealer gamma exposure in USD, calls positive and puts negative, unless the role says otherwise.
Row counts are as built on 2026-10-29.

| Key | Source | Symbols | Range (cap) | Role |
|-----|--------|---------|-------------|------|
| `jan2026_phase4a` | the January batch file `reports/validation/paper2_regime_windows/batch_jobs/phase4a_postgresql_20260104_184832.jsonl` (values printed at 0.01 B) | SPY | 2020-01-02 to 2025-12-31 (1,505 days = 1,476 windows + 29) | exact published inputs; the bridge; own calendar (rule J) |
| `old_bs` | archive `backups.options_daily_summary_pre_rebuild_20261004` (read-only; Black-Scholes gamma on integer DTE, same-day expiries zeroed) | SPY | 2008-01-02 to 2026-10-02 (4,667 days; lacks 2023-07-12, 2024-03-11 and 2026-01-02 to 2026-02-09) | diagnostic, optional arm `bridge_old` |
| `new_full` | `gex.options_daily_summary` after the 2026-10-08 rebuild (stored per-contract gamma, 0DTE included) | SPY, IWM, QQQ | SPY (4,700 days) and IWM (4,707) from 2008-01-02, QQQ (3,896) from 2011-03-23, all to 2026-10-09 | corrected primary series; also the master calendar of the hole detector |
| `new_ex0dte` | raw `gex.options_chains_partitioned` with `expiration > trading_date` | SPY, QQQ, IWM | as `new_full` | 0DTE ablation |
| `intraday_late` | `gex.intraday_gex_summary`, `snapshot_type = 'final_rush'` (19:55:59 UTC), one row per ET date | SPY | 2026-07-27 to 2026-10-09 (51 days; 2026-07-29, 2026-08-03 and 2026-09-14 excluded) | T+0 value of the composite windows `intraday_t0` |
| `call_only` | raw chains, call leg only, 0DTE included, put leg dropped | SPY | 2020-01-01 to 2026-10-09 (1,700 days) | diagnostic: reproduces the put-less January inputs from clean data; no LLM arm; `05_report.py` derives the same series in memory from `new_full.call_gex` when it is not stored |
| `new_full_scaled` | `new_full` of QQQ and IWM times one fixed factor per symbol: the median over 2020-01-01 to 2026-10-09 of the daily ratio SPY / symbol of open-interest notional (`total_weighted_oi * 100 * underlying_price` in `gex.options_daily_summary`) | QQQ (1,699 days), IWM (1,700) | 2020-01-02 to 2026-10-09 | cross-asset arms that make the fixed $5 B criterion reachable without touching the prompt (D-18, which closed Q-01); net, call and put GEX are scaled, `spot` is not |
| `p3_2024`, `p3_2024_dated` | the Nov-2025 Phase 3 input file `phase3_full_2024_baseline_v2.jsonl` | SPY | 2024-01-02 to 2024-12-31 (252 values = 223 windows + 29) | Phase 3 inputs as printed: gross call+put magnitude ex-0DTE with a negative sign imposed (242 of 252 values negative); identical rows under both keys |
| `p4_2020`, `p4_2020_dated` | the Nov-2025 Phase 4 input file `batch_regime_20251120_104630.jsonl` | SPY | 2020-01-02 to 2020-12-31 (252 values = 223 windows + 29) | Phase 4 inputs as printed: magnitude-only, positive on all 252 days; identical rows under both keys |

* The plain and the `_dated` key of one Nov-2025 phase hold the same 252 values. The key only decides how
  `02_build_windows.py` labels the days: `Day T-29` ... `Day T+0` for `p3_2024` and `p4_2020`, the ISO dates that the
  Nov-2025 prompts actually carried for `p3_2024_dated` and `p4_2020_dated` (`common.Series.labels`, recorded in
  `series_metadata.labels`). The second-audit memo explains why both conventions are kept
  (`planning/forensics/2026-10-28_memo_second_audit.md`, items 1 and 2).
* `new_full_scaled` stores the factor in every row's `series_metadata` (`scale = "oi_notional"`, `factor`, `n_days`):
  QQQ 4.2247 over 1,699 days, IWM 11.4309 over 1,700. The factor is computed over the whole registry range whatever
  dates a run builds, so a partial build carries the factor of a full one.
* Window ends never go past **2026-10-09**: equity options moved from Alpha Vantage to Cboe delayed quotes on
  2026-10-12. Index roots (SPX, XSP, NDX, RUT) have at most 70 days and are out of scope.
* `jan2026_phase4a`, `old_bs`, `intraday_late`, `call_only` and the four Nov-2025 keys are SPY only;
  `new_full_scaled` is QQQ and IWM only; `new_full` and `new_ex0dte` take all three symbols. `common.Series.symbols`
  lists what each key supports and the scripts reject the rest.

### 3.2 Windows, window rules and the deterministic label

* A window is 30 series rows, day T-29 to day T+0, one window per end date. The 30 values are shown to the model
  as `Day T-29` ... `Day T+0` with no dates and no ticker (`common.obfuscate`, labels `obfuscated`, the Phase 4A
  convention); the windows of `p3_2024_dated` and `p4_2020_dated` carry the ISO date of each day instead
  (`labels='dated'`, as in the Nov-2025 prompts). The stored `gex_sequence` is exactly what the runner sends.
* **Window rule** (`windows.window_rule`):
  * `A`: 30 consecutive rows of a series that follows the master calendar (`new_full`, `new_ex0dte`, `old_bs`,
    `call_only`, `new_full_scaled`). Nothing is dropped for a hole; the hole detectors below flag it.
  * `J`: 30 consecutive rows of a series with its own calendar (`common.Series.calendar == "self"`):
    `jan2026_phase4a`, `p3_2024`, `p3_2024_dated`, `p4_2020`, `p4_2020_dated`. Before anything is written the windows
    must reproduce the surviving batch input file (same `window_end` set, dates, values and, byte for byte, the
    prompt that `common.build_prompt()` renders from them), otherwise `FidelityError` (section 7).
  * `T0`: the composite `intraday_t0` (`--composite intraday_t0`): `new_full` for T-29 to T-1 plus the
    `intraday_late` value at T+0, one window per intraday day with 29 earlier `new_full` rows, stored under series
    key `intraday_t0`. `C` is reserved for a strict NYSE calendar and is not produced.
* **Hole detectors** (in `window_metadata`, every rule; flagged windows are kept, never dropped):
  `calendar_gap_days` is the widest calendar gap between neighbouring rows of the window; `missing_master_days`
  counts the trading dates of the symbol's master calendar (`gex.options_daily_summary`) that lie inside the window
  but are not among its rows, which catches a single skipped weekday that leaves no calendar gap. `gap_flag` is true
  when `calendar_gap_days` exceeds `common.CALENDAR_GAP_FLAG_DAYS` (4, so a plain holiday weekend never fires) or
  `missing_master_days` is above 0. Composite windows add `snapshot_timestamp`, `snapshot_type`, `t0_series` and
  `base_series`. As built: 87 windows per symbol of `new_full` are flagged by a gap of 5 days or more (storm closure
  2012-10, the data hole 2017-08-24 to 2017-09-11, the missing 2019-09-03), all ending before 2020; 58 windows of
  `jan2026_phase4a` are flagged by `missing_master_days = 1` (the January calendar lacks 2023-07-12 and 2024-03-11);
  `old_bs` has 174 flagged windows, the 87 of `new_full` plus its own holes.
* Label (`src/validation/regime_classifier.py`, thresholds fixed for every symbol and year): at least 21 of 30 days
  with the same sign, mean |GEX| of at least $5 B, at most 5 sign flips; $3 B is the low-conviction floor.
  `regime_detected` (model) and `clf_should_detect` (rule) are the primary labels, the four-way `regime_type` is
  secondary.

### 3.3 Arms (`common.ARMS`: 18 keys, 15 of them call a model)

An arm is one (series, symbol) combination sent to one model. Three arms are backfills of the published o4-mini
answers (`llm = False`, priority 0, never submitted). Window counts are as built on 2026-10-29; requests and cost use
the Batch figure of **$0.30 per 1,000 requests** (section 3.4) and leave out the 5 % test-retest sample (section 4,
step 4), which adds 5 % to every arm.

| Arm | Series (windows read from) | Symbol | Priority | Windows | Requests, cost | Purpose |
|-----|----------------------------|--------|----------|---------|----------------|---------|
| `r1_o4mini` | `jan2026_phase4a` | SPY | 0 (backfill) | 1,476 (1,412 published) | none | the published Phase 4A answers (o4-mini, January 2026) |
| `r1_p3_o4mini` | `p3_2024_dated` | SPY | 0 (backfill) | 223 | none | the published Phase 3 answers (o4-mini, 2025-11-20, dated prompts): 181 of 223 = 81.2 % |
| `r1_p4_o4mini` | `p4_2020_dated` | SPY | 0 (backfill) | 223 | none | the published Phase 4 answers (o4-mini, 2025-11-20, dated prompts): 27 of 223 = 12.1 % |
| `bridge_jan` | `jan2026_phase4a` | SPY | 1 | 1,476 | 1,476, $0.44 | gpt-6-luna on the identical inputs: model agreement with o4-mini (the gate) |
| `full_spy` | `new_full` | SPY | 1 | 4,671 | 4,671, $1.40 | corrected series, 2008 to 2026-10-09 |
| `ex0dte_spy` | `new_ex0dte` | SPY | 1 | 4,671 | 4,671, $1.40 | 0DTE ablation |
| `p34_dated_2024` | `p3_2024_dated` | SPY | 1 | 223 | 223, $0.07 | Phase 3 inputs with the dates actually sent (same prompts as `r1_p3_o4mini`, new model) |
| `p34_obf_2024` | `p3_2024` | SPY | 1 | 223 | 223, $0.07 | the same values with `Day T-k` labels (obfuscated rerun) |
| `p34_dated_2020` | `p4_2020_dated` | SPY | 1 | 223 | 223, $0.07 | Phase 4 inputs with the dates actually sent (same prompts as `r1_p4_o4mini`, new model) |
| `p34_obf_2020` | `p4_2020` | SPY | 1 | 223 | 223, $0.07 | the same values with `Day T-k` labels |
| `full_qqq` | `new_full` | QQQ | 2 | 3,867 | 3,867, $1.16 | cross-asset, unscaled (floor effect, section 3.5) |
| `full_iwm` | `new_full` | IWM | 2 | 4,678 | 4,678, $1.40 | cross-asset, unscaled (floor effect) |
| `full_qqq_scaled` | `new_full_scaled` | QQQ | 2 | 1,670 | 1,670, $0.50 | cross-asset, 2020 to 2026-10-09, OI-notional scaled |
| `full_iwm_scaled` | `new_full_scaled` | IWM | 2 | 1,671 | 1,671, $0.50 | cross-asset, 2020 to 2026-10-09, OI-notional scaled |
| `ex0dte_qqq` | `new_ex0dte` | QQQ | 3 | 1,699 (ends from 2020-01-01) | 1,699, $0.51 | 0DTE ablation, cross-asset |
| `ex0dte_iwm` | `new_ex0dte` | IWM | 3 | 1,700 (ends from 2020-01-01) | 1,700, $0.51 | 0DTE ablation, cross-asset |
| `intraday_spy` | `intraday_late` (windows `intraday_t0`) | SPY | 3 | 51 | 51, $0.02 | late-session snapshot against end of day |
| `bridge_old` | `old_bs` | SPY | 4 (optional) | 4,638 | 4,638, $1.39 | pre-rebuild convention, mostly repeats `bridge_jan` |

* **The Phase 3/4 rerun** is the four `p34_*` arms. Both `p34_dated_*` arms send the November prompts byte for byte
  (section 7), so they differ from `r1_p3_o4mini` and `r1_p4_o4mini` in the model and the strict answer format only;
  each `p34_obf_*` arm sends the same 30 values with `Day T-k` labels, so it differs from its dated twin in the labels
  only. Together they separate the effect of the model, of the dates and of the data in the 81.2 % versus 12.1 %
  contrast. Windows of 2024 and 2020 only (223 each); `p3_2024` is the gross, sign-imposed series and `p4_2020` the
  magnitude-only one, as printed.
* **The scaled arms** (`full_qqq_scaled`, `full_iwm_scaled`) read `new_full_scaled` and report under series key
  `new_full_scaled`; the prompt and the thresholds are unchanged, a disclosed protocol change (D-18). They never
  replace the unscaled arms `full_qqq` and `full_iwm`. The scaled series starts on 2020-01-02 (`Series.start`), so its
  first window ends on 2020-02-13 and the arms have 1,670 and 1,671 windows, 29 fewer than the 1,699 and 1,700 days
  of the series that `planning/02_decisions_log.md` (D-10, D-18) counts as requests.
* `intraday_spy` keeps `series_key = intraday_late` on its runs and detections while its windows are the composite
  `intraday_t0` windows (`common.arm_window_series`); 04 and 05 both resolve the windows that way.
* Priority 1 adds up to 11,710 requests ($3.51), priority 2 to 11,886 ($3.57), priority 3 to 3,450 ($1.04) and the
  optional priority 4 to 4,638 ($1.39): 31,684 requests and $9.51 for the whole registry. The 5 % sample adds about
  1,590 requests ($0.48); decision D-09's full repeat of `bridge_jan` (`--repeat-fraction 1.0`) is 1,476 requests
  ($0.44) instead of the sample's 74. The runner projects with 900 completion tokens ($0.32 per 1,000;
  $10.16 for the registry before repeats); at the mean-plus-two-standard-deviations figure ($0.375 per 1,000) the
  registry costs $11.88 and passes the $12.00 hard stop once repeats are added, so run in priority order and read
  `status` between arms. Priorities 2 and 3 wait for the authors (section 9).

### 3.4 Model configuration and cost (`common.py`)

| Field | Published runs (o4-mini) | Electronics runs |
|-------|--------------------------|------------------|
| model | `o4-mini`; Phase 4A answers report `o4-mini-2025-04-16`; the Nov-2025 requests asked for the alias `o4-mini` | `gpt-6-luna`: an alias with no dated snapshot; the model object's `created` time (2026-09-14T17:15:02Z) is stored in `runs.model_created_at` (`generate --online`, `submit`) |
| endpoint | Batch, `/v1/chat/completions` | same; completion window 24 h |
| prompt | `MechanicsPromptBuilder.build_regime_prompt`, `v2.0_postgresql`; dated labels in Phase 3/4 | unchanged; byte-identical on the 1,476 January windows and on the 223 + 223 Nov-2025 windows (section 7) |
| `reasoning_effort` | not sent (API default, medium) | `medium` |
| `max_completion_tokens` | not sent | 4,000; one retry at 8,000 for answers that end with `finish_reason = length` |
| `response_format` | free text (parsed afterwards; 64 of 1,476 Phase 4A answers were lost by the January ingestion) | strict `json_schema` with the nine Phase 4A fields: the one deliberate protocol change, disclosed in the paper |
| batch size | one file | chunks of at most 1,500 requests |

Cost, from the probe of 2026-10-28 (about 1,911 prompt and 814 completion tokens per request at medium effort):
**$0.30 per 1,000 Batch requests** ($0.05 per 1 M input tokens and $0.25 per 1 M output tokens; the standard API is
twice that, $0.60 per 1,000). The mean plus two standard deviations of the completion length gives $0.375 per 1,000.
The runner projects with 900 completion tokens, $0.32 per 1,000, until a run is ingested. The pilot of 2026-10-29
(40 synchronous calls, run `pilot_bridge_jan_gpt-6-luna_sync_20261029T203454Z_c0`) parsed 40 of 40 answers, used on
average 1,913 prompt and 700 completion tokens (maximum 1,063; every answer ended with `stop`) and cost $0.0217 at
standard rates, which is about $0.27 per 1,000 at Batch rates. The hard stop is **USD 12.00** in total
(`BUDGET_USD_HARD_STOP`); the key's balance was USD 16.86 on 2026-10-28, check the dashboard before any full batch.

**What counts as spend.** The ledger of `04_llm_runner.py` and the budget block of `cost_ledger.yaml` count a run only
when `common.counts_toward_budget(run)` is true: the model is `gpt-6-luna`, the arm is a registered LLM arm (not a
backfill) and `run_metadata` carries no `backfill` key. The three backfills are history, priced at o4-mini batch rates
for the record and never charged to the current balance: January o4-mini $7.90, November Phase 3 $1.12 and Phase 4
$0.94. `status` marks their rows with `*` and lists them on a line starting "outside the budget"; `cost_ledger.yaml`
reports them under `budget.not_spend` (`historical_backfill_usd`). Pilot rows (synchronous, standard rates) and
retries do count.

### 3.5 Expected result of the free replay

Share of windows labelled persistent by the deterministic rule (no LLM), by calendar year of `window_end`. The SPY
rows use the windows ending 2020-02-13 to 2025-12-31, the span of the published run. Counts in brackets.

| Series | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|--------|------|------|------|------|------|------|
| Published o4-mini answers (`r1_o4mini`, the 1,412 published windows) | 12.2 (26/213) | 3.7 (9/241) | 32.4 (79/244) | 20.2 (46/228) | 100 (241/241) | 100 (245/245) |
| January inputs, rule applied (`jan2026_phase4a`) | 12.1 (27/223) | 4.0 (10/252) | 32.3 (81/251) | 19.3 (48/249) | 100 (251/251) | 100 (250/250) |
| Call leg only, 0DTE included (`call_only`) | 90.6 (202/223) | 100 (252/252) | 100 (251/251) | 100 (250/250) | 100 (252/252) | 100 (250/250) |
| Pre-rebuild archive (`old_bs`) | 9.0 (20/223) | 3.6 (9/252) | 26.3 (66/251) | 22.5 (56/249) | 100 (251/251) | 100 (250/250) |
| Rebuilt, 0DTE included (`new_full`) | 12.1 (27/223) | 3.6 (9/252) | 40.6 (102/251) | 22.4 (56/250) | 10.3 (26/252) | 13.6 (34/250) |
| Rebuilt, 0DTE excluded (`new_ex0dte`) | 2.7 (6/223) | 0.0 (0/252) | 36.7 (92/251) | 25.2 (63/250) | 13.1 (33/252) | 16.4 (41/250) |

The other series (rule applied; every window of the series; the 2026 windows end to 2026-10-09):

| Series | Windows | Persistent |
|--------|---------|------------|
| Phase 3 inputs (`p3_2024`, `p3_2024_dated`), 2024 | 223 | 181 = 81.2 %, the published `r1_p3_o4mini` count |
| Phase 4 inputs (`p4_2020`, `p4_2020_dated`), 2020 | 223 | 27 = 12.1 %, the published `r1_p4_o4mini` count |
| QQQ and IWM, `new_full` and `new_ex0dte`, 2011 or 2008 to 2026 | 3,867 and 4,678 | 0 |
| QQQ, `new_full_scaled`, 2020 to 2026 | 1,670 | 350 = 21.0 %; by year 0.0, 23.4, 60.6, 16.8, 6.4, 20.4 (2020 to 2025), 15.5 (2026) |
| IWM, `new_full_scaled`, 2020 to 2026 | 1,671 | 901 = 53.9 %; by year 9.9, 65.5, 100, 79.2, 20.6, 50.8 (2020 to 2025), 44.6 (2026) |
| SPY, composite `intraday_t0`, 2026-07-27 to 2026-10-09 | 51 | 0 |

How to read it (details and evidence: `planning/00_design.md` section 2 and `planning/forensics/`):

* From 2023-09-29 to 2025-12-31 the January inputs equal the call leg alone (565 of 565 days within 0.005 B); before
  that they equal today's full net GEX on 900 of 940 days (39 scattered days are call-only, the first on 2021-09-17;
  2022-05-31 matches neither). The raw table the January run read had lost the put rows of the 604 SPY dates written
  through a faulty loader, where `option_type` defaulted to `call` (upstream gex-database-infrastructure #24, fixed and
  reloaded on 2026-02-03); that set contains every day from 2023-09-29 on. The archive was built from that same table,
  so it is also put-less there.
* The o4-mini verdict (`regime_detected`) equals the deterministic rule on every parsed window of all three published
  runs (1,476 of 1,476; 223 of 223; 223 of 223); the four-way `regime_type` on 1,232, 181 and 64 of them. The model
  tracked its inputs. The 81.2 % against 12.1 % contrast was produced on a gross, sign-imposed 2024 series and a
  magnitude-only 2020 series, both with dates in the prompt (second-audit memo, items 1 and 2); the `p34_*` arms test
  it again.
* QQQ and IWM have a floor effect. With the fixed $5 B threshold no window is persistent in any year: 0 of 3,867 QQQ
  windows and 0 of 4,678 IWM windows (606 of 4,671 for SPY); the largest 30-day mean |GEX| is $4.92 B for QQQ and
  $4.98 B for IWM, against $16.00 B for SPY. This is a property of the classifier, not a model result (D-18 runs the
  unscaled and the scaled arms side by side); `05_report.py` lists it under `diagnostics.floor_effect`. The scaled
  series lifts the floor by construction, and one factor per symbol does not equalise the rates.
* A row that does not reproduce means the source data changed. Stop and find out why before running anything that costs
  money.

---

## 4. Running the pipeline

Run the steps in order. Steps 0 to 3 and 5 are free and can be repeated at any time: parquet writes are upserts on the
natural key. In step 4 only `pilot` and `submit` spend money. Every script accepts `-h`; the `--help` text is
authoritative for flags. Steps 1 to 3 write parquet by default; the database path exists only behind `--db` and
`--rollback` (section 5.4).

### Step 0. Environment check

```bash
python $E/00_env_check.py                  # prints the report, exit 0 = no blocker, 1 = blocker
python $E/00_env_check.py --write          # also stores results/env_check_<UTC stamp>.json
python $E/00_env_check.py --require-tables  # missing backups.gex_llm_regime_* objects become a blocker
python $E/00_env_check.py --skip-model-check
```

Run it first, before every paid step, and after any change to the environment. It reports the interpreter, the
user-site status, package versions and where each was loaded from, a parquet round trip, the git commits of this
repository and of `gex-database-infrastructure`, database coverage (`gex.options_daily_summary` per symbol), whether the
source table of every database-backed series is readable (the archive and `call_only` are optional) and whether the four
tables and the view exist, whether a key is configured (never its value), whether `gpt-6-luna` is served
(`models.retrieve`, free), the sha256 of the Phase 4A files and the research cache, whether today's prompt builder
rebuilds all 1,476 published Phase 4A prompts byte for byte, and the classifier thresholds. Blockers: a missing package,
an unreadable source table, no key, a Phase 4A file that differs from its audited digest, prompt drift, wrong
thresholds, an unwritable output folder (and, with `--require-tables`, absent tables). Warnings: version drift, an
active user site, `json_repair` being importable, data ending before the window cap. It does not look at the
November-2025 Phase 3/4 files: their fidelity is checked by steps 2 and 3 (section 7).

### Step 1. Daily series

```bash
python $E/01_build_series.py --series new_full --symbol SPY                 # also QQQ, IWM; its parquet is the master calendar of step 2
python $E/01_build_series.py --series jan2026_phase4a --symbol SPY
python $E/01_build_series.py --series old_bs --symbol SPY                   # archive, read-only session
python $E/01_build_series.py --series intraday_late --symbol SPY
python $E/01_build_series.py --series new_ex0dte --symbol SPY               # raw scan, section 6; also QQQ, IWM
python $E/01_build_series.py --series call_only --symbol SPY                # raw scan, section 6
python $E/01_build_series.py --series new_full_scaled --symbol QQQ          # also IWM; prints the OI-notional factor
python $E/01_build_series.py --series p3_2024 --symbol SPY                  # also p3_2024_dated, p4_2020, p4_2020_dated
python $E/01_build_series.py --series new_ex0dte --symbol QQQ --years 2024 2025 --rollback
```

* At most one of `--parquet-only` (the default when no mode is given), `--db`, `--rollback` (section 5.4). The parquet
  file `tables/series/<series>_<symbol>.parquet` is written in all three modes.
* `--years`, `--start` and `--end` build a part of a series; the run replaces only its own dates in the parquet file.
  Requests beyond a series' range or cap are clipped with a warning. A partial file is not a series: step 2 refuses a
  series parquet that stops more than a week before the last window it should support.
* `new_full`, `old_bs`, `intraday_late` and `new_full_scaled` finish in about a second. `new_ex0dte` and `call_only`
  scan the raw chains one symbol-year per statement (0.7 to 2.0 s per SPY year when they were built on 2026-10-29).
  `jan2026_phase4a` reads about 90 days of raw trading dates to date the first 29 values, so it counts as a raw read
  too. The four Nov-2025 keys read their batch file and one master-calendar query; they build in seconds.
* Every row records its provenance in `series_metadata` (builder, SQL hash or input-file hash, planner setting, git sha,
  label style). A day with contracts that expired before the trading date is flagged there. The Nov-2025 series keep the
  printed values verbatim (0.01 B precision, no sign correction) and record the count of negative and positive values
  and the batch id; `new_full_scaled` records `scale`, `factor`, `n_days` and the ratio quantiles.
* `new_full` is stored as float4, so it equals `new_ex0dte` plus `gex_0dte` to about 1e-7 of the day's gross exposure.

### Step 2. Windows and deterministic labels

```bash
python $E/02_build_windows.py --series jan2026_phase4a --symbol SPY       # rule J, fidelity check against the January file
python $E/02_build_windows.py --series new_full --symbol SPY              # rule A; also QQQ, IWM
python $E/02_build_windows.py --series new_ex0dte --symbol SPY            # also QQQ, IWM
python $E/02_build_windows.py --series old_bs --symbol SPY
python $E/02_build_windows.py --series call_only --symbol SPY
python $E/02_build_windows.py --series p3_2024_dated --symbol SPY         # rule J, dated labels; also p3_2024, p4_2020, p4_2020_dated
python $E/02_build_windows.py --series new_full_scaled --symbol QQQ       # also IWM
python $E/02_build_windows.py --composite intraday_t0 --symbol SPY        # rule T0, needs new_full and intraday_late
python $E/02_build_windows.py --series new_full --symbol SPY --end-min 2024-01-01 --end-max 2024-12-31
python $E/02_build_windows.py --series new_full --symbol SPY --rollback   # database test, writes nothing
```

* Output: `tables/windows/<series>_<symbol>.parquet` with the columns of `backups.gex_llm_regime_windows`
  (`gex_sequence` and `window_metadata` as JSON text, `input_sha256` = sha256 of the stored sequence). A partial build
  replaces the windows in its range and keeps the rest; a file written by an earlier version of the script (whose
  `window_metadata` lacks `missing_master_days`) is refused instead of mixed. The composite windows are stored under the
  series key `intraday_t0` (`tables/windows/intraday_t0_SPY.parquet`).
* The script prints the detection rate by `window_end` year, with the hole counts (`cal_gap`, `missing_master`,
  `gap_flagged`). On `new_full` SPY it must show 4,671 windows, 10.3 % for 2024 and 13.6 % for 2025; on
  `jan2026_phase4a` 1,476 windows, 100 % for 2024 and 2025 and 58 gap-flagged windows (section 3.5).
* The master calendar of the hole detector is read once per run from the `new_full` series parquet of the symbol (run
  step 1 for `new_full` first); `--master-calendar db` reads `gex.options_daily_summary` instead (the default with
  `--from-db`). It must cover every window, otherwise the run stops.
* `--from-db` reads the series from Postgres instead of parquet and needs the tables. `--parquet-root DIR` moves the
  series input and the windows output to another root (for rehearsals). `intraday_late` alone is refused: it has no
  30-row windows, use `--composite intraday_t0`.

### Step 3. Backfill of the published runs

```bash
python $E/03_backfill_round1.py                          # all three arms: verify, then write backups and parquet copies
python $E/03_backfill_round1.py --dry-run                # parse, cross-check, report; writes nothing
python $E/03_backfill_round1.py --arm r1_p3_o4mini --arm r1_p4_o4mini
python $E/03_backfill_round1.py --rollback               # database test; no files
```

Three OpenAI Batch runs of Paper 2 kept their raw output next to their input but not a usable record of the answers.
Step 3 rebuilds each as an arm from the batch output itself, with no API call:

| Arm | Run | Batch | Windows | Published record |
|-----|-----|-------|---------|------------------|
| `r1_o4mini` | `r1_o4mini_phase4a_20260104` | `batch_695ab77d2fe8819084e397a55f10e6bc` | 1,476 (ends 2020-02-13 to 2025-12-31) | the SQLite ResearchCache `.cache/research_cache.db` (pattern `regime_30day`): 1,412 answers, 12.2 / 3.7 / 32.4 / 20.2 / 100 / 100 % for 2020 to 2025 |
| `r1_p3_o4mini` | `r1_p3_o4mini_20251120` | `batch_691ea7f7b79481909f4667eaff640f26` | 223 (2024-02-13 to 2024-12-31) | `reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml`: 181 of 223 = 81.2 % |
| `r1_p4_o4mini` | `r1_p4_o4mini_20251120` | `batch_691f37d94ef0819099136e88a69bef82` | 223 (2020-02-13 to 2020-12-31) | `.../phase4_baseline_2020.yaml`: 27 of 223 = 12.1 % |

For every arm the script parses all output lines with `common.parse_llm_content` (`parse_status` `ok` 445 and
`fallback` 1,031 for January, `ok` 59 and `fallback` 164 for Phase 3, `ok` 87 and `fallback` 136 for Phase 4; one January
answer, 2023-08-07, is wrapped in a markdown fence and holds a raw control character, so it is read leniently, stored as
`fallback` with `detection_metadata.lenient_json`, and logs the expected warning `All JSON parsing strategies failed.
Last error: Invalid control character`), cross-checks every field against the published record (1,412 of 1,412 cached
windows agree on every field; 223 of 223 YAML windows agree on the verdict and 220 of 220 on the other fields for
Phase 4), rebuilds the prompt of every request with `common.build_prompt` and compares it with the recorded request
text (1,476 of 1,476, 223 of 223 and 223 of 223 identical), and **refuses to write anything for any arm** unless the
published yearly rates are reproduced (and, for the November runs, the headline counts 181 of 223 and 27 of 223).
Windows the January ingestion lost are kept and flagged `detection_metadata = {"recovered_2026": true}` (64 windows,
all in `r1_o4mini`); three Phase 4 answers wrote the confidence as a word, were recorded as parse errors in November
and are read by the shared parser (verdict not detected). Published set of `r1_o4mini`:

```sql
WHERE arm = 'r1_o4mini' AND detection_metadata ->> 'recovered_2026' IS NULL
```

In the parquet copy (JSON columns are text) the same filter is
`d[~d.detection_metadata.fillna("").str.contains("recovered_2026")]`; it leaves 1,412 rows. The two November arms have no
recovered rows, so every row is published.

Modes (at most one): the default and `--parquet-only` copy each arm's two batch files to
`data/backups/gex_llm/<run_id>/` (`input.jsonl`, `output.jsonl`, `manifest.json` with sha256 and original paths) and
write `tables/detections/<arm>.parquet` (1,476 / 223 / 223 rows) and `tables/runs/<arm>.parquet` (1 row each, with
`created_at`, which `04_llm_runner.py` orders runs by and survives without); `--dry-run` only reports; `--rollback`
loads the rows into a transaction that is rolled back, writes no file and refuses to run in the quiet window; `--db`
writes the files and then upserts. `--arm` (repeatable) limits the run to some arms, `--backup-root DIR` moves the
outputs. The `model` of the rows is `o4-mini-2025-04-16` for `r1_o4mini` and the alias `o4-mini` (what the November
requests asked for) for the other two; `prompt_version` is `v2.0_postgresql` for all three. The OpenAI files of the
January batch have expired; for all three batches the local copies are the record. The estimated cost of each run
(January $7.90, Phase 3 $1.12, Phase 4 $0.94 at o4-mini batch rates) is stored for the record and is never counted as
spend (section 3.4).

### Step 4. LLM runner

`04_llm_runner.py` has nine subcommands. Run `python $E/04_llm_runner.py <command> --help` for the options. Every
command takes the storage flags `--parquet-only` (never connect to Postgres), `--rollback` (section 5.4),
`--backup-root DIR` (run directories and parquet copies, and the windows, live under that folder: use it to rehearse
without touching the shared tree) and `--ignore-busy-window`. The arms it accepts are the 15 with `llm = True`.

| Command | Does | Cost |
|---------|------|------|
| `pilot --arm A` | synchronous calls on a sample balanced on the classifier verdict; recorded and ingested like a run | spends (standard rates) |
| `generate --arm A` | selects windows, writes the Batch input chunks and `generated` runs rows | free, no network |
| `submit --run-id R` | uploads each chunk and creates its Batch job | spends |
| `poll --run-id R [--wait]` | refreshes batch status and usage | free |
| `retrieve --run-id R` | downloads output and error files verbatim | free |
| `ingest --run-id R` | parses answers into detections and updates the run rows; idempotent | free |
| `requeue [--run-id R] [--wait]` | sends chunks that the Batch API rejected at validation (enqueued-token quota) again, with the same files; `--wait` retries every `--interval` seconds (default 300) for up to `--max-hours` (24) | spends, like `submit` |
| `retry --run-id R` | new run for answers cut off by the token limit, at 8,000 tokens | free until submitted |
| `status` | runs, cost ledger, per-arm window state | free |

Typical sequence for one arm:

```bash
python $E/04_llm_runner.py pilot --arm bridge_jan                      # 40 windows, about $0.02 (standard rates)
python $E/04_llm_runner.py generate --arm bridge_jan --repeat-fraction 1.0   # D-09: every January window twice
export RUN_ID=<the id on the last line printed: RUN_ID=bridge_jan_gpt-6-luna_batch_<UTC stamp>>
python $E/04_llm_runner.py submit --run-id $RUN_ID --dry-run           # ledger check and plan, nothing is called
python $E/04_llm_runner.py submit --run-id $RUN_ID                     # spends money
python $E/04_llm_runner.py poll --run-id $RUN_ID --wait                # default 60 s between polls
python $E/04_llm_runner.py retrieve --run-id $RUN_ID
python $E/04_llm_runner.py ingest --run-id $RUN_ID
python $E/04_llm_runner.py retry --run-id $RUN_ID                      # only if ingest reports "retry pending N"
python $E/04_llm_runner.py status
```

**Selecting windows (`generate`).** The pool is the arm's windows in its date range (`--end-min`, `--end-max`), read from
`tables/windows/<window series>_<symbol>.parquet` (`--from-db`: from Postgres), where the window series is
`common.arm_window_series(arm)`. Windows that already have a parsed answer that was not cut off are skipped
(`--include-done` overrides), windows whose answer was cut off wait for `retry`, windows that a generated, submitted or
not yet ingested run already holds are skipped and logged (`--include-inflight` overrides), and the rest, including
windows whose answer could not be parsed, are requested. `--limit N` takes the first N windows, or with
`--sample stratified` N spread over calendar years in proportion to their size, picked by a reproducible hash rank
(`--seed`, default 261). `--repeat-fraction F` (default `common.REPEAT_FRACTION` = 0.05; 0 turns it off and logs a
warning; `1.0` repeats every window, which is decision D-09's full second pass of `bridge_jan`) adds `round(F x n)`
windows a second time for test-retest, topping up to the target so that running `generate` again never adds a second
batch of repeats. Whether the other arms carry the 5 % sample is Q-07 (section 10, item 3). `--online` records the
model object's created time (one free `models.retrieve`).

**Request format.** One line per window: the unchanged Phase 4A prompt in a chat-completions body with
`reasoning_effort = medium`, `max_completion_tokens = 4000` and the strict JSON schema (body keys `model`, `messages`,
`max_completion_tokens`, `reasoning_effort`, `response_format`). Batch bodies accept no per-request metadata and no
`service_tier`, so the keys travel in `custom_id`: `<arm>|<symbol>|<window_end>`, with `#rep1` appended for a
test-retest duplicate. A duplicate is stored under arm `<arm>#rep1` (`common.REPEAT_ARM_SUFFIX`, 40 characters are
enough), because the detections natural key has no repeat index. `common.custom_id(..., repeat=1)`,
`common.parse_custom_id`, `common.custom_id_repeat` and `common.base_arm` are the one definition; 04 writes the labels,
05 reads them, and `05_report.py --check-conventions` fails if the two ever disagree. The prompts of the dated arms are
the November prompts byte for byte; the prompts of `bridge_jan` are the January prompts byte for byte (section 7).

**Chunking.** A run is split into near-equal contiguous chunks of at most 1,500 requests (`--chunk-size`, the size
shown to be accepted by the Batch endpoint). With D-09's full repeat `bridge_jan` is 2 x 1,476 = 2,952 requests, two
chunks of 1,476 (projected $0.95); with the 5 % sample it is 1,476 + 74 = 1,550 requests, two chunks of 775
(projected $0.50). `full_spy` with the sample is 4,671 + 234 = 4,905 requests, four chunks of 1,226 or 1,227
(projected $1.57), without it four chunks of 1,167 or 1,168 (projected $1.50). With the sample the four `p34_*` arms are
223 + 11 = 234 requests each, one chunk (projected $0.075), and `full_qqq_scaled` and `full_iwm_scaled` are 1,754 and
1,755 requests, two chunks (projected $0.56 each). Each chunk is one Batch job and one `runs` row with `run_id`
`<arm>_gpt-6-luna_batch_<UTC stamp>_c<k>`. Commands taking `--run-id` accept the parent id (all chunks) or one chunk id.

**Capacity: submit in waves.** The organization's enqueued-token limit for `gpt-6-luna` is 20,000,000 tokens (batch
error `token_limit_exceeded`: `Enqueued token limit reached for gpt-6-luna ... Limit: 20,000,000 enqueued tokens. Please
try again once some in_progress batches have been completed.`). `submit` does not know the limit: the API accepts the
batch, which then ends `failed` without any cost. On 2026-10-29 this happened to all eleven chunks of `full_qqq`,
`full_iwm`, `full_qqq_scaled` and `full_iwm_scaled`, created while 14 priority-1 chunks (13,698 requests of about 1,900
input tokens) were still queued; `intraday_spy` (54 requests), created last, was accepted and completed. Such a chunk is
unchanged on disk: `requeue` sends it again (a new batch for the same `input_<k>.jsonl`, the rejected batch id kept in
`run_metadata.superseded_batches`) and with `--wait` keeps trying until the queue has room. Submit one arm or one wave of
arms at a time and `poll --wait` between them (section 6).

**Budget guard.** `submit` and `pilot` add the projection of what they are about to spend to the ledger and refuse when
the total would exceed `--budget` (default USD 12.00). The message reads `... = $X against a budget of $12.00 --
refusing (raise --budget or pass --force)`. `--force` goes ahead anyway and needs the authors' approval. The ledger sums
the cost of every run for which `common.counts_toward_budget` holds (section 3.4): the measured `est_cost_usd` once the
batch has finished (replaced by the per-request sums at `ingest`), the projection while a batch is in flight, the
completed share for an expired or cancelled batch, and zero for a `generated` run. `status` prints it and lists the
three o4-mini backfills apart, as "outside the budget ... never counted"; they are history, not spend. Always
`submit --dry-run` first.

**Double requests.** `generate` and `retry` skip windows that a generated, submitted or not yet ingested run already
holds (`--include-inflight` overrides), and `submit` refuses a chunk that repeats a request that was already sent or
answered (`... repeat earlier work, e.g. ... -- refusing (pass --force to send them anyway)`). Only ingested answers
count as done, so ingest a run before generating the next one for the same arm. The backfilled runs (`r1_*`) are not
runner runs: `submit`, `poll`, `retrieve`, `ingest` and `retry` refuse them (`... was not made by this script`).

**Recovery.** `submit` records each chunk's batch id the moment the batch exists and adopts a batch that an earlier,
interrupted submit already created (it searches the batches' `run_id` metadata), so repeating it is safe. Input files
are uploaded with a 30-day expiry; the local `input_<k>.jsonl` and the verbatim output are the durable record, and
`ingest` needs the local input file to find unanswered windows. `ingest` can be repeated at any time: it upserts on
the natural key, and re-ingesting after the tables exist loads an earlier parquet-only run into Postgres. A batch that
ends `failed`, `expired` or `cancelled` is retrieved and ingested like any other: answered windows are stored, the
rest stay open (`parse_status = missing`) and the next `generate --arm A` requests exactly those. A batch that failed
before it ran (no output and no error file, for example `token_limit_exceeded`) costs nothing and stays in `status` as a
`failed` row; send it again with `requeue`. If the chunk files are gone, `generate --arm A` requests the open windows
again instead, because a failed batch without files frees its windows; use one of the two ways for a given chunk, not
both, or its windows are requested twice.

**Retry on length.** Reasoning tokens count against `max_completion_tokens` (in the probe a cap of 500 returned
`finish_reason = length` with empty content). An answer that ends with `finish_reason = length` is stored with
`detection_metadata.retry_at = 8000` and its window is left in state `retry`, whatever its `parse_status` says.
`retry --run-id R` writes a new run with the same `custom_id`s at 8,000 tokens (all else identical); submit, poll,
retrieve and ingest it like any run. The new answer replaces the cut-off one on the natural key. At medium effort the
largest completion in the probe was 1,224 tokens, so retries should be rare.

**Gate order for the arms.**

1. `pilot --arm bridge_jan` prints the parse rate, token use, cost per request and, against the classifier and against
   the o4-mini answers in the January output file, the verdict agreement and Cohen's kappa. Pilot rows are stored under
   arm `pilot_bridge_jan`, so they never make a window done.
2. Run `bridge_jan` in full (decision D-09: `generate --arm bridge_jan --repeat-fraction 1.0` sends every January window
   twice, 2,952 requests in two chunks of 1,476, projected $0.95), then run
   `05_report.py --only bridge_agreement`. `bridge_agreement.yaml` holds the gate: Cohen's kappa on
   `regime_detected` between gpt-6-luna and the 1,412 published o4-mini answers, threshold 0.6. A low value would point
   at the model, not the data. The exact metric, window set and threshold are still open (Q-05); fix them before the
   result is seen.
3. With the authors' go: `full_spy`, `ex0dte_spy` and the four `p34_*` arms (priority 1), then priorities 2 and 3 after
   Q-03, then optionally `bridge_old`, in waves that fit the enqueued-token limit. Whether the arms other than
   `bridge_jan` carry the 5 % sample (the runner's default) or none (`--repeat-fraction 0`) is Q-07; decide it before
   the first `generate` of each arm (section 10).

**Files of a run** (`data/backups/gex_llm/<run_id>/`, `<run_id>` without the `_c<k>` suffix): `input_<k>.jsonl`,
`output_<k>.jsonl`, `errors_<k>.jsonl` (verbatim OpenAI files), `batch_<k>.json` (the batch object), `manifest.json`
(selection, package versions, git sha, sha256 of `04_llm_runner.py` and `common.py`, projection basis). The run row of
each chunk also goes to `tables/runs/<run_id>_c<k>.parquet` and its detections to
`tables/detections/<run_id>_c<k>.parquet`. Run status moves `generated`, `submitted`, `in_progress`, then
`completed`, `failed`, `expired` or `cancelled`, then `ingested`.

### Step 5. Report

```bash
python $E/05_report.py                        # auto: Postgres if all four tables exist, else the parquet copies
python $E/05_report.py --source parquet
python $E/05_report.py --only stats cost_ledger
python $E/05_report.py --source parquet --parquet-root /tmp/t/tables --results-dir /tmp/t/results   # test data
python $E/05_report.py --check-conventions    # do 05, common.py and 04 agree on the repeat labels?
```

Nothing is written to Postgres, and nothing is invented: a section whose inputs are absent is skipped with a warning.
Each section deletes its previous output files before it runs (or is skipped), so the results folder never mixes fresh
and old numbers; with `--only`, the files of the sections that are not rerun stay on disk and `report.yaml` lists each
under `files` as `carried_over` with a `stale` flag. A non-default `--parquet-root` requires an explicit
`--results-dir`, which keeps test data out of the paper results. Exit status: 0 = at least one section written and none
failed, 1 = a section failed, 2 = nothing was produced (no section wrote a file, or the tables could not be opened at all:
a `--parquet-root` that does not exist, an unreadable parquet file, `--source db` without the four tables; these stop at
once with an error message).
Section names (for `--only`): `detection_by_year`, `bridge_agreement`, `series_comparison`, `ex0dte_decomposition`,
`post_publication_2026`, `intraday`, `stats`, `cost_ledger`, `disagreements`, `llm_parse_stats`, `reported_vs_computed`.

### Step 6. Figures and manuscript

Figure scripts live in `docs/papers/electronics/figures/scripts/` (twelve `figNN_*.py`, the runner `run_all.py` and the
shared `theme.py`, `figdata.py` and `figllm.py`). They read only `results/*.csv|yaml` and the parquet copies and have no
synthetic fallback: a missing file, column or series stops the figure with a message naming it (exit status 1, nothing
written). A figure writes `<fig>.png` (300 dpi), `<fig>.pdf` and a provenance manifest `<fig>.json` to
`figures/output/`; `--results-dir`, `--tables-dir` and `--output-dir` redirect the three folders, for example to a
rehearsal tree. `python docs/papers/electronics/figures/scripts/run_all.py [--list | --check | fig04 fig10 ...]` lists,
checks or builds them. The manuscript builds with `docs/papers/electronics/build.sh [--strict]` (MDPI Electronics class;
pdflatex, bibtex, pdflatex, pdflatex); see `docs/papers/electronics/README.md`.

### Recipes

Each recipe assumes the environment block of section 2. Commands that spend are marked.

**A. Free replay (no spend; nothing written to Postgres).** Series, windows, backfills and report for everything that
needs no model call:

```bash
for s in new_full jan2026_phase4a old_bs intraday_late call_only new_ex0dte; do python $E/01_build_series.py --series $s --symbol SPY; done  # call_only and new_ex0dte: raw scans, not 21:50-22:45 UTC
for s in new_full new_ex0dte; do for y in QQQ IWM; do python $E/01_build_series.py --series $s --symbol $y; done; done
for y in QQQ IWM; do python $E/01_build_series.py --series new_full_scaled --symbol $y; done
for s in p3_2024 p3_2024_dated p4_2020 p4_2020_dated; do python $E/01_build_series.py --series $s --symbol SPY; done
for s in jan2026_phase4a new_full new_ex0dte old_bs call_only p3_2024 p3_2024_dated p4_2020 p4_2020_dated; do python $E/02_build_windows.py --series $s --symbol SPY; done
for s in new_full new_ex0dte new_full_scaled; do for y in QQQ IWM; do python $E/02_build_windows.py --series $s --symbol $y; done; done   # new_full_scaled: QQQ and IWM only
python $E/02_build_windows.py --composite intraday_t0 --symbol SPY
python $E/03_backfill_round1.py
python $E/05_report.py --source parquet
```

**B. Bridge and gate (spends about $0.45 to $0.95, depending on the repeat).** `pilot --arm bridge_jan` (about $0.02),
then the typical sequence of step 4 for `bridge_jan` with `--repeat-fraction 1.0`, then
`05_report.py --only bridge_agreement`; `bridge_agreement.yaml` holds the gate.

**C. Phase 3/4 rerun (spends about $0.27 for the four arms, $0.28 with the 5 % sample).** The inputs, windows and
backfills are free:

```bash
python $E/01_build_series.py --series new_full --symbol SPY         # its parquet is the master calendar of the hole detector
for s in p3_2024 p3_2024_dated p4_2020 p4_2020_dated; do
  python $E/01_build_series.py --series $s --symbol SPY
  python $E/02_build_windows.py --series $s --symbol SPY           # rule J: fails unless it reproduces the November batch file
done
python $E/03_backfill_round1.py --arm r1_p3_o4mini --arm r1_p4_o4mini
python $E/04_llm_runner.py generate --arm p34_dated_2024           # 223 windows (+ 11 repeats with the 5 % sample); free
python $E/04_llm_runner.py submit --run-id <RUN_ID printed above> --dry-run
python $E/04_llm_runner.py submit --run-id <RUN_ID printed above>  # spends, about $0.07
```

Repeat the last three lines for `p34_obf_2024`, `p34_dated_2020` and `p34_obf_2020`; the four arms fit into one wave
(892 requests). Then `poll --wait`, `retrieve` and `ingest` each run id. In `detection_by_year.csv` the rows for series
`p3_2024_dated`, `p3_2024`, `p4_2020_dated` and `p4_2020` give the rates of `r1_p3_o4mini`/`r1_p4_o4mini` (o4-mini,
dated), `p34_dated_*` (luna, dated) and `p34_obf_*` (luna, `Day T-k` labels). `bridge_agreement.csv` pairs each
`p34_dated_*` arm with its o4-mini backfill (comparison `bridge`: the model effect on identical prompts), and
`stats.yaml` holds the label contrasts (`series_contrast`, family `label`: `p34_obf_*` against `p34_dated_*`, the date
effect) and the Phase 3 against Phase 4 contrasts (`phase_contrast`) for the rule, o4-mini and luna.

**D. Scaled cross-asset arms (spends about $0.50 per arm; waits for Q-03).**

```bash
python $E/01_build_series.py --series new_full_scaled --symbol QQQ     # prints: oi_notional factor 4.2247... = median of 1699 daily SPY/QQQ ratios
python $E/02_build_windows.py --series new_full_scaled --symbol QQQ    # 1,670 windows; IWM: 1,671
python $E/04_llm_runner.py generate --arm full_qqq_scaled              # then submit, poll, retrieve, ingest as in step 4
```

The unscaled `full_qqq` and `full_iwm` stay separate arms: the scaling is a disclosed protocol change and never
replaces them (D-18).

**E. Intraday check (about $0.02).** `01 ... intraday_late`, `02 --composite intraday_t0`, `04 generate --arm intraday_spy`
(51 windows, plus 3 repeats with the 5 % sample).

---

## 5. Outputs, storage and the database gate

### 5.1 Results (`docs/papers/electronics/results/`, written by `05_report.py`)

The long schemas below are authoritative (they are what `docs/papers/electronics/figures/scripts/figdata.py` reads);
rates are percentages, intervals are Wilson 95 %, and `n_indep_30d` counts non-overlapping 30-day windows.

| File | Content (key columns) |
|------|------------------------|
| `detection_by_year.csv` | LONG: one row per classifier (series, symbol, year) and per LLM (arm, model, series, symbol, year) plus `scope = all`. `label_source` (classifier or llm), `arm`, `arm_role` (primary, backfill, backfill_all, repeat, pilot, other), `model`, `series_key`, `symbol`, `scope`, `year`, `n_windows`, `n_parsed`, `n`, `n_detect`, `rate_pct`, `ci_lo_pct`, `ci_hi_pct`, `n_indep_30d`, `mean_abs_gex_bn`, `n_compared`, `clf_rate_matched_pct`, `agree_pct`, `kappa`, `metrics_agree_pct`, `sign_flips_exact_pct`, `median_ratio_reported_to_computed`. Arm `r1_o4mini` is the published subset (1,412 windows); `r1_o4mini_all` adds the 64 recovered windows (an `_all` variant of `r1_p3_o4mini` or `r1_p4_o4mini` would exist only if some of their rows carried the flag) |
| `detection_by_year_wide.csv` | derived copy of the yearly rows in the shape of the written spec (rates as fractions); no figure reads it |
| `bridge_agreement.csv`, `.yaml` | published o4-mini arms against the luna arms that read the same series: `comparison` (`bridge`, `bridge_incl_recovered`, `test_retest`), `ref_arm`, `other_arm`, `series_key`, `symbol`, `scope`, `year`, the 2x2 counts `n_pairs`, `n_ref_det_oth_det`, `n_ref_det_oth_not`, `n_ref_not_oth_det`, `n_ref_not_oth_not`, `agree_pct`, `kappa` with bootstrap intervals, McNemar and bootstrap p-values. The gate (`r1_o4mini` against `bridge_jan`, kappa on `regime_detected`, threshold 0.6, `met = null` when kappa is undefined) is in the yaml. `r1_p3_o4mini` / `r1_p4_o4mini` are compared with `p34_dated_2024` / `p34_dated_2020`; test-retest compares `<arm>` with `<arm>#rep1` |
| `series_comparison.csv` | per series pair (`series_a`, `series_b`, `pair`), symbol and year: `n_days`, `mean_abs_a_bn`, `mean_abs_b_bn`, `sign_agree_pct`, `exact_match_pct` |
| `ex0dte_decomposition.csv` | `new_full` against `new_ex0dte` by year and the 0DTE share of net GEX |
| `post_publication_2026.csv`, `post_publication_2026_summary.csv` | per-window classifier and LLM labels for windows ending in 2026 (with `window_start`, `entirely_2026`), and their rates under both definitions of the period |
| `intraday.csv` | `intraday_t0` windows against `new_full` on the same `window_end` |
| `disagreements.csv`, `llm_parse_stats.csv`, `reported_vs_computed.csv` | every parsed answer whose verdict differs from the rule; parse and finish-reason counts and token use per arm; model-reported over computed mean \|GEX\| |
| `stats.yaml` | overlap-aware inference: rates by label source and period, series, label (`p3_2024` against `p3_2024_dated`, `p4_2020` against `p4_2020_dated`) and scale (`new_full_scaled` against `new_full`) contrasts, period shifts, Phase 3 against Phase 4, and the headline contrasts |
| `cost_ledger.csv`, `.yaml` | spend per run, arm and model, reconciled with per-request token use; `budget` counts only runs with `common.counts_toward_budget`, the three o4-mini backfills sit under `not_spend` |
| `report.yaml` | row counts, input fingerprint, script and git sha, warnings, caveats, classifier diagnostics (floor effect, scaling, flagged windows), headline numbers |
| `env_check_<UTC stamp>.json` | `00_env_check.py --write` |

Windows have stride 1, so consecutive windows share 29 of 30 days and the Wilson intervals are too narrow. Every
p-value is therefore reported next to a calendar-quarter block bootstrap (2,000 draws, seed 261) and the same
comparison on a non-overlapping 30-day subsample (decision D-13). Windows ending in 2026 are called the
**post-publication period**, never out-of-sample: `gpt-6-luna` was created on 2026-09-14 and its training cutoff is
undocumented (D-07). For fixed inputs every file but `report.yaml` is byte-identical between runs.

### 5.2 What gets stored

Four tables and one view in schema `backups`, named per the database repository's `docs/009_PROJECT_BACKUP_STRATEGY.md`
(`backups.<project>_<purpose>`, no foreign keys into core tables, every column commented). The DDL is
`sql/gex_llm_regime_schema.sql`: idempotent, schema-qualified, with the cleanup statements in its header.

| Object | One row per | Written by |
|--------|-------------|------------|
| `backups.gex_llm_regime_series` | (`series_key`, `symbol`, `trading_date`): the number shown to the model | 01 |
| `backups.gex_llm_regime_windows` | (`series_key`, `symbol`, `window_end`): the 30-day input as sent (labels `Day T-29` ... `Day T+0`, or ISO dates for the `_dated` series), its sha256 and the deterministic verdict | 02 |
| `backups.gex_llm_regime_runs` | OpenAI Batch job (one chunk), synchronous pilot, or backfilled run; written at submit time so the batch id is never lost | 03, 04 |
| `backups.gex_llm_regime_detections` | (`arm`, `series_key`, `symbol`, `window_end`, `model`, `prompt_version`): one model answer | 03, 04 |
| view `backups.gex_llm_regime_rates_summary` | yearly LLM detection rate next to the classifier rate, by arm | read-only |

### 5.3 The gate

None of these objects exists yet, and no script creates them. The database user does hold `CREATE` on schema `backups`
(the environment check prints it), so the gate is a process rule, not a permission:

1. The database repository requires, before any DDL: the schema SQL in the project repository (here), backup
   documentation in `gex-database-infrastructure/docs/gex-llm-patterns/backup-schema.md`, cleanup instructions, a
   storage estimate, and the maintainer's approval of the documentation pull request (against `development`). The
   document needs eight sections: quick summary, tables added, permissions and access, management and cleanup, backup
   and redundancy, schema definition, impact assessment, contact and coordination. The PR body starts with
   "Documentation only; no DDL is applied by this PR and none will be before approval." and ends with
   "Refs iAmGiG/gex-llm-patterns#261". Commits, PRs and documents carry no AI attribution lines.
2. Until the approval, every script runs with `--parquet-only` (or its default, which writes parquet only), or with
   `--rollback` to exercise the database path. Nobody creates the tables ad hoc.
3. After the approval the maintainer, or an author on the maintainer's go, applies the DDL outside 21:50 to 22:45 UTC:

   ```bash
   psql -h 127.0.0.1 -d gex_options -X -v ON_ERROR_STOP=1 -f scripts/validation/electronics/sql/gex_llm_regime_schema.sql
   python $E/00_env_check.py --require-tables      # expect 5 of 5 objects
   ```

4. Then load what exists: `01_build_series.py ... --db` and `02_build_windows.py ... --db` per series and symbol,
   `03_backfill_round1.py --db`, and `04_llm_runner.py ingest --run-id R` for every run made earlier. From then on the
   runner writes Postgres by itself unless `--parquet-only` is given, and `05_report.py --source auto` reads Postgres.
5. Removal: the `DROP VIEW` and `DROP TABLE` statements in the header of the SQL file.

The archive tables `backups.*_pre_rebuild_20261004` are only ever read, in read-only sessions.

### 5.4 What the flags do

| Script | no flag | `--parquet-only` | `--rollback` | `--db` |
|--------|---------|------------------|--------------|--------|
| 01 | parquet only (the default) | parquet only | parquet is written, then schema SQL (without its `BEGIN`/`COMMIT`) and upsert in one transaction that is always rolled back; prints `ROLLBACK: N rows WOULD have been written` | parquet, then upsert and commit; the table must exist |
| 02 | parquet only (the default) | parquet only | schema inline, upsert twice, read back, roll back; **no file is written** | upsert and commit, then parquet |
| 03 | the same as `--parquet-only`; `--dry-run` parses, verifies and reports without writing | raw backups, manifests, parquet; never connects | schema inline, upserts, read-back of the published rates, roll back; **no file** | files first, then upsert and commit |
| 04 | `auto`: Postgres when `runs` and `detections` exist, otherwise parquet with a warning | never connects | schema inline, every database write rolled back; run files and parquet are still written | no such flag: auto mode writes Postgres once the tables exist |
| 05 | `--source auto` | `--source parquet` | none (never writes Postgres) | `--source db` reads Postgres and fails if a table is missing |

`--rollback` checks afterwards that no `gex_llm_regime_*` object was left behind and says so in the log
(`rollback verified: the database is unchanged`, `ROLLBACK done; gex_llm_regime objects before and after: none`,
`rollback test passed`). `--db` and `--rollback` of 02 and 03, every Postgres write of 04 (`--rollback` and `status
--rollback` included, because they apply the DDL) and the same flags of 01 refuse to run between 21:50 and 22:45 UTC unless
`--ignore-busy-window` is given. To look yourself (no rows until the DDL has been applied):

```bash
psql -h 127.0.0.1 -d gex_options -X -At -c "select relname from pg_class where relnamespace = 'backups'::regnamespace and relname like 'gex_llm_regime%'"
```

### 5.5 Three copies and the git policy

`docs/009` asks for three copies of everything a project stores: Postgres, parquet and raw files in the project
repository. The authors' rule (2026-10-30): **nothing raw goes to the remote**. Every JSONL and every full table
(series, windows, detections with the model's text) stays on this machine's disk and is loaded into the research
database; git keeps the condensed material only.

| Copy | Location | In git |
|------|----------|--------|
| 1. Postgres | `backups.gex_llm_regime_*` after approval (the database repository dumps the whole database weekly) | n/a |
| 2. Parquet (full tables) | `data/backups/gex_llm/tables/{series,windows,detections}/` | ignored: loaded into Postgres, rebuilt by 01-04 |
| | `data/backups/gex_llm/tables/runs/` (run provenance: batch ids, file ids, sha256, tokens, cost) | tracked |
| 3. Raw files | `data/backups/gex_llm/<run_id>/input*.jsonl`, `output*.jsonl`, `errors*.jsonl` | ignored: never on the remote |
| | `data/backups/gex_llm/<run_id>/manifest.json`, `batch_<k>.json` | tracked |
| Condensed | `data/backups/gex_llm/condensed/detections.csv.gz` (verdicts and metrics, no text), `windows.csv.gz` (labels and input sha256, no sequences), `series_index.csv`; written by `06_condense.py` | tracked |
| Results | `docs/papers/electronics/results/`, `docs/papers/electronics/figures/output/` | tracked |
| Inputs with one copy | `reports/validation/paper2_regime_windows/batch_jobs/` (January and November batch files and their `batch_*_metadata.json`), `.cache/research_cache.db`, `config/` | ignored |
| Published result records | `reports/validation/paper2_regime_windows/phase3_baseline_2024_full_year.yaml`, `phase4_baseline_2020.yaml` | tracked |

Every number of the paper is reproducible from the condensed detections and windows alone (join on `series_key`,
`symbol`, `window_end`); the inputs themselves come from the database or from the series builders.

Layout on disk:

```text
data/backups/gex_llm/
|-- tables/
|   |-- series/        <series>_<symbol>.parquet                  (copy 2, ignored)
|   |-- windows/       <series>_<symbol>.parquet                  (copy 2, ignored)
|   |-- runs/          r1_o4mini.parquet, r1_p3_o4mini.parquet, r1_p4_o4mini.parquet, <run_id>_c<k>.parquet   (copy 2, tracked)
|   `-- detections/    the same names                                                                          (copy 2, ignored)
|-- condensed/         detections.csv.gz, windows.csv.gz, series_index.csv                                      (tracked)
|-- r1_o4mini_phase4a_20260104/   r1_p3_o4mini_20251120/   r1_p4_o4mini_20251120/
|                      input.jsonl, output.jsonl (ignored), manifest.json (tracked)
`-- <arm>_gpt-6-luna_batch_<UTC stamp>/
    |-- input_<k>.jsonl, output_<k>.jsonl, errors_<k>.jsonl      (copy 3, ignored)
    |-- batch_<k>.json                                           (copy 3, tracked)
    `-- manifest.json                                            (copy 3, tracked)
docs/papers/electronics/results/       csv and yaml of 05_report.py, env_check_<stamp>.json
docs/papers/electronics/figures/output/  png, pdf and a provenance manifest per figure
```

The patterns are in the block "Electronics extension (issue #261)" of the repository `.gitignore`
(`git check-ignore -v <path>` shows the rule). Ignored does not mean disposable: the January and November batch files
and the ResearchCache exist in one place on this filesystem (plus the copies that `03_backfill_round1.py` makes under
`r1_*/`, which are ignored too), and the weekly database dump does not cover files. Whether to add git-LFS for the large
files is an open decision (Q-09).

---

## 6. Operational rules

1. **Raw chains: one symbol-year per statement, index plan.** `gex.options_chains_partitioned` is read with a symbol
   and a one-year date range, with `SET LOCAL enable_seqscan = off` and `max_parallel_workers_per_gather = 0`
   (`01_build_series.py` does this; the second setting keeps the float8 sums identical from run to run). The 2026-10-28
   data audit (scratch outputs, not in the repository) measured SPY 2024 at 876,969 buffers read and 4.5 s with the
   default plan against 52,980 buffers and about 1 s with the index plan. Never scan the raw table across several
   years in one statement; use `gex.options_daily_summary` for per-day aggregates.
2. **Avoid 21:50 to 22:45 UTC.** The monitors rebuild the daily tables then. No raw scans, DDL or upserts in that window.
   `common.in_quiet_window()` and `common.assert_not_quiet(ignore)` hold the one definition (the minute 22:45 is
   inside). `01_build_series.py` refuses `jan2026_phase4a`, `new_ex0dte`, `call_only` and any `--db` or `--rollback`
   run in it; `02_build_windows.py` and `03_backfill_round1.py` refuse `--db` and `--rollback`; `04_llm_runner.py` refuses
   every Postgres write (`poll --wait` sleeps until the window ends instead). `--ignore-busy-window` overrides; do not
   use it. Parquet-only work and `05_report.py` are not affected. Judge by `date -u`.
3. **Read-only sessions for every source read**, `statement_timeout = 600s` in every session, archive tables never
   written. Source reads of `01_build_series.py` identify themselves as `gex-llm-patterns 01_build_series`.
4. **The tables `backups.gex_llm_regime_*` do not exist and no script creates them.** Only the maintainer applies the DDL
   (section 5.3). Test a database path with `--rollback`, never by creating the objects; afterwards check that none
   exists.
5. **Never print the OpenAI key.** Do not `echo` it, `cat config/config.json`, or paste debug output that may hold
   request headers. The runner scrubs it from error text; the environment check prints only "present".
6. **No paid call by accident.** `pilot` and `submit` are the only paid steps. Run `00_env_check.py` first,
   `submit --dry-run` before `submit`, `status` after it, and never pass `--force` without the authors' approval.
   Rehearse with `--backup-root DIR` (04, 03) or `--parquet-root DIR` (02, 05) and the dry-run flags; none of them calls
   the API.
7. **Spend is what the current balance paid for.** The three o4-mini backfills are history, listed apart and never
   counted against the $12.00 hard stop (`common.counts_toward_budget`).
8. **Submit in waves.** The organization's limit is 20,000,000 enqueued `gpt-6-luna` tokens; `submit` accepts more and
   the batch then fails without cost (section 4, step 4). One arm or wave at a time, `poll --wait` between them.
9. **The contract is shared.** `common.py` and `sql/gex_llm_regime_schema.sql` define the series and arm registry, the
   model configuration, the repeat labels, the column names and the file layout for all scripts and the figure loaders.
   Change them in one reviewed commit together with the code that depends on them.
10. **Reused code stays untouched.** The study calls `MechanicsPromptBuilder.build_regime_prompt`,
   `RegimeClassifier` and `src/utils/json_parser.extract_json`. Changing them changes the published prompt or labels;
   the fidelity checks below catch it.
11. **Shared environment, shared history.** No `pip install`. The pipeline changes no git state; commits on
    `paper/electronics` are made by the authors, without AI attribution lines.

---

## 7. Fidelity checks

These must hold before any result is trusted. Where the last column says "stops", the script refuses to continue when
the check fails; the other rows are read off the output.

| Check | Where | Expected on 2026-10-29 | Enforced |
|-------|-------|------------------------|----------|
| Phase 4A files unchanged | `00_env_check.py` | input `95f83fed9768bbe0553d4434f934ce6a5bd892993812a925b185295f4391eef6` (9,888,848 B), output `dffd8e78e7e639eb4e4c110316214f0d35d54c390501ebcead9d0947336871bd` (2,252,575 B), `.cache/research_cache.db` `7bdff7584ce679f7737d8c178331b0bd131112d9c5565199e1614b45a6e3caef`; each reported as "matches the audited digest" | blocker |
| Prompt byte-identity, Phase 4A | `00_env_check.py` | "1,476 of 1,476 prompts rebuilt byte for byte" by today's `MechanicsPromptBuilder` | blocker |
| 1,476 ids, values and prompts | `02_build_windows.py --series jan2026_phase4a` | `fidelity ok: 1476 windows, window_end set, every date and value and every prompt (byte for byte) equal to phase4a_postgresql_20260104_184832.jsonl` | stops (`FidelityError`) |
| Prompt byte-identity, Phase 3/4 dated prompts | `02_build_windows.py --series p3_2024_dated` (also `p3_2024`; `p4_2020_dated`, `p4_2020`) | `fidelity ok: 223 windows, ... equal to phase3_full_2024_baseline_v2.jsonl` and `... batch_regime_20251120_104630.jsonl`: the 30 ISO dates, the 30 values and the prompt rendered with dated labels are those of the November files, 223 of 223 in each | stops (`FidelityError`) |
| Rebuilt prompt equals the recorded request | `03_backfill_round1.py` | `prompts rebuilt with common.build_prompt (obfuscated labels): 1476 of 1476 identical to the recorded requests`; `(dated labels): 223 of 223` for each November arm | reported; a difference is a warning |
| Published rates reproduce | `03_backfill_round1.py` | `r1_o4mini`: 12.2, 3.7, 32.4, 20.2, 100.0, 100.0 % for 2020 to 2025 from the 1,412 cached windows (26/213, 9/241, 79/244, 46/228, 241/241, 245/245); the cache cross-check shows 1412/1412 on every field, 0 cache-only and 64 output-only windows. `r1_p3_o4mini` 181 of 223 = 81.2 % and `r1_p4_o4mini` 27 of 223 = 12.1 %, the counts the result YAMLs state (223/223 agree on the verdict) | stops (nothing is written for any arm) |
| Input file before paying | `submit` | sha256 and line count of `input_<k>.jsonl` equal the runs row | stops |
| Classifier thresholds | `00_env_check.py` | persistence 0.7 (21 of 30 days), $5 B, at most 5 flips, $3 B low-conviction floor | blocker |
| Request prompts | `04_llm_runner.py generate` | built with the same `obfuscate()` and `build_prompt()` as the checks above. Each stored answer carries `detection_metadata.prompt_sha256`, and `window_changed` is set when a stored window no longer matches what was sent. The by-hand comparison below | flag only |
| Repeat labels | `05_report.py --check-conventions` | `repeat labels: consistent with common.py and 04_llm_runner.py` | exit status 1 on a mismatch |
| Free replay | `02_build_windows.py` | the tables in section 3.5; `new_full` SPY gives 10.3 % (2024) and 13.6 % (2025) | read off |
| Model fields against the rule | `ingest` summary | `metrics agree n/n`: reported counts, magnitude and persistence equal the classifier within 0.5 day, 0.05 B and 0.5 pp. `sign_flips` is the least reliable field (the probe under-counted it in 7 of 32 answers); it is stored beside the classifier's value | read off |

Comparing the requests of a generated run with the original batch files (run it after `generate` for `bridge_jan`,
`p34_dated_2024` and `p34_dated_2020`, before `submit`; a repeat carries the same prompt as its original). Checked on
2026-10-29 against scratch runs and against the first real submissions: 1,476 of 1,476, 223 of 223 and 223 of 223.

```bash
python - <<'PY'
import glob, json, sys
from datetime import date
sys.path.insert(0, "scripts/validation/electronics")
import common as c

ORIGINAL = {"bridge_jan": c.PHASE4A_INPUT_JSONL, "p34_dated_2024": c.PHASE3_INPUT_JSONL, "p34_dated_2020": c.PHASE4_INPUT_JSONL}
for arm, path in ORIGINAL.items():
    sent = {}
    for f in glob.glob(f"data/backups/gex_llm/{arm}_gpt-6-luna_batch_*/input_*.jsonl"):
        for line in open(f):
            j = json.loads(line)
            end = date.fromisoformat(j["custom_id"].split("|")[2].split("#")[0])
            sent.setdefault(end, set()).add(j["body"]["messages"][0]["content"])
    original = {}
    for line in open(path):
        j = json.loads(line)
        original[date.fromisoformat(j["custom_id"].replace("window-", ""))] = j["body"]["messages"][0]["content"]
    same = sum(sent.get(end) == {prompt} for end, prompt in original.items())
    print(f"{arm}: {same} of {len(original)} windows sent with the original prompt")
PY
```

The obfuscated twins (`p34_obf_*`) send the same values with `Day T-k` labels, so none of their prompts equals the
November prompt; that is the point of the arm.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| env check: `json_repair  not importable` | deliberate: the package is not installed in the shared env and must not be | nothing to do. `src/utils/json_parser.py` skips its repair strategy. `common.parse_llm_content` retries with `json.loads(strict=False)` but cannot read the one January answer (2023-08-07) that is wrapped in a markdown fence and holds a raw control character; `03_backfill_round1.py` unwraps it, stores it as `fallback` with `lenient_json`, and logs the expected warning `All JSON parsing strategies failed. Last error: Invalid control character`. If the package ever becomes importable the check warns, because `fallback` results would then differ from runs made without it |
| env check: `user site is active ... export PYTHONNOUSERSITE=1`, a package marked `[user-site]` | `~/.local/lib/python3.12/site-packages` can shadow the env (on 2026-10-29 it still holds `yaml` and pip leftovers named `~umpy`, `~andas`, `~sycopg2`) | `export PYTHONNOUSERSITE=1` before every run |
| `OpenAI key not found (config/config.json OPEN_AI_KEY or env OPEN_AI_KEY)` | `config/` is git-ignored, so a fresh clone or `git worktree add` has no `config/config.json` (nor the batch files and `.cache/research_cache.db`, which are ignored too) | copy `config/config.json` from the main checkout, or `export OPEN_AI_KEY` for the session; never commit it. Copy the batch files and the cache as well, or work in the main checkout |
| `refusing to run between 21:50 and 22:45 UTC` (01) or `inside the 21:50-22:45 UTC quiet window; pass --ignore-busy-window to override` (02, 03) or `Postgres writes are paused: ...` (04) | quiet-window guard | wait until after 22:45 UTC (`date -u`); `--parquet-only` work is not blocked (01 still refuses its raw scans) |
| `... does not exist: apply ... after maintainer approval` or `... do not exist yet (DDL awaits approval): using parquet only` | the gate (section 5.3) | expected; use the default mode, `--parquet-only` or `--rollback` |
| `FidelityError: ... window_end set differs`, `... differ from <file> in their dates or values` or `... prompt(s) differ from the file` | the batch files, the prompt builder or the series parquet changed | stop; run `00_env_check.py`; rebuild the series (01) and the windows (02) |
| 02: `series parquet not found: ...`; `<series>/<symbol> ends <date>, more than 7 days before the last window_end requested ... the series looks incomplete`; `master calendar: ... not found (run 01_build_series.py --series new_full ...)` | step 01 has not been run, was run for part of the range (`--years`), or `new_full` of the symbol is missing | run 01 for the series (and for `new_full` of the symbol); or pass `--end-max` to build the windows a short series supports; or `--master-calendar db` |
| 02: `<file> holds N window(s) from an earlier version of this script (window_metadata without missing_master_days)` | a windows parquet written before the hole detectors existed | delete that windows parquet and rebuild the full range |
| 03: `the batch output does not reproduce the published run: ...` | a batch file, the research cache or the result YAML differs from what the published rates need | nothing was written; run `00_env_check.py`; do not continue until the cause is known |
| 04: `<path> not found: run 02_build_windows.py for <series>/<symbol> (or --from-db)` | the windows parquet of the arm is missing (the composite arm needs `intraday_t0`, the scaled arms `new_full_scaled`, the Phase 3/4 arms `p3_2024`, `p3_2024_dated`, `p4_2020`, `p4_2020_dated`) | build the series (01), then the windows (02) |
| 04: `... -- refusing (raise --budget or pass --force)` | ledger plus projection above the budget | `status`; raise `--budget` only with the authors' approval |
| 04: `... repeat earlier work, e.g. ... -- refusing (pass --force to send them anyway)` | the chunk asks again for a window that is answered or already requested in a sent run | `status`; ingest the earlier run, or generate again after it is finished |
| 04: `<run> was not made by this script (a backfill)` | `submit`, `poll`, `retrieve`, `ingest` or `retry` was given `r1_o4mini_phase4a_20260104`, `r1_p3_o4mini_20251120` or `r1_p4_o4mini_20251120` | none of these commands applies to a backfill; rerun step 3 instead |
| 04: `poll` shows a chunk `failed`; its `batch_<k>.json` has `errors.data[0].code = token_limit_exceeded` (`Enqueued token limit reached for gpt-6-luna ... Limit: 20,000,000 enqueued tokens`) | too many requests were queued at once (section 4, step 4); nothing ran and nothing was billed | `requeue --run-id R --wait` sends the rejected chunks again as soon as the queue has room (or `poll --wait` the batches in progress first, then `requeue`); submit one wave at a time |
| 04: `nothing to ingest ... run 'retrieve' first` | the batch is not finished or not downloaded | `poll --run-id R --wait`, then `retrieve` |
| 04: `window ... must hold 30 numeric daily values` | a missing or NaN value in a stored window (it would reach the model as the text `nanB`) | rebuild the series and windows |
| 04 `generate --repeat-fraction 0` logs a warning that cites D-09 | the warning assumes a 5 % sample on every arm; the decisions log (D-09, Q-07) asks for the full repeat of `bridge_jan` only and leaves the sample to the authors | expected when you choose no sample for an arm (section 10) |
| 05: `parquet root ... does not exist or is not a directory`, `--source db requested but the backups.gex_llm_regime_* tables do not exist` or `section <name> skipped: ...`; exit status 2 | a mistyped `--parquet-root`, the tables are not in Postgres yet, or the tables the section needs are empty | check the path or `--source`; run the earlier steps; nothing is invented |
| 05: `--check-conventions` prints `MISMATCH` | 04, 05 and `common.py` disagree on the repeat labels | fix the code before any test-retest number is trusted; the labels are `common.REPEAT_MARK` and `common.REPEAT_ARM_SUFFIX` |
| files under `/mnt/bst` show mtimes about nine minutes behind `date -u` | the NFS server's clock | use `date -u` for the quiet window and the UTC stamps in run ids and manifests for provenance |
| `psql` or `gh` not found | they exist only inside the AutoGex env | activate it |

---

## 9. Gates and open decisions

Some steps wait for the authors (Christopher Regan and Dr. Ying Xie) or for the database maintainer. The questions are
written out in `planning/02_decisions_log.md`; Q-01 (QQQ and IWM floor effect) is closed by D-18, which runs both the
unscaled and the scaled arms.

| Step | Waits for |
|------|-----------|
| any `--db` run, applying the DDL | the documentation PR and the maintainer's approval (D-14) |
| `submit` of `bridge_jan` | the pilot result, and Q-05: the gate metric, window set and threshold fixed before the bridge result is seen |
| the other priority-1 arms: `full_spy`, `ex0dte_spy`, the four `p34_*` arms (D-19) | the bridge gate; they run in priority order and the gate is read first |
| the priority-2 arms: `full_qqq`, `full_iwm`, `full_qqq_scaled`, `full_iwm_scaled` (D-18) | Q-03 (spend, after the pilot cost is known) |
| `ex0dte_qqq`, `ex0dte_iwm`, `intraday_spy` (priority 3), `bridge_old` (priority 4) | Q-03 and Q-08 |
| the 5 % test-retest sample on the arms other than `bridge_jan` (the full repeat of `bridge_jan` is D-09) | Q-07: the runner default is on, `--repeat-fraction 0` turns it off |
| `05_report.py` on full results | Q-06: window range for the main text, primary comparisons, which cross-asset variant leads |
| call-only diagnostic in the paper | Q-04 (the series itself costs nothing: `01_build_series.py --series call_only`) |
| wording about the data defect and the notices to the venues | Q-02 (authors only) |

---

## 10. Known issues (2026-10-31)

Found by following this runbook end to end against scratch copies of `data/backups/gex_llm/` with synthetic Batch
output (`--backup-root`, `--parquet-root`, `--results-dir`; no API call), by exercising every `--rollback` path, and
by the live runs of 2026-10-29 to 2026-10-31. Fixed and no longer listed: the six issues of the 2026-10-28 handoff,
the schema comments that lagged the registry, the untested `--db` paths (the tables exist and are loaded), and the
one January answer the shared parser rejected (fenced with a raw control character). Delete an entry when it is fixed.

| # | Symptom | Cause | Workaround until fixed |
|---|---------|-------|------------------------|
| 1 | `00_env_check.py` ends with `RESULT OK` and a later step fails | the check predates the Phase 3/4 inputs and the figure scripts: it does not look at the November-2025 batch files, treats a missing `.cache/research_cache.db` as a warning although `03` needs it, and does not check Pillow | run `03_backfill_round1.py --dry-run` and `figures/scripts/run_all.py --check` as well |
| 2 | `00_env_check.py --write` exits 1 when it cannot write the snapshot, but the printed report ended with `RESULT OK` | `main()` prints the report before it writes the file | read the exit status, not the last line |
| 3 | `04_llm_runner.py generate --repeat-fraction 0` warns that D-09 asks for 5 % on every arm | the warning predates D-22, which keeps the 5 % duplicate sample as the default on every arm and the full repeat on `bridge_jan` | ignore the warning; the default is what D-22 says |
| 4 | `submit` does not know the organization's enqueued-token limit (20 M tokens for gpt-6-luna) | the limit is only visible as `token_limit_exceeded` on a batch that has already been created (section 8) | submit everything, then run `04_llm_runner.py requeue --wait` in the background: it resends every rejected chunk with its original file as room frees |
| 5 | Background collection stops when the Claude Code session that started it closes | the collector and requeue loops are child processes of that session | on resume, relaunch the collector loop and `requeue --wait`; `status` shows what is pending |

---

## 11. Files

| Path | Purpose |
|------|---------|
| `common.py` | contract: paths, database access, series (11) and arm (18) registry, model configuration, strict JSON schema, obfuscation (obfuscated and dated labels), prompt and classifier bridge, repeat labels, cost accounting and `counts_toward_budget`, quiet window, raw-backup layout, the loaders of the published batch files (`load_phase4a_inputs`, `phase4a_daily_series`, `load_phase4a_outputs`, `load_phase34_inputs`, `phase34_daily_series`, `load_phase34_outputs`). No side effects on import |
| `sql/gex_llm_regime_schema.sql` | the four tables and the view; idempotent; every column commented; cleanup statements in the header |
| `00_env_check.py` | pre-flight check |
| `01_build_series.py` | daily GEX series |
| `02_build_windows.py` | 30-day windows with the deterministic verdict and the hole detectors |
| `03_backfill_round1.py` | the three published o4-mini runs as arms `r1_o4mini`, `r1_p3_o4mini`, `r1_p4_o4mini` |
| `04_llm_runner.py` | gpt-6-luna Batch runner and cost ledger |
| `05_report.py` | paper tables, overlap-aware statistics, cost ledger |
| `README.md` | this file |

Related:

| Path | Purpose |
|------|---------|
| `docs/papers/electronics/planning/00_design.md` | design memo (v2): what the published inputs were, the series, arms and cost |
| `docs/papers/electronics/planning/02_decisions_log.md` | decisions D-nn and open questions Q-nn |
| `docs/papers/electronics/planning/01_issue_261_archive.md` | archived text of issue #261 |
| `docs/papers/electronics/planning/forensics/` | evidence for the published inputs: memo, per-day comparison, month table, claim inventory, second-audit memo (Phase 3/4 dated prompts and sign conventions) |
| `docs/papers/electronics/results/` | output of `05_report.py` and `00_env_check.py --write` |
| `docs/papers/electronics/figures/` | figure scripts (`scripts/`: twelve figures, `run_all.py`, `theme.py`, `figdata.py`, `figllm.py`) and output |
| `docs/papers/electronics/latex/`, `build.sh` | manuscript (MDPI Electronics class) |
| `docs/papers/electronics/README.md` | the paper folder: status, layout, build, data provenance |
| `docs/papers/CORRECTIONS.md` | public record of the findings about the published results (no notices are filed; the Electronics paper carries the corrected analysis) |
| `src/llm/mechanics_prompt_builder.py`, `src/validation/regime_classifier.py`, `src/utils/json_parser.py` | the reused prompt builder, deterministic classifier and fallback JSON parser |
| `gex-database-infrastructure/docs/009_PROJECT_BACKUP_STRATEGY.md`, `docs/gex-llm-patterns/backup-schema.md` | storage rules and the documentation this project owes the database repository |
