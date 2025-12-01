# LaTeX Compilation Instructions

This document provides instructions for compiling the Paper #1 LaTeX project locally.

## Prerequisites

### Required Software

1. **MiKTeX** (LaTeX distribution for Windows)
   - Download: <https://miktex.org/download>
   - Version: 24.1 or later
   - Install with "Install missing packages on-the-fly: Yes"

2. **VS Code Extension** (Optional but recommended)
   - Extension: LaTeX Workshop by James Yu
   - Install: `code --install-extension james-yu.latex-workshop`

## Quick Start

### Option 1: Command Line Compilation

```bash
# Navigate to latex directory
cd a:\Projects\gex-llm-patterns\docs\papers\paper1\latex

# Full compilation cycle (run all commands in sequence)
pdflatex -interaction=nonstopmode Main.tex
bibtex Main
pdflatex -interaction=nonstopmode Main.tex
pdflatex -interaction=nonstopmode Main.tex
```

**Output**: `Main.pdf` (11 pages, ~1.9 MB)

### Option 2: VS Code with LaTeX Workshop

1. Open `Main.tex` in VS Code
2. Save the file (Ctrl+S)
3. Extension auto-compiles in background
4. PDF appears in side panel

**Manual Build**: Press `Ctrl+Alt+B`

## File Structure

```
latex/
├── Main.tex                      # Main document
├── 00_Header.tex                 # Preamble & packages
├── 01_Introduction.tex           # Section 1
├── 02_Related_work.tex           # Section 2
├── 03_Methodology.tex            # Section 3
├── 04_Experimental_setup.tex     # Section 4
├── 05_Results.tex                # Section 5
├── 06_Discussion.tex             # Section 6
├── 07_Conclusion.tex             # Section 7
├── references.bib                # Bibliography (40 entries)
└── ../figures/                   # Figures directory (shared)
    ├── fig1_obfuscation_example.png
    ├── fig2_gex_profile.png
    ├── fig3_validation_pipeline.png
    ├── fig4_detection_comparison.png
    ├── fig5_quarterly_stability.png
    ├── fig6_validation_funnel.png
    ├── fig7_confidence_distribution.png
    └── fig8_performance_matrix.png
```

## Compilation Process Explained

LaTeX requires multiple passes to resolve all references:

### Pass 1: Initial Compilation

```bash
pdflatex Main.tex
```

- Compiles document
- Generates `.aux` file with citation references
- Creates temporary files

### Pass 2: Bibliography Processing

```bash
bibtex Main
```

- Reads citations from `.aux` file
- Processes `references.bib`
- Generates `.bbl` file with formatted references

### Pass 3: Update References

```bash
pdflatex Main.tex
```

- Incorporates bibliography from `.bbl`
- Updates cross-references
- May still show warnings about undefined references

### Pass 4: Final Pass

```bash
pdflatex Main.tex
```

- Resolves all remaining cross-references
- Finalizes page numbers
- Produces final PDF

## Common Issues & Solutions

### Issue: `pdflatex: command not found`

**Solution**: MiKTeX not in PATH. Add to environment variables:

```
C:\Users\<username>\AppData\Local\Programs\MiKTeX\miktex\bin\x64
```

Or use full path:

```bash
"C:\Users\<username>\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe" Main.tex
```

### Issue: Missing bibliography entries

**Error**:

```
Warning--I didn't find a database entry for "citation_key"
```

**Solution**: Ensure `references.bib` contains all cited entries. Check for typos in citation keys.

### Issue: Missing figures

**Warning**:

```
LaTeX Warning: File `../figures/fig1.png' not found
```

**Solution**: Verify figures exist in `../figures/` directory relative to `latex/` folder.

### Issue: Missing packages

**Error**:

```
! LaTeX Error: File `packagename.sty' not found.
```

**Solution**: MiKTeX should auto-install. If not:

```bash
mpm --install packagename
```

Or update MiKTeX:

```bash
miktex --admin --update
```

## Output Files

### Generated Files (safe to delete)

- `*.aux` - Auxiliary files with references
- `*.log` - Compilation log
- `*.out` - Hyperref outline
- `*.bbl` - Formatted bibliography
- `*.blg` - BibTeX log
- `*.toc` - Table of contents
- `*.lof` - List of figures
- `*.lot` - List of tables

### Keep These Files

- `Main.pdf` - Final compiled document
- `Main.tex` - Main document source
- `*.tex` - All section files
- `references.bib` - Bibliography database

## Cleaning Build Files

Remove all temporary files (safe to regenerate):

```bash
# Windows Command Prompt
del *.aux *.log *.out *.bbl *.blg *.toc *.lof *.lot

# PowerShell
Remove-Item *.aux, *.log, *.out, *.bbl, *.blg, *.toc, *.lof, *.lot

# Git Bash
rm -f *.aux *.log *.out *.bbl *.blg *.toc *.lof *.lot
```

## Automated Build Script

The included `build.sh` script automates the entire compilation process:

**Linux/macOS:**

```bash
cd a:/Projects/gex-llm-patterns/docs/papers/paper1/latex
chmod +x build.sh
./build.sh
```

**Windows (Git Bash/WSL):**

```bash
cd a:/Projects/gex-llm-patterns/docs/papers/paper1/latex
bash build.sh
```

The script will:

- Check for required tools (pdflatex, bibtex)
- Run all 4 compilation passes automatically
- Report any errors with helpful messages
- Display output file size and page count

## Alternative: Overleaf

For cloud-based compilation:

1. Zip entire `latex/` folder
2. Upload to <https://www.overleaf.com>
3. Compiles automatically in browser

**Note**: Overleaf requires figures to be in `figures/` subdirectory (not `../figures/`).
If uploading to Overleaf, update all `\includegraphics` paths from `../figures/` to `figures/`.

## Verification

After successful compilation, verify:

- [ ] PDF is 11 pages
- [ ] All 8 figures appear correctly
- [ ] Bibliography has 40+ references
- [ ] No "undefined reference" warnings in final pass
- [ ] File size is ~1.9 MB

## Performance Notes

**Typical Compilation Time**:

- First run: 30-60 seconds (downloads missing packages)
- Subsequent runs: 5-15 seconds per pass
- Full cycle: ~30 seconds

**Disk Space**:

- MiKTeX installation: ~300 MB
- Build files (temporary): ~2 MB
- Final PDF: ~1.9 MB

## Troubleshooting

### Enable verbose output

```bash
pdflatex Main.tex
```

(No `-interaction=nonstopmode` flag)

This will pause on errors and show detailed messages.

### Check LaTeX log

```bash
# View last 50 lines of log
tail -50 Main.log

# Windows PowerShell
Get-Content Main.log -Tail 50
```

### Verify MiKTeX installation

```bash
pdflatex --version
bibtex --version
```

Expected output:

```
MiKTeX-pdfTeX 4.18 (MiKTeX 24.1)
BibTeX 0.99d (MiKTeX 24.1)
```

## Additional Resources

- **MiKTeX Manual**: <https://docs.miktex.org/>
- **LaTeX Workshop**: <https://github.com/James-Yu/LaTeX-Workshop>
- **IEEE Templates**: <https://www.ieee.org/conferences/publishing/templates.html>
- **BibTeX Guide**: <http://www.bibtex.org/>

## Contact

For issues specific to this paper:

- **Author**: Christopher Regan (<cregan1@kennesaw.edu>)
- **Advisor**: Ying Xie (<yxie2@kennesaw.edu>)
