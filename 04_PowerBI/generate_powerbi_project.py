"""Generate the Power BI project (PBIP) for this analysis.

    python 04_PowerBI/generate_powerbi_project.py

Output: 04_PowerBI/GeoINR_Dashboard/
    GeoINR.pbip                     <- double-click to open in Power BI Desktop
    GeoINR.SemanticModel/           <- TMDL model: tables (CSV import), relationships, DAX measures
    GeoINR.Report/                  <- PBIR report: 7 pages, one JSON file per visual

The model reads the CSVs in 01_Data/4_PowerBI_Tables through the parameter `DataFolder`
(Power BI Desktop: Transform data > Edit parameters) - change it if the project moves.
Re-run this script after changing measures/pages; re-run run_pipeline.py to refresh data.
"""
import json
import shutil
import uuid
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "01_Data" / "4_PowerBI_Tables"
PBI_DIR = ROOT / "04_PowerBI"
OUT = PBI_DIR / "GeoINR_Dashboard"
NAME = "GeoINR"
DEFAULT_DATA_FOLDER = r"E:\DA PROJECTS\Geopolitical Events & INRUSD\01_Data\4_PowerBI_Tables"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
NS = uuid.UUID("6f0e7c1a-3f7e-4d7b-9d7e-1b2c3d4e5f60")          # stable GUIDs across rebuilds


def gid(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))


# =============================================================================
# 1. SEMANTIC MODEL
# =============================================================================
TABLES = [
    "dim_date", "dim_event", "dim_event_milestone", "dim_window", "dim_fx_basis", "dim_series",
    "dim_analysis_series", "fact_daily_aligned", "fact_macro", "fact_event_anchor", "fact_event_window",
    "fact_event_window_corr", "fact_event_path", "fact_event_window_context",
    "dq_issues", "dq_series_coverage", "dq_alignment", "dq_fx_crosscheck", "dq_summary",
]
DATE_COLS = {"date", "event_start_date", "event_end_date", "anchor_date", "source_pub_date", "milestone_date",
             "t0_date", "t_minus1_date", "last_available_date", "start_date", "end_date", "obs_date",
             "first_date", "last_date", "period_start"}
TEXT_OVERRIDE = {("fact_event_anchor", "note")}
KEY_COLS = {"date_key", "t0_date_key", "issue_id", "sort_order", "month_num", "year", "rel_day",
            "start_offset", "end_offset", "is_weekend", "is_rbi_fx_day", "is_us_h10_day",
            "rbi_listed_holiday", "is_primary", "covered", "large_gap_flag", "trading_day_seq"}
SORT_BY = {("dim_window", "window_label"): "sort_order", ("dim_analysis_series", "display_name"): "sort_order",
           ("dim_date", "month_name"): "month_num"}
HIDDEN_TABLES = set()

RELATIONSHIPS = [  # (from table, from col, to table, to col, active)
    ("fact_daily_aligned", "date_key", "dim_date", "date_key", True),
    ("fact_daily_aligned", "basis", "dim_fx_basis", "basis", True),
    ("fact_macro", "date_key", "dim_date", "date_key", True),
    ("fact_macro", "series_id", "dim_series", "series_id", True),
    ("dq_fx_crosscheck", "date_key", "dim_date", "date_key", True),
    ("dim_event_milestone", "event_id", "dim_event", "event_id", True),
    ("fact_event_anchor", "event_id", "dim_event", "event_id", True),
    ("fact_event_anchor", "basis", "dim_fx_basis", "basis", True),
    ("fact_event_window", "event_id", "dim_event", "event_id", True),
    ("fact_event_window", "window_id", "dim_window", "window_id", True),
    ("fact_event_window", "series_id", "dim_analysis_series", "series_id", True),
    ("fact_event_window", "basis", "dim_fx_basis", "basis", True),
    ("fact_event_window_corr", "event_id", "dim_event", "event_id", True),
    ("fact_event_window_corr", "window_id", "dim_window", "window_id", True),
    ("fact_event_window_corr", "series_id", "dim_analysis_series", "series_id", True),
    ("fact_event_window_corr", "basis", "dim_fx_basis", "basis", True),
    ("fact_event_path", "event_id", "dim_event", "event_id", True),
    ("fact_event_path", "series_id", "dim_analysis_series", "series_id", True),
    ("fact_event_path", "basis", "dim_fx_basis", "basis", True),
    ("fact_event_window_context", "event_id", "dim_event", "event_id", True),
    ("fact_event_window_context", "window_id", "dim_window", "window_id", True),
    ("fact_event_window_context", "basis", "dim_fx_basis", "basis", True),
]

# ---- DAX measures: (name, expression, formatString, folder) --------------------------------
PCT, NUM2, NUM4, INT, TXT = "0.00%", "0.00", "0.0000", "0", None
ONE_WINDOW = "HASONEVALUE ( dim_window[window_id] )"


def corr_period(col):
    return f"""VAR _t =
    FILTER ( fact_daily_aligned,
        NOT ISBLANK ( fact_daily_aligned[usdinr_logret] ) && NOT ISBLANK ( fact_daily_aligned[{col}] ) )
VAR _n = COUNTROWS ( _t )
VAR _mx = AVERAGEX ( _t, fact_daily_aligned[usdinr_logret] )
VAR _my = AVERAGEX ( _t, fact_daily_aligned[{col}] )
VAR _cov = SUMX ( _t, ( fact_daily_aligned[usdinr_logret] - _mx ) * ( fact_daily_aligned[{col}] - _my ) )
VAR _sx = SQRT ( SUMX ( _t, ( fact_daily_aligned[usdinr_logret] - _mx ) ^ 2 ) )
VAR _sy = SQRT ( SUMX ( _t, ( fact_daily_aligned[{col}] - _my ) ^ 2 ) )
RETURN IF ( _n >= 40, DIVIDE ( _cov, _sx * _sy ) )"""


def window_series(sid, scale="/ 100"):
    return f"""IF ( {ONE_WINDOW},
    CALCULATE ( AVERAGE ( fact_event_window[change] ),
        dim_analysis_series[series_id] = "{sid}",
        fact_event_window[status] IN {{ "complete", "partial" }} ) {scale} )"""


def path_series(sid):
    return f'CALCULATE ( AVERAGE ( fact_event_path[indexed_value] ), dim_analysis_series[series_id] = "{sid}" )'


MEASURES = [
    # --- overview
    ("USDINR Rate", "AVERAGE ( fact_daily_aligned[usdinr] )", NUM4, "1 Overview"),
    ("USDINR Latest", """VAR _last = CALCULATE ( MAX ( fact_daily_aligned[date_key] ), NOT ISBLANK ( fact_daily_aligned[usdinr] ) )
RETURN CALCULATE ( [USDINR Rate], fact_daily_aligned[date_key] = _last )""", NUM2, "1 Overview"),
    ("USDINR First", """VAR _first = CALCULATE ( MIN ( fact_daily_aligned[date_key] ), NOT ISBLANK ( fact_daily_aligned[usdinr] ) )
RETURN CALCULATE ( [USDINR Rate], fact_daily_aligned[date_key] = _first )""", NUM2, "1 Overview"),
    ("USDINR % Change (period)", "DIVIDE ( [USDINR Latest], [USDINR First] ) - 1", PCT, "1 Overview"),
    ("INR % Change (period)", "DIVIDE ( [USDINR First], [USDINR Latest] ) - 1", PCT, "1 Overview"),
    ("USDINR Vol 20d (ann. %)", "AVERAGE ( fact_daily_aligned[usdinr_vol20] ) / 100", PCT, "1 Overview"),
    ("Repo Rate (latest)", """VAR _last = MAX ( fact_daily_aligned[date_key] )
RETURN CALCULATE ( AVERAGE ( fact_daily_aligned[in_repo] ), fact_daily_aligned[date_key] = _last )""", NUM2, "1 Overview"),
    ("Fed Funds Upper (latest)", """VAR _last = MAX ( fact_daily_aligned[date_key] )
RETURN CALCULATE ( AVERAGE ( fact_daily_aligned[ffr_upper] ), fact_daily_aligned[date_key] = _last )""", NUM2, "1 Overview"),
    ("Rate Differential IN-US (pp)", "[Repo Rate (latest)] - [Fed Funds Upper (latest)]", NUM2, "1 Overview"),
    ("India CPI YoY %", 'CALCULATE ( AVERAGE ( fact_macro[yoy_pct] ), dim_series[series_id] = "IN_CPI_MOSPI" ) / 100', PCT, "1 Overview"),
    ("US CPI YoY %", 'CALCULATE ( AVERAGE ( fact_macro[yoy_pct] ), dim_series[series_id] = "US_CPI" ) / 100', PCT, "1 Overview"),
    ("RBI Repo Rate %", 'CALCULATE ( AVERAGE ( fact_macro[value] ), dim_series[series_id] = "IN_REPO" ) / 100', PCT, "1 Overview"),
    ("Fed Funds Upper %", 'CALCULATE ( AVERAGE ( fact_macro[value] ), dim_series[series_id] = "FFR_UPPER" ) / 100', PCT, "1 Overview"),
    ("RBI Net FX (USD bn, monthly)", 'CALCULATE ( SUM ( fact_macro[value] ), dim_series[series_id] = "IN_RBI_FX_NET" ) / 1000', "0.0", "1 Overview"),
    # --- timeline
    ("Event Marker (USDINR)", """VAR _d = SELECTEDVALUE ( dim_date[date_key] )
VAR _isEvent =
    CALCULATE ( COUNTROWS ( fact_event_anchor ), fact_event_anchor[t0_date_key] = _d, fact_event_anchor[covered] = 1 )
RETURN IF ( _isEvent > 0, [USDINR Rate] )""", NUM2, "2 Timeline"),
    ("Event t0 Date", """VAR _b = SELECTEDVALUE ( dim_fx_basis[basis], "RBI" )
RETURN CALCULATE ( MIN ( fact_event_anchor[t0_date] ), fact_event_anchor[basis] = _b )""", "yyyy-mm-dd", "2 Timeline"),
    ("Event Name on Date", """VAR _d = SELECTEDVALUE ( dim_date[date_key] )
RETURN
    CONCATENATEX (
        FILTER ( fact_event_anchor, fact_event_anchor[t0_date_key] = _d ),
        RELATED ( dim_event[event_label] ), " | " )""", TXT, "2 Timeline"),
    ("Events in Selection", "DISTINCTCOUNT ( dim_event[event_id] )", INT, "2 Timeline"),
    # --- event windows
    ("Window Change", """CALCULATE ( AVERAGE ( fact_event_window[change] ),
    fact_event_window[status] IN { "complete", "partial" } )""", NUM2, "3 Event windows"),
    ("Window Change % (price series)", """IF ( SELECTEDVALUE ( dim_analysis_series[change_unit] ) = "%", [Window Change] / 100 )""", PCT, "3 Event windows"),
    ("USDINR Window Change % (matrix)", """CALCULATE ( AVERAGE ( fact_event_window[change] ),
    dim_analysis_series[series_id] = "USDINR",
    fact_event_window[status] IN { "complete", "partial" } ) / 100""", PCT, "3 Event windows"),
    ("USDINR Window Change %", window_series("USDINR"), PCT, "3 Event windows"),
    ("INR Window Change %", f"""IF ( {ONE_WINDOW},
    CALCULATE ( AVERAGE ( fact_event_window[inr_pct_change] ),
        dim_analysis_series[series_id] = "USDINR",
        fact_event_window[status] IN {{ "complete", "partial" }} ) / 100 )""", PCT, "3 Event windows"),
    ("USDINR minus Broad USD %", f"""IF ( {ONE_WINDOW},
    CALCULATE ( AVERAGE ( fact_event_window[usdinr_minus_dxy_pp] ),
        dim_analysis_series[series_id] = "USDINR",
        fact_event_window[status] IN {{ "complete", "partial" }} ) / 100 )""", PCT, "3 Event windows"),
    ("Median USDINR Window Change %", "MEDIANX ( VALUES ( dim_event[event_id] ), [USDINR Window Change %] )", PCT, "3 Event windows"),
    ("Events with INR Weaker", "COUNTROWS ( FILTER ( VALUES ( dim_event[event_id] ), [USDINR Window Change %] > 0 ) )", INT, "3 Event windows"),
    ("Events Measured", "COUNTROWS ( FILTER ( VALUES ( dim_event[event_id] ), NOT ISBLANK ( [USDINR Window Change %] ) ) )", INT, "3 Event windows"),
    ("Share of Events INR Weaker", "DIVIDE ( [Events with INR Weaker], [Events Measured] )", "0%", "3 Event windows"),
    ("USDINR Baseline Percentile", f"""IF ( {ONE_WINDOW},
    CALCULATE ( AVERAGE ( fact_event_window[percentile] ),
        dim_analysis_series[series_id] = "USDINR", fact_event_window[status] = "complete" ) )""", "0.0", "3 Event windows"),
    ("USDINR Baseline Z", f"""IF ( {ONE_WINDOW},
    CALCULATE ( AVERAGE ( fact_event_window[z_score] ),
        dim_analysis_series[series_id] = "USDINR", fact_event_window[status] = "complete" ) )""", NUM2, "3 Event windows"),
    ("Window Status", f"""IF ( {ONE_WINDOW},
    CALCULATE ( SELECTEDVALUE ( fact_event_window[status], "mixed" ), dim_analysis_series[series_id] = "USDINR" ) )""", TXT, "3 Event windows"),
    ("Window Start Date", f"""IF ( {ONE_WINDOW}, CALCULATE ( MIN ( fact_event_window[start_date] ), dim_analysis_series[series_id] = "USDINR" ) )""", "yyyy-mm-dd", "3 Event windows"),
    ("Window End Date", f"""IF ( {ONE_WINDOW}, CALCULATE ( MAX ( fact_event_window[end_date] ), dim_analysis_series[series_id] = "USDINR" ) )""", "yyyy-mm-dd", "3 Event windows"),
    ("Policy Changes in Window", f"""IF ( {ONE_WINDOW},
    VAR _t = SELECTCOLUMNS ( fact_event_window_context, "@txt",
        TRIM ( IF ( NOT ISBLANK ( fact_event_window_context[rbi_repo_changes] ), "RBI " & fact_event_window_context[rbi_repo_changes] )
            & IF ( NOT ISBLANK ( fact_event_window_context[fomc_target_changes] ), "  Fed " & fact_event_window_context[fomc_target_changes] ) ) )
    RETURN CONCATENATEX ( FILTER ( DISTINCT ( _t ), [@txt] <> "" ), [@txt], "; " ) )""", TXT, "3 Event windows"),
    ("Overlapping Events", f"""IF ( {ONE_WINDOW}, CONCATENATEX ( FILTER ( DISTINCT ( SELECTCOLUMNS ( fact_event_window_context, "@o", fact_event_window_context[overlapping_events] ) ), [@o] <> "" ), [@o], ", " ) )""", TXT, "3 Event windows"),
    ("RBI Net FX in Window (USD bn)", f"""IF ( {ONE_WINDOW}, DIVIDE ( SUM ( fact_event_window_context[rbi_net_fx_usd_mn] ), 1000 ) )""", "0.0", "3 Event windows"),
    ("USDINR Path (t-1 = 100)", path_series("USDINR"), NUM2, "3 Event windows"),
    # --- cross asset
    ("Brent Window Change %", window_series("BRENT"), PCT, "4-5 Cross-asset"),
    ("Gold Window Change %", window_series("GOLD_USD"), PCT, "4-5 Cross-asset"),
    ("Nifty Window Change %", window_series("NIFTY50"), PCT, "4-5 Cross-asset"),
    ("Broad USD Window Change %", window_series("DXY_BROAD"), PCT, "4-5 Cross-asset"),
    ("VIX Window Change %", window_series("VIX"), PCT, "4-5 Cross-asset"),
    ("Brent Path (t-1 = 100)", path_series("BRENT"), NUM2, "4-5 Cross-asset"),
    ("Gold Path (t-1 = 100)", path_series("GOLD_USD"), NUM2, "4-5 Cross-asset"),
    ("Nifty Path (t-1 = 100)", path_series("NIFTY50"), NUM2, "4-5 Cross-asset"),
    ("Brent (USD/bbl)", "AVERAGE ( fact_daily_aligned[brent] )", NUM2, "4-5 Cross-asset"),
    ("Gold (USD/oz)", "AVERAGE ( fact_daily_aligned[gold_usd] )", "#,0", "4-5 Cross-asset"),
    ("Nifty 50", "AVERAGE ( fact_daily_aligned[nifty50] )", "#,0", "4-5 Cross-asset"),
    ("Broad USD Index", "AVERAGE ( fact_daily_aligned[dxy_broad] )", NUM2, "4-5 Cross-asset"),
    ("Corr USDINR~Brent (period)", corr_period("brent_logret"), NUM2, "4-5 Cross-asset"),
    ("Corr USDINR~Gold (period)", corr_period("gold_logret"), NUM2, "4-5 Cross-asset"),
    ("Corr USDINR~Nifty (period)", corr_period("nifty_logret"), NUM2, "4-5 Cross-asset"),
    # --- volatility & correlation
    ("Brent Vol 20d (ann. %)", "AVERAGE ( fact_daily_aligned[brent_vol20] ) / 100", PCT, "6 Volatility & correlation"),
    ("Gold Vol 20d (ann. %)", "AVERAGE ( fact_daily_aligned[gold_vol20] ) / 100", PCT, "6 Volatility & correlation"),
    ("Rolling Corr 60d Brent", "AVERAGE ( fact_daily_aligned[corr60_brent] )", NUM2, "6 Volatility & correlation"),
    ("Rolling Corr 60d Gold", "AVERAGE ( fact_daily_aligned[corr60_gold] )", NUM2, "6 Volatility & correlation"),
    ("Rolling Corr 60d Broad USD", "AVERAGE ( fact_daily_aligned[corr60_dxy] )", NUM2, "6 Volatility & correlation"),
    ("Rolling Corr 60d VIX", "AVERAGE ( fact_daily_aligned[corr60_vix] )", NUM2, "6 Volatility & correlation"),
    ("Rolling Corr 60d Nifty", "AVERAGE ( fact_daily_aligned[corr60_nifty] )", NUM2, "6 Volatility & correlation"),
    ("USDINR Window Vol (ann. %)", f"""IF ( {ONE_WINDOW},
    CALCULATE ( AVERAGE ( fact_event_window[window_vol_ann_pct] ),
        dim_analysis_series[series_id] = "USDINR", fact_event_window[status] = "complete" ) / 100 )""", PCT, "6 Volatility & correlation"),
    ("Window Corr", f"IF ( {ONE_WINDOW}, AVERAGE ( fact_event_window_corr[corr] ) )", NUM2, "6 Volatility & correlation"),
    ("Window Corr n", f"IF ( {ONE_WINDOW}, SUM ( fact_event_window_corr[n_obs] ) )", INT, "6 Volatility & correlation"),
    ("Noise Band (±)", """VAR _n = [Window Corr n]
RETURN IF ( _n > 3, 1.96 / SQRT ( _n - 1 ) )""", NUM2, "6 Volatility & correlation"),
    # --- data quality
    ("DQ Issues", "COUNTROWS ( dq_issues )", INT, "7 Data quality"),
    ("DQ Warnings or Errors", 'CALCULATE ( COUNTROWS ( dq_issues ), dq_issues[severity] IN { "warning", "error" } )', INT, "7 Data quality"),
    ("Pct Days Exact Match", "DIVIDE ( SUM ( dq_alignment[exact] ), SUM ( dq_alignment[days] ) )", "0.0%", "7 Data quality"),
    ("Pct Days Carried Forward", "DIVIDE ( SUM ( dq_alignment[carried] ), SUM ( dq_alignment[days] ) )", "0.0%", "7 Data quality"),
    ("Pct Days Missing", "DIVIDE ( SUM ( dq_alignment[missing] ), SUM ( dq_alignment[days] ) )", "0.0%", "7 Data quality"),
    ("FRED minus RBI (%)", "AVERAGE ( dq_fx_crosscheck[diff_pct] ) / 100", "0.00%", "7 Data quality"),
    ("Mean Abs FRED-RBI Gap (%)", "AVERAGEX ( dq_fx_crosscheck, ABS ( dq_fx_crosscheck[diff_pct] ) ) / 100", "0.00%", "7 Data quality"),
    ("Days > 0.5% Gap", "SUM ( dq_fx_crosscheck[large_gap_flag] )", INT, "7 Data quality"),
    ("Series Not OK", 'CALCULATE ( COUNTROWS ( dq_series_coverage ), dq_series_coverage[status] <> "OK" )', INT, "7 Data quality"),
    # --- captions
    ("Causality Caption", '''"Association, not causation. Confounders: policy rates, oil, US dollar, risk sentiment, flows, RBI action."''', TXT, "0 Captions"),
    ("Basis Caption", '''VAR _b = SELECTEDVALUE ( dim_fx_basis[basis], "RBI" )
RETURN IF ( _b = "RBI",
    "Basis: RBI/FBIL reference rate (~13:30 IST), data to 29-Sep-2026",
    "Basis: Fed H.10 noon New York rate (cross-check), data to 25-Sep-2026" )''', TXT, "0 Captions"),
    ("Window Caption", '''IF ( HASONEVALUE ( dim_window[window_id] ),
    "Window: " & SELECTEDVALUE ( dim_window[window_label] ) & " (" & SELECTEDVALUE ( dim_window[definition] ) & ")",
    "Select ONE window in the slicer to populate the cards, scatter and context table" )''', TXT, "0 Captions"),
]


def q(name):
    """TMDL object name quoting."""
    if name.replace("_", "").isalnum() and not name[0].isdigit():
        return name
    return "'" + name.replace("'", "''") + "'"


def indent(text, n):
    return "\n".join(("\t" * n + line) if line.strip() else "" for line in text.splitlines())


def col_type(table, col, s):
    if (table, col) in TEXT_OVERRIDE:
        return "string"
    if col in DATE_COLS:
        return "dateTime"
    if pd.api.types.is_integer_dtype(s):
        return "int64"
    if pd.api.types.is_float_dtype(s):
        if s.dropna().empty:
            return "string"
        return "int64" if col in KEY_COLS and (s.dropna() % 1 == 0).all() else "double"
    return "string"


M_TYPE = {"int64": "Int64.Type", "double": "type number", "dateTime": "type date", "string": "type text"}


def table_tmdl(table):
    df = pd.read_csv(CSV_DIR / f"{table}.csv", low_memory=False)
    cols = [(c, col_type(table, c, df[c])) for c in df.columns]
    lines = [f"table {q(table)}", f"\tlineageTag: {gid('t', table)}"]
    if table == "dim_date":
        lines.append("\tdataCategory: Time")
    lines.append("")
    for c, t in cols:
        lines.append(f"\tcolumn {q(c)}")
        lines.append(f"\t\tdataType: {t}")
        if t == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        elif t == "int64":
            lines.append("\t\tformatString: 0")
        if table == "dim_date" and c == "date":
            lines.append("\t\tisKey")
        lines.append(f"\t\tlineageTag: {gid('c', table, c)}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: {c}")
        if (table, c) in SORT_BY:
            lines.append(f"\t\tsortByColumn: {SORT_BY[(table, c)]}")
        lines.append("")
    types = ", ".join('{"%s", %s}' % (c, M_TYPE[t]) for c, t in cols)
    m = f'''let
    Source = Csv.Document(File.Contents(DataFolder & "\\{table}.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Nulls = Table.TransformColumns(Promoted, List.Transform(Table.ColumnNames(Promoted), (c) => {{c, each if _ = "" then null else _}})),
    Typed = Table.TransformColumnTypes(Nulls, {{{types}}}, "en-US")
in
    Typed'''
    lines += [f"\tpartition {q(table)} = m", "\t\tmode: import", "\t\tsource =", indent(m, 4), ""]
    return "\n".join(lines) + "\n", {c for c, _ in cols}


def measures_tmdl():
    lines = ["table _Measures", f"\tlineageTag: {gid('t', '_Measures')}", ""]
    for name, expr, fmt, folder in MEASURES:
        if "\n" in expr:
            lines.append(f"\tmeasure {q(name)} =")
            lines.append(indent(expr, 3))
        else:
            lines.append(f"\tmeasure {q(name)} = {expr}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append(f"\t\tlineageTag: {gid('m', name)}")
        lines.append("")
    lines += ["\tcolumn _", "\t\tdataType: string", "\t\tisHidden", f"\t\tlineageTag: {gid('c', '_Measures', '_')}",
              "\t\tsummarizeBy: none", "\t\tsourceColumn: _", "",
              "\tpartition _Measures = m", "\t\tmode: import", "\t\tsource =",
              indent('let\n    Source = #table(type table [_ = text], {})\nin\n    Source', 4), ""]
    return "\n".join(lines) + "\n"


def build_model(root):
    sm = root / f"{NAME}.SemanticModel"
    d = sm / "definition"
    (d / "tables").mkdir(parents=True)
    (sm / "definition.pbism").write_text(json.dumps({
        "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "settings": {}}, indent=2))
    (sm / ".platform").write_text(json.dumps({
        "$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid("sm")}}, indent=2))
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n\n")
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull",
             "", "annotation PBI_ProTooling = [\"DevMode\"]", "", "annotation __PBI_TimeIntelligenceEnabled = 0", ""]
    for t in ["_Measures"] + TABLES:
        model.append(f"ref table {q(t)}")
    (d / "model.tmdl").write_text("\n".join(model) + "\n")
    (d / "expressions.tmdl").write_text(
        f'expression DataFolder = "{DEFAULT_DATA_FOLDER}" meta [IsParameterQuery = true, Type = "Text", '
        f'IsParameterQueryRequired = true]\n\tlineageTag: {gid("e", "DataFolder")}\n\n'
        "\tannotation PBI_ResultType = Text\n\n")
    columns = {}
    for t in TABLES:
        text, cols = table_tmdl(t)
        columns[t] = cols
        (d / "tables" / f"{t}.tmdl").write_text(text)
    (d / "tables" / "_Measures.tmdl").write_text(measures_tmdl())
    rel = []
    for ft, fc, tt, tc, active in RELATIONSHIPS:
        assert fc in columns[ft] and tc in columns[tt], (ft, fc, tt, tc)
        rel += [f"relationship {gid('r', ft, fc, tt, tc)}", f"\tfromColumn: {q(ft)}.{q(fc)}",
                f"\ttoColumn: {q(tt)}.{q(tc)}"] + ([] if active else ["\tisActive: false"]) + [""]
    (d / "relationships.tmdl").write_text("\n".join(rel) + "\n")
    return columns


# =============================================================================
# 2. REPORT (PBIR)
# =============================================================================
V_SCHEMA = f"{SCHEMA}/item/report/definition/visualContainer/2.13.0/schema.json"
P_SCHEMA = f"{SCHEMA}/item/report/definition/page/2.1.0/schema.json"
MEASURE_NAMES = {m[0] for m in MEASURES}


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def field(ref):
    """'table.column' -> column, 'Measure Name' (in MEASURES) -> measure."""
    if ref in MEASURE_NAMES:
        return ({"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": ref}},
                f"_Measures.{ref}", ref)
    t, c = ref.split(".", 1)
    return ({"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}}, f"{t}.{c}", c)


def projections(refs):
    out = []
    for r in refs:
        r, display = (r if isinstance(r, tuple) else (r, None))
        f, qref, native = field(r)
        proj = {"field": f, "queryRef": qref, "nativeQueryRef": native}
        if display:
            proj["displayName"] = display
        out.append(proj)
    return {"projections": out}


class Page:
    def __init__(self, name, display, W=1280, H=720):
        self.name, self.display, self.W, self.H = name, display, W, H
        self.visuals, self.interactions = [], []

    def add(self, vid, vtype, x, y, w, h, roles=None, title=None, objects=None, sort=None, container=None,
            title_size=None):
        vid = f"{self.name}_{vid}"[:50]
        visual = {"visualType": vtype}
        if roles:
            visual["query"] = {"queryState": {role: projections(refs) for role, refs in roles.items()}}
            if sort:
                f, _, _ = field(sort[0])
                visual["query"]["sortDefinition"] = {"sort": [{"field": f, "direction": sort[1]}],
                                                     "isDefaultSort": False}
        if vtype == "tableEx":
            objects = {"total": [{"properties": {"totals": lit(False)}}], **(objects or {})}
        if objects:
            visual["objects"] = objects
        vco = dict(container or {})
        if title:
            tprops = {"show": lit(True), "text": lit(title)}
            if title_size:
                tprops["fontSize"] = lit(title_size)
            vco["title"] = [{"properties": tprops}]
            vco["subTitle"] = [{"properties": {"show": lit(False)}}]
        if vco:
            visual["visualContainerObjects"] = vco
        self.visuals.append({"$schema": V_SCHEMA, "name": vid,
                             "position": {"x": x, "y": y, "z": len(self.visuals) * 100, "height": h,
                                          "width": w, "tabOrder": len(self.visuals) * 100},
                             "visual": visual})
        return vid

    def text(self, vid, x, y, w, h, text, size=10, bold=False, color="#3C434C"):
        style = {"fontSize": f"{size}pt", "color": color}
        if bold:
            style["fontWeight"] = "bold"
        return self.add(vid, "textbox", x, y, w, h,
                        objects={"general": [{"properties": {"paragraphs": [
                            {"textRuns": [{"value": text, "textStyle": style}]}]}}]})

    def no_filter(self, source, target):
        self.interactions.append({"source": source, "target": target, "type": "NoFilter"})


NO_SLICER_HEADER = {"header": [{"properties": {"show": lit(False)}}]}


def slicer_default(entity, column, value):
    """Saved slicer selection, in the format Power BI Desktop writes."""
    return {"general": [{"properties": {"filter": {"filter": {
        "Version": 2,
        "From": [{"Name": "s", "Entity": entity, "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": column}}],
            "Values": [[{"Literal": {"Value": "'" + value + "'"}}]]}}}]}}}}]}


def header(p, title, subtitle):
    p.text("title", 16, 6, 1010, 36, title, size=18, bold=True, color="#1F3A5F")
    p.text("subtitle", 16, 40, 1010, 28, subtitle, size=10)
    p.add("basis", "slicer", 1050, 6, 214, 64, roles={"Values": ["dim_fx_basis.basis"]}, title="USD/INR source",
          title_size=10, objects={"data": [{"properties": {"mode": lit("Dropdown")}}], **NO_SLICER_HEADER,
                                   **slicer_default("dim_fx_basis", "basis", "RBI"),
                                   "selection": [{"properties": {"singleSelect": lit(True)}}]})
    caption_objs = {"labels": [{"properties": {"fontSize": lit(8), "color": {"solid": {"color": lit("#5B6470")}}}}],
                    "categoryLabels": [{"properties": {"show": lit(False)}}],
                    "wordWrap": [{"properties": {"show": lit(True)}}]}
    p.add("caption", "card", 16, 672, 860, 42, roles={"Values": ["Causality Caption"]}, objects=caption_objs)
    p.add("basiscap", "card", 884, 672, 380, 42, roles={"Values": ["Basis Caption"]}, objects=caption_objs)


def card(p, vid, x, y, w, h, measure, title, size=20):
    return p.add(vid, "card", x, y, w, h, roles={"Values": [measure]}, title=title, title_size=10,
                 objects={"labels": [{"properties": {"fontSize": lit(size)}}],
                          "categoryLabels": [{"properties": {"show": lit(False)}}]})


def window_slicer(p, x, y, w, h):
    return p.add("window", "slicer", x, y, w, h, roles={"Values": ["dim_window.window_label"]},
                 title="Window (pick one)", title_size=10, objects={**NO_SLICER_HEADER, **slicer_default("dim_window", "window_label", "30 days after"),
                                                   "data": [{"properties": {"mode": lit("Dropdown")}}],
                                                   "selection": [{"properties": {"singleSelect": lit(True)}}]})


DEFAULT_EVENT = "E12 · US-Israel war on Iran (Feb-2026)"


def event_slicer(p, x, y, w, h, single=False, default=None):
    objs = {**NO_SLICER_HEADER, "data": [{"properties": {"mode": lit("Dropdown")}}]}
    if default:
        objs.update(slicer_default("dim_event", "event_label", default))
    if single:
        objs["selection"] = [{"properties": {"singleSelect": lit(True)}}]
    return p.add("event", "slicer", x, y, w, h, roles={"Values": ["dim_event.event_label"]},
                 title="Event" + (" (pick one)" if single else "s"), title_size=10, objects=objs)


def build_pages():
    pages = []

    # ---------------- Page 1
    p = Page("p1_overview", "1 INR-USD Overview")
    header(p, "USD/INR overview", "How the rupee moved 2013-2026 before any event is layered on. Up = rupee weaker. India CPI is on base 2024=100 from Jan-2026.")
    p.add("dates", "slicer", 16, 76, 300, 92, roles={"Values": ["dim_date.date"]}, title="Date range", title_size=10,
          objects=NO_SLICER_HEADER)
    for i, (m, t) in enumerate([("USDINR Latest", "USD/INR latest"), ("USDINR % Change (period)", "USD/INR % chg"),
                                ("INR % Change (period)", "Rupee % chg"), ("USDINR Vol 20d (ann. %)", "Avg 20d vol"),
                                ("Rate Differential IN-US (pp)", "Repo - Fed (pp)")]):
        card(p, f"k{i}", 326 + i * 189, 76, 181, 92, m, t)
    p.add("line", "lineChart", 16, 176, 780, 238, roles={"Category": ["dim_date.date"], "Y": ["USDINR Rate"]},
          title="USD/INR (INR per USD, up = rupee weaker)")
    p.add("vol", "lineChart", 804, 176, 460, 238, roles={"Category": ["dim_date.date"], "Y": ["USDINR Vol 20d (ann. %)"]},
          title="USD/INR 20-day volatility (annualised)")
    p.add("rates", "lineChart", 16, 422, 410, 242,
          roles={"Category": ["dim_date.date"], "Y": ["RBI Repo Rate %", "Fed Funds Upper %"]},
          title="Policy rates: RBI repo vs Fed funds")
    p.add("cpi", "lineChart", 434, 422, 410, 242,
          roles={"Category": ["dim_date.date"], "Y": ["India CPI YoY %", "US CPI YoY %"]},
          title="CPI inflation YoY, India vs US")
    p.add("rbi", "clusteredColumnChart", 852, 422, 412, 242,
          roles={"Category": ["dim_date.date"], "Y": ["RBI Net FX (USD bn, monthly)"]},
          title="RBI net USD bought (+) / sold (-), US$ bn")
    pages.append(p)

    # ---------------- Page 2
    p = Page("p2_timeline", "2 Event Timeline")
    header(p, "Event timeline", "13 events on the USD/INR path. Dots = t(0), the first trading day after the news.")
    event_slicer(p, 16, 76, 300, 64)
    p.text("hint", 330, 92, 700, 40, "Tip: click a row in the events table to filter the milestones beside it. "
           "Hover a dot on the chart for the event name.", size=9, color="#5B6470")
    p.add("line", "lineChart", 16, 148, 1248, 250,
          roles={"Category": ["dim_date.date"], "Y": ["USDINR Rate", "Event Marker (USDINR)"],
                 "Tooltips": ["Event Name on Date"]},
          title="USD/INR with event dates (dots = t0, first trading day after the news)",
          objects={"lineStyles": [
              {"properties": {"showMarker": lit(True), "strokeWidth": lit(0), "markerSize": lit(7)},
               "selector": {"metadata": "_Measures.Event Marker (USDINR)"}},
              {"properties": {"showMarker": lit(False)}, "selector": {"metadata": "_Measures.USDINR Rate"}}]})
    TABLE_WRAP = {"values": [{"properties": {"wordWrap": lit(True), "fontSize": lit(9)}}],
                  "columnHeaders": [{"properties": {"wordWrap": lit(True), "fontSize": lit(9)}}]}
    p.add("events", "tableEx", 16, 406, 790, 258,
          roles={"Values": [("dim_event.event_id", "ID"), ("dim_event.short_name", "Event"),
                            ("dim_event.event_type", "Type"), ("dim_event.anchor_date", "News date"),
                            ("Event t0 Date", "t0 (trading day)"), ("dim_event.source_org", "Source")]},
          title="Events: dates and sources", sort=("dim_event.event_id", "Ascending"), objects=TABLE_WRAP)
    p.add("ms", "tableEx", 814, 406, 450, 258,
          roles={"Values": [("dim_event_milestone.event_id", "ID"), ("dim_event_milestone.milestone_date", "Date"),
                            ("dim_event_milestone.milestone", "Milestone")]},
          title="Milestones inside each event", sort=("dim_event_milestone.milestone_date", "Ascending"),
          objects=TABLE_WRAP)
    pages.append(p)

    # ---------------- Page 3
    p = Page("p3_windows", "3 Event Window Analysis")
    header(p, "Event-window analysis", "USD/INR % change per window. Pre = t(-k)->t(-1); event = t(-1)->t(0); post = t(-1)->t(+k), trading days.")
    event_slicer(p, 16, 76, 300, 64)
    w = window_slicer(p, 324, 76, 260, 64)
    p.add("wcap", "card", 592, 76, 672, 64, roles={"Values": ["Window Caption"]},
          objects={"labels": [{"properties": {"fontSize": lit(9), "color": {"solid": {"color": lit("#1F3A5F")}}}}],
                   "categoryLabels": [{"properties": {"show": lit(False)}}],
                   "wordWrap": [{"properties": {"show": lit(True)}}]})
    diverging = {"FillRule": {
        "Input": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}},
                              "Property": "USDINR Window Change % (matrix)"}},
        "FillRule": {"linearGradient3": {
            "min": {"color": {"Literal": {"Value": "'#2A78D6'"}}, "value": {"Literal": {"Value": "-0.03D"}}},
            "mid": {"color": {"Literal": {"Value": "'#F0EFEC'"}}, "value": {"Literal": {"Value": "0D"}}},
            "max": {"color": {"Literal": {"Value": "'#E34948'"}}, "value": {"Literal": {"Value": "0.03D"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}}}}}}
    mx = p.add("matrix", "pivotTable", 16, 148, 760, 262,
               roles={"Rows": [("dim_event.event_id", "Event")], "Columns": [("dim_window.window_label", "Window")],
                      "Values": [("USDINR Window Change % (matrix)", "USD/INR % chg")]},
               title="USD/INR % change by event and window (red = rupee weaker, blue = stronger)",
               objects={"subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
                        "values": [{"properties": {"fontSize": lit(9)}},
                                   {"properties": {"backColor": {"solid": {"color": {"expr": diverging}}}},
                                    "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                                 "metadata": "_Measures.USDINR Window Change % (matrix)"}}],
                        "columnHeaders": [{"properties": {"fontSize": lit(9), "wordWrap": lit(True)}}],
                        "rowHeaders": [{"properties": {"fontSize": lit(9)}}]})
    p.no_filter(w, mx)
    pa = p.add("path", "lineChart", 784, 148, 480, 262,
               roles={"Category": ["fact_event_path.rel_day"], "Y": ["USDINR Path (t-1 = 100)"],
                      "Series": ["dim_event.event_id"]},
               title="USD/INR path, t(-1) = 100 (pick events above to compare)")
    p.no_filter(w, pa)
    card(p, "k1", 16, 418, 200, 78, "Median USDINR Window Change %", "Median change", size=15)
    card(p, "k2", 16, 502, 200, 78, "Share of Events INR Weaker", "Share: rupee weaker", size=15)
    card(p, "k3", 16, 586, 200, 78, "Events Measured", "Events measured", size=15)
    p.add("bar", "clusteredColumnChart", 224, 418, 380, 246,
          roles={"Category": [("dim_event.event_id", "Event")],
                 "Y": [("USDINR Window Change %", "USD/INR % chg"), ("USDINR minus Broad USD %", "Minus broad USD (pp)")]},
          title="Rupee-specific move? USD/INR vs USD/INR minus broad USD")
    p.add("ctx", "tableEx", 612, 418, 652, 246,
          roles={"Values": [("dim_event.event_id", "ID"), ("Window Start Date", "Start"), ("Window End Date", "End"),
                            ("USDINR Window Change %", "USD/INR %"), ("USDINR Baseline Percentile", "Pctile vs 3y"),
                            ("Policy Changes in Window", "Policy changes"), ("RBI Net FX in Window (USD bn)", "RBI FX $bn"),
                            ("Overlapping Events", "Overlaps")]},
          title="What else was happening in the selected window", sort=("dim_event.event_id", "Ascending"),
          objects={"values": [{"properties": {"wordWrap": lit(True), "fontSize": lit(9)}}],
                   "columnHeaders": [{"properties": {"wordWrap": lit(True), "fontSize": lit(9)}}]})
    pages.append(p)

    # ---------------- Page 4
    p = Page("p4_oil", "4 INR vs Crude Oil")
    header(p, "USD/INR vs crude oil", "India imports most of its crude - a plausible channel, but oil also reacts to the same events and to unrelated supply news.")
    window_slicer(p, 16, 76, 260, 64)
    ev = event_slicer(p, 284, 76, 320, 64, single=True, default=DEFAULT_EVENT)
    p.text("hint", 618, 90, 640, 40, "Window drives the scatter. Event drives the bottom-right path only; "
           "the other charts always show all events.", size=9, color="#5B6470")
    usd = p.add("usd", "lineChart", 16, 148, 620, 164, roles={"Category": ["dim_date.date"], "Y": ["USDINR Rate"]},
                title="USD/INR, INR per USD")
    br = p.add("brent", "lineChart", 16, 318, 620, 164, roles={"Category": ["dim_date.date"], "Y": ["Brent (USD/bbl)"]},
               title="Brent crude, USD per barrel")
    sc = p.add("sc", "scatterChart", 644, 148, 620, 334,
               roles={"Category": [("dim_event.event_id", "Event")], "X": [("Brent Window Change %", "Brent % chg")],
                      "Y": [("USDINR Window Change %", "USD/INR % chg")]},
               title="Each dot = one event: Brent vs USD/INR change in the selected window",
               objects={"categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(8)}}],
                        "dataPoint": [{"properties": {"fill": {"solid": {"color": lit("#1F3A5F")}}}}]})
    co = p.add("corr", "clusteredColumnChart", 16, 490, 620, 174,
               roles={"Category": [("dim_date.year", "Year")], "Y": [("Corr USDINR~Brent (period)", "Correlation")]},
               title="Correlation of daily returns by year, USD/INR vs Brent (near 0 = no link)")
    p.add("path", "lineChart", 644, 490, 620, 174,
          roles={"Category": [("fact_event_path.rel_day", "Trading days from t0")],
                 "Y": [("USDINR Path (t-1 = 100)", "USD/INR"), ("Brent Path (t-1 = 100)", "Brent")]},
          title="Selected event: USD/INR and Brent, t(-1) = 100")
    for target in (usd, br, sc, co):
        p.no_filter(ev, target)
    pages.append(p)

    # ---------------- Page 5
    p = Page("p5_gold_eq", "5 INR vs Gold & Equity")
    header(p, "USD/INR vs gold and Indian equities", "Safe-haven and risk-appetite channels, per event window.")
    window_slicer(p, 16, 76, 260, 64)
    p.text("hint", 290, 90, 960, 40, "Gold is a common safe haven and Nifty a gauge of risk appetite. Dots in the top-left or "
           "bottom-right quadrant mean the rupee and that market moved in opposite directions.", size=9, color="#5B6470")
    dot = {"categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(8)}}],
           "dataPoint": [{"properties": {"fill": {"solid": {"color": lit("#1F3A5F")}}}}]}
    p.add("scg", "scatterChart", 16, 148, 306, 250,
          roles={"Category": [("dim_event.event_id", "Event")], "X": [("Gold Window Change %", "Gold % chg")],
                 "Y": [("USDINR Window Change %", "USD/INR % chg")]},
          title="Gold vs USD/INR (each dot = event)", objects=dot)
    p.add("scn", "scatterChart", 330, 148, 306, 250,
          roles={"Category": [("dim_event.event_id", "Event")], "X": [("Nifty Window Change %", "Nifty % chg")],
                 "Y": [("USDINR Window Change %", "USD/INR % chg")]},
          title="Nifty 50 vs USD/INR (each dot = event)", objects=dot)
    p.add("gold", "lineChart", 644, 148, 306, 250, roles={"Category": ["dim_date.date"], "Y": [("Gold (USD/oz)", "Gold")]},
          title="Gold, USD per oz (LBMA AM)")
    p.add("nifty", "lineChart", 958, 148, 306, 250, roles={"Category": ["dim_date.date"], "Y": [("Nifty 50", "Nifty 50")]},
          title="NIFTY 50 index")
    p.add("mx", "pivotTable", 16, 406, 1248, 258,
          roles={"Rows": [("dim_event.event_label", "Event")], "Columns": [("dim_analysis_series.display_name", "Market")],
                 "Values": [("Window Change % (price series)", "% chg")]},
          title="% change of each market in the selected window",
          objects={"subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
                   "values": [{"properties": {"fontSize": lit(9)}}],
                   "columnHeaders": [{"properties": {"fontSize": lit(9), "wordWrap": lit(True)}}],
                   "rowHeaders": [{"properties": {"fontSize": lit(9)}}]})
    pages.append(p)

    # ---------------- Page 6
    p = Page("p6_vol_corr", "6 Volatility & Correlation")
    header(p, "Volatility and correlation", "Daily returns; series are observed at different clock times, which biases same-day correlation towards zero.")
    window_slicer(p, 16, 76, 260, 64)
    p.text("hint", 290, 90, 960, 40, "Top row: full history. Bottom row: the 13 events in the selected window. "
           "Correlations between -0.36 and +0.36 are within noise for a 30-day window.", size=9, color="#5B6470")

    def colours(pairs):
        return [{"properties": {"fill": {"solid": {"color": lit(c)}}}, "selector": {"metadata": f"_Measures.{m}"}}
                for m, c in pairs]
    p.add("vol", "lineChart", 16, 148, 620, 250,
          roles={"Category": ["dim_date.date"],
                 "Y": [("USDINR Vol 20d (ann. %)", "USD/INR"), ("Brent Vol 20d (ann. %)", "Brent"),
                       ("Gold Vol 20d (ann. %)", "Gold")]},
          title="20-day annualised volatility (axis capped at 100%; Brent hit ~350% in Apr-2020)",
          objects={"valueAxis": [{"properties": {"start": lit(0), "end": lit(1)}}],
                   "dataPoint": colours([("USDINR Vol 20d (ann. %)", "#1F3A5F"), ("Brent Vol 20d (ann. %)", "#D98E04"),
                                         ("Gold Vol 20d (ann. %)", "#1A7F7A")])})
    p.add("corr", "lineChart", 644, 148, 620, 250,
          roles={"Category": ["dim_date.date"],
                 "Y": [("Rolling Corr 60d Broad USD", "Broad US dollar"), ("Rolling Corr 60d Brent", "Brent")]},
          title="60-day rolling correlation with USD/INR daily returns",
          objects={"valueAxis": [{"properties": {"start": lit(-1), "end": lit(1)}}],
                   "dataPoint": colours([("Rolling Corr 60d Broad USD", "#1F3A5F"), ("Rolling Corr 60d Brent", "#D98E04")])})
    corr_fill = {"FillRule": {
        "Input": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": "Window Corr"}},
        "FillRule": {"linearGradient3": {
            "min": {"color": {"Literal": {"Value": "'#2A78D6'"}}, "value": {"Literal": {"Value": "-0.8D"}}},
            "mid": {"color": {"Literal": {"Value": "'#F0EFEC'"}}, "value": {"Literal": {"Value": "0D"}}},
            "max": {"color": {"Literal": {"Value": "'#E34948'"}}, "value": {"Literal": {"Value": "0.8D"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}}}}}}
    p.add("wc", "pivotTable", 16, 406, 620, 258,
          roles={"Rows": [("dim_event.event_id", "Event")], "Columns": [("dim_analysis_series.display_name", "Market")],
                 "Values": [("Window Corr", "r")]},
          title="In-window correlation with USD/INR daily returns (selected window)",
          objects={"subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
                   "values": [{"properties": {"fontSize": lit(9)}},
                              {"properties": {"backColor": {"solid": {"color": {"expr": corr_fill}}}},
                               "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                            "metadata": "_Measures.Window Corr"}}],
                   "columnHeaders": [{"properties": {"fontSize": lit(9), "wordWrap": lit(True)}}],
                   "rowHeaders": [{"properties": {"fontSize": lit(9)}}]})
    p.add("rbi", "scatterChart", 644, 406, 310, 258,
          roles={"Category": [("dim_event.event_id", "Event")], "X": [("RBI Net FX in Window (USD bn)", "RBI net FX, US$ bn")],
                 "Y": [("USDINR Window Change %", "USD/INR % chg")]},
          title="RBI net FX vs USD/INR change",
          objects={"categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(8)}}],
                   "dataPoint": [{"properties": {"fill": {"solid": {"color": lit("#1F3A5F")}}}}]})
    p.add("wv", "clusteredColumnChart", 962, 406, 302, 258,
          roles={"Category": [("dim_event.event_id", "Event")], "Y": [("USDINR Window Vol (ann. %)", "Vol (ann.)")]},
          title="USD/INR volatility inside the window", sort=("dim_event.event_id", "Ascending"))
    pages.append(p)

    # ---------------- Page 7
    p = Page("p7_dq", "7 Data Quality")
    header(p, "Data quality", "Every data decision is logged: coverage, alignment, source cross-checks and issues.")
    for i, (m, t) in enumerate([("DQ Issues", "Logged issues"), ("DQ Warnings or Errors", "Warnings / errors"),
                                ("Mean Abs FRED-RBI Gap (%)", "Mean |FRED - RBI|"), ("Days > 0.5% Gap", "Days gap > 0.5%"),
                                ("Series Not OK", "Series not OK")]):
        card(p, f"k{i}", 16 + i * 251, 76, 243, 92, m, t)
    wrap = {"values": [{"properties": {"wordWrap": lit(True), "fontSize": lit(9)}}],
            "columnHeaders": [{"properties": {"wordWrap": lit(True), "fontSize": lit(9)}}]}
    p.add("cov", "tableEx", 16, 176, 620, 238,
          roles={"Values": [("dq_series_coverage.series_id", "Series"), ("dq_series_coverage.first_date", "First"),
                            ("dq_series_coverage.last_date", "Last"), ("dq_series_coverage.n_obs", "Obs"),
                            ("dq_series_coverage.max_gap_calendar_days", "Max gap (days)"),
                            ("dq_series_coverage.status", "Status")]},
          title="Series coverage", objects=wrap)
    p.add("al", "hundredPercentStackedBarChart", 644, 176, 620, 238,
          roles={"Category": [("dq_alignment.series_id", "Series")],
                 "Y": [("Pct Days Exact Match", "Same-day value"), ("Pct Days Carried Forward", "Carried forward (<= 5 days)"),
                       ("Pct Days Missing", "Missing")]},
          title="How each series lines up with the Indian FX calendar")
    p.add("x", "clusteredColumnChart", 16, 422, 400, 242,
          roles={"Category": [("dim_date.year", "Year")], "Y": [("Mean Abs FRED-RBI Gap (%)", "Mean |gap|")]},
          title="FRED H.10 vs RBI rate: mean absolute gap by year")
    p.add("iss", "tableEx", 424, 422, 840, 242,
          roles={"Values": [("dq_issues.severity", "Severity"), ("dq_issues.series_id", "Series"),
                            ("dq_issues.obs_date", "Date"), ("dq_issues.rule", "Rule"),
                            ("dq_issues.detail", "Detail"), ("dq_issues.action", "Action taken")]},
          title="Issue log (every data decision)", sort=("dq_issues.severity", "Descending"), objects=wrap)
    pages.append(p)
    return pages


BASE_THEME = "Fluent2-CY26SU09"


def build_report(root):
    rp = root / f"{NAME}.Report"
    d = rp / "definition"
    (d / "pages").mkdir(parents=True)
    (rp / "definition.pbir").write_text(json.dumps({
        "$schema": f"{SCHEMA}/item/report/definitionProperties/1.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2))
    (rp / ".platform").write_text(json.dumps({
        "$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": gid("rp")}}, indent=2))
    (d / "version.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2))
    # custom theme shipped with the report
    theme_src = PBI_DIR / "Report_Theme.json"
    reg = rp / "StaticResources" / "RegisteredResources"
    reg.mkdir(parents=True)
    shutil.copy(theme_src, reg / "GeoINRTheme.json")
    # base theme exactly as Power BI Desktop (Sep 2026) writes it
    base = rp / "StaticResources" / "SharedResources" / "BaseThemes"
    base.mkdir(parents=True)
    shutil.copy(PBI_DIR / f"Base_Theme_{BASE_THEME}.json", base / f"{BASE_THEME}.json")
    (d / "report.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": BASE_THEME, "type": "SharedResources",
                          "reportVersionAtImport": {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"}},
            "customTheme": {"name": "GeoINRTheme.json", "type": "RegisteredResources",
                            "reportVersionAtImport": {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"}}},
        "objects": {"section": [{"properties": {"verticalAlignment": {"expr": {"Literal": {"Value": "'Top'"}}}}}]},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "GeoINRTheme.json", "path": "GeoINRTheme.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True}}, indent=2))
    pages = build_pages()
    (d / "pages" / "pages.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p.name for p in pages], "activePageName": pages[0].name}, indent=2))
    n_vis = 0
    for p in pages:
        pd_ = d / "pages" / p.name
        (pd_ / "visuals").mkdir(parents=True)
        page = {"$schema": P_SCHEMA, "name": p.name, "displayName": p.display, "displayOption": "FitToPage",
                "height": p.H, "width": p.W}
        if p.interactions:
            page["visualInteractions"] = p.interactions
        (pd_ / "page.json").write_text(json.dumps(page, indent=2))
        for v in p.visuals:
            (pd_ / "visuals" / v["name"]).mkdir()
            (pd_ / "visuals" / v["name"] / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False))
            n_vis += 1
    return pages, n_vis


def check_fields(pages, columns):
    """Every column a visual uses must exist in the model."""
    for p in pages:
        for v in p.visuals:
            for role in v["visual"].get("query", {}).get("queryState", {}).values():
                for pr in role["projections"]:
                    f = pr["field"]
                    if "Column" in f:
                        t, c = f["Column"]["Expression"]["SourceRef"]["Entity"], f["Column"]["Property"]
                        assert c in columns[t], f"{p.name}/{v['name']}: {t}.{c} not in model"


def write_measures_dax():
    lines = ["// Generated by 04_PowerBI/generate_powerbi_project.py - the same measures are inside GeoINR.SemanticModel.",
             "// Sign convention: USD/INR change > 0  =>  rupee WEAKENED.", ""]
    folder = None
    for name, expr, fmt, f in MEASURES:
        if f != folder:
            lines += ["", f"// ---------- {f} ----------"]
            folder = f
        lines += [f"{name} =", expr, f"// format: {fmt}" if fmt else "", ""]
    (PBI_DIR / "DAX_Measures.dax").write_text("\n".join(lines), encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / f"{NAME}.pbip").write_text(json.dumps({
        "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json", "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2))
    (OUT / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    columns = build_model(OUT)
    pages, n_vis = build_report(OUT)
    check_fields(pages, columns)
    write_measures_dax()
    print(f"PBIP written to {OUT}: {len(TABLES)} tables + _Measures ({len(MEASURES)} measures), "
          f"{len(RELATIONSHIPS)} relationships, {len(pages)} pages, {n_vis} visuals")


if __name__ == "__main__":
    main()
