# Open-weights paper (Paper B): reproducing an LLM evaluation after its hosted model is retired

Short paper (target 12-15 pages, MDPI class; the venue is not chosen) by Christopher Regan and Ying Xie. Working title:
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
| `latex/04_01_Overview` .. `04_08_Cost` | results: overview table and figure, gpt-oss-20b, Llama 3.1 8B, Qwen3-8B, departures, schema order (pending run), repeats and sampling (pending run), cost |
| `latex/07_Appendix_A_Schema` | field orders of the JSON schema (verdict first, reasoning first) |
| `latex/Regan_Xie_OpenWeights_Supplement.tex` + `S1_Run_Ledger`, `S2_Detail`, `S3_Engine` | local run ledgers (Tables S1-S3), per-model tables (S4-S6), engine settings (S7) |
| `latex/references.bib` | own bibliography: entries copied from the Electronics bib, plus six new ones verified on 2026-11-23 (see the header of the file) |
| `figures/scripts/` | `figopen.py` (model registry, output folder, manifest), `bf01`..`bf05` scripts, `run_all.py` (own registry) |
| `figures/output/` | PNG (300 dpi), PDF and a provenance manifest per figure |
| `check_numbers.py` | recomputes the numbers of the text from the tracked files (175 checks); the Section 4.6 numbers also need the git-ignored local folder `data/backups/gex_llm/exploratory_llama_reorder_20261108/` (`EXPLORATORY_DIR=...`) |
| `submission/cover_letter.md` | draft cover letter, venue left open |
| `build.sh` | build and checks |

## Build

```bash
bash docs/papers/openweights/build.sh              # article and supplement, page counts, warning summary
bash docs/papers/openweights/build.sh --strict     # also fails on undefined references, bibtex warnings, missing figures, \tbd, stale supplement numbers
bash docs/papers/openweights/build.sh --final      # strict + fails while a \pending marker or a TODO(authors)/TODO(runs) comment remains
bash docs/papers/openweights/build.sh --overleaf   # strict + overleaf/Regan_Xie_OpenWeights_overleaf.zip (git-ignored)
```

Figures (AutoGex env, `export PYTHONNOUSERSITE=1 PYTHONPATH=$(pwd)`):

```bash
~/miniconda3/envs/AutoGex/bin/python docs/papers/openweights/figures/scripts/run_all.py [--list | --check]
~/miniconda3/envs/AutoGex/bin/python docs/papers/openweights/check_numbers.py
```

Figures: BF1 reproduction ladder, BF2 agreement and kappa per model and arm, BF3 detection rate by period with the Qwen3-8B
bounds and the answered share, BF4 departures by direction and failing criterion, BF5 Llama 3.1 8B verdict first versus
reasoning first (placeholder until the arms `llamarf_*` exist; `run_all.py --check` reports it as `pending`).

## Where the numbers come from

Every number in the text and the tables has a `% src:` comment naming the tracked file and column or key:
`docs/papers/electronics/results/` (`detection_by_year.csv`, `bridge_agreement.csv`, `missing_answer_bounds.csv`,
`llm_parse_stats.csv`, `reported_vs_computed.csv`, `disagreements.csv`, `stats.yaml`) and `data/backups/gex_llm/condensed/`
(`runs.csv.gz` for requests, retries and GPU hours: `run_metadata.local.seconds` summed over `mode == local`; `detections.csv.gz`,
`windows.csv.gz`). GPU hours are engine wall-clock time summed over chunks on shared GPUs.

## Pending runs (placeholders `\pending{...}` and `% TODO(runs)`)

* **D-33**: the seven Llama 3.1 8B arms again with the reasoning field first (label `llama-3.1-8b-instruct-rf`, arms
  `llamarf_*`). Only evidence so far: an exploratory 40-window run of 2026-11-08, outside the stored arms (32 of 40 detected, 26 of
  40 equal to the rule; verdict-first pilot on the same windows: 40 detected, 20 equal). Fills Table 3 and Figure 5 (Section 4.6),
  the abstract, Section 5.4 and the conclusion; add ledger rows to Table S2.
* **D-34**: decoding control on the published inputs, gpt-oss-20b and Llama 3.1 8B (verdict first) with temperature 0
  (labels `gpt-oss-20b-t0`, `llama-3.1-8b-instruct-t0`, arms `osst0_bridge_jan`, `llamat0_bridge_jan`). Fills Table 4 (Section 4.7),
  the abstract, Section 5.4 and the conclusion.
* After both runs: `05_report.py` rerun by the branch that owns it, `common.ARMS`/`theme.ARM_LABELS` extended there, then
  `run_all.py`, update totals in the abstract/Table 1/Table 5 (`check_numbers.py` totals will change), `build.sh --final`.

## Open items for the authors

CRediT roles, funding, acknowledgments and AI-use statement, the Zenodo DOI (one record with Paper A), the title of the
companion manuscript in `references.bib`, the journal, and the page budget (see the build output). The default sampling values of
the existing runs are not stored in their run metadata (review item C110): the paper states that they come from each model's
`generation_config.json` (visible in the vLLM logs) and lists it as a limitation. Recoverable verdicts in truncated Qwen3-8B
answers (review item E7) are mentioned only as future work, without numbers.
