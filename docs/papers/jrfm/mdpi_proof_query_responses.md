# MDPI Proof — Query Response Sheet (jrfm-4256551)

Recommended response for each `%MDPI:` query in `jrfm-4256551-edited-CORRECTED.tex`.
Keyed by proof line number. **★ = needs an author decision/action (≈8 items); the rest are routine confirmations.**

## A. Author identity / corresponding author — ★ AUTHOR MUST CONFIRM

| Line | Query | Recommended response |
|---|---|---|
| 45 ★ | Name differs from susy.mdpi.com | "Publish as **Christopher Regan**. The susy.mdpi.com profile shows 'Christopher Michael Regan'; the correct published form is Christopher Regan. ORCID 0009-0009-3777-6148 is correct and links both." |
| 46 ★ | Confirm corresponding author | "Confirmed: **Christopher Regan**, cregan1@kennesaw.edu is the corresponding author." |
| 48 | "Dear Authors," (MDPI cover-note opener) | N/A — not a query; opening of MDPI's note block. No response needed. |
| 60 ★ | Email added per susy — confirm | "Confirmed: cregan1@kennesaw.edu is correct." |

## B. Figure-citation queries — RESOLVED (we added the citations)

| Line | Query | Recommended response |
|---|---|---|
| 481 | Cite Fig + (2) explain colors | "Figure is now cited in text in numerical order (Section 5.3, framework-selectivity discussion). (2) The color/legend is described in the caption; no further color explanation is needed." |
| 521 | Cite figure in numerical order | "Resolved — now cited in text in numerical order (Section 5.4, GEX-magnitude paragraph)." |
| 546 | Wrong order: Fig 6 after Fig 3 | "Resolved — all eight figures are now cited sequentially (1–8); Figures 4 and 5 are cited before Figure 6 in the revised text." |
| 617 | Minus-sign confirm + cite figure | "Figure now cited in text in numerical order (HMM benchmark, Section 5.7). Minus-sign revision in the figure: see item 186/617 in §F below." |
| 658 | Cite figure + en-dash | "Figure now cited in numerical order (end of LLM Reasoning Quality, Section 5.8). En-dash: confirmed, please apply (see §E)." |

## C. Reference-list completeness — ★ provide the values below

| Line | Query | Recommended response |
|---|---|---|
| 94 | "(SPY, 2024)" a citation? | "Not a reference citation. 'SPY, 2024' denotes the SPY index ETF over calendar-year 2024 (the dataset), not a bibliographic source. No reference required." |
| 346 | "(SPY, 2024)" a citation? | Same as line 94 — "Not a citation; it is the dataset descriptor (SPY ETF, year 2024)." |
| 1244 ★ | SSRN id 5641974 — URL + access date | "URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5641974 (accessed on 16 May 2026)." |
| 1284 ★ | CBOE report — add publisher | "Publisher: **Cboe Global Markets**." |
| 1299 ★ | SSRN id 4692190 — URL + access date | "URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4692190 (accessed on 16 May 2026)." |
| 1317 ★ | "Republished by" removed — confirm | "Please **restore** 'Republished by SpotGamma'. The Goldman Sachs note is publicly retrievable only via the SpotGamma republication (the cited URL); without it the reference is not locatable." |
| 1427 ★ | arXiv:2512.17923 removed — confirm | "Please **retain** arXiv:2512.17923. The IEEE BigData 2025 workshop proceedings are not yet formally indexed; the arXiv version is the accessible record." |
| 1436 | Publisher added (ACL) — confirm | "Confirmed — Association for Computational Linguistics is correct." |
| 1442 ★ | SpotGamma doc — add publisher | "Publisher: **SpotGamma** (self-published technical documentation)." |

## D. Run-in headings / list-vs-title — recommend "keep as run-in heading"

| Line | Query | Recommended response |
|---|---|---|
| 85 | Research gap — list or title? | "Keep as a run-in paragraph heading (title style), not a list." |
| 399 | Statistical conventions — list or title? | "Keep as a run-in paragraph heading (title style)." |
| 772 | Formatted as list + label added | "Confirmed." |
| 874 | Future directions — list/indention? | "Keep as a run-in paragraph heading (bold lead-in), consistent with the other run-in headings; no list needed." |

## E. MDPI made a change, asks confirm — answer "Confirmed" (routine)

Lines **67, 86, 172, 180, 292, 564, 588, 677, 976, 1215, 1436**: **"Confirmed."**
(67 = four-digit numbers without commas; 86/588/677 = "Section" symbol change; 172/292/976/1215 = added indention; 180 = standard date format; 564 = en-dash for numeric ranges — confirm and please apply throughout; 1436 = ACL publisher.)

## F. Typographic-convention queries — recommend a single consistent policy

| Line(s) | Query | Recommended response |
|---|---|---|
| 81, 187, 417, 487, 510 | Is bold necessary? | "Remove the decorative bold in running prose. **Retain** bold only on the run-in paragraph lead-in labels (e.g., 'Single-day validation.', 'Future directions') — those are intentional section lead-ins, not emphasis." |
| 82 | Are italics necessary? | "Remove decorative italics in prose; retain italics only for defined terms on first use and for statistical variables." |
| 192 | Is the font necessary? | "Remove the non-standard font; use the body font. Apply throughout." |
| 367 | Explain italics in table footer | "The italic rows ('Detection comparison', 'Reasoning quality') are sub-group headers within the table that separate the two metric blocks; retain the italics — they mark grouping, not emphasis." |
| 982 ★ | Should *n*/*N* be italic (whole text)? | "Yes — set statistical variables (*n*, *N*, *p*, *r*, *φ*, *χ²*) in italic math style throughout, per standard MDPI/statistical convention." |
| 1000 ★ | Remove blank row in verbatim (whole text)? | "Yes — remove the leading blank row inside the verbatim prompt blocks throughout." |

## G. Back-matter — accept MDPI suggestions

| Line | Query | Recommended response |
|---|---|---|
| 889 | Recommend removing the extra sentence; "Not applicable" suffices | "Accepted — set Institutional Review Board Statement to just **'Not applicable.'**" |
| 895 ★ | Provide data-availability access date | "Add: 'accessed on **16 May 2026**'." |

## H. Figure-image edits — ★ requires regenerating the figure assets

| Line | Query | Recommended response / action |
|---|---|---|
| 186, 617 | Change hyphen (-) to minus sign (−, U+2212) **inside the figure** | The minus glyph lives in the PNG axis labels, so MDPI cannot fix it in typesetting. **Author decision:** either (a) we regenerate the affected figures from their plotting scripts with a Unicode-minus axis formatter and supply replacements, or (b) respond that the axis uses the standard hyphen-minus and request it be accepted as-is. Recommended: (a) if time permits before final files are locked; (b) is acceptable and common for raster scientific figures if not. |

---

## Summary for the author

- **Routine confirmations (just "Confirmed")**: §E (11 lines) + several in §B/§D — no decisions needed.
- **Resolved by our edits**: all five figure-citation queries (§B) — answer text provided.
- **Provide-the-value (have the values, §C)**: SSRN URLs, Cboe/SpotGamma publishers, ACL publisher — copy from the table.
- **Real author decisions (★, ≈8)**: name/corresponding-author (45/46/60), retain arXiv & "Republished by" (1427/1317), *n*/*N* italics policy (982), verbatim blank-row (1000), data-availability date (895), and the figure minus-sign question (186/617 — the only one that may need a figure regenerate).

Nothing here is factual/scientific — all production/typesetting. The scientific content of the proof is already correct and locked.
