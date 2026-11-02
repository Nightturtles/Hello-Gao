"""Spec 12.2: train/test windows are disjoint and follow the global grid; the engine feeds fit()/step() only data
available at the time."""
import numpy as np
import pandas as pd

from backtest import config, strategies, walkforward as wf
from backtest.trading_calendar import sessions, walk_forward_grid
from tests import synth


def test_grid_geometry():
    sess = sessions()
    ws = walk_forward_grid(sess)
    assert sess[ws[0].test_start] == pd.Timestamp("2016-10-03")
    for a, b in zip(ws[:-1], ws[1:]):
        assert b.test_start - a.test_start == config.TEST_LEN
        assert a.test_end == b.test_start
    for w in ws:
        assert w.fit_end - w.fit_start == config.TRAIN_LEN
        assert w.fit_end == w.test_start                     # training ends the session before the test start
        assert sess[w.fit_end - 1] < sess[w.test_start]      # strictly before
    assert ws[-1].test_end == len(sess)
    assert sess[-1] == pd.Timestamp(config.SNAPSHOT_END)


class Recorder:
    """Delegates to strategies and records exactly what the engine hands to fit() and step()."""

    def __init__(self):
        self.fits, self.steps = [], []

    def fit(self, rule, hA, hB, params):
        self.fits.append((float(hA[0]), float(hA[-1]), len(hA), len(hB)))
        return strategies.fit(rule, hA, hB, params)

    def new_window_state(self, *a, **k):
        return strategies.new_window_state(*a, **k)

    def step(self, rule, state, hA, hB, fit_, params):
        self.steps.append((float(hA[-1]), float(hB[-1]), len(hA)))
        return strategies.step(rule, state, hA, hB, fit_, params)


def test_engine_feeds_only_past_data():
    n = len(synth.SESS)
    idx = np.arange(n, dtype=float)
    # each price encodes its own session index, so we can read off exactly what the engine passed in
    ac_a, ac_b = 10.0 + 0.01 * idx, 20.0 + 0.02 * idx + 0.003 * np.sin(idx)
    p = wf.PairData("ENC", "A", "B", synth.SESS, ac_a, ac_b, ac_a.copy(), ac_b.copy(), ac_a.copy(), ac_b.copy())
    rec = Recorder()
    res = wf.run_pair_rule("coint_ols", p, synth.WINDOWS, strat=rec)
    assert len(rec.fits) == len(synth.WINDOWS)
    for w, (first, last, la, lb) in zip(synth.WINDOWS, rec.fits):
        assert la == lb == config.TRAIN_LEN
        assert first == ac_a[w.fit_start] and last == ac_a[w.test_start - 1]
        assert last < ac_a[w.test_start]                       # fit data strictly before the first test day
    assert len(rec.steps) == len(res.daily) == n - synth.WINDOWS[0].test_start
    for j, (a_last, b_last, length) in enumerate(rec.steps):
        i = synth.WINDOWS[0].test_start + j
        assert length == i + 1 and a_last == ac_a[i] and b_last == ac_b[i]   # up to and including today only


def test_first_trade_fill_is_next_open():
    p = synth.cointegrated(4, half_life=6.0, stat_sd=0.08)
    res = wf.run_pair_rule("coint_ols", p, synth.WINDOWS)
    d = res.daily
    assert len(res.trades) > 3
    for _, t in res.trades.head(5).iterrows():
        e = pd.Timestamp(t["entry_date"])
        i = d.index.get_loc(e)
        # no position at the close before the fill day, a position at the close of the fill day
        assert abs(d["wA"].iloc[i - 1]) < 1e-12 and abs(d["wA"].iloc[i]) > 0.1
