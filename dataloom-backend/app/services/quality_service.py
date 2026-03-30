"""Dataset export and quality report helpers."""

from __future__ import annotations

from html import escape
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import schemas

EXPORT_MEDIA_TYPES = {
    schemas.ExportFormat.csv: "text/csv; charset=utf-8",
    schemas.ExportFormat.tsv: "text/tab-separated-values; charset=utf-8",
    schemas.ExportFormat.json: "application/json",
    schemas.ExportFormat.xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    schemas.ExportFormat.parquet: "application/octet-stream",
}

REPORT_MEDIA_TYPES = {
    schemas.ReportFormat.html: "text/html; charset=utf-8",
    schemas.ReportFormat.pdf: "application/pdf",
}


def _safe_scalar(value) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def build_quality_summary(df: pd.DataFrame) -> dict:
    """Compute dataset-level and column-level quality metrics."""
    missing = df.isna().sum()
    duplicate_rows = int(df.duplicated().sum())
    columns = []
    for column in df.columns:
        series = df[column]
        non_null = series.dropna()
        top_values = [
            {"value": _safe_scalar(idx), "count": int(count)}
            for idx, count in series.astype("string").fillna("<missing>").value_counts().head(3).items()
        ]
        column_summary = {
            "name": column,
            "dtype": str(series.dtype),
            "missing_count": int(missing[column]),
            "missing_pct": round(float(missing[column] / len(df) * 100), 2) if len(df) else 0.0,
            "unique_count": int(non_null.nunique()),
            "sample_values": [_safe_scalar(value) for value in non_null.head(3).tolist()],
            "top_values": top_values,
        }
        if pd.api.types.is_numeric_dtype(series):
            description = series.describe()
            column_summary["numeric_stats"] = {
                key: round(float(description[key]), 4)
                for key in ("mean", "std", "min", "max")
                if key in description and pd.notna(description[key])
            }
        columns.append(column_summary)

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "missing_cells": int(missing.sum()),
        "duplicate_rows": duplicate_rows,
        "completeness_pct": round(
            float((1 - (missing.sum() / max(len(df) * max(len(df.columns), 1), 1))) * 100),
            2,
        )
        if len(df.columns)
        else 100.0,
        "columns": columns,
    }


def render_quality_report_html(project_name: str, summary: dict) -> bytes:
    """Render an HTML quality report."""
    rows = "".join(
        """
        <tr>
          <td>{name}</td>
          <td>{dtype}</td>
          <td>{missing_count}</td>
          <td>{missing_pct}%</td>
          <td>{unique_count}</td>
          <td>{sample_values}</td>
        </tr>
        """.format(
            name=escape(column["name"]),
            dtype=escape(column["dtype"]),
            missing_count=column["missing_count"],
            missing_pct=column["missing_pct"],
            unique_count=column["unique_count"],
            sample_values=escape(", ".join(column["sample_values"]) or "-"),
        )
        for column in summary["columns"]
    )

    cards = [
        ("Rows", summary["row_count"]),
        ("Columns", summary["column_count"]),
        ("Missing Cells", summary["missing_cells"]),
        ("Duplicate Rows", summary["duplicate_rows"]),
        ("Completeness", f'{summary["completeness_pct"]}%'),
    ]
    card_html = "".join(
        f'<div class="card"><span class="label">{escape(label)}</span><strong>{escape(str(value))}</strong></div>'
        for label, value in cards
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{escape(project_name)} Quality Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; background: #f8fafc; }}
    h1, h2 {{ margin-bottom: 12px; }}
    .cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0 28px; }}
    .card {{ background: white; border: 1px solid #dbe3ef; border-radius: 12px; padding: 16px; min-width: 150px; }}
    .label {{ display: block; color: #64748b; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ padding: 10px 12px; border: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ background: #eff6ff; }}
  </style>
</head>
<body>
  <h1>{escape(project_name)} Quality Report</h1>
  <p>Generated from the current project data snapshot.</p>
  <div class="cards">{card_html}</div>
  <h2>Column Summary</h2>
  <table>
    <thead>
      <tr>
        <th>Column</th>
        <th>Type</th>
        <th>Missing</th>
        <th>Missing %</th>
        <th>Unique</th>
        <th>Sample Values</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>"""
    return html.encode("utf-8")


def render_quality_report_pdf(project_name: str, summary: dict) -> bytes:
    """Render a PDF quality report."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=32, rightMargin=32, topMargin=32, bottomMargin=32)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"{escape(project_name)} Quality Report", styles["Title"]),
        Paragraph("Generated from the current project data snapshot.", styles["BodyText"]),
        Spacer(1, 12),
    ]

    overview_rows = [
        ["Metric", "Value"],
        ["Rows", str(summary["row_count"])],
        ["Columns", str(summary["column_count"])],
        ["Missing Cells", str(summary["missing_cells"])],
        ["Duplicate Rows", str(summary["duplicate_rows"])],
        ["Completeness", f'{summary["completeness_pct"]}%'],
    ]
    overview = Table(overview_rows, hAlign="LEFT")
    overview.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([overview, Spacer(1, 18), Paragraph("Column Summary", styles["Heading2"])])

    table_rows = [["Column", "Type", "Missing", "Unique", "Samples"]]
    for column in summary["columns"]:
        table_rows.append(
            [
                column["name"],
                column["dtype"],
                str(column["missing_count"]),
                str(column["unique_count"]),
                ", ".join(column["sample_values"]) or "-",
            ]
        )
    details = Table(table_rows, repeatRows=1, colWidths=[120, 90, 60, 60, 180])
    details.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(details)
    doc.build(story)
    return buffer.getvalue()


def build_quality_report(project_name: str, df: pd.DataFrame, report_format: schemas.ReportFormat) -> bytes:
    """Build a quality report in the requested format."""
    summary = build_quality_summary(df)
    if report_format == schemas.ReportFormat.html:
        return render_quality_report_html(project_name, summary)
    return render_quality_report_pdf(project_name, summary)
