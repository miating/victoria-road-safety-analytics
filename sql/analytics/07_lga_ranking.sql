-- Question: Which LGAs had the most crashes and fatal/serious injury crashes in 2020-2024?
-- Techniques: GROUP BY, DENSE_RANK, window share of state total
-- Caveat: raw counts largely reflect population and traffic volume. The dataset has no exposure
--         measure (e.g. kilometres travelled), so a high count does not mean a road is riskier.

WITH lga_totals AS (
    SELECT l.lga_name,
           count(*)                                      AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious) AS ksi_crashes,
           count(*) FILTER (WHERE s.is_fatal)            AS fatal_crashes
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_location l USING (location_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.year BETWEEN 2020 AND 2024
      AND l.location_key <> -1
    GROUP BY l.lga_name
)
SELECT DENSE_RANK() OVER (ORDER BY crashes DESC)          AS rank,
       lga_name,
       crashes,
       round(100.0 * crashes / sum(crashes) OVER (), 1)   AS share_of_state_pct,
       ksi_crashes,
       fatal_crashes,
       round(100.0 * ksi_crashes / crashes, 1)            AS ksi_share_pct
FROM lga_totals
ORDER BY crashes DESC
LIMIT 15;
