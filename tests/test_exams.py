import io
import pytest
from fastapi import HTTPException, UploadFile
from backend.app.db.session import SessionLocal
from backend.app.models.models import User, UserRole, Exam, AnswerKey, MultiMarkedRule
from backend.app.schemas.exam import (
    ExamCreate,
    ExamUpdate,
    AnswerKeyCreate,
    AnswerKeyItem,
)
from backend.app.api.v1.exams import (
    list_exams,
    create_exam,
    get_exam,
    update_exam,
    delete_exam,
    get_answer_keys,
    set_answer_keys,
    upload_answer_keys_csv,
    download_answer_key_template,
)


@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def admin_user(db_session):
    user = db_session.query(User).filter(User.role == UserRole.ADMIN.value).first()
    if not user:
        user = User(
            username="exam_admin",
            email="exam_admin@test.com",
            hashed_password="pw",
            role=UserRole.ADMIN.value,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_exam_crud_flow(db_session, admin_user):
    # 1. Clean existing test exam
    db_session.query(Exam).filter(Exam.code == "BIO-2026").delete()
    db_session.commit()

    # 2. Create exam
    new_exam = ExamCreate(
        name="Biology Entrance Test 2026",
        code="BIO-2026",
        total_questions=40,
        marks_per_correct=3.0,
        negative_marks=0.5,
        multi_marked_rule=MultiMarkedRule.COUNT_AS_WRONG,
    )
    created = create_exam(exam_in=new_exam, current_user=admin_user, db=db_session)
    assert created.id is not None
    assert created.code == "BIO-2026"
    assert created.total_questions == 40

    # 3. Duplicate code raises 400
    with pytest.raises(HTTPException) as exc_info:
        create_exam(exam_in=new_exam, current_user=admin_user, db=db_session)
    assert exc_info.value.status_code == 400

    # 4. Get exam details
    detail = get_exam(exam_id=created.id, current_user=admin_user, db=db_session)
    assert detail.id == created.id
    assert detail.name == "Biology Entrance Test 2026"

    # 5. Update exam
    updated = update_exam(
        exam_id=created.id,
        exam_in=ExamUpdate(marks_per_correct=4.0, negative_marks=1.0),
        current_user=admin_user,
        db=db_session,
    )
    assert updated.marks_per_correct == 4.0
    assert updated.negative_marks == 1.0


def test_manual_answer_key_entry(db_session, admin_user):
    exam = db_session.query(Exam).filter(Exam.code == "BIO-2026").first()
    assert exam is not None

    payload = AnswerKeyCreate(
        set_code="A",
        keys=[
            AnswerKeyItem(question_no=1, correct_option="A"),
            AnswerKeyItem(question_no=2, correct_option="C"),
            AnswerKeyItem(question_no=3, correct_option="D"),
            AnswerKeyItem(question_no=4, correct_option="B"),
        ],
    )
    res = set_answer_keys(exam_id=exam.id, payload=payload, current_user=admin_user, db=db_session)
    assert res["status"] == "success"
    assert res["total_keys_saved"] == 4

    # Verify retrieval
    keys = get_answer_keys(exam_id=exam.id, set_code="A", current_user=admin_user, db=db_session)
    assert len(keys) == 4
    assert keys[0].question_no == 1
    assert keys[0].correct_option == "A"


def test_csv_upload_column_format(db_session, admin_user):
    exam = db_session.query(Exam).filter(Exam.code == "BIO-2026").first()
    assert exam is not None

    csv_data = "Question,SetA,SetB,SetC\n1,B,C,D\n2,D,A,B\n3,A,D,C\n"
    csv_bytes = csv_data.encode("utf-8")
    upload_file = UploadFile(filename="test_keys.csv", file=io.BytesIO(csv_bytes))

    res = upload_answer_keys_csv(exam_id=exam.id, file=upload_file, current_user=admin_user, db=db_session)
    assert res["status"] == "success"
    assert "A" in res["sets_updated"]
    assert "B" in res["sets_updated"]
    assert "C" in res["sets_updated"]
    assert res["total_keys_imported"] == 9


def test_csv_upload_row_format(db_session, admin_user):
    exam = db_session.query(Exam).filter(Exam.code == "BIO-2026").first()
    assert exam is not None

    csv_data = "Set,Question,Answer\nD,1,A\nD,2,B\nD,3,C\n"
    csv_bytes = csv_data.encode("utf-8")
    upload_file = UploadFile(filename="test_keys_rows.csv", file=io.BytesIO(csv_bytes))

    res = upload_answer_keys_csv(exam_id=exam.id, file=upload_file, current_user=admin_user, db=db_session)
    assert res["status"] == "success"
    assert "D" in res["sets_updated"]
    assert res["total_keys_imported"] == 3


def test_csv_upload_validation_errors(db_session, admin_user):
    exam = db_session.query(Exam).filter(Exam.code == "BIO-2026").first()
    assert exam is not None

    # Invalid option 'Z'
    bad_option_csv = "Set,Question,Answer\nA,1,Z\n".encode("utf-8")
    upload_file = UploadFile(filename="bad.csv", file=io.BytesIO(bad_option_csv))
    with pytest.raises(HTTPException) as exc_info:
        upload_answer_keys_csv(exam_id=exam.id, file=upload_file, current_user=admin_user, db=db_session)
    assert exc_info.value.status_code == 400

    # Question out of range (>40)
    out_of_range_csv = "Set,Question,Answer\nA,999,A\n".encode("utf-8")
    upload_file2 = UploadFile(filename="out_of_range.csv", file=io.BytesIO(out_of_range_csv))
    with pytest.raises(HTTPException) as exc_info:
        upload_answer_keys_csv(exam_id=exam.id, file=upload_file2, current_user=admin_user, db=db_session)
    assert exc_info.value.status_code == 400


def test_csv_template_generation(db_session):
    exam = db_session.query(Exam).filter(Exam.code == "BIO-2026").first()
    assert exam is not None

    response = download_answer_key_template(exam_id=exam.id, format_type="columns", db=db_session)
    assert response.status_code == 200
    assert "text/csv" in response.media_type
    content = response.body.decode("utf-8")
    assert "Question,SetA,SetB,SetC,SetD" in content
    assert "1," in content
