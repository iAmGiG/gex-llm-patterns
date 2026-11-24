#!/usr/bin/env bash
# Build the Electronics (MDPI) extension paper: docs/papers/electronics/latex/Regan_Xie_Electronics.pdf
#
# Usage: docs/papers/electronics/build.sh [--strict | --final | --overleaf | --clean | -h | --help]
#   (no option)  pdflatex, bibtex, pdflatex, pdflatex; print the page count, a warning summary and the count of unresolved
#                \tbd placeholders (in total and per source file, the main file included)
#   --strict     as above, then exit 1 unless the manuscript is submission-ready: no undefined references or
#                citations (article and supplement), no bibtex warnings, no missing figure files, no unresolved \tbd
#                placeholder in Regan_Xie_Electronics.tex, the part files or the supplement parts (commented-out text does
#                not count), no "Working title" left in \Title, no reference that still changed in the last pass, and the
#                hand-typed numbers that the article and the supplement use for each other match the .aux files.
#                Open TODO(authors) markers are counted and reported, not failed.
#   --final      --strict, and exit 1 while any TODO(authors) marker (CRediT, Zenodo DOI) remains in the sources
#   --overleaf   build, then write overleaf/Regan_Xie_Electronics_overleaf.zip: a self-contained project (one .tex per part,
#                Definitions/, figures/) that is compiled in a clean folder without the JRFM search paths before it is zipped
#   --clean      remove the LaTeX build files (the PDFs are kept) and exit
#
# The summary line also counts the open "% TODO(" markers (the guidance comments of the skeleton) and the TODO(authors)
# markers; --strict and --overleaf report them but do not fail on them, --final does fail on TODO(authors).
# TeX Live lives in the shared install below; set TEXLIVE_BIN to use another one.
# mdpi.cls hard-codes Definitions/journalnames.tex, Definitions/mdpi.bst and the logos relative to the working
# directory, so the JRFM copy of Definitions/ is reached through the TeX search paths exported below (the trailing
# ':' keeps the default TeX Live paths).  The Overleaf package carries its own copy of Definitions/ and figures/;
# nothing in the sources changes (the main file finds figures/ when it exists).
# The same search path reaches the JRFM section files, which have the same names as ours: the main file inputs
# ./NN_Name, and this script refuses to build when a local file is missing.
set -euo pipefail

MAIN="Regan_Xie_Electronics"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Section files input by the main file, in order.
SECTIONS=(01_Introduction 02_Related_Work 03_Methods
  04_01_Inputs 04_02_Replay 04_03_Bridge 04_04_Complete 04_05_Scope 04_06_Fidelity 04_07_Dated
  05_Discussion 06_Conclusion 07_Appendix_A_Data)
SUPPLEMENT="Regan_Xie_Electronics_Supplement"
SUPPLEMENT_PARTS=(S1_Series_SQL S2_Run_Ledger S3_Cross_Asset S4_Intraday S5_Fidelity S6_Prompt S7_Tables S8_Detail)

die() { echo "$*" >&2; exit 1; }
usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"; }

STRICT=0
OVERLEAF=0
FINAL=0
case "${1:-}" in
  "") ;;
  --strict) STRICT=1 ;;
  --final) STRICT=1; FINAL=1 ;;
  --overleaf) STRICT=1; OVERLEAF=1 ;;
  --clean) cd "$HERE/latex"; rm -f "$MAIN".{aux,bbl,blg,log,out,toc,fls} "$SUPPLEMENT".{aux,log,out} build_*.log; echo "cleaned"; exit 0 ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; die "unknown option: $1" ;;
esac

export PATH="${TEXLIVE_BIN:-/mnt/bst/a100/yxie2/cregan1/texlive/2026/bin/x86_64-linux}:$PATH"
command -v pdflatex >/dev/null && command -v bibtex >/dev/null || die "pdflatex/bibtex not found (set TEXLIVE_BIN)"
[ -f "$HERE/../jrfm/Definitions/mdpi.cls" ] || die "missing $HERE/../jrfm/Definitions/mdpi.cls"
# TEXINPUTS below also searches ../../jrfm: without this guard a missing local file would be replaced by the JRFM file of the same name.
SOURCES=("$MAIN.tex")
for f in "${SECTIONS[@]}"; do SOURCES+=("$f.tex"); done
for f in "${SOURCES[@]}" references.bib "$SUPPLEMENT.tex" "${SUPPLEMENT_PARTS[@]/%/.tex}"; do
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
echo "[supplement] pdflatex, twice"
for pass in 1 2; do
  pdflatex -interaction=nonstopmode -halt-on-error -file-line-error "$SUPPLEMENT.tex" >build_supplement.log 2>&1 \
    || { tail -25 build_supplement.log; die "FAILED: pdflatex (build_supplement.log)"; }
done

# pdfinfo (poppler) is not installed on this host: read the page count from the TeX log instead.
count() { grep -c -E "$1" "$2" || true; }   # grep -c prints 0 but exits 1 when nothing matches
ALL_SOURCES=("${SOURCES[@]}" "$SUPPLEMENT.tex" "${SUPPLEMENT_PARTS[@]/%/.tex}")   # the article, its parts and the supplement
live() { cat "${ALL_SOURCES[@]}" | sed -E 's/(^|[^\\])%.*$/\1/'; }   # the sources without comments (an unescaped % starts one)
PAGES=$(sed -n 's/^Output written on .* (\([0-9]*\) pages.*/\1/p' "$MAIN.log" | tail -1)
UNDEF=$(count '(LaTeX|natbib) Warning: (Reference|Citation).*undefined' "$MAIN.log")
SUP_UNDEF=$(count '(LaTeX|natbib) Warning: (Reference|Citation).*undefined' "$SUPPLEMENT.log")
SUP_PAGES=$(sed -n 's/^Output written on .* (\([0-9]*\) pages.*/\1/p' "$SUPPLEMENT.log" | tail -1)
# The supplement names sections and tables of the article by number (it compiles on its own), and the article names sections,
# tables and figures of the supplement by number: both must match the .aux files.
number_of() { sed -n "s/.*newlabel{$1}{{\([^}]*\)}.*/\1/p" "$MAIN.aux" | head -1; }
sup_number_of() { sed -n "s/.*newlabel{$1}{{\([^}]*\)}.*/\1/p" "$SUPPLEMENT.aux" | head -1; }
SUP_STALE=""
# the supplement names these article labels by number
for pair in "sec:methods:criteria=3.1" "sec:methods:series=3.2" "sec:methods:lineage=3.3" "sec:methods:windows=3.4" "sec:methods:arms=3.6" "sec:methods:storage=3.7" "sec:methods:statistics=3.8" "sec:results=4" "sec:results:inputs=4.1" "sec:results:replay=4.2" "sec:results:scope=4.5" "sec:results:fidelity=4.6" "app:data=A" "tab:series=1" "tab:arms=2" "fig:fidelity=6"; do
  [ "$(number_of "${pair%%=*}")" = "${pair##*=}" ] || SUP_STALE="$SUP_STALE ${pair%%=*}(is $(number_of "${pair%%=*}"), supplement says ${pair##*=})"
done
# the article names these supplement labels by number
for pair in "sup:series=S1" "sup:ledger=S2" "sup:cross=S3" "sup:intraday=S4" "sup:fidelity=S5" "sup:prompt=S6" "sup:tables=S7" "sup:detail=S8" "app:prompt:body=S6.2" "app:prompt:schema=S6.3" "tab:ledger=S1" "tab:ledger2=S2" "tab:cross=S3" "tab:s:llm=S4" "tab:intraday=S5" "tab:fidelity=S6" "tab:app:series=S7" "tab:app:replay=S8" "tab:complete=S9" "tab:ablation=S10" "tab:post=S11" "fig:cross=S1" "fig:intraday=S2" "fig:window=S3" "fig:post=S4" "fig:replay=S5" "fig:deep=S6" "tab:windows=S12"; do
  [ "$(sup_number_of "${pair%%=*}")" = "${pair##*=}" ] || SUP_STALE="$SUP_STALE ${pair%%=*}(is $(sup_number_of "${pair%%=*}"), article says ${pair##*=})"
done
RERUN=$(count 'Rerun to get|Label\(s\) may have changed' "$MAIN.log")
BIBWARN=$(count '^Warning' build_2_bibtex.log)
MISSING=$(( $(count '^Missing figure file' "$MAIN.log") + $(count '^Missing figure file' "$SUPPLEMENT.log") ))
OVERFULL=$(count '^Overfull' "$MAIN.log")
SUP_OVERFULL=$(count '^Overfull' "$SUPPLEMENT.log")
# The counts below must survive "no match" under pipefail: every grep that may find nothing sits in a { ...; } || true group.
tbd_in() { { sed -E 's/(^|[^\\])%.*$/\1/' "$1" | grep -v 'DeclareRobustCommand' | grep -o '\\tbd' || true; } | wc -l; }
TBD=$({ live | grep -v 'DeclareRobustCommand' | grep -o '\\tbd' || true; } | wc -l)   # the macro definition is not a placeholder
MAIN_TBD=$(tbd_in "$MAIN.tex")   # abstract and data availability: the placeholders the authors fill last
TBD_BY_FILE=""; for f in "${ALL_SOURCES[@]}"; do TBD_BY_FILE="$TBD_BY_FILE ${f%.tex} $(tbd_in "$f"),"; done
TITLE_OPEN=$({ live | grep -c 'Working title' || true; })
TODO=$({ cat "${ALL_SOURCES[@]}" | grep -o 'TODO(' || true; } | wc -l)
TODO_AUTHORS=$({ cat "${ALL_SOURCES[@]}" | grep -o 'TODO(authors)' || true; } | wc -l)

echo "=== SUCCESS: latex/$MAIN.pdf (${PAGES:-?} pages) ==="
echo "undefined references/citations: $UNDEF   bibtex warnings: $BIBWARN   missing figures: $MISSING   unresolved \\tbd: $TBD (main file: $MAIN_TBD)   working title left: $TITLE_OPEN   open TODO markers: $TODO   overfull boxes: $OVERFULL"
echo "unresolved \\tbd by file:${TBD_BY_FILE%,}"
echo "supplement: latex/$SUPPLEMENT.pdf (${SUP_PAGES:-?} pages), undefined references: $SUP_UNDEF, overfull boxes: $SUP_OVERFULL   TODO(authors) markers: $TODO_AUTHORS"

if [ "$STRICT" -eq 1 ]; then
  WHY=""
  [ "$UNDEF" -eq 0 ]      || WHY="$WHY; $UNDEF undefined reference(s) or citation(s)"
  [ "$SUP_UNDEF" -eq 0 ]  || WHY="$WHY; $SUP_UNDEF undefined reference(s) in the supplement"
  [ -z "$SUP_STALE" ]     || WHY="$WHY; hand-typed numbers between article and supplement are stale:$SUP_STALE"
  [ "$RERUN" -eq 0 ]      || WHY="$WHY; references still changed in the last pass"
  [ "$BIBWARN" -eq 0 ]    || WHY="$WHY; $BIBWARN bibtex warning(s)"
  [ "$MISSING" -eq 0 ]    || WHY="$WHY; $MISSING missing figure file(s)"
  [ "$TBD" -eq 0 ]        || WHY="$WHY; $TBD unresolved \\tbd"
  [ "$TITLE_OPEN" -eq 0 ] || WHY="$WHY; the working title is still in \\Title"
  [ -z "$WHY" ] || die "STRICT: not submission-ready:${WHY#;} (details in $MAIN.log and build_2_bibtex.log)"
  [ "$TODO" -eq 0 ] || echo "STRICT: note: $TODO open TODO marker(s) remain in the sources, $TODO_AUTHORS of them TODO(authors)"
  if [ "$FINAL" -eq 1 ] && [ "$TODO_AUTHORS" -gt 0 ]; then
    die "FINAL: not ready to submit: $TODO_AUTHORS TODO(authors) marker(s) remain (CRediT roles, Zenodo DOI; grep -n 'TODO(authors)' latex/*.tex)"
  fi
  echo "STRICT: ok"
  [ "$FINAL" -eq 0 ] || echo "FINAL: ok"
fi

if [ "$OVERLEAF" -eq 1 ]; then
  command -v zip >/dev/null || die "zip not found"
  STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
  OUT="$HERE/overleaf"; ZIP="$OUT/${MAIN}_overleaf.zip"; mkdir -p "$OUT" "$STAGE/figures"
  cp "${SOURCES[@]}" "$SUPPLEMENT.tex" "${SUPPLEMENT_PARTS[@]/%/.tex}" references.bib "$STAGE/"
  cp -r "$HERE/../jrfm/Definitions" "$STAGE/Definitions"
  find "$STAGE/Definitions" -name '.DS_Store' -delete
  cp "$HERE"/figures/output/fig*.png "$STAGE/figures/"
  cat >"$STAGE/README_overleaf.md" <<'NOTE'
# Overleaf project: Electronics manuscript

- Main document: Regan_Xie_Electronics.tex. Compiler: pdfLaTeX.
- The supplement compiles on its own: set Regan_Xie_Electronics_Supplement.tex as main document.
- To render one part, comment out the other input lines in the main file. Results has one file per subsection.
- Open author decisions are marked with TODO(authors) in the sources. The src comments name the result file behind each number.
NOTE
  echo "=== Overleaf package: compiling in a clean folder, without the JRFM search paths ==="
  (
    cd "$STAGE"; unset TEXINPUTS BSTINPUTS
    for step in 1 bib 2 3; do
      if [ "$step" = bib ]; then bibtex "$MAIN" >/dev/null 2>&1 || [ $? -le 1 ]
      else pdflatex -interaction=nonstopmode -halt-on-error "$MAIN.tex" >/dev/null 2>&1; fi
    done
    pdflatex -interaction=nonstopmode -halt-on-error "$SUPPLEMENT.tex" >/dev/null 2>&1
    pdflatex -interaction=nonstopmode -halt-on-error "$SUPPLEMENT.tex" >/dev/null 2>&1
    STAGE_UNDEF=$(grep -c -E '(LaTeX|natbib) Warning: (Reference|Citation).*undefined' "$MAIN.log" || true)
    STAGE_MISSING=$(cat "$MAIN.log" "$SUPPLEMENT.log" | grep -c '^Missing figure file' || true)
    [ "$STAGE_UNDEF" -eq 0 ] && [ "$STAGE_MISSING" -eq 0 ] || { echo "package check failed: $STAGE_UNDEF undefined, $STAGE_MISSING missing figures" >&2; exit 1; }
    rm -f ./*.aux ./*.bbl ./*.blg ./*.log ./*.out ./*.toc ./*.fls ./*.pdf
    rm -f "$ZIP"; zip -qr "$ZIP" .
  ) || die "FAILED: Overleaf package"
  echo "=== $ZIP ($(du -h "$ZIP" | cut -f1), $(unzip -l "$ZIP" | tail -1 | awk '{print $2}') files) ==="
fi
