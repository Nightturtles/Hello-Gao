"""Per-pick paper-trading engine: warm start and the daily loop.

Nothing here re-implements trading logic.  Signals come from ``backtest.strategies`` (``fit``, ``new_window_state``,
``step``, ``force_flat``), the warm start is ``backtest.walkforward.run_pair_rule`` itself, and the account-risk test
is ``backtest.walkforward.account_check``.  What this module adds is the live bookkeeping the backtest does not need:
RAW-price fills/marks, split and dividend handling, and state that survives between processes.

Timeline for one pick and one session d (``process_session``)
  0. splits / dividends dated d are applied to the position held at the PRIOR close;
  1. the order queued at the previous close fills at d's raw open (slippage on the raw price, commission per fill);
  2. positions are marked to d's raw close and the borrow fee accrues on short notional;
  3. on a walk-forward grid date the rule is refitted on the 504 sessions of adjusted closes strictly before d;
  4. ``strategies.step`` gets adjusted closes up to and including d -> target weights for the NEXT open;
  5. ``account_check`` on raw-price equity and gross exposure (margin call -> force flat, ruin -> never trade again);
  6. the target is queued only if it differs from the weights the current position was sized from.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backtest import config, strategies, walkforward
from backtest import data as bdata
from backtest.trading_calendar import sessions, walk_forward_grid

from . import cal
from .data import DataError

TOL = 1e-12
SPY = "SPY"
LOOKBACK = 61               # z_window + 1 adjusted closes are all any rule needs from the recent past


# --------------------------------------------------------------------------- small helpers
def pick_tickers(picks: list[dict]) -> list[str]:
    return [t for p in picks for t in (p["leg_a"], p["leg_b"])]


def commission(shares: float) -> float:
    return max(config.COMMISSION_MIN, config.COMMISSION_PER_SHARE * abs(shares))


def leg_slip(pick: dict, leg: str) -> float:
    return float(pick["slippage_bps"][leg]) / 1e4


def leg_borrow(pick: dict, leg: str) -> float:
    return float(pick["borrow_rate"][leg])


def _sign(x: float) -> int:
    return 0 if (not math.isfinite(x) or abs(x) <= TOL) else (1 if x > 0 else -1)


def weights_differ(a, b) -> bool:
    return abs(a[0] - b[0]) > TOL or abs(a[1] - b[1]) > TOL


def position_label(shares, rule: str, strategy_state: dict | None) -> str:
    if shares[0] > 0 and shares[1] < 0:
        return "long A / short B"
    if shares[0] < 0 and shares[1] > 0:
        return "short A / long B"
    if shares[0] == 0 and shares[1] == 0:
        if rule in ("coint_ols", "coint_kalman") and strategy_state and not strategy_state.get("armed", True):
            return "flat (disarmed)"
        return "flat"
    return "mixed"


def build_pair_data(pick: dict, fa: pd.DataFrame, fb: pd.DataFrame, sess: pd.DatetimeIndex) -> walkforward.PairData:
    """The backtest's ``PairData`` for one pick from two provider frames, on the NYSE session index ``sess``."""
    a, b = bdata.with_adjopen(fa).reindex(sess), bdata.with_adjopen(fb).reindex(sess)
    la, lb = pick["leg_a"], pick["leg_b"]
    return walkforward.PairData(
        pair_id=pick["pair_id"], leg_a=la, leg_b=lb, dates=sess,
        ac_a=a["adjclose"].to_numpy(dtype=float), ac_b=b["adjclose"].to_numpy(dtype=float),
        ao_a=a["adjopen"].to_numpy(dtype=float), ao_b=b["adjopen"].to_numpy(dtype=float),
        ro_a=a["open"].to_numpy(dtype=float), ro_b=b["open"].to_numpy(dtype=float),
        slip_a=leg_slip(pick, la), slip_b=leg_slip(pick, lb),
        borrow_a=leg_borrow(pick, la), borrow_b=leg_borrow(pick, lb))


# --------------------------------------------------------------------------- per-run price arrays
@dataclass
class PickData:
    """The numpy views one run needs for one pick, all aligned on ``sess`` (NYSE sessions from DOWNLOAD_START)."""
    pick: dict
    sess: pd.DatetimeIndex
    ac: tuple      # adjusted closes (A, B)
    op: tuple      # raw opens
    cl: tuple      # raw closes
    dv: tuple      # cash dividends per share (0 = none)
    sp: tuple      # split ratios (0 = none)
    slip: tuple    # fraction per side
    brate: tuple   # borrow rate per session (annual / 252)

    @property
    def tickers(self) -> tuple:
        return (self.pick["leg_a"], self.pick["leg_b"])


def build_pick_data(pick: dict, fa: pd.DataFrame, fb: pd.DataFrame, sess: pd.DatetimeIndex) -> PickData:
    def col(df, name, fill=None):
        s = df[name].reindex(sess)
        return (s.fillna(fill) if fill is not None else s).to_numpy(dtype=float)

    fr = (fa, fb)
    legs = (pick["leg_a"], pick["leg_b"])
    return PickData(
        pick=pick, sess=sess,
        ac=tuple(col(f, "adjclose") for f in fr), op=tuple(col(f, "open") for f in fr),
        cl=tuple(col(f, "close") for f in fr), dv=tuple(col(f, "dividends", 0.0) for f in fr),
        sp=tuple(col(f, "splits", 0.0) for f in fr),
        slip=tuple(leg_slip(pick, t) for t in legs),
        brate=tuple(leg_borrow(pick, t) / config.BORROW_DAYS for t in legs))


def grid_window_at(sess: pd.DatetimeIndex, i: int):
    """The walk-forward window that STARTS at session index i, else None.  Uses the backtest's own grid on the
    sessions up to and including d, as the spec requires."""
    if sess[i] < pd.Timestamp(config.GRID_START):
        return None
    w = walk_forward_grid(sess[:i + 1])[-1]
    return w if w.test_start == i else None


def check_data(pdta: PickData, i: int) -> str | None:
    """None if session index i can be processed, else a human-readable reason (a missing/invalid bar or a gap in the
    history the rules read).  A bar with a NaN, zero or negative price counts as missing."""
    d = pdta.sess[i]
    w = grid_window_at(pdta.sess, i)
    for leg, t in enumerate(pdta.tickers):
        for name, arr in (("open", pdta.op[leg]), ("close", pdta.cl[leg]), ("adjusted close", pdta.ac[leg])):
            v = arr[i]
            if not (np.isfinite(v) and v > 0):
                return f"{t}: no usable {name} bar for {d.date()}"
        if not np.isfinite(pdta.ac[leg][max(0, i - LOOKBACK + 1):i + 1]).all():
            return f"{t}: gap in the {LOOKBACK} adjusted closes ending {d.date()}"
        if w is not None and not np.isfinite(pdta.ac[leg][w.fit_start:w.fit_end]).all():
            return f"{t}: gap in the {config.TRAIN_LEN}-session training sample before {d.date()}"
    return None


# --------------------------------------------------------------------------- warm start
def _sync_reason(res: walkforward.RunResult, sp: pd.Timestamp, tgt: dict) -> str:
    last = res.daily.iloc[-1]
    wa, wb = float(last["wA"]), float(last["wB"])
    held_sign = _sign(wa) or _sign(wb)
    tgt_sign = _sign(tgt["A"]) or _sign(tgt["B"])
    if held_sign != 0 and held_sign == tgt_sign:
        ot = res.trades[res.trades["open_at_end"].astype(bool)]
        if len(ot):
            r = ot.iloc[-1]
            return (f"sync: position carried from backtest replay (entered {pd.Timestamp(r['entry_date']).date()}: "
                    f"{r['entry_reason']})")
        return "sync: position carried from backtest replay (entry date not available)"
    z = res.final_state.get("z")
    zt = f", z={z:.2f}" if z is not None else ""
    if held_sign != 0:
        return (f"sync: position carried from backtest replay (backtest held the opposite side at the close of "
                f"{sp.date()}; flips at the open{zt})")
    return f"sync: position carried from backtest replay (new entry signal at the close of {sp.date()}{zt})"


def warm_start(pick: dict, fa: pd.DataFrame, fb: pd.DataFrame, start, capital: float) -> tuple[dict, pd.DataFrame]:
    """The strategy state after the close of session (start - 1), computed by the REAL backtest engine on data sliced
    to dates <= start - 1 (nothing later can influence it).  Returns (pick state, replay daily series).

    The backtest's ``final_state`` / ``final_fit`` / ``final_target`` are exactly its state after that close.  A
    non-flat ``final_target`` is queued for the start-date open with reason ``sync: position carried ...``; the
    simulator then starts from a fresh ``capital`` in cash, so share counts are re-sized from that equity.
    """
    start = pd.Timestamp(start)
    sp = cal.prev_session(start)
    sess = sessions(config.DOWNLOAD_START, sp)
    fa, fb = fa.loc[:sp], fb.loc[:sp]                                    # no look-ahead
    for t, f in ((pick["leg_a"], fa), (pick["leg_b"], fb)):
        row = f.reindex([sp]).iloc[0] if sp in f.index else None
        if row is None or not (np.isfinite(row["open"]) and np.isfinite(row["close"]) and np.isfinite(row["adjclose"])):
            raise DataError(f"{t}: no bar for {sp.date()}, needed by the warm start")
    pdat = build_pair_data(pick, fa, fb, sess)
    res = walkforward.run_pair_rule(pick["rule"], pdat, walk_forward_grid(sess), pick["params"])
    if res.final_state is None or res.final_fit is None or len(res.daily) == 0 or res.meta["stopped"] \
            or res.daily.index[-1] != sp:
        why = res.meta["stopped"] or "no eligible walk-forward window"
        raise DataError(f"{pick['pair_id']}: warm-start replay did not reach {sp.date()} ({why})")
    tgt = {"A": float(res.final_target["A"]), "B": float(res.final_target["B"])}
    pending = None
    last = res.daily.iloc[-1]
    if weights_differ((tgt["A"], tgt["B"]), (0.0, 0.0)):
        pending = {"target": tgt, "reason": _sync_reason(res, sp, tgt), "signal_date": str(sp.date())}
    ps = {
        "pick_id": pick["pick_id"], "rule": pick["rule"], "last_processed": str(sp.date()),
        "cash": float(capital), "equity": float(capital), "hwm": float(capital), "start_equity": float(capital),
        "shares": [0.0, 0.0], "cur_w": [0.0, 0.0], "pending": pending,
        "strategy_state": copy.deepcopy(res.final_state), "fit": copy.deepcopy(res.final_fit),
        "ruined_on": None, "margin_calls": 0,
        "n_entries": 0, "n_sync": 0, "n_closed": 0, "open_trade": None, "n_days": 0, "n_days_in_market": 0,
        "costs_total": 0.0,
        "warm": {"replay_last": str(sp.date()), "n_windows": int(res.meta["n_windows"]),
                 "backtest_held_wA": None if not math.isfinite(float(last["wA"])) else float(last["wA"]),
                 "backtest_held_wB": None if not math.isfinite(float(last["wB"])) else float(last["wB"]),
                 "final_target": tgt, "backtest_margin_calls": int(res.meta["margin_calls"]),
                 "backtest_ruined_on": res.meta["ruined_on"]},
    }
    return ps, res.daily


# --------------------------------------------------------------------------- daily loop
def process_session(ps: dict, pdta: PickData, i: int, run_utc: str) -> tuple[dict, dict, list[dict]]:
    """Advance one pick by one session.  Pure with respect to ``ps`` (a deep copy is returned), so a failure half-way
    leaves the saved state untouched.  Returns (new state, equity-log row, trade-log rows)."""
    pick = pdta.pick
    rule, params = pick["rule"], pick["params"]
    d = pdta.sess[i]
    dstr = str(d.date())
    ps = copy.deepcopy(ps)
    sh, cur_w = ps["shares"], ps["cur_w"]
    cash, eq_prev = ps["cash"], ps["equity"]
    slip, brate = pdta.slip, pdta.brate
    costs = 0.0
    div_cash = 0.0
    trades: list[dict] = []

    # ---- 0. corporate actions on the position held at the prior close (split first, dividend on post-split shares)
    for leg in (0, 1):
        r = pdta.sp[leg][i]
        if sh[leg] != 0.0 and np.isfinite(r) and r > 0.0 and r != 1.0:
            sh[leg] *= r
    for leg in (0, 1):
        dv = pdta.dv[leg][i]
        if sh[leg] != 0.0 and np.isfinite(dv) and dv > 0.0:
            cash += sh[leg] * dv                       # long receives, short pays
            div_cash += sh[leg] * dv

    # ---- 1. fills at the raw open
    pend = ps["pending"]
    if pend is not None:
        tgt, reason, sig = pend["target"], pend["reason"], pend["signal_date"]
        new_w = (tgt["A"], tgt["B"])
        if weights_differ(new_w, cur_w):
            def log(leg, side, action, qty, px, fill, comm):
                trades.append({"run_utc": run_utc, "session": dstr, "pick_id": pick["pick_id"],
                               "ticker": pdta.tickers[leg], "side": side, "action": action, "shares": abs(qty),
                               "price": fill, "raw_open": px, "slippage": abs(qty) * px * slip[leg],
                               "commission": comm, "reason": reason, "signal_date": sig})

            closed_any = False
            for leg in (0, 1):
                if abs(new_w[leg] - cur_w[leg]) > TOL and sh[leg] != 0.0:
                    px = pdta.op[leg][i]
                    qty = sh[leg]
                    fill = px * (1.0 - slip[leg]) if qty > 0 else px * (1.0 + slip[leg])
                    cash += qty * fill                  # selling a long adds cash; covering a short removes it
                    c = commission(qty)
                    cash -= c
                    costs += c + abs(qty) * px * slip[leg]
                    log(leg, "sell" if qty > 0 else "buy", "close", qty, px, fill, c)
                    sh[leg] = 0.0
                    closed_any = True
            if closed_any and ps["open_trade"] is not None:
                ps["n_closed"] += 1
                ps["open_trade"] = None
            opened = False
            for leg in (0, 1):
                if (abs(new_w[leg] - cur_w[leg]) > TOL and abs(new_w[leg]) > TOL and eq_prev > 0.0
                        and ps["ruined_on"] is None):
                    px = pdta.op[leg][i]
                    qty = new_w[leg] * eq_prev / px
                    fill = px * (1.0 + slip[leg]) if qty > 0 else px * (1.0 - slip[leg])
                    cash -= qty * fill
                    c = commission(qty)
                    cash -= c
                    costs += c + abs(qty) * px * slip[leg]
                    log(leg, "buy" if qty > 0 else "sell", "open", qty, px, fill, c)
                    sh[leg] = qty
                    opened = True
            if opened:
                is_sync = reason.startswith("sync:")
                ps["n_sync" if is_sync else "n_entries"] += 1
                ps["open_trade"] = {"entry_date": dstr, "reason": reason, "sync": is_sync}
            cur_w = [new_w[0], new_w[1]]
        ps["pending"] = None

    # ---- 2. mark to the raw close; borrow on short notional
    borrow = 0.0
    for leg in (0, 1):
        if sh[leg] < 0:
            borrow += -sh[leg] * pdta.cl[leg][i] * brate[leg]
    cash -= borrow
    costs += borrow
    eq = cash + sh[0] * pdta.cl[0][i] + sh[1] * pdta.cl[1][i]

    # ---- 3. refit on a walk-forward grid date (training = the 504 adjusted closes strictly before d)
    acA, acB = pdta.ac
    refit_note = ""
    w = grid_window_at(pdta.sess, i)
    if w is not None:
        fit_ = strategies.fit(rule, acA[w.fit_start:w.fit_end], acB[w.fit_start:w.fit_end], params)
        ps["strategy_state"] = strategies.new_window_state(rule, ps["strategy_state"], fit_, params)
        ps["fit"] = fit_.to_dict()
        refit_note = (f"window {w.k}: beta={fit_.beta:.4f} " if fit_.beta is not None else f"window {w.k}: ") + \
            ("valid" if fit_.valid else f"invalid ({fit_.reason})")
        if fit_.k is not None:
            refit_note += f" k={fit_.k}"
    fit_ = strategies.FitResult.from_dict(ps["fit"])

    # ---- 4. signal at the close of d (adjusted closes up to and including d)
    state, tgt, reason = strategies.step(rule, ps["strategy_state"], acA[:i + 1], acB[:i + 1], fit_, params)

    # ---- 5. account risk, on raw-price equity and gross exposure
    gross = abs(sh[0]) * pdta.cl[0][i] + abs(sh[1]) * pdta.cl[1][i]
    check = "ruin" if ps["ruined_on"] is not None else walkforward.account_check(eq, gross)
    if check == "ruin":
        if ps["ruined_on"] is None:
            ps["ruined_on"] = dstr
            reason = f"ruin: equity {eq:,.0f} <= 0; liquidate and stop trading"
        else:
            reason = f"ruined on {ps['ruined_on']}: no further trading"
        state, tgt = strategies.force_flat(rule, state), dict(strategies.FLAT)
    elif check == "margin_call":
        ps["margin_calls"] += 1
        state, tgt = strategies.force_flat(rule, state), dict(strategies.FLAT)
        reason = (f"margin call: equity {eq / gross:.1%} of gross exposure < {config.MAINT_MARGIN:.0%}; "
                  f"liquidate")
    ps["strategy_state"] = state

    # ---- 6. queue for the next open only if the target differs from the weights the position was sized from
    new_w = (tgt["A"], tgt["B"])
    ps["pending"] = ({"target": {"A": tgt["A"], "B": tgt["B"]}, "reason": reason, "signal_date": dstr}
                     if weights_differ(new_w, cur_w) else None)

    # ---- bookkeeping
    ps["cur_w"] = cur_w
    ps["cash"], ps["equity"] = cash, eq
    ps["hwm"] = max(ps["hwm"], eq)
    dd = (ps["hwm"] - eq) / ps["hwm"] if ps["hwm"] > 0 else 0.0
    ps["last_processed"] = dstr
    ps["n_days"] += 1
    if sh[0] != 0.0 or sh[1] != 0.0:
        ps["n_days_in_market"] += 1
    ps["costs_total"] += costs
    pnd = ps["pending"]
    row = {"date": dstr, "pick_id": pick["pick_id"], "equity": eq, "cash": cash, "shares_a": sh[0], "shares_b": sh[1],
           "close_a": pdta.cl[0][i], "close_b": pdta.cl[1][i], "z": state.get("z"), "beta": state.get("beta_used"),
           "drawdown": dd, "hwm": ps["hwm"], "state": position_label(sh, rule, state), "costs": costs,
           "dividends": div_cash,
           "queued_wa": pnd["target"]["A"] if pnd else None, "queued_wb": pnd["target"]["B"] if pnd else None,
           "queued_reason": pnd["reason"] if pnd else "", "refit": refit_note}
    return ps, row, trades
