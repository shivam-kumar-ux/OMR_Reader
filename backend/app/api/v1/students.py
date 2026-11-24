from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user
from backend.app.db.session import get_db
from backend.app.models.models import Student, Result, Exam, User

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("")
def search_students(
    q: Optional[str] = Query(None, description="Search query for roll no, name, or mobile"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search students by roll number, name, or mobile phone.
    """
    query = db.query(Student)
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            (Student.roll_no.ilike(term)) |
            (Student.name_final.ilike(term)) |
            (Student.mobile_final.ilike(term))
        )
    students = query.order_by(Student.id.desc()).offset(skip).limit(limit).all()

    result = []
    for s in students:
        result.append({
            "id": s.id,
            "roll_no": s.roll_no,
            "name_final": s.name_final,
            "name_bubble": s.name_bubble,
            "name_ocr": s.name_ocr,
            "father_name_final": s.father_name_final,
            "mobile_final": s.mobile_final,
            "dob_final": s.dob_final,
            "class_name_final": s.class_name_final,
            "verified_flag": s.verified_flag,
            "created_at": s.created_at,
        })
    return result


@router.get("/{student_id}")
def get_student_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve comprehensive profile of a student including all exam results,
    scores, and scanned sheet image references.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    results = (
        db.query(Result)
        .filter(Result.student_id == student.id)
        .order_by(Result.id.desc())
        .all()
    )

    exam_records = []
    for r in results:
        exam_records.append({
            "result_id": r.id,
            "exam_id": r.exam_id,
            "exam_name": r.exam.name,
            "exam_code": r.exam.code,
            "set_code": r.set_code,
            "total_score": r.total_score,
            "percentage": r.percentage,
            "correct_count": r.correct_count,
            "wrong_count": r.wrong_count,
            "not_attempted_count": r.not_attempted_count,
            "multi_marked_count": r.multi_marked_count,
            "status": r.status,
            "confidence_score": r.confidence_score,
            "sheet_image_path": r.sheet_image_path,
            "processed_image_path": r.processed_image_path,
            "created_at": r.created_at,
        })

    return {
        "id": student.id,
        "roll_no": student.roll_no,
        "name_final": student.name_final,
        "name_bubble": student.name_bubble,
        "name_ocr": student.name_ocr,
        "father_name_final": student.father_name_final,
        "father_name_ocr": student.father_name_ocr,
        "mobile_final": student.mobile_final,
        "dob_final": student.dob_final,
        "class_name_final": student.class_name_final,
        "verified_flag": student.verified_flag,
        "verified_by_user_id": student.verified_by_user_id,
        "created_at": student.created_at,
        "results": exam_records,
    }
