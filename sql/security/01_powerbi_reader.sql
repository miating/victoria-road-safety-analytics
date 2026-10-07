-- Read-only login for Power BI (and any other reporting tool).
-- Least privilege: it can read the analytics schema and nothing else, so a dashboard
-- connection can never change data or see staging, core or audit tables.
--
-- Run once, choosing your own password (it is not stored in this repository):
--   psql -U postgres -d vic_road_safety -v reader_password='choose-a-password' -f sql/security/01_powerbi_reader.sql
--
-- Re-run the GRANT statements after `python -m src.load.apply_schema --reset`, which drops
-- and recreates the schema and its privileges.

CREATE ROLE powerbi_reader LOGIN PASSWORD :'reader_password';

GRANT CONNECT ON DATABASE :"DBNAME" TO powerbi_reader;
GRANT USAGE ON SCHEMA analytics TO powerbi_reader;
-- Covers tables, views and materialized views that exist now ...
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO powerbi_reader;
-- ... and tables created later by the postgres user.
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO powerbi_reader;
