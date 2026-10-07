"""Generate docs/data_quality_report.md from the audit tables of an ETL run.

The pipeline calls this after every successful run. It can also be run on its own:
    python -m src.validation.report            # latest successful run
    python -m src.validation.report --run-id 3
"""

import argparse
import logging
from pathlib import Path

import psycopg

from src.utils.db import get_connection

REPORT_PATH = Path(__file__).resolve().parents[2] / "docs" / "data_quality_report.md"

# Source file -> core table it is loaded into.
SOURCE_TO_CORE = {
    "accident": "crash",
    "person": "person",
    "vehicle": "vehicle",
    "node": "node",
    "atmospheric_cond": "crash_atmospheric_cond",
    "road_surface_cond": "crash_surface_cond",
    "sub_dca": "crash_sub_dca",
}

# Fields analysts rely on, and how "missing" is defined for each in the analytics layer.
MISSING_VALUE_CHECKS = {
    "Crash location (no node / coordinates)": "SELECT count(*) FROM analytics.fact_crash WHERE location_key = -1",
    "Crash weather (no atmospheric rows)": "SELECT count(*) FROM analytics.fact_crash WHERE weather_key = -1",
    "Crash weather recorded as 'Not known'": """
        SELECT count(*) FROM analytics.fact_crash f JOIN analytics.dim_weather w USING (weather_key)
        WHERE w.weather_key <> -1 AND w.is_not_known""",
    "Crash road surface recorded as 'Unk.'": """
        SELECT count(*) FROM analytics.fact_crash f JOIN analytics.dim_road_surface s USING (road_surface_key)
        WHERE s.road_surface_key <> -1 AND s.is_not_known""",
    "Crash speed limit (special code)": "SELECT count(*) FROM core.crash WHERE speed_limit_kmh IS NULL",
    "Person age group 'Unknown'": "SELECT count(*) FROM core.person WHERE age_group = 'Unknown'",
    "Person sex unknown or blank": "SELECT count(*) FROM core.person WHERE sex IS NULL OR sex = 'U'",
    "Vehicle year of manufacture": "SELECT count(*) FROM core.vehicle WHERE year_manufactured IS NULL",
}
MISSING_VALUE_TOTALS = {"Crash": "core.crash", "Person": "core.person", "Vehicle": "core.vehicle"}

logger = logging.getLogger(__name__)


def scalar(connection: psycopg.Connection, query: str, params: tuple = ()) -> int:
    return connection.execute(query, params).fetchone()[0]


def latest_successful_run(connection: psycopg.Connection) -> int:
    run_id = scalar(connection, "SELECT max(run_id) FROM audit.etl_run WHERE status = 'succeeded'")
    if run_id is None:
        raise RuntimeError("No successful ETL run found - run python -m src.pipeline first")
    return run_id


def failed_rows(connection: psycopg.Connection, run_id: int, rule_ids: list[str], table: str | None = None) -> int:
    query = "SELECT COALESCE(sum(rows_failed), 0) FROM audit.dq_check_result WHERE run_id = %s AND rule_id = ANY(%s)"
    params: tuple = (run_id, rule_ids)
    if table:
        query += " AND table_name = %s"
        params += (table,)
    return scalar(connection, query, params)


def markdown_table(headers: list[str], rows: list[list]) -> list[str]:
    def cell(value) -> str:
        return f"{value:,}" if isinstance(value, int) else str(value)

    return [
        "| " + " | ".join(headers) + " |",
        "|" + "---|" * len(headers),
        *("| " + " | ".join(cell(v) for v in row) + " |" for row in rows),
    ]


def run_section(connection: psycopg.Connection, run_id: int) -> list[str]:
    started, finished, status = connection.execute(
        "SELECT started_at, finished_at, status FROM audit.etl_run WHERE run_id = %s", (run_id,)
    ).fetchone()
    duration = (finished - started).total_seconds() if finished else None
    return [
        f"- ETL run: **{run_id}** ({status})",
        f"- Started: {started:%Y-%m-%d %H:%M:%S %Z}",
        f"- Duration: {duration:.0f} seconds" if duration is not None else "- Duration: n/a",
        "",
    ]


def summary_section(connection: psycopg.Connection, run_id: int) -> list[str]:
    total = scalar(connection, "SELECT count(*) FROM staging.accident")
    rejected = scalar(
        connection,
        "SELECT count(DISTINCT source_row_number) FROM audit.rejected_record WHERE run_id = %s AND source_table = 'accident'",
        (run_id,),
    )
    rows = [
        ["Total crash records", total],
        ["Valid crash records (loaded)", scalar(connection, "SELECT count(*) FROM core.crash")],
        ["Rejected crash records", rejected],
        ["Rejected records, all files", scalar(connection, "SELECT count(*) FROM audit.rejected_record WHERE run_id = %s", (run_id,))],
        ["Duplicate rows (exact duplicates in node.csv, DQ11)", failed_rows(connection, run_id, ["DQ11"])],
        ["Duplicate keys (DQ01, DQ27)", failed_rows(connection, run_id, ["DQ01", "DQ27"])],
        ["Invalid coordinates (DQ14)", failed_rows(connection, run_id, ["DQ14"], "staging.node")
                                       + failed_rows(connection, run_id, ["DQ14"], "staging.victorian_road_crash_data")],
        ["Crashes with unknown location (DQ29)", failed_rows(connection, run_id, ["DQ29"], "core.crash")],
        ["Crashes with at least one data quality flag",
         scalar(connection, "SELECT count(*) FROM core.crash WHERE cardinality(dq_flags) > 0")],
    ]
    return ["## Summary", "", *markdown_table(["Measure", "Count"], rows), ""]


def reconciliation_section(connection: psycopg.Connection, run_id: int) -> list[str]:
    rows = []
    for source, core_table in SOURCE_TO_CORE.items():
        rows.append([
            f"{source}.csv",
            scalar(connection, f"SELECT count(*) FROM staging.{source}"),
            scalar(connection,
                   "SELECT count(*) FROM audit.rejected_record WHERE run_id = %s AND source_table = %s",
                   (run_id, source)),
            f"core.{core_table}",
            scalar(connection, f"SELECT count(*) FROM core.{core_table}"),
        ])
    return [
        "## Source to core reconciliation",
        "",
        "`node.csv` has one row per crash (with duplicates); `core.node` has one row per location, "
        "so their counts are not expected to match.",
        "",
        *markdown_table(["Source file", "Source rows", "Rejected", "Core table", "Core rows"], rows),
        "",
    ]


def missing_values_section(connection: psycopg.Connection) -> list[str]:
    totals = {name: scalar(connection, f"SELECT count(*) FROM {table}") for name, table in MISSING_VALUE_TOTALS.items()}
    rows = []
    for label, query in MISSING_VALUE_CHECKS.items():
        missing = scalar(connection, query)
        total = totals[label.split()[0]]
        rows.append([label, missing, f"{missing / total:.2%}"])
    return [
        "## Missing and unknown values",
        "",
        "Unknown values are kept and mapped to explicit Unknown members, never dropped.",
        "",
        *markdown_table(["Field", "Rows", "Share"], rows),
        "",
    ]


def rules_section(connection: psycopg.Connection, run_id: int) -> list[str]:
    results = connection.execute(
        """
        SELECT rule_id, table_name, action, description, rows_checked, rows_failed
        FROM audit.dq_check_result
        WHERE run_id = %s
        ORDER BY rule_id, table_name
        """,
        (run_id,),
    ).fetchall()
    rows = [list(row) for row in results]
    return [
        "## Rule results",
        "",
        "Rules are defined in `src/validation/rules.py` and explained in "
        "[`data_quality_assessment.md`](data_quality_assessment.md).",
        "",
        *markdown_table(["Rule", "Table", "Action", "Check", "Rows checked", "Rows failed"], rows),
        "",
    ]


def build_report(connection: psycopg.Connection, run_id: int) -> str:
    lines = [
        "# Data Quality Report",
        "",
        "Generated by `python -m src.validation.report` from the audit tables. Do not edit by hand.",
        "",
        *run_section(connection, run_id),
        *summary_section(connection, run_id),
        *reconciliation_section(connection, run_id),
        *missing_values_section(connection),
        *rules_section(connection, run_id),
    ]
    return "\n".join(lines)


def write_report(run_id: int | None = None) -> Path:
    with get_connection() as connection:
        run_id = run_id or latest_successful_run(connection)
        REPORT_PATH.write_text(build_report(connection, run_id), encoding="utf-8")
    logger.info("Data quality report for run %s written to %s", run_id, REPORT_PATH)
    return REPORT_PATH


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Write the data quality report for an ETL run.")
    parser.add_argument("--run-id", type=int, help="ETL run to report on (default: latest successful run)")
    write_report(parser.parse_args().run_id)


if __name__ == "__main__":
    main()
