-- Materialized views: only where the measurements in docs/views.md justify one.
--
-- vw_location_hotspots ranks all 144k locations twice (statewide and within each LGA) and is
-- the slowest view by far, while the typical questions - "top 20 locations", "worst locations
-- in this LGA", map points - read a small part of it repeatedly. The data changes only when
-- the monthly load runs, so storing the result and refreshing it after each load is a good trade.
--
-- Created WITH NO DATA; the pipeline fills it with REFRESH MATERIALIZED VIEW after each load.
-- Note: IF NOT EXISTS will not pick up a changed definition - drop the view to rebuild it.

CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_location_hotspots AS
SELECT * FROM analytics.vw_location_hotspots
WITH NO DATA;

-- A unique index is required for REFRESH MATERIALIZED VIEW CONCURRENTLY, which refreshes
-- without blocking readers (useful for a refresh outside the load transaction).
CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_location_hotspots_location
    ON analytics.mv_location_hotspots (location_key);

-- "Top N" and "top N within an LGA" read the first few rows of these indexes.
CREATE INDEX IF NOT EXISTS ix_mv_location_hotspots_state_rank
    ON analytics.mv_location_hotspots (state_rank_recent);

CREATE INDEX IF NOT EXISTS ix_mv_location_hotspots_lga_rank
    ON analytics.mv_location_hotspots (lga_name, lga_rank_recent);
