-- Question: Which hours have the most crashes, and are crashes at some hours more severe?
-- Techniques: JOIN, GROUP BY, window aggregate over the whole result (SUM() OVER ()), RANK
-- Note: reported times cluster on the hour and half hour (DQ26), so hour level is the finest
--       reliable grain.

SELECT t.hour_key                                                          AS hour,
       t.time_band,
       count(*)                                                            AS crashes,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                  AS share_pct,
       RANK() OVER (ORDER BY count(*) DESC)                                AS volume_rank,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*), 1) AS ksi_share_pct,
       RANK() OVER (ORDER BY count(*) FILTER (WHERE s.is_fatal_or_serious)::NUMERIC / count(*) DESC)
                                                                           AS severity_rank
FROM analytics.fact_crash f
JOIN analytics.dim_time t USING (hour_key)
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.is_analysis_period
GROUP BY t.hour_key, t.time_band
ORDER BY t.hour_key;
