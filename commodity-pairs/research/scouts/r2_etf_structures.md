# Round 2 scouting: ETF and index structures tied to commodities

Eight candidate pairs, all typed `coint` with expected positive correlation. No leadlag or inverse pairs are proposed: I could not find a 1–10 day lag mechanism that survives in liquid commodity ETFs. The lagged channels (inventory, freight, capex guidance) run through single stocks or thin funds. Everything here is domain judgment, not tested. ADV, holdings weights and borrow levels are from memory and are estimates; verify against current fund files before use.

Considered and dropped:
- EWW/EWZ: Mexico's index is consumer, telecom and banks, so the commodity link is weak.
- EWC/XLE: Canadian banks are about a third of EWC, diluting the commodity link, and XLE has almost no Canadian exposure.
- XLE/XLB: a sector-rotation factor, not a structural tie.
- DBC/XLE: producer-vs-commodity-ETF type, which failed in Round 1.
- RYE/XLE and OIH/XES: same S&P 500 energy or services universe with different weights. The spread would be weight dispersion, but name overlap is near-complete, so rule (a) applies.
- IEO/XOP: both US E&P, overlap too high.
- GOEX, CRAK, WOOD: thin, likely below the $20M/day bar.
- GSG/DBC, GLD/IAU, XLE/VDE: avoided per rule (a).

## 1. XLE / XOP (coint, expected +)

- **Tickers:** XLE (leg A), XOP (leg B)
- **Type:** coint
- **Mechanism:** Both are US energy-equity wrappers driven by crude, but XLE is cap-weighted toward integrated majors and midstream, while XOP is equal-weighted E&P with much higher oil beta and small-cap beta. The spread isolates that mix factor and should anchor because both legs answer to the same crude cycle; it is wide enough to trade because XOP's small-cap beta moves the ratio several percent in a month. It breaks under a sustained small-cap or E&P-specific rerating (a consolidation premium or a gas-led E&P rally), or when majors buy E&P names and change both funds' composition.
- **Expected correlation sign:** +
- **Liquidity / borrow:** Both are among the most liquid sector ETFs (verify ADV; expected well above $20M/day). Both shortable. XOP's small-cap names may tighten borrow in stress (verify).
- **Holdings overlap:** Low by weight. XOP holds no XOM or CVX; shared E&P names (COP, EOG, OXY, DVN, FANG and similar) carry smaller weights in XLE. Rough estimate under 25% (verify).

## 2. XLE / IXC (coint, expected +)

- **Tickers:** XLE (leg A), IXC (leg B)
- **Type:** coint
- **Mechanism:** Both hold the same US supermajors, but IXC adds non-US integrateds (Shell, TotalEnergies, Equinor, plus state-linked Petrobras and PetroChina) and some Canadian producers. The spread therefore reflects USD translation against EUR, GBP, NOK, BRL and CAD, plus diverging capital-return policy (dividend-heavy European majors versus buyback-heavy US majors). Those differences are slow-moving, so the spread should anchor, but its size is modest and may not clear costs at size. It breaks under a USD move not matched by oil, or if a capital-return split persists.
- **Expected correlation sign:** +
- **Liquidity / borrow:** IXC is much thinner than XLE and may sit near or below the $20M/day bar (verify). XLE is well above. Both shortable; IXC itself can become hard-to-borrow in stress (verify).
- **Holdings overlap:** Meaningful but not extreme. XOM, CVX and COP recur; estimate 35–50% of IXC weight in names also held by XLE (verify). Judged overlapping, not identical, so it passes rule (a); the spread is driven by the non-US tail.

## 3. PICK / XME (coint, expected +)

- **Tickers:** PICK (leg A), XME (leg B)
- **Type:** coint
- **Mechanism:** PICK is global and cap-weighted toward diversified producers (iron ore, copper, gold, aluminum), while XME is US-listed and equal-weighted across steel, aluminum, coal and precious/copper names. The spread isolates a diversification-and-size factor plus a US steel and coal tilt; both legs respond to the same industrial-metals cycle, so the ratio should anchor, and equal-weight small caps move differently enough from global majors to make the spread tradeable. It breaks under US trade-policy shocks (steel tariffs, quotas), coal-specific shocks, or a large miner merger that reweights PICK.
- **Expected correlation sign:** +
- **Liquidity / borrow:** XME is well above the bar. PICK's ADV is uncertain and may sit near $20M/day (verify). Some XME small and coal names can be hard-to-borrow at times; check per-name borrow before sizing.
- **Holdings overlap:** Partial, estimate 20–30% by weight (FCX, NUE, STLD, AA recur; NEM possibly). Verify.

## 4. XLB / XME (coint, expected +, low confidence)

- **Tickers:** XLB (leg A), XME (leg B)
- **Type:** coint
- **Mechanism:** XLB is a materials sector fund dominated by chemicals and industrial gases (Linde is among its largest holdings), with a minority of miners; XME is an equal-weight metals-and-mining basket. They share a few producers (FCX, NUE, STLD, possibly NEM), so the spread is mostly a chemicals-versus-metals rotation. That makes cointegration weak: it may revert only over long windows and can trend in sector regimes. It breaks when a metals-only cycle (steel, aluminum, coal) decouples from chemicals, or when rates favor defensive chemical compounders.
- **Expected correlation sign:** +
- **Liquidity / borrow:** Both well above the bar (verify). Both shortable; XME small-name borrow as above.
- **Holdings overlap:** Low to moderate, estimate 15–25% by weight. Shared names are a minority of XLB and a larger share of XME. Verify.
- **Note:** On the team's list, but I would rank it last.

## 5. SIL / GDX (coint, expected +)

- **Tickers:** SIL (leg A), GDX (leg B)
- **Type:** coint
- **Mechanism:** Silver miners and gold miners both carry precious-metal exposure, but silver miners have higher operating leverage to silver and more base-metal by-product exposure, while GDX is weighted to gold majors. The spread encodes the gold/silver ratio times relative miner leverage; that ratio has mean-reverting tendencies over long windows, and silver miners move several times as much as gold miners on silver-specific days, so the spread is tradeable. It breaks in multi-year gold/silver regime shifts (the ratio has ranged very widely) or when industrial silver demand decouples silver from gold.
- **Expected correlation sign:** +
- **Liquidity / borrow:** GDX is very liquid. SIL is likely above $20M/day (verify). Some SIL junior and foreign-listed names may be hard-to-borrow at times; check per name.
- **Holdings overlap:** Low, under about 15% by weight. Most SIL silver producers are not in GDX, and GDX is gold-heavy. Verify.

## 6. COPX / XME (coint, expected +)

- **Tickers:** COPX (leg A), XME (leg B)
- **Type:** coint
- **Mechanism:** COPX is a global copper-miner basket (copper-weighted majors and developers, many non-US listings); XME is US steel, aluminum, coal and some precious/copper names. Both are metals equities, so the spread should anchor on the shared industrial-metals cycle, but copper demand (electrification, grid build-out) and US steel and coal (tariffs, domestic construction, coal policy) respond to different drivers, creating a tradeable tilt. It breaks under US tariff changes, coal-specific policy, or a copper supply shock (mine disruption in Chile, Peru or DRC) that moves COPX far from XME.
- **Expected correlation sign:** +
- **Liquidity / borrow:** XME is well above the bar. COPX is likely above $20M/day (verify). COPX holds foreign-listed names, so ETF-level borrow can tighten; XME small names may be hard-to-borrow at times.
- **Holdings overlap:** Low to moderate; FCX and possibly NEM recur, most names differ. The Anglo American–Teck combination announced in 2025 (verify close status) will reshape COPX weights.

## 7. EWA / EWC (coint, expected +)

- **Tickers:** EWA (leg A), EWC (leg B)
- **Type:** coint
- **Mechanism:** Both are developed-market commodity exporters whose currencies trade as commodity currencies, and both have large bank weights. Australia leans toward iron ore, copper and gold miners; Canada leans toward oil sands and pipelines, gold miners and banks. The spread should anchor on the shared commodity-currency factor, and the mix difference (China-linked iron ore versus North American energy) gives swings wide enough to trade. It breaks under a China-specific iron-ore shock that hits Australia alone, or a Canadian energy or pipeline shock that hits Canada alone.
- **Expected correlation sign:** +
- **Liquidity / borrow:** Both likely well above the bar (verify). Both shortable; no ETF-level hard-to-borrow issue expected.
- **Holdings overlap:** Near zero by name; overlap is at the factor level (banks, miners, commodity-currency beta).

## 8. EWZ / EWC (coint, expected +, low confidence)

- **Tickers:** EWZ (leg A), EWC (leg B)
- **Type:** coint
- **Mechanism:** Brazil is a commodity exporter (iron ore via Vale, oil via Petrobras, agriculture), but its index is dominated by banks, consumer and EM-specific names; Canada is a developed commodity exporter with energy and gold weights. The spread mostly captures EM-versus-developed risk appetite and BRL-versus-CAD translation layered on a commodity mix difference. It breaks in EM risk-off episodes, Brazilian fiscal or political shocks, or BRL moves not accompanied by commodity moves, so the commodity mapping is weaker than EWA/EWC.
- **Expected correlation sign:** +
- **Liquidity / borrow:** Both likely well above the bar (verify). Both shortable.
- **Holdings overlap:** Small by name. Vale and Petrobras are the Brazilian commodity names; Canada's energy and gold names are absent from EWZ.

## Closed/merged funds (survivorship)

None of the eight ETFs is known to have closed or merged; verify fund status. The survivorship risk sits in constituents and index methodology, so use point-in-time holdings in any backtest. Items to verify:

- Arch Resources (ARCH) and CONSOL Energy (CEIX) combined into Core Natural Resources (CNR) in January 2025; coal weights in XME and similar funds changed.
- US Steel (X) was taken private by Nippon Steel in 2025 and removed from steel and metals indices.
- E&P and integrated consolidation removed names from XOP, XLE and IXC: Pioneer (PXD) into Exxon (2024), Marathon Oil (MRO) into ConocoPhillips (2024), Hess (HES) into Chevron (2025), and Southwestern Energy (SWN) into Chesapeake, now Expand Energy (EXE), in 2024.
- Anglo American–Teck combination announced in 2025 (verify close status); affects COPX and PICK weights.
