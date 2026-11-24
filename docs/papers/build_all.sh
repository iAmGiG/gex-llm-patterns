#!/usr/bin/env bash
# Build both Electronics papers with one command and print one summary line per paper.
#
# Usage: docs/papers/build_all.sh [--strict | --final | --overleaf | --clean | -h | --help]
#   (no option)  --strict on both papers
#   --strict     docs/papers/electronics/build.sh --strict, then docs/papers/openweights/build.sh --strict
#   --final      the same with --final (fails while a TODO(authors) or TODO(runs) marker or a \pending placeholder remains)
#   --overleaf   the same with --overleaf (also writes the two Overleaf zips under each paper's overleaf/ folder)
#   --clean      removes the LaTeX build files of both papers and exits
#
# Both builds always run, even when the first fails. The summary has one line per paper: pages (article + supplement), the
# STRICT/FINAL result and the number of open TODO markers in the .tex sources (TODO(authors) and TODO(runs)).
# Exit status: 0 when both builds pass, 1 otherwise. The full output of each build is in build_all_<paper>.log in the
# paper's latex/ folder (the *.log pattern of .gitignore keeps it out of the repository).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLAG="${1:---strict}"
case "$FLAG" in
  --strict|--final|--overleaf|--clean) ;;
  -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"; exit 0 ;;
  *) echo "unknown option: $FLAG (use --strict, --final, --overleaf or --clean)" >&2; exit 2 ;;
esac

PAPERS=(electronics openweights)
TITLES=("Paper A (electronics)" "Paper B (openweights)")
status=0
summary=()

for i in 0 1; do
  paper="${PAPERS[$i]}"
  dir="$HERE/$paper"
  log="$dir/latex/build_all_$paper.log"
  echo "##### ${TITLES[$i]}: $paper/build.sh $FLAG"
  "$dir/build.sh" "$FLAG" 2>&1 | tee "$log"
  rc=${PIPESTATUS[0]}
  if [ "$FLAG" = "--clean" ]; then
    [ "$rc" -eq 0 ] || status=1
    continue
  fi
  pages=$(sed -n 's/^=== SUCCESS: .* (\([0-9]*\) pages.*/\1/p' "$log" | tail -1)
  sup=$(sed -n 's/^supplement: .* (\([0-9]*\) pages).*/\1/p' "$log" | tail -1)
  if [ "$rc" -ne 0 ]; then result="FAILED"; status=1
  elif grep -q '^FINAL: ok' "$log"; then result="FINAL ok"
  elif grep -q '^STRICT: ok' "$log"; then result="STRICT ok"
  else result="built (no strict check)"; fi
  todo=$(cat "$dir"/latex/*.tex 2>/dev/null | grep -o 'TODO(authors)\|TODO(runs)' | wc -l)
  summary+=("$(printf '%-22s pages %s (+%s supplement)   %s   open TODO markers: %s' "${TITLES[$i]}" "${pages:-?}" "${sup:-?}" "$result" "$todo")")
done

if [ "$FLAG" != "--clean" ]; then
  echo
  echo "===== summary ($FLAG) ====="
  printf '%s\n' "${summary[@]}"
fi
exit "$status"
