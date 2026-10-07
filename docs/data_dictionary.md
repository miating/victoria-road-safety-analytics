# Data Dictionary

This document describes the `analytics` schema, the star schema used by the SQL analysis, the
views and Power BI. The other layers are documented in their DDL:

| Layer | Contents | Defined in |
|---|---|---|
| `staging` | All source columns, as text | `sql/schema/03_staging.sql` |
| `core` | Cleaned relational tables | `sql/schema/04_core_reference.sql`, `sql/schema/05_core.sql` |
| `audit` | Pipeline runs, check results, rejected rows | `sql/schema/02_audit.sql` |

Row counts are from the snapshot in `data/raw/manifest.json` and include all loaded years.

## Conventions

- **`*_key`:** a surrogate key. `-1` is the **Unknown** member, and `-2` (vehicle type only) is **Not applicable** for pedestrians. Fact keys are never NULL.
- **`*_code`:** the code from the source file, kept for tracing back.
- **"Not known" vs "Unknown":**
  - "Not known" (or "Unk.") is a value recorded in the source.
  - "Unknown" (key `-1`) means the source had no value at all.
- **KSI:** a crash in which someone was killed or seriously injured.
- **Complete years:** 2012-2024. `dim_date.is_analysis_period` marks them (data quality rule DQ24).

## Fact tables

### `fact_crash`: one row per crash (200,754)

| Column | Type | Description |
|---|---|---|
| `accident_no` | text | Crash number from the source, e.g. `T20120002354` (degenerate dimension) |
| `date_key` | integer | Crash date, `YYYYMMDD` → `dim_date` |
| `hour_key` | smallint | Hour of the crash, 0-23 → `dim_time` |
| `location_key` | integer | → `dim_location`; `-1` for the 85 crashes with a placeholder node (DQ29) |
| `severity_key` | integer | → `dim_severity` |
| `accident_type_key` | integer | → `dim_accident_type` |
| `light_condition_key` | integer | → `dim_light_condition` |
| `road_geometry_key` | integer | → `dim_road_geometry` |
| `speed_zone_key` | integer | → `dim_speed_zone` |
| `weather_key` | integer | Weather combination → `dim_weather`; `-1` if the crash has no weather rows |
| `road_surface_key` | integer | Surface combination → `dim_road_surface` |
| `persons_killed` | smallint | People killed |
| `persons_seriously_injured` | smallint | People seriously injured |
| `persons_other_injury` | smallint | People with other injuries |
| `persons_not_injured` | smallint | People involved but not injured |
| `persons_involved` | smallint | Sum of the four counts above (enforced by a CHECK constraint in core) |
| `vehicles_involved` | smallint | Vehicles involved |

### `fact_person`: one row per person in a crash (467,730)

| Column | Type | Description |
|---|---|---|
| `accident_no`, `person_id` | text | Primary key. `person_id` is a letter, unique only within a crash |
| `date_key`, `location_key`, `severity_key` | integer | Same as the person's crash; severity is the crash's severity |
| `road_user_type_key` | integer | → `dim_road_user_type` |
| `injury_level_key` | integer | The person's own injury → `dim_injury_level` |
| `person_demographic_key` | integer | Age group and sex → `dim_person_demographic` |
| `vehicle_type_key` | integer | Vehicle the person was in → `dim_vehicle_type`; `-2` for pedestrians |
| `taken_to_hospital` | boolean | NULL when not recorded (65% of rows) |

### `fact_vehicle`: one row per vehicle in a crash (365,470)

| Column | Type | Description |
|---|---|---|
| `accident_no`, `vehicle_id` | text | Primary key. `vehicle_id` is a letter, unique only within a crash |
| `date_key`, `location_key`, `severity_key` | integer | Same as the vehicle's crash |
| `vehicle_type_key` | integer | → `dim_vehicle_type` |
| `occupants` | smallint | Total occupants recorded for the vehicle |
| `vehicle_age_years` | smallint | Crash year minus year of manufacture; NULL when the year is unknown (DQ22) |

## Dimensions

### `dim_date`: one row per day, 2012-01-01 to the end of the latest crash year

| Column | Description |
|---|---|
| `date_key` | `YYYYMMDD`, e.g. `20240315` |
| `full_date` | The date. Marked as the date table in Power BI |
| `year`, `quarter`, `month_number`, `month_name`, `year_month`, `day_of_month` | Calendar attributes. `year_month` is text like `2024-03` |
| `day_of_week_number`, `day_name` | ISO weekday (1 = Monday). Derived from the date, not the unreliable source code (DQ06) |
| `is_weekend`, `day_type` | Saturday/Sunday flag, and `Weekday` / `Weekend` for labels |
| `season` | Southern hemisphere: Summer = Dec-Feb, Autumn = Mar-May, Winter = Jun-Aug, Spring = Sep-Nov |
| `is_analysis_period` | True for 2012-2024 (complete years) |

### `dim_time`: one row per hour (24)

| Column | Description |
|---|---|
| `hour_key` | 0-23 |
| `hour_label` | e.g. `08:00-08:59` |
| `time_band`, `time_band_sort` | Night (00-05), Morning peak (06-09), Daytime (10-14), Afternoon peak (15-18), Evening (19-23). These bands are a project choice, not a DTP definition |

### `dim_location`: one row per location node with at least one crash (about 144k, plus Unknown)

| Column | Description |
|---|---|
| `location_key`, `node_id` | Surrogate key, and the source `NODE_ID`. Coordinates, LGA and road names are identical for every crash at a node |
| `node_type_code`, `node_type_desc` | `I` Intersection, `N` Non-intersection, `O` Other. **Inferred** from road geometry during profiling; not documented by DTP |
| `latitude`, `longitude` | WGS84. NULL if no valid coordinates in any source |
| `lga_name` | Local Government Area. Names in brackets, e.g. `(MOUNT HOTHAM)`, are unincorporated areas |
| `dtp_region` | DTP region |
| `postcode` | Postcode recorded for the crash location |
| `road_name`, `intersecting_road_name` | Road names including the road type, e.g. `PRINCES STREET` |
| `location_label` | Readable label, e.g. `CEMETERY ROAD / PRINCES STREET`. **Not unique**: several nodes can share a label, so rank by `node_id` |
| `is_unincorporated`, `has_coordinates` | Flags |

### `dim_severity`

| `severity_code` | `severity_desc` | `is_fatal` | `is_fatal_or_serious` (KSI) |
|---|---|---|---|
| 1 | Fatal accident | true | true |
| 2 | Serious injury accident | false | true |
| 3 | Other injury accident | false | false |
| 4 | Non injury accident (only 4 rows) | false | false |

### Crash attribute dimensions

| Table | Rows | Columns and notes |
|---|---|---|
| `dim_accident_type` | 9 + Unknown | `accident_type_code`, `accident_type_desc`, e.g. Collision with vehicle, Struck pedestrian |
| `dim_light_condition` | 7 + Unknown | `light_condition_desc`. `is_dark` is true for the four "Dark ..." values, false for Day and Dusk/Dawn, NULL for unknown |
| `dim_road_geometry` | 9 + Unknown | `road_geometry_desc`. `is_intersection` is true for cross, T, Y and multiple intersections |
| `dim_speed_zone` | 13 + Unknown | `speed_zone_code` as in the source, e.g. `060`. `speed_limit_kmh` is NULL for special codes 777, 888 and 999 (DQ10). `speed_band` groups: 50 km/h or less, 60-70, 75-90, 100-110, Special code / unknown |
| `dim_weather` | 36 combinations + Unknown | `weather_desc` is the combination, e.g. `Raining + Strong winds`. There is one `has_*` flag per condition. `weather_category` assigns each combination to one group: the first match in the order Snow, Fog, Rain, Strong winds, Smoke or dust, Clear |
| `dim_road_surface` | 17 combinations + Unknown | `surface_desc` is the combination. There are `has_*` flags. `surface_category` is Icy or snowy, Wet or muddy, Dry, or Not known |

### Person and vehicle dimensions

| Table | Rows | Columns and notes |
|---|---|---|
| `dim_road_user_type` | 8 + Unknown | `road_user_type_desc`: Drivers, Passengers, Motorcyclists, Pillion Passengers, Bicyclists, Pedestrians, E-scooter Rider, Not Known. Source codes 2/7 and 3/8 share a description and are merged |
| `dim_injury_level` | 4 + Unknown | Fatality, Serious injury, Other injury, Not injured |
| `dim_person_demographic` | age group x sex | `age_group` as in the source (0-4 ... 70+, Unknown), with `age_group_sort`. `sex_desc` is Male, Female, Unknown (source `U`), or Not recorded (blank) |
| `dim_vehicle_type` | 29 + Unknown + Not applicable | `vehicle_type_desc` as in the source. `vehicle_category` is a project grouping: Light passenger vehicle, Light commercial vehicle, Heavy vehicle, Bus, Motorcycle, Bicycle, Electric device, Tram / train, Other, Unknown |

## Views

Documented in [`views.md`](views.md):

- `vw_crash_summary`
- `vw_crash_severity_trend`
- `vw_crashes_by_lga`
- `vw_crash_time_analysis`
- `vw_vehicle_crash_analysis`
- `vw_location_hotspots`
- the materialized view `mv_location_hotspots`

## Source codes without official descriptions

Some source columns are codes with no description in the published files. These are kept in
`core` as codes and are not used in the analysis:

- `vehicle.fuel_type`
- `vehicle.level_of_damage`
- `person.helmet_belt_worn`
- `person.ejected_code`

The DCA codes (crash movement type) are described in `data/raw/dca_chart_and_sub_dca_codes.pdf`.
