-- Scenario: Count KSI crashes for 2012-2024 (a typical KPI card).
-- Purpose: a counter-example. It is tempting to index every foreign key, including
--          fact_crash.severity_key. But severity has only 5 values and KSI crashes are about
--          37% of rows. Reading that many rows through an index is slower than one sequential
--          scan, so PostgreSQL ignores the index: it would cost storage and write time for nothing.

SELECT count(*) AS ksi_crashes
FROM analytics.fact_crash f
JOIN analytics.dim_severity s USING (severity_key)
WHERE s.is_fatal_or_serious
  AND f.date_key BETWEEN 20120101 AND 20241231;
