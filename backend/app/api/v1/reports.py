"""
Reports API Endpoints: PDF, Excel, and Statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Optional

from backend.app.db.session import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.models import User, Exam, Result, Student, StudentAnswer
from backend.app.services.report_generator import (
    generate_exam_pdf_report,
    generate_student_card_pdf,
    generate_exam_excel_report
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/exam/{exam_id}/pdf")
def download_exam_pdf(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export exam evaluation summary and merit list as ReportLab PDF.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    results = db.query(Result).filter(Result.exam_id == exam_id).all()
    pdf_bytes = generate_exam_pdf_report(exam, results)

    filename = f"Exam_Report_{exam.code}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/exam/{exam_id}/excel")
def download_exam_excel(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export candidate roster, marks, and statistics as openpyxl Excel (.xlsx).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    results = db.query(Result).filter(Result.exam_id == exam_id).all()
    excel_bytes = generate_exam_excel_report(exam, results)

    filename = f"Exam_Results_{exam.code}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/result/{result_id}/pdf")
def download_result_pdf(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Download individual candidate scorecard PDF with item response grid.
    """
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    student = db.query(Student).filter(Student.id == result.student_id).first()
    exam = db.query(Exam).filter(Exam.id == result.exam_id).first()
    answers = db.query(StudentAnswer).filter(StudentAnswer.result_id == result.id).order_by(StudentAnswer.question_no.asc()).all()

    pdf_bytes = generate_student_card_pdf(exam, student, result, answers)
    filename = f"Scorecard_{student.roll_no}_{exam.code}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
