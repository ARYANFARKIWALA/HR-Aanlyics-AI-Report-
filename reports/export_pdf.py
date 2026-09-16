"""Corporate PDF Report Generator using ReportLab.

Produces boardroom-ready executive reports featuring:
- Branded header banner & metadata
- High-level KPI summary table
- AI Executive Briefing & Strategic Narrative
- Styled tabular query results with autowrap
- Governance, SQL Lineage, and Effective-Dating Audit
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .builder import ReportData


class PDFReportExporter:
    """Generates styled enterprise HR PDF reports."""

    @classmethod
    def generate_pdf(cls, report: ReportData, output_path: str | None = None) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            output_path or buffer,
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="Helvetica-Bold"
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B")
        )
        heading2_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=12,
            spaceAfter=6,
            fontName="Helvetica-Bold"
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1E293B")
        )
        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B")
        )
        table_hdr_style = ParagraphStyle(
            "TableHdr",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.white
        )

        story = []

        # 1. Title Banner
        story.append(Paragraph(f"HR Analytics Intelligence: {report.title}", title_style))
        meta_line = f"<b>Report ID:</b> {report.report_id} | <b>Category:</b> {report.category} | <b>Generated:</b> {report.generated_at} | <b>Requested By:</b> {report.requested_by}"
        story.append(Paragraph(meta_line, subtitle_style))
        story.append(Spacer(1, 14))

        # 2. Key Metrics Snapshot
        story.append(Paragraph("Executive Workforce Snapshot", heading2_style))
        kpis = report.kpis
        kpi_data = [
            [
                Paragraph("<b>Active Headcount</b>", table_cell_style),
                Paragraph(f"<b>{kpis.get('active_headcount', 0):,}</b>", table_cell_style),
                Paragraph("<b>Turnover Rate</b>", table_cell_style),
                Paragraph(f"<b>{kpis.get('attrition_rate_pct', 0)}%</b>", table_cell_style),
            ],
            [
                Paragraph("<b>Average Base Salary</b>", table_cell_style),
                Paragraph(f"<b>${kpis.get('avg_base_salary', 0):,.2f}</b>", table_cell_style),
                Paragraph("<b>Compa-Ratio Average</b>", table_cell_style),
                Paragraph(f"<b>{kpis.get('avg_compa_ratio', 1.0):.2f}</b>", table_cell_style),
            ],
            [
                Paragraph("<b>Female Representation</b>", table_cell_style),
                Paragraph(f"<b>{kpis.get('female_representation_pct', 0)}%</b>", table_cell_style),
                Paragraph("<b>Avg Performance Rating</b>", table_cell_style),
                Paragraph(f"<b>{kpis.get('avg_performance_rating', 0):.2f} / 5.0</b>", table_cell_style),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[150, 150, 150, 150])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1E293B")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # 3. AI Executive Narrative
        story.append(Paragraph("AI Executive Analysis & Strategic Briefing", heading2_style))
        # Format markdown paragraphs
        for para in report.executive_summary.split("\n\n"):
            cleaned_p = para.strip().replace("#", "").replace("*", "")
            if cleaned_p:
                story.append(Paragraph(cleaned_p, body_style))
                story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

        # 4. Detailed Data Table (First 35 rows)
        story.append(Paragraph("Detailed Analytical Data Table", heading2_style))
        if report.data_columns and report.data_rows:
            display_cols = report.data_columns[:8]  # cap at 8 columns for landscape fit
            col_width = max(60, min(140, int(720 / len(display_cols))))
            
            table_rows = []
            # Header
            table_rows.append([Paragraph(f"<b>{col.replace('_', ' ').title()}</b>", table_hdr_style) for col in display_cols])

            # Rows (up to 35)
            for row in report.data_rows[:35]:
                formatted_row = []
                for col in display_cols:
                    val = str(row.get(col, ""))
                    if len(val) > 40:
                        val = val[:37] + "..."
                    formatted_row.append(Paragraph(val, table_cell_style))
                table_rows.append(formatted_row)

            detail_table = Table(table_rows, colWidths=[col_width] * len(display_cols))
            detail_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(detail_table)
        else:
            story.append(Paragraph("No records found matching query criteria.", body_style))

        # 5. Governance and Lineage
        story.append(Spacer(1, 14))
        story.append(Paragraph("Data Governance & Business Logic Lineage", heading2_style))
        gov_text = f"<b>Business Rules:</b> {report.business_rules}<br/><b>Effective-Dating:</b> {report.effective_dating_notes}"
        story.append(Paragraph(gov_text, body_style))

        # Build document
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
