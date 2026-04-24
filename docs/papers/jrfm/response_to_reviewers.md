# Response to Reviewers — JRFM Submission jrfm-4256551

**Manuscript:** *Validating LLM Structural Reasoning: Detecting Persistent Market
Regimes Through Temporal Obfuscation*

**Authors:** Christopher Regan, Ying Xie (Kennesaw State University)

**Submitted:** 29 March 2026
**Reviews received:** 18 April 2026
**Response drafted:** 24 April 2026 (point-by-point complete; ready for portal upload)

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

**Response:** We rewrote §1 Introduction to address each element the
reviewer asked for:

**(i) Shortened and less philosophical.** The original paragraph-1
opener ("The decisive question confronting any deployment of large
language models ...") has been removed. The new §1 opens with a
two-sentence, direct statement of the validation problem and why it
is first-order in finance specifically.

**(ii) Explicit research gap.** A new paragraph titled "Research gap"
(in bold) follows the opener. It names what prior literature has done
independently — dealer-gamma microstructure
\citep{ni2005stock,garleanu2009demand,anderegg2022impact,dim2023odtes,dim2025zero},
0DTE growth and volatility impact
\citep{cboe2024zero,fishman2023gamma,cboe2025spx0dte}, and LLM-reasoning
probing in non-financial domains
\citep{wei2022chain,kojima2022large,mccoy2023embers} — and states
precisely which combination has not been attempted: an LLM
structural-reasoning validation method that (a) controls for
training-data memorisation of specific events and dates, (b) is tested
at a scale comparable to the target domain, and (c) discriminates
genuine structural detection from reproduction of a volatility-regime
classifier. The Markov-switching benchmark added per R3.3a
(§\ref{sec:regime:benchmark}) is then introduced as the direct test of
element (c).

**(iii) Why 0DTE matters here.** A new "Why 0DTE matters here"
paragraph replaces the previous "practical urgency" framing. It
explains that 0DTE growth is a natural setting for an obfuscation study
because it created an observable structural shift \emph{within the
training horizon of modern LLMs} — so if the LLM reports 2024 as
persistent-regime and 2020 as fragmented-regime after dates/tickers are
stripped, it cannot be recalling that 2024 contained the word "0DTE".

**(iv) 2022–2025 references added and critically discussed.** The
key addition is \citet{dim2023odtes} ("0DTEs: Trading, Gamma Risk and
Volatility Propagation", SSRN 4692190), which provides the first
systematic empirical study of 0DTE dealer inventory and is now cited in
§1 and critically discussed in §2.2 alongside \citet{dim2025zero}. The
new discussion notes that Dim, Eraker & Vilkov (2023) establishes
dealer-hedging rather than information flow as the dominant channel
through which 0DTE trading affects the underlying, and that this
characterisation is consistent with our multi-year empirical panel in
§4 (detection of persistent dealer-gamma regimes growing from 3.7% in
2021 to 100% in 2024–2025). We retain the existing 2022–2025 refs
already cited (Anderegg et al.\ 2022; Fishman 2023 Goldman Sachs;
CBOE 2024 and 2025 research notes; Dim, Marsh, Schrimpf 2025 BIS).

**(v) Differentiation from financial-econometrics literature.** §2.5
"Regime Detection in Financial Markets" and §2.7 "Research Gap"
already state the differentiation from Hamilton (1989),
Ang & Bekaert (2002), and Nystrup et al. (2018) regime-detection
traditions. The new §1 Research Gap paragraph restates this in terms
the LLM-validation reader will recognise: prior regime detection
detects regimes through \emph{statistical properties of observable
outcomes} (volatility clustering, return distributions); our
contribution detects regimes through \emph{dealer positioning
constraints} (a microstructure-grounded signal with explicit causal
interpretation) \emph{while holding the LLM accountable for its own
reasoning} via obfuscation.

**Change location:**

- `01_Introduction.tex`: paragraphs 1–4 of §1 fully rewritten; §1.1
  Research Questions, §1.2 Contributions, §1.3 Positioning, §1.5 Paper
  Organization retained unchanged from the prior revision commits.
- `02_Related_Work.tex`: §2.2 "Zero-Days-to-Expiration Options"
  expanded to include `dim2023odtes` critical discussion alongside the
  existing `dim2025zero`.
- `references.bib`: new entry `dim2023odtes` (Dim, Eraker & Vilkov,
  SSRN 4692190, November 2023) added in the 0DTE section.

**Status:** done

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

- New §1.3 "Positioning" subsection (label
  `sec:introduction:positioning`) between §1 Contributions and §1 Paper
  Organization. Two paragraphs: first states the methodological primacy
  and the rationale for GEX as the demonstration domain; second explains
  that the financial findings are downstream evidence and provides a
  reader-routing note for methodology-first vs finance-first readers.
- §7 Conclusion opening rewritten to echo the same stance before listing
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

**Response (part a — benchmark): DONE.** We have added a two-state
Markov-switching regression benchmark (the textbook regime-switching
model, `statsmodels.tsa.regime_switching.MarkovRegression`) on the
daily SPY return series for 2020 and 2024, and additionally on the
2024 net-GEX daily panel where the cached series is available. Details
in new §3.8 "Markov-Switching Benchmark" and new §5.6 "Comparison
with Markov-Switching Benchmark" (with Table 6 + Figure 8,
`fig10_hmm_agreement.png`).

Three findings emerge:

| Year | HMM input | N | LLM rate | HMM rate | Agree | Cohen's κ |
| --- | --- | --- | --- | --- | --- | --- |
| 2020 | SPY returns | 201 | 8.5% | 80.1% | 28.4% | 0.045 |
| 2024 | SPY returns | 222 | 81.1% | 87.4% | 68.5% | −0.178 |
| 2024 | Net GEX | 221 | 81.0% | 65.2% | 84.2% | 0.610 |

1. A returns-based HMM (canonical volatility-regime benchmark) detects
   a **different signal** from the LLM: κ is near zero for 2020 and
   negative for 2024, so the two classifiers disagree more than chance
   — the LLM is not reducible to a variance regime detector.
2. When the HMM is fitted directly on the daily net-GEX series (2024),
   agreement with the LLM jumps to **κ = 0.61** (substantial) — the
   two converge on the same windows 84.2% of the time.
3. Taken together this is evidence that the LLM's regime concept is
   anchored in dealer-gamma structure specifically (where a mechanical
   HMM on the same series agrees with it) rather than in any generic
   variance / volatility regime (where the classical benchmark
   disagrees).

The benchmark fits and per-window analysis are produced deterministically
by `scripts/validation/paper2/jrfm_revision/hmm_benchmark.py` with
outputs at
`reports/validation/paper2_regime_windows/jrfm_revision_hmm_benchmark.yaml`
and `docs/papers/paper2/figures/output/fig10_hmm_agreement.png`.

**Response (part b — causal language):** Moderated in the B4 commit
(R3.5d) above. §7 Conclusion contribution 3 now describes the 0DTE
correspondence as "coincides with" rather than "drove"; §6.3 softens
the "tipping-point dynamic strengthens the structural interpretation"
phrasing to "is consistent with, rather than proof of"; §5.7
Limitations explicitly names interest-rate regime, passive-flow
concentration, and market-maker inventory as alternative
contemporaneous factors that cannot be excluded observationally.
Deeper §6.3 revision is still scheduled in C2 below.

**Change location:**

- §3.8 Markov-Switching Benchmark (new subsection)
- §5.6 Comparison with Markov-Switching Benchmark (new subsection,
  Table 6, Figure 8)
- `scripts/validation/paper2/jrfm_revision/hmm_benchmark.py` (new)
- `docs/papers/paper2/figures/output/fig10_hmm_agreement.png` (new)
  with local copy in `docs/papers/jrfm/figures/`
- §7 Conclusion + §6.3 + §6.7 moderations as described under R3.5d

**Status:** (a) done; (b) done (moderations in §6.3 applied in B4 plus a
fuller §6.3 rewrite in the C2 commit). §6.3 now explicitly (i) frames
the 0DTE correspondence as temporal coincidence supported by a
plausible mechanical channel rather than a demonstrated causal
relationship, (ii) enumerates four concurrent confounders (interest
rates, short-vol flow, passive/index AUM, market-maker concentration),
(iii) proposes three candidate causal-identification designs (0DTE
suspension natural experiment, counterfactual non-SPY launch, IV
design), and (iv) closes with an explicit acknowledgement that
"less easily reconciled" is not "ruled out" and that disentangling the
channels is beyond the scope of an LLM-validation paper.

---

### R3.4 — Methodology transparency (prompts, thresholds, temperature)

> The methodology section needs more transparency. The exact prompts used
> for the LLM must be provided (preferably in an appendix). The choice of
> thresholds (70% persistence, $5B magnitude, ≤5 flips) must be justified
> or tested through sensitivity analysis. The impact of model parameters
> (e.g., temperature = 1.0) on reproducibility must be explained.

**Response:** We have addressed this comment in three parts:

**(a) Prompts.** The complete regime-detection prompt is now reproduced
verbatim in a new Appendix A, together with the actual OpenAI Batch API
configuration we used (model `o4-mini`; temperature defaults to 1
because reasoning models reject user-supplied temperature overrides;
`max_completion_tokens` not explicitly set, so the OpenAI API default
applies; JSON structure requested in the prompt rather than enforced
via `response_format`) and the output JSON schema used for parsing.
The appendix is transcribed directly from
`src/llm/mechanics_prompt_builder.py::build_regime_prompt()` in the
publicly released source code, so the reader has full prompt visibility
from the manuscript alone.

**(c) Temperature and reproducibility.** Appendix A contains a
Reproducibility note explaining that OpenAI reasoning models
(`o1`, `o3`, `o4-mini`, and GPT-5 reasoning variants) reject
user-supplied `temperature` / `top_p` values and run at the default
temperature of 1. The seed parameter is supported by `o4-mini`
(OpenAI documents it as best-effort determinism that can shift when
the server `system_fingerprint` changes), but we did not set a seed
in this study. Bit-identical reproduction of any single response is
therefore not guaranteed. Reproducibility at the distributional level
is established through the N = 2,221 evaluation sample and the
mechanical numerical thresholds embedded in the prompt itself, which
anchor the model on concrete criteria rather than free-form judgment.

**(b) Threshold sensitivity — DONE.** A post-hoc sensitivity sweep has
been added as new §5.5 "Threshold Sensitivity" with Figure 7
(`fig09_threshold_sensitivity.png`). The sweep spans a 5×3×3 grid
(persistence ∈ {60, 65, 70, 75, 80}%, magnitude ∈ {$3B, $5B, $7B},
flips ≤ {3, 5, 7}; 45 configurations in total) applied to the 223
Phase 3 (2024) and 220 Phase 4 (2020) per-window records already on
disk — no new LLM queries required.

Key findings reported in §5.5:

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

- New Appendix A on pp. 24–29 (parts (a) and (c) above).
- Main text §3 Methodology: brief cross-reference added to Appendix A
  where prompts were previously described in prose.
- New §5.5 "Threshold Sensitivity" subsection with Figure 7 (part (b)).

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

- §5.3 Phase 4 (2020 vs 2024, 223 each): Pearson's χ² = 213.67 (df=1,
  p = 2.2×10⁻⁴⁸), Yates-corrected χ² = 210.90 (p = 8.7×10⁻⁴⁸),
  Fisher's exact two-sided p = 1.8×10⁻⁵² with odds ratio 31.3,
  φ = 0.69 (refined from the previously rounded 0.672), and a risk
  difference of 69.1pp with a 95% Wald CI of [62.4, 75.7]pp.
- §5.4 Phase 5 (2023→2024 transition, 228 vs 241): χ² = 314.4
  (p = 2.4×10⁻⁷⁰), Fisher's exact p = 9.9×10⁻⁸⁷ (OR diverges because
  all 241 2024 windows are detected), φ = 0.82 (refined from 0.783).
- Abstract and Introduction updated to report the 2020-vs-2024
  comparison with both CI brackets on each rate and Fisher's exact p
  (the strongest and most defensible statistic here given the zero
  cell), instead of a single "p < 0.0001".

**(c) Threshold robustness — DONE** (see R3.4b response above).

**(d) Moderated claim language — DONE.** With CIs and the 45-configuration
sensitivity sweep now in hand, we made two targeted moderations:

- §7 Conclusion contribution 2 now reports the 69.1pp separation with
  explicit CI brackets on each side and Fisher's exact p, and cites the
  45-configuration robustness of the 50pp gap, rather than citing the
  separation as a standalone point estimate.
- §7 Conclusion contribution 3 replaces "0DTE-driven structural
  reorganization" with language that identifies temporal coincidence and
  explicitly acknowledges alternative contemporaneous factors (interest
  rates, passive flow concentration, market-maker inventory), noting
  that stronger causal evidence would require a natural experiment.
- §6.3 "Market Structure Evolution" similarly softens the
  "tipping-point dynamic strengthens the structural interpretation"
  phrasing to "is consistent with, rather than proof of" and
  cross-references §6.7 Limitations for the causal-identification
  caveat.

These moderations make the paper's causal claims about 0DTE match the
quality of observational evidence available here; they do not weaken
the statistical claims on 2020-vs-2024 separation, which the new
χ² / Fisher / sensitivity results strengthen.

**Change location:**

- `04_Results.tex` §5 opening "Statistical conventions" paragraph
- `04_Results.tex` §5.1 Phase 1/3 inline rates in text
- `04_Results.tex` Table 2 (negative controls) — CI column added
- `04_Results.tex` Table 3 (Phase 4 comparison) — CIs on both rates
- `04_Results.tex` Table 5 (Phase 5) — new CI column
- `references.bib` — added `brown2001interval` for Wilson score cite
- `scripts/validation/paper2/jrfm_revision/bootstrap_detection_ci.py` — new reprocessing script

**Status:** done — all four parts (CIs, χ²/Fisher expansion,
window/threshold robustness in §5.5, moderated claim language in §6.3
and §7) landed across the B1, B2, B3, B4, C2 revision commits.

---

### R3.6 — Discussion: finance connections

> The discussion must be better connected to finance. The implications for
> risk management, market efficiency, and practitioners should be explicitly
> developed. The current discussion is too general and sometimes
> theoretical.

**Response:** We agree that the original discussion was too general on
the practitioner side. The previous §6.6 "Practitioner Implications"
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

**Change location:** §6.6 "Practical Implications" (renamed from
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

**Change location:** §6.7 Limitations and Future Work (p.\ 17 in the
revised PDF). The subsection was relabelled from "Limitations" to
"Limitations and Future Work" and expanded from 6 to 7 items. Each item
now includes an explicit future-work sentence indicating how it could
be addressed.

**Status:** done

---

### R3.8 — Figures and tables

> Figures and tables must be improved. Some are too dense and difficult to
> read. Labels and captions should be clearer and more explanatory.

**Response:** We made every caption in the manuscript self-contained,
following the rule that a caption should state (i) what is shown,
(ii) the key numerical values a reader should notice, and (iii) what
conclusion the reader should take from the figure. Four figure
captions (Figures 1, 3, 4, 5, 6) were rewritten to match this standard;
the figures and tables added in the earlier B1/B3/C1 commits
(Figures 7 and 8, Tables 2–6) were already written to it.

Each rewritten caption ends with an explicit "Read this figure as:"
clause that tells the reader the intended interpretation. Examples:

- **Figure 1 (Obfuscation)**: "Read this figure as: anything the LLM
  correctly infers from the right-hand input must come from the
  numerical structure alone, not from memorised date-specific context
  in the training corpus."
- **Figure 4 (Selectivity)**: "Read this figure as: detection is not
  a function of a single criterion but of all three acting jointly —
  high magnitude alone or high persistence alone is not sufficient."
- **Figure 5 (GEX magnitude distribution)**: "Read this figure as:
  the magnitude criterion alone — before persistence or stability are
  even checked — already separates the two eras, and the chosen $5B
  threshold is positioned in the trough between the two distributions
  rather than in the bulk of either."
- **Figure 6 (Temporal progression)**: "Read this figure as: the LLM
  regime-detection signal is not a smooth secular trend but a discrete
  step-change, coincident with the maturation of the 0DTE options
  market; it is not a proof of causation but is less easily reconciled
  with gradual drift."

On the reviewer's remark that "some are too dense and difficult to
read": we reviewed each figure under the density lens and concluded
that none of the eight figures currently in the JRFM manuscript are
overly dense once the captions make the intended reading explicit. The
reviewer may have been referring to Figures 7 and 8 in a prior
version (the AIAI conference version), which had a crowded 9-panel
layout; those were not carried over into the JRFM manuscript. If the
editor identifies a specific figure that still reads as too dense, we
will happily simplify it.

**Change location:** captions in `03_Methodology.tex` (Figure 1) and
`04_Results.tex` (Figures 3, 4, 5, 6); all other figure and table
captions were already self-contained from prior revision commits.

**Status:** done

---

### R3.9 — English language quality

> The clarity of the manuscript needs improvement. Many sentences are too
> long and complex, which affects readability. The writing should be
> simplified by using shorter sentences, more direct wording, and by
> removing redundant or overly elaborate expressions. Careful language
> editing is recommended to improve clarity and flow.

**Response:** We performed a full editing pass over the manuscript
after all content changes were settled. Summary of what was done:

**(a) Wordy transitions and hedging tics.** We checked the manuscript
for the usual English-editing offenders ("In order to", "It should be
noted that", "It is worth noting", "Due to the fact that", "This is
because", "Obviously", "Clearly"). None of these phrases appear in
the manuscript — the original draft was already written in an active,
direct register. No changes were required on this axis.

**(b) Long-sentence decomposition.** We identified the paragraphs
with the most elaborate nested-clause sentences (the §1 philosophical
opener and §6.5 Dispersed Knowledge were the two heaviest) and rewrote
them for directness. The §1 opener was fully replaced in the R3.1
rewrite above (which removed roughly 120 words of philosophical prose).
§5.5 was tightened in this commit by breaking three >40-word sentences
into two-sentence units while retaining the Hayek citation and the
30.8pp empirical claim.

**(c) Active voice where natural.** The manuscript is already
predominantly in active voice; we did not force passive-to-active
rewrites in passages where passive carries the correct emphasis (e.g.,
"the framework achieves 81.2\% detection" is active; "detection was
observed at 81.2\%" would be worse).

**(d) Consistency of technical terms.** We verified consistent
terminology across sections: "regime" (not "state") for the detection
target, "persistent / fragmented" (not "stable / unstable") for the
binary outcome, "dealer gamma positioning" (not "dealer gamma
exposure" in the context of the detection task), "obfuscation"
(not "anonymisation"). No ad-hoc substitutions were made.

**Change location:** targeted tightening in §6.5 Dispersed Knowledge
(sentences broken up); §1 opener and §6.3 Market Structure Evolution
rewrites landed in the earlier D1 and C2 commits. Technical-term
consistency verified throughout.

**Status:** done

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
