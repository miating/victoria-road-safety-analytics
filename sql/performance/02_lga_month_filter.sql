-- Scenario: Dashboard filtered to one LGA and one year: monthly KSI crashes in Casey, 2024.
-- Problem: finding Casey's 6,077 locations scans all 144,096 rows of dim_location, and the
--          matching facts are found by scanning the whole fact table.
-- Fix: B-tree index on dim_location (lga_name), plus the composite fact index. The benchmark
--      compares both column orders of the composite index to show why order matters.

SELECT d.year_month,
       count(*)                                      AS crashes,
       count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes
FROM analytics.fact_crash f
JOIN analytics.dim_location l USING (location_key)
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE l.lga_name = 'CASEY'
  AND f.date_key BETWEEN 20240101 AND 20241231
GROUP BY d.year_month
ORDER BY d.year_month;
