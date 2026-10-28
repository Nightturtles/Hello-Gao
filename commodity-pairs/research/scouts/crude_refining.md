# Crude oil and refining: pair candidates (scout, as of 2026-10-27)

Ten candidate pairs in the crude oil and refining group: eight `coint`, one `inverse`, one `leadlag`. This is domain reasoning only. No prices were downloaded, nothing was backtested, and no code was written.

Caveats for the quant team:
- Tickers, listing status, approximate liquidity and borrow notes come from memory and may be dated. Verify every ticker and history start date in code. Items marked "verify" are the least certain.
- Liquidity figures are rough orders of magnitude, not measured averages.
- XOM appears in two pairs (a coint pair with CVX and the leadlag). Avoid running both at once without accounting for the overlap.

Ideas considered and left out:
- VLO vs USO as a "crack squeeze" inverse pair. Refiner margins compress when crude spikes on supply shocks, but in demand-driven rallies both legs rise together. The sign flips by regime, so the pair cannot be given one expected sign. Left out.
- Crude (USO or BNO) leading E&P equities at a 1 to 10 day lag. Crude futures settle around 2:30pm ET and the equity closes at 4pm ET, so any crude-to-equity lead happens intraday or overnight, not over several days. Not proposed as a daily-data leadlag.
- MGY (Magnolia) as a follower. It listed in 2018 after a SPAC merger, so it fails the Oct 2016 history requirement. MTDR is used instead.

## Cross-pair structural flags

- **USO**: 1-for-8 reverse split in 2020 (per brief; verify date). Roll methodology changed during COVID, including the April 2020 negative front-month WTI episode. Splice or truncate the series at the change.
- **PR**: history under the CDEV ticker (Centennial Resource Development), which began trading around the Oct 2016 SPAC merger (verify first trade date). Ticker and exchange later changed to PR (verify).
- **MPC**: the Andeavor merger (Oct 2018) changed scale and business mix. Pre-2018 MPC is not the same company.
- **ET**: the 2018 ETE and ETP combination and later acquisitions (SemGroup, Enable, Crestwood; verify all) affect share counts and ticker history.
- **CVE**: the Husky merger (2021) and later acquisitions (verify) change the share base and business profile.
- **Tankers**: heavy 2019 to 2025 consolidation in the sector (verify specifics before using any tanker name not listed here).

## Pairs

### 1. XOM / CVX (coint, expected sign +)

- Tickers: XOM (leg_a), CVX (leg_b), both NYSE.
- Mechanism: Two US integrated majors with similar global upstream and downstream exposure, the same crude and product price drivers, and similar capital discipline and dividend policy. The spread should revert as relative capex, production growth and project timing average out. Divergence comes from large M&A or project events that shift one company's mix, such as CVX's Hess acquisition (verify close date) or XOM's Pioneer acquisition.
- What would break it: a permanent change in mix (upstream vs downstream, Permian or Guyana exposure), a large one-off deal, or a persistent difference in buyback pace.
- Liquidity and borrow: very high ADV (multi-billion dollars). Easy borrow.

### 2. SLB / HAL (coint, expected sign +)

- Tickers: SLB (leg_a), HAL (leg_b), both NYSE.
- Mechanism: The two largest oilfield-service firms are driven by E&P capex and activity. Relative valuation should revert because both respond to the same upstream spending cycle. HAL is weighted toward North American land and frac work. SLB is more international and offshore, so the spread diverges when the North American and international cycles decouple.
- What would break it: a regime where North American land services run well ahead of international, or an acquisition that reshapes SLB's mix (the ChampionX deal, verify close date).
- Liquidity and borrow: high ADV (hundreds of millions of dollars). Easy borrow.

### 3. FANG / PR (coint, expected sign +)

- Tickers: FANG (leg_a), PR (leg_b). FANG is on Nasdaq and PR is on NYSE (verify exchange history).
- Mechanism: Both are Permian pure-play producers exposed to the same Midland and Delaware price and cost drivers. Their relative valuation should revert as basin-level factors dominate. Spread divergence reflects relative acreage quality, Midland versus Delaware mix, and M&A.
- What would break it: a large acquisition by either company, or a shift in the Midland versus Delaware mix. FANG absorbed Endeavor (private) in 2024 (verify).
- Liquidity and borrow: FANG is liquid. PR is smaller, roughly $100M or more of ADV (verify). Borrow is generally available but may cost more for PR.
- Structural: PR history begins around the Oct 2016 SPAC merger as CDEV. Confirm the first trade date and splice ticker history.

### 4. VLO / MPC (coint, expected sign +)

- Tickers: VLO (leg_a), MPC (leg_b), both NYSE.
- Mechanism: Two large US refiners share crack-spread exposure and turnaround cycles, so relative valuation should revert. MPC carries a midstream business through MPLX, which lowers its beta to refining margins. VLO has its renewable diesel joint venture. Divergence comes from changes in these business mixes.
- What would break it: MPC's midstream share of earnings changing, a Gulf Coast hurricane affecting one footprint more than the other, or a regulatory change (for example, renewable fuel credit rules) that hits VLO and MPC differently.
- Liquidity and borrow: high ADV. Easy borrow.
- Structural: MPC history changes around the Andeavor merger (Oct 2018).

### 5. ET / EPD (coint, expected sign +)

- Tickers: ET (leg_a), EPD (leg_b), both NYSE. Both are partnerships.
- Mechanism: Two large fee-based crude and NGL pipeline MLPs are exposed to similar volume trends and yield-driven investor flows. The spread should revert because both trade on the same distribution-yield and rate sensitivity. Divergence comes from leverage differences, distribution changes, or large M&A.
- What would break it: a distribution cut or a balance-sheet stress at one partnership, or large acquisitions. ET has been acquisitive (verify deal list).
- Liquidity and borrow: both have good ADV (on the order of $100M or more; verify). MLP borrow can be expensive or tight, so check.
- Structural: use total-return series. MLP tax and distribution accounting affect price-only returns. ET ticker and entity history spans the 2018 ETE and ETP combination (verify).

### 6. SU / CVE (coint, expected sign +)

- Tickers: SU (leg_a), CVE (leg_b), both NYSE, quoted in USD.
- Mechanism: Both are Canadian integrated oil companies with oil sands upstream and downstream refining. Both are exposed to the same WCS-WTI differential, Canadian pipeline capacity and the CAD/USD rate. Their spread should revert on these common drivers.
- What would break it: a major acquisition or divestiture by either company, such as the Husky merger (2021) or later deals (verify). Also different downstream exposure and pipeline outages affecting one company more.
- Liquidity and borrow: both liquid, with CVE probably at the lower end (verify). Borrow is generally available.
- Alternative: CNQ (pure upstream) is a possible substitute for CVE, with a weaker pair logic because it has no downstream leg.

### 7. FRO / DHT (coint, expected sign +)

- Tickers: FRO (leg_a), DHT (leg_b), both NYSE. FRO is a foreign private issuer.
- Mechanism: Both are NYSE-listed crude tanker owners with heavy VLCC exposure, priced off the same spot tanker-rate cycle. The spread should revert because they respond to the same rate environment. Divergence comes from fleet mix (FRO also has Suezmax and other tonnage, while DHT is mostly VLCC), charter cover, and sanctions-related shocks.
- What would break it: a rate regime where one fleet mix benefits and the other does not, large fleet sales, or a new charter structure at one company.
- Liquidity and borrow: ADV is smaller than the majors (probably tens of millions of dollars or more; verify). Tanker borrow fees are often elevated, so flag borrow cost as a likely constraint.
- Alternative: INSW was considered as the second leg. Its NYSE history and predecessor ticker changes may not meet the 2016 start requirement (verify before using).

### 8. USO / BNO (coint, expected sign +)

- Tickers: USO (leg_a), BNO (leg_b), both NYSE Arca.
- Mechanism: These are futures-based funds tracking WTI (USO) and Brent (BNO). Their price spread is tied by the WTI-Brent arbitrage, which depends on US export capacity and freight. The spread should revert within the band set by export and shipping costs. It diverges during US export bottlenecks, regional supply shocks, or shifts in Atlantic basin balances.
- What would break it: structural changes to US exports or freight, roll and contango effects that differ between the two funds, or fund-level flows that dominate short-term moves. Both funds carry roll effects, so the ETF price spread is not the same as the spot spread.
- Liquidity and borrow: USO is very liquid. BNO is much smaller, perhaps tens of millions of dollars of ADV (verify). BNO borrow may be tighter.
- Structural: USO's 2020 reverse split and roll change (see cross-pair flags). Expect a series break around 2020, and the April 2020 negative-price episode needs special handling (exclude or winsorize).

### 9. JETS / XOP (inverse, expected sign -)

- Tickers: JETS (leg_a), XOP (leg_b). Both are US-listed ETFs (verify exchange).
- Mechanism: Fuel is one of the largest airline operating costs. Supply-driven crude spikes compress airline margins while E&P equity returns rise, giving a negative return correlation. A rotation (long one leg, short the other, flipping as the regime changes) would profit when the oil move is supply-driven.
- What would break it: demand-driven oil moves. In 2020 and during the 2021 reopening, airlines and E&Ps moved together, so the sign is regime-dependent. Airline fuel hedging also dampens sensitivity.
- Liquidity and borrow: XOP is liquid, likely hundreds of millions of dollars of ADV. JETS is smaller, perhaps around $100M (verify). ETF borrow is usually available. Verify.
- Alternative legs: DAL or UAL against XLE or XOP, using single names. These are noisier but may have more idiosyncratic exposure.

### 10. XOM to MTDR (leadlag, expected sign +; leader leg_a, follower leg_b)

- Tickers: XOM (leader, leg_a), MTDR (follower, leg_b), both NYSE.
- Mechanism: Large-cap majors absorb sector news first because of heavier analyst coverage and institutional flow. Mid-cap E&Ps reprice a few days later as analysts and funds catch up. This is the industry lead-lag pattern (large caps lead smaller firms), and it should show up as cross-correlation at a 1 to 10 day lag, strongest after oil and macro shocks.
- What would break it: firm-specific news at MTDR (asset sales, M&A, operational updates) overwhelms the lagged sector signal. Also, if the effect is intraday, daily close-to-close data will not capture it, and the lag may be too short to trade after costs.
- Liquidity and borrow: XOM is very liquid. MTDR is mid-cap, roughly $150M to $300M of ADV (verify). Borrow is probably moderate.
- Structural: MTDR history from its 2012 IPO (verify). No known major structural break in the window.

## Merged, delisted or renamed names (survivorship)

These names were important in this space during Oct 2016 to today. A backtest on current listings cannot include them. Entries marked "verify" are from memory and need checking against the listing history.

Acquired or merged out of existence:
- Anadarko Petroleum (APC): acquired by Occidental, Aug 2019.
- Noble Energy (NBL): acquired by Chevron, Oct 2020.
- Concho Resources (CXO): acquired by ConocoPhillips, Jan 2021.
- Pioneer Natural Resources (PXD): acquired by Exxon Mobil, May 2024.
- Marathon Oil (MRO): acquired by ConocoPhillips, Nov 2024.
- Hess (HES): acquired by Chevron, mid-2025 (verify).
- Cimarex Energy (XEC): merged with Cabot, Oct 2021.
- WPX Energy (WPX): merged into Devon, Jan 2021.
- Parsley Energy (PE): acquired by Pioneer, Jan 2021.
- Southwestern Energy (SWN): merged into Chesapeake, Oct 2024 (verify).
- Callon Petroleum (CPE): acquired by APA, 2024 (verify).
- Whiting Petroleum (WLL) and Oasis Petroleum (OAS): combined into Chord Energy (CHRD), 2022 (verify).
- Denbury (DEN): acquired by Exxon Mobil, late 2023 (verify).
- Continental Resources (CLR): taken private by the Hamm family, around 2022 (verify).
- Andeavor (ANDV): acquired by Marathon Petroleum, Oct 2018.
- Andeavor Logistics (ANDX): acquired by MPLX, 2019 (verify).
- Magellan Midstream (MMP): acquired by ONEOK, Sep 2023.
- Crestwood Equity (CEQP): acquired by Energy Transfer, late 2023 (verify).
- Enable Midstream (ENBL): acquired by Energy Transfer, late 2021 (verify).
- SemGroup (SEMG): acquired by Energy Transfer, Dec 2019 (verify).
- Enbridge Energy Partners (EEP): merged into Enbridge, Dec 2018 (verify).
- Valero Energy Partners (VLP): acquired by Valero, 2019.
- HollyFrontier (HFC): combined with Sinclair; now HF Sinclair (DINO), 2022.
- Frank's International (FI): merged with Expro, 2021.
- Diamond Offshore (DO): acquired by Noble Corp, 2024 (verify).
- Rowan Companies (RDC): merged into Ensco (now Valaris), 2019.
- Gener8 Maritime (GNRT): acquired by Euronav, 2018.
- Overseas Shipholding Group (OSG): acquired, 2024 (verify).
- Euronav (EURN): combined into CMB.Tech, 2025 (verify).
- Husky Energy (HSE, TSX): combined into Cenovus, 2021. Not US-listed.

Bankrupt or delisted:
- Spirit Airlines (SAVE): second Chapter 11 filing, Aug 2025. Current listing status uncertain (verify).
- Hawaiian Holdings (HA): acquired by Alaska Air Group, 2024 (verify).
- Ultra Petroleum (UPL), EP Energy (EPE), Sanchez Energy (SN), Basic Energy Services (BAS), Pacific Drilling (PACD): bankruptcies and delistings (verify each).

Renamed and continuing (ticker changes that affect history splicing):
- Chesapeake Energy (CHK) renamed Expand Energy (EXE), 2024.
- Cabot Oil and Gas (COG) renamed Coterra Energy (CTRA), 2021.
- Encana (ECA) renamed Ovintiv (OVV), 2020.
- Centennial Resource Development (CDEV) renamed Permian Resources (PR), around 2022 (verify).
- Apache (APA) now APA Corp, same ticker.
