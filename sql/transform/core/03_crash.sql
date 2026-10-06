-- One row per valid crash. Rejected crashes (DQ01-DQ07) are excluded.
-- DEG_URBAN_NAME comes from the lite file because node.csv has conflicting
-- values for some crashes (DQ12); node.csv is used only when it is unambiguous.
-- Detail-row comparisons (DQ17, DQ21) use staging counts because person and
-- vehicle rows are loaded after crashes (they reference core.crash).

WITH person_rows AS (
    SELECT accident_no, count(*) AS row_count FROM staging.person GROUP BY accident_no
),
vehicle_rows AS (
    SELECT accident_no, count(*) AS row_count FROM staging.vehicle GROUP BY accident_no
),
atmospheric_crashes AS (
    SELECT DISTINCT accident_no FROM staging.atmospheric_cond
),
sub_dca_crashes AS (
    SELECT DISTINCT accident_no FROM staging.sub_dca
),
unambiguous_urban_name AS (
    SELECT accident_no, min(deg_urban_name) AS deg_urban_name
    FROM staging.node
    GROUP BY accident_no
    HAVING count(DISTINCT deg_urban_name) = 1
)
INSERT INTO core.crash (
    accident_no, crash_date, crash_time, node_id, accident_type_code, dca_code,
    light_condition_code, road_geometry_code, severity_code, speed_zone_code,
    police_attend_code, road_management_authority, deg_urban_name,
    distance_from_node_m, direction_from_node,
    vehicles_involved, persons_killed, persons_seriously_injured, persons_other_injury,
    persons_not_injured, persons_involved, dq_flags
)
SELECT a.accident_no,
       a.accident_date::DATE,
       a.accident_time::TIME,
       CASE WHEN a.node_id::INTEGER > 0 THEN a.node_id::INTEGER END,   -- DQ29
       a.accident_type::SMALLINT,
       a.dca_code::SMALLINT,
       a.light_condition::SMALLINT,
       a.road_geometry::SMALLINT,
       a.severity::SMALLINT,
       a.speed_zone,
       a.police_attend::SMALLINT,
       a.rma,
       COALESCE(l.deg_urban_name, u.deg_urban_name),
       -- -1 is a placeholder used with direction 'NK' (DQ28).
       CASE WHEN loc.distance_location ~ '^[0-9]+$' THEN loc.distance_location::INTEGER END,
       loc.direction_location,
       a.no_of_vehicles::SMALLINT,
       a.no_persons_killed::SMALLINT,
       a.no_persons_inj_2::SMALLINT,
       a.no_persons_inj_3::SMALLINT,
       a.no_persons_not_inj::SMALLINT,
       a.no_persons::SMALLINT,
       array_remove(ARRAY[
           CASE WHEN a.accident_time = '00:00:00' THEN 'DQ04' END,
           CASE WHEN a.node_id::INTEGER <= 0 THEN 'DQ29' END,
           CASE WHEN a.no_of_vehicles::INTEGER = 0 THEN 'DQ08' END,
           CASE WHEN (a.severity = '1' AND a.no_persons_killed::INTEGER = 0)
                  OR (a.severity = '2' AND a.no_persons_inj_2::INTEGER = 0) THEN 'DQ09' END,
           CASE WHEN pr.accident_no IS NULL OR vr.accident_no IS NULL OR ac.accident_no IS NULL THEN 'DQ17' END,
           CASE WHEN sc.accident_no IS NULL THEN 'DQ18' END,
           CASE WHEN pr.row_count <> a.no_persons::INTEGER
                  OR vr.row_count <> a.no_of_vehicles::INTEGER THEN 'DQ21' END
       ], NULL)
FROM staging.accident a
LEFT JOIN staging.victorian_road_crash_data l ON l.accident_no = a.accident_no
LEFT JOIN staging.accident_location loc ON loc.accident_no = a.accident_no
LEFT JOIN unambiguous_urban_name u ON u.accident_no = a.accident_no
LEFT JOIN person_rows pr ON pr.accident_no = a.accident_no
LEFT JOIN vehicle_rows vr ON vr.accident_no = a.accident_no
LEFT JOIN atmospheric_crashes ac ON ac.accident_no = a.accident_no
LEFT JOIN sub_dca_crashes sc ON sc.accident_no = a.accident_no
WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'accident' AND r.source_row_number = a.source_row_number);
