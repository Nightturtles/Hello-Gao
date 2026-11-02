# Round 2 scouting: twin producers

Research-only scout output. Domain reasoning only: no backtests, price pulls or code. Facts are from memory with a dated knowledge cutoff, so anything marked "verify" needs checking against current filings, exchange listings and deal status before a test is run.

Ten pairs are proposed: nine `coint` and one `leadlag` (CHRD/NOG), all with a positive expected correlation. None reuses a Round 1 pair in either ordering.

**Pending-deal exclusions (not proposed):**
- TECK (Teck Resources) is party to the pending Anglo American–Teck combination (verify). Excludes all TECK pairs, including TECK/FCX.
- DVN and CTRA (Devon, Coterra): I believe an all-stock merger was announced in early 2026 (verify). Excludes DVN/CTRA and any DVN pair while the deal is pending.
- RYN and PCH (Rayonier, PotlatchDeltic): I believe an all-stock merger was announced in late 2025 (verify). Excludes the timber twin.
- RIO (Rio Tinto): merger talks with Glencore were reported in early 2026 (verify). Excludes VALE/RIO until resolved.
- CIVI and SM (Civitas, SM Energy): I believe an all-stock merger was announced in late 2025 (verify). Excludes that pair.

**Considered, not proposed on structure:** EQNR/BP (gas and renewables mix too different), APA/MUR (asset mix), BKR/SLB and NOV/HAL (different sub-industries), CF/MOS (nitrogen versus phosphate and potash), PSX/VLO (PSX midstream and chemicals mix), NUE/CMC (CMC is a rebar fabricator), ERO/HBM (ERO average dollar volume likely below $20M, verify).

## Proposed pairs

### 1. SHEL / BP: coint, expected corr +
- **Mechanism:** Both are London-listed integrated majors with NYSE ADRs that sell the same Brent-linked barrels and run large refining and trading books, so relative value should be driven by portfolio events (asset sales, LNG, buybacks, strategy resets) rather than a different commodity. The spread should revert because both face the same oil, gas and margin cycles, and a shared sector multiple bounds the valuation gap. It breaks if one company makes a lasting strategy change (such as BP's 2025 pivot back toward upstream) or a takeover approach re-rates it.
- **Liquidity, borrow, M&A:** Both very liquid, with dollar volume far above $20M (verify). Not expected to be hard-to-borrow (verify). No pending deal known; BP takeover speculation from 2025 is event risk only (verify current status).

### 2. TTE / SHEL: coint, expected corr +
- **Mechanism:** Both are European integrated majors with large LNG, trading and refining books priced off Brent and the TTF gas curve, so common energy-price factors should dominate their relative value. The spread should revert around shared sector drivers and similar capital-return policy. It breaks if TotalEnergies' power and renewables build-out or Shell's LNG trading results diverge for an extended period, or if one company changes its dividend or buyback regime.
- **Liquidity, borrow, M&A:** Both NYSE-listed and very liquid (verify). Not expected hard-to-borrow. No pending deal known. Shell also appears in SHEL/BP, so the two pairs share a leg and are not independent.

### 3. COP / EOG: coint, expected corr +
- **Mechanism:** Both are large-cap, oil-weighted US E&Ps with major Delaware and Permian positions, similar hedging, and similar exposure to frac and rig-cost inflation, so WTI and service costs move both. The spread should be driven by capex, well-result and basin-specific news, which tends to mean-revert. It breaks if EOG's gas-weighted assets (Dorado, Utica; verify) or COP's Alaska and international positions drive a persistent gas or geographic divergence.
- **Liquidity, borrow, M&A:** Both NYSE and very liquid. ConocoPhillips closed its Marathon Oil acquisition in November 2024, so the MRO history ends there (verify). EOG has done bolt-on acquisitions (verify). Not expected hard-to-borrow.

### 4. CHRD / NOG: leadlag, leader CHRD, expected corr +
- **Mechanism:** Both are Williston Basin (Bakken and Three Forks) oil producers, so the level spread should track the same Bakken economics. Chord is the operator and NOG is a non-operator that learns well results, spacing and completion changes from operator disclosures, so Chord's updates should reach NOG's price with a lag of days. This is a weak, information-based effect that breaks if NOG's non-Bakken growth dominates or if Chord's M&A changes its acreage base.
- **Liquidity, borrow, M&A:** Verify that a lead-lag exists at all before any test. Chord's history is spliced through Oasis Petroleum's 2020 reorganisation and its 2022 combination (verify), so expect a coverage break before those dates. Chord trades on Nasdaq and NOG on NYSE American (verify); NOG's float and borrow may be thinner (verify). Check reverse-split and adjustment handling for both. Chord acquired Enerplus in 2024 (verify).

### 5. DINO / PBF: coint, expected corr +
- **Mechanism:** Both are mid-cap independent US refiners whose earnings track the same Gulf Coast and Mid-Continent crack spreads and crude differentials, with comparable throughput and no large upstream business. The spread should revert because the dominant drivers are shared margins rather than company-specific events. It breaks if PBF's coastal and California exposure, single-site outages, or HF Sinclair's lubricants and midstream earnings drive a persistent gap.
- **Liquidity, borrow, M&A:** Both NYSE. PBF's dollar volume and borrow need checking and may sit near the $20M line (verify). Single-site outage risk at PBF (verify current status of its Martinez refinery) is event risk. HF Sinclair's pre-2022 history is HollyFrontier's (verify). No pending deal known.

### 6. LBRT / PUMP: coint, expected corr +
- **Mechanism:** Both are Permian-centric pressure pumpers that sell frac service to the same operator budgets and face the same sand, labor and crew-cost cycles, so fleet utilization and pricing move both margins together. The spread should revert because both are priced off the same activity cycle. It breaks if LBRT's power-generation build-out (verify) or a fleet-sale or equipment-capex cycle creates a persistent margin gap.
- **Liquidity, borrow, M&A:** LBRT is a later listing (IPO around early 2018, verify), so a spread cannot be built over the full October 2016 window without a shorter sample. PUMP may be hard-to-borrow at times, and its dollar volume may be near $20M (verify). No pending deal known.

### 7. GFI / HMY: coint, expected corr +
- **Mechanism:** Both are South African underground gold producers whose costs are dominated by rand, Eskom power, wage settlements and deep-level mining, so gold and the rand should move their margins similarly. The spread should revert because these common cost and price drivers dominate, and company-specific operating incidents tend to be temporary. It breaks if Harmony's copper diversification (MAC Copper, verify) or Gold Fields' growth in Australia, Ghana and Chile (Gold Road, verify) changes the mix for an extended period.
- **Liquidity, borrow, M&A:** Both NYSE ADRs and liquid (verify). HMY may be hard-to-borrow at times (verify). Recent M&A on both sides needs completion dates checked (verify). No GFI–HMY deal known.

### 8. KGC / AU: coint, expected corr +
- **Mechanism:** Both are large diversified gold producers with Americas and African assets, trading on the same gold curve and generalist gold-equity flows, so the spread should be mostly company-specific noise around a shared gold beta. It should revert because gold and sector flows are common factors. It breaks if asset events (Kinross's Tasiast; AngloGold's Obuasi and Cerro Vanguardia, verify) or a lasting dividend or buyback re-rating widen the gap.
- **Liquidity, borrow, M&A:** Both NYSE-listed and very liquid (verify). AngloGold is a UK-incorporated issuer (verify). Not expected hard-to-borrow. No pending deal known.

### 9. AG / PAAS: coint, expected corr +
- **Mechanism:** Both are silver-weighted producers with large Mexican operations, so silver price, the peso, and Mexican cost and permitting shocks should drive both. The spread should revert because the silver beta is shared and the gap comes from company-specific mix and jurisdiction risk. It breaks if Mexican policy or peso moves hit First Majestic disproportionately, or if Pan American's gold, zinc and base-metal weighting grows through acquisitions.
- **Liquidity, borrow, M&A:** AG trades on NYSE and PAAS on Nasdaq, both liquid (verify). AG may be hard-to-borrow at times (verify). The 2025 acquisitions of MAG Silver by Pan American and Gatos Silver by First Majestic (verify) delisted those names, so check history splices. No pending deal known to me.

### 10. YPF / VIST: coint, expected corr +
- **Mechanism:** Both are NYSE-listed Vaca Muerta oil producers exposed to the same Brent and WTI realization, export-duty regime and peso, so policy and FX move both. YPF is integrated with refining and fuel marketing and majority state-owned (verify), so the spread reflects integration and ownership differences around a shared Argentine beta. It breaks if fuel price controls, export taxes or YPF-specific refining margins diverge persistently, or if VIST's asset deals change its production base.
- **Liquidity, borrow, M&A:** VIST is likely hard-to-borrow, and its dollar volume may fall below $20M (verify). YPF's dollar volume is high. VIST's NYSE history may not reach October 2016 (verify). Argentine sovereign and policy event risk applies to both legs. No pending deal known.

## Merged/delisted names (survivorship)

- MRO (Marathon Oil): acquired by ConocoPhillips, closed November 2024 (verify). Ends the MRO history relevant to COP.
- ARCH (Arch Resources) and CEIX (CONSOL Energy): combined as Core Natural Resources (CNR), January 2025 (verify). CNR history is spliced.
- X (United States Steel): acquired by Nippon Steel, 2025 (verify).
- HES (Hess): acquired by Chevron, 2025 (verify).
- PXD (Pioneer Natural Resources) and DEN (Denbury): acquired by Exxon in 2024 and 2023 (verify).
- ERF (Enerplus): acquired by Chord, 2024 (verify). CHRD history is spliced from Oasis Petroleum (OAS), whose pre-reorganisation equity was cancelled (verify).
- NEX (NexTier): merged into Patterson-UTI, 2023 (verify).
- LTM (Livent), then ALTM (Arcadium Lithium): acquired by Rio Tinto, 2025 (verify).
- SWC (Stillwater Mining): acquired by Sibanye-Stillwater, 2017 (verify).
- GATO (Gatos Silver) and MAG (MAG Silver): acquired in 2025 by First Majestic and Pan American respectively (verify).
- CBT (Cabot Oil & Gas): combined into Coterra (CTRA), 2021 (verify).
- CHK (Chesapeake): renamed Expand Energy (EXE); history spliced across the rename and the Southwestern combination (verify).
- SAFM (Sanderson Farms): taken private, 2022 (verify).
