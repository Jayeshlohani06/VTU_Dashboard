"""
PDF Report Generator for VTU Dashboard.
Generates styled PDF reports for individual students, class summaries,
and subject analysis using ReportLab.
"""

import io
import base64
import uuid
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
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
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
    styles.add(ParagraphStyle(
        "SmallMuted", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#6b7280"), leading=10
    ))
    styles.add(ParagraphStyle(
        "AlertText", parent=styles["Normal"],
        fontSize=9, textColor=FAIL_COLOR, leading=12
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
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("MINHEIGHT", (0, 0), (-1, -1), 20),
    ]
    return TableStyle(style)
def generate_student_report_pdf(student_row, subject_codes, institution_name="", report_meta=None):
    """Generate a proper marks-card style PDF for an individual student."""
    buffer = io.BytesIO()
    page_w, _page_h = A4
    left_m = right_m = 12 * mm
    content_w = page_w - left_m - right_m
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=8 * mm,
        bottomMargin=8 * mm,
        leftMargin=left_m,
        rightMargin=right_m,
    )
    styles = _get_styles()
    story = []

    # Palette
    indigo = colors.HexColor("#1a237e")
    indigo_mid = colors.HexColor("#283593")
    indigo_lite = colors.HexColor("#e8eaf6")
    border_c = colors.HexColor("#3949ab")
    grid_c = colors.HexColor("#c5cae9")
    alt_c = colors.HexColor("#f7f7fb")
    pass_c = colors.HexColor("#2e7d32")
    fail_c = colors.HexColor("#c62828")
    pass_bg_c = colors.HexColor("#e8f5e9")
    fail_bg_c = colors.HexColor("#ffebee")
    gray_fg = colors.HexColor("#6b7280")
    dark_fg = colors.HexColor("#1f2937")

    generated_at = datetime.now()
    generation_id = f"RC-{generated_at.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    def _is_blank(v):
        return str(v).strip().lower() in ("", "nan", "none", "-", "--")

    def _to_num(v):
        return pd.to_numeric(v, errors="coerce")

    def _fmt_mark(v):
        n = _to_num(v)
        if pd.isna(n):
            return "-"
        return str(int(n)) if float(n).is_integer() else f"{float(n):.1f}"

    def _rank_str(v):
        try:
            f = float(v)
            return str(int(f)) if float(f).is_integer() else f"{f:.2f}"
        except Exception:
            return str(v) if str(v).strip() else "-"

    def _resolve(row_obj, subject_key, component):
        for c in [f"{subject_key}_{component}", f"{subject_key} {component}"]:
            if c in row_obj:
                return row_obj.get(c)
        if " - " in str(subject_key):
            code = str(subject_key).split(" - ", 1)[0].strip()
            for key in row_obj.keys():
                key_s = str(key)
                if key_s.startswith(f"{code} - ") and key_s.endswith(f" {component}"):
                    return row_obj.get(key)
        return None

    def _extract_course_number(subject_code):
        m = re.search(r"(\d{3})", str(subject_code))
        return m.group(1) if m else None

    def _grade_from_total(total_num):
        if pd.isna(total_num):
            return "-", None
        v = float(total_num)
        if v >= 90:
            return "O", 10
        if v >= 80:
            return "A+", 9
        if v >= 70:
            return "A", 8
        if v >= 60:
            return "B+", 7
        if v >= 55:
            return "B", 6
        if v >= 50:
            return "C", 5
        if v >= 40:
            return "P", 4
        return "F", 0

    credit_map = student_row.get("Credit_Map") or student_row.get("Subject_Credit_Map") or {}

    def _get_credit(sub_code):
        if not isinstance(credit_map, dict):
            return None
        candidates = [str(sub_code).strip()]
        if " - " in str(sub_code):
            candidates.append(str(sub_code).split(" - ", 1)[0].strip())
        cn = _extract_course_number(sub_code)
        if cn:
            candidates.append(cn)
        for k in candidates:
            if k in credit_map:
                n = _to_num(credit_map.get(k))
                if pd.notna(n):
                    return float(n)
        return None

    sid = str(student_row.get("Student ID", student_row.get("Student_ID", "N/A")))
    name = str(student_row.get("Name", "N/A"))
    section = str(student_row.get("Section", "-"))
    overall = str(student_row.get("Overall_Result", "-")).strip()
    total_marks = str(student_row.get("Total_Marks", "-"))
    class_rank = _rank_str(student_row.get("Class_Rank", ""))
    section_rank = _rank_str(student_row.get("Section_Rank", ""))

    report_meta = report_meta or {}

    def _derive_college_code_from_usn(usn_val):
        usn_text = str(usn_val or "").strip().upper()
        m = re.match(r"^\d([A-Z]{2})\d{2}[A-Z]{2}\d+", usn_text)
        if m:
            return m.group(1)
        m2 = re.match(r"^\d([A-Z]{2})", usn_text)
        if m2:
            return m2.group(1)
        return "-"

    semester_val = report_meta.get("semester", student_row.get("Semester", student_row.get("Current Semester", "-")))
    scheme_val = report_meta.get("scheme", student_row.get("Scheme", student_row.get("Academic Scheme", "-")))
    semester = str(semester_val) if semester_val is not None else "-"
    scheme = str(scheme_val) if scheme_val is not None else "-"
    exam_month = str(student_row.get("Exam Month", student_row.get("Exam_Month", generated_at.strftime("%b"))))
    exam_year = str(student_row.get("Exam Year", student_row.get("Exam_Year", generated_at.strftime("%Y"))))
    college_code = str(student_row.get("College Code", student_row.get("College_Code", ""))).strip()
    if not college_code:
        college_code = _derive_college_code_from_usn(sid)

    sgpa_n = _to_num(str(student_row.get("Calculated_SGPA", "")).replace("%", ""))
    sgpa_str = f"{float(sgpa_n):.2f}" if pd.notna(sgpa_n) else "N/A"
    perc_n = _to_num(str(student_row.get("Calculated_Percentage", "")).replace("%", ""))
    perc_str = f"{float(perc_n):.2f}%" if pd.notna(perc_n) else "N/A"

    analysis_type = student_row.get("Analysis_Type", "Total")
    class_avg_map = student_row.get("Class_Avg_Map", {})
    class_max_map = student_row.get("Class_Max_Map", {})

    subject_rows = []
    chart_labels = []
    chart_values = []
    avg_values = []
    max_values = []
    failed_subjects = []
    attempted = 0
    passed = 0
    total_credits = 0.0
    total_credit_points = 0.0

    for sub in subject_codes:
        int_val = _resolve(student_row, sub, "Internal")
        ext_val = _resolve(student_row, sub, "External")
        tot_val = _resolve(student_row, sub, "Total")
        res_val = _resolve(student_row, sub, "Result")

        code_only = str(sub).split(" - ", 1)[0].strip()
        subj_name = str(sub).split(" - ", 1)[1].strip() if " - " in str(sub) else str(sub)
        int_num = _to_num(int_val)
        ext_num = _to_num(ext_val)
        total_num = _to_num(tot_val)
        res_norm = str(res_val).strip().upper() if not _is_blank(res_val) else ""

        # Keep only subjects actually present/attempted by this student.
        # This removes placeholder rows like '-', '-', 0, '-' from the marks card.
        has_positive_marks = any(
            pd.notna(v) and float(v) > 0 for v in [int_num, ext_num, total_num]
        )
        has_explicit_result = res_norm in ("P", "PASS", "F", "FAIL", "A", "ABSENT", "NE", "X", "RV")
        if (not has_positive_marks) and (not has_explicit_result):
            continue

        grade, gp = _grade_from_total(total_num)
        if res_norm in ("F", "FAIL"):
            grade, gp = "F", 0
        elif res_norm in ("A", "ABSENT"):
            grade, gp = "A", None
        elif res_norm in ("NE", "X", "RV"):
            grade, gp = res_norm, None

        credit = _get_credit(sub)
        cp = None
        if credit is not None and gp is not None:
            cp = float(credit) * float(gp)

        if pd.notna(total_num) or res_norm in ("P", "PASS", "F", "FAIL", "A", "ABSENT", "NE", "X", "RV"):
            attempted += 1
        if res_norm in ("P", "PASS") or (res_norm == "" and grade not in ("F", "A", "NE", "X", "RV")):
            passed += 1
        if res_norm in ("F", "FAIL") or grade == "F":
            failed_subjects.append(code_only)

        if credit is not None and gp is not None:
            total_credits += float(credit)
            total_credit_points += float(cp)

        subject_rows.append({
            "serial": len(subject_rows) + 1,
            "code": code_only,
            "name": subj_name,
            "int": _fmt_mark(int_val),
            "ext": _fmt_mark(ext_val),
            "total": _fmt_mark(tot_val),
            "result": res_norm or "-",
            "res_norm": res_norm,
            "grade": grade,
            "gp": "-" if gp is None else str(gp),
            "credit": "-" if credit is None else f"{float(credit):.1f}".rstrip("0").rstrip("."),
            "cp": "-" if cp is None else f"{float(cp):.2f}",
        })

        if pd.notna(total_num) and total_num > 0:
            chart_labels.append(code_only)
            chart_values.append(float(total_num))
            kpi_key = f"{sub} {analysis_type}"
            av = class_avg_map.get(kpi_key, 0)
            mx = class_max_map.get(kpi_key, 0)
            avg_values.append(float(av) if not pd.isna(av) else 0.0)
            max_values.append(float(mx) if not pd.isna(mx) else 0.0)

    overall_norm = str(overall).strip().upper()
    is_pass_overall = overall_norm in ("P", "PASS")

    # Match Ranking page rule: class categories are for PASS students only.
    if is_pass_overall and pd.notna(perc_n) and float(perc_n) >= 70:
        class_text = "First Class with Distinction"
    elif is_pass_overall and pd.notna(perc_n) and float(perc_n) >= 60:
        class_text = "First Class"
    elif is_pass_overall and pd.notna(perc_n) and float(perc_n) >= 50:
        class_text = "Second Class"
    elif is_pass_overall:
        class_text = "Pass Class"
    else:
        class_text = "-"

    if str(overall).strip().upper().startswith("F") and failed_subjects:
        remarks_text = f"Reappear in subject(s): {', '.join(sorted(set(failed_subjects)))}"
    elif str(overall).strip().upper().startswith("P"):
        remarks_text = "Eligible for promotion to next semester"
    else:
        remarks_text = "Refer to subject result status"

    def _band(title):
        t = Table([[Paragraph(
            f'<b><font size="8.5" color="white">{title}</font></b>',
            ParagraphStyle("band", parent=styles["Normal"], leading=11)
        )]], colWidths=[content_w])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), indigo_mid),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        return t

    # Official header
    top_head = Table([
        [
            Paragraph(
                f'<b><font size="11" color="#111827">{institution_name or "VISVESVARAYA TECHNOLOGICAL UNIVERSITY"}</font></b><br/>'
                f'<font size="8" color="#374151">OFFICIAL STUDENT MARKS CARD</font><br/>'
                f'<font size="7" color="#6b7280">College Code: {college_code}  |  Semester: {semester}  |  Scheme: {scheme}  |  Exam: {exam_month} {exam_year}</font>',
                ParagraphStyle("ct", parent=styles["Normal"], alignment=TA_CENTER, leading=11),
            )
        ]
    ], colWidths=[content_w])
    top_head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.8, border_c),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(top_head)
    story.append(Spacer(1, 2))

    # Security/meta strip
    meta_strip = Table([[
        Paragraph(
            f'<font size="7" color="white">Generation ID: {generation_id}  |  Generated: {generated_at.strftime("%d-%m-%Y %I:%M %p")}</font>',
            ParagraphStyle("ms", parent=styles["Normal"], alignment=TA_LEFT, leading=9),
        )
    ]], colWidths=[content_w])
    meta_strip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), indigo),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(meta_strip)
    story.append(Spacer(1, 2))

    # Student details
    label_style = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=7.5, textColor=gray_fg, fontName="Helvetica-Bold", leading=9)
    value_style = ParagraphStyle("val", parent=styles["Normal"], fontSize=9, textColor=dark_fg, fontName="Helvetica-Bold", leading=11)

    def _lp(text):
        return Paragraph(text, label_style)

    def _vp(text):
        return Paragraph(str(text), value_style)

    info_tbl = Table([
        [_lp("USN / STUDENT ID"), _vp(sid), _lp("STUDENT NAME"), _vp(name)],
        [_lp("SECTION"), _vp(section), _lp("OVERALL RESULT"), _vp(overall or "-")],
        [_lp("CLASS RANK"), _vp(class_rank), _lp("SECTION RANK"), _vp(section_rank)],
    ], colWidths=[78, 165, 78, content_w - 321])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), indigo_lite),
        ("BACKGROUND", (2, 0), (2, -1), indigo_lite),
        ("GRID", (0, 0), (-1, -1), 0.5, grid_c),
        ("BOX", (0, 0), (-1, -1), 1, border_c),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 2))

    # KPI strip
    kpi_tbl = Table([
        ["SGPA", "Percentage", "Total Marks", "Class"],
        [sgpa_str, perc_str, total_marks, class_text],
    ], colWidths=[content_w / 4] * 4)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), indigo_lite),
        ("TEXTCOLOR", (0, 0), (-1, 0), dark_fg),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, grid_c),
        ("BOX", (0, 0), (-1, -1), 1, border_c),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 2))

    if str(overall).upper().startswith("F") and failed_subjects:
        fail_box = Table([[Paragraph(
            f'<b>&#9888; Result Alert:</b> FAIL in subject(s): {", ".join(sorted(set(failed_subjects)))}',
            ParagraphStyle("fb", parent=styles["Normal"], textColor=fail_c, fontSize=8.5, leading=11)
        )]], colWidths=[content_w])
        fail_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), fail_bg_c),
            ("BOX", (0, 0), (-1, -1), 0.8, fail_c),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(fail_box)
        story.append(Spacer(1, 2))

    story.append(_band("SUBJECT-WISE MARKS (IA/SEE/TOTAL)"))

    # Proper report card columns including grade points and credits
    # widths sum to content_w: 20,48,132,35,35,40,34,26,34,42,53
    col_w = [20, 48, 132, 35, 35, 40, 34, 26, 34, 42, 53]
    table_data = [[
        "#", "Code", "Subject Name", "IA", "SEE", "Total",
        "Result", "Grade", "GP", "Credits", "Cr.Pts"
    ], [
        "", "", "", "Max 50", "Max 50", "Max 100", "", "", "", "", ""
    ]]

    for r in subject_rows:
        name_cell = Paragraph(
            f'<font size="7.8">{r["name"] or r["code"]}</font>',
            ParagraphStyle("nm", parent=styles["Normal"], alignment=TA_LEFT, leading=9)
        )
        table_data.append([
            str(r["serial"]),
            r["code"],
            name_cell,
            r["int"],
            r["ext"],
            r["total"],
            r["result"],
            r["grade"],
            r["gp"],
            r["credit"],
            r["cp"],
        ])

    if len(table_data) > 2:
        marks_tbl = Table(table_data, colWidths=col_w)
        ts = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), indigo),
            ("BACKGROUND", (0, 1), (-1, 1), indigo_mid),
            ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7.3),
            ("FONTSIZE", (0, 1), (-1, 1), 6.7),
            ("FONTSIZE", (0, 2), (-1, -1), 7.8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (2, 2), (2, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.45, grid_c),
            ("ROWBACKGROUNDS", (0, 2), (-1, -1), [colors.white, alt_c]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
        for idx, r in enumerate(subject_rows, start=2):
            rr = r["res_norm"]
            if rr.startswith("P") or r["grade"] in ("O", "A+", "A", "B+", "B", "C", "P"):
                ts.add("TEXTCOLOR", (6, idx), (7, idx), pass_c)
            if rr.startswith("F") or r["grade"] == "F":
                ts.add("TEXTCOLOR", (6, idx), (7, idx), fail_c)
                ts.add("BACKGROUND", (6, idx), (7, idx), fail_bg_c)
            if rr in ("A", "ABSENT", "NE", "X", "RV"):
                ts.add("TEXTCOLOR", (6, idx), (6, idx), colors.HexColor("#b45309"))
        marks_tbl.setStyle(ts)
        story.append(marks_tbl)
    else:
        story.append(Paragraph("No subject data available.", styles["Normal"]))

    story.append(Spacer(1, 2))

    # Chart kept compact for one-page friendly layout
    if chart_values and len(subject_rows) <= 10:
        story.append(_band("PERFORMANCE SNAPSHOT"))
        has_stats = any(v > 0 for v in avg_values) and any(v > 0 for v in max_values)
        drawing = Drawing(content_w, 115)
        chart = VerticalBarChart()
        chart.x = 20
        chart.y = 18
        chart.height = 78
        chart.width = int(content_w) - 34
        chart.data = [chart_values, avg_values, max_values] if has_stats else [chart_values]
        chart.categoryAxis.categoryNames = [f"S{i+1}" for i in range(len(chart_labels))]
        chart.categoryAxis.labels.fontSize = 6.5
        chart.categoryAxis.labels.dy = -8
        chart.valueAxis.valueMin = 0
        top_max = max(chart_values + (max_values if has_stats else []))
        chart.valueAxis.valueMax = max(100, int(top_max) + 10)
        chart.valueAxis.valueStep = 10
        chart.valueAxis.labels.fontSize = 6
        chart.bars[0].fillColor = colors.HexColor("#3f51b5")
        if has_stats:
            chart.bars[1].fillColor = colors.HexColor("#26a69a")
            chart.bars[2].fillColor = colors.HexColor("#ffa726")
        chart.barLabelFormat = "%d"
        chart.barLabels.fontSize = 5.5
        chart.barLabels.nudge = 4
        drawing.add(chart)
        story.append(drawing)
        legend_text = " | ".join([f"S{i+1}={c}" for i, c in enumerate(chart_labels)])
        story.append(Paragraph(
            f'<font size="6.5" color="#6b7280">{legend_text}</font>',
            ParagraphStyle("cl", parent=styles["Normal"], alignment=TA_CENTER, leading=8),
        ))
        story.append(Spacer(1, 2))

    # Result remarks + notation legend
    remarks_tbl = Table([
        [
            Paragraph(f'<font size="7.5"><b>Remarks:</b> {remarks_text}</font>', ParagraphStyle("rm", parent=styles["Normal"], leading=10)),
            Paragraph('<font size="7"><b>Legend:</b> A=Absent, NE=Not Eligible, X=Withheld, RV=Revaluation</font>', ParagraphStyle("lgd", parent=styles["Normal"], leading=10)),
        ]
    ], colWidths=[content_w * 0.6, content_w * 0.4])
    remarks_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(remarks_tbl)
    story.append(Spacer(1, 2))

    # Signature area for acknowledgement
    sign_tbl = Table([[
        Paragraph('<font size="7" color="#e2e8f0">_________________________<br/>Student Signature</font>', ParagraphStyle("s1", parent=styles["Normal"], alignment=TA_CENTER, leading=10)),
        Paragraph('<font size="7" color="#e2e8f0">_________________________<br/>Parent / Guardian</font>', ParagraphStyle("s2", parent=styles["Normal"], alignment=TA_CENTER, leading=10)),
        Paragraph('<font size="7" color="#e2e8f0">_________________________<br/>Class Advisor / HOD</font>', ParagraphStyle("s3", parent=styles["Normal"], alignment=TA_CENTER, leading=10)),
        Paragraph('<font size="7" color="#e2e8f0">_________________________<br/>Principal</font>', ParagraphStyle("s4", parent=styles["Normal"], alignment=TA_CENTER, leading=10)),
    ]], colWidths=[content_w / 4] * 4)
    sign_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), indigo),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER", (0, 0), (2, -1), 0.5, border_c),
    ]))
    story.append(sign_tbl)

    def _page_decor(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 42)
        canvas.setFillColor(colors.Color(0.78, 0.8, 0.9, alpha=0.12))
        canvas.translate(page_w / 2, 210)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "PROVISIONAL")
        canvas.restoreState()

    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.info("Generated proper marks card PDF for %s", sid)
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
