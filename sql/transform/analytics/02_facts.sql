-- Load the three fact tables. Every dimension lookup falls back to the Unknown
-- member (-1), so fact foreign keys are never NULL and no row is lost in joins.

INSERT INTO analytics.fact_crash
SELECT c.accident_no,
       to_char(c.crash_date, 'YYYYMMDD')::INTEGER,
       extract(hour FROM c.crash_time)::SMALLINT,
       COALESCE(dl.location_key, -1),
       COALESCE(ds.severity_key, -1),
       COALESCE(dat.accident_type_key, -1),
       COALESCE(dlc.light_condition_key, -1),
       COALESCE(drg.road_geometry_key, -1),
       COALESCE(dsz.speed_zone_key, -1),
       COALESCE(dw.weather_key, -1),
       COALESCE(drs.road_surface_key, -1),
       c.persons_killed,
       c.persons_seriously_injured,
       c.persons_other_injury,
       c.persons_not_injured,
       c.persons_involved,
       c.vehicles_involved
FROM core.crash c
LEFT JOIN analytics.dim_location dl ON dl.node_id = c.node_id
LEFT JOIN analytics.dim_severity ds ON ds.severity_code = c.severity_code
LEFT JOIN analytics.dim_accident_type dat ON dat.accident_type_code = c.accident_type_code
LEFT JOIN analytics.dim_light_condition dlc ON dlc.light_condition_code = c.light_condition_code
LEFT JOIN analytics.dim_road_geometry drg ON drg.road_geometry_code = c.road_geometry_code
LEFT JOIN analytics.dim_speed_zone dsz ON dsz.speed_zone_code = c.speed_zone_code
LEFT JOIN tmp_crash_weather tw ON tw.accident_no = c.accident_no
LEFT JOIN analytics.dim_weather dw ON dw.weather_desc = tw.weather_desc
LEFT JOIN tmp_crash_surface ts ON ts.accident_no = c.accident_no
LEFT JOIN analytics.dim_road_surface drs ON drs.surface_desc = ts.surface_desc;

INSERT INTO analytics.fact_vehicle
SELECT v.accident_no,
       v.vehicle_id,
       to_char(c.crash_date, 'YYYYMMDD')::INTEGER,
       COALESCE(dl.location_key, -1),
       COALESCE(ds.severity_key, -1),
       COALESCE(dvt.vehicle_type_key, -1),
       v.total_occupants,
       -- A vehicle can be a newer model year than the crash year; treat as age 0.
       -- The CASE matters: GREATEST ignores NULLs, so unknown years would become 0.
       CASE WHEN v.year_manufactured IS NOT NULL
            THEN GREATEST(extract(year FROM c.crash_date)::SMALLINT - v.year_manufactured, 0) END
FROM core.vehicle v
JOIN core.crash c ON c.accident_no = v.accident_no
LEFT JOIN analytics.dim_location dl ON dl.node_id = c.node_id
LEFT JOIN analytics.dim_severity ds ON ds.severity_code = c.severity_code
LEFT JOIN analytics.dim_vehicle_type dvt ON dvt.vehicle_type_code = v.vehicle_type_code;

INSERT INTO analytics.fact_person
SELECT p.accident_no,
       p.person_id,
       to_char(c.crash_date, 'YYYYMMDD')::INTEGER,
       COALESCE(dl.location_key, -1),
       COALESCE(ds.severity_key, -1),
       COALESCE(drut.road_user_type_key, -1),
       COALESCE(dil.injury_level_key, -1),
       COALESCE(dpd.person_demographic_key, -1),
       CASE WHEN p.vehicle_id IS NULL AND rut.description = 'Pedestrians' THEN -2
            ELSE COALESCE(dvt.vehicle_type_key, -1) END,
       p.taken_to_hospital
FROM core.person p
JOIN core.crash c ON c.accident_no = p.accident_no
JOIN core.ref_road_user_type rut ON rut.road_user_type_code = p.road_user_type_code
LEFT JOIN core.vehicle v ON v.accident_no = p.accident_no AND v.vehicle_id = p.vehicle_id
LEFT JOIN analytics.dim_location dl ON dl.node_id = c.node_id
LEFT JOIN analytics.dim_severity ds ON ds.severity_code = c.severity_code
LEFT JOIN analytics.dim_road_user_type drut ON drut.road_user_type_desc = rut.description
LEFT JOIN analytics.dim_injury_level dil ON dil.injury_level_code = p.injury_level_code
LEFT JOIN analytics.dim_person_demographic dpd
       ON dpd.age_group = p.age_group
      AND dpd.sex_code IS NOT DISTINCT FROM p.sex
      AND dpd.person_demographic_key <> -1     -- the Unknown member also has a NULL sex_code
LEFT JOIN analytics.dim_vehicle_type dvt ON dvt.vehicle_type_code = v.vehicle_type_code;
