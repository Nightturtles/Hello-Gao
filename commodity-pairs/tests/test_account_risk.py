"""Account-level risk (post-audit engine fix): maintenance-margin liquidation and ruin handling.

Before this fix the engine held share counts constant while equity collapsed (effective gross leverage reached
thousands of times equity) and, once equity went negative, sized new trades from negative equity (flipping their
direction). A margin account would have been liquidated long before either happened.
"""
import numpy as np
import pandas as pd
import pytest

from backtest import strategies, walkforward as wf
from backtest.trading_calendar import Window

from .test_costs import Scripted

HOLD = {i: {"A": 0.5, "B": -0.5} for i in range(2, 9)}     # script keeps asking for long A / short B


def _pair(close_b, open_b):
    dates = pd.bdate_range("2024-01-01", periods=len(close_b))
    a = np.full(len(close_b), 100.0)
    cb, ob = np.asarray(close_b, float), np.asarray(open_b, float)
    return wf.PairData("RISK", "A", "B", dates, a.copy(), cb, a.copy(), ob, a.copy(), ob.copy(),
                       slip_a=0.0, slip_b=0.0, borrow_a=0.0, borrow_b=0.0)


def _run(p):
    return wf.run_pair_rule("scripted", p, [Window(0, 0, 2, 2, len(p.dates))], strat=Scripted(HOLD),
                            capital=100_000.0, comm_min=0.0, comm_per_share=0.0)


def test_account_check_thresholds():
    assert wf.account_check(30_000, 100_000) is None            # 30% >= 25%
    assert wf.account_check(24_999, 100_000) == "margin_call"
    assert wf.account_check(0.0, 100_000) == "ruin"
    assert wf.account_check(50_000, 0.0) is None                # flat account


def test_margin_call_liquidates_at_next_open():
    # entry at open of session 3 (B = 100): long 500 A, short 500 B.  Close 5: B = 230 ->
    # equity 100k + 50k - 115k = 35k < 25% x gross (50k + 115k) -> margin call, liquidated at open of session 6.
    p = _pair(close_b=[100, 100, 100, 100, 160, 230, 240, 240, 240],
              open_b=[100, 100, 100, 100, 150, 220, 240, 240, 240])
    res = _run(p)
    d, t = res.daily, res.trades
    assert d["equity"].iloc[2] == pytest.approx(70_000.0)       # close 4
    assert d["equity"].iloc[3] == pytest.approx(35_000.0)       # close 5: below maintenance
    assert t.iloc[0]["exit_reason"].startswith("margin call")
    assert t.iloc[0]["exit_date"] == p.dates[6]
    assert d["wA"].iloc[4] == 0.0 and d["wB"].iloc[4] == 0.0     # flat at close 6
    assert d["equity"].iloc[4] == pytest.approx(100_000 + 500 * 100 - 500 * 240)   # 30k after liquidation
    assert res.meta["margin_calls"] == 1 and res.meta["ruined_on"] is None
    # the (stub) strategy asks to re-enter: the new position is sized from the remaining 30k, not the old size
    assert d["wA"].iloc[5] == pytest.approx(0.5) and d["equity"].iloc[5] == pytest.approx(30_000.0)


def test_ruin_stops_trading_and_caps_loss_at_100pct():
    # overnight gap: B opens and closes at 400 on session 4 -> equity 100k + 50k - 200k = -50k -> ruin
    p = _pair(close_b=[100, 100, 100, 100, 400, 400, 400, 400, 400],
              open_b=[100, 100, 100, 100, 400, 400, 400, 400, 400])
    res = _run(p)
    d = res.daily
    assert d["equity"].iloc[2] == pytest.approx(-50_000.0)
    assert d["net_ret"].iloc[2] == -1.0                        # capped at -100%
    assert (d["net_ret"].iloc[3:] == 0.0).all()                # no capital, no return
    assert res.meta["ruined_on"] == str(p.dates[4].date())
    assert len(res.trades) == 1 and res.trades.iloc[0]["exit_reason"].startswith("ruin")
    assert d["wA"].iloc[3:].isna().all()                       # never re-entered from negative equity
    assert d["equity"].iloc[-1] == pytest.approx(-50_000.0)    # the deficit is not traded away


def test_force_flat_disarms_spread_rules():
    st = strategies.initial_state("coint_ols")
    st.update(pos=1, w=[0.4, -0.6], beta_entry=1.5)
    out = strategies.force_flat("coint_ols", st)
    assert out["pos"] == 0 and out["w"] == [0.0, 0.0] and out["armed"] is False and out["beta_entry"] is None
    assert st["pos"] == 1                                     # input not mutated
    rot = strategies.force_flat("rotation", {**strategies.initial_state("rotation"), "pos": -1, "w": [-0.5, 0.5]})
    assert rot["pos"] == 0 and rot["armed"] is True
