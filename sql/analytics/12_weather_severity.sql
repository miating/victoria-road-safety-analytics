-- Question: How does weather relate to crash severity?
-- Approach: group the 36 weather combinations into categories. A crash with several conditions
--           is assigned to the first matching category in the CASE order below.
-- Techniques: CASE WHEN, conditional aggregation, window share
-- Caveat: association only. Weather also changes who travels, where and how fast.

WITH categorised AS (
    SELECT CASE WHEN w.weather_key = -1 OR w.is_not_known THEN 'Not known'
                WHEN w.has_snow THEN 'Snow'
                WHEN w.has_fog THEN 'Fog'
                WHEN w.has_rain THEN 'Rain'
                WHEN w.has_strong_winds THEN 'Strong winds'
                WHEN w.has_smoke OR w.has_dust THEN 'Smoke or dust'
                WHEN w.has_clear THEN 'Clear'
                ELSE 'Other' END AS weather,
           s.is_fatal_or_serious,
           s.is_fatal
    FROM analytics.fact_crash f
    JOIN analytics.dim_date d USING (date_key)
    JOIN analytics.dim_weather w USING (weather_key)
    JOIN analytics.dim_severity s USING (severity_key)
    WHERE d.is_analysis_period
)
SELECT weather,
       count(*)                                                       AS crashes,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)             AS share_pct,
       round(100.0 * count(*) FILTER (WHERE is_fatal_or_serious) / count(*), 1) AS ksi_share_pct,
       round(100.0 * count(*) FILTER (WHERE is_fatal) / count(*), 2)  AS fatal_share_pct
FROM categorised
GROUP BY weather
ORDER BY crashes DESC;
