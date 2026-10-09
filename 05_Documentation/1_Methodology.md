# Methodology

Scope: how USD/INR and selected market variables behaved around 13 geopolitical events (2014–2026).
This is an **event-window (temporal association) study**. It does not identify causal effects.

All parameters referenced below are defined in one place: `03_Notebooks/config.py`.

---

## 1. Units and sign conventions

| Quantity | Formula | Read as |
|---|---|---|
| USD/INR level | INR per 1 USD | 95.8 = one dollar costs ₹95.8 |
| **USD/INR return** (% change) | `(P_end / P_start − 1) × 100` | **> 0 ⇒ rupee weakened** |
| **INR % change** (rupee's own value) | `(P_start / P_end − 1) × 100` | > 0 ⇒ rupee strengthened. Not simply −(USD/INR return) because the base differs: +5% USD/INR ≠ −5% INR (it is −4.76%) |
| Log return (daily) | `ln(P_t / P_{t−1})` | used for volatility and correlation (additive over time) |
| Rates and yields (US 10Y, Fed funds, repo) | `level_end − level_start` | percentage points (pp), never % of a yield |
| Brent, gold, Nifty, dollar index, VIX | `(V_end / V_start − 1) × 100` | % change |

## 2. Trading-day calendars

Two calendars exist, one per USD/INR source (`dim_fx_basis`):

* **RBI calendar** (primary): every date with an RBI/FBIL reference rate in DBIE's *Daily Exchange Rate* table, 25 Aug 1998 → **29 Sep 2026**. Holidays are simply absent (3 are listed explicitly as `-`).
* **FRED calendar** (cross-check): every date with a Fed H.10 USD/INR noon rate (US business days), to 25 Sep 2026. Used to test whether results survive a different source and clock.

A "trading day" offset means **one row of the chosen calendar**, never a calendar day. Weekends and holidays are skipped automatically because they are not rows.

## 3. Event dates and the anchor

Each event has three dates (`dim_event`):

* `event_start_date`: when it happened (from the cited source).
* `anchor_date`: when the information became **public to Indian markets**. It usually equals the start date. Exceptions are documented per event: Doklam used the first official MEA statement, Pulwama happened after the market close, and Galwan used the Army statement the next day.
* `event_end_date`: a documented de-escalation or end point where one exists, otherwise NULL. It is used on the timeline only; windows are always measured from the anchor.

Then, per calendar:

* **t(0)** = the first trading day **on or after** the anchor date (`searchsorted`). Example: E12 was Saturday 28 Feb 2026, so t(0) = Monday 2 Mar 2026.
* **t(−1)** = the trading day before t(0): the last close **before** the information arrived. It is the base of every window.

## 4. Event windows

| Window | From | To | Meaning |
|---|---|---|---|
| PRE_30 / PRE_14 / PRE_7 | t(−30/−14/−7) | t(−1) | run-up before the event |
| EVENT | t(−1) | t(0) | event-day reaction |
| POST_7 / 14 / 30 / 90 | t(−1) | t(+7/+14/+30/+90) | cumulative move **including** the event day |

* `status = complete`: both endpoints exist in the calendar.
* `status = partial`: the calendar ends before t(+k). The change is measured to the last available day and labelled. Example: E13 (8 Jul 2026) +90 on both bases.
* `status = not_covered`: the event lies outside the calendar (none in this build).

For every window and series, `fact_event_window` stores the start and end values, the change, the log change, the realised volatility inside the window, and the staleness of each endpoint (§6).

**Event path** (`fact_event_path`): each series is indexed to **100 at t(−1)** for relative days −30…+90, so events at different price levels can be overlaid on one chart.

## 5. Missing dates

1. Blank, `.` or `-` values in a raw file are treated as **no observation**, never as zero (`03_Notebooks/01_Ingest_Raw_Data.ipynb`). The one documented exception is RBI Bulletin Table 4 (intervention), where RBI's own convention is that `-` means **nil**, so it is loaded as 0.
2. Duplicate dates keep the first occurrence and are logged. None were found in this build.
3. Missing days are **not interpolated**. A price series is never filled with a straight line between points.
4. Holidays are simply absent from the calendar, so a return always runs from one real observation to the next. `days_since_prev_obs` in the fact tables shows the gap: a Monday return after a Friday carries 3 days of news.
5. Every exception goes to `dq_issues`. Examples: 11 carried-forward copies in RBI's interbank table (mostly 1 April, excluded); 29 conflicts between the two RBI tables (flagged, primary kept); the missing US CPI for Oct 2025; the CPI base-year breaks; and Nifty rows repeated across yearly download files (de-duplicated).

## 6. Aligning different frequencies and time zones

The analysis is on the **Indian FX calendar**. Other series are brought onto it with an **as-of join** (`pd.merge_asof`, `direction='backward'`):

* On each Indian trading date, take the latest observation **on or before** that date.
* **Maximum staleness: 5 calendar days.** Older values become NULL rather than being carried indefinitely.
* **Never backward-fill.** A later value is never used for an earlier date, so there is no look-ahead.
* The staleness of each window endpoint is stored (`start_staleness_days`, `end_staleness_days`), and `dq_alignment` reports, per series, the share of days that are exact matches, carried forward, or missing. On the RBI calendar, 97.6% of Brent values are exact same-day matches.

**Step series** (RBI repo, Fed funds target) are carried forward **without** a cap, because a policy rate stays in force until changed.

**Monthly series** (CPI, reserves, RBI intervention) are **not** interpolated to daily. They live in `fact_macro` at monthly grain and are shown as monthly context. US CPI YoY is computed on a complete monthly grid, so a missing month cannot silently shift the 12-month lag. India CPI uses MoSPI's **published** YoY, because its base year changes (2012 → 2024 = 100 in Jan 2026) and index levels are not comparable across the break. RBI intervention is attached to event windows by summing the **calendar months each window touches**, so it is coarser than the windows themselves.

**Timestamp caveat.** "Same date" is not "same moment". The RBI fix is about 13:30 IST, the LBMA gold AM price is 10:30 London (about 15:00–16:00 IST), and Brent spot, VIX and the H.10 noon rate are observed hours after the Indian fix. So on a given date, foreign series can contain information that Indian markets only price on the next day. Consequences:

* Daily correlations understate the true relationship. RBI vs FRED daily returns correlate **0.56**; weekly returns correlate **0.89** (`dq_summary`).
* The EVENT-day change of a foreign series can include news from after the Indian fix.

That is why multi-day windows matter more than single days, and why weekly correlation is reported as a robustness check.

## 7. Volatility and correlation

* **Rolling volatility:** 20-trading-day standard deviation of daily log returns × √252 × 100 (annualised %). At least 15 observations are required.
* **Rolling correlation:** 60-trading-day Pearson correlation between USD/INR daily log returns and each other series' daily log returns (first differences for the US 10Y yield). At least 40 observations are required.
* **In-window correlation:** computed only when a window has ≥ 14 daily return pairs, so it is never shown for PRE_7, EVENT or POST_7. With n ≈ 30, a correlation of ±0.36 is roughly the 5% noise band, so most in-window correlations are indistinguishable from zero.
* **Baseline percentile:** for USD/INR, Brent, gold, Nifty and the broad dollar index, the event-window log change is compared with **all same-length changes in the ~750 trading days before the window starts**. Percentile = share of those historical changes that were smaller. This is a *descriptive* "how unusual" measure, **not a significance test**: overlapping windows are autocorrelated and volatility regimes change.
* **USD/INR − broad USD (pp):** USD/INR window change minus the broad dollar index's change over the same window. It separates "the dollar rose against everyone" from "the rupee moved on its own". It is a simple difference with no fitted beta.

## 8. Association vs causation: the language rules

| We can say | We cannot say |
|---|---|
| "USD/INR rose 0.85% on the day Russia invaded Ukraine (RBI reference rate, 23→24 Feb 2022)." | "The invasion caused the rupee to fall." |
| "In the 30 trading days after E12, USD/INR rose 3.17% while Brent rose 59.1%, and RBI was a net seller of US$11.3 bn over Feb–Apr 2026." | "Oil drove the rupee down by X." |
| "The move was larger than every same-length move in the prior three years (100th percentile)." | "The move was statistically significant because of the war." |
| "The daily-return correlation with Brent in that window was +0.20 (n = 31), inside the ±0.36 noise band." | "Brent explains the rupee." |

Why causation cannot be claimed:

1. **Confounding.** Other drivers move at the same time and are not held constant: monetary policy (RBI repo and FOMC changes are listed per window in `fact_event_window_context`), oil prices (partly driven by the events, partly not, such as OPEC's decision of 28 Sep 2016), global risk sentiment (VIX), US-dollar strength (broad dollar index), domestic conditions (elections, GST, demonetisation, COVID-19), and trade and capital flows (FPI flows and tariffs are not in this dataset; RBI intervention is included at monthly frequency).
2. **RBI intervention.** The RBI actively smooths INR volatility. An absent move may mean intervention, not absent pressure. In E07's first 30 days (Feb–Apr 2022), RBI was a net **seller of US$17.4 bn**.
3. **Anticipation and leakage.** Tensions build before a dated event (Uri before the surgical strikes, weeks of Iran tension before 28 Feb 2026), so part of any reaction sits in the PRE windows.
4. **Overlapping events.** E10 +90 contains E11, and E12 +90 contains E13 (`n_overlapping`).
5. **Small sample.** 13 events: no counterfactual, no control group, and correlations are not causal channels.
6. **Selection.** Events were chosen by the criteria in `05_Documentation/3_Event_Definitions.md`, not by their market impact. Still, any hand-picked list is a sample and results do not generalise.

## 9. Known limitations of this build

* India CPI has base-year breaks (2010/2012/2024 = 100). Only published YoY is comparable across them.
* RBI intervention is monthly and by value date, so it cannot be attributed to specific days within a window. Jul–Aug 2026 were not yet published at build time.
* The repo-rate history is hand-compiled from RBI policy statements. Verify it against the DBIE *Policy Rates* table.
* FX reserves are monthly (IMF IFS via FRED); RBI's weekly series would be more granular.
* No FPI-flow or trade-balance data are included. These are the main remaining omitted channels.
