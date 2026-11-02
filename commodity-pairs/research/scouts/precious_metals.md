# Precious metals: pair candidates (scout, 2026-10-27)

Scope: gold, silver, platinum and palladium. Candidates cover bullion trusts, senior and junior miners, royalty and streaming companies, and one consumer input-cost pair. This is economic reasoning only. Nothing has been backtested or downloaded.

Caveat on tickers: tickers, listing status and ETF launch dates are from memory and were not checked against live listings. The quant team should verify each ticker before use. Liquidity and borrow comments are qualitative and marked "verify" where uncertain. Dollar-volume estimates are rough tiers, not measured figures.

Considered and excluded:
- Leveraged or inverse pairs that are related by construction (DUST/NUGT, ZSL/AGQ, GLL/UGL). Their relationship is mechanical, not economic. They should be flagged so the quant team can exclude them from statistical tests.
- Near-identical physical gold trusts (GLD, IAU, GLDM). They hold the same underlying, so the spread reflects fees and creation/redemption noise. GLDM also launched in 2018, after the Oct 2016 start of the window.
- Miner versus equipment-supplier pairs. US-listed mining-equipment exposure is mostly diversified industrials (for example CAT), which dilutes any precious-metals signal.

Pair summary:

| # | Leg A (leader if leadlag) | Leg B | Type | Sign |
|---|---|---|---|---|
| 1 | GLD | GDX | coint | + |
| 2 | GLD | SLV | coint | + |
| 3 | PPLT | PALL | coint | + |
| 4 | GDX | GDXJ | leadlag | + |
| 5 | SLV | SILJ | leadlag | + |
| 6 | NEM | AEM | coint | + |
| 7 | FNV | RGLD | coint | + |
| 8 | WPM | RGLD | coint | + |
| 9 | PAAS | HL | coint | + |
| 10 | GLD | SIG | inverse | - |

## Pairs

### 1. GLD / GDX (coint, expected sign +)

- Mechanism: Gold miners are levered claims on the gold price. Margin is roughly spot minus all-in sustaining cost, so a 1% move in gold typically moves miner equities by more than 1%. That ties the GDX/GLD relative value to cost curves, balance-sheet health and equity risk appetite. Flow-driven dislocations (sell-offs, fund redemptions) should revert as miners reprice toward spot. The relationship breaks under sustained cost inflation (energy, labour, royalties), a sector re-rating driven by M&A, or equity-market stress that dominates gold's move.
- Liquidity and borrow: GLD is very liquid (very high dollar volume). GDX is also very liquid. Both are generally easy to borrow; verify. Both have long histories with no late listing.

### 2. GLD / SLV (coint, expected sign +)

- Mechanism: Gold is mainly a monetary store of value, while roughly half of silver demand is industrial (electronics, solar, brazing). The silver/gold ratio therefore reflects the balance between safe-haven flows and the industrial cycle. Historically the ratio has oscillated within broad bands, and spikes driven by panic or industrial news should partly revert as relative-value flows return. Breaks come from structural shifts in silver's industrial intensity or from long regime moves in central-bank gold buying that re-anchor the ratio.
- Liquidity and borrow: Both are very liquid. SLV borrow is generally easy; verify. Both are physical trusts that track spot, so the spread is close to the spot ratio. Check that the sample covers the 2020 ratio spike and its reversion.

### 3. PPLT / PALL (coint, expected sign +)

- Mechanism: Platinum and palladium substitute in autocatalysts (platinum more in diesel, palladium more in gasoline), and both are concentrated in South African and Russian supply. Their price ratio should therefore be bounded by substitution and recycling economics. Supply shocks (sanctions, mine outages) push the ratio away temporarily, and it should revert as substitution and producer responses adjust. Breaks come from prolonged shortage of one metal, from EV-driven loss of autocatalyst demand for one of them, or from a multi-year regime change in relative pricing.
- Liquidity and borrow: Both are materially less liquid than the gold and silver trusts. Dollar volume may sit near or below the $20M threshold on some days, so this is borderline. Borrow may be limited or fee-heavy; verify. Both trusts were launched around 2010 under the ETFS name (now abrdn sponsorship); tickers are unchanged, but verify.

### 4. GDX / GDXJ (leadlag, leader = GDX, expected sign +)

- Mechanism: Capital in gold equities usually rotates from large, liquid senior producers to thinly covered juniors. Senior-producer moves should therefore lead junior moves by a few trading days as risk appetite and exploration-financing sentiment spread. Juniors have fewer analysts and thinner order books, which slows their price response. The lag should disappear when a common same-day macro shock hits both, or when junior-specific news (discoveries, financings) dominates.
- Liquidity and borrow: GDX and GDXJ are both very liquid to highly liquid. GDXJ can become hard to borrow at times; verify. The quant team should test whether the lag survives controls for same-day market moves.

### 5. SLV / SILJ (leadlag, leader = SLV, expected sign +)

- Mechanism: SLV tracks spot silver in near-real time, while junior silver equities reprice more slowly because of thin liquidity, analyst lag and stale foreign-listed closes. SLV moves should therefore predict SILJ moves over one to several days. The effect should weaken in high-volume regimes where miners react the same day. Breaks come from company-specific news, from base-metal moves (zinc, lead, copper) that drive miner earnings independently of silver, and from stale-price artifacts that look like lead-lag but are data-timing effects.
- Liquidity and borrow: SILJ liquidity is moderate and may be borderline against the $20M threshold. Its holdings include foreign-listed names whose closes can be stale, so check for timing artifacts. Borrow fee spikes are possible; verify.

### 6. NEM / AEM (coint, expected sign +)

- Mechanism: The two largest senior producers have similar gold beta, similar cost-discipline strategies and overlapping institutional holders. Their relative price should therefore be anchored by common gold exposure. Idiosyncratic shocks (M&A, reserve write-downs, jurisdictional or operating news) create transient divergence that should revert as the market reprices the affected name. Breaks come from a structural change in one company's asset mix, or from a large acquisition that re-bases its share count and risk profile.
- Liquidity and borrow: Both are highly liquid. Newmont has had large acquisitions (Goldcorp in 2019, Newcrest in 2023), so check break dates against share-count changes. Borrow is likely easy; verify.

### 7. FNV / RGLD (coint, expected sign +)

- Mechanism: Franco-Nevada and Royal Gold run similar diversified royalty and streaming models with heavy gold exposure and low operating leverage, so their valuation ratio should be anchored by the shared business model. Divergence from asset-level events (a major ramp-up or write-down in one portfolio) or from sentiment rotation should revert as investors re-equalize. Breaks come from portfolio-level differences (metal mix, jurisdiction concentration) or from acquisitions that change one company's structure.
- Liquidity and borrow: Liquidity is moderate to high. FNV trades on the NYSE and RGLD on the Nasdaq. Borrow is usually available; verify. Royal Gold's acquisition history may add jumps to the series.

### 8. WPM / RGLD (coint, expected sign +)

- Mechanism: Wheaton has historically carried a silver-weighted stream book while Royal Gold is gold-weighted, so the WPM/RGLD ratio should loosely track the silver/gold price ratio and relative equity sentiment. When the metal ratio mean-reverts, the equity ratio should follow with a lag. Breaks come from changes in stream mix (for example, new gold-heavy streams at Wheaton), idiosyncratic asset events, or a metal ratio that keeps trending.
- Liquidity and borrow: Liquidity is moderate to high; borrow verify. The current metal mix of each company needs checking against recent reports, since the mix claim here is from memory. Wheaton Precious Metals was Silver Wheaton (ticker SLW) until its 2017 rename, so pre-2017 history needs ticker mapping.

### 9. PAAS / HL (coint, expected sign +)

- Mechanism: Pan American Silver and Hecla are both silver-weighted mid-tier producers with overlapping silver exposure and a shared silver-focused investor base. Their relative price should therefore be anchored by silver exposure and jurisdictional risk premia. Idiosyncratic operating problems or M&A create transient divergence that should revert as the market reprices. Breaks come from a mine-level failure or a large acquisition that shifts one company's asset base.
- Liquidity and borrow: PAAS trades on the Nasdaq and HL on the NYSE. Liquidity is moderate. Pan American's acquisition of Tahoe Resources (2019) changed its share count, so check the break. Borrow verify.

### 10. GLD / SIG (inverse, expected sign -, low confidence)

- Mechanism: Signet buys gold as a jewelry input, so rapid gold rallies can compress its gross margin (partly hedged, and lagged through inventory accounting) and may dampen discretionary jewelry demand. That implies a negative relationship after market beta is removed. Breaks are likely: consumer-discretionary beta, rates and price pass-through can dominate, so the raw correlation may be positive. Treat this as a low-confidence candidate rather than a clean rotation.
- Liquidity and borrow: Signet is moderately liquid. Borrow is uncertain; verify. The quant team should test beta-neutral returns (for example against a broad equity benchmark) before drawing conclusions.

## Merged / delisted names (survivorship)

These names were relevant during the Oct 2016 onward window but cannot be in a backtest that uses only current listings. Dates and acquirers are from memory; verify the ones marked.

- Goldcorp (GG, NYSE): acquired by Newmont, completed April 2019.
- Randgold Resources (GOLD, Nasdaq): acquired by Barrick, completed January 2019. Note the ticker collision: GOLD later became Barrick's NYSE ticker, so vendor joins on GOLD can mix two different companies.
- Barrick Gold legacy ABX (NYSE): renamed to Barrick Gold under the GOLD ticker in 2019. Map ABX history to GOLD.
- Newcrest Mining (NCM, ASX): acquired by Newmont, completed November 2023. Check whether an NYSE ADR existed and was delisted.
- Stillwater Mining (SWC, NYSE): acquired by Sibanye Gold (later Sibanye-Stillwater), completed 2017.
- Sibanye Gold (SBGL, NYSE ADS): replaced by SBSW after the 2017 Stillwater deal. Map pre-2017 history to SBSW. Verify.
- Silver Wheaton (SLW, NYSE): renamed Wheaton Precious Metals (WPM) in 2017. Map SLW history to WPM.
- Tahoe Resources (TAHO, NYSE): acquired by Pan American Silver, completed March 2019.
- Klondex Mines (KLDX, NYSE American / TSX): acquired by Hecla, completed 2018. Verify.
- Pershing Gold (PGLC, Nasdaq): acquired by McEwen Mining, 2019. Verify.
- Lonmin (LMI, London): acquired by Sibanye-Stillwater, 2019. Primary listing was non-US; any OTC ADR is not an exchange listing.
- Joy Global (JOY, Nasdaq; mining equipment): acquired by Komatsu, 2017. Relevant to any supplier-type pair.
- Richmont Mines (RIC, NYSE American): acquired by Alamos Gold, around 2021. Verify.
- Great Panther Mining (GPL, NYSE American): acquired by Dowa, around 2023. Verify.
- Sandstorm Gold (SAND, NYSE): acquisition by Royal Gold announced in 2025. Verify whether it has closed and the exact delisting date.

Status uncertain (could not confirm from memory, so check the exchange history): Yamana Gold (AUY, NYSE), Golden Star Resources (GSS, NYSE American), Gold Standard Ventures (GSV, NYSE American), and any 2025-2026 mid-tier gold and silver combinations that may have closed after my knowledge cutoff.

ETF sponsor renames (tickers unchanged, so not delistings but still relevant to name mapping): the ETFS physical platinum, palladium and silver trusts moved to abrdn branding (PPLT, PALL, SIVR). Verify.
