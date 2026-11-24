import os
import uuid
from typing import List, Optional
import cv2
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from backend.app.api.deps import require_operator, get_current_user
from backend.app.db.session import get_db
from backend.app.models.models import (
    Exam,
    AnswerKey,
    Student,
    Result,
    StudentAnswer,
    SheetStatus,
    User,
    AuditLog,
)
from backend.app.omr.engine import OMREngine
from backend.app.omr.evaluator import EvaluationEngine
from backend.app.omr.preprocessor import ImagePreprocessor
from backend.app.omr.validator import AccuracyValidator
from backend.app.schemas.scan import ScanFileStatus, BatchScanResponse
from backend.app.services.folder_watcher import FolderWatcherService
from backend.app.storage import get_storage_provider

router = APIRouter(prefix="/scan", tags=["Scanning & OMR Processing"])


def _process_single_sheet_core(
    image_bytes: bytes,
    filename: str,
    page_num: int,
    exam: Exam,
    current_user: User,
    db: Session,
    storage,
    omr_engine: OMREngine,
    evaluator: EvaluationEngine,
    forced_set_code: Optional[str] = None,
) -> ScanFileStatus:
    """
    Core function that processes one sheet image, evaluates it,
    stores images and database records, and returns status.
    Guaranteed not to raise unhandled exceptions.
    """
    try:
        # Load image via preprocessor
        images = ImagePreprocessor.load_images_from_file_or_bytes(image_bytes, filename)
        if not images:
            return ScanFileStatus(
                filename=filename,
                page_number=page_num,
                status="failed",
                error_message="Could not decode image data",
            )
        img, _ = images[0]

        # Save raw sheet image
        raw_path = storage.save_file(
            image_bytes,
            filename=f"raw_{page_num}_{filename}.png",
            content_type="image/png",
            folder="raw_sheets",
        )

        # Run OMR Engine
        engine_res = omr_engine.process_image(img, run_ocr=True, strict_quality=True)

        # Save processed debug image if available
        processed_path = ""
        if engine_res.get("processed_image") is not None:
            success, p_buf = cv2.imencode(".jpg", engine_res["processed_image"], [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if success:
                processed_path = storage.save_file(
                    p_buf.tobytes(),
                    filename=f"proc_{page_num}_{filename}.jpg",
                    content_type="image/jpeg",
                    folder="processed_sheets",
                )

        student_data = engine_res.get("student_data", {})
        roll_no = student_data.get("roll_no", {}).get("bubble_value", "").strip() or "UNKNOWN"
        detected_set = student_data.get("set_code", {}).get("bubble_value", "").strip()
        set_code = forced_set_code or detected_set or "A"

        # Fetch Answer Keys for this Exam and Set Code
        keys = (
            db.query(AnswerKey)
            .filter(AnswerKey.exam_id == exam.id, AnswerKey.set_code == set_code)
            .all()
        )
        answer_keys_dict = {k.question_no: k.correct_option for k in keys}

        # Evaluate against answer key
        eval_res = evaluator.evaluate_sheet(
            decoded_answers=engine_res.get("answers", {}),
            answer_keys=answer_keys_dict,
            total_questions=exam.total_questions,
        )

        # Validate Auto-Acceptance
        final_status, review_reasons, highlight_rois = AccuracyValidator.validate_for_acceptance(
            engine_output=engine_res,
            exam_id=exam.id,
            db=db,
            name_similarity_threshold=omr_engine.ocr_similarity_threshold,
        )

        # Database Persistence
        # 1. Upsert / Get Student
        student = db.query(Student).filter(Student.roll_no == roll_no).first()
        name_info = student_data.get("name", {})
        fname_info = student_data.get("father_name", {})
        mob_info = student_data.get("mobile", {})
        dob_info = student_data.get("dob", {})
        class_info = student_data.get("class_name", {})

        name_bubble = name_info.get("bubble_value", "")
        name_ocr = name_info.get("ocr_value", "")
        name_final = name_info.get("final_value", "") or f"Student_{roll_no}"

        if not student:
            student = Student(
                roll_no=roll_no,
                name_bubble=name_bubble,
                name_ocr=name_ocr,
                name_final=name_final,
                father_name_ocr=fname_info.get("ocr_value", ""),
                father_name_final=fname_info.get("final_value", ""),
                mobile_bubble=mob_info.get("bubble_value", ""),
                mobile_ocr=mob_info.get("ocr_value", ""),
                mobile_final=mob_info.get("final_value", ""),
                dob_bubble=dob_info.get("bubble_value", ""),
                dob_ocr=dob_info.get("ocr_value", ""),
                dob_final=dob_info.get("final_value", ""),
                class_name_bubble=class_info.get("bubble_value", ""),
                class_name_ocr=class_info.get("ocr_value", ""),
                class_name_final=class_info.get("final_value", ""),
                verified_flag=(final_status == SheetStatus.AUTO_ACCEPTED.value),
                verified_by_user_id=current_user.id if final_status == SheetStatus.AUTO_ACCEPTED.value else None,
            )
            db.add(student)
            db.commit()
            db.refresh(student)
        else:
            # Update fields if student exists
            if name_final and student.name_final.startswith("Student_"):
                student.name_final = name_final
            student.name_bubble = name_bubble
            student.name_ocr = name_ocr
            db.commit()

        # 2. Upsert Result
        result = (
            db.query(Result)
            .filter(Result.student_id == student.id, Result.exam_id == exam.id)
            .first()
        )
        if not result:
            result = Result(
                student_id=student.id,
                exam_id=exam.id,
                set_code=set_code,
                total_questions=exam.total_questions,
                correct_count=eval_res["correct_count"],
                wrong_count=eval_res["wrong_count"],
                not_attempted_count=eval_res["not_attempted_count"],
                multi_marked_count=eval_res["multi_marked_count"],
                total_score=eval_res["total_score"],
                percentage=eval_res["percentage"],
                status=final_status,
                review_reason="; ".join(review_reasons) if review_reasons else None,
                confidence_score=engine_res.get("confidence_score", 1.0),
                sheet_image_path=raw_path,
                processed_image_path=processed_path,
            )
            db.add(result)
            db.commit()
            db.refresh(result)
        else:
            result.set_code = set_code
            result.correct_count = eval_res["correct_count"]
            result.wrong_count = eval_res["wrong_count"]
            result.not_attempted_count = eval_res["not_attempted_count"]
            result.multi_marked_count = eval_res["multi_marked_count"]
            result.total_score = eval_res["total_score"]
            result.percentage = eval_res["percentage"]
            result.status = final_status
            result.review_reason = "; ".join(review_reasons) if review_reasons else None
            result.confidence_score = engine_res.get("confidence_score", 1.0)
            result.sheet_image_path = raw_path
            result.processed_image_path = processed_path
            db.commit()

        # 3. Save StudentAnswers
        db.query(StudentAnswer).filter(StudentAnswer.result_id == result.id).delete()
        student_answers_to_add = []
        for q_item in eval_res["question_evaluations"]:
            student_answers_to_add.append(
                StudentAnswer(
                    result_id=result.id,
                    question_no=q_item["question_no"],
                    marked_option=q_item["marked_option"],
                    is_correct=q_item["is_correct"],
                    confidence=q_item["confidence"],
                    status=q_item["status"],
                )
            )
        db.add_all(student_answers_to_add)
        db.commit()

        ui_status = "done" if final_status == SheetStatus.AUTO_ACCEPTED.value else "needs_review"

        return ScanFileStatus(
            filename=filename,
            page_number=page_num,
            status=ui_status,
            result_id=result.id,
            student_id=student.id,
            roll_no=roll_no,
            name=name_final,
            set_code=set_code,
            total_score=eval_res["total_score"],
            confidence_score=result.confidence_score,
            review_reasons=review_reasons,
            sheet_image_url=raw_path,
            processed_image_url=processed_path,
        )

    except Exception as e:
        db.rollback()
        return ScanFileStatus(
            filename=filename,
            page_number=page_num,
            status="failed",
            error_message=str(e),
        )


@router.post("", response_model=ScanFileStatus)
def scan_single_sheet(
    exam_id: int = Form(...),
    set_code: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """
    Process a single OMR sheet (image or single-page PDF).
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    storage = get_storage_provider()
    omr_engine = OMREngine()
    evaluator = EvaluationEngine(
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
    )

    contents = file.file.read()
    status_res = _process_single_sheet_core(
        image_bytes=contents,
        filename=file.filename or "sheet.png",
        page_num=1,
        exam=exam,
        current_user=current_user,
        db=db,
        storage=storage,
        omr_engine=omr_engine,
        evaluator=evaluator,
        forced_set_code=set_code,
    )

    return status_res


@router.post("/batch", response_model=BatchScanResponse)
def scan_batch_sheets(
    exam_id: int = Form(...),
    set_code: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """
    Process multiple OMR files in a batch.
    Multi-page PDFs have each page processed as a separate sheet.
    One bad file never stops the batch.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    storage = get_storage_provider()
    omr_engine = OMREngine()
    evaluator = EvaluationEngine(
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
    )

    batch_id = uuid.uuid4().hex[:8]
    all_results: List[ScanFileStatus] = []

    for upload_file in files:
        fname = upload_file.filename or "unknown.png"
        try:
            file_bytes = upload_file.file.read()
            ext = os.path.splitext(fname)[1].lower()

            if ext == ".pdf" or file_bytes.startswith(b"%PDF-"):
                pages = ImagePreprocessor.load_images_from_file_or_bytes(file_bytes, fname)
                for page_img, page_num in pages:
                    # Convert page image back to png bytes for standardized ingestion
                    _, p_buf = cv2.imencode(".png", page_img)
                    p_bytes = p_buf.tobytes()
                    p_status = _process_single_sheet_core(
                        image_bytes=p_bytes,
                        filename=fname,
                        page_num=page_num,
                        exam=exam,
                        current_user=current_user,
                        db=db,
                        storage=storage,
                        omr_engine=omr_engine,
                        evaluator=evaluator,
                        forced_set_code=set_code,
                    )
                    all_results.append(p_status)
            else:
                p_status = _process_single_sheet_core(
                    image_bytes=file_bytes,
                    filename=fname,
                    page_num=1,
                    exam=exam,
                    current_user=current_user,
                    db=db,
                    storage=storage,
                    omr_engine=omr_engine,
                    evaluator=evaluator,
                    forced_set_code=set_code,
                )
                all_results.append(p_status)
        except Exception as e:
            all_results.append(
                ScanFileStatus(
                    filename=fname,
                    page_number=1,
                    status="failed",
                    error_message=str(e),
                )
            )

    auto_acc = sum(1 for r in all_results if r.status == "done")
    needs_rev = sum(1 for r in all_results if r.status == "needs_review")
    failed = sum(1 for r in all_results if r.status == "failed")

    return BatchScanResponse(
        batch_id=batch_id,
        total_files_received=len(files),
        total_sheets_processed=len(all_results),
        auto_accepted_count=auto_acc,
        needs_review_count=needs_rev,
        failed_count=failed,
        results=all_results,
    )


@router.post("/scanner-folder", response_model=BatchScanResponse)
def process_scanner_folder(
    exam_id: int,
    current_user: User = Depends(require_operator),
    db: Session = Depends(get_db),
):
    """
    Imports and processes all pending files in the scanner hot-folder.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    watcher = FolderWatcherService()
    pending_files = watcher.scan_for_pending_files()

    if not pending_files:
        return BatchScanResponse(
            batch_id="empty",
            total_files_received=0,
            total_sheets_processed=0,
            auto_accepted_count=0,
            needs_review_count=0,
            failed_count=0,
            results=[],
        )

    storage = get_storage_provider()
    omr_engine = OMREngine()
    evaluator = EvaluationEngine(
        marks_per_correct=exam.marks_per_correct,
        negative_marks=exam.negative_marks,
        multi_marked_rule=exam.multi_marked_rule,
    )

    batch_id = uuid.uuid4().hex[:8]
    all_results = []

    for f_path in pending_files:
        fname = os.path.basename(f_path)
        try:
            with open(f_path, "rb") as f:
                f_bytes = f.read()

            p_status = _process_single_sheet_core(
                image_bytes=f_bytes,
                filename=fname,
                page_num=1,
                exam=exam,
                current_user=current_user,
                db=db,
                storage=storage,
                omr_engine=omr_engine,
                evaluator=evaluator,
            )
            all_results.append(p_status)
            watcher.move_to_processed(f_path, "processed")
        except Exception as e:
            all_results.append(
                ScanFileStatus(
                    filename=fname,
                    page_number=1,
                    status="failed",
                    error_message=str(e),
                )
            )
            watcher.move_to_processed(f_path, "failed")

    auto_acc = sum(1 for r in all_results if r.status == "done")
    needs_rev = sum(1 for r in all_results if r.status == "needs_review")
    failed = sum(1 for r in all_results if r.status == "failed")

    return BatchScanResponse(
        batch_id=batch_id,
        total_files_received=len(pending_files),
        total_sheets_processed=len(all_results),
        auto_accepted_count=auto_acc,
        needs_review_count=needs_rev,
        failed_count=failed,
        results=all_results,
    )
