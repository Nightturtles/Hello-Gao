"""Simulator engine: fill math, costs, corporate actions, warm start (no look-ahead), calendar and providers."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from backtest import config, strategies
from backtest.trading_calendar import sessions, walk_forward_grid
from sim import cal, engine
from sim.data import CacheProvider, DataError, YahooProvider

from .sim_support import START, real_picks

PICK = {"pick_id": "t", "pair_id": "AAA_BBB", "leg_a": "AAA", "leg_b": "BBB", "rule": "rotation",
        "params": config.PARAMS, "slippage_bps": {"AAA": 10.0, "BBB": 5.0}, "borrow_rate": {"AAA": 0.005, "BBB": 0.03}}
SESS = sessions(config.DOWNLOAD_START, "2026-07-20")        # 2026-07-20 is not a walk-forward grid date
I = len(SESS) - 1


def pdata(open_a, close_a, open_b, close_b, div=(0.0, 0.0), split=(0.0, 0.0)) -> engine.PickData:
    n = len(SESS)

    def arr(v, last):                      # constant history, `last` on the processed day
        a = np.full(n, v, dtype=float)
        a[-1] = last
        return a

    # A drifts up, B is flat, so the rotation rule keeps asking for long A / short B (weights 0.5 / -0.5)
    ac_a = 50.0 * np.exp(0.001 * np.arange(n))
    ac_b = np.full(n, 20.0)
    return engine.PickData(
        pick=PICK, sess=SESS, ac=(ac_a, ac_b),
        op=(arr(50.0, open_a), arr(20.0, open_b)), cl=(arr(50.0, close_a), arr(20.0, close_b)),
        dv=(arr(0.0, div[0]), arr(0.0, div[1])), sp=(arr(0.0, split[0]), arr(0.0, split[1])),
        slip=(0.001, 0.0005), brate=(0.005 / 252, 0.03 / 252))


def make_ps(shares=(0.0, 0.0), cur_w=(0.0, 0.0), cash=100_000.0, equity=100_000.0, pending=None) -> dict:
    st = strategies.initial_state("rotation")
    return {"pick_id": "t", "rule": "rotation", "last_processed": "2026-07-17", "cash": cash, "equity": equity,
            "hwm": equity, "start_equity": equity, "shares": list(shares), "cur_w": list(cur_w), "pending": pending,
            "strategy_state": st, "fit": strategies.FitResult(rule="rotation").to_dict(), "ruined_on": None,
            "margin_calls": 0, "n_entries": 0, "n_sync": 0, "n_closed": 0, "open_trade": None, "n_days": 0,
            "n_days_in_market": 0, "costs_total": 0.0}


def pending(wa, wb, reason="entry test"):
    return {"target": {"A": wa, "B": wb}, "reason": reason, "signal_date": "2026-07-17"}


# --------------------------------------------------------------------------- fills
def test_open_fill_at_raw_open_with_slippage_commission_borrow():
    ps = make_ps(pending=pending(0.5, -0.5))
    new, row, trades = engine.process_session(ps, pdata(50.0, 51.0, 20.0, 19.0), I, "T")
    # A: 0.5 x 100,000 / 50 = 1,000 sh, buy at 50 x 1.001; commission max($1, 0.005 x 1000) = $5
    # B: 0.5 x 100,000 / 20 = 2,500 sh short, sell at 20 x (1 - 0.0005); commission $12.50
    assert new["shares"] == pytest.approx([1000.0, -2500.0])
    a, b = trades
    assert (a["ticker"], a["side"], a["action"]) == ("AAA", "buy", "open")
    assert a["shares"] == pytest.approx(1000.0) and a["price"] == pytest.approx(50.05)
    assert a["raw_open"] == 50.0 and a["slippage"] == pytest.approx(50.0) and a["commission"] == pytest.approx(5.0)
    assert (b["ticker"], b["side"], b["action"]) == ("BBB", "sell", "open")
    assert b["shares"] == pytest.approx(2500.0) and b["price"] == pytest.approx(19.99)
    assert b["slippage"] == pytest.approx(25.0) and b["commission"] == pytest.approx(12.5)
    assert a["signal_date"] == "2026-07-17" and a["session"] == "2026-07-20" and a["reason"] == "entry test"
    borrow = 2500 * 19.0 * 0.03 / 252
    cash = 100_000 - 1000 * 50.05 - 5 + 2500 * 19.99 - 12.5 - borrow
    assert new["cash"] == pytest.approx(cash)
    assert new["equity"] == pytest.approx(cash + 1000 * 51.0 - 2500 * 19.0)      # marked at the RAW close
    assert row["costs"] == pytest.approx(50 + 25 + 5 + 12.5 + borrow)
    assert new["pending"] is None and new["cur_w"] == [0.5, -0.5] and new["n_entries"] == 1


def test_close_fill_uses_one_dollar_commission_minimum():
    ps = make_ps(shares=(100.0, -50.0), cur_w=(0.5, -0.5), cash=95_000.0, equity=100_000.0,
                 pending=pending(0.0, 0.0, "exit test"))
    ps["open_trade"] = {"entry_date": "2026-07-16", "reason": "x", "sync": False}
    new, _, trades = engine.process_session(ps, pdata(10.0, 10.0, 20.0, 20.0), I, "T")
    a, b = trades
    assert (a["side"], a["action"]) == ("sell", "close") and a["price"] == pytest.approx(10 * 0.999)
    assert (b["side"], b["action"]) == ("buy", "close") and b["price"] == pytest.approx(20 * 1.0005)
    assert a["commission"] == 1.0 and b["commission"] == 1.0        # 0.005 x 100 and 0.005 x 50 are below $1
    assert new["shares"] == [0.0, 0.0] and new["n_closed"] == 1 and new["open_trade"] is None
    assert new["cash"] == pytest.approx(95_000 + 100 * 10 * 0.999 - 50 * 20 * 1.0005 - 2.0)


def test_no_order_when_target_equals_current_weights():
    ps = make_ps(shares=(1000.0, -2500.0), cur_w=(0.5, -0.5), cash=100_000.0 - 50_000 + 50_000)
    new, row, trades = engine.process_session(ps, pdata(50.0, 50.0, 20.0, 20.0), I, "T")
    assert trades == [] and new["pending"] is None and row["queued_wa"] is None      # rotation keeps long A / short B


def test_split_and_dividends_apply_to_the_prior_close_position():
    # held: long 100 A, short 200 B.  A splits 2-for-1 (shares double, dividend paid on post-split shares), B pays 0.50
    ps = make_ps(shares=(100.0, -200.0), cur_w=(0.5, -0.5), cash=100_000.0, equity=100_000.0)
    new, row, _ = engine.process_session(ps, pdata(25.0, 25.0, 20.0, 20.0, div=(0.10, 0.50), split=(2.0, 0.0)), I, "T")
    assert new["shares"][0] == pytest.approx(200.0) and new["shares"][1] == pytest.approx(-200.0)
    assert row["dividends"] == pytest.approx(200 * 0.10 - 200 * 0.50)          # long receives, short pays
    borrow = 200 * 20.0 * 0.03 / 252
    assert new["cash"] == pytest.approx(100_000 + 20 - 100 - borrow)
    assert new["equity"] == pytest.approx(new["cash"] + 200 * 25.0 - 200 * 20.0)


def test_dividend_is_not_paid_on_a_position_opened_that_day():
    ps = make_ps(pending=pending(0.5, -0.5))
    new, row, _ = engine.process_session(ps, pdata(50.0, 50.0, 20.0, 20.0, div=(1.0, 1.0)), I, "T")
    assert row["dividends"] == 0.0                                          # nothing held at the prior close


def test_no_order_is_sized_from_non_positive_equity():
    ps = make_ps(equity=-5_000.0, cash=-5_000.0, pending=pending(0.5, -0.5))
    new, _, trades = engine.process_session(ps, pdata(50.0, 50.0, 20.0, 20.0), I, "T")
    assert trades == [] and new["shares"] == [0.0, 0.0]


# --------------------------------------------------------------------------- grid
def test_grid_window_at_matches_the_backtest_grid():
    sess = sessions(config.DOWNLOAD_START, "2026-10-26")
    starts = {w.test_start: w for w in walk_forward_grid(sess)}
    found = {i: engine.grid_window_at(sess, i) for i in range(len(sess))}
    assert {i for i, w in found.items() if w is not None} == set(starts)
    for i, w in found.items():
        if w is not None:
            assert (w.k, w.fit_start, w.fit_end) == (starts[i].k, starts[i].fit_start, starts[i].fit_end)
            assert w.fit_end - w.fit_start == config.TRAIN_LEN
    assert sess[min(starts)] == pd.Timestamp(config.GRID_START)
    grid_dates = [sess[i] for i, w in found.items() if w is not None]
    assert pd.Timestamp(START) in grid_dates and grid_dates[-1] == pd.Timestamp("2026-10-13")   # two refits in a run


# --------------------------------------------------------------------------- warm start
def _frames(pick, asof="2026-10-26"):
    p = CacheProvider(asof)
    return p.fetch(pick["leg_a"]), p.fetch(pick["leg_b"])


def _wreck(df: pd.DataFrame, after: pd.Timestamp, seed: int = 0) -> pd.DataFrame:
    """Violently change every bar dated after `after` (prices, splits, dividends)."""
    rng = np.random.default_rng(seed)
    out = df.copy()
    m = out.index > after
    for c in ("open", "high", "low", "close", "adjclose"):
        out.loc[m, c] = out.loc[m, c].to_numpy() * rng.uniform(0.2, 5.0, int(m.sum()))
    out.loc[m, "dividends"] = rng.uniform(0, 3, int(m.sum()))
    out.loc[m, "splits"] = rng.choice([0.0, 2.0, 0.1], int(m.sum()))
    return out


@pytest.mark.parametrize("pick", real_picks(), ids=lambda p: p["pick_id"])
def test_warm_start_cannot_see_data_after_start_minus_one(pick):
    sp = cal.prev_session(START)
    fa, fb = _frames(pick)
    ps, replay = engine.warm_start(pick, fa, fb, START, 100_000.0)
    ps2, replay2 = engine.warm_start(pick, _wreck(fa, sp, 1), _wreck(fb, sp, 2), START, 100_000.0)
    assert ps2 == ps                                      # state, fit, queued sync order: identical
    pd.testing.assert_frame_equal(replay2, replay)
    assert replay.index[-1] == sp and ps["last_processed"] == str(sp.date())
    # power check: changing the last allowed bar does change the state, so the test would notice a leak
    bad = fa.copy()
    bad.loc[sp, ["close", "adjclose", "open"]] *= 1.2
    ps3, _ = engine.warm_start(pick, bad, fb, START, 100_000.0)
    assert ps3 != ps


def test_warm_start_queues_the_backtests_open_position_as_a_sync_order():
    p = {p["pick_id"]: p for p in real_picks()}["pick_2"]               # rotation: always invested
    fa, fb = _frames(p)
    ps, _ = engine.warm_start(p, fa, fb, START, 100_000.0)
    assert ps["pending"]["reason"].startswith("sync: position carried from backtest replay (")
    assert ps["pending"]["signal_date"] == "2026-07-14"
    assert ps["pending"]["target"] == {"A": -0.5, "B": 0.5}
    assert ps["shares"] == [0.0, 0.0] and ps["equity"] == 100_000.0 and ps["cash"] == 100_000.0


def test_warm_start_fails_loudly_when_the_close_before_start_is_missing():
    p = real_picks()[1]
    fa, fb = _frames(p)
    with pytest.raises(DataError, match="2026-07-14"):
        engine.warm_start(p, fa.drop(index=[pd.Timestamp("2026-07-14")]), fb, START, 100_000.0)


# --------------------------------------------------------------------------- calendar and cutoff
@pytest.mark.parametrize("utc, expected", [
    (dt.datetime(2026, 7, 15, 19, 59, tzinfo=dt.timezone.utc), "2026-07-14"),     # 15:59 EDT: not final
    (dt.datetime(2026, 7, 15, 20, 9, tzinfo=dt.timezone.utc), "2026-07-14"),      # 16:09 EDT
    (dt.datetime(2026, 7, 15, 20, 10, tzinfo=dt.timezone.utc), "2026-07-15"),     # 16:10 EDT: final
    (dt.datetime(2026, 12, 15, 21, 9, tzinfo=dt.timezone.utc), "2026-12-14"),     # 16:09 EST
    (dt.datetime(2026, 12, 15, 21, 10, tzinfo=dt.timezone.utc), "2026-12-15"),    # 16:10 EST
])
def test_default_asof_close_cutoff(utc, expected):
    assert cal.default_asof(utc) == pd.Timestamp(expected)


def test_calendar_helpers_skip_weekends_and_holidays():
    assert not cal.is_session("2026-07-03") and not cal.is_session("2026-07-04")      # Independence Day observed
    assert cal.prev_session("2026-07-06") == pd.Timestamp("2026-07-02")
    assert cal.last_session_on_or_before("2026-08-15") == pd.Timestamp("2026-08-14")    # Saturday
    assert cal.nth_session_after("2026-07-02", 2) == pd.Timestamp("2026-07-07")
    assert len(cal.sessions_between("2026-07-03", "2026-07-05")) == 0


# --------------------------------------------------------------------------- yahoo provider (fake network)
def _yf_frame(asof_plus):
    df = CacheProvider("2026-10-26").fetch("SPY")
    h = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "adjclose": "Adj Close",
                           "volume": "Volume", "dividends": "Dividends", "splits": "Stock Splits"})
    h.index = pd.DatetimeIndex(h.index).tz_localize("America/New_York")
    return h[h.index < pd.Timestamp(asof_plus).tz_localize("America/New_York")]


def test_yahoo_provider_retries_then_succeeds_with_the_specified_request():
    calls, sleeps = [], []

    def history(ticker, start, end):
        calls.append((ticker, start, end))
        if len(calls) < 3:
            raise ConnectionError("boom")
        return _yf_frame(end)

    prov = YahooProvider("2026-07-10", history_fn=history, sleep=sleeps.append)
    df = prov.fetch("SPY")
    assert calls == [("SPY", config.DOWNLOAD_START, "2026-07-11")] * 3        # end = asof + 1 day
    assert sleeps == [2.0, 4.0]                                                # exponential backoff
    assert df.index[-1] == pd.Timestamp("2026-07-10") and list(df.columns)[:3] == ["open", "high", "low"]
    assert prov.fetch("SPY") is df and len(calls) == 3                         # memoised


def test_yahoo_provider_gives_up_after_four_attempts_and_never_returns_later_bars():
    calls = []

    def always_empty(ticker, start, end):
        calls.append(1)
        return pd.DataFrame()

    with pytest.raises(DataError, match="4 attempts"):
        YahooProvider("2026-07-10", history_fn=always_empty, sleep=lambda s: None).fetch("SPY")
    assert len(calls) == 4

    # a response that contains bars after asof is cut at asof
    prov = YahooProvider("2026-07-10", history_fn=lambda t, s, e: _yf_frame("2026-07-20"), sleep=lambda s: None)
    assert prov.fetch("SPY").index[-1] == pd.Timestamp("2026-07-10")
