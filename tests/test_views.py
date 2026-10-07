"""The reporting views must agree with the fact tables and with each other."""

import pytest

pytestmark = pytest.mark.integration


def scalar(db, query: str):
    return db.execute(query).fetchone()[0]


def test_summary_totals_match_fact_table(db):
    assert scalar(db, "SELECT sum(crashes) FROM analytics.vw_crash_summary") == scalar(
        db, "SELECT count(*) FROM analytics.fact_crash"
    )


@pytest.mark.parametrize(
    "view", ["vw_crash_severity_trend", "vw_crashes_by_lga", "vw_crash_time_analysis"]
)
def test_breakdown_views_reconcile_with_summary(db, view):
    assert scalar(db, f"SELECT sum(crashes) FROM analytics.{view}") == scalar(
        db, "SELECT sum(crashes) FROM analytics.vw_crash_summary"
    )


def test_vehicle_view_matches_vehicle_and_person_facts(db):
    vehicles, people = db.execute(
        "SELECT sum(vehicles_involved), sum(people) FROM analytics.vw_vehicle_crash_analysis"
    ).fetchone()
    assert vehicles == scalar(db, "SELECT count(*) FROM analytics.fact_vehicle")
    assert people == scalar(db, "SELECT count(*) FROM analytics.fact_person")


def test_yoy_change_only_between_complete_years(db):
    assert scalar(db, """
        SELECT count(*) FROM analytics.vw_crash_summary
        WHERE NOT is_complete_year AND crashes_yoy_pct IS NOT NULL
    """) == 0


def test_rolling_window_sums_twelve_months(db):
    expected = scalar(db, """
        SELECT sum(crashes) FROM analytics.vw_crash_severity_trend
        WHERE month_start BETWEEN DATE '2024-01-01' AND DATE '2024-12-01'
    """)
    assert scalar(db, """
        SELECT crashes_rolling_12m FROM analytics.vw_crash_severity_trend
        WHERE month_start = DATE '2024-12-01'
    """) == expected


def test_materialized_view_matches_its_view(db):
    # A stale materialized view would differ from the live view after a load.
    assert scalar(db, """
        SELECT count(*) FROM (
            (SELECT * FROM analytics.vw_location_hotspots EXCEPT SELECT * FROM analytics.mv_location_hotspots)
            UNION ALL
            (SELECT * FROM analytics.mv_location_hotspots EXCEPT SELECT * FROM analytics.vw_location_hotspots)
        ) differences
    """) == 0


def test_hotspots_exclude_unknown_location(db):
    assert scalar(db, "SELECT count(*) FROM analytics.mv_location_hotspots WHERE location_key = -1") == 0
