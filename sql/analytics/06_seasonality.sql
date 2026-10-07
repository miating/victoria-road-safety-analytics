-- Question: Is there seasonality in crashes?
-- Approach: crashes per day for each calendar month (months have different lengths), as an
--           index against the overall daily average (1.00 = average day).
-- Techniques: CTEs, scalar subquery, ratio to overall average

WITH crashes_by_month AS (
    SELECT d.month_number, count(*) AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
    GROUP BY d.month_number
),
days_by_month AS (
    SELECT month_number, month_name, season, count(*) AS days
    FROM analytics.dim_date
    WHERE is_analysis_period
    GROUP BY month_number, month_name, season
)
SELECT m.month_name,
       m.season,
       round(c.crashes::NUMERIC / m.days, 1)                         AS crashes_per_day,
       round((c.crashes::NUMERIC / m.days)
             / (SELECT sum(crashes)::NUMERIC FROM crashes_by_month)
             * (SELECT sum(days) FROM days_by_month), 2)             AS index_vs_average_day,
       round(100.0 * c.ksi_crashes / c.crashes, 1)                   AS ksi_share_pct
FROM crashes_by_month c
JOIN days_by_month m USING (month_number)
ORDER BY m.month_number;
