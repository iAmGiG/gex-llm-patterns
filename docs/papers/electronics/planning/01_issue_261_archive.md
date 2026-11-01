# Issue #261 — archived 2026-10-28 (source of truth is GitHub)

## Electronics SI extension: regime re-run on 2026 OOS, QQQ/IWM, 0DTE ablation, intraday check (results → Postgres)

https://github.com/iAmGiG/gex-llm-patterns/issues/261 · opened 2026-10-27T21:01:02Z

## Context

AIAI 2026 invited an extended version of paper #111 (*Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation*) to the MDPI **Electronics** Special Issue *"Timely AI Advancements and Interdisciplinary Synergies for Intelligent Modeling"*. MDPI expects substantial new material in an extended version.

JRFM (jrfm-4256551) already combines Papers 1 and 2. The new material therefore has to be **new experiments, beyond both AIAI and JRFM**. The cover letter must cite both papers.

`gex_options` now has what those experiments need:
- 2026 data through 2026-10-26.
- Complete QQQ and IWM for 2020–2025 (upstream #78).
- Intraday GEX from 2026-01-13.

## Findings that shape this issue

1. **Paper 2 is not affected by #260.**
   - Phase 4A (`scripts/validation/paper2/phase4a_postgresql_batch.py`) computes GEX from raw `gex.options_chains_partitioned` with the stored vendor gamma, 0DTE included. It never read `options_daily_summary`.
   - Its SPY values match the **rebuilt** `options_daily_summary.total_gex` exactly:

     | Date | Phase 4A / rebuilt | Old (pre-rebuild) | 0DTE-only |
     |---|---|---|---|
     | 2024-03-15 | −15.35B | +12.62B | −10.85B |
     | 2024-09-16 | 6.38B | 17.03B | |
     | 2025-06-16 | 6.16B | 17.45B | |
   - In other words, Paper 2 already used the corrected convention.
2. **o4-mini is retired.** The API returns 404 `model_not_found` on both keys, so the re-run needs a new model plus a bridge run on the original windows.
3. **Credits are OK on both keys** (`OPEN_AI_KEY`, `RH2MAS_OPEN_AI_KEY`); test calls to gpt-5-mini and o3 succeeded. Check the balance on the dashboard before any full batch.
4. **Round-1 cost basis:** about 3,777 tokens per request, and $11.07 for 2,221 requests, so roughly $0.005 per request at o4-mini batch prices.
5. **Round-1 pipeline gaps to fix:**
   - The batch ID was not logged.
   - The raw output JSONL was not kept.
   - 64 responses failed the regex parse.
   - `ResearchCache.record_detection()` drops the regime metrics (`structured_output` was filled in by hand).
   - fig02 queries a column `raw_response` that does not exist.
   - Figure scripts silently fall back to synthetic data.
6. **Data boundaries:**
   - Equity options switched from Alpha Vantage to Cboe on 2026-10-12, so **window ends are capped at 2026-10-09**.
   - Intraday equity rows before 2026-07-25 carry the previous day's EOD chain (upstream #64).
   - SPX has only about 70 days of data, so it is out of scope.

## Experiment arms

| Arm | Data | ~Windows |
|---|---|---|
| **A0 bridge** | SPY 2020–2025, same windows and prompt as Phase 4A, new model | 1,476 |
| **A1 out-of-sample** | SPY windows ending 2026-02-13 … 2026-10-09 | ~165 |
| **A2 / A3 cross-asset** | QQQ, IWM, 2020-02 … 2026-10-09 | ~1,640 each |
| **A4 0DTE ablation** | SPY 2020–2026 using only contracts with `expiration > trading_date`, which tests directly whether the 2023→2024 shift is driven by 0DTE | ~1,640 |
| **A5 intraday check** | SPY 2026, daily value taken from a late-session `intraday_gex_summary` snapshot vs EOD, days ≥ 2026-07-25 | ~25–50 |

That is about 6,600 requests, or about 25M tokens. Every window also stores a deterministic `RegimeClassifier` label as the criteria reference.

## Model selection (gate before any full batch)

- **Pilot:** 40 fixed SPY windows (20 detected, 20 not, by the o4-mini labels) on the standard API, run on each of **gpt-5-mini, gpt-5.4-mini and gpt-5.5**.
- **Measured per model:** tokens per request, $ per request, parse rate, and agreement with the o4-mini labels. Expected pilot cost is under $5.
- **Full-run estimate:** pilot $ per request × 6,600 × the batch discount (~0.5). At round-1 prices that would be about $35.
- **Prompt:** unchanged (`MechanicsPromptBuilder.build_regime_prompt`). The one protocol change, to be disclosed in the paper, is enforcing a JSON schema through `response_format`.

## Storage (follows `gex-database-infrastructure/docs/009_PROJECT_BACKUP_STRATEGY.md`)

Schema SQL goes in `scripts/database/gex_llm_regime_schema.sql` and is idempotent. It creates two tables, and this project writes to both.

**`backups.gex_llm_regime_runs`**: one row per batch.
- Identity: `run_id`, `arm`, `model`, `model_snapshot`, `prompt_version`.
- Provenance: `openai_batch_id`, `input_file_sha256`, `output_file_path`.
- Window range, request and parse counts, token usage, `est_cost_usd`, status and timestamps.
- `metadata` JSONB and `created_at`.

**`backups.gex_llm_regime_detections`**: one row per window.
- Keys: `run_id`, `arm`, `symbol`, `window_end_date`, `model`, `prompt_version`.
- `gex_sequence` JSONB: the obfuscated input actually sent.
- `classifier_label` and `classifier_metrics`.
- LLM output: `regime_detected`, `regime_type`, `confidence`, `positive_days`, `negative_days`, `avg_magnitude_billions`, `sign_flips`, `persistence_pct`, `reasoning`, `raw_response`, `parse_status`.
- Tokens, `metadata` JSONB, `created_at`.
- UNIQUE (`arm`, `symbol`, `window_end_date`, `model`, `prompt_version`).

**Raw backups** go in `data/backups/gex_llm/<run_id>/`: `input.jsonl`, `output.jsonl` (the verbatim OpenAI file), `batch.json` and `detections.parquet`.

**Backfill:** load the 1,412 round-1 o4-mini rows from `.cache/research_cache.db` as arm `R1_o4mini`, so every comparison can be done in SQL.

## Pipeline

- **Runner:** refactor `phase4a_postgresql_batch.py` into `scripts/validation/paper2/regime_batch_runner.py`.
  - Arguments: `--arm --symbol --start --end --model --prompt-version --exclude-0dte --source {eod,intraday}`.
  - Modes: `generate | submit | poll | retrieve | ingest`.
- **`submit`:** writes the runs row with the batch ID immediately.
- **`ingest`:** downloads the output file, parses it (schema first, with `src/utils/json_parser.extract_json` as fallback), and upserts the detections plus the parquet backup. It is idempotent.
- **Report:** `scripts/validation/paper2/extension_report.py` reads only Postgres and writes a YAML equivalent to round 1. It covers:
  - Detection rate by year, arm and symbol.
  - Bridge agreement (κ, % agreement).
  - LLM-vs-classifier accuracy.
  - 0DTE-excluded vs full, by year.
  - φ and p-values.

## Checklist

- [ ] Doc PR in gex-database-infrastructure: `docs/gex-llm-patterns/backup-schema.md` (against `development`)
- [ ] Schema SQL; test it inside a rolled-back transaction, then apply
- [ ] Backfill the R1 o4-mini rows (expect 1,412)
- [ ] Runner refactor + ingest
- [ ] Model pilot (40 windows × 3 models) → choose the model and budget
- [ ] A0 bridge → agreement check (gate: κ ≥ ~0.6, otherwise discuss)
- [ ] A1–A5 batches
- [ ] Extension report YAML + figures (fix fig02, remove the synthetic fallbacks)
- [ ] Comment on #260 that Paper 2 is unaffected

## Verification

- **Runner GEX:** for 5 SPY dates it equals `options_daily_summary.total_gex`. With `--exclude-0dte`, the difference equals the 0DTE-only sum.
- **A0 windows:** generated `custom_id`s match the 1,476 from round 1.
- **Pilot:** runs end to end (submit → retrieve → ingest), and re-running ingest changes nothing.
- **Reproduction:** the R1 arm reproduces the published rates from Postgres alone: 3.7% (2021), 32.4% (2022), 20.2% (2023), 100% (2024–25).

Refs #260


---

## Comment by iAmGiG · 2026-10-28T18:24:04Z

## Correction to Finding 1: Paper 2 IS affected by the GEX rebuild (#260)

The opening post says Phase 4A was unaffected because it read raw `options_chains_partitioned` rather than the daily table. That was wrong. Three independent checks:

**1. The raw table was reloaded after Phase 4A ran.** Every SPY row in `gex.options_chains_partitioned` (2008–2026) has `created_at = 2026-02-03`. Phase 4A ran 2026-01-04. Today's raw chains are not what the January script read. (The January batch files `file-46GWLecWpzfrCTU6fQtcsh` / `file-NUB1tA83KVboBvCJqcMEkU` have expired at OpenAI, so the exact inputs cannot be recovered; the stored responses in `.cache/research_cache.db` are the record.)

**2. The LLM's own reported magnitudes match the old convention.** Window ending 2024-09-16: January response says 30/30 positive days, avg $16.34B. Old daily table (`backups.options_daily_summary_pre_rebuild_20261004`) gives $17.03B that day; current data gives $6.06B avg with 50% same-sign. The 2021-06-15 window (no 0DTE) matches both: 4.04 vs 4.04.

**3. Replaying the deterministic criteria (persistence ≥70%, |avg| ≥$5B, flips ≤5) over all SPY 30-day windows:**

| Year | Published (o4-mini) | Old convention (frozen table) | New 0DTE-inclusive |
|---|---|---|---|
| 2020 | 12.2% | 9.0% | 11.7% |
| 2021 | 3.7% | 3.6% | 3.6% |
| 2022 | 32.4% | 26.3% | 40.6% |
| 2023 | 20.2% | 22.5% | 22.4% |
| **2024** | **100%** | **100%** | **10.3%** |
| **2025** | **100%** | **100%** | **13.6%** |

Avg |GEX| 2024: old $16.2B → new $6.5B. Avg persistence 2024: 100% → 69%.

Two separate effects are mixed in the rebuild (2024-03-15: old +12.62B; new ex-0DTE −4.50B; new full −15.35B): BS-on-integer-days vs stored vendor gamma, and 0DTE inclusion.

### Consequences for this issue
- The 0DTE ablation (A4) is the headline, not a side arm. The classifier-only version above already exists at zero cost.
- The LLM arms run on **three series**: old convention (frozen table, SPY, bridge to the published result), new ex-0DTE, new full. This decomposes the two effects.
- Historical range extends to **2008** (SPY/IWM; QQQ from 2011). Coverage is ~250 days/yr throughout.
- Model: **gpt-6-luna** (o4-mini retired on both Chat and Responses endpoints). $0.05/$0.25 per 1M on Batch; whole plan ≈ $8–10 at round-1 token volumes. `reasoning_effort=medium` pinned and recorded.
- The published AIAI/JRFM result is reproducible from the frozen table; the data sections should state the convention and the rebuild date (what #260 asked).

The checklist item "Comment on #260 (Paper 2 unaffected)" is replaced by the comment posted there.


---

