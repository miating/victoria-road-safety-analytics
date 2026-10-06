-- One row per location node referenced by a valid crash.
-- Node attributes are identical for every crash at a node (checked during
-- profiling), so any single row per node can be used.
-- Coordinates: node.csv first, then the lite file (DQ13). Values outside the
-- Victoria bounding box are set to NULL and flagged (DQ14).

WITH valid_crash AS (
    -- Negative NODE_IDs (-1, -3, -10) are "location unknown" placeholders, not real nodes (DQ29).
    SELECT a.accident_no, a.node_id::INTEGER AS node_id
    FROM staging.accident a
    WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'accident' AND r.source_row_number = a.source_row_number)
      AND a.node_id::INTEGER > 0
),
node_file AS (
    SELECT DISTINCT ON (n.node_id::INTEGER)
           n.node_id::INTEGER AS node_id, n.node_type, n.latitude, n.longitude,
           n.amg_x, n.amg_y, n.lga_name, n.postcode_crash
    FROM staging.node n
    WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'node' AND r.source_row_number = n.source_row_number)
    ORDER BY n.node_id::INTEGER, n.source_row_number
),
lite_file AS (
    -- Prefer a crash row that has coordinates.
    SELECT DISTINCT ON (c.node_id)
           c.node_id, l.latitude, l.longitude, l.lga_name, l.dtp_region
    FROM valid_crash c
    JOIN staging.victorian_road_crash_data l ON l.accident_no = c.accident_no
    ORDER BY c.node_id, l.latitude IS NULL, l.source_row_number
),
road_names AS (
    SELECT DISTINCT ON (loc.node_id::INTEGER)
           loc.node_id::INTEGER AS node_id, loc.road_route_1, loc.road_name, loc.road_type,
           loc.road_name_int, loc.road_type_int
    FROM staging.accident_location loc
    WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'accident_location' AND r.source_row_number = loc.source_row_number)
    ORDER BY loc.node_id::INTEGER, loc.source_row_number
),
combined AS (
    SELECT c.node_id,
           nf.node_type,
           CASE WHEN nf.latitude IS NOT NULL THEN nf.latitude ELSE lf.latitude END AS latitude_text,
           CASE WHEN nf.latitude IS NOT NULL THEN nf.longitude ELSE lf.longitude END AS longitude_text,
           CASE WHEN nf.latitude IS NOT NULL THEN 'node'
                WHEN lf.latitude IS NOT NULL THEN 'lite'
                ELSE 'none' END AS coordinate_source,
           nf.amg_x, nf.amg_y,
           COALESCE(nf.lga_name, lf.lga_name) AS lga_name,
           lf.dtp_region,
           nf.postcode_crash,
           rn.road_route_1, rn.road_name, rn.road_type, rn.road_name_int, rn.road_type_int
    FROM (SELECT DISTINCT node_id FROM valid_crash) c
    LEFT JOIN node_file nf ON nf.node_id = c.node_id
    LEFT JOIN lite_file lf ON lf.node_id = c.node_id
    LEFT JOIN road_names rn ON rn.node_id = c.node_id
),
checked AS (
    SELECT *,
           -- Nested CASE so the cast only runs on values that are valid numbers.
           CASE WHEN pg_input_is_valid(latitude_text, 'numeric') AND pg_input_is_valid(longitude_text, 'numeric')
                THEN latitude_text::NUMERIC BETWEEN -39.3 AND -33.9
                     AND longitude_text::NUMERIC BETWEEN 140.9 AND 150.1
                ELSE FALSE END AS has_valid_coordinates
    FROM combined
)
INSERT INTO core.node (
    node_id, node_type, latitude, longitude, amg_x, amg_y, lga_name, dtp_region, postcode,
    road_route_1, road_name, road_type, intersecting_road_name, intersecting_road_type,
    coordinate_source, dq_flags
)
SELECT node_id,
       node_type,
       CASE WHEN has_valid_coordinates THEN latitude_text::NUMERIC END,
       CASE WHEN has_valid_coordinates THEN longitude_text::NUMERIC END,
       amg_x::NUMERIC,
       amg_y::NUMERIC,
       lga_name,
       dtp_region,
       postcode_crash,
       CASE WHEN road_route_1 ~ '^[0-9]+$' THEN road_route_1::INTEGER END,   -- -1 = unknown route
       road_name,
       road_type,
       road_name_int,
       road_type_int,
       CASE WHEN has_valid_coordinates THEN coordinate_source ELSE 'none' END,
       CASE WHEN coordinate_source = 'none' THEN ARRAY['DQ13']
            WHEN NOT has_valid_coordinates THEN ARRAY['DQ14']
            ELSE ARRAY[]::TEXT[] END
FROM checked;
