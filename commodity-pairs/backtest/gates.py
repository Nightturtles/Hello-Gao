"""Pass gates (spec section 10) -> backtest/results/gates.csv.  Thresholds are pre-registered; never relaxed."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import strategies

# rule (a)
A_SHARPE_FULL, A_SHARPE_POST, A_MAXDD, A_TRIPS_FULL = 1.0, 0.8, 0.20, 20
A_P, A_DSR, A_COVERAGE, A_TRIPS_POST = 0.05, 0.95, 0.80, 5
# rule (b)
B_SHARPE_POST, B_MAXDD, B_TRIPS_POST, B_P, B_DSR = 1.0, 0.20, 20, 0.05, 0.95
PRE_SHARPE = 1.0


def _ge(x, thr) -> bool:
    return bool(pd.notna(x) and x >= thr)


def _le(x, thr) -> bool:
    return bool(pd.notna(x) and x <= thr)


def _lt(x, thr) -> bool:
    return bool(pd.notna(x) and x < thr)


def _fmt(x, nd=3):
    return "nan" if pd.isna(x) else f"{x:.{nd}f}"


def attach_primary_p(trials: pd.DataFrame, family: pd.DataFrame) -> pd.DataFrame:
    """Attach, by type consistency, the primary raw / BH / Bonferroni p for the full and post windows."""
    out = trials.copy()
    out["primary_test"] = out["rule"].map(strategies.RULE_P_TYPE)
    fam = family.set_index(["pair_id", "test", "window"])
    for win in ("full", "post"):
        for col, src in (("p_raw", "p_raw"), ("p_bh", "p_bh"), ("p_bonf", "p_bonf")):
            vals = []
            for r in out.itertuples():
                key = (r.pair_id, r.primary_test, win)
                vals.append(fam.at[key, src] if key in fam.index else np.nan)
            out[f"{col}_{win}"] = vals
    return out


def apply_gates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    g = {}
    g["a_sharpe_full"] = [_ge(x, A_SHARPE_FULL) for x in out["full_sharpe"]]
    g["a_sharpe_post"] = [_ge(x, A_SHARPE_POST) for x in out["post_sharpe"]]
    g["a_maxdd_full"] = [_le(x, A_MAXDD) for x in out["full_maxdd"]]
    g["a_trips_full"] = [_ge(x, A_TRIPS_FULL) for x in out["full_round_trips"]]
    g["a_bh_full"] = [_lt(x, A_P) for x in out["p_bh_full"]]
    g["a_bh_post"] = [_lt(x, A_P) for x in out["p_bh_post"]]
    g["a_dsr_full"] = [_ge(x, A_DSR) for x in out["dsr_full"]]
    g["a_coverage"] = [_ge(x, A_COVERAGE) for x in out["coverage"]]
    g["a_trips_post"] = [_ge(x, A_TRIPS_POST) for x in out["post_round_trips"]]
    g["b_sharpe_post"] = [_ge(x, B_SHARPE_POST) for x in out["post_sharpe"]]
    g["b_maxdd_post"] = [_le(x, B_MAXDD) for x in out["post_maxdd"]]
    g["b_trips_post"] = [_ge(x, B_TRIPS_POST) for x in out["post_round_trips"]]
    g["b_bh_post"] = [_lt(x, B_P) for x in out["p_bh_post"]]
    g["b_dsr_post"] = [_ge(x, B_DSR) for x in out["dsr_post"]]
    for k, v in g.items():
        out[k] = v
    a_cols = [c for c in g if c.startswith("a_")]
    b_cols = [c for c in g if c.startswith("b_")]
    out["pass_a"] = out[a_cols].all(axis=1)
    out["pass_b"] = out[b_cols].all(axis=1)
    out["quant_pass"] = out["pass_a"] | out["pass_b"]
    out["needs_regime_change_explanation"] = out["pass_b"] & ~out["pass_a"]
    out["pre_only"] = (out["pre_sharpe"] >= PRE_SHARPE) & ~out["quant_pass"]

    def reasons(r) -> str:
        if r.quant_pass:
            return ""
        a, b = [], []
        spec_a = [
            ("a_sharpe_full", f"full Sharpe {_fmt(r.full_sharpe)} < {A_SHARPE_FULL}"),
            ("a_sharpe_post", f"post Sharpe {_fmt(r.post_sharpe)} < {A_SHARPE_POST}"),
            ("a_maxdd_full", f"full maxDD {_fmt(r.full_maxdd)} > {A_MAXDD}"),
            ("a_trips_full", f"full round trips {r.full_round_trips} < {A_TRIPS_FULL}"),
            ("a_bh_full", f"BH p full {_fmt(r.p_bh_full, 4)} >= {A_P}"),
            ("a_bh_post", f"BH p post {_fmt(r.p_bh_post, 4)} >= {A_P}"),
            ("a_dsr_full", f"DSR full {_fmt(r.dsr_full)} < {A_DSR}"),
            ("a_coverage", f"coverage {_fmt(r.coverage)} < {A_COVERAGE}"),
            ("a_trips_post", f"post round trips {r.post_round_trips} < {A_TRIPS_POST}"),
        ]
        spec_b = [
            ("b_sharpe_post", f"post Sharpe {_fmt(r.post_sharpe)} < {B_SHARPE_POST}"),
            ("b_maxdd_post", f"post maxDD {_fmt(r.post_maxdd)} > {B_MAXDD}"),
            ("b_trips_post", f"post round trips {r.post_round_trips} < {B_TRIPS_POST}"),
            ("b_bh_post", f"BH p post {_fmt(r.p_bh_post, 4)} >= {B_P}"),
            ("b_dsr_post", f"DSR post {_fmt(r.dsr_post)} < {B_DSR}"),
        ]
        for col, msg in spec_a:
            if not getattr(r, col):
                a.append(msg)
        for col, msg in spec_b:
            if not getattr(r, col):
                b.append(msg)
        parts = []
        if a:
            parts.append("rule(a) fails: " + "; ".join(a))
        if b:
            parts.append("rule(b) fails: " + "; ".join(b))
        return " || ".join(parts)

    out["fail_reasons"] = [reasons(r) for r in out.itertuples()]
    out["n_gates_failed_a"] = (~out[a_cols]).sum(axis=1)
    out["n_gates_failed_b"] = (~out[b_cols]).sum(axis=1)
    return out
