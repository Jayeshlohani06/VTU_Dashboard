"""
PDF Report Generator for VTU Dashboard.
Generates styled PDF reports for individual students, class summaries,
and subject analysis using ReportLab.
"""

import io
import base64
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import pandas as pd
import re
from logging_config import get_logger

logger = get_logger("pdf_service")

# Color palette
HEADER_BG = colors.HexColor("#1f2937")
HEADER_TEXT = colors.white
ROW_ALT = colors.HexColor("#f3f4f6")
PASS_COLOR = colors.HexColor("#059669")
FAIL_COLOR = colors.HexColor("#dc2626")
BRAND_COLOR = colors.HexColor("#3b82f6")
LIGHT_BORDER = colors.HexColor("#e5e7eb")


def _get_styles():
    """Get custom paragraph styles."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "TitleCenter", parent=styles["Title"],
        alignment=TA_CENTER, fontSize=18, spaceAfter=6,
        textColor=HEADER_BG
    ))
    styles.add(ParagraphStyle(
        "SubtitleCenter", parent=styles["Normal"],
        alignment=TA_CENTER, fontSize=10, spaceAfter=12,
        textColor=colors.gray
    ))
    styles.add(ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontSize=13, textColor=BRAND_COLOR,
        spaceAfter=8, spaceBefore=12
    ))
    styles.add(ParagraphStyle(
        "SmallRight", parent=styles["Normal"],
        alignment=TA_RIGHT, fontSize=8, textColor=colors.gray
    ))
    return styles


def _build_table_style(header_rows=1):
    """Standard table styling."""
    style = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), HEADER_TEXT),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, header_rows - 1), 9),
        ("FONTSIZE", (0, header_rows), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_BORDER),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, ROW_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    return TableStyle(style)


def generate_student_report_pdf(student_row, subject_codes, institution_name=""):
    """
    Generate a PDF report card for an individual student.
    
    Parameters
    ----------
    student_row : dict or pd.Series
        Student data with subject marks, result, etc.
    subject_codes : list
        List of subject codes to include.
    institution_name : str
        Name of institution for header.
    
    Returns
    -------
    bytes : PDF file content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=15*mm)
    styles = _get_styles()
    story = []

    # Header
    story.append(Paragraph("Student Performance Report", styles["TitleCenter"]))
    if institution_name:
        story.append(Paragraph(institution_name, styles["SubtitleCenter"]))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["SmallRight"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_COLOR, spaceAfter=10))

    # Student Info
    student_id = student_row.get("Student ID", student_row.get("Student_ID", "N/A"))
    name = student_row.get("Name", "N/A")
    overall = student_row.get("Overall_Result", "N/A")
    
    info_data = [
        ["Student ID", str(student_id)],
        ["Name", str(name)],
        ["Overall Result", str(overall)],
    ]
    if "Section" in student_row:
        info_data.append(["Section", str(student_row["Section"])])
    if "Total_Marks" in student_row:
        info_data.append(["Total Marks", str(student_row["Total_Marks"])])
    if "Class_Rank" in student_row:
        info_data.append(["Class Rank", str(student_row["Class_Rank"])])

    info_table = Table(info_data, colWidths=[120, 300])
    info_style = TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, -1), (-1, -1), 1, LIGHT_BORDER),
    ])
    info_table.setStyle(info_style)
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Subject Performance Table
    story.append(Paragraph("Subject-wise Performance", styles["SectionHeader"]))

    headers = ["Subject", "Internal", "External", "Total", "Result"]
    table_data = [headers]

    for sub in subject_codes:
        int_val = student_row.get(f"{sub}_Internal", "")
        ext_val = student_row.get(f"{sub}_External", "")
        tot_val = student_row.get(f"{sub}_Total", "")
        res_val = student_row.get(f"{sub}_Result", "")

        # Skip electives not taken
        if all(str(v).strip() in ("", "nan", "None") for v in [int_val, ext_val, tot_val, res_val]):
            continue

        table_data.append([
            str(sub),
            str(int_val) if pd.notna(int_val) else "-",
            str(ext_val) if pd.notna(ext_val) else "-",
            str(tot_val) if pd.notna(tot_val) else "-",
            str(res_val) if pd.notna(res_val) else "-",
        ])

    if len(table_data) > 1:
        t = Table(table_data, colWidths=[120, 70, 70, 70, 70])
        style = _build_table_style()

        # Color result column
        for i, row in enumerate(table_data[1:], start=1):
            result = str(row[4]).strip().upper()
            if result.startswith("P"):
                style.add("TEXTCOLOR", (4, i), (4, i), PASS_COLOR)
            elif result.startswith("F"):
                style.add("TEXTCOLOR", (4, i), (4, i), FAIL_COLOR)

        t.setStyle(style)
        story.append(t)
    else:
        story.append(Paragraph("No subject data available.", styles["Normal"]))

    # Footer
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=6))
    story.append(Paragraph(
        "Generated by VTU Student Performance Dashboard",
        styles["SmallRight"]
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info("Generated student PDF for %s", student_id)
    return pdf_bytes


def generate_class_summary_pdf(df, subject_codes, kpi_data=None, institution_name="", subject_col_map=None):
    """
    Generate a class summary PDF with KPIs, top performers, and subject statistics.
    
    Parameters
    ----------
    df : pd.DataFrame
        Processed student DataFrame.
    subject_codes : list
        Subject codes to include.
    kpi_data : dict, optional
        KPI summary data.
    institution_name : str
        Institution name for header.
    subject_col_map : dict, optional
        Mapping of subject code to actual column names.
    
    Returns
    -------
    bytes : PDF file content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm)
    styles = _get_styles()
    story = []

    # Header
    story.append(Paragraph("Class Performance Summary Report", styles["TitleCenter"]))
    if institution_name:
        story.append(Paragraph(institution_name, styles["SubtitleCenter"]))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["SmallRight"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_COLOR, spaceAfter=10))

    # KPI Summary
    if kpi_data:
        story.append(Paragraph("Performance Overview", styles["SectionHeader"]))
        kpi_rows = [["Metric", "Value"]]
        for k, v in kpi_data.items():
            kpi_rows.append([str(k), str(v)])
        kpi_table = Table(kpi_rows, colWidths=[200, 150])
        kpi_table.setStyle(_build_table_style())
        story.append(kpi_table)
        story.append(Spacer(1, 15))

    id_col = "Student ID" if "Student ID" in df.columns else "Student_ID"

    # Top 10 Performers
    if "Total_Marks" in df.columns:
        story.append(Paragraph("Top 10 Performers", styles["SectionHeader"]))
        top_df = df.nlargest(10, "Total_Marks")
        top_headers = ["Rank", "Student ID", "Name", "Total Marks", "Result"]
        top_data = [top_headers]
        for rank, (_, row) in enumerate(top_df.iterrows(), 1):
            top_data.append([
                str(rank),
                str(row.get(id_col, "")),
                str(row.get("Name", "")),
                str(row.get("Total_Marks", "")),
                str(row.get("Overall_Result", "")),
            ])
        top_table = Table(top_data, colWidths=[40, 130, 180, 80, 60])
        top_table.setStyle(_build_table_style())
        story.append(top_table)
        story.append(Spacer(1, 15))

    # Subject Summary
    story.append(Paragraph("Subject-wise Summary", styles["SectionHeader"]))
    subj_headers = ["Subject", "Appeared", "Passed", "Failed", "Pass %"]
    subj_data = [subj_headers]

    for sub in subject_codes:
        # Resolve actual Result column name
        res_col = None
        if subject_col_map and sub in subject_col_map:
            res_col = subject_col_map[sub].get("Result")
        if not res_col:
            # Fallback: try common formats
            for candidate in [f"{sub}_Result", f"{sub} Result"]:
                if candidate in df.columns:
                    res_col = candidate
                    break
            if not res_col:
                for c in df.columns:
                    if c.startswith(f"{sub} - ") and c.endswith(" Result"):
                        res_col = c
                        break
        if not res_col or res_col not in df.columns:
            continue
        results = df[res_col].dropna().astype(str).str.strip().str.upper()
        results = results[results != ""]
        appeared = len(results)
        passed = results.str.startswith("P").sum()
        failed = appeared - passed
        pass_pct = round(passed / max(appeared, 1) * 100, 1)
        subj_data.append([sub, str(appeared), str(passed), str(failed), f"{pass_pct}%"])

    if len(subj_data) > 1:
        subj_table = Table(subj_data, colWidths=[120, 80, 80, 80, 80])
        subj_table.setStyle(_build_table_style())
        story.append(subj_table)

    # Footer
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=6))
    story.append(Paragraph(
        "Generated by VTU Student Performance Dashboard",
        styles["SmallRight"]
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info("Generated class summary PDF: %d students, %d subjects", len(df), len(subject_codes))
    return pdf_bytes


def generate_complete_report_pdf(sheets_dict, institution_name=""):
    """
    Generate a comprehensive multi-page PDF that mirrors the Excel download.

    Parameters
    ----------
    sheets_dict : dict
        Keys are sheet names, values are pd.DataFrames.
        Expected keys (all optional): 'Summary', 'Overview', 'Ranking (Marks)',
        'Ranking (SGPA)', 'Subject Analysis', 'Category Breakdown',
        plus any KPI breakdown sheets like 'Passed', 'Failed', etc.
    institution_name : str
        Institution name for header.

    Returns
    -------
    bytes : PDF file content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=12*mm, bottomMargin=12*mm,
                            leftMargin=10*mm, rightMargin=10*mm)
    styles = _get_styles()
    # Small cell style for wrapping long text (used for wide tables)
    cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7,
                                leading=9, alignment=TA_LEFT)
    cell_style_center = ParagraphStyle('CellCenter', parent=styles['Normal'], fontSize=7,
                                       leading=9, alignment=TA_CENTER)
    header_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=7,
                                  leading=9, alignment=TA_CENTER, textColor=HEADER_TEXT,
                                  fontName='Helvetica-Bold')

    # Larger styles for Summary & Subject Analysis pages
    cell_style_lg = ParagraphStyle('CellStyleLg', parent=styles['Normal'], fontSize=10,
                                   leading=13, alignment=TA_LEFT)
    cell_style_center_lg = ParagraphStyle('CellCenterLg', parent=styles['Normal'], fontSize=10,
                                          leading=13, alignment=TA_CENTER)
    header_style_lg = ParagraphStyle('HeaderCellLg', parent=styles['Normal'], fontSize=10,
                                     leading=13, alignment=TA_CENTER, textColor=HEADER_TEXT,
                                     fontName='Helvetica-Bold')

    PAGE_W = landscape(A4)[0] - 20*mm  # available width

    story = []

    # ── Title ──
    story.append(Paragraph("Complete Performance Report", styles["TitleCenter"]))
    if institution_name:
        story.append(Paragraph(institution_name, styles["SubtitleCenter"]))
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles["SmallRight"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_COLOR, spaceAfter=10))

    # ── Report summary info ──
    _ov = sheets_dict.get('Overview')
    _sa = sheets_dict.get('Subject Analysis')
    _summary = sheets_dict.get('Summary')
    _info_parts = []
    if isinstance(_ov, pd.DataFrame) and not _ov.empty:
        _info_parts.append(f"<b>Total Students:</b> {len(_ov)}")
    if isinstance(_sa, pd.DataFrame) and not _sa.empty:
        _info_parts.append(f"<b>Subjects:</b> {len(_sa)}")
    _info_parts.append(f"<b>Sheets:</b> {len(sheets_dict)}")
    if isinstance(_summary, dict):
        _pp = _summary.get('Pass %', '')
        if _pp:
            _info_parts.append(f"<b>Pass %:</b> {_pp}")
    if _info_parts:
        _info_style = ParagraphStyle('InfoLine', parent=styles['Normal'], fontSize=9,
                                     leading=13, alignment=TA_LEFT, textColor=colors.HexColor('#374151'))
        story.append(Paragraph(' &nbsp;&nbsp;|&nbsp;&nbsp; '.join(_info_parts), _info_style))
        story.append(Spacer(1, 6))

    # ── Table of Contents ──
    _toc_items = []
    _toc_map = [
        ('Summary', 'Performance Overview'),
        ('Subject Analysis', 'Subject Analysis'),
        ('Overview', 'Student Overview'),
        ('Ranking (Marks)', 'Ranking (Marks)'),
        ('Ranking (SGPA)', 'Ranking (SGPA)'),
        ('Category Breakdown', 'Category Breakdown'),
    ]
    for _key, _label in _toc_map:
        _v = sheets_dict.get(_key)
        if _v is not None and (isinstance(_v, dict) or (isinstance(_v, pd.DataFrame) and not _v.empty)):
            _toc_items.append(_label)
    # KPI breakdown sheets
    for _name in ['Total Students', 'Appeared', 'Absent', 'Passed', 'Failed',
                  '1 Subject Fail', '2 Subject Fails', '3+ Subject Fails',
                  'First Class Distinction', 'First Class', 'Second Class']:
        _v = sheets_dict.get(_name)
        if isinstance(_v, pd.DataFrame) and not _v.empty:
            _toc_items.append(_name)
    if _toc_items:
        _toc_style = ParagraphStyle('TOCStyle', parent=styles['Normal'], fontSize=8,
                                    leading=11, alignment=TA_LEFT, textColor=colors.HexColor('#6b7280'))
        _toc_text = '<b>Contents:</b> ' + ' &nbsp;&#8226;&nbsp; '.join(_toc_items)
        story.append(Paragraph(_toc_text, _toc_style))
        story.append(Spacer(1, 8))

    # Helper: build a styled table from a DataFrame
    def _df_to_table(df, title, col_widths=None, color_result=True, max_col_width=None, large=False):
        """Convert a DataFrame to a styled ReportLab Table with Paragraph-wrapped cells."""
        if df is None or df.empty:
            return

        cols = list(df.columns)
        n_cols = len(cols)

        # ── Desired widths per column ──
        MIN_COL_W = 30  # absolute minimum before splitting

        def _desired_widths(col_list):
            w = []
            for c in col_list:
                cl = c.lower()
                if 'subject' in cl and 'fail' in cl:
                    w.append(max(180, PAGE_W * 0.25))
                elif cl == 'name':
                    w.append(90)
                elif any(k in cl for k in ['student', 'usn', 'seat', 'university']):
                    w.append(80)
                elif cl == 'category':
                    w.append(120)
                elif cl == 'section':
                    w.append(50)
                else:
                    w.append(48)
            total = sum(w)
            if total != PAGE_W and total > 0:
                scale = PAGE_W / total
                w = [round(x * scale, 1) for x in w]
            return w

        auto_widths = _desired_widths(cols) if col_widths is None else list(col_widths)
        min_w = min(auto_widths) if auto_widths else 50

        # If columns are too narrow, split into multiple tables
        if min_w < MIN_COL_W and n_cols > 8:
            # Identify identity columns (first 3 non-subject cols) to repeat in each chunk
            id_cols = []
            data_cols = []
            for c in cols:
                cl = c.lower()
                if len(id_cols) < 3 and any(k in cl for k in ['student', 'usn', 'seat', 'university', 'name', 'section']):
                    id_cols.append(c)
                else:
                    data_cols.append(c)
            if not id_cols:
                id_cols = cols[:1]
                data_cols = cols[1:]

            # Determine how many data cols fit per chunk alongside id cols
            id_w = sum(_desired_widths(id_cols))
            remaining = PAGE_W - id_w
            per_data_col = max(remaining / max(len(data_cols), 1), MIN_COL_W)
            cols_per_chunk = max(int(remaining / per_data_col), 1)

            story.append(Paragraph(title, styles["SectionHeader"]))
            for chunk_start in range(0, len(data_cols), cols_per_chunk):
                chunk_data = data_cols[chunk_start:chunk_start + cols_per_chunk]
                chunk_cols = id_cols + chunk_data
                chunk_df = df[chunk_cols]
                chunk_widths = _desired_widths(chunk_cols)
                # Recurse with the chunk (will not re-split since it fits)
                _df_to_table(chunk_df, f"{title} (cols {chunk_start+1}–{chunk_start+len(chunk_data)})",
                             col_widths=chunk_widths, color_result=color_result)
            return

        col_widths = auto_widths

        story.append(Paragraph(title, styles["SectionHeader"]))

        # Pick font styles based on large flag
        _hs = header_style_lg if large else header_style
        _cs = cell_style_center_lg if large else cell_style_center

        # Build header row with Paragraphs
        header_row = [Paragraph(str(c), _hs) for c in cols]

        # Find result column index for coloring
        res_idx = None
        if color_result:
            for idx, c in enumerate(cols):
                if 'result' in c.lower():
                    res_idx = idx
                    break

        # Build data rows
        table_data = [header_row]
        for _, row in df.iterrows():
            r = []
            for c in cols:
                val = row.get(c, '')
                # row.get can return a Series if duplicate cols exist; grab first scalar
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                try:
                    is_na = pd.isna(val)
                except (ValueError, TypeError):
                    is_na = False
                if is_na:
                    val = '-'
                elif c.lower() in ('percentage', 'percentage (%)') or c == 'Pass %':
                    try:
                        v = float(val)
                        val = f"{v:.2f}%" if '%' not in str(val) else str(val)
                    except (ValueError, TypeError):
                        val = str(val)
                else:
                    val = str(val)
                r.append(Paragraph(val, _cs))
            table_data.append(r)

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        base = _build_table_style()
        t.setStyle(base)

        # Color pass/fail/absent rows
        if res_idx is not None:
            for i, row_data in enumerate(table_data[1:], 1):
                # Extract text from Paragraph
                try:
                    val = df.iloc[i-1][cols[res_idx]]
                    val = str(val).strip().upper() if pd.notna(val) else ''
                except (IndexError, KeyError):
                    val = ''
                if val in ['F', 'FAIL']:
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fef2f2")),
                    ]))
                elif val in ['A', 'ABSENT']:
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fffbeb")),
                    ]))

        story.append(t)
        story.append(Spacer(1, 10))

    def _kpi_table(kpi_dict, title="Performance Overview"):
        """Render KPI summary as a styled 2-column table."""
        if not kpi_dict:
            return
        story.append(Paragraph(title, styles["SectionHeader"]))

        # Color map for KPI rows
        kpi_colors = {
            'Total': colors.HexColor("#e0e7ff"),
            'Appeared': colors.HexColor("#dbeafe"),
            'Passed': colors.HexColor("#d1fae5"),
            'Failed': colors.HexColor("#fee2e2"),
            'Absent': colors.HexColor("#fef3c7"),
            'Pass %': colors.HexColor("#f5f3ff"),
            '1 Subject': colors.HexColor("#fee2e2"),
            '2 Subject': colors.HexColor("#fee2e2"),
            '3+': colors.HexColor("#fee2e2"),
            'First Class Distinction': colors.HexColor("#f5f3ff"),
            'First Class (': colors.HexColor("#f0f9ff"),
            'Second Class': colors.HexColor("#fffbf0"),
        }
        section_bg = colors.HexColor("#f1f5f9")

        rows = [[Paragraph("<b>Metric</b>", header_style_lg),
                 Paragraph("<b>Value</b>", header_style_lg)]]
        for k, v in kpi_dict.items():
            rows.append([Paragraph(str(k), cell_style_lg), Paragraph(str(v), cell_style_center_lg)])

        t = Table(rows, colWidths=[PAGE_W * 0.65, PAGE_W * 0.35])
        base = _build_table_style()
        t.setStyle(base)

        # Apply per-row colors
        for i, (k, v) in enumerate(kpi_dict.items(), 1):
            k_str = str(k)
            if k_str.startswith('──') or k_str.startswith('—'):
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, i), (-1, i), section_bg),
                    ("FONTNAME", (0, i), (-1, i), "Helvetica-BoldOblique"),
                ]))
            else:
                for key, clr in kpi_colors.items():
                    if key in k_str:
                        t.setStyle(TableStyle([("BACKGROUND", (0, i), (-1, i), clr)]))
                        break

        story.append(t)
        story.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════
    # Render each sheet in the same order as Excel
    # ═══════════════════════════════════════════════

    # 1. Summary (KPI dict or DataFrame)
    summary = sheets_dict.get('Summary')
    if summary is not None:
        if isinstance(summary, dict):
            _kpi_table(summary)
        elif isinstance(summary, pd.DataFrame) and not summary.empty:
            kpi_dict = {}
            for _, row in summary.iterrows():
                kpi_dict[str(row.get('Metric', ''))] = str(row.get('Value', ''))
            _kpi_table(kpi_dict)

    # 2. Subject Analysis (right after Summary) — larger font
    subj = sheets_dict.get('Subject Analysis')
    if subj is not None and not subj.empty:
        story.append(PageBreak())
        _df_to_table(subj, "Subject Analysis", large=True)

    # 3. Overview (full student data with all subjects)
    overview = sheets_dict.get('Overview')
    if overview is not None and not overview.empty:
        story.append(PageBreak())
        _df_to_table(overview, "Overview — Student Data")

    # 4. Ranking (Marks)
    ranking = sheets_dict.get('Ranking (Marks)')
    if ranking is not None and not ranking.empty:
        story.append(PageBreak())
        _df_to_table(ranking, "Ranking (Marks)")

    # 5. Ranking (SGPA)
    sgpa = sheets_dict.get('Ranking (SGPA)')
    if sgpa is not None and not sgpa.empty:
        story.append(PageBreak())
        _df_to_table(sgpa, "Ranking (SGPA)")

    # 6. Category Breakdown
    cat = sheets_dict.get('Category Breakdown')
    if cat is not None and not cat.empty:
        story.append(PageBreak())
        _df_to_table(cat, "Category Breakdown", color_result=False)

    # 7+ KPI breakdown sheets (Passed, Failed, 1 Subject Fail, FCD, etc.)
    _kpi_sheet_order = [
        'Total Students', 'Appeared', 'Absent', 'Passed', 'Failed',
        '1 Subject Fail', '2 Subject Fails', '3+ Subject Fails',
        'First Class Distinction', 'First Class', 'Second Class',
    ]
    for sheet_name in _kpi_sheet_order:
        sdf = sheets_dict.get(sheet_name)
        if sdf is not None and not sdf.empty:
            story.append(PageBreak())
            _df_to_table(sdf, f"{sheet_name} ({len(sdf)} students)")

    # Any remaining sheets not in the known order
    known = {'Summary', 'Overview', 'Ranking (Marks)', 'Ranking (SGPA)',
             'Subject Analysis', 'Category Breakdown'} | set(_kpi_sheet_order)
    for sheet_name, sdf in sheets_dict.items():
        if sheet_name not in known and isinstance(sdf, pd.DataFrame) and not sdf.empty:
            story.append(PageBreak())
            _df_to_table(sdf, f"{sheet_name} ({len(sdf)} students)")

    # ── Footer ──
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=6))
    story.append(Paragraph("Generated by VTU Student Performance Dashboard", styles["SmallRight"]))
    story.append(Paragraph("This report is auto-generated and confidential.", styles["SmallRight"]))

    # ── Page numbering ──
    def _add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.gray)
        page_num = f"Page {canvas.getPageNumber()}"
        canvas.drawRightString(landscape(A4)[0] - 10*mm, 8*mm, page_num)
        canvas.drawString(10*mm, 8*mm, "VTU Dashboard Report")
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info("Generated complete report PDF: %d sheets", len(sheets_dict))
    return pdf_bytes


def pdf_to_download_data(pdf_bytes, filename):
    """Convert PDF bytes to Dash dcc.Download-compatible dict."""
    encoded = base64.b64encode(pdf_bytes).decode()
    return dict(
        content=encoded,
        filename=filename,
        base64=True,
        type="application/pdf"
    )
