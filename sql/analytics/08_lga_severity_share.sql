-- Question: Which areas have the highest share of crashes that are fatal or serious (KSI)?
-- Approach: all complete years (2012-2024) and at least 500 crashes per LGA, so the share is
--           not driven by small numbers. Compared with the statewide share.
-- Techniques: HAVING, single-row CTE joined with CROSS JOIN, mode() ordered-set aggregate,
--             percentage-point difference

WITH state AS (
    SELECT 100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*) AS ksi_share_pct
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
),
lga AS (
    SELECT l.lga_name,
           -- Some LGAs span two DTP regions; show the region most of their crashes fall in.
           mode() WITHIN GROUP (ORDER BY l.dtp_region)                        AS dtp_region,
           count(*)                                                           AS crashes,
           count(*) FILTER (WHERE s.is_fatal_or_serious)                      AS ksi_crashes,
           100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*)   AS ksi_share_pct
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_location l USING (location_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
      AND l.location_key <> -1
    GROUP BY l.lga_name
    HAVING count(*) >= 500
)
SELECT lga.lga_name,
       lga.dtp_region,
       lga.crashes,
       lga.ksi_crashes,
       round(lga.ksi_share_pct, 1)                        AS ksi_share_pct,
       round(lga.ksi_share_pct - state.ksi_share_pct, 1)  AS pp_above_state
FROM lga
CROSS JOIN state
ORDER BY lga.ksi_share_pct DESC
LIMIT 15;
