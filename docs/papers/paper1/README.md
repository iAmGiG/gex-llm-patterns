# Paper #1: LLM-Based Validation of Dealer Constraint Patterns in Options Markets

**Final Title**: "Validating LLM Understanding of Market Microstructure Through Obfuscation Testing"

**Status**: ✅ Published at IEEE BigData 2025 — 2nd International Workshop on Large Language Models for Finance (December 2025, Macau). An extended version combining Paper 1 + Paper 2 was prepared for IEEE Access but that submission path was not pursued (archived at [docs/archive/papers_ieee_access/](../../archive/papers_ieee_access/)).

**Venues**:

- IEEE BigData 2025 Workshop (published)

---

## Repository Structure

### `latex/` - LaTeX Project Files

Complete IEEE-format LaTeX project ready for compilation or Overleaf upload.

**Core Files**:

- `Main.tex` - Main document with abstract, sections, acknowledgments
- `00_Header.tex` - Preamble with all packages and settings
- `01_Introduction.tex` - Introduction section
- `02_Related_work.tex` - Background and related work
- `03_Methodology.tex` - Methodology (obfuscation testing, WHO→WHOM→WHAT)
- `04_Experimental_setup.tex` - Data sources, pattern specifications
- `05_Results.tex` - Primary findings and ablation study
- `06_Discussion.tex` - Interpretation and limitations
- `07_Conclusion.tex` - Contributions and future work (or `conclusion/conclusion.tex`)
- `references.bib` - BibTeX bibliography (13 core papers)

**Note**:

- All tables are embedded directly in the section .tex files (no separate tables/ directory).
- Figure paths in .tex files reference `../figures/` to use the shared figures folder at paper1 level.

### `analysis/` - Research Artifacts

Actual research data and analysis used to write the paper.

**Files**:

- `validation_results_2024.md` - Full 2024 validation results (242 days, 3 patterns)
- `prompt_bias_analysis.md` - Detailed ablation study (biased vs unbiased prompts)
- `methodology_qa.md` - Technical Q&A and design decisions

### `figures/` - Generated Visualizations

All figure files generated for the paper (25 PNG files, ~5.6 MB total).

**Core 8 Figures** (recommended for paper):

1. `figure1_system_architecture.png` (200 KB) - Validation pipeline
2. `figure2_obfuscation_example.png` (297 KB) - Obfuscation methodology
3. `figure3_detection_vs_profitability.png` (191 KB) - Key finding visualization
4. `figure4_gex_profile_clean.png` (236 KB) - GEX profile example
5. `figure5_confidence_distribution.png` (181 KB) - Detection confidence
6. `figure6_pattern_performance_bars.png` (263 KB) - Pattern-specific results
7. `figure7_biased_unbiased_comparison.png` (309 KB) - Ablation study
8. `figure8_validation_funnel.png` (187 KB) - Validation funnel

**Supporting Files**:

- `captions.md` - Detailed captions for all figures

### `archive/` - Superseded Documentation

Historical documents from the drafting process.

**Subdirectories**:

- `draft_sections/` - Original markdown drafts (superseded by LaTeX)
  - `01_introduction.md` through `08_references.md`

**Files** (meta-documentation from drafting phase):

- `documentation_index.md` - Original documentation index
- `figure_inventory.md` - Figure catalog and selection process
- `figure_review.md` - Quality review of generated figures
- `paper1_status_summary.md` - Historical status tracking
- `paper_preparation_qa.md` - Drafting process Q&A
- `table_summary.md` - Table formatting guide

### Root Files

- `README.md` - This file

**Note**: `references.bib` is maintained only in `latex/` directory to avoid duplication.

---

## Key Results Summary

**Primary Findings** (Unbiased Prompts):

- **Detection Rate**: 71.5% average (all patterns >60% threshold)
- **Prediction Accuracy**: 91.2% (predictions materialize)
- **Sample Size**: 726 tests (242 days × 3 patterns)

**Prompt Bias Impact** (Ablation Study):

- **Detection Drop**: -28.5% (100% → 71.5%)
- **Accuracy Stable**: -1.0% (92.2% → 91.2%)
- **Interpretation**: LLM detects structure without label hints

**Detection-Profitability Divergence**:

- **Detection**: Remains 84-100% across quarters
- **Alpha**: Declines from +2 bps to -1 bps
- **Implication**: Methodology detects structure, not profits

---

## Pattern Specifications

### 1. Gamma Positioning

**Type**: Structural constraint (dealer hedging)
**Detection**: 69.4% (unbiased)
**Accuracy**: 92.5%

### 2. Stock Pinning

**Type**: Strike-level price gravity
**Detection**: 67.4% (unbiased)
**Accuracy**: 90.4%

### 3. 0DTE Hedging

**Type**: Intraday hedging flows
**Detection**: 77.7% (unbiased)
**Accuracy**: 90.8%

---

## Compilation Instructions

### Local Compilation

```bash
cd latex/
pdflatex Main.tex
bibtex Main
pdflatex Main.tex
pdflatex Main.tex
```

### Overleaf

1. Zip the `latex/` directory
2. Upload to Overleaf as a new project
3. Ensure compiler is set to pdfLaTeX
4. Bibliography processor: BibTeX

---

## Scripts and Data Sources

**Visualization Scripts**: `../../scripts/visualization/`

- 11 Python scripts for generating all figures

**Validation Data**: `../../reports/validation/pattern_taxonomy/`

- `gamma_positioning_SPY_2024_unbiased.yaml` (263 KB)
- `stock_pinning_SPY_2024_unbiased.yaml` (263 KB)
- `0dte_hedging_SPY_2024_unbiased.yaml` (266 KB)
- `gamma_positioning_SPY_2024Q2.yaml` (68 KB, biased prompt)

**Configuration**: `../../config_defaults/llm_prompts.yaml`

- Pattern specifications and prompt templates

---

## Citation (Provisional)

```bibtex
@article{regan2025inferring,
  title={Inferring Latent Market Forces: Evaluating LLM Detection of Gamma Exposure Patterns via Obfuscation Testing},
  author={Regan, Christopher and Xie, Ying},
  journal={TBD},
  year={2025},
  institution={Kennesaw State University}
}
```

---

## Contact

**Primary Author**: Christopher Regan (<cregan1@kennesaw.edu>)
**Advisor**: Ying Xie (<yxie2@kennesaw.edu>)
**Institution**: Kennesaw State University, Department of Computer Science
