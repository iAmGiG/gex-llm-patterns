#!/usr/bin/env python3
"""Agreement with the deterministic rule, per model and arm: percent agreement (a) and Cohen's kappa (b).

One row per arm (the seven arms of the comparison), one marker per open-weights model.  A hollow grey diamond marks
gpt-6-luna on the same arm as a reference; it is a result of the companion paper (Paper A), drawn only for orientation.
Agreement is over the windows that the model answered (Qwen3-8B left 8.8% of all windows unanswered, so its markers
condition on answering; see the bounds in Figure 3).  Kappa is drawn where it is defined; a model that answers one way
on every window has kappa 0 by construction, and it sits on the zero line.  No interval is drawn: windows have stride
one, and dependence-aware intervals of agreement are not stored.  Models of the two pending runs (decisions D-33 and
D-34: ``llamarf_*``, ``osst0_*``, ``llamat0_*``) join the figure as soon as their arms exist in ``results/``.

Input  results/detection_by_year.csv: label_source llm, scope all, arm_role primary; columns arm, n_compared, agree_pct,
  kappa for the arms of the seven comparison arms of each model and of gpt-6-luna.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
from matplotlib.lines import Line2D

import figopen  # first: it puts the Electronics figure modules on sys.path
import figdata  # noqa: E402
import theme  # noqa: E402

FIG_ID = "bf02_agreement_by_arm"
RESULTS_FILES = ("detection_by_year.csv",)
TABLE_KINDS: Sequence[str] = ()
HEIGHT_IN = 3.3


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figopen.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    detection = figopen.load_detection(inputs)
    by_arm = figopen.llm_all(detection)
    models = figopen.present(figopen.MODELS, by_arm)
    if not models:
        inputs.fail("no open-weights arm in detection_by_year.csv")
    arms = list(figopen.ARMS)
    n_rows = len(arms)
    offsets = np.linspace(-0.27, 0.27, len(models)) if len(models) > 1 else np.zeros(1)

    fig = theme.new_figure(HEIGHT_IN)
    ax_agree, ax_kappa = fig.subplots(1, 2, sharey=True)
    y = np.arange(n_rows)[::-1].astype(float)  # first arm on top
    drawn: dict = {}

    def value(arm: str, column: str) -> float:
        return float(by_arm.loc[arm, column]) if arm in by_arm.index else float("nan")

    for ax, column, scale in ((ax_agree, "agree_pct", 1.0), (ax_kappa, "kappa", 1.0)):
        for row, base in enumerate(arms):  # reference: gpt-6-luna on the same arm
            ax.plot([value(base, column)], [y[row]], linestyle="none", marker="d", markersize=5.2, markerfacecolor=theme.SURFACE,
                    markeredgecolor=figopen.HOSTED_COLOR, markeredgewidth=0.9, zorder=3, clip_on=False)
        for k, model in enumerate(models):
            xs, ys = [], []
            for row, base in enumerate(arms):
                arm = model.arm(base)
                if base in model.arms and arm in by_arm.index:
                    xs.append(value(arm, column) * scale)
                    ys.append(y[row] + offsets[k])
            ax.plot(xs, ys, linestyle="none", marker=model.marker, markersize=4.4, markerfacecolor=model.color,
                    markeredgecolor=theme.SURFACE, markeredgewidth=0.5, zorder=4, clip_on=False)
            drawn[(model.key, column)] = [round(v, 4) for v in xs]
        ax.grid(axis="x", color=theme.GRID, linewidth=0.5)
        ax.set_axisbelow(True)
        for r in y:
            ax.axhline(r - 0.5, color=theme.GRID, linewidth=0.4, zorder=0)
    ax_agree.set_xlim(0, 103)
    ax_agree.set_xticks([0, 25, 50, 75, 100])
    ax_agree.set_xlabel("Agreement with the rule (%)")
    ax_kappa.set_xlim(-0.06, 1.06)
    ax_kappa.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_kappa.set_xlabel("Cohen's kappa")
    ax_agree.set_yticks(y)
    ax_agree.set_yticklabels([figopen.ARM_LABELS[a] for a in arms], fontsize=8)
    ax_agree.set_ylim(-0.6, n_rows - 0.4)
    theme.panel_title(ax_agree, "a", "Agreement")
    theme.panel_title(ax_kappa, "b", "Kappa")
    handles: List[Line2D] = [Line2D([0], [0], linestyle="none", marker=m.marker, markersize=4.6, markerfacecolor=m.color,
                                    markeredgecolor=theme.SURFACE, markeredgewidth=0.5, label=m.label) for m in models]
    handles.append(Line2D([0], [0], linestyle="none", marker="d", markersize=5.0, markerfacecolor=theme.SURFACE,
                          markeredgecolor=figopen.HOSTED_COLOR, markeredgewidth=0.9, label=figopen.LUNA.label))
    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    figopen.finish(fig, FIG_ID, args, inputs.sources, inputs.rows,
                   {"models_drawn": [m.key for m in models], "arms": arms, "values": {f"{k[0]}:{k[1]}": v for k, v in drawn.items()}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
