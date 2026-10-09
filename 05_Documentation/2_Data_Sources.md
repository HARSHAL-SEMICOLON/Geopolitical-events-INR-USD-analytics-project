# Data sources

All files were retrieved on **30 Sep 2026** through a web browser, because the official sites were not reachable from a script. Raw files are kept unmodified in `01_Data/1_Raw/`. Full metadata for every series is in `01_Data/2_Reference/Series_Catalog.csv`, which loads into `dim_series`.

## Primary: USD/INR from the Reserve Bank of India

| Item | Detail |
|---|---|
| Where | RBI **Database on Indian Economy (DBIE)** → Statistics → Financial Market → Forex Market → *Daily Exchange Rate of the Indian Rupee* — https://data.rbi.org.in/DBIE/ |
| How | Opened the report in DBIE (SAP BusinessObjects), then Export → TXT (tab-delimited) |
| Raw file | `01_Data/1_Raw/RBI/RBI_USDINR_Reference_Rate_Daily.txt`, 25 Aug 1998 → **29 Sep 2026** |
| Columns | Date · US Dollar · Pound Sterling · Euro · Japanese Yen (₹ per unit; yen per 100) |
| Series used | **US Dollar** column → `USDINR_RBI` |
| What it is | The official daily **reference rate**. RBI computed it until 9 Jul 2018; since 10 Jul 2018 **FBIL** (Financial Benchmarks India Ltd) has computed it from market quotes in the midday window, published about 13:30 IST. The table notes say it is "based on RBI Reference Rate". |

### Second RBI table, used as a cross-check

DBIE → *Daily Interbank Forex Rates (USD vis-a-vis INR)* is saved as `RBI_USDINR_Interbank_Rates_Daily.txt` and runs 8 Aug 2000 → 30 Jun 2026. It contains interbank open, high, low and close, plus its own copy of the reference rate (`USDINR_RBI_IBTABLE`).

**How the two RBI tables compare** (logged in `dq_issues`):

| Finding | Count | Treatment |
|---|---|---|
| Identical on shared dates | 2,815 of 3,472 | — |
| Rounding differences of ≤ ₹0.005 (all 2012–2014) | 628 | primary value kept |
| Real conflicts | 29 | primary value kept, each date flagged. 25 are ₹0.005 rounding; the substantive ones are 18 Jul 2013 (60.051 vs 59.71) and 29 Oct–1 Nov 2019, where one table is shifted by a day. No event window's endpoints touch these dates. |
| Interbank table repeats the previous day's value exactly | 11 dates, mostly **1 April** (banks' annual closing) | Not in the primary table, so excluded. Keeping them would create fake zero-return days and shift trading-day counts. |

This is why the *Daily Exchange Rate* table is primary: it follows the holiday calendar, has no carried-forward copies, and runs to September 2026.

**Interbank-table quirk:** RBI labels "High" and "Low" from the rupee's side. "High" is the strongest rupee, i.e. the lowest INR per USD, so High < Low on 95% of rows. These columns are loaded as `inr_strongest` / `inr_weakest`.

**Why the reference rate rather than the interbank close?** It is the official benchmark: it is used for contract settlement and customs, it is published by the central bank, and it has the fewest gaps.

## Cross-check: USD/INR from the Federal Reserve (FRED)

`DEXINUS` is the Fed **H.10** noon buying rate in New York, via FRED (https://fred.stlouisfed.org/series/DEXINUS). It validates the RBI series (`dq_fx_crosscheck`) and provides a second "FRED basis" calendar for robustness. It is **never spliced** into the RBI series.

## India CPI (MoSPI, via RBI DBIE)

* **Where:** DBIE → Statistics → Real Sector → Prices & Wages → *Consumer Price Index – Rural, Urban, Combined (State-Wise)*. Only the **ALL INDIA** rows are used. File: `RBI_CPI_Rural_Urban_Combined_Statewise.txt`.
* **Series used:** *General Index, Combined*. The index level and the **published YoY inflation (%)** are both loaded.
* **Base years:** the file holds three blocks. The 2010=100 block is used before Jan 2014, the 2012=100 block for Jan 2014 – Dec 2025, and **2024=100 (MoSPI's new series) from Jan 2026**. Index levels are not comparable across a base change, so charts use the **published YoY**. The base is stored on every row (`fact_macro.series_version`).
* **Validation:** Aug-2026 YoY = **4.82%**, identical to the figure on the DBIE homepage banner on 30 Sep 2026.

## RBI foreign-exchange intervention

* **Where:** RBI Bulletin **Table No. 4 – Sale/Purchase of U.S. Dollar by the RBI**, via DBIE → Forex Market. File: `RBI_FX_Intervention_Sale_Purchase_USD.xlsx`, sheet 1.
* **Series:** net purchase(+)/sale(−) of USD (US$ mn), gross purchases, gross sales, and the outstanding net forward book. Monthly, Jun 1995 → Jul 2026.
* **Definition (RBI note):** includes the purchase and sale legs of swaps and outright forwards, **by value date**.
* **Convention:** in this table `-` means **nil**, so it is loaded as 0. This is the only place a dash becomes zero; elsewhere a dash means missing.
* **Use:** each event window's context shows RBI's net FX activity summed over the **calendar months the window touches** (`fact_event_window_context.rbi_net_fx_usd_mn`). This is monthly data, so it cannot be tied to specific days.

## Other series

| Series | Source (original publisher → distributor) | Code | Frequency | Timestamp |
|---|---|---|---|---|
| Brent crude spot | US EIA → FRED | DCOILBRENTEU | Daily | Europe/US end of day |
| Gold | **LBMA Gold Price AM** (ICE Benchmark Administration) → LBMA public JSON `prices.lbma.org.uk/json/gold_am.json` | USD field | Daily (London) | 10:30 London |
| Nifty 50 | NSE Indices Ltd, niftyindices.com historical data (14 yearly CSVs, 2013 → 29 Sep 2026) | NIFTY 50 | Daily | 15:30 IST close |
| Broad US dollar index | Federal Reserve H.10 → FRED | DTWEXBGS | Daily | NY noon |
| VIX | Cboe → FRED | VIXCLS | Daily | US close |
| US 10-year Treasury yield | Federal Reserve H.15 → FRED | DGS10 | Daily | US close |
| Fed funds target (upper) | Federal Reserve → FRED | DFEDTARU | Daily (step) | FOMC decision |
| Effective fed funds rate | NY Fed → FRED | DFF | Daily | — |
| RBI repo rate | RBI monetary policy statements and MPC resolutions (hand-compiled in `01_Data/2_Reference/RBI_Repo_Rate_History.csv`) | — | Event | Announcement date |
| US CPI (all items, SA) | BLS → FRED | CPIAUCSL | Monthly | — |
| India CPI (OECD, superseded) | OECD MEI → FRED (ends Mar 2025) | INDCPIALLMINMEI | Monthly | Kept only as a cross-check |
| India reserves excl. gold | IMF IFS → FRED | TRESEGINM052N | Monthly | End of month |

### Why these series: each one answers a specific confounder

| Series | Confounder it helps separate |
|---|---|
| Brent | Oil prices. India imports most of its crude, so the oil bill affects dollar demand. |
| Broad US dollar index | US dollar strength: is it the rupee moving, or the dollar against everyone? |
| VIX | Global risk sentiment (risk-off drives outflows from emerging markets) |
| US 10Y, Fed funds, RBI repo, rate differential | Monetary policy and interest-rate differentials |
| **RBI FX intervention** | Central-bank smoothing. A small rupee move can hide large RBI dollar sales. |
| Gold | Safe-haven demand; India is also a large gold importer |
| Nifty 50 | Domestic risk appetite and a proxy for equity flows |
| CPI (India and US) | Inflation differential (slow-moving context) |
| FX reserves | RBI's capacity to intervene |

## Still not included

* FPI flows (NSDL) and the trade balance, which are the main remaining omitted channels.
* Weekly FX reserves from the RBI Weekly Statistical Supplement (monthly IMF data is used instead).
