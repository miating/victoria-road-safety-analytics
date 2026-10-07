"""Data tests on the loaded database: invariants that must hold after every ETL run.

Several tests reconcile the analytics layer with the lite file published by DTP
(victorian_road_crash_data.csv), which is an independent one-row-per-crash
summary of the same data.
"""

import pytest

pytestmark = pytest.mark.integration

DIMENSIONS_WITH_UNKNOWN = [
    ("dim_location", "location_key"),
    ("dim_severity", "severity_key"),
    ("dim_accident_type", "accident_type_key"),
    ("dim_light_condition", "light_condition_key"),
    ("dim_road_geometry", "road_geometry_key"),
    ("dim_speed_zone", "speed_zone_key"),
    ("dim_weather", "weather_key"),
    ("dim_road_surface", "road_surface_key"),
    ("dim_road_user_type", "road_user_type_key"),
    ("dim_injury_level", "injury_level_key"),
    ("dim_person_demographic", "person_demographic_key"),
    ("dim_vehicle_type", "vehicle_type_key"),
]


def scalar(db, query: str):
    return db.execute(query).fetchone()[0]


def test_latest_run_succeeded(db):
    assert scalar(db, "SELECT status FROM audit.etl_run ORDER BY run_id DESC LIMIT 1") == "succeeded"


@pytest.mark.parametrize(
    ("core_table", "fact_table"),
    [("crash", "fact_crash"), ("person", "fact_person"), ("vehicle", "fact_vehicle")],
)
def test_every_core_row_has_one_fact_row(db, core_table, fact_table):
    assert scalar(db, f"SELECT count(*) FROM core.{core_table}") == scalar(db, f"SELECT count(*) FROM analytics.{fact_table}")


def test_valid_crashes_equal_source_minus_rejected(db):
    expected = scalar(db, """
        SELECT count(*) FROM staging.accident a
        WHERE NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                          WHERE r.run_id = (SELECT max(run_id) FROM audit.etl_run WHERE status = 'succeeded')
                            AND r.source_table = 'accident' AND r.source_row_number = a.source_row_number)
    """)
    assert scalar(db, "SELECT count(*) FROM core.crash") == expected


@pytest.mark.parametrize(("dimension", "key"), DIMENSIONS_WITH_UNKNOWN)
def test_dimension_has_one_unknown_member(db, dimension, key):
    assert scalar(db, f"SELECT count(*) FROM analytics.{dimension} WHERE {key} = -1") == 1


def test_dim_date_has_no_gaps(db):
    days, span = db.execute(
        "SELECT count(*), max(full_date) - min(full_date) + 1 FROM analytics.dim_date"
    ).fetchone()
    assert days == span


def test_analysis_period_is_2012_to_2024(db):
    first, last = db.execute(
        "SELECT min(full_date), max(full_date) FROM analytics.dim_date WHERE is_analysis_period"
    ).fetchone()
    assert (first.isoformat(), last.isoformat()) == ("2012-01-01", "2024-12-31")


def test_derived_weekday_matches_source_description(db):
    # The raw DAY_OF_WEEK code is unreliable (DQ06); the weekday is derived from the date instead.
    assert scalar(db, """
        SELECT count(*) FROM analytics.fact_crash f
        JOIN analytics.dim_date d USING (date_key)
        JOIN staging.accident a USING (accident_no)
        WHERE d.day_name <> a.day_week_desc
    """) == 0


def test_fatal_crash_count_matches_lite_file(db):
    assert scalar(db, """
        SELECT count(*) FROM analytics.fact_crash JOIN analytics.dim_severity USING (severity_key)
        WHERE is_fatal
    """) == scalar(db, "SELECT count(*) FROM staging.victorian_road_crash_data WHERE severity = 'Fatal accident'")


def test_persons_killed_matches_lite_file(db):
    assert scalar(db, "SELECT sum(persons_killed) FROM analytics.fact_crash") == scalar(
        db, "SELECT sum(fatality::INTEGER) FROM staging.victorian_road_crash_data"
    )


def test_crashes_per_lga_match_lite_file(db):
    assert scalar(db, """
        SELECT count(*) FROM (
            SELECT l.lga_name, count(*) AS crashes
            FROM analytics.fact_crash f JOIN analytics.dim_location l USING (location_key)
            GROUP BY l.lga_name
        ) loaded
        FULL JOIN (
            SELECT COALESCE(lga_name, 'Unknown') AS lga_name, count(*) AS crashes
            FROM staging.victorian_road_crash_data GROUP BY 1
        ) source USING (lga_name)
        WHERE loaded.crashes IS DISTINCT FROM source.crashes
    """) == 0


def test_ksi_flag_covers_fatal_and_serious_only(db):
    rows = dict(db.execute("SELECT severity_code, is_fatal_or_serious FROM analytics.dim_severity WHERE severity_key <> -1").fetchall())
    assert rows == {1: True, 2: True, 3: False, 4: False}


def test_crashes_with_weather_rows_have_known_weather_key(db):
    assert scalar(db, """
        SELECT count(*) FROM analytics.fact_crash f
        WHERE f.weather_key = -1
          AND EXISTS (SELECT 1 FROM core.crash_atmospheric_cond c WHERE c.accident_no = f.accident_no)
    """) == 0


def test_only_pedestrians_without_vehicle_are_not_applicable(db):
    assert scalar(db, """
        SELECT count(*) FROM analytics.fact_person f
        JOIN analytics.dim_road_user_type r USING (road_user_type_key)
        WHERE f.vehicle_type_key = -2 AND r.road_user_type_desc <> 'Pedestrians'
    """) == 0


def test_placeholder_nodes_are_not_locations(db):
    # Negative NODE_IDs are "unknown location" placeholders (DQ29) and must not become a fake hotspot.
    assert scalar(db, "SELECT count(*) FROM analytics.dim_location WHERE node_id <= 0") == 0


def test_placeholder_manufacture_years_removed(db):
    assert scalar(db, "SELECT count(*) FROM core.vehicle WHERE year_manufactured IN (0, 1900)") == 0
