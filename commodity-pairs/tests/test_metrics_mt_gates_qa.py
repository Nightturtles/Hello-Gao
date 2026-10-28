"""Metrics, multiple-testing, gate and data-QA unit tests."""
import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests

from backtest import config, data, gates, metrics, multiple_testing as mt


# ----------------------------------------------------------------------------- metrics
def test_drawdown_sharpe_cagr_known_values():
    r = np.array([0.10, -0.50, 0.20])
    assert metrics.max_drawdown(r) == pytest.approx(0.5)
    r2 = np.array([0.01, -0.01, 0.02, 0.0])
    assert metrics.sharpe(r2) == pytest.approx(r2.mean() / r2.std(ddof=1) * math.sqrt(252))
    assert metrics.sortino(r2) == pytest.approx(r2.mean() / math.sqrt(np.mean(np.minimum(r2, 0) ** 2)) * math.sqrt(252))
    flat = np.zeros(10)
    assert math.isnan(metrics.sharpe(flat))
    yr = np.full(252, 0.001)
    assert metrics.cagr(yr) == pytest.approx(1.001 ** 252 - 1)


def test_bootstrap_ci_brackets_point_estimate_and_is_seeded():
    rng = np.random.default_rng(1)
    r = rng.normal(0.0008, 0.01, 1500)
    lo, hi = metrics.stationary_bootstrap_ci(r, np.random.default_rng(5), B=600)
    lo2, hi2 = metrics.stationary_bootstrap_ci(r, np.random.default_rng(5), B=600)
    assert (lo, hi) == (lo2, hi2)
    assert lo < metrics.sharpe(r) < hi


def test_round_trips_belong_to_regime_of_entry_and_open_trade_not_counted():
    idx = pd.bdate_range("2016-10-03", "2026-10-26")
    daily = pd.DataFrame({"net_ret": 0.0, "gross_ret": 0.0, "wA": 0.0, "wB": 0.0}, index=idx)
    daily.iloc[::7, 0] = 0.001
    trades = pd.DataFrame({
        "entry_date": pd.to_datetime(["2017-01-03", "2020-02-27", "2020-03-02", "2022-01-03", "2025-01-02"]),
        "exit_date": pd.to_datetime(["2017-01-10", "2020-03-10", "2020-03-12", "2022-01-10", "2026-10-26"]),
        "net_pnl": [10.0, -5.0, 3.0, 4.0, 1.0], "holding_days": [5, 8, 8, 5, 3],
        "open_at_end": [False, False, False, False, True]})
    spy = pd.Series(0.0005, index=idx)
    m = metrics.compute_metrics(daily, trades, spy, covered_days=len(idx), full_window_days=len(idx), bootstrap=False)
    assert m["pre_round_trips"] == 2 and m["covid_round_trips"] == 1 and m["post_round_trips"] == 1
    assert m["full_round_trips"] == 4 and m["n_open_at_end"] == 1
    assert m["pre_win_rate"] == pytest.approx(0.5)


# ----------------------------------------------------------------------------- multiple testing
def test_expected_max_sr_and_psr_formulas():
    N, V = 223, 0.0004
    g = 0.5772156649
    exp = math.sqrt(V) * ((1 - g) * norm.ppf(1 - 1 / N) + g * norm.ppf(1 - 1 / (N * math.e)))
    assert mt.expected_max_sr(V, N) == pytest.approx(exp)
    assert mt.expected_max_sr(V, N) > 0
    sr, T = 0.1, 252
    manual = norm.cdf(sr * math.sqrt(T - 1) / math.sqrt(1 - 0 * sr + (3 - 1) / 4 * sr ** 2))
    assert mt.prob_sharpe(sr, 0.0, 0.0, 3.0, T) == pytest.approx(manual)
    # deflation lowers the score
    assert mt.prob_sharpe(sr, mt.expected_max_sr(V, N), 0.0, 3.0, T) < mt.prob_sharpe(sr, 0.0, 0.0, 3.0, T)


def test_bh_family_matches_statsmodels_and_is_conservative_vs_raw():
    pool = pd.DataFrame({"pair_id": ["P1", "P2", "P3"], "type": ["coint", "leadlag", "inverse"]})
    rows = []
    rng = np.random.default_rng(3)
    for pid in pool.pair_id:
        for reg in ("full", "post", "pre"):
            rows.append({"pair_id": pid, "regime": reg, "eg_p_primary": rng.uniform(0, 0.3),
                         "granger_p_ab": rng.uniform(0, 1), "granger_p_ba": rng.uniform(0, 1),
                         "inv_p_onesided": rng.uniform(0, 1)})
    fam = mt.build_family(pd.DataFrame(rows), pool)
    assert set(fam.window) == {"full", "post"}                       # 'pre' is not part of the family
    assert len(fam) == 3 * 2 * 3 + 1 * 2                              # 3 tests per pair/window + granger_ba for the leadlag pair
    _, padj, _, _ = multipletests(fam["p_raw"], alpha=0.05, method="fdr_bh")
    assert np.allclose(fam["p_bh"], padj) and (fam["p_bh"] >= fam["p_raw"] - 1e-15).all()
    assert (fam["p_bonf"] >= fam["p_bh"] - 1e-12).all()


# ----------------------------------------------------------------------------- gates
def _row(**kw):
    base = dict(pair_id="X", rule="coint_ols", full_sharpe=1.2, post_sharpe=0.9, pre_sharpe=0.5, full_maxdd=0.15,
                post_maxdd=0.1, full_round_trips=30, post_round_trips=12, p_bh_full=0.01, p_bh_post=0.02,
                dsr_full=0.97, dsr_post=0.5, coverage=0.9)
    base.update(kw)
    return base


def test_gate_logic_rule_a_rule_b_and_flags():
    df = pd.DataFrame([
        _row(),                                             # passes (a)
        _row(full_sharpe=0.99),                             # fails (a) Sharpe
        _row(p_bh_post=0.06),                               # fails (a) BH post
        _row(dsr_full=0.949),                               # fails (a) DSR
        _row(full_maxdd=0.2001),                            # fails (a) drawdown
        _row(full_round_trips=19),                          # fails (a) trips
        _row(coverage=0.79),                                # fails (a) coverage
        _row(post_round_trips=4),                           # fails hard sanity gate
        _row(full_sharpe=0.2, post_sharpe=1.4, dsr_full=0.3, dsr_post=0.96, post_round_trips=25),   # passes (b) only
        _row(full_sharpe=0.2, post_sharpe=1.4, dsr_full=0.3, dsr_post=0.96, post_round_trips=25, p_bh_post=0.2),
        _row(pre_sharpe=1.5, full_sharpe=0.3),              # pre_only
        _row(full_sharpe=np.nan, post_sharpe=np.nan),       # NaN never passes
    ])
    out = gates.apply_gates(df)
    assert list(out["pass_a"]) == [True, False, False, False, False, False, False, False, False, False, False, False]
    assert list(out["pass_b"])[8] and not list(out["pass_b"])[9]
    assert list(out["quant_pass"])[8] and not out["needs_regime_change_explanation"].iloc[0]
    assert out["needs_regime_change_explanation"].iloc[8]
    assert list(out["pre_only"])[10] and not out["pre_only"].iloc[0]
    assert "full Sharpe" in out["fail_reasons"].iloc[1]
    assert out["fail_reasons"].iloc[0] == ""


# ----------------------------------------------------------------------------- data QA
def _frame(n=400, seed=0):
    idx = pd.bdate_range("2020-01-01", periods=n)
    rng = np.random.default_rng(seed)
    close = 50 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    df = pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "adjclose": close,
                       "volume": 1e6, "dividends": 0.0, "splits": 0.0}, index=idx)
    return df


def test_qa_flags_each_problem_class():
    sess = pd.bdate_range("2020-01-01", periods=400)
    clean = _frame()
    assert not [r for r in data.qa_ticker("OK", clean, sess) if r["severity"] == "error"]
    bad = clean.copy()
    bad.iloc[100, bad.columns.get_loc("close")] = 0.0
    assert any(r["check"] == "nonpositive_price" and r["severity"] == "error" for r in data.qa_ticker("Z", bad, sess))
    nan = clean.copy()
    nan.iloc[50, nan.columns.get_loc("adjclose")] = np.nan
    assert any(r["check"] == "nan_price" and r["severity"] == "error" for r in data.qa_ticker("N", nan, sess))
    # unadjusted 2:1 split: price halves on the split date in both close and adjclose
    sp = clean.copy()
    sp.iloc[200:, sp.columns.get_loc("close")] *= 0.4
    sp.iloc[200:, sp.columns.get_loc("adjclose")] *= 0.4
    sp.iloc[200, sp.columns.get_loc("splits")] = 2.5
    res = data.qa_ticker("S", sp, sess)
    assert any(r["check"] == "abs_adjret_gt_25pct" and r["severity"] == "error" and "SPLIT_ADJUSTMENT_SUSPECT" in r["detail"]
               for r in res)
    # a genuine large move without a split is a warning, not an error
    gm = clean.copy()
    gm.iloc[200:, gm.columns.get_loc("close")] *= 1.4
    gm.iloc[200:, gm.columns.get_loc("adjclose")] *= 1.4
    res = data.qa_ticker("G", gm, sess)
    assert any(r["check"] == "abs_adjret_gt_25pct" and r["severity"] == "warning" for r in res)
    # a 10x one-day jump with no split is a spliced security (cancelled equity -> new shares), not a move
    sx = clean.copy()
    sx.iloc[:200, sx.columns.get_loc("close")] *= 0.01
    sx.iloc[:200, sx.columns.get_loc("adjclose")] *= 0.01
    res = data.qa_ticker("X", sx, sess)
    assert any(r["check"] == "abs_adjret_gt_25pct" and r["severity"] == "error" and "SECURITY_SPLICE_SUSPECT" in r["detail"]
               for r in res)
    # stale prints: >=5 identical closes with zero volume
    st = clean.copy()
    st.iloc[300:308, st.columns.get_loc("close")] = 77.0
    st.iloc[300:308, st.columns.get_loc("volume")] = 0
    assert any(r["check"] == "identical_close_run_ge5" and r["severity"] == "error" for r in data.qa_ticker("T", st, sess))
    # missing sessions are reported
    gap = clean.drop(clean.index[120:123])
    assert any(r["check"] == "missing_nyse_sessions" and r["count"] == 3 for r in data.qa_ticker("M", gap, sess))


def test_adjusted_open_formula():
    df = _frame(5)
    df["adjclose"] = df["close"] * 0.9
    out = data.with_adjopen(df)
    assert np.allclose(out["adjopen"], df["open"] * 0.9)
