# JRFM-4256551 — Final Production Proof, Per-Comment Responses

Source: `jrfm-4256551-5.21-final.pdf` (28 pages, 15 highlighted MDPI
comments). For each comment: the page, the highlighted anchor, MDPI's
text, and the recommended explicit response. **★ = author decision needed
before sending.**

Production tex (in `jrfm-4256551-5.21-final.zip` → `jrfm-4256551-tex.zip`
→ `jrfm-4256551.tex`) has had all `\hl{}` markup stripped and 7 of 45
queries auto-resolved; the 15 PDF comments are what remains open.

---

## Comments requiring only a confirmation reply (no .tex edit)

### #1 (p. 1) — meta instruction
>
> "Please review the entire text carefully. If there are any changes
> you'd like to make, please contact us as soon as possible…"

**Response:** Acknowledged. Manuscript reviewed in full; only the
specific items below require action.

### #2 (p. 1) — meta instruction
>
> "Please read all of our comments carefully and provide a response.
> We hope that every issue will be resolved."

**Response:** Acknowledged. Each comment is addressed explicitly below.

### #3 (p. 1) — Author identity and correspondence
>
> "1. Please confirm that the name of [Christopher Regan] is correct.
> 2. Please confirm that both authors are corresponding authors."

**Response:**

1. Confirmed — the published byline is **Christopher Regan**. (The
   susy.mdpi.com profile shows "Christopher Michael Regan"; the
   middle name is intentionally omitted from the byline. ORCID
   0009-0009-3777-6148 links both.)
2. Confirmed — per our prior email correspondence, **both Christopher
   Regan and Ying Xie are corresponding authors**. Christopher Regan
   (<cregan1@kennesaw.edu>) is the primary point of contact.

### #4 (p. 1) — Bold/italic preserved
>
> "Please confirm that all bold and italic formatting in the text is
> preserved as is."

**Response:** Confirmed. All bold/italic emphasis as produced matches
our intent; no changes requested.

### #5 (p. 2) — "(SPY, 2024)" — reference?

Anchor: "Applied to 242 trading days **(SPY, 2024)**" in the
Introduction's *Single-day validation* paragraph (production tex
line 94).

**Response:** **Not a reference citation.** "SPY, 2024" identifies the
dataset — the SPDR S&P 500 ETF Trust (ticker SPY) over calendar year
2024 — not a bibliographic source. No reference entry required.

### #7 (p. 10) — "(SPY, 2024)" — reference?

Anchor: same phrase in the *Detection Under Obfuscation* paragraph of
Section 4 (production tex line 346).

**Response:** **Not a citation; identical to comment #5.** "SPY, 2024"
is the dataset descriptor (SPY ETF, calendar 2024). No reference
entry required.

### #8 (p. 22) — Institutional Review Board statement
>
> "We re[moved] the highlighted sentence … generally, for cases where
> it does not apply, simply writing 'Not applicable' is sufficient."

**Response:** Accepted — confirmed. The IRB statement now reads
"Not applicable." (no further qualifier).

### #11 (p. 27) — meta instruction
>
> "Please carefully check that all references information is correct.
> Once an article is published, it is difficult to make changes."

**Response:** Acknowledged. References were re-verified by the
authors; specific items below (#13, #14, #15) carry concrete answers.

### #12 (p. 27) — "Please verify that the information is correct"

*(generic anchor in the references list; no specific field identified
in the PDF annotation)*

**Response:** Re-verified all bibliographic entries on this page. If
MDPI can flag the specific entry/field in question, the authors will
respond targetedly; otherwise, all entries are confirmed correct as
shown.

### #13 (p. 28) — URLs for the two CBOE references

Anchor:
> CBOE Global Markets (2024). *Zero days to expiration options
> (0DTE): Market structure and trading activity (CBOE Research Report)*.
> CBOE Insights.
>
> CBOE Global Markets (2025). *SPX 0DTE options jump to record 62%
> share in August*. CBOE Insights.

**Response:** URLs supplied:

- `cboe2024zero`: <https://www.cboe.com/insights/posts/zero-days-to-expiration-0dte-options/> (accessed on 24 May 2026).
- `cboe2025spx0dte`: <https://www.cboe.com/insights/posts/spx-0dte-options-jump-to-record-62-share-in-august/> (accessed on 24 May 2026). **★ Author — please verify this exact URL** for the second CBOE report; if the canonical URL differs, supply the corrected link.

### #14 (p. 28) — SSRN link updated, verify

Anchor: "SSRN ID 4692190. SSRN. [CrossRef]" — this is
`dim2023odtes` (Dim, Eraker & Vilkov, *0DTEs: Trading, Gamma Risk, and
Volatility Propagation*).

**Response:** Confirmed — the CrossRef link <https://doi.org/10.2139/ssrn.4692190>
resolves correctly to the SSRN abstract page for ID 4692190 as of
24 May 2026.

---

## Comments requiring a small .tex edit (production zip)

### #6 (p. 6) — ★ Hyphen → minus sign inside Figure 1
>
> "Please change the hyphen (-) into a minus sign (−, 'U+2212') in
> the figure, e.g., '-1' should be '−1'."

This concerns the axis/label glyphs **inside the PNG image**
(`figures/fig01_obfuscation.png`) — the "Day T-29 … T+0" labels
currently use ASCII hyphen-minus. MDPI raised the same request earlier
in the proof cycle; we previously requested "accept as-is" but MDPI
has re-flagged it in the final proof.

**Two options — author decision:**

- **(a) Regenerate the figure** with a Unicode-minus axis formatter
  (HPCC has the plotting script) and supply a replacement
  `fig01_obfuscation.png`. Same applies to any other figure where
  the matplotlib axis prints negative numbers with hyphen-minus
  (notably `fig10_hmm_agreement.png` per earlier query 617).
- **(b) Respond again:** "The figure axis labels use the standard
  hyphen-minus glyph (matplotlib default); given the production
  proof is otherwise final, please accept as-is."

**Recommendation: (a)** — since MDPI re-flagged this in the *final*
proof, doing the regenerate is the path of least friction toward
publication; the alternative risks a second round of queries. HPCC
can regenerate fig01 (and fig10) with a Unicode-minus formatter in
minutes; we then supply the replacement PNG(s) inside the zip.

### #9 (p. 22) — Access date confirmation
>
> "We added the access date." — production tex line 890:
> `accessed on 28 March 2026`.

**★ Author — date check.** 28 March 2026 was the original submission
date; the access date should be when the GitHub URL was last
verified. **Recommendation: update to "24 May 2026"** (today, the
final production date). If MDPI prefers the original submission date
for archival consistency, respond "confirmed as 28 March 2026" — both
defensible; my preference is the most recent verification date.

**If updated:** edit production tex line 890 from
`{accessed on 28 March 2026}` → `accessed on 24 May 2026`.

### #10 (p. 22) — "What is this?" (Claude Code)

Anchor: in the Acknowledgments (production tex line 895): "…the
authors used Anthropic's Claude **(Claude Code, 2025)** for the
purposes of clarifying and refining the written presentation."

MDPI wants either a URL (if web content) or a version (if software).

**Recommended response:** "Claude Code is Anthropic's command-line
AI coding assistant (software, not web content). URL:
<https://www.anthropic.com/claude-code>. Throughout manuscript
preparation we used Claude Code with Anthropic's Claude Opus 4
model family (May 2025 – May 2026 versions, including Opus 4.5–4.7
during the final-proof round). The authors have reviewed and edited
all output and take full responsibility for the content."

**★ Author — confirm the model version line** (which Opus version(s)
do you want disclosed) and whether you want the URL inlined into the
Acknowledgments sentence in the .tex or only supplied in the
response field. **Recommendation: also inline a URL into the .tex** —
e.g., change line 895's "Anthropic's Claude (Claude Code, 2025)" to
"Anthropic's Claude (Claude Code, \url{<https://www.anthropic.com/claude-code}>, 2025)".

### #15 (p. 28) — ★ Conference paper "could not be located"

Anchor (production tex lines 1387–1393): the **`regan2025obfuscation`**
entry. MDPI says:
> "We were unable to locate the original conference paper, so we have
> temporarily replaced it with the preprint version. Please confirm
> if this is correct."

In the production tex the proceedings line has been **commented out**:

```tex
Regan, C., \& Xie, Y. (2025).
\newblock Inferring latent market forces: Evaluating {LLM} detection of gamma
exposure patterns via obfuscation testing.
%\newblock In {\em 2nd IEEE international workshop on large language models for
%finance (LLM-Finance), IEEE international conference on big data (BigData),
%Macau, China}. {IEEE.}
\emph{arXiv}, arXiv:2512.17923.
```

The paper **is** published — *IEEE BigData 2025, 2nd Workshop on
Large Language Models for Finance*, 8–11 December 2025, Macau,
China. The IEEE Xplore listing may not be fully indexed yet (the
conference was Dec 2025), but the proceedings citation is correct.

**Recommended response:** "Please **restore** the full IEEE
proceedings citation **in addition to** the arXiv ID. The paper was
published at the *2nd IEEE Workshop on Large Language Models for
Finance, IEEE International Conference on Big Data (BigData) 2025*,
Macau, China, 8–11 December 2025; the IEEE Xplore DOI is
**[★ author to supply if available — please paste the IEEE Xplore
link]**, and arXiv:2512.17923 is the open-access version. The arXiv
preprint and the IEEE proceedings paper are the same work; both
should appear in the reference."

**.tex edit** (un-comment the proceedings lines, line 1391–1393):

```tex
\newblock In {\em 2nd IEEE international workshop on large language models for
finance (LLM-Finance), IEEE international conference on big data (BigData),
Macau, China}. {IEEE.}
\emph{arXiv}, arXiv:2512.17923.
```

**★ Author — please supply the IEEE Xplore DOI/URL** for this paper
so the citation is fully resolvable. If unavailable, the proceedings
citation alone (without DOI) plus the arXiv ID is sufficient.

---

## Summary — author decisions before sending

| # | Decision | Recommendation |
|---|---|---|
| #6 (fig01 hyphen) | Regenerate the figure (a) or push back (b)? | **(a) regenerate** — HPCC; supply replacement PNG(s) |
| #9 (access date) | Keep 28 Mar 2026 or update to 24 May 2026? | **Update to 24 May 2026** (most recent verification) |
| #10 (Claude Code version) | Which Opus version line + inline URL? | **Inline URL** + "Claude Opus 4 family (4.5–4.7 in final-proof round)" — confirm |
| #13 (2nd CBOE URL) | Verify exact URL | author to spot-check the URL above |
| #15 (IEEE Xplore DOI) | Supply DOI for the IEEE proceedings paper | author to supply if available; restore proceedings citation either way |

## Required .tex edits (if author approves)

All in `jrfm-4256551-tex.zip` → `jrfm-4256551.tex`:

1. **Line 890** (if D9 = update): `28 March 2026` → `24 May 2026`.
2. **Line 895** (D10 confirmed): inline `\url{https://www.anthropic.com/claude-code}` into the Claude Code mention.
3. **Lines 1391–1393** (D15): un-comment the IEEE proceedings lines; optionally append the IEEE Xplore DOI to the arXiv ID line.
4. **`figures/fig01_obfuscation.png`** (and possibly `fig10_hmm_agreement.png`) if D6 = (a): replace with Unicode-minus-formatted regenerations from HPCC.

I'll apply edits 1–3 and rebuild the return zip on your go-ahead. Edit 4 requires HPCC to supply the regenerated PNG(s).
