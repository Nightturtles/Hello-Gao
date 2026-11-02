# Midstream, transport and processing: pair candidates (scout round 2, as of 2026-10-28)

Eight candidate pairs, all `coint` with expected correlation sign `+`. Domain reasoning only: no prices downloaded, nothing backtested, no code written.

Round 1 failures (producer vs commodity ETF, input vs consumer, upstream vs downstream) pushed this round toward peers that share a contract or fee structure and a demand driver, rather than a producer against a price.

Caveats:
- Tickers, listing status, liquidity and borrow notes come from memory and may be dated. Verify each ticker and history start date in code. Items marked "verify" are the least certain.
- Liquidity figures are rough orders of magnitude, not measured averages.
- WY/RYN depends on a timber REIT combination (see survivorship section). Check the post-deal series before using it.

Considered and left out:
- CSX/NSC, and any leg of the pending Union Pacific–Norfolk Southern deal. This is merger-arb, so it is avoided.
- CQP/LNG and PAA/PAGP. Same economic entity.
- PAA/EPD. Crude-heavy vs NGL-heavy exposure, too loose a link.
- MPLX/EPD. Same MLP family as the ET/EPD pair that failed in round 1.
- SBLK/VALE and other shipper-vs-miner pairs. Upstream vs downstream, the round 1 failure mode.
- INSW/DHT and STNG/FRO. INSW/DHT is close to the failed FRO/DHT, and STNG/FRO has a weak product-vs-crude link.
- Leadlag pairs. No volume or contract mechanism I trust gives a stable 1 to 10 day lead between two listed midstream names.

## Pairs

### 1. WMB / KMI (coint, expected sign +)

- Tickers: WMB (leg_a), KMI (leg_b), both NYSE.
- Mechanism: Williams and Kinder Morgan are the two largest US gas-pipeline C-corps. Both earn mostly fee-based, contracted or FERC-regulated transmission and storage revenue from the same power-burn, LNG-feedgas and industrial demand. Both are valued on contracted EBITDA growth and leverage, so the log valuation ratio should revert around sector multiples.
- What would break it: KMI's CO2 and terminals exposure and its asset-sale decisions, WMB's Gulf and Haynesville gathering build-out, and differing capital-return policy.
- Liquidity and borrow: both very liquid and easy to borrow.
- M&A and splices: KMI consolidated its MLPs (KMP, EPB, KMR) into KMI around 2014 to 2015. WMB absorbed Williams Partners (WPZ) in 2018. Use adjusted series and verify. No known pending deal between them.

### 2. OKE / TRGP (coint, expected sign +)

- Tickers: OKE (leg_a), TRGP (leg_b), both NYSE.
- Mechanism: Both earn gas-processing, NGL-fractionation and NGL-logistics fees on Permian and Mid-Continent wet-gas volumes, so earnings respond to the same drilling and NGL-volume shocks. Both are valued on EBITDA and distribution yield, so the spread should revert around a basin-mix relationship.
- What would break it: TRGP is Permian-concentrated and OKE is broader in the Mid-Continent with more commodity-linked NGL margin. A Permian-specific takeaway or processing build-out would move TRGP alone.
- Liquidity and borrow: both liquid and shortable.
- M&A and splices: OKE's recent acquisitions (Magellan in 2023, plus Medallion and EnLink; verify closing dates) changed its footprint and share count. Use adjusted series. TRGP's 2016 Targa Resources Partners (NGLS) simplification is before the window (verify).

### 3. CNI / CP (coint, expected sign +)

- Tickers: CNI (leg_a), CP (leg_b), both NYSE, USD-quoted.
- Mechanism: Canadian National and Canadian Pacific Kansas City are the two transcontinental Canadian railways. They compete for and share Western Canadian grain, potash, sulfur and intermodal freight. Both are valued on operating ratio, EBITDA margin and the same freight cycle, which should keep the relative valuation range-bound.
- What would break it: CP's Mexico and US Southwest network, added through the Kansas City Southern combination, which CNI does not replicate. Labor or regulatory events that hit one railroad more also break it, as do corporate-action differences (buybacks, split history).
- Liquidity and borrow: both liquid. Borrow is generally fine (verify).
- M&A and splices: CP's series before its 2023 KCS combination reflects pre-combination CP only. KSU is delisted. CP has done share splits, so use adjusted prices. No known pending CN–CP transaction. CN's 2021 bid for KCS was lost and is historical only (verify).

### 4. IP / PKG (coint, expected sign +)

- Tickers: IP (leg_a), PKG (leg_b), both NYSE.
- Mechanism: Packaging Corp of America is a pure-play US containerboard and corrugated-box producer. International Paper makes containerboard and boxes too, but it has other businesses and, since early 2025, a large European business via DS Smith. Both price off the same US containerboard index and box-shipment demand, so the common factor should dominate and the relative valuation should revert.
- What would break it: IP's European and non-US earnings, which dominate after the DS Smith deal. Also IP's restructuring and separation actions, and PKG's mill acquisitions or capacity changes.
- Liquidity and borrow: both liquid and easy to borrow.
- M&A and splices: DS Smith closed around early 2025 (verify exact date). Split the IP history into pre- and post-close subperiods. IP's cellulose divestitures are also a break (verify dates).

### 5. BALL / CCK (coint, expected sign +)

- Tickers: BALL (leg_a), CCK (leg_b), both NYSE. BALL is reused from round 1 (CENX/BALL) in a new combination.
- Mechanism: Ball and Crown are the two largest beverage-can makers. They supply the same large brewers and soft-drink bottlers under multi-year contracts that pass aluminum cost through with a lag, so margins and volumes respond to the same can demand. Their per-can conversion economics are similar, so their EV-to-EBITDA ratio should revert.
- What would break it: Ball's larger Latin American and European beverage exposure, Crown's food and aerosol mix, and portfolio or restructuring decisions at either company (verify).
- Liquidity and borrow: both liquid. CCK is likely the thinner leg; check its ADV against the $20M bar (verify). Borrow is fine (verify).
- M&A and splices: check Ball's 2024 aerospace exit and any beverage disposals (verify).

### 6. WY / RYN (coint, expected sign +)

- Tickers: WY (leg_a), RYN (leg_b), both NYSE.
- Mechanism: Weyerhaeuser and Rayonier are US timberland REITs. Their cash flows come from harvest volumes and log prices in the US South and Pacific Northwest, and both trade on NAV and dividend yield. They therefore share the timber cycle and the rate factor, and similar REIT structures should keep their NAV discounts similar.
- What would break it: WY's wood-products exposure (lumber and OSB, housing-cycle sensitive), RYN's New Zealand forests (export-log pricing to Asia), and timber-REIT consolidation.
- Liquidity and borrow: WY is very liquid. RYN is borderline against the $20M bar (verify). Borrow is generally fine (verify).
- M&A and splices: I understand PotlatchDeltic (PCH) agreed in late 2025 to combine with Rayonier. If that closed, RYN's series after close is a splice and PCH is delisted. Verify status and which ticker survives. WY absorbed Plum Creek (PCL) in 2016, before the window.

### 7. TNK / INSW (coint, expected sign +)

- Tickers: TNK (leg_a), INSW (leg_b), both NYSE.
- Mechanism: Teekay Tankers and International Seaways both run mid-size crude (Aframax and Suezmax) and product tankers with overlapping Atlantic-basin trade. They draw on the same charter-rate cycle and trade near NAV on similar fleet-renewal and charter-cover profiles, so a shared rate factor should keep the spread range-bound.
- What would break it: a diverging fleet mix (INSW's LR2 product tankers and its lightering business, against TNK's own mix), newbuild or sale-leaseback activity at one company, or different charter cover.
- Liquidity and borrow: HARD-TO-BORROW risk for both. Tanker names are often expensive or unavailable to short. INSW is likely above $20M ADV. TNK is near the threshold (verify).
- M&A and splices: INSW only trades from November 2016, after its spin from OSG. The full Oct 2016 window needs the OSG pre-spin series (verify). Check TNK for any reverse split or class-share history.

### 8. SBLK / GNK (coint, expected sign +)

- Tickers: SBLK (leg_a, Nasdaq), GNK (leg_b, NYSE).
- Mechanism: Star Bulk and Genco are both US-listed, dividend-oriented dry-bulk owners. Their equities track the same Baltic and time-charter environment. Genco is more Capesize-weighted and Star Bulk is more diversified across Panamax, Kamsarmax and supramax, so the spread reflects the Capesize-vs-smaller-ship rate mix and should revert as those fleet rates re-converge.
- What would break it: fleet-mix shifts, newbuild and sale decisions, capital-return and leverage differences, and M&A (see below).
- Liquidity and borrow: HARD-TO-BORROW risk for both. SBLK is likely above $20M ADV. GNK is borderline (verify).
- M&A and splices: dry-bulk consolidation has been active. I believe Eagle Bulk (EGLE) was absorbed by Star Bulk and Golden Ocean merged into CMB.TECH (verify both). Check for any pending transaction involving Genco or Diana Shipping (DSX); I am not certain of its status. Genco restructured its debt and reverse-split its stock around 2014 to 2016, and Star Bulk has its own reverse-split history (verify). Use adjusted series.

## Merged/delisted names (survivorship)

- Kinder Morgan Energy Partners (KMP), Kinder Morgan Management (KMR), El Paso Pipeline Partners (EPB): folded into KMI around 2014 to 2015 (verify).
- Williams Partners (WPZ): merged into WMB in 2018 (verify).
- Targa Resources Partners (NGLS): folded into TRGP in 2016, before the window (verify).
- Magellan Midstream (MMP) and EnLink Midstream (ENLC): acquired by OKE (verify closing dates).
- Kansas City Southern (KSU): combined with CP in 2023 and delisted (verify).
- Plum Creek Timber (PCL): merged into WY in February 2016, before the window.
- PotlatchDeltic (PCH): combination with Rayonier agreed in late 2025 (verify whether closed and whether PCH is delisted).
- WestRock (WRK): combined into Smurfit Westrock (SW) in July 2024. Not in this set, but relevant to any containerboard follow-up.
- DS Smith (LSE): acquired by International Paper around early 2025. Not US-listed, but it sets the IP break date (verify).
- Overseas Shipholding Group (OSG): INSW's parent until the November 2016 spin. Later taken private (verify).
- Eagle Bulk (EGLE): acquired (verify).
- Golden Ocean (GOGL): merged into CMB.TECH (verify).
- Union Pacific–Norfolk Southern (NSC): pending merger, avoided. Verify status.
