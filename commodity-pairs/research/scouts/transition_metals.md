# Energy-transition metals: uranium, lithium/battery, rare earths (scout, 2026-10-27)

Scope: uranium miners and ETFs, uranium fuel services, nuclear-heavy power producers, lithium producers, battery and EV consumers, and rare-earth producers. Candidates are chosen for economic logic. Nothing has been backtested or downloaded.

Caveat on tickers: tickers, listing venues and listing dates are from memory and were not checked against live listings. They are marked "verify" where uncertain. Dollar-volume estimates are rough tiers, not measured figures. The quant team should verify each ticker before use.

Coverage caveat: several of the most relevant US-listed names are recent listings, so they cannot cover the full Oct 2016 start. These include CEG (spun off from Exelon around Feb 2022), MP (listed 2020), URNM (launched around Dec 2019), NXE's US listing, and the 2024 SPAC-era nuclear names. Each pair below states its coverage limit.

Considered and excluded:
- Non-US primary listings with no usable US exchange leg: Kazatomprom (LSE), Paladin, Pilbara and Lynas (ASX), CATL (HKEX), Sprott Physical Uranium Trust (TSX). Their US access, if any, is OTC or thin.
- ETF versus its own largest holding (URA vs CCJ, LIT vs ALB). The ETF holds the stock by construction, so the relationship is mechanical.
- Pre-revenue SPAC-era names (QuantumScape, SES AI, Oklo, NuScale). Their history fails the 2016 window and their economics are not yet stable.
- Power pairs without nuclear exposure (for example, a gas IPP vs a regulated utility). These belong in a power or gas group.

Pair summary:

| # | Leg A (leader if leadlag) | Leg B | Type | Sign |
|---|---|---|---|---|
| 1 | CCJ | UEC | coint | + |
| 2 | URA | URNM | coint | + |
| 3 | CEG | VST | coint | + |
| 4 | CEG | CCJ | leadlag | + |
| 5 | LEU | CCJ | coint | + |
| 6 | ALB | SQM | coint | + |
| 7 | ALB | TSLA | inverse | - |
| 8 | MP | GM | inverse | - |
| 9 | NXE | CCJ | coint | + |
| 10 | UUUU | DNN | coint | + |

## Pairs

### 1. CCJ / UEC (coint, expected sign +)

- Legs: Cameco (NYSE) / Uranium Energy Corp (NYSE American).
- Mechanism: Both trade off the uranium spot and term price, so the spot factor is shared. Cameco's production is largely contracted and it has large fuel-services and reactor-services exposure through its Westinghouse stake, so its equity moves less than spot. UEC is a US in-situ-recovery developer with much higher beta to spot. The log spread should revert around a stable beta. It breaks on Cameco-specific operating or Westinghouse news, on UEC equity raises or project-stage changes, and in spot regimes where contracting dominates.
- Liquidity and borrow: CCJ is highly liquid with easy borrow. UEC is likely above the $20M threshold, but it has historically carried high short interest and episodic hard-to-borrow periods. Verify fee history. Both were listed before 2016.

### 2. URA / URNM (coint, expected sign +)

- Legs: Global X Uranium ETF / Sprott Uranium Miners ETF (both NYSE Arca; verify sponsors).
- Mechanism: Both hold uranium producers and developers, so they share the spot factor. They differ in weights and small-cap tilt: URA is more concentrated in larger producers, while URNM leans toward juniors and includes more non-US names (verify holdings). The spread should be roughly stationary around the relative small-cap premium. Economic conviction is low. The relationship is mostly index construction and fund flows, so this pair is most useful as a sanity check on whether single-name uranium spreads reflect more than index mechanics.
- Liquidity and borrow: Both are liquid, but URNM's ADV is closer to the threshold (verify). URNM launched around December 2019, so it truncates the Oct 2016 window. Borrow is generally available; verify. Check holdings history before use.

### 3. CEG / VST (coint, expected sign +)

- Legs: Constellation Energy (Nasdaq) / Vistra (NYSE).
- Mechanism: Both are large merchant power producers with significant nuclear fleets in PJM and ERCOT. They share the wholesale power-price and data-center demand factor and both have signed hyperscaler deals. The spread reflects Vistra's larger gas, coal and retail mix against Constellation's nuclear-heavy profile, and should revert around a stable relative valuation. It breaks on gas price spikes (which favour Vistra's gas fleet), on retail-margin shocks, and on deal announcements specific to one name.
- Liquidity and borrow: Both are very liquid with easy borrow. Constellation separated from Exelon around February 2022 (when-issued trading began in late January 2022; verify), so it fails the 2016 window. Vistra's continuous history starts with its 2018 merger with Dynegy, when the combined company began trading as VST (verify). Pre-2018 coverage needs Dynegy (DYN) history.

### 4. CEG to CCJ (leadlag, leader = CEG, expected sign +)

- Legs: Constellation (leader) / Cameco (follower).
- Mechanism: Hyperscaler nuclear contracts and restart or uprate announcements hit generator equities first, because they are direct cash-flow news for those companies. Uranium equities should re-rate later, as investors revise long-run nuclear fuel demand. The expected lag is 1 to 10 trading days, and a rule would buy CCJ after a large CEG up-day.
- Liquidity and borrow: Both are liquid. The lag may not exist if Cameco reprices the same day through sector-ETF flows or sentiment, so the quant team should test same-day controls. Constellation's short history makes the pair unusable before 2022. Vistra (VST) is a possible leader for pre-2022 testing, though it carries gas exposure that CEG does not.

### 5. LEU / CCJ (coint, expected sign +)

- Legs: Centrus Energy (NYSE American) / Cameco.
- Mechanism: Centrus sells enrichment services (SWU), a mid-stream step after mining and conversion. Cameco sells U3O8, the upstream commodity. Both respond to Russian supply restrictions and US import policy, so they share a supply-security factor. The spread should reflect the gap between SWU and U3O8 prices and their contracting cycles. Breaks come from enrichment-capacity news (for example, government enrichment or HALEU awards to Centrus), from Cameco contract resets, and from sustained U3O8 moves without SWU follow-through.
- Liquidity and borrow: LEU is smaller, and its ADV is moderate and may be borderline against $20M (verify). Borrow is moderate. Centrus was USEC Inc. (NYSE: USU) until its 2014 rename, so pre-2014 history maps to a different ticker and company.

### 6. ALB / SQM (coint, expected sign +)

- Legs: Albemarle (NYSE) / Sociedad Quimica y Minera (NYSE ADR).
- Mechanism: Both are large, low-cost lithium producers with Chilean brine exposure. Their earnings scale with lithium carbonate and hydroxide prices, so the common price factor is strong. Relative valuation is anchored by cost position and balance-sheet quality. Divergence comes from Albemarle's bromine and catalyst segments, SQM's iodine and plant-nutrition businesses, Chilean royalty and regulatory changes, and SQM's partnership structure with Codelco (verify terms and effective date). Breaks come from one-company events and from a regime change in lithium pricing.
- Liquidity and borrow: ALB is liquid with easy borrow. SQM is liquid, likely above $20M, with moderate borrow. Verify which ADR share series trades on the NYSE (we believe Series B), and check how dividends and the peso are treated in the price series.

### 7. ALB / TSLA (inverse, expected sign -, low confidence)

- Legs: Albemarle (NYSE) / Tesla (Nasdaq).
- Mechanism: Higher lithium prices raise battery costs for EV makers, and battery packs are a large share of EV cost. Tesla's margin compresses when the input price rises, while lithium producers gain from the same price. The implied relationship is negative on lithium-price shock days. In 2022, lithium's spike coincided with a Tesla drawdown, but that period was confounded by rates and EV sentiment.
- Liquidity and borrow: Both are very liquid. Tesla borrow is generally easy but fees vary. The unconditional correlation is usually positive because EV demand and sentiment dominate, so the inverse structure may hold only when conditioned on lithium-price moves. Tesla's in-house cell production and lithium refining reduce pass-through, so the effect should be weaker than for a pure battery buyer.

### 8. MP / GM (inverse, expected sign -, low to moderate confidence)

- Legs: MP Materials (NYSE) / General Motors (NYSE).
- Mechanism: Chinese export controls or NdPr price spikes raise MP's realised prices and the value of its US-based supply. They also raise magnet costs and supply risk for GM's EV traction motors, which use NdFeB permanent magnets. Shock days should produce opposite-sign moves. The relationship is event-driven rather than an unconditional rotation, because background market beta is positive for both.
- Liquidity and borrow: MP is liquid, possibly above $20M, but has carried high short interest, so borrow may be costly or limited. MP's history starts around July 2020 after its SPAC merger (verify), so it fails the 2016 window. GM covers the window (listed since its 2010 IPO). 2025 US government support arrangements (verify terms) may have decoupled MP from commodity prices, which would weaken the event link.

### 9. NXE / CCJ (coint, expected sign +)

- Legs: NexGen Energy (NYSE; verify listing date) / Cameco.
- Mechanism: NexGen is developing the Rook I project in the Athabasca Basin, and Cameco operates in the same basin. Both share the long-run U3O8 price, the Canadian regulatory framework and basin logistics. NexGen's spread should move with development-stage risk premia, including licensing, financing and construction milestones, and should otherwise revert around the common uranium factor. Breaks come from project milestones or dilutive financings at NexGen, and from operating events in the Athabasca at Cameco.
- Liquidity and borrow: NexGen's dollar volume is possibly near the $20M threshold (verify), and borrow is likely limited. Its US listing is recent, and its longer TSX history falls outside the US-listed constraint.

### 10. UUUU / DNN (coint, expected sign +, low confidence)

- Legs: Energy Fuels (NYSE American) / Denison Mines (NYSE American).
- Mechanism: Both are US-focused uranium companies that share exposure to US uranium policy and to spot. Energy Fuels has a producing mill and rare-earth optionality, while Denison is a development-stage developer in the Athabasca Basin. The spread should revert on common uranium moves, and it diverges on project and processing news, financings and rare-earth headlines.
- Liquidity and borrow: DNN's dollar volume is borderline against $20M (verify), and both names may have periods of elevated borrow cost. Verify Energy Fuels' ticker and listing continuity before 2018. Denison's primary listing is on the TSX, so confirm which line the US-listed series uses.

## Merged / delisted names (survivorship)

These names were relevant during the Oct 2016 onward window but cannot appear in a backtest that uses only current listings. Dates and acquirers are from memory; verify the ones marked.

- Livent (LTHM, NYSE): merged with Allkem into Arcadium Lithium, completed January 2024.
- Allkem (AKE, NYSE): merged into Arcadium Lithium, January 2024. Its earlier Orocobre OTC history is non-US.
- Arcadium Lithium (ALTM, NYSE): acquired by Rio Tinto, completed around March 2025. Verify date. Its history after the 2024 merger is short.
- Dynegy (DYN, NYSE): merged into Vistra in October 2018. Map pre-2018 Vistra history to DYN. Verify.
- USEC Inc. (USU, NYSE): restructured and renamed Centrus Energy (LEU) in 2014. Map USU history to LEU. Verify.
- Uranerz Energy (URZ, NYSE American): merged into Ur-Energy in 2015, before the window. Relevant only if the lookback is extended. Verify.
- Uranium Resources Inc. (URRE): renamed Westwater Resources in 2019. Verify the ticker mapping.
- Molycorp (MCP, NYSE): bankrupt in 2015 and delisted. Relevant for rare-earth history before the window.
- Fisker (FSR, NYSE): filed for Chapter 11 in 2024 and was delisted. Verify.
- Nikola (NKLA, Nasdaq): filed for Chapter 11 in early 2025 and was delisted. Verify.
- Canoo (GOEV, Nasdaq): filed for Chapter 7 in early 2025. Verify.
- Lordstown Motors (RIDE, Nasdaq): filed for Chapter 11 in 2023. Verify.
- Proterra (PTRA, Nasdaq): filed for Chapter 11 in 2023. Verify.
- Romeo Power (RMO, NYSE): acquired by Nikola in 2022. Verify.

Status uncertain (could not confirm from memory; check the exchange history):
- Piedmont Lithium (PLL, Nasdaq): a 2025 combination with Sayona may have changed the listed entity or ticker.
- Lithium Americas (LAC, NYSE): a 2023 reorganisation split out the Argentine assets into a separate listing. Check whether the LAC price series is continuous across the split.
- Talen Energy (TLN): reorganised after a 2023 bankruptcy. Check its listing history and whether pre-bankruptcy prices sit in the same series.
- NexGen (NYSE listing date) and Energy Fuels (ticker history): verify both.
- Any 2025-2026 uranium, lithium or rare-earth combinations that closed after the knowledge cutoff.
