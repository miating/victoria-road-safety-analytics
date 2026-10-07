"""End-to-end pipeline: raw CSV -> staging -> validation -> core -> analytics.

All loading and transformation happens in one database transaction, so a
failed run leaves the previous successful load untouched. The run itself is
logged in audit.etl_run on a separate connection so failures are recorded too.

Usage:
    python -m src.pipeline
"""

import json
import logging
import time
from pathlib import Path

import psycopg

from src.load.constraints import foreign_keys_dropped
from src.load.load_staging import load_all
from src.transform.run_sql import run_sql_files
from src.utils.db import get_connection
from src.validation.checks import run_checks
from src.validation.report import write_report

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"
CORE_SQL_DIR = PROJECT_ROOT / "sql" / "transform" / "core"
ANALYTICS_SQL_DIR = PROJECT_ROOT / "sql" / "transform" / "analytics"

logger = logging.getLogger(__name__)


def start_run() -> int:
    manifest = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else None
    with get_connection() as connection:
        return connection.execute(
            "INSERT INTO audit.etl_run (manifest) VALUES (%s) RETURNING run_id", (manifest,)
        ).fetchone()[0]


def finish_run(run_id: int, status: str, error_message: str | None = None) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE audit.etl_run SET finished_at = now(), status = %s, error_message = %s WHERE run_id = %s",
            (status, error_message, run_id),
        )


def row_counts(connection: psycopg.Connection, schema: str) -> dict[str, int]:
    tables = connection.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
        (schema,),
    ).fetchall()
    return {
        name: connection.execute(f"SELECT count(*) FROM {schema}.{name}").fetchone()[0]
        for (name,) in tables
    }


def run_pipeline(run_id: int) -> None:
    with get_connection() as connection:
        # Makes the run ID available to SQL (current_setting) for this transaction only.
        connection.execute("SELECT set_config('etl.run_id', %s, true)", (str(run_id),))

        logger.info("Step 1/5: loading staging")
        load_all(connection, RAW_DIR)

        logger.info("Step 2/5: validating staging data")
        rejected = run_checks(connection, run_id, "staging")

        with foreign_keys_dropped(connection, ["core", "analytics"]):
            logger.info("Step 3/5: building core tables")
            run_sql_files(connection, CORE_SQL_DIR)

            logger.info("Step 4/5: checking core flags")
            run_checks(connection, run_id, "core")

            logger.info("Step 5/5: building analytics tables")
            run_sql_files(connection, ANALYTICS_SQL_DIR)
        connection.execute("ANALYZE core.crash, core.person, core.vehicle, core.node")
        # Fresh statistics so the planner uses the indexes in sql/indexes; the expression
        # index on dim_location needs ANALYZE to have statistics for lower(road_name).
        connection.execute(
            "ANALYZE analytics.fact_crash, analytics.fact_person, analytics.fact_vehicle, analytics.dim_location"
        )

        logger.info("Rejected rows: %s", f"{rejected:,}")
        for schema in ("core", "analytics"):
            logger.info("%s row counts: %s", schema, json.dumps(row_counts(connection, schema)))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    started = time.perf_counter()
    run_id = start_run()
    logger.info("Started ETL run %s", run_id)
    try:
        run_pipeline(run_id)
    except Exception as error:
        finish_run(run_id, "failed", str(error))
        logger.exception("ETL run %s failed; database left unchanged", run_id)
        raise
    finish_run(run_id, "succeeded")
    logger.info("ETL run %s succeeded in %.0f seconds", run_id, time.perf_counter() - started)
    write_report(run_id)


if __name__ == "__main__":
    main()
