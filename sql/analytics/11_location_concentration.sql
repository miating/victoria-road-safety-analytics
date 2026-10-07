-- Question: How concentrated are crashes? What share of crashes happened at the most crash-prone
--           1%, 5%, 10% and 25% of locations (2012-2024)?
-- Techniques: CTEs, ROW_NUMBER, running total (SUM() OVER ... ROWS UNBOUNDED PRECEDING),
--             whole-set window aggregates, CROSS JOIN with VALUES
-- Note: "locations" means nodes with at least one recorded injury crash; locations with no
--       crashes are not in the data, so the true concentration across all roads is higher.

WITH crashes_per_location AS (
    SELECT f.location_key, count(*) AS crashes
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    WHERE d.is_analysis_period
      AND f.location_key <> -1
    GROUP BY f.location_key
),
ranked AS (
    SELECT crashes,
           ROW_NUMBER() OVER (ORDER BY crashes DESC, location_key)                  AS location_rank,
           count(*) OVER ()                                                          AS total_locations,
           sum(crashes) OVER (ORDER BY crashes DESC, location_key ROWS UNBOUNDED PRECEDING) AS cumulative_crashes,
           sum(crashes) OVER ()                                                      AS total_crashes
    FROM crashes_per_location
)
SELECT p.top_pct                                                        AS top_pct_of_locations,
       max(r.location_rank)                                             AS locations,
       max(r.cumulative_crashes)                                        AS crashes,
       round(100.0 * max(r.cumulative_crashes) / max(r.total_crashes), 1) AS share_of_crashes_pct
FROM ranked r
CROSS JOIN (VALUES (1), (5), (10), (25)) AS p(top_pct)
WHERE r.location_rank <= ceil(r.total_locations * p.top_pct / 100.0)
GROUP BY p.top_pct
ORDER BY p.top_pct;
