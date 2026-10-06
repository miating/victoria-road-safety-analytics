"""Run the SQL transformation files in a directory, in name order."""

import logging
from pathlib import Path

import psycopg

logger = logging.getLogger(__name__)


def run_sql_files(connection: psycopg.Connection, directory: Path) -> None:
    for sql_file in sorted(directory.glob("*.sql")):
        logger.info("Running %s/%s", directory.name, sql_file.name)
        connection.execute(sql_file.read_text(encoding="utf-8"))
