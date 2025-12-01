# IEEE Big Data 2025 Camera-Ready Submission

**Conference:** IEEE International Conference on Big Data 2025
**Submission Deadline:** November 23, 2025
**Video Deadline:** November 20, 2025
**Format:** 10 pages maximum (including references)
**Presentation:** Fully virtual (20-minute video)

---

## Current Status

✅ **Camera-ready PDF:** 10 pages (meets IEEE limit)
✅ **All dealer citations integrated** (Anderegg, Dim, Krishnan)
✅ **Unbiased obfuscation testing clarified** (91.2% accuracy)
✅ **Page reduction complete** (condensed from 12-page master version)

**Latest Build:** 2025-11-13
**Branch:** `paper1-reviewer-revisions`
**Commit:** `5f9df0c` (latest page reduction)

---

## Submission Requirements

### Camera-Ready Paper

- **Page Limit:** 10 pages (strict)
- **Format:** IEEE format (template compliant)
- **Content:** All figures, tables, references included
- **Deadline:** **November 23, 2025**

### Video Presentation

- **Duration:** 20 minutes maximum (15 min presentation + 5 min Q&A buffer)
- **Format:** Pre-recorded video
- **Quality:** 1080p minimum, clear audio
- **Content:** Cover full methodology, results, contributions
- **Deadline:** **November 20, 2025**

---

## Contents

### LaTeX Source (`latex/` folder)

- `Main.tex` - Master document
- `00_Header.tex` - IEEE format packages
- `01_Introduction.tex` - Condensed introduction
- `02_Related_work.tex` - **Condensed to 5 subsections** (vs. 6 in master)
- `03_Methodology.tex` - Methodology
- `04_Experimental_setup.tex` - Experimental setup
- `05_Results.tex` - Tightened results
- `06_Discussion.tex` - Condensed discussion
- `07_Conclusion.tex` - Streamlined conclusion
- `references.bib` - **27 citations** (vs. 42 in master - removed 15)
- **Main.pdf** - **10-page camera-ready PDF**

### Supplementary Files

- `paper1-errata.md` - Documentation of all changes (Issue #113)
- `build.sh` - LaTeX build script

---

## What Was Condensed (vs. Master Version)

### Citations Removed (15 total, saved ~0.8-1.2 pages)

**Removed citations:**

- finra4210 (regulatory, kept SEC)
- ge2016why (volume ratio, tangential)
- squeezemetrics2017/2020 (kept SpotGamma)
- krishnan2021market (GEX assumptions, kept Anderegg & Dim)
- ederington2007/pearson2013 (higher-order Greeks, kept mixon2009)
- grossman1988liquidity, avellaneda2010statistical (kept Frey)
- brown2020language, wei2022chain, kojima2022large (kept GPT-4 report)
- wu2023bloomberggpt (kept Lopez & Chen)
- ribeiro2020beyond (validation methods, kept core claim)

### Sections Condensed

| Section | Master Version | IEEE Version |
|---------|----------------|--------------|
| **Related Work** | 6 subsections, detailed | 5 subsections, streamlined |
| **GEX Limitations** | Full paragraph (5 sentences) | Condensed (3 sentences) |
| **Gamma Rationale** | 5 detailed arguments | Combined into 1 paragraph |
| **LLM Reasoning** | Detailed subsection | Condensed summary |
| **Validation Methods** | Full subsection | Brief paragraph |

### Page Savings

- Related Work condensing: ~1.0 pages
- Introduction tightening: ~0.3 pages
- Results/Discussion/Conclusion: ~0.5 pages
- Citation removal: ~0.8 pages
- **Total saved:** ~2.6 pages (12 → 10 pages)

---

## Key Contributions (For Presentation)

### Main Contribution

**"We prove LLMs can detect structural market constraints through unbiased obfuscation testing—achieving 91.2% prediction materialization with fully obfuscated temporal and ticker data."**

### Three-Layer Novelty

1. **Obfuscation Testing Framework**
   - First validation of LLM structural reasoning in finance
   - Removes all memorizable context (dates → "Day T+0", tickers → "INDEX_1")
   - Proves detection is mechanical, not memorized

2. **100% Pattern Detection Without Context**
   - All three patterns detected with fully obfuscated data
   - Validates LLM understands market mechanics, not statistical correlations
   - Robust across varying market conditions (2024 full year)

3. **Comprehensive Academic Foundation**
   - Anderegg (2022): Options hedging → spot volatility mechanism
   - Dim (2025): Empirical validation via order flow measurement
   - Krishnan (2021): Dealer hedging dynamics & feedback loops

---

## Submission Links

**Portal:** <https://wi-lab.com/cyberchair/2025/bigdata25/scripts/final.php?subarea=S36>
**Instructions:** <https://wi-lab.com/cyberchair/2025/bigdata25/scripts/BigData_2025_Camera_ready_instruction.php>

---

## Video Presentation Outline (20 min)

### Suggested Structure

**1. Introduction (2 min)**

- Problem: Can LLMs detect structural market constraints?
- Challenge: Distinguishing reasoning from memorization
- Our approach: Unbiased obfuscation testing

**2. Background (2 min)**

- Dealer gamma hedging constraints
- Options market mechanics (0DTE explosion)
- Why validation is critical

**3. Methodology (4 min)**

- Obfuscation testing framework (remove dates/tickers)
- Three pattern types (gamma positioning, stock pinning, 0DTE hedging)
- Validation through forward-return materialization

**4. Results (4 min)**

- 100% detection rate with obfuscated data
- 91.2% prediction materialization accuracy
- Pattern persistence across full 2024 year

**5. Discussion (2 min)**

- Implications: LLMs understand market microstructure
- Academic foundation: Anderegg, Dim, Krishnan validation
- Robustness to GEX measurement variations

**6. Conclusion (1 min)**

- First framework for validating LLM structural reasoning in finance
- Opens pathway for AI-assisted pattern detection
- Future: Cross-asset, intraday extensions

---

## Post-Submission Plans

### Immediate (Nov 23-30)

- Archive submission confirmation
- Update GitHub Issue #125 with submission details
- Document presentation feedback

### Future Journal Version

- Expand back to master version (12 pages → 30-40 pages)
- Add comprehensive robustness tests (Issue #114)
- Target journals: JOIM, JFE, RFS, Management Science
- Timeline: Q1-Q2 2026

---

## Submission Files

### Files to Submit (via CyberChair)

✅ **1. Camera-Ready PDF:** `IEEE_BigData_2025_LLM_Structural_Reasoning.pdf`

- 10 pages (meets IEEE limit)
- Validated with PDF eXpress (Conference ID: 66926X)
- All fonts embedded, 300 DPI graphics

✅ **2. Source Files Archive:** `IEEE_BigData_2025_LLM_Structural_Reasoning_Source.tar.gz` (or .zip)

- All LaTeX source files (.tex, references.bib)
- All figures (PNG, 300 DPI)
- README_BUILD.txt (build instructions)
- **Size:** ~3-5MB (well under 320MB IEEE limit)

**Creating Source Package:**

```bash
# Windows
cd latex
package_submission.bat

# Linux/Mac/Git Bash
cd latex
bash package_submission.sh
```

✅ **3. IEEE eCF Copyright Form:** Via CyberChair submission system

✅ **4. Conference Registration Receipt:** Upload after registering

### Files NOT to Submit

❌ `paper1-errata.md` - Internal documentation only
❌ `build.sh` / `build.bat` / `package_submission.*` - Build scripts (not part of submission)
❌ `Main.pdf` - LaTeX intermediate (use camera-ready version instead)
❌ Intermediate LaTeX files (.aux, .bbl, .blg, .log, .out, .synctex.gz)

---

## Build Instructions

### Windows (Batch File)

```cmd
cd docs\papers\paper1\ieee_bigdata_2025\latex
build.bat
```

### Linux/macOS/Git Bash

```bash
cd docs/papers/paper1/ieee_bigdata_2025/latex
bash build.sh
```

### Manual Build (Windows with MiKTeX)

```bash
cd docs/papers/paper1/ieee_bigdata_2025/latex
"C:\Users\gigac\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" -interaction=nonstopmode Main.tex
```

**Output Files:**

- `Main.pdf` (LaTeX intermediate, 10 pages)
- `IEEE_BigData_2025_LLM_Structural_Reasoning.pdf` (camera-ready, 10 pages)

---

**Created:** 2025-11-13
**Purpose:** IEEE Big Data 2025 workshop camera-ready submission
**Related Issue:** #125
