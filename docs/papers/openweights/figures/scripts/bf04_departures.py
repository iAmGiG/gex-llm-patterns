#!/usr/bin/env python3
"""Where the models depart from the rule: the criterion at the edge, and the sign-flip counts behind it.

(a) Windows of the seven comparison arms on which a model's verdict differs from the rule, by direction and, where the
model detects a regime that the rule rejects, by the criterion that the rule's own numbers fail: only the limit of five
sign flips, only the magnitude threshold, only the persistence threshold, or two criteria.  gpt-oss-20b and qwen3-8b are the
open-weights models that answer on the windows where they differ; gpt-6-luna is a reference from the companion paper
(Paper A).  Llama 3.1 8B detects every window but two, so its departures are the rule's rejected windows and are not drawn.
(b) For the windows that fail only the flip limit: how many windows have each sign-flip count by the rule's computation
(filled) and by the model's report (open); the dashed line is the limit (at most five flips are allowed).

Input  results/disagreements.csv (arm, model, llm_detected, clf_detected, clf_persistence_pct, clf_avg_magnitude_bn,
  clf_sign_flips, llm_sign_flips; one row per window on which an arm of a model differs from the rule); thresholds from
  results/report.yaml diagnostics.thresholds.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import figopen  # first: it puts the Electronics figure modules on sys.path
import figdata  # noqa: E402
import theme  # noqa: E402

FIG_ID = "bf04_departures"
RESULTS_FILES = ("disagreements.csv", "report.yaml")
TABLE_KINDS: Sequence[str] = ()
HEIGHT_IN = 2.9
COLUMNS = ["arm", "arm_role", "model", "llm_detected", "clf_detected", "clf_persistence_pct", "clf_avg_magnitude_bn",
           "clf_sign_flips", "llm_sign_flips"]
ROWS = (("gpt-6-luna", "", "gpt-6-luna (Paper A)", figopen.HOSTED_COLOR), ("gpt-oss-20b", "oss_", "gpt-oss-20b", "#1B7837"),
        ("qwen3-8b", "qwen_", "qwen3-8b", "#6A3D9A"))
CLASSES = ("flips only", "magnitude only", "persistence only", "two criteria")
CLASS_FILL = {"flips only": "#8C510A", "magnitude only": "#DFC27D", "persistence only": "#80CDC1", "two criteria": "#01665E"}
REJECTS = "model rejects, rule detects"


def classify(frame: pd.DataFrame, limits: Dict[str, float]) -> pd.Series:
    """The failing criteria of the rule's own numbers for windows that the rule rejects."""
    failed = pd.DataFrame({
        "persistence": frame["clf_persistence_pct"] < 100.0 * limits["persistence"] - 1e-9,
        "magnitude": frame["clf_avg_magnitude_bn"] < limits["mean_abs_gex_usd"] / 1e9,
        "flips": frame["clf_sign_flips"] > limits["max_sign_flips"]})
    n = failed.sum(axis=1)
    out = pd.Series("", index=frame.index)
    out[(n == 1) & failed["flips"]] = "flips only"
    out[(n == 1) & failed["magnitude"]] = "magnitude only"
    out[(n == 1) & failed["persistence"]] = "persistence only"
    out[n >= 2] = "two criteria"
    if (n == 0).any():
        raise SystemExit(f"{FIG_ID}: {int((n == 0).sum())} window(s) that the rule rejects fail no criterion on its own numbers")
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figopen.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    table = inputs.csv("disagreements.csv", COLUMNS)
    limits = inputs.yaml("report.yaml")["diagnostics"]["thresholds"]
    table = table[table["arm_role"] == "primary"].copy()
    table["llm_detected"] = figllm_flag(table["llm_detected"])
    table["clf_detected"] = figllm_flag(table["clf_detected"])
    bases = set(figopen.ARMS)

    counts: Dict[str, Dict[str, int]] = {}
    flips: Dict[str, pd.DataFrame] = {}
    for model, prefix, _, _ in ROWS:
        rows = table[(table["model"] == model) & table["arm"].isin([prefix + b for b in bases])]
        detects = rows[rows["llm_detected"] & ~rows["clf_detected"]]
        kinds = classify(detects, limits)
        counts[model] = {c: int((kinds == c).sum()) for c in CLASSES}
        counts[model][REJECTS] = int((~rows["llm_detected"] & rows["clf_detected"]).sum())
        flips[model] = detects[kinds == "flips only"][["clf_sign_flips", "llm_sign_flips"]]

    fig = theme.new_figure(HEIGHT_IN)
    ax_bars, ax_flip = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.15, 1.0]})
    y = np.arange(len(ROWS))[::-1].astype(float)
    for r, (model, _, label, _) in zip(y, ROWS, strict=True):
        left = 0.0
        for c in CLASSES:
            ax_bars.barh(r, counts[model][c], left=left, height=0.55, color=CLASS_FILL[c], zorder=3)
            left += counts[model][c]
        ax_bars.barh(r, counts[model][REJECTS], left=left, height=0.55, facecolor=theme.SURFACE, edgecolor=theme.INK_SECONDARY,
                     linewidth=0.8, hatch="////", zorder=3)
        ax_bars.text(left + counts[model][REJECTS] + 1.5, r, f"{int(left)} + {counts[model][REJECTS]}", va="center", fontsize=8, color=theme.INK)
    ax_bars.set_yticks(y)
    ax_bars.set_yticklabels([r[2] for r in ROWS], fontsize=8)
    ax_bars.set_xlim(0, 135)
    ax_bars.set_xlabel("Windows that differ from the rule")
    ax_bars.grid(axis="x", color=theme.GRID, linewidth=0.5)
    theme.panel_title(ax_bars, "a", "Direction and criterion")

    xs = np.arange(0, 12)
    for r, (model, _, label, color) in zip(y, ROWS, strict=True):
        comp = flips[model]["clf_sign_flips"].value_counts().reindex(xs, fill_value=0)
        rep = flips[model]["llm_sign_flips"].value_counts().reindex(xs, fill_value=0)
        for series, dy, hollow in ((comp, 0.14, False), (rep, -0.14, True)):
            sel = series[series > 0]
            ax_flip.scatter(sel.index, np.full(len(sel), r + dy), s=6 + 5.0 * sel.to_numpy(), zorder=4, clip_on=False,
                            facecolors=theme.SURFACE if hollow else color, edgecolors=color, linewidths=0.9)
    theme.threshold_line(ax_flip, 5.5, "limit: at most 5", orientation="v", ha="right")
    ax_flip.set_yticks(y)
    ax_flip.set_yticklabels([])
    ax_flip.set_xticks(range(0, 12, 2))
    ax_flip.set_xlim(-0.5, 11.5)
    ax_flip.set_ylim(-0.6, len(ROWS) - 0.4)
    ax_bars.set_ylim(-0.6, len(ROWS) - 0.4)
    ax_flip.set_xlabel("Sign flips in the window")
    ax_flip.grid(axis="x", color=theme.GRID, linewidth=0.5)
    theme.panel_title(ax_flip, "b", "Windows that fail only the flip limit")

    handles: List = [Patch(facecolor=CLASS_FILL[c], label=f"model detects, rule rejects: {c}") for c in CLASSES]
    handles += [Patch(facecolor=theme.SURFACE, edgecolor=theme.INK_SECONDARY, hatch="////", label=REJECTS),
                Line2D([0], [0], linestyle="none", marker="o", markersize=4.4, markerfacecolor=theme.INK_SECONDARY,
                       markeredgecolor=theme.INK_SECONDARY, label="(b) rule's count"),
                Line2D([0], [0], linestyle="none", marker="o", markersize=4.4, markerfacecolor=theme.SURFACE,
                       markeredgecolor=theme.INK_SECONDARY, label="(b) model's report")]
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    figopen.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, {"counts": counts, "arms": sorted(bases)})
    return 0


def figllm_flag(values: pd.Series) -> pd.Series:
    """Boolean from a CSV column that holds True/False."""
    return values.map({True: True, False: False, "True": True, "False": False}).astype(bool)


if __name__ == "__main__":
    raise SystemExit(main())
