"""Run data quality rules, record results in audit.dq_check_result and
copy rejected rows to audit.rejected_record."""

import logging

import psycopg

from src.validation.rules import RULES, Rule

logger = logging.getLogger(__name__)


def count_failures(connection: psycopg.Connection, rule: Rule) -> tuple[int, int]:
    # The condition goes in a plain WHERE clause (not count(*) FILTER) so that
    # NOT EXISTS lookups are planned as hash anti-joins instead of per-row scans.
    table = f"{rule.stage}.{rule.table}"
    rows_checked = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    rows_failed = connection.execute(f"SELECT count(*) FROM {table} t WHERE {rule.condition}").fetchone()[0]
    return rows_checked, rows_failed


def store_rejections(connection: psycopg.Connection, run_id: int, rule: Rule) -> None:
    connection.execute(
        f"""
        INSERT INTO audit.rejected_record
            (run_id, rule_id, source_table, source_row_number, accident_no, reason, raw_record)
        SELECT %(run_id)s, %(rule_id)s, %(table)s, t.source_row_number, t.accident_no, %(reason)s,
               to_jsonb(t) - 'source_row_number'
        FROM staging.{rule.table} t
        WHERE {rule.condition}
        """,
        {"run_id": run_id, "rule_id": rule.rule_id, "table": rule.table, "reason": rule.description},
    )


def store_result(connection: psycopg.Connection, run_id: int, rule: Rule, rows_checked: int, rows_failed: int) -> None:
    connection.execute(
        """
        INSERT INTO audit.dq_check_result
            (run_id, rule_id, table_name, description, action, rows_checked, rows_failed)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (run_id, rule.rule_id, f"{rule.stage}.{rule.table}", rule.description, rule.action, rows_checked, rows_failed),
    )


def run_checks(connection: psycopg.Connection, run_id: int, stage: str) -> int:
    """Run all rules for one stage and return the number of rejected rows."""
    rejected = 0
    for rule in (r for r in RULES if r.stage == stage):
        rows_checked, rows_failed = count_failures(connection, rule)
        if rule.action == "reject" and rows_failed:
            store_rejections(connection, run_id, rule)
            rejected += rows_failed
        store_result(connection, run_id, rule, rows_checked, rows_failed)
        log = logger.warning if rows_failed and rule.action == "reject" else logger.info
        log("%s %-28s %-7s %s of %s rows", rule.rule_id, f"{rule.stage}.{rule.table}", rule.action,
            f"{rows_failed:,}", f"{rows_checked:,}")
    return rejected
