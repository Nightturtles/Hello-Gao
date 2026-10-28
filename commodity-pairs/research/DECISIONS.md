# Key decisions and why

All of these were fixed **before any backtest results were seen**, so none of them could be tuned to make a pair pass.

## Process
- **Scout and test the whole candidate pool once, then select picks one at a time** (confirmed by the owner). Every pair that is tested joins one multiple-testing family. Re-scouting before each pick would grow that family invisibly and make the corrections dishonest. Red-team and council still run separately for each pick.
- **Pass criteria are taken exactly as specified and never relaxed.** If fewer than 5 pairs pass, the report says so.

## Data
- **Source:** Yahoo Finance via `yfinance` (v8 chart API). It is free and was verified reachable from this environment. Stooq was blocked.
- **Download window: Oct 2014 → present.** Oct 2014–Oct 2016 is used *only* as the first 2-year training window. That way, out-of-sample (OOS) trading covers the whole Oct 2016 → present period that was requested.
- **Frozen snapshot committed to the repo** (`data/cache/`). Yahoo rewrites adjusted-close history after every dividend, so re-downloading would silently change results. Reruns read only the cache.
- **Adjusted open = raw open × (adjclose / close).** Signals use day t's close and fill at day t+1's adjusted open, which matches the live simulator.
- **Survivorship bias is unavoidable** with a free source, because the universe is built from tickers that still trade today. Mitigations:
  - Merged and delisted names are listed in the report.
  - ETFs are preferred.
  - The random-pair baseline is drawn from the same survivor universe, so it carries the same bias.

## Walk-forward
- **Train 504 trading days (about 2 years), trade the next 63 days (about 1 quarter), roll forward a quarter.** Two years is long enough to estimate a hedge ratio reliably. One quarter keeps the hedge ratio fresh without refitting constantly.
- All fitted quantities come from the training window only: hedge ratio β, lead-lag lag k, and any other estimate.

## Trading rules: one per relationship type, with global parameters
- **Cointegrated spread:**
  - spread s = ln A − β ln B, with β from OLS on the training window;
  - z-score of the spread over a rolling 60-day window;
  - enter at |z| ≥ 2.0, exit when z crosses 0, stop out at |z| ≥ 3.5, re-arm only after |z| falls back below 2;
  - β is frozen for the life of each trade.
  - A Kalman-filter β version runs as a robustness variant, and it counts as an extra trial in the deflated Sharpe ratio.
- **Inverse / rotation:**
  - long the leg with the higher 20-day return, short the other, and flip when the ranking changes;
  - this is honestly a directional rotation bet, not a hedge.
- **Lead-lag:**
  - lag k (1–10 days) is picked on the training window;
  - trade when the leader's k-day return z-score is ≥ 1;
  - the position is β-hedged in the follower, held k days.
- **Why global parameters:** per-pair tuning is the main way pairs backtests overfit. Fixed textbook parameters give up some in-sample fit in exchange for honest OOS numbers.

## Sizing and costs
- **1x gross** (confirmed by the owner): while a pair is in a trade, long plus short notional equals 100% of sub-portfolio equity, split by hedge ratio. Idle cash earns 0% (conservative).
- **Commission:** $0.005/share, $1 minimum.
- **Slippage:** 5 bps per side for ETFs and mega-caps, 10 bps for other names.
- **Borrow fee:** 0.5%/yr general collateral; 3%/yr for names flagged hard-to-borrow. Charged daily on short notional.
- **Short dividends** are captured automatically because the backtest uses total-return (adjusted) prices.

## Statistics and multiple testing
- **Primary p-value per relationship type:**
  - spread pairs: Engle-Granger;
  - lead-lag pairs: Granger;
  - inverse pairs: a correlation test corrected for autocorrelation.
- Benjamini-Hochberg FDR at 5% is applied across every pair and window tested, with Bonferroni reported alongside.
- **Deflated Sharpe ratio (DSR)** (Bailey & López de Prado, 2014), with N = every strategy variant run on every candidate. Must be ≥ 0.95.

## Acceptance
- **Rule (a):**
  - OOS net Sharpe ≥ 1.0 over the full period and ≥ 0.8 post-COVID;
  - max drawdown ≤ 20%;
  - ≥ 20 round trips;
  - significant after correction in both the full period and post-COVID;
  - DSR ≥ 0.95.
- **Rule (b), a new relationship that emerged post-COVID:**
  - every Rule (a) threshold, measured on Jan 2022 → present only;
  - plus an explicit economic reason the relationship changed.
- Pairs that only worked before COVID are rejected.

## Post-audit engine fix (made AFTER the first results were seen, disclosed here)
**What the review found.** A few trials showed impossible numbers: single-day returns of −3,300% and +1,700%, and a 90-day gain of 41,000% at nominal 1x gross. The price data was correct; the cause was the engine's account handling.
- The engine held share counts constant while a losing trade's equity collapsed, so effective leverage grew without limit. PAAS/HL reached about 2,400× gross exposure to equity.
- The z-score stop rarely fires on a trending spread, because the 60-day rolling mean follows the trend. So nothing closed these trades.
- Once equity went negative, new trades were sized from negative equity, which flipped their direction.
- A real margin account would have been liquidated long before any of this happened.

**The fix applies identically to every trial, the random baseline and the live simulator:**
- **Margin call:** if equity at the close is below 25% of gross position value, the position is liquidated at the next open. 25% is the FINRA Rule 4210 minimum maintenance requirement. The rule then goes flat and, for spread rules, disarms as it would after a stop.
- **Ruin:** if equity is ≤ 0, the position is liquidated, the account never trades again, and the loss is capped at −100%.
- Code: `walkforward.account_check` and `strategies.force_flat`. Tests: `tests/test_account_risk.py`.

**Why this is not tuning:**
- It never touches a signal parameter.
- It only acts in catastrophic states.
- It was applied to all 223 trials and the random baseline, and everything was re-run.
- **The pass/fail outcome did not change:** 0 of 223 before and after.
- The pre-fix gates are kept as `backtest/results/gates_pre_fix.csv` (sha256 `fff7d23dc8d10c85a07943de03cd91527045c3fa36a7e7a23edbbd7f68ec7d99`; 0 of 223 passed). The post-fix hash is in `backtest/results/RESULTS_HASH.txt`.

**Known weakness, left unchanged:** the pre-registered z-score stop (|z| ≥ 3.5 on a 60-day rolling window) rarely triggers on a spread that keeps trending. That is a property of the rule as pre-registered. Changing it now, after seeing results, would be tuning.

## Round 2 (second and final scouting round, run at the owner's request after round 1 found 0 passes)
- **No rule, parameter or gate changed.** Only new pairs were added: 34, proposed by four scouts organised by structure.
- **Pre-registered merge exclusions:** a duplicate of a round-1 pair, a near-identical instrument, or a pending merger between the two legs. No proposal hit any of them.
- **One multiple-testing family.** Rounds 1 and 2 were re-run together, so the BH family and the DSR's N (336) cover every trial. This is why the DSR bar rose from about 1.75 to about 1.83.
- **Borrow tiers:** new tickers flagged hard-to-borrow by the scouts get 3%/yr, the same rule as round 1. Tickers classified in round 1 keep their tier, so round 1 reproduces exactly.
- **Data check added after seeing round-2 data: `SECURITY_SPLICE_SUSPECT`.**
  - A one-day adjusted-price factor of ≥ 10× or ≤ 0.1× with no split is now a data error.
  - It caught CHRD, where Yahoo joins the cancelled pre-bankruptcy Oasis equity ($0.12 on 2020-11-20) to the reorganised shares ($34 on 2020-11-25). That jump drove two CHRD/NOG trials to ruin.
  - Before adding the rule I scanned all 145 tickers. CHRD is the only one with even a 5× one-day move, so the rule changes nothing else.
  - Round-1 trial files are byte-identical after the re-run.
- **Result:** 0 of 336 trials pass. Per the approved plan, there will be no third round.

## Paper-trading the near-misses (owner's decision after two rounds with 0 passes)
- **What the simulator trades.** The owner chose to build the simulator anyway and paper-trade the 5 best near-misses. Every report labels them **FAILED THE BAR**.
- **Purpose.** The live run is a system check: it tests that the live pipeline reproduces the backtest's signals, timing and costs. It is not a test of an edge.
- **Selection was done by code** (`sim/select_picks.py`), using the review protocol's rule:
  - rank by deflated Sharpe ratio (DSR), using the larger of the full and post-COVID values;
  - skip a trial that shares a leg with an earlier pick;
  - skip a trial whose daily returns correlate > 0.5 with an earlier pick's;
  - prefer a commodity group not yet represented.
- **Result:** NTR/DE `coint_ols`, RRC/CRK `rotation`, SLV/SILJ `leadlag`, YPF/VIST `leadlag`, ET/EPD `coint_ols`. BTU/EQT was skipped because its group was already represented. Details are in `research/near_miss_selection.md`.
- **Warm start.** The simulator's first run replays the real backtest engine on live data sliced to dates ≤ start − 1, so it starts in the backtest's state. A test guards against look-ahead.
