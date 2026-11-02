# Natural gas, coal, and gas-consuming chemicals: pair candidates (scout, as of 2026-10-27)

Ten candidate pairs in the natural gas, coal, and gas-consuming chemicals group: six `coint`, three `inverse`, one `leadlag`. This is domain reasoning only. No prices were downloaded, nothing was backtested, and no code was written.

Caveats for the quant team:
- Tickers, listing status, approximate liquidity and borrow notes come from memory and may be dated. Verify every ticker and history start date in code. Items marked "verify" are the least certain.
- Liquidity figures are rough orders of magnitude, not measured averages.
- Several names appear in more than one pair: CF in three (EQT/CF, CF/NTR, CF/LXU), EQT in two (EQT/AR, EQT/CF), DOW in two (AR/DOW, DOW/LYB), and CNR in two (CNR/CNX, CNR/AEP). Account for the overlap before running pairs concurrently.
- Expected signs for `inverse` pairs refer to the shock the mechanism describes. Total return correlation can be positive through sector or market beta, and the test should separate the two.

## Summary table

| # | Leg A | Leg B | Type | Expected sign | Confidence |
|---|---|---|---|---|---|
| 1 | EQT | AR | coint | + | Medium-high |
| 2 | RRC | CRK | coint | + | Medium |
| 3 | EQT | CF | inverse | - | Medium |
| 4 | AR | DOW | inverse | - | Medium |
| 5 | CF | NTR | coint | + | Medium-high |
| 6 | CF (leader) | LXU (follower) | leadlag | + | Low |
| 7 | DOW | LYB | coint | + | Medium-high |
| 8 | CNR | CNX | coint | + | Medium |
| 9 | AMR | HCC | coint | + | Medium |
| 10 | CNR | AEP | inverse | - | Low |

## Ideas considered and left out

- **UNG against gas producers as a spread.** UNG rolls its front-month contract, so roll yield (contango or backwardation) makes its price level drift away from equity levels. A stable long-run relation for a cointegration pair does not exist. A returns-based test is possible, but the equity-to-futures link is contemporaneous: futures settle around 2:30pm ET and equities close at 4pm ET. No useful 1-to-10-day lead is expected. UNG has also had fund-structure and share-count changes (verify).
- **UNG against UNL (front month versus 12-month strip).** This is a curve-shape spread that could mean-revert, but both legs are the same underlying, so the spread is mostly roll mechanics. UNL is likely far below $20M ADV (verify). Left out.
- **Cheniere (LNG) against gas producers.** Cheniere's contracted fee model makes most of its returns insensitive to Henry Hub, so the spread is unlikely to revert. A spot-margin inverse could be revisited later.
- **Gas-to-coal leadlag (UNG leading coal equities).** Fuel switching happens in power dispatch and contract repricing over months. Any transmission would be intraday or overnight, not over 1 to 10 days.
- **Thermal coal against met coal beyond AMR/HCC.** Peabody (BTU) mixes thermal and met exposure and has a post-2017 listing history. Left out to keep to cleaner pure-play pairs.
- **LNG as leader to Haynesville producers.** The story is thematic (LNG news spreads to Haynesville names with a lag), not a clear mechanism. Not proposed.

## Cross-pair structural flags

- **CNR / CNX / CEIX / ARCH naming.** CNR is Core Natural Resources, formed from the Arch and CONSOL Energy combination (completed around January 2025, verify). CNX is CNX Resources, the gas company. CNX's ticker before its 2017 separation belonged to the whole pre-separation CONSOL Energy, which included coal. Pre-2017 CNX history is not comparable to the current gas company. Confirm which predecessor's series the vendor carries under CNR (CEIX or ARCH, verify).
- **DOW.** The Dow Inc. spin-off was in April 2019. Before that, the DOW ticker belonged to old Dow Chemical, which merged into DowDuPont in 2017. Splice or truncate at the April 2019 break (verify vendor series).
- **NTR.** Nutrien was formed in January 2018 from Agrium and PotashCorp. Pre-2018 NTR history is a splice of the predecessor series (verify).
- **HCC.** Warrior Met Coal listed in April 2017 after the Walter Energy bankruptcy, so it has no Oct 2016 history (verify first trade date).
- **AMR.** The current listing traces to Contura Energy (renamed Alpha Metallurgical Resources, verify), a successor of Alpha Natural Resources. Verify ticker and series continuity before 2018.
- **CF, NTR, EQT, AR, RRC.** No known listing breaks inside the window, but verify share-count adjustments for EQT (2024 Equitrans transaction) and any recent acquisitions.

## Pairs

### 1. EQT / AR (coint, expected sign +)

- Tickers: EQT (leg_a), AR (leg_b), both NYSE.
- Mechanism: Both are Appalachian gas producers selling into the same Eastern hubs. They share basin differentials, pipeline constraints and Henry Hub exposure, so their long-run relative valuation should be anchored by common costs and capital-allocation norms. Divergence comes from AR's liquids-rich (wet gas) mix, hedge books and buyback pace, which should unwind as cost curves and multiples converge.
- What would break it: an acquisition by either company, a large shift in AR's liquids share, or a divergence in hedge books.
- Liquidity and borrow: both have high ADV and easy borrow.

### 2. RRC / CRK (coint, expected sign +)

- Tickers: RRC (leg_a), CRK (leg_b), both NYSE (verify CRK listing and ticker).
- Mechanism: Range (Appalachia) and Comstock (Haynesville) are gas-weighted pure plays whose returns share the Henry Hub factor. Their relative value should track a fairly stable basis between Appalachian and Gulf Coast gas economics. Divergence comes from basin-specific shocks, such as Appalachian pipeline constraints against Haynesville demand from Gulf Coast LNG feedgas, and from Comstock's higher leverage, which makes it the higher-beta leg.
- What would break it: a sustained shift in the Appalachia-Haynesville basis (new pipelines or LNG start-ups), or a Comstock acquisition or leverage change.
- Liquidity and borrow: RRC has high ADV and easy borrow. CRK is likely adequate on liquidity but verify, and check borrow.

### 3. EQT / CF (inverse, expected sign -)

- Tickers: EQT (leg_a), CF (leg_b), both NYSE.
- Mechanism: Henry Hub is EQT's revenue driver and CF's main cost input. US nitrogen margins are roughly global ammonia and urea prices minus US gas cost, so a US-specific gas rally should lift EQT and compress CF's margin. The rotation (long EQT, short CF when Henry Hub leads) therefore implies negative correlation on Henry Hub-driven shocks.
- What would break it: global shocks (TTF or JKM spikes, Russian or Middle Eastern supply) lift both legs together. Energy-versus-materials beta can also make raw correlation positive. The test should separate Henry Hub-specific moves from global moves.
- Liquidity and borrow: both have high ADV and easy borrow.

### 4. AR / DOW (inverse, expected sign -)

- Tickers: AR (leg_a), DOW (leg_b), both NYSE.
- Mechanism: Antero is liquids-rich, so part of its revenue rises with NGL and ethane prices. Dow's US crackers buy ethane as their main feedstock and see margin compression when ethane rallies. A feedstock or NGL shock therefore pushes the two legs in opposite directions, and the rotation (long AR, short DOW on NGL rallies) carries a negative expected sign.
- What would break it: Dow's polymer pricing and the global olefin cycle dominate its returns, or both legs trade on broad energy and materials beta in risk-off periods.
- Liquidity and borrow: both have high ADV and easy borrow.
- Structural: DOW history before April 2019 belongs to a different entity (see the cross-pair flags above).

### 5. CF / NTR (coint, expected sign +)

- Tickers: CF (leg_a), NTR (leg_b). CF is NYSE. NTR is NYSE and TSX (verify).
- Mechanism: Both are large nitrogen producers whose revenue depends on the same global urea and ammonia prices, so their long-run relative valuation should be anchored by that shared exposure. Divergence comes from Nutrien's potash and retail businesses, its Canadian gas cost (AECO) against CF's Henry Hub cost, and Nutrien's more diversified mix.
- What would break it: a potash-driven re-rating of Nutrien, a major retail acquisition or disposal, or a sustained gap between AECO and Henry Hub.
- Liquidity and borrow: both have high ADV and easy borrow.
- Structural: NTR pre-2018 history is a splice of predecessor series (see the cross-pair flags above).

### 6. CF (leader) / LXU (follower) (leadlag, expected sign +)

- Tickers: CF (leader, leg_a), LXU (follower, leg_b), both NYSE (verify LXU).
- Mechanism: CF is the nitrogen bellwether with much wider analyst and fund coverage, so nitrogen-price news and plant-outage news should reach its price first. The smaller, more levered LSB Industries should reprice a few days later as analysts and funds catch up. This is a plausible but low-conviction information-diffusion story.
- What would break it: LXU-specific events (outages at its own plants, financing or legal news) dominate its returns, or CF's news is company-specific and does not transfer to LXU.
- Liquidity and borrow: LXU is likely the least liquid name in this set and may fall below $20M ADV (verify). Short interest has been elevated historically (verify), so borrow may be tight or costly.
- Confidence: lowest-confidence leadlag in the set. The quant team should expect it to fail the lag test unless the effect is real.

### 7. DOW / LYB (coint, expected sign +)

- Tickers: DOW (leg_a), LYB (leg_b), both NYSE. LYB is Netherlands-domiciled and NYSE-listed (verify).
- Mechanism: The two largest US-listed ethane-cracking petrochemical producers share the same US ethane-versus-naphtha cost advantage and polyolefin cycle, so their relative valuation should be anchored by those shared drivers. Divergence comes from LYB's European and naphtha-based assets, differences in product mix, and closures or divestitures.
- What would break it: a structural change in one company (European closures, a major divestiture, or a change in ethane supply contracts), or a regional demand shock in Europe or China that hits one company more than the other.
- Liquidity and borrow: both have high ADV and easy borrow.
- Structural: DOW pre-April 2019 history (see the cross-pair flags above).

### 8. CNR / CNX (coint, expected sign +)

- Tickers: CNR (leg_a), CNX (leg_b), both NYSE. Name caution: CNR is Core Natural Resources and CNX is CNX Resources. The tickers are easy to confuse.
- Mechanism: Core Natural Resources (Pennsylvania thermal coal plus Appalachian met coal) and CNX (Appalachian gas) both sell into PJM and Appalachian power and gas markets. Higher gas prices help coal through fuel switching, so their relative value should be tied to a stable gas-coal relationship. Divergence comes from CNR's merger integration and met-coal exposure, and from CNX's hedges and leverage.
- What would break it: a structural coal retirement wave or gas-price shock that breaks the switching link, or CNR restructuring or integration events.
- Liquidity and borrow: CNX has high ADV and easy borrow. CNR is likely moderate on ADV (verify), and borrow should be checked.
- Structural: CNX history before the 2017 separation is not comparable (see the cross-pair flags above). Confirm the CNR series splice.

### 9. AMR / HCC (coint, expected sign +)

- Tickers: AMR (leg_a), HCC (leg_b), both NYSE.
- Mechanism: Both are US-listed seaborne met-coal producers whose realized prices track the same premium hard-coking-coal benchmark, which is set by global steel demand. Their margins should therefore share one driver. Spread divergence comes from mine geology and cost (Appalachia versus Alabama), contract versus spot mix, and balance-sheet and dividend policy.
- What would break it: a US-specific operational shock at one company (mine incident, strike, rail or port bottleneck), or a steel-demand shift that favors one grade or export route.
- Liquidity and borrow: both have moderate ADV (verify, likely tens of millions of dollars). Both have had elevated short interest at times, so check borrow.
- Structural: HCC has no pre-April 2017 history (see the cross-pair flags above). AMR lineage needs verification.

### 10. CNR / AEP (inverse, expected sign -)

- Tickers: CNR (leg_a), AEP (leg_b). AEP is listed on Nasdaq (verify).
- Mechanism: A coal-price rise helps coal producers immediately. A coal-burning regulated utility recovers higher fuel costs only with a lag and faces affordability and rate-case pressure, so coal-specific price shocks should rotate flows out of utilities and into coal.
- What would break it: utility equity is mostly driven by rates, rate-base growth and load-growth themes, so the inverse may be weak or unstable. It would also fail if AEP's coal share falls through retirements.
- Liquidity and borrow: AEP has high ADV and easy borrow. CNR borrow should be checked (see pair 8).
- Confidence: lowest-conviction pair in this set. It is included to cover coal against utilities, and the quant team should expect it to be the weakest.

## Merged, bankrupt, or delisted names (survivorship)

The following names were important in this space during or near the Oct 2016 to present window and are not in a backtest's universe if it is built from today's tickers. Verify each date.

**Gas producers and gas-linked midstream**
- Chesapeake Energy, old CHK: Chapter 11 in 2020, old equity cancelled, delisted. The successor listed in 2021 and later became Expand Energy (EXE, Nasdaq, verify). Any series under the EXE ticker has a different history.
- Southwestern Energy (SWN): acquired by Chesapeake (later Expand Energy) in 2024 (verify closing).
- Cabot Oil & Gas (COG) and Cimarex Energy (XEC): combined in October 2021 into Coterra Energy (CTRA). Coterra has reportedly been party to a 2026 combination with Devon Energy (verify status). If that deal closed, CTRA is also delisted.
- Rice Energy (RICE): acquired by EQT in 2017.
- Equitrans Midstream (ETRN): acquired by EQT in 2024 (verify).
- Montage Resources (MR, formerly Eclipse Resources): acquired by Southwestern Energy (verify year).
- WPX Energy (WPX): acquired by Devon Energy in January 2021 (verify).
- Ultra Petroleum (UPL): Chapter 11 in 2020, delisted.
- Gastar Exploration (GST): Chapter 11 in 2018, delisted.
- EXCO Resources (XCO): Chapter 11 in 2017, delisted.
- Gulfport Energy: Chapter 11 in 2020 with equity cancelled. Its later listing and venue changed (verify).
- Tellurian (TELL, LNG developer): acquired by Woodside Energy, taken private (verify closing date).

**Coal**
- Arch Coal, old ticker ACI: Chapter 11 in January 2016, delisted. New Arch (ARCH) listed in October 2016. Arch was combined with CONSOL Energy's coal business into Core Natural Resources (CNR) in January 2025 (verify), and ARCH was delisted.
- CONSOL Energy (CEIX): coal company listed in 2017 after the CNX separation. Combined into Core Natural Resources (CNR) in January 2025 (verify).
- Peabody Energy, pre-2016 equity: old equity cancelled in the 2016 Chapter 11. The new BTU listed in April 2017, so there is no series from Oct 2016 to April 2017 (verify).
- Alpha Natural Resources (ANR): Chapter 11 in 2015, delisted. Its lineage is relevant to AMR (verify).
- Walter Energy (WLTGQ): Chapter 11 in 2015, delisted. Warrior Met Coal (HCC) emerged from this group.
- Westmoreland Coal (WLB): Chapter 11 in 2018, delisted.
- Cloud Peak Energy (CLD): Chapter 11 in 2019, delisted.
- Foresight Energy (FELP): Chapter 11 in 2020, delisted.

**Fertilizer and petrochemicals**
- PotashCorp (POT) and Agrium (AGU): merged into Nutrien (NTR) in January 2018.
- Terra Nitrogen (TNH): acquired by CF Industries in 2018 (verify).
- Rentech Nitrogen Partners (RNF): merged into CVR Partners (UAN) in 2016 (verify).
- The Dow Chemical Company (old DOW): merged into DowDuPont (DWDP) in August 2017. DowDuPont later became DuPont de Nemours (DD). Dow Inc. (DOW) was spun off in April 2019.
