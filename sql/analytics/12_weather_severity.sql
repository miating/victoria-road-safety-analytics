-- Question: How does weather relate to crash severity?
-- Approach: group the 36 weather combinations by dim_weather.weather_category. A crash with
--           several conditions takes the first match in a fixed order (snow, fog, rain, wind,
--           smoke/dust, clear) - defined once in sql/transform/analytics/01_dimensions.sql.
-- Techniques: conditional aggregation, window share
-- Caveat: association only. Weather also changes who travels, where and how fast.

SELECT w.weather_category                                                  AS weather,
       count(*)                                                                    AS crashes,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                          AS share_pct,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*), 1) AS ksi_share_pct,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal) / count(*), 2)             AS fatal_share_pct
FROM analytics.fact_crash f
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_weather w USING (weather_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.is_analysis_period
GROUP BY w.weather_category
ORDER BY crashes DESC;
