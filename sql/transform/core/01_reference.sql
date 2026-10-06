-- Rebuild the core layer from staging. Lookup tables are filled first because
-- every other core table references them.
-- A code with two different descriptions would violate the primary key and stop
-- the load, which is intended: the mapping must be one-to-one.

TRUNCATE core.person, core.vehicle, core.crash_atmospheric_cond, core.crash_surface_cond,
         core.crash_sub_dca, core.crash, core.node,
         core.ref_severity, core.ref_accident_type, core.ref_dca, core.ref_light_condition,
         core.ref_road_geometry, core.ref_atmospheric_cond, core.ref_surface_cond, core.ref_sub_dca,
         core.ref_vehicle_type, core.ref_road_user_type, core.ref_injury_level;

-- accident.csv has codes only for severity and light condition; descriptions come from the lite file.
INSERT INTO core.ref_severity (severity_code, description)
SELECT DISTINCT a.severity::SMALLINT, l.severity
FROM staging.accident a
JOIN staging.victorian_road_crash_data l ON l.accident_no = a.accident_no;

INSERT INTO core.ref_light_condition (light_condition_code, description)
SELECT DISTINCT a.light_condition::SMALLINT, l.light_condition
FROM staging.accident a
JOIN staging.victorian_road_crash_data l ON l.accident_no = a.accident_no;

INSERT INTO core.ref_accident_type (accident_type_code, description)
SELECT DISTINCT accident_type::SMALLINT, accident_type_desc FROM staging.accident;

INSERT INTO core.ref_dca (dca_code, description)
SELECT DISTINCT dca_code::SMALLINT, dca_desc FROM staging.accident;

INSERT INTO core.ref_road_geometry (road_geometry_code, description)
SELECT DISTINCT road_geometry::SMALLINT, road_geometry_desc FROM staging.accident;

INSERT INTO core.ref_atmospheric_cond (atmosph_cond_code, description)
SELECT DISTINCT atmosph_cond::SMALLINT, atmosph_cond_desc FROM staging.atmospheric_cond;

INSERT INTO core.ref_surface_cond (surface_cond_code, description)
SELECT DISTINCT surface_cond::SMALLINT, surface_cond_desc FROM staging.road_surface_cond;

INSERT INTO core.ref_sub_dca (sub_dca_code, description)
SELECT DISTINCT sub_dca_code, sub_dca_code_desc FROM staging.sub_dca;

INSERT INTO core.ref_vehicle_type (vehicle_type_code, description)
SELECT DISTINCT vehicle_type, vehicle_type_desc FROM staging.vehicle;

INSERT INTO core.ref_road_user_type (road_user_type_code, description)
SELECT DISTINCT road_user_type::SMALLINT, road_user_type_desc FROM staging.person;

INSERT INTO core.ref_injury_level (injury_level_code, description)
SELECT DISTINCT inj_level::SMALLINT, inj_level_desc FROM staging.person;
