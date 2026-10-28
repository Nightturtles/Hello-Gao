# Quant pipeline summary

Snapshot: Yahoo Finance daily bars through 2026-10-26 (frozen cache, see `data/MANIFEST.json`). All numbers below were produced by `python -m backtest.run_all`; nothing is hand-typed. Research only: no brokerage, no real trades.

## Funnel

| stage | count |
|---|---|
| pairs scouted (candidates.csv) | 101 |
| pairs with usable data (both legs present, no unresolved QA error) | 97 |
| pairs screened in (liquidity > $20M both medians, rule-(b) history) | 82 |
| (pair, rule) trials tested  (= N for the DSR) | 336 |
| quant_pass = rule (a) OR rule (b) | 0 |
|    of which rule (a) | 0 |
|    of which rule (b) | 0 |
|    rule (b) only (needs_regime_change_explanation) | 0 |

Tickers: 145 downloaded of 145 requested (141 pass data QA, 130 pass liquidity, 142 have rule-(b) history).

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
| PICK_XME | screen | leg A PICK: liquidity (median $vol 252d=34.0M, post-COVID=11.6M; need >20M both) |
| TNK_INSW | screen | leg A TNK: liquidity (median $vol 252d=29.6M, post-COVID=17.9M; need >20M both) |
| SBLK_GNK | data | leg B GNK: unresolved data errors [identical_close_run_ge5(5)] | leg B GNK: liquidity (median $vol 252d=8.4M, post-COVID=10.5M; need >20M both) |
| MOS_ICL | screen | leg B ICL: liquidity (median $vol 252d=6.8M, post-COVID=5.7M; need >20M both) |
| CHRD_NOG | data | leg A CHRD: unresolved data errors [abs_adjret_gt_25pct(19)] |
| LBRT_PUMP | screen | leg B PUMP: liquidity (median $vol 252d=36.5M, post-COVID=12.7M; need >20M both) |

## Per-rule counts

| rule | trials | full Sharpe>=1.0 | post Sharpe>=0.8 | post Sharpe>=1.0 | full maxDD<=20% | trips>=20 | BH p<.05 full | BH p<.05 post | DSR full>=.95 | DSR post>=.95 | pass (a) | pass (b) | pre-only |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coint_kalman | 82 | 0 | 0 | 0 | 32 | 81 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| coint_ols | 82 | 0 | 1 | 0 | 20 | 73 | 0 | 1 | 0 | 0 | 0 | 0 | 3 |
| leadlag | 82 | 0 | 0 | 0 | 6 | 82 | 26 | 1 | 0 | 0 | 0 | 0 | 2 |
| leadlag_rev | 8 | 0 | 0 | 0 | 1 | 8 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| rotation | 82 | 0 | 1 | 0 | 0 | 82 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

## Multiple testing

Relationship family: 508 primary p-values (pair x test type x window in {full, post}); Benjamini-Hochberg at q = 0.05 rejects 33; Bonferroni (alpha 0.05) rejects 12.

| test | window | n | raw_lt_05 | bh_reject |
|---|---|---|---|---|
| eg | full | 82 | 7 | 0 |
| eg | post | 82 | 9 | 1 |
| granger_ab | full | 82 | 46 | 26 |
| granger_ab | post | 82 | 7 | 1 |
| granger_ba | full | 8 | 8 | 5 |
| granger_ba | post | 8 | 2 | 0 |
| inverse | full | 82 | 0 | 0 |
| inverse | post | 82 | 1 | 0 |

Deflated Sharpe: N = 336 trials; V(full) = 7.949e-04, V(post) = 1.178e-03 (variance of per-day Sharpe across trials); SR0 annualised: full 1.31, post 1.60.

## Top 25 (pair, rule) rows by DSR (max of DSR_full, DSR_post)

| pair | rule | SR full | SR post | SR pre | maxDD full | maxDD post | RT full | RT post | BH p full | BH p post | DSR full | DSR post | cover | fail(a) | fail(b) | pass |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NTR_DE | coint_ols | 0.67 | 0.94 | n/a | 0.18 | 0.15 | 25 | 21 | 0.7772 | 1.0000 | 0.044 | 0.075 | 0.68 | 5 | 3 | no |
| RRC_CRK | rotation | 0.05 | 0.87 | -0.02 | 0.76 | 0.27 | 235 | 88 | 1.0000 | 1.0000 | 0.000 | 0.055 | 1.00 | 5 | 4 | no |
| BTU_EQT | rotation | 0.72 | 0.64 | -1.57 | 0.47 | 0.32 | 160 | 103 | 1.0000 | 1.0000 | 0.050 | 0.019 | 0.75 | 7 | 4 | no |
| SLV_SILJ | leadlag | 0.34 | 0.78 | -0.21 | 0.18 | 0.12 | 145 | 67 | 0.2246 | 1.0000 | 0.001 | 0.039 | 1.00 | 5 | 3 | no |
| YPF_VIST | leadlag | 0.54 | 0.51 | n/a | 0.22 | 0.22 | 52 | 50 | 0.9279 | 1.0000 | 0.039 | 0.008 | 0.50 | 7 | 4 | no |
| ET_EPD | coint_ols | 0.22 | 0.70 | 0.40 | 0.28 | 0.08 | 45 | 21 | 1.0000 | 0.9767 | 0.001 | 0.025 | 1.00 | 6 | 3 | no |
| AR_DOW | coint_kalman | 0.45 | 0.56 | n/a | 0.09 | 0.05 | 26 | 19 | 1.0000 | 0.2211 | 0.020 | 0.010 | 0.55 | 6 | 4 | no |
| ALB_TSLA | rotation | 0.43 | 0.66 | 0.18 | 0.39 | 0.35 | 228 | 113 | 1.0000 | 1.0000 | 0.003 | 0.020 | 1.00 | 6 | 4 | no |
| WLK_LYB | coint_ols | 0.37 | 0.68 | 0.55 | 0.23 | 0.10 | 46 | 23 | 0.8919 | 1.0000 | 0.001 | 0.018 | 1.00 | 6 | 3 | no |
| OKE_TRGP | coint_ols | 0.07 | 0.63 | -0.74 | 0.29 | 0.12 | 33 | 20 | 0.7882 | 0.6586 | 0.000 | 0.016 | 1.00 | 6 | 3 | no |
| NTR_MOS | coint_ols | 0.45 | 0.58 | n/a | 0.16 | 0.16 | 27 | 20 | 1.0000 | 1.0000 | 0.012 | 0.012 | 0.68 | 6 | 3 | no |
| CTVA_FMC | leadlag | 0.40 | 0.56 | n/a | 0.11 | 0.11 | 68 | 62 | 1.0000 | 1.0000 | 0.012 | 0.006 | 0.53 | 6 | 3 | no |
| CCJ_UEC | coint_ols | 0.63 | 0.23 | 0.48 | 0.33 | 0.33 | 47 | 24 | 0.2515 | 0.8687 | 0.011 | 0.001 | 1.00 | 6 | 4 | no |
| BTU_EQT | leadlag | -0.25 | 0.55 | 0.30 | 0.94 | 0.34 | 122 | 47 | 0.0161 | 0.1943 | 0.000 | 0.011 | 0.75 | 6 | 4 | no |
| XOM_MTDR | rotation | 0.32 | 0.54 | -0.83 | 0.55 | 0.13 | 231 | 95 | 1.0000 | 1.0000 | 0.001 | 0.010 | 1.00 | 6 | 3 | no |
| UUUU_DNN | coint_kalman | 0.07 | 0.50 | -0.39 | 0.34 | 0.18 | 95 | 50 | 0.8848 | 1.0000 | 0.000 | 0.008 | 1.00 | 6 | 3 | no |
| HCC_CLF | coint_ols | 0.36 | 0.48 | 1.57 | 0.57 | 0.40 | 28 | 14 | 1.0000 | 0.9589 | 0.005 | 0.008 | 0.73 | 7 | 5 | no |
| WY_RYN | coint_ols | 0.29 | 0.49 | -0.37 | 0.20 | 0.10 | 38 | 18 | 0.4319 | 0.5438 | 0.001 | 0.007 | 1.00 | 5 | 4 | no |
| CNR_CNX | coint_ols | -0.06 | 0.48 | -0.70 | 0.74 | 0.26 | 25 | 18 | 1.0000 | 0.3802 | 0.000 | 0.007 | 0.68 | 7 | 5 | no |
| FNV_RGLD | coint_ols | 0.29 | 0.47 | 0.02 | 0.21 | 0.15 | 39 | 18 | 1.0000 | 1.0000 | 0.001 | 0.006 | 1.00 | 6 | 4 | no |
| HCC_CLF | coint_kalman | 0.40 | 0.40 | 0.62 | 0.17 | 0.14 | 65 | 41 | 1.0000 | 0.9589 | 0.006 | 0.003 | 0.73 | 6 | 3 | no |
| HCC_CLF | leadlag | 0.37 | 0.31 | 1.50 | 0.34 | 0.34 | 126 | 68 | 0.1704 | 0.8919 | 0.006 | 0.002 | 0.73 | 7 | 4 | no |
| USO_JETS | rotation | -0.16 | 0.44 | -0.85 | 0.73 | 0.32 | 241 | 119 | 1.0000 | 0.1488 | 0.000 | 0.006 | 0.93 | 6 | 4 | no |
| VST_NRG | rotation | -0.02 | 0.42 | 0.73 | 0.50 | 0.23 | 190 | 98 | 1.0000 | 1.0000 | 0.000 | 0.005 | 0.78 | 7 | 4 | no |
| TSN_PPC | coint_ols | 0.20 | 0.43 | -0.16 | 0.22 | 0.17 | 42 | 20 | 0.7202 | 0.8919 | 0.000 | 0.005 | 1.00 | 6 | 3 | no |

Gate values for the top 10 (why they fail):

- **NTR_DE / coint_ols**: rule(a) fails: full Sharpe 0.666 < 1.0; BH p full 0.7772 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.044 < 0.95; coverage 0.676 < 0.8 || rule(b) fails: post Sharpe 0.942 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.075 < 0.95
- **RRC_CRK / rotation**: rule(a) fails: full Sharpe 0.050 < 1.0; full maxDD 0.757 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe 0.874 < 1.0; post maxDD 0.272 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.055 < 0.95
- **BTU_EQT / rotation**: rule(a) fails: full Sharpe 0.720 < 1.0; post Sharpe 0.639 < 0.8; full maxDD 0.473 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.050 < 0.95; coverage 0.751 < 0.8 || rule(b) fails: post Sharpe 0.639 < 1.0; post maxDD 0.320 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.019 < 0.95
- **SLV_SILJ / leadlag**: rule(a) fails: full Sharpe 0.339 < 1.0; post Sharpe 0.779 < 0.8; BH p full 0.2246 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.779 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.039 < 0.95
- **YPF_VIST / leadlag**: rule(a) fails: full Sharpe 0.538 < 1.0; post Sharpe 0.513 < 0.8; full maxDD 0.220 > 0.2; BH p full 0.9279 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.039 < 0.95; coverage 0.502 < 0.8 || rule(b) fails: post Sharpe 0.513 < 1.0; post maxDD 0.220 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.008 < 0.95
- **ET_EPD / coint_ols**: rule(a) fails: full Sharpe 0.224 < 1.0; post Sharpe 0.703 < 0.8; full maxDD 0.283 > 0.2; BH p full 1.0000 >= 0.05; BH p post 0.9767 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.703 < 1.0; BH p post 0.9767 >= 0.05; DSR post 0.025 < 0.95
- **AR_DOW / coint_kalman**: rule(a) fails: full Sharpe 0.451 < 1.0; post Sharpe 0.563 < 0.8; BH p full 1.0000 >= 0.05; BH p post 0.2211 >= 0.05; DSR full 0.020 < 0.95; coverage 0.552 < 0.8 || rule(b) fails: post Sharpe 0.563 < 1.0; post round trips 19 < 20; BH p post 0.2211 >= 0.05; DSR post 0.010 < 0.95
- **ALB_TSLA / rotation**: rule(a) fails: full Sharpe 0.429 < 1.0; post Sharpe 0.657 < 0.8; full maxDD 0.391 > 0.2; BH p full 1.0000 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.003 < 0.95 || rule(b) fails: post Sharpe 0.657 < 1.0; post maxDD 0.351 > 0.2; BH p post 1.0000 >= 0.05; DSR post 0.020 < 0.95
- **WLK_LYB / coint_ols**: rule(a) fails: full Sharpe 0.368 < 1.0; post Sharpe 0.679 < 0.8; full maxDD 0.233 > 0.2; BH p full 0.8919 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.679 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.018 < 0.95
- **OKE_TRGP / coint_ols**: rule(a) fails: full Sharpe 0.072 < 1.0; post Sharpe 0.630 < 0.8; full maxDD 0.289 > 0.2; BH p full 0.7882 >= 0.05; BH p post 0.6586 >= 0.05; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe 0.630 < 1.0; BH p post 0.6586 >= 0.05; DSR post 0.016 < 0.95

## Closest to passing

Ranked by fewest failed gates under the better of rules (a)/(b), ties broken by DSR. Gate counts can flatter a row with a negative Sharpe that happens to clear the drawdown, trade-count and p-value gates, so read this together with the DSR ranking above.

- **BHP_RIO / leadlag** (rule (a) fails 5 gates, rule (b) fails 2): rule(a) fails: full Sharpe -0.888 < 1.0; post Sharpe -0.643 < 0.8; full maxDD 0.359 > 0.2; BH p full 0.0509 >= 0.05; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe -0.643 < 1.0; DSR post 0.000 < 0.95
- **GDX_GDXJ / coint_kalman** (rule (a) fails 5 gates, rule (b) fails 2): rule(a) fails: full Sharpe -0.589 < 1.0; post Sharpe -1.408 < 0.8; full maxDD 0.216 > 0.2; BH p full 0.7457 >= 0.05; DSR full 0.000 < 0.95 || rule(b) fails: post Sharpe -1.408 < 1.0; DSR post 0.000 < 0.95
- **NTR_DE / coint_ols** (rule (a) fails 5 gates, rule (b) fails 3): rule(a) fails: full Sharpe 0.666 < 1.0; BH p full 0.7772 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.044 < 0.95; coverage 0.676 < 0.8 || rule(b) fails: post Sharpe 0.942 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.075 < 0.95
- **SLV_SILJ / leadlag** (rule (a) fails 5 gates, rule (b) fails 3): rule(a) fails: full Sharpe 0.339 < 1.0; post Sharpe 0.779 < 0.8; BH p full 0.2246 >= 0.05; BH p post 1.0000 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.779 < 1.0; BH p post 1.0000 >= 0.05; DSR post 0.039 < 0.95
- **ET_EPD / coint_ols** (rule (a) fails 6 gates, rule (b) fails 3): rule(a) fails: full Sharpe 0.224 < 1.0; post Sharpe 0.703 < 0.8; full maxDD 0.283 > 0.2; BH p full 1.0000 >= 0.05; BH p post 0.9767 >= 0.05; DSR full 0.001 < 0.95 || rule(b) fails: post Sharpe 0.703 < 1.0; BH p post 0.9767 >= 0.05; DSR post 0.025 < 0.95

## Random-pair baseline

500 random pairs (seed 20261027) from tickers that pass data QA, liquidity and rule-(b) history, excluding the candidate pairs; each run with the same engine, costs and walk-forward grid. Percentile = share of baseline Sharpe ratios at or below the candidate's, for the same rule (baseline exists for coint_ols and rotation only).

| rule | window | n_runs | n_defined | mean | std | p05 | p25 | median | p75 | p95 | p99 | max | frac_ge_1 | frac_ge_0p8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| coint_ols | full | 500 | 497 | 0.01 | 0.31 | -0.52 | -0.18 | 0.01 | 0.20 | 0.48 | 0.74 | 1.35 | 0.006 | 0.010 |
| coint_ols | post | 500 | 494 | 0.03 | 0.43 | -0.69 | -0.25 | 0.03 | 0.33 | 0.72 | 0.98 | 1.39 | 0.008 | 0.038 |
| rotation | full | 500 | 500 | -0.29 | 0.41 | -0.94 | -0.54 | -0.30 | 0.01 | 0.37 | 0.59 | 0.81 | 0.000 | 0.002 |
| rotation | post | 500 | 500 | -0.37 | 0.48 | -1.18 | -0.68 | -0.32 | -0.06 | 0.34 | 0.79 | 1.05 | 0.004 | 0.010 |

Baseline percentile of the top-10 rows (where a baseline exists):

| pair_id | rule | full_sharpe | full_sharpe_baseline_pctile | post_sharpe | post_sharpe_baseline_pctile |
|---|---|---|---|---|---|
| NTR_DE | coint_ols | 0.67 | 98.0 | 0.94 | 98.6 |
| RRC_CRK | rotation | 0.05 | 79.6 | 0.87 | 99.4 |
| BTU_EQT | rotation | 0.72 | 99.8 | 0.64 | 98.4 |
| SLV_SILJ | leadlag | 0.34 | n/a | 0.78 | n/a |
| YPF_VIST | leadlag | 0.54 | n/a | 0.51 | n/a |
| ET_EPD | coint_ols | 0.22 | 76.3 | 0.70 | 94.5 |
| AR_DOW | coint_kalman | 0.45 | n/a | 0.56 | n/a |
| ALB_TSLA | rotation | 0.43 | 96.2 | 0.66 | 98.4 |
| WLK_LYB | coint_ols | 0.37 | 87.7 | 0.68 | 93.9 |
| OKE_TRGP | coint_ols | 0.07 | 57.1 | 0.63 | 92.9 |

## Buy-and-hold reference

SPY total-return buy-and-hold over 2016-10-03 -> 2026-10-26: CAGR 15.21%, Sharpe 0.88, max drawdown 33.7%. Per-pair leg and SPY buy-and-hold figures are in `baseline_buyhold.csv`.

## Data and implementation caveats

- QA: 4 unresolved error row(s) (CHRD, CPER, GNK, NXE); 67 warning row(s); see `data_qa.csv`.
- Survivorship bias: the universe is built from tickers that still trade; the random baseline carries the same bias.
- See `IMPLEMENTATION_NOTES.md` for every deviation and judgement call, and `sanity_checks.md` for the auto-generated cross-checks.
