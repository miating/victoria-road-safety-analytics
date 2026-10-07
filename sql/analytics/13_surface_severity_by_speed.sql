-- Question: Are crashes on wet roads more severe than crashes on dry roads?
-- Approach: compare within the same speed band. Speed is strongly related to severity, so a
--           simple wet-vs-dry comparison could just reflect where wet-road crashes happen.
--           Stratifying by speed band reduces (but does not remove) that confounding.
-- Techniques: multi-column GROUP BY, HAVING, conditional aggregation

SELECT sz.speed_band,
       rs.surface_category                                                       AS surface,
       count(*)                                                                  AS crashes,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*), 1) AS ksi_share_pct,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal) / count(*), 2)           AS fatal_share_pct
FROM analytics.fact_crash f
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_speed_zone sz USING (speed_zone_key)
JOIN analytics.dim_road_surface rs USING (road_surface_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.is_analysis_period
GROUP BY sz.speed_band, sz.speed_band_sort, 2
HAVING count(*) >= 100
ORDER BY sz.speed_band_sort, crashes DESC;
