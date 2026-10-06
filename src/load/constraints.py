"""Temporarily drop foreign keys during a bulk reload and recreate them afterwards.

PostgreSQL checks a foreign key with a trigger that runs once per inserted row.
For a full reload of hundreds of thousands of rows that is far slower than
validating the whole table at once, which is what ALTER TABLE ... ADD CONSTRAINT
does. Measured on fact_person (467,730 rows, 7 foreign keys): 115 s with the
keys in place versus 2.3 s without them.

Integrity is not weakened: every key is recreated and validated before the
transaction commits, and any violation fails the whole run.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg import sql

logger = logging.getLogger(__name__)


def foreign_keys(connection: psycopg.Connection, schemas: list[str]) -> list[tuple[str, str, str, str]]:
    return connection.execute(
        """
        SELECT n.nspname, c.relname, con.conname, pg_get_constraintdef(con.oid)
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE con.contype = 'f' AND n.nspname = ANY(%s)
        ORDER BY n.nspname, c.relname, con.conname
        """,
        (schemas,),
    ).fetchall()


@contextmanager
def foreign_keys_dropped(connection: psycopg.Connection, schemas: list[str]) -> Iterator[None]:
    keys = foreign_keys(connection, schemas)
    for schema, table, name, _ in keys:
        connection.execute(
            sql.SQL("ALTER TABLE {}.{} DROP CONSTRAINT {}").format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(name)
            )
        )
    logger.info("Dropped %d foreign keys for bulk load", len(keys))

    yield

    for schema, table, name, definition in keys:
        connection.execute(
            sql.SQL("ALTER TABLE {}.{} ADD CONSTRAINT {} {}").format(
                sql.Identifier(schema), sql.Identifier(table), sql.Identifier(name), sql.SQL(definition)
            )
        )
    logger.info("Recreated and validated %d foreign keys", len(keys))
