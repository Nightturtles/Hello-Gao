# Power generation, gas consumers and commodity processors: pair candidates (scout round 2, as of 2026-10-28)

Eight candidate pairs: six `coint`, one `inverse`, one `leadlag`. This is domain reasoning only. No prices were downloaded, nothing was backtested, and no code was written.

Round 1 lesson applied: the failed pairs were mostly ones where one leg's returns were dominated by idiosyncratic events (CEG/VST, DOW/LYB). Here I prefer pairs where both legs are priced off the same spread or policy factor. Where a leg reuses a ticker from a tested pair, the entry says so.

Caveats for the quant team:
- Tickers, listing history, liquidity and borrow notes come from memory and may be dated. Verify every ticker and history start date in code. Items marked "verify" are the least certain.
- Liquidity statements are rough orders of magnitude against the $20M ADV screen, not measured averages. No live borrow data was consulted, so "hard-to-borrow" flags are judgments to check against a current borrow feed.
- Names reused across pairs: WLK in three (WLK/OLN, WLK/LYB, EQT/WLK), CF in one (CF/MOS, after CF's three tested pairs), MOS in two (MOS/ICL, CF/MOS; NTR/MOS was tested), ADM in one (DAR/ADM; ADM/BG and MOO/ADM were tested), LYB in one (WLK/LYB; DOW/LYB was tested), EQT in one (EQT/WLK; EQT/AR, EQT/CF and BTU/EQT were tested).

## Summary table

| # | Leg A | Leg B | Type | Expected sign | Confidence |
|---|---|---|---|---|---|
| 1 | VST | NRG | coint | + | Medium |
| 2 | ATO | OGS | coint | + | Medium-high |
| 3 | WLK | OLN | coint | + | Medium |
| 4 | WLK | LYB | coint | + | Medium-low |
| 5 | MOS | ICL | coint | + | Medium |
| 6 | CF (leader) | MOS (follower) | leadlag | + | Low |
| 7 | EQT | WLK | inverse | - | Medium-low |
| 8 | DAR | ADM | coint | + | Medium-low |

## Proposed pairs

### 1. VST / NRG (coint, expected sign +)
- **Mechanism:** Both are merchant IPPs whose earnings are set by ERCOT energy and capacity prices, where gas is often the marginal fuel. Two similarly exposed merchant fleets should share a long-run valuation anchor. The spread breaks on fleet-mix differences (VST's nuclear and PJM footprint versus NRG's Texas gas and retail book) or on data-center contract news that re-rates only one name.
- **Liquidity, borrow, M&A:** Both NYSE, ADV well above $20M (verify). General collateral expected; hard-to-borrow risk low to moderate, verify live. NRG's acquisition of LS Power assets (announced 2025, verify closing) is buyer-side and not between the legs. VST began trading in October 2016 after its bankruptcy emergence, so its history starts at the window start (verify first trade date). CEG/VST failed in round 1, so expect VST-specific news to dominate.

### 2. ATO / OGS (coint, expected sign +)
- **Mechanism:** Both are rate-regulated gas distributors with overlapping Texas exposure. They pass through gas costs under similar allowed-return frameworks, so valuations should share a long-run anchor. The spread breaks on rate-case outcomes, capex-recovery timing, or a regulatory event in one jurisdiction, since Atmos spans several states (Texas is its largest) and ONE Gas is Oklahoma, Kansas and Texas.
- **Liquidity, borrow, M&A:** Both NYSE with history covering the window; ADV above $20M (verify). General collateral; hard-to-borrow risk very low. Utility sector beta dominates, so test against a utility-sector factor. No known M&A between them (verify).

### 3. WLK / OLN (coint, expected sign +)
- **Mechanism:** Westlake and Olin both make chlor-alkali and vinyl chain products (caustic soda, chlorine, PVC, ethylene derivatives). Their margins respond to the same construction and housing demand and to the same chlorine, caustic and ethylene pricing, so the spread should be stationary. It breaks on Olin's Winchester ammunition segment or Westlake's olefins and building-products businesses.
- **Liquidity, borrow, M&A:** Both NYSE; WLK and OLN ADV likely above $20M (verify). General collateral expected; hard-to-borrow risk low to moderate for OLN (verify). No known M&A between them (verify). Olin's dividend and portfolio actions are idiosyncratic events to screen out.

### 4. WLK / LYB (coint, expected sign +)
- **Mechanism:** Both are large US polyethylene and PVC producers running on ethane-based ethylene, so their margins share the ethylene-to-feedstock spread. The relation should hold while both run on US ethane. It breaks when LYB's naphtha, NGL and European exposure reprices differently from Westlake's ethane-based system, for example when the ethane-to-naphtha price gap moves sharply.
- **Liquidity, borrow, M&A:** Both NYSE, ADV above $20M (verify). LYB is reused from DOW/LYB, which failed in round 1; if that failure came from LYB-specific events (dividend, European or refinery changes, verify), expect the same problem here. Hard-to-borrow risk low to moderate for LYB (verify). No known M&A between them (verify).

### 5. MOS / ICL (coint, expected sign +)
- **Mechanism:** Mosaic (phosphate and potash) and ICL (potash, phosphate and specialty products) have closely matched product mixes. Both margins follow the same DAP and potash cycle and phosphate input costs, so the spread should revert across cycles. It breaks when ICL's Dead Sea potash cost base and shekel exposure diverge from Mosaic's Florida and Brazil phosphate operations.
- **Liquidity, borrow, M&A:** ICL is an NYSE-listed Israeli ordinary-share issuer (verify listing and filer status). Its ADV is close to the $20M line (verify). Hard-to-borrow risk for ICL is elevated relative to Mosaic; verify live borrow. Mosaic is general collateral. MOS is shared with NTR/MOS (tested), so check redundancy. No known M&A between them (verify).

### 6. CF / MOS (leadlag, leader CF, expected sign +)
- **Mechanism:** Nitrogen prices (CF's ammonia and urea) reprice faster than phosphate and potash, so CF's price-driven moves may lead Mosaic's by a few trading days as the market re-rates the farm-input complex. The sign is unstable because ammonia is an input cost for Mosaic's phosphate, so a high-ammonia regime can offset the crop-price channel.
- **Liquidity, borrow, M&A:** Both NYSE, ADV well above $20M, general collateral expected (verify). Low confidence; test lags of 1 to 5 trading days. CF is reused from CF/NTR, EQT/CF and CF/LXU (tested). No known M&A (verify).

### 7. EQT / WLK (inverse, expected sign -)
- **Mechanism:** A Henry Hub rally lifts gas producer revenue at EQT but raises ethane and gas feedstock costs for ethane-cracking Westlake, so the two should move in opposite directions on gas-driven shocks. This is a return relationship rather than a spread that mean-reverts, so the test should use return correlation on residuals.
- **Liquidity, borrow, M&A:** Both NYSE, ADV above $20M (verify). EQT's history is continuous through its 2024 Equitrans combination (verify). General collateral expected; hard-to-borrow risk low (verify). Sector and market beta can make raw correlation positive, so test on residuals. Round 1 input-versus-consumer pairs trended, so this may fail the same way; it is included as an inverse test, not a coint test. WLK is reused from two other pairs.

### 8. DAR / ADM (coint, expected sign +)
- **Mechanism:** Darling's fats-based rendering and its 50% share of Diamond Green Diesel track vegetable oil prices and biofuel policy values such as RINs and 45Z. ADM's crush margins depend on the same soybean oil price and policy. The spread should be stationary through this common oil-and-policy factor, and it breaks on Darling-specific DGD margin shifts or ADM's grain-merchandising and crush-capacity changes.
- **Liquidity, borrow, M&A:** Both NYSE; DAR ADV above $20M (verify). General collateral expected; hard-to-borrow risk low (verify). ADM is in MOO/ADM and ADM/BG (both tested), so the ADM leg may carry the same crush factor; check redundancy. Confirm how Darling reports its DGD stake (equity method, verify). No known M&A between them (verify).

## Ideas considered and left out

- **NRG / TLN.** TLN has no usable October 2016 equity history. Its pre-2023 equity was private or OTC, and it relisted after its 2023 Chapter 11 (verify dates). Fails the history screen; keep on a watch list only.
- **Gas-heavy regulated utilities against gas producers (for example ATO against EQT).** This is an input-versus-consumer structure, which failed in round 1, and there is no clear stationary anchor.
- **ATO / NJR and SWX as alternates.** NJR has large non-utility clean-energy and gas-marketing businesses. Southwest Gas owns Centuri (utility infrastructure services), which dilutes its utility link. Possible second-tier pairs if ATO/OGS works.
- **Merchant against regulated power.** The spread would be driven by rate-base growth and data-center narratives rather than a commodity spread. Not proposed.
- **Sugar and ethanol.** No liquid US-listed pure sugar name exists. The ethanol names (ALTO, REX) are likely below the $20M ADV screen (verify). Excluded.
- **Industrial gases (APD, LIN).** Not commodity-linked as required. Excluded.
- **Steel processors (RYI, ZEUS, IIIN).** ZEUS and IIIN look thin (verify ADV); RYI may pass but needs a second leg of comparable liquidity. Excluded for now.
- **Aluminum rolled products (KALU, CSTM).** Constellium's listing history and Kaiser's ADV are uncertain (verify). Not proposed.
- **CVR Partners (UAN) against CF.** UAN is likely thin (verify ADV). Excluded.
- **Renewable diesel: VLO against DAR.** Valero's DGD exposure is diluted by a refining-dominated business. Neste's ADR trades OTC, not on a US exchange (verify), so it is out of scope.
- **NRG / CEG.** CEG reinforces the round 1 CEG/VST failure, and the Calpine acquisition is a corporate event (verify closing). Excluded.

## Merged/delisted names (survivorship)

- **Talen Energy (TLN).** Chapter 11 in 2023, then relisting on Nasdaq after emergence (verify date). Pre-bankruptcy equity history is not comparable. Fails the October 2016 history screen.
- **Vistra Energy (VST).** Began trading in October 2016 after the Energy Future Holdings emergence (verify first trade date). History starts at the window start.
- **Dynegy (DYN).** Acquired by Vistra in 2018 and delisted. Not a leg, but relevant when reading VST's pre-2018 history.
- **Energy Harbor.** Private, acquired by Vistra (verify closing). Not a leg.
- **Calpine.** Private since 2018, acquired by Constellation (verify closing). Not a leg.
- **LS Power assets.** NRG acquisition announced 2025 (verify closing). Not a leg.
- **Chesapeake, now Expand Energy (EXE).** Old equity was cancelled in the 2021 bankruptcy, so the listed history restarts at emergence. Not proposed.
- **Pacific Ethanol, now Alto Ingredients (ALTO).** Renamed 2021, thin. Excluded.
- **Bunge (BG).** Viterra combination in 2023 and a later Swiss redomicile as Bunge Global SA (verify). BG continuity matters for ADM/BG (tested) and any future BG pair.
- **Worthington Steel (WS).** Separated from Worthington Industries in 2023 (verify). Ticker and history mapping needs checking. Not proposed.
- **Proposed legs.** No delisting or pending merger between legs was identified for VST, NRG, ATO, OGS, WLK, OLN, LYB, MOS, ICL, CF, EQT, DAR or ADM. Verify all of them.
