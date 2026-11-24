# Open-weights paper (Paper B): reproducing an LLM evaluation after its hosted model is retired

Short paper (about 16 pages, MDPI class; planned for MDPI *Electronics*, like Paper A, which is planned for the same journal) by Christopher Regan and Ying Xie. Working title:
*Reproducing an LLM Evaluation After Its Hosted Model Is Retired: Open-Weights Models on Stored Requests*.

**Question.** Can an LLM evaluation be reproduced after its hosted model is retired: with the hosted successor alias, and with
open-weights models run locally at pinned revisions on the stored requests?

**Relation to Paper A** ([`../electronics/`](../electronics/), the companion manuscript, cited as `regan2026rerun`). The setting
(obfuscated daily SPY gamma exposure, 30-day windows, the three-threshold rule, the prompt) comes from Paper A and the earlier
publications. Paper A owns the input-lineage finding, the re-run on the complete inputs and the bridge between o4-mini and
gpt-6-luna. This paper quotes those numbers only as cited context or as labelled reference columns ("Paper A"), never as its own
result. Its own results are the three open-weights models (gpt-oss-20b, Llama 3.1 8B, Qwen3-8B) on seven arms each: agreement
with the rule, with the stored o4-mini answers and with gpt-6-luna; unanswered windows and bounds (Qwen3-8B); departures from the
rule; test-retest; tokens and GPU time. Agreement with the rule shows that a model applies criteria that the prompt states; it is
the object of study, not a claim about reasoning or recall. Nothing here is a correction of an earlier paper.
One Zenodo record (issue #274) serves both papers.

Nothing under `docs/papers/electronics/` is edited by this folder; the figures read `docs/papers/electronics/results/` and
`data/backups/gex_llm/condensed/` (both tracked) and import `theme`, `figdata`, `figllm` from `docs/papers/electronics/figures/scripts`.

## Layout

| Path | Content |
|---|---|
| `latex/Regan_Xie_OpenWeights.tex` | main file (class setup, macros, abstract, back matter); one `\input` per part, never one flat file |
| `latex/01_Introduction` .. `06_Conclusion` | introduction (setting, four research questions, contributions), related work (issue #297), methods, discussion, conclusion |
| `latex/04_01_Overview` .. `04_08_Cost` | results: overview table and figure, gpt-oss-20b, Llama 3.1 8B, Qwen3-8B, departures, schema order (reasoning first), repeats and sampling (temperature 0), cost |
| `latex/07_Appendix_A_Schema` | field orders of the JSON schema (verdict first, reasoning first) |
| `latex/Regan_Xie_OpenWeights_Supplement.tex` + `S1_Run_Ledger`, `S2_Detail`, `S3_Engine` | local run ledgers (Tables S1-S3), per-model tables (S4-S6), unanswered windows of Qwen3-8B (S7-S10), engine settings (S11) |
| `latex/references.bib` | own bibliography: entries copied from the Electronics bib, plus six new ones verified on 2026-11-23 (see the header of the file) |
| `figures/scripts/` | `figopen.py` (model registry, output folder, manifest), `bf01`..`bf05` scripts, `run_all.py` (own registry) |
| `figures/output/` | PNG (300 dpi), PDF and a provenance manifest per figure |
| `check_numbers.py` | recomputes the numbers of the text from the tracked files (over 400 checks); the Section 4.6 numbers also need the git-ignored local folder `data/backups/gex_llm/exploratory_llama_reorder_20261108/` (`EXPLORATORY_DIR=...`) |
| `submission/cover_letter.md` | draft cover letter, venue left open |
| `build.sh` | build and checks |

## Build

```bash
bash docs/papers/openweights/build.sh              # article and supplement, page counts, warning summary
bash docs/papers/openweights/build.sh --strict     # also fails on undefined references, bibtex warnings, missing figures, \tbd, stale supplement numbers
bash docs/papers/openweights/build.sh --final      # strict + fails while a \pending marker or a TODO(authors)/TODO(runs) comment remains
bash docs/papers/openweights/build.sh --overleaf   # strict + overleaf/Regan_Xie_OpenWeights_overleaf.zip (git-ignored)
```

Page count: the article is about 16 pages in the MDPI layout; the journal sets no page limit, so figures stay at full text width.

Figures (AutoGex env, `export PYTHONNOUSERSITE=1 PYTHONPATH=$(pwd)`):

```bash
~/miniconda3/envs/AutoGex/bin/python docs/papers/openweights/figures/scripts/run_all.py [--list | --check]
~/miniconda3/envs/AutoGex/bin/python docs/papers/openweights/check_numbers.py
```

Figures: BF1 reproduction ladder, BF2 agreement and kappa per model and arm, BF3 detection rate by period with the Qwen3-8B
bounds and the answered share, BF4 departures by direction and failing criterion, BF5 Llama 3.1 8B verdict first versus
reasoning first (draws the `llamarf_*` arms; `run_all.py --check` reports it as `pending` only if they are missing). BF1 and BF2 show the variants; BF3 adds the reasoning-first dot.

## Where the numbers come from

Every number in the text and the tables has a `% src:` comment naming the tracked file and column or key:
`docs/papers/electronics/results/` (`detection_by_year.csv`, `bridge_agreement.csv`, `missing_answer_bounds.csv`,
`llm_parse_stats.csv`, `reported_vs_computed.csv`, `disagreements.csv`, `stats.yaml`) and `data/backups/gex_llm/condensed/`
(`runs.csv.gz` for requests, retries and GPU hours: `run_metadata.local.seconds` summed over `mode == local`; `detections.csv.gz`,
`windows.csv.gz`). GPU hours are the engine time (process seconds) summed over runs; the elapsed time is shorter because runs overlapped on several GPUs (Qwen3-8B: 98.5 summed hours, 31.7 elapsed on four GPUs; `unanswered_gpu_time.csv`). The unanswered-window analyses (recoverable verdicts, three agreements, contested windows, answering model, repeat stability) come from `unanswered_*.csv` in the same folder.

## The variant runs (done; named by model label and arm prefix)

Three local runs vary one setting each and are stored under their own labels, so they never mix with the arms of the three models
(registered in `scripts/validation/electronics/common.py`, 48 arms in all):

* **D-33**: Llama 3.1 8B with the reasoning field first (`common.REASONING_FIRST_ORDER`), seven arms: model `llama-3.1-8b-instruct-rf`,
  arms `llamarf_*` (12,379 requests, 2.35 GPU-hours). Findings: it no longer says yes to every window (47.1% of the complete series
  detected, rule 13.0%), but it does not follow the rule (agreement 56.7%, kappa 0.096), so the verdict-first order explains the
  constant answer and not the failure. Section 4.6, Table 3, Figure 5.
* **D-34**: temperature 0 in every request on the published inputs: `gpt-oss-20b-t0` / `osst0_bridge_jan` (1,614 requests) and
  `llama-3.1-8b-instruct-t0` / `llamat0_bridge_jan` (1,590 requests). Temperature 0 changes neither result. Section 4.7, Table 4.
* Totals: the abstract, Table 1 and the conclusion count the three models only (47,176 requests, 111.8 summed GPU-hours); Table 5 adds the
  variants (15,583 requests, 3.1 GPU-hours; 62,759 requests and 114.9 GPU-hours in all local runs). Only the variants record
  `run_metadata.local.request_sampling` and `schema_property_order`; the earlier runs do not (limitation, Section 5.5).
* The exploratory 40-window run of 2026-11-08 stays outside the stored arms (git-ignored folder `exploratory_llama_reorder_20261108/`).

No `\pending` or `TODO(runs)` remains; `build.sh --final` fails only on the `TODO(authors)` items and the DOI marker.

## Open items for the authors

CRediT roles, funding, acknowledgments and AI-use statement, the Zenodo DOI (one record with Paper A), the title of the
companion manuscript in `references.bib`, the Special Issue (if any). The default sampling values of
the existing runs are not stored in their run metadata (review item C110): the paper states that they come from each model's
`generation_config.json` (visible in the vLLM logs) and lists it as a limitation. Recoverable verdicts in truncated Qwen3-8B
answers (review item E7) are mentioned only as future work, without numbers.
