# Cover letter (draft, 2026-11-07)

<!-- Draft for the MDPI submission form. Items marked TODO(authors) need Chris and Dr. Xie before submission.
     Numbers are those of the manuscript as of commit 6a3ff03 (abstract, Sections 1.2, 3.3, 4.1-4.4), item 7 from
     Section 4.12 (2026-11-07). -->

Dear Guest Editors of the *Electronics* Special Issue "Timely AI Advancements and Interdisciplinary Synergies for
Intelligent Modeling",

We submit the article "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on Complete Inputs with a
Controlled LLM Re-Test" by Christopher Regan and Ying Xie (Kennesaw State University) for consideration in the Special
Issue held jointly with EAAAI 2026 and AIAI 2026, following the invitation to extend our AIAI 2026 paper.

**Relation to earlier publications.** The article extends "Validating LLM Structural Reasoning: Detecting Persistent
Market Regimes Through Temporal Obfuscation" (AIAI 2026, IFIP AICT, Springer, pp. 127-140,
doi:10.1007/978-3-032-30801-6_10). That paper and our IEEE BigData 2025 workshop paper are combined in a separate journal
article, "Temporal Obfuscation Testing for LLM Structural Reasoning: From Single-Day Dealer Constraints to Persistent
Market Regimes" (*JRFM* 2026, 19(6), 382, doi:10.3390/jrfm19060382). All three are cited (Section 1.2). The present
article reuses only the regime criteria and the prompt of the conference paper, restated in Section 3.1 and
Appendix A. Its experiments, results, figures and tables are new. Relative to all three publications it adds:

1. the provenance and definition of the daily input series, with six series assembled from recovered, archived and
   rebuilt data;
2. a second model, gpt-6-luna, bridged to the retired o4-mini on the exact published inputs (agreement 99.6%,
   Cohen's kappa 0.993);
3. the years 2008-2019, three exchange-traded funds (SPY, QQQ, IWM), the post-publication year 2026 and an intraday
   check;
4. inference that accounts for overlapping windows (quarter-block bootstrap, non-overlapping subsamples);
5. a rerun of the 2024 and 2020 baselines with and without calendar dates;
6. a disclosed per-symbol scaling for QQQ and IWM; and
7. three models with open weights from three developers, run locally at fixed revisions on seven arms, so that the
   bridge and the main arms stay reproducible after API models are retired and are not tied to one developer:
   gpt-oss-20b agrees with gpt-6-luna on 99.4% of the complete series; Qwen3-8B agrees with the rule on 98.7% of the
   windows it answers, and its 2024-2025 rate is bounded at 14.5-35.1%; Llama 3.1 8B, without a reasoning phase,
   detects almost every window (Section 4.12).

**Data statement.** While preparing the extension we found that the daily inputs of the published 2024-2025 windows
carried only the call leg of the options chain: an upstream database load had dropped the put rows. The article states
this in Sections 3.3 and 4.1 and reports the re-run on the complete data. On the published inputs the deterministic rule
detects 501 of 501 windows of 2024-2025 (100.0%); on the complete series it detects 60 of 502 (12.0%), and gpt-6-luna
63 of 502 (12.5%). The conference paper and the *JRFM* article, also published by MDPI, report the earlier rates. The
evidence is public in the project repository (`docs/papers/CORRECTIONS.md`).
<!-- TODO(authors): add one sentence on the earlier articles once decided, e.g. whether a correction has been or will
     be requested from JRFM and from Springer. -->

**Data, code and the use of AI tools.** Code, condensed per-window tables and every result file are available at
https://github.com/iAmGiG/gex-llm-patterns. The full tables (inputs, labels and model answers) will be deposited at
Zenodo. <!-- TODO(authors): DOI once the record is created (issue #274); the vendor's terms allow the deposit (D-31). --> The
options data come from Alpha Vantage under a premium subscription whose terms permit this use; the raw option chains
are not part of the deposit because of their size. gpt-6-luna and the three open-weights models are the objects of the study. As stated in the
Acknowledgments, the authors used Claude Code to write the analysis code and to draft and revise the text, and they take
full responsibility for the content.

The manuscript has not been published and is not under consideration elsewhere. All authors have approved the
submission and declare no conflict of interest. The study received no external funding.
<!-- TODO(authors): confirm, and decide whether to ask here for the APC discount the invitation offers to invited
     authors without funding. -->

Sincerely,

Christopher Regan (corresponding author), Kennesaw State University, cregan1@students.kennesaw.edu
Ying Xie, Kennesaw State University
