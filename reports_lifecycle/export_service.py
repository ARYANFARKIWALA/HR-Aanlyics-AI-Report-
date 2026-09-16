"""Export Service supporting CSV, multi-tab Excel, and boardroom PDF with CLS masking."""

import csv
import datetime
import io
from typing import Any

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.database.models import User
from backend.database.models_reports import SavedReport
from security.permissions import mask_pii_dataframe


class ReportExportService:
    """Generates sanitized, permission-masked exports in CSV, Excel, and PDF formats."""

    NAVY_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    GRAY_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    WHITE_BOLD = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    HEADER_TITLE = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    BOLD_FONT = Font(name="Calibri", size=11, bold=True, color="1E293B")
    REGULAR_FONT = Font(name="Calibri", size=10, color="1E293B")
    THIN_BORDER = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    @classmethod
    def prepare_sanitized_dataframe(
        cls,
        columns: list[str],
        rows: list[dict[str, Any]],
        user: User | None = None
    ) -> pd.DataFrame:
        """Applies column-level masking and sanitization to dataset based on user role."""
        if not rows:
            df = pd.DataFrame(columns=columns)
        else:
            df = pd.DataFrame(rows)
            # Ensure column order matches
            existing_cols = [c for c in columns if c in df.columns]
            df = df[existing_cols]

        user_role = getattr(user, "role", "hr_analyst") if user else "guest"
        # Mask sensitive fields (salary, ssn, email, phone) if user lacks full unmasked permissions
        masked_df = mask_pii_dataframe(df, user_role)
        return masked_df

    @classmethod
    def export_csv(
        cls,
        report: SavedReport,
        columns: list[str],
        rows: list[dict[str, Any]],
        user: User | None = None
    ) -> bytes:
        """Exports sanitized report data as UTF-8 CSV."""
        df = cls.prepare_sanitized_dataframe(columns, rows, user)
        output = io.StringIO()
        df.to_csv(output, index=False, quoting=csv.QUOTE_MINIMAL)
        return output.getvalue().encode("utf-8")

    @classmethod
    def export_excel(
        cls,
        report: SavedReport,
        columns: list[str],
        rows: list[dict[str, Any]],
        user: User | None = None,
        kpis: dict[str, Any] | None = None
    ) -> bytes:
        """Exports sanitized report data as a styled multi-sheet Excel workbook."""
        df = cls.prepare_sanitized_dataframe(columns, rows, user)
        wb = openpyxl.Workbook()

        # Tab 1: Executive Summary
        ws1 = wb.active
        ws1.title = "Executive Summary"
        ws1.views.sheetView[0].showGridLines = True

        ws1["A1"] = f"HR Analytics: {report.title}"
        ws1["A1"].font = cls.HEADER_TITLE
        gen_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
        requester = f"{user.full_name} ({user.role})" if user else "Automated System"
        ws1["A2"] = f"Generated: {gen_time} | Category: {report.category} | Version: v{report.current_version} | Requested By: {requester}"
        ws1["A2"].font = Font(name="Calibri", size=10, italic=True, color="64748B")

        # Report Metadata
        ws1["A4"] = "Report Overview & Statistics"
        ws1["A4"].font = cls.BOLD_FONT

        headers = ["Metadata Attribute", "Value"]
        for c_idx, h in enumerate(headers, 1):
            cell = ws1.cell(row=5, column=c_idx, value=h)
            cell.font = cls.WHITE_BOLD
            cell.fill = cls.NAVY_FILL

        meta_rows = [
            ("Report ID", report.report_id),
            ("Title", report.title),
            ("Category", report.category),
            ("Database", report.database_id),
            ("Total Records Exported", len(df)),
            ("Author", report.author_username or "System"),
            ("Status", "Archived" if report.is_archived else "Active"),
        ]

        for r_idx, (k, v) in enumerate(meta_rows, 6):
            c1 = ws1.cell(row=r_idx, column=1, value=k)
            c2 = ws1.cell(row=r_idx, column=2, value=str(v))
            c1.font = cls.BOLD_FONT
            c2.font = cls.REGULAR_FONT
            c1.border = cls.THIN_BORDER
            c2.border = cls.THIN_BORDER

        cls._auto_fit_columns(ws1)

        # Tab 2: Detailed Data Table
        ws2 = wb.create_sheet(title="Report Data")
        ws2.views.sheetView[0].showGridLines = True

        df_cols = list(df.columns)
        for col_idx, col_name in enumerate(df_cols, 1):
            cell = ws2.cell(row=1, column=col_idx, value=col_name.replace("_", " ").title())
            cell.font = cls.WHITE_BOLD
            cell.fill = cls.NAVY_FILL
            cell.alignment = Alignment(horizontal="center")
            cell.border = cls.THIN_BORDER

        for row_idx, row_values in enumerate(df.values, 2):
            fill = cls.ZEBRA_FILL if row_idx % 2 == 0 else PatternFill(fill_type=None)
            for col_idx, val in enumerate(row_values, 1):
                cell = ws2.cell(row=row_idx, column=col_idx, value=val)
                cell.font = cls.REGULAR_FONT
                cell.border = cls.THIN_BORDER
                if fill.fill_type:
                    cell.fill = fill

        cls._auto_fit_columns(ws2)

        # Tab 3: Governance & Lineage
        ws3 = wb.create_sheet(title="Lineage & Governance")
        ws3.views.sheetView[0].showGridLines = True

        ws3["A1"] = "Data Lineage & Executed SQL Query"
        ws3["A1"].font = cls.HEADER_TITLE
        ws3["A3"] = "Executed SQL Query"
        ws3["A3"].font = cls.BOLD_FONT
        ws3["A4"] = report.sql_query
        ws3["A4"].font = Font(name="Consolas", size=9, color="1E293B")

        cls._auto_fit_columns(ws3)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def export_pdf(
        cls,
        report: SavedReport,
        columns: list[str],
        rows: list[dict[str, Any]],
        user: User | None = None
    ) -> bytes:
        """Exports sanitized report data as an executive PDF document."""
        df = cls.prepare_sanitized_dataframe(columns, rows, user)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PDFTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E3A8A"),
            fontName="Helvetica-Bold"
        )
        subtitle_style = ParagraphStyle(
            "PDFSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64748B")
        )
        section_style = ParagraphStyle(
            "PDFSection",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=10,
            spaceAfter=4,
            fontName="Helvetica-Bold"
        )
        cell_style = ParagraphStyle(
            "PDFCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B")
        )
        header_cell_style = ParagraphStyle(
            "PDFHeaderCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.white
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph(f"HR Analytics Intelligence: {report.title}", title_style))
        gen_time = datetime.datetime.now().strftime("%B %d, %Y - %H:%M UTC")
        requester = f"{user.full_name} ({user.role})" if user else "Automated System"
        meta_line = f"<b>Report ID:</b> {report.report_id} | <b>Category:</b> {report.category} | <b>Version:</b> v{report.current_version} | <b>Generated:</b> {gen_time} | <b>Requested By:</b> {requester}"
        story.append(Paragraph(meta_line, subtitle_style))
        story.append(Spacer(1, 12))

        # 2. Tabular Data (Cap columns and rows for clean PDF layout)
        story.append(Paragraph(f"Analytical Dataset ({len(df)} records)", section_style))
        if not df.empty:
            display_cols = list(df.columns)[:8]
            col_width = max(50, min(130, int(720 / len(display_cols))))

            table_data = []
            # Header
            table_data.append([
                Paragraph(f"<b>{c.replace('_', ' ').title()}</b>", header_cell_style)
                for c in display_cols
            ])

            # Rows (up to 40)
            for _, r in df.head(40).iterrows():
                row_cells = []
                for c in display_cols:
                    v_str = str(r[c]) if pd.notnull(r[c]) else ""
                    if len(v_str) > 35:
                        v_str = v_str[:32] + "..."
                    row_cells.append(Paragraph(v_str, cell_style))
                table_data.append(row_cells)

            tbl = Table(table_data, colWidths=[col_width] * len(display_cols))
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph("No records found in this dataset.", cell_style))

        # 3. Governance block
        story.append(Spacer(1, 14))
        story.append(Paragraph("Governance & Provenance", section_style))
        gov_info = f"<b>Database Target:</b> {report.database_id}<br/><b>Access Security:</b> Role-based Column Level Masking applied."
        story.append(Paragraph(gov_info, cell_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def _auto_fit_columns(ws):
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) < 60:
                    max_len = max(max_len, len(val_str))
                else:
                    max_len = max(max_len, 35)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
