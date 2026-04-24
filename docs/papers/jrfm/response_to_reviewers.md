# Response to Reviewers — JRFM Submission jrfm-4256551

**Manuscript:** *Validating LLM Structural Reasoning: Detecting Persistent Market
Regimes Through Temporal Obfuscation*

**Authors:** Christopher Regan, Ying Xie (Kennesaw State University)

**Submitted:** 29 March 2026
**Reviews received:** 18 April 2026
**Response drafted:** in progress

---

## Overall summary for the editor

We thank the Editor and all three reviewers for their time. The review outcomes split as follows:

- **Reviewer 1** — The seven comments returned for Reviewer 1 concern a
  different manuscript on conformable derivatives in the Heston stochastic
  volatility framework. Our submission does not propose an option-pricing
  model, introduce conformable derivatives, or compare against Heston /
  Heston–He–Zhu models. We respectfully flag this apparent assignment error
  (see "Note to the editor" below) and are prepared to respond substantively
  once the correct review is available.

- **Reviewer 2** — Recommended acceptance with no revisions requested. We
  thank the reviewer for the positive evaluation.

- **Reviewer 3** — Provided substantive, actionable feedback with one "must
  be improved" mark (introduction background) and "can be improved" across
  design, methods, results, conclusions, and figures/tables. We address each
  of the eight points below, indicating the exact manuscript location of
  every change.

All changes in the revised manuscript are marked in red.

---

## Note to the editor (Reviewer 1 assignment)

Dear Editor,

Thank you for forwarding the reports for jrfm-4256551. On review, Reviewer 1's
comments do not appear to apply to our manuscript. The report asks about the
rigorous integration of conformable derivatives into the classical Heston
framework, comparison against the Heston–He and Zhu (HZ) model, jump-diffusion
and fractional alternatives, estimation and positivity of conformable
parameters, and computational challenges in an option-pricing algorithm.

Our submission, *Validating LLM Structural Reasoning: Detecting Persistent
Market Regimes Through Temporal Obfuscation*, is an empirical LLM-validation
study using temporal obfuscation on gamma-exposure sequences. It does not
propose an option-pricing model, does not introduce conformable derivatives,
and does not compare against Heston or HZ models. None of the seven questions
map to content in the manuscript, so a substantive point-by-point reply is
not feasible against these comments.

We respectfully request clarification: was this report forwarded from a
different submission in error, or could Reviewer 1 be asked to re-review the
correct manuscript (or a replacement reviewer be assigned)? We are happy to
respond substantively to any review of the actual paper.

Thank you for your time.

Sincerely,
Christopher Regan (on behalf of the authors)

---

## Reviewer 1 — Author's Notes to Reviewer box

> Please see my note to the editor — we believe this review concerns a
> different manuscript; requesting clarification before we can provide a
> substantive point-by-point response.

---

## Reviewer 2 — Author's Notes to Reviewer box

**Comments 1:** In this paper, the temporal obfuscation testing as a
methodology for validating LLM structural reasoning in domain-specific
applications is presented and applying this framework to options dealer
gamma exposure (GEX) patterns, the detection is validated by using 2,221
evaluations (1,412 real windows plus 809 synthetic controls) spanning
2020–2025. These studies have important theoretical value. I recommend it
to be published in JRFM.

**Response 1:** We thank the reviewer for their careful reading of the
manuscript and for the positive recommendation. We are grateful for the
confirmation that the temporal obfuscation framework and the scale of the
validation (2,221 evaluations across the 2020–2025 period) contribute
meaningful theoretical value to the field. No changes were requested in
this review, and none have been made in response.

---

## Reviewer 3 — Point-by-point response

Reviewer 3 provided eight substantive comments organised into the following
groups. We address each in turn, indicating the exact manuscript location of
every change (page / section / paragraph) in the revised manuscript.

### R3.1 — Introduction (must be improved)

> The introduction must be shortened and made more focused. It currently
> contains overly long and philosophical paragraphs. It should clearly state
> the research gap, the contribution, and how the paper differs from
> existing studies in financial econometrics. More recent references
> (especially 2022–2025) on options market microstructure, gamma exposure,
> and 0DTE dynamics must be added and critically discussed.

**Response:** *[to draft]*

**Change location:** *§1 Introduction, pp. TBD. Revised text shown in red.*

**Status:** todo

---

### R3.2 — Paper positioning

> The positioning of the paper must be clarified. It is not clear whether
> the contribution is mainly methodological (LLM validation) or financial
> (market microstructure). This needs to be explicitly stated and
> consistently reflected throughout the paper.

**Response:** We agree and have stated the positioning explicitly in
two places to ensure the stance is consistent throughout the paper.

The primary contribution is **methodological**: temporal obfuscation
testing (with the WHO→WHOM→WHAT causal framework and multi-scale
validation protocol) as a generalizable procedure for validating LLM
structural reasoning. Options dealer gamma-exposure regime detection is
the **empirical demonstration domain** — selected because it combines
theoretically grounded mechanical constraints, a large quantitative
testbed, and the sharp pre-vs-post-0DTE temporal contrast — not because
the paper is proposing novel claims about options microstructure. The
financial-market findings (69.1pp detection gap, 0% FP rate on synthetic
controls, 2021–2024 0DTE-tracking regime evolution) are downstream
evidence that the methodology discriminates correctly, not the primary
contribution.

**Change location:**

- New §1.4 "Positioning" subsection (label
  `sec:introduction:positioning`) between §1 Contributions and §1 Paper
  Organization. Two paragraphs: first states the methodological primacy
  and the rationale for GEX as the demonstration domain; second explains
  that the financial findings are downstream evidence and provides a
  reader-routing note for methodology-first vs finance-first readers.
- §6 Conclusion opening rewritten to echo the same stance before listing
  the four contributions, so that the stance frames the closing summary.

**Status:** done

---

### R3.3 — Benchmark comparison & causal claims

> The research design must be strengthened. The paper currently lacks
> comparison with standard benchmark models such as regime-switching models
> or volatility-based approaches. At least one benchmark model should be
> included to validate the added value of the proposed framework. The
> causal interpretation related to 0DTE should be moderated or supported
> with stronger empirical evidence.

**Response:** *[to draft — plan: add a Markov-switching regression (HMM /
statsmodels `MarkovRegression`) benchmark on the daily GEX series. Compare
HMM regime labels against LLM-detected regime labels per window for 2020 and
2024. Also moderate 0DTE causal language throughout.]*

**Change location:** *§3 Methodology (benchmark subsection, new) + §4
Results (HMM comparison table, new) + §5 Discussion (moderated causal
language).*

**Status:** todo — requires new analysis (HMM fit + label agreement table)

---

### R3.4 — Methodology transparency (prompts, thresholds, temperature)

> The methodology section needs more transparency. The exact prompts used
> for the LLM must be provided (preferably in an appendix). The choice of
> thresholds (70% persistence, $5B magnitude, ≤5 flips) must be justified
> or tested through sensitivity analysis. The impact of model parameters
> (e.g., temperature = 1.0) on reproducibility must be explained.

**Response:** We have addressed this comment in three parts:

**(a) Prompts.** The complete regime-detection prompt is now reproduced
verbatim in a new Appendix A, together with the OpenAI Batch API
configuration (o4-mini, temperature = 1.0, max completion tokens =
16,384, JSON-object response format) and the output JSON schema used for
parsing. The appendix is transcribed directly from
`src/llm/mechanics_prompt_builder.py::build_regime_prompt()` in the
publicly released source code, so the reader has full prompt visibility
from the manuscript alone.

**(c) Temperature and reproducibility.** Appendix A also contains a
Reproducibility note explaining that OpenAI reasoning models
(o1, o3, o4-mini) run at a fixed temperature of 1 and do not accept a
user-supplied seed parameter, so bit-identical reproduction of a single
response is not guaranteed. Reproducibility at the distributional level
is established through the N = 2,221 evaluation sample and the
mechanical numerical thresholds embedded in the prompt itself, which
anchor the model on concrete criteria rather than free-form judgment.

**(b) Threshold sensitivity — DONE.** A post-hoc sensitivity sweep has
been added as new §4.6 "Threshold Sensitivity" with Figure 7
(`fig09_threshold_sensitivity.png`). The sweep spans a 5×3×3 grid
(persistence ∈ {60, 65, 70, 75, 80}%, magnitude ∈ {$3B, $5B, $7B},
flips ≤ {3, 5, 7}; 45 configurations in total) applied to the 223
Phase 3 (2024) and 220 Phase 4 (2020) per-window records already on
disk — no new LLM queries required.

Key findings reported in §4.6:

- The 2024-vs-2020 detection gap ranges from 34.1 to 85.2 pp across
  the 45 configurations (median 63.2 pp).
- The gap exceeds 50 pp in 40 of 45 configurations.
- The five sub-50 pp cells all occur at the most permissive magnitude
  threshold ($3B) combined with the strictest flip limit (≤3) —
  deliberately degenerate settings.
- The persistence threshold has essentially no binding effect in this
  data because 2024 regime windows saturate ≥60% persistence and 2020
  windows rarely clear any persistence bar — so choosing 60%, 70%, or
  80% produces identical detection rates.
- Magnitude is the binding threshold; flip tolerance is the secondary
  lever.

The analysis is produced deterministically by the new
`scripts/validation/paper2/jrfm_revision/threshold_sensitivity.py`
(YAML summary at
`reports/validation/paper2_regime_windows/jrfm_revision_threshold_sensitivity.yaml`,
heatmap at `docs/papers/paper2/figures/output/fig09_threshold_sensitivity.png`
with a local copy at `docs/papers/jrfm/figures/fig09_threshold_sensitivity.png`
for LaTeX compilation).

**Change location:**

- New Appendix A on pp. 20–25 (parts (a) and (c) above).
- Main text §3 Methodology: brief cross-reference added to Appendix A
  where prompts were previously described in prose.
- New §4.6 "Threshold Sensitivity" subsection with Figure 7 (part (b)).

**Status:** done

---

### R3.5 — Statistical rigour in results

> The results section must include statistical validation. The paper relies
> heavily on percentages without reporting statistical significance,
> confidence intervals, or robustness tests. These must be added. Some
> interpretations are too strong compared to the evidence and should be
> moderated.

**Response:** We agree. The revision addresses this comment in four
parts; part (a) is complete, (b/c/d) are in progress.

**(a) Confidence intervals — DONE.** Every detection rate reported in
§4 Results now carries a 95% confidence interval. Methodology:

- For Phases 1--4 and all Phase 2 negative controls, per-window records
  are available, so we report a 10,000-replicate percentile bootstrap
  over windows (deterministic seed).
- For Phase 5 per-year rates (2020--2025), where only aggregate counts
  survive in the published pipeline, we report 95% Wilson score
  intervals for binomial proportions, which have equivalent coverage
  properties and are the standard recommendation in
  \citet{brown2001interval}.

The methodology is spelled out in a new "Statistical conventions"
paragraph at the head of §4.1, and all CIs are produced deterministically
by the new reprocessing script
`scripts/validation/paper2/jrfm_revision/bootstrap_detection_ci.py`
shipped with the code release.

Key numerical landings (point-estimate [95% CI] N):

| Phase | Rate (95% CI) |
| --- | --- |
| Phase 1 baseline 2024 Q1 | 71.2% [57.7, 82.7]% (37/52) |
| Phase 3 full 2024 | 81.2% [75.8, 86.1]% (181/223) |
| Phase 4 full 2020 | 12.1% [8.1, 16.6]% (27/223) |
| Phase 2b transitional 2020 | 0.0% [0.0, 1.7]% (0/223) |
| Phase 5 2020 | 12.2% [8.5, 17.3]% (26/213) |
| Phase 5 2024 | 100% [98.4, 100.0]% (241/241) |
| Phase 5 2025 | 100% [98.5, 100.0]% (245/245) |

Critically, the 2020 upper CI bound (17.3%) does not overlap the 2024
lower CI bound (98.4%), which directly supports the 69.1pp separation
claim with bounded evidence rather than point estimates alone.

**(b) Expanded χ² / Fisher reporting — DONE.** Every headline
contingency now reports the full suite of statistics rather than just φ
and "p < 0.0001". Specifically:

- §4.4 Phase 4 (2020 vs 2024, 223 each): Pearson's χ² = 213.67 (df=1,
  p = 2.2×10⁻⁴⁸), Yates-corrected χ² = 210.90 (p = 8.7×10⁻⁴⁸),
  Fisher's exact two-sided p = 1.8×10⁻⁵² with odds ratio 31.3,
  φ = 0.69 (refined from the previously rounded 0.672), and a risk
  difference of 69.1pp with a 95% Wald CI of [62.4, 75.7]pp.
- §4.5 Phase 5 (2023→2024 transition, 228 vs 241): χ² = 314.4
  (p = 2.4×10⁻⁷⁰), Fisher's exact p = 9.9×10⁻⁸⁷ (OR diverges because
  all 241 2024 windows are detected), φ = 0.82 (refined from 0.783).
- Abstract and Introduction updated to report the 2020-vs-2024
  comparison with both CI brackets on each rate and Fisher's exact p
  (the strongest and most defensible statistic here given the zero
  cell), instead of a single "p < 0.0001".

**(c/d)** — Threshold / window sensitivity (R3.4b) and softened claim
language (R3.5d) still to be completed in subsequent commits.

**Change location:**

- `04_Results.tex` §4.1 new "Statistical conventions" paragraph
- `04_Results.tex` Phase 1/3 inline rates in text
- `04_Results.tex` Table 2 (negative controls) — CI column added
- `04_Results.tex` Table 3 (Phase 4 comparison) — CIs on both rates
- `04_Results.tex` Table 5 (Phase 5) — new CI column
- `references.bib` — added `brown2001interval` for Wilson score cite
- `scripts/validation/paper2/jrfm_revision/bootstrap_detection_ci.py` — new reprocessing script

**Status:** (a) done; (b/c/d) todo

---

### R3.6 — Discussion: finance connections

> The discussion must be better connected to finance. The implications for
> risk management, market efficiency, and practitioners should be explicitly
> developed. The current discussion is too general and sometimes
> theoretical.

**Response:** We agree that the original discussion was too general on
the practitioner side. The previous §5.6 "Practitioner Implications"
subsection has been renamed "Practical Implications" and restructured
into three explicit subsubsections exactly matching the three axes the
reviewer identified:

**(a) Risk management.** Three concrete applications developed:
intraday volatility budgeting (regime as a leading indicator for
volatility-of-volatility exposure sizing), option-book hedging under
OpEx concentration (persistent-positive regimes amplify the OpEx
pinning dynamic), and risk-scenario design (2020 fragmented vs 2024
persistent-negative as natural conditioning variables for stress-test
calibration).

**(b) Market efficiency.** A new positive account is offered: the
detection-alpha orthogonality is consistent with a weakly efficient
market in which structural constraints are reliably identifiable but
already priced. This reconciles two claims often treated as
contradictory — that dealer-gamma positioning measurably influences
short-horizon price dynamics, and that systematic strategies exploiting
it deteriorate as attention accumulates — and explains why
microstructure-aware research can be genuinely informative for risk
without being informative for alpha.

**(c) Practitioners: pipeline design and model deployment.** Two
design implications developed from the experimental results: (i) the
30.8pp advantage of raw strike-level data over pre-aggregated GEX
challenges the default of parametric aggregation in quantitative
pipelines, with generalisations to credit risk, fixed-income
surveillance, and equity factor research explicitly noted; (ii) the
2022–2024 0DTE regime shift implies that static microstructure models
calibrated to pre-2022 data need recalibration rather than drift
correction.

**Change location:** §5.6 "Practical Implications" (renamed from
"Practitioner Implications"), with new `sec:discussion:practical` label
and three new `\subsubsection` headings corresponding to the
reviewer's three axes. The subsection expanded from one dense
paragraph (4 insights) to three structured subsubsections (~1 page).

**Status:** done

---

### R3.7 — Limitations expansion

> The limitations section must be expanded. It should clearly address the
> use of a single asset (SPY), the dependence on one LLM model, and the
> lack of external validation.

**Response:** We thank the reviewer for flagging these specific omissions.
We have renamed §5.7 to "Limitations and Future Work" and expanded it
from six limitations to seven, with each item now explicitly tied to a
concrete follow-up study. The three items the reviewer named are now
addressed as follows:

**(a) Single-asset scope.** The first limitation item (now titled
"Single-asset scope") explicitly acknowledges that all results concern
SPY, lists QQQ, IWM, individual equities, and non-equity underliers as
relevant but untested targets, and identifies cross-asset replication as
the single highest-priority item for future work. A pre-registered
protocol applying the same framework to at least QQQ and one individual
equity (e.g., NVDA or AAPL) is proposed.

**(b) Single-LLM dependence.** A dedicated second item ("Single-LLM
dependence") acknowledges that all 2,221 evaluations used one reasoning
model (o4-mini), so the reported detection rates are conditional on
that model's priors. We propose a model-swap protocol covering Anthropic
Claude, OpenAI o3, Google Gemini, and open-source reasoning models
using identical prompts and obfuscated sequences, with cross-model
agreement analysis as the diagnostic.

**(c) Lack of independent external validation.** A new third item
("Lack of independent external validation") acknowledges that per-window
ground-truth metrics are computed from the same Alpha Vantage feed used
to construct the windows, and proposes cross-validation against CBOE
DataShop / OPRA / commercial vendors (SpotGamma, MenthorQ) and against
related microstructure observables (realised volatility,
implied-realised spread, opening auction imbalance).

**Change location:** §5.7 Limitations and Future Work (p.\ 17 in the
revised PDF). The subsection was relabelled from "Limitations" to
"Limitations and Future Work" and expanded from 6 to 7 items. Each item
now includes an explicit future-work sentence indicating how it could
be addressed.

**Status:** done

---

### R3.8 — Figures and tables

> Figures and tables must be improved. Some are too dense and difficult to
> read. Labels and captions should be clearer and more explanatory.

**Response:** *[to draft — pass over all figures:
  (a) Captions rewritten to be self-contained (explain what the reader
      should conclude, not just what is shown).
  (b) Identify any dense figures (fig07 confidence discrimination,
      fig08 detection progression) and either split, enlarge, or simplify.
  (c) Ensure table headers use consistent units; add row totals where
      helpful.]*

**Change location:** *All figure captions throughout the manuscript; table
headers in §4.*

**Status:** todo — writing + possible figure re-rendering

---

### R3.9 — English language quality

> The clarity of the manuscript needs improvement. Many sentences are too
> long and complex, which affects readability. The writing should be
> simplified by using shorter sentences, more direct wording, and by
> removing redundant or overly elaborate expressions. Careful language
> editing is recommended to improve clarity and flow.

**Response:** *[to draft — full editing pass focusing on:
  (a) Breaking up sentences longer than ~30 words.
  (b) Removing redundant transitions ("In this section we will...",
      "It should be noted that...", etc.).
  (c) Active voice where appropriate.
  (d) Consistency of technical terms throughout.]*

**Change location:** *Throughout.*

**Status:** todo — final pass after content changes

---

## Work checklist (planning-only; live state below)

- [ ] R3.1 — Introduction rewrite + 2022–2025 references
- [ ] R3.2 — Methodological-contribution stance stated consistently
- [ ] R3.3a — HMM benchmark fit + agreement table
- [ ] R3.3b — Moderate 0DTE causal language
- [ ] R3.4a — Prompts appendix
- [ ] R3.4b — Threshold sensitivity sweep
- [ ] R3.4c — Temperature / reproducibility note
- [ ] R3.5a — Bootstrap CIs on detection rates
- [ ] R3.5b — χ² / Fisher reporting expanded
- [ ] R3.5c — Robustness to window length
- [ ] R3.5d — Moderate strong-claim language
- [ ] R3.6 — Practical Implications subsection
- [ ] R3.7 — Expanded Limitations
- [ ] R3.8 — Figure / table caption pass
- [ ] R3.9 — English editing pass (last)
- [ ] Final: regenerate `Regan_Xie_JRFM.pdf`, update submission zip
