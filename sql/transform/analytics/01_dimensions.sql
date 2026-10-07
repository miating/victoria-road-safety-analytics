-- Rebuild all dimensions from core (Type 1: no history kept).
-- Key -1 = Unknown member, -2 = Not applicable. Other keys come from the identity sequence.

TRUNCATE analytics.fact_crash, analytics.fact_person, analytics.fact_vehicle,
         analytics.dim_date, analytics.dim_time, analytics.dim_location, analytics.dim_severity,
         analytics.dim_accident_type, analytics.dim_light_condition, analytics.dim_road_geometry,
         analytics.dim_speed_zone, analytics.dim_weather, analytics.dim_road_surface,
         analytics.dim_road_user_type, analytics.dim_injury_level, analytics.dim_person_demographic,
         analytics.dim_vehicle_type
RESTART IDENTITY;

-- Date: every day from 2012-01-01 to the end of the latest crash year, so there are no gaps.
-- Explicit column list: a positional INSERT breaks silently when a column is added to the table.
INSERT INTO analytics.dim_date
    (date_key, full_date, year, quarter, month_number, month_name, year_month, day_of_month,
     day_of_week_number, day_name, is_weekend, day_type, season, is_analysis_period)
SELECT to_char(d, 'YYYYMMDD')::INTEGER,
       d,
       extract(year FROM d),
       extract(quarter FROM d),
       extract(month FROM d),
       to_char(d, 'FMMonth'),
       to_char(d, 'YYYY-MM'),
       extract(day FROM d),
       extract(isodow FROM d),
       to_char(d, 'FMDay'),
       extract(isodow FROM d) IN (6, 7),
       CASE WHEN extract(isodow FROM d) IN (6, 7) THEN 'Weekend' ELSE 'Weekday' END,
       CASE WHEN extract(month FROM d) IN (12, 1, 2) THEN 'Summer'
            WHEN extract(month FROM d) IN (3, 4, 5) THEN 'Autumn'
            WHEN extract(month FROM d) IN (6, 7, 8) THEN 'Winter'
            ELSE 'Spring' END,
       d BETWEEN DATE '2012-01-01' AND DATE '2024-12-31'   -- complete years only (DQ24)
FROM generate_series(
         DATE '2012-01-01',
         (SELECT make_date(extract(year FROM max(crash_date))::INTEGER, 12, 31) FROM core.crash),
         INTERVAL '1 day'
     ) AS g(day_value)
CROSS JOIN LATERAL (SELECT g.day_value::DATE AS d) AS day_row;

INSERT INTO analytics.dim_time
SELECT h,
       lpad(h::TEXT, 2, '0') || ':00-' || lpad(h::TEXT, 2, '0') || ':59',
       band.name,
       band.sort_order
FROM generate_series(0, 23) AS h
CROSS JOIN LATERAL (
    SELECT * FROM (VALUES
        ('Night (00-05)', 1, h BETWEEN 0 AND 5),
        ('Morning peak (06-09)', 2, h BETWEEN 6 AND 9),
        ('Daytime (10-14)', 3, h BETWEEN 10 AND 14),
        ('Afternoon peak (15-18)', 4, h BETWEEN 15 AND 18),
        ('Evening (19-23)', 5, h BETWEEN 19 AND 23)
    ) AS b(name, sort_order, matches)
    WHERE b.matches
) AS band;

-- Location ---------------------------------------------------------------------
INSERT INTO analytics.dim_location
    (location_key, node_id, node_type_code, node_type_desc, latitude, longitude, lga_name, dtp_region,
     postcode, road_name, intersecting_road_name, location_label, is_unincorporated, has_coordinates)
VALUES (-1, NULL, NULL, 'Unknown', NULL, NULL, 'Unknown', 'Unknown', NULL, NULL, NULL, 'Unknown location', FALSE, FALSE);

INSERT INTO analytics.dim_location
    (node_id, node_type_code, node_type_desc, latitude, longitude, lga_name, dtp_region,
     postcode, road_name, intersecting_road_name, location_label, is_unincorporated, has_coordinates)
SELECT n.node_id,
       n.node_type,
       -- Meaning inferred from road geometry during profiling; not officially documented.
       CASE n.node_type WHEN 'I' THEN 'Intersection' WHEN 'N' THEN 'Non-intersection'
                        WHEN 'O' THEN 'Other' ELSE 'Unknown' END,
       n.latitude,
       n.longitude,
       COALESCE(n.lga_name, 'Unknown'),
       COALESCE(n.dtp_region, 'Unknown'),
       n.postcode,
       NULLIF(concat_ws(' ', n.road_name, n.road_type), ''),
       NULLIF(concat_ws(' ', n.intersecting_road_name, n.intersecting_road_type), ''),
       CASE WHEN n.road_name IS NULL THEN 'Unnamed road (node ' || n.node_id || ')'
            WHEN n.intersecting_road_name IS NULL THEN concat_ws(' ', n.road_name, n.road_type)
            ELSE concat_ws(' ', n.road_name, n.road_type) || ' / '
                 || concat_ws(' ', n.intersecting_road_name, n.intersecting_road_type) END,
       COALESCE(n.is_unincorporated, FALSE),
       n.latitude IS NOT NULL
FROM core.node n;

-- Crash attributes -------------------------------------------------------------
INSERT INTO analytics.dim_severity
    (severity_key, severity_code, severity_desc, is_fatal, is_fatal_or_serious, sort_order)
VALUES (-1, NULL, 'Unknown', FALSE, FALSE, 99);

INSERT INTO analytics.dim_severity (severity_code, severity_desc, is_fatal, is_fatal_or_serious, sort_order)
SELECT severity_code, description, severity_code = 1, severity_code IN (1, 2), severity_code
FROM core.ref_severity
ORDER BY severity_code;

INSERT INTO analytics.dim_accident_type (accident_type_key, accident_type_code, accident_type_desc)
VALUES (-1, NULL, 'Unknown');

INSERT INTO analytics.dim_accident_type (accident_type_code, accident_type_desc)
SELECT accident_type_code, description FROM core.ref_accident_type ORDER BY accident_type_code;

INSERT INTO analytics.dim_light_condition (light_condition_key, light_condition_code, light_condition_desc, is_dark)
VALUES (-1, NULL, 'Unknown', NULL);

-- Codes 3-6 are the "Dark ..." conditions; 1 = Day, 2 = Dusk/Dawn; 9 = unknown.
INSERT INTO analytics.dim_light_condition (light_condition_code, light_condition_desc, is_dark)
SELECT light_condition_code, description,
       CASE WHEN light_condition_code IN (3, 4, 5, 6) THEN TRUE
            WHEN light_condition_code IN (1, 2) THEN FALSE END
FROM core.ref_light_condition
ORDER BY light_condition_code;

INSERT INTO analytics.dim_road_geometry (road_geometry_key, road_geometry_code, road_geometry_desc, is_intersection)
VALUES (-1, NULL, 'Unknown', NULL);

-- Codes 1-4 are cross, T, Y and multiple intersections; 9 = unknown.
INSERT INTO analytics.dim_road_geometry (road_geometry_code, road_geometry_desc, is_intersection)
SELECT road_geometry_code, description,
       CASE WHEN road_geometry_code IN (1, 2, 3, 4) THEN TRUE
            WHEN road_geometry_code IN (5, 6, 7, 8) THEN FALSE END
FROM core.ref_road_geometry
ORDER BY road_geometry_code;

INSERT INTO analytics.dim_speed_zone
    (speed_zone_key, speed_zone_code, speed_zone_desc, speed_limit_kmh, speed_band, speed_band_sort)
VALUES (-1, NULL, 'Unknown', NULL, 'Special code / unknown', 5);

INSERT INTO analytics.dim_speed_zone (speed_zone_code, speed_zone_desc, speed_limit_kmh, speed_band, speed_band_sort)
SELECT speed_zone_code,
       CASE WHEN speed_limit_kmh IS NULL THEN 'Special code ' || speed_zone_code
            ELSE speed_limit_kmh || ' km/h' END,
       speed_limit_kmh,
       CASE WHEN speed_limit_kmh <= 50 THEN '50 km/h or less'
            WHEN speed_limit_kmh <= 70 THEN '60-70 km/h'
            WHEN speed_limit_kmh <= 90 THEN '75-90 km/h'
            WHEN speed_limit_kmh IS NOT NULL THEN '100-110 km/h'
            ELSE 'Special code / unknown' END,
       CASE WHEN speed_limit_kmh <= 50 THEN 1
            WHEN speed_limit_kmh <= 70 THEN 2
            WHEN speed_limit_kmh <= 90 THEN 3
            WHEN speed_limit_kmh IS NOT NULL THEN 4
            ELSE 5 END
FROM (SELECT DISTINCT speed_zone_code, speed_limit_kmh FROM core.crash) AS zones
ORDER BY speed_zone_code;

-- Weather and road surface: one dimension row per observed combination ---------
-- The per-crash combinations are kept in temporary tables for the fact load.
CREATE TEMP TABLE tmp_crash_weather ON COMMIT DROP AS
SELECT c.accident_no,
       string_agg(r.description, ' + ' ORDER BY r.description) AS weather_desc,
       count(*) AS condition_count
FROM core.crash_atmospheric_cond c
JOIN core.ref_atmospheric_cond r ON r.atmosph_cond_code = c.atmosph_cond_code
GROUP BY c.accident_no;

CREATE TEMP TABLE tmp_crash_surface ON COMMIT DROP AS
SELECT c.accident_no,
       string_agg(r.description, ' + ' ORDER BY r.description) AS surface_desc,
       count(*) AS condition_count
FROM core.crash_surface_cond c
JOIN core.ref_surface_cond r ON r.surface_cond_code = c.surface_cond_code
GROUP BY c.accident_no;

INSERT INTO analytics.dim_weather
    (weather_key, weather_desc, condition_count, has_clear, has_rain, has_snow, has_fog,
     has_smoke, has_dust, has_strong_winds, is_not_known, weather_category)
VALUES (-1, 'Unknown', 0, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, 'Not known');

-- weather_category gives each combination one reporting group. A crash with several
-- conditions takes the first match in this order (e.g. 'Fog + Raining' is Fog).
INSERT INTO analytics.dim_weather
    (weather_desc, condition_count, has_clear, has_rain, has_snow, has_fog,
     has_smoke, has_dust, has_strong_winds, is_not_known, weather_category)
SELECT flags.*,
       CASE WHEN is_not_known THEN 'Not known'
            WHEN has_snow THEN 'Snow'
            WHEN has_fog THEN 'Fog'
            WHEN has_rain THEN 'Rain'
            WHEN has_strong_winds THEN 'Strong winds'
            WHEN has_smoke OR has_dust THEN 'Smoke or dust'
            WHEN has_clear THEN 'Clear'
            ELSE 'Other' END
FROM (
    SELECT DISTINCT weather_desc, condition_count,
           weather_desc LIKE '%Clear%'        AS has_clear,
           weather_desc LIKE '%Raining%'      AS has_rain,
           weather_desc LIKE '%Snowing%'      AS has_snow,
           weather_desc LIKE '%Fog%'          AS has_fog,
           weather_desc LIKE '%Smoke%'        AS has_smoke,
           weather_desc LIKE '%Dust%'         AS has_dust,
           weather_desc LIKE '%Strong winds%' AS has_strong_winds,
           weather_desc LIKE '%Not known%'    AS is_not_known
    FROM tmp_crash_weather
) AS flags
ORDER BY weather_desc;

INSERT INTO analytics.dim_road_surface
    (road_surface_key, surface_desc, condition_count, has_dry, has_wet, has_muddy, has_icy, has_snowy,
     is_not_known, surface_category)
VALUES (-1, 'Unknown', 0, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, 'Not known');

INSERT INTO analytics.dim_road_surface
    (surface_desc, condition_count, has_dry, has_wet, has_muddy, has_icy, has_snowy, is_not_known,
     surface_category)
SELECT flags.*,
       CASE WHEN is_not_known THEN 'Not known'
            WHEN has_icy OR has_snowy THEN 'Icy or snowy'
            WHEN has_wet OR has_muddy THEN 'Wet or muddy'
            WHEN has_dry THEN 'Dry'
            ELSE 'Other' END
FROM (
    SELECT DISTINCT surface_desc, condition_count,
           surface_desc LIKE '%Dry%'   AS has_dry,
           surface_desc LIKE '%Wet%'   AS has_wet,
           surface_desc LIKE '%Muddy%' AS has_muddy,
           surface_desc LIKE '%Icy%'   AS has_icy,
           surface_desc LIKE '%Snowy%' AS has_snowy,
           surface_desc LIKE '%Unk.%'  AS is_not_known
    FROM tmp_crash_surface
) AS flags
ORDER BY surface_desc;

-- People and vehicles ----------------------------------------------------------
INSERT INTO analytics.dim_road_user_type (road_user_type_key, road_user_type_desc, sort_order)
VALUES (-1, 'Unknown', 99);

-- Source codes 2/7 (Drivers) and 3/8 (Passengers) share a description and are merged.
INSERT INTO analytics.dim_road_user_type (road_user_type_desc, sort_order)
SELECT description, min(road_user_type_code)
FROM core.ref_road_user_type
GROUP BY description
ORDER BY min(road_user_type_code);

INSERT INTO analytics.dim_injury_level (injury_level_key, injury_level_code, injury_level_desc, sort_order)
VALUES (-1, NULL, 'Unknown', 99);

INSERT INTO analytics.dim_injury_level (injury_level_code, injury_level_desc, sort_order)
SELECT injury_level_code, description, injury_level_code
FROM core.ref_injury_level
ORDER BY injury_level_code;

INSERT INTO analytics.dim_person_demographic
    (person_demographic_key, age_group, age_group_sort, sex_code, sex_desc)
VALUES (-1, 'Unknown', 999, NULL, 'Unknown');

INSERT INTO analytics.dim_person_demographic (age_group, age_group_sort, sex_code, sex_desc)
SELECT age_group,
       CASE WHEN age_group ~ '^[0-9]' THEN substring(age_group FROM '^[0-9]+')::SMALLINT ELSE 998 END,
       sex,
       CASE sex WHEN 'M' THEN 'Male' WHEN 'F' THEN 'Female' WHEN 'U' THEN 'Unknown' ELSE 'Not recorded' END
FROM (SELECT DISTINCT age_group, sex FROM core.person) AS combinations
ORDER BY 2, 3;

INSERT INTO analytics.dim_vehicle_type (vehicle_type_key, vehicle_type_code, vehicle_type_desc, vehicle_category)
VALUES (-1, NULL, 'Unknown', 'Unknown'),
       (-2, NULL, 'Not applicable (pedestrian)', 'Not applicable');

INSERT INTO analytics.dim_vehicle_type (vehicle_type_code, vehicle_type_desc, vehicle_category)
SELECT vehicle_type_code,
       description,
       CASE WHEN vehicle_type_code IN ('01', '02', '03') THEN 'Light passenger vehicle'
            WHEN vehicle_type_code IN ('04', '05', '71') THEN 'Light commercial vehicle'
            WHEN vehicle_type_code IN ('06', '07', '60', '61', '62', '63', '72') THEN 'Heavy vehicle'
            WHEN vehicle_type_code IN ('08', '09') THEN 'Bus'
            WHEN vehicle_type_code IN ('10', '11', '12') THEN 'Motorcycle'
            WHEN vehicle_type_code = '13' THEN 'Bicycle'
            WHEN vehicle_type_code = '21' THEN 'Electric device'
            WHEN vehicle_type_code IN ('15', '16') THEN 'Tram / train'
            WHEN vehicle_type_code IN ('18', '99') THEN 'Unknown'
            ELSE 'Other' END
FROM core.ref_vehicle_type
ORDER BY vehicle_type_code;
