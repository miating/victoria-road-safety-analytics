-- One row per person in a valid crash.
-- A VEHICLE_ID that does not exist in core.vehicle is set to NULL and flagged (DQ19);
-- the original value remains in staging.person.

INSERT INTO core.person (
    accident_no, person_id, vehicle_id, sex, age_group, injury_level_code, road_user_type_code,
    seating_position, helmet_belt_worn_code, licence_state, taken_to_hospital, ejected_code, dq_flags
)
SELECT p.accident_no,
       p.person_id,
       v.vehicle_id,
       p.sex,
       p.age_group,
       p.inj_level::SMALLINT,
       p.road_user_type::SMALLINT,
       p.seating_position,
       p.helmet_belt_worn::SMALLINT,
       p.licence_state,
       CASE p.taken_hospital WHEN 'Y' THEN TRUE WHEN 'N' THEN FALSE END,
       p.ejected_code::SMALLINT,
       array_remove(ARRAY[
           CASE WHEN p.vehicle_id IS NOT NULL AND v.vehicle_id IS NULL THEN 'DQ19' END,
           CASE WHEN (p.road_user_type_desc = 'Pedestrians') <> (p.vehicle_id IS NULL) THEN 'DQ20' END
       ], NULL)
FROM staging.person p
JOIN core.crash c ON c.accident_no = p.accident_no
LEFT JOIN core.vehicle v ON v.accident_no = p.accident_no AND v.vehicle_id = p.vehicle_id
WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'person' AND r.source_row_number = p.source_row_number);
