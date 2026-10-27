"""summary.md and chart generation (spec section 11)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import charts, config


def _f(x, nd=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)) or pd.isna(x):
        return "n/a"
    if isinstance(x, (bool, np.bool_)):
        return "yes" if x else "no"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return f"{x:.{nd}f}"


def md_table(df: pd.DataFrame, fmt: dict | None = None, default_nd: int = 2) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            nd = fmt.get(c, default_nd)
            cells.append(_f(v, nd) if not isinstance(v, str) else v)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def rank_by_dsr(g: pd.DataFrame) -> pd.DataFrame:
    out = g.copy()
    out["dsr_best"] = out[["dsr_full", "dsr_post"]].max(axis=1)
    out["n_failed_min"] = out[["n_gates_failed_a", "n_gates_failed_b"]].min(axis=1)
    return out.sort_values(["dsr_best", "full_sharpe"], ascending=[False, False], na_position="last")


def closest(g: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    out = g.copy()
    out["n_failed_min"] = out[["n_gates_failed_a", "n_gates_failed_b"]].min(axis=1)
    out["dsr_best"] = out[["dsr_full", "dsr_post"]].max(axis=1)
    return out.sort_values(["n_failed_min", "dsr_best"], ascending=[True, False], na_position="last").head(k)


def write_summary(path, *, candidates, excluded, pool, gates, family, base_summary, base_runs, buyhold, qa,
                  screen, spy_stats, n_trials, dsr_info) -> None:
    L: list[str] = []
    A = L.append
    A("# Quant pipeline summary")
    A("")
    A(f"Snapshot: Yahoo Finance daily bars through {config.SNAPSHOT_END} (frozen cache, see `data/MANIFEST.json`). "
      "All numbers below were produced by `python -m backtest.run_all`; nothing is hand-typed. "
      "Research only: no brokerage, no real trades.")
    A("")
    # ------------------------------------------------------------------ funnel
    n_scouted = len(candidates)
    n_data_ok = n_scouted - int((excluded["stage"] == "data").sum())
    n_screened = len(pool)
    n_pass = int(gates["quant_pass"].sum())
    n_a, n_b = int(gates["pass_a"].sum()), int(gates["pass_b"].sum())
    A("## Funnel")
    A("")
    A(md_table(pd.DataFrame([
        {"stage": "pairs scouted (candidates.csv)", "count": n_scouted},
        {"stage": "pairs with usable data (both legs present, no unresolved QA error)", "count": n_data_ok},
        {"stage": "pairs screened in (liquidity > $20M both medians, rule-(b) history)", "count": n_screened},
        {"stage": "(pair, rule) trials tested  (= N for the DSR)", "count": n_trials},
        {"stage": "quant_pass = rule (a) OR rule (b)", "count": n_pass},
        {"stage": "   of which rule (a)", "count": n_a},
        {"stage": "   of which rule (b)", "count": n_b},
        {"stage": "   rule (b) only (needs_regime_change_explanation)", "count": int(gates["needs_regime_change_explanation"].sum())},
    ])))
    A("")
    tick = screen
    A(f"Tickers: {int((tick['rows'] > 0).sum())} downloaded of {len(tick)} requested "
      f"({int(tick['data_ok'].sum())} pass data QA, {int(tick['liq_pass'].sum())} pass liquidity, "
      f"{int(tick['rule_b_eligible'].sum())} have rule-(b) history).")
    A("")
    if n_pass == 0:
        A("**No (pair, rule) row passed the pre-registered gates.** Thresholds were not relaxed.")
        A("")
    # ------------------------------------------------------------------ exclusions
    A("## Excluded pairs")
    A("")
    ex = excluded[["pair_id", "stage", "reason"]].copy()
    A(md_table(ex))
    A("")
    # ------------------------------------------------------------------ per-rule counts
    A("## Per-rule counts")
    A("")
    rows = []
    for rule, g in gates.groupby("rule"):
        rows.append({"rule": rule, "trials": len(g),
                     "full Sharpe>=1.0": int(g["a_sharpe_full"].sum()), "post Sharpe>=0.8": int(g["a_sharpe_post"].sum()),
                     "post Sharpe>=1.0": int(g["b_sharpe_post"].sum()),
                     "full maxDD<=20%": int(g["a_maxdd_full"].sum()), "trips>=20": int(g["a_trips_full"].sum()),
                     "BH p<.05 full": int(g["a_bh_full"].sum()), "BH p<.05 post": int(g["a_bh_post"].sum()),
                     "DSR full>=.95": int(g["a_dsr_full"].sum()), "DSR post>=.95": int(g["b_dsr_post"].sum()),
                     "pass (a)": int(g["pass_a"].sum()), "pass (b)": int(g["pass_b"].sum()),
                     "pre-only": int(g["pre_only"].sum())})
    A(md_table(pd.DataFrame(rows)))
    A("")
    # ------------------------------------------------------------------ multiple testing
    A("## Multiple testing")
    A("")
    fam_n = int(family["family_size"].iloc[0]) if len(family) else 0
    A(f"Relationship family: {fam_n} primary p-values (pair x test type x window in {{full, post}}); "
      f"Benjamini-Hochberg at q = {config.FDR_Q} rejects {int(family['bh_reject_q05'].sum())}; "
      f"Bonferroni (alpha {config.FDR_Q}) rejects {int((family['p_bonf'] < config.FDR_Q).sum())}.")
    byt = family.groupby(["test", "window"]).agg(n=("p_raw", "size"), raw_lt_05=("p_raw", lambda s: int((s < 0.05).sum())),
                                                  bh_reject=("bh_reject_q05", "sum")).reset_index()
    A("")
    A(md_table(byt))
    A("")
    A(f"Deflated Sharpe: N = {dsr_info['N']} trials; V(full) = {dsr_info['V_full']:.3e}, "
      f"V(post) = {dsr_info['V_post']:.3e} (variance of per-day Sharpe across trials); "
      f"SR0 annualised: full {dsr_info['sr0_full_ann']:.2f}, post {dsr_info['sr0_post_ann']:.2f}.")
    A("")
    # ------------------------------------------------------------------ top 25
    ranked = rank_by_dsr(gates)
    A("## Top 25 (pair, rule) rows by DSR (max of DSR_full, DSR_post)")
    A("")
    top = ranked.head(25)
    tcols = {"pair_id": "pair", "rule": "rule", "full_sharpe": "SR full", "post_sharpe": "SR post", "pre_sharpe": "SR pre",
             "full_maxdd": "maxDD full", "post_maxdd": "maxDD post", "full_round_trips": "RT full",
             "post_round_trips": "RT post", "p_bh_full": "BH p full", "p_bh_post": "BH p post", "dsr_full": "DSR full",
             "dsr_post": "DSR post", "coverage": "cover", "n_gates_failed_a": "fail(a)", "n_gates_failed_b": "fail(b)",
             "quant_pass": "pass"}
    t = top[list(tcols)].rename(columns=tcols)
    A(md_table(t, {"BH p full": 4, "BH p post": 4, "DSR full": 3, "DSR post": 3}))
    A("")
    A("Gate values for the top 10 (why they fail):")
    A("")
    for r in ranked.head(10).itertuples():
        A(f"- **{r.pair_id} / {r.rule}**: {r.fail_reasons or 'passes'}")
    A("")
    # ------------------------------------------------------------------ closest
    A("## Closest to passing")
    A("")
    A("Ranked by fewest failed gates under the better of rules (a)/(b), ties broken by DSR. Gate counts can flatter a "
      "row with a negative Sharpe that happens to clear the drawdown, trade-count and p-value gates, so read this "
      "together with the DSR ranking above.")
    A("")
    cl = closest(gates, 5)
    for r in cl.itertuples():
        A(f"- **{r.pair_id} / {r.rule}** (rule (a) fails {r.n_gates_failed_a} gates, rule (b) fails {r.n_gates_failed_b}): "
          f"{r.fail_reasons or 'passes'}")
    A("")
    if n_pass:
        A("## quant_pass rows")
        A("")
        qp = gates[gates["quant_pass"]]
        A(md_table(qp[list(tcols)].rename(columns=tcols), {"BH p full": 4, "BH p post": 4, "DSR full": 3, "DSR post": 3}))
        A("")
    # ------------------------------------------------------------------ baseline
    A("## Random-pair baseline")
    A("")
    n_pairs = base_runs["pair_id"].nunique()
    A(f"{n_pairs} random pairs (seed {config.SEED}) from tickers that pass data QA, liquidity and rule-(b) history, "
      "excluding the candidate pairs; each run with the same engine, costs and walk-forward grid. "
      "Percentile = share of baseline Sharpe ratios at or below the candidate's, for the same rule "
      "(baseline exists for coint_ols and rotation only).")
    A("")
    A(md_table(base_summary, {"frac_ge_1": 3, "frac_ge_0p8": 3}))
    A("")
    A("Baseline percentile of the top-10 rows (where a baseline exists):")
    A("")
    pc = ranked.head(10)[["pair_id", "rule", "full_sharpe", "full_sharpe_baseline_pctile", "post_sharpe",
                          "post_sharpe_baseline_pctile"]]
    A(md_table(pc, {"full_sharpe_baseline_pctile": 1, "post_sharpe_baseline_pctile": 1}))
    A("")
    # ------------------------------------------------------------------ benchmarks
    A("## Buy-and-hold reference")
    A("")
    A(f"SPY total-return buy-and-hold over {config.REGIMES['full'][0]} -> {config.REGIMES['full'][1]}: "
      f"CAGR {spy_stats['cagr']:.2%}, Sharpe {spy_stats['sharpe']:.2f}, max drawdown {spy_stats['maxdd']:.1%}. "
      "Per-pair leg and SPY buy-and-hold figures are in `baseline_buyhold.csv`.")
    A("")
    # ------------------------------------------------------------------ data caveats
    A("## Data and implementation caveats")
    A("")
    err = qa[qa["severity"] == "error"]
    warn = qa[(qa["severity"] == "warning")]
    A(f"- QA: {len(err)} unresolved error row(s) ({', '.join(sorted(err['ticker'].unique())) or 'none'}); "
      f"{len(warn)} warning row(s); see `data_qa.csv`.")
    A("- Survivorship bias: the universe is built from tickers that still trade; the random baseline carries the same bias.")
    A("- See `IMPLEMENTATION_NOTES.md` for every deviation and judgement call, and `sanity_checks.md` for the "
      "auto-generated cross-checks.")
    A("")
    path.write_text("\n".join(L))


def make_charts(gates: pd.DataFrame, panel: dict, trials_dir, charts_dir, n_top: int = 10) -> list[str]:
    ranked = rank_by_dsr(gates)
    sel = list(ranked.head(n_top).index) + [i for i in gates.index[gates["quant_pass"]] if i not in ranked.head(n_top).index]
    spy_ret = panel["adjclose"]["SPY"].pct_change()
    made = []
    charts_dir.mkdir(parents=True, exist_ok=True)
    for old in charts_dir.glob("*.png"):
        old.unlink()
    for i in sel:
        r = gates.loc[i]
        k = f"{r['pair_id']}__{r['rule']}"
        daily = pd.read_csv(trials_dir / f"{k}.csv.gz", index_col=0, parse_dates=True)
        trades = pd.read_csv(trials_dir / f"{k}_trades.csv", parse_dates=["entry_date", "exit_date"])
        lr = np.log(panel["adjclose"][r["leg_a"]]) - np.log(panel["adjclose"][r["leg_b"]])
        charts.equity_chart(daily, spy_ret, r["pair_id"], r["rule"], charts_dir / f"{k}__equity.png")
        charts.spread_z_chart(daily, trades, lr, r["pair_id"], r["rule"], charts_dir / f"{k}__spread_z.png")
        made += [f"{k}__equity.png", f"{k}__spread_z.png"]
    return made
