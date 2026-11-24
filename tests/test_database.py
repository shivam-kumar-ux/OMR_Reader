import pytest
from sqlalchemy.exc import IntegrityError
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.models import (
    User,
    UserRole,
    Student,
    Exam,
    AnswerKey,
    Result,
    StudentAnswer,
    AuditLog,
    SheetStatus,
    MultiMarkedRule,
    BubbleState,
)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(StudentAnswer).delete()
        db.query(Result).delete()
        db.query(AnswerKey).delete()
        db.query(Exam).delete()
        db.query(Student).delete()
        db.query(AuditLog).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(StudentAnswer).delete()
        db.query(Result).delete()
        db.query(AnswerKey).delete()
        db.query(Exam).delete()
        db.query(Student).delete()
        db.query(AuditLog).delete()
        db.query(User).delete()
        db.commit()
    finally:
        db.close()


def test_create_user_and_roles():
    db = SessionLocal()
    try:
        user = User(
            username="admin_user",
            email="admin@test.com",
            hashed_password="hashed_secret_pw",
            role=UserRole.ADMIN.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.role == "Admin"
        assert user.is_active is True

        # Test unique constraint on username
        duplicate = User(
            username="admin_user",
            email="other@test.com",
            hashed_password="hashed_secret_pw",
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_student_bubble_and_ocr_fields():
    db = SessionLocal()
    try:
        user = User(
            username="verifier_1",
            email="verifier1@test.com",
            hashed_password="pw",
            role=UserRole.OPERATOR.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        student = Student(
            roll_no="100234",
            name_bubble="RAHUL SHARMA",
            name_ocr="RAHUL SHARMA",
            name_final="RAHUL SHARMA",
            father_name_bubble="VIKRAM SHARMA",
            father_name_ocr="VIKRAM SHARMA",
            father_name_final="VIKRAM SHARMA",
            mobile_bubble="9876543210",
            mobile_ocr="9876543210",
            mobile_final="9876543210",
            dob_bubble="15082005",
            dob_ocr="15082005",
            dob_final="15082005",
            class_name_bubble="12",
            class_name_ocr="12",
            class_name_final="12",
            verified_flag=True,
            verified_by_user_id=user.id,
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        assert student.id is not None
        assert student.name_bubble == "RAHUL SHARMA"
        assert student.name_ocr == "RAHUL SHARMA"
        assert student.verified_flag is True
        assert student.verified_by_user.username == "verifier_1"
    finally:
        db.close()


def test_exam_and_answer_key_unique_constraint():
    db = SessionLocal()
    try:
        exam = Exam(
            name="Physics Midterm",
            code="PHY-2026",
            total_questions=50,
            marks_per_correct=4.0,
            negative_marks=1.0,
            multi_marked_rule=MultiMarkedRule.COUNT_AS_WRONG.value,
        )
        db.add(exam)
        db.commit()
        db.refresh(exam)

        key1 = AnswerKey(
            exam_id=exam.id,
            set_code="A",
            question_no=1,
            correct_option="B",
        )
        db.add(key1)
        db.commit()

        # Duplicate key for same exam, set, and question
        key_dup = AnswerKey(
            exam_id=exam.id,
            set_code="A",
            question_no=1,
            correct_option="C",
        )
        db.add(key_dup)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_result_and_student_answers():
    db = SessionLocal()
    try:
        student = Student(
            roll_no="200001",
            name_final="PRIYA PATEL",
        )
        exam = Exam(
            name="Chemistry Final",
            code="CHEM-2026",
            total_questions=30,
        )
        db.add_all([student, exam])
        db.commit()
        db.refresh(student)
        db.refresh(exam)

        result = Result(
            student_id=student.id,
            exam_id=exam.id,
            set_code="B",
            total_questions=30,
            correct_count=25,
            wrong_count=4,
            not_attempted_count=1,
            total_score=96.0,
            percentage=80.0,
            status=SheetStatus.AUTO_ACCEPTED.value,
            confidence_score=0.98,
        )
        db.add(result)
        db.commit()
        db.refresh(result)

        ans1 = StudentAnswer(
            result_id=result.id,
            question_no=1,
            marked_option="A",
            is_correct=True,
            confidence=0.99,
            status=BubbleState.SINGLE.value,
        )
        ans2 = StudentAnswer(
            result_id=result.id,
            question_no=2,
            marked_option="C",
            is_correct=False,
            confidence=0.95,
            status=BubbleState.SINGLE.value,
        )
        db.add_all([ans1, ans2])
        db.commit()

        # Verify relationships
        loaded_res = db.query(Result).filter_by(id=result.id).first()
        assert loaded_res is not None
        assert len(loaded_res.answers) == 2
        assert loaded_res.student.name_final == "PRIYA PATEL"
        assert loaded_res.exam.code == "CHEM-2026"

        # Unique constraint on (student_id, exam_id)
        duplicate_res = Result(
            student_id=student.id,
            exam_id=exam.id,
            set_code="B",
        )
        db.add(duplicate_res)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_audit_log():
    db = SessionLocal()
    try:
        log = AuditLog(
            user_id=None,
            action="CHANGE_STUDENT_NAME",
            entity_type="Student",
            entity_id="101",
            old_values='{"name_final": "RAHUL"}',
            new_values='{"name_final": "RAHUL SHARMA"}',
            ip_address="127.0.0.1",
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.action == "CHANGE_STUDENT_NAME"
        assert log.timestamp is not None
    finally:
        db.close()
