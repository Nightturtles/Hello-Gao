"""Markdown reports: daily, rolling summary and the final comparison.

Every report starts with ``BANNER`` (verbatim).  Reports are built from the persisted logs (``equity.csv``,
``trades.csv``, ``state.json``) plus SPY, never from in-memory run state, so a report for an old session regenerated in
a later run (e.g. after a stuck pick catches up) is complete.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import cal, compare, engine, store
from .data import Issue, fetch_all, make_provider

BANNER = ("> ⚠️ **None of these 5 pairs passed the research bar.** They are paper-traded only to check that the "
          "live system behaves exactly as backtested — not as investment candidates. "
          "See reports/final_research_report.md.")

REQUIRED_STATEMENT = ("One month of live results is far too short to confirm or refute a strategy. The live run "
                      "checks that the system behaves as backtested; it is not evidence of an edge.")


@dataclass
class Ctx:
    cfg: dict
    state: dict
    equity: pd.DataFrame
    trades: pd.DataFrame
    spy: pd.Series | None            # SPY adjusted close by date (None = unavailable)
    run_utc: str
    issues: list[Issue] = field(default_factory=list)
    errors_log: list[str] = field(default_factory=list)

    @property
    def start(self) -> pd.Timestamp:
        return pd.Timestamp(self.cfg["start"])

    @property
    def end(self) -> pd.Timestamp:
        return pd.Timestamp(self.cfg["end"])

    @property
    def base_date(self) -> pd.Timestamp:
        """The close of the session before the start: the baseline for every since-start figure."""
        return cal.prev_session(self.start)

    @property
    def picks(self) -> list[dict]:
        return self.cfg["picks"]

    @property
    def capital(self) -> float:
        return float(self.cfg["capital_per_pick"])


# --------------------------------------------------------------------------- formatting
def usd(x: float, signed: bool = False) -> str:
    if x is None or not math.isfinite(x):
        return "n/a"
    s = f"${abs(x):,.0f}"
    if x < 0:
        return "-" + s
    return ("+" + s) if signed and x > 0 else s


def pct(x: float, digits: int = 2, signed: bool = True) -> str:
    if x is None or not math.isfinite(x):
        return "n/a"
    if round(x * 100, digits) == 0:
        x = 0.0                                     # no "-0.00%"
    return f"{x * 100:+.{digits}f}%" if signed else f"{x * 100:.{digits}f}%"


def num(x, fmt: str = ".2f") -> str:
    return "n/a" if x is None or not math.isfinite(x) else format(x, fmt)


def table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out)


def ordinal(x: float) -> str:
    if x is None or not math.isfinite(x):
        return "n/a"
    n = int(round(x))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _pct_cell(p: float, n_windows: int) -> str:
    return f"{ordinal(p)} percentile ({n_windows} windows)" if n_windows else "n/a"


def pair_label(pick: dict) -> str:
    return f"{pick['leg_a']}/{pick['leg_b']} · {pick['rule']}"


# --------------------------------------------------------------------------- series
def pick_curve(ctx: Ctx, pid: str) -> pd.Series:
    """Equity by date including the baseline (start capital at the close before the start)."""
    rows = ctx.equity[ctx.equity["pick_id"] == pid].sort_values("date")
    s = pd.Series(rows["equity"].to_numpy(dtype=float), index=pd.DatetimeIndex(rows["date"]), dtype=float)
    return pd.concat([pd.Series({ctx.base_date: ctx.capital}), s])


def combined_curve(ctx: Ctx) -> pd.Series:
    """Sum of the sub-portfolios; a pick with no row for a date is carried forward at its last equity."""
    df = pd.DataFrame({p["pick_id"]: pick_curve(ctx, p["pick_id"]) for p in ctx.picks}).sort_index().ffill()
    return df.sum(axis=1, min_count=1)


def max_drawdown(curve: pd.Series) -> float:
    v = curve.to_numpy(dtype=float)
    if len(v) == 0:
        return float("nan")
    peak = np.maximum.accumulate(v)
    return float(np.max(np.where(peak > 0, 1.0 - v / peak, 0.0)))


def ann_vol(curve: pd.Series) -> float:
    r = curve.pct_change().dropna().to_numpy()
    return float(r.std(ddof=1) * math.sqrt(252)) if len(r) >= 2 else float("nan")


def spy_return(ctx: Ctx, d0, d1) -> float:
    if ctx.spy is None:
        return float("nan")
    s = ctx.spy
    d0, d1 = pd.Timestamp(d0), pd.Timestamp(d1)
    if d0 not in s.index or d1 not in s.index or not (s[d0] > 0):
        return float("nan")
    return float(s[d1] / s[d0] - 1.0)


def session_index(ctx: Ctx, d) -> tuple[int, int]:
    s = cal.sessions_between(ctx.start, ctx.end)
    d = pd.Timestamp(d)
    return (int(s.get_loc(d)) + 1 if d in s else 0), len(s)


def last_row(ctx: Ctx, pid: str, d=None) -> pd.Series | None:
    rows = ctx.equity[ctx.equity["pick_id"] == pid]
    if d is not None:
        rows = rows[rows["date"] == pd.Timestamp(d)]
    return rows.iloc[-1] if len(rows) else None


def position_cell(shares: float, price: float, ticker: str) -> str:
    if shares == 0 or not math.isfinite(shares):
        return "—"
    side = "long" if shares > 0 else "short"
    return f"{side} {abs(shares):,.2f} {ticker} ({usd(abs(shares) * price)})"


def queued_cell(row: pd.Series | None, pick: dict) -> str:
    if row is None or pd.isna(row["queued_wa"]):
        return "none"
    wa, wb = float(row["queued_wa"]), float(row["queued_wb"])
    why = row["queued_reason"]
    if abs(wa) < 1e-12 and abs(wb) < 1e-12:
        return f"go flat — {why}"
    return f"{pick['leg_a']} {wa:+.1%} / {pick['leg_b']} {wb:+.1%} of equity — {why}"


def _issue_lines(issues: list[Issue], upto=None) -> list[str]:
    sel = [i for i in issues if upto is None or i.session is None or pd.Timestamp(i.session) <= pd.Timestamp(upto)]
    return [f"- {i.text()}" for i in sel]


def _header(title: str, ctx: Ctx, extra: str = "") -> list[str]:
    return [BANNER, "", f"# {title}", "", f"_Generated {ctx.run_utc} (UTC)._{extra}", ""]


# --------------------------------------------------------------------------- daily
def daily_report(ctx: Ctx, d) -> str:
    d = pd.Timestamp(d)
    prev = cal.prev_session(d)
    day_no, n_total = session_index(ctx, d)
    lines = _header(f"Paper-trading daily report: {d.date()}", ctx,
                    f" Session {day_no} of {n_total} (start {ctx.start.date()}, end {ctx.end.date()}), "
                    f"status **{ctx.cfg['status'] if d >= ctx.end else 'running'}**. Prices: RAW opens/closes; "
                    f"signals: adjusted closes.")
    rows, posrows = [], []
    stale = []
    for p in ctx.picks:
        pid = p["pick_id"]
        r = last_row(ctx, pid, d)
        if r is None:
            lp = ctx.state["picks"].get(pid, {}).get("last_processed")
            stale.append(pid)
            rows.append([pid, pair_label(p), "—", "—", "—", "—", "—", f"NOT ADVANCED (last processed {lp})", "—"])
            posrows.append([pid, "—", "—", "—"])
            continue
        curve = pick_curve(ctx, pid)
        prev_eq = float(curve[:prev].iloc[-1]) if len(curve[:prev]) else ctx.capital
        eq = float(r["equity"])
        rows.append([pid, pair_label(p), usd(eq), usd(eq - prev_eq, True), pct(eq / prev_eq - 1),
                     pct(eq / ctx.capital - 1), pct(-float(r["drawdown"]), signed=False) if r["drawdown"] else "0.00%",
                     r["state"], num(r["z"])])
        posrows.append([pid, position_cell(float(r["shares_a"]), float(r["close_a"]), p["leg_a"]),
                        position_cell(float(r["shares_b"]), float(r["close_b"]), p["leg_b"]), queued_cell(r, p)])
    comb = combined_curve(ctx)
    ce = float(comb[:d].iloc[-1])
    cp = float(comb[:prev].iloc[-1]) if len(comb[:prev]) else ctx.capital * len(ctx.picks)
    hwm = float(comb[:d].max())
    total_cap = ctx.capital * len(ctx.picks)
    rows.append([f"**Combined** ({usd(total_cap)})", f"{len(ctx.picks)} sub-portfolios", usd(ce), usd(ce - cp, True),
                 pct(ce / cp - 1), pct(ce / total_cap - 1), pct(-(1 - ce / hwm), signed=False) if hwm > ce else "0.00%",
                 "", ""])
    lines += ["## Equity and P&L", "",
              table(["Pick", "Pair · rule", "Equity", "Day P&L", "Day %", "Since start", "Drawdown from high",
                     "State", "z / signal"], rows), "",
              "## Positions at the close and order queued for the next open", "",
              table(["Pick", "Leg A", "Leg B", "Queued order"], posrows), ""]
    sd = spy_return(ctx, prev, d)
    ss = spy_return(ctx, ctx.base_date, d)
    lines += ["## SPY comparison", "",
              table(["", "Day", f"Since start (close of {ctx.base_date.date()})"],
                    [["Combined", pct(ce / cp - 1), pct(ce / total_cap - 1)],
                     ["SPY (total return, adjusted close)", pct(sd), pct(ss)],
                     ["Combined minus SPY", pct((ce / cp - 1) - sd), pct((ce / total_cap - 1) - ss)]]), ""]
    tr = ctx.trades[ctx.trades["session"] == str(d.date())]
    lines += ["## Trades filled today", ""]
    if len(tr):
        lines += [table(["Pick", "Ticker", "Side", "Action", "Shares", "Raw open", "Fill price", "Slippage $",
                         "Commission $", "Reason (signal date)"],
                        [[t.pick_id, t.ticker, t.side, t.action, f"{t.shares:,.4f}", f"{t.raw_open:,.4f}",
                          f"{t.price:,.4f}", f"{t.slippage:,.2f}", f"{t.commission:,.2f}",
                          f"{t.reason} ({t.signal_date})"] for t in tr.itertuples()]), ""]
    else:
        lines += ["none", ""]
    rf = ctx.equity[(ctx.equity["date"] == d) & (ctx.equity["refit"] != "")]
    if len(rf):
        lines += ["## Refits today", ""] + [f"- {r.pick_id}: {r.refit}" for r in rf.itertuples()] + [""]
    issues = _issue_lines(ctx.issues, d)
    if ctx.spy is not None and (d not in ctx.spy.index):
        issues.append(f"- SPY: no bar for {d.date()} (comparison shows n/a)")
    if stale:
        issues.append(f"- not advanced to {d.date()}: {', '.join(stale)}")
    lines += ["## Data issues", ""] + (issues or ["none"]) + [""]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- summary
def _pick_stats(ctx: Ctx, p: dict) -> dict:
    pid = p["pick_id"]
    ps = ctx.state["picks"].get(pid)
    curve = pick_curve(ctx, pid)
    eq = float(curve.iloc[-1])
    r = last_row(ctx, pid)
    return {"pid": pid, "ps": ps, "curve": curve, "eq": eq, "ret": eq / ctx.capital - 1,
            "mdd": max_drawdown(curve), "row": r,
            "last": ps["last_processed"] if ps else None,
            "opened": (ps["n_entries"] if ps else 0), "sync": (ps["n_sync"] if ps else 0),
            "closed": (ps["n_closed"] if ps else 0)}


def summary_report(ctx: Ctx) -> str:
    cfg = ctx.cfg
    processed = [pd.Timestamp(ps["last_processed"]) for ps in ctx.state["picks"].values()]
    done = [d for d in processed if d >= ctx.start]
    latest = max(done) if done else None
    lines = _header("Paper-trading summary", ctx)
    lines.append(f"**Status: {cfg['status']}** · start {cfg['start']} · end {cfg['end']} · "
                 f"capital {usd(ctx.capital)} per pick ({usd(ctx.capital * len(ctx.picks))} total)")
    if latest is not None:
        lines.append(f"Latest daily report: [{latest.date()}](daily/{latest.date()}.md)")
    else:
        lines.append("No session processed yet" + (" (warm start done; waiting for the first session)."
                     if ctx.state["picks"] else "."))
    lines.append("")
    rows = []
    for p in ctx.picks:
        s = _pick_stats(ctx, p)
        r = s["row"]
        rows.append([s["pid"], pair_label(p), s["last"] or "not started", usd(s["eq"]), pct(s["ret"]),
                     pct(-s["mdd"], signed=False) if s["mdd"] else "0.00%",
                     f"{s['opened']} (+{s['sync']} carried) / {s['closed']}",
                     r["state"] if r is not None else "—",
                     queued_cell(r, p) if r is not None else (
                         queued_cell(pd.Series({"queued_wa": s["ps"]["pending"]["target"]["A"],
                                                "queued_wb": s["ps"]["pending"]["target"]["B"],
                                                "queued_reason": s["ps"]["pending"]["reason"]}), p)
                         if s["ps"] and s["ps"]["pending"] else "none")])
    comb = combined_curve(ctx)
    total_cap = ctx.capital * len(ctx.picks)
    cl = comb.index[-1]
    rows.append(["**Combined**", f"{len(ctx.picks)} sub-portfolios", str(cl.date()), usd(float(comb.iloc[-1])),
                 pct(float(comb.iloc[-1]) / total_cap - 1), pct(-max_drawdown(comb), signed=False)
                 if max_drawdown(comb) else "0.00%", "", "", ""])
    lines += ["## Per pick", "",
              table(["Pick", "Pair · rule", "Last processed", "Equity", "Cumulative return", "Max drawdown",
                     "Trades opened / closed", "State", "Order queued"], rows), ""]
    spy_total = spy_return(ctx, ctx.base_date, cl)
    lines += ["## Combined result vs SPY", "",
              table(["", "Return since start", "Max drawdown"],
                    [["Combined", pct(float(comb.iloc[-1]) / total_cap - 1), pct(-max_drawdown(comb), signed=False)],
                     [f"SPY (total return, to {cl.date()})", pct(spy_total), ""]]), ""]
    lines += ["## Daily combined equity", ""]
    drows = []
    prev_v = total_cap
    for d, v in comb.items():
        if d < ctx.start:
            continue
        drows.append([f"[{d.date()}](daily/{d.date()}.md)", usd(float(v)), pct(float(v) / prev_v - 1),
                      pct(float(v) / total_cap - 1), pct(spy_return(ctx, ctx.base_date, d))])
        prev_v = float(v)
    lines += [table(["Session", "Combined equity", "Day %", "Since start", "SPY since start"], drows)
              if drows else "none yet", ""]
    issues = _issue_lines(ctx.issues)
    lines += ["## Data issues (latest run)", ""] + (issues or ["none"]) + [""]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- final
def _exit_cost(ps: dict | None, pick: dict, closes) -> float:
    """Estimated cost of closing the open position at the last close: slippage on both legs plus commissions."""
    if not ps or closes is None:
        return 0.0
    cost = 0.0
    for leg, t in enumerate((pick["leg_a"], pick["leg_b"])):
        sh = ps["shares"][leg]
        if sh != 0:
            cost += abs(sh) * closes[leg] * engine.leg_slip(pick, t) + engine.commission(sh)
    return cost


def final_report(ctx: Ctx, parity: dict | None, parity_note: str = "") -> str:
    cfg = ctx.cfg
    total_cap = ctx.capital * len(ctx.picks)
    comb = combined_curve(ctx)
    cl = comb.index[-1]
    lines = _header("Final paper-trading report", ctx,
                    f" Period {cfg['start']} to {cfg['end']}; status **{cfg['status']}**; last processed session "
                    f"{cl.date() if cl >= ctx.start else 'none'}.")
    lines += [f"> **{REQUIRED_STATEMENT}**", ""]

    # ---- side by side
    rows, exp_rows = [], []
    stats = {p["pick_id"]: _pick_stats(ctx, p) for p in ctx.picks}
    for p in ctx.picks:
        s = stats[p["pick_id"]]
        ps, curve = s["ps"], s["curve"]
        r = s["row"]
        exit_cost = _exit_cost(ps, p, (float(r["close_a"]), float(r["close_b"])) if r is not None else None)
        eqrows = ctx.equity[ctx.equity["pick_id"] == p["pick_id"]]
        gross = (eqrows["shares_a"].abs() * eqrows["close_a"] + eqrows["shares_b"].abs() * eqrows["close_b"])
        avg_gross = float((gross / eqrows["equity"].where(eqrows["equity"] > 0)).mean()) if len(eqrows) else float("nan")
        n_days = s["ps"]["n_days"] if s["ps"] else 0
        in_mkt = s["ps"]["n_days_in_market"] if s["ps"] else 0
        spy_r = spy_return(ctx, ctx.base_date, s["last"]) if s["last"] else float("nan")
        rows.append([s["pid"], pair_label(p), pct(s["ret"]), pct(ann_vol(curve), 1, signed=False),
                     pct(-s["mdd"], signed=False) if s["mdd"] else "0.00%",
                     f"{s['opened']} opened (+{s['sync']} carried), {s['closed']} closed",
                     f"{in_mkt}/{n_days} days in market, avg gross {pct(avg_gross, 0, signed=False)}",
                     usd(exit_cost), usd(s["eq"] - ctx.capital, True),
                     f"{pct(s['ret'] - spy_r)} ({usd((s['ret'] - spy_r) * ctx.capital, True)})"])
        n_live = n_days
        e = compare.expectations(p, n_live, s["ret"], s["opened"])
        if e["available"]:
            exp_rows.append([
                s["pid"], pair_label(p), f"{n_live}", pct(s["ret"]),
                _pct_cell(e["pct_full"], e["n_windows_full"]), _pct_cell(e["pct_post"], e["n_windows_post"]),
                f"{s['opened']} vs {num(e['expected_live_trades_full'], '.1f')} "
                f"({num(e['trades_per_month_full'], '.2f')}/mo; post-COVID {num(e['trades_per_month_post'], '.2f')}/mo)",
                f"{pct(e['month_mean_full'])} ± {pct(e['month_sd_full'], signed=False)}",
                f"{pct(e['month_mean_post'])} ± {pct(e['month_sd_post'], signed=False)}"])
        else:
            exp_rows.append([s["pid"], pair_label(p), f"{n_live}", pct(s["ret"]), "n/a", "n/a", "n/a", "n/a", "n/a"])
    spy_all = spy_return(ctx, ctx.base_date, cl)
    comb_ret = float(comb.iloc[-1]) / total_cap - 1
    rows.append(["**Combined**", f"{len(ctx.picks)} sub-portfolios", pct(comb_ret), pct(ann_vol(comb), 1, signed=False),
                 pct(-max_drawdown(comb), signed=False) if max_drawdown(comb) else "0.00%",
                 f"{sum(s['opened'] for s in stats.values())} opened, {sum(s['closed'] for s in stats.values())} closed",
                 "", "", usd(float(comb.iloc[-1]) - total_cap, True),
                 f"{pct(comb_ret - spy_all)} ({usd((comb_ret - spy_all) * total_cap, True)})"])
    rows.append([f"SPY (to {cl.date()})", "total return, adjusted close", pct(spy_all), "", "", "", "", "",
                 usd(spy_all * total_cap, True) + " on the same capital", ""])
    lines += ["## All picks side by side", "",
              table(["Pick", "Pair · rule", "Live return", "Live annualised vol", "Max drawdown", "Trades",
                     "Exposure", "Est. exit cost of open positions", "P&L", "P&L vs SPY"], rows), ""]

    # ---- live vs backtest expectations
    lines += ["## Live versus backtest expectations", "",
              "Percentile = share of rolling windows of the same length (in sessions) in the backtest's out-of-sample "
              "daily returns (`net_ret`) whose compounded return is at or below the live return. Trades: positions "
              "opened live (excluding carried-in) versus the backtest's closed round trips per month over its "
              "out-of-sample span. Monthly return = calendar-month compounded `net_ret`.", "",
              table(["Pick", "Pair · rule", "Live sessions", "Live return", "Percentile (full OOS)",
                     "Percentile (post-COVID)", "Trades live vs expected", "Backtest monthly mean ± sd (full)",
                     "Backtest monthly mean ± sd (post-COVID)"], exp_rows), ""]

    # ---- parity
    lines += ["## Parity check: does the live system behave as backtested?", "",
              "The backtest engine (`backtest.walkforward.run_pair_rule`) was re-run on the same provider data through "
              "each pick's last processed session. For every live session the sign of the backtest's held leg-A "
              "position (`sign(daily.wA)`) is compared with the sign of the simulator's leg-A position after that "
              "session's open.", ""]
    if parity is None:
        lines += [f"**Parity check unavailable:** {parity_note or 'no data'}", ""]
    else:
        prow = []
        total_n = total_m = 0
        for p in ctx.picks:
            q = parity[p["pick_id"]]
            if q["error"]:
                prow.append([q["pick_id"], pair_label(p), "—", "—", "—", "—", q["error"]])
                continue
            total_n += q["n"]
            total_m += q["matches"]
            prow.append([q["pick_id"], pair_label(p), str(q["n"]), str(q["matches"]), str(len(q["mismatches"])),
                         f"backtest {q['bt_margin_calls']} / sim {q['sim_margin_calls']}",
                         "identical" if q["n"] and not q["mismatches"] else ("see below" if q["mismatches"] else "")])
        lines += [table(["Pick", "Pair · rule", "Sessions compared", "Matches", "Mismatches", "Margin calls",
                         "Result"], prow), "",
                  f"**Total: {total_m} of {total_n} sessions match.**", ""]
        any_mm = False
        for p in ctx.picks:
            q = parity[p["pick_id"]]
            if q["mismatches"]:
                any_mm = True
                lines += [f"Mismatches for {q['pick_id']} ({pair_label(p)}):"] + \
                         [f"- {d}: backtest sign {b:+d}, simulator sign {s:+d}" for d, b, s in q["mismatches"]] + [""]
        if not any_mm:
            lines += ["No mismatches.", ""]
        lines += ["Note: margin-call timing can legitimately differ. The backtest has been compounding since 2016 "
                  "while the simulator starts with fresh $100,000 per pick, so the same adverse move can trip the "
                  "25% maintenance test in one account and not the other; a mismatch that coincides with a margin "
                  "call is therefore not a system fault. Sessions where the backtest equity was wiped out are "
                  "skipped. With live (Yahoo) data there is a second, small source of differences: Yahoo revises "
                  "the whole adjusted-close history whenever a dividend goes ex, so this re-run on today's data can "
                  "see marginally different z-scores than the simulator saw on the day.", ""]

    # ---- open positions
    orow = []
    for p in ctx.picks:
        s = stats[p["pick_id"]]
        r = s["row"]
        if r is None:
            continue
        orow.append([s["pid"], pair_label(p), r["state"], position_cell(float(r["shares_a"]), float(r["close_a"]),
                                                                       p["leg_a"]),
                     position_cell(float(r["shares_b"]), float(r["close_b"]), p["leg_b"]), queued_cell(r, p)])
    lines += ["## Positions at the last close", "",
              table(["Pick", "Pair · rule", "State", "Leg A", "Leg B", "Order queued"], orow) if orow else "none", ""]

    # ---- fills
    fills = ctx.trades.sort_values("session", kind="stable").tail(40)
    lines += ["## Fills" + (" (last 40)" if len(ctx.trades) > 40 else ""), ""]
    lines += [table(["Session", "Pick", "Ticker", "Side", "Action", "Shares", "Fill price", "Commission $", "Reason"],
                    [[t.session, t.pick_id, t.ticker, t.side, t.action, f"{t.shares:,.4f}", f"{t.price:,.4f}",
                      f"{t.commission:,.2f}", t.reason] for t in fills.itertuples()]) if len(fills) else "none", ""]

    # ---- data issues
    errs = ctx.errors_log
    lines += ["## Data issues", "", f"{len(errs)} line(s) in errors.log." if errs else "none"]
    lines += [f"- `{e}`" for e in errs[-20:]] + [""]
    lines += ["## Method notes", "",
              "- Fills at the next session's RAW open with slippage on the raw price; commission $0.005/share, "
              "$1 minimum per fill per leg; borrow = short notional x rate / 252 per session; marks at the RAW "
              "close; splits and cash dividends applied to the position held at the prior close.",
              "- Share counts are fractional, exactly as in the backtest.",
              "- The simulator starts each pick with fresh capital on the start date; the position the backtest "
              "would already hold is carried in at the start-date open (reason starting `sync:`).",
              ""]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- assembly helpers
def build_ctx(paths: store.Paths, cfg: dict, state: dict, spy: pd.Series | None, run_utc: str,
              issues: list[Issue]) -> Ctx:
    return Ctx(cfg=cfg, state=state, equity=store.read_equity(paths), trades=store.read_trades(paths), spy=spy,
               run_utc=run_utc, issues=list(issues), errors_log=store.read_errors(paths))


def write_final_report(paths: store.Paths, ctx: Ctx, frames: dict | None = None, provider=None) -> list[Issue]:
    """Write ``final_sim_report.md``.  ``frames`` are provider frames already in hand; anything missing (every leg and
    SPY are needed for the parity check and the SPY comparison) is fetched with ``provider`` if one is given.  The
    report is always written; a data problem is returned as issues and shown in the parity section."""
    issues: list[Issue] = []
    frames = dict(frames or {})
    done = [pd.Timestamp(ps["last_processed"]) for ps in ctx.state["picks"].values()]
    live = [d for d in done if d >= ctx.start]
    note = ""
    if not live:
        note = "no live session has been processed yet"
    else:
        need = [t for t in dict.fromkeys(engine.pick_tickers(ctx.picks) + [engine.SPY]) if t not in frames]
        if need and provider is not None:
            fr, errs = fetch_all(make_provider(provider, max(live)), need)
            frames.update(fr)
            for t, e in errs.items():
                issues.append(Issue(f"final report: {e}"))
        if ctx.spy is None and engine.SPY in frames:
            ctx.spy = frames[engine.SPY]["adjclose"].astype(float)
    parity = None
    if live:
        try:
            parity = compare.parity_check(ctx.cfg, ctx.state, ctx.equity, frames)
        except Exception as e:  # noqa: BLE001 - the report must still be written
            note = f"{type(e).__name__}: {e}"
            issues.append(Issue(f"final report: parity check failed ({note})"))
        else:
            for pid, q in parity.items():
                if q["error"] and q["last"] is not None:
                    issues.append(Issue(f"final report: parity check skipped ({q['error']})", pid))
    ctx.issues = list(ctx.issues) + issues
    store.atomic_write_text(paths.final, final_report(ctx, parity, note))
    return issues
