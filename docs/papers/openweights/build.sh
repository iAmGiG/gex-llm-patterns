#!/usr/bin/env bash
# Build the open-weights paper (Paper B, MDPI class): docs/papers/openweights/latex/Regan_Xie_OpenWeights.pdf
#
# Usage: docs/papers/openweights/build.sh [--strict | --final | --overleaf | --clean | -h | --help]
#   (no option)  pdflatex, bibtex, pdflatex, pdflatex; print the page count (target 12-15), a warning summary and the counts of
#                \tbd and \pending placeholders (in total and per source file, the main file included)
#   --strict     as above, then exit 1 unless the manuscript compiles cleanly: no undefined references or citations, no bibtex
#                warnings, no missing figure files, no \tbd, no "Working title" left in \Title, no reference that still changed in
#                the last pass, and a supplement whose table numbers match the ones the article cites.  A \pending marker (a result
#                of a run that is still being made) is reported but does not fail --strict.
#   --final      --strict, then exit 1 while a \pending marker or a TODO(authors) or TODO(runs) comment remains in the sources
#   --overleaf   --strict, then write overleaf/Regan_Xie_OpenWeights_overleaf.zip: a self-contained project (one .tex per part,
#                Definitions/, figures/) that is compiled in a clean folder without the JRFM search paths before it is zipped
#   --clean      remove the LaTeX build files (the PDFs are kept) and exit
#
# TeX Live lives in the shared install below; set TEXLIVE_BIN to use another one.
# mdpi.cls hard-codes Definitions/journalnames.tex, Definitions/mdpi.bst and the logos relative to the working directory, so the JRFM
# copy of Definitions/ is reached through the TeX search paths exported below (the trailing ':' keeps the default TeX Live paths).
# The same search path reaches the JRFM section files, which have the same names as ours: the main file inputs ./NN_Name, and this
# script refuses to build when a local file is missing.
set -euo pipefail

MAIN="Regan_Xie_OpenWeights"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Part files input by the main file, in order.
SECTIONS=(01_Introduction 02_Related_Work 03_Methods
  04_01_Overview 04_02_Oss 04_03_Llama 04_04_Qwen 04_05_Departures 04_06_Order 04_07_Repeat 04_08_Cost
  05_Discussion 06_Conclusion 07_Appendix_A_Schema)
SUPPLEMENT="Regan_Xie_OpenWeights_Supplement"
SUPPLEMENT_PARTS=(S1_Run_Ledger S2_Detail S3_Engine)

die() { echo "$*" >&2; exit 1; }
usage() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"; }

STRICT=0
FINAL=0
OVERLEAF=0
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

echo "=== Building $MAIN (MDPI) ==="
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
live() { cat "${SOURCES[@]}" | sed -E 's/(^|[^\\])%.*$/\1/'; }   # the sources without comments (an unescaped % starts one)
PAGES=$(sed -n 's/^Output written on .* (\([0-9]*\) pages.*/\1/p' "$MAIN.log" | tail -1)
UNDEF=$(count '(LaTeX|natbib) Warning: (Reference|Citation).*undefined' "$MAIN.log")
SUP_UNDEF=$(count '(LaTeX|natbib) Warning: (Reference|Citation).*undefined' "$SUPPLEMENT.log")
SUP_PAGES=$(sed -n 's/^Output written on .* (\([0-9]*\) pages.*/\1/p' "$SUPPLEMENT.log" | tail -1)
# The article cites the supplement tables by number and the supplement cites two article numbers: they must match.
number_of() { sed -n "s/.*newlabel{$2}{{\([^}]*\)}.*/\1/p" "$1" | head -1; }
STALE=""
for pair in "tab:s:led:oss=S1" "tab:s:led:llama=S2" "tab:s:led:qwen=S3" "tab:s:oss=S4" "tab:s:llama=S5" "tab:s:qwen=S6" "tab:s:engine=S7"; do
  [ "$(number_of "$SUPPLEMENT.aux" "${pair%%=*}")" = "${pair##*=}" ] || STALE="$STALE ${pair%%=*}(is $(number_of "$SUPPLEMENT.aux" "${pair%%=*}"), the article says ${pair##*=})"
done
for pair in "tab:results=2" "sec:methods=3"; do
  [ "$(number_of "$MAIN.aux" "${pair%%=*}")" = "${pair##*=}" ] || STALE="$STALE ${pair%%=*}(is $(number_of "$MAIN.aux" "${pair%%=*}"), the supplement says ${pair##*=})"
done
RERUN=$(count 'Rerun to get|Label\(s\) may have changed' "$MAIN.log")
BIBWARN=$(count '^Warning' build_2_bibtex.log)
MISSING=$(count '^Missing figure file' "$MAIN.log")
OVERFULL=$(count '^Overfull' "$MAIN.log")
SUP_OVERFULL=$(count '^Overfull' "$SUPPLEMENT.log")
# The counts below must survive "no match" under pipefail: every grep that may find nothing sits in a { ...; } || true group.
mark_in() {  # $1 = macro, $2 = file: occurrences in the text without comments, the macro definition excluded
  { sed -E 's/(^|[^\\])%.*$/\1/' "$2" | grep -v 'DeclareRobustCommand' | grep -o "\\\\$1" || true; } | wc -l
}
ALLSRC=("${SOURCES[@]}" "$SUPPLEMENT.tex" "${SUPPLEMENT_PARTS[@]/%/.tex}")   # article and supplement
TBD=0; PENDING=0; TBD_BY_FILE=""; PENDING_BY_FILE=""
for f in "${ALLSRC[@]}"; do
  t=$(mark_in tbd "$f"); p=$(mark_in pending "$f")
  TBD=$((TBD + t)); PENDING=$((PENDING + p))
  TBD_BY_FILE="$TBD_BY_FILE ${f%.tex} $t,"; PENDING_BY_FILE="$PENDING_BY_FILE ${f%.tex} $p,"
done
TITLE_OPEN=$({ live | grep -c 'Working title' || true; })
TODO_AUTHORS_SRC=$({ cat "${ALLSRC[@]}" | grep -o 'TODO(authors)' || true; } | wc -l)
TODO_RUNS_SRC=$({ cat "${ALLSRC[@]}" | grep -o 'TODO(runs)' || true; } | wc -l)

echo "=== SUCCESS: latex/$MAIN.pdf (${PAGES:-?} pages; target 12-15) ==="
echo "undefined references/citations: $UNDEF   bibtex warnings: $BIBWARN   missing figures: $MISSING   unresolved \\tbd: $TBD   \\pending: $PENDING   working title left: $TITLE_OPEN   overfull boxes: $OVERFULL"
echo "open markers in the sources: TODO(authors) $TODO_AUTHORS_SRC, TODO(runs) $TODO_RUNS_SRC"
echo "\\pending by file:${PENDING_BY_FILE%,}"
echo "supplement: latex/$SUPPLEMENT.pdf (${SUP_PAGES:-?} pages), undefined references: $SUP_UNDEF   overfull boxes: $SUP_OVERFULL"

if [ "$STRICT" -eq 1 ]; then
  WHY=""
  [ "$UNDEF" -eq 0 ]      || WHY="$WHY; $UNDEF undefined reference(s) or citation(s)"
  [ "$SUP_UNDEF" -eq 0 ]  || WHY="$WHY; $SUP_UNDEF undefined reference(s) in the supplement"
  [ -z "$STALE" ]         || WHY="$WHY; table or section numbers differ between the article and the supplement:$STALE"
  [ "$RERUN" -eq 0 ]      || WHY="$WHY; references still changed in the last pass"
  [ "$BIBWARN" -eq 0 ]    || WHY="$WHY; $BIBWARN bibtex warning(s)"
  [ "$MISSING" -eq 0 ]    || WHY="$WHY; $MISSING missing figure file(s)"
  [ "$TBD" -eq 0 ]        || WHY="$WHY; $TBD unresolved \\tbd (by file:${TBD_BY_FILE%,})"
  [ "$TITLE_OPEN" -eq 0 ] || WHY="$WHY; the working title is still in \\Title"
  if [ "$FINAL" -eq 1 ]; then
    [ "$PENDING" -eq 0 ]        || WHY="$WHY; $PENDING \\pending marker(s) (by file:${PENDING_BY_FILE%,})"
    [ "$TODO_AUTHORS_SRC" -eq 0 ] || WHY="$WHY; $TODO_AUTHORS_SRC TODO(authors) comment(s) in the sources"
    [ "$TODO_RUNS_SRC" -eq 0 ]    || WHY="$WHY; $TODO_RUNS_SRC TODO(runs) comment(s) in the sources"
  fi
  [ -z "$WHY" ] || die "STRICT: not clean:${WHY#;} (details in $MAIN.log and build_2_bibtex.log)"
  if [ "$FINAL" -eq 1 ]; then echo "FINAL: ok"; else echo "STRICT: ok"; fi
  [ "$PENDING" -eq 0 ] || echo "STRICT: note: $PENDING \\pending marker(s) remain (the Zenodo DOI)"
fi

if [ "$OVERLEAF" -eq 1 ]; then
  command -v zip >/dev/null || die "zip not found"
  STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
  OUT="$HERE/overleaf"; ZIP="$OUT/${MAIN}_overleaf.zip"; mkdir -p "$OUT" "$STAGE/figures"
  cp "${SOURCES[@]}" "$SUPPLEMENT.tex" "${SUPPLEMENT_PARTS[@]/%/.tex}" references.bib "$STAGE/"
  cp -r "$HERE/../jrfm/Definitions" "$STAGE/Definitions"
  find "$STAGE/Definitions" -name '.DS_Store' -delete
  cp "$HERE"/figures/output/bf*.png "$STAGE/figures/"
  cat >"$STAGE/README_overleaf.md" <<'NOTE'
# Overleaf project: open-weights manuscript

- Main document: Regan_Xie_OpenWeights.tex. Compiler: pdfLaTeX.
- The supplement compiles on its own: set Regan_Xie_OpenWeights_Supplement.tex as main document.
- To render one part, comment out the other input lines in the main file. Results has one file per subsection.
- Open author decisions are marked with TODO(authors), results of runs that are still being made with \pending{...} and TODO(runs).
  The src comments name the file behind each number.
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
    STAGE_MISSING=$(grep -c '^Missing figure file' "$MAIN.log" || true)
    [ "$STAGE_UNDEF" -eq 0 ] && [ "$STAGE_MISSING" -eq 0 ] || { echo "package check failed: $STAGE_UNDEF undefined, $STAGE_MISSING missing figures" >&2; exit 1; }
    rm -f ./*.aux ./*.bbl ./*.blg ./*.log ./*.out ./*.toc ./*.fls ./*.pdf
    rm -f "$ZIP"; zip -qr "$ZIP" .
  ) || die "FAILED: Overleaf package"
  echo "=== $ZIP ($(du -h "$ZIP" | cut -f1), $(unzip -l "$ZIP" | tail -1 | awk '{print $2}') files) ==="
fi
