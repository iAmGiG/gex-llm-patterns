# Electronics Special Issue extension — design memo

**Status:** v2, 2026-10-28 (supersedes v1 of the same day) · **Tracking:** gex-llm-patterns issue #261 (upstream context: #260; upstream root cause: gex-database-infrastructure #24) · **Branch:** `paper/electronics`

## 1. Context and scope

AIAI 2026 invited an extended version of paper #111 (*Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation*) to the MDPI *Electronics* Special Issue "Timely AI Advancements and Interdisciplinary Synergies for Intelligent Modeling". JRFM (jrfm-4256551, in production) already combines Papers 1 and 2, so the extension must consist of **new experiments** beyond both, and must cite both.

While preparing it, the exact inputs of the published Phase 4A run were recovered and found to be defective for 2023-09-29 onward. The extension is therefore framed as a **data-integrity correction with a controlled LLM re-test**, not as an incremental extension.

## 2. What the published inputs were (verified 2026-10-28)

Evidence trail: `planning/forensics/` (memo, per-day comparison CSV, month table, claim inventory). Three independent skeptics could not refute the central finding.

- The surviving batch file `reports/validation/paper2_regime_windows/batch_jobs/phase4a_postgresql_20260104_184832.jsonl` holds the 1,476 SPY windows (ends 2020-02-13 … 2025-12-31) sent to o4-mini on 2026-01-04; the raw outputs survive next to it. The current `MechanicsPromptBuilder.build_regime_prompt` reproduces every prompt byte-for-byte.
- **From 2023-09-29 through 2025-12-31 (565 of 565 days) the inputs equal call-side GEX only, 0DTE included, to within 0.005 B; puts contributed nothing.** Through 2023-09-28, 900 of 940 days equal today's full net GEX (calls + puts, 0DTE included); 39 scattered days are call-only (first: 2021-09-17); one day (2022-05-31) matches nothing.
- **Cause (upstream issue #24, fix commit 2c16a4d, 2026-02-03):** `PostgreSQLOptionsManager.store_options_chain()` read `row.get('option_type', 'call')` while Alpha Vantage's column is `type`; every contract was labelled "call" and `ON CONFLICT (symbol, trading_date, strike, option_type, expiration) DO NOTHING` discarded the put of each pair. The 604 SPY dates written through that path on 2026-01-02 (2021: 2, 2022: 3, 2023: 98, 2024: 251, 2025: 250) are exactly the call-only days; the other 901 dates went through the SQLite writer and kept their puts. The raw table was re-collected and reloaded on 2026-02-03.
- The archive `backups.options_daily_summary_pre_rebuild_20261004` was built on 2026-01-15 from the same put-less table (Black–Scholes gamma on integer DTE, same-day expiries zeroed), so it is also put-less there (put GEX zero on 98/249 days in 2023, 251/251 in 2024, 249/250 in 2025). It never equals the January series; the ≈1.22–1.27 ratio between them is the 0DTE share of call GEX.
- January's calendar lacked two real trading days (2023-07-12, 2024-03-11); 58 published windows span 31 trading days with one skipped.

Deterministic replay of the paper's own criteria (≥ 21 of 30 days same sign, mean |GEX| ≥ $5 B, ≤ 5 sign flips), detection % per year 2020–2025:

| Series | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|
| Published (o4-mini, Phase 4A) | 12.2 | 3.7 | 32.4 | 20.2 | 100 | 100 |
| January inputs (exact) | 12.1 | 4.0 | 32.3 | 19.3 | 100 | 100 |
| Today's full net GEX (calls + puts, 0DTE incl.) | 12.1 | 3.6 | 40.6 | 22.4 | **10.3** | **13.6** |
| Today's call-only GEX | 90.6 | 100 | 100 | 100 | 100 | 100 |

The o4-mini labels equal the deterministic rule on every parsed window, so the model tracked its inputs; the artifact is in the data. The 2020–2021 rows are unaffected, 2022 nearly so, 2023 mixed, 2024–2025 entirely call-only.

Other published-figure and lineage issues flagged by a single audit and under second review (do not repeat until verified): the detection-progression figure embedded in both PDFs is the script's synthetic fallback; two further figures are synthetic with data-like captions; "$23 B" and "+360 %" match no stored series; the Phase 3/4 (81.2 % vs 12.1 %) series used other sign conventions and dated prompts.

## 3. Daily GEX series

| key | source | symbols | range | role |
|---|---|---|---|---|
| `jan2026_phase4a` | the surviving batch file (values at 0.01 B precision, January calendar) | SPY | 2020-01-02 → 2025-12-31 | exact published inputs; bridge |
| `call_only` | raw `gex.options_chains_partitioned`, call leg incl. 0DTE | SPY (diagnostic) | 2020 → 2026-10-09 | reproduces the defect from clean data |
| `old_bs` | archive table (**read-only**) | SPY | 2008 → 2026-10-02 (holes) | diagnostic only; put-less 2023-10+ |
| `new_full` | `gex.options_daily_summary` after the 2026-10-08 rebuild (stored gamma, 0DTE incl.; equals the raw formula on all 4,712 SPY days) | SPY, IWM 2008+; QQQ 2011+ | → 2026-10-09 | corrected primary |
| `new_ex0dte` | raw table, `expiration > trading_date` | same | → 2026-10-09 | 0DTE ablation |
| `intraday_late` | `gex.intraday_gex_summary`, `snapshot_type = 'final_rush'` (19:55:59 UTC; the 20:00 slot *is* the EOD row) | SPY | 2026-07-27 → 2026-10-09 | intraday check (composite windows `intraday_t0`: EOD T-29…T-1, final_rush at T+0) |

Boundaries: equity options moved from Alpha Vantage to Cboe delayed quotes on **2026-10-12** (confirmed per symbol), so every window ends ≤ 2026-10-09; the archive has no QQQ/IWM rows 2020-12-03 → 2025-12-30; index roots have ≤ 70 days and are out of scope; nothing here reads theta/vega (upstream unit change 2026-11-03, #157). The DB maintainer's "0.47×" figure is not reproduced and is not used.

Every series is materialised in `backups.gex_llm_regime_series`, so the numbers shown to the model are stored, never recomputed.

## 4. Windows and deterministic classifier

30 consecutive trading days (T−29 … T+0), one window per end date (rule A: 30 consecutive series rows, flagged when a span covers a calendar gap > 3 days; rule J: January's own calendar for `jan2026_phase4a`, which must reproduce the 1,476 window ids exactly). Obfuscated as "Day T−29 … Day T+0" with no dates or tickers, identical to Phase 4A. `src/validation/regime_classifier.py::RegimeClassifier` labels every window at zero cost; results live in `backups.gex_llm_regime_windows` with the exact input vector and its sha256.

## 5. LLM arms and run matrix

Model: **gpt-6-luna** (o4-mini is retired on all endpoints), Batch API, `reasoning_effort = medium`, `max_completion_tokens = 4000` (retry at 8000 on `length`), strict JSON schema with the nine Phase 4A fields (the one protocol change, disclosed). Prompt text unchanged. Probe (2026-10-28): ~1,911 prompt + ~814 completion tokens per request, **$0.30 per 1,000 requests** on Batch; verdicts matched the deterministic rule 31/31; `sign_flips` under-counted in 7/32 (recomputed deterministically and stored beside the model's value with a mismatch flag).

| arm | series | symbol | ≈ windows | priority |
|---|---|---|---|---|
| `r1_o4mini` | jan2026_phase4a | SPY | 1,476 (1,412 parsed in Jan; ~63 recovered now) | backfill only |
| `bridge_jan` | jan2026_phase4a | SPY | 1,476 (+ one full repeat for test–retest) | 1 — model agreement with o4-mini on identical inputs |
| `full_spy` | new_full | SPY | ~4,670 | 1 |
| `ex0dte_spy` | new_ex0dte | SPY | ~4,670 | 1 |
| `full_qqq`, `full_iwm` | new_full | QQQ, IWM | ~3,870 + ~4,680 | 2 (floor effect, see §9) |
| `ex0dte_qqq`, `ex0dte_iwm` | new_ex0dte | QQQ, IWM | 2020+ only | 3 |
| `intraday_spy` | intraday_t0 | SPY | ≤ 54 | 3 |
| `bridge_old` | old_bs | SPY | ~4,550 | 4, optional |

Cost: priority-1 arms ≈ 12,300 requests ≈ $3.7; everything ≈ $11. Hard stop in the runner at $12 (balance $16.86 on 2026-10-28); batches submitted in chunks ≤ 1,500 requests, priority order, with a cost ledger. Gate: on `bridge_jan`, Cohen's κ between luna and the stored o4-mini labels; because both track a deterministic rule, κ is expected to be high and a low value would point at the model, not the data.

## 6. Storage (per gex-database-infrastructure docs/009)

Four tables plus one view in `backups`, created only after the documentation PR in the DB repo is approved (`docs/gex-llm-patterns/backup-schema.md`, worktree `.claude/worktrees/docs-gex-llm-regime`, branch `docs/gex-llm-regime-tables`): `gex_llm_regime_series`, `gex_llm_regime_windows`, `gex_llm_regime_runs` (row written at submit time, so the batch id is never lost), `gex_llm_regime_detections`, view `gex_llm_regime_rates_summary`. DDL: `scripts/validation/electronics/sql/gex_llm_regime_schema.sql` (idempotent, schema-qualified, every column commented, tested in a rolled-back transaction first). Until approval every script writes parquet under `data/backups/gex_llm/tables/` and can run its DB path inside a transaction that is rolled back. Raw copies per run under `data/backups/gex_llm/<run_id>/` (input/output JSONL on disk, manifests and detections parquet tracked in git). Archive tables are read in read-only sessions and never written.

## 7. Scripts (`scripts/validation/electronics/`)

`common.py` (contract) · `00_env_check.py` · `01_build_series.py` · `02_build_windows.py` · `03_backfill_round1.py` · `04_llm_runner.py` (generate / submit / poll / retrieve / ingest / pilot / retry / status, cost ledger) · `05_report.py` (Postgres or parquet → `docs/papers/electronics/results/`; Wilson CIs plus quarter-block bootstrap and a non-overlapping subsample, because stride-1 windows overlap) · `sql/` · `README.md`.

Reused from `src/`: `MechanicsPromptBuilder.build_regime_prompt`, `RegimeClassifier`, `src/utils/json_parser.extract_json` (fallback). All verified under the current AutoGex env (Python 3.12.12, numpy 2.4, pandas 2.3, openai 2.14; zero deprecation warnings). Run with `PYTHONNOUSERSITE=1 PYTHONPATH=<repo>` from the main working tree; install nothing in the shared env.

## 8. Paper folder (`docs/papers/electronics/`)

`latex/` (`\documentclass[electronics,article,submit,moreauthors,pdftex]{Definitions/mdpi}`, `TEXINPUTS/BSTINPUTS=.:../../jrfm:` set by `build.sh`), `figures/scripts` + `figures/output` (6.14 in wide, 8–9 pt, no synthetic fallbacks, provenance manifest per figure), `results/`, `planning/` (this memo, issue archive, decisions log, forensics).

## 9. Decisions still open for the authors

1. **JRFM (in production) and AIAI (published):** whether to request a hold/correction and a corrigendum. Decide with the verified memo; the second audit of the additional figure/lineage findings should finish first. *Settled 2026-10-29 (decisions log D-20): JRFM is published; no hold, no corrigendum, no notice; this paper carries the corrected analysis and does not present itself as a correction.*
2. **QQQ/IWM floor effect:** the fixed $5 B threshold yields zero persistent windows for both in every year. Options: report it as the result, or a disclosed per-symbol scaling of the input series (prompt unchanged). Priority-2 arms wait for this.
3. **Tracking large artefacts:** raw JSONL and series/windows parquet stay on disk (git-ignored); whether to add git-LFS.
4. "2026" is the *post-publication period*, not out-of-sample: luna was created 2026-09-14 and its training cutoff is undocumented.

## 10. Upstream constraints relayed by the database maintainer (2026-10-28)

Never write the `*_pre_rebuild_20261004` archives; expect rerun ≠ published; theta/vega units change 2026-11-03 (#157); follow docs/009. Suggested back to the maintainer: a put/call row-balance load invariant, annotating the archive tables as put-less, and confirming the symbols outside the #24 re-collection (upstream #69 says 72 of 108 were redone).
