"""Known-answer tests for stored_analyses.py (named *_check.py because .gitignore ignores test_*.py).

Run from the repository root with the AutoGex env::

    PYTHONNOUSERSITE=1 PYTHONPATH=$(pwd) python -m pytest -p no:cacheprovider scripts/validation/electronics/stored_analyses_check.py

The rule is checked against the real classifier (common.classify) on random windows and on hand-built boundary
cases; the resampling and the effective sample size against closed forms; the contested-window and lineage
definitions against small tables worked out by hand.  Nothing here reads the stored tables.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stored_analyses as sa  # noqa: E402

BN = 1e9


def seq(pos, neg, mag=10 * BN, dips=0, tail_neg=0):
    """30 values: ``pos`` positive days then ``neg`` negative ones (all of size ``mag``)."""
    return np.array([mag] * pos + [-mag] * neg, float)


def verdict(values, **kw):
    m = sa.window_metrics(values)
    return bool(sa.rule_verdict(m, **kw)[0])


def with_flips(k, mag=10 * BN):
    """30 values with exactly k sign flips and 27+ days of the majority sign (k = 5 -> 2 dips and one final negative day)."""
    v = np.full(30, mag)
    flips = 0
    i = 3
    while flips + 2 <= k - (k % 2):
        v[i] = -mag
        i += 3
        flips += 2
    if k % 2:
        v[29] = -mag
        flips += 1
    assert flips == k
    return v


# ---------------------------------------------------------------- the rule at its boundaries
def test_persistence_boundary_21_of_30():
    assert verdict(seq(21, 9))
    assert not verdict(seq(20, 10))
    assert verdict(seq(9, 21))  # persistent negative counts as detected too


def test_magnitude_boundary_is_inclusive():
    assert verdict(seq(30, 0, mag=5 * BN))  # mean |v| exactly 5e9
    assert not verdict(seq(30, 0, mag=5 * BN - 1.0))
    assert verdict(seq(30, 0, mag=5 * BN + 1.0))


def test_flip_limit_is_five():
    for k, expected in [(0, True), (4, True), (5, True), (6, False), (7, False)]:
        assert verdict(with_flips(k)) is expected, k
        assert sa.window_metrics(with_flips(k))["flips"][0] == k


def test_zero_counts_as_negative_day_and_as_its_own_sign():
    v = np.concatenate([np.full(9, 20 * BN), np.zeros(21)])
    m = sa.window_metrics(v)
    assert (m["pos"][0], m["neg"][0], m["flips"][0]) == (9, 21, 1)  # 9 positive, 21 zeros counted negative, one change
    assert verdict(v)  # 21 non-positive days, mean 6e9, one flip: persistent_negative in the classifier
    v2 = np.concatenate([np.full(20, 20 * BN), np.zeros(10)])
    assert not verdict(v2)  # 20 positive, 10 non-positive


def test_vectorised_rule_equals_the_classifier_on_random_windows():
    import common
    rng = np.random.default_rng(7)
    n_checked = 0
    for scale in (1e9, 6e9, 12e9):
        for p_pos in (0.5, 0.8, 0.95):
            x = rng.normal(0, scale, 400) * np.where(rng.random(400) < p_pos, 1, -1) * rng.choice([1, 1, 1, 0], 400)
            m = sa.window_metrics(x)
            ours = sa.rule_verdict(m)
            for i in range(0, len(m), 7):
                assert ours[i] == common.classify(x[i:i + 30])["should_detect"], (scale, p_pos, i)
                n_checked += 1
    assert n_checked > 200


def test_window_frame_dates_and_start():
    days = pd.DataFrame({"trading_date": pd.bdate_range("2020-01-01", periods=35), "net_gex": np.full(35, 6 * BN)})
    w = sa.window_frame(days)
    assert len(w) == 6
    assert w["window_start"].iloc[0] == days["trading_date"].iloc[0]
    assert w["window_end"].iloc[0] == days["trading_date"].iloc[29]
    assert w["window_end"].iloc[-1] == days["trading_date"].iloc[34]


# ---------------------------------------------------------------- episodes
def test_find_episodes_known_answer():
    flags = [0, 1, 1, 0, 0, 1, 0, 1, 1, 1]
    dates = pd.bdate_range("2024-01-01", periods=len(flags))
    e = sa.find_episodes(dates, flags)
    assert e["length"].tolist() == [2, 1, 3]
    assert e["gap_before"].tolist() == [1, 2, 1]
    assert e["start"].tolist() == [dates[1].date().isoformat(), dates[5].date().isoformat(), dates[7].date().isoformat()]
    assert e["end"].tolist() == [dates[2].date().isoformat(), dates[5].date().isoformat(), dates[9].date().isoformat()]
    assert sa.find_episodes(dates, [0] * 10).empty
    assert sa.find_episodes(dates, [1] * 10)["length"].tolist() == [10]


def test_episode_bootstrap_cycles_and_point_rate():
    f = np.array([0, 0, 1, 1, 0, 1, 0, 0, 0], bool)
    rate, lo, hi = sa.episode_bootstrap_rate(f, 200, np.random.default_rng(1))
    assert rate == pytest.approx(100 * 3 / 9)
    assert 0 <= lo <= rate <= hi <= 100


# ---------------------------------------------------------------- block bootstrap
def test_segment_ids():
    assert sa.segment_ids([3, 4, 5, 9, 10, 20]).tolist() == [0, 0, 0, 1, 1, 2]


def test_mbb_is_deterministic_and_seed_dependent():
    x = np.random.default_rng(0).integers(0, 2, 300).astype(float)
    a = sa.mbb_sums(x, 30, 200, sa.make_rng(5, "t"))
    b = sa.mbb_sums(x, 30, 200, sa.make_rng(5, "t"))
    c = sa.mbb_sums(x, 30, 200, sa.make_rng(6, "t"))
    d = sa.mbb_sums(x, 30, 200, sa.make_rng(5, "u"))
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c) and not np.array_equal(a, d)


def test_mbb_matches_an_explicit_construction():
    x = np.arange(1, 11, dtype=float)  # n = 10, L = 4 -> 3 blocks of 4, 4, 2
    for circular in (False, True):
        rng = sa.make_rng(3, "explicit")
        got = sa.mbb_sums(x, 4, 5, rng, circular)[:, 0]
        rng = sa.make_rng(3, "explicit")
        pool = np.arange(10) if circular else np.arange(10 - 4 + 1)
        starts = pool[rng.integers(0, len(pool), size=(5, 3))]
        want = []
        for s in starts:
            parts = [x[(np.arange(st, st + 4)) % 10] if circular else x[st:st + 4] for st in s]
            want.append(np.concatenate(parts)[:10].sum())
        assert np.allclose(got, want)


def test_mbb_full_length_block_is_the_sample_and_block_one_is_iid():
    x = np.random.default_rng(1).random(50)
    full = sa.mbb_sums(x, 50, 20, sa.make_rng(1))[:, 0]
    assert np.allclose(full, x.sum())  # one block, one possible start: every draw is the sample
    one = sa.mbb_sums(x, 1, 4000, sa.make_rng(1))[:, 0]
    assert one.mean() == pytest.approx(x.sum(), rel=0.02)
    assert one.var() == pytest.approx(len(x) * x.var(), rel=0.1)  # iid resampling: n * variance


def test_mbb_segments_never_bridge_a_gap():
    # two segments with values 0 and 1: a block that crossed the gap would contain both
    x = np.concatenate([np.zeros(40), np.ones(40)])
    seg = np.concatenate([np.zeros(40, int), np.ones(40, int)])
    s = sa.mbb_sums(x, 10, 400, sa.make_rng(2), False, seg)[:, 0]
    # n = 80 -> 8 blocks of 10; each block is wholly 0 or wholly 1, so every sum is a multiple of 10
    assert np.allclose(s % 10, 0)
    bridged = sa.mbb_sums(x, 10, 400, sa.make_rng(2), False)[:, 0]
    assert not np.allclose(bridged % 10, 0)


def test_ratio_interval_point_and_nan_handling():
    comp = np.column_stack([[1, 0, 1, 1], [1, 1, 1, 1]]).astype(float)
    p, lo, hi = sa.ratio_interval(comp, (0,), (1,), 2, 300, sa.make_rng(4))
    assert p == 0.75 and lo <= p <= hi
    empty_den = np.column_stack([[1, 1, 0, 0], [1, 1, 0, 0]]).astype(float)  # denominators vanish in some resamples
    p2, lo2, hi2 = sa.ratio_interval(empty_den, (0,), (1,), 1, 300, sa.make_rng(4))
    assert p2 == 1.0 and lo2 == hi2 == 1.0


# ---------------------------------------------------------------- effective sample size
def ar1(phi, n, seed):
    rng = np.random.default_rng(seed)
    e = rng.normal(size=n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def test_ess_matches_ar1_theory():
    n = 40000
    for phi in (0.0, 0.5, 0.9):
        x = ar1(phi, n, 11)
        theory = n * (1 - phi) / (1 + phi)
        assert sa.ess_acf(x) == pytest.approx(theory, rel=0.25), phi
        assert sa.ess_batch_means(x, 200) == pytest.approx(theory, rel=0.35), phi


def test_ess_constant_and_tiny_inputs():
    assert np.isnan(sa.ess_acf(np.zeros(100)))
    assert np.isnan(sa.ess_batch_means(np.ones(100), 10))
    assert np.isnan(sa.ess_batch_means(np.arange(15.0), 10))  # fewer than two batches


# ---------------------------------------------------------------- contested windows and comparators
def test_contested_definition_known_answer():
    # (pos, neg, mean_abs bn, flips) -> contested by (persistence, magnitude, flips) with margins 1 day, 1 bn, 1 flip
    rows = [
        (25, 5, 8.0, 2, (False, False, False)),   # nothing near
        (21, 9, 8.0, 2, (True, False, False)),    # exactly at the persistence threshold is within the margin
        (20, 10, 8.0, 2, (True, False, False)),   # 20 days: near and below the threshold, the others pass
        (22, 8, 8.0, 2, (True, False, False)),    # 22 days: within one day
        (23, 7, 8.0, 2, (False, False, False)),   # 23 days: two days away
        (25, 5, 4.5, 2, (False, True, False)),    # 4.5 bn: within 1 bn below the threshold, others pass
        (25, 5, 6.0, 2, (False, True, False)),    # 6.0 bn: within 1 bn above (boundary of the margin)
        (25, 5, 6.1, 2, (False, False, False)),
        (25, 5, 8.0, 4, (False, False, True)),    # 4 flips: within one of the limit
        (25, 5, 8.0, 6, (False, False, True)),    # 6 flips: within one, fails the limit
        (25, 5, 8.0, 7, (False, False, False)),
        (20, 10, 4.5, 2, (False, False, False)),  # two criteria near and failing: the other two do not both pass
        (25, 5, 8.0, 0, (False, False, False)),
    ]
    df = pd.DataFrame(rows, columns=["pos", "neg", "mag", "flips", "exp"])
    cm = sa.contested_mask(df["pos"], df["neg"], df["mag"] * BN, df["flips"])
    got = list(zip(cm["by_persistence"], cm["by_magnitude"], cm["by_flips"]))
    assert got == list(df["exp"]), pd.DataFrame({"got": got, "exp": df["exp"]})
    assert cm["contested"].tolist() == [any(e) for e in df["exp"]]


def test_contested_pivotal_variant_uses_half_billion_and_flips_5_and_6():
    df = pd.DataFrame({"pos": [25] * 4, "neg": [5] * 4, "mag": [4.5, 4.4, 8.0, 8.0], "flips": [2, 2, 4, 6]})
    cm = sa.contested_mask(df["pos"], df["neg"], df["mag"] * BN, df["flips"], 1, 0.5, 1, 0)
    # 4.5 bn fails the magnitude test but is within 0.5 bn: contested; 4.4 is not; 4 flips is outside {5, 6}; 6 flips is inside
    assert cm["contested"].tolist() == [True, False, False, True]


def test_comparators_known_answer():
    c = sa.comparator_labels([25, 20], [5, 10], [6 * BN, 6 * BN], [3, 3])
    assert c["always_yes"].tolist() == [True, True] and c["always_no"].tolist() == [False, False]
    assert c["persistence_only"].tolist() == [True, False]
    assert c["flips_only"].tolist() == [True, True] and c["magnitude_only"].tolist() == [True, True]
    assert c["persistence_magnitude"].tolist() == [True, False]


def test_confusion_summary_point_values():
    y = np.array([1, 1, 0, 0, 1, 0], bool)
    r = np.array([1, 0, 0, 1, 1, 0], bool)
    mask = np.array([1, 1, 1, 1, 0, 0], bool)  # windows 0-3: tp 1 (w0), fp 1 (w1), tn 1 (w2), fn 1 (w3)
    s = sa.confusion_summary(y, r, mask, 2, 100, (1, ("t",)))
    assert s["n"] == 4 and s["agree_pct"] == 50.0 and s["sens_pct"] == 50.0 and s["spec_pct"] == 50.0 and s["ppv_pct"] == 50.0


# ---------------------------------------------------------------- put weight grid
def test_put_weight_grid_known_answer():
    n = 330
    dates = pd.bdate_range("2008-01-01", periods=n)
    # call +12 bn every day, put -x bn: net = 12 - w * x
    x = 14.0
    days = pd.DataFrame({"trading_date": dates, "call_gex": np.full(n, 12 * BN), "put_gex": np.full(n, -x * BN)})
    cells, shifts = sa.put_weight_grid(days, weights=(0.5, 0.9, 1.0), thresholds_bn=(5.0,), periods=("2008-2019", "all"))
    got = cells[cells["period"] == "all"].set_index("put_weight")["rate_pct"]
    # w = 0.5: net = 5 bn -> mean |net| 5 >= 5, all positive -> every window detected;  w = 0.9: net = -0.6 -> mean 0.6 < 5;  w = 1.0: -2 -> no
    assert got[0.5] == 100.0 and got[0.9] == 0.0 and got[1.0] == 0.0
    assert (cells["n_windows"] == n - 29).all() or set(cells["period"]) == {"2008-2019", "all"}


def test_put_weight_w1_equals_classifier_on_call_plus_put():
    import common
    rng = np.random.default_rng(3)
    n = 120
    call = rng.uniform(0, 30 * BN, n)
    put = -rng.uniform(0, 30 * BN, n)
    days = pd.DataFrame({"trading_date": pd.bdate_range("2012-01-02", periods=n), "call_gex": call, "put_gex": put})
    cells, _ = sa.put_weight_grid(days, weights=(1.0,), thresholds_bn=(5.0,), periods=("all",))
    want = sum(common.classify(call[i:i + 30] + put[i:i + 30])["should_detect"] for i in range(n - 29))
    assert int(cells["n_detected"].iloc[0]) == want


def test_sign_crossings_interpolates():
    shifts = pd.DataFrame({"put_weight": [0.8, 0.9, 1.0], "threshold_bn": 5.0, "baseline": "b", "shift_pp": [10.0, -10.0, -20.0]})
    c = sa.sign_crossings(shifts)
    assert len(c) == 1 and c["put_weight"].iloc[0] == pytest.approx(0.85) and c["from_sign"].iloc[0] == 1


# ---------------------------------------------------------------- shifts, margin
def test_shift_interval_point_and_margin_logic():
    late = np.zeros(200)
    early = np.concatenate([np.ones(60), np.zeros(140)])
    r = sa.shift_interval(late, early, 20, 500, sa.make_rng(1))
    assert r["shift_pp"] == pytest.approx(-30.0) and r["ci_hi_pp"] < 0 < -r["ci_lo_pp"]


def test_baseline_masks_without_2022():
    we = pd.Series(pd.to_datetime(["2008-05-01", "2019-12-31", "2020-01-02", "2022-06-01", "2023-12-29", "2024-01-02"]))
    m = sa.baseline_masks(we)
    assert m["2020-2023"].tolist() == [False, False, True, True, True, False]
    assert m["2020-2023 without 2022"].tolist() == [False, False, True, False, True, False]
    assert m["2008-2023 without 2022"].tolist() == [True, True, True, False, True, False]


# ---------------------------------------------------------------- scale-free, E9, E13
def test_fold_ratio():
    by = pd.DataFrame({"year": [2009, 2026], "mean_spot": [100.0, 700.0], "mean_abs_net_bn": [1.0, 9.0], "mean_gross_bn": [4.0, 40.0]})
    f = sa.fold_ratio(by, 2009, 2026)
    assert f["spot"] == 7.0 and f["spot_squared"] == 49.0 and f["abs_net"] == 9.0 and f["gross"] == 10.0


def test_discordance_row_known_answer():
    full = np.array([1, 1, 1, 0, 0, 0, 0, 0], bool)
    ex = np.array([1, 0, 0, 1, 0, 0, 0, 0], bool)
    r = sa.discordance_row(full, ex)
    assert (r["both"], r["only_full"], r["only_ex0dte"], r["neither"]) == (1, 2, 1, 4)
    assert r["discordant"] == 3 and r["detected_by_either"] == 4 and r["discordant_pct_of_either"] == 75.0
    assert r["gap_pp"] == pytest.approx(100 * (3 / 8 - 2 / 8))


def test_era_interaction_known_answer():
    we = pd.to_datetime(["2015-01-02"] * 100 + ["2024-01-02"] * 100)
    pair = pd.DataFrame({"window_end": we, "full": [True] * 20 + [False] * 80 + [False] * 100,
                         "ex": [False] * 100 + [True] * 10 + [False] * 90})
    r = sa.era_interaction(pair, (2014, 2022), (2023, 2026), 10, 200, sa.make_rng(1))
    assert r["gap_a_pp"] == pytest.approx(20.0) and r["gap_b_pp"] == pytest.approx(-10.0) and r["interaction_pp"] == pytest.approx(-30.0)


def test_same_day_shares_known_answer():
    days = pd.DataFrame({"trading_date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "net_full": [10.0, -20.0],
                         "net_ex0dte": [4.0, -10.0], "call_full": [30.0, 30.0], "put_full": [-20.0, -50.0],
                         "call_ex": [20.0, 20.0], "put_ex": [-16.0, -30.0], "gex_0dte": [6.0, -10.0]})
    s = sa.same_day_shares(days).set_index("year").loc[2024]
    assert s["abs_0dte_share_of_abs_net"] == pytest.approx(100 * 16 / 30)
    assert s["abs_0dte_share_of_gross"] == pytest.approx(100 * 16 / 130)  # gross: 50 + 80
    assert s["gross_removed_share"] == pytest.approx(100 * (130 - 86) / 130)  # ex gross: 36 + 50
    assert s["sign_flip_pct"] == 0.0


def test_lineage_counts_known_answer():
    d = pd.to_datetime(["2020-03-02", "2020-03-03", "2021-03-02", "2021-03-03"])
    a = pd.DataFrame({"window_end": d, "label": [True, True, False, False]})
    b = pd.DataFrame({"window_end": d, "label": [True, False, False, True]})
    t = sa.lineage_counts(a, b, "a", "b").set_index("year")
    assert t.loc[2020, ["equal", "different", "only_a", "only_b"]].tolist() == [1, 1, 1, 0]
    assert t.loc[2021, ["equal", "different", "only_a", "only_b"]].tolist() == [1, 1, 0, 1]
    assert t.loc["all", "n_common"] == 4 and t.loc["all", "equal"] == 2


def test_hybrid_values_switch_at_the_break():
    dates = pd.Series(pd.to_datetime(["2023-09-28", "2023-09-29", "2023-10-02"]))
    full = pd.DataFrame({"trading_date": dates, "net_gex": [1.0, 2.0, 3.0]})
    call = pd.DataFrame({"trading_date": dates, "call_gex": [10.0, 20.0, 30.0]})
    assert sa.hybrid_values(dates, full, call, pd.Timestamp("2023-09-29")).tolist() == [1.0, 20.0, 30.0]


def test_period_mask_and_weekday():
    we = pd.Series(pd.to_datetime(["2019-12-31", "2020-01-02", "2025-12-31", "2026-01-02"]))
    assert sa.period_mask(we, "2024-2025").tolist() == [False, False, True, False]
    assert sa.period_mask(we, "all").tolist() == [True] * 4
    assert sa.weekday_name(0) == "Mon" and sa.weekday_name(4) == "Fri"
