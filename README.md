# Geopolitical Events, INR/USD & Indian Market Analytics System

An **event-window analytics** project: how USD/INR and selected market variables (Brent, gold, Nifty 50, the broad US dollar, VIX, US yields and policy rates) behaved around 13 major geopolitical events from 2014 to 2026.

> **This project measures temporal association, not causation.** It shows what moved around each event date and what else was happening at the time. It does not claim that any event caused a currency move.

**Primary question:** *How did USD/INR behave around selected geopolitical events, and what other market variables moved alongside it?*

---

## What to open

| I want to… | Open |
|---|---|
| See the dashboard | `04_PowerBI/GeoINR_Dashboard/GeoINR.pbip` (Power BI Desktop) |
| Walk through the analysis step by step | `03_Notebooks/` (open in Jupyter or VS Code, 01 → 06) |
| See the charts | `03_Notebooks/06_Analysis_and_Charts.ipynb` or `05_Documentation/Figures/` |
| Read the results | `05_Documentation/4_Event_Results.md` |
| Understand the method | `05_Documentation/1_Methodology.md` |
| Check where data came from | `05_Documentation/2_Data_Sources.md` |
| See how events were chosen | `05_Documentation/3_Event_Definitions.md` |
| Prepare for an interview | `06_Interview_Prep/Interview_Guide.md` |
| Query the data in SQL | `02_Database/geo_inr_analytics.db` (SQLite) |

## Folder structure

```
Geopolitical Events & INRUSD/
│
├── README.md                       ← you are here
├── run_pipeline.py                 ← runs all six notebooks in order (rebuilds everything)
│
├── 01_Data/
│   ├── 1_Raw/                      untouched source downloads
│   │   ├── RBI/                    reference rate, interbank rates, CPI, FX intervention
│   │   ├── FRED/                   Brent, dollar index, VIX, US 10Y, Fed funds, US CPI, reserves
│   │   ├── LBMA_Gold/              LBMA gold price (AM)
│   │   ├── NSE_Nifty50/            yearly NIFTY 50 history files
│   │   └── _Archive/               original downloads and a superseded file (not used)
│   ├── 2_Reference/                hand-built inputs
│   │   ├── Event_List.csv          13 events: dates, sources, rationale, concurrent factors
│   │   ├── Event_Milestones.csv    key dates inside each event
│   │   ├── RBI_Repo_Rate_History.csv
│   │   └── Series_Catalog.csv      metadata for every data series
│   ├── 3_Intermediate/             working files written by the pipeline
│   └── 4_PowerBI_Tables/           one CSV per table, read by Power BI
│
├── 02_Database/
│   ├── geo_inr_analytics.db        SQLite star schema (22 tables + 2 views)
│   └── schema.sql
│
├── 03_Notebooks/                   run in order (01 → 06), or all at once with run_pipeline.py
│   ├── config.py                           every path and analysis setting in one place
│   ├── 01_Ingest_Raw_Data.ipynb            read raw files, log every data issue
│   ├── 02_Align_and_Transform.ipynb        trading calendars, alignment, returns, volatility
│   ├── 03_Compute_Event_Windows.ipynb      event windows, baselines, correlation, context
│   ├── 04_Build_Database.ipynb             SQLite + Power BI CSV export + data-quality tables
│   ├── 05_Write_Results_Report.ipynb       writes 05_Documentation/4_Event_Results.md
│   └── 06_Analysis_and_Charts.ipynb        9 charts with a reading of each (saved to Figures/)
│
├── 04_PowerBI/
│   ├── GeoINR_Dashboard/           Power BI project → open GeoINR.pbip
│   ├── PowerBI_Build_Guide.md      what each of the 7 pages shows
│   ├── DAX_Measures.dax            all 74 measures, readable copy
│   ├── Report_Theme.json
│   └── generate_powerbi_project.py rebuilds GeoINR_Dashboard
│
├── 05_Documentation/
│   ├── 1_Methodology.md
│   ├── 2_Data_Sources.md
│   ├── 3_Event_Definitions.md
│   ├── 4_Event_Results.md          auto-generated
│   └── Figures/                    the 9 charts from notebook 06 (PNG)
│
└── 06_Interview_Prep/
    └── Interview_Guide.md
```

## How to rebuild

**In Jupyter / VS Code:** open `03_Notebooks/` and run notebooks 01 → 06 in order (Run All in each). Each one reads the previous one's outputs.

**Or in one command:**

```bash
python run_pipeline.py                          # runs the six notebooks and saves them with outputs
python 04_PowerBI/generate_powerbi_project.py   # only if you change pages or measures
```

Needs Python 3.10+ with `pandas`, `numpy`, `openpyxl`, `matplotlib`, and for the one-command run `nbclient` + `ipykernel` (all in Anaconda; otherwise `pip install pandas numpy openpyxl matplotlib jupyter`). No internet access is needed, because everything runs from the files in `01_Data/1_Raw/`.
Then open the dashboard and click **Refresh**. If the project folder has moved, change the `DataFolder` parameter first (Transform data → Edit parameters).

## Status (build of 30 Sep 2026)

| Item | Status |
|---|---|
| USD/INR (RBI/FBIL reference rate) | ✅ Aug 1998 → 29 Sep 2026 (DBIE *Daily Exchange Rate of the Indian Rupee*; cross-checked against the DBIE interbank table) |
| USD/INR (Fed H.10 cross-check) | ✅ to 25 Sep 2026 |
| Brent, gold, broad USD, VIX, US 10Y, Fed funds, RBI repo | ✅ |
| US CPI, India reserves | ✅ monthly |
| India CPI (MoSPI, via DBIE) | ✅ to Aug 2026. Base-year break Jan 2026 (2012 → 2024 = 100); published YoY used |
| RBI FX intervention (net USD purchase/sale) | ✅ monthly to Jul 2026 (RBI Bulletin Table 4) |
| Nifty 50 | ✅ 2013 → 29 Sep 2026 (14 yearly niftyindices.com CSVs) |

## Database (star schema)

| Type | Tables |
|---|---|
| Dimensions | `dim_date`, `dim_event`, `dim_event_milestone`, `dim_window`, `dim_series`, `dim_analysis_series`, `dim_fx_basis` |
| Native-frequency facts | `fact_fx`, `fact_commodity`, `fact_market`, `fact_macro` |
| Analysis facts | `fact_daily_aligned` (all series on the Indian FX calendar, with returns, 20-day vol and 60-day correlation), `fact_event_anchor`, `fact_event_window`, `fact_event_window_corr`, `fact_event_path`, `fact_event_window_context` |
| Data quality | `dq_issues`, `dq_series_coverage`, `dq_alignment`, `dq_fx_crosscheck`, `dq_summary` |
| Views | `v_event_usdinr_summary`, `v_event_cross_asset` |

Example query:

```sql
SELECT event_label, window_label, ROUND(usdinr_pct_change, 2) AS usdinr_pct,
       ROUND(percentile) AS pctile_vs_prior_3y, rbi_repo_changes, overlapping_events
FROM v_event_usdinr_summary
WHERE basis = 'RBI' AND window_id = 'POST_30'
ORDER BY event_id;
```

## Key design decisions (details in `05_Documentation/1_Methodology.md`)

* **USD/INR source:** RBI/FBIL reference rate from RBI DBIE. The Fed H.10 rate is a separate cross-check basis and is never spliced into it.
* **Event dates:** a start date from an official or wire source, plus an **anchor date** (when the news became public to Indian markets). t(0) = first trading day on or after the anchor; t(−1) = the base.
* **Windows:** −30/−14/−7 → t(−1); event day t(−1)→t(0); t(−1) → +7/+14/+30/+90, all in trading days.
* **Missing data:** never zero-filled or interpolated; every gap is logged.
* **Alignment:** as-of join onto the Indian calendar (≤ 5 days stale, no look-ahead). Monthly data stays monthly.
* **Guard rails:** each window lists RBI and FOMC policy changes and overlapping events; "USD/INR − broad USD" separates rupee-specific moves from dollar moves; percentiles are descriptive only.
