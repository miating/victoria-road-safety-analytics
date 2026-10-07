-- Scenario: A dashboard user clicks a hotspot on the map and sees every crash at that location.
--           Node 36335 is Cemetery Road / Princes Street, Melbourne (75 crashes since 2012).
-- Problem: about 75 of 200,754 fact rows are needed, but without an index on location_key
--          PostgreSQL must read the whole fact table (sequential scan) to find them.
-- Fix: B-tree index on fact_crash (location_key, date_key). Its leading column serves this
--      equality lookup; the second column also helps location + date filters (see 02).

SELECT d.full_date,
       t.hour_label,
       s.severity_desc,
       f.persons_killed,
       f.persons_seriously_injured,
       f.vehicles_involved
FROM analytics.fact_crash f
JOIN analytics.dim_location l USING (location_key)
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_time t USING (hour_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE l.node_id = 36335
ORDER BY d.full_date DESC;
