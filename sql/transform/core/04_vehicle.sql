-- One row per vehicle in a valid crash. VEHICLE_POWER is not loaded (100% empty).
-- Year of manufacture 0 or in the future becomes NULL (DQ22).

INSERT INTO core.vehicle (
    accident_no, vehicle_id, vehicle_type_code, year_manufactured, body_style, make,
    registration_state, fuel_type_code, road_surface_type, traffic_control, total_occupants,
    level_of_damage_code, towed_away_code, caught_fire_code
)
SELECT v.accident_no,
       v.vehicle_id,
       v.vehicle_type,
       CASE WHEN v.vehicle_year_manuf ~ '^[0-9]{4}$'
             AND v.vehicle_year_manuf::INTEGER BETWEEN 1900 AND extract(year FROM current_date)
            THEN v.vehicle_year_manuf::SMALLINT END,
       v.vehicle_body_style,
       v.vehicle_make,
       v.reg_state,
       v.fuel_type,
       v.road_surface_type_desc,
       v.traffic_control_desc,
       v.total_no_occupants::SMALLINT,
       v.level_of_damage::SMALLINT,
       v.towed_away_flag::SMALLINT,
       v.caught_fire::SMALLINT
FROM staging.vehicle v
JOIN core.crash c ON c.accident_no = v.accident_no
WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'vehicle' AND r.source_row_number = v.source_row_number);
