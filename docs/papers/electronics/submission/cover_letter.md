# Cover letter (draft, 2026-11-07; revised 2026-11-23 for the two-paper split; 2026-11-24 for the statement of what the article supersedes)

<!-- Draft for the MDPI submission form. Items marked TODO(authors) need Chris and Dr. Xie before submission.
     Numbers are those of the manuscript after the split and the cut of 2026-11-24 (abstract, Sections 1.1, 1.3, 3.3, 4.1-4.4); the open-weights
     results moved to the companion manuscript and are not quoted here. -->

Dear Guest Editors of the *Electronics* Special Issue "Timely AI Advancements and Interdisciplinary Synergies for
Intelligent Modeling",

We submit the article "Persistent Dealer-Gamma Regimes Under Temporal Obfuscation: A Re-Run on Inputs with Both Option
Legs and a Rule-Following Test of a Current LLM" by Christopher Regan and Ying Xie (Kennesaw State University) for consideration in the Special
Issue held jointly with EAAAI 2026 and AIAI 2026, following the invitation to extend our AIAI 2026 paper.

**Relation to earlier publications.** The article extends "Validating LLM Structural Reasoning: Detecting Persistent
Market Regimes Through Temporal Obfuscation" (AIAI 2026, IFIP AICT, Springer, pp. 127-140,
doi:10.1007/978-3-032-30801-6_10). That paper and our IEEE BigData 2025 workshop paper are combined in a separate journal
article, "Temporal Obfuscation Testing for LLM Structural Reasoning: From Single-Day Dealer Constraints to Persistent
Market Regimes" (*JRFM* 2026, 19(6), 382, doi:10.3390/jrfm19060382). All three are cited (Section 1.2). The present
article reuses only the regime criteria and the prompt of the conference paper, restated in Section 3.1 and
Section S6 of the Supplementary Materials. Its experiments, results, figures and tables are new. Relative to all three publications it adds:

1. the provenance and definition of the daily input series, with six series assembled from recovered, archived and
   rebuilt data;
2. a second model, gpt-6-luna, bridged to the retired o4-mini on the exact published inputs (agreement 99.6%,
   Cohen's kappa 0.993);
3. the years 2008-2019 and the post-publication year 2026, and, in the Supplementary Materials, the exchange-traded
   funds QQQ and IWM next to SPY and an intraday check;
4. inference that accounts for overlapping windows (quarter-block bootstrap, non-overlapping subsamples);
5. a rerun of the 2024 and 2020 baselines with and without calendar dates;
6. a disclosed per-symbol scaling for QQQ and IWM (Supplementary Materials).

The language-model arms test whether the model applies criteria that the prompt states; because the rule is in the
prompt and is the reference label, they cannot separate recall from reasoning, and the article says so.

**Companion manuscript.** A second manuscript, in preparation, repeats seven of the arms with open-weights models
at fixed revisions on local hardware (the question of whether the bridge and the main arms stay reproducible after a
hosted model is retired). It is cited in the article as a companion manuscript in preparation. The two manuscripts share
one data deposit, which holds the answers of both. Nothing is reported as new in both: the article owns the lineage
finding, the re-run and the bridge to gpt-6-luna; the companion manuscript owns every open-weights result.

**Data statement.** While preparing the extension we found that the daily inputs of the published 2024-2025 windows
carried only the call leg of the options chain: an upstream database load had dropped the put rows. The article states
this in Sections 3.3 and 4.1 and reports the re-run on the complete data. On the published inputs the deterministic rule
detects 501 of 501 windows of 2024-2025 (100.0%); on the complete series it detects 60 of 502 (12.0%), and gpt-6-luna
63 of 502 (12.5%). The conference paper and the *JRFM* article, also published by MDPI, report the earlier rates.
The article therefore says plainly, in Section 1.1 ("Relation to the Published Results") and in one sentence of the
abstract, which published results it supersedes: the 100% detection rates for 2024 and 2025 and the rise after 2023
(AIAI Table 4, JRFM Table 5), the magnitude-growth statement, and the 2021-2023 rates, because 39 earlier days before
2023-09-29 are also call-only (they lie in 332 of 911 published windows; replacing them changes 46 verdicts of the
rule). It also says that the 2024-versus-2020 baseline contrast of the earlier papers was run with calendar dates
visible. **No correction has yet been filed with the publishers.** We will file one, and until then the article and
the corrections page of the repository (`docs/papers/CORRECTIONS.md`) are the public record. The article is a
research article with a data statement, not a correction notice.
<!-- TODO(authors): decide whether to say here when and to whom the formal notices (JRFM, Springer) will go. -->

**Data, code and the use of AI tools.** Code, condensed per-window tables and every result file are available at
https://github.com/iAmGiG/gex-llm-patterns. The full tables (inputs, labels and model answers) will be deposited at
Zenodo. <!-- TODO(authors): DOI once the record is created (issue #274); the vendor's terms allow the deposit (D-31). --> The
options data come from Alpha Vantage under a premium subscription whose terms permit this use; the raw option chains
are not part of the deposit because of their size. gpt-6-luna is the object of the study. As stated in the
Acknowledgments, the authors used Claude Code to write the analysis code and to draft and revise the text, and they take
full responsibility for the content.

The manuscript has not been published and is not under consideration elsewhere. All authors have approved the
submission and declare no conflict of interest. The study received no external funding.
<!-- TODO(authors): confirm, and decide whether to ask here for the APC discount the invitation offers to invited
     authors without funding. -->

Sincerely,

Christopher Regan (corresponding author), Kennesaw State University, cregan1@students.kennesaw.edu
Ying Xie, Kennesaw State University
