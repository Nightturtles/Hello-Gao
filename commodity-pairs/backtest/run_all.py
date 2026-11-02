"""Single entry point:  .venv/bin/python -m backtest.run_all

screen -> stats -> backtests -> baseline -> multiple testing -> gates -> summary -> charts.
Reads only the frozen cache in data/cache (never the network)."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import warnings

import numpy as np
import pandas as pd

from . import (audit, baseline, config, data, gates as gates_mod, metrics, multiple_testing, report, runner, screen,
               stats_tests, strategies)
from .trading_calendar import sessions, walk_forward_grid

FLOAT_FMT = "%.10g"
RULE_ORDER = ["coint_ols", "coint_kalman", "rotation", "leadlag", "leadlag_rev"]


def _t(msg: str, t0: float) -> None:
    print(f"[{time.time() - t0:7.1f}s] {msg}", flush=True)


def build_tasks(pool: pd.DataFrame) -> list[dict]:
    tasks = []
    for r in pool.itertuples():
        rules = ["coint_ols", "coint_kalman", "rotation", "leadlag"]
        if r.type == "leadlag":
            rules.append("leadlag_rev")
        for rule in rules:
            tasks.append({"idx": len(tasks), "pair_id": r.pair_id, "leg_a": r.leg_a, "leg_b": r.leg_b, "rule": rule,
                          "save": True, "bootstrap": True})
    return tasks


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--processes", type=int, default=None)
    ap.add_argument("--n-random-pairs", type=int, default=config.N_RANDOM_PAIRS)
    args = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    t0 = time.time()
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    config.TRIALS_DIR.mkdir(parents=True, exist_ok=True)
    for old in list(config.TRIALS_DIR.glob("*")):
        old.unlink()

    # ------------------------------------------------------------------ data + QA
    probs = data.verify_manifest()
    if probs:
        raise SystemExit("cache does not match MANIFEST.json:\n" + "\n".join(probs))
    sess = sessions()
    windows = walk_forward_grid(sess)
    cands = data.candidate_pairs()
    frames, missing = data.load_all(data.all_tickers())
    panel = data.build_panel(frames, sess)
    qa = data.run_qa(frames, missing, sess, windows)
    qa.to_csv(config.RESULTS_DIR / "data_qa.csv", index=False)
    qa_err = data.unresolved_errors(qa)
    _t(f"data: {len(frames)} tickers loaded, {len(missing)} missing, QA errors on {sorted(qa_err)}", t0)

    # ------------------------------------------------------------------ screen
    sc = screen.run_screen(frames, missing, qa_err, panel, sess, windows)
    sc.to_csv(config.SCREEN_PATH, index=False, float_format=FLOAT_FMT)
    pool, excluded = screen.select_pool(cands, sc, panel, sess, windows)
    excluded.to_csv(config.RESULTS_DIR / "excluded_pairs.csv", index=False)
    pool.to_csv(config.RESULTS_DIR / "tested_pairs.csv", index=False)
    _t(f"screen: {len(pool)} pairs in pool, {len(excluded)} excluded", t0)

    # ------------------------------------------------------------------ stats
    stats = stats_tests.run_stats(pool, panel)
    stats.to_csv(config.RESULTS_DIR / "stats_tests.csv", index=False, float_format=FLOAT_FMT)
    _t(f"stats: {len(stats)} pair x regime rows", t0)

    # ------------------------------------------------------------------ trials
    spy_ret = panel["adjclose"]["SPY"].pct_change()
    s_full, e_full = config.REGIMES["full"]
    full_days = int(((sess >= pd.Timestamp(s_full)) & (sess <= pd.Timestamp(e_full))).sum())
    runner.set_context(panel, sc, windows, spy_ret, full_days, config.TRIALS_DIR)
    tasks = build_tasks(pool)
    res = runner.run_tasks(tasks, args.processes)
    trials = pd.DataFrame([m for m, _ in res])
    wl = pd.DataFrame([row for _, w in res for row in w])
    wl.to_csv(config.RESULTS_DIR / "trials_windows.csv.gz", index=False, float_format=FLOAT_FMT,
              compression={"method": "gzip", "mtime": 0})
    meta = pool.set_index("pair_id")
    trials["group"] = trials["pair_id"].map(meta["group"])
    trials["pair_type"] = trials["pair_id"].map(meta["type"])
    trials["expected_corr_sign"] = trials["pair_id"].map(meta["expected_corr_sign"])
    trials["rule_a_eligible"] = trials["pair_id"].map(meta["rule_a_eligible"])
    _t(f"trials: {len(trials)} (pair, rule) runs", t0)

    # ------------------------------------------------------------------ baseline
    rng = np.random.default_rng(config.SEED)
    base = baseline.run_baseline(sc, cands, panel, sess, windows, spy_ret, full_days, rng, args.n_random_pairs,
                                 args.processes)
    base.to_csv(config.RESULTS_DIR / "baseline.csv", index=False, float_format=FLOAT_FMT)
    bsum = baseline.baseline_summary(base)
    bsum.to_csv(config.RESULTS_DIR / "baseline_summary.csv", index=False, float_format=FLOAT_FMT)
    first_oos = dict(zip(trials["pair_id"], trials["first_oos_day"]))
    bh = baseline.buy_and_hold(panel, pool, first_oos)
    bh.to_csv(config.RESULTS_DIR / "baseline_buyhold.csv", index=False, float_format=FLOAT_FMT)
    trials = baseline.add_baseline_percentiles(trials, base)
    _t(f"baseline: {len(base)} runs on {base['pair_id'].nunique()} random pairs", t0)

    # ------------------------------------------------------------------ multiple testing
    family = multiple_testing.build_family(stats, pool)
    family.to_csv(config.RESULTS_DIR / "mt_family.csv", index=False, float_format=FLOAT_FMT)
    trials = multiple_testing.add_dsr(trials)
    trials = gates_mod.attach_primary_p(trials, family)
    _t(f"multiple testing: family of {int(family['family_size'].iloc[0])} p-values", t0)

    # ------------------------------------------------------------------ gates
    trials["rule"] = pd.Categorical(trials["rule"], RULE_ORDER, ordered=True)
    trials = trials.sort_values(["pair_id", "rule"]).reset_index(drop=True)
    trials["rule"] = trials["rule"].astype(str)
    g = gates_mod.apply_gates(trials)
    g.to_csv(config.RESULTS_DIR / "trials_metrics.csv", index=False, float_format=FLOAT_FMT)
    gate_cols = ["pair_id", "leg_a", "leg_b", "pair_type", "group", "rule", "primary_test",
                 "p_raw_full", "p_raw_post", "p_bh_full", "p_bh_post", "p_bonf_full", "p_bonf_post",
                 "full_sharpe", "post_sharpe", "pre_sharpe", "covid_sharpe", "full_sharpe_ci_lo", "full_sharpe_ci_hi",
                 "post_sharpe_ci_lo", "post_sharpe_ci_hi", "full_cagr", "post_cagr", "full_maxdd", "post_maxdd",
                 "full_round_trips", "post_round_trips", "full_win_rate", "coverage", "first_oos_day",
                 "dsr_full", "dsr_post", "psr_full", "psr_post", "dsr_N_full", "dsr_V_full", "sr0_full_ann",
                 "dsr_V_post", "sr0_post_ann", "full_sharpe_baseline_pctile", "post_sharpe_baseline_pctile",
                 "a_sharpe_full", "a_sharpe_post", "a_maxdd_full", "a_trips_full", "a_bh_full", "a_bh_post",
                 "a_dsr_full", "a_coverage", "a_trips_post", "pass_a",
                 "b_sharpe_post", "b_maxdd_post", "b_trips_post", "b_bh_post", "b_dsr_post", "pass_b",
                 "quant_pass", "needs_regime_change_explanation", "pre_only", "n_gates_failed_a", "n_gates_failed_b",
                 "fail_reasons"]
    gates_path = config.RESULTS_DIR / "gates.csv"
    g[gate_cols].to_csv(gates_path, index=False, float_format=FLOAT_FMT)
    sha = hashlib.sha256(gates_path.read_bytes()).hexdigest()
    (config.RESULTS_DIR / "RESULTS_HASH.txt").write_text(f"sha256(backtest/results/gates.csv) = {sha}\nrows = {len(g)}\n")
    _t(f"gates: {int(g['quant_pass'].sum())} quant_pass of {len(g)}; hash {sha[:16]}", t0)

    # ------------------------------------------------------------------ report + charts + audit
    spy = spy_ret.loc[s_full:e_full].dropna().to_numpy()
    spy_stats = {"cagr": metrics.cagr(spy), "sharpe": metrics.sharpe(spy), "maxdd": metrics.max_drawdown(spy)}
    dsr_info = {"N": int(g["dsr_N_full"].iloc[0]), "V_full": float(g["dsr_V_full"].iloc[0]),
                "V_post": float(g["dsr_V_post"].iloc[0]), "sr0_full_ann": float(g["sr0_full_ann"].iloc[0]),
                "sr0_post_ann": float(g["sr0_post_ann"].iloc[0])}
    report.write_summary(config.RESULTS_DIR / "summary.md", candidates=cands, excluded=excluded, pool=pool, gates=g,
                         family=family, base_summary=bsum, base_runs=base, buyhold=bh, qa=qa, screen=sc,
                         spy_stats=spy_stats, n_trials=len(g), dsr_info=dsr_info)
    made = report.make_charts(g, panel, config.TRIALS_DIR, config.CHARTS_DIR)
    (config.RESULTS_DIR / "sanity_checks.md").write_text(
        audit.build_sanity_report(panel, sc, pool, config.TRIALS_DIR, spy_ret, g, wl))
    _t(f"report: summary.md, {len(made)} charts, sanity_checks.md", t0)
    print(json.dumps({"pairs_in_pool": len(pool), "trials": len(g), "quant_pass": int(g["quant_pass"].sum()),
                      "runtime_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
