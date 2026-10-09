# Event definitions

Machine-readable versions: `01_Data/2_Reference/Event_List.csv` (→ `dim_event`) and `01_Data/2_Reference/Event_Milestones.csv` (→ `dim_event_milestone`).

## Selection criteria (fixed before any market data was examined)

An event is included only if **all** of these hold:

1. **Nature:** interstate military action, a major armed attack triggering a military response, or an armed standoff between states. No elections, trade disputes, sanctions announcements or pandemics. Those appear as *confounders*, not events.
2. **Relevance to INR:** India is a direct party, **or** the conflict involves a major oil or gas producer or a strategic chokepoint (Russia, Iran, the Persian Gulf).
3. **Datable:** a start date, and ideally a time of day, can be taken from an **official statement** (government, UN) or a reputable wire or news report quoting one.
4. **Coverage:** 2014–2026, so there are ≥ 30 trading days of data before the first event and a ~3-year baseline.
5. **Separable:** where two episodes are weeks apart (Pahalgam → Operation Sindoor), they are treated as **one episode** with milestones, not as separate events, to avoid double counting.

**Excluded, with reasons:**

* Uri attack (18 Sep 2016): folded into E02 as a pre-event milestone.
* Red Sea shipping attacks (from Nov 2023): inside E08's windows; no single defensible date.
* The 2025 US tariff actions: trade policy, not geopolitical conflict. Listed as a confounder for E10/E11.
* Kargil 1999 and earlier events: before the analysis period.

## Anchor-date rule

`anchor_date` = the date the information was **public during or before Indian market hours**. Then t(0) = the first RBI trading day on or after the anchor (see `METHODOLOGY.md` §3).

| ID | Event | Start | End | Anchor | Why the anchor differs from the start (if it does) | India a party? |
|---|---|---|---|---|---|---|
| E01 | Russia authorises force / Crimea annexation | 2014-03-01 | 2014-03-18 | 2014-03-01 → t0 3 Mar | Saturday | N |
| E02 | Surgical strikes across the LoC | 2016-09-29 | 2016-09-29 | 2016-09-29 | Announced during market hours | Y |
| E03 | Doklam standoff | 2017-06-16 | 2017-08-28 | **2017-06-30** | The start was not public; anchor = first MEA statement | Y |
| E04 | Pulwama attack → Balakot strike | 2019-02-14 | 2019-03-01 | **2019-02-15** | Attack about 15:15 IST, effectively after the close | Y |
| E05 | Killing of Qassem Soleimani | 2020-01-03 | 2020-01-08 | 2020-01-03 | About 03:30 IST, before the open | N |
| E06 | Galwan Valley clash | 2020-06-15 | 2020-06-15 | **2020-06-16** | Night clash; Army statement next day | Y |
| E07 | Russia's full-scale invasion of Ukraine | 2022-02-24 | ongoing | 2022-02-24 | About 08:20 IST, before the open | N |
| E08 | Hamas attack on Israel / Gaza war | 2023-10-07 | ongoing | 2023-10-09 | Saturday | N |
| E09 | Iran's direct strike on Israel | 2024-04-13 | 2024-04-19 | 2024-04-15 | Saturday night | N |
| E10 | Pahalgam attack → Operation Sindoor | 2025-04-22 | 2025-05-10 | **2025-04-23** | Reported late afternoon IST | Y |
| E11 | Israel–Iran "12-day war" | 2025-06-13 | 2025-06-24 | 2025-06-13 | About 04:30 IST, before the open | N |
| E12 | US–Israel war on Iran / Hormuz disruption | 2026-02-28 | 2026-04-08 | 2026-02-28 → t0 2 Mar | Saturday | N |
| E13 | Resumed US strikes on Iran | 2026-07-08 | ongoing | 2026-07-08 | — (+90 window still partial at build date) | N |

Every event's source (organisation, title, URL, **publication date**, source type), selection rationale and known concurrent factors are in `Event_List.csv`. Milestones (for example Balakot 26 Feb 2019, Operation Sindoor 7 May 2025, the Hormuz closure around 18–20 Mar 2026 and the ceasefire on 8 Apr 2026) have their own sources in `Event_Milestones.csv`. Secondary sources (Wikipedia summaries) are marked `Secondary` or `Secondary - verify`.

**Note on E12 and E13:** these occurred after the analyst's AI assistant's training cutoff (Jun 2026). Their facts come **only** from the cited sources (UN, CNN, Al Jazeera, World Bank), not from memory.

## Source hierarchy used

1. Official government or UN statement (MEA, PIB, Kremlin, UN Secretary-General)
2. Mirror of an official statement (GlobalSecurity.org copies of PIB/MEA text)
3. Wire or major news outlet quoting an official statement
4. Secondary compilations: used only for context milestones, and flagged
