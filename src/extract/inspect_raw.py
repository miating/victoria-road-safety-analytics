"""Inspect the raw crash CSV files and write a Markdown inventory.

Everything is read as text on purpose: letting pandas infer types would hide
problems such as leading zeros ("060") or mixed values in a numeric column.
Type guesses in the report are only hints for the schema design phase.

Usage:
    python -m src.extract.inspect_raw
"""

import itertools
import logging
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REPORT_PATH = PROJECT_ROOT / "docs" / "raw_data_inventory.md"

# Chosen after looking at the files: accident.csv has one row per crash and
# every other file carries ACCIDENT_NO, so it is the natural parent table.
PARENT_FILE = "accident.csv"
PARENT_KEY = "ACCIDENT_NO"
PARENT_DATE = "ACCIDENT_DATE"

MAX_CATEGORY_VALUES = 12
MAX_KEY_RESULTS = 3

logger = logging.getLogger(__name__)


def read_raw_csv(path: Path) -> pd.DataFrame:
    # Only an empty field counts as missing; strings like "NA" are kept as data.
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def guess_type(values: pd.Series) -> str:
    values = values.dropna()
    if values.empty:
        return "empty"
    if values.str.fullmatch(r"-?\d+").all():
        return "integer" if not values.str.match(r"0\d").any() else "code (leading zeros)"
    if pd.to_numeric(values, errors="coerce").notna().all():
        return "decimal"
    if values.str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        return "date"
    if values.str.fullmatch(r"\d{2}:\d{2}:\d{2}").all():
        return "time"
    return "text"


def profile_columns(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in df.columns:
        series = df[column]
        rows.append(
            {
                "column": column,
                "type_guess": guess_type(series),
                "nulls": int(series.isna().sum()),
                "null_pct": round(series.isna().mean() * 100, 2),
                "distinct": int(series.nunique()),
                "example": series.dropna().iloc[0] if series.notna().any() else "",
            }
        )
    return pd.DataFrame(rows)


def find_candidate_keys(df: pd.DataFrame) -> list[tuple[str, ...]]:
    """Return the smallest column combinations (1 or 2 columns) that uniquely identify a row."""
    complete_columns = [c for c in df.columns if df[c].notna().all()]
    singles = [(c,) for c in complete_columns if df[c].is_unique]
    if singles:
        return singles[:MAX_KEY_RESULTS]
    pairs = [p for p in itertools.combinations(complete_columns, 2) if not df.duplicated(list(p)).any()]
    return pairs[:MAX_KEY_RESULTS]


def low_cardinality_values(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        column: df[column].value_counts(dropna=False)
        for column in df.columns
        if df[column].nunique() <= MAX_CATEGORY_VALUES
    }


def describe_parent_coverage(child: pd.DataFrame, parent: pd.DataFrame) -> dict:
    parent_keys = set(parent[PARENT_KEY])
    child_keys = set(child[PARENT_KEY])
    missing = parent[parent[PARENT_KEY].isin(parent_keys - child_keys)]
    return {
        "orphans": len(child_keys - parent_keys),
        "parents_without_rows": len(missing),
        "missing_date_min": missing[PARENT_DATE].min() if len(missing) else "",
        "missing_date_max": missing[PARENT_DATE].max() if len(missing) else "",
        "max_rows_per_parent": int(child[PARENT_KEY].value_counts().max()),
    }


def to_markdown_table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(df.columns) + " |"
    divider = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(str(v).replace("|", "\\|") for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, divider, *body])


def file_section(name: str, df: pd.DataFrame, parent: pd.DataFrame) -> list[str]:
    keys = find_candidate_keys(df.drop_duplicates())
    lines = [
        f"## {name}",
        "",
        f"- Rows: {len(df):,}",
        f"- Columns: {len(df.columns)}",
        f"- Fully duplicated rows: {int(df.duplicated().sum()):,}",
        f"- Candidate keys (after removing exact duplicates): "
        + (", ".join("(" + ", ".join(k) + ")" for k in keys) if keys else "none found with 1-2 columns"),
    ]
    if name != PARENT_FILE and PARENT_KEY in df.columns:
        coverage = describe_parent_coverage(df, parent)
        lines += [
            f"- `{PARENT_KEY}` values not found in {PARENT_FILE} (orphans): {coverage['orphans']:,}",
            f"- Crashes in {PARENT_FILE} with no rows here: {coverage['parents_without_rows']:,}"
            + (
                f" (crash dates {coverage['missing_date_min']} to {coverage['missing_date_max']})"
                if coverage["parents_without_rows"]
                else ""
            ),
            f"- Max rows per crash: {coverage['max_rows_per_parent']}",
        ]
    lines += ["", to_markdown_table(profile_columns(df)), ""]

    categories = low_cardinality_values(df)
    if categories:
        lines += ["<details><summary>Low-cardinality column values</summary>", ""]
        for column, counts in categories.items():
            values = ", ".join(f"`{value}`: {count:,}" for value, count in counts.items())
            lines.append(f"- **{column}**: {values}")
        lines += ["", "</details>", ""]
    return lines


def build_report() -> str:
    csv_paths = sorted(RAW_DIR.glob("*.csv"))
    parent = read_raw_csv(RAW_DIR / PARENT_FILE)
    lines = [
        "# Raw Data Inventory",
        "",
        "Generated by `python -m src.extract.inspect_raw` from the files in `data/raw/`",
        "(see `data/raw/manifest.json` for the download snapshot). Do not edit by hand.",
        "",
        "Type guesses are based on the text values only and are hints, not final types.",
        "",
    ]
    for path in csv_paths:
        logger.info("Inspecting %s", path.name)
        df = parent if path.name == PARENT_FILE else read_raw_csv(path)
        lines += file_section(path.name, df, parent)
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    REPORT_PATH.write_text(build_report(), encoding="utf-8")
    logger.info("Report written to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
