from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.models import SheetStatus, Result, Student


class AccuracyValidator:
    """
    Enforces the strict accuracy rule:
    'The system must never silently save an uncertain result.'
    A sheet is AUTO_ACCEPTED only if:
      1. All 4 markers found and perspective aligned cleanly
      2. No uncertain bubbles in any question or field
      3. Roll number fully decoded from bubbles
      4. Bubble vs OCR match is at or above the threshold for every name field
      5. No duplicate roll number already evaluated for this exam in the database
    """

    @classmethod
    def validate_for_acceptance(
        cls,
        engine_output: Dict[str, Any],
        exam_id: int,
        db: Optional[Session] = None,
        name_similarity_threshold: float = None,
    ) -> Tuple[str, List[str], List[Dict[str, Any]]]:
        """
        Validates whether the processed sheet can be AUTO_ACCEPTED.
        Returns:
            status: "AUTO_ACCEPTED" or "NEEDS_REVIEW"
            review_reasons: list of str
            highlight_rois: list of questionable areas for verification UI
        """
        threshold = (
            name_similarity_threshold
            if name_similarity_threshold is not None
            else settings.OCR_NAME_SIMILARITY_THRESHOLD
        )

        review_reasons: List[str] = list(engine_output.get("review_reasons", []))
        highlight_rois: List[Dict[str, Any]] = []

        # 1. Check markers and alignment
        if not engine_output.get("success") or engine_output.get("aligned_image") is None:
            return "NEEDS_REVIEW", review_reasons, highlight_rois

        student_data = engine_output.get("student_data", {})
        answers = engine_output.get("answers", {})
        summary = engine_output.get("summary", {})

        # 2. Check Roll Number
        roll_info = student_data.get("roll_no", {})
        roll_val = roll_info.get("bubble_value", "").strip()
        if not roll_val or roll_info.get("is_uncertain") or len(roll_val) != 6:
            msg = f"Roll number '{roll_val}' is incomplete or uncertain"
            if msg not in review_reasons:
                review_reasons.append(msg)
            highlight_rois.append({
                "type": "field",
                "field_name": "roll_no",
                "reason": "Uncertain or incomplete roll number",
            })

        # 3. Check Duplicate Roll Number for Exam
        if db and roll_val and len(roll_val) == 6:
            existing_student = db.query(Student).filter(Student.roll_no == roll_val).first()
            if existing_student:
                existing_res = (
                    db.query(Result)
                    .filter(Result.student_id == existing_student.id, Result.exam_id == exam_id)
                    .first()
                )
                if existing_res:
                    msg = f"Duplicate roll number {roll_val} already processed for exam {exam_id}"
                    if msg not in review_reasons:
                        review_reasons.append(msg)
                    highlight_rois.append({
                        "type": "duplicate",
                        "field_name": "roll_no",
                        "reason": msg,
                    })

        # 4. Check Set Code
        set_info = student_data.get("set_code", {})
        set_val = set_info.get("bubble_value", "").strip()
        if set_val not in {"A", "B", "C", "D"}:
            msg = f"Invalid or missing set code: '{set_val}'"
            if msg not in review_reasons:
                review_reasons.append(msg)
            highlight_rois.append({
                "type": "field",
                "field_name": "set_code",
                "reason": msg,
            })

        # 5. Check Name OCR Similarity Match
        name_info = student_data.get("name", {})
        name_bubble = name_info.get("bubble_value", "").strip()
        name_ocr = name_info.get("ocr_value", "").strip()
        sim_score = name_info.get("similarity_score", 1.0)

        if name_bubble and name_ocr and sim_score < threshold:
            msg = f"Candidate name bubble ('{name_bubble}') and handwriting ('{name_ocr}') similarity ({int(sim_score*100)}%) below threshold ({int(threshold*100)}%)"
            if msg not in review_reasons:
                review_reasons.append(msg)
            highlight_rois.append({
                "type": "ocr_mismatch",
                "field_name": "name",
                "bubble_value": name_bubble,
                "ocr_value": name_ocr,
                "reason": msg,
            })

        # 6. Check for Uncertain Questions
        if summary.get("uncertain_count", 0) > 0:
            for q_no, q_data in answers.items():
                if q_data.get("status") == "UNCERTAIN":
                    highlight_rois.append({
                        "type": "question",
                        "question_no": q_no,
                        "status": "UNCERTAIN",
                        "reason": f"Question {q_no} has ambiguous or faint bubble mark",
                    })

        # Final auto-acceptance decision
        if len(review_reasons) == 0 and summary.get("uncertain_count", 0) == 0:
            status = SheetStatus.AUTO_ACCEPTED.value
        else:
            status = SheetStatus.NEEDS_REVIEW.value

        return status, review_reasons, highlight_rois
