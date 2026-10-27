"""Event-driven walk-forward engine (spec section 6).

The engine owns no trading logic: every day it calls ``strategies.step()`` (the same function the live
paper-trading simulator will call) and then fills the returned target at the NEXT open.

Timeline for session i
  1. fill the target decided at the close of session i-1, at the adjusted open of session i
     (buys at adjopen*(1+slip), sells at adjopen*(1-slip); commission $0.005/raw share, $1 minimum per fill);
  2. mark to the close of session i; charge borrow on short notional at the close (rate/252);
  3. call step() with adjusted closes up to and including session i -> target for the next open;
  4. account check at the close (``account_check``): if equity < MAINT_MARGIN x gross exposure the position is
     force-liquidated at the next open (margin call); if equity <= 0 the account is ruined: liquidate, never trade
     again, and book the day's return as -100%.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, strategies
from .trading_calendar import Window


@dataclass
class PairData:
    pair_id: str
    leg_a: str
    leg_b: str
    dates: pd.DatetimeIndex
    ac_a: np.ndarray        # adjusted close
    ac_b: np.ndarray
    ao_a: np.ndarray        # adjusted open
    ao_b: np.ndarray
    ro_a: np.ndarray        # raw open (commission share count)
    ro_b: np.ndarray
    slip_a: float = 0.001   # fraction per side
    slip_b: float = 0.001
    borrow_a: float = 0.005  # annual
    borrow_b: float = 0.005

    def complete_mask(self) -> np.ndarray:
        m = np.ones(len(self.dates), dtype=bool)
        for arr in (self.ac_a, self.ac_b, self.ao_a, self.ao_b, self.ro_a, self.ro_b):
            m &= np.isfinite(arr)
        return m


def build_pair_data(panel: dict, screen: pd.DataFrame, pair_id: str, leg_a: str, leg_b: str) -> PairData:
    s = screen.set_index("ticker")
    return PairData(
        pair_id=pair_id, leg_a=leg_a, leg_b=leg_b, dates=panel["adjclose"].index,
        ac_a=panel["adjclose"][leg_a].to_numpy(dtype=float), ac_b=panel["adjclose"][leg_b].to_numpy(dtype=float),
        ao_a=panel["adjopen"][leg_a].to_numpy(dtype=float), ao_b=panel["adjopen"][leg_b].to_numpy(dtype=float),
        ro_a=panel["open"][leg_a].to_numpy(dtype=float), ro_b=panel["open"][leg_b].to_numpy(dtype=float),
        slip_a=float(s.loc[leg_a, "slippage_bps"]) / 1e4, slip_b=float(s.loc[leg_b, "slippage_bps"]) / 1e4,
        borrow_a=float(s.loc[leg_a, "borrow_rate"]), borrow_b=float(s.loc[leg_b, "borrow_rate"]),
    )


@dataclass
class RunResult:
    pair_id: str
    rule: str
    daily: pd.DataFrame
    trades: pd.DataFrame
    windows: pd.DataFrame
    meta: dict = field(default_factory=dict)
    final_state: dict | None = None
    final_fit: dict | None = None
    final_target: dict | None = None


def account_check(equity: float, gross_exposure: float, maint_margin: float = config.MAINT_MARGIN) -> str | None:
    """Broker-style check at the close, shared with the live simulator: "ruin" if equity <= 0, "margin_call" if
    equity is below the maintenance requirement on the gross position, else None."""
    if equity <= 0.0:
        return "ruin"
    if gross_exposure > 0.0 and equity < maint_margin * gross_exposure:
        return "margin_call"
    return None


def eligible_windows(mask: np.ndarray, windows: list[Window]) -> list[bool]:
    """Window tradable iff both legs have complete data over the training sample and the test window."""
    return [bool(mask[w.fit_start:w.test_end].all()) for w in windows]


def run_pair_rule(rule: str, pdat: PairData, windows: list[Window], params: dict | None = None,
                  strat=strategies, capital: float = config.START_CAPITAL,
                  comm_per_share: float = config.COMMISSION_PER_SHARE, comm_min: float = config.COMMISSION_MIN,
                  borrow_days: int = config.BORROW_DAYS, maint_margin: float = config.MAINT_MARGIN) -> RunResult:
    params = params or config.PARAMS
    force_flat = getattr(strat, "force_flat", strategies.force_flat)
    elig = eligible_windows(pdat.complete_mask(), windows)
    dates = pdat.dates
    acA, acB = pdat.ac_a, pdat.ac_b
    aoA, aoB, roA, roB = pdat.ao_a.tolist(), pdat.ao_b.tolist(), pdat.ro_a.tolist(), pdat.ro_b.tolist()
    cA, cB = acA.tolist(), acB.tolist()
    slip = (pdat.slip_a, pdat.slip_b)
    brate = (pdat.borrow_a / borrow_days, pdat.borrow_b / borrow_days)
    ao = (aoA, aoB)
    ro = (roA, roB)
    cl = (cA, cB)

    cash = float(capital)
    sh = [0.0, 0.0]
    eq_prev = float(capital)
    cur_w = (0.0, 0.0)              # weights the current holdings were sized from
    pending = None                  # (target dict, reason) decided at the previous close
    state = None
    fit_ = None
    rows = {k: [] for k in ("i", "equity", "net_ret", "gross_ret", "costs", "wA", "wB", "z", "beta", "spread",
                            "window")}
    trades: list[dict] = []
    wlog: list[dict] = []
    open_trade = None
    covered_days = 0
    stopped = ""
    started = False
    last_i = -1
    last_target, last_reason = dict(strategies.FLAT), ""
    ruined_on = None
    margin_calls = 0

    def commission(raw_shares: float) -> float:
        return max(comm_min, comm_per_share * abs(raw_shares))

    for w in windows:
        if not elig[w.k]:
            if started:
                stopped = f"window {w.k} ({dates[w.test_start].date()}) ineligible after run start; run stopped"
                break
            continue
        started = True
        fit_ = strat.fit(rule, acA[w.fit_start:w.fit_end], acB[w.fit_start:w.fit_end], params)
        state = strat.new_window_state(rule, state, fit_, params)
        wlog.append({"pair_id": pdat.pair_id, "rule": rule, "k": w.k, "fit_start": dates[w.fit_start],
                     "fit_end": dates[w.fit_end - 1], "test_start": dates[w.test_start],
                     "test_end": dates[w.test_end - 1], "valid": fit_.valid, "reason": fit_.reason,
                     "beta": fit_.beta, "alpha": fit_.alpha, "k_star": fit_.k, "slope": fit_.slope,
                     "tstat": fit_.tstat, "h": fit_.h, "n_train": fit_.n_train})
        for i in range(w.test_start, w.test_end):
            cost_today = 0.0
            # ---------- 1. fills at the open of session i
            if pending is not None:
                tgt, reason = pending
                new_w = (tgt["A"], tgt["B"])
                if abs(new_w[0] - cur_w[0]) > 1e-12 or abs(new_w[1] - cur_w[1]) > 1e-12:
                    # close every leg whose weight changed
                    closed_any = False
                    for leg in (0, 1):
                        if abs(new_w[leg] - cur_w[leg]) > 1e-12 and sh[leg] != 0.0:
                            px = ao[leg][i]
                            fill = px * (1.0 - slip[leg]) if sh[leg] > 0 else px * (1.0 + slip[leg])
                            cash -= (-sh[leg]) * fill                         # selling +sh adds cash
                            c = commission(abs(sh[leg]) * px / ro[leg][i])
                            cash -= c
                            cost_today += c + abs(sh[leg]) * px * slip[leg]
                            sh[leg] = 0.0
                            closed_any = True
                    if closed_any and open_trade is not None:
                        pnl = cash - open_trade["cash0"]
                        trades.append({
                            "entry_date": open_trade["entry_date"], "exit_date": dates[i], "side": open_trade["side"],
                            "entry_reason": open_trade["entry_reason"], "exit_reason": reason,
                            "net_pnl": pnl, "holding_days": i - open_trade["entry_i"], "beta": open_trade["beta"],
                            "entry_equity": open_trade["entry_equity"], "open_at_end": False})
                        open_trade = None
                    # open new legs
                    opened = False
                    cash_before_open = cash
                    for leg in (0, 1):
                        if abs(new_w[leg] - cur_w[leg]) > 1e-12 and abs(new_w[leg]) > 1e-12 and eq_prev > 0:
                            px = ao[leg][i]
                            shares = new_w[leg] * eq_prev / px
                            fill = px * (1.0 + slip[leg]) if shares > 0 else px * (1.0 - slip[leg])
                            cash -= shares * fill
                            c = commission(abs(shares) * px / ro[leg][i])
                            cash -= c
                            cost_today += c + abs(shares) * px * slip[leg]
                            sh[leg] = shares
                            opened = True
                    if opened:
                        wa, wb = new_w
                        open_trade = {"cash0": cash_before_open, "entry_date": dates[i], "entry_i": i,
                                      "side": "long A / short B" if wa > 0 else "short A / long B",
                                      "entry_reason": reason, "entry_equity": eq_prev,
                                      "beta": abs(wb / wa) if wa != 0 else float("nan")}
                    cur_w = new_w
            # ---------- 2. mark to close, borrow on short notional
            borrow = 0.0
            for leg in (0, 1):
                if sh[leg] < 0:
                    borrow += -sh[leg] * cl[leg][i] * brate[leg]
            cash -= borrow
            cost_today += borrow
            eq = cash + sh[0] * cA[i] + sh[1] * cB[i]
            if eq_prev > 0:
                # a wiped-out account loses 100%, never more
                net = max(eq / eq_prev - 1.0, -1.0)
                gross = max((eq + cost_today) / eq_prev - 1.0, -1.0)
            else:
                net = gross = 0.0                   # ruined earlier: no capital left to earn a return on
            # ---------- 3. signal at the close of session i
            state, tgt, reason = strat.step(rule, state, acA[:i + 1], acB[:i + 1], fit_, params)
            # ---------- 4. account check (margin call / ruin)
            gross_exp = abs(sh[0]) * cA[i] + abs(sh[1]) * cB[i]
            check = "ruin" if ruined_on is not None else account_check(eq, gross_exp, maint_margin)
            if check == "ruin":
                if ruined_on is None:
                    ruined_on = str(dates[i].date())
                    reason = f"ruin: equity {eq:,.0f} <= 0; liquidate and stop trading"
                else:
                    reason = f"ruined on {ruined_on}: no further trading"
                state, tgt = force_flat(rule, state), dict(strategies.FLAT)
            elif check == "margin_call":
                margin_calls += 1
                state, tgt = force_flat(rule, state), dict(strategies.FLAT)
                reason = f"margin call: equity {eq / gross_exp:.1%} of gross exposure < {maint_margin:.0%}; liquidate"
            pending = (tgt, reason)
            rows["i"].append(i)
            rows["equity"].append(eq)
            rows["net_ret"].append(net)
            rows["gross_ret"].append(gross)
            rows["costs"].append(cost_today)
            rows["wA"].append(sh[0] * cA[i] / eq if eq > 0 else np.nan)
            rows["wB"].append(sh[1] * cB[i] / eq if eq > 0 else np.nan)
            rows["z"].append(state.get("z") if state.get("z") is not None else np.nan)
            rows["beta"].append(state.get("beta_used") if state.get("beta_used") is not None else np.nan)
            rows["spread"].append(state.get("spread") if state.get("spread") is not None else np.nan)
            rows["window"].append(w.k)
            eq_prev = eq
            last_i = i
            last_target, last_reason = tgt, reason
        covered_days += w.test_end - w.test_start

    if open_trade is not None and last_i >= 0:
        trades.append({
            "entry_date": open_trade["entry_date"], "exit_date": dates[last_i], "side": open_trade["side"],
            "entry_reason": open_trade["entry_reason"], "exit_reason": "open at end of sample (marked to last close)",
            "net_pnl": (cash + sh[0] * cA[last_i] + sh[1] * cB[last_i]) - open_trade["cash0"],
            "holding_days": last_i - open_trade["entry_i"], "beta": open_trade["beta"],
            "entry_equity": open_trade["entry_equity"], "open_at_end": True})

    daily = pd.DataFrame(rows)
    if len(daily):
        daily.insert(0, "date", dates[daily.pop("i").to_numpy()])
        daily = daily.set_index("date")
    else:
        daily = pd.DataFrame(columns=["equity", "net_ret", "gross_ret", "costs", "wA", "wB", "z", "beta", "spread",
                                      "window"])
    tr = pd.DataFrame(trades, columns=["entry_date", "exit_date", "side", "entry_reason", "exit_reason", "net_pnl",
                                       "holding_days", "beta", "entry_equity", "open_at_end"])
    meta = {"covered_days": covered_days, "first_oos_start": str(daily.index[0].date()) if len(daily) else None,
            "stopped": stopped, "n_windows": len(wlog), "margin_calls": margin_calls, "ruined_on": ruined_on}
    return RunResult(pdat.pair_id, rule, daily, tr, pd.DataFrame(wlog), meta,
                     final_state=state, final_fit=fit_.to_dict() if fit_ is not None else None,
                     final_target=last_target)
