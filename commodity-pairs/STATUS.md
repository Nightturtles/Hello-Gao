# Status

_Last updated: 2026-10-28_

| Phase | Status |
|---|---|
| 0. Project setup (venv, pinned requirements, layout) | ✅ done |
| 1. Scouting, round 1 (6 commodity groups) | ✅ 67 pairs |
| 1b. Scouting, round 2 (4 structure scouts), the final round | ✅ 34 pairs |
| 2–3. Data, screens, statistical tests, walk-forward backtest | ✅ 82 tradable pairs, 336 trials, **0 passed** (`backtest/results/summary.md`) |
| 4. Pick selection (red team + council) | ⛔ not reached: no candidate cleared the quantitative gates |
| 5. Paper-trading simulator | ⏸ waiting on the owner's decision (no picks to trade) |
| 6. Scheduling (GitHub Actions + launchd backup) | ⏸ files drafted; activation waits on step 5 |
| 7. Research report | ✅ `reports/final_research_report.md` |

## Picks approved
**None.** No (pair, rule) combination in either round met the pre-registered bar:
- out-of-sample Sharpe ≥ 1.0 net of costs, and ≥ 0.8 post-COVID;
- max drawdown ≤ 20%;
- ≥ 20 round trips;
- significance after multiple-testing correction, including a deflated Sharpe ratio ≥ 0.95.

The bar was not lowered. The best full-period Sharpe was 0.72, and the best before costs was 0.86.

## Notes
- This is research and paper trading only. No brokerage connection exists, and no real orders are placed.
- Two post-audit fixes, both applied uniformly with neither changing the outcome, are disclosed in `research/DECISIONS.md`:
  - margin and ruin handling;
  - the security-splice data check.
