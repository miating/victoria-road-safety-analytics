-- Question: Which vehicle types are most often involved in crashes, and how often is their
--           crash a fatal or serious one?
-- Grain: one row per vehicle in a crash (fact_vehicle).
-- Caveat: severity is a property of the crash. A car that hits a pedestrian counts as a car in a
--         KSI crash even if nobody in the car was hurt. Involvement does not mean fault.
-- Techniques: GROUP BY, window share, RANK on a calculated rate, HAVING

SELECT vt.vehicle_category,
       count(*)                                                                    AS vehicles_involved,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)                          AS share_pct,
       round(100.0 * count(*) FILTER (WHERE s.is_fatal_or_serious) / count(*), 1) AS in_ksi_crash_pct,
       round(1000.0 * count(*) FILTER (WHERE s.is_fatal) / count(*), 1)            AS in_fatal_crash_per_1000,
       RANK() OVER (ORDER BY count(*) FILTER (WHERE s.is_fatal_or_serious)::NUMERIC / count(*) DESC)
                                                                                   AS ksi_rank
FROM analytics.fact_vehicle fv
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_vehicle_type vt USING (vehicle_type_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.is_analysis_period
GROUP BY vt.vehicle_category
HAVING count(*) >= 100
ORDER BY vehicles_involved DESC;
