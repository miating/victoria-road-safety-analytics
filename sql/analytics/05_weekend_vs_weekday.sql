-- Question: Are weekend crashes different from weekday crashes - in when they happen and how
--           severe they are?
-- Techniques: CASE WHEN, GROUP BY, window share within a partition (SUM() OVER (PARTITION BY))

SELECT CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END                    AS day_type,
       t.time_band,
       count(*)                                                                    AS crashes,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY d.is_weekend), 1) AS share_of_day_type_pct,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*), 1) AS ksi_share_pct
FROM analytics.fact_crash f
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_time t USING (hour_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.is_analysis_period
GROUP BY d.is_weekend, t.time_band, t.time_band_sort
ORDER BY d.is_weekend, t.time_band_sort;
