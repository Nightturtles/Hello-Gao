"""One paper-trading run:  ``python -m sim.run_daily [--asof YYYY-MM-DD] [--provider yahoo|cache] [--base-dir DIR]``

Idempotent and resumable: sessions are processed strictly in order, state is saved atomically after every
(pick, session), a second run with nothing new changes no file, and missed sessions are caught up.  Missing data for a
pick leaves that pick un-advanced (logged, shown in the reports, exit code 1); the other picks carry on.

Exit code: 0 = no issues, 1 = at least one data issue, 2 = no config (run ``python -m sim.ctl init`` first).
No broker is involved anywhere: every fill is simulated.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import traceback

import pandas as pd

from backtest import config
from backtest.trading_calendar import sessions

from . import cal, engine, reports, store
from .data import DataError, Issue, fetch_all, make_provider

SPY = engine.SPY


def utc_stamp(now: dt.datetime) -> str:
    return now.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(base_dir=None, provider="yahoo", asof=None, now: dt.datetime | None = None, out=print) -> int:
    paths = store.Paths.of(base_dir)
    try:
        cfg = store.load_config(paths)
    except store.ConfigError as e:
        out(str(e))
        return 2
    if cfg["status"] != "running":
        out(f"simulation status is '{cfg['status']}': nothing to do")
        return 0
    now = now or dt.datetime.now(dt.timezone.utc)
    run_utc = utc_stamp(now)
    asof_ts = pd.Timestamp(asof).normalize() if asof else cal.default_asof(now)
    start, end = pd.Timestamp(cfg["start"]), pd.Timestamp(cfg["end"])
    start_prev = cal.prev_session(start)
    picks = cfg["picks"]
    capital = float(cfg["capital_per_pick"])

    state = store.load_state(paths)
    for note in store.repair(paths, state):
        out(f"repaired after an interrupted run: {note}")
    need_warm = [p for p in picks if p["pick_id"] not in state["picks"]]
    can_warm = asof_ts >= start_prev
    if need_warm and not state["picks"] and not can_warm:
        out(f"waiting for start: the close of {start_prev.date()} (session before {start.date()}) is not final yet "
            f"(asof {asof_ts.date()})")
        return 0
    target_last = min(asof_ts, end)

    # ---- which sessions each pick still has to process (calendar only; no network yet)
    todo: dict[str, pd.DatetimeIndex] = {}
    for p in picks:
        ps = state["picks"].get(p["pick_id"])
        if ps is None and not can_warm:
            continue
        lp = pd.Timestamp(ps["last_processed"]) if ps else start_prev
        todo[p["pick_id"]] = cal.sessions_between(lp + pd.Timedelta(days=1), target_last)
    warm_list = [p for p in need_warm] if can_warm else []
    work = bool(warm_list) or any(len(v) for v in todo.values())

    issues: list[Issue] = []
    warmed: list[str] = []
    newly: dict[pd.Timestamp, list[str]] = {}
    frames: dict = {}
    spy: pd.Series | None = None
    last_needed = max(target_last, start_prev)

    if work:
        sess = sessions(config.DOWNLOAD_START, last_needed)
        prov = make_provider(provider, last_needed)
        active = [p for p in picks if p in warm_list or len(todo.get(p["pick_id"], [])) > 0]
        frames, ferrors = fetch_all(prov, engine.pick_tickers(active) + [SPY])
        if SPY in frames:
            spy = frames[SPY]["adjclose"].astype(float)
        else:
            issues.append(Issue(f"SPY fetch failed ({ferrors.get(SPY, 'unknown')}); SPY comparison shows n/a"))

        def blocked(p) -> list[str]:
            return [ferrors[t] for t in (p["leg_a"], p["leg_b"]) if t in ferrors]

        # ---- warm start (once per pick; retried on a later run if its data was unavailable)
        for p in warm_list:
            pid = p["pick_id"]
            if blocked(p):
                issues.append(Issue(f"warm start blocked: {'; '.join(blocked(p))}", pid, str(start.date())))
                continue
            try:
                ps, replay = engine.warm_start(p, frames[p["leg_a"]], frames[p["leg_b"]], start, capital)
            except DataError as e:
                issues.append(Issue(f"warm start failed: {e}", pid, str(start.date())))
                continue
            store.atomic_write_text(paths.warmup(pid), replay.to_csv(float_format="%.10g", lineterminator="\n"))
            state["picks"][pid] = ps
            store.save_state(paths, state)
            warmed.append(pid)

        # ---- daily loop, session-major (so the logs are in the same order however the run is split): every pick
        # advances through its own sessions in order; a pick that hits a data problem stops there, the rest carry on
        live: dict[str, engine.PickData] = {}
        for p in picks:
            pid = p["pick_id"]
            if pid not in state["picks"] or len(todo.get(pid, [])) == 0:
                continue
            if blocked(p):
                issues.append(Issue(f"fetch failed ({'; '.join(blocked(p))}); not advanced past "
                                    f"{state['picks'][pid]['last_processed']}", pid, str(todo[pid][0].date())))
                continue
            live[pid] = engine.build_pick_data(p, frames[p["leg_a"]], frames[p["leg_b"]], sess)
        for d in sorted(set().union(*[set(todo[pid]) for pid in live])) if live else []:
            i = int(sess.get_loc(d))
            for p in picks:
                pid = p["pick_id"]
                if pid not in live or d not in todo[pid]:
                    continue
                ps = state["picks"][pid]
                msg = engine.check_data(live[pid], i)
                if msg:
                    issues.append(Issue(f"{msg}; not advanced past {ps['last_processed']}", pid, str(d.date())))
                    del live[pid]
                    continue
                try:
                    new_ps, erow, trows = engine.process_session(ps, live[pid], i, run_utc)
                except Exception as e:  # noqa: BLE001 - one pick's bug must not stop the others
                    issues.append(Issue(f"internal error {type(e).__name__}: {e}", pid, str(d.date())))
                    store.log_errors(paths, traceback.format_exc().splitlines())
                    del live[pid]
                    continue
                store.append_rows(paths.equity, store.EQUITY_COLS, [erow])
                store.append_rows(paths.trades, store.TRADE_COLS, trows)
                state["picks"][pid] = new_ps
                store.save_state(paths, state)
                newly.setdefault(d, []).append(pid)

    store.log_errors(paths, [f"{run_utc} {i.text()}" for i in issues])

    # ---- done?  every pick has processed the end date
    finished = all(p["pick_id"] in state["picks"] and pd.Timestamp(state["picks"][p["pick_id"]]["last_processed"]) >= end
                   for p in picks)
    if finished:
        cfg = dict(cfg, status="finished", finished_utc=run_utc)

    if newly or warmed or issues or finished:
        ctx = reports.build_ctx(paths, cfg, state, spy, run_utc, issues)
        for d in sorted(newly):
            store.atomic_write_text(paths.daily(d), reports.daily_report(ctx, d))
        if finished:                    # first: it can fetch SPY, which the summary also shows
            extra = reports.write_final_report(paths, ctx, frames, provider)
            store.log_errors(paths, [f"{run_utc} {i.text()}" for i in extra])
            issues += extra
        store.atomic_write_text(paths.summary, reports.summary_report(ctx))
        if finished:
            store.save_config(paths, cfg)

    out(render_console(cfg, state, asof_ts, newly, warmed, issues, work, provider))
    return 1 if issues else 0


def render_console(cfg, state, asof_ts, newly, warmed, issues, work, provider) -> str:
    prov = provider if isinstance(provider, str) else getattr(provider, "name", "custom")
    lines = [f"paper-sim: asof {asof_ts.date()}, provider {prov}, status {cfg['status']}, "
             f"{cfg['start']} -> {cfg['end']}"]
    if warmed:
        lines.append(f"  warm start done for: {', '.join(warmed)}")
    if not work:
        lines.append("  nothing new to process")
    for p in cfg["picks"]:
        ps = state["picks"].get(p["pick_id"])
        n = sum(1 for v in newly.values() if p["pick_id"] in v)
        if ps is None:
            lines.append(f"  {p['pick_id']} {p['leg_a']}/{p['leg_b']}: not started")
            continue
        q = ps["pending"]
        queued = "" if not q else (" | queued: flat" if not (q["target"]["A"] or q["target"]["B"])
                                   else " | queued: open/change position")
        lines.append(f"  {p['pick_id']} {p['leg_a']}/{p['leg_b']} {p['rule']}: +{n} session(s), last {ps['last_processed']}, "
                     f"equity ${ps['equity']:,.2f}{queued}")
    if issues:
        lines.append(f"  {len(issues)} DATA ISSUE(S):")
        lines += [f"    - {i.text()}" for i in issues]
    else:
        lines.append("  data issues: none")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="sim.run_daily", description=__doc__.splitlines()[0])
    ap.add_argument("--asof", help="treat sessions up to this date (YYYY-MM-DD) as final; default: today in New York "
                    "once it is past 16:10 New York time, else yesterday")
    ap.add_argument("--provider", choices=["yahoo", "cache"], default="yahoo")
    ap.add_argument("--base-dir", help="directory holding sim/ and reports/ (default: the project root)")
    a = ap.parse_args(argv)
    return run(a.base_dir, a.provider, a.asof)


if __name__ == "__main__":
    sys.exit(main())
