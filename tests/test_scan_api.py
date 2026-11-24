import io
import os
import cv2
import pytest
from fastapi import UploadFile
from backend.app.storage import LocalStorageProvider
from backend.app.db.session import SessionLocal
from backend.app.models.models import Exam, AnswerKey, Student, Result, User, UserRole, AuditLog
from backend.app.api.v1.scan import scan_single_sheet, scan_batch_sheets
from backend.app.api.v1.results import get_result_details, confirm_result_review, recheck_result_with_strict_threshold
from backend.app.api.v1.students import search_students, get_student_profile
from backend.app.schemas.scan import ConfirmReviewRequest, ReviewFieldConfirm, QuestionCorrection
from backend.app.omr.calibration import OMRCalibrator


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def admin_user(db_session):
    u = db_session.query(User).filter(User.role == UserRole.ADMIN.value).first()
    if not u:
        u = User(username="scan_admin", email="scan_admin@test.com", hashed_password="pw", role="Admin")
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
    return u


@pytest.fixture
def test_exam(db_session):
    exam = db_session.query(Exam).filter(Exam.code == "GSM-2026").first()
    if not exam:
        exam = Exam(
            name="General Science & Mathematics 2026",
            code="GSM-2026",
            total_questions=50,
            marks_per_correct=4.0,
            negative_marks=1.0,
            is_active=True,
        )
        db_session.add(exam)
        db_session.commit()
        db_session.refresh(exam)

        keys = [
            AnswerKey(exam_id=exam.id, set_code="A", question_no=q, correct_option="A")
            for q in range(1, 51)
        ]
        db_session.add_all(keys)
        db_session.commit()
    return exam


@pytest.fixture
def sample_marked_sheet():
    blank_path = "./samples/blank/omr_sheet_blank.png"
    if not os.path.exists(blank_path):
        from backend.app.omr.generator import generate_standard_omr_sheet
        generate_standard_omr_sheet()
    img = cv2.imread(blank_path)
    template = OMRCalibrator().template

    # Fill roll number 123456
    roll_config = template["personal_fields"]["roll_no"]
    for col_idx, d in enumerate([1, 2, 3, 4, 5, 6]):
        b = roll_config["grid"][col_idx][d]
        cv2.circle(img, (b["cx"], b["cy"]), b["radius"] - 2, (20, 20, 20), -1)

    # Fill set code A
    b_set = template["personal_fields"]["set_code"]["grid"][0][0]
    cv2.circle(img, (b_set["cx"], b_set["cy"]), b_set["radius"] - 2, (20, 20, 20), -1)

    # Fill name: AMIT SHARMA
    name_config = template["personal_fields"]["name"]
    name_letters = "AMIT SHARMA"
    for col_idx, ch in enumerate(name_letters):
        if ch != " ":
            l_idx = ord(ch) - ord("A")
            b_name = name_config["grid"][col_idx][l_idx]
            cv2.circle(img, (b_name["cx"], b_name["cy"]), b_name["radius"] - 2, (20, 20, 20), -1)

    # Fill questions 1 to 10 with option A
    for q in range(1, 11):
        b_q = template["answer_blocks"]["questions"][str(q)]["A"]
        cv2.circle(img, (b_q["cx"], b_q["cy"]), b_q["radius"] - 2, (20, 20, 20), -1)

    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_storage_provider():
    storage = LocalStorageProvider("./storage")
    data = b"Hello OMR Storage test bytes"
    path = storage.save_file(data, "test_file.txt", "text/plain", folder="test")
    assert path is not None
    read_data = storage.get_file(path)
    assert read_data == data
    assert storage.delete_file(path) is True


def test_scan_single_sheet_api(db_session, admin_user, test_exam, sample_marked_sheet):
    upload_file = UploadFile(filename="student_123456.png", file=io.BytesIO(sample_marked_sheet))
    res = scan_single_sheet(
        exam_id=test_exam.id,
        set_code="A",
        file=upload_file,
        current_user=admin_user,
        db=db_session,
    )

    assert res.result_id is not None
    assert res.student_id is not None
    assert res.roll_no == "123456"
    assert res.set_code == "A"
    assert res.status in {"done", "needs_review"}
    assert res.sheet_image_url is not None


def test_scan_batch_with_error_resilience(db_session, admin_user, test_exam, sample_marked_sheet):
    good_file = UploadFile(filename="batch_good.png", file=io.BytesIO(sample_marked_sheet))
    bad_file = UploadFile(filename="corrupt.png", file=io.BytesIO(b"Not an image at all"))

    batch_res = scan_batch_sheets(
        exam_id=test_exam.id,
        set_code="A",
        files=[good_file, bad_file],
        current_user=admin_user,
        db=db_session,
    )

    assert batch_res.total_files_received == 2
    assert batch_res.total_sheets_processed == 2
    assert batch_res.failed_count == 1
    assert len(batch_res.results) == 2

    # Verify bad file failed with clear reason
    failed_item = [r for r in batch_res.results if r.status == "failed"][0]
    assert failed_item.filename == "corrupt.png"
    assert failed_item.error_message is not None


def test_confirm_review_and_audit_log(db_session, admin_user):
    result = db_session.query(Result).order_by(Result.id.desc()).first()
    assert result is not None

    confirm_payload = ConfirmReviewRequest(
        result_id=result.id,
        student_fields=ReviewFieldConfirm(
            name_final="AMIT KUMAR SHARMA",
            father_name_final="RAJESH SHARMA",
            mobile_final="9876500000",
        ),
        question_corrections=[
            QuestionCorrection(question_no=1, marked_option="B"),
        ],
        comments="Verified with handwritten exam copy",
    )

    confirm_res = confirm_result_review(req=confirm_payload, current_user=admin_user, db=db_session)
    assert confirm_res["status"] == "success"
    assert confirm_res["sheet_status"] == "CONFIRMED"

    # Check AuditLog
    log = (
        db_session.query(AuditLog)
        .filter(AuditLog.entity_id == str(result.id))
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.action == "CONFIRM_VERIFY_SHEET"
    assert "AMIT KUMAR SHARMA" in log.new_values


def test_student_search_and_profile(db_session, admin_user):
    # Search for student
    students = search_students(q="AMIT", current_user=admin_user, db=db_session)
    assert len(students) > 0

    student_id = students[0]["id"]
    profile = get_student_profile(student_id=student_id, current_user=admin_user, db=db_session)
    assert profile["id"] == student_id
    assert len(profile["results"]) > 0


def test_recheck_result(db_session, admin_user):
    result = db_session.query(Result).filter(Result.sheet_image_path.isnot(None)).order_by(Result.id.desc()).first()
    assert result is not None

    recheck_res = recheck_result_with_strict_threshold(
        result_id=result.id,
        current_user=admin_user,
        db=db_session,
    )
    assert recheck_res["status"] == "success"
    assert "sheet_status" in recheck_res
