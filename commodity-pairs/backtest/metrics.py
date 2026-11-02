"""Performance metrics (spec section 7).

Conventions (documented in IMPLEMENTATION_NOTES.md):
  * Sharpe = mean(daily net return) / std(ddof=1) * sqrt(252), rf = 0.
  * Sortino = mean / downside_dev * sqrt(252), downside_dev = sqrt(mean(min(r, 0)^2)).
  * CAGR = (prod(1+r))^(252/n) - 1.
  * Max drawdown is measured on the equity curve rebuilt from the regime's returns only (starting at 1.0).
  * Flat days count as zero-return days (idle cash earns 0%).
  * A round trip is a CLOSED trade and belongs to the regime of its entry date.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import config

ANN = 252


def sharpe(r: np.ndarray) -> float:
    if len(r) < 2:
        return float("nan")
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(ANN)) if sd > 0 else float("nan")


def sharpe_daily(r: np.ndarray) -> float:
    if len(r) < 2:
        return float("nan")
    sd = r.std(ddof=1)
    return float(r.mean() / sd) if sd > 0 else float("nan")


def sortino(r: np.ndarray) -> float:
    if len(r) < 2:
        return float("nan")
    dd = math.sqrt(float(np.mean(np.minimum(r, 0.0) ** 2)))
    return float(r.mean() / dd * math.sqrt(ANN)) if dd > 0 else float("nan")


def cagr(r: np.ndarray) -> float:
    if len(r) < 2:
        return float("nan")
    tot = float(np.prod(1.0 + r))
    if tot <= 0:
        return -1.0
    return float(tot ** (ANN / len(r)) - 1.0)


def max_drawdown(r: np.ndarray) -> float:
    """Positive fraction (0.15 = 15% peak-to-trough)."""
    if len(r) < 1:
        return float("nan")
    eq = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    peak = np.maximum.accumulate(eq)
    return float(np.max(1.0 - eq / peak))


def stationary_bootstrap_ci(r: np.ndarray, rng: np.random.Generator, B: int = config.BOOTSTRAP_RESAMPLES,
                            mean_block: int = config.BOOTSTRAP_MEAN_BLOCK, chunk: int = 250):
    """95% CI of the annualised Sharpe from a Politis-Romano stationary block bootstrap."""
    T = len(r)
    if T < 30 or r.std(ddof=1) == 0:
        return float("nan"), float("nan")
    p = 1.0 / mean_block
    pos = np.arange(T)
    out = []
    for c0 in range(0, B, chunk):
        b = min(chunk, B - c0)
        starts = rng.integers(0, T, size=(b, T))
        newb = rng.random((b, T)) < p
        newb[:, 0] = True
        last = np.maximum.accumulate(np.where(newb, pos, 0), axis=1)
        idx = (np.take_along_axis(starts, last, axis=1) + (pos - last)) % T
        samp = r[idx]
        m, s = samp.mean(axis=1), samp.std(axis=1, ddof=1)
        out.append(np.where(s > 0, m / np.where(s > 0, s, 1.0) * math.sqrt(ANN), np.nan))
    sh = np.concatenate(out)
    return float(np.nanpercentile(sh, 2.5)), float(np.nanpercentile(sh, 97.5))


def regime_mask(index: pd.DatetimeIndex, regime: str) -> np.ndarray:
    s, e = config.REGIMES[regime]
    return (index >= pd.Timestamp(s)) & (index <= pd.Timestamp(e))


def compute_metrics(daily: pd.DataFrame, trades: pd.DataFrame, spy_ret: pd.Series, covered_days: int,
                    full_window_days: int, rng: np.random.Generator | None = None,
                    bootstrap: bool = True) -> dict:
    """Flat dict of metrics for each regime plus extras.  `daily` needs net_ret, wA, wB columns."""
    out: dict = {}
    idx = daily.index
    r_all = daily["net_ret"].to_numpy()
    spy = spy_ret.reindex(idx).to_numpy()
    pos_on = (np.abs(daily["wA"].to_numpy()) + np.abs(daily["wB"].to_numpy())) > 1e-9
    closed = trades[~trades["open_at_end"].astype(bool)] if len(trades) else trades
    for reg in config.REGIME_ORDER:
        m = regime_mask(idx, reg)
        r = r_all[m]
        n = int(m.sum())
        out[f"{reg}_n_days"] = n
        if n < 2:
            for k in ("cagr", "vol", "sharpe", "sharpe_daily", "sortino", "maxdd", "exposure", "corr_spy",
                      "skew", "kurt"):
                out[f"{reg}_{k}"] = float("nan")
            out[f"{reg}_round_trips"] = 0
            out[f"{reg}_win_rate"] = float("nan")
            out[f"{reg}_avg_hold_days"] = float("nan")
            continue
        out[f"{reg}_cagr"] = cagr(r)
        out[f"{reg}_vol"] = float(r.std(ddof=1) * math.sqrt(ANN))
        out[f"{reg}_sharpe"] = sharpe(r)
        out[f"{reg}_sharpe_daily"] = sharpe_daily(r)
        out[f"{reg}_sortino"] = sortino(r)
        out[f"{reg}_maxdd"] = max_drawdown(r)
        out[f"{reg}_exposure"] = float(pos_on[m].mean())
        sp = spy[m]
        ok = np.isfinite(sp)
        out[f"{reg}_corr_spy"] = float(np.corrcoef(r[ok], sp[ok])[0, 1]) if ok.sum() > 2 and r[ok].std() > 0 and sp[ok].std() > 0 else float("nan")
        if r.std(ddof=1) > 0:
            out[f"{reg}_skew"] = float(sps.skew(r, bias=True))
            out[f"{reg}_kurt"] = float(sps.kurtosis(r, fisher=False, bias=True))   # non-excess
        else:
            out[f"{reg}_skew"], out[f"{reg}_kurt"] = float("nan"), float("nan")
        if len(closed):
            ed = pd.to_datetime(closed["entry_date"])
            tm = closed[(ed >= pd.Timestamp(config.REGIMES[reg][0])) & (ed <= pd.Timestamp(config.REGIMES[reg][1]))]
        else:
            tm = closed
        out[f"{reg}_round_trips"] = int(len(tm))
        out[f"{reg}_win_rate"] = float((tm["net_pnl"] > 0).mean()) if len(tm) else float("nan")
        out[f"{reg}_avg_hold_days"] = float(tm["holding_days"].mean()) if len(tm) else float("nan")
    # bootstrap CIs
    for reg in ("full", "post"):
        if bootstrap and rng is not None:
            r = r_all[regime_mask(idx, reg)]
            lo, hi = stationary_bootstrap_ci(r, rng)
        else:
            lo, hi = float("nan"), float("nan")
        out[f"{reg}_sharpe_ci_lo"], out[f"{reg}_sharpe_ci_hi"] = lo, hi
    # concentration and calendar-year risk
    if len(trades):
        pnl = trades["net_pnl"].to_numpy()
        tot = float(pnl.sum())
        top5 = float(np.sort(pnl)[::-1][:5].sum())
        out["top5_trade_share"] = top5 / tot if tot > 0 else float("nan")
        out["total_trade_pnl"] = tot
    else:
        out["top5_trade_share"], out["total_trade_pnl"] = float("nan"), 0.0
    yr = pd.Series(r_all, index=idx).groupby(idx.year).apply(lambda x: float(np.prod(1.0 + x.to_numpy()) - 1.0))
    if len(yr):
        out["worst_year"], out["worst_year_ret"] = int(yr.idxmin()), float(yr.min())
    else:
        out["worst_year"], out["worst_year_ret"] = None, float("nan")
    out["n_trades_total"] = int(len(trades))
    out["n_open_at_end"] = int(trades["open_at_end"].astype(bool).sum()) if len(trades) else 0
    out["covered_days"] = int(covered_days)
    out["coverage"] = float(covered_days / full_window_days) if full_window_days else float("nan")
    out["first_oos_day"] = str(idx[0].date()) if len(idx) else None
    mfull = regime_mask(idx, "full")
    out["cost_drag_ann_full"] = float((daily["gross_ret"].to_numpy()[mfull] - r_all[mfull]).mean() * ANN) if mfull.any() else float("nan")
    return out
