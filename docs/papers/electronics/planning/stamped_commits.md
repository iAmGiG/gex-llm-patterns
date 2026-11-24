# Git commits stamped in the tracked provenance (review item B085)

Checked 2026-11-24 against `origin/main` at `ebdbf65` and GitHub's `refs/pull/*/head` (56 refs; the objects of all of
them were fetched locally to test reachability). The binding record of a result is the sha256 of the stored files
(`results/report.yaml`, `condensed/runs.csv.gz`, the deposit's `SHA256SUMS`), not a commit id: a squash merge leaves the
stamped commit off the history of `main`, and the figure manifests of Paper A were built from a modified working tree
(`git_dirty: true`), so even a reachable id does not name the exact code.

| SHA | Stamped where | Status | Tag |
|---|---|---|---|
| `d4765a1e16cc` | `results/report.yaml`; 12 figure manifests of Paper A (`git_dirty: true` in all of them) | not on `main`; reachable from `refs/pull/303/head` | none needed |
| `aa346430f90b` | 5 figure manifests of Paper B (`git_dirty: false`) | not on `main`; reachable from `refs/pull/303/head` | none needed |
| `e27bdc749ff0` | `runs.csv.gz` (27 runs of the first Batch round, 2026-10-29) | not on `main`; reachable from `refs/pull/263/head` | none needed |
| `872f35263cc9` | `runs.csv.gz` (8 runs, bridge_old and others, 2026-10-30) | not on `main`; reachable from `refs/pull/263/head` | none needed |
| `1ab82c72357d` | `runs.csv.gz` (8 runs of the 2026-11-03 re-run); also inside `clf_version` of every window | not on `main`; reachable from `refs/pull/265/head` | none needed |
| `c25b50c51f6b` | `clf_version` of the three backfilled runs (run_metadata) | not on `main`; reachable from `refs/pull/263/head` | none needed |
| `6a3ff03b784a` | `runs.csv.gz` (11 gpt-oss-20b runs) | not on `main`; reachable from `refs/pull/268/head` | none needed |
| `0295c0615126` | `runs.csv.gz` (9 gpt-oss-20b runs) | ancestor of `origin/main` | none needed |
| `131df2d21a6e` | `runs.csv.gz` (15 Llama 3.1 8B runs) | not on `main`; reachable from `refs/pull/278/head` | none needed |
| `0ff2c9febfe3` | `runs.csv.gz` (87 runs: Qwen pilots and arms) | not on `main`; reachable from `refs/pull/278/head` | none needed |
| `9cbb81d0a9c7` | `runs.csv.gz` (3 Qwen runs) | not on `main`; reachable from `refs/pull/278/head` | none needed |
| `22b7088da57f` | `runs.csv.gz` (1 Qwen run) | not on `main`; reachable from `refs/pull/278/head` | none needed |
| `4de24391a3ca` | `runs.csv.gz` (7 Qwen runs) | not on `main`; reachable from `refs/pull/278/head` | none needed |
| `0477dcebde43` | `runs.csv.gz` (21 reasoning-first and temperature-0 runs) | ancestor of `origin/main` (#282) | none needed |
| `744e6cce4796` | `runs.csv.gz` (2 runs: the second `llamarf_full_spy` run and one more of 2026-11-24) | not on `main`, on no branch and on no pull ref; the object exists locally | `archive/run-744e6cc` (local, annotated) |
| `e58f7d607c42` | `runs.csv.gz` (`r1_o4mini_phase4a_20260104`, written as `e58f7d6`) | ancestor of `origin/main`; also tagged `jrfm-stale-base-attempt-ecfc4ef` | none needed |
| `477bb415abd6` | note in the run record of the two November backfills (the commit that added the result YAML) | ancestor of `origin/main` | none needed |

Totals: 17 ids; 4 are ancestors of `origin/main` (0295c06, 0477dce, e58f7d6, 477bb41); 12 are not on
`main` but sit under a GitHub pull ref (`refs/pull/263`, `265`, `268`, `278`, `303`), which GitHub keeps after the
squash merge; 1 (744e6cc) was on no ref and is now tagged locally; 0 objects are lost. Two of the ids (`1ab82c7`,
`c25b50c`) are the short ids that `clf_version` carries, and both resolve to commits.

To keep the one unreferenced commit on the remote (the authors decide; nothing was pushed):

    git push origin archive/run-744e6cc
