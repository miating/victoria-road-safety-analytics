-- The five locations with the most crashes in one LGA and year.
-- Parameters (ODBC placeholders, in order): 1 = LGA name, 2 = report year.
WITH params AS (
    SELECT CAST(? AS text) AS lga, CAST(? AS integer) AS report_year
)
SELECT l.node_id,
       l.location_label,
       count(*)                                         AS crashes,
       count(*) FILTER (WHERE s.is_fatal_or_serious)    AS ksi_crashes
FROM analytics.fact_crash f
JOIN analytics.dim_date d USING (date_key)
JOIN analytics.dim_location l USING (location_key)
JOIN analytics.dim_severity s USING (severity_key)
CROSS JOIN params p
WHERE CASE WHEN l.lga_name = 'MORELAND' THEN 'MERRI-BEK' ELSE l.lga_name END = p.lga
  AND d.year = p.report_year
  AND l.has_coordinates
GROUP BY l.node_id, l.location_label
ORDER BY crashes DESC, ksi_crashes DESC, l.node_id   -- node_id breaks ties so the list is reproducible
LIMIT 5;
