# Zenodo deposit: steps (issue #274), draft of 2026-11-24

Nothing here has been done: no record exists and Zenodo has not been contacted. The authors decide the licence and the
basis for it (review item B094) before step 3.

1. Build and check the zip on this machine (no network):

       python scripts/validation/electronics/08_package_release.py
       python scripts/validation/electronics/08_package_release.py --check data/backups/gex_llm/release/regan_xie_electronics_tables_<date>.zip

   The current zip is `regan_xie_electronics_tables_20261125.zip` (204 runs, 89,904 answers; the counts of
   `condensed/runs.csv.gz` and `condensed/detections.csv.gz`); rebuild it if the tables change. `--check` must print `CHECK ok`. The zip carries the four tables, `detections_replaced.parquet`, `raw_backfill/` (the
   input and output of the three backfilled o4-mini runs, with `MANIFEST.csv`), the README and `SHA256SUMS`.
2. Sign in at zenodo.org with the account that will own the record and start a new upload.
3. Fill the form from `zenodo_metadata.json` (type Dataset; title; description; the two creators; keywords; version;
   language; related identifiers). Set the licence field last: it is a placeholder in the JSON.
4. Press Reserve DOI before publishing; the form then shows the DOI. Upload the zip. Do not publish yet.
5. Put the DOI into both manuscripts (table below), rebuild with `docs/papers/build_all.sh --final`, and publish the
   record at submission, when the access date is set as well. Publishing fixes the files: a change needs a new version.
6. Optional, after the papers are published: add their DOIs as related identifiers (isSupplementTo) in a new version.

## Where the DOI goes

| File and line (2026-11-25, branch `paper/b-finish`) | What |
|---|---|
| `docs/papers/electronics/latex/Regan_Xie_Electronics.tex:159` (the TODO) and `:160` (`\dataavailability`) | add the DOI and update the access date |
| `docs/papers/openweights/latex/Regan_Xie_OpenWeights.tex:147` (the TODO) and `:148` (`\dataavailability`, which holds `\pending{authors: Zenodo DOI}`) | replace the `\pending` marker by the DOI |
| `docs/papers/electronics/submission/cover_letter.md:58` | the TODO for the DOI |

Line numbers shift when these files are edited; grep for `TODO(authors)` and `Zenodo DOI` to find them again. The record
is shared by both papers, so both Data Availability Statements say so; keep them in step.
