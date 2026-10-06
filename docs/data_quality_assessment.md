# Data Quality Assessment

Profiling results for the raw Victoria Road Crash Data snapshot recorded in
`data/raw/manifest.json` (crash dates 2012-01-01 to 2026-01-31). All numbers
come from [`notebooks/01_data_profiling.ipynb`](../notebooks/01_data_profiling.ipynb)
and will change when the data is re-downloaded.

## Summary

Row-level quality is good: every crash ID is unique and well formed, every date
and time parses, no counts are negative, every coordinate falls inside Victoria
and no child table has orphan crash IDs.

The real issues are about meaning and consistency between files:

1. `node.csv` is half exact duplicates and still has conflicting rows after de-duplication.
2. The `DAY_OF_WEEK` code does not agree with the actual crash date.
3. The most recent months are incomplete.
4. The dataset covers injury crashes only.
5. Weather, road surface and sub-DCA can have several values per crash.

## Handling policy

Following the project rule of never silently deleting data:

| Action | Meaning |
|---|---|
| **Reject** | Row is not loaded into the cleaned tables; it is written to a rejected-records table with the rule ID and reason. |
| **Fix** | Value is corrected by a documented, deterministic rule. The original value stays in staging. |
| **Flag** | Row is loaded unchanged and the issue is recorded so analysis can include or exclude it. |
| **Document** | No change to the data; the limitation is stated in analysis and the dashboard. |

## Rules

### Crash table

| ID | Check | Result | Action |
|---|---|---|---|
| DQ01 | `ACCIDENT_NO` unique and matches `T` + 11 digits | 0 failures | Reject on failure |
| DQ02 | `ACCIDENT_DATE` parses as a date within the published range | 0 failures | Reject on failure |
| DQ03 | `ACCIDENT_TIME` parses as HH:MM:SS | 0 failures | Reject on failure |
| DQ04 | Times recorded as exactly `00:00:00` | 113 | Flag (possibly a placeholder for unknown time) |
| DQ05 | Year in `ACCIDENT_NO` equals crash year | 4,629 differ (mostly by +1) | Document: the ID is not date-based, never derive dates from it |
| DQ06 | `DAY_OF_WEEK` code agrees with the date | Code `0` on 4,653 rows; codes `1`-`6` each map to two different weekdays. `DAY_WEEK_DESC` matches the date on 100% of rows | Fix: derive the weekday from `ACCIDENT_DATE`; do not use the raw code |
| DQ07 | Count columns are non-negative and `NO_PERSONS` = killed + serious + other + not injured | 0 failures | Reject on failure |
| DQ08 | Crashes with `NO_OF_VEHICLES = 0` | 6 | Flag |
| DQ09 | `SEVERITY` agrees with injury counts | Fatal vs killed: 0 conflicts. Serious severity with no serious injury: 1 | Flag |
| DQ10 | `SPEED_ZONE` is a real speed limit | `777` (399), `888` (1,344), `999` (13,261) are special codes, not speeds | Fix: keep the original code, set numeric speed limit to NULL for these codes. Meaning of each code to be confirmed from DTP documentation |

### Location (`node.csv`, lite file)

| ID | Check | Result | Action |
|---|---|---|---|
| DQ11 | Exact duplicate rows in `node.csv` | 202,505 of 405,918 | Fix: drop exact duplicates, log the count |
| DQ12 | One location row per crash after de-duplication | 3,137 crashes still have 2-3 rows, differing only in `DEG_URBAN_NAME` | Fix: use the value from the lite file, which is always one of the conflicting values |
| DQ13 | Every crash has a location | 487 crashes missing from `node.csv`; 85 have no coordinates in the lite file either | Fix: take coordinates from the lite file when node is missing. Flag the remaining 85 as unknown location |
| DQ14 | Coordinates inside Victoria (lat -39.3 to -33.9, lon 140.9 to 150.1) and not zero | 0 outside, 0 zero. Node and lite coordinates are identical wherever both exist | Reject the coordinates (set to NULL, keep the crash) on failure |
| DQ15 | `LGA_NAME` is a council | 149 crashes in bracketed unincorporated areas, e.g. `(MOUNT HOTHAM)` | Flag as unincorporated, keep the name |

### Referential integrity

| ID | Check | Result | Action |
|---|---|---|---|
| DQ16 | Child rows reference an existing crash (orphans) | 0 in every child table | Reject on failure |
| DQ17 | Every crash has person / vehicle / atmospheric rows | About 400 crashes missing per table; 327 of them are from 2025-08 onwards, consistent with these files being an older snapshot than `accident.csv` | Flag; see DQ24 |
| DQ18 | Every crash has sub-DCA rows | 1,276 missing, including a gap in May-July 2014 | Flag; document the 2014 gap |
| DQ19 | Person `VEHICLE_ID` exists in `vehicle.csv` | 39 references not found | Flag, keep the person |
| DQ20 | Pedestrians have no vehicle and other road users do | 31 pedestrians with a vehicle; 24 non-pedestrians without one | Flag |
| DQ21 | Crash-level counts match detail rows | `NO_PERSONS` vs person rows: 2 differ. `NO_PERSONS_KILLED` vs fatal person rows: 0 differ. `NO_OF_VEHICLES` vs vehicle rows: 5 differ | Flag. Crash-level counts are the source of truth for crash metrics |

### Vehicle and person

| ID | Check | Result | Action |
|---|---|---|---|
| DQ22 | `VEHICLE_YEAR_MANUF` is a plausible year | 31,211 are `0`, 6,951 blank, 1 in the future | Fix: `0` and future years become NULL |
| DQ23 | Unknown categories | `AGE_GROUP = Unknown` 15,129; `SEX = U` 16,675; plus "Not known" codes in weather, surface and light condition | Map to an explicit Unknown member, never drop |
| — | `VEHICLE_POWER` | 100% empty | Not loaded |
| — | `ROAD_USER_TYPE` | Codes 2 and 7 both mean Drivers; 3 and 8 both mean Passengers | Document: analyse by description, not code |

### Analysis scope

| ID | Check | Result | Action |
|---|---|---|---|
| DQ24 | Recent months are complete | About 1,200-1,500 crashes per month until 2025-08, then 968, 1,058, 585, 692, 136 (2025-09 to 2026-01) | Document: load all data, but trend and year-over-year analysis uses only complete periods |
| DQ25 | Severity coverage | Only 4 non-injury crashes in 200,754 | Document: this is an **injury crash** dataset; never describe results as "all crashes" |
| DQ26 | Time precision | Times cluster on :00 and :30 | Document: analyse by hour, not by minute |

## Modelling implications for Phase 3

- **Grain:** `accident.csv` has exactly one row per crash and is the parent of every other file.
- **Location:** after de-duplication, `node.csv` has one `NODE_ID` per crash. The lite file is the most complete one-row-per-crash location source.
- **Multi-valued attributes:**
  - 2,509 crashes have more than one weather condition.
  - 1,070 have more than one surface condition.
  - 69,683 have more than one sub-DCA code.

  These need a bridge table or a "primary condition" rule rather than a single foreign key on the fact table.
- **Person to vehicle:** pedestrians have no `VEHICLE_ID`, so the foreign key from person to vehicle must allow NULL.
