"""
Report Generator Service using ReportLab (PDF) and openpyxl (Excel).
Produces high-quality executive summaries, candidate ranks, and student scorecards.
"""

import io
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, KeepTogether

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.app.models.models import Exam, Student, Result, StudentAnswer


def generate_exam_pdf_report(exam: Exam, results: List[Result]) -> bytes:
    """
    Generate an Exam Summary and Merit List PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=14
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    header_cell_style = ParagraphStyle(
        'HeaderCellText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    elements = []

    # Title & Metadata
    elements.append(Paragraph(f"OMR Evaluation Report: {exam.name}", title_style))
    elements.append(Paragraph(
        f"Exam Code: <b>{exam.code}</b> &bull; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &bull; Total Candidates: {len(results)}",
        subtitle_style
    ))

    # Compute Aggregates
    scores = [r.total_score for r in results if r.total_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    max_score = round(max(scores), 2) if scores else 0.0
    min_score = round(min(scores), 2) if scores else 0.0
    auto_accepted_cnt = sum(1 for r in results if r.status == "AUTO_ACCEPTED")
    review_cnt = sum(1 for r in results if r.status == "NEEDS_REVIEW")

    # Overview Cards Table
    stats_data = [
        [
            Paragraph(f"<b>Total Processed</b><br/>{len(results)} Sheets", cell_style),
            Paragraph(f"<b>Highest Score</b><br/>{max_score} / {exam.total_questions * exam.marks_per_correct}", cell_style),
            Paragraph(f"<b>Average Score</b><br/>{avg_score}", cell_style),
            Paragraph(f"<b>Lowest Score</b><br/>{min_score}", cell_style),
            Paragraph(f"<b>Auto Accepted</b><br/>{auto_accepted_cnt}", cell_style),
            Paragraph(f"<b>Needs Review</b><br/>{review_cnt}", cell_style),
        ]
    ]
    stats_table = Table(stats_data, colWidths=[85, 90, 85, 85, 85, 85])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 16))

    # Merit List Table
    elements.append(Paragraph("<b>Candidate Merit & Score Roster</b>", styles['Heading3']))
    elements.append(Spacer(1, 8))

    # Sort results by score descending
    sorted_results = sorted(results, key=lambda x: (x.total_score or 0.0), reverse=True)

    table_data = [[
        Paragraph("Rank", header_cell_style),
        Paragraph("Roll No", header_cell_style),
        Paragraph("Candidate Name", header_cell_style),
        Paragraph("Set", header_cell_style),
        Paragraph("Score", header_cell_style),
        Paragraph("Correct", header_cell_style),
        Paragraph("Wrong", header_cell_style),
        Paragraph("Blank", header_cell_style),
        Paragraph("Confidence", header_cell_style),
        Paragraph("Status", header_cell_style),
    ]]

    for rank, res in enumerate(sorted_results, 1):
        st = res.student
        name_str = st.name_final or "N/A"
        roll_str = st.roll_no or "N/A"
        conf_val = getattr(res, 'confidence_score', getattr(res, 'overall_confidence', 0.0))
        conf_str = f"{int((conf_val or 0.0) * 100)}%"
        status_str = res.status or "PROCESSED"
        unatt_cnt = getattr(res, 'not_attempted_count', getattr(res, 'unattempted_count', 0))
        
        table_data.append([
            Paragraph(str(rank), cell_style),
            Paragraph(roll_str, cell_style),
            Paragraph(name_str[:22], cell_style),
            Paragraph(res.set_code or "A", cell_style),
            Paragraph(f"<b>{res.total_score or 0.0}</b>", cell_style),
            Paragraph(str(res.correct_count or 0), cell_style),
            Paragraph(str(res.wrong_count or 0), cell_style),
            Paragraph(str(unatt_cnt or 0), cell_style),
            Paragraph(conf_str, cell_style),
            Paragraph(status_str, cell_style),
        ])

    candidate_table = Table(
        table_data,
        colWidths=[30, 65, 120, 30, 45, 45, 45, 45, 50, 60],
        repeatRows=1
    )
    candidate_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))

    elements.append(candidate_table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_student_card_pdf(exam: Exam, student: Student, result: Result, answers: List[StudentAnswer]) -> bytes:
    """
    Generate an individual student OMR scorecard PDF with a 50-question response grid.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B')
    )
    cell_style = ParagraphStyle('C', parent=styles['Normal'], fontSize=8, leading=10)
    header_style = ParagraphStyle('H', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)

    elements = []

    # Title
    elements.append(Paragraph(f"OMR Candidate Scorecard & Verification Report", title_style))
    elements.append(Paragraph(f"Exam: <b>{exam.name}</b> ({exam.code}) &bull; Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Spacer(1, 14))

    # Student Details Box
    res_conf = getattr(result, 'confidence_score', getattr(result, 'overall_confidence', 0.0))
    res_unatt = getattr(result, 'not_attempted_count', getattr(result, 'unattempted_count', 0))
    verified_str = "YES" if student.verified_flag else "AUTO"

    stud_info = [
        [
            Paragraph(f"<b>Candidate Name:</b> {student.name_final or 'N/A'}", cell_style),
            Paragraph(f"<b>Roll Number:</b> {student.roll_no or 'N/A'}", cell_style),
            Paragraph(f"<b>Exam Set:</b> {result.set_code or 'A'}", cell_style),
        ],
        [
            Paragraph(f"<b>Father's Name:</b> {student.father_name_final or 'N/A'}", cell_style),
            Paragraph(f"<b>Mobile:</b> {student.mobile_final or 'N/A'}", cell_style),
            Paragraph(f"<b>Class / DOB:</b> {student.class_name_final or ''} / {student.dob_final or ''}", cell_style),
        ],
        [
            Paragraph(f"<b>Validation Status:</b> {result.status}", cell_style),
            Paragraph(f"<b>Overall Confidence:</b> {int((res_conf or 0.0) * 100)}%", cell_style),
            Paragraph(f"<b>Verified By:</b> {verified_str}", cell_style),
        ]
    ]
    info_table = Table(stud_info, colWidths=[200, 170, 160])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 14))

    # Score Summary Banner
    max_marks = exam.total_questions * exam.marks_per_correct
    score_pct = round(((result.total_score or 0.0) / max_marks) * 100, 1) if max_marks > 0 else 0.0
    summary_data = [
        [
            Paragraph(f"<b>Total Score</b><br/><font size='14'><b>{result.total_score}</b></font> / {max_marks}", cell_style),
            Paragraph(f"<b>Percentage</b><br/><font size='14'><b>{score_pct}%</b></font>", cell_style),
            Paragraph(f"<b>Correct</b><br/><font size='14' color='#16A34A'><b>{result.correct_count}</b></font>", cell_style),
            Paragraph(f"<b>Wrong</b><br/><font size='14' color='#DC2626'><b>{result.wrong_count}</b></font>", cell_style),
            Paragraph(f"<b>Unattempted</b><br/><font size='14' color='#64748B'><b>{res_unatt}</b></font>", cell_style),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[110, 100, 105, 105, 110])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EEF2FF')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#6366F1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#C7D2FE')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    # Answers Breakdown Grid (Split 50 questions across 2 columns: Q1-25 and Q26-50)
    elements.append(Paragraph("<b>Item-by-Item Question Responses</b>", styles['Heading4']))
    elements.append(Spacer(1, 6))

    ans_map = {a.question_no: a for a in answers}
    
    # 25 rows, 2 columns of (Q#, Marked, Correct, Status)
    grid_rows = [
        [
            Paragraph("Q#", header_style), Paragraph("Marked", header_style), Paragraph("Key", header_style), Paragraph("Result", header_style),
            Paragraph("Q#", header_style), Paragraph("Marked", header_style), Paragraph("Key", header_style), Paragraph("Result", header_style),
        ]
    ]

    for q1 in range(1, 26):
        q2 = q1 + 25
        a1 = ans_map.get(q1)
        a2 = ans_map.get(q2)

        def fmt_ans(a, q_num):
            if not a:
                return (str(q_num), "-", "-", "Blank")
            status = "Correct" if a.is_correct else ("Wrong" if a.marked_option else "Blank")
            return (str(q_num), a.marked_option or "-", "-", status)

        r1 = fmt_ans(a1, q1)
        r2 = fmt_ans(a2, q2)

        grid_rows.append([
            Paragraph(r1[0], cell_style), Paragraph(r1[1], cell_style), Paragraph(r1[2], cell_style), Paragraph(r1[3], cell_style),
            Paragraph(r2[0], cell_style), Paragraph(r2[1], cell_style), Paragraph(r2[2], cell_style), Paragraph(r2[3], cell_style),
        ])

    grid_table = Table(grid_rows, colWidths=[25, 38, 25, 45, 25, 38, 25, 45] * 2)
    grid_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(grid_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_exam_excel_report(exam: Exam, results: List[Result]) -> bytes:
    """
    Generate an openpyxl Excel spreadsheet containing Merit Roster and Executive Summary.
    """
    wb = openpyxl.Workbook()
    
    # ----------------- Sheet 1: Merit List -----------------
    ws1 = wb.active
    ws1.title = "Merit Roster"
    ws1.views.sheetView[0].showGridLines = True

    # Styling definitions
    header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    headers = [
        "Rank", "Roll No", "Candidate Name", "Father's Name", "Mobile", 
        "Class", "DOB", "Set", "Score", "Max Marks", "Percentage", 
        "Correct", "Wrong", "Unattempted", "Confidence", "Status", "Verified"
    ]

    ws1.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws1.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    sorted_results = sorted(results, key=lambda x: (x.total_score or 0.0), reverse=True)
    max_marks = exam.total_questions * exam.marks_per_correct

    for rank, res in enumerate(sorted_results, 1):
        st = res.student
        pct = round(((res.total_score or 0.0) / max_marks) * 100, 2) if max_marks > 0 else 0.0
        conf_val = getattr(res, 'confidence_score', getattr(res, 'overall_confidence', 0.0))
        conf = f"{int((conf_val or 0.0) * 100)}%"
        unatt_cnt = getattr(res, 'not_attempted_count', getattr(res, 'unattempted_count', 0))

        row = [
            rank,
            st.roll_no or "",
            st.name_final or "",
            st.father_name_final or "",
            st.mobile_final or "",
            st.class_name_final or "",
            st.dob_final or "",
            res.set_code or "A",
            res.total_score or 0.0,
            max_marks,
            pct,
            res.correct_count or 0,
            res.wrong_count or 0,
            unatt_cnt,
            conf,
            res.status or "PROCESSED",
            "YES" if getattr(st, 'verified_flag', False) else "NO"
        ]
        ws1.append(row)
        current_row = ws1.max_row
        for col_idx in range(1, len(headers) + 1):
            c = ws1.cell(row=current_row, column=col_idx)
            c.font = data_font
            c.border = thin_border
            if col_idx in [1, 2, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]:
                c.alignment = Alignment(horizontal="center", vertical="center")

    # Auto-fit columns
    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 3, 10)

    # ----------------- Sheet 2: Executive Summary -----------------
    ws2 = wb.create_sheet(title="Executive Summary")
    ws2.views.sheetView[0].showGridLines = True

    scores = [r.total_score for r in results if r.total_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    highest_score = round(max(scores), 2) if scores else 0.0
    lowest_score = round(min(scores), 2) if scores else 0.0
    auto_cnt = sum(1 for r in results if r.status == "AUTO_ACCEPTED")
    review_cnt = sum(1 for r in results if r.status == "NEEDS_REVIEW")

    summary_rows = [
        ["Exam Name", exam.name],
        ["Exam Code", exam.code],
        ["Total Questions", exam.total_questions],
        ["Marks per Question", exam.marks_per_correct],
        ["Negative Marking", exam.negative_marks],
        ["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        [],
        ["Metric", "Value"],
        ["Total Candidates Evaluated", len(results)],
        ["Highest Score", highest_score],
        ["Average Score", avg_score],
        ["Lowest Score", lowest_score],
        ["Auto Accepted Sheets", auto_cnt],
        ["Needs Review Sheets", review_cnt],
        ["Auto-Acceptance Rate", f"{round((auto_cnt / len(results) * 100), 1)}%" if results else "0%"],
    ]

    for r in summary_rows:
        ws2.append(r)

    # Style header of metrics in Sheet 2
    ws2.cell(row=8, column=1).font = Font(name="Calibri", bold=True, color="FFFFFF")
    ws2.cell(row=8, column=1).fill = header_fill
    ws2.cell(row=8, column=2).font = Font(name="Calibri", bold=True, color="FFFFFF")
    ws2.cell(row=8, column=2).fill = header_fill

    for col in ws2.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws2.column_dimensions[col_letter].width = max(max_len + 4, 16)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
