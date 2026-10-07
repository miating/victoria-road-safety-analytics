-- Question: How have injury crashes, and fatal and serious injury crashes, changed by year?
-- Techniques: JOIN, GROUP BY, conditional aggregation (FILTER), CTE, LAG over a named WINDOW
-- Note: complete years 2012-2024 only (dim_date.is_analysis_period).

WITH yearly AS (
    SELECT d.year,
           count(*)                                         AS crashes,
           count(*) FILTER (WHERE s.is_fatal)               AS fatal_crashes,
           count(*) FILTER (WHERE s.severity_code = 2)      AS serious_injury_crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious)    AS ksi_crashes,
           sum(f.persons_killed)                            AS persons_killed
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
    GROUP BY d.year
)
SELECT year,
       crashes,
       round(100.0 * (crashes - LAG(crashes) OVER w) / LAG(crashes) OVER w, 1) AS crashes_change_pct,
       fatal_crashes,
       serious_injury_crashes,
       persons_killed,
       round(100.0 * ksi_crashes / crashes, 1)                                  AS ksi_share_pct
FROM yearly
WINDOW w AS (ORDER BY year)
ORDER BY year;
