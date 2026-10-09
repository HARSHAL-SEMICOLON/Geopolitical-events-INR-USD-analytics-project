CREATE VIEW v_event_cross_asset AS
SELECT f.basis, f.event_id, f.window_id, f.series_id, f.change, f.change_unit, f.status
FROM fact_event_window f;
CREATE VIEW v_event_usdinr_summary AS
SELECT e.event_id, e.event_label, w.window_id, w.window_label, w.sort_order,
       f.basis, f.status, f.start_date, f.end_date, f.change AS usdinr_pct_change,
       f.inr_pct_change, f.usdinr_minus_dxy_pp, f.percentile, f.z_score,
       c.overlapping_events, c.rbi_repo_changes, c.fomc_target_changes
FROM fact_event_window f
JOIN dim_event e  ON e.event_id = f.event_id
JOIN dim_window w ON w.window_id = f.window_id
LEFT JOIN fact_event_window_context c
       ON c.basis = f.basis AND c.event_id = f.event_id AND c.window_id = f.window_id
WHERE f.series_id = 'USDINR';
CREATE TABLE dim_analysis_series (
  series_id TEXT PRIMARY KEY, display_name TEXT, unit TEXT, change_unit TEXT, sort_order INTEGER,
  source_series_rbi_basis TEXT, source_series_fred_basis TEXT, interpretation_of_positive TEXT);
CREATE TABLE dim_date (
  date_key INTEGER PRIMARY KEY, date TEXT NOT NULL, year INTEGER, quarter TEXT,
  month_num INTEGER, month_name TEXT, year_month TEXT, day_of_week TEXT, is_weekend INTEGER,
  fiscal_year_in TEXT, is_rbi_fx_day INTEGER, is_us_h10_day INTEGER, rbi_listed_holiday INTEGER);
CREATE TABLE dim_event (
  event_id TEXT PRIMARY KEY, event_name TEXT NOT NULL, short_name TEXT, event_type TEXT, affected_region TEXT,
  india_direct TEXT, event_start_date TEXT NOT NULL, event_end_date TEXT, end_date_basis TEXT,
  anchor_date TEXT NOT NULL, anchor_rule TEXT, timing_note TEXT, source_org TEXT,
  source_title TEXT, source_url TEXT, source_pub_date TEXT, source_type TEXT,
  selection_rationale TEXT, known_concurrent_factors TEXT, duration_days INTEGER,
  event_label TEXT);
CREATE TABLE dim_event_milestone (
  event_id TEXT REFERENCES dim_event(event_id), milestone_date TEXT, milestone TEXT,
  source_org TEXT, source_url TEXT, source_pub_date TEXT, source_type TEXT, date_key INTEGER);
CREATE TABLE dim_fx_basis (
  basis TEXT PRIMARY KEY, fx_series_id TEXT REFERENCES dim_series(series_id),
  calendar_definition TEXT, is_primary INTEGER);
CREATE TABLE dim_series (
  series_id TEXT PRIMARY KEY, series_name TEXT, fact_table TEXT, category TEXT, unit TEXT,
  frequency TEXT, source_org TEXT, source_dataset TEXT, source_code TEXT, source_url TEXT,
  native_timestamp TEXT, role_in_analysis TEXT, notes TEXT);
CREATE TABLE dim_window (
  window_id TEXT PRIMARY KEY, window_label TEXT, start_offset INTEGER, end_offset INTEGER,
  window_type TEXT, sort_order INTEGER, definition TEXT);
CREATE TABLE dq_alignment (
  basis TEXT, series_id TEXT, days INTEGER, exact INTEGER, carried INTEGER, missing INTEGER,
  max_staleness INTEGER, note TEXT, pct_exact REAL, pct_carried REAL, pct_missing REAL,
  PRIMARY KEY (basis, series_id));
CREATE TABLE dq_fx_crosscheck (
  date_key INTEGER PRIMARY KEY, rbi_ref REAL, fred_h10 REAL, status TEXT, diff_inr REAL,
  diff_pct REAL, large_gap_flag INTEGER);
CREATE TABLE dq_issues (
  issue_id INTEGER PRIMARY KEY, stage TEXT, series_id TEXT, obs_date TEXT, rule TEXT,
  detail TEXT, severity TEXT, action TEXT);
CREATE TABLE dq_series_coverage (
  series_id TEXT PRIMARY KEY, first_date TEXT, last_date TEXT, n_obs INTEGER,
  expected_frequency TEXT, max_gap_calendar_days INTEGER, gaps_over_5d INTEGER,
  days_behind_build_date INTEGER, status TEXT);
CREATE TABLE dq_summary (
  metric TEXT PRIMARY KEY, value REAL, unit TEXT, explanation TEXT);
CREATE TABLE fact_commodity (
  date_key INTEGER REFERENCES dim_date(date_key), series_id TEXT REFERENCES dim_series(series_id),
  value REAL, pct_change REAL, log_return REAL, days_since_prev_obs INTEGER,
  PRIMARY KEY (date_key, series_id));
CREATE TABLE fact_daily_aligned (
  basis TEXT REFERENCES dim_fx_basis(basis), date_key INTEGER REFERENCES dim_date(date_key),
  trading_day_seq INTEGER, usdinr REAL, usdinr_pct REAL, inr_pct REAL, usdinr_logret REAL,
  brent REAL, gold_usd REAL, nifty50 REAL, dxy_broad REAL, vix REAL, ust10y REAL,
  ffr_upper REAL, in_repo REAL, rate_diff_in_us REAL,
  brent_logret REAL, gold_logret REAL, nifty_logret REAL, dxy_logret REAL, vix_logret REAL,
  ust10y_change_pp REAL,
  usdinr_vol20 REAL, brent_vol20 REAL, gold_vol20 REAL, nifty_vol20 REAL, dxy_vol20 REAL,
  corr60_brent REAL, corr60_gold REAL, corr60_nifty REAL, corr60_dxy REAL, corr60_vix REAL,
  corr60_ust10y REAL,
  PRIMARY KEY (basis, date_key));
CREATE TABLE fact_event_anchor (
  basis TEXT, event_id TEXT REFERENCES dim_event(event_id), covered INTEGER, anchor_date TEXT,
  t0_date TEXT, t_minus1_date TEXT, calendar_days_anchor_to_t0 INTEGER,
  last_available_date TEXT, trading_days_after_available INTEGER, note TEXT,
  t0_date_key INTEGER, PRIMARY KEY (basis, event_id));
CREATE TABLE fact_event_path (
  basis TEXT, event_id TEXT, rel_day INTEGER, date TEXT, series_id TEXT, indexed_value REAL,
  PRIMARY KEY (basis, event_id, rel_day, series_id));
CREATE TABLE fact_event_window (
  basis TEXT, event_id TEXT REFERENCES dim_event(event_id),
  window_id TEXT REFERENCES dim_window(window_id), series_id TEXT, status TEXT,
  start_date TEXT, end_date TEXT, trading_days INTEGER, start_value REAL, end_value REAL,
  change REAL, log_change REAL, change_unit TEXT, n_returns INTEGER, window_vol_ann_pct REAL,
  start_staleness_days REAL, end_staleness_days REAL, inr_pct_change REAL,
  usdinr_minus_dxy_pp REAL, baseline_n INTEGER, baseline_mean_pct REAL, baseline_sd_pct REAL,
  z_score REAL, percentile REAL, direction TEXT, is_unusual_2sd INTEGER,
  PRIMARY KEY (basis, event_id, window_id, series_id));
CREATE TABLE fact_event_window_context (
  basis TEXT, event_id TEXT, window_id TEXT, start_date TEXT, end_date TEXT, status TEXT,
  trading_days INTEGER, overlapping_events TEXT, rbi_repo_changes TEXT,
  fomc_target_changes TEXT, rbi_net_fx_usd_mn REAL, rbi_fx_months TEXT,
  n_overlapping INTEGER, has_policy_change INTEGER,
  PRIMARY KEY (basis, event_id, window_id));
CREATE TABLE fact_event_window_corr (
  basis TEXT, event_id TEXT, window_id TEXT, series_id TEXT, n_obs INTEGER, status TEXT,
  corr REAL, PRIMARY KEY (basis, event_id, window_id, series_id));
CREATE TABLE fact_fx (
  date_key INTEGER REFERENCES dim_date(date_key), series_id TEXT REFERENCES dim_series(series_id),
  usd_inr REAL, usdinr_open REAL, usdinr_close REAL, inr_strongest REAL, inr_weakest REAL,
  usdinr_pct_change REAL, inr_pct_change REAL, log_return REAL, days_since_prev_obs INTEGER,
  PRIMARY KEY (date_key, series_id));
CREATE TABLE fact_macro (
  date_key INTEGER, series_id TEXT REFERENCES dim_series(series_id), period_start TEXT,
  frequency TEXT, value REAL, yoy_pct REAL, mom_change REAL, series_version TEXT,
  PRIMARY KEY (date_key, series_id));
CREATE TABLE fact_market (
  date_key INTEGER REFERENCES dim_date(date_key), series_id TEXT REFERENCES dim_series(series_id),
  value REAL, change REAL, change_unit TEXT, log_return REAL, days_since_prev_obs INTEGER,
  PRIMARY KEY (date_key, series_id));
CREATE INDEX ix_ew_event ON fact_event_window(event_id, series_id);
CREATE INDEX ix_fx_series ON fact_fx(series_id);
CREATE INDEX ix_path_event ON fact_event_path(event_id, series_id);