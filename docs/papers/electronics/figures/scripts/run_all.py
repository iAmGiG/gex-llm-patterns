#!/usr/bin/env python3
"""Run the figure scripts of the Electronics extension (gex-llm-patterns issue #261).

Every figure is one script, ``figNN_<name>.py`` in this folder, that reads the stored results
(``docs/papers/electronics/results/`` and the parquet copies of the result tables) and writes
``figures/output/figNN_<name>.png`` (300 dpi, 6.14 in wide), a vector ``.pdf`` and a provenance manifest ``.json``.
The script stem is the output stem and is the name the manuscript includes.  A figure whose inputs are missing stops
with a message and writes nothing: there is no synthetic fallback.

Each figure runs in its own Python process, so a failure stops that figure only and its manifest lists exactly the
code it was drawn with.  ``--results-dir``, ``--tables-dir``, ``--output-dir``, ``--no-pdf`` and ``-v`` are handed to
every script; options of a single script (for example ``fig02_convention_window.py --window-end``) are used by
running that script directly.

Examples (repository root, AutoGex env)::

    python docs/papers/electronics/figures/scripts/run_all.py                  # all twelve figures
    python docs/papers/electronics/figures/scripts/run_all.py fig01 fig05      # a selection (fig01, 01, 1 or the stem)
    python docs/papers/electronics/figures/scripts/run_all.py --list           # the registry and the inputs of each figure
    python docs/papers/electronics/figures/scripts/run_all.py --check          # which outputs exist and which are stale

Exit status: 0 when every selected figure was drawn (or, with ``--check``, is present and current), 1 otherwise.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import theme

SCRIPTS_DIR = Path(__file__).resolve().parent
MANUSCRIPT = theme.common.PAPER_DIR / "latex" / "Regan_Xie_Electronics.tex"
STEM_PATTERN = re.compile(r"^(?:fig)?(\d{1,2})(?:_.*)?$")
MACRO_PATTERN = re.compile(r"\\newcommand\{\\fig[A-Za-z]+\}\{(fig\d{2}_[A-Za-z0-9_]+)\}")
OUTPUT_KINDS = ("png", "pdf", "json")


@dataclass(frozen=True)
class Figure:
    number: int
    stem: str  # script stem == output stem == the name the manuscript includes
    title: str

    @property
    def id(self) -> str:
        return f"fig{self.number:02d}"

    @property
    def script(self) -> Path:
        return SCRIPTS_DIR / f"{self.stem}.py"


FIGURES: Tuple[Figure, ...] = (
    Figure(1, "fig01_study_design", "Study design: series, windows, arms and cost"),
    Figure(2, "fig02_convention_window", "One SPY window under four GEX conventions"),
    Figure(3, "fig03_series_comparison", "Series compared: mean |GEX| and daily sign agreement, SPY"),
    Figure(4, "fig04_classifier_replay", "Deterministic replay of the published labels by year"),
    Figure(5, "fig05_llm_arms_by_year", "gpt-6-luna detection rate by year, per SPY arm"),
    Figure(6, "fig06_bridge_agreement", "Bridge: gpt-6-luna against the published o4-mini labels"),
    Figure(7, "fig07_llm_classifier_fidelity", "Fidelity of the model answers to the deterministic rule"),
    Figure(8, "fig08_deep_baseline", "Pre-0DTE baseline, SPY 2008-2019"),
    Figure(9, "fig09_cross_asset", "Cross-asset replication: SPY, QQQ, IWM"),
    Figure(10, "fig10_post_publication_2026", "Post-publication period, 2026"),
    Figure(11, "fig11_intraday_vs_eod", "Late-session intraday snapshot versus end of day"),
    Figure(12, "fig12_threshold_sensitivity", "Threshold sensitivity of the 2024-2025 detection rate"),
)  # fmt: skip


# --------------------------------------------------------------------------- selection
def select(tokens: Sequence[str]) -> List[Figure]:
    """Figures named by ``fig05``, ``05``, ``5`` or the full stem; no token selects all, in registry order."""
    if not tokens:
        return list(FIGURES)
    chosen: Dict[int, Figure] = {}
    for token in tokens:
        match = STEM_PATTERN.match(token)
        figure = next((f for f in FIGURES if match and f.number == int(match.group(1))), None)
        if figure is None or ("_" in token and token != figure.stem):
            known = ", ".join(f.id for f in FIGURES)
            raise SystemExit(f"run_all.py: unknown figure {token!r}; use one of {known} or a full stem (see --list)")
        chosen[figure.number] = figure
    return [chosen[n] for n in sorted(chosen)]


# --------------------------------------------------------------------------- what a script declares (read, not run)
def declared(script: Path) -> Dict[str, Any]:
    """FIG_ID, RESULTS_FILES and TABLE_KINDS of a script, and its docstring, read from the source without importing it."""
    if not script.is_file():
        return {}
    tree = ast.parse(script.read_text())
    found: Dict[str, Any] = {"doc": ast.get_docstring(tree)}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id in ("FIG_ID", "RESULTS_FILES", "TABLE_KINDS"):
            try:
                found[target.id] = ast.literal_eval(value)
            except ValueError:
                pass
    return found


def manuscript_stems() -> Optional[List[str]]:
    """Figure stems the manuscript registers (\\newcommand{\\figXxx}{figNN_name}), or None without a manuscript."""
    return MACRO_PATTERN.findall(MANUSCRIPT.read_text()) if MANUSCRIPT.is_file() else None


def summary_line(info: Dict[str, Any]) -> str:
    doc = (info.get("doc") or "").strip()
    return doc.splitlines()[0] if doc else ""


# --------------------------------------------------------------------------- --list
def list_figures(figures: Sequence[Figure]) -> int:
    print(f"{'id':<6}{'script':<8}{'stem':<34}inputs")
    for fig in figures:
        info = declared(fig.script)
        inputs = [*(f"results/{name}" for name in info.get("RESULTS_FILES", ())),
                  *(f"tables/{kind}" for kind in info.get("TABLE_KINDS", ()))]
        flag = "yes" if info else "MISSING"
        print(f"{fig.id:<6}{flag:<8}{fig.stem:<34}{', '.join(inputs) if inputs else ('-' if info else '')}")
        print(f"{'':<6}{'':<8}{fig.title}")
    return 0


# --------------------------------------------------------------------------- --check
class Hashes:
    """sha256 of files, computed once per path (several figures read the same parquet files)."""

    def __init__(self) -> None:
        self._seen: Dict[Path, Optional[str]] = {}

    def __call__(self, path: Path) -> Optional[str]:
        if path not in self._seen:
            self._seen[path] = theme.common.sha256_file(path) if path.is_file() else None
        return self._seen[path]


def resolve(recorded: str) -> Path:
    path = Path(recorded)
    return path if path.is_absolute() else theme.REPO_ROOT / path


def status_of(fig: Figure, output_dir: Path, hashes: Hashes) -> Tuple[str, str]:
    """(status, detail) of one figure: 'ok' only when script, outputs and manifest agree with the files on disk."""
    info = declared(fig.script)
    if not info:
        return "no script", f"{fig.script.name} does not exist"
    if info.get("FIG_ID") != fig.stem:
        return "stem mismatch", f"{fig.script.name} declares FIG_ID {info.get('FIG_ID')!r}, the registry says {fig.stem!r}"
    png, manifest_path = output_dir / f"{fig.stem}.png", output_dir / f"{fig.stem}.json"
    if not png.is_file():
        return "not built", "no png"
    if not manifest_path.is_file():
        return "no manifest", f"{manifest_path.name} is missing"
    manifest = json.loads(manifest_path.read_text())
    recorded = (manifest.get("outputs") or {}).get("png", {}).get("sha256")
    if recorded != hashes(png):
        return "png changed", "the png differs from the one the manifest describes"
    changed = [Path(s["path"]).name for s in manifest.get("sources", []) if hashes(resolve(s["path"])) != s.get("sha256")]
    if changed:
        return "stale", "inputs changed: " + ", ".join(sorted(set(changed)))
    recoded = [Path(c["path"]).name for c in manifest.get("code", []) if hashes(resolve(c["path"])) != c.get("sha256")]
    if recoded:
        return "stale", "code changed: " + ", ".join(sorted(set(recoded)))
    return "ok", ""


def check_figures(figures: Sequence[Figure], output_dir: Path) -> int:
    hashes = Hashes()
    print(f"{'id':<6}{'stem':<34}{'png':<10}{'status'}")
    current = 0
    for fig in figures:
        status, detail = status_of(fig, output_dir, hashes)
        png = output_dir / f"{fig.stem}.png"
        size = f"{png.stat().st_size / 1024:.0f} KB" if png.is_file() else "-"
        print(f"{fig.id:<6}{fig.stem:<34}{size:<10}{status}{f' ({detail})' if detail else ''}")
        current += status == "ok"
    registered = {f.stem for f in FIGURES}
    stray = sorted(p.stem for p in SCRIPTS_DIR.glob("fig[0-9][0-9]_*.py") if p.stem not in registered)
    manuscript = manuscript_stems()
    wanted = set(manuscript or ())
    notes = [f"script not in the registry: {stem}" for stem in stray]
    notes += [f"manuscript includes {stem}, which is not in the registry" for stem in sorted(wanted - registered)]
    notes += [f"registry figure {fig.stem} is not included by the manuscript" for fig in FIGURES
              if manuscript is not None and fig.stem not in wanted]
    for note in notes:
        print(f"note: {note}")
    print(f"{current}/{len(figures)} figures present and current; {len(notes)} registry note(s)")
    return 0 if current == len(figures) and not notes else 1


# --------------------------------------------------------------------------- run
def run_figure(fig: Figure, passthrough: Sequence[str], output_dir: Path) -> Tuple[str, float]:
    """Run one script in its own process; returns (status, seconds) and prints what the script logged."""
    if not fig.script.is_file():
        print(f"[{fig.id}] {fig.script.name}: script missing")
        return "script missing", 0.0
    started = time.time()
    written = [output_dir / f"{fig.stem}.{kind}" for kind in ("png", "json")]
    # Freshness is judged by a change of the file (mtime_ns and size), not against the wall clock: the output
    # tree is on NFS, whose file clock runs minutes behind the system clock, so a wall-clock test calls fresh
    # files stale.
    before = [(p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else None for p in written]
    print(f"[{fig.id}] {fig.stem}")
    done = subprocess.run([sys.executable, str(fig.script), *passthrough], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    seconds = time.time() - started
    for line in done.stdout.strip().splitlines():
        print(f"    {line}")
    if done.returncode != 0:
        return f"FAILED (exit {done.returncode})", seconds
    after = [(p.stat().st_mtime_ns, p.stat().st_size) if p.is_file() else None for p in written]
    if not all(a is not None and a != b for a, b in zip(after, before)):
        return "FAILED (no fresh output)", seconds
    return "ok", seconds


def run_figures(figures: Sequence[Figure], passthrough: Sequence[str], output_dir: Path, fail_fast: bool) -> int:
    results: List[Tuple[Figure, str, float]] = []
    for fig in figures:
        status, seconds = run_figure(fig, passthrough, output_dir)
        results.append((fig, status, seconds))
        if status != "ok" and fail_fast:
            break
    print("\nSummary")
    for fig, status, seconds in results:
        png = output_dir / f"{fig.stem}.png"
        size = f"{png.stat().st_size / 1024:.0f} KB" if status == "ok" and png.is_file() else "-"
        print(f"  {fig.id}  {fig.stem:<34}{status:<24}{size:>8}{seconds:>7.1f}s")
    failed = [fig.id for fig, status, _ in results if status != "ok"]
    skipped = len(figures) - len(results)
    print(f"{len(results) - len(failed)}/{len(figures)} figures drawn" + (f"; failed: {', '.join(failed)}" if failed else "")
          + (f"; {skipped} not run (--fail-fast)" if skipped else ""))
    return 1 if failed or skipped else 0


# --------------------------------------------------------------------------- command line
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("figures", nargs="*", metavar="FIG", help="figures to run: fig01, 01, 1 or a full stem (default: all)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="list the figures and what each reads, then exit")
    mode.add_argument("--check", action="store_true",
                      help="report which outputs exist and whether their inputs or code changed since they were drawn")
    parser.add_argument("--results-dir", type=Path, help="folder with the CSV/YAML of 05_report.py (default: the script's)")
    parser.add_argument("--tables-dir", type=Path, help="folder with the parquet copies of the result tables")
    parser.add_argument("--output-dir", type=Path, help="where the figures are written and checked (default: figures/output)")
    parser.add_argument("--no-pdf", action="store_true", help="write PNG and manifest only")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging in the scripts")
    parser.add_argument("-x", "--fail-fast", action="store_true", help="stop after the first figure that fails")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    figures = select(args.figures)
    output_dir = args.output_dir if args.output_dir is not None else theme.OUTPUT_DIR
    passthrough: List[str] = []
    for flag, value in (("--results-dir", args.results_dir), ("--tables-dir", args.tables_dir), ("--output-dir", args.output_dir)):
        if value is not None:
            passthrough += [flag, str(value)]
    passthrough += [flag for flag, on in (("--no-pdf", args.no_pdf), ("-v", args.verbose)) if on]
    if args.list:
        return list_figures(figures)
    if args.check:
        return check_figures(figures, output_dir)
    return run_figures(figures, passthrough, output_dir, args.fail_fast)


if __name__ == "__main__":
    raise SystemExit(main())
