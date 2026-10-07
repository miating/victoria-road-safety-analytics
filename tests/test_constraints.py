"""The core schema must reject invalid rows by itself, independent of the ETL code.

Each test inserts into a transaction that is always rolled back, so the loaded
data is never changed.
"""

import psycopg
import pytest

pytestmark = pytest.mark.integration

CRASH_COLUMNS = (
    "accident_no, crash_date, crash_time, node_id, accident_type_code, dca_code, light_condition_code, "
    "road_geometry_code, severity_code, speed_zone_code, vehicles_involved, persons_killed, "
    "persons_seriously_injured, persons_other_injury, persons_not_injured, persons_involved"
)


def crash_values(**overrides) -> dict:
    """A valid crash row built from codes that exist in the loaded reference tables."""
    values = {
        "accident_no": "'T99990000001'", "crash_date": "'2020-01-01'", "crash_time": "'10:00'",
        "node_id": "(SELECT min(node_id) FROM core.node)", "accident_type_code": "1", "dca_code": "121",
        "light_condition_code": "1", "road_geometry_code": "1", "severity_code": "2",
        "speed_zone_code": "'060'", "vehicles_involved": "1", "persons_killed": "0",
        "persons_seriously_injured": "1", "persons_other_injury": "0", "persons_not_injured": "0",
        "persons_involved": "1",
    }
    values.update(overrides)
    return values


def insert_crash(db, **overrides) -> None:
    values = crash_values(**overrides)
    db.execute(f"INSERT INTO core.crash ({CRASH_COLUMNS}) VALUES ({', '.join(values.values())})")


def test_valid_crash_is_accepted_and_speed_limit_is_derived(rollback):
    insert_crash(rollback)
    assert rollback.execute(
        "SELECT speed_limit_kmh FROM core.crash WHERE accident_no = 'T99990000001'"
    ).fetchone()[0] == 60


def test_special_speed_code_has_no_speed_limit(rollback):
    insert_crash(rollback, speed_zone_code="'999'")
    assert rollback.execute(
        "SELECT speed_limit_kmh FROM core.crash WHERE accident_no = 'T99990000001'"
    ).fetchone()[0] is None


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"accident_no": "'BAD-ID'"}, psycopg.errors.CheckViolation),
        ({"persons_involved": "5"}, psycopg.errors.CheckViolation),
        ({"persons_killed": "-1", "persons_involved": "0"}, psycopg.errors.CheckViolation),
        ({"severity_code": "9"}, psycopg.errors.ForeignKeyViolation),
        ({"node_id": "-1"}, psycopg.errors.ForeignKeyViolation),
        ({"accident_no": "(SELECT min(accident_no) FROM core.crash)"}, psycopg.errors.UniqueViolation),
    ],
    ids=["bad-id-format", "persons-total-mismatch", "negative-count", "unknown-severity",
         "unknown-node", "duplicate-crash"],
)
def test_invalid_crash_is_rejected(rollback, overrides, error):
    with pytest.raises(error):
        insert_crash(rollback, **overrides)


def test_coordinates_outside_victoria_are_rejected(rollback):
    with pytest.raises(psycopg.errors.CheckViolation):
        rollback.execute(
            "INSERT INTO core.node (node_id, latitude, longitude, coordinate_source) VALUES (-99, 0, 145, 'node')"
        )


def test_person_cannot_reference_missing_vehicle(rollback):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        rollback.execute("""
            INSERT INTO core.person (accident_no, person_id, vehicle_id, age_group, injury_level_code, road_user_type_code)
            SELECT min(accident_no), 'ZZ', 'ZZ', '30-39', 4, 2 FROM core.crash
        """)
