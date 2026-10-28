"""Statistical relationship tests (spec section 4) -> backtest/results/stats_tests.csv.

All tests use log adjusted closes (levels) or daily log returns, restricted to the regime window.  These are
full-window in-sample tests (as the spec prescribes); they are used only for the type-consistency p-value gate,
never to pick parameters.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from statsmodels.tsa.stattools import adfuller, coint, grangercausalitytests
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from . import config, strategies

CORR_WINDOWS = (60, 120, 250)
XCORR_LAGS = tuple(range(-10, 11))


def _ols_beta(y: np.ndarray, x: np.ndarray):
    xm, ym = x.mean(), y.mean()
    dx = x - xm
    b = float(dx @ (y - ym)) / float(dx @ dx)
    a = ym - b * xm
    return a, b, y - a - b * x


def half_life(s: np.ndarray) -> tuple[float, float]:
    """Regress ds_t on s_{t-1} with intercept; HL = -ln2/ln(1+b).  Returns (b, HL). inf if b >= 0."""
    ds = np.diff(s)
    lag = s[:-1]
    _, b, _ = _ols_beta(ds, lag)
    if b >= 0:
        return b, float("inf")
    if b <= -1:
        return b, float("nan")
    return b, -math.log(2.0) / math.log(1.0 + b)


def hurst(s: np.ndarray, lags=range(2, 101)) -> float:
    """Variance-of-lagged-differences Hurst exponent: slope of log std(s[t+l]-s[t]) on log l."""
    lags = [l for l in lags if l < len(s) - 2]
    tau = np.array([np.std(s[l:] - s[:-l], ddof=1) for l in lags])
    ok = tau > 0
    if ok.sum() < 5:
        return float("nan")
    return float(np.polyfit(np.log(np.asarray(lags)[ok]), np.log(tau[ok]), 1)[0])


def granger_p(y: np.ndarray, x: np.ndarray, maxlag: int = 5) -> float:
    """SSR F-test p-value at `maxlag`: do lags of x jointly help predict y?"""
    data = np.column_stack([y, x])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = grangercausalitytests(data, maxlag=maxlag)
    return float(res[maxlag][0]["ssr_ftest"][1])


def inverse_test(ra: np.ndarray, rb: np.ndarray) -> dict:
    """r_A = a + b r_B + e, Newey-West HAC (maxlags=10); one-sided p-value for slope < 0."""
    X = sm.add_constant(rb)
    res = sm.OLS(ra, X).fit(cov_type="HAC", cov_kwds={"maxlags": 10})
    slope, se = float(res.params[1]), float(res.bse[1])
    t = slope / se if se > 0 else float("nan")
    return {"inv_slope": slope, "inv_t": t, "inv_p_onesided": float(norm.cdf(t)),
            "inv_corr": float(np.corrcoef(ra, rb)[0, 1])}


def pair_regime_stats(pair, la: pd.Series, lb: pd.Series, kal_beta: pd.Series, regime: str,
                      start: str, end: str) -> dict:
    """Stats for one pair in one regime window.  la/lb: log adjusted closes indexed by date."""
    sl = slice(pd.Timestamp(start), pd.Timestamp(end))
    a, b = la.loc[sl], lb.loc[sl]
    ok = a.notna() & b.notna()
    a, b = a[ok], b[ok]
    rec = {"pair_id": pair.pair_id, "leg_a": pair.leg_a, "leg_b": pair.leg_b, "type": pair.type,
           "expected_corr_sign": pair.expected_corr_sign, "regime": regime, "start": str(start), "end": str(end),
           "n_obs": int(len(a)), "first_date": str(a.index[0].date()) if len(a) else None,
           "last_date": str(a.index[-1].date()) if len(a) else None}
    if len(a) < 130:
        rec["note"] = "insufficient data in regime"
        return rec
    ra, rb = a.diff().dropna(), b.diff().dropna()
    exp_sign = 1.0 if str(pair.expected_corr_sign).strip() == "+" else -1.0
    # rolling return correlations (computed inside the regime window only)
    for w in CORR_WINDOWS:
        rc = ra.rolling(w).corr(rb).dropna()
        if len(rc):
            rec[f"rc{w}_mean"], rec[f"rc{w}_std"] = float(rc.mean()), float(rc.std())
            rec[f"rc{w}_min"], rec[f"rc{w}_max"] = float(rc.min()), float(rc.max())
            rec[f"rc{w}_frac_expected_sign"] = float((np.sign(rc) == exp_sign).mean())
            rec[f"rc{w}_frac_negative"] = float((rc < 0).mean())
        else:
            for k in ("mean", "std", "min", "max", "frac_expected_sign", "frac_negative"):
                rec[f"rc{w}_{k}"] = np.nan
    av, bv = a.to_numpy(), b.to_numpy()
    # Engle-Granger, both orderings; PRIMARY = A on B
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        st_ab, p_ab, _ = coint(av, bv, trend="c", autolag="aic")
        st_ba, p_ba, _ = coint(bv, av, trend="c", autolag="aic")
    rec.update({"eg_stat_ab": float(st_ab), "eg_p_ab": float(p_ab), "eg_stat_ba": float(st_ba), "eg_p_ba": float(p_ba),
                "eg_p_primary": float(p_ab)})
    # Johansen (det_order=0, k_ar_diff=1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        jo = coint_johansen(np.column_stack([av, bv]), det_order=0, k_ar_diff=1)
    cvt = jo.cvt   # rows: r=0, r<=1 ; cols: 90, 95, 99
    rec.update({"joh_trace_r0": float(jo.lr1[0]), "joh_cv90_r0": float(cvt[0, 0]), "joh_cv95_r0": float(cvt[0, 1]),
                "joh_cv99_r0": float(cvt[0, 2]), "joh_trace_r1": float(jo.lr1[1]), "joh_cv95_r1": float(cvt[1, 1]),
                "joh_pass95": bool(jo.lr1[0] > cvt[0, 1])})
    # OLS spread: ADF, half-life, Hurst, hedge ratio
    alpha, beta, resid = _ols_beta(av, bv)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        adf = adfuller(resid, autolag="AIC")
    bcoef, hl = half_life(resid)
    rec.update({"ols_alpha": float(alpha), "ols_beta": float(beta), "adf_stat": float(adf[0]), "adf_p": float(adf[1]),
                "hl_b": float(bcoef), "half_life_days": hl, "hurst": hurst(resid)})
    # Kalman beta path inside the regime
    kb = kal_beta.loc[sl].dropna()
    if len(kb):
        rec.update({"kalman_beta_mean": float(kb.mean()), "kalman_beta_std": float(kb.std()),
                    "kalman_beta_min": float(kb.min()), "kalman_beta_max": float(kb.max())})
    # Granger (returns): primary a->b, also b->a
    rav, rbv = ra.to_numpy(), rb.to_numpy()
    rec["granger_p_ab"] = granger_p(rbv, rav)       # do lags of A predict B?
    rec["granger_p_ba"] = granger_p(rav, rbv)
    # lagged cross-correlation corr(r_A[t], r_B[t+k]); k>0: A leads B
    n = len(rav)
    for k in XCORR_LAGS:
        if k >= 0:
            x, y = rav[:n - k], rbv[k:]
        else:
            x, y = rav[-k:], rbv[:n + k]
        rec[f"xcorr_{'m' if k < 0 else 'p'}{abs(k)}"] = float(np.corrcoef(x, y)[0, 1])
    rec.update(inverse_test(rav, rbv))
    return rec


def run_stats(pool: pd.DataFrame, panel: dict, params: dict | None = None) -> pd.DataFrame:
    params = params or config.PARAMS
    la_all = np.log(panel["adjclose"])
    rows = []
    for pair in pool.itertuples():
        la, lb = la_all[pair.leg_a], la_all[pair.leg_b]
        both = la.notna() & lb.notna()
        # Kalman beta path over the pair's full joint history (state used to form the spread at t is beta_{t-1})
        jl, jb = la[both], lb[both]
        _, kbeta, _ = strategies.kalman_path(jl.to_numpy(), jb.to_numpy(), params)
        kal = pd.Series(kbeta, index=jl.index)
        for regime in config.REGIME_ORDER:
            s, e = config.REGIMES[regime]
            rows.append(pair_regime_stats(pair, la, lb, kal, regime, s, e))
    return pd.DataFrame(rows)
