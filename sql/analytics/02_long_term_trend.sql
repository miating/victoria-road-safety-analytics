-- Question: Over 2012-2024, are crashes increasing or decreasing?
-- Approach: compare the average of the first three years with the last three years, and fit a
--           least-squares slope (change per year). Three-year averages smooth single-year noise
--           such as 2020, when COVID-19 restrictions reduced travel.
-- Techniques: CTE, unpivot with CROSS JOIN LATERAL (VALUES ...), FILTER, regr_slope

WITH yearly AS (
    SELECT d.year,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes,
           sum(f.persons_killed)                         AS persons_killed
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
    GROUP BY d.year
),
measures AS (
    SELECT y.year, m.measure, m.sort_order, m.value
    FROM yearly y
    CROSS JOIN LATERAL (VALUES
        ('Injury crashes', 1, y.crashes),
        ('Fatal or serious injury (KSI) crashes', 2, y.ksi_crashes),
        ('Fatal crashes', 3, y.fatal_crashes),
        ('Persons killed', 4, y.persons_killed)
    ) AS m(measure, sort_order, value)
)
SELECT measure,
       round(avg(value) FILTER (WHERE year BETWEEN 2012 AND 2014))   AS avg_2012_2014,
       round(avg(value) FILTER (WHERE year BETWEEN 2022 AND 2024))   AS avg_2022_2024,
       round(100.0 * (avg(value) FILTER (WHERE year BETWEEN 2022 AND 2024)
                      / avg(value) FILTER (WHERE year BETWEEN 2012 AND 2014) - 1), 1) AS change_pct,
       round(regr_slope(value, year)::NUMERIC, 1)                     AS trend_per_year
FROM measures
GROUP BY measure, sort_order
ORDER BY sort_order;
