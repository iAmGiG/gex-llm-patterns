#!/usr/bin/env python3
"""Self-checks of theme.py, figdata.py and fig04_classifier_replay.py against the real output of 05_report.py.

The checks never use synthetic result tables: 05_report.py is run on the pipeline's parquet copies (the real tables)
and every loader, the typography lint, the manifest and fig04 are tested on what it wrote.  Negative cases are copies
of that real detection_by_year.csv with one defect each (a missing required series, a repeated row, percent turned
into fractions, ...); each must stop the figure with a message, and nothing may be written.

Run (repository root, AutoGex env)::

    python docs/papers/electronics/figures/scripts/check_core.py
    python docs/papers/electronics/figures/scripts/check_core.py --parquet-root /path/to/tables --work-dir /tmp/check_core

Exit status 0 = every check passed, 1 = at least one failed, 2 = the checks could not run (no tables, 05_report.py failed).
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import yaml

import figdata
import theme
from theme import common

SCRIPTS = Path(__file__).resolve().parent
REPORT = theme.PIPELINE_DIR / "05_report.py"
FIG04 = SCRIPTS / "fig04_classifier_replay.py"

FAILS: List[str] = []
COUNT = 0


def check(name: str, ok: Any, detail: str = "") -> None:
    global COUNT
    COUNT += 1
    if not ok:
        FAILS.append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not ok else ""))


def expect_exit(name: str, fn: Callable[[], Any], contains: Sequence[str] = ()) -> None:
    """``fn`` must stop with SystemExit whose text holds every ``contains`` string."""
    global COUNT
    COUNT += 1
    try:
        fn()
    except SystemExit as exc:
        text = str(exc)
        ok = all(c in text for c in contains)
        if not ok:
            FAILS.append(name)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: SystemExit '{text[:150]}'")
        return
    except Exception as exc:  # noqa: BLE001
        FAILS.append(name)
        print(f"  [FAIL] {name}: raised {type(exc).__name__}: {exc}")
        return
    FAILS.append(name)
    print(f"  [FAIL] {name}: no exit")


def expect_raises(name: str, exc_type: type, fn: Callable[[], Any], contains: Sequence[str] = ()) -> None:
    global COUNT
    COUNT += 1
    try:
        fn()
    except exc_type as exc:
        ok = all(c in str(exc) for c in contains)
        if not ok:
            FAILS.append(name)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {exc_type.__name__} '{str(exc)[:120]}'")
        return
    except Exception as exc:  # noqa: BLE001
        FAILS.append(name)
        print(f"  [FAIL] {name}: raised {type(exc).__name__}: {exc}")
        return
    FAILS.append(name)
    print(f"  [FAIL] {name}: nothing raised")


def wilson(k: int, n: int, z: float = 1.959963984540054) -> Tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# --------------------------------------------------------------------------------------------------------- A. theme
def check_theme(work: Path) -> None:
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    print("== A. theme.py")

    def flagged(text: str) -> bool:
        fig = theme.new_figure(2.0)
        fig.add_subplot(1, 1, 1).set_title(text, fontsize=9)
        found = bool(theme.lint_figure(fig))
        plt.close(fig)
        return found

    cases = {  # text -> must be flagged by the typography lint
        "Day T-29": True, "Day T-29 to Day T-1": True, "T-1": True, "0-100%": True, "5-7B": True, "2-4pp": True,
        "10%-20%": True, "\\$5B-7B": True, "3bn-4bn": True,
        "2008-2019": True, "2024-25": True, "21-30 days": True, "-3.5": True, "(-5.2)": True,
        "Day T−29": False, "−3.5": False, "0–100%": False, "2008–2019": False, "o4-mini": False,
        "gpt-6-luna": False, "Rebuilt, ex-0DTE": False, "non-overlapping": False, "Day-T labels": False,
        "2026-10-09": False, "2026-10": False, "o4-mini-2025-04-16": False, "up to 2026-10-09.": False, "30-day windows": False,
    }
    for text, should in cases.items():
        check(f"lint {'flags' if should else 'passes'} {text!r}", flagged(text) == should)
    for size, word in ((7.0, "7 pt"), (9.5, "9.5 pt")):
        fig = theme.new_figure(2.0)
        fig.add_subplot(1, 1, 1).text(0.5, 0.5, "size", fontsize=size)
        check(f"lint flags {word} text", any("font size" in p for p in theme.lint_figure(fig)))
        plt.close(fig)

    check("um('Day T-29') -> typographic minus", theme.um("Day T-29") == "Day T−29")
    check("um keeps model names", theme.um("-5 and o4-mini") == "−5 and o4-mini")
    check("usd_b(-12.5): minus before the currency sign", theme.usd_b(-12.5) == "−\\$12.5B", theme.usd_b(-12.5))
    check("usd_b(5), usd_b(2.5, 2)", theme.usd_b(5) == "\\$5B" and theme.usd_b(2.5, 2) == "\\$2.50B")
    check("usd_b(-0.04, 1) carries no sign", theme.usd_b(-0.04, 1) == "\\$0.0B", theme.usd_b(-0.04, 1))
    check("signed()", theme.signed(12.64) == "+12.6" and theme.signed(-4.5) == "−4.5" and theme.signed(-0.04) == "0.0")

    fig = theme.new_figure(2.0)
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlim(0, 10)
    n0 = len(ax.texts)
    theme.threshold_line(ax, 5.0, "\\$5B", orientation="v")
    check("threshold_line(orientation='v', label=...) draws the label", len(ax.texts) == n0 + 1 and ax.texts[-1].get_text() == "\\$5B")
    theme.threshold_line(ax, 7.0, "left", orientation="v", ha="right")
    check("vertical label on the left side", ax.texts[-1].get_ha() == "right")
    n1 = len(ax.texts)
    theme.threshold_line(ax, 6.0, orientation="v")
    check("no label, no text", len(ax.texts) == n1)
    theme.threshold_line(ax, 3.0, "h label")
    check("horizontal label unchanged", ax.texts[-1].get_ha() == "right")
    expect_raises("threshold_line refuses an unknown orientation", ValueError, lambda: theme.threshold_line(ax, 1.0, orientation="x"), ("orientation",))
    check("threshold_line text passes the lint", not [p for p in theme.lint_figure(fig) if "hyphen" in p])
    plt.close(fig)

    # registry coverage under the current contract (common.SERIES / common.ARMS)
    gaps = theme.registry_gaps()
    check("theme covers every registered series and arm", not any(gaps.values()), str(gaps))
    for key in common.SERIES:
        theme.series_color(key), theme.series_marker(key), theme.series_label(key)
    for key in ("intraday_late", "intraday_t0"):
        theme.series_color(key), theme.series_marker(key), theme.series_label(key)
    check("series tokens resolve for the registry and the intraday aliases", True)
    check("every registered arm has a colour and a label", all(theme.arm_color(a) and theme.arm_label(a) in theme.ARM_LABELS.values() for a in common.ARMS))
    published = [a for a, v in common.ARMS.items() if not v.llm]
    check("published arms (llm=False) are grey", published and all(theme.arm_color(a) == theme.PUBLISHED_COLOR for a in published), str(published))
    check("series of one family keep one colour (dated twins)", theme.series_color("p3_2024") == theme.series_color("p3_2024_dated")
          and theme.series_color("p4_2020") == theme.series_color("p4_2020_dated"))
    distinct = {k: theme.series_color(k) for k in theme.SERIES_ORDER}
    check("the six daily series have six different colours and markers", len(set(distinct.values())) == 6
          and len({theme.series_marker(k) for k in theme.SERIES_ORDER}) == 6)
    check("SERIES_ORDER_ALL is the registry: every common.SERIES key but the alias, SERIES_ORDER first",
          set(theme.SERIES_ORDER_ALL) - {"intraday"} == set(common.SERIES) - {"intraday_late"}
          and theme.SERIES_ORDER_ALL[: len(theme.SERIES_ORDER)] == theme.SERIES_ORDER)
    check("base_arm: variants map to the registry arm", theme.base_arm("r1_o4mini_all") == "r1_o4mini" and theme.base_arm("bridge_jan#rep1") == "bridge_jan"
          and theme.base_arm("full_spy#rep12") == "full_spy" and theme.base_arm("r1_p3_o4mini_all") == "r1_p3_o4mini"
          and theme.base_arm("pilot_full") == "pilot_full")
    check("variants keep the colour of their arm", theme.arm_color("r1_o4mini_all") == theme.PUBLISHED_COLOR
          and theme.arm_color("bridge_jan#rep1") == theme.arm_color("bridge_jan") and theme.arm_color("p34_obf_2024#rep1") == theme.arm_color("p34_obf_2024")
          and theme.arm_color("r1_p3_o4mini_all") == theme.PUBLISHED_COLOR)
    expect_raises("an unknown arm is a KeyError with a message", KeyError, lambda: theme.arm_color("pilot_full"), ("not a registered arm",))
    expect_raises("an unknown series is a KeyError with a message", KeyError, lambda: theme.series_color("nope"), ("no colour token",))
    check("arm labels of variants", theme.arm_label("r1_o4mini_all").endswith("incl. recovered") and theme.arm_label("bridge_jan#rep1").endswith("(repeat)")
          and theme.arm_label("bridge_jan#rep2").endswith("(repeat 2)") and theme.arm_label("pilot_full") == "pilot_full"
          and theme.arm_label("bridge_jan") == "luna, published inputs")
    check("the repeat label of the contract is the one the theme reads", common.REPEAT_ARM_SUFFIX == "#rep1"
          and theme.registered_arm("bridge_jan" + common.REPEAT_ARM_SUFFIX).key == "bridge_jan")

    # style, geometry
    theme.apply_style()
    rc1 = dict(mpl.rcParams)
    theme.apply_style()
    check("apply_style is idempotent", dict(mpl.rcParams) == rc1)
    check("rcParams: unicode minus, 6.14 in, 300 dpi, white surface", mpl.rcParams["axes.unicode_minus"] is True and theme.FIG_WIDTH_IN == 6.14
          and mpl.rcParams["savefig.dpi"] == 300 and mpl.rcParams["figure.facecolor"] == "#FFFFFF")

    # row-major legend
    from matplotlib.patches import Patch

    for n_entries, ncol in ((6, 3), (5, 3), (4, 3), (7, 3), (2, 3), (6, 2)):
        fig = theme.new_figure(2.0)
        fig.add_subplot(1, 1, 1)
        labels = [f"entry{i}" for i in range(n_entries)]
        legend = fig.legend(*theme.row_major([Patch(facecolor="C0") for _ in labels], labels, ncol), loc="outside upper center", ncol=ncol)
        fig.canvas.draw()
        pos = {t.get_text(): t.get_window_extent() for t in legend.get_texts()}
        ys = sorted({round(b.y0) for b in pos.values()}, reverse=True)
        read = [name for y in ys for name, _ in sorted(((n, b) for n, b in pos.items() if round(b.y0) == y), key=lambda kv: kv[1].x0)]
        check(f"legend reads row by row for {n_entries} entries in {ncol} columns", read == labels, str(read))
        plt.close(fig)

    check("to_native: numpy, nan, path, date, set", theme.to_native({"a": np.int64(3), "b": float("nan"), "c": Path("/x"), "d": np.float64(1.5),
                                                                       "e": pd.Timestamp("2026-01-02"), "f": np.array([1, 2]), "g": {3, 1}})
          == {"a": 3, "b": None, "c": "/x", "d": 1.5, "e": "2026-01-02T00:00:00", "f": [1, 2], "g": [1, 3]})

    # save_figure refuses a bad width and a lint failure without writing
    tmp = Path(tempfile.mkdtemp(prefix="theme_", dir=work))
    theme.apply_style()
    bad = plt.figure(figsize=(5.0, 2.0))
    expect_raises("save_figure refuses a 5.0 in wide figure", ValueError, lambda: theme.save_figure(bad, "fig98", tmp), ("width",))
    plt.close(bad)
    bad = theme.new_figure(2.0)
    bad.add_subplot(1, 1, 1).text(0.5, 0.5, "Day T-29", fontsize=8)
    expect_raises("save_figure refuses 'Day T-29' and writes nothing", ValueError, lambda: theme.save_figure(bad, "fig97", tmp), ("hyphen",))
    check("no file written on refusal", not any(tmp.iterdir()))
    plt.close(bad)
    shutil.rmtree(tmp)

    # provenance manifest
    tmp = Path(tempfile.mkdtemp(prefix="theme_", dir=work))
    fig = theme.new_figure(2.0)
    fig.add_subplot(1, 1, 1).bar([0, 1], [np.int64(3), 4])
    source = tmp / "source.csv"
    source.write_text("a,b\n1,2\n")

    class Args:
        output_dir = tmp
        no_pdf = False

    out = theme.finish(fig, "fig99_test", Args, [source], {"source.csv": 1}, {"n": np.int64(7), "nan": float("nan"), "path": Path("/a/b")})

    def no_constant(constant: str) -> None:
        raise ValueError(f"non-strict JSON constant {constant}")

    manifest = json.loads(out["json"].read_text(), parse_constant=no_constant)
    head = subprocess.run(["git", "-C", str(theme.REPO_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    check("manifest: strict JSON, extra converted", manifest["extra"] == {"n": 7, "nan": None, "path": "/a/b"}, str(manifest["extra"]))
    check("manifest: git_sha is HEAD, git_dirty and git_dirty_tracked are booleans", manifest["git_sha"] == head
          and isinstance(manifest["git_dirty"], bool) and isinstance(manifest["git_dirty_tracked"], bool))
    code = {c["path"]: c for c in manifest["code"]}
    here = theme.display_path(SCRIPTS)
    check("manifest: code lists theme.py, figdata.py (loaded by this check) and common.py with their sha256",
          {f"{here}/theme.py", f"{here}/figdata.py", "scripts/validation/electronics/common.py"} <= set(code)
          and all(common.sha256_file(theme.REPO_ROOT / p) == c["sha256"] for p, c in code.items()), str(sorted(code)))
    check("manifest: code git state is a known word", all(c["git"] in ("clean", "modified", "untracked", "ignored") for c in code.values()),
          str({p: c["git"] for p, c in code.items()}))
    check("manifest: versions of python, matplotlib, numpy, pandas, pyarrow, pyyaml, pillow",
          {"python", "matplotlib", "numpy", "pandas", "pyarrow", "pyyaml", "pillow"} <= set(manifest["versions"]))
    check("manifest: argv recorded", isinstance(manifest["argv"], list) and manifest["argv"])
    check("manifest: results is null when the folder has no report.yaml", manifest["results"] is None)
    check("results_provenance(None, ...) is None", theme.results_provenance(None, [source]) is None)
    broken = tmp / "broken"
    broken.mkdir()
    (broken / "report.yaml").write_text("files: [unclosed\n")
    theme.logger.setLevel(logging.CRITICAL)  # the warning that this case provokes is the expected outcome
    try:
        unreadable = theme.results_provenance(broken, [broken / "report.yaml"]) or {}
    finally:
        theme.logger.setLevel(logging.NOTSET)
    check("an unreadable report.yaml is recorded as an error and does not stop the figure", "error" in unreadable)
    check("manifest: source sha256, row counts, PNG pixels (6.14 x 2.0 in at 300 dpi)", manifest["sources"][0]["sha256"] == common.sha256_file(source)
          and manifest["rows"] == {"source.csv": 1} and manifest["outputs"]["png"]["pixels"] == [1842, 600], str(manifest["outputs"]["png"]))
    shutil.rmtree(tmp)


# --------------------------------------------------------------------------------------------------------- B. figdata
def check_figdata(results: Path, tables: Path, work: Path) -> pd.DataFrame:
    print("== B. figdata.py (loaders on the CSV written by the real 05_report.py)")
    inputs = figdata.Inputs("figT", results, tables)
    detection = figdata.load_detection_by_year(inputs)
    raw = pd.read_csv(results / "detection_by_year.csv")
    yearly = raw[raw.scope == "year"]
    check("detection: one row per yearly CSV row, int years", len(detection) == len(yearly) and detection["year"].dtype.kind == "i", f"{len(detection)} vs {len(yearly)}")
    classifier = figdata.classifier_rates(detection)
    llm = figdata.llm_rates(detection)
    check("classifier_rates = the classifier rows (blank arm), llm_rates = the LLM rows with a rate", len(classifier) == int((yearly.label_source == "classifier").sum())
          and classifier["arm"].isna().all() and len(llm) == int(((yearly.label_source == "llm") & yearly.rate_pct.notna()).sum()))
    ok_c = ok_l = True
    for _, r in yearly.iterrows():
        if r.label_source == "classifier":
            row = classifier[(classifier.series_key == r.series_key) & (classifier.symbol == r.symbol) & (classifier.year == int(r.year))].iloc[0]
            ok_c &= abs(row.clf_rate * 100 - r.rate_pct) < 1e-9 and abs(row.clf_ci_lo * 100 - r.ci_lo_pct) < 1e-9 and row.n == r.n
            lo, hi = wilson(int(r.n_detect), int(r.n))
            ok_c &= abs(lo * 100 - r.ci_lo_pct) < 1e-4 and abs(hi * 100 - r.ci_hi_pct) < 1e-4
        elif not pd.isna(r.rate_pct):
            row = llm[(llm.arm == r.arm) & (llm.model == r.model) & (llm.series_key == r.series_key) & (llm.symbol == r.symbol) & (llm.year == int(r.year))].iloc[0]
            ok_l &= abs(row.llm_rate * 100 - r.rate_pct) < 1e-9 and row.n_parsed == r.n_parsed and row.n_windows == r.n_windows and row.arm_role == r.arm_role
            lo, hi = wilson(int(r.n_detect), int(r.n))
            ok_l &= abs(lo * 100 - r.ci_lo_pct) < 1e-4 and abs(hi * 100 - r.ci_hi_pct) < 1e-4
    check("classifier rows: rate and interval = CSV percent / 100 = an independent Wilson interval on n", bool(ok_c))
    check("llm rows: rate and interval = CSV percent / 100, Wilson on the parsed answers, n_windows, arm_role", bool(ok_l))
    fractions = detection[["clf_rate", "clf_ci_lo", "clf_ci_hi", "llm_rate", "llm_ci_lo", "llm_ci_hi"]].stack()
    check("all rates are fractions in [0, 1]", fractions.between(0, 1).all())
    check("the CSV was recorded once with its row count", list(inputs.rows.values()) == [len(raw)], str(inputs.rows))
    check("every arm of the file has a colour and a label in theme.py", all(theme.arm_color(a) and theme.arm_label(a) for a in llm["arm"].unique() if not str(a).startswith("pilot")),
          str(sorted(llm["arm"].unique())))

    # the published arm, with and without the answers recovered in 2026
    pub = detection[detection.arm == figdata.PUBLISHED_ARM]
    both = detection[detection.arm == figdata.PUBLISHED_ARM + figdata.ALL_SUFFIX]
    check("published arm r1_o4mini has arm_role backfill, r1_o4mini_all has backfill_all", set(pub.arm_role) == {"backfill"} and set(both.arm_role) <= {"backfill_all"})
    recovered = figdata.recovered_by_year(detection)
    if both.empty:
        check("recovered_by_year is None when the file has no r1_o4mini_all arm", recovered is None)
    else:
        check("recovered_by_year = n_parsed(r1_o4mini_all) - n_parsed(r1_o4mini)", recovered is not None and (
            recovered.reindex(sorted(both.year)).fillna(0).astype(int).to_numpy()
            == (both.set_index("year").n_parsed.sort_index() - pub.set_index("year").n_parsed.reindex(sorted(both.year)).fillna(0)).astype(int).to_numpy()).all())
    check("recovered_by_year is None for a symbol without an _all arm", figdata.recovered_by_year(detection, symbol="IWM") is None)
    check("published arms are the registered arms without a model, r1_o4mini among them", set(figdata.PUBLISHED_ARMS) == {a for a, v in common.ARMS.items() if not v.llm}
          and figdata.PUBLISHED_ARM in figdata.PUBLISHED_ARMS, str(figdata.PUBLISHED_ARMS))

    # windows each arm was scored on
    for key, arm in common.ARMS.items():
        check(f"window_series_of({key!r}) = common.arm_window_series", figdata.window_series_of(key, arm.series_key) == common.arm_window_series(arm))
    check("window_series_of: repeats, _all variants and pilots", figdata.window_series_of("intraday_spy#rep1", "intraday_late") == common.INTRADAY_T0_KEY
          and figdata.window_series_of("r1_o4mini_all", "jan2026_phase4a") == "jan2026_phase4a" and figdata.window_series_of("pilot_intraday_spy", "intraday_late") == common.INTRADAY_T0_KEY
          and figdata.window_series_of("pilot_bridge_jan", "jan2026_phase4a") == "jan2026_phase4a")
    intraday = detection[detection.arm == "intraday_spy"]
    if len(intraday):
        check("intraday_spy rows carry the classifier of the intraday_t0 windows", intraday.window_series_key.eq("intraday_t0").all() and intraday.clf_rate.notna().all())

    # intervals
    frame = pd.DataFrame({"clf_rate": [0.1, 0.5], "clf_ci_lo": [0.05, 0.4], "clf_ci_hi": [0.2, 0.6]})
    check("ci_columns: Wilson columns and label when there is no bootstrap", figdata.ci_columns(frame, "clf") == ("clf_ci_lo", "clf_ci_hi", figdata.WILSON_LABEL))
    boot = frame.assign(clf_boot_lo=[0.02, 0.3], clf_boot_hi=[0.3, 0.7])
    check("ci_columns: bootstrap columns and the quarter-block label only when both columns have values on every row",
          figdata.ci_columns(boot, "clf") == ("clf_boot_lo", "clf_boot_hi", figdata.BOOTSTRAP_LABEL) and "quarter-block bootstrap" in figdata.BOOTSTRAP_LABEL)
    check("ci_columns: a bootstrap column with a gap falls back to Wilson", figdata.ci_columns(boot.assign(clf_boot_hi=[0.3, np.nan]), "clf")[2] == figdata.WILSON_LABEL)
    check("ci_columns(method='wilson') ignores the bootstrap", figdata.ci_columns(boot, "clf", method="wilson")[2] == figdata.WILSON_LABEL)
    check("the Wilson label names no bootstrap", "bootstrap" not in figdata.WILSON_LABEL)
    expect_raises("ci_columns refuses an unknown method", ValueError, lambda: figdata.ci_columns(frame, "clf", method="x"))
    expect_raises("ci_columns: KeyError when the prefix has no interval", KeyError, lambda: figdata.ci_columns(frame, "llm"))
    check("whiskers in percent points", np.allclose(figdata.whiskers(frame, "clf_rate", "clf_ci_lo", "clf_ci_hi"), [[5, 10], [10, 10]]))
    index = pd.DataFrame({"clf_rate": [0.1, np.nan, 0.3]}, index=[2020, 2021, 2022])
    check("years_without finds NaN and absent years", figdata.years_without(index, [2020, 2021, 2022, 2023], "clf_rate") == [2021, 2023])
    two = pd.DataFrame({"year": [2020, 2020], "model": ["a", "b"], "symbol": ["SPY", "SPY"], "x": [1, 2]})
    expect_raises("one_per_year refuses a repeated year", ValueError, lambda: figdata.one_per_year(two, "arm t"), ("several rows per year", "('a', 'SPY')"))
    extra_model = detection[(detection.arm == "r1_o4mini") & (detection.year == 2024)].assign(model="other-model")
    check("llm_rates keeps both models of an arm (nothing dropped silently)", len(figdata.llm_rates(pd.concat([detection, extra_model], ignore_index=True))) == len(llm) + 1)
    check("llm_rates(roles=...) selects by arm_role", set(figdata.llm_rates(detection, roles=["backfill"])["arm"]) <= set(figdata.PUBLISHED_ARMS)
          and set(figdata.llm_rates(detection, roles=["repeat"])["arm"]) == {a for a in llm["arm"].unique() if common.REPEAT_MARK in str(a)})

    # series comparison and bridge
    comparison = figdata.load_series_comparison(figdata.Inputs("figT", results, tables))
    raw_comparison = pd.read_csv(results / "series_comparison.csv")
    check("series_comparison: yearly rows, int year, Timestamp last_date, pair label", len(comparison) == int((raw_comparison.scope == "year").sum()) and comparison["year"].dtype.kind == "i"
          and pd.api.types.is_datetime64_any_dtype(comparison["last_date"]) and (comparison["pair"] == comparison["series_a"] + "_vs_" + comparison["series_b"]).all())
    check("series_comparison: the required columns are columns of the producer", set(figdata.SERIES_COMPARISON_REQUIRED) <= set(raw_comparison.columns))
    bridge = figdata.load_bridge_agreement(figdata.Inputs("figT", results, tables))
    raw_bridge = pd.read_csv(results / "bridge_agreement.csv")
    check("bridge: every row kept, year a nullable integer, empty on the all-years rows", len(bridge) == len(raw_bridge) and str(bridge["year"].dtype) == "Int64"
          and bridge.loc[bridge.scope == "all", "year"].isna().all() and bridge.loc[bridge.scope == "year", "year"].notna().all())
    check("bridge: the required columns are columns of the producer", set(figdata.BRIDGE_REQUIRED) <= set(raw_bridge.columns))
    ok = True
    for _, r in bridge.iterrows():
        k = figdata.cohen_kappa(r.n_ref_det_oth_det, r.n_ref_det_oth_not, r.n_ref_not_oth_det, r.n_ref_not_oth_not)
        ok &= bool(pd.isna(k)) if pd.isna(r.kappa) else abs(k - r.kappa) < 1e-5
    check("cohen_kappa reproduces the producer's kappa on every bridge row", bool(ok))
    check("kappa_defined is False wherever the producer's kappa is NaN", bool((figdata.kappa_defined(bridge) | bridge.kappa.isna() | (bridge.kappa == 0)).all()))

    # keys: every CSV read refuses a repeated key
    def variant(name: str, csv: str, mutate: Callable[[pd.DataFrame], pd.DataFrame]) -> figdata.Inputs:
        folder = work / "keys" / name
        folder.mkdir(parents=True)
        mutate(pd.read_csv(results / csv)).to_csv(folder / csv, index=False)
        return figdata.Inputs("figT", folder, tables)

    shutil.rmtree(work / "keys", ignore_errors=True)
    expect_exit("detection_by_year: a repeated row (classifier, all-years row) stops the loader", lambda: figdata.load_detection_by_year(
        variant("det_dup", "detection_by_year.csv", lambda f: pd.concat([f, f[f.scope == "all"].head(1)]))), ("repeats", "key"))
    expect_exit("detection_by_year: a repeated LLM row stops the loader", lambda: figdata.load_detection_by_year(
        variant("det_dup2", "detection_by_year.csv", lambda f: pd.concat([f, f[(f.label_source == "llm") & (f.scope == "year")].head(1)]))), ("repeats",))
    expect_exit("series_comparison: a repeated row stops the loader", lambda: figdata.load_series_comparison(
        variant("sc_dup", "series_comparison.csv", lambda f: pd.concat([f, f.head(1)]))), ("repeats", "series_a"))
    expect_exit("bridge_agreement: a repeated row stops the loader", lambda: figdata.load_bridge_agreement(
        variant("br_dup", "bridge_agreement.csv", lambda f: pd.concat([f, f.head(1)]))), ("repeats", "comparison"))
    expect_exit("bridge_agreement: a 'bridge' row with an '_all' reference is refused", lambda: figdata.load_bridge_agreement(variant(
        "br_all", "bridge_agreement.csv", lambda f: f.assign(ref_arm=f.ref_arm.where(f.comparison != "bridge", f.ref_arm + figdata.ALL_SUFFIX)))),
        ("bridge with an '_all' reference",))
    expect_exit("bridge_agreement: 'bridge_incl_recovered' without an '_all' reference is refused", lambda: figdata.load_bridge_agreement(variant(
        "br_incl", "bridge_agreement.csv", lambda f: f.assign(comparison=f.comparison.replace({"bridge": "bridge_incl_recovered"})))),
        ("bridge_incl_recovered without an '_all' reference",))
    expect_exit("bridge_agreement: a test_retest row whose other arm is no repeat is refused", lambda: figdata.load_bridge_agreement(variant(
        "br_rep", "bridge_agreement.csv", lambda f: f.assign(other_arm=f.other_arm.where(f.comparison != "test_retest", "p34_obf_2024")))),
        ("test_retest whose other arm",))
    expect_exit("a CSV read without a key refuses identical rows", lambda: variant("any_dup", "intraday.csv", lambda f: pd.concat([f, f.head(1)])).csv(
        "intraday.csv", ["window_end"]), ("repeats", "identical rows"))
    check("a CSV read without a key accepts distinct rows", len(figdata.Inputs("figT", results, tables).csv("intraday.csv", ["window_end"])) > 0)
    expect_exit("a required column is named when it is absent", lambda: figdata.load_series_comparison(
        variant("sc_col", "series_comparison.csv", lambda f: f.drop(columns=["sign_agree_pct"]))), ("lacks column", "sign_agree_pct"))
    expect_exit("the key columns are required too", lambda: variant("br_key", "bridge_agreement.csv", lambda f: f.drop(columns=["comparison"])).csv(
        "bridge_agreement.csv", ["scope"], key=figdata.BRIDGE_KEY), ("comparison",))

    def det_variant(name: str, mutate: Callable[[pd.DataFrame], pd.DataFrame]) -> figdata.Inputs:
        return variant(name, "detection_by_year.csv", mutate)

    expect_exit("a missing results file names the producer", lambda: figdata.load_detection_by_year(figdata.Inputs("figT", work / "nowhere", tables)), ("missing input", "05_report.py"))
    expect_exit("percent turned into fractions is refused", lambda: figdata.load_detection_by_year(det_variant("frac", lambda f: f.assign(
        rate_pct=f.rate_pct / 100, ci_lo_pct=f.ci_lo_pct / 100, ci_hi_pct=f.ci_hi_pct / 100))), ("rate_pct is not 100",))
    expect_exit("a rate above 100 percent is refused", lambda: figdata.load_detection_by_year(det_variant("x10", lambda f: f.assign(rate_pct=f.rate_pct * 10))), ("percent in [0, 100]",))
    expect_exit("a missing column is named", lambda: figdata.load_detection_by_year(det_variant("nocol", lambda f: f.drop(columns=["arm_role"]))), ("lacks column", "arm_role"))
    expect_exit("only all-years rows", lambda: figdata.load_detection_by_year(det_variant("allonly", lambda f: f[f.scope == "all"])), ("no yearly rows",))
    expect_exit("unknown label_source", lambda: figdata.load_detection_by_year(det_variant("src", lambda f: f.assign(label_source="x"))), ("label_source",))
    expect_exit("unknown scope", lambda: figdata.load_detection_by_year(det_variant("scope", lambda f: f.assign(scope=f.scope.replace({"all": "total"})))), ("scope value",))
    expect_exit("a yearly row without a year", lambda: figdata.load_detection_by_year(det_variant("noyear", lambda f: f.assign(year=f.year.where(f.index != 0)))), ("without a year",))
    expect_exit("an interval that excludes the rate", lambda: figdata.load_detection_by_year(det_variant("ci", lambda f: f.assign(ci_lo_pct=f.ci_lo_pct.where(f.index != 0, 99.9)))), ("inside",))
    expect_exit("an empty file", lambda: figdata.load_detection_by_year(det_variant("empty", lambda f: f.head(0))), ("no rows",))
    expect_exit("a classifier row with an arm", lambda: figdata.load_detection_by_year(det_variant("armclf", lambda f: f.assign(
        arm=f.arm.where(f.label_source != "classifier", "x")))), ("classifier row has an arm",))
    expect_exit("an LLM row without an arm", lambda: figdata.load_detection_by_year(det_variant("armllm", lambda f: f.assign(
        arm=f.arm.where(f.index != f[(f.label_source == "llm") & (f.scope == "year")].index[0], np.nan)))),
        ("classifier row has an arm or an llm row has none",))
    expect_exit("a text value in a numeric column", lambda: figdata.load_detection_by_year(det_variant("text", lambda f: f.assign(n=f.n.astype(object).where(f.index != 3, "many")))), ("not numbers",))
    expect_exit("one end of a bootstrap interval", lambda: figdata.load_detection_by_year(det_variant("bootone", lambda f: f.assign(rate_boot_lo_pct=f.rate_pct))), ("bootstrap interval needs both ends",))
    boot_inputs = det_variant("boot", lambda f: f.assign(rate_boot_lo_pct=f.ci_lo_pct, rate_boot_hi_pct=f.ci_hi_pct))
    with_boot = figdata.load_detection_by_year(boot_inputs)
    check("bootstrap percent columns come back as fractions named clf_/llm_boot_lo/hi", {"clf_boot_lo", "clf_boot_hi", "llm_boot_lo", "llm_boot_hi"} <= set(with_boot.columns)
          and np.allclose(with_boot.dropna(subset=["clf_boot_lo"])["clf_boot_lo"], with_boot.dropna(subset=["clf_boot_lo"])["clf_ci_lo"]))
    check("ci_columns then names the quarter-block bootstrap", figdata.ci_columns(figdata.classifier_rates(with_boot), "clf")[2] == figdata.BOOTSTRAP_LABEL
          and figdata.ci_columns(figdata.llm_rates(with_boot), "llm")[2] == figdata.BOOTSTRAP_LABEL)

    # report.yaml helpers
    yaml_inputs = figdata.Inputs("figT", results, tables)
    report = yaml_inputs.yaml("report.yaml")
    for kind in ("series", "windows", "detections"):
        coverage = figdata.report_coverage(yaml_inputs, report, kind)
        check(f"report_coverage({kind}) has first/last as Timestamps", pd.api.types.is_datetime64_any_dtype(coverage["first"]) and pd.api.types.is_datetime64_any_dtype(coverage["last"]))
    thresholds = figdata.classifier_thresholds(yaml_inputs)
    check("classifier_thresholds from report.yaml", thresholds == {"persistence": 0.7, "magnitude_bn": 5.0, "max_sign_flips": 5, "low_conviction_bn": 3.0}, str(thresholds))

    # YAML: a key repeated in one mapping is refused, the real files read as the plain loader reads them
    for name in ("report.yaml", "stats.yaml", "bridge_agreement.yaml", "cost_ledger.yaml"):
        if (results / name).is_file():
            with open(results / name) as handle:
                plain = yaml.safe_load(handle)
            check(f"{name}: the strict loader returns what yaml.safe_load returns", figdata.Inputs("figT", results, tables).yaml(name) == plain)
    broken = work / "yaml"
    broken.mkdir(parents=True, exist_ok=True)
    (broken / "report.yaml").write_text("a: 1\nb:\n  c: 2\n  c: 3\n")
    expect_exit("a key repeated in one YAML mapping is refused", lambda: figdata.Inputs("figT", broken, tables).yaml("report.yaml"), ("cannot be read as YAML", "twice"))
    (broken / "report.yaml").write_text("a: [1, 2\n")
    expect_exit("a YAML syntax error is refused with the file named", lambda: figdata.Inputs("figT", broken, tables).yaml("report.yaml"), ("report.yaml", "cannot be read as YAML"))
    (broken / "report.yaml").write_text("- 1\n- 2\n")
    expect_exit("a YAML file that is not a mapping is refused", lambda: figdata.Inputs("figT", broken, tables).yaml("report.yaml"), ("not a mapping",))

    # parquet tables: the duplicate guard reads the whole natural key
    print("== B2. Inputs.table")
    t = figdata.Inputs("figT", results, tables).table("series", ["net_gex"], series_keys=["new_full"], symbols=["SPY"])
    check("table(series, ['net_gex']) returns exactly that column", list(t.columns) == ["net_gex"] and len(t) > 1000, str(t.shape))
    t = figdata.Inputs("figT", results, tables).table("series", ["trading_date", "net_gex", "series_key"], series_keys=["new_full"], symbols=["SPY"])
    check("table keeps the requested order and tz-naive dates", list(t.columns) == ["trading_date", "net_gex", "series_key"] and t.trading_date.dt.tz is None)
    for kind, columns in (("series", ["net_gex"]), ("windows", ["clf_should_detect"]), ("detections", ["regime_detected"])):
        check(f"the real {kind} tables hold one row per natural key", len(figdata.Inputs("figT", results, tables).table(kind, columns)) > 0)
    dup = work / "dup_tables"
    shutil.rmtree(dup, ignore_errors=True)
    day = pd.Timestamp("2024-01-02").date()
    for kind, frame in {
        "series": pd.DataFrame({"series_key": ["a", "a"], "symbol": ["SPY", "SPY"], "trading_date": [day] * 2, "net_gex": [1.0, 2.0]}),
        "windows": pd.DataFrame({"series_key": ["a", "a"], "symbol": ["SPY", "SPY"], "window_end": [day] * 2, "clf_avg_magnitude": [1.0, 2.0]}),
        "detections": pd.DataFrame({"arm": ["x", "x"], "series_key": ["a", "a"], "symbol": ["SPY", "SPY"], "window_end": [day] * 2, "model": ["m", "m"],
                                    "prompt_version": ["v", "v"], "regime_detected": [True, False]}),
    }.items():
        (dup / kind).mkdir(parents=True)
        frame.to_parquet(dup / kind / "d.parquet", index=False)
    expect_exit("series duplicates are refused when only net_gex is requested", lambda: figdata.Inputs("figT", results, dup).table("series", ["net_gex"]), ("duplicate rows", "trading_date"))
    expect_exit("windows duplicates are refused when only a value column is requested", lambda: figdata.Inputs("figT", results, dup).table("windows", ["clf_avg_magnitude"]), ("duplicate rows",))
    expect_exit("detections duplicates are refused when only regime_detected is requested", lambda: figdata.Inputs("figT", results, dup).table("detections", ["regime_detected"]), ("duplicate rows", "prompt_version"))
    shutil.rmtree(dup)
    (dup / "detections").mkdir(parents=True)
    one = pd.DataFrame({"arm": ["x"], "series_key": ["a"], "symbol": ["SPY"], "window_end": [day], "model": ["m"], "prompt_version": ["v"], "regime_detected": [True]})
    one.to_parquet(dup / "detections" / "a.parquet", index=False)
    one.assign(arm="x" + common.REPEAT_ARM_SUFFIX).to_parquet(dup / "detections" / "b.parquet", index=False)
    r = figdata.Inputs("figT", results, dup).table("detections", ["arm", "regime_detected"])
    check("a repeat arm ('<arm>#rep1') is not a duplicate of its original", sorted(r.arm) == ["x", "x" + common.REPEAT_ARM_SUFFIX])
    one.to_parquet(dup / "detections" / "c.parquet", index=False)
    expect_exit("the same key in a second file is refused", lambda: figdata.Inputs("figT", results, dup).table("detections", ["regime_detected"]), ("duplicate rows",))
    shutil.rmtree(dup)
    (dup / "series").mkdir(parents=True)
    pd.DataFrame({"series_key": ["a"], "symbol": ["SPY"], "net_gex": [1.0]}).to_parquet(dup / "series" / "s.parquet", index=False)
    expect_exit("a table without a natural-key column is refused", lambda: figdata.Inputs("figT", results, dup).table("series", ["net_gex"]), ("lacks column", "trading_date"))
    expect_exit("no parquet files", lambda: figdata.Inputs("figT", results, work / "nowhere").table("series", ["net_gex"]), ("no parquet files",))
    expect_exit("a filter without matches", lambda: figdata.Inputs("figT", results, tables).table("series", ["net_gex"], series_keys=["no_such"]), ("hold no rows",))
    shutil.rmtree(dup)
    windows = figdata.Inputs("figT", results, tables).table("windows", ["window_end", "gex_sequence"], series_keys=["new_full"], symbols=["SPY"])
    matrix = figdata.sequence_matrix(windows.head(5))
    check("sequence_matrix: (n, 30) USD values from the stored gex_sequence", matrix.shape == (5, common.WINDOW_DAYS) and np.isfinite(matrix).all())
    return detection


# --------------------------------------------------------------------------------------------------------- C. fig04
def run_fig04(results: Path, output: Path, tables: Path) -> Tuple[int, str]:
    done = subprocess.run([sys.executable, str(FIG04), "--results-dir", str(results), "--tables-dir", str(tables), "--output-dir", str(output)],
                          capture_output=True, text=True)
    return done.returncode, (done.stderr or "") + (done.stdout or "")


def check_fig04(results: Path, tables: Path, work: Path) -> None:
    import matplotlib.pyplot as plt
    from PIL import Image

    print("== C. fig04_classifier_replay.py")
    raw = pd.read_csv(results / "detection_by_year.csv")
    base = work / "fig04"
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)

    def scenario(name: str, mutate: Optional[Callable[[pd.DataFrame], pd.DataFrame]]) -> Tuple[Path, Path]:
        folder = base / name / "results"
        folder.mkdir(parents=True)
        for item in results.glob("*"):
            if item.name != "detection_by_year.csv" and item.is_file():
                shutil.copy(item, folder / item.name)
        if mutate is None:  # byte for byte, so report.yaml still describes the file
            shutil.copy(results / "detection_by_year.csv", folder / "detection_by_year.csv")
        else:
            mutate(raw.copy()).to_csv(folder / "detection_by_year.csv", index=False)
        return folder, base / name / "out"

    def drop(series: str, years: Optional[Sequence[int]] = None, label: str = "classifier") -> Callable[[pd.DataFrame], pd.DataFrame]:
        def go(frame: pd.DataFrame) -> pd.DataFrame:
            hit = (frame.label_source == label) & (frame.series_key == series) & (frame.symbol == "SPY") & (frame.scope == "year" if years else True)
            if years:
                hit &= frame.year.isin(years)
            return frame[~hit]
        return go

    # the real figure
    folder, out = scenario("real", None)
    code, text = run_fig04(folder, out, tables)
    check("real results: fig04 exits 0 and writes png, pdf, json", code == 0 and {p.suffix for p in out.glob("fig04*")} == {".png", ".pdf", ".json"}, text[-300:])
    manifest = json.loads((out / "fig04_classifier_replay.json").read_text())
    with Image.open(out / "fig04_classifier_replay.png") as img:
        check("png: 6.14 in wide at 300 dpi, RGB", img.size[0] == 1842 and img.mode == "RGB" and abs(img.info["dpi"][0] - 300) < 0.5, f"{img.size} {img.mode} {img.info.get('dpi')}")
    extra = manifest["extra"]
    order = ["r1_o4mini", "jan2026_phase4a", "call_only", "old_bs", "new_ex0dte", "new_full"]
    spy = raw[(raw.symbol == "SPY") & (raw.scope == "year")]
    years = sorted(int(y) for y in spy[spy.arm == "r1_o4mini"].year)
    drawn = ["r1_o4mini"] + [k for k in order[1:] if k in set(spy[spy.label_source == "classifier"].series_key)]
    check("manifest: the bars, the published years, no gaps, Wilson label", extra["bars"] == drawn and extra["years"] == years and extra["gaps"] == {}
          and extra["absent_optional_series"] == [k for k in order[1:] if k not in drawn] and extra["ci"] == figdata.WILSON_LABEL, str(extra["bars"]))
    published = extra["published"]
    has_all = bool((raw.arm == "r1_o4mini_all").any())
    check("manifest: published arm r1_o4mini (arm_role backfill) and the recovered answers", published["arm"] == "r1_o4mini" and published["arm_role"] == ["backfill"]
          and (published["arm_with_recovered_answers"] == "r1_o4mini_all") == has_all
          and (not has_all or published["recovered_2026_total"] == sum(published["recovered_2026_by_year"].values())))
    sums = raw[(raw.arm == "r1_o4mini") & (raw.scope == "year")].n_parsed.sum()
    sums_all = raw[(raw.arm == "r1_o4mini_all") & (raw.scope == "year")].n_parsed.sum()
    check("manifest: published n_parsed total = the CSV; recovered = all - published", published["n_parsed_total"] == int(sums)
          and (published["recovered_2026_total"] == int(sums_all - sums) if has_all else published["recovered_2026_total"] is None),
          f"{published['n_parsed_total']} {sums} {published['recovered_2026_total']} {sums_all}")
    check("manifest: code sha256 of fig04, figdata.py, theme.py and common.py; git flags; versions", {Path(c["path"]).name for c in manifest["code"]} >= {
        "fig04_classifier_replay.py", "figdata.py", "theme.py", "common.py"} and all(len(c["sha256"]) == 64 for c in manifest["code"]) and "git_dirty" in manifest
          and {"numpy", "pandas", "pyarrow"} <= set(manifest["versions"]))
    check("manifest: source sha256 equals the CSV file", manifest["sources"][0]["sha256"] == common.sha256_file(folder / "detection_by_year.csv"))
    report = yaml.safe_load((folder / "report.yaml").read_text())
    provenance = manifest["results"]
    check("manifest: results ties the figure to report.yaml (sha256, generated_at, inputs_fingerprint) and to the CSV it read",
          provenance["report_yaml"]["sha256"] == common.sha256_file(folder / "report.yaml")
          and provenance["report_yaml"]["inputs_fingerprint"] == report["inputs_fingerprint"] == provenance["files"]["detection_by_year.csv"]["inputs_fingerprint"]
          and provenance["files"]["detection_by_year.csv"]["matches_report"] is True and provenance["files"]["detection_by_year.csv"]["sha256"] == manifest["sources"][0]["sha256"])

    # bar heights and whiskers read back from the Figure object
    import importlib.util

    spec = importlib.util.spec_from_file_location("fig04_under_test", FIG04)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fig04_under_test"] = module
    spec.loader.exec_module(module)
    captured: Dict[str, Any] = {}
    original_finish = theme.finish

    def capture(fig, fig_id, args, sources, rows, extra=None):
        captured["fig"] = fig
        captured["footnote"] = [t.get_text() for t in fig.texts]
        return {}

    theme.finish = capture
    theme.logger.setLevel(logging.ERROR)  # the in-process runs log what the subprocess runs log
    try:
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            rc = module.main(["--results-dir", str(folder), "--tables-dir", str(tables), "--output-dir", str(out)])
    finally:
        theme.finish = original_finish
        theme.logger.setLevel(logging.NOTSET)
    fig = captured["fig"]
    axis = fig.axes[0]
    bars = sorted((p for p in axis.patches), key=lambda p: p.get_x())
    expected: Dict[Tuple[str, int], float] = {}
    for key in ("jan2026_phase4a", "call_only", "old_bs", "new_ex0dte", "new_full"):
        for _, r in raw[(raw.label_source == "classifier") & (raw.series_key == key) & (raw.symbol == "SPY") & (raw.scope == "year") & raw.year.isin(years)].iterrows():
            expected[(key, int(r.year))] = float(r.rate_pct)
    for _, r in raw[(raw.arm == "r1_o4mini") & (raw.scope == "year")].iterrows():
        expected[("r1_o4mini", int(r.year))] = float(r.rate_pct)
    published_rates = [round(expected[("r1_o4mini", y)], 1) for y in years]
    check("the first bar reproduces the published rates by year (12.2, 3.7, 32.4, 20.2, 100, 100 percent)", years == list(range(2020, 2026))
          and published_rates == [12.2, 3.7, 32.4, 20.2, 100.0, 100.0], str(published_rates))
    heights = sorted(round(p.get_height(), 6) for p in bars)
    check(f"bar heights are exactly the CSV rates ({len(expected)} bars)", rc == 0 and len(bars) == len(expected) and heights == sorted(round(v, 6) for v in expected.values()),
          f"{len(bars)} bars, rc {rc}")
    # each bar sits at its (year, series) slot: slots left to right inside a year are the legend order
    slot = {}
    for p in bars:
        year = round(p.get_x() + p.get_width() / 2)
        slot.setdefault(year, []).append(round(p.get_height(), 6))
    check("bars inside each year follow the legend order", all(slot[y] == [round(expected[(k, years[y])], 6) for k in drawn] for y in slot), str(slot)[:200])
    foot = " ".join(captured["footnote"])
    check("footnote: interval, non-overlapping windows, parsed 1,412 of 1,476 and the answers re-parsed in 2026", "Wilson 95% CI" in foot and "non-overlapping" in foot
          and f"{int(sums):,} of" in foot and f"the {int(sums_all - sums):,} answers re-parsed in 2026 are not drawn" in foot, foot[:400])
    plt.close(fig)

    # defects of the input: each stops the figure and writes nothing
    def stops(name: str, mutate: Callable[[pd.DataFrame], pd.DataFrame], contains: Sequence[str]) -> None:
        folder_, out_ = scenario(name, mutate)
        code_, text_ = run_fig04(folder_, out_, tables)
        files = list(out_.glob("*")) if out_.exists() else []
        check(f"{name}: exit 1 with the cause named, nothing written", code_ == 1 and all(c in text_ for c in contains) and not files,
              f"exit {code_}, files {[f.name for f in files]}, text {text_[-250:]!r}")

    stops("req_gap_new_full_2025", drop("new_full", [2025]), ("new_full", "2025", "year(s)"))
    stops("req_gap_jan_2021", drop("jan2026_phase4a", [2021]), ("jan2026_phase4a", "2021"))
    stops("req_gap_ex0dte_all_years", lambda f: drop("new_ex0dte")(f), ("new_ex0dte", "lacks classifier rows"))
    stops("published_missing", lambda f: f[f.arm != "r1_o4mini"], ("r1_o4mini", "published labels are the reference"))
    stops("published_year_missing", lambda f: f[~((f.arm == "r1_o4mini") & (f.year == 2022))], ("no row for year(s) [2022]",))
    stops("published_unanswered", lambda f: f.assign(n_parsed=f.n_parsed.where(~((f.arm == "r1_o4mini") & (f.year == 2023) & (f.scope == "year")), 0),
                                                       n=f.n.where(~((f.arm == "r1_o4mini") & (f.year == 2023) & (f.scope == "year")), 0),
                                                       n_detect=f.n_detect.where(~((f.arm == "r1_o4mini") & (f.year == 2023) & (f.scope == "year")), 0),
                                                       rate_pct=f.rate_pct.where(~((f.arm == "r1_o4mini") & (f.year == 2023) & (f.scope == "year")), np.nan),
                                                       ci_lo_pct=f.ci_lo_pct.where(~((f.arm == "r1_o4mini") & (f.year == 2023) & (f.scope == "year")), np.nan),
                                                       ci_hi_pct=f.ci_hi_pct.where(~((f.arm == "r1_o4mini") & (f.year == 2023) & (f.scope == "year")), np.nan)),
          ("no parsed answer in year(s) [2023]",))
    stops("published_role", lambda f: f.assign(arm_role=f.arm_role.where(f.arm != "r1_o4mini", "backfill_all")), ("arm_role", "backfill_all"))
    stops("units_fractions", lambda f: f.assign(rate_pct=f.rate_pct / 100, ci_lo_pct=f.ci_lo_pct / 100, ci_hi_pct=f.ci_hi_pct / 100), ("rate_pct is not 100",))
    stops("duplicate_row", lambda f: pd.concat([f, f[f.scope == "year"].head(1)]), ("repeats",))
    stops("column_missing", lambda f: f.drop(columns=["n_indep_30d"]), ("lacks column", "n_indep_30d"))
    stops("all_arm_smaller_than_published", lambda f: f[~((f.arm == "r1_o4mini_all") & (f.year == 2022))], ("more answers than r1_o4mini_all", "[2022]"))
    stops("two_models_published", lambda f: pd.concat([f, f[(f.arm == "r1_o4mini") & (f.scope == "year") & (f.year == 2024)].assign(model="other-model")]),
          ("several rows per year", "other-model"))

    # optional series and the all-years variant: drawn when present, named when not
    def runs(name: str, mutate: Callable[[pd.DataFrame], pd.DataFrame]) -> Tuple[Dict[str, Any], str]:
        folder_, out_ = scenario(name, mutate)
        code_, text_ = run_fig04(folder_, out_, tables)
        if code_ != 0:
            check(f"{name}: exit 0", False, text_[-300:])
            return {}, ""
        data = json.loads((out_ / "fig04_classifier_replay.json").read_text())
        with Image.open(out_ / "fig04_classifier_replay.png") as img:
            img.load()
        return data["extra"], text_

    extra_gap, _ = runs("opt_gap_call_only_2022", drop("call_only", [2022]))
    check("optional gap: exit 0, call_only/2022 in extra.gaps, the bar is not drawn", extra_gap.get("gaps") == {"call_only": [2022]} and extra_gap["absent_optional_series"] == [])
    extra_absent, _ = runs("opt_absent_old_bs", drop("old_bs"))
    check("optional series absent: listed in extra.absent_optional_series, five bars", extra_absent.get("absent_optional_series") == ["old_bs"] and len(extra_absent["bars"]) == 5)
    extra_noall, _ = runs("no_all_arm", lambda f: f[f.arm != "r1_o4mini_all"])
    check("no r1_o4mini_all arm: exit 0, recovered answers reported as none", extra_noall["published"]["arm_with_recovered_answers"] is None and extra_noall["published"]["recovered_2026_total"] is None)
    extra_boot, _ = runs("boot_all", lambda f: f.assign(rate_boot_lo_pct=f.ci_lo_pct, rate_boot_hi_pct=f.ci_hi_pct))
    check("bootstrap columns on every row: the figure says quarter-block bootstrap", extra_boot.get("ci") == figdata.BOOTSTRAP_LABEL, str(extra_boot.get("ci")))
    changed = json.loads((base / "boot_all" / "out" / "fig04_classifier_replay.json").read_text())["results"]["files"]["detection_by_year.csv"]
    check("a CSV changed after 05_report.py wrote it is recorded (matches_report false), the figure is still drawn", changed["matches_report"] is False)
    folder_, out_ = scenario("no_report_yaml", None)
    (folder_ / "report.yaml").unlink()
    code_, text_ = run_fig04(folder_, out_, tables)
    check("without report.yaml fig04 is still drawn and its manifest says results: null", code_ == 0
          and json.loads((out_ / "fig04_classifier_replay.json").read_text())["results"] is None, text_[-200:])
    extra_plain, _ = runs("no_boot", lambda f: f)
    check("without bootstrap columns the figure says Wilson", extra_plain.get("ci") == figdata.WILSON_LABEL)
    extra_mixed, _ = runs("boot_llm_only", lambda f: f.assign(rate_boot_lo_pct=f.ci_lo_pct.where(f.label_source == "llm", np.nan), rate_boot_hi_pct=f.ci_hi_pct.where(f.label_source == "llm", np.nan)))
    check("bootstrap on the LLM rows only: every bar is drawn with the Wilson interval and says so", extra_mixed.get("ci") == figdata.WILSON_LABEL, str(extra_mixed.get("ci")))

    # a footnote that names what is not drawn
    folder_, out_ = scenario("footnote_gap", drop("call_only", [2022]))
    module2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module2)
    theme.finish = capture
    theme.logger.setLevel(logging.ERROR)
    try:
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            module2.main(["--results-dir", str(folder_), "--tables-dir", str(tables), "--output-dir", str(out_)])
    finally:
        theme.finish = original_finish
        theme.logger.setLevel(logging.NOTSET)
    foot2 = " ".join(captured["footnote"])
    check("footnote names the bar that is not drawn", "Not drawn: Rule, call leg only in 2022." in foot2, foot2[-200:])
    plt.close(captured["fig"])

    # --help, empty results
    done = subprocess.run([sys.executable, str(FIG04), "--help"], capture_output=True, text=True)
    check("--help works and names the long schema", done.returncode == 0 and "label_source" in done.stdout and "r1_o4mini_all" in done.stdout)
    code_, text_ = run_fig04(base / "nowhere", base / "nowhere_out", tables)
    check("a missing results folder names 05_report.py", code_ == 1 and "05_report.py" in text_ and not (base / "nowhere_out").exists())


# --------------------------------------------------------------------------------------------------------- main
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--parquet-root", type=Path, default=common.PARQUET_ROOT, help="folder with series/ windows/ detections/ runs/ (default: %(default)s)")
    parser.add_argument("--work-dir", type=Path, default=None, help="scratch folder (default: a new temporary folder, removed at the end)")
    parser.add_argument("--keep", action="store_true", help="keep the scratch folder")
    parser.add_argument("--results-dir", type=Path, default=None, help="use this folder of 05_report.py output instead of running 05_report.py")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    work = args.work_dir or Path(tempfile.mkdtemp(prefix="check_core_"))
    work.mkdir(parents=True, exist_ok=True)
    try:
        if args.results_dir is None:
            if not (args.parquet_root / "windows").is_dir():
                print(f"no result tables under {args.parquet_root} (01-04 write them)", file=sys.stderr)
                return 2
            results = work / "results"
            done = subprocess.run([sys.executable, str(REPORT), "--source", "parquet", "--parquet-root", str(args.parquet_root), "--results-dir", str(results)],
                                  capture_output=True, text=True)
            if done.returncode != 0:
                print(f"05_report.py exited {done.returncode}:\n{(done.stderr or done.stdout)[-1500:]}", file=sys.stderr)
                return 2
            print(f"05_report.py wrote {len(list(results.glob('*')))} files to {results}")
        else:
            results = args.results_dir
        check_theme(work)
        check_figdata(results, args.parquet_root, work)
        check_fig04(results, args.parquet_root, work)
    finally:
        if not args.keep and args.work_dir is None:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n{COUNT - len(FAILS)} of {COUNT} checks passed" + (f"; FAILED: {FAILS}" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
