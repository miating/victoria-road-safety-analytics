-- Staging layer: one table per source CSV file.
-- Every column is TEXT so files load exactly as published; typing and cleaning
-- happen when data moves into the core schema.
-- Column names are the source headers converted to snake_case.
-- source_row_number is the data line in the CSV (1 = first row after the header).

CREATE TABLE IF NOT EXISTS staging.accident (
    accident_no TEXT,
    accident_date TEXT,
    accident_time TEXT,
    accident_type TEXT,
    accident_type_desc TEXT,
    day_of_week TEXT,
    day_week_desc TEXT,
    dca_code TEXT,
    dca_desc TEXT,
    light_condition TEXT,
    node_id TEXT,
    no_of_vehicles TEXT,
    no_persons_killed TEXT,
    no_persons_inj_2 TEXT,
    no_persons_inj_3 TEXT,
    no_persons_not_inj TEXT,
    no_persons TEXT,
    police_attend TEXT,
    road_geometry TEXT,
    road_geometry_desc TEXT,
    severity TEXT,
    speed_zone TEXT,
    rma TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.accident_event (
    accident_no TEXT,
    event_seq_no TEXT,
    event_type TEXT,
    event_type_desc TEXT,
    vehicle_1_id TEXT,
    vehicle_1_coll_pt TEXT,
    vehicle_1_coll_pt_desc TEXT,
    vehicle_2_id TEXT,
    vehicle_2_coll_pt TEXT,
    vehicle_2_coll_pt_desc TEXT,
    person_id TEXT,
    object_type TEXT,
    object_type_desc TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.accident_location (
    accident_no TEXT,
    node_id TEXT,
    road_route_1 TEXT,
    road_name TEXT,
    road_type TEXT,
    road_name_int TEXT,
    road_type_int TEXT,
    distance_location TEXT,
    direction_location TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.atmospheric_cond (
    accident_no TEXT,
    atmosph_cond TEXT,
    atmosph_cond_seq TEXT,
    atmosph_cond_desc TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.node (
    accident_no TEXT,
    node_id TEXT,
    node_type TEXT,
    amg_x TEXT,
    amg_y TEXT,
    lga_name TEXT,
    lga_name_all TEXT,
    deg_urban_name TEXT,
    latitude TEXT,
    longitude TEXT,
    postcode_crash TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.person (
    accident_no TEXT,
    person_id TEXT,
    vehicle_id TEXT,
    sex TEXT,
    age_group TEXT,
    inj_level TEXT,
    inj_level_desc TEXT,
    seating_position TEXT,
    helmet_belt_worn TEXT,
    road_user_type TEXT,
    road_user_type_desc TEXT,
    licence_state TEXT,
    taken_hospital TEXT,
    ejected_code TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.road_surface_cond (
    accident_no TEXT,
    surface_cond TEXT,
    surface_cond_desc TEXT,
    surface_cond_seq TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.sub_dca (
    accident_no TEXT,
    sub_dca_code TEXT,
    sub_dca_seq TEXT,
    sub_dca_code_desc TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.vehicle (
    accident_no TEXT,
    vehicle_id TEXT,
    vehicle_year_manuf TEXT,
    vehicle_dca_code TEXT,
    initial_direction TEXT,
    road_surface_type TEXT,
    road_surface_type_desc TEXT,
    reg_state TEXT,
    vehicle_body_style TEXT,
    vehicle_make TEXT,
    vehicle_model TEXT,
    vehicle_power TEXT,
    vehicle_type TEXT,
    vehicle_type_desc TEXT,
    vehicle_weight TEXT,
    construction_type TEXT,
    fuel_type TEXT,
    no_of_wheels TEXT,
    no_of_cylinders TEXT,
    seating_capacity TEXT,
    tare_weight TEXT,
    total_no_occupants TEXT,
    carry_capacity TEXT,
    cubic_capacity TEXT,
    final_direction TEXT,
    driver_intent TEXT,
    vehicle_movement TEXT,
    trailer_type TEXT,
    vehicle_colour_1 TEXT,
    vehicle_colour_2 TEXT,
    caught_fire TEXT,
    initial_impact TEXT,
    lamps TEXT,
    level_of_damage TEXT,
    towed_away_flag TEXT,
    traffic_control TEXT,
    traffic_control_desc TEXT,
    source_row_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS staging.victorian_road_crash_data (
    accident_no TEXT,
    accident_date TEXT,
    accident_time TEXT,
    accident_type TEXT,
    day_of_week TEXT,
    dca_code TEXT,
    dca_code_description TEXT,
    light_condition TEXT,
    police_attend TEXT,
    road_geometry TEXT,
    severity TEXT,
    speed_zone TEXT,
    run_offroad TEXT,
    road_name TEXT,
    road_type TEXT,
    road_route_1 TEXT,
    lga_name TEXT,
    dtp_region TEXT,
    latitude TEXT,
    longitude TEXT,
    vicgrid_x TEXT,
    vicgrid_y TEXT,
    total_persons TEXT,
    inj_or_fatal TEXT,
    fatality TEXT,
    seriousinjury TEXT,
    otherinjury TEXT,
    noninjured TEXT,
    males TEXT,
    females TEXT,
    bicyclist TEXT,
    passenger TEXT,
    driver TEXT,
    pedestrian TEXT,
    pillion TEXT,
    motorcyclist TEXT,
    unknown TEXT,
    ped_cyclist_5_12 TEXT,
    ped_cyclist_13_18 TEXT,
    old_ped_65_and_over TEXT,
    old_driver_75_and_over TEXT,
    young_driver_18_25 TEXT,
    no_of_vehicles TEXT,
    heavyvehicle TEXT,
    passengervehicle TEXT,
    motorcycle TEXT,
    pt_vehicle TEXT,
    deg_urban_name TEXT,
    srns TEXT,
    rma TEXT,
    divided TEXT,
    stat_div_name TEXT,
    source_row_number INTEGER NOT NULL
);

