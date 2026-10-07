-- Reporting views: shared definitions of the main measures for SQL users and Power BI.
-- All views cover every loaded year; is_complete_year / is_analysis_period mark the complete
-- years 2012-2024 (DQ24), because the most recent months are not fully reported yet.
-- KSI = crash in which someone was killed or seriously injured.

-- One row per year: headline KPIs, year-over-year change and the LGA with most KSI crashes.
CREATE OR REPLACE VIEW analytics.vw_crash_summary AS
WITH yearly AS (
    SELECT d.year,
           bool_and(d.is_analysis_period)                AS is_complete_year,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes,
           count(*) FILTER (WHERE s.severity_code = 2)   AS serious_injury_crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           sum(f.persons_killed)                         AS persons_killed,
           sum(f.persons_seriously_injured)              AS persons_seriously_injured
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    GROUP BY d.year
),
lga_ranked AS (
    SELECT d.year,
           l.lga_name,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           ROW_NUMBER() OVER (PARTITION BY d.year
                              ORDER BY count(*) FILTER (WHERE s.is_fatal_or_serious) DESC, l.lga_name) AS position
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_location l USING (location_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE l.location_key <> -1
    GROUP BY d.year, l.lga_name
)
SELECT y.year,
       y.is_complete_year,
       y.crashes,
       y.fatal_crashes,
       y.serious_injury_crashes,
       y.ksi_crashes,
       y.persons_killed,
       y.persons_seriously_injured,
       round(100.0 * y.ksi_crashes / y.crashes, 1)                    AS ksi_share_pct,
       -- Year-over-year change only between complete years.
       CASE WHEN y.is_complete_year AND LAG(y.is_complete_year) OVER w
            THEN round(100.0 * (y.crashes - LAG(y.crashes) OVER w) / LAG(y.crashes) OVER w, 1) END
                                                                      AS crashes_yoy_pct,
       CASE WHEN y.is_complete_year AND LAG(y.is_complete_year) OVER w
            THEN round(100.0 * (y.ksi_crashes - LAG(y.ksi_crashes) OVER w) / LAG(y.ksi_crashes) OVER w, 1) END
                                                                      AS ksi_yoy_pct,
       r.lga_name                                                     AS top_ksi_lga,
       r.ksi_crashes                                                  AS top_ksi_lga_crashes
FROM yearly y
LEFT JOIN lga_ranked r ON r.year = y.year AND r.position = 1
WINDOW w AS (ORDER BY y.year);


-- One row per month: crashes by severity with rolling 12-month totals for trend lines.
CREATE OR REPLACE VIEW analytics.vw_crash_severity_trend AS
WITH monthly AS (
    SELECT d.year,
           d.month_number,
           d.year_month,
           make_date(d.year, d.month_number, 1)          AS month_start,
           bool_and(d.is_analysis_period)                AS is_analysis_period,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes,
           count(*) FILTER (WHERE s.severity_code = 2)   AS serious_injury_crashes,
           count(*) FILTER (WHERE s.severity_code = 3)   AS other_injury_crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    GROUP BY d.year, d.month_number, d.year_month
)
SELECT monthly.*,
       sum(crashes) OVER rolling_12     AS crashes_rolling_12m,
       sum(ksi_crashes) OVER rolling_12 AS ksi_crashes_rolling_12m,
       count(*) OVER rolling_12 = 12    AS has_full_12m_window
FROM monthly
WINDOW rolling_12 AS (ORDER BY month_start ROWS BETWEEN 11 PRECEDING AND CURRENT ROW);


-- One row per year and LGA, with share of the state and rank within the year.
-- Crashes with unknown location appear as LGA 'Unknown' so totals reconcile with the summary.
CREATE OR REPLACE VIEW analytics.vw_crashes_by_lga AS
WITH lga_region AS (
    -- Some LGAs span two DTP regions; use the region most of their locations are in.
    -- Computed from the 144k locations once, not per year from the 200k crashes: mode() needs
    -- a sort, which on the fact table spilled to disk (measured 580 ms -> 466 ms).
    SELECT lga_name, mode() WITHIN GROUP (ORDER BY dtp_region) AS dtp_region
    FROM analytics.dim_location
    GROUP BY lga_name
),
lga_year AS (
    SELECT d.year,
           bool_and(d.is_analysis_period)                AS is_complete_year,
           l.lga_name,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes,
           sum(f.persons_killed)                         AS persons_killed
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_location l USING (location_key)
    JOIN analytics.dim_severity s USING (severity_key)
    GROUP BY d.year, l.lga_name
)
SELECT lga_year.year,
       lga_year.is_complete_year,
       lga_year.lga_name,
       r.dtp_region,
       lga_year.crashes,
       lga_year.ksi_crashes,
       lga_year.fatal_crashes,
       lga_year.persons_killed,
       round(100.0 * ksi_crashes / crashes, 1)                                  AS ksi_share_pct,
       round(100.0 * crashes / sum(crashes) OVER (PARTITION BY year), 2)        AS share_of_state_pct,
       DENSE_RANK() OVER (PARTITION BY year ORDER BY lga_name = 'Unknown', crashes DESC)     AS crash_rank,
       DENSE_RANK() OVER (PARTITION BY year ORDER BY lga_name = 'Unknown', ksi_crashes DESC) AS ksi_rank
FROM lga_year
LEFT JOIN lga_region r USING (lga_name);


-- One row per year, weekday and hour: the data behind a day x hour heatmap.
-- weekdays_in_year allows a per-day rate (crashes / weekdays_in_year).
-- Aggregates on the numeric keys first and adds the text labels afterwards: grouping
-- 200k rows by several text columns was measured at 716 ms, this version at 306 ms.
CREATE OR REPLACE VIEW analytics.vw_crash_time_analysis AS
WITH counts AS (
    SELECT d.year, d.day_of_week_number, f.hour_key,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    GROUP BY d.year, d.day_of_week_number, f.hour_key
),
weekdays AS (
    SELECT year, day_of_week_number,
           min(day_name)                  AS day_name,
           bool_and(is_weekend)           AS is_weekend,
           bool_and(is_analysis_period)   AS is_complete_year,
           count(*)                       AS weekdays_in_year
    FROM analytics.dim_date
    GROUP BY year, day_of_week_number
)
SELECT c.year,
       w.is_complete_year,
       c.day_of_week_number,
       w.day_name,
       w.is_weekend,
       c.hour_key AS hour,
       t.hour_label,
       t.time_band,
       t.time_band_sort,
       c.crashes,
       c.ksi_crashes,
       c.fatal_crashes,
       w.weekdays_in_year
FROM counts c
JOIN weekdays w USING (year, day_of_week_number)
JOIN analytics.dim_time t ON t.hour_key = c.hour_key;


-- One row per year and vehicle type: how often each type is involved (fact_vehicle) and how
-- often the people travelling in it are hurt (fact_person). Pedestrians appear under the
-- 'Not applicable' vehicle type in the people columns only.
CREATE OR REPLACE VIEW analytics.vw_vehicle_crash_analysis AS
WITH involvement AS (
    SELECT d.year, fv.vehicle_type_key,
           count(*)                                      AS vehicles_involved,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS vehicles_in_ksi_crash,
           count(*) FILTER (WHERE s.is_fatal)            AS vehicles_in_fatal_crash
    FROM analytics.fact_vehicle fv
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    GROUP BY d.year, fv.vehicle_type_key
),
occupants AS (
    SELECT d.year, fp.vehicle_type_key,
           count(*)                                                AS people,
           count(*) FILTER (WHERE il.injury_level_code = 1)        AS people_killed,
           count(*) FILTER (WHERE il.injury_level_code IN (1, 2))  AS people_ksi
    FROM analytics.fact_person fp
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_injury_level il USING (injury_level_key)
    GROUP BY d.year, fp.vehicle_type_key
)
SELECT COALESCE(i.year, o.year)                       AS year,
       COALESCE(i.year, o.year) BETWEEN 2012 AND 2024 AS is_complete_year,
       vt.vehicle_category,
       vt.vehicle_type_desc,
       COALESCE(i.vehicles_involved, 0)               AS vehicles_involved,
       COALESCE(i.vehicles_in_ksi_crash, 0)           AS vehicles_in_ksi_crash,
       COALESCE(i.vehicles_in_fatal_crash, 0)         AS vehicles_in_fatal_crash,
       COALESCE(o.people, 0)                          AS people,
       COALESCE(o.people_killed, 0)                   AS people_killed,
       COALESCE(o.people_ksi, 0)                      AS people_ksi
FROM involvement i
FULL JOIN occupants o ON o.year = i.year AND o.vehicle_type_key = i.vehicle_type_key
JOIN analytics.dim_vehicle_type vt ON vt.vehicle_type_key = COALESCE(i.vehicle_type_key, o.vehicle_type_key);


-- One row per location (node) with at least one crash: totals, the last five complete years,
-- and ranks statewide and within the LGA. Read through mv_location_hotspots (02_materialized_views.sql).
CREATE OR REPLACE VIEW analytics.vw_location_hotspots AS
WITH recent AS (
    -- The five most recent complete years, e.g. 2020-2024.
    SELECT max(year) - 4 AS first_year, max(year) AS last_year
    FROM analytics.dim_date
    WHERE is_analysis_period
),
per_location AS (
    SELECT f.location_key,
           count(*)                                                     AS crashes_all_years,
           count(*) FILTER (WHERE d.year BETWEEN r.first_year AND r.last_year) AS crashes_recent,
           count(*) FILTER (WHERE d.year BETWEEN r.first_year AND r.last_year
                              AND s.is_fatal_or_serious)                AS ksi_crashes_recent,
           count(*) FILTER (WHERE d.year BETWEEN r.first_year AND r.last_year
                              AND s.is_fatal)                           AS fatal_crashes_recent,
           max(d.full_date)                                             AS last_crash_date,
           min(r.first_year)                                            AS recent_from_year,
           min(r.last_year)                                             AS recent_to_year
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    CROSS JOIN recent r
    WHERE f.location_key <> -1
    GROUP BY f.location_key
)
SELECT l.location_key,
       l.node_id,
       l.location_label,
       l.lga_name,
       l.dtp_region,
       l.node_type_desc,
       l.latitude,
       l.longitude,
       p.crashes_all_years,
       p.crashes_recent,
       p.ksi_crashes_recent,
       p.fatal_crashes_recent,
       p.last_crash_date,
       p.recent_from_year,
       p.recent_to_year,
       RANK() OVER (ORDER BY p.crashes_recent DESC, p.ksi_crashes_recent DESC)                AS state_rank_recent,
       RANK() OVER (PARTITION BY l.lga_name ORDER BY p.crashes_recent DESC, p.ksi_crashes_recent DESC) AS lga_rank_recent
FROM per_location p
JOIN analytics.dim_location l USING (location_key);
