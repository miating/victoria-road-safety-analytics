"""Create the database schemas and tables by running sql/schema/*.sql in name order.

All files run in one transaction, so a failure leaves the database unchanged.
The DDL uses IF NOT EXISTS, so running it again is safe. Use --reset during
development to drop and rebuild everything (this deletes all loaded data).

Usage:
    python -m src.load.apply_schema
    python -m src.load.apply_schema --reset
"""

import argparse
import logging
from pathlib import Path

from src.utils.db import get_connection

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "sql" / "schema"
SCHEMAS = ["analytics", "core", "staging", "audit"]

logger = logging.getLogger(__name__)


def apply_schema(reset: bool = False) -> None:
    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    with get_connection() as connection:
        if reset:
            for schema in SCHEMAS:
                logger.warning("Dropping schema %s", schema)
                connection.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        for sql_file in sql_files:
            logger.info("Applying %s", sql_file.name)
            connection.execute(sql_file.read_text(encoding="utf-8"))
    # Leaving the 'with' block commits; an exception rolls everything back.


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop all project schemas first")
    apply_schema(reset=parser.parse_args().reset)
    logger.info("Schema applied")


if __name__ == "__main__":
    main()
