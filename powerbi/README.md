# Power BI

The dashboard design (pages, visuals and the questions they answer) is in
[`docs/dashboard_design.md`](../docs/dashboard_design.md). This file explains how to build and
refresh the report.

| File | Contents |
|---|---|
| `victoria_road_safety.pbix` | The report (added once built) |
| `measures.dax` | Every DAX measure, with comments |
| `screenshots/` | One image per page, so the report can be reviewed without Power BI |

## 1. Prerequisites

- Power BI Desktop (free, from the Microsoft Store)
- The database loaded with `python -m src.pipeline`
- Recommended: a read-only login for reporting. See [`sql/security/01_powerbi_reader.sql`](../sql/security/01_powerbi_reader.sql)

## 2. Connect (Import mode)

1. **Get data > PostgreSQL database**.
2. Enter:
   - Server: `localhost`
   - Database: `vic_road_safety`
   - Data connectivity mode: **Import**
3. Credentials: choose the **Database** tab and sign in as `powerbi_reader`, or your own user. Power BI stores credentials on your machine, never in the `.pbix` file.
4. A local PostgreSQL install usually has no SSL certificate. If Power BI reports an encryption error, accept the prompt to connect without encryption. A hosted database (Neon or Supabase) uses SSL, and the prompt does not appear.

### Why Import and not DirectQuery

- The whole star schema is about one million rows and compresses to tens of MB.
- The data changes monthly.
- Import gives the fastest visuals and full DAX support.
- DirectQuery would send a SQL query to PostgreSQL on every click. It is only worth that cost for very large or near-real-time data.

## 3. Select tables

From the `analytics` schema, select the 3 facts and 14 dimensions:

- **Facts:** `fact_crash`, `fact_person`, `fact_vehicle`
- **Dimensions:**
  - `dim_date`, `dim_time`, `dim_location`, `dim_severity`
  - `dim_accident_type`, `dim_light_condition`, `dim_road_geometry`, `dim_speed_zone`
  - `dim_weather`, `dim_road_surface`
  - `dim_road_user_type`, `dim_injury_level`, `dim_person_demographic`, `dim_vehicle_type`

Choose **Transform Data**, not Load.

The reporting views (`vw_*`) are not imported. The dashboard needs every slicer to filter every visual, and that only works on the related star schema. The views serve SQL users.

## 4. Power Query

1. Rename each query to remove the `analytics ` prefix. For example, `analytics fact_crash` becomes `fact_crash`. The DAX in `measures.dax` uses these names.
2. Optional, for moving to Neon or Supabase later:
   - Create two parameters, `ServerName` and `DatabaseName` (**Manage Parameters > New**).
   - Replace the hard-coded values in each query's **Source** step with these parameters.
   - Switching databases is then a parameter change.
3. **Close & Apply**.

## 5. Model

1. **Relationships.** Open Model view. Power BI detects most relationships automatically, because the key columns share names. Check that the model contains exactly these, each one-to-many and single direction (dimension filters fact):

   | Dimension | Related to |
   |---|---|
   | `dim_date`, `dim_location`, `dim_severity` | all three facts |
   | `dim_time`, `dim_accident_type`, `dim_light_condition`, `dim_road_geometry`, `dim_speed_zone`, `dim_weather`, `dim_road_surface` | `fact_crash` |
   | `dim_vehicle_type` | `fact_vehicle` and `fact_person` |
   | `dim_road_user_type`, `dim_injury_level`, `dim_person_demographic` | `fact_person` |

   **Delete** any relationship Power BI creates *between fact tables* on `accident_no`. Facts are connected through measures (`TREATAS`), not relationships. See the comments in `measures.dax`.

2. **Date table.** Select `dim_date` and choose **Table tools > Mark as date table** on `full_date`.

3. **Sort by column.** Text columns would otherwise sort alphabetically.

   | Column | Sort by |
   |---|---|
   | `dim_date[month_name]` | `month_number` |
   | `dim_date[day_name]` | `day_of_week_number` |
   | `dim_time[time_band]` | `time_band_sort` |
   | `dim_severity[severity_desc]` | `sort_order` |
   | `dim_injury_level[injury_level_desc]` | `sort_order` |
   | `dim_road_user_type[road_user_type_desc]` | `sort_order` |
   | `dim_person_demographic[age_group]` | `age_group_sort` |
   | `dim_speed_zone[speed_band]` | `speed_band_sort` |

4. **Data categories.** Set `dim_location[latitude]` to **Latitude** and `dim_location[longitude]` to **Longitude**. Set both, plus `dim_date[year]` and all `*_code` columns, to **Don't summarize**.

5. **Hide technical columns** from report view:
   - every `*_key` column
   - the `accident_no`, `person_id` and `vehicle_id` columns in the facts
   - the sort columns

6. **Measures.**
   - Create the `_Measures` table with **Home > Enter data**, leave it empty, and click OK.
   - Add each measure from `measures.dax`.
   - Set the format noted in the comment above each measure.

## 6. Report-wide filter

In the Filters pane, under **Filters on all pages**, add `dim_date[is_analysis_period] = True`.

This keeps the incomplete months from 2025 onwards out of every visual by default (DQ24). Each page says so in its footer.

## 7. Check the measures against the database

Before building visuals, put each measure in a card with no slicers selected, so only the
complete-years filter is active. Compare the cards with these values from SQL. A mismatch
means a relationship or measure is wrong.

| Measure | Expected (2012-2024) | SQL source |
|---|---|---|
| Total Crashes | 186,596 | `fact_crash` joined to `dim_date` where `is_analysis_period` |
| Fatal Crashes | 3,087 | same, `dim_severity.is_fatal` |
| Serious Injury Crashes | 67,015 | same, `severity_code = 2` |
| KSI Crashes | 70,102 | same, `is_fatal_or_serious` |
| Persons Killed | 3,318 | `sum(persons_killed)` |
| Crashes YoY % | -1.1% (2024 vs 2023) | `vw_crash_summary` |
| Most Affected LGA | GEELONG (3,491 KSI crashes) | KSI crashes by `lga_name` |
| Total Crashes, vehicle type slicer = Motorcycle | 26,172 | crashes with at least one motorcycle |

These values come from the data snapshot in `data/raw/manifest.json` and change after a new download.

## 8. Build the pages and save

1. Follow [`docs/dashboard_design.md`](../docs/dashboard_design.md).
2. Save the report as `powerbi/victoria_road_safety.pbix`.
3. Export one PNG per page to `powerbi/screenshots/`.

## Refreshing after a new data load

1. Run `python -m src.extract.download` and then `python -m src.pipeline`.
2. In Power BI Desktop, click **Home > Refresh**.

Table names, columns and keys are stable between loads, so the report needs no changes.
