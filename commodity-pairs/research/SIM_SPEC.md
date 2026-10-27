# Paper-trading simulator: specification

A self-contained Python paper-trading simulator for the approved picks. It never connects to a broker; every fill is simulated.

## Principles
1. **Same rules as the backtest, by construction.**
   - The simulator imports `backtest.strategies` (`fit`, `step`) and the cost parameters exactly as the backtest uses them.
   - Rule parameters are frozen in `sim/picks.json` when the simulation is initialized and never change while it is live.
2. **Same timing as the backtest.**
   - A signal from day d's close fills at the next session's **open**.
   - Order size = equity at d's close × target weight ÷ the fill-day open price.
   - Shares are held constant until the signal changes; there is no daily rebalancing.
   - Refits follow the backtest's global walk-forward grid: every 63 NYSE sessions starting 2016-10-03, each fitted on the 504 sessions before the grid date.
3. **Idempotent and resumable.**
   - State is saved after each processed day.
   - A second run on the same day changes nothing, not even rewriting reports.
   - Missed sessions are caught up in order.
4. **Failures are never silent.**
   - Missing data for a pick leaves that pick un-advanced.
   - The failure is logged and shown in the report.
   - The run exits non-zero.

## Files
```
sim/__init__.py
sim/data.py         # providers: YahooProvider (live), CacheProvider (reads data/cache, used by tests and dry runs)
sim/engine.py       # per-pick daily processing
sim/reports.py      # daily, summary and final reports
sim/run_daily.py    # entry point: python -m sim.run_daily [--asof YYYY-MM-DD] [--provider yahoo|cache] [--state-dir DIR]
sim/ctl.py          # python -m sim.ctl {init,status,stop,extend,report}
sim/picks.json      # frozen pick definitions (written by the lead researcher)
sim/config.json     # run config (written by ctl init)
sim/state/state.json, trades.csv, equity.csv, errors.log
reports/daily/YYYY-MM-DD.md, reports/summary.md, reports/final_sim_report.md
```

## `sim/picks.json` (input, written by the lead researcher)
```json
{"picks": [{"pick_id": "pick_1", "pair_id": "GLD_GDX", "leg_a": "GLD", "leg_b": "GDX", "rule": "coint_ols",
            "params": {...exactly the backtest params...},
            "slippage_bps": {"GLD": 5, "GDX": 5}, "borrow_rate": {"GLD": 0.005, "GDX": 0.005},
            "backtest_daily_returns_path": "backtest/results/trials/<file>",
            "backtest_trades_path": "backtest/results/trials/<file>"}]}
```

## Prices
- **Signals and fits** use **adjusted closes**, the same series the backtest uses.
- **Fills and mark-to-market** use **raw** open and close prices: the prices you would actually have traded at.
- **Dividends:** on the ex-date, long positions are credited shares × dividend, and short positions are debited the same amount.
- **Splits:** share counts are multiplied by the split ratio on the split date.
- **Costs are identical to the backtest:**
  - slippage tier per leg, applied to the open price;
  - commission $0.005/share with a $1 minimum;
  - borrow fee = short notional at close × rate / 252, every session.
- **Each run fetches** about 650 sessions of history for each leg plus SPY, enough for the 504-day fit plus the 60-day z-score window. SPY is fetched for the report comparison.

## `ctl init --start YYYY-MM-DD [--months 1 | --end YYYY-MM-DD] [--force]`
- `--start` must be an NYSE session. The default end is start + 1 calendar month, snapped to the last session on or before that date.
- Refuses to run if state already exists, unless `--force` is given.
- **Warm start (sync with the backtest):** for each pick, replay `fit`/`step` from two grid windows before the start date up to the session before start, using the walk-forward grid's fits. This gives the strategy state on the day before start: armed or disarmed, and any open trade with its entry β.
  - If the replayed state holds an open position, the simulator opens that position at the **start-date open**, logged with reason `sync: position carried from backtest replay (entered <date>)`.
  - This way the live run continues exactly where the backtest would be, instead of starting artificially flat.
  - The replay is written to `sim/state/warmup_<pick>.csv` for audit.
- **Capital:** $100,000 per pick.

## `run_daily`: one run
1. Load the config and state. If the status is not `running`, print the status and exit 0 without changing anything.
2. **Sessions to process:** the NYSE sessions (`exchange_calendars` XNYS) with `last_processed < d ≤ min(asof, end_date)`.
   - `asof` defaults to today in America/New_York.
   - If d is today and it is before 16:30 New York time, today is not processed yet because the close isn't final.
3. **For each pick, for each session d in order:**
   1. Fill pending orders at d's raw open, apply slippage and commission, and append to `trades.csv`. Each row has: timestamp (UTC run time), session date, pick, ticker, side, shares, price, slippage, commission, reason, and the signal date.
   2. Apply that day's splits and dividends.
   3. Mark positions to market at d's raw close and accrue the borrow fee.
   4. If d is a grid date, refit using the 504 sessions before d, and log the new β.
   5. Call `step()` with the adjusted close history up to d to get target weights and a reason.
   6. If the target differs from the current position, queue an order for the next open: target notional = equity at close × weight.
   7. Append to `equity.csv`: date, pick, equity, cash, positions, z or signal value, β, drawdown.
   8. Set `last_processed_date = d`, then **save the state atomically** (write a temp file, then rename).
4. **Missing data:** if a leg's bar for d is missing or the data fetch fails, stop that pick at d−1. Write a timestamped line to `errors.log` and add it to the run's issue list. Other picks continue.
5. **Reports:**
   - One daily report per newly processed session.
   - Regenerate `reports/summary.md` **only if** something new was processed or a new error occurred.
6. **End of run:**
   - When `end_date` has been processed, set the status to `finished` and write the final report.
   - Exit code 0 if there were no issues, 1 if any data issue occurred. Reports are still written in that case.

## Daily report: `reports/daily/YYYY-MM-DD.md`
- **Header:** session date and run timestamp.
- **Table, one row per pick plus a combined row** ($500k across the 5 sub-portfolios). Columns:
  - equity;
  - day P&L in $ and %;
  - cumulative P&L % since start;
  - drawdown from the high-water mark;
  - position per leg (shares and $ notional, long or short);
  - current z-score or signal value;
  - state (flat, long spread, short spread, …);
  - order queued for the next open.
- **SPY comparison:** SPY's return since sim start and on the day, against the combined result.
- **Trades filled today**, with reasons.
- **Data issues:** a list of problems, or the text "none".

## `reports/summary.md` (rolling)
- Current status and the start and end dates.
- Latest per-pick table: cumulative return, max drawdown, number of trades, current state.
- Combined result vs SPY.
- A table of daily combined equity.
- A link to the latest daily report.

## `ctl` commands
| Command | What it does |
|---|---|
| `status` | Prints the state summary. |
| `stop` | Sets the status to `stopped` and writes the final report. |
| `extend --days N` | Adds N sessions to the end date. If the status is `finished`, sets it back to `running`. |
| `extend --until DATE` | Moves the end date to DATE, with the same `finished` → `running` rule. |
| `report` | Writes `reports/final_sim_report.md` now, without stopping. |

## Final report: `reports/final_sim_report.md`
- **Side by side for all picks:**
  - live return and live annualized volatility;
  - max drawdown, number of trades, and exposure;
  - estimated exit cost for any open positions;
  - P&L vs SPY.
- **Live vs backtest expectations**, for each pick:
  - the percentile of the live period return among all rolling windows of the same length in the backtest's out-of-sample (OOS) daily returns, measured both post-COVID and over the full period;
  - the expected number of trades per month (backtest) vs the actual count;
  - the backtest's mean and standard deviation of monthly return.
- **Parity check:** re-run the backtest engine (`backtest.walkforward`) over the live period, on the same data, from the same warm-start state. Compare the daily target or position sign series with the simulator's, and report the matches and mismatches with dates. This is the main test that the system behaves as backtested.
- **Required statement, in plain words:** one month of live results is far too short to confirm or refute a strategy. The live run checks that the system behaves as backtested; it is not evidence of an edge.

## Tests: `tests/test_sim_*.py`
These use the cache provider, so they need no network.
1. **Idempotency:** run twice with the same `asof`, and the state files and reports are byte-identical.
2. **Weekend and holiday skipping:** an `asof` on a Saturday, or on a holiday such as 2026-07-03, processes nothing new.
3. **Catch-up:** run with asof = d1, then asof = d1 + 3 sessions; the result equals a single run straight to d1 + 3.
4. **Missing data:** when the provider drops a bar for one leg, that pick does not advance, the error is logged, the exit code is 1, and other picks advance normally.
5. **Next-open fill:** a signal on d fills at d+1's open with the correct slippage, commission and share count.
6. **Parity:** a historical dry run (for example, picks over 2026-08-03 → 2026-10-23 using the cache) produces the same position-sign series as the backtest trial file for the same dates.
7. **Controls:** `stop`, `extend` and `report` behave as specified.
