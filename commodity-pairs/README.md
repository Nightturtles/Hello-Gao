# Commodity pair trades: research and paper-trading simulator

**Research and paper trading only.** Nothing here connects to a brokerage or places a real order.

## What this project found

The goal was to find 5 statistically robust, tradeable pair relationships among US-listed commodity stocks and ETFs. Each one had to clear an out-of-sample (OOS) backtest net of costs and then a red-team and council review.

- **Result: none passed.** Across two scouting rounds, 101 pairs were proposed, 82 survived the data and liquidity screens, and 336 (pair, rule) walk-forward trials were run. **0 cleared the pre-registered bar.**
- The best full-period Sharpe was 0.72 net of costs and 0.86 before costs, against a bar of 1.0 (about 1.8 after the deflated-Sharpe correction).
- The scouted pairs did no better than random pairs.
- The "42% in one semester" gold trade that started this project looks like luck plus leverage.

Full write-up: [`reports/final_research_report.md`](reports/final_research_report.md).

## The paper-trading simulator: a system check, not a strategy

You chose to paper-trade the **5 best near-misses** anyway, each one labeled **FAILED THE BAR**. Every simulator report opens with that warning.

- **The point:** confirm that the live pipeline behaves exactly as the backtest does: same signals, same next-open fills, same costs.
- **What one month can't tell you:** whether these pairs have an edge. One month is far too short to confirm or refute any strategy.
- **The near-misses:** NTR/DE spread, RRC/CRK rotation, SLV/SILJ lead-lag, YPF/VIST lead-lag, ET/EPD spread. They were selected by code in `sim/select_picks.py` and are listed in `research/near_miss_selection.md`.

**How it works:**
- Each pick runs as a separate **$100,000** sub-portfolio at 1x gross. Reports also show a combined view and a comparison with SPY.
- **Same rules as the backtest.** The simulator imports `backtest/strategies.py` unchanged, along with the same cost model and the same margin and ruin rule. Parameters are frozen in `sim/config.json` when the run is initialised.
- **Timing:** a signal from a session's close fills at the **next session's open**. Fills include slippage, commission and borrow fees.
- **Warm start:** the first run replays the real backtest engine on live data through the day before the start. The simulator therefore begins exactly where the backtest would be.
- **Idempotent:**
  - running it twice on the same day changes nothing;
  - weekends and NYSE holidays are skipped;
  - missed days are caught up in order.
- **Failures are never silent.** A data error leaves that pick un-advanced, is logged to `sim/state/errors.log`, is shown in the report, and makes the run exit non-zero, so GitHub emails you.

**Where the outputs go:**

| File | Contents |
|---|---|
| `reports/daily/YYYY-MM-DD.md` | Each session's report |
| `reports/summary.md` | Rolling summary |
| `reports/final_sim_report.md` | Side-by-side comparison, live vs backtest, and a parity check that re-runs the backtest over the live period and confirms identical positions |
| `sim/state/` | The simulator's state: `state.json`, `trades.csv`, `equity.csv`, `errors.log` |

**Current run:** started Monday **2026-11-02**, for one month (about 22 sessions).

### Commands

Run these from `commodity-pairs/` using the venv's Python.

```bash
python -m sim.run_daily                        # process any new sessions (this is what the scheduler runs)
python -m sim.ctl status                       # where the simulation stands
python -m sim.ctl stop                         # stop now and write the final report
python -m sim.ctl extend --days 10             # extend by 10 sessions (or: --until 2026-12-31)
python -m sim.ctl report                       # write the final comparison report now, without stopping
python -m sim.ctl check-data                   # fetch the latest bars for every leg and SPY (changes nothing)
python -m sim.ctl init --start 2026-11-02 --months 1 --force   # restart from scratch (replaces the current run)
```

The same commands are available from GitHub. Go to **Actions → paper-sim → Run workflow** and pick a command:

| Command | What to put in `arg` |
|---|---|
| `run`, `status`, `stop`, `report`, `check` | Nothing |
| `extend` | `--days N` or `--until YYYY-MM-DD` |
| `init` | `--start YYYY-MM-DD` |

## Scheduling

You chose both schedulers: GitHub Actions as the main one and a Mac launchd job as the backup. **Enable only one at a time.** Both pull first and the simulator is idempotent, so an accidental double run changes nothing, but one scheduler is cleaner.

**GitHub Actions (the main scheduler):** `.github/workflows/paper-sim.yml` at the repo root.
- **When it runs:** cron `30 21 * * 1-5`, which is 21:30 UTC on weekdays: 1:30pm Pacific in winter, 2:30pm while daylight saving is in effect. GitHub often starts scheduled runs a few minutes late, sometimes later; that is harmless.
- **What it does:** installs `requirements.txt` on Python 3.13, runs `python -m sim.run_daily`, then commits `sim/state`, `sim/config.json` and `reports/` back to `master`. It commits even when the run failed, so failure reports are visible.
- **Branch:** scheduled workflows only fire from the default branch, `master`. Merging the PR activates it.
- **Strengths:** runs while your laptop is asleep, keeps a full history of runs, and GitHub emails you on failures.
- **Weaknesses:**
  - Yahoo Finance sometimes throttles GitHub's servers. The run then fails, you get an email, and the next run catches up.
  - The repo is **public**, so the reports are too.
- **To pause:** Actions → paper-sim → "…" → Disable workflow.

**Mac launchd (the backup):** `sim/scheduling/`.
- **Install:** from your clone, run `bash commodity-pairs/sim/scheduling/install_launchd.sh`. Disable the GitHub workflow first.
- **When it runs:** 1:35pm local time, Monday to Friday. If the Mac is asleep, the job runs when it wakes. It does not run while the Mac is shut down.
- **What it does:** `git pull`, then `run_daily`, then commits and pushes to `master`.
- **Logs:** `~/Library/Logs/commodity-pairs/`.
- **Remove:** `bash commodity-pairs/sim/scheduling/uninstall_launchd.sh`.
- **Strengths:** uses your home internet connection, which Yahoo throttles less.
- **Weaknesses:** only runs while the Mac is on.

## Reproduce the research

```bash
cd commodity-pairs
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                  # the full test suite
.venv/bin/python -m backtest.run_all           # about 2 minutes; reads only the frozen price cache in data/cache/
.venv/bin/python -m backtest.semester_check    # the 42% semester analysis
```

## Layout

| Path | Contents |
|---|---|
| `research/` | Methodology (`DECISIONS.md`, `QUANT_SPEC.md`, `SIM_SPEC.md`, `REVIEW_PROTOCOL.md`), scout notes, candidate list, universe screen |
| `data/` | Frozen Yahoo Finance price snapshot (Oct 2014 → 2026-10-26), plus `MANIFEST.json` with checksums |
| `backtest/` | Engine, statistics, multiple-testing corrections, gates, baseline, charts; results in `backtest/results/` |
| `sim/` | Paper-trading simulator, frozen picks, state, schedulers |
| `reports/` | The research report, plus the simulator's daily, summary and final reports |
| `tests/` | pytest suite: look-ahead, cost accounting, determinism, account risk, simulator behaviour |

## Caveats

- **Survivorship bias.** The data source is free, and the universe is built from tickers that still trade.
- **Daily bars only.** No futures and no intraday data were used.
- **Parameters were fixed before any results were seen,** to avoid overfitting.
- **Expect large swings.** RRC/CRK rotation had a 76% drawdown in the backtest.
