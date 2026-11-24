#!/usr/bin/env python3
"""Llama 3.1 8B with the verdict first and with the reasoning first (run of decision D-33).

Pending until the arms ``llamarf_*`` exist in ``results/detection_by_year.csv`` (the model label is
``llama-3.1-8b-instruct-rf``).  Until then the script draws a boxed placeholder that says so, and writes it as the
figure; the manifest records ``pending: true``.  With the arms stored it draws, on the complete SPY series
(``full_spy``): (a) the detection rate by year of the rule (black line), of Llama 3.1 8B with the verdict first (open
markers; 100% in every year) and with the reasoning field first (filled markers), with gpt-oss-20b as a thin reference
line; (b) for each arm, the share of answers whose reported mean absolute GEX lies within 5% of the value computed from
the window, with the verdict first and with the reasoning first.

Input  results/detection_by_year.csv (arms llama_full_spy, llamarf_full_spy, oss_full_spy; classifier rows of new_full);
  results/reported_vs_computed.csv (basis arm, scope all: ratio_within_5pct_pct of llama_* and llamarf_* arms).
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
from matplotlib.patches import Rectangle

import figopen  # first: it puts the Electronics figure modules on sys.path
import figdata  # noqa: E402
import theme  # noqa: E402

FIG_ID = "bf05_llama_schema_order"
RESULTS_FILES = ("detection_by_year.csv", "reported_vs_computed.csv")
TABLE_KINDS: Sequence[str] = ()
PENDING_ARMS = ("llamarf_full_spy",)  # run_all.py reports the figure as pending while these arms are missing
HEIGHT_IN = 3.0
YEARS = tuple(range(2008, 2027))


def placeholder(fig) -> None:
    ax = fig.add_subplot(1, 1, 1)
    ax.axis("off")
    ax.add_patch(Rectangle((0.02, 0.06), 0.96, 0.88, transform=ax.transAxes, fill=False,
                                                            edgecolor=theme.MUTED, linewidth=0.9, linestyle=(0, (4, 2))))
    ax.text(0.5, 0.58, "Pending run: Llama 3.1 8B with the reasoning field first", transform=ax.transAxes, ha="center", va="center",
            fontsize=9, fontweight="bold", color=theme.INK)
    ax.text(0.5, 0.40, "Arms llamarf_* are not stored yet. The figure compares them with the verdict-first arms llama_*.",
            transform=ax.transAxes, ha="center", va="center", fontsize=8, color=theme.INK_SECONDARY)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figopen.parse_args(FIG_ID, __doc__, argv)
    inputs = figdata.Inputs(FIG_ID, args.results_dir, args.tables_dir)
    detection = figopen.load_detection(inputs)
    by_arm = figopen.llm_all(detection)
    fig = theme.new_figure(HEIGHT_IN)
    if not all(arm in by_arm.index for arm in PENDING_ARMS):
        placeholder(fig)
        figopen.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, {"pending": True, "missing_arms": list(PENDING_ARMS)})
        return 0

    reported = inputs.csv("reported_vs_computed.csv", ["basis", "arm", "arm_role", "scope", "year", "ratio_within_5pct_pct"])
    ax_year, ax_gex = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.5, 1.0]})
    rule = figopen.rule_years(detection, "new_full")
    years = [y for y in YEARS if y in rule.index]
    ax_year.plot(years, [100.0 * rule.loc[y, "n_detect"] / rule.loc[y, "n"] for y in years], color=theme.INK, linewidth=1.2, label="Rule (Paper A)")
    series = (("llama_full_spy", figopen.MODEL_BY_KEY["llama"], True), ("llamarf_full_spy", figopen.MODEL_BY_KEY["llamarf"], False))
    for arm, spec, hollow in series:
        frame = figopen.llm_years(detection, arm)
        ys = [100.0 * frame.loc[y, "n_detect"] / frame.loc[y, "n_parsed"] for y in years if y in frame.index]
        xs = [y for y in years if y in frame.index]
        ax_year.plot(xs, ys, linestyle="none", marker=spec.marker, markersize=4.4, markerfacecolor=theme.SURFACE if hollow else spec.color,
                     markeredgecolor=spec.color, markeredgewidth=0.9, clip_on=False, label=spec.label)
    oss = figopen.llm_years(detection, "oss_full_spy")
    ax_year.plot([y for y in years if y in oss.index], [100.0 * oss.loc[y, "n_detect"] / oss.loc[y, "n_parsed"] for y in years if y in oss.index],
                 color=figopen.MODEL_BY_KEY["oss"].color, linewidth=0.7, label="gpt-oss-20b")
    theme.percent_axis(ax_year, "y")
    ax_year.set_ylabel("Windows detected (%)")
    theme.year_axis(ax_year, years, step=3)
    ax_year.grid(axis="y", color=theme.GRID, linewidth=0.5)
    theme.panel_title(ax_year, "a", "Detection rate, complete SPY series")
    handles, labels = ax_year.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4, frameon=False, fontsize=8)

    arms = [a for a in figopen.ARMS if f"llamarf_{a}" in set(reported["arm"])]
    allrows = reported[(reported["basis"] == "arm") & (reported["scope"] == "all")].set_index("arm")["ratio_within_5pct_pct"]
    pos = np.arange(len(arms), dtype=float)
    for k, (prefix, spec, hollow) in enumerate((("llama_", figopen.MODEL_BY_KEY["llama"], True), ("llamarf_", figopen.MODEL_BY_KEY["llamarf"], False))):
        ax_gex.barh(pos + (k - 0.5) * 0.36, [float(allrows[prefix + a]) for a in arms], height=0.34, color=theme.SURFACE if hollow else spec.color,
                    edgecolor=spec.color, linewidth=0.9, zorder=3)
    ax_gex.set_yticks(pos)
    ax_gex.set_yticklabels([figopen.ARM_LABELS[a] for a in arms], fontsize=8)
    ax_gex.invert_yaxis()
    theme.percent_axis(ax_gex, "x")
    ax_gex.set_xlabel("Within 5% of computed (%)")
    ax_gex.grid(axis="x", color=theme.GRID, linewidth=0.5)
    theme.panel_title(ax_gex, "b", "Reported mean |GEX|")
    figopen.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, {"pending": False, "arms": arms})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
