"""Data quality rules. IDs and actions match docs/data_quality_assessment.md.

Each rule is a SQL condition that is TRUE for a failing row of one table
(referenced as alias `t`). Staging rules run on the raw text tables before
transformation; core rules count the flags written during transformation.
Rules run in list order, so rejections of crashes (DQ01-DQ07) happen before the
orphan check on child tables (DQ16) that depends on them.

Lookups against other tables use NOT EXISTS rather than NOT IN: NOT IN cannot
be turned into an anti-join (because of NULL semantics) and falls back to a
per-row scan when the subquery result does not fit in work_mem.
"""

from dataclasses import dataclass

# Approximate bounding box of Victoria with a small margin (same as the core.node CHECK).
LATITUDE_RANGE = (-39.3, -33.9)
LONGITUDE_RANGE = (140.9, 150.1)
SPECIAL_SPEED_ZONE_CODES = "('777', '888', '999')"

CHILD_TABLE_KEYS = {
    "person": "person_id",
    "vehicle": "vehicle_id",
    "atmospheric_cond": "atmosph_cond",
    "road_surface_cond": "surface_cond",
    "sub_dca": "sub_dca_code",
}
TABLES_REFERENCING_CRASH = [*CHILD_TABLE_KEYS, "node", "accident_location"]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    stage: str  # 'staging' or 'core'
    table: str
    action: str  # 'reject', 'fix' or 'flag'
    description: str
    condition: str


def is_valid(text_column: str, type_name: str) -> str:
    return f"pg_input_is_valid({text_column}, '{type_name}')"


def coordinate_outside_victoria(latitude: str, longitude: str) -> str:
    # CASE guarantees the cast only runs on values that can be cast.
    return f"""
        ({latitude} IS NOT NULL OR {longitude} IS NOT NULL)
        AND CASE WHEN {is_valid(latitude, 'numeric')} AND {is_valid(longitude, 'numeric')}
                 THEN NOT ({latitude}::numeric BETWEEN {LATITUDE_RANGE[0]} AND {LATITUDE_RANGE[1]}
                           AND {longitude}::numeric BETWEEN {LONGITUDE_RANGE[0]} AND {LONGITUDE_RANGE[1]})
                 ELSE TRUE END
    """


COUNT_COLUMNS = ["no_of_vehicles", "no_persons_killed", "no_persons_inj_2",
                 "no_persons_inj_3", "no_persons_not_inj", "no_persons"]

CRASH_RULES = [
    Rule("DQ01", "staging", "accident", "reject", "ACCIDENT_NO missing, badly formatted or duplicated",
         """t.accident_no IS NULL
            OR t.accident_no !~ '^T[0-9]{11}$'
            OR t.accident_no IN (SELECT accident_no FROM staging.accident GROUP BY 1 HAVING count(*) > 1)"""),
    Rule("DQ02", "staging", "accident", "reject", "ACCIDENT_DATE missing, invalid or outside 2012-01-01..today",
         f"""t.accident_date IS NULL
             OR CASE WHEN {is_valid('t.accident_date', 'date')}
                     THEN t.accident_date::date NOT BETWEEN DATE '2012-01-01' AND current_date
                     ELSE TRUE END"""),
    Rule("DQ03", "staging", "accident", "reject", "ACCIDENT_TIME missing or invalid",
         f"t.accident_time IS NULL OR NOT {is_valid('t.accident_time', 'time')}"),
    Rule("DQ07", "staging", "accident", "reject", "Person/vehicle counts not whole numbers or persons total inconsistent",
         " OR ".join(f"t.{c} IS NULL OR t.{c} !~ '^[0-9]+$'" for c in COUNT_COLUMNS)
         + """ OR (CASE WHEN t.no_persons ~ '^[0-9]+$' AND t.no_persons_killed ~ '^[0-9]+$'
                        AND t.no_persons_inj_2 ~ '^[0-9]+$' AND t.no_persons_inj_3 ~ '^[0-9]+$'
                        AND t.no_persons_not_inj ~ '^[0-9]+$'
                   THEN t.no_persons::int <> t.no_persons_killed::int + t.no_persons_inj_2::int
                                             + t.no_persons_inj_3::int + t.no_persons_not_inj::int
                   ELSE FALSE END)"""),
    # Assumes code 1 = Sunday ... 7 = Saturday, the mapping used by most rows.
    Rule("DQ06", "staging", "accident", "fix", "DAY_OF_WEEK code disagrees with ACCIDENT_DATE; weekday derived from date",
         f"""CASE WHEN {is_valid('t.accident_date', 'date')}
                  THEN t.day_of_week IS DISTINCT FROM (extract(dow FROM t.accident_date::date) + 1)::text
                  ELSE FALSE END"""),
    Rule("DQ10", "staging", "accident", "fix", "SPEED_ZONE is a special code, speed limit set to NULL",
         f"t.speed_zone IN {SPECIAL_SPEED_ZONE_CODES}"),
    Rule("DQ30", "staging", "accident", "reject", "NODE_ID missing or not a whole number",
         "t.node_id IS NULL OR t.node_id !~ '^-?[0-9]+$'"),
    Rule("DQ29", "staging", "accident", "fix", "NODE_ID is a negative placeholder; location set to unknown",
         "t.node_id LIKE '-%'"),
    Rule("DQ13", "staging", "accident", "fix", "Crash node missing from node.csv; location taken from lite file",
         "t.node_id NOT LIKE '-%' AND NOT EXISTS (SELECT 1 FROM staging.node n WHERE n.node_id = t.node_id)"),
]

LOCATION_RULES = [
    Rule("DQ11", "staging", "node", "fix", "Exact duplicate row in node.csv, ignored",
         """t.source_row_number IN (
                SELECT source_row_number FROM (
                    SELECT source_row_number,
                           row_number() OVER (
                               PARTITION BY accident_no, node_id, node_type, amg_x, amg_y, lga_name,
                                            lga_name_all, deg_urban_name, latitude, longitude, postcode_crash
                               ORDER BY source_row_number) AS copy_number
                    FROM staging.node) numbered
                WHERE copy_number > 1)"""),
    Rule("DQ12", "staging", "node", "fix", "Crash has conflicting DEG_URBAN_NAME rows; lite file value used",
         """t.accident_no IN (SELECT accident_no FROM staging.node
                             GROUP BY accident_no HAVING count(DISTINCT deg_urban_name) > 1)"""),
    Rule("DQ14", "staging", "node", "fix", "Coordinates outside Victoria or not numeric; set to NULL",
         coordinate_outside_victoria("t.latitude", "t.longitude")),
    Rule("DQ14", "staging", "victorian_road_crash_data", "fix", "Coordinates outside Victoria or not numeric; set to NULL",
         coordinate_outside_victoria("t.latitude", "t.longitude")),
    Rule("DQ28", "staging", "accident_location", "fix", "DISTANCE_LOCATION negative (placeholder -1); set to NULL",
         "t.distance_location LIKE '-%'"),
]

CHILD_RULES = [
    Rule("DQ16", "staging", table, "reject", "ACCIDENT_NO not found in accident.csv or that crash was rejected",
         """NOT EXISTS (SELECT 1 FROM staging.accident a
                        WHERE a.accident_no = t.accident_no
                          AND NOT EXISTS (SELECT 1 FROM audit.rejected_record r
                       WHERE r.run_id = current_setting('etl.run_id')::INTEGER
                         AND r.source_table = 'accident' AND r.source_row_number = a.source_row_number))""")
    for table in TABLES_REFERENCING_CRASH
] + [
    Rule("DQ27", "staging", table, "reject", f"Primary key (ACCIDENT_NO, {key.upper()}) missing or duplicated",
         f"""t.{key} IS NULL
             OR (t.accident_no, t.{key}) IN (SELECT accident_no, {key} FROM staging.{table}
                                            GROUP BY 1, 2 HAVING count(*) > 1)""")
    for table, key in CHILD_TABLE_KEYS.items()
] + [
    Rule("DQ22", "staging", "vehicle", "fix", "VEHICLE_YEAR_MANUF is 0 or in the future; set to NULL",
         """t.vehicle_year_manuf = '0'
            OR (t.vehicle_year_manuf ~ '^[0-9]+$'
                AND t.vehicle_year_manuf::int > extract(year FROM current_date))"""),
]


def flag_rule(rule_id: str, table: str, description: str) -> Rule:
    return Rule(rule_id, "core", table, "flag", description, f"'{rule_id}' = ANY(t.dq_flags)")


CORE_RULES = [
    flag_rule("DQ04", "crash", "Crash time recorded as exactly 00:00:00"),
    flag_rule("DQ29", "crash", "Crash location unknown (negative NODE_ID placeholder)"),
    flag_rule("DQ08", "crash", "Crash recorded with 0 vehicles"),
    flag_rule("DQ09", "crash", "Severity disagrees with injury counts"),
    flag_rule("DQ17", "crash", "Crash has no person, vehicle or atmospheric rows"),
    flag_rule("DQ18", "crash", "Crash has no sub-DCA rows"),
    flag_rule("DQ21", "crash", "Crash-level person/vehicle counts differ from detail rows"),
    flag_rule("DQ19", "person", "Person references a vehicle missing from vehicle.csv; vehicle_id set to NULL"),
    flag_rule("DQ20", "person", "Pedestrian with a vehicle, or non-pedestrian without one"),
    flag_rule("DQ13", "node", "Node has no valid coordinates in any source"),
    flag_rule("DQ14", "node", "Node coordinates outside Victoria, set to NULL"),
    Rule("DQ15", "core", "node", "flag", "Node in an unincorporated area (bracketed LGA name)", "t.is_unincorporated"),
]

RULES = CRASH_RULES + LOCATION_RULES + CHILD_RULES + CORE_RULES
