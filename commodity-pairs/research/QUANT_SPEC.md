# Quant engine specification

This is the binding methodology for the quant pipeline. Parameters here are **fixed in advance**: do not tune them to improve results. If something cannot be implemented exactly as written, implement the closest honest version and record the deviation in `backtest/results/IMPLEMENTATION_NOTES.md`.

Project root: `commodity-pairs/`. Use the venv at `commodity-pairs/.venv` (Python 3.13, pandas 3.x: copy-on-write is on and the default string dtype has changed, so write code accordingly). Run modules from the project root, e.g. `.venv/bin/python -m backtest.run_all`.

## 0. Ground rules
- **Every number must come from executed code.** Never estimate or type a result by hand.
- **No look-ahead.** A signal at day t may use only data up to and including day t's close. Fills happen at day t+1's open. Every fitted quantity uses only data strictly before its trading window starts: β, the lead-lag lag, σ estimates, the lead-lag regression slope.
- **Deterministic.** Seed all randomness (`numpy.random.default_rng(20261027)`).

## 1. Data: `backtest/data.py`
- **Download:**
  - Use `yfinance` `Ticker(t).history(start="2014-10-01", end="2026-10-27", auto_adjust=False, actions=True)`.
  - Freeze the research snapshot at the **last complete bar ≤ 2026-10-26**.
  - Retry 4× with backoff.
- **Cache:** save one file per ticker at `data/cache/{TICKER}.csv.gz`.
  - Columns: `date, open, high, low, close, adjclose, volume, dividends, splits`.
  - Dates are tz-naive.
- Write `data/MANIFEST.json`, with one entry per ticker: source, download UTC timestamp, rows, first/last date, sha256 of the file.
- **Load from cache only.** Research code never touches the network once a ticker is cached.
- **Adjusted open:** `adjopen = open * adjclose / close`.
- **Data checks** (write `backtest/results/data_qa.csv`):
  - zero or negative prices;
  - NaNs;
  - runs of 5+ identical closes;
  - |daily adjclose return| > 25% (cross-check against `splits`);
  - gaps against the NYSE calendar (`exchange_calendars` XNYS).
  - Report problems; do not silently drop them. A leg with unresolved data errors is excluded, and the exclusion is noted.
- **Benchmark and factor tickers to download as well:** SPY, XLE, GDX, XME, GLD, USO, plus every candidate leg.

## 2. Universe screen: `backtest/screen.py` → `research/universe_screen.csv`
For every ticker, report:
- first date;
- median dollar volume (close × volume) over the trailing 252 days and over the post-COVID regime;
- the borrow tier and slippage tier.

**Liquidity:** both dollar-volume medians must be > $20M.

**History** (training needs 504 trading days before the first out-of-sample (OOS) day):
- **Rule (a) eligible:** OOS can start by 2018-10-31, i.e. first date ≤ about 2016-10-31. This gives about 80% of the 10-year OOS window.
- **Rule (b) eligible:** OOS can start by 2022-01-03, i.e. first date ≤ about 2020-01-02.

**Tiers:**
- **ETF flag:** get `quoteType` from `yf.Ticker(t).info`, cache it in `data/ticker_info.json`, and fall back to a hand list if the info call fails.
- **Slippage:** 5 bps per side if the ticker is an ETF with median dollar volume ≥ $100M, or a stock with ≥ $500M. Otherwise 10 bps.
- **Borrow:** 0.5%/yr general collateral by default. 3%/yr if the ticker is flagged hard-to-borrow (HTB) in the scout notes, or if its median dollar volume is < $50M.
- Write the HTB list you use into the CSV.

**Candidates:** a pair stays in the tested pool only if both legs pass liquidity and at least rule (b) history. Pairs that fail are listed with the reason in `backtest/results/excluded_pairs.csv`.

## 3. Regimes and the walk-forward grid
- **Regimes:**
  - Pre-COVID: 2016-10-03 → 2020-02-28
  - COVID: 2020-03-02 → 2021-12-31
  - Post-COVID: 2022-01-03 → 2026-10-26
  - Full: 2016-10-03 → 2026-10-26
- **Global walk-forward grid:**
  - Test-window start dates are every 63 NYSE trading days, beginning 2016-10-03.
  - For each window, the training sample is the 504 trading days immediately before its start date.
  - A pair trades in a window only if both legs have complete data across the training sample.
  - All pairs share the same refit dates. This matters because the live simulator reuses this schedule.

## 4. Statistical tests: `backtest/stats_tests.py`
Use log adjusted closes. Use daily log returns for correlations and Granger tests.

Run for every candidate pair, in each of {full, pre, covid, post}:
- **Rolling return correlation, 60/120/250-day:**
  - mean, std, min, max;
  - fraction of days where the correlation's sign matches the expected sign;
  - fraction of days negative.
- **Engle-Granger:** `statsmodels.tsa.stattools.coint` in both orderings. Record both p-values.
  - **Primary EG p-value = the ordering A on B** (A = leg_a), so there is no min-over-orderings selection.
- **Johansen:** `coint_johansen(det_order=0, k_ar_diff=1)`. Record the trace statistic against the 90/95/99% critical values and pass/fail at 95%.
- **ADF on the OLS spread.**
- **Half-life:** from Δs_t = a + b·s_{t−1}, HL = −ln2 / ln(1+b). Infinite or NaN if b ≥ 0.
- **Hurst exponent of the spread:** variance-of-lagged-differences method, lags 2–100.
- **Hedge ratios:**
  - OLS β, by regime and over the full period;
  - a Kalman β path (spec in §5) — report its mean, std and range.
- **Granger** (`grangercausalitytests`, SSR F-test):
  - **Primary Granger p-value:** the joint test at maxlag = 5, run in the direction leg_a → leg_b. Also report b → a.
  - Lagged cross-correlation of returns at lags −10…+10.
- **Inverse test:**
  - Pearson correlation of daily returns.
  - **Primary inverse p-value:** regress r_A on r_B with Newey-West heteroskedasticity- and autocorrelation-consistent (HAC) standard errors (maxlags = 10) and take the **one-sided** p-value for slope < 0.

Output: `backtest/results/stats_tests.csv`, one row per pair × regime.

## 5. Strategies: `backtest/strategies.py` (shared with the live simulator)
**The live simulator will import this module.** Design it so one function call advances one day.

- `fit(rule, hist_A, hist_B, params) -> FitResult`: called at each test-window start with the training data only.
- `step(rule, state, hist_A, hist_B, fit, params) -> (new_state, target, reason)`:
  - called once per day after the close;
  - `hist_*` are adjusted closes up to and including today;
  - `target` gives target dollar weights per leg as a fraction of equity, e.g. `{A: +0.5, B: -0.5}` or `{A: 0, B: 0}`;
  - `reason` is a human-readable string such as `"entry long spread z=-2.13"`.
- State and fit results must be JSON-serializable, either dataclasses with `to_dict`/`from_dict` or plain dicts.
- **Weight normalization:** gross weights always sum to 1.0 when in a trade, because sizing is 1x gross.

### Rule `coint_ols`: mean-reverting spread
- **Fit:**
  - Regress ln A on ln B with an intercept over the training sample to get β.
  - If β ≤ 0.2 or β > 5, the window has no new entries (`reason: "beta out of range"`).
- **Daily step:**
  - Spread s_t = ln A_t − β·ln B_t, using the **current window's β for entry decisions** and the **trade's frozen entry β for an open trade**.
  - z_t = (s_t − mean(s over the last 60 days including t)) / std(same window, ddof=1).
- **Entry (when flat and armed):**
  - z ≤ −2.0 → long spread: long A, short B.
  - z ≥ +2.0 → short spread.
  - Weights: w_A = ±1/(1+β), w_B = ∓β/(1+β).
- **Exit:** z crosses 0, i.e. a long-spread trade exits when z ≥ 0 and a short-spread trade when z ≤ 0.
- **Stop:** |z| ≥ 3.5 → exit, then **disarm**.
- **Re-arm** when |z| < 2.0.
- **Freezing:** at entry, freeze β_entry. For an open trade, compute z from the β_entry spread (same 60-day rolling formula).
- Open trades carry across window boundaries.

### Rule `coint_kalman`: robustness variant, counts as its own trial
- **Kalman filter** on ln A_t = α_t + β_t ln B_t + e_t:
  - (α, β) follow a random walk;
  - δ = 1e-4, so W = δ/(1−δ)·I;
  - V_e = 1e-3;
  - initialized on the training sample (run the filter through the training data);
  - online thereafter, strictly causal: the prediction at t uses state t−1.
- **Spread:** s_t = ln A_t − β_{t−1} ln B_t − α_{t−1}.
- z-score, thresholds and position logic are the same as `coint_ols`. The weights use β_{t−1} at entry, frozen for the trade.
- β outside (0.2, 5] → no entry.

### Rule `rotation`: for inverse pairs
- **Daily:** compute the 20-day returns R_A = A_t/A_{t−20} − 1 and R_B.
- **Target:** if R_A > R_B → `{A: +0.5, B: −0.5}`, else `{A: −0.5, B: +0.5}`.
- Always invested. A flip counts as one round trip closed plus a new one opened.
- No fit is needed beyond data availability.

### Rule `leadlag`: leader = leg_a, follower = leg_b, as labeled by the scout
- **Fit, on training data only:**
  - For k in 1…10: regress the follower's forward k-day log return (t → t+k) on the leader's trailing k-day log return (t−k → t), using only pairs (t, t+k) whose t+k falls inside the training sample.
  - Pick k* = argmax |t-stat|, with slope b*.
  - σ_L = std of the leader's daily log returns in training.
  - h = OLS β of follower daily returns on leader daily returns (contemporaneous).
  - If |t-stat| < 2 or h ≤ 0, there are no entries this window.
- **Daily step:**
  - x_t = leader's trailing k* log return; z_x = x_t/(σ_L·√k*).
  - If flat and |z_x| ≥ 1.0: direction d = sign(b*·x_t); go d × (long follower, short h × leader), with gross normalized to 1.
  - Exit after holding k* trading days. Signals during a hold are ignored.
- If the scout labeled the pair `leadlag`, also run the reverse direction (b → a) as a separate trial.

### Which rules run on which pairs
- **Every candidate pair gets `coint_ols`, `coint_kalman` and `rotation`.**
- **`leadlag`** runs on pairs labeled `leadlag` by the scouts in **both directions**, and in direction a → b for every other pair. This tests whether lead-lag effects exist that the scouts didn't propose.
- **Every (pair, rule) run is a trial and counts toward the deflated Sharpe ratio's (DSR) N.**
- **Type consistency for pass gates:**
  - a `coint_*` run can only pass on the Engle-Granger primary p-value;
  - `rotation` can only pass on the inverse primary p-value;
  - `leadlag` can only pass on the Granger primary p-value in its direction.
  - So a rotation result on a positively correlated pair cannot become a pick, however good its P&L.

## 6. Walk-forward backtest: `backtest/walkforward.py`
- **Capital and sizing:** $100,000 start at the first OOS day of the pair's run. On each fill, target notional per leg = equity at the previous close × target weight. Hold share counts constant until the next signal change, with no daily rebalancing. Fractional shares are allowed.
- **Fill timing:** signal at close t, trade at **adjusted open t+1**. Returns on day t+1 are open→close for newly entered legs, plus close→close for the rest.
- **Costs, per fill per leg:**
  - **Slippage:** buys fill at adjopen × (1+slip), sells at adjopen × (1−slip), using the tier from §2.
  - **Commission:** $0.005 × shares, $1 minimum. Count shares using the *raw* open: shares_raw = notional / raw_open.
  - **Borrow:** each day, short notional at the close × rate/252.
- **Outputs per (pair, rule):**
  - daily series: date, equity, net return, gross return, positions, z or signal value, β in use;
  - a trade log: entry date, exit date, side, entry and exit reasons, net P&L, holding days, β.
- **Engine:** event-driven daily loop calling `strategies.step()`. The backtest and the simulator must share the step logic. Vectorized shortcuts are allowed only if a test proves they produce identical positions.

## 7. Metrics: `backtest/metrics.py`
Computed for each of {full, pre, covid, post}, on the daily net returns inside the regime:
- **CAGR, annualized volatility, Sharpe and Sortino.** Sharpe = mean/std×√252 with rf = 0, documented. Sortino uses downside deviation = sqrt(mean(min(r,0)²)).
- **Max drawdown, measured inside the regime.**
- **Win rate and number of round trips.** A round trip belongs to the regime of its entry date.
- **Average holding days and exposure** (% of days in a position).
- **Correlation to SPY daily returns.**

Also report:
- Bootstrap 95% CI for the full and post-COVID Sharpe: stationary block bootstrap, mean block 20 days, 2,000 resamples.
- Top-5-trade share of total net P&L.
- Worst calendar year.

## 8. Benchmarks: `backtest/baseline.py`
- Buy-and-hold of each leg and of SPY over the same OOS span: CAGR, Sharpe, max drawdown.
- **Random-pair baseline:**
  - Draw 500 random pairs (seeded) from all tickers that pass the liquidity and rule-(b) history screen, excluding candidate pairs.
  - Run `coint_ols` and `rotation` on them.
  - Save the distributions of full and post-COVID Sharpe.
  - For every candidate (pair, rule), report the percentile of its Sharpe within the baseline distribution for the same rule.

## 9. Multiple testing: `backtest/multiple_testing.py`
- **Relationship family:** every primary p-value that is computed, i.e. each (pair, test type, window ∈ {full, post}).
  - Apply Benjamini-Hochberg at q = 0.05 across the **whole family** (`statsmodels.stats.multitest.multipletests`, method `fdr_bh`).
  - Also report Bonferroni-adjusted values.
- **Deflated Sharpe Ratio** (Bailey & López de Prado 2014):
  - Use per-day Sharpe SR̂ = mean/std, not annualized.
  - N = number of (pair, rule) trials actually run on candidate pairs.
  - V = variance of the trials' SR̂ for the same window.
  - γ = 0.5772156649.
  - SR₀ = √V·[(1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e))].
  - DSR = Φ((SR̂−SR₀)·√(T−1) / √(1 − skew·SR̂ + (kurt−1)/4·SR̂²)), where kurt is non-excess kurtosis and T is the number of days.
  - Compute it on the full window for rule (a) and on the post-COVID window for rule (b), each with its own V.
  - Also report the probabilistic Sharpe ratio (PSR) against 0.

## 10. Pass gates: `backtest/gates.py` → `backtest/results/gates.csv`
Write one row per (pair, rule), with every gate as its own boolean column plus the values used.

**Rule (a), all of:**
- OOS full Sharpe ≥ 1.0 and post-COVID Sharpe ≥ 0.8;
- full max drawdown ≤ 20%;
- full round trips ≥ 20;
- BH-adjusted primary p < 0.05 for **both** the full and post windows;
- DSR_full ≥ 0.95;
- OOS coverage ≥ 80% of the full window;
- also a hard sanity gate: post-COVID round trips ≥ 5.

**Rule (b), all of:**
- post Sharpe ≥ 1.0;
- post max drawdown ≤ 20%;
- post round trips ≥ 20;
- BH-adjusted post primary p < 0.05;
- DSR_post ≥ 0.95.
- Rule (b) also needs a written "why did it change" explanation, which comes from the human/council review, not from code. Flag the row `needs_regime_change_explanation`.

**`quant_pass`** = rule (a) OR rule (b).

**Other columns:**
- `pre_only`: pre-COVID Sharpe ≥ 1.0 but fails both rules. Informational.
- `fail_reasons`: a readable list of the gates that failed.

## 11. Reports and charts
- **`backtest/results/summary.md`:**
  - the funnel: pairs scouted → screened → tested → quant_pass;
  - the top 25 (pair, rule) rows by DSR, with all gate values;
  - the baseline distribution summary;
  - per-rule counts.
- **Charts** for every (pair, rule) with `quant_pass`, plus the top 10 by DSR, in `backtest/charts/`:
  1. **Equity curve:** strategy equity vs SPY, indexed to 100.
  2. **Spread/z chart:** two vertically stacked panels sharing the x-axis (never twin y-axes) — log spread on top, z-score below with ±2 and ±3.5 dashed threshold lines and 0. Mark entries and exits.
  3. Regime boundaries shown as thin vertical lines with small labels.

**Chart style** (matplotlib, PNG, dpi = 150):
- **Background and grid:** surface `#fcfcfb`, gridlines `#e1e0d9` at linewidth 0.5, axis spines `#c3c2b7`, with top and right spines removed.
- **Ink:** primary `#0b0b0b`, secondary `#52514e`, muted `#898781`.
- **Series colors, in this fixed order:** blue `#2a78d6`, then orange `#eb6834`, then aqua `#1baf7a`.
- **Lines:** linewidth about 1.2. Thresholds are dashed and in muted ink.
- **Labels:** any chart with 2+ series needs a legend. Titles state the pair and rule. Axis labels give units.
- **Text color:** text never takes a series color.
- **Axes:** a single y-scale per panel.

## 12. Tests: `tests/` (pytest)
1. **No look-ahead:** perturb all prices after a date T, rerun, and assert that targets and `step` outputs for every date ≤ T are identical, and that fills at dates ≤ T are unchanged.
2. **Train/test disjoint:** for every window, the fit-data end date is before the test start date.
3. **Synthetic cointegrated pair** (B is a random walk; A = exp(1.0·ln B + OU noise with a half-life of about 10 days)): `coint_ols` produces Sharpe > 1 and the EG p-value is < 0.01.
4. **Two independent random walks:** the DSR across 50 random trials is < 0.95 for the best trial.
5. **Cost accounting:** hand-checked fills on a 3-day toy series give exactly the expected slippage, commission and borrow.
6. **Determinism:** running the same input twice gives identical outputs. Also write a hash of `gates.csv` to `backtest/results/RESULTS_HASH.txt`.

## 13. Entry point
`.venv/bin/python -m backtest.run_all` does everything end to end from the cache: screen → stats → backtests → baseline → multiple testing → gates → summary → charts. Downloading is a separate step: `python -m backtest.data --download`.
