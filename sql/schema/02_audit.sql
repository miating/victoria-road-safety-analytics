-- Audit layer: pipeline runs, data quality check results and rejected records.
-- Rule IDs (DQ01-DQ26) refer to docs/data_quality_assessment.md.

CREATE TABLE IF NOT EXISTS audit.etl_run (
    run_id        INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    status        TEXT NOT NULL DEFAULT 'running'
                  CHECK (status IN ('running', 'succeeded', 'failed')),
    manifest      JSONB,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS audit.dq_check_result (
    run_id       INTEGER NOT NULL REFERENCES audit.etl_run (run_id),
    rule_id      TEXT NOT NULL CHECK (rule_id ~ '^DQ[0-9]{2}$'),
    table_name   TEXT NOT NULL,
    description  TEXT NOT NULL,
    action       TEXT NOT NULL CHECK (action IN ('reject', 'fix', 'flag', 'document')),
    rows_checked INTEGER NOT NULL CHECK (rows_checked >= 0),
    rows_failed  INTEGER NOT NULL CHECK (rows_failed >= 0),
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, rule_id, table_name)
);

CREATE TABLE IF NOT EXISTS audit.rejected_record (
    rejected_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id            INTEGER NOT NULL REFERENCES audit.etl_run (run_id),
    rule_id           TEXT NOT NULL,
    source_table      TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    accident_no       TEXT,
    reason            TEXT NOT NULL,
    raw_record        JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_rejected_record_lookup
    ON audit.rejected_record (run_id, source_table, source_row_number);
