"""
Unit tests for Report Generation (PDF/Excel) and Admin Endpoints.
"""

import pytest
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.models.models import User, UserRole, Exam, Student, Result, StudentAnswer, AuditLog
from backend.app.services.report_generator import (
    generate_exam_pdf_report,
    generate_student_card_pdf,
    generate_exam_excel_report
)
from backend.app.api.v1.reports import (
    download_exam_pdf,
    download_exam_excel,
    download_result_pdf
)
from backend.app.api.v1.admin import (
    get_audit_logs,
    get_system_settings,
    update_system_settings,
    SettingsUpdateSchema
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def auth_admin():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin_test").first()
        if not user:
            user = User(
                username="admin_test",
                email="admin_test@example.com",
                hashed_password="hashed_pw",
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()


@pytest.fixture
def seeded_report_data():
    db = SessionLocal()
    try:
        # Create or fetch exam
        exam = db.query(Exam).filter(Exam.code == "RPT-101").first()
        if not exam:
            exam = Exam(
                name="Reporting Test Exam",
                code="RPT-101",
                total_questions=50,
                marks_per_correct=2.0,
                negative_marks=0.5
            )
            db.add(exam)
            db.commit()
            db.refresh(exam)

        # Create student
        student = db.query(Student).filter(Student.roll_no == "990011").first()
        if not student:
            student = Student(
                roll_no="990011",
                name_final="ALICE SMITH",
                father_name_final="BOB SMITH",
                mobile_final="9876543210",
                class_name_final="12A",
                dob_final="2005-01-01"
            )
            db.add(student)
            db.commit()
            db.refresh(student)

        # Create result
        result = db.query(Result).filter(Result.student_id == student.id, Result.exam_id == exam.id).first()
        if not result:
            result = Result(
                student_id=student.id,
                exam_id=exam.id,
                set_code="A",
                total_score=85.0,
                correct_count=45,
                wrong_count=5,
                not_attempted_count=0,
                status="AUTO_ACCEPTED",
                confidence_score=0.98
            )
            db.add(result)
            db.commit()
            db.refresh(result)

            # Add answers
            for q in range(1, 51):
                ans = StudentAnswer(
                    result_id=result.id,
                    question_no=q,
                    marked_option="A",
                    is_correct=(q <= 45),
                    confidence=0.99
                )
                db.add(ans)
            db.commit()

        # Add an audit log entry
        log = AuditLog(
            user_id=1,
            action="TEST_ACTION",
            entity_type="exam",
            entity_id=str(exam.id),
            new_values='{"msg": "Reporting test"}'
        )
        db.add(log)
        db.commit()

        return {
            "exam_id": exam.id,
            "student_id": student.id,
            "result_id": result.id
        }
    finally:
        db.close()


def test_pdf_report_generators_direct(seeded_report_data):
    db = SessionLocal()
    try:
        exam = db.query(Exam).filter(Exam.id == seeded_report_data["exam_id"]).first()
        student = db.query(Student).filter(Student.id == seeded_report_data["student_id"]).first()
        result = db.query(Result).filter(Result.id == seeded_report_data["result_id"]).first()
        answers = db.query(StudentAnswer).filter(StudentAnswer.result_id == result.id).all()

        # 1. Exam summary PDF
        exam_pdf = generate_exam_pdf_report(exam, [result])
        assert isinstance(exam_pdf, bytes)
        assert exam_pdf.startswith(b"%PDF-")

        # 2. Student scorecard PDF
        student_pdf = generate_student_card_pdf(exam, student, result, answers)
        assert isinstance(student_pdf, bytes)
        assert student_pdf.startswith(b"%PDF-")

        # 3. Excel report
        excel_bytes = generate_exam_excel_report(exam, [result])
        assert isinstance(excel_bytes, bytes)
        assert excel_bytes.startswith(b"PK")  # ZIP signature
    finally:
        db.close()


def test_reports_api_endpoints(auth_admin, seeded_report_data):
    db = SessionLocal()
    try:
        exam_id = seeded_report_data["exam_id"]
        result_id = seeded_report_data["result_id"]

        # 1. Test PDF Exam Download
        res = download_exam_pdf(exam_id=exam_id, db=db, current_user=auth_admin)
        assert res.media_type == "application/pdf"
        assert res.body.startswith(b"%PDF-")

        # 2. Test Excel Exam Download
        res = download_exam_excel(exam_id=exam_id, db=db, current_user=auth_admin)
        assert "spreadsheetml" in res.media_type
        assert res.body.startswith(b"PK")

        # 3. Test Student Scorecard PDF Download
        res = download_result_pdf(result_id=result_id, db=db, current_user=auth_admin)
        assert res.media_type == "application/pdf"
        assert res.body.startswith(b"%PDF-")
    finally:
        db.close()


def test_admin_audit_logs_and_settings(auth_admin):
    db = SessionLocal()
    try:
        # Get Audit Logs
        data = get_audit_logs(limit=50, offset=0, action=None, db=db, current_user=auth_admin)
        assert "total" in data
        assert "items" in data

        # Get Settings
        settings_data = get_system_settings(current_user=auth_admin)
        assert "BUBBLE_FILL_THRESHOLD" in settings_data

        # Update Settings
        res = update_system_settings(
            payload=SettingsUpdateSchema(BUBBLE_FILL_THRESHOLD=0.46),
            current_user=auth_admin
        )
        assert res["settings"]["BUBBLE_FILL_THRESHOLD"] == 0.46
    finally:
        db.close()
