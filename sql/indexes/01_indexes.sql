-- Secondary indexes, each justified by a measured query in sql/performance/.
-- Results and reasoning: docs/query_optimisation.md and docs/performance_results.md.
-- Deliberately NOT indexed: low-selectivity keys such as fact_crash.severity_key (see
-- sql/performance/05) and columns only used by full-table aggregations.

-- Drill-down to one location or a handful of locations (performance cases 01, 04).
CREATE INDEX IF NOT EXISTS ix_fact_crash_location_date
    ON analytics.fact_crash (location_key, date_key);

-- Date-range filters, e.g. one year for a whole LGA (case 02). Location-first could not serve
-- this: with thousands of locations in an LGA the planner preferred a sequential scan.
CREATE INDEX IF NOT EXISTS ix_fact_crash_date_location
    ON analytics.fact_crash (date_key, location_key);

-- Dashboard filter by LGA (case 02).
CREATE INDEX IF NOT EXISTS ix_dim_location_lga
    ON analytics.dim_location (lga_name);

-- Case-insensitive "starts with" road name search (case 04).
CREATE INDEX IF NOT EXISTS ix_dim_location_road_name_pattern
    ON analytics.dim_location (lower(road_name) text_pattern_ops);

-- Latest fatal crashes (case 03). Partial: only the 1.7% of crashes that are fatal.
CREATE INDEX IF NOT EXISTS ix_crash_fatal_recent
    ON core.crash (crash_date DESC, crash_time DESC)
    WHERE severity_code = 1;
