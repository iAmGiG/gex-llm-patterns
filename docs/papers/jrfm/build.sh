#!/bin/bash
# Build JRFM paper (MDPI format)
# Usage: ./build.sh

set -e

# TeX Live path
export PATH="/mnt/bst/a100/yxie2/cregan1/texlive/2026/bin/x86_64-linux:$PATH"

MAIN="Regan_Xie_JRFM"

echo "=== Building $MAIN (JRFM / MDPI format) ==="

echo "[1/4] pdflatex (first pass)..."
pdflatex -interaction=nonstopmode "$MAIN.tex" > /dev/null 2>&1 || true

echo "[2/4] bibtex..."
bibtex "$MAIN" > /dev/null 2>&1 || true

echo "[3/4] pdflatex (second pass)..."
pdflatex -interaction=nonstopmode "$MAIN.tex" > /dev/null 2>&1 || true

echo "[4/4] pdflatex (final pass)..."
pdflatex -interaction=nonstopmode "$MAIN.tex" > /dev/null 2>&1 || true

# Check result
if [ -f "$MAIN.pdf" ]; then
    PAGES=$(pdfinfo "$MAIN.pdf" 2>/dev/null | grep Pages | awk '{print $2}')
    SIZE=$(du -h "$MAIN.pdf" | awk '{print $1}')
    echo "=== SUCCESS: $MAIN.pdf ($PAGES pages, $SIZE) ==="
else
    echo "=== FAILED: No PDF generated ==="
    echo "Check $MAIN.log for errors"
    exit 1
fi
