-- Question: Which days of the week have the most crashes, and the most severe crashes?
-- Approach: divide by the number of each weekday in the period, so every day is compared on a
--           per-day basis.
-- Techniques: two CTEs joined together, conditional aggregation, ratio calculation

WITH days_in_period AS (
    SELECT day_of_week_number, count(*) AS days
    FROM analytics.dim_date
    WHERE is_analysis_period
    GROUP BY day_of_week_number
),
crashes_by_day AS (
    SELECT d.day_of_week_number,
           d.day_name,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
    GROUP BY d.day_of_week_number, d.day_name
)
SELECT c.day_name,
       c.crashes,
       round(c.crashes::NUMERIC / p.days, 1)        AS crashes_per_day,
       round(c.ksi_crashes::NUMERIC / p.days, 1)    AS ksi_crashes_per_day,
       round(100.0 * c.ksi_crashes / c.crashes, 1)  AS ksi_share_pct,
       round(100.0 * c.fatal_crashes / c.crashes, 2) AS fatal_share_pct
FROM crashes_by_day c
JOIN days_in_period p USING (day_of_week_number)
ORDER BY c.day_of_week_number;
