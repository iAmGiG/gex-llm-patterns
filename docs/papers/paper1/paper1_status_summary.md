# Paper #1 Status Summary

**Last Updated**: December 9, 2025
**Target Journal**: Journal of Financial Data Science (JFDS, PM-Research)
**Conference Version**: IEEE Big Data 2025 (Accepted, ArXiv uploaded)
**Status**: 🟢 JFDS CONVERSION IN PROGRESS

---

## Current Status

### Conference Version ✅ COMPLETE

- **IEEE Big Data 2025**: Accepted and presented
- **ArXiv**: Uploaded (cs.LG with cs.AI cross-list)
- **Location**: `docs/papers/paper1/ieee_bigdata_2025/`

### Journal Version 🔄 IN PROGRESS

- **Target**: Journal of Financial Data Science (PM-Research)
- **Branch**: `paper1/jfds-journal`
- **Location**: `docs/papers/paper1/journal_version/`
- **Current**: 19 pages, IEEEtran format (to be converted)

---

## JFDS Conversion Tasks

### Content Enhancements ✅ COMPLETE

| Issue | Task | Status |
|-------|------|--------|
| #175 | Practitioner Implementation Guidance | ✅ Added new section |
| #176 | Address Research Gaps | ✅ Enhanced limitations, added alpha puzzle |
| #177 | Articulate Derivative Value | ✅ Covered in practitioner section |
| #178 | Connect to Paper 2/3 Roadmap | ✅ Alpha puzzle + future directions |

### Format Conversion 🔄 PENDING

| Issue | Task | Status |
|-------|------|--------|
| #174 | Convert to JFDS format | 🔄 Requirements identified, conversion pending |

---

## PM-Research JFDS Format Requirements

**Source**: PMR_SubGuide_2025.pdf (PM-Research Submission Guidelines)
**Style Guide**: Chicago Manual of Style (18th Edition), Author-Date citation system

### Document Structure

| Section | Requirements |
|---------|--------------|
| **Title** | ≤12 words; start with key topic terms |
| **Abstract** | ~160 words, non-technical, no citations |
| **Highlights** | 3 bullet points (≤40 words each) - NEW SECTION NEEDED |
| **Introduction** | State purpose, findings, and relevance |
| **Headings** | Up to 3 levels; use PMR format |
| **Conclusion** | Summarize; no new material |
| **References** | Chicago Manual Author-Date; no endnotes |
| **Footnotes** | For commentary only, not citations |

### Formatting Specifications

| Element | Requirement |
|---------|-------------|
| **File Format** | Microsoft Word (.docx) OR LaTeX |
| **Page Size** | 8.5 × 11 inches |
| **Margins** | 1-inch all sides |
| **Main Font** | 12-pt Times New Roman |
| **Footnotes** | 10-pt Times New Roman |
| **Tables** | 9-pt or larger; consistent decimals |
| **Spacing** | Single-spaced; 12 pts before paragraphs; indented first line |
| **Page Numbers** | Bottom center |

### Page Order

1. Title, date, authors, affiliations, contact info
2. Title, date, abstract, highlights, keywords, JEL codes
3. Main text

### Exhibits (Figures/Tables)

- **Label all visuals as "Exhibits"** (not Tables/Figures)
- Number sequentially (Exhibit 1, Exhibit 2, etc.)
- Reference each exhibit in text with interpretation
- Must be legible in black and white
- Include sources and dates where relevant
- Tables: Create natively in Word (not images)
- Charts: Create in Excel with raw data included

### Key Conversion Tasks

| Current (IEEE) | Required (PM-Research) |
|----------------|------------------------|
| Two-column format | Single column, 8.5×11 |
| Numbered citations [1] | Author-Date (Smith 2024) |
| Figure 1, Table 1 | Exhibit 1, Exhibit 2 |
| BibTeX numerical | Chicago Author-Date |
| No highlights section | 3 bullet highlights required |
| Technical abstract | Non-technical ~160 words |
| No JEL codes | JEL classification required |

**Editor Contact**: Mitchell Gang (<m.gang@pm-research.com>)

---

## Journal Version Enhancements (Dec 2025)

### New Sections Added

1. **Practitioner Implementation Guidance** (06_Discussion.tex)
   - Role Separation (LLM vs statistical model)
   - Prompt Design guidelines
   - Signal Quality Assessment
   - Detection vs Alpha distinction
   - Obfuscation Testing for Validation
   - Raw Data Advantage

2. **The Alpha Disappearance Puzzle** (06_Discussion.tex)
   - Explicitly frames detection-profitability divergence
   - Lists candidate explanations
   - Connects to Paper 2 research

### Enhanced Sections

1. **Limitations** - Restructured with constructive framing
   - Single Asset Focus (with methodological justification)
   - Single Regime Environment (as harder test)
   - End-of-Day Granularity (with AUC validation)
   - Single Model Family (acknowledged)
   - Prompt Sensitivity (motivates methodology)
   - Interpretability Constraints (output validation approach)

2. **Future Directions** - Expanded with 5 specific paths
   - Cross-Asset Validation
   - Temporal Extension
   - Intraday Resolution
   - Multi-Model Consensus
   - Sequential Pattern Analysis (Paper 2 connection)

---

## Paper Statistics

### Current Metrics

- **Pages**: 19 (IEEE two-column)
- **Figures**: 12 (fig01-fig12)
- **Tables**: 8+ (detection, quarterly, materialization, etc.)
- **References**: 30+ citations
- **Sample Size**: 242 days × 3 patterns = 726 tests

### Key Results

- **Detection Rate**: 71.5% (unbiased prompts)
- **Materialization Accuracy**: 91.2%
- **Raw Chain Detection**: 92.3% (vs 61.5% baseline)
- **Alpha Divergence**: Sharpe 1.8 → 0.1 while detection stable

---

## Five Validation Pillars

1. **Sensitivity vs Guessing**: Non-detection days show 3.72× weaker GEX concentration (p < 0.0001)
2. **Inverse P-Hacking**: Detection days show 33% LOWER range expansion (p = 0.03)
3. **Not Profit-Chasing**: Confidence increases while alpha collapses
4. **EOD Validity**: Statistical baseline AUC = 0.681
5. **Structural Analyst**: Raw chain (92.3%) outperforms GEX-assisted (61.5%)

---

## File Locations

### Journal Version

```text
docs/papers/paper1/journal_version/
├── Regan_ObfuscationTesting.tex (main document)
├── 00_Header.tex
├── 01_Introduction.tex
├── 02_Related_work.tex
├── 03_Methodology.tex
├── 04_Experimental_setup.tex
├── 04B_Methodology_Validation.tex (Raw Chain)
├── 05_Results.tex
├── 06_Discussion.tex (JFDS enhancements)
├── 07_Conclusion.tex
├── references.bib
└── Regan_ObfuscationTesting.pdf (38 pages)
```

### Figures

```text
docs/papers/paper1/figures/
├── fig01_obfuscation_example.png
├── fig02_gex_profile.png
├── fig03_validation_pipeline.png
├── fig04_raw_chain.png
├── fig05_performance_matrix.png
├── fig06_bias_comparison.png
├── fig07_quarterly_stability.png
├── fig08_confidence_distribution.png
├── fig09_validation_funnel.png
├── fig10_gex_concentration.png
├── fig11_detection_calendar.png
├── fig12_inverse_phacking.png
└── archive/ (unused figures)
```

---

## GitHub Issues

### JFDS Conversion

- [#174](https://github.com/iAmGiG/gex-llm-patterns/issues/174) - Format Conversion
- [#175](https://github.com/iAmGiG/gex-llm-patterns/issues/175) - Practitioner Relevance ✅
- [#176](https://github.com/iAmGiG/gex-llm-patterns/issues/176) - Research Gaps ✅
- [#177](https://github.com/iAmGiG/gex-llm-patterns/issues/177) - Derivative Value ✅
- [#178](https://github.com/iAmGiG/gex-llm-patterns/issues/178) - Paper 2/3 Connection ✅

---

## Next Steps

1. **Write Highlights Section** - Create 3 bullet points (≤40 words each) for paper highlights
2. **Revise Abstract** - Shorten to ~160 words, remove technical jargon and citations
3. **Add JEL Codes** - Classify paper (likely G12, G14, C45, C55)
4. **Citation Conversion** - Convert BibTeX from numerical to Chicago Author-Date style
5. **Rename Figures/Tables** - Change all "Figure X" and "Table X" to "Exhibit X"
6. **Format Conversion** - Convert document layout to PM-Research specifications
7. **Final Review** - Proofread enhanced sections
8. **Submission** - Target 2026 (timeline TBD)

---

**Branch**: `paper1/jfds-journal`
**Worktree**: `gex-llm-patterns-jfds`
