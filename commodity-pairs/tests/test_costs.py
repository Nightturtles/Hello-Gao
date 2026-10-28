"""Spec 12.5: hand-checked fills on a 3-day toy series give exactly the expected slippage, commission and borrow."""
import numpy as np
import pandas as pd
import pytest

from backtest import strategies, walkforward as wf
from backtest.trading_calendar import Window


class Scripted:
    """Strategy stub that returns pre-set targets by session index (used only to test the accounting)."""

    def __init__(self, targets: dict):
        self.targets = targets

    def fit(self, rule, hA, hB, params):
        return strategies.FitResult(rule=rule)

    def new_window_state(self, rule, prev, fit_, params):
        return {"z": None, "beta_used": None, "spread": None}

    def step(self, rule, state, hA, hB, fit_, params):
        i = len(hA) - 1
        return dict(state), dict(self.targets.get(i, {"A": 0.0, "B": 0.0})), f"scripted day {i}"


def _toy(n=6):
    dates = pd.bdate_range("2024-01-01", periods=n)
    # sessions 0..5; training = sessions 0-1; test (signal) days = 2..5
    ao_a = np.array([50, 50, 50, 50, 52, 53.0]); ac_a = np.array([50, 50, 50, 51, 52, 54.0])
    ao_b = np.array([20, 20, 20, 20, 19.5, 18.5]); ac_b = np.array([20, 20, 20, 19.5, 19, 18.0])
    return wf.PairData("TOY", "A", "B", dates, ac_a, ac_b, ao_a, ao_b, ao_a.copy(), ao_b.copy(),
                       slip_a=0.0005, slip_b=0.001, borrow_a=0.005, borrow_b=0.03)


def test_three_day_toy_exact():
    p = _toy()
    win = [Window(0, 0, 2, 2, 6)]
    # signal at close of session 2 -> fill at open of session 3; exit signal at close of session 4 -> fill at open of 5
    strat = Scripted({2: {"A": 0.5, "B": -0.5}, 3: {"A": 0.5, "B": -0.5}})
    res = wf.run_pair_rule("scripted", p, win, strat=strat, capital=100_000.0)
    d = res.daily
    # --- hand calculation (see the numbers in the comments) ---
    # entry at open of session 3:  A: 50_000 / 50 = 1000 sh, buy @ 50*(1.0005)=50.025 -> -50_025.00, commission 1000*0.005 = 5.00
    #                              B: -50_000 / 20 = -2500 sh, sell @ 20*(0.999)=19.98 -> +49_950.00, commission 2500*0.005 = 12.50
    # cash = 100_000 - 50_025 - 5 + 49_950 - 12.5 = 99_907.5 ; slippage cost = 1000*50*0.0005 + 2500*20*0.001 = 25 + 50 = 75
    # day-3 borrow: 2500*19.5*0.03/252 ; day-4 borrow: 2500*19*0.03/252
    b3 = 2500 * 19.5 * 0.03 / 252
    b4 = 2500 * 19.0 * 0.03 / 252
    cash3 = 99_907.5 - b3
    eq3 = cash3 + 1000 * 51 - 2500 * 19.5
    cash4 = cash3 - b4
    eq4 = cash4 + 1000 * 52 - 2500 * 19.0
    # exit at open of session 5: A sell 1000 @ 53*(0.9995)=52.9735 ; B buy 2500 @ 18.5*(1.001)=18.5185
    cash5 = cash4 + 1000 * 52.9735 - 5.0 - 2500 * 18.5185 - 12.5
    assert d["equity"].iloc[0] == 100_000.0 and d["net_ret"].iloc[0] == 0.0
    assert d["equity"].iloc[1] == pytest.approx(eq3, abs=1e-9)
    assert d["equity"].iloc[2] == pytest.approx(eq4, abs=1e-9)
    assert d["equity"].iloc[3] == pytest.approx(cash5, abs=1e-9)
    # literal values for the headline numbers
    assert eq3 == pytest.approx(102_151.69642857, abs=1e-6)
    assert cash5 == pytest.approx(106_555.79166667, abs=1e-6)
    # day-3 cost bookkeeping: slippage 75 + commission 17.5 + borrow
    assert d["costs"].iloc[1] == pytest.approx(75.0 + 17.5 + b3, abs=1e-9)
    assert d["gross_ret"].iloc[1] - d["net_ret"].iloc[1] == pytest.approx((75.0 + 17.5 + b3) / 100_000.0, abs=1e-12)
    # exit-day costs: slippage 1000*53*0.0005 + 2500*18.5*0.001 = 26.5 + 46.25 ; commission 17.5 ; no borrow
    assert d["costs"].iloc[3] == pytest.approx(26.5 + 46.25 + 17.5, abs=1e-9)
    # trade log
    t = res.trades.iloc[0]
    assert len(res.trades) == 1 and not t["open_at_end"]
    assert t["net_pnl"] == pytest.approx(cash5 - 100_000.0, abs=1e-9)
    assert t["net_pnl"] == pytest.approx(6_555.79166667, abs=1e-6)
    assert t["holding_days"] == 2 and t["side"] == "long A / short B"
    assert d["equity"].iloc[-1] - 100_000.0 == pytest.approx(res.trades["net_pnl"].sum(), abs=1e-9)


def test_commission_minimum_and_flip_is_two_fills():
    """A flip closes the old position and opens the new one (4 fills, each with its own $1 minimum)."""
    dates = pd.bdate_range("2024-01-01", periods=6)
    px = np.full(6, 100.0)
    p = wf.PairData("FLIP", "A", "B", dates, px.copy(), px.copy(), px.copy(), px.copy(), px.copy(), px.copy(),
                    slip_a=0.001, slip_b=0.001, borrow_a=0.0, borrow_b=0.0)
    strat = Scripted({2: {"A": 0.0005, "B": -0.0005}, 3: {"A": -0.0005, "B": 0.0005}})   # tiny weights -> $1 minimum
    res = wf.run_pair_rule("scripted", p, [Window(0, 0, 2, 2, 6)], strat=strat)
    d = res.daily
    # entry at open of session 3: notional 50 per leg -> 0.5 sh -> commission max(1, 0.0025) = 1 per leg
    # flip at open of session 4: close 2 legs (2 x $1) + open 2 legs (2 x $1)
    # entry: 2 x $1 commission + slippage 2 * 0.5 sh * 100 * 10bps = 0.1  -> equity after entry = 100_000 - 2.1
    assert d["costs"].iloc[1] == pytest.approx(2.0 + 0.1, abs=1e-12)
    eq_after_entry = 100_000.0 - 2.1
    new_sh = 0.0005 * eq_after_entry / 100.0                      # re-sized from the previous close's equity
    flip_cost = 4.0 + (2 * 0.5 + 2 * new_sh) * 100.0 * 0.001      # 4 fills x $1 + slippage on closing 0.5 sh x2, opening new_sh x2
    assert d["costs"].iloc[2] == pytest.approx(flip_cost, abs=1e-12)
    assert len(res.trades) == 2
    assert list(res.trades["side"]) == ["long A / short B", "short A / long B"]
    assert not res.trades["open_at_end"].any()      # script goes flat at the close of session 4 -> closed at open of 5
