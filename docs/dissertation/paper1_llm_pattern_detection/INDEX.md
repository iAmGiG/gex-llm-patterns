# Paper #1 Dissertation Archive - File Index

**Quick Navigation Guide**

---

## Start Here

**📄 paper1_executive_summary.md** (5 KB)

- One-page overview
- Key results at a glance
- Perfect for quick reference or committee introduction

**📖 README.md** (12 KB)

- Comprehensive overview of the entire paper
- Research question, methods, findings, significance
- Connection to broader dissertation (3-paper arc)
- Reviewer feedback and revision status

---

## Detailed Content

**🔬 key_findings_and_implications.md** (12 KB)

- Deep dive into 5 primary findings
- Methodological contributions explained
- Academic significance and impact
- Integration with Papers #2 and #3

**📊 validation_summary.md** (13 KB)

- All validation data and statistics
- Multi-pattern results tables
- Quarterly analysis breakdown
- Granger causality results
- Statistical power calculations
- Pattern specifications

---

## Visual Materials

**🖼️ figures/** (1.8 MB total)

8 core figures from the paper:

1. **fig1_obfuscation_example.png** (288 KB)
   - Shows obfuscation methodology
   - Before/after comparison of data sanitization

2. **fig2_gex_profile.png** (248 KB)
   - Example GEX profile for single day
   - Strike distribution and open interest

3. **fig3_validation_pipeline.png** (184 KB)
   - Complete validation framework overview
   - Three-level validation process

4. **fig4_detection_comparison.png** (231 KB)
   - Biased vs unbiased prompt comparison
   - 28.5 percentage point detection drop

5. **fig5_quarterly_stability.png** (236 KB)
   - Detection vs profitability divergence
   - Q1→Q4 trend analysis

6. **fig6_validation_funnel.png** (72 KB)
   - Testing pipeline from data → results
   - Sample size flow diagram

7. **fig7_confidence_distribution.png** (229 KB)
   - LLM confidence scores histogram
   - Shows calibration quality

8. **fig8_performance_matrix.png** (279 KB)
   - Multi-pattern performance heatmap
   - Detection, accuracy, alpha across patterns

---

## Source Materials

**📝 latex_source/** (Complete LaTeX project)

Organized IEEE-format LaTeX files:

**Main Document**:

- `Main.tex` - Primary document with structure
- `00_Header.tex` - Preamble, packages, settings
- `references.bib` - Bibliography (13 core citations)

**Content Sections**:

- `01_Introduction.tex` - Research question and motivation
- `02_Related_work.tex` - Background on LLMs, gamma exposure, dealer constraints
- `03_Methodology.tex` - Obfuscation testing, WHO→WHOM→WHAT framework
- `04_Experimental_setup.tex` - Data sources, pattern specs, validation criteria
- `05_Results.tex` - Primary findings and ablation study
- `06_Discussion.tex` - Interpretation, limitations, significance
- `07_Conclusion.tex` - Contributions and future work

**Compilation**:

- `COMPILE_INSTRUCTIONS.md` - How to compile locally or on Overleaf
- `README.md` - LaTeX project documentation

**To compile**:

```bash
cd latex_source/
pdflatex Main.tex
bibtex Main
pdflatex Main.tex
pdflatex Main.tex
```

---

## Reading Recommendations

### For Quick Overview (5 minutes)

1. Read **paper1_executive_summary.md**
2. Look at **fig5_quarterly_stability.png** (detection vs profitability)
3. Look at **fig4_detection_comparison.png** (prompt bias)

### For Committee Presentation (15 minutes)

1. Read **README.md** (comprehensive overview)
2. Review **key_findings_and_implications.md** (significance)
3. Browse figures/ (visual support)

### For Deep Understanding (45 minutes)

1. Read **README.md** (context)
2. Read **key_findings_and_implications.md** (findings)
3. Read **validation_summary.md** (data)
4. Review **latex_source/** (full paper)

### For Replication/Extension

1. Review **validation_summary.md** (methods and data sources)
2. Check reproducibility commands in validation_summary.md
3. Examine **latex_source/** for technical details

---

## File Organization Summary

**Total Files**: 20 files across 3 directories
**Total Size**: ~2.1 MB

**Breakdown**:

- Documentation: 4 markdown files (42 KB)
- Figures: 8 PNG files (1.8 MB)
- LaTeX source: 8 files (varies)

**Consolidation**: Reduced from 50+ files in original paper1/ directory to 20 essential files

**Same Content**: All information preserved, just reorganized for dissertation reference

---

## Key Statistics Quick Reference

**Sample**: 242 trading days (2024), 94% coverage
**Patterns**: 3 (gamma positioning, stock pinning, 0DTE hedging)
**Detection**: 71.5% average (unbiased prompts)
**Accuracy**: 91.2% (predictions materialize)
**Statistical Power**: >99%
**Pass Threshold**: >60% detection, >75% accuracy
**Result**: ALL patterns PASS

**Prompt Bias**: 28.5 pp detection drop (100% → 71.5%)
**Profitability Trend**: +21 bps (Q1) → -1 bps (Q4)
**Significance**: Detection persists when alpha disappears

---

## Related Materials (Outside This Archive)

**Original Paper Directory**: `docs/papers/paper1/`

- Contains draft sections, planning docs, additional figures
- Preserved for historical reference
- NOT needed for dissertation (everything consolidated here)

**Validation Data**: `reports/validation/pattern_taxonomy/`

- Raw YAML files with all 242 days of results
- 3 files: gamma_positioning_SPY_2024_unbiased.yaml, etc.
- Each ~263 KB with full LLM reasoning
- Reference only (data summarized in validation_summary.md)

**Code Repository**: `scripts/validation/`, `src/validation/`

- Python scripts for validation pipeline
- OutcomeCalculator, PatternTaxonomy, DataObfuscator classes
- Replication requires these (paths documented in validation_summary.md)

---

## Version History

**v1.0** (November 10, 2025)

- Initial dissertation archive creation
- Consolidated from 50+ files to 20 essential files
- All content preserved, reorganized for clarity

---

## Contact

**Questions about this archive?**

- Author: Christopher Regan (<cregan1@kennesaw.edu>)
- Advisor: Ying Xie (<yxie2@kennesaw.edu>)

**Need to cite Paper #1?**

- See citation in README.md or paper1_executive_summary.md

**Want to extend this work?**

- See "Future Work" sections in key_findings_and_implications.md
- Papers #2 and #3 roadmap in README.md

---

**This archive is self-contained and ready for dissertation inclusion.**

All figures, data summaries, findings, and LaTeX source are included.
No external dependencies required for understanding the work.
