# Power BI build guide: 7 pages

**The report is already built:** open `04_PowerBI/GeoINR_Dashboard/GeoINR.pbip` in Power BI Desktop and click **Refresh**. It contains the model (19 tables, 22 relationships, 74 measures) and all 7 pages. `generate_powerbi_project.py` produced it, so re-run that script after changing pages or measures.

* Data comes from the CSVs in `01_Data/4_PowerBI_Tables/` through the `DataFolder` parameter. If the project folder moves, update it under Transform data → Edit parameters.
* Measures are in `DAX_Measures.dax` (a readable copy) and the theme is `Report_Theme.json`.
* The report uses Power BI's project format (PBIP). Older Desktop versions may need **File → Options → Preview features → Power BI Project (.pbip) save option** switched on.

The rest of this guide documents what the report contains, and doubles as step-by-step instructions for rebuilding it by hand.

---

## 1. Load the data

Get Data → **Text/CSV** once per table from `01_Data\4_PowerBI_Tables\` (or connect the SQLite ODBC driver to `02_Database\geo_inr_analytics.db`). Tables to load:

| Group | Tables |
|---|---|
| Dimensions | `dim_date`, `dim_event`, `dim_event_milestone`, `dim_window`, `dim_fx_basis`, `dim_series`, `dim_analysis_series` |
| Facts | `fact_daily_aligned`, `fact_fx`, `fact_commodity`, `fact_market`, `fact_macro`, `fact_event_anchor`, `fact_event_window`, `fact_event_window_corr`, `fact_event_path`, `fact_event_window_context` |
| Data quality | `dq_issues`, `dq_series_coverage`, `dq_alignment`, `dq_fx_crosscheck`, `dq_summary` |

**Power Query type fixes:** `dim_date[date]` → Date. All `*_date` text columns in event tables → Date. `date_key` → Whole number. `change`, `corr`, `value` → Decimal. Replace empty strings with null in `event_end_date`.

In `dim_date`, set **Mark as date table** on `dim_date[date]`.
Sort `dim_window[window_label]` by `dim_window[sort_order]`, and `dim_analysis_series[display_name]` by `sort_order`.

## 2. Relationships (star schema, all single-direction, 1 → *)

```
dim_date[date_key]            → fact_daily_aligned, fact_fx, fact_commodity, fact_market,
                                fact_macro, dq_fx_crosscheck, dim_event_milestone
dim_fx_basis[basis]           → fact_daily_aligned, fact_event_anchor, fact_event_window,
                                fact_event_window_corr, fact_event_path, fact_event_window_context
dim_event[event_id]           → fact_event_anchor, fact_event_window, fact_event_window_corr,
                                fact_event_path, fact_event_window_context, dim_event_milestone
dim_window[window_id]         → fact_event_window, fact_event_window_corr, fact_event_window_context
dim_analysis_series[series_id]→ fact_event_window, fact_event_window_corr, fact_event_path
dim_series[series_id]         → fact_fx, fact_commodity, fact_market, fact_macro
```

Do **not** relate `fact_event_anchor[t0_date_key]` to `dim_date`. The `Event Marker` measure matches dates itself, and an active link would filter the anchors by the date axis.

**Global slicer (sync across all pages):** `dim_fx_basis[basis]`, single select, default **RBI**. Put the `Basis Caption` measure in a card next to it.

On every page, place a small card with the **`Causality Caption`** measure at the bottom.

---

## Page 1: INR/USD Overview

Purpose: the currency's history before any event is layered on.

| Visual | Fields | Notes |
|---|---|---|
| KPI cards ×5 | `USDINR Latest`, `USDINR % Change (period)`, `INR % Change (period)`, `USDINR Vol 20d (ann. %)`, `Rate Differential IN-US (pp)` | Format % measures as percent |
| Line chart | X: `dim_date[date]`; Y: `USDINR Rate` | Title "USD/INR (up = rupee weaker)" |
| Line chart (secondary) | X: date; Y: `USDINR Vol 20d (ann. %)` | Shows calm vs turbulent regimes |
| Line chart | X: `dim_date[year_month]`; Y: `fact_macro[value]` filtered to `IN_REPO`, `FFR_UPPER`, `RATE_DIFF_IN_US` | Policy-rate context |
| Line chart | X: `dim_date[year_month]`; Y: `India CPI YoY %`, `US CPI YoY %` | Tooltip `fact_macro[series_version]`; add a text note "CPI base 2024=100 from Jan-2026" |
| Column chart | X: `dim_date[year_month]`; Y: `RBI Net FX (USD bn, monthly)` | Diverging colours (bought = blue, sold = orange). Shows when RBI leaned against the rupee |
| Slicer | `dim_date[date]` (between) | Default 2013 onward |

## Page 2: Event Timeline

Purpose: where the 13 events sit on the currency's path, with their start/end and milestones.

| Visual | Fields | Notes |
|---|---|---|
| Line chart | X: `dim_date[date]`; Y: `USDINR Rate` **and** `Event Marker (USDINR)` | For `Event Marker`: line width 0, markers on, size 8. Tooltip: `Event Name on Date` |
| Table | `dim_event[event_id]`, `event_name`, `event_type`, `affected_region`, `india_direct`, `event_start_date`, `event_end_date`, `anchor_date`, `fact_event_anchor[t0_date]` | Conditional icon on `india_direct` |
| Table (drill-through target) | `dim_event_milestone[milestone_date]`, `milestone`, `source_org`, `source_type`, `source_url` (Web URL) | Filtered by the selected event |
| Card / multi-row card | `dim_event[source_title]`, `source_pub_date`, `selection_rationale`, `known_concurrent_factors` | For the selected event |

Optional: a Gantt-style bar with `dim_event[event_start_date]` to `event_end_date` using the free "Gantt" visual from AppSource.

## Page 3: Event Window Analysis

Purpose: the core of the project. What USD/INR did in each of the 8 windows, for each event.

| Visual | Fields | Notes |
|---|---|---|
| Slicers | `dim_event[event_label]` (multi), `dim_window[window_label]` | |
| **Matrix (heatmap)** | Rows: `dim_event[event_label]`; Columns: `dim_window[window_label]`; Values: `USDINR Window Change %` | Diverging background colour centred at 0; add a `Window Status` tooltip; partial windows in italics via conditional formatting on `Window Status` = "partial" |
| Line chart (event path) | X: `fact_event_path[rel_day]`; Y: `Path Index (t-1 = 100)`; Legend: `dim_event[event_id]`; filter `dim_analysis_series[series_id]` = USDINR | Constant X line at 0; constant Y line at 100 |
| Clustered bar | Axis: `dim_event[event_id]`; Values: `USDINR Window Change %`, `USDINR minus Broad USD (pp)` | Answers "the rupee, or the dollar against everyone?" |
| Cards | `Median Window Change (across events)`, `Share of Events INR Weaker`, `Events Measured` | Respond to the window slicer |
| Table | `dim_event[event_id]`, `Window Start Date`, `Window End Date`, `Baseline Percentile`, `Baseline Z`, `Policy Changes in Window`, `RBI Net FX in Window (USD bn)`, `fact_event_window_context[rbi_fx_months]`, `Overlapping Events` | Context for every number. Intervention is summed over calendar months, so label it that way |

Text box: *"Pre = t(−k)→t(−1). Event day = t(−1)→t(0). Post = t(−1)→t(+k). Trading days on the selected FX calendar. Percentile compares the move with all same-length moves in the prior ~3 years (descriptive, not a significance test)."*

## Page 4: INR vs Crude Oil

| Visual | Fields | Notes |
|---|---|---|
| Line chart, two axes | X: `dim_date[date]`; Y1: `USDINR Rate`; Y2: `Brent (USD/bbl)` | Different scales, so label both axes |
| **Scatter (events)** | Details: `dim_event[event_id]`; X: `Brent Window Change %`; Y: `USDINR Window Change %`; window slicer (default POST_30) | Each dot is one event, not a regression; label the dots |
| Line chart | X: `dim_date[year]`; Y: `Corr USDINR~Brent (period)` | Calendar-year correlation of daily returns (n ≥ 40) |
| Line chart | X: `fact_event_path[rel_day]`; Y: `Path Index`; Legend: `dim_analysis_series[display_name]` filtered to USDINR + BRENT; event slicer single-select | Side-by-side path for one event |

Text: *"India imports most of its crude oil, so oil prices are a plausible channel, but they also respond to the same events and to supply decisions (e.g. OPEC, 28 Sep 2016)."*

## Page 5: INR vs Gold / Equity

| Visual | Fields |
|---|---|
| Scatter | X: `Gold Window Change %`; Y: `USDINR Window Change %`; Details: event |
| Scatter | X: `Nifty Window Change %`; Y: `USDINR Window Change %`  |
| Matrix | Rows: `dim_event[event_label]`; Columns: `dim_analysis_series[display_name]` (USDINR, BRENT, GOLD_USD, NIFTY50, DXY_BROAD, VIX); Values: `Window Change`; window slicer |
| Line chart | X: date; Y: `Gold (USD/oz)`, `Nifty 50` (indexed or separate axes) |

## Page 6: Volatility & Correlation

| Visual | Fields | Notes |
|---|---|---|
| Line chart | X: date; Y: `USDINR Vol 20d (ann. %)`, `Brent Vol 20d (ann. %)`, `Gold Vol 20d (ann. %)` | Constant lines at event t(0) dates are not dynamic; use the `Event Marker` measure on a secondary line instead |
| **Field parameter** `Corr Pair` | Modeling → New parameter → Fields → add `Rolling Corr 60d Brent`, `…Gold`, `…Broad USD`, `…VIX`, `…Nifty`, `…US10Y` | Slicer on the parameter |
| Line chart | X: date; Y: `Corr Pair` | Constant line at 0 |
| Matrix | Rows: event; Columns: `dim_analysis_series[display_name]`; Values: `Window Corr`; filter window = POST_30 / POST_90 | Add `Noise Band (±)` as a tooltip; grey out \|corr\| < noise band |
| Bar | Axis: event; Values: `Window Vol (ann. %)` for USD/INR, POST_30 | Compare with the baseline vol level on page 1 |
| Scatter | Details: event; X: `RBI Net FX in Window (USD bn)`; Y: `USDINR Window Change %`; window = POST_30 | "Low rupee volatility may reflect RBI selling dollars, not an absence of pressure" |

Text: *"Correlation of daily returns, 60-day rolling. Series are observed at different clock times (RBI ≈13:30 IST; Brent, VIX and US rates at the US close), which biases same-day correlation towards zero."*

## Page 7: Data Quality

| Visual | Fields |
|---|---|
| Cards | `DQ Issues`, `DQ Warnings`, `Mean Abs FRED-RBI Gap (%)`, `Days > 0.5% Gap`, `Series Ending Early` |
| Table | `dq_series_coverage` (all columns); conditional colour on `status` |
| Stacked bar (100%) | Axis: `dq_alignment[series_id]`; Values: `Pct Days Exact Match`, `Pct Days Carried Forward`, `Pct Days Missing`; basis slicer |
| Line chart | X: date; Y: `FRED minus RBI (%)` (from `dq_fx_crosscheck`) |
| Table | `dq_issues` (stage, series_id, obs_date, rule, detail, severity, action); slicer on severity |
| Table | `dq_summary` (metric, value, explanation) |
| Table | `dq_issues` filtered to `rule` in (table_crosscheck, table_conflict, carried_forward_copies, series_break) | The two-RBI-table reconciliation and the CPI base change |

---

## Formatting conventions

* Percent measures (`… %`) are already divided by 100, so format them as Percentage with 2 decimals.
* `(pp)` measures are percentage points: format as a decimal with the suffix " pp".
* Colours (from the theme): USD/INR navy, Brent amber, gold ochre, Nifty teal, broad USD grey. A diverging heatmap is blue (INR stronger) to orange (INR weaker). Avoid red/green "good/bad" colouring for currency moves.
* Every chart title states the unit and sign, for example "USD/INR % change (↑ = rupee weaker)".
