"""Multiple-testing control (spec section 9): Benjamini-Hochberg across the relationship family, Bonferroni
alongside, and the Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests

from . import config

EULER_GAMMA = 0.5772156649
FAMILY_WINDOWS = ("full", "post")


def build_family(stats: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    """Every primary p-value that is computed: (pair, test type, window in {full, post}).

    Test types: eg (A on B), granger_ab, inverse (one-sided slope<0), and granger_ba for the pairs the scouts
    labelled `leadlag` (their reverse-direction trial passes on it)."""
    rows = []
    leadlag_pairs = set(pool.loc[pool["type"] == "leadlag", "pair_id"])
    for r in stats[stats["regime"].isin(FAMILY_WINDOWS)].itertuples():
        tests = [("eg", r.eg_p_primary), ("granger_ab", r.granger_p_ab), ("inverse", r.inv_p_onesided)]
        if r.pair_id in leadlag_pairs:
            tests.append(("granger_ba", r.granger_p_ba))
        for name, p in tests:
            rows.append({"pair_id": r.pair_id, "test": name, "window": r.regime, "p_raw": p})
    fam = pd.DataFrame(rows)
    ok = fam["p_raw"].notna()
    fam["p_bh"] = np.nan
    fam["p_bonf"] = np.nan
    fam["bh_reject_q05"] = False
    if ok.any():
        rej, padj, _, _ = multipletests(fam.loc[ok, "p_raw"].to_numpy(), alpha=config.FDR_Q, method="fdr_bh")
        fam.loc[ok, "p_bh"], fam.loc[ok, "bh_reject_q05"] = padj, rej
        fam.loc[ok, "p_bonf"] = multipletests(fam.loc[ok, "p_raw"].to_numpy(), alpha=config.FDR_Q, method="bonferroni")[1]
    fam["family_size"] = int(ok.sum())
    return fam


def expected_max_sr(v: float, n_trials: int) -> float:
    """SR0 = sqrt(V) * [(1-g) Phi^-1(1-1/N) + g Phi^-1(1-1/(N e))]."""
    if n_trials < 2 or not math.isfinite(v) or v < 0:
        return float("nan")
    g = EULER_GAMMA
    return math.sqrt(v) * ((1 - g) * norm.ppf(1 - 1.0 / n_trials) + g * norm.ppf(1 - 1.0 / (n_trials * math.e)))


def prob_sharpe(sr: float, sr_bench: float, skew: float, kurt: float, T: int) -> float:
    """Probabilistic Sharpe ratio P(SR_true > sr_bench); sr per observation (daily), kurt non-excess."""
    if T < 3 or not all(math.isfinite(x) for x in (sr, sr_bench, skew, kurt)):
        return float("nan")
    den = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if den <= 0:
        return float("nan")
    return float(norm.cdf((sr - sr_bench) * math.sqrt(T - 1) / math.sqrt(den)))


def dsr_table(sr_daily: np.ndarray, skew: np.ndarray, kurt: np.ndarray, T: np.ndarray, n_trials: int | None = None):
    """DSR for a set of trials measured on the same window.

    N = n_trials (default: number of trials supplied); V = sample variance (ddof=1) of the finite per-day Sharpe
    ratios.  Returns DataFrame(sr0, dsr, psr) and the (N, V) used."""
    sr_daily = np.asarray(sr_daily, dtype=float)
    n = int(n_trials if n_trials is not None else len(sr_daily))
    finite = np.isfinite(sr_daily)
    v = float(np.var(sr_daily[finite], ddof=1)) if finite.sum() > 1 else float("nan")
    sr0 = expected_max_sr(v, n)
    dsr = np.array([prob_sharpe(s, sr0, k3, k4, int(t)) if np.isfinite(s) else np.nan
                    for s, k3, k4, t in zip(sr_daily, skew, kurt, T)])
    psr = np.array([prob_sharpe(s, 0.0, k3, k4, int(t)) if np.isfinite(s) else np.nan
                    for s, k3, k4, t in zip(sr_daily, skew, kurt, T)])
    return pd.DataFrame({"sr0_daily": sr0, "dsr": dsr, "psr0": psr}), n, v


def add_dsr(trials: pd.DataFrame) -> pd.DataFrame:
    """Add DSR/PSR columns for the full window (rule a) and the post-COVID window (rule b)."""
    out = trials.copy()
    for reg in ("full", "post"):
        tab, n, v = dsr_table(out[f"{reg}_sharpe_daily"].to_numpy(), out[f"{reg}_skew"].to_numpy(),
                              out[f"{reg}_kurt"].to_numpy(), out[f"{reg}_n_days"].to_numpy(), n_trials=len(out))
        out[f"dsr_{reg}"] = tab["dsr"].to_numpy()
        out[f"psr_{reg}"] = tab["psr0"].to_numpy()
        out[f"sr0_{reg}_daily"] = tab["sr0_daily"].to_numpy()
        out[f"sr0_{reg}_ann"] = tab["sr0_daily"].to_numpy() * math.sqrt(252)
        out[f"dsr_N_{reg}"] = n
        out[f"dsr_V_{reg}"] = v
    return out
