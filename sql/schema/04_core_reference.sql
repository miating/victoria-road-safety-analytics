-- Core lookup tables: one table per code set, keyed by the source code.
-- Codes stored with leading zeros in the source (e.g. vehicle type '01') stay TEXT.

CREATE TABLE IF NOT EXISTS core.ref_severity (
    severity_code SMALLINT PRIMARY KEY,
    description   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_accident_type (
    accident_type_code SMALLINT PRIMARY KEY,
    description        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_dca (
    dca_code    SMALLINT PRIMARY KEY,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_light_condition (
    light_condition_code SMALLINT PRIMARY KEY,
    description          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_road_geometry (
    road_geometry_code SMALLINT PRIMARY KEY,
    description        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_atmospheric_cond (
    atmosph_cond_code SMALLINT PRIMARY KEY,
    description       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_surface_cond (
    surface_cond_code SMALLINT PRIMARY KEY,
    description       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_sub_dca (
    sub_dca_code TEXT PRIMARY KEY,
    description  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_vehicle_type (
    vehicle_type_code TEXT PRIMARY KEY,
    description       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_road_user_type (
    road_user_type_code SMALLINT PRIMARY KEY,
    description         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS core.ref_injury_level (
    injury_level_code SMALLINT PRIMARY KEY,
    description       TEXT NOT NULL
);
