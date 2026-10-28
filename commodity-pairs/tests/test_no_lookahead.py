"""Spec 12.1: perturbing all prices after date T must not change targets, step outputs, fills or equity at dates <= T."""
import copy

import numpy as np
import pandas as pd
import pytest

from backtest import config, strategies, walkforward as wf
from tests import synth

RULES = strategies.RULES


def _pair_for(rule):
    if rule == "leadlag":
        return synth.leadlag(7)
    if rule == "leadlag_rev":                      # B leads A: swap the legs of the lead-lag generator
        q = synth.leadlag(7)
        q.ac_a, q.ac_b, q.ao_a, q.ao_b, q.ro_a, q.ro_b = q.ac_b, q.ac_a, q.ao_b, q.ao_a, q.ro_b, q.ro_a
        return q
    return synth.cointegrated(7, half_life=6.0, stat_sd=0.08)


def _perturb(p: wf.PairData, T: int, seed: int = 99) -> wf.PairData:
    q = copy.deepcopy(p)
    rng = np.random.default_rng(seed)
    n = len(p.dates)
    for name in ("ac_a", "ac_b", "ao_a", "ao_b", "ro_a", "ro_b"):
        arr = getattr(q, name).copy()
        # violent, independent multiplicative shocks on everything strictly after T
        arr[T + 1:] = arr[T + 1:] * np.exp(rng.normal(0.0, 0.5, n - T - 1))
        setattr(q, name, arr)
    return q


def _trace_steps(rule, p, window, T):
    """Replay the daily step loop for one window (fit on its own training data) up to and including T."""
    params = config.PARAMS
    fit = strategies.fit(rule, p.ac_a[window.fit_start:window.fit_end], p.ac_b[window.fit_start:window.fit_end], params)
    st = strategies.new_window_state(rule, None, fit, params)
    out = []
    for i in range(window.test_start, T + 1):
        st, tgt, reason = strategies.step(rule, st, p.ac_a[:i + 1], p.ac_b[:i + 1], fit, params)
        out.append((i, dict(st), dict(tgt), reason))
    return fit.to_dict(), out


@pytest.mark.parametrize("rule", RULES)
def test_step_outputs_identical_up_to_T(rule):
    p = _pair_for(rule)
    w = synth.WINDOWS[18]
    T = w.test_start + 40
    q = _perturb(p, T)
    f0, tr0 = _trace_steps(rule, p, w, T)
    f1, tr1 = _trace_steps(rule, q, w, T)
    assert f0 == f1
    assert tr0 == tr1
    # power check: the perturbation really does change later days
    _, later0 = _trace_steps(rule, p, w, w.test_end - 1)
    _, later1 = _trace_steps(rule, q, w, w.test_end - 1)
    assert later0 != later1


@pytest.mark.parametrize("rule", RULES)
def test_engine_identical_up_to_T(rule):
    p = _pair_for(rule)
    T = synth.WINDOWS[20].test_start + 30
    q = _perturb(p, T)
    base = wf.run_pair_rule(rule, p, synth.WINDOWS)
    pert = wf.run_pair_rule(rule, q, synth.WINDOWS)
    dT = p.dates[T]
    d0, d1 = base.daily.loc[:dT], pert.daily.loc[:dT]
    assert len(d0) > 500
    pd.testing.assert_frame_equal(d0, d1, check_exact=True)
    # trades whose fills (entry and exit) are at or before T are identical
    cols = ["entry_date", "exit_date", "side", "entry_reason", "exit_reason", "net_pnl", "holding_days", "beta"]
    t0 = base.trades[(base.trades.exit_date <= dT) & ~base.trades.open_at_end][cols].reset_index(drop=True)
    t1 = pert.trades[(pert.trades.exit_date <= dT) & ~pert.trades.open_at_end][cols].reset_index(drop=True)
    assert len(t0) > 0
    pd.testing.assert_frame_equal(t0, t1, check_exact=True)
    # power check: after T the runs diverge
    assert not np.array_equal(base.daily.loc[dT:, "equity"].to_numpy(), pert.daily.loc[dT:, "equity"].to_numpy())


def test_window_fits_identical_when_future_perturbed():
    p = synth.cointegrated(3)
    w = synth.WINDOWS[10]
    q = _perturb(p, w.test_start - 1)
    a = strategies.fit("coint_ols", p.ac_a[w.fit_start:w.fit_end], p.ac_b[w.fit_start:w.fit_end], config.PARAMS)
    b = strategies.fit("coint_ols", q.ac_a[w.fit_start:w.fit_end], q.ac_b[w.fit_start:w.fit_end], config.PARAMS)
    assert a.to_dict() == b.to_dict()
