#!/usr/bin/env bash
# Build the Electronics (MDPI) extension paper: docs/papers/electronics/latex/Regan_Xie_Electronics.pdf
#
# Usage: docs/papers/electronics/build.sh [--strict | --clean | -h | --help]
#   (no option)  pdflatex, bibtex, pdflatex, pdflatex; print the page count, a warning summary and the count of unresolved
#                \tbd placeholders (in total and per source file, the main file included)
#   --strict     as above, then exit 1 unless the manuscript is submission-ready: no undefined references or
#                citations, no bibtex warnings, no missing figure files, no unresolved \tbd placeholder in
#                Regan_Xie_Electronics.tex or 01-07 (commented-out text does not count), no "Working title" left in
#                \Title and no reference that still changed in the last pass
#   --clean      remove the LaTeX build files (the PDF is kept) and exit
#
# The summary line also counts the open "% TODO(" markers (the guidance comments of the skeleton); --strict reports
# them but does not fail on them.
# TeX Live lives in the shared install below; set TEXLIVE_BIN to use another one.
# mdpi.cls hard-codes Definitions/journalnames.tex, Definitions/mdpi.bst and the logos relative to the working
# directory, so the JRFM copy of Definitions/ is reached through the TeX search paths exported below (the trailing
# ':' keeps the default TeX Live paths).  For Overleaf or the MDPI submission zip copy Definitions/ next to the
# .tex file instead; nothing in the sources changes.
# The same search path reaches the JRFM section files, which have the same names as ours: the main file inputs
# ./NN_Name, and this script refuses to build when a local file is missing.
set -euo pipefail

MAIN="Regan_Xie_Electronics"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Section files input by the main file, in order.
SECTIONS=(01_Introduction 02_Related_Work 03_Methods 04_Results 05_Discussion 06_Conclusion 07_Appendix)

die() { echo "$*" >&2; exit 1; }
usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"; }

STRICT=0
case "${1:-}" in
  "") ;;
  --strict) STRICT=1 ;;
  --clean) cd "$HERE/latex"; rm -f "$MAIN".{aux,bbl,blg,log,out,toc,fls} build_*.log; echo "cleaned"; exit 0 ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; die "unknown option: $1" ;;
esac

export PATH="${TEXLIVE_BIN:-/mnt/bst/a100/yxie2/cregan1/texlive/2026/bin/x86_64-linux}:$PATH"
command -v pdflatex >/dev/null && command -v bibtex >/dev/null || die "pdflatex/bibtex not found (set TEXLIVE_BIN)"
[ -f "$HERE/../jrfm/Definitions/mdpi.cls" ] || die "missing $HERE/../jrfm/Definitions/mdpi.cls"
# TEXINPUTS below also searches ../../jrfm: without this guard a missing local file would be replaced by the JRFM file of the same name.
SOURCES=("$MAIN.tex")
for f in "${SECTIONS[@]}"; do SOURCES+=("$f.tex"); done
for f in "${SOURCES[@]}" references.bib; do
  [ -f "$HERE/latex/$f" ] || die "missing latex/$f (refusing to fall back to a file of the same name in ../jrfm)"
done
export TEXINPUTS=".:../../jrfm:"
export BSTINPUTS=".:../../jrfm:"
cd "$HERE/latex"

latex_pass() {  # $1 = step label, $2 = log file
  echo "[$1] pdflatex"
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$MAIN.tex" >"$2" 2>&1 \
    || { tail -25 "$2"; die "FAILED: pdflatex ($2)"; }
}

echo "=== Building $MAIN (MDPI Electronics) ==="
latex_pass "1/4" build_1_pdflatex.log
echo "[2/4] bibtex"
rc=0; bibtex "$MAIN" >build_2_bibtex.log 2>&1 || rc=$?   # exit 1 = warnings only, >= 2 = errors
[ "$rc" -le 1 ] || { tail -15 build_2_bibtex.log; die "FAILED: bibtex (build_2_bibtex.log)"; }
latex_pass "3/4" build_3_pdflatex.log
latex_pass "4/4" build_4_pdflatex.log

# pdfinfo (poppler) is not installed on this host: read the page count from the TeX log instead.
count() { grep -c -E "$1" "$2" || true; }   # grep -c prints 0 but exits 1 when nothing matches
live() { cat "${SOURCES[@]}" | sed -E 's/(^|[^\\])%.*$/\1/'; }   # the sources without comments (an unescaped % starts one)
PAGES=$(sed -n 's/^Output written on .* (\([0-9]*\) pages.*/\1/p' "$MAIN.log" | tail -1)
UNDEF=$(count '(LaTeX|natbib) Warning: (Reference|Citation).*undefined' "$MAIN.log")
RERUN=$(count 'Rerun to get|Label\(s\) may have changed' "$MAIN.log")
BIBWARN=$(count '^Warning' build_2_bibtex.log)
MISSING=$(count '^Missing figure file' "$MAIN.log")
OVERFULL=$(count '^Overfull' "$MAIN.log")
# The counts below must survive "no match" under pipefail: every grep that may find nothing sits in a { ...; } || true group.
tbd_in() { { sed -E 's/(^|[^\\])%.*$/\1/' "$1" | grep -v 'DeclareRobustCommand' | grep -o '\\tbd' || true; } | wc -l; }
TBD=$({ live | grep -v 'DeclareRobustCommand' | grep -o '\\tbd' || true; } | wc -l)   # the macro definition is not a placeholder
MAIN_TBD=$(tbd_in "$MAIN.tex")   # abstract and data availability: the placeholders the authors fill last
TBD_BY_FILE=""; for f in "${SOURCES[@]}"; do TBD_BY_FILE="$TBD_BY_FILE ${f%.tex} $(tbd_in "$f"),"; done
TITLE_OPEN=$({ live | grep -c 'Working title' || true; })
TODO=$({ cat "${SOURCES[@]}" | grep -o 'TODO(' || true; } | wc -l)

echo "=== SUCCESS: latex/$MAIN.pdf (${PAGES:-?} pages) ==="
echo "undefined references/citations: $UNDEF   bibtex warnings: $BIBWARN   missing figures: $MISSING   unresolved \\tbd: $TBD (main file: $MAIN_TBD)   working title left: $TITLE_OPEN   open TODO markers: $TODO   overfull boxes: $OVERFULL"
echo "unresolved \\tbd by file:${TBD_BY_FILE%,}"

if [ "$STRICT" -eq 1 ]; then
  WHY=""
  [ "$UNDEF" -eq 0 ]      || WHY="$WHY; $UNDEF undefined reference(s) or citation(s)"
  [ "$RERUN" -eq 0 ]      || WHY="$WHY; references still changed in the last pass"
  [ "$BIBWARN" -eq 0 ]    || WHY="$WHY; $BIBWARN bibtex warning(s)"
  [ "$MISSING" -eq 0 ]    || WHY="$WHY; $MISSING missing figure file(s)"
  [ "$TBD" -eq 0 ]        || WHY="$WHY; $TBD unresolved \\tbd"
  [ "$TITLE_OPEN" -eq 0 ] || WHY="$WHY; the working title is still in \\Title"
  [ -z "$WHY" ] || die "STRICT: not submission-ready:${WHY#;} (details in $MAIN.log and build_2_bibtex.log)"
  [ "$TODO" -eq 0 ] || echo "STRICT: note: $TODO open TODO marker(s) remain in the sources"
  echo "STRICT: ok"
fi
