import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_operator, get_current_user
from backend.app.db.session import get_db
from backend.app.models.models import (
    Result,
    Student,
    Exam,
    AnswerKey,
    StudentAnswer,
    AuditLog,
    SheetStatus,
    User,
)
try:
    from backend.app.omr.engine import OMREngine
    from backend.app.omr.evaluator import EvaluationEngine
except Exception:
    OMREngine = None
    EvaluationEngine = None
from backend.app.schemas.scan import ConfirmReviewRequest, RecheckRequest
from backend.app.storage import get_storage_provider

router = APIRouter(prefix="/results", tags=["Results & Verification"])


@router.get("")
def list_results(
    exam_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List evaluation results with optional filtering by exam and status.
    """
    query = db.query(Result)
    if exam_id:
        query = query.filter(Result.exam_id == exam_id)
    if status:
        query = query.filter(Result.status == status)

    total = query.count()
    results = query.order_by(Result.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for r in results:
        items.append({
            "id": r.id,
            "student_id": r.student_id,
            "exam_id": r.exam_id,
            "student_name": r.student.name_final if r.student else None,
            "student_roll": r.student.roll_no if r.student else None,
            "exam_name": r.exam.name if r.exam else None,
            "set_code": r.set_code,
            "total_score": r.total_score,
            "correct_count": r.correct_count,
            "wrong_count": r.wrong_count,
            "not_attempted_count": r.not_attempted_count,
            "status": r.status,
            "confidence_score": r.confidence_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"total": total, "items": items}


@router.get("/{result_id}")
def get_result_details(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get full evaluation result by ID, including student details,
    question breakdown, score, and image paths.
    """
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    student = result.student
    exam = result.exam

    answers = (
        db.query(StudentAnswer)
        .filter(StudentAnswer.result_id == result.id)
        .order_by(StudentAnswer.question_no)
        .all()
    )

    # Fetch Answer Keys for comparison
    keys = (
        db.query(AnswerKey)
        .filter(AnswerKey.exam_id == result.exam_id, AnswerKey.set_code == result.set_code)
        .all()
    )
    key_map = {k.question_no: k.correct_option for k in keys}

    answer_list = []
    for a in answers:
        answer_list.append({
            "question_no": a.question_no,
            "marked_option": a.marked_option,
            "correct_option": key_map.get(a.question_no),
            "is_correct": a.is_correct,
            "confidence": a.confidence,
            "status": a.status,
            "is_uncertain": a.is_uncertain,
        })

    return {
        "id": result.id,
        "exam": {
            "id": exam.id,
            "name": exam.name,
            "code": exam.code,
            "total_questions": exam.total_questions,
            "marks_per_correct": exam.marks_per_correct,
            "negative_marks": exam.negative_marks,
        },
        "student": {
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
        },
        "set_code": result.set_code,
        "counts": {
            "total_questions": result.total_questions,
            "correct": result.correct_count,
            "wrong": result.wrong_count,
            "not_attempted": result.not_attempted_count,
            "multi_marked": result.multi_marked_count,
        },
        "total_score": result.total_score,
        "percentage": result.percentage,
        "status": result.status,
        "review_reason": result.review_reason,
        "confidence_score": result.confidence_score,
        "sheet_image_path": result.sheet_image_path,
        "processed_image_path": result.processed_image_path,
        "answers": answer_list,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


@router.post("/confirm")
def confirm_result_review(
    req: ConfirmReviewRequest,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """
    Operator confirms or corrects questionable values for a sheet from the Verify screen.
    Writes all modifications to AuditLog and updates status to CONFIRMED.
    """
    result = db.query(Result).filter(Result.id == req.result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    student = result.student
    exam = result.exam

    # Track audit changes
    old_student_values = {
        "roll_no": student.roll_no,
        "name_final": student.name_final,
        "father_name_final": student.father_name_final,
        "mobile_final": student.mobile_final,
        "dob_final": student.dob_final,
        "class_name_final": student.class_name_final,
        "set_code": result.set_code,
    }

    # Apply student field updates
    sf = req.student_fields
    if sf.roll_no is not None and sf.roll_no.strip():
        student.roll_no = sf.roll_no.strip()
    if sf.name_final is not None and sf.name_final.strip():
        student.name_final = sf.name_final.strip().upper()
    if sf.father_name_final is not None:
        student.father_name_final = sf.father_name_final.strip().upper()
    if sf.mobile_final is not None:
        student.mobile_final = sf.mobile_final.strip()
    if sf.dob_final is not None:
        student.dob_final = sf.dob_final.strip()
    if sf.class_name_final is not None:
        student.class_name_final = sf.class_name_final.strip()

    student.verified_flag = True
    student.verified_by_user_id = current_user.id

    if sf.set_code is not None and sf.set_code.strip():
        result.set_code = sf.set_code.strip().upper()

    new_student_values = {
        "roll_no": student.roll_no,
        "name_final": student.name_final,
        "father_name_final": student.father_name_final,
        "mobile_final": student.mobile_final,
        "dob_final": student.dob_final,
        "class_name_final": student.class_name_final,
        "set_code": result.set_code,
    }

    # Apply question corrections if any
    keys = (
        db.query(AnswerKey)
        .filter(AnswerKey.exam_id == result.exam_id, AnswerKey.set_code == result.set_code)
        .all()
    )
    key_map = {k.question_no: k.correct_option for k in keys}

    for corr in req.question_corrections:
        q_ans = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.result_id == result.id, StudentAnswer.question_no == corr.question_no)
            .first()
        )
        if q_ans:
            q_ans.marked_option = corr.marked_option
            q_ans.is_uncertain = False
            q_ans.status = "SINGLE" if corr.marked_option and len(corr.marked_option) == 1 else ("EMPTY" if not corr.marked_option else "MULTI")
            corr_opt = key_map.get(corr.question_no)
            if corr_opt and corr.marked_option == corr_opt:
                q_ans.is_correct = True
            elif corr.marked_option:
                q_ans.is_correct = False
            else:
                q_ans.is_correct = None

    # Recalculate score after corrections
    all_answers = db.query(StudentAnswer).filter(StudentAnswer.result_id == result.id).all()
    correct_count = 0
    wrong_count = 0
    not_attempted_count = 0
    multi_count = 0
    total_score = 0.0

    for a in all_answers:
        if a.status == "EMPTY" or not a.marked_option:
            not_attempted_count += 1
        elif a.status == "MULTI":
            multi_count += 1
            if exam.multi_marked_rule == "COUNT_AS_WRONG":
                wrong_count += 1
                total_score -= exam.negative_marks
        elif a.is_correct is True:
            correct_count += 1
            total_score += exam.marks_per_correct
        else:
            wrong_count += 1
            total_score -= exam.negative_marks

    result.correct_count = correct_count
    result.wrong_count = wrong_count
    result.not_attempted_count = not_attempted_count
    result.multi_marked_count = multi_count
    result.total_score = round(total_score, 2)
    max_m = result.total_questions * exam.marks_per_correct
    result.percentage = round((total_score / max_m) * 100.0, 2) if max_m > 0 else 0.0

    # Mark as CONFIRMED
    result.status = SheetStatus.CONFIRMED.value
    result.review_reason = None

    # Write to AuditLog
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="CONFIRM_VERIFY_SHEET",
        entity_type="Result",
        entity_id=str(result.id),
        old_values=json.dumps(old_student_values),
        new_values=json.dumps(new_student_values),
        ip_address="127.0.0.1",
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "result_id": result.id,
        "sheet_status": result.status,
        "total_score": result.total_score,
        "percentage": result.percentage,
        "verified_by": current_user.username,
    }


@router.post("/{result_id}/recheck")
def recheck_result_with_strict_threshold(
    result_id: int,
    req: RecheckRequest = None,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """
    Re-runs OMR processing on the stored sheet image with stricter thresholds.
    """
    result = db.query(Result).filter(Result.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    if not result.sheet_image_path:
        raise HTTPException(status_code=400, detail="Sheet image path is missing for this result")

    storage = get_storage_provider()
    raw_bytes = storage.get_file(result.sheet_image_path)
    if not raw_bytes:
        raise HTTPException(status_code=404, detail="Original sheet image file not found in storage")

    # Stricter thresholds
    fill_thresh = (req.fill_threshold if req and req.fill_threshold else 0.50)
    engine = OMREngine(fill_threshold=fill_thresh, uncertain_low=0.28, uncertain_high=0.50)

    import cv2
    import numpy as np
    nparr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    engine_res = engine.process_image(img, run_ocr=True, strict_quality=True)

    # Re-evaluate
    exam = result.exam
    keys = db.query(AnswerKey).filter(AnswerKey.exam_id == exam.id, AnswerKey.set_code == result.set_code).all()
    key_map = {k.question_no: k.correct_option for k in keys}

    evaluator = EvaluationEngine(
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
    )
    eval_res = evaluator.evaluate_sheet(engine_res.get("answers", {}), key_map, exam.total_questions)

    # Update result
    result.correct_count = eval_res["correct_count"]
    result.wrong_count = eval_res["wrong_count"]
    result.not_attempted_count = eval_res["not_attempted_count"]
    result.multi_marked_count = eval_res["multi_marked_count"]
    result.total_score = eval_res["total_score"]
    result.percentage = eval_res["percentage"]
    result.confidence_score = engine_res.get("confidence_score", 1.0)

    reasons = engine_res.get("review_reasons", [])
    if len(reasons) == 0 and eval_res["uncertain_count"] == 0:
        result.status = SheetStatus.AUTO_ACCEPTED.value
        result.review_reason = None
    else:
        result.status = SheetStatus.NEEDS_REVIEW.value
        result.review_reason = "; ".join(reasons)

    # Audit log
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="RECHECK_STRICT_THRESHOLD",
        entity_type="Result",
        entity_id=str(result.id),
        old_values=f"Threshold default, Score: {result.total_score}",
        new_values=f"Strict Threshold {fill_thresh}, Score: {result.total_score}",
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "success",
        "result_id": result.id,
        "sheet_status": result.status,
        "total_score": result.total_score,
        "percentage": result.percentage,
        "reasons": reasons,
    }
