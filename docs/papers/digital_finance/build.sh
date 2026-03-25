#!/bin/bash
# Build script for Digital Finance (Springer svjour3) paper
# Usage: ./build.sh

set -e

MAIN="Regan_Xie_DigitalFinance"

echo "=== Building $MAIN ==="

echo "[1/4] First pdflatex pass..."
pdflatex -interaction=nonstopmode "$MAIN.tex" > /dev/null 2>&1 || pdflatex -interaction=nonstopmode "$MAIN.tex"

echo "[2/4] BibTeX pass..."
bibtex "$MAIN" || true

echo "[3/4] Second pdflatex pass..."
pdflatex -interaction=nonstopmode "$MAIN.tex" > /dev/null 2>&1

echo "[4/4] Third pdflatex pass..."
pdflatex -interaction=nonstopmode "$MAIN.tex" > /dev/null 2>&1

echo ""
echo "=== Build complete: $MAIN.pdf ==="

# Word count estimate (rough)
if command -v texcount &> /dev/null; then
    echo ""
    echo "=== Word count ==="
    texcount -inc -total "$MAIN.tex" 2>/dev/null | grep -E "Words in text|Words outside"
fi

ls -lh "$MAIN.pdf"
