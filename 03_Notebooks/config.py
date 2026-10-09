"""Shared paths and analysis constants.

Every analytical choice that an interviewer might ask about lives here,
so it can be read (and changed) in one place.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "01_Data"
RAW = DATA / "1_Raw"                    # untouched source files
REF = DATA / "2_Reference"              # hand-curated inputs (events, repo history, catalogue)
PROC = DATA / "3_Intermediate"          # working files written by each pipeline step
PBI = DATA / "4_PowerBI_Tables"         # one CSV per database table, read by Power BI
DB_PATH = ROOT / "02_Database" / "geo_inr_analytics.db"
DOCS = ROOT / "05_Documentation"

# Raw file names (01_Data/1_Raw/...)
RAW_RBI_REFERENCE = RAW / "RBI" / "RBI_USDINR_Reference_Rate_Daily.txt"
RAW_RBI_INTERBANK = RAW / "RBI" / "RBI_USDINR_Interbank_Rates_Daily.txt"
RAW_RBI_CPI = RAW / "RBI" / "RBI_CPI_Rural_Urban_Combined_Statewise.txt"
RAW_RBI_INTERVENTION = RAW / "RBI" / "RBI_FX_Intervention_Sale_Purchase_USD.xlsx"
RAW_FRED_DAILY = RAW / "FRED" / "FRED_Daily_Brent_DollarIndex_VIX_US10Y_FedFunds.zip"
RAW_FRED_MONTHLY = RAW / "FRED" / "FRED_Monthly_CPI_and_Reserves.csv"
RAW_FRED_USDINR = RAW / "FRED" / "FRED_USDINR_H10_Daily.csv"
RAW_LBMA_GOLD = RAW / "LBMA_Gold" / "LBMA_Gold_Price_AM.json"
RAW_NIFTY_DIR = RAW / "NSE_Nifty50"

# Reference file names (01_Data/2_Reference/...)
REF_EVENTS = "Event_List.csv"
REF_MILESTONES = "Event_Milestones.csv"
REF_REPO = "RBI_Repo_Rate_History.csv"
REF_CATALOG = "Series_Catalog.csv"

# Analysis period. Raw files go back further; we keep 2013+ so every event
# (first anchor Mar-2014) has >= 1 year of history for baselines.
ANALYSIS_START = "2013-01-01"
ANALYSIS_END = "2026-09-30"          # build date

# ---- Event windows (in TRADING days of the chosen calendar) ----------------
# Base point for every window is t(-1): the last close before the event
# information reached Indian markets.
#   pre windows : change from t(-k) to t(-1)   ("run-up")
#   event day   : change from t(-1) to t(0)
#   post windows: change from t(-1) to t(+k)   (cumulative, includes event day)
WINDOWS = [
    # id,        label,              start_off, end_off, type, sort
    ("PRE_30",  "30 days before",   -30, -1, "pre",   1),
    ("PRE_14",  "14 days before",   -14, -1, "pre",   2),
    ("PRE_7",   "7 days before",     -7, -1, "pre",   3),
    ("EVENT",   "Event day",         -1,  0, "event", 4),
    ("POST_7",  "7 days after",      -1,  7, "post",  5),
    ("POST_14", "14 days after",     -1, 14, "post",  6),
    ("POST_30", "30 days after",     -1, 30, "post",  7),
    ("POST_90", "90 days after",     -1, 90, "post",  8),
]
PATH_RANGE = (-30, 90)               # relative days kept for the event-path chart

# ---- Frequency alignment ---------------------------------------------------
# Non-Indian series are aligned to the Indian FX calendar with an AS-OF join:
# take the latest observation ON OR BEFORE the Indian date, but never older
# than MAX_STALENESS_DAYS calendar days. No back-filling (no look-ahead).
MAX_STALENESS_DAYS = 5

# ---- Rolling statistics ------------------------------------------------------
VOL_WINDOW = 20        # trading days, annualised with sqrt(252)
VOL_MIN_OBS = 15
CORR_WINDOW = 60       # trading days
CORR_MIN_OBS = 40
ANNUALISE = 252
MIN_OBS_WINDOW_CORR = 14   # no correlation reported inside windows shorter than this

# ---- Baseline ("how unusual was this move?") --------------------------------
BASELINE_LOOKBACK = 750    # ~3 years of trading days before t(-30)

# Series that are measured as LEVEL CHANGES (percentage points), not % returns
LEVEL_CHANGE_SERIES = {"UST10Y", "FFR_UPPER", "FFR_EFFECTIVE", "IN_REPO"}

# Market series carried in the aligned daily panel (order = column order)
PANEL_SERIES = ["BRENT", "GOLD_USD", "NIFTY50", "DXY_BROAD", "VIX", "UST10Y",
                "FFR_UPPER", "IN_REPO"]
CORR_PAIRS = ["BRENT", "GOLD_USD", "NIFTY50", "DXY_BROAD", "VIX", "UST10Y"]

FX_SOURCES = {"RBI": "USDINR_RBI", "FRED": "USDINR_FRED"}


# ---- Reference-file reader ---------------------------------------------------
# The hand-curated CSVs in 01_Data/2_Reference may be opened and re-saved in Excel,
# which rewrites ISO dates (2014-03-01) as locale dates (3/1/2014 or 1/3/2014).
# read_reference() accepts both and always returns ISO strings (YYYY-MM-DD).
REF_DATE_COLS = {
    REF_EVENTS: ["event_start_date", "event_end_date", "anchor_date", "source_pub_date"],
    REF_MILESTONES: ["milestone_date", "source_pub_date"],
    REF_REPO: ["effective_date"],
}


def _parse_date_column(s, name):
    import pandas as pd
    s = s.astype("string").str.strip()
    s = s.mask(s.isin(["", "nan", "NaN", "None"]))
    vals = s.dropna()
    if vals.empty:
        return s
    if vals.str.match(r"^\d{4}-\d{2}-\d{2}$").all():
        return pd.to_datetime(s, format="%Y-%m-%d").dt.strftime("%Y-%m-%d")
    parts = vals.str.extract(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$").astype(float)
    if parts.isna().any().any():
        raise ValueError(f"{name}: unrecognised date values {vals[parts.isna().any(axis=1)].tolist()[:3]}")
    dayfirst = bool((parts[0] > 12).any())
    monthfirst = bool((parts[1] > 12).any())
    if dayfirst and monthfirst:
        raise ValueError(f"{name}: mixed day/month order in dates")
    if not dayfirst and not monthfirst:
        print(f"WARNING {name}: day/month order ambiguous - assuming month/day (Excel en-US)")
    fmt = "%d/%m/%Y" if dayfirst else "%m/%d/%Y"
    norm = s.str.replace(r"[.-]", "/", regex=True)
    return pd.to_datetime(norm, format=fmt).dt.strftime("%Y-%m-%d")


def read_reference(filename):
    """Read a 01_Data/2_Reference CSV with dates normalised to ISO strings."""
    import pandas as pd
    df = pd.read_csv(REF / filename, dtype=str, encoding="utf-8-sig")
    for c in REF_DATE_COLS.get(filename, []):
        if c in df.columns:
            df[c] = _parse_date_column(df[c], f"{filename}:{c}")
    return df
