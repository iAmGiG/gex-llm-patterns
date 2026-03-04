# JFQA Submission Version

This folder contains the JFQA (Journal of Financial and Quantitative Analysis) formatted version.

## Status: REFRAMED & READY FOR COMPILATION

- **Main File**: `Regan_Xie_JFQA.tex`
- **Title Page**: `TitlePage.tex` (separate for blind review)
- **Target Journal**: [JFQA - Cambridge University Press](https://jfqa.org/submissions/)
- **GitHub Issue**: [#238 - JFQA Journal Submission Format Conversion](https://github.com/iAmGiG/gex-llm-patterns/issues/238)

## New Title

### The "Scar Tissue" of 0DTE: Identifying Structural Shifts in Dealer Inventory and Overnight Risk Premia

## Files

| File | Description |
|------|-------------|
| `Regan_Xie_JFQA.tex` | Main manuscript (blind - no author info) |
| `TitlePage.tex` | Author info, acknowledgments, declarations |
| `00_Header.tex` | JFQA packages, formatting, section numbering |
| `01-07_*.tex` | Content sections (converted citations, reframed language) |
| `references.bib` | Main bibliography |
| `statistical_references.bib` | Statistical references |

## Master Version

The master IEEE-formatted version is maintained in:

- `docs/papers/paper2/latex/` - **DO NOT MODIFY** for JFQA submission

## Completed Conversions

### Format Changes (All Complete)

- [x] Document class: `IEEEtran` → `article` (12pt)
- [x] Line spacing: Single → Double-spaced (`\doublespacing`)
- [x] Font: 10pt default → 12pt Times New Roman (`newtxtext`)
- [x] Margins: IEEE default → 1" all sides (`geometry`)
- [x] Section numbering: Arabic (1, 2, 3) → Roman (I, II, III)
- [x] Subsection numbering: Numbered → Letters (A, B, C)
- [x] Citations: `\cite{}` → `\citep{}` / `\citet{}` (natbib)
- [x] Bibliography style: IEEE numeric → `apalike` (author-year)
- [x] Figure/Table captions: Moved above content
- [x] `figure*` → `figure` (single-column format)

### Content Reframe (All Complete)

- [x] **New Title**: "The 'Scar Tissue' of 0DTE: Identifying Structural Shifts..."
- [x] **New Abstract**: ~140 words, finance-first framing emphasizing "scar tissue" mechanism and "great divergence"
- [x] **Model Name**: `o4-mini` → `o4-mini-2025-04-16` (4 instances fixed)
- [x] **Introduction**: Reframed to lead with 0DTE market structure, not LLM capabilities
- [x] **Discussion Subsections**:
  - "LLM Temporal Reasoning at 30-Day Scales" → "Temporal Persistence in Post-0DTE Markets"
  - "LLM Value Beyond Deterministic Thresholds" → "Continuous Quality Discrimination for Risk Management"
  - "Implications for LLM Financial Analysis" → "Implications for Market Microstructure"
- [x] **Conclusion**: Reframed opening and subsection titles
- [x] **Related Work**: Renamed "Obfuscation Testing" → "Temporal Robustness Protocols"

### Submission Requirements (Complete)

- [x] Two-file submission:
  - `Regan_Xie_JFQA.tex` - Blinded manuscript (no author identification)
  - `TitlePage.tex` - Title page (with author info + acknowledgments)

## Remaining Tasks

1. **Compile Test** - Run pdflatex to verify compilation
2. **Visual Review** - Check PDF output against JFQA requirements
3. **Final Proofread** - Review reframed sections for consistency

## Compilation

### VS Code Build Task (Windows - Local Only)

Press **Ctrl+Shift+B** to run the full build with citations.

Or run from command palette: "Tasks: Run Build Task"

**How it works:** The build task runs `build.bat` (Windows-specific, not committed to repo), which executes the full LaTeX → BibTeX → LaTeX × 2 sequence. This approach bypasses PowerShell conda activation and ensures all compilation steps run reliably.

**Note:** This setup is for local Windows development only. The HPCC Linux environment uses different LaTeX tools and build processes.

### Command Line (Alternative)

**Using build.bat (Windows):**

```bash
cd docs/papers/paper2/jfqa
./build.bat
```

**Manual sequence (cross-platform):**

```bash
cd docs/papers/paper2/jfqa
pdflatex Regan_Xie_JFQA.tex
bibtex Regan_Xie_JFQA
pdflatex Regan_Xie_JFQA.tex
pdflatex Regan_Xie_JFQA.tex
```

### VS Code LaTeX Workshop Setup

**Project Configuration** (`.vscode/settings.json` - applies to all users):

- Tool commands: `pdflatex` and `bibtex` (assumes they're in PATH)
- Recipe: `pdflatex → bibtex → pdflatex×2` for proper citation resolution
- `latex-workshop.latex.recipe.default: "first"` - use the bibtex recipe
- `latex-workshop.latex.build.forceRecipeUsage: true` - don't auto-detect recipes
- `latex-workshop.latex.tools.optional: []` - run all tools, don't skip bibtex
- `latex-workshop.latex.autoClean.run: "never"` - preserve aux files between steps

**Machine-Specific Setup** (optional - if MiKTeX not in PATH):

If you get "command not found" errors, override with full paths in User Settings (Ctrl+, → search "settings.json" → Edit in settings.json):

```json
{
    "latex-workshop.latex.tools": [
        {
            "name": "pdflatex",
            "command": "C:/Users/YOUR_USERNAME/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
            "args": ["-synctex=1", "-interaction=nonstopmode", "-file-line-error", "%DOC%"]
        },
        {
            "name": "bibtex",
            "command": "C:/Users/YOUR_USERNAME/AppData/Local/Programs/MiKTeX/miktex/bin/x64/bibtex.exe",
            "args": ["%DOCFILE%"]
        }
    ]
}
```

**Troubleshooting Citations Showing (??):**

If citations show as (??) in the PDF:

1. LaTeX Workshop may not be running the full recipe sequence
2. Run the manual build commands above to ensure bibtex processes the bibliography
3. Check that `.aux`, `.bbl`, and `.blg` files exist after compilation
4. The full sequence must run: pdflatex (creates .aux) → bibtex (creates .bbl from .bib) → pdflatex × 2 (resolves citations)

## Key Reframe Strategy

**Problem Addressed**: Paper read as "AI validation study" rather than "finance contribution"

**Solution**: Reversed hierarchy—now a **finance paper using structural reasoning framework**, not an AI paper testing financial data.

### Narrative Shifts Applied

| Previous (AI-centric) | New (Finance-centric) |
|----------------------|----------------------|
| "LLM Validation" | "Structural Identification" |
| "Obfuscation Testing" | "Temporal Robustness Protocol" |
| "Can LLMs detect regimes?" | "Did 0DTE create persistent regimes?" |
| Lead with LLM capabilities | Lead with market structure evolution |

## References

- [JFQA Submissions Page](https://jfqa.org/submissions/)
- [JFQA Style Guide](https://jfqa.org/submissions/style-guide-for-accepted-and-conditionally-accepted-papers/)

## Notes

- Content from Phase 5 language refinements (commit c9a95b4)
- JFQA recommends combining all .tex files into single manuscript (optional)
- Submission fee: $350 ($275 refunded if desk-rejected)
- Journal tier: Top 5 finance journal (<9% acceptance rate)
