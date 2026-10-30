#!/usr/bin/env python3
"""Fidelity of the model answers to the deterministic rule: verdict agreement by year, and the numbers behind each verdict.

Both models (o4-mini, gpt-6-luna) are asked to apply the Paper 2 criteria to a 30-day window and to report the
numbers they used.  Panels (a) and (b) compare each verdict (regime_detected) with the rule on the same window, by
series and year: accuracy and Cohen's kappa (not drawn, and marked, where the rule or the model gives one label for
the whole year, because kappa then says nothing).  Panels (c) to (e) compare the reported persistence, mean |GEX| and
sign-flip count with the values the rule computes from the same 30 numbers.  They plot the difference (reported minus
computed) against the computed value, because a deviation from the identity line is hard to see on a reported-versus-computed
scatter; the grey band is the tolerance of ``metrics_agree`` (0.5 percentage points, $0.05B; sign flips must be exact), the
light vertical band the borderline region around each threshold (21 of 30 days, $5B, 5 flips) and a red mark a report outside
the tolerance.  The sign-flip count is the field the probe found to be least reliable.

Input  results/detection_by_year.csv (read by figdata.load_detection_by_year()), results/report.yaml, and the
  detections and windows parquet copies
  * detection_by_year.csv, symbol SPY, arms r1_o4mini, bridge_jan, full_spy, ex0dte_spy and bridge_old (those that
    exist): n_compared, agree_pct, kappa, llm_rate, clf_rate_matched; the arms of QQQ and IWM add one sentence;
  * report.yaml: diagnostics.thresholds (the borderline bands);
  * detections parquet (arms r1_o4mini and every registered gpt-6-luna arm, parsed answers only): regime_detected,
    persistence_pct, avg_magnitude_billions, sign_flips; windows parquet: clf_should_detect, clf_persistence_pct,
    clf_avg_magnitude, clf_sign_flips of the window each answer scored (intraday answers use the intraday_t0 windows).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

import figdata
import figllm
import theme
from theme import common

FIG_ID = "fig07_llm_classifier_fidelity"
RESULTS_FILES = ("detection_by_year.csv", "report.yaml")
TABLE_KINDS: Sequence[str] = ("detections", "windows")
SYMBOL = "SPY"
YEAR_ARMS = (figllm.PUBLISHED_ARM, "bridge_jan", "full_spy", "ex0dte_spy", "bridge_old")  # drawn in panels (a) and (b)
CROSS_ARMS = ("full_qqq", "ex0dte_qqq", "full_iwm", "ex0dte_iwm")
ARM_MARKERS = {figllm.PUBLISHED_ARM: "o"}
GROUP_COLORS = {"o4-mini": theme.PUBLISHED_COLOR, "luna": theme.LUNA_COLOR}
GROUP_LABELS = {"o4-mini": "o4-mini answers", "luna": "gpt-6-luna answers"}
# metrics_agree tolerance: the same inequalities as common.metrics_agree (|reported - computed| <= tolerance)
PERSISTENCE_TOL_PP, MAGNITUDE_TOL_BN = 0.5, 0.05
BORDERLINE_MAGNITUDE = 0.10  # within 10% of the magnitude threshold
MAGNITUDE_AXIS_TOLERANCES = 5  # panel (d) shows errors up to this many tolerances; larger ones sit on the frame


def size_of(count: np.ndarray) -> np.ndarray:
    """Marker area (pt^2) that grows with the log of the number of identical answers."""
    return 5.0 + 9.0 * np.log10(np.maximum(count, 1))


def lattice(x: np.ndarray, error: np.ndarray, group: np.ndarray, digits: int) -> pd.DataFrame:
    """Count of answers per (computed value, reported minus computed, model group) cell."""
    cells = pd.DataFrame({"x": np.round(x, digits), "error": np.round(error, digits), "group": group})
    return cells.groupby(["x", "error", "group"], sort=False).size().rename("n").reset_index()


def draw_lattice(ax, cells: pd.DataFrame, tolerance: float) -> None:
    """Residual scatter of discrete values: marker area ~ log count, red ring where |error| exceeds ``tolerance``."""
    cells = cells.assign(area=size_of(cells["n"].to_numpy()), off=cells["error"].abs() > tolerance)
    cells = cells.sort_values("area", ascending=False, kind="stable")  # small markers on top of large ones
    ax.scatter(cells["x"], cells["error"], s=cells["area"], c=cells["group"].map(GROUP_COLORS), linewidths=0.3, edgecolors=theme.SURFACE,
               zorder=3)
    off = cells[cells["off"]]
    if len(off):
        ax.scatter(off["x"], off["error"], s=off["area"] + 22, facecolors="none", edgecolors=theme.NEGATIVE, linewidths=0.9, zorder=4)


def tolerance_band(ax, tolerance: float) -> None:
    """Grey band of the accepted error around the zero line."""
    ax.axhspan(-tolerance, tolerance, color=theme.GRID, zorder=0.5, linewidth=0)
    ax.axhline(0.0, color=theme.BASELINE, linewidth=0.8, zorder=1)


def within(error: np.ndarray, tolerance: float) -> float:
    """Percent of the reports whose absolute error is at most ``tolerance``."""
    return 100.0 * float((np.abs(error) <= tolerance).mean()) if len(error) else float("nan")


def kappa_informative(frame: pd.DataFrame) -> pd.Series:
    """True where neither the rule (on the compared windows) nor the model gives one label for the whole year."""
    varies = lambda rate: rate.notna() & (rate > 0.0) & (rate < 1.0)  # noqa: E731
    return varies(frame["clf_rate_matched"]) & varies(frame["llm_rate"])


def draw_years(ax_acc, ax_kappa, drawn: Sequence[Tuple[str, pd.DataFrame]], years: Sequence[int]):
    """Panels (a) and (b): one line per arm; returns the legend handles and the numbers for the manifest."""
    handles: List[Line2D] = []
    summary: Dict[str, dict] = {}
    accuracy_min, kappa_min = 100.0, 1.0
    for arm, frame in drawn:
        color = theme.arm_color(arm)
        marker = ARM_MARKERS.get(arm, theme.series_marker(common.ARMS[arm].series_key))
        agree = figllm.on_years(frame, years, "agree_pct")
        kappa = figllm.on_years(frame, years, "kappa")
        informative = kappa_informative(frame).reindex(list(years), fill_value=False).to_numpy(bool) & ~np.isnan(kappa)
        style = dict(color=color, marker=marker, markersize=3.6, linewidth=1.1, markeredgecolor=theme.SURFACE, markeredgewidth=0.5, clip_on=False)
        ax_acc.plot(years, agree, zorder=3, **style)
        ax_kappa.plot(years, np.where(informative, kappa, np.nan), zorder=3, **style)
        accuracy_min = min(accuracy_min, float(np.nanmin(agree)))
        if informative.any():
            kappa_min = min(kappa_min, float(np.nanmin(kappa[informative])))
        handles.append(figllm.line_handle(color, marker, theme.arm_label(arm)))
        summary[arm] = {"accuracy_pct": dict(zip(years, agree, strict=True)),
                        "kappa": dict(zip(years, np.where(informative, kappa, np.nan), strict=True)),
                        "kappa_not_informative_years": [int(y) for y, ok, a in zip(years, informative, agree, strict=True)
                                                        if not ok and not np.isnan(a)]}
    floor = float(min(95.0, 5.0 * np.floor((accuracy_min - 1.0) / 5.0)))
    ax_acc.set_ylim(floor, 100.6)
    ax_acc.set_yticks(np.arange(floor, 100.1, 5.0 if floor >= 80 else 10.0))
    k_floor = float(min(0.5, np.floor((kappa_min - 0.03) * 10.0) / 10.0))
    ax_kappa.set_ylim(k_floor, 1.04)
    ax_kappa.set_yticks([t for t in np.arange(-1.0, 1.01, 0.25 if (1.0 - k_floor) > 0.6 else 0.1) if k_floor <= t <= 1.0])
    for arm, _ in drawn:  # not informative: a cross on the floor of panel (b), in the arm's colour
        marks = np.asarray(summary[arm]["kappa_not_informative_years"], dtype=float)
        if marks.size:
            ax_kappa.plot(marks, np.full(marks.size, k_floor + 0.025), linestyle="none", marker="x", markersize=3.4, markeredgewidth=0.8,
                          color=theme.arm_color(arm), clip_on=False, zorder=4)
    handles.append(Line2D([0], [0], linestyle="none", marker="x", markersize=3.6, markeredgewidth=0.8, color=theme.MUTED,
                          label="kappa not drawn: one label all year"))
    return handles, summary


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = figllm.parse_args(FIG_ID, __doc__, argv)
    inputs = figllm.open_inputs(FIG_ID, args)
    detection = figdata.load_detection_by_year(inputs)
    thresholds = figdata.classifier_thresholds(inputs)
    pairs, answer_counts = figllm.load_answer_pairs(inputs, figllm.registered_llm_arms())

    # ---- (a), (b): yearly rows of the SPY arms that exist
    drawn: List[Tuple[str, pd.DataFrame]] = []
    for arm in YEAR_ARMS:
        frame = figllm.arm_by_year(inputs, detection, arm)
        frame = frame[frame["symbol"] == SYMBOL] if len(frame) else frame
        if len(frame) and frame["agree_pct"].notna().any():
            drawn.append((arm, frame))
    if not drawn:
        inputs.fail(f"detection_by_year.csv has no yearly agree_pct for any {SYMBOL} LLM arm {YEAR_ARMS} "
                    "(05_report.py needs the windows of the scored series to compare verdicts)")
    years = sorted({int(y) for _, f in drawn for y in f.index})

    fig = theme.new_figure(6.15)
    grid = fig.add_gridspec(4, 3, height_ratios=[1.0, 0.95, 0.2, 1.75])
    ax_acc = fig.add_subplot(grid[0, :])
    ax_kappa = fig.add_subplot(grid[1, :], sharex=ax_acc)
    ax_key = fig.add_subplot(grid[2, :])
    ax_per, ax_mag, ax_flip = (fig.add_subplot(grid[3, j]) for j in range(3))
    handles, yearly = draw_years(ax_acc, ax_kappa, drawn, years)
    ax_acc.set_ylabel("Accuracy (%)")
    ax_kappa.set_ylabel("Cohen's kappa")
    theme.panel_title(ax_acc, "a", "Verdict agreement with the rule, SPY, by year")
    theme.panel_title(ax_kappa, "b", "Chance-corrected agreement, SPY, by year")
    for ax in (ax_acc, ax_kappa):
        theme.style_grid(ax)
    theme.year_axis(ax_kappa, years, step=1 if len(years) <= 10 else 2)
    ax_acc.tick_params(labelbottom=False)
    fig.legend(handles=handles, loc="outside upper center", ncol=3, columnspacing=1.2)

    # ---- (c)-(e): reported against computed values
    groups = [g for g in ("o4-mini", "luna") if (pairs["group"] == g).any()]
    pairs = pairs.assign(computed_persistence=pairs["clf_persistence_pct"], computed_magnitude=pairs["clf_avg_magnitude"] / 1e9)
    clf_days = int(common.WINDOW_DAYS * thresholds["persistence"])
    threshold_bn, flip_limit_rule = thresholds["magnitude_bn"], thresholds["max_sign_flips"]

    sub = pairs[pairs["persistence_pct"].notna()]  # persistence
    computed = sub["computed_persistence"].to_numpy(float)
    error = sub["persistence_pct"].to_numpy(float) - computed
    cells = lattice(computed, error, sub["group"].to_numpy(), 1)
    low, high = 100.0 * (clf_days - 1) / common.WINDOW_DAYS, 100.0 * (clf_days + 1) / common.WINDOW_DAYS
    step = 100.0 / common.WINDOW_DAYS  # one day, in percentage points
    reach = float(max(2.0 * step, np.ceil(np.abs(error).max() / step) * step + step))
    ax_per.axvspan(low, high, color=theme.PANEL_BG, zorder=0, linewidth=0)
    tolerance_band(ax_per, PERSISTENCE_TOL_PP)
    draw_lattice(ax_per, cells, PERSISTENCE_TOL_PP)
    ax_per.set(xlim=(46, 102), ylim=(-reach, reach), xticks=[50, 60, 70, 80, 90, 100])
    ax_per.set_xlabel("Computed persistence (%)")
    ax_per.set_ylabel("Reported minus computed (pp)")
    theme.panel_title(ax_per, "c", "Persistence")

    sub = pairs[pairs["avg_magnitude_billions"].notna()].sort_values("group", key=lambda s: s.map({"luna": 0, "o4-mini": 1}))  # mean |GEX|
    x = sub["computed_magnitude"].to_numpy(float)
    error = sub["avg_magnitude_billions"].to_numpy(float) - x
    colors = sub["group"].map(GROUP_COLORS).to_numpy()
    window = MAGNITUDE_AXIS_TOLERANCES * MAGNITUDE_TOL_BN  # larger errors sit on the frame as triangles and are counted
    inside = np.abs(error) <= window
    off = np.abs(error) > MAGNITUDE_TOL_BN
    ax_mag.axvspan(threshold_bn * (1 - BORDERLINE_MAGNITUDE), threshold_bn * (1 + BORDERLINE_MAGNITUDE), color=theme.PANEL_BG, zorder=0, linewidth=0)
    tolerance_band(ax_mag, MAGNITUDE_TOL_BN)
    ax_mag.scatter(x[inside & ~off], error[inside & ~off], s=3.2, c=colors[inside & ~off], alpha=0.45, linewidths=0, zorder=3, rasterized=True)
    ax_mag.scatter(x[inside & off], error[inside & off], s=5.5, color=theme.NEGATIVE, alpha=0.85, linewidths=0, zorder=4, rasterized=True)
    beyond_mag = ~inside
    for sign, marker in ((1.0, "^"), (-1.0, "v")):
        pick = beyond_mag & (np.sign(error) == sign)
        if pick.any():
            ax_mag.plot(x[pick], np.full(int(pick.sum()), sign * window), linestyle="none", marker=marker, markersize=3.4, color=theme.NEGATIVE,
                        alpha=0.85, clip_on=False, zorder=5)
    ax_mag.set(xlim=(0, float(x.max()) * 1.04), ylim=(-window * 1.08, window * 1.08))
    ax_mag.set_xlabel("Computed mean |GEX| (\\$B)")
    ax_mag.set_ylabel("Reported minus computed (\\$B)")
    theme.panel_title(ax_mag, "d", "Mean |GEX|")

    sub = pairs[pairs["sign_flips"].notna()]  # sign flips
    computed = sub["clf_sign_flips"].to_numpy(float)
    error = sub["sign_flips"].to_numpy(float) - computed
    cells = lattice(computed, error, sub["group"].to_numpy(), 0)
    flip_reach = float(max(2.0, np.abs(cells["error"]).max())) + 0.8
    ax_flip.axvspan(flip_limit_rule - 1, flip_limit_rule + 1, color=theme.PANEL_BG, zorder=0, linewidth=0)
    tolerance_band(ax_flip, 0.0)
    draw_lattice(ax_flip, cells, 0.0)
    ax_flip.set(xlim=(-0.8, float(cells["x"].max()) + 1.0), ylim=(-flip_reach, flip_reach))
    ax_flip.set_xlabel("Computed sign flips")
    ax_flip.set_ylabel("Reported minus computed")
    theme.panel_title(ax_flip, "e", "Sign flips")
    for ax in (ax_per, ax_mag, ax_flip):
        theme.style_grid(ax, "both")

    # ---- numbers behind the footnote
    stats: Dict[str, dict] = {}
    for g in groups:
        part = pairs[pairs["group"] == g]
        p, m, f = part[part["persistence_pct"].notna()], part[part["avg_magnitude_billions"].notna()], part[part["sign_flips"].notna()]
        e_p = (p["persistence_pct"] - p["computed_persistence"]).to_numpy(float)
        e_m = (m["avg_magnitude_billions"] - m["computed_magnitude"]).to_numpy(float)
        e_f = (f["sign_flips"] - f["clf_sign_flips"]).to_numpy(float)
        stats[g] = {"answers": int(len(part)), "persistence_within_tolerance_pct": within(e_p, PERSISTENCE_TOL_PP),
                    "magnitude_within_tolerance_pct": within(e_m, MAGNITUDE_TOL_BN), "sign_flips_exact_pct": within(e_f, 0.0),
                    "sign_flips_under_pct": 100.0 * float((e_f < 0).mean()) if len(e_f) else None,
                    "sign_flips_over_pct": 100.0 * float((e_f > 0).mean()) if len(e_f) else None,
                    "magnitude_beyond_frame": int((np.abs(e_m) > MAGNITUDE_AXIS_TOLERANCES * MAGNITUDE_TOL_BN).sum()),
                    "verdicts_equal_rule_pct": 100.0 * float((part["regime_detected"] == part["clf_should_detect"]).mean()),
                    "median_reported_over_computed_magnitude":
                        float(np.median(m["avg_magnitude_billions"] / m["computed_magnitude"])) if len(m) else None}
    beyond = sum(v["magnitude_beyond_frame"] for v in stats.values())

    ax_key.axis("off")
    key_handles = [Line2D([0], [0], linestyle="none", marker="o", markersize=4.2, color=GROUP_COLORS[g], label=GROUP_LABELS[g]) for g in groups]
    key_handles.append(Line2D([0], [0], linestyle="none", marker="o", markersize=6.2, markerfacecolor="none", markeredgecolor=theme.NEGATIVE,
                              markeredgewidth=0.9, label="Outside tolerance"))
    key_handles.append(figllm.patch_handle(theme.GRID, "Tolerance"))
    key_handles.append(figllm.patch_handle(theme.PANEL_BG, "Borderline region", edge=theme.BASELINE))
    ax_key.legend(handles=key_handles, loc="center", ncol=len(key_handles), columnspacing=1.2, borderaxespad=0.0)

    cross: Dict[str, float] = {}
    for arm in CROSS_ARMS:  # accuracy over all years of the QQQ and IWM arms, from the yearly rows
        frame = figllm.arm_by_year(inputs, detection, arm)
        if len(frame) and frame["n_compared"].fillna(0).sum() > 0:
            cross[arm] = float((frame["agree_pct"] * frame["n_compared"]).sum() / frame["n_compared"].sum())
    footnote = (f"(c){theme.ENDASH}(e): {len(pairs):,} parsed answers of all registered arms; reported minus the value the rule computes for the "
                f"same window, against the computed value (marker area grows with the log of the number of identical answers in (c) and (e)). "
                f"Light band: within one day of the {clf_days}-day persistence threshold, within 10% of {theme.usd_b(threshold_bn)}, "
                f"within one flip of the limit of {flip_limit_rule}. Reports inside the tolerance (persistence, mean |GEX|, exact sign flips): "
                + "; ".join(f"{g} {v['persistence_within_tolerance_pct']:.1f}%, {v['magnitude_within_tolerance_pct']:.1f}%, "
                            f"{v['sign_flips_exact_pct']:.1f}%" for g, v in stats.items()) + ".")
    if beyond:
        limit = theme.usd_b(MAGNITUDE_AXIS_TOLERANCES * MAGNITUDE_TOL_BN)
        footnote += f" In (d), {beyond:,} errors beyond \u00b1{limit} sit on the frame as triangles."
    if cross:
        footnote += " Accuracy on QQQ and IWM: " + ", ".join(f"{arm} {value:.1f}%" for arm, value in cross.items()) + "."
    if theme.PARTIAL_YEAR in years:
        footnote += " " + theme.PARTIAL_YEAR_NOTE
    theme.footnote(fig, footnote)
    extra = {
        "symbol": SYMBOL, "years": years, "arms_drawn": [arm for arm, _ in drawn], "yearly": yearly, "answers": answer_counts,
        "groups": stats,
        "borderline": {"persistence_pct": [low, high],
                       "magnitude_bn": [threshold_bn * (1 - BORDERLINE_MAGNITUDE), threshold_bn * (1 + BORDERLINE_MAGNITUDE)],
                       "sign_flips": [flip_limit_rule - 1, flip_limit_rule + 1]},
        "tolerance": {"persistence_pp": PERSISTENCE_TOL_PP, "magnitude_bn": MAGNITUDE_TOL_BN, "sign_flips": "exact"},
        "cross_asset_accuracy_pct": cross,
    }
    theme.finish(fig, FIG_ID, args, inputs.sources, inputs.rows, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
