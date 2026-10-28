# Implementation notes

Everything here documents how `research/QUANT_SPEC.md` was implemented, where it was read or approximated, and what
looked surprising while auditing the engine. It contains no result numbers: every number is produced by code in
`summary.md`, `gates.csv`, `sanity_checks.md` and the other files under `backtest/results/`.

Reproduce: `.venv/bin/python -m backtest.data --download` (one time, network) then
`.venv/bin/python -m backtest.run_all` (cache only) and `.venv/bin/python -m pytest -q`.
No parameter was tuned; the only free choice I had to make (Kalman prior variance) is listed below.

## Package layout
- `backtest/data.py` download, gzip-CSV cache (deterministic bytes: gzip mtime 0), `MANIFEST.json`, QA.
- `backtest/screen.py` universe screen and pair pool. `backtest/trading_calendar.py` XNYS sessions and the global grid.
- `backtest/strategies.py` the five rules, shared with the live simulator. It imports only `numpy`/`math`; `fit()` results
  and per-pair `state` are plain JSON-serialisable dicts (tested by a JSON round trip inside the step loop).
- `backtest/walkforward.py` event-driven engine (calls `strategies.step()` every day, fills at the next open).
- `backtest/metrics.py`, `stats_tests.py`, `multiple_testing.py`, `gates.py`, `baseline.py`, `charts.py`, `report.py`,
  `audit.py`, `runner.py` (fork pool; every task is seeded from its task index so the process count cannot change results),
  `run_all.py`.
- No vectorised fast path was added, so there is no second implementation to keep in sync with `step()`.
  The whole pipeline (stats, 223 trials with 2,000-resample bootstraps, 1,000 baseline runs, 20 charts) takes about a minute on 4 cores.

## Step interface (what the live simulator must replicate)
- `fit(rule, hist_A, hist_B, params)` per window on training adjusted closes only (`FitResult.to_dict/from_dict`).
- `new_window_state(rule, prev_state, fit, params)` right after `fit`: keeps an open trade (frozen entry beta, hold counter,
  armed flag) and re-bases the Kalman filter on the new fit. This function is not named in the spec; it is the explicit
  version of "open trades carry across window boundaries".
- `step(rule, state, hist_A, hist_B, fit, params) -> (new_state, {"A": wA, "B": wB}, reason)`. Call it exactly once per
  trading day, in order (the Kalman state advances by one observation per call). `state` is not mutated.
- Target keys are the role labels `"A"` (= `leg_a`) and `"B"` (= `leg_b`). `leadlag_rev` (leader = B) is a separate rule name.

## Calendar, grid and eligibility
- Sessions come from `exchange_calendars` XNYS between 2014-10-01 and 2026-10-26. There are 505 sessions before 2016-10-03, so
  the first training sample (504 sessions) starts 2014-10-02. Windows start every 63 sessions; the last window is short.
- A window is tradable iff both legs have complete open/close/adjusted data over the 504-session training sample AND the test
  window (no gap exists in the cache, so in practice only the listing date matters). If a later window were ever ineligible the
  run would stop there (recorded in `meta["stopped"]`); this never happens with the frozen cache.
- Window k's first signal is computed at the close of its first test day with that window's fit; the signal from the last day of
  window k is filled at the open of window k+1's first day using window k's fit. Nothing is evaluated with a fit whose
  training data ends after the signal date.
- Rule (a)/(b) eligibility is evaluated on the grid: (a) first OOS window start <= 2018-10-31 (this is the 2018-10-03 window,
  which gives 80.1% coverage, just above the 80% gate); (b) first OOS window start <= **2022-01-04**, not 2022-01-03, because
  2022-01-03 is the last day of grid window 20 and 2022-01-04 is the first grid date at or after the post-COVID start.
  The pool keeps pairs with at least rule-(b) history, as specified.
- The run starts with $100,000 flat at the first OOS day (that day carries a zero return); metrics are computed on days from the
  first OOS day, flat days included (idle cash earns 0%). Coverage = days in executed windows / days in the full window.

## Data and QA decisions
- yfinance `Close` is split-adjusted but not dividend-adjusted; the spec's "raw" open/close are those series. Commission share
  counts use notional / that open. Adjusted open = open * adjclose / close.
- Adjusted history is back-adjusted for dividends known only later (standard total-return construction); the frozen cache is
  what keeps this reproducible. Cache integrity is verified against `MANIFEST.json` (sha256) at the start of `run_all`.
- QA severity: a problem dated before the first training sample the walk-forward can ever use for that ticker is a warning;
  one inside the usable span is an **error** and excludes the leg. A run of >= 5 identical closes is an error only when at
  least half of the run's days have zero volume (stale prints); big moves (>25%) are errors only if they look like an
  unadjusted split (price factor ~ 1/ratio near a split date) or if raw and adjusted returns disagree by > 10 points.
  Genuine large moves (COVID crash, small caps) are reported as warnings.
- Excluded for data errors: **NXE** (2014-15 history is stale OTC prints; the NYSE listing is much later) and **CPER**
  (stale prints; it also fails liquidity).
- **FANG_PR caveat (not excluded).** Yahoo's `PR` history starts in April 2016 as the Silver Run SPAC (flat $10, zero volume,
  flagged as a warning because it precedes the first usable sample) and the operating company (Centennial, now Permian
  Resources) only began trading around the 2016-10-11 merger. The first two training windows of FANG_PR (windows 7 and 8) still
  contain the pre-merger SPAC prices from July to October 2016. I did not patch the data; the lead may want to treat those two
  windows as untradable. `sanity_checks.md` lists the affected windows.
- Other structural breaks flagged by the scouts are left as they are in the data and are **not** spliced or trimmed: CNR is the
  CONSOL (CEIX) series that became Core Natural Resources after the 2025 Arch combination; NTR starts with the 2018 merger;
  DOW and CTVA start with their 2019 spin-offs; CEG starts 2022; HCC and BTU start in 2017; MP starts in 2020; AMR starts in 2021.
  Pairs that cannot reach rule-(b) history are excluded with the reason in `excluded_pairs.csv`.

## Screen tiers
- Liquidity uses the median of close * volume over the last 252 rows and over 2022-01-03 -> end; both must exceed $20M.
- Slippage/borrow tiers use the **smaller** of the two medians (conservative). ETF flag from `yf.Ticker.info['quoteType']`
  (cached in `data/ticker_info.json`; the fallback hand list in `config.ETF_FALLBACK` was not needed for any ticker).
- Hard-to-borrow list (`config.HTB_FLAGS`, also written into `universe_screen.csv`) = tickers whose scout notes say borrow is
  tight, expensive, limited, has fee spikes, or short interest is elevated: SCCO, CENX, ET, EPD, FRO, DHT, BNO, GPRE, LXU, AMR,
  HCC, GDXJ, SILJ, PPLT, PALL, UEC, MP, NXE, DNN, UUUU. "Check the borrow fee" without a stated problem (PPC, CNR) was not
  treated as a flag; those names only reach 3% if their median dollar volume is below $50M.

## Rules: interpretation choices
- **coint_ols** exactly as specified. One reading: a stop (|z| >= 3.5) is checked before the zero-cross exit, so the rare jump
  from one side to |z| >= 3.5 on the far side is booked as a stop and disarms. After a normal exit the rule stays armed. A window
  with beta outside (0.2, 5] blocks new entries only; an open trade keeps being managed with its frozen entry beta.
- **coint_kalman.** Prior and initialisation are not fully specified. I initialise (alpha, beta) at the OLS estimate on the training
  sample with prior covariance `kalman_p0 * I` (`kalman_p0 = 1e-2`, a free choice, chosen once for numerical sanity and never
  revisited), run the filter through the 504 training days (W = delta/(1-delta) * I, delta = 1e-4, V_e = 1e-3), and re-base
  from the new fit at every window start. The spread is the one-step-ahead innovation (alpha, beta from t-1). Its 60-day z
  is computed from a rolling buffer of innovations kept in the state. For an open trade the z is the live innovation z; only
  the weights use the frozen entry beta (beta_{t-1} at entry). The filter is cross-checked against an independent matrix
  implementation in the tests.
- **leadlag.** The k-selection t-statistic is the plain OLS slope t-stat, as written. Forward k-day returns overlap, so these
  t-stats are inflated and grow with k; the selected k* is therefore biased towards the upper bound and the |t| >= 2 filter is
  permissive (see the computed k* histogram in `sanity_checks.md`). HAC t-stats would be more honest but are not what was
  specified; no pair can pass on this alone because the Granger gate and the DSR still apply. Holding "k* trading days"
  means the exit is signalled at the close of the k*-th session after the signal, filled at the next open, so a trade
  occupies exactly k* sessions between fills (tested).
- **rotation.** Ties go to the `else` branch (A short, B long). A flip is booked as closing one trade and opening another.

## Engine accounting
- Fills at the adjusted open of t+1. Shares = target weight * equity at the previous close / adjusted open (reference price);
  buys fill at adjopen*(1+slip), sells at adjopen*(1-slip), so slippage is a cost on top of the reference notional.
- Commission = max($1, $0.005 * raw shares) per fill per leg. A rotation flip is two fills per leg (close, then open), each
  with its own $1 minimum, which is slightly conservative versus one netted order.
- Borrow = short notional at the close * rate / 252, charged daily including the entry day and excluding the exit day.
- Weights are re-derived only when the target changes (no daily rebalancing); the actual weights drift between signals.
- Gross return = net return + (slippage + commission + borrow) / previous equity. Sum of trade P&L equals final equity minus
  start capital (checked for every trial in `sanity_checks.md`, together with an independent recomputation of closed trades
  from raw prices).
- Round trips (gates and regime counts) are CLOSED trades only, assigned to the regime of their entry date. A trade still open at
  the last bar is logged with `open_at_end=True` and marked to the last close without exit costs; it is in equity and in
  top-5 concentration but not in round-trip counts.

## Statistics, multiple testing, gates
- Stats use only observations inside each regime window (rolling correlations are not warmed up from before the window).
  EG uses `coint(trend="c", autolag="aic")`; the primary p-value is the A-on-B ordering. Johansen is run on log prices.
  Cross-correlation column `xcorr_pK` is corr(r_A[t], r_B[t+K]) (K > 0: A leads B), `xcorr_mK` the reverse.
- The BH family contains the three primary p-values per pair for the full and post windows, plus the Granger b->a p-value for
  pairs the scouts labelled `leadlag` (their reverse trial is gated on it). Excluded pairs are not in the family. Windows with
  too little data produce no p-value and are left out of the family (the `family_size` column says how many entered).
- The three tests run on full-window in-sample data by specification; they are gates, not inputs to any fit.
- DSR: per-day Sharpe, N = all trials run on candidate pairs (includes trials with an undefined Sharpe), V = sample variance
  (ddof = 1) of the finite per-day Sharpes of the same window, T = number of daily returns in the window (flat days
  included), population skew and non-excess kurtosis. `psr_*` is against 0.
- `fail_reasons` is empty for quant_pass rows; otherwise it lists failed gates for rule (a) and rule (b) separately.
  `needs_regime_change_explanation` is set when a row passes only rule (b).
- Baseline: 500 random pairs drawn from tickers passing data QA, liquidity and rule-(b) history (the benchmark ETFs are in the
  pool), candidate pairs excluded, random orientation, same tiers/costs/grid. Percentiles exist only for `coint_ols` and
  `rotation` (the two rules the spec runs on the baseline); other rules show n/a.
- Baseline and trials share survivorship bias (universe built from today's tickers). The liquidity screen is evaluated at the end of
  the sample, which is itself a mild selection effect; both follow the spec.

## Things noticed during the self-audit
- No look-ahead found. Tests perturb every price after a date T (violent multiplicative shocks) and assert that fits, step
  outputs, equity, fills and trade logs up to T are bit-for-bit identical for all five rules; a recording strategy proves the
  engine hands `fit()` exactly the 504 sessions ending the day before the window and `step()` data through today only.
- SPY buy-and-hold over the OOS span: price-only CAGR sits inside the 12-14% ballpark and the adjusted-close total return is
  higher by the dividend contribution (numbers in `sanity_checks.md`); its max drawdown matches the March 2020 crash.
- `coint_kalman` as specified trades the one-step innovation, which is close to white noise by construction: the spread
  "reverts" within a few days, so average holds are very short, turnover is high and costs dominate. This is a property of
  the specified rule, not a bug (the matrix cross-check passes); it is why this rule is the weakest in the per-rule table.
- `rotation` is always invested at 1x gross and flips often, so its cost drag is the largest of all rules; the random-pair
  baseline for rotation has a negative mean Sharpe for the same reason.
- Rule (a) coverage gate: the 2018-10-03 window gives 0.8008 coverage on the 2,530-session full window, so a pair whose first
  OOS window is the next one (2019-01-04) fails the gate by a hair; this is why late-listed names cannot pass rule (a).
- Pandas 3.1: no chained assignment, no `inplace`; `exchange_calendars` emits a `Pandas4Warning`, filtered in `pytest.ini`.
- `requirements.txt` needed no changes.

## Post-review changes (lead researcher, after the first full run)
- **Account risk added:** `walkforward.account_check` and `strategies.force_flat`, with `config.MAINT_MARGIN = 0.25`.
  - **Margin call:** if equity at the close is below 25% of gross exposure, the position is liquidated at the next open, and the rule goes flat and disarms.
  - **Ruin:** if equity is ≤ 0, the account is liquidated, never trades again, and the day's return is capped at −100%.
  - **Guard:** new legs are never sized from equity ≤ 0.
- **Why:** without these, a losing trade's leverage grew without bound (up to about 2,400× equity) and negative equity flipped trade direction. This produced impossible daily returns of −3,300% and +1,700%. The data itself was correct.
- **Re-run:** all 223 trials and the baseline were re-run. The quant_pass count is unchanged at 0. `gates_pre_fix.csv` keeps the pre-fix gates.
- **Tests:** `tests/test_account_risk.py`, 4 tests. The full suite now has 57 tests.
- **New modules:**
  - `backtest/semester_check.py`: the "42% semester" analysis, written to `research/semester_42pct.md`;
  - `backtest/final_charts.py`: the report chart.
