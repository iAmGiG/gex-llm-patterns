#!/usr/bin/env python3
"""Reproduction ladder: what is stored, what a hosted successor adds, and what open weights at a pinned revision add.

A left-to-right schematic of three rungs.  Rung 1 (grey, cited from the companion paper, Paper A): the hosted model of
the published run is retired and only its stored answers survive.  Rung 2 (grey, cited from Paper A): its hosted
successor alias reproduces the stored verdicts, but the alias has no dated snapshot and can be retired in turn.  Rung 3
(coloured, the object of this paper): open-weights models at pinned revisions answer the stored requests on local GPUs.
Boxes of the two pending runs (the Llama 3.1 8B arms with the reasoning field first and the temperature-0 control) are
dashed until their runs exist in ``runs.csv.gz``, and solid, with their counts, afterwards.

Input  data/backups/gex_llm/condensed/runs.csv.gz (model, mode, n_requests, run_metadata.local.seconds, run_metadata.retry_of);
  results/bridge_agreement.csv (comparison bridge, ref_arm r1_o4mini, other_arm bridge_jan, scope all: n_pairs, agree_pct,
  kappa).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import figopen  # first: it puts the Electronics figure modules on sys.path
import figdata  # noqa: E402
import theme  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

import fig01_study_design as f1  # noqa: E402  (its Canvas draws boxes and checks that no text leaves its box)

FIG_ID = "bf01_reproduction_ladder"
RESULTS_FILES = ("bridge_agreement.csv",)
TABLE_KINDS: Sequence[str] = ()
HEIGHT_IN = 3.0
LINE = f1.LINE
PAD = f1.PAD
COL = {1: (0.04, 1.60), 2: (1.86, 3.42), 3: (3.68, 6.10)}
TOP = 0.42
STRIPE = f1.STRIPE

# (model label in runs.csv.gz, name drawn, pending description)
OPEN_ROWS: Tuple[Tuple[str, str, str], ...] = (
    ("gpt-oss-20b", "gpt-oss-20b", ""), ("llama-3.1-8b-instruct", "Llama 3.1 8B", ""), ("qwen3-8b", "qwen3-8b", ""),
    ("llama-3.1-8b-instruct-rf", "Llama 3.1 8B, reasoning first", "pending run"),
    ("gpt-oss-20b-t0 / llama-3.1-8b-instruct-t0", "Decoding control, temperature 0", "pending run"))


def counts(runs, models: Sequence[str]) -> Optional[Tuple[int, float]]:
    """(requests, GPU-hours) of the local runs of these models, or None when none exists."""
    local = runs[(runs["mode"] == "local") & runs["model"].isin(models)]
    if local.empty:
        return None
    return int(local["n_requests"].sum()), float(local["seconds"].sum()) / 3600.0


def dashed(canvas: f1.Canvas, x0: float, y0: float, x1: float, y1: float) -> Rectangle:
    patch = Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=theme.SURFACE, edgecolor=theme.MUTED, linewidth=0.8, linestyle=(0, (4, 2)), zorder=1)
    canvas.ax.add_patch(patch)
    return patch


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figopen.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    bridge = inputs.csv("bridge_agreement.csv", ["comparison", "ref_arm", "other_arm", "scope", "n_pairs", "agree_pct", "kappa"])
    row = bridge[(bridge["comparison"] == "bridge") & (bridge["ref_arm"] == "r1_o4mini") & (bridge["other_arm"] == "bridge_jan")
                 & (bridge["scope"] == "all")]
    if len(row) != 1:
        inputs.fail("bridge_agreement.csv has no single all-years bridge row of r1_o4mini versus bridge_jan")
    runs, runs_path = figopen.condensed_runs()
    inputs._record(runs_path, len(runs))
    n_pairs, agree, kappa = int(row["n_pairs"].iloc[0]), float(row["agree_pct"].iloc[0]), float(row["kappa"].iloc[0])

    fig = theme.new_figure(HEIGHT_IN)
    canvas = f1.Canvas(fig, theme.FIG_WIDTH_IN, HEIGHT_IN)
    for rung, title in ((1, "Rung 1: retired model"), (2, "Rung 2: hosted alias"), (3, "Rung 3: open weights, pinned revision")):
        canvas.text(COL[rung][0], 0.06, title, bold=True)
    canvas.text(COL[3][0], 0.06 + LINE, "vLLM 0.32.0, one A100 per worker, no API cost")

    # rungs 1 and 2: cited from Paper A, grey
    cited = {
        1: [("o4-mini", True), ("stored answers only", False), (f"{n_pairs:,} verdicts kept", False), ("endpoint: model_not_found", False), ("cited from Paper A", False)],
        2: [("gpt-6-luna", True), ("no dated snapshot", False), ("same verdict as o4-mini:", False), (f"{agree:.1f}% (kappa {kappa:.2f})", False),
            ("can be retired in turn", False), ("cited from Paper A", False)]}
    bottoms = []
    for rung, lines in cited.items():
        x0, x1 = COL[rung]
        box = canvas.box(x0, TOP, x1, TOP + 2 * PAD + LINE * len(lines) + 0.04, stripe=figopen.HOSTED_COLOR)
        canvas.lines(x0 + STRIPE + PAD, TOP + PAD, lines, container=box)
        bottoms.append(TOP + 2 * PAD + LINE * len(lines) + 0.04)
    shared = [("The same stored requests in every rung", True), ("30 obfuscated daily values, the rule stated in the prompt,", False),
              ("and a strict JSON schema (companion paper, Paper A)", False)]
    y_shared = max(bottoms) + 0.12
    box = canvas.box(COL[1][0], y_shared, COL[2][1], y_shared + 2 * PAD + LINE * len(shared), face=theme.PANEL_BG)
    canvas.lines(COL[1][0] + PAD, y_shared + PAD, shared, container=box)
    mid = TOP + (bottoms[0] - TOP) / 2
    canvas.arrow((COL[1][1] + 0.02, mid), (COL[2][0] - 0.02, mid))
    canvas.arrow((COL[2][1] + 0.02, mid), (COL[3][0] - 0.02, mid))

    # rung 3: one box per model, coloured; pending runs dashed
    x0, x1 = COL[3]
    y = TOP
    box_h = 2 * PAD + 2 * LINE
    drawn: List[Dict[str, object]] = []
    colors = {"gpt-oss-20b": figopen.MODEL_BY_KEY["oss"].color, "llama-3.1-8b-instruct": figopen.MODEL_BY_KEY["llama"].color,
              "qwen3-8b": figopen.MODEL_BY_KEY["qwen"].color, "llama-3.1-8b-instruct-rf": figopen.MODEL_BY_KEY["llamarf"].color,
              "gpt-oss-20b-t0 / llama-3.1-8b-instruct-t0": figopen.MODEL_BY_KEY["osst0"].color}
    for models, name, tag in OPEN_ROWS:
        found = counts(runs, models.split(" / "))
        if found is None:
            patch = dashed(canvas, x0, y, x1, y + box_h)
            canvas.lines(x0 + PAD, y + PAD, [(name, True), (tag, False)], container=patch)
            drawn.append({"model": models, "pending": True})
        else:
            patch = canvas.box(x0, y, x1, y + box_h, stripe=colors[models])
            canvas.lines(x0 + STRIPE + PAD, y + PAD, [(name, True), (f"{found[0]:,} requests, {found[1]:.1f} GPU hours", False)], container=patch)
            drawn.append({"model": models, "pending": False, "requests": found[0], "gpu_hours": round(found[1], 1)})
        y += box_h + 0.07
    canvas.check()
    figopen.finish(fig, FIG_ID, args, inputs.sources, inputs.rows,
                   {"boxes": drawn, "bridge": {"n_pairs": n_pairs, "agree_pct": round(agree, 3), "kappa": round(kappa, 4)}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
