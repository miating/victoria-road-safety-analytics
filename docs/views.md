# Reporting Views

The views in `sql/views/` hold the shared definitions of the main road safety measures, such
as KSI, year-over-year change and hotspot rank. SQL users, Power BI and any future application
all read the same logic instead of re-implementing it. The views also act as a stable interface:
the underlying tables can change as long as the view columns stay the same.

Timings are from [`performance_results.md`](performance_results.md) (local PostgreSQL 17,
median of 5 runs).

## The views

| View | Grain | Used for | Rows | Time |
|---|---|---|---|---|
| `vw_crash_summary` | year | KPI cards: crashes, fatal, serious, KSI, YoY change, LGA with most KSI crashes | 15 | 319 ms |
| `vw_crash_severity_trend` | month | Trend lines, with rolling 12-month totals | 169 | 131 ms |
| `vw_crashes_by_lga` | year x LGA | LGA ranking, share of state | 1,246 | 421 ms |
| `vw_crash_time_analysis` | year x weekday x hour | Day x hour heatmap, weekday vs weekend | 2,435 | 127 ms |
| `vw_vehicle_crash_analysis` | year x vehicle type | Vehicle involvement and occupant injuries | 399 | 312 ms |
| `vw_location_hotspots` | location | Hotspot ranking and map (read through the materialized view) | 144,095 | 2,903 ms |

Design choices common to all of them:

- **Every loaded year is included, with a completeness flag.** `is_complete_year` and `is_analysis_period` mark 2012-2024. Year-over-year change is only calculated between two complete years, so the incomplete 2025 is never compared with 2024 (DQ24).
- **Totals reconcile.** Crashes with an unknown location appear as LGA "Unknown" in `vw_crashes_by_lga`, so its total equals the summary. Tests in `tests/test_views.py` check that every breakdown view adds up to the same total as the fact table.
- **Counts are stored, rates are left to the consumer** where a rate needs a denominator from the user's filter. For example, `vw_crash_time_analysis` provides `weekdays_in_year` so a per-day rate can be computed for any selection of years.

## Making the views fast before materialising anything

A materialized view hides a slow query rather than fixing it, so the first step was to look at
the query plans of the slowest views.

| View | Problem in the plan | Fix | Before | After |
|---|---|---|---|---|
| `vw_crash_time_analysis` | Grouped 200,754 rows by eight columns, five of them text labels | Aggregate on the numeric keys first, join the labels to the 2,435 result rows afterwards | 716 ms | 306 ms |
| `vw_crashes_by_lga` | `mode()` (an ordered-set aggregate) forced a sort of all 200,754 crashes, which spilled to disk with the default `work_mem` | Compute each LGA's region once from the location dimension instead of from every crash | 580 ms | 466 ms |

Both rewrites were checked with `EXCEPT` in both directions to return exactly the same rows.
The before/after figures come from one session timed with the same method. Run-to-run variation on this machine is noticeable, which is why later runs show different absolute values.

## Why only one materialized view

A materialized view stores the result of its query. Reads become fast, but:

- the data is only as fresh as the last refresh
- it takes storage
- every load must refresh it

It is worth it only when a query is **slow, read often, and based on data that changes rarely**.
The data here changes once a month, so the deciding factors were speed and how the view is read.

| View | Slow? | Read often by an interactive user? | Materialized? |
|---|---|---|---|
| `vw_location_hotspots` | Yes, about 3 s: ranks 144k locations twice, and sorts spill to disk | Yes: "top N", "worst in my LGA", map points | **Yes** |
| The other five | No, 130-420 ms | Power BI in Import mode reads them once per refresh | No |

### Result

| Query | View | Materialized view |
|---|---|---|
| Top 20 locations statewide | 1,369.5 ms | 0.04 ms |
| Top 10 locations in Casey | 1,847.8 ms | 0.03 ms |

| Cost | Value |
|---|---|
| Refresh time per load | 4.8 s (median of 3) |
| Storage including indexes | 32 MB |

The materialized view has three indexes:

- `(state_rank_recent)` for the statewide top N
- `(lga_name, lga_rank_recent)` for the top N within an LGA
- a unique index on `location_key`

With these indexes, a top-N query reads a handful of index entries instead of ranking 144k rows.

### Refresh strategy

- The pipeline runs `REFRESH MATERIALIZED VIEW` at the end of the load, inside the load transaction. A plain refresh locks the view while it runs. But because the whole load is one transaction, readers keep seeing the previous version until the load commits, so this is acceptable.
- `REFRESH MATERIALIZED VIEW CONCURRENTLY` refreshes without blocking readers. It needs a unique index, which is why `ux_mv_location_hotspots_location` exists. It is the option for refreshing outside a load, for example on a schedule while dashboards are being used.
- A test (`test_materialized_view_matches_its_view`) fails if the materialized view ever differs from its live view, which would mean a missed refresh.
- I also tested raising `work_mem` from 4 MB to 64 MB for the refresh, because the plan showed sorts spilling to disk. Refresh time did not improve consistently (1.8 s vs 1.9 s, then 4.2 s vs 4.0 s), so the setting was left at the default.
