# Interview guide: explaining this project

Short answers first, then the detail to use if pushed. All numbers come from `02_Database/geo_inr_analytics.db` (build of 30 Sep 2026).

---

## 30-second pitch

> "I built an event-window analytics system to study how USD/INR behaved around 13 geopolitical events from 2014 to 2026: India–Pakistan and India–China crises, the Russia–Ukraine war, and the Middle East conflicts up to the 2026 Iran war. The rupee rate comes from the RBI's DBIE database, and I cross-check it against the Fed's H.10 series. I aligned Brent, gold, the Nifty, the dollar index, VIX, US yields, policy rates, CPI and RBI's own FX intervention onto the Indian trading calendar, computed returns over eight trading-day windows per event, and loaded everything into a SQLite star schema that feeds a 7-page Power BI report. The design point I care most about: it measures temporal association, not causation. Every window also shows the policy changes, overlapping events and dollar moves that happened at the same time."

---

## 1. Where did the USD/INR data come from?

**Short:** The RBI's Database on Indian Economy (DBIE), table *Daily Exchange Rate of the Indian Rupee*: the official RBI/FBIL **reference rate**, Aug 1998 to 29 Sep 2026. I validated it against a second DBIE table and against the Federal Reserve H.10 noon rate (FRED `DEXINUS`).

**Detail:**
- The reference rate was computed by RBI until July 2018 and by **FBIL** since 10 Jul 2018. DBIE carries it as one continuous series, published around 13:30 IST.
- I chose the reference rate over the interbank close because it's the official benchmark and has fewer gaps.
- **Two RBI tables disagreed, and I resolved it with evidence.** DBIE's *Daily Interbank Forex Rates* table also carries the reference rate. On 3,472 shared dates, 2,815 are identical and 628 differ only by rounding. But the interbank table has **11 carried-forward copies**, mostly on 1 April (the banks' annual closing day), where it repeats the previous day's value. Those would create fake zero-return days and shift every trading-day count. So the *Daily Exchange Rate* table is primary, and the 29 remaining conflicts are flagged, not edited.
- **Another quirk:** in the interbank table, RBI's "High" and "Low" columns are quoted from the rupee's side. "High" is the strongest rupee, i.e. the *lower* INR-per-USD number, so High < Low on 95% of rows. I renamed them `inr_strongest` / `inr_weakest` rather than silently swapping.
- **Cross-check against the Fed:** on 3,180 common days the mean absolute gap between FRED and RBI is **0.17%**. Daily returns correlate only **0.56**, but weekly returns correlate **0.89**. The difference is the ~9-hour gap between the two fixings, not an error in either series.
- FRED is kept as a **separate basis** (its own calendar) for robustness. I never splice two sources into one line.

## 2. How were the event dates defined?

**Short:** Each event has a start date from an official or wire source, and a separate **anchor date**: the day the information became public to Indian markets. Windows are measured from the anchor.

**Detail:**
- Selection criteria were fixed before looking at market data: interstate military action or a major armed attack; India a party or a major oil producer or chokepoint involved; datable from an official source; 2014–2026 (`05_Documentation/3_Event_Definitions.md`).
- Every event stores the source organisation, title, URL, **publication date** and source type.
- Examples where the anchor differs from the start:
  - **Doklam:** the standoff began 16 Jun 2017 but wasn't public. The anchor is the MEA press release on 30 Jun 2017.
  - **Pulwama:** the attack was around 15:15 IST, effectively after the market close, so the anchor is the next day.
  - **Galwan:** the clash was at night on 15 Jun 2020 and the Army statement came on the 16th.
  - **Weekend events** (Hamas attack, 2026 Iran strikes) move to the next trading day automatically.
- E12/E13 (2026) happened after my AI assistant's training cutoff, so those facts come only from cited UN, CNN, Al Jazeera and World Bank sources.

## 3. How were the event windows constructed?

**Short:** On the Indian FX trading calendar, t(0) is the first trading day on or after the anchor, and t(−1) is the last close before the news. Pre windows run t(−30/−14/−7)→t(−1), the event day runs t(−1)→t(0), and post windows run t(−1)→t(+7/+14/+30/+90), counted in trading days.

**Detail:**
- "Trading day" = one row of the calendar, so weekends and holidays are skipped automatically.
- Everything is measured from t(−1) so the event-day reaction is included in every post window and never double-counted.
- If the calendar ends before t(+k), the window is labelled **partial**. E13 (8 Jul 2026) had only about 60 trading days of data by the build date.
- Overlap detection flags windows containing another event's anchor. E10's +90 window contains E11, and E12's +90 contains E13.
- Each window also lists the **RBI repo changes, FOMC changes and RBI's net dollar purchases/sales in the months it covers**. E05's +90 window (Jan–May 2020) contains a 75 bp and a 40 bp RBI cut plus two emergency Fed cuts, because it overlaps the COVID crash.

## 4. How were returns calculated?

- **USD/INR return** = P_end / P_start − 1. Positive means the **rupee weakened**.
- **INR % change** = P_start / P_end − 1, the rupee's own value. It isn't simply the negative of the USD/INR return: +5% USD/INR is −4.76% for the rupee.
- **Log returns** ln(P_t/P_{t−1}) are used for volatility and correlation because they add up over time.
- **Yields and policy rates** use changes in percentage points, never "% of a yield".
- **Worked example (Russia invades Ukraine, E07):** RBI reference 74.6224 on 23 Feb 2022 → 75.2578 on 24 Feb. 75.2578 / 74.6224 − 1 = **+0.85%**, so the rupee weakened 0.84%. That move was at about the 99th percentile (98.8) of one-day moves in the prior three years.

## 5. How were missing dates handled?

- Blank, `.` and `-` values are **no observation, never zero**.
- Missing days are **not interpolated**. Returns run from one real observation to the next, and `days_since_prev_obs` records the gap (a Monday return carries three days of news).
- Holidays are simply absent from RBI's table (3 are listed explicitly with `-`). The only place a dash becomes 0 is RBI's intervention table, where RBI's own convention says `-` means **nil**.
- Anything unusual goes to `dq_issues` and the Data Quality page: the two-table RBI conflicts, the missing Oct 2025 US CPI (not published during the US government shutdown), large daily moves (flagged, not removed), and Nifty boundary days repeated across yearly files (de-duplicated). A year-coverage check caught a missing 2022 Nifty file during the build. It was flagged, not filled, until the file was added.

## 6. How were different data frequencies aligned?

- **Daily foreign series** (Brent, gold, VIX, dollar index, US 10Y) are aligned to the Indian calendar with an **as-of join**: the latest value on or before the Indian date, at most **5 calendar days** old, and **never back-filled**, so there is no look-ahead. On the RBI calendar, 97.6% of Brent values are exact same-day matches, 2.4% are carried forward, and none are missing.
- **Step series** (repo rate, Fed funds target) carry forward without a cap, because a policy rate stays in force until changed.
- **Monthly series** (CPI, reserves, RBI intervention) stay monthly in `fact_macro`. I don't interpolate them to daily, because that invents data. For event windows, intervention is summed over the calendar months the window touches, and I say so, because it's coarser than the window.
- **CPI base change:** MoSPI moved CPI from base 2012 to **base 2024 in January 2026**. Index levels aren't comparable across the break, so I use the **published YoY** and store the base year on every row. Check: Aug-2026 = 4.82%, identical to RBI's homepage.
- **Time-zone caveat:** "same date" isn't "same moment". The RBI fixes at 13:30 IST; Brent, VIX and US yields close hours later. Same-day correlations are therefore biased towards zero, and an event-day move in Brent can contain news from after the Indian fix. That's why I lean on multi-day windows and report weekly correlation as a robustness check.

## 7. Why doesn't correlation prove causation, using this project's own data?

1. **Confounders move at the same time.** After E05 (Soleimani, Jan 2020), USD/INR rose **6.02%** over 90 trading days. That window runs to 26 May 2020, straight through the COVID crash, with two emergency Fed cuts and two RBI cuts. Attributing the 6% to the Soleimani strike would be absurd.
2. **Oil is both a channel and a confounder.** On the E02 event day (Sep 2016 surgical strikes), Brent rose 6.5%, but that was OPEC's Algiers output deal, not India–Pakistan.
3. **The dollar moves against everyone.** In E07's +90 window (Feb–Jul 2022), USD/INR rose 6.42%, but the Fed's broad dollar index rose **7.53%** during the 2022 hiking cycle. Relative to the dollar's move against 26 currencies, the rupee did *better* than average (−1.11 pp). The headline "rupee fell 6% after the war" hides that.
4. **Source and timing sensitivity.** For Galwan (E06), the event-day change is **−0.35%** on the RBI basis but **+0.29%** on the FRED basis. If the sign flips with the measurement clock, one day tells you very little.
5. **The central bank intervenes.** The RBI actively smooths the rupee, so a small move can hide large pressure. Over Feb–Apr 2022 (E07's first 30 days), RBI was a net **seller of US$17.4 bn**. The rupee's move was dampened, so the market move alone understates the pressure. And in the 30 days after the Hamas attack (E08, Oct 2023), USD/INR's annualised volatility was **1.1%**, against roughly 4–6% in most other windows.
6. **Anticipation, overlap and sample size.** Tensions build before a dated event, windows overlap, and with 13 events there's no counterfactual. Correlations over about 30 days have a noise band of roughly ±0.36.

**What I *can* say:** "USD/INR rose 3.17% in the 30 trading days after the 2026 Iran war began. That was larger than every same-length move in the prior three years (100th percentile), during a period when Brent rose 59% and RBI was a net seller of US$11.3 bn. That's a strong temporal association and consistent with an oil-import channel. But the Fed, global risk-off, capital flows and RBI intervention were all changing at the same time, and this design can't separate them."

---

## Likely follow-ups

| Question | Answer |
|---|---|
| Why trading days, not calendar days? | Markets price information only when open. Calendar windows would mix different numbers of price observations across events. |
| Why t(−1) as the base, not t(0)? | t(0) already contains the reaction, so using it would hide the event-day move. |
| Why not a regression or a formal event study with abnormal returns? | With 13 events and heavy confounding, a model would give false precision. The next step would be a market-model benchmark, e.g. USD/INR regressed on the broad dollar index over a clean estimation window, and cumulative abnormal returns. `usdinr_minus_dxy_pp` is a transparent first version. |
| Why RBI, not Yahoo Finance? | Official source, documented methodology, and it's the rate used for settlement. Yahoo is an unofficial aggregator with unknown timestamps. |
| Is the percentile a p-value? | No. Overlapping windows are autocorrelated and volatility regimes change, so it only says how unusual the move was relative to recent history. |
| What would you add next? | FPI flow data (NSDL), daily or weekly intervention proxies (RBI weekly reserves), a market-model benchmark, and placebo dates (random non-event dates run through the same windows). |
| How do you keep it reproducible? | Raw files are untouched, and one command (`python run_pipeline.py`) rebuilds everything. All paths and parameters live in `03_Notebooks/config.py`, and every data decision is logged in `dq_issues`. |
