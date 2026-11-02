"""Live-versus-backtest comparisons for the final report: the PARITY CHECK and the backtest expectations."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from backtest import config, walkforward
from backtest.trading_calendar import sessions, walk_forward_grid

from . import engine

POST_START = pd.Timestamp(config.REGIMES["post"][0])
MONTH = 21                      # sessions per month used for "per month" rates


# --------------------------------------------------------------------------- parity
def parity_check(cfg: dict, state: dict, equity: pd.DataFrame, frames: dict) -> dict[str, dict]:
    """Re-run the backtest engine (``walkforward.run_pair_rule``) on the same provider data through each pick's last
    processed session and compare, for every live session, the sign of the backtest's held leg-A position
    (``sign(daily.wA)``) with the sign of the simulator's leg-A position after that session's open.

    Margin-call timing can legitimately differ: the backtest has been compounding since 2016 while the simulator
    starts with fresh capital, so the same adverse move can trip the maintenance test in one and not the other."""
    start = pd.Timestamp(cfg["start"])
    out: dict[str, dict] = {}
    for pick in cfg["picks"]:
        pid = pick["pick_id"]
        ps = state["picks"].get(pid)
        rec = {"pick_id": pid, "n": 0, "matches": 0, "mismatches": [], "skipped": 0, "error": None,
               "bt_margin_calls": None, "sim_margin_calls": ps["margin_calls"] if ps else None, "last": None}
        out[pid] = rec
        if ps is None or pd.Timestamp(ps["last_processed"]) < start:
            rec["error"] = "no live session processed yet"
            continue
        last = pd.Timestamp(ps["last_processed"])
        rec["last"] = str(last.date())
        try:
            fa, fb = frames[pick["leg_a"]].loc[:last], frames[pick["leg_b"]].loc[:last]
        except KeyError as e:
            rec["error"] = f"no data for {e.args[0]}"
            continue
        sess = sessions(config.DOWNLOAD_START, last)
        res = walkforward.run_pair_rule(pick["rule"], engine.build_pair_data(pick, fa, fb, sess),
                                        walk_forward_grid(sess), pick["params"])
        rec["bt_margin_calls"] = int(res.meta["margin_calls"])
        bt = np.sign(res.daily["wA"])                      # NaN stays NaN (wiped-out account)
        live = equity[equity["pick_id"] == pid].set_index("date")
        for d, row in live.iterrows():
            sim_sign = int(np.sign(row["shares_a"]))
            b = bt.get(d, np.nan)
            if not np.isfinite(b):
                rec["skipped"] += 1
                continue
            rec["n"] += 1
            if int(b) == sim_sign:
                rec["matches"] += 1
            else:
                rec["mismatches"].append((str(d.date()), int(b), sim_sign))
    return out


# --------------------------------------------------------------------------- backtest expectations
def _read_trial(pick: dict) -> pd.Series | None:
    p = config.ROOT / pick.get("backtest_daily_returns_path", "")
    if not p.is_file():
        return None
    return pd.read_csv(p, index_col=0, parse_dates=True)["net_ret"].astype(float)


def _read_closed_trades(pick: dict) -> pd.DataFrame | None:
    p = config.ROOT / pick.get("backtest_trades_path", "")
    if not p.is_file():
        return None
    t = pd.read_csv(p, parse_dates=["entry_date", "exit_date"])
    return t[~t["open_at_end"].astype(bool)]


def rolling_window_returns(r: np.ndarray, n: int) -> np.ndarray:
    """Compounded return of every window of n consecutive daily returns."""
    if n < 1 or len(r) < n:
        return np.array([])
    w = np.lib.stride_tricks.sliding_window_view(1.0 + r, n)
    return w.prod(axis=1) - 1.0


def percentile_of(x: float, dist: np.ndarray) -> float:
    """Percent of the distribution at or below x (nan if empty)."""
    return float((dist <= x).mean() * 100.0) if len(dist) else float("nan")


def monthly_stats(r: pd.Series) -> tuple[float, float, int]:
    if r is None or len(r) == 0:
        return float("nan"), float("nan"), 0
    m = (1.0 + r).groupby(r.index.to_period("M")).prod() - 1.0
    return float(m.mean()), float(m.std(ddof=1)) if len(m) > 1 else float("nan"), int(len(m))


def expectations(pick: dict, n_live_days: int, live_return: float, live_entries: int) -> dict:
    """Where the live period sits in the backtest's out-of-sample distribution, for one pick."""
    r = _read_trial(pick)
    tr = _read_closed_trades(pick)
    out = {"available": r is not None, "n_live_days": n_live_days, "live_return": live_return,
           "live_entries": live_entries}
    if r is None:
        return out
    post = r[r.index >= POST_START]
    for tag, series in (("full", r), ("post", post)):
        dist = rolling_window_returns(series.to_numpy(), n_live_days)
        out[f"pct_{tag}"] = percentile_of(live_return, dist)
        out[f"n_windows_{tag}"] = int(len(dist))
        mean, sd, nm = monthly_stats(series)
        out[f"month_mean_{tag}"], out[f"month_sd_{tag}"], out[f"n_months_{tag}"] = mean, sd, nm
        if tr is not None and len(series):
            trades = tr if tag == "full" else tr[tr["entry_date"] >= POST_START]
            months = len(series) / MONTH
            out[f"trades_per_month_{tag}"] = len(trades) / months if months > 0 else float("nan")
        else:
            out[f"trades_per_month_{tag}"] = float("nan")
    out["expected_live_trades_full"] = out["trades_per_month_full"] * (n_live_days / MONTH) \
        if math.isfinite(out.get("trades_per_month_full", float("nan"))) else float("nan")
    return out
