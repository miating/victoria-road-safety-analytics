"""Generate the paginated report lga_monthly_performance.rdl from code.

The report is RDL (Report Definition Language), the format used by SQL Server Reporting Services
and Power BI Report Builder. The SQL lives in queries/*.sql and is embedded at build time, so the
queries can be reviewed and tested on their own.

    python reports/paginated/build_rdl.py

Then open the .rdl in Power BI Report Builder (see README.md in this folder).
"""

import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "lga_monthly_performance.rdl"

NS = "http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition"
RD = "http://schemas.microsoft.com/SQLServer/reporting/reportdesigner"
ET.register_namespace("", NS)
ET.register_namespace("rd", RD)

# psqlODBC 64-bit driver name; the login is asked for when the report runs.
CONNECT_STRING = "Driver={PostgreSQL Unicode(x64)};Server=localhost;Port=5432;Database=vic_road_safety;"
FONT = "Segoe UI"
HEADER_FILL = "#1F3B57"
BORDER = "#D0D7DE"
PAGE_WIDTH_IN = 7.47  # A4 portrait (8.27in) minus 0.4in margins


def el(tag: str, text=None, rd: bool = False, **attrs) -> ET.Element:
    element = ET.Element(f"{{{RD if rd else NS}}}{tag}", attrs)
    if text is not None:
        element.text = str(text)
    return element


def sub(parent: ET.Element, tag: str, text=None, rd: bool = False, **attrs) -> ET.Element:
    child = el(tag, text, rd, **attrs)
    parent.append(child)
    return child


def style(parent: ET.Element, **props) -> ET.Element:
    """<Style> with simple properties plus optional border=(colour, style)."""
    node = sub(parent, "Style")
    border = props.pop("border", None)
    if border:
        b = sub(node, "Border")
        sub(b, "Color", border[0])
        sub(b, "Style", border[1])
    for key, value in props.items():
        sub(node, key, value)
    return node


# ------------------------------------------------------------------ report items

_names: set[str] = set()


def textbox(name: str, value: str, *, size: str = "9pt", bold: bool = False, align: str = "Left",
            fmt: str | None = None, colour: str = "#1F2328", fill: str | None = None, cell: bool = False,
            position: tuple[float, float, float, float] | None = None) -> ET.Element:
    """A textbox. `cell` adds a border for table cells; `position` = (top, left, height, width) in inches."""
    assert name not in _names, name
    _names.add(name)
    box = el("Textbox", Name=name)
    sub(box, "CanGrow", "true")
    sub(box, "KeepTogether", "true")
    paragraph = sub(sub(box, "Paragraphs"), "Paragraph")
    run = sub(sub(paragraph, "TextRuns"), "TextRun")
    sub(run, "Value", value)
    run_style = {"FontFamily": FONT, "FontSize": size, "Color": colour}
    if bold:
        run_style["FontWeight"] = "Bold"
    if fmt:
        run_style["Format"] = fmt
    style(run, **run_style)
    style(paragraph, TextAlign=align)
    if position:
        top, left, height, width = position
        sub(box, "Top", f"{top}in")
        sub(box, "Left", f"{left}in")
        sub(box, "Height", f"{height}in")
        sub(box, "Width", f"{width}in")
    box_style = {"VerticalAlign": "Middle", "PaddingLeft": "4pt", "PaddingRight": "4pt",
                 "PaddingTop": "2pt", "PaddingBottom": "2pt"}
    if cell:
        box_style["border"] = (BORDER, "Solid")
    if fill:
        box_style["BackgroundColor"] = fill
    style(box, **box_style)
    return box


def set_colour_expression(box: ET.Element, expression: str) -> None:
    """Replace the text colour with an expression (conditional formatting)."""
    colour = box.find(f".//{{{NS}}}TextRun/{{{NS}}}Style/{{{NS}}}Color")
    colour.text = expression


def header_cell(name: str, text: str, align: str = "Right") -> ET.Element:
    return textbox(name, text, bold=True, align=align, colour="White", fill=HEADER_FILL, cell=True)


def tablix(name: str, dataset: str, widths: list[float], rows: list[tuple[float, list[ET.Element], str]],
           top: float, left: float = 0.0) -> ET.Element:
    """A table. rows: (height, cells, kind) with kind 'header', 'detail', 'total' or 'static'."""
    table = el("Tablix", Name=name)
    body = sub(table, "TablixBody")
    columns = sub(body, "TablixColumns")
    for width in widths:
        sub(sub(columns, "TablixColumn"), "Width", f"{width}in")
    table_rows = sub(body, "TablixRows")
    for height, cells, _ in rows:
        row = sub(table_rows, "TablixRow")
        sub(row, "Height", f"{height}in")
        row_cells = sub(row, "TablixCells")
        for cell in cells:
            sub(sub(row_cells, "TablixCell"), "CellContents").append(cell)
    column_members = sub(sub(table, "TablixColumnHierarchy"), "TablixMembers")
    for _ in widths:
        sub(column_members, "TablixMember")
    row_members = sub(sub(table, "TablixRowHierarchy"), "TablixMembers")
    for _, _, kind in rows:
        member = sub(row_members, "TablixMember")
        if kind == "header":
            sub(member, "KeepWithGroup", "After")
            sub(member, "RepeatOnNewPage", "true")
        elif kind == "detail":
            sub(member, "Group", Name=f"{name}_details")
        elif kind == "total":
            sub(member, "KeepWithGroup", "Before")
    sub(table, "DataSetName", dataset)
    sub(table, "Top", f"{top}in")
    sub(table, "Left", f"{left}in")
    sub(table, "Height", f"{sum(h for h, _, _ in rows):.2f}in")
    sub(table, "Width", f"{sum(widths):.2f}in")
    style(table, border=("#FFFFFF", "None"))
    return table


# ------------------------------------------------------------------ data

def dataset(name: str, query_file: str, fields: dict[str, str], parameters: bool = True) -> ET.Element:
    ds = el("DataSet", Name=name)
    query = sub(ds, "Query")
    sub(query, "DataSourceName", "VicRoadSafety")
    if parameters:
        # ODBC uses positional ? markers: the order here must match the order in the SQL.
        params = sub(query, "QueryParameters")
        for marker, report_parameter in (("lga", "LGA"), ("report_year", "ReportYear")):
            sub(sub(params, "QueryParameter", Name=marker), "Value", f"=Parameters!{report_parameter}.Value")
    sub(query, "CommandText", (HERE / "queries" / query_file).read_text(encoding="utf-8").strip())
    field_list = sub(ds, "Fields")
    for field, type_name in fields.items():
        f = sub(field_list, "Field", Name=field)
        sub(f, "DataField", field)
        sub(f, "TypeName", type_name, rd=True)
    return ds


def report_parameter(name: str, data_type: str, prompt: str, default: str, values_dataset: str, field: str) -> ET.Element:
    p = el("ReportParameter", Name=name)
    sub(p, "DataType", data_type)
    sub(sub(sub(p, "DefaultValue"), "Values"), "Value", default)
    sub(p, "Prompt", prompt)
    ref = sub(sub(p, "ValidValues"), "DataSetReference")
    sub(ref, "DataSetName", values_dataset)
    sub(ref, "ValueField", field)
    sub(ref, "LabelField", field)
    return p


# ------------------------------------------------------------------ layout

def change(current: str, previous: str) -> str:
    """Expression: relative change, blank when the previous value is zero."""
    return f"=IIf({previous} = 0, Nothing, ({current} - {previous}) / {previous})"


# Red when crashes rose, green when they fell (lower is better).
CHANGE_COLOUR = "=IIf(Me.Value > 0, \"#B42318\", IIf(Me.Value < 0, \"#1A7F37\", \"#1F2328\"))"


def summary_table(top: float) -> ET.Element:
    def s(field: str) -> str:
        return f"Sum(Fields!{field}.Value)"

    rows = [(0.26, [header_cell("sum_h_measure", "Measure", "Left"),
                    header_cell("sum_h_year", "=Parameters!ReportYear.Value"),
                    header_cell("sum_h_prev", "=Parameters!ReportYear.Value - 1"),
                    header_cell("sum_h_change", "Change")], "static")]
    measures = [
        ("crashes", "Injury crashes", "#,0"),
        ("ksi", "Killed or seriously injured (KSI) crashes", "#,0"),
        ("killed", "People killed", "#,0"),
    ]
    for key, label, fmt in measures:
        field = {"crashes": "crashes", "ksi": "ksi_crashes", "killed": "persons_killed"}[key]
        change_box = textbox(f"sum_{key}_change", change(s(field), s(f"prev_{field}")),
                             align="Right", fmt="+0.0%;-0.0%;0.0%", cell=True)
        set_colour_expression(change_box, CHANGE_COLOUR)
        rows.append((0.25, [textbox(f"sum_{key}_label", label, cell=True),
                            textbox(f"sum_{key}_year", f"={s(field)}", align="Right", fmt=fmt, cell=True),
                            textbox(f"sum_{key}_prev", f"={s('prev_' + field)}", align="Right", fmt=fmt, cell=True),
                            change_box], "static"))
    rows.append((0.25, [textbox("sum_share_label", "KSI share of crashes (Victoria in brackets)", cell=True),
                        textbox("sum_share_year",
                                "=Format(Sum(Fields!ksi_crashes.Value) / IIf(Sum(Fields!crashes.Value) = 0, 1, "
                                "Sum(Fields!crashes.Value)), \"0.0%\") & \" (\" & "
                                "Format(Sum(Fields!victoria_ksi_share_pct.Value) / 100, \"0.0%\") & \")\"",
                                align="Right", cell=True),
                        textbox("sum_share_prev",
                                "=Sum(Fields!prev_ksi_crashes.Value) / IIf(Sum(Fields!prev_crashes.Value) = 0, 1, "
                                "Sum(Fields!prev_crashes.Value))", align="Right", fmt="0.0%", cell=True),
                        textbox("sum_share_change", "", cell=True)], "static"))
    return tablix("SummaryTable", "YearSummary", [3.27, 1.4, 1.4, 1.4], rows, top)


def monthly_table(top: float) -> ET.Element:
    columns = [("month_name", "Month", None), ("crashes", "Crashes", "#,0"), ("ksi_crashes", "KSI", "#,0"),
               ("persons_killed", "Killed", "#,0"), ("prev_crashes", "Crashes prev. year", "#,0"),
               ("prev_ksi_crashes", "KSI prev. year", "#,0")]
    header = [header_cell(f"mon_h_{f}", label, "Left" if f == "month_name" else "Right") for f, label, _ in columns]
    header.append(header_cell("mon_h_change", "KSI change"))
    detail = [textbox(f"mon_{f}", f"=Fields!{f}.Value", align="Left" if f == "month_name" else "Right", fmt=fmt, cell=True)
              for f, _, fmt in columns]
    ksi_change = textbox("mon_ksi_change", change("Fields!ksi_crashes.Value", "Fields!prev_ksi_crashes.Value"),
                         align="Right", fmt="+0%;-0%;0%", cell=True)
    set_colour_expression(ksi_change, CHANGE_COLOUR)
    detail.append(ksi_change)
    total = [textbox("mon_t_label", "Year", bold=True, cell=True, fill="#F6F8FA")]
    total += [textbox(f"mon_t_{f}", f"=Sum(Fields!{f}.Value)", bold=True, align="Right", fmt=fmt, cell=True, fill="#F6F8FA")
              for f, _, fmt in columns[1:]]
    total_change = textbox("mon_t_change", change("Sum(Fields!ksi_crashes.Value)", "Sum(Fields!prev_ksi_crashes.Value)"),
                           bold=True, align="Right", fmt="+0%;-0%;0%", cell=True, fill="#F6F8FA")
    set_colour_expression(total_change, CHANGE_COLOUR)
    total.append(total_change)
    widths = [1.07, 1.0, 1.0, 1.0, 1.2, 1.2, 1.0]
    return tablix("MonthlyTable", "MonthlyPerformance", widths,
                  [(0.36, header, "header"), (0.25, detail, "detail"), (0.25, total, "total")], top)


def locations_table(top: float) -> ET.Element:
    header = [header_cell("loc_h_node", "Node", "Left"), header_cell("loc_h_label", "Location", "Left"),
              header_cell("loc_h_crashes", "Crashes"), header_cell("loc_h_ksi", "KSI")]
    detail = [textbox("loc_node", "=Fields!node_id.Value", fmt="0", cell=True),
              textbox("loc_label", "=Fields!location_label.Value", cell=True),
              textbox("loc_crashes", "=Fields!crashes.Value", align="Right", fmt="#,0", cell=True),
              textbox("loc_ksi", "=Fields!ksi_crashes.Value", align="Right", fmt="#,0", cell=True)]
    return tablix("LocationsTable", "TopLocations", [0.9, 4.57, 1.0, 1.0],
                  [(0.26, header, "header"), (0.25, detail, "detail")], top)


def build() -> ET.Element:
    report = el("Report")
    sub(report, "AutoRefresh", "0")
    sub(report, "Language", "en-AU")  # dates and numbers formatted the same on every machine

    sources = sub(report, "DataSources")
    source = sub(sources, "DataSource", Name="VicRoadSafety")
    props = sub(source, "ConnectionProperties")
    sub(props, "DataProvider", "ODBC")
    sub(props, "ConnectString", CONNECT_STRING)
    sub(props, "Prompt", "PostgreSQL login (the read-only powerbi_reader role is recommended)")
    sub(source, "SecurityType", "DataBase", rd=True)
    sub(source, "DataSourceID", str(uuid.uuid5(uuid.NAMESPACE_URL, "vic-road-safety-datasource")), rd=True)

    datasets = sub(report, "DataSets")
    # Types as psqlODBC returns them: count(*) is bigint, the year column smallint, booleans text.
    integer, small, text, decimal = "System.Int64", "System.Int16", "System.String", "System.Decimal"
    datasets.append(dataset("ParameterLgas", "parameter_lgas.sql", {"lga_name": text}, parameters=False))
    datasets.append(dataset("ParameterYears", "parameter_years.sql", {"year": small}, parameters=False))
    datasets.append(dataset("YearSummary", "year_summary.sql", {
        "crashes": integer, "prev_crashes": integer, "ksi_crashes": integer, "prev_ksi_crashes": integer,
        "persons_killed": integer, "prev_persons_killed": integer, "victoria_ksi_share_pct": decimal,
        "years_complete": text}))
    datasets.append(dataset("MonthlyPerformance", "monthly_performance.sql", {
        "month_number": "System.Int32", "month_name": text, "crashes": integer, "ksi_crashes": integer,
        "persons_killed": integer, "prev_crashes": integer, "prev_ksi_crashes": integer}))
    datasets.append(dataset("TopLocations", "top_locations.sql", {
        "node_id": "System.Int32", "location_label": text, "crashes": integer, "ksi_crashes": integer}))

    section = sub(sub(report, "ReportSections"), "ReportSection")
    body = sub(section, "Body")
    items = sub(body, "ReportItems")
    width = PAGE_WIDTH_IN
    items.append(textbox("Title", "=\"Road Safety Performance Report: \" & Parameters!LGA.Value & \", \" & Parameters!ReportYear.Value",
                         size="16pt", bold=True, colour=HEADER_FILL, position=(0, 0, 0.4, width)))
    items.append(textbox("Subtitle",
                         "Injury crashes recorded in the LGA, compared with the previous year. "
                         "KSI = crashes in which someone was killed or seriously injured.",
                         size="9pt", colour="#57606A", position=(0.42, 0, 0.3, width)))
    items.append(textbox("SummaryHeading", "Year summary", size="11pt", bold=True, position=(0.85, 0, 0.28, width)))
    items.append(summary_table(1.15))
    # Tops are design positions: a table is laid out with one detail row, and the rows added at run
    # time push everything below it down. So items below a table start right after its design height.
    items.append(textbox("MonthlyHeading", "Month by month", size="11pt", bold=True, position=(2.55, 0, 0.28, width)))
    items.append(monthly_table(2.85))
    items.append(textbox("LocationsHeading", "Locations with the most crashes this year", size="11pt", bold=True,
                         position=(3.95, 0, 0.28, width)))
    items.append(locations_table(4.25))
    items.append(textbox("Notes",
                         "Notes: counts are not adjusted for traffic volume. Crashes are assigned to the LGA of their "
                         "location; Moreland and Merri-bek (renamed in 2022) are reported together as MERRI-BEK. "
                         "Only complete years can be selected, because recent months are published with a lag. "
                         "Source: Department of Transport and Planning, Victoria road crash data (CC BY 4.0).",
                         size="8pt", colour="#57606A", position=(4.95, 0, 0.6, width)))
    sub(body, "Height", "5.6in")
    style(body)
    sub(section, "Width", f"{width}in")

    page = sub(section, "Page")
    footer = sub(page, "PageFooter")
    sub(footer, "Height", "0.3in")
    sub(footer, "PrintOnFirstPage", "true")
    sub(footer, "PrintOnLastPage", "true")
    footer_items = sub(footer, "ReportItems")
    footer_items.append(textbox("FooterGenerated", "=\"Generated \" & Format(Globals!ExecutionTime, \"d MMM yyyy HH:mm\") & "
                                "\" from the vic_road_safety analytics schema\"", size="7pt", colour="#57606A",
                                position=(0.05, 0, 0.22, 5.0)))
    footer_items.append(textbox("FooterPage", "=\"Page \" & Globals!PageNumber & \" of \" & Globals!TotalPages", size="7pt",
                                colour="#57606A", align="Right", position=(0.05, 5.0, 0.22, width - 5.0)))
    style(footer)
    for tag, value in (("PageHeight", "11.69in"), ("PageWidth", "8.27in"), ("LeftMargin", "0.4in"),
                       ("RightMargin", "0.4in"), ("TopMargin", "0.4in"), ("BottomMargin", "0.4in")):
        sub(page, tag, value)
    style(page)

    parameters = sub(report, "ReportParameters")
    parameters.append(report_parameter("LGA", "String", "LGA", "CASEY", "ParameterLgas", "lga_name"))
    parameters.append(report_parameter("ReportYear", "Integer", "Year", "2024", "ParameterYears", "year"))
    grid = sub(sub(report, "ReportParametersLayout"), "GridLayoutDefinition")
    sub(grid, "NumberOfColumns", "2")
    sub(grid, "NumberOfRows", "1")
    cells = sub(grid, "CellDefinitions")
    for index, name in enumerate(("LGA", "ReportYear")):
        cell = sub(cells, "CellDefinition")
        sub(cell, "ColumnIndex", str(index))
        sub(cell, "RowIndex", "0")
        sub(cell, "ParameterName", name)

    sub(report, "ReportUnitType", "Inch", rd=True)
    sub(report, "ReportID", str(uuid.uuid5(uuid.NAMESPACE_URL, "vic-road-safety-lga-monthly")), rd=True)
    return report


def main() -> None:
    tree = ET.ElementTree(build())
    ET.indent(tree, space="  ")
    tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)
    print(f"Wrote reports/paginated/{OUTPUT.name}")


if __name__ == "__main__":
    main()
