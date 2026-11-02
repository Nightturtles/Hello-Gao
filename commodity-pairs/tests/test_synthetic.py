"""Spec 12.3 and 12.4: the machinery finds a planted cointegrated pair, and does not find skill in noise."""
import numpy as np
import pytest
from statsmodels.tsa.stattools import coint

from backtest import metrics, multiple_testing as mt, walkforward as wf
from tests import synth


def test_synthetic_cointegrated_pair_sharpe_and_eg():
    """B is a random walk; A = exp(1.0 ln B + OU noise, half-life ~10d).  coint_ols: Sharpe > 1; EG p < 0.01."""
    p = synth.cointegrated(1, beta=1.0, half_life=10.0)
    res = wf.run_pair_rule("coint_ols", p, synth.WINDOWS)
    sr = metrics.sharpe(res.daily["net_ret"].to_numpy())
    assert sr > 1.0, sr
    _, pval, _ = coint(np.log(p.ac_a), np.log(p.ac_b), trend="c", autolag="aic")
    assert pval < 0.01, pval
    # the planted hedge ratio is recovered by the walk-forward fits
    betas = res.windows["beta"].astype(float)
    assert abs(betas.median() - 1.0) < 0.25
    assert len(res.trades) >= 20


@pytest.mark.parametrize("seed", [2, 3, 4])
def test_synthetic_cointegrated_pair_other_seeds(seed):
    p = synth.cointegrated(seed)
    res = wf.run_pair_rule("coint_ols", p, synth.WINDOWS)
    assert metrics.sharpe(res.daily["net_ret"].to_numpy()) > 1.0


def test_independent_random_walks_no_deflated_skill():
    """50 independent random-walk pairs: even the best of 50 trials must not clear DSR 0.95."""
    from scipy import stats as sps

    srs, sk, ku, T = [], [], [], []
    for seed in range(50):
        r = wf.run_pair_rule("coint_ols", synth.independent(seed), synth.WINDOWS).daily["net_ret"].to_numpy()
        srs.append(metrics.sharpe_daily(r))
        sk.append(float(sps.skew(r, bias=True)))
        ku.append(float(sps.kurtosis(r, fisher=False, bias=True)))
        T.append(len(r))
    tab, n, v = mt.dsr_table(np.array(srs), np.array(sk), np.array(ku), np.array(T), n_trials=50)
    assert n == 50 and v > 0
    assert np.nanmax(tab["dsr"].to_numpy()) < 0.95
    # without deflation (PSR vs 0) the luckiest trial looks better than its deflated score
    assert np.nanmax(tab["psr0"].to_numpy()) >= np.nanmax(tab["dsr"].to_numpy())
