-- Question: Which specific locations (intersections and road nodes) had the most crashes in
--           the last five complete years (2020-2024)?
-- Techniques: GROUP BY on a location dimension, RANK, conditional aggregation
-- Note: crashes with unknown location (DQ29) are excluded so they cannot form a false hotspot.

SELECT RANK() OVER (ORDER BY count(*) DESC)               AS rank,
       l.location_label,
       l.lga_name,
       l.node_type_desc,
       count(*)                                           AS crashes,
       count(*) FILTER (WHERE s.is_fatal_or_serious)      AS ksi_crashes,
       count(*) FILTER (WHERE s.is_fatal)                 AS fatal_crashes,
       l.latitude,
       l.longitude
FROM analytics.fact_crash f
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_location l USING (location_key)
JOIN analytics.dim_severity s USING (severity_key)
WHERE d.year BETWEEN 2020 AND 2024
  AND l.location_key <> -1
GROUP BY l.location_key, l.location_label, l.lga_name, l.node_type_desc, l.latitude, l.longitude
ORDER BY crashes DESC, ksi_crashes DESC
LIMIT 20;
