# Review protocol: red team and council

Every candidate must clear both stages before it becomes a pick. Candidates reach review one at a time, best first, from the pool that passes the quantitative gates (`backtest/results/gates.csv`, `quant_pass = True`).

## Stage 1: Red team
**Who:** one agent per candidate, in a fresh context.
- It sees the code, data, results and specs.
- It does **not** see the quant's own notes (`IMPLEMENTATION_NOTES.md`) or the lead's reasoning.

**Mandate:** try to break the candidate. Each finding is rated **FATAL**, **MAJOR** or **MINOR**, and every check must be backed by code the red team actually ran. Checks:
1. **Look-ahead and leakage.**
   - Read the engine.
   - Re-run with an extra one-day signal delay. A Sharpe collapse suggests timing leakage or fragility.
2. **Overfitting and fragility.** Sweep entry threshold 1.5/2.5 and z-score lookback 40/90. This is for reporting only; the parameters never change.
3. **Outlier dependence.**
   - Remove the best month, and separately the best 5 trades, then recompute Sharpe.
   - Break results out by calendar year.
4. **Costs.** Double them. Add plausible hard-to-borrow fees for the actual legs.
5. **Data errors.** Spot-check prices around the largest P&L days against the split and dividend data.
6. **Liquidity, borrow and capacity.** Average daily volume, crowding, and short-squeeze history of each leg.
7. **Common factor.**
   - Regress strategy returns on SPY, XLE, GDX, XME, GLD and USO.
   - Check whether the "relationship" is just both legs tracking one factor.
   - Check whether the residual alpha survives.
8. **Regime dependence.** Look at results by regime, and at whether one period drives everything.

**Output:** `research/redteam/<pair>_<rule>.md`, containing:
- the findings table;
- the code that was run, under `research/redteam/code/`;
- a verdict: `SURVIVES`, `SURVIVES WITH CAVEATS` or `BROKEN`.

**What happens with the verdict:**
- **BROKEN** (any FATAL finding that the lead confirms): the candidate is rejected.
- **A real bug in the engine:** it is fixed and **all** candidates are re-run.

## Stage 2: Council
**Who:** five independent reviewers, all launched in parallel. None can see another's score.

**What each reviewer reads:**
- the draft dossier;
- the red-team report;
- `gates.csv` and the trial files.

**Roles, each scoring 1–5 with a written rationale:**
1. **Quantitative researcher:** statistical validity, multiple-testing adequacy, out-of-sample (OOS) integrity.
2. **Commodity market analyst:** whether the economic mechanism and supply-chain logic are real and durable.
3. **Risk manager:** drawdowns, tail risk, crowding, short-squeeze risk, and correlation with existing picks.
4. **Execution / microstructure trader:** liquidity, slippage realism, borrow availability, and open-auction fills.
5. **Skeptic:** argues it is noise or luck and scores how well that argument is rebutted.

**Scoring anchors:**
| Score | Meaning |
|---|---|
| 5 | Compelling; I would allocate capital |
| 4 | Sound; minor concerns |
| 3 | Acceptable but material doubts |
| 2 | Serious flaws |
| 1 | Reject |

**Approval:** the average score must be ≥ 4.0 **and** no score may be below 3.

**Output:** `research/council/<candidate>/<role>.md`, ending with a machine-readable line `SCORE: n`.

## After approval
- Write the final dossier, `dossiers/pick_N_<A>_<B>.md`.
- Commit it.
- **Exclusion rules for later picks:**
  - drop any candidate sharing a leg with an existing pick;
  - drop any candidate whose daily OOS strategy returns correlate > 0.5 with an existing pick's returns over overlapping dates.
- **Next candidate:** the highest-ranked survivor, with a preference for commodity groups not yet represented.
