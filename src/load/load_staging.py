"""Load raw CSV files into the staging schema with PostgreSQL COPY.

Each CSV maps to the staging table with the same name. Before loading, the CSV
header is compared with the table definition so that a change in the source
files (schema drift) stops the pipeline instead of loading shifted columns.
"""

import csv
import logging
import re
from pathlib import Path

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)


def to_snake_case(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def staging_columns(connection: psycopg.Connection, table: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'staging' AND table_name = %s AND column_name <> 'source_row_number'
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    if not rows:
        raise ValueError(f"No staging table for {table}.csv - add it to sql/schema/03_staging.sql")
    return [row[0] for row in rows]


def check_header(csv_columns: list[str], table_columns: list[str], table: str) -> None:
    if csv_columns != table_columns:
        added = sorted(set(csv_columns) - set(table_columns))
        removed = sorted(set(table_columns) - set(csv_columns))
        raise ValueError(
            f"Schema drift in {table}.csv: new columns {added}, missing columns {removed}"
            + (" (column order changed)" if not added and not removed else "")
        )


def load_csv(connection: psycopg.Connection, csv_path: Path) -> int:
    table = csv_path.stem
    columns = staging_columns(connection, table)

    # utf-8-sig strips a byte order mark if the publisher ever adds one.
    with csv_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        check_header([to_snake_case(name) for name in next(reader)], columns, table)

        connection.execute(sql.SQL("TRUNCATE staging.{}").format(sql.Identifier(table)))
        copy_statement = sql.SQL("COPY staging.{} ({}) FROM STDIN").format(
            sql.Identifier(table),
            sql.SQL(", ").join(sql.Identifier(name) for name in [*columns, "source_row_number"]),
        )
        row_count = 0
        with connection.cursor().copy(copy_statement) as copy:
            for row_count, row in enumerate(reader, start=1):
                copy.write_row([value if value != "" else None for value in row] + [row_count])

    logger.info("Loaded %s rows into staging.%s", f"{row_count:,}", table)
    return row_count


def load_all(connection: psycopg.Connection, raw_dir: Path) -> dict[str, int]:
    return {path.stem: load_csv(connection, path) for path in sorted(raw_dir.glob("*.csv"))}
