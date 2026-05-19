# Editorial Notice — jrfm-4256551: Proactive Disclosure + Title Change

**To:** JRFM Editorial Office; Avery Li (MDPI Assigned Editor)
**From:** Christopher Regan (corresponding author), Ying Xie
**Re:** Manuscript jrfm-4256551
**Date:** <fill on send>

---

## RESOLVED — Editorial decision (Avery Li, email reply)

The editor responded with the following ruling, which is now implemented:

- **Title change: APPROVED.** Use the preferred option:
  *"Temporal Obfuscation Testing for LLM Structural Reasoning: From
  Single-Day Dealer Constraints to Persistent Market Regimes."* Applied in
  both the returnable proof (`jrfm-4256551-edited-CORRECTED.tex`) and the
  repo source (`Regan_Xie_JRFM.tex`).
- **Disclosure: DECLINED by the editor.** Avery Li explicitly advised
  *against* adding any explanation about the two conference papers,
  reasoning that the title change alone removes the duplicate-submission
  confusion, that the manuscript is substantially different with no
  copyright issue, and that the JRFM manuscript was submitted earlier than
  the AIAI conference paper. Accordingly, the two-paper disclosure paragraph
  has been **removed** from both the proof and the repo source, and the
  now-unused `regan2026regimes` (AIAI) bib entry has been removed from
  `references.bib`. The original IEEE-only companion-paper sentence is
  restored; the MDPI line-158 copyedit query is resolved by this editorial
  instruction (title revised, no disclosure added).

Net final state: **title changed, no disclosure**. The text of the original
notice below is retained as the historical record of what was sent to the
editor; it is superseded by the decision above.

---

Dear Avery Li and the JRFM Editorial Office,

While preparing the copyedited proof of jrfm-4256551, we wish to proactively
disclose the relationship between this manuscript and two of our prior
peer-reviewed conference papers, and to request a title change for the
journal article. We raise this now, before returning the proof, so that the
editorial overlap assessment is fully informed.

## 1. Relationship to prior conference work

This journal article draws on the same research program as two conference
papers by the same authors:

1. **Regan & Xie (2025)**, "Inferring Latent Market Forces: Evaluating LLM
   Detection of Gamma Exposure Patterns via Obfuscation Testing," 2nd IEEE
   International Workshop on Large Language Models for Finance (LLM-Finance),
   IEEE BigData 2025. This paper established the **single-day**
   dealer-constraint detection results summarized in Section 4.1.

2. **Regan & Xie (2026)**, "Validating LLM Structural Reasoning: Detecting
   Persistent Market Regimes Through Temporal Obfuscation," 22nd IFIP AIAI
   2026 (Springer, IFIP AICT), Chania, Crete, Greece. This paper introduced
   the **30-day multi-day regime-detection** framework and the 2020–2025
   0DTE-evolution analysis.

The journal manuscript (and its predecessor submission, from which the
JRFM submission was formatted) has carried the title *"Validating LLM
Structural Reasoning: Detecting Persistent Market Regimes Through Temporal
Obfuscation"* since before the AIAI 2026 camera-ready was accepted (AIAI
acceptance/camera-ready: April 2026; the journal-lineage manuscript was
submitted in March 2026). The shared title therefore reflects a common
origin, not a second submission of the conference paper. **To remove any
possibility of confusion or any appearance of duplicate publication, we
propose to retitle the journal article** (options in §3 below) and to add
an explicit extension/disclosure statement (text in §4 below).

## 2. What is, and is not, new in the journal article

We want to be candid about the nature of the extension:

- The journal article **unifies** the single-day (IEEE BigData 2025) and
  multi-day (AIAI 2026) results into a single two-temporal-scale validation
  framework — a synthesis present in neither conference paper.
- It adds material **not present in either conference paper**: a
  Markov-switching benchmark establishing the detector is not a relabelled
  volatility-regime classifier; a 45-configuration threshold-sensitivity
  analysis; bootstrap and Wilson confidence intervals throughout; and an
  expanded methodological appendix (full prompt, API configuration, output
  schema).
- The **underlying experiments are those reported in the conference
  papers**; no new experiments were conducted for the journal article, and
  the manuscript prose has been written in full for this article (we
  measured negligible verbatim overlap with the AIAI text).

We believe this constitutes a substantial extension consistent with the
conference-to-journal norm, but we prefer the editor to make that
determination with the complete picture rather than infer it.

## 3. Title change (applied in the returned proof)

To differentiate the journal article from the AIAI 2026 conference paper
and signal its broader, multi-scale scope, we have **retitled the article
in the returned proof** to:

- **(applied)** "Temporal Obfuscation Testing for LLM Structural
  Reasoning: From Single-Day Dealer Constraints to Persistent Market
  Regimes"

If the editorial office would prefer a different title, we are glad to
adopt either alternative below (or any wording you suggest):

- **(B)** "Validating LLM Structural Reasoning Across Temporal Scales: A
  Multi-Scale Obfuscation Study of Dealer-Gamma Market Regimes"
- **(C)** "Distinguishing Reasoning from Memorization in Financial LLMs: A
  Multi-Scale Temporal-Obfuscation Validation of Dealer-Gamma Regime
  Detection"

## 4. Disclosure statement (applied in the returned proof)

We have added the following disclosure to the article (at the end of the
Obfuscation Testing subsection of the Related Work section, where the
copyedited proof carried the editorial query on this point). We are happy
to move it to a title footnote or the end of Section 1 if the editorial
office prefers a different placement:

> *This article is an extended journal version that consolidates and
> substantially extends two of the authors' prior conference papers:
> Regan & Xie (2025, IEEE BigData / LLM-Finance), which established
> single-day dealer-constraint detection under temporal obfuscation; and
> Regan & Xie (2026, AIAI / Springer IFIP AICT), which introduced the
> 30-day multi-day regime-detection framework and the 2020–2025
> 0DTE-evolution analysis. This article unifies the single-day and
> multi-day scales into one validation framework and adds a Markov-switching
> benchmark, a 45-configuration threshold-sensitivity analysis, bootstrap
> and Wilson confidence intervals throughout, and an expanded methodological
> appendix. The underlying experiments are those reported in the conference
> papers; no new experiments were conducted, and the text has been written
> in full for this article.*

## 5. Materials we can provide

We can supply the AIAI 2026 camera-ready PDF and the IEEE BigData 2025
paper to the editorial office for the overlap/originality assessment on
request. We are happy to adjust the disclosure wording or title to meet
JRFM and MDPI editorial-policy requirements.

The retitle and disclosure are already incorporated in the proof we are
returning; we will gladly adjust either the title wording or the disclosure
placement should the editorial office prefer.

With thanks,
Christopher Regan (corresponding author), on behalf of both authors
cregan1@kennesaw.edu

---

### Internal notes (not part of the message — for the authors)

- **Confirm exact dates before sending.** JRFM/predecessor submission date
  vs. AIAI acceptance date: repo evidence shows the JRFM (MDPI) initial
  format commit on 2026-03-25 and the jrfm-4256551 cover letter dated
  29 March 2026; AIAI camera-ready commits are 2026-04-17 / 2026-04-24.
  State only dates you can substantiate from submission-system timestamps.
- **Do not overclaim precedence.** The notice deliberately frames the remedy
  (retitle + disclose) rather than litigating who-titled-it-first; keep it
  that way unless you have hard submission-system proof.
- **Reuse rights.** Confirm the IEEE and Springer (IFIP AICT) copyright /
  author-reuse terms permit an extended journal version with citation
  before final submission.
- The AIAI bib entry (`regan2026regimes`) is in `references.bib`. The
  Option-A title change and the two-paper disclosure are **applied** to
  both `jrfm-4256551-edited-CORRECTED.tex` (the returnable proof) and the
  repo modular source (`Regan_Xie_JRFM.tex` title; `02_Related_Work.tex`
  disclosure). Rebuilt PDF: 29 pages, 0 undefined citations, AIAI entry
  renders in the bibliography. If the editor prefers title B/C or a
  different disclosure placement, it is a one-line change in each of the
  two files.
