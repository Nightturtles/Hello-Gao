"""Paper-trading simulator, end to end on the cached research data (no network)."""
import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from backtest import config, walkforward
from sim import cal, compare, engine, reports, store
from sim.data import CacheProvider

from .sim_support import (END, START, Synthetic, assert_banner, copy_base, ctl_run, init, patched, real_picks,
                          reports_under, run, snapshot, strip_run_stamps, write_picks)

PICKS = {p["pick_id"]: p for p in real_picks()}
UTC = dt.timezone.utc


def subset(path, *ids):
    return write_picks(path / "picks_subset.json", [PICKS[i] for i in ids])


def daily_files(base):
    return sorted(p.name for p in (base / "reports" / "daily").glob("*.md")) if (base / "reports" / "daily").exists() else []


def state_of(base):
    return json.loads((base / "sim" / "state" / "state.json").read_text())


@pytest.fixture(scope="module")
def full_base(warm_template, tmp_path_factory):
    """The whole historical dry run START..END on the cache, done once for the read-only checks below."""
    b = copy_base(warm_template, tmp_path_factory.mktemp("full") / "base")
    assert run(b, END) == 0
    return b


# --------------------------------------------------------------------------- start, cutoff, idempotency
def test_waiting_for_start_does_nothing(tmp_path):
    assert init(tmp_path) == 0
    assert run(tmp_path, "2026-07-13") == 0
    assert not (tmp_path / "sim" / "state").exists() and not (tmp_path / "reports").exists()


def test_close_cutoff_new_york_16_10(tmp_path):
    assert init(tmp_path) == 0
    # 15:00 EDT on the start date: the close of the start-1 session is final (warm start), the start session is not
    assert run(tmp_path, None, now=dt.datetime(2026, 7, 15, 19, 0, tzinfo=UTC)) == 0
    assert state_of(tmp_path)["picks"]["pick_1"]["last_processed"] == "2026-07-14" and daily_files(tmp_path) == []
    # 16:09 EDT: still not final
    assert run(tmp_path, None, now=dt.datetime(2026, 7, 15, 20, 9, tzinfo=UTC)) == 0
    assert daily_files(tmp_path) == []
    # 16:10 EDT: final
    assert run(tmp_path, None, now=dt.datetime(2026, 7, 15, 20, 10, tzinfo=UTC)) == 0
    assert daily_files(tmp_path) == ["2026-07-15.md"]


def test_second_run_is_byte_identical(base):
    assert run(base, "2026-07-24") == 0
    first = snapshot(base)
    assert run(base, "2026-07-24") == 0
    assert snapshot(base) == first                       # state, logs, daily reports, summary: not rewritten
    assert "reports/summary.md" in first and len(daily_files(base)) == 8


def test_weekend_and_holiday_process_nothing(tmp_path):
    picks = subset(tmp_path, "pick_1", "pick_2")
    base = tmp_path / "b"
    assert init(base, "2026-06-29", "2026-07-17", picks) == 0
    assert run(base, "2026-07-02") == 0
    assert daily_files(base) == ["2026-06-29.md", "2026-06-30.md", "2026-07-01.md", "2026-07-02.md"]
    snap = snapshot(base)
    for asof in ("2026-07-03", "2026-07-04", "2026-07-05"):       # holiday (July 4 observed), Saturday, Sunday
        assert run(base, asof) == 0
        assert snapshot(base) == snap
    assert run(base, "2026-07-06") == 0
    assert daily_files(base)[-2:] == ["2026-07-02.md", "2026-07-06.md"]
    assert run(base, "2026-07-10") == 0
    snap = snapshot(base)
    for asof in ("2026-07-11", "2026-07-12"):
        assert run(base, asof) == 0
        assert snapshot(base) == snap


def test_catch_up_in_two_steps_equals_one_run(warm_template, tmp_path):
    two, one = copy_base(warm_template, tmp_path / "two"), copy_base(warm_template, tmp_path / "one")
    assert run(two, "2026-07-20") == 0 and run(two, "2026-07-23") == 0       # d1, then d1 + 3 sessions
    assert run(one, "2026-07-23") == 0
    a, b = strip_run_stamps(snapshot(two)), strip_run_stamps(snapshot(one))
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == b[k], k
    assert state_of(two)["picks"]["pick_1"]["last_processed"] == "2026-07-23"


def test_interrupted_run_is_repaired_not_double_counted(base):
    assert run(base, "2026-07-16") == 0
    clean = snapshot(base)
    # simulate a crash after the CSV rows of 2026-07-17 were appended but before the state was saved
    with open(base / "sim" / "state" / "equity.csv", "a") as f:
        f.write("2026-07-17,pick_1," + ",".join(["1"] * 17) + "\n")
    assert run(base, "2026-07-16") == 0
    assert snapshot(base) == clean
    assert run(base, "2026-07-17") == 0
    eq = store.read_equity(store.Paths.of(base))
    assert not eq.duplicated(["date", "pick_id"]).any() and len(eq) == 15


# --------------------------------------------------------------------------- missing data
@pytest.mark.parametrize("how", ["absent", "nan"])
def test_missing_bar_stops_only_that_pick(warm_template, tmp_path, how):
    bad = pd.Timestamp("2026-07-17")

    def patch(ticker, df):
        if ticker != "SILJ":
            return df
        if how == "absent":
            return df.drop(index=[bad])
        df = df.copy()
        df.loc[bad, "open"] = np.nan
        return df

    base, ref = copy_base(warm_template, tmp_path / "b"), copy_base(warm_template, tmp_path / "ref")
    assert run(ref, "2026-07-21") == 0
    assert run(base, "2026-07-21", provider=patched(patch)) == 1
    st = state_of(base)["picks"]
    assert st["pick_3"]["last_processed"] == "2026-07-16"
    assert all(st[p]["last_processed"] == "2026-07-21" for p in ("pick_1", "pick_2", "pick_4", "pick_5"))
    log = (base / "sim" / "state" / "errors.log").read_text()
    assert "pick_3" in log and "SILJ" in log and "2026-07-17" in log
    eq = store.read_equity(store.Paths.of(base))
    assert eq[eq.pick_id == "pick_3"]["date"].max() == pd.Timestamp("2026-07-16")
    assert eq[eq.pick_id == "pick_1"]["date"].max() == pd.Timestamp("2026-07-21")
    day = (base / "reports" / "daily" / "2026-07-21.md").read_text()
    assert "NOT ADVANCED" in day and "SILJ" in day
    assert "SILJ" in (base / "reports" / "summary.md").read_text()
    # the failure is logged again (never silent) while the data stays broken, and nothing else moves
    n_log = len(log.splitlines())
    assert run(base, "2026-07-21", provider=patched(patch)) == 1
    assert len((base / "sim" / "state" / "errors.log").read_text().splitlines()) > n_log
    # once the data is back the pick catches up and ends exactly where a clean run does
    assert run(base, "2026-07-21") == 0
    assert state_of(base)["picks"] == state_of(ref)["picks"]


def test_fetch_failure_blocks_dependent_picks_and_warm_start(tmp_path):
    class Down(CacheProvider):
        def _fetch(self, ticker):
            if ticker == "ET":
                from sim.data import DataError
                raise DataError("ET: yfinance failed after 4 attempts (empty response)")
            return super()._fetch(ticker)

    assert init(tmp_path) == 0
    assert run(tmp_path, "2026-07-17", provider=lambda asof: Down(asof)) == 1
    st = state_of(tmp_path)["picks"]
    assert set(st) == {"pick_1", "pick_2", "pick_3", "pick_4"}                 # pick_5 (ET/EPD) could not warm start
    assert "pick_5" in (tmp_path / "sim" / "state" / "errors.log").read_text()
    # later, with data back, pick_5 warm-starts from the SAME start-1 data and catches up
    assert run(tmp_path, "2026-07-17") == 0
    assert state_of(tmp_path)["picks"]["pick_5"]["last_processed"] == "2026-07-17"


# --------------------------------------------------------------------------- fills
def test_every_fill_is_at_the_next_raw_open_with_costs_and_the_right_size(full_base):
    paths = store.Paths.of(full_base)
    tr, eq, st = store.read_trades(paths), store.read_equity(paths), state_of(full_base)["picks"]
    cache = CacheProvider(END)
    assert len(tr) > 20 and {"open", "close"} <= set(tr["action"])
    for r in tr.itertuples():
        pick = PICKS[r.pick_id]
        assert pd.Timestamp(r.session) == cal.next_session(r.signal_date)               # next session's open
        raw = float(cache.fetch(r.ticker).loc[pd.Timestamp(r.session), "open"])
        slip = pick["slippage_bps"][r.ticker] / 1e4
        assert r.raw_open == pytest.approx(raw)
        assert r.price == pytest.approx(raw * (1 + slip) if r.side == "buy" else raw * (1 - slip))
        assert r.slippage == pytest.approx(r.shares * raw * slip)
        assert r.commission == pytest.approx(max(1.0, 0.005 * r.shares))
        leg = "A" if r.ticker == pick["leg_a"] else "B"
        if r.action == "open":
            sig = eq[(eq.pick_id == r.pick_id) & (eq.date == pd.Timestamp(r.signal_date))]
            if r.reason.startswith("sync:"):
                equity, w = 100_000.0, st[r.pick_id]["warm"]["final_target"][leg]
            else:
                equity = float(sig["equity"].iloc[0])
                w = float(sig["queued_wa" if leg == "A" else "queued_wb"].iloc[0])
            assert r.shares * raw == pytest.approx(abs(w) * equity)                      # weight x equity / raw open
            assert (r.side == "buy") == (w > 0)
        else:                                                                            # a close sells what was held
            sig = eq[(eq.pick_id == r.pick_id) & (eq.date == pd.Timestamp(r.signal_date))].iloc[0]
            held = sig["shares_a" if leg == "A" else "shares_b"]
            assert r.shares == pytest.approx(abs(held)) and (r.side == "sell") == (held > 0)


def test_sync_orders_and_refits_are_logged(full_base):
    paths = store.Paths.of(full_base)
    tr, eq = store.read_trades(paths), store.read_equity(paths)
    sync = tr[tr.reason.str.startswith("sync: position carried from backtest replay")]
    assert set(sync.pick_id) == {"pick_2", "pick_4", "pick_5"} and set(sync.session) == {"2026-07-15"}
    assert set(sync.signal_date) == {"2026-07-14"}
    refits = eq[eq.refit != ""]
    assert set(refits.date.dt.strftime("%Y-%m-%d")) == {"2026-07-15", "2026-10-13"}      # the two grid dates in the run
    for pid in PICKS:
        assert (full_base / "sim" / "state" / f"warmup_{pid}.csv").exists()


# --------------------------------------------------------------------------- parity with the backtest
def test_live_position_signs_equal_the_backtest_trial_files(full_base):
    paths = store.Paths.of(full_base)
    eq = store.read_equity(paths)
    sessions_live = cal.sessions_between(START, END)
    assert len(sessions_live) == 73
    for pid, pick in PICKS.items():
        trial = pd.read_csv(config.TRIALS_DIR / f"{pick['pair_id']}__{pick['rule']}.csv.gz", index_col=0,
                            parse_dates=True)
        live = eq[eq.pick_id == pid].set_index("date")
        assert list(live.index) == list(sessions_live)
        bt = trial.loc[sessions_live]
        # no margin call in either run, so there is nothing that could legitimately make the signs differ
        assert state_of(full_base)["picks"][pid]["margin_calls"] == 0
        assert (np.sign(bt["wA"].to_numpy()) == np.sign(live["shares_a"].to_numpy())).all(), pid
        assert (np.sign(bt["wB"].to_numpy()) == np.sign(live["shares_b"].to_numpy())).all(), pid
    # and the same statement, as the final report makes it
    final = (full_base / "reports" / "final_sim_report.md").read_text()
    assert "**Total: 365 of 365 sessions match.**" in final and "No mismatches." in final


def test_parity_check_names_every_mismatching_session(full_base):
    paths = store.Paths.of(full_base)
    cfg, state, eq = json.loads((full_base / "sim" / "config.json").read_text()), store.load_state(paths), store.read_equity(paths)
    frames = {t: CacheProvider(END).fetch(t) for t in engine.pick_tickers(cfg["picks"])}
    ok = compare.parity_check(cfg, state, eq, frames)
    assert all(q["n"] == 73 and q["matches"] == 73 and not q["mismatches"] for q in ok.values())
    bad = eq.copy()                                               # flip the simulator's leg-A sign on two sessions
    bad.loc[(bad.pick_id == "pick_2") & bad.date.isin(pd.to_datetime(["2026-08-03", "2026-08-04"])), "shares_a"] *= -1
    q = compare.parity_check(cfg, state, bad, frames)["pick_2"]
    assert [d for d, *_ in q["mismatches"]] == ["2026-08-03", "2026-08-04"] and q["matches"] == 71
    ctx = reports.build_ctx(paths, cfg, state, None, "T", [])
    text = reports.final_report(ctx, compare.parity_check(cfg, state, bad, frames))
    assert "- 2026-08-03: backtest sign" in text and "**Total: 363 of 365 sessions match.**" in text


def test_run_finishes_and_writes_the_final_report(full_base):
    assert json.loads((full_base / "sim" / "config.json").read_text())["status"] == "finished"
    final = (full_base / "reports" / "final_sim_report.md").read_text()
    for needle in ("Parity check", "Live versus backtest expectations", "All picks side by side",
                   "far too short to confirm or refute a strategy", "Percentile (full OOS)"):
        assert needle in final
    assert len(daily_files(full_base)) == 73


def test_every_report_starts_with_the_banner(full_base):
    files = reports_under(full_base)
    assert len(files) == 73 + 2
    for f in files:
        assert_banner(f)


# --------------------------------------------------------------------------- warm start end to end
def test_warm_start_is_unaffected_by_data_after_start_minus_one(warm_template, tmp_path):
    def wreck(ticker, df):
        out = df.copy()
        m = out.index > pd.Timestamp("2026-07-14")
        out.loc[m, ["open", "high", "low", "close", "adjclose"]] *= 3.7
        return out

    clean, dirty = copy_base(warm_template, tmp_path / "clean"), tmp_path / "dirty"
    assert init(dirty) == 0
    assert run(dirty, "2026-07-20", provider=patched(wreck)) == 0
    for pid in PICKS:
        a = (clean / "sim" / "state" / f"warmup_{pid}.csv").read_bytes()
        b = (dirty / "sim" / "state" / f"warmup_{pid}.csv").read_bytes()
        assert a == b
    qa = {k: v["pending"] for k, v in state_of(clean)["picks"].items()}
    for pid, q in qa.items():                                   # the queued sync order (target and reason) is the same
        trades = store.read_trades(store.Paths.of(dirty))
        got = trades[(trades.pick_id == pid) & (trades.session == "2026-07-15")]
        assert (len(got) > 0) == (q is not None)
        if q is not None:
            assert (got.reason == q["reason"]).all()


# --------------------------------------------------------------------------- account risk through the simulator
def _synth_run(tmp_path, factor):
    jump = pd.Timestamp("2026-07-17")

    def a(sess):
        c = 50.0 * np.exp(0.001 * np.arange(len(sess)))
        return np.r_[c[0], c[:-1]], c

    def b(sess):
        c = np.where(sess >= jump, 40.0 * factor, 40.0)
        return c.copy(), c

    def spy(sess):
        c = np.full(len(sess), 400.0)
        return c, c

    spec = {"AAA": a, "BBB": b, "SPY": spy}
    pick = {"pick_id": "m1", "pair_id": "AAA_BBB", "leg_a": "AAA", "leg_b": "BBB", "rule": "rotation",
            "params": config.PARAMS, "slippage_bps": {"AAA": 5.0, "BBB": 5.0}, "borrow_rate": {"AAA": 0.005, "BBB": 0.005}}
    pf = write_picks(tmp_path / "synth_picks.json", [pick])
    base = tmp_path / "b"
    assert init(base, START, "2026-07-31", pf) == 0
    assert run(base, "2026-07-24", provider=lambda asof: Synthetic(asof, spec)) == 0
    paths = store.Paths.of(base)
    return base, store.read_trades(paths), store.read_equity(paths).set_index("date"), state_of(base)["picks"]["m1"]


def test_margin_call_liquidates_at_the_next_open_and_resizes_from_the_remaining_equity(tmp_path):
    # carried long A / short B; B gaps to 2.5x on 2026-07-17 -> equity < 25% of gross at that close
    _, tr, eq, ps = _synth_run(tmp_path, 2.5)
    j, nxt = pd.Timestamp("2026-07-17"), pd.Timestamp("2026-07-20")
    gross = abs(eq.loc[j, "shares_a"]) * eq.loc[j, "close_a"] + abs(eq.loc[j, "shares_b"]) * eq.loc[j, "close_b"]
    assert walkforward.account_check(eq.loc[j, "equity"], gross) == "margin_call"
    assert walkforward.account_check(eq.loc[pd.Timestamp("2026-07-16"), "equity"], 1.0) is None
    assert eq.loc[j, "queued_reason"].startswith("margin call") and eq.loc[j, "queued_wa"] == 0.0
    closes = tr[tr.reason.str.startswith("margin call")]
    assert set(closes.session) == {"2026-07-20"} and set(closes.action) == {"close"} and len(closes) == 2
    assert closes[closes.ticker == "BBB"].iloc[0].side == "buy" and closes[closes.ticker == "AAA"].iloc[0].side == "sell"
    assert closes[closes.ticker == "BBB"].iloc[0].price == pytest.approx(100.0 * 1.0005)       # raw open + slippage
    assert eq.loc[nxt, "shares_a"] == 0.0 and eq.loc[nxt, "shares_b"] == 0.0 and ps["margin_calls"] == 1
    # the rule asks for a new position (it was force-flattened, not frozen): sized from the REMAINING equity
    reopen = tr[(tr.session == "2026-07-21") & (tr.action == "open")]
    assert len(reopen) == 2
    eq_before = eq.loc[nxt, "equity"]
    assert eq_before < 30_000
    for r in reopen.itertuples():
        assert r.shares * r.raw_open == pytest.approx(0.5 * eq_before)
    assert ps["ruined_on"] is None


def test_ruin_liquidates_and_never_trades_again(tmp_path):
    _, tr, eq, ps = _synth_run(tmp_path, 6.0)
    j = pd.Timestamp("2026-07-17")
    assert eq.loc[j, "equity"] < 0 and ps["ruined_on"] == "2026-07-17"
    assert eq.loc[j, "queued_reason"].startswith("ruin")
    after = tr[tr.session > "2026-07-17"]
    assert set(after.session) == {"2026-07-20"} and set(after.action) == {"close"}      # only the liquidation
    assert (eq.loc[pd.Timestamp("2026-07-20"):, ["shares_a", "shares_b"]] == 0).all().all()
    assert (eq.loc[pd.Timestamp("2026-07-21"):, "queued_wa"].isna()).all()              # no order is ever queued again
    assert eq.loc[pd.Timestamp("2026-07-24"), "equity"] == pytest.approx(eq.loc[pd.Timestamp("2026-07-20"), "equity"])


# --------------------------------------------------------------------------- controls
def test_status_report_stop_controls(base):
    assert run(base, "2026-07-16") == 0
    rc, lines = ctl_run(base, "status")
    assert rc == 0 and lines[0].startswith("status: running") and any("pick_3" in x for x in lines)
    rc, _ = ctl_run(base, "report", "--provider", "cache")                       # writes the report, does not stop
    assert rc == 0 and (base / "reports" / "final_sim_report.md").exists()
    assert json.loads((base / "sim" / "config.json").read_text())["status"] == "running"
    assert_banner(base / "reports" / "final_sim_report.md")
    rc, _ = ctl_run(base, "stop", "--provider", "cache")
    assert rc == 0 and json.loads((base / "sim" / "config.json").read_text())["status"] == "stopped"
    assert_banner(base / "reports" / "summary.md")
    snap = snapshot(base)
    assert run(base, "2026-07-24") == 0                                          # stopped: nothing is processed
    assert snapshot(base) == snap
    rc, lines = ctl_run(base, "extend", "--days", "3")
    assert rc == 2 and "stopped" in lines[0]
    rc, lines = ctl_run(base, "stop", "--provider", "cache")
    assert rc == 0 and "already stopped" in lines[0]


def test_finish_extend_and_unfinish(tmp_path):
    assert init(tmp_path, START, "2026-07-17") == 0
    assert run(tmp_path, "2026-07-24") == 0                                      # capped at the end date
    assert daily_files(tmp_path) == ["2026-07-15.md", "2026-07-16.md", "2026-07-17.md"]
    cfg = json.loads((tmp_path / "sim" / "config.json").read_text())
    assert cfg["status"] == "finished" and (tmp_path / "reports" / "final_sim_report.md").exists()
    assert "status **finished**" in (tmp_path / "reports" / "summary.md").read_text() or "finished" in \
        (tmp_path / "reports" / "summary.md").read_text()
    snap = snapshot(tmp_path)
    assert run(tmp_path, "2026-07-24") == 0 and snapshot(tmp_path) == snap
    rc, lines = ctl_run(tmp_path, "extend", "--days", "2")
    assert rc == 0 and "2026-07-21" in lines[0] and "finished -> running" in lines[0]
    assert json.loads((tmp_path / "sim" / "config.json").read_text())["status"] == "running"
    assert run(tmp_path, "2026-07-30") == 0
    assert daily_files(tmp_path)[-2:] == ["2026-07-20.md", "2026-07-21.md"] and len(daily_files(tmp_path)) == 5
    assert json.loads((tmp_path / "sim" / "config.json").read_text())["status"] == "finished"
    rc, lines = ctl_run(tmp_path, "extend", "--until", "2026-07-25")             # a Saturday: snaps to Friday 07-24
    assert rc == 0 and "2026-07-24" in lines[0]
    rc, _ = ctl_run(tmp_path, "extend", "--until", "2026-07-24")
    assert rc == 2                                                               # not after the current end
    assert run(tmp_path, "2026-08-10") == 0
    assert daily_files(tmp_path)[-1] == "2026-07-24.md" and len(daily_files(tmp_path)) == 8


def test_init_rules_force_and_frozen_picks(tmp_path):
    picks = subset(tmp_path, "pick_1", "pick_2")
    b = tmp_path / "b"
    rc, lines = ctl_run(b, "init", "--start", "2026-07-18")                      # a Saturday
    assert rc == 2 and "not an NYSE session" in lines[0]
    rc, lines = ctl_run(b, "init", "--start", START, "--picks", str(picks))
    assert rc == 0
    cfg = json.loads((b / "sim" / "config.json").read_text())
    assert cfg["end"] == "2026-08-14"                                            # 07-15 + 1 month = Sat 08-15 -> Friday
    assert cfg["status"] == "running" and cfg["capital_per_pick"] == 100_000.0 and cfg["created_utc"]
    assert [p["pick_id"] for p in cfg["picks"]] == ["pick_1", "pick_2"]
    assert not (b / "sim" / "state").exists()                                    # init fetches nothing, writes no state
    rc, lines = ctl_run(b, "init", "--start", START, "--picks", str(picks))
    assert rc == 2 and "--force" in " ".join(lines)
    # the picks are frozen into config.json: changing the picks file afterwards changes nothing
    write_picks(picks, [PICKS["pick_5"]])
    assert run(b, "2026-07-16") == 0
    assert set(state_of(b)["picks"]) == {"pick_1", "pick_2"}
    # --force prints and removes the run's own files only
    (b / "reports").mkdir(exist_ok=True)
    (b / "reports" / "final_research_report.md").write_text("keep me")
    rc, lines = ctl_run(b, "init", "--start", START, "--end", "2026-07-31", "--force", "--picks", str(picks))
    out = " ".join(lines)
    assert rc == 0 and "removing" in out and "state" in out and "daily" in out
    assert not (b / "sim" / "state").exists() and not (b / "reports" / "daily").exists()
    assert not (b / "reports" / "summary.md").exists()
    assert (b / "reports" / "final_research_report.md").read_text() == "keep me"
    assert json.loads((b / "sim" / "config.json").read_text())["end"] == "2026-07-31"


def test_check_data_reports_every_ticker_and_fails_on_a_missing_one(base, tmp_path):
    rc, lines = ctl_run(base, "check-data", "--provider", "cache", "--asof", "2026-10-26")
    assert rc == 0 and len(lines) == 2 + 11 and lines[-1].startswith("SPY")
    assert "2026-10-26" in lines[-1]
    bogus = dict(PICKS["pick_1"], pick_id="x", leg_a="ZZZZ", slippage_bps={"ZZZZ": 5.0, "DE": 5.0},
                 borrow_rate={"ZZZZ": 0.005, "DE": 0.005})
    b2 = tmp_path / "b2"
    assert init(b2, START, END, write_picks(tmp_path / "bogus.json", [bogus])) == 0
    rc, lines = ctl_run(b2, "check-data", "--provider", "cache", "--asof", "2026-10-26")
    assert rc == 1 and any("ZZZZ" in x and "FAILED" in x for x in lines)
