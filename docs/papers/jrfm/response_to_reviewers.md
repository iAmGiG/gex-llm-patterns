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

**Response:** *[to draft — proposed stance: the contribution is primarily
methodological (LLM validation through temporal obfuscation), with the GEX
regime-detection study serving as the empirical demonstration domain.
Market-microstructure observations are downstream findings, not the primary
contribution.]*

**Change location:** *§1 Introduction final paragraph + §6 Conclusion
opening; contribution restated consistently.*

**Status:** todo

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

**Response:** *[to draft — three parts:
  (a) Full LLM system + user prompts added as Appendix A, lifted verbatim
      from `src/llm/mechanics_prompt_builder.py` and related modules.
  (b) Threshold sensitivity sweep (persistence ∈ {60, 65, 70, 75, 80}%,
      magnitude ∈ {$3B, $5B, $7B}, flips ≤ {3, 5, 7}) — post-hoc on the
      existing 2,221 evaluations, presented as a heatmap or table.
  (c) Temperature = 1.0 reproducibility note: we use the OpenAI Batch API
      with fixed `seed`/deterministic settings where available; we report
      variance across repeated runs on a held-out sample.]*

**Change location:** *§3 Methodology (threshold justification); new
Appendix A (prompts); new Appendix B or §3.5 (sensitivity table +
reproducibility note).*

**Status:** todo — mostly writing; sensitivity sweep is post-hoc reprocessing

---

### R3.5 — Statistical rigour in results

> The results section must include statistical validation. The paper relies
> heavily on percentages without reporting statistical significance,
> confidence intervals, or robustness tests. These must be added. Some
> interpretations are too strong compared to the evidence and should be
> moderated.

**Response:** *[to draft — additions:
  (a) Bootstrap 95% confidence intervals on each detection rate in Tables
      and Phase summaries (Phase 1 baseline, full 2024, 2020 comparison,
      multi-year panel).
  (b) Fisher / χ² tests on contingency tables (already have φ = 0.672,
      p < 0.0001; expand reporting with test statistic, df, exact p).
  (c) Robustness to window length (30 / 45 / 60 days) and to the
      persistence / magnitude thresholds (cross-reference R3.4 sensitivity).
  (d) Moderate strong-claim language in §5 Discussion.]*

**Change location:** *§4 Results (CI columns in detection tables + new
robustness paragraph); §5 Discussion (softened causal language).*

**Status:** todo — requires post-hoc bootstrap on existing results

---

### R3.6 — Discussion: finance connections

> The discussion must be better connected to finance. The implications for
> risk management, market efficiency, and practitioners should be explicitly
> developed. The current discussion is too general and sometimes
> theoretical.

**Response:** *[to draft — add a subsection "Practical Implications" with
three angles:
  (a) Risk management — dealer gamma regimes as a leading indicator for
      realised volatility clustering; pinning behaviour at OpEx.
  (b) Market efficiency — the coexistence of stable detection with
      collapsing Sharpe (1.8 → 0.1) reinforces the structural-mechanics
      interpretation over exploitable inefficiencies.
  (c) Practitioners — how a regime-aware overlay could inform dealer-side
      hedging and sell-side positioning, with caveats on single-asset scope.]*

**Change location:** *§5 Discussion, new §5.x Practical Implications.*

**Status:** todo — writing only

---

### R3.7 — Limitations expansion

> The limitations section must be expanded. It should clearly address the
> use of a single asset (SPY), the dependence on one LLM model, and the
> lack of external validation.

**Response:** *[to draft — expand §5 Limitations to explicitly cover:
  (a) Single-asset scope: SPY only; future work covers cross-asset
      (QQQ / IWM / individual names) validation.
  (b) Single-model dependence: o4-mini only; future work covers
      GPT-4o / Claude / open-source LLM replication with identical prompts.
  (c) No external validation: no held-out dataset from an independent
      source; future work covers CBOE / OPRA cross-check and replication on
      additional years.]*

**Change location:** *§5.x Limitations and Future Work.*

**Status:** todo — writing only

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
