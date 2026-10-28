# Corrections to published results

**Maintained by the authors (C. Regan, Y. Xie). Last updated 2026-10-28.**

This page records problems found in our published results, what caused them, what the corrected numbers are, and the status of formal corrections. It exists because the repository is public and readers of the papers should not have to find these things out from the code. Evidence for every item is in `docs/papers/electronics/planning/forensics/` (two memos with command-level evidence, the recovered inputs, per-day comparisons, and a claim inventory with file:line anchors). Items were established by automated forensic passes and then tested by independent adversarial re-analysis against the primary files; nothing below rests on a single reading.

Formal corrections (a corrigendum for the AIAI 2026 paper, a correction for the JRFM article, a note for the IEEE BigData 2025 paper and its arXiv version) are in preparation; drafts live next to each paper's sources under `corrections/`. The extension study tracked in issue #261 re-runs the analysis on corrected data with every input and label stored.

## Paper 2 — *Validating LLM Structural Reasoning: Detecting Persistent Market Regimes Through Temporal Obfuscation* (AIAI 2026, Springer LNCS) and the combined article in JRFM (MDPI, 2026)

### A. The 2024–2025 inputs lacked put-side exposure (data defect)

- The multi-year run of January 2026 (Phase 4A/"Phase 5", 1,476 SPY 30-day windows) was generated from a database load in which every contract had been labelled a call and the put of each pair discarded (`option_type` was read from a column the vendor data does not have; the de-duplication key then dropped the second row). Upstream fix: gex-database-infrastructure issue #24, 2026-02-03. **From 2023-09-29 through 2025-12-31 every daily value shown to the model equals call-side GEX only** (565/565 days, within 0.005 B); before that, 900 of 940 days equal the complete net GEX.
- Call-only exposure is positive by construction and roughly twice the net, which is exactly the published 2024–2025 signature (100% detection, 30/30 positive days, ~$20 B). Replaying the paper's own criteria (≥ 21 of 30 days same sign, mean |GEX| ≥ $5 B, ≤ 5 sign flips) on the exact recovered inputs reproduces the published yearly rates within 1 pp; on the complete series the same criteria give **10.3% for 2024 and 13.6% for 2025** instead of 100%. The 2020–2021 rows are unaffected, 2022 nearly so, 2023 mixed.
- Affected: AIAI Table 4 / JRFM Table 5 rows for 2024 and 2025, the pooled 646/1,412 = 45.8% (pre-break windows 117/866 = 13.5%), the magnitude-growth claim, AIAI Fig. 5 / JRFM Fig. 5 (2024 histogram), AIAI Fig. 6 / JRFM Fig. 8, and the "2023→2024 structural shift" interpretation.
- The model's labels equal the deterministic criteria on all 1,476 windows, so the model tracked its inputs; the defect is in the data. January's trading-day list also lacked 2023-07-12 and 2024-03-11 (58 windows span a skipped day).

### B. The 2024-vs-2020 baseline contrast (81.2% vs 12.1%) was not obfuscated and mixed two sign conventions

- The two runs behind that contrast (November 2025) were sent **with calendar dates visible** (30 ISO dates per prompt, 223/223 prompts in each run), not with the "Day T−29 … T+0" labels the papers describe. All other runs (Phase 1, the Phase 2 controls, the multi-year runs, Phase 4A) were obfuscated as described. The prompts contained only daily net GEX (no spot price or days-to-expiration).
- The 2024 series in that run is the gross magnitude (call + put dollar gamma, same-day expiries excluded) with a negative sign imposed (negative on 242 of 252 days; the 10 other days are backfilled placeholder rows that drive the 42 "rejected" windows); the 2020 series is a magnitude-only, always-positive series. Under one consistent signed definition neither year is a single-sign regime (2024: 157 positive / 95 negative days; 2020: 159 / 93). The "Dominant sign: Negative (2024) vs Positive (2020)" row of Table 3 and the "persistent negative regime" narrative are convention artifacts.
- φ recomputed from 181/223 vs 27/223 is **0.692** (JRFM prints 0.69); the AIAI abstract's 0.672 does not reproduce.

### C. Figures

- AIAI Fig. 6 / JRFM Fig. 8 (detection progression): the image in both PDFs is the figure script's **synthetic fallback** (27/223, 8/223, 72/223, 45/223, 223/223, 74/74; "360% growth"), not the Phase 4A data (213/26, 241/9, 244/79, 228/46, 241/241, 245/245).
- AIAI Fig. 4 / JRFM Fig. 4 (selectivity examples) and JRFM Fig. 2 (regime-window example) are synthetic illustrations; the JRFM captions describe them as real windows.
- AIAI Fig. 3 / JRFM Fig. 3 (validation pipeline) hard-codes a "6.3% (n = 52)" false-positive rate and φ = 0.672 that exist in no result file. The Phase 2 controls give: shuffled 2024-Q1 33/54 = 61.1%, shuffled 2020 27/223 = 12.1%, transitional 0/255, low-magnitude 0/277 (pooled 60/809 = 7.4%). "0% false positives" holds only for the transitional and low-magnitude controls.

### D. Numbers

- "$23 B" (AIAI Table 4 and text) matches no stored series; the yearly window means are $3.0 / 4.9 / 5.5 / 9.6 / 20.3 / 19.0 B (as JRFM Table 5 prints). "+360% ($5 B → $23 B)" is arithmetic on numbers not in the data (2021→2024 is +317%; 2020→2024 is +585%, which JRFM rounds to +577%). All 2024–2025 magnitudes are call-only in any case (item A).

## Paper 1 — *Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing* (IEEE BigData 2025 workshop; arXiv 2512.17923; journal version in preparation)

- The scalar GEX series behind the single-day results (242 days of 2024) is the **negative of the unsigned sum** of call and put dollar gamma, excluding same-day expiries. "GEX < −$2 B on all 242 days" therefore holds by construction and carries no regime information. Under the calls-positive/puts-negative convention stated in the paper, the same dates have 93 negative days and a mean of +$1.26 B.
- "Mean −$19.87 B (range −$40.69 to −$4.75 B)" comes from the quarterly run files, whose Q3–Q4 values are on a different, smaller scale; the series that produced the 71.5% detection has mean −$31.35 B (range −44.49 to −20.66). The paper mixes two scalars.
- The 13-date raw-chain comparison (92.3% vs 61.5%) fed its baseline arm that same scalar, and the 13 dates were stratified on the baseline outcome (8 detections, 5 misses); 61.5% is therefore not an unbiased baseline rate (the full-year rate is 69.4%). Complete 2024 chains exist in the database for all 252 dates, so the comparison can be re-run without the 72-date cache limit.
- The illustrative "−$32.9 B on 2024-03-15" matches no stored value for that date (stored: −$29.29 B).
- The put-row defect of item A does not affect Paper 1: its raw-chain data came from a separate store that holds calls and puts.

## What is being done

1. All inputs, deterministic labels and model answers of the re-analysis are stored (`backups.gex_llm_regime_*` in the research database, with parquet and raw JSONL copies), so every number in the correction and in the extension paper is reproducible from SQL.
2. The re-analysis uses obfuscated prompts throughout, one signed GEX convention, the complete chain, and reports the deterministic rule next to every model rate; it includes an obfuscated-vs-dated rerun of the 2024/2020 baselines to measure the effect of item B.
3. Formal correction notices are being drafted for the three venues; this page will link them when submitted.
