"""One-shot font-size bump for the JRFM figure generators.

Reviewer 3 (JRFM jrfm-4256551) flagged that "Figures and tables must be
improved. Some are too dense and difficult to read." Inspection of the
six JRFM figure generators shows many hardcoded ``fontsize=`` values in
the 8-11 range, which renders as sub-10pt type when the figure is
scaled to textwidth in the journal's A4 layout. This script:

1. Scans the six JRFM figure generator files.
2. Replaces every ``fontsize=N`` and ``labelsize=N`` by ``fontsize=M``
   where M is chosen by the size-bump rule below.
3. Writes the files back in place.

Size-bump rule (conservative +2 with a floor of 12pt, capped at 18pt so
big display numbers remain prominent but do not balloon beyond the
figure canvas):

    original -> bumped
    ------------------
    8-10     -> 12
    11       -> 13
    12       -> 14
    13       -> 15
    14       -> 16
    15       -> 17
    16       -> 18
    17-25    -> keep (already large / title-sized)
    26+      -> keep (display-number emphasis such as a headline stat)

Run this once, then re-run each figure generator to produce updated
PNGs. Commit the generator edits so the change is reproducible.

Usage:
    python bump_font_sizes.py
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

TARGETS = [
    "fig02_regime_window_example.py",
    "fig03_obfuscation.py",
    "fig04_validation_pipeline.py",
    "fig05_selectivity_demo.py",
    "fig06_gex_magnitude_distribution.py",
    "fig08_detection_progression.py",
]


def bump(n: int) -> int:
    if n >= 26:
        return n
    if n >= 17:
        return n
    if n <= 10:
        return 12
    if n == 11:
        return 13
    return n + 2  # 12-16 -> 14-18


def rewrite_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n_changes = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal n_changes
        key = match.group(1)
        size = int(match.group(2))
        new = bump(size)
        if new != size:
            n_changes += 1
        return f"{key}={new}"

    text = re.sub(r"\b(fontsize|labelsize)=(\d+)", repl, text)
    path.write_text(text, encoding="utf-8")
    return n_changes


def main() -> None:
    total = 0
    for name in TARGETS:
        path = HERE / name
        if not path.exists():
            print(f"SKIP (missing): {name}")
            continue
        n = rewrite_file(path)
        print(f"{name}: {n} substitutions")
        total += n
    print(f"Total: {total} substitutions across {len(TARGETS)} files")


if __name__ == "__main__":
    main()
