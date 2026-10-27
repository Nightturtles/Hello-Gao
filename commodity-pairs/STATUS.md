# Status

_Last updated: 2026-10-27_

| Phase | Status |
|---|---|
| 0. Project setup (venv, pinned requirements, layout) | ✅ done |
| 1. Scouting (6 commodity groups) | ✅ done: 67 candidate pairs (`research/candidates.csv`) |
| 2–3. Data, universe screen, statistical tests, walk-forward backtest | ✅ done: 223 trials, **0 passed** (`backtest/results/summary.md`) |
| 4. Pick selection (red team + council) | ⛔ not reached: no candidate cleared the quantitative gates |
| 5. Paper-trading simulator | ⏸ waiting on the owner's decision (no picks to trade) |
| 6. Scheduling (GitHub Actions + launchd backup) | ⏸ files drafted; activation waits on step 5 |
| 7. Research report | ✅ `reports/final_research_report.md` |

## Picks approved
**None.** No (pair, rule) combination met the pre-registered bar:
- out-of-sample Sharpe ≥ 1.0 net of costs, and ≥ 0.8 post-COVID;
- max drawdown ≤ 20%;
- ≥ 20 round trips;
- significance after multiple-testing correction, including a deflated Sharpe ratio ≥ 0.95.

The bar was not lowered. The best full-period Sharpe was 0.72, and the best before costs was 0.86.

## Notes
- This is research and paper trading only. No brokerage connection exists, and no real orders are placed.
- An engine fix (maintenance-margin liquidation and ruin handling) was made after the first run. It is disclosed in `research/DECISIONS.md`. The outcome was the same before and after: 0 of 223 passed.
