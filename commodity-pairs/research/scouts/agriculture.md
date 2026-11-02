# Agriculture scout: candidate pairs

Snapshot: 2026-10-27. Domain reasoning only; no prices pulled, no backtests run. My knowledge of listings and corporate actions may be stale, so anything marked "verify" must be checked before use.

**Labels.** `inverse`: returns move in opposite directions, so the rule is a rotation. `coint`: legs co-move and the log spread mean-reverts. `leadlag`: leg_a leads leg_b by 1–10 trading days; expected_corr_sign is the sign of the lagged correlation.

**Liquidity.** ADV figures are order-of-magnitude guesses from memory, not measured. Futures-based ETFs (CORN, DBA) embed roll yield, so their returns are not spot returns; use total-return or underlying futures for a fair test.

**Count.** 9 pairs: 5 coint, 2 leadlag, 2 inverse.

**Considered and excluded.** CNH (NYSE ticker and listing changed; verify before use). SOYB and WEAT (ADV very likely below $20M). REX American (thin). ANDE (borderline ADV). Consumer-food names such as Kellanova and WK Kellogg (not ag-input exposure).

---

### 1. ADM / BG: `coint`, expected corr sign +

- **Legs:** ADM (NYSE), BG (NYSE).
- **Mechanism:** Both run the same model (origination, oilseed crush, merchandising, biofuel feedstocks), so both respond to the same crush-margin, export-basis and biofuel-policy factors (RVO, 45Z), which anchors the spread. The spread diverges on firm-specific news, such as ADM's 2024 disclosure of an accounting investigation in its Nutrition segment, and should revert only if that news was an overreaction.
- **What breaks it:** Bunge's share count, balance sheet and reporting perimeter changed with the Viterra acquisition, so expect a structural break; test for it before cointegration testing. A permanent change in ADM's mix (asset sales, restructuring) also shifts the hedge ratio.
- **Liquidity / borrow:** Both very likely above $100M ADV (verify). Both generally shortable.
- **Listing history:** ADM full history. Bunge re-domiciled from Bermuda to Switzerland around 2023 (verify) under the same ticker, and the Viterra merger closed in 2025 (verify). Check the vendor's splice before treating BG as continuous.

### 2. DE / AGCO: `coint`, expected corr sign +

- **Legs:** DE (NYSE), AGCO (NYSE).
- **Mechanism:** Both sell large farm machinery into the same farm-income cycle (crop prices, farmland values, interest rates, used-equipment inventories), so order books and multiples move together over the cycle. The spread diverges on mix: Deere is North American row-crop heavy, with a large captive finance arm and construction exposure, while AGCO is weighted to Europe and South America (Fendt, Massey Ferguson, Valtra).
- **What breaks it:** A North-America-only farm downturn or an EU-only shock; Deere's construction and forestry cycle; AGCO restructuring or portfolio moves.
- **Liquidity / borrow:** DE well above the bar. AGCO plausibly $50–100M ADV, so it is a borderline pass (verify). Both shortable.
- **Listing history:** Both full history. Fiscal calendars differ (Deere's fiscal year ends around early November; AGCO reports on a calendar year), so earnings-day jumps will not line up. Strip event days.

### 3. CF / NTR: `coint`, expected corr sign +

- **Legs:** CF (NYSE), NTR (NYSE; also TSX).
- **Mechanism:** Both are fertilizer producers whose profits depend on farm nutrient demand and global benchmark prices, so they share a long-run demand factor. They differ in input exposure: CF is close to pure gas-to-ammonia, so US natural gas spikes compress its margin, whereas Nutrien's potash segment is largely gas-independent and its retail arm dilutes the price cycle.
- **What breaks it:** Natural gas shocks (hit CF's conversion margin harder than NTR's); Chinese or Indian export policy on urea and phosphate; potash contract resets that decouple the potash cycle from nitrogen.
- **Liquidity / borrow:** Both liquid. Use the NYSE series for NTR. Both shortable.
- **Listing history:** CF full history. The Nutrien entity dates from the January 2018 PotashCorp and Agrium merger, so an NTR-only series may start in 2018 (verify). Without a vendor splice of POT/AGU history, the sample shrinks to about eight years.

### 4. NTR (leader) to MOS (follower): `leadlag`, expected corr sign +

- **Legs:** NTR (leader), MOS (follower).
- **Mechanism:** Nutrien is the largest potash producer, and its commentary on potash prices and volumes is a major input to how the market prices the potash benchmark. Mosaic sells into the same benchmark through its potash business (Canada and New Mexico) but is smaller and more phosphate-heavy, so its equity may reprice the same news over one to five trading days through sell-side read-through and slower rebalancing.
- **Test:** NTR return on day t against MOS return on days t+1 through t+10.
- **What breaks it:** Earnings-window coincidence (if both report in the same week the link is contemporaneous, not lagged); phosphate-specific shocks from sulfur and ammonia costs or Chinese export quotas; a flat potash market gives no signal.
- **Liquidity / borrow:** Both liquid (verify). Both shortable.
- **Listing history:** MOS full history. NTR as in pair 3.

### 5. TSN (leader) to PPC (follower): `leadlag`, expected corr sign +

- **Legs:** TSN (leader), PPC (follower). PPC trades on Nasdaq.
- **Mechanism:** Tyson is the largest US chicken, beef and pork processor, and its chicken commentary (pricing, broiler supply, feed cost) is a sector read-through for Pilgrim's, which is almost pure chicken and more sensitive to the US broiler cycle. Investors may reprice Pilgrim's over several days after Tyson's chicken news, so a positive lagged correlation at 1–5 days is plausible.
- **Test:** TSN return on day t against PPC returns on days t+1 through t+5.
- **What breaks it:** Earnings timing (if Pilgrim's reports in the same week as Tyson, drop those days); Tyson's beef and pork cycle differs from chicken; Pilgrim's has larger Mexico and Europe exposure.
- **Liquidity / borrow:** TSN liquid. PPC plausibly $30–80M ADV (verify). Check PPC borrow fee.
- **Listing history:** Both full history.

### 6. PPC vs DBA: `inverse`, expected corr sign -

- **Legs:** PPC (Nasdaq), DBA (NYSE Arca).
- **Mechanism:** Corn and soybean meal are the largest broiler cost, so when grain prices rise faster than chicken prices Pilgrim's margin compresses and the two legs should move in opposite directions over short rotations. DBA holds corn, soybeans, wheat and sugar, so its corn and soy weights roughly track a feed-cost proxy, though wheat and sugar add noise.
- **What breaks it:** Weather or demand shocks that push both legs the same way; contract feed pass-through lags; DBA's futures roll yield.
- **Liquidity / borrow:** DBA borderline ADV (plausibly $20–40M, verify). Generally shortable (verify). CORN is a tighter corn-only alternative but very likely below $20M ADV.
- **Listing history:** PPC full history. DBA full history back to 2007.

### 7. GPRE vs CORN: `inverse`, expected corr sign -

- **Legs:** GPRE (Nasdaq), CORN (NYSE Arca, Teucrium).
- **Mechanism:** Corn is the dominant input for dry-mill ethanol producers, so a corn rally without an offsetting ethanol price rise compresses the ethanol crush margin and pushes GPRE down. Ethanol prices are tied mainly to gasoline and RIN values, so a corn-led shock should dominate short-term correlation.
- **What breaks it:** Corn and ethanol both rise on weather or farm-economy shocks (positive correlation); policy shocks (RVO, E15 waivers, 45Z) overwhelm the margin channel; CORN roll yield.
- **Liquidity / borrow:** CORN very likely below $20M ADV and futures-based. This is the weakest liquidity pair. GPRE probably passes ADV (verify) but has historically elevated short interest, so check the borrow fee.
- **Listing history:** GPRE full history. CORN launched 2010 (verify current status).

### 8. CTVA / FMC: `coint`, expected corr sign +

- **Legs:** CTVA (NYSE), FMC (NYSE).
- **Mechanism:** Both sell crop protection into the same acreage and pricing cycle, shaped by generic-chemical supply from China and India, channel destocking and patent expiries, which gives a shared factor. The spread diverges because Corteva is mostly seed (the majority of its revenue) while FMC is a pure-play chemistry company, so it tracks the seed-versus-chemistry margin cycle.
- **What breaks it:** FMC-specific events (2025 guidance cuts, portfolio sales, dividend changes); a weak long-run relation may cause cointegration to fail outright.
- **Liquidity / borrow:** CTVA well above the bar. FMC likely passes (verify). Both shortable.
- **Listing history:** CTVA only since June 2019, when it spun out of DowDuPont, so about seven years of history, which may be too short. My understanding is that Corteva announced in late 2025 a plan to separate into seed and crop-protection companies, targeted for the second half of 2026 (verify). If that happened, the CTVA series is discontinuous. FMC has full history.

### 9. MOO / ADM: `coint`, expected corr sign +

- **Legs:** MOO (NYSE Arca, VanEck Agribusiness ETF), ADM (NYSE). Low priority.
- **Mechanism:** MOO is an agribusiness equity basket that holds ADM and other ag names, so ADM's price should track the sector's long-run earnings expectations, and a stock that drifts far from the basket on idiosyncratic news may revert.
- **What breaks it:** ADM is a large MOO constituent, so the spread contains ADM's own weight and is partly mechanical. Sector rotation and ADM's governance or accounting news dominate.
- **Liquidity / borrow:** MOO borderline ADV (plausibly $10–30M, verify). Both shortable. Treat as a diagnostic or drop it.
- **Listing history:** MOO full history back to 2007.

---

## Merged / delisted names (survivorship)

A backtest on today's tickers would miss these. Dates are from memory; verify.

- **PotashCorp (POT, NYSE) and Agrium (AGU, NYSE):** merged into Nutrien (NTR) effective 1 January 2018. Both delisted.
- **Monsanto (MON, NYSE):** acquired by Bayer, closed June 2018. Bayer's US access is via OTC ADR, not NYSE common.
- **DowDuPont (DWDP, NYSE):** split in 2019 into Dow (DOW), DuPont (DD) and Corteva (CTVA). DWDP delisted. CTVA trading starts June 2019.
- **Syngenta (SYT, NYSE ADR):** NYSE ADR delisted after the ChemChina takeover (2017, verify).
- **Sanderson Farms (SAFM, Nasdaq):** taken private by Cargill and Continental Grain, closed 2022. Delisted. Lost protein peer for TSN and PPC-style pairs.
- **Dean Foods (DF, NYSE):** Chapter 11 in 2019, delisted. Adjacent dairy.
- **Renewable Energy Group (REGI, Nasdaq):** agreed acquisition by Chevron in 2025. Delisted if the deal closed (verify). Lost biofuel peer.
- **Smithfield Foods (SFD):** taken private by WH Group in 2013; relisted on Nasdaq in 2025 (verify). No public listing 2013–2024, so any test on it is survivorship-biased.
- **Viterra:** privately held Canadian grain merchant with no US listing; absorbed into Bunge in 2025 (verify). It cannot appear in any test.
- **Private majors (Cargill, Louis Dreyfus, COFCO, Scoular):** never listed in the US, so the merchant peer set is inherently survivorship-limited.
- **Bunge (BG):** not a delisting, but the 2023 re-domicile and the Viterra merger are corporate actions that break series continuity (see pair 1).
