# Electronics (MDPI) extension: regime detection under temporal obfuscation, re-run on corrected inputs

Extended version of *Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal
Obfuscation* (AIAI 2026, Springer, in press), for the MDPI *Electronics* Special Issue "Timely AI Advancements and
Interdisciplinary Synergies for Intelligent Modeling". Authors: Christopher Regan and Ying Xie (Kennesaw State
University). Tracking issue: [#261](https://github.com/iAmGiG/gex-llm-patterns/issues/261). Branch: `paper/electronics`.

The extension has to consist of new experiments beyond the AIAI paper and the JRFM article (MDPI, manuscript
jrfm-4256551), and it cites both. While it was being prepared, the exact inputs of the published Phase 4A run were
recovered and found to lack the put leg of dealer gamma exposure (GEX) from 2023-09-29 onward, and the inputs of the
published 2024-versus-2020 baselines turned out to carry calendar dates. The article is therefore framed as a
**data-integrity correction with a controlled LLM re-test**, not as an incremental extension.

## Status (2026-10-29)

| Part | State |
|---|---|
| Manuscript, [`latex/`](latex/) | Skeleton that builds with `build.sh` (23 pages as built, most of it placeholders): MDPI front matter, Sections 1 to 6, Appendices A to C. Appendix A (prompt, schema, request body) is transcribed from the code and checked against it; Appendix B is the verbatim text of the four audited series statements plus the statement of the scaling factor. The abstract, most prose, every result number, the per-year tables of Appendix C and the title are still placeholders (`\tbd{}`, a working title); each heading carries a `% TODO(tag)` guidance comment. |
| Figures, [`figures/`](figures/) | One script for each of the 12 figures, `run_all.py`, `theme.py`, `figdata.py`, `figllm.py`. `figures/output/` is empty: the scripts read `results/` and the parquet copies and stop with a message when an input is missing, so nothing has been drawn yet. |
| Results, `results/` | Empty (an empty directory, so git does not track it yet). Written by `scripts/validation/electronics/05_report.py` once series, windows and model runs exist. |
| Pipeline, [`scripts/validation/electronics/`](../../../scripts/validation/electronics/) | `common.py` (the contract: 11 series and 18 arms, extended on 2026-10-29 with the Phase 3/4 date-effect arms and the scaled QQQ/IWM series), scripts 00 to 05, the schema SQL and a runbook README. A first build of the SPY series and windows and the January backfill exist as parquet under `data/backups/gex_llm/`. The pipeline has submitted no `gpt-6-luna` request; the only calls so far were the probe of 2026-10-28. |
| Database tables | `backups.gex_llm_regime_*` do **not** exist. The DDL waits for the documentation pull request in the database repository and the maintainer's approval; until then every script writes parquet only. |
| Corrections | The public record is [`docs/papers/CORRECTIONS.md`](../CORRECTIONS.md), tracked in [#262](https://github.com/iAmGiG/gex-llm-patterns/issues/262). Whether and how AIAI and JRFM are corrected is for the authors and the editors; nothing in this folder edits `docs/papers/jrfm/`. |
| Submission | Not submitted. Open decisions for the authors are listed in [`planning/02_decisions_log.md`](planning/02_decisions_log.md) (section 3). The bibliography entry of the JRFM article still says "in production" and needs volume, article number and DOI. |

## What is new relative to AIAI 2026 and the JRFM article

The JRFM article combines the IEEE BigData 2025 paper and the AIAI 2026 paper. This article cites all three and adds:

1. **A data-integrity correction.** The published inputs are reconstructed from the surviving batch file and compared
   with five other daily GEX series; the published 2024 and 2025 inputs turn out to be call-only (next section).
2. **A model bridge.** `gpt-6-luna` re-labels the exact published inputs (the published `o4-mini` is retired), so the
   effect of the model is separated from the effect of the data.
3. **Convention sensitivity.** The rebuilt series with and without same-day expiries (0DTE ablation), the pre-rebuild
   archive and the call leg alone are compared by deterministic replay and by model.
4. **Wider scope.** 2008 to 2019, before weekly and daily expirations; QQQ and IWM, unscaled (the fixed $5 B threshold
   is a floor for them) and with a disclosed per-symbol scaling of the input series (`new_full_scaled`); the
   post-publication period (windows ending in 2026); and a late-session intraday check.
5. **A date-effect rerun.** The 2024 and 2020 baselines behind the published 81.2% versus 12.1% contrast were run with
   ISO dates as day labels and on two sign conventions. `gpt-6-luna` re-runs the identical values with the dates and
   with relative labels (arms `p34_*`) next to the stored `o4-mini` answers (`r1_p3_o4mini`, `r1_p4_o4mini`).
6. **Overlap-aware statistics.** Windows have stride one, so every p-value comes with a calendar-quarter block
   bootstrap (2,000 draws, seed 261) and a non-overlapping 30-day subsample; the AIAI and JRFM p-values treated the
   windows as independent.
7. **Stored inputs and answers.** Every series value, window, deterministic label, request and model answer is stored,
   so each table and figure is regenerated from stored data.

## The data-integrity correction

Evidence (command-level, with the per-day comparison files) is in [`planning/forensics/`](planning/forensics/): the
[first memo](planning/forensics/2026-10-28_memo_published_inputs.md) (put-row loss) and the
[second-audit memo](planning/forensics/2026-10-28_memo_second_audit.md) (dated prompts and sign conventions of the
baselines, synthetic figures, headline numbers).

- The exact Phase 4A inputs (1,476 SPY 30-day windows sent to `o4-mini` on 2026-01-04) survive in
  `reports/validation/paper2_regime_windows/batch_jobs/` and are read by `common.load_phase4a_inputs()`.
- From 2023-09-29 through 2025-12-31 (565 of 565 trading days) the daily value shown to the model equals the call leg of
  the option chain alone, same-day expiries included, to within 0.005 B: the puts contributed nothing. Through
  2023-09-28, 900 of 940 days equal today's full net GEX and 39 scattered days are call-only.
- Cause: upstream issue #24 of gex-database-infrastructure (fix commit `2c16a4d`, 2026-02-03). The PostgreSQL loader
  read `option_type` from a column the vendor data does not have, labelled every contract a call, and the table's unique
  key discarded the put of each call and put pair. The raw table was reloaded on 2026-02-03.
- The pre-rebuild daily table (archived as `backups.options_daily_summary_pre_rebuild_20261004`) was built on 2026-01-15
  from the same put-less raw table, so it is put-less on the same dates and is not a clean "old convention".
- Replaying the paper's criteria (at least 21 of 30 days of one sign, mean |GEX| of at least $5 B, at most 5 sign flips)
  gives 100% and 100% for 2024 and 2025 on the January inputs and 10.3% and 13.6% on the complete series. The `o4-mini`
  labels equal the rule on every parsed window, so the model followed its inputs: the defect is in the data.
- January's trading-day list lacks 2023-07-12 and 2024-03-11, so 58 published windows span 31 trading days.
- The Phase 3 (2024) and Phase 4 (2020) baselines of 2025-11-20 (223 windows each, 81.2% and 12.1%) sent ISO dates, not
  "Day T-k" labels, and the two series are on different conventions (2024: gross call-plus-put magnitude with a negative
  sign imposed, negative on 242 of 252 days; 2020: magnitude only). phi of the published contrast is 0.692, not the
  0.672 printed in AIAI. The inputs and answers survive; `common.load_phase34_inputs()` reads them, and
  `common.obfuscate(..., labels="dated")` plus `build_prompt()` reproduces all 223 + 223 dated prompts byte for byte
  (checked 2026-10-29), so the dated and the obfuscated arms differ in the day labels only.

How the article words all of this, and what is sent to the editors of AIAI and JRFM, is for the authors to decide
(see the decisions log, Q-02, and issue #262).

## Layout

```
docs/papers/electronics/
  README.md           this file
  build.sh            build the PDF (below)
  latex/              Regan_Xie_Electronics.tex, 01_Introduction ... 06_Conclusion, 07_Appendix, references.bib
  figures/scripts/    figNN_<name>.py (12), run_all.py, theme.py, figdata.py, figllm.py
  figures/output/     figNN_<name>.png (300 dpi), .pdf and a provenance manifest .json; written by the scripts
  results/            CSV and YAML tables written by 05_report.py; the only numbers the manuscript may quote
  planning/           00_design.md (design memo v2), 01_issue_261_archive.md, 02_decisions_log.md, forensics/
```

## Build

```bash
docs/papers/electronics/build.sh            # pdflatex, bibtex, pdflatex, pdflatex; page count and warning summary
docs/papers/electronics/build.sh --strict   # as above, then exit 1 unless the manuscript is submission-ready
docs/papers/electronics/build.sh --clean    # remove the TeX build files (the PDF is kept)
```

- The MDPI class is `\documentclass[electronics,article,submit,moreauthors,pdftex]{Definitions/mdpi}`. `build.sh` puts
  `../../jrfm` on `TEXINPUTS` and `BSTINPUTS` so that `Definitions/` resolves to `docs/papers/jrfm/Definitions`;
  nothing in `docs/papers/jrfm/` is modified. For Overleaf or the MDPI submission zip copy `Definitions/` next to the
  `.tex` file; the sources do not change.
- TeX Live is the shared install named in the script; set `TEXLIVE_BIN` to use another one. The build stops at the first
  failing pass and prints the tail of its log. The output is `latex/Regan_Xie_Electronics.pdf` plus
  `latex/build_*.log` (the TeX auxiliary files and logs are git-ignored, the PDF is not).
- The sections are included as `./NN_Name` and `build.sh` refuses to run when one of them is missing, because the JRFM
  folder has files of the same names (`01_Introduction.tex`, `04_Results.tex`, ...) that TeX would otherwise find on the
  search path and typeset silently.
- A figure whose PNG does not exist yet is drawn as a boxed placeholder and logged as `Missing figure file`.
- The summary prints the undefined references and citations, the bibtex warnings, the missing figures, the unresolved
  `\tbd` placeholders (in total, for the main file and for every file; comments do not count), a working title left in
  `\Title`, the open `% TODO(` markers and the overfull boxes. `--strict` fails on the first five of these and on a
  reference that still changed in the last pass; the TODO markers and the overfull boxes are only reported. The main
  file keeps three `\tbd` on purpose (abstract, and the access date and the data release of the Data Availability
  Statement); they are the last ones to fill.

## Figures

```bash
source ~/miniconda3/etc/profile.d/conda.sh && conda activate AutoGex
export PYTHONNOUSERSITE=1 PYTHONPATH=$(pwd)          # from the repository root
python docs/papers/electronics/figures/scripts/run_all.py              # all twelve figures
python docs/papers/electronics/figures/scripts/run_all.py fig04 fig10  # a selection
python docs/papers/electronics/figures/scripts/run_all.py --check      # which outputs exist and which are stale
python docs/papers/electronics/figures/scripts/fig02_convention_window.py --window-end 2024-03-15   # one script, its own options
```

Every script reads only `results/*.csv|yaml` and the parquet copies of the result tables, draws at the printed text
width of the class (6.14 in, 8 to 9 pt, light theme), and writes the PNG, a PDF and a manifest (inputs with sha256 and
row counts, git sha, library versions). A missing input stops the figure with a message that names it: there is no
synthetic fallback. The manuscript includes `figures/output/<stem>.png` through the registry at the top of
`latex/Regan_Xie_Electronics.tex`, which `run_all.py` reads, so a renamed script and a stale registry are reported.
Manuscript figure numbers follow the text, file numbers follow the figure list of the data audit: Figures 5, 7 and 12
of the manuscript are `fig12_threshold_sensitivity`, `fig05_llm_arms_by_year` and `fig07_llm_classifier_fidelity`.

## Data provenance

**Tables.** Four tables and one view, defined in `scripts/validation/electronics/sql/gex_llm_regime_schema.sql` (every
column commented): `backups.gex_llm_regime_series` (the daily values shown to the model), `_windows` (30-day windows
with the exact input vector, its sha256 and the deterministic label), `_runs` (one row per OpenAI Batch job or pilot,
written at submit time so the batch id is never lost), `_detections` (one row per window and run) and the view
`_rates_summary`. They are standalone: no foreign keys into the core tables. Until the DDL is approved the same columns
are written as parquet to `data/backups/gex_llm/tables/{series,windows,runs,detections}/`; raw batch files and manifests
per run are in `data/backups/gex_llm/<run_id>/` (the raw JSONL and the large parquet files are git-ignored, see the
decisions log D-17). The archive tables `backups.*_pre_rebuild_20261004` are read, never written.

**Series and arms.** `common.SERIES` holds 11 series: the six of the study (`jan2026_phase4a`, `call_only`, `old_bs`,
`new_full`, `new_ex0dte`, `intraday_late`) and the derived inputs of the rerun arms (`new_full_scaled`, `p3_2024`,
`p3_2024_dated`, `p4_2020`, `p4_2020_dated`; the Phase 3/4 series use their own calendar, window rule J, and the
`_dated` ones carry the ISO dates sent in November 2025). `common.ARMS` holds 18 arms: 15 model arms and three
backfills of stored `o4-mini` answers. The definitions are in Appendix B of the manuscript, in the pipeline README
(section 3) and in the decisions log (D-04 to D-08).

**Run ids.** `<arm>_<model>_<mode>_<UTC timestamp>`, with `_c<k>` appended for each chunk of at most 1,500 requests; a
test-retest repeat is stored under the arm `<arm>#rep1` with a `custom_id` ending in `#rep1`. The three backfilled runs
carry fixed ids and make no API call:

| Run id | Arm | OpenAI batch | Windows |
|---|---|---|---|
| `r1_o4mini_phase4a_20260104` | `r1_o4mini` | `batch_695ab77d2fe8819084e397a55f10e6bc` (`o4-mini-2025-04-16`) | 1,476 (64 answers lost to a parsing error in January are re-parsed from the stored output) |
| `r1_p3_o4mini_20251120` | `r1_p3_o4mini` | `batch_691ea7f7b79481909f4667eaff640f26` | 223 (Phase 3, 2024, dated prompts) |
| `r1_p4_o4mini_20251120` | `r1_p4_o4mini` | `batch_691f37d94ef0819099136e88a69bef82` | 223 (Phase 4, 2020, dated prompts) |

Only runs paid in this study count as spend (`common.counts_toward_budget()`); the backfills are shown apart in the
ledger.

**Dates that define the data.**

| Date | Event |
|---|---|
| 2025-11-20 | Phase 3 (2024) and Phase 4 (2020) baseline batches (`o4-mini`, 223 windows each) with ISO dates as day labels |
| 2026-01-02 | SPY options re-collected through the PostgreSQL writer that dropped the puts (upstream #24) |
| 2026-01-04 | Phase 4A batch run: the published inputs (1,476 windows, ends 2020-02-13 to 2025-12-31) |
| 2026-01-15 | the pre-rebuild daily table is computed from the same put-less raw table |
| 2026-02-03 | fix of #24 (`2c16a4d`); the raw options table is reloaded with the puts |
| 2026-07-25 | equity intraday rows before this date carried the previous day's chain (upstream #64), so the intraday check starts on 2026-07-27 |
| 2026-09-14 | the `gpt-6-luna` model object is created (the API alias has no dated snapshot) |
| 2026-10-04 | the pre-rebuild daily table is archived as `backups.options_daily_summary_pre_rebuild_20261004` |
| 2026-10-08 | `gex.options_daily_summary` is rebuilt from stored per-contract gamma, same-day expiries included |
| 2026-10-12 | equity options move from Alpha Vantage to Cboe delayed quotes, so every window ends on or before 2026-10-09 |

## Related issues and documents

- [#261](https://github.com/iAmGiG/gex-llm-patterns/issues/261): this extension (corrections to its first post are in
  its comments).
- [#260](https://github.com/iAmGiG/gex-llm-patterns/issues/260): upstream notice that the daily GEX convention changed
  on 2026-10-08 (same-day expiries now included); it stays open until the authors decide how the published papers are
  corrected.
- [#262](https://github.com/iAmGiG/gex-llm-patterns/issues/262): tracking issue for the corrections to the published
  results (IEEE BigData 2025, AIAI 2026, JRFM 2026); the public record is [`docs/papers/CORRECTIONS.md`](../CORRECTIONS.md).
- gex-database-infrastructure (private repository): [#164](https://github.com/iAmGiG/gex-database-infrastructure/issues/164),
  the follow-up from this side (the archive daily tables are put-less for SPY 2023-10 to 2025-12; proposes a put and
  call balance check at load); [#24](https://github.com/iAmGiG/gex-database-infrastructure/issues/24), the root cause of
  the put-row loss; [#64](https://github.com/iAmGiG/gex-database-infrastructure/issues/64), the intraday T-1 chain.
- gex-database-infrastructure `docs/009_PROJECT_BACKUP_STRATEGY.md`, which the storage follows (three copies:
  Postgres, parquet, raw JSONL; documentation before DDL); the documentation for these tables is
  `docs/gex-llm-patterns/backup-schema.md` on branch `docs/gex-llm-regime-tables`.
- [#164](https://github.com/iAmGiG/gex-llm-patterns/issues/164) of this repository (closed): the earlier upgrade of the
  Paper 1 revision to `o4-mini`, the model that is now retired and has to be bridged.

## Scripts

[`scripts/validation/electronics/`](../../../scripts/validation/electronics/) holds the pipeline; its
[README](../../../scripts/validation/electronics/README.md) has the run order, flags, cost and safety rules.

| Script | Purpose |
|---|---|
| `common.py` | the shared contract: registries of series and arms, model configuration, obfuscation, prompt and classifier bridge, JSON schema, cost, paths |
| `00_env_check.py` | read-only check of environment, database, Phase 4A files and model object |
| `01_build_series.py` | the daily GEX series, one (series, symbol) per run |
| `02_build_windows.py` | 30-day windows and deterministic labels (no model, no cost) |
| `03_backfill_round1.py` | the published `o4-mini` answers as arms `r1_o4mini`, `r1_p3_o4mini` and `r1_p4_o4mini` (no API call) |
| `04_llm_runner.py` | `gpt-6-luna` Batch runs: generate, submit, poll, retrieve, ingest, pilot, retry, status, with a cost ledger |
| `05_report.py` | every table and number of the manuscript, written to `results/` |
| `sql/gex_llm_regime_schema.sql` | the DDL, idempotent, applied only after approval |

## Before submission

1. Run steps 0 to 5 of the pipeline README (series, windows, backfills, pilot, bridge gate, arms, report); decide the
   open questions of the decisions log first (spend, agreement gate, primary analyses).
2. `run_all.py` for the figures, then fill every `\tbd{}` and `% TODO(...)` of the sections from `results/`; write the
   abstract and choose the title.
3. State the authoritative copy of the result tables (parquet release, and the `backups` schema once the DDL is
   approved) in Section 3.7 and in the Data Availability Statement. The raw batch files (the Phase 3, 4 and 4A inputs
   and answers included: `reports/validation/paper2_regime_windows/batch_jobs/` and `data/backups/gex_llm/<run_id>/`) and
   the series and windows parquet are git-ignored and exist on this machine only; decide how they are released
   (decisions log, Q-09).
4. `build.sh --strict` must end with `STRICT: ok`; commit from `paper/electronics` (no attribution lines).

## Keeping Appendices A and B in step with the code

The prompt, the schema and the request body of Appendix A are transcribed from
`MechanicsPromptBuilder.build_regime_prompt`, `common.REGIME_JSON_SCHEMA` and `common.chat_body`. Appendix B.1 to B.4 are
the four statements of the data audit of 2026-10-28 (`sql_series_a_frozen`, `_b_new`, `_c_ex0dte`, `_d_intraday.sql`),
verbatim and comments included (the audit working folder is not in the repository, so the appendix is the repository's
copy); B.5 adds the statement of the scaling factor, tested read-only on 2026-10-29. After any change to the prompt, the
schema or the model configuration, re-check Appendix A from the repository root (the typeset symbols are written `<=`,
`>=` and `->` in the `.tex` file and set as symbols by the `prompt` listing style):

```bash
python - <<'PY'
import json, re, sys
sys.path.insert(0, "scripts/validation/electronics")
import common

tex = open("docs/papers/electronics/latex/07_Appendix.tex").read()
listing = lambda style: re.search(r"\\begin\{lstlisting\}\[style=%s[^\]]*\]\n(.*?)\n\\end\{lstlisting\}" % style, tex, re.S).group(1)
seq = common.obfuscate([float(i) * 1e8 - 1.5e9 for i in range(30)])
real = common.build_prompt(seq)
table = "\n".join(l for l in real.split("\n") if l.startswith("Day T"))
rebuilt = listing("prompt").replace("<=", "\u2264").replace(">=", "\u2265").replace("->", "\u2192").replace("{gex_data_table}", table)
print("prompt (A.2) matches the code:", rebuilt == real)
schema = json.loads(re.findall(r"\\begin\{lstlisting\}\[style=appcode\]\n(.*?)\n\\end\{lstlisting\}", tex, re.S)[0])
print("schema (A.3) matches the code:", schema == common.chat_body("x")["response_format"])
PY
```

## Conventions

- Numbers in the manuscript come from `results/` or the stored tables and are never typed by hand; a number that is
  not available yet is `\tbd{}`.
- Windows ending in 2026 are the *post-publication period*, never "out-of-sample": `gpt-6-luna` was created on
  2026-09-14 and its training cutoff is undocumented.
- Detection is reported as the binary label `regime_detected` (model) and `clf_should_detect` (rule); the fixed $5 B
  and $3 B thresholds are not rescaled, so QQQ and IWM show the floor effect as it is. The scaled arms change the input
  series, not the thresholds or the prompt, and are labelled as a protocol change.
- The published `o4-mini` result is the 1,412 answers without the `recovered_2026` flag; the 64 re-parsed answers are
  reported separately (`r1_o4mini_all`).
- `docs/papers/jrfm/` (the JRFM article) is never edited from here.
- Commits on `paper/electronics` are made by Chris, without attribution lines.
