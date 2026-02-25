@echo off
cd /d "%~dp0"
pdflatex -interaction=nonstopmode Regan_Xie_AIAI.tex
bibtex Regan_Xie_AIAI
pdflatex -interaction=nonstopmode Regan_Xie_AIAI.tex
pdflatex -interaction=nonstopmode Regan_Xie_AIAI.tex
echo.
echo Build complete! Check for citation errors above.
