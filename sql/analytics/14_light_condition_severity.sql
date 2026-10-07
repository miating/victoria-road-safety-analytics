-- Question: Does lighting condition relate to crash severity?
-- Approach: severity by light condition, plus the share of each group's crashes in 100-110 km/h
--           zones. If dark crashes happen more often on high-speed rural roads, part of any
--           severity difference is about the road, not only the light.
-- Techniques: JOIN, GROUP BY, conditional aggregation with several FILTER conditions

SELECT lc.light_condition_desc,
       count(*)                                                                  AS crashes,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*), 1) AS ksi_share_pct,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal) / count(*), 2)           AS fatal_share_pct,
       round(100.0 * count(*) FILTER (WHERE sz.speed_limit_kmh >= 100) / count(*), 1)
                                                                                 AS in_100_110_zone_pct
FROM analytics.fact_crash f
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_light_condition lc USING (light_condition_key)
JOIN analytics.dim_speed_zone sz USING (speed_zone_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.is_analysis_period
GROUP BY lc.light_condition_key, lc.light_condition_desc
ORDER BY lc.light_condition_key;
