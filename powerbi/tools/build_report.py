"""Generate the report pages of victoria_road_safety.pbip from code.

Run with Power BI Desktop closed, then open the .pbip:
    python powerbi/tools/build_report.py

Every page is regenerated, so layout changes belong in this file, not in Power BI Desktop.
Design reference: docs/dashboard_design.md
"""

from pathlib import Path

from pbir import (card, categorical_filter, colour_scale, column, labelled_bars, matrix_style, measure,
                  set_report_filters, slicer, table_style, textbox, top_n_filter, visual, write_pages)

REPORT_DIR = Path(__file__).resolve().parents[1] / "victoria_road_safety.Report"

COMPLETE_YEARS_FILTER = categorical_filter("complete_years", column("dim_date", "is_analysis_period"), [True])

FOOTER = ("Injury crashes only. Complete years 2012-2024. Counts are not adjusted for traffic volume; "
          "associations do not imply causation. KSI = killed or seriously injured. "
          "Source: DTP Victoria road crash data (CC BY 4.0).")

# Fields used on several pages.
YEAR = column("dim_date", "year")
LGA = column("dim_location", "lga_name")
LOCATION = column("dim_location", "location_label")
# Rank and group by node: several nodes can share a label such as "WELLINGTON ROAD / WELLINGTON ROAD".
NODE = column("dim_location", "node_id")
KNOWN_LOCATION = categorical_filter("known_location", column("dim_location", "has_coordinates"), [True])
TOTAL = measure("Total Crashes")
KSI = measure("KSI Crashes")
KSI_SHARE = measure("KSI Share")
PER_DAY = measure("Crashes per Day")
ASCENDING, DESCENDING = "Ascending", "Descending"


def header(page: str, title: str, slicers: list[tuple[dict, str, str]]) -> list[dict]:
    """Page title plus a row of slicers: (field, label, mode)."""
    items = [textbox(f"{page}_title", (20, 8, 1240, 40), title, size=18, bold=True)]
    width = (1240 - 10 * (len(slicers) - 1)) // len(slicers)
    for i, (field, label, mode) in enumerate(slicers):
        items.append(slicer(f"{page}_slicer_{i + 1}", (20 + i * (width + 10), 52, width, 62), field, label,
                            mode=mode, z=i + 1))
    return items


def footer(page: str) -> dict:
    return textbox(f"{page}_footer", (20, 690, 1240, 26), FOOTER, size=8, z=99)


def crash_map(name: str, position: tuple[int, int, int, int], top: int, z: int) -> dict:
    return visual(
        name, "azureMap", position,
        # Coordinates only (Y = latitude, X = longitude). A Category/Location field would make the
        # map geocode its text instead of using the coordinates.
        roles={
            "Y": [(column("dim_location", "latitude"), "Latitude")],
            "X": [(column("dim_location", "longitude"), "Longitude")],
            "Size": [(TOTAL, "Crashes")],
            "Tooltips": [(NODE, "Node"), (LOCATION, "Location"), (LGA, "LGA"), (KSI, "KSI crashes"),
                         (KSI_SHARE, "KSI share")],
        },
        title=f"Crash locations (top {top} by number of crashes)",
        filters=[KNOWN_LOCATION, top_n_filter(f"{name}_top", NODE, TOTAL, top)],
        z=z,
    )


def executive_overview_page() -> dict:
    page = "overview"
    visuals = header(page, "Victoria Road Safety - Executive Overview", [
        (YEAR, "Year", "Between"),
        (LGA, "LGA", "Dropdown"),
        (column("dim_severity", "severity_desc"), "Severity", "Dropdown"),
        (column("dim_vehicle_type", "vehicle_category"), "Vehicle type", "Dropdown"),
    ])
    kpis = [
        (TOTAL, "Injury crashes"),
        (measure("Fatal Crashes"), "Fatal crashes"),
        (measure("Serious Injury Crashes"), "Serious injury crashes"),
        (measure("Crashes YoY %"), "Change vs previous year"),
        (measure("Most Affected LGA"), "Most KSI crashes (LGA)"),
    ]
    for i, (value, title) in enumerate(kpis):
        visuals.append(card(f"{page}_kpi_{i + 1}", (20 + i * 250, 122, 240, 106), value, title, z=10 + i))
    visuals += [
        visual(f"{page}_trend", "lineChart", (20, 236, 410, 236),
               roles={"Category": [(YEAR, "Year")], "Y": [(TOTAL, "All injury crashes"), (KSI, "KSI crashes")]},
               title="Crashes and KSI crashes by year", sort=[(YEAR, ASCENDING)], z=20),
        visual(f"{page}_severity", "clusteredBarChart", (440, 236, 250, 236),
               roles={"Category": [(column("dim_severity", "severity_desc"), "Severity")], "Y": [(TOTAL, "Crashes")]},
               title="Severity distribution", sort=[(column("dim_severity", "severity_desc"), ASCENDING)],
               objects=labelled_bars(), z=21),
        crash_map(f"{page}_map", (700, 236, 560, 236), top=500, z=22),
        visual(f"{page}_heatmap", "pivotTable", (20, 480, 1240, 204),
               roles={"Rows": [(column("dim_date", "day_name"), "Day")],
                      "Columns": [(column("dim_time", "hour_key"), "Hour")],
                      "Values": [(PER_DAY, "Crashes per day")]},
               title="Crashes per day by weekday and hour",
               objects={**matrix_style(8), "values": matrix_style(8)["values"] + colour_scale(PER_DAY, "#FFFFFF", "#9B1C1C")},
               z=23),
        footer(page),
    ]
    return {"name": "executive_overview", "displayName": "Executive Overview", "visuals": visuals}


def location_time_page() -> dict:
    page = "location"
    visuals = header(page, "Location & Time", [(YEAR, "Year", "Between"), (LGA, "LGA", "Dropdown")])
    visuals += [
        crash_map(f"{page}_map", (20, 122, 530, 330), top=1000, z=10),
        visual(f"{page}_lga_rank", "clusteredBarChart", (560, 122, 270, 330),
               roles={"Category": [(LGA, "LGA")], "Y": [(TOTAL, "Crashes")], "Tooltips": [(KSI_SHARE, "KSI share")]},
               title="Top 15 LGAs by crashes",
               sort=[(TOTAL, DESCENDING)], filters=[top_n_filter(f"{page}_lga_top", LGA, TOTAL, 15)], z=11),
        visual(f"{page}_hotspots", "tableEx", (840, 122, 420, 330),
               roles={"Values": [(NODE, "Node"), (LOCATION, "Location"), (LGA, "LGA"), (TOTAL, "Crashes"),
                                 (KSI, "KSI")]},
               title="Top 20 locations", sort=[(TOTAL, DESCENDING)],
               filters=[KNOWN_LOCATION, top_n_filter(f"{page}_location_top", NODE, TOTAL, 20)],
               objects=table_style(8), z=12),
        visual(f"{page}_by_hour", "lineClusteredColumnComboChart", (20, 460, 410, 222),
               roles={"Category": [(column("dim_time", "hour_key"), "Hour")], "Y": [(TOTAL, "Crashes")],
                      "Y2": [(KSI_SHARE, "KSI share")]},
               title="Busiest hours vs most severe hours", sort=[(column("dim_time", "hour_key"), ASCENDING)], z=13),
        visual(f"{page}_weekend", "clusteredColumnChart", (440, 460, 410, 222),
               roles={"Category": [(column("dim_time", "time_band"), "Time of day")],
                      "Series": [(column("dim_date", "day_type"), "Day type")],
                      "Y": [(PER_DAY, "Crashes per day")]},
               title="Weekday vs weekend by time of day", sort=[(column("dim_time", "time_band"), ASCENDING)], z=14),
        visual(f"{page}_by_month", "lineChart", (860, 460, 400, 222),
               roles={"Category": [(column("dim_date", "month_name"), "Month")], "Y": [(PER_DAY, "Crashes per day")],
                      "Tooltips": [(column("dim_date", "season"), "Season")]},
               title="Seasonality: crashes per day by month", sort=[(column("dim_date", "month_name"), ASCENDING)], z=15),
        footer(page),
    ]
    return {"name": "location_time", "displayName": "Location & Time", "visuals": visuals}


def risk_factors_page() -> dict:
    page = "risk"
    visuals = header(page, "Risk Factors - how severe are crashes when they happen?", [(YEAR, "Year", "Between"), (LGA, "LGA", "Dropdown")])
    charts = [
        ("weather", "clusteredBarChart", {"Category": [(column("dim_weather", "weather_category"), "Weather")],
                                          "Y": [(KSI_SHARE, "KSI share")], "Tooltips": [(TOTAL, "Crashes")]},
         "Weather: share of crashes that are KSI", [(KSI_SHARE, DESCENDING)]),
        ("surface", "clusteredBarChart", {"Category": [(column("dim_speed_zone", "speed_band"), "Speed zone")],
                                          "Series": [(column("dim_road_surface", "surface_category"), "Surface")],
                                          "Y": [(KSI_SHARE, "KSI share")], "Tooltips": [(TOTAL, "Crashes")]},
         "Road surface within each speed zone", [(column("dim_speed_zone", "speed_band"), ASCENDING)]),
        ("light", "clusteredBarChart", {"Category": [(column("dim_light_condition", "light_condition_desc"), "Light")],
                                        "Y": [(KSI_SHARE, "KSI share"), (measure("Fatal Share"), "Fatal share")],
                                        "Tooltips": [(TOTAL, "Crashes")]},
         "Light condition", [(KSI_SHARE, DESCENDING)]),
        ("vehicle", "clusteredBarChart", {"Category": [(column("dim_vehicle_type", "vehicle_category"), "Vehicle")],
                                          "Y": [(measure("Vehicles in KSI Crash %"), "In a KSI crash")],
                                          "Tooltips": [(measure("Vehicles Involved"), "Vehicles involved")]},
         "Vehicles: share involved in a KSI crash", [(measure("Vehicles in KSI Crash %"), DESCENDING)]),
        ("road_user", "clusteredBarChart", {"Category": [(column("dim_road_user_type", "road_user_type_desc"), "Road user")],
                                            "Y": [(measure("People KSI %"), "Killed or seriously injured")],
                                            "Tooltips": [(measure("Killed per 1,000 People Involved"), "Killed per 1,000")]},
         "Road users: share killed or seriously injured", [(measure("People KSI %"), DESCENDING)]),
        ("age", "clusteredColumnChart", {"Category": [(column("dim_person_demographic", "age_group"), "Age group")],
                                         "Y": [(measure("People KSI %"), "Killed or seriously injured")],
                                         "Tooltips": [(measure("People Involved"), "People involved")]},
         "Age: share killed or seriously injured", [(column("dim_person_demographic", "age_group"), ASCENDING)]),
    ]
    for i, (name, visual_type, roles, title, sort) in enumerate(charts):
        x = 20 + (i % 3) * 415
        y = 122 + (i // 3) * 284
        visuals.append(visual(f"{page}_{name}", visual_type, (x, y, 405, 276), roles=roles, title=title,
                              sort=sort, z=10 + i))
    visuals.append(footer(page))
    return {"name": "risk_factors", "displayName": "Risk Factors", "visuals": visuals}


def model_check_page() -> dict:
    """Cards to compare with the SQL values in powerbi/README.md (section 7)."""
    checks = [
        ("Total Crashes", "Total Crashes - expect 186,596", None),
        ("Fatal Crashes", "Fatal Crashes - expect 3,087", None),
        ("Serious Injury Crashes", "Serious Injury Crashes - expect 67,015", None),
        ("KSI Crashes", "KSI Crashes - expect 70,102", None),
        ("Persons Killed", "Persons Killed - expect 3,318", None),
        ("Crashes YoY %", "Crashes YoY % - expect -1.1%", None),
        ("Most Affected LGA", "Most Affected LGA - expect GEELONG", None),
        ("Total Crashes", "Crashes involving a motorcycle - expect 26,172",
         [categorical_filter("motorcycle_only", column("dim_vehicle_type", "vehicle_category"), ["Motorcycle"])]),
    ]
    visuals = [textbox("check_title", (20, 10, 1240, 50),
                       "Model check: each card should match the value in its title (2012-2024)", size=16, bold=True)]
    for i, (measure_name, title, filters) in enumerate(checks):
        x = 20 + (i % 4) * 310
        y = 80 + (i // 4) * 200
        visuals.append(card(f"check_{i + 1}", (x, y, 300, 180), measure(measure_name), title, filters=filters, z=i + 1))
    return {"name": "model_check", "displayName": "Model check", "visuals": visuals, "hidden": True}


def main() -> None:
    write_pages(REPORT_DIR, [executive_overview_page(), location_time_page(), risk_factors_page(),
                             model_check_page()])
    set_report_filters(REPORT_DIR, [COMPLETE_YEARS_FILTER])
    # Relative path: some Windows consoles cannot print non-ASCII folder names.
    print(f"Report pages written to powerbi/{REPORT_DIR.name}")


if __name__ == "__main__":
    main()
