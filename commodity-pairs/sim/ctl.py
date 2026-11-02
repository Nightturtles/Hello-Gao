"""Controls for the paper-trading simulator:  ``python -m sim.ctl {init,status,stop,extend,report,check-data}``

  init        write config.json for a new run (start, end, capital, a COPY of the picks); fetches no data.
  status      print the state summary.
  stop        set status 'stopped' and write the final report.
  extend      move the end date (--days N sessions or --until DATE); a finished run becomes 'running' again.
  report      write reports/final_sim_report.md now, without stopping.
  check-data  fetch the latest bars for every leg and SPY and print ticker / last bar date / last close.

All commands accept ``--base-dir DIR`` (default: the project root) so tests and dry runs never touch the real
``sim/state`` or ``reports``.  Exit codes: 0 ok, 1 data issue, 2 usage or refusal.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

from backtest import config, strategies

from . import cal, engine, reports, store
from .data import fetch_all, make_provider
from .run_daily import utc_stamp

PICK_KEYS = ("pick_id", "pair_id", "leg_a", "leg_b", "rule", "params", "slippage_bps", "borrow_rate")


# --------------------------------------------------------------------------- helpers
def validate_picks(picks: list[dict]) -> None:
    if not picks:
        raise ValueError("picks file contains no picks")
    seen = set()
    for p in picks:
        miss = [k for k in PICK_KEYS if k not in p]
        if miss:
            raise ValueError(f"pick {p.get('pick_id', '?')} is missing {miss}")
        if p["pick_id"] in seen:
            raise ValueError(f"duplicate pick_id {p['pick_id']}")
        seen.add(p["pick_id"])
        if p["rule"] not in strategies.RULES:
            raise ValueError(f"{p['pick_id']}: unknown rule {p['rule']}")
        for t in (p["leg_a"], p["leg_b"]):
            if t not in p["slippage_bps"] or t not in p["borrow_rate"]:
                raise ValueError(f"{p['pick_id']}: slippage_bps / borrow_rate missing for {t}")
        absent = [k for k in config.PARAMS if k not in p["params"]]
        if absent:
            raise ValueError(f"{p['pick_id']}: params missing {absent}")


def _load(paths: store.Paths, out=print):
    try:
        return store.load_config(paths)
    except store.ConfigError as e:
        out(str(e))
        return None


def _asof(a) -> pd.Timestamp:
    return pd.Timestamp(a.asof).normalize() if getattr(a, "asof", None) else cal.default_asof()


def _now_utc() -> str:
    return utc_stamp(dt.datetime.now(dt.timezone.utc))


# --------------------------------------------------------------------------- commands
def cmd_init(a, out=print) -> int:
    paths = store.Paths.of(a.base_dir)
    start = pd.Timestamp(a.start).normalize()
    if not cal.is_session(start):
        out(f"--start {start.date()} is not an NYSE session (next session: {cal.next_session_on_or_after(start).date()})")
        return 2
    if a.end:
        end = cal.last_session_on_or_before(a.end)
        if pd.Timestamp(a.end).normalize() != end:
            out(f"--end {a.end} is not an NYSE session: using the last session on or before it, {end.date()}")
    else:
        end = cal.last_session_on_or_before(start + pd.DateOffset(months=a.months))
    if end < start:
        out(f"end date {end.date()} is before the start date {start.date()}")
        return 2
    picks_path = Path(a.picks) if a.picks else store.PICKS_PATH
    try:
        picks = store.load_picks(picks_path)
        validate_picks(picks)
    except (OSError, KeyError, ValueError) as e:
        out(f"cannot use picks from {picks_path}: {e}")
        return 2
    existing = store.sim_artifacts(paths)
    if existing and not a.force:
        out("refusing to initialise: a run already exists here (use --force to replace it):")
        out("\n".join(f"  {p} ({n} file{'s' if n != 1 else ''})" for p, n in existing))
        return 2
    if existing:
        out("--force: removing the existing run (config.json is overwritten):")
        out("\n".join(f"  {p} ({n} file{'s' if n != 1 else ''})" for p, n in existing))
        store.remove_artifacts(paths)
    try:
        shown = str(picks_path.relative_to(store.PROJECT_ROOT))
    except ValueError:
        shown = str(picks_path)
    cfg = {"version": 1, "start": str(start.date()), "end": str(end.date()), "capital_per_pick": float(a.capital),
           "status": "running", "created_utc": _now_utc(), "picks_source": shown, "picks": picks}
    store.save_config(paths, cfg)
    n = len(cal.sessions_between(start, end))
    out(f"initialised {paths.config}: {len(picks)} picks, ${a.capital:,.0f} each, "
        f"{start.date()} -> {end.date()} ({n} sessions), status running")
    out(f"warm start happens on the first `run_daily` after the close of {cal.prev_session(start).date()}; "
        f"no data was fetched.")
    return 0


def cmd_status(a, out=print) -> int:
    paths = store.Paths.of(a.base_dir)
    cfg = _load(paths, out)
    if cfg is None:
        return 2
    state = store.load_state(paths)
    out(f"status: {cfg['status']} | start {cfg['start']} | end {cfg['end']} | capital ${cfg['capital_per_pick']:,.0f}/pick"
        f" | created {cfg['created_utc']}")
    total = 0.0
    for p in cfg["picks"]:
        ps = state["picks"].get(p["pick_id"])
        if ps is None:
            out(f"  {p['pick_id']} {p['leg_a']}/{p['leg_b']} {p['rule']}: not started (no warm start yet)")
            total += cfg["capital_per_pick"]
            continue
        total += ps["equity"]
        q = ps["pending"]
        queued = "none" if not q else (f"go flat ({q['reason']})" if not (q["target"]["A"] or q["target"]["B"])
                                       else f"A {q['target']['A']:+.3f} / B {q['target']['B']:+.3f} ({q['reason']})")
        out(f"  {p['pick_id']} {p['leg_a']}/{p['leg_b']} {p['rule']}: last {ps['last_processed']} "
            f"equity ${ps['equity']:,.2f} ({ps['equity'] / cfg['capital_per_pick'] - 1:+.2%}) "
            f"{engine.position_label(ps['shares'], ps['rule'], ps['strategy_state'])} | trades opened "
            f"{ps['n_entries']} (+{ps['n_sync']} carried), closed {ps['n_closed']} | margin calls {ps['margin_calls']}"
            f"{' | RUINED ' + ps['ruined_on'] if ps['ruined_on'] else ''} | queued: {queued}")
    out(f"  combined: ${total:,.2f} ({total / (cfg['capital_per_pick'] * len(cfg['picks'])) - 1:+.2%})")
    errs = store.read_errors(paths)
    out(f"  errors.log: {len(errs)} line(s)" + (f", last: {errs[-1]}" if errs else ""))
    return 0


def _write_reports(paths, cfg, provider, out, why: str) -> int:
    """Refresh summary.md and write the final report from the persisted logs (+ fetched data for SPY and parity)."""
    state = store.load_state(paths)
    ctx = reports.build_ctx(paths, cfg, state, None, _now_utc(), [])
    issues = reports.write_final_report(paths, ctx, None, provider)
    store.log_errors(paths, [f"{ctx.run_utc} {i.text()}" for i in issues])
    ctx.errors_log = store.read_errors(paths)
    store.atomic_write_text(paths.summary, reports.summary_report(ctx))
    out(f"{why}: wrote {paths.final}")
    for i in issues:
        out(f"  DATA ISSUE: {i.text()}")
    return 1 if issues else 0


def cmd_stop(a, out=print) -> int:
    paths = store.Paths.of(a.base_dir)
    cfg = _load(paths, out)
    if cfg is None:
        return 2
    if cfg["status"] == "stopped":
        out("already stopped; nothing changed")
        return 0
    was = cfg["status"]
    cfg = dict(cfg, status="stopped", stopped_utc=_now_utc())
    store.save_config(paths, cfg)
    out(f"status set to stopped (was {was})")
    return _write_reports(paths, cfg, a.provider, out, "stop")


def cmd_report(a, out=print) -> int:
    paths = store.Paths.of(a.base_dir)
    cfg = _load(paths, out)
    if cfg is None:
        return 2
    return _write_reports(paths, cfg, a.provider, out, "report")


def cmd_extend(a, out=print) -> int:
    paths = store.Paths.of(a.base_dir)
    cfg = _load(paths, out)
    if cfg is None:
        return 2
    if cfg["status"] == "stopped":
        out("the simulation was stopped; start a new one with `ctl init --force` instead of extending it")
        return 2
    old = pd.Timestamp(cfg["end"])
    if a.days is not None:
        if a.days < 1:
            out("--days must be at least 1")
            return 2
        new = cal.nth_session_after(old, a.days)
    else:
        new = cal.last_session_on_or_before(a.until)
    if new <= old:
        out(f"new end {new.date()} is not after the current end {old.date()}; nothing changed")
        return 2
    was = cfg["status"]
    cfg = dict(cfg, end=str(new.date()))
    if was == "finished":
        cfg["status"] = "running"
        cfg.pop("finished_utc", None)
    store.save_config(paths, cfg)
    out(f"end date {old.date()} -> {new.date()}; status {was}" + (" -> running" if was != cfg["status"] else ""))
    return 0


def cmd_check_data(a, out=print) -> int:
    paths = store.Paths.of(a.base_dir)
    try:
        picks = store.load_config(paths)["picks"]
    except store.ConfigError:
        picks = store.load_picks()
    asof = _asof(a)
    prov = make_provider(a.provider, asof)
    tickers = list(dict.fromkeys(engine.pick_tickers(picks) + [engine.SPY]))
    frames, errs = fetch_all(prov, tickers)
    expected = cal.last_session_on_or_before(asof)
    out(f"provider {a.provider}, asof {asof.date()} (latest session {expected.date()})")
    out(f"{'ticker':8s} {'last bar':12s} {'last close':>12s}")
    for t in tickers:
        if t in frames:
            f = frames[t]
            stale = "" if f.index[-1] >= expected else f"  (older than {expected.date()})"
            out(f"{t:8s} {str(f.index[-1].date()):12s} {f['close'].iloc[-1]:12.4f}{stale}")
        else:
            out(f"{t:8s} {'FAILED':12s} {errs[t]}")
    if errs:
        out(f"{len(errs)} ticker(s) failed")
        return 1
    return 0


# --------------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    def common(defaults: bool) -> argparse.ArgumentParser:
        c = argparse.ArgumentParser(add_help=False)
        d = (lambda v: v) if defaults else (lambda v: argparse.SUPPRESS)
        c.add_argument("--base-dir", default=d(None), help="directory holding sim/ and reports/ (default: project root)")
        c.add_argument("--provider", choices=["yahoo", "cache"], default=d("yahoo"))
        c.add_argument("--asof", default=d(None), help="YYYY-MM-DD; sessions up to it are treated as final")
        return c

    ap = argparse.ArgumentParser(prog="sim.ctl", description=__doc__.splitlines()[0], parents=[common(True)])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = common(False)
    p = sub.add_parser("init", parents=[sc], help="write config.json for a new run (no data is fetched)")
    p.add_argument("--start", required=True, help="first live session, YYYY-MM-DD (must be an NYSE session)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--months", type=int, default=1, help="run length in calendar months (default 1)")
    g.add_argument("--end", help="explicit last session, YYYY-MM-DD")
    p.add_argument("--force", action="store_true", help="replace an existing run (removes its state and reports)")
    p.add_argument("--picks", help="picks file (default: sim/picks.json in the project)")
    p.add_argument("--capital", type=float, default=config.START_CAPITAL, help="capital per pick")
    sub.add_parser("status", parents=[sc], help="print the state summary")
    sub.add_parser("stop", parents=[sc], help="stop the simulation and write the final report")
    p = sub.add_parser("extend", parents=[sc], help="move the end date")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--days", type=int, help="add N sessions")
    g.add_argument("--until", help="new end date YYYY-MM-DD")
    sub.add_parser("report", parents=[sc], help="write the final report now, without stopping")
    sub.add_parser("check-data", parents=[sc], help="fetch the latest bars for every leg and SPY")
    return ap


COMMANDS = {"init": cmd_init, "status": cmd_status, "stop": cmd_stop, "extend": cmd_extend, "report": cmd_report,
            "check-data": cmd_check_data}


def main(argv=None, out=print) -> int:
    a = build_parser().parse_args(argv)
    return COMMANDS[a.cmd](a, out)


if __name__ == "__main__":
    sys.exit(main())
