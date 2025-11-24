# IEEE Big Data 2025 Camera-Ready Submission Checklist

**Paper:** Testing LLM Structural Reasoning in Market Microstructure Through Unbiased Obfuscation
**Conference:** IEEE International Conference on Big Data 2025 (Workshop Paper)
**Submission System:** <https://wi-lab.com/cyberchair/2025/bigdata25/>

---

## Important Deadlines

| Item | Deadline |
|------|----------|
| **Video Presentation** | November 20, 2025 |
| **Camera-Ready Paper** | November 23, 2025 |
| **Conference Dates** | December 8-11, 2025 (Macau, China) |

---

## Camera-Ready Submission Requirements (5 Steps)

### Step 1: IEEE Electronic Copyright Form (eCF) ✅ TODO

**What to do:**

- Access eCF through submission system (CyberChair link provided in acceptance email)
- Complete copyright transfer form for your paper
- **CRITICAL:** Verify paper title and author names/affiliations are CORRECT before submitting eCF
- **You cannot redo the form once submitted**

**Copyright Options (typical):**

- **IEEE Copyright:** Transfer copyright to IEEE
- **Crown Copyright:** For government employees
- **Creative Commons:** CC-BY license (if applicable)

**Status:** [ ] Not Started | [ ] In Progress | [ ] Completed

**Notes:**

- eCF must be submitted before paper can be published on IEEE Xplore
- Download confirmation after submission

---

### Step 2: PDF eXpress Validation ✅ TODO

**What to do:**

- Access PDF eXpress at: <https://ieee-pdf-express.org/>
- **Conference ID:** 66926X
- Opens: October 1, 2025
- Upload your PDF or LaTeX source files for validation
- Tool checks IEEE Xplore compatibility

**PDF Requirements:**

- ✅ **Format:** IEEE 2-column conference format
- ✅ **Page limit:** 10 pages max (including figures, tables, references)
- ✅ **Page size:** 8.5" x 11" (US Letter)
- ✅ **Fonts:** ALL fonts embedded and subset
- ✅ **Graphics:** Minimum 300 dpi resolution
- ✅ **Compatibility:** Acrobat 5.0 optimized
- ✅ **File format:** PDF only

**Current Status:**

- [x] PDF already generated at 10 pages (Main.pdf)
- [ ] PDF eXpress validation (opens Oct 1, 2025)
- [ ] Validated PDF downloaded

**Status:** [ ] Not Started | [ ] In Progress | [ ] Completed

**Notes:**

- PDF eXpress is validation tool, NOT submission system
- Keep validated PDF for final submission

---

### Step 3: Final PDF + Source Files Submission ✅ TODO

**What to do:**

- Upload TWO files through CyberChair submission system:
  1. **Camera-ready PDF** (validated by PDF eXpress)
  2. **Source files archive** (tar.gz or zip with LaTeX source)
- Verify both files upload successfully

**Source Files Package Requirements:**

- All .tex files (Main.tex, 00-07 sections)
- references.bib (bibliography)
- figures/ folder (all PNG files at 300 DPI)
- README_BUILD.txt (build instructions for reviewers)
- **Max size:** 320MB (ours is ~3-5MB total)
- **Format:** tar.gz OR zip

**Creating Source Package:**

```bash
# Windows
cd docs\papers\paper1\ieee_bigdata_2025\latex
package_submission.bat

# Linux/Mac/Git Bash
cd docs/papers/paper1/ieee_bigdata_2025/latex
bash package_submission.sh
```

**Pre-Submission Checklist:**

- [ ] PDF validated by PDF eXpress
- [ ] Source package created (tar.gz or zip)
- [ ] Source package under 320MB
- [ ] All fonts embedded in PDF
- [ ] Graphics render clearly at 300 dpi
- [ ] Page count = 10 pages exactly
- [ ] Copyright notice added (if required by eCF)
- [ ] Author names/affiliations match eCF submission
- [ ] No page numbers in footer (IEEE template handles this)
- [ ] README_BUILD.txt included in source package

**Status:** [ ] Not Started | [ ] In Progress | [ ] Completed

**Deadline:** November 23, 2025

---

### Step 4: Conference Registration ✅ TODO

**What to do:**

- Register for IEEE Big Data 2025 conference
- Pay registration fee
- Download/save registration receipt
- Upload receipt to submission system

**Registration Options:**

- **In-person:** Attend conference in Macau (Dec 8-11, 2025)
- **Virtual:** Remote presentation (if offered)

**Status:** [ ] Not Started | [ ] In Progress | [ ] Completed

**Notes:**

- At least one author MUST register for the paper to be published
- Early bird registration typically cheaper

---

### Step 5: Presentation Format Indication ✅ TODO

**What to do:**

- Indicate in submission system: In-person vs Virtual presentation
- Confirm presentation format preference

**Options:**

- [ ] In-person presentation (Macau, China)
- [ ] Virtual presentation (if available)

**Status:** [ ] Not Started | [ ] In Progress | [ ] Completed

---

## Video Presentation Requirements ✅ TODO

**Deadline:** November 20, 2025

**Format (Based on Standard IEEE Practices):**

- **Duration:** 15-20 minutes (target 15:00 exactly)
- **Format:** MP4 video file
- **Resolution:** 1920x1080 (1080p)
- **Codec:** H.264 video, AAC audio
- **Content:** Slides with voiceover narration (no camera required)
- **File size:** Under 500 MB (slides-only: 50-200 MB typical)

**Preparation Status:**

- [x] Presentation outline created (ieee_bigdata_2025_outline.md)
- [x] Figures prepared (8 external figures in figures/ folder)
- [ ] PowerPoint deck built (15 slides)
- [ ] Video recorded
- [ ] Video edited and exported
- [ ] Video submitted

**Related Files:**

- Outline: `docs/presentations/ieee_bigdata_2025_outline.md`
- Figures: `docs/presentations/ieee_bigdata_2025/figures/` (8 files)
- Figure mapping: `docs/presentations/ieee_bigdata_2025_figures.md`

---

## Current Paper Status

**Location:** `docs/papers/paper1/ieee_bigdata_2025/`

**Paper Details:**

- **Title:** Testing LLM Structural Reasoning in Market Microstructure Through Unbiased Obfuscation
- **Current pages:** 10 (verified via MiKTeX build)
- **Format:** IEEE 2-column conference format
- **Template:** IEEE Computer Society Proceedings Manuscript Format
- **Citations:** 27 (condensed from 42 in master version)

**Files:**

- `latex/` - LaTeX source files
- `Main.pdf` - Current 10-page camera-ready PDF
- `paper1-errata.md` - Change documentation

---

## Master Version Archive

**Location:** `docs/papers/paper1/archive/master_journal_version/`

**Purpose:** Preserves full 12-page version with complete citations (42 total) for future journal submission expansion to 30-40 pages.

---

## Action Items Summary

**Immediate (This Week):**

- [ ] Complete IEEE eCF copyright form
- [ ] Build PowerPoint deck (15 slides)
- [ ] Record video presentation

**By November 20:**

- [ ] Submit video presentation

**By November 23:**

- [ ] Validate PDF with PDF eXpress (when available Oct 1)
- [ ] Submit final camera-ready PDF
- [ ] Complete conference registration
- [ ] Upload registration receipt

---

## Useful Links

- **Submission System:** <https://wi-lab.com/cyberchair/2025/bigdata25/>
- **Camera-Ready Instructions:** <https://wi-lab.com/cyberchair/2025/bigdata25/scripts/BigData_2025_Camera_ready_instruction.php?subarea=S>
- **PDF eXpress:** <https://ieee-pdf-express.org/> (Conference ID: 66926X, opens Oct 1)
- **IEEE Templates:** <https://www.ieee.org/conferences/publishing/templates.html>
- **Conference Website:** <https://bigdataieee.org/BigData2025/>

---

## Notes

- **Copyright form cannot be redone** - verify all details before submission
- **PDF eXpress opens October 1, 2025** - validation step must wait until then
- **At least one author must register** for paper to be published
- **Video format not specified** - using standard IEEE practices (slides-only MP4)
- **Additional pages cost $100 each** - current 10 pages meets limit

---

**Last Updated:** 2025-11-13
**GitHub Issue:** #125 (IEEE Big Data 2025 camera-ready submission)
