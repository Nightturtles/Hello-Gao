"""Synthetic price generators shared by the tests."""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import walkforward as wf
from backtest.trading_calendar import sessions, walk_forward_grid

SESS = sessions()
WINDOWS = walk_forward_grid(SESS)


def _prices(log_close: np.ndarray, rng: np.random.Generator, gap_sd: float = 0.004):
    close = np.exp(log_close)
    prev = np.r_[close[0], close[:-1]]
    open_ = prev * np.exp(rng.normal(0.0, gap_sd, len(close)))
    return close, open_


def pair_data(log_a: np.ndarray, log_b: np.ndarray, seed: int, pair_id: str = "SYN", slip_bps: float = 5.0,
              borrow: float = 0.005) -> wf.PairData:
    rng = np.random.default_rng(seed + 10_000)
    ca, oa = _prices(log_a, rng)
    cb, ob = _prices(log_b, rng)
    s = slip_bps / 1e4
    return wf.PairData(pair_id, "A", "B", SESS, ca, cb, oa, ob, oa.copy(), ob.copy(), s, s, borrow, borrow)


def random_walk(n: int, seed: int, vol: float = 0.012, drift: float = 0.0002, start: float = 50.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.log(start) + np.cumsum(rng.normal(drift, vol, n))


def ou(n: int, seed: int, half_life: float = 10.0, stat_sd: float = 0.05) -> np.ndarray:
    rng = np.random.default_rng(seed)
    phi = 0.5 ** (1.0 / half_life)
    sig = stat_sd * np.sqrt(1 - phi ** 2)
    x = np.zeros(n)
    x[0] = rng.normal(0, stat_sd)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal(0, sig)
    return x


def cointegrated(seed: int, beta: float = 1.0, half_life: float = 10.0, stat_sd: float = 0.05, **kw) -> wf.PairData:
    n = len(SESS)
    lb = random_walk(n, seed)
    la = beta * lb + ou(n, seed + 1, half_life, stat_sd) + np.log(2.0)
    return pair_data(la, lb, seed, **kw)


def independent(seed: int, **kw) -> wf.PairData:
    n = len(SESS)
    return pair_data(random_walk(n, 2 * seed + 1), random_walk(n, 2 * seed + 2), seed, **kw)


def leadlag(seed: int, lag: int = 3, strength: float = 0.8, contemp: float = 0.5, **kw) -> wf.PairData:
    """B (follower) reacts to the leader A's return `lag` days earlier (plus a contemporaneous loading)."""
    n = len(SESS)
    rng = np.random.default_rng(seed)
    ra = rng.normal(0.0002, 0.012, n)
    rb = rng.normal(0.0002, 0.006, n) + contemp * ra
    rb[lag:] += strength * ra[:-lag]
    return pair_data(np.log(50) + np.cumsum(ra), np.log(50) + np.cumsum(rb), seed, **kw)


def panel_from_pairs(pairs: list, seed: int = 0):
    """Build a (panel, screen) like the real data layer from synthetic PairData objects (tickers S{i}A / S{i}B)."""
    cols_ac, cols_ao, cols_ro = {}, {}, {}
    rows = []
    for i, p in enumerate(pairs):
        for side, ac, ao, ro in (("A", p.ac_a, p.ao_a, p.ro_a), ("B", p.ac_b, p.ao_b, p.ro_b)):
            t = f"S{i}{side}"
            cols_ac[t], cols_ao[t], cols_ro[t] = ac, ao, ro
            rows.append({"ticker": t, "slippage_bps": 5.0, "borrow_rate": 0.005})
    spy = random_walk(len(SESS), seed + 777, vol=0.01, drift=0.0004)
    cols_ac["SPY"] = np.exp(spy)
    cols_ao["SPY"] = np.exp(spy)
    cols_ro["SPY"] = np.exp(spy)
    rows.append({"ticker": "SPY", "slippage_bps": 5.0, "borrow_rate": 0.005})
    mk = lambda d: pd.DataFrame(d, index=SESS)   # noqa: E731
    panel = {"adjclose": mk(cols_ac), "adjopen": mk(cols_ao), "open": mk(cols_ro), "close": mk(cols_ac),
             "volume": mk({k: np.full(len(SESS), 1e6) for k in cols_ac})}
    return panel, pd.DataFrame(rows)
