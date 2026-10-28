"""Benchmarks and random-pair baseline (spec section 8)."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from . import config, metrics, runner
from .screen import complete_mask, window_eligibility
from .trading_calendar import Window

BASELINE_RULES = ("coint_ols", "rotation")


def draw_random_pairs(screen: pd.DataFrame, candidates: pd.DataFrame, panel: dict, sess: pd.DatetimeIndex,
                      windows: list[Window], n: int, rng: np.random.Generator) -> list[tuple[str, str, str]]:
    """Random pairs from tickers that pass data QA, liquidity and rule-(b) history; candidate pairs excluded."""
    ok = screen[(screen["data_ok"]) & (screen["liq_pass"]) & (screen["rule_b_eligible"])]["ticker"].tolist()
    ok = sorted(ok)
    cand = {frozenset((a, b)) for a, b in zip(candidates["leg_a"], candidates["leg_b"])}
    masks = {t: complete_mask(panel, [t]) for t in ok}
    combos = []
    for a, b in itertools.combinations(ok, 2):
        if frozenset((a, b)) in cand:
            continue
        m = masks[a] & masks[b]
        elig = window_eligibility(m, windows)
        first = next((w.test_start for w, e in zip(windows, elig) if e), None)
        if first is None or sess[first] > config.RULE_B_OOS_BY:
            continue
        combos.append((a, b))
    idx = rng.choice(len(combos), size=min(n, len(combos)), replace=False)
    out = []
    for j in sorted(idx.tolist()):
        a, b = combos[j]
        if rng.random() < 0.5:
            a, b = b, a
        out.append((f"RND_{a}_{b}", a, b))
    return out


def run_baseline(screen, candidates, panel, sess, windows, spy_ret, full_days, rng, n_pairs: int,
                 processes: int | None = None) -> pd.DataFrame:
    pairs = draw_random_pairs(screen, candidates, panel, sess, windows, n_pairs, rng)
    runner.set_context(panel, screen, windows, spy_ret, full_days, None)
    tasks = []
    for pid, a, b in pairs:
        for rule in BASELINE_RULES:
            tasks.append({"idx": len(tasks), "pair_id": pid, "leg_a": a, "leg_b": b, "rule": rule,
                          "save": False, "bootstrap": False})
    res = runner.run_tasks(tasks, processes)
    keep = ["pair_id", "leg_a", "leg_b", "rule", "first_oos_day", "coverage", "full_sharpe", "post_sharpe",
            "pre_sharpe", "covid_sharpe", "full_cagr", "post_cagr", "full_maxdd", "post_maxdd", "full_round_trips",
            "post_round_trips", "full_exposure", "full_corr_spy"]
    return pd.DataFrame([{k: m.get(k) for k in keep} for m, _ in res])


def percentile_of(value: float, dist: np.ndarray) -> float:
    dist = dist[np.isfinite(dist)]
    if not np.isfinite(value) or len(dist) == 0:
        return float("nan")
    return float(100.0 * (dist <= value).mean())


def add_baseline_percentiles(trials: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    out = trials.copy()
    for win in ("full", "post"):
        col = f"{win}_sharpe_baseline_pctile"
        vals = []
        for r in out.itertuples():
            d = base.loc[base["rule"] == r.rule, f"{win}_sharpe"].to_numpy(dtype=float)
            vals.append(percentile_of(getattr(r, f"{win}_sharpe"), d) if len(d) else float("nan"))
        out[col] = vals
    return out


def baseline_summary(base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rule, g in base.groupby("rule"):
        for win in ("full", "post"):
            x = g[f"{win}_sharpe"].astype(float)
            xf = x[np.isfinite(x)]
            rows.append({"rule": rule, "window": win, "n_runs": len(g), "n_defined": len(xf),
                         "mean": xf.mean(), "std": xf.std(ddof=1), "p05": xf.quantile(.05), "p25": xf.quantile(.25),
                         "median": xf.median(), "p75": xf.quantile(.75), "p95": xf.quantile(.95),
                         "p99": xf.quantile(.99), "max": xf.max(), "frac_ge_1": float((xf >= 1.0).mean()),
                         "frac_ge_0p8": float((xf >= 0.8).mean())})
    return pd.DataFrame(rows)


def buy_and_hold(panel: dict, pool: pd.DataFrame, first_oos: dict[str, str]) -> pd.DataFrame:
    """Buy-and-hold of each leg and of SPY over each pair's OOS span (first OOS day -> snapshot end)."""
    ac = panel["adjclose"]
    ret = ac.pct_change()
    rows = []
    end = pd.Timestamp(config.REGIMES["full"][1])
    for r in pool.itertuples():
        start = pd.Timestamp(first_oos[r.pair_id])
        for role, t in (("leg_a", r.leg_a), ("leg_b", r.leg_b), ("SPY", "SPY")):
            x = ret[t].loc[start:end].dropna().to_numpy()
            rows.append({"pair_id": r.pair_id, "role": role, "ticker": t, "span_start": str(start.date()),
                         "n_days": len(x), "cagr": metrics.cagr(x), "sharpe": metrics.sharpe(x),
                         "maxdd": metrics.max_drawdown(x)})
    return pd.DataFrame(rows)
