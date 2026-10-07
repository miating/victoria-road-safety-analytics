-- Scenario: A search box finds locations by road name as the user types ("clyde...").
-- Problem: case-insensitive matching with lower() cannot use a normal index on road_name, so
--          every one of the 144,096 locations is read and lower-cased on each search.
-- Fix: expression index on lower(road_name) with text_pattern_ops. The index stores the
--      lower-cased value, and text_pattern_ops makes it usable for LIKE 'prefix%' patterns
--      (a default B-tree only supports LIKE prefixes in the C collation).

SELECT l.location_label,
       l.lga_name,
       count(f.accident_no) AS crashes
FROM analytics.dim_location l
LEFT JOIN analytics.fact_crash f USING (location_key)
WHERE lower(l.road_name) LIKE 'clyde%'
GROUP BY l.location_key, l.location_label, l.lga_name
ORDER BY crashes DESC
LIMIT 20;
