# Quant pipeline summary

Snapshot: Yahoo Finance daily bars through 2026-10-26 (frozen cache, see `data/MANIFEST.json`). All numbers below were produced by `python -m backtest.run_all`; nothing is hand-typed. Research only: no brokerage, no real trades.

## Funnel

| stage | count |
|---|---|
| pairs scouted (candidates.csv) | 67 |
| pairs with usable data (both legs present, no unresolved QA error) | 65 |
| pairs screened in (liquidity > $20M both medians, rule-(b) history) | 54 |
| (pair, rule) trials tested  (= N for the DSR) | 223 |
| quant_pass = rule (a) OR rule (b) | 0 |
|    of which rule (a) | 0 |
|    of which rule (b) | 0 |
|    rule (b) only (needs_regime_change_explanation) | 0 |

Tickers: 99 downloaded of 99 requested (97 pass data QA, 89 pass liquidity, 96 have rule-(b) history).

**No (pair, rule) row passed the pre-registered gates.** Thresholds were not relaxed.

## Excluded pairs

| pair_id | stage | reason |
|---|---|---|
| PPC_DBA | screen | leg B DBA: liquidity (median $vol 252d=20.1M, post-COVID=12.4M; need >20M both) |
| GPRE_CORN | screen | leg A GPRE: liquidity (median $vol 252d=19.6M, post-COVID=20.9M; need >20M both) | leg B CORN: liquidity (median $vol 252d=4.7M, post-COVID=1.7M; need >20M both) |
| MOO_ADM | screen | leg A MOO: liquidity (median $vol 252d=17.2M, post-COVID=5.7M; need >20M both) |
| CPER_COPX | data | leg A CPER: unresolved data errors [identical_close_run_ge5(2)] | leg A CPER: liquidity (median $vol 252d=21.0M, post-COVID=3.9M; need >20M both) |
| USO_BNO | screen | leg B BNO: liquidity (median $vol 252d=80.7M, post-COVID=16.7M; need >20M both) |
| CF_LXU | screen | leg B LXU: liquidity (median $vol 252d=8.0M, post-COVID=4.9M; need >20M both) |
| AMR_HCC | screen | history: first joint OOS window start 2023-04-06 > 2022-01-04 (first dates {'AMR': '2021-02-08', 'HCC': '2017-04-13'}) |
| PPLT_PALL | screen | leg A PPLT: liquidity (median $vol 252d=45.5M, post-COVID=14.2M; need >20M both) | leg B PALL: liquidity (median $vol 252d=27.0M, post-COVID=8.4M; need >20M both) |
| CEG_VST | screen | history: first joint OOS window start 2024-04-09 > 2022-01-04 (first dates {'CEG': '2022-01-19', 'VST': '2016-10-05'}) |
| CEG_CCJ | screen | history: first joint OOS window start 2024-04-09 > 2022-01-04 (first dates {'CEG': '2022-01-19', 'CCJ': '2014-10-01'}) |
| LEU_CCJ | screen | leg A LEU: liquidity (median $vol 252d=154.5M, post-COVID=12.5M; need >20M both) |
| MP_GM | screen | history: first joint OOS window start 2022-07-07 > 2022-01-04 (first dates {'MP': '2020-06-22', 'GM': '2014-10-01'}) |
| NXE_CCJ | data | leg A NXE: unresolved data errors [identical_close_run_ge5(6)] |

## Per-rule counts

| rule | trials | full Sharpe>=1.0 | post Sharpe>=0.8 | post Sharpe>=1.0 | full maxDD<=20% | trips>=20 | BH p<.05 full | BH p<.05 post | DSR full>=.95 | DSR post>=.95 | pass (a) | pass (b) | pre-only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coint_kalman | 54 | 0 | 0 | 0 | 24 | 53 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| coint_ols | 54 | 0 | 1 | 0 | 10 | 46 | 0 | 1 | 0 | 0 | 0 | 0 | 3 |
| leadlag | 54 | 0 | 0 | 0 | 5 | 54 | 20 | 1 | 0 | 0 | 0 | 0 | 1 |
| leadlag_rev | 7 | 0 | 0 | 0 | 1 | 7 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation | 54 | 0 | 1 | 0 | 0 | 54 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

## Multiple testing

Relationship family: 338 primary p-values (pair x test type x window in {full, post}); Benjamini-Hochberg at q = 0.05 rejects 27; Bonferroni (alpha 0.05) rejects 13.

| test | window | n | raw_lt_05 | bh_reject |
|---|---|---|---|---|
| eg | full | 54 | 3 | 0 |
| eg | post | 54 | 5 | 1 |
| granger_ab | full | 54 | 32 | 20 |
| granger_ab | post | 54 | 5 | 1 |
| granger_ba | full | 7 | 7 | 5 |
| granger_ba | post | 7 | 2 | 0 |
| inverse | full | 54 | 0 | 0 |
| inverse | post | 54 | 1 | 0 |

Deflated Sharpe: N = 223 trials; V(full) = 7.655e-04, V(post) = 1.193e-03 (variance of per-day Sharpe across trials); SR0 annualised: full 1.23, post 1.54.

## Top 25 (pair, rule) rows by DSR (max of DSR_full, DSR_post)

| pair | rule | SR full | SR post | SR pre | maxDD full | maxDD post | RT full | RT post | BH p full | BH p post | DSR full | DSR post | cover | fail(a) | fail(b) | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NTR_DE | coint_ols | 0.67 | 0.94 | n/a | 0.18 | 0.15 | 25 | 21 | 0.7849 | 1.0000 | 0.068 | 0.096 | 0.68 | 5 | 3 | no |
| BTU_EQT | rotation | 0.72 | 0.64 | -1.57 | 0.47 | 0.32 | 160 | 103 | 1.0000 | 1.0000 | 0.078 | 0.026 | 0.75 | 7 | 4 | no |
| RRC_CRK | rotation | 0.05 | 0.87 | -0.02 | 0.76 | 0.27 | 235 | 88 | 1.0000 | 1.0000 | 0.000 | 0.072 | 1.00 | 5 | 4 | no |
| SLV_SILJ | leadlag | 0.34 | 0.78 | -0.21 | 0.18 | 0.12 | 145 | 67 | 0.2192 | 1.0000 | 0.002 | 0.052 | 1.00 | 5 | 3 | no |
| ET_EPD | coint_ols | 0.22 | 0.70 | 0.40 | 0.28 | 0.08 | 45 | 21 | 1.0000 | 1.0000 | 0.001 | 0.033 | 1.00 | 6 | 3 | no |
| AR_DOW | coint_kalman | 0.45 | 0.56 | n/a | 0.09 | 0.05 | 26 | 19 | 1.0000 | 0.2177 | 0.032 | 0.014 | 0.55 | 6 | 4 | no |
| ALB_TSLA | rotation | 0.43 | 0.66 | 0.18 | 0.39 | 0.35 | 228 | 113 | 1.0000 | 1.0000 | 0.006 | 0.027 | 1.00 | 6 | 4 | no |
| CCJ_UEC | coint_ols | 0.63 | 0.23 | 0.48 | 0.33 | 0.33 | 47 | 24 | 0.2386 | 0.8767 | 0.023 | 0.002 | 1.00 | 6 | 4 | no |
| NTR_MOS | coint_ols | 0.45 | 0.58 | n/a | 0.16 | 0.16 | 27 | 20 | 1.0000 | 1.0000 | 0.020 | 0.017 | 0.68 | 6 | 3 | no |
| CTVA_FMC | leadlag | 0.40 | 0.56 | n/a | 0.11 | 0.11 | 68 | 62 | 1.0000 | 1.0000 | 0.019 | 0.008 | 0.53 | 6 | 3 | no |
| BTU_EQT | leadlag | -0.25 | 0.55 | 0.30 | 0.94 | 0.34 | 122 | 47 | 0.0130 | 0.1914 | 0.000 | 0.016 | 0.75 | 6 | 4 | no |
| XOM_MTDR | rotation | 0.32 | 0.54 | -0.83 | 0.55 | 0.13 | 231 | 95 | 1.0000 | 1.0000 | 0.002 | 0.014 | 1.00 | 6 | 3 | no |
| UUUU_DNN | coint_kalman | 0.07 | 0.50 | -0.39 | 0.34 | 0.18 | 95 | 50 | 0.9136 | 1.0000 | 0.000 | 0.012 | 1.00 | 6 | 3 | no |
| HCC_CLF | coint_ols | 0.36 | 0.48 | 1.57 | 0.57 | 0.40 | 28 | 14 | 1.0000 | 1.0000 | 0.009 | 0.011 | 0.73 | 7 | 5 | no |
| HCC_CLF | coint_kalman | 0.40 | 0.40 | 0.62 | 0.17 | 0.14 | 65 | 41 | 1.0000 | 1.0000 | 0.011 | 0.004 | 0.73 | 6 | 3 | no |
| HCC_CLF | leadlag | 0.37 | 0.31 | 1.50 | 0.34 | 0.34 | 126 | 68 | 0.1701 | 0.9245 | 0.010 | 0.003 | 0.73 | 7 | 4 | no |
| FRO_DHT | coint_ols | 0.50 | 0.30 | 0.87 | 0.18 | 0.18 | 43 | 18 | 0.2112 | 0.9267 | 0.010 | 0.003 | 1.00 | 5 | 4 | no |
| CNR_CNX | coint_ols | -0.06 | 0.48 | -0.70 | 0.74 | 0.26 | 25 | 18 | 1.0000 | 0.3774 | 0.000 | 0.010 | 0.68 | 7 | 5 | no |
| FNV_RGLD | coint_ols | 0.29 | 0.47 | 0.02 | 0.21 | 0.15 | 39 | 18 | 1.0000 | 1.0000 | 0.001 | 0.009 | 1.00 | 6 | 4 | no |
| USO_JETS | rotation | -0.16 | 0.44 | -0.85 | 0.73 | 0.32 | 241 | 119 | 1.0000 | 0.1454 | 0.000 | 0.008 | 0.93 | 6 | 4 | no |
| TSN_PPC | coint_ols | 0.20 | 0.43 | -0.16 | 0.22 | 0.17 | 42 | 20 | 0.7228 | 0.9267 | 0.001 | 0.007 | 1.00 | 6 | 3 | no |
| SLB_HAL | coint_ols | 0.15 | 0.41 | -0.20 | 0.27 | 0.15 | 44 | 19 | 0.3589 | 0.9566 | 0.000 | 0.007 | 1.00 | 6 | 4 | no |
| CAT_COPX | coint_ols | 0.21 | 0.40 | -0.19 | 0.27 | 0.19 | 41 | 21 | 0.6727 | 0.5808 | 0.001 | 0.007 | 1.00 | 6 | 3 | no |
| EQT_CF | coint_kalman | 0.29 | 0.39 | -1.14 | 0.19 | 0.17 | 65 | 52 | 0.7228 | 0.4927 | 0.001 | 0.006 | 1.00 | 5 | 3 | no |
| GLD_GDX | leadlag | 0.11 | 0.39 | 0.66 | 0.18 | 0.08 | 169 | 63 | 0.2359 | 0.2192 | 0.000 | 0.006 | 1.00 | 5 | 3 | no |

Gate values for the top 10 (why they fail):

- **NTR_DE / coint_ols**: rule(a) fails: full Sharpe 0.666 < 1.0; BH p full 0.7849 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.068 < 0.95; coverage 0.676 < 0.8 || rule(b) fails: post Sharpe 0.942 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.096 < 0.95
- **BTU_EQT / rotation**: rule(a) fails: full Sharpe 0.720 < 1.0; post Sharpe 0.639 < 0.8; full maxDD 0.473 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.078 < 0.95; coverage 0.751 < 0.8 || rule(b) fails: post Sharpe 0.639 < 1.0; post maxDD 0.320 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.026 < 0.95
- **RRC_CRK / rotation**: rule(a) fails: full Sharpe 0.050 < 1.0; full maxDD 0.757 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe 0.874 < 1.0; post maxDD 0.272 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.072 < 0.95
- **SLV_SILJ / leadlag**: rule(a) fails: full Sharpe 0.339 < 1.0; post Sharpe 0.779 < 0.8; BH p full 0.2192 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.002 < 0.95 || rule(b) fails: post Sharpe 0.779 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.052 < 0.95
- **ET_EPD / coint_ols**: rule(a) fails: full Sharpe 0.224 < 1.0; post Sharpe 0.703 < 0.8; full maxDD 0.283 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.703 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.033 < 0.95
- **AR_DOW / coint_kalman**: rule(a) fails: full Sharpe 0.451 < 1.0; post Sharpe 0.563 < 0.8; BH p full 1.0000 >= 0.05; BH p post 0.2177 >= 0.05; DSR full 0.032 < 0.95; coverage 0.552 < 0.8 || rule(b) fails: post Sharpe 0.563 < 1.0; post round trips 19 < 20; BH p post 0.2177 >= 0.05; DSR post 0.014 < 0.95
- **ALB_TSLA / rotation**: rule(a) fails: full Sharpe 0.429 < 1.0; post Sharpe 0.657 < 0.8; full maxDD 0.391 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.006 < 0.95 || rule(b) fails: post Sharpe 0.657 < 1.0; post maxDD 0.351 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.027 < 0.95
- **CCJ_UEC / coint_ols**: rule(a) fails: full Sharpe 0.627 < 1.0; post Sharpe 0.227 < 0.8; full maxDD 0.332 > 0.2; BH p full 0.2386 >= 0.05; BH p post 0.8767 >= 0.05; DSR full 0.023 < 0.95 || rule(b) fails: post Sharpe 0.227 < 1.0; post maxDD 0.332 > 0.2; BH p post 0.8767 >= 0.05; DSR post 0.002 < 0.95
- **NTR_MOS / coint_ols**: rule(a) fails: full Sharpe 0.454 < 1.0; post Sharpe 0.581 < 0.8; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.020 < 0.95; coverage 0.676 < 0.8 || rule(b) fails: post Sharpe 0.581 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.017 < 0.95
- **CTVA_FMC / leadlag**: rule(a) fails: full Sharpe 0.403 < 1.0; post Sharpe 0.559 < 0.8; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.019 < 0.95; coverage 0.527 < 0.8 || rule(b) fails: post Sharpe 0.559 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.008 < 0.95

## Closest to passing

Ranked by fewest failed gates under the better of rules (a)/(b), ties broken by DSR. Gate counts can flatter a row with a negative Sharpe that happens to clear the drawdown, trade-count and p-value gates, so read this together with the DSR ranking above.

- **BHP_RIO / leadlag** (rule (a) fails 4 gates, rule (b) fails 2): rule(a) fails: full Sharpe -0.888 < 1.0; post Sharpe -0.643 < 0.8; full maxDD 0.359 > 0.2; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe -0.643 < 1.0; DSR post 0.000 < 0.95
- **GDX_GDXJ / coint_kalman** (rule (a) fails 5 gates, rule (b) fails 2): rule(a) fails: full Sharpe -0.589 < 1.0; post Sharpe -1.408 < 0.8; full maxDD 0.216 > 0.2; BH p full 0.7465 >= 0.05; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe -1.408 < 1.0; DSR post 0.000 < 0.95
- **NTR_DE / coint_ols** (rule (a) fails 5 gates, rule (b) fails 3): rule(a) fails: full Sharpe 0.666 < 1.0; BH p full 0.7849 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.068 < 0.95; coverage 0.676 < 0.8 || rule(b) fails: post Sharpe 0.942 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.096 < 0.95
- **SLV_SILJ / leadlag** (rule (a) fails 5 gates, rule (b) fails 3): rule(a) fails: full Sharpe 0.339 < 1.0; post Sharpe 0.779 < 0.8; BH p full 0.2192 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.002 < 0.95 || rule(b) fails: post Sharpe 0.779 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.052 < 0.95
- **ET_EPD / coint_ols** (rule (a) fails 6 gates, rule (b) fails 3): rule(a) fails: full Sharpe 0.224 < 1.0; post Sharpe 0.703 < 0.8; full maxDD 0.283 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.703 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.033 < 0.95

## Random-pair baseline

500 random pairs (seed 20261027) from tickers that pass data QA, liquidity and rule-(b) history, excluding the candidate pairs; each run with the same engine, costs and walk-forward grid. Percentile = share of baseline Sharpe ratios at or below the candidate's, for the same rule (baseline exists for coint_ols and rotation only).

| rule | window | n_runs | n_defined | mean | std | p05 | p25 | median | p75 | p95 | p99 | max | frac_ge_1 | frac_ge_0p8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coint_ols | full | 500 | 498 | -0.02 | 0.32 | -0.58 | -0.21 | -0.02 | 0.18 | 0.51 | 0.67 | 1.17 | 0.002 | 0.004 |
| coint_ols | post | 500 | 493 | -0.04 | 0.43 | -0.80 | -0.28 | -0.03 | 0.23 | 0.66 | 0.98 | 1.60 | 0.010 | 0.022 |
| rotation | full | 500 | 500 | -0.25 | 0.41 | -0.99 | -0.51 | -0.22 | 0.03 | 0.38 | 0.63 | 0.73 | 0.000 | 0.000 |
| rotation | post | 500 | 500 | -0.31 | 0.47 | -1.13 | -0.60 | -0.26 | 0.01 | 0.40 | 0.60 | 0.94 | 0.000 | 0.004 |

Baseline percentile of the top-10 rows (where a baseline exists):

| pair_id | rule | full_sharpe | full_sharpe_baseline_pctile | post_sharpe | post_sharpe_baseline_pctile |
|---|---|---|---|---|---|
| NTR_DE | coint_ols | 0.67 | 98.8 | 0.94 | 98.6 |
| BTU_EQT | rotation | 0.72 | 99.6 | 0.64 | 99.4 |
| RRC_CRK | rotation | 0.05 | 75.4 | 0.87 | 99.6 |
| SLV_SILJ | leadlag | 0.34 | n/a | 0.78 | n/a |
| ET_EPD | coint_ols | 0.22 | 79.1 | 0.70 | 96.6 |
| AR_DOW | coint_kalman | 0.45 | n/a | 0.56 | n/a |
| ALB_TSLA | rotation | 0.43 | 96.0 | 0.66 | 99.4 |
| CCJ_UEC | coint_ols | 0.63 | 98.0 | 0.23 | 74.8 |
| NTR_MOS | coint_ols | 0.45 | 92.6 | 0.58 | 93.5 |
| CTVA_FMC | leadlag | 0.40 | n/a | 0.56 | n/a |

## Buy-and-hold reference

SPY total-return buy-and-hold over 2016-10-03 -> 2026-10-26: CAGR 15.21%, Sharpe 0.88, max drawdown 33.7%. Per-pair leg and SPY buy-and-hold figures are in `baseline_buyhold.csv`.

## Data and implementation caveats

- QA: 2 unresolved error row(s) (CPER, NXE); 46 warning row(s); see `data_qa.csv`.
- Survivorship bias: the universe is built from tickers that still trade; the random baseline carries the same bias.
- See `IMPLEMENTATION_NOTES.md` for every deviation and judgement call, and `sanity_checks.md` for the auto-generated cross-checks.
