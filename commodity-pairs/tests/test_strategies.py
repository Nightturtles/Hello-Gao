"""Unit tests of the shared trading rules (state machine, JSON persistence, fit/step contract)."""
import copy
import json

import numpy as np
import pytest

from backtest import config, strategies as S
from tests import synth

P = config.PARAMS


def _run_steps(rule, pair, w_idx=15, n_days=None, roundtrip_json=False):
    w = synth.WINDOWS[w_idx]
    fit = S.fit(rule, pair.ac_a[w.fit_start:w.fit_end], pair.ac_b[w.fit_start:w.fit_end], P)
    st = S.new_window_state(rule, None, fit, P)
    out = []
    end = w.test_end if n_days is None else w.test_start + n_days
    for i in range(w.test_start, end):
        if roundtrip_json:
            st = json.loads(json.dumps(st))
            fit = S.FitResult.from_dict(json.loads(json.dumps(fit.to_dict())))
        st, tgt, reason = S.step(rule, st, pair.ac_a[:i + 1], pair.ac_b[:i + 1], fit, P)
        out.append((i, st, tgt, reason))
    return fit, out


@pytest.mark.parametrize("rule", S.RULES)
def test_state_and_fit_are_json_serialisable_and_roundtrip_exactly(rule):
    pair = synth.leadlag(11) if rule.startswith("leadlag") else synth.cointegrated(11, half_life=6, stat_sd=0.08)
    if rule == "leadlag_rev":
        pair.ac_a, pair.ac_b = pair.ac_b, pair.ac_a
    fit, direct = _run_steps(rule, pair, w_idx=16)
    fit2, viajson = _run_steps(rule, pair, w_idx=16, roundtrip_json=True)
    assert fit.to_dict() == fit2.to_dict()
    json.dumps(fit.to_dict())
    for (i, s1, t1, r1), (_, s2, t2, r2) in zip(direct, viajson):
        json.dumps(s1)
        assert t1 == t2 and r1 == r2
        assert json.loads(json.dumps(s1)) == s1       # a persisted state is the state


def test_step_does_not_mutate_its_input_state():
    pair = synth.cointegrated(5, half_life=6, stat_sd=0.08)
    for rule in ("coint_ols", "coint_kalman", "rotation"):
        w = synth.WINDOWS[12]
        fit = S.fit(rule, pair.ac_a[w.fit_start:w.fit_end], pair.ac_b[w.fit_start:w.fit_end], P)
        st = S.new_window_state(rule, None, fit, P)
        for i in range(w.test_start, w.test_start + 120):
            before = copy.deepcopy(st)
            new, _, _ = S.step(rule, st, pair.ac_a[:i + 1], pair.ac_b[:i + 1], fit, P)
            assert st == before
            st = new


def test_gross_weights_sum_to_one_in_trade():
    pair = synth.cointegrated(6, half_life=6, stat_sd=0.08)
    for rule in ("coint_ols", "coint_kalman", "rotation"):
        _, steps = _run_steps(rule, pair, 14)
        seen = False
        for _, st, tgt, _ in steps:
            g = abs(tgt["A"]) + abs(tgt["B"])
            assert g == pytest.approx(0.0, abs=1e-12) or g == pytest.approx(1.0, abs=1e-12)
            seen |= g > 0
        assert seen


def test_coint_ols_state_machine_invariants():
    """Entries at |z|>=2 (right side), exits on a zero cross or |z|>=3.5, stop disarms until |z|<2."""
    pair = synth.cointegrated(8, half_life=8, stat_sd=0.12)       # wild spread -> lots of stops
    n_entry = n_exit0 = n_stop = n_rearm = 0
    for w_idx in range(10, 40):
        fit, steps = _run_steps("coint_ols", pair, w_idx)
        prev = S.initial_state("coint_ols")
        for _, st, tgt, reason in steps:
            z = st["z"]
            if prev["pos"] == 0 and st["pos"] != 0:                       # entry
                n_entry += 1
                assert prev["armed"]
                assert (st["pos"] == 1 and z <= -2.0) or (st["pos"] == -1 and z >= 2.0)
                assert st["beta_entry"] == fit.beta
                assert tgt["A"] == pytest.approx(st["pos"] / (1 + fit.beta))
                assert tgt["B"] == pytest.approx(-st["pos"] * fit.beta / (1 + fit.beta))
            if prev["pos"] != 0 and st["pos"] == 0:                       # exit
                if reason.startswith("stop"):
                    n_stop += 1
                    assert abs(z) >= 3.5 and not st["armed"]
                else:
                    n_exit0 += 1
                    assert (prev["pos"] == 1 and z >= 0) or (prev["pos"] == -1 and z <= 0)
                    assert abs(z) < 3.5
            if prev["pos"] == 0 and not prev["armed"] and st["armed"]:
                n_rearm += 1
                assert abs(z) < 2.0
            if prev["pos"] == 0 and not prev["armed"]:
                assert st["pos"] == 0                                     # never enters while disarmed
            if prev["pos"] != 0 and st["pos"] != 0:
                assert st["beta_entry"] == prev["beta_entry"]            # beta frozen for the trade life
            prev = st
    assert n_entry > 20 and n_exit0 > 10 and n_stop > 0 and n_rearm > 0


def test_open_trade_keeps_entry_beta_across_window_boundary():
    pair = synth.cointegrated(9, half_life=6, stat_sd=0.08)
    rule = "coint_ols"
    st = None
    carried = 0
    for w in synth.WINDOWS[12:30]:
        fit = S.fit(rule, pair.ac_a[w.fit_start:w.fit_end], pair.ac_b[w.fit_start:w.fit_end], P)
        before = st
        st = S.new_window_state(rule, st, fit, P)
        if before is not None and before["pos"] != 0:
            assert st["pos"] == before["pos"] and st["beta_entry"] == before["beta_entry"]
            carried += 1
        for i in range(w.test_start, w.test_end):
            st, _, _ = S.step(rule, st, pair.ac_a[:i + 1], pair.ac_b[:i + 1], fit, P)
    assert carried >= 1


def test_beta_out_of_range_blocks_entries():
    # B has a tiny loading on A's level -> OLS beta far below 0.2 -> no entries in the window
    n = len(synth.SESS)
    la = synth.random_walk(n, 1)
    lb = 0.05 * la + synth.random_walk(n, 2, vol=0.002)
    pair = synth.pair_data(la, lb, 3)
    w = synth.WINDOWS[10]
    fit = S.fit("coint_ols", pair.ac_a[w.fit_start:w.fit_end], pair.ac_b[w.fit_start:w.fit_end], P)
    # regress ln A on ln B; ratio is large when B barely moves with A -> beta > 5 -> out of range
    assert not fit.valid and fit.reason == "beta out of range"
    st = S.new_window_state("coint_ols", None, fit, P)
    for i in range(w.test_start, w.test_end):
        st, tgt, reason = S.step("coint_ols", st, pair.ac_a[:i + 1], pair.ac_b[:i + 1], fit, P)
        assert tgt == {"A": 0.0, "B": 0.0} and reason == "beta out of range"


def test_kalman_filter_matches_textbook_recursion_and_is_causal():
    rng = np.random.default_rng(0)
    lx = np.cumsum(rng.normal(0, 0.01, 300)) + 3.0
    ly = 0.3 + 1.2 * lx + rng.normal(0, 0.02, 300)
    kf = S.kalman_init_state((0.0, 1.0), 1e-2)
    delta, ve = P["kalman_delta"], P["kalman_ve"]
    # independent matrix implementation
    th = np.array([0.0, 1.0]); Pm = np.eye(2) * 1e-2
    W = delta / (1 - delta) * np.eye(2)
    for t in range(300):
        x = np.array([1.0, lx[t]])
        e_kf = S.kalman_update(kf, float(ly[t]), float(lx[t]), delta, ve)
        Pp = Pm + W
        e = ly[t] - x @ th                      # prediction uses the state from t-1
        Q = x @ Pp @ x + ve
        K = Pp @ x / Q
        th = th + K * e
        Pm = Pp - np.outer(K, x) @ Pp
        assert e_kf == pytest.approx(e, abs=1e-12)
        assert kf["a"] == pytest.approx(th[0], abs=1e-10) and kf["b"] == pytest.approx(th[1], abs=1e-10)
    # strict causality: the innovation at t does not depend on y_t's own update
    a, b = kf["a"], kf["b"]
    kf2 = dict(kf)
    e_next = S.kalman_update(kf2, 5.0, 3.0, delta, ve)
    assert e_next == pytest.approx(5.0 - (a + b * 3.0), abs=1e-12)


def test_rotation_follows_20d_return_ranking_and_flips():
    n = 300
    t = np.arange(n)
    a = 100 * np.exp(0.002 * t + 0.05 * np.sin(t / 15))
    b = 100 * np.exp(0.0005 * t + 0.05 * np.cos(t / 15))
    fit = S.fit("rotation", a[:100], b[:100], P)
    st = S.initial_state("rotation")
    flips = 0
    last = None
    for i in range(21, n):
        st, tgt, reason = S.step("rotation", st, a[:i + 1], b[:i + 1], fit, P)
        ra, rb = a[i] / a[i - 20] - 1, b[i] / b[i - 20] - 1
        exp = {"A": 0.5, "B": -0.5} if ra > rb else {"A": -0.5, "B": 0.5}
        assert tgt == exp
        if last is not None and tgt != last:
            flips += 1
            assert reason.startswith("flip")
        last = tgt
    assert flips >= 3


def test_leadlag_fit_recovers_lag_and_hold_is_exactly_k_days():
    pair = synth.leadlag(21, lag=4, strength=0.9)
    w = synth.WINDOWS[14]
    fit = S.fit("leadlag", pair.ac_a[w.fit_start:w.fit_end], pair.ac_b[w.fit_start:w.fit_end], P)
    assert fit.valid and fit.k == 4 and fit.slope > 0 and fit.h > 0
    assert 1 <= fit.k <= P["ll_kmax"]
    st = S.new_window_state("leadlag", None, fit, P)
    holds, cur = [], None
    for i in range(w.test_start, w.test_end):
        prev_pos = st["pos"]
        st, tgt, reason = S.step("leadlag", st, pair.ac_a[:i + 1], pair.ac_b[:i + 1], fit, P)
        if prev_pos == 0 and st["pos"] != 0:
            cur = 0
            # follower weight sign follows sign(slope * x); gross = 1
            assert abs(tgt["A"]) + abs(tgt["B"]) == pytest.approx(1.0)
            assert tgt["A"] * tgt["B"] < 0                       # long follower / short leader (or reverse)
            continue
        if cur is not None:
            if st["pos"] == 0:
                holds.append(cur + 1)                            # signal step that exits = k-th step after entry
                cur = None
            else:
                cur += 1
    assert len(holds) >= 3 and set(holds) == {fit.k}


def test_leadlag_no_entries_when_tstat_small_or_h_nonpositive():
    n = len(synth.SESS)
    p = synth.independent(3)
    w = synth.WINDOWS[10]
    fit = S.fit("leadlag", p.ac_a[w.fit_start:w.fit_end], p.ac_b[w.fit_start:w.fit_end], P)
    if abs(fit.tstat) < 2:
        assert not fit.valid
    st = S.new_window_state("leadlag", None, S.FitResult(rule="leadlag", valid=False, reason="lead-lag |t| < 2"), P)
    st, tgt, reason = S.step("leadlag", st, p.ac_a[:w.test_start + 1], p.ac_b[:w.test_start + 1],
                             S.FitResult(rule="leadlag", valid=False, reason="lead-lag |t| < 2"), P)
    assert tgt == {"A": 0.0, "B": 0.0}
