"""Small helpers for writing Power BI report definition (PBIR) JSON files.

PBIR stores each page and visual as its own JSON file, so report pages can be generated from
code and reviewed in Git like any other source file. Only the parts of the format this project
needs are covered here.
"""

import json
import shutil
from pathlib import Path

VISUAL_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PAGES_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"


# ------------------------------------------------------------------ field references

def column(table: str, name: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def measure(name: str, table: str = "_Measures") -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def query_ref(field: dict) -> str:
    kind = "Column" if "Column" in field else "Measure"
    return f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}"


def literal(value) -> dict:
    """Formatting values are DAX-style literals: 'text', true, 12D (number)."""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        text = f"{value}D"
    else:
        text = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": text}}}


# ------------------------------------------------------------------ filters

def _source_column(field: dict, source: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": source}}, "Property": field["Column"]["Property"]}}


def _literal_value(value) -> dict:
    if isinstance(value, bool):
        return {"Literal": {"Value": "true" if value else "false"}}
    if isinstance(value, (int, float)):
        return {"Literal": {"Value": f"{value}L"}}
    return {"Literal": {"Value": "'" + str(value).replace("'", "''") + "'"}}


def categorical_filter(name: str, field: dict, values: list) -> dict:
    """Keep only rows where the column equals one of the values."""
    table = field["Column"]["Expression"]["SourceRef"]["Entity"]
    return {
        "name": name,
        "field": field,
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "t", "Entity": table, "Type": 0}],
            "Where": [{
                "Condition": {"In": {
                    "Expressions": [_source_column(field, "t")],
                    "Values": [[_literal_value(v)] for v in values],
                }}
            }],
        },
    }


def top_n_filter(name: str, field: dict, by_measure: dict, count: int) -> dict:
    """Keep the top `count` values of a column, ranked by a measure."""
    table = field["Column"]["Expression"]["SourceRef"]["Entity"]
    measure_table = by_measure["Measure"]["Expression"]["SourceRef"]["Entity"]
    ranking_measure = {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": by_measure["Measure"]["Property"]}}
    return {
        "name": name,
        "field": field,
        "type": "TopN",
        "filter": {
            "Version": 2,
            "From": [
                {
                    "Name": "subquery",
                    "Expression": {"Subquery": {"Query": {
                        "Version": 2,
                        "From": [{"Name": "t", "Entity": table, "Type": 0},
                                 {"Name": "m", "Entity": measure_table, "Type": 0}],
                        "Select": [{**_source_column(field, "t"), "Name": "field"}],
                        "OrderBy": [{"Direction": 2, "Expression": ranking_measure}],
                        "Top": count,
                    }}},
                    "Type": 2,
                },
                {"Name": "t", "Entity": table, "Type": 0},
            ],
            "Where": [{
                "Condition": {"In": {
                    "Expressions": [_source_column(field, "t")],
                    "Table": {"SourceRef": {"Source": "subquery"}},
                }}
            }],
        },
    }


# ------------------------------------------------------------------ visuals

def _projection(item) -> dict:
    """A field, or (field, display name) to rename it in the visual."""
    field, display_name = item if isinstance(item, tuple) else (item, None)
    projection = {"field": field, "queryRef": query_ref(field), "nativeQueryRef": query_ref(field).split(".", 1)[1]}
    if display_name:
        projection["displayName"] = display_name
    return projection


def visual(
    name: str,
    visual_type: str,
    position: tuple[int, int, int, int],
    roles: dict[str, list] | None = None,
    title: str | None = None,
    sort: list[tuple[dict, str]] | None = None,
    filters: list[dict] | None = None,
    objects: dict | None = None,
    z: int = 0,
) -> dict:
    x, y, width, height = position
    body: dict = {"visualType": visual_type}
    if roles:
        body["query"] = {"queryState": {
            role: {"projections": [_projection(item) for item in items]}
            for role, items in roles.items()
        }}
        if sort:
            body["query"]["sortDefinition"] = {
                "sort": [{"field": field, "direction": direction} for field, direction in sort],
                "isDefaultSort": False,
            }
    if objects:
        body["objects"] = objects
    if title:
        body["visualContainerObjects"] = {
            "title": [{"properties": {"show": literal(True), "text": literal(title)}}],
            # Power BI otherwise adds an automatic subtitle ("Crashes by Year") in the UI language.
            "subTitle": [{"properties": {"show": literal(False)}}],
        }
    result = {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z},
        "visual": body,
    }
    if filters:
        result["filterConfig"] = {"filters": filters}
    return result


def textbox(name: str, position: tuple[int, int, int, int], text: str, size: int = 10, bold: bool = False, z: int = 0) -> dict:
    style = {"fontSize": f"{size}pt"}
    if bold:
        style["fontWeight"] = "bold"
    x, y, width, height = position
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z},
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [
                {"textRuns": [{"value": text, "textStyle": style}]}
            ]}}]},
        },
    }


def slicer(name: str, position: tuple[int, int, int, int], field: dict, title: str,
           mode: str = "Dropdown", z: int = 0) -> dict:
    """mode: 'Dropdown' for lists, 'Between' for a numeric range slider."""
    objects = {"data": [{"properties": {"mode": literal(mode)}}]}
    return visual(name, "slicer", position, roles={"Values": [(field, title)]}, objects=objects, z=z)


def matrix_style(font_size: int) -> dict:
    """Compact matrix without row or column totals."""
    size = literal(font_size)
    return {
        "subTotals": [{"properties": {"rowSubtotals": literal(False), "columnSubtotals": literal(False)}}],
        "grid": [{"properties": {"rowPadding": literal(0)}}],
        "columnHeaders": [{"properties": {"fontSize": size}}],
        "rowHeaders": [{"properties": {"fontSize": size}}],
        "values": [{"properties": {"fontSize": size}}],
    }


def table_style(font_size: int) -> dict:
    """Compact table without a totals row."""
    size = literal(font_size)
    return {
        "total": [{"properties": {"totals": literal(False)}}],
        "grid": [{"properties": {"rowPadding": literal(0)}}],
        "columnHeaders": [{"properties": {"fontSize": size}}],
        "values": [{"properties": {"fontSize": size}}],
    }


def labelled_bars() -> dict:
    """Bar chart with data labels instead of a value axis (full numbers, no 'millions' axis)."""
    return {
        "valueAxis": [{"properties": {"show": literal(False)}}],
        "labels": [{"properties": {"show": literal(True), "labelDisplayUnits": literal(1)}}],
    }


def colour_scale(value_measure: dict, low: str, high: str) -> list[dict]:
    """Background colour scale for a matrix value (conditional formatting). Goes in objects['values']."""
    return [{
        "properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
            "Input": value_measure,
            "FillRule": {"linearGradient2": {
                "min": {"color": {"Literal": {"Value": f"'{low}'"}}},
                "max": {"color": {"Literal": {"Value": f"'{high}'"}}},
                "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}},
            }},
        }}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": query_ref(value_measure)},
    }]


def card(name: str, position: tuple[int, int, int, int], value: dict, title: str,
         filters: list[dict] | None = None, z: int = 0) -> dict:
    """Classic card showing the full value (display units: none)."""
    return visual(
        name, "card", position, roles={"Values": [value]}, title=title, filters=filters, z=z,
        objects={
            "labels": [{"properties": {"labelDisplayUnits": literal(1)}}],
            "categoryLabels": [{"properties": {"show": literal(False)}}],
        },
    )


# ------------------------------------------------------------------ pages

def write_pages(report_dir: Path, pages: list[dict]) -> None:
    """Replace every page in the report with the given pages.

    Each page: {"name", "displayName", "visuals": [visual dicts], optional "filters"}.
    """
    pages_dir = report_dir / "definition" / "pages"
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    for page in pages:
        page_dir = pages_dir / page["name"]
        page_json = {
            "$schema": PAGE_SCHEMA,
            "name": page["name"],
            "displayName": page["displayName"],
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        }
        if page.get("filters"):
            page_json["filterConfig"] = {"filters": page["filters"]}
        if page.get("hidden"):
            page_json["visibility"] = "HiddenInViewMode"
        _write_json(page_dir / "page.json", page_json)
        for item in page["visuals"]:
            _write_json(page_dir / "visuals" / item["name"] / "visual.json", item)
    _write_json(pages_dir / "pages.json", {
        "$schema": PAGES_SCHEMA,
        "pageOrder": [p["name"] for p in pages],
        "activePageName": pages[0]["name"],
    })


def set_report_filters(report_dir: Path, filters: list[dict]) -> None:
    path = report_dir / "definition" / "report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["filterConfig"] = {"filters": filters}
    _write_json(path, report)


def _write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
