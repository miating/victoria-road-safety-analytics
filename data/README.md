# Data

## Source

**Victoria road crash data**, published by the Department of Transport and Planning (DTP),
Victoria, on the [DTP open data portal](https://opendata.transport.vic.gov.au/dataset/victoria-road-crash-data).

- Licence: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Data © State of Victoria (Department of Transport and Planning).
- Coverage: crashes from 2012-01-01. The data is updated monthly, with about a seven-month lag, and the most recent months are incomplete.
- Content: police-reported crashes in which someone was injured. Non-injury crashes are almost absent (4 rows).

## Download

```bash
python -m src.extract.download
```

This asks the portal's CKAN API for the current list of files and downloads each one into `data/raw/`. Files that already exist with the right size are skipped.

`data/raw/manifest.json` records the snapshot that was used: for each file, its URL, the publisher's last-modified date, size and SHA-256 hash. The manifest is committed so every result in this repository can be traced to a specific download.

## Files

| File | Rows | Grain |
|---|---|---|
| `accident.csv` | 200,754 | One row per crash |
| `person.csv` | 467,730 | One row per person in a crash |
| `vehicle.csv` | 365,470 | One row per vehicle in a crash |
| `accident_event.csv` | 331,114 | One row per event in a crash (loaded to staging only) |
| `atmospheric_cond.csv` | 202,905 | One row per weather condition of a crash |
| `road_surface_cond.csv` | 201,829 | One row per surface condition of a crash |
| `sub_dca.csv` | 287,521 | One row per sub-DCA code of a crash |
| `node.csv` | 405,918 | Crash location node. Half the rows are exact duplicates (DQ11) |
| `accident_location.csv` | 200,754 | Road names for each crash |
| `victorian_road_crash_data.csv` | 200,754 | DTP's own one-row-per-crash summary. Used for lookups and to reconcile the results |
| `dca_chart_and_sub_dca_codes.pdf` | | Code chart for crash movement types |

Row counts are for the snapshot in the manifest (crash dates 2012-01-01 to 2026-01-31).

The column-by-column profile is in [`docs/raw_data_inventory.md`](../docs/raw_data_inventory.md), and the quality issues are in [`docs/data_quality_assessment.md`](../docs/data_quality_assessment.md).

## What is in Git

| Folder | Contents | In Git? |
|---|---|---|
| `raw/` | Downloaded files | Only `manifest.json` |
| `processed/` | Not used yet; reserved for derived files | No |

The CSV files are not committed because they are large (about 280 MB) and can be downloaded again from the source.
