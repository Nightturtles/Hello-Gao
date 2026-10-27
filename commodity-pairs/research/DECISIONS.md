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
