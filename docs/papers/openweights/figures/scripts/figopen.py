#!/usr/bin/env python3
"""Helpers of the open-weights paper's figures (gex-llm-patterns, docs/papers/openweights).

The look (``theme``), the pipeline contract and the readers of ``results/`` (``figdata``, ``figllm``) belong to the
Electronics manuscript and live in ``docs/papers/electronics/figures/scripts``; this module imports them from there and
does not copy or change them.  What it adds is what only this paper needs:

* the model registry of the comparison (labels, colours, markers, the arm prefix of each model) and the seven arms;
* a command line whose default output folder is ``docs/papers/openweights/figures/output``;
* ``finish``, which writes the figure and its manifest as ``theme.finish`` does and adds the hashes of this paper's own
  code (the Electronics ``code`` list only covers the modules of the Electronics folders);
* small loaders of the stored tables (``detection_by_year.csv``, the condensed runs table).

Nothing here reads a database or invents values; a model or arm that has no rows yet (the two runs of decisions D-33 and
D-34 while they are pending) is reported back to the caller, which says so on the figure or leaves it out.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

HERE = Path(__file__).resolve().parent
PAPER_DIR = HERE.parents[1]  # docs/papers/openweights
REPO_ROOT = HERE.parents[4]
ELECTRONICS_SCRIPTS = REPO_ROOT / "docs" / "papers" / "electronics" / "figures" / "scripts"
if str(ELECTRONICS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ELECTRONICS_SCRIPTS))

import figdata  # noqa: E402
import figllm  # noqa: E402
import theme  # noqa: E402
from theme import common  # noqa: E402

OUTPUT_DIR = PAPER_DIR / "figures" / "output"
CONDENSED_DIR = REPO_ROOT / "data" / "backups" / "gex_llm" / "condensed"

# --------------------------------------------------------------------------- the seven arms
ARMS: Tuple[str, ...] = ("bridge_jan", "full_spy", "ex0dte_spy", "p34_obf_2024", "p34_dated_2024", "p34_obf_2020", "p34_dated_2020")
ARM_LABELS: Dict[str, str] = {
    "bridge_jan": "Published inputs", "full_spy": "Complete SPY series", "ex0dte_spy": "Complete, no same-day expiries",
    "p34_obf_2024": "2024 baseline, relative labels", "p34_dated_2024": "2024 baseline, dated",
    "p34_obf_2020": "2020 baseline, relative labels", "p34_dated_2020": "2020 baseline, dated",
}

# --------------------------------------------------------------------------- the models
HOSTED_COLOR = theme.PUBLISHED_COLOR  # models and results cited from Paper A are grey


class Model:
    """One compared model: the label in the stored tables, the arm prefix, how it is drawn and which arms it ran."""

    def __init__(self, key: str, model: str, prefix: str, label: str, color: str, marker: str,
                 arms: Sequence[str] = ARMS) -> None:
        self.key, self.model, self.prefix, self.label = key, model, prefix, label
        self.color, self.marker, self.arms = color, marker, tuple(arms)

    def arm(self, base: str) -> str:
        return f"{self.prefix}{base}"


MODELS: Tuple[Model, ...] = (
    Model("oss", "gpt-oss-20b", "oss_", "gpt-oss-20b", "#1B7837", "o"),
    Model("llama", "llama-3.1-8b-instruct", "llama_", "Llama 3.1 8B, verdict first", "#B35806", "s"),
    Model("qwen", "qwen3-8b", "qwen_", "qwen3-8b", "#6A3D9A", "^"),
    # Pending runs (decisions D-33 and D-34): drawn as soon as their arms exist in results/.
    Model("llamarf", "llama-3.1-8b-instruct-rf", "llamarf_", "Llama 3.1 8B, reasoning first", "#E08214", "D"),
    Model("osst0", "gpt-oss-20b-t0", "osst0_", "gpt-oss-20b, temperature 0", "#5AAE61", "P", arms=("bridge_jan",)),
    Model("llamat0", "llama-3.1-8b-instruct-t0", "llamat0_", "Llama 3.1 8B, temperature 0", "#D8A15A", "X", arms=("bridge_jan",)),
)
MODEL_BY_KEY = {m.key: m for m in MODELS}
LUNA = Model("luna", "gpt-6-luna", "", "gpt-6-luna (Paper A)", HOSTED_COLOR, "d")

PERIODS: Tuple[Tuple[str, str, int, int], ...] = (
    ("2008–2019", "2008-2019", 2008, 2019), ("2020–2023", "2020-2023", 2020, 2023),
    ("2024–2025", "2024-2025", 2024, 2025), ("2026", "2026", 2026, 2026))  # (label, key of missing_answer_bounds.csv, from, to)


# --------------------------------------------------------------------------- command line and output
def parse_args(fig_id: str, doc: Optional[str], argv: Optional[Sequence[str]] = None, configure=None):
    def add_options(parser) -> None:
        parser.set_defaults(output_dir=OUTPUT_DIR)
        if configure is not None:
            configure(parser)

    return figllm.parse_args(fig_id, doc, argv, add_options)


def own_code() -> Dict[str, str]:
    """sha256 of this paper's figure code (figopen.py and the figure script that is running)."""
    files = [Path(sys.argv[0]).resolve(), Path(__file__).resolve()]
    return {theme.display_path(p): common.sha256_file(p) for p in dict.fromkeys(files) if p.is_file()}


def finish(fig, fig_id: str, args, sources: Sequence[Path], rows: Dict[str, int], extra: Optional[Dict[str, Any]] = None):
    """theme.finish plus the hashes of this paper's own code in the manifest."""
    return theme.finish(fig, fig_id, args, sources, rows, {**(extra or {}), "openweights_code": own_code()})


# --------------------------------------------------------------------------- tables of results/
def load_detection(inputs: figdata.Inputs) -> pd.DataFrame:
    """detection_by_year.csv as written by 05_report.py (percent columns as stored)."""
    return inputs.csv("detection_by_year.csv", ["label_source", "arm", "arm_role", "model", "series_key", "symbol", "scope", "year",
                                                 "n_windows", "n_parsed", "n", "n_detect", "rate_pct", "n_compared", "agree_pct",
                                                 "kappa"])


def llm_all(detection: pd.DataFrame) -> pd.DataFrame:
    """The all-years LLM rows (primary arms), indexed by arm."""
    frame = detection[(detection["label_source"] == "llm") & (detection["scope"] == "all") & (detection["arm_role"] == "primary")]
    return frame.set_index("arm")


def llm_years(detection: pd.DataFrame, arm: str) -> pd.DataFrame:
    """The yearly rows of one LLM arm, indexed by year."""
    frame = detection[(detection["label_source"] == "llm") & (detection["scope"] == "year") & (detection["arm"] == arm)
                      & (detection["arm_role"] == "primary")]
    return frame.assign(year=frame["year"].astype(int)).set_index("year")


def rule_years(detection: pd.DataFrame, series_key: str, symbol: str = "SPY") -> pd.DataFrame:
    """The yearly rows of the rule on one series, indexed by year."""
    frame = detection[(detection["label_source"] == "classifier") & (detection["scope"] == "year")
                      & (detection["series_key"] == series_key) & (detection["symbol"] == symbol)]
    return frame.assign(year=frame["year"].astype(int)).set_index("year")


def present(models: Sequence[Model], by_arm: pd.DataFrame) -> List[Model]:
    """Models with at least one of their arms in the table."""
    return [m for m in models if any(m.arm(a) in by_arm.index for a in m.arms)]


def condensed_runs() -> Tuple[pd.DataFrame, Path]:
    """runs.csv.gz (git keeps it) with ``seconds`` and ``retry_of`` read from the run_metadata JSON."""
    path = CONDENSED_DIR / "runs.csv.gz"
    if not path.is_file():
        raise SystemExit(f"missing input {path} (06_condense.py writes it; git keeps it)")
    runs = pd.read_csv(path)
    meta = runs["run_metadata"].map(lambda s: json.loads(s) if isinstance(s, str) else {})
    runs["seconds"] = meta.map(lambda m: (m.get("local") or {}).get("seconds"))
    runs["retry_of"] = meta.map(lambda m: m.get("retry_of"))
    return runs, path
