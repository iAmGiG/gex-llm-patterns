# Paper #1: LaTeX Source Files

IEEE conference paper format implementing the obfuscation testing methodology for LLM validation.

## Quick Compilation

### Automated Build Script (Recommended)

```bash
# Linux/macOS/Git Bash
chmod +x build.sh
./build.sh

# Windows PowerShell
bash build.sh
```

Automatically runs all compilation passes.

### Manual Compilation

```bash
pdflatex Main.tex
bibtex Main
pdflatex Main.tex
pdflatex Main.tex
```

See [COMPILE_INSTRUCTIONS.md](COMPILE_INSTRUCTIONS.md) for detailed instructions.

## Project Structure

### Main Files

- **Main.tex** - Root document with title, abstract, keywords
- **00_Header.tex** - LaTeX preamble with all package imports

### Section Files

1. **01_Introduction.tex** - Research motivation and contributions
2. **02_Related_work.tex** - Background, dealer hedging, LLMs in finance
3. **03_Methodology.tex** - Obfuscation testing framework
4. **04_Experimental_setup.tex** - Data sources, patterns, validation pipeline
5. **05_Results.tex** - Detection rates, statistical validation, Granger tests
6. **06_Discussion.tex** - Interpretation, limitations, implications
7. **07_Conclusion.tex** - Summary and future work

### Supporting Files

- **references.bib** - Bibliography database (40 entries)
- **../figures/** - Figure files (8 PNG images, shared with parent folder)

## Output

**Expected PDF**:

- Pages: 11
- Size: ~1.9 MB
- Format: IEEE two-column conference paper

## Requirements

- **MiKTeX** 24.1+ (or equivalent LaTeX distribution)
- **Figures**: 8 PNG files in `../figures/` directory
- **Packages**: IEEEtran, booktabs, graphicx, hyperref, etc. (auto-installed by MiKTeX)

## Key Results in Paper

- **Detection Rate**: 71.5% (unbiased prompts)
- **Prediction Accuracy**: 91.2%
- **Sample Size**: 242 trading days × 3 patterns = 726 tests
- **Statistical Significance**: All patterns p < 0.001

## Figure List

All figures referenced as `../figures/figN_*.png`:

1. `fig1_obfuscation_example.png` - Obfuscation methodology
2. `fig2_gex_profile.png` - GEX profile example
3. `fig3_validation_pipeline.png` - System architecture
4. `fig4_detection_comparison.png` - Biased vs unbiased
5. `fig5_quarterly_stability.png` - Detection-profitability divergence
6. `fig6_validation_funnel.png` - Validation funnel
7. `fig7_confidence_distribution.png` - Confidence scores
8. `fig8_performance_matrix.png` - Pattern performance

## Troubleshooting

### Missing pdflatex

Install MiKTeX from <https://miktex.org/download>

Add to PATH:

```bash
C:\Users\<username>\AppData\Local\Programs\MiKTeX\miktex\bin\x64
```

### Missing Packages

MiKTeX should auto-install. If not:

```bash
mpm --install packagename
```

### Missing Figures

Ensure all 8 PNG files exist in `../figures/` directory.

## For Overleaf

To upload to Overleaf:

1. Copy all `.tex` and `.bib` files
2. Create `figures/` subdirectory
3. Copy 8 PNG files to `figures/`
4. Update `\includegraphics` paths from `../figures/` to `figures/`

Or use the automated script (if available) to prepare Overleaf package.

## Clean Build

Remove temporary files:

```bash
# Windows
del *.aux *.log *.out *.bbl *.blg *.toc

# PowerShell
Remove-Item *.aux, *.log, *.out, *.bbl, *.blg, *.toc
```

## License

Academic research paper - all rights reserved pending publication.
