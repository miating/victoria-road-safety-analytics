-- Core layer: cleaned, typed and constrained data (normalised).
-- dq_flags holds the IDs of data quality rules a row was flagged by (e.g. '{DQ08}'),
-- so flagged rows stay in the data but can be filtered: WHERE 'DQ08' = ANY(dq_flags).

CREATE TABLE IF NOT EXISTS core.node (
    node_id                INTEGER PRIMARY KEY,
    node_type              CHAR(1) CHECK (node_type IN ('I', 'N', 'O')),
    latitude               NUMERIC(9, 6) CHECK (latitude BETWEEN -39.3 AND -33.9),
    longitude              NUMERIC(9, 6) CHECK (longitude BETWEEN 140.9 AND 150.1),
    amg_x                  NUMERIC(12, 3),
    amg_y                  NUMERIC(12, 3),
    lga_name               TEXT,
    dtp_region             TEXT,
    postcode               TEXT CHECK (postcode ~ '^[0-9]{4}$'),
    road_route_1           INTEGER,
    road_name              TEXT,
    road_type              TEXT,
    intersecting_road_name TEXT,
    intersecting_road_type TEXT,
    coordinate_source      TEXT NOT NULL CHECK (coordinate_source IN ('node', 'lite', 'none')),
    is_unincorporated      BOOLEAN GENERATED ALWAYS AS (lga_name LIKE '(%') STORED,
    dq_flags               TEXT[] NOT NULL DEFAULT '{}',
    CHECK ((latitude IS NULL) = (longitude IS NULL))
);

CREATE TABLE IF NOT EXISTS core.crash (
    accident_no              TEXT PRIMARY KEY CHECK (accident_no ~ '^T[0-9]{11}$'),
    crash_date               DATE NOT NULL,
    crash_time               TIME NOT NULL,
    node_id                  INTEGER NOT NULL REFERENCES core.node (node_id),
    accident_type_code       SMALLINT NOT NULL REFERENCES core.ref_accident_type (accident_type_code),
    dca_code                 SMALLINT NOT NULL REFERENCES core.ref_dca (dca_code),
    light_condition_code     SMALLINT NOT NULL REFERENCES core.ref_light_condition (light_condition_code),
    road_geometry_code       SMALLINT NOT NULL REFERENCES core.ref_road_geometry (road_geometry_code),
    severity_code            SMALLINT NOT NULL REFERENCES core.ref_severity (severity_code),
    speed_zone_code          TEXT NOT NULL CHECK (speed_zone_code ~ '^[0-9]{3}$'),
    -- 777, 888 and 999 are special codes, not speed limits (DQ10).
    speed_limit_kmh          SMALLINT GENERATED ALWAYS AS (
                                 CASE WHEN speed_zone_code IN ('777', '888', '999') THEN NULL
                                      ELSE speed_zone_code::SMALLINT END
                             ) STORED,
    police_attend_code       SMALLINT,
    road_management_authority TEXT,
    deg_urban_name           TEXT,
    distance_from_node_m     INTEGER CHECK (distance_from_node_m >= 0),
    direction_from_node      TEXT,
    vehicles_involved        SMALLINT NOT NULL CHECK (vehicles_involved >= 0),
    persons_killed           SMALLINT NOT NULL CHECK (persons_killed >= 0),
    persons_seriously_injured SMALLINT NOT NULL CHECK (persons_seriously_injured >= 0),
    persons_other_injury     SMALLINT NOT NULL CHECK (persons_other_injury >= 0),
    persons_not_injured      SMALLINT NOT NULL CHECK (persons_not_injured >= 0),
    persons_involved         SMALLINT NOT NULL,
    dq_flags                 TEXT[] NOT NULL DEFAULT '{}',
    CHECK (persons_involved = persons_killed + persons_seriously_injured
                              + persons_other_injury + persons_not_injured)
);

CREATE TABLE IF NOT EXISTS core.vehicle (
    accident_no          TEXT NOT NULL REFERENCES core.crash (accident_no),
    vehicle_id           TEXT NOT NULL,
    vehicle_type_code    TEXT NOT NULL REFERENCES core.ref_vehicle_type (vehicle_type_code),
    year_manufactured    SMALLINT CHECK (year_manufactured BETWEEN 1900 AND 2100),
    body_style           TEXT,
    make                 TEXT,
    registration_state   TEXT,
    fuel_type_code       TEXT,
    road_surface_type    TEXT,
    traffic_control      TEXT,
    total_occupants      SMALLINT CHECK (total_occupants >= 0),
    level_of_damage_code SMALLINT,
    towed_away_code      SMALLINT,
    caught_fire_code     SMALLINT,
    dq_flags             TEXT[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (accident_no, vehicle_id)
);

CREATE TABLE IF NOT EXISTS core.person (
    accident_no            TEXT NOT NULL REFERENCES core.crash (accident_no),
    person_id              TEXT NOT NULL,
    -- NULL for pedestrians and for references to vehicles missing from vehicle.csv (DQ19).
    vehicle_id             TEXT,
    sex                    CHAR(1) CHECK (sex IN ('M', 'F', 'U')),
    age_group              TEXT NOT NULL,
    injury_level_code      SMALLINT NOT NULL REFERENCES core.ref_injury_level (injury_level_code),
    road_user_type_code    SMALLINT NOT NULL REFERENCES core.ref_road_user_type (road_user_type_code),
    seating_position       TEXT,
    helmet_belt_worn_code  SMALLINT,
    licence_state          TEXT,
    taken_to_hospital      BOOLEAN,
    ejected_code           SMALLINT,
    dq_flags               TEXT[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (accident_no, person_id),
    FOREIGN KEY (accident_no, vehicle_id) REFERENCES core.vehicle (accident_no, vehicle_id)
);

CREATE TABLE IF NOT EXISTS core.crash_atmospheric_cond (
    accident_no       TEXT NOT NULL REFERENCES core.crash (accident_no),
    atmosph_cond_code SMALLINT NOT NULL REFERENCES core.ref_atmospheric_cond (atmosph_cond_code),
    sequence_no       SMALLINT,
    PRIMARY KEY (accident_no, atmosph_cond_code)
);

CREATE TABLE IF NOT EXISTS core.crash_surface_cond (
    accident_no       TEXT NOT NULL REFERENCES core.crash (accident_no),
    surface_cond_code SMALLINT NOT NULL REFERENCES core.ref_surface_cond (surface_cond_code),
    sequence_no       SMALLINT,
    PRIMARY KEY (accident_no, surface_cond_code)
);

CREATE TABLE IF NOT EXISTS core.crash_sub_dca (
    accident_no  TEXT NOT NULL REFERENCES core.crash (accident_no),
    sub_dca_code TEXT NOT NULL REFERENCES core.ref_sub_dca (sub_dca_code),
    sequence_no  SMALLINT,
    PRIMARY KEY (accident_no, sub_dca_code)
);
