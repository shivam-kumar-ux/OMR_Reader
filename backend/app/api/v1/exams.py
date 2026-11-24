import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_operator, require_admin, get_current_user
from backend.app.db.session import get_db
from backend.app.models.models import Exam, AnswerKey, User
from backend.app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    ExamResponse,
    ExamDetailResponse,
    AnswerKeyCreate,
    AnswerKeyResponse,
)

router = APIRouter(prefix="/exams", tags=["Exams & Answer Keys"])


def _get_exam_sets(exam_id: int, db: Session) -> List[str]:
    sets = (
        db.query(AnswerKey.set_code)
        .filter(AnswerKey.exam_id == exam_id)
        .distinct()
        .order_by(AnswerKey.set_code)
        .all()
    )
    return [s[0] for s in sets]


@router.get("", response_model=List[ExamResponse])
def list_exams(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all exams with their configured sets."""
    query = db.query(Exam)
    if active_only:
        query = query.filter(Exam.is_active == True)
    exams = query.order_by(Exam.id.desc()).offset(skip).limit(limit).all()

    result = []
    for exam in exams:
        sets = _get_exam_sets(exam.id, db)
        exam_dict = {
            "id": exam.id,
            "name": exam.name,
            "code": exam.code,
            "total_questions": exam.total_questions,
            "marks_per_correct": exam.marks_per_correct,
            "negative_marks": exam.negative_marks,
            "multi_marked_rule": exam.multi_marked_rule,
            "is_active": exam.is_active,
            "created_at": exam.created_at,
            "sets": sets,
        }
        result.append(ExamResponse(**exam_dict))
    return result


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_in: ExamCreate,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Create a new exam."""
    existing = db.query(Exam).filter(Exam.code == exam_in.code.strip().upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Exam with code '{exam_in.code}' already exists",
        )

    exam = Exam(
        name=exam_in.name.strip(),
        code=exam_in.code.strip().upper(),
        total_questions=exam_in.total_questions,
        marks_per_correct=exam_in.marks_per_correct,
        negative_marks=exam_in.negative_marks,
        multi_marked_rule=exam_in.multi_marked_rule.value,
        is_active=exam_in.is_active,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    return ExamResponse(
        id=exam.id,
        name=exam.name,
        code=exam.code,
        total_questions=exam.total_questions,
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
        is_active=exam.is_active,
        created_at=exam.created_at,
        sets=[],
    )


@router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get exam details with all configured sets and answer keys."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    keys = db.query(AnswerKey).filter(AnswerKey.exam_id == exam_id).all()
    answer_keys_by_set = {}
    sets_list = set()
    for k in keys:
        sets_list.add(k.set_code)
        if k.set_code not in answer_keys_by_set:
            answer_keys_by_set[k.set_code] = {}
        answer_keys_by_set[k.set_code][k.question_no] = k.correct_option

    return ExamDetailResponse(
        id=exam.id,
        name=exam.name,
        code=exam.code,
        total_questions=exam.total_questions,
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
        is_active=exam.is_active,
        created_at=exam.created_at,
        sets=sorted(list(sets_list)),
        answer_keys=answer_keys_by_set,
    )


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Update exam parameters."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    if exam_in.name is not None:
        exam.name = exam_in.name.strip()
    if exam_in.code is not None:
        new_code = exam_in.code.strip().upper()
        if new_code != exam.code:
            existing = db.query(Exam).filter(Exam.code == new_code).first()
            if existing:
                raise HTTPException(status_code=400, detail="Exam code already in use")
            exam.code = new_code
    if exam_in.total_questions is not None:
        exam.total_questions = exam_in.total_questions
    if exam_in.marks_per_correct is not None:
        exam.marks_per_correct = exam_in.marks_per_correct
    if exam_in.negative_marks is not None:
        exam.negative_marks = exam_in.negative_marks
    if exam_in.multi_marked_rule is not None:
        exam.multi_marked_rule = exam_in.multi_marked_rule.value
    if exam_in.is_active is not None:
        exam.is_active = exam_in.is_active

    db.commit()
    db.refresh(exam)
    return ExamResponse(
        id=exam.id,
        name=exam.name,
        code=exam.code,
        total_questions=exam.total_questions,
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
        is_active=exam.is_active,
        created_at=exam.created_at,
        sets=_get_exam_sets(exam.id, db),
    )


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an exam and all associated answer keys and results (Admin only)."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    db.delete(exam)
    db.commit()
    return None


@router.get("/{exam_id}/answer-keys", response_model=List[AnswerKeyResponse])
def get_answer_keys(
    exam_id: int,
    set_code: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all answer keys for an exam, optionally filtered by set_code."""
    query = db.query(AnswerKey).filter(AnswerKey.exam_id == exam_id)
    if set_code:
        query = query.filter(AnswerKey.set_code == set_code.strip().upper())
    keys = query.order_by(AnswerKey.set_code, AnswerKey.question_no).all()
    return keys


@router.post("/{exam_id}/answer-keys")
def set_answer_keys(
    exam_id: int,
    payload: AnswerKeyCreate,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """Set or replace answer keys for a specific set code."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    set_code = payload.set_code.strip().upper()

    # Validate question numbers
    for k in payload.keys:
        if k.question_no > exam.total_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question number {k.question_no} exceeds exam total questions ({exam.total_questions})",
            )

    # Delete existing keys for this set and exam
    db.query(AnswerKey).filter(
        AnswerKey.exam_id == exam_id,
        AnswerKey.set_code == set_code,
    ).delete()

    # Add new keys
    new_keys = [
        AnswerKey(
            exam_id=exam_id,
            set_code=set_code,
            question_no=k.question_no,
            correct_option=k.correct_option.strip().upper(),
        )
        for k in payload.keys
    ]
    db.add_all(new_keys)
    db.commit()

    return {
        "status": "success",
        "exam_id": exam_id,
        "set_code": set_code,
        "total_keys_saved": len(new_keys),
    }


@router.post("/{exam_id}/answer-keys/csv")
def upload_answer_keys_csv(
    exam_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """
    Upload answer keys from CSV.
    Supports two standard formats:
    Format 1 (Multi-column sets):
      Question,SetA,SetB,SetC,SetD
      1,A,B,C,D
      2,C,A,D,B

    Format 2 (Row-wise):
      Set,Question,Answer
      A,1,B
      A,2,C
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    content = file.file.read()
    try:
        decoded_content = content.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV encoding. Please upload UTF-8 text.")

    csv_reader = csv.reader(io.StringIO(decoded_content))
    header = next(csv_reader, None)
    if not header:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    header_clean = [h.strip().upper() for h in header]

    keys_to_insert = []
    sets_affected = set()

    # Detect format
    if "QUESTION" in header_clean and len(header_clean) > 2 and ("SETA" in header_clean or "SET_A" in header_clean or "A" in header_clean):
        # Format 1: Multi-column
        q_idx = header_clean.index("QUESTION")
        set_cols = {}
        for idx, col_name in enumerate(header_clean):
            if idx == q_idx:
                continue
            set_code = col_name.replace("SET", "").replace("_", "").strip()
            if set_code:
                set_cols[idx] = set_code
                sets_affected.add(set_code)

        for row_num, row in enumerate(csv_reader, start=2):
            if not row or not any(row):
                continue
            try:
                q_no = int(row[q_idx].strip())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Line {row_num}: Invalid question number '{row[q_idx]}'")
            if q_no < 1 or q_no > exam.total_questions:
                raise HTTPException(status_code=400, detail=f"Line {row_num}: Question {q_no} outside range 1..{exam.total_questions}")

            for col_idx, set_code in set_cols.items():
                if col_idx < len(row):
                    ans = row[col_idx].strip().upper()
                    if ans in {"A", "B", "C", "D", "E"}:
                        keys_to_insert.append(
                            AnswerKey(
                                exam_id=exam_id,
                                set_code=set_code,
                                question_no=q_no,
                                correct_option=ans,
                            )
                        )
    else:
        # Format 2: Row-wise (Set, Question, Answer)
        try:
            set_idx = header_clean.index("SET")
            q_idx = header_clean.index("QUESTION")
            ans_idx = header_clean.index("ANSWER") if "ANSWER" in header_clean else header_clean.index("OPTION")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="CSV must contain headers: 'Question, SetA, SetB...' OR 'Set, Question, Answer'",
            )

        for row_num, row in enumerate(csv_reader, start=2):
            if not row or not any(row):
                continue
            set_code = row[set_idx].strip().upper()
            try:
                q_no = int(row[q_idx].strip())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Line {row_num}: Invalid question number '{row[q_idx]}'")
            if q_no < 1 or q_no > exam.total_questions:
                raise HTTPException(status_code=400, detail=f"Line {row_num}: Question {q_no} outside range 1..{exam.total_questions}")
            ans = row[ans_idx].strip().upper()
            if ans not in {"A", "B", "C", "D", "E"}:
                raise HTTPException(status_code=400, detail=f"Line {row_num}: Invalid answer option '{ans}' (must be A-E)")

            sets_affected.add(set_code)
            keys_to_insert.append(
                AnswerKey(
                    exam_id=exam_id,
                    set_code=set_code,
                    question_no=q_no,
                    correct_option=ans,
                )
            )

    if not keys_to_insert:
        raise HTTPException(status_code=400, detail="No valid answer keys found in CSV")

    # Clear previous keys for affected sets
    for sc in sets_affected:
        db.query(AnswerKey).filter(
            AnswerKey.exam_id == exam_id,
            AnswerKey.set_code == sc,
        ).delete()

    db.add_all(keys_to_insert)
    db.commit()

    return {
        "status": "success",
        "exam_id": exam_id,
        "sets_updated": sorted(list(sets_affected)),
        "total_keys_imported": len(keys_to_insert),
    }


@router.get("/{exam_id}/answer-keys/template")
def download_answer_key_template(
    exam_id: int,
    format_type: str = "columns",  # "columns" or "rows"
    db: Session = Depends(get_db),
):
    """Download a CSV template pre-filled with question numbers for this exam."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    output = io.StringIO()
    writer = csv.writer(output)

    if format_type == "rows":
        writer.writerow(["Set", "Question", "Answer"])
        for sc in ["A", "B", "C", "D"]:
            for q in range(1, min(exam.total_questions + 1, 101)):
                writer.writerow([sc, q, ""])
    else:
        writer.writerow(["Question", "SetA", "SetB", "SetC", "SetD"])
        for q in range(1, exam.total_questions + 1):
            writer.writerow([q, "", "", "", ""])

    output.seek(0)
    filename = f"{exam.code}_answer_key_template.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
