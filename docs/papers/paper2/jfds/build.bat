@echo off
cd /d "%~dp0"
pdflatex -interaction=nonstopmode Regan_Xie_JFDS.tex
bibtex Regan_Xie_JFDS
pdflatex -interaction=nonstopmode Regan_Xie_JFDS.tex
pdflatex -interaction=nonstopmode Regan_Xie_JFDS.tex
echo.
echo Build complete! Check for citation errors above.
