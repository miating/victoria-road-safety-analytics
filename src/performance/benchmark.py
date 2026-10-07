"""Measure the queries in sql/performance with and without candidate indexes.

Each variant runs inside a transaction that is always rolled back: every candidate index is
dropped, the variant's indexes are created, statistics are refreshed, and the query is timed
with EXPLAIN (ANALYZE, BUFFERS). The database is left exactly as it was.

Usage:
    python -m src.performance.benchmark
"""

import json
import logging
import re
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import psycopg

from src.utils.db import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERFORMANCE_SQL_DIR = PROJECT_ROOT / "sql" / "performance"
PRODUCTION_INDEX_FILE = PROJECT_ROOT / "sql" / "indexes" / "01_indexes.sql"
RESULTS_PATH = PROJECT_ROOT / "docs" / "performance_results.md"
MEASURED_RUNS = 5

# Indexes that are only tested, never kept.
EXPERIMENTAL_INDEXES = {
    "tmp_crash_date_full": "CREATE INDEX tmp_crash_date_full ON core.crash (crash_date DESC, crash_time DESC)",
    "tmp_dim_location_road_name": "CREATE INDEX tmp_dim_location_road_name ON analytics.dim_location (road_name)",
    "tmp_fact_crash_severity": "CREATE INDEX tmp_fact_crash_severity ON analytics.fact_crash (severity_key)",
}
TABLES = ["analytics.fact_crash", "analytics.dim_location", "core.crash"]


@dataclass(frozen=True)
class Variant:
    label: str
    indexes: tuple[str, ...] = ()


CASES = {
    "01_location_crash_history.sql": [
        Variant("No index"),
        Variant("B-tree (location_key, date_key)", ("ix_fact_crash_location_date",)),
    ],
    "02_lga_month_filter.sql": [
        Variant("No index"),
        Variant("Index on lga_name only", ("ix_dim_location_lga",)),
        Variant("lga_name + composite (date_key, location_key)", ("ix_dim_location_lga", "ix_fact_crash_date_location")),
        Variant("lga_name + composite (location_key, date_key)", ("ix_dim_location_lga", "ix_fact_crash_location_date")),
    ],
    "03_recent_fatal_crashes.sql": [
        Variant("No index"),
        Variant("Full index on (crash_date, crash_time)", ("tmp_crash_date_full",)),
        Variant("Partial index WHERE severity_code = 1", ("ix_crash_fatal_recent",)),
    ],
    "04_road_name_search.sql": [
        Variant("No index"),
        Variant("Plain index on road_name", ("tmp_dim_location_road_name",)),
        Variant("Expression index lower(road_name)", ("ix_dim_location_road_name_pattern",)),
        Variant("Expression index + fact (location_key, date_key)",
                ("ix_dim_location_road_name_pattern", "ix_fact_crash_location_date")),
    ],
    "05_severity_count_no_benefit.sql": [
        Variant("No index"),
        Variant("Index on severity_key", ("tmp_fact_crash_severity",)),
    ],
}

logger = logging.getLogger(__name__)


def production_indexes() -> dict[str, str]:
    text = PRODUCTION_INDEX_FILE.read_text(encoding="utf-8")
    statements = [s.strip() for s in re.sub(r"--[^\n]*", "", text).split(";") if s.strip()]
    return {re.search(r"INDEX IF NOT EXISTS (\w+)", s).group(1): s for s in statements}


def all_indexes() -> dict[str, str]:
    return {**production_indexes(), **EXPERIMENTAL_INDEXES}


def index_schema(name: str, ddl: str) -> str:
    return re.search(r"ON (\w+)\.", ddl).group(1)


def prepare_variant(connection: psycopg.Connection, variant: Variant) -> None:
    for name, ddl in all_indexes().items():
        connection.execute(f"DROP INDEX IF EXISTS {index_schema(name, ddl)}.{name}")
    for name in variant.indexes:
        connection.execute(all_indexes()[name])
    for table in TABLES:
        connection.execute(f"ANALYZE {table}")


def plan_steps(node: dict) -> list[str]:
    """Scan and join steps of a plan, e.g. 'Seq Scan on fact_crash'."""
    description = node["Node Type"]
    if "Index Name" in node:
        description += f" using {node['Index Name']}"
    elif "Relation Name" in node:
        description += f" on {node['Relation Name']}"
    steps = [description] if "Scan" in node["Node Type"] else []
    for child in node.get("Plans", []):
        steps += plan_steps(child)
    return steps


def explain(connection: psycopg.Connection, query: str) -> dict:
    result = connection.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}").fetchone()[0]
    return (json.loads(result) if isinstance(result, str) else result)[0]


def measure_variant(connection: psycopg.Connection, query: str, variant: Variant) -> dict:
    with connection.transaction(force_rollback=True):
        prepare_variant(connection, variant)
        explain(connection, query)  # warm-up run: loads data into cache
        runs = [explain(connection, query) for _ in range(MEASURED_RUNS)]
        index_bytes = sum(
            connection.execute("SELECT pg_relation_size(%s::regclass)",
                               (f"{index_schema(n, all_indexes()[n])}.{n}",)).fetchone()[0]
            for n in variant.indexes
        )
    plan = runs[-1]["Plan"]
    return {
        "variant": variant.label,
        "median_ms": statistics.median(r["Execution Time"] for r in runs),
        "buffers": plan.get("Shared Hit Blocks", 0) + plan.get("Shared Read Blocks", 0),
        "steps": plan_steps(plan),
        "index_kb": index_bytes // 1024,
    }


def drop_foreign_keys(connection: psycopg.Connection, table: str) -> None:
    # The pipeline loads with foreign keys dropped (src/load/constraints.py), so the index
    # cost is measured the same way; otherwise per-row FK checks dominate the timing.
    names = connection.execute(
        "SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass AND contype = 'f'", (table,)
    ).fetchall()
    for (name,) in names:
        connection.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")


def measure_write_cost(connection: psycopg.Connection) -> list[dict]:
    """Time a full reload of fact_crash with and without its secondary indexes."""
    variants = [
        Variant("No secondary indexes"),
        Variant("With both adopted fact_crash indexes", ("ix_fact_crash_location_date", "ix_fact_crash_date_location")),
    ]
    results = []
    for variant in variants:
        timings = []
        for _ in range(3):
            with connection.transaction(force_rollback=True):
                prepare_variant(connection, variant)
                drop_foreign_keys(connection, "analytics.fact_crash")
                connection.execute("CREATE TEMP TABLE fact_copy ON COMMIT DROP AS SELECT * FROM analytics.fact_crash")
                connection.execute("TRUNCATE analytics.fact_crash")
                started = time.perf_counter()
                connection.execute("INSERT INTO analytics.fact_crash SELECT * FROM fact_copy")
                timings.append((time.perf_counter() - started) * 1000)
        results.append({"variant": variant.label, "median_ms": statistics.median(timings)})
    return results


REPORTING_VIEWS = [
    "vw_crash_summary", "vw_crash_severity_trend", "vw_crashes_by_lga",
    "vw_crash_time_analysis", "vw_vehicle_crash_analysis", "vw_location_hotspots",
]
HOTSPOT_QUERIES = {
    "Top 20 locations statewide":
        "SELECT location_label, lga_name, crashes_recent FROM analytics.{} ORDER BY state_rank_recent LIMIT 20",
    "Top 10 locations in Casey":
        "SELECT location_label, crashes_recent FROM analytics.{} WHERE lga_name = 'CASEY' ORDER BY lga_rank_recent LIMIT 10",
}


def median_execution_ms(connection: psycopg.Connection, query: str) -> float:
    # TIMING OFF: per-node timing adds large overhead on queries that process many rows.
    runs = [
        connection.execute(f"EXPLAIN (ANALYZE, TIMING OFF, FORMAT JSON) {query}").fetchone()[0][0]["Execution Time"]
        for _ in range(MEASURED_RUNS + 1)
    ]
    return statistics.median(runs[1:])


def views_section(connection: psycopg.Connection) -> list[str]:
    lines = ["## Reporting views", "", "| View | Rows | Median execution (ms) |", "|---|---|---|"]
    for view in REPORTING_VIEWS:
        rows = connection.execute(f"SELECT count(*) FROM analytics.{view}").fetchone()[0]
        lines.append(f"| {view} | {rows:,} | {median_execution_ms(connection, f'SELECT * FROM analytics.{view}'):.0f} |")

    lines += ["", "## View vs materialized view: location hotspots", "",
              "| Query | View (ms) | Materialized view (ms) |", "|---|---|---|"]
    for label, query in HOTSPOT_QUERIES.items():
        view_ms = median_execution_ms(connection, query.format("vw_location_hotspots"))
        mv_ms = median_execution_ms(connection, query.format("mv_location_hotspots"))
        lines.append(f"| {label} | {view_ms:,.1f} | {mv_ms:.2f} |")
        logger.info("hotspots | %-28s view %8.1f ms  mv %6.2f ms", label, view_ms, mv_ms)

    refresh_times = []
    for _ in range(3):
        with connection.transaction(force_rollback=True):
            started = time.perf_counter()
            connection.execute("REFRESH MATERIALIZED VIEW analytics.mv_location_hotspots")
            refresh_times.append(time.perf_counter() - started)
    size = connection.execute(
        "SELECT pg_total_relation_size('analytics.mv_location_hotspots') / 1024"
    ).fetchone()[0]
    lines += ["", "| Cost of the materialized view | Value |", "|---|---|",
              f"| Refresh time (median of 3) | {statistics.median(refresh_times):.1f} s |",
              f"| Storage including indexes | {size:,} KB |", ""]
    return lines


def header_text(sql_text: str) -> list[str]:
    lines = []
    for line in sql_text.splitlines():
        if not line.startswith("--"):
            break
        text = line[2:].strip()
        if re.match(r"^[A-Z][a-z]+:", text):
            label, rest = text.split(":", 1)
            lines.append(f"**{label}:** {rest.strip()}")
        elif lines:
            lines[-1] += " " + text
    return lines


def case_section(sql_file: Path, results: list[dict]) -> list[str]:
    baseline = results[0]["median_ms"]
    lines = [f"## {sql_file.stem.replace('_', ' ')}", "", f"Query: [`sql/performance/{sql_file.name}`](../sql/performance/{sql_file.name})", ""]
    for line in header_text(sql_file.read_text(encoding="utf-8")):
        lines += [line, ""]
    lines += [
        "| Variant | Median execution (ms) | Speed-up | Buffers read | Index size (KB) | Plan steps |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['variant']} | {r['median_ms']:.2f} | {baseline / r['median_ms']:.1f}x | {r['buffers']:,} "
            f"| {r['index_kb']:,} | {'; '.join(dict.fromkeys(r['steps']))} |"
        )
    return lines + [""]


def size_section(connection: psycopg.Connection) -> list[str]:
    rows = connection.execute(
        """
        SELECT c.relname, pg_relation_size(c.oid) / 1024 AS kb, t.relname AS table_name,
               pg_relation_size(t.oid) / 1024 AS table_kb
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        WHERE c.relname = ANY(%s)
        ORDER BY c.relname
        """,
        (list(production_indexes()),),
    ).fetchall()
    lines = ["## Storage cost of the adopted indexes", "",
             "| Index | Table | Index size (KB) | Table size (KB) |", "|---|---|---|---|"]
    lines += [f"| {name} | {table} | {kb:,} | {table_kb:,} |" for name, kb, table, table_kb in rows]
    return lines + [""]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    lines = [
        "# Performance Results",
        "",
        "Generated by `python -m src.performance.benchmark`. Do not edit by hand.",
        f"Each figure is the median of {MEASURED_RUNS} `EXPLAIN (ANALYZE, BUFFERS)` runs after one warm-up run, "
        "on a local PostgreSQL 17 instance. Absolute times depend on the machine; the relative difference is what matters.",
        "",
    ]
    with get_connection() as connection:
        for file_name, variants in CASES.items():
            sql_file = PERFORMANCE_SQL_DIR / file_name
            query = sql_file.read_text(encoding="utf-8")
            results = [measure_variant(connection, query, v) for v in variants]
            for r in results:
                logger.info("%s | %-50s %8.2f ms", file_name, r["variant"], r["median_ms"])
            lines += case_section(sql_file, results)

        write_cost = measure_write_cost(connection)
        lines += ["## Write cost: reloading fact_crash (200,754 rows)", "",
                  "| Variant | Median load time (ms) |", "|---|---|"]
        lines += [f"| {r['variant']} | {r['median_ms']:.0f} |" for r in write_cost]
        lines.append("")
        for r in write_cost:
            logger.info("write cost | %-30s %8.0f ms", r["variant"], r["median_ms"])
        lines += size_section(connection)
        lines += views_section(connection)

    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    logger.info("Results written to %s", RESULTS_PATH)


if __name__ == "__main__":
    main()
