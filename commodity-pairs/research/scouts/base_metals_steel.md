# Base metals, iron ore and steel: pair scouting (as of 2026-10-27)

Scope: 10 candidate pairs across copper miners, diversified and iron-ore majors, US steel, aluminum, met coal and mining equipment. This is economic reasoning only: no price data pulled, no statistics run, no code. Tickers, listing dates and liquidity come from memory and are marked "verify" where unsure. The quant team should confirm them in code. Liquidity figures are rough orders of magnitude, not measurements.

Universe rules applied: NYSE, NYSE Arca and Nasdaq listings only (ADRs OK). OTC-only ADRs were excluded: Anglo American (AAUKY), Glencore (GLNCY), First Quantum (FQVLF), Lundin Mining (LUNMF).

Considered but not included, because of the 10-pair cap: ETN or HUBB vs COPX (electrification demand vs copper), and FCX vs COPX (COPX holds FCX, so that pair is partly mechanical).

Conventions: coint spreads are log(A) minus beta times log(B), with beta estimated by the quant team. For leadlag pairs the leader is leg_a. Expected signs are what the mechanism predicts, not what the data will show; market beta often overrides inverse logic in practice.

## Pairs

### 1. FCX / SCCO: coint
- Mechanism: Both are large porphyry copper producers with copper-driven earnings and similar cost curves, so the copper price anchors them together. Asset-specific shocks (FCX Indonesian operations; SCCO Peru and Mexico policy) should widen the spread temporarily. The main failure mode is a permanent reset, such as a lasting operational loss at one company, which stops reversion.
- Expected return correlation sign: +
- Liquidity and borrow: Both NYSE and highly liquid. SCCO is majority-controlled by Grupo Mexico, so free float and borrow are thinner than volume suggests. Check float-adjusted ADV.

### 2. BHP / RIO: coint
- Mechanism: Both are Anglo-Australian diversified miners whose largest earnings line is iron ore, so Chinese steel demand and Pilbara costs tie them together. Their mixes differ (BHP: copper, potash, petroleum; RIO: aluminum, lithium, borates), so the spread reflects portfolio-mix and capital-allocation moves that tend to reverse. The break risk is corporate action: asset sales, or reported Rio Tinto and Glencore merger discussions in early 2026 (verify).
- Expected return correlation sign: +
- Liquidity and borrow: Both NYSE ADRs with very high volume and easy borrow. The BHP ADR represents two ordinary shares; a constant ratio is absorbed by the intercept, but confirm the ADR ratio in the data.

### 3. NUE / STLD: coint
- Mechanism: Both are large US scrap-based mini-mill steelmakers facing the same domestic hot-rolled coil price, scrap cost, Section 232 tariff regime and construction and auto demand. Similar cost structures bound their relative margins. The spread widens on product mix (STLD's aluminum division and flat-rolled investment versus Nucor's larger steel products and raw-materials business) and on company-specific capacity news.
- Expected return correlation sign: +
- Liquidity and borrow: Both highly liquid (NUE on NYSE, STLD on Nasdaq). Easy borrow.

### 4. VALE / MT: coint (upstream iron ore vs downstream steel margin)
- Mechanism: VALE is close to a pure iron ore producer (with nickel and copper), and ArcelorMittal is a global steelmaker with partial captive ore, so the ratio approximates the iron ore-to-steel margin. That margin mean-reverts because high ore prices squeeze steel producers and weak ore prices restore their spread. Breakdowns come from VALE-specific operational or dam risk, and from MT's European carbon costs and regional demand.
- Expected return correlation sign: +
- Liquidity and borrow: Both NYSE with high volume. Verify MT's listed share class and ADV. VALE borrow is generally available; check fees under stress.

### 5. CPER / COPX: coint (copper futures proxy vs miner equities)
- Mechanism: CPER tracks front-month copper futures, while COPX holds global copper miners whose equities carry leveraged copper beta plus equity-market beta and cost-curve effects. Miner margins anchor the long-run ratio, so divergences from sentiment or cost inflation should partly revert. Contango roll drag in CPER is a systematic drift the model must handle.
- Expected return correlation sign: +
- Liquidity and borrow: COPX is liquid. CPER is the main liquidity risk: its volume may fall below $20M ADV (verify). If it fails, drop the pair rather than substituting a futures contract, which is outside this universe. CPER history starts Nov 2011; COPX starts 2010.

### 6. HCC / CLF: inverse (met coal cost vs integrated steel)
- Mechanism: Met coal is a direct cost input for blast-furnace steel. A coking-coal price spike lifts HCC, a premium hard coking coal producer, while squeezing margins at blast-furnace producers such as Cleveland-Cliffs, which buys coal and runs integrated assets acquired with AK Steel. EAF-based peers are much less exposed. The expected rotation is HCC up and CLF down on coal shocks. In practice, US tariff news and broad market beta can flip the sign.
- Expected return correlation sign: -
- Liquidity and borrow: CLF is very liquid. HCC volume is moderate (verify ADV). HCC's listed history starts with its March 2017 IPO (the predecessor Walter Energy equity was cancelled), so Oct 2016 is missing, about 9.5 of the 10 years. CLF's business changed materially after the AK Steel deal (2020), so test around regime breaks.

### 7. CENX / BALL: inverse (aluminum policy: producer vs can maker)
- Mechanism: Section 232 aluminum tariffs and the Midwest premium raise domestic aluminum costs for can makers while lifting revenue at US primary smelters such as Century. Policy and aluminum-price shocks should therefore push the two legs in opposite directions. Ball's metal pass-through contracts dampen and lag the effect, so the signal should concentrate on policy-announcement days.
- Expected return correlation sign: -
- Liquidity and borrow: BALL is highly liquid. CENX ADV is adequate, but it has historically carried high short interest and borrow-fee spikes; check borrow before any trade. Crown Holdings (CCK) is a possible alternate consumer leg.

### 8. AA -> CENX: leadlag (leader AA)
- Mechanism: Alcoa is larger, more widely covered, and reprices aluminum and Midwest-premium news first. Smaller primary smelter Century catches up over several trading days as analyst revisions and flows diffuse. This is a large-to-small industry lead-lag mechanism. Breaks come from Century-specific restart or hedging news and from Alcoa's alumina and bauxite exposure.
- Expected return correlation sign: +
- Liquidity and borrow: AA on NYSE is liquid. CENX ADV and borrow need checking. History: AA's listed series starts with the Nov 1, 2016 spin-off. Pre-spin prices belong to the old Alcoa Inc (now Howmet, HWM), so Oct 2016 AA data is not comparable. Test 1 to 10 day lags only.

### 9. FCX -> HBM: leadlag (leader FCX)
- Mechanism: FCX is the US copper bellwether with much deeper coverage and index weight, so sector-level copper news and flows reach it first. Smaller producer Hudbay (Constancia in Peru, Copper World in Arizona) reprices with a lag as revisions and fund rebalancing reach it. The lead-lag should weaken in large-cap-driven rallies and break on Hudbay-specific news.
- Expected return correlation sign: +
- Liquidity and borrow: HBM volume is borderline against the $20M ADV screen (verify). HBM is also TSX-listed, so arbitrage supports price but not necessarily the lag. Verify the NYSE listing start date and borrow.

### 10. CAT / COPX: coint (mining capex vs miner equities)
- Mechanism: Caterpillar's Resource Industries sells haul trucks, shovels and parts to miners, whose capex and fleet replacement follow metal prices with a lag of several quarters. That capex link anchors the long-run ratio against the miner basket. The weakness is that CAT's power-generation and data-center demand and general industrial beta can dominate, causing persistent drift instead of reversion.
- Expected return correlation sign: +
- Liquidity and borrow: Both very liquid, with easy borrow. Lowest-confidence pair in this set; include mainly for breadth and as a control on the copper-equity factor.

## Merged, delisted and renamed names (survivorship)

All dates and tickers from memory; verify before use. A backtest universe built from today's listings would omit the first group.

Merged or delisted (relevant to this group):
- United States Steel (X, NYSE): acquired by Nippon Steel, closed June 2025, delisted.
- AK Steel (AK, NYSE): acquired by Cleveland-Cliffs, closed March 2020.
- Arconic Corporation (ARNC, NYSE): acquired by Apollo, closed 2023. Not the same entity as Howmet (HWM), which was the old Arconic Inc parent of the pre-spin Alcoa.
- Noranda Aluminum (NOR, NYSE): Chapter 11 in February 2016, equity cancelled. Not trading at the window start.
- Alpha Natural Resources (ANR, NYSE): Chapter 11 in 2015 and 2016; equity cancelled. Met coal peer not in the window.
- Walter Energy (WLT, NYSE): Chapter 11 in 2015. Its Alabama met coal assets became Warrior Met Coal (HCC), which listed only in March 2017.
- Joy Global (JOY, Nasdaq): acquired by Komatsu, 2017 (verify). Mining equipment peer for pair 10.
- General Cable (BGC, NYSE): acquired by Prysmian, 2018. Copper cable.
- Global Brass & Copper (BRSS, NYSE): acquired by Wieland, 2019. Copper products.
- Anixter (AXE, NYSE): acquired by WESCO, 2020. Copper-intensive electrical distribution.
- Encore Wire (WIRE, Nasdaq): acquired by Prysmian, 2024. Copper wire.
- Haynes International (HAYN, Nasdaq): acquired by Acerinox, 2024 (verify). Nickel alloys.
- Bucyrus International (BUCY): acquired by Caterpillar, 2011. Pre-window.

Renamed or entity-changed (still listed, but history must be linked):
- Cliffs Natural Resources to Cleveland-Cliffs (CLF retained; business model changed after 2014 and the 2020 AK Steel deal).
- Schnitzer Steel (SCHN) to Radius Recycling (RDUS), 2022 (verify).
- Contura Energy (CTRA) to Alpha Metallurgical Resources (AMR), 2021 (verify). AMR's history starts with the predecessor, around 2017.
- Arconic Inc to Howmet Aerospace (HWM), 2023. The ARNC symbol was later reused (verify).

Corporate-action watch (still listed, status may have changed):
- Teck Resources (TECK, NYSE): Anglo American and Teck combination announced September 2025. If completed, TECK may have been delisted or re-listed under a new name. Not used in any pair above, but check the universe.
- Rio Tinto and Glencore: reported merger discussions in early 2026 (verify). Affects RIO in pair 2.
