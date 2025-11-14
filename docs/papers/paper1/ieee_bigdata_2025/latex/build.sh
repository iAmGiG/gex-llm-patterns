#!/bin/bash
# ========================================
# Paper #1 LaTeX Build Script (Cross-platform)
# ========================================

echo ""
echo "========================================"
echo "  Building Paper #1 LaTeX Document"
echo "========================================"
echo ""

# Check if pdflatex exists
if ! command -v pdflatex &> /dev/null; then
    echo "ERROR: pdflatex not found in PATH"
    echo ""
    echo "Please install a LaTeX distribution:"
    echo "  - Linux: sudo apt-get install texlive-full"
    echo "  - macOS: brew install --cask mactex"
    echo "  - Windows: Install MiKTeX from https://miktex.org/download"
    echo ""
    exit 1
fi

echo "[1/4] First pdflatex pass..."
pdflatex -interaction=nonstopmode Main.tex > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: First pdflatex pass failed"
    echo "Run 'pdflatex Main.tex' without redirection to see errors"
    exit 1
fi
echo "      DONE"

echo "[2/4] Running bibtex..."
bibtex Main > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "WARNING: BibTeX reported issues (this may be normal)"
fi
echo "      DONE"

echo "[3/4] Second pdflatex pass..."
pdflatex -interaction=nonstopmode Main.tex > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Second pdflatex pass failed"
    exit 1
fi
echo "      DONE"

echo "[4/4] Final pdflatex pass..."
pdflatex -interaction=nonstopmode Main.tex > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Final pdflatex pass failed"
    exit 1
fi
echo "      DONE"

echo ""
echo "========================================"
echo "  Compilation Complete!"
echo "========================================"

if [ -f Main.pdf ]; then
    echo ""
    echo "Output: Main.pdf"

    # Get file size (cross-platform)
    if command -v stat &> /dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            SIZE=$(stat -f%z Main.pdf)
        else
            # Linux
            SIZE=$(stat -c%s Main.pdf)
        fi
        SIZE_MB=$((SIZE / 1048576))
        echo "Size: ${SIZE_MB} MB"
    fi

    # Count pages (if pdfinfo available)
    if command -v pdfinfo &> /dev/null; then
        PAGES=$(pdfinfo Main.pdf | grep "Pages:" | awk '{print $2}')
        echo "Pages: ${PAGES}"
    fi

    echo ""
    echo "Build complete!"
else
    echo ""
    echo "WARNING: Main.pdf was not created"
    echo "Check Main.log for errors"
    exit 1
fi